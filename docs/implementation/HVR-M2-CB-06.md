# HVR-M2-CB-06 — Finalize / Attachment Delivery

**Verification type:** Odoo Discuss UI using the current authenticated user; synthetic workbook already stored in Odoo.
**Status:** **PARTIAL — UI Finalize and attachment card PASS; browser download evidence BLOCKED/UNVERIFIED.**
**Date:** 2026-11-10.

## Scenario record

| Item | Actual evidence |
|---|---|
| Environment | Odoo 18 CE, `odoo18ce`, local 8091; current Discuss user shown as Mitchell Admin. Server was restarted with existing `odoo.conf` so the UI used the new code; no module upgrade. |
| Thread / Session | Thread `15880`; Session `12212`. Existing synthetic HVR Thread; no business workbook/data used. |
| Accepted Current | Version `1464`, version no. `5`, parent version `1176`, validation grade `PARTIALLY_VERIFIED`. |
| User message | “请正式交付当前已接受的合成工作簿版本（Current 1464）。不要编辑、接受或拒绝任何候选；只执行 office(action="finalize")，交付到当前 Thread。完成后如实说明结果。” |
| Agent Tool call | Public Tool `office`; call ID `call_PbQQIr6GtcUPhMxwkcLortkD`; arguments `{"action":"finalize"}`. The Thread's configured OpenAI chat model returned the Tool call. The workbook was not uploaded to the Provider. |
| Tool result | `status=completed`, `operation_status=finalized`, `artifact_state=finalized`, `delivery_state=delivered`, `operation_executed=true`; version `1464`; Current=Last Valid=`1464`; Document Revision=`3`; grade `PARTIALLY_VERIFIED`; `attachment_posted_to_thread=true`; attachment `39747`; delivery message `101090`; SHA-256 `f97014323e07563f7cbee3d0c37c3fd831e3cba48cbeaa8afc431ed312e909e9`. |
| Discuss card | **PASS.** UI displayed an XLSX card named `cb04-synthetic-candidate.xlsx` with a Download control and a message stating the accepted version was attached. Screenshot observation is present in the task trace; Odoo UI tab remains available for handoff. |
| Download | **BLOCKED/UNVERIFIED.** The attachment card's Download control was clicked in the UI. The in-app browser did not expose a resulting local file or HTTP status. Opening the known content endpoint in a separate IAB tab was blocked by the browser client, so that attempt is not counted as a download. |
| Independent byte readback | **PASS for stored attachment, not browser-download evidence.** As the Thread owner, read `ir.attachment.raw`; actual SHA matched `office.workbook.version.output_sha256`. A local evidence copy was parsed by `openpyxl`. |
| Workbook content | Inventory: A1=`15`, A2=`20`, C1=`=A1*2`; Notes: A1=`Synthetic HVR fixture`, A2=`Protected value`. XLSX opened successfully. |
| Final database state | Version `1464` state=`finalized`; delivery=`delivered`; attachment is private; message `101090` is assistant role on Thread `15880` and includes attachment `39747`. Current=Last Valid=`1464`; revision `3`; SHA and validation grade unchanged. |

The finalization UI turn made two Chat Completions requests in the configured assistant loop. Only the text instruction and existing synthetic Thread context were sent; the workbook binary remained in Odoo and was read by the local `office` service. No Responses API / Code Interpreter request was made.

## Scenario disposition

| CC-06 HVR scenario | Result | Notes |
|---|---|---|
| A — Finalize accepted Current | **PASS** | Real UI request called the public `office` action and returned completed/finalized/delivered. |
| B — Thread attachment card | **PASS** | Card visible in Discuss; private attachment/message binding verified. Browser download HTTP/file capture remains unverified. |
| C — CC-05 two-stage contact workbook final V3 delivery | **NOT RUN** | This run delivered the existing synthetic Inventory workbook, not the CC-05 contact workbook. Automated CB-06 tests cover delivery services; they do not replace this HVR case. |
| D — Duplicate UI delivery | **NOT RUN in UI; PASS in automated test** | TransactionCase verified same attachment/message reuse and no duplicate delivery record. |

## Evidence files

- `evidence/CB-M2-CB-06/odoo-8091-hvr.log` — service start and assistant provider requests.
- `evidence/CB-M2-CB-06/readback_finalize_20261110.py` — read-only current-user ORM verification and workbook extraction.
- `evidence/CB-M2-CB-06/readback_finalize_20261110_retry1.log` — record binding, SHA and independent XLSX values.
- `evidence/CB-M2-CB-06/finalized-current-1464.xlsx` — local readback copy of the same private Odoo attachment bytes; not a browser download artifact.
- `evidence/CB-M2-CB-06/readback_finalize_20261110.log` preserves the first failed readback-script attempt (incorrect use of `env["user"]`); retry corrected the script and passed.

## HVR conclusion

Finalize execution and Thread attachment-card creation are confirmed. The stored attachment bytes, Current/Last Valid pointers, revision, SHA, private access flag, and original partial-validation grade are consistent. The browser download result and CC-05 contact-workbook final delivery scenario remain unverified, so full CC-06 HVR and Final Acceptance are not claimed.
