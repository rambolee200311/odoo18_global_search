# CC-005 Global Search Workspace 查询与 Refinement

## 0. 文档治理

| 项 | 内容 |
|---|---|
| Coding Contract | CC-005 |
| 版本 | v0.1 DRAFT |
| 状态 | Draft / Ready for Review |
| Intent ID | `GS-SEARCH-WORKSPACE-QUERY-REFINEMENT` |
| 上游 SRS | [SRS_global_search](../../requirement/SRS_global_search.md) v1.4 FROZEN |
| 上游 TDD | [TDD_global_search](../../design/TDD_global_search.md) v0.3 FROZEN |
| 实施计划 | [IMPLEMENTATION_PLAN_global_search](../../implementation/IMPLEMENTATION_PLAN_global_search.md) v0.2 FROZEN，Phase 5 |
| 前置 CC | [CC-001](./CC-001_global_search_configuration_foundation.md) v1.0 FROZEN；[CC-002](./CC-002_global_search_service_core.md) v0.2 FROZEN；[CC-003](./CC-003_global_search_permission_boundary.md) v0.2 FROZEN；[CC-004](./CC-004_global_search_preview_container.md) v0.2 FROZEN |
| 模块 | `wd_global_search` |
| 目标 | 将 Preview 容器扩展为当前用户可用的 Search Workspace，支持 Raw Query、结果发现、Query Understanding 和 Refinement |
| 批准冻结 | 待评审 |

本 CC 只冻结 Phase 5 Workspace 查询与 Refinement，不实现外部搜索引擎、LLM、向量检索、索引迁移或新的业务权限语义。

## 1. 上游与范围

### 1.1 SRS / TDD 追溯

| 来源 | 相关章节 | 本 CC 落实 |
|---|---|---|
| SRS FR-SW-001~003 | 统一搜索入口、结果发现、Snapshot | Workspace 输入、分类结果和配置摘要 |
| SRS FR-RF-001~005 | Refinement、Resource、日期、状态筛选 | Refinement 控件生成条件 |
| SRS FR-RF-007~009 | 初始状态、状态关系、两条路径汇合 | Raw Query 与 Refinement 状态机 |
| SRS FR-QU-001 | Query Understanding | Effective Conditions 可见 |
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

## 7. 实施结构

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
  status: IDLE | SEARCHING | SUCCESS | EMPTY | ERROR
```

## 8. 评审闸门

- 评审必须确认 Raw Query/Refinement 分离和两条路径等价；
- 评审必须确认权限边界位于结果聚合和计数之前；
- 评审必须确认 CC-004 Preview 仍是唯一只读记录入口；
- 未经用户批准冻结，不得实现 CC-005。
