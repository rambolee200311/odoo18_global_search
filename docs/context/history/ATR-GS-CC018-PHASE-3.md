# ATR - CC-018 Phase 3

## 1. Execution Metadata

| Field | Value |
|---|---|
| Intent ID | `GS-SEARCH-ARCHITECTURE-REFACTORING` |
| Contract | CC-018 v1.2.0 |
| Module | `wd_global_search` |
| Framework | Odoo tests / HttpCase; pytest-playwright 0.10.0 / Chromium |
| Environment | Local Odoo 18, `odoo18ce`, port 8091 |
| Code baseline | Working tree based on `09205c718e600b868824156864584016f63aa0bb`; uncommitted |
| Executed | 2026-10-15 |

## 2. Test Contract Baseline

CC-TEST-025 and CC-TEST-001-012, as defined by
[CC-018 §§7 and 11](../intent/CC-018_architecture_refactoring.md).

## 3. Coverage

| Test | Result | Evidence |
|---|---|---|
| Route registry uniqueness and metadata | PASS | `TestControllerRouteRegistry` |
| Unauthenticated route-family requests | PASS | `TestControllerUnauthenticatedRoutes` |
| Template field descriptor unit test | PASS | `TestTemplateFieldDescriptor` |
| CC-TEST-025 targeted | PASS, 1 passed / 15 deselected | `run_isolated.py --browser chromium -k cc_test_025` |
| CC-TEST-001-012, CC-TEST-024, and CC-TEST-025 | PASS, 16/16 | `run_isolated.py --browser chromium` |

## 4. Run History

| Run | Scope | Result |
|---|---|---|
| ATR-RUN-001 | Odoo registry and unauthenticated HttpCase route checks | PASS, 2 selected test methods |
| ATR-RUN-002 | CC-TEST-025 controller endpoint contract | PASS, 1 passed |
| ATR-RUN-003 | Odoo registry, unauthenticated HttpCase, and field descriptor tests | PASS, 3 selected test methods; 0 failures, 0 errors |
| ATR-RUN-004 | Full current Chromium UI suite | PASS, 16 passed in 20.10s |

CC-TEST-025 checks the 13 registered routes for URL uniqueness and expected
route type, authentication, HTTP methods, and CSRF metadata. Its normal-user
Playwright requests cover configuration descriptor/records/preview/check,
wrong-method and missing-CSRF rejection, safe invalid-resource save/apply
errors, reader denial, Preview/navigation errors, and Search/Cancel response
shapes. It does not mutate the existing published baseline.

## 5. Limitations and Handoff

The initial targeted CC-TEST-025 run exposed a 403 in the descriptor endpoint
for the normal configuration-manager role. The user approved a narrow
permission-safe correction; it uses the existing related model-name field and
retains the translated field metadata lookup. The successful final run verifies
that route under the authorized role.

The local Odoo test run logged warnings for unrelated optional modules that are
not installed in this database. The selected `wd_global_search` tests
completed with 0 failures and 0 errors.

Cross-engine/Safari manual verification remains waived only for this execution;
see [the phase-1 HVR waiver record](HVR-GS-CC018-PHASE-1.md). Phase 4 may
proceed; CC-018 remains open.
