# IHR GS-SEARCH-SERVICE-CORE

## 0. 文档治理

| 项 | 内容 |
|---|---|
| IHR 文档 | `IHR-GS-SEARCH-SERVICE-CORE.md` |
| Intent ID | `GS-SEARCH-SERVICE-CORE` |
| CC 引用 | [CC-002](../intent/CC-002_global_search_service_core.md) v0.2 FROZEN |
| 模块 | `wd_global_search` |
| 实施负责人 | Copilot Agent |
| 开始时间 | 2026-10-04 19:12 |
| 最后更新 | 2026-10-04 21:41 |
| 当前实施状态 | In Progress |

## 1. Coding Contract 基线

| 项 | 引用 |
|---|---|
| Scope | CC-002 §3 |
| Change Boundary | CC-002 §4 |
| Required Behavior | CC-CHANGE-001~006 |
| Preservation | CC-PRESERVE-001~005 |
| Test Contract | CC-TEST-001~010 |
| Stop Conditions | CC-002 §12 |
| Done Criteria | CC-002 §13 |

## 2. 当前实施状态摘要

| 项 | 状态 |
|---|---|
| CC-CHANGE 落实进度 | 6 项均有初始实现，均未完成最终验收 |
| Preservation Impact | Potential Impact；既有 Preview 路由保留，待 ATR 回归 |
| Deviation | None |
| Stop Condition 触发 | No |
| Open Issues | 3：真实 request 级超时、cancel 并发生命周期、Search Service 集成测试覆盖待补；cursor/基础限流已接线 |
| Revert 发生 | No |
| 当前状态 | In Progress |

## 3. 实施历史条目

### IHR-001

| 字段 | 内容 |
|---|---|
| 时间 | 2026-10-04 19:12–19:30 |
| 阶段 | Implementation |
| Action | 冻结 CC-002；新增 `services/` 核心模块：types、errors、conditions、provider、cursor、executor、aggregator、limiter、facade。 |
| Reason | 落实 UserContext、Published 配置消费、条件合并、只读资源执行、结果聚合、cursor 和并发边界。 |
| Files / Components | `mymodules/wd_global_search/services/` |
| Contract Reference | CC-CHANGE-001~006、CC-DEC-001~004 |
| Upstream Reference | Implementation Plan Phase 2；TDD §3、§9、§10 |
| Result | Partial |
| Deviation | None |
| Follow-up | 补齐真实超时/取消生命周期、限流窗口、cursor API 接线和集成测试。 |

### IHR-002

| 字段 | 内容 |
|---|---|
| 时间 | 2026-10-04 19:25–19:30 |
| 阶段 | Implementation |
| Action | 在 `controllers/main.py` 增加只读 Search/Cancel JSON 路由；保留既有 Preview 路由和前端入口不变。 |
| Reason | 提供 Phase 2 服务端协议，不扩大到 Search Workspace 菜单。 |
| Files / Components | `mymodules/wd_global_search/controllers/main.py` |
| Contract Reference | CC-CHANGE-001、CC-CHANGE-006、CC-PRESERVE-002、CC-DEC-005 |
| Upstream Reference | TDD §10.1~§10.2 |
| Result | Partial |
| Deviation | None |
| Follow-up | 增加请求协议、错误协议和当前用户取消的集成测试。 |

### IHR-003

| 字段 | 内容 |
|---|---|
| 时间 | 2026-10-04 19:30–19:35 |
| 阶段 | Implementation |
| Action | 增加 `test_service_core.py`，接入模块测试发现；执行 Python 编译、diff check 和 Odoo 模块测试。 |
| Reason | 建立 Search Service 核心的第一批自动化证据。 |
| Files / Components | `mymodules/wd_global_search/tests/test_service_core.py`、`tests/__init__.py` |
| Contract Reference | CC-TEST-004、CC-TEST-005、CC-TEST-007 的初始覆盖 |
| Upstream Reference | TDD §12.3~§12.5 |
| Result | Completed for executed slice |
| Deviation | None |
| Follow-up | ATR 记录当前测试范围；未执行的 CC-TEST 保持 NOT RUN。 |

### IHR-004

| 字段 | 内容 |
|---|---|
| 时间 | 2026-10-04 20:xx |
| 阶段 | Browser verification remediation |
| Action | 修正 Odoo `type="json"` 路由的 payload 读取：使用路由参数 `kwargs`，不访问当前 Odoo Request 不提供的 `jsonrequest` 属性；重启服务后重新执行浏览器验证。 |
| Reason | 首次浏览器请求暴露真实运行时 AttributeError，导致 Search/Cancel 路由无法进入服务层。 |
| Files / Components | `mymodules/wd_global_search/controllers/main.py` |
| Contract Reference | CC-CHANGE-001、CC-TEST-003、CC-TEST-008 |
| Result | Fixed; tool-assisted HVR requests completed |
| Deviation | None |
| Follow-up | 补充请求协议集成测试；Published 配置后验证正向 cursor/cancel 流程。 |

### IHR-005

| 字段 | 内容 |
|---|---|
| 时间 | 2026-10-04 20:xx |
| 阶段 | Human verification evidence |
| Action | 通过已登录 Chromium 会话执行 HVR-002 的 Search failure-close、边界请求和 Preview 回归观察，并更新 HVR-002。 |
| Reason | 建立不将自动化测试冒充人工验收的浏览器证据。 |
| Files / Components | `docs/context/history/HVR-002_GS-SEARCH-SERVICE-CORE.md` |
| Contract Reference | CC-TEST-003、CC-TEST-005、CC-TEST-008、CC-TEST-009 |
| Result | Tool-assisted observations complete; formal human confirmation pending |
| Deviation | 当前无 Published 配置，正向搜索/分页/cursor/cancel 尚未验证。 |
| Follow-up | 用户确认观察结果后再记录正式人工 PASS；发布配置后追加 HVR-RUN-002。 |

### IHR-006

| 字段 | 内容 |
|---|---|
| 时间 | 2026-10-04 21:04 |
| 阶段 | Configuration publication and positive verification |
| Action | 通过 Odoo ORM 对 `global_search_baseline` Version 1 执行配置校验和正式发布，生成 6,438-byte snapshot/checksum；随后通过 JSON-RPC 浏览器请求验证资源搜索和分页。 |
| Reason | 消除无 Published 配置对 CC-002 正向 Search、分页和 cancel 验证的阻塞。 |
| Files / Components | `global_search_baseline`；Version 1；Published snapshot |
| Contract Reference | CC-001 lifecycle；CC-002 CC-TEST-003、005、008、010 |
| Result | Published successfully; positive resource search and offset pagination observed |
| Deviation | Cancel 正向流程和 cursor 完整接线仍未验证。资源 scope 使用配置 key（如 `warehouse`、`stock_picking`、`sale_order`、`purchase_order`），不是 Odoo model 名。 |
| Follow-up | 修正 JSON-RPC payload 集成测试；追加 cancel/cursor/timeout/limiter 验证。 |

### IHR-007

| 字段 | 内容 |
|---|---|
| 时间 | 2026-10-04 21:04 |
| 阶段 | Pagination correction |
| Action | 修正 Resource Executor 的抓取上限，使 `offset + limit` 的分页窗口在资源执行阶段可用；重启 Odoo 后通过浏览器验证 product `[1,2]` 与 `[3,4]` 两页无重复。 |
| Reason | 初始实现只抓取 `limit` 条，再由聚合器应用 offset，导致非首分页为空。 |
| Files / Components | `mymodules/wd_global_search/services/facade.py` |
| Contract Reference | CC-CHANGE-003、CC-TEST-005 |
| Result | Fixed for bounded offset window |
| Deviation | 当前每资源抓取仍受 50 条上限约束；cursor 分页尚未接线。 |
| Follow-up | 增加分页集成测试并继续完成 cursor 方案。 |

### IHR-008

| 字段 | 内容 |
|---|---|
| 时间 | 2026-10-04 21:41 |
| 阶段 | Service boundary completion slice |
| Action | 接通 HMAC cursor 的生成、绑定校验、过期/伪造拒绝；增加 database secret 作为签名密钥；增加请求限流窗口、非法 limit 错误码、5 秒请求预算检查和请求生命周期清理。 |
| Reason | 落实 CC-TEST-005、CC-TEST-006、CC-TEST-007、CC-TEST-010 的核心边界。 |
| Files / Components | `services/facade.py`、`services/limiter.py`、`services/errors.py`、`controllers/main.py` |
| Contract Reference | CC-CHANGE-003~006、CC-TEST-005~007、CC-TEST-010 |
| Result | Partial; live browser evidence completed for cursor, invalid limit, resource scope and cancel-after-completion rejection |
| Deviation | 真正跨线程 cancel 和执行器级 per-resource timeout 仍需集成测试。 |
| Follow-up | 增加 Search/Cancel 集成 fixture，覆盖 active request cancellation and timeout. |

## 4. 实际变更清单

| 路径 | 变更 |
|---|---|
| `mymodules/wd_global_search/services/` | 新增 Search Service 核心模块 |
| `mymodules/wd_global_search/controllers/main.py` | 新增 Search/Cancel JSON 路由 |
| `mymodules/wd_global_search/tests/test_service_core.py` | 新增核心纯单元测试 |
| `mymodules/wd_global_search/tests/__init__.py` | 接入测试模块 |
| `docs/context/intent/CC-002_global_search_service_core.md` | CC-002 冻结状态记录 |
| `docs/context/history/HVR-002_GS-SEARCH-SERVICE-CORE.md` | 记录 Playwright 工具辅助验证 |

## 5. 未完成项

- 未完成 CC-002 全部 10 项测试契约；
- 未完成真实 request 级超时和取消生命周期；
- 未完成速率窗口与有界队列；
- 未完成 cursor 与 Search API 的完整接线；
- 未完成 Search Service 集成数据 fixture；
- 未完成 ATR 全量、HVR-002 和 FR。

## 6. 交接状态

IHR 记录当前实施事实，不表示 CC-002 已完成。后续顺序为：继续 Implementation → ATR 追加测试 Run → HVR-002（如需要）→ FR。
