# CC-M2-CB-02 — Workbook Version & Artifact Service

## v0.3.1 — Approved Concurrency Environment Amendment

- Status: **APPROVED — AMENDMENT TO CC v0.3 §10 / §11 ONLY**
- Approval: project owner response on 2026-11-07: “批准最小修订并允许保留合成版本链”。
- Base contract: [CC-M2-CB-02 v0.3](CC-M2-CB-02_Workbook_Version_Artifact_Service_v0.3.md)
- Scope: concurrency test environment and retention boundary only. All other requirements and acceptance criteria in v0.3 remain unchanged.

## Amendment

For the §10 “Database concurrency” matrix row and its following environment restriction, replace the disposable-database-only condition with:

> A real concurrency test may run on a non-production Odoo development/test database explicitly authorized by the project owner, using a dedicated, uniquely identifiable synthetic Session/Thread/Version/Attachment lineage. Before execution, verify through Odoo ORM that the target lineage is test-only and has no active business operation. Use two independent Odoo cursors/transactions synchronized to compete for the same parent and Document Revision. Exactly one candidate must commit; the other must be rejected for a specifically asserted stale/revision conflict. Any unrelated exception is a test failure. Verify the final current/last-valid/revision pointers, candidate states, and attachment bindings, and verify there were no out-of-scope changes. Roll back or clean up test records after execution when possible. Because the version and version-bound attachment history is immutable, retaining one uniquely marked synthetic lineage in the explicitly authorized non-production test database is permitted when ORM cleanup is not possible. Production databases remain prohibited unless separately authorized. Sequential calls are not concurrency evidence.

The related references in §11 to “isolated database concurrency” mean concurrency performed in an environment permitted by this amended §10. The §11 requirement for a real, independently executed race and all one-winner, stale-loser, attachment, and state-consistency assertions remain unchanged.

## Explicitly unchanged

- No business acceptance criterion is removed or weakened.
- Odoo ORM ACL/Record Rules and attachment checks remain in force.
- The race must use separate database connections and overlapping transactions; sequential simulation is insufficient.
- Only synthetic test objects may be created or retained. No existing business record may be modified.
- No PostgreSQL or Odoo service restart, database creation/replacement, or production database test is authorized by this amendment.
- The amendment authorizes the remaining CB-02 concurrency test only; it does not start CB-03 or authorize production release.
