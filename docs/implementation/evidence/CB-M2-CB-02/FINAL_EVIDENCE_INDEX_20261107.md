# CC-M2-CB-02 — Final Acceptance Evidence Index

Evidence date: 2026-11-07; reconciliation compiled: 2026-11-08
Contract baseline: [CC v0.3](../../CC-M2-CB-02_Workbook_Version_Artifact_Service_v0.3.md) plus owner-approved [v0.3.1 concurrency environment amendment](../../CC-M2-CB-02_Workbook_Version_Artifact_Service_v0.3.1_Concurrency_Amendment.md)
Status: **READY FOR FINAL ACCEPTANCE — owner decision pending; not Final Accepted**

This index reconciles evidence already recorded in ATR-RUN-005 and ATR-RUN-006. It records no new test execution.

## Acceptance evidence

| Requirement | Result | Evidence |
|---|---|---|
| Upgrade `office_engine_odoo` and `office_engine_m2` | PASS | [`cc02_transactioncase_20261107_retry1.log`](cc02_transactioncase_20261107_retry1.log): both modules loaded during the authorized upgrade/registry test run. |
| Full Odoo TransactionCase run | PASS with one skip | Same log: 203 test methods started; final result 0 failures and 0 errors. 202 were not skipped; the browser-backed RPC test was skipped because `websocket-client` was unavailable. |
| CB-02 focused TransactionCase | PASS | [`cc02_targeted_20261107_retry1.log`](cc02_targeted_20261107_retry1.log): 18 tests, 0 failures, 0 errors. |
| M1 / RenderBridge regression | PASS | [`cc02_m1_regression_20261107_retry1.log`](cc02_m1_regression_20261107_retry1.log): 23 tests, 0 failures, 0 errors. |
| Database race under permitted environment | PASS | [`concurrency-run-20261107_authorized.log`](concurrency-run-20261107_authorized.log) records two distinct backend PIDs, one committed winner, and the competing transaction's serialization rollback. The loser retry was rejected as `WORKBOOK_VERSION_STALE`. Environment eligibility is provided by approved v0.3.1; no unapproved deviation from the amended contract remains. |
| State, attachment binding and XLSX readback | PASS | [`concurrency-lineage-readback-20261107.log`](concurrency-lineage-readback-20261107.log): current/last-valid/revision consistency, exactly three versions and output attachments, matching SHA-256, ZIP integrity and `openpyxl` readback. |
| 203 versus 241 test-statistics difference | RESOLVED | [`test-count-analysis-20261107.md`](test-count-analysis-20261107.md) explains 241 as 203 started test methods plus 38 setup/teardown statistics entries; it is not 241 tests. |

## Concurrency result details

- Authorized non-production database: `odoo18ce`; no production database was used.
- Unique synthetic lineage: `CB02-CONCURRENCY-APPROVED-20261107-01`; retained under the owner's explicit approval because immutable version/attachment records cannot be removed through ORM.
- Thread `13850`; Session `10612`; V1 `101`; competing candidates `102` and `103`.
- Independent backend PIDs: `37490` and `37491`.
- Candidate `103` alone committed as `accepted_current`; candidate `102`'s racing transaction rolled back with PostgreSQL `SerializationFailure`, and a fresh service retry returned `WORKBOOK_VERSION_STALE`.
- Final current and last-valid: `103`; Document Revision: `2`; no business records modified; Provider calls: `0`.
- Version-output attachments `32117`, `32118`, and `32119` each match their recorded version SHA and pass ZIP/openpyxl checks.

## Preserved limitations and release boundary

- One test method remains skipped because `websocket-client` is not installed; its browser-backed RPC path is therefore not verified by this run.
- Production attachment retention/deletion policy remains **Release Gate OPEN**. This does not block synthetic-data CB-02 technical acceptance, but it blocks production enablement as recorded in the contract/IHR/ATR.
- CB-03 Validator production integration, Provider/Browser E2E, and production release are outside CB-02 and are not implied by this evidence.
- Historical first-run failures and environment-attempt logs remain preserved and are not rewritten as passes.

## Log digests

| Evidence file | SHA-256 |
|---|---|
| `cc02_transactioncase_20261107_retry1.log` | `b7e1621c780620775f178e81d10a3cc977e178ed9e36eca558c30f94f2b14bc1` |
| `cc02_targeted_20261107_retry1.log` | `f9913c3b0c312de20bea17ef36ee7c54f6c47b204293f87779465eb9fa9553c5` |
| `cc02_m1_regression_20261107_retry1.log` | `79d9f28c89ebbf37643bf27c1504a19e9e5146e0e0ccec67540e184d58f7f689` |
| `concurrency-run-20261107_authorized.log` | `f2ac9a10eae2cc0183a3c9801f5cf277195af31839e2be2b978cbc613f1f0af1` |
| `concurrency-lineage-readback-20261107.log` | `dcf60940934251ed7322fbd21f91fd018f639c54d9240cbf7535ed0f67d67def` |
| `test-count-analysis-20261107.md` | `3963ac212e7ec3954aa49dbe5a8bc7c0420edbf7c5a17f983708387849677bd0` |

## Disposition

The evidence supports **READY FOR FINAL ACCEPTANCE** for the CB-02 scope. The project owner must record the separate `Final Accepted` decision. No CC v0.3 contract text is changed by this index.
