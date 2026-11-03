"""Strict JSON decoding and bounded structural validation."""

import json
import re
from typing import Any

from .contracts import (
    CLARIFICATION_KEYS,
    CLARIFICATION_REASON_CODES,
    EXTENDED_ROOT_KEYS,
    FALLBACK_MAPPING_KEYS,
    FORMULA_MAPPING_KEYS,
    LITERAL_MAPPING_KEYS,
    MAPPING_KEYS,
    MAPPING_SCHEMA_VERSION,
    has_valid_root_keys,
    ROOT_KEYS,
    SUPPORTED_VALUE_TYPES,
    MappingParseError,
    ParseLimits,
    normalize_empty_value_mappings,
)
from .formula import formula_references


def _object_without_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise MappingParseError("duplicate_json_key")
        result[key] = value
    return result


def _reject_non_json_constant(value: str) -> None:
    raise MappingParseError(f"invalid_json_constant:{value}")


def _require_text(value: Any, limit: int, code: str) -> str:
    if not isinstance(value, str):
        raise MappingParseError(code)
    if not value or not value.strip() or len(value) > limit:
        raise MappingParseError(code)
    return value


def _require_exact_keys(value: Any, expected: frozenset[str], code: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise MappingParseError(code)
    if set(value) != expected:
        raise MappingParseError(code)
    return value


def parse_mapping_proposal(raw_text: str, limits: ParseLimits | None = None) -> dict[str, Any]:
    """Parse a single exact-schema JSON object or raise a stable error.

    No markdown stripping or best-effort repair is performed. The caller owns
    retries; this function accepts only bounded UTF-8 JSON with no duplicate
    object keys.
    """

    active_limits = limits if limits is not None else ParseLimits()
    if not isinstance(raw_text, str):
        raise MappingParseError("invalid_input_type")
    try:
        raw_size = len(raw_text.encode("utf-8"))
    except UnicodeEncodeError as error:
        raise MappingParseError("invalid_unicode") from error
    if raw_size > active_limits.max_json_bytes:
        raise MappingParseError("input_too_large")
    try:
        proposal = json.loads(
            raw_text,
            object_pairs_hook=_object_without_duplicate_keys,
            parse_constant=_reject_non_json_constant,
        )
    except MappingParseError:
        raise
    except json.JSONDecodeError as error:
        raise MappingParseError("invalid_json") from error
    except RecursionError as error:
        raise MappingParseError("json_nesting_too_deep") from error
    if not isinstance(proposal, dict):
        raise MappingParseError("root_must_be_object")
    if not has_valid_root_keys(set(proposal)):
        raise MappingParseError("invalid_root_keys")
    if proposal["schema_version"] != MAPPING_SCHEMA_VERSION:
        raise MappingParseError("unsupported_schema_version")
    proposal = normalize_empty_value_mappings(proposal)

    mappings = proposal["mappings"]
    clarifications = proposal["clarifications"]
    skipped_targets = proposal["skipped_targets"]
    clear_targets = proposal.get("clear_targets", [])
    clear_columns = proposal.get("clear_columns", [])
    format_patches = proposal.get("format_patches", [])
    if not isinstance(mappings, list):
        raise MappingParseError("mappings_must_be_array")
    if not isinstance(clarifications, list):
        raise MappingParseError("clarifications_must_be_array")
    if not isinstance(skipped_targets, list):
        raise MappingParseError("skipped_targets_must_be_array")
    if not isinstance(clear_targets, list):
        raise MappingParseError("clear_targets_must_be_array")
    if not isinstance(clear_columns, list):
        raise MappingParseError("clear_columns_must_be_array")
    if not isinstance(format_patches, list):
        raise MappingParseError("format_patches_must_be_array")
    if len(mappings) > active_limits.max_mappings:
        raise MappingParseError("too_many_mappings")
    if len(clarifications) > active_limits.max_clarifications:
        raise MappingParseError("too_many_clarifications")
    if len(skipped_targets) > active_limits.max_skipped_targets:
        raise MappingParseError("too_many_skipped_targets")
    if len(clear_targets) > active_limits.max_skipped_targets:
        raise MappingParseError("too_many_clear_targets")
    if len(clear_columns) > 64:
        raise MappingParseError("too_many_clear_columns")
    if len(format_patches) > active_limits.max_mappings:
        raise MappingParseError("too_many_format_patches")

    seen_clear_columns = set()
    for column in clear_columns:
        if not isinstance(column, dict) or set(column) != {"sheet", "column"}:
            raise MappingParseError("invalid_clear_column_shape")
        sheet = _require_text(column["sheet"], 255, "invalid_clear_column_sheet")
        letter = column["column"]
        if not isinstance(letter, str) or not re.fullmatch(r"[A-Z]{1,3}", letter):
            raise MappingParseError("invalid_clear_column_letter")
        identity = (sheet, letter)
        if identity in seen_clear_columns:
            raise MappingParseError("duplicate_clear_column")
        seen_clear_columns.add(identity)

    seen_format_targets = set()
    for patch in format_patches:
        direct_shape = isinstance(patch, dict) and set(patch) == {"element_id", "number_format"}
        column_shape = isinstance(patch, dict) and set(patch) == {"sheet", "column", "number_format"}
        if not (direct_shape or column_shape):
            raise MappingParseError("invalid_format_patch_shape")
        if direct_shape:
            target_key = _require_text(
                patch["element_id"], active_limits.max_identifier_chars, "invalid_format_patch_target"
            )
        else:
            target_key = _require_text(patch["sheet"], 255, "invalid_format_patch_sheet")
            if not isinstance(patch["column"], str) or not re.fullmatch(r"[A-Z]{1,3}", patch["column"]):
                raise MappingParseError("invalid_format_patch_column")
            target_key = f"{target_key}!{patch['column']}"
        number_format = patch["number_format"]
        if target_key in seen_format_targets:
            raise MappingParseError("duplicate_format_patch_target")
        if (
            not isinstance(number_format, str)
            or not number_format
            or len(number_format) > 128
            or any(ord(char) < 32 for char in number_format)
        ):
            raise MappingParseError("invalid_number_format")
        seen_format_targets.add(target_key)

    for mapping in mappings:
        if not isinstance(mapping, dict):
            raise MappingParseError("invalid_mapping_shape")
        keys = set(mapping)
        if keys not in (MAPPING_KEYS, FALLBACK_MAPPING_KEYS, FORMULA_MAPPING_KEYS, LITERAL_MAPPING_KEYS):
            raise MappingParseError("invalid_mapping_shape")
        item = mapping
        _require_text(item["element_id"], active_limits.max_identifier_chars, "invalid_element_id")
        value_type = _require_text(item["value_type"], active_limits.max_identifier_chars, "invalid_value_type")
        if keys == MAPPING_KEYS:
            _require_text(item["source_field"], active_limits.max_identifier_chars, "invalid_source_field")
            if value_type not in SUPPORTED_VALUE_TYPES:
                raise MappingParseError("unsupported_value_type")
        elif keys == FALLBACK_MAPPING_KEYS:
            sources = item["source_fields"]
            if (
                not isinstance(sources, list)
                or not 2 <= len(sources) <= 8
                or any(
                    not isinstance(source, str)
                    or not source.strip()
                    or len(source) > active_limits.max_identifier_chars
                    for source in sources
                )
                or len(set(sources)) != len(sources)
            ):
                raise MappingParseError("invalid_source_fields")
            if value_type not in SUPPORTED_VALUE_TYPES:
                raise MappingParseError("unsupported_value_type")
        elif keys == FORMULA_MAPPING_KEYS:
            formula = item["formula"]
            if not isinstance(formula, str) or not formula.strip() or len(formula) > 512:
                raise MappingParseError("invalid_formula")
            # Accept the common model shorthand `A1*B1*2`, while storing the
            # canonical Excel form used by the renderer and verifier.
            if not formula.startswith("="):
                item["formula"] = "=" + formula
            try:
                formula_references(item["formula"])
            except ValueError as error:
                raise MappingParseError("invalid_formula") from error
            if value_type != "formula":
                raise MappingParseError("invalid_formula_value_type")
        else:
            literal = item["literal_value"]
            valid_literal = (
                value_type == "string" and isinstance(literal, str)
            ) or (
                value_type == "number"
                and isinstance(literal, (int, float))
                and not isinstance(literal, bool)
            ) or (
                value_type == "boolean" and type(literal) is bool
            )
            if not valid_literal:
                raise MappingParseError("invalid_literal_value")

    for clarification in clarifications:
        item = _require_exact_keys(clarification, CLARIFICATION_KEYS, "invalid_clarification_shape")
        _require_text(item["element_id"], active_limits.max_identifier_chars, "invalid_clarification_target")
        reason_code = _require_text(item["reason_code"], 64, "invalid_clarification_reason")
        if reason_code not in CLARIFICATION_REASON_CODES:
            raise MappingParseError("unsupported_clarification_reason")
        _require_text(item["question"], active_limits.max_question_chars, "invalid_clarification_question")

    for target_id in skipped_targets:
        _require_text(target_id, active_limits.max_identifier_chars, "invalid_skipped_target")
    for target_id in clear_targets:
        _require_text(target_id, active_limits.max_identifier_chars, "invalid_clear_target")
    return proposal
