"""Current-user mapping compilation and idempotent M1 render bridge."""

from __future__ import annotations

import json
import uuid

from odoo import _
from odoo.exceptions import AccessError, UserError, ValidationError
from office_mapping_verify import validate_proposal

from .ai_orchestrator import (
    _approved_collection_field_types,
    _approved_field_types,
    _mapping_field_types,
    _retrieve_collection,
    _retrieve_record,
)
from .mapping_service import _load_mapping_data, _owned_session


_REQUEST_NAMESPACE = uuid.UUID("89337b62-c77e-4c8f-a12a-24f353f2cb51")


def _m1_value(value, value_type):
    if value is None:
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
        return value
    if value_type == "boolean":
        if type(value) is not bool:
            raise ValidationError(_("The current record value is not a boolean."))
        return value
    raise ValidationError(_("The mapping value type is not supported."))


def _stable_request_uuid(env, session):
    value = f"{env.cr.dbname}:office-m2:{session.id}:confirmed-revision:{session.confirmed_revision}"
    return str(uuid.uuid5(_REQUEST_NAMESPACE, value))


def _render_result_url(attachment_id):
    return f"/web/content/{int(attachment_id)}?download=true"


def render_confirmed_mapping(env, session_id, expected_revision):
    """Reauthorize, freshly retrieve values, then call only M1's safe service."""
    session = _owned_session(env, session_id)
    session.thread_id.check_access("read")
    session.source_message_id.check_access("read")
    session.source_attachment_id.check("read")
    if session.thread_id.user_id.id != env.uid:
        raise AccessError(_("The mapping session is unavailable."))
    if session.source_message_id.model != "llm.thread" or session.source_message_id.res_id != session.thread_id.id:
        raise AccessError(_("The mapping session is unavailable."))
    if type(expected_revision) is not int or expected_revision < 1:
        raise ValidationError(_("Invalid mapping session revision."))
    if session.state == "completed" and session.confirmed_revision == expected_revision:
        request_uuid = _stable_request_uuid(env, session)
        request = env["office.document.request"].search([("request_uuid", "=", request_uuid)], limit=1)
        if request and request.output_attachment_id:
            request.check_access("read")
            request.output_attachment_id.check("read")
            return {
                "session_id": session.id,
                "state": "completed",
                "revision": session.revision,
                "output_attachment_id": request.output_attachment_id.id,
                "download_url": _render_result_url(request.output_attachment_id.id),
            }
    if (
        session.state != "awaiting_confirmation"
        or session.revision != expected_revision
        or session.confirmed_revision != expected_revision
    ):
        raise ValidationError(_("MAPPING_REVISION_STALE: refresh and confirm the current mapping."))

    rules, manifest, configured_fields, groups = _load_mapping_data(session)
    target, current_fields = _approved_field_types(env, session, configured_fields)
    group_fields = {}
    group_values = {}
    element_slots = {}
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
    report = validate_proposal(rules, manifest, mapping_fields)
    if not report.ready_for_review:
        raise ValidationError(_("The confirmed mapping is no longer complete or authorized."))

    # Read fresh data at confirmation time through the existing Retriever under
    # this user's env. Neither the model's sample nor stored prompt data is used.
    values = _retrieve_record(env, session, current_fields)
    summary = env["office.document.request"]._inspect_chat_attachment(
        session.source_attachment_id,
        session.thread_id,
        session.source_message_id,
    )
    writes = []
    for item in rules["mappings"]:
        field_name = item["source_field"]
        if item["element_id"] not in {spec["element_id"] for spec in manifest}:
            raise ValidationError(_("A mapping target is no longer available."))
        if field_name in current_fields:
            raw_value = values[field_name]
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
            raw_value = rows[row_index].get(relation_field)
        value = _m1_value(raw_value, item["value_type"])
        writes.append(
            {
                "element_id": item["element_id"],
                "operation": "set_value",
                "value": {"type": item["value_type"], "data": value},
            }
        )
    mapping_plan = {
        "schema_version": "1",
        "template_sha256": summary["template_sha256"],
        "writes": writes,
    }

    # The Odoo service owns request persistence, spawn isolation, independent
    # verification, private attachment creation and its idempotent UUID.
    session._transition_from_service("rendering", expected_revision)
    request_uuid = _stable_request_uuid(env, session)
    try:
        result = env["office.document.request"]._render_request_sync(
            request_uuid,
            session.source_attachment_id.id,
            mapping_plan,
            session.thread_id.id,
            session.source_message_id.id,
        )
        if result.get("state") != "generated" or not result.get("output_attachment_id"):
            session.invalidate_recordset(["state", "revision"])
            session._transition_from_service(
                "failed",
                session.revision,
                error_code=(result.get("error_code") or "office_render_failed").lower(),
            )
            return {
                "session_id": session.id,
                "state": "failed",
                "revision": session.revision,
                "error_code": result.get("error_code") or "office_render_failed",
                "output_attachment_id": False,
            }
        output_id = result.get("output_attachment_id")
        if type(output_id) is not int or output_id <= 0:
            raise AccessError(_("The generated attachment is unavailable."))
        # M1 creates and commits the output in its own short transaction, and
        # checks attachment read access there before returning. The caller's
        # PostgreSQL REPEATABLE READ snapshot cannot necessarily see that newly
        # committed row yet, so a second browse().exists() here can falsely turn
        # a successful render into a failed RPC and roll back the Session.
        session.invalidate_recordset(["state", "revision"])
        completed = session._transition_from_service("completed", session.revision)
        return {
            "session_id": session.id,
            "state": "completed",
            "revision": completed["revision"],
            "output_attachment_id": output_id,
            "download_url": _render_result_url(output_id),
            "request_uuid": request_uuid,
        }
    except Exception:
        session.invalidate_recordset(["state", "revision"])
        if session.state == "rendering":
            failed = session._transition_from_service(
                "failed", session.revision, error_code="office_render_failed"
            )
            return {
                "session_id": session.id,
                "state": "failed",
                "revision": failed["revision"],
                "error_code": "office_render_failed",
                "output_attachment_id": False,
            }
        raise
