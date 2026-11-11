# IHR-M2-CB-06 — Finalize / Attachment Delivery

**Contract:** `CC-M2-CB-06_Finalize_Attachment_Delivery_v0.2.md`
**Status:** Implementation complete; HVR partially verified; not yet ready for Final Acceptance.
**Database:** Existing development database `odoo18ce`.

## Implementation

Candidate B now exposes `office(action="finalize")` through the existing single `office` Tool. The service resolves the current accepted version from the trusted Thread/Session context, rechecks current/last-valid/revision, private attachment binding and SHA, then reuses the accepted version attachment in an assistant message on the same Thread and registers it through `record_finalize_reference`.

Finalize does not edit bytes, create a version, move Current/Last Valid, increment Document Revision, rerun CB-03, or upgrade validation grade. It accepts both `VERIFIED` and an already accepted `PARTIALLY_VERIFIED` Current and preserves the original grade. Repeated delivery reuses the same message and attachment.

Files changed for implementation:

- `mymodules/office_engine_m2/services/workbook_version_service.py`
- `mymodules/office_engine_m2/services/edit_orchestrator.py`
- `mymodules/office_engine_m2/models/office_mapping_tools.py`
- `mymodules/office_engine_m2/models/llm_thread.py`
- `mymodules/office_engine_m2/tests/test_workbook_version_state.py`
- `mymodules/office_engine_m2/tests/test_edit_orchestration.py`
- `mymodules/office_engine_m2/tests/test_native_chat_integration.py`
- `docs/design/TDD_office_engine_m2_v2.0.4_CB06_Amendment.md`

The TDD amendment is narrowly limited to the v0.2 decision that a formally accepted PARTIALLY_VERIFIED Current may be delivered without revalidation or grade promotion. M1 `office_finalize`, CB-02 version acceptance, CB-03 validation, and the single public Tool boundary remain unchanged.

## Runtime and Odoo UI execution

The existing `odoo18ce` server on port 8091 was restarted using `odoo.conf` to load the implementation. No module upgrade was run. A current-user Discuss session opened synthetic Thread `15880` (Session `12212`) and submitted a finalize instruction for its already accepted Current `1464`. The UI agent invoked `office` once with `{"action":"finalize"}` (tool call `call_PbQQIr6GtcUPhMxwkcLortkD`). Odoo returned `completed / finalized / delivered`, and Discuss displayed the `cb04-synthetic-candidate.xlsx` XLSX attachment card.

The UI scenario and exact result are recorded in `HVR-M2-CB-06.md`. Current/Last Valid remained `1464`, Document Revision remained `3`, and the grade remained `PARTIALLY_VERIFIED`. The server-side attachment was independently read as the Thread owner and matched the version SHA. The in-app browser download button was clicked, but the browser harness did not expose a downloaded file or HTTP result; a direct endpoint navigation was blocked by the browser client. Therefore this is not recorded as a successful browser-download/readback HVR.

## Runtime state

- 8091 now runs the current workspace code against the existing `odoo18ce` database; startup log: `evidence/CB-M2-CB-06/odoo-8091-hvr.log`.
- The startup log contains unrelated unavailable-addon/missing-model errors for `wd_advanced_m2o_record_panel`, `wd_evidence_album`, and `wd_qooling_app`; the M2 modules loaded and the requested UI flow succeeded.
- No schema upgrade, production data operation, Candidate edit, or git write operation was performed in this implementation run.
- One chat turn used the Thread's configured OpenAI Chat Completions provider to interpret the text-only finalize request. The workbook bytes were not uploaded to the Provider; the `office` service read the Odoo attachment locally. No Responses API / Code Interpreter file-edit request was made.

See ATR, HVR, and FR for verification details and remaining acceptance evidence.
