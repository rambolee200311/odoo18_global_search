"""Revision-bound preview and final rendering through the M1 Office engine."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import uuid
from datetime import date, datetime

from odoo import _, api, fields
from odoo.exceptions import AccessError, UserError, ValidationError
from office_mapping_verify import ParseLimits, validate_proposal
from office_mapping_verify import apply_transform

from office_core import (
    OfficeCoreError,
    expand_repeat_rows,
    inspect_document,
    render_candidate,
)
from odoo.addons.office_engine_odoo.models.office_document_request import (
    _resource_budget,
)

from .ai_orchestrator import (
    _approved_collection_field_types,
    _approved_field_types,
    _mapping_field_types,
    _retrieve_collection,
    _retrieve_record,
    _resolve_record_target_cell_edits,
)

_logger = logging.getLogger(__name__)
from .mapping_service import _load_mapping_data, _owned_session


_REQUEST_NAMESPACE = uuid.UUID("89337b62-c77e-4c8f-a12a-24f353f2cb51")
_MIME = {
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def _m1_value(value, value_type):
    if value is None:
        if value_type == "string":
            return ""
        raise ValidationError(_("The current record contains an unsupported null value."))
    if value_type == "string":
        if value is False:
            return ""
        if isinstance(value, (str, int, float)) and not isinstance(value, bool):
            return str(value)
        raise ValidationError(_("The current record value cannot be safely mapped to text."))
    if value_type == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValidationError(_("The current record value is not a number."))
        # Odoo Float fields may carry binary tails (for example
        # 8.300000000000001). Normalize to a stable decimal before passing the
        # value through JSON and OOXML's numeric serializer/read-back check.
        return round(value, 12) if isinstance(value, float) else value
    if value_type == "boolean":
        if type(value) is not bool:
            raise ValidationError(_("The current record value is not a boolean."))
        return value
    if value_type == "date":
        if isinstance(value, datetime):
            raise ValidationError(_("The current record value is a datetime, not a date."))
        try:
            return (value if isinstance(value, date) else date.fromisoformat(value)).isoformat()
        except (TypeError, ValueError) as error:
            raise ValidationError(_("The current record value is not an ISO date.")) from error
    if value_type == "datetime":
        try:
            parsed = value if isinstance(value, datetime) else datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (TypeError, ValueError) as error:
            raise ValidationError(_("The current record value is not an ISO datetime.")) from error
        if parsed.utcoffset() is not None:
            raise ValidationError(_("Timezone-aware datetimes cannot be written to XLSX without conversion."))
        return parsed.isoformat()
    raise ValidationError(_("The mapping value type is not supported."))


def _first_nonempty_mapping_value(values):
    """Select the first meaningful scalar without treating numeric zero as empty."""
    return next(
        (value for value in values if value is not None and value is not False and value != ""),
        None,
    )


def _concatenate_text_values(values, separator):
    """Join authorized text values while treating Odoo's empty Char False as blank."""
    if not isinstance(separator, str) or len(separator) > 32 or any(ord(char) < 32 for char in separator):
        raise ValidationError(_("The mapping separator is invalid."))
    parts = []
    for value in values:
        # Odoo commonly represents an unset Char/Text value as False. Keep this
        # identity check precise: numeric 0 and boolean False are otherwise
        # easy to conflate in Python, while only the ORM's False sentinel is
        # meaningful as an empty string for this already-authorized text field.
        if value is None or value is False or value == "":
            continue
        if not isinstance(value, str):
            raise ValidationError(_("Concatenation sources must contain text values."))
        parts.append(value)
    return separator.join(parts)


def _stable_request_uuid(env, session, attempt_revision=None):
    """Bind one idempotency key to a Session revision's finalize attempt."""
    if attempt_revision is None:
        if session.state == "completed":
            attempt_revision = session.revision - 3
        elif session.state in {"confirmed", "generating"}:
            attempt_revision = session.revision - 1
        else:
            attempt_revision = session.revision
    value = (
        f"{env.cr.dbname}:office-m2:{session.id}:proposal-revision:"
        f"{session.confirmed_revision}:attempt-revision:{attempt_revision}"
    )
    return str(uuid.uuid5(_REQUEST_NAMESPACE, value))


def _render_result_url(attachment_id):
    return f"/web/content/{int(attachment_id)}?download=true"


def finalize_confirmed_mapping_in_isolated_transaction(
    env,
    thread_id,
    session_id,
    expected_revision,
    proposal_revision,
    *,
    confirmation_proof=None,
):
    """Run the confirmed M1 handoff outside the LLM tool wrapper savepoint.

    The legacy renderer commits its request/output from an independent cursor.
    Its caller must therefore have a root transaction that can checkpoint the
    authorized ``generating`` Session state, observe the generated request,
    register V1, and commit completion. LLM tool execution itself is wrapped
    in a savepoint; committing that cursor would invalidate the savepoint.
    This helper uses a fresh cursor and rechecks ownership, Thread, revision,
    and the latest user confirmation before any rendering side effect.
    """
    context = dict(env.context)
    # The current tool-call message is owned by the outer streaming
    # transaction. It is not needed for final authorization and must not be
    # carried as a cross-cursor recordset.
    context.pop("message", None)
    with env.registry.cursor() as cursor:
        isolated_env = api.Environment(cursor, env.uid, context)
        result = isolated_env["office.mapping.tool"]._office_finalize(
            session_id,
            expected_revision,
            proposal_revision,
            expected_thread_id=thread_id,
            confirmation_proof=confirmation_proof,
        )
        # Structured failures may contain a legitimate retryable Session
        # transition, so commit the result atomically with its state.
        cursor.commit()
        return result


def _register_initial_workbook_version(env, session, request_uuid):
    """Best-effort V1 registration without changing the established M1 result contract."""
    from .workbook_version_service import record_finalize_reference, register_initial_v1

    request = env["office.document.request"].search(
        [
            ("request_uuid", "=", request_uuid),
            ("owner_id", "=", env.uid),
            ("thread_id", "=", session.thread_id.id),
            ("input_message_id", "=", session.source_message_id.id),
            ("source_attachment_id", "=", session.source_attachment_id.id),
            ("state", "=", "generated"),
            ("output_attachment_id", "!=", False),
        ],
        limit=1,
    )
    if not request:
        _logger.warning(
            "M1 output could not be registered as V1; session_id=%s reason=request_unavailable",
            session.id,
        )
        return {"version": False, "state": "legacy", "error_code": "m1_version_registration_unavailable"}
    try:
        with env.cr.savepoint():
            version = register_initial_v1(env, session.id, request.id)
            delivery_message_id = env["office.document.request"]._ensure_output_delivery_message(request.id)
            if not delivery_message_id:
                raise ValidationError(_("The generated workbook has no verified Thread delivery message."))
            record_finalize_reference(
                env,
                version.id,
                request.output_attachment_id.id,
                delivery_message_id,
            )
        return {"version": version, "state": version.state, "error_code": False}
    except Exception:
        # M1 has already committed its verified, private output. Preserve its
        # historical return behavior, while making the missing V1 explicit.
        _logger.exception(
            "M1 output remains outside workbook version lineage; session_id=%s request_uuid=%s",
            session.id,
            request_uuid,
        )
        return {"version": False, "state": "legacy", "error_code": "m1_version_registration_unavailable"}


def _compile_plan(env, session):
    """Compile the deterministic template -> map/sort -> edit pipeline.

    Template inspection and authorization happen first. Collection retrieval
    establishes final sort order before repeat mappings are projected to row
    coordinates. Explicit user edits are resolved/applied after those mapped
    writes; only then does office_core validate and generate a candidate.
    """
    session.thread_id.check_access("read")
    session.source_message_id.check_access("read")
    session.source_attachment_id.check_access("read")
    if session.thread_id.user_id.id != env.uid:
        raise AccessError(_("The mapping session is unavailable."))
    if (
        session.source_message_id.model != "llm.thread"
        or session.source_message_id.res_id != session.thread_id.id
        or session.source_attachment_id not in session.source_message_id.attachment_ids
    ):
        raise AccessError(_("The mapping session is unavailable."))

    rules, manifest, configured_fields, groups = _load_mapping_data(session)
    target, current_fields = _approved_field_types(env, session, configured_fields)
    group_fields, group_values, element_slots = {}, {}, {}
    for group in groups:
        if "relation_model" not in group:
            continue
        permitted = _approved_collection_field_types(env, session, group)
        records = _retrieve_collection(env, session, group, permitted)
        group_fields[group["group_id"]] = permitted
        group_values[group["group_id"]] = records
        for row in group["target_rows"]:
            for item in row["targets"]:
                element_slots[item["element_id"]] = (group["group_id"], row["row_index"])

    mapping_fields = _mapping_field_types(current_fields, groups, group_fields)
    document_context = json.loads(session.context_json or "{}")
    if document_context.get("document_format") == "docx":
        # The DOCX adapter replaces complete text paragraphs. Keep source
        # authorization in current_fields, but validate its rendered values as
        # strings because numeric and boolean scalars are serialized to text.
        mapping_fields = {name: "string" for name in mapping_fields}
    compiled_repeat_mappings = sum(
        len(row.get("targets", []))
        for group in groups
        if isinstance(group, dict) and isinstance(group.get("target_rows"), list)
        for row in group["target_rows"]
        if isinstance(row, dict) and isinstance(row.get("targets"), list)
    )
    compiled_mapping_limit = min(
        ParseLimits().max_mappings + compiled_repeat_mappings,
        _resource_budget().max_cells,
    )
    resolved_cell_edits = _resolve_record_target_cell_edits(
        env, session, rules.get("cell_edits", []), groups, group_values_by_id=group_values
    )
    validation_rules = dict(rules)
    validation_rules["cell_edits"] = [
        {
            "element_id": item["element_id"],
            "value": item["value"],
            "value_type": item["value_type"],
        }
        for item in resolved_cell_edits
    ]
    report = validate_proposal(
        validation_rules,
        manifest,
        mapping_fields,
        limits=ParseLimits(max_mappings=compiled_mapping_limit),
        ordered_cell_edit_overrides=True,
    )
    if not report.ready_for_review:
        raise ValidationError(_("The current mapping is incomplete or no longer authorized."))
    mapped_root_fields = sorted(
        {
            field_name
            for item in rules.get("mappings", [])
            if isinstance(item, dict)
            for field_name in (
                [item["source_field"]]
                if isinstance(item.get("source_field"), str)
                else item.get("source_fields") or item.get("concat_fields", [])
            )
            if isinstance(field_name, str) and "::" not in field_name
        }
    )
    if not set(mapped_root_fields).issubset(current_fields):
        raise AccessError(_("A mapped field is no longer available."))
    values = _retrieve_record(env, session, mapped_root_fields) if mapped_root_fields else {}
    summary = env["office.document.request"]._inspect_chat_attachment(
        session.source_attachment_id, session.thread_id, session.source_message_id
    )
    if session.template_fingerprint and summary["template_sha256"] != session.template_fingerprint:
        raise UserError(_("The template changed. Rebuild the mapping from the current file before continuing."))

    render_source = session.source_attachment_id.raw or b""
    repeat_rows_instruction = None
    authorized_blank_targets = []
    explicit_clear_edits = []
    repeating_group = next(
        (group for group in groups if group.get("target_rows") and group.get("row_count")),
        None,
    )
    if repeating_group:
        first_target = repeating_group["target_rows"][0]["targets"][0]["element_id"]
        match = re.fullmatch(r"xlsx:(.+)!([A-Z]{1,3})([1-9][0-9]*)", first_target)
        if not match:
            raise ValidationError(_("The repeating-row target layout is invalid."))
        sheet_name, first_row = match.group(1), int(match.group(3))
        source_inspection = inspect_document(
            render_source,
            session.source_attachment_id.name or "template.xlsx",
            session.source_attachment_id.mimetype or "application/octet-stream",
            _resource_budget(),
        )
        source_ids = {item.element_id for item in source_inspection.elements}
        requested_ids = {
            target["element_id"]
            for row in repeating_group["target_rows"]
            for target in row["targets"]
        }
        missing_ids = requested_ids - source_ids
        columns = {}
        for target in repeating_group["target_rows"][0]["targets"]:
            coordinate = target["element_id"].rsplit("!", 1)[-1]
            match = re.fullmatch(r"([A-Z]{1,3})[1-9][0-9]*", coordinate)
            if match:
                columns[match.group(1)] = target.get("column_id") or match.group(1)
        repeat_rows_instruction = {
            "action": "insert_repeat_rows",
            "sheet": sheet_name,
            "start_row": first_row,
            "record_count": repeating_group["row_count"],
            "columns": columns,
        }
        try:
            expansion = expand_repeat_rows(
                render_source,
                repeat_rows_instruction,
                _resource_budget(),
            )
        except OfficeCoreError:
            if missing_ids or repeating_group["row_count"] > len(repeating_group["target_rows"]):
                raise
        else:
            render_source = expansion.content
        if missing_ids and render_source == (session.source_attachment_id.raw or b""):
            raise ValidationError(_("The repeating-row target layout is missing cells."))
        normalized_inspection = inspect_document(
            render_source,
            session.source_attachment_id.name or "template.xlsx",
            session.source_attachment_id.mimetype or "application/octet-stream",
            _resource_budget(),
        )
        if normalized_inspection.format != "xlsx" or not requested_ids.issubset(
            {item.element_id for item in normalized_inspection.elements}
        ):
            raise UserError(_("The expanded spreadsheet did not pass M1 inspection."))
        repeated_row_numbers = {
            int(match.group(1))
            for row in repeating_group["target_rows"]
            for target_spec in row["targets"]
            if (match := re.fullmatch(
                rf"xlsx:{re.escape(sheet_name)}![A-Z]{{1,3}}([1-9][0-9]*)",
                target_spec["element_id"],
            ))
        }
        # The verifier may accept a target absent from the expanded source
        # only when M2 derived it from an explicit clear in this exact,
        # server-bound repeat-row band. It remains a no-content write and is
        # independently checked against the output package.
        manifest_ids = {item["element_id"] for item in manifest}
        for element_id in rules.get("clear_targets", []):
            match = re.fullmatch(
                rf"xlsx:{re.escape(sheet_name)}![A-Z]{{1,3}}([1-9][0-9]*)",
                element_id,
            )
            if (
                match
                and int(match.group(1)) in repeated_row_numbers
                and element_id in manifest_ids
            ):
                authorized_blank_targets.append(element_id)
        render_template_sha256 = normalized_inspection.template_sha256
    else:
        render_template_sha256 = summary["template_sha256"]

    writes, snapshot = [], {}
    manifest_ids = {spec["element_id"] for spec in manifest}
    manifest_by_id = {spec["element_id"]: spec for spec in manifest}
    for item in rules["mappings"]:
        if item["element_id"] not in manifest_ids:
            raise ValidationError(_("A mapping target is no longer available."))
        if "formula" in item:
            writes.append(
                {
                    "element_id": item["element_id"],
                    "operation": "set_formula",
                    "value": {"type": "formula", "data": item["formula"]},
                }
            )
            continue

        if "literal_value" in item:
            writes.append(
                {
                    "element_id": item["element_id"],
                    "operation": "set_value",
                    "value": {
                        "type": item["value_type"],
                        "data": _m1_value(item["literal_value"], item["value_type"]),
                    },
                }
            )
            continue

        is_concatenation = isinstance(item.get("concat_fields"), list)
        field_names = item.get("concat_fields") if is_concatenation else item.get("source_fields") or [item.get("source_field")]
        if not field_names or any(not isinstance(name, str) for name in field_names):
            raise ValidationError(_("The mapping source is invalid."))
        raw_values = []
        for field_name in field_names:
            if field_name in current_fields:
                raw_value = values[field_name]
                snapshot[field_name] = raw_value
            else:
                if "::" not in field_name:
                    raise AccessError(_("A mapped field is no longer available."))
                group_id, relation_field = field_name.split("::", 1)
                slot = element_slots.get(item["element_id"])
                if not slot or slot[0] != group_id or relation_field not in group_fields.get(group_id, {}):
                    raise AccessError(_("A mapped collection field is no longer available."))
                row_index = slot[1]
                rows = group_values.get(group_id, [])
                if row_index >= len(rows):
                    raise ValidationError(_("The authorized collection no longer matches the mapping rows."))
                source_row = rows[row_index]
                raw_value = source_row.get(relation_field)
                snapshot[f"{group_id}:{row_index}:source_record_id"] = source_row.get("id")
                snapshot[f"{group_id}:{row_index}:{relation_field}"] = raw_value
            raw_values.append(raw_value)

        if is_concatenation:
            if item.get("value_type") != "string":
                raise ValidationError(_("Concatenation sources must contain text values."))
            separator = item.get("separator", "")
            raw_value = _concatenate_text_values(raw_values, separator)
        else:
            raw_value = _first_nonempty_mapping_value(raw_values)
        if item.get("transform") is not None:
            try:
                raw_value = apply_transform(raw_value, item["transform"], item["value_type"])
            except (TypeError, ValueError) as error:
                raise ValidationError(
                    _("The mapped date value cannot be transformed using the requested offset.")
                ) from error
        if raw_value is None and item["value_type"] == "string":
            raw_value = ""
        writes.append(
            {
                "element_id": item["element_id"],
                "operation": "set_value",
                "value": {"type": item["value_type"], "data": _m1_value(raw_value, item["value_type"])},
            }
        )
    # A clear is an explicit, user-directed blank write. Unmentioned targets
    # (including formula cells) are absent from this list and stay unchanged.
    for element_id in rules.get("clear_targets", []):
        if element_id not in manifest_ids:
            raise ValidationError(_("A clear target is no longer available."))
        if manifest_by_id[element_id].get("writable") is not True:
            # Explicit clears of protected-but-inspected cells (for example a
            # table heading) travel through the same coordinate-write path as
            # cell_edits. The caller has already obtained any required user
            # confirmation; core still validates that the target is a real
            # inspected cell in this document.
            explicit_clear_edits.append(
                {"element_id": element_id, "value": "", "value_type": "string"}
            )
            continue
        writes.append(
            {
                "element_id": element_id,
                "operation": "set_value",
                "value": {"type": "string", "data": ""},
            }
        )
    for patch in rules.get("format_patches", []):
        element_id = patch.get("element_id")
        if element_id not in manifest_ids:
            raise ValidationError(_("A number-format target is no longer available."))
        writes.append(
            {
                "element_id": element_id,
                "operation": "set_number_format",
                "value": {"type": "number_format", "data": patch["number_format"]},
            }
        )
    plan = {"schema_version": "1", "template_sha256": render_template_sha256, "writes": writes}
    snapshot_json = json.dumps(
        {"template_sha256": summary["template_sha256"], "values": snapshot},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    summary["render_source"] = render_source
    summary["authorized_blank_targets"] = tuple(authorized_blank_targets)
    # Explicit coordinate writes remain separate from source-field mappings.
    # office_core re-inspects the XLSX and compiles them into canonical
    # Document Operation set_value operations.
    summary["explicit_cell_edits"] = [
        *[
            {
                "element_id": item["element_id"],
                "value": item["value"],
                "value_type": item["value_type"],
            }
            for item in resolved_cell_edits
        ],
        *explicit_clear_edits,
    ]
    if repeat_rows_instruction is not None:
        # Preview and finalization must compile from the same authorized,
        # deterministic row-expansion instruction. The original upload stays
        # the M1 request's authenticated source attachment.
        summary["preprocessing"] = repeat_rows_instruction
    return plan, hashlib.sha256(snapshot_json.encode("utf-8")).hexdigest(), summary


def render_preview(env, session_id, expected_revision):
    """Create a private, verified preview; only a short optimistic-lock write follows rendering."""
    session = _owned_session(env, session_id)
    if type(expected_revision) is not int or session.revision != expected_revision:
        raise ValidationError(_("MAPPING_REVISION_STALE: reload the current proposal."))
    if session.state not in {"revision_pending", "preview_ready", "confirmation_required"}:
        raise ValidationError(_("The current session is not ready for preview rendering."))
    attachment = session.source_attachment_id
    attachment.check_access("read")
    source = attachment.raw or b""
    if not source or attachment.file_size > 32 * 1024 * 1024:
        raise UserError(_("The template is empty or exceeds the preview size limit."))

    plan, data_fingerprint, summary = _compile_plan(env, session)
    preprocessing = summary.get("preprocessing")
    filename = attachment.name or "document.xlsx"
    mimetype = attachment.mimetype or _MIME[summary["format"]]
    candidate = render_candidate(
        source,
        filename,
        mimetype,
        plan,
        _resource_budget(),
        preprocessing=preprocessing,
        authorized_blank_targets=tuple(summary.get("authorized_blank_targets", ())),
        explicit_cell_edits=summary.get("explicit_cell_edits", []),
    )
    verification = candidate.verification
    if not isinstance(verification, dict):
        raise UserError(_("The document engine did not return a mandatory read-back result."))
    verification_status = verification.get("status")
    verification_sha = verification.get("output_sha256")
    if verification_status != "PASS" or verification_sha != candidate.candidate_sha256:
        raise UserError(_("The preview did not pass the M1 read-back check."))

    root = filename.rsplit(".", 1)[0]
    ext = summary["format"]
    record_name = "record"
    if session.target_model in env.registry.models and session.target_record_id:
        target = env[session.target_model].browse(session.target_record_id).exists()
        if target:
            target.check_access("read")
            record_name = target.display_name or record_name
    safe_record_name = re.sub(r"[^A-Za-z0-9_-]+", "_", record_name).strip("_")[:48]
    preview = env["ir.attachment"].create(
        {
            "name": f"preview_{safe_record_name or 'record'}_{root}.{ext}",
            "type": "binary",
            "mimetype": _MIME[ext],
            "raw": candidate.content,
            "res_model": session._name,
            "res_id": session.id,
            "company_id": session.company_id.id,
            "public": False,
        }
    )
    stored_bytes = preview.raw or b""
    if (
        not stored_bytes
        or len(stored_bytes) != len(candidate.content)
        or hashlib.sha256(stored_bytes).hexdigest() != candidate.candidate_sha256
    ):
        preview.unlink()
        raise UserError(_("The preview attachment did not preserve the verified file bytes."))
    try:
        stored = session._store_preview_from_service(
            preview,
            expected_revision,
            data_fingerprint,
            summary["template_sha256"],
        )
        session.invalidate_recordset(["revision", "state"])
        confirmed_step = session._require_confirmation_from_service(stored["revision"])
    except Exception:
        preview.unlink()
        raise
    return {
        **stored,
        "state": "confirmation_required",
        "revision": confirmed_step["revision"],
        "preview_attachment_id": preview.id,
        "proposal_revision": session.proposal_revision,
        "data_fingerprint": data_fingerprint,
    }


def _post_preview_message(session, body):
    preview = session.preview_attachment_id
    if not preview:
        raise UserError(_("The verified preview is unavailable."))
    preview.check_access("read")
    return session.thread_id.message_post(
        body=body,
        llm_role="assistant",
        author_id=False,
        attachment_ids=[preview.id],
    )


def _rebuild_proposal(env, session, *, template_changed):
    """Refresh preview data without changing the validated Proposal."""
    if template_changed:
        raise UserError(_("The source template changed. Upload it again to start a new mapping Session."))
    refreshed = render_preview(env, session.id, session.revision)
    session.invalidate_recordset(["revision", "state", "preview_attachment_id"])
    message = _post_preview_message(session, _("源数据已变化，已按当前映射更新预览；请检查后再次确认。"))
    return {**refreshed, "message_id": message.id}


def render_confirmed_mapping(env, session_id, expected_revision):
    """Reauthorize, require an unchanged preview snapshot, then create the archived M1 output."""
    session = _owned_session(env, session_id)
    if (
        session.state == "completed"
        and session.confirmed_revision == session.proposal_revision
        and session.preview_proposal_revision == session.proposal_revision
    ):
        # Prefer the request identity persisted with the completed Session. The
        # deterministic key is retained for completed Sessions created before
        # this field existed.
        final_request_uuid = session.final_request_uuid
        if not final_request_uuid:
            completed_attempt_revision = session.revision - 3
            final_request_uuid = _stable_request_uuid(
                env, session, completed_attempt_revision
            )
        request = env["office.document.request"].search(
            [
                ("request_uuid", "=", final_request_uuid),
                ("owner_id", "=", env.uid),
                ("thread_id", "=", session.thread_id.id),
                ("input_message_id", "=", session.source_message_id.id),
                ("source_attachment_id", "=", session.source_attachment_id.id),
                ("state", "=", "generated"),
                ("output_attachment_id", "!=", False),
            ],
            limit=1,
        )
        if request and request.output_attachment_id:
            output = request.output_attachment_id
            output.check_access("read")
            version_result = _register_initial_workbook_version(env, session, final_request_uuid)
            delivery_message_id = env["office.document.request"]._ensure_output_delivery_message(
                request.id
            )
            return {
                "session_id": session.id,
                "state": "completed",
                "revision": session.revision,
                "output_attachment_id": output.id,
                "download_url": _render_result_url(output.id),
                "request_uuid": request.request_uuid,
                "filename": output.name or False,
                "mimetype": output.mimetype or False,
                "delivery_message_id": delivery_message_id or False,
                "workbook_version_id": version_result["version"].id if version_result["version"] else False,
                "workbook_version_state": version_result["state"],
                "workbook_version_error_code": version_result["error_code"],
            }
    if session.revision != expected_revision or session.state != "confirmation_required":
        raise ValidationError(_("MAPPING_REVISION_STALE: refresh the current preview and confirm again."))
    if (
        not session.preview_attachment_id
        or session.preview_proposal_revision != session.proposal_revision
    ):
        raise ValidationError(_("The preview no longer matches the current proposal."))

    try:
        plan, data_fingerprint, summary = _compile_plan(env, session)
    except UserError as exc:
        if "template changed" not in str(exc).lower():
            raise
        plan = data_fingerprint = summary = None
    template_changed = bool(
        summary and summary["template_sha256"] != session.template_fingerprint
    )
    if template_changed or not summary:
        rebuilt = _rebuild_proposal(env, session, template_changed=True)
        session.invalidate_recordset(["revision", "state", "preview_attachment_id"])
        return {
            "session_id": session.id,
            "state": rebuilt["state"],
            "revision": rebuilt["revision"],
            "requires_reconfirmation": True,
            "message_id": rebuilt["message_id"],
            "output_attachment_id": False,
        }
    if data_fingerprint != session.preview_data_fingerprint:
        rebuilt = _rebuild_proposal(env, session, template_changed=False)
        session.invalidate_recordset(["revision", "state", "preview_attachment_id"])
        return {
            "session_id": session.id,
            "state": rebuilt["state"],
            "revision": rebuilt["revision"],
            "requires_reconfirmation": True,
            "message_id": rebuilt["message_id"],
            "output_attachment_id": False,
        }

    confirmed = session._mark_confirmed_from_service(expected_revision)
    session.invalidate_recordset(["revision", "state", "confirmed_revision"])
    session._transition_from_service("generating", confirmed["revision"])
    session.invalidate_recordset(["revision", "state", "proposal_revision"])
    version_binding = {
        "session_id": session.id,
        "session_revision": session.revision,
        "proposal_revision": session.proposal_revision,
    }
    # The M1 request is executed and committed on independent cursors. Persist
    # the already authorized `generating` transition first so those cursors can
    # validate the exact Session binding, and so this caller's next transaction
    # can observe the generated request/output before registering V1. Without
    # this checkpoint PostgreSQL's repeatable-read snapshot cannot see the
    # child cursor's committed request row and V1 silently remains legacy.
    env.cr.commit()
    session.invalidate_recordset(["revision", "state", "proposal_revision"])
    request_uuid = session.final_request_uuid or _stable_request_uuid(
        env, session, expected_revision
    )
    try:
        result = env["office.document.request"]._render_request_sync(
            request_uuid,
            session.source_attachment_id.id,
            plan,
            session.thread_id.id,
            session.source_message_id.id,
            **(
                {"preprocessing": summary["preprocessing"]}
                if summary.get("preprocessing")
                else {}
            ),
            **(
                {"explicit_cell_edits": summary["explicit_cell_edits"]}
                if summary.get("explicit_cell_edits")
                else {}
            ),
            version_binding=version_binding,
        )
        session.invalidate_recordset(["revision", "state"])
        if result.get("state") != "generated" or not result.get("output_attachment_id"):
            retryable = session._recover_finalize_failure_from_service(
                session.revision, final_request_uuid=False
            )
            return {
                "session_id": session.id,
                "state": "failed",
                "session_state": retryable["state"],
                "revision": retryable["revision"],
                "error_code": result.get("error_code") or "office_render_failed",
                "failed_stage": result.get("failed_stage") or False,
                "message": result.get("message") or _("The final document was not generated. The verified preview remains available."),
                "output_attachment_id": False,
            }
        # _render_request_sync commits its generated request and output from a
        # second connection. Rebase this root transaction after that commit so
        # the request/attachment are visible under PostgreSQL REPEATABLE READ.
        # This function is called for production finalization through the
        # isolated root-cursor gate above; it must not run inside an LLM tool
        # wrapper savepoint.
        env.cr.commit()
        session.invalidate_recordset(["revision", "state", "proposal_revision"])
        result_request_uuid = result.get("request_uuid") or request_uuid
        version_result = _register_initial_workbook_version(env, session, result_request_uuid)
        if not result.get("delivery_message_id"):
            retryable = session._recover_finalize_failure_from_service(
                session.revision, final_request_uuid=result_request_uuid
            )
            return {
                "session_id": session.id,
                "state": "failed",
                "session_state": retryable["state"],
                "revision": retryable["revision"],
                "error_code": result.get("error_code") or "office_delivery_pending",
                "failed_stage": result.get("failed_stage") or "chat_delivery",
                "message": result.get("message")
                or _(
                    "The final file was generated, but its chat attachment could not be confirmed. The verified preview remains available; retry delivery."
                ),
                "artifact_state": "generated",
                "delivery_state": "pending",
                "request_uuid": result_request_uuid,
                "output_attachment_id": False,
                "delivery_message_id": False,
                "workbook_version_id": version_result["version"].id if version_result["version"] else False,
                "workbook_version_state": version_result["state"],
                "workbook_version_error_code": version_result["error_code"],
            }
        output_id = result["output_attachment_id"]
        completed = session._transition_from_service(
            "completed",
            session.revision,
            final_request_uuid=result_request_uuid,
        )
        return {
            "session_id": session.id,
            "state": "completed",
            "revision": completed["revision"],
            "output_attachment_id": output_id,
            "download_url": _render_result_url(output_id),
            "request_uuid": result_request_uuid,
            "filename": result.get("filename") or False,
            "mimetype": result.get("mimetype") or False,
            "delivery_message_id": result.get("delivery_message_id") or False,
            "workbook_version_id": version_result["version"].id if version_result["version"] else False,
            "workbook_version_state": version_result["state"],
            "workbook_version_error_code": version_result["error_code"],
        }
    except Exception as exc:
        _logger.exception("Final Office rendering failed for Session %s", session.id)
        session.invalidate_recordset(["revision", "state"])
        if session.state == "generating":
            retryable = session._recover_finalize_failure_from_service(session.revision)
            session.invalidate_recordset(["revision", "state"])
        else:
            retryable = {"state": session.state, "revision": session.revision}
        error_message = (
            str(exc)
            if isinstance(exc, (UserError, ValidationError))
            else _("The Office renderer failed. The verified preview is still available for another attempt.")
        )
        return {
            "session_id": session.id,
            "state": "failed",
            "session_state": retryable["state"],
            "revision": retryable["revision"],
            "error_code": "office_render_failed",
            "message": error_message,
            "output_attachment_id": False,
        }
