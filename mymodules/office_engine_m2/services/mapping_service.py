import json

from odoo import _
from odoo.exceptions import AccessError, ValidationError
from office_mapping_verify import validate_user_revision


_UNAVAILABLE = "The mapping session context is unavailable."


def _positive_id(value, label):
    if type(value) is not int or value < 1:
        raise ValidationError(_("Invalid %s reference.") % label)
    return value


def _validate_session_bindings(
    env,
    *,
    thread_id,
    source_message_id,
    source_attachment_id,
    target_model,
    target_record_id,
):
    """Validate all references under the caller's current Odoo environment."""
    thread_id = _positive_id(thread_id, "thread")
    source_message_id = _positive_id(source_message_id, "source message")
    source_attachment_id = _positive_id(source_attachment_id, "source attachment")
    target_record_id = _positive_id(target_record_id, "target record")
    if not isinstance(target_model, str) or not target_model.strip():
        raise ValidationError(_("Invalid target model."))

    thread = env["llm.thread"].browse(thread_id).exists()
    message = env["mail.message"].browse(source_message_id).exists()
    attachment = env["ir.attachment"].browse(source_attachment_id).exists()
    if not thread or not message or not attachment:
        raise AccessError(_(_UNAVAILABLE))

    # Check access before examining relationships so a forged ID cannot be used
    # to discover another user's thread, message, or attachment.
    thread.check_access("read")
    if thread.user_id.id != env.uid:
        raise AccessError(_(_UNAVAILABLE))
    message.check_access("read")
    attachment.check_access("read")

    if (
        message.model != "llm.thread"
        or message.res_id != thread.id
        or message not in thread.message_ids
        or attachment not in message.attachment_ids
    ):
        raise AccessError(_(_UNAVAILABLE))
    if attachment.company_id and attachment.company_id not in env.companies:
        raise AccessError(_(_UNAVAILABLE))

    if target_model not in env.registry.models:
        raise AccessError(_(_UNAVAILABLE))
    target_model_recordset = env[target_model]
    target_model_recordset.browse().check_access("read")
    target = target_model_recordset.browse(target_record_id).exists()
    if not target:
        raise AccessError(_(_UNAVAILABLE))
    target.check_access("read")
    if "company_id" in target._fields and target.company_id and target.company_id not in env.companies:
        raise AccessError(_(_UNAVAILABLE))
    return thread, message, attachment, target


def create_session(
    env,
    *,
    thread_id,
    source_message_id,
    source_attachment_id,
    target_model,
    target_record_id,
):
    """Create a minimal session after rechecking every binding as the caller."""
    values = {
        "thread_id": thread_id,
        "source_message_id": source_message_id,
        "source_attachment_id": source_attachment_id,
        "target_model": target_model,
        "target_record_id": target_record_id,
    }
    session = env["office.mapping.session"]._create_from_mapping_service(values)
    return get_session_context(env, session.id)


def get_session_context(env, session_id):
    """Return allowlisted metadata for a session owned by the current user."""
    session_id = _positive_id(session_id, "mapping session")
    session = env["office.mapping.session"].search([("id", "=", session_id)], limit=1)
    if not session:
        raise AccessError(_(_UNAVAILABLE))
    session.check_access("read")
    return {
        "session_id": session.id,
        "owner_id": session.owner_id.id,
        "company_id": session.company_id.id,
        "thread_id": session.thread_id.id,
        "source_message_id": session.source_message_id.id,
        "source_attachment_id": session.source_attachment_id.id,
        "target_model": session.target_model,
        "target_record_id": session.target_record_id,
        "state": session.state,
        "revision": session.revision,
        "error_code": session.error_code or None,
    }


def transition_session(env, session_id, target_state, expected_revision, *, error_code=None):
    """Apply one server-authorized state change with optimistic revision control."""
    session_id = _positive_id(session_id, "mapping session")
    session = env["office.mapping.session"].search([("id", "=", session_id)], limit=1)
    if not session:
        raise AccessError(_(_UNAVAILABLE))
    result = session._transition_from_service(
        target_state,
        expected_revision,
        error_code=error_code,
    )
    return result


def _owned_session(env, session_id):
    session_id = _positive_id(session_id, "mapping session")
    session = env["office.mapping.session"].browse(session_id).exists()
    if not session:
        raise AccessError(_(_UNAVAILABLE))
    session.check_access("read")
    if session.owner_id.id != env.uid or session.company_id.id not in env.companies.ids:
        raise AccessError(_(_UNAVAILABLE))
    return session


def _load_mapping_data(session):
    try:
        rules = json.loads(session.mapping_rules_json or "{}")
        context = json.loads(session.context_json or "{}")
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValidationError(_("The mapping context is invalid.")) from exc
    if (
        not isinstance(rules, dict)
        or not isinstance(context, dict)
        or set(context) != {"target_manifest", "allowed_fields"}
    ):
        raise ValidationError(_("The mapping context is invalid."))
    return rules, context["target_manifest"], context["allowed_fields"]


def set_mapping_context(env, session_id, target_manifest, allowed_fields):
    """Install server-owned TargetManifest/allowlist metadata for a session.

    This internal Python service is not exposed as an RPC route. It exists for
    trusted orchestration and deterministic test fixtures; browser input never
    supplies these values.
    """
    session = _owned_session(env, session_id)
    if not isinstance(target_manifest, list) or not isinstance(allowed_fields, dict):
        raise ValidationError(_("Invalid mapping context."))
    proposal = {
        "schema_version": "m2.mapping-proposal.v1",
        "mappings": [],
        "clarifications": [],
        "skipped_targets": [],
    }
    report = validate_user_revision(proposal, [], target_manifest, allowed_fields)
    if report.status == "invalid":
        raise ValidationError(_("Invalid mapping context."))
    session._set_context_from_service(
        json.dumps(
            {"target_manifest": target_manifest, "allowed_fields": allowed_fields},
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )
    return {"session_id": session.id, "revision": session.revision}


def post_mapping_card(env, session_id):
    """Post a server-authored card reference without persisting business data."""
    session = _owned_session(env, session_id)
    return session.thread_id.message_post(
        body=_("Review the proposed document mapping."),
        llm_role="assistant",
        body_json={
            "office_mapping_card": {
                "type": "office_mapping_card_v1",
                "session_id": session.id,
                "revision": session.revision,
            }
        },
    )


def get_mapping_card_context(env, session_id, expected_revision):
    session = _owned_session(env, session_id)
    if type(expected_revision) is not int or expected_revision < 1:
        raise ValidationError(_("Invalid mapping session revision."))
    rules, manifest, allowed_fields = _load_mapping_data(session)
    if not isinstance(manifest, list) or not isinstance(allowed_fields, dict):
        raise ValidationError(_("The mapping context is invalid."))
    mapped = {item["element_id"]: item for item in rules.get("mappings", [])}
    return {
        "session_id": session.id,
        "revision": session.revision,
        "state": session.state,
        "stale": expected_revision != session.revision,
        "targets": [
            {
                "element_id": item["element_id"],
                "label": item["element_id"],
                "required": item["required"],
                "source_field": mapped.get(item["element_id"], {}).get("source_field", ""),
            }
            for item in manifest
        ],
        "fields": [
            {"field_id": field_id, "label": field_id, "value_type": value_type}
            for field_id, value_type in sorted(allowed_fields.items())
        ],
    }


def save_mapping_edits(env, session_id, expected_revision, edits):
    session = _owned_session(env, session_id)
    if type(expected_revision) is not int or expected_revision < 1:
        raise ValidationError(_("Invalid mapping session revision."))
    if not isinstance(edits, list):
        raise ValidationError(_("Invalid mapping edits."))
    rules, manifest, allowed_fields = _load_mapping_data(session)
    report = validate_user_revision(rules, edits, manifest, allowed_fields)
    if report.status == "invalid":
        raise ValidationError(_("One or more mapping choices are invalid."))

    edits_by_target = {item["element_id"]: dict(item) for item in edits}
    updated = dict(rules)
    updated["mappings"] = [
        edits_by_target.pop(item["element_id"], dict(item))
        for item in rules.get("mappings", [])
    ]
    updated["mappings"].extend(edits_by_target.values())
    edited_ids = {item["element_id"] for item in edits}
    updated["clarifications"] = [
        item for item in rules.get("clarifications", [])
        if item.get("element_id") not in edited_ids
    ]
    updated["skipped_targets"] = [
        item for item in rules.get("skipped_targets", []) if item not in edited_ids
    ]

    if session.state == "collecting":
        new_state = "awaiting_confirmation" if report.ready_for_review else "needs_clarification"
    elif session.state == "needs_clarification":
        new_state = "editing" if report.ready_for_review else "needs_clarification"
    elif session.state == "awaiting_confirmation":
        new_state = "editing"
    elif session.state == "editing":
        new_state = "editing" if report.ready_for_review else "needs_clarification"
    else:
        raise ValidationError(_("The mapping session cannot be edited in its current state."))

    return session._save_mapping_from_service(
        json.dumps(updated, ensure_ascii=False, separators=(",", ":")),
        expected_revision,
        new_state,
    )


def confirm_mapping(env, session_id, expected_revision):
    session = _owned_session(env, session_id)
    if type(expected_revision) is not int or expected_revision < 1:
        raise ValidationError(_("Invalid mapping session revision."))
    rules, manifest, allowed_fields = _load_mapping_data(session)
    report = validate_user_revision(rules, [], manifest, allowed_fields)
    if not report.ready_for_review:
        raise ValidationError(_("Complete all required mapping choices before confirming."))
    return session._confirm_mapping_from_service(expected_revision)
