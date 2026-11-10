# CC-M2-CB-02 Concurrency Gate Review — 2026-11-07

Status: initial read-only review and amendment request; the owner later approved the narrow amendment. Test execution and results are recorded below. The frozen v0.3 source remains unchanged.

## Frozen requirement

`CC-M2-CB-02_Workbook_Version_Artifact_Service_v0.3.md` §10 (lines 243, 247, 252) requires a real race between two independent Odoo cursors/connections, with only one candidate accepted, and restricts the race to a disposable/isolated test database. Sequential `TransactionCase` calls do not satisfy this evidence requirement. The existing authorization to use `odoo18ce` for ordinary integration tests did not amend this clause.

## Existing helper and cleanup constraint

- `mymodules/office_engine_m2/tests/integration/test_workbook_version_race.py:15-33` creates a two-party barrier and separate `registry.cursor()` instances, then commits a successful candidate and rolls back an exception.
- `test_workbook_version_race.py:26-28` catches every `Exception` and labels it `rejected`; it does not prove that the losing candidate was rejected specifically for stale parent/revision. Other exceptions must be classified as test failures in any execution evidence.
- `mymodules/office_engine_m2/models/office_workbook_version.py:195-196` prohibits deleting version history. `mymodules/office_engine_m2/models/ir_attachment.py:52-55` prohibits deleting version-bound attachments. A real race needs one committed winner, so ordinary ORM cleanup cannot remove the resulting immutable synthetic lineage from a shared database.

## Approved narrow amendment

Replace only the §10 database-environment restriction with:

> A real concurrency test may run on a non-production Odoo development/test database only with explicit owner approval and a dedicated, uniquely identifiable synthetic Session/Thread/Version/Attachment set. Before execution, verify that the targets are test-only and have no active business operation. Use two independent Odoo cursors/transactions synchronized to compete for the same parent and Document Revision. Exactly one candidate must commit; the other must be rejected for a specifically asserted stale/revision conflict. Any unrelated exception is a test failure. Verify the final current/last-valid/revision pointers, candidate states, and attachment bindings, and verify there were no out-of-scope changes. Roll back or clean up test records after execution. If immutable history prevents cleanup, retaining a uniquely marked synthetic version lineage requires separate explicit owner approval; without that approval, use a disposable database. Production databases remain prohibited unless separately authorized. Sequential calls are not concurrency evidence.

This changes no business acceptance criteria, permission checks, atomicity assertions, or one-winner requirement. It only clarifies eligible test environments and the cleanup exception required by the immutable version-history implementation. The approved amendment is recorded in `docs/implementation/CC-M2-CB-02_Workbook_Version_Artifact_Service_v0.3.1_Concurrency_Amendment.md`; v0.3 is preserved unchanged.

## Owner decision — resolved

Choose one:

The owner selected option 1 on 2026-11-07: approve the narrow amendment and allow retaining one uniquely marked synthetic version lineage in non-production `odoo18ce` if ORM cleanup is impossible.

## Actual concurrency evidence

- The one-shot ORM runner was executed as `./venv/bin/python docs/implementation/evidence/CB-M2-CB-02/run-concurrency-acceptance-shell.py`; exit code 0. It created only the tagged synthetic Thread `13850`, Session `10612`, V1 `101`, and candidates `102`/`103`; it made zero Provider calls. The setup guard found no pre-existing Thread with this exact tag.
- Two independent database backends, PIDs `37490` and `37491`, met at the test barrier. Candidate `103` committed as the sole current version. Candidate `102`'s original concurrent transaction rolled back with PostgreSQL `SerializationFailure: could not serialize access due to concurrent update`; a fresh retry was rejected by the service with `WORKBOOK_VERSION_STALE`.
- Final pointers are consistent: current/last-valid `103`, Document Revision `2`; V1 `101` is superseded; exactly one candidate is accepted and the competing candidate remains non-current. The independent read-only ORM check found exactly three version records and exactly three version-owned output attachments, with expected parent/input relationships and no orphan version attachment.
- All three retained XLSX attachments passed SHA-256 matching, ZIP integrity, and `openpyxl` readback. No business records were modified. The immutable synthetic lineage is retained under the owner-approved unique tag.
- Logs: `concurrency-run-20261107_authorized.log` and `concurrency-lineage-readback-20261107.log`. Earlier bootstrap failures are retained separately and occurred before any DB writes.

Concurrency status: **PASS** under approved CC amendment v0.3.1. This is not Final Acceptance; the owner remains responsible for the Final Acceptance decision.
