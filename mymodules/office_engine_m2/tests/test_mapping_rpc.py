import base64
import json
from uuid import uuid4

from odoo.exceptions import AccessError, ValidationError
from odoo.tests import HttpCase, TransactionCase
from odoo.tests.common import JsonRpcException

from ..services.mapping_service import (
    create_session,
    get_mapping_card_context,
    post_mapping_card,
    save_mapping_edits,
    set_mapping_context,
)


def _create_thread_attachment_message(env, provider, model, label):
    thread = env["llm.thread"].create(
        {"name": f"M2 Card {label} {uuid4().hex}", "provider_id": provider.id, "model_id": model.id}
    )
    attachment = env["ir.attachment"].create(
        {
            "name": f"mapping-{uuid4().hex}.xlsx",
            "type": "binary",
            "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "datas": base64.b64encode(b"synthetic mapping template"),
            "company_id": env.company.id,
        }
    )
    message = thread.message_post(
        body="Synthetic mapping template.",
        llm_role="user",
        attachment_ids=[attachment.id],
    )
    return thread, message, attachment


def _create_mapping_session(env, provider, model, label, target=None):
    thread, source_message, attachment = _create_thread_attachment_message(
        env, provider, model, label
    )
    target = target or env["res.partner"].create(
        {"name": f"M2 Mapping Target {uuid4().hex}", "company_id": env.company.id}
    )
    session_data = create_session(
        env,
        thread_id=thread.id,
        source_message_id=source_message.id,
        source_attachment_id=attachment.id,
        target_model=target._name,
        target_record_id=target.id,
    )
    session_id = session_data["session_id"]
    set_mapping_context(
        env,
        session_id,
        [
            {
                "element_id": "xlsx:Sheet1!B1",
                "required": True,
                "writable": True,
                "allowed_value_types": ["string"],
                "approved_to_skip": False,
            }
        ],
        {"name": "string", "display_name": "string"},
    )
    return env["office.mapping.session"].browse(session_id), thread


class TestOfficeMappingRpcTransactions(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.provider = cls.env["llm.provider"].create(
            {"name": "M2 RPC Provider " + uuid4().hex, "service": "openai"}
        )
        cls.model = cls.env["llm.model"].create(
            {"name": "M2 RPC Model " + uuid4().hex, "provider_id": cls.provider.id, "model_use": "chat"}
        )

    def _session(self):
        return _create_mapping_session(self.env, self.provider, self.model, "unit")

    def test_mapping_fields_are_service_managed_and_context_is_server_owned(self):
        session, _thread = self._session()
        self.assertEqual(session.confirmed_revision, 0)
        self.assertEqual(json.loads(session.mapping_rules_json)["mappings"], [])
        with self.assertRaises(AccessError):
            session.write({"mapping_rules_json": "{}"})
        with self.assertRaises(AccessError):
            session.write({"context_json": "{}"})
        with self.assertRaises(AccessError):
            session.write({"confirmed_revision": session.revision})

    def test_legal_edit_is_validated_persisted_and_revision_increments(self):
        session, _thread = self._session()
        context = get_mapping_card_context(self.env, session.id, 1)
        self.assertEqual(context["fields"][0]["field_id"], "display_name")
        result = save_mapping_edits(
            self.env,
            session.id,
            1,
            [{
                "element_id": "xlsx:Sheet1!B1",
                "source_field": "name",
                "value_type": "string",
            }],
        )
        session.invalidate_recordset()
        self.assertEqual(result["revision"], 2)
        self.assertEqual(session.revision, 2)
        self.assertEqual(session.state, "awaiting_confirmation")
        self.assertEqual(
            json.loads(session.mapping_rules_json)["mappings"],
            [{
                "element_id": "xlsx:Sheet1!B1",
                "source_field": "name",
                "value_type": "string",
            }],
        )
        self.assertEqual(session.confirmed_revision, 0)

    def test_illegal_field_is_rejected_without_persistence(self):
        session, _thread = self._session()
        before = (session.mapping_rules_json, session.revision, session.state)
        with self.assertRaises(ValidationError):
            save_mapping_edits(
                self.env,
                session.id,
                1,
                [{
                    "element_id": "xlsx:Sheet1!B1",
                    "source_field": "password",
                    "value_type": "string",
                }],
            )
        session.invalidate_recordset()
        self.assertEqual((session.mapping_rules_json, session.revision, session.state), before)

    def test_stale_revision_is_rejected_without_overwriting_first_update(self):
        session, _thread = self._session()
        edits = [{
            "element_id": "xlsx:Sheet1!B1",
            "source_field": "name",
            "value_type": "string",
        }]
        save_mapping_edits(self.env, session.id, 1, edits)
        saved_rules = session.mapping_rules_json
        with self.assertRaises(ValidationError):
            save_mapping_edits(self.env, session.id, 1, edits)
        session.invalidate_recordset()
        self.assertEqual(session.mapping_rules_json, saved_rules)
        self.assertEqual(session.revision, 2)

    def test_confirmation_binds_current_revision_and_cancel_is_service_only(self):
        session, _thread = self._session()
        save_mapping_edits(
            self.env,
            session.id,
            1,
            [{"element_id": "xlsx:Sheet1!B1", "source_field": "name", "value_type": "string"}],
        )
        from ..services.mapping_service import confirm_mapping, transition_session

        result = confirm_mapping(self.env, session.id, 2)
        session.invalidate_recordset()
        self.assertEqual(result["confirmed_revision"], 3)
        self.assertEqual(session.confirmed_revision, session.revision)
        transition_session(self.env, session.id, "cancelled", session.revision)
        session.invalidate_recordset()
        self.assertEqual(session.state, "cancelled")

    def test_incomplete_mapping_cannot_be_confirmed(self):
        session, _thread = self._session()
        from ..services.mapping_service import confirm_mapping

        with self.assertRaises(ValidationError):
            confirm_mapping(self.env, session.id, session.revision)
        session.invalidate_recordset()
        self.assertEqual(session.state, "collecting")
        self.assertEqual(session.revision, 1)
        self.assertEqual(session.confirmed_revision, 0)

    def test_posted_card_contains_only_fixed_server_authored_body(self):
        session, _thread = self._session()
        message = post_mapping_card(self.env, session.id)
        self.assertIn("Review the proposed document mapping.", message.body)
        self.assertEqual(
            message.body_json["office_mapping_card"]["type"], "office_mapping_card_v1"
        )

    def test_session_and_card_persist_only_mapping_schema_metadata(self):
        session, _thread = self._session()
        context = json.loads(session.context_json)
        rules = json.loads(session.mapping_rules_json)
        message = post_mapping_card(self.env, session.id)

        self.assertEqual(set(context), {"target_manifest", "allowed_fields"})
        self.assertEqual(
            set(rules), {"schema_version", "mappings", "clarifications", "skipped_targets"}
        )
        self.assertEqual(
            set(message.body_json["office_mapping_card"]),
            {"type", "session_id", "revision"},
        )
        self.assertNotIn("prompt", session._fields)
        self.assertNotIn("sample_values", session._fields)
        self.assertNotIn("AcmeSecretSampleValue", json.dumps([context, rules, message.body_json]))


class TestOfficeMappingRpcHttp(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.provider = cls.env["llm.provider"].create(
            {"name": "M2 RPC HTTP Provider " + uuid4().hex, "service": "openai"}
        )
        cls.model = cls.env["llm.model"].create(
            {"name": "M2 RPC HTTP Model " + uuid4().hex, "provider_id": cls.provider.id, "model_use": "chat"}
        )
        cls.mapping_session, cls.mapping_thread = _create_mapping_session(
            cls.env, cls.provider, cls.model, "browser"
        )
        cls.mapping_message = post_mapping_card(cls.env, cls.mapping_session.id)
        cls.other_user = cls.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "M2 RPC Other User " + uuid4().hex,
                "login": "m2-rpc-other-" + uuid4().hex,
                "email": "m2-rpc-other-" + uuid4().hex + "@example.invalid",
                "groups_id": [(6, 0, [cls.env.ref("base.group_user").id])],
                "company_ids": [(6, 0, [cls.env.company.id])],
                "company_id": cls.env.company.id,
            }
        )
        cls.other_user_env = cls.env(
            user=cls.other_user.id,
            context={"allowed_company_ids": [cls.env.company.id]},
        )
        cls.other_user_target = cls.env["res.partner"].create(
            {"name": "Shared Mapping Target " + uuid4().hex, "company_id": cls.env.company.id}
        )
        cls.other_mapping_session, cls.other_mapping_thread = _create_mapping_session(
            cls.other_user_env,
            cls.provider,
            cls.model,
            "other-browser",
            target=cls.other_user_target,
        )
        cls.other_mapping_message = post_mapping_card(
            cls.other_user_env, cls.other_mapping_session.id
        )

    def test_cross_user_context_rpc_raises_access_error(self):
        self.authenticate(self.other_user.login, "test-password")
        with self.assertRaises(JsonRpcException) as error:
            self.make_jsonrpc_request(
                "/office_engine_m2/mapping/context",
                {"session_id": self.mapping_session.id, "expected_revision": self.mapping_session.revision},
            )
        self.assertIn("odoo.exceptions.AccessError", str(error.exception))

    def test_http_update_rejects_old_revision(self):
        self.authenticate(self.other_user.login, "test-password")
        edits = [{
            "element_id": "xlsx:Sheet1!B1",
            "source_field": "name",
            "value_type": "string",
        }]
        result = self.make_jsonrpc_request(
            "/office_engine_m2/mapping/update",
            {"session_id": self.other_mapping_session.id, "expected_revision": 1, "edits": edits},
        )
        self.assertEqual(result["revision"], 2)
        response = self.url_open(
            "/office_engine_m2/mapping/update",
            data=json.dumps({
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "session_id": self.other_mapping_session.id,
                    "expected_revision": 1,
                    "edits": edits,
                },
            }).encode(),
            headers={"Content-Type": "application/json"},
        )
        error = response.json()["error"]
        self.assertEqual(error["data"]["name"], "odoo.exceptions.ValidationError")
        self.assertIn("MAPPING_REVISION_STALE", error["data"]["message"])

    def test_real_backend_browser_renders_select_and_saves_over_rpc(self):
        action_id = self.env.ref("llm_thread.llm_thread_action").id
        url = f"/odoo/action-{action_id}?active_id=llm.thread_{self.other_mapping_thread.id}"
        code = r"""
            (async () => {
                const waitFor = async (predicate, message) => {
                    const deadline = Date.now() + 20000;
                    while (Date.now() < deadline) {
                        if (predicate()) return;
                        await new Promise((resolve) => setTimeout(resolve, 100));
                    }
                    throw new Error(message);
                };
                await waitFor(() => document.querySelector('[data-testid="office-mapping-card"] select'),
                    "mapping card did not render");
                const select = document.querySelector('[data-testid="office-mapping-card"] select');
                if (!select.querySelector('option[value="name"]')) throw new Error("expected option missing");
                select.value = "name";
                select.dispatchEvent(new Event("change", { bubbles: true }));
                document.querySelector('[data-testid="mapping-save"]').click();
                await waitFor(() => document.querySelector('[data-testid="mapping-status"]')?.textContent.includes("Mapping saved"),
                    "save RPC did not complete");
                location.reload();
                await waitFor(() => document.querySelector('[data-testid="office-mapping-card"] select')?.value === "name",
                    "saved field was not restored after reload");
                console.log("test successful");
            })();
        """
        self.browser_js(url, code, login=self.other_user.login, timeout=90)
