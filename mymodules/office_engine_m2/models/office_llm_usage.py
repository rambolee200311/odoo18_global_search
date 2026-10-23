import uuid

from odoo import fields, models


class NullableInteger(fields.Integer):
    """Odoo integer field that preserves SQL NULL separately from integer zero."""

    def convert_to_column(self, value, record, values=None, validate=True):
        if value is None or value is False:
            return None
        if type(value) is not int:
            raise ValueError("Expected an integer or null value.")
        return value

    def convert_to_cache(self, value, record, validate=True):
        if value is None or value is False:
            return None
        if type(value) is not int:
            raise ValueError("Expected an integer or null value.")
        return value

    def convert_to_record(self, value, record):
        return value

    def convert_to_read(self, value, record, use_display_name=True):
        if value is None:
            return None
        return super().convert_to_read(value, record, use_display_name)


class OfficeLlmUsage(models.Model):
    _name = "office.llm.usage"
    _description = "Office Engine LLM Usage Metadata"
    _order = "create_date desc, id desc"

    call_uuid = fields.Char(
        required=True,
        readonly=True,
        copy=False,
        index=True,
        default=lambda self: str(uuid.uuid4()),
    )
    thread_id = fields.Many2one(
        "llm.thread",
        readonly=True,
        copy=False,
        ondelete="set null",
        index=True,
    )
    owner_id = fields.Many2one(
        "res.users",
        required=True,
        readonly=True,
        copy=False,
        ondelete="restrict",
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        readonly=True,
        copy=False,
        ondelete="restrict",
        index=True,
    )
    provider_code = fields.Selection(
        [("openai", "OpenAI")],
        required=True,
        readonly=True,
        copy=False,
    )
    model_name = fields.Char(required=True, readonly=True, copy=False, index=True)
    response_id = fields.Char(readonly=True, copy=False)
    prompt_tokens = NullableInteger(readonly=True, copy=False)
    completion_tokens = NullableInteger(readonly=True, copy=False)
    total_tokens = NullableInteger(readonly=True, copy=False)
    reasoning_tokens = NullableInteger(readonly=True, copy=False)
    elapsed_ms = NullableInteger(readonly=True, copy=False)
    attempt_no = NullableInteger(readonly=True, copy=False)
    outcome = fields.Selection(
        [
            ("success", "Success"),
            ("provider_error", "Provider Error"),
            ("processing_error", "Processing Error"),
        ],
        required=True,
        readonly=True,
        copy=False,
    )
    error_code = fields.Char(readonly=True, copy=False, size=64)

    _sql_constraints = [
        ("call_uuid_unique", "unique(call_uuid)", "Usage call UUID must be unique."),
        (
            "token_counts_nonnegative",
            "check((prompt_tokens IS NULL OR prompt_tokens >= 0) AND "
            "(completion_tokens IS NULL OR completion_tokens >= 0) AND "
            "(total_tokens IS NULL OR total_tokens >= 0) AND "
            "(reasoning_tokens IS NULL OR reasoning_tokens >= 0))",
            "Token counts must be nonnegative.",
        ),
        (
            "elapsed_ms_nonnegative",
            "check(elapsed_ms IS NULL OR elapsed_ms >= 0)",
            "Elapsed time must be nonnegative.",
        ),
        (
            "attempt_no_positive",
            "check(attempt_no IS NULL OR attempt_no > 0)",
            "Attempt number must be positive.",
        ),
    ]
