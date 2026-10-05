import hashlib
import json

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


MAX_SNAPSHOT_BYTES = 1024 * 1024
SUPPORTED_CONFIG_SCHEMA = 1


class ConfigurationDomain(models.Model):
    _name = "wd.gs.config.domain"
    _description = "Global Search Configuration Domain"
    _order = "name, id"

    key = fields.Char(required=True, index=True)
    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
    version_ids = fields.One2many("wd.gs.config.version", "domain_id", string="Versions")

    _sql_constraints = [
        ("key_unique", "unique(key)", "Configuration domain keys must be unique."),
    ]


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
        if any(record.state == "published" for record in self) and not self.env.context.get(
            "wd_gs_allow_published_write"
        ):
            raise UserError(_("Published configuration versions are immutable."))
        return super().write(vals)

    def action_validate(self):
        for record in self:
            record._assert_editable()
            record.write({"state": "validating", "rejection_code": False, "rejection_message": False})
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
                previous.with_context(wd_gs_allow_published_write=True).write({"state": "retired"})
                self.env["wd.gs.audit.event"].create(
                    {
                        "action": "retire",
                        "domain_id": record.domain_id.id,
                        "version_id": previous.id,
                        "checksum": previous.checksum,
                    }
                )
            record.with_context(wd_gs_allow_published_write=True).write(
                {
                    "state": "published",
                    "checksum": checksum,
                    "snapshot_json": snapshot_json,
                    "snapshot_size": snapshot_size,
                    "published_at": fields.Datetime.now(),
                    "published_by": self.env.user.id,
                    "rejection_code": False,
                    "rejection_message": False,
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
            record.with_context(wd_gs_allow_published_write=True).write({"state": "retired"})
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
            raise UserError(_("Published and Retired configuration versions are immutable."))

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
        self.with_context(wd_gs_allow_published_write=True).write(
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
    _description = "Global Search Business Resource"

    version_id = fields.Many2one("wd.gs.config.version", required=True, ondelete="cascade", index=True)
    key = fields.Char(required=True, index=True)
    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
    composite = fields.Boolean(default=False)
    result_identity_scope = fields.Selection(
        [("resource", "Resource"), ("model", "Technical Model")],
        required=True,
        default="resource",
    )
    model_mapping_ids = fields.One2many("wd.gs.resource.model.mapping", "resource_id")
    relation_path_ids = fields.One2many("wd.gs.relation.path", "resource_id")
    business_date_ids = fields.One2many("wd.gs.business.date.mapping", "resource_id")
    state_mapping_ids = fields.One2many("wd.gs.state.mapping", "resource_id")
    snapshot_field_ids = fields.One2many("wd.gs.snapshot.field", "resource_id")

    _sql_constraints = [
        ("version_key_unique", "unique(version_id, key)", "Business resource keys must be unique per version."),
    ]

    def _validate_configuration(self):
        self.ensure_one()
        if not self.model_mapping_ids:
            raise ValidationError(_("Business Resource %s needs a technical model mapping.") % self.key)
        priorities = self.model_mapping_ids.mapped("priority")
        if len(priorities) != len(set(priorities)):
            raise ValidationError(_("Technical model priorities must be unique for %s.") % self.key)
        if not self.business_date_ids:
            raise ValidationError(_("Business Date is not configured for %s.") % self.key)
        for mapping in self.model_mapping_ids:
            mapping._validate_configuration()
        for field in self.model_mapping_ids.mapped("searchable_field_ids"):
            field._validate_configuration()
        for path in self.relation_path_ids:
            path._validate_configuration()
        for business_date in self.business_date_ids:
            business_date._validate_configuration()

    def _snapshot_values(self):
        self.ensure_one()
        return {
            "key": self.key,
            "name": self.name,
            "active": self.active,
            "composite": self.composite,
            "result_identity_scope": self.result_identity_scope,
            "models": [
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
            ],
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
                    "format_type": item.format_type,
                    "allow_empty": item.allow_empty,
                }
                for item in self.snapshot_field_ids
            ],
        }


class ResourceModelMapping(models.Model):
    _name = "wd.gs.resource.model.mapping"
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
    _description = "Global Search Searchable Field"

    mapping_id = fields.Many2one("wd.gs.resource.model.mapping", required=True, ondelete="cascade")
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

    def _validate_configuration(self):
        self.ensure_one()
        model = self.env[self.mapping_id.model_name]
        if self.field_name not in model._fields:
            raise ValidationError(_("Field %s does not exist on %s.") % (self.field_name, self.mapping_id.model_name))
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


class BusinessDateMapping(models.Model):
    _name = "wd.gs.business.date.mapping"
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
    _description = "Global Search State Mapping"

    resource_id = fields.Many2one("wd.gs.business.resource", required=True, ondelete="cascade")
    business_state = fields.Char(required=True)
    technical_values = fields.Char(required=True)

    _sql_constraints = [
        ("resource_state_unique", "unique(resource_id, business_state)", "Business states must be unique per resource."),
    ]


class SnapshotField(models.Model):
    _name = "wd.gs.snapshot.field"
    _description = "Global Search Snapshot Field"

    resource_id = fields.Many2one("wd.gs.business.resource", required=True, ondelete="cascade")
    field_name = fields.Char(required=True)
    label = fields.Char(required=True, translate=True)
    format_type = fields.Selection(
        [("text", "Text"), ("date", "Date"), ("datetime", "Datetime"), ("number", "Number")],
        required=True,
        default="text",
    )
    allow_empty = fields.Boolean(default=True)


class VocabularyEntry(models.Model):
    _name = "wd.gs.vocabulary.entry"
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
        [("publish", "Publish"), ("retire", "Retire"), ("reject", "Reject"), ("invalidate", "Invalidate")],
        required=True,
    )
    domain_id = fields.Many2one("wd.gs.config.domain", ondelete="set null", index=True)
    version_id = fields.Many2one("wd.gs.config.version", ondelete="set null", index=True)
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
