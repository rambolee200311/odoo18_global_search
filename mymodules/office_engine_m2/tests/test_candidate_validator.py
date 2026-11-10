"""Odoo integration tests for the internal Candidate Validator boundary."""

import hashlib
import json
import logging
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


def _effect(parent, input_bytes, *, expected=15, unknowns=None):
    effect = {
        "schema_version": "1",
        "parent_version_id": parent.id,
        "input_sha256": hashlib.sha256(input_bytes).hexdigest(),
        "target_scopes": [{"kind": "cell", "sheet": "Data", "address": "A1"}],
        "allowed_change_kinds": ["cell_value"],
        "expected_assertions": [{
            "kind": "cell_value", "sheet": "Data", "address": "A1",
            "value_type": "number", "value": expected,
        }] if expected is not None else [],
        "unknowns": list(unknowns or []),
    }
    encoded = json.dumps(effect, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    effect["effect_digest"] = hashlib.sha256(encoded).hexdigest()
    return effect


class TestCandidateValidator(WorkbookVersionFixtures, TransactionCase):
    def _candidate(self, candidate_bytes=None, *, effect=None, expected=15, unknowns=None, tag=None):
        from ..services.workbook_version_service import register_initial_v1

        env, session, thread, message, source_attachment = self._session_fixture()
        input_bytes = _xlsx(10)
        request, _output = self._m1_request_fixture(env, session, output_bytes=input_bytes)
        parent = register_initial_v1(env, session.id, request.id)
        candidate_bytes = candidate_bytes or _xlsx(15)
        effect = effect or _effect(parent, input_bytes, expected=expected, unknowns=unknowns)
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
            intent_effect_digest=effect["effect_digest"],
        )
        return env, session, parent, candidate, input_bytes, effect

    def test_verified_receipt_is_bound_and_does_not_advance_current(self):
        from ..services.candidate_validator import validate_workbook_candidate

        env, session, parent, candidate, input_bytes, effect = self._candidate()
        prior = (session.current_version_id.id, session.last_valid_version_id.id, session.document_revision)
        outcome = validate_workbook_candidate(env, session.id, candidate.id, effect)
        candidate.invalidate_recordset()
        session.invalidate_recordset()
        self.assertEqual(outcome["report"]["validation_result"], "VERIFIED")
        self.assertEqual(candidate.validation_result, "VERIFIED")
        self.assertEqual(candidate.state, "verified")
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
            "source_bytes=%s candidate_bytes=%s expected_effect_budget_bytes=%s",
            execution["elapsed_seconds"],
            outcome["budget"]["timeout_seconds"],
            execution["rss_observed"],
            execution["max_observed_rss_bytes"],
            execution["worker_exited"],
            outcome["budget"]["source_file_size"],
            outcome["budget"]["candidate_file_size"],
            outcome["budget"]["max_expected_effect_bytes"],
        )
        self.assertGreaterEqual(execution["elapsed_seconds"], 0)
        self.assertLessEqual(execution["elapsed_seconds"], outcome["budget"]["timeout_seconds"])
        self.assertTrue(execution["rss_observed"])
        self.assertGreater(execution["max_observed_rss_bytes"], 0)
        self.assertTrue(execution["worker_exited"])

    def test_out_of_scope_difference_records_failed_receipt_without_advancing(self):
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
        env, session, parent, candidate, _input, effect = self._candidate(candidate_bytes=output.getvalue())
        outcome = validate_workbook_candidate(env, session.id, candidate.id, effect)
        candidate.invalidate_recordset()
        session.invalidate_recordset()
        self.assertEqual(outcome["report"]["validation_result"], "FAILED")
        self.assertEqual(candidate.state, "failed")
        self.assertEqual(session.current_version_id, parent)
        self.assertEqual(session.document_revision, 1)

    def test_effect_digest_mismatch_is_rejected_before_receipt_registration(self):
        from ..services.candidate_validator import validate_workbook_candidate

        env, session, parent, candidate, input_bytes, effect = self._candidate()
        effect["effect_digest"] = "0" * 64
        with self.assertRaises(ValidationError):
            validate_workbook_candidate(env, session.id, candidate.id, effect)
        candidate.invalidate_recordset()
        self.assertEqual(candidate.state, "candidate_received")
        self.assertFalse(candidate.validation_result)

    def test_other_session_owner_cannot_read_or_validate_candidate(self):
        from ..services.candidate_validator import validate_workbook_candidate

        env, session, _parent, candidate, _input, effect = self._candidate()
        other_env = self.env(user=self.other_user.id, context={"allowed_company_ids": [self.other_user.company_id.id]})
        with self.assertRaises(AccessError):
            validate_workbook_candidate(other_env, session.id, candidate.id, effect)

    def test_malformed_candidate_registers_failed_receipt_and_keeps_parent_current(self):
        from ..services.candidate_validator import validate_workbook_candidate

        env, session, parent, candidate, _input, effect = self._candidate(candidate_bytes=b"not-a-workbook")
        outcome = validate_workbook_candidate(env, session.id, candidate.id, effect)
        candidate.invalidate_recordset()
        session.invalidate_recordset()
        self.assertEqual(outcome["report"]["validation_result"], "FAILED")
        self.assertEqual(candidate.state, "failed")
        self.assertEqual(session.current_version_id, parent)
        self.assertEqual(session.document_revision, 1)
        self.assertLessEqual(outcome["execution"]["elapsed_seconds"], outcome["budget"]["timeout_seconds"])
        self.assertTrue(outcome["execution"]["rss_observed"])
        self.assertTrue(outcome["execution"]["worker_exited"])

    def test_missing_precise_expectation_records_partial_without_advancing_current(self):
        from ..services.candidate_validator import validate_workbook_candidate

        env, session, parent, candidate, _input, effect = self._candidate(
            expected=None, unknowns=("The requested result is not precise enough to assert.",)
        )
        before = (session.current_version_id.id, session.last_valid_version_id.id, session.document_revision)
        outcome = validate_workbook_candidate(env, session.id, candidate.id, effect)
        candidate.invalidate_recordset()
        session.invalidate_recordset()
        self.assertEqual(outcome["report"]["validation_result"], "PARTIALLY_VERIFIED")
        self.assertEqual(candidate.state, "partially_verified")
        self.assertEqual(
            (session.current_version_id.id, session.last_valid_version_id.id, session.document_revision),
            before,
        )


