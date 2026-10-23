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
)

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


def validate(value, manifest=None, fields=None):
    return validate_proposal(
        value,
        manifest if manifest is not None else [target("xlsx:Sheet1!A1")],
        fields if fields is not None else {"name": "string"},
    )


def test_valid_complete_proposal_is_ready_and_report_serializes():
    report = validate(proposal([mapping("xlsx:Sheet1!A1")]))
    assert report.ready_for_review is True
    assert report.status == "ready"
    assert json.loads(json.dumps(report.to_dict()))["status"] == "ready"


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
    assert "unsupported_allowed_field_type" in report.structural_errors


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
    assert "target_not_writable:read-only" in report.structural_errors
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


def test_skips_required_optional_approved_duplicate_unknown_and_conflict():
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
    assert "required" in report.skipped_unapproved
    assert "optional" in report.skipped_unapproved
    assert "approved" in report.duplicates
    assert "target_mapped_and_skipped:approved" in report.structural_errors
    assert "required" in report.missing_required
    assert report.ready_for_review is False


def test_approved_optional_skip_satisfies_only_that_target():
    report = validate(
        proposal(skipped=["optional"]),
        [target("required"), target("optional", required=False, approved=True)],
        {"name": "string"},
    )
    assert report.missing_required == ("required",)
    assert report.skipped_unapproved == ()
    assert report.status == "incomplete"


def test_5_of_20_regression_reports_exactly_15_missing_and_not_ready():
    manifest = [target(f"xlsx:Sheet1!A{index}") for index in range(1, 21)]
    fields = {f"field_{index}": "string" for index in range(1, 6)}
    mappings = [mapping(f"xlsx:Sheet1!A{index}", f"field_{index}") for index in range(1, 6)]
    report = validate(proposal(mappings), manifest, fields)
    assert report.missing_required == tuple(f"xlsx:Sheet1!A{index}" for index in range(6, 21))
    assert len(report.missing_required) == 15
    assert report.status == "incomplete"
    assert report.ready_for_review is False


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
