import math

from odoo import _, fields, models
from odoo.exceptions import ValidationError

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
        if (
            min(
                self.max_results,
                self.resource_timeout,
                self.request_timeout,
                self.max_relation_depth,
            )
            <= 0
            or not math.isfinite(self.resource_timeout)
            or not math.isfinite(self.request_timeout)
        ):
            raise ValidationError(_("Performance limits must be positive."))
        if (
            self.max_results > 200
            or self.resource_timeout > 3.0
            or self.request_timeout > 5.0
            or self.max_relation_depth > 3
        ):
            raise ValidationError(
                _("Performance configuration cannot exceed the Search Service limits.")
            )
