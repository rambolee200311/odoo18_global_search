from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from ..services.field_path import FieldPathError, validate_field_path

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
    collection_match = fields.Selection(
        [("any", "Any related record"), ("all", "All query values")],
        required=True,
        default="any",
        help=(
            "Applies only to Many2many and One2many Searchable Field paths. "
            "Direct and Many2one paths must use Any."
        ),
    )
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

    def _validate_configuration(self, max_relation_depth=None):
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
        try:
            validate_field_path(
                model,
                self.field_name,
                operator_set=self.operator_set,
                index_strategy=self.index_strategy,
                collection_match=self.collection_match,
                max_relation_depth=max_relation_depth,
            )
        except FieldPathError as exc:
            raise ValidationError(
                _("Invalid Searchable Field path %s: %s")
                % (self.field_name, str(exc))
            ) from exc

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
