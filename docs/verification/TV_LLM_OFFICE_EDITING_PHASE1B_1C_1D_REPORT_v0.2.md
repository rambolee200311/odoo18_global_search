# Office Engine M2 — Candidate B Phase 1B–1D Report v0.2

**Date:** 2026-11-06  
**Status:** **BLOCKED** — Responses API connection failed before a Response was received. Phase 1B–1D editing claims are not verified. Review also found a budget-gate deviation before the manual retry; exact billing and compliance with the $2 cap cannot be proven.
**Scope:** Authorized synthetic-file TV using the existing Odoo OpenAI Provider, fixed model **gpt-5.6-luna**, Responses API, and Code Interpreter. No production Odoo code, business data, configuration, or service was changed.

This is the post-authorization execution result. The earlier v0.1 report remains unchanged as a record of the pre-authorization **BLOCKED AT G0** state.

## 1. G0 and Execution Baseline

| Gate | Result | Evidence |
|---|---|---|
| Git baseline | PASS | Branch main; HEAD f9801fca76f7c248a9cc823c583138ab0191b978. Existing untracked reports, evidence, and .coverage were preserved. No tracked diff was present before this execution. |
| Runtime | PASS for test tooling | Repository venv: Python 3.11.9, OpenAI SDK 2.54.0, openpyxl 3.1.5. |
| Odoo 8091 | PASS (not restarted) | Read-only listener check after the attempts showed PID 4295 on *:8091. |
| Provider / model selection | PASS for local configuration | The runner found exactly one active default OpenAI chat model named gpt-5.6-luna; a credential was configured. A later read-only ORM recheck classified the endpoint as the exact approved OpenAI base shape. Neither credential nor endpoint literal was logged. Project ID is UNVERIFIED because llm.provider has no Project ID field. |
| User authorization | PASS | This round explicitly authorized synthetic XLSX uploads, the existing Provider, up to eight Responses requests, a $2 cap, and temporary remote retention. |
| Request / cost controls | PARTIAL — budget-gate deviation; actual charge UNVERIFIED | SDK max_retries=0, timeout 120 seconds, output cap 4,000 tokens, one 1GB Code Interpreter container configuration, network disabled, and an evidence ledger that counts each attempted Responses request before dispatch. Runner ceiling was five, below the authorized eight, but the six-request contingency was not included before the manual retry. |
| Provider API response | BLOCKED | Two explicitly counted responses.create attempts raised APIConnectionError; neither returned an HTTP status, request ID, Response ID, usage, container ID, or file ID. |

### Budget preflight

Before the first call, the five-request execution plan reserved per request: 100,000 input tokens at the published standard input rate, 4,000 output tokens, one 1GB/20-minute container session, 100 generic tool-call units, and a 15% margin. This produced a planned reserve of **$1.7526**, below the **$2.00** cap. The 100 tool-call amount was a budget reserve, not a provider-enforced call limit; max_tool_calls=1 was requested but is not treated as a reliable hard limit based on the prior Phase 1A-2 evidence.

The fixtures are 5.9–6.5 KB compressed and 20.3–22.3 KB uncompressed. No token usage was returned in this round, so actual token charges and invoice charges are UNVERIFIED; no $0 spend is claimed. The two attempted calls each consumed a planned reserve of $0.35052, or $0.70104 in reserved budget. No further request was made after the repeated connection error.

**Budget-gate deviation:** the original five-request plan covered one Phase 1B request, three Phase 1C requests, and one Phase 1D request. After the first connection failure, adding a manual retry made the full intended plan six requests. At the same reserve this is $2.10312, above the $2.00 cap. I did not recompute this full-plan reserve before issuing attempt 2. That retry was a process error even though it remained within the eight-request count cap. No more Provider requests were made; known reserve for the two attempted calls is $0.70104, but actual charges and the hard cap outcome remain UNVERIFIED because neither API call returned usage or a request ID.

## 2. Official Capability Evidence

Official documentation available on the execution date states that gpt-5.6-luna supports the Responses endpoint and Code Interpreter, and lists input/output rates of $0.20/$1.20 per million tokens. The Code Interpreter guide documents XLSX files as a supported container file type and retrieval of generated container files. The pricing page lists 1GB Hosted Shell/Code Interpreter at $0.03 per 20-minute container session, billed by minute with a five-minute minimum.

- [GPT-5.6 Luna model capabilities and pricing](https://developers.openai.com/api/docs/models/gpt-5.6-luna)
- [Code Interpreter, generated files, and retrieval](https://developers.openai.com/api/docs/guides/tools-code-interpreter)
- [API pricing, including container sessions](https://developers.openai.com/api/docs/pricing)

These official capabilities do not prove this Odoo Provider credential or Project can reach the API in the current runtime. The two failed calls provide no evidence that the model lacks XLSX-editing capability.

## 3. Provider Request Log

Input for both attempts was the synthetic phase1b_input.xlsx, SHA-256 38499b0f59737af2e11460a738602199aa2696d496b23ce8f6f4e652d1ab4d07. The prompt asked the model to set Inventory!B2 to 15 and Inventory!C3 to 9.5, preserve all other values, formulas, styles, sheets, and structure, and return the actual edited XLSX.

| Attempt | Result | Elapsed | HTTP / request IDs | Response / usage | File / cleanup |
|---|---|---:|---|---|---|
| 1 | APIConnectionError during responses.create | 36.129 s | No HTTP status or request ID | No Response received; token usage unavailable | No output, Response ID, or container ID returned; no identifiable remote resource could be deleted. |
| 2 (explicit manual retry) | APIConnectionError during responses.create | 38.689 s | No HTTP status or request ID | No Response received; token usage unavailable | No output, Response ID, or container ID returned; no identifiable remote resource could be deleted. |

There were **two attempted Responses API create calls**, **zero returned Responses**, **zero returned XLSX files**, and no SDK automatic retries. The manual retry was separately recorded in the ledger; it was not silent. The API connection failure's lower-level cause is UNVERIFIED: retained logs do not distinguish DNS, transport, TLS, proxy, or service-side causes. No raw exception text was retained because it may contain request details.

The inline XLSX input created no separate Files API file ID. Because neither call returned a Response or container identifier, remote deletion and whether the server accepted any request before the connection failed cannot be confirmed. This is a cleanup evidence gap, not evidence that a resource definitely remained.

Detailed sanitized ledger: docs/verification/evidence/TV_LLM_OFFICE_EDITING_PHASE1B_1C_1D/responses_ledger.json.

## 4. Phase Results

| Phase | Functional capability | Safety / file result | Product capability result | Reason |
|---|---|---|---|---|
| Phase 1B / TV-LE-02 | UNVERIFIED | No candidate file; no readback | UNSATISFIED / BLOCKED | Both API attempts failed before returning a Response. This is not an edit-function FAIL and does not establish NOT SUPPORTED. |
| Phase 1C / TV-LE-03 | NOT RUN | No V2/V3/V4 and no lineage diff | UNSATISFIED / BLOCKED | The required Phase 1B / V2 dependency did not produce a valid file. No model-generated later version was fabricated. |
| Phase 1D / TV-LE-04 | NOT RUN | No output workbook to compare | UNSATISFIED / BLOCKED | Per the approved test order and dependency rule, Phase 1D was not run after Phase 1B failed. |

The previously prepared fixtures remain offline-valid, but no phase1b_output.xlsx, V2, V3, V4, or phase1d_output.xlsx exists. Consequently, no independent candidate-file diff or output SHA-256 exists. Formula preservation, row sorting, styles, workbook structure, and multi-turn lineage were not tested in this round. No formula recalculation was claimed.

## 5. Offline Test Evidence

Commands run:

    ./venv/bin/python -m py_compile docs/verification/evidence/TV_LLM_OFFICE_EDITING_PHASE1B_1C_1D/provider_runner.py docs/verification/evidence/TV_LLM_OFFICE_EDITING_PHASE1B_1C_1D/verify_candidates.py
    ./venv/bin/python docs/verification/evidence/TV_LLM_OFFICE_EDITING_PHASE1B_1C_1D/verify_fixtures.py

Actual results: Python syntax compilation exited 0; fixture verifier reported offline_fixture_verification=PASS, all three input XLSX ZIP checks PASS, and candidate_edits=0. These checks validate test inputs and scripts only; they are not Provider editing tests.

| Input fixture | Bytes | SHA-256 | Offline result |
|---|---:|---|---|
| phase1b_input.xlsx | 5,953 | 38499b0f59737af2e11460a738602199aa2696d496b23ce8f6f4e652d1ab4d07 | PASS |
| phase1c_v1.xlsx | 5,887 | 578ba0caffd61da9866262cca42e9da14b7f1dbed90c41667426e013a505e909 | PASS |
| phase1d_input.xlsx | 6,420 | 7e1d01384c3c16c57a058fe73a7c53395ad8d45203eedb5be625e055280ff24d | PASS |

## 6. Evidence and Change Scope

Created or updated by this authorized TV run:

- docs/verification/TV_LLM_OFFICE_EDITING_PHASE1B_1C_1D_REPORT_v0.2.md — this execution report; v0.1 was not overwritten.
- docs/verification/evidence/TV_LLM_OFFICE_EDITING_PHASE1B_1C_1D/provider_runner.py — bounded Responses runner using the existing Odoo Provider client.
- docs/verification/evidence/TV_LLM_OFFICE_EDITING_PHASE1B_1C_1D/verify_candidates.py — independent read-only candidate comparison, not run because outputs are absent.
- docs/verification/evidence/TV_LLM_OFFICE_EDITING_PHASE1B_1C_1D/responses_ledger.json — two sanitized attempted requests and their results.

The three synthetic input files and their manifests were already present as prepared evidence and were preserved. No Odoo business record was queried or changed by the test runner; only configured llm.model / llm.provider metadata was read to select the client. No provider setting was changed. Odoo remained running on port 8091; no module upgrade, Git stage, commit, push, reset, or clean was run.

## 7. Findings and Stop Decision

1. **Phase 1A-2 prior capability evidence remains valid for its scope:** the earlier separate run obtained and independently read back a simple XLSX edit. This round does not replace that evidence.
2. **Phase 1B–1D remain unverified:** repeated connection errors prevented any Response or candidate artifact from being observed. No conclusion about model edit correctness, multi-turn continuity, or workbook fidelity is supported.
3. **Current API Project identity and request billing remain unverified.** The local Provider credential was configured, but successful project access cannot be inferred from a failed connection.
4. **Remote cleanup is unverified:** no Response/container IDs were returned, so no remote resources were addressable for deletion.
5. **Stop condition reached:** no further Provider requests or dependent phase tests were made. Re-run requires resolving the network/API connection path and setting a request plan whose conservative reserve, including a retry contingency, remains under $2.00. Exact billing/cap compliance from this run is UNVERIFIED. This report does not authorize Candidate C, Odoo integration, or later TV phases.
