# IHR - CC-018 Phase 3

## 1. Execution Metadata

| Field | Value |
|---|---|
| Intent ID | `GS-SEARCH-ARCHITECTURE-REFACTORING` |
| Contract | CC-018 v1.2.0 |
| Module | `wd_global_search` |
| Phase | Controller route split |
| Code baseline | Working tree based on `09205c718e600b868824156864584016f63aa0bb`; uncommitted |
| Environment | Local Odoo 18, `odoo18ce`, port 8091 |
| Status | Implementation and automated verification complete; one-time HVR waiver applies |

## 2. Contract Baseline

CC-018 §7. The route families, authentication, methods, CSRF behavior, response
handling, and shared service state were captured from the pre-split
`controllers/main.py` before moving the route handlers.

## 3. Implementation History

| ID | Action | Result |
|---|---|---|
| IHR-001 | Split the routes into `workspace.py`, `search_api.py`, `configuration.py`, and `navigation.py`; explicitly import each module from `controllers/__init__.py`. | Completed |
| IHR-002 | Moved shared HTTP response helpers and the single SearchService instance to `controllers/_shared.py`; kept the template preview limiter and token limit in the configuration route module. | Shared state remains singular |
| IHR-003 | Added registry and unauthenticated HttpCase coverage, plus Playwright endpoint contract coverage as CC-TEST-025. | Completed |
| IHR-004 | Fixed descriptor model-name resolution for a normal configuration manager by using the existing `primary_model_name` related field instead of reading `ir.model` directly. The original `fields_get()` metadata path remains in place. | User-approved narrow correction |

## 4. Change Inventory

- Removed `mymodules/wd_global_search/controllers/main.py`.
- Added `controllers/_shared.py`, `controllers/workspace.py`,
  `controllers/search_api.py`, `controllers/configuration.py`, and
  `controllers/navigation.py`.
- Updated `controllers/__init__.py`.
- Added `tests/test_controller_routes.py` and imported it from
  `tests/__init__.py`.
- Updated `tests/test_template_descriptor.py` and added CC-TEST-025 to
  `tests/ui/test_workspace_baseline.py`.

## 5. Verification

- Odoo route registry, unauthenticated HttpCase, and field descriptor tests:
  3 selected tests passed; 0 failures and 0 errors.
- CC-TEST-025 targeted Chromium run: 1 passed.
- Full current Chromium UI suite, including CC-TEST-001-012, CC-TEST-024, and
  CC-TEST-025: 16 passed.
- Python compilation, pytest collection (17 tests), and `git diff --check`
  passed.
- The local Odoo service was restored and returned HTTP 200 on port 8091 after
  the server-side test run.

## 6. Deviations / Limitations

- The first CC-TEST-025 attempt found that the authorized configuration manager
  received HTTP 403 while the descriptor read `primary_model_id.model`. The
  user approved the minimal permission-safe correction. No group, ACL, record
  rule, or elevated access was added; the translated `fields_get()` metadata
  path was retained.
- CC-TEST-025 exercised successful read/preview/check endpoints and tested
  save/apply rejection using a nonexistent resource ID. It did not save or
  apply changes to the existing published baseline.
- No manual HVR or Safari PASS is claimed. The one-time user-approved waiver is
  documented in [HVR-GS-CC018-PHASE-1.md](HVR-GS-CC018-PHASE-1.md).

## 7. Handoff

Phase 3 automated implementation and verification are complete under the
recorded waiver. Phase 4 may proceed. This record does not close CC-018 as a
whole; phases 4 and 5 and the final deviation review remain open.
