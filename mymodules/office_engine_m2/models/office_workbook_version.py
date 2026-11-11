"""Private, immutable workbook version metadata managed by trusted services."""

from __future__ import annotations

import contextvars
import re
import uuid

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError


_VERSION_MUTATION = contextvars.ContextVar("office_workbook_version_internal_mutation", default=False)
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_VERSION_STATES = {
    "verifying",
    "candidate_received",
    "awaiting_confirmation",
    "verified",
    "accepted_current",
    "superseded",
    "finalized",
    "partially_verified",
    "rejected",
    "failed",
    "stale",
}
_TRANSITIONS = {
    "verifying": {"verified", "partially_verified", "failed", "rejected"},
    "candidate_received": {
        "awaiting_confirmation", "verified", "partially_verified", "failed", "rejected", "stale"
    },
    "awaiting_confirmation": {"candidate_received", "failed", "rejected", "stale"},
    "verified": {"accepted_current", "failed", "rejected", "stale"},
    "accepted_current": {"superseded", "finalized"},
    "superseded": set(),
    "finalized": {"superseded"},
    # PARTIALLY_VERIFIED remains an unchanged validation grade; only the
    # scoped CB-02 user-review service may move an edit Candidate to Current.
    "partially_verified": {"accepted_current", "failed", "rejected"},
    "rejected": set(),
    "failed": set(),
    "stale": set(),
}


class OfficeWorkbookVersion(models.Model):
    _name = "office.workbook.version"
    _description = "Private Office Workbook Version"
    _order = "session_id, version_no, id"

    version_uuid = fields.Char(required=True, readonly=True, copy=False, index=True)
    session_id = fields.Many2one(
        "office.mapping.session", required=True, readonly=True, copy=False, ondelete="restrict", index=True
    )
    owner_id = fields.Many2one("res.users", required=True, readonly=True, copy=False, index=True, ondelete="restrict")
    company_id = fields.Many2one("res.company", required=True, readonly=True, copy=False, index=True, ondelete="restrict")
    thread_id = fields.Many2one("llm.thread", required=True, readonly=True, copy=False, ondelete="restrict", index=True)
    source_message_id = fields.Many2one("mail.message", readonly=True, copy=False, ondelete="restrict")
    intent_message_id = fields.Many2one("mail.message", readonly=True, copy=False, ondelete="restrict", index=True)
    candidate_review_watermark_message_id = fields.Many2one(
        "mail.message", readonly=True, copy=False, ondelete="restrict"
    )
    source_request_id = fields.Many2one("office.document.request", readonly=True, copy=False, ondelete="restrict", index=True)
    version_no = fields.Integer(required=True, readonly=True, copy=False, index=True)
    version_kind = fields.Selection(
        [("initial", "Initial"), ("edit", "Edit"), ("restore", "Restore")],
        required=True,
        readonly=True,
        copy=False,
    )
    state = fields.Selection(
        [(name, name.replace("_", " ").title()) for name in sorted(_VERSION_STATES)],
        required=True,
        readonly=True,
        copy=False,
        index=True,
    )
    parent_version_id = fields.Many2one(
        "office.workbook.version", readonly=True, copy=False, ondelete="restrict", index=True
    )
    restored_from_version_id = fields.Many2one(
        "office.workbook.version", readonly=True, copy=False, ondelete="restrict", index=True
    )
    idempotency_key = fields.Char(required=True, readonly=True, copy=False, size=128, index=True)
    request_digest = fields.Char(required=True, readonly=True, copy=False, size=64)
    intent_effect_digest = fields.Char(readonly=True, copy=False, size=64)
    confirmation_receipt_id = fields.Char(readonly=True, copy=False, size=128)
    requires_confirmation = fields.Boolean(readonly=True, copy=False, default=False)
    acceptance_authorization_kind = fields.Selection(
        [("explicit_intent", "Explicit Intent"), ("confirmed_intent", "Confirmed Intent"), ("candidate_review", "Candidate Review")],
        readonly=True,
        copy=False,
    )
    acceptance_authorization_message_id = fields.Many2one(
        "mail.message", readonly=True, copy=False, ondelete="restrict"
    )
    acceptance_authorization_digest = fields.Char(readonly=True, copy=False, size=64)
    rejection_message_id = fields.Many2one("mail.message", readonly=True, copy=False, ondelete="restrict")
    rejection_digest = fields.Char(readonly=True, copy=False, size=64)
    rejected_at = fields.Datetime(readonly=True, copy=False)
    input_attachment_id = fields.Many2one("ir.attachment", readonly=True, copy=False, ondelete="restrict")
    output_attachment_id = fields.Many2one("ir.attachment", readonly=True, copy=False, ondelete="restrict")
    input_sha256 = fields.Char(readonly=True, copy=False, size=64)
    output_sha256 = fields.Char(readonly=True, copy=False, size=64)
    filename = fields.Char(readonly=True, copy=False, size=255)
    mimetype = fields.Char(readonly=True, copy=False, size=128)
    file_size = fields.Integer(readonly=True, copy=False)
    session_revision = fields.Integer(required=True, readonly=True, copy=False)
    proposal_revision = fields.Integer(required=True, readonly=True, copy=False)
    document_revision = fields.Integer(required=True, readonly=True, copy=False)
    accepted_document_revision = fields.Integer(readonly=True, copy=False)
    provider_id = fields.Char(readonly=True, copy=False, size=128)
    provider_model = fields.Char(readonly=True, copy=False, size=128)
    provider_response_id = fields.Char(readonly=True, copy=False, size=255)
    provider_tool_call_id = fields.Char(readonly=True, copy=False, size=255)
    provider_file_id = fields.Char(readonly=True, copy=False, size=255)
    provider_usage_json = fields.Text(readonly=True, copy=False)
    provider_cleanup_state = fields.Selection(
        [("not_applicable", "Not Applicable"), ("pending", "Pending"), ("complete", "Complete"), ("failed", "Failed")],
        readonly=True,
        copy=False,
    )
    validation_result = fields.Selection(
        [("VERIFIED", "Verified"), ("PARTIALLY_VERIFIED", "Partially Verified"), ("FAILED", "Failed"), ("REJECTED", "Rejected")],
        readonly=True,
        copy=False,
    )
    validator_policy_version = fields.Char(readonly=True, copy=False, size=128)
    validation_report_id = fields.Char(readonly=True, copy=False, size=64)
    validation_report_sha256 = fields.Char(readonly=True, copy=False, size=64)
    validated_candidate_sha256 = fields.Char(readonly=True, copy=False, size=64)
    validation_completed_at = fields.Datetime(readonly=True, copy=False)
    delivery_state = fields.Selection(
        [("not_finalized", "Not Finalized"), ("delivered", "Delivered"), ("failed", "Failed")],
        required=True,
        readonly=True,
        copy=False,
        default="not_finalized",
        index=True,
    )
    final_attachment_id = fields.Many2one("ir.attachment", readonly=True, copy=False, ondelete="restrict")
    final_message_id = fields.Many2one("mail.message", readonly=True, copy=False, ondelete="restrict")
    finalized_at = fields.Datetime(readonly=True, copy=False)
    error_code = fields.Char(readonly=True, copy=False, size=64)
    created_at = fields.Datetime(required=True, readonly=True, copy=False, default=fields.Datetime.now)

    _sql_constraints = [
        ("version_uuid_unique", "unique(version_uuid)", "The workbook version UUID must be unique."),
        ("version_no_unique", "unique(session_id, version_no)", "Version numbers must be unique within a Session."),
        ("idempotency_unique", "unique(session_id, idempotency_key)", "The idempotency key must be unique within a Session."),
        ("request_unique", "unique(session_id, source_request_id)", "An M1 request can register only one initial workbook version."),
        ("version_no_positive", "CHECK(version_no > 0)", "The version number must be positive."),
        ("revision_nonnegative", "CHECK(session_revision > 0 AND proposal_revision >= 0 AND document_revision >= 0)", "Captured revisions are invalid."),
        ("file_size_nonnegative", "CHECK(file_size IS NULL OR file_size >= 0)", "The file size cannot be negative."),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        if not _VERSION_MUTATION.get():
            raise AccessError(_("Workbook versions can only be created by the internal version service."))
        allowed = {
            "version_uuid", "session_id", "owner_id", "company_id", "thread_id", "source_message_id", "intent_message_id",
            "candidate_review_watermark_message_id",
            "source_request_id", "version_no", "version_kind", "state", "parent_version_id",
            "restored_from_version_id", "idempotency_key", "request_digest", "intent_effect_digest",
            "confirmation_receipt_id", "requires_confirmation", "input_attachment_id", "input_sha256",
            "filename", "mimetype", "session_revision", "proposal_revision", "document_revision",
            "provider_id", "provider_model", "provider_response_id", "provider_tool_call_id", "provider_file_id",
            "provider_usage_json", "provider_cleanup_state", "error_code",
        }
        normalized = []
        for vals in vals_list:
            if set(vals) - allowed:
                raise ValidationError(_("The workbook version contains unsupported fields."))
            session = self.env["office.mapping.session"].browse(vals.get("session_id")).exists()
            if not session:
                raise AccessError(_("The workbook Session is unavailable."))
            session.check_access("write")
            if session.owner_id.id != self.env.uid:
                raise AccessError(_("The workbook Session is unavailable."))
            values = dict(vals)
            if values.get("version_kind") in {"edit", "restore"} and not values.get("intent_message_id"):
                raise ValidationError(_("An edit or restore version must be bound to its user Intent message."))
            if values.get("version_kind") in {"edit", "restore"} and not values.get("candidate_review_watermark_message_id"):
                raise ValidationError(_("An edit or restore Candidate must record its Thread review watermark."))
            if values.get("source_message_id") not in (None, False, session.source_message_id.id):
                raise ValidationError(_("A workbook version must use its Session source message."))
            values.update({
                "owner_id": session.owner_id.id,
                "company_id": session.company_id.id,
                "thread_id": session.thread_id.id,
                "version_uuid": values.get("version_uuid") or str(uuid.uuid4()),
            })
            normalized.append(values)
        return super().create(normalized)

    def write(self, vals):
        if not _VERSION_MUTATION.get():
            raise AccessError(_("Workbook version fields are managed by the internal version service."))
        allowed = {
            "state", "output_attachment_id", "output_sha256", "file_size", "validator_policy_version",
            "filename", "mimetype",
            "validation_report_id", "validation_report_sha256", "validated_candidate_sha256",
            "validation_result", "validation_completed_at", "accepted_document_revision", "error_code",
            "delivery_state", "final_attachment_id", "final_message_id", "finalized_at",
            "acceptance_authorization_kind", "acceptance_authorization_message_id",
            "acceptance_authorization_digest", "rejection_message_id", "rejection_digest", "rejected_at",
            "provider_response_id", "provider_tool_call_id", "provider_file_id",
            "provider_usage_json", "provider_cleanup_state",
        }
        if set(vals) - allowed:
            raise ValidationError(_("The workbook version update contains unsupported fields."))
        next_state = vals.get("state")
        if next_state:
            if next_state not in _VERSION_STATES:
                raise ValidationError(_("The workbook version state is invalid."))
            for record in self:
                if next_state not in _TRANSITIONS.get(record.state, set()):
                    raise ValidationError(_("The workbook version state transition is not allowed."))
        return super().write(vals)

    def unlink(self):
        raise AccessError(_("Workbook version history is immutable and cannot be deleted."))

    @api.constrains(
        "session_id",
        "owner_id",
        "company_id",
        "thread_id",
        "source_message_id",
        "intent_message_id",
        "candidate_review_watermark_message_id",
        "acceptance_authorization_message_id",
        "rejection_message_id",
        "version_kind",
        "parent_version_id",
        "restored_from_version_id",
        "input_attachment_id",
        "output_attachment_id",
        "final_attachment_id",
        "final_message_id",
        "delivery_state",
        "finalized_at",
        "state",
        "delivery_state",
        "finalized_at",
        "filename",
        "mimetype",
        "file_size",
    )
    def _check_version_bindings(self):
        for version in self:
            session = version.session_id
            if (
                version.owner_id != session.owner_id
                or version.company_id != session.company_id
                or version.thread_id != session.thread_id
                or version.source_message_id != session.source_message_id
            ):
                raise ValidationError(_("The workbook version must remain bound to its Session."))
            if version.intent_message_id:
                intent = version.intent_message_id
                if (
                    intent.model != version.thread_id._name
                    or intent.res_id != version.thread_id.id
                    or intent.author_id != version.owner_id.partner_id
                    or getattr(intent, "llm_role", False) != "user"
                    or getattr(intent, "is_error", False)
                ):
                    raise ValidationError(_("The workbook Intent message must belong to its owner and Thread."))
            if version.candidate_review_watermark_message_id:
                watermark = version.candidate_review_watermark_message_id
                if watermark.model != version.thread_id._name or watermark.res_id != version.thread_id.id:
                    raise ValidationError(_("The Candidate review watermark must belong to its Thread."))
            for message, label in (
                (version.acceptance_authorization_message_id, "acceptance"),
                (version.rejection_message_id, "rejection"),
            ):
                if message and (
                    message.model != version.thread_id._name
                    or message.res_id != version.thread_id.id
                    or message.author_id != version.owner_id.partner_id
                    or getattr(message, "llm_role", False) != "user"
                    or getattr(message, "is_error", False)
                ):
                    raise ValidationError(_("The workbook %(label)s message must belong to its owner and Thread.", label=label))
            if version.acceptance_authorization_kind:
                if (
                    not version.acceptance_authorization_message_id
                    or not _HEX64.fullmatch(version.acceptance_authorization_digest or "")
                ):
                    raise ValidationError(_("The Candidate acceptance authorization record is incomplete."))
            elif version.acceptance_authorization_message_id or version.acceptance_authorization_digest:
                raise ValidationError(_("The Candidate acceptance authorization record is inconsistent."))
            if version.rejection_message_id:
                if (
                    version.state != "rejected"
                    or not _HEX64.fullmatch(version.rejection_digest or "")
                    or not version.rejected_at
                ):
                    raise ValidationError(_("The Candidate rejection record is incomplete."))
            if version.parent_version_id and version.parent_version_id.session_id != session:
                raise ValidationError(_("A workbook parent must belong to the same Session."))
            if version.restored_from_version_id:
                if (
                    version.version_kind != "restore"
                    or version.restored_from_version_id.session_id != session
                    or version.restored_from_version_id == version.parent_version_id
                ):
                    raise ValidationError(_("A restore source must be historical within the same Session."))
            if version.version_kind == "initial":
                if version.parent_version_id or version.restored_from_version_id:
                    raise ValidationError(_("An initial version cannot have a parent or restore source."))
                if session.origin_kind == "fileless":
                    if version.input_attachment_id or version.input_sha256 or session.source_attachment_id:
                        raise ValidationError(_("A fileless initial version cannot claim source file bytes."))
                elif version.input_attachment_id != session.source_attachment_id:
                    raise ValidationError(_("An uploaded initial version must use the Session source attachment."))
            elif version.parent_version_id:
                parent = version.parent_version_id
                if not parent.output_attachment_id or version.input_attachment_id != parent.output_attachment_id:
                    raise ValidationError(_("A candidate input must be the output of its parent version."))
            if version.output_attachment_id:
                output = version.output_attachment_id
                if (
                    output.res_model != version._name
                    or output.res_id != version.id
                    or output.public
                    or output.type != "binary"
                    or output.url
                    or output.company_id != version.company_id
                ):
                    raise ValidationError(_("A workbook output must be private and bound to its version."))
                output.check("read")
                if version.file_size and output.file_size != version.file_size:
                    raise ValidationError(_("The version byte size does not match its output attachment."))
            if version.final_attachment_id:
                final_attachment = version.final_attachment_id
                if (
                    final_attachment.public
                    or final_attachment.type != "binary"
                    or final_attachment.url
                    or final_attachment.company_id not in (False, version.company_id)
                ):
                    raise ValidationError(_("A finalized workbook attachment must remain private and company-scoped."))
                final_attachment.check("read")
            if version.delivery_state == "delivered":
                if not version.final_attachment_id or not version.final_message_id or not version.finalized_at:
                    raise ValidationError(_("A delivered workbook version needs an attachment, message, and timestamp."))
                if (
                    version.final_message_id.model != version.thread_id._name
                    or version.final_message_id.res_id != version.thread_id.id
                    or version.final_message_id.llm_role != "assistant"
                    or version.final_attachment_id not in version.final_message_id.attachment_ids
                    or version.state not in {"finalized", "superseded"}
                ):
                    raise ValidationError(_("The delivery reference must point to an attachment on its Thread message."))
            elif version.final_attachment_id or version.final_message_id or version.finalized_at:
                raise ValidationError(_("Finalize references require delivered state."))
            elif version.state == "finalized":
                raise ValidationError(_("A finalized workbook version must have a verified delivery reference."))
