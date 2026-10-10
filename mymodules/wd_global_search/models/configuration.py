import ast
import hashlib
import json

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


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


class BusinessResource(models.Model):
    _name = "wd.gs.business.resource"
    _inherit = ["wd.gs.configuration.mutation.mixin"]
    _description = "Global Search Business Resource"

    version_id = fields.Many2one("wd.gs.config.version", required=True, ondelete="cascade", index=True)
    key = fields.Char(required=True, index=True)
    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
    composite = fields.Boolean(default=False)
    primary_model_id = fields.Many2one(
        "ir.model",
        string="Primary Model",
        help="The model searched by this single-model Resource. Composite Resources use Model Mappings instead.",
    )
    primary_model_name = fields.Char(related="primary_model_id.model")
    navigation_action_id = fields.Many2one(
        "ir.actions.act_window",
        string="Result Form Action",
        ondelete="restrict",
        help="Window Action for the Primary Model. Its Form View and group restrictions are preserved.",
    )
    result_identity_scope = fields.Selection(
        [("resource", "Resource"), ("model", "Technical Model")],
        required=True,
        default="resource",
    )
    model_mapping_ids = fields.One2many("wd.gs.resource.model.mapping", "resource_id")
    searchable_field_ids = fields.One2many("wd.gs.searchable.field", "resource_id")
    relation_path_ids = fields.One2many("wd.gs.relation.path", "resource_id")
    business_date_ids = fields.One2many("wd.gs.business.date.mapping", "resource_id")
    state_mapping_ids = fields.One2many("wd.gs.state.mapping", "resource_id")
    snapshot_field_ids = fields.One2many("wd.gs.snapshot.field", "resource_id")

    _sql_constraints = [
        ("version_key_unique", "unique(version_id, key)", "Business resource keys must be unique per version."),
    ]

    def init(self):
        self.env.cr.execute(
            """
            UPDATE wd_gs_config_version AS version
               SET pending_changes = TRUE,
                   pending_global_changes = TRUE
             WHERE version.state IN ('published', 'retired')
               AND EXISTS (
                    SELECT 1
                      FROM wd_gs_business_resource AS resource
                      JOIN wd_gs_resource_model_mapping AS model_mapping
                        ON model_mapping.resource_id = resource.id
                     WHERE resource.version_id = version.id
                       AND resource.composite = FALSE
               )
            """
        )
        self.env.cr.execute(
            """
            UPDATE wd_gs_business_resource AS resource
               SET primary_model_id = ir_model.id
              FROM (
                    SELECT resource_id, MIN(model_name) AS model_name
                      FROM wd_gs_resource_model_mapping
                     GROUP BY resource_id
                    HAVING COUNT(*) = 1
                   ) AS legacy_mapping
              JOIN ir_model ON ir_model.model = legacy_mapping.model_name
             WHERE resource.id = legacy_mapping.resource_id
               AND resource.composite = FALSE
               AND resource.primary_model_id IS NULL
            """
        )
    def _validate_configuration(self):
        self.ensure_one()
        priorities = self.model_mapping_ids.mapped("priority")
        if len(priorities) != len(set(priorities)):
            raise ValidationError(_("Technical model priorities must be unique for %s.") % self.key)
        if not self.business_date_ids:
            raise ValidationError(_("Business Date is not configured for %s.") % self.key)
        if not self.snapshot_field_ids:
            raise ValidationError(_("At least one Card field is required for %s.") % self.key)
        if not self.composite:
            if not self.primary_model_id or self.model_mapping_ids:
                raise ValidationError(
                    _("A single-model Resource must have a Primary Model and no Model Mappings.")
                )
            if not self.navigation_action_id:
                raise ValidationError(
                    _("A Form Action is required for single-model Resource %s.") % self.key
                )
            self._validate_navigation_action()
        elif (
            self.primary_model_id
            or len(self.model_mapping_ids) < 2
            or self.navigation_action_id
            or self.searchable_field_ids
        ):
            raise ValidationError(
                _("Composite Resources use Model Mappings and cannot define a Primary Model or single-model Action.")
            )
        sequences = self.snapshot_field_ids.mapped("sequence")
        if any(sequence <= 0 for sequence in sequences):
            raise ValidationError(_("Card field sequence must be positive."))
        if len(sequences) != len(set(sequences)):
            raise ValidationError(
                _("Card field sequences must be unique for Resource %s.") % self.key
            )
        if not self.snapshot_field_ids or not any(
            item.visible for item in self.snapshot_field_ids
        ):
            raise ValidationError(
                _("At least one visible Card field is required for Resource %s.") % self.key
            )
        for snapshot_field in self.snapshot_field_ids:
            snapshot_field._validate_for_resource(self)
        for mapping in self.model_mapping_ids:
            mapping._validate_configuration()
        searchable_fields = (
            self.model_mapping_ids.mapped("searchable_field_ids")
            | self.searchable_field_ids
        )
        direct_field_names = self.searchable_field_ids.filtered(
            lambda item: not item.mapping_id
        ).mapped("field_name")
        if len(direct_field_names) != len(set(direct_field_names)):
            raise ValidationError(_("Searchable fields must be unique per Primary Model."))
        for field in searchable_fields:
            field._validate_configuration()
        for path in self.relation_path_ids:
            path._validate_configuration()
        for business_date in self.business_date_ids:
            business_date._validate_configuration()

    def _validate_navigation_action(self):
        self.ensure_one()
        action = self.navigation_action_id
        model_name = self.primary_model_id.model
        if not model_name:
            raise ValidationError(_("Select a Primary Model before configuring its Form Action."))
        if action.type != "ir.actions.act_window":
            raise ValidationError(_("Result Action must be an Odoo Window Action."))
        if action.res_model != model_name:
            raise ValidationError(
                _("Result Action model must match Resource %s.") % self.key
            )
        if "form" not in (action.view_mode or "").split(","):
            raise ValidationError(_("Result Action must provide a Form View."))
        if action.target not in ("current", "main"):
            raise ValidationError(
                _("Result Action must open the Form in the current browser client.")
            )
        for expression in (action.context or "{}", action.domain or "[]"):
            try:
                expression_tree = ast.parse(expression, mode="eval")
            except SyntaxError as exc:
                raise ValidationError(
                    _("Result Action Context and Domain must be valid expressions.")
                ) from exc
            if any(
                isinstance(node, ast.Name)
                and node.id in {"active_id", "active_ids", "active_model"}
                for node in ast.walk(expression_tree)
            ):
                raise ValidationError(
                    _(
                        "Result Action Context and Domain cannot depend on "
                        "active_id, active_ids, or active_model."
                    )
                )
        form_action_views = action.view_ids.filtered(
            lambda item: item.view_mode == "form"
        )
        configured_view = (
            form_action_views[:1].view_id
            or (action.view_id if action.view_id.type == "form" else self.env["ir.ui.view"])
        )
        if configured_view and (
            configured_view.model != model_name or configured_view.type != "form"
        ):
            raise ValidationError(
                _("Result Action Form View must match Resource %s.") % self.key
            )
        try:
            view = self.env[model_name].get_view(
                view_id=configured_view.id if configured_view else False,
                view_type="form",
            )
        except (AccessError, UserError, ValidationError) as exc:
            raise ValidationError(
                _("Result Action Form View is unavailable for Resource %s.") % self.key
            ) from exc
        if not view.get("arch"):
            raise ValidationError(
                _("Result Action Form View is unavailable for Resource %s.") % self.key
            )

    def _navigation_action_snapshot(self):
        self.ensure_one()
        action = self.navigation_action_id
        if not action:
            return None
        form_action_views = action.view_ids.filtered(
            lambda item: item.view_mode == "form"
        )
        form_view = form_action_views[:1].view_id
        if not form_view and action.view_id.type == "form":
            form_view = action.view_id
        return {
            "id": action.id,
            "res_model": action.res_model,
            "view_mode": action.view_mode,
            "view_id": form_view.id or None,
            "target": action.target,
            "groups": sorted(action.groups_id.ids),
            "context": action.context or "{}",
            "domain": action.domain or "[]",
        }

    def _snapshot_values(self):
        self.ensure_one()
        languages = self.env["res.lang"].search([("active", "=", True)])

        def translated(value, field_name):
            result = {
                language.code: value.with_context(lang=language.code)[field_name]
                for language in languages
            }
            result.setdefault(
                "en_US",
                value.with_context(lang="en_US")[field_name]
                or value[field_name],
            )
            return result

        return {
            "key": self.key,
            "name": self.name,
            "name_translations": translated(self, "name"),
            "active": self.active,
            "composite": self.composite,
            "result_identity_scope": self.result_identity_scope,
            "navigation_action_id": self.navigation_action_id.id or None,
            "navigation_action": self._navigation_action_snapshot(),
            "models": (
                [
                    {
                        "model_name": self.primary_model_id.model,
                        "priority": 1,
                        "fields": [
                            {
                                "name": field.field_name,
                                "purpose": field.purpose,
                                "operator_set": field.operator_set,
                                "index_strategy": field.index_strategy,
                            }
                            for field in self.searchable_field_ids
                        ],
                    }
                ]
                if not self.composite
                else [
                    {
                        "model_name": mapping.model_name,
                        "priority": mapping.priority,
                        "fields": [
                            {
                                "name": field.field_name,
                                "purpose": field.purpose,
                                "operator_set": field.operator_set,
                                "index_strategy": field.index_strategy,
                            }
                            for field in mapping.searchable_field_ids
                        ],
                    }
                    for mapping in self.model_mapping_ids
                ]
            ),
            "relation_paths": [
                {"path": path.path, "max_depth": path.max_depth}
                for path in self.relation_path_ids
            ],
            "business_dates": [
                {
                    "model_name": item.model_name,
                    "field_name": item.field_name,
                    "timezone_behavior": item.timezone_behavior,
                    "empty_date_policy": item.empty_date_policy,
                }
                for item in self.business_date_ids
            ],
            "states": [
                {
                    "business_state": item.business_state,
                    "technical_values": item.technical_values,
                }
                for item in self.state_mapping_ids
            ],
            "snapshot_fields": [
                {
                    "field_name": item.field_name,
                    "label": item.label,
                    "labels": translated(item, "label"),
                    "sequence": item.sequence,
                    "visible": item.visible,
                    "format_type": item.format_type,
                    "allow_empty": item.allow_empty,
                }
                for item in self.snapshot_field_ids.sorted(
                    lambda field: (field.sequence, field.id)
                )
            ],
        }


class ResourceModelMapping(models.Model):
    _name = "wd.gs.resource.model.mapping"
    _inherit = ["wd.gs.configuration.mutation.mixin"]
    _description = "Global Search Resource Model Mapping"

    resource_id = fields.Many2one("wd.gs.business.resource", required=True, ondelete="cascade")
    model_name = fields.Char(required=True, index=True)
    priority = fields.Integer(required=True, default=10)
    searchable_field_ids = fields.One2many("wd.gs.searchable.field", "mapping_id")

    _sql_constraints = [
        ("resource_model_unique", "unique(resource_id, model_name)", "A model may only be mapped once per resource."),
        ("priority_positive", "check(priority > 0)", "Model priority must be positive."),
    ]

    def _validate_configuration(self):
        self.ensure_one()
        if self.model_name not in self.env:
            raise ValidationError(_("Technical model %s does not exist.") % self.model_name)


class SearchableField(models.Model):
    _name = "wd.gs.searchable.field"
    _inherit = ["wd.gs.configuration.mutation.mixin"]
    _description = "Global Search Searchable Field"

    resource_id = fields.Many2one("wd.gs.business.resource", ondelete="cascade")
    mapping_id = fields.Many2one("wd.gs.resource.model.mapping", ondelete="cascade")
    field_name = fields.Char(required=True)
    purpose = fields.Selection(
        [("identifier", "Identifier"), ("entity", "Entity"), ("location", "Location"), ("text", "Text")],
        required=True,
    )
    operator_set = fields.Selection(
        [("exact", "Exact"), ("prefix", "Prefix"), ("contains", "Contains")],
        required=True,
        default="exact",
    )
    searchable = fields.Boolean(default=True)
    readable_required = fields.Boolean(default=True)
    index_strategy = fields.Selection(
        [
            ("btree", "B-tree"),
            ("pattern_ops", "text_pattern_ops"),
            ("gin_trgm", "GIN pg_trgm"),
            ("gist_trgm", "GiST pg_trgm"),
            ("none", "None"),
        ],
        required=True,
        default="none",
    )
    weight = fields.Float(default=1.0)

    _sql_constraints = [
        ("mapping_field_unique", "unique(mapping_id, field_name)", "A searchable field may only be configured once."),
        ("weight_non_negative", "check(weight >= 0)", "Field weight must not be negative."),
    ]

    def init(self):
        self.env.cr.execute(
            """
            UPDATE wd_gs_searchable_field AS searchable_field
               SET resource_id = model_mapping.resource_id,
                   mapping_id = NULL
              FROM wd_gs_resource_model_mapping AS model_mapping
              JOIN wd_gs_business_resource AS resource
                ON resource.id = model_mapping.resource_id
             WHERE searchable_field.mapping_id = model_mapping.id
               AND resource.composite = FALSE
               AND resource.primary_model_id IS NOT NULL
            """
        )
        self.env.cr.execute(
            """
            DELETE FROM wd_gs_resource_model_mapping AS model_mapping
             USING wd_gs_business_resource AS resource
             WHERE model_mapping.resource_id = resource.id
               AND resource.composite = FALSE
               AND resource.primary_model_id IS NOT NULL
            """
        )

    def _validate_configuration(self):
        self.ensure_one()
        model_name = (
            self.resource_id.primary_model_id.model
            if self.resource_id and not self.resource_id.composite
            else self.mapping_id.model_name
            if self.mapping_id
            else False
        )
        if not model_name:
            raise ValidationError(_("A searchable field must belong to a Resource model."))
        model = self.env[model_name]
        if self.field_name not in model._fields:
            raise ValidationError(_("Field %s does not exist on %s.") % (self.field_name, model_name))
        compatible = {
            "exact": {"btree", "none"},
            "prefix": {"pattern_ops", "btree", "none"},
            "contains": {"gin_trgm", "gist_trgm", "none"},
        }
        if self.index_strategy not in compatible[self.operator_set]:
            raise ValidationError(
                _("Index strategy %s is incompatible with operator %s.")
                % (self.index_strategy, self.operator_set)
            )


class RelationPath(models.Model):
    _name = "wd.gs.relation.path"
    _inherit = ["wd.gs.configuration.mutation.mixin"]
    _description = "Global Search Relation Path"

    resource_id = fields.Many2one("wd.gs.business.resource", required=True, ondelete="cascade")
    path = fields.Char(required=True)
    max_depth = fields.Integer(required=True, default=2)

    _sql_constraints = [
        ("resource_path_unique", "unique(resource_id, path)", "Relation paths must be unique per resource."),
        ("depth_positive", "check(max_depth > 0)", "Relation path depth must be positive."),
    ]

    def _validate_configuration(self):
        self.ensure_one()
        if len(self.path.split(".")) > self.max_depth:
            raise ValidationError(_("Relation path %s exceeds its configured depth.") % self.path)
        if self.resource_id.composite:
            raise ValidationError(
                _("Relation Paths require one Primary Model; Composite Resources are ambiguous.")
            )
        model_name = self.resource_id.primary_model_id.model
        if not model_name:
            raise ValidationError(_("Select a Primary Model before configuring Relation Paths."))
        for field_name in self.path.split("."):
            model = self.env[model_name]
            relation = model._fields.get(field_name)
            if not relation or relation.type not in {"many2one", "one2many", "many2many"}:
                raise ValidationError(
                    _("Relation Path field %s is not a relation on %s.")
                    % (field_name, model_name)
                )
            model_name = relation.comodel_name


class BusinessDateMapping(models.Model):
    _name = "wd.gs.business.date.mapping"
    _inherit = ["wd.gs.configuration.mutation.mixin"]
    _description = "Global Search Business Date Mapping"

    resource_id = fields.Many2one("wd.gs.business.resource", required=True, ondelete="cascade")
    model_name = fields.Char(required=True)
    field_name = fields.Char(required=True)
    timezone_behavior = fields.Selection(
        [("user", "User timezone"), ("utc", "UTC")], required=True, default="user"
    )
    empty_date_policy = fields.Selection(
        [("exclude", "Exclude"), ("include", "Include")], required=True, default="exclude"
    )

    _sql_constraints = [
        ("resource_model_date_unique", "unique(resource_id, model_name)", "Only one Business Date is allowed per resource model."),
    ]

    def _validate_configuration(self):
        self.ensure_one()
        if self.model_name not in self.env:
            raise ValidationError(_("Technical model %s does not exist.") % self.model_name)
        if self.field_name not in self.env[self.model_name]._fields:
            raise ValidationError(
                _("Business Date field %s does not exist on %s.")
                % (self.field_name, self.model_name)
            )


class StateMapping(models.Model):
    _name = "wd.gs.state.mapping"
    _inherit = ["wd.gs.configuration.mutation.mixin"]
    _description = "Global Search State Mapping"

    resource_id = fields.Many2one("wd.gs.business.resource", required=True, ondelete="cascade")
    business_state = fields.Char(required=True)
    technical_values = fields.Char(required=True)

    _sql_constraints = [
        ("resource_state_unique", "unique(resource_id, business_state)", "Business states must be unique per resource."),
    ]


class SnapshotField(models.Model):
    _name = "wd.gs.snapshot.field"
    _inherit = ["wd.gs.configuration.mutation.mixin"]
    _description = "Global Search Snapshot Field"

    resource_id = fields.Many2one("wd.gs.business.resource", required=True, ondelete="cascade")
    allowed_model_names = fields.Json(
        compute="_compute_allowed_model_names",
        compute_sudo=False,
    )
    field_reference_id = fields.Many2one(
        "ir.model.fields",
        string="Field",
        compute="_compute_field_reference_id",
        inverse="_inverse_field_reference_id",
        compute_sudo=False,
        domain="[('model', 'in', allowed_model_names), "
        "('ttype', 'in', ['char', 'text', 'html', 'selection', 'boolean', "
        "'many2one', 'date', 'datetime', 'integer', 'float', 'monetary'])]",
    )
    field_name = fields.Char(required=True, readonly=True)
    label = fields.Char(required=True, translate=True)
    sequence = fields.Integer(required=True, default=10)
    visible = fields.Boolean(default=True)
    format_type = fields.Selection(
        [("text", "Text"), ("date", "Date"), ("datetime", "Datetime"), ("number", "Number")],
        required=True,
        default="text",
    )
    allow_empty = fields.Boolean(default=True)

    _order = "sequence, id"

    @api.depends(
        "resource_id",
        "resource_id.primary_model_id",
        "resource_id.model_mapping_ids.model_name",
    )
    def _compute_allowed_model_names(self):
        for record in self:
            resource = record.resource_id
            if resource and not resource.composite and resource.primary_model_id:
                record.allowed_model_names = [resource.primary_model_id.model]
            else:
                record.allowed_model_names = (
                    resource.model_mapping_ids.mapped("model_name") if resource else []
                )

    @api.depends(
        "field_name",
        "resource_id",
        "resource_id.primary_model_id",
        "resource_id.model_mapping_ids.model_name",
    )
    def _compute_field_reference_id(self):
        IrModelField = self.env["ir.model.fields"]
        for record in self:
            resource = record.resource_id
            if resource and not resource.composite and resource.primary_model_id:
                model_names = [resource.primary_model_id.model]
            else:
                model_names = resource.model_mapping_ids.mapped("model_name") if resource else []
            reference = IrModelField.search(
                [("model", "in", model_names), ("name", "=", record.field_name)],
                order="model,id",
                limit=1,
            )
            record.field_reference_id = reference.id or False

    def _inverse_field_reference_id(self):
        for record in self:
            record.field_name = record.field_reference_id.name or False

    @api.onchange("field_reference_id")
    def _onchange_field_reference_id(self):
        for record in self:
            if record.field_reference_id:
                record.field_name = record.field_reference_id.name

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        resource_id = values.get("resource_id") or self.env.context.get("default_resource_id")
        if "sequence" in fields_list and resource_id:
            previous = self.search(
                [("resource_id", "=", resource_id)],
                order="sequence desc, id desc",
                limit=1,
            )
            values["sequence"] = (previous.sequence if previous else 0) + 10
        return values

    def _validate_for_resource(self, resource):
        self.ensure_one()
        model_names = (
            resource.model_mapping_ids.mapped("model_name")
            if resource.composite
            else [resource.primary_model_id.model]
        )
        for model_name in model_names:
            model = self.env[model_name]
            field = model._fields.get(self.field_name)
            if not field:
                raise ValidationError(
                    _("Card field %s does not exist on %s.")
                    % (self.field_name, model_name)
                )
            compatible = {
                "text": {"char", "text", "html", "selection", "boolean", "many2one"},
                "date": {"date"},
                "datetime": {"datetime"},
                "number": {"integer", "float", "monetary"},
            }
            if field.type not in compatible[self.format_type]:
                raise ValidationError(
                    _("Card format %s is incompatible with field %s on %s.")
                    % (self.format_type, self.field_name, model_name)
                )


class VocabularyEntry(models.Model):
    _name = "wd.gs.vocabulary.entry"
    _inherit = ["wd.gs.configuration.mutation.mixin"]
    _description = "Global Search Vocabulary Entry"

    version_id = fields.Many2one("wd.gs.config.version", required=True, ondelete="cascade")
    lang = fields.Char(required=True, default=lambda self: self.env.lang)
    term = fields.Char(required=True)
    value = fields.Char(required=True)

    _sql_constraints = [
        ("version_lang_term_unique", "unique(version_id, lang, term)", "Vocabulary terms must be unique per version and language."),
    ]


class EntityScoringConfig(models.Model):
    _name = "wd.gs.entity.scoring.config"
    _inherit = ["wd.gs.configuration.mutation.mixin"]
    _description = "Global Search Entity Scoring Configuration"

    version_id = fields.Many2one("wd.gs.config.version", required=True, ondelete="cascade")
    resource_key = fields.Char(required=True)
    threshold = fields.Float(required=True, default=0.0)
    candidate_limit = fields.Integer(required=True, default=20)
    weight = fields.Float(required=True, default=1.0)

    def _validate_configuration(self):
        self.ensure_one()
        if not 0 <= self.threshold <= 1:
            raise ValidationError(_("Scoring threshold must be between 0 and 1."))
        if self.candidate_limit <= 0 or self.weight < 0:
            raise ValidationError(_("Scoring limits must be positive and weights non-negative."))


class PerformanceConfig(models.Model):
    _name = "wd.gs.performance.config"
    _inherit = ["wd.gs.configuration.mutation.mixin"]
    _description = "Global Search Performance Configuration"

    version_id = fields.Many2one("wd.gs.config.version", required=True, ondelete="cascade")
    resource_key = fields.Char(required=True)
    max_results = fields.Integer(required=True, default=200)
    resource_timeout = fields.Float(required=True, default=3.0)
    request_timeout = fields.Float(required=True, default=5.0)
    max_relation_depth = fields.Integer(required=True, default=2)

    def _validate_configuration(self):
        self.ensure_one()
        if min(
            self.max_results,
            self.resource_timeout,
            self.request_timeout,
            self.max_relation_depth,
        ) <= 0:
            raise ValidationError(_("Performance limits must be positive."))


class AuditEvent(models.Model):
    _name = "wd.gs.audit.event"
    _description = "Global Search Configuration Audit Event"
    _order = "create_date desc, id desc"

    action = fields.Selection(
        [
            ("publish", "Publish"),
            ("retire", "Retire"),
            ("reject", "Reject"),
            ("stage", "Stage"),
            ("apply", "Apply"),
            ("apply_rejected", "Apply Rejected"),
            ("invalidate", "Invalidate"),
            ("upgrade", "Upgrade"),
        ],
        required=True,
    )
    domain_id = fields.Many2one("wd.gs.config.domain", ondelete="set null", index=True)
    version_id = fields.Many2one("wd.gs.config.version", ondelete="set null", index=True)
    previous_checksum = fields.Char(readonly=True)
    checksum = fields.Char(readonly=True)
    error_code = fields.Char(readonly=True)
    message = fields.Text(readonly=True)
    request_id = fields.Char(readonly=True)
    user_id = fields.Many2one("res.users", readonly=True, default=lambda self: self.env.user)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals.setdefault("request_id", self.env.context.get("request_id"))
            vals.setdefault("user_id", self.env.user.id)
        return super().create(vals_list)
