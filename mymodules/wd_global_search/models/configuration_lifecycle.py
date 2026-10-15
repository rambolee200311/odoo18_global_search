import hashlib
import json

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

MAX_SNAPSHOT_BYTES = 1024 * 1024
SUPPORTED_CONFIG_SCHEMA = 1

class ConfigurationMutationMixin(models.AbstractModel):
    _name = "wd.gs.configuration.mutation.mixin"
    _description = "Global Search Configuration Mutation Tracking"

    def _configuration_scope(self):
        Resource = self.env["wd.gs.business.resource"]
        if self._name == "wd.gs.config.domain":
            versions = self.mapped("version_ids")
            return versions, versions.mapped("resource_ids")
        if self._name == "wd.gs.business.resource":
            return self.mapped("version_id"), self
        if "resource_id" in self._fields and self.mapped("resource_id"):
            resources = self.mapped("resource_id")
            return resources.mapped("version_id"), resources
        if "mapping_id" in self._fields:
            resources = self.mapped("mapping_id.resource_id")
            return resources.mapped("version_id"), resources
        if "version_id" in self._fields:
            return self.mapped("version_id"), Resource
        return self.env["wd.gs.config.version"], Resource

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        versions, resources = records._configuration_scope()
        versions._mark_pending_changes(
            resources=resources,
            global_change=not bool(resources) or records._name == "wd.gs.config.domain",
            source_model=records._name,
            changed_fields=set().union(*(values.keys() for values in vals_list)),
        )
        return records

    def write(self, vals):
        old_versions, old_resources = self._configuration_scope()
        result = super().write(vals)
        if self.env.context.get("wd_gs_internal_apply"):
            return result
        new_versions, new_resources = self._configuration_scope()
        versions = old_versions | new_versions
        resources = old_resources | new_resources
        versions._mark_pending_changes(
            resources=resources,
            global_change=not bool(resources) or self._name == "wd.gs.config.domain",
            source_model=self._name,
            changed_fields=vals.keys(),
        )
        return result

    def unlink(self):
        versions, resources = self._configuration_scope()
        result = super().unlink()
        versions._mark_pending_changes(
            resources=resources,
            global_change=not bool(resources.exists()) or self._name == "wd.gs.config.domain",
            source_model=self._name,
            changed_fields=("unlink",),
        )
        return result

class ConfigurationDomain(models.Model):
    _name = "wd.gs.config.domain"
    _inherit = ["wd.gs.configuration.mutation.mixin"]
    _description = "Global Search Configuration Domain"
    _order = "name, id"

    key = fields.Char(required=True, index=True)
    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
    pending_active = fields.Boolean(readonly=True, copy=False)
    pending_active_set = fields.Boolean(readonly=True, copy=False)
    version_ids = fields.One2many("wd.gs.config.version", "domain_id", string="Versions")

    _sql_constraints = [
        ("key_unique", "unique(key)", "Configuration domain keys must be unique."),
    ]

    def write(self, vals):
        if (
            {"pending_active", "pending_active_set"}.intersection(vals)
            and not self.env.context.get("wd_gs_internal_apply")
        ):
            raise UserError(_("Pending domain activity can only be changed through configuration actions."))
        if "key" in vals and any(record.version_ids for record in self):
            raise UserError(_("A configuration domain key cannot change after versions exist."))
        if "active" in vals and not self.env.context.get("wd_gs_internal_apply"):
            for record in self:
                record_vals = dict(vals)
                if record.version_ids.filtered(lambda item: item.state == "published"):
                    super(ConfigurationDomain, record).write(
                        {
                            "pending_active": vals["active"],
                            "pending_active_set": True,
                        }
                    )
                    record_vals.pop("active", None)
                if record_vals:
                    super(ConfigurationDomain, record).write(record_vals)
            return True
        return super().write(vals)

class ConfigurationVersion(models.Model):
    _name = "wd.gs.config.version"
    _description = "Global Search Configuration Version"
    _order = "domain_id, version desc"

    domain_id = fields.Many2one(
        "wd.gs.config.domain", required=True, ondelete="restrict", index=True
    )
    version = fields.Integer(required=True, default=1)
    schema_version = fields.Integer(required=True, default=SUPPORTED_CONFIG_SCHEMA)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("validating", "Validating"),
            ("published", "Published"),
            ("retired", "Retired"),
            ("rejected", "Rejected"),
        ],
        required=True,
        default="draft",
        index=True,
    )
    checksum = fields.Char(readonly=True, copy=False, index=True)
    snapshot_json = fields.Text(readonly=True, copy=False)
    snapshot_size = fields.Integer(readonly=True, copy=False)
    published_at = fields.Datetime(readonly=True, copy=False)
    published_by = fields.Many2one("res.users", readonly=True, copy=False)
    rejection_code = fields.Char(readonly=True, copy=False)
    rejection_message = fields.Text(readonly=True, copy=False)
    pending_changes = fields.Boolean(readonly=True, copy=False)
    pending_global_changes = fields.Boolean(readonly=True, copy=False)
    pending_resource_ids = fields.Many2many(
        "wd.gs.business.resource",
        "wd_gs_config_version_pending_resource_rel",
        "version_id",
        "resource_id",
        readonly=True,
        copy=False,
    )

    resource_ids = fields.One2many("wd.gs.business.resource", "version_id")
    vocabulary_ids = fields.One2many("wd.gs.vocabulary.entry", "version_id")
    scoring_ids = fields.One2many("wd.gs.entity.scoring.config", "version_id")
    performance_ids = fields.One2many("wd.gs.performance.config", "version_id")

    _sql_constraints = [
        (
            "domain_version_unique",
            "unique(domain_id, version)",
            "Configuration versions must be unique within a domain.",
        ),
        (
            "schema_version_positive",
            "check(schema_version > 0)",
            "Configuration schema version must be positive.",
        ),
    ]

    def write(self, vals):
        protected_fields = {
            "version",
            "domain_id",
            "state",
            "checksum",
            "snapshot_json",
            "snapshot_size",
            "published_at",
            "published_by",
            "rejection_code",
            "rejection_message",
            "pending_changes",
            "pending_global_changes",
            "pending_resource_ids",
        }
        if protected_fields.intersection(vals):
            raise UserError(_("Use the configuration lifecycle actions to change version metadata."))
        result = super().write(vals)
        if "schema_version" in vals:
            self._mark_pending_changes(
                source_model=self._name,
                changed_fields=vals.keys(),
                global_change=True,
            )
        if "resource_ids" in vals:
            self._mark_pending_changes(
                resources=self.mapped("resource_ids"),
                source_model=self._name,
                changed_fields=vals.keys(),
            )
        return result

    def unlink(self):
        if any(record.state in ("published", "retired") for record in self):
            raise UserError(_("Published and Retired versions cannot be deleted."))
        return super().unlink()

    def _write_internal(self, vals):
        return super(ConfigurationVersion, self).write(vals)

    def _mark_pending_changes(
        self, resources=None, global_change=False, source_model=None, changed_fields=()
    ):
        resources = (resources or self.env["wd.gs.business.resource"]).exists()
        fields_changed = ", ".join(sorted(str(name) for name in changed_fields))
        for version in self.filtered(lambda item: item.state in ("published", "retired")):
            affected = (
                self.env["wd.gs.business.resource"]
                if global_change
                else resources.filtered(lambda item: item.version_id == version)
            )
            global_pending = global_change or not affected
            values = {"pending_changes": True}
            if global_pending:
                values["pending_global_changes"] = True
            if affected:
                values["pending_resource_ids"] = [(4, item.id) for item in affected]
            version._write_internal(values)
            self.env["wd.gs.audit.event"].create(
                {
                    "action": "stage",
                    "domain_id": version.domain_id.id,
                    "version_id": version.id,
                    "previous_checksum": version.checksum,
                    "checksum": version.checksum,
                    "message": _(
                        "Staged configuration edit to %(model)s (%(fields)s)."
                    )
                    % {
                        "model": source_model or "configuration",
                        "fields": fields_changed or "records",
                    },
                }
            )

    def action_apply_changes(self):
        self.check_access("write")
        for version in self:
            if version.state not in ("published", "retired"):
                raise UserError(_("Only Published or Retired versions can apply staged changes."))
            if not version.pending_changes:
                raise UserError(_("There are no staged configuration changes to apply."))
            try:
                version._validate_configuration()
                snapshot_json = json.dumps(
                    version._build_snapshot(),
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                snapshot_size = len(snapshot_json.encode("utf-8"))
                if snapshot_size > MAX_SNAPSHOT_BYTES:
                    raise ValidationError(_("Configuration snapshot exceeds the 1 MB limit."))
            except (ValidationError, UserError) as error:
                self.env["wd.gs.audit.event"].create(
                    {
                        "action": "apply_rejected",
                        "domain_id": version.domain_id.id,
                        "version_id": version.id,
                        "previous_checksum": version.checksum,
                        "checksum": version.checksum,
                        "error_code": "CONFIGURATION_ERROR",
                        "message": str(error),
                    }
                )
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": _("Configuration not applied"),
                        "message": str(error),
                        "type": "danger",
                        "sticky": True,
                    },
                }

            previous_checksum = version.checksum
            checksum = hashlib.sha256(snapshot_json.encode("utf-8")).hexdigest()
            version._write_internal(
                {
                    "snapshot_json": snapshot_json,
                    "snapshot_size": snapshot_size,
                    "checksum": checksum,
                    "pending_changes": False,
                    "pending_global_changes": False,
                    "pending_resource_ids": [(5, 0, 0)],
                }
            )
            if version.state == "published" and version.domain_id.pending_active_set:
                version.domain_id.with_context(wd_gs_internal_apply=True).write(
                    {
                        "active": version.domain_id.pending_active,
                        "pending_active": False,
                        "pending_active_set": False,
                    }
                )
            self.env["wd.gs.audit.event"].create(
                {
                    "action": "apply",
                    "domain_id": version.domain_id.id,
                    "version_id": version.id,
                    "previous_checksum": previous_checksum,
                    "checksum": checksum,
                    "message": _("Applied staged configuration changes."),
                }
            )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Configuration updated"),
                "message": _("Staged changes are now active."),
                "type": "success",
                "sticky": False,
            },
        }

    def action_validate(self):
        for record in self:
            record._assert_editable()
            record._write_internal(
                {"state": "validating", "rejection_code": False, "rejection_message": False}
            )
            try:
                record._validate_configuration()
            except (ValidationError, UserError) as error:
                record._reject("CONFIGURATION_ERROR", str(error))
                return False
        return True

    def action_publish(self):
        for record in self:
            record._assert_editable()
            try:
                record._validate_configuration()
                record._assert_single_published()
                snapshot = record._build_snapshot()
                snapshot_json = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                snapshot_size = len(snapshot_json.encode("utf-8"))
                if snapshot_size > MAX_SNAPSHOT_BYTES:
                    raise ValidationError(_("Configuration snapshot exceeds the 1 MB limit."))
                checksum = hashlib.sha256(snapshot_json.encode("utf-8")).hexdigest()
            except (ValidationError, UserError) as error:
                record._reject("CONFIGURATION_ERROR", str(error))
                return False

            previous = self.search(
                [
                    ("domain_id", "=", record.domain_id.id),
                    ("state", "=", "published"),
                    ("id", "!=", record.id),
                ],
                limit=1,
            )
            if previous:
                previous._write_internal({"state": "retired"})
                self.env["wd.gs.audit.event"].create(
                    {
                        "action": "retire",
                        "domain_id": record.domain_id.id,
                        "version_id": previous.id,
                        "checksum": previous.checksum,
                    }
                )
            record._write_internal(
                {
                    "state": "published",
                    "checksum": checksum,
                    "snapshot_json": snapshot_json,
                    "snapshot_size": snapshot_size,
                    "published_at": fields.Datetime.now(),
                    "published_by": self.env.user.id,
                    "rejection_code": False,
                    "rejection_message": False,
                    "pending_changes": False,
                    "pending_global_changes": False,
                    "pending_resource_ids": [(5, 0, 0)],
                }
            )
            self.env["wd.gs.audit.event"].create(
                {
                    "action": "publish",
                    "domain_id": record.domain_id.id,
                    "version_id": record.id,
                    "checksum": checksum,
                }
            )
        return True

    def action_retire(self):
        for record in self:
            if record.state != "published":
                raise UserError(_("Only a Published configuration can be retired."))
            record._write_internal({"state": "retired"})
            self.env["wd.gs.audit.event"].create(
                {
                    "action": "retire",
                    "domain_id": record.domain_id.id,
                    "version_id": record.id,
                    "checksum": record.checksum,
                }
            )
        return True

    def _assert_editable(self):
        if any(record.state in ("published", "retired") for record in self):
            raise UserError(_("Published and Retired versions cannot be validated or republished."))

    def _assert_single_published(self):
        published = self.search(
            [
                ("domain_id", "=", self.domain_id.id),
                ("state", "=", "published"),
                ("id", "!=", self.id),
            ],
            limit=1,
        )
        if published:
            return

    def _reject(self, code, message):
        self._write_internal(
            {
                "state": "rejected",
                "rejection_code": code,
                "rejection_message": message,
            }
        )
        self.env["wd.gs.audit.event"].create(
            {
                "action": "reject",
                "domain_id": self.domain_id.id,
                "version_id": self.id,
                "error_code": code,
                "message": message,
            }
        )

    def _validate_configuration(self):
        if self.schema_version != SUPPORTED_CONFIG_SCHEMA:
            raise ValidationError(_("Unsupported configuration schema version."))
        if not self.resource_ids:
            raise ValidationError(_("At least one Business Resource is required."))
        for resource in self.resource_ids:
            resource._validate_configuration()
        for scoring in self.scoring_ids:
            scoring._validate_configuration()
        for performance in self.performance_ids:
            performance._validate_configuration()
        resource_keys = set(self.resource_ids.mapped("key"))
        performance_by_resource = {}
        for performance in self.performance_ids:
            if performance.resource_key not in resource_keys:
                raise ValidationError(
                    _("Performance configuration references an unknown Resource.")
                )
            if performance.resource_key in performance_by_resource:
                raise ValidationError(
                    _("A Resource may have only one Performance configuration.")
                )
            performance_by_resource[performance.resource_key] = performance
        for resource in self.resource_ids:
            max_relation_depth = performance_by_resource.get(
                resource.key
            ).max_relation_depth if resource.key in performance_by_resource else 2
            fields_to_validate = (
                resource.searchable_field_ids
                | resource.model_mapping_ids.mapped("searchable_field_ids")
            )
            for searchable_field in fields_to_validate:
                searchable_field._validate_configuration(
                    max_relation_depth=max_relation_depth
                )

    def _build_snapshot(self):
        self.ensure_one()
        return {
            "schema_version": self.schema_version,
            "domain": {"key": self.domain_id.key, "name": self.domain_id.name},
            "version": self.version,
            "resources": [resource._snapshot_values() for resource in self.resource_ids],
            "vocabulary": [
                {"lang": entry.lang, "term": entry.term, "value": entry.value}
                for entry in self.vocabulary_ids
            ],
            "scoring": [
                {
                    "resource_key": item.resource_key,
                    "threshold": item.threshold,
                    "candidate_limit": item.candidate_limit,
                    "weight": item.weight,
                }
                for item in self.scoring_ids
            ],
            "performance": [
                {
                    "resource_key": item.resource_key,
                    "max_results": item.max_results,
                    "resource_timeout": item.resource_timeout,
                    "request_timeout": item.request_timeout,
                    "max_relation_depth": item.max_relation_depth,
                }
                for item in self.performance_ids
            ],
        }
