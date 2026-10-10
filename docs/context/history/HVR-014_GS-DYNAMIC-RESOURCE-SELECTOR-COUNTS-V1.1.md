# HVR-014 — CC-012 v1.1 Resource Selector and Permission-Safe Counts

## 1. Verification Metadata

| Field | Value |
|---|---|
| Intent ID | `GS-SEARCH-DYNAMIC-RESOURCE-SELECTOR-COUNTS` |
| CC Version | CC-012 v1.1 FROZEN |
| IHR Reference | `IHR-GS-DYNAMIC-RESOURCE-SELECTOR-COUNTS.md` |
| ATR Reference | `ATR-GS-DYNAMIC-RESOURCE-SELECTOR-COUNTS.md` |
| Module | `wd_global_search` |
| Environment | Odoo 18, database `odoo18ce`, local Workspace |
| Code Baseline | CC-012 v1.1 working tree; no commit created for this implementation |
| Browser / Device | Shared Chromium browser used for tool-assisted checks; human run pending |
| Human Verifier | Not yet recorded |

## 2. Human Verification Contract Baseline

| Source | IDs | Human verification |
|---|---|---|
| CC-012 | CC12-TEST-001~006 | Dynamic descriptors, stable keys, multi-select and exact request scope |
| CC-012 | CC12-TEST-007~015, 019~024 | Authorized Facet Count, zero/positive transitions, isolation and version refresh |
| CC-012 | CC12-TEST-016~018, 028 | Timeout, failure, partial success and CC-007 protocol |
| CC-012 | CC12-TEST-029~031 | Initial hidden state, empty selection, Facet-only refresh and explicit reselect |
| CC-012 | CC12-TEST-025~027 | CC-002, CC-003 and CC-005 regression |

## 3. Current Human Verification Status

| Metric | Value |
|---|---|
| Human Verification Required | Yes |
| Required scenarios | 6 |
| PASS / FAIL / BLOCKED | 0 / 0 / 0 |
| NOT RUN | 6 |
| Current code baseline | CC-012 v1.1 working tree |
| Current valid human evidence | None |
| Evidence baseline status | Incomplete |

Tool-assisted Playwright observations are recorded in ATR, not as human HVR PASS.

## 4. Human Verification Coverage Matrix

| Requirement | Scenario | Evidence | Result |
|---|---|---|---|
| Selector hidden before first Query and explicit initial keys | HVR-SCN-001 | — | NOT RUN |
| Multi-select, self-excluding Facets and empty selection | HVR-SCN-002 | — | NOT RUN |
| Zero-count hide and positive-count reappearance | HVR-SCN-003 | — | NOT RUN |
| Timeout/Failure/Partial Success presentation | HVR-SCN-004 | — | NOT RUN |
| User/company permission isolation and unauthorized Resource invisibility | HVR-SCN-005 | — | NOT RUN |
| Published version refresh and CC-002/003/005/007 regressions | HVR-SCN-006 | — | NOT RUN |

## 5. Verification Scenarios

### HVR-SCN-001 — Initial Selector state

- **Steps:** Open a fresh Workspace without submitting a Query; then submit a Query.
- **Expected:** Selector is hidden before the first Search; the first request explicitly contains all current authorized stable Resource keys.
- **Evidence:** Visual observation and browser request payload.

### HVR-SCN-002 — Multi-select and empty scope

- **Steps:** Select/deselect multiple Resources; deselect all; change a non-Resource Refinement while selection remains empty; use the explicit reselect-all control.
- **Expected:** Requests exactly match selection; empty selection returns no business Results but refreshes Facets; only explicit reselect-all restores the all-authorized selection.
- **Evidence:** Visible selection and browser request/response observation.

### HVR-SCN-003 — Authorized zero/positive count transition

- **Steps:** Search a Query with zero-result Resources, then change the Query so a previously hidden Resource has positive results.
- **Expected:** Successful zero-count Resources are hidden and deselected; a newly positive Resource reappears unselected; no `(0)` is displayed.
- **Evidence:** Visible Selector and count labels.

### HVR-SCN-004 — Failure is not empty

- **Steps:** Observe a Resource timeout/failure and a partial-success Search in the acceptance environment.
- **Expected:** Failed Resource remains visible with unknown/error status; successful Resource counts remain; failure is not rendered as zero or hidden.
- **Evidence:** Actual fault-injection/timeout environment and browser observation; synthetic UI tests alone are insufficient.

### HVR-SCN-005 — Permission isolation

- **Steps:** Compare the Workspace as an ordinary user, a user with a different company context, and a user lacking access to one Published Resource.
- **Expected:** Unauthorized Resource Descriptor, count, error key and existence are not exposed; authorized counts reflect the current user/context only.
- **Evidence:** Human observation in distinct authorized sessions.

### HVR-SCN-006 — Published version and regression

- **Steps:** Publish a Resource configuration change, refresh the Workspace, then exercise Query, Date/State Refinement and Resource Selection.
- **Expected:** Descriptors and Facets use the same current Published version; Search/Permission/Error behavior remains consistent with CC-002/003/005/007.
- **Evidence:** Human observation and visible version-bound behavior.

## 6. Verification Run History

No HVR-RUN has been recorded for CC-012 v1.1. Do not infer a human PASS from the automated/browser checks listed in ATR.

## 7. Findings / Issues

No human findings have been recorded for v1.1. The SRS/TDD and Permission Boundary baselines remain unchanged.

## 8. Handoff

HVR-014 remains NOT RUN. Complete the required human scenarios and record an identifiable verifier, browser/device, actual observations, and any evidence before declaring CC-012 DoD satisfied.
