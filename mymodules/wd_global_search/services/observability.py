"""Odoo-native observability helpers with a strict field allowlist."""

import hashlib
import hmac
import json
import logging


_logger = logging.getLogger(__name__)
HASH_VERSION = "v1"
ALLOWED_FIELDS = frozenset(
    {
        "request_id",
        "config_version",
        "resource",
        "latency_ms",
        "result_count",
        "status",
        "error_code",
        "retryable",
        "failed_resources",
        "boundary",
        "model",
        "raw_query_hash",
        "conditions_hash",
        "hash_version",
        "user_context_hash",
        "event",
    }
)


def hash_value(secret, value):
    if not secret:
        raise ValueError("Observability secret is required")
    encoded = str(value).encode("utf-8")
    return hmac.new(str(secret).encode("utf-8"), encoded, hashlib.sha256).hexdigest()


def canonical_hash(secret, value):
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hash_value(secret, canonical)


def event_fields(event, fields):
    payload = {"event": event, "hash_version": HASH_VERSION}
    payload.update({key: value for key, value in fields.items() if key in ALLOWED_FIELDS})
    return payload


def log_event(level, event, fields):
    payload = event_fields(event, fields)
    getattr(_logger, level)("global_search.observability %s", json.dumps(payload, ensure_ascii=False))
    return payload
