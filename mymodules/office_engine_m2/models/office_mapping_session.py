import json
import re

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError


SESSION_STATES = (
    "collecting",
    "needs_clarification",
    "awaiting_confirmation",
    "editing",
    "rendering",
    "completed",
    "failed",
    "cancelled",
)

ALLOWED_TRANSITIONS = {
    "collecting": {
        "needs_clarification",
        "awaiting_confirmation",
        "failed",
        "cancelled",
    },
    "needs_clarification": {
        "collecting",
        "editing",
        "failed",
        "cancelled",
    },
    "awaiting_confirmation": {"editing", "rendering", "failed", "cancelled"},
    "editing": {"awaiting_confirmation", "needs_clarification", "failed", "cancelled"},
    "rendering": {"completed", "failed"},
    "completed": set(),
    "failed": set(),
    "cancelled": set(),
}

_ERROR_CODE_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_EMPTY_PROPOSAL = {
    "schema_version": "m2.mapping-proposal.v1",
    "mappings": [],
    "clarifications": [],
    "skipped_targets": [],
}


class OfficeMappingSession(models.Model):
    _name = "office.mapping.session"
    _description = "Office Mapping Session"
    _order = "write_date desc, id desc"

    owner_id = fields.Many2one(
        "res.users", required=True, readonly=True, copy=False, index=True, ondelete="restrict"
    )
    company_id = fields.Many2one(
        "res.company", required=True, readonly=True, copy=False, index=True, ondelete="restrict"
    )
    thread_id = fields.Many2one(
        "llm.thread", required=True, readonly=True, copy=False, index=True, ondelete="cascade"
    )
    source_message_id = fields.Many2one(
        "mail.message", required=True, readonly=True, copy=False, ondelete="restrict"
    )
    source_attachment_id = fields.Many2one(
        "ir.attachment", required=True, readonly=True, copy=False, ondelete="restrict"
    )
    target_model = fields.Char(required=True, readonly=True, copy=False, index=True)
    target_record_id = fields.Integer(required=True, readonly=True, copy=False, index=True)
    state = fields.Selection(
        [
            ("collecting", "Collecting"),
            ("needs_clarification", "Needs Clarification"),
            ("awaiting_confirmation", "Awaiting Confirmation"),
            ("editing", "Editing"),
            ("rendering", "Rendering"),
            ("completed", "Completed"),
            ("failed", "Failed"),
            ("cancelled", "Cancelled"),
        ],
        required=True,
        readonly=True,
        copy=False,
        default="collecting",
        index=True,
    )
    revision = fields.Integer(required=True, readonly=True, copy=False, default=1)
    mapping_rules_json = fields.Text(
        readonly=True,
        copy=False,
        default=lambda self: json.dumps(_EMPTY_PROPOSAL, separators=(",", ":")),
    )
    confirmed_revision = fields.Integer(readonly=True, copy=False, default=0)
    context_json = fields.Text(readonly=True, copy=False, default="{}")
    error_code = fields.Char(readonly=True, copy=False, size=64)

    _sql_constraints = [
        ("revision_positive", "CHECK(revision > 0)", "Revision must be positive."),
        (
            "target_record_positive",
            "CHECK(target_record_id > 0)",
            "Target record ID must be positive.",
        ),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        # ORM create is remotely callable. Session creation is restricted to the
        # internal Python service, which calls _create_from_mapping_service().
        raise AccessError(_("Create mapping sessions through the mapping service."))

    @api.model
    def _create_from_mapping_service(self, vals):
        allowed = {
            "thread_id",
            "source_message_id",
            "source_attachment_id",
            "target_model",
            "target_record_id",
        }
        if not isinstance(vals, dict) or set(vals) != allowed:
            raise ValidationError(_("Invalid mapping session input."))

        from ..services.mapping_service import _validate_session_bindings

        thread, message, attachment, target = _validate_session_bindings(
            self.env,
            thread_id=vals["thread_id"],
            source_message_id=vals["source_message_id"],
            source_attachment_id=vals["source_attachment_id"],
            target_model=vals["target_model"],
            target_record_id=vals["target_record_id"],
        )
        self.browse().check_access("create")
        values = {
            "owner_id": self.env.uid,
            "company_id": self.env.company.id,
            "thread_id": thread.id,
            "source_message_id": message.id,
            "source_attachment_id": attachment.id,
            "target_model": target._name,
            "target_record_id": target.id,
            "state": "collecting",
            "revision": 1,
        }
        return super(OfficeMappingSession, self).create(values)

    def write(self, vals):
        raise AccessError(_("Mapping session fields are managed by the mapping service."))

    def _transition_from_service(self, target_state, expected_revision, error_code=None):
        self.ensure_one()
        self.check_access("write")
        if target_state not in SESSION_STATES:
            raise ValidationError(_("Invalid mapping session state."))
        if type(expected_revision) is not int or expected_revision < 1:
            raise ValidationError(_("Invalid mapping session revision."))
        if error_code is not None and (
            not isinstance(error_code, str) or not _ERROR_CODE_RE.fullmatch(error_code)
        ):
            raise ValidationError(_("Invalid mapping session error code."))
        if error_code and target_state != "failed":
            raise ValidationError(_("An error code is only valid for failed sessions."))

        self.flush_recordset(["state", "revision"])
        self.env.cr.execute(
            "SELECT state, revision FROM office_mapping_session WHERE id = %s FOR UPDATE",
            [self.id],
        )
        row = self.env.cr.fetchone()
        if not row:
            raise AccessError(_("The mapping session is unavailable."))
        current_state, current_revision = row
        if current_revision != expected_revision:
            raise ValidationError(_("MAPPING_REVISION_STALE: reload the mapping card and retry."))
        if target_state not in ALLOWED_TRANSITIONS[current_state]:
            raise ValidationError(_("This mapping session state transition is not allowed."))

        update = {"state": target_state, "revision": current_revision + 1}
        if target_state == "failed":
            update["error_code"] = error_code or False
        super(OfficeMappingSession, self).write(update)
        self.invalidate_recordset(["state", "revision", "error_code"])
        return {"session_id": self.id, "state": target_state, "revision": current_revision + 1}

    def _set_context_from_service(self, context_json):
        """Persist server-owned schema metadata; never accept it through ORM write."""
        self.ensure_one()
        self.check_access("write")
        try:
            context = json.loads(context_json)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValidationError(_("Invalid mapping context.")) from exc
        if (
            not isinstance(context, dict)
            or set(context) != {"target_manifest", "allowed_fields"}
            or not isinstance(context["target_manifest"], list)
            or not isinstance(context["allowed_fields"], dict)
        ):
            raise ValidationError(_("Invalid mapping context."))
        super(OfficeMappingSession, self).write(
            {"context_json": json.dumps(context, ensure_ascii=False, separators=(",", ":"))}
        )
        self.invalidate_recordset(["context_json"])

    def _save_mapping_from_service(self, mapping_rules_json, expected_revision, target_state):
        """Atomically save validator-approved mapping and advance its revision."""
        self.ensure_one()
        self.check_access("write")
        if target_state not in ("needs_clarification", "awaiting_confirmation", "editing"):
            raise ValidationError(_("Invalid mapping state."))
        if type(expected_revision) is not int or expected_revision < 1:
            raise ValidationError(_("Invalid mapping session revision."))
        try:
            rules = json.loads(mapping_rules_json)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValidationError(_("Invalid mapping rules.")) from exc
        if not isinstance(rules, dict) or set(rules) != {
            "schema_version", "mappings", "clarifications", "skipped_targets"
        }:
            raise ValidationError(_("Invalid mapping rules."))

        self.flush_recordset(["state", "revision"])
        self.env.cr.execute(
            "SELECT state, revision FROM office_mapping_session WHERE id = %s FOR UPDATE",
            [self.id],
        )
        row = self.env.cr.fetchone()
        if not row:
            raise AccessError(_("The mapping session is unavailable."))
        current_state, current_revision = row
        if current_revision != expected_revision:
            raise ValidationError(_("MAPPING_REVISION_STALE: reload the mapping card and retry."))
        if target_state != current_state and target_state not in ALLOWED_TRANSITIONS[current_state]:
            raise ValidationError(_("This mapping session state transition is not allowed."))

        new_revision = current_revision + 1
        super(OfficeMappingSession, self).write(
            {
                "mapping_rules_json": json.dumps(rules, ensure_ascii=False, separators=(",", ":")),
                "confirmed_revision": 0,
                "state": target_state,
                "revision": new_revision,
                "error_code": False,
            }
        )
        self.invalidate_recordset(
            ["mapping_rules_json", "confirmed_revision", "state", "revision", "error_code"]
        )
        return {"session_id": self.id, "state": target_state, "revision": new_revision}

    def _confirm_mapping_from_service(self, expected_revision):
        """Bind explicit confirmation to the current, already validated mapping."""
        self.ensure_one()
        self.check_access("write")
        if type(expected_revision) is not int or expected_revision < 1:
            raise ValidationError(_("Invalid mapping session revision."))
        self.flush_recordset(["state", "revision"])
        self.env.cr.execute(
            "SELECT state, revision FROM office_mapping_session WHERE id = %s FOR UPDATE",
            [self.id],
        )
        row = self.env.cr.fetchone()
        if not row:
            raise AccessError(_("The mapping session is unavailable."))
        current_state, current_revision = row
        if current_revision != expected_revision:
            raise ValidationError(_("MAPPING_REVISION_STALE: reload the mapping card and retry."))
        if current_state not in ("awaiting_confirmation", "editing"):
            raise ValidationError(_("The mapping session cannot be confirmed in its current state."))
        if current_state == "editing" and "awaiting_confirmation" not in ALLOWED_TRANSITIONS[current_state]:
            raise ValidationError(_("This mapping session state transition is not allowed."))
        new_revision = current_revision + 1
        super(OfficeMappingSession, self).write(
            {
                "state": "awaiting_confirmation",
                "revision": new_revision,
                "confirmed_revision": new_revision,
            }
        )
        self.invalidate_recordset(["state", "revision", "confirmed_revision"])
        return {
            "session_id": self.id,
            "state": "awaiting_confirmation",
            "revision": new_revision,
            "confirmed_revision": new_revision,
        }
