# IHR - CC-018 Phase 5

## 1. Execution Metadata

| Field | Value |
|---|---|
| Intent ID | `GS-SEARCH-ARCHITECTURE-REFACTORING` |
| Contract | CC-018 v1.2.0 |
| Module | `wd_global_search` |
| Phase | Configuration ORM model split |
| Code baseline | Working tree based on `09205c718e600b868824156864584016f63aa0bb`; uncommitted |
| Environment | Local Odoo 18, `odoo18ce`, port 8091 |
| Status | Split and automated verification complete; final cross-phase deviations remain recorded |

## 2. Contract Baseline

CC-018 §9. The source class order and Odoo registry behavior were treated as
frozen. No fields, models, access rules, migrations, direct SQL, or existing
configuration data were added, removed, or changed.

## 3. Implementation History

| ID | Action | Result |
|---|---|---|
| IHR-001 | Split lifecycle mixin/domain/version definitions into `configuration_lifecycle.py`. | Original class order retained. |
| IHR-002 | Moved `BusinessResource` to `business_resource.py`, including its existing `init()` implementation. | Class body preserved exactly. |
| IHR-003 | Moved mapping, searchable field, relation path, date/state mapping, and snapshot field models to `resource_mapping.py`. | Original class order retained. |
| IHR-004 | Moved vocabulary, scoring, and performance policy models to `configuration_policy.py`; moved `AuditEvent` to `audit_event.py`. | Original class order retained. |
| IHR-005 | Updated `models/__init__.py` to import modules in the original model declaration order. | Abstract mutation mixin and dependent model registration order preserved. |
| IHR-006 | Added CC-TEST-027 registry, field type/relation, and lifecycle-method assertions. | Assertions use Odoo ORM metadata; no direct SQL. |
| IHR-007 | Compared parsed ASTs of all 14 original model classes with the extracted classes before removing `configuration.py`. | All 14 class ASTs matched exactly. |
| IHR-008 | Reduced the temporary test role set by removing the unapproved `status_writer`; supplied the existing authorized operator session only for isolated Sales Order fixture cleanup. | No extra test account is created for cleanup. |
| IHR-009 | Added CC-TEST-028 role-scope coverage and kept `status_reader` only for the previously approved Sales Order state-filter scenario. | Cleanup uses ordinary ORM and verifies the unique run marker is absent; the frozen four-role wording remains a recorded exception. |

## 4. Change Inventory

- Removed `mymodules/wd_global_search/models/configuration.py`.
- Added `models/configuration_lifecycle.py`, `models/business_resource.py`,
  `models/resource_mapping.py`, `models/configuration_policy.py`, and
  `models/audit_event.py`.
- Updated `models/__init__.py` in original declaration order.
- Added `tests/test_configuration_registry.py` and imported it from
  `tests/__init__.py`.
- Updated the UI fixture role provisioning and Sales Order cleanup to avoid
  creating `status_writer`.
- Added CC-TEST-028 role-scope coverage and updated the UI test README.
- Updated the CC-TEST-023 evidence index with the final post-correction
  30-sample run.

## 5. Verification

- CC-TEST-027 is included in the full Odoo module upgrade test run:
  108 tests, 0 failures, 0 errors.
- CC-TEST-005 and CC-TEST-028 targeted Chromium run: 2 passed.
- Full Chromium UI suite after model and role-scope changes: 18 passed.
- CC-TEST-023 final Chromium run: 30 measured samples after 3 warm-ups;
  navigation P95 21.638 ms and response-to-render P95 4.882 ms.
- Compared with the phase-1 recorded values (21.427 ms and 4.944 ms),
  navigation changed by +1.0% and response-to-render by -1.3%. Both remain
  within the 10% regression allowance and absolute soft thresholds.
- Python compilation and `git diff --check` passed.
- The local Odoo service was restored and returned HTTP 200 on port 8091.

## 6. Deviations / Limitations

- The phase-1 record documents cross-browser/HVR waivers, the pre-baseline
  QWeb extraction, additional temporary `status_reader` role, and an earlier
  privileged stale-fixture cleanup. `status_writer` has been removed; the
  `status_reader` role remains only under the earlier user approval and still
  differs from the frozen four-role text. These limitations remain recorded
  in [ATR-GS-CC018-PHASE-5.md](ATR-GS-CC018-PHASE-5.md).
- CC-TEST-028 cleanup passed using normal ORM and an existing authorized
  operator session for Sales Order fixture deletion. The remaining
  `status_reader` exception means strict four-role conformance is not claimed.

## 7. Handoff

The phase 5 split and automated verification are complete. No human HVR,
Firefox, WebKit, or Safari PASS is claimed. CC-018 final closure remains
subject to the recorded cross-phase deviations and the user's one-time
waivers.
