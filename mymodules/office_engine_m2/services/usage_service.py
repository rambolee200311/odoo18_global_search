import re
import uuid

from odoo.exceptions import ValidationError

_USAGE_KEYS = {
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "reasoning_tokens",
    "status",
}
_USAGE_STATUS_TO_ERROR = {
    "partial": "usage_partial",
    "invalid": "usage_invalid",
}
_OUTCOMES = {"success", "provider_error", "processing_error"}
_ERROR_CODE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


def _nonnegative_integer(value, field_name, *, allow_none=True):
    if value is None and allow_none:
        return None
    if type(value) is not int or value < 0:
        raise ValidationError("Invalid Usage metadata: %s." % field_name)
    return value


def _validated_recordset(record, model_name, label):
    if record is None or record is False:
        return None
    if getattr(record, "_name", None) != model_name or len(record) != 1:
        raise ValidationError("Invalid Usage metadata: %s." % label)
    record.check_access("read")
    if not record.exists():
        raise ValidationError("Invalid Usage metadata: %s." % label)
    return record


def record_usage(
    env,
    *,
    model,
    usage=None,
    elapsed_ms=None,
    attempt_no=None,
    outcome,
    error_code=None,
    response_id=None,
    thread=None,
    **unexpected,
):
    """Persist allowlisted usage metadata through a non-RPC Python service.

    No prompt, completion, template, business values, raw SDK object, or secret
    is accepted. The returned value is a non-sensitive UUID/status dictionary,
    never a privileged ORM recordset.
    """
    if unexpected:
        raise ValidationError("Usage metadata contains unsupported fields.")
    if outcome not in _OUTCOMES:
        raise ValidationError("Invalid Usage metadata: outcome.")
    if error_code is not None and (
        not isinstance(error_code, str) or not _ERROR_CODE.fullmatch(error_code)
    ):
        raise ValidationError("Invalid Usage metadata: error_code.")

    model = _validated_recordset(model, "llm.model", "model")
    if not model or model.provider_id.service != "openai":
        raise ValidationError("Only an authorized OpenAI model can be metered.")
    thread = _validated_recordset(thread, "llm.thread", "thread")

    if usage is None:
        normalized_usage = {
            "prompt_tokens": None,
            "completion_tokens": None,
            "total_tokens": None,
            "reasoning_tokens": None,
        }
        status = "missing"
        status_error = "usage_missing"
    else:
        if not isinstance(usage, dict):
            raise ValidationError("Usage must be a allowlisted dictionary.")
        unknown = set(usage) - _USAGE_KEYS
        if unknown:
            raise ValidationError("Usage metadata contains unsupported fields.")
        status = usage.get("status")
        if status not in {"available", "partial", "invalid"}:
            raise ValidationError("Invalid Usage metadata: status.")
        normalized_usage = {
            name: _nonnegative_integer(usage.get(name), name)
            for name in (
                "prompt_tokens",
                "completion_tokens",
                "total_tokens",
                "reasoning_tokens",
            )
        }
        required_present = all(
            normalized_usage[name] is not None
            for name in ("prompt_tokens", "completion_tokens", "total_tokens")
        )
        if status == "available" and not required_present:
            raise ValidationError("Available Usage must contain all required counts.")
        if status == "partial" and required_present:
            raise ValidationError("Partial Usage must preserve a missing required count.")
        status_error = _USAGE_STATUS_TO_ERROR.get(status)

    elapsed_ms = _nonnegative_integer(elapsed_ms, "elapsed_ms")
    if attempt_no is not None and (type(attempt_no) is not int or attempt_no <= 0):
        raise ValidationError("Invalid Usage metadata: attempt_no.")

    if response_id is not None and (
        not isinstance(response_id, str) or len(response_id) > 255
    ):
        raise ValidationError("Invalid Usage metadata: response_id.")

    values = {
        "call_uuid": str(uuid.uuid4()),
        "thread_id": thread.id if thread else False,
        "owner_id": env.user.id,
        "company_id": env.company.id,
        "provider_code": "openai",
        "model_name": model.name,
        "response_id": response_id or False,
        **normalized_usage,
        "elapsed_ms": elapsed_ms,
        "attempt_no": attempt_no,
        "outcome": outcome,
        "error_code": status_error or error_code or False,
    }

    # The service performs the only permitted elevation, after validating all
    # associations and all input keys in the caller's original environment.
    created = env["office.llm.usage"].sudo().create(values)
    return {"call_uuid": created.call_uuid, "status": status}
