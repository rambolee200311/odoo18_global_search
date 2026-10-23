from types import SimpleNamespace
from unittest.mock import Mock, patch

from odoo.tests import TransactionCase


def _usage(prompt=8, completion=5, total=13, reasoning=2):
    return SimpleNamespace(
        prompt_tokens=prompt,
        completion_tokens=completion,
        total_tokens=total,
        completion_tokens_details=SimpleNamespace(reasoning_tokens=reasoning),
        vendor_private_field="must not escape",
    )


def _response(*, content="answer", tool_calls=None, usage=None, response_id="resp-test"):
    message = SimpleNamespace(content=content, tool_calls=tool_calls or [])
    return SimpleNamespace(
        choices=[SimpleNamespace(message=message)],
        usage=usage,
        id=response_id,
        vendor_private_field="must not escape",
    )


class TestProviderUsageNormalization(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.provider = cls.env["llm.provider"]

    def _normalize(self, response):
        return self.provider._openai_process_non_streaming_response(response)

    def test_cc_test_001_valid_usage_and_tool_calls_are_allowlisted(self):
        call = SimpleNamespace(
            id="call-1",
            type="function",
            function=SimpleNamespace(name="lookup", arguments='{"id":1}'),
        )
        result = self._normalize(
            _response(tool_calls=[call], usage=_usage(), response_id="resp-123")
        )
        self.assertEqual(
            result["tool_calls"],
            [
                {
                    "id": "call-1",
                    "type": "function",
                    "function": {"name": "lookup", "arguments": '{"id":1}'},
                }
            ],
        )
        self.assertEqual(
            result["usage"],
            {
                "prompt_tokens": 8,
                "completion_tokens": 5,
                "total_tokens": 13,
                "reasoning_tokens": 2,
                "status": "available",
            },
        )
        self.assertEqual(result["response_id"], "resp-123")
        self.assertNotIn("vendor_private_field", result)

    def test_cc_test_002_missing_and_partial_usage_preserve_content(self):
        no_usage = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="kept", tool_calls=[]))],
            id="resp-no-usage",
        )
        result = self._normalize(no_usage)
        self.assertEqual(result["content"], "kept")
        self.assertNotIn("usage", result)
        self.assertEqual(result["response_id"], "resp-no-usage")

        result_none = self._normalize(_response(content="still kept", usage=None))
        self.assertEqual(result_none["content"], "still kept")
        self.assertNotIn("usage", result_none)

        result_partial = self._normalize(
            _response(
                content="partial kept",
                usage=_usage(prompt=0, completion=None, total=0, reasoning=None),
            )
        )
        self.assertEqual(result_partial["content"], "partial kept")
        self.assertEqual(result_partial["usage"]["prompt_tokens"], 0)
        self.assertIsNone(result_partial["usage"]["completion_tokens"])
        self.assertEqual(result_partial["usage"]["total_tokens"], 0)
        self.assertIsNone(result_partial["usage"]["reasoning_tokens"])
        self.assertEqual(result_partial["usage"]["status"], "partial")

    def test_cc_test_003_illegal_usage_isolated_from_content_and_tool_calls(self):
        invalid_values = [-1, True, "4", 3.5]
        for invalid_value in invalid_values:
            with self.subTest(invalid_value=invalid_value):
                result = self._normalize(
                    _response(content="valid content", usage=_usage(prompt=invalid_value))
                )
                self.assertEqual(result["content"], "valid content")
                self.assertIsNone(result["usage"]["prompt_tokens"])
                self.assertEqual(result["usage"]["status"], "invalid")

        class BrokenUsage:
            @property
            def prompt_tokens(self):
                raise RuntimeError("synthetic SDK property failure")

            completion_tokens = 1
            total_tokens = 1
            completion_tokens_details = None

        result = self._normalize(_response(content="survives", usage=BrokenUsage()))
        self.assertEqual(result["content"], "survives")
        self.assertEqual(result["usage"]["status"], "invalid")

    def test_usage_only_response_is_still_returned_as_metadata(self):
        result = self._normalize(_response(content=None, usage=_usage()))
        self.assertNotIn("content", result)
        self.assertNotIn("tool_calls", result)
        self.assertEqual(result["usage"]["status"], "available")

    def test_cc_test_008_openai_chat_uses_mock_client_without_network(self):
        provider = self.env["llm.provider"].create(
            {"name": "M2 Mock OpenAI Provider", "service": "openai"}
        )
        model = self.env["llm.model"].create(
            {"name": "gpt-5.6-luna", "provider_id": provider.id, "model_use": "chat"}
        )
        completion = _response(content="mocked", usage=_usage())
        create = Mock(return_value=completion)
        fake_client = SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=create))
        )
        with (
            patch.object(type(provider), "openai_get_client", return_value=fake_client),
            patch.object(type(provider), "format_messages", return_value=[{"role": "user", "content": "synthetic"}]),
            patch("socket.create_connection", side_effect=AssertionError("network access attempted")),
        ):
            result = provider.openai_chat([], model=model, stream=False)
        self.assertEqual(create.call_count, 1)
        self.assertEqual(result["content"], "mocked")
        self.assertEqual(result["usage"]["prompt_tokens"], 8)
