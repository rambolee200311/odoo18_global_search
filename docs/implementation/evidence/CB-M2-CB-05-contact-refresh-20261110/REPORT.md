# Office Engine M2 — Contact Excel Refresh E2E Check

**Date:** 2026-11-10  
**Result:** BLOCKED before data retrieval; source-level route gap confirmed  
**Purpose:** Check whether existing Agent + `odoo_record_retriever` + Office Engine can perform two Odoo reads and two accepted workbook edits in one Thread.

## Scope and safety

- Used the authenticated Odoo 18 CE UI as Mitchell Admin in database `odoo18ce`.
- Created one empty test Thread, `llm.thread_16662`, and selected the existing `M2 E2E Local Mock 20261026` provider for that Thread.
- Read the provider form only to confirm its API base was loopback `http://127.0.0.1:8909/v1`; the API key remained redacted.
- No chat request was sent, no contact data was retrieved, no XLSX was uploaded, and no Candidate or workbook version was generated.
- No Odoo business record was changed. No module upgrade, service restart, code edit, or Git operation occurred.

## Execution evidence

| Step | Result | Evidence |
|---|---|---|
| Local Mock availability | **BLOCKED** | A no-payload `GET /v1/models` to the configured loopback endpoint failed immediately with connection refused (`HTTP 000`, curl exit 7). No model request was sent. |
| Odoo ORM shell startup | **BLOCKED** | The read-only local `odoo-bin shell -c odoo.conf -d odoo18ce` attempt failed while loading the registry: `ModuleNotFoundError: No module named 'emoji'`. It did not reach the current-user or partner queries, or Retriever. |
| Three-contact selection / IDs | **NOT RUN** | No partner records were read; no contact IDs or values are claimed. |
| Synthetic workbook creation/upload | **NOT RUN** | Stopped before file creation/upload because the local Agent dispatch path was unavailable. |
| Stage 1 Retriever → Candidate → accept | **NOT RUN** | No Agent request, Retriever call, Candidate, or acceptance occurred. |
| Stage 2 Retriever by the same IDs → Candidate → accept | **NOT RUN** | Depends on Stage 1; no data or file state was created. |
| Current / Revision / SHA comparisons | **NOT RUN** | No versioned workbook was created. |

The only Odoo state created for this check is the empty test Thread `llm.thread_16662` with the local Mock Provider selected. The previous user Thread was not used or modified.

## Existing implementation findings

1. **The Retriever has the required query capability.** [`llm_tool_record_retriever.py`](../../../../odoo-llm/llm_tool/models/llm_tool_record_retriever.py) uses the request's ORM environment for `search_read`/`read`, accepts model/domain/fields/order/limit/offset, adds an ID tie-breaker when an order is supplied, and can return `count`, `offset`, `limit`, and `has_more`. The M2 Thread override delegates to this existing implementation at [`llm_thread.py`](../../../../office_engine_m2/models/llm_thread.py).

2. **The M1-style initial path can expose the Retriever.** `_OFFICE_TOOL_NAMES` includes `odoo_record_retriever`; `_office_bind_tools()` binds the existing tool. Prior tests cover current-user ACLs and paging in [`test_native_chat_integration.py`](../../../../office_engine_m2/tests/test_native_chat_integration.py#L3699) and [`test_edit_orchestration.py`](../../../../office_engine_m2/tests/test_edit_orchestration.py#L164).

3. **The post-Current path intentionally removes Retriever access.** Once a Thread has an accepted versioned Current Workbook, `_prepare_chat_kwargs()` exposes only the `office` tool, and `_execute_tool_call()` rejects any other tool name: [`llm_thread.py`](../../../../office_engine_m2/models/llm_thread.py#L205), [`llm_thread.py`](../../../../office_engine_m2/models/llm_thread.py#L534). The routing test asserts the tool set is exactly `{"office"}`. Existing evidence records the test's successful run at [`candidate-b-tool-routing-test.log`](../CB-M2-CB-04/browser-simulation/candidate-b-tool-routing-test.log#L275).

4. **The `office` Facade has no data-read route.** Its public action schema is `status`, `plan`, `edit`, `accept`, or `reject` in [`office_mapping_tools.py`](../../../../office_engine_m2/models/office_mapping_tools.py#L1541). `dispatch_office_action()` has no branch that invokes `odoo_record_retriever`; it handles only those five actions in [`edit_orchestrator.py`](../../../../office_engine_m2/services/edit_orchestrator.py#L825).

5. **Existing tests show query behavior, not the requested multi-turn UI flow.** Current tests cover ORM permissions, pagination, relation reads, and M1 Retriever handoff. They do not establish a second Retriever read after an accepted versioned Current Workbook, nor a two-Candidate UI acceptance flow.

## Conclusion

**B. Only a minimal integration repair is indicated; do not implement the original snapshot framework.**

The existing Retriever can perform the data queries; a second ORM query service is not evidenced as necessary. The versioned Thread tool policy currently prevents the Agent from calling Retriever after the first Candidate has become Current, while the sole `office` Facade has no data-read action. This is the source-confirmed functional gap for the requested second-stage refresh.

The requested real-contact end-to-end scenario itself remains **unverified**: the local Mock endpoint was offline and the local ORM shell could not load `emoji`, so no contacts, workbook, Candidate, acceptance, or SHA values were produced. This report does not claim E2E PASS and does not claim that CC-05’s snapshot, incremental, or fingerprint mechanisms are required.

## Evidence limits

- No contact IDs or personal contact values were obtained.
- No real Provider or external service received Odoo data.
- The loopback Mock availability check sent no request body; no chat/model request was attempted.
- Existing automated tests and historical HVR logs are cited as prior evidence only, not as this run's results.
