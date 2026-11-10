# IHR-M2-CB-01 — Responses Provider Adapter

**Status:** FINAL ACCEPTED — Contract Verified and authorized real Provider Adapter integration validated; no production activation
**Contract:** `docs/implementation/CC-M2-CB-01_Responses_Provider_Adapter_v0.2.md` — frozen under bounded authorization
**Date:** 2026-11-06

## 1. Authorization and Scope

**Initial implementation authorization (historical):** The project owner approved local Adapter implementation, SDK-mocked tests, synthetic XLSX fixtures, and local independent readback only. That original authorization did not allow a real Provider request or external file upload. A separate dated authorization is recorded in §7 below; it superseded that limitation only for a bounded synthetic real-Provider test. It did not amend SRS/TDD or authorize production activation, deployment, or Git staging/commit/push.

Implementation is restricted to the CC v0.2 allowlist: the isolated `llm_openai.services.responses_adapter` package, its unit tests, and this IHR/ATR. `openai_provider.py`, addon registration/manifest, Usage ORM, M2 business code, and frozen design/plan baselines are not in scope.

## 2. Start-of-Work Baseline

| Item | Observed before implementation |
|---|---|
| Repository | `/Users/lijianqiang/Documents/odoo18_global_search` |
| Branch / HEAD | `main` / `f9801fca76f7c248a9cc823c583138ab0191b978` |
| Git state | `main...origin/main [ahead 1]`; tracked diff was empty. Existing untracked work was present and preserved. |
| Existing untracked items | `.coverage`; docs A/A2/B audit/design drafts; TDD V2.0.0–2.0.2; Architecture Change Assessment v0.1/v0.2; CC Runtime v0.1; CB-01 v0.1/v0.2; continuity and Candidate B plans; prior TV reports and evidence directories. No pre-existing item was removed or overwritten. |
| Python | repository venv, Python 3.11.9 |
| OpenAI SDK | 2.54.0 at `venv/lib/python3.11/site-packages/openai` |
| pytest | 8.4.2 |
| Existing Provider path | `openai_provider.py`: `openai_get_client()` constructs a configured OpenAI SDK client; `openai_chat()` calls Chat Completions. No Responses Adapter existed. |
| SDK surface | Local introspection confirmed `responses.create`, `with_options(max_retries=...)`, streamed container-file retrieval, container deletion, and response deletion methods. No API call was made. |

The user-visible `git status --short --branch` at the start listed only pre-existing untracked items; all were retained. Python introspection attempted no client construction with credentials and made no network request.

## 3. Existing Evidence and Root Boundary

The prior Phase 1A-2 report records one real synthetic XLSX edit and independent readback, while Phase 1B–1D retains two historical pre-response `APIConnectionError` results. These are historical TV facts, not this implementation's test results.

The current addon imports `models` and `utils` from its root `__init__.py`; the proposed service can remain unregistered and independently importable under the normal Odoo addon namespace. A direct `import llm_openai` outside Odoo's addon namespace raises Odoo's expected addon-import assertion; therefore tests load the pure service source directly without booting Odoo. This avoids changing package registration or the existing Chat Completions path.

## 4. Implementation Log

- Frozen the existing v0.2 CC under the user's explicit bounded approval; preserved v0.1 and all upstream baselines.
- Added the isolated service package and `ResponsesAdapter`; no Odoo imports, ORM access, file-path access, code execution, Provider configuration read, or production caller was added.
- Added SDK-mocked tests and an in-memory synthetic workbook for independent openpyxl readback.
- `py_compile` passed for all three new Python files.
- The direct `pytest` invocation initially failed during Odoo Addon package setup because pytest imported the addon root outside Odoo's addon loader. The same tests were then run with a test-only module namespace shim that avoids importing the Odoo addon; all 25 tests passed. Details are in `ATR-M2-CB-01.md`.
- No Provider request, Odoo service/runtime/database operation, TransactionCase, module upgrade, Browser test, or production-data operation was performed. These remain outside the bounded authorization.

See `ATR-M2-CB-01.md` for exact commands, test level distinctions, scope review, and open integration evidence.

## 7. Separately Authorized Real Provider Integration Addendum — 2026-11-06

The project owner separately authorized up to 10 sequential Responses API creation attempts using only a synthetic workbook and the existing approved OpenAI Provider/model. One attempt was made; no retry or concurrent request occurred. No credentials were printed, serialized, or persisted.

### 7.1 Gate and execution evidence

- The existing configured OpenAI Provider was selected through read-only Odoo ORM. The active default model resolved uniquely to `gpt-5.6-luna`; the approved HTTPS endpoint was checked in memory. The SDK client was obtained through the existing `provider.client` factory. The API Key value was not emitted or stored.
- The real call was made through `ResponsesAdapter.execute()` using OpenAI SDK 2.54.0, `store=False`, `max_retries=0`, one sequential request, a 120-second timeout, 4,000 output-token limit, 2 MB input/output limits, a 1 GB hosted container, and disabled container networking.
- The synthetic XLSX was 5,563 bytes. The Provider returned a completed Response and one Code Interpreter call, a container-file citation, and downloadable XLSX bytes. Adapter result: `candidate_received`; container cleanup: `completed`.
- IDs: Response `resp_08d257b63d57f6c1016aed953b25b887d288a414dec2c8ed93`; request `req_2d5daa2765b44dc2bcd8e3f1207d3a55`; Code Interpreter `ci_08d257b63d57f6c1016aed954295f887d2a29c3f8e9a36db5e`; container `cntr_6aed953e1e908191908c4929d71f46830e6895d01718b496`; container file `cfile_6aed954637888191ac5bf1f739cee762`.

### 7.2 Independent file readback

The downloaded output is 5,567 bytes. Independent `openpyxl` readback and ZIP integrity checks passed:

- Input SHA-256: `756a1ffa467e24da035952cbbf63c5d1c0ad8d47bf53bf17a4b8e4613e95d82b`.
- Output SHA-256: `9b2a7c48928737a0a8ee7878770e7206bafbc394f2631a764e1b0ece55f8266f`.
- `Inventory!B2` is numeric `15`; `Inventory!C2` remains `KEEP`; `Inventory!D2` remains formula text `=B2*2`.
- Inventory row 3, the `Notes` sheet values, sheet names, populated cell types, number formats and styles remained unchanged. The independent diff found only `Inventory!B2` changed.
- Formula recalculation was not tested or claimed.

Evidence files are under `docs/verification/evidence/TV_LLM_OFFICE_EDITING_CB01/real_provider_20261106/`: runner, input XLSX, downloaded candidate, request ledger, sanitized Adapter result and independent readback report.

### 7.3 Usage, cost visibility and cleanup

Provider usage: 2,149 input tokens; 693 output tokens (331 reasoning tokens); 2,842 total tokens. Local estimated cost was USD 0.0337614 using the documented token/tool/container rates; this is an estimate, not an invoice or account-level hard-budget guarantee. Invoice cost is `UNVERIFIED`. One Responses creation attempt was used of the authorized ten; SDK automatic retries were disabled. `store=False` was sent, and hosted container deletion completed. No separate persistent Response/file deletion was attempted because the Response was not stored and the output was a container file removed with its container.

### 7.4 Chat Completions compatibility and local regression

Added three SDK-mocked compatibility checks in the allowlisted `test_responses_adapter.py`. They load the unchanged `openai_provider.py` methods with narrow Odoo import stubs and no registry/database, exercising non-streaming content/tool calls and legacy return shape, streaming content/tool calls, and the existing OpenAI client constructor's `api_key`/`api_base` argument contract using synthetic placeholders only. These are method-level unit/mock checks, not Odoo Provider ORM integration. `openai_provider.py` remains unchanged.

Latest local results: `py_compile` passed for the Adapter, test and evidence scripts; the isolated pytest command completed **28 passed**. The historical direct pytest addon-collection failure remains recorded in ATR and was not removed or rewritten.

The authorized real Provider Adapter integration criterion and Chat Completions method-level compatibility checks are evidenced. This does not constitute Odoo TransactionCase, production activation, Preview/Finalize/Attachment delivery, Browser E2E, or M2 stage-wide/production acceptance.

## 8. Owner Acceptance — 2026-11-06

The project owner explicitly approved closing CC-M2-CB-01 after reviewing the real Provider and independent XLSX evidence. The corresponding ATR records `Final Accepted`. Acceptance is limited to CC-M2-CB-01 and does not authorize production release or implementation of CB-02.
