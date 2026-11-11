# ATR-M2-CB-06 — Automated Test Report

**Contract:** `CC-M2-CB-06_Finalize_Attachment_Delivery_v0.2.md`
**Database:** `odoo18ce`
**Result:** Automated regression PASS; this report does not claim full HVR or Final Acceptance.

## Test evidence

| Layer | Command/evidence | Result |
|---|---|---|
| Focused CB-06 | `evidence/CB-M2-CB-06/odoo-cb06-focused-final3.log` | **6 tests; 0 failed, 0 errors; exit 0.** Covers facade route, Discuss Store attachment event, exact accepted bytes, idempotent delivery, and preserving `PARTIALLY_VERIFIED`. |
| Full M2 + M1 regression | `evidence/CB-M2-CB-06/odoo-cb06-full-regression.log` | **250 tests; 0 failed, 0 errors; exit 0.** Existing `office_engine_m2` and `office_engine_odoo` tagged suite. No `-u` module upgrade. |
| Python syntax | `py_compile` for the four changed Python modules and three changed test files | **PASS.** |
| Whitespace | `git diff --check` for the implementation diff | **PASS.** |

The full log reports `tests.stats` values of 266 for M2 and 28 for M1 (294 summed), while `odoo.tests.result` reports 250 executed tests. This pre-existing difference is **UNEXPLAINED**; no claim is made that 294 tests ran. The final suite result and test-start records are retained in the raw log. Startup/test logs also report unrelated unavailable addons and missing models; they did not produce failed/error tests.

## Covered invariants

- `office(action="finalize")` is in the existing `office` action schema; no separate public Tool was added.
- Only an accepted Current bound to the current Thread/Session/revision can be delivered.
- Finalize rechecks attachment and output SHA, posts/reuses the assistant Thread message, and registers through `record_finalize_reference`.
- Current, Last Valid, Document Revision, and output bytes remain unchanged by delivery.
- Both `VERIFIED` and already accepted `PARTIALLY_VERIFIED` retain their original grades; no validation rerun or promotion occurs.
- Duplicate retries reuse the same attachment/message; failure paths do not falsely report delivered.
- M1 Finalize/RenderBridge/attachment paths remained in the full regression scope.

## Preserved initial failures

Earlier focused logs in this evidence directory are retained. One run exposed a stale action-schema assertion; a subsequent selected run exposed an outdated prompt assertion. Both test expectations were updated to the v0.2 `finalize` contract, and the final focused and full runs above passed. No production behavior was weakened to make those tests pass.

## HVR boundary

Automated tests verify service and Store behavior. They are not evidence of a successful browser download. See `HVR-M2-CB-06.md`: the card was visible and clicked, but the CUA environment did not provide a downloadable local file or successful HTTP result; the attachment bytes were verified separately via current-user ORM readback.
