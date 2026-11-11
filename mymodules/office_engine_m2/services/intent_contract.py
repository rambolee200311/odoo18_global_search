"""Server-owned request and confirmation fingerprints for Route B."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def digest_json(value: Any) -> str:
    """Hash server-built JSON for idempotency and scoped receipts."""
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def confirmation_receipt_id(
    binding: dict[str, Any], *, owner_id: int, session_revision: int,
    proposal_revision: int, document_revision: int,
    decision_message_id: int | None = None,
    confirmed_by_user_id: int | None = None,
) -> str:
    """Fingerprint a pending risk confirmation or its authenticated decision."""
    if (decision_message_id is None) != (confirmed_by_user_id is None):
        raise ValueError("Confirmation identity fields must be supplied together.")
    if decision_message_id is not None and any(
        type(value) is not int or value < 1 for value in (decision_message_id, confirmed_by_user_id)
    ):
        raise ValueError("Confirmation identity fields are invalid.")
    return digest_json({
        "kind": "office.confirmation.v1",
        "owner_id": owner_id,
        "confirmed_by_user_id": confirmed_by_user_id or False,
        "decision_message_id": decision_message_id or False,
        "thread_id": binding["thread_id"],
        "session_id": binding["session_id"],
        "intent_message_id": binding["intent_message_id"],
        "intent_digest": binding["intent_digest"],
        "parent_version_id": binding["parent_version_id"],
        "input_sha256": binding["input_sha256"],
        # Retained for the existing, explicitly confirmed historical restore
        # path; ordinary Route B edits leave it false and never ask the model.
        "effect_digest": binding.get("effect_digest") or False,
        "session_revision": session_revision,
        "proposal_revision": proposal_revision,
        "document_revision": document_revision,
    })
