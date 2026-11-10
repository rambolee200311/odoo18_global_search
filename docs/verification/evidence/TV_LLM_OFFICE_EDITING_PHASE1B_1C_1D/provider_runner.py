"""One-request-at-a-time Responses + Code Interpreter TV runner.

Execute from an Odoo shell so it can obtain the existing OpenAI client without
exporting or printing its credential. Only the three synthetic XLSX fixtures
in this directory are eligible inputs.
"""

from __future__ import annotations

import base64
import hashlib
import json
import time
import zipfile
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent
LEDGER = ROOT / "responses_ledger.json"
MODEL = "gpt-5.6-luna"
MIME_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
MAX_RESPONSES = 5  # deliberately lower than the user's authorized ceiling of 8
MAX_OUTPUT_TOKENS = 4000
TIMEOUT_SECONDS = 120
MAX_INPUT_BYTES = 8000
MAX_UNCOMPRESSED_BYTES = 30000
BUDGET_USD = 2.00
INPUT_RESERVE_TOKENS = 100000
OUTPUT_RATE_PER_M = 1.20
INPUT_RATE_PER_M = 0.20
CI_CONTAINER_RESERVE = 0.03  # one 1 GB, 20-minute billing session per response
CI_TOOL_CALL_RESERVE = 100  # conservative cost reserve; not an API-enforced limit
CI_TOOL_CALL_RATE_PER_1K = 2.50
MARGIN = 1.15
RESERVE_PER_RESPONSE = (
    INPUT_RESERVE_TOKENS * INPUT_RATE_PER_M / 1_000_000
    + MAX_OUTPUT_TOKENS * OUTPUT_RATE_PER_M / 1_000_000
    + CI_CONTAINER_RESERVE
    + CI_TOOL_CALL_RESERVE * CI_TOOL_CALL_RATE_PER_1K / 1000
) * MARGIN
PLANNED_RESPONSES = 5
INPUTS = {
    "phase1b": "phase1b_input.xlsx",
    "phase1c_v2": "phase1c_v1.xlsx",
    "phase1c_v3": "phase1c_v2.xlsx",
    "phase1c_v4": "phase1c_v3.xlsx",
    "phase1d": "phase1d_input.xlsx",
}
OUTPUTS = {
    "phase1b": "phase1b_output.xlsx",
    "phase1c_v2": "phase1c_v2.xlsx",
    "phase1c_v3": "phase1c_v3.xlsx",
    "phase1c_v4": "phase1c_v4.xlsx",
    "phase1d": "phase1d_output.xlsx",
}
INSTRUCTIONS = {
    "phase1b": (
        "Use the Code Interpreter's Python tool to edit this attached synthetic workbook and return an actual XLSX file. "
        "In the Inventory sheet, set B2 (Quantity for ITEM-A) to numeric 15 and C3 (Unit Price for ITEM-B) to numeric 9.5. "
        "Preserve all formulas, values, types, styles, number formats, sheets, and workbook structure outside those two value changes. "
        "Do not recalculate or replace formulas. Save as phase1b_output.xlsx and attach that file in the response."
    ),
    "phase1c_v2": (
        "Use the Code Interpreter's Python tool to edit the attached V1 synthetic workbook and return an actual XLSX file. "
        "Change only Inventory!B2 (ITEM-A Quantity) from 10 to numeric 15. Preserve the V1 formulas, other values, styles, "
        "and workbook structure. Save as phase1c_v2.xlsx and attach the saved file in the response."
    ),
    "phase1c_v3": (
        "Use the Code Interpreter's Python tool to edit the attached actual V2 workbook and return an actual XLSX file. "
        "Change Inventory!C3 (ITEM-B Unit Price) to numeric 9.5. Apply a light yellow fill to the whole ITEM-B row A3:D3. "
        "Keep the earlier V2 change Inventory!B2=15, all formulas, other values, sheets, and workbook structure. "
        "Save as phase1c_v3.xlsx and attach that file."
    ),
    "phase1c_v4": (
        "Use the Code Interpreter's Python tool to edit the attached actual V3 workbook and return an actual XLSX file. "
        "Sort the Inventory data rows (rows 2 through 4) by Product ascending, moving each whole row together so its values and styles stay paired. "
        "Preserve the V2/V3 value and fill edits, formulas, the header, Notes sheet, and all other workbook content. "
        "Save as phase1c_v4.xlsx and attach that file."
    ),
    "phase1d": (
        "Use the Code Interpreter's Python tool to edit the attached synthetic structure-fidelity workbook and return an actual XLSX file. "
        "Change only Inventory!B2 from 10 to numeric 11. Preserve the formulas and references, styles, dates and number formats, merged cells, "
        "freeze panes, hidden rows/columns, data validation, conditional formatting, defined names, sheet names/order/visibility, and all non-target values. "
        "Save as phase1d_output.xlsx and attach that actual file."
    ),
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n")
    temporary.replace(path)


def _safe_error(exc: Exception) -> dict:
    status = getattr(exc, "status_code", None)
    request_id = getattr(exc, "request_id", None)
    return {
        "class": type(exc).__name__,
        "http_status": status if isinstance(status, int) else None,
        "request_id": request_id if isinstance(request_id, str) and len(request_id) < 100 else None,
        "message": "redacted; exception text may contain request details",
    }


def _init_or_read_ledger() -> dict:
    if LEDGER.exists():
        return json.loads(LEDGER.read_text())
    ledger = {
        "authorization": "user authorized Candidate B Phase 1B-1D, synthetic XLSX only",
        "model": MODEL,
        "max_responses_authorized": 8,
        "runner_response_ceiling": MAX_RESPONSES,
        "budget_cap_usd": BUDGET_USD,
        "budget_reserve_per_response_usd": round(RESERVE_PER_RESPONSE, 6),
        "planned_response_count": PLANNED_RESPONSES,
        "planned_reserve_with_margin_usd": round(RESERVE_PER_RESPONSE * PLANNED_RESPONSES, 6),
        "sdk_automatic_retries": 0,
        "attempts": [],
    }
    _write_json(LEDGER, ledger)
    return ledger


def _provider(env):
    matches = env["llm.model"].search([
        ("name", "=", MODEL),
        ("active", "=", True),
        ("model_use", "=", "chat"),
        ("default", "=", True),
        ("provider_id.service", "=", "openai"),
        ("provider_id.active", "=", True),
    ])
    if len(matches) != 1:
        raise RuntimeError("active_default_model_not_unique")
    provider = matches.provider_id
    if not provider.api_key:
        raise RuntimeError("provider_credential_not_configured")
    base = (provider.api_base or "").strip()
    if base:
        parsed = urlparse(base)
        if (
            parsed.scheme != "https"
            or parsed.hostname != "api.openai.com"
            or parsed.path.rstrip("/") != "/v1"
            or parsed.port not in (None, 443)
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise RuntimeError("provider_endpoint_not_approved_openai_endpoint")
    return matches, provider


def _input_manifest_check(path: Path) -> dict:
    if not path.is_file() or path.stat().st_size > MAX_INPUT_BYTES:
        raise RuntimeError("input_missing_or_exceeds_size_guard")
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise RuntimeError("input_xlsx_zip_integrity_failed")
        uncompressed = sum(member.file_size for member in archive.infolist())
        if uncompressed > MAX_UNCOMPRESSED_BYTES:
            raise RuntimeError("input_xlsx_uncompressed_size_exceeds_guard")
        if any(name.startswith("xl/media/") for name in archive.namelist()):
            raise RuntimeError("embedded_media_not_allowed_in_synthetic_fixture")
    return {
        "name": path.name,
        "bytes": path.stat().st_size,
        "uncompressed_xlsx_member_bytes": uncompressed,
        "sha256": sha256(path.read_bytes()),
    }


def run_case(env, case_id: str) -> dict:
    if case_id not in INPUTS:
        raise ValueError("unknown_case")
    ledger = _init_or_read_ledger()
    if ledger.get("model") != MODEL or ledger.get("budget_cap_usd") != BUDGET_USD:
        raise RuntimeError("ledger_scope_mismatch")
    if len(ledger["attempts"]) >= MAX_RESPONSES:
        raise RuntimeError("responses_request_ceiling_reached")
    if RESERVE_PER_RESPONSE * len(ledger["attempts"]) + RESERVE_PER_RESPONSE > BUDGET_USD:
        raise RuntimeError("preflight_budget_reserve_exceeds_cap")

    input_path = ROOT / INPUTS[case_id]
    output_path = ROOT / OUTPUTS[case_id]
    if output_path.exists():
        raise RuntimeError("refusing_to_overwrite_existing_candidate")
    input_meta = _input_manifest_check(input_path)
    models, provider = _provider(env)
    client = provider.client.with_options(timeout=TIMEOUT_SECONDS, max_retries=0)
    request_index = len(ledger["attempts"]) + 1
    record = {
        "request_index": request_index,
        "case_id": case_id,
        "model": MODEL,
        "input": input_meta,
        "output_expected": OUTPUTS[case_id],
        "status": "started",
        "started_unix": time.time(),
        "request_timeout_seconds": TIMEOUT_SECONDS,
        "sdk_automatic_retries": 0,
        "output_token_cap": MAX_OUTPUT_TOKENS,
        "max_tool_calls_requested_but_not_treated_as_hard_cap": 1,
        "provider_preflight": {
            "active_default_chat_model_count": len(models),
            "service": "openai",
            "credential_present_without_reading_or_logging_value": True,
            "endpoint_host_path_validated_without_logging_value": True,
            "project_id": "UNVERIFIED: no project identifier field on llm.provider",
        },
    }
    ledger["attempts"].append(record)
    _write_json(LEDGER, ledger)  # an interrupted call still consumes a slot

    response = None
    response_id = None
    container_id = None
    file_id = None
    client_http_request_id = None
    started = time.monotonic()
    cleanup = {"container": "not_found", "response": "not_created"}
    phase = "responses.create"
    try:
        data = "data:" + MIME_XLSX + ";base64," + base64.b64encode(input_path.read_bytes()).decode("ascii")
        response = client.responses.create(
            model=MODEL,
            input=[{
                "role": "user",
                "content": [
                    {"type": "input_file", "filename": input_path.name, "file_data": data},
                    {"type": "input_text", "text": INSTRUCTIONS[case_id]},
                ],
            }],
            tools=[{
                "type": "code_interpreter",
                "container": {
                    "type": "auto",
                    "memory_limit": "1g",
                    "network_policy": {"type": "disabled"},
                },
            }],
            tool_choice="required",
            max_output_tokens=MAX_OUTPUT_TOKENS,
            max_tool_calls=1,
            store=True,
        )
        phase = "response_processing"
        response_id = getattr(response, "id", None)
        client_http_request_id = getattr(response, "_request_id", None)
        item_types = []
        tool_ids = []
        annotations = []
        for item in response.output:
            item_type = getattr(item, "type", "unknown")
            item_types.append(item_type)
            if item_type == "code_interpreter_call":
                container_id = container_id or getattr(item, "container_id", None)
                tool_ids.append(getattr(item, "id", None))
            if item_type == "message":
                for content in getattr(item, "content", []) or []:
                    for annotation in getattr(content, "annotations", []) or []:
                        if getattr(annotation, "type", None) == "container_file_citation":
                            candidate = {
                                "container_id": getattr(annotation, "container_id", None),
                                "file_id": getattr(annotation, "file_id", None),
                                "filename": getattr(annotation, "filename", None),
                            }
                            annotations.append(candidate)
                            container_id = container_id or candidate["container_id"]
                            if candidate["filename"] == OUTPUTS[case_id]:
                                file_id = candidate["file_id"]
        usage = getattr(response, "usage", None)
        input_tokens = getattr(usage, "input_tokens", None) if usage else None
        output_tokens = getattr(usage, "output_tokens", None) if usage else None
        multiplier_in = 2 if input_tokens is not None and input_tokens > 272000 else 1
        multiplier_out = 1.5 if multiplier_in == 2 else 1
        token_cost = None
        if isinstance(input_tokens, int) and isinstance(output_tokens, int):
            token_cost = (
                input_tokens * INPUT_RATE_PER_M * multiplier_in
                + output_tokens * OUTPUT_RATE_PER_M * multiplier_out
            ) / 1_000_000
        record["provider_response"] = {
            "request_id": client_http_request_id,
            "response_id": response_id,
            "status": getattr(response, "status", None),
            "incomplete_reason": getattr(getattr(response, "incomplete_details", None), "reason", None),
            "actual_model": getattr(response, "model", None),
            "output_item_types": item_types,
            "code_interpreter_call_ids": tool_ids,
            "code_interpreter_call_count": len(tool_ids),
            "container_id": container_id,
            "file_citations": annotations,
            "selected_output_file_id": file_id,
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": getattr(usage, "total_tokens", None) if usage else None,
            },
            "estimated_token_cost_usd": token_cost,
        }
        if not file_id and container_id:
            phase = "container_files.list"
            files = list(client.containers.files.list(container_id, limit=30, timeout=30))
            candidates = [
                item for item in files
                if (getattr(item, "filename", "") or "").lower().endswith(".xlsx")
                and getattr(item, "filename", None) != input_path.name
            ]
            record["container_file_list"] = [
                {"id": getattr(item, "id", None), "filename": getattr(item, "filename", None), "bytes": getattr(item, "bytes", None)}
                for item in files
            ]
            if len(candidates) == 1:
                file_id = getattr(candidates[0], "id", None)
                record["provider_response"]["selected_output_file_id"] = file_id
                record["provider_response"]["selected_output_filename"] = getattr(candidates[0], "filename", None)
            elif len(candidates) > 1:
                raise RuntimeError("ambiguous_xlsx_outputs")
        if file_id and container_id:
            phase = "container_file_content.retrieve"
            binary_response = client.containers.files.content.retrieve(file_id, container_id=container_id, timeout=60)
            try:
                output_bytes = binary_response.read()
                record["download_request_id"] = getattr(binary_response, "request_id", None)
            finally:
                binary_response.close()
            if not output_bytes or len(output_bytes) > 2_000_000:
                raise RuntimeError("downloaded_xlsx_empty_or_exceeds_guard")
            output_path.write_bytes(output_bytes)
            record["output"] = {
                "filename": output_path.name,
                "provider_filename": record["provider_response"].get("selected_output_filename") or next(
                    (x["filename"] for x in annotations if x["file_id"] == file_id), None
                ),
                "provider_file_id": file_id,
                "bytes": len(output_bytes),
                "sha256": sha256(output_bytes),
                "zip_integrity": _zip_integrity(output_path),
            }
        else:
            record["output"] = None
        record["status"] = "file_downloaded" if record["output"] else "no_xlsx_output"
    except Exception as exc:  # no raw exception, prompt, code, or credential is persisted
        record["failure_phase"] = phase
        record["response_received"] = response is not None
        record["status"] = "api_connection_error" if type(exc).__name__ == "APIConnectionError" and response is None else "request_or_download_failed"
        record["error"] = _safe_error(exc)
    finally:
        record["elapsed_seconds"] = round(time.monotonic() - started, 3)
        if container_id:
            try:
                client.containers.delete(container_id, timeout=30)
                cleanup["container"] = "deleted"
            except Exception as exc:
                cleanup["container"] = "delete_failed_or_unconfirmed"
                cleanup["container_error"] = _safe_error(exc)
        if response_id:
            try:
                client.responses.delete(response_id, timeout=30)
                cleanup["response"] = "deleted"
            except Exception as exc:
                cleanup["response"] = "delete_failed_or_unconfirmed"
                cleanup["response_error"] = _safe_error(exc)
        record["cleanup"] = cleanup
        record["finished_unix"] = time.time()
        record["reserved_amount_for_response_usd"] = round(RESERVE_PER_RESPONSE, 6)
        _write_json(LEDGER, ledger)
        client.close()
    return record


def _zip_integrity(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        return "PASS" if archive.testzip() is None else "FAIL"
