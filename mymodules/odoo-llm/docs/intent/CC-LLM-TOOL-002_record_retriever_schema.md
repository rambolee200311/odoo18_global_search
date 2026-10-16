# CC-LLM-TOOL-002: Record Retriever Tool Schema Contract

> Document version: v0.2 Draft
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
| Goal | Investigate the earlier empty-arguments tool failure and fix the confirmed cause only. Verify that the schema exposed to the model matches runtime validation, and prevent a confirmed schema-generation failure from silently degrading to an empty object schema. |
| Triggering evidence | An earlier Odoo chat flow sent `{}` and `llm.tool.execute()` rejected it because required `model` was absent; no records were read in that run. A later user-provided screenshot on the same code baseline shows successful `odoo_record_retriever` execution and three purchase-order results with links and summaries. See `ATR-CC-OPENAI-001.md` §§8.3–8.5, `IHR-CC-OPENAI-001.md` IHR-004 / IHR-005, and `HVR-CC-OPENAI-001.md` HVR-RUN-001. |

## 2. Baselines and Traceability

### 2.1 SRS / DDD

N/A. This is a tool-contract compatibility bug fix; it does not define a new business process or domain model.

### 2.2 Technical design

**Required before freezing this CC.** The repository has `llm_tool/OPENAI_SCHEMA_COMPATIBILITY.md`, which is technical guidance, not a frozen TDD. The design must resolve schema generation, provider conversion, and fail-closed behavior without assuming the model's empty arguments alone prove the root cause.

### 2.3 Source observations

- `llm_tool/models/llm_tool_record_retriever.py` defines `odoo_record_retriever_execute(model, domain=[], fields=[], limit=100)`. `model` is required; the other parameters have defaults.
- `llm_tool/models/llm_tool.py:get_input_schema()` prefers stored `input_schema`; otherwise it calls MCP SDK `func_metadata()` on the implementation method.
- The XML definition in `llm_tool/data/llm_tool_data.xml` does not supply a stored `input_schema` for `odoo_record_retriever`.
- `llm_openai/models/openai_provider.py:_openai_format_tool()` catches schema-formatting errors and can fall back to a tool schema with empty properties and no required fields. That behavior can conceal a schema-generation failure from the model.
- `llm_tool/models/llm_tool.py:execute()` independently builds a Pydantic model from the method signature and validates the returned arguments. This is why an empty argument object is rejected at execution even if the provider was shown an empty fallback schema.

These code paths make a schema contract defect plausible, but the recorded browser evidence does not include the exact function schema sent to the Provider. The implementation investigation must capture and compare the generated schema, provider payload schema, tool-call arguments, and runtime signature before claiming a single root cause.

The later successful run shows that the empty-argument failure is not consistently reproducible on the reviewed baseline. The TDD and final CC must treat reproduction and schema capture as an initial diagnostic gate; if the schema is valid and the Provider emitted `{}` despite it, the fix may be different or no production change may be justified.

## 3. Scope Proposal

### 3.1 In scope

- Diagnose schema generation for the built-in `odoo_record_retriever` against the installed supported `mcp` / Pydantic versions.
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

The exact file allowlist remains subject to the required TDD. Candidate files for review are:

| Candidate path | Purpose |
|---|---|
| `llm_tool/models/llm_tool.py` | Schema generation and runtime validation contract |
| `llm_tool/models/llm_tool_record_retriever.py` | Retriever argument signature and descriptions |
| `llm_openai/models/openai_provider.py` | Provider schema conversion and fail-closed handling, only if the TDD assigns this responsibility here |
| `llm_tool/data/llm_tool_data.xml` | Explicit schema or description for the built-in retriever, only if selected by the TDD |
| `llm_tool/tests/` and, if needed, `llm_openai/tests/` | Automated regression tests |

Do not modify these candidate files until the TDD and this CC are reviewed and frozen. Any final CC must narrow this list to the approved implementation.

## 5. Required Behavior (Draft)

| ID | Current behavior / evidence | Proposed expected behavior |
|---|---|---|
| CC-CHANGE-001 | Tool schema generation may rely on MCP SDK metadata; the OpenAI formatter can replace an error with an empty schema, but the earlier failure was not reproduced in the later successful run. | First reproduce and inspect the generated and transmitted schema. If schema mismatch or silent fallback is confirmed, the model receives a schema that accurately declares `model` as required and the supported optional arguments, or request construction stops with a controlled diagnostic before contacting the Provider. |
| CC-CHANGE-002 | Runtime argument validation is generated separately from the schema sent to the Provider. | Automated tests demonstrate schema/runtime parity for `odoo_record_retriever`; invalid or missing required arguments do not invoke `search()` / `search_read()`. |
| CC-CHANGE-003 | The recorded chat execution failure is visible as a lower-level Pydantic validation error. | Tool failure is returned through the existing chat tool-error path without exposing a traceback, filesystem path, credentials, or record contents. Exact user-facing text is to be specified by the TDD. |

## 6. Preservation Requirements (Draft)

| ID | Behavior to preserve |
|---|---|
| CC-PRESERVE-001 | Odoo record access continues to use the calling user's environment and existing ACL / record-rule behavior. |
| CC-PRESERVE-002 | Tool execution remains read-only for `odoo_record_retriever`; this CC adds no writes or approval actions. |
| CC-PRESERVE-003 | Existing valid schemas for unrelated tools remain unchanged. |
| CC-PRESERVE-004 | The fix does not make a missing `model` argument silently default to a different model. |

## 7. Test Contract Proposal

These are proposed tests only; they have not been run.

| Test ID | Scenario | Expected result |
|---|---|---|
| CC-TEST-001 | Generate the retriever schema with the supported runtime dependencies. | `model` is a required string; `domain`, `fields`, and `limit` are represented with types compatible with the callable. |
| CC-TEST-002 | Convert that schema into the OpenAI function definition. | Required fields and supported properties survive conversion; conversion does not silently emit an empty schema. |
| CC-TEST-003 | Force MCP metadata/schema generation to fail. | Provider request construction fails before external HTTP; a safe diagnostic is logged / returned. |
| CC-TEST-004 | Execute with `{}` or without `model`. | Validation fails before any Odoo search call; the chat tool path returns a controlled error. |
| CC-TEST-005 | Execute with valid `model`, `domain`, `fields`, and `limit` values. | Arguments validate and are forwarded without semantic changes; access remains under the current user. |
| CC-TEST-006 | Regression for unrelated tools and Provider schema formatting. | Existing schemas and function-call behavior remain intact. |
| CC-TEST-007 | Browser end-to-end call to retrieve a small, authorized sales-order result set. | Provider emits non-empty arguments including `model="sale.order"`; Odoo reads only records authorized for the current user and the assistant returns actual data. No record links are required by this CC. |

## 8. Security and Data Boundaries

- No `sudo()` or caller-supplied UID may be introduced to make the retriever work.
- Missing or invalid arguments must stop before record search.
- Do not log API keys, full prompts, complete tool arguments, or returned business records in evidence attachments.
- E2E validation must use the existing development database and current user unless a later, explicit authorization specifies otherwise; do not create an isolated database.

## 9. Stop Conditions

Stop and revise the TDD / CC if implementation would require changing Odoo permissions, introducing a new public tool API, changing all tools' schemas, modifying bridge/search behavior, or replacing the provider protocol. Stop if the captured provider schema differs from the source-derived schema in a way not covered by the approved design.

## 10. Draft Readiness

- [x] Source code and observed runtime validation error reviewed.
- [ ] Dedicated TDD created, reviewed, and frozen.
- [ ] Final file allowlist and failure semantics approved.
- [ ] This CC reviewed and explicitly frozen.
- [ ] Implementation authorization recorded.

This document is a draft only. No item above is implied complete beyond the checked source review.

## Appendix A — Version History

| Version | Date | Change | Status |
|---|---|---|---|
| v0.1 | 2026-10-16 | Initial draft separating the retriever schema / runtime-argument issue from the OpenAI `reasoning_effort` fix. | Draft |
| v0.2 | 2026-10-16 | Incorporated the later successful user-provided E2E screenshot; changed the draft to require reproduction and schema capture before selecting a fix. | Draft |
