from uuid import uuid4

from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase

from ..services import record_usage


class TestOfficeLlmUsage(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group_user = cls.env.ref("base.group_user")
        cls.operator_group = cls.env.ref(
            "office_engine_m2.group_office_usage_operator"
        )
        cls.provider = cls.env["llm.provider"].create(
            {"name": "M2 Usage Test Provider " + uuid4().hex, "service": "openai"}
        )
        cls.model = cls.env["llm.model"].create(
            {
                "name": "gpt-5.6-luna",
                "provider_id": cls.provider.id,
                "model_use": "chat",
            }
        )
        cls.admin_thread = cls.env["llm.thread"].create(
            {
                "name": "M2 Usage Admin-Owned Thread",
                "provider_id": cls.provider.id,
                "model_id": cls.model.id,
                "user_id": cls.env.user.id,
            }
        )
        cls.user = cls.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "M2 Usage Ordinary User",
                "login": "m2-usage-" + uuid4().hex,
                "email": "m2-usage-" + uuid4().hex + "@example.invalid",
                "groups_id": [(6, 0, [cls.group_user.id])],
            }
        )
        cls.operator = cls.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "M2 Usage Operator",
                "login": "m2-operator-" + uuid4().hex,
                "email": "m2-operator-" + uuid4().hex + "@example.invalid",
                "groups_id": [(6, 0, [cls.group_user.id, cls.operator_group.id])],
            }
        )

    def _record(self, *, env=None, **kwargs):
        env = env or self.env
        kwargs.setdefault("outcome", "success")
        return record_usage(
            env,
            model=self.model.with_env(env),
            **kwargs,
        )

    def test_cc_test_005_writes_minimal_usage_metadata_and_distinguishes_zero(self):
        result = self._record(
            usage={
                "prompt_tokens": 0,
                "completion_tokens": 3,
                "total_tokens": 3,
                "reasoning_tokens": None,
                "status": "available",
            },
            response_id="resp-safe-1",
            elapsed_ms=120,
            attempt_no=1,
        )
        record = self.env["office.llm.usage"].search(
            [("call_uuid", "=", result["call_uuid"])]
        )
        self.assertEqual(len(record), 1)
        self.assertEqual(record.prompt_tokens, 0)
        self.assertEqual(record.completion_tokens, 3)
        self.assertEqual(record.total_tokens, 3)
        self.assertIsNone(record.reasoning_tokens)
        self.assertEqual(record.owner_id, self.env.user)
        self.assertEqual(record.company_id, self.env.company)
        self.assertEqual(record.provider_code, "openai")
        self.assertEqual(record.model_name, "gpt-5.6-luna")
        self.assertEqual(record.response_id, "resp-safe-1")
        self.assertEqual(record.error_code, False)
        self.assertNotIn("usage_status", record._fields)
        forbidden_fields = {
            "prompt",
            "completion",
            "prompt_text",
            "response_text",
            "api_key",
            "template_content",
            "business_data",
            "raw_response",
        }
        self.assertFalse(forbidden_fields.intersection(record._fields))

        another = self._record(
            usage={
                "prompt_tokens": 1,
                "completion_tokens": 1,
                "total_tokens": 2,
                "status": "available",
            },
            attempt_no=2,
        )
        self.assertNotEqual(result["call_uuid"], another["call_uuid"])

    def test_missing_partial_and_invalid_status_codes_use_error_code(self):
        missing = self._record(usage=None, outcome="success")
        missing_record = self.env["office.llm.usage"].search(
            [("call_uuid", "=", missing["call_uuid"])]
        )
        self.assertEqual(missing["status"], "missing")
        self.assertEqual(missing_record.error_code, "usage_missing")
        self.assertIsNone(missing_record.prompt_tokens)
        self.assertIsNone(missing_record.attempt_no)

        partial = self._record(
            usage={
                "prompt_tokens": 5,
                "completion_tokens": None,
                "total_tokens": 5,
                "reasoning_tokens": None,
                "status": "partial",
            },
            outcome="provider_error",
            error_code="provider_error",
        )
        partial_record = self.env["office.llm.usage"].search(
            [("call_uuid", "=", partial["call_uuid"])]
        )
        self.assertEqual(partial_record.error_code, "usage_partial")
        self.assertEqual(partial_record.outcome, "provider_error")
        self.assertIsNone(partial_record.completion_tokens)

        invalid = self._record(
            usage={
                "prompt_tokens": None,
                "completion_tokens": 2,
                "total_tokens": 2,
                "reasoning_tokens": None,
                "status": "invalid",
            },
            outcome="processing_error",
        )
        invalid_record = self.env["office.llm.usage"].search(
            [("call_uuid", "=", invalid["call_uuid"])]
        )
        self.assertEqual(invalid_record.error_code, "usage_invalid")
        self.assertEqual(invalid_record.outcome, "processing_error")

    def test_service_rejects_prompts_business_data_raw_objects_and_unknown_keys(self):
        for forbidden in (
            {"prompt": "must never persist"},
            {"completion": "must never persist"},
            {"api_key": "synthetic-secret"},
            {"template_content": "sensitive template"},
            {"business_data": {"customer": "synthetic"}},
            {"file_bytes": b"synthetic"},
            {"unknown_field": "not allowlisted"},
        ):
            with self.subTest(forbidden=tuple(forbidden)):
                with self.assertRaises(ValidationError):
                    self._record(usage=None, **forbidden)
        with self.assertRaises(ValidationError):
            self._record(usage={"prompt_tokens": 1, "raw": "payload"})
        with self.assertRaises(ValidationError):
            self._record(usage=object())
        with self.assertRaises(ValidationError):
            self._record(
                usage={
                    "prompt_tokens": -1,
                    "completion_tokens": 1,
                    "total_tokens": 0,
                    "status": "invalid",
                }
            )
        self.assertFalse(self.env["office.llm.usage"].search([]))

    def test_cc_test_006_acl_and_internal_create_are_restricted(self):
        user_env = self.env(user=self.user.id)
        created = self._record(
            env=user_env,
            usage={
                "prompt_tokens": 1,
                "completion_tokens": 1,
                "total_tokens": 2,
                "status": "available",
            },
        )
        usage_model = self.env["office.llm.usage"]
        usage = usage_model.search([("call_uuid", "=", created["call_uuid"])])
        self.assertEqual(usage.owner_id, self.user)
        self.assertEqual(usage.company_id, user_env.company)

        ordinary_model = usage_model.with_user(self.user)
        ordinary_usage = ordinary_model.browse(usage.id)
        with self.assertRaises(AccessError):
            ordinary_model.search([])
        with self.assertRaises(AccessError):
            ordinary_model.create({"model_name": "forbidden"})
        with self.assertRaises(AccessError):
            ordinary_usage.write({"error_code": "tamper"})
        with self.assertRaises(AccessError):
            ordinary_usage.unlink()

        operator_usage = usage_model.with_user(self.operator).browse(usage.id)
        self.assertEqual(operator_usage.read(["call_uuid"])[0]["call_uuid"], created["call_uuid"])
        with self.assertRaises(AccessError):
            operator_usage.write({"error_code": "tamper"})
        with self.assertRaises(AccessError):
            operator_usage.unlink()

        admin_usage = usage_model.with_user(self.env.ref("base.user_admin")).browse(usage.id)
        self.assertEqual(admin_usage.read(["call_uuid"])[0]["call_uuid"], created["call_uuid"])
        with self.assertRaises(AccessError):
            admin_usage.write({"error_code": "tamper"})
        with self.assertRaises(AccessError):
            admin_usage.unlink()

        user_env = self.env(user=self.user.id)
        with self.assertRaises(AccessError):
            self._record(
                env=user_env,
                thread=self.admin_thread.with_env(user_env),
                usage={
                    "prompt_tokens": 1,
                    "completion_tokens": 1,
                    "total_tokens": 2,
                    "status": "available",
                },
            )

    def test_addon_model_and_acl_schema_are_registered(self):
        self.assertIn("office.llm.usage", self.env.registry.models)
        self.assertIn("call_uuid", self.env["office.llm.usage"]._fields)
        self.assertNotIn("usage_status", self.env["office.llm.usage"]._fields)
        self.assertTrue(self.operator_group)
