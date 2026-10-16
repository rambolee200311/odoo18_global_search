# Human Verification Record — CC-OPENAI-001

## 0. Document Governance

This record captures the user-provided successful Odoo chat verification and preserves the distinction between the full user flow and the Provider-only procedure specified in CC-TEST-011.

## 1. Verification Metadata

| Field | Value |
|---|---|
| Intent ID | CC-OPENAI-001 |
| CC Version | v1.0.0 Frozen |
| IHR Reference | IHR-CC-OPENAI-001.md; IHR-005 |
| ATR Reference | ATR-CC-OPENAI-001.md |
| Module | `llm_openai`, `llm_tool` |
| Environment | Local Odoo development instance at `127.0.0.1:8091`, existing `odoo18ce` database; Codex in-app browser |
| Environment Type | Normal development |
| Application Version | Odoo 18.0; OpenAI model `gpt-5.6-luna` |
| Initial Code Baseline / Commit | `55a930fbb234f9b82c4a9a3f6292b8f081ac956a` |
| Database / Dataset | `odoo18ce`; existing development purchase-order data |
| Browser / Device | Codex in-app browser |
| Verification Start | 2026-10-16, approximately 15:30 Asia/Shanghai (time displayed in the screenshot) |
| Verification End | 2026-10-16, approximately 15:30 Asia/Shanghai |

## 2. Human Verification Contract Baseline

| Source | ID | Relevance |
|---|---|---|
| CC Human Verification Requirement | CC-TEST-011 | Real configured Provider tool-call behavior; this run supplies integrated UI evidence, not the prescribed Provider-only capture. |
| CC Human Verification Requirement | CC-TEST-012 | Other model / compatible endpoint regression; not exercised in this run. |
| CC Human Verification Requirement | CC-TEST-013 | Actual Odoo tool execution and result; exercised successfully in this run. |
| CC-CHANGE | CC-CHANGE-001 | Explicit `reasoning_effort="none"` allows the configured model's tool call. |
| CC-PRESERVE | CC-PRESERVE-005 | Existing Chat Completions tool path continues to operate. |

## 3. Current Human Verification Status

| Field | Value |
|---|---|
| Human Verification Required | Yes |
| Required Scenarios | 3 |
| PASS | 1 |
| FAIL | 0 |
| BLOCKED | 0 |
| NOT RUN | 2 |
| Current Code Baseline | `55a930fbb234f9b82c4a9a3f6292b8f081ac956a` |
| Current Valid Evidence Set | HVR-RUN-001 |
| Evidence Baseline Status | Partial; the successful full-flow scenario is on the current implementation baseline. |

## 4. Human Verification Coverage Matrix

| Verification Requirement | Scenario | Upstream | Current Valid Evidence | Result | Baseline Validity |
|---|---|---|---|---|---|
| CC-TEST-013: actual Odoo tool execution | HVR-SCN-001 | CC-TEST-013 | HVR-RUN-001 / HVR-EVD-001 | PASS | Current |
| CC-TEST-011: prescribed Provider-only capture | HVR-SCN-002 | CC-TEST-011 | — | NOT RUN | No strict Provider-only capture in this run |
| CC-TEST-012: alternate model / endpoint regression | HVR-SCN-003 | CC-TEST-012 | — | NOT RUN | No alternate endpoint exercised |

## 5. Verification Scenarios

### HVR-SCN-001 — Natural-language Odoo retrieval returns records and navigation links

| Field | Value |
|---|---|
| Purpose | Confirm the real chat flow can invoke the configured Provider tool, execute `odoo_record_retriever`, and return actual records with links and summaries. |
| Upstream Reference | CC-TEST-013; supporting evidence for CC-TEST-011 and CC-PRESERVE-005 |
| Preconditions | Odoo chat is configured with OpenAI `gpt-5.6-luna`; `odoo_record_retriever` is enabled; existing user-accessible purchase-order data matches the query. |
| Role | Odoo user shown as “Mitchell Admin”; the current user supplied the screenshot and confirmed the manual verification passed. |
| Verification Steps | In the Odoo chat, request three purchase orders whose product names contain “lamp”, asking for links and summaries. Observe the tool call and assistant response. |
| Expected Behavior | Provider requests `odoo_record_retriever`; Odoo completes the read under the current user; the assistant presents three matching records with navigation links and summaries; no prior `reasoning_effort` error occurs. |
| Evidence Required | User-provided screenshot showing the completed tool card and assistant response. |

### HVR-SCN-002 — Provider-only response capture

This scenario preserves the specific CC-TEST-011 method: capture the raw Provider response and stop before the Odoo tool loop. The successful full-flow screenshot is supporting evidence for Provider behavior but does not satisfy this isolated capture procedure.

### HVR-SCN-003 — Alternate model / compatible endpoint regression

This scenario preserves CC-TEST-012. The screenshot uses the configured OpenAI `gpt-5.6-luna` model only and cannot verify an alternate model or endpoint.

## 6. Verification Run History (Append-only)

### HVR-RUN-001

| Field | Value |
|---|---|
| Run ID | HVR-RUN-001 |
| Timestamp | 2026-10-16, approximately 15:30 Asia/Shanghai |
| Human Verifier | Mitchell Admin (Odoo display identity shown in the evidence; verification confirmed by the current user) |
| Verification Type | Functional end-to-end |
| Run Code Baseline | `55a930fbb234f9b82c4a9a3f6292b8f081ac956a` |
| Environment | Odoo 18.0 local development instance, `odoo18ce`, Codex in-app browser |
| Scenarios | HVR-SCN-001 PASS; HVR-SCN-002 NOT RUN; HVR-SCN-003 NOT RUN |
| Execution Assistance | Codex in-app browser; screenshot supplied by the human verifier |
| Result Summary | PARTIAL: the actual user-facing retrieval scenario passed; the two separate regression procedures were not run. |
| Evidence | HVR-EVD-001 |
| Follow-up | ATR and FR updated to distinguish this successful run from the earlier failed run. |

**Scenario result — HVR-SCN-001**

- Expected behavior: a successful tool call returns three matching purchase orders, each with a link and summary.
- Actual observation: the screenshot shows a green successful `odoo_record_retriever` tool card and an assistant response containing three purchase-order entries with a navigation link and summary for each. No `reasoning_effort` error is visible. Record names, suppliers, and monetary values are intentionally omitted from this record.
- Result: PASS.
- Evidence: HVR-EVD-001.
- Finding: none for this scenario.

**Scenario result — HVR-SCN-002**

- Expected behavior: capture the raw Provider response and stop before tool execution, as specified by CC-TEST-011.
- Actual observation: the human performed a complete UI flow through tool execution; the screenshot does not show a raw HTTP response or status.
- Result: NOT RUN to the prescribed procedure.
- Evidence: HVR-EVD-001 is supporting integrated-flow evidence only.
- Finding: none; the isolated procedure remains open.

**Scenario result — HVR-SCN-003**

- Expected behavior: verify an alternate model / compatible endpoint as specified by CC-TEST-012.
- Actual observation: only `gpt-5.6-luna` is visible in this run.
- Result: NOT RUN.
- Evidence: none.
- Finding: none.

## 7. Human Regression Verification

| CC-PRESERVE | Scenario | Run | Result | Evidence |
|---|---|---|---|---|
| CC-PRESERVE-005 | HVR-SCN-001 | HVR-RUN-001 | PASS for the observed configured OpenAI chat flow | HVR-EVD-001 |

## 8. Findings / Issues

| ID | Scenario | Run | Finding | Severity | Status | Follow-up |
|---|---|---|---|---|---|---|
| HVR-FIND-001 | HVR-SCN-002 | HVR-RUN-001 | The full UI flow did not follow the Provider-only capture procedure. | Low | Open | Keep strict CC-TEST-011 status distinct from the successful integrated-flow evidence. |
| HVR-FIND-002 | HVR-SCN-003 | HVR-RUN-001 | No alternate model / endpoint was exercised. | Low | Open | Run CC-TEST-012 if required for closure. |

## 9. Evidence Inventory

| Evidence ID | Type | Scenario | Run | Location / Reference | Sensitive Data |
|---|---|---|---|---|---|
| HVR-EVD-001 | Screenshot | HVR-SCN-001 | HVR-RUN-001 | User-provided attachment `codex-clipboard-46321db9-67a2-4e24-8cfa-9e52306cf0f1.png` in the Codex conversation. Not copied into the repository because it displays business records and monetary values. | Yes; retained only as user-provided conversation evidence, details omitted here. |

## 10. Handoff to Final Report

- Required Scenarios: 3
- PASS: 1 / FAIL: 0 / BLOCKED: 0 / NOT RUN: 2
- Current Valid Evidence Set: HVR-RUN-001
- Evidence Baseline Status: Partial
- Open Findings: 2

## Appendix A — Version History

| Version | Date | Change | Status |
|---|---|---|---|
| v0.1 | 2026-10-16 | Recorded the successful user-provided integrated chat and retriever run; kept the separate Provider-only and alternate-endpoint procedures visible as NOT RUN. | Current |
