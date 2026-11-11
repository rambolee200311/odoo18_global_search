# FR-M2-CB-06 — Final Review

**Contract:** CC-M2-CB-06 v0.2
**Implementation status:** **Implementation complete; HVR partial; not ready for Final Acceptance.**

## Summary

Candidate B can finalize an already accepted Current through the existing single `office` Tool. Odoo attaches the same private version bytes to an assistant message in the current Thread and records the existing finalize reference. Delivery preserves Current, Last Valid, Document Revision, SHA, and the original validation grade, including `PARTIALLY_VERIFIED`.

## Acceptance matrix

| Requirement | Result | Evidence |
|---|---|---|
| Existing `office` Tool has controlled `finalize` action; no second public Tool | **PASS** | Focused tests in `ATR-M2-CB-06.md`. |
| Current and attachment identity/SHA checks; finalization reference and thread message | **PASS** | TransactionCase plus real UI tool result and current-user ORM readback. |
| `PARTIALLY_VERIFIED` delivered without revalidation/promotion | **PASS** | Focused test and UI version `1464` result; grade remains partial. |
| Idempotent service retry | **PASS** | TransactionCase reuses same attachment/message IDs. UI duplicate request not run. |
| Full M2/M1 Odoo regression | **PASS** | 250 tests, 0 failed/errors in `evidence/CB-M2-CB-06/odoo-cb06-full-regression.log`. |
| Real Discuss card in current Thread | **PASS** | HVR Thread `15880`, assistant message `101090`, private attachment `39747`. |
| Current-user browser download, successful response, downloaded-file SHA/readback | **BLOCKED/UNVERIFIED** | Download was clicked; IAB did not expose file or HTTP status and blocked direct endpoint navigation. ORM attachment bytes match SHA and parse, but do not substitute for browser download. |
| CC-05 contact workbook V3 final delivery HVR | **NOT RUN** | HVR used synthetic Inventory workbook, not the CC-05 contact V3 artifact. |

## Evidence index

- `IHR-M2-CB-06.md` — implementation and runtime facts.
- `ATR-M2-CB-06.md` — focused/full automation and static checks.
- `HVR-M2-CB-06.md` — current-user Discuss HVR and limitations.
- `evidence/CB-M2-CB-06/odoo-cb06-focused-final3.log`
- `evidence/CB-M2-CB-06/odoo-cb06-full-regression.log`
- `evidence/CB-M2-CB-06/odoo-8091-hvr.log`
- `evidence/CB-M2-CB-06/readback_finalize_20261110_retry1.log`
- `evidence/CB-M2-CB-06/finalized-current-1464.xlsx`
- `TDD_office_engine_m2_v2.0.4_CB06_Amendment.md`

## Result

The technical implementation and automated regression pass. The live UI completed Finalize and showed the expected attachment card. CC-06 cannot be submitted as `READY FOR FINAL ACCEPTANCE` because the required browser-download byte evidence and the contact-workbook final-delivery HVR scenario are incomplete. No `Final Accepted` status is claimed.
