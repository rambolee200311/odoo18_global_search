"""Bounded structural expansion for repeating rows in OOXML workbooks.

This module knows about spreadsheet structure only. Callers provide the sheet,
first detail row, and live row count; it does not infer business meaning or
access application data.
"""

from __future__ import annotations

from copy import deepcopy
from collections.abc import Mapping
from io import BytesIO
import re
from typing import NamedTuple
from zipfile import ZIP_DEFLATED, ZipFile
from xml.etree import ElementTree as ET

from openpyxl.formula.translate import Translator
from openpyxl.formula.translate import TranslatorError

from .errors import OfficeCoreError
from .models import ResourceBudget


_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_REL_DOC = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
_NS = {"m": _MAIN, "r": _REL_DOC, "p": _PKG_REL}
ET.register_namespace("", _MAIN)
ET.register_namespace("r", _REL_DOC)

_CELL_REF = re.compile(r"(\$?[A-Z]{1,3}\$?)([1-9][0-9]*)$")
_FORMULA_REF = re.compile(r"(?<![A-Za-z0-9_.])((?:'[^']+'|[A-Za-z_][A-Za-z0-9_. ]*)!)?(\$?[A-Z]{1,3}\$?)([1-9][0-9]*)(?![A-Za-z0-9_])")
_SUM_RANGE = re.compile(r"(?i)SUM\(\s*(\$?[A-Z]{1,3}\$?)([1-9][0-9]*):(\$?[A-Z]{1,3}\$?)([1-9][0-9]*)\s*\)")
_COLUMN_ID = re.compile(r"[A-Z]{1,3}")


class RepeatRowsResult(NamedTuple):
    """Result metadata for one caller-described repeating-row action."""

    content: bytes
    sheet: str
    start_row: int
    record_count: int
    columns: dict[str, str]
    summary_row_before: int | None
    summary_row_after: int | None
    inserted_rows: int


def _fail(message: str, code: str = "OFFICE_MAPPING_INVALID") -> OfficeCoreError:
    return OfficeCoreError(code, "xlsx_structure", message)


def _sheet_path(archive: ZipFile, sheet_name: str) -> str:
    try:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    except (KeyError, ET.ParseError) as exc:
        raise _fail("工作簿目录无法安全读取。", "OFFICE_INVALID_OR_MISMATCHED") from exc
    sheet = next(
        (node for node in workbook.findall("m:sheets/m:sheet", _NS) if node.get("name") == sheet_name),
        None,
    )
    if sheet is None:
        raise _fail("指定工作表不存在。")
    relationship_id = sheet.get(f"{{{_REL_DOC}}}id")
    relationship = next(
        (node for node in relationships.findall("p:Relationship", _NS) if node.get("Id") == relationship_id),
        None,
    )
    if relationship is None or relationship.get("TargetMode") == "External":
        raise _fail("工作表关系无效。", "OFFICE_INVALID_OR_MISMATCHED")
    target = relationship.get("Target", "")
    from pathlib import PurePosixPath

    target_path = PurePosixPath(target)
    normalized = target_path.as_posix().lstrip("/") if target_path.is_absolute() else (PurePosixPath("xl") / target_path).as_posix()
    if normalized.startswith("../") or normalized not in archive.namelist():
        raise _fail("工作表 XML 不存在。", "OFFICE_INVALID_OR_MISMATCHED")
    return normalized


def find_summary_row(
    source: bytes,
    *,
    sheet_name: str,
    first_row: int,
    budget: ResourceBudget,
    allow_missing: bool = False,
) -> int | None:
    """Find the first row below a repeated range that aggregates that range.

    Detection relies on spreadsheet formulas, not worksheet names, labels, or
    document-specific coordinates. A caller must still supply the intended
    detail start row from its validated mapping/layout context.
    """
    budget.validate()
    if type(first_row) is not int or first_row < 1:
        raise _fail("first_row 必须是正整数。")
    if not isinstance(source, bytes) or not source or len(source) > budget.max_file_size:
        raise _fail("源文件为空或超出文件大小限制。", "OFFICE_RESOURCE_LIMIT")
    try:
        archive = ZipFile(BytesIO(source), "r")
    except Exception as exc:
        raise _fail("源文件不是有效的 OOXML 压缩包。", "OFFICE_INVALID_OR_MISMATCHED") from exc
    with archive:
        infos = archive.infolist()
        if len(infos) > budget.max_zip_entries or archive.testzip() is not None:
            raise _fail("OOXML 压缩包损坏或条目数超限。", "OFFICE_INVALID_OR_MISMATCHED")
        if any(info.file_size > budget.max_entry_size for info in infos) or sum(info.file_size for info in infos) > budget.max_expanded_size:
            raise _fail("OOXML 解压体积超出资源限制。", "OFFICE_RESOURCE_LIMIT")
        part = _sheet_path(archive, sheet_name)
        try:
            worksheet = ET.fromstring(archive.read(part))
        except (KeyError, ET.ParseError) as exc:
            raise _fail("工作表 XML 无法安全读取。", "OFFICE_INVALID_OR_MISMATCHED") from exc
        matches = []
        for row in worksheet.findall("m:sheetData/m:row", _NS):
            row_number = int(row.get("r"))
            if row_number <= first_row:
                continue
            for cell in row.findall("m:c", _NS):
                formula = cell.find("m:f", _NS)
                if formula is None or not formula.text:
                    continue
                for match in _SUM_RANGE.finditer(formula.text):
                    start_row, end_row = int(match.group(2)), int(match.group(4))
                    if start_row >= first_row and end_row == row_number - 1 and end_row >= start_row:
                        matches.append(row_number)
                        break
                if matches and matches[-1] == row_number:
                    break
        if not matches:
            if allow_missing:
                return None
            raise _fail("未找到聚合明细区域的汇总公式。", "OFFICE_UNSUPPORTED_FEATURE")
        return min(matches)


def _has_cell_content(cell) -> bool:
    """Return whether an OOXML cell contains a value or formula."""
    if cell.find(f"{{{_MAIN}}}f") is not None:
        return True
    value = cell.find(f"{{{_MAIN}}}v")
    if value is not None and value.text not in (None, ""):
        return True
    inline = cell.find(f"{{{_MAIN}}}is")
    return inline is not None and any(
        text.text not in (None, "")
        for text in inline.iter(f"{{{_MAIN}}}t")
    )


def _expand_xlsx_rows_append_only(
    source: bytes,
    *,
    sheet_name: str,
    first_row: int,
    row_count: int,
    columns: tuple[str, ...],
    budget: ResourceBudget,
) -> tuple[bytes, int]:
    """Expand a repeated region into a structurally empty tail of a worksheet.

    This path is intentionally append-only: without an aggregation formula,
    there is no reliable anchor for moving content below the repeated region.
    Any populated cell, formula, merge, or Excel table below the first row
    makes the layout ambiguous and is rejected. A present prototype row keeps
    its existing styles; when it is absent, default-style rows and requested
    target cells are materialized.
    """
    budget.validate()
    if not isinstance(source, bytes) or not source or len(source) > budget.max_file_size:
        raise _fail("源文件为空或超出文件大小限制。", "OFFICE_RESOURCE_LIMIT")
    try:
        archive = ZipFile(BytesIO(source), "r")
    except Exception as exc:
        raise _fail("源文件不是有效的 OOXML 压缩包。", "OFFICE_INVALID_OR_MISMATCHED") from exc
    with archive:
        infos = archive.infolist()
        if len(infos) > budget.max_zip_entries or archive.testzip() is not None:
            raise _fail("OOXML 压缩包损坏或条目数超限。", "OFFICE_INVALID_OR_MISMATCHED")
        if any(info.file_size > budget.max_entry_size for info in infos) or sum(info.file_size for info in infos) > budget.max_expanded_size:
            raise _fail("OOXML 解压体积超出资源限制。", "OFFICE_RESOURCE_LIMIT")
        part = _sheet_path(archive, sheet_name)
        try:
            worksheet = ET.fromstring(archive.read(part))
        except (KeyError, ET.ParseError) as exc:
            raise _fail("工作表 XML 无法安全读取。", "OFFICE_INVALID_OR_MISMATCHED") from exc
        sheet_data = worksheet.find(f"{{{_MAIN}}}sheetData")
        if sheet_data is None:
            raise _fail("工作表缺少数据区域。", "OFFICE_INVALID_OR_MISMATCHED")
        rows = {
            int(node.get("r")): node
            for node in sheet_data.findall(f"{{{_MAIN}}}row")
        }
        prototype = rows.get(first_row)
        # A single record already fits a present template row. Preserve the
        # historical no-op behavior in that case. If the row is absent, it
        # still needs to be materialized so the mapping manifest can expose
        # its target cells.
        if row_count == 1 and prototype is not None:
            return source, 0

        # No-summary layouts are safe only when the tail has no meaningful
        # worksheet content that would need to be shifted or reinterpreted.
        if worksheet.find(f"{{{_MAIN}}}tableParts") is not None:
            raise _fail("无汇总行的重复区域不能安全扩展包含 Excel 表格的工作表。", "OFFICE_UNSUPPORTED_FEATURE")
        for row_number, row in rows.items():
            if row_number > first_row and any(
                _has_cell_content(cell)
                for cell in row.findall(f"{{{_MAIN}}}c")
            ):
                raise _fail("无汇总行时，起始行下方已有内容，无法安全追加重复行。", "OFFICE_UNSUPPORTED_FEATURE")
        merge_cells = worksheet.find(f"{{{_MAIN}}}mergeCells")
        if merge_cells is not None:
            from openpyxl.utils.cell import range_boundaries

            for merged in merge_cells.findall(f"{{{_MAIN}}}mergeCell", _NS):
                try:
                    _min_col, min_row, _max_col, max_row = range_boundaries(merged.get("ref", ""))
                except ValueError as exc:
                    raise _fail("工作表合并区域无效。", "OFFICE_INVALID_OR_MISMATCHED") from exc
                if max_row >= first_row:
                    raise _fail("无汇总行时，重复区域包含合并单元格，无法安全追加。", "OFFICE_UNSUPPORTED_FEATURE")

        last_row = first_row + row_count - 1
        if last_row > 1_048_576:
            raise _fail("扩展后的行号超出工作表限制。", "OFFICE_RESOURCE_LIMIT")
        from openpyxl.utils.cell import column_index_from_string

        ordered_columns = tuple(sorted(columns, key=column_index_from_string))
        created_rows = 0
        if prototype is None:
            prototype = ET.Element(f"{{{_MAIN}}}row", {"r": str(first_row)})
            rows[first_row] = prototype
            created_rows += 1

        def ensure_target_cells(row, row_number):
            existing = {cell.get("r") for cell in row.findall(f"{{{_MAIN}}}c")}
            for column in ordered_columns:
                reference = f"{column}{row_number}"
                if reference not in existing:
                    row.append(ET.Element(f"{{{_MAIN}}}c", {"r": reference}))
                    existing.add(reference)

        ensure_target_cells(prototype, first_row)
        formula_prototypes = _formula_prototypes(rows, first_row, first_row)
        replaced_rows = []
        for row_number in range(first_row + 1, last_row + 1):
            existing = rows.get(row_number)
            if existing is not None:
                # Blank reserved rows retain their own styles and row height.
                ensure_target_cells(existing, row_number)
                continue
            new_row = _clone_formula_row(prototype, row_number, first_row)
            ensure_target_cells(new_row, row_number)
            rows[row_number] = new_row
            replaced_rows.append(new_row)
            created_rows += 1

        if sum(len(row.findall(f"{{{_MAIN}}}c")) for row in rows.values()) > budget.max_cells:
            raise _fail("扩展后的行结构超过资源预算。", "OFFICE_RESOURCE_LIMIT")
        _fill_down_formulas(
            list(rows.values()),
            formula_prototypes,
            first_row,
            last_row,
        )
        for child in list(sheet_data):
            if child.tag == f"{{{_MAIN}}}row":
                sheet_data.remove(child)
        for row in sorted(rows.values(), key=lambda item: int(item.get("r"))):
            sheet_data.append(row)

        dimension = worksheet.find(f"{{{_MAIN}}}dimension")
        if dimension is not None:
            from openpyxl.utils.cell import get_column_letter, range_boundaries

            try:
                min_col, min_row, max_col, max_row = range_boundaries(dimension.get("ref", ""))
            except ValueError as exc:
                raise _fail("工作表尺寸范围无效。", "OFFICE_INVALID_OR_MISMATCHED") from exc
            if ordered_columns:
                max_col = max(max_col, max(column_index_from_string(column) for column in ordered_columns))
            max_row = max(max_row, last_row)
            end = f"{get_column_letter(max_col)}{max_row}"
            start = f"{get_column_letter(min_col)}{min_row}"
            dimension.set("ref", start if start == end else f"{start}:{end}")

        replacement = ET.tostring(worksheet, encoding="utf-8", xml_declaration=True)
        output = BytesIO()
        with ZipFile(output, "w", ZIP_DEFLATED) as result:
            for info in infos:
                result.writestr(info, replacement if info.filename == part else archive.read(info.filename))
        candidate = output.getvalue()
        if len(candidate) > budget.max_file_size:
            raise _fail("扩展后的文件超过大小限制。", "OFFICE_RESOURCE_LIMIT")
        return candidate, created_rows


def _cell_ref(ref: str, insertion_row: int, amount: int) -> str:
    match = _CELL_REF.fullmatch(ref or "")
    if not match:
        return ref
    row = int(match.group(2))
    return f"{match.group(1)}{row + amount if row >= insertion_row else row}"


def _shift_range(value: str, insertion_row: int, amount: int) -> str:
    shifted = []
    for token in (value or "").split():
        if ":" in token:
            start, end = token.split(":", 1)
            shifted.append(f"{_cell_ref(start, insertion_row, amount)}:{_cell_ref(end, insertion_row, amount)}")
        else:
            shifted.append(_cell_ref(token, insertion_row, amount))
    return " ".join(shifted)


def _shift_formula(formula: str, insertion_row: int, amount: int, sheet_name: str) -> str:
    escaped_sheet = sheet_name.replace("'", "''")

    def replace(match):
        qualifier, column, row_text = match.groups()
        if qualifier:
            clean = qualifier[:-1].strip("'").replace("''", "'")
            if clean != sheet_name:
                return match.group(0)
        row = int(row_text)
        if row < insertion_row:
            return match.group(0)
        prefix = f"'{escaped_sheet}'!" if qualifier and qualifier.startswith("'") else (f"{sheet_name}!" if qualifier else "")
        return f"{prefix}{column}{row + amount}"

    return _FORMULA_REF.sub(replace, formula)


def _clone_formula_row(template_row, new_row_number: int, template_row_number: int):
    row = deepcopy(template_row)
    row.set("r", str(new_row_number))
    for cell in row.findall(f"{{{_MAIN}}}c"):
        match = _CELL_REF.fullmatch(cell.get("r", ""))
        if match:
            cell.set("r", f"{match.group(1)}{new_row_number}")
        formula = cell.find(f"{{{_MAIN}}}f")
        for child in list(cell):
            if child is formula:
                continue
            cell.remove(child)
        cell.attrib.pop("t", None)
        if formula is not None and formula.text:
            formula.text = re.sub(
                rf"(?<![A-Za-z0-9_])([\$]?[A-Z]{{1,3}}\$?){template_row_number}(?![A-Za-z0-9_])",
                lambda match: f"{match.group(1)}{new_row_number}",
                formula.text,
            )
    return row


def _formula_prototypes(rows, first_row: int, last_row: int):
    """Collect the first formula in each repeated column as a fill-down rule."""
    prototypes = {}
    for row_number in range(first_row, last_row + 1):
        row = rows.get(row_number)
        if row is None:
            continue
        for cell in row.findall(f"{{{_MAIN}}}c"):
            formula = cell.find(f"{{{_MAIN}}}f")
            if formula is None or not formula.text:
                continue
            if formula.attrib:
                raise _fail(
                    "共享公式或特殊公式类型不支持安全的行扩展。",
                    "OFFICE_UNSUPPORTED_FEATURE",
                )
            match = _CELL_REF.fullmatch(cell.get("r", ""))
            if match:
                prototypes.setdefault(match.group(1).replace("$", ""), (row_number, cell, formula.text))
    return prototypes


def _fill_down_formulas(shifted_rows, prototypes, first_row: int, last_row: int) -> None:
    rows = {int(row.get("r")): row for row in shifted_rows}
    for column, (origin_row, origin_cell, formula_text) in prototypes.items():
        for row_number in range(origin_row + 1, last_row + 1):
            row = rows.get(row_number)
            if row is None:
                raise _fail("公式目标行不存在。", "OFFICE_ENGINE_FAILED")
            reference = f"{column}{row_number}"
            cell = next(
                (item for item in row.findall(f"{{{_MAIN}}}c") if item.get("r") == reference),
                None,
            )
            if cell is None:
                cell = ET.Element(f"{{{_MAIN}}}c", {"r": reference})
                row.append(cell)
            if cell.find(f"{{{_MAIN}}}f") is not None:
                continue
            value = cell.find(f"{{{_MAIN}}}v")
            if value is not None and value.text not in (None, ""):
                continue
            for child in list(cell):
                cell.remove(child)
            cell.attrib.pop("t", None)
            if origin_cell.get("s") is not None:
                cell.set("s", origin_cell.get("s"))
            try:
                translated = Translator(
                    f"={formula_text}",
                    origin=origin_cell.get("r"),
                ).translate_formula(reference)
            except (TranslatorError, TypeError, ValueError) as exc:
                raise _fail(
                    "重复行公式无法安全平移。",
                    "OFFICE_UNSUPPORTED_FEATURE",
                ) from exc
            ET.SubElement(cell, f"{{{_MAIN}}}f").text = translated.lstrip("=")
            ET.SubElement(cell, f"{{{_MAIN}}}v")
        row = rows.get(origin_row)
        if row is not None:
            row[:] = sorted(
                list(row),
                key=lambda item: (
                    0 if item.tag != f"{{{_MAIN}}}c" else 1,
                    _CELL_REF.fullmatch(item.get("r", "")).group(1)
                    if item.tag == f"{{{_MAIN}}}c" and _CELL_REF.fullmatch(item.get("r", ""))
                    else "",
                ),
            )
    for row in rows.values():
        row[:] = sorted(
            list(row),
            key=lambda item: (
                0 if item.tag != f"{{{_MAIN}}}c" else 1,
                _CELL_REF.fullmatch(item.get("r", "")).group(1)
                if item.tag == f"{{{_MAIN}}}c" and _CELL_REF.fullmatch(item.get("r", ""))
                else "",
            ),
        )


def _extend_summary_formula(formula: str, first_row: int, prior_last_row: int, new_last_row: int) -> str:
    def replace(match):
        start_column, start_text, end_column, end_text = match.groups()
        if int(start_text) == first_row and int(end_text) == prior_last_row:
            return f"SUM({start_column}{start_text}:{end_column}{new_last_row})"
        return match.group(0)

    return _SUM_RANGE.sub(replace, formula)


def expand_xlsx_rows(
    source: bytes,
    *,
    sheet_name: str,
    first_row: int,
    row_count: int,
    summary_row: int,
    budget: ResourceBudget,
) -> bytes:
    """Insert repeat rows before a summary row and extend adjacent SUM ranges.

    The row immediately above ``summary_row`` is used as the style/formula
    prototype. Existing rows below the insertion point and worksheet range
    metadata are shifted. The source is immutable; unsupported structures fail
    closed through normal Office package validation by the caller.
    """
    budget.validate()
    if not isinstance(source, bytes) or not source or len(source) > budget.max_file_size:
        raise _fail("源文件为空或超出文件大小限制。", "OFFICE_RESOURCE_LIMIT")
    if not isinstance(sheet_name, str) or not sheet_name or len(sheet_name) > 255:
        raise _fail("工作表名称无效。")
    for label, value in (("first_row", first_row), ("row_count", row_count), ("summary_row", summary_row)):
        if type(value) is not int or value < 1:
            raise _fail(f"{label} 必须是正整数。")
    if summary_row <= first_row or row_count < 1:
        raise _fail("重复行布局参数无效。")

    try:
        archive = ZipFile(BytesIO(source), "r")
    except Exception as exc:
        raise _fail("源文件不是有效的 OOXML 压缩包。", "OFFICE_INVALID_OR_MISMATCHED") from exc
    with archive:
        infos = archive.infolist()
        if len(infos) > budget.max_zip_entries or archive.testzip() is not None:
            raise _fail("OOXML 压缩包损坏或条目数超限。", "OFFICE_INVALID_OR_MISMATCHED")
        if any(info.file_size > budget.max_entry_size for info in infos) or sum(info.file_size for info in infos) > budget.max_expanded_size:
            raise _fail("OOXML 解压体积超出资源限制。", "OFFICE_RESOURCE_LIMIT")
        part = _sheet_path(archive, sheet_name)
        try:
            worksheet = ET.fromstring(archive.read(part))
        except (KeyError, ET.ParseError) as exc:
            raise _fail("工作表 XML 无法安全读取。", "OFFICE_INVALID_OR_MISMATCHED") from exc
        sheet_data = worksheet.find(f"{{{_MAIN}}}sheetData")
        if sheet_data is None:
            raise _fail("工作表缺少数据区域。", "OFFICE_INVALID_OR_MISMATCHED")
        rows = {int(node.get("r")): node for node in sheet_data.findall(f"{{{_MAIN}}}row")}
        if summary_row not in rows or first_row not in rows or summary_row - 1 not in rows:
            raise _fail("指定的重复行或汇总行不存在。")

        prior_last_row = summary_row - 1
        capacity = summary_row - first_row
        inserted = max(0, row_count - capacity)
        if not inserted:
            return source

        formula_prototypes = _formula_prototypes(rows, first_row, prior_last_row)

        original_summary = rows[summary_row]
        formulas = [
            node for node in original_summary.findall(f"{{{_MAIN}}}c")
            if node.find(f"{{{_MAIN}}}f") is not None
        ]
        if not formulas or not any(
            _SUM_RANGE.search(cell.find(f"{{{_MAIN}}}f").text or "") for cell in formulas
        ):
            raise _fail("扩展前必须存在可验证的汇总行公式。", "OFFICE_UNSUPPORTED_FEATURE")

        shifted_rows = []
        for row in list(sheet_data.findall(f"{{{_MAIN}}}row")):
            original_number = int(row.get("r"))
            new_number = original_number + inserted if original_number >= summary_row else original_number
            row.set("r", str(new_number))
            for cell in row.findall(f"{{{_MAIN}}}c"):
                cell.set("r", _cell_ref(cell.get("r", ""), summary_row, inserted))
                formula = cell.find(f"{{{_MAIN}}}f")
                if formula is not None and formula.text:
                    formula.text = _shift_formula(formula.text, summary_row, inserted, sheet_name)
            shifted_rows.append(row)

        prototype = rows[prior_last_row]
        for offset in range(inserted):
            shifted_rows.append(_clone_formula_row(prototype, summary_row + offset, prior_last_row))

        _fill_down_formulas(
            shifted_rows,
            formula_prototypes,
            first_row,
            first_row + row_count - 1,
        )

        final_row = summary_row + inserted
        final_summary = next((node for node in shifted_rows if int(node.get("r")) == final_row), None)
        if final_summary is None:
            raise _fail("汇总行移动失败。", "OFFICE_ENGINE_FAILED")
        last_detail_row = first_row + row_count - 1
        for cell in final_summary.findall(f"{{{_MAIN}}}c"):
            formula = cell.find(f"{{{_MAIN}}}f")
            if formula is not None and formula.text:
                formula.text = _extend_summary_formula(
                    formula.text, first_row, prior_last_row, last_detail_row
                )

        if len(shifted_rows) > budget.max_cells:
            raise _fail("扩展后的行结构超过资源预算。", "OFFICE_RESOURCE_LIMIT")
        for child in list(sheet_data):
            if child.tag == f"{{{_MAIN}}}row":
                sheet_data.remove(child)
        for row in sorted(shifted_rows, key=lambda item: int(item.get("r"))):
            sheet_data.append(row)
        for node in worksheet.iter():
            for attribute in ("ref", "sqref", "activeCell", "topLeftCell"):
                if attribute in node.attrib:
                    node.set(attribute, _shift_range(node.get(attribute, ""), summary_row, inserted))

        replacement = ET.tostring(worksheet, encoding="utf-8", xml_declaration=True)
        output = BytesIO()
        with ZipFile(output, "w", ZIP_DEFLATED) as result:
            for info in infos:
                result.writestr(info, replacement if info.filename == part else archive.read(info.filename))
        candidate = output.getvalue()
        if len(candidate) > budget.max_file_size:
            raise _fail("扩展后的文件超过大小限制。", "OFFICE_RESOURCE_LIMIT")
        return candidate


def expand_repeat_rows(
    source: bytes,
    instruction: Mapping,
    budget: ResourceBudget,
) -> RepeatRowsResult:
    """Apply a generic ``insert_repeat_rows`` structure instruction.

    The caller supplies the worksheet, first data row, collection length and
    writable columns. This engine does not inspect template filenames, record
    models, business labels, or the meaning of column descriptors. A summary
    row is located from formulas and shifted only when the repeated range
    exceeds the template's existing capacity.
    """
    if not isinstance(instruction, Mapping):
        raise _fail("结构指令必须是对象。")
    required = {"action", "sheet", "start_row", "record_count", "columns"}
    if set(instruction) != required:
        raise _fail("重复行结构指令字段无效。")
    if instruction.get("action") != "insert_repeat_rows":
        raise _fail("不支持的结构指令。", "OFFICE_UNSUPPORTED_FEATURE")
    sheet = instruction.get("sheet")
    start_row = instruction.get("start_row")
    record_count = instruction.get("record_count")
    columns = instruction.get("columns")
    if not isinstance(sheet, str) or not sheet or len(sheet) > 255:
        raise _fail("工作表名称无效。")
    if type(start_row) is not int or not 1 <= start_row <= 1_048_576:
        raise _fail("start_row 必须是有效的工作表行号。")
    if type(record_count) is not int or not 1 <= record_count <= budget.max_cells:
        raise _fail("record_count 超出允许范围。", "OFFICE_RESOURCE_LIMIT")
    if not isinstance(columns, Mapping) or not columns:
        raise _fail("columns 必须包含至少一个重复列。")
    normalized_columns = {}
    for column, descriptor in columns.items():
        if not isinstance(column, str) or not _COLUMN_ID.fullmatch(column.upper()):
            raise _fail("重复列标识无效。")
        if not isinstance(descriptor, str) or not descriptor.strip():
            raise _fail("重复列描述必须是非空字符串。")
        normalized_columns[column.upper()] = descriptor.strip()

    summary_row = find_summary_row(
        source,
        sheet_name=sheet,
        first_row=start_row,
        budget=budget,
        allow_missing=True,
    )
    if summary_row is None:
        content, inserted_rows = _expand_xlsx_rows_append_only(
            source,
            sheet_name=sheet,
            first_row=start_row,
            row_count=record_count,
            columns=tuple(normalized_columns),
            budget=budget,
        )
        return RepeatRowsResult(
            content=content,
            sheet=sheet,
            start_row=start_row,
            record_count=record_count,
            columns=normalized_columns,
            summary_row_before=None,
            summary_row_after=None,
            inserted_rows=inserted_rows,
        )
    if summary_row <= start_row:
        raise _fail("汇总行必须位于重复区域之后。")
    capacity = summary_row - start_row
    inserted_rows = max(0, record_count - capacity)
    if summary_row + inserted_rows > 1_048_576:
        raise _fail("扩展后的行号超出工作表限制。", "OFFICE_RESOURCE_LIMIT")
    content = (
        expand_xlsx_rows(
            source,
            sheet_name=sheet,
            first_row=start_row,
            row_count=record_count,
            summary_row=summary_row,
            budget=budget,
        )
        if inserted_rows
        else source
    )
    return RepeatRowsResult(
        content=content,
        sheet=sheet,
        start_row=start_row,
        record_count=record_count,
        columns=normalized_columns,
        summary_row_before=summary_row,
        summary_row_after=summary_row + inserted_rows,
        inserted_rows=inserted_rows,
    )
