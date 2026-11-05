"""Independent saved-file verification using a fresh XLSX read."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import Any

from openpyxl import load_workbook
from openpyxl.styles.numbers import is_date_format
from openpyxl.utils.datetime import from_excel, to_excel
from openpyxl.utils.cell import column_index_from_string, range_boundaries

from .errors import DocumentOperationError
from .schema import validate_operation_list


def validate_saved_output(input_path: str | Path, output_path: str | Path, operation_list: object) -> dict[str, Any]:
    """Re-open source and output independently, replay expected semantics, compare.

    The validator does not receive or inspect the executor's Workbook object.
    It reloads both filesystem paths, builds a separate expected workbook from
    the original file, and compares the complete normalized workbook state.
    Formula text is compared; formulas are not recalculated by openpyxl.
    """
    normalized = validate_operation_list(operation_list)
    operations = normalized["operations"]
    source_path, output_path = Path(input_path), Path(output_path)
    if normalized["schema_version"] == "1.1" and _sha256(source_path) != normalized["source_sha256"]:
        raise DocumentOperationError("source_fingerprint_mismatch", "validation", "Operation List does not match the input file fingerprint.")
    if not output_path.is_file() or output_path.stat().st_size <= 0:
        raise DocumentOperationError("output_missing_or_empty", "validation", "Saved output is missing or empty.")
    if source_path.resolve() == output_path.resolve():
        raise DocumentOperationError("input_output_collision", "validation", "Output must not overwrite the input file.")
    try:
        with zipfile.ZipFile(output_path, "r") as archive:
            bad_member = archive.testzip()
            if bad_member is not None:
                raise DocumentOperationError("xlsx_zip_corrupt", "validation", f"Corrupt XLSX ZIP member: {bad_member}.")
    except zipfile.BadZipFile as exc:
        raise DocumentOperationError("xlsx_zip_corrupt", "validation", "Output is not a valid XLSX ZIP container.") from exc

    try:
        expected = load_workbook(source_path, data_only=False, read_only=False, keep_links=True)
        actual = load_workbook(output_path, data_only=False, read_only=False, keep_links=True)
    except Exception as exc:
        raise DocumentOperationError("xlsx_readback_failed", "validation", "openpyxl could not independently reopen the saved XLSX.") from exc
    try:
        for operation in operations:
            _reference_apply(expected, operation)
        expected_state = _workbook_state(expected)
        actual_state = _workbook_state(actual)
        difference = _first_state_difference(expected_state, actual_state)
        if difference:
            raise DocumentOperationError(
                "output_state_mismatch",
                "validation",
                "Independently reopened output differs from the ordered operations at "
                f"{difference}.",
            )
        return {
            "status": "PASS",
            "output_size": output_path.stat().st_size,
            "output_sha256": _sha256(output_path),
            "zip_valid": True,
            "openpyxl_readable": True,
            "sheets": list(actual.sheetnames),
            "operation_count": len(operations),
            "operation_ids": [operation["operation_id"] for operation in operations],
            "formula_cells": sum(1 for sheet in actual.worksheets for row in sheet.iter_rows() for cell in row if cell.data_type == "f"),
            "note": "Formula text is validated; formula results are not recalculated by openpyxl.",
        }
    finally:
        expected.close()
        actual.close()


def _reference_apply(workbook, operation: dict[str, Any]) -> None:
    """Small reference interpreter intentionally separate from XlsxAdapter."""
    target, params, kind = operation["target"], operation["parameters"], operation["type"]
    sheet = workbook[target["sheet"]]
    if kind == "insert_rows":
        row, count = target["row"], params["count"]
        prototype_row = params.get("style_from_row")
        styles = [copy.copy(sheet.cell(prototype_row, col)._style) for col in range(1, sheet.max_column + 1)] if prototype_row else []
        dim = sheet.row_dimensions[prototype_row] if prototype_row else None
        dimensions = (dim.height, dim.hidden, dim.outlineLevel, dim.collapsed) if dim else None
        sheet.insert_rows(row, amount=count)
        if prototype_row:
            for new_row in range(row, row + count):
                for col, style in enumerate(styles, 1):
                    if style is not None:
                        sheet.cell(new_row, col)._style = copy.copy(style)
                target_dim = sheet.row_dimensions[new_row]
                target_dim.height, target_dim.hidden, target_dim.outlineLevel, target_dim.collapsed = dimensions
        return

    bounds = _target_bounds(target)
    min_col, min_row, max_col, max_row = bounds
    if kind == "set_value":
        values = [[params["value"]]] if "cell" in target else params["values"]
        for row_offset, row_values in enumerate(values):
            for col_offset, typed in enumerate(row_values):
                cell = sheet.cell(min_row + row_offset, min_col + col_offset)
                number_format = cell.number_format
                cell.value = _reference_value(typed)
                if typed["type"] in {"date", "datetime"}:
                    # Match the operation contract: assigning a typed date
                    # changes the value, not the target cell's formatting.
                    cell.number_format = number_format
                if typed["type"] == "string":
                    cell.data_type = "s"
    elif kind == "set_formula":
        sheet[target["cell"]] = params["formula"]
    elif kind == "format":
        for row in sheet.iter_rows(min_row=min_row, max_row=max_row, min_col=min_col, max_col=max_col):
            for cell in row:
                cell.number_format = params["number_format"]
    elif kind == "clear":
        for row in sheet.iter_rows(min_row=min_row, max_row=max_row, min_col=min_col, max_col=max_col):
            for cell in row:
                if params["mode"] in {"values", "all"}:
                    if params["formula_policy"] == "clear" or cell.data_type != "f":
                        cell.value = None
                if params["mode"] in {"formats", "all"}:
                    cell._style = None
    elif kind == "sort":
        first = min_row + int(params["header"])
        key_col = column_index_from_string(params["key"])
        records = []
        for row_index in range(first, max_row + 1):
            snapshot = [_reference_cell(sheet.cell(row_index, col)) for col in range(min_col, max_col + 1)]
            dimension = sheet.row_dimensions[row_index]
            dim_data = (dimension.height, dimension.hidden, dimension.outlineLevel, dimension.collapsed)
            records.append((sheet.cell(row_index, key_col).value, snapshot, dim_data))
        populated = [record for record in records if record[0] is not None]
        blanks = [record for record in records if record[0] is None]
        populated.sort(key=lambda record: _reference_sort_key(record[0]), reverse=params["direction"] == "descending")
        for row_index, (_key, cells, dim_data) in zip(range(first, max_row + 1), populated + blanks):
            for col, state in enumerate(cells, min_col):
                _reference_restore_cell(sheet.cell(row_index, col), state)
            dim = sheet.row_dimensions[row_index]
            dim.height, dim.hidden, dim.outlineLevel, dim.collapsed = dim_data


def _target_bounds(target: dict[str, Any]) -> tuple[int, int, int, int]:
    if "cell" in target:
        return range_boundaries(f"{target['cell']}:{target['cell']}")
    if "range" in target:
        return range_boundaries(target["range"])
    column_data = target["column_data"]
    index = column_index_from_string(column_data["column"])
    return index, column_data["start_row"], index, column_data["end_row"]


def _reference_value(typed: dict[str, Any]):
    kind, data = typed["type"], typed["data"]
    if kind == "date":
        return date.fromisoformat(data)
    if kind == "datetime":
        return datetime.fromisoformat(data.replace("Z", "+00:00"))
    return None if kind == "null" else data


def _reference_sort_key(value):
    if isinstance(value, bool):
        return 0, int(value)
    if isinstance(value, (int, float)):
        if not math.isfinite(float(value)):
            raise DocumentOperationError("sort_value_unsupported", "validation", "Non-finite sort key.")
        return 1, float(value)
    if isinstance(value, datetime):
        return 2, value.isoformat()
    if isinstance(value, date):
        return 2, value.isoformat()
    if isinstance(value, str):
        return 3, value.casefold()
    raise DocumentOperationError("sort_value_unsupported", "validation", "Unsupported sort key type.")


def _reference_cell(cell):
    return (cell.value, cell.data_type, copy.copy(cell._style), copy.copy(cell.hyperlink), copy.copy(cell.comment))


def _reference_restore_cell(cell, state):
    cell.value, cell.data_type = state[0], state[1]
    cell._style, cell._hyperlink, cell.comment = copy.copy(state[2]), copy.copy(state[3]), copy.copy(state[4])


def _workbook_state(workbook) -> tuple[Any, ...]:
    state = []
    for sheet in workbook.worksheets:
        cells = []
        for row in sheet.iter_rows():
            for cell in row:
                style = tuple(cell._style) if cell._style else None
                if style is not None and not any(style):
                    style = None
                blank_value = cell.value is None or cell.value == ""
                if blank_value and style is None and cell.hyperlink is None and cell.comment is None:
                    continue
                # openpyxl reopens a saved empty string from a styled cell as
                # ``value=None, data_type='inlineStr'``. Normalize every blank
                # representation alike while retaining its style/format state.
                data_type = "n" if blank_value else cell.data_type
                value = cell.value
                stable_value = None
                # Excel stores dates as numeric serials. When the target has
                # no date number format, openpyxl correctly reopens the saved
                # value as a number; compare the reference workbook using that
                # same on-disk representation while leaving formatting intact.
                if isinstance(value, (date, datetime)) and not is_date_format(cell.number_format):
                    stable_value = ("xlsx-date-serial", to_excel(value, epoch=workbook.epoch))
                    data_type = "n"
                if stable_value is None:
                    stable_value = _stable_value(value, cell.number_format, workbook.epoch)
                cells.append((cell.coordinate, stable_value, data_type, style,
                              cell.number_format, getattr(cell.hyperlink, "target", None),
                              getattr(cell.hyperlink, "location", None),
                              getattr(cell.comment, "text", None), getattr(cell.comment, "author", None)))
        row_dimensions = tuple(
            (index, dim.height, dim.hidden, dim.outlineLevel, dim.collapsed)
            for index, dim in sorted(sheet.row_dimensions.items())
            if dim.height is not None or dim.hidden or dim.outlineLevel or dim.collapsed
        )
        column_dimensions = tuple(
            (key, dim.width, dim.hidden, dim.bestFit, dim.outlineLevel, dim.collapsed, dim.min, dim.max)
            for key, dim in sorted(sheet.column_dimensions.items())
            if dim.width is not None or dim.hidden or dim.bestFit or dim.outlineLevel or dim.collapsed
        )
        tables = tuple(sorted((table.displayName, table.ref) for table in sheet.tables.values()))
        state.append((sheet.title, sheet.sheet_state, tuple(cells), tuple(sorted(str(item) for item in sheet.merged_cells.ranges)),
                      row_dimensions, column_dimensions, sheet.freeze_panes.coordinate if hasattr(sheet.freeze_panes, "coordinate") else sheet.freeze_panes,
                      sheet.auto_filter.ref, tables))
    names = tuple(sorted(workbook.defined_names))
    return tuple(state), names


def _stable_value(value, number_format="General", epoch=None):
    if isinstance(value, datetime):
        # XLSX stores datetimes as floating-point day serials. openpyxl
        # round-trips those serials to millisecond precision, so compare the
        # reference value at the same representable precision as an
        # independently reopened workbook (using the workbook's date system).
        if epoch is not None:
            value = from_excel(to_excel(value, epoch=epoch), epoch=epoch)
        if value.time().isoformat() == "00:00:00" and not any(token in number_format.lower() for token in ("h", "s")):
            return ("date", value.date().isoformat())
        return ("datetime", value.isoformat())
    if isinstance(value, date):
        return ("date", value.isoformat())
    if value == "":
        # XLSX stores an empty string as an empty inline string; openpyxl reads
        # that representation back as None. They are the same blank cell.
        return ("NoneType", None)
    if isinstance(value, float):
        return ("float", value.hex())
    if isinstance(value, (str, int, bool)) or value is None:
        return (type(value).__name__, value)
    return (type(value).__name__, str(value))


def _first_state_difference(expected_state, actual_state) -> str | None:
    """Describe the first differing cell/structure without exposing cell data."""
    expected_sheets, expected_names = expected_state
    actual_sheets, actual_names = actual_state
    if expected_names != actual_names:
        return "workbook defined names (structure)"
    if len(expected_sheets) != len(actual_sheets):
        return "workbook worksheet count (structure)"
    for expected, actual in zip(expected_sheets, actual_sheets):
        title = expected[0]
        if expected[:2] != actual[:2]:
            return f"worksheet {title!r} (state)"
        expected_cells = {cell[0]: cell[1:] for cell in expected[2]}
        actual_cells = {cell[0]: cell[1:] for cell in actual[2]}
        for coordinate in sorted(set(expected_cells) | set(actual_cells)):
            left, right = expected_cells.get(coordinate), actual_cells.get(coordinate)
            if left is None and right is None:
                continue
            if left is None or right is None:
                category = "cell presence"
            elif left[1:] == right[1:] and (
                left[0] == right[0] or _same_excel_date_serial(left[0], right[0])
            ):
                continue
            elif left[1:3] != right[1:3]:
                category = "cell value/type"
            elif left[3:5] != right[3:5]:
                category = "cell style/number format"
            else:
                category = "cell annotation"
            return f"{title}!{coordinate} ({category})"
        if expected[3:] != actual[3:]:
            return f"worksheet {title!r} (dimensions or structure)"
    return None


def _same_excel_date_serial(left, right) -> bool:
    """Compare a date written to a General cell with its numeric XLSX serial."""
    def number(value):
        if not isinstance(value, tuple) or len(value) != 2:
            return None
        kind, raw = value
        if kind == "xlsx-date-serial":
            return float(raw)
        if kind == "float":
            return float.fromhex(raw)
        if kind == "int" and type(raw) is int:
            return float(raw)
        return None

    expected, actual = number(left), number(right)
    if expected is None or actual is None:
        expected, actual = number(right), number(left)
    return expected is not None and actual is not None and abs(expected - actual) <= 1e-10


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
