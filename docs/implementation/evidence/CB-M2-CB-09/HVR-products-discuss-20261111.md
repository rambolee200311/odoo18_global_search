# CC-M2-CB-09 Supplemental HVR — Product Archive from Odoo

**Result: PASS — real Odoo Discuss UI, Agent tool loop, OpenAI Responses API + Hosted Code Interpreter, V1 delivery, actual attachment download, and independent XLSX readback.**

## Root cause and repair

The earlier user turns in Thread `llm.thread_19915` produced no Retriever or Office tool call. In the prior Thread integration, `LLMThread.generate()` bound the Office tool set only for an incoming Office attachment, and `_office_is_active()` otherwise relied on an upload or active Office Session. A fileless create request has neither. As a result, the native Agent request did not include Route B Office guidance or the relevant Tool schema; the model asked the user for an upload and then returned CSV text. The failure was before Provider dispatch, not an unavailable `office(action="create")` action or a disabled Provider.

The minimal change is in `mymodules/office_engine_m2/models/llm_thread.py`:

- `_office_requests_fileless_workbook()` recognizes a user-owned workbook request from generic file-format and create/edit terms and checks recent user messages in the same Thread for follow-up turns.
- `generate()` activates and binds the existing Office tools before the native Agent constructs its Provider request.
- `_office_is_active()` keeps fileless requests and fileless Sessions on the existing Route B path; `_office_has_versioned_current()` recognizes their accepted Current.
- The existing Agent instruction routes creation to `office(action="create")` and Odoo reads to `odoo_record_retriever`. No public Tool, query service, permission rule or Provider setting was added or bypassed.

Evidence in the original transcript: earlier turns at 9:02–9:03 show no `Tools Requested` card; the successful 9:23 turn below shows both existing Tools. This Thread header displayed six bound tools, while the Agent's actual relevant calls were Retriever followed by Office. The focused schema regression verifies the Route B Provider request exposes `office` and `odoo_record_retriever` and carries the `create` instruction.

## User action and real tool calls

**User instruction (Thread 19915):**

> 请从本公司当前用户有权访问的真实产品档案中任意选择 5 个产品，直接创建并交付一个新的 Excel（XLSX），包含产品名称、价格、重量、计数方式（数量/批次/序列号）。只使用实际读取到的数据，不要编造，也不要修改任何 Odoo 产品记录；请提供可下载的 XLSX 文件，不要用 CSV 文本替代。

The user authorized transmission of the requested product fields to OpenAI `gpt-5.6-luna` immediately before this run.

1. `odoo_record_retriever`, call `call_AhSSeFxCYyRrlM0ybw55Vi4E`: model `product.template`; fields `name`, `list_price`, `weight`, `tracking`; `domain=[]`, `order="id asc"`, `limit=5`, `offset=0`, pagination enabled. It returned 5 records, IDs 1–5, `count=47`, `has_more=true`.
2. `office`, call `call_5FqqU4hXfxJ5dPbITqa2JlWK`: `{ "action": "create" }`. No source file, input SHA or parent version was supplied or fabricated.

## Provider, version and delivery evidence

| Field | Actual result |
|---|---|
| Odoo | Non-production Odoo 18 CE, `odoo18ce`, Discuss on 8091 |
| User / Thread | Mitchell Admin / `llm.thread_19915` |
| Provider | OpenAI Responses API + Hosted Code Interpreter; model `gpt-5.6-luna` |
| Response / request | `resp_058f906fb0cb7b64016af46c7278bc87d2a362ec2acd13174c` / `req_9a26f37e14d94768a9c050ac0b1dcb23` |
| Provider file / container | `cfile_6af46c9584bc8191aad71e649d0c8c22` / `cntr_6af46c72ae2481919cfb3fc96a796edd07e7f3ff12324934` |
| Usage / duration | 9,700 input + 2,748 output = 12,448 tokens (690 reasoning); 42.778 s |
| Remote cleanup | `completed`, no error |
| V1 | Session 15457; version 3369; version no. 1; Current=Last Valid=3369; Revision=1; finalized |
| Verification | `PARTIALLY_VERIFIED`; the service reports file integrity/readability checked while business completeness/correctness remains outside that receipt |
| Delivery | Attachment 49900; message 116235; attached to Thread; status `created_v1_and_delivered` |
| Source binding | `input_attachment_id=false`, `input_sha256=false`, `parent_version_id=false` |

## Download and independent readback

Downloaded by clicking the visible Discuss attachment card's Download button. The actual link targeted `/web/content/49900?...&download=true`; browser download saved to `/Users/lijianqiang/Downloads/odoo_product_archive_5.xlsx`.

- File size: 7,160 bytes.
- SHA-256: `f84d034b2e3a7cb2d3a010a53dffa02fb169ee9027e4902a5d5a0e98bbd4d8e9`; matches the Office tool result and V1 output SHA.
- ZIP/OOXML integrity: PASS; `openpyxl` readback: PASS.
- Worksheet: `产品档案`, dimension `A1:D11`; headers at row 4 are `产品名称`, `价格`, `重量`, `计数方式`.
- Five data rows were compared field-by-field against the five Retriever result records: PASS. Each source `tracking="none"` is represented as `数量`; price and weight remain numeric values.
- No product write Tool was called. Retrieval was read-only; the only Office action was file creation/delivery.

Machine-readable assertions and identifiers are in `HVR-products-readback-20261111.json`.

## Focused regression

The following Odoo TransactionCase pair ran against `odoo18ce`:

- `TestNativeOfficeChatIntegration.test_fileless_xlsx_request_binds_route_b_tools_for_create_and_followup_turns`
- `TestEditOrchestration.test_fileless_current_is_used_as_parent_for_next_edit`

**Result: 2 tests, 0 failed, 0 errors.** Log: `ATR-fileless-tool-binding-and-current-20261111-rerun.log`.

The earlier unprivileged shell attempt was blocked before test startup by sandbox denial of local PostgreSQL access; the authorized rerun completed. No Provider Mock was used for this HVR. The existing full-suite result (240 tests) predates this small Thread activation change and is not represented as a post-change full-suite run.

## Acceptance statement

This HVR passes the product fileless-create scenario from the real Odoo Discuss user entry through authorized data retrieval, real Provider execution, V1/Current registration, Thread attachment delivery, browser download and independent content/hash verification. It does not claim that the service's `PARTIALLY_VERIFIED` level proves business correctness. CC-09 closure is recorded in `FR-M2-CB-09.md`.
