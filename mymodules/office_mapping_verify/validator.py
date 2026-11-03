"""Fail-closed validation for untrusted mapping proposals and user edits."""

from collections.abc import Mapping, Sequence
import re
from typing import Any

from .contracts import (
    CLARIFICATION_KEYS,
    CLARIFICATION_REASON_CODES,
    EXTENDED_ROOT_KEYS,
    has_valid_root_keys,
    FALLBACK_MAPPING_KEYS,
    FORMULA_MAPPING_KEYS,
    LITERAL_MAPPING_KEYS,
    MAPPING_KEYS,
    MAPPING_KEY_SHAPES,
    MAPPING_SCHEMA_VERSION,
    ParseLimits,
    ROOT_KEYS,
    SUPPORTED_VALUE_TYPES,
    TARGET_VALUE_TYPES,
    ValidationReport,
    normalize_empty_value_mappings,
)
from .formula import formula_references


def _append_once(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)


def _mapping_shape(mapping: Any) -> frozenset[str] | None:
    if not isinstance(mapping, Mapping):
        return None
    keys = frozenset(mapping)
    return keys if keys in MAPPING_KEY_SHAPES else None


def _normalize_manifest(target_manifest: Any) -> tuple[list[dict[str, Any]], list[str]]:
    errors: list[str] = []
    if not isinstance(target_manifest, Sequence) or isinstance(target_manifest, (str, bytes)):
        return [], ["invalid_target_manifest"]
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    expected = {"element_id", "required", "writable", "allowed_value_types", "approved_to_skip"}
    optional = {
        "merge_range", "write_target", "visual_labels", "table_role", "table_header"
    }
    for item in target_manifest:
        if (
            not isinstance(item, Mapping)
            or not expected.issubset(item)
            or set(item) - expected - optional
        ):
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
        if any(not isinstance(value_type, str) or value_type not in TARGET_VALUE_TYPES for value_type in value_types):
            _append_once(errors, "unsupported_target_type")
            continue
        if element_id in seen:
            _append_once(errors, "duplicate_manifest_target")
            continue
        merge_range = item.get("merge_range")
        write_target = item.get("write_target")
        visual_labels = item.get("visual_labels", [])
        table_role = item.get("table_role")
        table_header = item.get("table_header")
        if (
            (merge_range is not None and (
                not isinstance(merge_range, str)
                or len(merge_range) > 32
                or not re.fullmatch(r"[A-Z]{1,3}[1-9][0-9]*:[A-Z]{1,3}[1-9][0-9]*", merge_range)
            ))
            or (write_target is not None and write_target != element_id)
            or not isinstance(visual_labels, Sequence)
            or isinstance(visual_labels, (str, bytes))
            or len(visual_labels) > 3
            or any(
                not isinstance(label, Mapping)
                or set(label) != {"element_id", "text", "relation"}
                or not isinstance(label.get("element_id"), str)
                or len(label["element_id"]) > 512
                or not isinstance(label.get("text"), str)
                or len(label["text"]) > 300
                or not isinstance(label.get("relation"), str)
                or label.get("relation") not in {"same_row_left", "same_column_above", "above_merged_region"}
                for label in visual_labels
            )
            or (table_role is not None and table_role not in {"table_header", "table_data"})
            or (table_header is not None and (not isinstance(table_header, str) or len(table_header) > 600))
        ):
            _append_once(errors, "invalid_target_metadata")
            continue
        seen.add(element_id)
        normalized_target = {
            "element_id": element_id,
            "required": required,
            "writable": writable,
            "allowed_value_types": tuple(value_types),
            "approved_to_skip": approved_to_skip,
        }
        if "merge_range" in item:
            normalized_target["merge_range"] = merge_range
        if "write_target" in item:
            normalized_target["write_target"] = write_target
        if "visual_labels" in item:
            normalized_target["visual_labels"] = tuple(dict(label) for label in visual_labels)
        if table_role is not None:
            normalized_target["table_role"] = table_role
        if table_header is not None:
            normalized_target["table_header"] = table_header
        normalized.append(normalized_target)
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


def _proposal_shape_errors(
    proposal: Any,
) -> tuple[list[str], list[dict[str, Any]], list[dict[str, Any]], list[str], list[str], list[dict[str, Any]]]:
    errors: list[str] = []
    if not isinstance(proposal, Mapping):
        return ["invalid_proposal_object"], [], [], [], [], []
    proposal = normalize_empty_value_mappings(proposal)
    if not has_valid_root_keys(set(proposal)):
        _append_once(errors, "invalid_proposal_keys")
    if proposal.get("schema_version") != MAPPING_SCHEMA_VERSION:
        _append_once(errors, "unsupported_schema_version")
    mappings = proposal.get("mappings")
    clarifications = proposal.get("clarifications")
    skipped = proposal.get("skipped_targets")
    clear_targets = proposal.get("clear_targets", [])
    clear_columns = proposal.get("clear_columns", [])
    format_patches = proposal.get("format_patches", [])
    if not isinstance(mappings, list):
        _append_once(errors, "invalid_mappings")
        mappings = []
    if not isinstance(clarifications, list):
        _append_once(errors, "invalid_clarifications")
        clarifications = []
    if not isinstance(skipped, list):
        _append_once(errors, "invalid_skipped_targets")
        skipped = []
    if not isinstance(clear_targets, list):
        _append_once(errors, "invalid_clear_targets")
        clear_targets = []
    if not isinstance(clear_columns, list):
        _append_once(errors, "invalid_clear_columns")
        clear_columns = []
    if not isinstance(format_patches, list):
        _append_once(errors, "invalid_format_patches")
        format_patches = []
    return errors, mappings, clarifications, skipped, clear_targets, format_patches


def expand_table_column_operations(
    proposal: Mapping[str, Any], manifest: Sequence[Mapping[str, Any]]
) -> tuple[dict[str, Any], list[str]]:
    """Expand explicit column operations only to detected table data cells.

    The template reader supplies ``table_role`` and coordinate IDs. Header
    cells, unrelated regions, and cells outside the detected table body never
    become column operation targets.
    """
    if not isinstance(proposal, Mapping):
        return proposal, []
    result = dict(proposal)
    targets = list(manifest)
    errors: list[str] = []

    def column_targets(sheet, column):
        return [
            item["element_id"]
            for item in targets
            if item.get("table_role") == "table_data"
            and item.get("writable") is True
            and isinstance(item.get("element_id"), str)
            and (match := re.fullmatch(r"xlsx:(.+)!([A-Z]{1,3})[1-9][0-9]*", item["element_id"]))
            and match.group(1) == sheet
            and match.group(2) == column
        ]

    clear_targets = list(result.get("clear_targets", []))
    for column_spec in result.pop("clear_columns", []):
        if not isinstance(column_spec, Mapping) or set(column_spec) != {"sheet", "column"}:
            _append_once(errors, "invalid_clear_column_shape")
            continue
        sheet, column = column_spec.get("sheet"), column_spec.get("column")
        matches = column_targets(sheet, column)
        if not matches:
            _append_once(errors, "clear_column_not_in_detected_table")
        clear_targets.extend(matches)
    if clear_targets or "clear_targets" in result:
        # Preserve duplicates for the validator to report as an explicit
        # conflict instead of silently normalizing a malformed patch.
        result["clear_targets"] = clear_targets

    expanded_formats: list[dict[str, Any]] = []
    for patch in result.get("format_patches", []):
        if not isinstance(patch, Mapping):
            _append_once(errors, "invalid_format_patch_shape")
            continue
        if set(patch) == {"element_id", "number_format"}:
            expanded_formats.append(dict(patch))
        elif set(patch) == {"sheet", "column", "number_format"}:
            matches = column_targets(patch.get("sheet"), patch.get("column"))
            if not matches:
                _append_once(errors, "format_column_not_in_detected_table")
            expanded_formats.extend(
                {"element_id": element_id, "number_format": patch["number_format"]}
                for element_id in matches
            )
        else:
            _append_once(errors, "invalid_format_patch_shape")
    if expanded_formats or "format_patches" in result:
        result["format_patches"] = expanded_formats
    return result, errors


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
    expanded_proposal, column_errors = expand_table_column_operations(proposal, manifest)
    shape_errors, mappings, clarifications, skipped, clear_targets, format_patches = _proposal_shape_errors(expanded_proposal)
    structural_errors = manifest_errors + field_errors + column_errors + shape_errors
    if not structural_errors:
        if len(mappings) > ParseLimits().max_mappings:
            _append_once(structural_errors, "too_many_mappings")
        if len(clarifications) > ParseLimits().max_clarifications:
            _append_once(structural_errors, "too_many_clarifications")
        if len(skipped) > ParseLimits().max_skipped_targets:
            _append_once(structural_errors, "too_many_skipped_targets")
        if len(clear_targets) > ParseLimits().max_skipped_targets:
            _append_once(structural_errors, "too_many_clear_targets")
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
        shape = _mapping_shape(mapping)
        if shape is None:
            _append_once(structural_errors, "invalid_mapping_shape")
            continue
        element_id = mapping["element_id"]
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
        if target.get("table_role") == "table_header":
            _append_once(type_errors, f"target_not_writable:{element_id}")
            continue
        if shape == MAPPING_KEYS:
            source_field = mapping["source_field"]
            if not isinstance(source_field, str) or not source_field.strip() or source_field not in fields:
                _append_once(unknown_fields, source_field if isinstance(source_field, str) else "<invalid>")
                continue
            if not isinstance(value_type, str) or value_type not in SUPPORTED_VALUE_TYPES:
                _append_once(type_errors, f"unsupported_value_type:{element_id}")
                continue
            if fields[source_field] != value_type or value_type not in target["allowed_value_types"]:
                _append_once(type_errors, f"type_mismatch:{element_id}")
                continue
        elif shape == FALLBACK_MAPPING_KEYS:
            sources = mapping["source_fields"]
            if (
                not isinstance(sources, list)
                or not 2 <= len(sources) <= 8
                or any(not isinstance(source, str) or not source.strip() for source in sources)
                or len(set(sources)) != len(sources)
            ):
                _append_once(structural_errors, f"invalid_source_fields:{element_id}")
                continue
            missing_sources = [source for source in sources if source not in fields]
            for source in missing_sources:
                _append_once(unknown_fields, source)
            if missing_sources:
                continue
            if not isinstance(value_type, str) or value_type not in SUPPORTED_VALUE_TYPES:
                _append_once(type_errors, f"unsupported_value_type:{element_id}")
                continue
            if (
                any(fields[source] != value_type for source in sources)
                or value_type not in target["allowed_value_types"]
            ):
                _append_once(type_errors, f"type_mismatch:{element_id}")
                continue
        elif shape == FORMULA_MAPPING_KEYS:
            try:
                formula_references(mapping["formula"])
            except (KeyError, ValueError):
                _append_once(structural_errors, f"invalid_formula:{element_id}")
                continue
            if value_type != "formula" or value_type not in target["allowed_value_types"]:
                _append_once(type_errors, f"type_mismatch:{element_id}")
                continue
        else:
            literal = mapping["literal_value"]
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
                _append_once(type_errors, f"invalid_literal_value:{element_id}")
                continue
            if value_type not in target["allowed_value_types"]:
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
        # Skip declarations are descriptive. Template-required and
        # approved_to_skip metadata do not control user-authored operations.

    clear_ids: set[str] = set()
    for element_id in clear_targets:
        if not isinstance(element_id, str) or not element_id.strip():
            _append_once(structural_errors, "invalid_clear_target")
            continue
        if element_id in clear_ids:
            _append_once(duplicates, f"duplicate_clear_target:{element_id}")
            continue
        clear_ids.add(element_id)
        target = targets.get(element_id)
        if target is None:
            _append_once(unknown_targets, element_id)
            continue
        if target.get("table_role") == "table_header":
            _append_once(type_errors, f"target_not_writable:{element_id}")
        # A clear is an explicit string write. It may replace existing values
        # or formulas regardless of template labels or the old writability bit.

    format_ids: set[str] = set()
    for patch in format_patches:
        if not isinstance(patch, Mapping) or set(patch) != {"element_id", "number_format"}:
            _append_once(structural_errors, "invalid_format_patch_shape")
            continue
        element_id = patch.get("element_id")
        number_format = patch.get("number_format")
        if not isinstance(element_id, str) or not element_id.strip():
            _append_once(structural_errors, "invalid_format_patch_target")
            continue
        if element_id in format_ids:
            _append_once(duplicates, f"duplicate_format_patch:{element_id}")
            continue
        format_ids.add(element_id)
        target = targets.get(element_id)
        if target is None:
            _append_once(unknown_targets, element_id)
            continue
        if target.get("table_role") == "table_header":
            _append_once(type_errors, f"target_not_writable:{element_id}")
        if (
            not isinstance(number_format, str)
            or not number_format
            or len(number_format) > 128
            or any(ord(char) < 32 for char in number_format)
        ):
            _append_once(type_errors, f"invalid_number_format:{element_id}")

    for element_id in clear_ids.intersection(valid_candidates):
        _append_once(structural_errors, f"target_mapped_and_cleared:{element_id}")
    for element_id in clear_ids.intersection(skipped_ids):
        _append_once(structural_errors, f"target_skipped_and_cleared:{element_id}")

    for element_id in skipped_ids.intersection(valid_candidates):
        _append_once(structural_errors, f"target_mapped_and_skipped:{element_id}")

    valid_mapped = {element_id for element_id, valid in valid_candidates.items() if valid}
    # A template label is descriptive metadata, not a business requirement.
    # The business instruction decides which writable targets to populate;
    # omitted targets remain unchanged unless explicitly listed in clear_targets.
    missing_required: list[str] = []
    ready = not any(
        (
            structural_errors,
            unknown_targets,
            unknown_fields,
            type_errors,
            duplicates,
            missing_required,
            pending_clarifications,
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

    if not isinstance(revision, Mapping) or not has_valid_root_keys(set(revision)):
        return ValidationReport(structural_errors=("invalid_revision",))
    base_mappings = revision.get("mappings")
    if not isinstance(base_mappings, list):
        return ValidationReport(structural_errors=("invalid_revision_mappings",))
    if len(base_mappings) > ParseLimits().max_mappings:
        return ValidationReport(structural_errors=("too_many_mappings",))
    base_clarifications = revision.get("clarifications")
    base_skipped = revision.get("skipped_targets")
    base_clear_targets = revision.get("clear_targets", [])
    if (
        not isinstance(base_clarifications, list)
        or not isinstance(base_skipped, list)
        or not isinstance(base_clear_targets, list)
    ):
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
        if _mapping_shape(edit) is None:
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
        if _mapping_shape(mapping) is None:
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
    if "clear_targets" in updated:
        updated["clear_targets"] = [
            target_id
            for target_id in base_clear_targets
            if not isinstance(target_id, str) or target_id not in edited_ids
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
