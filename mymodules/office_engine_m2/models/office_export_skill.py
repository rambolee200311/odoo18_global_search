"""Private, value-free Office export mapping assets."""

import json
import re

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError


_FINGERPRINT = re.compile(r"^[0-9a-f]{64}$")
_CREATE_FROM_SERVICE = "_office_engine_m2_private_skill_create"
_MAX_RULE_BYTES = 256 * 1024


class OfficeExportSkill(models.Model):
    _name = "office.export.skill"
    _description = "Private Office Export Mapping Skill"
    _order = "write_date desc, id desc"

    name = fields.Char(required=True, readonly=True, copy=False, size=128, index=True)
    owner_id = fields.Many2one(
        "res.users", required=True, readonly=True, copy=False, index=True, ondelete="restrict"
    )
    company_id = fields.Many2one(
        "res.company", required=True, readonly=True, copy=False, index=True, ondelete="restrict"
    )
    template_fingerprint = fields.Char(
        required=True, readonly=True, copy=False, size=64, index=True
    )
    model_name = fields.Char(required=True, readonly=True, copy=False, size=128, index=True)
    mapping_rules_json = fields.Text(required=True, readonly=True, copy=False)
    state = fields.Selection(
        [
            ("active", "Active"),
            ("pending_validation", "Pending Validation"),
            ("disabled", "Disabled"),
        ],
        required=True,
        readonly=True,
        copy=False,
        default="active",
        index=True,
    )
    revision = fields.Integer(required=True, readonly=True, copy=False, default=1)

    _sql_constraints = [
        (
            "fingerprint_sha256",
            "CHECK(template_fingerprint ~ '^[0-9a-f]{64}$')",
            "A template fingerprint must be a lowercase SHA-256 digest.",
        ),
        ("revision_positive", "CHECK(revision > 0)", "Skill revision must be positive."),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        # Ordinary users have read-only ACLs. The only create path is the
        # private service after it has verified a completed, delivered M1 run.
        if not self.env.su or not self.env.context.get(_CREATE_FROM_SERVICE):
            raise AccessError(_("Private Skills can only be created by the validated service."))
        allowed = {
            "name",
            "owner_id",
            "company_id",
            "template_fingerprint",
            "model_name",
            "mapping_rules_json",
            "state",
            "revision",
        }
        for vals in vals_list:
            if not isinstance(vals, dict) or set(vals) != allowed:
                raise ValidationError(_("Invalid private Skill data."))
            if (
                not isinstance(vals["name"], str)
                or not vals["name"].strip()
                or len(vals["name"]) > 128
                or not isinstance(vals["model_name"], str)
                or not vals["model_name"].strip()
                or len(vals["model_name"]) > 128
                or not isinstance(vals["template_fingerprint"], str)
                or not _FINGERPRINT.fullmatch(vals["template_fingerprint"])
                or vals["state"] != "active"
                or vals["revision"] != 1
                or vals["owner_id"] != self.env.uid
                or vals["company_id"] != self.env.company.id
                or not isinstance(vals["mapping_rules_json"], str)
                or len(vals["mapping_rules_json"].encode("utf-8")) > _MAX_RULE_BYTES
            ):
                raise ValidationError(_("Invalid private Skill data."))
            try:
                proposal = json.loads(vals["mapping_rules_json"])
            except (TypeError, json.JSONDecodeError) as exc:
                raise ValidationError(_("Invalid private Skill mapping rules.")) from exc
            if not isinstance(proposal, dict) or set(proposal) not in (
                {"schema_version", "mappings", "clarifications", "skipped_targets"},
                {"schema_version", "mappings", "clarifications", "skipped_targets", "clear_targets"},
            ):
                raise ValidationError(_("Invalid private Skill mapping rules."))
            if "clear_targets" in proposal and (
                not isinstance(proposal["clear_targets"], list)
                or any(not isinstance(item, str) or not item.strip() for item in proposal["clear_targets"])
            ):
                raise ValidationError(_("Invalid private Skill mapping rules."))
            for mapping in proposal.get("mappings", []):
                if not isinstance(mapping, dict) or set(mapping) != {
                    "element_id", "source_field", "value_type"
                }:
                    raise ValidationError(_("Private Skill rules cannot contain business values."))
        return super().create(vals_list)

    def write(self, vals):
        raise AccessError(_("Private Skill rules are immutable in this version."))

    def unlink(self):
        raise AccessError(_("Private Skills cannot be deleted through this interface."))
