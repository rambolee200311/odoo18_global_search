# IHR — CC-018 Phase 2

## 1. Execution Metadata

| Field | Value |
|---|---|
| Intent ID | `GS-SEARCH-ARCHITECTURE-REFACTORING` |
| Contract | CC-018 v1.2.0 |
| Module | `wd_global_search` |
| Phase | Workspace HTML extraction |
| Code baseline | Working tree based on `09205c718e600b868824156864584016f63aa0bb`; uncommitted |
| Environment | Local Odoo 18, `odoo18ce`, port 8091 |
| Status | Implementation and automated verification complete; waiver/deviation record applies |

## 2. Contract Baseline

CC-018 §§4 and 6. The user had already requested extraction of all inline
controller pages. The existing extraction was performed before phase 1 was
closed; this ordering deviation remains recorded in the phase-1 IHR.

## 3. Implementation History

| ID | Action | Result |
|---|---|---|
| IHR-001 | Workspace, card-template designer, and navigation-error markup are rendered from QWeb in `views/controller_pages.xml`. | Completed |
| IHR-002 | Workspace controller renders the QWeb template with the existing resource descriptor, configuration version, and timezone values. | Completed |
| IHR-003 | Added CC-TEST-024 assertions for HTTP status/content type, title, language, document order, resource JSON attributes, text-only labels, designer output, and navigation error output. | Completed |

## 4. Change Inventory

- `mymodules/wd_global_search/views/controller_pages.xml`
- `mymodules/wd_global_search/controllers/main.py`
- `mymodules/wd_global_search/__manifest__.py`
- `mymodules/wd_global_search/tests/ui/test_workspace_baseline.py`

## 5. Verification

CC-TEST-024 passed in Chromium (1 passed, 14 deselected). The complete current
Chromium UI suite, including CC-TEST-024, passed 15/15. The response returned
HTTP 200 with `text/html; charset=utf-8`; the tested DOM order and dynamic
resource attributes matched the contract assertions.

## 6. Deviations / Limitations

- The HTML extraction predates the phase-1 closure and has no directly captured
  pre-extraction browser response for byte-for-byte comparison. The user
  accepted the current built-in browser evidence for this execution; this
  record does not claim a historical response comparison.
- The user-approved HVR/Safari waiver is documented in
  [HVR-GS-CC018-PHASE-1.md](HVR-GS-CC018-PHASE-1.md); no human PASS is claimed.

## 7. Handoff

Phase 2 is accepted for transition to phase 3 under the recorded one-time
waiver. Phase 3 must preserve the HTTP route and response contracts verified
here.
