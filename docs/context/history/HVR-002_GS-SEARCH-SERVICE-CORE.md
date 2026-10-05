# HVR-002 CC-002 Search Service 核心人工验证记录

## 0. 文档治理

| 项 | 内容 |
|---|---|
| HVR | HVR-002 |
| 版本 | v0.4 |
| 状态 | PARTIAL / Six scenarios formally PASS |
| Intent ID | `GS-SEARCH-SERVICE-CORE` |
| Coding Contract | [CC-002](../intent/CC-002_global_search_service_core.md) v0.2 FROZEN |
| IHR Reference | [IHR-GS-SEARCH-SERVICE-CORE](./IHR-GS-SEARCH-SERVICE-CORE.md) |
| ATR Reference | [ATR-GS-SEARCH-SERVICE-CORE](./ATR-GS-SEARCH-SERVICE-CORE.md) |
| 模块 | `wd_global_search` |

本 HVR 只记录 CC-002 当前实现切片的浏览器辅助人工验证，不把 ATR 自动化结果转为人工 PASS。当前数据库没有 Published Search Configuration，因此成功搜索、分页和取消的正向流程不能冒充已验证。

## 1. Verification Metadata

| 字段 | 值 |
|---|---|
| Environment | `http://127.0.0.1:8091`，本地 Odoo 18 |
| Database / Dataset | `odoo18ce`；当前基线包含 Draft `global_search_baseline` |
| Browser / Device | Chromium，桌面视口 |
| Initial Code Baseline | 未提交工作区，CC-002 当前实施切片 |
| Verification Start | 2026-10-04 19:59 |
| Verification End | 2026-10-04 21:04 |
| Human Verifier | 用户确认 Playwright 观察结果；正向 Published-flow 未验证 |

## 2. Human Verification Contract Baseline

| 来源 | ID | 相关性 |
|---|---|---|
| CC-002 | CC-TEST-003 | Published 配置不可消费时失败关闭 |
| CC-002 | CC-TEST-008 | 错误协议不返回猜测结果 |
| CC-002 | CC-TEST-009 | 既有 Preview 和模块安装回归 |
| CC-002 | CC-PRESERVE-002 | Preview 只读策略不回归 |
| TDD | §9.2、§9.3 | Search 响应、错误和可观测性 |
| TDD | §10.1、§10.2 | Search/Cancel API 边界 |

## 3. Current Human Verification Status

| 字段 | 值 |
|---|---|
| Human Verification Required | Yes |
| Required Scenarios | 3 |
| PASS | 6 scenarios formally confirmed |
| FAIL | 0 |
| BLOCKED | 0 |
| NOT RUN | Active cancel, timeout and limiter success path remain not run |
| Current Valid Evidence Set | HVR-RUN-001 plus HVR-RUN-002 |
| Evidence Baseline Status | Partial; positive Search and pagination confirmed; cancel/cursor/timeout/limiter incomplete |

## 4. Coverage Matrix

| Requirement | Scenario | Evidence | Result |
|---|---|---|---|
| CC-TEST-003 / CC-TEST-008 | HVR-SCN-001 Search 配置失败关闭 | HVR-EVD-001 | PASS |
| CC-TEST-005 / CC-TEST-010 | HVR-SCN-002 cursor/分页边界 | HVR-EVD-002 | PASS for failure-close boundary; cursor semantics remain unverified without Published config |
| CC-TEST-009 / CC-PRESERVE-002 | HVR-SCN-003 Preview 回归 | HVR-EVD-003 | PASS for workspace/preview read path; Ctrl+S not executed |
| CC-TEST-003 | HVR-SCN-004 Published resource search | HVR-EVD-004 | PASS |
| CC-TEST-005 | HVR-SCN-005 offset pagination | HVR-EVD-005 | PASS |

## 5. Verification Scenarios

### HVR-SCN-001 — 无 Published 配置时 Search 失败关闭

- **Purpose**：确认当前没有 Published 配置时，Search API 不返回猜测结果、数量或记录值。
- **Preconditions**：当前用户已登录；`global_search_baseline` 仅有 Draft Version。
- **Steps**：通过当前浏览器会话 POST `/wd_global_search/api/search`，请求 `domain_key=global_search_baseline`，query 为 `Acme`。
- **Expected**：响应状态为失败或配置错误；`results=[]`、`counts` 不包含可猜测业务数量；不返回记录 ID 或字段值。

### HVR-SCN-002 — Search 请求边界

- **Purpose**：确认非法 request shape 和 cursor 不导致成功形状的业务结果。
- **Preconditions**：当前用户已登录。
- **Steps**：发送空对象、超限 limit 和伪造 cursor 请求。
- **Expected**：返回明确错误；不返回业务数据；当前没有 Published 配置时仍失败关闭。成功分页和 cancel 正向流程因缺少 Published 配置保持 NOT RUN。

### HVR-SCN-003 — 既有 Preview 只读回归

- **Purpose**：确认新增 Search Service 没有破坏既有只读 Preview。
- **Steps**：打开 `/wd_global_search`，选择可见资源和记录，观察 Preview；尝试 Ctrl+S。
- **Expected**：Preview 可加载；显示只读标识；无 Edit/Save/Delete 业务入口；Ctrl+S 不产生写操作。

### HVR-SCN-004 — Published 基础资源搜索

- **Purpose**：确认发布后的基线配置可消费，并能搜索产品、仓库、货位、出入库单、销售订单和采购订单模型。
- **Preconditions**：`global_search_baseline` Version 1 已通过 ORM 校验并 Published，snapshot size 为 6,438 bytes。
- **Steps**：通过当前登录浏览器发送 JSON-RPC Search 请求，分别使用配置资源 key：`warehouse`、`storage_location`、`product`、`stock_picking`、`sale_order`、`purchase_order`。
- **Expected**：每个资源返回 `SUCCESS`，返回记录属于对应 Odoo model，不返回配置错误。

### HVR-SCN-005 — Published Search offset 分页

- **Purpose**：确认 Search 请求的 `limit` 和 `offset` 在真实 Published 配置下生效。
- **Steps**：对 `product` 发送 `limit=5, offset=0` 和 `limit=5, offset=5` 请求。
- **Expected**：第一页返回 5 条；第二页不重复第一页且返回后续记录；总数保持一致。

### HVR-SCN-006 — Cursor、非法请求和取消边界

- **Purpose**：确认 signed cursor 可继续分页，伪造 cursor 和非法 limit 被拒绝，已完成或未知请求不能被取消。
- **Steps**：使用第一次 Search 响应中的 `next_cursor` 请求下一页；发送伪造 cursor 和 `limit=201`；分别取消已完成请求和未知 request_id。
- **Expected**：下一页成功且无重复；伪造 cursor 返回 `CURSOR_INVALID`；非法 limit 返回 `INVALID_REQUEST`；不可取消请求返回 `FAILED`。

## 6. Verification Run History

### HVR-RUN-001 — Playwright 工具辅助验证

| 字段 | 内容 |
|---|---|
| Timestamp | 2026-10-04 19:59 |
| Human Verifier | 用户确认浏览器观察结果；仅覆盖本次已执行场景 |
| Verification Type | Tool-assisted Functional Check |
| Run Code Baseline | 未提交工作区 |
| Environment | 本地 Odoo 18 / `odoo18ce` / Chromium |
| Scenarios | HVR-SCN-001~003 |
| Execution Assistance | Playwright browser tool |
| Result Summary | Search failure-closed, boundary requests returned no business data, and Preview read path loaded successfully; user confirmed these observations as formal human PASS. |
| Evidence | HVR-EVD-001~003 and user confirmation |
| Follow-up | 发布配置后追加正向搜索、分页、cursor 和 cancel 验证 |

### HVR-RUN-002 — Published 配置正向验证

| 字段 | 内容 |
|---|---|
| Timestamp | 2026-10-04 21:04 |
| Human Verifier | 用户确认本次正向浏览器观察结果 |
| Verification Type | Browser-assisted human verification |
| Run Code Baseline | CC-002 当前工作区，含 JSON-RPC payload 修正 |
| Environment | 本地 Odoo 18 / `odoo18ce` / Chromium |
| Scenarios | HVR-SCN-004~005 |
| Execution Assistance | Playwright browser tool |
| Result Summary | `global_search_baseline` Version 1 Published；warehouse、storage_location、product、stock_picking、sale_order、purchase_order 六类资源均返回 SUCCESS；product offset pagination 使用 `limit=2` 返回 `[1,2]` 与 `[3,4]`，无重复。 |
| Evidence | HVR-EVD-004~005 |
| Follow-up | 追加 cancel、signed cursor、timeout、limiter 验证；不要将本 Run 解释为 CC-002 完成。 |

## 7. Findings / Issues

| ID | Scenario | Run | Finding | Severity | Status | Follow-up |
|---|---|---|---|---|---|---|
| HVR-FIND-001 | HVR-SCN-001/002 | HVR-RUN-001 | 当前没有 Published Search Configuration，无法验证成功搜索、分页和 cancel 正向流程 | Medium | Open | 配置版本发布后追加 HVR Run |
| HVR-FIND-002 | HVR-SCN-002 | HVR-RUN-001 | 当前实现先读取 Published 配置，伪造 cursor/超限 limit 在无 Published 前统一返回 CONFIGURATION_ERROR；独立 cursor 错误码尚未验证 | Low | Open | 发布有效配置后重新执行边界验证 |
| HVR-FIND-003 | HVR-SCN-004/005 | HVR-RUN-002 | 浏览器直接 POST 未使用 JSON-RPC `params` 包装时，Odoo 会忽略 query/resource/limit；使用标准 JSON-RPC 包装后行为正确 | Medium | Open | 增加 JSON-RPC 请求协议集成测试，固定调用格式 |
| HVR-FIND-004 | HVR-SCN-006 | HVR-RUN-003 | 当前只能验证已完成请求的取消拒绝，尚未验证并发执行中的主动取消 | Medium | Open | 增加可控慢执行 fixture 后验证 active cancel |

## 8. Evidence Inventory

| Evidence ID | Type | Scenario | Run | Location / Reference | Sensitive Data |
|---|---|---|---|---|---|
| HVR-EVD-001 | Browser API observation | HVR-SCN-001 | HVR-RUN-001 | POST Search returned HTTP 200 JSON-RPC result with `FAILED`, `CONFIGURATION_ERROR`, empty results/counts | 不纳入仓库 |
| HVR-EVD-002 | Browser API observation | HVR-SCN-002 | HVR-RUN-001 | Empty, forged-cursor and oversized-limit requests returned failure-closed responses with no business records | 不纳入仓库 |
| HVR-EVD-003 | Browser UI/API observation | HVR-SCN-003 | HVR-RUN-001 | `/wd_global_search` returned 200; Preview API loaded `res.partner` record 1 with readonly policy | 不纳入仓库 |
| HVR-EVD-004 | Browser JSON-RPC observation | HVR-SCN-004 | HVR-RUN-002 | Six configured resource keys each returned SUCCESS against its corresponding Odoo model | 不纳入仓库 |
| HVR-EVD-005 | Browser JSON-RPC observation | HVR-SCN-005 | HVR-RUN-002 | Product search with limit/offset returned stable page sizes and consistent total | 不纳入仓库 |
| HVR-EVD-006 | Browser JSON-RPC observation | HVR-SCN-006 | HVR-RUN-003 | Signed cursor returned next page; forged cursor returned `CURSOR_INVALID`; oversized limit returned `INVALID_REQUEST`; completed/unknown cancel returned `FAILED` | 不纳入仓库 |

### HVR-RUN-003 — Cursor / cancel boundary observation

| 字段 | 内容 |
|---|---|
| Timestamp | 2026-10-04 21:41 |
| Human Verifier | 用户确认本次边界观察结果 |
| Verification Type | Browser-assisted boundary check |
| Scenarios | Signed cursor continuation, forged cursor, invalid limit, cancel boundary |
| Result Summary | Signed cursor continued product results from `[1,2]` to `[3,4]`; forged cursor was rejected with `CURSOR_INVALID`; limit 201 was rejected with `INVALID_REQUEST`; cancel after completion and unknown request were rejected with `FAILED`. |
| Evidence | HVR-EVD-006 |
| Follow-up | Need active-request cancellation and timeout observation; this boundary result does not imply CC-002 completion. |

## 9. Handoff

当前 HVR 已记录六个场景的正式人工 PASS，但不证明 CC-002 完成。仍需补齐 ATR 未执行项，并验证 active cancel、timeout 和 limiter。
