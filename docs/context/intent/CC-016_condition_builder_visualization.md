# CC-016 — 条件构建器与可视化（Condition Builder and Visualization）

## 0. Governance

| 字段 | 内容 |
|---|---|
| 文档类型 | Coding Contract |
| 版本 | v0.2 FROZEN |
| 状态 | APPROVED / FROZEN |
| Intent ID | CC-016 |
| 上游基线 | SRS_global_search v1.5 FROZEN；TDD_global_search v0.4 FROZEN；IMPLEMENTATION_PLAN_global_search v0.3 FROZEN |
| 前置契约 | CC-001 至 CC-014；CC-014-1；CC-014-2；CC-015 |
| 关联技术债 | TD-002（Condition Builder and Visualization） |
| 模块 | `wd_global_search` |
| 目标 | 仅改善用户编辑和理解现有搜索条件的方式，不增加搜索语义 |
| 批准 / 冻结 | 用户批准冻结；2026-10-13 14:38 +08:00 |

**版本基线与冻结边界：**

- 本 CC 基于 SRS v1.5、TDD v0.4、IMPLEMENTATION_PLAN v0.3；CC-014-2 v0.2 为 FROZEN，CC-015 v0.4 为 AMENDED / APPROVED。
- CC-015 虽已批准，但尚未正式关闭；TD-002 将其正式关闭列为依赖，因此本草案不得据以开始实施。
- CC-016 不修改上述上游及已批准契约的既有冻结语义；如评审或实施要求改变，须先完成影响评审并取得批准。

本 CC 的批准冻结 UI 编辑、字段选择器及条件分区展示要求，不代表实施、ATR、HVR、FR 或 Coding Closure 已完成。TD-002 将 CC-015 正式关闭列为依赖；当前 CC-015 尚未正式关闭。冻结 CC-016 不构成该依赖的豁免；在 CC-015 正式关闭或该前置依赖经批准正式变更前，不得开始 CC-016 实施。

**冻结边界：**

1. Raw Query 仍由 CC-015 服务端确定性解析；前端不生成 Condition Query Object（CQO）。
2. 字段选择器只生成 CC-002 已有 `conditions[]` 条件，不新增搜索协议或查询语义。
3. 所有实际搜索、字段可用性、operator、权限、Count、分页及错误行为继续由既有 CC 决定。
4. 本 CC 不修改 SRS、TDD、既有 CC 或 Published Configuration schema。

## 1. Contract Goal

**一句话目标：** 将 CC-015 的 Raw Query 关键词显示为可编辑 chip，为既有 `conditions[]` 提供受 Published 配置约束的字段选择器，并分区展示关键词、结构化条件和 Refinement，同时保持现有搜索语义和接口不变。

```text
当前用户输入的 Raw Query
          │
          ▼
现有 CC-015 服务端解析器 ──► 已验证 keyword terms
          │                           │
          │                           └──► 关键词 chips（仅作为 UI 表示）
          │                                  编辑/删除/添加
          │                                       │
          └───────────────────────────────────────┘
                         更新既有 query 文本后重提交

Published Searchable Fields
          │
          ├── 当前用户/公司字段与关系授权
          ├── Published operator_set
          └── 当前语言 Odoo 字段描述 ──► 字段选择器可读选项
                                             │
                                             └──► 既有 conditions[]

关键词 Raw Query + conditions[] + 既有 Refinement Conditions
                         │
                         ▼
             CC-015 / CC-002 / CC-005 既有合并与执行
                         │
                         ▼
            现有 SearchResponse、Count、分页及错误语义
                         │
                         ▼
          分区 Query Understanding（不得显示内部路径）
```

条件构建器是现有输入与有效条件的表现层。它不得替代 CC-015 parser、CC-002 Condition Merger、CC-003 Permission Boundary 或 Search Service。

## 2. Background and Acceptance Findings

### 2.1 起草前核对结果

核对范围包括 TD-002、CC-015 指定章节、CC-014-2 指定章节、CC-005、CC-002、CC-003、现有服务端/前端代码、测试组织、授权 Odoo UI 中的 Published Configuration 及当前 Search Workspace。核对仅为文档/代码读取和授权 UI 只读观察；未执行数据库或 ORM 数据查询，未直接读写数据库，未使用业务 `sudo()`，未改配置、业务数据或既有文档。

| 核对对象 | 核对依据 | 当前事实及对 CC-016 的约束 |
|---|---|---|
| TD-002 | `docs/context/debt/TD-002_condition_builder_visualization.md` | Open / P2 / 用户体验；指出当前只有文本输入，关键词不能独立编辑或删除，且没有字段选择器。建议以 chips、字段选择器和业务标签映射到完整 Published `field_path`；能力边界为 UI，不改变 CC-015 语义。依赖 CC-015 关闭、CC-014-2 路径及 CC-005 Query Understanding；按触发反馈和用户使用后评估。 |
| CC-015 §4 Condition Query Object | `CC-015_multi_condition_search.md` §4 | CQO 是服务端内部规范化对象，外层 `SearchRequest` 不变；关键词 token、完整 Published field condition 和 source 含义不得由浏览器伪造。 |
| CC-015 §6 Multi-Condition Syntax | §6 | Raw Query 使用空白或 `+` 分隔；仅 AND；最多 10 个 token、每 token 最多 100 字符，整体遵守 500 字符边界；非法语法整体拒绝。 |
| CC-015 §7 Text Entry | §7 | parser 必须是服务端确定性、无副作用流程；单 token 保持旧路径；失败按既有 `INVALID_REQUEST` 整体拒绝，不执行有效前缀。 |
| CC-015 §8 JSON Entry | §8 | 字段条件沿用 `conditions[]` 的 `dimension`、`operator`、`value`；dimension 必须是完整 Published `field_path`；不得新增 CQO 请求 envelope 或 alias。 |
| CC-015 §9 Condition Combination | §9 | 关键词 token 之间 AND；不同维度按现有 AND；同维度多值、集合字段 `any/all`、Refinement 优先级和 Resource 处理遵循既有契约。UI 的“共同筛选”说明不得改写这些规则。 |
| CC-015 §11 Query Understanding | §11 | 只显示已完成请求的、用户可见且已授权的摘要；不展示内部 relation path、未授权字段/值、内部 ID 或 SQL；错误/无效请求不能展示未执行条件为有效摘要。 |
| CC-015 §12 Permission Boundary | §12 | 字段集合来自 Published searchable 配置和当前用户授权；模型、字段、每一关系跳转、公司/Record Rule 继续由服务器执行；不使用业务 sudo。 |
| CC-015 §13 Count Consistency | §13 | 条件 UI 不改变相同有效谓词的 Count、去重、分页、Resource scope 或 cursor 绑定。 |
| CC-015 §14 Error Handling | §14 | 继续使用原状态、错误码及失败关闭；UI 不把失败转换为空成功、不显示未执行条件摘要。 |
| CC-015 §15 Invariants | §15 | CQO、parser、权限、Count、分页、Query Understanding 和禁止语义均保持 CC-015 不变量。 |
| CC-015 §17 Test Matrix | §17 | 关键词、字段权限、结构化条件、Count、分页、错误及既有回归测试仍适用；CC-016 只增加 UI 表现和字段选择交互测试。 |
| CC-014-2 §§4–7 | `CC-014-2_searchable_field_multi_level.md` | 多级 Searchable Field 使用由根模型解析的完整 `field_path`；M2O/M2M/O2M 路径深度、末端类型和集合语义按既有规则校验。UI 不简化或重写路径。 |
| CC-014-2 §10 | §10 | `operator_set` / `index_strategy` 为 Published 声明；UI 只能显示允许的 operator，不能推断物理索引或提供未配置操作符。 |
| CC-014-2 §13 | §13 | 字段路径、集合语义、权限、Count、Published Snapshot 和请求响应不变量保持不变。 |
| CC-005 Refinement | `CC-005_global_search_workspace_query_refinement.md` §§2–3、7、9、12 | Raw Query 与 Refinement 分离；修改 Raw Query 按既有状态机重置 Refinement/结果/选择；Refinement 增删时保留 Raw Query；分页、Resource Selector、错误及响应结构不变。 |
| CC-005 Query Understanding | CC-005 §§2–3、5、7 | Query Understanding 展示 Raw/Parsed/Refinement/Effective Conditions；只呈现完成请求结果，遵守语言、权限及状态机规则。 |
| CC-002 SearchRequest | `CC-002_global_search_service_core.md` §§7、9、16 | 既有字段为 `raw_query`、`parsed_conditions`、`refinement_conditions`、`resource_scope`、`offset`、`limit`、`cursor`；请求体不是权限来源。 |
| CC-002 `conditions[]` / 响应 | CC-002 §§9、16 | 沿用既有 Search API、`conditions[]`、`SearchResponse`、`effective_conditions`、`counts`、`errors`、`meta`、cursor 和错误码；不得新增搜索路由、CQO 外壳或要求客户端拼 ORM domain。 |
| CC-003 权限 | `CC-003_global_search_permission_boundary.md` §§3、5、10–12、16 | 只由 `request.env` 建立当前用户上下文；逐模型、字段、关系授权；权限或配置不能验证时失败关闭。不得用 sudo、管理员环境或请求体权限字段。 |
| 现有代码结构 | `services/types.py`、`conditions.py`、`request_boundary.py`、`executor.py`、`facade.py`、`models/configuration.py`、`controllers/main.py`、`static/src/js/preview.js` | SearchRequest/CQO、合并、解析、执行和 Query Understanding 已分层；Workspace 目前一个 Raw Query 输入、独立 Resource Selector、日期/状态 Refinement、一行 Query Understanding 和现有分页。前端目前只提交既有 `query`、`conditions`、`refinement_conditions`、`resources`、分页值。 |
| 配置与字段标签 | `models/configuration.py`、授权 UI、CC-015 §2.3 | Searchable Field Snapshot 包含完整 `name`、`purpose`、`operator_set`、`index_strategy`、`searchable`、`readable_required`、`collection_match`；没有独立选择器标签。卡片 `snapshot_fields.label` 是结果卡配置，不等同 Searchable Field 标签。用户确认：选择器标签由服务端按当前用户语言从 Odoo 字段描述生成，映射回 Published `field_path`；不新增配置字段或 Snapshot schema。 |
| 当前 Published Configuration | 授权 Odoo UI；当前页可见 `global_search_baseline` Published version `5`，checksum `4cd6cb4e0e59b2116bd7261bb8f9e8f504c1970e3bee90ea7b07dd510f00597b`；字段详情见 CC-015 §2.3 的同版本授权 UI 记录 | `name` Exact/B-tree；`client_order_ref`、`origin` Prefix/`text_pattern_ops`；`partner_id.name` Contains/GIN `pg_trgm`；`order_line.product_id.product_tmpl_id.name` Contains/GIN `pg_trgm`。Relation Paths：`partner_id` depth 1；`order_line.product_id` depth 2。当前版本校验与 CC-015 记录 checksum 一致；未修改或发布配置。 |
| 现有 Search Workspace | 用户授权内置浏览器，`/wd_global_search` | 单个文本搜索框；日期 preset/from/to、state Refinement；Query Understanding 当前为单行；Resource Selector 在搜索后呈现。没有关键词 chips、结构化字段条件选择器或条件来源分区。 |
| 现有测试结构 | `mymodules/wd_global_search/tests/` 与 `tests/__init__.py` | 有 `test_configuration.py`、`test_field_path.py`、`test_service_core.py`、`test_permission_boundary.py` 等 Odoo/纯单元测试；`test_request_boundary.py` 存在但当前未由 `tests/__init__.py` 导入。实施时必须验证新增测试的实际发现/运行方式，不得仅以文件存在视作覆盖。 |

### 2.2 Implementation Gap

1. Workspace 输入仍是一个文本框；CC-015 返回的 keyword terms 尚未呈现为独立、可编辑/删除的 chips。
2. Workspace 不维护独立的结构化 `conditions[]` 编辑状态，也没有从已发布字段创建条件的选择器。
3. 当前 Resource descriptor 只包含 Resource key 和用户可见 Resource label；不包含 Searchable Field 选择器选项或 Searchable Field 的可读标签。
4. Searchable Field Snapshot 没有用户可读的 field label；当前 Query Understanding 对结构化条件直接显示 dimension 文本，可能露出技术路径。
5. Query Understanding 当前把有效条件放在一个单行摘要中，未分区显示关键词、结构化条件和 Refinement。
6. 现有控制器、SearchRequest、Search API 与条件合并已经提供复用边界；CC-016 不需要新增公开请求 envelope 或搜索路由。

### 2.3 Existing Contract Support

- CC-015 已定义 server-side keyword 解析、条件 CQO、结构化 `conditions[]`、有效条件组合及已授权摘要，可供 UI 作为唯一搜索语义来源。
- CC-002 已定义 SearchRequest、SearchResponse、`conditions[]`、分页、cursor、Count 和错误边界。
- CC-003/CC-014-2 已定义当前用户字段/关系授权和完整 `field_path` 校验。
- CC-005 已定义 Raw Query、Refinement 的状态转换以及 Query Understanding 的完成时机。
- 当前 Published 配置已经提供字段路径、operator_set 和字段类型校验依据；标签可从当前用户语言下 Odoo 字段描述生成，不改变配置 schema。

本 CC 是增补的 UI 契约，不修改 SRS、TDD、CC-001、CC-002、CC-003、CC-005、CC-007、CC-012、CC-013、CC-014、CC-014-1、CC-014-2 或 CC-015 的冻结语义。

## 3. Scope

### 3.1 In Scope

- 将已验证的 Raw Query 多词结果显示为关键词 chips，支持删除、编辑和添加关键词。
- 所有关键词 chip 编辑只更新既有 Raw Query 文本，再走 CC-015 解析器。
- 根据当前 Published Searchable Fields 和当前用户授权提供字段选择器。
- 由服务端按当前用户语言从 Odoo 字段描述生成可读标签，并将选择映射到对应的完整 Published `field_path`。
- 字段选择器只允许 Published `operator_set` 所允许的 operator，并使用现有 `conditions[]` 提交结构化条件。
- 将关键词、结构化条件及 Refinement 分区展示，解释其既有合取关系。
- 错误、部分成功、进行中和条件/配置变化时遵守现有 Query Understanding、分页和权限状态机。

### 3.2 Out of Scope

- 新增搜索语义、OR、NOT、括号、字段限定或自然语言解释。
- 搜索历史、保存搜索、分享、收藏或条件建议。
- 性能优化、索引/查询计划改造、缓存或估算 Count。
- 修改 CC-015 的 Contains 多词、单词兼容、JSON 条件或错误语义。
- 修改 CC-014-2 的路径语法、深度、集合匹配或索引规则。
- 修改 CC-002/CC-003/CC-005/CC-007/CC-012/CC-013/CC-014/CC-014-1 的语义。
- 新增公开 API 路由、CQO envelope、Published Searchable Field label 字段或 Snapshot schema。
- 引入 LLM、向量检索、Elasticsearch、OpenSearch 或其他外部搜索服务。
- 修改 `odoo/`、官方 addons、数据库 schema 或业务数据。

### 3.3 与 CC-015 的边界

- 关键词 chips 是 Raw Query 的可视化编辑方式；用户可见的 token 解析和搜索域始终由 CC-015 服务端 parser/adapter 决定。
- 字段选择器只产生 CC-002 既有 `conditions[]`；同维度 OR、不同维度 AND、Published operator、集合匹配及 Refinement 优先级完全沿用 CC-015/CC-002。
- UI 不自行生成、提交或修改 CQO，不创建新 dimension、operator、alias 或查询 combinator。

### 3.4 与 CC-014-2 的边界

- 选择器选项只来自已 Published、`searchable=true` 且通过 CC-014-2 校验的完整 `field_path`。
- 关系路径的显示标签不替代或缩短 `field_path`；请求仍用既有完整 dimension。
- 路径形态、关系深度、末端字段类型、`collection_match` 和索引规则保持 CC-014-2 决定。

## 4. Keyword Chip

### 4.1 展示

- 成功/EMPTY 响应的 Query Understanding 可将服务端 `effective_conditions` 中的 `dimension="keyword"` 项展示为独立关键词 chip。
- 每个 chip 显示一个已验证 token；多个关键词之间明确显示 `AND`。
- 搜索框仍保留可编辑 Raw Query 文本及 CC-005 既有提交行为。Chip 是该文本已解析结果的交互表示，不是新的查询状态或 CQO。
- 正在处理新请求时不得把旧响应摘要呈现为新输入的已生效 chips；响应状态依 CC-015/CC-005 处理。

### 4.2 删除关键词

- 删除一个关键词后，UI 只更新 Raw Query 文本并按既有分隔符序列化剩余关键词；不得直接修改服务端条件对象。
- 更新后的文本重新提交给 CC-015 parser。零个关键词时按既有空 Raw Query 行为处理；单个关键词必须重新走 CC-015 的单 token 兼容路径。
- 因为 Raw Query 已改变，按 CC-005 既有状态转换清除 Refinement、旧结果、选中记录和不兼容的分页/cursor；结构化 `conditions[]` 仍作为独立条件，不由关键词删除隐式改写。

### 4.3 编辑关键词

- 编辑一个 chip 只替换其对应文本 token，并重新提交 Raw Query。
- 前端不自行验证/规范化为 CQO，不执行字段判断，也不对错误文本做部分解析。
- 编辑结果如果违反 CC-015 语法或边界，显示既有错误状态；不能保留旧 chips 作为新查询的有效条件。

### 4.4 添加关键词

- “添加关键词”输入只把文本追加到现有 Raw Query，再提交至 CC-015 parser。
- 空白和 `+` 继续遵循 CC-015 分隔符规则；UI 不提供引号、OR、NOT、括号或转义语法。
- 新增/删除/编辑后重置当前页和 cursor。原始关键词组合行为仍完全由 CC-015 决定。

### 4.5 前端责任

- 前端只序列化现有 `query` 文本；不得构造 `ConditionQueryObject`、ORM domain、relation expression 或 server-side keyword term。
- 服务端返回并授权的有效关键词是已提交 chip 显示的权威来源；客户端本地草稿仅供编辑，不得冒充搜索已生效条件。
- 关键词变化触发搜索时，始终使用原有 SearchRequest 和 CC-005 状态机。

## 5. Field Selector

### 5.1 可选字段来源

- 选项来自当前 Published Snapshot 中当前 Resource/model 的 `searchable=true` Searchable Fields。
- 每次构造选项都使用当前请求用户的授权环境检查模型、字段、路径每一跳和关联模型；不得复用跨用户的授权结论。
- 多 Resource 选择下，只呈现对本次所选范围都可按既有条件语义安全使用的字段选项；不能把一个 Resource 的字段条件静默限制为该 Resource 专属，也不能让其他 Resource 忽略该条件。若不存在可安全共用的选项，说明无可用字段，不猜测或扩大查询。
- Published Configuration 版本或 Resource Selection 改变后，丢弃旧选择器项并按当前版本/范围重新生成。

### 5.2 用户可读标签与路径映射

- 当前模型的 Searchable Field Snapshot 只有完整 `field_path` 等配置，没有选择器专用显示标签；CC-016 不新增 `selector_label` 或修改 Published schema。
- 服务端通过当前用户 `request.env` 的 Odoo ORM 字段元数据（例如 `fields_get()` 返回的已翻译字段 `string`/field description）取得路径各段描述；不得直接 SQL 查询字段元数据。标签按当前用户语言生成，并在服务器选项中保留到唯一 Published `field_path` 的映射。
- 重复字段名使用父关系段的可读描述形成层级区分，例如“客户 › 城市”和“供应商 › 城市”。如完整可读层级仍冲突或缺少翻译/描述，该选项不显示；不得附加技术路径以强行区分。Resource/model 提示也只能使用现有可见标签，不显示技术 model name。
- UI 可见文本、辅助文本、Query Understanding 和错误不得显示完整 `field_path`、模型名、关系表达式或内部配置 ID。`conditions[].dimension` 仍按 CC-015 使用完整路径作为既有协议值，但不得作为可见 label。
- 如果当前用户语言下无法生成安全、可区分的标签，该字段选项不显示；不得退回显示技术路径。遵守 CC-009 现有语言来源及 fallback。

### 5.3 Operator 与值

- Operator 选项只来自该 Published Searchable Field 的 `operator_set`；当前配置模型每条字段记录声明一个 `exact`、`prefix` 或 `contains` operator set。UI 不扩展为未配置的 operator。
- 展示名遵循用户语言；提交值遵循 CC-015/CC-002 现有 `conditions[]` operator 约定。Exact 使用已定义的精确 operator；不新增比较符、模糊匹配或别名。
- 字段值控件限于 CC-014-2 §5 已支持的末端类型：Char/Text 使用文本输入；Integer 使用整数输入；Float/Monetary 使用数值输入；Date 使用日期选择器；Datetime 使用日期时间选择器；Boolean 使用是/否选择；Selection 使用当前用户语言下的选项选择器。
- 以上控件只负责产生类型正确的既有 JSON scalar；不得转换币种、把日期/数值格式文本作为另一种比较语义提交，或增加新的控件/字段类型。CC-014-2 不支持的类型不提供选择器选项。
- 字段或操作符不再可用时，提交前刷新/重新校验；不能用历史选项替代当前 Published 配置。

### 5.4 提交条件

- 添加结构化条件时提交既有 `conditions[]` 条目：完整 Published `dimension`、允许的 `operator` 和类型正确的 `value`。
- 不新增 `condition_query`、field alias、client domain、路径属性或权限声明。
- 增删/编辑结构化条件只更新结构化条件状态，不改写 Raw Query；既有 Raw Query 与 Refinement 状态规则不变。任何条件变化均回到第 1 页并丢弃旧 cursor。
- 服务端重新验证字段路径、operator、值类型及当前用户权限。选择器显示过某字段不构成授权凭证。

## 6. Condition Partition Display

### 6.1 分区

Query Understanding 使用独立分区展示当前已生效条件：

1. **关键词：** 每个服务端确认的 keyword token 一个 chip，并明确说明关键词之间为 AND。
2. **结构化条件：** 使用用户可读字段标签、用户可读 operator 和安全格式化后的值显示现有 `conditions[]` 条件。
3. **Refinement：** 展示现有 Resource/date/state Refinement；沿用 CC-005 控件、日期和状态标签，不转换成关键词或字段条件。
4. **共同筛选关系：** 明确关键词、结构化条件与 Refinement 经现有 Effective Conditions 组合筛选结果；不同来源/不同维度按既有 CC-002/CC-005/CC-015 AND 语义组合。

“共同筛选”是对现行合并结果的说明，不得将同一维度多个值的现有 OR、集合字段 `any/all`、Resource scope 或 Refinement 优先级显示成新的全局 AND 规则。

示意布局（可按既有 Workspace 视觉规范调整，不冻结具体控件或 CSS）：

```text
关键词：
  [001 ×] [chair ×]
  → 关键词之间是 AND

结构化条件：
  客户 › 名称  包含  Acme  [×]
  → 与关键词及其他有效条件按既有合并规则组合

Refinement：
  日期：2026-01 ~ 2026-03
  状态：未完成
  → 与关键词及结构化条件按既有合并规则组合

共同筛选结果：
  关键词 AND 结构化条件 AND Refinement
```

示意中的可读字段文本来自运行时本地化标签；共同筛选文案须同时遵守本节第一段的同维度 OR、集合及优先级限制。

### 6.2 权威性与状态

- 分区显示以最近一次完成请求的有效响应为准，且只有通过权限及配置验证的条件才可显示为已生效。
- `SEARCHING` 时不得将未完成请求的部分解析内容标为有效；旧响应不得冒充新 Raw Query/conditions 的结果。
- `SUCCESS`/`EMPTY` 显示有效摘要；`PARTIAL_SUCCESS` 保留失败 Resource 状态，只显示服务端确认可见的已生效摘要；整体失败、超时或无效请求遵守 CC-015/CC-005，不显示未执行条件为已生效条件。
- Resource Selector 和 facet counts 仍按 CC-012 显示，不把 Resource 数量混入结构化字段条件。

### 6.3 隐私与可读性

- UI 只显示可读字段标签，不展示内部路径；无法映射的 dimension 显示安全通用状态或不展示，不回显技术值。
- 结构化值及 Refinement value 只在当前用户有权且本次成功结果允许显示时呈现；不得通过标签、数量或错误暗示未授权字段/记录存在。
- 所有用户可见文本遵循当前用户语言与 CC-009；用户输入以文本节点安全渲染。

## 7. CC-015 Compatibility

- **Contains 多词语义：** 编辑器只展示/更新 Raw Query；每个 token 的字段展开、Contains 字段集合、token AND 及同一根记录身份仍由 CC-015 执行。
- **单词兼容：** 删除或编辑后剩余一个 token 时走 CC-015 单 token 旧路径，不因存在 chips 改变 operator 或字段范围。
- **结构化条件：** 字段选择器只通过既有 `conditions[]` 表达；Published `operator_set`、同维度 OR、不同维度 AND 及完整路径校验不变。
- **Count：** 不做本地估算，不从当前页或 Resource selector 推导 Count。Count 与结果继续使用服务端同一有效谓词和权限集合。
- **分页/cursor：** Raw Query、结构化条件、Refinement、Resource Selection、Published version 或 page size 改变时，按既有规则重置页/失效 cursor；不复用旧条件的页状态。
- **错误行为：** 超限、非法 token、无效字段、未配置 operator、无权限、配置异常、部分失败和超时均使用 CC-002/CC-003/CC-005/CC-007/CC-015 既有协议。UI 不吞错、不把错误显示为空成功。
- **请求/响应：** 不增加公开 SearchRequest envelope 或 endpoint；保留既有 `query`、`conditions[]`、`refinement_conditions[]`、`resources[]`、分页/cursor 及响应结构。选择器所需的显示元数据只能通过既有 Workspace descriptor/response 扩展机制提供，且不得改变搜索 API 语义。

## 8. Permission Boundary

- 可选字段及其标签只能由服务端从当前 Published Snapshot 和当前用户/公司环境生成；不得直接从客户端提供的路径、字段列表或权限声明建构。
- 当前用户可访问性须在展示字段选项前，通过 CC-003 对模型、字段、关系每一跳和公司范围的现有授权流程检查。
- 结构化条件提交时，服务端再次验证完整 `field_path`、Published `operator_set`、末端类型、有效 Resource/model 和当前用户权限；UI 隐藏或曾展示字段均不能替代请求时授权。
- 权限变化或 Published version 变化后，旧字段选项作废并按当前环境重新验证；不得跨用户共享授权缓存。
- 无权限字段不能通过 selector option、错误、Query Understanding、结果、Count、分页或 timing 推断。不可验证时按 CC-003/CC-007 失败关闭。
- 不使用业务 `sudo()`、superuser/admin env、直接 SQL、数据库读取或请求体用户/公司/权限字段。仅复用现有 CC-001 Published configuration provider 的控制面读取边界，不扩大其授权例外。

## 9. Invariants

前两条专指关键词 chip；字段选择器另按 INV-004、INV-006 和 INV-022 使用既有结构化条件。

| ID | 冻结不变量 |
|---|---|
| CC16-INV-001 | 前端不自行生成 CQO；CQO 只由 CC-015 服务端流程构造。 |
| CC16-INV-002 | 关键词 chip 编辑/删除/添加只更新 Raw Query 文本，不直接改写 CQO、domain 或服务端条件。 |
| CC16-INV-003 | 更新后的关键词查询文本一律交给 CC-015 确定性解析流程。 |
| CC16-INV-004 | 字段选择器标签映射到当前 Published 配置中的完整 `field_path`；结构化搜索继续提交既有 `conditions[]`。 |
| CC16-INV-005 | UI 不向用户展示技术 `field_path`、内部 model/path 表达式或配置 ID。 |
| CC16-INV-006 | 字段选择器不允许超出该字段 Published `operator_set` 的操作符。 |
| CC16-INV-007 | 保持 CC-015 多词 Char/Text Contains 与 token AND 语义。 |
| CC16-INV-008 | 保持 CC-015 单 token 兼容行为。 |
| CC16-INV-009 | 保持 CC-015/CC-002 精确 Count 语义；不使用客户端估算。 |
| CC16-INV-010 | 保持 CC-002/CC-005 分页、cursor、重置与稳定结果语义。 |
| CC16-INV-011 | 保持 CC-002/CC-003/CC-005/CC-007/CC-015 错误、失败关闭和部分失败行为。 |
| CC16-INV-012 | 字段可用性、权限、operator/value/path 校验仍由服务端完成。 |
| CC16-INV-013 | 条件分区展示不得泄露未授权信息或内部技术路径。 |
| CC16-INV-014 | 条件分区明确展示现有 AND 关系，同时保留同维度 OR 与集合语义。 |
| CC16-INV-015 | CC-016 不增加搜索语义。 |
| CC16-INV-016 | CC-016 不增加 OR、NOT 或括号。 |
| CC16-INV-017 | CC-016 不增加字段限定语法或客户端 relation expression。 |
| CC16-INV-018 | CC-016 不增加搜索历史。 |
| CC16-INV-019 | CC-016 不增加保存、分享或收藏搜索。 |
| CC16-INV-020 | CC-016 不增加条件建议。 |
| CC16-INV-021 | CC-016 不修改 CC-014-2 `field_path` 语法、深度或集合语义。 |
| CC16-INV-022 | 字段选择器提交沿用 CC-002/CC-015 的 `conditions[]`，不新增外部 envelope 或 route。 |
| CC16-INV-023 | Keyword、structured condition、Refinement 的分区仅用于安全展示，不改变其来源或 Effective Conditions 合并顺序。 |
| CC16-INV-024 | 未完成、失败、过期或无效请求的条件不得呈现为当前已生效条件。 |
| CC16-INV-025 | 选项元数据不持久化跨用户条件、不写业务数据、不修改 Published Configuration。 |
| CC16-INV-026 | Odoo 当前用户语言只由服务端上下文提供；标签不由请求体指定。 |

## 10. Publish-time Validation

### 10.1 字段选择器配置验证

- 选择器候选字段必须来自当前版本中适用 Resource/model 的 Published `searchable=true` 配置。
- 发布/Apply 时复用现有配置发布校验和 CC-014-2 `validate_field_path`：完整路径、根模型、关系类型/深度、终端字段类型、存储属性、`collection_match` 和配置上限不得被 UI 放宽。
- UI 不增加独立 alias 或另一个未经 Published 配置约束的字段来源。

### 10.2 Operator 配置验证

- 发布/Apply 时复用 `operator_set`、`index_strategy` 的既有类型兼容校验。
- 选择器仅呈现该字段当前 Published `operator_set` 所允许的操作；前端传入不匹配的 operator 时仍由服务端失败关闭。
- Operator 标签仅是本地化显示映射，不能更改既有 Search API operator 或 executor 解释。

### 10.3 关键词 chip 验证

- 关键词 chip 没有独立的 Published 配置项；不得新建 chip 配置或 Snapshot schema。
- 可参与 Raw Query 的字段资格继续使用 CC-015 的 Publish-time searchable-field 验证。
- 每次 chip 操作产生的文本长度、token 数、语法和字符限制均由 CC-015 request boundary 校验；Publish-time 不重复实现 parser。

### 10.4 标签验证时机

- 用户可读标签由服务端在当前用户语言上下文中按 Odoo 字段描述生成；不写回 Published Snapshot。
- Publish-time 验证字段路径及 operator 配置；运行时验证当前语言标签可安全显示、映射唯一且对应当前 Published path。
- 运行时不能安全生成标签时，不显示该字段选项且不得回退输出技术路径；不改变已发布字段的搜索执行语义。

## 11. Test Matrix

所有测试使用隔离配置/fixture 与当前用户环境；不读写共享业务数据、不直接访问数据库、不使用业务 sudo。浏览器测试走现有 Workspace/Search API；不新增公开路由。

测试 fixture 沿用现有 Odoo 测试事务/隔离模式，不在本 CC 固定新增目录或模块布局。覆盖的 Resource、字段类型、Published operator、用户权限和语言只取 CC-014-2 支持范围；测试结束由现有测试事务回滚，不从生产数据复制 fixture。

| 测试 ID | 类型 | 输入 / 操作 | 必须断言 |
|---|---|---|---|
| CC16-TEST-001 | 浏览器 | 搜索两个有效 token，例如 `001 chair` | 完成请求后展示两个独立 keyword chips，并明确标出 AND；请求和结果符合 CC-015。 |
| CC16-TEST-002 | 浏览器 + 请求断言 | 删除其中一个 keyword chip | 仅 Raw Query 文本更新；单 token 请求交给 CC-015 旧路径；不由 UI 直接改 CQO。 |
| CC16-TEST-003 | 浏览器 + 请求断言 | 编辑一个 keyword chip 为另一个单 token | 更新后的 Raw Query 被提交，服务端返回的 effective keyword 决定最终 chips；旧摘要不冒充新结果。 |
| CC16-TEST-004 | 浏览器 + 请求断言 | 添加一个关键词 | 文本追加到既有 Raw Query 后经 CC-015 解析；未新增请求 envelope。 |
| CC16-TEST-005 | 浏览器 | chip 编辑后产生不支持语法或超限 token | 既有 `INVALID_REQUEST` 全量错误状态；无有效前缀执行，未执行条件不显示为有效 chips。 |
| CC16-TEST-006 | 配置/服务集成 + 浏览器 | 在有效 Published 配置下打开字段选择器 | 只显示当前 Resource/model 中 Published searchable 且当前用户获准字段。 |
| CC16-TEST-007 | 浏览器 + SearchRequest 断言 | 选择多级关系字段并添加条件 | 显示标签来自当前用户语言下字段描述的可读层级；提交的 `conditions[].dimension` 映射到确切完整 Published `field_path`。 |
| CC16-TEST-008 | 浏览器 | 检查字段选项、辅助文本、Query Understanding、错误文本及 DOM 可见内容 | 不显示技术 path、内部 model/path 表达式或配置 ID。 |
| CC16-TEST-009 | 浏览器 + 配置测试 | 检查 Exact、Prefix、Contains 配置字段的操作符选项 | 每个字段只提供其 Published `operator_set` 对应操作；无配置 operator 不可选。 |
| CC16-TEST-010 | API/集成 | 篡改字段 dimension、operator 或类型不符的 value | 服务端重新校验并按既有 INVALID_REQUEST / 权限 / 配置错误失败关闭；不执行猜测条件。 |
| CC16-TEST-011 | 浏览器 + API 断言 | 添加一个结构化字段条件 | 使用既有 `conditions[]` 的完整 dimension/operator/value；Raw Query 和 SearchRequest 外层不变。 |
| CC16-TEST-012 | 浏览器 | 在关键词、字段选择器、日期/状态 Refinement 均有值时查看 Query Understanding | 显示三个独立分区和共同筛选的 AND 说明；遵守同维度 OR 和既有 Refinement 语义。 |
| CC16-TEST-013 | 浏览器 + 响应对比 | 提交 Resource/date/state Refinement 并改变 Refinement | Refinement 分区使用既有标签/值；Raw Query 保持 CC-005 规则，资源/日期/状态条件不被改写为 keyword/field 条件。 |
| CC16-TEST-014 | 浏览器 | 发起慢请求后再提交另一请求，随后观察 Query Understanding | SEARCHING/过期响应不得把旧摘要或新请求未完成条件标成已生效。 |
| CC16-TEST-015 | 浏览器 + 权限集成 | 查询成功、EMPTY、PARTIAL_SUCCESS、FAILED、TIMEOUT 或 INVALID_REQUEST | 按 CC-005/CC-007/CC-015 展示状态；错误/失败 Resource 不伪装为零结果，未执行条件不显示为有效。 |
| CC16-TEST-016 | 用户权限集成 + 浏览器 | 以可访问/不可访问字段用户加载选择器 | 不可访问字段和标签不出现；伪造旧选项提交仍由服务端拒绝；Count/结果不泄露字段存在性。 |
| CC16-TEST-017 | 多 Resource 集成 + 浏览器 | 选择多个 Resource 并打开字段选择器 | 仅呈现对整个所选范围都安全适用的共有字段；不存在共有项时不给出可能扩大结果的选项。 |
| CC16-TEST-018 | 配置版本集成 + 浏览器 | Published version/checksum 改变后继续编辑旧选择器 | 旧 option 作废，按新版本刷新；旧 dimension 不能绕过当前 Published 校验。 |
| CC16-TEST-019 | 浏览器 + 搜索结果对比 | 对同一有效 `001 chair` Raw Query 比较加入 chips 前后的请求和结果 | Raw Query、授权 Result Identity、Count 与 CC-015 基线一致；UI 表示变化不影响 Contains 多词语义。 |
| CC16-TEST-020 | 浏览器 + 搜索结果对比 | 对同一单 token 查询比较加入 chips 前后的请求 | 维持 CC-015 单 token 路径、Result Identity、Count 和错误行为。 |
| CC16-TEST-021 | 集成 | 对相同条件比较 Count、分页结果和 page size | Count 与 CC-015/CC-002 基线一致，不使用客户端估算；更改条件后页/cursor 按既有规则失效。 |
| CC16-TEST-022 | 多公司/多用户集成 | 用户、公司、字段权限变化后刷新选择器并提交条件 | 新请求/选项按当前用户重新授权；不跨用户复用路径或标签授权。 |
| CC16-TEST-023 | 浏览器安全 | 在值/标签中输入 HTML 特殊字符并呈现 | 以文本安全渲染，不执行用户输入；不改变服务端错误或日志策略。 |
| CC16-TEST-024 | 配置集成 | 验证无效路径、无效 operator、unsupported terminal type 的 Published 配置 | 复用 CC-014-2/现有发布校验拒绝；CC-016 不使无效配置通过。 |
| CC16-TEST-025 | 回归集成 | 同维度多个结构化值、不同维度条件及 collection `any/all` | 与 CC-002/CC-014-2 既有 OR/AND/集合语义一致，不因分区显示改变条件组合。 |
| CC16-TEST-026 | 浏览器矩阵 | 在 CC-005 规定的浏览器/视口验证 chips、selector、分区及现有 Workspace | 控件可操作且无路径泄露；Resource Selector、Refinement、结果、分页、无 Preview 规则不回归。 |
| CC16-TEST-027 | 性能回归与观测 | 在 CC-015 性能测试的相同受控环境执行搜索、Count、Query Understanding；同时记录 chips/字段选择器的渲染测量 | 搜索、Refinement、Query Understanding、结果列表及 Count 遵守 CC-002/CC-005/CC-012/CC-015 继承预算并记录环境与 P50/P95/P99；chips/selector 不引入重复搜索请求，其测量仅记录，不增加未经批准的新阈值。 |

浏览器兼容性矩阵继承 CC-005 §10.3；必须记录实际浏览器版本及各视口结果，不因 CC-016 扩大或缩小浏览器支持范围：

| 浏览器 | 版本 | 桌面 | 平板 | 窄屏 |
|---|---|---|---|---|
| Chrome | 最新稳定版 | 必测 | 必测 | 必测 |
| Firefox | 最新稳定版 | 必测 | 必测 | 必测 |
| Safari | 最新稳定版 | 必测 | 必测 | 必测 |
| Edge | 最新稳定版 | 必测 | 必测 | 必测 |

## 12. Regression Requirements

- **CC-002：** `SearchRequest`、`conditions[]`、Search API/response、counts、cursor、分页、错误结构及同维度 OR/不同维度 AND 保持兼容。
- **CC-003：** 当前用户/公司、模型/字段/关系授权、Record Rule、字段过滤及失败关闭不被 UI 选项绕过。
- **CC-005：** Raw Query 与 Refinement 分离、Raw Query 变更时的既有状态机、Refinement 增删、Query Understanding 完成时机、Resource Selector、分页和响应式行为保持兼容。
- **CC-007：** `EMPTY`、`PARTIAL_SUCCESS`、`FAILED`、`TIMEOUT` 和错误聚合保持原语义；UI 不伪造成功。
- **CC-008：** 日志字段 allowlist/audit 语义不变；不新增记录 Raw Query、条件值、field path 或用户输入的日志。
- **CC-009：** 标签、语言、时区来源继续由服务端提供；UI 使用当前用户语言显示 Odoo 字段描述。
- **CC-010：** Published checksum、配置版本、Apply/Publish 工作流不因 Workspace 编辑而变化。
- **CC-012：** Resource Selector、多选、facet counts、selected-resource scope 和精确结果 Count 不变。
- **CC-013：** 结果卡片及显式打开记录仍使用已配置的 Form Action。
- **CC-014 / CC-014-1：** Card Template、关系字段渲染、字段授权和导航不变。
- **CC-014-2：** 完整 `field_path`、M2O/M2M/O2M 深度、`collection_match`、operator 和索引规则不变；label 映射不得变为新 alias。
- **CC-015：** Contains 多词语义、单 token 兼容、Text/JSON adapter、权限、Count、分页、cursor、错误与 Query Understanding 安全约束不变。
- **TD-001：** Raw Query 500 字符、合计条件数 20、嵌套深度 3、请求 Relation Path 深度 2、日志/错误输入边界保持不变。

## 13. Stop Conditions

出现以下任一情形，停止对应设计/实施，不得静默降级：

1. 关键词 chips 无法以可复核证据证明只更新既有 Raw Query，或要求前端构造 CQO。
2. 删除/编辑关键词不能复用 CC-015 parser，或需要改变 CC-015 的 token/错误/单词语义。
3. 字段标签无法在当前用户语言下安全映射到唯一 Published `field_path`，且唯一可用回退是显示技术路径。
4. 字段选择器无法证明选项来自当前 Published snapshot 和当前用户授权集合。
5. 多 Resource 下无法确定一个结构化条件对所选范围均安全适用，或条件会被部分 Resource 静默忽略。
6. 字段选择器需要绕开 CC-014-2 路径校验、扩大 operator_set、改变 field_path 或引入 alias。
7. Query Understanding 分区无法证明不泄露内部路径、隐藏字段、未授权值或失败 Resource 信息。
8. 条件分区显示要求改变 CC-002 同维度 OR、CC-005 Refinement 优先级或 CC-015 AND/token 语义。
9. 请求/响应要求新增 Search API 路由、公开 CQO envelope、客户端 domain 或不兼容 SearchRequest。
10. 需要改动现有冻结契约但未完成影响分析和用户批准。
11. 需要 `sudo()`/superuser/admin env 读取业务模型、业务字段或业务记录，或需要直接数据库读取。
12. 需要修改 `odoo/` 或官方 addons，或引入 LLM、向量检索、Elasticsearch、OpenSearch、搜索历史、保存搜索、建议或性能优化。
13. CC-015 未正式关闭且 TD-002 的前置依赖没有获准变更时，不得开始 CC-016 实施，即使本 CC 已批准冻结。
14. 新增测试无法在既有测试体系中被发现并实际执行，且没有经评审的替代验证方式。

## 14. Definition of Done

只有全部适用证据完成后，CC-016 才可关闭：

- 关键词 chip 展示、添加、删除、编辑均只操作 Raw Query 文本，并经 CC-015 parser。
- 字段选择器候选来自当前 Published searchable 配置及当前用户权限；标签按当前用户语言安全生成并映射回完整 Published path。
- 操作符和值控件严格符合 Published `operator_set` 和 CC-015/CC-014-2 类型约束。
- Query Understanding 将关键词、结构化条件、Refinement 分区并明确解释既有合并关系，不泄露技术路径或未授权信息。
- CC-015 Contains 多词、单 token、错误状态、Count、分页/cursor、Partial Success 及 HVR 相关搜索行为回归通过。
- CC-002、CC-003、CC-005、CC-007、CC-008、CC-009、CC-010、CC-012、CC-013、CC-014、CC-014-1、CC-014-2、CC-015 和 TD-001 适用回归通过并有证据。
- CC16-TEST-001 至 CC16-TEST-027 有可复核执行结果；未执行项不得标成通过。
- 性能验证复用 CC-002/CC-005/CC-012/CC-015 已批准软预算及观测要求；不采用本 CC 新设的 P95 阈值，不得以牺牲权限检查满足预算。
- `IHR`、`ATR` 和适用的人工 `HVR` 证据齐备；人工验证覆盖所需浏览器/视口，并明确已确认范围。
- 未修改冻结 SRS/TDD/既有 CC、Published schema、业务数据或官方 Odoo 代码；未引入权限旁路或禁用依赖。
- 由 FR 汇总 CC + IHR + ATR + HVR 判断 Closure；CC-016 本身及自动化/Playwright 不得替代 FR 或用户 HVR。

### 14.1 验收场景

1. 输入 `001 chair` 并完成搜索，看到两个关键词 chip 及其 AND 说明。
2. 删除一个 chip 后，Raw Query 更新并按 CC-015 重新解析；不保留失效摘要。
3. 编辑一个 chip 后，仅对应关键词文本变化，服务端响应决定有效条件。
4. 添加关键词后，Raw Query 更新并按 CC-015 重新解析。
5. 打开字段选择器，只看到当前 Published 且当前用户可访问、标签安全的字段。
6. 选择字段、operator 和类型正确的值，提交现有 `conditions[]`。
7. 查看 Query Understanding，关键词、结构化条件和 Refinement 分区及 AND 说明清楚。
8. 用无权用户验证不可访问字段和相关信息不泄露。
9. 多 Resource 选择时只显示对所选范围共有且安全适用的字段；无共有项时明确无可用选项。
10. 验证非法输入、权限失败和 Resource 部分失败遵守原错误状态，不伪装成功。

### 14.2 HVR 场景

由用户在授权内置浏览器中人工执行以上 10 项验收场景，记录浏览器/版本/视口、Published version/checksum、请求结果和实际观察；HVR 记录只确认实际执行场景，不得把未执行项标为通过。浏览器与视口按 §11 继承 CC-005 §10.3 矩阵。

## 15. Decisions

| Decision ID | 决定 | 理由 |
|---|---|---|
| CC16-DEC-001 | 前端不自行生成 CQO。 | CQO 是 CC-015 服务端内部对象；由客户端生成会复制 parser/授权边界并可能造成语义分叉。 |
| CC16-DEC-002 | 关键词 chip 编辑仅更新 Raw Query 文本。 | 复用现有 SearchRequest 和 CC-005 状态机，不引入第二个关键词协议。 |
| CC16-DEC-003 | 所有更新后的关键词文本交给 CC-015 解析流程。 | 保证 token 限制、Contains 语义、单词兼容和失败关闭只有一套权威实现。 |
| CC16-DEC-004 | 选择器标签由服务端按当前用户语言从 Odoo 字段描述生成，再映射到 Published 完整 `field_path`；不新增显式标签字段或 Snapshot schema。 | 当前 Searchable Field Snapshot 没有专用标签；用户已选择复用 Odoo 字段描述，避免改变冻结配置契约。 |
| CC16-DEC-005 | 技术路径只作为既有 conditions dimension 的内部提交值，不作为 UI 可见标签。 | 兼容 CC-015 完整路径验证，同时满足不泄露技术路径的要求。 |
| CC16-DEC-006 | 操作符选项严格由 Published `operator_set` 提供。 | 防止 UI 暴露配置未允许的比较能力或改变执行语义。 |
| CC16-DEC-007 | 关键词 chip 保持 CC-015 的 Contains-on-text token AND。 | CC-016 只改变编辑方式，不重新定义搜索逻辑。 |
| CC16-DEC-008 | 单 token 仍使用 CC-015 的旧路径。 | 防止可视化包装意外改变既有单词查询兼容行为。 |
| CC16-DEC-009 | Query Understanding 分区标示跨来源的 AND，但保留同维度 OR、集合和 Refinement 优先级。 | 说明用户可见组合关系，同时不与 CC-002/CC-005/CC-014-2 冻结规则冲突。 |
| CC16-DEC-010 | 不增加搜索语义、外部服务、新 route 或 CQO 请求 envelope。 | 维持 CC-016 的 UI-only 范围和所有前置契约兼容。 |
| CC16-DEC-011 | 多 Resource 选择时只显示可安全应用于整个所选范围的共有字段选项。 | 现有 `conditions[]` 没有按 Resource 限定的语义；共有字段避免条件被部分 Resource 静默忽略或扩大搜索结果。 |
| CC16-DEC-012 | Published 配置变更或用户权限变化时重新生成/授权字段选择器选项。 | 避免过期 selector 项充当权限凭证或绕过当前 Snapshot。 |
| CC16-DEC-013 | 不引入性能优化或新性能阈值；只继承 CC-002/CC-005/CC-012/CC-015 已批准的性能预算并记录新 UI 的测量值。 | 防止 CC-016 改变为性能项目或凭空设定 P95 预算；新阈值须以基线证据另行评审。 |

## 16. Implementation Structure

以下为依据当前实现结构确认的职责边界，不是冻结文件计划、新目录约定或 API 路由约定：

| 当前组件 | CC-016 对应职责 | 不应承担的责任 |
|---|---|---|
| `services/types.py` | 保持现有 SearchRequest/CQO 服务端类型；只有实施确有需要且经评审时才扩展显示类型。 | 不让浏览器构造 CQO。 |
| `services/conditions.py` | 复用现有 Parsed/Refinement 合并及去重语义。 | 不新增 AND/OR 解析或改写来源优先级。 |
| `services/request_boundary.py` | 继续由 CC-015 解析关键词、验证长度/语法/条件边界。 | 不复制一份前端权威 parser。 |
| `services/executor.py` | 保持现有 Published operator/path 执行及 Count 谓词。 | 不加入 UI label 或改变查询语义。 |
| `services/facade.py` | 复用 Published snapshot、当前用户授权、资源描述与有效条件；按需提供安全 selector 元数据和可读摘要。 | 不在字段选择器绕开 `authorize_searchable_fields`。 |
| `models/configuration.py` / `services/provider.py` | 复用 Published searchable fields、operator_set、路径校验和 snapshot；运行时由 Odoo 字段描述产生本地化标签。 | 不新增 selector label 字段、修改 Published schema 或写配置。 |
| `controllers/main.py` | 复用 Workspace 页面与既有 SearchRequest/SearchResponse 接线；如需 selector 元数据只走经评审的既有 descriptor/response 扩展机制。 | 不新增公开搜索 route 或请求 envelope。 |
| `static/src/js/preview.js` | 实现关键词 chip、结构化条件输入状态、可读 label 映射、条件分区和现有状态机衔接。 | 不在浏览器生成 domain/CQO、显示 field_path、合成 Count 或吞掉错误。 |
| `tests/` | 扩展现有 unit、Odoo ORM/集成和授权内置浏览器验证；确认测试发现与执行方式。 | 不以未导入/未发现的测试文件冒充通过证据。 |

本节不规定新增文件名、测试模块拆分、descriptor 具体路由或网络 payload 扩展形状；实施阶段必须继续保持既有 SearchRequest/response 和冻结接口兼容，如需额外接口评审须先更新本 CC。

### 16.1 迁移与兼容策略

- 不新增数据库表、配置字段或 Published Snapshot schema，不需要配置数据迁移。
- 既有 Raw Query、`conditions[]`、Refinement、Published Snapshot、SearchRequest/response 继续按当前契约消费。
- CC-016 的 UI 能力不得使未更新客户端或旧 Raw Query 失效；服务端仍接受既有合法请求。
- 不要求重新发布既有配置；只有配置本身因独立、获批的配置变更而修改时，才走 CC-010/既有正常 Publish 流程。CC-016 不通过 Publish 流程注入 UI 配置。

### 16.2 日志与可观测性

- 复用 CC-008 的 Odoo 日志事件、级别和字段 allowlist；本 CC 不新增成功/校验/失败日志事件、日志位置或字段。
- 不记录 Raw Query、token 值、完整条件、字段值、技术路径、SQL、Record Rule 或权限令牌；前端不增加输入内容日志。
- 如后续实现认为需要新增 `keyword_count`、`condition_count` 等字段或事件，必须先完成 CC-008 敏感数据白名单影响评审并获批；不得由 CC-016 默认授权。

## 17. Appendix

### 17.1 SRS / TDD 追溯矩阵

| 来源 | 相关契约 | CC-016 覆盖 |
|---|---|---|
| SRS_global_search v1.5 | FR-SW-001~003 | 在现有 Search Workspace 改善 Raw Query 条件编辑和结果理解。 |
| SRS_global_search v1.5 | FR-RF-001~009 | 保留 Resource/date/state Refinement、删除和状态分离。 |
| SRS_global_search v1.5 | FR-QU-001、BR-006~008 | 显示 Parsed、Refinement 和 Effective Conditions 的安全分区。 |
| TDD_global_search v0.4 | §3.4 | Raw Query、Parsed Conditions 和 Refinement 只经 Effective Conditions 汇合。 |
| TDD_global_search v0.4 | §6.5 | 未知条件、权限异常、配置错误和无效 label/path 按失败关闭。 |
| TDD_global_search v0.4 | §8、§10 | Workspace 负责交互；服务端负责 ORM、权限和条件执行。 |
| TDD_global_search v0.4 | §12.5 | 适用 UI 行为以授权内置浏览器进行人工 HVR。 |

### 17.2 与前置契约接口

| 输入/输出 | 既有契约 | CC-016 约束 |
|---|---|---|
| Raw Query | CC-002 / CC-005 / CC-015 | 保持原始文本；chips 仅编辑该文本；服务端 parser 产生关键词语义。 |
| Structured Conditions | CC-002 / CC-015 | 使用既有 `conditions[]` 的完整 dimension/operator/value，不新增 envelope。 |
| Refinement Conditions | CC-005 / CC-012 | 独立保持 Resource/date/state 状态和原优先级。 |
| Published field identity | CC-001 / CC-014-2 | 以完整已发布 `field_path` 为身份；UI label 不取代路径。 |
| Search Response | CC-002 / CC-005 / CC-015 | 沿用现有 status/results/counts/errors/meta/effective conditions/cursor。 |
| Permission | CC-003 | 由服务器当前用户环境重新授权；selector option 不作为访问令牌。 |

### 17.3 与 TD-002 的对应关系

| TD-002 建议 | CC-016 对应章节 |
|---|---|
| AND 关键词 chip，可编辑/删除 | §§4、6、11 |
| 字段选择器，标签映射到完整 Published `field_path` | §§5、8、10 |
| 条件按关键词/结构化/Refinement 分区 | §6 |
| 不改变 CC-015 语义 | §§3、7、9、12 |
| 按使用后用户反馈评估 | 本 CC 不新增部署计划；TD-002 的触发条件和评估时机保持原记录 |

### 17.4 术语

| 术语 | 定义 |
|---|---|
| Keyword chip | 对服务端已解析 Raw Query keyword term 的 UI 表示；不是独立搜索条件协议。 |
| Field selector label | 服务端由当前用户语言下 Odoo 字段描述生成的可读路径标签，不是 Published `field_path` 本身。 |
| Structured condition | 既有 `conditions[]` 中使用完整 Published dimension 的字段条件。 |
| Condition partition | 对关键词、结构化条件及 Refinement 来源的展示分组，不改变 Effective Conditions。 |

### 17.5 版本历史

| 版本 | 日期 | 变更 | 状态 |
|---|---|---|---|
| v0.1 | 2026-10-13 | 初始草案；记录现有契约/代码/UI/Published Snapshot 核对及字段标签来源决策 | DRAFT / NOT APPROVED |
| v0.2 | 2026-10-13 | 根据附件评审澄清版本基线、元数据标签来源、类型控件、分区示意、继承性能验证、HVR/浏览器、迁移与日志边界；用户批准冻结 | APPROVED / FROZEN |

### 17.6 评审记录

| 日期 | 来源/评审人 | 结论 | 处理状态 |
|---|---|---|---|
| 2026-10-13 | 用户提供的附件评审；附件未注明评审人 | 建议补充后进入 Freeze 流程 | 已采纳与既有冻结契约兼容的澄清；性能硬阈值、未经 CC-008 批准的日志字段及固定新增 fixture 目录未纳入 |
| 2026-10-13 14:38 +08:00 | 用户 | 批准冻结 CC-016 | v0.2 APPROVED / FROZEN；实施仍受 TD-002 / §13 前置条件约束 |
