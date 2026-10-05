# HVR-003 CC-003 Global Search 权限边界人工验证记录

## 0. 文档治理

| 项 | 内容 |
|---|---|
| HVR | HVR-003 |
| 版本 | v0.2 |
| 状态 | Tool-assisted run complete / PARTIAL |
| CC | [CC-003](../intent/CC-003_global_search_permission_boundary.md) v0.2 FROZEN |
| IHR | [IHR-GS-PERMISSION-BOUNDARY](./IHR-GS-PERMISSION-BOUNDARY.md) |
| ATR | [ATR-GS-PERMISSION-BOUNDARY](./ATR-GS-PERMISSION-BOUNDARY.md) |
| Environment | Odoo 18 / `odoo18ce` / Chromium and ORM-assisted verification |

## 1. Scenarios

| ID | 场景 | 当前结果 |
|---|---|---|
| HVR3-SCN-001 | 公司 1 用户和公司 2 用户只看到各自授权业务记录 | ORM/tool-assisted PASS |
| HVR3-SCN-002 | Portal 用户访问业务资源 | ORM/tool-assisted PASS，`RESOURCE_NOT_ACCESSIBLE` |
| HVR3-SCN-003 | 普通用户不能直接读取配置模型，但 Search 可消费 Published 配置 | ORM/tool-assisted PASS |
| HVR3-SCN-004 | 无权字段不参与搜索 | Unit PASS；真实浏览器/业务字段场景 NOT RUN |
| HVR3-SCN-005 | Relation Path 中间段权限阻断 | Unit PASS；真实关系 fixture NOT RUN |
| HVR3-SCN-006 | 权限变化后新请求反映变化 | NOT RUN |

## 2.1 HVR-RUN-001 — Current-user browser boundary

| 字段 | 内容 |
|---|---|
| Timestamp | 2026-10-05 19:09 |
| Browser | Chromium, current authenticated Odoo session |
| Execution | Playwright JSON-RPC requests |
| Result | Current-user product Search returned `SUCCESS`; normal and forged request-body identity (`uid=103`, `company_id=2`, `company_ids=[2]`) returned identical sale-order record IDs `[1,2]`; unknown resource returned empty result without business data |
| Interpretation | Browser evidence confirms request-body identity cannot replace server context for this session |
| Human status | Tool-assisted observation; not a multi-user formal PASS |

### HVR-RUN-002 — Built-in browser visible Preview observation

| 字段 | 内容 |
|---|---|
| Timestamp | 2026-10-05 19:18 |
| Tool | Integrated browser navigation and visible element clicks |
| Steps | Opened `/wd_global_search`; clicked Contacts, Sales Orders and Transfers resources; attempted to interact with the Search query field |
| Observation | Contacts, Sales Orders and Transfers each loaded a visible `READ ONLY · FORM VIEW` preview under the current session; query input was visibly `readonly` and Search button remained disabled |
| Result | Preview read-only boundary observed; Search Workspace input is intentionally not active in this phase |
| Human status | Tool-assisted browser observation; user can inspect the shared page |

> Search Query 输入框为 `readonly` 属于 Phase 5 Workspace 尚未实施，不作为 CC-003 验收项。

## 3. Evidence

- 用户 102（公司 1）与用户 103（公司 2）的 `sale_order` / `stock_picking` 结果已通过 ORM Search 对比；
- Portal 用户 7/101 搜索产品返回 `RESOURCE_NOT_ACCESSIBLE`，结果为空；
- 普通用户直接读取 `wd.gs.config.domain` 被 AccessError 拒绝；
- 当前登录浏览器 Search 仍返回 `SUCCESS`，CC-002 正向行为未回归；
- Playwright 当前用户场景：产品 Search `SUCCESS`；伪造请求体身份与正常请求返回相同销售订单 `[1,2]`；
- 内置浏览器可见场景：Contacts、Sales Orders、Transfers 均显示 `READ ONLY · FORM VIEW`；Search query 输入框为 readonly；
- 本文不将 ORM/tool-assisted 观察自动等同于正式人工 PASS。

## 4. Remaining Human Verification

- 需要不同用户浏览器登录会话；
- 需要人工观察公司隔离、Portal 失败关闭和权限变化后的结果；
- 需要真实字段权限和 Relation Path fixture；
- HVR-003 当前不构成 CC-003 完成。
