"""Current-user ORM bridge from a CB-02 Candidate to the bounded pure verifier."""

from __future__ import annotations

import hashlib
import json
import time

from odoo import _, fields
from odoo.exceptions import ValidationError
from odoo.addons.office_engine_odoo.models.office_document_request import _load_trusted_python_package

from .workbook_version_service import (
    ValidationReceipt,
    _check_version_attachment,
    _read_attachment,
    _require_session,
    _require_user_thread_message,
    _require_version,
    record_validation_receipt,
)


_office_verify = _load_trusted_python_package("office_verify")
_CANDIDATE_POLICY_VERSION = "office_verify.candidate.xlsx.v1"
_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _bound_candidate(env, session_id, candidate_version_id, expected_effect):
    session = _require_session(env, session_id, write=True)
    candidate = _require_version(env, session, candidate_version_id, write=True)
    if candidate.state != "candidate_received":
        raise ValidationError(_("Only a received Candidate can be validated."))
    if candidate.version_kind == "initial":
        if candidate.parent_version_id or candidate.source_request_id:
            raise ValidationError(_("The initial Candidate source binding is invalid."))
        if (
            session.current_version_id
            or session.document_revision != 0
            or candidate.document_revision != 0
            or candidate.input_attachment_id != session.source_attachment_id
            or candidate.source_message_id != session.source_message_id
        ):
            raise ValidationError(_("WORKBOOK_VERSION_STALE: the initial Candidate no longer matches its upload."))
        if not candidate.intent_message_id:
            raise ValidationError(_("The initial Candidate has no bound user Intent message."))
        _require_user_thread_message(env, session, candidate.intent_message_id.id, "Intent")
        parent = False
        input_attachment = session.source_attachment_id
    elif candidate.version_kind == "edit" and candidate.parent_version_id:
        parent = _require_version(env, session, candidate.parent_version_id.id)
        if parent.state not in {"accepted_current", "finalized"}:
            raise ValidationError(_("The Candidate parent version is no longer valid."))
        if (
            session.current_version_id != parent
            or session.document_revision != candidate.document_revision
            or session.revision != candidate.session_revision
            or session.proposal_revision != candidate.proposal_revision
            or parent.accepted_document_revision != candidate.document_revision
        ):
            raise ValidationError(_("WORKBOOK_VERSION_STALE: the Candidate no longer matches the current document."))
        _check_version_attachment(parent, parent.output_attachment_id)
        input_attachment = parent.output_attachment_id
    else:
        raise ValidationError(_("Only an initial or edit Candidate can be validated."))
    _check_version_attachment(candidate, candidate.output_attachment_id)
    if candidate.input_attachment_id != input_attachment:
        raise ValidationError(_("The Candidate input is not the recorded parent output."))
    input_bytes, input_sha = _read_attachment(
        env, input_attachment, expected_sha=parent.output_sha256 if parent else False
    )
    candidate_input, candidate_input_sha = _read_attachment(
        env, candidate.input_attachment_id, expected_sha=candidate.input_sha256
    )
    output_bytes, output_sha = _read_attachment(
        env, candidate.output_attachment_id, expected_sha=candidate.output_sha256
    )
    if input_sha != candidate.input_sha256 or candidate_input_sha != input_sha or candidate_input != input_bytes:
        raise ValidationError(_("The Candidate source bytes do not match its parent binding."))
    if output_sha != candidate.output_sha256 or candidate.file_size != len(output_bytes):
        raise ValidationError(_("The Candidate output bytes do not match its stored binding."))
    if candidate.mimetype != _XLSX_MIME or not (candidate.filename or "").lower().endswith(".xlsx"):
        raise ValidationError(_("The Candidate is not a supported XLSX file."))
    if not isinstance(expected_effect, dict):
        raise ValidationError(_("Expected Effect must be a structured object."))
    if (
        expected_effect.get("parent_version_id") != (parent.id if parent else 0)
        or expected_effect.get("input_sha256") != input_sha
        or expected_effect.get("effect_digest") != candidate.intent_effect_digest
    ):
        raise ValidationError(_("Expected Effect is stale or is not bound to this Candidate."))
    return session, parent, candidate, input_bytes, input_sha, output_bytes, output_sha


def _failed_report(source_sha, output_sha, parent_id, effect_digest, error):
    return _office_verify.CandidateValidationReport(
        validation_result="FAILED",
        input_sha256=source_sha,
        output_sha256=output_sha,
        parent_version_id=parent_id,
        effect_digest=effect_digest,
        actual_effects=(),
        risk_facts=(),
        feature_results=(),
        error=error.as_dict(),
    )


def validate_workbook_candidate(env, session_id, candidate_version_id, expected_effect):
    """Validate and register one typed result; never accepts or advances a version.

    The callable is an internal Python service, not a model method or RPC endpoint.
    All Session, Version and Attachment reads use the caller's current ORM env.
    """
    session, parent, candidate, source_bytes, source_sha, output_bytes, output_sha = _bound_candidate(
        env, session_id, candidate_version_id, expected_effect
    )
    budget = _office_verify.VerificationBudget()
    policy = _office_verify.VerificationPolicy(enabled_formats=("xlsx",))
    started_monotonic = time.monotonic()
    started_at = fields.Datetime.now()
    try:
        report, worker_metrics = _office_verify.verify_candidate_output_with_metrics(
            source_bytes,
            output_bytes,
            candidate.filename,
            candidate.mimetype,
            expected_effect,
            policy=policy,
            budget=budget,
        )
    except _office_verify.OfficeVerifyError as error:
        report = _failed_report(source_sha, output_sha, parent.id if parent else 0, candidate.intent_effect_digest, error)
        worker_metrics = getattr(error, "execution_metrics", None) or {
            "elapsed_seconds": max(0.0, time.monotonic() - started_monotonic),
            "rss_observed": False,
            "max_observed_rss_bytes": None,
        }
    completed_at = fields.Datetime.now()
    execution = {
        "started_at": fields.Datetime.to_string(started_at),
        "completed_at": fields.Datetime.to_string(completed_at),
        "elapsed_seconds": worker_metrics["elapsed_seconds"],
        "rss_observed": worker_metrics["rss_observed"],
        "max_observed_rss_bytes": worker_metrics["max_observed_rss_bytes"],
        "worker_exited": worker_metrics.get("worker_exited", False),
        "source_file_size": len(source_bytes),
        "candidate_file_size": len(output_bytes),
    }
    report_payload = report.as_dict()
    audit_payload = {
        "schema_version": "1",
        "candidate_version_id": candidate.id,
        "session_id": session.id,
        "session_revision": candidate.session_revision,
        "proposal_revision": candidate.proposal_revision,
        "document_revision": candidate.document_revision,
        "parent_version_id": parent.id if parent else 0,
        "validator_policy_version": _CANDIDATE_POLICY_VERSION,
        "source_sha256": source_sha,
        "candidate_output_sha256": output_sha,
        "effect_digest": candidate.intent_effect_digest,
        "report": report_payload,
        "execution": execution,
        "budget": {
            "max_file_size": budget.max_file_size,
            "max_expanded_size": budget.max_expanded_size,
            "max_zip_entries": budget.max_zip_entries,
            "max_entry_size": budget.max_entry_size,
            "max_xml_elements": budget.max_xml_elements,
            "max_cells": budget.max_cells,
            "max_mapping_bytes": budget.max_mapping_bytes,
            "max_expected_effect_bytes": budget.max_expected_effect_bytes,
            "max_memory_bytes": budget.max_memory_bytes,
            "timeout_seconds": budget.timeout_seconds,
            "source_file_size": len(source_bytes),
            "candidate_file_size": len(output_bytes),
        },
    }
    encoded = json.dumps(audit_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    report_sha = hashlib.sha256(encoded).hexdigest()
    receipt = ValidationReceipt(
        candidate_version_id=candidate.id,
        candidate_output_sha256=output_sha,
        validator_policy_version=_CANDIDATE_POLICY_VERSION,
        validation_report_id=report_sha,
        validation_report_sha256=report_sha,
        validation_result=report.validation_result,
        session_id=session.id,
        session_revision=candidate.session_revision,
        proposal_revision=candidate.proposal_revision,
        document_revision=candidate.document_revision,
        parent_version_id=parent.id if parent else False,
        input_sha256=source_sha,
        effect_digest=candidate.intent_effect_digest or False,
    )
    # CB-02 rechecks permissions, revisions, parent, proof fields and actual
    # attachment bytes before it records this result. No current pointer changes
    # occur here; only the separate CB-02 accept_verified_candidate call may accept.
    record_validation_receipt(env, candidate.id, receipt)
    candidate.invalidate_recordset()
    session.invalidate_recordset()
    return {
        "candidate_version_id": candidate.id,
        "candidate_state": candidate.state,
        "validation_result": candidate.validation_result,
        "receipt_sha256": report_sha,
        "report": report_payload,
        "execution": execution,
        "budget": audit_payload["budget"],
        "current_version_id": session.current_version_id.id or False,
        "last_valid_version_id": session.last_valid_version_id.id or False,
        "document_revision": session.document_revision,
    }
