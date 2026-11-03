"""Native assistant flow checks; local intent routing is no longer a product path."""

import json
from contextlib import contextmanager
from io import BytesIO
from unittest.mock import Mock, patch
from uuid import uuid4

from openpyxl import Workbook
from openpyxl.styles import PatternFill
from odoo import tools
from odoo.addons.llm_assistant.models.llm_thread import LLMThread as AssistantThread
from odoo.tests import TransactionCase

from ..services.mapping_service import create_session, set_mapping_context


XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _xlsx():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Sheet1"
    sheet["A1"] = "Customer"
    sheet["B1"].fill = PatternFill(fill_type="solid", fgColor="FFFFFF")
    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


class TestOfficeNativeConversation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.provider = cls.env["llm.provider"].create(
            {"name": "Native Office conversation " + uuid4().hex, "service": "openai"}
        )
        cls.model = cls.env["llm.model"].create(
            {
                "name": "gpt-5.6-luna",
                "provider_id": cls.provider.id,
                "model_use": "multimodal",
            }
        )

    @contextmanager
    def _test_context(self):
        yield

    def _thread(self):
        return self.env["llm.thread"].create(
            {
                "name": "Native Office thread " + uuid4().hex,
                "provider_id": self.provider.id,
                "model_id": self.model.id,
            }
        )

    def _upload(self, thread, instruction):
        attachment = self.env["ir.attachment"].create(
            {
                "name": "native-office-" + uuid4().hex + ".xlsx",
                "type": "binary",
                "mimetype": XLSX_MIME,
                "raw": _xlsx(),
                "company_id": self.env.company.id,
            }
        )
        return attachment, thread.generate(
            user_message_body=instruction,
            attachment_ids=[attachment.id],
        )

    def test_office_upload_uses_one_native_user_message_and_native_provider(self):
        thread = self._thread()
        instruction = "如果订单没有仓库，b4就用本公司地址。"
        attachment = self.env["ir.attachment"].create(
            {
                "name": "native-office-" + uuid4().hex + ".xlsx",
                "type": "binary",
                "mimetype": XLSX_MIME,
                "raw": _xlsx(),
                "company_id": self.env.company.id,
            }
        )
        response = {"content": "请确认业务记录；条件回退当前不在支持范围内。"}
        with self._test_context(), patch.object(
            type(self.model), "chat", autospec=True, return_value=response
        ) as provider_call:
            events = list(thread.generate(instruction, attachment_ids=[attachment.id]))

        provider_call.assert_called_once()
        call_kwargs = provider_call.call_args.kwargs
        self.assertFalse(call_kwargs["stream"])
        messages = call_kwargs["messages"]
        user_message = messages.filtered(lambda item: item.llm_role == "user")[-1]
        self.assertEqual(tools.html2plaintext(user_message.body), instruction)
        self.assertEqual(
            user_message.openai_format_message(is_multimodal=True),
            {"role": "user", "content": instruction},
        )
        payload_text = json.dumps(
            user_message.openai_format_message(is_multimodal=True), ensure_ascii=False
        )
        encoded = attachment.datas
        if isinstance(encoded, bytes):
            encoded = encoded.decode("ascii")
        self.assertNotIn(encoded, payload_text)
        self.assertNotIn("base64", payload_text.lower())
        self.assertEqual(
            self.env["mail.message"].search_count(
                [
                    ("model", "=", "llm.thread"),
                    ("res_id", "=", thread.id),
                    ("llm_role", "=", "user"),
                    ("body", "ilike", instruction),
                ]
            ),
            1,
        )
        self.assertTrue(any(event.get("type") == "message_create" for event in events))
        self.assertIn("office_prepare_context", thread.tool_ids.mapped("name"))

    def test_question_is_sent_to_model_without_local_router_or_preview_side_effect(self):
        thread = self._thread()
        attachment = self.env["ir.attachment"].create(
            {
                "name": "question-template-" + uuid4().hex + ".xlsx",
                "type": "binary",
                "mimetype": XLSX_MIME,
                "raw": _xlsx(),
                "company_id": self.env.company.id,
            }
        )
        source = thread.message_post(
            body="template source",
            llm_role="user",
            author_id=self.env.user.partner_id.id,
            attachment_ids=[attachment.id],
        )
        created = create_session(
            self.env,
            thread_id=thread.id,
            source_message_id=source.id,
            source_attachment_id=attachment.id,
            target_model="res.partner",
            target_record_id=self.env.user.partner_id.id,
        )
        session = self.env["office.mapping.session"].browse(created["session_id"])
        set_mapping_context(
            self.env,
            session.id,
            [
                {
                    "element_id": "xlsx:Sheet1!B1",
                    "required": True,
                    "writable": True,
                    "allowed_value_types": ["string"],
                    "approved_to_skip": False,
                }
            ],
            {"name": "string"},
        )
        session._save_mapping_from_service(
            json.dumps(
                {
                    "schema_version": "m2.mapping-proposal.v1",
                    "mappings": [
                        {
                            "element_id": "xlsx:Sheet1!B1",
                            "source_field": "name",
                            "value_type": "string",
                        }
                    ],
                    "clarifications": [],
                    "skipped_targets": [],
                }
            ),
            session.revision,
            "revision_pending",
        )
        old_revision = session.revision
        old_proposal = session.mapping_rules_json
        old_preview = session.preview_attachment_id
        answer = {"content": "B1 当前映射到联系人名称字段 name。"}
        with self._test_context(), patch.object(
            type(self.model), "chat", autospec=True, return_value=answer
        ) as provider_call, patch(
            "odoo.addons.office_engine_m2.services.render_bridge.render_preview"
        ) as preview_call:
            list(thread.generate(user_message_body="B1 是联系人名称吗？"))

        provider_call.assert_called_once()
        preview_call.assert_not_called()
        session.invalidate_recordset()
        self.assertEqual(session.revision, old_revision)
        self.assertEqual(session.mapping_rules_json, old_proposal)
        self.assertEqual(session.preview_attachment_id, old_preview)

    def test_native_tool_call_response_continues_through_assistant_loop(self):
        thread = self._thread()
        attachment = self.env["ir.attachment"].create(
            {
                "name": "tool-loop-template-" + uuid4().hex + ".xlsx",
                "type": "binary",
                "mimetype": XLSX_MIME,
                "raw": _xlsx(),
                "company_id": self.env.company.id,
            }
        )
        tool_call = {
            "id": "call_native_retriever_test",
            "type": "function",
            "function": {"name": "odoo_record_retriever", "arguments": "{}"},
        }
        responses = [
            {"tool_calls": [tool_call]},
            {"content": "The native tool cycle returned to the model."},
        ]

        def execute_tool(thread_record, call, _assistant_message):
            result = thread_record.message_post(
                body="Synthetic tool result",
                llm_role="tool",
                body_json={
                    "type": "tool_execution",
                    "tool_call_id": call["id"],
                    "tool_call": call,
                    "status": "completed",
                    "tool_name": call["function"]["name"],
                    "arguments": {},
                    "result": {"synthetic": True},
                },
            )
            yield {"type": "message_create", "message": result.to_store_format()}
            return result

        with (
            self._test_context(),
            patch.object(
                type(self.model), "chat", autospec=True, side_effect=responses
            ) as provider_call,
            patch.object(
                AssistantThread, "_execute_tool_call", autospec=True, side_effect=execute_tool
            ) as tool_executor,
            patch.object(self.env.cr, "commit", new=Mock()) as commit_call,
        ):
            list(
                thread.generate(
                    user_message_body="请读取合成联系人并映射工作簿。",
                    attachment_ids=[attachment.id],
                )
            )

        self.assertEqual(provider_call.call_count, 2)
        self.assertEqual(tool_executor.call_count, 1)
        self.assertIsNotNone(commit_call)
        self.assertEqual(
            self.env["mail.message"].search_count(
                [
                    ("model", "=", "llm.thread"),
                    ("res_id", "=", thread.id),
                    ("llm_role", "=", "user"),
                    ("body", "ilike", "请读取合成联系人并映射工作簿。"),
                ]
            ),
            1,
        )

    def test_native_office_tools_are_registered_once_and_only_for_office_thread(self):
        thread = self._thread()
        names = set(thread._office_bind_tools().mapped("name"))
        self.assertEqual(
            names,
            {
                "office_prepare_context",
                "office_save_mapping_preview",
                "office_restore_proposal_revision",
                "office_finalize",
                "odoo_record_retriever",
            },
        )
        office_tool = self.env["llm.tool"].search(
            [("name", "=", "office_prepare_context"), ("active", "=", True)]
        )
        self.assertEqual(len(office_tool), 1)
        self.assertEqual(office_tool.decorator_model, "office.mapping.tool")
