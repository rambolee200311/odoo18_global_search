"""One final, tightly bounded Candidate B Responses request."""

from __future__ import annotations

import importlib.util
import json
import time
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
HELPER_PATH = SCRIPT_DIR / "run_candidate_b.py"
HELPER_SPEC = importlib.util.spec_from_file_location("candidate_b_helper", HELPER_PATH)
HELPER = importlib.util.module_from_spec(HELPER_SPEC)
HELPER_SPEC.loader.exec_module(HELPER)

ATTEMPT1_RESULT = SCRIPT_DIR / "attempt1_run_result.json"
ATTEMPT2_RESULT = SCRIPT_DIR / "attempt2_run_result.json"
OUTPUT_PATH = SCRIPT_DIR / "tv_phase1a2_output.xlsx"
MAX_OUTPUT_TOKENS = 4000
MAX_TOOL_CALLS = 1
MAX_HTTP_REQUESTS_FOR_ATTEMPT = 3


def main(env) -> dict:
    result = {
        "status": "not_run",
        "model": HELPER.MODEL_NAME,
        "attempt_number": 2,
        "api_requests": [],
        "limits": {
            "max_test_responses_requests_total": 3,
            "test_responses_requests_used_before_this_attempt": 1,
            "max_resource_http_requests_this_attempt": MAX_HTTP_REQUESTS_FOR_ATTEMPT,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "max_builtin_tool_calls": MAX_TOOL_CALLS,
            "timeout_seconds": 120,
            "automatic_retries": 0,
            "memory_limit": "1g",
            "network": "disabled",
            "budget_cap_usd": HELPER.MAX_BUDGET_USD,
        },
    }
    client = None
    container_id = None
    request_count = 0
    responses_request_attempted = 0
    started = time.monotonic()
    try:
        if OUTPUT_PATH.exists():
            raise HELPER.TestFailure("output_path_already_exists_refusing_overwrite")
        manifest = json.loads((SCRIPT_DIR / "input_manifest.json").read_text())
        if manifest.get("sha256") != HELPER.sha256_file(HELPER.INPUT_PATH):
            raise HELPER.TestFailure("input_fixture_changed_since_attempt1")
        previous = json.loads(ATTEMPT1_RESULT.read_text())
        previous_tokens = previous.get("provider_response", {}).get("estimated_token_cost_usd")
        if previous_tokens is None:
            raise HELPER.TestFailure("prior_usage_unavailable_budget_cannot_be_reconciled")

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

        input_reserve = (
            1_000_000 * HELPER.MODEL_INPUT_USD_PER_MILLION * 2
            + MAX_OUTPUT_TOKENS * HELPER.MODEL_OUTPUT_USD_PER_MILLION * 1.5
        ) / 1_000_000
        container_reserve = HELPER.CONTAINER_RESERVE_UNITS * HELPER.CI_1GB_USD_PER_20_MINUTES
        prior_container_reserve = HELPER.CONTAINER_RESERVE_UNITS * HELPER.CI_1GB_USD_PER_20_MINUTES
        cumulative_preflight = (input_reserve + container_reserve + previous_tokens + prior_container_reserve) * 1.10
        result["budget_preflight"] = {
            "previous_actual_token_cost_usd": previous_tokens,
            "input_token_reserve_this_attempt": 1_000_000,
            "output_token_cap_this_attempt": MAX_OUTPUT_TOKENS,
            "two_container_reserves_usd": prior_container_reserve + container_reserve,
            "cumulative_reserve_with_10_percent_margin_usd": round(cumulative_preflight, 6),
            "cap_usd": HELPER.MAX_BUDGET_USD,
            "within_cap": cumulative_preflight <= HELPER.MAX_BUDGET_USD,
        }
        if cumulative_preflight > HELPER.MAX_BUDGET_USD:
            raise HELPER.TestFailure("cumulative_budget_preflight_exceeds_cap")

        file_bytes = HELPER.INPUT_PATH.read_bytes()
        if len(file_bytes) > HELPER.MAX_INPUT_BYTES:
            raise HELPER.TestFailure("synthetic_input_exceeds_size_guard")
        file_data = "data:" + HELPER.MIME_XLSX + ";base64," + __import__("base64").b64encode(file_bytes).decode("ascii")
        client = provider.client.with_options(timeout=120, max_retries=0)
        request_count += 1
        responses_request_attempted += 1
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
                            "Use exactly one Code Interpreter execution. In that one execution, open the attached "
                            "tv_phase1a2_input.xlsx, set only Inventory!B2 from 10 to 15, keep D2 and D3 as their "
                            "original formulas, keep ITEM-B and the entire Notes sheet unchanged, save as "
                            "tv_phase1a2_output.xlsx, read the saved workbook back once, and return that XLSX file. "
                            "Do not explain the steps or perform extra inspections."
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
                input_tokens * HELPER.MODEL_INPUT_USD_PER_MILLION * threshold_multiplier
                + output_tokens * HELPER.MODEL_OUTPUT_USD_PER_MILLION * output_multiplier
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
                            container_id = container_id or getattr(annotation, "container_id", None)
                            name = getattr(annotation, "filename", None)
                            if name and name.lower().endswith(".xlsx"):
                                if file_id is not None:
                                    raise HELPER.TestFailure("multiple_xlsx_outputs_not_expected")
                                file_id = getattr(annotation, "file_id", None)
                                output_filename = name
        result["provider_response"].update({
            "code_interpreter_tool_call_ids": tool_call_ids,
            "container_id": container_id,
            "output_file_id": file_id,
            "output_filename": output_filename,
        })
        if not container_id or not file_id:
            raise HELPER.TestFailure("no_downloadable_xlsx_file_annotation")

        if request_count >= MAX_HTTP_REQUESTS_FOR_ATTEMPT:
            raise HELPER.TestFailure("request_budget_guard_exceeded")
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
            **validation,
        }

        if token_cost is None:
            raise HELPER.TestFailure("provider_usage_missing_cannot_reconcile_budget")
        container_cost_reserve = HELPER.CONTAINER_RESERVE_UNITS * HELPER.CI_1GB_USD_PER_20_MINUTES
        cumulative_cost_reserve = (previous_tokens + token_cost + prior_container_reserve + container_cost_reserve) * 1.10
        result["budget"] = {
            "previous_token_cost_usd": previous_tokens,
            "this_attempt_token_cost_usd": token_cost,
            "two_container_reserves_usd": prior_container_reserve + container_cost_reserve,
            "cumulative_reserve_with_10_percent_margin_usd": round(cumulative_cost_reserve, 6),
            "cap_usd": HELPER.MAX_BUDGET_USD,
            "within_cap": cumulative_cost_reserve <= HELPER.MAX_BUDGET_USD,
        }
        if cumulative_cost_reserve > HELPER.MAX_BUDGET_USD:
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
            if request_count < MAX_HTTP_REQUESTS_FOR_ATTEMPT:
                try:
                    request_count += 1
                    result["api_requests"].append({"operation": "containers.delete", "attempt_request": request_count})
                    client.containers.delete(container_id, timeout=30)
                    result["cleanup"] = {"container_delete": "success", "container_id": container_id}
                except Exception as exc:
                    result["cleanup"] = {
                        "container_delete": "failed_or_unconfirmed",
                        "error": HELPER.api_error_metadata(exc),
                        "container_id": container_id,
                        "automatic_expiry_expected": True,
                    }
            else:
                result["cleanup"] = {
                    "container_delete": "not_attempted_request_limit_reached",
                    "container_id": container_id,
                    "automatic_expiry_expected": True,
                }
        result["api_request_count_this_attempt"] = request_count
        result["provider_test_request_count_cumulative"] = 1 + responses_request_attempted
        ATTEMPT2_RESULT.write_text(json.dumps(result, indent=2, sort_keys=True, default=str))
        if client is not None:
            client.close()
    print(json.dumps(result, indent=2, sort_keys=True, default=str), flush=True)
    return result
