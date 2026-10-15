# ATR - CC-018 Phase 5

## 1. Execution Metadata

| Field | Value |
|---|---|
| Intent ID | `GS-SEARCH-ARCHITECTURE-REFACTORING` |
| Contract | CC-018 v1.2.0 |
| Module | `wd_global_search` |
| Framework | Odoo ORM/TransactionCase and pytest-playwright 0.10.0 / Chromium |
| Environment | Local Odoo 18, `odoo18ce`, port 8091 |
| Code baseline | Working tree based on `09205c718e600b868824156864584016f63aa0bb`; uncommitted |
| Executed | 2026-10-15 |

## 2. Test Contract Baseline

CC-TEST-027 and the full Odoo module test suite, CC-TEST-001-012,
CC-TEST-024-026, and CC-TEST-023, as defined by
[CC-018 §§9 and 11](../intent/CC-018_architecture_refactoring.md).

## 3. Coverage

| Test | Result | Evidence |
|---|---|---|
| CC-TEST-027 registry/schema/lifecycle checks | PASS, 2 tests | `test_configuration_registry.py`, included in module upgrade suite |
| Odoo module upgrade and full module tests | PASS, 108 tests; 0 failures, 0 errors | `odoo-bin -c odoo.conf -d odoo18ce --stop-after-init --test-enable -u wd_global_search` |
| CC-TEST-005 and CC-TEST-028 role/fixture checks | PASS, 2 passed | `run_isolated.py --browser chromium -k 'cc_test_005 or cc_test_028'` |
| Full Chromium UI suite after role correction | PASS, 18 passed | `run_isolated.py --browser chromium` |
| CC-TEST-023 performance soft gate | PASS, 30 measured samples after 3 warm-ups | `CC018-performance-chromium-20261015T085931Z.json` |
| Phase-1-to-final CC-TEST-023 comparison | PASS, within soft gate | Navigation +1.0%; response-to-render -1.3%; both below absolute thresholds |
| Model syntax / AST preservation | PASS | Python compilation and exact AST comparison for all 14 model classes |
| Workspace service restoration | PASS | HTTP 200 from local `/web/login` after upgrade tests |

CC-TEST-027 checks every original model name through the Odoo environment,
representative field types and comodel relations across all model families,
and the Configuration Version lifecycle method entry points. It performs no
direct database access.

## 4. Run History

| Run | Scope | Result |
|---|---|---|
| ATR-RUN-001 | CC-TEST-027 on the pre-split model source | PASS, 2 tests; 0 failures, 0 errors |
| ATR-RUN-002 | CC-TEST-027 after extraction | PASS, included in the full module suite |
| ATR-RUN-003 | Full Odoo module upgrade/test suite | PASS, 108 tests; 0 failures, 0 errors |
| ATR-RUN-004 | Full Chromium UI suite after model split | PASS, 17 passed in 20.95s |
| ATR-RUN-005 | CC-TEST-023 before role correction | PASS, 1 passed in 10.61s |
| ATR-RUN-006 | CC-TEST-005 and CC-TEST-028 after removing `status_writer` | PASS, 2 passed |
| ATR-RUN-007 | Full Chromium UI suite after role correction | PASS, 18 passed in 19.72s |
| ATR-RUN-008 | Final CC-TEST-023 after role correction | PASS, 1 passed in 9.77s |

The Odoo log also reports optional, unrelated modules unavailable in this
database. The `wd_global_search` module test result remains 108 tests with no
failures or errors.

## 5. Final Cross-Phase Deviation Disposition

The following are retained as limitations and are not represented as PASS:

| ID | Deviation / limitation | Current disposition |
|---|---|---|
| DEV-001 | Workspace QWeb extraction preceded phase-1 baseline capture. | CC-TEST-024 verifies current rendering and HTTP output, but no historical pre-extraction response exists for exact comparison. Accepted as a historical limitation for this execution by the user's final freeze approval; the missing baseline is not represented as recovered. |
| DEV-002 | A Sales Order reader role extends the frozen four-role test-user list. | The unapproved `status_writer` was removed. `status_reader` remains under the earlier recorded user approval because the four frozen roles lack Sales Order ACL. Accepted as a documented exception for this execution; strict four-role conformance is not claimed. |
| DEV-003 | Earlier cleanup of stale fixtures used `sudo()`, contrary to the frozen normal-ORM-only rule. | The unique markers were subsequently verified absent; no privileged cleanup was repeated. Accepted as a historical process deviation for this execution; it is not represented as compliant behavior. |
| DEV-004 | Firefox could not launch in the macOS Playwright environment. | BLOCKED, not PASS. The browser limitation was accepted for this execution by the user's final freeze approval; Firefox is not represented as passed. |
| HVR / CC-TEST-020 | No full manual HVR or Safari validation; no phase-4/5 Firefox or WebKit rerun. | Waivers remain waivers, not test passes. The user reported final manual verification passed on 2026-10-15 and approved the CC-018 freeze; this does not assign PASS to individual HVR scenarios or Safari. |
| CC-TEST-028 | The session fixture creates the four frozen roles plus the previously approved `status_reader`; it does not create `status_writer`. | ORM cleanup and unique-marker verification pass. The documented `status_reader` exception is accepted for this execution; strict four-role conformance is not claimed. |

The phase-1-to-final performance comparison is valid for the captured
phase-1 working tree, but that working tree already included the QWeb
extraction; it is not a pristine pre-QWeb implementation baseline.

## 6. Handoff

Phase 5 automated implementation and verification are complete. All five
phase records exist. On 2026-10-15, after the `wd_global_search` upgrade and
service restart on port 8091, the user reported that manual verification
passed and approved freezing CC-018. This approval accepts the documented
deviations and waivers for this execution; it does not erase them or convert
blocked/waived checks into PASS.

The CC-018 implementation is frozen at this accepted state. Any further
implementation change requires a new approved change scope.
