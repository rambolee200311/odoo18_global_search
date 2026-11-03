"""Conservative XLSX operations implemented with openpyxl."""

from __future__ import annotations

import copy
import math
import re
import warnings
from datetime import date, datetime
from pathlib import Path
from typing import Any

from openpyxl import load_workbook
from openpyxl.cell.cell import MergedCell
from openpyxl.utils.cell import column_index_from_string, get_column_letter, range_boundaries

from .errors import DocumentOperationError

_MAX_ROW = 1_048_576
_MAX_COLUMN = 16_384
_CELL_RE = re.compile(r"^[A-Z]{1,3}[1-9][0-9]*$")
_RANGE_RE = re.compile(r"^[A-Z]{1,3}[1-9][0-9]*:[A-Z]{1,3}[1-9][0-9]*$")


class XlsxAdapter:
    """Small adapter for a deliberately bounded set of XLSX operations."""

    @staticmethod
    def load(path: str | Path):
        path = Path(path)
        if path.suffix.lower() != ".xlsx":
            raise DocumentOperationError("unsupported_file_type", "adapter", "Only .xlsx files are supported.")
        if not path.is_file() or path.stat().st_size == 0:
            raise DocumentOperationError("input_file_missing_or_empty", "adapter", "Input XLSX is missing or empty.")
        try:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                workbook = load_workbook(path, data_only=False, read_only=False, keep_links=True)
        except Exception as exc:
            raise DocumentOperationError("xlsx_load_failed", "adapter", "openpyxl could not load the input XLSX.") from exc
        # openpyxl can emit ResourceWarning for file handles leaked by callers
        # elsewhere in the process (for example a workbook opened for a
        # separate inspection and not closed yet). That warning says nothing
        # about this input file's structure. Still reject every other warning:
        # openpyxl uses UserWarning for features it cannot preserve on save.
        structure_warnings = [warning for warning in caught if not issubclass(warning.category, ResourceWarning)]
        if structure_warnings:
            workbook.close()
            details = "; ".join(
                f"{warning.category.__name__}: {warning.message}" for warning in structure_warnings
            )
            raise DocumentOperationError(
                "xlsx_structure_warning",
                "adapter",
                f"openpyxl reported a structure warning; refusing a potentially lossy save. {details}",
            )
        return workbook

    def preflight(self, workbook, operation: dict[str, Any]) -> None:
        operation_id = operation["operation_id"]
        target = operation["target"]
        sheet_name = target["sheet"]
        if sheet_name not in workbook.sheetnames:
            raise self._error("sheet_not_found", "The target worksheet does not exist.", operation_id)
        sheet = workbook[sheet_name]
        kind = operation["type"]
        if kind == "insert_rows":
            self._preflight_insert(workbook, sheet, operation)
            return

        bounds = self._bounds(target, operation_id)
        min_col, min_row, max_col, max_row = bounds
        if min_row < 1 or min_col < 1 or max_row > _MAX_ROW or max_col > _MAX_COLUMN:
            raise self._error("target_out_of_bounds", "Target exceeds XLSX worksheet limits.", operation_id)
        self._reject_merged_intersection(sheet, bounds, operation, operation_id)

        if kind == "set_value":
            self._preflight_set(sheet, operation, bounds)
        elif kind == "set_formula":
            if "cell" not in target:
                raise self._error("formula_target_invalid", "Formula operations require one cell target.", operation["operation_id"])
        elif kind == "sort":
            self._preflight_sort(workbook, sheet, operation, bounds)
        elif kind == "clear":
            self._preflight_clear(sheet, operation, bounds)
        elif kind == "format":
            self._preflight_format(operation)
        else:  # The schema validator should make this unreachable.
            raise self._error("unknown_operation", "Unknown operation type.", operation_id)

    def apply(self, workbook, operation: dict[str, Any]) -> dict[str, Any]:
        operation_id = operation["operation_id"]
        try:
            self.preflight(workbook, operation)
        except DocumentOperationError as exc:
            if exc.operation_id is None:
                exc.operation_id = operation_id
            raise
        except Exception as exc:
            raise DocumentOperationError(
                "operation_preflight_failed",
                "preflight",
                "The operation target or workbook structure could not be preflighted.",
                operation_id,
            ) from exc
        target = operation["target"]
        sheet = workbook[target["sheet"]]
        kind = operation["type"]
        parameters = operation["parameters"]
        try:
            if kind == "insert_rows":
                return self._insert_rows(workbook, sheet, operation)
            bounds = self._bounds(target, operation_id)
            if kind == "set_value":
                self._set_value(sheet, operation, bounds)
            elif kind == "set_formula":
                sheet[target["cell"]] = parameters["formula"]
            elif kind == "sort":
                self._sort(sheet, operation, bounds)
            elif kind == "format":
                for row in sheet.iter_rows(min_row=bounds[1], max_row=bounds[3], min_col=bounds[0], max_col=bounds[2]):
                    for cell in row:
                        cell.number_format = parameters["number_format"]
            elif kind == "clear":
                self._clear(sheet, operation, bounds)
        except DocumentOperationError as exc:
            if exc.operation_id is None:
                exc.operation_id = operation_id
            raise
        except Exception as exc:
            raise self._error(
                "operation_execution_failed",
                "The operation could not be applied to the workbook.",
                operation_id,
            ) from exc
        return {
            "operation_id": operation_id,
            "status": "applied_in_memory",
            "target": copy.deepcopy(target),
            "result": self._result_summary(sheet, operation, bounds),
        }

    @staticmethod
    def _error(code: str, message: str, operation_id: str | None) -> DocumentOperationError:
        return DocumentOperationError(code, "execution", message, operation_id)

    def _bounds(self, target: dict[str, Any], operation_id: str) -> tuple[int, int, int, int]:
        if "cell" in target:
            address = target["cell"]
            if not _CELL_RE.fullmatch(address):
                raise self._error("invalid_cell_address", "Cell address is invalid.", operation_id)
            return (*range_boundaries(address + ":" + address)[:2], *range_boundaries(address + ":" + address)[2:])
        if "range" in target:
            address = target["range"]
            if not _RANGE_RE.fullmatch(address):
                raise self._error("invalid_range_address", "Range address is invalid.", operation_id)
            try:
                bounds = range_boundaries(address)
            except ValueError as exc:
                raise self._error("invalid_range_address", "Range address is invalid.", operation_id) from exc
            min_col, min_row, max_col, max_row = bounds
            if min_col > max_col or min_row > max_row:
                raise self._error("invalid_range_address", "Range endpoints are reversed.", operation_id)
            return bounds
        column_data = target.get("column_data")
        if isinstance(column_data, dict):
            column = column_data["column"]
            start_row, end_row = column_data["start_row"], column_data["end_row"]
            if start_row > end_row:
                raise self._error("invalid_column_data_range", "Column data start_row must not exceed end_row.", operation_id)
            index = column_index_from_string(column)
            return (index, start_row, index, end_row)
        raise self._error("invalid_target", "Operation target is invalid.", operation_id)

    def _reject_merged_intersection(self, sheet, bounds, operation, operation_id):
        min_col, min_row, max_col, max_row = bounds
        for merged in sheet.merged_cells.ranges:
            m_min_col, m_min_row, m_max_col, m_max_row = range_boundaries(str(merged))
            if not (max_col < m_min_col or min_col > m_max_col or max_row < m_min_row or min_row > m_max_row):
                single_anchor = (
                    min_col == max_col == m_min_col
                    and min_row == max_row == m_min_row
                )
                kind = operation["type"]
                value_only_clear = (
                    kind == "clear"
                    and operation["parameters"].get("mode") == "values"
                )
                if single_anchor and (kind in {"set_value", "set_formula"} or value_only_clear):
                    continue
                raise self._error(
                    "merged_range_unsupported",
                    f"Target intersects merged range {merged}; only single-cell value operations at its top-left anchor are supported.",
                    operation_id,
                )

    def _preflight_set(self, sheet, operation, bounds):
        target, parameters = operation["target"], operation["parameters"]
        min_col, min_row, max_col, max_row = bounds
        if "cell" in target:
            cells = [(min_row, min_col)]
            if "values" in parameters:
                raise self._error("cell_value_shape_mismatch", "A cell target requires one typed value.", operation["operation_id"])
        else:
            rows = parameters.get("values")
            if rows is None:
                raise self._error("range_value_shape_required", "A range target requires a values matrix.", operation["operation_id"])
            if len(rows) != max_row - min_row + 1 or any(len(row) != max_col - min_col + 1 for row in rows):
                raise self._error("range_value_shape_mismatch", "Values matrix dimensions must match the target range.", operation["operation_id"])
            cells = [(row, col) for row in range(min_row, max_row + 1) for col in range(min_col, max_col + 1)]
        if not parameters.get("overwrite_formula", False):
            for row, col in cells:
                cell = sheet.cell(row, col)
                if cell.data_type == "f":
                    raise self._error("formula_overwrite_requires_explicit_opt_in", "Target contains a formula; set overwrite_formula=true to replace it with a literal.", operation["operation_id"])

    def _preflight_sort(self, workbook, sheet, operation, bounds):
        min_col, min_row, max_col, max_row = bounds
        params = operation["parameters"]
        key_col = column_index_from_string(params["key"])
        if not min_col <= key_col <= max_col:
            raise self._error("sort_key_outside_range", "Sort key must be a column inside the target range.", operation["operation_id"])
        first_data_row = min_row + (1 if params["header"] else 0)
        if first_data_row > max_row:
            raise self._error("sort_range_has_no_data", "Sort range has no data rows.", operation["operation_id"])
        if not params["header"] and min_row in self._header_rows(sheet):
            raise self._error("header_protection", "The range starts with a detected header; set header=true to preserve it.", operation["operation_id"])
        for row in range(first_data_row, max_row + 1):
            for col in range(min_col, max_col + 1):
                cell = sheet.cell(row, col)
                if cell.data_type == "f":
                    raise self._error("sort_formula_unsupported", "Sorting a range containing formulas is not supported.", operation["operation_id"])
            for col in list(range(1, min_col)) + list(range(max_col + 1, sheet.max_column + 1)):
                if sheet.cell(row, col).value is not None:
                    raise self._error("sort_partial_row", "Sort range omits populated cells from a record row.", operation["operation_id"])

    def _preflight_clear(self, sheet, operation, bounds):
        min_col, min_row, max_col, max_row = bounds
        header_rows = self._header_rows(sheet)
        intersects_header = any(min_row <= row <= max_row for row in header_rows)
        if intersects_header and not operation["parameters"]["include_header"]:
            raise self._error("header_protection", "Clear target includes a detected header; set include_header=true to clear it explicitly.", operation["operation_id"])

    def _preflight_format(self, operation):
        value = operation["parameters"]["number_format"]
        if not value or any(ord(char) < 32 for char in value):
            raise self._error("invalid_number_format", "number_format is empty or contains control characters.", operation["operation_id"])

    def _preflight_insert(self, workbook, sheet, operation):
        row = operation["target"]["row"]
        count = operation["parameters"]["count"]
        operation_id = operation["operation_id"]
        if row + count - 1 > _MAX_ROW:
            raise self._error("insert_rows_out_of_bounds", "Inserted rows exceed worksheet limits.", operation_id)
        if row > sheet.max_row + 1:
            raise self._error("insert_rows_gap", "Rows may only be inserted within the used sheet or at its next row.", operation_id)
        style_row = operation["parameters"].get("style_from_row")
        if style_row is not None and style_row > max(sheet.max_row, 1):
            raise self._error("style_source_row_missing", "style_from_row does not exist in the current worksheet.", operation_id)
        # Appending after the current used range shifts no existing references.
        # Mid-sheet insertion is rejected whenever openpyxl cannot guarantee
        # that workbook-level references and objects are updated.
        if row <= sheet.max_row:
            if any(cell.data_type == "f" for ws in workbook.worksheets for line in ws.iter_rows() for cell in line):
                raise self._error("insert_rows_formula_reference_risk", "Mid-sheet insertion with formulas is not guaranteed safe.", operation_id)
            if list(workbook.defined_names):
                raise self._error("insert_rows_defined_name_risk", "Mid-sheet insertion with defined names is not guaranteed safe.", operation_id)
            for merged in sheet.merged_cells.ranges:
                if range_boundaries(str(merged))[3] >= row:
                    raise self._error("insert_rows_merged_range_risk", f"Mid-sheet insertion may affect merged range {merged}.", operation_id)
            for table in sheet.tables.values():
                try:
                    table_min_col, table_min_row, table_max_col, table_max_row = range_boundaries(table.ref)
                except ValueError:
                    raise self._error("insert_rows_table_ref_invalid", "An Excel Table has an invalid reference.", operation_id)
                if table_max_row >= row:
                    raise self._error("insert_rows_table_risk", f"Mid-sheet insertion may affect Excel Table {table.displayName}.", operation_id)
            if sheet.auto_filter.ref:
                _min_col, _min_row, _max_col, filter_max_row = range_boundaries(sheet.auto_filter.ref)
                if filter_max_row >= row:
                    raise self._error("insert_rows_filter_risk", "Mid-sheet insertion may affect an AutoFilter range.", operation_id)
            if getattr(sheet, "_charts", None) or getattr(sheet, "_images", None):
                raise self._error("insert_rows_drawing_risk", "Mid-sheet insertion with drawings or charts is not guaranteed safe.", operation_id)
            if getattr(sheet, "conditional_formatting", None) and len(sheet.conditional_formatting):
                raise self._error("insert_rows_conditional_format_risk", "Mid-sheet insertion with conditional formatting is not guaranteed safe.", operation_id)
            validations = getattr(getattr(sheet, "data_validations", None), "dataValidation", [])
            if validations:
                raise self._error("insert_rows_validation_risk", "Mid-sheet insertion with data validation is not guaranteed safe.", operation_id)

    def _insert_rows(self, workbook, sheet, operation):
        target, params = operation["target"], operation["parameters"]
        row, count = target["row"], params["count"]
        style_row = params.get("style_from_row")
        style_snapshot = None
        dimension_snapshot = None
        if style_row is not None:
            style_snapshot = [copy.copy(sheet.cell(style_row, col)._style) for col in range(1, sheet.max_column + 1)]
            dim = sheet.row_dimensions[style_row]
            dimension_snapshot = (dim.height, dim.hidden, dim.outlineLevel, dim.collapsed)
        sheet.insert_rows(row, amount=count)
        if style_snapshot is not None:
            for new_row in range(row, row + count):
                for col, style in enumerate(style_snapshot, 1):
                    if style is not None:
                        sheet.cell(new_row, col)._style = copy.copy(style)
                dim = sheet.row_dimensions[new_row]
                dim.height, dim.hidden, dim.outlineLevel, dim.collapsed = dimension_snapshot
        return {
            "operation_id": operation["operation_id"],
            "status": "applied_in_memory",
            "target": copy.deepcopy(target),
            "result": {"inserted_rows": count, "first_inserted_row": row, "last_inserted_row": row + count - 1, "style_from_row": style_row},
        }

    def _set_value(self, sheet, operation, bounds):
        target, params = operation["target"], operation["parameters"]
        min_col, min_row, max_col, max_row = bounds
        if "cell" in target:
            values = [[params["value"]]]
        else:
            values = params["values"]
        for row_offset, row_values in enumerate(values):
            for col_offset, typed_value in enumerate(row_values):
                cell = sheet.cell(min_row + row_offset, min_col + col_offset)
                if cell.data_type == "f" and not params.get("overwrite_formula", False):
                    raise self._error("formula_overwrite_requires_explicit_opt_in", "Target contains a formula.", operation["operation_id"])
                data = self._python_value(typed_value)
                cell.value = data
                if typed_value["type"] == "string":
                    # A leading '=' is data in set_value; formulas require a
                    # distinct future operation and are never inferred.
                    cell.data_type = "s"

    def _clear(self, sheet, operation, bounds):
        params = operation["parameters"]
        for row in sheet.iter_rows(min_row=bounds[1], max_row=bounds[3], min_col=bounds[0], max_col=bounds[2]):
            for cell in row:
                if isinstance(cell, MergedCell):
                    raise self._error("merged_range_unsupported", "Cannot clear a non-anchor merged cell.", operation["operation_id"])
                if params["mode"] in {"values", "all"}:
                    if params["formula_policy"] == "clear" or cell.data_type != "f":
                        cell.value = None
                if params["mode"] in {"formats", "all"}:
                    cell._style = None

    def _sort(self, sheet, operation, bounds):
        min_col, min_row, max_col, max_row = bounds
        params = operation["parameters"]
        first_row = min_row + (1 if params["header"] else 0)
        key_col = column_index_from_string(params["key"])
        records = []
        for row_index in range(first_row, max_row + 1):
            values = [self._snapshot_cell(sheet.cell(row_index, col)) for col in range(min_col, max_col + 1)]
            key = sheet.cell(row_index, key_col).value
            records.append((key, values, self._snapshot_dimension(sheet, row_index)))
        nonblank = [record for record in records if record[0] is not None]
        blank = [record for record in records if record[0] is None]
        nonblank.sort(key=lambda record: self._sort_key(record[0]), reverse=params["direction"] == "descending")
        ordered = nonblank + blank
        for row_index, (_key, values, dimension) in zip(range(first_row, max_row + 1), ordered):
            for col_index, snapshot in enumerate(values, min_col):
                self._restore_cell(sheet.cell(row_index, col_index), snapshot)
            self._restore_dimension(sheet, row_index, dimension)

    @staticmethod
    def _snapshot_cell(cell):
        return {
            "value": cell.value,
            "data_type": cell.data_type,
            "style": copy.copy(cell._style),
            "hyperlink": copy.copy(cell.hyperlink),
            "comment": copy.copy(cell.comment),
        }

    @staticmethod
    def _restore_cell(cell, snapshot):
        cell.value = snapshot["value"]
        cell.data_type = snapshot["data_type"]
        cell._style = copy.copy(snapshot["style"])
        cell._hyperlink = copy.copy(snapshot["hyperlink"])
        cell.comment = copy.copy(snapshot["comment"])

    @staticmethod
    def _snapshot_dimension(sheet, row):
        dimension = sheet.row_dimensions[row]
        return (dimension.height, dimension.hidden, dimension.outlineLevel, dimension.collapsed)

    @staticmethod
    def _restore_dimension(sheet, row, snapshot):
        dimension = sheet.row_dimensions[row]
        dimension.height, dimension.hidden, dimension.outlineLevel, dimension.collapsed = snapshot

    @staticmethod
    def _sort_key(value):
        if isinstance(value, bool):
            return (0, int(value))
        if isinstance(value, (int, float)):
            if not math.isfinite(float(value)):
                raise DocumentOperationError("sort_value_unsupported", "execution", "Non-finite numeric sort keys are unsupported.")
            return (1, float(value))
        if isinstance(value, datetime):
            return (2, value.isoformat())
        if isinstance(value, date):
            return (2, value.isoformat())
        if isinstance(value, str):
            return (3, value.casefold())
        raise DocumentOperationError("sort_value_unsupported", "execution", f"Unsupported sort key type: {type(value).__name__}.")

    @staticmethod
    def _python_value(typed_value):
        kind, data = typed_value["type"], typed_value["data"]
        if kind == "date":
            return date.fromisoformat(data)
        if kind == "datetime":
            return datetime.fromisoformat(data.replace("Z", "+00:00"))
        if kind == "null":
            return None
        return data

    @staticmethod
    def _header_rows(sheet) -> set[int]:
        rows: set[int] = set()
        for table in sheet.tables.values():
            try:
                _min_col, min_row, _max_col, _max_row = range_boundaries(table.ref)
                rows.update(range(min_row, min_row + (table.headerRowCount or 1)))
            except ValueError:
                continue
        for row_index in range(1, max(sheet.max_row, 1)):
            nonempty = [cell.value for cell in sheet[row_index] if cell.value is not None]
            if len(nonempty) < 2 or any(not isinstance(value, str) or not value.strip() for value in nonempty):
                continue
            following = sheet[row_index + 1]
            if any(cell.value is not None or cell.has_style for cell in following):
                rows.add(row_index)
        return rows

    def _result_summary(self, sheet, operation, bounds):
        kind = operation["type"]
        if kind == "sort":
            min_col, min_row, max_col, max_row = bounds
            first = min_row + int(operation["parameters"]["header"])
            key_col = column_index_from_string(operation["parameters"]["key"])
            return {"rows": max_row - first + 1, "key": operation["parameters"]["key"], "direction": operation["parameters"]["direction"], "values": [sheet.cell(row, key_col).value for row in range(first, max_row + 1)]}
        if kind == "format":
            return {"number_format": operation["parameters"]["number_format"], "cell_count": (bounds[2] - bounds[0] + 1) * (bounds[3] - bounds[1] + 1)}
        if kind == "clear":
            return {"mode": operation["parameters"]["mode"], "target": operation["target"]}
        if kind == "set_value":
            return {"cell_count": (bounds[2] - bounds[0] + 1) * (bounds[3] - bounds[1] + 1)}
        return {}
