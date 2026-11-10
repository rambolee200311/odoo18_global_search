"""Candidate B orchestration over the existing CB-01/02/03 services.

This module owns no Provider transport, workbook parser, version model, or UI.
The public tool facade deliberately supplies no external Provider client while
the SRS/data-processing release gate is open. Tests inject a Mock adapter into
``execute_planned_edit``; production dispatch remains blocked until that gate
is formally opened.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any

from odoo import _, tools
from odoo.exceptions import AccessError, ValidationError

from .intent_contract import (
    IntentContractError,
    bind_intent,
    canonicalize_expected_effect,
    confirmation_receipt_id,
    digest_json,
    normalize_interpretation,
)
from .workbook_version_service import (
    CandidateAcceptanceAuthorization,
    CandidateRejection,
    _read_attachment,
    _require_session,
    _require_user_thread_message,
    _require_version,
    accept_verified_candidate,
    register_candidate,
    reject_verified_candidate,
)
from .candidate_validator import validate_workbook_candidate


XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
EXTERNAL_PROVIDER_DISPATCH_ENABLED = False
_CONFIRM = "确认"
_ACCEPT = "接受"
_REJECT = "拒绝"
_logger = logging.getLogger(__name__)


def _public_result(outcome: str, operation_status: str, **values) -> dict[str, Any]:
    return {
        "status": outcome,
        "operation_status": operation_status,
        "operation_executed": False,
        "artifact_state": "not_presented",
        "delivery_state": "not_finalized",
        "verified_facts": [],
        "model_claims": [],
        "unverified_aspects": [],
        "unknowns": [],
        "risk_facts": [],
        **values,
    }


def _latest_user_message(env, thread):
    message_model = env["mail.message"]
    # The native chat loop can execute the tool in the same transaction that
    # posted the user turn. llm_role is a stored computed field derived from
    # subtype_id, so flush that pending computation before searching for this
    # turn; otherwise the query can return the prior upload message.
    message_model.flush_model(["subtype_id", "llm_role", "author_id", "model", "res_id", "is_error"])
    messages = message_model.search(
        [
            ("model", "=", thread._name),
            ("res_id", "=", thread.id),
            ("llm_role", "=", "user"),
            ("author_id", "=", env.user.partner_id.id),
            ("is_error", "=", False),
        ],
        order="id desc",
        limit=1,
    )
    if not messages or messages not in thread.message_ids:
        raise AccessError(_("The current Office user message is unavailable."))
    messages.check_access("read")
    return messages


def _message_text(message):
    return tools.html2plaintext(message.body or "").strip()


def _candidate_artifact_review_fields(env, candidate, edit_result):
    attachment = candidate.output_attachment_id
    if not attachment:
        raise ValidationError(_("The Candidate workbook file is unavailable."))
    attachment.check("read")
    return {
        "candidate_filename": attachment.name,
        "candidate_download_url": f"/web/content/{attachment.id}?download=true",
        "candidate_output_sha256": candidate.output_sha256,
        "verified_facts": edit_result.get("verified_facts", []),
        "actual_effects": edit_result.get("actual_effects", []),
        "model_claims": edit_result.get("model_claims", []),
        "unverified_aspects": edit_result.get("unverified_aspects", []),
    }


def _resolve_current(env, thread):
    """Resolve only the current user's latest upload and accepted CB-02 bytes."""
    thread.ensure_one()
    thread.check_access("read")
    if thread.user_id.id != env.uid:
        raise AccessError(_("The Office Thread is unavailable."))
    upload, source_attachment = thread._office_latest_upload()
    if not upload or not source_attachment:
        raise AccessError(_("A current versioned Office workbook is unavailable."))
    upload.check_access("read")
    source_attachment.check("read")
    session = env["office.mapping.session"].search(
        [
            ("thread_id", "=", thread.id),
            ("owner_id", "=", env.uid),
            ("company_id", "in", env.companies.ids),
            ("source_message_id", "=", upload.id),
            ("source_attachment_id", "=", source_attachment.id),
            ("current_version_id", "!=", False),
        ],
        order="id desc",
        limit=1,
    )
    if not session:
        raise AccessError(_("This upload has no accepted, versioned workbook."))
    session = _require_session(env, session.id, write=True)
    current = _require_version(env, session, session.current_version_id.id, write=True)
    if current.state not in {"accepted_current", "finalized"} or current.version_kind not in {"initial", "edit", "restore"}:
        raise ValidationError(_("The Session does not have an accepted current workbook version."))
    if current != session.last_valid_version_id:
        raise ValidationError(_("Current and last-valid workbook versions are inconsistent."))
    content, sha256 = _read_attachment(env, current.output_attachment_id, expected_sha=current.output_sha256)
    if current.mimetype != XLSX_MIME or not (current.filename or "").lower().endswith(".xlsx"):
        raise ValidationError(_("Candidate B currently supports XLSX workbooks only."))
    user_message = _latest_user_message(env, thread)
    if user_message.id <= upload.id:
        raise AccessError(_("A user-authored edit Intent is required after the workbook upload."))
    _require_user_thread_message(env, session, user_message.id, "Intent")
    return {
        "thread": thread,
        "session": session,
        "current": current,
        "input_bytes": content,
        "input_sha256": sha256,
        "user_message": user_message,
        "upload_message": upload,
    }


def _retrieve_odoo_data(env, thread, tool_message, query_spec):
    """Reuse this Thread's existing Retriever without requiring a workbook version."""
    thread.ensure_one()
    thread.check_access("read")
    if thread.user_id.id != env.uid:
        raise AccessError(_("The Office Thread is unavailable."))
    if (
        not tool_message
        or tool_message._name != "mail.message"
        or tool_message.model != thread._name
        or tool_message.res_id != thread.id
    ):
        raise AccessError(_("The Office chat context is unavailable."))
    tool_message.check_access("read")
    _latest_user_message(env, thread)

    if not isinstance(query_spec, dict):
        return _public_result(
            "clarification_required", "retriever_query_missing", action="retrieve",
            error_code="retriever_query_missing",
            message="Provide a query_spec using the existing Odoo Record Retriever parameters.",
        )
    allowed = {"model", "domain", "fields", "limit", "offset", "order", "include_pagination"}
    if set(query_spec) - allowed or not isinstance(query_spec.get("model"), str) or not query_spec["model"].strip():
        return _public_result(
            "blocked", "retriever_query_invalid", action="retrieve",
            error_code="retriever_query_invalid",
            message="The Odoo query was rejected because its parameters are invalid.",
        )

    # A private copy allows M2 to preserve a stable identity and page order
    # without changing the shared M1 Retriever contract or caller input.
    normalized = dict(query_spec)
    requested_fields = normalized.get("fields")
    if isinstance(requested_fields, list) and requested_fields and "id" not in requested_fields:
        normalized["fields"] = [*requested_fields, "id"]
    pagination = normalized.get("include_pagination", False)
    order = normalized.get("order", "")
    if order is None:
        order = ""
        normalized["order"] = ""
    if pagination is True and isinstance(order, str) and not order.strip():
        normalized["order"] = "id"

    retriever = thread.tool_ids.filtered(
        lambda item: item.name == "odoo_record_retriever" and item.active
    )[:1]
    if not retriever:
        return _public_result(
            "blocked", "retriever_not_bound", action="retrieve",
            error_code="retriever_not_bound",
            message="The existing Odoo Record Retriever is not available in this Thread.",
        )
    retriever.check_access("read")

    try:
        data = retriever.with_context(message=tool_message).execute(normalized)
    except AccessError:
        raise
    except ValidationError:
        _logger.info(
            "Office retrieve query rejected by the existing Retriever (thread_id=%s, model=%s)",
            thread.id,
            normalized.get("model"),
            exc_info=True,
        )
        return _public_result(
            "blocked", "retriever_query_rejected", action="retrieve",
            error_code="retriever_query_rejected",
            message="The existing Retriever or current-user Odoo rules rejected this query.",
        )

    scope = {
        "model": normalized["model"],
        "domain": normalized.get("domain", []),
        "fields": normalized.get("fields", []),
        "order": normalized.get("order", ""),
        "limit": normalized.get("limit", 100),
        "offset": normalized.get("offset", 0),
        "include_pagination": normalized.get("include_pagination", False),
    }
    return _public_result(
        "completed", "odoo_data_retrieved", action="retrieve",
        operation_executed=False,
        data=data,
        query_scope=scope,
        retrieved_at=datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        message="Odoo data was read through the current user's existing Retriever. No workbook or business record was changed.",
    )


def _version_facts(context):
    session, current = context["session"], context["current"]
    return {
        "thread_id": context["thread"].id,
        "session_id": session.id,
        "current_version_id": current.id,
        "last_valid_version_id": session.last_valid_version_id.id or False,
        "parent_version_id": current.id,
        "input_sha256": context["input_sha256"],
        "session_revision": session.revision,
        "proposal_revision": session.proposal_revision,
        "document_revision": session.document_revision,
        "intent_message_id": context["user_message"].id,
    }


def _tool_results_before(env, thread, before_id):
    messages = env["mail.message"].search(
        [
            ("model", "=", thread._name),
            ("res_id", "=", thread.id),
            ("llm_role", "=", "tool"),
            ("id", "<", before_id),
        ],
        order="id desc",
        limit=100,
    )
    for message in messages:
        message.check_access("read")
        data = message.get_tool_data() or {}
        if data.get("tool_name") != "office" or data.get("status") != "completed":
            continue
        result = data.get("result")
        if isinstance(result, dict):
            yield message, result


def _latest_plan(env, context, tool_message):
    for message, result in _tool_results_before(env, context["thread"], tool_message.id):
        if result.get("action") == "plan":
            return message, result
    return None, None


def _latest_edit(env, context, tool_message):
    for message, result in _tool_results_before(env, context["thread"], tool_message.id):
        if result.get("action") == "edit" and result.get("candidate_version_id"):
            return message, result
    return None, None


def _build_plan(
    context, interpretation, expected_effect, model_risk_claims=None,
    confirmation_required=None, confirmation_reason=None,
):
    try:
        normalized = normalize_interpretation(interpretation)
        effect, effect_digest = canonicalize_expected_effect(
            expected_effect,
            parent_version_id=context["current"].id,
            input_sha256=context["input_sha256"],
        )
    except IntentContractError as exc:
        return None, _public_result(
            "clarification_required", "intent_not_ready", action="plan",
            error_code=exc.code, message=str(exc),
        )
    if normalized["target_scope"]["basis"] == "ambiguous":
        return None, _public_result(
            "clarification_required", "intent_not_ready", action="plan",
            message="The model identified an ambiguous target; clarify the request before editing.",
            clarification_question=(normalized["unknowns"][0] if normalized["unknowns"] else normalized["target_scope"]["description"]),
            model_claims=[normalized["summary"]], unknowns=normalized["unknowns"],
        )
    if type(confirmation_required) is not bool:
        return None, _public_result(
            "clarification_required", "confirmation_decision_missing", action="plan",
            message="The model must explicitly decide whether this request needs business-risk confirmation.",
        )
    if confirmation_reason is None:
        confirmation_reason = ""
    if not isinstance(confirmation_reason, str) or len(confirmation_reason) > 2000:
        return None, _public_result(
            "clarification_required", "confirmation_reason_invalid", action="plan",
            message="The model confirmation explanation is invalid.",
        )
    confirmation_reason = confirmation_reason.strip()
    if confirmation_required and not confirmation_reason:
        return None, _public_result(
            "clarification_required", "confirmation_reason_missing", action="plan",
            message="The model requested confirmation without explaining the identified risk.",
        )
    if not confirmation_required and confirmation_reason:
        return None, _public_result(
            "clarification_required", "confirmation_reason_unexpected", action="plan",
            message="A risk explanation was supplied without requesting confirmation.",
        )
    binding = bind_intent(
        intent_message_id=context["user_message"].id,
        thread_id=context["thread"].id,
        session_id=context["session"].id,
        parent_version_id=context["current"].id,
        input_sha256=context["input_sha256"],
        interpretation=normalized,
        effect_digest=effect_digest,
        confirmation_required=confirmation_required,
        confirmation_reason=confirmation_reason,
    )
    claims = model_risk_claims or []
    if not isinstance(claims, list) or len(claims) > 32 or any(not isinstance(item, dict) for item in claims):
        return None, _public_result(
            "clarification_required", "intent_not_ready", action="plan",
            error_code="risk_claims_invalid", message="Model risk claims must be a bounded list of objects.",
        )
    # The LLM supplies business-risk judgment; this layer only binds its
    # decision and verifies the later user's response against that binding.
    needs_confirmation = confirmation_required
    receipt_id = False
    if needs_confirmation:
        facts = _version_facts(context)
        receipt_id = confirmation_receipt_id(
            binding,
            owner_id=context["session"].owner_id.id,
            session_revision=facts["session_revision"],
            proposal_revision=facts["proposal_revision"],
            document_revision=facts["document_revision"],
        )
    plan = {
        "schema_version": "office.plan.v1",
        "action": "plan",
        "binding": binding,
        "expected_effect": effect,
        "requires_confirmation": needs_confirmation,
        "confirmation_reason": confirmation_reason,
        "confirmation_receipt_id": receipt_id,
        "model_claims": claims,
        "risk_facts": [],
    }
    plan["plan_digest"] = digest_json(plan)
    if needs_confirmation:
        result = _public_result(
            "confirmation_required", "plan_ready", action="plan",
            message="The requested scope requires a user decision before candidate editing.",
            confirmation_question=(
                confirmation_reason + "\n若仍要继续生成候选，请回复“确认”；回复“拒绝”将取消本次编辑。"
            ),
            confirmation_receipt_id=receipt_id,
            plan_digest=plan["plan_digest"],
            binding=binding,
            confirmation_reason=confirmation_reason,
            expected_effect=effect,
            target_scopes=effect["target_scopes"],
            allowed_change_kinds=effect["allowed_change_kinds"],
            expected_assertions=effect["expected_assertions"],
            model_claims=claims,
            unknowns=normalized["unknowns"],
        )
    else:
        result = _public_result(
            "completed", "plan_ready", action="plan",
            message="The model plan is bound to the current file; no file change has occurred.",
            plan_digest=plan["plan_digest"],
            binding=binding,
            expected_effect=effect,
            target_scopes=effect["target_scopes"],
            allowed_change_kinds=effect["allowed_change_kinds"],
            expected_assertions=effect["expected_assertions"],
            model_claims=claims,
            unknowns=normalized["unknowns"],
        )
    plan["public_result"] = result
    return plan, result


def _read_plan(
    context, tool_message, interpretation, expected_effect, model_risk_claims,
    confirmation_required, confirmation_reason,
):
    if type(confirmation_required) is not bool:
        raise ValidationError(_("The current model call did not provide a confirmation decision."))
    if confirmation_reason is None:
        confirmation_reason = ""
    if not isinstance(confirmation_reason, str):
        raise ValidationError(_("The current model call provided an invalid confirmation explanation."))
    confirmation_reason = confirmation_reason.strip()
    plan_message, tool_result = _latest_plan(context["thread"].env, context, tool_message)
    if not tool_result or not isinstance(tool_result.get("binding"), dict):
        raise ValidationError(_("Plan the edit in this Thread before executing it."))
    binding = tool_result["binding"]
    if binding.get("session_id") != context["session"].id or binding.get("thread_id") != context["thread"].id:
        raise ValidationError(_("The saved edit plan belongs to another Thread or Session."))
    if binding.get("intent_message_id") != tool_result.get("binding", {}).get("intent_message_id"):
        raise ValidationError(_("The saved edit plan is invalid."))
    try:
        normalized = normalize_interpretation(interpretation)
        effect, digest = canonicalize_expected_effect(
            expected_effect,
            parent_version_id=context["current"].id,
            input_sha256=context["input_sha256"],
        )
    except IntentContractError as exc:
        raise ValidationError(str(exc)) from exc
    recomputed = bind_intent(
        intent_message_id=binding["intent_message_id"],
        thread_id=context["thread"].id,
        session_id=context["session"].id,
        parent_version_id=context["current"].id,
        input_sha256=context["input_sha256"],
        interpretation=normalized,
        effect_digest=digest,
        confirmation_required=confirmation_required,
        confirmation_reason=confirmation_reason or "",
    )
    if recomputed != binding or effect != tool_result.get("expected_effect"):
        raise ValidationError(_("The current file or requested effect differs from the planned operation."))
    if tool_result.get("model_claims", []) != (model_risk_claims or []):
        raise ValidationError(_("The model risk claims changed after planning."))
    if tool_result.get("requires_confirmation") is not confirmation_required:
        raise ValidationError(_("The model confirmation decision changed after planning."))
    if tool_result.get("confirmation_reason", "") != (confirmation_reason or ""):
        raise ValidationError(_("The model confirmation explanation changed after planning."))
    return plan_message, tool_result, normalized, effect


def plan_edit(
    env, thread, tool_message, interpretation, expected_effect, model_risk_claims=None,
    *, confirmation_required=None, confirmation_reason=None,
):
    context = _resolve_current(env, thread)
    plan, result = _build_plan(
        context, interpretation, expected_effect, model_risk_claims,
        confirmation_required, confirmation_reason,
    )
    if plan:
        # The native llm_tool loop stores this returned value on the tool message.
        return plan["public_result"] | {
            "plan_digest": plan["plan_digest"],
            "binding": plan["binding"],
            "expected_effect": plan["expected_effect"],
            "requires_confirmation": plan["requires_confirmation"],
            "confirmation_reason": plan["confirmation_reason"],
            "confirmation_receipt_id": plan["confirmation_receipt_id"],
            "model_claims": plan["model_claims"],
        }
    return result


def _candidate_existing(env, session, idempotency_key):
    return env["office.workbook.version"].search(
        [("session_id", "=", session.id), ("idempotency_key", "=", idempotency_key)], limit=1
    )


def execute_planned_edit(
    env, thread, tool_message, interpretation, expected_effect, model_risk_claims=None,
    *, adapter, provider_client, model, limits, confirmation_required=None,
    confirmation_reason=None,
):
    """Execute one already planned edit with injected trusted dependencies.

    This is an internal Python service seam for Mock/authorized integration
    tests. It is not an ORM model method, RPC endpoint, or Agent Tool.
    """
    context = _resolve_current(env, thread)
    plan_message, plan_result, normalized, effect = _read_plan(
        context, tool_message, interpretation, expected_effect, model_risk_claims,
        confirmation_required, confirmation_reason,
    )
    user_message = context["user_message"]
    binding = plan_result["binding"]
    is_confirmation = plan_result.get("requires_confirmation") is True
    confirmation_id = plan_result.get("confirmation_receipt_id") or False
    effective_confirmation_id = False
    if is_confirmation:
        answer = _message_text(user_message)
        if user_message.id > plan_message.id and answer in {"拒绝", "取消", "不同意"}:
            return _public_result(
                "completed", "confirmation_declined", action="edit",
                message="The user declined the model-requested risk confirmation. No Candidate was created and Current is unchanged.",
                confirmation_receipt_id=confirmation_id,
                current_version_id=context["current"].id,
            )
        if user_message.id <= plan_message.id or answer != _CONFIRM:
            return _public_result(
                "confirmation_required", "awaiting_user_decision", action="edit",
                message="No Candidate was created. The current user must confirm or decline the model-described risk.",
                confirmation_receipt_id=confirmation_id,
                confirmation_reason=plan_result.get("confirmation_reason"),
                target_scopes=effect["target_scopes"],
                expected_assertions=effect["expected_assertions"],
                current_version_id=context["current"].id,
            )
        # Confirmation receipt binds the current user message sequence as well
        # as all immutable source/effect/revision inputs.
        recalculated = confirmation_receipt_id(
            binding,
            owner_id=context["session"].owner_id.id,
            session_revision=context["session"].revision,
            proposal_revision=context["session"].proposal_revision,
            document_revision=context["session"].document_revision,
        )
        if recalculated != confirmation_id:
            return _public_result(
                "confirmation_required", "confirmation_stale", action="edit",
                error_code="confirmation_binding_changed",
                message="The file, revision, scope, or effect changed; a new plan and confirmation are required.",
            )
        # `_resolve_current` already enforces current Thread ownership and
        # author identity. Re-check explicitly as a confirmation credential,
        # then bind the real user message and authenticated uid into the
        # Candidate's opaque receipt reference.
        decision = _require_user_thread_message(
            env, context["session"], user_message.id, "Confirmation"
        )
        effective_confirmation_id = confirmation_receipt_id(
            binding,
            owner_id=context["session"].owner_id.id,
            session_revision=context["session"].revision,
            proposal_revision=context["session"].proposal_revision,
            document_revision=context["session"].document_revision,
            decision_message_id=decision.id,
            confirmed_by_user_id=env.uid,
        )
    else:
        if user_message.id != binding["intent_message_id"]:
            return _public_result(
                "clarification_required", "plan_stale", action="edit",
                message="The user message changed after planning; create a new plan for the current request.",
            )

    # This internal seam is unavailable to Agent/RPC inputs. The public facade
    # keeps Provider processing fail-closed until the release gate is opened.
    if adapter is None or provider_client is None or not model or limits is None:
        return _public_result(
            "blocked", "provider_dispatch_disabled", action="edit",
            error_code="external_file_processing_not_authorized",
            message="Candidate B external file processing is disabled until the SRS/data-policy gate is approved.",
            current_version_id=context["current"].id,
        )

    session, current = context["session"], context["current"]
    idempotency_key = "cb04:" + digest_json({
        "session_id": session.id,
        "intent_message_id": binding["intent_message_id"],
        "parent_version_id": current.id,
        "effect_digest": binding["effect_digest"],
    })
    request_digest = digest_json({
        "binding": binding,
        "confirmation_receipt_id": effective_confirmation_id or False,
    })
    existing = _candidate_existing(env, session, idempotency_key)
    if existing:
        for _message, prior_result in _tool_results_before(env, thread, tool_message.id):
            if prior_result.get("action") == "edit" and prior_result.get("candidate_version_id") == existing.id:
                replay = dict(prior_result)
                replay.update({
                    "operation_executed": False,
                    "idempotent_replay": True,
                    "message": "This exact Intent already has a Candidate; the existing review result is reused and no second Provider request was made.",
                })
                return replay
        if (
            existing.state in {"verified", "partially_verified"}
            and existing.validation_result in {"VERIFIED", "PARTIALLY_VERIFIED"}
            and existing.parent_version_id == current
        ):
            partial = existing.validation_result == "PARTIALLY_VERIFIED"
            return _public_result(
                "confirmation_required", "candidate_review_required", action="edit",
                operation_executed=False,
                artifact_state="candidate_registered_not_presented",
                requires_user_acceptance=not partial,
                persisted_review_decision_supported=not partial,
                candidate_version_id=existing.id,
                candidate_state=existing.state,
                validation_result=existing.validation_result,
                validation_classification=(
                    "technical_checks_passed_business_effect_unverified"
                    if partial else "deterministic_expected_effect_checked_full_intent_unproven"
                ),
                receipt_sha256=existing.validation_report_sha256,
                verified_facts=[
                    f"Candidate attachment SHA-256 is {existing.output_sha256}.",
                    f"CB-03 validation status is {existing.validation_result}.",
                ],
                model_claims=[{"kind": "edit_summary", "text": normalized["summary"]}, *(model_risk_claims or [])],
                unverified_aspects=(
                    effect["unknowns"] + ["The local Validator does not independently establish full business-effect correctness."]
                ),
                current_version_id=session.current_version_id.id or False,
                last_valid_version_id=session.last_valid_version_id.id or False,
                document_revision=session.document_revision,
                message="The existing Candidate is available for the current user's review; no new edit was run.",
            )
        return _public_result(
            "failed", "idempotent_existing_candidate", action="edit",
            operation_executed=False,
            candidate_version_id=existing.id,
            candidate_state=existing.state,
            validation_result=existing.validation_result or False,
            current_version_id=session.current_version_id.id or False,
            message="An existing Candidate for this request is not reviewable; no second Provider request was made and Current remains unchanged.",
        )

    try:
        _require_user_thread_message(env, session, binding["intent_message_id"], "Intent")
        # Resolve bytes/revision again immediately before external work.
        fresh = _resolve_current(env, thread)
        if _version_facts(fresh) != _version_facts(context):
            raise ValidationError(_("WORKBOOK_VERSION_STALE: edit plan bindings changed."))
        intent_message = env["mail.message"].browse(binding["intent_message_id"])
        prompt = _message_text(intent_message)
        provider_result = adapter.execute(
            provider_client=provider_client,
            model=model,
            input_xlsx=fresh["input_bytes"],
            instruction=prompt,
            limits=limits,
            input_sha256=fresh["input_sha256"],
            correlation_id=binding["intent_digest"],
        )
        status = getattr(provider_result, "operation_status", None)
        candidate_bytes = getattr(provider_result, "candidate_bytes", None)
        if status != "candidate_received" or not isinstance(candidate_bytes, bytes) or not candidate_bytes:
            if status == "blocked":
                return _public_result(
                    "blocked", "provider_blocked", action="edit",
                    error_code=getattr(getattr(provider_result, "error", None), "category", "provider_blocked"),
                    provider=provider_result.to_dict(),
                    current_version_id=current.id,
                )
            return _public_result(
                "failed", "provider_candidate_unavailable", action="edit",
                error_code=getattr(getattr(provider_result, "error", None), "category", "provider_result_unavailable"),
                provider=provider_result.to_dict(),
                current_version_id=current.id,
                message="The Provider did not return a reliable XLSX candidate; Current remains unchanged.",
            )

        provider_ids = getattr(provider_result, "provider_file_ids", ()) or ()
        cleanup = getattr(provider_result, "cleanup_state", "not_required")
        cleanup_map = {
            "not_required": "not_applicable", "completed": "complete",
            "cleanup_pending": "pending", "unknown": "pending",
        }
        candidate = register_candidate(
            env,
            session.id,
            parent_version_id=current.id,
            expected_document_revision=session.document_revision,
            candidate_bytes=candidate_bytes,
            filename=(
                getattr(provider_result, "provider_filename", None)
                if (getattr(provider_result, "provider_filename", "") or "").lower().endswith(".xlsx")
                else (current.filename or "candidate.xlsx")
            ),
            mimetype=XLSX_MIME,
            idempotency_key=idempotency_key,
            request_digest=request_digest,
            intent_message_id=binding["intent_message_id"],
            intent_effect_digest=binding["effect_digest"],
            confirmation_receipt_id=effective_confirmation_id,
            provider_id="openai-responses",
            provider_model=model,
            provider_response_id=getattr(provider_result, "provider_response_id", False),
            provider_tool_call_id=(getattr(provider_result, "tool_call_ids", ()) or (False,))[0],
            provider_file_id=(provider_ids or (False,))[0],
            provider_usage_json=getattr(provider_result, "usage", {}) or {},
            provider_cleanup_state=cleanup_map.get(cleanup, "pending"),
        )
        validation = validate_workbook_candidate(env, session.id, candidate.id, effect)
        candidate.invalidate_recordset()
        session.invalidate_recordset()
        validation_result = validation["validation_result"]
        base = {
            "action": "edit",
            "operation_executed": True,
            "candidate_version_id": candidate.id,
            "candidate_state": candidate.state,
            "candidate_filename": candidate.output_attachment_id.name,
            # Authenticated /web/content rechecks attachment ACL and record rules;
            # this link exposes the real Candidate bytes without making them public.
            "candidate_download_url": f"/web/content/{candidate.output_attachment_id.id}?download=true",
            "candidate_output_sha256": candidate.output_sha256,
            "validation_result": validation_result,
            "validation_classification": (
                "technical_checks_passed_business_effect_unverified"
                if validation_result == "PARTIALLY_VERIFIED"
                else "deterministic_expected_effect_checked_full_intent_unproven"
                if validation_result == "VERIFIED"
                else "technical_validation_failed"
            ),
            "receipt_sha256": validation.get("receipt_sha256"),
            "verified_facts": [
                f"Current parent version ID: {current.id}",
                f"Input bytes SHA-256 matched the accepted parent: {fresh['input_sha256']}",
                f"Candidate attachment SHA-256 matched its registered bytes: {candidate.output_sha256}",
                f"CB-03 validation status: {validation_result}",
            ],
            # CB-03's deterministic report is unchanged. CC-04 exposes observed
            # differences but does not consume its legacy `risk_facts` label
            # as a business-risk decision or confirmation trigger.
            "risk_facts": [],
            "actual_effects": validation["report"].get("actual_effects", []),
            "feature_results": validation["report"].get("feature_results", []),
            "unknowns": validation["report"].get("unknowns", []),
            "model_claims": [
                {"kind": "edit_summary", "text": normalized["summary"]},
                *plan_result.get("model_claims", []),
            ],
            "operation_summary": normalized["summary"],
            "assumptions": normalized["assumptions"],
            "unverified_aspects": list(validation["report"].get("unknowns", [])),
            "binding": binding,
            "provider": provider_result.to_dict(),
            "current_version_id": session.current_version_id.id or False,
            "last_valid_version_id": session.last_valid_version_id.id or False,
            "document_revision": session.document_revision,
            "confirmation_receipt_id": effective_confirmation_id or False,
        }
        if validation_result not in {"VERIFIED", "PARTIALLY_VERIFIED"}:
            _logger.warning(
                "Office Candidate technical validation failed candidate_id=%s result=%s error=%s",
                candidate.id, validation_result, validation["report"].get("error"),
            )
            return _public_result(
                "failed", "candidate_technical_validation_failed", **base,
                message="The Candidate failed a deterministic CB-03 validation check; it cannot be accepted and Current remains unchanged.",
            )
        if validation_result == "PARTIALLY_VERIFIED":
            if not base["unverified_aspects"]:
                base["unverified_aspects"].append(
                    "The requested business effect is not fully proven by the local Validator."
                )
            base["unverified_aspects"].append(
                "The workbook passed applicable deterministic checks, but business-effect completeness and correctness remain for the user to review."
            )
        else:
            base["unverified_aspects"].append(
                "The local Validator does not prove complete business correctness or completeness of the natural-language request."
            )
        base.update({
            "artifact_state": "candidate_registered_not_presented",
            "requires_user_acceptance": True,
            "persisted_review_decision_supported": True,
            "message": (
                "A Candidate was generated and passed the applicable technical checks. It is not Current and has not been finalized or delivered. "
                "Review the Candidate workbook at candidate_download_url and inspect verified_facts, actual_effects, model_claims, "
                "and unverified_aspects. The current user may reply 接受 or 拒绝; a PARTIALLY_VERIFIED grade remains unchanged."
            ),
        })
        return _public_result(
            "confirmation_required", "candidate_review_required", **base,
        )
    except AccessError:
        raise
    except (ValidationError, IntentContractError) as exc:
        message = str(exc)
        stale = "WORKBOOK_VERSION_STALE" in message or "changed" in message.lower()
        return _public_result(
            "clarification_required" if stale else "failed",
            "stale_binding" if stale else "candidate_execution_failed",
            action="edit", error_code="workbook_version_stale" if stale else "candidate_execution_failed",
            current_version_id=session.current_version_id.id or False,
            message="The planned edit no longer matches the current file/revision." if stale else "Candidate processing failed; Current was not intentionally advanced.",
        )
    except Exception as exc:
        # Keep the detail in the server log for diagnosis; never expose exception
        # text or workbook contents through the public Agent result.
        _logger.exception(
            "Office Candidate orchestration failed (session_id=%s, parent_version_id=%s, intent_message_id=%s)",
            context["session"].id,
            context["current"].id,
            binding.get("intent_message_id"),
        )
        return _public_result(
            "failed", "candidate_execution_failed", action="edit",
            error_code=type(exc).__name__.lower(),
            current_version_id=context["session"].current_version_id.id or False,
            message="Candidate processing failed; Current was not intentionally advanced.",
        )


def review_candidate(env, thread, tool_message, decision):
    context = _resolve_current(env, thread)
    if decision not in {_ACCEPT, _REJECT} or _message_text(context["user_message"]) != decision:
        return _public_result(
            "clarification_required", "review_decision_invalid", action="accept" if decision == _ACCEPT else "reject",
            message="Reply exactly 接受 or 拒绝 to decide the latest reviewable Candidate.",
        )
    _edit_message, edit_result = _latest_edit(env, context, tool_message)
    if not edit_result:
        return _public_result("clarification_required", "candidate_not_found", action="accept" if decision == _ACCEPT else "reject")
    candidate_id = edit_result.get("candidate_version_id")
    candidate = _require_version(env, context["session"], candidate_id, write=True)
    if (
        candidate.version_kind != "edit"
        or candidate.state not in {"verified", "partially_verified"}
        or candidate.validation_result not in {"VERIFIED", "PARTIALLY_VERIFIED"}
        or candidate.parent_version_id != context["current"]
        or candidate.document_revision != context["session"].document_revision
        or candidate.intent_message_id.id != edit_result.get("binding", {}).get("intent_message_id", candidate.intent_message_id.id)
    ):
        return _public_result(
            "blocked", "candidate_not_reviewable", action="accept" if decision == _ACCEPT else "reject",
            message="Only a Candidate with successful applicable technical checks and a current parent can be reviewed.",
            current_version_id=context["current"].id,
        )
    review_fields = _candidate_artifact_review_fields(env, candidate, edit_result)
    if decision == _REJECT:
        rejection = CandidateRejection(
            candidate_version_id=candidate.id,
            session_id=context["session"].id,
            owner_id=env.uid,
            intent_message_id=candidate.intent_message_id.id,
            decision_message_id=context["user_message"].id,
            parent_version_id=candidate.parent_version_id.id,
            document_revision=candidate.document_revision,
            output_sha256=candidate.output_sha256,
            effect_digest=candidate.intent_effect_digest or False,
        )
        rejected = reject_verified_candidate(env, candidate.id, rejection)
        return _public_result(
            "completed", "candidate_rejected", action="reject", operation_executed=True,
            candidate_version_id=rejected.id, candidate_state=rejected.state,
            validation_result=rejected.validation_result,
            current_version_id=context["session"].current_version_id.id,
            last_valid_version_id=context["session"].last_valid_version_id.id,
            document_revision=context["session"].document_revision,
            **review_fields,
            message=(
                "The Candidate was rejected; Current and Last Valid remain unchanged. "
                "Its original validation grade and unverified aspects remain recorded."
            ),
        )
    authorization = CandidateAcceptanceAuthorization(
        authorization_kind="candidate_review",
        candidate_version_id=candidate.id,
        session_id=context["session"].id,
        owner_id=env.uid,
        thread_id=thread.id,
        intent_message_id=candidate.intent_message_id.id,
        decision_message_id=context["user_message"].id,
        parent_version_id=candidate.parent_version_id.id,
        document_revision=candidate.document_revision,
        output_sha256=candidate.output_sha256,
        effect_digest=candidate.intent_effect_digest or False,
    )
    accepted = accept_verified_candidate(env, candidate.id, authorization)
    context["session"].invalidate_recordset()
    return _public_result(
        "completed", "accepted_current", action="accept", operation_executed=True,
        candidate_version_id=accepted.id, candidate_state=accepted.state,
        validation_result=accepted.validation_result,
        current_version_id=context["session"].current_version_id.id,
        last_valid_version_id=context["session"].last_valid_version_id.id,
        document_revision=context["session"].document_revision,
        **review_fields,
        message=(
            "The user accepted the Candidate; its validation grade is unchanged. "
            "Any unverified business aspects remain unverified. Finalize and delivery remain separate."
        ),
    )


def dispatch_office_action(
    env, thread, tool_message, action, query_spec=None, interpretation=None, expected_effect=None,
    model_risk_claims=None, candidate_version_id=None, confirmation_required=None,
    confirmation_reason=None,
):
    """Entry used only by the single ``office`` Agent Tool facade."""
    try:
        if action == "retrieve":
            return _retrieve_odoo_data(env, thread, tool_message, query_spec)
        context = _resolve_current(env, thread)
        if action == "status":
            return _public_result("completed", "current_version_status", action=action, **_version_facts(context))
        if action == "plan":
            return plan_edit(
                env, thread, tool_message, interpretation, expected_effect, model_risk_claims,
                confirmation_required=confirmation_required,
                confirmation_reason=confirmation_reason,
            )
        if action == "edit":
            # The external processing gate is intentionally fail-closed. Only
            # the dedicated loopback synthetic browser process may install the
            # test-only expected-effect adapter; no Agent/RPC parameter can
            # select or enable it.
            dependencies = None
            try:
                from ..tests.support.browser_simulation import dependencies_for

                dependencies = dependencies_for(env, thread, tool_message)
            except Exception:
                _logger.exception("CC-04 synthetic browser adapter setup failed")
            if dependencies:
                adapter, provider_client, model, limits = dependencies
                return execute_planned_edit(
                    env, thread, tool_message, interpretation, expected_effect,
                    model_risk_claims, adapter=adapter, provider_client=provider_client,
                    model=model, limits=limits,
                    confirmation_required=confirmation_required,
                    confirmation_reason=confirmation_reason,
                )
            return _public_result(
                "blocked", "provider_dispatch_disabled", action=action,
                error_code="external_file_processing_not_authorized",
                current_version_id=context["current"].id,
                message="External Candidate B file processing is disabled pending the SRS/data-policy release gate.",
            )
        if action in {"accept", "reject"}:
            if candidate_version_id:
                return _public_result(
                    "blocked", "candidate_identity_not_authoritative", action=action,
                    message="Candidate identity is derived from this Thread's persisted Office tool history, not a model-supplied ID.",
                )
            return review_candidate(env, thread, tool_message, _ACCEPT if action == "accept" else _REJECT)
        return _public_result("clarification_required", "action_invalid", action=action, message="Unsupported Office action.")
    except AccessError:
        raise
    except ValidationError as exc:
        message = str(exc)
        stale = "WORKBOOK_VERSION_STALE" in message or "stale" in message.lower()
        confirmation_mismatch = "confirmation" in message.lower()
        return _public_result(
            "clarification_required" if (stale or confirmation_mismatch) else "blocked",
            "stale_binding" if stale else "confirmation_binding_invalid" if confirmation_mismatch else "context_unavailable",
            action=action,
            error_code="workbook_version_stale" if stale else "confirmation_binding_invalid" if confirmation_mismatch else "office_context_unavailable",
            message=(
                "The current file or revision changed; create a new plan."
                if stale else "Repeat the unchanged model confirmation decision and reason from the saved plan."
                if confirmation_mismatch else "The current Office context cannot be used."
            ),
        )
