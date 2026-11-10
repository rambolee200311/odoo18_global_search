"""Trusted test-only receipt issuer. Never imported by production modules."""

import hashlib
import json

from odoo.addons.office_engine_m2.services.workbook_version_service import (
    ConfirmationReceipt,
    ValidationReceipt,
    _restore_effect,
)


def verified_receipt(candidate):
    payload = {
        "candidate_id": candidate.id,
        "output_sha256": candidate.output_sha256,
        "session_id": candidate.session_id.id,
        "session_revision": candidate.session_revision,
        "proposal_revision": candidate.proposal_revision,
        "document_revision": candidate.document_revision,
        "parent_version_id": candidate.parent_version_id.id or False,
        "input_sha256": candidate.input_sha256,
        "effect_digest": candidate.intent_effect_digest or False,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    return ValidationReceipt(
        candidate_version_id=candidate.id,
        candidate_output_sha256=candidate.output_sha256,
        validator_policy_version="test-validator.v1",
        validation_report_id=digest,
        validation_report_sha256=digest,
        validation_result="VERIFIED",
        session_id=candidate.session_id.id,
        session_revision=candidate.session_revision,
        proposal_revision=candidate.proposal_revision,
        document_revision=candidate.document_revision,
        parent_version_id=candidate.parent_version_id.id or False,
        input_sha256=candidate.input_sha256,
        effect_digest=candidate.intent_effect_digest or False,
    )


def restore_confirmation(session, source_version, *, current=None):
    current = current or session.current_version_id
    effect = _restore_effect(session, current, source_version, session.document_revision)
    intent = session.thread_id.message_post(
        body="Synthetic request to restore workbook version " + str(source_version.version_no),
        llm_role="user",
        author_id=session.env.user.partner_id.id,
    )
    decision = session.thread_id.message_post(
        body="Confirm restore of workbook version " + str(source_version.version_no),
        llm_role="user",
        author_id=session.env.user.partner_id.id,
    )
    return ConfirmationReceipt(
        receipt_id=hashlib.sha256((effect + "test-confirmed" + str(intent.id) + str(decision.id)).encode()).hexdigest(),
        session_id=session.id,
        owner_id=session.owner_id.id,
        current_version_id=current.id,
        source_version_id=source_version.id,
        document_revision=session.document_revision,
        output_sha256=source_version.output_sha256,
        effect_digest=effect,
        operation="restore",
        intent_message_id=intent.id,
        decision_message_id=decision.id,
    )
