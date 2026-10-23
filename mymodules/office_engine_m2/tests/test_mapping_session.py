import base64
from uuid import uuid4

from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase

from ..services import create_session, get_session_context, transition_session
from ..models.office_mapping_session import SESSION_STATES


class TestOfficeMappingSession(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group_user = cls.env.ref("base.group_user")
        cls.provider = cls.env["llm.provider"].create(
            {"name": "M2 Session Provider " + uuid4().hex, "service": "openai"}
        )
        cls.model = cls.env["llm.model"].create(
            {
                "name": "M2 Session Model " + uuid4().hex,
                "provider_id": cls.provider.id,
                "model_use": "chat",
            }
        )
        cls.company_b = cls.env["res.company"].search(
            [("id", "!=", cls.env.company.id)], order="id", limit=1
        )
        if not cls.company_b:
            raise AssertionError("CC-TEST-006 requires an existing second company fixture.")
        cls.user_a = cls._create_user("owner-a")
        cls.user_b = cls._create_user("owner-b")
        cls.target = cls.env["res.partner"].create(
            {
                "name": "Mapping Session Target " + uuid4().hex,
                "company_id": cls.env.company.id,
            }
        )
        cls.target_b = cls.env["res.partner"].create(
            {
                "name": "Mapping Session Target B " + uuid4().hex,
                "company_id": cls.company_b.id,
            }
        )

    @classmethod
    def _create_user(cls, prefix):
        return cls.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "M2 Session " + prefix,
                "login": "m2-session-" + prefix + "-" + uuid4().hex,
                "email": "m2-session-" + prefix + "-" + uuid4().hex + "@example.invalid",
                "groups_id": [(6, 0, [cls.group_user.id])],
                "company_ids": [(6, 0, [cls.env.company.id, cls.company_b.id])],
                "company_id": cls.env.company.id,
            }
        )

    def _input_context(self, user, company=None):
        company = company or self.env.company
        user_env = self.env(
            user=user.id,
            context={"allowed_company_ids": [company.id]},
        )
        thread = user_env["llm.thread"].create(
            {
                "name": "M2 Session Thread " + uuid4().hex,
                "provider_id": self.provider.id,
                "model_id": self.model.id,
            }
        )
        attachment = user_env["ir.attachment"].create(
            {
                "name": "mapping-template-" + uuid4().hex + ".xlsx",
                "type": "binary",
                "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "datas": base64.b64encode(b"synthetic-template-bytes"),
                "company_id": company.id,
            }
        )
        message = thread.message_post(
            body="Template attached for a session test.",
            llm_role="user",
            attachment_ids=[attachment.id],
        )
        return user_env, thread, message, attachment

    def _create(self, *, env=None, thread=None, message=None, attachment=None, target=None):
        env = env or self.env(
            user=self.user_a.id,
            context={"allowed_company_ids": [self.env.company.id]},
        )
        if thread is None or message is None or attachment is None:
            _env, thread, message, attachment = self._input_context(self.user_a)
        target = target or self.target
        return create_session(
            env,
            thread_id=thread.id,
            source_message_id=message.id,
            source_attachment_id=attachment.id,
            target_model=target._name,
            target_record_id=target.id,
        )

    def test_cc_test_001_create_minimal_session_from_current_user_context(self):
        user_env, thread, message, attachment = self._input_context(self.user_a)
        context = self._create(
            env=user_env, thread=thread, message=message, attachment=attachment
        )
        session = user_env["office.mapping.session"].browse(context["session_id"])

        self.assertEqual(session.owner_id, self.user_a)
        self.assertEqual(session.company_id, user_env.company)
        self.assertEqual(session.thread_id, thread)
        self.assertEqual(session.source_message_id, message)
        self.assertEqual(session.source_attachment_id, attachment)
        self.assertEqual(session.target_model, "res.partner")
        self.assertEqual(session.target_record_id, self.target.id)
        self.assertEqual(session.state, "collecting")
        self.assertEqual(session.revision, 1)
        self.assertEqual(context["state"], "collecting")

    def test_cc_test_002_denies_other_users_thread_and_unreadable_target(self):
        _user_a_env, thread_a, message_a, attachment_a = self._input_context(self.user_a)
        _user_b_env, thread_b, message_b, attachment_b = self._input_context(self.user_b)
        user_a_env = self.env(
            user=self.user_a.id,
            context={"allowed_company_ids": [self.env.company.id]},
        )
        sessions_before = self.env["office.mapping.session"].search_count([])

        with self.assertRaises(AccessError):
            self._create(
                env=user_a_env,
                thread=thread_b.with_env(user_a_env),
                message=message_b.with_env(user_a_env),
                attachment=attachment_b.with_env(user_a_env),
            )

        # Bind an attachment belonging to user B as the target record. User A
        # has no read access to it under ir.attachment's record rules.
        with self.assertRaises(AccessError):
            create_session(
                user_a_env,
                thread_id=thread_a.id,
                source_message_id=message_a.id,
                source_attachment_id=attachment_a.id,
                target_model="ir.attachment",
                target_record_id=attachment_b.id,
            )
        self.assertEqual(
            self.env["office.mapping.session"].search_count([]), sessions_before
        )

    def test_cc_test_003_attachment_must_be_attached_to_the_same_thread_message(self):
        user_env, thread, message, _attachment = self._input_context(self.user_a)
        unrelated = user_env["ir.attachment"].create(
            {
                "name": "unrelated-" + uuid4().hex + ".xlsx",
                "type": "binary",
                "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "datas": base64.b64encode(b"unrelated"),
            }
        )
        with self.assertRaises(AccessError):
            create_session(
                user_env,
                thread_id=thread.id,
                source_message_id=message.id,
                source_attachment_id=unrelated.id,
                target_model=self.target._name,
                target_record_id=self.target.id,
            )
        self.assertEqual(self.env["office.mapping.session"].search_count([]), 0)

        other_user_env, other_thread, other_message, foreign_attachment = self._input_context(self.user_b)
        self.assertNotIn(foreign_attachment, thread.attachment_ids)
        with self.assertRaises(AccessError):
            create_session(
                user_env,
                thread_id=thread.id,
                source_message_id=message.id,
                source_attachment_id=foreign_attachment.id,
                target_model=self.target._name,
                target_record_id=self.target.id,
            )
        self.assertEqual(self.env["office.mapping.session"].search_count([]), 0)

    def test_cc_test_004_rejects_direct_jump_to_completed_without_mutation(self):
        context = self._create()
        user_env = self.env(
            user=self.user_a.id,
            context={"allowed_company_ids": [self.env.company.id]},
        )
        session = user_env["office.mapping.session"].browse(context["session_id"])

        with self.assertRaises(ValidationError):
            transition_session(
                user_env,
                session.id,
                "completed",
                expected_revision=1,
            )
        session.invalidate_recordset(["state", "revision"])
        self.assertEqual(session.state, "collecting")
        self.assertEqual(session.revision, 1)

    def test_cc_test_005_all_frozen_states_and_revision_control(self):
        self.assertEqual(
            set(SESSION_STATES),
            {
                "collecting",
                "needs_clarification",
                "awaiting_confirmation",
                "editing",
                "rendering",
                "completed",
                "failed",
                "cancelled",
            },
        )
        context = self._create()
        user_env = self.env(
            user=self.user_a.id,
            context={"allowed_company_ids": [self.env.company.id]},
        )
        session_id = context["session_id"]

        result = transition_session(
            user_env, session_id, "needs_clarification", expected_revision=1
        )
        self.assertEqual((result["state"], result["revision"]), ("needs_clarification", 2))
        with self.assertRaises(ValidationError):
            transition_session(user_env, session_id, "collecting", expected_revision=1)
        self.assertEqual(get_session_context(user_env, session_id)["revision"], 2)

        result = transition_session(user_env, session_id, "editing", expected_revision=2)
        self.assertEqual((result["state"], result["revision"]), ("editing", 3))
        result = transition_session(
            user_env, session_id, "awaiting_confirmation", expected_revision=3
        )
        self.assertEqual((result["state"], result["revision"]), ("awaiting_confirmation", 4))
        result = transition_session(user_env, session_id, "rendering", expected_revision=4)
        self.assertEqual((result["state"], result["revision"]), ("rendering", 5))
        result = transition_session(user_env, session_id, "completed", expected_revision=5)
        self.assertEqual((result["state"], result["revision"]), ("completed", 6))

        with self.assertRaises(ValidationError):
            transition_session(user_env, session_id, "failed", expected_revision=6)

        # Exercise the clarification return paths and the failed/cancelled
        # terminal branches, including the stable error category write.
        clarification = self._create()
        clarification_id = clarification["session_id"]
        transition_session(user_env, clarification_id, "needs_clarification", 1)
        transition_session(user_env, clarification_id, "collecting", 2)
        transition_session(user_env, clarification_id, "awaiting_confirmation", 3)
        transition_session(user_env, clarification_id, "editing", 4)
        transition_session(user_env, clarification_id, "needs_clarification", 5)
        transition_session(user_env, clarification_id, "editing", 6)
        failed = transition_session(
            user_env, clarification_id, "failed", 7, error_code="provider_error"
        )
        self.assertEqual((failed["state"], failed["revision"]), ("failed", 8))
        self.assertEqual(
            get_session_context(user_env, clarification_id)["error_code"],
            "provider_error",
        )
        with self.assertRaises(ValidationError):
            transition_session(user_env, clarification_id, "collecting", 8)

        cancelled = self._create()
        cancelled_result = transition_session(
            user_env, cancelled["session_id"], "cancelled", 1
        )
        self.assertEqual(
            (cancelled_result["state"], cancelled_result["revision"]),
            ("cancelled", 2),
        )
        with self.assertRaises(ValidationError):
            transition_session(user_env, cancelled["session_id"], "collecting", 2)

    def test_cc_test_006_user_b_cannot_read_or_mutate_user_a_session(self):
        context = self._create()
        user_b_env = self.env(
            user=self.user_b.id,
            context={"allowed_company_ids": [self.env.company.id]},
        )
        sessions = user_b_env["office.mapping.session"]
        self.assertEqual(sessions.search_count([("id", "=", context["session_id"])]), 0)
        with self.assertRaises(AccessError):
            get_session_context(user_b_env, context["session_id"])
        with self.assertRaises(AccessError):
            transition_session(
                user_b_env,
                context["session_id"],
                "failed",
                expected_revision=1,
                error_code="unauthorized",
            )
        with self.assertRaises(AccessError):
            sessions.browse(context["session_id"]).read(["state"])

        # A user's Session created while Company B is the active/allowed
        # company is hidden when the same user narrows the environment to A.
        company_b_env, thread_b, message_b, attachment_b = self._input_context(
            self.user_a, company=self.company_b
        )
        company_b_context = self._create(
            env=company_b_env,
            thread=thread_b,
            message=message_b,
            attachment=attachment_b,
            target=self.target_b,
        )
        company_a_only_env = self.env(
            user=self.user_a.id,
            context={"allowed_company_ids": [self.env.company.id]},
        )
        self.assertEqual(
            company_a_only_env["office.mapping.session"].search_count(
                [("id", "=", company_b_context["session_id"])]
            ),
            0,
        )
        with self.assertRaises(AccessError):
            get_session_context(company_a_only_env, company_b_context["session_id"])

        before = self.env["office.mapping.session"].search_count([])
        with self.assertRaises(ValidationError):
            company_b_env["office.mapping.session"]._create_from_mapping_service(
                {
                    "thread_id": thread_b.id,
                    "source_message_id": message_b.id,
                    "source_attachment_id": attachment_b.id,
                    "target_model": self.target_b._name,
                    "target_record_id": self.target_b.id,
                    "prompt": "SENTINEL_MUST_NOT_PERSIST",
                }
            )
        self.assertEqual(self.env["office.mapping.session"].search_count([]), before)

    def test_cc_test_007_upgrade_registry_and_access_metadata_contract(self):
        model = self.env["ir.model"]._get("office.mapping.session")
        self.assertTrue(model)
        self.assertEqual(model.model, "office.mapping.session")
        access = self.env["ir.model.access"].search(
            [("model_id", "=", model.id), ("group_id", "=", self.group_user.id)],
            limit=1,
        )
        self.assertTrue(access.perm_read and access.perm_create and access.perm_write)
        self.assertFalse(access.perm_unlink)
        rule = self.env.ref("office_engine_m2.office_mapping_session_owner_company_rule")
        self.assertIn("owner_id", rule.domain_force)
        self.assertIn("company_id", rule.domain_force)
        self.assertEqual(
            set(self.env["office.mapping.session"]._fields).intersection(
                {"prompt", "template_text", "template_content", "business_data", "sample_values", "attachment_bytes", "raw_response"}
            ),
            set(),
        )

    def test_cc_test_008_direct_rpc_style_create_and_write_cannot_forge_server_fields(self):
        user_env, thread, message, attachment = self._input_context(self.user_a)
        session_model = user_env["office.mapping.session"]

        with self.assertRaises(AccessError):
            session_model.create(
                {
                    "thread_id": thread.id,
                    "source_message_id": message.id,
                    "source_attachment_id": attachment.id,
                    "target_model": self.target._name,
                    "target_record_id": self.target.id,
                    "owner_id": self.user_b.id,
                }
            )
        context = self._create(
            env=user_env, thread=thread, message=message, attachment=attachment
        )
        session = session_model.browse(context["session_id"])
        with self.assertRaises(AccessError):
            session.write({"state": "completed"})
        with self.assertRaises(AccessError):
            session.write({"owner_id": self.user_b.id})
        with self.assertRaises(AccessError):
            session.unlink()

        returned = get_session_context(user_env, session.id)
        self.assertEqual(set(returned), {
            "session_id", "owner_id", "company_id", "thread_id", "source_message_id",
            "source_attachment_id", "target_model", "target_record_id", "state",
            "revision", "error_code",
        })
