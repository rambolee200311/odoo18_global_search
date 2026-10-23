import base64
import os
from io import BytesIO
from unittest.mock import patch
from uuid import uuid4

from openpyxl import Workbook, load_workbook
from odoo.exceptions import UserError
from odoo.tests import TransactionCase

from odoo.addons.office_engine_odoo.models.office_document_request import _internal_mutation
from office_core import ResourceBudget, inspect_document, render_candidate
from office_verify import VerificationBudget, VerificationPolicy, verify_output

from ..services.mapping_service import (
    confirm_mapping,
    create_session,
    get_mapping_card_context,
    save_mapping_edits,
    set_mapping_context,
)
from ..services.render_bridge import _stable_request_uuid, render_confirmed_mapping


class TestOfficeRenderBridge(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.provider = cls.env["llm.provider"].create(
            {"name": "M2-005 Render Provider " + uuid4().hex, "service": "openai"}
        )
        cls.model = cls.env["llm.model"].create(
            {"name": "gpt-5.6-luna", "provider_id": cls.provider.id, "model_use": "chat"}
        )
        cls.retriever = cls.env.ref("llm_tool.llm_tool_odoo_record_retriever")

    def _session(self):
        target = self.env["res.partner"].create(
            {"name": "Fresh value " + uuid4().hex, "company_id": self.env.company.id}
        )
        thread = self.env["llm.thread"].create(
            {
                "name": "M2-005 render thread " + uuid4().hex,
                "provider_id": self.provider.id,
                "model_id": self.model.id,
            }
        )
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "Sheet"
        worksheet["A1"] = "Customer"
        worksheet["B1"] = None
        buffer = BytesIO()
        workbook.save(buffer)
        attachment = self.env["ir.attachment"].create(
            {
                "name": "m2-005-render-" + uuid4().hex + ".xlsx",
                "type": "binary",
                "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "datas": base64.b64encode(buffer.getvalue()),
            }
        )
        message = thread.message_post(
            body="Synthetic export request.", llm_role="user", attachment_ids=[attachment.id]
        )
        created = create_session(
            self.env,
            thread_id=thread.id,
            source_message_id=message.id,
            source_attachment_id=attachment.id,
            target_model="res.partner",
            target_record_id=target.id,
        )
        session = self.env["office.mapping.session"].browse(created["session_id"])
        manifest = [
            {
                "element_id": "xlsx:Sheet!B1",
                "required": True,
                "writable": True,
                "allowed_value_types": ["string"],
                "approved_to_skip": False,
            }
        ]
        set_mapping_context(self.env, session.id, manifest, {"name": "string"})
        save_mapping_edits(
            self.env,
            session.id,
            session.revision,
            [{"element_id": "xlsx:Sheet!B1", "source_field": "name", "value_type": "string"}],
        )
        session.invalidate_recordset()
        confirmed = confirm_mapping(self.env, session.id, session.revision)
        return session, thread, message, attachment, target, confirmed["revision"]

    def _approved_synthetic_environment(self):
        return patch.dict(
            os.environ,
            {
                "OFFICE_ENGINE_M2_DATA_POLICY_APPROVED": "1",
                "OFFICE_ENGINE_M2_SAFE_FIELDS_JSON": '{"res.partner":["name"]}',
            },
        )

    def test_confirmed_revision_retrieves_fresh_data_and_calls_m1_idempotently(self):
        session, thread, message, source, target, revision = self._session()
        request_model = self.env["office.document.request"]
        source_hash = "a" * 64
        output_bytes = b"synthetic-m1-output"
        calls = []

        def fake_m1(_request_recordset, request_uuid, source_attachment_id, plan, thread_id, message_id):
            calls.append((request_uuid, plan, source_attachment_id, thread_id, message_id))
            request = request_model.search([("request_uuid", "=", request_uuid)], limit=1)
            if not request:
                with _internal_mutation():
                    request = request_model.create(
                        {
                            "request_uuid": request_uuid,
                            "thread_id": thread_id,
                            "input_message_id": message_id,
                            "source_attachment_id": source_attachment_id,
                            "input_sha256": source_hash,
                        }
                    )
                    output = self.env["ir.attachment"].create(
                        {
                            "name": "m2-005-result-" + uuid4().hex + ".xlsx",
                            "type": "binary",
                            "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            "raw": output_bytes,
                            "public": False,
                            "res_model": request._name,
                            "res_id": request.id,
                        }
                    )
                    request.write({"state": "validating"})
                    request.write({"state": "processing"})
                    request.write(
                        {
                            "output_attachment_id": output.id,
                            "output_sha256": source_hash,
                            "state": "generated",
                        }
                    )
            else:
                output = request.output_attachment_id
            return {"state": "generated", "output_attachment_id": output.id}

        with self._approved_synthetic_environment(), patch.object(
            type(request_model), "_inspect_chat_attachment", return_value={"template_sha256": source_hash}
        ), patch.object(type(request_model), "_render_request_sync", autospec=True, side_effect=fake_m1):
            result = render_confirmed_mapping(self.env, session.id, revision)
            session.invalidate_recordset()
            duplicate = render_confirmed_mapping(self.env, session.id, revision)

        self.assertEqual(result["state"], "completed")
        self.assertEqual(session.state, "completed")
        self.assertTrue(result["download_url"].endswith("?download=true"))
        self.assertEqual(result["output_attachment_id"], duplicate["output_attachment_id"])
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][1]["writes"][0]["value"]["data"], target.name)
        self.assertEqual(calls[0][1]["template_sha256"], source_hash)
        self.assertEqual(calls[0][2:], (source.id, thread.id, message.id))

    def test_list_rows_expand_to_explicit_m1_writes_in_relation_order(self):
        session, thread, message, source, target, _revision = self._session()
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = "Sheet"
        worksheet["B1"] = "Customer placeholder"
        worksheet["A8"] = "First detail placeholder"
        worksheet["A9"] = "Second detail placeholder"
        worksheet["C1"] = "=1+1"
        source_buffer = BytesIO()
        workbook.save(source_buffer)
        workbook.close()
        source.write({"datas": base64.b64encode(source_buffer.getvalue())})
        source_bytes = source_buffer.getvalue()
        mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        resource_budget = ResourceBudget(
            max_file_size=8 * 1024 * 1024,
            max_expanded_size=32 * 1024 * 1024,
            max_zip_entries=128,
            max_entry_size=8 * 1024 * 1024,
            max_xml_elements=100_000,
            max_cells=50_000,
            max_paragraphs=10_000,
            max_memory_bytes=2 * 1024 * 1024 * 1024,
            timeout_seconds=15,
        )
        verify_budget = VerificationBudget(
            max_file_size=8 * 1024 * 1024,
            max_expanded_size=32 * 1024 * 1024,
            max_zip_entries=128,
            max_entry_size=8 * 1024 * 1024,
            max_xml_elements=100_000,
            max_cells=50_000,
            max_paragraphs=10_000,
            max_mapping_bytes=64 * 1024,
            max_memory_bytes=2 * 1024 * 1024 * 1024,
            timeout_seconds=15,
        )
        inspection = inspect_document(source_bytes, source.name, mime, resource_budget)
        children = self.env["res.partner"].create([
            {"name": "First detail", "parent_id": target.id, "company_id": self.env.company.id},
            {"name": "Second detail", "parent_id": target.id, "company_id": self.env.company.id},
        ])
        manifest = [
            {
                "element_id": "xlsx:Sheet!B1",
                "required": True,
                "writable": True,
                "allowed_value_types": ["string"],
                "approved_to_skip": False,
            },
            *[
                {
                    "element_id": f"xlsx:Sheet!A{index + 8}",
                    "required": True,
                    "writable": True,
                    "allowed_value_types": ["string"],
                    "approved_to_skip": False,
                }
                for index in range(2)
            ],
        ]
        group = {
            "group_id": "order_lines",
            "collection_field": "child_ids",
            "relation_model": "res.partner",
            "row_count": 2,
            "target_rows": [
                {
                    "row_index": index,
                    "targets": [{"column_id": "name", "element_id": f"xlsx:Sheet!A{index + 8}"}],
                }
                for index in range(2)
            ],
            "allowed_fields": {"name": "string"},
        }
        set_mapping_context(self.env, session.id, manifest, {"name": "string"}, [group])
        from office_mapping_verify import validate_user_revision
        from ..services.mapping_service import _load_mapping_data

        rules, checked_manifest, root_fields, saved_groups = _load_mapping_data(session)
        edit_values = [
            {"element_id": "xlsx:Sheet!B1", "source_field": "name", "value_type": "string"},
            *[
                {
                    "element_id": f"xlsx:Sheet!A{index + 8}",
                    "source_field": "order_lines::name",
                    "value_type": "string",
                }
                for index in range(2)
            ],
        ]
        combined_fields = {**root_fields, "order_lines::name": "string"}
        revision_report = validate_user_revision(rules, edit_values, checked_manifest, combined_fields)
        self.assertEqual(
            revision_report.status,
            "ready",
            f"report={revision_report.to_dict()!r}; groups={saved_groups!r}",
        )
        save_mapping_edits(
            self.env,
            session.id,
            session.revision,
            edit_values,
        )
        session.invalidate_recordset()
        confirmed = confirm_mapping(self.env, session.id, session.revision)
        request_model = self.env["office.document.request"]
        actual_reports = []

        def fake_m1(_request_recordset, _request_uuid, _attachment_id, plan, _thread_id, _message_id):
            candidate = render_candidate(source_bytes, source.name, mime, plan, resource_budget)
            report = verify_output(
                source_bytes,
                candidate.content,
                source.name,
                mime,
                plan,
                VerificationPolicy(enabled_formats=("xlsx",), require_styles=True),
                verify_budget,
            )
            actual_reports.append((report, candidate.content, plan))
            return {"state": "generated", "output_attachment_id": 2_000_000_021}

        with self._approved_synthetic_environment(), patch.object(
            type(request_model),
            "_inspect_chat_attachment",
            return_value={"template_sha256": inspection.template_sha256},
        ), patch.object(
            type(request_model), "_render_request_sync", autospec=True, side_effect=fake_m1
        ) as render_call:
            result = render_confirmed_mapping(self.env, session.id, confirmed["revision"])

        plan = actual_reports[0][2]
        self.assertEqual(result["state"], "completed")
        self.assertEqual(
            [(write["element_id"], write["value"]["data"]) for write in plan["writes"]],
            [
                ("xlsx:Sheet!B1", target.name),
                ("xlsx:Sheet!A8", children[0].name),
                ("xlsx:Sheet!A9", children[1].name),
            ],
        )
        self.assertEqual(actual_reports[0][0].status, "PASS")
        self.assertEqual(actual_reports[0][0].checked_targets, 3)
        rendered = load_workbook(BytesIO(actual_reports[0][1]), data_only=False)
        try:
            self.assertEqual(rendered["Sheet"]["B1"].value, target.name)
            self.assertEqual(rendered["Sheet"]["A8"].value, children[0].name)
            self.assertEqual(rendered["Sheet"]["A9"].value, children[1].name)
            self.assertEqual(rendered["Sheet"]["C1"].value, "=1+1")
        finally:
            rendered.close()

    def test_m1_failure_sets_failed_and_returns_no_download(self):
        session, _thread, _message, _source, _target, revision = self._session()
        request_model = self.env["office.document.request"]
        with self._approved_synthetic_environment(), patch.object(
            type(request_model), "_inspect_chat_attachment", return_value={"template_sha256": "b" * 64}
        ), patch.object(
            type(request_model),
            "_render_request_sync",
            return_value={"state": "failed", "error_code": "OFFICE_INTEGRITY_FAILED", "output_attachment_id": False},
        ):
            result = render_confirmed_mapping(self.env, session.id, revision)

        session.invalidate_recordset()
        self.assertEqual(result["state"], "failed")
        self.assertFalse(result["output_attachment_id"])
        self.assertNotIn("download_url", result)
        self.assertEqual(session.state, "failed")

    def test_retriever_failure_stops_before_m1_and_does_not_complete_session(self):
        session, _thread, _message, _source, _target, revision = self._session()
        request_model = self.env["office.document.request"]
        retriever = self.env.ref("llm_tool.llm_tool_odoo_record_retriever")
        before_requests = self.env["office.document.request"].search_count([])
        with self._approved_synthetic_environment(), patch.object(
            type(retriever), "execute", autospec=True, side_effect=TimeoutError("synthetic timeout")
        ), patch.object(
            type(request_model), "_inspect_chat_attachment", return_value={"template_sha256": "e" * 64}
        ), patch.object(type(request_model), "_render_request_sync") as render_call:
            with self.assertRaises(UserError):
                render_confirmed_mapping(self.env, session.id, revision)

        session.invalidate_recordset()
        self.assertEqual(render_call.call_count, 0)
        self.assertEqual(session.state, "awaiting_confirmation")
        self.assertEqual(session.confirmed_revision, revision)
        self.assertEqual(self.env["office.document.request"].search_count([]), before_requests)

    def test_m1_delivery_exception_marks_session_failed_without_download(self):
        session, _thread, _message, _source, _target, revision = self._session()
        request_model = self.env["office.document.request"]
        observed_states = []

        def fail_render(*_args, **_kwargs):
            session.invalidate_recordset(["state", "revision"])
            observed_states.append((session.state, session.revision))
            raise RuntimeError("synthetic handoff failure")

        before_requests = self.env["office.document.request"].search_count([])
        with self._approved_synthetic_environment(), patch.object(
            type(request_model), "_inspect_chat_attachment", return_value={"template_sha256": "f" * 64}
        ), patch.object(
            type(request_model), "_render_request_sync", side_effect=fail_render
        ):
            result = render_confirmed_mapping(self.env, session.id, revision)

        self.assertEqual(observed_states, [("rendering", revision + 1)])
        session.invalidate_recordset()
        self.assertEqual(session.state, "failed")
        self.assertEqual(result["state"], "failed")
        self.assertEqual(result["error_code"], "office_render_failed")
        self.assertFalse(result["output_attachment_id"])
        self.assertNotIn("download_url", result)
        self.assertEqual(self.env["office.document.request"].search_count([]), before_requests)

    def test_m1_committed_output_is_not_requeried_from_parent_snapshot(self):
        """M1 commits on another cursor; this transaction may not see its output row."""
        session, _thread, _message, _source, _target, revision = self._session()
        request_model = self.env["office.document.request"]
        newly_committed_attachment_id = 2_000_000_001
        with self._approved_synthetic_environment(), patch.object(
            type(request_model),
            "_inspect_chat_attachment",
            return_value={"template_sha256": "c" * 64},
        ), patch.object(
            type(request_model),
            "_render_request_sync",
            return_value={
                "state": "generated",
                "output_attachment_id": newly_committed_attachment_id,
            },
        ):
            result = render_confirmed_mapping(self.env, session.id, revision)

        session.invalidate_recordset()
        self.assertEqual(result["state"], "completed")
        self.assertEqual(result["output_attachment_id"], newly_committed_attachment_id)
        self.assertEqual(
            result["download_url"],
            f"/web/content/{newly_committed_attachment_id}?download=true",
        )
        self.assertEqual(session.state, "completed")

    def test_completed_card_reload_restores_verified_download_link(self):
        session, _thread, message, source, _target, confirmed_revision = self._session()
        request_uuid = _stable_request_uuid(self.env, session)
        digest = "d" * 64
        with _internal_mutation():
            request = self.env["office.document.request"].create(
                {
                    "request_uuid": request_uuid,
                    "owner_id": self.env.uid,
                    "thread_id": session.thread_id.id,
                    "input_message_id": message.id,
                    "source_attachment_id": source.id,
                    "input_sha256": digest,
                }
            )
            output = self.env["ir.attachment"].create(
                {
                    "name": "m2-005-reload-" + uuid4().hex + ".xlsx",
                    "type": "binary",
                    "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "raw": b"synthetic-completed-output",
                    "public": False,
                    "res_model": request._name,
                    "res_id": request.id,
                }
            )
            request.write({"state": "validating"})
            request.write({"state": "processing"})
            request.write(
                {"state": "generated", "output_attachment_id": output.id, "output_sha256": digest}
            )
        session._transition_from_service("rendering", confirmed_revision)
        session.invalidate_recordset(["revision"])
        session._transition_from_service("completed", session.revision)

        context = get_mapping_card_context(self.env, session.id, confirmed_revision)

        self.assertEqual(context["state"], "completed")
        self.assertTrue(context["stale"])
        self.assertEqual(context["download_url"], f"/web/content/{output.id}?download=true")
