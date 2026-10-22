"""Format-specific inspection and candidate rendering in a constrained worker."""

from __future__ import annotations

import hashlib
import math
import re
import warnings
import zipfile
from copy import deepcopy
from io import BytesIO

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from lxml import etree
from openpyxl import load_workbook
from openpyxl.cell.cell import MergedCell

from .errors import OfficeCoreError
from .models import DocumentInspection, Element, RenderCandidate, ResourceBudget
from .security import Package, _safe_xlsx_extension_list, inspect_package, reject_unsupported_ooxml_nodes


def _parser_warning_gate(caught: list[warnings.WarningMessage], stage: str) -> tuple[str, ...]:
    messages = tuple(str(item.message) for item in caught)
    for item in caught:
        message = str(item.message).lower()
        if "extension" in message or "unsupported" in message or "removed" in message or "dropped" in message:
            raise OfficeCoreError("OFFICE_UNSUPPORTED_FEATURE", stage, "解析器报告文件包含无法保证保留的结构，已拒绝处理。")
        # No warning is silently suppressed. A warning not explicitly allowlisted
        # is treated as a structure-integrity risk.
        raise OfficeCoreError("OFFICE_UNSUPPORTED_FEATURE", stage, "解析器发出未审核的结构或完整性警告，已拒绝处理。")
    return messages


def _qname(node: etree._Element) -> str:
    if not isinstance(node.tag, str):
        return ""
    return etree.QName(node).localname


def _xlsx_inspection(data: bytes, package: Package, budget: ResourceBudget) -> DocumentInspection:
    reject_unsupported_ooxml_nodes(package)
    caught: list[warnings.WarningMessage] = []
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            workbook = load_workbook(BytesIO(data), data_only=False, keep_links=False, read_only=False)
            warning_text = _parser_warning_gate(caught, "xlsx_parse")
    except OfficeCoreError:
        raise
    except Exception as exc:
        raise OfficeCoreError("OFFICE_INVALID_OR_MISMATCHED", "xlsx_parse", "Excel 工作簿无法安全解析。") from exc
    elements: list[Element] = []
    order = 0
    total_cells = 0
    for sheet in workbook.worksheets:
        if sheet.max_row * sheet.max_column > budget.max_cells:
            raise OfficeCoreError("OFFICE_RESOURCE_LIMIT", "xlsx_structure", "工作表单元格范围超过限制。")
        for row in sheet.iter_rows():
            total_cells += len(row)
            if total_cells > budget.max_cells:
                raise OfficeCoreError("OFFICE_RESOURCE_LIMIT", "xlsx_structure", "工作簿单元格数量超过限制。")
            populated_columns = [cell.column for cell in row if cell.value is not None]
            target_columns = {cell.column for cell in row if cell.has_style and not isinstance(cell, MergedCell)}
            if populated_columns:
                # Empty input cells between labelled/formula cells in the same
                # row are valid explicit Mapping Plan targets. Leading/trailing
                # blank worksheet space is not exposed as writable structure.
                target_columns.update(range(min(populated_columns), max(populated_columns) + 1))
            for cell in row:
                if cell.column not in target_columns or isinstance(cell, MergedCell):
                    continue
                order += 1
                if cell.value is None:
                    elements.append(
                        Element(
                            f"xlsx:{sheet.title}!{cell.coordinate}",
                            "cell",
                            None,
                            True,
                            order,
                        )
                    )
                    continue
                is_formula = isinstance(cell.value, str) and cell.value.startswith("=")
                value = {"formula": cell.value} if is_formula else cell.value
                elements.append(
                    Element(
                        f"xlsx:{sheet.title}!{cell.coordinate}",
                        "formula" if is_formula else "cell",
                        value,
                        not is_formula,
                        order,
                    )
                )
    workbook.close()
    return DocumentInspection(
        "xlsx",
        hashlib.sha256(data).hexdigest(),
        tuple(elements),
        (),
        warning_text,
        "xlsx_basic_cells_candidate; formula_cells_read_only; advanced_parts_rejected",
    )


def _paragraph_text(paragraph: Paragraph) -> tuple[str, bool]:
    p = paragraph._p
    simple_paragraph = True
    for child in p:
        name = _qname(child)
        if name == "pPr":
            continue
        if name != "r":
            simple_paragraph = False
            continue
        for run_child in child:
            if _qname(run_child) not in {"rPr", "t"}:
                simple_paragraph = False
    runs = list(paragraph.runs)
    text = "".join(node.text or "" for node in p.iter() if node.tag == "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t")
    writable = (
        simple_paragraph
        and len(runs) == 1
        and bool(runs[0]._r.findall("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"))
    )
    return text, writable


def _docx_inspection(data: bytes, package: Package, budget: ResourceBudget) -> DocumentInspection:
    reject_unsupported_ooxml_nodes(package)
    try:
        document = Document(BytesIO(data))
    except Exception as exc:
        raise OfficeCoreError("OFFICE_INVALID_OR_MISMATCHED", "docx_parse", "Word 文档无法安全解析。") from exc
    elements: list[Element] = []
    order = 0
    paragraph_index = 0
    table_index = 0

    def add_paragraph(paragraph: Paragraph, element_id: str) -> None:
        nonlocal order
        value, writable = _paragraph_text(paragraph)
        if not value:
            return
        order += 1
        elements.append(Element(element_id, "paragraph", value, writable, order))

    for body_item in document.element.body.iterchildren():
        name = _qname(body_item)
        if name == "p":
            paragraph_index += 1
            add_paragraph(Paragraph(body_item, document), f"docx:p:{paragraph_index}")
        elif name == "tbl":
            table_index += 1
            table = Table(body_item, document)
            for row_index, row in enumerate(table.rows, 1):
                if len(row.cells) > budget.max_paragraphs:
                    raise OfficeCoreError("OFFICE_RESOURCE_LIMIT", "docx_structure", "Word 表格单元格数量超过限制。")
                for cell_index, cell in enumerate(row.cells, 1):
                    if any(_qname(child) == "tbl" for child in cell._tc.iterchildren()):
                        raise OfficeCoreError("OFFICE_UNSUPPORTED_FEATURE", "docx_structure", "Word 包含嵌套表格，当前未启用该结构。")
                    for cell_para_index, paragraph in enumerate(cell.paragraphs, 1):
                        paragraph_index += 1
                        add_paragraph(
                            paragraph,
                            f"docx:table:{table_index}:row:{row_index}:cell:{cell_index}:p:{cell_para_index}",
                        )
        elif name in {"sectPr"}:
            continue
        else:
            raise OfficeCoreError("OFFICE_UNSUPPORTED_FEATURE", "docx_structure", "Word 正文包含当前未启用的结构。")
        if paragraph_index > budget.max_paragraphs:
            raise OfficeCoreError("OFFICE_RESOURCE_LIMIT", "docx_structure", "Word 段落数量超过限制。")
    return DocumentInspection(
        "docx",
        hashlib.sha256(data).hexdigest(),
        tuple(elements),
        (),
        (),
        "docx_text_inspection; standard_png_jpeg_images_headers_footers_and_safe_fields_preserved; active_or_unknown_objects_rejected",
    )


def inspect_inline(data: bytes, filename: str, mime_type: str, budget: ResourceBudget) -> DocumentInspection:
    package = inspect_package(data, filename, mime_type, budget)
    if package.kind == "xlsx":
        return _xlsx_inspection(data, package, budget)
    if package.kind == "docx":
        return _docx_inspection(data, package, budget)
    raise OfficeCoreError("OFFICE_UNSUPPORTED_FEATURE", "format", "该 Office 格式当前未启用。")


def _mapping_error(message: str) -> OfficeCoreError:
    return OfficeCoreError("OFFICE_MAPPING_INVALID", "mapping", message)


def _has_exact_keys(value: dict, expected: set[str]) -> bool:
    return all(isinstance(key, str) for key in value) and set(value) == expected


def _validate_mapping(mapping: object, inspection: DocumentInspection) -> list[tuple[Element, dict[str, object]]]:
    if not isinstance(mapping, dict) or not _has_exact_keys(mapping, {"schema_version", "template_sha256", "writes"}):
        raise _mapping_error("映射结构包含缺失或未知字段。")
    if mapping.get("schema_version") != "1":
        raise _mapping_error("映射版本不受支持。")
    if mapping.get("template_sha256") != inspection.template_sha256:
        raise _mapping_error("映射对应的模板指纹不匹配。")
    writes = mapping.get("writes")
    if not isinstance(writes, list):
        raise _mapping_error("writes 必须是数组。")
    known = {element.element_id: element for element in inspection.elements}
    seen: set[str] = set()
    validated: list[tuple[Element, dict[str, object]]] = []
    for write in writes:
        if not isinstance(write, dict) or not _has_exact_keys(write, {"element_id", "operation", "value"}):
            raise _mapping_error("写入项包含缺失或未知字段。")
        element_id = write.get("element_id")
        if not isinstance(element_id, str) or element_id not in known:
            raise _mapping_error("写入目标不存在或不在当前结构目录中。")
        if element_id in seen:
            raise _mapping_error("写入目标重复。")
        seen.add(element_id)
        if write.get("operation") != "set_value":
            raise _mapping_error("只允许 set_value 操作。")
        if not known[element_id].writable:
            raise _mapping_error("写入目标为公式或当前不可写结构。")
        value = write.get("value")
        if not isinstance(value, dict) or not _has_exact_keys(value, {"type", "data"}):
            raise _mapping_error("value 必须同时包含 type 与 data，且不能显式为 null。")
        kind, data = value.get("type"), value.get("data")
        if data is None:
            raise _mapping_error("显式 null 不受支持。")
        if kind == "string":
            if not isinstance(data, str):
                raise _mapping_error("string 类型的 data 必须是字符串。")
            if known[element_id].kind == "cell" or known[element_id].kind == "paragraph":
                pass
        elif kind == "number":
            if known[element_id].kind != "cell" or isinstance(data, bool) or not isinstance(data, (int, float)):
                raise _mapping_error("number 类型只适用于 Excel 单元格，且必须是数字。")
            if isinstance(data, float) and not math.isfinite(data):
                raise _mapping_error("number 不允许 NaN 或无穷值。")
        elif kind == "boolean":
            if known[element_id].kind != "cell" or not isinstance(data, bool):
                raise _mapping_error("boolean 类型只适用于 Excel 单元格。")
        else:
            raise _mapping_error("值类型不受支持。")
        validated.append((known[element_id], {"type": kind, "data": data}))
    return validated


def _render_xlsx(data: bytes, filename: str, mime_type: str, mapping: object, budget: ResourceBudget) -> RenderCandidate:
    inspection = inspect_inline(data, filename, mime_type, budget)
    writes = _validate_mapping(mapping, inspection)
    try:
        workbook = load_workbook(BytesIO(data), data_only=False, keep_links=False, read_only=False)
        # Formula cells are read-only mapping targets, but their presence does
        # not prevent edits to other cells. openpyxl preserves formula text but
        # does not calculate cached results; office_verify independently checks
        # formula expressions and reports cache changes to the caller.
        for element, value in writes:
            _, location = element.element_id.split(":", 1)
            sheet_name, coordinate = location.rsplit("!", 1)
            cell = workbook[sheet_name][coordinate]
            if isinstance(cell, MergedCell):
                raise _mapping_error("合并单元格非锚点不可写。")
            cell.value = value["data"]
        out = BytesIO()
        caught: list[warnings.WarningMessage] = []
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            workbook.save(out)
            warning_text = _parser_warning_gate(caught, "xlsx_serialize")
        workbook.close()
        candidate = _restore_safe_xlsx_extensions(data, out.getvalue())
    except OfficeCoreError:
        raise
    except Exception as exc:
        raise OfficeCoreError("OFFICE_ENGINE_FAILED", "xlsx_render", "Excel 候选文件生成失败。") from exc
    if len(candidate) > budget.max_file_size:
        raise OfficeCoreError("OFFICE_RESOURCE_LIMIT", "xlsx_render", "生成的候选文件超过大小限制。")
    # Validate the candidate container but do not claim this is the independent
    # office_verify contract introduced in CC-002.
    inspect_package(candidate, filename, mime_type, budget)
    return RenderCandidate("xlsx", inspection.template_sha256, hashlib.sha256(candidate).hexdigest(), candidate, len(writes), warning_text)


def _restore_safe_xlsx_extensions(source: bytes, candidate: bytes) -> bytes:
    """Restore whitelisted passive extLst blocks that openpyxl does not model."""
    source_zip = zipfile.ZipFile(BytesIO(source), "r")
    candidate_zip = zipfile.ZipFile(BytesIO(candidate), "r")
    replacements: dict[str, bytes] = {}
    for part_name in ("xl/workbook.xml", "xl/styles.xml"):
        if part_name not in source_zip.namelist() or part_name not in candidate_zip.namelist():
            continue
        try:
            original_root = etree.fromstring(source_zip.read(part_name))
            candidate_root = etree.fromstring(candidate_zip.read(part_name))
        except etree.XMLSyntaxError as exc:
            raise OfficeCoreError("OFFICE_INVALID_OR_MISMATCHED", "xlsx_serialize", "Excel 扩展结构无法安全回读。") from exc
        original_extensions = [node for node in original_root if _qname(node) == "extLst"]
        candidate_extensions = [node for node in candidate_root if _qname(node) == "extLst"]
        if candidate_extensions:
            # The candidate parser does not currently emit extension lists;
            # avoid merging where a writer starts managing them differently.
            continue
        for extension in original_extensions:
            if not _safe_xlsx_extension_list(extension):
                raise OfficeCoreError("OFFICE_UNSUPPORTED_FEATURE", "xlsx_serialize", "Excel 扩展结构不在安全保留白名单中。")
            candidate_root.append(deepcopy(extension))
        if original_extensions:
            replacements[part_name] = etree.tostring(
                candidate_root,
                xml_declaration=True,
                encoding="UTF-8",
                standalone=True,
            )
    source_zip.close()
    candidate_zip.close()
    if not replacements:
        return candidate
    merged = BytesIO()
    with zipfile.ZipFile(BytesIO(candidate), "r") as archive, zipfile.ZipFile(merged, "w", zipfile.ZIP_DEFLATED) as output:
        for info in archive.infolist():
            output.writestr(info, replacements.get(info.filename, archive.read(info.filename)))
    return merged.getvalue()


def _locate_docx_paragraph(document, element_id: str) -> Paragraph:
    if element_id.startswith("docx:p:"):
        wanted = int(element_id.rsplit(":", 1)[1])
        index = 0
        for child in document.element.body.iterchildren():
            if _qname(child) == "p":
                index += 1
                if index == wanted:
                    return Paragraph(child, document)
            elif _qname(child) == "tbl":
                table = Table(child, document)
                for row in table.rows:
                    for cell in row.cells:
                        index += len(cell.paragraphs)
        raise _mapping_error("Word 段落目标不存在。")
    match = re.fullmatch(r"docx:table:(\d+):row:(\d+):cell:(\d+):p:(\d+)", element_id)
    if not match:
        raise _mapping_error("Word 目标标识无效。")
    table_n, row_n, cell_n, paragraph_n = map(int, match.groups())
    tables = document.tables
    try:
        return tables[table_n - 1].rows[row_n - 1].cells[cell_n - 1].paragraphs[paragraph_n - 1]
    except IndexError as exc:
        raise _mapping_error("Word 表格目标不存在。") from exc


def _render_docx(data: bytes, filename: str, mime_type: str, mapping: object, budget: ResourceBudget) -> RenderCandidate:
    inspection = inspect_inline(data, filename, mime_type, budget)
    writes = _validate_mapping(mapping, inspection)
    try:
        document = Document(BytesIO(data))
        for element, value in writes:
            paragraph = _locate_docx_paragraph(document, element.element_id)
            if len(paragraph.runs) != 1:
                raise _mapping_error("仅支持单一文本 run 的 Word 段落写入。")
            paragraph.runs[0].text = value["data"]
        out = BytesIO()
        document.save(out)
        candidate = out.getvalue()
    except OfficeCoreError:
        raise
    except Exception as exc:
        raise OfficeCoreError("OFFICE_ENGINE_FAILED", "docx_render", "Word 候选文件生成失败。") from exc
    if len(candidate) > budget.max_file_size:
        raise OfficeCoreError("OFFICE_RESOURCE_LIMIT", "docx_render", "生成的候选文件超过大小限制。")
    inspect_package(candidate, filename, mime_type, budget)
    return RenderCandidate("docx", inspection.template_sha256, hashlib.sha256(candidate).hexdigest(), candidate, len(writes), ())


def render_inline(data: bytes, filename: str, mime_type: str, mapping: object, budget: ResourceBudget) -> RenderCandidate:
    inspection = inspect_inline(data, filename, mime_type, budget)
    if inspection.format == "xlsx":
        return _render_xlsx(data, filename, mime_type, mapping, budget)
    if inspection.format == "docx":
        return _render_docx(data, filename, mime_type, mapping, budget)
    raise OfficeCoreError("OFFICE_UNSUPPORTED_FEATURE", "format", "该 Office 格式当前未启用。")
