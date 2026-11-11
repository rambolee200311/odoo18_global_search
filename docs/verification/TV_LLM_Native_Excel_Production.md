# TV — LLM-Native Excel Content Production and Two-Round Editing

**Date:** 2026-11-10  
**Status:** Technical validation report; no formal Odoo code, configuration, or database changes made.  
**Scope:** `contact1.xlsx`, two consecutive Excel content-production/edit rounds, current-user Odoo contact reads, and source-level integration audit.

## Executive result

| Question | Result |
|---|---|
| Can the configured model produce an XLSX? | **VERIFIED** through Responses API + hosted Code Interpreter. A separate model-generated full-content descriptor + generic serializer route also produced a readable XLSX. |
| Did two consecutive content rounds run? | **VERIFIED** for isolated file-generation routes B and C. Round 2 used the actual Round 1 output as its input and retained A–C while adding D. |
| Did the complete Odoo UI → Candidate → Accept → Current → Finalize delivery flow run? | **NOT VERIFIED.** The public Odoo edit action remains fail-closed, and this TV did not register or accept versions or use the browser UI. |
| Can the current implementation accept a first model-produced file as V1 without M1? | **NOT VERIFIED / CURRENTLY UNSUPPORTED BY THE EXISTING ENTRY POINT.** `register_initial_v1` requires M1 validation proof; `register_candidate` requires an already accepted parent version. |
| Recommended next step | Use Route B as the leading implementation candidate, then add the smallest trusted first-file registration and public dispatch integration. Keep Current/Accept/Finalize and private attachment handling in Odoo. |

The actual file-generation capability is established. The remaining gap is connecting that capability to the Odoo version lifecycle from a raw first upload; it is not a lack of model ability to create a workbook.

## 1. Test authorization, environment, and privacy

- Used the existing `contact1.xlsx` supplied by the user. Input SHA-256: `673428f62dba4b77781951c343f193b77de450b715750225d7b19f2e3d006ff3`; 9,367 bytes; one sheet (`Sheet1`); source cells A1:C1 contain only the three supplied headers. The input file was not modified.
- Read three `res.partner` records through the existing Thread-bound `odoo_record_retriever` under the Thread owner’s Odoo user (user ID 2), using that user’s ORM access: record IDs `1`, `3`, and `7`. A second, independent Retriever call queried exactly those IDs and the address fields. Both calls returned three records. No business records were written.
- The user had explicitly authorized this bounded test using real contact data and the currently configured OpenAI Provider/model. The existing configured provider resolved to `gpt-5.6-luna` at `api.openai.com`; the API key was not displayed, copied, or written to evidence.
- Four sequential Responses API requests were made; SDK retries were disabled. Requests used `store=False`; hosted Code Interpreter containers were requested with networking disabled. Both containers were deleted successfully. No Odoo service restart, module upgrade, Git operation, or business-data write occurred.
- Personal contact values are deliberately omitted from this report. The generated files and raw model content are outside the repository under `/private/tmp/TV_LLM_Native_Excel_Production_20261110_01/`.

## 2. Route comparison and actual results

| Route | What the model receives/returns | Round 1 | Round 2 | Assessment |
|---|---|---|---|---|
| A. Native file input/output | Raw XLSX input and model-native binary XLSX output without an execution tool | XLSX file input is supported by the Responses file-input API. A separate no-tool binary XLSX output path was not demonstrated. | Not run as a distinct route. | **UNVERIFIED as a complete route.** Do not conflate it with Route B. |
| B. Model-driven hosted code execution | Raw XLSX + instruction + authorized data; model invokes hosted Code Interpreter and returns a real XLSX file | **PASS.** Actual Responses request returned XLSX bytes; independent ZIP/openpyxl checks confirmed the three records and original headers. | **PASS.** The exact Round 1 output bytes were passed as input. The model added the address column; A–C remained unchanged. | **VERIFIED for this simple two-round workbook.** No M1 `repeat_rows`, Mapping, fixed-cell rule, or local content-filling code was used. |
| C. Model-generated full workbook contents | Locally parsed workbook structure + authorized data go to the model; model returns the full sheet content; a generic serializer materializes XLSX | **PASS.** The model returned a complete four-row content description; the generic Artifact Tool serializer produced a valid XLSX. | **PASS.** The actual Route C Round 1 XLSX was parsed and supplied as the next-round state; the model returned the full updated content, which was serialized and independently read back. | **VERIFIED for this simple workbook.** This proves content authorship can stay with the model, but not preservation of arbitrary Excel-native features. |

Official documentation distinguishes Responses file input from Chat Completions file input, lists XLSX as a supported spreadsheet input, and describes Code Interpreter as a hosted environment that can process uploaded files and return generated files. The `gpt-5.6-luna` model page lists both Responses and Code Interpreter support. These are API/model capability facts; the successful Route B runs below are the actual access and output evidence for this configured Project. See [Responses file inputs](https://developers.openai.com/api/docs/guides/file-inputs), [Code Interpreter](https://developers.openai.com/api/docs/guides/tools-code-interpreter), and [GPT-5.6 Luna](https://developers.openai.com/api/docs/models/gpt-5.6-luna).

### Round 1: fill the original workbook

For Route B, the model received the raw original one-row `contact1.xlsx`, the user’s request, and the three records returned by the Retriever. For Route C, a local read-only parser supplied the original workbook’s sheet/header structure with the same request and records; the model generated the complete new sheet content. Both produced three data rows under the existing headers. The workbook did not need pre-existing A2 cells.

| Evidence | Route B | Route C |
|---|---|---|
| Provider request / response | `req_89b3f7905f074ccbac1a4864c80eda10` / `resp_0cfabb6e94767c64016af2e9a9aa2c87d28cd8fafee56ee3ae` | `req_2c1339f5f7094fa2af912df0ec343334` / `resp_0125a104102a6275016af2e9d11a7087d2832c6e4010416037` |
| Model-produced result | Provider Code Interpreter file `cfile_6af2e9ca74248191bd52be20f378e0c6`; 4 Code Interpreter calls | Complete model-produced sheet-content JSON; no Code Interpreter |
| Output | `route_b_v1.xlsx`, 6,938 bytes; SHA-256 `6d8ac35455f9904ec82f57bc9b7aae5d814c1bd92deb6f98d7c392210d965a55` | `route_c_v1.xlsx`, 3,575 bytes; SHA-256 `246584913373a949f9a83348e9f1d34f3273e8d68180955907bf3bd7b3300ec3` |
| Independent readback | **PASS:** ZIP/XLSX readable, header and three rows present, values match the Retriever results, sheet name preserved | **PASS:** ZIP/XLSX readable, header and three model-generated rows present; values match the Retriever results |

### Round 2: add addresses to the actual Round 1 workbook

The second Retriever query used domain `id in [1, 3, 7]`, with `id`, name/contact, and address fields. The returned identity set matched Round 1 exactly. Route B received the exact Route B Round 1 bytes. For Route C, the same actual Route C Round 1 workbook was locally read into its full content representation, which was supplied to the model as the next-round state.

| Evidence | Route B | Route C |
|---|---|---|
| Provider request / response | `req_15e2b56d3bdc4f079190f078da6b4680` / `resp_0311e7c8b586d6a0016af2ea2206d887d28dff209b1018fce8` | `req_c882d8105c474ac5a57d72e234af458e` / `resp_0961ca692e48c6d3016af2ea524f9087d2bc31732c18947ae3` |
| Input continuity | Input SHA equals Route B Round 1 output: `6d8ac35455f9904ec82f57bc9b7aae5d814c1bd92deb6f98d7c392210d965a55` | Input workbook SHA: `246584913373a949f9a83348e9f1d34f3273e8d68180955907bf3bd7b3300ec3` |
| Model-produced result | Provider Code Interpreter file `cfile_6af2ea4cc2b8819185614a995d8e12b8`; 10 Code Interpreter calls | Complete model-produced updated sheet-content JSON; no Code Interpreter |
| Output | `route_b_v2.xlsx`, 7,102 bytes; SHA-256 `5cf62d4f907dce0dd29b25f5d4fab8f9f06cafd968501449aac8d0e00cb3e53f` | `route_c_v2.xlsx`, 3,726 bytes; SHA-256 `ff2b74f3784e9d23d7db7064a3b725298eec7db33485a22717b245b6e4f15cbc` |
| Independent readback | **PASS:** A–C unchanged from Route B Round 1; D1 is `地址`; D2:D4 match the second Retriever result; ZIP/XLSX and sheet names valid | **PASS:** A–C unchanged from Route C Round 1; D1 is `地址`; addresses match the second Retriever result; ZIP/XLSX valid |

The Route B and Route C workbooks also matched each other cell-for-cell for A–C in Round 1 and A–D in Round 2. These are file-content results only: neither route registered a Candidate or changed Current/Last Valid/Revision.

### Requests, usage, and hosted resources

- Total: 4 sequential Responses creation requests, 0 automatic retries; 2 hosted Code Interpreter containers, 14 total Code Interpreter calls; both containers cleaned up successfully.
- Recorded token usage: 15,349 input tokens and 4,901 output tokens (20,250 total). This is API usage evidence, not an account invoice. Total billed cost, including any tool/container charge, is **UNVERIFIED**.
- Route B Response `store=False`; Route C Response `store=False`. Code Interpreter’s hosted environment is separate from the Odoo process. The tested request disabled container network access. This does not establish an organization-wide retention guarantee; it records the specific request settings and observed container cleanup.

## 3. Complex workbook capability boundary

This TV workbook contains a single sheet with three headers and no formulas, styles, merged cells, tables, named ranges, hidden rows/columns, charts, or external links. Therefore the following are **not established by this TV**:

| Feature | Status in this TV | Evidence boundary |
|---|---|---|
| Basic cell values and adding rows/columns | **VERIFIED** | Both routes completed two rounds on the supplied one-sheet workbook. |
| Multiple worksheets | **UNVERIFIED** | Not present in this fixture. Existing CB-01 synthetic testing preserves a two-sheet fixture in one separate edit case; that is not proof of arbitrary multi-sheet fidelity for these two routes. |
| Formulas and cross-sheet references | **UNVERIFIED for this task** | No formulas in `contact1.xlsx`; no recalculation claim. CB-01 synthetic fixture readback preserves formula text in a different test. |
| Styles and number formats | **UNVERIFIED** | No meaningful style-change requirement in this fixture. |
| Merged cells, tables, named ranges, hidden rows/columns | **UNVERIFIED** | Not tested here. |
| Charts, pivots, external links, macros, embedded objects | **UNVERIFIED** | Not tested; no complete preservation guarantee is made. |
| Large workbooks | **UNVERIFIED** | No scale test was run. The official spreadsheet file-input guide describes parsing up to the first 1,000 rows per sheet; this is not a guarantee that every larger workbook’s complete state is available to the model. |

No complexity-based route switching is proposed. The tested evidence does not establish that either approach preserves all workbook features. A production verifier must report unsupported or changed features accurately rather than equating “opens successfully” with complete fidelity.

## 4. Actual Odoo call path and integration gap

### Reused components

- `llm_record_retriever` can read the current user’s permitted Odoo records using ORM and serializes the result for the model. The two TV reads returned actual current-user records and the second query reused their IDs.
- The configured OpenAI SDK client and `ResponsesAdapter` are reusable. The Adapter accepts XLSX bytes and an instruction; it uses Responses `input_file` plus hosted Code Interpreter and returns downloaded candidate bytes and metadata.
- The existing M2 code has `office.retrieve`, edit/validate/review, Candidate acceptance, accepted Current, and Finalize/delivery paths. Once a versioned accepted parent exists, the Candidate/Accept/Finalize services can be reused.
- The only M2-facing tool is `office`; no new public tool is needed.

### Current constraints confirmed in code

1. `openai_provider.py::openai_chat` uses `client.chat.completions.create()`; the normal Chat Completions provider path has no XLSX upload/download implementation.
2. The separate Responses Adapter does have real XLSX input/output support, but the public M2 edit dispatcher is fail-closed: `EXTERNAL_PROVIDER_DISPATCH_ENABLED = False`, and the public `edit` path returns `external_file_processing_not_authorized` when trusted adapter dependencies are absent. The public edit route was not enabled or called in this TV.
3. The existing first-version function, `register_initial_v1`, only registers an M1 output with persistent M1 validation proof tied to the Session/request. It cannot register a newly model-produced first workbook without that M1 proof.
4. `register_candidate` requires its parent to be an already accepted current/finalized version. It cannot create the initial version from a raw upload.
5. Consequently, raw upload → model-produced first workbook → Odoo V1/Current is not available through the existing production version entry points without a small, new trusted initialization path or a formally amended existing one. This is the concrete integration blocker; the LLM file production itself passed.
6. Once a valid Current exists, `register_candidate` and `accept_verified_candidate` bind the actual file bytes/hash and parent version; the latter supports user-authorized `PARTIALLY_VERIFIED` without changing its grade. Finalize can deliver an already accepted Current through the existing attachment/message mechanism.
7. Local validation is not only observational in the current edit path: `validate_workbook_candidate` creates a typed receipt, and the orchestrator returns a failure and disallows acceptance when CB-03 reports `FAILED`. This is a governance gate, not a content-production mechanism. Prior CC-04 evidence records that legitimate XLSX dimension/default-style serialization was once falsely rejected and was corrected generically; this TV did not test complex-file validation behavior.

Relevant code: `mymodules/odoo-llm/llm_openai/models/openai_provider.py`; `mymodules/odoo-llm/llm_openai/services/responses_adapter.py`; `mymodules/office_engine_m2/services/edit_orchestrator.py`; `mymodules/office_engine_m2/services/candidate_validator.py`; `mymodules/office_engine_m2/services/workbook_version_service.py`.

## 5. Route recommendation and minimum implementation estimate

### Recommendation

**Route B is the best evidenced leading route for implementation validation.** It already has a working Responses Adapter, produced real XLSX bytes on two consecutive requests, and can use the previous actual XLSX as the next input. It requires less new workbook-content protocol than Route C. The hosted execution boundary is provider-managed; the Odoo service itself did not execute generated code. The exercised request disabled container networking.

Route C is also feasible for simple grids, but it needs a generic workbook-to-content representation and a generic serializer. This test proves those can handle the present small fixture; it does not prove faithful round-tripping of arbitrary Excel features. Route A as a complete binary in/out path remains unverified.

### Minimum code changes indicated by current evidence

This is an estimate, not an implementation result:

1. Add a trusted initial-file registration path for model-produced XLSX bytes, with the same user/Thread/attachment/hash and technical validation ownership required for V1. Keep it separate from M1 Mapping semantics; do not let a client write Current pointers directly.
2. Connect the existing public `office` edit action to the configured Responses Adapter under an explicitly approved external-processing gate. This must not run model-generated code in Odoo.
3. Allow an uploaded raw workbook to enter the first-file flow before a version exists, then feed the returned candidate through the trusted initialization/acceptance sequence. Subsequent rounds can use existing parent-version Candidate/Accept paths.
4. Add integration tests for first-file initialization, two sequential edits, refusal/failure state preservation, and Finalize/download. No new query service or public Tool is indicated.

**Effort estimate (`INFERRED`):** approximately **5–9 engineer-days** for a minimal end-to-end integration: 2–4 days for the trusted initial-file/public dispatch connection, 2–3 days for Odoo integration and security/state tests, and 1–2 days for runtime acceptance. This has moderate uncertainty because the initial V1 proof model and external-processing policy are unresolved implementation decisions. It is not a measured estimate or approval to start coding.

## 6. Evidence index and exact output files

Evidence directory: `/private/tmp/TV_LLM_Native_Excel_Production_20261110_01/`.

| Artifact | SHA-256 |
|---|---|
| Original `/Users/lijianqiang/Documents/contact1.xlsx` (not modified) | `673428f62dba4b77781951c343f193b77de450b715750225d7b19f2e3d006ff3` |
| [Route B Round 1 XLSX](/private/tmp/TV_LLM_Native_Excel_Production_20261110_01/route_b_v1.xlsx) | `6d8ac35455f9904ec82f57bc9b7aae5d814c1bd92deb6f98d7c392210d965a55` |
| [Route B Round 2 XLSX](/private/tmp/TV_LLM_Native_Excel_Production_20261110_01/route_b_v2.xlsx) | `5cf62d4f907dce0dd29b25f5d4fab8f9f06cafd968501449aac8d0e00cb3e53f` |
| [Route C Round 1 XLSX](/private/tmp/TV_LLM_Native_Excel_Production_20261110_01/route_c_v1.xlsx) | `246584913373a949f9a83348e9f1d34f3273e8d68180955907bf3bd7b3300ec3` |
| [Route C Round 2 XLSX](/private/tmp/TV_LLM_Native_Excel_Production_20261110_01/route_c_v2.xlsx) | `ff2b74f3784e9d23d7db7064a3b725298eec7db33485a22717b245b6e4f15cbc` |

The temporary evidence directory also contains the two bounded runner scripts, request metadata, and model-generated Route C content descriptors. These remain outside the repository because they contain real contact data. No raw contact values or credentials are included in this report.

## Final answers

1. **Can the current model actually produce XLSX? — VERIFIED.** Route B returned real XLSX bytes through hosted Code Interpreter. Route C also produced readable files through model-generated complete content plus generic serialization. A separate no-tool binary output route is not verified.
2. **What makes the LLM lead production? — VERIFIED for Routes B/C.** In B, the model read/edited the input workbook in the hosted execution tool. In C, the model generated the full cell content; the local serializer only materialized that content into XLSX.
3. **Did two contact rounds actually run? — VERIFIED at isolated Provider/file level; NOT VERIFIED through Odoo Candidate/Accept/Current.** Both rounds performed actual Retriever reads and actual model calls, and both output files passed independent readback. No persisted versions were created.
4. **Which governance services can be reused? — VERIFIED by source audit.** Current-user Retriever/ORM, Responses Adapter, Candidate/Validator, version acceptance, Finalize, private attachments, and the single `office` Tool exist. Their normal public edit connection remains gated, and first V1 registration remains M1-proof-only.
5. **How much implementation is needed? — INFERRED, 5–9 engineer-days.** The core provider and downstream version/delivery services exist; the main missing pieces are the first-file registration path and trusted public dispatch integration, plus focused Odoo integration and end-to-end validation.

**Overall TV conclusion:** the technical premise “LLM can produce and continuously edit Excel content while Odoo governs access, versions, review, and delivery” is **VERIFIED for a simple workbook at isolated file level**. The complete Odoo product flow and fidelity for complex Excel constructs remain **UNVERIFIED**. No formal implementation or production activation is authorized by this report.
