"""Semantic readback checks for the narrowly enabled XLSX/DOCX baseline."""

from __future__ import annotations

import hashlib
import json
import math
import re
from decimal import Decimal, InvalidOperation

from lxml import etree

from .errors import OfficeVerifyError
from .models import VerificationBudget, VerificationPolicy, VerificationReport
from .security import CT_NS, Package, read_package, reject_unsupported_nodes

NS_REL_DOC = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
NS_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
NS_X = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def _fail(code: str, stage: str, message: str) -> OfficeVerifyError:
    return OfficeVerifyError(code, stage, message)


def _name(node: etree._Element) -> str:
    return etree.QName(node).localname if isinstance(node.tag, str) else ""


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
    seen: set[str] = set()
    clean: list[dict[str, object]] = []
    for item in writes:
        if not isinstance(item, dict) or set(item) != {"element_id", "operation", "value"}:
            raise _fail("OFFICE_MAPPING_INVALID", "mapping", "写入项包含缺失或未知字段。")
        element_id = item.get("element_id")
        value = item.get("value")
        if not isinstance(element_id, str) or element_id in seen:
            raise _fail("OFFICE_MAPPING_INVALID", "mapping", "写入目标无效或重复。")
        if len(element_id) > 512:
            raise _fail("OFFICE_RESOURCE_LIMIT", "mapping", "映射目标标识超过大小限制。")
        seen.add(element_id)
        if item.get("operation") != "set_value":
            raise _fail("OFFICE_MAPPING_INVALID", "mapping", "只允许 set_value 操作。")
        if not isinstance(value, dict) or set(value) != {"type", "data"}:
            raise _fail("OFFICE_MAPPING_INVALID", "mapping", "value 必须包含且仅包含 type 与 data。")
        kind, data = value.get("type"), value.get("data")
        if data is None:
            raise _fail("NULL_NOT_SUPPORTED", "mapping", "显式 null 当前不支持。")
        if kind == "string" and isinstance(data, str):
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
        else:
            raise _fail("OFFICE_MAPPING_INVALID", "mapping", "映射值类型与数据不匹配。")
        clean.append({"element_id": element_id, "type": kind, "data": data})
    try:
        serialized_size = len(json.dumps(plan, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8"))
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise _fail("OFFICE_MAPPING_INVALID", "mapping", "映射值不是受支持的 JSON 数据。") from exc
    if serialized_size > budget.max_mapping_bytes:
        raise _fail("OFFICE_RESOURCE_LIMIT", "mapping", "映射计划超过大小限制。")
    return clean


def _compare_packages(source: Package, output: Package, policy: VerificationPolicy) -> list[dict[str, str]]:
    if source.kind != output.kind:
        raise _fail("OFFICE_INVALID_OR_MISMATCHED", "format", "输出格式与输入格式不一致。")
    if source.entries != output.entries:
        raise _fail("OFFICE_STRUCTURE_MISMATCH", "structure", "OOXML 部件集合发生变化。")
    for required in policy.required_parts:
        if required not in source.entries or required not in output.entries:
            raise _fail("OFFICE_STRUCTURE_MISMATCH", "structure", "策略要求保留的 Office 部件缺失。")
    if policy.require_relationships and source.relationships != output.relationships:
        raise _fail("OFFICE_STRUCTURE_MISMATCH", "relationships", "Office 部件关系发生变化。")
    warnings: list[dict[str, str]] = []
    for style_part in ("xl/styles.xml", "word/styles.xml"):
        if style_part in source.raw_parts and source.raw_parts.get(style_part) != output.raw_parts.get(style_part):
            if policy.require_styles:
                raise _fail("OFFICE_STRUCTURE_MISMATCH", "styles", "策略要求保留的样式部件发生变化。")
            warnings.append({"code": "NON_TARGET_STYLE_PART_CHANGED", "element_id": style_part})
    allowed_variable_parts = {
        "docProps/core.xml", "docProps/app.xml", "xl/workbook.xml", "xl/sharedStrings.xml",
        "word/document.xml", "xl/calcChain.xml",
    }
    if source.kind == "xlsx":
        allowed_variable_parts.update(name for name in source.entries if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", name))
    for name in source.entries:
        if name in allowed_variable_parts or name in {"xl/styles.xml", "word/styles.xml"}:
            continue
        if source.raw_parts.get(name) != output.raw_parts.get(name):
            raise _fail("OFFICE_STRUCTURE_MISMATCH", "structure", "非目标 Office 部件发生未分类变化。")
    return warnings


def _workbook_sheets(package: Package) -> list[tuple[str, str]]:
    workbook = package.roots.get("xl/workbook.xml")
    if workbook is None or workbook.tag != NS_X + "workbook":
        raise _fail("OFFICE_INVALID_OR_MISMATCHED", "xlsx", "工作簿主部件缺失。")
    if any(isinstance(node.tag, str) and not node.tag.startswith(NS_X) for node in workbook.iter()):
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


def _xlsx_state(package: Package, budget: VerificationBudget) -> dict[str, object]:
    sheets = _workbook_sheets(package)
    shared = _shared_strings(package)
    cells: dict[str, tuple[str, object]] = {}
    formulas: dict[str, tuple[str, tuple[tuple[str, str], ...]]] = {}
    caches: dict[str, str | None] = {}
    styles: dict[str, str] = {}
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
        for cell in _elements(root, "c"):
            if cell.tag != NS_X + "c" or any(isinstance(node.tag, str) and not node.tag.startswith(NS_X) for node in cell.iter()):
                raise _fail("OFFICE_UNSUPPORTED_FEATURE", "xlsx", "单元格包含外来 XML 结构。")
            address = cell.get("r", "")
            if not re.fullmatch(r"[A-Z]{1,3}[1-9][0-9]*", address) or address in sheet_cells:
                raise _fail("OFFICE_INVALID_OR_MISMATCHED", "xlsx", "工作表单元格坐标无效或重复。")
            sheet_cells[address] = cell
            cell_count += 1
            if cell_count > budget.max_cells:
                raise _fail("OFFICE_RESOURCE_LIMIT", "xlsx", "工作表单元格数量超过限制。")
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
            if "s" in cell.attrib:
                styles[key] = cell.get("s", "")
            if address in merged_nonanchors and kind != "blank":
                raise _fail("OFFICE_STRUCTURE_MISMATCH", "xlsx", "合并单元格非锚点包含值。")
    return {"sheets": sheet_names, "cells": cells, "formulas": formulas, "caches": caches, "styles": styles, "merges": merges}


def _col_number(value: str) -> int:
    number = 0
    for char in value:
        number = number * 26 + ord(char) - 64
    return number


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
) -> tuple[int, int, tuple[dict[str, object], ...], list[dict[str, str]]]:
    before = _xlsx_state(source, budget)
    after = _xlsx_state(output, budget)
    warnings: list[dict[str, str]] = []
    if before["sheets"] != after["sheets"]:
        raise _fail("OFFICE_STRUCTURE_MISMATCH", "xlsx", "工作表名称或顺序发生变化。")
    if before["merges"] != after["merges"]:
        raise _fail("OFFICE_STRUCTURE_MISMATCH", "xlsx", "合并单元格结构发生变化。")
    if before["formulas"] != after["formulas"]:
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
    for write in writes:
        element_id = write["element_id"]
        if not isinstance(element_id, str) or not element_id.startswith("xlsx:"):
            raise _fail("OFFICE_MAPPING_INVALID", "mapping", "映射目标与文件格式不匹配。")
        if element_id in targets:
            raise _fail("OFFICE_MAPPING_INVALID", "mapping", "写入目标重复。")
        if element_id not in before["cells"]:
            raise _fail("OFFICE_MAPPING_INVALID", "mapping", "映射目标不存在于模板结构目录中。")
        if element_id in before["formulas"]:
            raise _fail("OFFICE_MAPPING_INVALID", "mapping", "公式单元格不可写。")
        targets[element_id] = write
    if set(before["cells"]) != set(after["cells"]):
        raise _fail("OFFICE_STRUCTURE_MISMATCH", "xlsx", "非空单元格结构发生变化。")
    for key in before["cells"]:
        if key in targets:
            expected = targets[key]
            actual_kind, actual_value = after["cells"][key]
            if not _matches(expected["type"], expected["data"], actual_kind, actual_value):
                raise _fail("OFFICE_TARGET_MISMATCH", "target", "映射目标的回读值与预期不一致。")
        elif before["cells"][key] != after["cells"][key]:
            raise _fail("OFFICE_STRUCTURE_MISMATCH", "xlsx", "非目标单元格内容发生变化。")
    before_styles, after_styles = before["styles"], after["styles"]
    for key in set(before_styles) | set(after_styles):
        if before_styles.get(key) != after_styles.get(key):
            if policy.require_styles:
                raise _fail("OFFICE_STRUCTURE_MISMATCH", "styles", "策略要求保留的单元格样式发生变化。")
            warnings.append({"code": "NON_TARGET_STYLE_CHANGED", "element_id": key})
    return len(targets), len(before["formulas"]), cache_status, warnings


def _matches(expected_kind: object, expected: object, actual_kind: str, actual: object) -> bool:
    if expected_kind == "string":
        return actual_kind == "string" and actual == expected
    if expected_kind == "boolean":
        return actual_kind == "boolean" and actual is expected
    if expected_kind == "number" and actual_kind == "number":
        try:
            return Decimal(str(expected)) == actual
        except InvalidOperation:
            return False
    return False


def _paragraph_plain_text(paragraph: etree._Element) -> str:
    for child in paragraph:
        if isinstance(child.tag, str) and not child.tag.startswith(NS_W):
            raise _fail("OFFICE_UNSUPPORTED_FEATURE", "docx", "Word 段落包含外来 XML 结构。")
        if _name(child) == "pPr":
            continue
        if _name(child) != "r":
            raise _fail("OFFICE_UNSUPPORTED_FEATURE", "docx", "Word 段落含当前不支持的活动结构。")
        for run_child in child:
            if isinstance(run_child.tag, str) and not run_child.tag.startswith(NS_W):
                raise _fail("OFFICE_UNSUPPORTED_FEATURE", "docx", "Word 文本包含外来 XML 结构。")
            if _name(run_child) not in {"rPr", "t"}:
                raise _fail("OFFICE_UNSUPPORTED_FEATURE", "docx", "Word 文本含当前不支持的控制结构。")
            if _name(run_child) == "t" and len(run_child):
                raise _fail("OFFICE_UNSUPPORTED_FEATURE", "docx", "Word 文本节点含嵌套结构。")
    return "".join(node.text or "" for node in paragraph.iter() if node.tag == NS_W + "t")


def _canonical(node: etree._Element) -> bytes:
    return etree.tostring(node, method="c14n", exclusive=True, with_comments=False)


def _paragraph_format(paragraph: etree._Element) -> tuple[bytes, tuple[bytes, ...]]:
    paragraph_properties = next((child for child in paragraph if _name(child) == "pPr"), None)
    ppr = _canonical(paragraph_properties) if paragraph_properties is not None else b""
    run_styles: list[bytes] = []
    for run in (child for child in paragraph if _name(child) == "r"):
        run_properties = next((child for child in run if _name(child) == "rPr"), None)
        signature = _canonical(run_properties) if run_properties is not None else b""
        if not run_styles or run_styles[-1] != signature:
            run_styles.append(signature)
    return ppr, tuple(run_styles)


def _docx_texts(package: Package, budget: VerificationBudget) -> tuple[dict[str, str], tuple[object, ...], dict[str, object]]:
    root = package.roots.get("word/document.xml")
    if root is None or root.tag != NS_W + "document":
        raise _fail("OFFICE_INVALID_OR_MISMATCHED", "docx", "Word 正文部件缺失。")
    if any(isinstance(node.tag, str) and not node.tag.startswith(NS_W) for node in root.iter()):
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
                if any(_name(node) not in {"trPr", "tc"} for node in row):
                    raise _fail("OFFICE_UNSUPPORTED_FEATURE", "docx", "Word 表格行含当前未启用的结构。")
                formatting[f"docx:table:{table_index}:row:{row_index}:properties"] = tuple(
                    _canonical(node) for node in row if _name(node) == "trPr"
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
) -> VerificationReport:
    if not isinstance(policy, VerificationPolicy) or not isinstance(budget, VerificationBudget):
        raise _fail("OFFICE_INVALID_OR_MISMATCHED", "input", "验证策略或资源预算类型无效。")
    policy.validate()
    budget.validate()
    if not isinstance(source_bytes, bytes) or not isinstance(candidate_bytes, bytes):
        raise _fail("OFFICE_INVALID_OR_MISMATCHED", "input", "源文件和候选文件必须以字节传入。")
    source_sha = hashlib.sha256(source_bytes).hexdigest()
    output_sha = hashlib.sha256(candidate_bytes).hexdigest()
    plan_writes = _validate_plan(mapping_plan, source_sha, budget)
    source = read_package(source_bytes, filename, mime_type, budget)
    output = read_package(candidate_bytes, filename, mime_type, budget)
    if source.kind not in policy.enabled_formats:
        raise _fail("OFFICE_UNSUPPORTED_FEATURE", "format", "该文件格式当前未启用回读能力。")
    reject_unsupported_nodes(source)
    reject_unsupported_nodes(output)
    warnings = _compare_packages(source, output, policy)
    if source.kind == "xlsx":
        count, formulas, formula_cache_status, semantic_warnings = _check_xlsx(source, output, plan_writes, budget, policy)
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
