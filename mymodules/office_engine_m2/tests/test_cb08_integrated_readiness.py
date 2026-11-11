"""CC-08 focused TransactionCase coverage for freshness and read revocation."""

import hashlib
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from openpyxl import load_workbook
from odoo.tests import TransactionCase

from .support import WorkbookVersionFixtures


class TestCB08IntegratedReadiness(WorkbookVersionFixtures, TransactionCase):
    def _office_tool(self, thread):
        thread._office_bind_tools()
        tool = thread.tool_ids.filtered(lambda item: item.name == "office")[:1]
        self.assertTrue(tool)
        return tool

    def _retriever_tool(self, thread):
        thread._office_bind_tools()
        tool = thread.tool_ids.filtered(lambda item: item.name == "odoo_record_retriever")[:1]
        self.assertTrue(tool)
        return tool

    def _retriever_call(self, thread, tool, arguments):
        call = thread.message_post(
            body="Synthetic Retriever tool call",
            body_json={"type": "tool_execution", "tool_name": "odoo_record_retriever", "status": "executing"},
            llm_role="tool",
            author_id=False,
        )
        result = tool.with_context(message=call).execute(arguments)
        call.write({
            "body_json": {
                "type": "tool_execution",
                "tool_name": "odoo_record_retriever",
                "arguments": arguments,
                "status": "completed",
                "result": result,
            }
        })
        return result

    def test_second_read_fresh_value_reaches_edit_adapter(self):
        """The edit call receives only the latest per-turn authorized Retriever result."""
        env, session, thread, _upload, _source, _request, current_attachment, initial_version = (
            self._versioned_session_fixture()
        )
        suffix = uuid4().hex
        partner = self.env["res.partner"].create({
            "name": "CC08 old name " + suffix,
            "email": "cc08-fresh-" + suffix + "@example.invalid",
            "company_id": False,
        })
        retriever = self._retriever_tool(thread)

        first_intent = thread.message_post(
            body="Read this synthetic contact.", llm_role="user", author_id=env.user.partner_id.id,
        )
        first = self._retriever_call(thread, retriever, {
            "model": "res.partner", "domain": [["id", "=", partner.id]],
            "fields": ["id", "name", "email"], "limit": 1,
            "offset": 0, "include_pagination": True,
        })
        self.assertEqual(first["records"][0]["name"], "CC08 old name " + suffix)

        new_name = "CC08 updated name " + suffix
        partner.write({"name": new_name})
        partner.invalidate_recordset()
        second_intent = thread.message_post(
            body="Use the current contact name to fill this workbook.",
            llm_role="user", author_id=env.user.partner_id.id,
        )
        second = self._retriever_call(thread, retriever, {
            "model": "res.partner", "domain": [["id", "=", partner.id]],
            "fields": ["id", "name", "email"], "limit": 1,
            "offset": 0, "include_pagination": True,
        })
        self.assertEqual(second["records"][0]["name"], new_name)

        current_bytes = current_attachment.raw
        book = load_workbook(BytesIO(current_bytes), data_only=False)
        book.active["A2"] = new_name
        candidate_stream = BytesIO()
        book.save(candidate_stream)
        book.close()
        candidate_bytes = candidate_stream.getvalue()

        class RecordingAdapter:
            def __init__(self):
                self.calls = []

            def execute(self, **kwargs):
                self.calls.append(kwargs)
                return SimpleNamespace(
                    operation_status="candidate_received",
                    candidate_bytes=candidate_bytes,
                    input_sha256=kwargs.get("input_sha256"),
                    candidate_sha256=hashlib.sha256(candidate_bytes).hexdigest(),
                    provider_response_id="cc08-test-only",
                    request_id="cc08-test-only",
                    tool_call_ids=("cc08-test-only",),
                    provider_file_ids=("cc08-test-only",),
                    provider_filename="cc08-freshness.xlsx",
                    usage={"input_tokens": 0, "output_tokens": 0},
                    duration_ms=0,
                    cleanup_state="not_required",
                    error=None,
                    to_dict=lambda: {"operation_status": "candidate_received"},
                )

        adapter = RecordingAdapter()
        office = self._office_tool(thread)
        tool_message = thread.message_post(
            body="Office edit", body_json={"type": "tool_execution", "tool_name": "office"},
            llm_role="tool", author_id=False,
        )
        revision_before = session.document_revision
        with patch(
            "odoo.addons.office_engine_m2.services.edit_orchestrator._provider_dependencies",
            return_value=(adapter, object(), "test-model", SimpleNamespace()),
        ):
            edit_result = office.with_context(message=tool_message).execute({"action": "edit"})

        self.assertEqual(edit_result["operation_status"], "candidate_review_required", edit_result)
        self.assertEqual(len(adapter.calls), 1)
        instruction = adapter.calls[0]["instruction"]
        self.assertIn(new_name, instruction)
        self.assertNotIn("CC08 old name " + suffix, instruction)
        self.assertIn(str(partner.id), instruction)
        candidate = env["office.workbook.version"].browse(edit_result["candidate_version_id"])
        self.assertTrue(candidate.exists())
        self.assertEqual(candidate.parent_version_id, initial_version)
        self.assertEqual(candidate.input_sha256, hashlib.sha256(current_bytes).hexdigest())
        output = load_workbook(BytesIO(candidate.output_attachment_id.raw), data_only=False)
        self.assertEqual(output.active["A2"].value, new_name)
        output.close()
        session.invalidate_recordset()
        self.assertEqual(session.document_revision, revision_before)
        self.assertTrue(first_intent.id < second_intent.id)

    def test_revoked_record_rule_yields_empty_fresh_context_without_candidate(self):
        """A new turn after revocation receives no previous-turn data or version side effect."""
        env, session, thread, _upload, _attachment = self._session_fixture()
        suffix = uuid4().hex
        secret_name = "CC08 restricted " + suffix
        partner = self.env["res.partner"].create({
            "name": secret_name,
            "email": "cc08-revoked-" + suffix + "@example.invalid",
            "company_id": False,
        })
        retriever = self._retriever_tool(thread)

        thread.message_post(
            body="Read the synthetic contact.", llm_role="user", author_id=env.user.partner_id.id,
        )
        first = self._retriever_call(thread, retriever, {
            "model": "res.partner", "domain": [["id", "=", partner.id]],
            "fields": ["id", "name", "email"], "limit": 1,
            "offset": 0, "include_pagination": True,
        })
        self.assertEqual(first["records"][0]["name"], secret_name)

        # This global rule and synthetic record exist only in the test transaction.
        self.env["ir.rule"].create({
            "name": "CC08 revoke read visibility " + suffix,
            "model_id": self.env["ir.model"]._get_id("res.partner"),
            "domain_force": "[('id', '!=', %d)]" % partner.id,
            "perm_read": True,
            "perm_write": False,
            "perm_create": False,
            "perm_unlink": False,
        })
        second_intent = thread.message_post(
            body="Read the same contact again using current permissions.",
            llm_role="user", author_id=env.user.partner_id.id,
        )
        second = self._retriever_call(thread, retriever, {
            "model": "res.partner", "domain": [["id", "=", partner.id]],
            "fields": ["id", "name", "email"], "limit": 1,
            "offset": 0, "include_pagination": True,
        })
        self.assertEqual(second["records"], [])
        self.assertEqual(second["count"], 0)
        self.assertNotIn(secret_name, str(second))

        office_message = thread.message_post(
            body="Office edit was not dispatched after the empty authorized read.",
            body_json={"type": "tool_execution", "tool_name": "office"},
            llm_role="tool", author_id=False,
        )
        from odoo.addons.office_engine_m2.services.edit_orchestrator import _authorized_retriever_context

        env["mail.message"].flush_model(["subtype_id", "llm_role", "model", "res_id", "body_json"])
        edit_context, _context_digest = _authorized_retriever_context(
            env, thread, second_intent.id, office_message
        )
        self.assertEqual(len(edit_context), 1)
        self.assertEqual(edit_context[0]["result"]["records"], [])
        self.assertNotIn(secret_name, str(edit_context))

        # The simulated caller stops after an empty authorized read: no Provider dispatch,
        # Candidate creation, or workbook pointer mutation occurs.
        self.assertFalse(session.current_version_id)
        self.assertFalse(session.last_valid_version_id)
        self.assertEqual(session.document_revision, 0)
        self.assertFalse(env["office.workbook.version"].search([("session_id", "=", session.id)]))
