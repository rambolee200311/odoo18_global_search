"""Strict JSON decoding and bounded structural validation."""

import json
from typing import Any

from .contracts import (
    CLARIFICATION_KEYS,
    CLARIFICATION_REASON_CODES,
    MAPPING_KEYS,
    MAPPING_SCHEMA_VERSION,
    ROOT_KEYS,
    SUPPORTED_VALUE_TYPES,
    MappingParseError,
    ParseLimits,
)


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
    if set(proposal) != ROOT_KEYS:
        raise MappingParseError("invalid_root_keys")
    if proposal["schema_version"] != MAPPING_SCHEMA_VERSION:
        raise MappingParseError("unsupported_schema_version")

    mappings = proposal["mappings"]
    clarifications = proposal["clarifications"]
    skipped_targets = proposal["skipped_targets"]
    if not isinstance(mappings, list):
        raise MappingParseError("mappings_must_be_array")
    if not isinstance(clarifications, list):
        raise MappingParseError("clarifications_must_be_array")
    if not isinstance(skipped_targets, list):
        raise MappingParseError("skipped_targets_must_be_array")
    if len(mappings) > active_limits.max_mappings:
        raise MappingParseError("too_many_mappings")
    if len(clarifications) > active_limits.max_clarifications:
        raise MappingParseError("too_many_clarifications")
    if len(skipped_targets) > active_limits.max_skipped_targets:
        raise MappingParseError("too_many_skipped_targets")

    for mapping in mappings:
        item = _require_exact_keys(mapping, MAPPING_KEYS, "invalid_mapping_shape")
        _require_text(item["element_id"], active_limits.max_identifier_chars, "invalid_element_id")
        _require_text(item["source_field"], active_limits.max_identifier_chars, "invalid_source_field")
        value_type = _require_text(item["value_type"], active_limits.max_identifier_chars, "invalid_value_type")
        if value_type not in SUPPORTED_VALUE_TYPES:
            raise MappingParseError("unsupported_value_type")

    for clarification in clarifications:
        item = _require_exact_keys(clarification, CLARIFICATION_KEYS, "invalid_clarification_shape")
        _require_text(item["element_id"], active_limits.max_identifier_chars, "invalid_clarification_target")
        reason_code = _require_text(item["reason_code"], 64, "invalid_clarification_reason")
        if reason_code not in CLARIFICATION_REASON_CODES:
            raise MappingParseError("unsupported_clarification_reason")
        _require_text(item["question"], active_limits.max_question_chars, "invalid_clarification_question")

    for target_id in skipped_targets:
        _require_text(target_id, active_limits.max_identifier_chars, "invalid_skipped_target")
    return proposal
