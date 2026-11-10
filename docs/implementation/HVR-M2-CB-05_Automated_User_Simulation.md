# HVR-M2-CB-05 — Automated User Simulation

**Verification type:** Automated User Simulation (not human manual verification)
**Status:** PASS — Automated User Simulation (TransactionCase / Mock Candidate adapter)
**Date:** 2026-11-10
**Provider:** Mock only in the test definition; no Provider call occurred in this turn.

## Execution Record — 2026-11-10

- Database: `odoo18ce`, as set in `odoo.conf` and explicitly passed with `-d odoo18ce`.
- Verification type: **Automated User Simulation** through an Odoo `TransactionCase`. It is not human manual verification, browser HVR, or a real-model Agent conversation.
- Candidate editing: existing service path with `ExpectedEffectWorkbookAdapter` test Mock. No real Provider request or external file transfer.
- Final combined runner executed 13 test methods: all 5 CC-05 methods plus 8 M1 Retriever regressions; result **0 failed / 0 errors**, exit code 0. Full log: `evidence/CB-M2-CB-05/cc05_artifact_run_20261110.log`.
- The simulated user messages and Tool calls use the registered `office` facade. The test retrieves through the existing Thread-bound Retriever, creates Candidates through the existing plan/edit/validator/version services, and accepts only through `office(action="accept")`; it does not directly write Candidate or Current status fields.

### Stage 1 — contact details

Simulated instruction: “请从 Odoo 联系人中选择这 3 个联系人，将名称、电话和邮件填写到当前 Excel。”

- Thread `16723`; Session `12840`; initial V1 `1574`.
- First `office.retrieve` queried three synthetic `res.partner` rows with `name`, `phone`, `email`, limit 3, stable `id` order. Returned IDs: **29862, 29863, 29864**.
- Test logged and checked the actual retrieved synthetic rows:
  - `CB05 Contact 0 c8432cb6cdf64dce84d972ed9b419190`, `+12025550000`, `cb05-c8432cb6cdf64dce84d972ed9b419190-0@example.invalid`
  - `CB05 Contact 1 c8432cb6cdf64dce84d972ed9b419190`, `+12025550001`, `cb05-c8432cb6cdf64dce84d972ed9b419190-1@example.invalid`
  - `CB05 Contact 2 c8432cb6cdf64dce84d972ed9b419190`, `+12025550002`, `cb05-c8432cb6cdf64dce84d972ed9b419190-2@example.invalid`
- Candidate V2 `1575` was accepted through the registered `office` action: `accepted_current`. Parent V1 `1574`; Current=Last Valid=`1575`; Document Revision `2`.
- V1 input SHA-256: `210c33c9c5490b7930ce8806e889d3830a9237bdcaa261f7ab1e6f5ba352282b`.
- V2 output SHA-256: `2fd550748e270db754943a66e7445955abd2db047d2bef1e5624c96ff5806928`.
- Independent readback confirmed the three header cells and A2:C4 values.

### Stage 2 — address refresh

Simulated instruction: “请在第四列增加地址表头，并从 Odoo 查询刚才这 3 个联系人的地址，填写到对应行。”

- Same Thread `16723`, same Session `12840`.
- Three additional independent `office.retrieve` calls queried exactly IDs **29862**, **29863**, **29864** for `street`, `street2`, `city`, `state_id`, `zip`, `country_id`. The log records all three ID-constrained queries.
- Returned address values, with empty fields omitted:
  - `100 Synthetic Street, Test City 0, 10000`
  - `101 Synthetic Street, Unit 2, Test City 1, 10001`
  - `102 Synthetic Street, Test City 2, 10002`
- Candidate V3 `1576` was accepted through `office(action="accept")`: `accepted_current`. Parent V2 `1575`; Current=Last Valid=`1576`; Document Revision `3`.
- V3 input SHA equals V2 output SHA: `2fd550748e270db754943a66e7445955abd2db047d2bef1e5624c96ff5806928`.
- V3 output SHA-256: `c7bc3c001ced2374cb94a278461ec8169921d0f8b31b3e2679c9a2b6f7e7a8b6`.
- Candidate readback asserted D1=`地址`, D2:D4 equal the retrieved addresses, and every A2:C4 value unchanged from V2.

### Artifacts and independent readback

- Exact generated XLSX bytes are retained under `evidence/CB-M2-CB-05/hvr_artifacts_20261110/`: V1 input, V2 Candidate, V3 Candidate.
- Independent reader: `evidence/CB-M2-CB-05/readback_hvr_artifacts_20261110.py`; execution output: `evidence/CB-M2-CB-05/hvr_artifacts_20261110_readback.log`.
- Independent checks: ZIP integrity, `openpyxl` read, header/content assertions, A–C preservation and D-column address match — all PASS.
- Contact rows were synthetic records created within the test transaction. A before/after ORM comparison confirmed their fields were unchanged. The Odoo `TransactionCase` rolled back the synthetic ORM rows, Thread, Session, Candidate and attachment data after completion; only the three local XLSX evidence files remain.
- The Odoo runner's log reports its standard `filestore gc 10 checked, 10 removed`; the log does not identify those blobs, so exact GC scope is **UNVERIFIED**. The test did not issue an explicit business-attachment deletion.

## HVR Result

**PASS for the CC-05 Automated User Simulation scope.** Both data-retrieval stages and both formal acceptance transitions passed, including version pointers, revisions, hashes and independent workbook readback. No claim is made for real Provider, browser UI, human manual review, or persistent production data.
