import base64
import hashlib
import json
from io import BytesIO
import re
from unittest.mock import patch
from uuid import uuid4

from openpyxl import Workbook, load_workbook
from openpyxl.styles import PatternFill
from odoo.exceptions import UserError
from odoo.tests import TransactionCase

from odoo.addons.office_engine_odoo.models.office_document_request import _internal_mutation
from office_core import ResourceBudget, expand_repeat_rows, inspect_document, render_candidate
from office_verify import VerificationBudget, VerificationPolicy, verify_output

from ..services.mapping_service import (
    confirm_mapping,
    create_session,
    get_mapping_card_context,
    save_mapping_edits,
    set_mapping_context,
)
from ..services.render_bridge import _stable_request_uuid, render_confirmed_mapping, render_preview


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
        worksheet["B1"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
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
        with self._synthetic_context():
            preview = render_preview(self.env, session.id, session.revision)
        session.invalidate_recordset()
        confirm_mapping(self.env, session.id, preview["revision"])
        return session, thread, message, attachment, target, preview["revision"]

    def _synthetic_context(self):
        # Odoo TransactionCase forbids committing its shared test cursor. The
        # RenderBridge tests mock the independent M1 worker, so model the
        # checkpoint boundary without committing test fixtures.
        return patch.object(self.env.cr, "commit")

    def test_preview_filename_uses_any_target_model_display_name(self):
        session, _thread, _message, _source, target, _revision = self._session()
        safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", target.display_name).strip("_")[:48]

        self.assertIn(safe_name, session.preview_attachment_id.name)
        self.assertTrue(session.preview_attachment_id.name.endswith(".xlsx"))

    def test_confirmed_revision_retrieves_fresh_data_and_calls_m1_idempotently(self):
        session, thread, message, source, target, revision = self._session()
        request_model = self.env["office.document.request"]
        source_hash = session.template_fingerprint
        calls = []

        def fake_m1(
            _request_recordset, request_uuid, source_attachment_id, plan, thread_id,
            message_id, version_binding=None,
        ):
            calls.append((request_uuid, plan, source_attachment_id, thread_id, message_id))
            from odoo.addons.office_engine_m2.services.workbook_version_service import (
                M1_VALIDATOR_POLICY_VERSION,
            )
            from odoo.addons.office_engine_odoo.models.office_document_request import _resource_budget

            request = request_model.search([("request_uuid", "=", request_uuid)], limit=1)
            if not request:
                candidate = render_candidate(
                    source.raw,
                    source.name,
                    source.mimetype,
                    plan,
                    _resource_budget(),
                )
                report = candidate.verification["office_verify"]
                output_bytes = candidate.content
                output_hash = candidate.candidate_sha256
                report_digest = hashlib.sha256(
                    json.dumps(
                        {"policy": M1_VALIDATOR_POLICY_VERSION, "report": report},
                        sort_keys=True,
                        separators=(",", ":"),
                        ensure_ascii=False,
                    ).encode("utf-8")
                ).hexdigest()
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
                            "output_sha256": output_hash,
                            "state": "generated",
                            "m1_validation_status": "VERIFIED",
                            "m1_validator_policy_version": M1_VALIDATOR_POLICY_VERSION,
                            "m1_validation_report_id": report_digest,
                            "m1_validation_report_sha256": report_digest,
                            "m1_validation_input_sha256": source_hash,
                            "m1_validation_output_sha256": output_hash,
                            "m1_validation_completed_at": "2026-11-06 09:00:00",
                            "m1_version_session_id": version_binding["session_id"],
                            "m1_version_session_revision": version_binding["session_revision"],
                            "m1_version_proposal_revision": version_binding["proposal_revision"],
                        }
                    )
            else:
                output = request.output_attachment_id
            delivery_message_id = request_model._ensure_output_delivery_message(request.id)
            return {
                "state": "generated",
                "output_attachment_id": output.id,
                "filename": output.name,
                "mimetype": output.mimetype,
                "delivery_message_id": delivery_message_id,
            }

        with self._synthetic_context(), patch.object(
            type(request_model), "_render_request_sync", autospec=True, side_effect=fake_m1
        ):
            result = render_confirmed_mapping(self.env, session.id, revision)
            session.invalidate_recordset()
            duplicate = render_confirmed_mapping(self.env, session.id, revision)

        self.assertEqual(result["state"], "completed")
        self.assertEqual(session.state, "completed")
        self.assertTrue(result["download_url"].endswith("?download=true"))
        self.assertEqual(result["output_attachment_id"], duplicate["output_attachment_id"])
        self.assertEqual(result["workbook_version_state"], "finalized")
        self.assertEqual(duplicate["workbook_version_id"], result["workbook_version_id"])
        self.assertEqual(session.current_version_id.id, result["workbook_version_id"])
        version = self.env["office.workbook.version"].browse(result["workbook_version_id"])
        self.assertEqual(version.delivery_state, "delivered")
        self.assertEqual(version.final_attachment_id.id, result["output_attachment_id"])
        self.assertEqual(version.final_message_id.id, result["delivery_message_id"])
        self.assertEqual(result["filename"], duplicate["filename"])
        self.assertEqual(result["mimetype"], duplicate["mimetype"])
        self.assertTrue(duplicate["delivery_message_id"])
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
        worksheet["A8"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
        worksheet["A9"] = "Second detail placeholder"
        worksheet["A9"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
        worksheet["D10"] = "=SUM(D8:D9)"
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
            {"name": f"Detail {index}", "parent_id": target.id, "company_id": self.env.company.id}
            for index in range(1, 4)
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
                for index in range(3)
            ],
        ]
        group = {
            "group_id": "order_lines",
            "collection_field": "child_ids",
            "relation_model": "res.partner",
            "row_count": 3,
            "target_rows": [
                {
                    "row_index": index,
                    "targets": [{"column_id": "name", "element_id": f"xlsx:Sheet!A{index + 8}"}],
                }
                for index in range(3)
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
                for index in range(3)
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
        with self._synthetic_context():
            preview = render_preview(self.env, session.id, session.revision)
        session.invalidate_recordset()
        confirmed = confirm_mapping(self.env, session.id, preview["revision"])
        request_model = self.env["office.document.request"]
        actual_reports = []

        def fake_m1(
            _request_recordset,
            _request_uuid,
            _attachment_id,
            plan,
            _thread_id,
            _message_id,
            preprocessing=None,
            version_binding=None,
        ):
            self.assertEqual(version_binding["session_id"], session.id)
            self.assertEqual(version_binding["session_revision"], session.revision)
            self.assertEqual(version_binding["proposal_revision"], session.proposal_revision)
            render_source = (
                expand_repeat_rows(source_bytes, preprocessing, resource_budget).content
                if preprocessing
                else source_bytes
            )
            candidate = render_candidate(render_source, source.name, mime, plan, resource_budget)
            report = verify_output(
                render_source,
                candidate.content,
                source.name,
                mime,
                plan,
                VerificationPolicy(enabled_formats=("xlsx",), require_styles=True),
                verify_budget,
            )
            actual_reports.append((report, candidate.content, plan, preprocessing))
            return {
                "state": "generated",
                "output_attachment_id": 2_000_000_021,
                "delivery_message_id": 2_000_000_022,
            }

        with self._synthetic_context(), patch.object(
            type(request_model),
            "_inspect_chat_attachment",
            return_value={"template_sha256": inspection.template_sha256},
        ), patch.object(
            type(request_model), "_render_request_sync", autospec=True, side_effect=fake_m1
        ) as render_call:
            result = render_confirmed_mapping(self.env, session.id, confirmed["revision"])

        plan = actual_reports[0][2]
        preprocessing = actual_reports[0][3]
        self.assertEqual(result["state"], "completed")
        self.assertEqual(
            preprocessing,
            {
                "action": "insert_repeat_rows",
                "sheet": "Sheet",
                "start_row": 8,
                "record_count": 3,
                "columns": {"A": "name"},
            },
        )
        self.assertEqual(
            [(write["element_id"], write["value"]["data"]) for write in plan["writes"]],
            [
                ("xlsx:Sheet!B1", target.name),
                ("xlsx:Sheet!A8", children[0].name),
                ("xlsx:Sheet!A9", children[1].name),
                ("xlsx:Sheet!A10", children[2].name),
            ],
        )
        self.assertEqual(actual_reports[0][0].status, "PASS")
        self.assertEqual(actual_reports[0][0].checked_targets, 4)
        rendered = load_workbook(BytesIO(actual_reports[0][1]), data_only=False)
        try:
            self.assertEqual(rendered["Sheet"]["B1"].value, target.name)
            self.assertEqual(rendered["Sheet"]["A8"].value, children[0].name)
            self.assertEqual(rendered["Sheet"]["A9"].value, children[1].name)
            self.assertEqual(rendered["Sheet"]["A10"].value, children[2].name)
            self.assertEqual(rendered["Sheet"]["C1"].value, "=1+1")
            self.assertEqual(rendered["Sheet"]["D11"].value, "=SUM(D8:D10)")
        finally:
            rendered.close()

    def test_m1_failure_preserves_confirmation_state_and_returns_no_download(self):
        session, _thread, _message, _source, _target, revision = self._session()
        request_model = self.env["office.document.request"]
        with self._synthetic_context(), patch.object(
            type(request_model),
            "_render_request_sync",
            return_value={"state": "failed", "error_code": "OFFICE_INTEGRITY_FAILED", "output_attachment_id": False},
        ):
            result = render_confirmed_mapping(self.env, session.id, revision)

        session.invalidate_recordset()
        self.assertEqual(result["state"], "failed")
        self.assertEqual(result["session_state"], "confirmation_required")
        self.assertFalse(result["output_attachment_id"])
        self.assertNotIn("download_url", result)
        self.assertEqual(session.state, "confirmation_required")
        self.assertTrue(session.preview_attachment_id)

    def test_retriever_failure_stops_before_m1_and_does_not_complete_session(self):
        session, _thread, _message, _source, _target, revision = self._session()
        request_model = self.env["office.document.request"]
        retriever = self.env.ref("llm_tool.llm_tool_odoo_record_retriever")
        before_requests = self.env["office.document.request"].search_count([])
        with self._synthetic_context(), patch.object(
            type(retriever), "execute", autospec=True, side_effect=TimeoutError("synthetic timeout")
        ), patch.object(type(request_model), "_render_request_sync") as render_call:
            with self.assertRaises(UserError):
                render_confirmed_mapping(self.env, session.id, revision)

        session.invalidate_recordset()
        self.assertEqual(render_call.call_count, 0)
        self.assertEqual(session.state, "confirmation_required")
        self.assertEqual(session.confirmed_revision, 0)
        self.assertEqual(self.env["office.document.request"].search_count([]), before_requests)

    def test_m1_delivery_exception_returns_retryable_failure_and_preserves_preview(self):
        session, _thread, _message, _source, _target, revision = self._session()
        request_model = self.env["office.document.request"]
        observed_states = []

        def fail_render(*_args, **_kwargs):
            session.invalidate_recordset(["state", "revision"])
            observed_states.append((session.state, session.revision))
            raise RuntimeError("synthetic handoff failure")

        before_requests = self.env["office.document.request"].search_count([])
        with self._synthetic_context(), patch.object(
            type(request_model), "_render_request_sync", side_effect=fail_render
        ):
            result = render_confirmed_mapping(self.env, session.id, revision)

        self.assertEqual(observed_states, [("generating", revision + 2)])
        session.invalidate_recordset()
        self.assertEqual(result["state"], "failed")
        self.assertEqual(result["session_state"], "confirmation_required")
        self.assertEqual(session.state, "confirmation_required")
        self.assertTrue(session.preview_attachment_id)
        self.assertEqual(self.env["office.document.request"].search_count([]), before_requests)

    def test_failed_finalize_can_retry_with_a_new_idempotency_key(self):
        session, _thread, _message, _source, _target, revision = self._session()
        request_model = self.env["office.document.request"]
        summary = {
            "template_sha256": session.template_fingerprint,
            "format": "xlsx",
            "preprocessing": None,
        }
        results = [
            {"state": "failed", "error_code": "OFFICE_ENGINE_FAILED", "message": "temporary failure"},
            {
                "state": "generated",
                "output_attachment_id": 2_000_000_003,
                "filename": "office-output-retry.xlsx",
                "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "delivery_message_id": 2_000_000_004,
            },
        ]
        with self._synthetic_context(), patch(
            "odoo.addons.office_engine_m2.services.render_bridge._compile_plan",
            return_value=({}, session.preview_data_fingerprint, summary),
        ), patch.object(
            type(request_model), "_render_request_sync", autospec=True, side_effect=results
        ) as render_call:
            first = render_confirmed_mapping(self.env, session.id, revision)
            session.invalidate_recordset(["revision", "state"])
            second = render_confirmed_mapping(self.env, session.id, session.revision)

        self.assertEqual(first["state"], "failed")
        self.assertEqual(first["session_state"], "confirmation_required")
        self.assertEqual(second["state"], "completed")
        self.assertEqual(session.state, "completed")
        self.assertEqual(render_call.call_count, 2)
        self.assertNotEqual(
            render_call.call_args_list[0].args[1],
            render_call.call_args_list[1].args[1],
        )

    def test_generated_output_without_chat_message_retries_same_request(self):
        session, _thread, _message, _source, _target, revision = self._session()
        request_model = self.env["office.document.request"]
        summary = {
            "template_sha256": session.template_fingerprint,
            "format": "xlsx",
            "preprocessing": None,
        }
        results = [
            {
                "state": "generated",
                "output_attachment_id": 2_000_000_031,
                "filename": "office-output-pending.xlsx",
                "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "delivery_message_id": False,
            },
            {
                "state": "generated",
                "output_attachment_id": 2_000_000_031,
                "filename": "office-output-pending.xlsx",
                "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "delivery_message_id": 2_000_000_032,
            },
        ]
        rendered_request_uuids = []

        def fake_m1(_request_model, request_uuid, *_args, **_kwargs):
            rendered_request_uuids.append(request_uuid)
            return {**results[len(rendered_request_uuids) - 1], "request_uuid": request_uuid}

        with self._synthetic_context(), patch(
            "odoo.addons.office_engine_m2.services.render_bridge._compile_plan",
            return_value=({}, session.preview_data_fingerprint, summary),
        ), patch.object(
            type(request_model), "_render_request_sync", autospec=True, side_effect=fake_m1
        ) as render_call:
            first = render_confirmed_mapping(self.env, session.id, revision)
            session.invalidate_recordset(["state", "revision", "final_request_uuid"])
            self.assertEqual(session.state, "confirmation_required")
            self.assertEqual(session.final_request_uuid, rendered_request_uuids[0])
            retry_revision = session.revision
            confirm_mapping(self.env, session.id, retry_revision)
            second = render_confirmed_mapping(
                self.env, session.id, retry_revision
            )

        session.invalidate_recordset()
        self.assertEqual(first["state"], "failed")
        self.assertEqual(first["artifact_state"], "generated")
        self.assertEqual(first["delivery_state"], "pending")
        self.assertFalse(first["output_attachment_id"])
        self.assertEqual(session.state, "completed")
        self.assertEqual(session.final_request_uuid, rendered_request_uuids[0])
        self.assertEqual(second["state"], "completed")
        self.assertEqual(second["request_uuid"], rendered_request_uuids[0])
        self.assertEqual(second["delivery_message_id"], 2_000_000_032)
        self.assertEqual(render_call.call_count, 2)
        self.assertEqual(
            rendered_request_uuids[0],
            rendered_request_uuids[1],
        )

    def test_completed_finalize_uses_persisted_request_identity(self):
        session, _thread, message, source, _target, revision = self._session()
        marked = session._mark_confirmed_from_service(revision)
        session.invalidate_recordset(["revision", "state"])
        request_uuid = str(uuid4())
        digest = "e" * 64
        request_model = self.env["office.document.request"]
        with _internal_mutation():
            request = request_model.create(
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
                    "name": "office-output-persisted-identity.xlsx",
                    "type": "binary",
                    "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "raw": b"verified persisted request output",
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
        session._transition_from_service("generating", marked["revision"])
        session.invalidate_recordset(["revision", "state"])
        session._transition_from_service(
            "completed", session.revision, final_request_uuid=request_uuid
        )

        result = render_confirmed_mapping(self.env, session.id, revision)

        self.assertEqual(result["state"], "completed")
        self.assertEqual(result["request_uuid"], request_uuid)
        self.assertEqual(result["output_attachment_id"], output.id)
        self.assertTrue(result["delivery_message_id"])
        delivered = self.env["mail.message"].browse(result["delivery_message_id"])
        self.assertEqual(delivered.model, session.thread_id._name)
        self.assertEqual(delivered.res_id, session.thread_id.id)
        self.assertIn(output, delivered.attachment_ids)

    def test_m1_finalize_commits_generating_checkpoint_before_subcursor_handoff_and_registers_v1(self):
        session, thread, message, source, _target, revision = self._session()
        events = []
        generated_output = source.raw

        def fake_commit():
            events.append("checkpoint_commit" if not events else "post_worker_snapshot_rebase")

        def fake_m1(
            request_model, request_uuid, source_attachment_id, _plan, thread_id,
            input_message_id, version_binding=None, **_kwargs,
        ):
            events.append("subcursor_handoff")
            self.assertEqual(events, ["checkpoint_commit", "subcursor_handoff"])
            self.assertEqual(session.state, "generating")
            self.assertEqual(version_binding["session_revision"], session.revision)
            from odoo.addons.office_engine_odoo.models.office_document_request import (
                M1_VALIDATOR_POLICY_VERSION,
                _internal_mutation,
            )

            input_sha = hashlib.sha256(source.raw or b"").hexdigest()
            output_sha = hashlib.sha256(generated_output).hexdigest()
            report_digest = hashlib.sha256((input_sha + output_sha + request_uuid).encode()).hexdigest()
            with _internal_mutation():
                request = request_model.create({
                    "request_uuid": request_uuid,
                    "owner_id": self.env.uid,
                    "thread_id": thread_id,
                    "input_message_id": input_message_id,
                    "source_attachment_id": source_attachment_id,
                    "input_sha256": input_sha,
                })
                request.write({"state": "validating"})
                request.write({"state": "processing"})
                output = self.env["ir.attachment"].create({
                    "name": "synthetic-m1-v1.xlsx",
                    "type": "binary",
                    "raw": generated_output,
                    "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "company_id": session.company_id.id,
                    "public": False,
                    "res_model": request._name,
                    "res_id": request.id,
                })
                request.write({
                    "state": "generated",
                    "output_attachment_id": output.id,
                    "output_sha256": output_sha,
                    "m1_validation_status": "VERIFIED",
                    "m1_validator_policy_version": M1_VALIDATOR_POLICY_VERSION,
                    "m1_validation_report_id": report_digest,
                    "m1_validation_report_sha256": report_digest,
                    "m1_validation_input_sha256": input_sha,
                    "m1_validation_output_sha256": output_sha,
                    "m1_validation_completed_at": "2026-11-09 00:00:00",
                    "m1_version_session_id": session.id,
                    "m1_version_session_revision": version_binding["session_revision"],
                    "m1_version_proposal_revision": version_binding["proposal_revision"],
                })
            delivery_message_id = request_model._ensure_output_delivery_message(request.id)
            return {
                "state": "generated", "request_uuid": request_uuid,
                "output_attachment_id": output.id, "filename": output.name,
                "mimetype": output.mimetype, "delivery_message_id": delivery_message_id,
            }

        with patch.object(self.env.cr, "commit", side_effect=fake_commit):
            with patch.object(type(self.env["office.document.request"]), "_render_request_sync", fake_m1):
                result = render_confirmed_mapping(self.env, session.id, revision)

        session.invalidate_recordset()
        self.assertEqual(
            events,
            ["checkpoint_commit", "subcursor_handoff", "post_worker_snapshot_rebase"],
        )
        self.assertEqual(result["state"], "completed", result)
        self.assertEqual(result["workbook_version_state"], "finalized", result)
        self.assertTrue(result["workbook_version_id"])
        self.assertEqual(session.current_version_id.id, result["workbook_version_id"])
        self.assertEqual(session.last_valid_version_id.id, result["workbook_version_id"])
        self.assertEqual(session.document_revision, 1)
        self.assertEqual(session.current_version_id.version_no, 1)
        self.assertEqual(session.current_version_id.validation_result, "VERIFIED")

    def test_m1_committed_output_is_not_requeried_from_parent_snapshot(self):
        """M1 commits on another cursor; this transaction may not see its output row."""
        session, _thread, _message, _source, _target, revision = self._session()
        request_model = self.env["office.document.request"]
        newly_committed_attachment_id = 2_000_000_001
        with self._synthetic_context(), patch.object(
            type(request_model),
            "_render_request_sync",
            return_value={
                "state": "generated",
                "output_attachment_id": newly_committed_attachment_id,
                "filename": "office-output-test.xlsx",
                "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "delivery_message_id": 2_000_000_002,
            },
        ):
            result = render_confirmed_mapping(self.env, session.id, revision)

        session.invalidate_recordset()
        self.assertEqual(result["state"], "completed")
        self.assertEqual(result["output_attachment_id"], newly_committed_attachment_id)
        self.assertEqual(result["filename"], "office-output-test.xlsx")
        self.assertEqual(
            result["mimetype"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertEqual(result["delivery_message_id"], 2_000_000_002)
        self.assertEqual(
            result["download_url"],
            f"/web/content/{newly_committed_attachment_id}?download=true",
        )
        self.assertEqual(session.state, "completed")

    def test_completed_card_reload_restores_verified_download_link(self):
        session, _thread, message, source, _target, confirmed_revision = self._session()
        confirmed = session._mark_confirmed_from_service(confirmed_revision)
        session.invalidate_recordset(["revision", "state"])
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
        session._transition_from_service("generating", confirmed["revision"])
        session.invalidate_recordset(["revision"])
        session._transition_from_service("completed", session.revision)

        context = get_mapping_card_context(self.env, session.id, confirmed_revision)

        self.assertEqual(context["state"], "completed")
        self.assertTrue(context["stale"])
        self.assertEqual(context["download_url"], f"/web/content/{output.id}?download=true")
