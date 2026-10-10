# CC-012 Global Search Dynamic Resource Selector & Permission-Safe Counts

## 0. Governance

| 项 | 内容 |
|---|---|
| Coding Contract | CC-012 |
| 版本 | v1.1 FROZEN |
| 状态 | FROZEN，2026-10-08 17:28 用户批准进入实施 |
| Intent ID | `GS-SEARCH-DYNAMIC-RESOURCE-SELECTOR-COUNTS` |
| 上游 SRS | [SRS_global_search](../../requirement/SRS_global_search.md) v1.4 FROZEN |
| 上游 TDD | [TDD_global_search](../../design/TDD_global_search.md) v0.3 FROZEN |
| 实施计划 | [IMPLEMENTATION_PLAN_global_search](../../implementation/IMPLEMENTATION_PLAN_global_search.md) v0.2 FROZEN，Phase 11 补充契约 |
| 前置 CC | CC-001~CC-011；TD-001 |
| 模块 | `wd_global_search` |
| 目标 | 让 Workspace Resource Selector 由 Published Configuration 驱动，支持多选，并展示经过当前用户权限边界后的 Resource Counts |
| 批准冻结 | 2026-10-08 17:28，用户批准冻结 CC-012 并进入实施 |

本次修订替代 v1.0 中与空选择、零计数显示和 Resource Selection/Count 语义冲突的
规定。除本文明确限定的 Resource Selector 与 Resource Count 行为外，不重定义
Configuration Lifecycle、Permission Boundary、Search API 路由或 CC-002 的分页协议。
本文件是 CC-012 v1.1 冻结契约。实施必须遵守下述边界，不得修改 SRS/TDD 或扩展为新的 Search API。

### 修订记录

| 版本 | 变更 |
|---|---|
| v1.0 | Published Resource 动态化、多选和基础权限计数契约 |
| v1.1 FROZEN | 明确多选初始态、空选择不搜索、零计数隐藏、失败状态、完整授权计数及 Facet 与结果范围分离 |

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
Authorized Facet Counts for all eligible Resources
        ↓
Resource Selector Refresh
```

Selector 使用 Published Resource 中服务端定义的稳定 `resource_key`。本次请求中
所有 Published 且授权的 Resource 都参与 Selector Facet Count；`resources[]`
只限定实际返回的 Search Results。Facet count 不因当前 Resource Selection 把其它
Resource 人为变成 0，因此未选但有结果的 Resource 仍可见并可重新选择。

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
| Workspace Resource Descriptor | 已有实现 | Controller 从当前 Published Snapshot 取 key/label，并先作 model read ACL 检查 |
| 多选 | 已有实现但语义不完整 | JS 使用 `Set`；按钮可多选 |
| 空 `resources[]` | 与本修订冲突 | Facade 仅在 scope 非空时过滤，故空数组代表全资源搜索 |
| 默认选择状态 | 与本修订冲突 | 前端 Set 初始为空、按钮初始未选；请求空数组却由服务端扩大为全部 Resource |
| Count API | 部分实现 | `search_count(domain)` 已调用，但 `execute()` 最终将 count 覆盖为当前 `len(results)`，会受 fetch limit 影响 |
| Resource Count 响应 | 部分实现 | Aggregator 只统计实际执行成功的 Resource；Controller 的 `resource_counts` 是 `counts.by_resource` 别名，未提供未选 Resource 的 Facet Count |
| 失败状态 | 部分实现 | Aggregator 从 errors/meta 暴露失败 Resource；UI 只显示通用 partial message，单资源状态未与 Selector 项关联 |
| count=0 UI 行为 | HEAD 与工作区有差异 | 已提交 JS 对成功的 0 显示 `0`；当前工作区另有未提交改动会隐藏 0，但不清理 Set 中对应选择 |
| Published Resource 动态显示 | 已实现基础部分 | Controller 使用 Published Snapshot key/name；资源移除/版本刷新和动态重载未形成完整 HVR |

验证方法：

| 发现 | 验证方法 |
|---|---|
| Selector 来源、初始选择和资源 key | 检查 `controllers/main.py`、`preview.js`、Published Snapshot |
| 空 scope 的实际行为 | 检查 Facade 对 `request.resource_scope` 的过滤分支 |
| 计数是否受 limit 影响 | 检查 Executor 的 `search_count()`、最终 ResourceOutcome.count 和 Aggregator |
| 当前页面 0/失败显示 | 比较 HEAD 与工作区 `preview.js`，检查 renderCounts 和错误渲染 |

### 2.3 当前行为问题的直接答复

1. **CC-012 是否已定义 Resource Selector：** 是；v1.0 定义了 Published Snapshot
   Descriptor 和多选，但零结果显示、空选择语义和 Facet/Result Count 分离与本次规则冲突。
2. **当前是否支持多 Resource：** 前端 `state.resources: Set` 与请求数组支持多选；
   但空 Set 被服务端按“全部资源”解释，未符合新规则。
3. **当前 Request Contract：** `/wd_global_search/api/search` 的 JSON `resources`
   进入 `SearchRequest.resource_scope: tuple[str, ...]`；Facade 只在 tuple 非空时过滤，
   因此空数组目前表示全资源。
4. **当前 Count Contract：** Controller 的 `resource_counts` 是
   `counts.by_resource` 的别名；Aggregator 只统计实际执行成功的 Resource。
   Executor 虽调用 `model.search_count(domain)`，最终 ResourceOutcome 却将 count
   覆盖成 fetch 后的 `len(results)`，所以会受执行 limit 截断。当前也没有未选
   Resource 的 Facet Count。
5. **当前 UI 是否单选：** 不再是单选；JS `Set` 支持多选，Workspace buttons 来自
   Published Resource。但初始没有 selected 按钮，而空 Set 会被服务端解释成全选。
6. **当前 count=0 UI 行为：** 已提交 HEAD 显示 `0`；当前未提交工作区 JS 改动会隐藏
   count=0 项，但没有从 selection Set 移除该 key。新契约要求隐藏且取消选择。
7. **Search Service 是否支持 `resources[]`：** 是，现有 Search API/SearchRequest
   支持多 key；无需新 API。必须修正空数组实现语义。
8. **CC-003 Resource Authorization：** 以当前请求用户环境检查 model read access、
   searchable field 和 Relation Path；ORM 查询遵守当前 Record Rule 与公司上下文；
   权限失败关闭，不得用 `sudo()` 读取业务数据。
9. **CC-005 Workspace / CC-007 Partial Success：** CC-005/SRS 已规定零结果 Resource
   不显示且计数随 Refinement 更新；CC-007 规定失败与 Empty 不混淆、只统计成功资源、
   保留 `failed_resources`。本修订细化而不推翻其基线。
10. **是否修改其它冻结文档：** 不需要。SRS FR-RF-002/FR-PM-007/BR-013 已覆盖筛选、
    零结果隐藏、权限与精确计数；TDD/CC-002 资源数组结构可复用；CC-003/005/007
    语义一致。仅运行时代码需按本 CC 修正空数组、Facet Count 和 count 截断实现。

以上是 CC-012 的验收发现，不修改既有冻结文档。若实现需要改变 CC-002 的响应字段
或 CC-003 的授权顺序，必须先走契约变更评审。

## 3. Scope

- 从当前有效 Published Snapshot 生成 Resource Descriptor；
- 服务端返回稳定的 `resource_key` 和本地化 `label`；
- Workspace 资源选择采用多选，初始选择全部当前可参与搜索的授权 Resource；
- 未选择任何 Resource 时不得运行结果搜索；可通过既有 Search API 请求 count-only Facet 刷新，并提示至少选择一个 Resource；
- Facet Count 对所有当前授权候选 Resource 计算，结果集仍严格受 `resources[]` 选择范围约束；
- 授权结果 count 为 0 的 Resource 自动隐藏并取消选择；正数 Resource 自动显示；
- 失败 Resource 保持可见的失败状态，count 为 unknown，不被隐藏或表示为 0；
- 保持 CC-002 的 `SearchRequest.resources` 数组语义；
- 将精确、完整且经权限过滤的 Resource Facet Counts 绑定到 Selector；
- 区分授权空结果、失败、超时和部分成功；
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
- 不改变 CC-002 的 Search API 路径、请求字段、分页/cursor 或响应顶层协议；
- 不把未选 Resource 的 facet count 当作其 Search Results，也不把它加入结果总数。

## 5. Upstream Impact Analysis

### 5.1 CC-002 Search Service

**复用：**

- `resources: string[]`；
- `resource_counts`/`counts.by_resource`；
- 当前 Published Configuration version；
- `completed_resources`、`failed_resources`；
- 既有分页、cursor 和错误协议。

**缺口：**

- `resources[]` 选择范围与 Selector Facet Count 范围必须分开：被取消选择的资源仍参与 facet count；
- 所有当前授权候选 Resource 均需尝试计数，成功返回精确 count（可为 0），失败通过现有 errors/failed_resources 表达；
- `counts.by_resource` 作为结果选择 scope 的响应计数不能单独支撑未选资源的 Facet；实现可以在同一 SearchResponse/meta 中提供 Facet count 映射，但不得新建 Search API 或改变 CC-002 顶层响应协议；
- Result count 必须按 Result Identity 精确去重、在权限边界后、且不受 page limit 影响。当前 Executor 的最终 ResourceOutcome count 被 `len(results)` 覆盖，实施必须修复该差异。

复用 CC-002 Search API 路径、请求结构和错误协议；若 Facet count 需要新增内部映射，
仅允许在既有 `counts`/`meta` 响应扩展中表达，不得重新定义 Search API。若需要改变
既有字段语义或顶层 shape，必须先单独提出 CC-002 兼容性评审。

### 5.5 SRS/TDD 追溯与上游影响结论

本修订依赖 SRS v1.4 已冻结的 FR-RF-002、FR-PM-007、BR-013、AC-040：

- FR-RF-002 已规定按 Business Resource 筛选，且只显示当前结果集中有数据的 Resource；
- FR-PM-007 已规定无权 Resource 不显示、有权但当前结果为空也不显示；
- BR-013 已规定分类 count 按 Result Identity 去重、精确且不受分页影响；
- CC-007 已区分 EMPTY、TIMEOUT、PARTIAL_SUCCESS、FAILED。

多选是对 SRS Business Resource 筛选交互的细化；SRS/TDD 未规定必须为互斥单选，
因此可保持现有 Tab/selector 呈现形式而支持多项同时 active。本 CC 不要求改动
SRS、TDD、Implementation Plan 或 CC-001~CC-011 的文档与版本。运行时代码必须遵循
本 CC 对 `resources: []` 的定义；CC-002 既有请求字段仍为资源 key 列表，顶层 Search
API 协议不变。

| 上游 | 是否修改 | 影响结论 |
|---|---|---|
| SRS v1.4 | 否 | 新语义与 FR-RF-002 / FR-PM-007 / BR-013 / AC-040 一致 |
| TDD v0.3 | 否 | SearchRequest.resource_scope 已为 key 列表；权限、Result Identity 和分页计数均有定义 |
| Implementation Plan v0.2 | 否 | Phase 11 已容纳补充 Coding Contract；不新增项目阶段 |
| CC-001 | 否 | 复用 Published lifecycle、稳定 key、name/label 和 Snapshot |
| CC-002 | 否（API 合同） | 复用现有 Search API 与 resources 数组；实现需将 empty scope 改为 no-results scope，并扩展既有 Resource Count 聚合语义 |
| CC-003 | 否 | 沿用当前用户、公司、字段、Record Rule 和失败关闭边界 |
| CC-004 | 否 | Preview 与 Resource Selector 无行为变化 |
| CC-005 | 否 | 仅细化已有动态资源过滤、计数和 Workspace 交互 |
| CC-006 | 否 | 不改变索引和性能策略 |
| CC-007 | 否 | 直接继承 failure ≠ empty、partial success 语义 |
| CC-008 | 否 | 沿用观测字段白名单 |
| CC-009 | 否 | Resource label 仍由服务端本地化 |
| CC-010 | 否 | Published snapshot/version 不变 |
| CC-011 | 否 | 更新本 CC 的 ATR/HVR 后再进入最终验收汇总 |

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
- 每个 Resource 的结果和 Facet count 必须使用当前请求的 `env`/公司上下文并遵守 Record Rule；
- 不得先获得越权/全局 count 再应用 Permission Filter；
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
CC-005 §2.2 和 SRS FR-RF-002/FR-PM-007 已规定只有当前有结果的资源才显示；
本 CC 具体化其为由当前条件下 Facet Count 驱动的动态多选 Selector。空选择不发起
请求，不将 `resources: []` 当成全选。此为既有上游语义的实现补全，不改变 Workspace
其它语义。

### 5.4 CC-007 Error/Partial Failure

**复用：**

- `SUCCESS`、`EMPTY`、`PARTIAL_SUCCESS`、`FAILED`；
- `completed_resources` 和 `failed_resources`；
- 成功资源计数保留；
- 失败资源不得进入成功计数。

**新增 UI 规则：**

- authorized empty：从 Selector 隐藏，不能展示 `(0)`；
- resource failure/timeout：保留 Resource Descriptor 并显示 `—`/统一失败状态，
  不得隐藏成空结果，也不得展示 `(0)`；
- `PARTIAL_SUCCESS` 必须同时显示成功计数和失败 Resource 状态；
- 不以隐藏 Resource 或空成功响应掩盖失败。Failure Resource 若按权限策略不可暴露，
  应遵循 CC-003/CC-007 的通用错误约束，不能由 CC-012 产生额外存在性线索。

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
  -> Published/active Snapshot resources
  -> CC-003 Resource authorization
  -> Authorized Resource Descriptor candidates
  -> per-request Facet Count and Execution Status
  -> visible/hidden Selector entries
```

场景：

- Scenario A：首次搜索时默认选择所有授权候选 Resource；成功 count=0 的 Resource 隐藏并取消选择；
- Scenario B：发布新 Version 增加 Resource，新版本请求可动态获得其 Descriptor 和 Facet Count；
- Scenario C：Resource retired/removed/disabled，下一次以新 Published Version 处理时消失；
- Scenario D：Resource 存在但当前用户无权访问，不生成 Descriptor/count/error；
- Scenario E：Published Version 变化，Descriptor、结果和 count 使用同一版本，不能混用旧值；
- Scenario F：先前为 0 的 Resource 在 Raw Query/Refinement 改变后变为正数时重新显示，初始为未选中；
- Scenario G：Resource 失败或超时保留可见错误状态，不得作为 0 隐藏。

不重新定义 CC-001 的发布、退休、checksum 和 Apply 规则；Workspace 不得修改配置，管理员 Apply 的变更由配置管理界面和 CC-001 契约控制。

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

- 首次搜索前隐藏 Resource Selector；内部默认 selection 为全部当前已授权、可参与搜索的 Published Resource；
- 首次提交 Query 时必须将该资源集合显式序列化为 `resources: [stable_key, ...]`，不得发送空数组；
- 首次搜索响应到达后，Selector 才按 Facet Count 显示 count>0 和执行失败的 Resource；
- Resource 选择可以多选；取消一项只移除该稳定 key，保留其它选择；
- 用户主动取消全部后，空 `resources: []` 明确表示“没有选中任何结果 Resource”，绝不表示全部；
- 空选择时不执行/返回全资源结果查询；Search Response `results` 必须为空，UI 提示“至少选择一个 Resource”；
- 空选择时仍可通过同一 Search API 刷新所有授权候选 Resource 的 Facet Count/错误状态，以便当前 Query 改变后重新显示正数 Resource；该 count-only 请求必须令结果列表为空，绝不能把 `resources: []` 解释为全资源结果搜索；
- 全部资源因 count=0 隐藏后，Selector 显示空状态及显式“重新选择全部可访问资源”操作；只有用户触发后才重新选择并执行全资源结果搜索；
- `resources[]` 必须与用户当前选中且当前可选的稳定 key 完全一致；不得补全或替换为空全选；
- Raw Query、Date/State/其它非 Resource Refinement 改变时保留当前选择；若选择为空，只刷新 Facet Count，不返回业务结果；
- 成功 count=0 时立即隐藏该项并取消选择；count>0 时显示该项；此前隐藏的项恢复时默认为未选中；
- Resource Selection 改变后立即刷新结果与 Facet Count；旧响应和旧 count 立即失效；
- 客户端提交未知/retired key 必须失败关闭为 `INVALID_REQUEST` 或安全的配置错误，不得静默扩大范围；
- Search Results 的 `_resource` 与用户选中 key 一致；Facet Count/错误使用相同服务端 key。

## 9. Resource Count Contract

`resource_count` / Resource Facet Count 定义为：

> 当前 Raw Query、Date/State/其它非 Resource Refinement、同一 Published Version 和
> 当前用户 Permission Context 下，该 Resource 经 CC-003 授权后的最终 Result Identity
> 总数。该 Facet 计数对每个候选 Resource 独立计算，不受用户当前选择了哪些其它
> Resource 影响；`resources[]` 仅约束实际返回的结果集合。

Selector Facet Count 不是：

- 数据库原始 count；
- 未应用 Record Rule 的 count；
- 当前页 `results.length`；
- 被 page limit 截断的长度；
- 未授权 Resource 的 0；
- 其它用户或其它 Request 的缓存值。

结果计数与 Facet Count 分离：

| 字段 | 语义 |
|---|---|
| `counts.all` | 当前选中 Resource 的最终授权 Result Identity 总数；不受分页影响 |
| `counts.by_resource` | 当前选中且成功 Resource 的最终授权结果总数 |
| `resource_counts` | 所有当前授权候选 Resource 的 Facet Count；未选 Resource 仍可有 count |
| `meta.failed_resources` / `errors` | 对应 Facet 或结果执行失败的授权 Resource；绝不补零 |

Count pipeline:

```text
Published Resource candidates
  -> CC-003 model/field/company/Record Rule authorization
  -> Effective Query + non-resource Refinements
  -> authorized, deduplicated Result Identity set
  -> exact total count (before pagination)
  -> resource_counts
```

显示/选择规则：

| Resource 状态 | Selector 显示 |
|---|---|
| 当前 Published、已授权、Facet 成功且 count > 0 | 显示 `Label N`；若新出现则未选中 |
| 当前 Published、已授权、Facet 成功且 count = 0 | 隐藏并清除 selection |
| 已授权候选但执行失败/超时，count unknown | 保持可见；显示统一 failure/timeout 状态；不自动变成 0 |
| 未授权 / 不在当前 Published Resource 候选集 | 完全不显示，也不返回 Descriptor/count/error key |
| 首次搜索前 | 整个 Resource Selector 隐藏；首次请求显式带全部当前授权候选 key |
| 用户取消全部 / 所有成功 count 均为 0 | 显示空选择提示；提供显式“重新选择全部可访问资源”操作，不静默扩大 Search scope |

Facet Count 必须与 Query、非 Resource Refinement、Published Version 和当前 Permission
Context 一致。Resource Selection 改变时重新刷新 Facet/状态，但不能通过改变所选项将
未选 Resource 的 Facet count 置 0。

软性能预算：

- 单次 Resource Count P95 ≤ 500ms；
- Count 刷新 P95 ≤ 1s；
- Count 与对应结果响应的完成时间差 ≤ 200ms；
- 超出预算记录观测事件，不得通过绕过 Permission Boundary 降低延迟。

## 10. Permission Boundary

强制顺序：

```text
Published candidate
  -> 当前用户 ORM 环境与 CC-003 授权
  -> 应用 Query + non-resource Refinements
  -> ORM Record Rule / company / field permission filtering
  -> deduplicate by Result Identity
  -> exact count
  -> resource_counts
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
6. Search 重新提交；
7. Published Configuration Version/cache 变化；
8. 服务端当前 Permission Context 改变（uid/company/groups/rules 等）。

Resource Selection 改变也重新发起既有 Search API 请求，以更新所选结果、Selector
Facet Counts 和执行状态；Facet Query 对 Resource Selection 本身采用 self-excluding
语义。分页/cursor 只影响返回页，不改变精确总数，但新 Query/Refinement/Version/权限
上下文必须使旧 cursor/count 失效。

刷新期间先清除/标记旧 counts、错误状态和旧结果。响应必须与当前 request generation
及 `config_version` 匹配，否则丢弃；不得短暂复用不兼容的旧 count。

## 12. Partial Success and Error Semantics

遵循 CC-007：

- 成功 Resource 且 count > 0：显示精确 count；
- 成功 Resource 且 count = 0：标记 authorized empty，隐藏并取消选择；
- 失败/超时 Resource：count 为 unknown，保持可见且显示 CC-007 对应错误状态，
  不伪装成 0，也不按 empty 隐藏；
- `PARTIAL_SUCCESS`：保留成功结果和 count，同时标记失败 Resource；
- 空 `resources[]`：不运行/返回任何 Resource Results，返回空选择提示；Facet Count
  仍可按上述授权候选流程更新，绝不能将空数组扩成全资源结果 scope；
- 全部失败：显示 `FAILED`，不得显示空成功结果；
- `PERMISSION_DENIED`、`CONFIGURATION_ERROR` 和 `RELATION_PATH_BLOCKED` 不泄露资源、
  记录或规则细节；
- 错误中的 Resource key 也必须遵守当前用户可见性边界。

## 13. State Model

每 Resource 使用彼此独立的 `AUTHORIZED`、`VISIBLE`、`SELECTED`、`COUNT`、
`EXECUTION_STATUS` 状态，不能由一个字段推导其它状态：

| 示例 | Authorized | Visible | Selected | Count | Status |
|---|---:|---:|---:|---:|---|
| A | true | true | true | 10 | SUCCESS |
| B | true | false | false | 0 | SUCCESS |
| C | true | true | false（默认）/保持用户选择 | unknown | TIMEOUT/FAILED |
| D | false | false | false | 不存在 | 不向客户端暴露 |

全局 UI 状态：

```text
IDLE -> LOADING_DESCRIPTOR -> READY
READY -> SEARCHING                     非空选中集，执行结果与 Facet
READY -> FACET_REFRESHING              空选中集，仅刷新 Facet/状态，不执行结果搜索
INITIAL -> FIRST_SEARCH                Selector hidden；显式提交全部授权候选 key
SEARCHING -> SUCCESS | EMPTY | PARTIAL_SUCCESS | FAILED
FACET_REFRESHING -> READY | PARTIAL_SUCCESS | FAILED
EMPTY_SELECTION -> EXPLICIT_RESELECT_ALL -> SEARCHING
任意状态 -> 新 request generation      丢弃旧响应/旧 count
```

任何新 Query、Selection 或 Refinement 使旧结果/count 失效时，进入 `SEARCHING`；
不得在新响应到达前把旧 count 当作当前值。

状态转换规则：

```text
IDLE -> LOADING_DESCRIPTOR       Workspace 初始化
LOADING_DESCRIPTOR -> READY      Descriptor 成功
LOADING_DESCRIPTOR -> FAILED     Descriptor 失败
READY -> SEARCHING               `resources[]` 非空
READY -> FACET_REFRESHING        `resources[]` 为空；不运行结果搜索
SEARCHING -> SUCCESS             至少一个结果 Resource 成功且无失败
SEARCHING -> EMPTY               选中 Resource 成功但结果为空
SEARCHING -> PARTIAL_SUCCESS     至少一个成功且至少一个失败
SEARCHING -> FAILED              无可安全返回的结果/请求级失败
FACET_REFRESHING -> READY        Facet 全部成功，results 必为空
FACET_REFRESHING -> PARTIAL_SUCCESS / FAILED
任意可交互状态 -> 新 request generation     使旧响应/count 失效
```

## 13.1 Cache and Freshness

Descriptor 和 Count 均禁止跨用户、跨公司、跨 Permission Context 和跨 Request
共享。若实现引入缓存：

- Descriptor key 至少包含 user、company context 和 Published `config_version`；
- Count key 至少包含 request generation、user context、config version、candidate
  Resource set 和 Effective Query/non-resource Refinements；
- 当前选择集可以作为响应/结果 scope 的 request 参数，但不改变每个候选 Resource 的
  self-excluding Facet Count；
- 用户权限变化、公司变化或 Published Version 变化必须失效；
- Query、Selection、Refinement 或 cursor/page 变化必须失效；
- 未验证缓存隔离前不得启用业务结果缓存。

## 14. Security Invariants

| ID | 不变量 |
|---|---|
| CC12-INV-001 | Resource Selector 来源于当前 Published Configuration，不得硬编码 |
| CC12-INV-002 | 每个 Resource 使用服务端定义的稳定 `resource_key` |
| CC12-INV-003 | Search Request、Results、`resource_counts` 和 Selector 使用相同 `resource_key`；选择 scope 只限制 Results，不扩大/缩小 Facet candidate set |
| CC12-INV-004 | Resource Selector 支持多个 Resource |
| CC12-INV-005 | `resource_count` 是当前用户最终授权 Result Identity 数，不是 page length |
| CC12-INV-006 | Permission Filtering 与 Result Identity 去重必须发生在最终 count 之前 |
| CC12-INV-007 | Authorized count 不得跨 user/company/permission context/request 共享 |
| CC12-INV-008 | count=0 只表示当前条件下授权结果为空；只触发隐藏，不表示 Resource 不存在 |
| CC12-INV-009 | Unauthorized Resource 不得通过 Selector/count/error 或其它 UI 泄露存在性 |
| CC12-INV-010 | Query/Refinement/selection/version/permission context 改变后不得复用失效 count |
| CC12-INV-011 | Resource execution failure/timeout 不得转换成 count=0，也不得因此隐藏 |
| CC12-INV-012 | CC-012 不得绕过 CC-003 Permission Boundary |
| CC12-INV-013 | Authorized、Visible、Selected、Count、Execution Status 是语义独立状态 |

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

`resources` semantics:

- 必须与 UI 当前选中 key 集完全一致；
- 非空数组仅限制 Search Results；
- 空数组是显式空结果 scope，不得被解释为全资源；
- 空数组请求的 `results` 必须为空；服务端可在同一请求中运行 count-only
  Facet 计算，以供零选择提示状态刷新 Selector；
- 未知、Retired 或不在当前 Published Snapshot 的 key 必须安全拒绝，不得扩成全资源。

响应至少需区分 Result Count、Facet Count 和失败：

```json
{
  "status": "PARTIAL_SUCCESS",
  "results": [{"_resource": "contact", "_model": "res.partner", "_record_id": 42}],
  "counts": {
    "all": 1,
    "by_resource": {"contact": 1}
  },
  "resource_counts": {
    "contact": 1,
    "sale_order": 3,
    "stock_picking": 2
  },
  "meta": {
    "config_version": 5,
    "completed_resources": ["contact", "sale_order", "stock_picking"],
    "failed_resources": ["purchase_order"]
  },
  "errors": [
    {"code": "TIMEOUT", "resource": "purchase_order", "retryable": true}
  ]
}
```

响应约定：

- `counts` 只汇总所选 Resource 的结果集；
- `resource_counts` 是所有已授权候选 Resource 的 Facet Count，包括未选的成功资源；
- 失败资源不得写入 `resource_counts` 数字 map；前端用 `failed_resources`/`errors`
  显示 unknown 状态，不能补零；
- 未授权资源不得出现在以上任何 key 集合；
- `meta.config_version` 必须绑定 Descriptor、结果、count、错误；
- `resource_counts` 保留现有顶层字段，不创建新的 Search API。

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
- 初始选中所有当前已授权且可参与搜索的 Published Resource；
- 在首次 Query 提交前隐藏 Selector；首个 Query 以全部授权候选 key 显式搜索；
- 完成首个响应后才展示有结果及失败的 Resource；
- 显示 `label + exact facet count`；
- loading/unknown 显示 `Resource …`；
- 成功 count=0 后自动隐藏并取消选择，不显示 `(0)`；
- 成功 count>0 显示且可选择；之前隐藏的 Resource 恢复时默认未选中；
- Resource 失败/超时保持可见，显示项目统一错误状态或 `—`，不显示 0；
- 无权 Resource 不显示；
- 空选择显式显示“至少选择一个 Resource”，不提交全资源结果搜索；
- 当 Selector 因 count=0 全部隐藏时提供显式“重新选择全部可访问资源”操作；
- 该操作先明确恢复选择状态，然后以非空 key 数组发出 Search，不得将空数组默认为全选；
- 空选择时允许同一 API 只刷新 Facet 状态，结果必须为空；
- 选择变化后刷新 Search/Facet，不得混用旧结果、旧 count 或旧错误状态。

错误提示规范：

- `PARTIAL_SUCCESS`：显示成功 count 和失败 Resource 状态；
- `EMPTY` / authorized count=0：不在 Selector 显示 `(0)`，隐藏该 Resource；
- `TIMEOUT` / `RESOURCE_FAILURE`：显示 `—` 或受控错误，不隐藏成 empty；
- `FAILED`：显示通用失败和 request_id；
- 空 selection：提示至少选择一个 Resource；
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
| CC12-TEST-001 | Published Configuration 动态生成 Resource Selector | Odoo+API | Descriptor 来自当前 Published |
| CC12-TEST-002 | Descriptor 使用稳定 `resource_key` | API | key 唯一、稳定、由服务端提供 |
| CC12-TEST-003 | 新增 Published Resource | 集成+浏览器 | 无 frontend registry/code 修改即可获取 |
| CC12-TEST-004 | Retired/removed Resource | 集成+浏览器 | 新 Published Version 后消失 |
| CC12-TEST-005 | Resource Selector 多选 | 浏览器 | 多个 Resource 可同时选中 |
| CC12-TEST-006 | Search Request.resources 一致性 | API | 数组精确匹配用户选择；空数组不扩成全资源 |
| CC12-TEST-007 | Authorized Resource count 正确 | ORM+集成 | 等于最终授权 Result Identity 数 |
| CC12-TEST-008 | count=0 自动隐藏 | 浏览器 | 成功空资源隐藏且取消选择 |
| CC12-TEST-009 | count>0 自动显示 | 浏览器 | 正数资源显示；重新出现时未选中 |
| CC12-TEST-010 | Raw Query 改变刷新 count | 浏览器+API | 所有 Facet 重算，0↔正数正确隐藏/出现 |
| CC12-TEST-011 | Date Refinement 改变刷新 count | 浏览器+API | 按新日期条件精确重算 |
| CC12-TEST-012 | State Refinement 改变刷新 count | 浏览器+API | 按新状态条件精确重算 |
| CC12-TEST-013 | Count 与 page result length 分离 | API+ORM | 37 条 total/page limit 20 时 count=37 |
| CC12-TEST-014 | Unauthorized Resource 不显示 | 多用户+浏览器 | 无 Descriptor、count 或状态线索 |
| CC12-TEST-015 | Unauthorized Resource 不以 0 暴露 | 多用户+API | unauthorized key 不出现在 Facet map |
| CC12-TEST-016 | Resource Timeout | 故障注入+浏览器 | 显示 Timeout/unknown，不是 0/hidden |
| CC12-TEST-017 | Resource Failure | 故障注入+浏览器 | 显示统一失败状态，不是 0/hidden |
| CC12-TEST-018 | Partial Success | 故障注入+浏览器 | 成功 counts/results 保留，失败 Resource 可辨识 |
| CC12-TEST-019 | 所有 Resource 成功但 count=0 | 集成+浏览器 | Search `EMPTY`，Selector 隐藏零项 |
| CC12-TEST-020 | A count=0、B count>0 | 集成+浏览器 | 仅 B 显示 |
| CC12-TEST-021 | 隐藏 Resource 在后续 Query 转为正数 | 浏览器+API | Resource 重新出现并未选中 |
| CC12-TEST-022 | 不同用户 Count 隔离 | 多用户集成 | 不共享 Facet Count |
| CC12-TEST-023 | 公司/权限 Context 隔离 | 多公司集成 | 不共享授权结果/Count |
| CC12-TEST-024 | Published Config Version 改变 | 集成 | Descriptor、Facet 和 Results 使用同一新版本 |
| CC12-TEST-025 | CC-002 Search Service regression | Odoo+API | Search/Cancel/page/cursor/错误协议不回退 |
| CC12-TEST-026 | CC-003 Permission Boundary regression | 多用户集成 | 当前用户/公司/字段/Record Rule 语义不回退 |
| CC12-TEST-027 | CC-005 Workspace regression | 浏览器 | Query/Refinement/Preview/空选择提示一致 |
| CC12-TEST-028 | CC-007 Error Protocol regression | 故障注入 | EMPTY/PARTIAL/FAILED/TIMEOUT 不混淆 |
| CC12-TEST-029 | 首次 Query 前隐藏 Selector | 浏览器 | 选择区隐藏；首个请求显式提交全部授权 key |
| CC12-TEST-030 | 用户取消全部 Resource | 浏览器+API | no-results scope；不全资源返回结果，提示选择 Resource |
| CC12-TEST-031 | 空选择 Facet refresh 与恢复 | 浏览器+API | Query 改变后 Facet 更新；显式重新选择后才能返回结果 |

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

1. 首次 Query 前 Selector 隐藏；
2. 首次 Query 显式提交全部当前授权 Resource key，返回后只显示 count>0 与执行失败 Resource；
3. 新增 Published Resource 后随新配置版本自动参与 Facet；
4. Resource retired 后消失，无权 Resource 从不显示；
5. 多选/取消 Resource 后结果 scope 与所选 key 一致；
6. Query、Date、State 改变后重新计算 Facet；
7. count=0 隐藏且不显示 `(0)`，正数 count 显示；
8. Partial Success 显示成功 count 和失败状态；
9. 空选择只刷新 Facet、results 为空，并提示选择 Resource；
10. 不同用户/公司看到隔离 count，日志无用户输入泄露。

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
- CC-010 的 Published checksum 和配置版本不可被 Workspace 修改；管理员显式 Apply 的边界由 CC-001 控制。
- Count 计算和刷新必须处于本 CC 的软性能预算内，超预算需记录并保留失败证据。

## 19. Stop Conditions

发现以下任一情况，不得直接实施：

1. 同一 Search API 无法将所选结果 scope 与跨所有授权候选 Resource 的 Facet Count 分离；
2. CC-003 无法证明 count 在 Permission Boundary 之后计算；
3. 空 `resources[]` 仍会导致全资源结果查询，或无法将结果列表保持为空；
4. Published Configuration 无法提供稳定 key/label；
5. 当前 API 无法安全表达多个 Resource；
6. count 在权限过滤/Result Identity 去重前计算，或受 page limit 截断；
7. 存在跨用户或跨公司 count 缓存；
8. unauthorized Resource 会因 count=0、错误或 Descriptor 泄露；
9. Resource Selection、Visible、Authorized、Count、Execution Status 被混为单一状态；
10. 需要 `sudo()`、superuser/admin env 或直接数据库 count。

## 20. Definition of Done

- Descriptor 来自当前 Published Configuration；
- Selector 不再硬编码 Resource；
- 首次搜索前隐藏 Selector，首次请求显式提交全部授权 Resource keys；
- Selector 支持多选并与非空 `resources[]` 完全一致；空数组不表示 all；
- 空选择只运行 Facet Count，不运行/返回业务结果搜索，并提示用户；
- Selector Facet Count 覆盖所有当前授权候选 Resource，结果 scope 只由选择集决定；
- count 精确等于最终授权 Result Identity 数，不受分页影响；
- count=0 隐藏并取消选择；正数显示；failure/timeout 保持可见且 count unknown；
- Query、Selection、Refinement、Published Version 和 Permission Context 改变会正确刷新；
- CC12-TEST-001~031 全部有证据，或有明确批准的延期；
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
| CC12-DEC-003 | 首次 Query 前隐藏 Selector；首次搜索显式选择并发送全部授权 key | 先显示未筛选资源列表 | 用户无需在无 Query 时看到全部类目，同时不依赖空数组全选 |
| CC12-DEC-004 | count 只来自授权结果 | Raw DB Count | 避免权限泄露 |
| CC12-DEC-005 | authorized empty 隐藏；failure/timeout 显示 unknown/error 且保持可见 | 两者都隐藏或显示 0 | 贯彻 SRS FR-PM-007 与 CC-007 failure ≠ empty |
| CC12-DEC-006 | 失败 Resource 不进入成功 count | 失败补 0 | 不把失败伪装为空结果 |
| CC12-DEC-007 | 前端只展示服务端 count | 浏览器自行计算 | 防止权限和条件不一致 |
| CC12-DEC-008 | CC-003 是唯一 Permission Boundary | CC-012 重写权限系统 | 避免安全边界分裂 |
| CC12-DEC-009 | Descriptor 通过独立 API 或 Search `meta` 获取 | 前端硬编码 | 保持前端与 Published Configuration 解耦 |
| CC12-DEC-010 | `resource_counts` 是跨授权候选 Resource 的 self-excluding Facet Count；`counts.by_resource` 仍对应结果 scope | 只计算选中 Resource | 未选但有结果的 Resource 必须可见并可重新选择 |
| CC12-DEC-011 | 空 `resources[]` 表示无结果 scope；可仅刷新 Facet，结果必须为空 | 空数组表示所有 Resource | 禁止空选择触发全资源结果搜索 |
| CC12-DEC-012 | count=0 后隐藏并取消选择；再次有结果时显示为未选中 | 保留隐藏项 selection | 保持 Visible 与 Selected 语义独立 |

用户于 2026-10-08 17:28 批准冻结本版本并进入实施；不得超出本 CC 冻结范围实施。

## 22. Data, Migration and Implementation Structure

- 不新增业务数据模型、业务字段或数据库表；
- 不迁移既有业务数据；
- Published Configuration 继续由 CC-001 生命周期管理；
- 不新增 Search API；复用 `/wd_global_search/api/search`；
- 不改变 `resources` 字段类型或分页/cursor 顶层协议；
- 更新既有 `resource_counts` 语义为授权候选 Facet Map，同时保留 `counts` 的当前结果 scope 语义；
- 空 `resources[]` 的后端结果 scope 为空；可执行受权限约束的 Facet Count-only 计算；
- 若改变 Snapshot schema、Resource key 或 label 存储，必须先提出 CC-001/TDD
  兼容性评审，不在 CC-012 内隐式迁移；
- 最小实施范围：
  - `services/facade.py`：资源 scope 非空校验语义、同时运行 selected Results 与 all-authorized Facets；
  - `services/executor.py`：精确 `search_count`/Result Identity 去重，避免 count 被 fetch limit 覆盖；
  - `services/aggregator.py` 与既有响应组装：区分 `counts.by_resource`、`resource_counts`、失败/timeout；
  - `controllers/main.py`：首次 Selector hidden、服务端授权候选 key 初始化与版本一致性；
  - `static/src/js/preview.js`/CSS：首次隐藏、提交后筛选可见项、多选、零项取消选择、失败保留、空选择提示/显式重选；
  - `tests/`：覆盖 CC12-TEST-001~031；
- 证据位于 `docs/context/history/`，不修改官方 addons；
- Fixture 仅用于隔离测试，不能替代当前用户 ORM 权限验证。
