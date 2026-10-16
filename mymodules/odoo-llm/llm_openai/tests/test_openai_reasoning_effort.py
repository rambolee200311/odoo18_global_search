from types import SimpleNamespace
from unittest.mock import Mock, PropertyMock, patch
from uuid import uuid4

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase

from ..models.llm_model import _parse_openai_model_parameters


class TestOpenAIReasoningEffort(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.provider = cls.env["llm.provider"].create(
            {
                "name": f"OpenAI reasoning-effort test provider {uuid4().hex}",
                "service": "openai",
            }
        )

    def create_model(self, parameters=False):
        return self.env["llm.model"].create(
            {
                "name": f"reasoning-effort-test-model-{uuid4().hex}",
                "provider_id": self.provider.id,
                "model_use": "chat",
                "parameters": parameters,
            }
        )

    def test_empty_values_leave_request_unchanged(self):
        for value in (False, None, ""):
            with self.subTest(value=value):
                self.assertEqual(_parse_openai_model_parameters("openai", value), {})
                model = self.create_model(value)
                self.assertEqual(model._get_openai_request_parameters(), {})
                self.assertNotIn("reasoning_effort", self._capture_chat_params(model))

    def test_empty_objects_are_valid_and_do_not_add_effort(self):
        for value in ('{}', '{"openai":{}}'):
            with self.subTest(value=value):
                model = self.create_model(value)
                self.assertEqual(model._get_openai_request_parameters(), {})
                self.assertNotIn("reasoning_effort", self._capture_chat_params(model))

    def test_non_openai_provider_ignores_namespace_without_parsing(self):
        self.assertEqual(
            _parse_openai_model_parameters("other-provider", "not-json"),
            {},
        )
        self.assertEqual(
            _parse_openai_model_parameters(
                "other-provider",
                '{"openai":{"reasoning_effort":null}}',
            ),
            {},
        )

    def test_unknown_namespaces_and_keys_are_ignored(self):
        self.assertEqual(
            _parse_openai_model_parameters("openai", '{"other":{"x":1}}'),
            {},
        )
        self.assertEqual(
            _parse_openai_model_parameters(
                "openai",
                '{"openai":{"unknown":"x"}}',
            ),
            {},
        )
        model = self.create_model('{"openai":{"unknown":"x"}}')
        self.assertNotIn("reasoning_effort", self._capture_chat_params(model))

    def test_invalid_json_and_non_object_top_level_are_rejected(self):
        for value in ("{", "null", "[]", '"text"'):
            with self.subTest(value=value):
                with self.assertRaises(UserError):
                    _parse_openai_model_parameters("openai", value)
                with self.assertRaises(ValidationError):
                    self.create_model(value)

    def test_invalid_namespace_and_effort_values_are_rejected(self):
        invalid_values = (
            '{"openai":null}',
            '{"openai":[]}',
            '{"openai":"x"}',
            '{"openai":{"reasoning_effort":null}}',
            '{"openai":{"reasoning_effort":1}}',
            '{"openai":{"reasoning_effort":""}}',
            '{"openai":{"reasoning_effort":"low"}}',
        )
        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaises(UserError):
                    _parse_openai_model_parameters("openai", value)
                with self.assertRaises(ValidationError):
                    self.create_model(value)

    def _capture_chat_params(self, model, stream=False, with_tools=False):
        provider_class = type(self.provider)
        response = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=None, tool_calls=None),
                ),
            ],
        )
        create = Mock(return_value=iter([]) if stream else response)
        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=create),
            ),
        )
        tools = object() if with_tools else None

        with (
            patch.object(
                provider_class,
                "client",
                new_callable=PropertyMock,
                return_value=client,
            ),
            patch.object(
                provider_class,
                "format_messages",
                return_value=[{"role": "user", "content": "test"}],
            ),
            patch.object(
                provider_class,
                "format_tools",
                return_value=[
                    {
                        "type": "function",
                        "function": {"name": "stub", "parameters": {"type": "object"}},
                    },
                ],
            ),
        ):
            result = self.provider.openai_chat(
                [],
                model=model,
                stream=stream,
                tools=tools,
                prepend_messages=None,
            )
            if stream:
                list(result)

        create.assert_called_once()
        return create.call_args.kwargs

    def test_reasoning_effort_is_added_to_request(self):
        model = self.create_model('{"openai":{"reasoning_effort":"none"}}')
        params = self._capture_chat_params(model)
        self.assertEqual(params["reasoning_effort"], "none")

    def test_model_owned_request_fields_are_not_overridden(self):
        model = self.create_model(
            '{"openai":{"reasoning_effort":"none","model":"other",'
            '"messages":[],"stream":false,"tools":[],"tool_choice":"none"}}'
        )
        params = self._capture_chat_params(model, with_tools=True)
        self.assertEqual(params["model"], model.name)
        self.assertEqual(params["messages"], [{"role": "user", "content": "test"}])
        self.assertFalse(params["stream"])
        self.assertEqual(params["tools"][0]["function"]["name"], "stub")
        self.assertEqual(params["tool_choice"], "auto")
        self.assertEqual(params["reasoning_effort"], "none")

    def test_tool_and_stream_matrix(self):
        model = self.create_model('{"openai":{"reasoning_effort":"none"}}')
        for stream in (False, True):
            for with_tools in (False, True):
                with self.subTest(stream=stream, with_tools=with_tools):
                    params = self._capture_chat_params(
                        model,
                        stream=stream,
                        with_tools=with_tools,
                    )
                    self.assertEqual(params["reasoning_effort"], "none")
                    self.assertEqual(params["stream"], stream)
                    self.assertEqual("tools" in params, with_tools)

    def test_invalid_runtime_configuration_stops_before_http_call(self):
        provider_class = type(self.provider)
        create = Mock()
        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=create),
            ),
        )
        with (
            patch.object(
                provider_class,
                "client",
                new_callable=PropertyMock,
                return_value=client,
            ),
            patch.object(
                provider_class,
                "format_messages",
                return_value=[{"role": "user", "content": "test"}],
            ),
        ):
            for parameters in (
                "not-json",
                "null",
                '{"openai":null}',
                '{"openai":{"reasoning_effort":"low"}}',
            ):
                with self.subTest(parameters=parameters):
                    model = self.env["llm.model"].new(
                        {
                            "name": "unsaved-invalid-model",
                            "provider_id": self.provider.id,
                            "model_use": "chat",
                            "parameters": parameters,
                        }
                    )
                    with self.assertRaisesRegex(
                        UserError,
                        "Please contact an administrator",
                    ):
                        self.provider.openai_chat([], model=model)
        create.assert_not_called()
