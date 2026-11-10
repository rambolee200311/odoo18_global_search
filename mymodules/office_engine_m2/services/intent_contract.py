"""Small, business-neutral contracts for Candidate B user Intent.

The Intent layer binds a user message and a coarse interpretation to the
current CB-02 version. Expected Effect validation is delegated to the frozen
CB-03 contract; this module does not define an Excel editing language.
"""

from __future__ import annotations

import hashlib
import importlib
import json
from typing import Any

from .candidate_validator import _office_verify


class IntentContractError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def _canonical_json(value: Any) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise IntentContractError("intent_invalid", "Intent data must be finite JSON values.") from exc


def digest_json(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def normalize_interpretation(value: object) -> dict[str, Any]:
    """Validate an agent-proposed, generic interpretation without trusting it."""
    required = {"summary", "target_scope", "assumptions", "unknowns"}
    if not isinstance(value, dict) or set(value) != required:
        raise IntentContractError("intent_invalid", "Interpretation must contain exactly the declared fields.")
    summary = value["summary"]
    scope = value["target_scope"]
    if not isinstance(summary, str) or not summary.strip() or len(summary) > 2000:
        raise IntentContractError("intent_invalid", "Interpretation summary is missing or too long.")
    if (
        not isinstance(scope, dict)
        or set(scope) != {"description", "basis"}
        or not isinstance(scope.get("description"), str)
        or not scope["description"].strip()
        or len(scope["description"]) > 1000
        or scope.get("basis") not in {"explicit", "inferred", "ambiguous"}
    ):
        raise IntentContractError("intent_invalid", "Interpretation target scope is invalid.")
    normalized_lists: dict[str, list[str]] = {}
    for key in ("assumptions", "unknowns"):
        items = value[key]
        if (
            not isinstance(items, list)
            or len(items) > 32
            or any(not isinstance(item, str) or not item.strip() or len(item) > 512 for item in items)
        ):
            raise IntentContractError("intent_invalid", f"Interpretation {key} must be a bounded string list.")
        normalized_lists[key] = [item.strip() for item in items]
    return {
        "summary": summary.strip(),
        "target_scope": {"description": scope["description"].strip(), "basis": scope["basis"]},
        "assumptions": normalized_lists["assumptions"],
        "unknowns": normalized_lists["unknowns"],
    }


def canonicalize_expected_effect(effect: object, *, parent_version_id: int, input_sha256: str):
    """Bind an agent-declared effect to current bytes, then delegate to CB-03.

    The public tool accepts the frozen effect semantics (targets, allowed
    change kinds, assertions and unknowns), while the service supplies the
    current parent/hash and computes the canonical digest. A caller may replay
    the complete canonical value returned by a prior plan; any supplied stale
    binding or digest is still rejected by CB-03.
    """
    if not isinstance(effect, dict):
        raise IntentContractError("expected_effect_invalid", "Expected Effect must be a structured object.")
    contract_fields = {
        "schema_version", "parent_version_id", "input_sha256", "target_scopes",
        "allowed_change_kinds", "expected_assertions", "unknowns", "effect_digest",
    }
    required_fields = {"target_scopes", "allowed_change_kinds", "expected_assertions", "unknowns"}
    if set(effect) - contract_fields or not required_fields.issubset(effect):
        raise IntentContractError(
            "expected_effect_invalid",
            "Expected Effect must use target_scopes, allowed_change_kinds, expected_assertions, and unknowns.",
        )
    payload = {
        "schema_version": effect.get("schema_version", "1"),
        "parent_version_id": effect.get("parent_version_id", parent_version_id),
        "input_sha256": effect.get("input_sha256", input_sha256),
        "target_scopes": effect["target_scopes"],
        "allowed_change_kinds": effect["allowed_change_kinds"],
        "expected_assertions": effect["expected_assertions"],
        "unknowns": effect["unknowns"],
    }
    if "effect_digest" in effect:
        payload["effect_digest"] = effect["effect_digest"]
    else:
        payload["effect_digest"] = digest_json(payload)
    try:
        verifier = importlib.import_module("office_verify.verify")
        budget = _office_verify.VerificationBudget()
        canonical, digest = verifier._canonical_effect(payload, input_sha256, budget)
    except Exception as exc:
        code = getattr(exc, "error_code", "expected_effect_invalid")
        raise IntentContractError(code, "Expected Effect is invalid or exceeds the Validator contract.") from exc
    if canonical["parent_version_id"] != parent_version_id:
        raise IntentContractError("expected_effect_stale", "Expected Effect is bound to another parent version.")
    # CB-03's canonical payload deliberately excludes the digest it validates.
    # Its public input contract, however, requires that digest alongside the
    # payload, so reattach the verified value for downstream validation.
    canonical["effect_digest"] = digest
    return canonical, digest


def bind_intent(
    *, intent_message_id: int, thread_id: int, session_id: int,
    parent_version_id: int, input_sha256: str, interpretation: dict[str, Any],
    effect_digest: str, confirmation_required: bool = False,
    confirmation_reason: str = "",
) -> dict[str, Any]:
    if any(type(item) is not int or item < 1 for item in (
        intent_message_id, thread_id, session_id, parent_version_id
    )):
        raise IntentContractError("intent_binding_invalid", "Intent identity binding is invalid.")
    normalized = normalize_interpretation(interpretation)
    if type(confirmation_required) is not bool:
        raise IntentContractError(
            "confirmation_decision_invalid",
            "The model must provide an explicit boolean confirmation decision.",
        )
    if not isinstance(confirmation_reason, str) or len(confirmation_reason) > 2000:
        raise IntentContractError("confirmation_reason_invalid", "The confirmation explanation is invalid.")
    confirmation_reason = confirmation_reason.strip()
    if confirmation_required and not confirmation_reason:
        raise IntentContractError(
            "confirmation_reason_missing", "A model-requested confirmation needs a user-facing reason."
        )
    if not confirmation_required and confirmation_reason:
        raise IntentContractError(
            "confirmation_reason_unexpected", "A confirmation reason cannot be supplied when confirmation is not requested."
        )
    payload = {
        "schema_version": "office.intent.v1",
        "intent_message_id": intent_message_id,
        "thread_id": thread_id,
        "session_id": session_id,
        "parent_version_id": parent_version_id,
        "input_sha256": input_sha256,
        "interpretation": normalized,
        "effect_digest": effect_digest,
        "confirmation_required": confirmation_required,
        "confirmation_reason": confirmation_reason,
    }
    payload["intent_digest"] = digest_json(payload)
    return payload


def confirmation_receipt_id(
    binding: dict[str, Any], *, owner_id: int, session_revision: int,
    proposal_revision: int, document_revision: int,
    decision_message_id: int | None = None,
    confirmed_by_user_id: int | None = None,
) -> str:
    """Fingerprint either a pending confirmation request or its real decision.

    The pending form binds the proposed operation before the user responds.
    The confirmed form additionally binds the actual user-authored Thread
    message and authenticated Odoo user; callers must verify that message via
    the current ORM environment before constructing the decision fingerprint.
    """
    if (decision_message_id is None) != (confirmed_by_user_id is None):
        raise IntentContractError(
            "confirmation_decision_invalid", "Confirmation identity fields must be supplied together."
        )
    if decision_message_id is not None and any(
        type(value) is not int or value < 1 for value in (decision_message_id, confirmed_by_user_id)
    ):
        raise IntentContractError(
            "confirmation_decision_invalid", "Confirmation identity fields are invalid."
        )
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
        "effect_digest": binding["effect_digest"],
        "session_revision": session_revision,
        "proposal_revision": proposal_revision,
        "document_revision": document_revision,
    })
