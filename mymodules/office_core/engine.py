"""Format-specific inspection and candidate rendering in a constrained worker."""

from __future__ import annotations

import hashlib
import math
import posixpath
import re
import tempfile
import warnings
import zipfile
from copy import deepcopy
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from lxml import etree
from openpyxl import load_workbook
from openpyxl.cell.cell import MergedCell
from openpyxl.utils.cell import get_column_letter, range_boundaries

from .errors import OfficeCoreError
from .models import DocumentInspection, Element, RenderCandidate, ResourceBudget
from .row_expansion import expand_repeat_rows
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
        merged_ranges_by_anchor = {
            merged_range.start_cell.coordinate: str(merged_range)
            for merged_range in sheet.merged_cells.ranges
        }
        # Recognize only a bounded, conventional table shape: a row containing
        # at least two text headings followed by a row with data or formatting.
        # The heading range supplies the blank first data-row targets. This
        # keeps headings visible but prevents record values from being mapped
        # into them when a template formats only selected cells in its data row.
        table_roles: dict[tuple[int, int], tuple[str, str | None]] = {}
        for header_row in range(1, sheet.max_row):
            headings = {
                cell.column: str(cell.value).strip()
                for cell in sheet[header_row]
                if isinstance(cell.value, str)
                and cell.value.strip()
                and not cell.value.startswith("=")
                and not isinstance(cell, MergedCell)
            }
            if len(headings) < 2:
                continue
            first_column, last_column = min(headings), max(headings)
            first_data_row = header_row + 1
            first_data_cells = [
                sheet.cell(first_data_row, column)
                for column in range(first_column, last_column + 1)
            ]
            if not any(cell.value is not None or cell.has_style for cell in first_data_cells):
                continue
            for column, heading in headings.items():
                table_roles[(header_row, column)] = ("table_header", heading)
            # Continue through contiguous populated or formatted rows. A
            # completely empty, unformatted row or a formula-owned summary
            # row ends the detected table body. This exposes generic column
            # targets for all existing/expanded records without treating a
            # distant template region as data.
            for data_row in range(first_data_row, sheet.max_row + 1):
                row_cells = [
                    sheet.cell(data_row, column)
                    for column in range(first_column, last_column + 1)
                ]
                if any(
                    isinstance(cell.value, str) and cell.value.startswith("=")
                    for cell in row_cells
                ):
                    break
                if not any(cell.value is not None or cell.has_style for cell in row_cells):
                    break
                for column in range(first_column, last_column + 1):
                    table_roles[(data_row, column)] = ("table_data", headings.get(column))
        for row in sheet.iter_rows():
            total_cells += len(row)
            if total_cells > budget.max_cells:
                raise OfficeCoreError("OFFICE_RESOURCE_LIMIT", "xlsx_structure", "工作簿单元格数量超过限制。")
            populated_columns = [cell.column for cell in row if cell.value is not None]
            target_columns = {cell.column for cell in row if cell.has_style and not isinstance(cell, MergedCell)}
            target_columns.update(
                column
                for (role_row, column), _metadata in table_roles.items()
                if role_row == row[0].row and _metadata[0] == "table_data"
            )
            if populated_columns:
                # Empty input cells between labelled/formula cells in the same
                # row are valid explicit Mapping Plan targets. Leading/trailing
                # blank worksheet space is not exposed as writable structure.
                target_columns.update(range(min(populated_columns), max(populated_columns) + 1))
            for cell in row:
                if cell.column not in target_columns or isinstance(cell, MergedCell):
                    continue
                order += 1
                role, table_header = table_roles.get((cell.row, cell.column), (None, None))
                writable = role != "table_header"
                if cell.value is None:
                    elements.append(
                        Element(
                            f"xlsx:{sheet.title}!{cell.coordinate}",
                            "cell",
                            None,
                            writable,
                            order,
                            merged_ranges_by_anchor.get(cell.coordinate),
                            role,
                            table_header,
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
                        writable,
                        order,
                        merged_ranges_by_anchor.get(cell.coordinate),
                        role,
                        table_header,
                    )
                )
    workbook.close()
    return DocumentInspection(
        "xlsx",
        hashlib.sha256(data).hexdigest(),
        tuple(elements),
        (),
        warning_text,
        "xlsx_basic_cells_candidate; formulas_preserved_unless_explicitly_written; advanced_parts_rejected",
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


def _valid_arithmetic_formula(formula: object) -> bool:
    """Accept arithmetic-only formulas with local cell references and no functions."""
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
    seen: dict[str, set[str]] = {}
    validated: list[tuple[Element, dict[str, object]]] = []
    for write in writes:
        if not isinstance(write, dict) or not _has_exact_keys(write, {"element_id", "operation", "value"}):
            raise _mapping_error("写入项包含缺失或未知字段。")
        element_id = write.get("element_id")
        if not isinstance(element_id, str):
            raise _mapping_error("写入目标不存在或不在当前结构目录中。")
        element = known.get(element_id)
        if element is None:
            # The mapping was already validated against the caller's current
            # manifest. XLSX operations may target an explicitly described
            # blank coordinate outside the conservative inspection catalogue;
            # the operation adapter still checks sheet, bounds and merges.
            match = re.fullmatch(r"xlsx:([^!]{1,31})!([A-Z]{1,3}[1-9][0-9]*)", element_id)
            if not match:
                raise _mapping_error("写入目标格式无效。")
            element = Element(element_id, "cell", None, True, len(validated))
        operation = write.get("operation")
        if operation not in {"set_value", "set_formula", "set_number_format"}:
            raise _mapping_error("只允许 set_value、受限 set_formula 或 set_number_format 操作。")
        prior_operations = seen.setdefault(element_id, set())
        if operation in prior_operations or (
            operation != "set_number_format"
            and prior_operations.intersection({"set_value", "set_formula"})
        ):
            raise _mapping_error("同一目标的值操作冲突或重复。")
        prior_operations.add(operation)
        if not element.writable:
            raise _mapping_error("写入目标为公式或当前不可写结构。")
        value = write.get("value")
        if not isinstance(value, dict) or not _has_exact_keys(value, {"type", "data"}):
            raise _mapping_error("value 必须同时包含 type 与 data。")
        kind, data = value.get("type"), value.get("data")
        if operation == "set_number_format":
            if (
                element.kind not in {"cell", "formula"}
                or kind != "number_format"
                or not isinstance(data, str)
                or not data
                or len(data) > 128
                or any(ord(char) < 32 for char in data)
            ):
                raise _mapping_error("数字格式必须是有效的 Excel 格式字符串。")
            # A format patch changes presentation only; it must not replace
            # the cell's underlying value.
            validated.append((element, {"type": kind, "data": data, "operation": operation}))
            continue
        elif operation == "set_formula":
            if element.kind not in {"cell", "formula"} or kind != "formula" or not _valid_arithmetic_formula(data):
                raise _mapping_error("公式目标或公式内容无效；仅支持本表算术公式。")
        elif data is None:
            if kind != "string":
                raise _mapping_error("只有字符串目标可以将 null 映射为空白。")
            data = ""
        if kind == "string":
            if not isinstance(data, str):
                raise _mapping_error("string 类型的 data 必须是字符串。")
        elif kind == "number":
            if element.kind not in {"cell", "formula"} or isinstance(data, bool) or not isinstance(data, (int, float)):
                raise _mapping_error("number 类型只适用于 Excel 单元格，且必须是数字。")
            if isinstance(data, float) and not math.isfinite(data):
                raise _mapping_error("number 不允许 NaN 或无穷值。")
        elif kind == "boolean":
            if element.kind not in {"cell", "formula"} or not isinstance(data, bool):
                raise _mapping_error("boolean 类型只适用于 Excel 单元格。")
        elif kind == "formula" and operation == "set_formula":
            pass
        else:
            raise _mapping_error("值类型不受支持。")
        validated.append((element, {"type": kind, "data": data, "operation": operation}))
    return validated


def _repeat_rows_handler(source: bytes, operation: dict[str, object], budget: ResourceBudget):
    from office_document_operations.errors import DocumentOperationError

    target = operation["target"]
    parameters = operation["parameters"]
    try:
        result = expand_repeat_rows(
            source,
            {
                "action": "insert_repeat_rows",
                "sheet": target["sheet"],
                "start_row": target["start_row"],
                "record_count": parameters["record_count"],
                "columns": parameters["columns"],
            },
            budget,
        )
    except OfficeCoreError as exc:
        raise DocumentOperationError(exc.code, exc.stage, exc.message, operation["operation_id"]) from exc
    return result.content, {
        "sheet": result.sheet,
        "start_row": result.start_row,
        "record_count": result.record_count,
        "summary_row_before": result.summary_row_before,
        "summary_row_after": result.summary_row_after,
        "inserted_rows": result.inserted_rows,
    }


def _format_target_ids(operations: list[dict[str, object]], budget: ResourceBudget) -> set[str]:
    targets: set[str] = set()
    for operation in operations:
        if operation["type"] != "format":
            continue
        target = operation["target"]
        if "cell" in target:
            coordinates = [target["cell"]]
        elif "range" in target:
            min_col, min_row, max_col, max_row = range_boundaries(target["range"])
            if (max_col - min_col + 1) * (max_row - min_row + 1) > budget.max_cells:
                raise OfficeCoreError("OFFICE_RESOURCE_LIMIT", "operations", "格式目标超过单次处理单元格预算。")
            coordinates = [
                f"{get_column_letter(column)}{row}"
                for row in range(min_row, max_row + 1)
                for column in range(min_col, max_col + 1)
            ]
        else:
            column = target["column_data"]["column"]
            start_row, end_row = target["column_data"]["start_row"], target["column_data"]["end_row"]
            if end_row - start_row + 1 > budget.max_cells:
                raise OfficeCoreError("OFFICE_RESOURCE_LIMIT", "operations", "格式目标超过单次处理单元格预算。")
            coordinates = [f"{column}{row}" for row in range(start_row, end_row + 1)]
        targets.update(f"xlsx:{target['sheet']}!{coordinate}" for coordinate in coordinates)
    return targets


def _numeric_write_pairs(operations: list[dict[str, object]]):
    pairs = []
    for operation in operations:
        if operation["type"] != "set_value":
            continue
        target = operation["target"]
        params = operation["parameters"]
        if "cell" in target:
            values = [[params["value"]]]
            min_col, min_row, _, _ = range_boundaries(f"{target['cell']}:{target['cell']}")
        else:
            values = params["values"]
            min_col, min_row, _, _ = range_boundaries(target["range"])
        for row_offset, row_values in enumerate(values):
            for col_offset, value in enumerate(row_values):
                data = value["data"]
                if value["type"] == "number" and isinstance(data, (int, float)) and not isinstance(data, bool):
                    element_id = f"xlsx:{target['sheet']}!{get_column_letter(min_col + col_offset)}{min_row + row_offset}"
                    pairs.append((SimpleNamespace(element_id=element_id), value))
    return pairs


def _execute_xlsx_operations_inline(
    data: bytes,
    filename: str,
    mime_type: str,
    operation_list: object,
    budget: ResourceBudget,
) -> RenderCandidate:
    from office_document_operations import DocumentOperationEngine, validate_operation_list
    from office_document_operations.errors import DocumentOperationError

    inspection = inspect_inline(data, filename, mime_type, budget)
    try:
        normalized = validate_operation_list(operation_list)
    except DocumentOperationError as exc:
        raise OfficeCoreError(exc.code, exc.stage, exc.message) from exc
    if normalized["schema_version"] != "1.1":
        raise OfficeCoreError("OFFICE_OPERATION_VERSION", "operations", "生产操作必须使用 Document Operation Schema 1.1。")
    if normalized["source_sha256"] != inspection.template_sha256:
        raise OfficeCoreError("OFFICE_TEMPLATE_FINGERPRINT_MISMATCH", "operations", "操作列表与当前源文件指纹不匹配。")
    if len(normalized["operations"]) > 500:
        raise OfficeCoreError("OFFICE_RESOURCE_LIMIT", "operations", "单次操作数量超过限制。")

    repeat_rows_handler = lambda source, operation: _repeat_rows_handler(source, operation, budget)
    try:
        with tempfile.TemporaryDirectory(prefix="office-core-operations-") as directory:
            input_path = Path(directory) / "source.xlsx"
            output_path = Path(directory) / "candidate.xlsx"
            input_path.write_bytes(data)

            def preserve_core_ooxml(source: bytes, candidate: bytes, operations: list[dict[str, object]]) -> bytes:
                from office_document_operations.errors import DocumentOperationError

                try:
                    format_targets = _format_target_ids(operations, budget)
                    result = _restore_safe_xlsx_extensions(source, candidate, format_targets)
                    return _canonicalize_xlsx_numeric_writes(result, _numeric_write_pairs(operations))
                except OfficeCoreError as exc:
                    raise DocumentOperationError(exc.code, exc.stage, exc.message) from exc

            report = DocumentOperationEngine().execute(
                input_path,
                output_path,
                normalized,
                repeat_rows_handler=repeat_rows_handler,
                candidate_postprocessor=preserve_core_ooxml,
                max_output_bytes=budget.max_file_size,
            )
            result = report.as_dict()
            if result["status"] != "PASS" or not output_path.is_file():
                detail = result.get("error") or {}
                raise OfficeCoreError(
                    detail.get("error_code", "OFFICE_OPERATION_FAILED"),
                    detail.get("stage", "operations"),
                    detail.get("message", "Document operation execution failed."),
                )
            candidate = output_path.read_bytes()
    except OfficeCoreError:
        raise
    except Exception as exc:
        raise OfficeCoreError("OFFICE_ENGINE_FAILED", "xlsx_operations", "Excel 操作执行或保存后验证失败。") from exc

    if not candidate or len(candidate) > budget.max_file_size:
        raise OfficeCoreError("OFFICE_RESOURCE_LIMIT", "xlsx_operations", "生成的候选文件为空或超过大小限制。")
    inspect_package(candidate, filename, mime_type, budget)
    return RenderCandidate(
        "xlsx",
        inspection.template_sha256,
        hashlib.sha256(candidate).hexdigest(),
        candidate,
        len(normalized["operations"]),
        inspection.warnings,
        "candidate_verified_not_delivered",
        result["output"]["validation"],
    )


def _mapping_operation_list(data: bytes, writes, preprocessing=None) -> dict[str, object]:
    operations: list[dict[str, object]] = []
    if preprocessing is not None:
        if not isinstance(preprocessing, dict) or set(preprocessing) != {"action", "sheet", "start_row", "record_count", "columns"}:
            raise _mapping_error("重复行结构指令字段无效。")
        if preprocessing.get("action") != "insert_repeat_rows":
            raise _mapping_error("重复行结构指令类型无效。")
        operations.append({
            "operation_id": "repeat-rows-0001",
            "type": "repeat_rows",
            "target": {"sheet": preprocessing["sheet"], "start_row": preprocessing["start_row"]},
            "parameters": {"record_count": preprocessing["record_count"], "columns": preprocessing["columns"]},
        })
    for index, (element, value) in enumerate(writes, 1):
        location = element.element_id[5:]
        sheet, coordinate = location.rsplit("!", 1)
        operation = value["operation"]
        if operation == "set_number_format":
            entry = {"operation_id": f"mapping-format-{index:04d}", "type": "format", "target": {"sheet": sheet, "cell": coordinate}, "parameters": {"number_format": value["data"]}}
        elif operation == "set_formula":
            entry = {"operation_id": f"mapping-formula-{index:04d}", "type": "set_formula", "target": {"sheet": sheet, "cell": coordinate}, "parameters": {"formula": value["data"]}}
        else:
            entry = {
                "operation_id": f"mapping-value-{index:04d}",
                "type": "set_value",
                "target": {"sheet": sheet, "cell": coordinate},
                "parameters": {
                    "value": {"type": value["type"], "data": value["data"]},
                    "overwrite_formula": element.kind == "formula",
                },
            }
        operations.append(entry)
    return {"schema_version": "1.1", "source_sha256": hashlib.sha256(data).hexdigest(), "operations": operations}


def _render_xlsx(
    data: bytes,
    filename: str,
    mime_type: str,
    mapping: object,
    budget: ResourceBudget,
    preprocessing=None,
    authorized_blank_targets: tuple[str, ...] = (),
) -> RenderCandidate:
    source_inspection = inspect_inline(data, filename, mime_type, budget)
    expanded = data
    repeat_instruction = preprocessing
    expanded_for_inspection = False
    if repeat_instruction is not None:
        try:
            expanded = expand_repeat_rows(data, repeat_instruction, budget).content
            expanded_for_inspection = True
        except OfficeCoreError:
            raise
        except Exception as exc:
            raise _mapping_error("重复行结构扩展失败。") from exc
    inspection = inspect_inline(expanded, filename, mime_type, budget) if expanded_for_inspection else source_inspection
    writes = _validate_mapping(mapping, inspection)
    operation_list = _mapping_operation_list(data, writes, repeat_instruction)
    candidate = _execute_xlsx_operations_inline(data, filename, mime_type, operation_list, budget)
    return _attach_independent_verification(
        expanded,
        candidate,
        filename,
        mime_type,
        mapping,
        budget,
        enabled_format="xlsx",
        authorized_blank_targets=authorized_blank_targets,
    )


def _attach_independent_verification(
    source: bytes,
    candidate: RenderCandidate,
    filename: str,
    mime_type: str,
    mapping: object,
    budget: ResourceBudget,
    *,
    enabled_format: str,
    authorized_blank_targets: tuple[str, ...] = (),
) -> RenderCandidate:
    try:
        from office_verify.errors import OfficeVerifyError
        from office_verify.models import VerificationBudget, VerificationPolicy
        from office_verify.verify import verify_inline
    except ImportError as exc:
        raise OfficeCoreError("OFFICE_VERIFIER_UNAVAILABLE", "verify", "独立文件验证器不可用，已拒绝交付候选文件。") from exc

    try:
        verification_budget = VerificationBudget(
            max_file_size=budget.max_file_size,
            max_expanded_size=budget.max_expanded_size,
            max_zip_entries=budget.max_zip_entries,
            max_entry_size=budget.max_entry_size,
            max_xml_elements=budget.max_xml_elements,
            max_cells=budget.max_cells,
            max_paragraphs=budget.max_paragraphs,
            max_mapping_bytes=min(budget.max_file_size, 1 * 1024 * 1024),
            max_memory_bytes=budget.max_memory_bytes,
            timeout_seconds=budget.timeout_seconds,
        )
        report = verify_inline(
            source,
            candidate.content,
            filename,
            mime_type,
            mapping,
            VerificationPolicy(enabled_formats=(enabled_format,), require_styles=True),
            verification_budget,
            authorized_blank_targets=authorized_blank_targets,
        )
    except OfficeVerifyError as exc:
        raise OfficeCoreError(exc.code, exc.stage, exc.message) from exc
    except ImportError as exc:
        raise OfficeCoreError("OFFICE_VERIFIER_UNAVAILABLE", "verify", "独立文件验证器不可用，已拒绝交付候选文件。") from exc
    verification = {
        "status": report.status,
        "output_sha256": report.output_sha256,
        "office_verify": report.as_dict(),
    }
    if candidate.verification is not None:
        verification["document_operations"] = candidate.verification
    return RenderCandidate(
        candidate.format,
        candidate.template_sha256,
        candidate.candidate_sha256,
        candidate.content,
        candidate.applied_writes,
        candidate.warnings,
        candidate.delivery_status,
        verification,
    )


def execute_operations_inline(data: bytes, filename: str, mime_type: str, operation_list: object, budget: ResourceBudget) -> RenderCandidate:
    inspection = inspect_inline(data, filename, mime_type, budget)
    if inspection.format != "xlsx":
        raise OfficeCoreError("OFFICE_UNSUPPORTED_FEATURE", "operations", "Document Operation Schema 1.1 currently supports XLSX only.")
    return _execute_xlsx_operations_inline(data, filename, mime_type, operation_list, budget)


def _xlsx_sheet_titles_by_part(archive: zipfile.ZipFile) -> dict[str, str]:
    parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False)
    workbook_root = etree.fromstring(archive.read("xl/workbook.xml"), parser=parser)
    rels_root = etree.fromstring(archive.read("xl/_rels/workbook.xml.rels"), parser=parser)
    relationships = {
        item.get("Id"): item.get("Target")
        for item in rels_root
        if _qname(item) == "Relationship"
    }
    result = {}
    for sheet in (item for item in workbook_root.iter() if _qname(item) == "sheet"):
        target = relationships.get(sheet.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"))
        if not target:
            continue
        part = target.lstrip("/") if target.startswith("/") else posixpath.normpath(posixpath.join("xl", target))
        result[part] = sheet.get("name", "")
    return result


def _restore_safe_xlsx_extensions(source: bytes, candidate: bytes, format_targets=()) -> bytes:
    """Restore safe OOXML extensions and style metadata omitted by openpyxl.

    openpyxl may normalize or drop style references on blank cells while it
    serializes a workbook.  Those cells can carry visible borders/fills in
    business templates even though they contain no value.  Since M1 only
    changes cell values, preserve the source style table and every source cell
    style reference verbatim; candidate values and formulas remain from the
    writer output.
    """
    source_zip = zipfile.ZipFile(BytesIO(source), "r")
    candidate_zip = zipfile.ZipFile(BytesIO(candidate), "r")
    replacements: dict[str, bytes] = {}
    candidate_sheet_titles = _xlsx_sheet_titles_by_part(candidate_zip)
    format_targets = set(format_targets)
    candidate_style_map = {}
    if "xl/styles.xml" in source_zip.namelist() and "xl/styles.xml" in candidate_zip.namelist():
        # Validate that any passive extension metadata remains within the
        # existing allowlist, then keep the complete source style catalog.
        try:
            original_styles = etree.fromstring(
                source_zip.read("xl/styles.xml"),
                parser=etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False),
            )
            candidate_styles = etree.fromstring(
                candidate_zip.read("xl/styles.xml"),
                parser=etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False),
            )
        except etree.XMLSyntaxError as exc:
            raise OfficeCoreError(
                "OFFICE_INVALID_OR_MISMATCHED", "xlsx_serialize", "Excel 样式结构无法安全回读。"
            ) from exc
        for extension in (node for node in original_styles if _qname(node) == "extLst"):
            if not _safe_xlsx_extension_list(extension):
                raise OfficeCoreError(
                    "OFFICE_UNSUPPORTED_FEATURE", "xlsx_serialize", "Excel 扩展结构不在安全保留白名单中。"
                )
        if format_targets:
            original_xfs = next((node for node in original_styles if _qname(node) == "cellXfs"), None)
            candidate_xfs = next((node for node in candidate_styles if _qname(node) == "cellXfs"), None)
            original_numfmts = next((node for node in original_styles if _qname(node) == "numFmts"), None)
            candidate_numfmts = next((node for node in candidate_styles if _qname(node) == "numFmts"), None)
            if original_xfs is None or candidate_xfs is None:
                raise OfficeCoreError("OFFICE_STRUCTURE_MISMATCH", "xlsx_serialize", "数字格式样式表缺少 cellXfs。")
            original_formats = {
                item.get("numFmtId"): item.get("formatCode")
                for item in (original_numfmts if original_numfmts is not None else [])
                if _qname(item) == "numFmt"
            }
            if original_numfmts is None and candidate_numfmts is not None:
                original_numfmts = etree.Element(candidate_numfmts.tag)
                # OOXML requires numFmts before fonts.
                original_styles.insert(0, original_numfmts)
            if candidate_numfmts is not None:
                for candidate_format in (item for item in candidate_numfmts if _qname(item) == "numFmt"):
                    format_id = candidate_format.get("numFmtId")
                    existing_code = original_formats.get(format_id)
                    if existing_code is not None and existing_code != candidate_format.get("formatCode"):
                        raise OfficeCoreError("OFFICE_STRUCTURE_MISMATCH", "xlsx_serialize", "数字格式 ID 与模板冲突。")
                    if existing_code is None:
                        original_numfmts.append(deepcopy(candidate_format))
                        original_formats[format_id] = candidate_format.get("formatCode")
            if original_numfmts is not None:
                original_numfmts.set("count", str(len(original_numfmts)))

            signature_to_index = {
                etree.tostring(item, method="c14n"): index
                for index, item in enumerate(original_xfs)
            }
            for candidate_index, candidate_xf in enumerate(candidate_xfs):
                signature = etree.tostring(candidate_xf, method="c14n")
                target_index = signature_to_index.get(signature)
                if target_index is None:
                    target_index = len(original_xfs)
                    original_xfs.append(deepcopy(candidate_xf))
                    signature_to_index[signature] = target_index
                candidate_style_map[candidate_index] = target_index
            original_xfs.set("count", str(len(original_xfs)))
            replacements["xl/styles.xml"] = etree.tostring(
                original_styles, xml_declaration=True, encoding="UTF-8", standalone=True
            )
        else:
            replacements["xl/styles.xml"] = source_zip.read("xl/styles.xml")

    # Restore source cell style references and blank styled cells in each
    # worksheet.  Do not replace values: mapped values, formulas, and shared
    # string representation remain owned by the candidate serializer.
    sheet_parts = tuple(
        name for name in source_zip.namelist()
        if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", name)
        and name in candidate_zip.namelist()
    )
    parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False)
    for part_name in sheet_parts:
        try:
            source_root = etree.fromstring(source_zip.read(part_name), parser=parser)
            candidate_root = etree.fromstring(candidate_zip.read(part_name), parser=parser)
        except etree.XMLSyntaxError as exc:
            raise OfficeCoreError(
                "OFFICE_INVALID_OR_MISMATCHED", "xlsx_serialize", "Excel 工作表结构无法安全回读。"
            ) from exc
        sheet_data = next((node for node in candidate_root if _qname(node) == "sheetData"), None)
        source_data = next((node for node in source_root if _qname(node) == "sheetData"), None)
        if sheet_data is None or source_data is None:
            raise OfficeCoreError(
                "OFFICE_INVALID_OR_MISMATCHED", "xlsx_serialize", "Excel 工作表数据区域缺失。"
            )
        candidate_rows = {
            row.get("r"): row for row in sheet_data if _qname(row) == "row"
        }
        for source_row in (node for node in source_data if _qname(node) == "row"):
            row_number = source_row.get("r")
            candidate_row = candidate_rows.get(row_number)
            if candidate_row is None:
                # A row omitted by openpyxl is recoverable only if it contains
                # no values or formulas; preserve its row formatting metadata.
                nonempty = any(
                    _qname(cell) == "c" and _xlsx_cell_has_content(cell)
                    for cell in source_row
                )
                if nonempty:
                    raise OfficeCoreError(
                        "OFFICE_STRUCTURE_MISMATCH", "xlsx_serialize", "保存时丢失了非空 Excel 行。"
                    )
                candidate_row = etree.Element(source_row.tag)
                for key, value in source_row.attrib.items():
                    candidate_row.set(key, value)
                # Keep sheetData rows ordered by row number.
                following = next(
                    (
                        row for row in sheet_data
                        if _qname(row) == "row"
                        and int(row.get("r", "0")) > int(row_number or "0")
                    ),
                    None,
                )
                if following is None:
                    sheet_data.append(candidate_row)
                else:
                    following.addprevious(candidate_row)
                candidate_rows[row_number] = candidate_row

            candidate_cells = {
                cell.get("r"): cell for cell in candidate_row if _qname(cell) == "c"
            }
            for source_cell in (node for node in source_row if _qname(node) == "c"):
                coordinate = source_cell.get("r")
                candidate_cell = candidate_cells.get(coordinate)
                if candidate_cell is None:
                    if _xlsx_cell_has_content(source_cell):
                        raise OfficeCoreError(
                            "OFFICE_STRUCTURE_MISMATCH", "xlsx_serialize", "保存时丢失了非空 Excel 单元格。"
                        )
                    candidate_cell = etree.Element(source_cell.tag)
                    for key, value in source_cell.attrib.items():
                        candidate_cell.set(key, value)
                    column_number = _xlsx_column_number(coordinate or "")
                    following = next(
                        (
                            cell for cell in candidate_row
                            if _qname(cell) == "c"
                            and _xlsx_column_number(cell.get("r", "")) > column_number
                        ),
                        None,
                    )
                    if following is None:
                        candidate_row.append(candidate_cell)
                    else:
                        following.addprevious(candidate_cell)
                    candidate_cells[coordinate] = candidate_cell
                else:
                    # Style IDs in the source and candidate tables may have
                    # been normalized differently by openpyxl.  Restore the
                    # original style and cell metadata attributes exactly.
                    sheet_title = candidate_sheet_titles.get(part_name, "")
                    is_format_target = f"xlsx:{sheet_title}!{coordinate}" in format_targets
                    for attribute in ("s", "cm", "vm", "ph"):
                        if attribute in source_cell.attrib:
                            if attribute != "s" or not is_format_target:
                                candidate_cell.set(attribute, source_cell.get(attribute))
                        else:
                            if attribute != "s" or not is_format_target:
                                candidate_cell.attrib.pop(attribute, None)
        sheet_title = candidate_sheet_titles.get(part_name, "")
        if candidate_style_map and sheet_title:
            target_coordinates = {
                target.split("!", 1)[1]
                for target in format_targets
                if target.startswith(f"xlsx:{sheet_title}!")
            }
            for cell in (node for node in candidate_root.iter() if _qname(node) == "c"):
                if cell.get("r") in target_coordinates:
                    style_index = int(cell.get("s", "0"))
                    if style_index not in candidate_style_map:
                        raise OfficeCoreError("OFFICE_STRUCTURE_MISMATCH", "xlsx_serialize", "格式目标样式不存在。")
                    cell.set("s", str(candidate_style_map[style_index]))
        replacements[part_name] = etree.tostring(
            candidate_root,
            xml_declaration=True,
            encoding="UTF-8",
            standalone=True,
        )

    for part_name in ("xl/workbook.xml",):
        if part_name not in source_zip.namelist() or part_name not in candidate_zip.namelist():
            continue
        try:
            original_root = etree.fromstring(
                source_zip.read(part_name),
                parser=etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False),
            )
            candidate_root = etree.fromstring(
                candidate_zip.read(part_name),
                parser=etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False),
            )
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


def _canonicalize_xlsx_numeric_writes(candidate: bytes, writes) -> bytes:
    """Restore the caller's decimal spelling for mapped numeric cells.

    openpyxl serializes some binary floats with a 16-digit tail (8.3 becomes
    8.300000000000001). The independent verifier compares the explicit M1
    value with the OOXML numeric value, so preserve the canonical JSON decimal
    spelling for each mapped numeric target after openpyxl has written it.
    """
    numeric_writes = []
    for element, value in writes:
        data = value.get("data") if isinstance(value, dict) else None
        if value.get("type") == "number" and isinstance(data, (int, float)) and not isinstance(data, bool):
            if isinstance(data, float) and not math.isfinite(data):
                raise OfficeCoreError("OFFICE_MAPPING_INVALID", "mapping", "数字值必须为有限数。")
            location = element.element_id[5:].split("!", 1)
            if len(location) == 2:
                numeric_writes.append((location[0], location[1], "0" if data == 0 else str(data)))
    if not numeric_writes:
        return candidate

    try:
        source_zip = zipfile.ZipFile(BytesIO(candidate), "r")
        workbook = etree.fromstring(
            source_zip.read("xl/workbook.xml"),
            parser=etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False),
        )
        relationships = etree.fromstring(
            source_zip.read("xl/_rels/workbook.xml.rels"),
            parser=etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False),
        )
        relation_targets = {
            relation.get("Id"): relation.get("Target")
            for relation in relationships
            if etree.QName(relation).localname == "Relationship"
        }
        sheet_parts = {}
        for sheet in workbook.xpath("//*[local-name()='sheet']"):
            target = relation_targets.get(sheet.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"))
            if not target:
                continue
            part = target.lstrip("/") if target.startswith("/") else posixpath.normpath(posixpath.join("xl", target))
            sheet_parts[sheet.get("name")] = part
        replacements = {}
        for sheet_name, coordinate, canonical_value in numeric_writes:
            part_name = sheet_parts.get(sheet_name)
            if not part_name or part_name not in source_zip.namelist():
                raise OfficeCoreError("OFFICE_MAPPING_INVALID", "mapping", "数字映射目标所在工作表不存在。")
            root = etree.fromstring(
                replacements.get(part_name, source_zip.read(part_name)),
                parser=etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False),
            )
            cell = next(
                (node for node in root.xpath("//*[local-name()='c']") if node.get("r") == coordinate),
                None,
            )
            value_node = next(
                (node for node in cell if etree.QName(node).localname == "v"),
                None,
            ) if cell is not None else None
            if value_node is None:
                raise OfficeCoreError("OFFICE_ENGINE_FAILED", "xlsx_serialize", "数字目标无法序列化。")
            value_node.text = canonical_value
            replacements[part_name] = etree.tostring(
                root, xml_declaration=True, encoding="UTF-8", standalone=True
            )
        source_zip.close()
        merged = BytesIO()
        with zipfile.ZipFile(BytesIO(candidate), "r") as archive, zipfile.ZipFile(merged, "w", zipfile.ZIP_DEFLATED) as output:
            for info in archive.infolist():
                output.writestr(info, replacements.get(info.filename, archive.read(info.filename)))
        return merged.getvalue()
    except OfficeCoreError:
        raise
    except (KeyError, OSError, zipfile.BadZipFile, etree.XMLSyntaxError) as exc:
        raise OfficeCoreError("OFFICE_ENGINE_FAILED", "xlsx_serialize", "数字映射无法安全序列化。") from exc


def _xlsx_cell_has_content(cell: etree._Element) -> bool:
    """Return whether an OOXML cell carries a value, formula, or inline text."""
    for child in cell:
        name = _qname(child)
        if name == "f":
            return True
        if name == "v" and child.text is not None:
            return True
        if name == "is" and (child.text is not None or any(node.text is not None for node in child.iter())):
            return True
    return False


def _xlsx_column_number(coordinate: str) -> int:
    match = re.match(r"([A-Z]+)", coordinate)
    if not match:
        return 0
    value = 0
    for char in match.group(1):
        value = value * 26 + ord(char) - ord("A") + 1
    return value


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
    unverified = RenderCandidate(
        "docx",
        inspection.template_sha256,
        hashlib.sha256(candidate).hexdigest(),
        candidate,
        len(writes),
        (),
    )
    return _attach_independent_verification(
        data,
        unverified,
        filename,
        mime_type,
        mapping,
        budget,
        enabled_format="docx",
    )


def render_inline(
    data: bytes,
    filename: str,
    mime_type: str,
    mapping: object,
    budget: ResourceBudget,
    preprocessing=None,
    authorized_blank_targets: tuple[str, ...] = (),
) -> RenderCandidate:
    inspection = inspect_inline(data, filename, mime_type, budget)
    if inspection.format == "xlsx":
        return _render_xlsx(data, filename, mime_type, mapping, budget, preprocessing, authorized_blank_targets)
    if inspection.format == "docx":
        return _render_docx(data, filename, mime_type, mapping, budget)
    raise OfficeCoreError("OFFICE_UNSUPPORTED_FEATURE", "format", "该 Office 格式当前未启用。")
