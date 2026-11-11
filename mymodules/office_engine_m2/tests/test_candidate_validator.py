"""Odoo integration tests for the internal Candidate Validator boundary."""

import logging
import hashlib
from io import BytesIO
from uuid import uuid4

from openpyxl import Workbook
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase

from .support import WorkbookVersionFixtures


MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_logger = logging.getLogger(__name__)


def _xlsx(value):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Data"
    sheet["A1"] = value
    sheet["B1"] = "KEEP"
    sheet["C1"] = "=A1*2"
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


class TestCandidateValidator(WorkbookVersionFixtures, TransactionCase):
    def _candidate(self, candidate_bytes=None, *, tag=None):
        from ..services.workbook_version_service import register_initial_v1

        env, session, thread, message, source_attachment = self._session_fixture()
        input_bytes = _xlsx(10)
        request, _output = self._m1_request_fixture(env, session, output_bytes=input_bytes)
        parent = register_initial_v1(env, session.id, request.id)
        candidate_bytes = candidate_bytes or _xlsx(15)
        candidate = self._register_candidate(
            env,
            session,
            parent_version_id=parent.id,
            expected_document_revision=session.document_revision,
            candidate_bytes=candidate_bytes,
            filename="neutral-candidate.xlsx",
            mimetype=MIME,
            idempotency_key="candidate-" + (tag or uuid4().hex),
            request_digest=hashlib.sha256((tag or uuid4().hex).encode()).hexdigest(),
            intent_effect_digest=False,
        )
        return env, session, parent, candidate, input_bytes

    def test_verified_receipt_is_bound_and_does_not_advance_current(self):
        from ..services.candidate_validator import validate_workbook_candidate

        env, session, parent, candidate, input_bytes = self._candidate()
        prior = (session.current_version_id.id, session.last_valid_version_id.id, session.document_revision)
        outcome = validate_workbook_candidate(env, session.id, candidate.id)
        candidate.invalidate_recordset()
        session.invalidate_recordset()
        self.assertEqual(outcome["report"]["validation_result"], "PARTIALLY_VERIFIED")
        self.assertEqual(candidate.validation_result, "PARTIALLY_VERIFIED")
        self.assertEqual(candidate.state, "partially_verified")
        self.assertEqual(candidate.validation_report_id, outcome["receipt_sha256"])
        self.assertEqual(
            (session.current_version_id.id, session.last_valid_version_id.id, session.document_revision),
            prior,
        )
        self.assertEqual(session.current_version_id, parent)
        self.assertIn("existing_value_replaced", {item["kind"] for item in outcome["report"]["risk_facts"]})
        execution = outcome["execution"]
        _logger.info(
            "CB03_RESOURCE_EVIDENCE elapsed_seconds=%.6f timeout_seconds=%s "
            "rss_observed=%s max_observed_rss_bytes=%s worker_exited=%s "
            "source_bytes=%s candidate_bytes=%s",
            execution["elapsed_seconds"],
            outcome["budget"]["timeout_seconds"],
            execution["rss_observed"],
            execution["max_observed_rss_bytes"],
            execution["worker_exited"],
            outcome["budget"]["source_file_size"],
            outcome["budget"]["candidate_file_size"],
        )
        self.assertGreaterEqual(execution["elapsed_seconds"], 0)
        self.assertLessEqual(execution["elapsed_seconds"], outcome["budget"]["timeout_seconds"])
        self.assertTrue(execution["rss_observed"])
        self.assertGreater(execution["max_observed_rss_bytes"], 0)
        self.assertTrue(execution["worker_exited"])

    def test_all_valid_workbook_differences_are_recorded_without_range_rejection(self):
        from ..services.candidate_validator import validate_workbook_candidate

        candidate_bytes = _xlsx(15)
        # Change an additional cell outside the exact target declared in the Effect.
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Data"
        sheet["A1"] = 15
        sheet["B1"] = "UNAUTHORIZED CHANGE"
        sheet["C1"] = "=A1*2"
        output = BytesIO()
        workbook.save(output)
        env, session, parent, candidate, _input = self._candidate(candidate_bytes=output.getvalue())
        outcome = validate_workbook_candidate(env, session.id, candidate.id)
        candidate.invalidate_recordset()
        session.invalidate_recordset()
        self.assertEqual(outcome["report"]["validation_result"], "PARTIALLY_VERIFIED")
        self.assertEqual(candidate.state, "partially_verified")
        self.assertTrue(any(item.get("target") == "xlsx:Data!B1" for item in outcome["report"]["actual_effects"]))
        self.assertEqual(session.current_version_id, parent)
        self.assertEqual(session.document_revision, 1)

    def test_other_session_owner_cannot_read_or_validate_candidate(self):
        from ..services.candidate_validator import validate_workbook_candidate

        env, session, _parent, candidate, _input = self._candidate()
        other_env = self.env(user=self.other_user.id, context={"allowed_company_ids": [self.other_user.company_id.id]})
        with self.assertRaises(AccessError):
            validate_workbook_candidate(other_env, session.id, candidate.id)

    def test_malformed_candidate_registers_failed_receipt_and_keeps_parent_current(self):
        from ..services.candidate_validator import validate_workbook_candidate

        env, session, parent, candidate, _input = self._candidate(candidate_bytes=b"not-a-workbook")
        outcome = validate_workbook_candidate(env, session.id, candidate.id)
        candidate.invalidate_recordset()
        session.invalidate_recordset()
        self.assertEqual(outcome["report"]["validation_result"], "FAILED")
        self.assertEqual(candidate.state, "failed")
        self.assertEqual(session.current_version_id, parent)
        self.assertEqual(session.document_revision, 1)
        self.assertLessEqual(outcome["execution"]["elapsed_seconds"], outcome["budget"]["timeout_seconds"])
        self.assertTrue(outcome["execution"]["rss_observed"])
        self.assertTrue(outcome["execution"]["worker_exited"])

    def test_no_agent_effect_contract_is_needed_to_register_validation(self):
        from ..services.candidate_validator import validate_workbook_candidate

        env, session, parent, candidate, _input = self._candidate()
        before = (session.current_version_id.id, session.last_valid_version_id.id, session.document_revision)
        outcome = validate_workbook_candidate(env, session.id, candidate.id)
        candidate.invalidate_recordset()
        session.invalidate_recordset()
        self.assertEqual(outcome["report"]["validation_result"], "PARTIALLY_VERIFIED")
        self.assertEqual(candidate.state, "partially_verified")
        self.assertEqual(
            (session.current_version_id.id, session.last_valid_version_id.id, session.document_revision),
            before,
        )


