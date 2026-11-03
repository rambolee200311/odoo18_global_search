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
    operations = validate_operation_list(operation_list)["operations"]
    source_path, output_path = Path(input_path), Path(output_path)
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
        if expected_state != actual_state:
            raise DocumentOperationError(
                "output_state_mismatch",
                "validation",
                "Independently reopened output differs from the state required by the ordered operations.",
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
                cell.value = _reference_value(typed)
                if typed["type"] == "string":
                    cell.data_type = "s"
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
                data_type = "n" if cell.value == "" else cell.data_type
                cells.append((cell.coordinate, _stable_value(cell.value, cell.number_format), data_type, style,
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


def _stable_value(value, number_format="General"):
    if isinstance(value, datetime):
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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
