"""Native Odoo-LLM Office tool binding and safe message serialization tests."""

import json
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile

from openpyxl import Workbook, load_workbook
from openpyxl.styles import PatternFill
from docx import Document
from lxml import etree
from odoo import tools
from odoo.exceptions import AccessError, UserError
from odoo.addons.llm_assistant.models.llm_thread import LLMThread as AssistantThread
from odoo.addons.llm_thread.controllers.main import LLMThreadController
from odoo.tests import TransactionCase
from office_core import inspect_document
from office_mapping_verify import MappingParseError
from odoo.addons.office_engine_odoo.models.office_document_request import _resource_budget

from ..services.chat_entrypoint import (
    _field_candidates,
    _repeat_row_collection_candidates,
    _selected_record_context,
    _template_context,
)
from ..services.mapping_service import create_session, set_mapping_context
from ..services.render_bridge import _compile_plan
from ..models.office_mapping_tools import (
    _is_explicit_finalize_confirmation,
    _merge_mapping_patch,
    _normalize_merged_target_aliases,
)


XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _xlsx():
    workbook = Workbook()
    workbook.active["A1"] = "Customer"
    workbook.active["B1"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


def _docx():
    document = Document()
    document.add_paragraph("Contact: placeholder")
    table = document.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "Reference"
    table.cell(0, 1).text = "placeholder"
    output = BytesIO()
    document.save(output)
    source = ZipFile(BytesIO(output.getvalue()), "r")
    clean = BytesIO()
    type_ns = "{http://schemas.openxmlformats.org/package/2006/content-types}"
    with ZipFile(clean, "w", ZIP_DEFLATED) as destination:
        for item in source.infolist():
            name = item.filename
            if name.startswith("customXml/") or name in {"word/stylesWithEffects.xml", "docProps/thumbnail.jpeg"}:
                continue
            raw = source.read(name)
            if name in {"word/_rels/document.xml.rels", "_rels/.rels"}:
                root = etree.fromstring(raw)
                for relationship in list(root):
                    relation_type = relationship.get("Type", "")
                    if relation_type.endswith("/customXml") or relation_type.endswith("/stylesWithEffects"):
                        root.remove(relationship)
                    elif name == "_rels/.rels" and relation_type.endswith("/thumbnail"):
                        root.remove(relationship)
                raw = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
            elif name == "[Content_Types].xml":
                root = etree.fromstring(raw)
                for node in list(root):
                    if node.get("PartName", "") in {"/customXml/itemProps1.xml", "/word/stylesWithEffects.xml"}:
                        root.remove(node)
                    elif node.tag == type_ns + "Default" and node.get("Extension") == "jpeg":
                        root.remove(node)
                raw = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
            destination.writestr(name, raw)
    source.close()
    return clean.getvalue()


def _repeat_rows_xlsx():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Data"
    sheet["A1"] = "Parent"
    sheet["B1"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
    sheet["A3"] = "Record"
    sheet["B3"] = "Name"
    sheet["B4"] = "example value"
    sheet["B4"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
    sheet["B5"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
    sheet["C4"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
    sheet["C5"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
    sheet["D4"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
    sheet["D5"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
    sheet["A6"] = "Total"
    sheet["B6"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
    sheet["C6"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
    sheet["D6"] = "Total"
    sheet["E6"] = "=SUM(E4:E5)"
    sheet["F6"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


def _no_summary_repeat_rows_xlsx():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Import"
    sheet["A1"] = "Record"
    sheet["B1"] = "Email"
    sheet["C1"] = "Unstyled email"
    sheet["A2"] = "example"
    for column in "A":
        sheet[f"{column}2"].fill = PatternFill(fill_type="solid", fgColor="D9EAF7")
    sheet["B2"].number_format = "@"
    # Keep an explicit, unstyled blank cell in the prototype row. Real import
    # sheets commonly contain these cells, and repeat-row writes must verify.
    sheet["B2"] = ""
    sheet["C2"] = ""
    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


def _formula_repeat_rows_xlsx():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Data"
    sheet["A1"] = "Parent"
    sheet["B1"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
    sheet["A3"] = "Record"
    sheet["B3"] = "Name"
    sheet["C3"] = "Weight"
    sheet["B4"] = "example value"
    sheet["B4"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
    sheet["B5"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
    sheet["C4"] = "=B4*2"
    sheet["C5"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
    sheet["A6"] = "Total"
    sheet["C6"] = "=SUM(C4:C5)"
    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


def _zero_numeric_repeat_rows_xlsx():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Data"
    sheet["A1"] = "Parent"
    sheet["B1"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
    sheet["A3"] = "Record"
    sheet["B3"] = "Name"
    sheet["B4"] = "example value"
    sheet["B4"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
    sheet["B5"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
    sheet["C3"] = "Color index"
    sheet["C4"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
    sheet["C5"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
    sheet["A6"] = "Total"
    sheet["C6"] = "=SUM(C4:C5)"
    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


class TestNativeOfficeChatIntegration(TransactionCase):
    def test_mapping_patch_rejects_same_target_mapping_and_clarification(self):
        patch_data = {
            "schema_version": "m2.mapping-proposal.v1",
            "mappings": [
                {"element_id": "xlsx:Purchase Reconciliation!B4", "literal_value": 3329.15, "value_type": "number"}
            ],
            "clarifications": [
                {
                    "element_id": "xlsx:Purchase Reconciliation!B4",
                    "reason_code": "unsupported_value",
                    "question": "Please confirm the value.",
                }
            ],
            "skipped_targets": [],
        }
        with self.assertRaisesRegex(MappingParseError, "conflicting_patch_target"):
            _merge_mapping_patch({"mappings": [], "clarifications": [], "skipped_targets": []}, patch_data)

    def test_explicit_clear_wins_over_echoed_mapping_for_same_target(self):
        current = {
            "schema_version": "m2.mapping-proposal.v1",
            "mappings": [
                {"element_id": "xlsx:Data!B3", "source_field": "partner_id.name", "value_type": "string"},
                {"element_id": "xlsx:Data!F18", "source_field": "client_order_ref", "value_type": "string"},
            ],
            "clarifications": [],
            "skipped_targets": [],
        }
        patch_data = {
            "schema_version": "m2.mapping-proposal.v1",
            "mappings": [
                {"element_id": "xlsx:Data!F18", "source_field": "client_order_ref", "value_type": "string"}
            ],
            "clarifications": [],
            "skipped_targets": [],
            "clear_targets": ["xlsx:Data!F18"],
        }

        merged = _merge_mapping_patch(current, patch_data)

        self.assertEqual(
            merged["mappings"],
            [{"element_id": "xlsx:Data!B3", "source_field": "partner_id.name", "value_type": "string"}],
        )
        self.assertEqual(merged["clear_targets"], ["xlsx:Data!F18"])

    def test_column_format_patch_replaces_older_cell_patches_in_that_column(self):
        current = {
            "schema_version": "m2.mapping-proposal.v1",
            "mappings": [],
            "clarifications": [],
            "skipped_targets": [],
            "format_patches": [
                {"element_id": "xlsx:Import!I2", "number_format": "0.00"},
                {"element_id": "xlsx:Import!I3", "number_format": "0.00"},
                {"element_id": "xlsx:Import!H2", "number_format": "yyyy-mm-dd"},
            ],
        }
        patch_data = {
            "schema_version": "m2.mapping-proposal.v1",
            "mappings": [],
            "clarifications": [],
            "skipped_targets": [],
            "format_patches": [
                {"sheet": "Import", "column": "I", "number_format": "0.0"}
            ],
        }

        merged = _merge_mapping_patch(current, patch_data)

        self.assertEqual(
            merged["format_patches"],
            [
                {"element_id": "xlsx:Import!H2", "number_format": "yyyy-mm-dd"},
                {"sheet": "Import", "column": "I", "number_format": "0.0"},
            ],
        )

    def test_numeric_literal_mapping_writes_computed_value_to_preview(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Purchase Reconciliation"
        sheet["A1"] = "Adjusted amount (EUR)"
        sheet["B1"].number_format = "0.00"
        output = BytesIO()
        workbook.save(output)
        workbook.close()

        thread = self.env["llm.thread"].create(
            {
                "name": "Numeric literal mapping " + uuid4().hex,
                "provider_id": self.provider.id,
                "model_id": self.model.id,
            }
        )
        attachment = self.env["ir.attachment"].create(
            {
                "name": "numeric-literal.xlsx",
                "type": "binary",
                "mimetype": XLSX_MIME,
                "raw": output.getvalue(),
                "company_id": self.env.company.id,
            }
        )
        user_message = thread.message_post(
            body="Fill the adjusted amount",
            llm_role="user",
            author_id=self.env.user.partner_id.id,
            attachment_ids=[attachment.id],
        )
        retriever_result = thread.message_post(
            body="Authorized record lookup",
            llm_role="tool",
            body_json={
                "type": "tool_execution",
                "tool_call_id": "numeric-literal-retriever-" + uuid4().hex,
                "tool_call": {"function": {"name": "odoo_record_retriever", "arguments": "{}"}},
                "tool_name": "odoo_record_retriever",
                "arguments": {"model": "res.partner", "domain": [["id", "=", self.env.user.partner_id.id]], "fields": ["id", "name"], "limit": 1},
                "status": "completed",
                "result": [{"id": self.env.user.partner_id.id, "name": self.env.user.partner_id.name}],
            },
        )
        tool = self.env["office.mapping.tool"].with_context(message=retriever_result)
        context = tool.office_prepare_context("res.partner", self.env.user.partner_id.id)
        session = self.env["office.mapping.session"].browse(context["session_id"])
        result = tool.office_save_mapping_preview(
            session.id,
            session.revision,
            {
                "schema_version": "m2.mapping-proposal.v1",
                "mappings": [
                    {"element_id": "xlsx:Purchase Reconciliation!B1", "literal_value": 3329.15, "value_type": "number"}
                ],
                "clarifications": [],
                "skipped_targets": [],
            },
        )
        self.assertEqual(result["status"], "preview_ready", result)
        rendered = load_workbook(BytesIO(session.preview_attachment_id.raw), data_only=False)
        try:
            self.assertEqual(rendered["Purchase Reconciliation"]["B1"].value, 3329.15)
            self.assertEqual(rendered["Purchase Reconciliation"]["A1"].value, "Adjusted amount (EUR)")
        finally:
            rendered.close()

    def test_sse_client_disconnect_does_not_cancel_native_tool_loop(self):
        """The server must finish tool/model work even if the SSE reader closes."""
        events = []

        def generate(*args, **kwargs):
            events.append("assistant_tool_call")
            yield {"type": "message_create", "message": {"id": 1}}
            events.append("tool_result_processed")
            yield {"type": "message_update", "message": {"id": 2}}
            events.append("assistant_followup_processed")
            yield {"type": "message_create", "message": {"id": 3}}

        thread = SimpleNamespace(exists=lambda: True, generate=generate)
        model = SimpleNamespace(browse=lambda _thread_id: thread)
        class FakeEnv:
            uid = self.env.uid
            context = dict(self.env.context)

            def __getitem__(self, _name):
                return model

        env = FakeEnv()
        cursor = SimpleNamespace()

        class CursorContext:
            def __enter__(self):
                return cursor

            def __exit__(self, *_args):
                return False

        cursor_context = CursorContext()
        registry = SimpleNamespace(cursor=lambda: cursor_context)

        with (
            patch("odoo.addons.llm_thread.controllers.main.Registry", return_value=registry),
            patch("odoo.addons.llm_thread.controllers.main.api.Environment", return_value=env),
        ):
            response = LLMThreadController._llm_thread_generate(
                "test_db", env, 4242, None
            )
            next(response)
            response.close()

        self.assertEqual(
            events,
            ["assistant_tool_call", "tool_result_processed", "assistant_followup_processed"],
        )

    def test_native_docx_context_and_mapping_preview_use_generic_paragraph_targets(self):
        thread = self.env["llm.thread"].create(
            {
                "name": "Native DOCX thread " + uuid4().hex,
                "provider_id": self.provider.id,
                "model_id": self.model.id,
            }
        )
        target = self.env["res.partner"].create(
            {"name": "DOCX target " + uuid4().hex, "company_id": self.env.company.id}
        )
        attachment = self.env["ir.attachment"].create(
            {
                "name": "native-office-" + uuid4().hex + ".docx",
                "type": "binary",
                "mimetype": DOCX_MIME,
                "raw": _docx(),
                "company_id": self.env.company.id,
            }
        )
        thread.message_post(
            body="Fill the contact paragraph",
            llm_role="user",
            author_id=self.env.user.partner_id.id,
            attachment_ids=[attachment.id],
        )
        retriever_result = thread.message_post(
            body="Retriever result",
            llm_role="tool",
            body_json={
                "type": "tool_execution",
                "tool_call_id": "docx-retriever-call",
                "tool_call": {"function": {"name": "odoo_record_retriever", "arguments": "{}"}},
                "tool_name": "odoo_record_retriever",
                "arguments": {
                    "model": "res.partner",
                    "domain": [["id", "=", target.id]],
                    "fields": ["id", "name"],
                    "limit": 1,
                },
                "status": "completed",
                "result": [{"id": target.id, "name": target.name}],
            },
        )

        tool = self.env["office.mapping.tool"].with_context(message=retriever_result)
        context = tool.office_prepare_context("res.partner", target.id)
        self.assertEqual(context["document_format"], "docx")
        self.assertIn("docx:p:1", {item["element_id"] for item in context["target_manifest"]})
        self.assertIn("docx:table:1:row:1:cell:2:p:1", {item["element_id"] for item in context["target_manifest"]})
        self.assertIn("docx_simple_paragraph_replacement", context["mapping_limits"]["supported"])
        self.assertNotIn("docx", context["mapping_limits"]["unsupported"])
        result = tool.office_save_mapping_preview(
            context["session_id"],
            context["revision"],
            {
                "schema_version": "m2.mapping-proposal.v1",
                "mappings": [
                    {
                        "element_id": "docx:p:1",
                        "source_field": "name",
                        "value_type": "string",
                    }
                ],
                "clarifications": [],
                "skipped_targets": [],
            },
        )

        self.assertEqual(result["status"], "preview_ready")
        preview = self.env["office.mapping.session"].browse(context["session_id"]).preview_attachment_id
        self.assertTrue(preview.name.endswith(".docx"))
        rendered = Document(BytesIO(preview.raw))
        self.assertEqual(rendered.paragraphs[0].text, target.name)

    def test_finalize_gate_accepts_only_exact_supported_confirmation_phrases(self):
        self.assertTrue(_is_explicit_finalize_confirmation("<p>确认并生成正式文件</p>"))
        self.assertTrue(_is_explicit_finalize_confirmation("<p>确认生成正式文件</p>"))
        self.assertFalse(_is_explicit_finalize_confirmation("请确认并生成正式文件"))
        self.assertFalse(_is_explicit_finalize_confirmation("确认并生成正式文件：S05457"))

    def test_finalize_uses_committed_output_metadata_without_reloading_stale_attachment(self):
        from types import SimpleNamespace

        thread, _source, _upload = self._office_message("Generate the confirmed workbook")
        confirmation = thread.message_post(
            body="确认并生成正式文件",
            llm_role="user",
            author_id=self.env.user.partner_id.id,
        )
        session = SimpleNamespace(
            id=701,
            thread_id=thread,
            owner_id=self.env.user,
            revision=9,
            proposal_revision=4,
            preview_proposal_revision=4,
            confirmed_revision=4,
            state="confirmation_required",
            invalidate_recordset=lambda *_args: None,
        )
        tool_model = self.env["office.mapping.tool"].with_context(message=confirmation)
        result_metadata = {
            "state": "completed",
            "output_attachment_id": 987654321,
            "filename": "office-output-verified.xlsx",
            "mimetype": XLSX_MIME,
            "download_url": "/web/content/987654321?download=true",
            "delivery_message_id": 987654322,
        }
        with (
            patch(
                "odoo.addons.office_engine_m2.models.office_mapping_tools._owned_session",
                return_value=session,
            ),
            patch(
                "odoo.addons.office_engine_m2.models.office_mapping_tools.render_confirmed_mapping",
                return_value=result_metadata,
            ),
            patch.object(
                type(self.env["ir.attachment"]),
                "browse",
                side_effect=AssertionError("Finalize must not re-read M1's committed attachment in the stale cursor"),
            ),
        ):
            result = tool_model.office_finalize(session.id, session.revision, session.proposal_revision)

        self.assertEqual(result["status"], "finalized")
        self.assertEqual(result["filename"], result_metadata["filename"])
        self.assertEqual(result["mimetype"], XLSX_MIME)
        self.assertEqual(result["attachment_id"], result_metadata["output_attachment_id"])
        self.assertEqual(result["delivery_message_id"], result_metadata["delivery_message_id"])
        self.assertTrue(result["attachment_posted_to_thread"])

    def test_finalize_replay_returns_same_committed_delivery_after_session_completed(self):
        from types import SimpleNamespace

        thread, _source, _upload = self._office_message("Generate the confirmed workbook")
        replay_message = thread.message_post(
            body="请重新显示刚生成的正式文件",
            llm_role="user",
            author_id=self.env.user.partner_id.id,
        )
        session = SimpleNamespace(
            id=702,
            thread_id=thread,
            owner_id=self.env.user,
            revision=12,
            proposal_revision=4,
            preview_proposal_revision=4,
            confirmed_revision=4,
            state="completed",
            invalidate_recordset=lambda *_args: None,
        )
        existing = {
            "state": "completed",
            "output_attachment_id": 987654321,
            "filename": "office-output-verified.xlsx",
            "mimetype": XLSX_MIME,
            "download_url": "/web/content/987654321?download=true",
            "delivery_message_id": 987654322,
        }
        with (
            patch(
                "odoo.addons.office_engine_m2.models.office_mapping_tools._owned_session",
                return_value=session,
            ),
            patch(
                "odoo.addons.office_engine_m2.models.office_mapping_tools.render_confirmed_mapping",
                return_value=existing,
            ),
        ):
            result = self.env["office.mapping.tool"].with_context(message=replay_message).office_finalize(
                session.id, expected_revision=9, proposal_revision=session.proposal_revision
            )

        self.assertEqual(result["status"], "finalized")
        self.assertEqual(result["attachment_id"], existing["output_attachment_id"])
        self.assertEqual(result["delivery_message_id"], existing["delivery_message_id"])

    def test_finalize_stale_revision_returns_structured_failure(self):
        from types import SimpleNamespace

        thread, _source, _upload = self._office_message("Generate the confirmed workbook")
        confirmation = thread.message_post(
            body="确认并生成正式文件",
            llm_role="user",
            author_id=self.env.user.partner_id.id,
        )
        session = SimpleNamespace(
            id=703,
            thread_id=thread,
            owner_id=self.env.user,
            revision=12,
            proposal_revision=5,
            preview_proposal_revision=5,
            confirmed_revision=5,
            state="confirmation_required",
            invalidate_recordset=lambda *_args: None,
        )
        with patch(
            "odoo.addons.office_engine_m2.models.office_mapping_tools._owned_session",
            return_value=session,
        ):
            result = self.env["office.mapping.tool"].with_context(message=confirmation).office_finalize(
                session.id, expected_revision=12, proposal_revision=4
            )

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error_code"], "mapping_revision_stale")

    def test_finalize_reports_generated_artifact_when_chat_delivery_is_pending(self):
        from types import SimpleNamespace

        thread, _source, _upload = self._office_message("Generate the confirmed workbook")
        confirmation = thread.message_post(
            body="确认并生成正式文件",
            llm_role="user",
            author_id=self.env.user.partner_id.id,
        )
        session = SimpleNamespace(
            id=704,
            thread_id=thread,
            owner_id=self.env.user,
            revision=15,
            proposal_revision=8,
            preview_proposal_revision=8,
            confirmed_revision=0,
            state="confirmation_required",
            invalidate_recordset=lambda *_args: None,
        )
        with (
            patch(
                "odoo.addons.office_engine_m2.models.office_mapping_tools._owned_session",
                return_value=session,
            ),
            patch(
                "odoo.addons.office_engine_m2.models.office_mapping_tools.render_confirmed_mapping",
                return_value={
                    "state": "failed",
                    "revision": 18,
                    "error_code": "office_delivery_pending",
                    "failed_stage": "chat_delivery",
                    "artifact_state": "generated",
                    "delivery_state": "pending",
                    "message": "Artifact exists; chat message publication must be retried.",
                    "output_attachment_id": False,
                },
            ),
        ):
            result = self.env["office.mapping.tool"].with_context(message=confirmation).office_finalize(
                session.id, session.revision, session.proposal_revision
            )

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["artifact_state"], "generated")
        self.assertEqual(result["delivery_state"], "pending")
        self.assertEqual(result["failed_stage"], "chat_delivery")
        self.assertFalse(result.get("attachment_id"))
        self.assertEqual(
            result["message"],
            "Artifact exists; chat message publication must be retried.",
        )

    def test_finalize_emits_committed_attachment_message_to_live_store(self):
        from types import SimpleNamespace

        thread, _source, _upload = self._office_message("Generate the confirmed workbook")
        result = {
            "status": "finalized",
            "attachment_id": 901,
            "delivery_message_id": 902,
            "attachment_posted_to_thread": True,
        }
        tool_message = SimpleNamespace(get_tool_data=lambda: {"result": result})

        def execute_tool_call(_thread, _tool_call, _assistant_message):
            yield {"type": "message_create", "message": {"id": 900}}
            return tool_message

        message_data = {"id": 902, "attachment_ids": [901]}
        store_data = {
            "mail.message": [message_data],
            "ir.attachment": [{"id": 901, "name": "office-output.xlsx", "mimetype": XLSX_MIME}],
        }
        with (
            patch.object(AssistantThread, "_execute_tool_call", execute_tool_call),
            patch.object(
                type(thread),
                "_office_committed_message_store_payload",
                return_value=(message_data, store_data),
            ),
        ):
            events = list(
                thread._execute_tool_call(
                    {"function": {"name": "office_finalize"}}, assistant_message=None
                )
            )

        self.assertEqual(events[-1]["type"], "message_create")
        self.assertEqual(events[-1]["message"], message_data)
        self.assertEqual(events[-1]["store_data"], store_data)

    def test_finalize_store_failure_updates_tool_result_and_live_message(self):
        from types import SimpleNamespace

        thread, _source, _upload = self._office_message("Generate the confirmed workbook")
        tool_data = {
            "status": "completed",
            "result": {
                "status": "finalized",
                "attachment_id": 911,
                "delivery_message_id": 912,
                "attachment_posted_to_thread": True,
            },
        }

        class ToolMessage:
            def get_tool_data(self):
                return tool_data

            def write(self, values):
                tool_data.update(values["body_json"])

            def to_store_format(self):
                return {"id": 910, "body_json": tool_data}

        tool_message = ToolMessage()

        def execute_tool_call(_thread, _tool_call, _assistant_message):
            yield {"type": "message_create", "message": {"id": 910}}
            return tool_message

        with (
            patch.object(AssistantThread, "_execute_tool_call", execute_tool_call),
            patch.object(
                type(thread),
                "_office_committed_message_store_payload",
                side_effect=UserError("attachment read failed"),
            ),
        ):
            events = list(
                thread._execute_tool_call(
                    {"function": {"name": "office_finalize"}}, assistant_message=None
                )
            )

        self.assertEqual(tool_data["status"], "error")
        self.assertEqual(tool_data["result"]["status"], "failed")
        self.assertEqual(tool_data["result"]["error_code"], "final_attachment_not_visible")
        self.assertEqual(events[-1]["type"], "message_update")
        self.assertEqual(events[-1]["message"]["body_json"]["result"]["status"], "failed")

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.provider = cls.env["llm.provider"].create(
            {"name": "Native Office test " + uuid4().hex, "service": "openai"}
        )
        cls.model = cls.env["llm.model"].create(
            {
                "name": "gpt-5.6-luna",
                "provider_id": cls.provider.id,
                "model_use": "multimodal",
            }
        )

    def _office_message(self, body, raw=None):
        thread = self.env["llm.thread"].create(
            {
                "name": "Native Office thread " + uuid4().hex,
                "provider_id": self.provider.id,
                "model_id": self.model.id,
            }
        )
        attachment = self.env["ir.attachment"].create(
            {
                "name": "native-office-" + uuid4().hex + ".xlsx",
                "type": "binary",
                "mimetype": XLSX_MIME,
                "raw": raw or _xlsx(),
                "company_id": self.env.company.id,
            }
        )
        message = thread.message_post(
            body=body,
            llm_role="user",
            author_id=self.env.user.partner_id.id,
            attachment_ids=[attachment.id],
        )
        return thread, attachment, message

    def test_prepare_context_returns_chat_recoverable_result_when_template_is_missing(self):
        thread = self.env["llm.thread"].create(
            {
                "name": "No-template Office thread " + uuid4().hex,
                "provider_id": self.provider.id,
                "model_id": self.model.id,
            }
        )
        message = thread.message_post(
            body="Please fill the workbook",
            llm_role="user",
            author_id=self.env.user.partner_id.id,
        )
        target = self.env["res.partner"].create(
            {"name": "No-template target " + uuid4().hex, "company_id": self.env.company.id}
        )

        result = self.env["office.mapping.tool"].with_context(message=message).office_prepare_context(
            "res.partner", target.id
        )

        self.assertEqual(result["status"], "needs_input")
        self.assertEqual(result["error_code"], "office_template_missing")
        self.assertIn("attach one", result["message"])
        self.assertFalse(thread._office_active_session())

    def test_prepare_context_reuses_thread_bound_session_when_followup_omits_record_identity(self):
        thread, _attachment, upload = self._office_message("Fill this workbook")
        target = self.env["res.partner"].create(
            {"name": "Bound Session target " + uuid4().hex, "company_id": self.env.company.id}
        )
        tool = self.env["office.mapping.tool"].with_context(message=upload)

        initial = tool.office_prepare_context("res.partner", target.id)
        resumed = tool.office_prepare_context("unknown", 0)

        self.assertEqual(initial["status"], "ready")
        self.assertEqual(resumed["status"], "ready")
        self.assertEqual(resumed["session_id"], initial["session_id"])
        self.assertEqual(resumed["target_model"], "res.partner")
        self.assertEqual(resumed["target_record_id"], target.id)
        self.assertEqual(resumed["revision"], initial["revision"])

    def test_assistant_html_and_markdown_render_without_literal_tags_or_fake_attachment_links(self):
        thread = self.env["llm.thread"]
        response = (
            "&lt;p&gt;预览已生成。&lt;/p&gt; "
            "&lt;ul&gt;&lt;li&gt;&lt;strong&gt;地址&lt;/strong&gt;：完整地址&lt;/li&gt;&lt;/ul&gt; "
            "&lt;div class=\"attachment-card\"&gt;"
            "&lt;a href=\"attachment://15727\"&gt;preview_S05457.xlsx&lt;/a&gt;&lt;/div&gt;"
        )

        rendered = thread._process_llm_body(response)
        plain = tools.html2plaintext(str(rendered), include_references=False)

        self.assertIn("<p>预览已生成。</p>", str(rendered))
        self.assertIn("<strong>地址</strong>", str(rendered))
        self.assertNotIn("&lt;p&gt;", str(rendered))
        self.assertNotIn("attachment://", str(rendered))
        self.assertNotIn("attachment-card", str(rendered))
        self.assertNotIn("<p>", plain)
        self.assertIn("preview_S05457.xlsx", plain)
        self.assertIn("<strong>Markdown</strong>", str(thread._process_llm_body("**Markdown**")))

    def test_preview_tool_streams_attachment_metadata_to_native_chat_store(self):
        thread, _source_attachment, _source_message = self._office_message(
            "Fill this workbook"
        )
        preview = self.env["ir.attachment"].create(
            {
                "name": "preview_store_payload.xlsx",
                "type": "binary",
                "mimetype": XLSX_MIME,
                "raw": _xlsx(),
                "company_id": self.env.company.id,
            }
        )
        tool_call = {
            "id": "call_preview_store_payload",
            "type": "function",
            "function": {
                "name": "office_save_mapping_preview",
                "arguments": "{}",
            },
        }
        preview_message = thread.message_post(
            body="已生成并通过回读验证的 Office 预览。",
            llm_role="assistant",
            author_id=False,
            attachment_ids=[preview.id],
        )
        tool_result_message = thread.message_post(
            body="Preview tool result",
            llm_role="tool",
            body_json={
                "type": "tool_execution",
                "tool_call_id": tool_call["id"],
                "tool_call": tool_call,
                "tool_name": "office_save_mapping_preview",
                "arguments": {},
                "status": "completed",
                "result": {
                    "status": "preview_ready",
                    "preview_attachment_id": preview.id,
                    "filename": preview.name,
                    "attachment_posted_to_thread": True,
                    "attachment": {
                        "id": preview.id,
                        "name": preview.name,
                        "mimetype": XLSX_MIME,
                        "message_id": preview_message.id,
                    },
                },
            },
        )
        assistant_message = thread.message_post(
            body="Preview tool call",
            llm_role="assistant",
        )

        def execute_tool(_thread, _call, _assistant_message):
            yield {
                "type": "message_create",
                "message": tool_result_message.to_store_format(),
            }
            return tool_result_message

        with patch.object(
            AssistantThread,
            "_execute_tool_call",
            autospec=True,
            side_effect=execute_tool,
        ):
            events = list(thread._execute_tool_call(tool_call, assistant_message))

        preview_events = [
            event
            for event in events
            if event.get("type") == "message_create"
            and event.get("message", {}).get("id") == preview_message.id
        ]
        self.assertEqual(len(preview_events), 1)
        event = preview_events[0]
        self.assertIn("mail.message", event["store_data"])
        self.assertIn("ir.attachment", event["store_data"])
        stored_attachment = next(
            item
            for item in event["store_data"]["ir.attachment"]
            if item["id"] == preview.id
        )
        self.assertEqual(stored_attachment["name"], preview.name)
        self.assertEqual(stored_attachment["mimetype"], XLSX_MIME)
        self.assertEqual(event["message"]["id"], preview_message.id)

    def test_partial_mapping_update_preserves_other_rules_and_returns_published_attachment(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Data"
        for coordinate in ("B3", "F16"):
            sheet[coordinate].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
        sheet.merge_cells("E17:H17")
        sheet["E17"] = "old reference"
        output = BytesIO()
        workbook.save(output)
        workbook.close()

        thread = self.env["llm.thread"].create(
            {
                "name": "Incremental mapping thread " + uuid4().hex,
                "provider_id": self.provider.id,
                "model_id": self.model.id,
            }
        )
        attachment = self.env["ir.attachment"].create(
            {
                "name": "incremental-mapping.xlsx",
                "type": "binary",
                "mimetype": XLSX_MIME,
                "raw": output.getvalue(),
                "company_id": self.env.company.id,
            }
        )
        upload = thread.message_post(
            body="Fill this workbook",
            llm_role="user",
            author_id=self.env.user.partner_id.id,
            attachment_ids=[attachment.id],
        )
        target = self.env["res.partner"].create(
            {
                "name": "Incremental target " + uuid4().hex,
                "email": "first@example.test",
                "phone": "+1-555-0100",
                "company_id": self.env.company.id,
            }
        )
        retriever_result = thread.message_post(
            body="Retriever result",
            llm_role="tool",
            body_json={
                "type": "tool_execution",
                "tool_call_id": "incremental-target-" + uuid4().hex,
                "tool_call": {"function": {"name": "odoo_record_retriever", "arguments": "{}"}},
                "tool_name": "odoo_record_retriever",
                "arguments": {
                    "model": "res.partner",
                    "domain": [["id", "=", target.id]],
                    "fields": ["id", "name", "email", "phone"],
                    "limit": 1,
                },
                "status": "completed",
                "result": [{"id": target.id, "name": target.name}],
            },
        )
        tool = self.env["office.mapping.tool"].with_context(message=retriever_result)
        context = tool.office_prepare_context("res.partner", target.id)
        session = self.env["office.mapping.session"].browse(context["session_id"])
        first = tool.office_save_mapping_preview(
            session.id,
            session.revision,
            {
                "schema_version": "m2.mapping-proposal.v1",
                "mappings": [
                    {"element_id": "xlsx:Data!B3", "source_field": "name", "value_type": "string"},
                    {"element_id": "xlsx:Data!F16", "source_field": "email", "value_type": "string"},
                ],
                "clarifications": [],
                "skipped_targets": [],
            },
        )
        self.assertEqual(first["status"], "preview_ready", first)

        # This is a true patch: only F16 and F17 are mentioned in this turn.
        second = tool.office_save_mapping_preview(
            session.id,
            session.revision,
            {
                "schema_version": "m2.mapping-proposal.v1",
                "mappings": [
                    {"element_id": "xlsx:Data!F16", "source_field": "phone", "value_type": "string"},
                    {"element_id": "F17", "value": ""},
                ],
                "clarifications": [],
                "skipped_targets": [],
                "clear_targets": ["F17"],
            },
        )

        self.assertEqual(second["status"], "preview_ready", second)
        saved = json.loads(session.mapping_rules_json)
        self.assertEqual(
            {item["element_id"]: item.get("source_field") for item in saved["mappings"]},
            {"xlsx:Data!B3": "name", "xlsx:Data!F16": "phone"},
        )
        self.assertEqual(saved["clear_targets"], ["xlsx:Data!E17"])
        final_preview = session.preview_attachment_id
        rendered = load_workbook(BytesIO(final_preview.raw), data_only=False)
        try:
            self.assertEqual(rendered["Data"]["B3"].value, target.name)
            self.assertEqual(rendered["Data"]["F16"].value, target.phone)
            self.assertIsNone(rendered["Data"]["E17"].value)
            self.assertIsNone(rendered["Data"]["F17"].value)
        finally:
            rendered.close()

        self.assertTrue(second["attachment_posted_to_thread"])
        self.assertEqual(
            second["attachment"],
            {
                "id": final_preview.id,
                "name": final_preview.name,
                "mimetype": XLSX_MIME,
                "message_id": second["message_id"],
            },
        )
        posted_message = self.env["mail.message"].browse(second["message_id"])
        self.assertIn(final_preview, posted_message.attachment_ids)
        self.assertEqual(posted_message.model, "llm.thread")
        self.assertEqual(posted_message.res_id, thread.id)

    def test_merged_range_alias_normalizes_to_the_single_writable_anchor(self):
        manifest = [
            {
                "element_id": "xlsx:Data!E17",
                "merge_range": "E17:H17",
                "write_target": "xlsx:Data!E17",
                "writable": True,
            }
        ]
        rules = {
            "mappings": [{"element_id": "E17:H17", "value": ""}],
            "clear_targets": ["E17:H17"],
            "skipped_targets": [],
            "clarifications": [],
        }

        _normalize_merged_target_aliases(rules, manifest)

        self.assertEqual(rules["mappings"][0]["element_id"], "xlsx:Data!E17")
        self.assertEqual(rules["clear_targets"], ["xlsx:Data!E17"])

        qualified = {
            "mappings": [{"element_id": "xlsx:Data!E17:H17", "value": ""}],
            "clear_targets": [],
            "skipped_targets": [],
            "clarifications": [],
        }
        _normalize_merged_target_aliases(qualified, manifest)
        self.assertEqual(qualified["mappings"][0]["element_id"], "xlsx:Data!E17")

        ambiguous_manifest = manifest + [
            {
                "element_id": "xlsx:Other!E17",
                "merge_range": "E17:H17",
                "write_target": "xlsx:Other!E17",
                "writable": True,
            }
        ]
        ambiguous = {
            "mappings": [{"element_id": "E17:H17", "value": ""}],
            "clear_targets": [],
            "skipped_targets": [],
            "clarifications": [],
        }
        _normalize_merged_target_aliases(ambiguous, ambiguous_manifest)
        self.assertEqual(ambiguous["mappings"][0]["element_id"], "E17:H17")

    def test_restore_current_proposal_returns_existing_preview_instead_of_history_error(self):
        thread, attachment, _upload = self._office_message("Fill this workbook")
        target = self.env["res.partner"].create(
            {"name": "Current revision target " + uuid4().hex, "company_id": self.env.company.id}
        )
        retriever_result = thread.message_post(
            body="Retriever result",
            llm_role="tool",
            body_json={
                "type": "tool_execution",
                "tool_call_id": "current-revision-" + uuid4().hex,
                "tool_call": {"function": {"name": "odoo_record_retriever", "arguments": "{}"}},
                "tool_name": "odoo_record_retriever",
                "arguments": {"model": "res.partner", "domain": [["id", "=", target.id]], "fields": ["id", "name"], "limit": 1},
                "status": "completed",
                "result": [{"id": target.id, "name": target.name}],
            },
        )
        tool = self.env["office.mapping.tool"].with_context(message=retriever_result)
        context = tool.office_prepare_context("res.partner", target.id)
        session = self.env["office.mapping.session"].browse(context["session_id"])
        generated = tool.office_save_mapping_preview(
            session.id,
            session.revision,
            {
                "schema_version": "m2.mapping-proposal.v1",
                "mappings": [{"element_id": "xlsx:Sheet!B1", "source_field": "name", "value_type": "string"}],
                "clarifications": [],
                "skipped_targets": [],
            },
        )
        self.assertEqual(generated["status"], "preview_ready", generated)
        proposal_revision = session.proposal_revision
        revision = session.revision
        preview_id = session.preview_attachment_id.id

        restored = tool.office_restore_proposal_revision(session.id, revision, proposal_revision)

        self.assertEqual(restored["status"], "unchanged")
        self.assertEqual(restored["restored_from_proposal_revision"], proposal_revision)
        self.assertEqual(restored["preview_attachment_id"], preview_id)
        self.assertTrue(restored["attachment_posted_to_thread"])
        self.assertEqual(session.revision, revision)
        self.assertEqual(session.preview_attachment_id.id, preview_id)

    def test_historical_restore_creates_new_revision_and_publishes_restored_preview(self):
        thread, _attachment, _upload = self._office_message("Fill this workbook")
        target = self.env["res.partner"].create(
            {
                "name": "Historical restore target " + uuid4().hex,
                "email": "historical@example.test",
                "company_id": self.env.company.id,
            }
        )
        retriever_result = thread.message_post(
            body="Retriever result",
            llm_role="tool",
            body_json={
                "type": "tool_execution",
                "tool_call_id": "historical-restore-" + uuid4().hex,
                "tool_call": {"function": {"name": "odoo_record_retriever", "arguments": "{}"}},
                "tool_name": "odoo_record_retriever",
                "arguments": {
                    "model": "res.partner",
                    "domain": [["id", "=", target.id]],
                    "fields": ["id", "name", "email"],
                    "limit": 1,
                },
                "status": "completed",
                "result": [{"id": target.id, "name": target.name, "email": target.email}],
            },
        )
        tool = self.env["office.mapping.tool"].with_context(message=retriever_result)
        context = tool.office_prepare_context("res.partner", target.id)
        session = self.env["office.mapping.session"].browse(context["session_id"])
        first_proposal = {
            "schema_version": "m2.mapping-proposal.v1",
            "mappings": [
                {"element_id": "xlsx:Sheet!B1", "source_field": "name", "value_type": "string"}
            ],
            "clarifications": [],
            "skipped_targets": [],
        }
        first = tool.office_save_mapping_preview(session.id, session.revision, first_proposal)
        self.assertEqual(first["status"], "preview_ready", first)
        self.assertEqual(session.proposal_revision, 1)

        second = tool.office_save_mapping_preview(
            session.id,
            session.revision,
            {
                **first_proposal,
                "mappings": [
                    {"element_id": "xlsx:Sheet!B1", "source_field": "email", "value_type": "string"}
                ],
            },
        )
        self.assertEqual(second["status"], "preview_ready", second)
        self.assertEqual(session.proposal_revision, 2)

        restored = tool.office_restore_proposal_revision(
            session.id, session.revision, proposal_revision=1
        )

        self.assertEqual(restored["status"], "preview_ready", restored)
        self.assertEqual(restored["restored_from_proposal_revision"], 1)
        self.assertEqual(session.proposal_revision, 3)
        self.assertEqual(json.loads(session.mapping_rules_json), first_proposal)
        self.assertTrue(restored["attachment_posted_to_thread"])
        preview = session.preview_attachment_id
        self.assertEqual(restored["preview_attachment_id"], preview.id)
        posted = self.env["mail.message"].browse(restored["message_id"])
        self.assertEqual((posted.model, posted.res_id), ("llm.thread", thread.id))
        self.assertIn(preview, posted.attachment_ids)
        workbook = load_workbook(BytesIO(preview.raw), data_only=False)
        try:
            self.assertEqual(workbook["Sheet"]["B1"].value, target.name)
        finally:
            workbook.close()

    def test_preview_failure_rolls_back_patch_and_preserves_previous_preview_delivery(self):
        thread, _attachment, _upload = self._office_message("Fill this workbook")
        target = self.env["res.partner"].create(
            {
                "name": "Preview rollback target " + uuid4().hex,
                "email": "before@example.test",
                "company_id": self.env.company.id,
            }
        )
        retriever_result = thread.message_post(
            body="Retriever result",
            llm_role="tool",
            body_json={
                "type": "tool_execution",
                "tool_call_id": "preview-rollback-" + uuid4().hex,
                "tool_call": {"function": {"name": "odoo_record_retriever", "arguments": "{}"}},
                "tool_name": "odoo_record_retriever",
                "arguments": {
                    "model": "res.partner",
                    "domain": [["id", "=", target.id]],
                    "fields": ["id", "name", "email"],
                    "limit": 1,
                },
                "status": "completed",
                "result": [{"id": target.id, "name": target.name, "email": target.email}],
            },
        )
        tool = self.env["office.mapping.tool"].with_context(message=retriever_result)
        context = tool.office_prepare_context("res.partner", target.id)
        session = self.env["office.mapping.session"].browse(context["session_id"])
        original = {
            "schema_version": "m2.mapping-proposal.v1",
            "mappings": [
                {"element_id": "xlsx:Sheet!B1", "source_field": "name", "value_type": "string"}
            ],
            "clarifications": [],
            "skipped_targets": [],
        }
        generated = tool.office_save_mapping_preview(session.id, session.revision, original)
        self.assertEqual(generated["status"], "preview_ready", generated)
        session.invalidate_recordset()
        original_rules = session.mapping_rules_json
        original_revision = session.revision
        original_proposal_revision = session.proposal_revision
        original_preview = session.preview_attachment_id
        original_message_ids = thread.message_ids.ids

        with patch(
            "odoo.addons.office_engine_m2.models.office_mapping_tools.render_preview",
            side_effect=UserError("synthetic preview rendering failure"),
        ):
            with self.assertRaisesRegex(UserError, "synthetic preview rendering failure"):
                tool.office_save_mapping_preview(
                    session.id,
                    session.revision,
                    {
                        **original,
                        "mappings": [
                            {"element_id": "xlsx:Sheet!B1", "source_field": "email", "value_type": "string"}
                        ],
                    },
                )

        session.invalidate_recordset()
        self.assertEqual(session.mapping_rules_json, original_rules)
        self.assertEqual(session.revision, original_revision)
        self.assertEqual(session.proposal_revision, original_proposal_revision)
        self.assertEqual(session.preview_attachment_id, original_preview)
        self.assertTrue(original_preview.exists())
        self.assertEqual(thread.message_ids.ids, original_message_ids)
        self.assertTrue(
            self.env["mail.message"].search_count(
                [
                    ("model", "=", "llm.thread"),
                    ("res_id", "=", thread.id),
                    ("attachment_ids", "in", [original_preview.id]),
                ]
            )
        )

    def test_related_full_address_is_discovered_only_through_readable_relations(self):
        fields = _field_candidates(self.env, self.env.company)
        self.assertEqual(fields.get("partner_id.contact_address"), "string")

        root = self.env["res.partner"].create(
            {"name": "Address root " + uuid4().hex, "company_id": self.env.company.id}
        )
        parent = self.env["res.partner"].create(
            {"name": "Address parent " + uuid4().hex, "parent_id": root.id, "company_id": self.env.company.id}
        )
        target = self.env["res.partner"].create(
            {"name": "Address target " + uuid4().hex, "parent_id": parent.id, "company_id": self.env.company.id}
        )
        nested_fields = _field_candidates(self.env, target)
        self.assertEqual(nested_fields.get("parent_id.parent_id.contact_address"), "string")

    def test_fallback_uses_second_authorized_address_when_first_is_empty(self):
        thread = self.env["llm.thread"].create(
            {
                "name": "Address fallback thread " + uuid4().hex,
                "provider_id": self.provider.id,
                "model_id": self.model.id,
            }
        )
        attachment = self.env["ir.attachment"].create(
            {
                "name": "address-fallback.xlsx",
                "type": "binary",
                "mimetype": XLSX_MIME,
                "raw": _xlsx(),
                "company_id": self.env.company.id,
            }
        )
        source_message = thread.message_post(
            body="Use the available company address",
            llm_role="user",
            author_id=self.env.user.partner_id.id,
            attachment_ids=[attachment.id],
        )
        inspection = inspect_document(attachment.raw, attachment.name, attachment.mimetype, _resource_budget())
        manifest, template_text = _template_context(inspection)
        created = create_session(
            self.env,
            thread_id=thread.id,
            source_message_id=source_message.id,
            source_attachment_id=attachment.id,
            target_model="res.company",
            target_record_id=self.env.company.id,
        )
        session = self.env["office.mapping.session"].browse(created["session_id"])
        set_mapping_context(
            self.env,
            session.id,
            manifest,
            {"partner_id.contact_address": "string", "partner_id.street": "string"},
            template_text=template_text,
        )
        rules = {
            "schema_version": "m2.mapping-proposal.v1",
            "mappings": [
                {
                    "element_id": "xlsx:Sheet!B1",
                    "source_fields": ["partner_id.contact_address", "partner_id.street"],
                    "value_type": "string",
                }
            ],
            "clarifications": [],
            "skipped_targets": [],
        }
        session._save_mapping_from_service(json.dumps(rules), session.revision, "revision_pending")

        with patch(
            "odoo.addons.office_engine_m2.services.render_bridge._retrieve_record",
            return_value={
                "partner_id.contact_address": False,
                "partner_id.street": "250 Executive Park Blvd, Suite 3400, San Francisco, CA 94134",
            },
        ):
            plan, _snapshot_hash, _summary = _compile_plan(self.env, session)

        self.assertEqual(
            plan["writes"],
            [
                {
                    "element_id": "xlsx:Sheet!B1",
                    "operation": "set_value",
                    "value": {
                        "type": "string",
                        "data": "250 Executive Park Blvd, Suite 3400, San Francisco, CA 94134",
                    },
                }
            ],
        )

    def test_openai_payload_keeps_user_text_and_excludes_office_attachment_bytes(self):
        instruction = "如果订单没有仓库，b4就用本公司地址。"
        thread, attachment, message = self._office_message(instruction)

        # The same native history used by llm_assistant still contains the upload.
        self.assertIn(message, thread.get_llm_messages())
        payload = message.openai_format_message(is_multimodal=True)
        self.assertEqual(payload, {"role": "user", "content": instruction})
        self.assertEqual(message._get_attachments_by_mimetype((XLSX_MIME,)), self.env["ir.attachment"])
        encoded = attachment.datas
        if isinstance(encoded, bytes):
            encoded = encoded.decode("ascii")
        self.assertNotIn(encoded, json.dumps(payload, ensure_ascii=False))
        self.assertNotIn("base64", json.dumps(payload, ensure_ascii=False).lower())

    def test_linked_chat_thread_reuses_parent_office_tools_and_template(self):
        parent, attachment, upload = self._office_message("已上传的模板")
        child = self.env["llm.thread"].create(
            {
                "name": "Linked chat thread " + uuid4().hex,
                "provider_id": self.provider.id,
                "model_id": self.model.id,
                "model": "llm.thread",
                "res_id": parent.id,
            }
        )
        linked_attachment_ids = child._office_linked_template_attachment_ids([])
        self.assertEqual(linked_attachment_ids, [attachment.id])
        child_upload = child.message_post(
            body="用可读的业务记录填写已上传模板",
            llm_role="user",
            author_id=self.env.user.partner_id.id,
            attachment_ids=linked_attachment_ids,
        )

        # The chatter's AI Chat creates a linked child Thread. It must inherit
        # Office capability and carry the existing attachment reference on the
        # first native child-chat turn. This lets existing M1 request validation
        # work while the Provider serializer keeps Office bytes out of payloads.
        self.assertTrue(child._office_is_active())
        found_upload, found_attachment = child._office_latest_upload()
        self.assertEqual(found_upload, child_upload)
        self.assertEqual(found_attachment, attachment)
        self.assertFalse(child._office_linked_template_attachment_ids([]))
        provider_payload = child_upload.openai_format_message(is_multimodal=True)
        self.assertEqual(provider_payload, {"role": "user", "content": "用可读的业务记录填写已上传模板"})
        self.assertEqual(
            set(child._office_bind_tools().mapped("name")),
            {
                "office_prepare_context",
                "office_save_mapping_preview",
                "office_restore_proposal_revision",
                "office_finalize",
                "odoo_record_retriever",
            },
        )

        target = self.env["res.partner"].create(
            {"name": "Linked child target " + uuid4().hex, "company_id": self.env.company.id}
        )
        tool_message = child.message_post(
            body="Retriever result",
            llm_role="tool",
            body_json={
                "type": "tool_execution",
                "tool_call_id": "linked-child-retriever-call",
                "tool_call": {"function": {"name": "odoo_record_retriever", "arguments": "{}"}},
                "tool_name": "odoo_record_retriever",
                "arguments": {"model": "res.partner", "domain": [["id", "=", target.id]], "fields": ["name"], "limit": 1},
                "status": "completed",
                "result": [{"id": target.id, "name": target.name}],
            },
        )
        context = self.env["office.mapping.tool"].with_context(message=tool_message).office_prepare_context(
            "res.partner", target.id
        )
        session = self.env["office.mapping.session"].browse(context["session_id"])
        self.assertEqual(session.thread_id, child)
        self.assertEqual(session.source_message_id, child_upload)
        self.assertEqual(session.source_attachment_id, attachment)

    def test_template_targets_are_optional_even_when_next_to_labels(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Data"
        sheet["A1"] = "Customer:"
        sheet["B1"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
        sheet["B4"] = "Warehouse address"
        sheet["B5"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
        sheet["B6"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
        output = BytesIO()
        workbook.save(output)
        workbook.close()

        from odoo.addons.office_engine_odoo.models.office_document_request import _resource_budget

        inspection = inspect_document(output.getvalue(), "labels.xlsx", XLSX_MIME, _resource_budget())
        manifest, _template_text = _template_context(inspection)
        required_by_id = {item["element_id"]: item["required"] for item in manifest}

        self.assertFalse(required_by_id["xlsx:Data!B1"])
        self.assertFalse(required_by_id["xlsx:Data!B5"])
        self.assertFalse(required_by_id["xlsx:Data!B6"])

    def test_office_message_is_one_native_user_message_not_reposted_by_m2(self):
        thread, _attachment, message = self._office_message("Read this workbook")
        self.assertEqual(
            self.env["mail.message"].search_count(
                [
                    ("model", "=", "llm.thread"),
                    ("res_id", "=", thread.id),
                    ("llm_role", "=", "user"),
                    ("body", "ilike", "Read this workbook"),
                ]
            ),
            1,
        )
        self.assertEqual(message.author_id, self.env.user.partner_id)

    def test_retriever_uses_current_user_model_and_field_rights(self):
        thread, _attachment, message = self._office_message("Fill the workbook")
        retriever = self.env["llm.tool"].with_context(message=message)
        # ``sale`` is intentionally not an addon dependency, so Odoo's
        # isolated module test registry may omit it. In the live 8091
        # environment the same assertion is exercised against sale.order.
        retrieval_model, retrieval_field = (
            ("sale.order", "amount_total")
            if "sale.order" in self.env.registry.models
            else ("res.partner", "email")
        )
        result = retriever.odoo_record_retriever_execute(
            model=retrieval_model,
            domain=[["name", "=", "NO-SUCH-OFFICE-ORDER"]],
            fields=[retrieval_field],
            limit=1,
        )
        self.assertEqual(result, [])

        limited_user = self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "Office Retriever Limited User " + uuid4().hex,
                "login": "office-retriever-limited-" + uuid4().hex,
                "company_id": self.env.company.id,
                "company_ids": [(6, 0, [self.env.company.id])],
                "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        limited_retriever = self.env["llm.tool"].with_user(limited_user).with_context(message=message)
        with self.assertRaises(AccessError):
            limited_retriever.odoo_record_retriever_execute(
                "ir.config_parameter", [["key", "=", "database.uuid"]], ["key"], 1
            )

    def test_native_retriever_honors_model_limit_for_duplicate_matches(self):
        thread, _attachment, user_message = self._office_message("用同名记录填工作簿")
        duplicate_name = "Office duplicate " + uuid4().hex
        records = self.env["res.partner"].create([
            {"name": duplicate_name, "company_id": self.env.company.id},
            {"name": duplicate_name, "company_id": self.env.company.id},
        ])
        rows = self.env["llm.tool"].with_context(message=user_message).odoo_record_retriever_execute(
            "res.partner", [["name", "=", duplicate_name]], ["id", "name"], 1
        )
        self.assertEqual(len(rows), 1)
        self.assertIn(rows[0]["id"], records.ids)

        # office_prepare_context accepts an ACL-readable target directly; it
        # does not require a Retriever transcript or silently choose a record.
        context = self.env["office.mapping.tool"].with_context(
            message=user_message
        ).office_prepare_context("res.partner", records[0].id)
        session = self.env["office.mapping.session"].browse(context["session_id"])
        self.assertEqual(session.target_record_id, records[0].id)
        self.assertEqual(session.thread_id, thread)

    def test_native_retriever_pages_with_stable_order_and_current_user_count(self):
        thread, _attachment, user_message = self._office_message("Read these records in pages")
        records = self.env["res.partner"].create(
            [
                {"name": f"Paged partner {index} {uuid4().hex}", "company_id": self.env.company.id}
                for index in range(5)
            ]
        )
        retriever = self.env["llm.tool"].with_context(message=user_message)
        first = retriever.odoo_record_retriever_execute(
            "res.partner",
            [["id", "in", records.ids]],
            ["name"],
            2,
            offset=0,
            order="name asc",
            include_pagination=True,
        )
        second = retriever.odoo_record_retriever_execute(
            "res.partner",
            [["id", "in", records.ids]],
            ["name"],
            2,
            offset=2,
            order="name asc",
            include_pagination=True,
        )
        final = retriever.odoo_record_retriever_execute(
            "res.partner",
            [["id", "in", records.ids]],
            ["name"],
            2,
            offset=4,
            order="name asc",
            include_pagination=True,
        )
        self.assertEqual(first["count"], 5)
        self.assertEqual(first["offset"], 0)
        self.assertTrue(first["has_more"])
        self.assertTrue(second["has_more"])
        self.assertFalse(final["has_more"])
        self.assertEqual(len(first["records"]), 2)
        self.assertEqual(len(second["records"]), 2)
        self.assertEqual(len(final["records"]), 1)
        self.assertEqual(
            [item["name"] for page in (first, second, final) for item in page["records"]],
            sorted(records.mapped("name")),
        )

    def test_selected_root_records_fill_sorted_repeat_rows_without_losing_identity(self):
        thread = self.env["llm.thread"].create(
            {
                "name": "Selected-record repeat thread " + uuid4().hex,
                "provider_id": self.provider.id,
                "model_id": self.model.id,
            }
        )
        attachment = self.env["ir.attachment"].create(
            {
                "name": "selected-records.xlsx",
                "type": "binary",
                "mimetype": XLSX_MIME,
                "raw": _repeat_rows_xlsx(),
                "company_id": self.env.company.id,
            }
        )
        upload = thread.message_post(
            body="Fill every selected record into repeated rows",
            llm_role="user",
            author_id=self.env.user.partner_id.id,
            attachment_ids=[attachment.id],
        )
        names = ["Selected E", "Selected C", "Selected A", "Selected D", "Selected B"]
        records = self.env["res.partner"].create(
            [{"name": name + " " + uuid4().hex, "company_id": self.env.company.id} for name in names]
        )
        retriever_message = thread.message_post(
            body="Retrieved all selected records",
            llm_role="tool",
            body_json={
                "type": "tool_execution",
                "tool_call_id": "selected-record-page-call",
                "tool_call": {"function": {"name": "odoo_record_retriever", "arguments": "{}"}},
                "tool_name": "odoo_record_retriever",
                "arguments": {
                    "model": "res.partner",
                    "domain": [["id", "in", records.ids]],
                    "fields": ["id", "name"],
                    "limit": 100,
                    "offset": 0,
                    "order": "name asc",
                    "include_pagination": True,
                },
                "status": "completed",
                "result": {
                    "records": [{"id": item.id, "name": item.name} for item in records],
                    "count": len(records),
                    "offset": 0,
                    "limit": 100,
                    "has_more": False,
                },
            },
        )
        tool = self.env["office.mapping.tool"].with_context(message=retriever_message)
        context = tool.office_prepare_context(
            "res.partner", records[0].id, target_record_ids=records.ids
        )
        self.assertEqual(context["source_records"]["count"], len(records))
        selected_collection = next(
            item for item in context["repeat_row_collections"]
            if item["collection_field"] == "selected_records"
        )
        self.assertEqual(selected_collection["row_count"], len(records))
        self.assertIn("name", selected_collection["allowed_fields"])

        session = self.env["office.mapping.session"].browse(context["session_id"])
        result = tool.office_save_mapping_preview(
            session.id,
            session.revision,
            {
                "schema_version": "m2.mapping-proposal.v1",
                "mappings": [],
                "clarifications": [],
                "skipped_targets": [],
            },
            repeat_rows=[
                {
                    "collection_field": "selected_records",
                    "sheet": "Data",
                    "start_row": 4,
                    "sort_by": "name",
                    "sort_direction": "asc",
                    "columns": [{"column": "B", "source_field": "name"}],
                }
            ],
        )
        self.assertEqual(result["status"], "preview_ready", result)
        session.invalidate_recordset(["context_json", "preview_attachment_id"])
        stored_context = json.loads(session.context_json)
        group = stored_context["mapping_groups"][0]
        self.assertEqual(group["record_ids"], records.ids)
        self.assertEqual(len(group["target_rows"]), len(records))
        preview = session.preview_attachment_id
        self.assertTrue(preview.raw)
        workbook = load_workbook(BytesIO(preview.raw), data_only=False)
        self.assertEqual(
            [workbook["Data"][f"B{row}"].value for row in range(4, 9)],
            sorted(records.mapped("name")),
        )
        self.assertEqual(workbook["Data"]["A1"].value, "Parent")
        workbook.close()

    def test_selected_root_records_reauthorize_explicit_retrieved_fields_for_repeat_rows(self):
        """Fields returned by an authorized Retriever remain usable after context refresh."""
        thread, _attachment, user_message = self._office_message(
            "Fill the selected records into repeated rows", raw=_repeat_rows_xlsx()
        )
        records = self.env["res.partner"].create([
            {
                "name": "Explicit field row %s %s" % (index, uuid4().hex),
                "email": "row%s@example.invalid" % index,
                "company_id": self.env.company.id,
            }
            for index in range(3)
        ])
        tool = self.env["office.mapping.tool"].with_context(message=user_message)
        context = tool.office_prepare_context(
            "res.partner",
            records[0].id,
            target_record_ids=records.ids,
            requested_fields=["email", "create_date"],
        )
        session = self.env["office.mapping.session"].browse(context["session_id"])
        self.assertIn("email", context["allowed_fields"])
        self.assertIn("create_date", context["allowed_fields"])
        self.assertEqual(context["unavailable_requested_fields"], [])
        collection = next(
            item for item in context["repeat_row_collections"]
            if item["collection_field"] == "selected_records"
        )
        self.assertIn("email", collection["allowed_fields"])
        self.assertIn("create_date", collection["allowed_fields"])

        result = tool.office_save_mapping_preview(
            session.id,
            session.revision,
            {
                "schema_version": "m2.mapping-proposal.v1",
                "mappings": [],
                "clarifications": [],
                "skipped_targets": [],
            },
            repeat_rows=[
                {
                    "collection_field": "selected_records",
                    "sheet": "Data",
                    "start_row": 4,
                    "columns": [
                        {"column": "B", "source_field": "name"},
                        {"column": "C", "source_field": "email"},
                        {"column": "D", "source_field": "create_date"},
                    ],
                }
            ],
        )
        self.assertEqual(result["status"], "preview_ready", result)
        workbook = load_workbook(BytesIO(session.preview_attachment_id.raw), data_only=False)
        try:
            self.assertEqual(
                [workbook["Data"][f"C{row}"].value for row in range(4, 7)],
                records.mapped("email"),
            )
            self.assertTrue(all(workbook["Data"][f"D{row}"].value for row in range(4, 7)))
        finally:
            workbook.close()

    def test_selected_records_generate_preview_for_append_only_template(self):
        thread, _attachment, user_message = self._office_message(
            "Fill selected records into this import sheet", raw=_no_summary_repeat_rows_xlsx()
        )
        records = self.env["res.partner"].create([
            {
                "name": "Append-only record %s %s" % (index, uuid4().hex),
                "email": "append%s@example.invalid" % index,
                "company_id": self.env.company.id,
            }
            for index in range(3)
        ])
        retriever_message = thread.message_post(
            body="Retrieved selected records",
            llm_role="tool",
            body_json={
                "type": "tool_execution",
                "tool_call_id": "append-only-record-call",
                "tool_call": {"function": {"name": "odoo_record_retriever", "arguments": "{}"}},
                "tool_name": "odoo_record_retriever",
                "arguments": {
                    "model": "res.partner",
                    "domain": [["id", "in", records.ids]],
                    "fields": ["id", "name", "email"],
                    "limit": 100,
                    "offset": 0,
                    "order": "name asc",
                },
                "status": "completed",
                "result": [
                    {"id": record.id, "name": record.name, "email": record.email}
                    for record in records
                ],
            },
        )
        tool = self.env["office.mapping.tool"].with_context(message=retriever_message)
        context = tool.office_prepare_context(
            "res.partner", records[0].id, target_record_ids=records.ids
        )
        session = self.env["office.mapping.session"].browse(context["session_id"])
        result = tool.office_save_mapping_preview(
            session.id,
            session.revision,
            {"schema_version": "m2.mapping-proposal.v1", "mappings": [], "clarifications": [], "skipped_targets": []},
            repeat_rows=[
                {
                    "collection_field": "selected_records",
                    "sheet": "Import",
                    "start_row": 2,
                    "sort_by": "name",
                    "sort_direction": "asc",
                    "columns": [
                        {"column": "A", "source_field": "name"},
                        {"column": "B", "source_field": "email"},
                        {"column": "C", "source_field": "email"},
                    ],
                }
            ],
        )
        self.assertEqual(result["status"], "preview_ready", result)
        self.assertTrue(session.preview_attachment_id.raw)
        self.assertTrue(session.preview_attachment_id.name.endswith(".xlsx"))
        self.assertEqual(session.preview_attachment_id.mimetype, XLSX_MIME)

        workbook = load_workbook(BytesIO(session.preview_attachment_id.raw), data_only=False)
        try:
            sheet = workbook["Import"]
            self.assertEqual(sheet["A1"].value, "Record")
            self.assertEqual(
                [sheet[f"A{row}"].value for row in range(2, 5)],
                sorted(records.mapped("name")),
            )
            by_name = {record.name: record.email for record in records}
            self.assertEqual(
                [sheet[f"B{row}"].value for row in range(2, 5)],
                [by_name[name] for name in sorted(by_name)],
            )
            self.assertEqual(
                [sheet[f"C{row}"].value for row in range(2, 5)],
                [by_name[name] for name in sorted(by_name)],
            )
            self.assertEqual(sheet["A4"].fill.fgColor.rgb, "00D9EAF7")
            self.assertEqual(sheet["B4"].number_format, "@")
        finally:
            workbook.close()

    def test_repeat_rows_can_clear_an_unmapped_physical_cell_in_data_band(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Import"
        sheet["A1"] = "Record"
        sheet["B1"] = "Email"
        sheet["M1"] = "Summary"
        sheet["A2"] = "example"
        sheet["A2"].fill = PatternFill(fill_type="solid", fgColor="D9EAF7")
        sheet["B2"] = ""
        sheet["B2"].number_format = "@"
        source = BytesIO()
        workbook.save(source)
        workbook.close()
        thread, _attachment, _user_message = self._office_message(
            "Fill selected records into this import sheet", raw=source.getvalue()
        )
        records = self.env["res.partner"].create([
            {
                "name": "Clearable repeat record %s %s" % (index, uuid4().hex),
                "email": "clearable%s@example.invalid" % index,
                "company_id": self.env.company.id,
            }
            for index in range(3)
        ])
        retriever_message = thread.message_post(
            body="Retrieved selected records",
            llm_role="tool",
            body_json={
                "type": "tool_execution",
                "tool_call_id": "clear-repeat-cell-call",
                "tool_call": {"function": {"name": "odoo_record_retriever", "arguments": "{}"}},
                "tool_name": "odoo_record_retriever",
                "arguments": {
                    "model": "res.partner",
                    "domain": [["id", "in", records.ids]],
                    "fields": ["id", "name", "email"],
                    "limit": 10,
                    "offset": 0,
                    "order": "name asc",
                },
                "status": "completed",
                "result": [
                    {"id": record.id, "name": record.name, "email": record.email}
                    for record in records
                ],
            },
        )
        tool = self.env["office.mapping.tool"].with_context(message=retriever_message)
        context = tool.office_prepare_context(
            "res.partner", records[0].id, target_record_ids=records.ids
        )
        session = self.env["office.mapping.session"].browse(context["session_id"])
        repeat_rows = [
            {
                "collection_field": "selected_records",
                "sheet": "Import",
                "start_row": 2,
                "sort_by": "name",
                "sort_direction": "asc",
                "columns": [
                    {"column": "A", "source_field": "name"},
                    {"column": "B", "source_field": "email"},
                ],
            }
        ]
        initial = tool.office_save_mapping_preview(
            session.id,
            session.revision,
            {
                "schema_version": "m2.mapping-proposal.v1",
                "mappings": [],
                "clarifications": [],
                "skipped_targets": [],
            },
            repeat_rows=repeat_rows,
        )
        self.assertEqual(initial["status"], "preview_ready", initial)
        before_revision = session.revision
        result = tool.office_save_mapping_preview(
            session.id,
            before_revision,
            {
                "schema_version": "m2.mapping-proposal.v1",
                # Match the compact blank-write representation emitted by
                # the live model. Sheet-qualified coordinates without the
                # internal xlsx: prefix must still resolve to this sheet.
                "mappings": [
                    {"element_id": f"Import!C{row}", "value": ""}
                    for row in range(2, 5)
                ],
                "clarifications": [],
                "skipped_targets": [],
            },
        )

        self.assertEqual(result["status"], "preview_ready", result)
        self.assertGreater(session.revision, before_revision)
        self.assertEqual(result["revision"], session.revision)
        self.assertEqual(session.preview_attachment_id.file_size, len(session.preview_attachment_id.raw))
        workbook = load_workbook(BytesIO(session.preview_attachment_id.raw), data_only=False)
        try:
            sheet = workbook["Import"]
            self.assertEqual(sheet["A1"].value, "Record")
            self.assertEqual([sheet[f"A{row}"].value for row in range(2, 5)], sorted(records.mapped("name")))
            by_name = {record.name: record.email for record in records}
            self.assertEqual(
                [sheet[f"B{row}"].value for row in range(2, 5)],
                [by_name[name] for name in sorted(by_name)],
            )
            self.assertEqual([sheet[f"C{row}"].value for row in range(2, 5)], [None, None, None])
        finally:
            workbook.close()

        # A model may include the current repeat_rows again when applying a
        # conversational clear. The existing mapped rows and explicit blank
        # writes must remain valid in that full-plan submission.
        retry = tool.office_save_mapping_preview(
            session.id,
            session.revision,
            {
                "schema_version": "m2.mapping-proposal.v1",
                "mappings": [
                    {"element_id": f"Import!C{row}", "value": ""}
                    for row in range(2, 5)
                ],
                "clarifications": [],
                "skipped_targets": [],
            },
            repeat_rows=repeat_rows,
        )
        self.assertIn(retry["status"], {"preview_ready", "unchanged"}, retry)

    def test_explicit_field_discovery_does_not_bypass_current_user_field_acl(self):
        limited_user = self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "Office Field ACL User " + uuid4().hex,
                "login": "office-field-acl-" + uuid4().hex,
                "company_id": self.env.company.id,
                "company_ids": [(6, 0, [self.env.company.id])],
                "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        user_env = self.env(user=limited_user)
        _records, fields = _selected_record_context(
            user_env, "res.users", [limited_user.id], requested_fields=["totp_secret"]
        )
        self.assertNotIn("totp_secret", fields)

    def test_office_retriever_supports_acl_readable_relational_fields(self):
        thread, _attachment, message = self._office_message("Read the related records")
        parent = self.env["res.partner"].create(
            {"name": "Office relation parent " + uuid4().hex, "company_id": self.env.company.id}
        )
        child = self.env["res.partner"].create(
            {"name": "Office relation child " + uuid4().hex, "parent_id": parent.id}
        )
        retriever = self.env["llm.tool"].with_context(message=message)
        rows = retriever.odoo_record_retriever_execute(
            model="res.partner",
            domain=[["name", "=", parent.name]],
            fields=["id", "name", "child_ids"],
            limit=1,
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], parent.id)
        self.assertIn(child.id, rows[0]["child_ids"])

    def test_office_prepare_advertises_repeat_rows_from_readable_one2many(self):
        thread, _attachment, user_message = self._office_message("填充订单明细")
        parent = self.env["res.partner"].create(
            {"name": "Repeat parent " + uuid4().hex, "company_id": self.env.company.id}
        )
        children = self.env["res.partner"].create([
            {"name": "Repeat child 1 " + uuid4().hex, "parent_id": parent.id},
            {"name": "Repeat child 2 " + uuid4().hex, "parent_id": parent.id},
        ])
        retriever_result = thread.message_post(
            body="Retriever result",
            llm_role="tool",
            body_json={
                "type": "tool_execution",
                "tool_call_id": "repeat-parent-call",
                "tool_call": {"function": {"name": "odoo_record_retriever", "arguments": "{}"}},
                "tool_name": "odoo_record_retriever",
                "arguments": {"model": "res.partner", "domain": [["id", "=", parent.id]], "fields": ["name"], "limit": 1},
                "status": "completed",
                "result": [{"id": parent.id, "name": parent.name}],
            },
        )
        context = self.env["office.mapping.tool"].with_context(
            message=retriever_result
        ).office_prepare_context("res.partner", parent.id)

        self.assertIn("repeat_rows", context["mapping_limits"]["supported"])
        self.assertNotIn("repeat_rows", context["mapping_limits"]["unsupported"])
        candidates = context["repeat_row_collections"]
        candidate = next(item for item in candidates if item["collection_field"] == "child_ids")
        self.assertEqual(candidate["relation_model"], "res.partner")
        self.assertEqual(candidate["row_count"], len(children))
        self.assertIn("name", candidate["allowed_fields"])
        self.assertNotIn("sample", candidate)

    def test_repeat_row_candidates_keep_product_identifiers_and_weight_in_bounded_schema(self):
        class Rows:
            def __bool__(self):
                return True

            def __len__(self):
                return 6

            def check_access(self, _operation):
                return None

        class Target:
            _fields = {
                "order_line": SimpleNamespace(
                    type="one2many", comodel_name="sale.order.line", inverse_name="order_id"
                )
            }

            def check_access(self, _operation):
                return None

            def check_field_access_rights(self, _operation, _field_names):
                return None

            def __getitem__(self, _field_name):
                return Rows()

        discovered_fields = {f"unrelated_{index}": "string" for index in range(200)}
        discovered_fields.update(
            {
                "product_id.default_code": "string",
                "product_id.barcode": "string",
                "product_id.weight": "number",
                "product_id.net_weight": "number",
                "product_uom_qty": "number",
            }
        )
        with patch("odoo.addons.office_engine_m2.services.chat_entrypoint._field_candidates", return_value=discovered_fields):
            candidate = _repeat_row_collection_candidates(self.env, Target())[0]

        self.assertIn("product_id.default_code", candidate["allowed_fields"])
        self.assertIn("product_id.barcode", candidate["allowed_fields"])
        self.assertIn("product_id.weight", candidate["allowed_fields"])
        self.assertIn("product_uom_qty", candidate["allowed_fields"])

    def test_repeat_row_candidates_preserve_direct_fields_before_related_field_overflow(self):
        class Rows:
            def __bool__(self):
                return True

            def __len__(self):
                return 2

            def check_access(self, _operation):
                return None

        class Target:
            _fields = {
                "quant_ids": SimpleNamespace(
                    type="one2many", comodel_name="stock.quant", inverse_name="location_id"
                )
            }

            def check_access(self, _operation):
                return None

            def check_field_access_rights(self, _operation, _field_names):
                return None

            def __getitem__(self, _field_name):
                return Rows()

        discovered_fields = {
            **{f"aaa_relation_{index:03d}.unrelated": "string" for index in range(200)},
            "quantity": "number",
            "reserved_quantity": "number",
            "available_quantity": "number",
            "location_id.complete_name": "string",
            "product_id.default_code": "string",
        }
        with patch(
            "odoo.addons.office_engine_m2.services.chat_entrypoint._field_candidates",
            return_value=discovered_fields,
        ):
            candidate = _repeat_row_collection_candidates(self.env, Target())[0]

        self.assertLessEqual(len(candidate["allowed_fields"]), 160)
        self.assertIn("quantity", candidate["allowed_fields"])
        self.assertIn("reserved_quantity", candidate["allowed_fields"])
        self.assertIn("available_quantity", candidate["allowed_fields"])
        self.assertIn("location_id.complete_name", candidate["allowed_fields"])
        self.assertIn("product_id.default_code", candidate["allowed_fields"])

    def test_office_retriever_uses_requested_domain_inside_active_session(self):
        thread, _attachment, message = self._office_message("读取关联明细")
        parent = self.env["res.partner"].create(
            {"name": "Bound parent " + uuid4().hex, "company_id": self.env.company.id}
        )
        children = self.env["res.partner"].create([
            {"name": "Bound child A " + uuid4().hex, "parent_id": parent.id},
            {"name": "Bound child B " + uuid4().hex, "parent_id": parent.id},
        ])
        other = self.env["res.partner"].create(
            {"name": "Other readable record " + uuid4().hex, "company_id": self.env.company.id}
        )
        from ..services.mapping_service import create_session, set_mapping_context

        created = create_session(
            self.env,
            thread_id=thread.id,
            source_message_id=message.id,
            source_attachment_id=message.attachment_ids.id,
            target_model="res.partner",
            target_record_id=parent.id,
        )
        set_mapping_context(self.env, created["session_id"], [], {"name": "string"})
        retriever = self.env["llm.tool"].with_context(message=message)

        # Even in an active Office Session, the native Retriever receives the
        # supplied model/domain/fields/limit unchanged. The caller's ACLs and
        # record rules are the only record-visibility policy.
        linked_rows = retriever.odoo_record_retriever_execute(
            "res.partner", [["parent_id", "=", parent.id]], ["id", "name"], 2
        )
        other_rows = retriever.odoo_record_retriever_execute(
            "res.partner", [["id", "=", other.id]], ["id", "name"], 1
        )
        self.assertEqual({row["id"] for row in linked_rows}, set(children.ids))
        self.assertEqual(other_rows, [{"id": other.id, "name": other.name}])
    def test_mapping_accepts_new_live_readable_field_not_in_session_discovery_snapshot(self):
        thread, attachment, upload = self._office_message("Fill the workbook from the contact record")
        target = self.env["res.partner"].create(
            {
                "name": "Newly requested mapping field " + uuid4().hex,
                "email": "newly-requested@example.test",
                "company_id": self.env.company.id,
            }
        )
        from ..services.mapping_service import create_session

        created = create_session(
            self.env,
            thread_id=thread.id,
            source_message_id=upload.id,
            source_attachment_id=attachment.id,
            target_model="res.partner",
            target_record_id=target.id,
        )
        inspection = inspect_document(attachment.raw, attachment.name, attachment.mimetype, _resource_budget())
        manifest, visible_text = _template_context(inspection)
        set_mapping_context(
            self.env,
            created["session_id"],
            manifest,
            {"name": "string"},
            template_text=visible_text,
            document_format="xlsx",
        )
        session = self.env["office.mapping.session"].browse(created["session_id"])
        retriever_result = thread.message_post(
            body="Verified target record",
            llm_role="tool",
            body_json={
                "type": "tool_execution",
                "tool_call_id": "verified-target-" + uuid4().hex,
                "tool_call": {"function": {"name": "odoo_record_retriever", "arguments": "{}"}},
                "tool_name": "odoo_record_retriever",
                "arguments": {
                    "model": "res.partner",
                    "domain": [["id", "=", target.id]],
                    "fields": ["id", "name"],
                    "limit": 1,
                },
                "status": "completed",
                "result": [{"id": target.id, "name": target.name}],
            },
        )
        result = self.env["office.mapping.tool"].with_context(message=retriever_result).office_save_mapping_preview(
            session.id,
            session.revision,
            {
                "schema_version": "m2.mapping-proposal.v1",
                "mappings": [
                    {"element_id": "xlsx:Sheet!A1", "source_field": "email", "value_type": "string"}
                ],
                "clarifications": [],
                "skipped_targets": [],
            },
        )

        self.assertEqual(result["status"], "preview_ready", result)
        self.assertEqual(json.loads(session.context_json)["allowed_fields"]["email"], "string")
        rendered = load_workbook(BytesIO(session.preview_attachment_id.raw), data_only=False)
        try:
            self.assertEqual(rendered.active["A1"].value, target.email)
        finally:
            rendered.close()

    def test_office_retriever_allows_acl_readable_records_before_prepare(self):
        thread, _attachment, user_message = self._office_message("Fill the workbook from this parent")
        parent = self.env["res.partner"].create(
            {"name": "Pre-session parent " + uuid4().hex, "company_id": self.env.company.id}
        )
        children = self.env["res.partner"].create([
            {"name": "Pre-session child A " + uuid4().hex, "parent_id": parent.id},
            {"name": "Pre-session child B " + uuid4().hex, "parent_id": parent.id},
        ])
        unrelated = self.env["res.partner"].create(
            {"name": "Unretrieved parent " + uuid4().hex, "company_id": self.env.company.id}
        )
        retriever = self.env["llm.tool"].with_context(message=user_message)

        rows = retriever.odoo_record_retriever_execute(
            "res.partner", [["parent_id", "=", parent.id]], ["id", "name", "parent_id"], 10
        )
        exact_unretrieved = retriever.odoo_record_retriever_execute(
            "res.partner", [["id", "=", unrelated.id]], ["id", "name"], 1
        )
        self.assertEqual({row["id"] for row in rows}, set(children.ids))
        self.assertEqual({row["parent_id"][0] for row in rows}, {parent.id})
        self.assertEqual(exact_unretrieved, [{"id": unrelated.id, "name": unrelated.name}])
        self.assertFalse(self.env["office.mapping.session"].search([("thread_id", "=", thread.id)]))
    def test_office_retriever_uses_native_search_read_for_relation_queries(self):
        _thread, _attachment, user_message = self._office_message("Fill the workbook from this parent")
        parent = self.env["res.partner"].create(
            {"name": "Relation parent " + uuid4().hex, "company_id": self.env.company.id}
        )
        children = self.env["res.partner"].create([
            {"name": "Relation child A " + uuid4().hex, "parent_id": parent.id},
            {"name": "Relation child B " + uuid4().hex, "parent_id": parent.id},
        ])
        retriever = self.env["llm.tool"].with_context(message=user_message)

        child_rows = retriever.odoo_record_retriever_execute(
            "res.partner", [["id", "in", children.ids]], ["id", "name", "parent_id"], len(children)
        )
        parent_rows = retriever.odoo_record_retriever_execute(
            "res.partner", [["id", "=", parent.id]], ["id", "name", "contact_address"], 1
        )

        self.assertEqual({row["id"] for row in child_rows}, set(children.ids))
        self.assertEqual({row["parent_id"][0] for row in child_rows}, {parent.id})
        self.assertEqual(parent_rows[0]["id"], parent.id)
        self.assertEqual(parent_rows[0]["contact_address"], parent.contact_address)
    def test_native_repeat_rows_tool_runs_generic_expansion_and_m1_preview(self):
        thread = self.env["llm.thread"].create(
            {
                "name": "Repeat rows native thread " + uuid4().hex,
                "provider_id": self.provider.id,
                "model_id": self.model.id,
            }
        )
        attachment = self.env["ir.attachment"].create(
            {
                "name": "repeat-rows-native.xlsx",
                "type": "binary",
                "mimetype": XLSX_MIME,
                "raw": _repeat_rows_xlsx(),
                "company_id": self.env.company.id,
            }
        )
        upload = thread.message_post(
            body="请把关联明细填入重复行",
            llm_role="user",
            author_id=self.env.user.partner_id.id,
            attachment_ids=[attachment.id],
        )
        parent = self.env["res.partner"].create(
            {"name": "Repeat parent value", "company_id": self.env.company.id}
        )
        children = self.env["res.partner"].create([
            {"name": "Repeat value C", "parent_id": parent.id, "company_id": self.env.company.id},
            {"name": "Repeat value A", "parent_id": parent.id, "company_id": self.env.company.id},
            {"name": "Repeat value B", "parent_id": parent.id, "company_id": self.env.company.id},
        ])
        repeat_candidates = next(
            item for item in _repeat_row_collection_candidates(self.env, parent)
            if item["collection_field"] == "child_ids"
        )
        self.assertTrue(
            {"name", "contact_address"}.issubset(repeat_candidates["allowed_fields"]),
            sorted(repeat_candidates["allowed_fields"]),
        )
        retriever_result = thread.message_post(
            body="Retriever result",
            llm_role="tool",
            body_json={
                "type": "tool_execution",
                "tool_call_id": "repeat-native-parent-call",
                "tool_call": {"function": {"name": "odoo_record_retriever", "arguments": "{}"}},
                "tool_name": "odoo_record_retriever",
                "arguments": {"model": "res.partner", "domain": [["id", "=", parent.id]], "fields": ["name"], "limit": 1},
                "status": "completed",
                "result": [{"id": parent.id, "name": parent.name}],
            },
        )
        tool_model = self.env["office.mapping.tool"].with_context(message=retriever_result)
        context = tool_model.office_prepare_context("res.partner", parent.id)
        session = self.env["office.mapping.session"].browse(context["session_id"])
        result = tool_model.office_save_mapping_preview(
            session.id,
            session.revision,
            {
                "schema_version": "m2.mapping-proposal.v1",
                "mappings": [
                    {"element_id": "xlsx:Data!B1", "source_field": "name", "value_type": "string"}
                ],
                "clarifications": [
                    {
                        "element_id": "xlsx:Data!B4",
                        "reason_code": "missing_source",
                        "question": "This cell is already handled by the repeat-row column mapping.",
                    },
                    {
                        "element_id": "xlsx:Data!F6",
                        "reason_code": "missing_source",
                        "question": "This blank neighbor belongs to the template's formula summary row.",
                    }
                ],
                "skipped_targets": ["xlsx:Data!B4", "xlsx:Data!B6", "xlsx:Data!C6"],
            },
            repeat_rows=[
                {
                    "collection_field": "child_ids",
                    "sheet": "Data",
                    "start_row": 4,
                    "sort_by": "name",
                    "sort_direction": "asc",
                    "columns": [
                        {"column": "B", "source_field": "name"},
                        {"column": "C", "fallback_fields": ["name", "contact_address"]},
                        # Provider tool calls sometimes omit Excel's leading
                        # equals sign. The service should canonicalize the
                        # safe arithmetic before validation and rendering.
                        {"column": "D", "formula": "1*3+E{row}*0"},
                    ],
                }
            ],
        )
        refreshed_context = tool_model.office_prepare_context("res.partner", parent.id)

        self.assertEqual(result["status"], "preview_ready", result)
        saved_rules = json.loads(session.mapping_rules_json)
        self.assertNotIn("xlsx:Data!F7", [item["element_id"] for item in saved_rules["clarifications"]])
        self.assertIn("xlsx:Data!F7", saved_rules["skipped_targets"])
        self.assertEqual(session.source_message_id, upload)
        self.assertTrue(session.preview_attachment_id.name.startswith("preview_"))
        self.assertTrue(session.preview_attachment_id.name.endswith(".xlsx"))
        self.assertEqual(session.preview_attachment_id.mimetype, XLSX_MIME)
        rendered = load_workbook(BytesIO(session.preview_attachment_id.raw), data_only=False)
        try:
            sheet = rendered["Data"]
            self.assertEqual(sheet["B1"].value, parent.name)
            self.assertEqual(
                [sheet[f"B{row}"].value for row in range(4, 7)],
                sorted(child.name for child in children),
            )
            self.assertEqual(
                [sheet[f"C{row}"].value for row in range(4, 7)],
                sorted(child.name for child in children),
            )
            self.assertEqual(
                [sheet[f"D{row}"].value for row in range(4, 7)],
                [f"=1*3+E{row}*0" for row in range(4, 7)],
            )
            self.assertEqual(sheet["E7"].value, "=SUM(E4:E6)")
        finally:
            rendered.close()

        # A later repeat-row patch that omits ordering preserves the already
        # saved sort rule; omission is not an implicit unsort operation.
        second_result = tool_model.office_save_mapping_preview(
            session.id,
            session.revision,
            {
                "schema_version": "m2.mapping-proposal.v1",
                "mappings": [
                    {"element_id": "xlsx:Data!B1", "source_field": "name", "value_type": "string"}
                ],
                "clarifications": [],
                "skipped_targets": [],
            },
            repeat_rows=[
                {
                    "collection_field": "child_ids",
                    "sheet": "Data",
                    "start_row": 4,
                    "columns": [
                        {"column": "B", "source_field": "name"},
                        {"column": "C", "fallback_fields": ["name", "contact_address"]},
                        {"column": "D", "formula": "1*3+E{row}*0"},
                    ],
                }
            ],
        )
        self.assertIn(second_result["status"], {"preview_ready", "unchanged"}, second_result)
        refreshed_context = tool_model.office_prepare_context("res.partner", parent.id)
        self.assertEqual(
            refreshed_context["current_repeat_rows"][0]["columns"],
            [
                {"column": "B", "source_field": "name"},
                {"column": "C", "fallback_fields": ["name", "contact_address"]},
                {"column": "D", "formula": "=1*3+E{row}*0"},
            ],
        )
        self.assertEqual(refreshed_context["current_repeat_rows"][0]["sort_by"], "name")
        self.assertEqual(refreshed_context["current_repeat_rows"][0]["sort_direction"], "asc")
        final_preview = load_workbook(BytesIO(session.preview_attachment_id.raw), data_only=False)
        try:
            self.assertEqual(
                [final_preview["Data"][f"B{row}"].value for row in range(4, 7)],
                sorted(child.name for child in children),
            )
        finally:
            final_preview.close()

    def test_native_repeat_rows_preserves_zero_numeric_values(self):
        thread = self.env["llm.thread"].create(
            {
                "name": "Repeat zero numeric thread " + uuid4().hex,
                "provider_id": self.provider.id,
                "model_id": self.model.id,
            }
        )
        attachment = self.env["ir.attachment"].create(
            {
                "name": "repeat-zero-numeric.xlsx",
                "type": "binary",
                "mimetype": XLSX_MIME,
                "raw": _zero_numeric_repeat_rows_xlsx(),
                "company_id": self.env.company.id,
            }
        )
        thread.message_post(
            body="Map the child names and zero-valued numeric field.",
            llm_role="user",
            author_id=self.env.user.partner_id.id,
            attachment_ids=[attachment.id],
        )
        parent = self.env["res.partner"].create(
            {"name": "Zero parent " + uuid4().hex, "company_id": self.env.company.id}
        )
        children = self.env["res.partner"].create([
            {"name": "Zero child A " + uuid4().hex, "parent_id": parent.id, "color": 0},
            {"name": "Zero child B " + uuid4().hex, "parent_id": parent.id, "color": 0},
        ])
        candidate = next(
            item for item in _repeat_row_collection_candidates(self.env, parent)
            if item["collection_field"] == "child_ids"
        )
        self.assertEqual(candidate["allowed_fields"].get("color"), "number")
        retriever_result = thread.message_post(
            body="Retriever result",
            llm_role="tool",
            body_json={
                "type": "tool_execution",
                "tool_call_id": "repeat-zero-parent-call",
                "tool_call": {"function": {"name": "odoo_record_retriever", "arguments": "{}"}},
                "tool_name": "odoo_record_retriever",
                "arguments": {
                    "model": "res.partner", "domain": [["id", "=", parent.id]],
                    "fields": ["name"], "limit": 1,
                },
                "status": "completed",
                "result": [{"id": parent.id, "name": parent.name}],
            },
        )
        tool_model = self.env["office.mapping.tool"].with_context(message=retriever_result)
        context = tool_model.office_prepare_context("res.partner", parent.id)
        session = self.env["office.mapping.session"].browse(context["session_id"])
        result = tool_model.office_save_mapping_preview(
            session.id,
            session.revision,
            {
                "schema_version": "m2.mapping-proposal.v1",
                "mappings": [
                    {"element_id": "xlsx:Data!B1", "source_field": "name", "value_type": "string"}
                ],
                "clarifications": [],
                "skipped_targets": [],
            },
            repeat_rows=[
                {
                    "collection_field": "child_ids",
                    "sheet": "Data",
                    "start_row": 4,
                    "columns": [
                        {"column": "B", "source_field": "name"},
                        {"column": "C", "source_field": "color"},
                    ],
                }
            ],
        )

        self.assertEqual(result["status"], "preview_ready", result)
        rendered = load_workbook(BytesIO(session.preview_attachment_id.raw), data_only=False)
        try:
            sheet = rendered["Data"]
            self.assertEqual(sheet["B1"].value, parent.name)
            self.assertEqual(
                [sheet[f"B{row}"].value for row in (4, 5)], [child.name for child in children]
            )
            self.assertEqual([sheet[f"C{row}"].value for row in (4, 5)], [0, 0])
        finally:
            rendered.close()

    def test_repeat_context_allows_explicit_overwrite_of_existing_formula_columns(self):
        thread = self.env["llm.thread"].create(
            {
                "name": "Repeat formula guard thread " + uuid4().hex,
                "provider_id": self.provider.id,
                "model_id": self.model.id,
            }
        )
        attachment = self.env["ir.attachment"].create(
            {
                "name": "repeat-formula-guard.xlsx",
                "type": "binary",
                "mimetype": XLSX_MIME,
                "raw": _formula_repeat_rows_xlsx(),
                "company_id": self.env.company.id,
            }
        )
        thread.message_post(
            body="Fill the related rows",
            llm_role="user",
            author_id=self.env.user.partner_id.id,
            attachment_ids=[attachment.id],
        )
        parent = self.env["res.partner"].create(
            {"name": "Repeat formula parent " + uuid4().hex, "company_id": self.env.company.id}
        )
        children = self.env["res.partner"].create([
            {"name": "Repeat formula child A", "parent_id": parent.id, "company_id": self.env.company.id},
            {"name": "Repeat formula child B", "parent_id": parent.id, "company_id": self.env.company.id},
            {"name": "Repeat formula child C", "parent_id": parent.id, "company_id": self.env.company.id},
        ])
        retriever_result = thread.message_post(
            body="Retriever result",
            llm_role="tool",
            body_json={
                "type": "tool_execution",
                "tool_call_id": "repeat-formula-guard-call",
                "tool_call": {"function": {"name": "odoo_record_retriever", "arguments": "{}"}},
                "tool_name": "odoo_record_retriever",
                "arguments": {"model": "res.partner", "domain": [["id", "=", parent.id]], "fields": ["name"], "limit": 1},
                "status": "completed",
                "result": [{"id": parent.id, "name": parent.name}],
            },
        )
        tool_model = self.env["office.mapping.tool"].with_context(message=retriever_result)
        context = tool_model.office_prepare_context("res.partner", parent.id)
        session = self.env["office.mapping.session"].browse(context["session_id"])
        result = tool_model.office_save_mapping_preview(
            session.id,
            session.revision,
            {
                "schema_version": "m2.mapping-proposal.v1",
                "mappings": [
                    {"element_id": "xlsx:Data!B1", "source_field": "name", "value_type": "string"}
                ],
                "clarifications": [],
                "skipped_targets": [],
            },
            repeat_rows=[
                {
                    "collection_field": "child_ids",
                    "sheet": "Data",
                    "start_row": 4,
                    "columns": [
                        {"column": "B", "source_field": "name"},
                        {"column": "C", "formula": "=B{row}*2"},
                    ],
                }
            ],
        )

        self.assertEqual(len(children), 3)
        self.assertIn(
            "xlsx:Data!C4",
            {item["element_id"] for item in context["mapping_limits"]["template_formula_cells"]},
        )
        self.assertIn("template_formula_cells", context["mapping_limits"])
        self.assertEqual(result["status"], "preview_ready", result)
        rendered = load_workbook(BytesIO(session.preview_attachment_id.raw), data_only=False)
        try:
            self.assertEqual(
                [rendered["Data"][f"C{row}"].value for row in range(4, 7)],
                [f"=B{row}*2" for row in range(4, 7)],
            )
            self.assertEqual(rendered["Data"]["C7"].value, "=SUM(C4:C6)")
        finally:
            rendered.close()

        # A repeat column initially populated by formulas remains a valid
        # target for a later explicit literal-value patch. The initial
        # operation choice must not permanently narrow the cell's type.
        session.invalidate_recordset(["context_json"])
        persisted_manifest = json.loads(session.context_json)["target_manifest"]
        c4_target = next(item for item in persisted_manifest if item["element_id"] == "xlsx:Data!C4")
        self.assertIn("number", c4_target["allowed_value_types"])
        self.assertIn("formula", c4_target["allowed_value_types"])
        literal_patch = tool_model.office_save_mapping_preview(
            session.id,
            session.revision,
            {
                "schema_version": "m2.mapping-proposal.v1",
                "mappings": [
                    {"element_id": f"xlsx:Data!C{row}", "literal_value": value, "value_type": "number"}
                    for row, value in zip(range(4, 7), (10, 11, 12))
                ],
                "clarifications": [],
                "skipped_targets": [],
            },
        )
        self.assertEqual(literal_patch["status"], "preview_ready", literal_patch)
        rendered = load_workbook(BytesIO(session.preview_attachment_id.raw), data_only=False)
        try:
            self.assertEqual(
                [rendered["Data"][f"B{row}"].value for row in range(4, 7)],
                [child.name for child in children],
            )
            self.assertEqual(
                [rendered["Data"][f"C{row}"].value for row in range(4, 7)],
                [10, 11, 12],
            )
            self.assertEqual(rendered["Data"]["C7"].value, "=SUM(C4:C6)")
        finally:
            rendered.close()

        # Clears inside the expanded repeat band are already expressed in
        # post-expansion coordinates. They must remain on the data rows and
        # must not shift onto (and clear) the moved summary formula.
        clear_result = tool_model.office_save_mapping_preview(
            session.id,
            session.revision,
            {
                "schema_version": "m2.mapping-proposal.v1",
                "mappings": [
                    {"element_id": "xlsx:Data!B1", "source_field": "name", "value_type": "string"}
                ],
                "clarifications": [],
                "skipped_targets": [],
                "clear_targets": ["xlsx:Data!C4", "xlsx:Data!C5", "xlsx:Data!C6"],
            },
            repeat_rows=[
                {
                    "collection_field": "child_ids",
                    "sheet": "Data",
                    "start_row": 4,
                    "columns": [
                        {"column": "B", "source_field": "name"},
                        {"column": "C", "formula": "=B{row}*2"},
                    ],
                }
            ],
        )
        self.assertEqual(clear_result["status"], "preview_ready", clear_result)
        cleared_preview_id = session.preview_attachment_id.id
        rendered = load_workbook(BytesIO(session.preview_attachment_id.raw), data_only=False)
        try:
            self.assertEqual(
                [rendered["Data"][f"C{row}"].value for row in range(4, 7)],
                [None, None, None],
            )
            self.assertEqual(rendered["Data"]["C7"].value, "=SUM(C4:C6)")
        finally:
            rendered.close()

        # A row-number token outside a cell reference must not silently
        # become a constant calculation or replace the valid preview.
        existing_preview_id = session.preview_attachment_id.id
        existing_revision = session.revision
        invalid_formula = tool_model.office_save_mapping_preview(
            session.id,
            existing_revision,
            {
                "schema_version": "m2.mapping-proposal.v1",
                "mappings": [
                    {"element_id": "xlsx:Data!B1", "source_field": "name", "value_type": "string"}
                ],
                "clarifications": [],
                "skipped_targets": [],
            },
            repeat_rows=[
                {
                    "collection_field": "child_ids",
                    "sheet": "Data",
                    "start_row": 4,
                    "columns": [
                        {"column": "B", "source_field": "name"},
                        {"column": "C", "formula": "{row}*{row}*2"},
                    ],
                }
            ],
        )
        self.assertEqual(invalid_formula["status"], "invalid")
        self.assertIn("repeat_rows_not_authorized_or_not_renderable", invalid_formula["errors"])
        self.assertEqual(session.revision, existing_revision)
        self.assertEqual(session.preview_attachment_id.id, existing_preview_id)
        self.assertEqual(existing_preview_id, cleared_preview_id)

        # The live Provider schema exposes format_patches beside proposal.
        # They must reach the tool executor instead of being silently ignored.
        column_operations = tool_model.office_save_mapping_preview(
            session.id,
            session.revision,
            {
                "schema_version": "m2.mapping-proposal.v1",
                "mappings": [
                    {"element_id": "xlsx:Data!B1", "source_field": "name", "value_type": "string"}
                ],
                "clarifications": [],
                "skipped_targets": [],
            },
            format_patches=[
                {"element_id": "xlsx:Data!B4", "number_format": "0.00"}
            ],
        )
        self.assertEqual(column_operations["status"], "preview_ready", column_operations)
        rendered = load_workbook(BytesIO(session.preview_attachment_id.raw), data_only=False)
        try:
            self.assertEqual(rendered["Data"]["B1"].value, parent.name)
            self.assertEqual(rendered["Data"]["B4"].value, children[0].name)
            self.assertEqual(rendered["Data"]["B4"].number_format, "0.00")
            self.assertEqual(
                [rendered["Data"][f"C{row}"].value for row in range(4, 7)],
                [None, None, None],
            )
            self.assertEqual(rendered["Data"]["C7"].value, "=SUM(C4:C6)")
        finally:
            rendered.close()

    def test_top_level_clear_column_reaches_preview_executor(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Orders"
        sheet["A3"] = "Order"
        sheet["B3"] = "Partner"
        sheet["C3"] = "Amount"
        sheet["A4"] = "SO-1"
        sheet["C4"] = 10
        sheet["A5"] = "SO-2"
        sheet["C5"] = 20
        output = BytesIO()
        workbook.save(output)
        workbook.close()

        thread, _attachment, upload = self._office_message("Update the partner and clear amounts", output.getvalue())
        target = self.env["res.partner"].create(
            {"name": "Top-level operation partner " + uuid4().hex, "company_id": self.env.company.id}
        )
        tool = self.env["office.mapping.tool"].with_context(message=upload)
        context = tool.office_prepare_context("res.partner", target.id)
        session = self.env["office.mapping.session"].browse(context["session_id"])

        result = tool.office_save_mapping_preview(
            session.id,
            session.revision,
            {
                "schema_version": "m2.mapping-proposal.v1",
                "mappings": [
                    {"element_id": "xlsx:Orders!B4", "source_field": "name", "value_type": "string"}
                ],
                "clarifications": [],
                "skipped_targets": [],
            },
            clear_columns=[{"sheet": "Orders", "column": "C"}],
            format_patches=[
                {"element_id": "xlsx:Orders!C4", "number_format": "0.00"}
            ],
        )
        self.assertEqual(result["status"], "preview_ready", result)
        self.assertTrue(result["attachment_posted_to_thread"])
        rendered = load_workbook(BytesIO(session.preview_attachment_id.raw), data_only=False)
        try:
            self.assertEqual(rendered["Orders"]["A3"].value, "Order")
            self.assertEqual(rendered["Orders"]["B3"].value, "Partner")
            self.assertEqual(rendered["Orders"]["C3"].value, "Amount")
            self.assertEqual(rendered["Orders"]["A4"].value, "SO-1")
            self.assertEqual(rendered["Orders"]["B4"].value, target.name)
            self.assertIsNone(rendered["Orders"]["C4"].value)
            self.assertEqual(rendered["Orders"]["C4"].number_format, "0.00")
            self.assertIsNone(rendered["Orders"]["C5"].value)
            self.assertEqual(rendered["Orders"]["A5"].value, "SO-2")
        finally:
            rendered.close()

    def test_explicit_clear_renders_blank_and_ignored_formula_skip_preserves_formula(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Data"
        sheet["F16"] = "old order number"
        sheet.merge_cells("E17:H17")
        sheet["E17"] = "old merged placeholder"
        sheet["F18"] = "old legacy-required placeholder"
        sheet["F24"] = "=SUM(F20:F23)"
        sheet["F25"] = "=SUM(F20:F24)"
        output = BytesIO()
        workbook.save(output)
        workbook.close()

        thread = self.env["llm.thread"].create({
            "name": "Explicit clear test " + uuid4().hex,
            "provider_id": self.provider.id,
            "model_id": self.model.id,
        })
        attachment = self.env["ir.attachment"].create({
            "name": "clear-target-test-" + uuid4().hex + ".xlsx",
            "type": "binary",
            "mimetype": XLSX_MIME,
            "raw": output.getvalue(),
            "company_id": self.env.company.id,
        })
        upload = thread.message_post(
            body="Put the order number in F16 and clear F17.",
            llm_role="user",
            author_id=self.env.user.partner_id.id,
            attachment_ids=[attachment.id],
        )
        target = self.env["res.partner"].create({"name": "S05457", "company_id": self.env.company.id})
        tool_message = thread.message_post(
            body="Retriever result",
            llm_role="tool",
            body_json={
                "type": "tool_execution",
                "tool_call_id": "explicit-clear-test-call",
                "tool_call": {"function": {"name": "odoo_record_retriever", "arguments": "{}"}},
                "tool_name": "odoo_record_retriever",
                "arguments": {
                    "model": "res.partner",
                    "domain": [["id", "=", target.id]],
                    "fields": ["id", "name"],
                    "limit": 1,
                },
                "status": "completed",
                "result": [{"id": target.id, "name": target.name}],
            },
        )
        inspection = inspect_document(
            attachment.raw, attachment.name, attachment.mimetype, _resource_budget()
        )
        manifest, visible_text = _template_context(inspection)
        created = create_session(
            self.env,
            thread_id=thread.id,
            source_message_id=upload.id,
            source_attachment_id=attachment.id,
            target_model="res.partner",
            target_record_id=target.id,
        )
        session = self.env["office.mapping.session"].browse(created["session_id"])
        set_mapping_context(self.env, session.id, manifest, {"name": "string"}, template_text=visible_text)
        # Simulate a persisted pre-fix Session whose real, writable F18 target
        # was marked required. The service must now treat the user's omission
        # as an explicit blank rather than preserving that stale requirement.
        context = json.loads(session.context_json)
        legacy_required = next(
            item for item in context["target_manifest"]
            if item["element_id"] == "xlsx:Data!F18"
        )
        legacy_required["required"] = True
        legacy_required["approved_to_skip"] = False
        session._set_context_from_service(json.dumps(context, ensure_ascii=False))

        tool = self.env["office.mapping.tool"].with_context(message=tool_message)
        result = tool.office_save_mapping_preview(
            session.id,
            session.revision,
            {
                "schema_version": "m2.mapping-proposal.v1",
                "mappings": [{
                    "element_id": "xlsx:Data!F16",
                    "source_field": "name",
                    "value_type": "string",
                }, {
                    # The compact provider form is an explicit blank write.
                    "element_id": "xlsx:Data!F17",
                    "value": "",
                }],
                "clarifications": [],
                "skipped_targets": ["xlsx:Data!F24", "xlsx:Data!F25", "xlsx:Data!Z999"],
                "clear_targets": ["xlsx:Data!F24"],
            },
        )

        self.assertEqual(result["status"], "preview_ready", result)
        rules = json.loads(session.mapping_rules_json)
        self.assertEqual(rules["clear_targets"], ["xlsx:Data!E17", "xlsx:Data!F18", "xlsx:Data!F24"])
        self.assertEqual([item["element_id"] for item in rules["mappings"]], ["xlsx:Data!F16"])
        self.assertEqual(rules["skipped_targets"], [])
        self.assertNotIn("xlsx:Data!F24", rules["skipped_targets"])
        self.assertNotIn("xlsx:Data!F25", rules["skipped_targets"])
        self.assertIn("xlsx:Data!F18", rules["clear_targets"])
        rendered = load_workbook(BytesIO(session.preview_attachment_id.raw), data_only=False)
        try:
            self.assertEqual(rendered["Data"]["F16"].value, "S05457")
            self.assertIsNone(rendered["Data"]["E17"].value)
            self.assertIsNone(rendered["Data"]["F17"].value)
            self.assertIsNone(rendered["Data"]["F18"].value)
            self.assertIsNone(rendered["Data"]["F24"].value)
            self.assertEqual(rendered["Data"]["F25"].value, "=SUM(F20:F24)")
        finally:
            rendered.close()

    def test_new_office_upload_is_not_blocked_by_an_older_active_session(self):
        thread, old_attachment, old_message = self._office_message("Old workbook request")
        old_target = self.env["res.partner"].create(
            {"name": "Old Office target " + uuid4().hex, "company_id": self.env.company.id}
        )
        from ..services.mapping_service import create_session

        create_session(
            self.env,
            thread_id=thread.id,
            source_message_id=old_message.id,
            source_attachment_id=old_attachment.id,
            target_model="res.partner",
            target_record_id=old_target.id,
        )

        new_attachment = self.env["ir.attachment"].create(
            {
                "name": "new-office-" + uuid4().hex + ".xlsx",
                "type": "binary",
                "mimetype": XLSX_MIME,
                "raw": _xlsx(),
                "company_id": self.env.company.id,
            }
        )
        latest_upload = thread.message_post(
            body="Fill the new workbook",
            llm_role="user",
            author_id=self.env.user.partner_id.id,
            attachment_ids=[new_attachment.id],
        )
        self.assertFalse(thread._office_active_session())

        retriever = self.env["llm.tool"].with_context(message=latest_upload)
        rows = retriever.odoo_record_retriever_execute(
            model="res.partner",
            domain=[["name", "=", old_target.name]],
            fields=["id", "name"],
            limit=1,
        )
        self.assertEqual([row["id"] for row in rows], [old_target.id])

        retriever_result = thread.message_post(
            body="Retriever result",
            llm_role="tool",
            body_json={
                "type": "tool_execution",
                "tool_call_id": "new-upload-retriever-call",
                "tool_call": {"function": {"name": "odoo_record_retriever", "arguments": "{}"}},
                "tool_name": "odoo_record_retriever",
                "arguments": {
                    "model": "res.partner",
                    "domain": [["name", "=", old_target.name]],
                    "fields": ["id", "name"],
                    "limit": 1,
                },
                "status": "completed",
                "result": rows,
            },
        )
        context = self.env["office.mapping.tool"].with_context(
            message=retriever_result
        ).office_prepare_context("res.partner", old_target.id)
        new_session = self.env["office.mapping.session"].browse(context["session_id"])
        self.assertEqual(new_session.source_message_id, latest_upload)
        self.assertEqual(new_session.source_attachment_id, new_attachment)

    def test_office_retriever_uses_current_user_permissions_without_environment_gate(self):
        _thread, _attachment, message = self._office_message("Fill the workbook")
        retriever = self.env["llm.tool"].with_context(message=message)
        retrieval_model = "sale.order" if "sale.order" in self.env.registry.models else "res.partner"
        result = retriever.odoo_record_retriever_execute(
            retrieval_model,
            [["name", "=", "NO-SUCH-OFFICE-RECORD"]],
            ["name"],
            1,
        )
        self.assertEqual(result, [])

    def test_office_thread_uses_native_tools_and_prepare_binds_current_upload_and_record(self):
        instruction = "用联系人记录填这个工作簿"
        thread, _attachment, user_message = self._office_message(instruction)
        tool_names = set(thread._office_bind_tools().mapped("name"))
        self.assertEqual(
            tool_names,
            {
                "office_prepare_context",
                "office_save_mapping_preview",
                "office_restore_proposal_revision",
                "office_finalize",
                "odoo_record_retriever",
            },
        )
        schemas = {
            tool.name: tool.get_input_schema()
            for tool in thread.tool_ids.filtered(lambda item: item.name in tool_names)
        }
        self.assertIn("model", schemas["odoo_record_retriever"]["properties"])
        self.assertIn("model", schemas["odoo_record_retriever"]["required"])
        self.assertIn("target_model", schemas["office_prepare_context"]["properties"])
        self.assertIn("proposal", schemas["office_save_mapping_preview"]["properties"])
        self.assertIn("session_id", schemas["office_finalize"]["properties"])
        proposal_schema = schemas["office_save_mapping_preview"]["properties"]["proposal"]
        self.assertEqual(
            proposal_schema["required"],
            ["schema_version", "mappings", "clarifications", "skipped_targets"],
        )
        self.assertIn("clear_targets", proposal_schema["properties"])
        self.assertNotIn("clear_targets", proposal_schema["required"])
        mapping_schema = proposal_schema["properties"]["mappings"]["items"]
        self.assertEqual(mapping_schema["required"], ["element_id"])
        self.assertEqual(mapping_schema["properties"]["value"]["enum"], [""])
        self.assertIn("literal_value", mapping_schema["properties"])
        self.assertFalse(mapping_schema["additionalProperties"])
        kwargs = thread._prepare_chat_kwargs(thread.get_llm_messages(), use_streaming=True)
        # This method preserves the value supplied by llm_assistant; the
        # Office-specific non-streaming choice is made at the native response
        # handler boundary in LLMThread._generate_assistant_response.
        self.assertTrue(kwargs["stream"])
        self.assertEqual(set(kwargs["tools"].mapped("name")), tool_names)
        self.assertEqual(kwargs["messages"], thread.get_llm_messages())

        office_system_message = next(
            message
            for message in kwargs["prepend_messages"]
            if message.get("role") == "system" and "For an initial Office mapping request" in message.get("content", "")
        )
        self.assertIn("that request authorizes a draft preview", office_system_message["content"])
        self.assertIn("Do not ask the user to separately approve or confirm a preview", office_system_message["content"])
        self.assertIn("ask one concise natural-language question in this chat", office_system_message["content"])
        self.assertIn("Never direct the user to a record-picker dialog", office_system_message["content"])
        self.assertIn("request at least two results", office_system_message["content"])
        self.assertIn("no match or multiple matches", office_system_message["content"])
        self.assertIn("fields argument accepts only direct fields", office_system_message["content"])
        self.assertIn("Odoo's current-user ACLs", office_system_message["content"])
        self.assertIn("continue that Session and its saved Proposal", office_system_message["content"])
        self.assertIn("literal_value", office_system_message["content"])
        self.assertNotIn("Retriever constrains the result to the current Session", office_system_message["content"])
        self.assertIn("Call office_finalize only after the user explicitly confirms", office_system_message["content"])
        self.assertIn("returns status=finalized", office_system_message["content"])

        target = self.env["res.partner"].create(
            {"name": "Authorized Office target", "company_id": self.env.company.id}
        )
        # This tool result stands in for the preceding Retriever tool result in
        # this isolated handler test; it is not evidence of a live LLM call.
        retriever_result = thread.message_post(
            body="Retriever result",
            llm_role="tool",
            body_json={
                "type": "tool_execution",
                "tool_call_id": "test-retriever-call",
                "tool_call": {"function": {"name": "odoo_record_retriever", "arguments": "{}"}},
                "tool_name": "odoo_record_retriever",
                "arguments": {"model": "res.partner", "domain": [["name", "=", target.name]], "fields": ["name"], "limit": 1},
                "status": "completed",
                "result": [{"id": target.id, "name": target.name}],
            },
        )
        context = self.env["office.mapping.tool"].with_context(message=retriever_result).office_prepare_context(
            "res.partner", target.id
        )
        session = self.env["office.mapping.session"].browse(context["session_id"])
        self.assertEqual(session.thread_id, thread)
        self.assertEqual(session.source_message_id, user_message)
        self.assertEqual(session.source_attachment_id, user_message.attachment_ids)
        self.assertEqual(session.target_record_id, target.id)
        self.assertIn("name", context["allowed_fields"])
        self.assertEqual(context["allowed_fields"]["name"]["type"], "string")
        self.assertEqual(
            context["allowed_fields"]["name"]["label"],
            self.env["res.partner"]._fields["name"].string,
        )

    def test_prepare_context_accepts_selected_record_ids_without_anchor_id(self):
        """A selected record set needs no redundant singular ID from the model."""
        thread, _attachment, user_message = self._office_message(
            "Fill the selected business records into repeated rows", raw=_repeat_rows_xlsx()
        )
        records = self.env["res.partner"].create([
            {"name": "Batch anchor %s" % uuid4().hex, "company_id": self.env.company.id},
            {"name": "Batch row %s" % uuid4().hex, "company_id": self.env.company.id},
        ])
        tool = self.env["office.mapping.tool"].with_context(message=user_message)

        context = tool.office_prepare_context(
            target_model="res.partner", target_record_ids=records.ids
        )

        session = self.env["office.mapping.session"].browse(context["session_id"])
        self.assertEqual(session.target_record_id, records[0].id)
        self.assertEqual(
            json.loads(session.context_json)["selected_record_ids"], records.ids
        )
        prepare_tool = thread._office_bind_tools().filtered(
            lambda item: item.name == "office_prepare_context"
        )
        schema = prepare_tool.get_input_schema()
        self.assertNotIn("target_record_id", schema.get("required", []))
        self.assertIn("target_record_ids", schema["properties"])

    def test_resumed_thread_with_bound_office_tools_uses_gpt5_compatible_reasoning_effort(self):
        thread = self.env["llm.thread"].create(
            {
                "name": "Resumed Office tool thread " + uuid4().hex,
                "provider_id": self.provider.id,
                "model_id": self.model.id,
            }
        )
        thread._office_bind_tools()

        # This reproduces a resumed Thread whose Office tools remain bound
        # after its Session is no longer active. Native llm_assistant still
        # passes those tools to the Provider, so GPT-5 must not inherit an
        # unsupported model-level reasoning_effort value.
        self.assertFalse(thread._office_is_active())
        with patch.object(
            type(self.model),
            "chat",
            autospec=True,
            return_value={"content": "Native Office tool continuation", "tool_calls": []},
        ) as provider_call:
            events = list(thread._generate_assistant_response())

        self.assertTrue(events)
        kwargs = provider_call.call_args.kwargs
        self.assertFalse(kwargs["stream"])
        self.assertEqual(kwargs["reasoning_effort"], "none")
        self.assertIn("odoo_record_retriever", kwargs["tools"].mapped("name"))

    def test_prepare_context_refreshes_server_field_schema_without_losing_proposal_revision(self):
        thread, attachment, upload = self._office_message("用联系人记录填这个工作簿")
        target = self.env["res.partner"].create(
            {"name": "Address context refresh " + uuid4().hex, "company_id": self.env.company.id}
        )
        retriever_result = thread.message_post(
            body="Retriever result",
            llm_role="tool",
            body_json={
                "type": "tool_execution",
                "tool_call_id": "address-context-refresh-call",
                "tool_call": {"function": {"name": "odoo_record_retriever", "arguments": "{}"}},
                "tool_name": "odoo_record_retriever",
                "arguments": {
                    "model": "res.partner",
                    "domain": [["id", "=", target.id]],
                    "fields": ["name"],
                    "limit": 1,
                },
                "status": "completed",
                "result": [{"id": target.id, "name": target.name}],
            },
        )
        tool_model = self.env["office.mapping.tool"].with_context(message=retriever_result)
        first_context = tool_model.office_prepare_context("res.partner", target.id)
        session = self.env["office.mapping.session"].browse(first_context["session_id"])
        original_revision = session.revision
        original_rules = session.mapping_rules_json
        original_state = session.state

        # A completed repeat-row setup can contain targets created by M1
        # row expansion that are absent from the original uploaded XLSX.
        # Refreshing only the field dictionary must preserve this expanded
        # manifest and its server-owned group.
        expanded_manifest = [
            *first_context["target_manifest"],
            *[
                {
                    "element_id": f"xlsx:Sheet!B{row_number}",
                    "required": True,
                    "writable": True,
                    "allowed_value_types": ["string"],
                    "approved_to_skip": False,
                }
                for row_number in (23, 24)
            ],
        ]
        repeat_group = {
            "group_id": "repeat_rows",
            "collection_field": "child_ids",
            "relation_model": "res.partner",
            "row_count": 2,
            "target_rows": [
                {
                    "row_index": index,
                    "targets": [
                        {"column_id": "B", "element_id": f"xlsx:Sheet!B{23 + index}"}
                    ],
                }
                for index in range(2)
            ],
            "allowed_fields": {"name": "string"},
        }

        # Simulate a Session created before a newly authorized field path
        # (such as contact_address) was added to server discovery.
        set_mapping_context(
            self.env,
            session.id,
            expanded_manifest,
            {"name": "string"},
            mapping_groups=[repeat_group],
            template_text=first_context["template_text"],
        )
        refreshed = tool_model.office_prepare_context("res.partner", target.id)

        self.assertEqual(session.source_message_id, upload)
        self.assertEqual(session.source_attachment_id, attachment)
        self.assertIn("contact_address", refreshed["allowed_fields"])
        self.assertEqual(session.revision, original_revision)
        self.assertEqual(session.mapping_rules_json, original_rules)
        self.assertEqual(session.state, original_state)
        self.assertTrue(
            {"xlsx:Sheet!B23", "xlsx:Sheet!B24"}.issubset(
                {item["element_id"] for item in refreshed["target_manifest"]}
            )
        )
        refreshed_context = json.loads(session.context_json)
        self.assertEqual(refreshed_context["mapping_groups"][0]["collection_field"], "child_ids")
        self.assertEqual(refreshed_context["mapping_groups"][0]["row_count"], 2)

    def test_office_tool_provider_schemas_include_required_arguments(self):
        thread = self.env["llm.thread"].create(
            {
                "name": "Native Office schema thread " + uuid4().hex,
                "provider_id": self.provider.id,
                "model_id": self.model.id,
            }
        )
        tools = thread._office_bind_tools()
        schemas = {tool.name: tool.get_input_schema() for tool in tools}
        self.assertIn("model", schemas["odoo_record_retriever"]["properties"])
        self.assertIn("model", schemas["odoo_record_retriever"]["required"])
        for argument in ("offset", "order", "include_pagination"):
            self.assertIn(argument, schemas["odoo_record_retriever"]["properties"])
        self.assertIn("target_model", schemas["office_prepare_context"]["properties"])
        self.assertNotIn("target_record_id", schemas["office_prepare_context"].get("required", []))
        self.assertIn("target_record_ids", schemas["office_prepare_context"]["properties"])
        self.assertIn("requested_fields", schemas["office_prepare_context"]["properties"])
        self.assertIn("proposal", schemas["office_save_mapping_preview"]["properties"])
        self.assertIn("repeat_rows", schemas["office_save_mapping_preview"]["properties"])
        self.assertIn("clear_columns", schemas["office_save_mapping_preview"]["properties"])
        self.assertIn("format_patches", schemas["office_save_mapping_preview"]["properties"])
        repeat_schema = schemas["office_save_mapping_preview"]["properties"]["repeat_rows"]
        self.assertEqual(repeat_schema["maxItems"], 1)
        self.assertIn("collection_field", repeat_schema["items"]["properties"])
        self.assertIn("fallback_fields", repeat_schema["items"]["properties"]["columns"]["items"]["properties"])
        self.assertIn("formula", repeat_schema["items"]["properties"]["columns"]["items"]["properties"])
        self.assertIn("source_fields", schemas["office_save_mapping_preview"]["properties"]["proposal"]["properties"]["mappings"]["items"]["properties"])
        self.assertIn("session_id", schemas["office_finalize"]["properties"])
