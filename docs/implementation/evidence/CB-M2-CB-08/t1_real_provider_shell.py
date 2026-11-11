"""One-shot CC-08 T1 runner; execute through `odoo-bin shell` in odoo18ce.

The script uses one synthetic XLSX and the existing office Tool/Responses
Adapter/Validator/Accept services. All Odoo writes are rolled back at exit.
No credential value is read into evidence or printed.
"""

import hashlib
import json
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from openpyxl import Workbook, load_workbook


ROOT = Path("docs/implementation/evidence/CB-M2-CB-08")
PREFIX = "CB08-T1"
MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
MODEL_NAME = "gpt-5.6-luna"
# The active 8091 Discuss Thread is a read-only source for the already-selected
# Provider/Model pair. Its messages or attachments are never read or sent.
PROVIDER_REFERENCE_THREAD_ID = 19293
INSTRUCTION = (
    "In the Ledger worksheet, format the Amount value in cell B2 as USD currency "
    "with two decimal places. Preserve all values, formulas, worksheet names, "
    "and other workbook contents. Return the edited XLSX for review."
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def save_json(payload):
    payload["recorded_at_utc"] = datetime.now(timezone.utc).isoformat()
    (ROOT / "T1-real-provider-result.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def tool_message(thread, status="executing", result=None):
    data = {"type": "tool_execution", "tool_name": "office", "status": status}
    if result is not None:
        data["result"] = result
    return thread.message_post(
        body="Executing office" if status == "executing" else "Office result",
        body_json=data,
        llm_role="tool",
        author_id=False,
    )


def style_signature(cell):
    # Compare the workbook's resolved style record. openpyxl StyleProxy objects
    # can compare unequal across separately loaded workbooks despite identical
    # serialized styles; the stable style id is appropriate for this synthetic
    # no-style-change assertion, excluding the one requested target cell.
    return cell.style_id


result_doc = {
    "scenario": "CB08-T1",
    "layer": "real OpenAI Responses API + Hosted Code Interpreter + Odoo Tool/Validator/Accept services",
    "provider_call_count": 0,
    "provider_model_requested": MODEL_NAME,
    "synthetic_only": True,
    "database": "odoo18ce",
    "operation": "not_run",
}
source_bytes = b""
candidate_bytes = b""
candidate = session = thread = None

try:
    from odoo import tools
    from odoo.addons.office_engine_m2.services.edit_orchestrator import _provider_dependencies
    from odoo.addons.office_engine_m2.services.mapping_service import create_session

    dispatch_enabled = tools.config.get("office_engine_m2_external_provider_dispatch_enabled", False)
    result_doc["trusted_dispatch_config_enabled"] = dispatch_enabled is True or str(dispatch_enabled).lower() in {"1", "true", "yes"}
    reference_thread = env["llm.thread"].browse(PROVIDER_REFERENCE_THREAD_ID).exists()
    model = reference_thread.model_id if reference_thread else env["llm.model"]
    if (
        not result_doc["trusted_dispatch_config_enabled"]
        or not reference_thread
        or model.name != MODEL_NAME
        or model.provider_id.service != "openai"
        or model.model_use not in {"chat", "multimodal"}
    ):
        result_doc.update(operation="blocked", reason="dispatch_config_disabled_or_approved_model_unavailable")
        save_json(result_doc)
    else:
        provider = model.provider_id
        result_doc.update({
            "provider_reference_thread_id": reference_thread.id,
            "configured_provider": provider.name,
            "provider_service": provider.service,
            "api_key_present": bool(provider.api_key),
            "api_base_configured": bool(provider.api_base),
            "model_record_id": model.id,
        })
        if not provider.api_key:
            result_doc.update(operation="blocked", reason="provider_credential_not_configured")
            save_json(result_doc)
        else:
            company = env.company
            group_user = env.ref("base.group_user")
            owner = env["res.users"].with_context(no_reset_password=True).create({
                "name": "CC08 Synthetic Provider Test " + uuid4().hex[:8],
                "login": "cc08-provider-test-" + uuid4().hex,
                "email": "cc08-provider-test@example.invalid",
                "groups_id": [(6, 0, [group_user.id])],
                "company_ids": [(6, 0, [company.id])],
                "company_id": company.id,
            })
            user_env = env(user=owner.id, context={"allowed_company_ids": [company.id]})
            thread = user_env["llm.thread"].create({
                "name": "CC08 real Provider synthetic style edit " + uuid4().hex,
                "provider_id": provider.id,
                "model_id": model.id,
            })
            workbook = Workbook()
            worksheet = workbook.active
            worksheet.title = "Ledger"
            worksheet.append(["Description", "Amount", "Double"])
            worksheet.append(["Synthetic sample", 1234.5, "=B2*2"])
            stream = BytesIO()
            workbook.save(stream)
            workbook.close()
            source_bytes = stream.getvalue()
            (ROOT / "T1-input.xlsx").write_bytes(source_bytes)
            source_attachment = user_env["ir.attachment"].create({
                "name": "CB08-synthetic-ledger.xlsx",
                "type": "binary",
                "raw": source_bytes,
                "mimetype": MIME,
                "company_id": company.id,
                "public": False,
            })
            upload = thread.message_post(
                body="Synthetic XLSX upload for CC08-T1.",
                llm_role="user",
                author_id=user_env.user.partner_id.id,
                attachment_ids=[source_attachment.id],
            )
            create_session(
                user_env,
                thread_id=thread.id,
                source_message_id=upload.id,
                source_attachment_id=source_attachment.id,
                target_model="ir.attachment",
                target_record_id=source_attachment.id,
            )
            intent = thread.message_post(
                body=INSTRUCTION,
                llm_role="user",
                author_id=user_env.user.partner_id.id,
            )
            thread._office_bind_tools()
            office = thread.tool_ids.filtered(lambda item: item.name == "office")[:1]
            if not office:
                result_doc.update(operation="failed", reason="office_tool_not_bound")
                save_json(result_doc)
            else:
                deps = _provider_dependencies(user_env, thread)
                result_doc["provider_dependencies_available"] = bool(deps)
                if not deps:
                    result_doc.update(operation="blocked", reason="trusted_provider_dependencies_unavailable")
                    save_json(result_doc)
                else:
                    adapter, _client, configured_model, limits = deps
                    result_doc.update({
                        "adapter_class": type(adapter).__name__,
                        "configured_model": configured_model,
                        "timeout_seconds": limits.timeout_seconds,
                        "max_output_tokens": limits.max_output_tokens,
                        "memory_limit": limits.memory_limit,
                        "input_sha256": digest(source_bytes),
                        "input_bytes": len(source_bytes),
                    })
                    request_message = tool_message(thread)
                    result_doc["provider_call_count"] = 1
                    edit_result = office.with_context(message=request_message).execute({"action": "edit"})
                    request_message.write({
                        "body_json": {
                            "type": "tool_execution", "tool_name": "office",
                            "status": "completed", "result": edit_result,
                        }
                    })
                    result_doc["edit_result"] = {
                        key: edit_result.get(key)
                        for key in (
                            "status", "operation_status", "error_code", "candidate_version_id",
                            "candidate_state", "validation_result", "current_version_id",
                            "last_valid_version_id", "document_revision", "candidate_output_sha256",
                        )
                    }
                    provider_meta = edit_result.get("provider") or {}
                    result_doc["provider"] = {
                        key: provider_meta.get(key)
                        for key in (
                            "operation_status", "provider_response_id", "request_id",
                            "download_request_id", "tool_call_ids", "container_id",
                            "provider_file_ids", "provider_filename", "usage", "duration_ms",
                            "cleanup_state", "error", "candidate_sha256",
                        )
                    }
                    candidate_id = edit_result.get("candidate_version_id")
                    if edit_result.get("operation_status") != "candidate_review_required" or not candidate_id:
                        result_doc.update(operation="failed", reason="provider_did_not_produce_reviewable_candidate")
                        save_json(result_doc)
                    else:
                        candidate = user_env["office.workbook.version"].browse(candidate_id).exists()
                        session = candidate.session_id
                        candidate_bytes = candidate.output_attachment_id.raw or b""
                        (ROOT / "T1-candidate.xlsx").write_bytes(candidate_bytes)
                        result_doc.update({
                            "candidate_id": candidate.id,
                            "candidate_version_no": candidate.version_no,
                            "candidate_state": candidate.state,
                            "candidate_validation_result": candidate.validation_result,
                            "candidate_output_sha256": digest(candidate_bytes),
                            "candidate_output_bytes": len(candidate_bytes),
                            "candidate_input_sha256": candidate.input_sha256,
                            "current_before_accept_id": session.current_version_id.id or False,
                            "last_valid_before_accept_id": session.last_valid_version_id.id or False,
                            "revision_before_accept": session.document_revision,
                        })
                        src = load_workbook(BytesIO(source_bytes), data_only=False)
                        out = load_workbook(BytesIO(candidate_bytes), data_only=False)
                        src_ws = src["Ledger"]
                        out_ws = out["Ledger"]
                        target_format = out_ws["B2"].number_format
                        style_ok = ("$" in target_format or "USD" in target_format.upper()) and "0.00" in target_format
                        content_ok = all(
                            src_ws.cell(row=row, column=col).value == out_ws.cell(row=row, column=col).value
                            for row in range(1, max(src_ws.max_row, out_ws.max_row) + 1)
                            for col in range(1, max(src_ws.max_column, out_ws.max_column) + 1)
                        )
                        sheets_ok = src.sheetnames == out.sheetnames
                        non_target_style_ok = all(
                            style_signature(src_ws.cell(row=row, column=col))
                            == style_signature(out_ws.cell(row=row, column=col))
                            for row in range(1, max(src_ws.max_row, out_ws.max_row) + 1)
                            for col in range(1, max(src_ws.max_column, out_ws.max_column) + 1)
                            if (row, col) != (2, 2)
                        )
                        result_doc["independent_readback"] = {
                            "xlsx_opens": True,
                            "sheet_names_preserved": sheets_ok,
                            "target_number_format": target_format,
                            "target_format_is_usd_two_decimals": style_ok,
                            "values_and_formulas_preserved": content_ok,
                            "non_target_styles_preserved": non_target_style_ok,
                            "formula_c2": out_ws["C2"].value,
                        }
                        src.close()
                        out.close()
                        if not (style_ok and content_ok and sheets_ok and non_target_style_ok):
                            result_doc.update(operation="failed", reason="independent_xlsx_readback_assertion_failed")
                            save_json(result_doc)
                        else:
                            decision = thread.message_post(
                                body="I reviewed the synthetic Candidate and accept it.",
                                llm_role="user", author_id=user_env.user.partner_id.id,
                            )
                            accept_message = tool_message(thread)
                            accepted = office.with_context(message=accept_message).execute({
                                "action": "accept", "candidate_version_id": candidate.id,
                            })
                            accept_message.write({
                                "body_json": {
                                    "type": "tool_execution", "tool_name": "office",
                                    "status": "completed", "result": accepted,
                                }
                            })
                            session.invalidate_recordset()
                            candidate.invalidate_recordset()
                            accepted_bytes = session.current_version_id.output_attachment_id.raw or b""
                            (ROOT / "T1-accepted-v1.xlsx").write_bytes(accepted_bytes)
                            result_doc["accept_result"] = {
                                key: accepted.get(key)
                                for key in (
                                    "status", "operation_status", "version_id", "version_no",
                                    "current_version_id", "last_valid_version_id", "document_revision",
                                )
                            }
                            result_doc["accepted_state"] = {
                                "candidate_state": candidate.state,
                                "validation_result": candidate.validation_result,
                                "current_version_id": session.current_version_id.id,
                                "last_valid_version_id": session.last_valid_version_id.id,
                                "document_revision": session.document_revision,
                                "accepted_sha256": digest(accepted_bytes),
                                "accepted_matches_candidate_bytes": accepted_bytes == candidate_bytes,
                                "decision_message_id": decision.id,
                            }
                            result_doc["operation"] = (
                                "pass" if accepted.get("operation_status") == "accepted_current"
                                and session.current_version_id == candidate
                                and session.last_valid_version_id == candidate
                                and session.document_revision == 1
                                and candidate.validation_result in {"VERIFIED", "PARTIALLY_VERIFIED"}
                                and accepted_bytes == candidate_bytes
                                else "failed"
                            )
                            save_json(result_doc)
except Exception as exc:
    result_doc.update(operation="failed", exception_type=type(exc).__name__)
    save_json(result_doc)
finally:
    env.cr.rollback()

print("CC08-T1", result_doc.get("operation"), "provider_calls=", result_doc.get("provider_call_count"))
