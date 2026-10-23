from odoo import _
from odoo.exceptions import AccessError, ValidationError


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
