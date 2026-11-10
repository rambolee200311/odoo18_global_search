# CB-06 Synthetic UI HVR — 2026-11-10

## Environment and boundary

- Odoo 18 CE, non-production database `odoo18ce`.
- Dedicated test server: `127.0.0.1:8092`; existing 8091 was not restarted.
- Logged-in user: Mitchell Admin.
- Thread: `llm.thread_15880`; Session: `12212`.
- Workbook candidates were produced by the existing local test adapter. No XLSX bytes were sent to Responses API / Code Interpreter. The chat model processed synthetic text and tool orchestration.
- No business records were modified. No module upgrade or Git operation was performed.

## Version and UI action evidence

| Step | Version/Candidate | Parent | Input SHA-256 | Output / attachment SHA-256 | UI/tool evidence | State after action |
|---|---:|---:|---|---|---|---|
| Initial workbook V1 | 1175 | — | — | `7d4b731af6e2905241f4f70457dc82867722cfc5b761be2312cb0d801cd6f2d8` | Existing HVR record; finalize call `call_wAGsDCIW93W4NLjf613SyW5T` | Current=Last Valid=1175; Revision=1 |
| A1 edit V2 | 1176 | 1175 | `7d4b731af6e2905241f4f70457dc82867722cfc5b761be2312cb0d801cd6f2d8` | `5c5c35508f076884f6450ee04409a59796920ef3540297e268bd84a69efa95f4` | Plan/edit calls `call_4ummvAHCsh9peoUd0NJhcfpF`, `call_HkyFQ532rM5aNwiKPqK63tcH`; accept `call_TzYomiNqomqJg0y6V3ImmbCZ` | Current=Last Valid=1176; Revision=2 |
| A2 edit/accept V3 | 1464 | 1176 | `5c5c35508f076884f6450ee04409a59796920ef3540297e268bd84a69efa95f4` | `f97014323e07563f7cbee3d0c37c3fd831e3cba48cbeaa8afc431ed312e909e9` | UI acceptance call `call_B095VQIjhRMNRQDPUz3lM4mC` | Current=Last Valid=1464; Revision=3; validation remains `PARTIALLY_VERIFIED` |
| A3 edit/reject V4 | 1561 | 1464 | `f97014323e07563f7cbee3d0c37c3fd831e3cba48cbeaa8afc431ed312e909e9` | `8bb6257f8c3df1350b203053d175dbb793c69f3c0eceaa2d1233df6ac5721fbb` | Plan/edit calls `call_TPZVDDNjKf5sBejDF3rPLqax`, `call_Qm3agQSzjfuDkEJ6Qmz83qDZ`; UI rejection call `call_EC1WAltBjkFlN0peF1sL4oYk` | Candidate= rejected; Current=Last Valid=1464; Revision=3 |

## Independent XLSX readback

- V3 / version 1464: `Inventory!A1=15`, `A2=20`, `C1` formula `=A1*2`; ZIP/XLSX readable.
- V4 / candidate 1561: `Inventory!A1=15`, `A2=20`, `A3=30`, `C1` formula `=A1*2`; ZIP/XLSX readable.
- V4 attachment SHA-256 matched the candidate output SHA-256.
- ORM readback was read-only and used as content/identity evidence only; it is not counted as UI download or user review.

## Final ORM state readback

Read-only query on 2026-11-10 after UI rejection:

```text
(1464, 'accepted_current', 'PARTIALLY_VERIFIED', 1176,
 '5c5c35508f076884f6450ee04409a59796920ef3540297e268bd84a69efa95f4',
 'f97014323e07563f7cbee3d0c37c3fd831e3cba48cbeaa8afc431ed312e909e9',
 12212, 1464, 1464, 3)
(1561, 'rejected', 'PARTIALLY_VERIFIED', 1464,
 'f97014323e07563f7cbee3d0c37c3fd831e3cba48cbeaa8afc431ed312e909e9',
 '8bb6257f8c3df1350b203053d175dbb793c69f3c0eceaa2d1233df6ac5721fbb',
 12212, 1464, 1464, 3)
```

Column order: version ID, state, validation result, parent version, input SHA-256, output SHA-256, Session ID, Current version ID, Last Valid version ID, Document Revision.

## Outcome

- A1→V2 acceptance: PASS (existing UI evidence).
- A2→V3 acceptance and Current advancement: PASS (UI/Agent/`office` tool; local test adapter generated file).
- Rejection of V4 with Current unchanged: PASS (UI/Agent/`office` tool).
- Candidate UI download and user opening: **FAIL**. The UI did not provide a usable clickable attachment link. ORM readback does not substitute for this requirement.
- Full “view then accept” UI closure: **not passed** because of HVR-02.
- No claim of real Responses API XLSX editing.
