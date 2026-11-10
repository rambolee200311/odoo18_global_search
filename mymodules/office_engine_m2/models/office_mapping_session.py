import json
import hashlib
import re

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError


SESSION_STATES = (
    "analyzing",
    "preview_ready",
    "revision_pending",
    "confirmation_required",
    "confirmed",
    "generating",
    "completed",
    "failed",
)

ALLOWED_TRANSITIONS = {
    "analyzing": {
        "preview_ready",
        "revision_pending",
        "failed",
    },
    "preview_ready": {
        "revision_pending",
        "confirmation_required",
        "analyzing",
        "failed",
    },
    "revision_pending": {"preview_ready", "confirmation_required", "analyzing", "failed"},
    "confirmation_required": {"revision_pending", "preview_ready", "confirmed", "analyzing", "failed"},
    "confirmed": {"generating", "confirmation_required", "failed"},
    "generating": {"completed", "confirmation_required", "failed"},
    "completed": set(),
    "failed": set(),
}


def _valid_saved_cell_edit(item):
    """Validate coordinate or stable repeat-row selectors in stored rules."""
    if not isinstance(item, dict) or item.get("value_type") not in {
        "string", "number", "boolean", "date", "datetime"
    }:
        return False
    if set(item) == {"element_id", "value", "value_type"}:
        return (
            isinstance(item.get("element_id"), str)
            and bool(item["element_id"].strip())
            and len(item["element_id"]) <= 255
        )
    if set(item) == {"record_target", "value", "value_type"}:
        target = item.get("record_target")
        return bool(
            isinstance(target, dict)
            and set(target) == {"group_id", "record_id", "column"}
            and isinstance(target.get("group_id"), str)
            and target["group_id"].isidentifier()
            and len(target["group_id"]) <= 64
            and type(target.get("record_id")) is int
            and target["record_id"] > 0
            and isinstance(target.get("column"), str)
            and re.fullmatch(r"[A-Z]{1,3}", target["column"])
        )
    return False


def _saved_cell_edit_identity(item):
    if "record_target" in item:
        return "record:" + json.dumps(
            item["record_target"], ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
    return "coordinate:" + item["element_id"]

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
            ("analyzing", "Analyzing"),
            ("preview_ready", "Preview Ready"),
            ("revision_pending", "Revision Pending"),
            ("confirmation_required", "Confirmation Required"),
            ("confirmed", "Confirmed"),
            ("generating", "Generating"),
            ("completed", "Completed"),
            ("failed", "Failed"),
        ],
        required=True,
        readonly=True,
        copy=False,
        default="analyzing",
        index=True,
    )
    revision = fields.Integer(required=True, readonly=True, copy=False, default=1)
    proposal_revision = fields.Integer(required=True, readonly=True, copy=False, default=0)
    document_revision = fields.Integer(required=True, readonly=True, copy=False, default=0)
    current_version_id = fields.Many2one(
        "office.workbook.version", readonly=True, copy=False, ondelete="restrict", index=True
    )
    last_valid_version_id = fields.Many2one(
        "office.workbook.version", readonly=True, copy=False, ondelete="restrict", index=True
    )
    mapping_rules_json = fields.Text(
        readonly=True,
        copy=False,
        default=lambda self: json.dumps(_EMPTY_PROPOSAL, separators=(",", ":")),
    )
    proposal_history_json = fields.Text(readonly=True, copy=False, default="[]")
    confirmed_revision = fields.Integer(readonly=True, copy=False, default=0)
    final_request_uuid = fields.Char(readonly=True, copy=False, size=36)
    preview_attachment_id = fields.Many2one(
        "ir.attachment", readonly=True, copy=False, ondelete="set null"
    )
    preview_proposal_revision = fields.Integer(readonly=True, copy=False, default=0)
    template_fingerprint = fields.Char(readonly=True, copy=False, size=64)
    proposal_data_fingerprint = fields.Char(readonly=True, copy=False, size=64)
    preview_data_fingerprint = fields.Char(readonly=True, copy=False, size=64)
    pending_cell_override_json = fields.Text(readonly=True, copy=False, default=False)
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

    def init(self):
        # Existing development sessions are migrated to the replacement state
        # vocabulary when the addon is upgraded. Terminal legacy cancellation
        # remains terminal and is represented as failed with a stable code.
        self.env.cr.execute(
            "UPDATE office_mapping_session SET error_code = 'user_cancelled' WHERE state = 'cancelled' AND error_code IS NULL"
        )
        self.env.cr.execute(
            """UPDATE office_mapping_session SET state = CASE state
                WHEN 'collecting' THEN 'analyzing'
                WHEN 'needs_clarification' THEN 'revision_pending'
                WHEN 'awaiting_confirmation' THEN 'revision_pending'
                WHEN 'editing' THEN 'revision_pending'
                WHEN 'rendering' THEN 'generating'
                WHEN 'cancelled' THEN 'failed'
                ELSE state END
                WHERE state IN ('collecting','needs_clarification','awaiting_confirmation','editing','rendering','cancelled')"""
        )

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
            "state": "analyzing",
            "revision": 1,
        }
        return super(OfficeMappingSession, self).create(values)

    def write(self, vals):
        raise AccessError(_("Mapping session fields are managed by the mapping service."))

    def _transition_from_service(
        self, target_state, expected_revision, error_code=None, final_request_uuid=None
    ):
        self.ensure_one()
        self.check_access("write")
        if target_state not in SESSION_STATES:
            raise ValidationError(_("Invalid mapping session state."))
        if target_state in {"preview_ready", "confirmation_required", "confirmed"}:
            raise ValidationError(_("Use the preview or confirmation service for this state transition."))
        if type(expected_revision) is not int or expected_revision < 1:
            raise ValidationError(_("Invalid mapping session revision."))
        if error_code is not None and (
            not isinstance(error_code, str) or not _ERROR_CODE_RE.fullmatch(error_code)
        ):
            raise ValidationError(_("Invalid mapping session error code."))
        if error_code and target_state != "failed":
            raise ValidationError(_("An error code is only valid for failed sessions."))
        if final_request_uuid not in (None, False) and (
            target_state != "completed"
            or not isinstance(final_request_uuid, str)
            or not re.fullmatch(
                r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}",
                final_request_uuid,
            )
        ):
            raise ValidationError(_("Invalid final Office request reference."))

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
        if final_request_uuid is not None:
            update["final_request_uuid"] = final_request_uuid.lower()
        super(OfficeMappingSession, self).write(update)
        self.invalidate_recordset(["state", "revision", "error_code", "final_request_uuid"])
        return {"session_id": self.id, "state": target_state, "revision": current_revision + 1}

    def _advance_document_version_from_service(
        self, version, *, expected_document_revision, expected_current_version_id
    ):
        """Atomically move current/last-valid after caller ACL and proof checks.

        SQL is used only to acquire the Session row lock. Values are invalidated
        and re-read through the current user's ORM after the lock is held.
        """
        self.ensure_one()
        self.check_access("write")
        if self.owner_id.id != self.env.uid:
            raise AccessError(_("The mapping session is unavailable."))
        if type(expected_document_revision) is not int or expected_document_revision < 0:
            raise ValidationError(_("Invalid document revision."))
        if expected_current_version_id not in (False, None) and (
            type(expected_current_version_id) is not int or expected_current_version_id < 1
        ):
            raise ValidationError(_("Invalid current workbook version."))
        version.ensure_one()
        version.check_access("write")
        if (
            version.session_id != self
            or version.owner_id.id != self.env.uid
            or version.company_id != self.company_id
            or version.thread_id != self.thread_id
            or version.state not in {"verified", "accepted_current"}
        ):
            raise AccessError(_("The workbook version is unavailable."))

        self.flush_recordset(["document_revision", "current_version_id", "last_valid_version_id"])
        self.env.cr.execute(
            "SELECT id FROM office_mapping_session WHERE id = %s FOR UPDATE", [self.id]
        )
        if not self.env.cr.fetchone():
            raise AccessError(_("The mapping session is unavailable."))
        self.invalidate_recordset(["document_revision", "current_version_id", "last_valid_version_id"])
        fresh = self.browse(self.id).exists()
        fresh.check_access("write")
        if (
            fresh.document_revision != expected_document_revision
            or (fresh.current_version_id.id or False) != (expected_current_version_id or False)
        ):
            raise ValidationError(_("WORKBOOK_VERSION_STALE: the current document version changed."))
        next_document_revision = fresh.document_revision + 1
        super(OfficeMappingSession, fresh).write(
            {
                "current_version_id": version.id,
                "last_valid_version_id": version.id,
                "document_revision": next_document_revision,
            }
        )
        fresh.invalidate_recordset(["document_revision", "current_version_id", "last_valid_version_id"])
        return {
            "session_id": self.id,
            "current_version_id": version.id,
            "last_valid_version_id": version.id,
            "document_revision": next_document_revision,
        }

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
            or not {"target_manifest", "allowed_fields"}.issubset(context)
            or set(context) - {
                "target_manifest", "allowed_fields", "mapping_groups", "template_text",
                "manifest_metadata_version", "document_format", "selected_record_ids",
                "extra_authorized_fields", "extra_authorized_collection_fields",
            }
            or not isinstance(context["target_manifest"], list)
            or not isinstance(context["allowed_fields"], dict)
            or (
                "manifest_metadata_version" in context
                and (
                    type(context["manifest_metadata_version"]) is not int
                    or context["manifest_metadata_version"] != 2
                )
            )
            or (
                "document_format" in context
                and context["document_format"] not in {"xlsx", "docx"}
            )
            or (
                "mapping_groups" in context
                and not isinstance(context["mapping_groups"], list)
            )
            or (
                "selected_record_ids" in context
                and (
                    not isinstance(context["selected_record_ids"], list)
                    or not context["selected_record_ids"]
                    or len(context["selected_record_ids"]) > 100
                    or any(
                        type(record_id) is not int or record_id < 1
                        for record_id in context["selected_record_ids"]
                    )
                    or len(set(context["selected_record_ids"]))
                    != len(context["selected_record_ids"])
                    or context["selected_record_ids"][0] != self.target_record_id
                )
            )
            or (
                "extra_authorized_fields" in context
                and (
                    not isinstance(context["extra_authorized_fields"], list)
                    or len(context["extra_authorized_fields"]) > 64
                    or any(
                        not isinstance(name, str) or not name.strip() or len(name) > 255
                        for name in context["extra_authorized_fields"]
                    )
                    or len(set(context["extra_authorized_fields"]))
                    != len(context["extra_authorized_fields"])
                    or any(name not in context["allowed_fields"] for name in context["extra_authorized_fields"])
                )
            )
            or (
                "extra_authorized_collection_fields" in context
                and (
                    not isinstance(context["extra_authorized_collection_fields"], dict)
                    or len(context["extra_authorized_collection_fields"]) > 40
                    or any(
                        not isinstance(collection, str)
                        or not collection.strip()
                        or len(collection) > 255
                        or not isinstance(paths, list)
                        or len(paths) > 64
                        or any(
                            not isinstance(path, str) or not path.strip() or len(path) > 255
                            for path in paths
                        )
                        or len(set(paths)) != len(paths)
                        for collection, paths in context["extra_authorized_collection_fields"].items()
                    )
                    or sum(
                        len(paths)
                        for paths in context["extra_authorized_collection_fields"].values()
                    ) > 64
                )
            )
            or (
                "template_text" in context
                and (
                    not isinstance(context["template_text"], list)
                    or len(context["template_text"]) > 160
                    or any(
                        not isinstance(item, dict)
                        or set(item) != {"element_id", "text"}
                        or not isinstance(item["element_id"], str)
                        or not isinstance(item["text"], str)
                        or len(item["text"]) > 600
                        for item in context["template_text"]
                    )
                )
            )
        ):
            raise ValidationError(_("Invalid mapping context."))
        super(OfficeMappingSession, self).write(
            {
                "context_json": json.dumps(context, ensure_ascii=False, separators=(",", ":")),
                "template_fingerprint": hashlib.sha256(
                    self.source_attachment_id.raw or b""
                ).hexdigest(),
            }
        )
        self.invalidate_recordset(["context_json", "template_fingerprint"])

    def _save_mapping_from_service(
        self, mapping_rules_json, expected_revision, target_state, data_fingerprint=None
    ):
        """Atomically save validator-approved mapping and advance its revision."""
        self.ensure_one()
        self.check_access("write")
        if target_state != "revision_pending":
            raise ValidationError(_("Invalid mapping state."))
        if type(expected_revision) is not int or expected_revision < 1:
            raise ValidationError(_("Invalid mapping session revision."))
        try:
            rules = json.loads(mapping_rules_json)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValidationError(_("Invalid mapping rules.")) from exc
        base_keys = {"schema_version", "mappings", "clarifications", "skipped_targets"}
        optional_keys = {"clear_targets", "format_patches", "cell_edits", "header_edits"}
        if (
            not isinstance(rules, dict)
            or not base_keys.issubset(rules)
            or set(rules) - base_keys - optional_keys
        ):
            raise ValidationError(_("Invalid mapping rules."))
        if "clear_targets" in rules and (
            not isinstance(rules["clear_targets"], list)
            or len(rules["clear_targets"]) > 200
            or any(not isinstance(item, str) or not item.strip() or len(item) > 255 for item in rules["clear_targets"])
        ):
            raise ValidationError(_("Invalid mapping rules."))
        if "format_patches" in rules and (
            not isinstance(rules["format_patches"], list)
            or len(rules["format_patches"]) > 200
            or any(
                not isinstance(item, dict)
                or set(item) != {"element_id", "number_format"}
                or not isinstance(item["element_id"], str)
                or not item["element_id"].strip()
                or not isinstance(item["number_format"], str)
                or not item["number_format"]
                or len(item["number_format"]) > 128
                for item in rules["format_patches"]
            )
        ):
            raise ValidationError(_("Invalid number-format patches."))
        if "cell_edits" in rules and (
            not isinstance(rules["cell_edits"], list)
            or len(rules["cell_edits"]) > 200
            or any(not _valid_saved_cell_edit(item) for item in rules["cell_edits"])
            or len({_saved_cell_edit_identity(item) for item in rules["cell_edits"]})
            != len(rules["cell_edits"])
        ):
            raise ValidationError(_("Invalid explicit cell edits."))
        if "header_edits" in rules and (
            not isinstance(rules["header_edits"], list)
            or len(rules["header_edits"]) > 200
            or any(
                not isinstance(item, dict)
                or set(item) != {"element_id", "value"}
                or not isinstance(item["element_id"], str)
                or not item["element_id"].strip()
                or len(item["element_id"]) > 255
                or not isinstance(item["value"], str)
                or not item["value"]
                or len(item["value"]) > 300
                or any(ord(char) < 32 for char in item["value"])
                for item in rules["header_edits"]
            )
            or len({item["element_id"] for item in rules["header_edits"]})
            != len(rules["header_edits"])
        ):
            raise ValidationError(_("Invalid explicit header edits."))
        if data_fingerprint is not None and not re.fullmatch(r"[0-9a-f]{64}", data_fingerprint):
            raise ValidationError(_("Invalid proposal data fingerprint."))

        self.flush_recordset(
            ["state", "revision", "proposal_revision", "mapping_rules_json", "proposal_history_json"]
        )
        self.env.cr.execute(
            "SELECT state, revision, proposal_revision, mapping_rules_json, proposal_history_json "
            "FROM office_mapping_session WHERE id = %s FOR UPDATE",
            [self.id],
        )
        row = self.env.cr.fetchone()
        if not row:
            raise AccessError(_("The mapping session is unavailable."))
        current_state, current_revision, current_proposal_revision, current_rules_json, history_json = row
        if current_revision != expected_revision:
            raise ValidationError(_("MAPPING_REVISION_STALE: reload the mapping card and retry."))
        if target_state != current_state and target_state not in ALLOWED_TRANSITIONS[current_state]:
            raise ValidationError(_("This mapping session state transition is not allowed."))

        new_revision = current_revision + 1
        try:
            history = json.loads(history_json or "[]")
            previous_rules = json.loads(current_rules_json or "{}")
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValidationError(_("The Proposal history is invalid.")) from exc
        if not isinstance(history, list) or any(
            not isinstance(entry, dict)
            or set(entry) != {"proposal_revision", "mapping_rules"}
            or type(entry["proposal_revision"]) is not int
            or not isinstance(entry["mapping_rules"], dict)
            for entry in history
        ):
            raise ValidationError(_("The Proposal history is invalid."))
        old_canonical = json.dumps(previous_rules, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        new_canonical = json.dumps(rules, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if current_proposal_revision > 0 and old_canonical != new_canonical:
            history = [
                entry for entry in history
                if entry["proposal_revision"] != current_proposal_revision
            ]
            history.append(
                {"proposal_revision": current_proposal_revision, "mapping_rules": previous_rules}
            )
        history = sorted(history, key=lambda entry: entry["proposal_revision"])[-20:]
        values = {
                "mapping_rules_json": json.dumps(rules, ensure_ascii=False, separators=(",", ":")),
                "proposal_history_json": json.dumps(history, ensure_ascii=False, separators=(",", ":")),
                "confirmed_revision": 0,
                "proposal_revision": current_proposal_revision + 1,
                "preview_proposal_revision": 0,
                "preview_attachment_id": False,
                "preview_data_fingerprint": False,
                "pending_cell_override_json": False,
                "final_request_uuid": False,
                "state": target_state,
                "revision": new_revision,
                "error_code": False,
            }
        if data_fingerprint is not None:
            values["proposal_data_fingerprint"] = data_fingerprint
        super(OfficeMappingSession, self).write(values)
        self.invalidate_recordset(
            ["mapping_rules_json", "proposal_history_json", "confirmed_revision", "proposal_revision", "proposal_data_fingerprint", "preview_proposal_revision", "state", "revision", "error_code", "final_request_uuid", "pending_cell_override_json"]
        )
        return {"session_id": self.id, "state": target_state, "revision": new_revision}

    def _set_pending_cell_override_from_service(self, pending_json, expected_revision):
        """Persist a scoped write-risk confirmation without changing the mapping revision."""
        self.ensure_one()
        self.check_access("write")
        try:
            pending = json.loads(pending_json)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValidationError(_("Invalid Office operation confirmation.")) from exc
        required = {
            "thread_id",
            "user_id",
            "request_message_id",
            "revision",
            "proposal_revision",
            "preview_attachment_id",
            "template_fingerprint",
            "context_fingerprint",
            "document_fingerprint",
            "cell_edits",
            "observed_values",
        }
        optional = {"operation_scope", "risks"}
        if (
            not isinstance(pending, dict)
            or not required.issubset(pending)
            or set(pending) - required - optional
            or ("operation_scope" in pending and not isinstance(pending["operation_scope"], dict))
            or ("risks" in pending and not isinstance(pending["risks"], list))
        ):
            raise ValidationError(_("Invalid Office operation confirmation."))
        if (
            type(expected_revision) is not int
            or type(pending["thread_id"]) is not int
            or type(pending["user_id"]) is not int
            or type(pending["request_message_id"]) is not int
            or type(pending["revision"]) is not int
            or type(pending["proposal_revision"]) is not int
            or pending["revision"] != expected_revision
            or pending["thread_id"] != self.thread_id.id
            or pending["user_id"] != self.owner_id.id
            or not isinstance(pending["cell_edits"], list)
            or not isinstance(pending["observed_values"], dict)
            or (
                not pending["cell_edits"]
                and not pending.get("risks")
            )
            or (
                not pending["cell_edits"]
                and not pending.get("operation_scope")
            )
        ):
            raise ValidationError(_("Invalid Office operation confirmation."))
        self.flush_recordset(["revision", "proposal_revision"])
        self.env.cr.execute(
            "SELECT revision, proposal_revision FROM office_mapping_session WHERE id = %s FOR UPDATE",
            [self.id],
        )
        row = self.env.cr.fetchone()
        if not row or row[0] != expected_revision or row[1] != pending["proposal_revision"]:
            raise ValidationError(_("MAPPING_REVISION_STALE: the mapping changed before overwrite confirmation."))
        super(OfficeMappingSession, self).write(
            {"pending_cell_override_json": json.dumps(pending, ensure_ascii=False, sort_keys=True, separators=(",", ":"))}
        )
        self.invalidate_recordset(["pending_cell_override_json"])
        return True

    def _clear_pending_cell_override_from_service(self, expected_revision):
        """Clear a consumed or superseded overwrite confirmation under revision lock."""
        self.ensure_one()
        self.check_access("write")
        if type(expected_revision) is not int or expected_revision < 1:
            raise ValidationError(_("Invalid mapping session revision."))
        self.flush_recordset(["revision"])
        self.env.cr.execute(
            "SELECT revision FROM office_mapping_session WHERE id = %s FOR UPDATE",
            [self.id],
        )
        row = self.env.cr.fetchone()
        if not row:
            raise AccessError(_("The mapping session is unavailable."))
        if row[0] != expected_revision:
            raise ValidationError(_("MAPPING_REVISION_STALE: the mapping changed before confirmation was cleared."))
        super(OfficeMappingSession, self).write({"pending_cell_override_json": False})
        self.invalidate_recordset(["pending_cell_override_json"])
        return True

    def _store_preview_from_service(
        self, attachment, expected_revision, data_fingerprint, template_fingerprint
    ):
        """Bind a completed, verified preview to the exact proposal under a short row lock."""
        self.ensure_one()
        self.check_access("write")
        attachment.ensure_one()
        attachment.check_access("read")
        if not re.fullmatch(r"[0-9a-f]{64}", data_fingerprint or ""):
            raise ValidationError(_("Invalid preview data fingerprint."))
        if not re.fullmatch(r"[0-9a-f]{64}", template_fingerprint or ""):
            raise ValidationError(_("Invalid template fingerprint."))
        self.flush_recordset(["revision", "proposal_revision", "state"])
        self.env.cr.execute(
            "SELECT revision, proposal_revision, state FROM office_mapping_session WHERE id = %s FOR UPDATE",
            [self.id],
        )
        row = self.env.cr.fetchone()
        if not row or row[0] != expected_revision:
            raise ValidationError(_("MAPPING_REVISION_STALE: the mapping changed while the preview was being built."))
        if row[2] not in ("revision_pending", "preview_ready", "confirmation_required"):
            raise ValidationError(_("The current mapping cannot accept a preview."))
        if row[2] not in ("preview_ready",) and "preview_ready" not in ALLOWED_TRANSITIONS[row[2]]:
            raise ValidationError(_("This mapping session state transition is not allowed."))
        if attachment.res_model != self._name or attachment.res_id != self.id or attachment.public:
            raise ValidationError(_("The preview attachment must be private and session-bound."))
        values = {
            "preview_attachment_id": attachment.id,
            "pending_cell_override_json": False,
            "preview_proposal_revision": row[1],
            "final_request_uuid": False,
            "template_fingerprint": template_fingerprint,
            "preview_data_fingerprint": data_fingerprint,
            "state": "preview_ready",
            "revision": row[0] + 1,
            "confirmed_revision": 0,
            "error_code": False,
        }
        super(OfficeMappingSession, self).write(values)
        self.invalidate_recordset(values.keys())
        return {"session_id": self.id, "state": "preview_ready", "revision": values["revision"], "proposal_revision": row[1]}

    def _mark_confirmed_from_service(self, expected_revision):
        self.ensure_one()
        self.check_access("write")
        self.flush_recordset(["revision", "proposal_revision", "preview_proposal_revision", "state"])
        self.env.cr.execute(
            "SELECT revision, proposal_revision, preview_proposal_revision, state FROM office_mapping_session WHERE id = %s FOR UPDATE",
            [self.id],
        )
        row = self.env.cr.fetchone()
        if not row or row[0] != expected_revision:
            raise ValidationError(_("MAPPING_REVISION_STALE: reload the current preview."))
        if row[3] != "confirmation_required" or row[1] != row[2]:
            raise ValidationError(_("The current proposal has no matching preview."))
        new_revision = row[0] + 1
        super(OfficeMappingSession, self).write(
            {"state": "confirmed", "confirmed_revision": row[1], "revision": new_revision}
        )
        self.invalidate_recordset(["state", "confirmed_revision", "revision"])
        return {"session_id": self.id, "state": "confirmed", "revision": new_revision, "confirmed_revision": row[1]}

    def _require_confirmation_from_service(self, expected_revision):
        self.ensure_one()
        self.check_access("write")
        self.flush_recordset(["revision", "proposal_revision", "preview_proposal_revision", "state"])
        self.env.cr.execute(
            "SELECT revision, proposal_revision, preview_proposal_revision, state FROM office_mapping_session WHERE id = %s FOR UPDATE",
            [self.id],
        )
        row = self.env.cr.fetchone()
        if not row or row[0] != expected_revision:
            raise ValidationError(_("MAPPING_REVISION_STALE: reload the current preview."))
        if row[3] != "preview_ready" or row[1] != row[2]:
            raise ValidationError(_("The preview no longer matches the current proposal."))
        new_revision = row[0] + 1
        super(OfficeMappingSession, self).write({"state": "confirmation_required", "revision": new_revision})
        self.invalidate_recordset(["state", "revision"])
        return {"session_id": self.id, "state": "confirmation_required", "revision": new_revision}

    def _recover_finalize_failure_from_service(self, expected_revision, final_request_uuid=None):
        """Return a failed generation attempt to its still-valid preview state."""
        self.ensure_one()
        self.check_access("write")
        self.flush_recordset(
            [
                "revision",
                "proposal_revision",
                "preview_proposal_revision",
                "confirmed_revision",
                "preview_attachment_id",
                "state",
                "final_request_uuid",
            ]
        )
        self.env.cr.execute(
            "SELECT revision, proposal_revision, preview_proposal_revision, confirmed_revision, "
            "preview_attachment_id, state, final_request_uuid "
            "FROM office_mapping_session WHERE id = %s FOR UPDATE",
            [self.id],
        )
        row = self.env.cr.fetchone()
        if not row:
            raise AccessError(_("The mapping session is unavailable."))
        (
            revision,
            proposal_revision,
            preview_revision,
            confirmed_revision,
            preview_attachment_id,
            state,
            current_final_request_uuid,
        ) = row
        if revision != expected_revision:
            raise ValidationError(_("MAPPING_REVISION_STALE: reload the current preview."))
        if (
            state != "generating"
            or proposal_revision != preview_revision
            or confirmed_revision != proposal_revision
            or not preview_attachment_id
        ):
            raise ValidationError(_("The verified preview is no longer available for retry."))

        new_revision = revision + 1
        if final_request_uuid not in (None, False) and (
            not isinstance(final_request_uuid, str)
            or not re.fullmatch(
                r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}",
                final_request_uuid,
            )
        ):
            raise ValidationError(_("Invalid retryable Office request reference."))
        retry_request_uuid = (
            False
            if final_request_uuid is False
            else final_request_uuid.lower()
            if final_request_uuid is not None
            else current_final_request_uuid
        )
        super(OfficeMappingSession, self).write(
            {
                "state": "confirmation_required",
                "revision": new_revision,
                "confirmed_revision": 0,
                "error_code": False,
                "final_request_uuid": retry_request_uuid or False,
            }
        )
        self.invalidate_recordset(
            ["state", "revision", "confirmed_revision", "error_code", "final_request_uuid"]
        )
        return {
            "session_id": self.id,
            "state": "confirmation_required",
            "revision": new_revision,
            "proposal_revision": proposal_revision,
        }

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
        if current_state != "confirmation_required":
            raise ValidationError(_("The mapping session cannot be confirmed in its current state."))
        if self.preview_proposal_revision != self.proposal_revision:
            raise ValidationError(_("This mapping session state transition is not allowed."))
        new_revision = current_revision + 1
        super(OfficeMappingSession, self).write(
            {
                "state": "confirmed",
                "revision": new_revision,
                "confirmed_revision": self.proposal_revision,
            }
        )
        self.invalidate_recordset(["state", "revision", "confirmed_revision"])
        return {
            "session_id": self.id,
            "state": "confirmed",
            "revision": new_revision,
            "confirmed_revision": self.proposal_revision,
        }
