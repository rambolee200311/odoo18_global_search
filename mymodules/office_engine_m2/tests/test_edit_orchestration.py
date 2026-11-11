"""Synthetic XLSX TransactionCase coverage for Candidate B orchestration."""

import hashlib
import json
import re
from zipfile import ZIP_DEFLATED, ZipFile
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from openpyxl import Workbook, load_workbook
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase

from .support import WorkbookVersionFixtures


MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_EVIDENCE_DIR = Path(__file__).resolve().parents[3] / "docs/implementation/evidence/CB-M2-CB-04"


def _persist_synthetic_xlsx(name, data):
    """Persist a synthetic test artifact and independently reopen its bytes."""
    if not name.endswith(".xlsx") or "/" in name or "\\" in name:
        raise AssertionError("Evidence artifact names must be plain XLSX filenames.")
    _EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    path = _EVIDENCE_DIR / name
    path.write_bytes(data)
    with ZipFile(path, "r") as package:
        if package.testzip() is not None:
            raise AssertionError(f"Generated test artifact is a corrupt XLSX ZIP: {name}")
    workbook = load_workbook(path, data_only=False)
    return {
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "sheetnames": list(workbook.sheetnames),
        "size": path.stat().st_size,
    }


def _persist_chain_metadata(name, payload):
    if not name.endswith(".json") or "/" in name or "\\" in name:
        raise AssertionError("Evidence metadata names must be plain JSON filenames.")
    _EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    path = _EVIDENCE_DIR / name
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return str(path)


def _stable_core_metadata(data):
    """Normalize serializer timestamps so tests assert document effects only."""
    source = BytesIO(data)
    output = BytesIO()
    with ZipFile(source, "r") as package, ZipFile(output, "w", ZIP_DEFLATED) as normalized:
        for entry in package.infolist():
            content = package.read(entry.filename)
            if entry.filename == "docProps/core.xml":
                content, created_count = re.subn(
                    rb"(<dcterms:created\b[^>]*>).*?(</dcterms:created>)",
                    rb"\g<1>2000-01-01T00:00:00Z\g<2>",
                    content,
                )
                content, modified_count = re.subn(
                    rb"(<dcterms:modified\b[^>]*>).*?(</dcterms:modified>)",
                    rb"\g<1>2000-01-01T00:00:00Z\g<2>",
                    content,
                )
                if created_count != 1 or modified_count != 1:
                    raise AssertionError("Synthetic XLSX core properties changed shape.")
            normalized.writestr(entry, content)
    return output.getvalue()


def _xlsx(a1=10, a2="KEEP", *, sheet_name="Data"):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = sheet_name
    sheet["A1"] = a1
    # Keep a styled blank target in the baseline when a1=None so openpyxl's
    # first value write does not introduce a serializer-only default style
    # delta outside the declared cell_value effect.
    sheet["A1"].number_format = "0.00"
    # A2 is also used by the broad-scope synthetic case; predeclare its style
    # so the test isolates the value effect rather than serialization details.
    sheet["A2"].number_format = "0.00"
    sheet["B1"] = a2
    sheet["C1"] = "=A1*2"
    stream = BytesIO()
    workbook.save(stream)
    return _stable_core_metadata(stream.getvalue())


def _effect(parent, source_bytes, *, first=15, second=None, broad=False, address="A1", value_type="number", sheet="Data"):
    scopes = [{"kind": "cell", "sheet": sheet, "address": address}]
    assertions = [{"kind": "cell_value", "sheet": sheet, "address": address, "value_type": value_type, "value": first}]
    if broad:
        scopes = [{"kind": "range", "sheet": sheet, "start": "A1", "end": "A2"}]
        assertions.append({"kind": "cell_value", "sheet": sheet, "address": "A2", "value_type": "number", "value": second})
    effect = {
        "schema_version": "1",
        "parent_version_id": parent.id,
        "input_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "target_scopes": scopes,
        "allowed_change_kinds": ["cell_value"],
        "expected_assertions": assertions,
        "unknowns": [],
    }
    encoded = json.dumps(effect, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    effect["effect_digest"] = hashlib.sha256(encoded).hexdigest()
    return effect


class _FakeAdapter:
    def __init__(self, candidate_bytes, status="candidate_received"):
        self.candidate_bytes = candidate_bytes
        self.status = status
        self.calls = []

    def execute(self, **kwargs):
        self.calls.append(kwargs)
        if self.status == "candidate_received":
            data = self.candidate_bytes
        else:
            data = None
        return SimpleNamespace(
            operation_status=self.status,
            candidate_bytes=data,
            input_sha256=kwargs.get("input_sha256"),
            candidate_sha256=hashlib.sha256(data).hexdigest() if data else None,
            provider_response_id="mock-response",
            request_id="mock-request",
            tool_call_ids=("mock-tool-call",),
            provider_file_ids=("mock-file",),
            provider_filename="candidate.xlsx",
            usage={"input_tokens": 1, "output_tokens": 1},
            duration_ms=1,
            cleanup_state="not_required",
            error=None,
            to_dict=lambda: {
                "operation_status": self.status,
                "provider_response_id": "mock-response",
                "candidate_present": bool(data),
            },
        )


class TestEditOrchestration(WorkbookVersionFixtures, TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._fake_limits = SimpleNamespace()

    def _versioned(self, bytes_v1=None):
        from odoo.addons.office_engine_m2.services.workbook_version_service import register_initial_v1

        env, session, thread, _upload_message, _source_attachment = self._session_fixture()
        bytes_v1 = bytes_v1 or _xlsx(None)
        request, _output = self._m1_request_fixture(env, session, output_bytes=bytes_v1)
        version = register_initial_v1(env, session.id, request.id)
        session.invalidate_recordset()
        return env, session, thread, version, bytes_v1

    def test_office_finalize_action_delivers_accepted_current(self):
        env, session, thread, current, _input_bytes = self._versioned()
        revision = session.document_revision
        user_message = self._user(thread, "Please generate and deliver the accepted workbook.")
        tool_message = self._tool(thread)

        result = env["office.mapping.tool"].with_context(message=tool_message).office(action="finalize")

        session.invalidate_recordset()
        current.invalidate_recordset()
        self.assertEqual(result["status"], "completed", result)
        self.assertEqual(result["operation_status"], "finalized")
        self.assertEqual(result["delivery_state"], "delivered")
        self.assertTrue(result["attachment_posted_to_thread"])
        self.assertEqual(result["validation_result"], "VERIFIED")
        self.assertEqual(result["current_version_id"], current.id)
        self.assertEqual(result["last_valid_version_id"], current.id)
        self.assertEqual(result["document_revision"], revision)
        self.assertEqual(current.final_message_id.attachment_ids.ids, [current.output_attachment_id.id])
        self.assertEqual(current.final_message_id.llm_role, "assistant")
        self.assertEqual(current.final_message_id.res_id, thread.id)
        self.assertEqual(current.final_attachment_id, current.output_attachment_id)
        self.assertEqual(hashlib.sha256(current.final_attachment_id.raw).hexdigest(), current.output_sha256)
        self.assertGreater(user_message.id, current.source_message_id.id)
        schema = env["llm.tool"].search([("name", "=", "office")], limit=1).get_input_schema()
        self.assertIn("finalize", schema["properties"]["action"]["enum"])

    def test_versioned_current_routes_chat_through_office_and_existing_retriever(self):
        _env, _session, thread, _parent, _input_bytes = self._versioned()
        thread._office_bind_tools()

        self.assertTrue(thread._office_has_versioned_current())
        kwargs = thread._prepare_chat_kwargs(thread.get_llm_messages(), use_streaming=False)
        self.assertEqual(set(kwargs["tools"].mapped("name")), {"office", "odoo_record_retriever"})

        office_rules = next(
            item["content"]
            for item in kwargs["prepend_messages"]
            if item.get("role") == "system" and "Use the Route B Office workflow" in item.get("content", "")
        )
        self.assertIn("Do not use M1 Mapping or row-expansion tools for Route B content production", office_rules)
        self.assertIn("separate `odoo_record_retriever` Tool", office_rules)
        self.assertNotIn("office(action='retrieve')", office_rules)
        self.assertIn("office(action='finalize')", office_rules)
        self.assertIn("without asking for another Accept", office_rules)
        self.assertIn("The Candidate is not Current until the user reviews and accepts it", office_rules)

    def test_raw_upload_candidate_is_accepted_as_first_route_b_version(self):
        from odoo.addons.office_engine_m2.services.intent_contract import digest_json
        from .support import attachment_values

        env = self.env(user=self.owner.id, context={"allowed_company_ids": [self.owner.company_id.id]})
        thread = env["llm.thread"].create({
            "name": "Initial Route B upload " + uuid4().hex,
            "provider_id": self.provider.id,
            "model_id": self.model.id,
        })
        source_bytes = _xlsx(None)
        attachment = env["ir.attachment"].create(attachment_values(
            "route-b-initial-" + uuid4().hex + ".xlsx", source_bytes,
            company_id=env.company.id,
        ))
        upload = thread.message_post(
            body="Raw Route B workbook upload.", llm_role="user",
            author_id=env.user.partner_id.id, attachment_ids=[attachment.id],
        )
        resolved_upload, resolved_attachment = thread._office_latest_upload()
        self.assertEqual(resolved_upload, upload)
        self.assertEqual(resolved_attachment, attachment)
        intent = self._user(thread, "Set the uploaded workbook's A1 value to 15.")
        self.assertTrue(thread._office_is_candidate_b_route())
        thread._office_bind_tools()
        tool = thread.tool_ids.filtered(lambda item: item.name == "office")[:1]
        effect = {
            "schema_version": "1",
            "parent_version_id": 0,
            "input_sha256": hashlib.sha256(source_bytes).hexdigest(),
            "target_scopes": [{"kind": "cell", "sheet": "Data", "address": "A1"}],
            "allowed_change_kinds": ["cell_value"],
            "expected_assertions": [{
                "kind": "cell_value", "sheet": "Data", "address": "A1",
                "value_type": "number", "value": 15,
            }],
            "unknowns": [],
        }
        effect["effect_digest"] = digest_json(effect)
        interpretation = {
            "summary": "Set the explicitly requested value.",
            "target_scope": {"description": "Data!A1", "basis": "explicit"},
            "assumptions": [], "unknowns": [],
        }
        adapter = _FakeAdapter(_xlsx(15))
        call = self._tool(thread)
        dependencies = (adapter, object(), "synthetic-route-b", self._fake_limits)
        with patch(
            "odoo.addons.office_engine_m2.tests.support.browser_simulation.dependencies_for",
            return_value=dependencies,
        ):
            candidate_result = tool.with_context(message=call).execute({
                "action": "edit",
                "interpretation": interpretation,
                "expected_effect": effect,
                "model_risk_claims": [],
            })
        call.write({"body_json": {
            "type": "tool_execution", "tool_name": "office", "status": "completed",
            "result": candidate_result,
        }})
        self.assertEqual(candidate_result["operation_status"], "candidate_review_required", candidate_result)
        session = env["office.mapping.session"].search([
            ("thread_id", "=", thread.id),
            ("source_message_id", "=", upload.id),
            ("source_attachment_id", "=", attachment.id),
        ], limit=1)
        candidate = env["office.workbook.version"].browse(candidate_result["candidate_version_id"])
        self.assertTrue(session)
        self.assertEqual(session.target_model, "ir.attachment")
        self.assertFalse(session.current_version_id)
        self.assertEqual(candidate.version_kind, "initial")
        self.assertEqual(candidate.version_no, 1)
        self.assertFalse(candidate.parent_version_id)
        self.assertEqual(candidate.intent_message_id, intent)
        self.assertEqual(candidate.input_sha256, hashlib.sha256(source_bytes).hexdigest())
        self.assertEqual(session.document_revision, 0)

        self._user(thread, "接受")
        decision = self._tool(thread)
        accepted = tool.with_context(message=decision).execute({
            "action": "accept", "candidate_version_id": candidate.id,
        })
        session.invalidate_recordset()
        candidate.invalidate_recordset()
        self.assertEqual(accepted["operation_status"], "accepted_current", accepted)
        self.assertEqual(accepted["validation_result"], candidate.validation_result)
        self.assertEqual(session.current_version_id, candidate)
        self.assertEqual(session.last_valid_version_id, candidate)
        self.assertEqual(session.document_revision, 1)
        self.assertEqual(candidate.version_no, 1)
        workbook = load_workbook(BytesIO(candidate.output_attachment_id.raw), data_only=False)
        self.assertEqual(workbook["Data"]["A1"].value, 15)

    def test_browser_simulation_candidate_preserves_package_core_properties(self):
        from .support.browser_simulation import ExpectedEffectWorkbookAdapter

        input_bytes = _xlsx("Header")
        input_sha = hashlib.sha256(input_bytes).hexdigest()
        effect = {
            "input_sha256": input_sha,
            "expected_assertions": [
                {"kind": "cell_value", "sheet": "Data", "address": "A1", "value_type": "string", "value": "Product"}
            ],
        }
        _env, _session, thread, _parent, _bytes = self._versioned(input_bytes)
        result = ExpectedEffectWorkbookAdapter(
            self.env, thread, SimpleNamespace(id=1), effect
        ).execute(
            input_xlsx=input_bytes,
            instruction="Set the explicitly declared cell value.",
            input_sha256=input_sha,
        )

        self.assertEqual(result.operation_status, "candidate_received")
        with ZipFile(BytesIO(input_bytes), "r") as source, ZipFile(
            BytesIO(result.candidate_bytes), "r"
        ) as candidate:
            self.assertEqual(
                source.read("docProps/core.xml"),
                candidate.read("docProps/core.xml"),
            )

    def _user(self, thread, body):
        return thread.message_post(body=body, llm_role="user", author_id=thread.env.user.partner_id.id)

    def _tool(self, thread, result=None):
        data = {"type": "tool_execution", "tool_name": "office", "status": "completed"}
        if result is not None:
            data["result"] = result
        return thread.message_post(body="office", body_json=data, llm_role="tool", author_id=False)

    def _intent(self, env, session, thread, parent, input_bytes, body, *, broad=False, address="A1", first=15, second=20, value_type="number", sheet="Data", target_basis="explicit", confirmation_required=False, confirmation_reason="", unknowns=None, assertions=True, model_risk_claims=None):
        from odoo.addons.office_engine_m2.services.edit_orchestrator import plan_edit

        user_message = self._user(thread, body)
        upload, _attachment = thread._office_latest_upload()
        self.assertEqual(user_message.llm_role, "user")
        self.assertEqual(user_message.author_id, env.user.partner_id)
        self.assertEqual(user_message.model, thread._name)
        self.assertEqual(user_message.res_id, thread.id)
        self.assertGreater(
            user_message.id,
            upload.id,
            f"intent={user_message.id}, upload={upload.id}, role={user_message.llm_role}, "
            f"author={user_message.author_id.id}, user_partner={env.user.partner_id.id}",
        )
        effect = _effect(parent, input_bytes, first=first, second=second, broad=broad, address=address, value_type=value_type, sheet=sheet)
        interpretation = {
            "summary": "Apply the explicitly requested workbook value change.",
            "target_scope": {
                "description": address if not broad else "A1:A2",
                "basis": target_basis,
            },
            "assumptions": [],
            "unknowns": list(unknowns or []),
        }
        if not assertions:
            effect["expected_assertions"] = []
            effect["unknowns"] = list(unknowns or ["The business effect is not independently verifiable."])
            effect["effect_digest"] = hashlib.sha256(json.dumps(
                {key: value for key, value in effect.items() if key != "effect_digest"},
                sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False,
            ).encode()).hexdigest()
        plan_call = self._tool(thread)
        result = plan_edit(
            env, thread, plan_call, interpretation, effect, model_risk_claims or [],
            # Model claims are displayed but do not trigger local risk policy.
            confirmation_required=confirmation_required,
            confirmation_reason=confirmation_reason,
        )
        plan_call.write({"body_json": {"type": "tool_execution", "tool_name": "office", "status": "completed", "result": result}})
        return user_message, plan_call, interpretation, effect, result

    def _execute(self, env, thread, interpretation, effect, *, plan_required=True, adapter=None, confirmation_required=False, confirmation_reason="", model_risk_claims=None):
        from odoo.addons.office_engine_m2.services.edit_orchestrator import execute_planned_edit

        call = self._tool(thread)
        result = execute_planned_edit(
            env, thread, call, interpretation, effect, model_risk_claims or [],
            adapter=adapter or _FakeAdapter(_xlsx(15)),
            provider_client=object(), model="mock-model", limits=self._fake_limits,
            confirmation_required=confirmation_required,
            confirmation_reason=confirmation_reason,
        )
        call.write({"body_json": {"type": "tool_execution", "tool_name": "office", "status": "completed", "result": result}})
        return result

    def _review_latest(self, env, session, thread, decision):
        from odoo.addons.office_engine_m2.services.edit_orchestrator import review_candidate

        self._user(thread, decision)
        result = review_candidate(env, thread, self._tool(thread), decision)
        session.invalidate_recordset()
        return result

    def test_explicit_edit_uses_current_version_and_accepts_only_after_cb03_receipt(self):
        env, session, thread, parent, input_bytes = self._versioned()
        _user_message, _plan_message, interpretation, effect, plan = self._intent(
            env, session, thread, parent, input_bytes, "Set Data!A1 to 15."
        )
        self.assertEqual(plan["status"], "completed")
        adapter = _FakeAdapter(_xlsx(15))
        result = self._execute(env, thread, interpretation, effect, adapter=adapter)
        session.invalidate_recordset()
        self.assertEqual(adapter.calls[0]["input_xlsx"], input_bytes)
        self.assertEqual(result["status"], "confirmation_required", result)
        self.assertEqual(result["operation_status"], "candidate_review_required")
        self.assertEqual(result["validation_result"], "VERIFIED")
        self.assertEqual(session.current_version_id, parent)
        accepted = self._review_latest(env, session, thread, "接受")
        self.assertEqual(accepted["operation_status"], "accepted_current")
        self.assertEqual(session.current_version_id.id, result["candidate_version_id"])
        self.assertEqual(session.last_valid_version_id, session.current_version_id)
        self.assertEqual(session.document_revision, 2)
        accepted_bytes = session.current_version_id.output_attachment_id.raw
        workbook = load_workbook(BytesIO(accepted_bytes), data_only=False)
        self.assertEqual(workbook["Data"]["A1"].value, 15)
        self.assertEqual(workbook["Data"]["C1"].value, "=A1*2")
        self.assertEqual(result["delivery_state"], "not_finalized")
        parent_artifact = _persist_synthetic_xlsx("v3-t01-parent.xlsx", input_bytes)
        candidate_artifact = _persist_synthetic_xlsx("v3-t01-candidate.xlsx", accepted_bytes)
        _persist_chain_metadata("v3-t01-version-evidence.json", {
            "evidence_class": "Odoo TransactionCase with Mock Provider and synthetic XLSX",
            "provider_called": False,
            "parent_version_id": parent.id,
            "parent_version_no": parent.version_no,
            "parent_sha256": parent.output_sha256,
            "parent_artifact": parent_artifact,
            "candidate_version_id": session.current_version_id.id,
            "candidate_version_no": session.current_version_id.version_no,
            "candidate_parent_version_id": session.current_version_id.parent_version_id.id,
            "candidate_sha256": session.current_version_id.output_sha256,
            "candidate_artifact": candidate_artifact,
            "independent_readback": {"Data!A1": 15, "Data!C1": "=A1*2"},
        })

    def test_explicit_header_replacement_has_no_extra_risk_confirmation(self):
        env, session, thread, parent, input_bytes = self._versioned(_xlsx("Customer"))
        _user_message, _plan_message, interpretation, effect, plan = self._intent(
            env, session, thread, parent, input_bytes,
            "把 Data!A1 的表头修改为产品编码。",
            first="产品编码", value_type="string",
        )
        self.assertEqual(plan["status"], "completed")
        result = self._execute(
            env, thread, interpretation, effect,
            adapter=_FakeAdapter(_xlsx("产品编码")),
        )
        session.invalidate_recordset()
        self.assertEqual(result["status"], "confirmation_required", result)
        self.assertEqual(result["operation_status"], "candidate_review_required")
        self.assertEqual(result["risk_facts"], [])
        self.assertTrue(any(item["target"] == "xlsx:Data!A1" for item in result["actual_effects"]))
        self.assertEqual(session.current_version_id, parent)
        candidate = env["office.workbook.version"].browse(result["candidate_version_id"])
        self.assertFalse(candidate.requires_confirmation)
        self.assertFalse(candidate.confirmation_receipt_id)
        self._review_latest(env, session, thread, "接受")
        self.assertEqual(session.current_version_id.id, result["candidate_version_id"])
        workbook = load_workbook(BytesIO(session.current_version_id.output_attachment_id.raw), data_only=False)
        self.assertEqual(workbook["Data"]["A1"].value, "产品编码")
        self.assertEqual(workbook["Data"]["B1"].value, "KEEP")
        self.assertEqual(workbook["Data"]["C1"].value, "=A1*2")

    def test_llm_decides_confirmation_for_broad_scope_without_local_risk_rule(self):
        env, session, thread, parent, input_bytes = self._versioned()
        _user_message, _plan_message, interpretation, effect, plan = self._intent(
            env, session, thread, parent, input_bytes,
            "Apply these changes across A1:A2.", broad=True,
            confirmation_required=False,
            model_risk_claims=[{"risk": "the model is unsure about formatting quality"}],
        )
        self.assertEqual(plan["status"], "completed")
        candidate_workbook = load_workbook(BytesIO(_xlsx(15)))
        candidate_workbook["Data"]["A2"] = 20
        candidate_stream = BytesIO()
        candidate_workbook.save(candidate_stream)
        adapter = _FakeAdapter(_stable_core_metadata(candidate_stream.getvalue()))
        result = self._execute(
            env, thread, interpretation, effect, adapter=adapter,
            model_risk_claims=[{"risk": "the model is unsure about formatting quality"}],
        )
        self.assertEqual(len(adapter.calls), 1)
        self.assertEqual(result["operation_status"], "candidate_review_required")
        self.assertEqual(result["status"], "confirmation_required")
        self.assertTrue(result["unverified_aspects"])
        self._review_latest(env, session, thread, "接受")

    def test_llm_confirmation_request_gates_even_an_explicit_single_cell_edit(self):
        env, session, thread, parent, input_bytes = self._versioned()
        _user_message, plan_message, interpretation, effect, plan = self._intent(
            env, session, thread, parent, input_bytes, "Set Data!A1 to 15.",
            confirmation_required=True,
            confirmation_reason="The model identifies a material business risk for this change.",
        )
        self.assertEqual(plan["status"], "confirmation_required")
        self.assertIn("material business risk", plan["confirmation_reason"])
        adapter = _FakeAdapter(_xlsx(15))
        waiting = self._execute(
            env, thread, interpretation, effect, adapter=adapter,
            confirmation_required=True,
            confirmation_reason="The model identifies a material business risk for this change.",
        )
        self.assertEqual(waiting["status"], "confirmation_required")
        self.assertEqual(adapter.calls, [])
        self.assertEqual(session.current_version_id, parent)
        decision = self._user(thread, "确认")
        candidate_result = self._execute(
            env, thread, interpretation, effect, adapter=adapter,
            confirmation_required=True,
            confirmation_reason="The model identifies a material business risk for this change.",
        )
        session.invalidate_recordset()
        self.assertEqual(candidate_result["operation_status"], "candidate_review_required")
        self.assertEqual(len(adapter.calls), 1)
        from odoo.addons.office_engine_m2.services.intent_contract import confirmation_receipt_id
        expected_confirmation_receipt = confirmation_receipt_id(
            plan["binding"],
            owner_id=session.owner_id.id,
            session_revision=session.revision,
            proposal_revision=session.proposal_revision,
            document_revision=session.document_revision,
            decision_message_id=decision.id,
            confirmed_by_user_id=env.uid,
        )
        candidate = env["office.workbook.version"].browse(candidate_result["candidate_version_id"])
        self.assertEqual(candidate.confirmation_receipt_id, expected_confirmation_receipt)
        self.assertNotEqual(candidate.confirmation_receipt_id, plan["confirmation_receipt_id"])
        self.assertTrue(candidate.requires_confirmation)
        review = self._review_latest(env, session, thread, "接受")
        self.assertEqual(review["operation_status"], "accepted_current")

    def test_user_declines_model_confirmation_without_candidate_or_current_change(self):
        env, session, thread, parent, input_bytes = self._versioned()
        _user_message, _plan, interpretation, effect, _result = self._intent(
            env, session, thread, parent, input_bytes, "Clear the stated range.",
            confirmation_required=True,
            confirmation_reason="The model identifies possible loss of existing values.",
        )
        adapter = _FakeAdapter(_xlsx(15))
        self._user(thread, "拒绝")
        result = self._execute(
            env, thread, interpretation, effect, adapter=adapter,
            confirmation_required=True,
            confirmation_reason="The model identifies possible loss of existing values.",
        )
        session.invalidate_recordset()
        self.assertEqual(result["operation_status"], "confirmation_declined")
        self.assertEqual(adapter.calls, [])
        self.assertEqual(session.current_version_id, parent)
        self.assertEqual(session.document_revision, 1)

    def test_confirmation_decision_cannot_be_changed_between_plan_and_edit(self):
        env, session, thread, parent, input_bytes = self._versioned()
        _user_message, _plan, interpretation, effect, _result = self._intent(
            env, session, thread, parent, input_bytes, "Apply the proposed operation.",
            confirmation_required=True,
            confirmation_reason="The model identified a material business risk.",
        )
        adapter = _FakeAdapter(_xlsx(15))
        with self.assertRaises(ValidationError):
            self._execute(env, thread, interpretation, effect, adapter=adapter)
        self.assertEqual(adapter.calls, [])
        self.assertEqual(session.current_version_id, parent)

    def test_partial_candidate_can_be_accepted_without_changing_its_validation_grade(self):
        env, session, thread, parent, input_bytes = self._versioned()
        _user_message, _plan_message, interpretation, effect, plan = self._intent(
            env, session, thread, parent, input_bytes, "Reorganize the worksheet as requested.",
            unknowns=["The business correctness of the reorganization is not independently verifiable."],
            assertions=False,
        )
        self.assertEqual(plan["status"], "completed")
        result = self._execute(env, thread, interpretation, effect, adapter=_FakeAdapter(_xlsx(15)))
        session.invalidate_recordset()
        candidate = env["office.workbook.version"].browse(result["candidate_version_id"])
        self.assertEqual(result["validation_result"], "PARTIALLY_VERIFIED")
        self.assertEqual(result["status"], "confirmation_required")
        self.assertEqual(result["operation_status"], "candidate_review_required")
        self.assertTrue(result["verified_facts"])
        self.assertTrue(result["model_claims"])
        self.assertTrue(result["unverified_aspects"])
        self.assertEqual(candidate.state, "partially_verified")
        self.assertEqual(result["candidate_download_url"], f"/web/content/{candidate.output_attachment_id.id}?download=true")
        self.assertEqual(result["candidate_output_sha256"], hashlib.sha256(candidate.output_attachment_id.raw).hexdigest())
        self.assertEqual(session.current_version_id, parent)
        from odoo.addons.office_engine_m2.services.edit_orchestrator import review_candidate

        decision = self._user(thread, "接受")
        # Reviewing an existing Candidate depends on its trusted Version and
        # Session bindings, not reopening the original upload from the filestore.
        with patch.object(type(thread), "_office_latest_upload", side_effect=AssertionError("review reopened upload")):
            accepted = review_candidate(env, thread, self._tool(thread), "接受")
        session.invalidate_recordset()
        candidate.invalidate_recordset()
        self.assertEqual(accepted["status"], "completed", accepted)
        self.assertEqual(accepted["operation_status"], "accepted_current")
        self.assertEqual(accepted["validation_result"], "PARTIALLY_VERIFIED")
        self.assertEqual(accepted["candidate_state"], "accepted_current")
        self.assertEqual(candidate.validation_result, "PARTIALLY_VERIFIED")
        self.assertEqual(candidate.state, "accepted_current")
        self.assertEqual(session.current_version_id, candidate)
        self.assertEqual(session.last_valid_version_id, candidate)
        self.assertEqual(session.document_revision, 2)
        self.assertEqual(candidate.acceptance_authorization_message_id, decision)
        self.assertIn("business-effect", " ".join(accepted["unverified_aspects"]))
        accepted_bytes = candidate.output_attachment_id.raw
        self.assertEqual(hashlib.sha256(accepted_bytes).hexdigest(), candidate.output_sha256)
        workbook = load_workbook(BytesIO(accepted_bytes), data_only=False)
        try:
            self.assertEqual(workbook["Data"]["A1"].value, 15)
            self.assertEqual(workbook["Data"]["C1"].value, "=A1*2")
        finally:
            workbook.close()
        artifact = _persist_synthetic_xlsx("v3-partially-accepted-candidate.xlsx", accepted_bytes)
        _persist_chain_metadata("v3-partially-accepted-candidate.json", {
            "evidence_class": "Odoo TransactionCase with Mock Provider and synthetic XLSX",
            "provider_called": False,
            "validation_result": candidate.validation_result,
            "candidate_version_id": candidate.id,
            "parent_version_id": parent.id,
            "input_sha256": candidate.input_sha256,
            "output_sha256": candidate.output_sha256,
            "accepted_by_message_id": decision.id,
            "current_version_id": session.current_version_id.id,
            "document_revision": session.document_revision,
            "artifact": artifact,
            "independent_readback": {"Data!A1": 15, "Data!C1": "=A1*2"},
        })
        self.assertEqual(_message_author(decision), env.user.partner_id.id)

    def test_partial_candidate_can_be_rejected_without_advancing_current(self):
        env, session, thread, parent, input_bytes = self._versioned()
        _user_message, _plan_message, interpretation, effect, _plan = self._intent(
            env, session, thread, parent, input_bytes, "Reorganize the worksheet as requested.",
            unknowns=["The business correctness of the reorganization is not independently verifiable."],
            assertions=False,
        )
        result = self._execute(env, thread, interpretation, effect, adapter=_FakeAdapter(_xlsx(15)))
        session.invalidate_recordset()
        candidate = env["office.workbook.version"].browse(result["candidate_version_id"])
        self.assertEqual(candidate.validation_result, "PARTIALLY_VERIFIED")
        self.assertEqual(candidate.state, "partially_verified")
        decision = self._user(thread, "拒绝")
        from odoo.addons.office_engine_m2.services.edit_orchestrator import review_candidate
        rejected = review_candidate(env, thread, self._tool(thread), "拒绝")
        session.invalidate_recordset()
        candidate.invalidate_recordset()
        self.assertEqual(rejected["status"], "completed", rejected)
        self.assertEqual(rejected["operation_status"], "candidate_rejected")
        self.assertEqual(candidate.validation_result, "PARTIALLY_VERIFIED")
        self.assertEqual(candidate.state, "rejected")
        self.assertEqual(session.current_version_id, parent)
        self.assertEqual(session.last_valid_version_id, parent)
        self.assertEqual(session.document_revision, 1)
        self.assertEqual(candidate.rejection_message_id, decision)
        self.assertEqual(_message_author(decision), env.user.partner_id.id)

    def test_failed_candidate_is_never_reviewable_even_if_user_accepts(self):
        env, session, thread, parent, input_bytes = self._versioned()
        _user_message, _plan_message, interpretation, effect, _plan = self._intent(
            env, session, thread, parent, input_bytes, "Set Data!A1 to 15."
        )
        output = load_workbook(BytesIO(_xlsx(15)))
        output["Data"]["B1"] = "UNAUTHORIZED CHANGE"
        stream = BytesIO()
        output.save(stream)
        result = self._execute(env, thread, interpretation, effect, adapter=_FakeAdapter(stream.getvalue()))
        self.assertEqual(result["validation_result"], "FAILED")
        self.assertEqual(result["status"], "failed")
        self._user(thread, "接受")
        call = self._tool(thread)
        from odoo.addons.office_engine_m2.services.edit_orchestrator import review_candidate
        review = review_candidate(env, thread, call, "接受")
        session.invalidate_recordset()
        self.assertEqual(review["status"], "blocked")
        self.assertEqual(session.current_version_id, parent)

    def test_model_unknowns_are_review_data_not_local_clarification_rule(self):
        env, session, thread, parent, input_bytes = self._versioned()
        _user_message, _plan_message, interpretation, effect, plan = self._intent(
            env, session, thread, parent, input_bytes, "Make the requested change in A1.",
            unknowns=["Business formatting quality is not independently verifiable."],
        )
        self.assertEqual(plan["status"], "completed")
        self.assertNotEqual(plan["status"], "clarification_required")
        self.assertEqual(session.current_version_id, parent)

    def test_ambiguous_intent_requests_clarification_without_candidate(self):
        env, session, thread, parent, input_bytes = self._versioned()
        _user_message, _plan_message, interpretation, effect, plan = self._intent(
            env, session, thread, parent, input_bytes,
            "Adjust the table in the way that makes sense.",
            target_basis="ambiguous",
            unknowns=["Which table and desired adjustment are not specified."],
        )
        self.assertEqual(plan["status"], "clarification_required")
        self.assertEqual(plan["operation_status"], "intent_not_ready")
        self.assertFalse(plan.get("candidate_version_id"))
        self.assertEqual(session.current_version_id, parent)
        self.assertFalse(env["office.workbook.version"].search([
            ("session_id", "=", session.id), ("version_kind", "=", "edit"),
        ]))

    def test_corrupt_candidate_is_hard_blocked_and_never_current(self):
        env, session, thread, parent, input_bytes = self._versioned()
        _user_message, _plan_message, interpretation, effect, _plan = self._intent(
            env, session, thread, parent, input_bytes, "Set Data!A1 to 15."
        )
        result = self._execute(
            env, thread, interpretation, effect,
            adapter=_FakeAdapter(b"not a valid xlsx zip package"),
        )
        session.invalidate_recordset()
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["validation_result"], "FAILED")
        self.assertEqual(result["operation_status"], "candidate_technical_validation_failed")
        self.assertEqual(session.current_version_id, parent)
        self.assertEqual(session.last_valid_version_id, parent)
        self.assertEqual(session.document_revision, 1)

    def test_arbitrary_worksheet_and_coordinate_are_not_special_cased(self):
        source_workbook = Workbook()
        source_workbook.active.title = "Quarterly Output"
        # Predeclare a blank styled target so the case tests a generic location,
        # not a worksheet-dimension/structure expansion outside the effect.
        source_workbook["Quarterly Output"]["Z42"].number_format = "0.00"
        source_stream = BytesIO()
        source_workbook.save(source_stream)
        input_bytes = _stable_core_metadata(source_stream.getvalue())
        env, session, thread, parent, input_bytes = self._versioned(input_bytes)
        _user_message, _plan_message, interpretation, effect, plan = self._intent(
            env, session, thread, parent, input_bytes,
            "Set the explicitly identified target to 27.",
            address="Z42", first=27, sheet="Quarterly Output",
        )
        self.assertEqual(plan["status"], "completed")
        candidate_wb = load_workbook(BytesIO(input_bytes), data_only=False)
        candidate_wb["Quarterly Output"]["Z42"] = 27
        candidate_stream = BytesIO()
        candidate_wb.save(candidate_stream)
        result = self._execute(
            env, thread, interpretation, effect,
            adapter=_FakeAdapter(_stable_core_metadata(candidate_stream.getvalue())),
        )
        self.assertEqual(result["validation_result"], "VERIFIED")
        self.assertEqual([item["change_kind"] for item in result["actual_effects"]], ["cell_value"])
        self._review_latest(env, session, thread, "接受")
        accepted_bytes = session.current_version_id.output_attachment_id.raw
        accepted = load_workbook(BytesIO(accepted_bytes), data_only=False)
        self.assertEqual(accepted["Quarterly Output"]["Z42"].value, 27)
        self.assertEqual(session.current_version_id.parent_version_id.id, parent.id)

    def test_confirmed_plan_is_stale_after_current_version_advances(self):
        from odoo.addons.office_engine_m2.services.candidate_validator import validate_workbook_candidate
        from odoo.addons.office_engine_m2.services.edit_orchestrator import review_candidate
        from odoo.addons.office_engine_m2.services.workbook_version_service import register_candidate

        env, session, thread, parent, input_bytes = self._versioned()
        _old_intent, _plan_message, interpretation, effect, _plan = self._intent(
            env, session, thread, parent, input_bytes,
            "Apply the proposed change to Data!A1.",
            confirmation_required=True,
            confirmation_reason="The model identified a material risk.",
        )

        # A separate, valid Candidate advances Current after the first plan.
        new_intent = self._user(thread, "Set Data!A1 to 15 as a separate request.")
        new_effect = _effect(parent, input_bytes, first=15)
        advanced_candidate = register_candidate(
            env, session.id, parent_version_id=parent.id,
            expected_document_revision=session.document_revision,
            candidate_bytes=_xlsx(15), filename="candidate.xlsx", mimetype=MIME,
            idempotency_key="stale-plan-" + uuid4().hex,
            request_digest=hashlib.sha256(uuid4().hex.encode()).hexdigest(),
            intent_message_id=new_intent.id, intent_effect_digest=new_effect["effect_digest"],
        )
        validation = validate_workbook_candidate(env, session.id, advanced_candidate.id, new_effect)
        self.assertEqual(validation["validation_result"], "VERIFIED")
        edit_result = {
            "action": "edit", "candidate_version_id": advanced_candidate.id,
            "binding": {"intent_message_id": new_intent.id},
        }
        self._tool(thread, edit_result)
        self._user(thread, "接受")
        review = review_candidate(env, thread, self._tool(thread), "接受")
        self.assertEqual(review["operation_status"], "accepted_current")
        advanced_parent = session.current_version_id

        self._user(thread, "确认")
        adapter = _FakeAdapter(_xlsx(30))
        from odoo.addons.office_engine_m2.services.edit_orchestrator import execute_planned_edit
        with self.assertRaises(ValidationError):
            execute_planned_edit(
                env, thread, self._tool(thread), interpretation, effect,
                adapter=adapter, provider_client=object(), model="mock-model",
                limits=self._fake_limits,
                confirmation_required=True,
                confirmation_reason="The model identified a material risk.",
            )
        self.assertEqual(adapter.calls, [])
        session.invalidate_recordset()
        self.assertEqual(session.current_version_id, advanced_parent)

    def test_confirmed_broad_scope_runs_only_after_exact_reply_and_keeps_receipt_bound(self):
        env, session, thread, parent, input_bytes = self._versioned()
        _user_message, plan_message, interpretation, effect, plan = self._intent(
            env, session, thread, parent, input_bytes, "Apply the specified changes in A1:A2.", broad=True,
            confirmation_required=True,
            confirmation_reason="The model identified possible overwriting across this range.",
        )
        self.assertEqual(plan["status"], "confirmation_required")
        self.assertFalse(plan.get("operation_executed"))
        broad_candidate = load_workbook(BytesIO(_xlsx(15)))
        broad_candidate["Data"]["A2"] = 20
        broad_stream = BytesIO()
        broad_candidate.save(broad_stream)
        adapter = _FakeAdapter(_stable_core_metadata(broad_stream.getvalue()))
        no_confirmation = self._execute(
            env, thread, interpretation, effect, adapter=adapter,
            confirmation_required=True,
            confirmation_reason="The model identified possible overwriting across this range.",
        )
        self.assertEqual(no_confirmation["status"], "confirmation_required")
        self.assertEqual(adapter.calls, [])
        self.assertEqual(session.current_version_id, parent)
        self._user(thread, "确认")
        result = self._execute(
            env, thread, interpretation, effect, adapter=adapter,
            confirmation_required=True,
            confirmation_reason="The model identified possible overwriting across this range.",
        )
        session.invalidate_recordset()
        self.assertEqual(result["status"], "confirmation_required", result)
        self.assertEqual(result["operation_status"], "candidate_review_required")
        self.assertEqual(result["validation_result"], "VERIFIED")
        self.assertEqual(session.current_version_id, parent)
        accepted = self._review_latest(env, session, thread, "接受")
        accepted_version = env["office.workbook.version"].browse(result["candidate_version_id"])
        self.assertEqual(accepted["operation_status"], "accepted_current")
        self.assertEqual(accepted_version.acceptance_authorization_kind, "candidate_review")
        self.assertTrue(accepted_version.acceptance_authorization_message_id)
        self.assertEqual(session.current_version_id.id, result["candidate_version_id"])

    def test_provider_failure_does_not_register_candidate_or_advance_current(self):
        env, session, thread, parent, input_bytes = self._versioned()
        _user_message, _plan_message, interpretation, effect, _plan = self._intent(
            env, session, thread, parent, input_bytes, "Set Data!A1 to 15."
        )
        adapter = _FakeAdapter(None, status="indeterminate")
        result = self._execute(env, thread, interpretation, effect, adapter=adapter)
        session.invalidate_recordset()
        self.assertEqual(result["status"], "failed")
        self.assertEqual(session.current_version_id, parent)
        self.assertEqual(session.document_revision, 1)
        candidates = env["office.workbook.version"].search([("session_id", "=", session.id), ("version_kind", "=", "edit")])
        self.assertFalse(candidates)

    def test_facade_fails_closed_while_srs_external_processing_gate_is_open(self):
        env, session, thread, parent, input_bytes = self._versioned()
        self._user(thread, "Set Data!A1 to 15.")
        call = self._tool(thread)
        tool = env["office.mapping.tool"].with_context(message=call)
        result = tool.office("edit")
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["error_code"], "external_file_processing_not_authorized")
        self.assertEqual(session.current_version_id, parent)

    def test_two_successive_edits_use_successive_accepted_workbook_versions(self):
        env, session, thread, parent, input_bytes = self._versioned()
        _first_user, _plan, interpretation, effect, _result = self._intent(
            env, session, thread, parent, input_bytes, "Set Data!A1 to 15.", assertions=False,
        )
        first = self._execute(env, thread, interpretation, effect, adapter=_FakeAdapter(_xlsx(15)))
        session.invalidate_recordset()
        self.assertEqual(first["operation_status"], "candidate_review_required")
        self.assertEqual(first["validation_result"], "PARTIALLY_VERIFIED")
        first_decision = self._review_latest(env, session, thread, "接受")
        self.assertEqual(first_decision["status"], "completed", first_decision)
        self.assertEqual(first_decision["validation_result"], "PARTIALLY_VERIFIED")
        v2 = session.current_version_id
        v2_bytes = v2.output_attachment_id.raw
        _second_user, _plan2, interpretation2, effect2, _result2 = self._intent(
            env, session, thread, v2, v2_bytes, "Set Data!A2 to 20.", address="A2", first=20,
            assertions=False,
        )
        adapter2 = _FakeAdapter(_xlsx(15))
        output = load_workbook(BytesIO(adapter2.candidate_bytes))
        output["Data"]["A2"] = 20
        stream = BytesIO()
        output.save(stream)
        adapter2 = _FakeAdapter(_stable_core_metadata(stream.getvalue()))
        second = self._execute(env, thread, interpretation2, effect2, adapter=adapter2)
        session.invalidate_recordset()
        self.assertEqual(second["operation_status"], "candidate_review_required", second)
        self.assertEqual(second["validation_result"], "PARTIALLY_VERIFIED")
        second_decision = self._review_latest(env, session, thread, "接受")
        self.assertEqual(second_decision["status"], "completed", second_decision)
        self.assertEqual(second_decision["validation_result"], "PARTIALLY_VERIFIED")
        self.assertEqual(adapter2.calls[0]["input_xlsx"], v2_bytes)
        self.assertEqual(session.current_version_id.version_no, 3)
        workbook = load_workbook(BytesIO(session.current_version_id.output_attachment_id.raw), data_only=False)
        self.assertEqual(workbook["Data"]["A1"].value, 15)
        self.assertEqual(workbook["Data"]["A2"].value, 20)
        v1_artifact = _persist_synthetic_xlsx("v3-partially-verified-v1.xlsx", input_bytes)
        v2_artifact = _persist_synthetic_xlsx("v3-partially-verified-v2.xlsx", v2_bytes)
        v3_bytes = session.current_version_id.output_attachment_id.raw
        v3_artifact = _persist_synthetic_xlsx("v3-partially-verified-v3.xlsx", v3_bytes)
        _persist_chain_metadata("v3-partially-verified-version-chain.json", {
            "evidence_class": "Odoo TransactionCase with Mock Provider and synthetic XLSX",
            "provider_called": False,
            "versions": [
                {"version_no": 1, "version_id": parent.id, "sha256": hashlib.sha256(input_bytes).hexdigest(), "artifact": v1_artifact},
                {"version_no": 2, "version_id": v2.id, "parent_version_id": parent.id, "input_sha256": v2.input_sha256, "sha256": v2.output_sha256, "artifact": v2_artifact},
                {"version_no": 3, "version_id": session.current_version_id.id, "parent_version_id": v2.id, "input_sha256": session.current_version_id.input_sha256, "sha256": session.current_version_id.output_sha256, "artifact": v3_artifact},
            ],
            "independent_readback": {"V2.Data!A1": 15, "V3.Data!A1": 15, "V3.Data!A2": 20},
        })

    def test_out_of_scope_candidate_is_not_accepted(self):
        env, session, thread, parent, input_bytes = self._versioned()
        _user_message, _plan_message, interpretation, effect, _plan = self._intent(
            env, session, thread, parent, input_bytes, "Set Data!A1 to 15."
        )
        output = load_workbook(BytesIO(_xlsx(15)))
        output["Data"]["B1"] = "UNAUTHORIZED"
        stream = BytesIO()
        output.save(stream)
        result = self._execute(env, thread, interpretation, effect, adapter=_FakeAdapter(stream.getvalue()))
        session.invalidate_recordset()
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["validation_result"], "FAILED")
        self.assertEqual(session.current_version_id, parent)
        self.assertEqual(session.document_revision, 1)

    def test_verified_candidate_review_accept_and_reject_are_user_bound(self):
        from odoo.addons.office_engine_m2.services.candidate_validator import validate_workbook_candidate
        from odoo.addons.office_engine_m2.services.edit_orchestrator import review_candidate
        from odoo.addons.office_engine_m2.services.workbook_version_service import register_candidate

        env, session, thread, parent, input_bytes = self._versioned()
        intent = self._user(thread, "Set Data!A1 to 15.")
        effect = _effect(parent, input_bytes, first=15)
        candidate = register_candidate(
            env, session.id, parent_version_id=parent.id,
            expected_document_revision=session.document_revision,
            candidate_bytes=_xlsx(15), filename="candidate.xlsx", mimetype=MIME,
            idempotency_key="review-" + uuid4().hex,
            request_digest=hashlib.sha256(uuid4().hex.encode()).hexdigest(),
            intent_message_id=intent.id, intent_effect_digest=effect["effect_digest"],
        )
        validation = validate_workbook_candidate(env, session.id, candidate.id, effect)
        self.assertEqual(validation["validation_result"], "VERIFIED", validation)
        result = {
            "action": "edit", "candidate_version_id": candidate.id,
            "binding": {"intent_message_id": intent.id},
        }
        self._tool(thread, result)
        decision = self._user(thread, "拒绝")
        call = self._tool(thread)
        outcome = review_candidate(env, thread, call, "拒绝")
        session.invalidate_recordset()
        candidate.invalidate_recordset()
        self.assertEqual(outcome["operation_status"], "candidate_rejected")
        self.assertEqual(candidate.state, "rejected")
        self.assertEqual(session.current_version_id, parent)
        self.assertEqual(session.last_valid_version_id, parent)
        self.assertEqual(session.document_revision, 1)
        self.assertEqual(_message_author(decision), env.user.partner_id.id)


def _message_author(message):
    return message.author_id.id

