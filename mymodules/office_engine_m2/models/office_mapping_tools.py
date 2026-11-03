"""Office capabilities exposed through the native llm.tool execution loop."""

import hashlib
import json
import logging
import re

from odoo import _, models, tools
from odoo.addons.llm_tool.decorators import llm_tool
from odoo.exceptions import AccessError, UserError, ValidationError
from office_mapping_verify import (
    MappingParseError,
    ParseLimits,
    expand_table_column_operations,
    parse_mapping_proposal,
    validate_proposal,
)
from office_core import OfficeCoreError

from ..services.chat_entrypoint import (
    SELECTED_RECORDS_COLLECTION,
    _cell_coordinates,
    _field_metadata,
    _field_candidates,
    _repeat_row_collection_candidates,
    _selected_record_context,
    _template_context,
)
from ..services.mapping_service import (
    _owned_session,
    create_session,
    restore_proposal_revision,
    set_mapping_context,
)
from ..services.ai_orchestrator import _approved_collection_field_types
from ..services.render_bridge import render_confirmed_mapping, render_preview


_CONFIRMATIONS = frozenset(
    {
        "确认",
        "确认生成",
        "确认并生成",
        "生成正式文件",
        "确认生成正式文件",
        "确认并生成正式文件",
    }
)
_logger = logging.getLogger(__name__)


def _is_explicit_finalize_confirmation(body):
    """Accept only an exact, user-authored confirmation phrase."""
    confirmation = tools.html2plaintext(body or "").strip()
    return confirmation in _CONFIRMATIONS


def _repeat_mapping_context(env, session, specifications):
    """Turn one model-proposed repeat layout into server-authorized rows.

    The model chooses a readable one2many, sheet/start row and source-to-column
    mapping. Record count, relation model, target IDs, target manifest and
    field types are all re-derived on the server from the bound Session.
    """
    if not isinstance(specifications, list) or len(specifications) != 1:
        raise ValidationError(_("At most one repeat-row region can be rendered in this slice."))
    spec = specifications[0]
    required_spec_keys = {"collection_field", "sheet", "start_row", "columns"}
    optional_spec_keys = {"sort_by", "sort_direction"}
    if (
        not isinstance(spec, dict)
        or not required_spec_keys.issubset(spec)
        or set(spec) - required_spec_keys - optional_spec_keys
        or ("sort_by" in spec) != ("sort_direction" in spec)
    ):
        raise ValidationError(_("The repeat-row instruction has an invalid shape."))
    collection_field = spec["collection_field"]
    sheet = spec["sheet"]
    start_row = spec["start_row"]
    columns = spec["columns"]
    sort_by = spec.get("sort_by")
    sort_direction = spec.get("sort_direction")
    if (
        not isinstance(collection_field, str)
        or not collection_field.isidentifier()
        or not isinstance(sheet, str)
        or not sheet
        or len(sheet) > 255
        or type(start_row) is not int
        or not 1 <= start_row <= 1_048_576
        or not isinstance(columns, list)
        or not columns
        or len(columns) > 64
    ):
        raise ValidationError(_("The repeat-row instruction is invalid."))

    target_model = env[session.target_model]
    target_model.check_access("read")
    target = target_model.browse(session.target_record_id).exists()
    if not target:
        raise AccessError(_("The target record is unavailable."))
    target.check_access("read")
    stored_context = json.loads(session.context_json or "{}")
    selected_record_ids = stored_context.get("selected_record_ids") or [session.target_record_id]
    selected_source_records = collection_field == SELECTED_RECORDS_COLLECTION
    relation = None
    if selected_source_records:
        if selected_record_ids[0] != session.target_record_id:
            raise AccessError(_("The selected-record mapping no longer matches its Session."))
        records, candidates = _selected_record_context(
            env,
            session.target_model,
            selected_record_ids,
            requested_fields=stored_context.get("extra_authorized_fields", []),
        )
        group_relation_model = session.target_model
    else:
        relation = target_model._fields.get(collection_field)
        if not relation or relation.type != "one2many":
            raise AccessError(_("The requested collection is not related to this Session target."))
        target.check_field_access_rights("read", [collection_field])
        records = target[collection_field]
        records.check_access("read")
        candidate = next(
            (
                item
                for item in _repeat_row_collection_candidates(env, target)
                if item["collection_field"] == collection_field
            ),
            None,
        )
        candidates = candidate["allowed_fields"] if candidate else {}
        group_relation_model = relation.comodel_name
    if not records:
        raise ValidationError(_("The authorized collection has no rows to repeat."))
    if not candidates:
        raise AccessError(_("The collection has no approved repeat-row source fields."))
    if sort_by is not None and (
        not isinstance(sort_by, str)
        or sort_by not in candidates
        or sort_direction not in {"asc", "desc"}
    ):
        raise AccessError(_("The requested repeat-row sort field is not authorized."))
    clean_columns = []
    allowed_fields = {}
    seen_columns = set()
    for column in columns:
        if not isinstance(column, dict) or column.get("column") is None:
            raise ValidationError(_("A repeat-row column has an invalid shape."))
        column_id = column["column"]
        mapping_modes = [key for key in ("source_field", "fallback_fields", "formula") if key in column]
        if (
            not isinstance(column_id, str)
            or not re.fullmatch(r"[A-Z]{1,3}", column_id)
            or column_id in seen_columns
            or len(mapping_modes) != 1
            or set(column) != {"column", *(mapping_modes or [""])}
        ):
            raise ValidationError(_("Each repeat-row column must have exactly one supported mapping mode."))
        seen_columns.add(column_id)
        mode = mapping_modes[0]
        if mode == "source_field":
            source_field = column[mode]
            if not isinstance(source_field, str) or source_field not in candidates:
                raise AccessError(_("A repeat-row source field is not authorized."))
            value_type = candidates[source_field]
            clean_columns.append({"column_id": column_id, "source_field": source_field, "value_type": value_type})
            allowed_fields[source_field] = value_type
        elif mode == "fallback_fields":
            source_fields = column[mode]
            if (
                not isinstance(source_fields, list)
                or not 2 <= len(source_fields) <= 8
                or any(not isinstance(name, str) or name not in candidates for name in source_fields)
                or len(set(source_fields)) != len(source_fields)
            ):
                raise AccessError(_("A repeat-row fallback field is not authorized."))
            value_types = {candidates[name] for name in source_fields}
            if len(value_types) != 1:
                raise ValidationError(_("Fallback fields must have the same value type."))
            value_type = next(iter(value_types))
            clean_columns.append({"column_id": column_id, "source_fields": source_fields, "value_type": value_type})
            allowed_fields.update({name: candidates[name] for name in source_fields})
        else:
            formula_template = column[mode]
            if not isinstance(formula_template, str) or "{row}" not in formula_template or formula_template.count("{row}") > 16:
                raise ValidationError(_("A repeat-row formula must use the {row} placeholder."))
            # ``{row}`` is a row-number substitution inside a cell reference
            # (for example ``=E{row}*D{row}*2``), not a value by itself.
            # Reject ``{row}*{row}``, which otherwise becomes a valid but
            # semantically wrong constant formula such as ``=23*23``.
            if not re.search(r"\$?[A-Z]{1,3}\$?\{row\}", formula_template, re.IGNORECASE):
                raise ValidationError(
                    _("Use {row} inside a cell reference, for example =E{row}*D{row}*2.")
                )
            # Models commonly return the arithmetic expression without Excel's
            # leading '='. Canonicalize that notation before the strict parser;
            # the expression itself remains constrained to safe local arithmetic.
            if not formula_template.startswith("="):
                formula_template = f"={formula_template}"
            if re.search(r"\{(?!row\})[^{}]*\}", formula_template):
                raise ValidationError(_("The repeat-row formula contains an unsupported placeholder."))
            from office_mapping_verify.formula import formula_references

            for row_number in range(start_row, start_row + len(records)):
                try:
                    formula_references(formula_template.replace("{row}", str(row_number)))
                except ValueError as exc:
                    raise ValidationError(_("A repeat-row formula is not safe arithmetic.")) from exc
            clean_columns.append({"column_id": column_id, "formula_template": formula_template, "value_type": "formula"})

    if sort_by is not None:
        allowed_fields[sort_by] = candidates[sort_by]

    from office_core import expand_repeat_rows, inspect_document
    from odoo.addons.office_engine_odoo.models.office_document_request import _resource_budget

    attachment = session.source_attachment_id
    attachment.check_access("read")
    source = attachment.raw or b""
    mime = attachment.mimetype or "application/octet-stream"
    filename = attachment.name or "template.xlsx"
    expansion = expand_repeat_rows(
        source,
        {
            "action": "insert_repeat_rows",
            "sheet": sheet,
            "start_row": start_row,
            "record_count": len(records),
        "columns": {
            item["column_id"]: item.get("source_field")
            or (item.get("source_fields") or ["formula"])[0]
            for item in clean_columns
        },
        },
        _resource_budget(),
    )
    expanded = inspect_document(expansion.content, filename, mime, _resource_budget())
    manifest, template_text = _template_context(expanded)
    target_rows = []
    manifest_by_id = {item["element_id"]: item for item in manifest}
    elements_by_id = {item.element_id: item for item in expanded.elements if item.kind in {"cell", "formula"}}
    group_id = "repeat_rows"
    selected_columns = {item["column_id"] for item in clean_columns}
    first_data_row = start_row
    last_data_row = start_row + len(records) - 1
    # Repeated columns are an explicit overwrite region: templates commonly
    # contain example text in the first row. Only caller-selected, non-formula
    # cells become required mapping targets. Other blank cells in the data
    # band remain intentionally unchanged and do not block the Proposal.
    for item in manifest:
        match = re.fullmatch(r"xlsx:(.+)!([A-Z]{1,3})([1-9][0-9]*)", item["element_id"])
        if match and match.group(1) == sheet and first_data_row <= int(match.group(3)) <= last_data_row:
            if match.group(2) not in selected_columns:
                item["required"] = False
                item["approved_to_skip"] = True
    for row_index in range(len(records)):
        targets = []
        row_number = start_row + row_index
        for column in clean_columns:
            element_id = f"xlsx:{sheet}!{column['column_id']}{row_number}"
            element = elements_by_id.get(element_id)
            if not element or element.kind not in {"cell", "formula"}:
                raise ValidationError(_("A repeat-row target is not a cell in the expanded template."))
            target_spec = manifest_by_id.get(element_id)
            if target_spec is None:
                target_spec = {
                    "element_id": element_id,
                    "required": False,
                    "writable": True,
                    "allowed_value_types": ["string", "number", "formula"],
                    "approved_to_skip": True,
                }
                manifest.append(target_spec)
                manifest_by_id[element_id] = target_spec
            else:
                target_spec["required"] = False
                target_spec["approved_to_skip"] = True
            if column["value_type"] == "formula":
                # Selecting a formula for this revision must not narrow the
                # persistent target contract. A later conversational patch
                # may intentionally replace the formula with a typed literal.
                target_spec["allowed_value_types"] = list(
                    dict.fromkeys([*target_spec["allowed_value_types"], "formula"])
                )
            elif "formula" in target_spec["allowed_value_types"]:
                target_spec["allowed_value_types"] = ["string", "number"]
            targets.append({"column_id": column["column_id"], "element_id": element_id})
        target_rows.append({"row_index": row_index, "targets": targets})

    # Formula-bearing summary rows are owned by the template/M1 expansion.
    # Blank neighboring cells (for example, a unit or spacer cell beside the
    # total label) are not data requirements and must not block a valid repeat
    # mapping merely because they are geometrically close to that label.
    summary_formula_present = any(
        element.kind == "formula"
        and (match := re.fullmatch(r"xlsx:(.+)!([A-Z]{1,3})([1-9][0-9]*)", element.element_id))
        and match.group(1) == sheet
        and int(match.group(3)) == expansion.summary_row_after
        for element in expanded.elements
    )
    if summary_formula_present:
        for target_spec in manifest:
            match = re.fullmatch(
                r"xlsx:(.+)!([A-Z]{1,3})([1-9][0-9]*)", target_spec["element_id"]
            )
            if match and match.group(1) == sheet and int(match.group(3)) == expansion.summary_row_after:
                target_spec["required"] = False
                target_spec["approved_to_skip"] = True

    group = {
        "group_id": group_id,
        "collection_field": collection_field,
        "relation_model": group_relation_model,
        "row_count": len(records),
        "target_rows": target_rows,
        "allowed_fields": allowed_fields,
    }
    if selected_source_records:
        group["record_ids"] = list(selected_record_ids)
    if sort_by is not None:
        group.update({"sort_by": sort_by, "sort_direction": sort_direction})
    return {
        "manifest": manifest,
        "template_text": template_text,
        "group": group,
        "columns": clean_columns,
        "expansion": expansion,
    }


def _shift_cell_target(element_id, sheet, first_row, amount):
    match = re.fullmatch(r"xlsx:(.+)!([A-Z]{1,3})([1-9][0-9]*)", element_id or "")
    if not match or match.group(1) != sheet or int(match.group(3)) < first_row:
        return element_id
    return f"xlsx:{sheet}!{match.group(2)}{int(match.group(3)) + amount}"


def _is_repeat_band_target(element_id, sheet, first_row, last_row):
    match = re.fullmatch(r"xlsx:(.+)!([A-Z]{1,3})([1-9][0-9]*)", element_id or "")
    return bool(
        match
        and match.group(1) == sheet
        and first_row <= int(match.group(3)) <= last_row
    )


def _repeat_group_band(group):
    """Return the sheet and contiguous row bounds from a stored repeat group."""
    coordinates = [
        match
        for row in (group.get("target_rows", []) if isinstance(group, dict) else [])
        if isinstance(row, dict)
        for target in row.get("targets", [])
        if isinstance(target, dict)
        if (match := re.fullmatch(
            r"xlsx:(.+)!([A-Z]{1,3})([1-9][0-9]*)", target.get("element_id", "")
        ))
    ]
    sheets = {match.group(1) for match in coordinates}
    row_numbers = {int(match.group(3)) for match in coordinates}
    row_count = group.get("row_count") if isinstance(group, dict) else None
    if (
        len(sheets) != 1
        or type(row_count) is not int
        or len(row_numbers) != row_count
        or not row_numbers
    ):
        return None
    first_row, last_row = min(row_numbers), max(row_numbers)
    if last_row - first_row + 1 != row_count:
        return None
    return next(iter(sheets)), first_row, last_row


def _include_explicit_repeat_band_clears(rules, manifest, sheet, first_row, last_row):
    """Authorize only explicit blank writes within this Session's repeated rows."""
    manifest_ids = {item.get("element_id") for item in manifest if isinstance(item, dict)}
    added = []
    for element_id in rules.get("clear_targets", []):
        if (
            element_id in manifest_ids
            or not _is_repeat_band_target(element_id, sheet, first_row, last_row)
        ):
            continue
        manifest.append(
            {
                "element_id": element_id,
                "required": False,
                "writable": True,
                "allowed_value_types": ["string"],
                "approved_to_skip": True,
            }
        )
        manifest_ids.add(element_id)
        added.append(element_id)
    return added


def _qualify_sheet_scoped_xlsx_targets(rules, manifest):
    """Canonicalize model shorthand such as ``Sheet!M2`` to an XLSX target ID.

    The sheet must already be present in the server-derived manifest. This
    only normalizes coordinates; it does not make a target writable. A blank
    target omitted from the package is separately admitted only by the
    server-bound repeat-row clear logic below.
    """
    known_sheets = {
        match.group(1)
        for item in manifest
        if isinstance(item, dict)
        and isinstance(item.get("element_id"), str)
        and (match := re.fullmatch(r"xlsx:(.+)!([A-Z]{1,3}[1-9][0-9]*)", item["element_id"]))
    }

    def qualify(element_id):
        if not isinstance(element_id, str) or element_id.startswith("xlsx:"):
            return element_id
        match = re.fullmatch(r"(.+)!([A-Z]{1,3}[1-9][0-9]*)", element_id)
        if match and match.group(1) in known_sheets:
            return f"xlsx:{element_id}"
        return element_id

    for mapping in rules.get("mappings", []):
        if isinstance(mapping, dict) and "element_id" in mapping:
            mapping["element_id"] = qualify(mapping["element_id"])
    for clarification in rules.get("clarifications", []):
        if isinstance(clarification, dict) and "element_id" in clarification:
            clarification["element_id"] = qualify(clarification["element_id"])
    for key in ("clear_targets", "skipped_targets"):
        if key in rules:
            rules[key] = [qualify(item) for item in rules[key]]
    for patch in rules.get("format_patches", []):
        if isinstance(patch, dict) and "element_id" in patch:
            patch["element_id"] = qualify(patch["element_id"])


def _shift_formula_rows(formula, first_row, amount):
    """Shift local formula references moved by repeat-row insertion."""
    cell_ref = re.compile(r"(?<![A-Za-z0-9_!])(\$?)([A-Z]{1,3})(\$?)([1-9][0-9]*)")

    def replace(match):
        row = int(match.group(4))
        if row < first_row:
            return match.group(0)
        return f"{match.group(1)}{match.group(2)}{match.group(3)}{row + amount}"

    return cell_ref.sub(replace, formula)


def _normalize_merged_target_aliases(rules, manifest):
    """Resolve any coordinate inside a merged range to its writable anchor."""
    anchors = []
    range_aliases = []
    for target in manifest:
        merge_range = target.get("merge_range")
        write_target = target.get("write_target")
        anchor = _cell_coordinates(write_target)
        if not isinstance(merge_range, str) or not anchor:
            continue
        range_aliases.append((anchor[0], merge_range, write_target))
        first, separator, last = merge_range.partition(":")
        start = _cell_coordinates(f"xlsx:{anchor[0]}!{first}")
        end = _cell_coordinates(f"xlsx:{anchor[0]}!{last}") if separator else None
        if start and end:
            anchors.append((anchor[0], start, end, write_target))

    def resolve(element_id):
        if isinstance(element_id, str):
            qualified_range = re.fullmatch(r"xlsx:(.+)!([A-Z]{1,3}[1-9][0-9]*:[A-Z]{1,3}[1-9][0-9]*)", element_id)
            bare_range = re.fullmatch(r"[A-Z]{1,3}[1-9][0-9]*:[A-Z]{1,3}[1-9][0-9]*", element_id)
            if qualified_range or bare_range:
                requested_sheet = qualified_range.group(1) if qualified_range else None
                requested_range = qualified_range.group(2) if qualified_range else element_id
                candidates = {
                    write_target
                    for sheet, merge_range, write_target in range_aliases
                    if merge_range == requested_range
                    and (requested_sheet is None or sheet == requested_sheet)
                }
                # A bare range is accepted only if it resolves to one unique
                # writable anchor across the current template manifest.
                return next(iter(candidates)) if len(candidates) == 1 else element_id
        location = _cell_coordinates(element_id)
        if not location and isinstance(element_id, str) and re.fullmatch(
            r"[A-Z]{1,3}[1-9][0-9]*", element_id
        ):
            # Models sometimes use the bare cell coordinate from the user's
            # wording (for example ``F17``). Resolve it only when the current
            # manifest identifies exactly one merged write anchor containing
            # that coordinate. If several sheets match, the caller must use
            # the qualified target ID so the sheet choice stays unambiguous.
            candidates = set()
            for sheet in {item[0] for item in anchors}:
                bare_location = _cell_coordinates(f"xlsx:{sheet}!{element_id}")
                if not bare_location:
                    continue
                _, column, row, _coordinate = bare_location
                for anchor_sheet, start, end, write_target in anchors:
                    if (
                        sheet == anchor_sheet
                        and min(start[1], end[1]) <= column <= max(start[1], end[1])
                        and min(start[2], end[2]) <= row <= max(start[2], end[2])
                    ):
                        candidates.add(write_target)
            return next(iter(candidates)) if len(candidates) == 1 else element_id
        if location:
            sheet, column, row, _coordinate = location
            for anchor_sheet, start, end, write_target in anchors:
                if (
                    sheet == anchor_sheet
                    and min(start[1], end[1]) <= column <= max(start[1], end[1])
                    and min(start[2], end[2]) <= row <= max(start[2], end[2])
                ):
                    return write_target
        return element_id

    for mapping in rules["mappings"]:
        mapping["element_id"] = resolve(mapping["element_id"])
    for patch in rules.get("format_patches", []):
        if isinstance(patch, dict) and "element_id" in patch:
            patch["element_id"] = resolve(patch["element_id"])
    for key in ("clear_targets", "skipped_targets"):
        if key in rules:
            rules[key] = [resolve(element_id) for element_id in rules[key]]
    for clarification in rules["clarifications"]:
        clarification["element_id"] = resolve(clarification["element_id"])


def _merge_mapping_patch(current, patch):
    """Apply the targets mentioned in a new Proposal to the persisted rules.

    Mapping tool calls are conversational patches. Empty arrays do not mean
    "delete everything"; a target changes only when the new Proposal contains
    a mapping, clarification, skip, or explicit clear for that target.
    """
    current = current if isinstance(current, dict) else {}
    result = {
        "schema_version": patch["schema_version"],
        "mappings": [item for item in current.get("mappings", []) if isinstance(item, dict)],
        "clarifications": [item for item in current.get("clarifications", []) if isinstance(item, dict)],
        "skipped_targets": list(current.get("skipped_targets", [])),
    }
    if "clear_targets" in current or "clear_targets" in patch:
        result["clear_targets"] = list(current.get("clear_targets", []))
    if "clear_columns" in current or "clear_columns" in patch:
        result["clear_columns"] = list(current.get("clear_columns", []))

    if "format_patches" in current or "format_patches" in patch:
        result["format_patches"] = [
            dict(item) for item in current.get("format_patches", []) if isinstance(item, dict)
        ]
        incoming_format_columns = {
            (item.get("sheet"), item.get("column"))
            for item in patch.get("format_patches", [])
            if isinstance(item, dict) and set(item) == {"sheet", "column", "number_format"}
        }
        if incoming_format_columns:
            # A new column-level formatting instruction supersedes older
            # per-cell patches in that column. Otherwise expanding the new
            # instruction would create duplicate operations for the same
            # cells and reject a valid incremental edit.
            def is_superseded(item):
                if (item.get("sheet"), item.get("column")) in incoming_format_columns:
                    return True
                element_id = item.get("element_id", "")
                match = re.fullmatch(r"xlsx:(.+)!([A-Z]{1,3})[1-9][0-9]*", element_id)
                return bool(match and (match.group(1), match.group(2)) in incoming_format_columns)

            result["format_patches"] = [
                item for item in result["format_patches"] if not is_superseded(item)
            ]
        format_by_target = {
            item.get("element_id", f"{item.get('sheet')}!{item.get('column')}"): item
            for item in result["format_patches"]
        }
        for item in patch.get("format_patches", []):
            if not isinstance(item, dict):
                continue
            target = item.get("element_id", f"{item.get('sheet')}!{item.get('column')}")
            format_by_target[target] = dict(item)
        result["format_patches"] = list(format_by_target.values())
    if "clear_columns" in patch:
        existing_columns = {
            (item.get("sheet"), item.get("column")): item
            for item in result.get("clear_columns", [])
            if isinstance(item, dict)
        }
        for item in patch.get("clear_columns", []):
            existing_columns[(item["sheet"], item["column"])] = dict(item)
        result["clear_columns"] = list(existing_columns.values())

    patch_mappings = {}
    for item in patch["mappings"]:
        target = item["element_id"]
        if target in patch_mappings:
            raise MappingParseError("duplicate_mapping_target")
        patch_mappings[target] = item
    patch_clarifications = {}
    for item in patch["clarifications"]:
        target = item["element_id"]
        if target in patch_clarifications:
            raise MappingParseError("duplicate_clarification_target")
        patch_clarifications[target] = item
    patch_skips = set(patch["skipped_targets"])
    patch_clears = set(patch.get("clear_targets", []))

    # Mapping and clarification express incompatible outcomes and must be
    # clarified. Explicit clears are intentionally authoritative: the model
    # may echo an old mapping for a cell while also carrying the user's clear
    # instruction, and clearing must not be rejected or silently lose to it.
    if set(patch_mappings) & set(patch_clarifications):
        raise MappingParseError("conflicting_patch_target")

    touched = set(patch_mappings) | set(patch_clarifications) | patch_skips | patch_clears
    if not touched:
        return result

    result["mappings"] = [item for item in result["mappings"] if item.get("element_id") not in touched]
    result["clarifications"] = [
        item for item in result["clarifications"] if item.get("element_id") not in touched
    ]
    result["skipped_targets"] = [item for item in result["skipped_targets"] if item not in touched]
    if "clear_targets" in result:
        result["clear_targets"] = [item for item in result["clear_targets"] if item not in touched]

    # An explicit clear is authoritative. Otherwise a concrete mapping takes
    # precedence over stale skip/clarification annotations for the same cell.
    for target in sorted(touched):
        if target in patch_clears:
            result.setdefault("clear_targets", []).append(target)
        elif target in patch_mappings:
            result["mappings"].append(patch_mappings[target])
        elif target in patch_clarifications:
            result["clarifications"].append(patch_clarifications[target])
        elif target in patch_skips:
            result["skipped_targets"].append(target)

    result["skipped_targets"] = sorted(set(result["skipped_targets"]))
    if "clear_targets" in result:
        result["clear_targets"] = sorted(set(result["clear_targets"]))
    return result


def _unexpand_saved_repeat_mappings(env, session, stored, rules, *, remove_generated=True):
    """Return saved targets to the uploaded template coordinates before a new expansion.

    A Session stores its rendered Proposal in post-expansion coordinates. If a
    later turn supplies repeat_rows again, rebuild that layout from the source
    workbook rather than shifting the already-expanded Proposal a second time.
    """
    groups = stored.get("mapping_groups", [])
    if not groups:
        return rules
    if len(groups) != 1 or not isinstance(groups[0], dict):
        raise MappingParseError("unsupported_saved_repeat_groups")
    group = groups[0]
    rows = group.get("target_rows", [])
    if not rows or not rows[0].get("targets"):
        raise MappingParseError("invalid_saved_repeat_group")
    first_target = rows[0]["targets"][0]
    match = re.fullmatch(r"xlsx:(.+)!([A-Z]{1,3})([1-9][0-9]*)", first_target.get("element_id", ""))
    if not match:
        raise MappingParseError("invalid_saved_repeat_group")
    from office_core import expand_repeat_rows
    from odoo.addons.office_engine_odoo.models.office_document_request import _resource_budget

    sheet, start_row = match.group(1), int(match.group(3))
    columns = {
        target["column_id"]: "mapping"
        for target in rows[0].get("targets", [])
        if isinstance(target, dict) and isinstance(target.get("column_id"), str)
    }
    if not columns:
        raise MappingParseError("invalid_saved_repeat_group")
    expansion = expand_repeat_rows(
        session.source_attachment_id.raw or b"",
        {
            "action": "insert_repeat_rows",
            "sheet": sheet,
            "start_row": start_row,
            "record_count": group.get("row_count"),
            "columns": columns,
        },
        _resource_budget(),
    )
    generated_targets = {
        target["element_id"]
        for row in rows
        for target in row.get("targets", [])
        if isinstance(target, dict) and isinstance(target.get("element_id"), str)
    }
    rules = json.loads(json.dumps(rules, ensure_ascii=False))
    if remove_generated:
        rules["mappings"] = [
            item for item in rules.get("mappings", []) if item.get("element_id") not in generated_targets
        ]
    shift_at = expansion.summary_row_after
    if shift_at is None:
        # Append-only layouts do not move coordinates outside the repeated
        # range. Generated detail mappings stay in their original row numbers.
        return rules
    shift_by = -expansion.inserted_rows
    for item in rules["mappings"]:
        item["element_id"] = _shift_cell_target(item["element_id"], sheet, shift_at, shift_by)
        if isinstance(item.get("formula"), str):
            item["formula"] = _shift_formula_rows(item["formula"], shift_at, shift_by)
    for item in rules.get("clarifications", []):
        item["element_id"] = _shift_cell_target(item["element_id"], sheet, shift_at, shift_by)
    for key in ("skipped_targets", "clear_targets"):
        if key in rules:
            rules[key] = [
                _shift_cell_target(item, sheet, shift_at, shift_by)
                for item in rules[key]
            ]
    return rules


def _preview_delivery_metadata(env, session, attachment, message=None):
    """Describe only a preview attachment that is actually linked to chat."""
    if not attachment:
        return {"attachment_posted_to_thread": False, "attachment": False, "message_id": False}
    if not message:
        message = env["mail.message"].search(
            [
                ("model", "=", "llm.thread"),
                ("res_id", "=", session.thread_id.id),
                ("llm_role", "=", "assistant"),
                ("attachment_ids", "in", [attachment.id]),
            ],
            order="id desc",
            limit=1,
        )
    linked = bool(
        message
        and message.model == "llm.thread"
        and message.res_id == session.thread_id.id
        and attachment in message.attachment_ids
    )
    return {
        "attachment_posted_to_thread": linked,
        "attachment": (
            {
                "id": attachment.id,
                "name": attachment.name,
                "mimetype": attachment.mimetype,
                "message_id": message.id,
            }
            if linked
            else False
        ),
        "message_id": message.id if linked else False,
    }


def _repeat_formula_template(formula, element_id):
    match = re.fullmatch(r"xlsx:.+![A-Z]{1,3}([1-9][0-9]*)", element_id or "")
    if not match or not isinstance(formula, str):
        return None
    row_number = match.group(1)
    reference_row = re.compile(rf"(\$?[A-Z]{{1,3}}\$?){row_number}(?![0-9])")
    return reference_row.sub(r"\g<1>{row}", formula)


def _aggregate_summary_optional_targets(manifest, template_text):
    """Identify optional blank targets on rows owned by aggregate formulas."""
    aggregate_rows = set()
    for item in template_text or []:
        element_id = item.get("element_id") if isinstance(item, dict) else None
        text = item.get("text") if isinstance(item, dict) else None
        match = re.fullmatch(r"xlsx:(.+)!([A-Z]{1,3})([1-9][0-9]*)", element_id or "")
        if (
            match
            and isinstance(text, str)
            and re.search(r"(?i)\b(?:SUM|SUBTOTAL|AGGREGATE)\s*\(", text)
        ):
            aggregate_rows.add((match.group(1), int(match.group(3))))
    result = set()
    for target in manifest or []:
        if target.get("required") or not target.get("approved_to_skip"):
            continue
        match = re.fullmatch(r"xlsx:(.+)!([A-Z]{1,3})([1-9][0-9]*)", target.get("element_id") or "")
        if match and (match.group(1), int(match.group(3))) in aggregate_rows:
            result.add(target["element_id"])
    return result
class LLMThreadOfficeTools(models.AbstractModel):
    _name = "office.mapping.tool"
    _description = "Office Mapping Native Assistant Tools"

    def _office_tool_context(self):
        message = self.env.context.get("message")
        if not message or message.model != "llm.thread" or not message.res_id:
            raise AccessError(_("The Office chat context is unavailable."))
        thread = self.env["llm.thread"].browse(message.res_id).exists()
        if not thread:
            raise AccessError(_("The Office chat context is unavailable."))
        thread.check_access("read")
        if thread.user_id.id != self.env.uid:
            raise AccessError(_("The Office chat context is unavailable."))
        return thread, message

    def _office_source_upload(self, thread):
        upload, office = thread._office_latest_upload()
        if not upload or not office:
            return None, None, {
                "status": "needs_input",
                "error_code": "office_template_missing",
                "message": _("No supported Office template was found in this chat. Ask the user to attach one.")
            }
        if len(upload.attachment_ids) != 1:
            return None, None, {
                "status": "needs_input",
                "error_code": "multiple_office_templates",
                "message": _("More than one attachment is present on the latest upload. Ask the user which template to use.")
            }
        if (office.name or "").lower().endswith((".xlsm", ".xltm", ".docm", ".dotm", ".pptm", ".potm", ".ppsm")):
            return None, None, {
                "status": "unsupported",
                "error_code": "macro_enabled_office_file",
                "message": _("This Office file contains macros and cannot be processed by the current document reader.")
            }
        return upload, office, None

    @llm_tool(
        xml_managed=True,
        destructive_hint=True,
        description=(
            "Prepare an Office mapping context for a business record readable by the current Odoo user. "
            "Reads the current Thread's latest validated .xlsx or basic .docx upload and "
            "returns writable target IDs, template text, server-approved field names/types, and (for XLSX) readable "
            "related collections and explicitly selected record sets for repeat_rows. "
            "If the native Retriever has just read fields needed for this mapping that are not listed, pass their exact "
            "field paths in requested_fields; this is a discovery hint only and every path is reauthorized for every "
            "selected record before use. Never send attachment bytes to the model."
        ),
    )
    def office_prepare_context(
        self,
        target_model: str,
        target_record_id: int | None = None,
        target_record_ids: list[int] | None = None,
        requested_fields: list[str] | None = None,
    ) -> dict:
        """Bind an authorized record or ordered record set and the latest upload."""
        thread, _tool_message = self._office_tool_context()
        active = thread._office_active_session()
        if target_model == "unknown" and target_record_id in (None, 0) and active:
            # A follow-up turn may ask to reuse the current mapping but the
            # model may not repeat the bound record identifiers. Reuse only
            # the Session already bound to this Thread, owner, company, and
            # latest uploaded template; never infer a new business record.
            target_model = active.target_model
            target_record_id = active.target_record_id
            active_context = json.loads(active.context_json or "{}")
            target_record_ids = active_context.get("selected_record_ids") or [active.target_record_id]
        if not isinstance(target_model, str) or target_model not in self.env.registry.models:
            raise AccessError(_("The requested Odoo model is unavailable."))
        if target_record_id in (None, 0) and isinstance(target_record_ids, list) and target_record_ids:
            # The first selected ID is the deterministic Session anchor. This
            # lets native Tool Calling bind an ordered record set without
            # redundantly sending the same ID in a separate scalar argument.
            target_record_id = target_record_ids[0]
        if target_record_id in (None, 0):
            active_for_model = active.filtered(lambda item: item.target_model == target_model)[:1]
            if active_for_model:
                target_record_id = active_for_model.target_record_id
                active_context = json.loads(active_for_model.context_json or "{}")
                target_record_ids = target_record_ids or active_context.get("selected_record_ids")
        if type(target_record_id) is not int or target_record_id < 1:
            raise ValidationError(_("The requested business record ID must be an integer."))
        if target_record_ids is None:
            active_for_record = active.filtered(
                lambda item: item.target_model == target_model and item.target_record_id == target_record_id
            )[:1]
            if active_for_record:
                active_context = json.loads(active_for_record.context_json or "{}")
                target_record_ids = active_context.get("selected_record_ids") or [target_record_id]
            else:
                target_record_ids = [target_record_id]
        if (
            not isinstance(target_record_ids, list)
            or not target_record_ids
            or any(type(record_id) is not int or record_id < 1 for record_id in target_record_ids)
            or len(set(target_record_ids)) != len(target_record_ids)
        ):
            raise ValidationError(_("The selected business records are invalid."))
        # The Session anchor remains the first selected record. Keep the model's
        # supplied record order for row correspondence while normalizing it to
        # the anchor so Session ownership and retry checks stay deterministic.
        selected_record_ids = [target_record_id] + [
            record_id for record_id in target_record_ids if record_id != target_record_id
        ]
        upload, attachment, upload_result = self._office_source_upload(thread)
        if upload_result:
            return upload_result
        is_xlsx_upload = (attachment.name or "").lower().endswith(".xlsx")
        Session = self.env["office.mapping.session"]
        session = active.filtered(
            lambda item: item.source_message_id == upload
            and item.source_attachment_id == attachment
            and item.target_model == target_model
            and item.target_record_id == target_record_id
        )[:1]
        if session:
            old_context = json.loads(session.context_json or "{}")
            if (old_context.get("selected_record_ids") or [session.target_record_id]) != selected_record_ids:
                session = Session
        previous_extra_fields = []
        if session:
            previous_context = json.loads(session.context_json or "{}")
            previous_extra_fields = previous_context.get("extra_authorized_fields", [])
        requested_fields = [] if requested_fields is None else requested_fields
        if (
            not isinstance(requested_fields, list)
            or len(requested_fields) > 64
            or any(not isinstance(name, str) or not name.strip() or len(name) > 255 for name in requested_fields)
            or len(set(requested_fields)) != len(requested_fields)
        ):
            raise ValidationError(_("The explicitly requested field list is invalid."))
        reauthorized_field_paths = list(dict.fromkeys([*previous_extra_fields, *requested_fields]))
        selected_records, allowed_fields = _selected_record_context(
            self.env, target_model, selected_record_ids, requested_fields=reauthorized_field_paths
        )
        extra_authorized_fields = [
            name for name in reauthorized_field_paths if name in allowed_fields
        ]
        unavailable_requested_fields = [
            name for name in requested_fields if name not in allowed_fields
        ]
        target = selected_records[0]
        repeat_row_collections = (
            _repeat_row_collection_candidates(self.env, target) if is_xlsx_upload else []
        )
        if is_xlsx_upload and len(selected_record_ids) > 1:
            repeat_row_collections.append(
                {
                    "collection_field": SELECTED_RECORDS_COLLECTION,
                    "relation_model": target_model,
                    "inverse_field": "id",
                    "row_count": len(selected_record_ids),
                    "allowed_fields": allowed_fields,
                }
            )
        if session:
            existing = json.loads(session.context_json or "{}")
            current_hash = hashlib.sha256(attachment.raw or b"").hexdigest()
            if session.template_fingerprint != current_hash or not isinstance(
                existing.get("target_manifest"), list
            ):
                raise ValidationError(_("The template changed; start a new mapping Session."))
            manifest = existing["target_manifest"]
            visible_text = existing.get("template_text", [])
            context_refresh = existing.get("document_format") != ("xlsx" if is_xlsx_upload else "docx")
            if existing.get("manifest_metadata_version") != 2 or context_refresh:
                # Upgrade an existing Session once. Preserve its current target
                # set and repeat-row entries; attach only metadata derived from
                # the same fingerprinted template.
                inspection = self.env["office.document.request"]._inspect_chat_attachment_document(
                    attachment, thread, upload
                )
                fresh_manifest, _fresh_text = _template_context(inspection)
                fresh_by_id = {item["element_id"]: item for item in fresh_manifest}
                manifest = []
                for old_item in existing["target_manifest"]:
                    refreshed = dict(old_item)
                    fresh_item = fresh_by_id.get(old_item["element_id"], {})
                    for policy_key in (
                        "required", "writable", "allowed_value_types", "approved_to_skip"
                    ):
                        if policy_key in fresh_item:
                            refreshed[policy_key] = fresh_item[policy_key]
                    for metadata_key in (
                        "merge_range", "write_target", "visual_labels", "table_role", "table_header"
                    ):
                        refreshed.pop(metadata_key, None)
                        if metadata_key in fresh_item:
                            refreshed[metadata_key] = fresh_item[metadata_key]
                    manifest.append(refreshed)
                context_refresh = True
            if (
                existing.get("allowed_fields") != allowed_fields
                or existing.get("extra_authorized_fields", []) != extra_authorized_fields
                or context_refresh
            ):
                # A deployment may add newly authorized field paths (for
                # example, a readable full address) while a user is already
                # working in a Session. Refresh only the field dictionary.
                # The stored manifest may include server-built repeated-row
                # targets that do not exist in the raw upload; re-inspecting
                # the source here would discard those targets and invalidate
                # the Session's existing repeat group.
                set_mapping_context(
                    self.env,
                    session.id,
                    manifest,
                    allowed_fields,
                    mapping_groups=existing.get("mapping_groups", []),
                    template_text=visible_text,
                    document_format="xlsx" if is_xlsx_upload else "docx",
                    selected_record_ids=selected_record_ids,
                    extra_authorized_fields=extra_authorized_fields,
                )
                session.invalidate_recordset(["context_json", "template_fingerprint"])
        else:
            request_model = self.env["office.document.request"]
            inspection = request_model._inspect_chat_attachment_document(attachment, thread, upload)
            if inspection.format not in {"xlsx", "docx"}:
                return {
                    "status": "unsupported",
                    "error_code": "office_format_not_supported",
                    "message": _("The current document reader supports XLSX and basic DOCX. Ask the user for a supported file format."),
                    "detected_format": inspection.format,
                }
            manifest, visible_text = _template_context(inspection)
            created = create_session(
                self.env,
                thread_id=thread.id,
                source_message_id=upload.id,
                source_attachment_id=attachment.id,
                target_model=target_model,
                target_record_id=target.id,
            )
            session = Session.browse(created["session_id"])
            set_mapping_context(
                self.env,
                session.id,
                manifest,
                allowed_fields,
                template_text=visible_text,
                document_format=inspection.format,
                selected_record_ids=selected_record_ids,
                extra_authorized_fields=extra_authorized_fields,
            )
        current_rules = json.loads(session.mapping_rules_json or "{}")
        stored_groups = json.loads(session.context_json or "{}").get("mapping_groups", [])
        repeated_targets = {
            item["element_id"]
            for group in stored_groups
            for row in group.get("target_rows", [])
            for item in row.get("targets", [])
        }
        current_proposal = dict(current_rules)
        current_proposal["mappings"] = [
            item
            for item in current_rules.get("mappings", [])
            if item.get("element_id") not in repeated_targets
        ]
        current_repeat_rows = []
        mappings_by_target = {
            item.get("element_id"): item
            for item in current_rules.get("mappings", [])
            if isinstance(item, dict)
        }
        for group in stored_groups:
            rows = group.get("target_rows", [])
            if not rows:
                continue
            columns = []
            consistent = True
            for first_target in rows[0].get("targets", []):
                first_mapping = mappings_by_target.get(first_target["element_id"], {})
                prefix = group["group_id"] + "::"
                if isinstance(first_mapping.get("formula_template"), str):
                    column_spec = {
                        "column": first_target["column_id"],
                        "formula": first_mapping["formula_template"],
                    }
                elif isinstance(first_mapping.get("formula"), str):
                    formula_template = _repeat_formula_template(
                        first_mapping["formula"], first_target["element_id"]
                    )
                    row_templates = [
                        _repeat_formula_template(
                            mappings_by_target.get(target["element_id"], {}).get("formula"),
                            target["element_id"],
                        )
                        for row in rows
                        for target in row.get("targets", [])
                        if target.get("column_id") == first_target.get("column_id")
                    ]
                    if not formula_template or any(item != formula_template for item in row_templates):
                        consistent = False
                        break
                    column_spec = {"column": first_target["column_id"], "formula": formula_template}
                elif isinstance(first_mapping.get("source_field"), str) and first_mapping["source_field"].startswith(prefix):
                    namespaced = first_mapping["source_field"]
                    if any(
                        mappings_by_target.get(target["element_id"], {}).get("source_field") != namespaced
                        for row in rows
                        for target in row.get("targets", [])
                        if target.get("column_id") == first_target.get("column_id")
                    ):
                        consistent = False
                        break
                    column_spec = {
                        "column": first_target["column_id"],
                        "source_field": namespaced[len(prefix):],
                    }
                elif isinstance(first_mapping.get("source_fields"), list) and all(
                    isinstance(name, str) and name.startswith(prefix)
                    for name in first_mapping["source_fields"]
                ):
                    namespaced_fields = first_mapping["source_fields"]
                    if any(
                        mappings_by_target.get(target["element_id"], {}).get("source_fields") != namespaced_fields
                        for row in rows
                        for target in row.get("targets", [])
                        if target.get("column_id") == first_target.get("column_id")
                    ):
                        consistent = False
                        break
                    column_spec = {
                        "column": first_target["column_id"],
                        "fallback_fields": [name[len(prefix):] for name in namespaced_fields],
                    }
                else:
                    consistent = False
                    break
                columns.append(column_spec)
            if consistent and columns:
                first_id = rows[0]["targets"][0]["element_id"]
                match = re.fullmatch(r"xlsx:(.+)!([A-Z]{1,3})[1-9][0-9]*", first_id)
                if match:
                    current_group = {
                        "collection_field": group["collection_field"],
                        "sheet": match.group(1),
                        "start_row": int(re.search(r"[1-9][0-9]*$", first_id).group()),
                        "columns": columns,
                    }
                    if group.get("sort_by"):
                        current_group.update(
                            {
                                "sort_by": group["sort_by"],
                                "sort_direction": group["sort_direction"],
                            }
                        )
                    current_repeat_rows.append(current_group)
        template_formula_cells = [
            {
                "element_id": item["element_id"],
                "formula": item["text"],
                "repeat_behavior": "preserved_unless_explicitly_mapped_or_cleared",
            }
            for item in visible_text
            if isinstance(item, dict)
            and isinstance(item.get("element_id"), str)
            and isinstance(item.get("text"), str)
            and item["text"].startswith("=")
        ]
        model_fields = _field_metadata(self.env, target_model, allowed_fields)
        described_collections = [
            {
                **item,
                "allowed_fields": _field_metadata(
                    self.env, item["relation_model"], item["allowed_fields"]
                ),
            }
            for item in repeat_row_collections
        ]
        try:
            available_revisions = [
                item["proposal_revision"]
                for item in json.loads(session.proposal_history_json or "[]")
            ]
        except (TypeError, KeyError, json.JSONDecodeError):
            available_revisions = []
        document_format = json.loads(session.context_json or "{}").get("document_format") or (
            "xlsx" if is_xlsx_upload else "docx"
        )
        if document_format == "xlsx":
            mapping_limits = {
                "supported": [
                    "direct_field_mapping",
                    "repeat_rows",
                    "source_fallbacks",
                    "safe_arithmetic_formulas",
                    "blank_string_values",
                    "template_formula_row_expansion",
                    "number_format_patches",
                    "table_column_clear_and_format",
                ],
                "unsupported": ["conditions", "arbitrary_excel_functions", "cross_sheet_or_external_formulas", "docx"],
                "repeat_rows_contract": {
                    "collection_field": "必须选自 repeat_row_collections；selected_records 表示本次明确传入并绑定到 Session 的整组源记录",
                    "sheet": "模板中的工作表名",
                    "start_row": "首条明细行号",
                    "columns": "每列只能指定 source_field、fallback_fields 或安全算术 formula 其中一种；{row} 是行号，只能写在单元格引用内，例如 =E{row}*D{row}*2。",
                    "sorting": "仅在用户明确要求排序时，可同时提供 sort_by 和 sort_direction。sort_by 必须是该集合 allowed_fields 中的字段；方向为 asc 或 desc；空值始终排在末尾。不提供时保留关联集合当前顺序。",
                    "row_count": "由服务端读取关联集合，模型不得指定",
                    "existing_formula_cells": "模板公式默认保留；只有明确选择公式格作为 repeat_rows.columns 时才会覆盖，未提及的公式不变。",
                },
                "formula_contract": "只接受同表单元格引用、数字、括号和 + - * /；不支持函数、跨表、外链或任意表达式。",
                "fallback_contract": "按顺序选择第一个非空、非 False 的同类型授权字段；全部为空时字符串目标保持空白。",
                "dynamic_total_contract": "M1 可将模板中位于重复行区域下方的既有公式行随插入行下移并扩展其 SUM 范围；不会替用户创建任意业务总计公式。",
            }
        else:
            mapping_limits = {
                "supported": ["direct_field_mapping", "source_fallbacks", "blank_string_values", "docx_simple_paragraph_replacement"],
                "unsupported": ["conditions", "repeat_rows", "formulas", "arbitrary_excel_functions", "cross_sheet_or_external_formulas", "complex_docx_runs", "docx_table_row_insertion"],
                "fallback_contract": "按顺序选择第一个非空、非 False 的同类型授权字段；全部为空时段落保持空白。",
                "docx_contract": "仅支持替换具有单一文本 run 的正文段落或表格段落；不会新增段落、表格行或改写复杂富文本结构。标量值由服务端安全转换为文本。",
            }
        return {
            "status": "ready",
            "session_id": session.id,
            "revision": session.revision,
            "proposal_revision": session.proposal_revision,
            "target_model": target_model,
            "target_record_id": target.id,
            "source_records": {
                "record_ids": selected_record_ids,
                "count": len(selected_record_ids),
                "order": "the supplied ID order; repeat_rows can apply an explicit allowed-field sort",
            },
            "document_format": document_format,
            "target_manifest": manifest,
            "template_text": visible_text,
            # Dynamic Odoo field metadata helps semantic selection. The
            # persisted server context remains type-only and is reauthorized
            # before any read or render.
            "allowed_fields": model_fields,
            "unavailable_requested_fields": unavailable_requested_fields,
            "current_proposal": current_proposal,
            "current_repeat_rows": current_repeat_rows,
            "repeat_row_collections": described_collections,
            "available_proposal_revisions": available_revisions,
            "mapping_limits": {
                **mapping_limits,
                **({"template_formula_cells": template_formula_cells} if document_format == "xlsx" else {}),
            },
        }

    @llm_tool(
        xml_managed=True,
        destructive_hint=True,
        description=(
            "Apply a conversational patch to the current direct/fallback/formula/typed-literal Proposal and optional single XLSX repeat_rows layout, then validate it against the "
            "current Session, server-authorized related collection, fields, target cells and revision. "
            "The Proposal is a patch: targets omitted from mappings, clarifications, skipped_targets, and clear_targets remain unchanged. "
            "Supports independent number-format patches and detected table-column clear/format operations; these do not replace cell values. "
            "Template labels do not create mandatory business targets. Use the optional "
            "clear_targets list or a compact mapping {element_id, value: \"\"} only for cells the user explicitly asks to blank. Existing formula cells not written "
            "by the Proposal stay unchanged; an explicit mapping or clear replaces the formula at that target. "
            "A typed literal is a scalar the user supplied or requested as a deterministic calculation; never invent one. "
            "The server derives the related row count and target cells, then runs M1 expansion and read-back "
            "verification. Existing template formulas are preserved unless the Proposal explicitly replaces them. "
            "On invalid results, use the returned error details/recovery_hint to correct the proposal or ask "
            "the user; never claim a preview was generated. Formulas are restricted arithmetic only; conditions are unsupported."
        ),
    )
    def office_save_mapping_preview(
        self,
        session_id: int,
        expected_revision: int,
        proposal: dict,
        repeat_rows: list | None = None,
        clear_columns: list | None = None,
        format_patches: list | None = None,
    ) -> dict:
        """Merge a partial direct-field/repeat-row Proposal patch and render its preview."""
        thread, _tool_message = self._office_tool_context()
        session = _owned_session(self.env, session_id)
        if session.thread_id != thread or session.owner_id.id != self.env.uid:
            raise AccessError(_("The mapping Session is unavailable."))
        if type(expected_revision) is not int or expected_revision != session.revision:
            raise ValidationError(_("MAPPING_REVISION_STALE: reload the current Office mapping."))
        # These two operation arrays are exposed both at the tool-call root
        # (the native Provider schema) and inside proposal for compatibility
        # with saved clients. Merge them explicitly before parsing; otherwise
        # llm_tool's signature validation would silently discard unknown root
        # keys and could report a preview whose requested operations never ran.
        if clear_columns is not None or format_patches is not None:
            if not isinstance(proposal, dict):
                return {
                    "status": "invalid",
                    "errors": ["invalid_proposal_json"],
                    "details": "proposal must be an object when top-level operations are supplied",
                }
            proposal = dict(proposal)
            for key, operation_list in (
                ("clear_columns", clear_columns),
                ("format_patches", format_patches),
            ):
                if operation_list is None:
                    continue
                if key in proposal:
                    return {
                        "status": "invalid",
                        "errors": ["duplicate_operation_location"],
                        "details": f"{key} must be supplied either beside proposal or inside proposal, not both",
                    }
                proposal[key] = operation_list
        try:
            rules = parse_mapping_proposal(json.dumps(proposal, ensure_ascii=False))
        except (TypeError, MappingParseError) as exc:
            return {"status": "invalid", "errors": ["invalid_proposal_json"], "details": str(exc)}
        stored = json.loads(session.context_json or "{}")
        if set(stored) - {
            "target_manifest", "allowed_fields", "mapping_groups", "template_text",
            "manifest_metadata_version", "document_format", "selected_record_ids",
            "extra_authorized_fields",
        }:
            raise ValidationError(_("The mapping context is invalid."))
        document_format = stored.get("document_format", "xlsx")
        if document_format not in {"xlsx", "docx"}:
            raise ValidationError(_("The mapping context is invalid."))
        manifest = stored.get("target_manifest", [])
        template_text = stored.get("template_text", [])
        groups = stored.get("mapping_groups", [])
        _qualify_sheet_scoped_xlsx_targets(rules, manifest)
        _normalize_merged_target_aliases(rules, manifest)
        try:
            previous_rules = json.loads(session.mapping_rules_json or "{}")
            if repeat_rows is not None:
                # A subsequent repeat-row patch may focus on another part of
                # the mapping. Preserve the saved order unless the caller
                # supplies a replacement sort; omission is not an instruction
                # to discard an existing ordering rule.
                effective_repeat_rows = repeat_rows
                if (
                    isinstance(repeat_rows, list)
                    and len(repeat_rows) == 1
                    and isinstance(repeat_rows[0], dict)
                ):
                    proposed_group = repeat_rows[0]
                    previous_group = next(
                        (
                            item for item in groups
                            if isinstance(item, dict)
                            and item.get("collection_field") == proposed_group.get("collection_field")
                        ),
                        None,
                    )
                    if (
                        previous_group
                        and previous_group.get("sort_by")
                        and "sort_by" not in proposed_group
                        and "sort_direction" not in proposed_group
                    ):
                        effective_repeat_rows = [
                            {
                                **proposed_group,
                                "sort_by": previous_group["sort_by"],
                                "sort_direction": previous_group["sort_direction"],
                            }
                        ]
                previous_rules = _unexpand_saved_repeat_mappings(
                    self.env, session, stored, previous_rules
                )
                rules = _unexpand_saved_repeat_mappings(
                    self.env, session, stored, rules, remove_generated=False
                )
            rules = _merge_mapping_patch(previous_rules, rules)
        except (TypeError, json.JSONDecodeError, MappingParseError, OfficeCoreError) as exc:
            return {"status": "invalid", "errors": ["invalid_mapping_patch"], "details": str(exc)}
        repeat_context = None
        if repeat_rows is not None:
            if document_format != "xlsx":
                return {
                    "status": "unsupported",
                    "errors": ["repeat_rows_requires_xlsx"],
                    "details": "The current M1 repeated-row adapter operates on XLSX worksheets.",
                }
            try:
                repeat_context = _repeat_mapping_context(self.env, session, effective_repeat_rows)
            except (AccessError, UserError, ValidationError, OfficeCoreError) as exc:
                return {
                    "status": "unsupported" if isinstance(exc, OfficeCoreError) else "invalid",
                    "errors": ["repeat_rows_not_authorized_or_not_renderable"],
                    "details": str(exc),
                }
            manifest = repeat_context["manifest"]
            template_text = repeat_context["template_text"]
            groups = [repeat_context["group"]]
            expansion = repeat_context["expansion"]
            shift_row = expansion.summary_row_before or 1
            shift_by = (
                expansion.inserted_rows
                if expansion.summary_row_before is not None
                else 0
            )
            repeated_ids = {
                target["element_id"]
                for row in repeat_context["group"]["target_rows"]
                for target in row["targets"]
            }
            repeat_start_row = repeat_rows[0]["start_row"]
            repeat_end_row = repeat_start_row + repeat_context["group"]["row_count"] - 1
            repeat_sheet = repeat_context["expansion"].sheet
            repeat_band_ids = {
                item["element_id"]
                for item in manifest
                if isinstance(item, dict)
                and _is_repeat_band_target(
                    item.get("element_id"),
                    repeat_sheet,
                    repeat_start_row,
                    repeat_end_row,
                )
            }
            direct_mappings = []
            for item in rules["mappings"]:
                shifted = dict(item)
                shifted["element_id"] = _shift_cell_target(
                    shifted["element_id"], repeat_context["expansion"].sheet, shift_row, shift_by
                )
                source_names = [shifted.get("source_field", "")] + shifted.get("source_fields", [])
                if shifted["element_id"] in repeated_ids or any("::" in name for name in source_names):
                    return {
                        "status": "invalid",
                        "errors": ["repeat_row_cells_must_be_declared_only_in_repeat_rows"],
                    }
                if isinstance(shifted.get("formula"), str):
                    shifted["formula"] = _shift_formula_rows(shifted["formula"], shift_row, shift_by)
                direct_mappings.append(shifted)
            rules["mappings"] = direct_mappings
            rules["clarifications"] = [
                {
                    **item,
                    "element_id": _shift_cell_target(
                        item["element_id"], repeat_context["expansion"].sheet, shift_row, shift_by
                    ),
                }
                for item in rules["clarifications"]
            ]
            mapped_ids = {item["element_id"] for item in direct_mappings} | repeated_ids
            # A selected repeat column is the authoritative mapping for its
            # cells. Drop stale cell-level clarification/skip entries that the
            # model may have emitted while it was still reasoning from the
            # unexpanded template. A direct mapping likewise resolves an older
            # clarification for that exact target.
            rules["clarifications"] = [
                item for item in rules["clarifications"] if item["element_id"] not in mapped_ids
            ]
            rules["skipped_targets"] = [
                _shift_cell_target(item, repeat_context["expansion"].sheet, shift_row, shift_by)
                for item in rules["skipped_targets"]
                if item not in repeated_ids
            ]
            if "clear_targets" in rules:
                rules["clear_targets"] = [
                    item if _is_repeat_band_target(
                        item, repeat_sheet, repeat_start_row, repeat_end_row
                    ) else _shift_cell_target(item, repeat_sheet, shift_row, shift_by)
                    for item in rules["clear_targets"]
                ]
                # A user may explicitly clear a cell in the repeated data
                # band even when the XLSX package omits that empty cell. Such
                # a target is derived from the server-bound row range and the
                # user's exact clear instruction; no other coordinates are
                # added to the writable manifest.
                _include_explicit_repeat_band_clears(
                    rules,
                    manifest,
                    repeat_sheet,
                    repeat_start_row,
                    repeat_end_row,
                )
            if "format_patches" in rules:
                rules["format_patches"] = [
                    {
                        **patch,
                        "element_id": patch["element_id"]
                        if patch["element_id"] in repeat_band_ids
                        else _shift_cell_target(
                            patch["element_id"],
                            repeat_context["expansion"].sheet,
                            shift_row,
                            shift_by,
                        ),
                    }
                    if isinstance(patch, dict) and "element_id" in patch
                    else patch
                    for patch in rules["format_patches"]
                ]
            repeated_mappings = []
            group_id = repeat_context["group"]["group_id"]
            for row in repeat_context["group"]["target_rows"]:
                for target_spec in row["targets"]:
                    column = next(
                        item
                        for item in repeat_context["columns"]
                        if item["column_id"] == target_spec["column_id"]
                    )
                    mapping = {
                        "element_id": target_spec["element_id"],
                        "value_type": column["value_type"],
                    }
                    if "formula_template" in column:
                        row_number = re.search(r"[1-9][0-9]*$", target_spec["element_id"]).group()
                        mapping["formula"] = column["formula_template"].replace("{row}", row_number)
                    elif "source_fields" in column:
                        mapping["source_fields"] = [
                            f"{group_id}::{name}" for name in column["source_fields"]
                        ]
                    else:
                        mapping["source_field"] = f"{group_id}::{column['source_field']}"
                    repeated_mappings.append(mapping)
            if len(rules["mappings"]) + len(repeated_mappings) > ParseLimits().max_mappings:
                return {"status": "invalid", "errors": ["too_many_repeat_row_mappings"]}
            rules["mappings"].extend(repeated_mappings)
        elif document_format == "xlsx" and groups and "clear_targets" in rules:
            # A later conversational patch may omit repeat_rows entirely.
            # Reuse the server-persisted group layout so an explicit blank
            # write still applies to the current effective repeated rows.
            stored_repeat_group = next(
                (
                    item for item in groups
                    if isinstance(item, dict) and item.get("target_rows") and item.get("row_count")
                ),
                None,
            )
            repeat_band = _repeat_group_band(stored_repeat_group)
            if repeat_band:
                _include_explicit_repeat_band_clears(
                    rules, manifest, *repeat_band
                )

        if not isinstance(manifest, list) or not isinstance(groups, list):
            raise ValidationError(_("The mapping context is invalid."))
        rules, column_operation_errors = expand_table_column_operations(rules, manifest)
        if column_operation_errors:
            return {
                "status": "invalid",
                "errors": column_operation_errors,
                "message": "A column operation did not resolve to a detected table data range.",
            }
        # Older persisted manifests inferred mandatory fields from nearby
        # template labels. That metadata is not a business rule: if such a
        # writable target has no assignment, make the legacy expectation an
        # explicit blank write and remove conflicting no-op/clarification
        # entries. New manifests mark all targets optional.
        mapped_target_ids = {
            item.get("element_id") for item in rules["mappings"] if isinstance(item, dict)
        }
        legacy_required_blanks = {
            item["element_id"]
            for item in manifest
            if isinstance(item, dict)
            and item.get("required") is True
            and item.get("writable") is True
            and item.get("element_id") not in mapped_target_ids
        }
        if legacy_required_blanks:
            rules["clear_targets"] = sorted(
                set(rules.get("clear_targets", [])) | legacy_required_blanks
            )
            rules["skipped_targets"] = [
                item for item in rules["skipped_targets"] if item not in legacy_required_blanks
            ]
            rules["clarifications"] = [
                item for item in rules["clarifications"]
                if item.get("element_id") not in legacy_required_blanks
            ]
        # A previous model proposal can carry a clarification for a blank
        # spacer on the original total row. Once the server expands the detail
        # region, that stale clarification moves with the row even though the
        # corresponding summary-row target is optional and the formula owns
        # the row. Resolve only those server-identified optional aggregate
        # targets as intentional skips; preserve all other clarifications.
        aggregate_optional_targets = _aggregate_summary_optional_targets(manifest, template_text)
        stale_summary_clarifications = {
            item["element_id"]
            for item in rules["clarifications"]
            if item["element_id"] in aggregate_optional_targets
        }
        if stale_summary_clarifications:
            rules["clarifications"] = [
                item for item in rules["clarifications"]
                if item["element_id"] not in stale_summary_clarifications
            ]
            rules["skipped_targets"] = sorted(
                set(rules["skipped_targets"]) | stale_summary_clarifications
            )
        # A skip on an existing formula is a no-op. Leave it out of the saved
        # skip list; the formula remains untouched unless a write/clear targets it.
        formula_target_ids = {
            item.get("element_id")
            for item in template_text
            if isinstance(item, dict)
            and isinstance(item.get("element_id"), str)
            and isinstance(item.get("text"), str)
            and item["text"].startswith("=")
        }
        if formula_target_ids:
            rules["skipped_targets"] = [
                item for item in rules["skipped_targets"] if item not in formula_target_ids
            ]
        manifest_target_ids = {
            item.get("element_id") for item in manifest if isinstance(item, dict)
        }
        # Skips are declarations of no-op behavior; omitted targets already
        # remain untouched. A model may carry coordinates from the pre-expansion
        # sheet, so discard stale/unknown skips rather than failing an otherwise
        # valid mapping. Actual mappings and explicit clears remain strict.
        rules["skipped_targets"] = [
            item for item in rules["skipped_targets"] if item in manifest_target_ids
        ]
        # An explicit user-requested clear is authoritative for that exact
        # target. Models often preserve the previous mapping while adding a
        # clear instruction; remove that stale mapping/skip/clarification
        # before validation so a clear can replace an existing assignment.
        # An explicit clear overrides any old mapping for its target, including
        # a formula cell. The M1 plan will write a blank value at that cell.
        clear_target_ids = set(rules.get("clear_targets", []))
        if clear_target_ids:
            rules["mappings"] = [
                item for item in rules["mappings"]
                if item.get("element_id") not in clear_target_ids
            ]
            rules["clarifications"] = [
                item for item in rules["clarifications"]
                if item.get("element_id") not in clear_target_ids
            ]
            rules["skipped_targets"] = [
                item for item in rules["skipped_targets"]
                if item not in clear_target_ids
            ]
        group_field_types = {}
        try:
            for group in groups:
                permitted = _approved_collection_field_types(self.env, session, group)
                group_field_types[group["group_id"]] = permitted
        except (AccessError, UserError, ValidationError) as exc:
            return {"status": "invalid", "errors": ["repeat_rows_not_authorized"], "details": str(exc)}
        # ``allowed_fields`` in the persisted context is a discovery aid for
        # the model, not an authorization boundary. Add any directly mapped
        # scalar path after rechecking its live Odoo fields and ACLs against
        # the Session's bound record. The same path is then persisted so the
        # renderer can repeat the authorization check when it reads values.
        stored_allowed_fields = dict(stored.get("allowed_fields", {}))
        target = self.env[session.target_model].browse(session.target_record_id).exists()
        if not target:
            raise AccessError(_("The target record is unavailable."))
        target.check_access("read")
        from ..services.ai_orchestrator import _authorized_scalar_field_type

        direct_source_fields = {
            source
            for mapping in rules["mappings"]
            if isinstance(mapping, dict)
            for source in [mapping.get("source_field"), *(mapping.get("source_fields") or [])]
            if isinstance(source, str) and "::" not in source
        }
        for source_field in sorted(direct_source_fields):
            value_type = _authorized_scalar_field_type(target, source_field)
            if value_type:
                stored_allowed_fields[source_field] = value_type

        mapping_fields = dict(stored_allowed_fields)
        for group_id, fields in group_field_types.items():
            mapping_fields.update({f"{group_id}::{name}": kind for name, kind in fields.items()})
        if document_format == "docx":
            # Office Core writes DOCX paragraphs as text. The server still
            # reauthorizes each path using its real Odoo type at render time.
            mapping_fields = {name: "string" for name in mapping_fields}
        report = validate_proposal(
            rules,
            manifest,
            mapping_fields,
        )
        if report.status == "invalid":
            return {"status": "invalid", "errors": report.to_dict()}
        if not report.ready_for_review:
            return {"status": "incomplete", "errors": report.to_dict()}

        canonical = json.dumps(rules, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        current = json.dumps(
            json.loads(session.mapping_rules_json or "{}"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        current_groups = json.dumps(stored.get("mapping_groups", []), sort_keys=True, separators=(",", ":"))
        proposed_groups = json.dumps(groups, sort_keys=True, separators=(",", ":"))
        context_changed = (
            current_groups != proposed_groups
            or stored.get("target_manifest") != manifest
            or stored.get("allowed_fields") != stored_allowed_fields
        )
        if canonical == current and not context_changed and session.preview_attachment_id:
            session.preview_attachment_id.check_access("read")
            preview = session.preview_attachment_id
            delivery = _preview_delivery_metadata(self.env, session, preview)
            return {
                "status": "unchanged",
                "session_id": session.id,
                "revision": session.revision,
                "proposal_revision": session.proposal_revision,
                "preview_attachment_id": preview.id,
                "filename": preview.name,
                **delivery,
            }

        preview_message = False
        with self.env.cr.savepoint():
            if context_changed:
                set_mapping_context(
                    self.env,
                    session.id,
                    manifest,
                    stored_allowed_fields,
                    mapping_groups=groups,
                    template_text=template_text,
                    document_format=document_format,
                    selected_record_ids=stored.get("selected_record_ids") or [session.target_record_id],
                    extra_authorized_fields=stored.get("extra_authorized_fields", []),
                )
                session.invalidate_recordset(["context_json", "template_fingerprint"])
            if canonical != current:
                session._save_mapping_from_service(canonical, expected_revision, "revision_pending")
                session.invalidate_recordset(["revision", "state", "mapping_rules_json", "proposal_revision"])
            elif session.state == "analyzing":
                # The first Proposal may be structurally unchanged while the
                # model adds the server-derived repeat-row context. Move the
                # Session into its renderable state without inventing a new
                # Proposal revision.
                session._transition_from_service("revision_pending", expected_revision)
                session.invalidate_recordset(["revision", "state"])
            preview = render_preview(self.env, session.id, session.revision)
            session.invalidate_recordset(["revision", "state", "preview_attachment_id"])
            from ..services.render_bridge import _post_preview_message

            preview_message = _post_preview_message(session, _("已生成并通过回读验证的 Office 预览。"))
            session.invalidate_recordset(["preview_attachment_id"])
            posted_preview = session.preview_attachment_id
        delivery = _preview_delivery_metadata(self.env, session, posted_preview, preview_message)
        return {
            "status": "preview_ready",
            "session_id": session.id,
            "revision": preview["revision"],
            "proposal_revision": preview["proposal_revision"],
            "preview_attachment_id": preview["preview_attachment_id"],
            "filename": posted_preview.name,
            **delivery,
        }

    @llm_tool(
        xml_managed=True,
        destructive_hint=True,
        description=(
            "Restore one prior Proposal revision listed by office_prepare_context, revalidate it against the current "
            "template and authorized Odoo fields, and create a new revision-bound preview. The historical revision "
            "number is never reused; a successful restore becomes a new Proposal revision."
        ),
    )
    def office_restore_proposal_revision(
        self, session_id: int, expected_revision: int, proposal_revision: int
    ) -> dict:
        """Restore a saved Proposal under a new revision and verify a new preview."""
        thread, _tool_message = self._office_tool_context()
        session = _owned_session(self.env, session_id)
        if session.thread_id != thread or session.owner_id.id != self.env.uid:
            raise AccessError(_("The mapping Session is unavailable."))
        with self.env.cr.savepoint():
            restored = restore_proposal_revision(
                self.env, session.id, expected_revision, proposal_revision
            )
            session.invalidate_recordset(
                ["mapping_rules_json", "proposal_history_json", "proposal_revision", "revision", "state"]
            )
            if restored["status"] == "unchanged":
                preview = session.preview_attachment_id
                if preview and session.preview_proposal_revision == session.proposal_revision:
                    delivery = _preview_delivery_metadata(self.env, session, preview)
                    return {
                        **restored,
                        "preview_attachment_id": preview.id,
                        "filename": preview.name,
                        **delivery,
                    }
                preview = False
            else:
                preview = False
            if restored["status"] == "unchanged" and not preview:
                preview = render_preview(self.env, session.id, session.revision)
                session.invalidate_recordset(["revision", "state", "preview_attachment_id"])
                from ..services.render_bridge import _post_preview_message

                preview_message = _post_preview_message(session, _("已生成当前映射版本的预览，请检查附件。"))
                session.invalidate_recordset(["preview_attachment_id"])
                posted_preview = session.preview_attachment_id
                delivery = _preview_delivery_metadata(self.env, session, posted_preview, preview_message)
                return {
                    **restored,
                    "status": "preview_ready",
                    "revision": preview["revision"],
                    "proposal_revision": preview["proposal_revision"],
                    "preview_attachment_id": preview["preview_attachment_id"],
                    "filename": posted_preview.name,
                    **delivery,
                }
            preview = render_preview(self.env, session.id, session.revision)
            session.invalidate_recordset(["revision", "state", "preview_attachment_id"])
            from ..services.render_bridge import _post_preview_message

            preview_message = _post_preview_message(session, _("已恢复历史映射版本并生成新预览，请检查附件。"))
            session.invalidate_recordset(["preview_attachment_id"])
            posted_preview = session.preview_attachment_id
        delivery = _preview_delivery_metadata(self.env, session, posted_preview, preview_message)
        return {
            "status": "preview_ready",
            "session_id": session.id,
            "revision": preview["revision"],
            "proposal_revision": preview["proposal_revision"],
            "restored_from_proposal_revision": proposal_revision,
            "preview_attachment_id": preview["preview_attachment_id"],
            "filename": posted_preview.name,
            **delivery,
        }

    @llm_tool(
        xml_managed=True,
        destructive_hint=True,
        description=(
            "Create the final archived Office file for the current validated Proposal. This tool is only "
            "authorized when the latest user message in this Thread is exactly '确认并生成正式文件' "
            "(or another explicitly supported exact confirmation phrase) and both Session revision "
            "and Proposal revision match."
        ),
    )
    def office_finalize(
        self, session_id: int, expected_revision: int, proposal_revision: int
    ) -> dict:
        """Return a structured result for every expected finalization outcome."""
        try:
            return self._office_finalize(session_id, expected_revision, proposal_revision)
        except AccessError as exc:
            return {
                "status": "failed",
                "error_code": "finalize_not_authorized",
                "message": str(exc),
            }
        except UserError as exc:
            return {
                "status": "failed",
                "error_code": (
                    "mapping_revision_stale"
                    if "MAPPING_REVISION_STALE" in str(exc)
                    else "finalize_validation_failed"
                ),
                "message": str(exc),
            }
        except Exception:
            _logger.exception("Unexpected Office finalization failure for Session %s", session_id)
            return {
                "status": "failed",
                "error_code": "finalize_internal_error",
                "message": _("The final document could not be generated. The current verified preview remains available; please retry or ask for help."),
            }

    def _office_finalize(self, session_id, expected_revision, proposal_revision):
        """Finalize only after an exact user confirmation for the current Proposal revision."""
        thread, _tool_message = self._office_tool_context()
        session = _owned_session(self.env, session_id)
        if session.thread_id != thread or session.owner_id.id != self.env.uid:
            raise AccessError(_("The mapping Session is unavailable."))
        if type(proposal_revision) is not int or proposal_revision != session.proposal_revision:
            raise ValidationError(_("MAPPING_REVISION_STALE: reload the current mapping and retry."))

        already_finalized = (
            session.state == "completed"
            and session.confirmed_revision == proposal_revision
            and session.preview_proposal_revision == proposal_revision
        )
        if not already_finalized:
            if (
                type(expected_revision) is not int
                or expected_revision != session.revision
                or session.preview_proposal_revision != proposal_revision
            ):
                raise ValidationError(_("MAPPING_REVISION_STALE: generate a current preview and confirm again."))
            latest_user = self.env["mail.message"].search(
                [
                    ("model", "=", "llm.thread"),
                    ("res_id", "=", thread.id),
                    ("llm_role", "=", "user"),
                    ("author_id", "=", self.env.user.partner_id.id),
                    ("is_error", "=", False),
                ],
                order="id desc",
                limit=1,
            )
            if latest_user not in thread.message_ids or not _is_explicit_finalize_confirmation(latest_user.body):
                raise AccessError(_("Send an explicit confirmation message before final file generation."))

        result = render_confirmed_mapping(self.env, session.id, expected_revision)
        if result.get("requires_reconfirmation"):
            return {"status": "requires_reconfirmation", **result}
        if result.get("state") != "completed" or not result.get("output_attachment_id"):
            session.invalidate_recordset(["revision", "state"])
            return {
                "status": "failed",
                "state": session.state,
                "revision": session.revision,
                "error_code": result.get("error_code") or "office_render_failed",
                "failed_stage": result.get("failed_stage") or False,
                "artifact_state": result.get("artifact_state") or "not_generated",
                "delivery_state": result.get("delivery_state") or "not_published",
                "message": result.get("message") or _("The final document was not generated. The verified preview remains available."),
            }
        # The M1 service persists the private output and attaches it to this
        # validated thread in its own committed cursor. The current chat RPC
        # transaction cannot safely re-read that row under its older snapshot.
        filename = result.get("filename")
        mimetype = result.get("mimetype")
        delivery_message_id = result.get("delivery_message_id")
        output_attachment_id = result.get("output_attachment_id")
        if not output_attachment_id or not filename or not mimetype or not delivery_message_id:
            return {
                "status": "failed",
                "state": session.state,
                "revision": session.revision,
                "error_code": "final_output_metadata_unavailable",
                "message": _("The document renderer completed without all required delivery metadata."),
            }
        session.invalidate_recordset(["revision", "state", "confirmed_revision"])
        return {
            "status": "finalized",
            "session_id": session.id,
            "proposal_revision": session.confirmed_revision,
            "revision": session.revision,
            "attachment_id": output_attachment_id,
            "delivery_message_id": delivery_message_id,
            "filename": filename,
            "mimetype": mimetype,
            "attachment": {
                "id": output_attachment_id,
                "message_id": delivery_message_id,
                "name": filename,
                "mimetype": mimetype,
            },
            "attachment_posted_to_thread": True,
        }


class LLMTool(models.Model):
    _inherit = "llm.tool"

    def get_input_schema(self):
        """Expose additive batch and paging arguments on stored legacy schemas."""
        schema = super().get_input_schema()
        if not isinstance(schema, dict) or not isinstance(schema.get("properties"), dict):
            return schema
        schema = json.loads(json.dumps(schema))
        properties = schema["properties"]
        if self.name == "odoo_record_retriever":
            properties.update(
                {
                    "offset": {"type": "integer", "minimum": 0, "description": "Zero-based result offset."},
                    "order": {"type": "string", "description": "Optional Odoo ORM order expression; a stable ID tie-breaker is added."},
                    "include_pagination": {"type": "boolean", "description": "Return records with count, offset, limit, and has_more metadata."},
                }
            )
        elif self.name == "office_prepare_context":
            # Stored XML-managed schemas may predate the optional argument in
            # the Python signature, so normalize requiredness at the exposed
            # schema boundary as well as in the execution signature.
            required = schema.get("required")
            if isinstance(required, list):
                schema["required"] = [name for name in required if name != "target_record_id"]
            properties["target_record_ids"] = {
                "type": "array",
                "items": {"type": "integer", "minimum": 1},
                "minItems": 1,
                "maxItems": 100,
                "description": "Ordered, explicitly selected record IDs for mapping a record set into repeated rows; all are reauthorized by the current user.",
            }
        return schema
