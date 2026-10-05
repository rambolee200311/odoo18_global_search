# CC-005 Global Search Workspace 查询与 Refinement

## 0. 文档治理

| 项 | 内容 |
|---|---|
| Coding Contract | CC-005 |
| 版本 | v0.1 FROZEN |
| 状态 | FROZEN，进入实施 |
| Intent ID | `GS-SEARCH-WORKSPACE-QUERY-REFINEMENT` |
| 上游 SRS | [SRS_global_search](../../requirement/SRS_global_search.md) v1.4 FROZEN |
| 上游 TDD | [TDD_global_search](../../design/TDD_global_search.md) v0.3 FROZEN |
| 实施计划 | [IMPLEMENTATION_PLAN_global_search](../../implementation/IMPLEMENTATION_PLAN_global_search.md) v0.2 FROZEN，Phase 5 |
| 前置 CC | [CC-001](./CC-001_global_search_configuration_foundation.md) v1.0 FROZEN；[CC-002](./CC-002_global_search_service_core.md) v0.2 FROZEN；[CC-003](./CC-003_global_search_permission_boundary.md) v0.2 FROZEN；[CC-004](./CC-004_global_search_preview_container.md) v0.2 FROZEN |
| 模块 | `wd_global_search` |
| 目标 | 将 Preview 容器扩展为当前用户可用的 Search Workspace，支持 Raw Query、结果发现、Query Understanding 和 Refinement |
| 批准冻结 | 2026-10-05 21:28，用户完成 HVR 并批准冻结 |

本 CC 只冻结 Phase 5 Workspace 查询与 Refinement，不实现外部搜索引擎、LLM、向量检索、索引迁移或新的业务权限语义。

## 1. 上游与范围

### 1.1 SRS / TDD 追溯

| 来源 | 相关章节 | 本 CC 落实 |
|---|---|---|
| SRS FR-SW-001~003 | 统一搜索入口、结果发现、Snapshot | Workspace 输入、分类结果和配置摘要 |
| SRS FR-RF-001~006 | Refinement、Resource、日期、状态和日期口径筛选 | Refinement 控件生成条件；日期口径切换按 V1 是否实现受控 |
| SRS FR-RF-007~009 | 初始状态、状态关系、两条路径汇合 | Raw Query 与 Refinement 状态机 |
| SRS FR-QU-001 | Query Understanding | Effective Conditions 可见 |
| SRS FR-ER-002~003 | 结果状态、错误分类 | SUCCESS、PARTIAL_SUCCESS、FAILED、TIMEOUT、CANCELLED 等状态展示 |
| SRS FR-PM-001~008 | 当前用户权限边界 | 结果、计数、Snapshot 均消费 CC-003 |
| SRS BR-006~008 | Query/Refinement 分离、Effective Conditions、路径等价 | 前端状态与 Search Service 请求契约 |
| SRS NFR-001~004 | 性能、新鲜度、可观测性、响应式 | Workspace 交互和错误状态 |
| TDD §2.2、§3.4~§3.5 | 请求生命周期、条件合并、时间语义 | 只通过 CC-002 条件模型执行 |
| TDD §6、§6.5 | 权限边界、失败关闭 | 不在前端模拟授权 |
| TDD §8 | Workspace、结果和 Refinement | 本 CC 核心 |
| TDD §10.1~§10.3 | API 与前端边界 | Search API 只接受可序列化条件 |
| TDD §12.5 | 浏览器测试 | HVR 验证 |

DDD：N/A，不得虚构领域对象或不变式。

### 1.2 在范围内

- Search Workspace 菜单/入口和可用资源 Tab；
- Raw Query 输入、提交、清空和加载状态；
- 结果按 Business Resource 分类、计数和 Snapshot 展示；
- Resource、日期范围、状态 Refinement；
- Query Understanding 展示 Raw Query、Parsed Conditions、Refinement 和 Effective Conditions；
- 保持 Raw Query 与 Refinement 独立；
- 结果切换与 CC-004 Preview 联动；
- 前端通过 CC-002 Search API，使用 CC-003 授权结果；
- 错误、取消、分页和无结果状态。

### 1.3 超出范围

- 修改 SRS、TDD 或官方 Odoo 代码；
- LLM、向量、外部搜索引擎和 PostgreSQL 索引；
- 新增业务模型、业务 ACL 或角色；
- 先取全量记录再在浏览器或 Python 中模拟权限；
- Preview 写操作、业务数据迁移；
- CC-002 尚未完成的真实 request timeout 和 active cancel 实现；如 Workspace 依赖它，必须先修订 CC-002。

## 2. 行为契约

### 2.1 状态模型

```text
Raw Query
  -> Parsed Conditions
  + Refinement Conditions
  -> Effective Conditions
  -> SearchRequest
  -> Authorized Results
  -> Preview
```

- Raw Query 是用户原始输入，不能被 Refinement 改写；
- Refinement 可叠加、删除和替换同一维度；
- 资源、日期和状态的初始值分别为全部、不限和全部；
- 修改搜索框时重置 Refinement、结果和 Preview；
- 修改 Refinement 时保留 Raw Query，刷新结果和 Query Understanding；
- 切换记录不重置 Raw Query 或 Refinement；
- 前端不直接拼接 ORM domain，所有条件通过 CC-002 Search Service 发送。

状态必须显式区分：

- `IDLE`：尚未提交；
- `SEARCHING`：请求进行中；
- `SUCCESS`：全部资源成功；
- `PARTIAL_SUCCESS`：部分资源成功、部分失败；
- `EMPTY`：请求成功但无结果；
- `FAILED`：全部资源失败；
- `TIMEOUT`：请求超时；
- `RATE_LIMITED`：超过速率限制；
- `CANCELLED`：用户取消。

### 2.2 权限与数据边界

- 资源 Tab 只显示当前用户有权访问且当前结果集有数据的 Business Resource；
- 无权记录不出现在结果、计数、Snapshot、分页或 cursor；
- Snapshot 字段消费 Published 配置并再次经过 CC-003 字段过滤；
- 请求体中的 uid、company_id、company_ids、groups 和权限声明一律忽略；
- 授权异常、配置错误或响应结构异常默认失败关闭，不返回猜测数据；
- 不跨用户共享 Search、Refinement 或 Preview 结果缓存。

## 3. API 契约

Workspace 使用既有 `POST /wd_global_search/api/search`：

```json
{
  "query": "A客户",
  "conditions": [],
  "refinement_conditions": [
    {"dimension": "resource", "value": "sale_order"},
    {"dimension": "date", "operator": "this_month"},
    {"dimension": "state", "value": "draft"}
  ],
  "resources": [],
  "limit": 20,
  "cursor": null
}
```

前端只提交可序列化值。成功结果必须包含 `results`、`resource_counts`、`effective_conditions`、`next_cursor` 和配置版本；失败响应使用 CC-002 错误码，不以空成功结果掩盖失败。

成功响应：

```json
{
  "status": "SUCCESS",
  "results": [{
    "resource": "customer",
    "model": "res.partner",
    "record_id": 42,
    "snapshot": {
      "title": "Acme Corporation",
      "subtitle": "Customer",
      "fields": [{"label": "Email", "value": "cc04@example.com"}]
    }
  }],
  "resource_counts": {"all": 1, "customer": 1},
  "effective_conditions": [
    {"dimension": "resource", "value": "customer", "source": "refinement"}
  ],
  "next_cursor": null,
  "meta": {
    "config_version": "1",
    "request_id": "...",
    "completed_resources": ["customer"],
    "failed_resources": []
  }
}
```

失败和部分成功响应必须沿用 CC-002 错误协议，并在 `meta.failed_resources` 中列出失败资源；不得使用空的 `SUCCESS` 响应隐藏错误。

## 4. 必需行为变更

| ID | 当前缺口 | 期望行为 | 验证 |
|---|---|---|---|
| CC5-CHANGE-001 | Query 输入框只读 | 用户可输入 Raw Query 并提交 | CC5-TEST-001 |
| CC5-CHANGE-002 | 结果区域只有占位卡片 | 显示授权后的分类结果、Snapshot 和计数 | CC5-TEST-002 |
| CC5-CHANGE-003 | Refinement 未实现 | 支持 Resource、日期、状态筛选和删除 | CC5-TEST-003 |
| CC5-CHANGE-004 | Effective Conditions 不可见 | Query Understanding 展示条件来源和合并结果 | CC5-TEST-004 |
| CC5-CHANGE-005 | Workspace 未接入普通用户入口 | 普通用户可进入 Workspace，配置管理员入口保持隔离 | CC5-TEST-005 |
| CC5-CHANGE-006 | Preview 与查询状态未联动 | 结果点击打开 CC-004 Preview，状态变更符合契约 | CC5-TEST-006 |

## 5. 测试契约

| ID | 测试内容 | 类型 | 预期结果 | 人工验证 |
|---|---|---|---|---|
| CC5-TEST-001 | Raw Query 输入和提交 | 浏览器+集成 | 搜索请求只携带当前用户上下文和序列化 Query | 是 |
| CC5-TEST-002 | 资源分类、计数、Snapshot | 集成+浏览器 | 结果经过权限过滤，分类和计数一致 | 是 |
| CC5-TEST-003 | Resource/日期/状态 Refinement | 浏览器+集成 | 条件可叠加、删除，结果实时收窄 | 是 |
| CC5-TEST-004 | Query Understanding | 浏览器 | Raw、Parsed、Refinement、Effective Conditions 可见且不混淆 | 是 |
| CC5-TEST-005 | 多用户、多公司、Portal 回归 | ORM+浏览器 | 无权资源、记录、字段和计数不泄露 | 是 |
| CC5-TEST-006 | 结果到 Preview | 浏览器 | 点击结果打开 CC-004 只读 Preview | 是 |
| CC5-TEST-007 | 两条路径等价 | 集成 | 组合 Query 与逐步 Refinement 产生相同条件和记录集 | 否 |
| CC5-TEST-008 | 分页、cursor 和空结果 | 集成+浏览器 | 游标绑定用户/配置，分页和空状态正确 | 是 |
| CC5-TEST-009 | Workspace 写操作边界 | 浏览器+网络监控 | 搜索交互不产生业务 create/write/unlink/copy | 是 |
| CC5-TEST-010 | 桌面和窄屏响应式 | 浏览器 | 桌面分栏、窄屏单栏，无控制台错误 | 是 |
| CC5-TEST-011 | 前端状态机 | 浏览器 | 修改 Raw Query 重置 Refinement；修改 Refinement 保持 Raw Query；切换记录保持两者 | 是 |
| CC5-TEST-012 | Query Understanding 不泄露 | 集成+浏览器 | 无权实体、字段和记录不出现在 Query Understanding | 是 |

## 6. 停止条件与完成定义

### 6.1 停止条件

1. 需要改变 SRS/TDD 的权限、条件或结果语义；
2. 需要修改官方代码、新增业务 ACL/角色或使用 `sudo()` 读取业务数据；
3. 无法证明计数、Snapshot、分页和 cursor 经过权限过滤；
4. 前端绕过 CC-002 直接访问 ORM 或拼接授权域；
5. 需要实现真实 timeout/active cancel 才能满足 Workspace 行为；
6. 发现跨用户共享授权结果或缓存。

### 6.2 完成定义

1. CC5-CHANGE-001~006 全部实现并有 IHR；
2. CC5-TEST-001~010 执行并有 ATR；
3. 至少一名普通用户、一名多公司用户和一名 Portal 用户完成权限 HVR；
4. Resource、日期、状态 Refinement 与 Query Understanding 浏览器验证通过；
5. 两条路径等价、分页/cursor 和 Preview 联动通过；
6. CC-001~CC-004 既有行为不回归；
7. 无业务写操作、权限旁路、官方代码修改或 Phase 5 之外功能宣称。
8. Workspace 搜索 P95 ≤ 2 秒、Refinement P95 ≤ 1 秒、Query Understanding 渲染 P95 ≤ 500ms；均为软闸门并记录为 TV-01 输入。

## 7. 既有行为保留

| ID | 行为 |
|---|---|
| CC5-PRESERVE-001 | CC-001 Published 配置、配置管理员隔离和快照语义不变 |
| CC5-PRESERVE-002 | CC-002 Search/Cancel API、cursor、限流和错误协议不被前端覆盖 |
| CC5-PRESERVE-003 | CC-003 当前用户、公司、字段权限和失败关闭继续生效 |
| CC5-PRESERVE-004 | CC-004 Preview 仍为只读，Workspace 不产生业务写操作 |

## 8. TDD 防护栏、数据和迁移影响

- TDD §3.4：Raw Query、Parsed Conditions、Refinement Conditions 只能通过 Effective Conditions 汇合；
- TDD §6.5：授权异常、配置异常和未知条件默认失败关闭；
- TDD §8：Workspace 只负责交互和状态，不复制 Search Service 执行逻辑；
- TDD §10：前端只调用服务端 API，不接触 ORM；
- TDD §12.5：至少使用内置浏览器完成 HVR；
- 不新增业务模型、字段、ACL、数据库表或数据迁移；
- 不改变 Published 配置快照格式；如需要 Snapshot 新字段，必须单独修订 CC-001；
- 前端状态和条件不得持久化为跨用户共享数据。

## 9. CC-002 / CC-004 接口契约

### 9.1 CC-002 → CC-005

- CC-005 只通过 `POST /wd_global_search/api/search` 提交查询；
- CC-005 不直接调用 ORM、不拼接 domain、不覆盖 CC-002 错误协议；
- CC-005 消费 `effective_conditions`、`next_cursor`、`request_id`、资源结果和错误码；
- CC-002 的 timeout/active cancel 未完成时，CC-005 不模拟或宣称真实取消。

### 9.2 CC-004 → CC-005

- CC-005 选中结果后调用 CC-004 Preview API，传递 `model` 和 `record_id`；
- CC-004 返回 `PreviewResult`，CC-005 只负责展示，不修改其只读状态；
- 切换记录时重新调用 Preview API；
- CC-004 的权限过滤、失败关闭和无写入口不受 CC-005 影响。

## 10. 补充规范

### 10.1 响应式与国际化

- `>=1024px`：结果和 Preview 分栏；
- `768~1023px`：分栏，可折叠；
- `<768px`：单栏，先结果后 Preview；
- `375px`：Preview 可全屏显示；
- Query placeholder、资源、Refinement、Query Understanding、错误消息按当前用户语言；
- 日期、数字和时区按当前用户环境格式化，缺失翻译回退英文。

### 10.2 错误、日志与性能

- `SUCCESS` 正常显示；`PARTIAL_SUCCESS` 显示结果和失败资源；`FAILED` 不显示猜测结果；`TIMEOUT` 显示已完成结果；`RATE_LIMITED`、`CANCELLED` 和 `EMPTY` 显示明确状态；
- 日志只记录 `request_id`、用户上下文标识、条件哈希、资源、状态和延迟，不记录原始 Query、条件值、字段值、SQL 或令牌；
- 性能预算为搜索 P95 ≤2 秒、Refinement P95 ≤1 秒、Query Understanding 渲染 P95 ≤500ms、结果列表渲染 P95 ≤1 秒、Preview P95 ≤1 秒。

### 10.3 Fixture、验收和浏览器矩阵

- Fixture 位置：`tests/fixtures/workspace/`，覆盖普通用户、Portal、多公司、可访问/不可访问资源、字段权限和 Refinement 组合；
- 验收必须覆盖输入搜索、资源/日期/状态筛选、删除筛选、Query Understanding、Preview 联动、权限隔离、分页、空结果和响应式布局；
- 首轮浏览器矩阵：Chrome、Firefox、Safari、Edge 最新版；桌面、平板和窄屏均记录结果。

## 11. CC-DEC

| ID | 决策 | 替代方案 | 理由 |
|---|---|---|---|
| CC5-DEC-001 | Raw Query 与 Refinement 分离 | 单一查询状态 | 符合 BR-006 |
| CC5-DEC-002 | 前端只提交可序列化条件 | 前端拼接 domain | 符合 TDD §3.4 并避免权限旁路 |
| CC5-DEC-003 | 权限过滤在聚合和计数前完成 | 聚合后过滤 | 防止计数和 Snapshot 泄露 |
| CC5-DEC-004 | 资源 Tab 只显示有权且有数据的资源 | 显示所有有权资源 | 避免空 Tab，符合 FR-RF-002 |
| CC5-DEC-005 | 不补做 CC-002 未完成的 timeout/active cancel | 前端模拟取消 | 避免宣称未验证行为 |

## 12. 状态机

```text
IDLE -> SEARCHING -> SUCCESS
                 -> PARTIAL_SUCCESS
                 -> EMPTY
                 -> FAILED / TIMEOUT / RATE_LIMITED / CANCELLED
SUCCESS/PARTIAL_SUCCESS -> SEARCHING (add/remove refinement)
SUCCESS/PARTIAL_SUCCESS -> IDLE (clear query)
FAILED/TIMEOUT -> SEARCHING (retry)
```

## 13. 实施结构

```text
controllers/main.py             # Workspace 页面和既有 Search API 接线
services/facade.py              # 消费 CC-002/CC-003
static/src/js/workspace.js      # Query、Refinement、结果和 Preview 状态
static/src/css/workspace.css    # Workspace 响应式布局
tests/test_workspace.py         # 状态、权限和 API 集成测试
```

建议前端状态接口：

```text
WorkspaceState:
  rawQuery: string
  parsedConditions: list
  refinementConditions: list
  effectiveConditions: list
  selectedResource: string | null
  selectedRecord: {model, id} | null
  results: list
  resourceCounts: dict
  cursor: string | null
  status: IDLE | SEARCHING | SUCCESS | PARTIAL_SUCCESS | EMPTY | FAILED | TIMEOUT | RATE_LIMITED | CANCELLED
```

建议前端接口：

```javascript
submitQuery(rawQuery): Promise<SearchResponse>
addRefinement(dimension, value): Promise<SearchResponse>
removeRefinement(dimension): Promise<SearchResponse>
selectRecord(model, id): void
clearQuery(): void
loadMore(cursor): Promise<SearchResponse>
cancelRequest(requestId): Promise<CancelResponse>
```

## 14. 评审闸门

- 评审必须确认 Raw Query/Refinement 分离和两条路径等价；
- 评审必须确认权限边界位于结果聚合和计数之前；
- 评审必须确认 CC-004 Preview 仍是唯一只读记录入口；
- 未经用户批准冻结，不得实现 CC-005。
