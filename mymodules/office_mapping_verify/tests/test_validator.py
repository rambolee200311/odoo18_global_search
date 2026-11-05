import ast
import json
from pathlib import Path

import pytest

from mymodules.office_mapping_verify import (
    MAPPING_SCHEMA_VERSION,
    ValidationReport,
    apply_manual_edits,
    validate_proposal,
    validate_user_revision,
    parse_mapping_proposal,
)
from mymodules.office_mapping_verify.validator import expand_table_column_operations

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_IMPORTS = {
    "odoo",
    "office_core",
    "office_verify",
    "openai",
    "anthropic",
    "httpx",
    "requests",
    "urllib",
    "socket",
    "sqlite3",
    "psycopg2",
    "psycopg",
    "mysql",
    "pymysql",
    "asyncpg",
    "sqlalchemy",
    "importlib",
    "http",
    "urllib3",
    "ftplib",
    "smtplib",
    "ssl",
    "aiohttp",
    "websocket",
}


def target(element_id, required=True, writable=True, allowed=("string", "number", "boolean"), approved=False):
    return {
        "element_id": element_id,
        "required": required,
        "writable": writable,
        "allowed_value_types": list(allowed),
        "approved_to_skip": approved,
    }


def mapping(element_id, source_field="name", value_type="string"):
    return {"element_id": element_id, "source_field": source_field, "value_type": value_type}


def proposal(mappings=None, clarifications=None, skipped=None, **overrides):
    value = {
        "schema_version": MAPPING_SCHEMA_VERSION,
        "mappings": [] if mappings is None else mappings,
        "clarifications": [] if clarifications is None else clarifications,
        "skipped_targets": [] if skipped is None else skipped,
    }
    value.update(overrides)
    return value


def validate(value, manifest=None, fields=None, **kwargs):
    return validate_proposal(
        value,
        manifest if manifest is not None else [target("xlsx:Sheet1!A1")],
        fields if fields is not None else {"name": "string"},
        **kwargs,
    )


def test_valid_complete_proposal_is_ready_and_report_serializes():
    report = validate(proposal([mapping("xlsx:Sheet1!A1")]))
    assert report.ready_for_review is True
    assert report.status == "ready"
    assert json.loads(json.dumps(report.to_dict()))["status"] == "ready"


def test_numeric_literal_is_valid_for_numeric_target_without_source_field():
    value = proposal(
        [{"element_id": "xlsx:Sheet1!B4", "literal_value": 3329.15, "value_type": "number"}]
    )
    report = validate(value, [target("xlsx:Sheet1!B4", allowed=("number",))], {})
    assert report.ready_for_review is True


def test_iso_date_literal_is_valid_for_date_target_and_rejected_when_invalid():
    value = proposal(
        [{"element_id": "xlsx:Sheet1!B2", "literal_value": "2026-11-10", "value_type": "date"}]
    )
    report = validate(value, [target("xlsx:Sheet1!B2", allowed=("date",))], {})
    assert report.ready_for_review is True, report.to_dict()
    assert parse_mapping_proposal(json.dumps(value))["mappings"][0]["literal_value"] == "2026-11-10"

    invalid = proposal(
        [{"element_id": "xlsx:Sheet1!B2", "literal_value": "2026-02-30", "value_type": "date"}]
    )
    assert not validate(invalid, [target("xlsx:Sheet1!B2", allowed=("date",))], {}).ready_for_review


def test_date_offset_transform_is_a_bounded_typed_operation():
    value = proposal(
        [
            {
                "element_id": "xlsx:Sheet1!B2",
                "source_field": "date_order",
                "value_type": "date",
                "transform": {"type": "date_offset", "days": 7},
            }
        ]
    )
    report = validate(value, [target("xlsx:Sheet1!B2", allowed=("date",))], {"date_order": "date"})
    assert report.ready_for_review is True, report.to_dict()
    parsed = parse_mapping_proposal(json.dumps(value))
    assert parsed["mappings"][0]["transform"] == {"type": "date_offset", "days": 7}

    for transform in (
        {"type": "date_offset", "days": True},
        {"type": "date_offset", "days": 365001},
        {"type": "python", "expression": "__import__('os').system('id')"},
    ):
        invalid = proposal([{**value["mappings"][0], "transform": transform}])
        assert not validate(invalid, [target("xlsx:Sheet1!B2", allowed=("date",))], {"date_order": "date"}).ready_for_review


def test_concatenated_mapping_requires_authorized_string_fields():
    value = proposal([{
        "element_id": "xlsx:Sheet1!A1",
        "concat_fields": ["comment", "name"],
        "separator": " ",
        "value_type": "string",
    }])
    report = validate(
        value,
        [target("xlsx:Sheet1!A1", allowed=("string",))],
        {"comment": "string", "name": "string"},
    )
    assert report.ready_for_review is True, report.to_dict()

    wrong_type = validate(
        value,
        [target("xlsx:Sheet1!A1", allowed=("string",))],
        {"comment": "string", "name": "number"},
    )
    assert "type_mismatch:xlsx:Sheet1!A1" in wrong_type.type_errors


def test_date_offset_applies_to_iso_date_without_changing_type():
    from mymodules.office_mapping_verify.transforms import apply_transform

    assert apply_transform("2026-11-03", {"type": "date_offset", "days": 7}, "date") == "2026-11-10"


def test_number_format_patch_is_independent_of_value_mapping():
    value = proposal(
        [mapping("xlsx:Sheet1!B2", "amount_total", "number")],
        format_patches=[{"element_id": "xlsx:Sheet1!B2", "number_format": "0.0"}],
    )
    report = validate(
        value,
        [target("xlsx:Sheet1!B2", allowed=("number",))],
        {"amount_total": "number"},
    )
    assert report.ready_for_review is True, report.to_dict()


def test_nonwritable_table_header_cannot_receive_mapping():
    header = target("xlsx:Sheet1!A1")
    header["writable"] = False
    header["table_role"] = "table_header"
    header["table_role"] = "table_header"
    report = validate(proposal([mapping("xlsx:Sheet1!A1")]), [header], {"name": "string"})
    assert report.status == "invalid"
    assert "target_not_writable:xlsx:Sheet1!A1" in report.type_errors


def test_explicit_header_edit_is_allowed_only_for_detected_header_text():
    header = {
        **target("xlsx:Orders!F1"),
        "writable": False,
        "table_role": "table_header",
        "table_header": "供应商产品名称",
    }
    value = proposal(
        mappings=[],
        header_edits=[{"element_id": "xlsx:Orders!F1", "value": "供应商商品描述"}],
    )
    report = validate(value, [header], {})
    assert report.ready_for_review is True, report.to_dict()


def test_explicit_cell_edit_accepts_authorized_data_and_rejects_unknown_targets():
    value = proposal(
        mappings=[],
        header_edits=[{"element_id": "xlsx:Orders!F2", "value": "新标签"}],
    )
    data_target = {**target("xlsx:Orders!F2"), "table_role": "table_data", "table_header": "供应商产品名称"}
    data_report = validate(value, [data_target], {})
    assert data_report.ready_for_review is True, data_report.to_dict()

    unknown_report = validate(value, [], {})
    assert unknown_report.status == "invalid"
    assert "xlsx:Orders!F2" in unknown_report.unknown_targets


def test_explicit_header_edit_does_not_make_ordinary_mapping_writable():
    header = {
        **target("xlsx:Orders!F1"),
        "writable": False,
        "table_role": "table_header",
        "table_header": "供应商产品名称",
    }
    ordinary_mapping = proposal([mapping("xlsx:Orders!F1")])
    report = validate(ordinary_mapping, [header], {"name": "string"})
    assert report.status == "invalid"
    assert "target_not_writable:xlsx:Orders!F1" in report.type_errors


def test_explicit_cell_edit_overwrites_existing_header_or_data_only_when_in_manifest():
    manifest = [
        {
            **target("xlsx:Orders!F1", writable=False),
            "table_role": "table_header",
            "table_header": "供应商产品名称",
        },
        {**target("xlsx:Orders!F2"), "table_role": "table_data", "table_header": "供应商产品名称"},
    ]
    value = proposal(
        mappings=[],
        cell_edits=[
            {"element_id": "xlsx:Orders!F1", "value": "供应商商品描述", "value_type": "string"},
            {"element_id": "xlsx:Orders!F2", "value": "说明文本", "value_type": "string"},
        ],
    )
    report = validate(value, manifest, {})
    assert report.ready_for_review is True, report.to_dict()

    outside = proposal(
        mappings=[],
        cell_edits=[{"element_id": "xlsx:Orders!Z999", "value": "越界", "value_type": "string"}],
    )
    outside_report = validate(outside, manifest, {})
    assert outside_report.status == "invalid"
    assert "xlsx:Orders!Z999" in outside_report.unknown_targets


def test_explicit_cell_edit_does_not_bypass_other_nonwritable_manifest_targets():
    protected = target("xlsx:Orders!F2", writable=False)
    value = proposal(
        mappings=[],
        cell_edits=[{"element_id": "xlsx:Orders!F2", "value": "new value", "value_type": "string"}],
    )
    report = validate(value, [protected], {})
    assert report.status == "invalid"
    assert "cell_edit_target_not_writable:xlsx:Orders!F2" in report.type_errors


def test_mapping_and_cell_edit_overlap_requires_declared_execution_order():
    target_id = "xlsx:Orders!B2"
    value = proposal(
        mappings=[mapping(target_id, "name")],
        cell_edits=[{"element_id": target_id, "value": "", "value_type": "string"}],
    )
    manifest = [target(target_id)]

    unordered = validate(value, manifest, {"name": "string"})
    assert unordered.status == "invalid"
    assert f"target_mapped_and_cell_edited:{target_id}" in unordered.structural_errors

    ordered = validate(
        value,
        manifest,
        {"name": "string"},
        ordered_cell_edit_overrides=True,
    )
    assert ordered.ready_for_review is True, ordered.to_dict()


def test_record_target_requires_session_resolution_before_mapping_validation():
    value = proposal(
        mappings=[],
        cell_edits=[{
            "record_target": {"group_id": "repeat_rows", "record_id": 42, "column": "B"},
            "value": False,
            "value_type": "boolean",
        }],
    )
    report = validate(value, [], {})
    assert report.status == "invalid"
    assert "record_target_requires_session_resolution" in report.structural_errors


def test_column_operations_expand_only_to_detected_writable_table_data():
    manifest = [
        {**target("xlsx:Orders!B1"), "writable": False, "table_role": "table_header", "table_header": "Amount"},
        {**target("xlsx:Orders!B2", allowed=("number",)), "table_role": "table_data", "table_header": "Amount"},
        {**target("xlsx:Orders!B3", allowed=("number",)), "table_role": "table_data", "table_header": "Amount"},
        {**target("xlsx:Orders!A2"), "table_role": "table_data", "table_header": "Order"},
        target("xlsx:Orders!B8", allowed=("number",)),
    ]
    proposal_value = proposal(
        mappings=[],
        clear_columns=[{"sheet": "Orders", "column": "B"}],
        format_patches=[{"sheet": "Orders", "column": "B", "number_format": "0.0"}],
    )
    normalized, errors = expand_table_column_operations(proposal_value, manifest)
    assert errors == []
    assert normalized["clear_targets"] == ["xlsx:Orders!B2", "xlsx:Orders!B3"]
    assert normalized["format_patches"] == [
        {"element_id": "xlsx:Orders!B2", "number_format": "0.0"},
        {"element_id": "xlsx:Orders!B3", "number_format": "0.0"},
    ]
    assert "clear_columns" not in normalized


def test_template_required_flag_does_not_block_an_unmapped_target():
    report = validate(proposal(), [target("xlsx:Sheet1!F17", required=True)], {"name": "string"})
    assert report.ready_for_review is True
    assert report.missing_required == ()


def test_merged_target_metadata_is_preserved_without_changing_write_authority():
    merged_target = {
        **target("xlsx:Sheet1!E17"),
        "merge_range": "E17:H17",
        "write_target": "xlsx:Sheet1!E17",
        "visual_labels": [{
            "element_id": "xlsx:Sheet1!F16",
            "text": "订单号",
            "relation": "above_merged_region",
        }],
    }
    report = validate_proposal(
        proposal([mapping("xlsx:Sheet1!E17")]),
        [merged_target],
        {"name": "string"},
    )
    assert report.ready_for_review is True
    # validate_user_revision normalizes the manifest before re-validating the
    # updated proposal. The normalized visual_labels are a tuple, so this also
    # protects the metadata round trip used by Odoo's mapping session service.
    from office_mapping_verify import validate_user_revision

    revision_report = validate_user_revision(
        proposal(),
        [],
        [merged_target],
        {"name": "string"},
    )
    assert revision_report.status == "ready"


@pytest.mark.parametrize(
    "metadata,expected",
    [
        ({"merge_range": "E17:not-a-cell"}, "invalid_target_metadata"),
        ({"write_target": "xlsx:Sheet1!F17"}, "invalid_target_metadata"),
        ({"visual_labels": [{"element_id": "x", "text": "label", "relation": "guess"}]}, "invalid_target_metadata"),
        ({"visual_labels": [{"element_id": "x", "text": "label", "relation": []}]}, "invalid_target_metadata"),
        ({"unknown_metadata": True}, "invalid_target_spec"),
    ],
)
def test_invalid_or_unknown_target_metadata_fails_closed(metadata, expected):
    report = validate_proposal(
        proposal(),
        [dict(target("xlsx:Sheet1!E17"), **metadata)],
        {"name": "string"},
    )
    assert expected in report.structural_errors


def test_fallback_requires_every_candidate_to_be_authorized_with_same_type():
    report = validate(
        proposal(
            [
                {
                    "element_id": "xlsx:Sheet1!A1",
                    "source_fields": ["default_code", "barcode"],
                    "value_type": "string",
                }
            ]
        ),
        [target("xlsx:Sheet1!A1")],
        {"default_code": "string", "barcode": "string"},
    )
    assert report.ready_for_review is True
    report = validate(
        proposal(
            [
                {
                    "element_id": "xlsx:Sheet1!A1",
                    "source_fields": ["default_code", "secret"],
                    "value_type": "string",
                }
            ]
        ),
        [target("xlsx:Sheet1!A1")],
        {"default_code": "string"},
    )
    assert "secret" in report.unknown_fields


def test_arithmetic_formula_is_allowed_only_for_formula_enabled_target():
    formula_target = target("xlsx:Sheet1!G23", allowed=("formula",))
    report = validate(
        proposal(
            [
                {
                    "element_id": "xlsx:Sheet1!G23",
                    "formula": "=D23*E23*3",
                    "value_type": "formula",
                }
            ]
        ),
        [formula_target],
        {},
    )
    assert report.ready_for_review is True
    report = validate(
        proposal(
            [
                {
                    "element_id": "xlsx:Sheet1!G23",
                    "formula": "=D23*E23*3",
                    "value_type": "formula",
                }
            ]
        ),
        [target("xlsx:Sheet1!G23")],
        {},
    )
    assert "type_mismatch:xlsx:Sheet1!G23" in report.type_errors


def test_report_status_is_invalid_for_structural_and_allowlist_errors():
    assert validate({}, manifest=[], fields={}).status == "invalid"
    assert validate(proposal([mapping("unknown")]), manifest=[], fields={}).status == "invalid"


@pytest.mark.parametrize(
    "manifest,fields,expected",
    [
        (None, {}, "invalid_target_manifest"),
        ([None], {}, "invalid_target_spec"),
        ([{"element_id": "x"}], {}, "invalid_target_spec"),
        ([target("")], {}, "invalid_target_id"),
        ([dict(target("x"), required=1)], {}, "invalid_target_flags"),
        ([dict(target("x"), allowed_value_types="string")], {}, "invalid_target_types"),
        ([dict(target("x"), allowed_value_types=[[]])], {}, "unsupported_target_type"),
        ([target("x"), target("x")], {}, "duplicate_manifest_target"),
    ],
)
def test_invalid_manifest_fails_closed(manifest, fields, expected):
    report = validate_proposal(proposal(), manifest, fields)
    assert expected in report.structural_errors
    assert report.ready_for_review is False


def test_string_manifest_and_non_mapping_allowed_fields_fail_closed():
    report = validate(proposal(), "not-a-manifest", {})
    assert "invalid_target_manifest" in report.structural_errors
    report = validate(proposal(), [], [])
    assert "invalid_allowed_fields" in report.structural_errors


def test_invalid_allowed_field_keys_and_types_fail_closed():
    report = validate(proposal(), [], {"": "string", "bad": "date", 1: "boolean"})
    assert "invalid_allowed_field_id" in report.structural_errors
    assert "unsupported_allowed_field_type" not in report.structural_errors
    invalid_type = validate(proposal(), [], {"bad": "binary"})
    assert "unsupported_allowed_field_type" in invalid_type.structural_errors


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, "invalid_proposal_object"),
        ({"schema_version": "bad"}, "invalid_proposal_keys"),
        (proposal(schema_version="bad"), "unsupported_schema_version"),
        (proposal(mappings={}), "invalid_mappings"),
        (proposal(clarifications={}), "invalid_clarifications"),
        (proposal(skipped={}), "invalid_skipped_targets"),
    ],
)
def test_invalid_proposal_shape_fails_closed(value, expected):
    report = validate(value)
    assert expected in report.structural_errors


def test_malformed_mapping_and_all_membership_type_edges():
    manifest = [
        target("read-only", writable=False),
        target("good"),
        target("bad-field"),
        target("invalid-type"),
        target("unsupported-type"),
        target("number", allowed=("number",)),
    ]
    report = validate(
        proposal(
            mappings=[
                None,
                {"element_id": "", "source_field": "name", "value_type": "string"},
                mapping("missing"),
                mapping("read-only"),
                    mapping("good", "", "string"),
                    mapping("bad-field", "secret", "string"),
                    mapping("invalid-type", "name", []),
                    mapping("unsupported-type", "name", "date"),
                mapping("number", "name", "string"),
                mapping("good", "name", "string"),
                mapping("good", "name", "string"),
            ]
        ),
        manifest,
        {"name": "string"},
    )
    assert "invalid_mapping_shape" in report.structural_errors
    assert "invalid_mapping_target" in report.structural_errors
    assert "target_not_writable:read-only" not in report.structural_errors
    assert "missing" in report.unknown_targets
    assert "" in report.unknown_fields
    assert "secret" in report.unknown_fields
    assert "unsupported_value_type:invalid-type" in report.type_errors
    assert "type_mismatch:number" in report.type_errors
    assert "good" in report.duplicates
    assert report.ready_for_review is False


def test_unknown_source_type_and_empty_target_types_reject_mapping():
    report = validate(
        proposal([mapping("empty", "name", "string")]),
        [target("empty", allowed=())],
        {"name": []},
    )
    assert "unsupported_allowed_field_type" in report.structural_errors


def test_invalid_clarifications_and_unknown_target_are_reported():
    report = validate(
        proposal(
            clarifications=[
                None,
                {"element_id": "x"},
                {"element_id": "", "reason_code": "missing_source", "question": "q"},
                {"element_id": "unknown", "reason_code": "missing_source", "question": "q"},
                {"element_id": "x", "reason_code": "nope", "question": "q"},
                {"element_id": "x", "reason_code": "missing_source", "question": " "},
                {"element_id": "x", "reason_code": "missing_source", "question": "need name"},
            ]
        ),
        [target("x")],
        {"name": "string"},
    )
    assert "invalid_clarification_shape" in report.structural_errors
    assert "invalid_clarification_target" in report.structural_errors
    assert "invalid_clarification_reason:x" in report.structural_errors
    assert "invalid_clarification_question:x" in report.structural_errors
    assert "unknown" in report.unknown_targets
    assert report.clarifications == ("x",)
    assert report.ready_for_review is False


def test_skips_are_declarative_and_duplicate_or_unknown_skips_are_reported():
    manifest = [target("required"), target("optional", required=False), target("approved", required=False, approved=True)]
    report = validate(
        proposal(
            mappings=[mapping("approved")],
            skipped=[None, "unknown", "required", "optional", "approved", "approved"],
        ),
        manifest,
        {"name": "string"},
    )
    assert "invalid_skipped_target" in report.structural_errors
    assert "unknown" in report.unknown_targets
    assert report.skipped_unapproved == ()
    assert "approved" in report.duplicates
    assert "target_mapped_and_skipped:approved" in report.structural_errors
    assert report.missing_required == ()
    assert report.ready_for_review is False


def test_approved_optional_skip_satisfies_only_that_target():
    report = validate(
        proposal(skipped=["optional"]),
        [target("required"), target("optional", required=False, approved=True)],
        {"name": "string"},
    )
    assert report.missing_required == ()
    assert report.skipped_unapproved == ()
    assert report.status == "ready"


def test_skip_does_not_require_template_approval_metadata():
    report = validate(
        proposal(skipped=["optional"]),
        [target("optional", required=True, writable=False, approved=False)],
        {"name": "string"},
    )
    assert report.ready_for_review is True
    assert report.skipped_unapproved == ()


def test_required_flag_does_not_block_an_explicit_skip():
    report = validate(
        proposal(skipped=["required"]),
        [target("required", required=True, approved=False)],
        {"name": "string"},
    )
    assert report.ready_for_review is True
    assert report.skipped_unapproved == ()
    assert report.missing_required == ()


def test_explicit_mapping_can_replace_a_formula_or_locked_template_target():
    report = validate(
        proposal([mapping("formula-cell")]),
        [target("formula-cell", required=True, writable=False, allowed=("string",))],
        {"name": "string"},
    )
    assert report.ready_for_review is True
    assert report.structural_errors == ()


def test_5_of_20_partial_mapping_is_ready_and_leaves_other_targets_untouched():
    manifest = [target(f"xlsx:Sheet1!A{index}") for index in range(1, 21)]
    fields = {f"field_{index}": "string" for index in range(1, 6)}
    mappings = [mapping(f"xlsx:Sheet1!A{index}", f"field_{index}") for index in range(1, 6)]
    report = validate(proposal(mappings), manifest, fields)
    assert report.missing_required == ()
    assert report.status == "ready"
    assert report.ready_for_review is True


def test_explicit_clear_target_is_validated_without_mapping():
    value = proposal(mappings=[], clear_targets=["xlsx:Sheet1!A1"])
    report = validate(value)
    assert report.ready_for_review is True


def test_explicit_clear_accepts_formula_target_and_empty_string_even_if_not_writable():
    report = validate(
        proposal(mappings=[], clear_targets=["xlsx:Sheet1!A1"]),
        [target("xlsx:Sheet1!A1", writable=False, allowed=("number",))],
        {"name": "string"},
    )
    assert report.ready_for_review is True
    assert report.structural_errors == ()
    assert report.unknown_targets == ()


def test_empty_value_mapping_clears_required_formula_target():
    report = validate(
        proposal([{"element_id": "xlsx:Sheet1!A1", "value": ""}]),
        [target("xlsx:Sheet1!A1", required=True, writable=False, allowed=("formula",))],
        {},
    )
    assert report.ready_for_review is True
    assert report.structural_errors == ()
    assert report.unknown_targets == ()
    assert report.missing_required == ()


def test_explicit_clear_rejects_duplicates_and_conflicts():
    duplicate = validate(proposal(mappings=[], clear_targets=["xlsx:Sheet1!A1"] * 2))
    assert "duplicate_clear_target:xlsx:Sheet1!A1" in duplicate.duplicates
    overlap = validate(proposal([mapping("xlsx:Sheet1!A1")], clear_targets=["xlsx:Sheet1!A1"]))
    assert "target_mapped_and_cleared:xlsx:Sheet1!A1" in overlap.structural_errors


def test_validator_enforces_manifested_proposal_collection_limits_when_parser_is_bypassed():
    empty_manifest = []
    too_many_mappings = proposal([mapping(f"t{i}") for i in range(201)])
    too_many_clarifications = proposal(
        clarifications=[
            {"element_id": "t", "reason_code": "missing_source", "question": "q"}
            for _ in range(101)
        ]
    )
    too_many_skips = proposal(skipped=[f"t{i}" for i in range(201)])
    assert "too_many_mappings" in validate(too_many_mappings, empty_manifest, {}).structural_errors
    assert "too_many_clarifications" in validate(too_many_clarifications, empty_manifest, {}).structural_errors
    assert "too_many_skipped_targets" in validate(too_many_skips, empty_manifest, {}).structural_errors


def test_manual_revision_accepts_frozen_edit_count_limit():
    edits = [mapping(f"target-{index}") for index in range(200)]
    report = validate_user_revision(proposal(), edits, [], {})
    assert "too_many_edits" not in report.structural_errors
    assert len(report.unknown_targets) == 200


def test_manual_revision_adds_and_replaces_then_revalidates_without_stale_pass():
    manifest = [target("a"), target("b")]
    original = proposal(
        [mapping("a", "bad", "string")],
        clarifications=[{"element_id": "b", "reason_code": "missing_source", "question": "choose"}],
        skipped=["b"],
    )
    edits = [mapping("a", "name", "string"), mapping("b", "name", "string")]
    report = validate_user_revision(original, edits, manifest, {"name": "string"})
    assert report.ready_for_review is True
    assert apply_manual_edits(original, edits, manifest, {"name": "string"}) == report
    assert original["mappings"][0]["source_field"] == "bad"


def test_manual_mapping_edit_clears_prior_explicit_clear_for_same_target():
    manifest = [target("xlsx:Sheet1!F17")]
    original = proposal(mappings=[], clear_targets=["xlsx:Sheet1!F17"])
    report = validate_user_revision(
        original,
        [mapping("xlsx:Sheet1!F17", "name")],
        manifest,
        {"name": "string"},
    )
    assert report.ready_for_review is True


@pytest.mark.parametrize(
    "revision,edits,manifest,expected",
    [
        (None, [], [], "invalid_revision"),
        ({"bad": 1}, [], [], "invalid_revision"),
        (proposal(mappings={}), [], [], "invalid_revision_mappings"),
        (proposal(mappings=[mapping(f"t{i}") for i in range(201)]), [], [], "too_many_mappings"),
        (proposal(clarifications={}), [], [], "invalid_revision_state"),
        (proposal(skipped={}), [], [], "invalid_revision_state"),
        (proposal(), None, [], "invalid_edits"),
        (proposal(), [], "bad-manifest", "invalid_target_manifest"),
        (proposal(), [mapping(f"x{i}") for i in range(201)], [], "too_many_edits"),
        (proposal(), [None], [], "invalid_edit_shape"),
        (proposal(), [{"element_id": None, "source_field": "x", "value_type": "string"}], [], "invalid_edit_target"),
        (proposal(), [mapping("x"), mapping("x")], [], "x"),
        (proposal(mappings=[None]), [], [], "invalid_revision_mapping_shape"),
        (proposal(mappings=[{"element_id": None, "source_field": "x", "value_type": "string"}]), [], [], "invalid_revision_mapping_target"),
    ],
)
def test_manual_revision_rejects_invalid_shapes(revision, edits, manifest, expected):
    if expected == "x":
        assert validate_user_revision(revision, edits, manifest, {}).duplicates == ("x",)
    else:
        assert expected in validate_user_revision(revision, edits, manifest, {}).structural_errors


def test_manual_revision_reports_unknown_or_bad_type_edit():
    base = proposal()
    report = validate_user_revision(base, [mapping("a", "bad", "string")], [target("a")], {})
    assert "bad" in report.unknown_fields
    report = validate_user_revision(base, [mapping("a", "name", "number")], [target("a", allowed=("string",))], {"name": "string"})
    assert "type_mismatch:a" in report.type_errors


def test_static_import_guard_covers_production_and_test_python_files():
    violations = []
    for path in sorted(PACKAGE_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name.split(".")[0] for alias in node.names]
                if FORBIDDEN_IMPORTS.intersection(names):
                    violations.append(path.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module.split(".")[0] in FORBIDDEN_IMPORTS:
                    violations.append(path.name)
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "__import__":
                violations.append(path.name)
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "import_module":
                violations.append(path.name)
    assert violations == []
