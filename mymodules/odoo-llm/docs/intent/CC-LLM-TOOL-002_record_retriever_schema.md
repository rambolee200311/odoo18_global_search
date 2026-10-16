# CC-LLM-TOOL-002: Record Retriever Tool Schema Contract

> Document version: v0.3 Draft
> Status: Draft — not frozen; implementation is not authorized
> Intent ID: `CC-LLM-TOOL-002`
> Module: `llm_tool` (with the OpenAI tool formatter as a consumer)
> Draft date: 2026-10-16
> Related contract: `CC-OPENAI-001` v1.0.0 Frozen
> Code baseline reviewed: `mymodules/odoo-llm`, commit `55a930fbb234f9b82c4a9a3f6292b8f081ac956a`

## 0. Governance

This is a draft scope proposal for the separate `odoo_record_retriever` argument-schema defect. It is not a frozen implementation contract and does not authorize code changes, module upgrades, real-provider calls, or database operations.

The project workflow requires a frozen technical design before a CC can be frozen or implemented. No dedicated frozen TDD for this issue was found. A TDD must define the selected schema-generation and failure-handling design before this CC can pass review.

## 1. Change Summary

| Field | Value |
|---|---|
| Intent ID | `CC-LLM-TOOL-002` |
| Work type | Bug investigation and fix |
| Goal | Diagnose the earlier empty-arguments tool failure across schema generation, Provider argument generation, and Odoo runtime validation; implement a fix only if diagnosis confirms an in-scope defect. |
| Relationship to `CC-OPENAI-001` | This CC concerns the retriever schema / runtime-argument chain. `CC-OPENAI-001` concerns OpenAI Provider request compatibility (`reasoning_effort`). They are separately scoped and may be diagnosed in parallel; this CC's production implementation is gated on `CC-OPENAI-001` CC-TEST-011 passing or receiving an authorized disposition. |
| Triggering evidence | An earlier Odoo chat flow sent `{}` and `llm.tool.execute()` rejected it because required `model` was absent; no records were read in that run. A later user-provided screenshot shows successful `odoo_record_retriever` execution and three purchase-order results with links and summaries. The failure run's exact code baseline and persisted tool-schema state were not recorded, so the two observations cannot yet be treated as same-runtime reproduction evidence. See §2.3, `ATR-CC-OPENAI-001.md` §§8.3–8.5, `IHR-CC-OPENAI-001.md` IHR-004 / IHR-005, and `HVR-CC-OPENAI-001.md` HVR-RUN-001. |

## 2. Baselines and Traceability

### 2.1 SRS / DDD

N/A. This is a tool-contract compatibility bug fix; it does not define a new business process or domain model.

### 2.2 Technical design

**Required before freezing this CC.** The repository has `llm_tool/OPENAI_SCHEMA_COMPATIBILITY.md`, which is technical guidance, not a frozen TDD. The TDD must, at minimum, define:

- The diagnostic procedure for capturing the generated schema, Provider request `tools` schema, Provider tool-call argument shape, and arguments received by `execute()`.
- Root-cause criteria distinguishing schema-generation defects, Provider argument-generation behavior, and Odoo runtime-validation defects.
- The repair or no-production-change disposition for each diagnostic outcome.
- Fail-closed behavior when schema generation or conversion fails, including whether Provider request construction stops.

### 2.3 Source observations

- `llm_tool/models/llm_tool_record_retriever.py` defines `odoo_record_retriever_execute(model, domain=[], fields=[], limit=100)`. `model` is required; the other parameters have defaults.
- `llm_tool/models/llm_tool.py:get_input_schema()` prefers stored `input_schema`; otherwise it calls MCP SDK `func_metadata()` on the implementation method.
- The XML definition in `llm_tool/data/llm_tool_data.xml` does not supply a stored `input_schema` for `odoo_record_retriever`.
- `llm_openai/models/openai_provider.py:_openai_format_tool()` catches schema-formatting errors and can fall back to a tool schema with empty properties and no required fields. That behavior can conceal a schema-generation failure from the model.
- `llm_tool/models/llm_tool.py:execute()` independently builds a Pydantic model from the method signature and validates the returned arguments. This is why an empty argument object is rejected at execution even if the provider was shown an empty fallback schema.

These code paths make a schema contract defect plausible, but the recorded browser evidence does not include the exact function schema sent to the Provider. Diagnosis must cover three links in the chain: (1) schema generation and conversion, (2) Provider-produced tool arguments, and (3) the arguments and validation result at Odoo `execute()`. A valid schema followed by `{}` from the Provider points to a different cause than valid Provider arguments rejected by Odoo.

#### Recorded run comparison

| Observation | Earlier failure — IHR-004 | Later success — HVR-RUN-001 | Comparison status |
|---|---|---|---|
| Time | 2026-10-16 approximately 15:20 Asia/Shanghai | 2026-10-16 approximately 15:30 Asia/Shanghai | Recorded |
| Model / Provider | OpenAI `gpt-5.6-luna` | OpenAI `gpt-5.6-luna` | Same as recorded |
| Odoo instance / database | In-app Odoo chat; ambient URL was `127.0.0.1:8091`; database not recorded in IHR-004 | Local Odoo at `127.0.0.1:8091`; `odoo18ce` | Instance URL aligns; database is not comparable from the failure record |
| Code baseline | Not recorded for this UI run | `55a930fbb234f9b82c4a9a3f6292b8f081ac956a` recorded | Not comparable; collect in TDD diagnostic |
| Tool state | `odoo_record_retriever` enabled in the chat; stored `llm.tool.input_schema` value not captured | Tool call completed; stored `llm.tool.input_schema` value not captured | Not comparable; collect read-only schema snapshot |
| Model parameters | `reasoning_effort="none"` was set for the failure verification | Exact persisted value at this run was not captured in the screenshot | Not comparable; collect model configuration state |
| Outcome | Provider requested the tool with `{}`; Odoo validation reported required `model` missing; no records read | Tool execution succeeded and returned three purchase-order results | Different outcome; root cause remains undetermined |

The successful run does not establish that the failure was unreproducible under identical code and runtime configuration: the failure run's code baseline, stored schema, and success-run model-parameter snapshot are missing. The initial TDD diagnostic must collect those differences before assigning cause. If no in-scope defect is confirmed, this CC may close with the diagnostic report and a separate issue or no production change; it must not force a code fix.

## 3. Scope Proposal

### 3.1 In scope

- Diagnose schema generation for the built-in `odoo_record_retriever` against the installed supported `mcp` / Pydantic versions.
- Capture a redacted comparison of: schema returned by `get_input_schema()`, Provider request `tools` entry, Provider tool-call function name and argument structure, and the parameter shape/type validation result at `execute()`. Record the comparison and root-cause classification in ATR; omit credentials, prompts, sensitive argument values, and returned records.
- Ensure the provider-visible function schema represents the runtime callable: required `model`; optional `domain`, `fields`, and `limit` with documented types and defaults.
- Ensure schema-generation or conversion errors are visible and stop an invalid tool request from being sent with an empty fallback schema.
- Ensure the schema advertised to the model and the parameters accepted by `llm.tool.execute()` have a tested, explicit relationship.
- Add automated tests for schema generation, OpenAI schema conversion, and argument validation, plus a controlled end-to-end tool call using the existing Odoo development environment when approved.
- Preserve Odoo's current-user environment and access checks; this contract does not grant broader model access.

### 3.2 Out of scope

- Changing `llm_openai` reasoning-effort handling already covered by `CC-OPENAI-001`.
- Building the `wd_global_search_llm` bridge, natural-language search planning, navigation links, or search-result cards.
- Changing permissions, record rules, `sudo()` behavior, or the retriever's generic model access policy.
- Modifying creator, updater, unlinker, or model-method-executor tools.
- Claiming that the retriever returns safe navigation URLs; it currently returns record data.
- Migrating the chat stack to a different Provider API or changing unrelated tool schemas.

## 4. Proposed Change Boundaries

The exact file allowlist remains subject to the required TDD. Candidate methods / records for review are:

| Candidate path and method / record | Limited purpose |
|---|---|
| `llm_tool/models/llm_tool.py:get_input_schema()` | Load or generate a tool schema |
| `llm_tool/models/llm_tool.py:execute()` and `get_pydantic_model_from_signature()` | Validate arguments against the implementation signature and dispatch only validated values |
| `llm_tool/models/llm_tool_record_retriever.py:odoo_record_retriever_execute()` | Define the retriever signature, types, defaults, and parameter descriptions |
| `llm_openai/models/openai_provider.py:_openai_format_tool()` | Provider schema conversion and fail-closed handling, only if the TDD assigns this responsibility here |
| `llm_tool/data/llm_tool_data.xml:<llm.tool record for odoo_record_retriever>` | Stored schema / metadata for this one built-in tool, only if selected by TDD |
| `llm_tool/tests/test_llm_tool_schema.py` and, if needed, an exact test module under `llm_openai/tests/` | Regression tests for approved methods and schema contract |

Do not modify these candidate methods or records until the TDD and this CC are reviewed and frozen. These candidates do not authorize whole-file changes. The frozen CC must name exact methods or data records and tests; no entire-file allowlist is permitted.

## 5. Required Behavior (Draft)

| ID | Current behavior / evidence | Proposed expected behavior |
|---|---|---|
| CC-CHANGE-001a — Diagnosis | The earlier run failed on `{}` while a later run succeeded; exact wire schema and runtime inputs were not captured. | Capture and compare the generated schema, Provider request schema, Provider arguments, and `execute()` input / validation result; record differences and root-cause classification in ATR. This diagnostic has no implied production-code change. |
| CC-CHANGE-001b — Conditional repair | Source paths permit schema fallback and independently generate runtime validation, but the cause is not yet confirmed. | If and only if diagnosis confirms an in-scope schema-generation, schema-conversion, or schema/runtime mismatch, implement the TDD-selected repair and fail-closed behavior. If no in-scope defect is confirmed, make no production-code change; close this CC with the diagnostic report and record any separate defect independently. |
| CC-CHANGE-002 — Schema/runtime parity | Runtime validation is generated separately from the schema sent to the Provider. | Tests establish parity: required fields match required callable parameters; schema types and nullability accept the supported JSON argument types; omission/default behavior matches the callable; and field descriptions do not contradict execution behavior. |
| CC-CHANGE-003 — Controlled errors | The recorded chat execution failure is visible as a lower-level Pydantic validation error. | Confirmed schema or argument failures use the existing controlled tool-error path without exposing a traceback, filesystem path, credentials, or record contents. Exact user-facing text is specified by the TDD. |

## 6. Preservation Requirements (Draft)

| ID | Behavior to preserve |
|---|---|
| CC-PRESERVE-001 | Odoo record access continues to use the calling user's environment and existing ACL / record-rule behavior. |
| CC-PRESERVE-002 | Tool execution remains read-only for `odoo_record_retriever`; this CC adds no writes or approval actions. |
| CC-PRESERVE-003 | Existing valid schemas for unrelated tools remain unchanged. Before implementation, capture a read-only snapshot of existing `llm.tool` names and `input_schema` values through `odoo-bin shell -c odoo.conf`; after implementation, compare the snapshot and confirm unrelated schemas did not change. Record the comparison in ATR. |
| CC-PRESERVE-004 | The fix does not make a missing `model` argument silently default to a different model. |

## 7. Test Contract Proposal

These are proposed tests only; they have not been run.

| Test ID | Scenario | Expected result |
|---|---|---|
| CC-TEST-001 | Generate the retriever schema with the supported runtime dependencies. | `model` is a required string; each field's type/nullability, omission/default behavior, and description are compatible with the callable signature. |
| CC-TEST-002 | Convert that schema into the OpenAI function definition. | Required fields and supported properties, types, omission/default behavior, and non-contradictory descriptions survive conversion; conversion does not silently emit an empty schema. |
| CC-TEST-003 | For a tool without stored `input_schema`, monkey-patch `mcp.server.fastmcp.utilities.func_metadata.func_metadata` to raise when `get_input_schema()` calls it. | Schema generation follows the TDD-defined controlled failure path; the Provider HTTP client is not called and no empty fallback schema is sent. |
| CC-TEST-004 | Execute with `{}` or without `model`. | Validation fails before any Odoo search call; the chat tool path returns a controlled error. |
| CC-TEST-005 | Execute with valid `model`, `domain`, `fields`, and `limit` values. | Arguments validate and are forwarded without semantic changes; access remains under the current user. |
| CC-TEST-006 | Regression for unrelated tools and Provider schema formatting. | Existing schemas and function-call behavior remain intact. |
| CC-TEST-007 | Browser end-to-end call to retrieve a small, authorized record set. | Provider emits arguments including the requested model; Odoo reads only records authorized for the current user and the assistant returns actual data. Link construction and rendering are outside this CC; this test validates tool calling, execution, and returned data only. The owning chat/navigation or bridge contract must verify links. |
| CC-TEST-008 | Compare the pre-change and post-change snapshot of existing `llm.tool.input_schema` values. | Snapshot is captured read-only through the approved Odoo shell workflow; only the explicitly approved retriever schema may differ. |

## 8. Security and Data Boundaries

- No `sudo()` or caller-supplied UID may be introduced to make the retriever work.
- Missing or invalid arguments must stop before record search.
- Do not log API keys, full prompts, complete tool arguments, or returned business records in evidence attachments.
- The ATR diagnostic comparison may include schema structure, argument field names, types, and validation outcome, but must redact business values and must not persist full Provider payloads or returned records.
- E2E validation must use the existing development database and current user unless a later, explicit authorization specifies otherwise; do not create an isolated database.

## 9. Stop Conditions

Stop and revise the TDD / CC if implementation would require changing Odoo permissions, introducing a new public tool API, changing all tools' schemas, modifying bridge/search behavior, or replacing the provider protocol. Stop if the captured Provider schema differs from the source-derived schema in a way not covered by the approved design. If the schema is valid and the Provider returns arguments conforming to it, but Odoo rejects those arguments for a runtime-validation defect beyond the specific schema/runtime parity contract in §5, stop and re-scope before implementation. More generally, if diagnosis identifies a cause or repair outside the approved scope, revise the root-cause model and frozen TDD / CC instead of forcing the proposed fix.

## 10. Draft Readiness

- [x] Source code and observed runtime validation error reviewed.
- [ ] Diagnostic comparison report produced: generated schema, Provider request schema, Provider argument shape, and `execute()` input / validation result, with root-cause classification.
- [ ] Dedicated TDD created, reviewed, and frozen.
- [ ] Final file allowlist and failure semantics approved.
- [ ] This CC reviewed and explicitly frozen.
- [ ] Implementation authorization recorded.

Diagnostic work may proceed in parallel with `CC-OPENAI-001`; production implementation under this CC must wait until `CC-OPENAI-001` CC-TEST-011 passes or an authorized disposition is recorded. This sequencing isolates the Provider compatibility change before modifying the tool-schema path.

This document is a draft only. No item above is implied complete beyond the checked source review.

## Appendix A — Version History

| Version | Date | Change | Status |
|---|---|---|---|
| v0.1 | 2026-10-16 | Initial draft separating the retriever schema / runtime-argument issue from the OpenAI `reasoning_effort` fix. | Draft |
| v0.2 | 2026-10-16 | Incorporated the later successful user-provided E2E screenshot; changed the draft to require reproduction and schema capture before selecting a fix. | Draft |
| v0.3 | 2026-10-16 | Added a failure/success comparison with unknowns marked for TDD collection; defined the three-link diagnostic, conditional repair/no-change outcome, ATR artifacts, method-level file boundaries, parity criteria, schema snapshot, concrete metadata-failure test, link ownership, stop condition, and sequencing with CC-OPENAI-001. | Draft |
