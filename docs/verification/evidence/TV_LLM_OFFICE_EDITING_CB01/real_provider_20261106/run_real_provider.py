"""One sequential, synthetic-only real Provider attempt for CC-M2-CB-01.

Run this file inside the repository's read-only Odoo shell. It obtains the
existing configured provider client through the ORM, never reads or prints the
credential value, records one Responses attempt before dispatch, and delegates
the only network operation to the production ResponsesAdapter.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from urllib.parse import urlparse

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

from odoo.addons.llm_openai.services.responses_adapter import AdapterLimits, ResponsesAdapter


EVIDENCE_DIR = Path(
    "docs/verification/evidence/TV_LLM_OFFICE_EDITING_CB01/real_provider_20261106"
).resolve()
INPUT_PATH = EVIDENCE_DIR / "input_synthetic.xlsx"
LEDGER_PATH = EVIDENCE_DIR / "responses_ledger.json"
MODEL = "gpt-5.6-luna"
MAX_RESPONSES = 10
INSTRUCTION = (
    "Edit the attached synthetic workbook using Code Interpreter and return the actual XLSX file. "
    "In the Inventory sheet, change only cell B2 from numeric 10 to numeric 15. "
    "Preserve Inventory!C2, the formula in Inventory!D2, every other cell, and the Notes sheet. "
    "Save the edited workbook as cc01_candidate.xlsx and attach that file in your response."
)


def _write_json(path: Path, value: dict) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")
    temp.replace(path)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _make_fixture() -> bytes:
    workbook = Workbook()
    inventory = workbook.active
    inventory.title = "Inventory"
    inventory.append(["Product", "Quantity", "Marker", "Amount"])
    inventory.append(["ITEM-A", 10, "KEEP", "=B2*2"])
    inventory.append(["ITEM-B", 20, "KEEP-B", "=B3*2"])
    notes = workbook.create_sheet("Notes")
    notes.append(["Key", "Value"])
    notes.append(["Source", "Synthetic CC-01"])
    notes.append(["Status", "Original"])
    for cell in inventory[1] + notes[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="365F91")
    inventory["B2"].number_format = "0.0"
    output = __import__("io").BytesIO()
    workbook.save(output)
    return output.getvalue()


def _select_provider(env):
    matches = env["llm.model"].search(
        [
            ("name", "=", MODEL),
            ("active", "=", True),
            ("model_use", "=", "chat"),
            ("default", "=", True),
            ("provider_id.service", "=", "openai"),
            ("provider_id.active", "=", True),
        ]
    )
    if len(matches) != 1:
        raise RuntimeError("approved_active_default_model_not_unique")
    provider = matches.provider_id
    base = (provider.api_base or "https://api.openai.com/v1").strip()
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
        raise RuntimeError("provider_endpoint_not_approved")
    # The existing provider factory accesses the secret only to construct the
    # SDK client. This runner never reads, serializes, prints, or persists it.
    client = provider.client
    return matches, provider, client


def run(env):
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    if INPUT_PATH.exists():
        fixture_bytes = INPUT_PATH.read_bytes()
    else:
        fixture_bytes = _make_fixture()
        INPUT_PATH.write_bytes(fixture_bytes)
    input_hash = _sha256(fixture_bytes)
    started_at = time.time()
    client = None
    matches = None
    provider = None
    result = None
    ledger = None
    attempt_record = None
    request_attempt_reserved = False
    output_path = None
    result_path = None
    try:
        matches, provider, client = _select_provider(env)
        ledger = json.loads(LEDGER_PATH.read_text()) if LEDGER_PATH.exists() else {
            "authorization": "CC-M2-CB-01 real Provider test; synthetic XLSX only",
            "model": MODEL,
            "max_responses_create_authorized": MAX_RESPONSES,
            "sdk_automatic_retries": 0,
            "concurrent_requests": 1,
            "attempts": [],
        }
        if ledger.get("model") != MODEL or ledger.get("max_responses_create_authorized") != MAX_RESPONSES:
            raise RuntimeError("request_ledger_scope_mismatch")
        if len(ledger.get("attempts", [])) >= MAX_RESPONSES:
            raise RuntimeError("responses_create_limit_reached")
        attempt_no = len(ledger["attempts"]) + 1
        output_path = EVIDENCE_DIR / f"output_candidate_{attempt_no:02d}.xlsx"
        result_path = EVIDENCE_DIR / f"provider_result_{attempt_no:02d}.json"
        if output_path.exists() or result_path.exists():
            raise RuntimeError("refusing_to_overwrite_attempt_evidence")
        attempt_record = {
            "attempt": attempt_no,
            "status": "started",
            "model": MODEL,
            "fixture_bytes": len(fixture_bytes),
            "input_sha256": input_hash,
            "instruction_summary": "Set Inventory!B2 from 10 to 15; preserve all other content.",
            "request_timeout_seconds": 120,
            "max_output_tokens": 4000,
            "max_input_bytes": 2_000_000,
            "max_output_bytes": 2_000_000,
            "container_memory_limit": "1g",
            "container_network": "disabled",
            "endpoint_policy": "HTTPS api.openai.com/v1 validated in memory",
            "provider_service": provider.service,
            "active_default_model_count": len(matches),
            "api_key_value_logged": False,
            "responses_create_attempted": True,
        }
        ledger["attempts"].append(attempt_record)
        _write_json(LEDGER_PATH, ledger)

        limits = AdapterLimits(
            allowed_models=frozenset({MODEL}),
            max_input_bytes=2_000_000,
            max_output_bytes=2_000_000,
            max_output_tokens=4000,
            timeout_seconds=120,
            memory_limit="1g",
            max_archive_entries=10_000,
            max_uncompressed_bytes=100_000_000,
            remote_cleanup_required=False,
        )
        request_attempt_reserved = True
        result = ResponsesAdapter().execute(
            provider_client=client,
            model=MODEL,
            input_xlsx=fixture_bytes,
            instruction=INSTRUCTION,
            limits=limits,
            input_sha256=input_hash,
            correlation_id=f"cc01-real-provider-20261106-attempt-{attempt_no}",
        )

        if result.candidate_bytes is not None:
            output_path.write_bytes(result.candidate_bytes)

        usage = result.usage
        token_cost_estimate = None
        if usage.get("input_tokens") is not None and usage.get("output_tokens") is not None:
            input_rate_multiplier = 2 if usage["input_tokens"] > 272_000 else 1
            output_rate_multiplier = 1.5 if input_rate_multiplier == 2 else 1
            token_cost_estimate = (
                usage["input_tokens"] * 0.20 * input_rate_multiplier
                + usage["output_tokens"] * 1.20 * output_rate_multiplier
            ) / 1_000_000
        tool_call_count = len(result.tool_call_ids)
        container_estimate = 0.03 if result.container_id else None
        tool_cost_estimate = tool_call_count * 2.50 / 1000
        estimated_cost = (
            token_cost_estimate + tool_cost_estimate + container_estimate
            if token_cost_estimate is not None and container_estimate is not None
            else None
        )
        final_result = result.to_dict()
        final_result.update(
            {
                "provider_model_returned": MODEL if result.provider_response_id else None,
                "output_path": str(output_path) if result.candidate_bytes is not None else None,
                "output_bytes": len(result.candidate_bytes) if result.candidate_bytes is not None else None,
                "estimated_token_cost_usd_uncached_rate": token_cost_estimate,
                "estimated_container_cost_usd_one_session": container_estimate,
                "estimated_tool_call_cost_usd": tool_cost_estimate,
                "estimated_total_cost_usd_not_invoice": estimated_cost,
                "invoice_cost": "UNVERIFIED",
                "provider_key_logged": False,
                "provider_prompt_logged": False,
                "elapsed_seconds": round(time.time() - started_at, 3),
            }
        )
        _write_json(result_path, final_result)
        attempt_record.update(
            {
                "status": result.operation_status,
                "provider_response_id": result.provider_response_id,
                "request_id": result.request_id,
                "download_request_id": result.download_request_id,
                "tool_call_ids": list(result.tool_call_ids),
                "container_id": result.container_id,
                "provider_file_ids": list(result.provider_file_ids),
                "cleanup_state": result.cleanup_state,
                "candidate_sha256": result.candidate_sha256,
                "usage": usage,
                "duration_ms": result.duration_ms,
                "error_category": result.error.category if result.error else None,
                "estimated_total_cost_usd_not_invoice": estimated_cost,
            }
        )
        _write_json(LEDGER_PATH, ledger)
        print(
            "CC01_PROVIDER_RESULT="
            + json.dumps(
                {
                    "operation_status": result.operation_status,
                    "candidate_present": result.candidate_bytes is not None,
                    "provider_response_id": result.provider_response_id,
                    "request_id": result.request_id,
                    "candidate_sha256": result.candidate_sha256,
                    "usage": usage,
                    "cleanup_state": result.cleanup_state,
                    "error_category": result.error.category if result.error else None,
                },
                sort_keys=True,
            )
        )
    except Exception as exc:
        # Never expose exception text; it can contain request/configuration
        # details. Once a slot is durably recorded, conservatively count it.
        failure = {
            "status": "indeterminate" if request_attempt_reserved else "preflight_blocked",
            "exception_class": type(exc).__name__,
            "error_category": "provider_or_runner_error_redacted",
            "responses_create_attempted": request_attempt_reserved,
            "credential_value_logged": False,
            "elapsed_seconds": round(time.time() - started_at, 3),
        }
        if result_path is not None:
            _write_json(result_path, failure)
        if attempt_record is not None and ledger is not None:
            attempt_record.update(failure)
            _write_json(LEDGER_PATH, ledger)
        print("CC01_PROVIDER_RESULT=" + json.dumps(failure, sort_keys=True))
    finally:
        if client is not None:
            try:
                client.close()
            except Exception:
                pass
        # This script performs ORM reads only; explicitly roll back the shell
        # transaction so this verification cannot persist Odoo writes.
        try:
            env.cr.rollback()
        except Exception:
            pass


run(env)
