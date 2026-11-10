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

from .support import WorkbookVersionFixtures

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
        tool = self._office_tool(thread)

        user_message = thread.message_post(
            body="Read three authorized contacts for the current workbook.",
            llm_role="user",
            author_id=env.user.partner_id.id,
        )
        first = self._office_call(thread, tool, {
            "action": "retrieve",
            "query_spec": {
                "model": "res.partner",
                "domain": [["email", "like", f"cb05-{suffix}-%"]],
                "fields": ["name", "email", "phone"],
                "limit": 3,
                "offset": 0,
                "include_pagination": True,
            },
        })

        self.assertEqual(first["status"], "completed", first)
        self.assertEqual(first["operation_status"], "odoo_data_retrieved")
        self.assertFalse(first["operation_executed"])
        self.assertEqual(first["data"]["count"], 3)
        self.assertFalse(first["data"]["has_more"])
        self.assertEqual(first["query_scope"]["order"], "id")
        self.assertTrue(first["retrieved_at"].endswith("Z"))
        first_ids = [row["id"] for row in first["data"]["records"]]
        self.assertEqual(first_ids, partners.ids)
        self.assertIs(first["data"]["records"][0]["phone"], False)
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
            result = self._office_call(thread, tool, {
                "action": "retrieve",
                "query_spec": {
                    "model": "res.partner",
                    "domain": [["id", "=", partner_id]],
                    "fields": ["name", "street", "street2", "city", "state_id", "zip", "country_id"],
                    "limit": 1,
                    "offset": 0,
                    "include_pagination": True,
                },
            })
            self.assertEqual(result["status"], "completed", result)
            self.assertEqual(result["data"]["count"], 1)
            self.assertEqual(result["data"]["records"][0]["id"], partner_id)
            self.assertEqual(result["data"]["records"][0]["name"], partners.browse(partner_id).name)
            self.assertTrue(followup)
            second_results.append(result["data"]["records"][0])

        self.assertEqual([row["id"] for row in second_results], first_ids)
        self.assertEqual(partners.read(["name", "email", "phone"]), before)
        session.invalidate_recordset()
        self.assertEqual(
            (session.current_version_id.id, session.last_valid_version_id.id, session.document_revision),
            session_before,
        )

    def test_retrieve_distinguishes_empty_result_from_missing_query(self):
        env, _session, thread, _upload, _attachment = self._session_fixture()
        tool = self._office_tool(thread)
        thread.message_post(
            body="Read a contact matching this nonexistent email.",
            llm_role="user",
            author_id=env.user.partner_id.id,
        )
        empty = self._office_call(thread, tool, {
            "action": "retrieve",
            "query_spec": {
                "model": "res.partner",
                "domain": [["email", "=", f"missing-{uuid4().hex}@example.invalid"]],
                "fields": ["name"],
                "limit": 1,
                "offset": 0,
                "include_pagination": True,
            },
        })
        self.assertEqual(empty["status"], "completed")
        self.assertEqual(empty["data"], {
            "records": [], "count": 0, "offset": 0, "limit": 1, "has_more": False,
        })

        thread.message_post(
            body="Retry with a missing query specification.",
            llm_role="user",
            author_id=env.user.partner_id.id,
        )
        missing = self._office_call(thread, tool, {"action": "retrieve"})
        self.assertEqual(missing["status"], "clarification_required")
        self.assertEqual(missing["operation_status"], "retriever_query_missing")

        thread.message_post(
            body="Reject an unsupported query extension.",
            llm_role="user",
            author_id=env.user.partner_id.id,
        )
        invalid = self._office_call(thread, tool, {
            "action": "retrieve",
            "query_spec": {"model": "res.partner", "snapshot_id": "not-supported"},
        })
        self.assertEqual(invalid["status"], "blocked")
        self.assertEqual(invalid["operation_status"], "retriever_query_invalid")

    def test_retrieve_rejects_a_user_who_does_not_own_the_thread(self):
        env, _session, thread, _upload, _attachment = self._session_fixture()
        tool = self._office_tool(thread)
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
                "action": "retrieve",
                "query_spec": {"model": "res.partner", "domain": [], "fields": ["name"]},
            })

    def test_office_schema_exposes_retrieve_without_a_second_public_tool(self):
        _env, _session, thread, _upload, _attachment = self._session_fixture()
        tool = self._office_tool(thread)
        schema = tool.get_input_schema()
        self.assertIn("retrieve", schema["properties"]["action"]["enum"])
        self.assertEqual(set(thread.tool_ids.filtered(lambda item: item.name == "office").mapped("name")), {"office"})
        self.assertFalse(schema["properties"]["query_spec"]["additionalProperties"])

    def test_automated_user_simulation_two_contact_reads_and_formal_accepts(self):
        """Two-stage contact HVR using a Mock Candidate adapter and real services."""
        from odoo.addons.office_engine_m2.services.intent_contract import digest_json
        from odoo.addons.office_engine_m2.services.workbook_version_service import register_initial_v1
        from .support.browser_simulation import ExpectedEffectWorkbookAdapter

        def contact_book_bytes():
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "Contacts"
            sheet.append(["名称", "电话", "邮件", None])
            # Predeclare the destination area and display format so this test
            # isolates value edits from serializer-only dimensions/styles.
            for row in range(2, 5):
                for column in range(1, 5):
                    sheet.cell(row, column).number_format = "@"
            sheet["D1"].number_format = "@"
            output = BytesIO()
            workbook.save(output)
            return output.getvalue()

        def result_effect(parent, source, sheet_name, target_range, assertions):
            effect = {
                "schema_version": "1",
                "parent_version_id": parent.id,
                "input_sha256": hashlib.sha256(source).hexdigest(),
                "target_scopes": [{"kind": "range", "sheet": sheet_name, "start": target_range[0], "end": target_range[1]}],
                "allowed_change_kinds": ["cell_value"],
                "expected_assertions": assertions,
                "unknowns": [],
            }
            effect["effect_digest"] = digest_json(effect)
            return effect

        def assertion(address, value):
            return {
                "kind": "cell_value",
                "sheet": "Contacts",
                "address": address,
                "value_type": "string",
                "value": value,
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
            if value is False or value is None or value == "":
                return ""
            return str(value)

        suffix = uuid4().hex
        partner_values = [
            {
                "name": f"CB05 Contact {index} {suffix}",
                "phone": f"+12025550{index:03d}",
                "email": f"cb05-{suffix}-{index}@example.invalid",
                "street": f"{100 + index} Synthetic Street",
                "street2": "Unit 2" if index == 1 else False,
                "city": f"Test City {index}",
                "zip": f"1000{index}",
                "company_id": False,
            }
            for index in range(3)
        ]
        partners = self.env["res.partner"].create(partner_values)
        partner_before = partners.read(["name", "phone", "email", "street", "street2", "city", "zip"])

        env, session, thread, _upload, _attachment = self._session_fixture()
        source_bytes = contact_book_bytes()
        request, _m1_output = self._m1_request_fixture(env, session, output_bytes=source_bytes)
        parent = register_initial_v1(env, session.id, request.id)
        session.invalidate_recordset()
        thread._office_bind_tools()
        office_tool = thread.tool_ids.filtered(lambda item: item.name == "office")[:1]
        self.assertTrue(office_tool)

        def invoke_office(args, *, adapter=None, effect=None):
            call = thread.message_post(
                body="Automated User Simulation office call",
                body_json={"type": "tool_execution", "tool_name": "office", "status": "executing"},
                llm_role="tool",
                author_id=False,
            )
            if adapter is None:
                outcome = office_tool.with_context(message=call).execute(args)
            else:
                adapter = ExpectedEffectWorkbookAdapter(env, thread, call, effect)
                dependency = (adapter, object(), "cb05-synthetic-mock", SimpleNamespace(synthetic=True))
                with patch(
                    "odoo.addons.office_engine_m2.tests.support.browser_simulation.dependencies_for",
                    return_value=dependency,
                ):
                    outcome = office_tool.with_context(message=call).execute(args)
            call.write({
                "body_json": {
                    "type": "tool_execution", "tool_name": "office", "status": "completed", "result": outcome,
                }
            })
            return outcome

        def make_candidate(user_text, current, cells, target_range):
            source = current.output_attachment_id.raw
            effect = result_effect(current, source, "Contacts", target_range, [assertion(cell, value) for cell, value in cells])
            intent = interpretation(user_text, f"Contacts!{target_range[0]}:{target_range[1]}")
            plan = invoke_office({
                "action": "plan",
                "interpretation": intent,
                "expected_effect": effect,
                "model_risk_claims": [],
                "confirmation_required": False,
                "confirmation_reason": "",
            })
            self.assertEqual(plan["status"], "completed", plan)
            self.assertEqual(plan["operation_status"], "plan_ready")
            edited = invoke_office({
                "action": "edit",
                "interpretation": intent,
                "expected_effect": plan["expected_effect"],
                "model_risk_claims": [],
                "confirmation_required": False,
                "confirmation_reason": "",
            }, adapter=object(), effect=plan["expected_effect"])
            self.assertEqual(edited["operation_status"], "candidate_review_required", edited)
            self.assertEqual(edited["current_version_id"], current.id)
            return edited, source

        def accept_candidate():
            thread.message_post(body="接受", llm_role="user", author_id=env.user.partner_id.id)
            return invoke_office({"action": "accept"})

        # Stage 1: retrieve, plan, edit and accept through the registered office tool.
        thread.message_post(
            body="请从 Odoo 联系人中选择这 3 个联系人，将名称、电话和邮件填写到当前 Excel。",
            llm_role="user",
            author_id=env.user.partner_id.id,
        )
        first_read = invoke_office({
            "action": "retrieve",
            "query_spec": {
                "model": "res.partner",
                "domain": [["email", "like", f"cb05-{suffix}-%"]],
                "fields": ["name", "phone", "email"],
                "limit": 3,
                "offset": 0,
                "include_pagination": True,
            },
        })
        self.assertEqual(first_read["status"], "completed", first_read)
        first_records = first_read["data"]["records"]
        first_ids = [record["id"] for record in first_records]
        self.assertEqual(first_ids, partners.ids)
        self.assertEqual(len(set(first_ids)), 3)
        first_cells = []
        for row_number, record in enumerate(first_records, start=2):
            for column, field in zip("ABC", ("name", "phone", "email")):
                first_cells.append((f"{column}{row_number}", record[field]))
        first_edit, v1_bytes = make_candidate(
            "请从 Odoo 联系人中选择这 3 个联系人，将名称、电话和邮件填写到当前 Excel。",
            parent,
            first_cells,
            ("A2", "C4"),
        )
        first_accept = accept_candidate()
        self.assertEqual(first_accept["operation_status"], "accepted_current", first_accept)
        self.assertEqual(first_accept["current_version_id"], first_edit["candidate_version_id"])
        session.invalidate_recordset()
        candidate1 = session.current_version_id
        self.assertEqual(candidate1.parent_version_id, parent)
        self.assertEqual(candidate1.version_no, 2)
        self.assertEqual(session.last_valid_version_id, candidate1)
        self.assertEqual(session.document_revision, 2)
        self.assertEqual(candidate1.output_sha256, hashlib.sha256(candidate1.output_attachment_id.raw).hexdigest())
        self.assertEqual(candidate1.input_sha256, parent.output_sha256)
        workbook1 = load_workbook(BytesIO(candidate1.output_attachment_id.raw), data_only=False)
        self.assertEqual([workbook1["Contacts"].cell(1, col).value for col in range(1, 4)], ["名称", "电话", "邮件"])
        for row_number, record in enumerate(first_records, start=2):
            self.assertEqual(workbook1["Contacts"][f"A{row_number}"].value, record["name"])
            self.assertEqual(workbook1["Contacts"][f"B{row_number}"].value, record["phone"])
            self.assertEqual(workbook1["Contacts"][f"C{row_number}"].value, record["email"])

        # Stage 2: same Thread, separate reads by the exact IDs from Stage 1.
        thread.message_post(
            body="请在第四列增加地址表头，并从 Odoo 查询刚才这 3 个联系人的地址，填写到对应行。",
            llm_role="user",
            author_id=env.user.partner_id.id,
        )
        address_records = []
        for partner_id in first_ids:
            address_read = invoke_office({
                "action": "retrieve",
                "query_spec": {
                    "model": "res.partner",
                    "domain": [["id", "=", partner_id]],
                    "fields": ["street", "street2", "city", "state_id", "zip", "country_id"],
                    "limit": 1,
                    "offset": 0,
                    "include_pagination": True,
                },
            })
            self.assertEqual(address_read["status"], "completed", address_read)
            record = address_read["data"]["records"][0]
            self.assertEqual(record["id"], partner_id)
            address_records.append(record)
        session.invalidate_recordset()
        self.assertEqual(session.current_version_id, candidate1)
        self.assertEqual(session.last_valid_version_id, candidate1)
        self.assertEqual(session.document_revision, 2)
        addresses = [
            ", ".join(filter(None, [
                address_part(record.get("street")), address_part(record.get("street2")),
                address_part(record.get("city")), address_part(record.get("state_id")),
                address_part(record.get("zip")), address_part(record.get("country_id")),
            ]))
            for record in address_records
        ]
        second_cells = [("D1", "地址"), *[(f"D{row_number}", address) for row_number, address in enumerate(addresses, start=2)]]
        second_edit, v2_bytes = make_candidate(
            "请在第四列增加地址表头，并补充这三位联系人的 Odoo 地址。",
            candidate1,
            second_cells,
            ("D1", "D4"),
        )
        self.assertEqual(second_edit["binding"]["parent_version_id"], candidate1.id)
        second_accept = accept_candidate()
        self.assertEqual(second_accept["operation_status"], "accepted_current", second_accept)
        session.invalidate_recordset()
        candidate2 = session.current_version_id
        self.assertEqual(candidate2.parent_version_id, candidate1)
        self.assertEqual(candidate2.version_no, 3)
        self.assertEqual(candidate2.input_sha256, candidate1.output_sha256)
        self.assertEqual(candidate2.output_sha256, hashlib.sha256(candidate2.output_attachment_id.raw).hexdigest())
        self.assertEqual(session.last_valid_version_id, candidate2)
        self.assertEqual(session.document_revision, 3)

        workbook2 = load_workbook(BytesIO(candidate2.output_attachment_id.raw), data_only=False)
        self.assertEqual(workbook2["Contacts"]["D1"].value, "地址")
        for row_number, record in enumerate(first_records, start=2):
            for column, field in zip("ABC", ("name", "phone", "email")):
                self.assertEqual(workbook2["Contacts"][f"{column}{row_number}"].value, workbook1["Contacts"][f"{column}{row_number}"].value)
            self.assertEqual(workbook2["Contacts"][f"D{row_number}"].value, addresses[row_number - 2])
        self.assertEqual(partners.read(["name", "phone", "email", "street", "street2", "city", "zip"]), partner_before)
        self.assertEqual(hashlib.sha256(v1_bytes).hexdigest(), parent.output_sha256)
        self.assertEqual(hashlib.sha256(v2_bytes).hexdigest(), candidate1.output_sha256)
        artifact_dir = os.environ.get("CB05_HVR_ARTIFACT_DIR")
        saved_artifacts = []
        if artifact_dir:
            output_dir = Path(artifact_dir)
            output_dir.mkdir(parents=True, exist_ok=False)
            for filename, content in (
                ("hvr_v1_input.xlsx", source_bytes),
                ("hvr_v2_candidate.xlsx", candidate1.output_attachment_id.raw),
                ("hvr_v3_candidate.xlsx", candidate2.output_attachment_id.raw),
            ):
                (output_dir / filename).write_bytes(content)
                saved_artifacts.append(filename)
        _logger.info(
            "CC05_HVR_AUTOMATED_USER_SIMULATION thread=%s session=%s initial_v1=%s contact_ids=%s first_rows=%s "
            "stage1_candidate=%s stage1_accept=%s stage1_current=%s stage1_last_valid=%s "
            "stage1_revision=%s stage1_input_sha256=%s stage1_output_sha256=%s "
            "stage2_candidate=%s stage2_accept=%s stage2_parent=%s stage2_current=%s "
            "stage2_last_valid=%s stage2_revision=%s stage2_input_sha256=%s stage2_output_sha256=%s "
            "addresses=%s a_to_c_preserved=true contacts_unchanged=true artifact_dir=%s saved_artifacts=%s",
            thread.id,
            session.id,
            parent.id,
            first_ids,
            [(row["id"], row["name"], row["phone"], row["email"]) for row in first_records],
            candidate1.id,
            first_accept.get("operation_status"),
            candidate1.id,
            candidate1.id,
            2,
            candidate1.input_sha256,
            candidate1.output_sha256,
            candidate2.id,
            second_accept.get("operation_status"),
            candidate2.parent_version_id.id,
            session.current_version_id.id,
            session.last_valid_version_id.id,
            session.document_revision,
            candidate2.input_sha256,
            candidate2.output_sha256,
            addresses,
            artifact_dir,
            saved_artifacts,
        )
