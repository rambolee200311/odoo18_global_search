"""Fail-closed validation for untrusted mapping proposals and user edits."""

from collections.abc import Mapping, Sequence
from typing import Any

from .contracts import (
    CLARIFICATION_KEYS,
    CLARIFICATION_REASON_CODES,
    MAPPING_KEYS,
    MAPPING_SCHEMA_VERSION,
    ParseLimits,
    ROOT_KEYS,
    SUPPORTED_VALUE_TYPES,
    ValidationReport,
)


def _append_once(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)


def _normalize_manifest(target_manifest: Any) -> tuple[list[dict[str, Any]], list[str]]:
    errors: list[str] = []
    if not isinstance(target_manifest, Sequence) or isinstance(target_manifest, (str, bytes)):
        return [], ["invalid_target_manifest"]
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    expected = {"element_id", "required", "writable", "allowed_value_types", "approved_to_skip"}
    for item in target_manifest:
        if not isinstance(item, Mapping) or set(item) != expected:
            _append_once(errors, "invalid_target_spec")
            continue
        element_id = item["element_id"]
        required = item["required"]
        writable = item["writable"]
        approved_to_skip = item["approved_to_skip"]
        value_types = item["allowed_value_types"]
        if not isinstance(element_id, str) or not element_id.strip():
            _append_once(errors, "invalid_target_id")
            continue
        if any(type(flag) is not bool for flag in (required, writable, approved_to_skip)):
            _append_once(errors, "invalid_target_flags")
            continue
        if not isinstance(value_types, Sequence) or isinstance(value_types, (str, bytes)):
            _append_once(errors, "invalid_target_types")
            continue
        if any(not isinstance(value_type, str) or value_type not in SUPPORTED_VALUE_TYPES for value_type in value_types):
            _append_once(errors, "unsupported_target_type")
            continue
        if element_id in seen:
            _append_once(errors, "duplicate_manifest_target")
            continue
        seen.add(element_id)
        normalized.append(
            {
                "element_id": element_id,
                "required": required,
                "writable": writable,
                "allowed_value_types": tuple(value_types),
                "approved_to_skip": approved_to_skip,
            }
        )
    return normalized, errors


def _normalize_allowed_fields(allowed_fields: Any) -> tuple[dict[str, str], list[str]]:
    errors: list[str] = []
    if not isinstance(allowed_fields, Mapping):
        return {}, ["invalid_allowed_fields"]
    normalized: dict[str, str] = {}
    for field_id, value_type in allowed_fields.items():
        if not isinstance(field_id, str) or not field_id.strip():
            _append_once(errors, "invalid_allowed_field_id")
            continue
        if not isinstance(value_type, str) or value_type not in SUPPORTED_VALUE_TYPES:
            _append_once(errors, "unsupported_allowed_field_type")
            continue
        normalized[field_id] = value_type
    return normalized, errors


def _proposal_shape_errors(proposal: Any) -> tuple[list[str], list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    errors: list[str] = []
    if not isinstance(proposal, Mapping):
        return ["invalid_proposal_object"], [], [], []
    if set(proposal) != ROOT_KEYS:
        _append_once(errors, "invalid_proposal_keys")
    if proposal.get("schema_version") != MAPPING_SCHEMA_VERSION:
        _append_once(errors, "unsupported_schema_version")
    mappings = proposal.get("mappings")
    clarifications = proposal.get("clarifications")
    skipped = proposal.get("skipped_targets")
    if not isinstance(mappings, list):
        _append_once(errors, "invalid_mappings")
        mappings = []
    if not isinstance(clarifications, list):
        _append_once(errors, "invalid_clarifications")
        clarifications = []
    if not isinstance(skipped, list):
        _append_once(errors, "invalid_skipped_targets")
        skipped = []
    return errors, mappings, clarifications, skipped


def validate_proposal(
    proposal: Any,
    target_manifest: Sequence[Mapping[str, Any]],
    allowed_fields: Mapping[str, str],
) -> ValidationReport:
    """Validate schema, membership, type compatibility and completeness.

    `allowed_fields` maps a server-authorized field ID to its already
    normalized M1 value type. No ACL check or type conversion occurs here.
    """

    manifest, manifest_errors = _normalize_manifest(target_manifest)
    fields, field_errors = _normalize_allowed_fields(allowed_fields)
    shape_errors, mappings, clarifications, skipped = _proposal_shape_errors(proposal)
    structural_errors = manifest_errors + field_errors + shape_errors
    if not structural_errors:
        if len(mappings) > ParseLimits().max_mappings:
            _append_once(structural_errors, "too_many_mappings")
        if len(clarifications) > ParseLimits().max_clarifications:
            _append_once(structural_errors, "too_many_clarifications")
        if len(skipped) > ParseLimits().max_skipped_targets:
            _append_once(structural_errors, "too_many_skipped_targets")
    if structural_errors:
        return ValidationReport(structural_errors=tuple(structural_errors))

    targets = {target["element_id"]: target for target in manifest}
    unknown_targets: list[str] = []
    unknown_fields: list[str] = []
    type_errors: list[str] = []
    duplicates: list[str] = []
    skipped_unapproved: list[str] = []
    valid_candidates: dict[str, bool] = {}

    for mapping in mappings:
        if not isinstance(mapping, Mapping) or set(mapping) != MAPPING_KEYS:
            _append_once(structural_errors, "invalid_mapping_shape")
            continue
        element_id = mapping["element_id"]
        source_field = mapping["source_field"]
        value_type = mapping["value_type"]
        if not isinstance(element_id, str) or not element_id.strip():
            _append_once(structural_errors, "invalid_mapping_target")
            continue
        if element_id in valid_candidates:
            _append_once(duplicates, element_id)
            valid_candidates[element_id] = False
            continue
        valid_candidates[element_id] = False
        target = targets.get(element_id)
        if target is None:
            _append_once(unknown_targets, element_id)
            continue
        if not target["writable"]:
            _append_once(structural_errors, f"target_not_writable:{element_id}")
            continue
        if not isinstance(source_field, str) or not source_field.strip() or source_field not in fields:
            _append_once(unknown_fields, source_field if isinstance(source_field, str) else "<invalid>")
            continue
        if not isinstance(value_type, str) or value_type not in SUPPORTED_VALUE_TYPES:
            _append_once(type_errors, f"unsupported_value_type:{element_id}")
            continue
        if fields[source_field] != value_type or value_type not in target["allowed_value_types"]:
            _append_once(type_errors, f"type_mismatch:{element_id}")
            continue
        valid_candidates[element_id] = True

    pending_clarifications: list[str] = []
    for clarification in clarifications:
        if not isinstance(clarification, Mapping) or set(clarification) != CLARIFICATION_KEYS:
            _append_once(structural_errors, "invalid_clarification_shape")
            continue
        element_id = clarification["element_id"]
        reason_code = clarification["reason_code"]
        question = clarification["question"]
        if not isinstance(element_id, str) or not element_id.strip():
            _append_once(structural_errors, "invalid_clarification_target")
            continue
        if element_id not in targets:
            _append_once(unknown_targets, element_id)
            continue
        if not isinstance(reason_code, str) or reason_code not in CLARIFICATION_REASON_CODES:
            _append_once(structural_errors, f"invalid_clarification_reason:{element_id}")
            continue
        if not isinstance(question, str) or not question.strip() or len(question) > 2_000:
            _append_once(structural_errors, f"invalid_clarification_question:{element_id}")
            continue
        _append_once(pending_clarifications, element_id)

    skipped_ids: set[str] = set()
    for element_id in skipped:
        if not isinstance(element_id, str) or not element_id.strip():
            _append_once(structural_errors, "invalid_skipped_target")
            continue
        if element_id in skipped_ids:
            _append_once(duplicates, element_id)
            continue
        skipped_ids.add(element_id)
        target = targets.get(element_id)
        if target is None:
            _append_once(unknown_targets, element_id)
            continue
        if target["required"] or not target["approved_to_skip"]:
            _append_once(skipped_unapproved, element_id)

    for element_id in skipped_ids.intersection(valid_candidates):
        _append_once(structural_errors, f"target_mapped_and_skipped:{element_id}")

    valid_mapped = {element_id for element_id, valid in valid_candidates.items() if valid}
    approved_skips = {
        element_id
        for element_id in skipped_ids
        if element_id in targets
        and not targets[element_id]["required"]
        and targets[element_id]["approved_to_skip"]
    }
    missing_required = [
        target["element_id"]
        for target in manifest
        if target["required"]
        and target["element_id"] not in valid_mapped
        and target["element_id"] not in approved_skips
    ]
    ready = not any(
        (
            structural_errors,
            unknown_targets,
            unknown_fields,
            type_errors,
            duplicates,
            missing_required,
            pending_clarifications,
            skipped_unapproved,
        )
    )
    return ValidationReport(
        structural_errors=tuple(structural_errors),
        unknown_targets=tuple(unknown_targets),
        unknown_fields=tuple(unknown_fields),
        type_errors=tuple(type_errors),
        duplicates=tuple(duplicates),
        missing_required=tuple(missing_required),
        clarifications=tuple(pending_clarifications),
        skipped_unapproved=tuple(skipped_unapproved),
        ready_for_review=ready,
    )


def validate_user_revision(
    revision: Any,
    edits: Any,
    target_manifest: Sequence[Mapping[str, Any]],
    allowed_fields: Mapping[str, str],
) -> ValidationReport:
    """Apply untrusted mapping edits and validate the resulting revision."""

    if not isinstance(revision, Mapping) or set(revision) != ROOT_KEYS:
        return ValidationReport(structural_errors=("invalid_revision",))
    base_mappings = revision.get("mappings")
    if not isinstance(base_mappings, list):
        return ValidationReport(structural_errors=("invalid_revision_mappings",))
    if len(base_mappings) > ParseLimits().max_mappings:
        return ValidationReport(structural_errors=("too_many_mappings",))
    base_clarifications = revision.get("clarifications")
    base_skipped = revision.get("skipped_targets")
    if not isinstance(base_clarifications, list) or not isinstance(base_skipped, list):
        return ValidationReport(structural_errors=("invalid_revision_state",))
    if not isinstance(edits, list):
        return ValidationReport(structural_errors=("invalid_edits",))
    manifest, manifest_errors = _normalize_manifest(target_manifest)
    if manifest_errors:
        return ValidationReport(structural_errors=tuple(manifest_errors))
    if len(edits) > ParseLimits().max_mappings:
        return ValidationReport(structural_errors=("too_many_edits",))

    edited_ids: set[str] = set()
    replacement_by_id: dict[str, dict[str, Any]] = {}
    for edit in edits:
        if not isinstance(edit, Mapping) or set(edit) != MAPPING_KEYS:
            return ValidationReport(structural_errors=("invalid_edit_shape",))
        element_id = edit["element_id"]
        if not isinstance(element_id, str) or not element_id.strip():
            return ValidationReport(structural_errors=("invalid_edit_target",))
        if element_id in edited_ids:
            return ValidationReport(duplicates=(element_id,))
        edited_ids.add(element_id)
        replacement_by_id[element_id] = dict(edit)

    updated_mappings: list[dict[str, Any]] = []
    for mapping in base_mappings:
        if not isinstance(mapping, Mapping) or set(mapping) != MAPPING_KEYS:
            return ValidationReport(structural_errors=("invalid_revision_mapping_shape",))
        element_id = mapping["element_id"]
        if not isinstance(element_id, str):
            return ValidationReport(structural_errors=("invalid_revision_mapping_target",))
        updated_mappings.append(replacement_by_id.pop(element_id, dict(mapping)))
    updated_mappings.extend(replacement_by_id.values())

    updated = dict(revision)
    updated["mappings"] = updated_mappings
    updated["clarifications"] = [
        item
        for item in base_clarifications
        if not isinstance(item, Mapping)
        or not isinstance(item.get("element_id"), str)
        or item.get("element_id") not in edited_ids
    ]
    updated["skipped_targets"] = [
        target_id for target_id in base_skipped if not isinstance(target_id, str) or target_id not in edited_ids
    ]
    return validate_proposal(updated, manifest, allowed_fields)


def apply_manual_edits(
    proposal: Any,
    edits: Any,
    target_manifest: Sequence[Mapping[str, Any]],
    allowed_fields: Mapping[str, str],
) -> ValidationReport:
    """Compatibility alias for the TDD §3.2 name."""

    return validate_user_revision(proposal, edits, target_manifest, allowed_fields)
