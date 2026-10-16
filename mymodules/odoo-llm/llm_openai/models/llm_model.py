import json

from odoo import _, api, models
from odoo.exceptions import UserError, ValidationError


def _parse_openai_model_parameters(service, raw_parameters):
    """Return the allow-listed OpenAI request parameters for one model."""
    if service != "openai" or raw_parameters in (False, None, ""):
        return {}

    try:
        parameters = json.loads(raw_parameters)
    except (TypeError, ValueError):
        raise UserError(
            _("OpenAI model parameters must contain valid JSON.")
        ) from None

    if not isinstance(parameters, dict):
        raise UserError(_("OpenAI model parameters must be a JSON object."))

    if "openai" not in parameters:
        return {}

    openai_parameters = parameters["openai"]
    if not isinstance(openai_parameters, dict):
        raise UserError(_("The 'openai' model parameter namespace must be an object."))

    if "reasoning_effort" not in openai_parameters:
        return {}

    reasoning_effort = openai_parameters["reasoning_effort"]
    if type(reasoning_effort) is not str or reasoning_effort != "none":
        raise UserError(
            _("OpenAI reasoning_effort currently supports only the string 'none'.")
        )

    return {"reasoning_effort": reasoning_effort}


class LLMModel(models.Model):
    _inherit = "llm.model"

    @api.constrains("parameters", "provider_id")
    def _check_openai_model_parameters(self):
        for record in self:
            try:
                _parse_openai_model_parameters(
                    record.provider_id.service,
                    record.parameters,
                )
            except UserError as error:
                raise ValidationError(str(error)) from None

    def _get_openai_request_parameters(self):
        """Return validated OpenAI-only parameters for Chat Completions."""
        self.ensure_one()
        try:
            return _parse_openai_model_parameters(
                self.provider_id.service,
                self.parameters,
            )
        except UserError:
            raise UserError(
                _(
                    "OpenAI model configuration is invalid. "
                    "Please contact an administrator."
                )
            ) from None
