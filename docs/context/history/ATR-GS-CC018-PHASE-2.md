# ATR — CC-018 Phase 2

## 1. Execution Metadata

| Field | Value |
|---|---|
| Intent ID | `GS-SEARCH-ARCHITECTURE-REFACTORING` |
| Contract | CC-018 v1.2.0 |
| Module | `wd_global_search` |
| Framework | pytest-playwright 0.10.0 / Chromium |
| Environment | Local Odoo 18, `odoo18ce`, port 8091 |
| Code baseline | Working tree based on `09205c718e600b868824156864584016f63aa0bb`; uncommitted |
| Executed | 2026-10-15 |

## 2. Test Contract Baseline

CC-TEST-024 and CC-TEST-001–012, as defined by
[CC-018 §§6 and 11](../intent/CC-018_architecture_refactoring.md).

## 3. Coverage

| Test | Result | Evidence |
|---|---|---|
| CC-TEST-024 targeted | PASS, 1 passed / 14 deselected | `run_isolated.py --browser chromium -k cc_test_024` |
| CC-TEST-001–012 + CC-TEST-024 | PASS, 15/15 | `run_isolated.py --browser chromium` |
| Cross-engine / Safari HVR | WAIVED for this execution; see the phase-1 waiver record | [HVR-GS-CC018-PHASE-1.md](HVR-GS-CC018-PHASE-1.md) |

## 4. Run History

| Run | Scope | Result |
|---|---|---|
| ATR-RUN-001 | Targeted QWeb/HTTP/DOM CC-TEST-024 | PASS, 1 passed in 7.48s |
| ATR-RUN-002 | Full current Chromium UI suite | PASS, 15 passed in 19.96s |

## 5. Limitations and Handoff

The UI response and DOM contract were tested on the accepted current baseline.
This does not provide a historical pre-extraction response comparison. No
`HttpCase` was added because it would require an Odoo test-admin environment;
the controller was exercised instead through the authenticated normal-user
Playwright session. Phase 3 may proceed under the user-approved waiver.
