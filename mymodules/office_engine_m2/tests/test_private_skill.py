"""Private Skill persistence, isolation, matching, and live-data tests."""

import base64
import json
from contextlib import contextmanager
from io import BytesIO
from unittest.mock import patch
from uuid import uuid4

from openpyxl import Workbook, load_workbook
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase
from office_core import ResourceBudget, render_candidate
from office_verify import VerificationBudget, VerificationPolicy, verify_output

from odoo.addons.office_engine_odoo.models.office_document_request import _internal_mutation

from ..services.mapping_service import (
    confirm_mapping,
    create_session,
    save_mapping_edits,
    set_mapping_context,
)
from ..services.private_skill_service import (
    match_for_request,
    save_from_success,
    select_skill_for_request,
    skill_context_for_request,
)
from ..services.render_bridge import _stable_request_uuid, render_confirmed_mapping, render_preview


XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _xlsx(label="Customer", placeholder="Fill customer"):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Sheet1"
    sheet["A1"] = label
    sheet["B1"] = placeholder
    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


def _budgets():
    return (
        ResourceBudget(
            max_file_size=8 * 1024 * 1024,
            max_expanded_size=32 * 1024 * 1024,
            max_zip_entries=128,
            max_entry_size=8 * 1024 * 1024,
            max_xml_elements=100_000,
            max_cells=50_000,
            max_paragraphs=10_000,
            max_memory_bytes=2 * 1024 * 1024 * 1024,
            timeout_seconds=15,
        ),
        VerificationBudget(
            max_file_size=8 * 1024 * 1024,
            max_expanded_size=32 * 1024 * 1024,
            max_zip_entries=128,
            max_entry_size=8 * 1024 * 1024,
            max_xml_elements=100_000,
            max_cells=50_000,
            max_paragraphs=10_000,
            max_mapping_bytes=64 * 1024,
            max_memory_bytes=2 * 1024 * 1024 * 1024,
            timeout_seconds=15,
        ),
    )


@contextmanager
def _test_context():
    yield


class TestPrivateOfficeExportSkill(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.provider = cls.env["llm.provider"].create(
            {"name": "M2-006 Skill Provider " + uuid4().hex, "service": "openai"}
        )
        cls.model = cls.env["llm.model"].create(
            {
                "name": "gpt-5.6-luna",
                "provider_id": cls.provider.id,
                "model_use": "chat",
            }
        )

    def _new_session(
        self,
        *,
        label="Customer",
        target=None,
        model_name="res.partner",
        env=None,
        template_bytes=None,
    ):
        env = env or self.env
        target = target or env[model_name].create(
            {"name": "Initial customer " + uuid4().hex, "company_id": env.company.id}
        )
        thread = env["llm.thread"].create(
            {
                "name": "M2-006 private Skill " + uuid4().hex,
                "provider_id": self.provider.id,
                "model_id": self.model.id,
            }
        )
        source_bytes = template_bytes if template_bytes is not None else _xlsx(label=label)
        attachment = env["ir.attachment"].create(
            {
                "name": "m2-006-" + uuid4().hex + ".xlsx",
                "type": "binary",
                "mimetype": XLSX_MIME,
                "raw": source_bytes,
                "company_id": env.company.id,
            }
        )
        message = thread.message_post(
            body="Generate a document from the authorized target.",
            llm_role="user",
            attachment_ids=[attachment.id],
        )
        session_data = create_session(
            env,
            thread_id=thread.id,
            source_message_id=message.id,
            source_attachment_id=attachment.id,
            target_model=target._name,
            target_record_id=target.id,
        )
        session = env["office.mapping.session"].browse(session_data["session_id"])
        set_mapping_context(
            env,
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
        return session, thread, message, attachment, target, source_bytes

    def _complete_mapping(self, *, target=None, label="Customer"):
        session, thread, message, source, target, source_bytes = self._new_session(
            target=target, label=label
        )
        save_mapping_edits(
            self.env,
            session.id,
            session.revision,
            [
                {
                    "element_id": "xlsx:Sheet1!B1",
                    "source_field": "name",
                    "value_type": "string",
                }
            ],
        )
        session.invalidate_recordset()
        with _test_context():
            preview = render_preview(self.env, session.id, session.revision)
        session.invalidate_recordset()
        confirmation = confirm_mapping(self.env, session.id, preview["revision"])
        marked = session._mark_confirmed_from_service(confirmation["revision"])
        session.invalidate_recordset()
        session._transition_from_service("generating", marked["revision"])
        session.invalidate_recordset()
        session._transition_from_service("completed", session.revision)
        session.invalidate_recordset()
        fingerprint = self.env["office.document.request"]._inspect_chat_attachment(
            source, thread, message
        )["template_sha256"]
        request_uuid = _stable_request_uuid(self.env, session)
        request_model = self.env["office.document.request"]
        with _internal_mutation():
            request = request_model.create(
                {
                    "request_uuid": request_uuid,
                    "thread_id": thread.id,
                    "input_message_id": message.id,
                    "source_attachment_id": source.id,
                    "input_sha256": fingerprint,
                }
            )
            request.write({"state": "validating"})
            request.write({"state": "processing"})
            output = self.env["ir.attachment"].create(
                {
                    "name": "m2-006-output-" + uuid4().hex + ".xlsx",
                    "type": "binary",
                    "mimetype": XLSX_MIME,
                    "raw": b"synthetic private M1 delivery fixture",
                    "public": False,
                    "res_model": request._name,
                    "res_id": request.id,
                    "company_id": self.env.company.id,
                }
            )
            request.write(
                {
                    "output_attachment_id": output.id,
                    "output_sha256": "a" * 64,
                    "state": "generated",
                }
            )
        return session, thread, message, source, target, source_bytes, confirmation, request

    def _save_skill(self, *, name="Customer export", target=None, label="Customer"):
        completed = self._complete_mapping(target=target, label=label)
        session = completed[0]
        with _test_context():
            result = save_from_success(self.env, session.id, session.revision, name)
        return result, completed

    def test_uncompleted_session_cannot_save_a_skill(self):
        session, *_rest = self._new_session()
        skill_name = "Not generated " + uuid4().hex
        with self.assertRaises(ValidationError):
            save_from_success(self.env, session.id, session.revision, skill_name)
        self.assertEqual(
            self.env["office.export.skill"].search_count(
                [("owner_id", "=", self.env.uid), ("name", "=", skill_name)]
            ),
            0,
        )

    def test_only_a_delivered_completed_session_creates_a_value_free_skill(self):
        (saved, completed) = self._save_skill()
        session, _thread, _message, _source, target, _bytes, _confirmation, request = completed
        skill = self.env["office.export.skill"].browse(saved["skill_id"])
        self.assertEqual(skill.owner_id, self.env.user)
        self.assertEqual(skill.company_id, self.env.company)
        self.assertEqual(skill.template_fingerprint, request.input_sha256)
        self.assertEqual(skill.model_name, "res.partner")
        self.assertEqual(skill.state, "active")
        self.assertEqual(json.loads(skill.mapping_rules_json)["mappings"][0]["source_field"], "name")
        self.assertNotIn(target.name, skill.mapping_rules_json)
        self.assertNotIn(str(target.id), skill.mapping_rules_json)
        self.assertNotIn(str(_source.id), skill.mapping_rules_json)
        with _test_context():
            self.assertEqual(
                save_from_success(self.env, session.id, session.revision, "Customer export")["skill_id"],
                skill.id,
            )

    def test_completed_card_can_show_saved_skill_with_default_environment(self):
        (saved, completed) = self._save_skill(name="Completed card skill")
        session = completed[0]
        result = skill_context_for_request(self.env, session.id)
        self.assertEqual(
            result["saved_skills"],
            [{"skill_id": saved["skill_id"], "name": "Completed card skill"}],
        )

    def test_failure_or_missing_output_request_cannot_be_saved(self):
        session, _thread, _message, _source, _target, _bytes = self._new_session()
        session._transition_from_service("failed", session.revision, error_code="synthetic_failure")
        skill_name = "Failed export " + uuid4().hex
        with self.assertRaises(ValidationError):
            save_from_success(self.env, session.id, session.revision, skill_name)
        self.assertEqual(
            self.env["office.export.skill"].search_count(
                [("owner_id", "=", self.env.uid), ("name", "=", skill_name)]
            ),
            0,
        )

    def test_skill_model_denies_client_create_write_and_unlink(self):
        model = self.env["office.export.skill"]
        with self.assertRaises(AccessError):
            model.create({})
        with self.assertRaises(AccessError):
            model.browse().write({"name": "forged"})
        with self.assertRaises(AccessError):
            model.browse().unlink()

    def test_owner_and_company_record_rule_hides_another_users_skill(self):
        (saved, completed) = self._save_skill()
        session, _thread, _message, _source, _target, _bytes, _confirmation, _request = completed
        other = self.env["res.users"].create(
            {
                "name": "M2-006 other user " + uuid4().hex,
                "login": "m2-006-" + uuid4().hex,
                "email": "m2-006-" + uuid4().hex + "@example.invalid",
                "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
                "company_id": self.env.company.id,
                "company_ids": [(6, 0, [self.env.company.id])],
            }
        )
        other_env = self.env(user=other)
        self.assertFalse(other_env["office.export.skill"].search([("id", "=", saved["skill_id"])]))
        with self.assertRaises(AccessError):
            other_env["office.export.skill"].browse(saved["skill_id"]).read(["name"])

        # User B's own session cannot match A's private Skill or discover its existence.
        target_a = completed[4]
        target_a.with_env(other_env).check_access("read")
        session_b, *_ = self._new_session(
            target=target_a.with_env(other_env),
            env=other_env,
            template_bytes=completed[5],
        )
        service_result = match_for_request(other_env, session_b.id)
        self.assertEqual(service_result["status"], "none")
        with self.assertRaises(AccessError):
            select_skill_for_request(other_env, session_b.id, session_b.revision, saved["skill_id"])
        self.assertEqual(session.state, "completed")

    def test_fingerprint_and_model_must_match_exactly(self):
        _saved, completed = self._save_skill()
        _session, _thread, _message, _source, target, _bytes, _confirmation, _request = completed
        changed = self.env["llm.thread"].create(
            {
                "name": "M2-006 changed fingerprint " + uuid4().hex,
                "provider_id": self.provider.id,
                "model_id": self.model.id,
            }
        )
        altered_bytes = _xlsx(label="Customer", placeholder="Changed bytes")
        attachment = self.env["ir.attachment"].create(
            {
                "name": "m2-006-changed-" + uuid4().hex + ".xlsx",
                "type": "binary",
                "mimetype": XLSX_MIME,
                "raw": altered_bytes,
                "company_id": self.env.company.id,
            }
        )
        message = changed.message_post(
            body="Changed template request.", llm_role="user", attachment_ids=[attachment.id]
        )
        created = create_session(
            self.env,
            thread_id=changed.id,
            source_message_id=message.id,
            source_attachment_id=attachment.id,
            target_model="res.partner",
            target_record_id=target.id,
        )
        session = self.env["office.mapping.session"].browse(created["session_id"])
        set_mapping_context(
            self.env,
            session.id,
            [{"element_id": "xlsx:Sheet1!B1", "required": True, "writable": True,
              "allowed_value_types": ["string"], "approved_to_skip": False}],
            {"name": "string"},
        )
        self.assertEqual(match_for_request(self.env, session.id)["status"], "none")
        with self.assertRaises(ValidationError):
            match_for_request(
                self.env,
                session.id,
                template_fingerprint="0" * 64,
                model_name="res.partner",
            )
        with self.assertRaises(ValidationError):
            match_for_request(self.env, session.id, model_name="res.company")

    def test_matching_logs_skill_id_skips_provider_and_keeps_confirmation(self):
        (saved, completed) = self._save_skill()
        _first, _thread, _message, _source, target, _bytes, _confirmation, _request = completed
        second, *_rest = self._new_session(target=target, template_bytes=completed[5])
        logger = "odoo.addons.office_engine_m2.services.private_skill_service"
        with _test_context(), self.assertLogs(logger, level="INFO") as logs, patch.object(
            type(self.model), "chat", autospec=True
        ) as provider:
            result = match_for_request(self.env, second.id)
        self.assertEqual(provider.call_count, 0)
        self.assertEqual(result["status"], "matched")
        self.assertEqual(result["skill_id"], saved["skill_id"])
        self.assertTrue(result["requires_confirmation"])
        self.assertIn("SKILL_MATCHED: %s" % saved["skill_id"], "\n".join(logs.output))
        second.invalidate_recordset()
        self.assertEqual(second.state, "confirmation_required")
        skill_reply = second.thread_id.message_ids.filtered(
            lambda message: "匹配私有技能“Customer export”" in (message.body or "")
        )
        self.assertTrue(skill_reply)
        self.assertTrue(second.preview_attachment_id)
        with _test_context():
            context = skill_context_for_request(self.env, second.id, saved["skill_id"])
        self.assertIn(target.display_name, context["target_summary"])
        self.assertEqual(context["model_name"], "res.partner")

    def test_skill_hit_uses_latest_data_through_m1_engine(self):
        (_saved, completed) = self._save_skill()
        _first, _thread, _message, _source, target, _bytes, _confirmation, _request = completed
        skill = self.env["office.export.skill"].browse(_saved["skill_id"])
        target.write({"name": "Changed after original generation"})
        second, _thread2, _message2, source2, _target2, _source_bytes2 = self._new_session(
            target=target, template_bytes=completed[5]
        )
        with _test_context(), patch.object(type(self.model), "chat", autospec=True) as provider:
            self.assertEqual(skill.owner_id.id, self.env.uid)
            self.assertEqual(skill.company_id.id, second.company_id.id)
            self.assertEqual(skill.model_name, second.target_model)
            fingerprint = self.env["office.document.request"]._inspect_chat_attachment(
                second.source_attachment_id, second.thread_id, second.source_message_id
            )["template_sha256"]
            self.assertEqual(fingerprint, skill.template_fingerprint)
            match = match_for_request(self.env, second.id, selected_skill_id=_saved["skill_id"])
            self.assertEqual(provider.call_count, 0)
            self.assertEqual(match["status"], "matched")
            confirmed = confirm_mapping(self.env, second.id, match["revision"])
            generated = []
            request_model = self.env["office.document.request"]
            core_budget, verify_budget = _budgets()

            def render_real_engine(_model, request_uuid, source_attachment_id, plan, thread_id, message_id):
                source_attachment = self.env["ir.attachment"].browse(source_attachment_id)
                candidate = render_candidate(
                    source_attachment.raw, source_attachment.name, XLSX_MIME, plan, core_budget
                )
                report = verify_output(
                    source_attachment.raw,
                    candidate.content,
                    source_attachment.name,
                    XLSX_MIME,
                    plan,
                    VerificationPolicy(enabled_formats=("xlsx",), require_styles=True),
                    verify_budget,
                )
                generated.append((report.status, candidate.content, plan))
                # This test isolates private-skill reuse and M1 rendering; the
                # M1 boundary reports a committed chat delivery on success.
                return {
                    "state": "generated",
                    "output_attachment_id": 2_100_006_001,
                    "delivery_message_id": 2_100_006_002,
                }

            with patch.object(
                type(request_model), "_render_request_sync", autospec=True, side_effect=render_real_engine
            ) as m1:
                result = render_confirmed_mapping(self.env, second.id, confirmed["revision"])

        self.assertEqual(provider.call_count, 0)
        self.assertEqual(m1.call_count, 1)
        self.assertEqual(result["state"], "completed")
        self.assertEqual(generated[0][0], "PASS")
        self.assertEqual(generated[0][2]["writes"][0]["value"]["data"], "Changed after original generation")
        output = load_workbook(BytesIO(generated[0][1]), data_only=False)
        try:
            self.assertEqual(output["Sheet1"]["B1"].value, "Changed after original generation")
        finally:
            output.close()
        self.assertEqual(source2.name.rsplit(".", 1)[-1], "xlsx")

    def test_multiple_matches_are_returned_for_user_selection(self):
        saved, completed = self._save_skill(name="First skill")
        session, _thread, _message, source, target, _bytes, _confirmation, _request = completed
        skill = self.env["office.export.skill"].browse(saved["skill_id"])
        self.assertEqual(skill.owner_id.id, self.env.uid)
        self.assertEqual(skill.company_id.id, session.company_id.id)
        # Create a second valid private candidate via the same validated service-only path.
        duplicate = self.env["office.export.skill"].sudo().with_context(
            _office_engine_m2_private_skill_create=True
        ).create(
            {
                "name": "Second skill",
                "owner_id": self.env.uid,
                "company_id": self.env.company.id,
                "template_fingerprint": skill.template_fingerprint,
                "model_name": skill.model_name,
                "mapping_rules_json": skill.mapping_rules_json,
                "state": "active",
                "revision": 1,
            }
        )
        next_session, *_ = self._new_session(target=target, template_bytes=completed[5])
        self.assertEqual(next_session.target_model, skill.model_name)
        self.assertEqual(
            self.env["office.document.request"]._inspect_chat_attachment(
                next_session.source_attachment_id,
                next_session.thread_id,
                next_session.source_message_id,
            )["template_sha256"],
            skill.template_fingerprint,
        )
        self.assertEqual(
            self.env["office.export.skill"].search_count(
                [
                    ("owner_id", "=", self.env.uid),
                    ("company_id", "=", next_session.company_id.id),
                    ("template_fingerprint", "=", skill.template_fingerprint),
                    ("model_name", "=", next_session.target_model),
                    ("state", "=", "active"),
                ]
            ),
            2,
        )
        with _test_context():
            result = match_for_request(self.env, next_session.id)
        self.assertEqual(result["status"], "multiple")
        self.assertEqual({item["skill_id"] for item in result["candidates"]}, {skill.id, duplicate.id})
        self.assertEqual(next_session.state, "analyzing")
        with _test_context():
            selected = select_skill_for_request(
                self.env, next_session.id, result["revision"], duplicate.id
            )
        self.assertEqual(selected["status"], "matched")
        self.assertEqual(selected["skill_id"], duplicate.id)

    def test_inactive_or_invalid_skill_does_not_match(self):
        (saved, completed) = self._save_skill()
        skill = self.env["office.export.skill"].browse(saved["skill_id"])
        self.env.cr.execute("UPDATE office_export_skill SET state = %s WHERE id = %s", ["disabled", skill.id])
        skill.invalidate_recordset(["state"])
        session, *_ = self._new_session(target=completed[4])
        self.assertEqual(match_for_request(self.env, session.id)["status"], "none")
        with self.assertRaises(AccessError):
            skill.write({"state": "active"})

    def test_stale_revision_and_invalid_skill_name_are_rejected(self):
        (saved, completed) = self._save_skill()
        session = completed[0]
        with self.assertRaises(ValidationError):
            save_from_success(self.env, session.id, session.revision - 1, "stale")
        with self.assertRaises(ValidationError):
            save_from_success(self.env, session.id, session.revision, "   ")
        self.assertEqual(self.env["office.export.skill"].browse(saved["skill_id"]).name, "Customer export")
