"""Route B single-call Office lifecycle tests with a synthetic Provider."""

import hashlib
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from openpyxl import Workbook, load_workbook
from odoo.tests import TransactionCase

from .support import WorkbookVersionFixtures, attachment_values


MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _xlsx(a1=10, a2="KEEP", *, sheet_name="Data"):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = sheet_name
    sheet["A1"] = a1
    sheet["B1"] = a2
    sheet["C1"] = "=A1*2"
    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


class _FakeAdapter:
    """Test double at the Provider boundary; never used by production code."""

    def __init__(self, candidate_bytes, status="candidate_received"):
        self.candidate_bytes = candidate_bytes
        self.status = status
        self.calls = []

    def execute(self, **kwargs):
        self.calls.append(kwargs)
        data = self.candidate_bytes if self.status == "candidate_received" else None
        return SimpleNamespace(
            operation_status=self.status,
            candidate_bytes=data,
            input_sha256=kwargs.get("input_sha256"),
            candidate_sha256=hashlib.sha256(data).hexdigest() if data else None,
            provider_response_id="test-response",
            request_id="test-request",
            tool_call_ids=("test-tool-call",),
            provider_file_ids=("test-file",),
            provider_filename="candidate.xlsx",
            usage={"input_tokens": 1, "output_tokens": 1},
            duration_ms=1,
            cleanup_state="not_required",
            error=None,
            to_dict=lambda: {"operation_status": self.status, "candidate_present": bool(data)},
        )


class TestEditOrchestration(WorkbookVersionFixtures, TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._fake_limits = SimpleNamespace()

    def _versioned(self, bytes_v1=None):
        from odoo.addons.office_engine_m2.services.workbook_version_service import register_initial_v1

        env, session, thread, upload, _source_attachment = self._session_fixture()
        bytes_v1 = bytes_v1 or _xlsx()
        request, _output = self._m1_request_fixture(env, session, output_bytes=bytes_v1)
        version = register_initial_v1(env, session.id, request.id)
        session.invalidate_recordset()
        return env, session, thread, version, bytes_v1

    def _user(self, thread, body):
        return thread.message_post(body=body, llm_role="user", author_id=thread.env.user.partner_id.id)

    def _tool(self, thread):
        return thread.message_post(
            body="office", llm_role="tool", author_id=False,
            body_json={"type": "tool_execution", "tool_name": "office", "status": "completed"},
        )

    def _edit(self, env, thread, adapter, *, confirmation_required=False, confirmation_reason=None):
        tool_message = self._tool(thread)
        dependencies = (adapter, object(), "synthetic-route-b", self._fake_limits)
        with patch("odoo.addons.office_engine_m2.services.edit_orchestrator._provider_dependencies", return_value=dependencies):
            result = env["office.mapping.tool"].with_context(message=tool_message).office(
                action="edit",
                confirmation_required=confirmation_required,
                confirmation_reason=confirmation_reason,
            )
        tool_message.write({"body_json": {
            "type": "tool_execution", "tool_name": "office", "status": "completed", "result": result,
        }})
        return result, tool_message

    def _decide(self, env, thread, candidate_id, decision):
        self._user(thread, decision)
        tool_message = self._tool(thread)
        result = env["office.mapping.tool"].with_context(message=tool_message).office(
            action="accept" if decision == "接受" else "reject",
            candidate_version_id=candidate_id,
        )
        tool_message.write({"body_json": {
            "type": "tool_execution", "tool_name": "office", "status": "completed", "result": result,
        }})
        return result

    def test_office_schema_exposes_one_direct_edit_action_without_effect_contract(self):
        _env, _session, thread, _parent, _bytes = self._versioned()
        thread._office_bind_tools()
        schema = self.env["llm.tool"].search([("name", "=", "office")], limit=1).get_input_schema()
        self.assertEqual(schema["properties"]["action"]["enum"], ["status", "create", "edit", "accept", "reject", "finalize"])
        self.assertNotIn("expected_effect", schema["properties"])
        self.assertNotIn("interpretation", schema["properties"])
        self.assertNotIn("effect_digest", schema["properties"])
        self.assertNotIn("workbook_inspection_id", schema["properties"])

    def test_fileless_create_registers_and_delivers_v1_without_candidate_or_fake_source(self):
        env = self.env(user=self.owner.id, context={"allowed_company_ids": [self.owner.company_id.id]})
        thread = env["llm.thread"].create({
            "name": "Route B fileless " + uuid4().hex,
            "provider_id": self.provider.id,
            "model_id": self.model.id,
        })
        intent = self._user(thread, "Create a simple XLSX with a title and today's date.")
        adapter = _FakeAdapter(_xlsx("Title", "New workbook"))
        tool_message = self._tool(thread)
        dependencies = (adapter, object(), "synthetic-route-b", self._fake_limits)
        with patch("odoo.addons.office_engine_m2.services.edit_orchestrator._provider_dependencies", return_value=dependencies):
            result = env["office.mapping.tool"].with_context(message=tool_message).office(action="create")
        tool_message.write({"body_json": {
            "type": "tool_execution", "tool_name": "office", "status": "completed", "result": result,
        }})

        session = env["office.mapping.session"].search([("thread_id", "=", thread.id)], limit=1)
        version = session.current_version_id
        self.assertEqual(result["operation_status"], "created_v1_and_delivered", result)
        self.assertEqual(adapter.calls[0]["operation"], "create")
        self.assertIsNone(adapter.calls[0]["input_xlsx"])
        self.assertIsNone(adapter.calls[0]["input_sha256"])
        self.assertEqual(session.origin_kind, "fileless")
        self.assertFalse(session.source_attachment_id)
        self.assertFalse(session.target_model)
        self.assertFalse(session.target_record_id)
        self.assertEqual(session.source_message_id, intent)
        self.assertEqual(version.version_no, 1)
        self.assertEqual(version.state, "finalized")
        self.assertEqual(version.validation_result, "PARTIALLY_VERIFIED")
        self.assertTrue(version.filename.endswith(".xlsx"))
        self.assertEqual(version.mimetype, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        self.assertFalse(version.input_attachment_id)
        self.assertFalse(version.input_sha256)
        self.assertFalse(version.parent_version_id)
        self.assertEqual(version, session.last_valid_version_id)
        self.assertEqual(session.document_revision, 1)
        self.assertFalse(result.get("candidate_version_id"))
        self.assertFalse(result["user_acceptance_recorded"])
        self.assertTrue(result["attachment_posted_to_thread"])
        self.assertEqual(hashlib.sha256(version.final_attachment_id.raw).hexdigest(), version.output_sha256)

        # Replaying the same user intent is idempotent: reuse V1 and its final
        # attachment without a second Provider request or duplicate version.
        with patch("odoo.addons.office_engine_m2.services.edit_orchestrator._provider_dependencies", return_value=dependencies):
            retry = env["office.mapping.tool"].with_context(message=tool_message).office(action="create")
        self.assertEqual(retry["operation_status"], "created_v1_and_delivered", retry)
        self.assertEqual(len(adapter.calls), 1)
        self.assertEqual(env["office.workbook.version"].search_count([("session_id", "=", session.id)]), 1)
        self.assertEqual(retry["version_id"], result["version_id"])
        self.assertEqual(retry["attachment_id"], result["attachment_id"])

    def test_fileless_current_is_used_as_parent_for_next_edit(self):
        env = self.env(user=self.owner.id, context={"allowed_company_ids": [self.owner.company_id.id]})
        thread = env["llm.thread"].create({
            "name": "Route B fileless then edit " + uuid4().hex,
            "provider_id": self.provider.id,
            "model_id": self.model.id,
        })
        self._user(thread, "Create a simple XLSX workbook.")
        first_adapter = _FakeAdapter(_xlsx("Title", "V1"))
        first_tool = self._tool(thread)
        dependencies = (first_adapter, object(), "synthetic-route-b", self._fake_limits)
        with patch("odoo.addons.office_engine_m2.services.edit_orchestrator._provider_dependencies", return_value=dependencies):
            first_result = env["office.mapping.tool"].with_context(message=first_tool).office(action="create")
        first_tool.write({"body_json": {
            "type": "tool_execution", "tool_name": "office", "status": "completed", "result": first_result,
        }})
        session = env["office.mapping.session"].search([("thread_id", "=", thread.id)], limit=1)
        parent = session.current_version_id
        parent_bytes = parent.output_attachment_id.raw

        self._user(thread, "Change the workbook title to V2 and keep the rest.")
        second_adapter = _FakeAdapter(_xlsx("Title", "V2"))
        second_result, _tool = self._edit(env, thread, second_adapter)
        candidate = env["office.workbook.version"].browse(second_result["candidate_version_id"])
        self.assertEqual(second_adapter.calls[0]["input_xlsx"], parent_bytes)
        self.assertEqual(second_adapter.calls[0]["input_sha256"], parent.output_sha256)
        self.assertEqual(candidate.parent_version_id, parent)
        self.assertEqual(self._decide(env, thread, candidate.id, "接受")["operation_status"], "accepted_current")
        session.invalidate_recordset()
        self.assertEqual(session.current_version_id, candidate)
        self.assertEqual(session.document_revision, 2)
        self.assertTrue(thread._office_is_active())
        self.assertTrue(thread._office_is_candidate_b_route())

        # Once a fileless workbook has an accepted edit version, subsequent
        # actions must resolve that real Current byte source rather than
        # treating the original creation version as the only valid version.
        self._user(thread, "Please deliver the accepted workbook.")
        from odoo.addons.office_engine_m2.services.edit_orchestrator import _resolve_current

        context = _resolve_current(env, thread)
        self.assertEqual(context["current"], candidate)
        self.assertEqual(context["input_sha256"], candidate.output_sha256)
        self.assertEqual(context["input_bytes"], candidate.output_attachment_id.raw)

        finalize_tool = self._tool(thread)
        finalized = env["office.mapping.tool"].with_context(message=finalize_tool).office(action="finalize")
        finalize_tool.write({"body_json": {
            "type": "tool_execution", "tool_name": "office", "status": "completed", "result": finalized,
        }})
        session.invalidate_recordset()
        candidate.invalidate_recordset()
        self.assertEqual(finalized["operation_status"], "finalized", finalized)
        self.assertEqual(finalized["current_version_id"], candidate.id)
        self.assertEqual(finalized["last_valid_version_id"], candidate.id)
        self.assertEqual(finalized["document_revision"], 2)
        self.assertEqual(finalized["sha256"], candidate.output_sha256)
        self.assertEqual(candidate.state, "finalized")

    def test_initial_upload_single_edit_creates_candidate_then_accepts_v1(self):
        from odoo.addons.office_engine_m2.services.mapping_service import create_session

        env = self.env(user=self.owner.id, context={"allowed_company_ids": [self.owner.company_id.id]})
        thread = env["llm.thread"].create({
            "name": "Route B direct initial " + uuid4().hex,
            "provider_id": self.provider.id,
            "model_id": self.model.id,
        })
        source_bytes = _xlsx("Name")
        source = env["ir.attachment"].create(attachment_values(
            "initial-" + uuid4().hex + ".xlsx", source_bytes, company_id=env.company.id,
        ))
        upload = thread.message_post(
            body="Uploaded workbook", llm_role="user", author_id=env.user.partner_id.id,
            attachment_ids=[source.id],
        )
        create_session(
            env, thread_id=thread.id, source_message_id=upload.id, source_attachment_id=source.id,
            target_model="ir.attachment", target_record_id=source.id,
        )
        self._user(thread, "Fill the workbook with authorized data and let me review it.")
        candidate_bytes = _xlsx("Name", "Contact A")
        adapter = _FakeAdapter(candidate_bytes)
        result, _tool = self._edit(env, thread, adapter)
        self.assertEqual(result["operation_status"], "candidate_review_required", result)
        self.assertEqual(len(adapter.calls), 1)
        self.assertEqual(adapter.calls[0]["input_xlsx"], source_bytes)
        session = env["office.mapping.session"].search([("thread_id", "=", thread.id)], limit=1)
        candidate = env["office.workbook.version"].browse(result["candidate_version_id"])
        self.assertFalse(session.current_version_id)
        self.assertEqual(candidate.version_kind, "initial")
        self.assertEqual(candidate.state, "partially_verified")
        accepted = self._decide(env, thread, candidate.id, "接受")
        session.invalidate_recordset()
        candidate.invalidate_recordset()
        self.assertEqual(accepted["operation_status"], "accepted_current")
        self.assertEqual(session.current_version_id, candidate)
        self.assertEqual(candidate.version_no, 1)
        self.assertEqual(candidate.validation_result, "PARTIALLY_VERIFIED")
        self.assertEqual(hashlib.sha256(candidate.output_attachment_id.raw).hexdigest(), candidate.output_sha256)

    def test_one_call_edit_uses_accepted_current_and_records_all_observed_changes(self):
        env, session, thread, parent, input_bytes = self._versioned()
        self._user(thread, "Change the first cell and preserve the rest of the workbook.")
        candidate_bytes = _xlsx(15)
        adapter = _FakeAdapter(candidate_bytes)
        result, _tool = self._edit(env, thread, adapter)
        session.invalidate_recordset()
        candidate = env["office.workbook.version"].browse(result["candidate_version_id"])
        self.assertEqual(adapter.calls[0]["input_xlsx"], input_bytes)
        self.assertEqual(result["validation_result"], "PARTIALLY_VERIFIED")
        self.assertTrue(result["actual_effects"])
        self.assertEqual(session.current_version_id, parent)
        self.assertEqual(candidate.parent_version_id, parent)
        self.assertEqual(self._decide(env, thread, candidate.id, "接受")["operation_status"], "accepted_current")
        session.invalidate_recordset()
        self.assertEqual(session.current_version_id, candidate)
        self.assertEqual(candidate.validation_result, "PARTIALLY_VERIFIED")

    def test_two_successive_edits_use_successive_accepted_workbook_bytes(self):
        env, session, thread, parent, input_bytes = self._versioned()
        self._user(thread, "Set A1 to 15.")
        first_bytes = _xlsx(15)
        first, _ = self._edit(env, thread, _FakeAdapter(first_bytes))
        first_candidate = env["office.workbook.version"].browse(first["candidate_version_id"])
        self._decide(env, thread, first_candidate.id, "接受")
        session.invalidate_recordset()
        v2 = session.current_version_id
        v2_bytes = v2.output_attachment_id.raw

        self._user(thread, "Now add 20 in A2, preserving the accepted workbook.")
        book = load_workbook(BytesIO(v2_bytes), data_only=False)
        book["Data"]["A2"] = 20
        out = BytesIO()
        book.save(out)
        book.close()
        second_adapter = _FakeAdapter(out.getvalue())
        second, _ = self._edit(env, thread, second_adapter)
        v3 = env["office.workbook.version"].browse(second["candidate_version_id"])
        self.assertEqual(second_adapter.calls[0]["input_xlsx"], v2_bytes)
        self.assertEqual(v3.parent_version_id, v2)
        self.assertEqual(v3.input_sha256, v2.output_sha256)
        self._decide(env, thread, v3.id, "接受")
        session.invalidate_recordset()
        workbook = load_workbook(BytesIO(session.current_version_id.output_attachment_id.raw), data_only=False)
        self.assertEqual(workbook["Data"]["A1"].value, 15)
        self.assertEqual(workbook["Data"]["A2"].value, 20)
        self.assertEqual(session.current_version_id, v3)
        self.assertEqual(v3.parent_version_id, v2)
        self.assertEqual(session.last_valid_version_id, v3)
        self.assertEqual(session.document_revision, 3)
        self.assertEqual(parent.version_no, 1)

    def test_reject_does_not_advance_current_or_last_valid(self):
        env, session, thread, current, _input = self._versioned()
        before = (session.current_version_id.id, session.last_valid_version_id.id, session.document_revision)
        self._user(thread, "Make another edit for review.")
        result, _ = self._edit(env, thread, _FakeAdapter(_xlsx(12)))
        rejected = self._decide(env, thread, result["candidate_version_id"], "拒绝")
        session.invalidate_recordset()
        self.assertEqual(rejected["operation_status"], "candidate_rejected")
        self.assertEqual(
            (session.current_version_id.id, session.last_valid_version_id.id, session.document_revision), before,
        )
        self.assertEqual(session.current_version_id, current)

    def test_failed_xlsx_is_blocked_but_valid_unexpected_changes_are_review_data(self):
        env, session, thread, parent, _input = self._versioned()
        self._user(thread, "Rearrange this workbook.")
        out = load_workbook(BytesIO(_xlsx(15)))
        out["Data"]["B1"] = "also changed"
        stream = BytesIO()
        out.save(stream)
        result, _ = self._edit(env, thread, _FakeAdapter(stream.getvalue()))
        session.invalidate_recordset()
        self.assertEqual(result["validation_result"], "PARTIALLY_VERIFIED")
        self.assertEqual(session.current_version_id, parent)
        self.assertTrue(any(item.get("target") == "xlsx:Data!B1" for item in result["actual_effects"]))

        self._user(thread, "Try the invalid workbook.")
        corrupt, _ = self._edit(env, thread, _FakeAdapter(b"not an xlsx"))
        session.invalidate_recordset()
        self.assertEqual(corrupt["validation_result"], "FAILED")
        self.assertEqual(corrupt["operation_status"], "candidate_technical_validation_failed")
        self.assertEqual(session.current_version_id, parent)

    def test_confirmation_is_only_requested_when_agent_reports_a_business_risk(self):
        env, session, thread, parent, _input = self._versioned()
        self._user(thread, "Clear the existing values in the requested area.")
        adapter = _FakeAdapter(_xlsx(None))
        pending, _ = self._edit(
            env, thread, adapter, confirmation_required=True,
            confirmation_reason="This request may remove existing business data.",
        )
        self.assertEqual(pending["operation_status"], "awaiting_user_decision")
        self.assertEqual(adapter.calls, [])
        self.assertEqual(session.current_version_id, parent)
        self._user(thread, "确认")
        result, _ = self._edit(
            env, thread, adapter, confirmation_required=True,
            confirmation_reason="This request may remove existing business data.",
        )
        self.assertEqual(result["operation_status"], "candidate_review_required")
        self.assertEqual(len(adapter.calls), 1)

    def test_provider_failure_and_dispatch_disabled_leave_current_unchanged(self):
        env, session, thread, current, _input = self._versioned()
        self._user(thread, "Make a file edit.")
        result, _ = self._edit(env, thread, _FakeAdapter(None, status="indeterminate"))
        self.assertEqual(result["operation_status"], "provider_candidate_unavailable")
        self.assertEqual(session.current_version_id, current)

        self._user(thread, "Try another edit.")
        tool_message = self._tool(thread)
        with patch("odoo.addons.office_engine_m2.services.edit_orchestrator._provider_dependencies", return_value=None):
            blocked = env["office.mapping.tool"].with_context(message=tool_message).office(action="edit")
        self.assertEqual(blocked["operation_status"], "provider_dispatch_disabled")
        self.assertEqual(session.current_version_id, current)

    def test_finalize_delivers_exact_accepted_current(self):
        env, session, thread, current, _ = self._versioned()
        self._user(thread, "Please finalize and deliver the accepted workbook.")
        tool_message = self._tool(thread)
        delivered = env["office.mapping.tool"].with_context(message=tool_message).office(action="finalize")
        session.invalidate_recordset()
        current.invalidate_recordset()
        self.assertEqual(delivered["operation_status"], "finalized")
        self.assertEqual(delivered["current_version_id"], current.id)
        self.assertEqual(current.final_attachment_id, current.output_attachment_id)
        self.assertEqual(hashlib.sha256(current.final_attachment_id.raw).hexdigest(), current.output_sha256)
        self.assertTrue(current.final_message_id.attachment_ids)
