# CC-005 Global Search Workspace 查询与 Refinement

## 0. 文档治理

| 项 | 内容 |
|---|---|
| Coding Contract | CC-005 |
| 版本 | v0.3 FROZEN |
| 状态 | FROZEN，进入实施 |
| Intent ID | `GS-SEARCH-WORKSPACE-QUERY-REFINEMENT` |
| 上游 SRS | [SRS_global_search](../../requirement/SRS_global_search.md) v1.4 FROZEN |
| 上游 TDD | [TDD_global_search](../../design/TDD_global_search.md) v0.3 FROZEN |
| 实施计划 | [IMPLEMENTATION_PLAN_global_search](../../implementation/IMPLEMENTATION_PLAN_global_search.md) v0.2 FROZEN，Phase 5 |
| 前置 CC | [CC-001](./CC-001_global_search_configuration_foundation.md) v1.0 FROZEN；[CC-002](./CC-002_global_search_service_core.md) v0.2 FROZEN；[CC-003](./CC-003_global_search_permission_boundary.md) v0.2 FROZEN；[CC-004](./CC-004_global_search_preview_container.md) v0.3 FROZEN |
| 模块 | `wd_global_search` |
| 目标 | 将 Preview 容器扩展为当前用户可用的 Search Workspace，支持 Raw Query、结果发现、Query Understanding 和 Refinement |
| 批准冻结 | v0.1：2026-10-05 21:28；v0.2：2026-10-08 11:58；v0.3：2026-10-08 15:35，用户批准全宽度不显示 Preview 并进入实施 |

本 CC 只冻结 Phase 5 Workspace 查询与 Refinement，不实现外部搜索引擎、LLM、向量检索、索引迁移或新的业务权限语义。

### 修订记录

| 版本 | 变更 |
|---|---|
| v0.1 | Workspace 查询、Refinement、结果和 Preview 联动基线 |
| v0.2 FROZEN | 明确 Desktop 独立滚动、Narrow 不显示 Preview，以及 Google 式数字分页和每页数量选择；记录 TDD/CC-004 窄屏 Preview 规则的获批例外 |
| v0.3 FROZEN | 扩展为 Desktop/Narrow 所有宽度均不显示/请求 Preview；通过 configured Form Action 打开记录；记录 SRS/TDD 偏离，不修改 SRS/TDD |

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
| TDD §3.10 | 分页、稳定排序、计数和 cursor | 复用现有 offset/limit 与 cursor，不改变 Search API |
| SRS NFR-005 | 响应式安全降级 | 窄屏以结果列表为主，不覆盖主业务区 |
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
- 结果选择与 configured Odoo Form Action 联动；Workspace 不嵌入/调用 CC-004 Preview；
- Desktop Workspace Results-only 布局及独立滚动边界；
- 所有宽度的 Results-only Workspace；Narrow Workspace 页面自然纵向滚动；
- 结果页码、动态页码窗口和每页数量选择；
- 前端通过 CC-002 Search API，使用 CC-003 授权结果；
- 错误、取消、分页和无结果状态。

### 1.3 超出范围

- 修改 SRS、TDD 或官方 Odoo 代码；
- LLM、向量、外部搜索引擎和 PostgreSQL 索引；
- 新增业务模型、业务 ACL 或角色；
- 先取全量记录再在浏览器或 Python 中模拟权限；
- Preview 写操作、业务数据迁移；
- CC-002 尚未完成的真实 request timeout 和 active cancel 实现；如 Workspace 依赖它，必须先修订 CC-002。
- 修改 SRS、TDD、CC-004 或 CC-002 的既有安全、Search API、分页和 Preview 只读语义；发现上游冲突时须停止并完成契约对齐。

## 2. 行为契约

### 2.1 状态模型

```text
Raw Query
  -> Parsed Conditions
  + Refinement Conditions
  -> Effective Conditions
  -> SearchRequest
  -> Authorized Results
  -> Paginated Results
  -> Selected Result
  -> Configured Odoo Form Action (explicit open only)
```

- Raw Query 是用户原始输入，不能被 Refinement 改写；
- Refinement 可叠加、删除和替换同一维度；
- 资源、日期和状态的初始值分别为全部、不限和全部；
- 修改搜索框时重置 Refinement、结果和选中记录；
- 修改 Refinement 时保留 Raw Query，刷新结果和 Query Understanding；
- 选择记录不重置 Raw Query 或 Refinement，也不加载 Preview；
- 用户显式双击/打开记录时调用 configured Odoo Form Action；
- 切换结果页保留 Raw Query、Refinement 和 Resource Selection；页码改变只请求对应结果页；
- 新 Query、Resource Selection、Refinement 或 Published Configuration version 改变时回到第 1 页并丢弃不兼容的旧页/cursor；
- 改变每页数量时回到第 1 页，不复用旧页的 offset 或 cursor；
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

### 2.3 Workspace 展示与分页

**Desktop Web（现有 `max-width: 700px` 响应式断点之外）：**

- Search Controls 位于 Accessible Records 上方；
- Workspace 不渲染 Preview pane，不建立双栏 Preview 布局；
- Workspace 使用 Odoo Web 可用视口空间，不以固定像素高度作为主要布局约束；
- Accessible Records 建立独立垂直滚动边界；记录数增加不得无限撑高整个页面；
- Records 滚动限制在结果区内，不推动 Search Controls 或整个 Page 无限增长。

**Narrow Workspace（沿用现有 `max-width: 700px` CSS 断点，不新增设备检测）：**

- 不显示 Preview，不创建双栏或 Preview 内部滚动区；
- Accessible Records 为主要工作区，页面按普通纵向流动并可垂直滚动；
- 搜索、Refinement、分页、结果选择和既有打开记录 Action 继续可用；
- 不因隐藏 Preview 改变 Search Request、结果、权限、计数或 Action 语义。

**全宽度 Preview 边界：** Desktop、平板、Narrow 和 375px 均不渲染 Preview pane，也不从 Workspace 调用 `/wd_global_search/api/preview`。CC-004 的只读/权限 API 定义保持原样，不得由 Workspace 消费。

**分页控件：**

- 默认每页 10 条；可选 20、50、100 条；
- 使用 Google 式动态数字分页：First、Previous、当前页附近的页码窗口、Next、Last；页码缺口以省略号表示，页数较少时不显示省略号或重复页码；
- 页码和 Last 的范围依据当前 Query、Refinement、Published Configuration、当前用户权限上下文及 Resource Selection 下的精确结果总数计算；
- 分页总数使用选中 Resource 结果范围的 `counts.all`，不得使用 Facet `resource_counts` 或当前页 `results.length` 推算；CC-012 结果计数契约冻结后须保持字段语义一致；
- 跳转至第 N 页使用既有 Search API 的 `offset = (N - 1) * limit` 与 `limit = pageSize`；不新增 Search API，不把空 `resources[]` 解释为全资源；
- 每页数量和页码变化不得影响精确总计、Resource Facet Count、权限过滤或稳定排序；
- `PARTIAL_SUCCESS` 必须保留失败 Resource 的明确状态；分页总数不得将成功 Resource 的计数伪装为包含失败 Resource 的完整总数；
- `EMPTY` 不显示可导航页码；单页结果不显示无意义的页码导航，但仍可显示每页数量控件。

### 2.4 Workspace 不变量

| ID | 不变量 |
|---|---|
| WORKSPACE-SCROLL-INV-001 | Desktop Web 的 Accessible Records 必须具有独立垂直滚动边界；Records 数量不得无限增加整个 Page 高度。 |
| WORKSPACE-SCROLL-INV-002 | Desktop Web 中，Accessible Records 滚动不得增加整个 Page 高度或推动 Workspace 控件离开其边界。 |
| WORKSPACE-SCROLL-INV-003 | Desktop Web 中，Accessible Records 使用自己的滚动区域；Workspace 不创建 Preview 滚动区域。 |
| WORKSPACE-SCROLL-INV-004 | 所有 Workspace 宽度均不显示 Preview。 |
| WORKSPACE-SCROLL-INV-005 | Workspace 不得为 Preview 引入双栏布局或 Preview 滚动容器。 |
| WORKSPACE-SCROLL-INV-006 | Desktop/PDA Workspace 的布局差异不得改变 Search Result、Permission、Count、Search Request 或 Action 的业务语义。 |
| WORKSPACE-PAGINATION-INV-001 | 每页数量默认 10，可选 20、50、100；分页作用于跨 Resource 合并后的授权结果，而不是为每个 Resource 单独创建页码。 |
| WORKSPACE-PAGINATION-INV-002 | 页码和 Last 页只由当前 Query、Refinement、Resource Selection、配置版本及权限上下文下的精确选中结果总数决定；Facet `resource_counts` 和当前页长度不得用于推算。 |
| WORKSPACE-PAGINATION-INV-003 | 翻页与页大小变化不得改变 Permission Boundary、Result Identity、稳定排序或精确结果总数。 |
| WORKSPACE-PAGINATION-INV-004 | Raw Query、Refinement、Resource Selection 或页大小改变后，当前页重置为第 1 页，失效的结果、offset/cursor 不得复用。 |
| WORKSPACE-PAGINATION-INV-005 | Unauthorized Resource/Record 不得通过结果页、页码、总页数或计数暴露。 |
| WORKSPACE-PAGINATION-INV-006 | Partial failure 不得伪装为完整总数；失败 Resource 状态必须保留，已知成功结果的分页语义必须明确标为部分结果。 |
| WORKSPACE-PREVIEW-INV-001 | 选择搜索结果不得请求或显示 Preview；显式打开记录必须使用 configured Odoo Form Action。 |

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
  "limit": 10,
  "offset": 0,
  "cursor": null
}
```

前端只提交可序列化值。成功结果必须包含 `results`、`resource_counts`、`effective_conditions`、`next_cursor` 和配置版本；失败响应使用 CC-002 错误码，不以空成功结果掩盖失败。
页码直达请求使用既有 `offset`/`limit`；服务端排序、Result Identity 去重、权限过滤和计数仍按 CC-002/TDD 契约执行。若使用 cursor 连续翻页，cursor 失效或页大小改变时必须回到第 1 页重新请求。页数总计依赖所选 Resource 结果范围中的精确 `counts.all`，不得从 `resource_counts` Facet Map 推导。

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
| CC5-CHANGE-006 | Workspace 仍嵌入 Preview | 所有宽度均不显示/请求 Preview；双击/打开结果走 configured Odoo Form Action | CC5-TEST-006、018 |
| CC5-CHANGE-007 | Workspace 未建立 Records 滚动边界，且仍渲染 Preview | Desktop 单栏结果区独立滚动；所有宽度无 Preview；Narrow 使用页面纵向滚动 | CC5-TEST-013~020 |
| CC5-CHANGE-008 | 分页 UI 未提供页码跳转和页大小选择 | 提供动态页码、First/Previous/Next/Last、默认 10 条和 20/50/100 选项 | CC5-TEST-021~028 |

## 5. 测试契约

| ID | 测试内容 | 类型 | 预期结果 | 人工验证 |
|---|---|---|---|---|
| CC5-TEST-001 | Raw Query 输入和提交 | 浏览器+集成 | 搜索请求只携带当前用户上下文和序列化 Query | 是 |
| CC5-TEST-002 | 资源分类、计数、Snapshot | 集成+浏览器 | 结果经过权限过滤，分类和计数一致 | 是 |
| CC5-TEST-003 | Resource/日期/状态 Refinement | 浏览器+集成 | 条件可叠加、删除，结果实时收窄 | 是 |
| CC5-TEST-004 | Query Understanding | 浏览器 | Raw、Parsed、Refinement、Effective Conditions 可见且不混淆 | 是 |
| CC5-TEST-005 | 多用户、多公司、Portal 回归 | ORM+浏览器 | 无权资源、记录、字段和计数不泄露 | 是 |
| CC5-TEST-006 | 结果选择和打开 Action | 浏览器 | 单击选择不请求 Preview；双击/打开进入 configured Odoo Form Action | 是 |
| CC5-TEST-007 | 两条路径等价 | 集成 | 组合 Query 与逐步 Refinement 产生相同条件和记录集 | 否 |
| CC5-TEST-008 | 分页、cursor 和空结果 | 集成+浏览器 | 游标绑定用户/配置，分页和空状态正确 | 是 |
| CC5-TEST-009 | Workspace 写操作边界 | 浏览器+网络监控 | 搜索交互不产生业务 create/write/unlink/copy | 是 |
| CC5-TEST-010 | 桌面和窄屏响应式 | 浏览器 | 所有宽度均为 Results-only Workspace，无 Preview，无控制台错误 | 是 |
| CC5-TEST-011 | 前端状态机 | 浏览器 | 修改 Raw Query 重置 Refinement；修改 Refinement 保持 Raw Query；选择结果保持两者 | 是 |
| CC5-TEST-012 | Query Understanding 不泄露 | 集成+浏览器 | 无权实体、字段和记录不出现在 Query Understanding | 是 |
| CC5-TEST-013 | Desktop Records 独立滚动 | 浏览器 | 10、50、100 条结果下 Records 区域可独立垂直滚动，页面高度不随结果数无限增长 | 是 |
| CC5-TEST-014 | 所有宽度无 Preview | 浏览器 | Desktop、701px、700px、375px 均无 Preview pane、双栏或 Preview API 请求 | 是 |
| CC5-TEST-015 | Desktop 结果滚动边界 | 浏览器 | Records 滚动不改变 Page/Workspace 高度或 Search Controls 位置 | 是 |
| CC5-TEST-016 | Narrow 无 Preview | 浏览器 | 700px 以下和 375px 无 Preview，页面可正常纵向滚动 | 是 |
| CC5-TEST-017 | Narrow 结果列表滚动 | 浏览器 | 页面正常纵向滚动浏览结果，不产生 Preview 嵌套滚动区 | 是 |
| CC5-TEST-018 | Desktop/Narrow 打开记录 | 浏览器 | 单击选择不请求 Preview；双击/打开在所有宽度触发 configured Action | 是 |
| CC5-TEST-019 | Responsive 搜索回归 | 浏览器 | Desktop/Narrow 搜索、Refinement、Resource Selector、权限结果和无 Preview 语义一致 | 是 |
| CC5-TEST-020 | Desktop/Narrow 宽度边界 | 浏览器 | 700px、701px、375px 下布局与既有断点及本契约一致，无溢出/控制台错误 | 是 |
| CC5-TEST-021 | 默认与页大小选项 | 浏览器+集成 | 默认 `limit=10`；可选 20、50、100；请求 limit 与选择一致 | 是 |
| CC5-TEST-022 | 动态数字页码 | 浏览器 | 页码窗口随当前页和总页数更新；省略号、First/Last 不重复且可用 | 是 |
| CC5-TEST-023 | First/Previous/Next/Last 跳转 | 浏览器+集成 | 每个控件请求正确 offset；边界控件禁用或隐藏；Last 到达最后一页 | 是 |
| CC5-TEST-024 | 分页总数语义 | 集成+浏览器 | 总页数基于当前选择下精确 `counts.all`，不使用当前页长度或 Facet Count | 是 |
| CC5-TEST-025 | 结果数量与分页分离 | 集成 | 总数 37、page size 10 时总页数 4；末页 7 条；总数不受页大小/分页影响 | 否 |
| CC5-TEST-026 | Query/Refinement/Resource 切换 | 浏览器+集成 | 条件或 Resource Selection 改变后回第 1 页，旧结果/cursor 不复用 | 是 |
| CC5-TEST-027 | 页大小切换 | 浏览器+集成 | 10/20/50/100 切换后回第 1 页，并按新 limit 请求 | 是 |
| CC5-TEST-028 | EMPTY/单页/部分失败分页 | 集成+浏览器 | EMPTY 无页码；单页无无效导航；部分失败明确失败状态且不伪报完整总数 | 是 |

## 6. 停止条件与完成定义

### 6.1 停止条件

1. 需要改变 SRS/TDD 的权限、条件、Search API 或结果语义；
2. 需要修改官方代码、新增业务 ACL/角色或使用 `sudo()` 读取业务数据；
3. 无法证明计数、Snapshot、分页和 cursor 经过权限过滤；
4. 前端绕过 CC-002 直接访问 ORM 或拼接授权域；
5. 需要实现真实 timeout/active cancel 才能满足 Workspace 行为；
6. 发现跨用户共享授权结果或缓存。
7. `counts.all` 不可用、不精确，或无法区分所选结果总数与 Resource Facet Count；
8. 服务端取数上限无法满足 100 条全局页大小，或导致总页数/Last 页错误；不得通过截断结果伪造成功；

### 6.2 完成定义

1. CC5-CHANGE-001~008 全部实现并有 IHR；
2. CC5-TEST-001~028 执行并有 ATR；
3. 至少一名普通用户、一名多公司用户和一名 Portal 用户完成权限 HVR；
4. Resource、日期、状态 Refinement 与 Query Understanding 浏览器验证通过；
5. 两条路径等价、动态数字分页、页大小切换和 configured Form Action 通过；
6. CC-001~CC-004 既有行为不回归；
7. 无业务写操作、权限旁路、官方代码修改或 Phase 5 之外功能宣称。
8. Workspace 搜索 P95 ≤ 2 秒、Refinement P95 ≤ 1 秒、Query Understanding 渲染 P95 ≤ 500ms；均为软闸门并记录为 TV-01 输入。
9. Desktop Records 独立滚动；所有宽度均不显示/请求 Preview；Narrow/375px 页面正常纵向滚动。
10. 分页总数来自当前用户最终授权的选中 Resource 结果计数；翻页和页大小变化不改变 Count、权限或结果排序语义。
11. 按用户 2026-10-08 批准，CC-005 v0.3 的 Workspace 所有宽度均不显示/请求 Preview；CC-004 只读 Preview API 与 CC-003 权限语义保持不变。

## 7. 既有行为保留

| ID | 行为 |
|---|---|
| CC5-PRESERVE-001 | CC-001 Published 配置、配置管理员隔离和快照语义不变 |
| CC5-PRESERVE-002 | CC-002 Search/Cancel API、cursor、限流和错误协议不被前端覆盖 |
| CC5-PRESERVE-003 | CC-003 当前用户、公司、字段权限和失败关闭继续生效 |
| CC5-PRESERVE-004 | CC-004 Preview API 的只读/权限语义不变；Workspace 不调用 Preview API，也不产生业务写操作 |

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
- 数字分页使用现有 `offset`/`limit`，count 不受分页影响；所选结果 scope 的精确总数按 CC-002/CC-012 已冻结响应契约消费；
- CC-002 的 timeout/active cancel 未完成时，CC-005 不模拟或宣称真实取消。

### 9.2 CC-004 → CC-005

- CC-005 不调用 CC-004 Preview API，也不显示 `PreviewResult`；
- 双击/打开结果通过既有 `/wd_global_search/api/form_url` 获取 configured Odoo Form Action；
- 选择结果和分页保持 Raw Query/Refinement；Search/Action 的权限语义不变；
- CC-004 的 Preview API 权限过滤、失败关闭和无写入口不受 CC-005 影响。

### 9.3 上游契约对齐状态

- SRS v1.4 FR-SW-004 要求 Desktop Preview；全宽度不显示 Preview 与该要求冲突。按用户明确指示，不修改 SRS，**SRS semantic baseline remains unchanged**，FR-SW-004 保留为未满足/偏离项。
- TDD v0.3 §7.4 仍描述 Desktop/窄屏 Preview；按用户明确指示不修改 TDD。CC-004 v0.3 记录该产品例外并明确 Workspace 不嵌入 Preview。
- 实现所有宽度均不显示或请求 Preview；CC-004 只读 API、configured Form Action 和 CC-003 权限边界保持不变。
- 每页 10/20/50/100 是 Workspace 展示规则，不改变 CC-002 Search API；100 条必须与 SRS CFG-011 每 Resource 可配置最大返回记录数协调，服务端不得因 50 条硬上限产生假总页数或不可达 Last 页。
- 当前 CC-012 v1.1 仍为 DRAFT；实现前须确认 `counts.all`（所选 Resource 结果总数）与 `resource_counts`（Facet Count）的分离语义已经冻结并可由 Search Response 精确提供。

## 10. 补充规范

### 10.1 响应式与国际化

- `>700px`：Desktop 单栏 Accessible Records Workspace，记录区具有独立滚动边界，无 Preview；
- `<=700px`：Narrow Result List Workspace，不显示 Preview，不建立双栏或 Preview 滚动区；
- 断点沿用当前 Workspace CSS 的 `max-width:700px`；不新增 PDA/device detection；
- Desktop 可用视口高度按 Odoo Web 内容区布局，不将固定像素高度作为主要约束；flex/grid 子项正确设置 `min-height:0`；
- Narrow 页面正常纵向滚动；所有宽度选择结果均不触发 Preview；既有 configured Action 不变；
- 分页默认每页 10 条，选项为 20、50、100；页码控件动态展示 First、Previous、页码窗口、Next、Last；
- 375px 属于 Narrow Workspace；所有宽度均不显示 Preview；
- Query placeholder、资源、Refinement、Query Understanding、错误消息按当前用户语言；
- 日期、数字和时区按当前用户环境格式化，缺失翻译回退英文。

### 10.2 错误、日志与性能

- `SUCCESS` 正常显示；`PARTIAL_SUCCESS` 显示结果和失败资源；`FAILED` 不显示猜测结果；`TIMEOUT` 显示已完成结果；`RATE_LIMITED`、`CANCELLED` 和 `EMPTY` 显示明确状态；
- 日志只记录 `request_id`、用户上下文标识、条件哈希、资源、状态和延迟，不记录原始 Query、条件值、字段值、SQL 或令牌；
- 性能预算为搜索 P95 ≤2 秒、Refinement P95 ≤1 秒、Query Understanding 渲染 P95 ≤500ms、结果列表渲染 P95 ≤1 秒；Workspace 不发起 Preview 请求。

### 10.3 Fixture、验收和浏览器矩阵

- Fixture 位置：`tests/fixtures/workspace/`，覆盖普通用户、Portal、多公司、可访问/不可访问资源、字段权限和 Refinement 组合；
- 验收必须覆盖输入搜索、资源/日期/状态筛选、删除筛选、Query Understanding、权限隔离、分页/页大小/First-Last 跳转、EMPTY/PARTIAL_SUCCESS、Desktop 独立滚动、Narrow 无 Preview 及 configured Action；
- 首轮浏览器矩阵：Chrome、Firefox、Safari、Edge 最新版；桌面、平板和窄屏均记录结果。

## 11. CC-DEC

| ID | 决策 | 替代方案 | 理由 |
|---|---|---|---|
| CC5-DEC-001 | Raw Query 与 Refinement 分离 | 单一查询状态 | 符合 BR-006 |
| CC5-DEC-002 | 前端只提交可序列化条件 | 前端拼接 domain | 符合 TDD §3.4 并避免权限旁路 |
| CC5-DEC-003 | 权限过滤在聚合和计数前完成 | 聚合后过滤 | 防止计数和 Snapshot 泄露 |
| CC5-DEC-004 | 资源 Tab 只显示有权且有数据的资源 | 显示所有有权资源 | 避免空 Tab，符合 FR-RF-002 |
| CC5-DEC-005 | 不补做 CC-002 未完成的 timeout/active cancel | 前端模拟取消 | 避免宣称未验证行为 |
| CC5-DEC-006 | 所有宽度使用 Results-only Workspace，不显示/请求 Preview | Desktop 嵌入 Preview | 用户明确批准移除 Workspace Preview；显式打开使用 configured Odoo Form Action |
| CC5-DEC-007 | 页码基于所选 Resource 结果范围的精确 `counts.all` | 使用 `resource_counts` 或当前页长度 | 防止 Facet 与结果 scope 混淆及错误 Last 页 |
| CC5-DEC-008 | 使用既有 offset/limit 实现 Google 式数字分页；默认 10，可选 20/50/100 | 无限滚动/仅 Load More | 支持 First、任意页码和 Last，无需新增 Search API |
| CC5-DEC-009 | Responsive 断点沿用现有 700px CSS 机制 | 新增 PDA 设备检测或单独框架 | 最小化实现并保持设备语义与布局模式解耦 |

## 12. 状态机

```text
IDLE -> SEARCHING -> SUCCESS
                 -> PARTIAL_SUCCESS
                 -> EMPTY
                 -> FAILED / TIMEOUT / RATE_LIMITED / CANCELLED
SUCCESS/PARTIAL_SUCCESS -> SEARCHING (add/remove refinement/page)
SUCCESS/PARTIAL_SUCCESS -> IDLE (clear query)
FAILED/TIMEOUT -> SEARCHING (retry)
Selected Result -> Configured Odoo Form Action (explicit open)
```

## 13. 实施结构

```text
controllers/main.py             # Workspace 页面和既有 Search API 接线
services/facade.py              # 消费 CC-002/CC-003
static/src/js/preview.js        # 当前 Workspace Query、Refinement、结果、Preview 和分页状态
static/src/css/preview.css      # 当前 Workspace Desktop/Narrow 布局与滚动边界
services/executor.py            # 仅在既有服务端分页/资源上限阻止精确页面时调整
services/aggregator.py          # 仅消费既有精确授权总数，不在前端重算
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
  pageSize: 10 | 20 | 50 | 100
  currentPage: number
  totalPages: number
  totalResultCount: number
  offset: number
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
goToPage(page): Promise<SearchResponse>
setPageSize(pageSize): Promise<SearchResponse>
cancelRequest(requestId): Promise<CancelResponse>
```

## 14. 评审闸门

- 评审必须确认 Raw Query/Refinement 分离和两条路径等价；
- 评审必须确认权限边界位于结果聚合和计数之前；
- 评审必须确认 Workspace 所有宽度不显示/请求 Preview；显式打开使用 configured Form Action；
- 全宽度不显示 Preview 按用户批准的 CC-005 v0.3 / CC-004 v0.3 执行；不修改 SRS/TDD，且将 FR-SW-004 明确列为未满足项；
- 评审必须确认 `counts.all` 是当前 selected Resource scope 的精确总数，独立于分页且不等于 Facet `resource_counts`；
- 评审必须确认 100 条页面大小与 CFG-011 服务端每 Resource 限制兼容，不会制造不可达页码；
- 评审必须覆盖 Desktop/Narrow 滚动边界、动态数字页码及 First/Last 行为；
- 用户已批准 CC-005 v0.3 冻结并进入实施。
