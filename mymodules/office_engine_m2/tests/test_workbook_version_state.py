"""Version state, restore, atomicity, and attachment immutability tests."""

import hashlib
from unittest.mock import patch

from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase

from .support import WorkbookVersionFixtures, synthetic_xlsx
from .support.validator_stub import restore_confirmation, verified_receipt
from ..models.office_mapping_session import OfficeMappingSession
from ..services.workbook_version_service import (
    accept_verified_candidate,
    finalize_accepted_current,
    record_validation_receipt,
    record_finalize_reference,
    request_restore_candidate,
)


class TestWorkbookVersionState(WorkbookVersionFixtures, TransactionCase):
    def test_candidate_b_finalize_delivers_exact_current_and_is_idempotent(self):
        env, session, thread, _upload, _source, _request, _m1_output, current = self._versioned_session_fixture()
        initial_revision = session.document_revision
        initial_sha = current.output_sha256
        first_intent = thread.message_post(
            body="Please deliver the accepted workbook.",
            llm_role="user",
            author_id=env.user.partner_id.id,
        )

        delivered = finalize_accepted_current(
            env, session.id, current.id, initial_revision, first_intent.id
        )
        session.invalidate_recordset()
        current.invalidate_recordset()
        self.assertEqual(current.state, "finalized")
        self.assertEqual(current.validation_result, "VERIFIED")
        self.assertEqual(current.delivery_state, "delivered")
        self.assertEqual(current.final_attachment_id, current.output_attachment_id)
        self.assertEqual(current.final_message_id, delivered["message"])
        self.assertEqual(delivered["message"].model, thread._name)
        self.assertEqual(delivered["message"].res_id, thread.id)
        self.assertEqual(delivered["message"].llm_role, "assistant")
        self.assertIn(current.output_attachment_id, delivered["message"].attachment_ids)
        self.assertEqual(delivered["output_sha256"], initial_sha)
        self.assertEqual(session.current_version_id, current)
        self.assertEqual(session.last_valid_version_id, current)
        self.assertEqual(session.document_revision, initial_revision)

        retry_intent = thread.message_post(
            body="Please deliver the same accepted workbook again.",
            llm_role="user",
            author_id=env.user.partner_id.id,
        )
        repeated = finalize_accepted_current(
            env, session.id, current.id, initial_revision, retry_intent.id
        )
        self.assertEqual(repeated["attachment"], delivered["attachment"])
        self.assertEqual(repeated["message"], delivered["message"])
        self.assertEqual(
            env["mail.message"].search_count(
                [
                    ("model", "=", thread._name),
                    ("res_id", "=", thread.id),
                    ("llm_role", "=", "assistant"),
                    ("attachment_ids", "in", [current.output_attachment_id.id]),
                ]
            ),
            1,
        )

    def test_candidate_b_finalize_preserves_partially_verified_grade(self):
        env, session, thread, _upload, _source, _request, _output, parent = self._versioned_session_fixture()
        candidate = self._register_candidate(
            env,
            session,
            parent_version_id=parent.id,
            expected_document_revision=session.document_revision,
            candidate_bytes=synthetic_xlsx("partial-finalize"),
            filename="partial-finalize.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            idempotency_key="partial-finalize",
            request_digest=hashlib.sha256(b"partial-finalize").hexdigest(),
        )
        receipt = verified_receipt(candidate)
        object.__setattr__(receipt, "validation_result", "PARTIALLY_VERIFIED")
        record_validation_receipt(env, candidate.id, receipt)
        self._accept_candidate(env, candidate)
        session.invalidate_recordset()
        accepted_revision = session.document_revision
        intent = thread.message_post(
            body="Deliver the accepted workbook while retaining its validation status.",
            llm_role="user",
            author_id=env.user.partner_id.id,
        )

        delivered = finalize_accepted_current(
            env, session.id, candidate.id, accepted_revision, intent.id
        )
        session.invalidate_recordset()
        candidate.invalidate_recordset()
        self.assertEqual(candidate.state, "finalized")
        self.assertEqual(candidate.validation_result, "PARTIALLY_VERIFIED")
        self.assertEqual(delivered["version"].validation_result, "PARTIALLY_VERIFIED")
        self.assertEqual(session.current_version_id, candidate)
        self.assertEqual(session.last_valid_version_id, candidate)
        self.assertEqual(session.document_revision, accepted_revision)
        self.assertEqual(candidate.final_attachment_id, candidate.output_attachment_id)

    def test_candidate_attachment_creation_failure_rolls_back_metadata(self):
        env, session, _thread, _message, _source, _request, _output, v1 = self._versioned_session_fixture()
        before_count = env["office.workbook.version"].search_count([("session_id", "=", session.id)])
        with patch(
            "odoo.addons.office_engine_m2.services.workbook_version_service._create_version_attachment",
            side_effect=ValidationError("synthetic attachment storage failure"),
        ):
            with self.assertRaisesRegex(ValidationError, "synthetic attachment storage failure"):
                self._register_candidate(
                    env, session,
                    parent_version_id=v1.id,
                    expected_document_revision=session.document_revision,
                    candidate_bytes=synthetic_xlsx("attachment-failure"),
                    filename="attachment-failure.xlsx",
                    mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    idempotency_key="attachment-failure",
                    request_digest=hashlib.sha256(b"attachment-failure").hexdigest(),
                )
        self.assertEqual(
            env["office.workbook.version"].search_count([("session_id", "=", session.id)]),
            before_count,
        )
        self.assertEqual(session.current_version_id, v1)
        self.assertEqual(session.last_valid_version_id, v1)

    def test_acceptance_rollback_preserves_prior_effective_version(self):
        env, session, _thread, _message, _source, _request, _output, v1 = self._versioned_session_fixture()
        candidate = self._register_candidate(
            env, session,
            parent_version_id=v1.id,
            expected_document_revision=session.document_revision,
            candidate_bytes=synthetic_xlsx("accept-rollback"),
            filename="accept-rollback.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            idempotency_key="accept-rollback",
            request_digest=hashlib.sha256(b"accept-rollback").hexdigest(),
        )
        record_validation_receipt(env, candidate.id, verified_receipt(candidate))
        with patch.object(
            OfficeMappingSession,
            "_advance_document_version_from_service",
            side_effect=ValidationError("synthetic pointer update failure"),
        ):
            with self.assertRaisesRegex(ValidationError, "synthetic pointer update failure"):
                self._accept_candidate(env, candidate)
        session.invalidate_recordset()
        candidate.invalidate_recordset()
        v1.invalidate_recordset()
        self.assertEqual(session.current_version_id, v1)
        self.assertEqual(session.last_valid_version_id, v1)
        self.assertEqual(session.document_revision, 1)
        self.assertEqual(v1.state, "accepted_current")
        self.assertEqual(candidate.state, "verified")

    def test_partial_receipt_waits_for_user_decision_and_failed_results_never_advance(self):
        env, session, _thread, _message, _source, _request, _output, v1 = self._versioned_session_fixture()
        for result in ("PARTIALLY_VERIFIED", "FAILED", "REJECTED"):
            candidate = self._register_candidate(
                env, session,
                parent_version_id=v1.id,
                expected_document_revision=session.document_revision,
                candidate_bytes=synthetic_xlsx("result-" + result.lower()),
                filename="result-" + result.lower() + ".xlsx",
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                idempotency_key="result-" + result.lower(),
                request_digest=hashlib.sha256(result.encode()).hexdigest(),
            )
            receipt = verified_receipt(candidate)
            object.__setattr__(receipt, "validation_result", result)
            record_validation_receipt(env, candidate.id, receipt)
            if result == "PARTIALLY_VERIFIED":
                # Validation registration is not user acceptance; unbound service
                # calls still cannot promote a partial Candidate.
                with self.assertRaises(AccessError):
                    accept_verified_candidate(env, candidate.id)
            else:
                with self.assertRaises(ValidationError):
                    self._accept_candidate(env, candidate)
            self.assertEqual(
                candidate.state,
                {"PARTIALLY_VERIFIED": "partially_verified", "FAILED": "failed", "REJECTED": "rejected"}[result],
            )
            session.invalidate_recordset()
            self.assertEqual(session.current_version_id, v1)
            self.assertEqual(session.document_revision, 1)
    def test_finalized_reference_matches_current_bytes_and_is_immutable(self):
        env, session, thread, _message, _source, _request, output, version = self._versioned_session_fixture()
        message = thread.message_post(
            body="Synthetic final workbook delivery.",
            llm_role="assistant",
            attachment_ids=[output.id],
        )
        record_finalize_reference(env, version.id, output.id, message.id)
        self.assertEqual(version.state, "finalized")
        self.assertEqual(version.delivery_state, "delivered")
        self.assertEqual(version.final_attachment_id, output)
        self.assertEqual(version.final_message_id, message)
        self.assertEqual(session.current_version_id, version)
        self.assertEqual(
            record_finalize_reference(env, version.id, output.id, message.id),
            version,
        )
        with self.assertRaises(AccessError):
            output.write({"name": "mutated-after-finalize.xlsx"})

    def test_finalization_rejects_mismatched_bytes_or_wrong_thread_message(self):
        env, session, thread, _message, _source, _request, _output, version = self._versioned_session_fixture()
        wrong_bytes = self.env["ir.attachment"].create(
            {
                "name": "different-final.xlsx",
                "type": "binary",
                "raw": synthetic_xlsx("different-final"),
                "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "company_id": session.company_id.id,
                "public": False,
                "res_model": session._name,
                "res_id": session.id,
            }
        )
        message = thread.message_post(body="Wrong output", llm_role="assistant", attachment_ids=[wrong_bytes.id])
        with self.assertRaises(ValidationError):
            record_finalize_reference(env, version.id, wrong_bytes.id, message.id)
        self.assertEqual(session.current_version_id, version)
        self.assertEqual(version.delivery_state, "not_finalized")

    def test_new_current_supersedes_finalized_version_without_losing_delivery_reference(self):
        env, session, thread, _message, _source, _request, output, version = self._versioned_session_fixture()
        message = thread.message_post(
            body="Synthetic final workbook delivery.",
            llm_role="assistant",
            attachment_ids=[output.id],
        )
        record_finalize_reference(env, version.id, output.id, message.id)
        candidate = self._register_candidate(
            env, session,
            parent_version_id=version.id,
            expected_document_revision=session.document_revision,
            candidate_bytes=synthetic_xlsx("after-finalize"),
            filename="after-finalize.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            idempotency_key="after-finalize",
            request_digest=hashlib.sha256(b"after-finalize").hexdigest(),
        )
        record_validation_receipt(env, candidate.id, verified_receipt(candidate))
        self._accept_candidate(env, candidate)
        self.assertEqual(version.state, "superseded")
        self.assertEqual(version.delivery_state, "delivered")
        self.assertEqual(version.final_attachment_id, output)
        self.assertEqual(session.current_version_id, candidate)

    def test_restore_creates_new_child_and_requires_fresh_confirmation_and_proof(self):
        env, session, _thread, _message, _source, _request, _output, v1 = self._versioned_session_fixture()
        v2 = self._register_candidate(
            env, session, parent_version_id=v1.id,
            expected_document_revision=session.document_revision,
            candidate_bytes=self._m1_request_fixture(env, session)[1].raw,
            filename="candidate-v2.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            idempotency_key="restore-source-v2", request_digest=hashlib.sha256(b"v2").hexdigest(),
            intent_effect_digest=hashlib.sha256(b"effect-v2").hexdigest(),
        )
        record_validation_receipt(env, v2.id, verified_receipt(v2))
        self._accept_candidate(env, v2)
        session.invalidate_recordset()
        v3 = self._register_candidate(
            env, session, parent_version_id=v2.id,
            expected_document_revision=session.document_revision,
            candidate_bytes=self._m1_request_fixture(env, session)[1].raw,
            filename="candidate-v3.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            idempotency_key="restore-source-v3", request_digest=hashlib.sha256(b"v3").hexdigest(),
            intent_effect_digest=hashlib.sha256(b"effect-v3").hexdigest(),
        )
        record_validation_receipt(env, v3.id, verified_receipt(v3))
        self._accept_candidate(env, v3)
        session.invalidate_recordset()
        source_hash = v1.output_sha256
        source_bytes = v1.output_attachment_id.raw
        confirmation = restore_confirmation(session, v1)
        recovery = request_restore_candidate(
            env,
            session.id,
            v1.id,
            expected_current_version_id=v3.id,
            expected_document_revision=session.document_revision,
            idempotency_key="restore-v1-from-v3",
            confirmation_receipt=confirmation,
        )
        session.invalidate_recordset()
        self.assertEqual(recovery.parent_version_id, v3)
        self.assertEqual(recovery.restored_from_version_id, v1)
        self.assertEqual(recovery.state, "candidate_received")
        self.assertEqual(recovery.confirmation_receipt_id, confirmation.receipt_id)
        self.assertEqual(session.current_version_id, v3)
        self.assertEqual(v1.output_sha256, source_hash)
        self.assertEqual(v1.output_attachment_id.raw, source_bytes)
        record_validation_receipt(env, recovery.id, verified_receipt(recovery))
        accept_verified_candidate(env, recovery.id)
        session.invalidate_recordset()
        self.assertEqual(session.current_version_id, recovery)
        self.assertEqual(recovery.output_sha256, source_hash)
        self.assertEqual(recovery.accepted_document_revision, 4)
        self.assertEqual(v1.state, "superseded")
        self.assertEqual(v3.state, "superseded")

    def test_restore_rejects_old_confirmation_and_stale_revision(self):
        env, session, _thread, _message, _source, _request, _output, v1 = self._versioned_session_fixture()
        v2 = self._register_candidate(
            env, session, parent_version_id=v1.id,
            expected_document_revision=session.document_revision,
            candidate_bytes=self._m1_request_fixture(env, session)[1].raw,
            filename="current-v2.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            idempotency_key="restore-current-v2", request_digest=hashlib.sha256(b"current-v2").hexdigest(),
        )
        record_validation_receipt(env, v2.id, verified_receipt(v2))
        self._accept_candidate(env, v2)
        session.invalidate_recordset()
        confirmation = restore_confirmation(session, v1)
        recovery = request_restore_candidate(
            env, session.id, v1.id,
            expected_current_version_id=v2.id,
            expected_document_revision=session.document_revision,
            idempotency_key="restore-v1", confirmation_receipt=confirmation,
        )
        record_validation_receipt(env, recovery.id, verified_receipt(recovery))
        accept_verified_candidate(env, recovery.id)
        session.invalidate_recordset()
        with self.assertRaises(ValidationError):
            request_restore_candidate(
                env, session.id, v1.id,
                expected_current_version_id=v2.id,
                expected_document_revision=2,
                idempotency_key="restore-stale-current",
                confirmation_receipt=confirmation,
            )
        self.assertEqual(session.current_version_id, recovery)
        self.assertEqual(session.document_revision, 3)

    def test_failed_receipt_and_attachment_write_do_not_mutate_last_valid(self):
        env, session, _thread, _message, _source, _request, _output, v1 = self._versioned_session_fixture()
        candidate = self._register_candidate(
            env, session, parent_version_id=v1.id,
            expected_document_revision=session.document_revision,
            candidate_bytes=v1.output_attachment_id.raw,
            filename="candidate.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            idempotency_key="candidate-fail", request_digest=hashlib.sha256(b"candidate").hexdigest(),
            intent_effect_digest=hashlib.sha256(b"effect").hexdigest(),
        )
        with self.assertRaises(AccessError):
            candidate.output_attachment_id.write({"name": "changed.xlsx"})
        receipt = verified_receipt(candidate)
        object.__setattr__(receipt, "validation_result", "FAILED")
        record_validation_receipt(env, candidate.id, receipt)
        self.assertEqual(candidate.state, "failed")
        self.assertEqual(candidate.validation_result, "FAILED")
        with self.assertRaises(ValidationError):
            self._accept_candidate(env, candidate)
        session.invalidate_recordset()
        self.assertEqual(session.current_version_id, v1)
        self.assertEqual(session.last_valid_version_id, v1)
        self.assertEqual(session.document_revision, 1)
