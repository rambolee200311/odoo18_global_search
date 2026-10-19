import json
from unittest.mock import patch

from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged

from .common import LLMToolCase


@tagged("post_install", "-at_install")
class TestLLMToolSchema(LLMToolCase):
    """Test schema generation and storage for llm.tool"""

    def test_get_input_schema_from_stored_field(self):
        """Test get_input_schema() returns stored schema from DB field"""
        custom_schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        }

        tool = self._create_test_tool(input_schema=json.dumps(custom_schema))

        result = tool.get_input_schema()

        self.assertEqual(result, custom_schema)
        self.assertIsInstance(result, dict)

    def test_get_input_schema_raises_controlled_error_on_invalid_json(self):
        """Invalid stored JSON fails closed with a stable user-facing error."""
        tool = self._create_test_tool(input_schema="invalid json {")

        with self.assertRaises(UserError) as error:
            tool.get_input_schema()
        self.assertEqual(
            str(error.exception),
            "The input schema for this tool could not be prepared.",
        )

    def test_get_input_schema_rejects_non_object_json(self):
        for index, stored_schema in enumerate(
            ("null", "[]", json.dumps({"properties": {}}))
        ):
            with self.subTest(stored_schema=stored_schema):
                tool = self._create_test_tool(
                    name=f"test_non_object_schema_{index}",
                    input_schema=stored_schema,
                )
                with self.assertRaises(UserError):
                    tool.get_input_schema()

    def test_retriever_schema_is_generated_from_execution_signature(self):
        tool = self.LLMTool.search(
            [("name", "=", "odoo_record_retriever")],
            limit=1,
        )
        self.assertTrue(tool)

        method = tool._get_implementation_method()
        expected = tool.get_pydantic_model_from_signature(method).model_json_schema(
            by_alias=True
        )
        schema = tool.get_input_schema()

        self.assertEqual(schema, expected)
        self.assertEqual(schema["type"], "object")
        self.assertEqual(schema["required"], ["model"])
        self.assertEqual(schema["properties"]["model"]["type"], "string")
        self.assertEqual(schema["properties"]["fields"]["items"]["type"], "string")
        self.assertEqual(schema["properties"]["limit"]["type"], "integer")
        self.assertEqual(schema["properties"]["limit"]["default"], 100)
        domain_items = schema["properties"]["domain"]["items"]["items"]
        self.assertIn("anyOf", domain_items)
        self.assertNotIn("type", domain_items)

    def test_execute_missing_required_model_stops_before_callable(self):
        tool = self.LLMTool.search(
            [("name", "=", "odoo_record_retriever")],
            limit=1,
        )
        self.assertTrue(tool)

        from pydantic import ValidationError as PydanticValidationError

        calls = []

        def stub_retriever(
            self,
            model: str,
            domain: list[list[str | int | bool | float | None]] = [],
            fields: list[str] = [],
            limit: int = 100,
        ):
            calls.append((model, domain, fields, limit))
            return []

        with patch.object(type(tool), "odoo_record_retriever_execute", stub_retriever):
            with self.assertRaises(PydanticValidationError):
                tool.execute({})
        self.assertEqual(calls, [])

    def test_execute_uses_signature_defaults_for_optional_parameters(self):
        tool = self.LLMTool.search(
            [("name", "=", "odoo_record_retriever")],
            limit=1,
        )
        self.assertTrue(tool)

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
            result = tool.execute({"model": "res.partner"})

        self.assertEqual(result, {"ok": True})
        self.assertEqual(
            calls,
            [("res.partner", [], [], 100)],
        )

    def test_retriever_keeps_current_user_model_access(self):
        tool = self.LLMTool.search(
            [("name", "=", "odoo_record_retriever")],
            limit=1,
        )
        self.assertTrue(tool)

        restricted_user = self.env["res.users"].with_context(
            no_reset_password=True
        ).create(
            {
                "name": "Schema ACL Test User",
                "login": "schema-acl-test-user",
                "company_id": self.env.company.id,
                "company_ids": [(6, 0, self.env.company.ids)],
                "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )

        with self.assertRaises(AccessError):
            tool.with_user(restricted_user).execute(
                {"model": "sale.order", "fields": ["id"], "limit": 1}
            )

    def test_get_input_schema_unimplemented_implementation_raises_error(self):
        """Test get_input_schema() raises NotImplementedError for missing {implementation}_execute method"""

        # Patch _get_available_implementations to allow a dummy implementation
        def patched_implementations():
            return [
                ("function", "Function"),
                ("dummy_implementation", "Dummy"),
            ]

        with patch.object(
            type(self.LLMTool),
            "_get_available_implementations",
            patched_implementations,
        ):
            # Create tool with dummy implementation (no stored schema)
            tool = self.LLMTool.create(
                {
                    "name": "test_dummy_schema_tool",
                    "description": "Test tool with unimplemented implementation",
                    "implementation": "dummy_implementation",
                }
            )

            # Schema errors are exposed as a controlled user-facing error.
            with self.assertRaises(UserError) as ctx:
                tool.get_input_schema()

            self.assertNotIn("dummy_implementation_execute", str(ctx.exception))

    def test_get_tool_definition_respects_stored_schema(self):
        """Test get_tool_definition() uses stored input_schema field"""
        custom_schema = {
            "type": "object",
            "properties": {"custom_field": {"type": "string"}},
        }

        tool = self._create_test_tool(
            name="test_def_tool",
            description="Test description",
            input_schema=json.dumps(custom_schema),
            decorator_model="res.users",
            decorator_method="read",  # Common method that exists on all models
        )

        definition = tool.get_tool_definition()

        # Should use the custom schema from DB
        self.assertEqual(definition["inputSchema"], custom_schema)
        self.assertEqual(definition["name"], "test_def_tool")
        self.assertEqual(definition["description"], "Test description")

    def test_action_reset_input_schema_regenerates(self):
        """Test action_reset_input_schema() regenerates schema"""
        # Create tool with custom schema
        tool = self._create_test_tool(
            decorator_model="res.users",
            decorator_method="read",
            input_schema=json.dumps({"custom": "schema"}),
        )

        original_schema = json.loads(tool.input_schema)

        # Reset should regenerate
        tool.action_reset_input_schema()

        new_schema = json.loads(tool.input_schema)

        # Schema should have changed
        self.assertNotEqual(new_schema, original_schema)
        self.assertIsInstance(new_schema, dict)

    def test_onchange_implementation_populates_empty_schema(self):
        """Test _onchange_implementation() populates schema when empty"""
        tool = self.LLMTool.new(
            {
                "name": "test_tool",
                "description": "Test",
                "decorator_model": "res.users",
                "decorator_method": "read",
            }
        )

        # Set implementation (triggers onchange)
        tool.implementation = "function"
        tool._onchange_implementation()

        # Schema should be populated
        self.assertTrue(tool.input_schema)
        schema = json.loads(tool.input_schema)
        self.assertIsInstance(schema, dict)

    def test_onchange_implementation_preserves_existing_schema(self):
        """Test _onchange_implementation() doesn't overwrite existing schema"""
        custom_schema = {"custom": "schema"}

        tool = self.LLMTool.new(
            {
                "name": "test_tool",
                "description": "Test",
                "decorator_model": "res.users",
                "decorator_method": "read",
                "input_schema": json.dumps(custom_schema),
            }
        )

        # Set implementation (triggers onchange)
        tool.implementation = "function"
        tool._onchange_implementation()

        # Schema should remain unchanged
        self.assertEqual(json.loads(tool.input_schema), custom_schema)
