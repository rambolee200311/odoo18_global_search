from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import date, datetime
from pathlib import Path

import pytest
from openpyxl import Workbook, load_workbook
from openpyxl.styles import PatternFill
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.utils.datetime import from_excel

from office_document_operations import DocumentOperationEngine, validate_operation_list, validate_saved_output


HEADERS = [f"Field {column}" for column in "ABCDEFGHIJKLM"]


def _typed(value):
    if value is None:
        return {"type": "null", "data": None}
    if isinstance(value, bool):
        return {"type": "boolean", "data": value}
    if isinstance(value, (int, float)):
        return {"type": "number", "data": value}
    if isinstance(value, date) and not isinstance(value, datetime):
        return {"type": "date", "data": value.isoformat()}
    if isinstance(value, datetime):
        return {"type": "datetime", "data": value.isoformat()}
    return {"type": "string", "data": value}


def _row(order, supplier, quantity, when, amount, flag, m_value):
    values = [order, supplier, quantity, when, amount, flag, "x", "y", "z", "note", None, None, m_value]
    return [_typed(value) for value in values]


def _fixture(path: Path):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Orders"
    sheet.append(HEADERS)
    sheet.append(["OLD-002", "Existing supplier", 0, date(2026, 11, 1), 12.5, False, "x", "y", "z", "kept", None, None, "keep M2"])
    sheet.append(["OLD-003", "Existing supplier", 7, date(2026, 11, 2), 13.75, True, "x", "y", "z", "kept", None, None, "keep M3"])
    sheet.append(["OLD-004", "Existing supplier", 2, date(2026, 11, 3), 14.25, False, "x", "y", "z", "kept", None, None, "keep M4"])
    fill = PatternFill(fill_type="solid", fgColor="D9EAF7")
    for row in range(4, 8):
        for col in range(1, 14):
            sheet.cell(row, col).fill = fill
    sheet["P1"] = "PROTECTED OUTSIDE OPERATION TARGETS"
    sheet["P1"].fill = PatternFill(fill_type="solid", fgColor="FFFF00")
    workbook.save(path)
    workbook.close()


def _main_operations():
    rows = [
        _row("SO-103", "Vendor C", 3, date(2026, 10, 4), 30.55, False, "erase-c"),
        _row("SO-101", "Vendor A", 0, date(2026, 10, 2), 10.05, True, "erase-a"),
        _row("SO-105", "Vendor E", 5, date(2026, 10, 6), 50.15, False, "erase-e"),
        _row("SO-102", "Vendor B", 2, date(2026, 10, 3), 20.25, False, "erase-b"),
        _row("SO-104", "Vendor D", 4, date(2026, 10, 5), 40.45, True, "erase-d"),
    ]
    return {
        "schema_version": "1.0",
        "operations": [
            {
                "operation_id": "rows-1", "type": "insert_rows",
                "target": {"sheet": "Orders", "row": 5},
                "parameters": {"count": 5, "style_from_row": 4},
            },
            {
                "operation_id": "values-1", "type": "set_value",
                "target": {"sheet": "Orders", "range": "A5:M9"},
                "parameters": {"values": rows},
            },
            {
                "operation_id": "sort-1", "type": "sort",
                "target": {"sheet": "Orders", "range": "A5:M9"},
                "parameters": {"key": "A", "direction": "ascending", "header": False},
            },
            {
                "operation_id": "format-1", "type": "format",
                "target": {"sheet": "Orders", "column_data": {"column": "E", "start_row": 5, "end_row": 9}},
                "parameters": {"number_format": "0.0"},
            },
            {
                "operation_id": "clear-1", "type": "clear",
                "target": {"sheet": "Orders", "range": "M5:M9"},
                "parameters": {"mode": "values"},
            },
        ],
    }


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_main_operation_sequence_saves_and_independently_validates_real_xlsx(tmp_path):
    source = tmp_path / "operations_source.xlsx"
    output = tmp_path / "operations_output.xlsx"
    _fixture(source)
    source_hash = _digest(source)

    report = DocumentOperationEngine().execute(source, output, _main_operations()).as_dict()

    assert report["status"] == "PASS", report
    assert report["output"]["size"] > 0
    assert report["output"]["validation"]["zip_valid"] is True
    assert report["output"]["validation"]["openpyxl_readable"] is True
    assert report["output"]["validation"]["operation_count"] == 5
    assert _digest(source) == source_hash
    assert [item["status"] for item in report["operations"]] == ["verified"] * 5

    # This is a second independent read after the Engine's own Validator pass.
    workbook = load_workbook(output, data_only=False)
    try:
        sheet = workbook["Orders"]
        assert [sheet.cell(1, col).value for col in range(1, 14)] == HEADERS
        assert [sheet.cell(row, 1).value for row in range(5, 10)] == [f"SO-10{i}" for i in range(1, 6)]
        assert [sheet.cell(row, 2).value for row in range(5, 10)] == ["Vendor A", "Vendor B", "Vendor C", "Vendor D", "Vendor E"]
        assert [sheet.cell(row, 5).value for row in range(5, 10)] == [10.05, 20.25, 30.55, 40.45, 50.15]
        assert all(sheet.cell(row, 5).number_format == "0.0" for row in range(5, 10))
        assert all(sheet.cell(row, 13).value is None for row in range(5, 10))
        assert sheet["C6"].value == 2
        assert sheet["C2"].value == 0 and sheet["C2"].value is not None
        assert sheet["F2"].value is False and sheet["F2"].value is not None
        assert sheet["D2"].value.date() == date(2026, 11, 1)
        assert sheet["M2"].value == "keep M2" and sheet["M3"].value == "keep M3"
        assert sheet["P1"].value == "PROTECTED OUTSIDE OPERATION TARGETS"
        assert sheet["P1"].fill.fgColor.rgb.endswith("FFFF00")
        assert sheet["E5"].fill.fgColor.rgb.endswith("D9EAF7")
    finally:
        workbook.close()


def test_tail_row_append_needs_no_sum_row_and_preserves_source(tmp_path):
    source, output = tmp_path / "tail.xlsx", tmp_path / "tail-output.xlsx"
    _fixture(source)
    before = _digest(source)
    operations = {"schema_version": "1.0", "operations": [
        {"operation_id": "append", "type": "insert_rows", "target": {"sheet": "Orders", "row": 8}, "parameters": {"count": 1, "style_from_row": 7}},
        {"operation_id": "append-value", "type": "set_value", "target": {"sheet": "Orders", "range": "A8:B8"}, "parameters": {"values": [_row("SO-106", "Vendor F", 1, date(2026, 10, 7), 60.0, False, None)[:2]]}},
    ]}
    report = DocumentOperationEngine().execute(source, output, operations).as_dict()
    assert report["status"] == "PASS", report
    assert _digest(source) == before
    workbook = load_workbook(output)
    try:
        assert workbook["Orders"]["A8"].value == "SO-106"
        assert workbook["Orders"]["B8"].value == "Vendor F"
    finally:
        workbook.close()


@pytest.mark.parametrize(
    "document",
    [
        {"schema_version": "2.0", "operations": [{"operation_id": "x", "type": "clear", "target": {"sheet": "S", "range": "A1:A1"}, "parameters": {"mode": "values"}}]},
        {"schema_version": "1.0", "operations": [{"operation_id": "x", "type": "merge_cells", "target": {}, "parameters": {}}]},
        {"schema_version": "1.0", "operations": [{"operation_id": "x", "type": "format", "target": {"sheet": "S", "range": "A1:A2"}, "parameters": {}}]},
        {"schema_version": "1.0", "operations": [{"operation_id": "x", "type": "clear", "target": {"sheet": "S", "range": "A1:A2"}, "parameters": {"mode": "values", "unknown": True}}]},
    ],
)
def test_schema_rejects_version_unknown_type_missing_parameters_and_unknown_keys(document):
    with pytest.raises(Exception):
        validate_operation_list(document)


def test_schema_rejects_duplicate_operation_ids():
    operation = {"operation_id": "same", "type": "insert_rows", "target": {"sheet": "S", "row": 1}, "parameters": {"count": 1}}
    with pytest.raises(Exception, match="unique"):
        validate_operation_list({"schema_version": "1.0", "operations": [operation, operation]})


@pytest.mark.parametrize("operation", [
    {"operation_id": "sheet", "type": "clear", "target": {"sheet": "Missing", "range": "A1:A2"}, "parameters": {"mode": "values"}},
    {"operation_id": "range", "type": "clear", "target": {"sheet": "Orders", "range": "A2:A1"}, "parameters": {"mode": "values"}},
])
def test_missing_sheet_and_invalid_range_return_structured_failure_without_output(tmp_path, operation):
    source, output = tmp_path / "in.xlsx", tmp_path / "out.xlsx"
    _fixture(source)
    before = _digest(source)
    report = DocumentOperationEngine().execute(source, output, {"schema_version": "1.0", "operations": [operation]}).as_dict()
    assert report["status"] == "FAIL"
    assert report["error"]["error_code"] in {"sheet_not_found", "invalid_range_address", "invalid_range_address"}
    assert not output.exists()
    assert _digest(source) == before


def test_clear_header_requires_explicit_opt_in(tmp_path):
    source, output = tmp_path / "in.xlsx", tmp_path / "out.xlsx"
    _fixture(source)
    operation = {"operation_id": "clear-head", "type": "clear", "target": {"sheet": "Orders", "range": "A1:M1"}, "parameters": {"mode": "values"}}
    report = DocumentOperationEngine().execute(source, output, {"schema_version": "1.0", "operations": [operation]}).as_dict()
    assert report["status"] == "FAIL"
    assert report["error"]["error_code"] == "header_protection"
    assert not output.exists()


def test_set_value_distinguishes_zero_false_null_and_formula_looking_text(tmp_path):
    source, output = tmp_path / "in.xlsx", tmp_path / "out.xlsx"
    _fixture(source)
    operation = {
        "schema_version": "1.0",
        "operations": [
            {"operation_id": "zero", "type": "set_value", "target": {"sheet": "Orders", "cell": "A15"}, "parameters": {"value": _typed(0)}},
            {"operation_id": "false", "type": "set_value", "target": {"sheet": "Orders", "cell": "B15"}, "parameters": {"value": _typed(False)}},
            {"operation_id": "null", "type": "set_value", "target": {"sheet": "Orders", "cell": "C15"}, "parameters": {"value": _typed(None)}},
            {"operation_id": "literal-formula", "type": "set_value", "target": {"sheet": "Orders", "cell": "D15"}, "parameters": {"value": _typed("=1+1")}},
        ],
    }
    report = DocumentOperationEngine().execute(source, output, operation).as_dict()
    assert report["status"] == "PASS", report
    workbook = load_workbook(output, data_only=False)
    try:
        sheet = workbook["Orders"]
        assert sheet["A15"].value == 0 and sheet["A15"].value is not None
        assert sheet["B15"].value is False and sheet["B15"].value is not None
        assert sheet["C15"].value is None
        assert sheet["D15"].value == "=1+1" and sheet["D15"].data_type == "s"
    finally:
        workbook.close()


def test_set_empty_string_roundtrips_as_blank_cell(tmp_path):
    source, output = tmp_path / "empty-string.xlsx", tmp_path / "empty-string-output.xlsx"
    _fixture(source)
    operation = {"schema_version": "1.0", "operations": [{
        "operation_id": "empty-string",
        "type": "set_value",
        "target": {"sheet": "Orders", "cell": "A15"},
        "parameters": {"value": _typed("")},
    }]}
    report = DocumentOperationEngine().execute(source, output, operation).as_dict()
    assert report["status"] == "PASS", report
    workbook = load_workbook(output, data_only=False)
    try:
        assert workbook["Orders"]["A15"].value is None
    finally:
        workbook.close()


def test_datetime_write_is_verified_at_xlsx_millisecond_precision(tmp_path):
    source, output = tmp_path / "datetime-precision.xlsx", tmp_path / "datetime-precision-output.xlsx"
    _fixture(source)
    requested = datetime(2026, 11, 3, 12, 30, 0, 123456)
    operations = {
        "schema_version": "1.0",
        "operations": [{
            "operation_id": "datetime-precision",
            "type": "set_value",
            "target": {"sheet": "Orders", "cell": "D15"},
            "parameters": {"value": _typed(requested)},
        }],
    }

    report = DocumentOperationEngine().execute(source, output, operations).as_dict()

    assert report["status"] == "PASS", report
    workbook = load_workbook(output, data_only=False)
    try:
        # The fixture's D column uses General formatting, so the stored date
        # is a numeric serial. Recovering it with the workbook epoch shows the
        # millisecond precision available through an XLSX readback.
        value = workbook["Orders"]["D15"].value
        assert isinstance(value, (int, float))
        assert from_excel(value, epoch=workbook.epoch) == datetime(2026, 11, 3, 12, 30, 0, 123000)
    finally:
        workbook.close()


def test_styled_empty_string_roundtrips_as_blank_and_preserves_style(tmp_path):
    source, output = tmp_path / "styled-empty-string.xlsx", tmp_path / "styled-empty-string-output.xlsx"
    _fixture(source)
    workbook = load_workbook(source)
    workbook["Orders"]["A15"].fill = PatternFill(fill_type="solid", fgColor="D9EAF7")
    workbook.save(source)
    workbook.close()
    operation = {"schema_version": "1.0", "operations": [{
        "operation_id": "styled-empty-string", "type": "set_value",
        "target": {"sheet": "Orders", "cell": "A15"},
        "parameters": {"value": _typed("")},
    }]}

    report = DocumentOperationEngine().execute(source, output, operation).as_dict()

    assert report["status"] == "PASS", report
    result = load_workbook(output, data_only=False)
    try:
        cell = result["Orders"]["A15"]
        assert cell.value is None
        assert cell.fill.fgColor.rgb.endswith("D9EAF7")
    finally:
        result.close()


@pytest.mark.parametrize("operation", [
    {"operation_id": "merged-anchor-set", "type": "set_value",
     "target": {"sheet": "Orders", "cell": "E17"},
     "parameters": {"value": _typed("updated")}},
    {"operation_id": "merged-anchor-clear", "type": "clear",
     "target": {"sheet": "Orders", "range": "E17:E17"},
     "parameters": {"mode": "values", "formula_policy": "clear"}},
])
def test_merged_anchor_cell_value_operations_are_supported(tmp_path, operation):
    source, output = tmp_path / "merged.xlsx", tmp_path / "merged-output.xlsx"
    _fixture(source)
    workbook = load_workbook(source)
    sheet = workbook["Orders"]
    sheet.merge_cells("E17:H17")
    sheet["E17"] = "old value"
    workbook.save(source)
    workbook.close()

    report = DocumentOperationEngine().execute(
        source, output, {"schema_version": "1.0", "operations": [operation]}
    ).as_dict()

    assert report["status"] == "PASS", report
    result = load_workbook(output, data_only=False)
    try:
        expected = "updated" if operation["type"] == "set_value" else None
        assert result["Orders"]["E17"].value == expected
        assert "E17:H17" in {str(item) for item in result["Orders"].merged_cells.ranges}
    finally:
        result.close()


@pytest.mark.parametrize("target", [
    {"sheet": "Orders", "range": "F17:F17"},
    {"sheet": "Orders", "range": "E17:H17"},
    {"sheet": "Orders", "range": "D17:E17"},
])
def test_merged_non_anchor_or_multi_cell_targets_remain_rejected(tmp_path, target):
    source, output = tmp_path / "merged-reject.xlsx", tmp_path / "merged-reject-output.xlsx"
    _fixture(source)
    workbook = load_workbook(source)
    workbook["Orders"].merge_cells("E17:H17")
    workbook.save(source)
    workbook.close()
    operation = {"operation_id": "merged-invalid", "type": "clear", "target": target,
                 "parameters": {"mode": "values"}}

    report = DocumentOperationEngine().execute(
        source, output, {"schema_version": "1.0", "operations": [operation]}
    ).as_dict()

    assert report["status"] == "FAIL"
    assert report["error"]["error_code"] == "merged_range_unsupported"
    assert not output.exists()


def test_clearing_styled_formula_roundtrips_as_blank_and_preserves_style(tmp_path):
    source, output = tmp_path / "styled-formula.xlsx", tmp_path / "styled-formula-output.xlsx"
    _fixture(source)
    workbook = load_workbook(source)
    cell = workbook["Orders"]["G2"]
    cell.value = "=C2*E2"
    cell.fill = PatternFill(fill_type="solid", fgColor="D9EAF7")
    workbook.save(source)
    workbook.close()
    operation = {"schema_version": "1.0", "operations": [{
        "operation_id": "clear-styled-formula", "type": "clear",
        "target": {"sheet": "Orders", "range": "G2:G2"},
        "parameters": {"mode": "values", "formula_policy": "clear"},
    }]}

    report = DocumentOperationEngine().execute(source, output, operation).as_dict()

    assert report["status"] == "PASS", report
    result = load_workbook(output, data_only=False)
    try:
        cleared = result["Orders"]["G2"]
        assert cleared.value is None
        assert cleared.fill.fgColor.rgb.endswith("D9EAF7")
    finally:
        result.close()


def test_illegal_cell_text_returns_operation_scoped_error_and_no_output(tmp_path):
    source, output = tmp_path / "illegal.xlsx", tmp_path / "illegal-output.xlsx"
    _fixture(source)
    operation = {"schema_version": "1.0", "operations": [{
        "operation_id": "illegal-text",
        "type": "set_value",
        "target": {"sheet": "Orders", "cell": "A15"},
        "parameters": {"value": {"type": "string", "data": "bad" + chr(1) + "text"}},
    }]}
    report = DocumentOperationEngine().execute(source, output, operation).as_dict()
    assert report["status"] == "FAIL"
    assert report["error"]["operation_id"] == "illegal-text"
    assert report["error"]["error_code"] == "operation_execution_failed"
    assert not output.exists()


def test_timezone_aware_datetime_is_rejected_without_implicit_conversion(tmp_path):
    source, output = tmp_path / "tz.xlsx", tmp_path / "tz-output.xlsx"
    _fixture(source)
    operation = {"schema_version": "1.0", "operations": [{
        "operation_id": "timezone",
        "type": "set_value",
        "target": {"sheet": "Orders", "cell": "A15"},
        "parameters": {"value": {"type": "datetime", "data": "2026-11-03T12:30:00+08:00"}},
    }]}
    report = DocumentOperationEngine().execute(source, output, operation).as_dict()
    assert report["status"] == "FAIL"
    assert report["error"]["error_code"] == "timezone_unsupported"
    assert report["error"]["operation_id"] == "timezone"
    assert not output.exists()


def test_format_preserves_values_and_clear_values_preserves_styles_and_formula_text(tmp_path):
    source, output = tmp_path / "in.xlsx", tmp_path / "out.xlsx"
    _fixture(source)
    workbook = load_workbook(source)
    workbook["Orders"]["E2"].number_format = "0.00"
    workbook["Orders"]["G2"] = "=C2*E2"
    workbook["Orders"]["M2"].fill = PatternFill(fill_type="solid", fgColor="D9EAF7")
    workbook.save(source)
    workbook.close()
    operations = {
        "schema_version": "1.0",
        "operations": [
            {"operation_id": "format", "type": "format", "target": {"sheet": "Orders", "range": "E2:E2"}, "parameters": {"number_format": "0.0"}},
            {"operation_id": "clear", "type": "clear", "target": {"sheet": "Orders", "range": "M2:M2"}, "parameters": {"mode": "values"}},
        ],
    }
    report = DocumentOperationEngine().execute(source, output, operations).as_dict()
    assert report["status"] == "PASS", report
    result = load_workbook(output, data_only=False)
    try:
        sheet = result["Orders"]
        assert sheet["E2"].value == 12.5 and sheet["E2"].number_format == "0.0"
        assert sheet["M2"].value is None
        assert sheet["M2"].fill.fgColor.rgb.endswith("D9EAF7")
        assert sheet["G2"].value == "=C2*E2" and sheet["G2"].data_type == "f"
    finally:
        result.close()


def test_clear_formats_and_all_have_explicit_value_and_formula_semantics(tmp_path):
    source, output = tmp_path / "clear-modes.xlsx", tmp_path / "clear-modes-output.xlsx"
    _fixture(source)
    workbook = load_workbook(source)
    sheet = workbook["Orders"]
    sheet["A2"].fill = PatternFill(fill_type="solid", fgColor="00FF00")
    sheet["B2"] = "clear all"
    sheet["B2"].fill = PatternFill(fill_type="solid", fgColor="FF0000")
    sheet["G2"] = "=C2*E2"
    workbook.save(source)
    workbook.close()
    operations = {"schema_version": "1.0", "operations": [
        {"operation_id": "formats-only", "type": "clear", "target": {"sheet": "Orders", "range": "A2:A2"}, "parameters": {"mode": "formats"}},
        {"operation_id": "all-including-formula", "type": "clear", "target": {"sheet": "Orders", "range": "B2:B2"}, "parameters": {"mode": "all"}},
        {"operation_id": "formula-all", "type": "clear", "target": {"sheet": "Orders", "range": "G2:G2"}, "parameters": {"mode": "all", "formula_policy": "clear"}},
    ]}
    report = DocumentOperationEngine().execute(source, output, operations).as_dict()
    assert report["status"] == "PASS", report
    result = load_workbook(output, data_only=False)
    try:
        sheet = result["Orders"]
        assert sheet["A2"].value == "OLD-002"
        assert sheet["A2"].fill.fgColor.rgb != "0000FF00"
        assert sheet["B2"].value is None
        assert sheet["B2"].fill.fgColor.rgb == "00000000"
        assert sheet["G2"].value is None
    finally:
        result.close()


def test_sort_is_stable_for_duplicates_and_puts_blank_keys_last(tmp_path):
    source, output = tmp_path / "sort.xlsx", tmp_path / "sorted.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Orders"
    sheet.append(["Key", "Payload"])
    sheet.append(["B", "row-b"])
    sheet.append(["A", "first-a"])
    sheet.append(["A", "second-a"])
    sheet.append([None, "blank-key"])
    workbook.save(source)
    workbook.close()
    operation = {"schema_version": "1.0", "operations": [{
        "operation_id": "sort", "type": "sort", "target": {"sheet": "Orders", "range": "A1:B5"},
        "parameters": {"key": "A", "direction": "ascending", "header": True},
    }]}
    result = DocumentOperationEngine().execute(source, output, operation).as_dict()
    assert result["status"] == "PASS", result
    workbook = load_workbook(output)
    try:
        assert [workbook["Orders"].cell(row, 2).value for row in range(2, 6)] == ["first-a", "second-a", "row-b", "blank-key"]
    finally:
        workbook.close()


def test_sort_rejects_partial_record_ranges(tmp_path):
    source, output = tmp_path / "in.xlsx", tmp_path / "out.xlsx"
    _fixture(source)
    operation = {"schema_version": "1.0", "operations": [{
        "operation_id": "partial", "type": "sort", "target": {"sheet": "Orders", "range": "A2:B4"},
        "parameters": {"key": "A", "direction": "ascending", "header": False},
    }]}
    result = DocumentOperationEngine().execute(source, output, operation).as_dict()
    assert result["status"] == "FAIL" and result["error"]["error_code"] == "sort_partial_row"
    assert not output.exists()


def test_mid_sheet_insert_with_formula_is_blocked_and_source_is_unchanged(tmp_path):
    source, output = tmp_path / "formula.xlsx", tmp_path / "out.xlsx"
    _fixture(source)
    workbook = load_workbook(source)
    workbook["Orders"]["G2"] = "=C2*E2"
    workbook.save(source)
    workbook.close()
    before = _digest(source)
    operation = {"schema_version": "1.0", "operations": [{
        "operation_id": "insert", "type": "insert_rows", "target": {"sheet": "Orders", "row": 3}, "parameters": {"count": 2},
    }]}
    report = DocumentOperationEngine().execute(source, output, operation).as_dict()
    assert report["status"] == "FAIL"
    assert report["error"]["error_code"] == "insert_rows_formula_reference_risk"
    assert not output.exists() and _digest(source) == before


def test_mid_sheet_insert_with_merge_is_blocked_explicitly(tmp_path):
    source, output = tmp_path / "merge.xlsx", tmp_path / "out.xlsx"
    _fixture(source)
    workbook = load_workbook(source)
    workbook["Orders"].merge_cells("Q5:R5")
    workbook.save(source)
    workbook.close()
    operation = {"schema_version": "1.0", "operations": [{
        "operation_id": "insert", "type": "insert_rows", "target": {"sheet": "Orders", "row": 5}, "parameters": {"count": 2},
    }]}
    report = DocumentOperationEngine().execute(source, output, operation).as_dict()
    assert report["status"] == "FAIL" and report["error"]["error_code"] == "insert_rows_merged_range_risk"
    assert not output.exists()


def test_mid_sheet_insert_with_excel_table_is_blocked_explicitly(tmp_path):
    source, output = tmp_path / "table.xlsx", tmp_path / "out.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Orders"
    sheet.append(["Order", "Amount"])
    sheet.append(["SO-1", 1])
    sheet.append(["SO-2", 2])
    table = Table(displayName="OrdersTable", ref="A1:B3")
    table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
    sheet.add_table(table)
    workbook.save(source)
    workbook.close()
    operation = {"schema_version": "1.0", "operations": [{
        "operation_id": "insert", "type": "insert_rows", "target": {"sheet": "Orders", "row": 2}, "parameters": {"count": 2},
    }]}
    report = DocumentOperationEngine().execute(source, output, operation).as_dict()
    assert report["status"] == "FAIL" and report["error"]["error_code"] == "insert_rows_table_risk"
    assert not output.exists()


def test_failed_later_operation_does_not_publish_partial_output_or_change_source(tmp_path):
    source, output = tmp_path / "in.xlsx", tmp_path / "existing-output.xlsx"
    _fixture(source)
    output.write_bytes(b"previous validated output")
    before_input, before_output = _digest(source), output.read_bytes()
    operations = {
        "schema_version": "1.0",
        "operations": [
            {"operation_id": "set", "type": "set_value", "target": {"sheet": "Orders", "cell": "A20"}, "parameters": {"value": _typed("written only to simulation")}},
            {"operation_id": "bad", "type": "clear", "target": {"sheet": "missing", "range": "A1:A1"}, "parameters": {"mode": "values"}},
        ],
    }
    result = DocumentOperationEngine().execute(source, output, operations).as_dict()
    assert result["status"] == "FAIL" and result["error"]["stage"] == "execution"
    assert [op["status"] for op in result["operations"]] == ["not_committed", "failed"]
    assert _digest(source) == before_input and output.read_bytes() == before_output


def test_save_failure_keeps_source_and_existing_destination(tmp_path, monkeypatch):
    source, output = tmp_path / "save-failure.xlsx", tmp_path / "previous-output.xlsx"
    _fixture(source)
    output.write_bytes(b"previous verified version")
    before_input, before_output = _digest(source), output.read_bytes()

    def fail_save(_workbook, _filename):
        raise OSError("injected save failure")

    monkeypatch.setattr("openpyxl.workbook.workbook.Workbook.save", fail_save)
    operation = {"schema_version": "1.0", "operations": [{
        "operation_id": "write",
        "type": "set_value",
        "target": {"sheet": "Orders", "cell": "A15"},
        "parameters": {"value": _typed("candidate")},
    }]}
    report = DocumentOperationEngine().execute(source, output, operation).as_dict()
    assert report["status"] == "FAIL"
    assert report["error"]["error_code"] == "xlsx_save_failed"
    assert _digest(source) == before_input
    assert output.read_bytes() == before_output
    assert not list(tmp_path.glob(".previous-output.*.xlsx"))


def test_validation_failure_keeps_source_and_existing_destination(tmp_path, monkeypatch):
    source, output = tmp_path / "validation-failure.xlsx", tmp_path / "previous-output.xlsx"
    _fixture(source)
    output.write_bytes(b"previous verified version")
    before_input, before_output = _digest(source), output.read_bytes()

    def fail_validation(*_args):
        from office_document_operations import DocumentOperationError
        raise DocumentOperationError("output_state_mismatch", "validation", "injected read-back mismatch")

    monkeypatch.setattr("office_document_operations.engine.validate_saved_output", fail_validation)
    operation = {"schema_version": "1.0", "operations": [{
        "operation_id": "write",
        "type": "set_value",
        "target": {"sheet": "Orders", "cell": "A15"},
        "parameters": {"value": _typed("candidate")},
    }]}
    report = DocumentOperationEngine().execute(source, output, operation).as_dict()
    assert report["status"] == "FAIL"
    assert report["error"]["error_code"] == "output_state_mismatch"
    assert _digest(source) == before_input
    assert output.read_bytes() == before_output
    assert not list(tmp_path.glob(".previous-output.*.xlsx"))


def test_publish_failure_keeps_source_and_existing_destination(tmp_path, monkeypatch):
    source, output = tmp_path / "publish-failure.xlsx", tmp_path / "previous-output.xlsx"
    _fixture(source)
    output.write_bytes(b"previous verified version")
    before_input, before_output = _digest(source), output.read_bytes()

    def fail_replace(_source, _destination):
        raise OSError("injected publish failure")

    monkeypatch.setattr("office_document_operations.engine.os.replace", fail_replace)
    operation = {"schema_version": "1.0", "operations": [{
        "operation_id": "write",
        "type": "set_value",
        "target": {"sheet": "Orders", "cell": "A15"},
        "parameters": {"value": _typed("candidate")},
    }]}
    report = DocumentOperationEngine().execute(source, output, operation).as_dict()
    assert report["status"] == "FAIL"
    assert report["error"]["error_code"] == "output_publish_failed"
    assert _digest(source) == before_input
    assert output.read_bytes() == before_output
    assert not list(tmp_path.glob(".previous-output.*.xlsx"))


def test_validator_rejects_corrupt_saved_file(tmp_path):
    source, output = tmp_path / "in.xlsx", tmp_path / "corrupt.xlsx"
    _fixture(source)
    output.write_bytes(b"not a zip file")
    with pytest.raises(Exception, match="valid XLSX ZIP"):
        validate_saved_output(source, output, _main_operations())


def test_formula_is_not_recalculated_by_openpyxl(tmp_path):
    source, output = tmp_path / "formula.xlsx", tmp_path / "formula-output.xlsx"
    _fixture(source)
    workbook = load_workbook(source)
    workbook["Orders"]["G2"] = "=C2*E2"
    workbook.save(source)
    workbook.close()
    operation = {"schema_version": "1.0", "operations": [{
        "operation_id": "format", "type": "format", "target": {"sheet": "Orders", "cell": "E2"}, "parameters": {"number_format": "0.0"},
    }]}
    result = DocumentOperationEngine().execute(source, output, operation).as_dict()
    assert result["status"] == "PASS", result
    assert result["output"]["validation"]["formula_cells"] == 1
    assert "not recalculated" in result["output"]["validation"]["note"]
    check = load_workbook(output, data_only=False)
    try:
        assert check["Orders"]["G2"].value == "=C2*E2"
    finally:
        check.close()


def test_validator_requires_nonempty_file_and_valid_zip(tmp_path):
    source, output = tmp_path / "in.xlsx", tmp_path / "empty.xlsx"
    _fixture(source)
    output.write_bytes(b"")
    with pytest.raises(Exception, match="missing or empty"):
        validate_saved_output(source, output, _main_operations())

