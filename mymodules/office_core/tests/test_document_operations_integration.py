from __future__ import annotations

import hashlib
from io import BytesIO

from openpyxl import Workbook, load_workbook

from office_core import ResourceBudget, execute_document_operations, expand_repeat_rows, inspect_document, render_candidate


MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _budget():
    return ResourceBudget(
        max_file_size=2_000_000,
        max_expanded_size=8_000_000,
        max_zip_entries=128,
        max_entry_size=2_000_000,
        max_xml_elements=100_000,
        max_cells=100_000,
        max_paragraphs=10_000,
        max_memory_bytes=2_000_000_000_000,
        timeout_seconds=15,
    )


def _source():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Ledger"
    sheet.append(["Reference", "Amount", "Date", "Untouched"])
    sheet.append(["A-2", 0, "2026-11-03", "keep"])
    sheet["B2"].number_format = "0.00"
    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


def test_office_core_executes_operations_and_validates_saved_bytes():
    source = _source()
    operation_list = {
        "schema_version": "1.1",
        "source_sha256": hashlib.sha256(source).hexdigest(),
        "operations": [
            {
                "operation_id": "replace-reference",
                "type": "set_value",
                "target": {"sheet": "Ledger", "cell": "A2"},
                "parameters": {"value": {"type": "string", "data": "A-1"}},
            },
            {
                "operation_id": "format-amount",
                "type": "format",
                "target": {"sheet": "Ledger", "cell": "B2"},
                "parameters": {"number_format": "0.0"},
            },
        ],
    }

    candidate = execute_document_operations(source, "ledger.xlsx", MIME, operation_list, _budget())

    workbook = load_workbook(BytesIO(candidate.content), data_only=False)
    sheet = workbook["Ledger"]
    assert sheet["A2"].value == "A-1"
    assert sheet["B2"].value == 0
    assert sheet["B2"].number_format == "0.0"
    assert sheet["C2"].value == "2026-11-03"
    assert sheet["D2"].value == "keep"
    workbook.close()
    assert candidate.verification["status"] == "PASS"
    assert candidate.verification["zip_valid"] is True
    assert candidate.verification["openpyxl_readable"] is True


def test_operation_list_supports_formula_write_and_reopens_formula_text():
    source = _source()
    operation_list = {
        "schema_version": "1.1",
        "source_sha256": hashlib.sha256(source).hexdigest(),
        "operations": [
            {
                "operation_id": "set-total-formula",
                "type": "set_formula",
                "target": {"sheet": "Ledger", "cell": "B3"},
                "parameters": {"formula": "=B2*2"},
            }
        ],
    }

    candidate = execute_document_operations(source, "ledger.xlsx", MIME, operation_list, _budget())

    workbook = load_workbook(BytesIO(candidate.content), data_only=False)
    assert workbook["Ledger"]["B3"].value == "=B2*2"
    workbook.close()
    assert candidate.verification["formula_cells"] == 1
    assert "not recalculated" in candidate.verification["note"]


def test_repeat_rows_is_an_ordered_core_operation_before_mapping_writes():
    source = _source()
    operation_list = {
        "schema_version": "1.1",
        "source_sha256": hashlib.sha256(source).hexdigest(),
        "operations": [
            {
                "operation_id": "expand-details",
                "type": "repeat_rows",
                "target": {"sheet": "Ledger", "start_row": 2},
                "parameters": {"record_count": 3, "columns": {"A": "Reference", "B": "Amount"}},
            },
            {
                "operation_id": "write-details",
                "type": "set_value",
                "target": {"sheet": "Ledger", "range": "A2:B4"},
                "parameters": {
                    "values": [
                        [{"type": "string", "data": "R-1"}, {"type": "number", "data": 1.0}],
                        [{"type": "string", "data": "R-2"}, {"type": "number", "data": 2.0}],
                        [{"type": "string", "data": "R-3"}, {"type": "number", "data": 3.0}],
                    ]
                },
            },
        ],
    }

    candidate = execute_document_operations(source, "ledger.xlsx", MIME, operation_list, _budget())

    workbook = load_workbook(BytesIO(candidate.content), data_only=False)
    sheet = workbook["Ledger"]
    assert [sheet.cell(row, 1).value for row in range(2, 5)] == ["R-1", "R-2", "R-3"]
    assert [sheet.cell(row, 2).value for row in range(2, 5)] == [1, 2, 3]
    assert sheet["D2"].value == "keep"
    workbook.close()
    assert candidate.verification["operation_count"] == 2


def test_legacy_mapping_writes_and_repeat_rows_use_the_same_core_operation_path():
    source = _source()
    repeat_instruction = {
        "action": "insert_repeat_rows",
        "sheet": "Ledger",
        "start_row": 2,
        "record_count": 2,
        "columns": {"A": "Reference", "B": "Amount"},
    }
    expanded = expand_repeat_rows(source, repeat_instruction, _budget()).content
    inspection = inspect_document(expanded, "ledger.xlsx", MIME, _budget())
    mapping = {
        "schema_version": "1",
        "template_sha256": inspection.template_sha256,
        "writes": [
            {"element_id": "xlsx:Ledger!B2", "operation": "set_value", "value": {"type": "number", "data": 1}},
            {"element_id": "xlsx:Ledger!B3", "operation": "set_value", "value": {"type": "number", "data": 2}},
        ],
    }

    candidate = render_candidate(
        source,
        "ledger.xlsx",
        MIME,
        mapping,
        _budget(),
        preprocessing=repeat_instruction,
    )

    workbook = load_workbook(BytesIO(candidate.content), data_only=False)
    assert [workbook["Ledger"][f"B{row}"].value for row in (2, 3)] == [1, 2]
    workbook.close()
    assert candidate.verification["status"] == "PASS"


def test_mapping_candidate_runs_independent_office_verify_and_reports_both_checks():
    source = _source()
    inspection = inspect_document(source, "ledger.xlsx", MIME, _budget())
    mapping = {
        "schema_version": "1",
        "template_sha256": inspection.template_sha256,
        "writes": [
            {"element_id": "xlsx:Ledger!D2", "operation": "set_value", "value": {"type": "string", "data": ""}},
            {"element_id": "xlsx:Ledger!B2", "operation": "set_number_format", "value": {"type": "number_format", "data": "0.0"}},
        ],
    }

    candidate = render_candidate(
        source,
        "ledger.xlsx",
        MIME,
        mapping,
        _budget(),
        authorized_blank_targets=("xlsx:Ledger!D2",),
    )

    workbook = load_workbook(BytesIO(candidate.content), data_only=False)
    assert workbook["Ledger"]["D2"].value is None
    assert workbook["Ledger"]["B2"].number_format == "0.0"
    workbook.close()
    assert candidate.verification["status"] == "PASS"
    assert candidate.verification["output_sha256"] == candidate.candidate_sha256
    assert candidate.verification["office_verify"]["status"] == "PASS"
    assert candidate.verification["document_operations"]["status"] == "PASS"


def test_mapping_can_write_an_explicit_unformatted_coordinate_in_an_existing_sheet():
    source = _source()
    inspection = inspect_document(source, "ledger.xlsx", MIME, _budget())
    mapping = {
        "schema_version": "1",
        "template_sha256": inspection.template_sha256,
        "writes": [
            {"element_id": "xlsx:Ledger!M12", "operation": "set_value", "value": {"type": "string", "data": "new target"}},
        ],
    }

    candidate = render_candidate(source, "ledger.xlsx", MIME, mapping, _budget())

    workbook = load_workbook(BytesIO(candidate.content), data_only=False)
    assert workbook["Ledger"]["M12"].value == "new target"
    workbook.close()
    assert candidate.verification["office_verify"]["status"] == "PASS"


def test_core_mapping_can_authorize_clear_of_an_unserialized_coordinate():
    source = _source()
    inspection = inspect_document(source, "ledger.xlsx", MIME, _budget())
    target = "xlsx:Ledger!M12"
    mapping = {
        "schema_version": "1",
        "template_sha256": inspection.template_sha256,
        "writes": [
            {"element_id": target, "operation": "set_value", "value": {"type": "string", "data": ""}},
        ],
    }

    candidate = render_candidate(
        source,
        "ledger.xlsx",
        MIME,
        mapping,
        _budget(),
        authorized_blank_targets=(target,),
    )

    workbook = load_workbook(BytesIO(candidate.content), data_only=False)
    assert workbook["Ledger"]["M12"].value is None
    workbook.close()
    assert candidate.verification["office_verify"]["status"] == "PASS"


def test_operation_list_rejects_stale_source_fingerprint():
    source = _source()
    operation_list = {
        "schema_version": "1.1",
        "source_sha256": "0" * 64,
        "operations": [
            {
                "operation_id": "write",
                "type": "set_value",
                "target": {"sheet": "Ledger", "cell": "A2"},
                "parameters": {"value": {"type": "string", "data": "changed"}},
            }
        ],
    }
    try:
        execute_document_operations(source, "ledger.xlsx", MIME, operation_list, _budget())
    except Exception as exc:
        assert getattr(exc, "code", None) == "OFFICE_TEMPLATE_FINGERPRINT_MISMATCH"
    else:
        raise AssertionError("stale source fingerprint should be rejected")
