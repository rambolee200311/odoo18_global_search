import json
from dataclasses import replace

import pytest

from mymodules.office_mapping_verify import (
    MAPPING_SCHEMA_VERSION,
    MappingParseError,
    ParseLimits,
    parse_mapping_proposal,
)


def proposal(**overrides):
    value = {
        "schema_version": MAPPING_SCHEMA_VERSION,
        "mappings": [{"element_id": "xlsx:Sheet1!A1", "source_field": "name", "value_type": "string"}],
        "clarifications": [],
        "skipped_targets": [],
    }
    value.update(overrides)
    return value


def raw(value):
    return json.dumps(value, ensure_ascii=False)


def assert_parse_error(text, code, limits=None):
    with pytest.raises(MappingParseError) as error:
        parse_mapping_proposal(text, limits)
    assert error.value.code == code


def test_parse_valid_exact_proposal_and_utf8_bytes():
    value = proposal(
        mappings=[{"element_id": "xlsx:Sheet1!客户", "source_field": "partner.name", "value_type": "string"}],
        clarifications=[{
            "element_id": "xlsx:Sheet1!B1",
            "reason_code": "missing_source",
            "question": "客户名称来自哪个字段？",
        }],
        skipped_targets=["xlsx:Sheet1!C1"],
    )
    parsed = parse_mapping_proposal(raw(value))
    assert parsed == value


def test_parse_explicit_clear_targets():
    value = proposal(mappings=[], clear_targets=["xlsx:Sheet1!F17"])
    assert parse_mapping_proposal(raw(value)) == value


def test_parse_empty_value_mapping_as_explicit_clear_target():
    value = proposal(mappings=[{"element_id": "xlsx:Sheet1!F17", "value": ""}])
    parsed = parse_mapping_proposal(raw(value))
    assert parsed["mappings"] == []
    assert parsed["clear_targets"] == ["xlsx:Sheet1!F17"]


def test_parse_number_format_patch():
    parsed = parse_mapping_proposal(raw(proposal(mappings=[], format_patches=[
        {"element_id": "xlsx:Sheet1!B2", "number_format": "0.0"}
    ])))
    assert parsed["format_patches"] == [
        {"element_id": "xlsx:Sheet1!B2", "number_format": "0.0"}
    ]


def test_parse_explicit_header_text_edit():
    value = proposal(
        mappings=[],
        header_edits=[{"element_id": "xlsx:Orders!F1", "value": "供应商商品描述"}],
    )
    parsed = parse_mapping_proposal(raw(value))
    assert parsed["cell_edits"] == [
        {"element_id": "xlsx:Orders!F1", "value": "供应商商品描述", "value_type": "string"}
    ]
    assert "header_edits" not in parsed


def test_parse_generic_explicit_cell_edit():
    value = proposal(
        mappings=[],
        cell_edits=[
            {"element_id": "xlsx:Orders!F1", "value": "供应商商品描述", "value_type": "string"}
        ],
    )
    assert parse_mapping_proposal(raw(value)) == value


def test_parse_concatenated_string_mapping_with_explicit_separator():
    value = proposal(mappings=[{
        "element_id": "xlsx:Sheet1!A1",
        "concat_fields": ["remark", "contact_name"],
        "separator": " ",
        "value_type": "string",
    }])
    assert parse_mapping_proposal(raw(value)) == value


def test_parse_record_relative_cell_edit_with_explicit_empty_value():
    value = proposal(
        mappings=[],
        cell_edits=[{
            "record_target": {"group_id": "repeat_rows", "record_id": 42, "column": "I"},
            "value": "",
            "value_type": "string",
        }],
    )
    assert parse_mapping_proposal(raw(value)) == value


@pytest.mark.parametrize(
    ("edit_value", "value_type"),
    [(0, "number"), (False, "boolean")],
)
def test_record_relative_cell_edit_preserves_zero_and_false_types(edit_value, value_type):
    value = proposal(mappings=[], cell_edits=[{
        "record_target": {"group_id": "repeat_rows", "record_id": 42, "column": "I"},
        "value": edit_value,
        "value_type": value_type,
    }])
    assert parse_mapping_proposal(raw(value)) == value


def test_record_relative_cell_edit_rejects_null_instead_of_treating_it_as_clear():
    value = proposal(mappings=[], cell_edits=[{
        "record_target": {"group_id": "repeat_rows", "record_id": 42, "column": "I"},
        "value": None,
        "value_type": "string",
    }])
    with pytest.raises(MappingParseError):
        parse_mapping_proposal(raw(value))


@pytest.mark.parametrize(
    "record_target",
    [
        {"group_id": "repeat_rows", "record_id": True, "column": "I"},
        {"group_id": "repeat_rows", "record_id": 0, "column": "I"},
        {"group_id": "repeat_rows", "record_id": 42, "column": "i"},
        {"group_id": "missing-group", "record_id": 42, "column": "I", "row": 2},
    ],
)
def test_parse_rejects_invalid_record_relative_cell_edit_target(record_target):
    value = proposal(mappings=[], cell_edits=[{
        "record_target": record_target,
        "value": "",
        "value_type": "string",
    }])
    with pytest.raises(MappingParseError):
        parse_mapping_proposal(raw(value))


@pytest.mark.parametrize(
    "header_edits",
    [
        [{"element_id": "xlsx:Orders!F1", "value": "two\nlines"}],
        [
            {"element_id": "xlsx:Orders!F1", "value": "first"},
            {"element_id": "xlsx:Orders!F1", "value": "second"},
        ],
    ],
)
def test_parse_rejects_invalid_or_duplicate_header_text_edits(header_edits):
    value = proposal(mappings=[], header_edits=header_edits)
    with pytest.raises(MappingParseError):
        parse_mapping_proposal(raw(value))


def test_parse_rejects_ambiguous_legacy_and_generic_edit_arrays():
    value = proposal(
        mappings=[],
        header_edits=[{"element_id": "xlsx:Orders!F1", "value": "Old"}],
        cell_edits=[{"element_id": "xlsx:Orders!F1", "value": "New", "value_type": "string"}],
    )
    with pytest.raises(MappingParseError) as error:
        parse_mapping_proposal(raw(value))
    assert error.value.code == "duplicate_explicit_cell_edit_location"


def test_parse_typed_empty_value_mapping_as_explicit_clear_target():
    value = proposal(
        mappings=[{"element_id": "xlsx:Sheet1!F17", "value": "", "value_type": "string"}]
    )
    parsed = parse_mapping_proposal(raw(value))
    assert parsed["mappings"] == []
    assert parsed["clear_targets"] == ["xlsx:Sheet1!F17"]


def test_parse_supported_field_fallback_and_bounded_arithmetic_formula():
    value = proposal(
        mappings=[
            {
                "element_id": "xlsx:Sheet1!C1",
                "source_fields": ["product_id.default_code", "product_id.barcode"],
                "value_type": "string",
            },
            {"element_id": "xlsx:Sheet1!G23", "formula": "=D23*E23*3", "value_type": "formula"},
        ]
    )
    assert parse_mapping_proposal(raw(value)) == value


def test_parse_typed_numeric_literal_mapping():
    value = proposal(
        mappings=[
            {"element_id": "xlsx:Sheet1!B4", "literal_value": 3329.15, "value_type": "number"}
        ]
    )
    assert parse_mapping_proposal(raw(value)) == value


def test_parse_canonicalizes_arithmetic_formula_without_leading_equals():
    value = proposal(
        mappings=[{"element_id": "xlsx:Sheet1!G23", "formula": "D23*E23*2", "value_type": "formula"}]
    )
    parsed = parse_mapping_proposal(raw(value))
    assert parsed["mappings"][0]["formula"] == "=D23*E23*2"


@pytest.mark.parametrize(
    "formula",
    [
        "=HYPERLINK(\"https://example.invalid\",\"x\")",
        "='Other Sheet'!A1",
        "=A1:B3",
        "=1+",
        "=A1+[cmd]Sheet1!B2",
    ],
)
def test_parse_rejects_unsafe_or_malformed_formula(formula):
    value = proposal(
        mappings=[{"element_id": "xlsx:Sheet1!C1", "formula": formula, "value_type": "formula"}]
    )
    assert_parse_error(raw(value), "invalid_formula")


@pytest.mark.parametrize("value,code", [(None, "invalid_input_type"), (b"{}", "invalid_input_type")])
def test_reject_non_text_input(value, code):
    assert_parse_error(value, code)


def test_reject_invalid_unicode():
    assert_parse_error('{"text":"\ud800"}', "invalid_unicode")


def test_reject_deeply_nested_json_without_leaking_recursion_error():
    assert_parse_error("[" * 1_100 + "]" * 1_100, "json_nesting_too_deep")


def test_reject_input_over_byte_limit_and_accept_exact_limit():
    limits = ParseLimits(max_json_bytes=32)
    assert_parse_error(" " * 33, "input_too_large", limits)
    exact = '{"schema_version":"m2.mapping-proposal.v1","mappings":[],"clarifications":[],"skipped_targets":[]}'
    assert_parse_error(exact, "input_too_large", limits)
    exact_limit = ParseLimits(max_json_bytes=len(raw(proposal()).encode("utf-8")))
    assert parse_mapping_proposal(raw(proposal()), exact_limit)["schema_version"] == MAPPING_SCHEMA_VERSION


def test_frozen_json_byte_cap_accepts_exactly_65536_and_rejects_one_more():
    base = raw(proposal(mappings=[]))
    exact = base + (" " * (65_536 - len(base.encode("utf-8"))))
    assert len(exact.encode("utf-8")) == 65_536
    assert parse_mapping_proposal(exact)["mappings"] == []
    assert_parse_error(exact + " ", "input_too_large")


@pytest.mark.parametrize(
    "text,code",
    [
        ("{", "invalid_json"),
        ('{"a":1,"a":2}', "duplicate_json_key"),
        ('{"a":{"b":1,"b":2}}', "duplicate_json_key"),
        ('{"schema_version":"m2.mapping-proposal.v1","mappings":[],"clarifications":[],"skipped_targets":[],}', "invalid_json"),
        ('{"v":NaN}', "invalid_json_constant:NaN"),
        ('{"v":Infinity}', "invalid_json_constant:Infinity"),
        ('{"v":-Infinity}', "invalid_json_constant:-Infinity"),
        ('```json\n{}\n```', "invalid_json"),
        ('prefix {}', "invalid_json"),
        ('{} suffix', "invalid_json"),
        ('"root"', "root_must_be_object"),
        ('[]', "root_must_be_object"),
    ],
)
def test_reject_json_ambiguity_or_wrong_root(text, code):
    assert_parse_error(text, code)


def test_reject_invalid_root_keys_and_version():
    assert_parse_error(raw({"schema_version": MAPPING_SCHEMA_VERSION}), "invalid_root_keys")
    value = proposal(schema_version="future.v9")
    assert_parse_error(raw(value), "unsupported_schema_version")


@pytest.mark.parametrize(
    "field,value,code",
    [
        ("mappings", {}, "mappings_must_be_array"),
        ("clarifications", {}, "clarifications_must_be_array"),
        ("skipped_targets", {}, "skipped_targets_must_be_array"),
    ],
)
def test_reject_non_array_collections(field, value, code):
    assert_parse_error(raw(proposal(**{field: value})), code)


@pytest.mark.parametrize(
    "field,limit,error_code,item_factory",
    [
        ("mappings", "max_mappings", "too_many_mappings", lambda i: {"element_id": f"t{i}", "source_field": "f", "value_type": "string"}),
        ("clarifications", "max_clarifications", "too_many_clarifications", lambda i: {"element_id": f"t{i}", "reason_code": "missing_source", "question": "q"}),
        ("skipped_targets", "max_skipped_targets", "too_many_skipped_targets", lambda i: f"t{i}"),
    ],
)
def test_collection_limits_accept_boundary_and_reject_over(field, limit, error_code, item_factory):
    limits = ParseLimits(**{limit: 1})
    one_item = [item_factory(0)]
    assert parse_mapping_proposal(raw(proposal(**{field: one_item})), limits)[field] == one_item
    two_items = [item_factory(0), item_factory(1)]
    assert_parse_error(raw(proposal(**{field: two_items})), error_code, limits)


def test_frozen_collection_caps_accept_exact_maxima():
    mappings = [{"element_id": f"t{i}", "source_field": "f", "value_type": "string"} for i in range(200)]
    clarifications = [
        {"element_id": "t", "reason_code": "missing_source", "question": "q"} for _ in range(100)
    ]
    skipped_targets = [f"t{i}" for i in range(200)]
    parsed = parse_mapping_proposal(
        raw(proposal(mappings=mappings, clarifications=clarifications, skipped_targets=skipped_targets))
    )
    assert len(parsed["mappings"]) == 200
    assert len(parsed["clarifications"]) == 100
    assert len(parsed["skipped_targets"]) == 200


def test_reject_bad_mapping_schema_and_values():
    cases = [
        ({"element_id": "t", "source_field": "f"}, "invalid_mapping_shape"),
        ({"element_id": "t", "source_field": "f", "value_type": "string", "value": "x"}, "invalid_mapping_shape"),
        ({"element_id": 2, "source_field": "f", "value_type": "string"}, "invalid_element_id"),
        ({"element_id": " ", "source_field": "f", "value_type": "string"}, "invalid_element_id"),
        ({"element_id": "t", "source_field": None, "value_type": "string"}, "invalid_source_field"),
        ({"element_id": "t", "source_field": 0, "value_type": "string"}, "invalid_source_field"),
        ({"element_id": "t", "source_field": "f", "value_type": " "}, "invalid_value_type"),
        ({"element_id": "t", "source_field": "f", "value_type": "binary"}, "unsupported_value_type"),
    ]
    for item, code in cases:
        assert_parse_error(raw(proposal(mappings=[item])), code)
    assert_parse_error(raw(proposal(mappings=[None])), "invalid_mapping_shape")
    for injected_value in (None, "", 0):
        assert_parse_error(
            raw(proposal(mappings=[{"element_id": "t", "source_field": "f", "value_type": "string", "value": injected_value}])),
            "invalid_mapping_shape",
        )


def test_reject_identifier_and_question_length_limits():
    limits = ParseLimits(max_identifier_chars=2, max_question_chars=3)
    assert_parse_error(raw(proposal(mappings=[{"element_id": "long", "source_field": "f", "value_type": "string"}])), "invalid_element_id", limits)
    assert_parse_error(raw(proposal(mappings=[], clarifications=[{"element_id": "t", "reason_code": "missing_source", "question": "long"}])), "invalid_clarification_question", limits)


def test_reject_bad_clarification_shape_reason_and_text():
    cases = [
        ({"element_id": "t"}, "invalid_clarification_shape"),
        ({"element_id": 1, "reason_code": "missing_source", "question": "q"}, "invalid_clarification_target"),
        ({"element_id": "t", "reason_code": "other", "question": "q"}, "unsupported_clarification_reason"),
        ({"element_id": "t", "reason_code": 3, "question": "q"}, "invalid_clarification_reason"),
        ({"element_id": "t", "reason_code": "missing_source", "question": " "}, "invalid_clarification_question"),
        ({"element_id": "t", "reason_code": "missing_source", "question": 5}, "invalid_clarification_question"),
    ]
    for item, code in cases:
        assert_parse_error(raw(proposal(clarifications=[item])), code)
    assert_parse_error(raw(proposal(clarifications=[None])), "invalid_clarification_shape")


def test_reject_invalid_skipped_target():
    assert_parse_error(raw(proposal(skipped_targets=[None])), "invalid_skipped_target")


@pytest.mark.parametrize("clear_targets,code", [
    (None, "clear_targets_must_be_array"),
    ([None], "invalid_clear_target"),
    ([""], "invalid_clear_target"),
])
def test_reject_invalid_clear_targets(clear_targets, code):
    assert_parse_error(raw(proposal(mappings=[], clear_targets=clear_targets)), code)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_json_bytes": True},
        {"max_mappings": 1.5},
        {"max_clarifications": 0},
        {"max_skipped_targets": -1},
        {"max_identifier_chars": "10"},
        {"max_question_chars": False},
    ],
)
def test_parse_limits_must_be_positive_non_boolean_integers(kwargs):
    with pytest.raises(ValueError, match="positive integers"):
        replace(ParseLimits(), **kwargs)
