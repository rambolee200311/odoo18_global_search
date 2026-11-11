"""TransactionCase coverage for M2 Retriever reuse and automated HVR."""

import hashlib
import logging
import os
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from openpyxl import Workbook, load_workbook
from odoo.exceptions import AccessError
from odoo.tests import TransactionCase

from .support import WorkbookVersionFixtures, attachment_values, synthetic_xlsx

_logger = logging.getLogger(__name__)


class TestOfficeRetrieverIntegration(WorkbookVersionFixtures, TransactionCase):
    def _office_tool(self, thread):
        thread._office_bind_tools()
        tool = thread.tool_ids.filtered(lambda item: item.name == "office")[:1]
        self.assertTrue(tool, "The single Office facade must be bound to the Thread.")
        return tool

    def _office_call(self, thread, tool, arguments):
        call = thread.message_post(
            body="Synthetic office tool call",
            body_json={"type": "tool_execution", "tool_name": "office", "status": "executing"},
            llm_role="tool",
            author_id=False,
        )
        result = tool.with_context(message=call).execute(arguments)
        call.write({
            "body_json": {
                "type": "tool_execution",
                "tool_name": "office",
                "status": "completed",
                "result": result,
            }
        })
        return result

    def _retriever_tool(self, thread):
        thread._office_bind_tools()
        tool = thread.tool_ids.filtered(lambda item: item.name == "odoo_record_retriever")[:1]
        self.assertTrue(tool, "The existing Odoo Record Retriever must remain independently bound.")
        return tool

    def _retriever_call(self, thread, tool, arguments):
        call = thread.message_post(
            body="Synthetic Retriever tool call",
            body_json={"type": "tool_execution", "tool_name": "odoo_record_retriever", "status": "executing"},
            llm_role="tool",
            author_id=False,
        )
        result = tool.with_context(message=call).execute(arguments)
        call.write({
            "body_json": {
                "type": "tool_execution",
                "tool_name": "odoo_record_retriever",
                "arguments": arguments,
                "status": "completed",
                "result": result,
            }
        })
        return result

    def test_retrieve_reuses_bound_retriever_without_current_and_preserves_identity(self):
        env, session, thread, _upload, _attachment = self._session_fixture()
        suffix = uuid4().hex
        partners = self.env["res.partner"].create([
            {
                "name": f"CB05 synthetic {suffix} {index}",
                "email": f"cb05-{suffix}-{index}@example.invalid",
                "phone": False if index == 0 else f"+1000000000{index}",
                "company_id": False,
            }
            for index in range(3)
        ])
        before = partners.read(["name", "email", "phone"])
        session_before = (session.current_version_id.id, session.last_valid_version_id.id, session.document_revision)
        tool = self._retriever_tool(thread)

        user_message = thread.message_post(
            body="Read three authorized contacts for the current workbook.",
            llm_role="user",
            author_id=env.user.partner_id.id,
        )
        first = self._retriever_call(thread, tool, {
            "model": "res.partner",
            "domain": [["email", "like", f"cb05-{suffix}-%"]],
            "fields": ["name", "email", "phone"],
            "limit": 3,
            "offset": 0,
            "include_pagination": True,
        })

        self.assertEqual(first["count"], 3)
        self.assertFalse(first["has_more"])
        first_ids = [row["id"] for row in first["records"]]
        self.assertEqual(first_ids, partners.ids)
        self.assertIs(first["records"][0]["phone"], False)
        self.assertIn(user_message, thread.message_ids)
        session.invalidate_recordset()
        self.assertFalse(session.current_version_id)
        self.assertFalse(session.last_valid_version_id)
        self.assertEqual(session.document_revision, session_before[2])

        # Follow-up reads use the original Odoo identities, never worksheet rows.
        second_results = []
        for partner_id in first_ids:
            followup = thread.message_post(
                body=f"Read address fields for contact id {partner_id}.",
                llm_role="user",
                author_id=env.user.partner_id.id,
            )
            result = self._retriever_call(thread, tool, {
                "model": "res.partner",
                "domain": [["id", "=", partner_id]],
                "fields": ["name", "street", "street2", "city", "state_id", "zip", "country_id"],
                "limit": 1,
                "offset": 0,
                "include_pagination": True,
            })
            self.assertEqual(result["count"], 1)
            self.assertEqual(result["records"][0]["id"], partner_id)
            self.assertEqual(result["records"][0]["name"], partners.browse(partner_id).name)
            self.assertTrue(followup)
            second_results.append(result["records"][0])

        self.assertEqual([row["id"] for row in second_results], first_ids)
        self.assertEqual(partners.read(["name", "email", "phone"]), before)
        session.invalidate_recordset()
        self.assertEqual(
            (session.current_version_id.id, session.last_valid_version_id.id, session.document_revision),
            session_before,
        )

    def test_retriever_empty_result_keeps_existing_pagination_shape(self):
        env, _session, thread, _upload, _attachment = self._session_fixture()
        tool = self._retriever_tool(thread)
        empty = self._retriever_call(thread, tool, {
            "model": "res.partner",
            "domain": [["email", "=", f"missing-{uuid4().hex}@example.invalid"]],
            "fields": ["name"],
            "limit": 1,
            "offset": 0,
            "include_pagination": True,
        })
        self.assertEqual(empty, {
            "records": [], "count": 0, "offset": 0, "limit": 1, "has_more": False,
        })

    def test_retrieve_rejects_a_user_who_does_not_own_the_thread(self):
        env, _session, thread, _upload, _attachment = self._session_fixture()
        tool = self._retriever_tool(thread)
        thread.message_post(
            body="Owner query.", llm_role="user", author_id=env.user.partner_id.id,
        )
        call = thread.message_post(
            body="office", body_json={"type": "tool_execution", "tool_name": "office"},
            llm_role="tool", author_id=False,
        )
        other_env = self.env(user=self.other_user.id, context={"allowed_company_ids": [self.other_user.company_id.id]})
        with self.assertRaises(AccessError):
            tool.with_env(other_env).with_context(message=call.with_env(other_env)).execute({
                "model": "res.partner", "domain": [], "fields": ["name"],
            })

    def test_office_and_retriever_are_separate_tools_without_office_retrieve_action(self):
        _env, _session, thread, _upload, _attachment = self._session_fixture()
        tool = self._office_tool(thread)
        schema = tool.get_input_schema()
        self.assertNotIn("retrieve", schema["properties"]["action"]["enum"])
        self.assertNotIn("query_spec", schema["properties"])
        self.assertEqual(
            set(thread.tool_ids.filtered(lambda item: item.name in {"office", "odoo_record_retriever"}).mapped("name")),
            {"office", "odoo_record_retriever"},
        )

    def test_fresh_upload_and_pending_initial_candidate_keep_route_b_tools_visible(self):
        from odoo.addons.office_engine_m2.services.mapping_service import create_session

        env = self.env(user=self.owner.id, context={"allowed_company_ids": [self.owner.company_id.id]})
        thread = env["llm.thread"].create({
            "name": "Route B initial tool visibility " + uuid4().hex,
            "provider_id": self.provider.id,
            "model_id": self.model.id,
        })
        content = synthetic_xlsx("raw upload")
        attachment = env["ir.attachment"].create(attachment_values(
            "route-b-upload.xlsx", content, company_id=env.company.id,
        ))
        upload = thread.message_post(
            body="Create a workbook from this upload.", llm_role="user",
            author_id=env.user.partner_id.id, attachment_ids=[attachment.id],
        )
        self.assertEqual(upload.attachment_ids.ids, [attachment.id])
        classified = thread._office_engine_classify_attachments(upload.attachment_ids)
        self.assertEqual(classified.ids, [attachment.id])
        self.assertEqual(thread._office_upload_from_thread(thread), (upload, attachment))
        thread._office_bind_tools()
        self.assertTrue(thread._office_is_candidate_b_route())
        initial_session = create_session(
            env,
            thread_id=thread.id,
            source_message_id=upload.id,
            source_attachment_id=attachment.id,
            target_model="ir.attachment",
            target_record_id=attachment.id,
        )
        self.assertTrue(initial_session["session_id"])
        self.assertTrue(thread._office_has_route_b_session())
        self.assertTrue(thread._office_is_candidate_b_route())
        kwargs = thread._prepare_chat_kwargs(thread.get_llm_messages(), use_streaming=False)
        self.assertEqual(set(kwargs["tools"].mapped("name")), {"office", "odoo_record_retriever"})
        rules = next(
            item["content"] for item in kwargs["prepend_messages"]
            if item.get("role") == "system" and "Use the Route B Office workflow" in item.get("content", "")
        )
        self.assertIn("office(action='edit') directly", rules)
        self.assertIn("Successful `odoo_record_retriever` results", rules)
        self.assertNotIn("office(action='retrieve')", rules)

    def test_automated_user_simulation_two_contact_reads_and_formal_accepts(self):
        """Exercise raw-upload Candidate -> V1 -> second edit -> V2 with real services."""
        from odoo.addons.office_engine_m2.services.intent_contract import digest_json
        from .support.browser_simulation import ExpectedEffectWorkbookAdapter

        def contact_book_bytes():
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "Contacts"
            sheet.append(["名称", "电话", "邮件"])
            output = BytesIO()
            workbook.save(output)
            return output.getvalue()

        def result_effect(parent, source, target_range, assertions):
            effect = {
                "schema_version": "1",
                "parent_version_id": parent.id if parent else 0,
                "input_sha256": hashlib.sha256(source).hexdigest(),
                "target_scopes": [{"kind": "range", "sheet": "Contacts", "start": target_range[0], "end": target_range[1]}],
                "allowed_change_kinds": ["cell_value"],
                "expected_assertions": assertions,
                "unknowns": [],
            }
            effect["effect_digest"] = digest_json(effect)
            return effect

        def assertion(address, value):
            return {
                "kind": "cell_value", "sheet": "Contacts", "address": address,
                "value_type": "string", "value": value,
            }

        def interpretation(summary, scope):
            return {
                "summary": summary,
                "target_scope": {"description": scope, "basis": "explicit"},
                "assumptions": [],
                "unknowns": [],
            }

        def address_part(value):
            if isinstance(value, (list, tuple)) and len(value) == 2:
                value = value[1]
            return "" if value is False or value is None or value == "" else str(value)

        suffix = uuid4().hex
        partners = self.env["res.partner"].create([
            {
                "name": f"CB07 Contact {index} {suffix}",
                "phone": f"+12025550{index:03d}",
                "email": f"cb07-{suffix}-{index}@example.invalid",
                "street": f"{100 + index} Synthetic Street",
                "street2": "Unit 2" if index == 1 else False,
                "city": f"Test City {index}",
                "zip": f"1000{index}",
                "company_id": False,
            }
            for index in range(3)
        ])
        partner_before = partners.read(["name", "phone", "email", "street", "street2", "city", "zip"])
        env = self.env(user=self.owner.id, context={"allowed_company_ids": [self.owner.company_id.id]})
        source_bytes = contact_book_bytes()
        thread = env["llm.thread"].create({
            "name": "Route B Retriever integration " + suffix,
            "provider_id": self.provider.id,
            "model_id": self.model.id,
        })
        source_attachment = env["ir.attachment"].create(attachment_values(
            "contact-refresh-" + suffix + ".xlsx", source_bytes,
            company_id=env.company.id,
        ))
        upload = thread.message_post(
            body="Synthetic raw workbook upload.",
            llm_role="user",
            author_id=env.user.partner_id.id,
            attachment_ids=[source_attachment.id],
        )
        self.assertEqual(upload.attachment_ids.ids, [source_attachment.id])
        thread._office_bind_tools()
        self.assertTrue(thread._office_is_candidate_b_route())
        resolved_upload, resolved_attachment = thread._office_latest_upload()
        self.assertEqual(resolved_upload, upload)
        self.assertEqual(resolved_attachment, source_attachment)
        office_tool = thread.tool_ids.filtered(lambda item: item.name == "office")[:1]
        retriever_tool = thread.tool_ids.filtered(lambda item: item.name == "odoo_record_retriever")[:1]
        self.assertTrue(office_tool)
        self.assertTrue(retriever_tool)

        def invoke_office(args, *, effect=None):
            call = thread.message_post(
                body="Automated User Simulation office call",
                body_json={"type": "tool_execution", "tool_name": "office", "status": "executing"},
                llm_role="tool", author_id=False,
            )
            if effect is None:
                outcome = office_tool.with_context(message=call).execute(args)
            else:
                adapter = ExpectedEffectWorkbookAdapter(env, thread, call, effect)
                dependencies = (adapter, object(), "cb07-synthetic-mock", SimpleNamespace(synthetic=True))
                with patch(
                    "odoo.addons.office_engine_m2.tests.support.browser_simulation.dependencies_for",
                    return_value=dependencies,
                ):
                    outcome = office_tool.with_context(message=call).execute(args)
            call.write({"body_json": {
                "type": "tool_execution", "tool_name": "office", "status": "completed", "result": outcome,
            }})
            return outcome, adapter if effect is not None else None

        def accept_candidate(candidate_id):
            thread.message_post(body="接受", llm_role="user", author_id=env.user.partner_id.id)
            return invoke_office({"action": "accept", "candidate_version_id": candidate_id})[0]

        first_text = "请查询三位联系人并填写名称、电话和邮件。"
        first_intent = thread.message_post(body=first_text, llm_role="user", author_id=env.user.partner_id.id)
        first_read = self._retriever_call(thread, retriever_tool, {
            "model": "res.partner",
            "domain": [["email", "like", f"cb07-{suffix}-%"]],
            "fields": ["name", "phone", "email"],
            "limit": 3, "offset": 0, "include_pagination": True,
        })
        first_records = first_read["records"]
        first_ids = [record["id"] for record in first_records]
        self.assertEqual(first_ids, partners.ids)
        self.assertEqual(len(set(first_ids)), 3)
        first_values = [
            (f"{column}{row_number}", record[field])
            for row_number, record in enumerate(first_records, start=2)
            for column, field in zip("ABC", ("name", "phone", "email"))
        ]
        initial_effect = result_effect(
            None, source_bytes, ("A2", "C4"),
            [assertion(address, value) for address, value in first_values],
        )
        first_result, first_adapter = invoke_office({
            "action": "edit",
            "interpretation": interpretation(first_text, "Contacts!A2:C4"),
            "expected_effect": initial_effect,
            "model_risk_claims": [],
        }, effect=initial_effect)
        self.assertEqual(first_result["operation_status"], "candidate_review_required", first_result)
        session = env["office.mapping.session"].search([
            ("thread_id", "=", thread.id), ("source_message_id", "=", upload.id),
        ], limit=1)
        self.assertTrue(session)
        self.assertTrue(thread._office_is_candidate_b_route(), "Route B must persist while its initial Candidate is pending.")
        self.assertFalse(session.current_version_id)
        self.assertEqual(session.document_revision, 0)
        candidate1 = env["office.workbook.version"].browse(first_result["candidate_version_id"])
        self.assertEqual(candidate1.version_kind, "initial")
        self.assertFalse(candidate1.parent_version_id)
        self.assertEqual(candidate1.version_no, 1)
        self.assertEqual(candidate1.input_sha256, hashlib.sha256(source_bytes).hexdigest())
        self.assertEqual(candidate1.intent_message_id, first_intent)
        for record in first_records:
            self.assertIn(record["name"], first_adapter.last_instruction)
            self.assertIn(record["email"], first_adapter.last_instruction)
        first_accept = accept_candidate(candidate1.id)
        self.assertEqual(first_accept["operation_status"], "accepted_current", first_accept)
        session.invalidate_recordset()
        candidate1.invalidate_recordset()
        self.assertEqual(session.current_version_id, candidate1)
        self.assertEqual(session.last_valid_version_id, candidate1)
        self.assertEqual(session.document_revision, 1)
        self.assertEqual(candidate1.version_no, 1)
        self.assertEqual(candidate1.output_sha256, hashlib.sha256(candidate1.output_attachment_id.raw).hexdigest())
        workbook1 = load_workbook(BytesIO(candidate1.output_attachment_id.raw), data_only=False)
        for row_number, record in enumerate(first_records, start=2):
            for column, field in zip("ABC", ("name", "phone", "email")):
                self.assertEqual(workbook1["Contacts"][f"{column}{row_number}"].value, record[field])

        second_text = "请为这三位联系人补充 Odoo 地址，保留已填写内容。"
        thread.message_post(body=second_text, llm_role="user", author_id=env.user.partner_id.id)
        address_records = []
        for partner_id in first_ids:
            address_result = self._retriever_call(thread, retriever_tool, {
                "model": "res.partner",
                "domain": [["id", "=", partner_id]],
                "fields": ["street", "street2", "city", "state_id", "zip", "country_id"],
                "limit": 1, "offset": 0, "include_pagination": True,
            })
            address_record = address_result["records"][0]
            self.assertEqual(address_record["id"], partner_id)
            address_records.append(address_record)
        addresses = [", ".join(filter(None, [
            address_part(record.get("street")), address_part(record.get("street2")),
            address_part(record.get("city")), address_part(record.get("state_id")),
            address_part(record.get("zip")), address_part(record.get("country_id")),
        ])) for record in address_records]
        current_bytes = candidate1.output_attachment_id.raw
        second_effect = result_effect(
            candidate1, current_bytes, ("D1", "D4"),
            [assertion("D1", "地址"), *[
                assertion(f"D{row_number}", address)
                for row_number, address in enumerate(addresses, start=2)
            ]],
        )
        second_intent = interpretation(second_text, "Contacts!D1:D4")
        plan_result, _unused_adapter = invoke_office({
            "action": "plan",
            "interpretation": second_intent,
            "expected_effect": second_effect,
            "model_risk_claims": [],
            "confirmation_required": False,
            "confirmation_reason": "",
        })
        self.assertEqual(plan_result["operation_status"], "plan_ready", plan_result)
        second_result, second_adapter = invoke_office({
            "action": "edit",
            "interpretation": second_intent,
            "expected_effect": plan_result["expected_effect"],
            "model_risk_claims": [],
            "confirmation_required": False,
            "confirmation_reason": "",
        }, effect=plan_result["expected_effect"])
        self.assertEqual(second_result["operation_status"], "candidate_review_required", second_result)
        for record in address_records:
            self.assertIn(str(record["id"]), second_adapter.last_instruction)
        candidate2 = env["office.workbook.version"].browse(second_result["candidate_version_id"])
        self.assertEqual(candidate2.parent_version_id, candidate1)
        self.assertEqual(candidate2.input_sha256, candidate1.output_sha256)
        second_accept = accept_candidate(candidate2.id)
        self.assertEqual(second_accept["operation_status"], "accepted_current", second_accept)
        session.invalidate_recordset()
        candidate2.invalidate_recordset()
        self.assertEqual(session.current_version_id, candidate2)
        self.assertEqual(session.last_valid_version_id, candidate2)
        self.assertEqual(session.document_revision, 2)
        self.assertEqual(candidate2.version_no, 2)
        self.assertEqual(candidate2.output_sha256, hashlib.sha256(candidate2.output_attachment_id.raw).hexdigest())
        workbook2 = load_workbook(BytesIO(candidate2.output_attachment_id.raw), data_only=False)
        self.assertEqual(workbook2["Contacts"]["D1"].value, "地址")
        for row_number, record in enumerate(first_records, start=2):
            for column, field in zip("ABC", ("name", "phone", "email")):
                self.assertEqual(workbook2["Contacts"][f"{column}{row_number}"].value, workbook1["Contacts"][f"{column}{row_number}"].value)
            self.assertEqual(workbook2["Contacts"][f"D{row_number}"].value, addresses[row_number - 2])
        self.assertEqual(partners.read(["name", "phone", "email", "street", "street2", "city", "zip"]), partner_before)

        artifact_dir = os.environ.get("CB07_HVR_ARTIFACT_DIR")
        saved_artifacts = []
        if artifact_dir:
            output_dir = Path(artifact_dir)
            output_dir.mkdir(parents=True, exist_ok=False)
            for filename, content in (
                ("raw_upload.xlsx", source_bytes),
                ("accepted_v1.xlsx", candidate1.output_attachment_id.raw),
                ("accepted_v2.xlsx", candidate2.output_attachment_id.raw),
            ):
                (output_dir / filename).write_bytes(content)
                saved_artifacts.append(filename)
        _logger.info(
            "CC07_AUTOMATED_USER_SIMULATION thread=%s session=%s upload=%s initial_candidate=%s "
            "contact_ids=%s stage1_accept=%s stage1_current=%s stage1_revision=%s stage1_sha=%s "
            "stage2_candidate=%s stage2_parent=%s stage2_accept=%s stage2_current=%s stage2_revision=%s "
            "stage2_input_sha=%s stage2_output_sha=%s addresses=%s a_to_c_preserved=true contacts_unchanged=true "
            "artifact_dir=%s saved_artifacts=%s",
            thread.id, session.id, upload.id, candidate1.id, first_ids,
            first_accept.get("operation_status"), candidate1.id, 1, candidate1.output_sha256,
            candidate2.id, candidate2.parent_version_id.id, second_accept.get("operation_status"),
            candidate2.id, session.document_revision, candidate2.input_sha256,
            candidate2.output_sha256, addresses, artifact_dir, saved_artifacts,
        )
