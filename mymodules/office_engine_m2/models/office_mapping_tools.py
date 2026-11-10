"""Office capabilities exposed through the native llm.tool execution loop."""

import hashlib
import json
import logging
import re
from datetime import date, datetime

from odoo import _, models, tools
from odoo.addons.llm_tool.decorators import llm_tool
from odoo.exceptions import AccessError, UserError, ValidationError
from office_mapping_verify import (
    MappingParseError,
    ParseLimits,
    expand_table_column_operations,
    parse_mapping_proposal,
    validate_proposal,
    validate_transform,
)
from office_core import OfficeCoreError

from ..services.chat_entrypoint import (
    SELECTED_RECORDS_COLLECTION,
    _cell_coordinates,
    _field_metadata,
    _field_candidates,
    _normalize_requested_collection_fields,
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
from ..services.ai_orchestrator import (
    _approved_collection_field_types,
    _bind_repeat_row_coordinate_cell_edits,
    _resolve_record_target_cell_edits,
    _scalar_field_path_status,
)
from ..services.edit_orchestrator import dispatch_office_action
from ..services.finalize_confirmation import (
    build_finalize_confirmation_proof,
    is_explicit_finalize_confirmation,
    validate_finalize_confirmation_proof,
)
from ..services.render_bridge import (
    finalize_confirmed_mapping_in_isolated_transaction,
    render_confirmed_mapping,
    render_preview,
)


_logger = logging.getLogger(__name__)
_CONFIRMATION_AUTHORIZED = object()


def _normalize_office_mapping_result(result):
    """Expose one execution status while preserving the specific preview outcome."""
    if not isinstance(result, dict):
        return {
            "status": "error",
            "error_code": "invalid_tool_result",
            "operation_executed": False,
            "message": _("The Office tool returned an invalid result."),
        }
    result = dict(result)
    status = result.get("status")
    if status in {"preview_ready", "unchanged"}:
        result["operation_status"] = status
        result["status"] = "success"
        result["operation_executed"] = status == "preview_ready"
        return result
    if status in {"needs_confirmation", "blocked", "error"}:
        result.setdefault("operation_executed", False)
        return result
    if status == "invalid":
        result["operation_status"] = status
        errors = result.get("errors")
        unknown_targets = errors.get("unknown_targets", []) if isinstance(errors, dict) else []
        type_errors = errors.get("type_errors", []) if isinstance(errors, dict) else []
        error_codes = errors if isinstance(errors, list) else []
        if unknown_targets:
            result.update(status="blocked", error_code="target_outside_authorized_manifest")
        elif any("cell_edit_target_not_writable" in str(item) for item in type_errors):
            result.update(status="blocked", error_code="target_not_authorized_for_cell_edit")
        else:
            result.update(status="error", error_code=result.get("error_code", "invalid_mapping_operation"))
        result["operation_executed"] = False
        return result
    if status in {"unsupported", "incomplete"}:
        result["operation_status"] = status
        result["status"] = "error"
        result.setdefault("error_code", status)
        result["operation_executed"] = False
        return result
    result.update(
        status="error",
        error_code=result.get("error_code", "office_operation_failed"),
        operation_executed=False,
    )
    return result


def _is_explicit_finalize_confirmation(body):
    """Accept only an exact, user-authored confirmation phrase."""
    return is_explicit_finalize_confirmation(body)


def _is_exact_cell_override_confirmation(body):
    """Cell overwrite approval is deliberately a single exact user reply."""
    return tools.html2plaintext(body or "").strip() == "确认"


def _latest_office_user_message(env, thread):
    message = env["mail.message"].search(
        [
            ("model", "=", "llm.thread"),
            ("res_id", "=", thread.id),
            ("llm_role", "=", "user"),
            ("author_id", "=", env.user.partner_id.id),
            ("is_error", "=", False),
        ],
        order="id desc",
        limit=1,
    )
    if not message or message not in thread.message_ids:
        raise AccessError(_("The confirming user message is unavailable."))
    return message


def _cell_edit_signature(edits):
    return json.dumps(
        sorted(
            (dict(item) for item in edits),
            key=lambda item: (
                item.get("element_id", ""),
                json.dumps(item.get("record_target"), sort_keys=True, separators=(",", ":")),
            ),
        ),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _cell_value_label(value):
    if isinstance(value, dict) and isinstance(value.get("formula"), str):
        return "公式 " + value["formula"]
    if value is None or value == "":
        return "空白"
    return str(value)


def _confirmation_json_value(value):
    """Make inspected cell values stable and JSON-safe for a pending decision."""
    if isinstance(value, datetime):
        return {"type": "datetime", "value": value.isoformat()}
    if isinstance(value, date):
        return {"type": "date", "value": value.isoformat()}
    if isinstance(value, dict):
        return {str(key): _confirmation_json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_confirmation_json_value(item) for item in value]
    return value


def _confirmation_json_values(values):
    return {target: _confirmation_json_value(value) for target, value in values.items()}


def _is_exact_cell_override_rejection(body):
    """Recognize only explicit replies while a matching confirmation is pending."""
    text = tools.html2plaintext(body or "").strip().casefold()
    return text in {"拒绝", "取消", "不同意", "不确认", "不覆盖", "不要覆盖", "拒绝覆盖", "cancel", "no", "reject"}


def _inspect_cell_edits(env, session, edits, manifest, inspect_for_risk=False):
    """Read explicit edit targets from the current effective preview/template."""
    if not edits and not inspect_for_risk:
        return {}, b"", False
    from office_core import inspect_document
    from odoo.addons.office_engine_odoo.models.office_document_request import _resource_budget

    attachment = session.source_attachment_id
    if (
        session.preview_attachment_id
        and session.preview_proposal_revision == session.proposal_revision
    ):
        attachment = session.preview_attachment_id
    attachment.check_access("read")
    content = attachment.raw or b""
    inspected = inspect_document(
        content,
        attachment.name or "document.xlsx",
        attachment.mimetype or "application/octet-stream",
        _resource_budget(),
    )
    if inspected.format != "xlsx":
        return {}, content, False
    known_targets = {
        item.get("element_id")
        for item in manifest
        if isinstance(item, dict) and isinstance(item.get("element_id"), str)
    }
    requested_targets = {edit.get("element_id") for edit in edits if isinstance(edit, dict)}
    values = {
        element.element_id: element.value
        for element in inspected.elements
        if element.kind in {"cell", "formula"}
        and element.element_id in known_targets
        and element.element_id in requested_targets
    }
    return values, content, True


def _cell_override_pending_payload(
    env, thread, session, request_message, edits, observed_values, content, operation_scope, risks
):
    context_json = session.context_json or "{}"
    source_bytes = session.source_attachment_id.raw or b""
    return {
        "thread_id": thread.id,
        "user_id": env.uid,
        "request_message_id": request_message.id,
        "revision": session.revision,
        "proposal_revision": session.proposal_revision,
        "preview_attachment_id": session.preview_attachment_id.id or False,
        "template_fingerprint": session.template_fingerprint
        or hashlib.sha256(source_bytes).hexdigest(),
        "context_fingerprint": hashlib.sha256(context_json.encode("utf-8")).hexdigest(),
        "document_fingerprint": hashlib.sha256(content).hexdigest(),
        "cell_edits": sorted((dict(item) for item in edits), key=lambda item: item["element_id"]),
        "observed_values": _confirmation_json_values(observed_values),
        "operation_scope": operation_scope,
        "risks": risks,
    }


def _cell_override_operation_scope(
    env, thread, session, edits, content, operation_payload, derived_scope=None
):
    operation_payload_json = json.dumps(
        operation_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    mapping_targets = sorted(
        item.get("element_id")
        for item in operation_payload.get("proposal", {}).get("mappings", [])
        if isinstance(item, dict) and isinstance(item.get("element_id"), str)
    )
    return {
        "action": "office_mapping_update",
        "thread_id": thread.id,
        "session_id": session.id,
        "revision": session.revision,
        "proposal_revision": session.proposal_revision,
        "document_fingerprint": hashlib.sha256(content).hexdigest(),
        "operation_fingerprint": hashlib.sha256(operation_payload_json.encode("utf-8")).hexdigest(),
        "mapping_targets": mapping_targets,
        "repeat_row_regions": [
            {
                "sheet": item.get("sheet"),
                "start_row": item.get("start_row"),
                "collection_field": item.get("collection_field"),
                "columns": item.get("columns"),
            }
            for item in operation_payload.get("repeat_rows", [])
            if isinstance(item, dict)
        ],
        "format_targets": [
            item.get("element_id")
            for item in operation_payload.get("format_patches", [])
            if isinstance(item, dict)
        ],
        "operations": [
            {
                "action": item.get("operation", "set_value"),
                "target": item.get("element_id"),
                "value": _confirmation_json_value(item.get("value")),
                "value_type": item.get("value_type", "string"),
            }
            for item in sorted(edits, key=lambda entry: entry["element_id"])
        ],
        "derived_scope": derived_scope or {},
    }


def _cell_override_risk_details(edits, observed_values):
    risk_reasons = {
        "table_header_change": "This changes a detected table heading and may change how users interpret the column.",
        "formula_replacement": "This replaces an existing formula and its future calculated behavior.",
        "content_clear": "This removes existing cell content.",
        "content_replacement": "This replaces existing cell content.",
    }
    risks = []
    for edit in edits:
        target = edit["element_id"]
        old_value = _confirmation_json_value(observed_values.get(target))
        new_value = _confirmation_json_value(edit.get("value"))
        coordinate = target.rsplit("!", 1)[-1]
        old_label = _cell_value_label(observed_values.get(target))
        new_label = _cell_value_label(edit.get("value"))
        operation = edit.get("operation", "set_value")
        risks.append(
            {
                "target": target,
                "risk_type": edit.get("_risk_type", "content_replacement"),
                "reason": risk_reasons.get(edit.get("_risk_type"), "Existing content may be replaced."),
                "affected_scope": [target],
                "old_value": old_value,
                "new_value": new_value,
                "recommendation": "Review the old and new values before confirming this exact cell operation.",
                "confirmation_question": f"{coordinate} 单元格原本是‘{old_label}’，您确定要将其覆盖为‘{new_label}’吗？",
                "operation": operation,
            }
        )
    return risks


def _confirmation_id(pending):
    payload = {
        key: pending.get(key)
        for key in (
            "thread_id", "user_id", "request_message_id", "revision", "proposal_revision",
            "preview_attachment_id", "template_fingerprint", "context_fingerprint",
            "document_fingerprint", "cell_edits",
            "operation_scope",
        )
    }
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _cell_override_needs_confirmation(edits, observed_values, manifest):
    targets = {
        item.get("element_id"): item
        for item in manifest
        if isinstance(item, dict) and isinstance(item.get("element_id"), str)
    }
    risks = []
    for edit in edits:
        target_id = edit.get("element_id")
        if target_id not in targets or target_id not in observed_values:
            continue
        old_value = observed_values[target_id]
        new_value = edit.get("value")
        if old_value == new_value:
            continue
        is_header = targets[target_id].get("table_role") == "table_header"
        is_formula = isinstance(old_value, dict) and isinstance(old_value.get("formula"), str)
        is_occupied = old_value not in (None, "")
        if is_header or is_formula or is_occupied:
            risks.append({**edit, "_risk_type": (
                "formula_replacement" if is_formula else
                "table_header_change" if is_header else
                "content_clear" if new_value in (None, "") else
                "content_replacement"
            )})
    return risks


def _repeat_row_expansion_confirmation_risk(repeat_context):
    """Describe structural scope added beyond a template's existing row capacity."""
    if not repeat_context:
        return None
    group = repeat_context["group"]
    expansion = repeat_context["expansion"]
    if not expansion.inserted_rows:
        return None
    start_row = expansion.start_row
    record_count = expansion.record_count
    if expansion.summary_row_before is not None:
        existing_capacity = expansion.summary_row_before - start_row
    else:
        existing_capacity = max(1, record_count - expansion.inserted_rows)
    original_last_row = start_row + existing_capacity - 1
    last_detail_row = start_row + record_count - 1
    added_start_row = original_last_row + 1
    column_ids = sorted(item["column_id"] for item in repeat_context["columns"])
    added_ranges = [
        f"xlsx:{expansion.sheet}!{column}{added_start_row}:{column}{last_detail_row}"
        for column in column_ids
    ]
    formula_impacts = []
    for item in repeat_context["template_text"]:
        if not isinstance(item, dict) or not isinstance(item.get("text"), str):
            continue
        target = item.get("element_id", "")
        match = re.fullmatch(r"xlsx:(.+)!([A-Z]{1,3})([1-9][0-9]*)", target)
        if (
            match
            and match.group(1) == expansion.sheet
            and item["text"].startswith("=")
            and (
                start_row <= int(match.group(3)) <= last_detail_row
                or int(match.group(3)) == expansion.summary_row_after
            )
        ):
            formula_impacts.append({"target": target, "formula": item["text"]})
    summary_formula_targets = [
        item["target"]
        for item in formula_impacts
        if expansion.summary_row_after is not None
        and int(item["target"].rsplit("!", 1)[-1][1:]) == expansion.summary_row_after
    ]
    scope = {
        "collection_field": group["collection_field"],
        "sheet": expansion.sheet,
        "start_row": start_row,
        "record_count": record_count,
        "columns": column_ids,
        "existing_detail_rows": [start_row, original_last_row],
        "expanded_detail_rows": [start_row, last_detail_row],
        "added_detail_rows": [added_start_row, last_detail_row],
        "inserted_rows": expansion.inserted_rows,
        "summary_row_before": expansion.summary_row_before,
        "summary_row_after": expansion.summary_row_after,
    }
    summary_ranges = [
        {"target": item["target"], "formula": item["formula"]}
        for item in formula_impacts
        if item["target"] in summary_formula_targets
    ]
    risk_target = added_ranges[0] if len(added_ranges) == 1 else f"xlsx:{expansion.sheet}!rows:{added_start_row}-{last_detail_row}"
    return {
        "target": risk_target,
        "risk_type": "repeat_row_range_expansion",
        "reason": (
            "The requested row count exceeds the template's existing repeat-row capacity. "
            "Inserting rows changes worksheet structure and can shift formulas and later content."
        ),
        "affected_scope": [
            *added_ranges,
            *summary_formula_targets,
        ],
        "old_value": {
            "detail_rows": [start_row, original_last_row],
            "summary_row": expansion.summary_row_before,
        },
        "new_value": {
            "detail_rows": [start_row, last_detail_row],
            "summary_row": expansion.summary_row_after,
            "inserted_rows": expansion.inserted_rows,
        },
        "formula_impacts": formula_impacts,
        "summary_formula_impacts": summary_ranges,
        "recommendation": "Review the exact added detail rows and the listed formulas before confirming this structural change.",
        "confirmation_question": (
            f"模板现有明细行范围为第 {start_row}–{original_last_row} 行；" if original_last_row >= start_row else ""
        ) + (
            f"本次将扩展到第 {start_row}–{last_detail_row} 行，插入 {expansion.inserted_rows} 行；"
            + (f"汇总行将从第 {expansion.summary_row_before} 行移至第 {expansion.summary_row_after} 行。" if expansion.summary_row_before else "")
            + "请确认是否继续。"
        ),
        "operation_scope": scope,
    }


def _repeat_rows_required_result(report, stored, manifest):
    """Explain a missing repeat_rows operation when a selected record set exceeds a detected data band."""
    selected_ids = stored.get("selected_record_ids", [])
    errors = report.to_dict()
    unknown_targets = errors.get("unknown_targets", [])
    unresolved_targets = list(dict.fromkeys([
        *unknown_targets,
        *errors.get("clarifications", []),
    ]))
    if not isinstance(selected_ids, list) or len(selected_ids) < 2 or not unresolved_targets:
        return None
    manifest_rows = {}
    summary_rows = {}
    for item in stored.get("template_text", []):
        if not isinstance(item, dict) or not isinstance(item.get("text"), str):
            continue
        match = re.fullmatch(
            r"xlsx:(.+)!([A-Z]{1,3})([1-9][0-9]*)", item.get("element_id", "")
        )
        if match and re.search(r"(?i)\b(?:SUM|SUBTOTAL|AGGREGATE)\s*\(", item["text"]):
            summary_rows.setdefault(match.group(1), set()).add(int(match.group(3)))
    for item in manifest:
        if not isinstance(item, dict):
            continue
        match = re.fullmatch(
            r"xlsx:(.+)!([A-Z]{1,3})([1-9][0-9]*)", item.get("element_id", "")
        )
        # This is only a capacity inference, never a write authorization.
        # Include read-only data cells (for example formula columns) so the
        # structural band is inferred from the whole table, then exclude the
        # aggregate row using the template's actual formulas.
        if (
            match
            and item.get("table_role") != "table_header"
            and (item.get("writable") or item.get("table_role") == "table_data")
            and int(match.group(3)) not in summary_rows.get(match.group(1), set())
        ):
            manifest_rows.setdefault(match.group(1), set()).add(int(match.group(3)))
    for target in unresolved_targets:
        match = re.fullmatch(r"xlsx:(.+)!([A-Z]{1,3})([1-9][0-9]*)", target or "")
        if not match:
            continue
        rows = manifest_rows.get(match.group(1), set())
        row_number = int(match.group(3))
        if not rows or row_number not in rows:
            continue
        capacity = max(rows) - min(rows) + 1
        if len(selected_ids) <= capacity:
            continue
        return {
            "status": "incomplete",
            "error_code": "repeat_rows_required",
            "operation_executed": False,
            "unknown_targets": list(unknown_targets),
            "unresolved_targets": unresolved_targets,
            "selected_record_count": len(selected_ids),
            "existing_row_capacity": capacity,
            "message": _(
                "The selected record set contains %(count)s records while the detected data band has %(capacity)s rows. "
                "Do not map individual cells outside the TargetManifest. Call office_prepare_context with the exact "
                "retrieved field paths that are missing, then submit the complete row/column mapping with repeat_rows. "
                "The server will request confirmation before inserting rows beyond the template's existing capacity."
            ) % {"count": len(selected_ids), "capacity": capacity},
        }
    return None


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
        stored_requested_fields = stored_context.get(
            "extra_authorized_collection_fields", {}
        ).get(collection_field, [])
        candidate = next(
            (
                item
                for item in _repeat_row_collection_candidates(
                    env,
                    target,
                    requested_fields_by_collection={
                        collection_field: stored_requested_fields
                    },
                )
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
        mapping_modes = [key for key in ("source_field", "fallback_fields", "concat_fields", "formula") if key in column]
        expected_keys = {"column", *(mapping_modes or [""])}
        if "concat_fields" in column:
            if "separator" in column:
                expected_keys.add("separator")
        if "transform" in column:
            expected_keys.add("transform")
        if (
            not isinstance(column_id, str)
            or not re.fullmatch(r"[A-Z]{1,3}", column_id)
            or column_id in seen_columns
            or len(mapping_modes) != 1
            or set(column) != expected_keys
        ):
            raise ValidationError(_("Each repeat-row column must have exactly one supported mapping mode."))
        seen_columns.add(column_id)
        mode = mapping_modes[0]
        if mode == "source_field":
            source_field = column[mode]
            if not isinstance(source_field, str) or source_field not in candidates:
                raise AccessError(
                    _("Repeat-row source field '%s' is not authorized or is no longer available.")
                    % (source_field if isinstance(source_field, str) else "<invalid>")
                )
            value_type = candidates[source_field]
            clean_column = {"column_id": column_id, "source_field": source_field, "value_type": value_type}
            if "transform" in column:
                try:
                    clean_column["transform"] = validate_transform(column["transform"], value_type)
                except (TypeError, ValueError) as exc:
                    raise ValidationError(_("A repeat-row transformation is invalid.")) from exc
            clean_columns.append(clean_column)
            allowed_fields[source_field] = value_type
        elif mode == "fallback_fields":
            source_fields = column[mode]
            if (
                not isinstance(source_fields, list)
                or not 2 <= len(source_fields) <= 8
                or any(not isinstance(name, str) or name not in candidates for name in source_fields)
                or len(set(source_fields)) != len(source_fields)
            ):
                rejected_fields = (
                    [name for name in source_fields if not isinstance(name, str) or name not in candidates]
                    if isinstance(source_fields, list)
                    else ["<invalid>"]
                )
                raise AccessError(
                    _("Repeat-row fallback field(s) '%s' are not authorized or are no longer available.")
                    % ", ".join(str(name) for name in rejected_fields)
                )
            value_types = {candidates[name] for name in source_fields}
            if len(value_types) != 1:
                raise ValidationError(_("Fallback fields must have the same value type."))
            value_type = next(iter(value_types))
            clean_column = {"column_id": column_id, "source_fields": source_fields, "value_type": value_type}
            if "transform" in column:
                try:
                    clean_column["transform"] = validate_transform(column["transform"], value_type)
                except (TypeError, ValueError) as exc:
                    raise ValidationError(_("A repeat-row transformation is invalid.")) from exc
            clean_columns.append(clean_column)
            allowed_fields.update({name: candidates[name] for name in source_fields})
        elif mode == "concat_fields":
            source_fields = column[mode]
            separator = column.get("separator", "")
            if (
                not isinstance(source_fields, list)
                or not 2 <= len(source_fields) <= 8
                or any(not isinstance(name, str) or name not in candidates for name in source_fields)
                or len(set(source_fields)) != len(source_fields)
            ):
                rejected_fields = (
                    [name for name in source_fields if not isinstance(name, str) or name not in candidates]
                    if isinstance(source_fields, list)
                    else ["<invalid>"]
                )
                raise AccessError(
                    _("Repeat-row concatenation field(s) '%s' are not authorized or are no longer available.")
                    % ", ".join(str(name) for name in rejected_fields)
                )
            if (
                any(candidates[name] != "string" for name in source_fields)
                or not isinstance(separator, str)
                or len(separator) > 32
                or any(ord(char) < 32 for char in separator)
            ):
                raise ValidationError(_("Concatenation requires authorized string fields and a bounded separator."))
            clean_columns.append({
                "column_id": column_id,
                "concat_fields": source_fields,
                "separator": separator,
                "value_type": "string",
            })
            allowed_fields.update({name: candidates[name] for name in source_fields})
        else:
            if "transform" in column:
                raise ValidationError(_("A repeat-row formula cannot include a source-value transformation."))
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
            or (item.get("source_fields") or item.get("concat_fields") or ["formula"])[0]
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
                    "allowed_value_types": ["string", "number", "date", "datetime", "formula"],
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
            else:
                target_spec["allowed_value_types"] = list(
                    dict.fromkeys([*target_spec["allowed_value_types"], column["value_type"]])
                )
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
    _canonicalize_cell_edit_key(rules)
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
    for edit in rules.get("cell_edits", []):
        if isinstance(edit, dict) and "element_id" in edit:
            edit["element_id"] = qualify(edit["element_id"])
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
    for edit in rules.get("cell_edits", []):
        if isinstance(edit, dict) and "element_id" in edit:
            edit["element_id"] = resolve(edit["element_id"])
    for patch in rules.get("format_patches", []):
        if isinstance(patch, dict) and "element_id" in patch:
            patch["element_id"] = resolve(patch["element_id"])
    for key in ("clear_targets", "skipped_targets"):
        if key in rules:
            rules[key] = [resolve(element_id) for element_id in rules[key]]
    for clarification in rules["clarifications"]:
        clarification["element_id"] = resolve(clarification["element_id"])


def _canonicalize_cell_edit_key(rules):
    """Normalize persisted legacy header edits to the generic cell operation."""
    if not isinstance(rules, dict) or "header_edits" not in rules:
        return rules
    if "cell_edits" in rules:
        raise MappingParseError("duplicate_explicit_cell_edit_location")
    legacy_edits = rules.pop("header_edits")
    if not isinstance(legacy_edits, list):
        raise MappingParseError("invalid_cell_edits")
    rules["cell_edits"] = [
        {**item, "value_type": "string"}
        if isinstance(item, dict) and set(item) == {"element_id", "value"}
        else item
        for item in legacy_edits
    ]
    return rules


def _merge_mapping_patch(current, patch):
    """Apply the targets mentioned in a new Proposal to the persisted rules.

    Mapping tool calls are conversational patches. Empty arrays do not mean
    "delete everything"; a target changes only when the new Proposal contains
    a mapping, clarification, skip, or explicit clear for that target.
    """
    current = dict(current) if isinstance(current, dict) else {}
    patch = dict(patch)
    _canonicalize_cell_edit_key(current)
    _canonicalize_cell_edit_key(patch)
    result = {
        "schema_version": patch["schema_version"],
        "mappings": [item for item in current.get("mappings", []) if isinstance(item, dict)],
        "clarifications": [item for item in current.get("clarifications", []) if isinstance(item, dict)],
        "skipped_targets": list(current.get("skipped_targets", [])),
    }
    if "cell_edits" in current or "cell_edits" in patch:
        result["cell_edits"] = [
            dict(item) for item in current.get("cell_edits", []) if isinstance(item, dict)
        ]
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
    patch_cell_edits = {}
    patch_record_cell_edits = {}
    for item in patch.get("cell_edits", []):
        target = _cell_edit_identity(item)
        if isinstance(item, dict) and isinstance(item.get("record_target"), dict):
            if target in patch_record_cell_edits:
                raise MappingParseError("duplicate_cell_edit_target")
            patch_record_cell_edits[target] = item
        else:
            coordinate = item.get("element_id")
            if coordinate in patch_cell_edits:
                raise MappingParseError("duplicate_cell_edit_target")
            patch_cell_edits[coordinate] = item

    # Mapping and clarification express incompatible outcomes and must be
    # clarified. Explicit clears are intentionally authoritative: the model
    # may echo an old mapping for a cell while also carrying the user's clear
    # instruction, and clearing must not be rejected or silently lose to it.
    if (set(patch_mappings) & set(patch_clarifications)) - set(patch_cell_edits):
        raise MappingParseError("conflicting_patch_target")
    if set(patch_cell_edits) & (set(patch_clarifications) | patch_skips):
        # A concrete user-directed cell operation supersedes stale no-op
        # annotations for that same coordinate.
        patch_clarifications = {
            target: item for target, item in patch_clarifications.items()
            if target not in patch_cell_edits
        }
        patch_skips.difference_update(patch_cell_edits)
    for target in patch_cell_edits:
        patch_mappings.pop(target, None)
    if set(patch_cell_edits) & patch_clears:
        raise MappingParseError("conflicting_patch_target")

    touched = set(patch_mappings) | set(patch_clarifications) | patch_skips | patch_clears | set(patch_cell_edits)
    touched_edit_identities = {"coordinate:" + target for target in patch_cell_edits}
    touched_edit_identities.update(patch_record_cell_edits)
    if not touched and not patch_record_cell_edits:
        return result

    result["mappings"] = [item for item in result["mappings"] if item.get("element_id") not in touched]
    result["clarifications"] = [
        item for item in result["clarifications"] if item.get("element_id") not in touched
    ]
    result["skipped_targets"] = [item for item in result["skipped_targets"] if item not in touched]
    if "cell_edits" in result:
        result["cell_edits"] = [
            item for item in result["cell_edits"] if _cell_edit_identity(item) not in touched_edit_identities
        ]
    if "clear_targets" in result:
        result["clear_targets"] = [item for item in result["clear_targets"] if item not in touched]

    # An explicit clear is authoritative. Otherwise a concrete mapping takes
    # precedence over stale skip/clarification annotations for the same cell.
    for target in sorted(touched):
        if target in patch_cell_edits:
            result["mappings"] = [item for item in result["mappings"] if item.get("element_id") != target]
            result.setdefault("cell_edits", []).append(patch_cell_edits[target])
        elif target in patch_clears:
            result.setdefault("clear_targets", []).append(target)
        elif target in patch_mappings:
            result["mappings"].append(patch_mappings[target])
        elif target in patch_clarifications:
            result["clarifications"].append(patch_clarifications[target])
        elif target in patch_skips:
            result["skipped_targets"].append(target)

    if patch_record_cell_edits:
        result.setdefault("cell_edits", []).extend(
            patch_record_cell_edits[target] for target in sorted(patch_record_cell_edits)
        )

    result["skipped_targets"] = sorted(set(result["skipped_targets"]))
    if "clear_targets" in result:
        result["clear_targets"] = sorted(set(result["clear_targets"]))
    return result


def _cell_edit_identity(item):
    """Return a patch key for either a stable record target or a coordinate."""
    if isinstance(item, dict) and isinstance(item.get("record_target"), dict):
        target = item["record_target"]
        return "record:" + json.dumps(target, sort_keys=True, separators=(",", ":"))
    if isinstance(item, dict) and isinstance(item.get("element_id"), str):
        return "coordinate:" + item["element_id"]
    raise MappingParseError("invalid_cell_edit_target")


def _merge_bound_cell_edit_patch(current, incoming):
    """Replace prior edits only when a new patch resolves to the same target.

    This second merge is needed after repeat-row coordinates have been bound to
    their stable record identities. Before binding, ``I2`` and a saved
    ``record_target`` for the record currently occupying I2 are different
    syntactic keys even though they describe the same logical cell.
    """
    incoming = [dict(item) for item in incoming if isinstance(item, dict)]
    incoming_identities = {_cell_edit_identity(item) for item in incoming}
    retained = [
        dict(item)
        for item in current
        if isinstance(item, dict) and _cell_edit_identity(item) not in incoming_identities
    ]
    return [*retained, *incoming]


def _repeat_column_signature(mapping, group_id, target_id=None):
    """Normalize one persisted or incoming repeat-column mapping for comparison."""
    prefix = f"{group_id}::"
    if isinstance(mapping.get("formula_template"), str):
        mode, fields, separator, formula = "formula", (), "", mapping["formula_template"]
    elif isinstance(mapping.get("formula"), str):
        mode, fields, separator = "formula", (), ""
        formula = _repeat_formula_template(mapping["formula"], target_id) if target_id else mapping["formula"]
    elif isinstance(mapping.get("source_field"), str) and mapping["source_field"].startswith(prefix):
        mode, fields, separator, formula = "source_field", (mapping["source_field"][len(prefix):],), "", ""
    elif isinstance(mapping.get("source_fields"), list) and all(
        isinstance(name, str) and name.startswith(prefix) for name in mapping["source_fields"]
    ):
        mode = "fallback_fields"
        fields = tuple(name[len(prefix):] for name in mapping["source_fields"])
        separator, formula = "", ""
    elif isinstance(mapping.get("concat_fields"), list) and all(
        isinstance(name, str) and name.startswith(prefix) for name in mapping["concat_fields"]
    ):
        mode = "concat_fields"
        fields = tuple(name[len(prefix):] for name in mapping["concat_fields"])
        separator, formula = mapping.get("separator", ""), ""
    else:
        return None
    transform = mapping.get("transform")
    return mode, fields, separator, formula, json.dumps(transform, sort_keys=True, separators=(",", ":"))


def _incoming_repeat_column_signature(column):
    mode = next(
        (key for key in ("source_field", "fallback_fields", "concat_fields", "formula") if key in column),
        None,
    )
    if mode == "source_field":
        fields = (column[mode],)
    elif mode in {"fallback_fields", "concat_fields"}:
        fields = tuple(column[mode]) if isinstance(column[mode], list) else ()
    else:
        fields = ()
    separator = column.get("separator", "") if mode == "concat_fields" else ""
    formula = column.get("formula", "") if mode == "formula" else ""
    transform = column.get("transform")
    return mode, fields, separator, formula, json.dumps(transform, sort_keys=True, separators=(",", ":"))


def _changed_repeat_columns(stored_groups, persisted_rules, repeat_rows):
    """Identify only explicitly redefined repeated columns; leave other edits intact."""
    if not isinstance(stored_groups, list) or len(stored_groups) != 1 or not isinstance(repeat_rows, list):
        return set()
    group = stored_groups[0]
    if not isinstance(group, dict) or not group.get("target_rows") or len(repeat_rows) != 1:
        return set()
    group_id = group.get("group_id")
    mappings = {
        item.get("element_id"): item
        for item in persisted_rules.get("mappings", [])
        if isinstance(item, dict)
    }
    first_row = group["target_rows"][0]
    previous = {}
    for target in first_row.get("targets", []):
        if not isinstance(target, dict) or not isinstance(target.get("column_id"), str):
            continue
        element_id = target.get("element_id")
        mapping = mappings.get(element_id, {})
        previous[target["column_id"]] = _repeat_column_signature(mapping, group_id, element_id)
    incoming = repeat_rows[0].get("columns", []) if isinstance(repeat_rows[0], dict) else []
    changed = set()
    for column in incoming:
        if not isinstance(column, dict) or not isinstance(column.get("column"), str):
            continue
        column_id = column["column"]
        incoming_signature = _incoming_repeat_column_signature(column)
        if previous.get(column_id) != incoming_signature:
            changed.add(column_id)
    return changed


def _drop_superseded_repeat_cell_edits(edits, group_id, changed_columns):
    if not changed_columns:
        return edits
    return [
        item for item in edits
        if not (
            isinstance(item, dict)
            and isinstance(item.get("record_target"), dict)
            and item["record_target"].get("group_id") == group_id
            and item["record_target"].get("column") in changed_columns
        )
    ]


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
    for item in rules.get("cell_edits", []):
        if isinstance(item, dict) and isinstance(item.get("element_id"), str):
            item["element_id"] = _shift_cell_target(item["element_id"], sheet, shift_at, shift_by)
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

    @llm_tool(
        name="office",
        schema={
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["status", "retrieve", "plan", "edit", "accept", "reject"],
                    "description": "The bounded Office action. Candidate identity is resolved from this Thread's trusted tool history.",
                },
                "query_spec": {
                    "type": ["object", "null"],
                    "additionalProperties": False,
                    "description": "Required only for action=retrieve. Uses the existing odoo_record_retriever query parameters; no workbook version is required for this read-only action.",
                    "properties": {
                        "model": {"type": "string", "minLength": 1},
                        "domain": {
                            "type": "array",
                            "items": {
                                "type": "array",
                                "items": {"anyOf": [
                                    {"type": "string"}, {"type": "integer"},
                                    {"type": "number"}, {"type": "boolean"},
                                    {"type": "null"},
                                ]},
                            },
                        },
                        "fields": {"type": "array", "items": {"type": "string"}},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 500},
                        "offset": {"type": "integer", "minimum": 0},
                        "order": {"type": ["string", "null"]},
                        "include_pagination": {"type": "boolean"},
                    },
                    "required": ["model"],
                },
                "interpretation": {
                    "type": ["object", "null"],
                    "additionalProperties": False,
                    "properties": {
                        "summary": {"type": "string", "maxLength": 2000},
                        "target_scope": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["description", "basis"],
                            "properties": {
                                "description": {"type": "string", "maxLength": 1000},
                                "basis": {"type": "string", "enum": ["explicit", "inferred", "ambiguous"]},
                            },
                        },
                        "assumptions": {"type": "array", "maxItems": 32, "items": {"type": "string", "maxLength": 512}},
                        "unknowns": {"type": "array", "maxItems": 32, "items": {"type": "string", "maxLength": 512}},
                    },
                    "required": ["summary", "target_scope", "assumptions", "unknowns"],
                },
                "expected_effect": {
                    "type": ["object", "null"],
                    "additionalProperties": False,
                    "description": (
                        "Use the frozen CB-03 Expected Effect shape: target_scopes, allowed_change_kinds, "
                        "expected_assertions, and unknowns. For a plan, omit parent_version_id, input_sha256, "
                        "and effect_digest; the server binds those to the current accepted workbook and computes "
                        "the digest. Reuse the returned canonical expected_effect for edit. For a cell value change, "
                        "target_scopes contains {kind:'cell',sheet:'<worksheet>',address:'A1'}, allowed_change_kinds "
                        "contains 'cell_value', and expected_assertions contains {kind:'cell_value',sheet:'<worksheet>', "
                        "address:'A1',value_type:'string',value:'new value'}. Do not send legacy targets/change/scope "
                        "keys. This is a bounded verification declaration, not an Excel editing DSL."
                    ),
                    "properties": {
                        "schema_version": {"type": "string", "enum": ["1"]},
                        "parent_version_id": {"type": "integer", "minimum": 1},
                        "input_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                        "effect_digest": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                        "target_scopes": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "kind": {"type": "string", "enum": ["cell", "range", "worksheet_structure", "workbook_structure"]},
                                    "sheet": {"type": "string"},
                                    "address": {"type": "string", "pattern": "^[A-Z]{1,3}[1-9][0-9]*$"},
                                    "start": {"type": "string", "pattern": "^[A-Z]{1,3}[1-9][0-9]*$"},
                                    "end": {"type": "string", "pattern": "^[A-Z]{1,3}[1-9][0-9]*$"},
                                },
                                "required": ["kind"],
                            },
                        },
                        "allowed_change_kinds": {
                            "type": "array",
                            "items": {"type": "string", "enum": ["cell_value", "formula_text", "cell_style", "worksheet_structure", "workbook_structure"]},
                        },
                        "expected_assertions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "kind": {"type": "string", "enum": ["cell_value"]},
                                    "sheet": {"type": "string"},
                                    "address": {"type": "string", "pattern": "^[A-Z]{1,3}[1-9][0-9]*$"},
                                    "value_type": {"type": "string", "enum": ["string", "number", "boolean", "blank", "date", "datetime"]},
                                    "value": {"type": ["string", "number", "boolean", "null"]},
                                },
                                "required": ["kind", "sheet", "address", "value_type", "value"],
                            },
                        },
                        "unknowns": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["target_scopes", "allowed_change_kinds", "expected_assertions", "unknowns"],
                },
                "model_risk_claims": {"type": ["array", "null"], "maxItems": 32, "items": {"type": "object"}, "description": "Unverified model-generated claims to display separately from locally verified facts. Their presence does not trigger local business-risk policy."},
                "confirmation_required": {
                    "type": ["boolean", "null"],
                    "description": "For plan/edit, the LLM's explicit judgment whether a material business risk not already authorized by the user's request needs a real user confirmation. The server binds this value and does not infer business risk. Required for plan and must be repeated unchanged for edit.",
                },
                "confirmation_reason": {
                    "type": ["string", "null"],
                    "maxLength": 2000,
                    "description": "User-facing explanation supplied by the LLM when confirmation_required=true. It is a model claim, not a locally verified business fact. Must be repeated unchanged with edit.",
                },
            },
            "required": ["action"],
        },
        destructive_hint=True,
        description=(
            "The single Office facade. action=retrieve is a read-only call to the Thread-bound existing Odoo "
            "Record Retriever and does not require an accepted workbook version. Candidate actions resolve the "
            "current user's Thread, accepted workbook version, and persisted Office tool history. The LLM owns intent ambiguity and business-risk judgment; "
            "for plan, explicitly provide confirmation_required and any confirmation_reason. The server binds that "
            "decision to the current user, Thread, Session, version, file SHA and request, then verifies a real user "
            "confirmation before execution when requested. A generated Candidate never advances Current until the "
            "user explicitly accepts it. Local checks remain authoritative for permissions, safety, versions and file "
            "integrity. External Provider file processing remains disabled while the SRS/data-policy release gate is open."
        ),
    )
    def office(
        self,
        action: str,
        query_spec: dict | None = None,
        interpretation: dict | None = None,
        expected_effect: dict | None = None,
        model_risk_claims: list[dict] | None = None,
        confirmation_required: bool | None = None,
        confirmation_reason: str | None = None,
    ) -> dict:
        """Dispatch a bounded Office action through trusted services."""
        thread, tool_message = self._office_tool_context()
        return dispatch_office_action(
            self.env,
            thread,
            tool_message,
            action,
            query_spec=query_spec,
            interpretation=interpretation,
            expected_effect=expected_effect,
            model_risk_claims=model_risk_claims,
            confirmation_required=confirmation_required,
            confirmation_reason=confirmation_reason,
        )

    def _cell_override_confirmation_gate(
        self,
        thread,
        session,
        edits,
        manifest,
        expected_revision,
        force_override,
        operation_payload,
        additional_risks=None,
        derived_scope=None,
    ):
        """Return a structured risk decision; only an exact bound approval permits the write."""
        pending = {}
        had_pending = bool(session.pending_cell_override_json)
        if session.pending_cell_override_json:
            try:
                pending = json.loads(session.pending_cell_override_json)
            except (TypeError, json.JSONDecodeError):
                return {
                    "status": "error",
                    "error_code": "cell_override_confirmation_state_invalid",
                    "operation_executed": False,
                    "message": _("The overwrite confirmation state is invalid. Ask the user to issue the cell edit again."),
                }
        try:
            observed_values, content, is_xlsx = _inspect_cell_edits(
                self.env,
                session,
                edits,
                manifest,
                inspect_for_risk=bool(additional_risks),
            )
        except AccessError:
            return {
                "status": "blocked",
                "error_code": "cell_override_target_access_denied",
                "operation_executed": False,
                "message": _("The current user cannot read the document needed to verify this overwrite."),
            }
        except (UserError, ValidationError, OfficeCoreError) as exc:
            return {
                "status": "error",
                "error_code": "cell_override_inspection_failed",
                "operation_executed": False,
                "message": str(exc),
            }
        occupied = (
            _cell_override_needs_confirmation(edits, observed_values, manifest)
            if is_xlsx
            else []
        )
        risks = [*_cell_override_risk_details(occupied, observed_values), *(additional_risks or [])]
        operation_scope = _cell_override_operation_scope(
            self.env, thread, session, edits, content, operation_payload, derived_scope
        )
        latest_user = _latest_office_user_message(self.env, thread)
        signature_matches = bool(pending) and (
            _cell_edit_signature(pending.get("cell_edits", [])) == _cell_edit_signature(edits)
        )
        current_binding_matches = bool(pending) and all(
            (
                pending.get("thread_id") == thread.id,
                pending.get("user_id") == self.env.uid,
                pending.get("revision") == session.revision == expected_revision,
                pending.get("proposal_revision") == session.proposal_revision,
                pending.get("preview_attachment_id") == (session.preview_attachment_id.id or False),
                pending.get("template_fingerprint")
                == (session.template_fingerprint or hashlib.sha256(session.source_attachment_id.raw or b"").hexdigest()),
                pending.get("context_fingerprint")
                == hashlib.sha256((session.context_json or "{}").encode("utf-8")).hexdigest(),
                pending.get("document_fingerprint") == hashlib.sha256(content).hexdigest(),
                pending.get("observed_values") == _confirmation_json_values(observed_values),
                pending.get("operation_scope") == operation_scope,
            )
        )
        later_users = self.env["mail.message"]
        if pending and current_binding_matches and signature_matches:
            later_users = self.env["mail.message"].search(
                [
                    ("model", "=", "llm.thread"),
                    ("res_id", "=", thread.id),
                    ("llm_role", "=", "user"),
                    ("author_id", "=", self.env.user.partner_id.id),
                    ("is_error", "=", False),
                    ("id", ">", pending.get("request_message_id", 0)),
                    ("id", "<=", latest_user.id),
                ],
                order="id asc",
            )
        confirmed_by_user = False
        if pending and current_binding_matches and signature_matches:
            confirmed_by_user = (
                len(later_users) == 1
                and later_users == latest_user
                and _is_exact_cell_override_confirmation(latest_user.body)
            )
            rejected_by_user = (
                len(later_users) == 1
                and later_users == latest_user
                and _is_exact_cell_override_rejection(latest_user.body)
            )
            if rejected_by_user:
                try:
                    session._clear_pending_cell_override_from_service(expected_revision)
                except AccessError:
                    return {
                        "status": "blocked",
                        "error_code": "cell_override_rejection_access_denied",
                        "operation_executed": False,
                        "message": _("The current user cannot update this confirmation state. No overwrite was performed."),
                    }
                except ValidationError:
                    return {
                        "status": "error",
                        "error_code": "cell_override_rejection_state_stale",
                        "operation_executed": False,
                        "message": _("The refusal could not be recorded because the confirmation state changed. No overwrite was performed."),
                    }
                return {
                    "status": "blocked",
                    "error_code": "user_rejected_confirmation",
                    "operation_executed": False,
                    "operation_scope": pending.get("operation_scope", {}),
                    "affected_scope": list(dict.fromkeys(
                        target
                        for risk in pending.get("risks", [])
                        for target in risk.get("affected_scope", [risk.get("target")])
                        if target
                    )),
                    "message": _("The user declined the overwrite. No file content was changed."),
                }
        if pending and current_binding_matches and signature_matches and confirmed_by_user:
            # The user-authored confirmation, plus the server-side binding
            # checks above, is the authorization. A Provider may omit the
            # optional force_override hint; do not require a second turn.
            return _CONFIRMATION_AUTHORIZED

        if risks:
            # A repeated tool call in the same model turn must not rebind the
            # pending authorization to its own prior request. Keep that exact
            # pending payload until the user confirms or submits a new edit.
            reuse_pending = pending and current_binding_matches and signature_matches
            if (
                reuse_pending
                and latest_user.id != pending.get("request_message_id")
                and not _is_exact_cell_override_confirmation(latest_user.body)
                and not force_override
            ):
                # A new natural-language instruction starts a fresh confirmation
                # attempt; an earlier approval cannot be reused for it.
                reuse_pending = False
            if not reuse_pending:
                new_pending = _cell_override_pending_payload(
                    self.env,
                    thread,
                    session,
                    latest_user,
                    edits,
                    observed_values,
                    content,
                    operation_scope,
                    risks,
                )
                try:
                    session._set_pending_cell_override_from_service(
                        json.dumps(new_pending, ensure_ascii=False), expected_revision
                    )
                except AccessError:
                    return {
                        "status": "blocked",
                        "error_code": "cell_override_confirmation_access_denied",
                        "operation_executed": False,
                        "message": _("The current user cannot create this confirmation state."),
                    }
                except ValidationError as exc:
                    return {
                        "status": "error",
                        "error_code": "cell_override_confirmation_state_stale",
                        "operation_executed": False,
                        "message": str(exc),
                    }
                pending = new_pending
            response_risks = pending.get("risks", risks)
            changed_binding = had_pending and not current_binding_matches
            if changed_binding:
                confirmation_error = "confirmation_scope_changed"
            elif force_override:
                confirmation_error = "confirmation_not_received"
            else:
                confirmation_error = "confirmation_required"
            return {
                "status": "needs_confirmation",
                "error_code": confirmation_error,
                "confirmation_id": _confirmation_id(pending),
                "operation_executed": False,
                "session_id": session.id,
                "revision": session.revision,
                "proposal_revision": session.proposal_revision,
                "target": response_risks[0].get("target"),
                "current_value": _confirmation_json_value(response_risks[0].get("old_value")),
                "requested_value": _confirmation_json_value(response_risks[0].get("new_value")),
                "risk_type": response_risks[0]["risk_type"] if len(response_risks) == 1 else "multiple_business_risks",
                "risks": response_risks,
                "affected_scope": list(dict.fromkeys(
                    target
                    for risk in response_risks
                    for target in risk.get("affected_scope", [risk.get("target")])
                    if target
                )),
                "operation_scope": pending.get("operation_scope", {}),
                "recommendation": _(
                    "Confirm only if these exact changes are intended. Confirmation applies to the listed targets and values; no file is written before confirmation."
                ),
                "confirmation_question": "\n".join(
                    risk.get("confirmation_question", "") for risk in response_risks
                ),
                "confirmation_questions": [
                    risk.get("confirmation_question", "") for risk in response_risks
                ],
                "message": _("Explain each listed risk and ask the exact confirmation question. Wait for a new user reply. If the user replies exactly ‘确认’, repeat the identical operation; the server verifies the user confirmation and exact operation scope. If the user explicitly declines, repeat the identical operation to record the refusal; no write will occur."),
            }

        if pending:
            try:
                session._clear_pending_cell_override_from_service(expected_revision)
            except AccessError:
                return {
                    "status": "blocked",
                    "error_code": "cell_override_confirmation_access_denied",
                    "operation_executed": False,
                    "message": _("The current user cannot update this confirmation state."),
                }
            except ValidationError as exc:
                return {
                    "status": "error",
                    "error_code": "cell_override_confirmation_state_stale",
                    "operation_executed": False,
                    "message": str(exc),
                }
        return None

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
            "selected record before use. For related repeat-row values, pass requested_fields_by_collection as a map "
            "from the exact readable collection field to exact Many2one scalar paths; each path is checked on every row "
            "with the current user's ORM permissions and only approved paths are added to that collection's schema. "
            "Never send attachment bytes to the model."
        ),
    )
    def office_prepare_context(
        self,
        target_model: str,
        target_record_id: int | None = None,
        target_record_ids: list[int] | None = None,
        requested_fields: list[str] | None = None,
        requested_fields_by_collection: dict[str, list[str]] | None = None,
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
        previous_extra_collection_fields = {}
        if session:
            previous_context = json.loads(session.context_json or "{}")
            previous_extra_fields = previous_context.get("extra_authorized_fields", [])
            previous_extra_collection_fields = previous_context.get(
                "extra_authorized_collection_fields", {}
            )
        requested_fields = [] if requested_fields is None else requested_fields
        if (
            not isinstance(requested_fields, list)
            or len(requested_fields) > 64
            or any(not isinstance(name, str) or not name.strip() or len(name) > 255 for name in requested_fields)
            or len(set(requested_fields)) != len(requested_fields)
        ):
            raise ValidationError(_("The explicitly requested field list is invalid."))
        reauthorized_field_paths = list(dict.fromkeys([*previous_extra_fields, *requested_fields]))
        requested_fields_by_collection = _normalize_requested_collection_fields(
            requested_fields_by_collection
        )
        # ``selected_records`` is a synthetic repeat-row collection over the
        # explicitly bound record set, not an Odoo one2many field. Reauthorize
        # its requested paths through the same per-record ORM checks as root
        # fields; the candidate is assembled below from this approved map.
        requested_selected_record_fields = requested_fields_by_collection.get(
            SELECTED_RECORDS_COLLECTION, []
        )
        reauthorized_field_paths = list(
            dict.fromkeys([*reauthorized_field_paths, *requested_selected_record_fields])
        )
        requested_related_collection_fields = {
            collection: paths
            for collection, paths in requested_fields_by_collection.items()
            if collection != SELECTED_RECORDS_COLLECTION
        }
        previous_related_collection_fields = {
            collection: paths
            for collection, paths in previous_extra_collection_fields.items()
            if collection != SELECTED_RECORDS_COLLECTION
        }
        reauthorized_collection_fields = {
            collection: list(
                dict.fromkeys(
                    [
                        *previous_related_collection_fields.get(collection, []),
                        *requested_related_collection_fields.get(collection, []),
                    ]
                )
            )
            for collection in sorted(
                set(previous_related_collection_fields) | set(requested_related_collection_fields)
            )
        }
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
            _repeat_row_collection_candidates(
                self.env,
                target,
                requested_fields_by_collection=reauthorized_collection_fields,
            )
            if is_xlsx_upload
            else []
        )
        selected_records_candidate = None
        if is_xlsx_upload and (
            len(selected_record_ids) > 1 or requested_selected_record_fields
        ):
            selected_record_unavailable_fields = [
                path for path in requested_selected_record_fields if path not in allowed_fields
            ]
            selected_record_unavailable_reasons = {}
            for path in selected_record_unavailable_fields:
                reasons = {
                    reason
                    for record in selected_records
                    for value_type, reason in [_scalar_field_path_status(record, path)]
                    if not value_type and reason
                }
                selected_record_unavailable_reasons[path] = sorted(reasons) or [
                    "inconsistent_type_across_records"
                ]
            selected_records_candidate = {
                "collection_field": SELECTED_RECORDS_COLLECTION,
                "relation_model": target_model,
                "inverse_field": "id",
                "row_count": len(selected_record_ids),
                "allowed_fields": allowed_fields,
                "unavailable_requested_fields": selected_record_unavailable_fields,
                "unavailable_requested_field_reasons": selected_record_unavailable_reasons,
            }
            repeat_row_collections.append(selected_records_candidate)
        available_by_collection = {
            item["collection_field"]: item["allowed_fields"]
            for item in repeat_row_collections
        }
        extra_authorized_collection_fields = {
            collection: [
                path
                for path in paths
                if path in available_by_collection.get(collection, {})
            ]
            for collection, paths in reauthorized_collection_fields.items()
        }
        extra_authorized_collection_fields = {
            collection: paths
            for collection, paths in extra_authorized_collection_fields.items()
            if paths
        }
        unavailable_requested_collection_fields = {
            collection: [
                path
                for path in paths
                if path
                not in (
                    allowed_fields
                    if collection == SELECTED_RECORDS_COLLECTION
                    else available_by_collection.get(collection, {})
                )
            ]
            for collection, paths in requested_fields_by_collection.items()
        }
        unavailable_requested_collection_fields = {
            collection: paths
            for collection, paths in unavailable_requested_collection_fields.items()
            if paths
        }
        requested_collection_candidates = {
            item["collection_field"]: item
            for item in repeat_row_collections
        }
        unavailable_requested_collection_field_reasons = {
            collection: {
                path: (
                    requested_collection_candidates[collection]["unavailable_requested_field_reasons"].get(
                        path, ["not_authorized_or_unavailable"]
                    )
                    if collection in requested_collection_candidates
                    else ["collection_not_authorized_or_unavailable"]
                )
                for path in paths
            }
            for collection, paths in unavailable_requested_collection_fields.items()
        }
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
                or existing.get("extra_authorized_collection_fields", {})
                != extra_authorized_collection_fields
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
                    extra_authorized_collection_fields=extra_authorized_collection_fields,
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
                extra_authorized_collection_fields=extra_authorized_collection_fields,
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
                elif isinstance(first_mapping.get("concat_fields"), list) and all(
                    isinstance(name, str) and name.startswith(prefix)
                    for name in first_mapping["concat_fields"]
                ):
                    namespaced_fields = first_mapping["concat_fields"]
                    if any(
                        mappings_by_target.get(target["element_id"], {}).get("concat_fields") != namespaced_fields
                        or mappings_by_target.get(target["element_id"], {}).get("separator", "")
                        != first_mapping.get("separator", "")
                        for row in rows
                        for target in row.get("targets", [])
                        if target.get("column_id") == first_target.get("column_id")
                    ):
                        consistent = False
                        break
                    column_spec = {
                        "column": first_target["column_id"],
                        "concat_fields": [name[len(prefix):] for name in namespaced_fields],
                        "separator": first_mapping.get("separator", ""),
                    }
                elif isinstance(first_mapping.get("concat_fields"), list) and all(
                    isinstance(name, str) and name.startswith(prefix)
                    for name in first_mapping["concat_fields"]
                ):
                    namespaced_fields = first_mapping["concat_fields"]
                    if any(
                        mappings_by_target.get(target["element_id"], {}).get("concat_fields") != namespaced_fields
                        or mappings_by_target.get(target["element_id"], {}).get("separator", "")
                        != first_mapping.get("separator", "")
                        for row in rows
                        for target in row.get("targets", [])
                        if target.get("column_id") == first_target.get("column_id")
                    ):
                        consistent = False
                        break
                    column_spec = {
                        "column": first_target["column_id"],
                        "concat_fields": [name[len(prefix):] for name in namespaced_fields],
                        "separator": first_mapping.get("separator", ""),
                    }
                else:
                    consistent = False
                    break
                if "transform" in first_mapping:
                    transforms = [
                        mappings_by_target.get(target["element_id"], {}).get("transform")
                        for row in rows
                        for target in row.get("targets", [])
                        if target.get("column_id") == first_target.get("column_id")
                    ]
                    if any(transform != first_mapping["transform"] for transform in transforms):
                        consistent = False
                        break
                    column_spec["transform"] = first_mapping["transform"]
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
                    "string_field_concatenation",
                    "safe_arithmetic_formulas",
                    "blank_string_values",
                    "template_formula_row_expansion",
                    "number_format_patches",
                    "table_column_clear_and_format",
                    "explicit_coordinate_cell_edits",
                ],
                "unsupported": ["conditions", "arbitrary_excel_functions", "cross_sheet_or_external_formulas", "docx"],
                "repeat_rows_contract": {
                    "collection_field": "必须选自 repeat_row_collections；selected_records 表示本次明确传入并绑定到 Session 的整组源记录",
                    "sheet": "模板中的工作表名",
                    "start_row": "首条明细行号",
                    "columns": "每列只能指定 source_field、fallback_fields（按顺序取首个非空字段）、concat_fields（按 separator 拼接多个已授权字符串字段）或安全算术 formula 其中一种；{row} 是行号，只能写在单元格引用内，例如 =E{row}*D{row}*2。",
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
            "unavailable_requested_collection_fields": unavailable_requested_collection_fields,
            "unavailable_requested_collection_field_reasons": unavailable_requested_collection_field_reasons,
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
            "Apply a conversational patch to the current direct/fallback/concatenation/formula/typed-literal Proposal, explicit coordinate cell edits, and optional single XLSX repeat_rows layout, then validate it against the "
            "current Session, server-authorized related collection, fields, target cells and revision. "
            "The Proposal is a patch: targets omitted from mappings, clarifications, skipped_targets, and clear_targets remain unchanged. "
            "Supports independent number-format patches and detected table-column clear/format operations; these do not replace cell values. "
            "Use the separate cell_edits operation when the user explicitly names a coordinate and asks to set its value. If the inspected cell has a value, formula, or is a table heading, the first call returns status needs_confirmation with the exact old/new values and scope, without saving or rendering. Explain that risk, then wait. Only after the user replies exactly 确认, repeat the identical operation. If the user explicitly declines, repeat the identical operation so the server records status blocked without writing. The server verifies the Thread, Session, revision, current preview, document bytes, target, value and user message; force_override is only an optional execution hint and never authorizes a write by itself. The confirmed edit does not change other source-field mappings or cell styles. Normal field mappings remain restricted to writable data targets. "
            "Template labels do not create mandatory business targets. Use the optional "
            "clear_targets list or a compact mapping {element_id, value: \"\"} only for cells the user explicitly asks to blank. Existing formula cells not written "
            "by the Proposal stay unchanged; an explicit mapping or clear replaces the formula at that target. "
            "A typed literal is a scalar the user supplied or requested as a deterministic calculation; never invent one. "
            "The server derives the related row count and target cells. If the count requires inserting rows "
            "beyond the template's existing repeat-row capacity, the first call returns needs_confirmation with "
            "the exact added rows, affected columns, shifted summary row, and formula impacts; no mapping or file "
            "is saved. Explain that scope, wait for the user's exact 确认, and retry the identical Proposal and "
            "repeat_rows. The confirmation binds the selected records, operation, file bytes, "
            "Thread, user, and revisions; the flag alone never expands its scope. If a multi-record mapping omits "
            "repeat_rows and proposes an out-of-manifest cell inside the detected data band, follow the returned "
            "repeat_rows_required guidance instead of inventing coordinates. M1 then performs expansion and read-back "
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
        cell_edits: list | None = None,
        header_edits: list | None = None,
        force_override: bool = False,
    ) -> dict:
        """Execute a preview patch and normalize its public operation status."""
        try:
            result = self._office_save_mapping_preview_impl(
                session_id,
                expected_revision,
                proposal,
                repeat_rows=repeat_rows,
                clear_columns=clear_columns,
                format_patches=format_patches,
                cell_edits=cell_edits,
                header_edits=header_edits,
                force_override=force_override,
            )
        except AccessError:
            return {
                "status": "blocked",
                "error_code": "access_denied",
                "operation_executed": False,
                "message": _("The current user is not authorized to execute this Office operation."),
            }
        except (ValidationError, UserError, OfficeCoreError) as exc:
            return {
                "status": "error",
                "error_code": getattr(exc, "name", None) or "office_operation_failed",
                "operation_executed": False,
                "message": str(exc),
            }
        return _normalize_office_mapping_result(result)

    def _office_save_mapping_preview_impl(
        self,
        session_id: int,
        expected_revision: int,
        proposal: dict,
        repeat_rows: list | None = None,
        clear_columns: list | None = None,
        format_patches: list | None = None,
        cell_edits: list | None = None,
        header_edits: list | None = None,
        force_override: bool = False,
    ) -> dict:
        """Merge a partial direct-field/repeat-row Proposal patch and render its preview."""
        thread, _tool_message = self._office_tool_context()
        session = _owned_session(self.env, session_id)
        if session.thread_id != thread or session.owner_id.id != self.env.uid:
            raise AccessError(_("The mapping Session is unavailable."))
        if type(expected_revision) is not int or expected_revision != session.revision:
            raise ValidationError(_("MAPPING_REVISION_STALE: reload the current Office mapping."))
        if type(force_override) is not bool:
            return {"status": "invalid", "errors": ["force_override_must_be_boolean"]}
        # These operation arrays are exposed both at the tool-call root
        # (the native Provider schema) and inside proposal for compatibility
        # with saved clients. Merge them explicitly before parsing; otherwise
        # llm_tool's signature validation would silently discard unknown root
        # keys and could report a preview whose requested operations never ran.
        if cell_edits is not None and header_edits is not None:
            return {"status": "invalid", "errors": ["duplicate_explicit_cell_edit_location"]}
        top_cell_edits = cell_edits
        if top_cell_edits is None and header_edits is not None:
            top_cell_edits = [
                {"element_id": item.get("element_id"), "value": item.get("value"), "value_type": "string"}
                if isinstance(item, dict) else item
                for item in header_edits
            ] if isinstance(header_edits, list) else header_edits
        if clear_columns is not None or format_patches is not None or top_cell_edits is not None:
            if not isinstance(proposal, dict):
                return {
                    "status": "invalid",
                    "errors": ["invalid_proposal_json"],
                    "details": "proposal must be an object when top-level operations are supplied",
                }
            proposal = dict(proposal)
            if top_cell_edits is not None:
                if "cell_edits" in proposal or "header_edits" in proposal:
                    return {
                        "status": "invalid",
                        "errors": ["duplicate_operation_location"],
                        "details": "cell edits must be supplied either beside proposal or inside proposal, not both",
                    }
                # Explicit user-directed writes replace stale no-op
                # annotations for the exact same target.
                cell_targets = {
                    item.get("element_id")
                    for item in top_cell_edits
                    if isinstance(item, dict) and isinstance(item.get("element_id"), str)
                } if isinstance(top_cell_edits, list) else set()
                if isinstance(proposal.get("clarifications"), list):
                    proposal["clarifications"] = [
                        item for item in proposal["clarifications"]
                        if not isinstance(item, dict) or item.get("element_id") not in cell_targets
                    ]
                if isinstance(proposal.get("skipped_targets"), list):
                    proposal["skipped_targets"] = [
                        item for item in proposal["skipped_targets"]
                        if item not in cell_targets
                    ]
                if isinstance(proposal.get("clear_targets"), list):
                    proposal["clear_targets"] = [item for item in proposal["clear_targets"] if item not in cell_targets]
            for key, operation_list in (
                ("clear_columns", clear_columns),
                ("format_patches", format_patches),
                ("cell_edits", top_cell_edits),
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
            "extra_authorized_fields", "extra_authorized_collection_fields",
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
        incoming_cell_edits = [
            dict(item) for item in rules.get("cell_edits", []) if isinstance(item, dict)
        ]
        try:
            previous_rules = json.loads(session.mapping_rules_json or "{}")
            changed_repeat_columns = set()
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
                changed_repeat_columns = _changed_repeat_columns(
                    groups, previous_rules, effective_repeat_rows
                )
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
        compiled_mapping_limit = ParseLimits().max_mappings
        if repeat_rows is not None:
            if document_format != "xlsx":
                return {
                    "status": "unsupported",
                    "errors": ["repeat_rows_requires_xlsx"],
                    "details": "The current M1 repeated-row adapter operates on XLSX worksheets.",
                }
            try:
                repeat_context = _repeat_mapping_context(self.env, session, effective_repeat_rows)
            except AccessError as exc:
                return {
                    "status": "blocked",
                    "error_code": "repeat_rows_access_denied",
                    "operation_executed": False,
                    "message": str(exc),
                }
            except (UserError, ValidationError, OfficeCoreError) as exc:
                return {
                    "status": "error",
                    "operation_status": "invalid",
                    "error_code": "repeat_rows_not_renderable",
                    "operation_executed": False,
                    "message": str(exc),
                }
            # The 200-item parser limit still applies to model-authored input.
            # Repeat-row mappings are generated server-side from the already
            # bounded record count and column list, so give that compiled list
            # a separate limit derived from its exact size and the XLSX cell
            # resource budget instead of truncating/rejecting valid tables.
            from odoo.addons.office_engine_odoo.models.office_document_request import _resource_budget

            compiled_repeat_targets = (
                len(repeat_context["group"]["target_rows"])
                * len(repeat_context["columns"])
            )
            compiled_mapping_limit = min(
                ParseLimits().max_mappings + compiled_repeat_targets,
                _resource_budget().max_cells,
            )
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
                source_names = (
                    [shifted.get("source_field", "")]
                    + shifted.get("source_fields", [])
                    + shifted.get("concat_fields", [])
                )
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
                    elif "concat_fields" in column:
                        mapping["concat_fields"] = [
                            f"{group_id}::{name}" for name in column["concat_fields"]
                        ]
                        mapping["separator"] = column["separator"]
                    else:
                        mapping["source_field"] = f"{group_id}::{column['source_field']}"
                    if "transform" in column:
                        mapping["transform"] = column["transform"]
                    repeated_mappings.append(mapping)
            if len(rules["mappings"]) + len(repeated_mappings) > compiled_mapping_limit:
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
        # A legacy template's ``required`` flag is descriptive metadata, not
        # an instruction from the user. An omitted target is a no-op: never
        # synthesize a clear or discard a clarification/skip on the user's
        # behalf. Explicit clear operations are handled below and enter the
        # normal risk-confirmation gate before any file is changed.
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
        except AccessError as exc:
            return {
                "status": "blocked",
                "error_code": "repeat_rows_access_denied",
                "operation_executed": False,
                "message": str(exc),
            }
        except (UserError, ValidationError) as exc:
            return {"status": "invalid", "errors": ["repeat_rows_not_authorized"], "details": str(exc)}

        # Resolve stable record-relative edits only after the current repeat
        # layout and its final ordering are known. If the model sent a fixed
        # coordinate that falls inside that layout, bind it to the record that
        # currently occupies the target row. Keep that stable selector in the
        # persisted Proposal; coordinates remain compilation metadata only.
        try:
            if rules.get("cell_edits"):
                rules["cell_edits"] = _bind_repeat_row_coordinate_cell_edits(
                    self.env, session, rules["cell_edits"], groups
                )
            else:
                # Empty operation arrays are no-ops; do not make them a
                # synthetic Proposal revision or change restored history.
                rules.pop("cell_edits", None)
            incoming_cell_edits = _bind_repeat_row_coordinate_cell_edits(
                self.env, session, incoming_cell_edits, groups
            )
            if repeat_context and changed_repeat_columns:
                # A new, explicitly changed repeat-column mapping is a later
                # batch edit for that column. Remove only older per-record
                # overrides in those columns before applying this turn's
                # explicit cell edits (which remain the last-write layer).
                rules["cell_edits"] = _drop_superseded_repeat_cell_edits(
                    rules.get("cell_edits", []),
                    repeat_context["group"]["group_id"],
                    changed_repeat_columns,
                )
            if incoming_cell_edits:
                # The first patch merge happens before repeat-row coordinates
                # can be resolved to stable record targets. Once both lists
                # are bound, apply normal patch precedence again: a new edit
                # for the same record/column replaces its persisted version,
                # while edits to every other record or column remain intact.
                rules["cell_edits"] = _merge_bound_cell_edit_patch(
                    rules.get("cell_edits", []), incoming_cell_edits
                )
            resolved_cell_edits = _resolve_record_target_cell_edits(
                self.env, session, rules.get("cell_edits", []), groups
            )
            incoming_cell_edits = _resolve_record_target_cell_edits(
                self.env, session, incoming_cell_edits, groups
            )
        except AccessError as exc:
            return {
                "status": "blocked",
                "error_code": "record_cell_edit_access_denied",
                "operation_executed": False,
                "message": str(exc),
            }
        except ValidationError as exc:
            return {
                "status": "invalid",
                "errors": ["invalid_record_cell_edit_target"],
                "details": str(exc),
                "operation_executed": False,
            }
        validation_rules = dict(rules)
        validation_rules["cell_edits"] = [
            {
                "element_id": item["element_id"],
                "value": item["value"],
                "value_type": item["value_type"],
            }
            for item in resolved_cell_edits
        ]
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
            for source in [mapping.get("source_field"), *(mapping.get("source_fields") or []), *(mapping.get("concat_fields") or [])]
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
            validation_rules,
            manifest,
            mapping_fields,
            limits=ParseLimits(max_mappings=compiled_mapping_limit),
            ordered_cell_edit_overrides=True,
        )
        if report.status == "invalid":
            repeat_guidance = (
                _repeat_rows_required_result(report, stored, manifest)
                if repeat_rows is None
                else None
            )
            if repeat_guidance:
                return repeat_guidance
            return {"status": "invalid", "errors": report.to_dict()}
        if not report.ready_for_review:
            repeat_guidance = (
                _repeat_rows_required_result(report, stored, manifest)
                if repeat_rows is None
                else None
            )
            if repeat_guidance:
                return repeat_guidance
            return {"status": "incomplete", "errors": report.to_dict()}

        confirmation_edits = list(incoming_cell_edits)
        confirmation_edits.extend(
            {
                "element_id": target_id,
                "value": "",
                "value_type": "string",
                "operation": "clear",
            }
            for target_id in rules.get("clear_targets", [])
        )
        operation_payload = {
            "proposal": rules,
            "mapping_groups": groups,
            "repeat_rows": effective_repeat_rows if repeat_rows is not None else [],
            "clear_columns": clear_columns or [],
            "format_patches": format_patches or [],
            "cell_edits": incoming_cell_edits,
        }
        repeat_expansion_risk = _repeat_row_expansion_confirmation_risk(repeat_context)
        resolved_record_edit_scope = [
            {
                "record_target": item["record_target"],
                "element_id": item["element_id"],
            }
            for item in incoming_cell_edits
            if isinstance(item, dict) and isinstance(item.get("record_target"), dict)
        ]
        derived_confirmation_scope = {}
        if repeat_expansion_risk:
            derived_confirmation_scope["repeat_row_expansion"] = repeat_expansion_risk["operation_scope"]
        if resolved_record_edit_scope:
            derived_confirmation_scope["record_cell_edits"] = resolved_record_edit_scope
        confirmation_result = self._cell_override_confirmation_gate(
            thread,
            session,
            confirmation_edits,
            manifest,
            expected_revision,
            force_override,
            operation_payload,
            additional_risks=[repeat_expansion_risk] if repeat_expansion_risk else None,
            derived_scope=derived_confirmation_scope or None,
        )
        confirmation_authorized = confirmation_result is _CONFIRMATION_AUTHORIZED
        if confirmation_result and not confirmation_authorized:
            return confirmation_result

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
            if confirmation_authorized and session.pending_cell_override_json:
                session._clear_pending_cell_override_from_service(expected_revision)
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
                    extra_authorized_collection_fields=stored.get(
                        "extra_authorized_collection_fields", {}
                    ),
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
            if confirmation_authorized and session.pending_cell_override_json:
                session.invalidate_recordset(["revision"])
                session._clear_pending_cell_override_from_service(session.revision)
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
            thread, _tool_message = self._office_tool_context()
            session = _owned_session(self.env, session_id)
            if session.thread_id != thread or session.owner_id.id != self.env.uid:
                raise AccessError(_("The mapping Session is unavailable."))
            confirmation_proof = None
            if session.state != "completed":
                latest_user = _latest_office_user_message(self.env, thread)
                confirmation_proof = build_finalize_confirmation_proof(
                    self.env,
                    thread,
                    session,
                    latest_user,
                    expected_revision,
                    proposal_revision,
                )
            return finalize_confirmed_mapping_in_isolated_transaction(
                self.env,
                thread.id,
                session_id,
                expected_revision,
                proposal_revision,
                confirmation_proof=confirmation_proof,
            )
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

    def _office_finalize(
        self,
        session_id,
        expected_revision,
        proposal_revision,
        *,
        expected_thread_id=None,
        confirmation_proof=None,
    ):
        """Finalize only after an exact user confirmation for the current Proposal revision."""
        if expected_thread_id is None:
            thread, _tool_message = self._office_tool_context()
        else:
            thread = self.env["llm.thread"].browse(expected_thread_id).exists()
            if not thread:
                raise AccessError(_("The Office chat context is unavailable."))
            thread.check_access("read")
            if thread.user_id.id != self.env.uid:
                raise AccessError(_("The Office chat context is unavailable."))
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
            if confirmation_proof is not None:
                validate_finalize_confirmation_proof(
                    self.env,
                    confirmation_proof,
                    thread,
                    session,
                    expected_revision,
                    proposal_revision,
                )
            else:
                latest_user = _latest_office_user_message(self.env, thread)
                if not _is_explicit_finalize_confirmation(latest_user.body):
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

    def execute(self, parameters):
        """Normalize the observed single-object repeat_rows call shape.

        The public contract remains an array containing at most one repeat-row
        group. Some Provider responses send that single group as an object;
        normalize only that shape at the tool boundary, before llm_tool's
        signature validation. The Office tool still performs the same
        authorization, row-count confirmation, and execution checks.
        """
        self.ensure_one()
        if self.name == "office_save_mapping_preview" and isinstance(parameters, dict):
            repeat_rows = parameters.get("repeat_rows")
            if isinstance(repeat_rows, dict):
                parameters = dict(parameters)
                parameters["repeat_rows"] = [repeat_rows]
        return super().execute(parameters)

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
