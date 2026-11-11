"""Semantic readback checks for the narrowly enabled XLSX/DOCX baseline."""

from __future__ import annotations

import hashlib
import json
import math
import re
from copy import deepcopy
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation

from lxml import etree

from .errors import OfficeVerifyError
from .models import CandidateValidationReport, VerificationBudget, VerificationPolicy, VerificationReport
from .security import CT_NS, Package, _is_safe_picture_drawing, _safe_xlsx_extension_list, read_package, reject_unsupported_nodes

NS_REL_DOC = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
NS_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
NS_X = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
NS_CP = "{http://schemas.openxmlformats.org/package/2006/metadata/core-properties}"
NS_DC = "{http://purl.org/dc/elements/1.1/}"
NS_DCTERMS = "{http://purl.org/dc/terms/}"
NS_XSI = "{http://www.w3.org/2001/XMLSchema-instance}"
NS_XML = "{http://www.w3.org/XML/1998/namespace}"


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


def _semantic_xml_signature(node: etree._Element) -> tuple[object, ...]:
    """Represent XML by expanded names so namespace prefix spelling is immaterial."""
    return (
        node.tag,
        tuple(sorted(node.attrib.items())),
        (node.text or "").strip(),
        tuple(_semantic_xml_signature(child) for child in node if isinstance(child.tag, str)),
    )


def _core_properties_signature(
    package: Package,
) -> tuple[tuple[str, tuple[tuple[str, str], ...], str], ...] | None:
    """Return a strict semantic signature for standard OOXML core properties.

    The modified timestamp is volatile when an editor saves a workbook. Its
    value may change, but the part's schema, date type, presence and all other
    property values remain significant. Unknown fields/attributes are rejected
    so this exception cannot become a blanket exemption for docProps/core.xml.
    """
    root = package.roots.get("docProps/core.xml")
    if root is None:
        return None
    if root.tag != NS_CP + "coreProperties" or root.attrib:
        raise _fail("OFFICE_INVALID_OR_MISMATCHED", "core_properties", "OOXML 核心属性根结构无效。")

    allowed_names = {
        NS_DC + name for name in ("title", "subject", "creator", "description", "keywords", "language", "identifier")
    } | {
        NS_CP + name for name in ("lastModifiedBy", "revision", "lastPrinted", "category", "contentStatus", "version")
    } | {NS_DCTERMS + "created", NS_DCTERMS + "modified"}
    values: dict[str, tuple[tuple[tuple[str, str], ...], str]] = {}
    for child in root:
        if not isinstance(child.tag, str) or child.tag not in allowed_names or len(child):
            raise _fail("OFFICE_UNSUPPORTED_FEATURE", "core_properties", "OOXML 核心属性包含未支持的字段或嵌套结构。")
        if child.tag in values:
            raise _fail("OFFICE_INVALID_OR_MISMATCHED", "core_properties", "OOXML 核心属性字段重复。")

        attributes = dict(child.attrib)
        type_attribute = NS_XSI + "type"
        space_attribute = NS_XML + "space"
        allowed_attributes = {space_attribute}
        if child.tag in {NS_DCTERMS + "created", NS_DCTERMS + "modified"}:
            allowed_attributes.add(type_attribute)
            declared_type = attributes.get(type_attribute)
            if declared_type is not None:
                prefix, separator, local_name = declared_type.partition(":")
                namespace = child.nsmap.get(prefix) if separator else None
                if (namespace, local_name) != (NS_DCTERMS[1:-1], "W3CDTF"):
                    raise _fail("OFFICE_INVALID_OR_MISMATCHED", "core_properties", "OOXML 核心属性日期类型无效。")
            attributes[type_attribute] = NS_DCTERMS + "W3CDTF"
            text = child.text or ""
            try:
                parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            except ValueError as exc:
                raise _fail("OFFICE_INVALID_OR_MISMATCHED", "core_properties", "OOXML 核心属性日期值无效。") from exc
            if parsed.tzinfo is not None:
                parsed = parsed.astimezone(timezone.utc)
                normalized = parsed.isoformat(timespec="microseconds").replace("+00:00", "Z")
            else:
                normalized = parsed.isoformat(timespec="microseconds")
            if child.tag == NS_DCTERMS + "modified":
                normalized = "<volatile-modified-timestamp>"
        else:
            normalized = child.text or ""
        if set(attributes) - allowed_attributes or attributes.get(space_attribute) not in (None, "default", "preserve"):
            raise _fail("OFFICE_UNSUPPORTED_FEATURE", "core_properties", "OOXML 核心属性包含未支持的属性。")
        if attributes.get(space_attribute) == "default":
            attributes.pop(space_attribute)
        values[child.tag] = (tuple(sorted(attributes.items())), normalized)
    return tuple((name, attributes, value) for name, (attributes, value) in sorted(values.items()))


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
    if cell_type == "d":
        if raw is None:
            raise _fail("OFFICE_INVALID_OR_MISMATCHED", "xlsx", "日期单元格缺少值。")
        try:
            if "T" in raw or "t" in raw:
                value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                return "datetime", value
            return "date", date.fromisoformat(raw)
        except ValueError as exc:
            raise _fail("OFFICE_INVALID_OR_MISMATCHED", "xlsx", "日期单元格值无效。") from exc
    if cell_type == "e":
        raise _fail("OFFICE_UNSUPPORTED_FEATURE", "xlsx", "错误单元格当前不在回读白名单中。")
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
    built_in_formats.update({
        format_id: f"builtin_date:{format_id}"
        for format_id in (*range(27, 37), *range(50, 59))
    })
    merges: dict[str, tuple[str, ...]] = {}
    worksheet_structures: dict[str, tuple[bytes, ...]] = {}
    row_structures: dict[str, tuple[tuple[str, tuple[tuple[str, str], ...]], ...]] = {}
    cell_structures: dict[str, tuple[tuple[tuple[str, str], ...], tuple[str, ...]]] = {}
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
            cell_structures[f"xlsx:{title}!{address}"] = (
                tuple(sorted((key, value) for key, value in cell.attrib.items() if key not in {"r", "s", "t"})),
                tuple(_name(child) for child in cell if _name(child) not in {"f", "v", "is"}),
            )
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
        worksheet_structures[title] = tuple(
            _canonical(node)
            for node in root
            # Worksheet dimension is derived from populated coordinates and
            # can change during an ordinary cell write. It is not independent
            # worksheet structure; the package/XML and cell-coordinate checks
            # above remain responsible for integrity.
            if _name(node) not in {"sheetData", "mergeCells", "extLst", "dimension"}
        )
        row_structures[title] = tuple(sorted(
            (node.get("r", ""), tuple(sorted((key, value) for key, value in node.attrib.items() if key != "r")))
            for node in _elements(root, "row")
            # Empty row elements are a serialization detail when a new cell is
            # written. Meaningful row properties (height, hidden, style, etc.)
            # remain compared and unauthorized differences still fail.
            if any(key != "r" for key in node.attrib)
        ))
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
            # Writers may serialize the OOXML defaults explicitly on an xf
            # that was previously represented by omitted attributes. Compare
            # the effective style, not whether default zero/false attributes
            # happened to be present in this serialization.
            for attribute in (
                "fontId", "fillId", "borderId", "xfId", "pivotButton", "quotePrefix",
            ):
                if xf.get(attribute) == "0":
                    xf.attrib.pop(attribute, None)
            for attribute in (
                "applyNumberFormat", "applyFont", "applyFill", "applyBorder",
                "applyAlignment", "applyProtection",
            ):
                if (xf.get(attribute) or "").lower() in {"0", "false"}:
                    xf.attrib.pop(attribute, None)
            style_bases[key] = repr(_semantic_xml_signature(xf)).encode("utf-8")
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
        "worksheet_structures": worksheet_structures,
        "row_structures": row_structures,
        "cell_structures": cell_structures,
        "sheet_parts": {title: part for title, part in sheets},
        "workbook_structures": tuple(
            _canonical(node)
            for node in workbook_root
            if _name(node) not in {"sheets", "workbookPr"}
        ),
        "workbook_attributes": tuple(sorted(workbook_root.attrib.items())),
        "workbook_properties": tuple(sorted(workbook_properties.attrib.items())) if workbook_properties is not None else (),
        "content_types": _content_type_signature(package),
    }


_CANDIDATE_CHANGE_KINDS = {
    "cell_value", "formula_text", "cell_style", "worksheet_structure", "workbook_structure"
}
_A1 = re.compile(r"^[A-Z]{1,3}[1-9][0-9]*$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _candidate_failure(message: str, *, input_sha: str, output_sha: str, parent_id: int, digest: str) -> CandidateValidationReport:
    return CandidateValidationReport(
        validation_result="FAILED",
        input_sha256=input_sha,
        output_sha256=output_sha,
        parent_version_id=parent_id,
        effect_digest=digest,
        actual_effects=(),
        risk_facts=(),
        feature_results=(),
        error={"error_code": "OFFICE_TARGET_MISMATCH", "failed_stage": "effect", "message": message},
    )


def _canonical_effect(effect: object, source_sha: str, budget: VerificationBudget) -> tuple[dict[str, object], str]:
    required = {
        "schema_version", "parent_version_id", "input_sha256", "target_scopes",
        "allowed_change_kinds", "expected_assertions", "unknowns", "effect_digest",
    }
    if not isinstance(effect, dict) or set(effect) != required or effect.get("schema_version") != "1":
        raise _fail("OFFICE_MAPPING_INVALID", "effect", "Expected Effect 结构或版本无效。")
    parent_id = effect.get("parent_version_id")
    # Parent 0 is the explicit, unversioned raw-upload source used only for
    # the first Route B Candidate. Positive IDs remain required for edits.
    if type(parent_id) is not int or parent_id < 0:
        raise _fail("OFFICE_MAPPING_INVALID", "effect", "Expected Effect 父版本无效。")
    if effect.get("input_sha256") != source_sha:
        raise _fail("OFFICE_INVALID_OR_MISMATCHED", "effect", "Expected Effect 的输入文件指纹不匹配。")
    scopes = effect.get("target_scopes")
    allowed = effect.get("allowed_change_kinds")
    assertions = effect.get("expected_assertions")
    unknowns = effect.get("unknowns")
    if not isinstance(scopes, list) or not scopes or len(scopes) > budget.max_cells:
        raise _fail("OFFICE_MAPPING_INVALID", "effect", "Expected Effect 目标范围无效。")
    if not isinstance(allowed, list) or any(item not in _CANDIDATE_CHANGE_KINDS for item in allowed) or len(set(allowed)) != len(allowed):
        raise _fail("OFFICE_MAPPING_INVALID", "effect", "Expected Effect 变化类别无效。")
    if not isinstance(assertions, list) or len(assertions) > budget.max_cells:
        raise _fail("OFFICE_MAPPING_INVALID", "effect", "Expected Effect 预期断言无效。")
    if not isinstance(unknowns, list) or len(unknowns) > 256 or any(not isinstance(item, str) or not item or len(item) > 512 for item in unknowns):
        raise _fail("OFFICE_MAPPING_INVALID", "effect", "Expected Effect 未知项无效。")

    clean_scopes: list[dict[str, str]] = []
    for scope in scopes:
        if not isinstance(scope, dict) or not isinstance(scope.get("kind"), str):
            raise _fail("OFFICE_MAPPING_INVALID", "effect", "Expected Effect 目标描述无效。")
        kind = scope["kind"]
        if kind == "workbook_structure" and set(scope) == {"kind"}:
            clean_scopes.append({"kind": kind})
            continue
        if kind == "worksheet_structure" and set(scope) == {"kind", "sheet"}:
            if not isinstance(scope["sheet"], str) or not scope["sheet"] or len(scope["sheet"]) > 255:
                raise _fail("OFFICE_MAPPING_INVALID", "effect", "Worksheet 目标无效。")
            clean_scopes.append({"kind": kind, "sheet": scope["sheet"]})
            continue
        if kind == "cell" and set(scope) == {"kind", "sheet", "address"}:
            if not isinstance(scope["sheet"], str) or not scope["sheet"] or len(scope["sheet"]) > 255 or not isinstance(scope["address"], str) or not _A1.fullmatch(scope["address"]):
                raise _fail("OFFICE_MAPPING_INVALID", "effect", "单元格目标无效。")
            clean_scopes.append({"kind": kind, "sheet": scope["sheet"], "address": scope["address"]})
            continue
        if kind == "range" and set(scope) == {"kind", "sheet", "start", "end"}:
            if not isinstance(scope["sheet"], str) or not scope["sheet"] or len(scope["sheet"]) > 255 or not all(isinstance(scope[x], str) and _A1.fullmatch(scope[x]) for x in ("start", "end")):
                raise _fail("OFFICE_MAPPING_INVALID", "effect", "单元格区域目标无效。")
            start, end = scope["start"], scope["end"]
            width = _col_number(re.match(r"[A-Z]+", end).group()) - _col_number(re.match(r"[A-Z]+", start).group()) + 1
            height = int(re.search(r"[0-9]+$", end).group()) - int(re.search(r"[0-9]+$", start).group()) + 1
            if width <= 0 or height <= 0 or width * height > budget.max_cells:
                raise _fail("OFFICE_RESOURCE_LIMIT", "effect", "Expected Effect 单元格区域超过限制或反向定义。")
            clean_scopes.append({"kind": kind, "sheet": scope["sheet"], "start": start, "end": end})
            continue
        raise _fail("OFFICE_MAPPING_INVALID", "effect", "Expected Effect 使用了不支持的目标结构。")

    clean_assertions: list[dict[str, object]] = []
    assertion_targets: set[tuple[str, str]] = set()
    for assertion in assertions:
        if not isinstance(assertion, dict) or set(assertion) != {"kind", "sheet", "address", "value_type", "value"}:
            raise _fail("OFFICE_MAPPING_INVALID", "effect", "Expected Effect 断言包含缺失或额外字段。")
        if assertion["kind"] != "cell_value" or not isinstance(assertion["sheet"], str) or not assertion["sheet"] or not isinstance(assertion["address"], str) or not _A1.fullmatch(assertion["address"]):
            raise _fail("OFFICE_MAPPING_INVALID", "effect", "Expected Effect 仅支持受限的单元格值断言。")
        key = (assertion["sheet"], assertion["address"])
        if key in assertion_targets:
            raise _fail("OFFICE_MAPPING_INVALID", "effect", "Expected Effect 断言目标重复。")
        assertion_targets.add(key)
        if not any(_scope_contains(scope, f"xlsx:{key[0]}!{key[1]}", "cell_value") for scope in clean_scopes):
            raise _fail("OFFICE_MAPPING_INVALID", "effect", "Expected Effect 断言不在声明的目标范围内。")
        kind, value = assertion["value_type"], assertion["value"]
        valid = (
            (kind == "string" and isinstance(value, str))
            or (kind == "number" and type(value) in {int, float} and math.isfinite(float(value)))
            or (kind == "boolean" and isinstance(value, bool))
            or (kind == "blank" and value is None)
            or (kind in {"date", "datetime"} and isinstance(value, str))
        )
        if not valid:
            raise _fail("OFFICE_MAPPING_INVALID", "effect", "Expected Effect 的值类型不受支持或与值不匹配。")
        clean_assertions.append(dict(assertion))

    payload = {
        "schema_version": "1",
        "parent_version_id": parent_id,
        "input_sha256": source_sha,
        "target_scopes": clean_scopes,
        "allowed_change_kinds": list(allowed),
        "expected_assertions": clean_assertions,
        "unknowns": list(unknowns),
    }
    try:
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise _fail("OFFICE_MAPPING_INVALID", "effect", "Expected Effect 不是规范 JSON。") from exc
    if len(canonical) > budget.max_expected_effect_bytes:
        raise _fail("OFFICE_RESOURCE_LIMIT", "effect", "Expected Effect 超过独立元数据序列化预算。")
    digest = hashlib.sha256(canonical).hexdigest()
    if not isinstance(effect.get("effect_digest"), str) or not _SHA256.fullmatch(effect["effect_digest"]) or effect["effect_digest"] != digest:
        raise _fail("OFFICE_MAPPING_INVALID", "effect", "Expected Effect 指纹无效。")
    return payload, digest


def _scope_contains(scope: dict[str, str], target: str, change_kind: str) -> bool:
    if target == "xlsx:__workbook__!structure":
        return scope.get("kind") == "workbook_structure" and change_kind == "workbook_structure"
    match = re.fullmatch(r"xlsx:(.+)!([A-Z]{1,3}[1-9][0-9]*|__structure__)", target)
    if not match:
        return False
    sheet, address = match.groups()
    if address == "__structure__":
        return scope.get("kind") in {"workbook_structure", "worksheet_structure"} and (
            scope.get("kind") == "workbook_structure" or scope.get("sheet") == sheet
        ) and change_kind == "worksheet_structure"
    if scope.get("kind") == "workbook_structure":
        return False
    if scope.get("sheet") != sheet:
        return False
    if scope.get("kind") == "cell":
        return scope.get("address") == address
    if scope.get("kind") == "range":
        return _coordinate_in_range(address, scope["start"], scope["end"])
    return False


def _candidate_typed_value(value: tuple[str, object] | None) -> dict[str, object]:
    if value is None:
        return {"type": "blank", "value": None}
    kind, raw = value
    if kind == "formula":
        expression, attributes = raw
        return {"type": "formula", "value": expression, "attributes": dict(attributes)}
    if kind in {"date", "datetime"} and isinstance(raw, (date, datetime)):
        return {"type": kind, "value": raw.isoformat()}
    if kind == "number" and isinstance(raw, Decimal):
        return {"type": "number", "value": str(raw)}
    return {"type": kind, "value": raw}


def _candidate_expected_matches(assertion: dict[str, object], state: dict[str, object]) -> bool:
    key = f"xlsx:{assertion['sheet']}!{assertion['address']}"
    cells = state["cells"]
    actual = cells.get(key)
    kind = str(assertion["value_type"])
    expected = assertion["value"]
    if kind == "blank":
        return actual is None or actual[0] == "blank"
    if actual is None:
        return False
    actual_kind, actual_value = actual
    if kind in {"date", "datetime"}:
        try:
            parsed_expected = date.fromisoformat(expected) if kind == "date" else datetime.fromisoformat(expected.replace("Z", "+00:00"))
        except (AttributeError, TypeError, ValueError):
            return False
        if actual_kind == kind:
            return actual_value == parsed_expected
        if actual_kind != "number":
            return False
        number_format = state["number_formats"].get(key, "General")
        if not _number_format_has_date_semantics(number_format):
            return False
        try:
            expected_serial = _excel_date_serial(kind, expected, bool(state["date_1904"]))
            if kind == "date" and actual_value != actual_value.to_integral_value():
                return False
            return abs(actual_value - expected_serial) <= Decimal("0.0000000001")
        except (InvalidOperation, TypeError, ValueError):
            return False
    if kind == "number":
        try:
            return actual_kind == "number" and not isinstance(expected, bool) and actual_value == Decimal(str(expected))
        except InvalidOperation:
            return False
    return actual_kind == kind and actual_value is expected if kind == "boolean" else actual_kind == kind and actual_value == expected


def _number_format_has_date_semantics(number_format: str) -> bool:
    """Distinguish Excel date serials from ordinary numbers using the cell format."""
    if number_format.startswith("builtin_date:"):
        return True
    cleaned = re.sub(r'"[^\"]*"|\\.|_.|\*.', "", number_format.lower())
    cleaned = re.sub(r"\[[^\]]*\]", "", cleaned)
    has_calendar_component = bool(re.search(r"[yd]", cleaned))
    has_month_component = "m" in cleaned
    has_clock_component = bool(re.search(r"[hs]", cleaned)) or "am/pm" in cleaned or "a/p" in cleaned
    return has_calendar_component or (has_month_component and not has_clock_component)


def verify_candidate_inline(
    source_bytes: bytes,
    candidate_bytes: bytes,
    filename: str,
    mime_type: str,
    expected_effect: object,
    policy: VerificationPolicy,
    budget: VerificationBudget,
) -> CandidateValidationReport:
    """Compare XLSX bytes against a bounded, read-only Expected Effect contract."""
    if not isinstance(policy, VerificationPolicy) or not isinstance(budget, VerificationBudget):
        raise _fail("OFFICE_INVALID_OR_MISMATCHED", "input", "验证策略或资源预算类型无效。")
    policy.validate()
    budget.validate()
    if not isinstance(source_bytes, bytes) or not isinstance(candidate_bytes, bytes):
        raise _fail("OFFICE_INVALID_OR_MISMATCHED", "input", "源文件和候选文件必须以字节传入。")
    if len(source_bytes) > budget.max_file_size or len(candidate_bytes) > budget.max_file_size:
        raise _fail("OFFICE_RESOURCE_LIMIT", "input", "文件超过输入大小限制。")
    source_sha = hashlib.sha256(source_bytes).hexdigest()
    output_sha = hashlib.sha256(candidate_bytes).hexdigest()
    raw_parent = expected_effect.get("parent_version_id") if isinstance(expected_effect, dict) else 0
    parent_id = raw_parent if type(raw_parent) is int else 0
    raw_digest = expected_effect.get("effect_digest", "") if isinstance(expected_effect, dict) else ""
    digest = raw_digest if isinstance(raw_digest, str) else ""
    effect, digest = _canonical_effect(expected_effect, source_sha, budget)
    if parent_id != effect["parent_version_id"]:
        raise _fail("OFFICE_MAPPING_INVALID", "effect", "Expected Effect 父版本无效。")
    if not filename.lower().endswith(".xlsx") or mime_type.lower().split(";", 1)[0].strip() not in {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/octet-stream"
    }:
        raise _fail("OFFICE_UNSUPPORTED_FEATURE", "format", "Candidate Validator 仅支持 XLSX。")
    source = read_package(source_bytes, filename, mime_type, budget)
    output = read_package(candidate_bytes, filename, mime_type, budget)
    if source.kind != "xlsx" or output.kind != "xlsx":
        raise _fail("OFFICE_UNSUPPORTED_FEATURE", "format", "Candidate Validator 仅支持 XLSX。")
    reject_unsupported_nodes(source)
    reject_unsupported_nodes(output)
    source_state = _xlsx_state(source, budget, policy)
    output_state = _xlsx_state(output, budget, policy)
    changes: list[dict[str, object]] = []
    risks: list[dict[str, object]] = []
    valid = True

    source_cells = source_state["cells"]
    output_cells = output_state["cells"]
    for target in sorted(set(source_cells) | set(output_cells)):
        before = source_cells.get(target)
        after = output_cells.get(target)
        if before == after:
            continue
        change_kind = "formula_text" if (before and before[0] == "formula") or (after and after[0] == "formula") else "cell_value"
        entry = {"target": target, "change_kind": change_kind, "before": _candidate_typed_value(before), "after": _candidate_typed_value(after)}
        changes.append(entry)
        if before and before[0] != "blank" and before[1] not in (None, ""):
            risks.append({"kind": "existing_value_replaced", "target": target, "before": _candidate_typed_value(before), "after": _candidate_typed_value(after)})
            if before[0] == "formula":
                risks.append({"kind": "existing_formula_replaced", "target": target})
        if change_kind not in effect["allowed_change_kinds"] or not any(_scope_contains(scope, target, change_kind) for scope in effect["target_scopes"]):
            valid = False

    for target in sorted(set(source_state["caches"]) | set(output_state["caches"])):
        before, after = source_state["caches"].get(target), output_state["caches"].get(target)
        if before != after:
            changes.append({"target": target, "change_kind": "formula_cache", "before": before, "after": after})
            risks.append({"kind": "formula_cache_changed", "target": target})
            valid = False

    source_style_keys = set(source_state["style_bases"]) | set(source_state["number_formats"])
    output_style_keys = set(output_state["style_bases"]) | set(output_state["number_formats"])
    default_style_signature = repr(
        _semantic_xml_signature(etree.Element(NS_X + "xf"))
    ).encode("utf-8")
    for target in sorted(source_style_keys | output_style_keys):
        before_style = (
            source_state["style_bases"].get(target, default_style_signature),
            source_state["number_formats"].get(target, "General"),
        )
        after_style = (
            output_state["style_bases"].get(target, default_style_signature),
            output_state["number_formats"].get(target, "General"),
        )
        if before_style == after_style:
            continue
        entry = {
            "target": target, "change_kind": "cell_style",
            "before": {"style": before_style[0].hex() if before_style[0] else None, "number_format": before_style[1]},
            "after": {"style": after_style[0].hex() if after_style[0] else None, "number_format": after_style[1]},
        }
        changes.append(entry)
        if "cell_style" not in effect["allowed_change_kinds"] or not any(_scope_contains(scope, target, "cell_style") for scope in effect["target_scopes"]):
            valid = False

    if source_state["sheets"] != output_state["sheets"]:
        changes.append({"target": "xlsx:__workbook__!structure", "change_kind": "workbook_structure", "before": list(source_state["sheets"]), "after": list(output_state["sheets"])})
    if source_state["sheet_states"] != output_state["sheet_states"]:
        for sheet in sorted(set(source_state["sheets"]) | set(output_state["sheets"])):
            before_state = next((state for name, state in source_state["sheet_states"] if name == sheet), None)
            after_state = next((state for name, state in output_state["sheet_states"] if name == sheet), None)
            if before_state != after_state:
                changes.append({"target": f"xlsx:{sheet}!__structure__", "change_kind": "worksheet_structure", "before": before_state, "after": after_state})
    for field in ("merges", "worksheet_structures", "row_structures"):
        before_values = source_state[field]
        after_values = output_state[field]
        for sheet in sorted(set(before_values) | set(after_values)):
            before = before_values.get(sheet)
            after = after_values.get(sheet)
            if before == after:
                continue
            if field == "worksheet_structures":
                before = [item.hex() for item in before or ()]
                after = [item.hex() for item in after or ()]
            elif field == "cell_structures":
                before = [[list(attrs), list(children)] for attrs, children in (before or (((), ()),))]
                after = [[list(attrs), list(children)] for attrs, children in (after or (((), ()),))]
            elif field == "row_structures":
                before = [[row, [list(pair) for pair in attrs]] for row, attrs in before or ()]
                after = [[row, [list(pair) for pair in attrs]] for row, attrs in after or ()]
            else:
                before, after = list(before or ()), list(after or ())
            changes.append({"target": f"xlsx:{sheet}!__structure__", "change_kind": "worksheet_structure", "before": before, "after": after})

    for target in sorted(set(source_state["cell_structures"]) | set(output_state["cell_structures"])):
        before = source_state["cell_structures"].get(target, ((), ()))
        after = output_state["cell_structures"].get(target, ((), ()))
        if before != after:
            changes.append({
                "target": target, "change_kind": "worksheet_structure",
                "before": [list(before[0]), list(before[1])],
                "after": [list(after[0]), list(after[1])],
            })

    source_parts = source_state["sheet_parts"]
    output_parts = output_state["sheet_parts"]
    for sheet in sorted(set(source_parts) & set(output_parts)):
        if source_parts[sheet] != output_parts[sheet]:
            changes.append({"target": f"xlsx:{sheet}!__structure__", "change_kind": "worksheet_structure", "before": source_parts[sheet], "after": output_parts[sheet]})
    if source_state["workbook_structures"] != output_state["workbook_structures"]:
        changes.append({"target": "xlsx:__workbook__!structure", "change_kind": "workbook_structure", "before": [item.hex() for item in source_state["workbook_structures"]], "after": [item.hex() for item in output_state["workbook_structures"]]})

    def known_candidate_part(name: str) -> bool:
        return name in {
            "[Content_Types].xml", "xl/workbook.xml", "xl/_rels/workbook.xml.rels",
            "xl/styles.xml", "xl/sharedStrings.xml", "xl/calcChain.xml", "docProps/core.xml",
        } or bool(re.fullmatch(r"xl/worksheets/sheet[0-9]+\.xml", name))

    source_names, output_names = set(source.entries), set(output.entries)
    sheet_part_pattern = re.compile(r"xl/worksheets/sheet[0-9]+\.xml$")
    source_sheet_names = {name for name in source_names if sheet_part_pattern.fullmatch(name)}
    output_sheet_names = {name for name in output_names if sheet_part_pattern.fullmatch(name)}
    referenced_source_parts = set(source_parts.values())
    referenced_output_parts = set(output_parts.values())
    if (source_sheet_names ^ output_sheet_names) != (referenced_source_parts ^ referenced_output_parts):
        changes.append({"target": "xlsx:__package__!worksheet_parts", "change_kind": "unsupported_structure", "before": sorted(source_sheet_names), "after": sorted(output_sheet_names)})
    source_core = _core_properties_signature(source)
    output_core = _core_properties_signature(output)
    if source_core != output_core:
        changes.append({
            "target": "xlsx:__package__!docProps/core.xml",
            "change_kind": "unsupported_structure",
            "before": source_core,
            "after": output_core,
        })
    for name in sorted(source_names | output_names):
        before_part, after_part = source.raw_parts.get(name), output.raw_parts.get(name)
        if before_part == after_part or known_candidate_part(name):
            continue
        changes.append({
            "target": f"xlsx:__package__!{name}", "change_kind": "unsupported_structure",
            "before": hashlib.sha256(before_part).hexdigest() if before_part is not None else None,
            "after": hashlib.sha256(after_part).hexdigest() if after_part is not None else None,
        })
    if source_state["workbook_attributes"] != output_state["workbook_attributes"] or source_state["workbook_properties"] != output_state["workbook_properties"]:
        changes.append({
            "target": "xlsx:__workbook__!structure", "change_kind": "workbook_structure",
            "before": {"attributes": list(source_state["workbook_attributes"]), "properties": list(source_state["workbook_properties"])},
            "after": {"attributes": list(output_state["workbook_attributes"]), "properties": list(output_state["workbook_properties"])},
        })
    if source_state["content_types"] != output_state["content_types"] and source_state["sheets"] == output_state["sheets"]:
        changes.append({"target": "xlsx:__package__!content_types", "change_kind": "unsupported_structure", "before": list(source_state["content_types"]), "after": list(output_state["content_types"])})
    non_sheet_part_changes = (source_names ^ output_names) - source_sheet_names - output_sheet_names
    for name in sorted(non_sheet_part_changes):
        changes.append({"target": f"xlsx:__package__!{name}", "change_kind": "unsupported_structure", "before": name in source_names, "after": name in output_names})

    failures: list[dict[str, str]] = []
    for entry in changes:
        kind = entry["change_kind"]
        if kind not in effect["allowed_change_kinds"] or not any(_scope_contains(scope, entry["target"], kind) for scope in effect["target_scopes"]):
            valid = False
            if kind == "unsupported_structure":
                error_code, failed_stage, rule = "OFFICE_UNSUPPORTED_FEATURE", "unsupported_structure", "unapproved OOXML package change"
            elif kind in {"workbook_structure", "worksheet_structure", "formula_cache"}:
                error_code, failed_stage, rule = "OFFICE_STRUCTURE_MISMATCH", "structure", "unapproved workbook structure or formula-cache change"
            else:
                error_code, failed_stage, rule = "OFFICE_TARGET_MISMATCH", "expected_effect", "change is outside the authorized Expected Effect"
            actual_change = json.dumps(entry, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
            failures.append({
                "error_code": error_code,
                "failed_stage": failed_stage,
                "message": f"target={entry['target']}; rule={rule}; actual_change={actual_change[:600]}",
            })

    for assertion in effect["expected_assertions"]:
        if _candidate_expected_matches(assertion, output_state):
            continue
        valid = False
        target = f"xlsx:{assertion.get('sheet', '')}!{assertion.get('address', '')}"
        actual = output_cells.get(target)
        failures.append({
            "error_code": "OFFICE_TARGET_MISMATCH",
            "failed_stage": "expected_effect",
            "message": (
                f"target={target}; rule=expected assertion did not match; "
                f"expected={json.dumps(assertion, ensure_ascii=False, sort_keys=True, default=str)[:300]}; "
                f"actual={json.dumps(_candidate_typed_value(actual), ensure_ascii=False, sort_keys=True, default=str)[:300]}"
            ),
        })
    if not valid:
        result = "FAILED"
    elif effect["unknowns"] or not effect["expected_assertions"]:
        result = "PARTIALLY_VERIFIED"
    else:
        result = "VERIFIED"
    features = (
        {"feature": "cell_values_and_types", "capability": "SUPPORTED", "checked": True},
        {"feature": "regular_formula_text", "capability": "SUPPORTED", "checked": True, "calculation": "NOT_CHECKED"},
        {"feature": "formula_cached_values", "capability": "PARTIALLY_SUPPORTED", "checked": True, "calculation": "NOT_CHECKED"},
        {"feature": "common_cell_styles", "capability": "SUPPORTED", "checked": True},
        {"feature": "basic_worksheet_structure", "capability": "SUPPORTED", "checked": True},
    )
    return CandidateValidationReport(
        validation_result=result,
        input_sha256=source_sha,
        output_sha256=output_sha,
        parent_version_id=effect["parent_version_id"],
        effect_digest=digest,
        actual_effects=tuple(changes),
        risk_facts=tuple(risks),
        feature_results=features,
        unknowns=tuple(effect["unknowns"]),
        error=failures[0] if failures else None,
    )


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
