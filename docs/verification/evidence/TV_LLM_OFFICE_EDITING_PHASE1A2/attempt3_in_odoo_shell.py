"""Final authorized Candidate B Responses request and artifact readback."""

from __future__ import annotations

import base64
import importlib.util
import json
import time
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
HELPER_PATH = SCRIPT_DIR / "run_candidate_b.py"
SPEC = importlib.util.spec_from_file_location("candidate_b_helper_attempt3", HELPER_PATH)
HELPER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HELPER)

ATTEMPT1 = json.loads((SCRIPT_DIR / "attempt1_run_result.json").read_text())
ATTEMPT2 = json.loads((SCRIPT_DIR / "attempt2_run_result.json").read_text())
ATTEMPT3_RESULT = SCRIPT_DIR / "attempt3_run_result.json"
OUTPUT_PATH = SCRIPT_DIR / "tv_phase1a2_output.xlsx"
MAX_OUTPUT_TOKENS = 4000
MAX_TOOL_CALLS = 1
MAX_RESOURCE_HTTP_CALLS = 5


def main(env) -> dict:
    result = {
        "status": "not_run",
        "attempt_number": 3,
        "model": HELPER.MODEL_NAME,
        "api_requests": [],
        "limits": {
            "max_test_responses_requests_total": 3,
            "previous_test_responses_requests": 2,
            "max_resource_http_calls_this_attempt": MAX_RESOURCE_HTTP_CALLS,
            "output_tokens": MAX_OUTPUT_TOKENS,
            "requested_builtin_tool_calls": MAX_TOOL_CALLS,
            "timeout_seconds": 120,
            "automatic_retries": 0,
            "memory_limit": "1g",
            "network": "disabled",
            "budget_cap_usd": HELPER.MAX_BUDGET_USD,
        },
    }
    client = None
    response_id = None
    container_id = None
    request_count = 0
    response_request_count = 0
    started = time.monotonic()
    try:
        if OUTPUT_PATH.exists():
            raise HELPER.TestFailure("output_path_already_exists_refusing_overwrite")
        manifest = json.loads((SCRIPT_DIR / "input_manifest.json").read_text())
        if manifest.get("sha256") != HELPER.sha256_file(HELPER.INPUT_PATH):
            raise HELPER.TestFailure("input_fixture_changed_since_prior_attempts")

        prior_token_costs = []
        prior_containers = 0
        for prior in (ATTEMPT1, ATTEMPT2):
            cost = prior.get("provider_response", {}).get("estimated_token_cost_usd")
            if cost is None:
                raise HELPER.TestFailure("prior_usage_unavailable_budget_cannot_be_reconciled")
            prior_token_costs.append(cost)
            if prior.get("provider_response", {}).get("container_id"):
                prior_containers += 1

        models = env["llm.model"].search([
            ("name", "=", HELPER.MODEL_NAME),
            ("active", "=", True),
            ("model_use", "=", "chat"),
            ("default", "=", True),
            ("provider_id.service", "=", "openai"),
            ("provider_id.active", "=", True),
        ])
        if len(models) != 1:
            raise HELPER.TestFailure("active_default_provider_model_not_unique")
        provider = models.provider_id
        if not provider.api_key:
            raise HELPER.TestFailure("provider_credential_not_configured")
        if not HELPER.standard_endpoint(provider):
            raise HELPER.TestFailure("provider_api_base_not_standard_openai_endpoint")
        result["provider_preflight"] = {
            "active_default_chat_match_count": 1,
            "service": "openai",
            "credential_present": True,
            "api_base_class": "standard_https_openai_api_v1",
            "credential_source": "existing Odoo provider client; key value not read into logs",
        }

        max_input_tokens_reserved = 1_000_000
        input_reserve = max_input_tokens_reserved * HELPER.MODEL_INPUT_USD_PER_MILLION * 2 / 1_000_000
        output_reserve = MAX_OUTPUT_TOKENS * HELPER.MODEL_OUTPUT_USD_PER_MILLION * 1.5 / 1_000_000
        current_container_reserve = HELPER.CONTAINER_RESERVE_UNITS * HELPER.CI_1GB_USD_PER_20_MINUTES
        prior_container_reserve = prior_containers * HELPER.CONTAINER_RESERVE_UNITS * HELPER.CI_1GB_USD_PER_20_MINUTES
        preflight_total = (sum(prior_token_costs) + prior_container_reserve + input_reserve + output_reserve + current_container_reserve) * 1.10
        result["budget_preflight"] = {
            "prior_actual_token_costs_usd": prior_token_costs,
            "prior_container_count": prior_containers,
            "input_token_reserve_this_attempt": max_input_tokens_reserved,
            "output_token_cap_this_attempt": MAX_OUTPUT_TOKENS,
            "container_reserve_units_each": HELPER.CONTAINER_RESERVE_UNITS,
            "cumulative_reserve_with_10_percent_margin_usd": round(preflight_total, 6),
            "cap_usd": HELPER.MAX_BUDGET_USD,
            "within_cap": preflight_total <= HELPER.MAX_BUDGET_USD,
        }
        if preflight_total > HELPER.MAX_BUDGET_USD:
            raise HELPER.TestFailure("cumulative_budget_preflight_exceeds_cap")

        file_bytes = HELPER.INPUT_PATH.read_bytes()
        if len(file_bytes) > HELPER.MAX_INPUT_BYTES:
            raise HELPER.TestFailure("synthetic_input_exceeds_size_guard")
        file_data = "data:" + HELPER.MIME_XLSX + ";base64," + base64.b64encode(file_bytes).decode("ascii")
        client = provider.client.with_options(timeout=120, max_retries=0)
        request_count += 1
        response_request_count += 1
        result["api_requests"].append({"operation": "responses.create", "attempt_request": request_count})
        response = client.responses.create(
            model=HELPER.MODEL_NAME,
            input=[{
                "role": "user",
                "content": [
                    {"type": "input_file", "filename": HELPER.INPUT_PATH.name, "file_data": file_data},
                    {
                        "type": "input_text",
                        "text": (
                            "Edit the attached workbook with Code Interpreter and return the actual XLSX artifact, "
                            "not only a description. In one Python execution, open the attached "
                            "tv_phase1a2_input.xlsx from /mnt/data, change only Inventory!B2 to 15, preserve the "
                            "formulas in D2 and D3 and all other cells/styles/sheets, save to "
                            "/mnt/data/tv_phase1a2_output.xlsx, reopen it to check the requested change, then "
                            "include that saved workbook as a downloadable file in your final response."
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
        )
        response_id = getattr(response, "id", None)
        usage = getattr(response, "usage", None)
        input_tokens = getattr(usage, "input_tokens", None) if usage else None
        output_tokens = getattr(usage, "output_tokens", None) if usage else None
        threshold_multiplier = 2 if input_tokens is not None and input_tokens > 272_000 else 1
        output_multiplier = 1.5 if threshold_multiplier == 2 else 1
        token_cost = None
        if input_tokens is not None and output_tokens is not None:
            token_cost = (
                input_tokens * HELPER.MODEL_INPUT_USD_PER_MILLION * threshold_multiplier
                + output_tokens * HELPER.MODEL_OUTPUT_USD_PER_MILLION * output_multiplier
            ) / 1_000_000

        item_diagnostics = []
        file_id = None
        filename = None
        tool_call_ids = []
        for item in response.output:
            item_type = getattr(item, "type", "unknown")
            diagnostic = {"type": item_type, "id": getattr(item, "id", None)}
            if item_type == "code_interpreter_call":
                container_id = container_id or getattr(item, "container_id", None)
                tool_call_ids.append(getattr(item, "id", None))
                outputs = getattr(item, "outputs", []) or []
                diagnostic["tool_output_types"] = [getattr(output, "type", "unknown") for output in outputs]
                diagnostic["tool_output_count"] = len(outputs)
            if item_type == "message":
                content_diagnostics = []
                for content in getattr(item, "content", []):
                    annotations = []
                    for annotation in getattr(content, "annotations", []):
                        annotation_type = getattr(annotation, "type", "unknown")
                        annotations.append(annotation_type)
                        if annotation_type == "container_file_citation":
                            container_id = container_id or getattr(annotation, "container_id", None)
                            name = getattr(annotation, "filename", None)
                            if name and name.lower().endswith(".xlsx"):
                                if file_id is not None:
                                    raise HELPER.TestFailure("multiple_xlsx_outputs_not_expected")
                                file_id = getattr(annotation, "file_id", None)
                                filename = name
                    content_diagnostics.append({
                        "type": getattr(content, "type", "unknown"),
                        "annotation_types": annotations,
                    })
                diagnostic["content"] = content_diagnostics
            item_diagnostics.append(diagnostic)
        result["provider_response"] = {
            "request_id": getattr(response, "_request_id", None),
            "response_id": response_id,
            "model": getattr(response, "model", None),
            "status": getattr(response, "status", None),
            "incomplete_reason": getattr(getattr(response, "incomplete_details", None), "reason", None),
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": getattr(usage, "total_tokens", None) if usage else None,
            },
            "estimated_token_cost_usd": token_cost,
            "output_items": item_diagnostics,
            "code_interpreter_tool_call_ids": tool_call_ids,
            "container_id": container_id,
            "output_file_id_from_citation": file_id,
            "output_filename_from_citation": filename,
        }

        if not container_id:
            raise HELPER.TestFailure("no_code_interpreter_container_id")
        if not file_id:
            if request_count >= MAX_RESOURCE_HTTP_CALLS:
                raise HELPER.TestFailure("request_budget_guard_exceeded_before_container_listing")
            request_count += 1
            result["api_requests"].append({"operation": "container_files.list", "attempt_request": request_count})
            page = client.containers.files.list(container_id, limit=20, timeout=30)
            listed = list(page)
            result["container_files"] = [
                {"id": getattr(item, "id", None), "filename": getattr(item, "filename", None), "bytes": getattr(item, "bytes", None)}
                for item in listed
            ]
            candidates = [
                item for item in listed
                if (getattr(item, "filename", "") or "").lower().endswith(".xlsx")
                and getattr(item, "filename", None) != HELPER.INPUT_PATH.name
            ]
            if len(candidates) == 1:
                file_id = getattr(candidates[0], "id", None)
                filename = getattr(candidates[0], "filename", None)
            elif len(candidates) > 1:
                raise HELPER.TestFailure("ambiguous_container_xlsx_outputs")

        if not file_id:
            raise HELPER.TestFailure("no_generated_xlsx_available_in_container")
        if request_count >= MAX_RESOURCE_HTTP_CALLS:
            raise HELPER.TestFailure("request_budget_guard_exceeded_before_download")
        request_count += 1
        result["api_requests"].append({"operation": "container_file_content.retrieve", "attempt_request": request_count})
        binary_response = client.containers.files.content.retrieve(file_id, container_id=container_id, timeout=120)
        try:
            output_bytes = binary_response.read()
            download_request_id = getattr(binary_response, "request_id", None)
        finally:
            binary_response.close()
        if not output_bytes:
            raise HELPER.TestFailure("downloaded_output_is_empty")
        OUTPUT_PATH.write_bytes(output_bytes)
        validation = HELPER.validate_output(manifest)
        result["download"] = {
            "request_id": download_request_id,
            "file": OUTPUT_PATH.name,
            "provider_filename": filename,
            "provider_file_id": file_id,
            **validation,
        }

        if token_cost is None:
            raise HELPER.TestFailure("provider_usage_missing_cannot_reconcile_budget")
        actual_total = (
            sum(prior_token_costs) + token_cost
            + (prior_containers + 1) * HELPER.CONTAINER_RESERVE_UNITS * HELPER.CI_1GB_USD_PER_20_MINUTES
        ) * 1.10
        result["budget"] = {
            "prior_token_costs_usd": prior_token_costs,
            "this_attempt_token_cost_usd": token_cost,
            "container_reserve_total_usd": (prior_containers + 1) * HELPER.CONTAINER_RESERVE_UNITS * HELPER.CI_1GB_USD_PER_20_MINUTES,
            "cumulative_reserve_with_10_percent_margin_usd": round(actual_total, 6),
            "cap_usd": HELPER.MAX_BUDGET_USD,
            "within_cap": actual_total <= HELPER.MAX_BUDGET_USD,
        }
        if actual_total > HELPER.MAX_BUDGET_USD:
            raise HELPER.TestFailure("cumulative_budget_reconciliation_exceeds_cap")
        result["status"] = "pass" if getattr(response, "status", None) == "completed" else "pass_file_verified_response_incomplete"
    except HELPER.TestFailure as exc:
        result["status"] = "blocked" if str(exc).startswith(("active_default", "provider_credential", "provider_api_base", "prior_usage")) else "fail"
        result["error"] = {"class": type(exc).__name__, "code": str(exc)}
    except Exception as exc:
        result["status"] = "fail"
        result["error"] = HELPER.api_error_metadata(exc)
    finally:
        result["elapsed_seconds"] = round(time.monotonic() - started, 3)
        if container_id and client is not None:
            if request_count < MAX_RESOURCE_HTTP_CALLS:
                try:
                    request_count += 1
                    result["api_requests"].append({"operation": "containers.delete", "attempt_request": request_count})
                    client.containers.delete(container_id, timeout=30)
                    result["cleanup_container"] = "success"
                except Exception as exc:
                    result["cleanup_container"] = "failed_or_unconfirmed"
                    result["cleanup_container_error"] = HELPER.api_error_metadata(exc)
            else:
                result["cleanup_container"] = "not_attempted_resource_request_limit_reached"
        if response_id and client is not None:
            if request_count < MAX_RESOURCE_HTTP_CALLS:
                try:
                    request_count += 1
                    result["api_requests"].append({"operation": "responses.delete", "attempt_request": request_count})
                    client.responses.delete(response_id, timeout=30)
                    result["cleanup_response"] = "success"
                except Exception as exc:
                    result["cleanup_response"] = "failed_or_unconfirmed"
                    result["cleanup_response_error"] = HELPER.api_error_metadata(exc)
            else:
                result["cleanup_response"] = "not_attempted_resource_request_limit_reached"
        result["api_request_count_this_attempt_including_cleanup"] = request_count
        result["test_response_request_count_cumulative"] = 2 + response_request_count
        result["total_api_requests_never_exceeds_this_attempt"] = MAX_RESOURCE_HTTP_CALLS
        ATTEMPT3_RESULT.write_text(json.dumps(result, indent=2, sort_keys=True, default=str))
        if client is not None:
            client.close()
    print(json.dumps(result, indent=2, sort_keys=True, default=str), flush=True)
    return result
