# IHR — CC-OPENAI-001

## 0. Document Governance

This record captures implementation facts for CC-OPENAI-001. It does not redefine the frozen contract or declare the contract closed.

## 1. Execution Metadata

| Field | Value |
|---|---|
| Intent ID | CC-OPENAI-001 |
| CC | CC-OPENAI-001_tool_call_reasoning_effort.md, v1.0.0 Frozen |
| Module | llm_openai |
| Work type | Provider compatibility bug fix |
| Implementer | Codex |
| Date | 2026-10-16 |
| Base commit | 609ec6dda3645165f6a4a843d7af5d286081a29d |
| Current implementation state | Implementation Complete; CC verification remains open |

## 2. Coding Contract Baseline

Scope, change boundaries, preservation requirements, test contract, and stop conditions are governed by CC-OPENAI-001 v1.0.0 Frozen, §§3–13. Applicable change IDs: CC-CHANGE-001–CC-CHANGE-004. Applicable preservation IDs: CC-PRESERVE-001–CC-PRESERVE-006.

## 3. Current Implementation Snapshot

| Item | State |
|---|---|
| CC-CHANGE implementation | 4 / 4 implemented |
| Preservation impact | Potential impact; automated evidence in ATR |
| Deviation | None |
| CC §12 stop condition triggered | No; the authorized outgoing-payload diagnostic found no reasoning_effort field in the captured request |
| Open issues | Strict CC-TEST-011 procedure and CC-TEST-012 alternate-endpoint regression remain open; see §7 |
| Current state | Implementation complete; later integrated tool execution passed in HVR-RUN-001; FR closure assessment remains separate |

## 4. Implementation History Entries

### IHR-001

| Field | Value |
|---|---|
| Time | 2026-10-16 |
| Stage | Implementation / diagnostic gate |
| Action | Sent one authorized request through the configured OpenAI Provider and captured only redacted transport metadata. The captured request was POST https://api.openai.com/v1/chat/completions, model gpt-5.6-luna, tool odoo_record_retriever; payload keys were messages, model, stream, tool_choice, tools, with no reasoning_effort. The request timed out before a Provider response was received. |
| Reason | Close the CC §12 outgoing-payload provenance gate before implementation. |
| Files / Components | Current Odoo runtime, OpenAI SDK transport |
| Contract Reference | CC §2.4, §12; CC-TEST-011 is not satisfied by this diagnostic request |
| Result | Payload capture completed; response acceptance not verified |
| Deviation | None |
| Follow-up | Keep CC-TEST-011 open; do not retry the external request without renewed authorization. |

### IHR-002

| Field | Value |
|---|---|
| Time | 2026-10-16 |
| Stage | Implementation |
| Action | Added strict parsing and save-time validation for the OpenAI namespace; added request-time validation and allow-listed reasoning_effort="none" injection; added model form help and README configuration guidance. |
| Reason | Implement CC-CHANGE-001–003 while preserving unconfigured requests and provider-owned request fields. |
| Files / Components | llm_openai/models/openai_provider.py, llm_openai/models/llm_model.py, llm_openai/models/__init__.py, llm_openai/views/llm_model_views.xml, llm_openai/__manifest__.py, llm_openai/README.md |
| Contract Reference | CC-CHANGE-001–003; CC-PRESERVE-001–005 |
| Upstream Reference | Frozen technical scheme §4.1–§5 |
| Result | Completed |
| Deviation | None; module version remains unchanged as required by the frozen CC |
| Follow-up | None for implementation |

### IHR-003

| Field | Value |
|---|---|
| Time | 2026-10-16 |
| Stage | Implementation / verification |
| Action | Added the llm_openai automated test package and 10 test methods covering configuration validation, request construction, provider isolation, request-field preservation, streaming/tool combinations, and no-call behavior for invalid runtime configuration. |
| Reason | Implement CC-CHANGE-004 and provide evidence for CC-TEST-001–010. |
| Files / Components | llm_openai/tests/__init__.py, llm_openai/tests/test_openai_reasoning_effort.py |
| Contract Reference | CC-CHANGE-004; CC-TEST-001–010 |
| Result | Completed; latest run evidence is in ATR-CC-OPENAI-001 §5 |
| Deviation | None |
| Follow-up | None for the automated test implementation |

### IHR-004

| Field | Value |
|---|---|
| Time | 2026-10-16 15:20 Asia/Shanghai |
| Stage | Browser UI verification |
| Action | In the Codex in-app Odoo UI, set the active OpenAI `gpt-5.6-luna` model parameters to `{"openai":{"reasoning_effort":"none"}}` and sent the approved tool-call verification query with `odoo_record_retriever` enabled. The Provider returned a tool call without the earlier `reasoning_effort` error. Odoo then rejected the tool arguments because required `model` was missing from `{}`; no sales records were read. |
| Reason | Verify the implemented Provider compatibility fix on the real chat path and identify the remaining tool execution boundary. |
| Files / Components | Odoo in-app chat; `llm_openai` Provider; `llm_tool` execution path |
| Contract Reference | CC-TEST-011 diagnostic evidence; CC-TEST-013 |
| Result | Provider tool-call behavior observed; strict CC-TEST-011 remains not run because the UI did not stop before the tool loop and the raw HTTP response was not captured. CC-TEST-013 is blocked by the separate tool schema validation issue. |
| Deviation | This was a full UI flow, not the Provider-only harness prescribed by CC-TEST-011. |
| Follow-up | Keep CC verification open; treat `llm_tool` schema repair as a separate contract. |

### IHR-005

| Field | Value |
|---|---|
| Time | 2026-10-16 approximately 15:30 Asia/Shanghai (as shown in user-provided screenshot) |
| Stage | Human end-to-end verification evidence update |
| Action | The user supplied a screenshot of a later Odoo chat run using the OpenAI `gpt-5.6-luna` model. `odoo_record_retriever` completed successfully, and the assistant returned three purchase-order entries with links and summaries. No record identifiers, suppliers, amounts, credentials, or full payload were transcribed. |
| Reason | Update the current verification snapshot after the earlier IHR-004 run failed argument validation. |
| Files / Components | Odoo chat; OpenAI Provider; `odoo_record_retriever` |
| Contract Reference | CC-TEST-013; supporting integrated-flow evidence for CC-TEST-011; CC-PRESERVE-005 |
| Result | Latest integrated tool scenario PASS; earlier empty-arguments failure retained as historical evidence. HVR-RUN-001 is the evidence record. |
| Deviation | The user performed the complete UI flow rather than stopping before the tool loop; the raw Provider response was not captured. |
| Follow-up | Keep CC-TEST-011 strict procedure and CC-TEST-012 statuses distinct in ATR / FR. |

## 5. Actual Change Inventory

| File | Action | Change | CC source |
|---|---|---|---|
| llm_openai/models/openai_provider.py | Modified | Add validated model options to existing Chat Completions request | CC-CHANGE-001 |
| llm_openai/models/llm_model.py | Added | Validate OpenAI model parameters at save and request time | CC-CHANGE-002 |
| llm_openai/models/__init__.py | Modified | Register model extension | CC-CHANGE-002 |
| llm_openai/views/llm_model_views.xml | Added | Explain the supported JSON setting on the model form | CC-CHANGE-003 |
| llm_openai/__manifest__.py | Modified | Load the inherited model view | CC-CHANGE-003 |
| llm_openai/README.md | Modified | Document the namespace and supported value | CC-CHANGE-003 |
| llm_openai/tests/__init__.py | Added | Register tests | CC-CHANGE-004 |
| llm_openai/tests/test_openai_reasoning_effort.py | Added | Automated configuration and request tests | CC-CHANGE-004 |
| docs/intent/IHR-CC-OPENAI-001.md | Added | Implementation history | Workflow record |
| docs/intent/ATR-CC-OPENAI-001.md | Added | Test evidence record | Workflow record |
| docs/intent/evidence/ATR-CC-OPENAI-001-RUN-003.log | Added | Odoo test-run log | Workflow evidence |

## 6. Deviation / Stop Condition Record

Deviation: None. No CC §12 stop condition required stopping implementation after the authorized payload capture. The captured request contained no reasoning_effort; the Provider response timed out, so this is diagnostic evidence only and does not satisfy the configured-model acceptance test.

## 7. Open Issues / Follow-up

| ID | Issue | Category | Severity | Status | Owner |
|---|---|---|---|---|---|
| OI-001 | Strict CC-TEST-011 still requires a Provider-only response capture that stops before the tool loop. HVR-RUN-001 confirms the successful integrated flow, but does not capture the raw response or follow the isolated procedure. | External integration | Major | Open | User / Provider environment |
| OI-002 | No alternate model or OpenAI-compatible endpoint was exercised for CC-TEST-012. | External integration | Minor | Open | User / Provider environment |
| OI-003 | The first CC-TEST-013 run failed because required `model` was missing from `{}`. The later HVR-RUN-001 completed the integrated retrieval successfully; the original failure remains relevant to the separate schema investigation. | Dependency / E2E | Major | Resolved for latest E2E; historical failure retained | llm_tool maintenance |
| OI-004 | Odoo runtime logs contain pre-existing errors for unavailable custom addons and an unconditional import of wd_global_search.tests in normal server mode. These are outside the CC file boundary; the server nevertheless starts and listens on 8091. | Environment | Minor | Open | Project owner |

## 8. Handoff to ATR / HVR / FR

Implemented: CC-CHANGE-001–004. Actual files: see §5. Open issues: OI-001, OI-002, OI-004. Deviation: the successful full UI flow did not follow the Provider-only CC-TEST-011 procedure; see IHR-005 and HVR-RUN-001. Automated test evidence: ATR-CC-OPENAI-001. The latest Odoo tool retrieval returned three purchase-order results with links and summaries; the first empty-arguments failure remains in IHR-004 / ATR history.

This IHR records implementation facts only. FR / Human Review must decide contract closure and any merge or release action.
