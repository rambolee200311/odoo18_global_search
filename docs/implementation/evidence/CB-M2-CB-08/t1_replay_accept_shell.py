"""Replay the real CC-08 Provider output through formal Candidate/Accept.

No Provider request is made here. ``T1-candidate.xlsx`` is the exact XLSX
downloaded by the one real Responses API execution and its metadata is bound
from ``T1-real-provider-result-attempt-01.json``. The injected adapter only
replays those bytes so the Odoo Candidate/Validator/Accept path can be checked
in one transaction after the original shell run rolled back its test rows.
"""

import hashlib
import json
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from openpyxl import Workbook, load_workbook


ROOT = Path("docs/implementation/evidence/CB-M2-CB-08")
MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
REFERENCE_THREAD_ID = 19293
INSTRUCTION = (
    "In the Ledger worksheet, format the Amount value in cell B2 as USD currency "
    "with two decimal places. Preserve all values, formulas, worksheet names, "
    "and other workbook contents. Return the edited XLSX for review."
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def tool_message(thread, status="executing", result=None):
    payload = {"type": "tool_execution", "tool_name": "office", "status": status}
    if result is not None:
        payload["result"] = result
    return thread.message_post(
        body="Executing office" if status == "executing" else "Office result",
        body_json=payload,
        llm_role="tool",
        author_id=False,
    )


provider_evidence = json.loads(
    (ROOT / "T1-real-provider-result-attempt-01.json").read_text(encoding="utf-8")
)
source_bytes = (ROOT / "T1-input.xlsx").read_bytes()
candidate_bytes = (ROOT / "T1-candidate.xlsx").read_bytes()
if provider_evidence.get("provider_call_count") != 1:
    raise RuntimeError("Expected exactly one real Provider request in source evidence")
if provider_evidence.get("provider", {}).get("operation_status") != "candidate_received":
    raise RuntimeError("Source evidence does not contain a downloaded Provider Candidate")
if sha(source_bytes) != provider_evidence.get("input_sha256"):
    raise RuntimeError("Input XLSX does not match real Provider request evidence")
if sha(candidate_bytes) != provider_evidence.get("candidate_output_sha256"):
    raise RuntimeError("Candidate XLSX does not match real Provider response evidence")

from odoo import tools
from odoo.addons.llm_openai.services import AdapterLimits, AdapterResult
from odoo.addons.office_engine_m2.services.mapping_service import create_session


result_doc = {
    "scenario": "CB08-T1-replay-accept",
    "database": "odoo18ce",
    "layer": "real Provider bytes replayed through Office Tool, Candidate Validator, and formal Accept",
    "provider_requests_in_this_run": 0,
    "provider_response_id_source": provider_evidence["provider"]["provider_response_id"],
    "provider_candidate_sha256": sha(candidate_bytes),
    "input_sha256": sha(source_bytes),
    "synthetic_only": True,
}


class ReplayAdapter:
    def execute(self, *, provider_client, model, input_xlsx, instruction, limits, input_sha256=None, correlation_id=None):
        if input_xlsx != source_bytes or sha(input_xlsx) != input_sha256:
            raise RuntimeError("Replay input differs from the captured real Provider request")
        return AdapterResult(
            operation_status="candidate_received",
            candidate_bytes=candidate_bytes,
            input_sha256=sha(input_xlsx),
            candidate_sha256=sha(candidate_bytes),
            provider_response_id=provider_evidence["provider"]["provider_response_id"],
            request_id=provider_evidence["provider"].get("request_id"),
            download_request_id=provider_evidence["provider"].get("download_request_id"),
            tool_call_ids=tuple(provider_evidence["provider"].get("tool_call_ids") or ()),
            container_id=provider_evidence["provider"].get("container_id"),
            provider_file_ids=tuple(provider_evidence["provider"].get("provider_file_ids") or ()),
            provider_filename=provider_evidence["provider"].get("provider_filename") or "ledger_amount_usd.xlsx",
            usage=provider_evidence["provider"].get("usage") or {},
            duration_ms=provider_evidence["provider"].get("duration_ms") or 0,
            cleanup_state="completed",
        )


try:
    dispatch_enabled = tools.config.get("office_engine_m2_external_provider_dispatch_enabled", False)
    result_doc["trusted_dispatch_enabled"] = dispatch_enabled is True or str(dispatch_enabled).lower() in {"1", "true", "yes"}
    reference_thread = env["llm.thread"].browse(REFERENCE_THREAD_ID).exists()
    model_record = reference_thread.model_id if reference_thread else env["llm.model"]
    if not reference_thread or not model_record or model_record.name != "gpt-5.6-luna":
        raise RuntimeError("Existing configured Provider/Model reference is unavailable")

    company = env.company
    user = env["res.users"].with_context(no_reset_password=True).create({
        "name": "CC08 Synthetic Replay " + uuid4().hex[:8],
        "login": "cc08-replay-" + uuid4().hex,
        "email": "cc08-replay@example.invalid",
        "groups_id": [(6, 0, [env.ref("base.group_user").id])],
        "company_ids": [(6, 0, [company.id])],
        "company_id": company.id,
    })
    user_env = env(user=user.id, context={"allowed_company_ids": [company.id]})
    thread = user_env["llm.thread"].create({
        "name": "CC08 replay captured real Provider Candidate " + uuid4().hex,
        "provider_id": model_record.provider_id.id,
        "model_id": model_record.id,
    })
    attachment = user_env["ir.attachment"].create({
        "name": "CB08-synthetic-ledger.xlsx",
        "type": "binary",
        "raw": source_bytes,
        "mimetype": MIME,
        "company_id": company.id,
        "public": False,
    })
    upload = thread.message_post(
        body="Synthetic XLSX for captured Provider output replay.",
        llm_role="user",
        author_id=user_env.user.partner_id.id,
        attachment_ids=[attachment.id],
    )
    session_context = create_session(
        user_env,
        thread_id=thread.id,
        source_message_id=upload.id,
        source_attachment_id=attachment.id,
        target_model="ir.attachment",
        target_record_id=attachment.id,
    )
    thread.message_post(body=INSTRUCTION, llm_role="user", author_id=user_env.user.partner_id.id)
    thread._office_bind_tools()
    office = thread.tool_ids.filtered(lambda item: item.name == "office")[:1]
    if not office:
        raise RuntimeError("office Tool was not bound to the synthetic Thread")

    from odoo.addons.office_engine_m2.services.edit_orchestrator import MAX_VERSION_BYTES
    limits = AdapterLimits(
        allowed_models=frozenset({model_record.name}),
        max_input_bytes=MAX_VERSION_BYTES,
        max_output_bytes=MAX_VERSION_BYTES,
        max_output_tokens=4096,
        timeout_seconds=120,
        memory_limit="1g",
    )
    edit_message = tool_message(thread)
    # execute_candidate_edit requires a non-null client token even though this
    # replay adapter never reads or uses it.
    replay_dependencies = (ReplayAdapter(), object(), model_record.name, limits)
    with patch(
        "odoo.addons.office_engine_m2.services.edit_orchestrator._provider_dependencies",
        return_value=replay_dependencies,
    ):
        edit_result = office.with_context(message=edit_message).execute({"action": "edit"})
    edit_message.write({
        "body_json": {"type": "tool_execution", "tool_name": "office", "status": "completed", "result": edit_result}
    })
    result_doc["edit_result"] = {
        key: edit_result.get(key)
        for key in ("operation_status", "candidate_version_id", "candidate_state", "validation_result", "candidate_output_sha256")
    }
    if edit_result.get("operation_status") != "candidate_review_required":
        raise RuntimeError("Captured real Provider bytes did not enter formal Candidate review")
    candidate = user_env["office.workbook.version"].browse(edit_result["candidate_version_id"]).exists()
    session = candidate.session_id
    replayed_output = candidate.output_attachment_id.raw or b""
    if replayed_output != candidate_bytes:
        raise RuntimeError("Formal Candidate attachment differs from captured real Provider XLSX")

    source_book = load_workbook(BytesIO(source_bytes), data_only=False)
    candidate_book = load_workbook(BytesIO(replayed_output), data_only=False)
    source_ws, output_ws = source_book["Ledger"], candidate_book["Ledger"]
    non_target_style_ids_preserved = all(
        source_ws.cell(row, col).style_id == output_ws.cell(row, col).style_id
        for row in range(1, max(source_ws.max_row, output_ws.max_row) + 1)
        for col in range(1, max(source_ws.max_column, output_ws.max_column) + 1)
        if (row, col) != (2, 2)
    )
    values_formulas_preserved = all(
        source_ws.cell(row, col).value == output_ws.cell(row, col).value
        for row in range(1, max(source_ws.max_row, output_ws.max_row) + 1)
        for col in range(1, max(source_ws.max_column, output_ws.max_column) + 1)
    )
    target_format = output_ws["B2"].number_format
    target_format_ok = ("$" in target_format or "USD" in target_format.upper()) and "0.00" in target_format
    result_doc["readback"] = {
        "xlsx_opens": True,
        "sheet_names_preserved": source_book.sheetnames == candidate_book.sheetnames,
        "target_number_format": target_format,
        "target_format_is_usd_two_decimals": target_format_ok,
        "values_and_formulas_preserved": values_formulas_preserved,
        "non_target_style_ids_preserved": non_target_style_ids_preserved,
        "formula_c2": output_ws["C2"].value,
        "candidate_attachment_sha256": sha(replayed_output),
    }
    source_book.close()
    candidate_book.close()
    if not (target_format_ok and values_formulas_preserved and non_target_style_ids_preserved):
        raise RuntimeError("Captured real Provider Candidate failed the corrected independent readback")

    accept_message = thread.message_post(body="接受", llm_role="user", author_id=user_env.user.partner_id.id)
    accept_tool_message = tool_message(thread)
    accept_result = office.with_context(message=accept_tool_message).execute({
        "action": "accept", "candidate_version_id": candidate.id,
    })
    accept_tool_message.write({
        "body_json": {"type": "tool_execution", "tool_name": "office", "status": "completed", "result": accept_result}
    })
    session.invalidate_recordset()
    candidate.invalidate_recordset()
    accepted_bytes = session.current_version_id.output_attachment_id.raw or b""
    (ROOT / "T1-accepted-v1.xlsx").write_bytes(accepted_bytes)
    result_doc["accept_result"] = {
        key: accept_result.get(key)
        for key in ("operation_status", "candidate_version_id", "candidate_state", "validation_result", "current_version_id", "last_valid_version_id", "document_revision")
    }
    result_doc["accepted_state"] = {
        "current_version_id": session.current_version_id.id,
        "last_valid_version_id": session.last_valid_version_id.id,
        "document_revision": session.document_revision,
        "candidate_validation_result_unchanged": candidate.validation_result == edit_result.get("validation_result"),
        "accepted_sha256": sha(accepted_bytes),
        "accepted_bytes_match_provider_candidate": accepted_bytes == candidate_bytes,
        "decision_message_id": accept_message.id,
    }
    result_doc["operation"] = (
        "pass"
        if accept_result.get("operation_status") == "accepted_current"
        and session.current_version_id == candidate
        and session.last_valid_version_id == candidate
        and session.document_revision == 1
        and candidate.validation_result == edit_result.get("validation_result")
        and accepted_bytes == candidate_bytes
        else "failed"
    )
except Exception as exc:
    result_doc.update(operation="failed", exception_type=type(exc).__name__, error=str(exc)[:300])
finally:
    result_doc["recorded_at_utc"] = datetime.now(timezone.utc).isoformat()
    (ROOT / "T1-replay-accept-result.json").write_text(
        json.dumps(result_doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    env.cr.rollback()

print("CC08-T1 replay acceptance", result_doc.get("operation"), "provider_requests=0")
