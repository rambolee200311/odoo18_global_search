# ATR-RUN-005 Test Count Reconciliation

Status: read-only analysis of the preserved Odoo log and the repository's Odoo test-runner source. No tests were rerun.

## Log observations

Source log: `cc02_transactioncase_20261107_retry1.log`.

| Metric | `office_engine_m2` | `office_engine_odoo` | Total |
|---|---:|---:|---:|
| `Starting Test` events | 180 | 23 | 203 |
| Unique started test IDs | 180 | 23 | 203 |
| Duplicate started test IDs | 0 | 0 | 0 |
| `tests.stats` reported entries | 214 | 27 | 241 |
| Difference | 34 | 4 | 38 |
| Distinct test classes | 17 | 2 | 19 |

The final `odoo.tests.result` line is `0 failed, 0 error(s) of 203 tests`. One test was explicitly skipped:
`TestOfficeMappingRpcHttp.test_real_backend_browser_renders_select_and_saves_over_rpc`, reason `websocket-client module is not installed`. Thus 202 tests were not skipped; zero failures and zero errors were reported. The three `not installable` addon messages (`wd_qooling_app`, `wd_advanced_m2o_record_panel`, `wd_evidence_album`) are module-graph skips, not test-method skips.

## Explanation of 214/27 versus 203

The discrepancy is explained by Odoo's own statistics implementation:

- `odoo/tests/result.py:108-121`: `startTest()` increments `testsRun`; `stopTest()` adds a statistics entry keyed by the test ID.
- `odoo/tests/suite.py:161-190`: `OdooSuite` separately wraps `setUpClass` and `tearDownClass` in `result.collectStats(...)`.
- `odoo/tests/result.py:244-272`: `log_stats()` counts all matching statistics keys, including those class-lifecycle IDs, as `tests` in the module statistics line.
- `odoo/service/server.py:638` reports the result object string based on `testsRun`, not the statistics-key count.

The additional 38 entries equal two class-lifecycle statistics entries per test class: 17 M2 classes × 2 = 34, and 2 Odoo Request classes × 2 = 4. The log has 203 start events, 203 unique test IDs, and zero repeated IDs. Therefore 241 is a statistics-entry count, not the number of executed test methods. The runner result's 203 is the test-method count including the single skipped method.

## Acceptance count

Use the final `odoo.tests.result` count and individual `Starting Test` records as test-method execution evidence. Report **203 started, 202 not skipped, 1 skipped, 0 failures, 0 errors**. Do not report 241 as passed tests.
