"""Run one bounded Candidate B XLSX edit from an Odoo shell.

This script only reads the configured LLM model/provider records, uses the
existing provider client without exposing its credential, and creates local
synthetic evidence files. It never reads or writes Odoo business records.
"""

from __future__ import annotations

import base64
import hashlib
import json
import time
import zipfile
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill


MODEL_NAME = "gpt-5.6-luna"
MIME_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
MAX_INPUT_BYTES = 2_000_000
MAX_OUTPUT_BYTES = 2_000_000
MAX_OUTPUT_TOKENS = 1200
MAX_TOOL_CALLS = 1
MAX_HTTP_REQUESTS = 3
MAX_BUDGET_USD = 2.00
MODEL_INPUT_USD_PER_MILLION = 0.20
MODEL_OUTPUT_USD_PER_MILLION = 1.20
CI_1GB_USD_PER_20_MINUTES = 0.03
CONSERVATIVE_INPUT_TOKEN_RESERVE = 1_000_000
CONTAINER_RESERVE_UNITS = 4
EVIDENCE_DIR = Path(__file__).resolve().parent
INPUT_PATH = EVIDENCE_DIR / "tv_phase1a2_input.xlsx"
OUTPUT_PATH = EVIDENCE_DIR / "tv_phase1a2_output.xlsx"
MANIFEST_PATH = EVIDENCE_DIR / "input_manifest.json"
RESULT_PATH = EVIDENCE_DIR / "run_result.json"


class TestFailure(Exception):
    """A controlled TV failure with no sensitive exception text."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_fixture() -> dict:
    workbook = Workbook()
    inventory = workbook.active
    inventory.title = "Inventory"
    inventory.append(["Product", "Quantity", "Unit Price", "Amount"])
    inventory.append(["ITEM-A", 10, 5, "=B2*C2"])
    inventory.append(["ITEM-B", 20, 8, "=B3*C3"])

    notes = workbook.create_sheet("Notes")
    notes.append(["Key", "Value"])
    notes.append(["Source", "Synthetic TV"])
    notes.append(["Status", "Original"])

    header_fill = PatternFill(fill_type="solid", fgColor="1F4E78")
    header_font = Font(bold=True, color="FFFFFF")
    for sheet in (inventory, notes):
        for cell in sheet[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center")
    for row in (2, 3):
        inventory.cell(row=row, column=2).number_format = "0"
        inventory.cell(row=row, column=3).number_format = "0.00"
        inventory.cell(row=row, column=4).number_format = "0.00"
    inventory.column_dimensions["A"].width = 18
    inventory.column_dimensions["B"].width = 14
    inventory.column_dimensions["C"].width = 14
    inventory.column_dimensions["D"].width = 14
    notes.column_dimensions["A"].width = 14
    notes.column_dimensions["B"].width = 22
    workbook.properties.title = "Synthetic Candidate B TV"
    workbook.save(INPUT_PATH)

    if INPUT_PATH.stat().st_size > MAX_INPUT_BYTES:
        raise TestFailure("synthetic_input_exceeds_size_guard")
    with zipfile.ZipFile(INPUT_PATH) as archive:
        if archive.testzip() is not None:
            raise TestFailure("input_zip_integrity_failed")

    book = load_workbook(INPUT_PATH, data_only=False)
    sheets = {}
    for sheet in book.worksheets:
        cells = {}
        for row in sheet.iter_rows():
            for cell in row:
                if cell.value is not None:
                    cells[cell.coordinate] = {
                        "value": cell.value,
                        "data_type": cell.data_type,
                        "number_format": cell.number_format,
                        "style_id": cell.style_id,
                    }
        sheets[sheet.title] = {
            "state": sheet.sheet_state,
            "max_row": sheet.max_row,
            "max_column": sheet.max_column,
            "cells": cells,
            "merged_ranges": sorted(str(item) for item in sheet.merged_cells.ranges),
        }
    manifest = {
        "file": INPUT_PATH.name,
        "sha256": sha256_file(INPUT_PATH),
        "size_bytes": INPUT_PATH.stat().st_size,
        "sheetnames": book.sheetnames,
        "sheets": sheets,
        "defined_names": sorted(book.defined_names.keys()),
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True, default=str))
    book.close()
    return manifest


def standard_endpoint(provider) -> bool:
    from urllib.parse import urlparse

    raw_base = provider.api_base or ""
    base = raw_base or "https://api.openai.com/v1"
    parsed = urlparse(base)
    return (
        parsed.scheme == "https"
        and parsed.hostname == "api.openai.com"
        and parsed.port in (None, 443)
        and parsed.path.rstrip("/") == "/v1"
        and not parsed.query
        and not parsed.username
        and not parsed.password
    )


def style_signature(cell) -> tuple:
    color = cell.font.color
    color_signature = None
    if color is not None:
        color_signature = (color.type, color.rgb, color.indexed, color.theme, color.tint)
    fill_color = cell.fill.fgColor
    fill_signature = (fill_color.type, fill_color.rgb, fill_color.indexed, fill_color.theme, fill_color.tint)
    return (
        cell.style_id,
        cell.number_format,
        cell.font.name,
        cell.font.sz,
        cell.font.bold,
        cell.font.italic,
        color_signature,
        cell.fill.fill_type,
        fill_signature,
        cell.alignment.horizontal,
        cell.alignment.vertical,
        cell.alignment.wrap_text,
        cell.protection.locked,
        cell.protection.hidden,
    )


def validate_output(manifest: dict) -> dict:
    if not OUTPUT_PATH.exists() or OUTPUT_PATH.stat().st_size == 0:
        raise TestFailure("output_file_missing_or_empty")
    if OUTPUT_PATH.stat().st_size > MAX_OUTPUT_BYTES:
        raise TestFailure("output_exceeds_size_guard")
    with zipfile.ZipFile(OUTPUT_PATH) as archive:
        bad_member = archive.testzip()
        if bad_member is not None:
            raise TestFailure("output_zip_integrity_failed")

    original = load_workbook(INPUT_PATH, data_only=False)
    candidate = load_workbook(OUTPUT_PATH, data_only=False)
    checks = {}
    checks["sheetnames_unchanged"] = candidate.sheetnames == manifest["sheetnames"]
    checks["target_value"] = candidate["Inventory"]["B2"].value == 15
    checks["target_type_numeric"] = candidate["Inventory"]["B2"].data_type == "n"
    checks["untargeted_quantity_unchanged"] = candidate["Inventory"]["B3"].value == 20
    checks["formula_d2_preserved"] = candidate["Inventory"]["D2"].value == "=B2*C2"
    checks["formula_d3_preserved"] = candidate["Inventory"]["D3"].value == "=B3*C3"
    checks["notes_unchanged"] = (
        candidate["Notes"]["B2"].value == "Synthetic TV"
        and candidate["Notes"]["B3"].value == "Original"
    )
    checks["defined_names_unchanged"] = sorted(candidate.defined_names.keys()) == manifest["defined_names"]

    value_differences = []
    style_differences = []
    dimension_differences = []
    for title in manifest["sheetnames"]:
        before = original[title]
        after = candidate[title]
        if sorted(str(item) for item in before.merged_cells.ranges) != sorted(
            str(item) for item in after.merged_cells.ranges
        ):
            value_differences.append({"sheet": title, "kind": "merged_ranges"})
        if before.sheet_state != after.sheet_state:
            value_differences.append({"sheet": title, "kind": "sheet_state"})
        if (before.max_row, before.max_column) != (after.max_row, after.max_column):
            dimension_differences.append({
                "sheet": title,
                "before": [before.max_row, before.max_column],
                "after": [after.max_row, after.max_column],
            })
        max_row = max(before.max_row, after.max_row)
        max_col = max(before.max_column, after.max_column)
        for row in range(1, max_row + 1):
            for col in range(1, max_col + 1):
                left = before.cell(row=row, column=col)
                right = after.cell(row=row, column=col)
                expected_value = 15 if (title, left.coordinate) == ("Inventory", "B2") else left.value
                if right.value != expected_value or right.data_type != (
                    "n" if (title, left.coordinate) == ("Inventory", "B2") else left.data_type
                ):
                    value_differences.append({"sheet": title, "cell": left.coordinate})
                if style_signature(left) != style_signature(right):
                    style_differences.append({"sheet": title, "cell": left.coordinate})
    checks["only_target_cell_value_changed"] = not value_differences
    checks["styles_unchanged"] = not style_differences
    checks["dimensions_unchanged"] = not dimension_differences
    checks["formula_text_only_checked_not_recalculated"] = True
    original.close()
    candidate.close()
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise TestFailure("readback_assertions_failed:" + ",".join(failed))
    return {
        "checks": checks,
        "value_differences": value_differences,
        "style_differences": style_differences,
        "dimension_differences": dimension_differences,
        "output_sha256": sha256_file(OUTPUT_PATH),
        "output_size_bytes": OUTPUT_PATH.stat().st_size,
    }


def api_error_metadata(exc) -> dict:
    status = getattr(exc, "status_code", None)
    request_id = getattr(exc, "request_id", None)
    return {
        "class": type(exc).__name__,
        "http_status": status,
        "request_id": request_id,
    }


def main(env) -> dict:
    result = {
        "status": "not_run",
        "model": MODEL_NAME,
        "api_endpoint_class": "official_openai_api",
        "limits": {
            "max_api_http_requests": MAX_HTTP_REQUESTS,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "max_builtin_tool_calls": MAX_TOOL_CALLS,
            "client_timeout_seconds": 120,
            "sdk_automatic_retries": 0,
            "code_interpreter_memory_limit": "1g",
            "code_interpreter_network": "disabled",
            "budget_cap_usd": MAX_BUDGET_USD,
        },
        "api_requests": [],
        "cleanup": {"container_delete": "not_needed"},
    }
    client = None
    container_id = None
    request_count = 0
    started = time.monotonic()
    try:
        manifest = build_fixture()
        result["input"] = {
            "file": INPUT_PATH.name,
            "sha256": manifest["sha256"],
            "size_bytes": manifest["size_bytes"],
            "sheetnames": manifest["sheetnames"],
            "formulas": ["Inventory!D2 =B2*C2", "Inventory!D3 =B3*C3"],
        }

        models = env["llm.model"].search([
            ("name", "=", MODEL_NAME),
            ("active", "=", True),
            ("model_use", "=", "chat"),
            ("default", "=", True),
            ("provider_id.service", "=", "openai"),
            ("provider_id.active", "=", True),
        ])
        if len(models) != 1:
            raise TestFailure("active_default_provider_model_not_unique")
        provider = models.provider_id
        if not provider.api_key:
            raise TestFailure("provider_credential_not_configured")
        if not standard_endpoint(provider):
            raise TestFailure("provider_api_base_not_standard_openai_endpoint")
        result["provider_preflight"] = {
            "active_default_chat_match_count": 1,
            "service": "openai",
            "credential_present": True,
            "api_base": "https://api.openai.com/v1 (verified without logging its value)",
            "project_identity": "credential selected from active Odoo provider; project identifier is not stored in llm.provider",
        }

        preflight_token_reserve = (
            CONSERVATIVE_INPUT_TOKEN_RESERVE * MODEL_INPUT_USD_PER_MILLION * 2
            + MAX_OUTPUT_TOKENS * MODEL_OUTPUT_USD_PER_MILLION * 1.5
        ) / 1_000_000
        preflight_container_reserve = CONTAINER_RESERVE_UNITS * CI_1GB_USD_PER_20_MINUTES
        preflight_total = (preflight_token_reserve + preflight_container_reserve) * 1.10
        result["budget_preflight"] = {
            "input_token_reserve": CONSERVATIVE_INPUT_TOKEN_RESERVE,
            "output_token_cap": MAX_OUTPUT_TOKENS,
            "container_reserve_units": CONTAINER_RESERVE_UNITS,
            "including_10_percent_margin_usd": round(preflight_total, 6),
            "cap_usd": MAX_BUDGET_USD,
            "within_cap": preflight_total <= MAX_BUDGET_USD,
        }
        if preflight_total > MAX_BUDGET_USD:
            raise TestFailure("budget_preflight_exceeds_cap")

        if request_count >= MAX_HTTP_REQUESTS:
            raise TestFailure("request_budget_guard_exceeded")
        client = provider.client.with_options(timeout=120, max_retries=0)
        file_bytes = INPUT_PATH.read_bytes()
        file_data = "data:" + MIME_XLSX + ";base64," + base64.b64encode(file_bytes).decode("ascii")
        request_count += 1
        result["api_requests"].append({"operation": "responses.create", "attempt": request_count})
        response = client.responses.create(
            model=MODEL_NAME,
            input=[{
                "role": "user",
                "content": [
                    {"type": "input_file", "filename": INPUT_PATH.name, "file_data": file_data},
                    {
                        "type": "input_text",
                        "text": (
                            "Edit the attached synthetic Excel workbook using the Code Interpreter tool. "
                            "Set Inventory!B2 (the Quantity for ITEM-A) from 10 to 15. Preserve both "
                            "Amount formulas exactly. Do not change ITEM-B or any other cell, style, "
                            "sheet, or workbook structure. Save and return the edited workbook as "
                            "tv_phase1a2_output.xlsx."
                        ),
                    },
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
            max_tool_calls=MAX_TOOL_CALLS,
            store=False,
        )
        usage = getattr(response, "usage", None)
        input_tokens = getattr(usage, "input_tokens", None) if usage else None
        output_tokens = getattr(usage, "output_tokens", None) if usage else None
        threshold_multiplier = 2 if input_tokens is not None and input_tokens > 272_000 else 1
        output_multiplier = 1.5 if threshold_multiplier == 2 else 1
        token_cost = None
        if input_tokens is not None and output_tokens is not None:
            token_cost = (
                input_tokens * MODEL_INPUT_USD_PER_MILLION * threshold_multiplier
                + output_tokens * MODEL_OUTPUT_USD_PER_MILLION * output_multiplier
            ) / 1_000_000
        result["provider_response"] = {
            "request_id": getattr(response, "_request_id", None),
            "response_id": getattr(response, "id", None),
            "model": getattr(response, "model", None),
            "status": getattr(response, "status", None),
            "output_item_types": [getattr(item, "type", "unknown") for item in response.output],
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": getattr(usage, "total_tokens", None) if usage else None,
            },
            "estimated_token_cost_usd": token_cost,
        }

        file_id = None
        output_filename = None
        tool_call_ids = []
        for item in response.output:
            if getattr(item, "type", None) == "code_interpreter_call":
                container_id = container_id or getattr(item, "container_id", None)
                tool_call_ids.append(getattr(item, "id", None))
            if getattr(item, "type", None) == "message":
                for content in getattr(item, "content", []):
                    for annotation in getattr(content, "annotations", []):
                        if getattr(annotation, "type", None) == "container_file_citation":
                            candidate_container = getattr(annotation, "container_id", None)
                            if candidate_container:
                                container_id = container_id or candidate_container
                            candidate_filename = getattr(annotation, "filename", None)
                            if candidate_filename and candidate_filename.lower().endswith(".xlsx"):
                                if file_id is not None:
                                    raise TestFailure("multiple_xlsx_outputs_not_expected")
                                file_id = getattr(annotation, "file_id", None)
                                output_filename = candidate_filename

        result["provider_response"]["code_interpreter_tool_call_ids"] = tool_call_ids
        result["provider_response"]["container_id"] = container_id
        result["provider_response"]["output_file_id"] = file_id
        result["provider_response"]["output_filename"] = output_filename
        if getattr(response, "status", None) != "completed":
            raise TestFailure("provider_response_not_completed")
        if not container_id or not file_id:
            raise TestFailure("no_downloadable_xlsx_file_annotation")
        if request_count >= MAX_HTTP_REQUESTS:
            raise TestFailure("request_budget_guard_exceeded")

        request_count += 1
        result["api_requests"].append({"operation": "container_file_content.retrieve", "attempt": request_count})
        binary_response = client.containers.files.content.retrieve(file_id, container_id=container_id, timeout=120)
        try:
            output_bytes = binary_response.read()
            download_request_id = getattr(binary_response, "request_id", None)
        finally:
            binary_response.close()
        if not output_bytes:
            raise TestFailure("downloaded_output_is_empty")
        OUTPUT_PATH.write_bytes(output_bytes)
        validation = validate_output(manifest)
        result["download"] = {
            "request_id": download_request_id,
            "file": OUTPUT_PATH.name,
            **validation,
        }
        actual_cost = token_cost
        # Reserve four 20-minute 1GB container billing units, exceeding the
        # normal short edit and inactivity-expiry window by a wide margin.
        conservative_container_reserve = CONTAINER_RESERVE_UNITS * CI_1GB_USD_PER_20_MINUTES
        if actual_cost is None:
            raise TestFailure("provider_usage_missing_cannot_reconcile_budget")
        budget_reserve = actual_cost + conservative_container_reserve
        budget_reserve_with_margin = budget_reserve * 1.10
        result["budget"] = {
            "model_token_cost_usd": actual_cost,
            "container_cost_reserve_usd": conservative_container_reserve,
            "conservative_total_with_10_percent_margin_usd": budget_reserve_with_margin,
            "cap_usd": MAX_BUDGET_USD,
            "within_cap": budget_reserve_with_margin <= MAX_BUDGET_USD,
        }
        if budget_reserve_with_margin > MAX_BUDGET_USD:
            raise TestFailure("conservative_budget_reserve_exceeds_cap")
        result["status"] = "pass"
    except TestFailure as exc:
        result["status"] = "blocked" if str(exc).startswith(("active_default", "provider_credential", "provider_api_base")) else "fail"
        result["error"] = {"class": type(exc).__name__, "code": str(exc)}
    except Exception as exc:  # Do not serialize exception text or request bodies.
        result["status"] = "fail"
        result["error"] = api_error_metadata(exc)
    finally:
        result["elapsed_seconds"] = round(time.monotonic() - started, 3)
        result["api_request_count"] = request_count
        if container_id and client is not None:
            if request_count < MAX_HTTP_REQUESTS:
                try:
                    request_count += 1
                    result["api_requests"].append({"operation": "containers.delete", "attempt": request_count})
                    client.containers.delete(container_id, timeout=30)
                    result["cleanup"] = {"container_delete": "success", "container_id": container_id}
                except Exception as exc:
                    result["cleanup"] = {
                        "container_delete": "failed_or_unconfirmed",
                        "error": api_error_metadata(exc),
                        "container_id": container_id,
                        "automatic_expiry_expected": True,
                    }
            else:
                result["cleanup"] = {
                    "container_delete": "not_attempted_request_limit_reached",
                    "container_id": container_id,
                    "automatic_expiry_expected": True,
                }
        result["api_request_count"] = request_count
        result["total_api_requests_never_exceeds"] = MAX_HTTP_REQUESTS
        RESULT_PATH.write_text(json.dumps(result, indent=2, sort_keys=True, default=str))
        if client is not None:
            client.close()
    print(json.dumps(result, indent=2, sort_keys=True, default=str), flush=True)
    return result
