import json
from types import SimpleNamespace
from unittest.mock import Mock, PropertyMock, patch
from uuid import uuid4

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestOpenAIToolSchema(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.provider = cls.env["llm.provider"].create(
            {
                "name": f"OpenAI schema test provider {uuid4().hex}",
                "service": "openai",
            }
        )

    def create_model(self):
        return self.env["llm.model"].create(
            {
                "name": f"openai-schema-test-model-{uuid4().hex}",
                "provider_id": self.provider.id,
                "model_use": "chat",
            }
        )

    def create_tool(self, **values):
        defaults = {
            "name": f"openai_schema_test_tool_{uuid4().hex}",
            "description": "Schema test tool",
            "implementation": "odoo_record_retriever",
        }
        defaults.update(values)
        return self.env["llm.tool"].create(defaults)

    def _mock_client(self):
        create = Mock()
        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=create),
            ),
        )
        return client, create

    def test_openai_formatter_preserves_schema_semantics_without_mutating_input(self):
        schema = {
            "type": "object",
            "properties": {
                "model": {"type": "string", "description": "Odoo model name"},
                "domain": {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": {
                            "anyOf": [
                                {"type": "string"},
                                {"type": "integer"},
                                {"type": "boolean"},
                                {"type": "number"},
                                {"type": "null"},
                            ],
                        },
                    },
                },
            },
            "required": ["model"],
            "additionalProperties": False,
        }
        original = json.loads(json.dumps(schema))
        tool = self.create_tool(input_schema=json.dumps(schema))

        formatted = self.provider._openai_format_tool(tool)

        self.assertEqual(formatted["type"], "function")
        self.assertEqual(formatted["function"]["parameters"], original)
        self.assertEqual(schema, original)
        self.assertEqual(json.loads(tool.input_schema), original)
        domain_items = formatted["function"]["parameters"]["properties"]["domain"]
        domain_items = domain_items["items"]["items"]
        self.assertIn("anyOf", domain_items)
        self.assertNotIn("type", domain_items)

    def test_dynamic_retriever_schema_is_sent_without_loss(self):
        tool = self.env["llm.tool"].search(
            [("name", "=", "odoo_record_retriever")],
            limit=1,
        )
        self.assertTrue(tool)
        schema = tool.get_input_schema()

        formatted = self.provider._openai_format_tool(tool)

        parameters = formatted["function"]["parameters"]
        self.assertEqual(parameters, schema)
        self.assertEqual(parameters["required"], ["model"])
        domain_items = parameters["properties"]["domain"]["items"]["items"]
        self.assertIn("anyOf", domain_items)
        self.assertNotIn("type", domain_items)

    def test_other_tool_schema_is_not_dropped_by_formatter(self):
        tool = self.env["llm.tool"].search(
            [("name", "=", "odoo_record_updater")],
            limit=1,
        )
        self.assertTrue(tool)
        schema = tool.get_input_schema()

        formatted = self.provider._openai_format_tool(tool)

        self.assertEqual(formatted["function"]["parameters"], schema)

    def test_stub_provider_arguments_reach_execute_validation(self):
        model = self.create_model()
        tool = self.env["llm.tool"].search(
            [("name", "=", "odoo_record_retriever")],
            limit=1,
        )
        self.assertTrue(tool)
        arguments = {"model": "res.partner"}
        tool_call = SimpleNamespace(
            id="call-schema-test",
            type="function",
            function=SimpleNamespace(
                name=tool.name,
                arguments=json.dumps(arguments),
            ),
        )
        response = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=None, tool_calls=[tool_call]),
                ),
            ],
        )
        client, create = self._mock_client()
        create.return_value = response

        with patch.object(
            type(self.provider),
            "client",
            new_callable=PropertyMock,
            return_value=client,
        ):
            result = self.provider.openai_chat(
                self.env["mail.message"],
                model=model,
                tools=tool,
            )

        create.assert_called_once()
        self.assertEqual(result["tool_calls"][0]["function"]["name"], tool.name)
        sent_schema = create.call_args.kwargs["tools"][0]["function"]["parameters"]
        self.assertEqual(sent_schema["required"], ["model"])
        decoded = json.loads(result["tool_calls"][0]["function"]["arguments"])

        calls = []

        def stub_retriever(
            self,
            model: str,
            domain: list[list[str | int | bool | float | None]] = [],
            fields: list[str] = [],
            limit: int = 100,
        ):
            calls.append((model, domain, fields, limit))
            return {"ok": True}

        with patch.object(type(tool), "odoo_record_retriever_execute", stub_retriever):
            self.assertEqual(tool.execute(decoded), {"ok": True})
        self.assertEqual(calls, [("res.partner", [], [], 100)])

    def test_invalid_stored_schema_fails_before_provider_http(self):
        model = self.create_model()
        client, create = self._mock_client()

        with (
            patch.object(
                type(self.provider),
                "client",
                new_callable=PropertyMock,
                return_value=client,
            ),
        ):
            for index, schema in enumerate(("{not valid json", "null", "[]")):
                tool = self.create_tool(
                    name=f"openai_invalid_schema_{uuid4().hex}_{index}",
                    input_schema=schema,
                )
                with self.subTest(schema=schema):
                    with self.assertRaises(UserError):
                        self.provider.openai_chat(
                            self.env["mail.message"],
                            model=model,
                            tools=tool,
                        )

        create.assert_not_called()

    def test_schema_generation_failure_is_sanitized_and_stops_before_http(self):
        model = self.create_model()
        tool = self.create_tool()
        client, create = self._mock_client()
        internal_marker = "CC-TEST-005-INTERNAL-MARKER"

        with (
            patch.object(
                type(tool),
                "get_input_schema",
                side_effect=RuntimeError(internal_marker),
            ),
            patch.object(
                type(self.provider),
                "client",
                new_callable=PropertyMock,
                return_value=client,
            ),
            self.assertRaises(UserError) as error,
        ):
            self.provider.openai_chat(
                self.env["mail.message"],
                model=model,
                tools=tool,
            )

        self.assertNotIn(internal_marker, str(error.exception))
        create.assert_not_called()

    def test_chat_error_path_displays_controlled_schema_error(self):
        model = self.create_model()
        tool = self.create_tool()
        thread = self.env["llm.thread"].create(
            {
                "name": f"Schema error test {uuid4().hex}",
                "provider_id": self.provider.id,
                "model_id": model.id,
                "tool_ids": [(6, 0, tool.ids)],
            }
        )
        thread.message_post(
            body="Schema generation error-path test",
            subtype_xmlid="llm.mt_user",
            author_id=self.env.user.partner_id.id,
        )
        client, create = self._mock_client()
        internal_marker = "CC-TEST-011-SECRET-INTERNAL-MARKER"

        with (
            patch.object(
                type(tool),
                "get_input_schema",
                side_effect=RuntimeError(internal_marker),
            ),
            patch.object(
                type(self.provider),
                "client",
                new_callable=PropertyMock,
                return_value=client,
            ),
        ):
            events = list(thread._generate_assistant_response())

        create.assert_not_called()
        self.assertTrue(events)
        error_message = self.env["mail.message"].search(
            [
                ("model", "=", "llm.thread"),
                ("res_id", "=", thread.id),
                ("is_error", "=", True),
            ],
            order="id desc",
            limit=1,
        )
        self.assertTrue(error_message)
        visible_error = error_message.body
        self.assertIn("schema", visible_error.lower())
        self.assertNotIn(internal_marker, visible_error)
        self.assertNotIn("Traceback", visible_error)
        self.assertNotIn("openai_provider.py", visible_error)
