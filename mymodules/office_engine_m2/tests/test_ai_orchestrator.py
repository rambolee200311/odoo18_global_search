import base64
import json
import os
from contextlib import ExitStack
from unittest.mock import patch
from uuid import uuid4

from odoo.exceptions import UserError
from odoo.tests import TransactionCase

from ..services import ai_orchestrator
from ..services.ai_orchestrator import run_mapping
from ..services.mapping_service import create_session, set_mapping_context


class TestOfficeAiOrchestrator(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.provider = cls.env["llm.provider"].create(
            {"name": "M2-005 OpenAI " + uuid4().hex, "service": "openai"}
        )
        cls.model = cls.env["llm.model"].create(
            {
                "name": "gpt-5.6-luna",
                "provider_id": cls.provider.id,
                "model_use": "chat",
            }
        )
        cls.retriever = cls.env.ref("llm_tool.llm_tool_odoo_record_retriever")

    def _session(self, count=20):
        target = self.env["res.partner"].create(
            {"name": "M2 synthetic target " + uuid4().hex, "company_id": self.env.company.id}
        )
        thread = self.env["llm.thread"].create(
            {
                "name": "M2-005 thread " + uuid4().hex,
                "provider_id": self.provider.id,
                "model_id": self.model.id,
            }
        )
        attachment = self.env["ir.attachment"].create(
            {
                "name": "synthetic-m2-005.xlsx",
                "type": "binary",
                "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "datas": base64.b64encode(b"synthetic-only-not-rendered"),
            }
        )
        message = thread.message_post(
            body="Use this synthetic target to fill the supplied test template.",
            llm_role="user",
            attachment_ids=[attachment.id],
        )
        created = create_session(
            self.env,
            thread_id=thread.id,
            source_message_id=message.id,
            source_attachment_id=attachment.id,
            target_model="res.partner",
            target_record_id=target.id,
        )
        session_id = created["session_id"]
        manifest = [
            {
                "element_id": f"xlsx:Sheet1!B{index + 1}",
                "required": True,
                "writable": True,
                "allowed_value_types": ["string"],
                "approved_to_skip": False,
            }
            for index in range(count)
        ]
        set_mapping_context(self.env, session_id, manifest, {"name": "string"})
        return self.env["office.mapping.session"].browse(session_id), thread

    @staticmethod
    def _provider_result(proposal):
        return {
            "content": json.dumps(proposal, ensure_ascii=False),
            "usage": {
                "prompt_tokens": 120,
                "completion_tokens": 60,
                "total_tokens": 180,
                "reasoning_tokens": None,
                "status": "available",
            },
            "response_id": "m2-005-response-" + uuid4().hex,
        }

    @staticmethod
    def _proposal(mapping_count, total=20):
        return {
            "schema_version": "m2.mapping-proposal.v1",
            "mappings": [
                {
                    "element_id": f"xlsx:Sheet1!B{index + 1}",
                    "source_field": "name",
                    "value_type": "string",
                }
                for index in range(mapping_count)
            ],
            "clarifications": [],
            "skipped_targets": [],
        }

    def _approved_synthetic_environment(self):
        return patch.dict(
            os.environ,
            {
                "OFFICE_ENGINE_M2_DATA_POLICY_APPROVED": "1",
                "OFFICE_ENGINE_M2_SAFE_FIELDS_JSON": '{"res.partner":["name"]}',
            },
        )

    def test_cc_test_004_five_of_twenty_retries_once_then_requires_clarification(self):
        session, thread = self._session()
        five_of_twenty = self._provider_result(self._proposal(5))
        model_class = type(self.model)
        before_usage = self.env["office.llm.usage"].search_count([("thread_id", "=", thread.id)])
        before_requests = self.env["office.document.request"].search_count([])
        before_outputs = self.env["ir.attachment"].search_count([("name", "ilike", "office-output-")])
        with self._approved_synthetic_environment(), patch.object(
            model_class, "chat", autospec=True, side_effect=[five_of_twenty, five_of_twenty]
        ) as provider_call:
            result = run_mapping(self.env, session.id)

        session.invalidate_recordset()
        rules = json.loads(session.mapping_rules_json)
        self.assertEqual(provider_call.call_count, 2)
        self.assertEqual(result["state"], "needs_clarification")
        self.assertEqual(session.state, "needs_clarification")
        self.assertEqual(len(rules["mappings"]), 5)
        self.assertEqual(len(rules["clarifications"]), 15)
        self.assertEqual(
            self.env["office.llm.usage"].search_count([("thread_id", "=", thread.id)]) - before_usage,
            2,
        )
        usage_rows = self.env["office.llm.usage"].search(
            [("thread_id", "=", thread.id)], order="attempt_no"
        )
        self.assertEqual([row.attempt_no for row in usage_rows], [1, 2])
        self.assertTrue(all(type(row.elapsed_ms) is int and row.elapsed_ms >= 0 for row in usage_rows))
        self.assertEqual([row.outcome for row in usage_rows], ["success", "success"])
        self.assertTrue(all(row.response_id for row in usage_rows))
        self.assertEqual(self.env["office.document.request"].search_count([]), before_requests)
        self.assertEqual(
            self.env["ir.attachment"].search_count([("name", "ilike", "office-output-")]),
            before_outputs,
        )

    def test_complete_proposal_is_saved_for_explicit_user_confirmation(self):
        session, thread = self._session()
        prompt_sentinel = "M2_PROMPT_SENTINEL_" + uuid4().hex
        self.env[session.target_model].browse(session.target_record_id).write({"name": prompt_sentinel})
        complete = self._provider_result(self._proposal(20))
        before_requests = self.env["office.document.request"].search_count([])
        with self._approved_synthetic_environment(), patch.object(
            type(self.model), "chat", autospec=True, return_value=complete
        ) as provider_call:
            result = run_mapping(self.env, session.id)

        session.invalidate_recordset()
        self.assertEqual(provider_call.call_count, 1)
        self.assertEqual(result["state"], "awaiting_confirmation")
        self.assertEqual(session.state, "awaiting_confirmation")
        self.assertEqual(session.confirmed_revision, 0)
        self.assertEqual(
            self.env["office.llm.usage"].search_count([("thread_id", "=", thread.id)]), 1
        )
        usage = self.env["office.llm.usage"].search([("thread_id", "=", thread.id)], limit=1)
        self.assertEqual(usage.attempt_no, 1)
        self.assertEqual(usage.prompt_tokens, 120)
        self.assertEqual(usage.completion_tokens, 60)
        self.assertEqual(usage.total_tokens, 180)
        self.assertEqual(usage.response_id, complete["response_id"])
        self.assertFalse(
            self.env["mail.message"].search_count([("body", "ilike", prompt_sentinel)])
        )
        self.assertNotIn(prompt_sentinel, repr(usage.read()[0]))
        self.assertFalse(
            {"prompt", "completion", "prompt_text", "completion_text", "response_text"}
            & set(self.env["office.llm.usage"]._fields)
        )
        self.assertEqual(self.env["office.document.request"].search_count([]), before_requests)

    def test_list_group_prompt_uses_explicit_targets_and_authorized_retriever_rows(self):
        session, thread = self._session(count=2)
        target = self.env[session.target_model].browse(session.target_record_id)
        children = self.env["res.partner"].create([
            {"name": "Line One", "parent_id": target.id, "company_id": self.env.company.id},
            {"name": "Line Two", "parent_id": target.id, "company_id": self.env.company.id},
        ])
        manifest = [
            {
                "element_id": f"xlsx:Sheet1!A{index + 8}",
                "required": True,
                "writable": True,
                "allowed_value_types": ["string"],
                "approved_to_skip": False,
            }
            for index in range(2)
        ]
        group = {
            "group_id": "order_lines",
            "collection_field": "child_ids",
            "relation_model": "res.partner",
            "row_count": 2,
            "target_rows": [
                {"row_index": index, "targets": [{"column_id": "name", "element_id": spec["element_id"]}]}
                for index, spec in enumerate(manifest)
            ],
            "allowed_fields": {"name": "string"},
        }
        set_mapping_context(
            self.env, session.id, manifest, {"name": "string"}, mapping_groups=[group]
        )
        proposal = {
            "schema_version": "m2.mapping-proposal.v1",
            "mappings": [
                {
                    "element_id": spec["element_id"],
                    "source_field": "order_lines::name",
                    "value_type": "string",
                }
                for spec in manifest
            ],
            "clarifications": [],
            "skipped_targets": [],
        }
        captured = {}

        def mock_chat(_model, message, **_kwargs):
            captured["payload"] = json.loads(message.body)
            return self._provider_result(proposal)

        with self._approved_synthetic_environment(), patch.object(
            type(self.model), "chat", autospec=True, side_effect=mock_chat
        ) as provider_call:
            result = run_mapping(self.env, session.id)

        self.assertEqual(provider_call.call_count, 1)
        self.assertEqual(result["state"], "awaiting_confirmation")
        group_prompt = captured["payload"]["mapping_groups"][0]
        self.assertEqual(group_prompt["group_id"], "order_lines")
        self.assertEqual(group_prompt["row_count"], 2)
        self.assertEqual(len(group_prompt["target_rows"]), 2)
        self.assertEqual(
            [row["order_lines::name"] for row in group_prompt["authorized_sample_rows"]],
            [children[0].name, children[1].name],
        )
        self.assertIn("list-loop mapping", ai_orchestrator._SYSTEM_PROMPT)

    def test_collection_size_change_fails_before_provider_dispatch(self):
        session, _thread = self._session(count=1)
        spec = {
            "element_id": "xlsx:Sheet1!A8",
            "required": True,
            "writable": True,
            "allowed_value_types": ["string"],
            "approved_to_skip": False,
        }
        group = {
            "group_id": "order_lines",
            "collection_field": "child_ids",
            "relation_model": "res.partner",
            "row_count": 1,
            "target_rows": [{"row_index": 0, "targets": [{"column_id": "name", "element_id": spec["element_id"]}]}],
            "allowed_fields": {"name": "string"},
        }
        set_mapping_context(self.env, session.id, [spec], {"name": "string"}, mapping_groups=[group])
        with self._approved_synthetic_environment(), patch.object(
            type(self.model), "chat", autospec=True
        ) as provider_call:
            with self.assertRaises(UserError):
                run_mapping(self.env, session.id)
        self.assertEqual(provider_call.call_count, 0)

    def test_cc_test_006_missing_usage_is_recorded_without_losing_proposal(self):
        session, thread = self._session(count=1)
        response = self._provider_result(self._proposal(1, total=1))
        response.pop("usage")
        with self._approved_synthetic_environment(), patch.object(
            type(self.model), "chat", autospec=True, return_value=response
        ) as provider_call:
            result = run_mapping(self.env, session.id)

        session.invalidate_recordset()
        usage = self.env["office.llm.usage"].search([("thread_id", "=", thread.id)], limit=1)
        self.assertEqual(provider_call.call_count, 1)
        self.assertEqual(result["state"], "awaiting_confirmation")
        self.assertEqual(session.state, "awaiting_confirmation")
        self.assertTrue(usage)
        self.assertEqual(usage.error_code, "usage_missing")
        self.assertIsNone(usage.prompt_tokens)
        self.assertIsNone(usage.completion_tokens)
        self.assertIsNone(usage.total_tokens)

    def test_default_denies_provider_without_data_policy_or_field_baseline(self):
        session, thread = self._session()
        with patch.dict(
            os.environ,
            {
                "OFFICE_ENGINE_M2_DATA_POLICY_APPROVED": "0",
                "OFFICE_ENGINE_M2_SAFE_FIELDS_JSON": "",
            },
        ), patch.object(type(self.model), "chat", autospec=True) as provider_call:
            with self.assertRaises(UserError):
                run_mapping(self.env, session.id)

        self.assertEqual(provider_call.call_count, 0)
        self.assertFalse(self.env["office.llm.usage"].search_count([("thread_id", "=", thread.id)]))

    def test_cc_test_005_retries_invalid_json_then_clarifies_without_m1(self):
        session, thread = self._session()
        malformed = {
            **self._provider_result(self._proposal(0)),
            "content": "```json\n{not valid json}\n```",
        }
        before_requests = self.env["office.document.request"].search_count([])
        before_usage = self.env["office.llm.usage"].search_count([("thread_id", "=", thread.id)])
        with self._approved_synthetic_environment(), patch.object(
            type(self.model), "chat", autospec=True, side_effect=[malformed, malformed]
        ) as provider_call:
            result = run_mapping(self.env, session.id)

        session.invalidate_recordset()
        self.assertEqual(provider_call.call_count, 2)
        self.assertEqual(result["state"], "needs_clarification")
        self.assertEqual(session.state, "needs_clarification")
        self.assertTrue(result["missing_targets"])
        self.assertEqual(self.env["office.document.request"].search_count([]), before_requests)
        self.assertEqual(
            self.env["office.llm.usage"].search_count([("thread_id", "=", thread.id)]) - before_usage,
            2,
        )

    def test_cc_test_005_unknown_field_proposal_is_not_forwarded_to_m1(self):
        session, _thread = self._session(count=1)
        forged = self._proposal(1, total=1)
        forged["mappings"][0]["source_field"] = "administrator_password"
        response = self._provider_result(forged)
        before_requests = self.env["office.document.request"].search_count([])
        with self._approved_synthetic_environment(), patch.object(
            type(self.model), "chat", autospec=True, side_effect=[response, response]
        ) as provider_call:
            result = run_mapping(self.env, session.id)

        session.invalidate_recordset()
        rules = json.loads(session.mapping_rules_json)
        self.assertEqual(provider_call.call_count, 2)
        self.assertEqual(result["state"], "needs_clarification")
        self.assertFalse(rules["mappings"])
        self.assertEqual(len(rules["clarifications"]), 1)
        self.assertEqual(self.env["office.document.request"].search_count([]), before_requests)

    def test_cc_test_005_unknown_target_extra_key_and_type_mismatch_fail_closed(self):
        cases = []
        unknown_target = self._proposal(1, total=1)
        unknown_target["mappings"][0]["element_id"] = "xlsx:Other!Z99"
        cases.append(("unknown_target", unknown_target))
        extra_key = self._proposal(1, total=1)
        extra_key["mappings"][0]["untrusted_instruction"] = "emit a download URL"
        cases.append(("extra_key", extra_key))
        wrong_type = self._proposal(1, total=1)
        wrong_type["mappings"][0]["value_type"] = "number"
        cases.append(("wrong_type", wrong_type))

        for label, proposal in cases:
            with self.subTest(case=label):
                session, _thread = self._session(count=1)
                response = self._provider_result(proposal)
                before_requests = self.env["office.document.request"].search_count([])
                with self._approved_synthetic_environment(), patch.object(
                    type(self.model), "chat", autospec=True, side_effect=[response, response]
                ) as provider_call:
                    result = run_mapping(self.env, session.id)

                session.invalidate_recordset()
                saved = json.loads(session.mapping_rules_json)
                self.assertEqual(provider_call.call_count, 2)
                self.assertEqual(result["state"], "needs_clarification")
                self.assertEqual(session.state, "needs_clarification")
                self.assertEqual(saved["mappings"], [])
                self.assertEqual(len(saved["clarifications"]), 1)
                self.assertEqual(self.env["office.document.request"].search_count([]), before_requests)

    def test_cc_test_002_retriever_timeout_or_missing_record_stops_before_provider(self):
        for scenario in ("timeout", "missing"):
            with self.subTest(scenario=scenario):
                session, thread = self._session(count=1)
                before_requests = self.env["office.document.request"].search_count([])
                retriever_type = type(self.retriever)
                retriever_patch = (
                    patch.object(
                        retriever_type,
                        "execute",
                        autospec=True,
                        side_effect=TimeoutError("synthetic timeout"),
                    )
                    if scenario == "timeout"
                    else patch.object(retriever_type, "execute", autospec=True, return_value=[])
                )
                with self._approved_synthetic_environment(), retriever_patch, patch.object(
                    type(self.model), "chat", autospec=True
                ) as provider_call:
                    with self.assertRaises(UserError):
                        run_mapping(self.env, session.id)

                self.assertEqual(provider_call.call_count, 0)
                self.assertFalse(
                    self.env["office.llm.usage"].search_count([("thread_id", "=", thread.id)])
                )
                self.assertEqual(self.env["office.document.request"].search_count([]), before_requests)

    def test_cc_test_010_provider_or_usage_failure_stops_before_m1(self):
        for failure_mode in ("provider", "usage"):
            with self.subTest(failure_mode=failure_mode):
                session, thread = self._session(count=1)
                before_requests = self.env["office.document.request"].search_count([])
                before_usage = self.env["office.llm.usage"].search_count([("thread_id", "=", thread.id)])
                usage_recorder = None
                with self._approved_synthetic_environment(), ExitStack() as stack:
                    if failure_mode == "provider":
                        provider_call = stack.enter_context(patch.object(
                            type(self.model),
                            "chat",
                            autospec=True,
                            side_effect=RuntimeError("mock provider unavailable"),
                        ))
                        usage_recorder = stack.enter_context(
                            patch.object(
                                ai_orchestrator,
                                "record_usage",
                                wraps=ai_orchestrator.record_usage,
                            )
                        )
                    else:
                        provider_call = stack.enter_context(patch.object(
                            type(self.model), "chat", autospec=True,
                            return_value=self._provider_result(self._proposal(1, total=1)),
                        ))
                        usage_recorder = stack.enter_context(
                            patch.object(ai_orchestrator, "record_usage", return_value=False)
                        )
                    if failure_mode == "provider":
                        result = run_mapping(self.env, session.id)
                    else:
                        with self.assertRaises(UserError):
                            run_mapping(self.env, session.id)

                self.assertEqual(provider_call.call_count, 1)
                self.assertEqual(self.env["office.document.request"].search_count([]), before_requests)
                usage_records = self.env["office.llm.usage"].search(
                    [("thread_id", "=", thread.id)], order="id desc"
                )
                if failure_mode == "provider":
                    session.invalidate_recordset()
                    self.assertEqual(result["state"], "failed")
                    self.assertEqual(session.state, "failed")
                    self.assertEqual(session.error_code, "provider_error")
                    self.assertEqual(usage_recorder.call_count, 1)
                    usage_metadata = usage_recorder.call_args.kwargs
                    self.assertEqual(usage_metadata["outcome"], "provider_error")
                    self.assertEqual(usage_metadata["error_code"], "provider_error")
                    self.assertIsNone(usage_metadata["usage"])
                    self.assertEqual(len(usage_records), before_usage + 1)
                    self.assertEqual(usage_records[0].outcome, "provider_error")
                    self.assertEqual(usage_records[0].error_code, "usage_missing")
                    self.assertEqual(usage_records[0].attempt_no, 1)
                    self.assertIsInstance(usage_records[0].elapsed_ms, int)
                    self.assertGreaterEqual(usage_records[0].elapsed_ms, 0)
                else:
                    self.assertEqual(usage_recorder.call_count, 1)
                    self.assertEqual(len(usage_records), before_usage)
