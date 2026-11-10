# Office Engine M2 TV Phase 1A-2 Report v0.2

**Status:** Completed for the authorized minimal Candidate B capability test. This report supplements and does not replace the earlier v0.1 report.

**Scope:** One synthetic XLSX edit using the configured Odoo OpenAI Provider, Responses API, and Code Interpreter. No business data, Odoo production code, or service restart was involved.

## 1. Outcome

| Capability | Result | Evidence |
|---|---|---|
| Responses API route | `SUPPORTED` | Three actual requests returned Responses objects from the configured provider. |
| XLSX input | `SUPPORTED` | The synthetic workbook was sent as an inline `input_file` data URL. |
| `gpt-5.6-luna` + Code Interpreter | `SUPPORTED` | All three Responses requests used the approved model; Code Interpreter calls appeared in each response. |
| Current Provider credential / model access | `PASS` | The active default OpenAI chat model was unique and the real requests were accepted. The key value was never read into output or logs. |
| Actual XLSX edit and file return | `PASS` | Attempt 3 returned a container file citation; its actual bytes were downloaded and independently read. |
| Independent workbook verification | `PASS` | All required cell, formula-text, style, non-target and ZIP assertions passed. |
| Multi-turn editing | `NOT RUN` | This authorization covered a minimal single-edit capability proof, not multi-turn TV-LE-03. |
| Exact billed invoice amount | `UNVERIFIED` | Provider token usage was returned and priced from the published rate card; no billing dashboard or invoice endpoint was queried. A conservative reserve remained under the $2 cap. |
| Odoo Chat UI integration | `NOT RUN` | This was a direct Responses API test through the current Provider client, not a change to the existing Chat Completions UI path. |

**Conclusion:** Candidate B can perform a simple, model-driven XLSX edit and return a valid workbook through the current OpenAI Responses/Code Interpreter route. This does not establish multi-turn continuity, complex structure fidelity, confirmation behavior, Finalize, or browser delivery.

## 2. G0 — Execution Gates

### Workspace and environment

- Branch: `main`
- HEAD before the test: `f9801fca76f7c248a9cc823c583138ab0191b978`
- Existing untracked work was present before the task and preserved. The v0.1 Phase 1A-2 report and earlier TV evidence were not overwritten.
- Python: 3.11.9 from the repository `venv`.
- OpenAI Python SDK: 2.54.0.
- openpyxl: 3.1.5.
- The existing Odoo listener on port 8091 was not restarted. No Odoo production code was modified.

### Provider selection and credential handling

A read-only Odoo ORM query found exactly one active, default `gpt-5.6-luna` chat model attached to an active OpenAI Provider. The Provider has a configured credential and its API base was checked in memory against the standard HTTPS `api.openai.com/v1` shape. Neither the credential value nor the literal API base was emitted by the probe. The test obtained the client through the Provider's existing `provider.client` property and set SDK retries to zero.

The Odoo `llm.provider` model has no explicit API Project ID field. The Project ID therefore remains `UNVERIFIED`; successful real calls establish that the current Provider credential is authorized for the selected model and endpoint. The exact project identifier was not inferred from the credential.

The first shell attempt using system Python failed because the environment lacked the Odoo dependency `emoji`. A retry with the repository venv succeeded. A sandboxed attempt also hit a macOS process-enumeration permission error; the authorized elevated read-only shell was then used. These failures occurred before any API test request and caused no database writes.

### Budget gate

Before the first API request, the run reserved a conservative maximum of 1,000,000 input tokens priced at the model's high-context multiplier, the per-attempt output token cap, four 1 GB Code Interpreter 20-minute billing units per container, and a 10% margin. The maximum preflight reserve across the three authorized Responses requests was about **$0.85**, below the **$2.00** cap. The input workbook was only 5,708 bytes and contained two sheets with three rows each. Each client used a 120-second timeout and `max_retries=0`; no further Responses request was made after the third.

The Code Interpreter `max_tool_calls=1` request parameter did not consistently limit actual Code Interpreter calls (observed counts were 4, 1, and 2). This is recorded as a control limitation. Calls in each Response shared one 1 GB container, each completed synchronously in under 28 seconds, and each container was deleted. The API Responses request count remained exactly three. The actual token charges calculated from returned usage total about **$0.005212**. A four-session-unit reserve for each of the three containers is **$0.36**; with token cost and 10% margin the conservative total is **$0.401733**. The exact invoice amount was not queried.

## 3. Official API and SDK Evidence

- OpenAI's [File Inputs guide](https://developers.openai.com/api/docs/guides/file-inputs) lists `.xlsx` as an accepted Responses API spreadsheet input. It documents spreadsheet augmentation over up to the first 1,000 rows per sheet and distinguishes this from Chat Completions file input support.
- OpenAI's [GPT-5.6 Luna model page](https://developers.openai.com/api/docs/models/gpt-5.6-luna) lists the Responses endpoint and Code Interpreter as supported. The page lists standard token prices of $0.20 per million input tokens and $1.20 per million output tokens; long-context price multipliers were applied conservatively where relevant.
- The [Code Interpreter guide](https://developers.openai.com/api/docs/guides/tools-code-interpreter) documents container file citations, the `container_id` / `file_id` output metadata, automatic availability of input files in the container, and retrieving generated file content.
- The [API pricing page](https://developers.openai.com/api/docs/pricing) lists a 1 GB Hosted Shell / Code Interpreter container at $0.03 per 20-minute session, billed by the minute with a five-minute minimum.
- The installed SDK 2.54.0 exposes `responses.create`, `max_output_tokens`, `max_tool_calls`, container file retrieval, and container/response deletion. SDK support alone was not treated as proof; the real requests below supplied runtime evidence.

## 4. Synthetic Input and Real API Attempts

The fixture contains `Inventory` and `Notes` worksheets. `Inventory` contains ITEM-A (quantity 10, unit price 5, formula `=B2*C2`) and ITEM-B (quantity 20, unit price 8, formula `=B3*C3`). `Notes` contains `Source / Synthetic TV` and `Status / Original`. The workbook uses distinct header and numeric formats. It contains no Odoo, customer, or commercial data.

The XLSX was sent inline in the Responses request as `file_data`; a separate Files API upload was not made. The Code Interpreter automatically received the input. Attempts 1 and 2 used `store=False`; attempt 3 used the default stored Response so the returned artifact could be inspected, then the Response and its container were deleted.

| Attempt | Request / response IDs | Response status; usage | Code Interpreter calls | File result and cleanup |
|---|---|---|---:|---|
| 1 | Request `req_60f6d439fc894d47a484d2f0b0332ef6`; response `resp_058495d0a11bd388016aed4561868c87d2a71d0460cf44ed0e` | `incomplete`; 3,081 input / 1,200 output tokens; estimated token cost $0.0020562 | 4 | No XLSX citation. Container `cntr_6aed456643d081918ff6b94e40e04a7504c5038c6ba09a5f` deleted successfully. |
| 2 | Request `req_897c5357c50e4bf78c95d8bd77f337b8`; response `resp_0b660b22ec63b11a016aed45ed596087d2b4d69ba18924e01c` | `completed`; 2,079 input / 650 output tokens; estimated token cost $0.0011958 | 1 | No XLSX citation or returned file. Container `cntr_6aed45efdb548191ac67229660f727ff046b7d23d227b331` deleted successfully. |
| 3 | Request `req_4cbc6f75ebb34bb69107ecd35a4954d3`; response `resp_011d206f3d9927e8006aed466e8ac887d2a38b11166f168488` | `completed`; 3,056 input / 1,124 output tokens; estimated token cost $0.0019600 | 2 | Returned `tv_phase1a2_output.xlsx`, file `cfile_6aed467d692481919173fea2a018143d`, from container `cntr_6aed4671001c81918746632af73ab2130f84aaab865e1536`; downloaded, independently validated, then container and Response deleted successfully. |

All three Response objects reported model `gpt-5.6-luna`. No automatic retry was enabled. Tool call IDs are retained in `attempt1_run_result.json`, `attempt2_run_result.json`, and `attempt3_run_result.json`; they are also listed here for audit:

- Attempt 1: `ci_058495d0a11bd388016aed456b805487d2b17c2809bb63b38c`, `ci_058495d0a11bd388016aed457112e487d2a3c8393a1b8887fe`, `ci_058495d0a11bd388016aed45760d0c87d2aa3c6f64c386e9e3`, `ci_058495d0a11bd388016aed457a87f487d29bba9c3bdfdb770d`.
- Attempt 2: `ci_0b660b22ec63b11a016aed45f402f887d2a9269d250893c03d`.
- Attempt 3: `ci_011d206f3d9927e8006aed4674da1487d2b39801afb9a0ca3f`, `ci_011d206f3d9927e8006aed4679630887d296461ea7bc36238d`.

There were three Responses test requests and five supporting HTTP operations (two container deletions after attempts 1/2, then one download, one container deletion, and one Response deletion after attempt 3): eight API operations in total. No separate Files API upload was used. No further Provider request is authorized or planned in this run.

## 5. File Evidence and Independent Readback

| File | Size | SHA-256 |
|---|---:|---|
| `evidence/TV_LLM_OFFICE_EDITING_PHASE1A2/tv_phase1a2_input.xlsx` | 5,708 bytes | `5a246ca4c8539ea723294d08689a63731c560b9e9fc87d3100ea0c49a9bb32a0` |
| `evidence/TV_LLM_OFFICE_EDITING_PHASE1A2/tv_phase1a2_output.xlsx` | 5,713 bytes | `3981e64c9c8caa9c01a18f256b67150c529243d86dbe1abdc663e212ffa52567` |

The returned output file was independently downloaded from the container content endpoint and read locally with openpyxl in a separate verification command. Both input and output ZIP containers passed `ZipFile.testzip()`.

| Check | Actual result |
|---|---|
| `Inventory!B2` | Numeric `15` (requested change from 10) |
| `Inventory!B3` | `20` (unchanged) |
| `Inventory!D2` | `=B2*C2` (formula text preserved) |
| `Inventory!D3` | `=B3*C3` (formula text preserved) |
| `Notes!B2` / `Notes!B3` | `Synthetic TV` / `Original` (unchanged) |
| Worksheet names and order | `Inventory`, `Notes` (unchanged) |
| Other cell values and types | No differences outside the requested target |
| Styles and number formats | No differences |
| Sheet dimensions, visibility, merged ranges and defined names | Unchanged |
| ZIP/XLSX integrity | Valid |

Formula text and references were checked; **formula recalculation was not tested**. No spreadsheet engine was used to calculate the formulas.

## 6. Cleanup and Evidence Files

All three Code Interpreter containers were deleted successfully. The stored Response from attempt 3 was deleted successfully. The input was passed inline rather than uploaded through the Files API, so there was no separate Files API file object to delete. Attempts 1 and 2 were created with `store=False`. Local synthetic input/output files and the sanitized logs are retained as requested test evidence.

Evidence directory: `docs/verification/evidence/TV_LLM_OFFICE_EDITING_PHASE1A2/`

- `run_candidate_b.py` — bounded single-request runner used for attempt 1.
- `attempt2_in_odoo_shell.py` — second request runner.
- `attempt3_in_odoo_shell.py` — final request, artifact download, and cleanup runner.
- `tv_phase1a2_input.xlsx`, `tv_phase1a2_output.xlsx` — synthetic input and returned output.
- `input_manifest.json` — input workbook structure and target baseline.
- `attempt1_run_result.json`, `attempt2_run_result.json`, `attempt3_run_result.json` — sanitized response metadata, IDs, usage, checks, and cleanup status.

No API key, Authorization header, cookie, business record, or response prompt/body was written to the logs.

## 7. Remaining Limits and Recommendation

1. The exact OpenAI Project ID is not represented on the Odoo Provider record; current credential/model access was proven by successful requests, but the project identifier itself remains `UNVERIFIED`.
2. Exact invoice billing was not retrieved. Token cost is calculated from actual returned usage and the published rate card; container cost is represented by a conservative reserve, not an invoice line.
3. The `max_tool_calls=1` parameter did not match the returned Code Interpreter call counts. Any later TV must treat it as an ineffective hard ceiling unless a separately authorized verification proves otherwise. The three-Responses-request cap was enforced by the runner, and no fourth request was made.
4. Attempts 1 and 2 did not return an XLSX artifact. Those failures are preserved; attempt 3 produced the verified file.
5. This test used a tiny synthetic workbook and does not prove multi-turn editing, complex formulas, workbook feature preservation beyond the checked simple structure, pre-edit confirmation, Odoo Preview/Finalize integration, or browser attachment delivery.

Candidate B is worth continuing through the separately authorized TV-LE-02/03/04 scenarios because the minimal file-edit loop passed. This result must not be treated as a complete TV pass or as authorization to proceed to later phases.

## 8. Git and Change Scope

Only this new report and the dedicated synthetic evidence directory were added by this task. Pre-existing untracked work was preserved. No tracked production file was changed; no stage, commit, push, reset, clean, Odoo module upgrade, or service restart was performed.

## Official Sources

- [OpenAI Responses API file inputs](https://developers.openai.com/api/docs/guides/file-inputs)
- [OpenAI Code Interpreter](https://developers.openai.com/api/docs/guides/tools-code-interpreter)
- [GPT-5.6 Luna model capabilities and pricing](https://developers.openai.com/api/docs/models/gpt-5.6-luna)
- [OpenAI API pricing](https://developers.openai.com/api/docs/pricing)
