# CC-012 Global Search Dynamic Resource Selector & Permission-Safe Counts

## 0. Governance

| 项 | 内容 |
|---|---|
| Coding Contract | CC-012 |
| 版本 | v1.0 FROZEN |
| 状态 | FROZEN，已批准进入实施 |
| Intent ID | `GS-SEARCH-DYNAMIC-RESOURCE-SELECTOR-COUNTS` |
| 上游 SRS | [SRS_global_search](../../requirement/SRS_global_search.md) v1.4 FROZEN |
| 上游 TDD | [TDD_global_search](../../design/TDD_global_search.md) v0.3 FROZEN |
| 实施计划 | [IMPLEMENTATION_PLAN_global_search](../../implementation/IMPLEMENTATION_PLAN_global_search.md) v0.2 FROZEN，Phase 11 补充契约 |
| 前置 CC | CC-001~CC-011；TD-001 |
| 模块 | `wd_global_search` |
| 目标 | 让 Workspace Resource Selector 由 Published Configuration 驱动，支持多选，并展示经过当前用户权限边界后的 Resource Counts |

本 CC 只起草契约，不修改 SRS、TDD、CC-001~CC-011 或代码。它不重新定义
Configuration Lifecycle、Permission Boundary 或 Search API；实现时复用既有契约。

### DDD

N/A。本项目没有冻结 DDD；不得虚构聚合、实体、值对象或领域不变式编号。

## 1. Contract Goal

建立以下闭环：

```text
Published Configuration
        ↓
Authorized Business Resources
        ↓
Resource Descriptor
        ↓
Multi-select Resource Selector
        ↓
SearchRequest.resources
        ↓
Search Service
        ↓
CC-003 Permission Boundary
        ↓
Authorized Resource Counts
        ↓
Resource Selector Refresh
```

Resource Selector、Search Request、Search Response 的结果、计数和错误必须使用同一
服务端定义的稳定 `resource_key`。

## 2. Background and Acceptance Findings

### 2.1 Existing Contract Baseline

- CC-002 已定义 `resources` 为 Search Request 的资源范围数组，并返回
  `resource_counts`/`counts.by_resource` 结构；
- CC-003 要求模型、字段、Record Rule、公司和 Relation Path 遵守当前用户权限；
- CC-005 定义 Workspace Resource、日期/状态 Refinement、结果计数和当前用户边界；
- CC-007 定义 `PARTIAL_SUCCESS`、失败资源和计数一致性；
- CC-001 定义 Published Configuration、Business Resource、key、label 和 Snapshot；
- CC-008 要求日志/审计不泄露业务输入；
- CC-009 定义服务端语言和时区来源。

### 2.2 Current Implementation Findings

当前实现核查发现：

| 发现 | 分类 | 证据/影响 |
|---|---|---|
| Workspace 资源按钮从 `preview.MODEL_CONFIG` 硬编码生成 | Implementation Gap | 当前为 Contacts、Sales Orders、Transfers 三个固定入口 |
| 前端 `state.resource` 是单个字符串 | Implementation Gap | 只能发送一个资源范围 |
| Search API 已接受 `resources` 数组 | Existing Contract Support | 不需要新建 Search API |
| Facade/Aggregator 已返回 `resource_counts` 和 `counts.by_resource` | Existing Contract Support | 前端尚未绑定到 Selector |
| 当前 Executor 的成功计数来自资源结果，失败资源不进入 count | Existing Contract Support | 需补齐 UI 对失败与 authorized empty 的区分 |
| Published Snapshot 已包含 Business Resource key/label | Existing Contract Support | 可作为动态 Descriptor 来源 |
| 当前 Workspace 不显示所有 Published Resource | Requirement/Implementation Gap | 新增/退休 Resource 不会自动反映 |

验证方法：

| 发现 | 验证方法 |
|---|---|
| Resource 按钮硬编码 | 检查 `controllers/main.py` Workspace HTML 和资源注册来源 |
| 前端只能单选 | 检查前端 state、资源事件处理和请求 `resources` 构造 |
| API 已接受 resources 数组 | 检查 `controllers/main.py` SearchRequest 构造和 CC-002 |
| resource_counts 已返回 | 检查 `services/aggregator.py`、Facade response 和 API JSON |
| Snapshot 已包含 key/label | 检查 `models/configuration.py` `_build_snapshot` 和 Provider |
| 新增/退休 Resource 未自动反映 | 发布配置版本后执行 Workspace Descriptor 浏览器回归 |

以上是 CC-012 的验收发现，不修改既有冻结文档。若实现需要改变 CC-002 的响应字段
或 CC-003 的授权顺序，必须先走契约变更评审。

## 3. Scope

- 从当前有效 Published Snapshot 生成 Resource Descriptor；
- 服务端返回稳定的 `resource_key` 和本地化 `label`；
- Workspace 资源选择从单选改为多选；
- 保持 CC-002 的 `SearchRequest.resources` 数组语义；
- 将成功且授权的 `resource_counts` 绑定到 Selector；
- 区分 authorized empty 与 resource-level failure；
- Raw Query、Resource Selection、Date/State/其它 Refinement 后刷新计数；
- Published Version/cache 变化后按既有配置新鲜度语义刷新；
- 用户、公司、权限上下文和 Request 之间的计数隔离；
- 动态 Resource、权限、错误、分页和既有 Workspace 回归测试。

## 4. Out of Scope

- 不修改 SRS、TDD 或 CC-001~CC-011；
- 不重新定义 Configuration Lifecycle，复用 CC-001；
- 不重新实现权限系统，复用 CC-003；
- 不创建新的 Search API，不改变 CC-002 请求语义；
- 不把 Resource Count 变成数据库原始 count；
- 不引入 Elasticsearch、OpenSearch、LLM、向量检索或外部缓存；
- 不在浏览器计算 count；
- 不接受客户端提供 `uid`、company、groups、permissions；
- 不通过 `sudo()`、管理员环境或跨用户缓存获取 count；
- 不扩展业务 Resource 的语义、模型 ACL 或 Record Rule；
- 不把失败资源转换成 `(0)`；
- 不在本 CC 中修改官方 Odoo 代码。

## 5. Upstream Impact Analysis

### 5.1 CC-002 Search Service

**复用：**

- `resources: string[]`；
- `resource_counts`/`counts.by_resource`；
- 当前 Published Configuration version；
- `completed_resources`、`failed_resources`；
- 既有分页、cursor 和错误协议。

**缺口：**

- 需明确所有授权成功 Resource 是否都返回 count，包括 count=0；
- 失败 Resource 不得在 UI 被解释为 count=0；
- 若当前 `counts.by_resource` 只包含成功资源，需通过 `failed_resources` 明确失败状态，
  不得添加伪造的 0。

不建议修改 CC-002 冻结契约；优先在 CC-012 的 Descriptor 和 UI 映射层完成。
若需要改变 response shape，必须单独提出 CC-002 兼容性变更。

### 5.5 SRS/TDD 追溯

| SRS ID | 标题 | 本 CC 落实 |
|---|---|---|
| FR-SW-002 | 结果发现 | 动态 Resource Selector |
| FR-RF-002 | Business Resource 筛选 | 多选 Resource |
| FR-RF-003 | 日期筛选 | Date Refinement 后刷新 count |
| FR-RF-005 | 状态筛选 | State Refinement 后刷新 count |
| FR-SW-006 | 结果摘要 | Resource Count 显示 |
| FR-PM-001~003 | 权限继承、不扩大、无权不泄露 | Descriptor/count 权限过滤 |
| BR-013 | Result Count | 授权结果 count 定义 |
| CON-011 | 无权限字段不参与搜索 | Permission Boundary 后 count |

| TDD 章节 | 主题 | 本 CC 落实 |
|---|---|---|
| §3.6 | Result Identity 和计数 | count 与结果身份一致 |
| §6 | 权限边界 | Descriptor/count 授权顺序 |
| §8 | Workspace、结果和 Refinement | Selector、刷新和状态 |
| §9 | 错误协议 | Partial/Failure 与 count 区分 |


### 5.2 CC-003 Permission Boundary

**复用：**

- 当前用户 `env`/`UserContext`；
- 模型、字段、Record Rule、公司和 Relation Path 检查；
- 失败关闭；
- 不接受请求体权限声明；
- 权限过滤先于结果、分页和计数。

**新增约束：**

- Descriptor 本身只暴露当前用户有权使用的 Resource；
- count 必须来自同一权限边界之后的资源结果；
- 不得用 count=0 表达 unauthorized Resource；
- 不同用户/company/permission context/request 不共享授权 count。

不修改 CC-003 权限语义；CC-012 只规定 Selector/Count 消费边界。

### 5.3 CC-005 Workspace

**复用：**

- Raw Query 与 Refinement 分离；
- Resource、Date、State Refinement；
- Search API 和 Effective Conditions；
- 当前用户权限和失败关闭；
- Search/Refinement 后刷新结果。

**澄清：**

CC-005 的固定 Resource Tab 实现与 Published Configuration 动态 Descriptor 不一致。
CC-012 将其列为 Implementation Gap，并要求以服务端 Descriptor 取代前端 Registry；
不改变 CC-005 的 Search Workspace 总体语义。

### 5.4 CC-007 Error/Partial Failure

**复用：**

- `SUCCESS`、`EMPTY`、`PARTIAL_SUCCESS`、`FAILED`；
- `completed_resources` 和 `failed_resources`；
- 成功资源计数保留；
- 失败资源不得进入成功计数。

**新增 UI 规则：**

- authorized empty：显示 `Resource (0)`；
- resource failure：显示错误状态或 `—`，不得显示 `Resource (0)`；
- `PARTIAL_SUCCESS` 必须同时显示成功计数和失败 Resource 状态；
- 不以隐藏 Resource 或空成功响应掩盖失败。

## 6. Resource Descriptor Contract

服务端向 Workspace 提供稳定 Descriptor：

```json
{
  "resources": [
    {
      "key": "sale_order",
      "label": "Sales Orders"
    },
    {
      "key": "stock_picking",
      "label": "Transfers"
    }
  ],
  "config_version": 5
}
```

要求：

1. `key` 由服务端 Published Configuration 定义；
2. `label` 来自 Published Snapshot/Vocabulary 或服务端 i18n；
3. 前端不得从 model name 推导 key；
4. 前端不得维护第二份 Resource Registry；
5. Descriptor 只包含当前用户授权可用 Resource；
6. retired、removed、disabled 或不可访问 Resource 不得继续作为可用 Resource；
7. Descriptor 与 Search response 使用同一 `config_version`；
8. Descriptor 不返回无权 Resource 的 count、错误或存在性线索。

Descriptor 获取方式由实现选择以下一种，但不得新增第二套 Resource Registry：

- 独立的服务端 Descriptor API；或
- Search 响应中的 `meta.resources`；
- 必须复用当前 Published Snapshot 和 `config_version`；
- 不得由浏览器语言、model name 或客户端配置推导 Descriptor。

若项目已有 Descriptor 响应结构，实现必须复用，不创建第二套协议。

## 7. Published Configuration Binding

Workspace 每次建立或刷新搜索上下文时消费当前有效 Published Snapshot：

```text
Published Domain
  -> Published Version
  -> Snapshot resources
  -> Permission authorize_resource
  -> Resource Descriptor
```

场景：

- Scenario A：Published 有 Contacts、Sales Orders、Transfers，Selector 显示三者；
- Scenario B：发布新 Version 增加 Products，Selector 自动出现 Products；
- Scenario C：Resource retired/removed/disabled，Selector 不再显示；
- Scenario D：Resource 存在但当前用户无权访问，不显示，不用 `(0)` 暴露；
- Scenario E：Published Version 变化，Selector 和 count 使用同一新版本，不能混用旧缓存。

不重新定义 CC-001 的发布、退休、checksum 和 immutable 规则。

## 8. Multi-select Resource Contract

Selector 允许多个 Resource：

```text
☑ Contacts
☑ Sales Orders
☐ Transfers
☑ Products
```

请求保持 CC-002 结构：

```json
{
  "resources": ["contact", "sale_order", "product"]
}
```

约定：

- 初始状态为全部已授权 Resource；
- 取消一个 Resource 后保留其它选择；
- 取消全部 Resource 等价于“全部授权 Resource”，避免空数组产生歧义；
- Resource Selection 改变后立即重新 Search，或由实现明确采用显式 Search，但不得显示旧结果/旧 count；
- Raw Query 改变时保留 Resource Selection，除非 CC-005 现有语义要求重置；
- Refinement 改变时保留 Resource Selection；
- 客户端提交未知 key 时服务端忽略或失败关闭，不能扩大搜索范围；
- 客户端提交空数组 `[]` 等价于全部授权 Resource；
- 客户端提交的 key 全部未知时，服务端按空数组语义处理为全部授权 Resource，
  或返回 `INVALID_REQUEST`，实现必须固定且记录；
- 选择状态、请求 `resources`、结果 `_resource` 和 count key 必须一致。

## 9. Resource Count Contract

`resource_count` 定义为：

> 当前 Raw Query + Effective Refinement Conditions + Published Configuration +
> 当前用户 Permission Context 下，该 Business Resource 最终授权可见结果的数量。

不是：

- 数据库原始 count；
- 未应用 Record Rule 的 count；
- 分页页内数量；
- 未授权 Resource 的 0；
- 其它用户或其它 Request 的缓存值。

显示规则：

| Resource 状态 | Selector 显示 |
|---|---|
| 授权且有结果 | `Resource (N)` |
| 授权且结果为空 | `Resource (0)` |
| 资源级失败 | `Resource —` 或错误状态，不显示 `(0)` |
| 当前用户无权 | 不显示 Resource |

count 必须与 `Effective Conditions`、Published Version 和当前用户上下文一致。

软性能预算：

- 单次 Resource Count P95 ≤ 500ms；
- Count 刷新 P95 ≤ 1s；
- Count 与对应结果响应的完成时间差 ≤ 200ms；
- 超出预算记录观测事件，不得通过绕过 Permission Boundary 降低延迟。

## 10. Permission Boundary

强制顺序：

```text
Search
  ↓
Resource Executor
  ↓
Model/Field/Record Rule/Relation Permission Boundary
  ↓
Authorized Results
  ↓
Count
  ↓
resource_counts
```

禁止：

```text
Raw DB Count
  ↓
resource_counts
  ↓
Permission Filtering
```

不得使用 `sudo()`、superuser/admin env、请求体 uid/company/groups/permissions。
不得跨 user、company、request 或 permission context 共享授权 count。

## 11. Refresh Semantics

以下操作必须重新计算或刷新 Resource Counts：

1. Raw Query 改变；
2. Resource Selection 改变；
3. Date Refinement 改变；
4. State Refinement 改变；
5. 其它已定义 Refinement 改变；
6. Published Configuration Version/cache 变化；
7. Search 重新提交或 cursor/page 语义发生改变。

刷新期间应显示明确加载状态，不能继续显示与当前条件不一致的旧 count。

## 12. Partial Success and Error Semantics

遵循 CC-007：

- 成功 Resource：显示成功 count；
- authorized empty：显示 `(0)`；
- 失败 Resource：显示失败状态/错误提示，不伪装成 `(0)`；
- `PARTIAL_SUCCESS`：保留成功结果和 count，同时标记失败 Resource；
- 全部失败：显示 `FAILED`，不得显示空成功结果；
- `PERMISSION_DENIED`、`CONFIGURATION_ERROR` 和 `RELATION_PATH_BLOCKED` 不泄露资源、
  记录或规则细节；
- 错误中的 Resource key 也必须遵守当前用户可见性边界。

## 13. State Model

```text
IDLE
  -> LOADING_DESCRIPTOR
  -> READY
  -> SEARCHING
  -> PRESENTING_COUNTS
  -> PRESENTING_RESULTS
  -> PARTIAL_SUCCESS
  -> AUTHORIZED_EMPTY
  -> RESOURCE_FAILURE
  -> FAILED
```

任何新 Query、Selection 或 Refinement 使旧结果/count 失效时，进入 `SEARCHING`；
不得在新响应到达前把旧 count 当作当前值。

状态转换规则：

```text
IDLE -> LOADING_DESCRIPTOR       Workspace 初始化
LOADING_DESCRIPTOR -> READY      Descriptor 成功
LOADING_DESCRIPTOR -> FAILED     Descriptor 失败
READY -> SEARCHING               提交 Query/Selection/Refinement
SEARCHING -> PRESENTING_COUNTS   Count 响应到达
SEARCHING -> PRESENTING_RESULTS  Results 响应到达
PRESENTING_COUNTS -> PRESENTING_RESULTS
PRESENTING_RESULTS -> PARTIAL_SUCCESS
PRESENTING_RESULTS -> AUTHORIZED_EMPTY
PRESENTING_RESULTS -> RESOURCE_FAILURE
PRESENTING_RESULTS -> FAILED
任意可交互状态 -> SEARCHING       新请求使旧响应失效
```

## 13.1 Cache and Freshness

Descriptor 和 Count 均禁止跨用户、跨公司、跨 Permission Context 和跨 Request
共享。若实现引入缓存：

- Descriptor key 至少包含 user、company context 和 Published `config_version`；
- Count key 至少包含 request、user context、config version、resources 和
  Effective Conditions；
- 用户权限变化、公司变化或 Published Version 变化必须失效；
- Query、Selection、Refinement 或 cursor/page 变化必须失效；
- 未验证缓存隔离前不得启用业务结果缓存。

## 14. Security Invariants

| ID | 不变量 |
|---|---|
| CC12-INV-001 | Resource Selector 来源于当前 Published Configuration，不得硬编码 |
| CC12-INV-002 | 每个 Resource 使用服务端定义的稳定 `resource_key` |
| CC12-INV-003 | Request、Results、resource_counts、Selector 使用一致 key |
| CC12-INV-004 | Selector 支持多个 Resource 同时参与 Search |
| CC12-INV-005 | resource_counts 只统计最终授权可见结果 |
| CC12-INV-006 | Permission filtering 发生在最终 count 之前 |
| CC12-INV-007 | 不同用户、公司、Permission Context、Request 不共享授权 count |
| CC12-INV-008 | `count=0` 只表示授权搜索结果为空，不表示无权限 |
| CC12-INV-009 | Unauthorized Resource 不得通过 Selector/count/error/result 泄露 |
| CC12-INV-010 | Query/Refinement 改变后不得复用旧 count |
| CC12-INV-011 | Resource-level failure 不得伪装成 authorized empty |
| CC12-INV-012 | CC-012 不得绕过 CC-003 Permission Boundary |

## 15. API / Data Contract

不新增 Search API。沿用 CC-002：

```json
{
  "query": "GS-CUSTOMER-001",
  "conditions": [],
  "refinement_conditions": [],
  "resources": ["contact", "sale_order"],
  "limit": 20,
  "cursor": null
}
```

响应至少需要让前端区分：

```json
{
  "status": "PARTIAL_SUCCESS",
  "results": [],
  "resource_counts": {
    "contact": 1,
    "sale_order": 20
  },
  "meta": {
    "config_version": 5,
    "completed_resources": ["contact", "sale_order"],
    "failed_resources": []
  },
  "errors": []
}
```

若失败 Resource 不在 `resource_counts`，前端必须从 `failed_resources` 判断失败，
不能补成 0。

## 16. Frontend Contract

- 不维护硬编码 Resource Registry；
- 不从 model name、label 文本或结果数量推导 resource key；
- Descriptor label 以文本渲染；
- 复选状态与请求数组同步；
- count 只显示服务端返回值；
- 前端不计算、合并或猜测 count；
- Query/Refinement/Selection 改变时清理或标记旧响应；
- 不把失败 Resource 渲染为 `(0)`；
- 不展示无权 Resource；
- 资源、计数和结果排序保持稳定；
- 当前用户语言由服务端决定。

Selector UI 规范：

- 使用复选框列表，不使用前端硬编码 Resource Registry；
- 按 Published Configuration 顺序显示；
- 显示 `label + count`；
- 加载中显示 `Resource (…)`；
- 授权空结果显示 `Resource (0)`；
- 资源失败显示 `Resource —` 或错误状态；
- 无权 Resource 不显示；
- 选择变化后立即重新 Search，或显示明确的待提交状态，不得混用旧 count。

错误提示规范：

- `PARTIAL_SUCCESS`：显示成功 count 和失败 Resource 状态；
- `AUTHORIZED_EMPTY`：显示 `(0)`；
- `RESOURCE_FAILURE`：显示 `—`/受控错误；
- `FAILED`：显示通用失败和 request_id；
- 不显示原始 Query、条件值、字段值、SQL 或 Record Rule。

## 16.1 Logging and Observability

复用 CC-008 的 `services/observability.py` 和 Odoo 原生日志。Count/Descriptor
事件可记录：

- `request_id`
- `config_version`
- `resource`
- `status`
- `latency_ms`

禁止记录原始 Query、conditions、业务字段值、SQL、Record Rule、token 或完整结果。

## 17. Test Matrix

| ID | 测试内容 | 类型 | 预期 |
|---|---|---|---|
| CC12-TEST-001 | Published Configuration 动态生成 Resource | Odoo+API | Descriptor 来自当前 Published |
| CC12-TEST-002 | Descriptor key/label | API | key 稳定、label 服务端拥有 |
| CC12-TEST-003 | 新增 Published Resource | 集成+浏览器 | 无前端改动自动出现 |
| CC12-TEST-004 | Retired/Removed Resource | 集成+浏览器 | 不再作为可用 Resource |
| CC12-TEST-005 | Selector 多选 | 浏览器 | 多个 Resource 可同时选中 |
| CC12-TEST-006 | Request.resources 一致性 | API | 与选择状态完全一致 |
| CC12-TEST-007 | Count 绑定 | 浏览器 | Selector 显示服务端 count |
| CC12-TEST-008 | Authorized Empty | 集成+浏览器 | 显示 `(0)` |
| CC12-TEST-009 | Raw Query count refresh | 浏览器 | 不保留旧 count |
| CC12-TEST-010 | Date Refinement count refresh | 浏览器+API | 按当前时间范围重算 |
| CC12-TEST-011 | State Refinement count refresh | 浏览器+API | 按当前状态重算 |
| CC12-TEST-012 | Authorized count | ORM+集成 | count 等于最终授权结果 |
| CC12-TEST-013 | 不同用户 count | 多用户集成 | count 隔离 |
| CC12-TEST-014 | 公司/权限 context 隔离 | 多公司集成 | 不共享授权 count |
| CC12-TEST-015 | Unauthorized Resource | 多用户+浏览器 | 不泄露存在性 |
| CC12-TEST-016 | Partial Success | 故障注入+浏览器 | 失败不显示 `(0)` |
| CC12-TEST-017 | Pagination/count 兼容 | API | 与 CC-002 cursor/page 一致 |
| CC12-TEST-018 | Published version/cache refresh | 集成 | Selector/count 使用同一版本 |
| CC12-TEST-019 | CC-002 regression | Odoo+API | Search/Cancel/错误协议不回退 |
| CC12-TEST-020 | CC-003 regression | 多用户集成 | 权限边界不回退 |
| CC12-TEST-021 | CC-005 regression | 浏览器 | Query/Refinement/Preview 不回退 |
| CC12-TEST-022 | CC-007 regression | 故障注入 | EMPTY/PARTIAL/FAILED 语义不回退 |

浏览器兼容性矩阵：

| 浏览器 | 桌面 | 窄屏 |
|---|---|---|
| Chrome 最新 | 待验证 | 待验证 |
| Firefox 最新 | 待验证 | 待验证 |
| Safari 最新 | 待验证 | 待验证 |
| Edge 最新 | 待验证 | 待验证 |

Fixture 规范：

- 位置：`tests/fixtures/resource_selector/`；
- 覆盖 Published、Retired、Disabled Resource；
- 覆盖普通用户、Portal、多公司和部分授权；
- 覆盖 SUCCESS、PARTIAL_SUCCESS、EMPTY、FAILED；
- 使用唯一标记，测试结束验证 fixture 已清理；
- 不使用共享跨测试 Count 缓存。

验收场景：

1. Workspace 初始化显示所有授权 Published Resource；
2. 新增 Published Resource 后自动出现；
3. Resource retired 后消失；
4. 无权 Resource 不显示；
5. 多选和取消 Resource 后结果一致；
6. Query、Date、State 改变后 count 刷新；
7. Partial Success 显示成功 count 和失败状态；
8. Authorized Empty 显示 `(0)`；
9. 不同用户/公司看到隔离 count；
10. 检查日志无用户输入泄露。

HVR 场景：

1. 打开 Workspace 检查动态 Selector；
2. 多选/取消 Resource；
3. 改变 Query 和 Refinement 检查 count；
4. 观察 EMPTY、PARTIAL_SUCCESS、RESOURCE_FAILURE 和 FAILED；
5. 检查桌面/窄屏和浏览器控制台；
6. 核对 Odoo 日志和 request_id。

## 18. Regression Requirements

- CC-002 的 resources 数组、分页、cursor、counts 和错误结构保持兼容；
- CC-003 的当前用户、公司、字段、关系和失败关闭保持兼容；
- CC-005 的 Raw Query、Refinement、Effective Conditions 和 Preview 联动保持兼容；
- CC-007 的失败资源、PARTIAL_SUCCESS、EMPTY 和错误唯一性保持兼容；
- CC-008 的日志字段白名单和 audit 语义保持兼容；
- CC-009 的 label、语言和时区来源保持服务端唯一；
- CC-010 的 Published checksum 和配置版本不可被 Workspace 修改。
- Count 计算和刷新必须处于本 CC 的软性能预算内，超预算需记录并保留失败证据。

## 19. Stop Conditions

发现以下任一情况，不得直接实施：

1. CC-002 的 `resource_counts` 语义不足以区分授权空结果和资源失败；
2. CC-003 无法证明 count 在 Permission Boundary 之后计算；
3. CC-005 与多选/动态 Resource 语义存在未批准冲突；
4. Published Configuration 无法提供稳定 key/label；
5. 当前 API 无法安全表达多个 Resource；
6. count 在权限过滤前计算；
7. 存在跨用户或跨公司 count 缓存；
8. unauthorized Resource 会因 count=0、错误或 Descriptor 泄露；
9. 需要修改既有冻结契约但未完成影响评审；
10. 需要 `sudo()`、superuser/admin env 或直接数据库 count。

## 20. Definition of Done

- Descriptor 来自当前 Published Configuration；
- Selector 不再硬编码 Resource；
- Selector 支持多选并与 `resources[]` 一致；
- count 在当前用户权限边界后计算；
- authorized empty 与 resource failure 可区分；
- Query、Selection、Refinement 和 Published Version 改变会刷新 count；
- CC12-TEST-001~022 全部有证据，或有明确批准的延期；
- CC-002、CC-003、CC-005、CC-007 回归通过；
- 完成 IHR、ATR、HVR；
- 不修改 SRS/TDD/既有 CC，除非另行批准契约变更；
- 不修改 Odoo 核心或官方 addons；
- 未通过权限和错误门禁不得声明完成。

## 21. Decisions

| ID | 决策 | 替代方案 | 理由 |
|---|---|---|---|
| CC12-DEC-001 | Resource Descriptor 来自 Published Snapshot | 前端维护 Registry | 避免配置与 UI 漂移 |
| CC12-DEC-002 | 复用 CC-002 `resources[]` | 新建 Search API | 保持协议兼容 |
| CC12-DEC-003 | 默认选择全部授权 Resource | 默认空选 | 保持现有 Workspace “All” 语义 |
| CC12-DEC-004 | count 只来自授权结果 | Raw DB Count | 避免权限泄露 |
| CC12-DEC-005 | authorized empty 显示 0，failure 显示错误状态 | 两者都显示 0 | 保持 CC-007 失败语义 |
| CC12-DEC-006 | 失败 Resource 不进入成功 count | 失败补 0 | 不把失败伪装为空结果 |
| CC12-DEC-007 | 前端只展示服务端 count | 浏览器自行计算 | 防止权限和条件不一致 |
| CC12-DEC-008 | CC-003 是唯一 Permission Boundary | CC-012 重写权限系统 | 避免安全边界分裂 |
| CC12-DEC-009 | Descriptor 通过独立 API 或 Search `meta` 获取 | 前端硬编码 | 保持前端与 Published Configuration 解耦 |

未经用户批准冻结，不得实施 CC-012。

## 22. Data, Migration and Implementation Structure

- 不新增业务数据模型、业务字段或数据库表；
- 不迁移既有业务数据；
- Published Configuration 继续由 CC-001 生命周期管理；
- 若实现只增加 Descriptor/Selector API，不需要数据 migration；
- 若改变 Snapshot schema、Resource key 或 label 存储，必须先提出 CC-001/TDD
  兼容性评审，不在 CC-012 内隐式迁移；
- 实施代码预期位于 `controllers/`、`services/`、`static/src/` 和测试目录；
- 证据位于 `docs/context/history/`，不修改官方 addons；
- Fixture 仅用于隔离测试，不能替代当前用户 ORM 权限验证。
