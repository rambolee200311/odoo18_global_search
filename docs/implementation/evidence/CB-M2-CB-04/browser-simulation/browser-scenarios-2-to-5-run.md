# CC-M2-CB-04 Browser Simulation Run — Scenarios 2–5

- Date: 2026-11-09 (Odoo UI local time; approximately 4:26–4:28 PM)
- Environment: dedicated Odoo 8092 process, database `odoo18ce`, user `Mitchell Admin`
- Thread: `llm.thread_15154`; Session: `11628`
- Model shown in UI: `gpt-5.6-luna`
- Workbook: synthetic `Inventory` + `Notes` workbook; no customer or business data
- Candidate edit transport: process-only `CC-04 browser simulation adapter`; no external Provider file-edit request, no Responses/Code Interpreter editing
- Current version before these scenarios: V2 `687`, SHA-256 `82607bc498439cebe5a5b0cfd94a1ca182726b3127ad71d10d3b8922f4c8f092`
- Formal human HVR status: unchanged; all five manual entries remain `PENDING_MANUAL_VALIDATION`.

## Scenario 2 — Ambiguous request

User message: `帮我调整一下表格。`

The Agent asked which sheet/cell or range to modify, the desired value/header/formula, whether formatting should change, and whether rows/columns should be added, deleted, or sorted. No `office` tool call followed this message and no Candidate was produced at this point. The next plan (Scenario 3) remained bound to current version `687` and its SHA above.

Result: `SIMULATED PASS` for clarification/no edit. This is browser evidence, not human validation.

## Scenario 3 — Broad clear request and confirmation gate

Initial user message: `把现有数据全部清空`

The Agent first asked whether “all” meant every worksheet or only the current `Inventory` worksheet. The user selected all worksheets. The `office` tool call `call_2EJRvGgErDU3NSOQX6g72Mja` returned:

- `status=confirmation_required`
- `operation_status=plan_ready`
- `operation_executed=false`
- `requires_confirmation=true`
- Parent version `687`, input SHA equal to the current V2 SHA
- Bound scope: all worksheets; clear current cell values and formulas; retain worksheet/row/column structure and formatting
- A bound confirmation receipt and plan digest were returned

The Agent displayed the concrete risk and asked the user to confirm or reject. No Candidate was created before confirmation.

Result: `SIMULATED PASS` for clarification, risk disclosure, and no pre-confirmation edit. This is browser evidence, not human validation.

## Scenario 4 — Confirmed scope and execution result

The user replied `确认` to the immediately preceding, explicitly described whole-workbook clear plan. The `office` tool call `call_rPr95SZUsMYFbTY9x0K2abib` ran the candidate path and returned:

- `operation_executed=true`, Candidate version `688`, parent `687`
- Candidate SHA-256 `77cffdefa4da4d9a7e7c6d419d1e7e2fb175b5442371b3ea955fb11653e0fb36`
- Validation `PARTIALLY_VERIFIED`; Receipt SHA-256 `b0e70cc901d0d76f4fac84b6adb4e22321a0d5b0e65cc637c72faf4c3ae13e47`
- `actual_effects=[]`; unknown: exact populated-cell range was to be determined by candidate generation
- Current and Last Valid remained `687`; Document Revision remained `2`
- The Agent reported that clearing did not pass validation and the current workbook did not change

Independent Odoo ORM readback in `browser-scenario-independent-readback.log` verified the Candidate attachment SHA and ZIP integrity. Comparing V2 `687` to Candidate `688` yielded **zero cell-value/type/format differences**, with worksheet names unchanged. The requested clear therefore did not occur. The frozen validator correctly prevented a `PARTIALLY_VERIFIED` Candidate from becoming Current; the functional scenario did not pass. No out-of-scope workbook change was found.

Result: `PARTIAL / FUNCTIONAL FAIL; SAFETY GATE HELD`. This is browser plus independent ORM/XLSX evidence, not human validation.

## Scenario 5 — Sequential edit from the accepted header version

The browser composer retained the previous `确认` text; the visible submitted message was `确认把 Inventory 工作表的 B2 修改为 15，保留其他内容。` The structured Intent resolved to only `Inventory!B2 = 15`, and the resulting plan was bound to accepted version `687` (not failed, non-current Candidate `688`).

The `office` tool result reported:

- Candidate version `689`, parent `687`, state `accepted_current`
- Validation `VERIFIED`; Receipt SHA-256 `9a1fc6f0d068c440e8cc90f37e433ea1fd9aec5e78391524479ad7feaf2e1296`
- Input SHA-256 `82607bc498439cebe5a5b0cfd94a1ca182726b3127ad71d10d3b8922f4c8f092`
- Candidate SHA-256 `32e589004fa12e9b5907e419f58ae7b38cc9143e1c1c464300e8f38bfd505704`
- Actual effect: only `Inventory!B2`, numeric `10 → 15`
- Current/Last Valid advanced to `689`; Document Revision advanced to `3`
- `artifact_state=not_presented`, `delivery_state=not_finalized`; no download was performed

Independent Odoo ORM/openpyxl readback verified attachment SHA, ZIP integrity, worksheet names, all required cells and formula text. The only parent-to-candidate cell difference was `Inventory!B2` (same number format and style). The earlier accepted header edit remains in `Inventory!A1=产品编码`; `Inventory!B3=20`, formulas `D2 =B2*2` and `D3 =B3*2`, and Notes data remain unchanged.

Result: `SIMULATED PASS` for accepted-version continuity and effect containment; the composer prefix is recorded as a UI automation artifact. No Finalize/download or real Provider file edit was tested. This is not human validation.

## Evidence files

- Scenario 1 earlier independent comparison: `scene-1-accepted-version-diff-detail.txt`
- Scenarios 2–5 independent ORM/openpyxl readback: `browser-scenario-independent-readback.log`
- Readback script: `read_back_browser_scenarios.py`
- Candidate core-properties adapter regression: `candidate-core-properties-red.log`, `candidate-core-properties-green.log`
- Candidate B tool routing and contract tests: `candidate-b-tool-routing-test.log`, `candidate-b-tool-contract-tests.log`

The scenario 5 built-in-browser screenshot was captured in the CUA run. The current CUA capture interface did not persist it to a workspace file; no screenshot file is claimed in this evidence index.
