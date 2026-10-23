from types import SimpleNamespace

from odoo.tests import TransactionCase


class TestNonStreamingResponseCompatibility(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.provider = cls.env["llm.provider"].create(
            {"name": "M2 Response Test Provider", "service": "openai"}
        )
        cls.model = cls.env["llm.model"].create(
            {
                "name": "gpt-5.6-luna",
                "provider_id": cls.provider.id,
                "model_use": "chat",
            }
        )
        cls.thread = cls.env["llm.thread"].create(
            {
                "name": "M2 Usage Response Compatibility",
                "provider_id": cls.provider.id,
                "model_id": cls.model.id,
                "user_id": cls.env.user.id,
            }
        )

    def _sdk_response(self, *, content="answer", tool_calls=None, usage=None):
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=content, tool_calls=tool_calls or [])
                )
            ],
            usage=usage,
            id="resp-private-metadata",
        )

    def test_cc_test_004_usage_and_response_id_never_enter_mail_message(self):
        tool_call = SimpleNamespace(
            id="call-compat",
            type="function",
            function=SimpleNamespace(name="lookup", arguments='{"record":1}'),
        )
        normalized = self.provider._openai_process_non_streaming_response(
            self._sdk_response(
                content="visible assistant answer",
                tool_calls=[tool_call],
                usage=SimpleNamespace(
                    prompt_tokens=11,
                    completion_tokens=7,
                    total_tokens=18,
                    completion_tokens_details=SimpleNamespace(reasoning_tokens=3),
                ),
            )
        )

        yielded = list(self.thread._handle_non_streaming_response(normalized))
        self.assertEqual(len(yielded), 1)
        assistant_message = self.thread.message_ids.sorted("id")[-1]
        self.assertEqual(assistant_message.body_json, {"tool_calls": normalized["tool_calls"]})
        self.assertNotIn("usage", assistant_message.body_json)
        self.assertNotIn("response_id", assistant_message.body_json)
        self.assertNotIn("resp-private-metadata", assistant_message.body or "")
        self.assertNotIn("prompt_tokens", assistant_message.body or "")

    def test_usage_without_content_keeps_existing_no_response_behavior(self):
        normalized = self.provider._openai_process_non_streaming_response(
            self._sdk_response(
                content=None,
                usage=SimpleNamespace(
                    prompt_tokens=1,
                    completion_tokens=1,
                    total_tokens=2,
                    completion_tokens_details=None,
                ),
            )
        )
        yielded = list(self.thread._handle_non_streaming_response(normalized))
        self.assertEqual(len(yielded), 1)
        assistant_message = self.thread.message_ids.sorted("id")[-1]
        self.assertIn("No response from model", assistant_message.body or "")
        self.assertFalse(assistant_message.body_json)

    def test_streaming_parser_contract_is_unchanged(self):
        chunk = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    delta=SimpleNamespace(content="stream text", tool_calls=None),
                    finish_reason=None,
                )
            ]
        )
        self.assertEqual(
            list(self.provider._openai_process_streaming_response([chunk])),
            [{"content": "stream text"}],
        )
