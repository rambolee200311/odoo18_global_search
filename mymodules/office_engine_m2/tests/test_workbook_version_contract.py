"""Neutral version contract and M1 V1 registration tests."""

import hashlib
from dataclasses import replace

from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase

from .support import WorkbookVersionFixtures, synthetic_xlsx
from .support.validator_stub import verified_receipt
from ..services.workbook_version_service import (
    CandidateAcceptanceAuthorization,
    CandidateRejection,
    accept_verified_candidate,
    record_validation_receipt,
    reject_verified_candidate,
)


class TestWorkbookVersionContract(WorkbookVersionFixtures, TransactionCase):
    def test_m1_output_registers_private_v1_from_persisted_readback_proof(self):
        env, session, _thread, _message, _source, request, output, version = self._versioned_session_fixture()

        self.assertEqual(version.version_no, 1)
        self.assertEqual(version.version_kind, "initial")
        self.assertEqual(version.state, "accepted_current")
        self.assertEqual(session.current_version_id, version)
        self.assertEqual(session.last_valid_version_id, version)
        self.assertEqual(session.document_revision, 1)
        self.assertEqual(version.output_sha256, hashlib.sha256(output.raw).hexdigest())
        self.assertEqual(version.output_attachment_id.public, False)
        self.assertEqual(version.output_attachment_id.res_model, version._name)
        self.assertEqual(version.validation_result, "VERIFIED")
        self.assertEqual(version.validation_report_id, request.m1_validation_report_id)

    def test_unproved_historical_request_stays_legacy(self):
        env, session, _thread, _message, _source = self._session_fixture()
        request, _output = self._m1_request_fixture(env, session, include_proof=False)
        with self.assertRaises(ValidationError):
            from ..services.workbook_version_service import register_initial_v1
            register_initial_v1(env, session.id, request.id)
        self.assertFalse(session.current_version_id)
        self.assertEqual(session.document_revision, 0)

    def test_v1_v2_v3_parent_chain_and_idempotency(self):
        env, session, _thread, _message, _source, _request, _output, v1 = self._versioned_session_fixture()
        v2_bytes = synthetic_xlsx("candidate-v2")
        v2 = self._register_candidate(
            env,
            session,
            parent_version_id=v1.id,
            expected_document_revision=session.document_revision,
            candidate_bytes=v2_bytes,
            filename="candidate-v2.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            idempotency_key="candidate-v2-1",
            request_digest=hashlib.sha256(b"request-v2").hexdigest(),
            intent_effect_digest=hashlib.sha256(b"effect-v2").hexdigest(),
        )
        self.assertEqual(v2.state, "candidate_received")
        same_v2 = self._register_candidate(
            env,
            session,
            parent_version_id=v1.id,
            expected_document_revision=session.document_revision,
            candidate_bytes=v2_bytes,
            filename="candidate-v2.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            idempotency_key="candidate-v2-1",
            request_digest=hashlib.sha256(b"request-v2").hexdigest(),
            intent_effect_digest=hashlib.sha256(b"effect-v2").hexdigest(),
            intent_message_id=v2.intent_message_id.id,
        )
        self.assertEqual(same_v2, v2)
        record_validation_receipt(env, v2.id, verified_receipt(v2))
        self._accept_candidate(env, v2)
        session.invalidate_recordset()
        self.assertEqual(session.current_version_id, v2)
        self.assertEqual(session.document_revision, 2)

        v3 = self._register_candidate(
            env,
            session,
            parent_version_id=v2.id,
            expected_document_revision=session.document_revision,
            candidate_bytes=synthetic_xlsx("candidate-v3"),
            filename="candidate-v3.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            idempotency_key="candidate-v3-1",
            request_digest=hashlib.sha256(b"request-v3").hexdigest(),
            intent_effect_digest=hashlib.sha256(b"effect-v3").hexdigest(),
        )
        record_validation_receipt(env, v3.id, verified_receipt(v3))
        self._accept_candidate(env, v3)
        session.invalidate_recordset()
        self.assertEqual((v3.version_no, v3.parent_version_id), (3, v2))
        self.assertEqual(session.current_version_id, v3)
        self.assertEqual(session.last_valid_version_id, v3)
        with self.assertRaises(ValidationError):
            self._register_candidate(
                env,
                session,
                parent_version_id=v1.id,
                expected_document_revision=1,
                candidate_bytes=synthetic_xlsx("different-output"),
                filename="candidate-v2.xlsx",
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                idempotency_key="candidate-v2-1",
                request_digest=hashlib.sha256(b"different-request").hexdigest(),
                intent_effect_digest=hashlib.sha256(b"effect-v2").hexdigest(),
                intent_message_id=v2.intent_message_id.id,
            )

    def test_invalid_and_cross_candidate_receipts_do_not_advance(self):
        env, session, _thread, _message, _source, _request, _output, v1 = self._versioned_session_fixture()
        a = self._register_candidate(
            env, session, parent_version_id=v1.id,
            expected_document_revision=session.document_revision,
            candidate_bytes=synthetic_xlsx("candidate-a"), filename="a.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            idempotency_key="candidate-a", request_digest=hashlib.sha256(b"a").hexdigest(),
            intent_effect_digest=hashlib.sha256(b"effect-a").hexdigest(),
        )
        b = self._register_candidate(
            env, session, parent_version_id=v1.id,
            expected_document_revision=session.document_revision,
            candidate_bytes=synthetic_xlsx("candidate-b"), filename="b.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            idempotency_key="candidate-b", request_digest=hashlib.sha256(b"b").hexdigest(),
            intent_effect_digest=hashlib.sha256(b"effect-b").hexdigest(),
        )
        with self.assertRaises(ValidationError):
            record_validation_receipt(env, b.id, verified_receipt(a))
        bad = verified_receipt(b)
        object.__setattr__(bad, "candidate_output_sha256", "0" * 64)
        with self.assertRaises(ValidationError):
            record_validation_receipt(env, b.id, bad)
        self.assertEqual(session.current_version_id, v1)
        self.assertEqual(session.document_revision, 1)

    def test_candidate_intent_and_conditional_acceptance_are_bound_and_idempotent(self):
        env, session, _thread, source_message, _source, _request, _output, v1 = self._versioned_session_fixture()
        candidate = self._register_candidate(
            env, session,
            parent_version_id=v1.id,
            expected_document_revision=session.document_revision,
            candidate_bytes=synthetic_xlsx("intent-bound-candidate"),
            filename="intent-bound.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            idempotency_key="intent-bound",
            request_digest=hashlib.sha256(b"intent-bound-request").hexdigest(),
            intent_effect_digest=hashlib.sha256(b"intent-bound-effect").hexdigest(),
        )
        self.assertEqual(candidate.source_message_id, source_message)
        self.assertNotEqual(candidate.intent_message_id, source_message)
        record_validation_receipt(env, candidate.id, verified_receipt(candidate))
        with self.assertRaises(AccessError):
            accept_verified_candidate(env, candidate.id)
        invalid = CandidateAcceptanceAuthorization(
            authorization_kind="explicit_intent",
            candidate_version_id=candidate.id,
            session_id=session.id,
            owner_id=env.uid,
            thread_id=session.thread_id.id,
            intent_message_id=candidate.intent_message_id.id,
            decision_message_id=candidate.intent_message_id.id,
            parent_version_id=v1.id,
            document_revision=candidate.document_revision,
            output_sha256="0" * 64,
            effect_digest=candidate.intent_effect_digest,
        )
        with self.assertRaises(ValidationError):
            accept_verified_candidate(env, candidate.id, invalid)
        self.assertEqual(session.current_version_id, v1)
        self.assertEqual(session.document_revision, 1)

        valid = CandidateAcceptanceAuthorization(
            authorization_kind="explicit_intent",
            candidate_version_id=candidate.id,
            session_id=session.id,
            owner_id=env.uid,
            thread_id=session.thread_id.id,
            intent_message_id=candidate.intent_message_id.id,
            decision_message_id=candidate.intent_message_id.id,
            parent_version_id=v1.id,
            document_revision=candidate.document_revision,
            output_sha256=candidate.output_sha256,
            effect_digest=candidate.intent_effect_digest,
        )
        self.assertEqual(accept_verified_candidate(env, candidate.id, valid), candidate)
        self.assertEqual(candidate.state, "accepted_current")
        self.assertEqual(candidate.acceptance_authorization_kind, "explicit_intent")
        revision = session.document_revision
        self.assertEqual(accept_verified_candidate(env, candidate.id, valid), candidate)
        session.invalidate_recordset()
        self.assertEqual(session.current_version_id, candidate)
        self.assertEqual(session.document_revision, revision)
        with self.assertRaises(AccessError):
            candidate.write({"intent_message_id": source_message.id})

    def test_confirmed_acceptance_is_bound_to_the_candidate_effect_and_receipt(self):
        env, session, _thread, _source_message, _source, _request, _output, v1 = self._versioned_session_fixture()
        intent = session.thread_id.message_post(
            body="Edit the synthetic workbook in the explicitly confirmed scope.",
            llm_role="user",
            author_id=env.user.partner_id.id,
        )
        decision = session.thread_id.message_post(
            body="Confirm the described synthetic effect before editing.",
            llm_role="user",
            author_id=env.user.partner_id.id,
        )
        candidate = self._register_candidate(
            env,
            session,
            parent_version_id=v1.id,
            expected_document_revision=session.document_revision,
            candidate_bytes=synthetic_xlsx("confirmed-effect-candidate"),
            filename="confirmed-effect.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            idempotency_key="confirmed-effect",
            request_digest=hashlib.sha256(b"confirmed-effect-request").hexdigest(),
            intent_effect_digest=hashlib.sha256(b"confirmed-effect-digest").hexdigest(),
            confirmation_receipt_id="synthetic-confirmation-receipt-v1",
            intent_message_id=intent.id,
        )
        record_validation_receipt(env, candidate.id, verified_receipt(candidate))
        authorization = CandidateAcceptanceAuthorization(
            authorization_kind="confirmed_intent",
            candidate_version_id=candidate.id,
            session_id=session.id,
            owner_id=env.uid,
            thread_id=candidate.thread_id.id,
            intent_message_id=candidate.intent_message_id.id,
            decision_message_id=decision.id,
            parent_version_id=v1.id,
            document_revision=candidate.document_revision,
            output_sha256=candidate.output_sha256,
            effect_digest=candidate.intent_effect_digest,
            confirmation_receipt_id="synthetic-confirmation-receipt-v1",
        )
        foreign_env, _foreign_session, foreign_thread, _foreign_message, _foreign_source = self._session_fixture()
        foreign_decision = foreign_thread.message_post(
            body="A decision from a different Thread.",
            llm_role="user",
            author_id=env.user.partner_id.id,
        )
        invalid_authorizations = (
            replace(authorization, effect_digest=hashlib.sha256(b"different-effect").hexdigest()),
            replace(authorization, confirmation_receipt_id="stale-receipt"),
            replace(authorization, parent_version_id=candidate.id),
            replace(authorization, document_revision=authorization.document_revision + 1),
            replace(authorization, output_sha256="0" * 64),
            replace(authorization, decision_message_id=foreign_decision.id),
        )
        for invalid in invalid_authorizations:
            with self.subTest(invalid=invalid):
                try:
                    accept_verified_candidate(env, candidate.id, invalid)
                except (AccessError, ValidationError):
                    pass
                else:
                    self.fail("Mismatched Candidate acceptance authorization was accepted.")
        self.assertEqual(session.current_version_id, v1)
        self.assertEqual(session.document_revision, 1)

        self.assertEqual(accept_verified_candidate(env, candidate.id, authorization), candidate)
        session.invalidate_recordset()
        self.assertEqual(session.current_version_id, candidate)
        self.assertEqual(session.document_revision, 2)

    def test_candidate_review_and_rejection_require_a_post_candidate_thread_message(self):
        from ..services.workbook_version_service import reject_verified_candidate

        env, session, thread, _message, _source, _request, _output, v1 = self._versioned_session_fixture()
        intent = thread.message_post(
            body="Synthetic Intent before Candidate creation.",
            llm_role="user",
            author_id=env.user.partner_id.id,
        )
        stale_decision = thread.message_post(
            body="Synthetic stale review decision before Candidate creation.",
            llm_role="user",
            author_id=env.user.partner_id.id,
        )
        candidate = self._register_candidate(
            env,
            session,
            parent_version_id=v1.id,
            expected_document_revision=session.document_revision,
            candidate_bytes=synthetic_xlsx("post-candidate-review-boundary"),
            filename="review-boundary.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            idempotency_key="review-boundary",
            request_digest=hashlib.sha256(b"review-boundary-request").hexdigest(),
            intent_effect_digest=hashlib.sha256(b"review-boundary-effect").hexdigest(),
            intent_message_id=intent.id,
        )
        self.assertEqual(candidate.candidate_review_watermark_message_id, stale_decision)
        record_validation_receipt(env, candidate.id, verified_receipt(candidate))
        authorization = CandidateAcceptanceAuthorization(
            authorization_kind="candidate_review",
            candidate_version_id=candidate.id,
            session_id=session.id,
            owner_id=env.uid,
            thread_id=thread.id,
            intent_message_id=intent.id,
            decision_message_id=stale_decision.id,
            parent_version_id=v1.id,
            document_revision=candidate.document_revision,
            output_sha256=candidate.output_sha256,
            effect_digest=candidate.intent_effect_digest,
        )
        with self.assertRaises(ValidationError):
            accept_verified_candidate(env, candidate.id, authorization)
        rejection = CandidateRejection(
            candidate_version_id=candidate.id,
            session_id=session.id,
            owner_id=env.uid,
            intent_message_id=intent.id,
            decision_message_id=stale_decision.id,
            parent_version_id=v1.id,
            document_revision=candidate.document_revision,
            output_sha256=candidate.output_sha256,
            effect_digest=candidate.intent_effect_digest,
        )
        with self.assertRaises(ValidationError):
            reject_verified_candidate(env, candidate.id, rejection)
        self.assertEqual(candidate.state, "verified")
        self.assertEqual(session.current_version_id, v1)
        self.assertEqual(session.document_revision, 1)

    def test_candidate_idempotency_does_not_reuse_a_different_confirmation(self):
        env, session, _thread, _message, _source, _request, _output, v1 = self._versioned_session_fixture()
        payload = synthetic_xlsx("confirmation-idempotency")
        candidate = self._register_candidate(
            env,
            session,
            parent_version_id=v1.id,
            expected_document_revision=session.document_revision,
            candidate_bytes=payload,
            filename="confirmation-idempotency.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            idempotency_key="confirmation-idempotency",
            request_digest=hashlib.sha256(b"confirmation-idempotency-request").hexdigest(),
            intent_effect_digest=hashlib.sha256(b"confirmation-idempotency-effect").hexdigest(),
            confirmation_receipt_id="confirmation-v1",
        )
        with self.assertRaises(ValidationError):
            self._register_candidate(
                env,
                session,
                parent_version_id=v1.id,
                expected_document_revision=session.document_revision,
                candidate_bytes=payload,
                filename="confirmation-idempotency.xlsx",
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                idempotency_key="confirmation-idempotency",
                request_digest=hashlib.sha256(b"confirmation-idempotency-request").hexdigest(),
                intent_effect_digest=hashlib.sha256(b"confirmation-idempotency-effect").hexdigest(),
                confirmation_receipt_id="confirmation-v2",
                intent_message_id=candidate.intent_message_id.id,
            )
        self.assertEqual(session.current_version_id, v1)
        self.assertEqual(session.document_revision, 1)

    def test_verified_candidate_rejection_is_scoped_and_does_not_advance_current(self):
        env, session, _thread, _message, _source, _request, _output, v1 = self._versioned_session_fixture()
        candidate = self._register_candidate(
            env, session,
            parent_version_id=v1.id,
            expected_document_revision=session.document_revision,
            candidate_bytes=synthetic_xlsx("rejected-candidate"),
            filename="rejected.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            idempotency_key="rejected-candidate",
            request_digest=hashlib.sha256(b"rejected-request").hexdigest(),
            intent_effect_digest=hashlib.sha256(b"rejected-effect").hexdigest(),
        )
        record_validation_receipt(env, candidate.id, verified_receipt(candidate))
        attachment_sha = hashlib.sha256(candidate.output_attachment_id.raw).hexdigest()
        decision = candidate.thread_id.message_post(
            body="Reject this synthetic Candidate.", llm_role="user", author_id=env.user.partner_id.id
        )
        rejection = CandidateRejection(
            candidate_version_id=candidate.id,
            session_id=session.id,
            owner_id=env.uid,
            intent_message_id=candidate.intent_message_id.id,
            decision_message_id=decision.id,
            parent_version_id=v1.id,
            document_revision=candidate.document_revision,
            output_sha256=candidate.output_sha256,
            effect_digest=candidate.intent_effect_digest,
        )
        self.assertEqual(reject_verified_candidate(env, candidate.id, rejection), candidate)
        self.assertEqual(reject_verified_candidate(env, candidate.id, rejection), candidate)
        session.invalidate_recordset()
        candidate.invalidate_recordset()
        self.assertEqual(candidate.state, "rejected")
        self.assertEqual(candidate.rejection_message_id, decision)
        self.assertEqual(session.current_version_id, v1)
        self.assertEqual(session.last_valid_version_id, v1)
        self.assertEqual(session.document_revision, 1)
        self.assertEqual(candidate.output_sha256, attachment_sha)
        self.assertEqual(hashlib.sha256(candidate.output_attachment_id.raw).hexdigest(), attachment_sha)
        with self.assertRaises(ValidationError):
            self._register_candidate(
                env, session,
                parent_version_id=candidate.id,
                expected_document_revision=session.document_revision,
                candidate_bytes=synthetic_xlsx("rejected-parent"),
                filename="rejected-parent.xlsx",
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                idempotency_key="rejected-parent",
                request_digest=hashlib.sha256(b"rejected-parent").hexdigest(),
            )

    def test_candidate_intent_message_cannot_be_reused_across_threads(self):
        env, session, _thread, _message, _source, _request, _output, v1 = self._versioned_session_fixture()
        _other_env, _other_session, other_thread, _other_message, _other_attachment = self._session_fixture()
        foreign_message = other_thread.message_post(
            body="Synthetic user message in another Thread.",
            llm_role="user",
            author_id=env.user.partner_id.id,
        )
        with self.assertRaises(AccessError):
            self._register_candidate(
                env, session,
                parent_version_id=v1.id,
                expected_document_revision=session.document_revision,
                candidate_bytes=synthetic_xlsx("foreign-intent"),
                filename="foreign-intent.xlsx",
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                idempotency_key="foreign-intent",
                request_digest=hashlib.sha256(b"foreign-intent").hexdigest(),
                intent_message_id=foreign_message.id,
            )

    def test_direct_orm_cannot_forge_proof_or_pointer(self):
        env, session, _thread, _message, _source, _request, _output, v1 = self._versioned_session_fixture()
        user_model = env["office.workbook.version"]
        with self.assertRaises(AccessError):
            user_model.create({
                "session_id": session.id,
                "owner_id": env.uid,
                "company_id": env.company.id,
                "version_no": 999,
                "state": "accepted_current",
                "validation_result": "VERIFIED",
                "output_sha256": "a" * 64,
            })
        with self.assertRaises(AccessError):
            v1.write({"validation_result": "VERIFIED", "state": "accepted_current"})
        with self.assertRaises(AccessError):
            v1.write({"acceptance_authorization_digest": "a" * 64})
        with self.assertRaises(AccessError):
            env["ir.attachment"].create({
                "name": "forged-version.xlsx",
                "type": "binary",
                "raw": synthetic_xlsx("forged"),
                "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "company_id": session.company_id.id,
                "public": False,
                "res_model": v1._name,
                "res_id": v1.id,
            })
        with self.assertRaises(AccessError):
            session.write({"current_version_id": v1.id, "document_revision": 999})
        self.assertEqual(session.current_version_id, v1)
        self.assertEqual(session.document_revision, 1)
