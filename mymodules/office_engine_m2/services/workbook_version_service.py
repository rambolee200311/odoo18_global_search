"""Current-user ORM services for private workbook version lineage.

This module exposes no Odoo model/RPC method for accepting validation proofs.
Trusted in-process M1/CB-03 callers pass typed receipts; tests construct receipts
only through the test-only stub under ``tests/support``.
"""

from __future__ import annotations

import contextvars
import hashlib
import json
import re
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import PurePath

from odoo import _, fields
from odoo.exceptions import AccessError, ValidationError
from odoo.addons.office_engine_odoo.models.office_document_request import M1_VALIDATOR_POLICY_VERSION

from ..models.office_workbook_version import _VERSION_MUTATION


MAX_VERSION_BYTES = 32 * 1024 * 1024
_HASH = re.compile(r"^[0-9a-f]{64}$")
_POLICY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_MIME_TYPES = {
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


@dataclass(frozen=True)
class ValidationReceipt:
    candidate_version_id: int
    candidate_output_sha256: str
    validator_policy_version: str
    validation_report_id: str
    validation_report_sha256: str
    validation_result: str
    session_id: int
    session_revision: int
    proposal_revision: int
    document_revision: int
    parent_version_id: int | bool
    input_sha256: str
    effect_digest: str | bool


@dataclass(frozen=True)
class ConfirmationReceipt:
    """Typed restore confirmation, never accepted from a user/RPC payload."""

    receipt_id: str
    session_id: int
    owner_id: int
    current_version_id: int
    source_version_id: int
    document_revision: int
    output_sha256: str
    effect_digest: str
    operation: str
    intent_message_id: int
    decision_message_id: int


@dataclass(frozen=True)
class CandidateAcceptanceAuthorization:
    """Trusted in-process authorization bound to one edit Candidate and real user decision."""

    authorization_kind: str
    candidate_version_id: int
    session_id: int
    owner_id: int
    thread_id: int
    intent_message_id: int
    decision_message_id: int
    parent_version_id: int
    document_revision: int
    output_sha256: str
    effect_digest: str | bool
    confirmation_receipt_id: str | bool = False


@dataclass(frozen=True)
class CandidateRejection:
    """Trusted in-process rejection of one reviewable, non-current candidate."""

    candidate_version_id: int
    session_id: int
    owner_id: int
    intent_message_id: int
    decision_message_id: int
    parent_version_id: int
    document_revision: int
    output_sha256: str
    effect_digest: str | bool


@contextmanager
def _version_mutation():
    token = _VERSION_MUTATION.set(True)
    try:
        yield
    finally:
        _VERSION_MUTATION.reset(token)


def _require_hash(value, label, *, optional=False):
    if optional and value in (None, False, ""):
        return False
    if not isinstance(value, str) or not _HASH.fullmatch(value):
        raise ValidationError(_("Invalid %(label)s digest.", label=label))
    return value


def _require_idempotency_key(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 128 or "\x00" in value:
        raise ValidationError(_("Invalid workbook version idempotency key."))
    return value


def _require_confirmation_reference(value):
    if value in (None, False, ""):
        return False
    if (
        not isinstance(value, str)
        or len(value) > 128
        or any(ord(char) < 32 for char in value)
    ):
        raise ValidationError(_("Invalid workbook confirmation reference."))
    return value


def _filename_and_mimetype(filename, mimetype):
    if not isinstance(filename, str) or not filename or len(filename) > 255:
        raise ValidationError(_("Invalid workbook filename."))
    if PurePath(filename).name != filename or "/" in filename or "\\" in filename:
        raise ValidationError(_("Workbook filenames cannot contain paths."))
    extension = PurePath(filename).suffix.lower()
    if extension not in _MIME_TYPES or mimetype != _MIME_TYPES[extension]:
        raise ValidationError(_("The workbook filename and content type do not match."))
    return filename, mimetype


def _require_session(env, session_id, *, write=False):
    if isinstance(session_id, bool) or not isinstance(session_id, int) or session_id < 1:
        raise AccessError(_("The workbook Session is unavailable."))
    session = env["office.mapping.session"].browse(session_id).exists()
    if not session:
        raise AccessError(_("The workbook Session is unavailable."))
    session.check_access("write" if write else "read")
    if session.owner_id.id != env.uid or session.thread_id.user_id.id != env.uid:
        raise AccessError(_("The workbook Session is unavailable."))
    session.thread_id.check_access("read")
    if session.company_id.id not in env.companies.ids:
        raise AccessError(_("The workbook Session is unavailable."))
    return session


def _require_user_thread_message(env, session, message_id, label):
    if isinstance(message_id, bool) or not isinstance(message_id, int) or message_id < 1:
        raise AccessError(_("The %(label)s message is unavailable.", label=label))
    message = env["mail.message"].browse(message_id).exists()
    if not message:
        raise AccessError(_("The %(label)s message is unavailable.", label=label))
    message.check_access("read")
    if (
        message.model != session.thread_id._name
        or message.res_id != session.thread_id.id
        or message.author_id != session.owner_id.partner_id
        or getattr(message, "llm_role", False) != "user"
        or getattr(message, "is_error", False)
    ):
        raise AccessError(_("The %(label)s message is unavailable.", label=label))
    return message


def _latest_thread_message(env, session):
    """Capture a same-Thread message sequence boundary for post-Candidate decisions."""
    message = env["mail.message"].search(
        [("model", "=", session.thread_id._name), ("res_id", "=", session.thread_id.id)],
        order="id desc",
        limit=1,
    )
    if not message:
        raise ValidationError(_("The workbook Thread has no review watermark message."))
    message.check_access("read")
    return message


def _authorization_payload(authorization):
    return {
        "authorization_kind": authorization.authorization_kind,
        "candidate_version_id": authorization.candidate_version_id,
        "session_id": authorization.session_id,
        "owner_id": authorization.owner_id,
        "thread_id": authorization.thread_id,
        "intent_message_id": authorization.intent_message_id,
        "decision_message_id": authorization.decision_message_id,
        "parent_version_id": authorization.parent_version_id,
        "document_revision": authorization.document_revision,
        "output_sha256": authorization.output_sha256,
        "effect_digest": authorization.effect_digest or False,
        "confirmation_receipt_id": authorization.confirmation_receipt_id or False,
    }


def _authorization_digest(authorization):
    return hashlib.sha256(
        json.dumps(_authorization_payload(authorization), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _validate_candidate_acceptance_authorization(env, candidate, authorization):
    if not isinstance(authorization, CandidateAcceptanceAuthorization):
        raise AccessError(_("A trusted, scoped Candidate acceptance authorization is required."))
    if not isinstance(authorization.authorization_kind, str):
        raise ValidationError(_("The acceptance authorization kind is invalid."))
    confirmation_receipt_id = authorization.confirmation_receipt_id
    if confirmation_receipt_id not in (False, None, "") and (
        not isinstance(confirmation_receipt_id, str)
        or len(confirmation_receipt_id) > 128
        or any(ord(char) < 32 for char in confirmation_receipt_id)
    ):
        raise ValidationError(_("The confirmation reference is invalid."))
    session = _require_session(env, candidate.session_id.id, write=True)
    if candidate.version_kind != "edit":
        raise ValidationError(_("Only an edit Candidate can use edit authorization."))
    reviewable_result_states = {
        "VERIFIED": {"verified", "accepted_current", "superseded", "finalized"},
        "PARTIALLY_VERIFIED": {"partially_verified", "accepted_current", "superseded", "finalized"},
    }
    if (
        candidate.validation_result not in reviewable_result_states
        or candidate.state not in reviewable_result_states[candidate.validation_result]
        or candidate.validation_result == "PARTIALLY_VERIFIED" and candidate.version_kind != "edit"
    ):
        raise ValidationError(_("Only a technically reviewable Candidate can use edit acceptance authorization."))
    if (
        any(type(value) is not int or value < 1 for value in (
            authorization.candidate_version_id,
            authorization.session_id,
            authorization.owner_id,
            authorization.thread_id,
            authorization.intent_message_id,
            authorization.decision_message_id,
            authorization.parent_version_id,
        ))
        or type(authorization.document_revision) is not int
        or authorization.document_revision < 0
        or authorization.authorization_kind not in {"explicit_intent", "confirmed_intent", "candidate_review"}
        or authorization.candidate_version_id != candidate.id
        or authorization.session_id != session.id
        or authorization.owner_id != env.uid
        or authorization.thread_id != session.thread_id.id
        or authorization.intent_message_id != candidate.intent_message_id.id
        or authorization.parent_version_id != candidate.parent_version_id.id
        or authorization.document_revision != candidate.document_revision
        or authorization.output_sha256 != candidate.output_sha256
        or (authorization.effect_digest or False) != (candidate.intent_effect_digest or False)
    ):
        raise ValidationError(_("The acceptance authorization does not match this Candidate and its bound effect."))
    intent = _require_user_thread_message(env, session, authorization.intent_message_id, "Intent")
    decision = _require_user_thread_message(env, session, authorization.decision_message_id, "decision")
    if authorization.authorization_kind == "explicit_intent":
        if decision != intent or candidate.requires_confirmation or not authorization.effect_digest:
            raise ValidationError(_("Explicit authorization must match an unconfirmed, effect-bound user Intent."))
        if authorization.confirmation_receipt_id:
            raise ValidationError(_("Explicit authorization cannot carry a confirmation receipt."))
    elif authorization.authorization_kind == "confirmed_intent":
        if (
            decision.id <= intent.id
            or not candidate.requires_confirmation
            or not authorization.confirmation_receipt_id
            or candidate.confirmation_receipt_id != authorization.confirmation_receipt_id
            or not authorization.effect_digest
        ):
            raise ValidationError(_("The confirmation authorization is missing or no longer matches the Candidate."))
    else:  # candidate_review
        watermark = candidate.candidate_review_watermark_message_id
        if not watermark or decision.id <= max(intent.id, watermark.id):
            raise ValidationError(_("The Candidate review decision predates the Candidate."))
        if authorization.confirmation_receipt_id:
            raise ValidationError(_("A Candidate review decision cannot reuse a confirmation receipt."))
    return _authorization_digest(authorization)


def _rejection_digest(decision):
    payload = {
        "candidate_version_id": decision.candidate_version_id,
        "session_id": decision.session_id,
        "owner_id": decision.owner_id,
        "intent_message_id": decision.intent_message_id,
        "decision_message_id": decision.decision_message_id,
        "parent_version_id": decision.parent_version_id,
        "document_revision": decision.document_revision,
        "output_sha256": decision.output_sha256,
        "effect_digest": decision.effect_digest or False,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _require_version(env, session, version_id, *, write=False):
    if isinstance(version_id, bool) or not isinstance(version_id, int) or version_id < 1:
        raise AccessError(_("The workbook version is unavailable."))
    version = env["office.workbook.version"].browse(version_id).exists()
    if not version:
        raise AccessError(_("The workbook version is unavailable."))
    version.check_access("write" if write else "read")
    if (
        version.session_id != session
        or version.owner_id.id != env.uid
        or version.company_id != session.company_id
        or version.thread_id != session.thread_id
    ):
        raise AccessError(_("The workbook version is unavailable."))
    return version


def _read_attachment(env, attachment, *, expected_sha=False):
    if not attachment or len(attachment) != 1:
        raise AccessError(_("The workbook attachment is unavailable."))
    attachment.check("read")
    if attachment.type != "binary" or attachment.url or attachment.public:
        raise AccessError(_("The workbook attachment is unavailable."))
    if attachment.file_size <= 0 or attachment.file_size > MAX_VERSION_BYTES:
        raise ValidationError(_("The workbook attachment is empty or exceeds the size limit."))
    content = attachment.raw or b""
    if len(content) != attachment.file_size or len(content) > MAX_VERSION_BYTES:
        raise ValidationError(_("The workbook attachment bytes are incomplete or exceed the size limit."))
    digest = hashlib.sha256(content).hexdigest()
    if expected_sha and digest != expected_sha:
        raise ValidationError(_("The workbook attachment digest does not match its version."))
    return content, digest


def _check_version_attachment(version, attachment):
    attachment.check("read")
    if (
        attachment.res_model != version._name
        or attachment.res_id != version.id
        or attachment.public
        or attachment.type != "binary"
        or attachment.url
        or attachment.company_id != version.company_id
    ):
        raise AccessError(_("The workbook version attachment is unavailable."))
    return attachment


def _lock_session(session):
    """Lock only after ORM authorization; reread all state through ORM."""
    session.ensure_one()
    session.check_access("write")
    if session.owner_id.id != session.env.uid:
        raise AccessError(_("The workbook Session is unavailable."))
    session.flush_recordset(["document_revision", "current_version_id"])
    session.env.cr.execute(
        "SELECT id FROM office_mapping_session WHERE id = %s FOR UPDATE", [session.id]
    )
    if not session.env.cr.fetchone():
        raise AccessError(_("The workbook Session is unavailable."))
    session.invalidate_recordset(["document_revision", "current_version_id"])
    fresh = session.browse(session.id).exists()
    fresh.check_access("write")
    return fresh


def _next_version_number(env, session):
    latest = env["office.workbook.version"].search(
        [("session_id", "=", session.id)], order="version_no desc, id desc", limit=1
    )
    return (latest.version_no if latest else 0) + 1


def _version_metadata(version):
    """Return a bounded, read-authorized version summary without file bytes."""
    version.check_access("read")
    if version.output_attachment_id:
        version.output_attachment_id.check_access("read")
    if version.final_attachment_id:
        version.final_attachment_id.check_access("read")
    if version.final_message_id:
        version.final_message_id.check_access("read")
    return {
        "version_id": version.id,
        "version_uuid": version.version_uuid,
        "session_id": version.session_id.id,
        "version_no": version.version_no,
        "version_kind": version.version_kind,
        "state": version.state,
        "parent_version_id": version.parent_version_id.id or False,
        "restored_from_version_id": version.restored_from_version_id.id or False,
        "source_message_id": version.source_message_id.id or False,
        "intent_message_id": version.intent_message_id.id or False,
        "document_revision": version.document_revision,
        "accepted_document_revision": version.accepted_document_revision,
        "input_sha256": version.input_sha256 or False,
        "output_sha256": version.output_sha256 or False,
        "filename": version.filename or False,
        "mimetype": version.mimetype or False,
        "file_size": version.file_size or 0,
        "validation_result": version.validation_result or False,
        "acceptance_authorization_kind": version.acceptance_authorization_kind or False,
        "acceptance_authorization_message_id": version.acceptance_authorization_message_id.id or False,
        "acceptance_authorization_digest": version.acceptance_authorization_digest or False,
        "rejection_message_id": version.rejection_message_id.id or False,
        "rejection_digest": version.rejection_digest or False,
        "delivery_state": version.delivery_state,
        "final_attachment_id": version.final_attachment_id.id or False,
        "final_message_id": version.final_message_id.id or False,
        "error_code": version.error_code or False,
    }


def get_workbook_version(env, session_id, version_id):
    """Read one version summary after rechecking the current user's Session scope."""
    session = _require_session(env, session_id)
    version = _require_version(env, session, version_id)
    return _version_metadata(version)


def list_workbook_versions(env, session_id, *, limit=100):
    """List bounded version metadata for one authorized Session."""
    session = _require_session(env, session_id)
    if type(limit) is not int or not 1 <= limit <= 200:
        raise ValidationError(_("The workbook version list limit must be between 1 and 200."))
    versions = env["office.workbook.version"].search(
        [("session_id", "=", session.id)], order="version_no desc, id desc", limit=limit
    )
    return [_version_metadata(version) for version in versions]


def _create_version_row(env, values):
    with _version_mutation():
        return env["office.workbook.version"].create(values)


def _write_version(version, values):
    with _version_mutation():
        version.write(values)


def _create_version_attachment(env, version, filename, mimetype, content):
    version.check_access("write")
    with _version_mutation():
        return env["ir.attachment"].create(
            {
                "name": filename,
                "type": "binary",
                "raw": content,
                "mimetype": mimetype,
                "company_id": version.company_id.id,
                "public": False,
                "res_model": version._name,
                "res_id": version.id,
            }
        )


def _same_idempotent_result(
    existing, *, parent_id, input_sha, output_sha, request_digest, effect_digest, kind,
    source_version_id=False, intent_message_id=False, confirmation_receipt_id=False,
):
    if (
        (existing.parent_version_id.id or False) != (parent_id or False)
        or existing.input_sha256 != input_sha
        or existing.output_sha256 != output_sha
        or existing.request_digest != request_digest
        or (existing.intent_effect_digest or False) != (effect_digest or False)
        or existing.version_kind != kind
        or (existing.restored_from_version_id.id or False) != (source_version_id or False)
        or (existing.intent_message_id.id or False) != (intent_message_id or False)
        or (existing.confirmation_receipt_id or False) != (confirmation_receipt_id or False)
    ):
        raise ValidationError(_("The idempotency key is already bound to a different workbook effect."))
    return existing


def _check_request_scope(env, session, request):
    request.check_access("read")
    if (
        request.owner_id.id != env.uid
        or request.thread_id != session.thread_id
        or request.input_message_id != session.source_message_id
        or request.source_attachment_id != session.source_attachment_id
        or request.state != "generated"
        or not request.output_attachment_id
    ):
        raise AccessError(_("The verified M1 request is unavailable."))
    request.output_attachment_id.check("read")
    if (
        request.output_attachment_id.res_model != request._name
        or request.output_attachment_id.res_id != request.id
        or request.output_attachment_id.public
    ):
        raise AccessError(_("The verified M1 request is unavailable."))
    return request


def register_initial_v1(env, session_id, request_id):
    """Register a new M1 output as V1 only when persisted M1 proof matches bytes."""
    session = _require_session(env, session_id, write=True)
    if isinstance(request_id, bool) or not isinstance(request_id, int) or request_id < 1:
        raise AccessError(_("The verified M1 request is unavailable."))
    request = env["office.document.request"].browse(request_id).exists()
    if not request:
        raise AccessError(_("The verified M1 request is unavailable."))
    request = _check_request_scope(env, session, request)
    if (
        request.m1_validation_status != "VERIFIED"
        or request.m1_validator_policy_version != M1_VALIDATOR_POLICY_VERSION
        or not _HASH.fullmatch(request.m1_validation_report_id or "")
        or request.m1_validation_report_sha256 != request.m1_validation_report_id
    ):
        raise ValidationError(_("The M1 output has no supported persistent validation proof."))
    if request.m1_version_session_id != session.id:
        raise AccessError(_("The verified M1 request is unavailable."))

    input_bytes, input_sha = _read_attachment(env, session.source_attachment_id)
    output_bytes, output_sha = _read_attachment(
        env, request.output_attachment_id, expected_sha=request.output_sha256
    )
    if (
        request.m1_validation_input_sha256 != input_sha
        or request.m1_validation_output_sha256 != output_sha
        or request.input_sha256 != input_sha
        or request.m1_validation_completed_at is False
    ):
        raise ValidationError(_("The M1 validation proof does not match the current request bytes."))
    if (
        type(request.m1_version_session_revision) is not int
        or request.m1_version_session_revision < 1
        or type(request.m1_version_proposal_revision) is not int
        or request.m1_version_proposal_revision < 0
        or request.m1_version_proposal_revision != session.proposal_revision
    ):
        raise ValidationError(_("The M1 validation proof is not bound to this Session revision."))

    idempotency_key = "m1:" + request.request_uuid
    request_digest = hashlib.sha256(
        json.dumps(
            {
                "request_uuid": request.request_uuid,
                "input_sha256": input_sha,
                "output_sha256": output_sha,
                "report_id": request.m1_validation_report_id,
                "policy": request.m1_validator_policy_version,
                "session_revision": request.m1_version_session_revision,
                "proposal_revision": request.m1_version_proposal_revision,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    existing = env["office.workbook.version"].search(
        [("session_id", "=", session.id), ("idempotency_key", "=", idempotency_key)], limit=1
    )
    if existing:
        _same_idempotent_result(
            existing,
            parent_id=False,
            input_sha=input_sha,
            output_sha=output_sha,
            request_digest=request_digest,
            effect_digest=False,
            kind="initial",
        )
        if (
            existing.session_revision != request.m1_version_session_revision
            or existing.proposal_revision != request.m1_version_proposal_revision
        ):
            raise ValidationError(_("The existing V1 record is bound to different Session revisions."))
        _read_attachment(env, existing.output_attachment_id, expected_sha=output_sha)
        return existing

    if session.revision != request.m1_version_session_revision:
        raise ValidationError(_("The M1 validation proof is stale for the current Session revision."))

    with env.cr.savepoint():
        locked = _lock_session(session)
        if locked.document_revision != 0 or locked.current_version_id:
            raise ValidationError(_("The Session already has a current document version."))
        if not input_bytes or not output_bytes:
            raise ValidationError(_("The initial workbook version is empty."))
        version = _create_version_row(
            env,
            {
                "session_id": session.id,
                "source_message_id": session.source_message_id.id,
                "source_request_id": request.id,
                "version_no": 1,
                "version_kind": "initial",
                "state": "verifying",
                "idempotency_key": idempotency_key,
                "request_digest": request_digest,
                "input_attachment_id": session.source_attachment_id.id,
                "input_sha256": input_sha,
                "filename": request.output_attachment_id.name or "workbook.xlsx",
                "mimetype": request.output_attachment_id.mimetype,
                "session_revision": request.m1_version_session_revision,
                "proposal_revision": request.m1_version_proposal_revision,
                "document_revision": locked.document_revision,
            },
        )
        attachment = _create_version_attachment(
            env, version, version.filename, version.mimetype, output_bytes
        )
        _check_version_attachment(version, attachment)
        copied_bytes, copied_sha = _read_attachment(env, attachment, expected_sha=output_sha)
        if copied_bytes != output_bytes:
            raise ValidationError(_("The V1 attachment copy did not preserve the verified bytes."))
        _write_version(
            version,
            {
                "output_attachment_id": attachment.id,
                "output_sha256": copied_sha,
                "file_size": len(copied_bytes),
                "validator_policy_version": request.m1_validator_policy_version,
                "validation_report_id": request.m1_validation_report_id,
                "validation_report_sha256": request.m1_validation_report_sha256,
                "validated_candidate_sha256": copied_sha,
                "validation_result": "VERIFIED",
                "validation_completed_at": request.m1_validation_completed_at,
                "state": "verified",
            },
        )
        _accept_verified_version(env, version, expected_document_revision=0, expected_current=False)
        return version


def register_candidate(
    env,
    session_id,
    *,
    parent_version_id,
    expected_document_revision,
    candidate_bytes,
    filename,
    mimetype,
    idempotency_key,
    request_digest,
    intent_message_id,
    intent_effect_digest=False,
    confirmation_receipt_id=False,
    provider_id=False,
    provider_model=False,
    provider_response_id=False,
    provider_tool_call_id=False,
    provider_file_id=False,
    provider_usage_json=False,
    provider_cleanup_state="not_applicable",
):
    """Persist real candidate bytes under current-user ACL; never accept it here."""
    session = _require_session(env, session_id, write=True)
    parent = _require_version(env, session, parent_version_id)
    if parent.state not in {"accepted_current", "finalized"}:
        raise ValidationError(_("A candidate must be based on an accepted current version."))
    expected_document_revision = _check_expected_revision(expected_document_revision)
    idempotency_key = _require_idempotency_key(idempotency_key)
    request_digest = _require_hash(request_digest, "request")
    effect_digest = _require_hash(intent_effect_digest, "effect", optional=True)
    confirmation_receipt_id = _require_confirmation_reference(confirmation_receipt_id)
    intent = _require_user_thread_message(env, session, intent_message_id, "Intent")
    filename, mimetype = _filename_and_mimetype(filename, mimetype)
    if not isinstance(candidate_bytes, bytes) or not candidate_bytes or len(candidate_bytes) > MAX_VERSION_BYTES:
        raise ValidationError(_("The candidate workbook bytes are empty or exceed the size limit."))
    output_sha = hashlib.sha256(candidate_bytes).hexdigest()
    input_bytes, input_sha = _read_attachment(env, parent.output_attachment_id, expected_sha=parent.output_sha256)
    if input_sha != parent.output_sha256:
        raise ValidationError(_("The accepted parent workbook changed."))
    existing = env["office.workbook.version"].search(
        [("session_id", "=", session.id), ("idempotency_key", "=", idempotency_key)], limit=1
    )
    if existing:
        return _same_idempotent_result(
            existing,
            parent_id=parent.id,
            input_sha=input_sha,
            output_sha=output_sha,
            request_digest=request_digest,
            effect_digest=effect_digest,
            kind="edit",
            intent_message_id=intent.id,
            confirmation_receipt_id=confirmation_receipt_id,
        )

    with env.cr.savepoint():
        locked = _lock_session(session)
        if (
            locked.current_version_id != parent
            or locked.document_revision != expected_document_revision
            or locked.document_revision != parent.accepted_document_revision
        ):
            raise ValidationError(_("WORKBOOK_VERSION_STALE: the candidate parent is no longer current."))
        existing = env["office.workbook.version"].search(
            [("session_id", "=", session.id), ("idempotency_key", "=", idempotency_key)], limit=1
        )
        if existing:
            return _same_idempotent_result(
                existing,
                parent_id=parent.id,
                input_sha=input_sha,
                output_sha=output_sha,
                request_digest=request_digest,
                effect_digest=effect_digest,
                kind="edit",
                intent_message_id=intent.id,
                confirmation_receipt_id=confirmation_receipt_id,
            )
        version = _create_version_row(
            env,
            {
                "session_id": session.id,
                "source_message_id": session.source_message_id.id,
                "intent_message_id": intent.id,
                "candidate_review_watermark_message_id": _latest_thread_message(env, session).id,
                "version_no": _next_version_number(env, session),
                "version_kind": "edit",
                "state": "candidate_received",
                "parent_version_id": parent.id,
                "idempotency_key": idempotency_key,
                "request_digest": request_digest,
                "intent_effect_digest": effect_digest,
                "confirmation_receipt_id": confirmation_receipt_id or False,
                "requires_confirmation": bool(confirmation_receipt_id),
                "input_attachment_id": parent.output_attachment_id.id,
                "input_sha256": input_sha,
                "filename": filename,
                "mimetype": mimetype,
                "session_revision": session.revision,
                "proposal_revision": session.proposal_revision,
                "document_revision": locked.document_revision,
                "provider_id": _safe_metadata(provider_id, 128),
                "provider_model": _safe_metadata(provider_model, 128),
                "provider_response_id": _safe_metadata(provider_response_id, 255),
                "provider_tool_call_id": _safe_metadata(provider_tool_call_id, 255),
                "provider_file_id": _safe_metadata(provider_file_id, 255),
                "provider_usage_json": _safe_usage(provider_usage_json),
                "provider_cleanup_state": provider_cleanup_state,
            },
        )
        attachment = _create_version_attachment(env, version, filename, mimetype, candidate_bytes)
        _check_version_attachment(version, attachment)
        stored, stored_sha = _read_attachment(env, attachment, expected_sha=output_sha)
        if stored != candidate_bytes:
            raise ValidationError(_("The candidate attachment did not preserve the received bytes."))
        _write_version(version, {"output_attachment_id": attachment.id, "output_sha256": stored_sha, "file_size": len(stored)})
        return version


def _check_expected_revision(value):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValidationError(_("Invalid document revision."))
    return value


def _safe_metadata(value, limit):
    if value in (None, False, ""):
        return False
    if not isinstance(value, str) or len(value) > limit or any(ord(char) < 32 for char in value):
        raise ValidationError(_("Provider metadata is invalid."))
    return value


def _safe_usage(value):
    if value in (None, False, ""):
        return False
    if not isinstance(value, dict):
        raise ValidationError(_("Provider usage metadata must be an object."))
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"))
    if len(encoded.encode()) > 4096:
        raise ValidationError(_("Provider usage metadata exceeds the storage limit."))
    return encoded


def _restore_effect(session, current, source, revision):
    payload = {
        "operation": "restore",
        "session_id": session.id,
        "owner_id": session.owner_id.id,
        "current_version_id": current.id,
        "source_version_id": source.id,
        "output_sha256": source.output_sha256,
        "document_revision": revision,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def request_restore_candidate(
    env,
    session_id,
    source_version_id,
    *,
    expected_current_version_id,
    expected_document_revision,
    idempotency_key,
    confirmation_receipt,
):
    """Create a new child from immutable history after a fresh typed confirmation."""
    session = _require_session(env, session_id, write=True)
    source = _require_version(env, session, source_version_id)
    current = _require_version(env, session, expected_current_version_id, write=True)
    expected_document_revision = _check_expected_revision(expected_document_revision)
    idempotency_key = _require_idempotency_key(idempotency_key)
    if source.state not in {"accepted_current", "superseded", "finalized"} or not source.output_attachment_id:
        raise ValidationError(_("Only an accepted historical version can be restored."))
    if source == current:
        raise ValidationError(_("The selected version is already current."))
    if current != session.current_version_id or current.accepted_document_revision != expected_document_revision:
        raise ValidationError(_("WORKBOOK_VERSION_STALE: the current version changed before restore."))
    source_bytes, source_sha = _read_attachment(env, source.output_attachment_id, expected_sha=source.output_sha256)
    current_bytes, current_sha = _read_attachment(env, current.output_attachment_id, expected_sha=current.output_sha256)
    if not current_bytes:
        raise ValidationError(_("The current workbook is unavailable."))
    effect_digest = _restore_effect(session, current, source, expected_document_revision)
    if not isinstance(confirmation_receipt, ConfirmationReceipt):
        raise AccessError(_("A fresh, scoped restore confirmation is required."))
    if (
        confirmation_receipt.operation != "restore"
        or confirmation_receipt.session_id != session.id
        or confirmation_receipt.owner_id != env.uid
        or confirmation_receipt.current_version_id != current.id
        or confirmation_receipt.source_version_id != source.id
        or confirmation_receipt.document_revision != expected_document_revision
        or confirmation_receipt.output_sha256 != source_sha
        or confirmation_receipt.effect_digest != effect_digest
        or isinstance(confirmation_receipt.intent_message_id, bool)
        or not isinstance(confirmation_receipt.intent_message_id, int)
        or isinstance(confirmation_receipt.decision_message_id, bool)
        or not isinstance(confirmation_receipt.decision_message_id, int)
        or not isinstance(confirmation_receipt.receipt_id, str)
        or not confirmation_receipt.receipt_id
        or len(confirmation_receipt.receipt_id) > 128
        or any(ord(char) < 32 for char in confirmation_receipt.receipt_id)
    ):
        raise ValidationError(_("The restore confirmation does not match the current file effect."))
    intent = _require_user_thread_message(env, session, confirmation_receipt.intent_message_id, "restore Intent")
    decision = _require_user_thread_message(env, session, confirmation_receipt.decision_message_id, "restore confirmation")
    if decision.id <= intent.id:
        raise ValidationError(_("The restore confirmation does not follow its Intent."))
    request_digest = hashlib.sha256(
        json.dumps(
            {
                "effect_digest": effect_digest,
                "input_sha256": current_sha,
                "source_sha256": source_sha,
                "intent_message_id": intent.id,
                "decision_message_id": decision.id,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    existing = env["office.workbook.version"].search(
        [("session_id", "=", session.id), ("idempotency_key", "=", idempotency_key)], limit=1
    )
    if existing:
        return _same_idempotent_result(
            existing,
            parent_id=current.id,
            input_sha=current_sha,
            output_sha=source_sha,
            request_digest=request_digest,
            effect_digest=effect_digest,
            kind="restore",
            source_version_id=source.id,
            intent_message_id=intent.id,
            confirmation_receipt_id=confirmation_receipt.receipt_id,
        )
    with env.cr.savepoint():
        locked = _lock_session(session)
        if locked.current_version_id != current or locked.document_revision != expected_document_revision:
            raise ValidationError(_("WORKBOOK_VERSION_STALE: the current file changed before restore."))
        existing = env["office.workbook.version"].search(
            [("session_id", "=", session.id), ("idempotency_key", "=", idempotency_key)], limit=1
        )
        if existing:
            return _same_idempotent_result(
                existing,
                parent_id=current.id,
                input_sha=current_sha,
                output_sha=source_sha,
                request_digest=request_digest,
                effect_digest=effect_digest,
                kind="restore",
                source_version_id=source.id,
                intent_message_id=intent.id,
                confirmation_receipt_id=confirmation_receipt.receipt_id,
            )
        filename, mimetype = _filename_and_mimetype(source.filename, source.mimetype)
        version = _create_version_row(
            env,
            {
                "session_id": session.id,
                "source_message_id": session.source_message_id.id,
                "intent_message_id": intent.id,
                "candidate_review_watermark_message_id": _latest_thread_message(env, session).id,
                "version_no": _next_version_number(env, session),
                "version_kind": "restore",
                "state": "candidate_received",
                "parent_version_id": current.id,
                "restored_from_version_id": source.id,
                "idempotency_key": idempotency_key,
                "request_digest": request_digest,
                "intent_effect_digest": effect_digest,
                "confirmation_receipt_id": confirmation_receipt.receipt_id,
                "requires_confirmation": True,
                "input_attachment_id": current.output_attachment_id.id,
                "input_sha256": current_sha,
                "filename": filename,
                "mimetype": mimetype,
                "session_revision": session.revision,
                "proposal_revision": session.proposal_revision,
                "document_revision": locked.document_revision,
            },
        )
        attachment = _create_version_attachment(env, version, filename, mimetype, source_bytes)
        _check_version_attachment(version, attachment)
        stored_bytes, stored_sha = _read_attachment(env, attachment, expected_sha=source_sha)
        if stored_bytes != source_bytes:
            raise ValidationError(_("The restored candidate did not preserve the selected version bytes."))
        _write_version(version, {"output_attachment_id": attachment.id, "output_sha256": stored_sha, "file_size": len(stored_bytes)})
        return version


def record_finalize_reference(env, version_id, final_attachment_id, final_message_id):
    """Bind a delivered Thread attachment to the accepted version with identical bytes."""
    if type(version_id) is not int or version_id < 1:
        raise AccessError(_("The workbook version is unavailable."))
    if type(final_attachment_id) is not int or final_attachment_id < 1:
        raise AccessError(_("The finalized workbook is unavailable."))
    if type(final_message_id) is not int or final_message_id < 1:
        raise AccessError(_("The finalized workbook message is unavailable."))
    version = env["office.workbook.version"].browse(version_id).exists()
    if not version:
        raise AccessError(_("The workbook version is unavailable."))
    version.check_access("write")
    session = _require_session(env, version.session_id.id, write=True)
    if version.state not in {"accepted_current", "finalized"} or session.current_version_id != version:
        raise ValidationError(_("Only the accepted current workbook can be finalized."))
    attachment = env["ir.attachment"].browse(final_attachment_id).exists()
    message = env["mail.message"].browse(final_message_id).exists()
    if not attachment or not message:
        raise AccessError(_("The finalized workbook delivery is unavailable."))
    attachment.check("read")
    message.check_access("read")
    if (
        message.model != session.thread_id._name
        or message.res_id != session.thread_id.id
        or message.llm_role != "assistant"
        or attachment not in message.attachment_ids
        or attachment.company_id not in (False, session.company_id)
        or attachment.mimetype != version.mimetype
    ):
        raise AccessError(_("The finalized workbook delivery is unavailable."))
    _filename_and_mimetype(attachment.name, attachment.mimetype)
    content, actual_sha = _read_attachment(env, attachment, expected_sha=version.output_sha256)
    if not content or actual_sha != version.output_sha256:
        raise ValidationError(_("The finalized attachment does not match the accepted workbook bytes."))
    if version.delivery_state == "delivered":
        if version.final_attachment_id != attachment or version.final_message_id != message:
            raise ValidationError(_("The accepted workbook already has a different final delivery reference."))
        return version

    with env.cr.savepoint():
        locked = _lock_session(session)
        if locked.current_version_id != version or locked.document_revision != version.accepted_document_revision:
            raise ValidationError(_("WORKBOOK_VERSION_STALE: the accepted workbook changed before finalization."))
        content, actual_sha = _read_attachment(env, attachment, expected_sha=version.output_sha256)
        if not content or actual_sha != version.output_sha256:
            raise ValidationError(_("The finalized attachment changed before its delivery reference was recorded."))
        _write_version(
            version,
            {
                "state": "finalized",
                "delivery_state": "delivered",
                "final_attachment_id": attachment.id,
                "final_message_id": message.id,
                "finalized_at": fields.Datetime.now(),
            },
        )
    return version


def _receipt_fields(candidate, receipt):
    if not isinstance(receipt, ValidationReceipt):
        raise ValidationError(_("A trusted in-process validation receipt is required."))
    if receipt.validation_result not in {"VERIFIED", "PARTIALLY_VERIFIED", "FAILED", "REJECTED"}:
        raise ValidationError(_("The validation receipt result is invalid."))
    for value, label, minimum in (
        (receipt.candidate_version_id, "candidate version", 1),
        (receipt.session_id, "session", 1),
        (receipt.session_revision, "session revision", 1),
        (receipt.proposal_revision, "proposal revision", 0),
        (receipt.document_revision, "document revision", 0),
    ):
        if type(value) is not int or value < minimum:
            raise ValidationError(_("The validation receipt contains an invalid %(label)s.", label=label))
    if receipt.parent_version_id not in (False, None) and (
        type(receipt.parent_version_id) is not int or receipt.parent_version_id < 1
    ):
        raise ValidationError(_("The validation receipt parent version is invalid."))
    _require_hash(receipt.candidate_output_sha256, "candidate output")
    _require_hash(receipt.validation_report_id, "validation report")
    _require_hash(receipt.validation_report_sha256, "validation report")
    _require_hash(receipt.input_sha256, "validation input")
    _require_hash(receipt.effect_digest, "effect", optional=True)
    if not isinstance(receipt.validator_policy_version, str) or not _POLICY.fullmatch(receipt.validator_policy_version):
        raise ValidationError(_("The validator policy version is invalid."))
    if (
        receipt.candidate_version_id != candidate.id
        or receipt.candidate_output_sha256 != candidate.output_sha256
        or receipt.validation_report_sha256 != receipt.validation_report_id
        or receipt.session_id != candidate.session_id.id
        or receipt.session_revision != candidate.session_revision
        or receipt.proposal_revision != candidate.proposal_revision
        or receipt.document_revision != candidate.document_revision
        or (receipt.parent_version_id or False) != (candidate.parent_version_id.id or False)
        or receipt.input_sha256 != candidate.input_sha256
        or (receipt.effect_digest or False) != (candidate.intent_effect_digest or False)
    ):
        raise ValidationError(_("The validation receipt is not bound to this candidate and revision."))
    _check_version_attachment(candidate, candidate.output_attachment_id)
    content, actual_sha = _read_attachment(
        candidate.env, candidate.output_attachment_id, expected_sha=candidate.output_sha256
    )
    if not content or actual_sha != receipt.candidate_output_sha256:
        raise ValidationError(_("The validation receipt candidate bytes do not match."))
    input_content, actual_input_sha = _read_attachment(
        candidate.env, candidate.input_attachment_id, expected_sha=candidate.input_sha256
    )
    if not input_content or actual_input_sha != receipt.input_sha256:
        raise ValidationError(_("The validation receipt input bytes do not match."))
    if candidate.version_kind != "initial":
        parent = _require_version(candidate.env, candidate.session_id, candidate.parent_version_id.id)
        _check_version_attachment(parent, candidate.input_attachment_id)
    session = candidate.session_id
    session.check_access("write")
    if (
        session.revision != candidate.session_revision
        or session.proposal_revision != candidate.proposal_revision
        or session.document_revision != candidate.document_revision
        or (session.current_version_id.id or False) != (candidate.parent_version_id.id or False)
    ):
        raise ValidationError(_("The candidate revisions or parent are stale."))
    if candidate.version_kind == "restore" and not candidate.confirmation_receipt_id:
        raise ValidationError(_("A restored candidate requires a fresh scoped confirmation."))
    return {
        "validator_policy_version": receipt.validator_policy_version,
        "validation_report_id": receipt.validation_report_id,
        "validation_report_sha256": receipt.validation_report_sha256,
        "validated_candidate_sha256": actual_sha,
        "validation_result": receipt.validation_result,
        "validation_completed_at": fields.Datetime.now(),
        "state": {
            "VERIFIED": "verified",
            "PARTIALLY_VERIFIED": "partially_verified",
            "FAILED": "failed",
            "REJECTED": "rejected",
        }[receipt.validation_result],
    }


def record_validation_receipt(env, candidate_id, receipt):
    if isinstance(candidate_id, bool) or not isinstance(candidate_id, int) or candidate_id < 1:
        raise AccessError(_("The workbook candidate is unavailable."))
    candidate = env["office.workbook.version"].browse(candidate_id).exists()
    if not candidate:
        raise AccessError(_("The workbook candidate is unavailable."))
    candidate.check_access("write")
    session = _require_session(env, candidate.session_id.id, write=True)
    if candidate.state != "candidate_received":
        raise ValidationError(_("Only a received candidate can accept a validation result."))
    values = _receipt_fields(candidate, receipt)
    _write_version(candidate, values)
    return candidate


def _revalidate_stored_receipt(env, candidate):
    session = _require_session(env, candidate.session_id.id, write=True)
    valid_state_result = (
        candidate.validation_result == "VERIFIED" and candidate.state == "verified"
    ) or (
        candidate.validation_result == "PARTIALLY_VERIFIED"
        and candidate.state == "partially_verified"
        and candidate.version_kind == "edit"
    )
    if not valid_state_result:
        raise ValidationError(_("The Candidate does not have a reviewable validation result for this operation."))
    if (
        not candidate.validator_policy_version
        or not _POLICY.fullmatch(candidate.validator_policy_version)
        or not _HASH.fullmatch(candidate.validation_report_id or "")
        or candidate.validation_report_sha256 != candidate.validation_report_id
        or candidate.validated_candidate_sha256 != candidate.output_sha256
    ):
        raise ValidationError(_("The candidate has no valid persisted validation proof."))
    _check_version_attachment(candidate, candidate.output_attachment_id)
    output, output_sha = _read_attachment(
        env, candidate.output_attachment_id, expected_sha=candidate.output_sha256
    )
    input_bytes, input_sha = _read_attachment(
        env, candidate.input_attachment_id, expected_sha=candidate.input_sha256
    )
    if not output or not input_bytes or output_sha != candidate.validated_candidate_sha256 or input_sha != candidate.input_sha256:
        raise ValidationError(_("Candidate attachment bytes changed after validation."))
    if candidate.version_kind != "initial":
        parent = _require_version(env, session, candidate.parent_version_id.id)
        _check_version_attachment(parent, candidate.input_attachment_id)
    if (
        session.revision != candidate.session_revision
        or session.proposal_revision != candidate.proposal_revision
        or session.document_revision != candidate.document_revision
        or session.current_version_id != candidate.parent_version_id
    ):
        raise ValidationError(_("WORKBOOK_VERSION_STALE: the candidate no longer matches current state."))
    if candidate.version_kind == "restore" and not candidate.confirmation_receipt_id:
        raise ValidationError(_("The restore candidate has no fresh confirmation receipt."))
    if candidate.version_kind == "edit":
        if not candidate.intent_message_id:
            raise ValidationError(_("The edit candidate has no bound user Intent message."))
        _require_user_thread_message(env, session, candidate.intent_message_id.id, "Intent")
    return session


def _accept_verified_version(
    env, version, *, expected_document_revision, expected_current, acceptance_authorization=None
):
    session = _revalidate_stored_receipt(env, version)
    verified = version.state == "verified" and version.validation_result == "VERIFIED"
    partial_edit = (
        version.state == "partially_verified"
        and version.validation_result == "PARTIALLY_VERIFIED"
        and version.version_kind == "edit"
        and acceptance_authorization is not None
    )
    if not (verified or partial_edit):
        raise ValidationError(_("Only a verified Candidate or a user-authorized partially verified edit can become Current."))
    with env.cr.savepoint():
        locked = _lock_session(session)
        if (
            locked.document_revision != expected_document_revision
            or (locked.current_version_id.id or False) != (expected_current or False)
        ):
            raise ValidationError(_("WORKBOOK_VERSION_STALE: the current document version changed."))
        # Re-read proof, input/output bytes, and revisions under the Session lock.
        session = _revalidate_stored_receipt(env, version)
        authorization_digest = False
        if version.version_kind == "edit":
            authorization_digest = _validate_candidate_acceptance_authorization(
                env, version, acceptance_authorization
            )
        previous = locked.current_version_id
        if previous:
            _write_version(previous, {"state": "superseded"})
        next_revision = expected_document_revision + 1
        acceptance_values = {
            "state": "accepted_current",
            "accepted_document_revision": next_revision,
        }
        if authorization_digest:
            acceptance_values.update({
                "acceptance_authorization_kind": acceptance_authorization.authorization_kind,
                "acceptance_authorization_message_id": acceptance_authorization.decision_message_id,
                "acceptance_authorization_digest": authorization_digest,
            })
        _write_version(version, acceptance_values)
        locked._advance_document_version_from_service(
            version,
            expected_document_revision=expected_document_revision,
            expected_current_version_id=expected_current,
        )
    return version


def accept_verified_candidate(env, candidate_id, authorization=None):
    """Atomically accept a VERIFIED Candidate or a user-authorized PARTIAL edit.

    Acceptance preserves the receipt's validation grade. PARTIALLY_VERIFIED is
    never upgraded to VERIFIED and requires the same scoped human decision
    binding as any edit Candidate.
    """
    if isinstance(candidate_id, bool) or not isinstance(candidate_id, int) or candidate_id < 1:
        raise AccessError(_("The workbook candidate is unavailable."))
    candidate = env["office.workbook.version"].browse(candidate_id).exists()
    if not candidate:
        raise AccessError(_("The workbook candidate is unavailable."))
    candidate.check_access("write")
    _require_session(env, candidate.session_id.id, write=True)
    if candidate.version_kind == "edit":
        authorization_digest = _validate_candidate_acceptance_authorization(env, candidate, authorization)
        if candidate.state in {"accepted_current", "superseded", "finalized"}:
            _check_version_attachment(candidate, candidate.output_attachment_id)
            _read_attachment(env, candidate.output_attachment_id, expected_sha=candidate.output_sha256)
            if candidate.acceptance_authorization_digest == authorization_digest:
                return candidate
            raise ValidationError(_("The candidate was already accepted under a different authorization."))
    elif authorization is not None:
        raise ValidationError(_("This Candidate kind cannot use edit acceptance authorization."))
    return _accept_verified_version(
        env,
        candidate,
        expected_document_revision=candidate.document_revision,
        expected_current=candidate.parent_version_id.id or False,
        acceptance_authorization=authorization,
    )


def reject_verified_candidate(env, candidate_id, decision):
    if isinstance(candidate_id, bool) or not isinstance(candidate_id, int) or candidate_id < 1:
        raise AccessError(_("The workbook candidate is unavailable."))
    candidate = env["office.workbook.version"].browse(candidate_id).exists()
    if not candidate:
        raise AccessError(_("The workbook candidate is unavailable."))
    candidate.check_access("write")
    session = _require_session(env, candidate.session_id.id, write=True)
    if not isinstance(decision, CandidateRejection):
        raise AccessError(_("A trusted, scoped Candidate rejection is required."))
    if (
        any(type(value) is not int or value < 1 for value in (
            decision.candidate_version_id,
            decision.session_id,
            decision.owner_id,
            decision.intent_message_id,
            decision.decision_message_id,
            decision.parent_version_id,
        ))
        or type(decision.document_revision) is not int
        or decision.document_revision < 0
        or candidate.version_kind == "initial"
        or decision.candidate_version_id != candidate.id
        or decision.session_id != session.id
        or decision.owner_id != env.uid
        or decision.intent_message_id != candidate.intent_message_id.id
        or decision.parent_version_id != candidate.parent_version_id.id
        or decision.document_revision != candidate.document_revision
        or decision.output_sha256 != candidate.output_sha256
        or (decision.effect_digest or False) != (candidate.intent_effect_digest or False)
    ):
        raise ValidationError(_("The rejection decision does not match this Candidate."))
    _require_user_thread_message(env, session, decision.intent_message_id, "Intent")
    decision_message = _require_user_thread_message(env, session, decision.decision_message_id, "rejection")
    watermark = candidate.candidate_review_watermark_message_id
    if not watermark or decision_message.id <= max(decision.intent_message_id, watermark.id):
        raise ValidationError(_("The rejection decision must follow its Intent."))
    digest = _rejection_digest(decision)
    if candidate.state == "rejected":
        if candidate.rejection_digest == digest:
            return candidate
        raise ValidationError(_("The Candidate was already rejected under a different decision."))
    reviewable_state = (
        candidate.state == "verified" and candidate.validation_result == "VERIFIED"
    ) or (
        candidate.state == "partially_verified"
        and candidate.validation_result == "PARTIALLY_VERIFIED"
        and candidate.version_kind == "edit"
    )
    if not reviewable_state:
        raise ValidationError(_("Only a technically reviewable, non-current Candidate can be rejected."))
    if session.current_version_id == candidate:
        raise ValidationError(_("A current Candidate cannot be rejected."))
    with env.cr.savepoint():
        locked = _lock_session(session)
        candidate.invalidate_recordset()
        if candidate.state not in {"verified", "partially_verified"} or locked.current_version_id == candidate:
            raise ValidationError(_("The Candidate is no longer available for rejection."))
        _revalidate_stored_receipt(env, candidate)
        _write_version(candidate, {
            "state": "rejected",
            "rejection_message_id": decision_message.id,
            "rejection_digest": digest,
            "rejected_at": fields.Datetime.now(),
        })
    return candidate
