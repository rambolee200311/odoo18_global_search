"""Semantic readback checks for the narrowly enabled XLSX/DOCX baseline."""

from __future__ import annotations

import hashlib
import json
import math
import re
from copy import deepcopy
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from lxml import etree

from .errors import OfficeVerifyError
from .models import VerificationBudget, VerificationPolicy, VerificationReport
from .security import CT_NS, Package, _is_safe_picture_drawing, _safe_xlsx_extension_list, read_package, reject_unsupported_nodes

NS_REL_DOC = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
NS_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
NS_X = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def _fail(code: str, stage: str, message: str) -> OfficeVerifyError:
    return OfficeVerifyError(code, stage, message)


def _name(node: etree._Element) -> str:
    return etree.QName(node).localname if isinstance(node.tag, str) else ""


def _extension_signature(root: etree._Element | None) -> tuple[object, ...]:
    if root is None:
        return ()

    def signature(node: etree._Element) -> tuple[object, ...]:
        return (
            node.tag,
            tuple(sorted(node.attrib.items())),
            (node.text or "").strip(),
            tuple(signature(child) for child in node if isinstance(child.tag, str)),
        )

    return tuple(signature(node) for node in root if _name(node) == "extLst")


def _content_type_signature(package: Package) -> tuple[tuple[str, str, str], ...]:
    root = package.roots.get("[Content_Types].xml")
    if root is None:
        return ()
    result = []
    for node in root:
        part_name = node.get("PartName", "").lstrip("/")
        if part_name == "xl/sharedStrings.xml":
            continue
        result.append((_name(node), node.get("Extension", "") or part_name, node.get("ContentType", "")))
    return tuple(sorted(result))


def _elements(root: etree._Element, local: str) -> list[etree._Element]:
    return [node for node in root.iter() if _name(node) == local]


def _validate_plan(plan: object, source_sha: str, budget: VerificationBudget) -> list[dict[str, object]]:
    if not isinstance(plan, dict) or set(plan) != {"schema_version", "template_sha256", "writes"}:
        raise _fail("OFFICE_MAPPING_INVALID", "mapping", "映射结构包含缺失或未知字段。")
    if plan.get("schema_version") != "1":
        raise _fail("OFFICE_MAPPING_INVALID", "mapping", "映射版本不受支持。")
    if plan.get("template_sha256") != source_sha:
        raise _fail("OFFICE_MAPPING_INVALID", "mapping", "映射对应的模板指纹不匹配。")
    writes = plan.get("writes")
    if not isinstance(writes, list):
        raise _fail("OFFICE_MAPPING_INVALID", "mapping", "writes 必须是数组。")
    if len(writes) > max(budget.max_cells, budget.max_paragraphs):
        raise _fail("OFFICE_RESOURCE_LIMIT", "mapping", "映射目标数量超过限制。")
    seen: dict[str, set[str]] = {}
    clean: list[dict[str, object]] = []
    for item in writes:
        if not isinstance(item, dict) or set(item) != {"element_id", "operation", "value"}:
            raise _fail("OFFICE_MAPPING_INVALID", "mapping", "写入项包含缺失或未知字段。")
        element_id = item.get("element_id")
        value = item.get("value")
        if not isinstance(element_id, str):
            raise _fail("OFFICE_MAPPING_INVALID", "mapping", "写入目标无效或重复。")
        if len(element_id) > 512:
            raise _fail("OFFICE_RESOURCE_LIMIT", "mapping", "映射目标标识超过大小限制。")
        operation = item.get("operation")
        if operation not in {"set_value", "set_formula", "set_number_format"}:
            raise _fail("OFFICE_MAPPING_INVALID", "mapping", "只允许 set_value、受限 set_formula 或 set_number_format 操作。")
        prior_operations = seen.setdefault(element_id, set())
        if operation in prior_operations or (
            operation != "set_number_format"
            and prior_operations.intersection({"set_value", "set_formula"})
        ):
            raise _fail("OFFICE_MAPPING_INVALID", "mapping", "同一目标的值操作冲突或重复。")
        prior_operations.add(operation)
        if not isinstance(value, dict) or set(value) != {"type", "data"}:
            raise _fail("OFFICE_MAPPING_INVALID", "mapping", "value 必须包含且仅包含 type 与 data。")
        kind, data = value.get("type"), value.get("data")
        if operation == "set_number_format":
            if kind != "number_format" or not isinstance(data, str) or not data or len(data) > 128 or any(ord(char) < 32 for char in data):
                raise _fail("OFFICE_MAPPING_INVALID", "mapping", "数字格式字符串无效。")
        elif operation == "set_formula":
            if kind != "formula" or not _safe_arithmetic_formula(data):
                raise _fail("OFFICE_MAPPING_INVALID", "mapping", "公式内容无效；仅支持本表算术公式。")
        elif data is None:
            if kind != "string":
                raise _fail("NULL_NOT_SUPPORTED", "mapping", "只有字符串目标可以将 null 映射为空白。")
            data = ""
        if operation == "set_number_format":
            pass
        elif operation == "set_formula":
            pass
        elif kind == "string" and isinstance(data, str):
            try:
                encoded_size = len(data.encode("utf-8"))
            except UnicodeEncodeError as exc:
                raise _fail("OFFICE_MAPPING_INVALID", "mapping", "映射字符串不是有效 Unicode。") from exc
            if encoded_size > budget.max_mapping_bytes:
                raise _fail("OFFICE_RESOURCE_LIMIT", "mapping", "映射字符串超过大小限制。")
            pass
        elif kind == "number" and not isinstance(data, bool) and isinstance(data, (int, float)):
            if isinstance(data, float) and not math.isfinite(data):
                raise _fail("OFFICE_MAPPING_INVALID", "mapping", "数字值必须为有限数。")
        elif kind == "boolean" and isinstance(data, bool):
            pass
        elif kind == "date" and isinstance(data, str):
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", data):
                raise _fail("OFFICE_MAPPING_INVALID", "mapping", "日期必须使用有效的 ISO-8601 日期。")
            try:
                date.fromisoformat(data)
            except ValueError as exc:
                raise _fail("OFFICE_MAPPING_INVALID", "mapping", "日期必须使用有效的 ISO-8601 日期。") from exc
        elif kind == "datetime" and isinstance(data, str):
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?", data):
                raise _fail("OFFICE_MAPPING_INVALID", "mapping", "日期时间必须使用本地 ISO-8601 时间戳。")
            try:
                parsed = datetime.fromisoformat(data)
            except ValueError as exc:
                raise _fail("OFFICE_MAPPING_INVALID", "mapping", "日期时间必须使用本地 ISO-8601 时间戳。") from exc
            if parsed.utcoffset() is not None:
                raise _fail("OFFICE_MAPPING_INVALID", "mapping", "XLSX 日期时间不支持时区偏移。")
        else:
            raise _fail("OFFICE_MAPPING_INVALID", "mapping", "映射值类型与数据不匹配。")
        clean.append({"element_id": element_id, "operation": operation, "type": kind, "data": data})
    try:
        serialized_size = len(json.dumps(plan, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8"))
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise _fail("OFFICE_MAPPING_INVALID", "mapping", "映射值不是受支持的 JSON 数据。") from exc
    if serialized_size > budget.max_mapping_bytes:
        raise _fail("OFFICE_RESOURCE_LIMIT", "mapping", "映射计划超过大小限制。")
    return clean


def _safe_arithmetic_formula(formula: object) -> bool:
    """Validate arithmetic-only local formulas independently of the writer."""
    token_pattern = re.compile(
        r"\s*(?:(\$?[A-Za-z]{1,3}\$?[1-9][0-9]*)|((?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[Ee][+-]?[0-9]+)?)|([()+\-*/]))"
    )
    if not isinstance(formula, str) or not formula.startswith("=") or len(formula) > 512:
        return False
    expression = formula[1:].strip()
    if not expression:
        return False
    tokens = []
    position = 0
    while position < len(expression):
        match = token_pattern.match(expression, position)
        if not match:
            return False
        reference, number, operator = match.groups()
        tokens.append("reference" if reference else "number" if number else operator)
        position = match.end()
        if len(tokens) > 128:
            return False
    cursor = 0

    def peek(value=None):
        return cursor < len(tokens) and (value is None or tokens[cursor] == value)

    def consume():
        nonlocal cursor
        if cursor >= len(tokens):
            return None
        token = tokens[cursor]
        cursor += 1
        return token

    def expression_rule():
        if not term_rule():
            return False
        while peek("+") or peek("-"):
            consume()
            if not term_rule():
                return False
        return True

    def term_rule():
        if not factor_rule():
            return False
        while peek("*") or peek("/"):
            consume()
            if not factor_rule():
                return False
        return True

    def factor_rule():
        if peek("+") or peek("-"):
            consume()
            return factor_rule()
        if peek("("):
            consume()
            if not expression_rule() or not peek(")"):
                return False
            consume()
            return True
        return consume() in {"reference", "number"}

    return expression_rule() and cursor == len(tokens)


def _compare_packages(
    source: Package,
    output: Package,
    policy: VerificationPolicy,
    *,
    allow_number_format_changes: bool = False,
) -> list[dict[str, str]]:
    if source.kind != output.kind:
        raise _fail("OFFICE_INVALID_OR_MISMATCHED", "format", "输出格式与输入格式不一致。")
    source_entries = set(source.entries)
    output_entries = set(output.entries)
    # openpyxl rewrites shared strings as inline strings. This is an OOXML
    # representation change, not a loss of cell text; every other part remains
    # subject to the normal structure checks.
    optional_representation_parts = {"xl/sharedStrings.xml", "xl/styles.xml"} if source.kind == "xlsx" else set()
    if (source_entries - output_entries) - optional_representation_parts or (output_entries - source_entries) - optional_representation_parts:
        raise _fail("OFFICE_STRUCTURE_MISMATCH", "structure", "OOXML 部件集合发生变化。")
    for required in policy.required_parts:
        if required not in source.entries or required not in output.entries:
            raise _fail("OFFICE_STRUCTURE_MISMATCH", "structure", "策略要求保留的 Office 部件缺失。")
    if policy.require_relationships:
        for part_name in set(source.relationships) | set(output.relationships):
            source_rels = source.relationships.get(part_name, ())
            output_rels = output.relationships.get(part_name, ())
            if source.kind == "xlsx" and part_name == "xl/_rels/workbook.xml.rels":
                source_rels = tuple(rel for rel in source_rels if not rel[1].endswith("/sharedStrings"))
                output_rels = tuple(rel for rel in output_rels if not rel[1].endswith("/sharedStrings"))
                # Relationship IDs may be renumbered by the writer. The sheet
                # reader separately verifies that workbook sheet IDs resolve.
                source_rels = tuple(sorted((rel_type, target) for _, rel_type, target in source_rels))
                output_rels = tuple(sorted((rel_type, target) for _, rel_type, target in output_rels))
            elif part_name == "_rels/.rels":
                # Package-root relationship IDs are not referenced from part
                # XML. Writers may renumber these while preserving targets.
                source_rels = tuple(sorted((rel_type, target) for _, rel_type, target in source_rels))
                output_rels = tuple(sorted((rel_type, target) for _, rel_type, target in output_rels))
            if source_rels != output_rels:
                raise _fail("OFFICE_STRUCTURE_MISMATCH", "relationships", "Office 部件关系发生变化。")

    if source.kind == "xlsx" and "docProps/custom.xml" in source_entries:
        if "docProps/custom.xml" not in output_entries:
            raise _fail("OFFICE_STRUCTURE_MISMATCH", "custom_properties", "自定义文档属性部件缺失。")
        if _custom_properties(source.roots.get("docProps/custom.xml")) != _custom_properties(output.roots.get("docProps/custom.xml")):
            raise _fail("OFFICE_STRUCTURE_MISMATCH", "custom_properties", "自定义文档属性值发生变化。")
    if source.kind == "xlsx":
        if _content_type_signature(source) != _content_type_signature(output):
            raise _fail("OFFICE_STRUCTURE_MISMATCH", "content_types", "Office 部件类型声明发生未授权变化。")
        for part_name in ("xl/workbook.xml", "xl/styles.xml"):
            if _extension_signature(source.roots.get(part_name)) != _extension_signature(output.roots.get(part_name)):
                raise _fail("OFFICE_STRUCTURE_MISMATCH", "extensions", "已识别的 Excel 扩展结构发生变化。")
    else:
        if _content_type_signature(source) != _content_type_signature(output):
            raise _fail("OFFICE_STRUCTURE_MISMATCH", "content_types", "Word 部件类型声明发生未授权变化。")
        preserved_xml_parts = {
            name for name in source.entries
            if name == "docProps/custom.xml"
            or re.fullmatch(r"word/(?:header|footer)\d+\.xml", name)
        }
        for name in preserved_xml_parts:
            if _canonical(source.roots.get(name)) != _canonical(output.roots.get(name)):
                raise _fail("OFFICE_STRUCTURE_MISMATCH", "preserved_parts", "Word 页眉、页脚或自定义属性发生变化。")
    warnings: list[dict[str, str]] = []
    for style_part in ("xl/styles.xml", "word/styles.xml"):
        if style_part in source.roots and _canonical(source.roots[style_part]) != _canonical(output.roots.get(style_part)):
            if style_part == "xl/styles.xml" and allow_number_format_changes:
                continue
            if policy.require_styles:
                raise _fail("OFFICE_STRUCTURE_MISMATCH", "styles", "策略要求保留的样式部件发生变化。")
            warnings.append({"code": "NON_TARGET_STYLE_PART_CHANGED", "element_id": style_part})
    allowed_variable_parts = {
        "[Content_Types].xml", "_rels/.rels", "xl/_rels/workbook.xml.rels",
        "docProps/core.xml", "docProps/app.xml", "docProps/custom.xml", "xl/workbook.xml", "xl/sharedStrings.xml",
        "word/document.xml", "xl/calcChain.xml",
    }
    allowed_variable_parts.update(
        name for name in source.entries
        if name == "docProps/custom.xml" or re.fullmatch(r"word/(?:header|footer)\d+\.xml", name)
    )
    if source.kind == "xlsx":
        allowed_variable_parts.update(name for name in source.entries if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", name))
    for name in source.entries:
        if name in allowed_variable_parts or name in {"xl/styles.xml", "word/styles.xml"}:
            continue
        if name in optional_representation_parts or source.raw_parts.get(name) == output.raw_parts.get(name):
            continue
        if name in source.roots and name in output.roots and _canonical(source.roots[name]) == _canonical(output.roots[name]):
            continue
        raise _fail("OFFICE_STRUCTURE_MISMATCH", "structure", "非目标 Office 部件发生未分类变化。")
    return warnings


def _custom_properties(root: etree._Element | None) -> tuple[tuple[str, str, str, str], ...]:
    if root is None:
        return ()
    properties: list[tuple[str, str, str, str]] = []
    for node in root:
        if _name(node) != "property":
            raise _fail("OFFICE_INVALID_OR_MISMATCHED", "custom_properties", "自定义属性结构无效。")
        name = node.get("name", "")
        value_nodes = [child for child in node if isinstance(child.tag, str)]
        if not name or len(value_nodes) != 1 or len(value_nodes[0]):
            raise _fail("OFFICE_INVALID_OR_MISMATCHED", "custom_properties", "自定义属性结构无效。")
        value = value_nodes[0]
        properties.append((name, node.get("fmtid", ""), _name(value), value.text or ""))
    if len({item[0] for item in properties}) != len(properties):
        raise _fail("OFFICE_INVALID_OR_MISMATCHED", "custom_properties", "自定义属性名称重复。")
    return tuple(sorted(properties))


def _workbook_sheets(package: Package) -> list[tuple[str, str]]:
    workbook = package.roots.get("xl/workbook.xml")
    if workbook is None or workbook.tag != NS_X + "workbook":
        raise _fail("OFFICE_INVALID_OR_MISMATCHED", "xlsx", "工作簿主部件缺失。")
    safe_extensions = {
        child
        for extension in workbook
        if _name(extension) == "extLst" and _safe_xlsx_extension_list(extension)
        for child in extension.iter()
    }
    if any(
        node not in safe_extensions and isinstance(node.tag, str) and not node.tag.startswith(NS_X)
        for node in workbook.iter()
    ):
        raise _fail("OFFICE_UNSUPPORTED_FEATURE", "xlsx", "工作簿包含外来 XML 结构。")
    rels = {rel_id: target for rel_id, _, target in package.relationships.get("xl/_rels/workbook.xml.rels", ())}
    result: list[tuple[str, str]] = []
    seen: set[str] = set()
    for sheet in _elements(workbook, "sheet"):
        if sheet.tag != NS_X + "sheet":
            raise _fail("OFFICE_UNSUPPORTED_FEATURE", "xlsx", "工作簿包含外来 XML 结构。")
        title = sheet.get("name", "")
        rel_id = sheet.get(NS_REL_DOC + "id", "")
        target = rels.get(rel_id)
        if not title or title in seen or not target or target not in package.roots:
            raise _fail("OFFICE_INVALID_OR_MISMATCHED", "xlsx", "工作表名称或关系无效。")
        seen.add(title)
        result.append((title, target))
    if not result:
        raise _fail("OFFICE_INVALID_OR_MISMATCHED", "xlsx", "工作簿没有可验证的工作表。")
    return result


def _shared_strings(package: Package) -> list[str]:
    root = package.roots.get("xl/sharedStrings.xml")
    if root is None:
        return []
    return ["".join(node.text or "" for node in item.iter() if _name(node) == "t") for item in _elements(root, "si")]


def _cell_value(cell: etree._Element, shared: list[str]) -> tuple[str, object]:
    formula_nodes = [child for child in cell if _name(child) == "f"]
    value_nodes = [child for child in cell if _name(child) == "v"]
    if len(formula_nodes) > 1 or len(value_nodes) > 1:
        raise _fail("OFFICE_INVALID_OR_MISMATCHED", "xlsx", "单元格公式或值结构无效。")
    if formula_nodes:
        formula = formula_nodes[0]
        expression = formula.text or ""
        if "[" in expression or "]" in expression:
            raise _fail("OFFICE_UNSUPPORTED_FEATURE", "xlsx", "外部工作簿或当前未准入的结构化公式不支持。")
        return "formula", (expression, tuple(sorted(formula.attrib.items())))
    cell_type = cell.get("t", "n")
    raw = value_nodes[0].text if value_nodes else None
    if cell_type == "s":
        if raw is None or not raw.isdigit() or int(raw) >= len(shared):
            raise _fail("OFFICE_INVALID_OR_MISMATCHED", "xlsx", "共享字符串索引无效。")
        return "string", shared[int(raw)]
    if cell_type == "inlineStr":
        inline = next((child for child in cell if _name(child) == "is"), None)
        if inline is None:
            return "string", ""
        return "string", "".join(node.text or "" for node in inline.iter() if _name(node) == "t")
    if cell_type in {"str", "inlineStr"}:
        return "string", raw or ""
    if cell_type == "b":
        if raw not in {"0", "1"}:
            raise _fail("OFFICE_INVALID_OR_MISMATCHED", "xlsx", "布尔单元格值无效。")
        return "boolean", raw == "1"
    if cell_type in {"e", "d"}:
        raise _fail("OFFICE_UNSUPPORTED_FEATURE", "xlsx", "错误或日期序列单元格当前不在回读白名单中。")
    if raw is None:
        return "blank", None
    try:
        number = Decimal(raw)
    except InvalidOperation as exc:
        raise _fail("OFFICE_INVALID_OR_MISMATCHED", "xlsx", "数字单元格值无效。") from exc
    if not number.is_finite():
        raise _fail("OFFICE_INVALID_OR_MISMATCHED", "xlsx", "数字单元格值无效。")
    return "number", number


def _xlsx_state(
    package: Package, budget: VerificationBudget, policy: VerificationPolicy
) -> dict[str, object]:
    sheets = _workbook_sheets(package)
    workbook_root = package.roots["xl/workbook.xml"]
    workbook_properties = next(
        (node for node in workbook_root if _name(node) == "workbookPr"), None
    )
    date_1904_value = workbook_properties.get("date1904", "0") if workbook_properties is not None else "0"
    if date_1904_value not in {"0", "1", "false", "true"}:
        raise _fail("OFFICE_INVALID_OR_MISMATCHED", "xlsx", "Excel 日期系统声明无效。")
    date_1904 = date_1904_value in {"1", "true"}
    sheet_states = tuple(
        (node.get("name", ""), node.get("state", "visible"))
        for parent in workbook_root
        if _name(parent) == "sheets"
        for node in parent
        if _name(node) == "sheet"
    )
    if any(state not in {"visible", "hidden", "veryHidden"} for _, state in sheet_states):
        raise _fail("OFFICE_INVALID_OR_MISMATCHED", "xlsx", "工作表可见性状态无效。")
    shared = _shared_strings(package)
    cells: dict[str, tuple[str, object]] = {}
    cell_ids: set[str] = set()
    blank_targets: set[str] = set()
    formulas: dict[str, tuple[str, tuple[tuple[str, str], ...]]] = {}
    caches: dict[str, str | None] = {}
    styles: dict[str, str] = {}
    style_bases: dict[str, bytes] = {}
    number_formats: dict[str, str] = {}
    style_root = package.roots.get("xl/styles.xml")
    if style_root is None and policy.require_styles:
        raise _fail("OFFICE_STRUCTURE_MISMATCH", "styles", "Excel 样式部件缺失。")
    cell_xfs = (
        next((node for node in style_root if _name(node) == "cellXfs"), None)
        if style_root is not None
        else None
    )
    if cell_xfs is None and policy.require_styles:
        raise _fail("OFFICE_STRUCTURE_MISMATCH", "styles", "Excel cellXfs 样式表缺失。")
    # OOXML permits a workbook with no styles part. Such cells have the
    # implicit default style (index 0); use that semantic default for the
    # readback comparison instead of treating an omitted optional part as a
    # damaged workbook.
    default_xf = etree.Element(NS_X + "xf")
    effective_xfs = list(cell_xfs) if cell_xfs is not None else [default_xf]
    custom_formats = {
        int(node.get("numFmtId", "-1")): node.get("formatCode", "")
        for parent in (style_root if style_root is not None else ()) if _name(parent) == "numFmts"
        for node in parent if _name(node) == "numFmt"
    }
    built_in_formats = {
        0: "General", 1: "0", 2: "0.00", 3: "#,##0", 4: "#,##0.00",
        9: "0%", 10: "0.00%", 11: "0.00E+00", 12: "# ?/?", 13: "# ??/??",
        14: "mm-dd-yy", 15: "d-mmm-yy", 16: "d-mmm", 17: "mmm-yy",
        18: "h:mm AM/PM", 19: "h:mm:ss AM/PM", 20: "h:mm", 21: "h:mm:ss",
        22: "m/d/yy h:mm", 37: "#,##0 ;(#,##0)", 38: "#,##0 ;[Red](#,##0)",
        39: "#,##0.00;(#,##0.00)", 40: "#,##0.00;[Red](#,##0.00)",
    }
    merges: dict[str, tuple[str, ...]] = {}
    cell_count = 0
    sheet_names = tuple(title for title, _ in sheets)
    for title, part in sheets:
        root = package.roots[part]
        if root.tag != NS_X + "worksheet":
            raise _fail("OFFICE_INVALID_OR_MISMATCHED", "xlsx", "工作表主部件无效。")
        if any(isinstance(node.tag, str) and not node.tag.startswith(NS_X) for node in root.iter()):
            raise _fail("OFFICE_UNSUPPORTED_FEATURE", "xlsx", "工作表包含外来 XML 结构。")
        sheet_cells: dict[str, etree._Element] = {}
        populated_by_row: dict[int, list[int]] = {}
        for cell in _elements(root, "c"):
            if cell.tag != NS_X + "c" or any(isinstance(node.tag, str) and not node.tag.startswith(NS_X) for node in cell.iter()):
                raise _fail("OFFICE_UNSUPPORTED_FEATURE", "xlsx", "单元格包含外来 XML 结构。")
            address = cell.get("r", "")
            if not re.fullmatch(r"[A-Z]{1,3}[1-9][0-9]*", address) or address in sheet_cells:
                raise _fail("OFFICE_INVALID_OR_MISMATCHED", "xlsx", "工作表单元格坐标无效或重复。")
            sheet_cells[address] = cell
            cell_ids.add(f"xlsx:{title}!{address}")
            cell_count += 1
            if cell_count > budget.max_cells:
                raise _fail("OFFICE_RESOURCE_LIMIT", "xlsx", "工作表单元格数量超过限制。")
            kind, value = _cell_value(cell, shared)
            coordinate = re.fullmatch(r"([A-Z]{1,3})([1-9][0-9]*)", address)
            if coordinate is None:
                raise _fail("OFFICE_INVALID_OR_MISMATCHED", "xlsx", "工作表单元格坐标无效或重复。")
            if kind == "blank":
                if "s" in cell.attrib:
                    blank_targets.add(f"xlsx:{title}!{address}")
            else:
                populated_by_row.setdefault(int(coordinate.group(2)), []).append(
                    _col_number(coordinate.group(1))
                )
        merge_refs = tuple(sorted(node.get("ref", "") for node in _elements(root, "mergeCell")))
        if any(not value for value in merge_refs):
            raise _fail("OFFICE_INVALID_OR_MISMATCHED", "xlsx", "合并单元格引用无效。")
        merges[title] = merge_refs
        merged_nonanchors: set[str] = set()
        for merge in merge_refs:
            match = re.fullmatch(r"([A-Z]+[1-9][0-9]*):([A-Z]+[1-9][0-9]*)", merge)
            if not match:
                raise _fail("OFFICE_INVALID_OR_MISMATCHED", "xlsx", "合并单元格范围无效。")
            # The verifier only needs to ensure the requested target is not a non-anchor.
            for coordinate in sheet_cells:
                if coordinate != match.group(1) and _coordinate_in_range(coordinate, *match.groups()):
                    merged_nonanchors.add(coordinate)
        for address, cell in sheet_cells.items():
            key = f"xlsx:{title}!{address}"
            kind, value = _cell_value(cell, shared)
            if kind != "blank":
                cells[key] = (kind, value)
            if kind == "formula":
                formulas[key] = value  # type: ignore[assignment]
                v = next((child.text for child in cell if _name(child) == "v"), None)
                caches[key] = v
            style_index = int(cell.get("s", "0"))
            if style_index >= len(effective_xfs):
                raise _fail("OFFICE_STRUCTURE_MISMATCH", "styles", "单元格样式引用超出范围。")
            if style_index:
                styles[key] = str(style_index)
            xf = deepcopy(effective_xfs[style_index])
            num_fmt_id = int(xf.get("numFmtId", "0"))
            xf.attrib.pop("numFmtId", None)
            style_bases[key] = _canonical(xf)
            number_formats[key] = custom_formats.get(
                num_fmt_id, built_in_formats.get(num_fmt_id, f"builtin:{num_fmt_id}")
            )
            if address in merged_nonanchors and kind != "blank":
                raise _fail("OFFICE_STRUCTURE_MISMATCH", "xlsx", "合并单元格非锚点包含值。")
        for row_number, columns in populated_by_row.items():
            for column_number in range(min(columns), max(columns) + 1):
                coordinate = f"{_column_name(column_number)}{row_number}"
                cell = sheet_cells.get(coordinate)
                if cell is None or _cell_value(cell, shared)[0] == "blank":
                    blank_targets.add(f"xlsx:{title}!{coordinate}")
        for merge in merge_refs:
            start, end = merge.split(":", 1)
            for key in tuple(blank_targets):
                prefix = f"xlsx:{title}!"
                if key.startswith(prefix):
                    coordinate = key[len(prefix):]
                    if coordinate != start and _coordinate_in_range(coordinate, start, end):
                        blank_targets.discard(key)
    return {
        "sheets": sheet_names,
        "date_1904": date_1904,
        "sheet_states": sheet_states,
        "cells": cells,
        "cell_ids": cell_ids,
        "blank_targets": blank_targets,
        "formulas": formulas,
        "caches": caches,
        "styles": styles,
        "style_bases": style_bases,
        "number_formats": number_formats,
        "merges": merges,
    }


def _col_number(value: str) -> int:
    number = 0
    for char in value:
        number = number * 26 + ord(char) - 64
    return number


def _column_name(number: int) -> str:
    letters = ""
    while number:
        number, remainder = divmod(number - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def _coordinate_in_range(address: str, start: str, end: str) -> bool:
    def parts(cell: str) -> tuple[int, int]:
        match = re.fullmatch(r"([A-Z]+)([1-9][0-9]*)", cell)
        if not match:
            return (-1, -1)
        return _col_number(match.group(1)), int(match.group(2))
    col, row = parts(address)
    c1, r1 = parts(start)
    c2, r2 = parts(end)
    return col >= 0 and c1 >= 0 and min(c1, c2) <= col <= max(c1, c2) and min(r1, r2) <= row <= max(r1, r2)


def _check_xlsx(
    source: Package,
    output: Package,
    writes: list[dict[str, object]],
    budget: VerificationBudget,
    policy: VerificationPolicy,
    authorized_blank_targets: frozenset[str] = frozenset(),
) -> tuple[int, int, tuple[dict[str, object], ...], list[dict[str, str]]]:
    before = _xlsx_state(source, budget, policy)
    after = _xlsx_state(output, budget, policy)
    warnings: list[dict[str, str]] = []
    if before["sheets"] != after["sheets"]:
        raise _fail("OFFICE_STRUCTURE_MISMATCH", "xlsx", "工作表名称或顺序发生变化。")
    if before["date_1904"] != after["date_1904"]:
        raise _fail("OFFICE_STRUCTURE_MISMATCH", "xlsx", "Excel 日期系统发生变化。")
    if before["sheet_states"] != after["sheet_states"]:
        raise _fail("OFFICE_STRUCTURE_MISMATCH", "xlsx", "工作表可见性状态发生变化。")
    if before["merges"] != after["merges"]:
        raise _fail("OFFICE_STRUCTURE_MISMATCH", "xlsx", "合并单元格结构发生变化。")
    formula_writes = {
        item["element_id"]: item
        for item in writes
        if item.get("operation") == "set_formula"
    }
    number_format_writes = {
        item["element_id"]: item
        for item in writes
        if item.get("operation") == "set_number_format"
    }
    value_written_ids = {
        item["element_id"] for item in writes
        if item.get("operation") in {"set_value", "set_formula"}
    }
    expected_formulas = {
        key: value for key, value in before["formulas"].items() if key not in value_written_ids
    }
    for element_id, write in formula_writes.items():
        expression = write["data"][1:]
        expected_formulas[element_id] = (expression, ())
    if expected_formulas != after["formulas"]:
        raise _fail("OFFICE_FORMULA_MISMATCH", "xlsx", "工作簿公式表达式发生变化。")
    formula_caches = before["caches"]
    output_caches = after["caches"]
    cache_status = tuple(
        {
            "element_id": key,
            "source_cache": "present" if formula_caches[key] is not None else "missing",
            "output_cache": "present" if output_caches.get(key) is not None else "missing",
            "cached_value_changed": formula_caches[key] != output_caches.get(key),
        }
        for key in sorted(formula_caches)
    )
    targets: dict[str, dict[str, object]] = {}
    seen_operations: dict[str, set[str]] = {}
    for write in writes:
        element_id = write["element_id"]
        if not isinstance(element_id, str) or not element_id.startswith("xlsx:"):
            raise _fail("OFFICE_MAPPING_INVALID", "mapping", "映射目标与文件格式不匹配。")
        operation = write.get("operation")
        prior_operations = seen_operations.setdefault(element_id, set())
        if operation in prior_operations or (
            operation in {"set_value", "set_formula"}
            and prior_operations.intersection({"set_value", "set_formula"})
        ):
            raise _fail("OFFICE_MAPPING_INVALID", "mapping", "同一目标的值操作冲突或重复。")
        prior_operations.add(operation)
        sheet, coordinate = element_id[len("xlsx:"):].split("!", 1)
        location = re.fullmatch(r"([A-Z]{1,3})([1-9][0-9]*)", coordinate)
        if (
            sheet not in before["sheets"]
            or location is None
            or _col_number(location.group(1)) > 16_384
            or int(location.group(2)) > 1_048_576
        ):
            raise _fail("OFFICE_MAPPING_INVALID", "mapping", "映射目标不是当前工作表中的有效单元格。")
        target_is_in_source = (
            element_id in before["cells"]
            or element_id in before["cell_ids"]
            or element_id in before["blank_targets"]
        )
        is_explicit_clear = (
            operation == "set_value"
            and write.get("type") == "string"
            and write.get("data") == ""
        )
        is_value_write = operation in {"set_value", "set_formula"} and not is_explicit_clear
        if not target_is_in_source and not is_value_write and not (
            element_id in authorized_blank_targets and is_explicit_clear
        ):
            raise _fail(
                "OFFICE_MAPPING_INVALID",
                "mapping",
                f"映射目标不存在于模板结构目录中，且不是已授权的显式清空：{element_id}。",
            )
        if element_id in authorized_blank_targets:
            if not is_explicit_clear:
                raise _fail("OFFICE_MAPPING_INVALID", "mapping", "显式清空目标必须对应空字符串写入。")
        if any(
            coordinate != merge.split(":", 1)[0]
            and _coordinate_in_range(coordinate, *merge.split(":", 1))
            for merge in before["merges"].get(sheet, ())
        ):
            raise _fail("OFFICE_MAPPING_INVALID", "mapping", "合并单元格非锚点不可写。")
        if operation != "set_number_format":
            targets[element_id] = write
    explicit_clears = {
        item["element_id"]
        for item in writes
        if item.get("operation") == "set_value"
        and item.get("type") == "string"
        and item.get("data") == ""
    }
    if not authorized_blank_targets.issubset(explicit_clears):
        raise _fail("OFFICE_MAPPING_INVALID", "mapping", "缺失单元格授权只能用于显式清空操作。")
    source_content = {
        key
        for key, (kind, value) in before["cells"].items()
        if not (kind == "string" and value == "")
    }
    # A mapping write is an explicit authorization for the requested coordinate.
    # The independent verifier checks that it is a valid cell on an existing
    # sheet, then verifies its value and ensures unrelated source cells survive.
    # Requiring the blank target to already be serialized in the source package
    # would reject normal unformatted blank cells that the adapter can write.
    expected_cells = (
        source_content
        | {
            key for key, write in targets.items()
            if write.get("operation") in {"set_value", "set_formula"}
            and key not in explicit_clears
        }
    ) - explicit_clears
    after_content = {
        key
        for key, (kind, value) in after["cells"].items()
        if not (kind == "string" and value == "")
    }
    if expected_cells != after_content:
        raise _fail("OFFICE_STRUCTURE_MISMATCH", "xlsx", "非空单元格结构发生变化。")
    if any(
        after["cells"].get(key) not in (None, ("string", ""))
        for key in explicit_clears
    ):
        raise _fail("OFFICE_TARGET_MISMATCH", "target", "清空目标仍包含内容。")
    for key in expected_cells:
        if key in formula_writes:
            if after["cells"].get(key, (None, None))[0] != "formula":
                raise _fail("OFFICE_TARGET_MISMATCH", "target", "公式目标未写入公式。")
        elif key in targets:
            expected = targets[key]
            actual_kind, actual_value = after["cells"][key]
            if not _matches(
                expected["type"],
                expected["data"],
                actual_kind,
                actual_value,
                after["date_1904"],
            ):
                raise _fail("OFFICE_TARGET_MISMATCH", "target", "映射目标的回读值与预期不一致。")
        elif key in number_format_writes:
            if before["cells"].get(key) != after["cells"].get(key):
                raise _fail("OFFICE_TARGET_MISMATCH", "target", "仅修改数字格式时，单元格值必须保持不变。")
        elif before["cells"].get(key) != after["cells"].get(key):
            raise _fail("OFFICE_STRUCTURE_MISMATCH", "xlsx", "非目标单元格内容发生变化。")
    for key, write in number_format_writes.items():
        if before["style_bases"].get(key) != after["style_bases"].get(key):
            raise _fail("OFFICE_STRUCTURE_MISMATCH", "styles", "数字格式修改意外改变了目标单元格的其他样式。")
        if after["number_formats"].get(key) != write["data"]:
            raise _fail("OFFICE_TARGET_MISMATCH", "target", "目标单元格数字格式与映射不一致。")
    before_styles, after_styles = before["styles"], after["styles"]
    for key in set(before_styles) | set(after_styles):
        if before_styles.get(key) != after_styles.get(key):
            if key in number_format_writes:
                continue
            if policy.require_styles:
                raise _fail("OFFICE_STRUCTURE_MISMATCH", "styles", "策略要求保留的单元格样式发生变化。")
            warnings.append({"code": "NON_TARGET_STYLE_CHANGED", "element_id": key})
    return len(targets), len(after["formulas"]), cache_status, warnings


def _matches(
    expected_kind: object,
    expected: object,
    actual_kind: str,
    actual: object,
    date_1904: bool = False,
) -> bool:
    if expected_kind == "string":
        return actual_kind == "string" and actual == expected
    if expected_kind == "boolean":
        return actual_kind == "boolean" and actual is expected
    if expected_kind == "number" and actual_kind == "number":
        try:
            return Decimal(str(expected)) == actual
        except InvalidOperation:
            return False
    if expected_kind in {"date", "datetime"} and actual_kind == "number":
        try:
            expected_serial = _excel_date_serial(expected_kind, expected, date_1904)
            return abs(Decimal(actual) - expected_serial) <= Decimal("0.0000000001")
        except (InvalidOperation, TypeError, ValueError):
            return False
    return False


def _excel_date_serial(kind: str, value: str, date_1904: bool) -> Decimal:
    """Convert a validated local ISO date to its stored Excel serial value."""
    if kind == "date":
        parsed_date = date.fromisoformat(value)
        parsed = datetime.combine(parsed_date, datetime.min.time())
    elif kind == "datetime":
        parsed = datetime.fromisoformat(value)
        if parsed.utcoffset() is not None:
            raise ValueError("timezone_unsupported")
    else:
        raise ValueError("unsupported_date_type")
    epoch = datetime(1904, 1, 1) if date_1904 else datetime(1899, 12, 30)
    delta = parsed - epoch
    serial = Decimal(delta.days) + Decimal(
        delta.seconds * 1_000_000 + delta.microseconds
    ) / Decimal(86_400_000_000)
    # Excel's 1900 date system includes the fictitious 1900-02-29.
    if not date_1904 and 0 < delta.days <= 60:
        serial -= Decimal(1)
    return serial


def _paragraph_plain_text(paragraph: etree._Element) -> str:
    paragraph_children = {"pPr", "r", "bookmarkStart", "bookmarkEnd", "proofErr"}
    run_children = {"rPr", "t", "instrText", "fldChar", "drawing", "br", "tab", "noBreakHyphen", "softHyphen"}
    for child in paragraph:
        if isinstance(child.tag, str) and not child.tag.startswith(NS_W):
            raise _fail("OFFICE_UNSUPPORTED_FEATURE", "docx", "Word 段落包含外来 XML 结构。")
        if _name(child) not in paragraph_children:
            raise _fail("OFFICE_UNSUPPORTED_FEATURE", "docx", "Word 段落含当前不支持的结构。")
        if _name(child) in {"pPr", "bookmarkStart", "bookmarkEnd", "proofErr"}:
            continue
        for run_child in child:
            if isinstance(run_child.tag, str) and not run_child.tag.startswith(NS_W):
                raise _fail("OFFICE_UNSUPPORTED_FEATURE", "docx", "Word 文本包含外来 XML 结构。")
            if _name(run_child) not in run_children:
                raise _fail("OFFICE_UNSUPPORTED_FEATURE", "docx", "Word 文本含当前不支持的控制结构。")
            if _name(run_child) == "t" and len(run_child):
                raise _fail("OFFICE_UNSUPPORTED_FEATURE", "docx", "Word 文本节点含嵌套结构。")
    return "".join(node.text or "" for node in paragraph.iter() if node.tag == NS_W + "t")


def _canonical(node: etree._Element) -> bytes:
    return etree.tostring(node, method="c14n", exclusive=True, with_comments=False)


def _paragraph_format(paragraph: etree._Element) -> tuple[bytes, tuple[bytes, ...], bytes]:
    paragraph_properties = next((child for child in paragraph if _name(child) == "pPr"), None)
    ppr = _canonical(paragraph_properties) if paragraph_properties is not None else b""
    run_styles: list[bytes] = []
    for run in (child for child in paragraph if _name(child) == "r"):
        run_properties = next((child for child in run if _name(child) == "rPr"), None)
        signature = _canonical(run_properties) if run_properties is not None else b""
        if not run_styles or run_styles[-1] != signature:
            run_styles.append(signature)
    structure = deepcopy(paragraph)
    for text_node in structure.iter(NS_W + "t"):
        text_node.text = "__OFFICE_TEXT__"
    return ppr, tuple(run_styles), _canonical(structure)


def _docx_texts(package: Package, budget: VerificationBudget) -> tuple[dict[str, str], tuple[object, ...], dict[str, object]]:
    root = package.roots.get("word/document.xml")
    if root is None or root.tag != NS_W + "document":
        raise _fail("OFFICE_INVALID_OR_MISMATCHED", "docx", "Word 正文部件缺失。")
    safe_drawing_nodes: set[etree._Element] = set()
    for drawing in root.iter(NS_W + "drawing"):
        if not _is_safe_picture_drawing(drawing, "word/document.xml", package):
            raise _fail("OFFICE_UNSUPPORTED_FEATURE", "docx", "Word 正文图片结构未通过安全校验。")
        safe_drawing_nodes.update(drawing.iter())
    if any(
        isinstance(node.tag, str) and not node.tag.startswith(NS_W) and node not in safe_drawing_nodes
        for node in root.iter()
    ):
        raise _fail("OFFICE_UNSUPPORTED_FEATURE", "docx", "Word 正文包含外来 XML 结构。")
    body = next((node for node in root.iter() if node.tag == NS_W + "body"), None)
    if body is None:
        raise _fail("OFFICE_INVALID_OR_MISMATCHED", "docx", "Word 正文结构无效。")
    text_by_id: dict[str, str] = {}
    formatting: dict[str, object] = {}
    layout: list[object] = []
    paragraph_index = 0
    table_index = 0
    total_paragraphs = 0

    def add_paragraph(node: etree._Element, element_id: str) -> None:
        nonlocal paragraph_index, total_paragraphs
        paragraph_index += 1
        total_paragraphs += 1
        if total_paragraphs > budget.max_paragraphs:
            raise _fail("OFFICE_RESOURCE_LIMIT", "docx", "Word 段落数量超过限制。")
        value = _paragraph_plain_text(node)
        layout.append(("p", element_id))
        formatting[element_id] = _paragraph_format(node)
        if value:
            text_by_id[element_id] = value

    for child in body:
        if isinstance(child.tag, str) and not child.tag.startswith(NS_W):
            raise _fail("OFFICE_UNSUPPORTED_FEATURE", "docx", "Word 正文包含外来 XML 结构。")
        local = _name(child)
        if local == "p":
            add_paragraph(child, f"docx:p:{paragraph_index + 1}")
        elif local == "tbl":
            table_index += 1
            if any(_name(node) not in {"tblPr", "tblGrid", "tr"} for node in child):
                raise _fail("OFFICE_UNSUPPORTED_FEATURE", "docx", "Word 表格含当前未启用的结构。")
            formatting[f"docx:table:{table_index}:properties"] = tuple(
                _canonical(node) for node in child if _name(node) in {"tblPr", "tblGrid"}
            )
            rows: list[tuple[tuple[str, ...], ...]] = []
            row_nodes = [node for node in child if _name(node) == "tr"]
            for row_index, row in enumerate(row_nodes, 1):
                if any(_name(node) not in {"tblPrEx", "trPr", "tc"} for node in row):
                    raise _fail("OFFICE_UNSUPPORTED_FEATURE", "docx", "Word 表格行含当前未启用的结构。")
                formatting[f"docx:table:{table_index}:row:{row_index}:properties"] = tuple(
                    _canonical(node) for node in row if _name(node) in {"tblPrEx", "trPr"}
                )
                cells = [node for node in row if _name(node) == "tc"]
                row_cells: list[tuple[str, ...]] = []
                for cell_index, cell in enumerate(cells, 1):
                    if any(_name(node) not in {"tcPr", "p"} for node in cell):
                        raise _fail("OFFICE_UNSUPPORTED_FEATURE", "docx", "Word 表格单元格含当前未启用的结构。")
                    formatting[f"docx:table:{table_index}:row:{row_index}:cell:{cell_index}:properties"] = tuple(
                        _canonical(node) for node in cell if _name(node) == "tcPr"
                    )
                    cell_paragraph_ids: list[str] = []
                    if any(_name(nested) == "tbl" for nested in cell.iter() if nested is not cell):
                        raise _fail("OFFICE_UNSUPPORTED_FEATURE", "docx", "嵌套表格当前不支持。")
                    paragraphs = [node for node in cell if _name(node) == "p"]
                    for cell_para_index, paragraph in enumerate(paragraphs, 1):
                        element_id = f"docx:table:{table_index}:row:{row_index}:cell:{cell_index}:p:{cell_para_index}"
                        cell_paragraph_ids.append(element_id)
                        add_paragraph(paragraph, element_id)
                    row_cells.append(tuple(cell_paragraph_ids))
                rows.append(tuple(row_cells))
            layout.append(("table", tuple(rows)))
        elif local == "sectPr":
            layout.append(("sectPr",))
            formatting["docx:section"] = _canonical(child)
        else:
            raise _fail("OFFICE_UNSUPPORTED_FEATURE", "docx", "Word 正文含当前不支持的结构。")
    return text_by_id, tuple(layout), formatting


def _check_docx(
    source: Package,
    output: Package,
    writes: list[dict[str, object]],
    budget: VerificationBudget,
    policy: VerificationPolicy,
) -> tuple[int, int, tuple[dict[str, object], ...], list[dict[str, str]]]:
    before, before_layout, before_formatting = _docx_texts(source, budget)
    after, after_layout, after_formatting = _docx_texts(output, budget)
    if before_layout != after_layout or set(before) != set(after):
        raise _fail("OFFICE_STRUCTURE_MISMATCH", "docx", "Word 段落/表格结构或文本目标目录发生变化。")
    targets: dict[str, dict[str, object]] = {}
    for write in writes:
        element_id = write["element_id"]
        if not isinstance(element_id, str) or not element_id.startswith("docx:"):
            raise _fail("OFFICE_MAPPING_INVALID", "mapping", "映射目标与文件格式不匹配。")
        if element_id in targets:
            raise _fail("OFFICE_MAPPING_INVALID", "mapping", "写入目标重复。")
        if element_id not in before:
            raise _fail("OFFICE_MAPPING_INVALID", "mapping", "映射目标不存在于模板结构目录中。")
        if write["type"] != "string":
            raise _fail("OFFICE_MAPPING_INVALID", "mapping", "Word 只接受字符串映射值。")
        targets[element_id] = write
    for key, original in before.items():
        if key in targets:
            if after[key] != targets[key]["data"]:
                raise _fail("OFFICE_TARGET_MISMATCH", "target", "映射目标的回读值与预期不一致。")
        elif original != after[key]:
            raise _fail("OFFICE_STRUCTURE_MISMATCH", "docx", "非目标 Word 段落文本发生变化。")
    if before_formatting.keys() != after_formatting.keys():
        raise _fail("OFFICE_STRUCTURE_MISMATCH", "docx", "Word 样式结构目标发生变化。")
    style_warnings: list[dict[str, str]] = []
    for key in before_formatting:
        if before_formatting[key] != after_formatting[key]:
            if policy.require_styles or key in targets:
                raise _fail("OFFICE_STRUCTURE_MISMATCH", "styles", "策略要求保留的 Word 样式结构发生变化。")
            style_warnings.append({"code": "NON_TARGET_STYLE_CHANGED", "element_id": key})
    return len(targets), 0, (), style_warnings


def verify_inline(
    source_bytes: bytes,
    candidate_bytes: bytes,
    filename: str,
    mime_type: str,
    mapping_plan: object,
    policy: VerificationPolicy,
    budget: VerificationBudget,
    *,
    authorized_blank_targets: tuple[str, ...] = (),
) -> VerificationReport:
    if not isinstance(policy, VerificationPolicy) or not isinstance(budget, VerificationBudget):
        raise _fail("OFFICE_INVALID_OR_MISMATCHED", "input", "验证策略或资源预算类型无效。")
    policy.validate()
    budget.validate()
    if (
        not isinstance(authorized_blank_targets, tuple)
        or len(authorized_blank_targets) > budget.max_cells
        or any(not isinstance(item, str) or len(item) > 512 for item in authorized_blank_targets)
        or len(set(authorized_blank_targets)) != len(authorized_blank_targets)
    ):
        raise _fail("OFFICE_MAPPING_INVALID", "mapping", "显式清空目标列表无效。")
    if not isinstance(source_bytes, bytes) or not isinstance(candidate_bytes, bytes):
        raise _fail("OFFICE_INVALID_OR_MISMATCHED", "input", "源文件和候选文件必须以字节传入。")
    source_sha = hashlib.sha256(source_bytes).hexdigest()
    output_sha = hashlib.sha256(candidate_bytes).hexdigest()
    plan_writes = _validate_plan(mapping_plan, source_sha, budget)
    source = read_package(source_bytes, filename, mime_type, budget)
    output = read_package(candidate_bytes, filename, mime_type, budget)
    if source.kind not in policy.enabled_formats:
        raise _fail("OFFICE_UNSUPPORTED_FEATURE", "format", "该文件格式当前未启用回读能力。")
    if authorized_blank_targets and source.kind != "xlsx":
        raise _fail("OFFICE_MAPPING_INVALID", "mapping", "缺失单元格授权仅适用于 Excel 清空操作。")
    reject_unsupported_nodes(source)
    reject_unsupported_nodes(output)
    has_number_format_write = any(item.get("operation") == "set_number_format" for item in plan_writes)
    warnings = _compare_packages(
        source,
        output,
        policy,
        allow_number_format_changes=has_number_format_write,
    )
    if source.kind == "xlsx":
        count, formulas, formula_cache_status, semantic_warnings = _check_xlsx(
            source,
            output,
            plan_writes,
            budget,
            policy,
            frozenset(authorized_blank_targets),
        )
    else:
        count, formulas, formula_cache_status, semantic_warnings = _check_docx(source, output, plan_writes, budget, policy)
    warnings.extend(semantic_warnings)
    # Stable de-duplication prevents one style change from generating duplicate warnings.
    warnings = list({(item["code"], item["element_id"]): item for item in warnings}.values())
    return VerificationReport(
        status="PASS",
        format=source.kind,
        input_sha256=source_sha,
        output_sha256=output_sha,
        checked_targets=count,
        checked_formulas=formulas,
        cached_value_changed=any(item["cached_value_changed"] for item in formula_cache_status),
        formula_cache_status=formula_cache_status,
        warnings=tuple(sorted(warnings, key=lambda item: (item["code"], item["element_id"]))),
    )
