# CC-013 — Search Result Card & Native Form Navigation

## 0. Governance

| 项 | 内容 |
|---|---|
| Coding Contract | CC-013 |
| 版本 | v0.1 |
| 状态 | FROZEN，进入实施 |
| Intent ID | `GS-SEARCH-RESULT-CARD-NATIVE-FORM` |
| 上游 SRS | [SRS_global_search](../../requirement/SRS_global_search.md) v1.4 FROZEN |
| 上游 TDD | [TDD_global_search](../../design/TDD_global_search.md) v0.3 FROZEN |
| 实施计划 | [IMPLEMENTATION_PLAN_global_search](../../implementation/IMPLEMENTATION_PLAN_global_search.md) v0.2 FROZEN |
| 前置 CC | CC-001~CC-012；TD-001 |
| 模块 | `wd_global_search` |
| 目标 | 为 Global Search 建立 Published Configuration 驱动的搜索结果卡片和 configured Odoo Form Action 导航 |
| 批准冻结 | 2026-10-09 12:12，用户批准冻结 v0.1 并进入实施 |

本 CC 只定义 Result Card 展示与原生 Odoo Action 导航契约。不重定义搜索、
Published Configuration 生命周期、Permission Boundary、错误协议或只读原生表单能力。

## 1. Contract Goal

用户提交搜索后，系统将当前 Published Resource 的 Card 配置应用到 CC-002 返回的
当前用户授权结果；用户显式打开一条结果时，服务器根据稳定 `resource_key` 查找
该 Resource 的 configured Odoo Action，并让 Odoo 以新浏览器 Tab 打开对应原生 Form。

```text
Published Configuration
  └── Business Resource
        ├── Searchable Fields
        ├── Snapshot / Result Card Fields
        └── Configured Form Action (single-model Resource)
                  │
                  ▼
Search Service → CC-003 authorized result + stable resource_key
                  │
                  ▼
          Result Card (configured fields only)
                  │ single click: select
                  │ double-click / Ctrl-or-Cmd-click: open
                  ▼
        Server resolver(resource_key, record_id)
                  │ current-user reauthorization
                  ▼
        Configured Odoo Action / Router target
                  ▼
       New Tab → Native Odoo Form View
```

Workspace 不显示 Preview（见 CC-004/CC-005 v0.3）。CC-013 的 Card 是识别结果的摘要，
不是重新实现 Form，也不替代独立的 Readonly Native Form 契约。

## 2. Background and Acceptance Findings

### 2.1 Existing Contract Support

| 来源 | 已有语义 |
|---|---|
| SRS FR-SW-003 / CFG-003 | Result Snapshot 来自 Business Resource 配置，支持展示字段、顺序、格式和字段权限保护 |
| SRS FR-SW-005 | 双击、Ctrl/Cmd-click 可在新 Tab 打开标准 Odoo Form；Workspace 状态保持 |
| SRS FR-SW-006 / BR-013 | 结果摘要和 Result Identity 具有稳定业务语义 |
| SRS FR-PM-001~008 | 当前用户、公司、记录和字段权限贯穿搜索结果与打开记录 |
| SRS CON-008 / CON-011 | 安全相关异常失败关闭；无权限字段不得参与搜索或输出 |
| TDD §4.1 / §4.5 | Business Resource 与 Snapshot 字段属于 Published Configuration；Snapshot 与 Form View 分离 |
| TDD §6 | 当前用户、Record Rule、公司、模型/字段权限是唯一权限边界 |
| TDD §3.14 | Label、日期、时间、数字按当前用户服务端语言/时区格式化 |
| CC-002 | Search API 返回授权结果、`_resource`、`_model`、`_record_id` 和分页状态 |
| CC-003 | Search/Preview 的模型、记录、字段读取服从当前用户权限和失败关闭 |
| CC-004/CC-005 v0.3 | Workspace 不显示/调用 Preview；结果通过 configured Form Action 打开 |
| CC-012 v1.1 | `resource_key` 来自 Published Descriptor；Resource selection / result counts 不由前端推导 |

### 2.2 Current Implementation Findings

| 发现 | 当前证据 | 影响 |
|---|---|---|
| Card fields | `BusinessResource.snapshot_field_ids` 已发布 `field_name`、`label`、`format_type`、`allow_empty`；没有显式 `sequence` 或 `visible` | 配置字段顺序/可见性不能完整满足本 CC |
| Label localization | Snapshot Field label 是 translated configuration field；需确认 Published Snapshot 按当前用户 `lang` 提供对应翻译/英文回退 | Card label 不得由浏览器语言或硬编码文本决定 |
| Card payload | `executor.py` 读取配置的 Searchable Fields；Workspace `renderResults` 当前主要显示记录名称与 Resource label | Card 未按 Snapshot/Card Field 配置渲染多个字段 |
| Action 配置 | 当前 `controllers/main.py::form_url` 维护 model-name → 静态 XML Action 的映射；Published Resource 没有 Action 字段 | 新增 Resource 或更换业务 Action 需改前端/Controller registry |
| Navigation request | 当前 Workspace 发送 `model + record_id`；本 CC 要求只发送稳定 `resource_key + record_id` | 客户端仍决定技术模型，未达到 server-defined Resource/Action resolution |
| Native Form URL | 当前 Controller 拼接 `/web#id=...&action=...&model=...` | 未以配置 Action/当前 Odoo 18 Router 作为唯一导航来源 |
| Open-time authorization | 当前 `form_url` 调用 `record.check_access_rule("read")`；未显式校验 action/resource 配置与模型 read ACL 的完整组合 | Search 时的授权不能代替打开时重新授权 |
| Resource model cardinality | Business Resource 可映射多个 Technical Model；一个 `ir.actions.act_window.res_model` 不能同时匹配多个模型 | 本 v0.1 将 Action 导航限定为单模型 Resource；复合 Resource 不得错误路由 |

上述差异为 CC-013 范围内的验收发现。本 CC 不修改 SRS/TDD 或既有 CC；如实施发现需要改变其冻结语义，触发 Stop Condition。

## 3. Scope

### 3.1 In Scope

- 复用现有 Published Snapshot / `SnapshotField` 配置作为 Result Card 字段来源，不新建平行 Card Field Registry；
- 将 Card 字段配置明确为 Field、Label、Sequence、Visible、Format；
- Search API 使用现有路由和结果 identity；Result Card 只展示 Published 配置指定且经 CC-003 授权的字段；
- 每个可导航的 single-model Business Resource 配置一个 `ir.actions.act_window` Form Action；
- Publish 时验证 Card Field、Action、Resource Model、Form View 配置；
- 复用既有 `/wd_global_search/api/form_url` 导航入口，将调用参数改为 `resource_key + record_id`；
- 前端只负责选择结果/触发打开，不提交任意 `model`、`action_id`、XML ID、域或 context；
- 单击选择、双击打开、Ctrl/Cmd-click 打开新 Tab；
- 打开前按当前用户重新验证 Resource、模型 ACL、记录 Record Rule、Action 可用性；
- Action 不可用、记录删除/失权和无效请求沿用既有安全错误协议；
- Card 字段顺序、格式、可见性、翻译和权限过滤测试。

### 3.2 Composite Resource Decision

CC-013 v0.1 的 native Form navigation 仅适用于**恰好映射一个 Technical Model**
的 Business Resource。Composite Resource 可继续由 CC-001~CC-012 搜索和展示其既有
Snapshot/Card 内容，但本 CC 不为其提供 Native Form Action；不得依据结果中的
`_model` 在多个 Action 中猜测或选择。Composite Action 支持需单独契约评审。

该限制是 CC-013 v0.1 的冻结产品边界；不得在实施中通过 fallback、前端 model 路由或
任选一个 mapping 绕过。

### 3.3 Out of Scope

- Readonly Native Form 能力、Form 内编辑/保存/删除阻断；
- Search Service、资源多选、动态 Resource Selector、count/Facet 语义；
- CC-003 权限系统和 CC-007 错误协议的重设计；
- 新 Search API、新外部搜索/索引/LLM/向量技术；
- 修改 SRS、TDD、CC-001~CC-012 或官方 Odoo 核心/addons；
- 为 Composite Resource 设计多个 Action、按模型猜测导航或创建新的 Card Field 模型。

## 4. Result Card Configuration

### 4.1 Reuse Existing Snapshot Fields

Result Card fields 是 Business Resource 当前 Published Snapshot 的展示配置，不是
Searchable Field，也不是权限授权。v0.1 复用现有 `wd.gs.snapshot.field`，不得新建
平行 `result.card.field` 模型。

| 配置项 | 契约 |
|---|---|
| Field (`field_name`) | 必须存在于对应 Resource Technical Model；使用稳定技术字段名 |
| Label | 用户可见标签，使用服务端 Published/i18n 值；不可由结果值覆盖 |
| Sequence | 正整数；Card 按 Sequence 升序显示 |
| Visible | 布尔值；false 字段不进入 Card payload 或 DOM |
| Format (`format_type`) | 复用已支持的 `text`、`date`、`datetime`、`number`；其它格式不属于 v0.1 |
| Allow Empty (`allow_empty`) | 复用现有策略；false 时空值不显示为误导性数据 |

- 同一 Resource 内 Sequence 必须唯一；重复值在 Publish 时拒绝，确保顺序确定。
- Label 使用当前 Published/i18n 的服务端翻译；不同用户按 `request.env.user.lang`
  显示对应 Label，缺失翻译回退英文；浏览器语言不覆盖服务端用户语言。
- Label 是受信配置文本但仍以纯文本渲染；不得被业务字段值覆盖。
- 每个可发布的 Result Card 至少配置一个 Visible 字段。
- Card 仅包含 Visible、格式受支持、属于 Resource Model 的字段；不把 Searchable Fields
  自动复制成 Card fields。
- 现有配置中缺少 Sequence/Visible 时，CC-013 实施须在现有 Snapshot Field 配置上
  作增量扩展；不得创建第二套字段模型或原地篡改既有 Published Snapshot。
- 旧 Published Snapshot 不因代码升级而隐式重写；缺少 v0.1 必需配置时，须通过正常
  Draft → Publish 建立兼容的新版本，否则该 Resource Card/Action 不得假装已配置成功。

### 4.2 Card Payload and Rendering

沿用现有 Search API 和 result item，在每项中返回已授权的 Snapshot/Card 内容，例如：

```json
{
  "_resource": "sale_order",
  "_model": "sale.order",
  "_record_id": 5052,
  "snapshot": {
    "fields": [
      {"field_name": "name", "label": "Order", "format": "text", "value": "SO012"},
      {"field_name": "date_order", "label": "Order Date", "format": "datetime", "value": "..."},
      {"field_name": "amount_total", "label": "Total", "format": "number", "value": "..."}
    ]
  }
}
```

- `_resource` 必须是稳定的 Published `resource_key`；Result Identity 仍服从 CC-002。
- `snapshot.fields` 按 Sequence 排序，只含 Visible 且当前用户可读的值。
- Card 以纯文本展示 Label/Value；必须 HTML-escape，不允许配置或业务值注入 HTML。
- 日期、时间、数字使用当前 Odoo 用户语言/时区格式；不得客户端猜测时区。
- Card 不得把 `_model` 或模型名显示为业务 Resource，也不得从 `_model` 推导 Resource key。
- Card 不显示未配置字段、不可读字段、raw domain、Record Rule、Action XML ID 或内部配置 ID。
- 若当前用户无法读取某个 Card 字段，仅省略该字段；不得因管理员配置而绕过 CC-003。
- 若当前用户无任何可显示字段，Card 仅可显示安全的 Resource label/通用提示，不得输出字段值或猜测记录身份。

### 4.3 Card UI and Responsive Behavior

- 每条搜索结果以独立 Card 展示；Card 使用 Published `resource_key` 和 Resource Label，
  不使用 Technical Model 作为业务标题。
- 字段按 Sequence 升序显示：
  - 第一个 Visible 且授权的字段作为主标识；
  - 第二个 Visible 且授权的字段作为副标识（若存在）；
  - 其余字段按 `Label: Value` 顺序显示。
- 空值若 `allow_empty=true` 显示 `—`；`allow_empty=false` 时省略字段。
- Card 的交互样式应明确区分 hover、keyboard focus、selected 和 disabled/loading 状态；
  结果失败状态使用 CC-007 安全提示，不在 Card 中显示原始异常。
- 不新增设备检测；Card 内容密度只按 viewport CSS 响应式处理，Workspace 模式仍严格沿用
  CC-005 v0.3 的 `max-width:700px` 断点：
  - `>=1024px`：显示所有授权的 Visible Card fields；
  - `768px~1023px`：显示所有授权字段，允许换行，不得改变字段顺序；
  - `<768px`：默认显示前两个授权字段，其余字段收在显式“更多”展开区；375px 同样适用；
  - 所有宽度均不显示 Preview，不改变结果/权限/Action 语义。
- “更多”展开区仅改变展示，不触发额外数据读取，不重新搜索，不成为绕过 Visible、
  字段权限或 `allow_empty` 的途径。

### 4.4 Performance and Logging Guardrails

以下是 CC-013 的软性能目标，作为 TV-01 输入，不覆盖 SRS NFR-001；超预算须记录并
分析，不得通过跳过权限、减字段校验或缓存跨用户数据来达成：

| 项 | 目标 |
|---|---|
| 当前页至多 100 张 Card 的浏览器渲染 | P95 ≤ 100 ms |
| 本页 Card Field 序列化 | P95 ≤ 200 ms |
| Card Field ACL/权限过滤处理 | P95 ≤ 100 ms |
| Search response 中 Card 摘要可用时间 | P95 ≤ 500 ms 的增量预算；端到端仍服从 SRS 搜索预算 |

日志复用 CC-008 的 Odoo structured logging 与字段白名单；允许必要的 `request_id`、
`config_version`、`resource`、`latency_ms`、`status`、`error_code`、`retryable`。
不得为 CC-013 私自扩展日志字段白名单；尤其不得记录 `record_id`、Card 字段值、
原始 Action XML ID、domain/context、Record Rule、token 或用户输入。

## 5. Field Security Boundary

强制数据路径：

```text
Published Snapshot Field
  -> Field exists/type/Visible validation
  -> Current user model read ACL
  -> CC-003 current user field permission
  -> ORM read under current user / Record Rule / company context
  -> allowed formatted value
  -> Result Card
```

- CC-003 是唯一 Field/Record Permission Boundary。
- Card Field Configuration 表示“管理员希望展示什么”，不代表当前用户有权读取。
- Card 字段必须通过与其他 Workspace Read 一致的 `PermissionBoundary` / 当前用户 ORM
  权限检查；不得只依赖 Searchable Field ACL，也不得读取 `sudo()` 数据。
- 打开记录前再次检查 Model Read ACL、Record Rule 和 Action 可用性；搜索时授权不产生
  可长期复用的导航授权。
- 权限拒绝、字段不可读或记录不存在时，不区分“记录不存在”和“用户无权访问”；
  使用 CC-004/CC-007 已有安全错误语义。
- 不将无权字段、记录/Action 是否存在的细节写入客户端错误、Card、日志或 Selector。

## 6. Configured Form Action

- 每个支持 Native Form navigation 的 single-model Business Resource 配置一个
  `ir.actions.act_window` Form Action。
- Action 作为现有 Business Resource 的 Published Configuration 属性保存；建议使用
  现有配置模型上的 `Many2one(ir.actions.act_window)` 并将 Action 的稳定服务端引用
  纳入 Published Snapshot。不得创建新的通用 Action Registry。
- 前端不得接收或维护 Action XML ID、任意 `action_id`、`res_model` 或业务 context。
- Action 保留业务模块配置的 View、View mode、Context 和默认行为；Global Search 不
  复制 Form View、不重新实现业务 Form。
- 用户显式打开结果时，前端只提交：

```json
{"resource_key": "sale_order", "record_id": 5052}
```

- 服务端按当前 Published Snapshot 的 `resource_key` 查找 Resource、唯一 Model 和
  configured Action；不得使用客户端传入的 `model` 或 `action`.
- Navigation resolver 复用现有 `/wd_global_search/api/form_url` 路由；不得创建新的
  Search API。其 v0.1 request contract 仅接受 `resource_key + record_id`。
- 成功响应包含由服务端基于 configured Action/Odoo 18 Router 生成的同源
  `navigation_url`；前端不得自己拼接 `/web#id=...` 或 `/odoo/action-...`。
- Action 必须为可用的 `ir.actions.act_window`；它的 `res_model` 必须匹配 Resource
  唯一的 Technical Model；`view_mode` 必须提供 Form View。
- Action 有 `groups_id` 等 group 限制时，服务端必须按当前用户检查 Action 可用性；用户
  不满足限制时不得打开，也不得在错误中泄露 Action 或记录存在性。
- 配置 Action 不得扩大业务记录权限；Action 可用不等价于记录有读权限，记录 ACL、
  Record Rule 和公司边界仍须独立检查。
- Composite Resource 不可配置一个模糊的单 Action；Publish 必须拒绝把单模型 Action
  配给多模型 Resource。

## 7. Why a Configured Odoo Action Is Required

- Odoo Action 决定 Form View、View mode、Context、默认入口和业务模块特定行为；
- `res_model + record_id` 直接打开 Form 会绕过这些业务入口语义；
- Global Search 的职责是找到已授权业务对象；
- Odoo Action 的职责是决定用户如何进入业务对象；
- 因此 Action 必须来自 Published Resource Configuration，由服务端解析，不由前端猜测。

## 8. Card Selection and Open Interaction

| 操作 | 行为 |
|---|---|
| Single click | 只选择/标记 Card；不导航、不写业务数据、不加载 Preview |
| Double click | 打开该 Resource 的 configured Odoo Action |
| Ctrl/Cmd-click | 按 SRS FR-SW-005 在新 Tab 打开 configured Odoo Action |
| Tab / Shift+Tab | 按文档顺序在 Card 间移动焦点；Card 必须有清晰 focus indicator |
| Space on focused Card | 选择/取消选择 Card，不导航 |
| Enter on focused Card | 显式打开 configured Action；不得触发写操作 |
| Ctrl/Cmd+Enter | 在新 Tab 显式打开 configured Action |
| Escape | 清除当前 Card selection；不得清除 Query/Refinement/Resource Selection |

双击/快捷键链路：

```text
Selected Card
  -> {resource_key, record_id}
  -> server resolves current Published Resource + Action
  -> current-user ACL + record-rule recheck
  -> Odoo-native navigation target
  -> new browser Tab
```

- 前端不得提交或重写 Action/model/domain/context。
- Space 只选择，Enter 只打开；键盘行为不得依赖双击模拟或触发两次导航。
- 为避免异步请求后 `window.open` 被浏览器 Popup Blocker 阻止，用户手势处理器必须同步
  打开待定新 Tab，再将服务器返回的同源 Odoo navigation target 赋给该 Tab；请求失败时
  关闭待定 Tab，并在 Workspace 显示 CC-007 安全错误。
- Card selection、Search Query、Refinement、Resource Selector 和分页状态不因 Open
  Action 被清除。
- CC-013 不配置 `readonly` 行为；原生 Form 的只读能力由单独 Readonly Native Form
  契约定义。

## 9. New Browser Tab

- 当前 Tab 始终保留 Search Workspace。
- Double-click / Ctrl-or-Cmd-click 在新 Tab 进入 Odoo Router 生成的 Native Form。
- 新 Tab 使用原用户 Odoo Session；不得建立无权限的代理用户或共享管理员 Session。
- Navigation URL 必须是同源 Odoo Router target；外部 URL、`javascript:` URL 或客户端任意
  URL 一律拒绝。
- Odoo 原生 Action 保留已配置 Context、View 和模块行为。

## 10. Readonly Native Form Boundary

- CC-013 定义“Card 展示哪些字段”和“用哪个 Odoo Action/记录导航”。
- CC-013 不定义 Form View 的只读、编辑、保存、删除、复制、按钮、Chatter、附件或活动权限。
- CC-013 不得在 Card/Navigation 中声称 Native Form 已只读。
- Readonly Native Form 必须由独立合同定义并验证；CC-013 仅要求 Native Form 继续由
  Odoo 当前用户权限和 Action 处理。

## 11. Invariants

| ID | 不变量 |
|---|---|
| CC13-INV-001 | Result Card 不得硬编码业务字段；字段来源只能是当前 Published Snapshot |
| CC13-INV-002 | Card 字段必须服从当前用户模型/字段/记录权限；配置不授予权限 |
| CC13-INV-003 | Result Card 使用稳定 `resource_key`，不得从 model/label 推导 |
| CC13-INV-004 | Card 字段按 Published Sequence 升序展示，Visible=false 字段不得出现在 payload/DOM |
| CC13-INV-005 | Native Form 打开必须使用该 Resource 配置的 `ir.actions.act_window` |
| CC13-INV-006 | 客户端只提交 `resource_key + record_id`，不得指定任意 model/action/context |
| CC13-INV-007 | Publish 时 Action `res_model` 必须匹配 Resource 唯一 Model |
| CC13-INV-008 | 打开记录前必须按当前用户重新验证 Model Read ACL、Record Rule、记录存在性和 Action 可用性 |
| CC13-INV-009 | Card 配置/Action 配置必须来自当前 Published Version；Draft/旧版本不得混用 |
| CC13-INV-010 | Double-click/keyboard Open 不得清空原 Workspace 或改变搜索条件 |
| CC13-INV-011 | CC-013 不得将 Native Form 描述为只读；Readonly Native Form 属于独立契约 |
| CC13-INV-012 | Native Action 导航只支持 single-model Resource；Composite Resource 不得猜测 Action |
| CC13-INV-013 | 权限、删除、Action 或配置错误不得泄露记录/Action 存在性或无权字段值 |
| CC13-INV-014 | Card 不得显示 Action XML ID、内部配置 ID 或 Record Rule 内容 |

## 12. Publish-time Configuration Validation

Publish MUST 验证 Card 与 Action 配置：

### 12.1 Card Fields

1. Resource Model 存在且通过 CC-001 校验；
2. `field_name` 存在于 Resource Model；Composite Resource 字段须对其每个 Model mapping
   有明确适用性，否则拒绝该 Card 配置；
3. Label 非空且可由服务端语言规则解析；
4. Sequence 是正整数且在同一 Resource 内唯一；
5. Visible 是布尔值；至少有一个 Visible Card field；
6. Format 属于 v0.1 支持集合 `text/date/datetime/number`，并与字段类型兼容；
7. Visible=false 的字段不进入 Published Card descriptor/value 输出；
8. `allow_empty` 保持现有 Snapshot Field 语义。

### 12.2 Form Action

1. Action 存在且类型为 `ir.actions.act_window`；
2. Resource 恰好映射一个 Technical Model；
3. Action `res_model` 与该唯一 Model 完全匹配；
4. `view_mode` 包含 `form`，所引用的默认/指定 Form View 存在；
5. Action 是稳定服务端配置引用并进入当前 Published Version；
6. Action 的 group restrictions 必须保留在 Published Action，不得通过 Search/导航配置扩大可用用户范围；
7. Publish 校验 group restriction 的元数据可读且合法；是否允许当前用户执行 Action
   在打开时按该用户权限重新验证，不以发布者权限代替；
8. Action 无法加载、Model 不匹配、Resource 为 Composite 或 Form View 不可用时，
   Publish 返回配置错误，不转为运行时猜测。

配置失败 MUST 阻止 Published Version 生效；不得在运行时 fallback 到硬编码 model/action map。

## 13. Test Matrix

| ID | 测试 | 类型 | 预期 |
|---|---|---|---|
| CC13-TEST-001 | Card 从 Published Configuration 生成 | Odoo+API | 不依赖硬编码字段 registry |
| CC13-TEST-002 | 多个 Card fields 正确显示 | API+浏览器 | Label/Value 对应配置 |
| CC13-TEST-003 | Field Sequence 排序 | Odoo+浏览器 | Sequence 升序且稳定 |
| CC13-TEST-004 | 修改并重新 Publish Card 配置 | Odoo+浏览器 | 新 Published Version 自动反映新字段/标签/顺序 |
| CC13-TEST-005 | Unauthorized Field 不显示 | 多用户 ORM+浏览器 | 该字段不在 payload、Card DOM、错误或日志 |
| CC13-TEST-006 | Resource key 稳定 | API | `_resource` 与 Descriptor 的 `resource_key` 相同 |
| CC13-TEST-007 | Configured Action 被解析 | API+浏览器 | 服务器解析 Resource Action，不使用硬编码 model map |
| CC13-TEST-008 | Action Model 不匹配 | Odoo Publish | Publish 拒绝，不生成 Published Version |
| CC13-TEST-009 | Double click 打开当前 record | 浏览器+Action | Native Form record id 与 Card identity 一致 |
| CC13-TEST-010 | New Tab | 浏览器 | Workspace 保留；Native Form 在新 Tab |
| CC13-TEST-011 | Client cannot specify arbitrary Action/model | API security | 额外 `model/action_id/xmlid` 被拒绝/忽略；不得影响 resolver |
| CC13-TEST-012 | Open-time permission recheck | 多用户 ORM+API | 搜索后撤权时不打开记录，不泄露存在性 |
| CC13-TEST-013 | Deleted record navigation | ORM+API+浏览器 | CC-007 safe status；不泄露原字段 |
| CC13-TEST-014 | Pagination / Resource change Card regression | 浏览器 | 各页 Card 均按同一 Published Card config |
| CC13-TEST-015 | CC-003 Field/Record Permission regression | 多用户集成 | 只显示当前授权 Snapshot fields |
| CC13-TEST-016 | CC-012 Selector regression | 浏览器+API | Resource Card key/count/selection 一致 |
| CC13-TEST-017 | CC-007 Error Protocol regression | 故障注入 | EMPTY/PARTIAL/FAILED/TIMEOUT 不混淆 |
| CC13-TEST-018 | Composite Resource navigation guard | Odoo Publish+API | 单 Action 不得映射到多模型；不产生 guessed navigation |
| CC13-TEST-019 | Card keyboard operations | 浏览器 | Tab/Shift+Tab focus、Space select、Enter open、Ctrl/Cmd+Enter new Tab、Escape clear selection 均符合契约 |
| CC13-TEST-020 | Action group restriction | 多用户集成+浏览器 | 不满足 Action group restriction 的用户不可打开；不泄露 Action/Record 存在性 |
| CC13-TEST-021 | Card Label localization | 多语言浏览器 | Label 使用服务端用户语言；缺失翻译回退英文；浏览器语言不覆盖 Odoo 用户语言 |
| CC13-TEST-022 | Card payload/DOM internal-data exclusion | API+浏览器+日志断言 | 不含 Action XML ID、内部配置 ID、Record Rule、不可见字段或无权值 |
| CC13-TEST-023 | Card responsive field disclosure | 浏览器 | >=1024 全部字段；768–1023 压缩且顺序不变；<768 默认主/副字段，其余显式展开 |

Required tests execute against single-model Action-enabled Resources; Composite Resource test
validates the explicit v0.1 navigation limit. Action group tests must use distinct current-user
group memberships and must not substitute a superuser environment for the tested user.

## 14. Regression Requirements

- CC-002: `resources[]`, pagination/cursor, counts and error envelope unchanged;
- CC-003: current user/company/field/record/relation permissions and fail-closed behavior unchanged;
- CC-004/CC-005 v0.3: Results-only Workspace; no Preview API/pane; configured Action still opens
  the native Form in a new Tab;
- CC-007: failed Resource, `PARTIAL_SUCCESS`, `EMPTY` and safe errors remain distinct;
- CC-008: logging whitelist and audit semantics unchanged;
- CC-009: label/number/date formatting uses current server-provided language/timezone;
- CC-010: Workspace cannot change Published checksum/version; admin-applied snapshot changes remain governed by CC-001;
- CC-012: stable Resource key, multi-select, Facet Count and empty scope semantics unchanged.

## 15. Stop Conditions

Stop implementation if any condition holds:

1. Card fields cannot be tied to a Published Resource Snapshot;
2. Card value serialization cannot prove CC-003 Field/Record permission filtering;
3. Action mapping depends on client-supplied model/action/XML ID/context;
4. Action `res_model` cannot be matched to one Resource Model at Publish;
5. Resource composite Action is required without a separately approved per-model Action contract;
6. Open-time Model ACL/Record Rule/record existence recheck cannot be enforced;
7. Odoo Router/native Action cannot be used without inventing an incompatible route;
8. Implementing the contract requires changing SRS/TDD/CC-001~CC-012 semantics or Published
   lifecycle without a separate approved contract revision;
9. Readonly Native Form controls must be implemented in this CC;
10. Card payload/DOM would expose any unauthorized field, Record Rule content, Action XML ID or
    internal configuration identifier;
11. Implementation would require `sudo()`/superuser for business records, direct SQL, official
    Odoo code changes, or external search infrastructure.

## 16. Definition of Done

- Card fields are sourced from the current Published Snapshot; no frontend field registry;
- Card fields are ordered/formatted from config and filtered under CC-003;
- Action is server-resolved by `resource_key + record_id`; client cannot choose model/action;
- Publish validation rejects invalid fields, unsupported formats, model mismatch and invalid Action;
- Explicit open uses configured Odoo Action/Router in a new Tab;
- Open-time reauthorization and safe error behavior are verified;
- Composite Resources cannot receive guessed single-model Actions;
- CC13-TEST-001~023 have evidence or explicitly approved deferral;
- CC-002~CC-012 regressions pass;
- IHR/ATR/HVR exist; HVR records human execution, not agent inference;
- No changes to SRS/TDD/official addons; no prohibited permission bypass.

## 17. Decisions

| ID | Decision | Alternative | Rationale |
|---|---|---|---|
| CC13-DEC-001 | Reuse existing Published Snapshot Fields as Card fields | New Card field model | Avoid duplicate config/registry; preserve CC-001 lifecycle |
| CC13-DEC-002 | Card output is only configured, Visible and authorized Snapshot values | Render all Searchable Fields | Separate searchability from presentation; minimize data exposure |
| CC13-DEC-003 | Use the configured Odoo `ir.actions.act_window` | Hardcoded model-to-action map | Preserve business module View/Context behavior |
| CC13-DEC-004 | Frontend sends `resource_key + record_id` only | Send model/action from Card | Server owns Resource/Action resolution |
| CC13-DEC-005 | Double-click and Ctrl/Cmd-click open a new Tab | Replace current Workspace | Keep Search state and follow FR-SW-005 |
| CC13-DEC-006 | Readonly Native Form remains a separate contract | Make Card navigation impose read-only | Avoid mixing navigation and form editing security |
| CC13-DEC-007 | Validate Card/Action config at Publish | Defer validation to click time | Prevent invalid Published navigation configuration |
| CC13-DEC-008 | Action lookup uses current Published Resource config | Client-supplied Action XML ID | Enforce versioned server configuration |
| CC13-DEC-009 | Recheck permissions at open time | Reuse search-time authorization | Permission may change between search and navigation |
| CC13-DEC-010 | Native Action navigation v0.1 is single-model only; Composite Resource navigation is out of scope | Guess one Action from result model or add per-model Actions | User-approved scope limit; avoids ambiguous Action routing |
| CC13-DEC-011 | Card Labels use server-side Published/i18n resolution with English fallback | Browser-side translation or client language override | Keep labels consistent with CC-009 server language source |

用户于 2026-10-09 12:12 批准冻结 CC-013 v0.1 并进入实施。

## 18. Implementation Structure

Reuse the existing module layout; no new framework or external infrastructure:

```text
models/configuration.py           # Extend existing SnapshotField/BusinessResource config
services/card.py                  # Serialize configured, authorized Card Snapshot fields
services/action.py                # Resolve and validate Published Action under current user
services/navigation.py            # Produce Odoo-native navigation target
controllers/main.py               # Reuse existing Search and form_url routes
static/src/js/preview.js          # Results-only Card render and explicit open interaction
static/src/css/preview.css        # Card fields/layout
tests/test_card.py
tests/test_navigation.py
```

The service split above is a suggested organization, not a new architecture requirement; small,
cohesive helpers in existing services are acceptable.

## 19. Appendix

### 19.1 Traceability

| CC-013 | Upstream |
|---|---|
| Result Card Snapshot fields | SRS FR-SW-003, FR-SW-006, CFG-003; TDD §4.5 |
| Open full record | SRS FR-SW-005; TDD §10.2 |
| Result identity/resource key | SRS BR-011/BR-013; CC-002; CC-012 |
| Field/record security | SRS FR-PM-001~008; TDD §6; CC-003 |
| Configured Action | SRS FR-SW-005; CC-005 v0.3; this CC adds Published Action binding |
| Error behavior | CC-007; CC-004 safe permission/deleted semantics |
| Secure failure/field exclusion | SRS CON-008/CON-011; TDD §6.5; CC-003 |
| Label/format locale | TDD §3.14; CC-009 |

### 19.2 Interface Contract

Workspace → existing resolver:

```text
GET /wd_global_search/api/form_url?resource_key=<stable key>&record_id=<integer>
```

The server resolves current Published Resource → single model → configured Action, rechecks
current-user access, and returns a same-origin Odoo navigation target. The client must not send
`model`, `action_id`, XML ID, domain or context.

### 19.3 Terms

| Term | Meaning |
|---|---|
| Result Card | Search Workspace summary for one authorized Result Identity |
| Card Field | A Visible field from the Published Snapshot rendered on a Result Card |
| Configured Action | Published `ir.actions.act_window` selected for a Business Resource |
| Native Form | Odoo standard Form View opened through that Action |
| Readonly Native Form | Separate future contract; not implied by CC-013 |

### 19.4 Card Acceptance Scenarios

1. Search a Customer and confirm configured fields (for example name/ref/email/phone) and
   configured order/labels are rendered; only values actually configured and authorized appear.
2. Search a Sales Order and confirm its Published Card fields and their formats.
3. Change Card configuration, Publish a new version and confirm subsequent searches use that
   version without stale Card configuration.
4. Double-click a Card and confirm a new Tab opens the matching native Form through the
   configured Action while the Search Workspace remains intact.
5. Revoke or lack access to a Card field/record and confirm the value/record is not exposed.
6. Delete a record or make its Action unavailable before opening; confirm a safe CC-007 error.
7. Verify Card labels follow the Odoo user's language and fall back to English when untranslated.
8. Verify Desktop, Tablet and Narrow Card content density without changing the CC-005 workspace
   700px layout mode or showing a Preview.

### 19.5 Human Verification Scenarios

HVR must record an identifiable human verifier, browser/device, code baseline, actual observation
and result for each executed scenario:

1. Inspect configured Customer and Sales Order Card fields/order/format.
2. Double-click a Card; verify new Tab opens the configured Native Form.
3. Verify Ctrl/Cmd-click and keyboard Enter open behavior; Space selects; Escape clears selection.
4. Verify Search Workspace and query/refinement/resource selection remain intact after opening.
5. Verify a user with partial field access sees only authorized Card values.
6. Verify an Action group restriction prevents opening for an ineligible user.
7. Verify no browser console error and no business write RPC is triggered by Card interaction.
8. Confirm Native Form read-only behavior only if a separate Readonly Native Form contract is
   in force; do not claim it from CC-013.

### 19.6 Performance Guardrail

Targets in §4.4 are soft gates. ATR records sample count, environment and P95; a miss triggers
investigation and evidence, not a permission shortcut. Overall search timing remains governed by
SRS NFR-001 and CC-002.

### 19.7 Fixture Convention

- Fixture root: `mymodules/wd_global_search/tests/fixtures/card/`.
- Cover single-model Customer/Sales Order/Purchase Order Resources, field formats, Visible/order,
  translated/untranslated Labels, authorized/unauthorized fields, allowed/disallowed Action groups,
  missing/deleted records and invalid/mismatched Actions.
- Use Odoo ORM and the real current-user access environment; fixtures must not use `sudo()` for
  business records or substitute a superuser for permission assertions.
- Give each test case a unique marker; tear down only records created by that test through ORM,
  then assert its fixture marker has no remaining records. Do not delete shared acceptance data.

### 19.8 Browser Compatibility Matrix

| Browser | Desktop | Tablet | Narrow |
|---|---|---|---|
| Chrome latest | Required | Required | Required |
| Firefox latest | Required | Required | Required |
| Safari latest | Required | Required | Required |
| Edge latest | Required | Required | Required |

Record exact browser version, viewport and result. The Card content breakpoint does not change
CC-005 v0.3 Workspace mode: `>700px` Desktop Results-only; `<=700px` Narrow Results-only.

### 19.9 Review Change Log

| Revision | Change |
|---|---|
| v0.1 initial draft | Initial Result Card, configured Action, security and navigation contract |
| v0.1 review update | Added SRS FR-PM/CON traceability, server Label i18n, Action group checks, keyboard controls, internal-data invariant, tests 019~023, Card layout/responsive rules, soft performance guardrails, CC-008-compliant logging boundary, fixtures, acceptance/HVR scenarios and browser matrix |
