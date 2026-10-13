# CC-015 — 多条件搜索（Multi-Condition Search）

## 0. 文档治理（Governance）

| 字段 | 内容 |
|---|---|
| 文档类型 | Coding Contract |
| 版本 | v0.4 |
| 状态 | AMENDED / APPROVED（多词 Contains 语义获用户批准） |
| Intent ID | CC-015 |
| 上游基线 | SRS_global_search v1.5 FROZEN；TDD_global_search v0.4 FROZEN；IMPLEMENTATION_PLAN_global_search v0.3 FROZEN |
| 前置契约 | CC-001 至 CC-014；CC-014-1；CC-014-2；TD-001 |
| 模块 | `wd_global_search` |
| 目标 | 在不改变冻结的外层 Search API、也不侵占 CC-002/003/005/007/012 职责的前提下，增加多条件查询归一化与执行 |
| 批准 / 冻结 | v0.3 冻结并于 2026-10-13 修订获用户批准（Asia/Shanghai） |

**版本基线与冻结边界：**

- 本 CC 以 SRS v1.5、TDD v0.4、IMPLEMENTATION_PLAN v0.3 为上游基线；CC-001 至 CC-014、CC-014-1、CC-014-2 和 TD-001 按其各自已批准版本保持冻结。
- 本 CC 只补充多条件搜索语义，不修改任何上述文档的已冻结接口、权限、错误、计数、分页或兼容行为。
- v0.3 的多词 Exact-only 决策现由用户批准修订为 Char/Text Contains-on-text；本 CC 的单 token 和结构化条件兼容边界保持不变。
- 如实现要求改变其他冻结语义，必须先完成影响评审并取得批准，再更新本 CC；不得以实现便利为由直接变更上游。

本契约冻结以下兼容边界：

1. 保留 CC-002 的 SearchRequest 和 Search API 形状。Condition Query Object（条件查询对象，CQO）只作为内部规范化结构，不新增外层 `condition_query` 请求字段。
2. 多词文本查询中，每个词在当前用户可读且 Published、searchable 的 Char/Text 字段中按 Contains 匹配；每个词至少命中一个字段，所有词都必须在同一候选记录上命中。非文本字段仍仅在允许 Exact 时按字段类型精确匹配。
3. Contains-on-text 仅改变新增多词 Raw Query 语义；单 token Raw Query 与结构化条件仍遵循 CC-002 和字段 Published `operator_set`。

本 CC v0.3 于 2026-10-13 经用户批准冻结；v0.4 仅按用户明确批准修订多词 Char/Text 匹配规则。其余停止条件和冻结边界继续有效。

## 1. 契约目标（Contract Goal）

**目标：** 将确定性多词文本输入和既有结构化条件归一化为统一的内部条件表示，并共用校验、权限、执行、Query Understanding 和 Count 路径，同时保留既有 SearchRequest、Resource、Refinement、分页及错误契约。

```text
既有 SearchRequest
  query ───────────────┐
  conditions[] ────────┴─> 确定性解析 / 结构化条件适配
                              │
                              ▼
                     内部 Condition Query Object
                              │
                 请求及 Published 配置校验
                              │
                 CC-003 当前用户权限边界
                              │
                 CC-002 Effective Conditions / 执行器
                              │
              已授权结果 + 精确的已授权 Count
                              │
              CC-014 卡片渲染 / CC-013 导航
                              │
               面向用户的 Query Understanding 摘要

refinement_conditions[]、resources[]、limit、offset、cursor
  仍分别由 CC-005 / CC-012 / CC-002 负责。
```

CQO 是内部条件表示，不是新的 HTTP/RPC 请求外壳、路由、权限上下文、ORM domain，也不替代 Effective Conditions。

## 2. 背景与验收发现（Background and Acceptance Findings）

### 2.1 核对方法

起草前只读核对了冻结的 CC-002、CC-003、CC-005、CC-012、CC-014-2、SRS v1.5、TDD v0.4、实施计划 v0.3、当前 Controller/Service 代码及现有测试。Published Configuration 仅通过 Odoo 授权界面查看（界面由 Odoo ORM 提供数据）；未直接读写数据库、未修改配置或业务数据、未通过 SQL 读取业务数据、未对业务记录使用 `sudo()`、未修改官方 Odoo 代码，也未修改任何冻结上游文档。核对结果仅代表当时可见证据，不替代实现前的权威配置确认。

### 2.2 既有契约与实现核对结果

| 范围 | 已核对基线 | 对 CC-015 的约束 |
|---|---|---|
| CC-002 SearchRequest | 内部 `SearchRequest` 包含 `raw_query`、`parsed_conditions`、`refinement_conditions`、`resource_scope`、`offset`、`limit` 和 `cursor`。现有 Controller 接收 `query`、`conditions`、`refinement_conditions`、`resources`、分页参数及 `cursor`。 | 保留外层结构。`query` 与 `conditions` 可以共存；不得新增 `condition_query` XOR 规则。 |
| CC-002 Search API / 响应 | 现有搜索路由为 `/wd_global_search/api/search`。响应包含 status、request ID、results、counts、errors、metadata、effective conditions 和 cursor 信息。 | 复用现有 API、响应与错误契约；不新增路由或响应状态。 |
| CC-002 Effective Conditions | TDD §3.3–3.4 规定不同维度 AND、同维度多值 OR、重复条件去重，以及既有 Refinement 冲突优先级。 | 新增的 token 级 AND 不得改写既有同维度 OR 或 Refinement 合并规则。 |
| CC-002 请求边界 | TD-001 将 Raw Query 限制为 500 字符；Parsed 与 Refinement 条件合计最多 20 个；嵌套深度最多 3；客户端 relation path 深度最多 2。 | 新限制只能收紧本次文本 token 语法，不得放宽 CC-002 的现有上限。 |
| CC-002 Count / 分页 / cursor | Count 不受当前页影响。Result Identity、稳定排序、分页和 cursor 绑定已由上游定义；cursor 与条件、配置及用户上下文关联。 | CQO 必须影响有效条件/cursor 身份，但不得改动 cursor 形状或 Count 职责。 |
| CC-002 / CC-005 / CC-012 性能 | CC-002 默认单资源/总请求超时为 3/5 秒，并要求记录 P50/P95/P99 基线；CC-005 §10.2 定义搜索、Refinement、Query Understanding 和列表渲染软预算；CC-012 §9 定义 Count 软预算。 | 复用既有预算和观测要求；本 CC 不另设按 token 数量递增的延迟目标。 |
| CC-003 权限边界 | 当前用户和公司上下文来自服务端环境；模型访问、Record Rule、字段权限、每一关系跳转、失败关闭及 Count 隐私均有约束。 | 条件不得提供或覆盖用户、公司、groups、domain、model 或权限上下文。 |
| CC-005 Query / Refinement | Raw Query 与 Refinement 分离；Refinement 可增删，不改写 Raw Query；Query Understanding 展示有效解释。 | 文本 token 属于 Parsed Query；Resource/date/state 控件仍走现有 Refinement。 |
| CC-012 Resource 语义 | `resources[]` 仍是 SearchRequest 的 Resource scope；Selector/facet Count 具有独立的 Published Resource 与权限语义。 | CQO 不得选择、扩大或重新解释 Resources/facet counts。 |
| CC-014-2 字段路径 | Searchable Field 路径按 Published Resource/model 和 Odoo ORM 元数据校验；路径形态、关系深度、末端类型及 `any/all` 均受该契约约束。 | 结构化字段必须使用完整配置的 `field_path`；客户端不能提交 relation path 或猜测 alias。 |
| SRS / TDD 条件规则 | SRS BR-010 和 TDD §3.3–3.4 规定不同维度 AND、同维度多值 OR。TDD §3.5 管理现有时间解释和服务端用户语言/时区。 | CC-015 只增加文本 token 之间的 AND，不重定义维度、日期/状态词典或 Refinement。 |
| 当前 Controller | `controllers/main.py` 将非空 `query` 转成现有 `name`/`ilike` 条件，并追加结构化 `conditions`。 | 多词行为必须通过明确的新解析分支实现；单词/旧路径必须有回归测试。 |
| 当前 merger / executor | `services/conditions.py` 去重条件，缺省 operator 当前为 `contains`。`services/executor.py` 按已配置维度分组，对路径条件采用 CC-014-2 `operator_set`，并按集合路径配置应用 `collection_match`。 | 不得静默改变旧 operator 缺省值。新 Contains token 条件必须能在内部表示中与旧条件区分。 |
| 当前 request boundary | `services/request_boundary.py` 执行 CC-002 的长度、条件数、嵌套和 2 段客户端路径限制。 | CQO 不得放宽客户端 relation-path 边界。 |
| 现有测试 | 相关测试覆盖 request boundary、service core、field path、configuration、permission boundary、index strategy、i18n/timezone、navigation 和 observability。 | 在既有单元/ORM/浏览器测试体系中增加场景，不取代上游回归测试。 |

### 2.3 Published Configuration 核验结果

2026-10-13 通过新打开的授权 Odoo UI 只读核验 `global_search_baseline` 的 Published version 5；版本状态为 Published，checksum 为 `4cd6cb4e0e59b2116bd7261bb8f9e8f504c1970e3bee90ea7b07dd510f00597b`。在同一版本记录中核验了 Sales Order 的 Search Fields 与 Relation Paths：

| Searchable Field | Purpose | Operator Set | Collection Match | Index Strategy | Searchable |
|---|---|---|---|---|---|
| `name` | Identifier | Exact | Any related record | B-tree | 是 |
| `client_order_ref` | Text | Prefix | Any related record | `text_pattern_ops` | 是 |
| `origin` | Text | Prefix | Any related record | `text_pattern_ops` | 是 |
| `partner_id.name` | Entity | Contains | Any related record | GIN `pg_trgm` | 是 |
| `order_line.product_id.product_tmpl_id.name` | Entity | Contains | Any related record | GIN `pg_trgm` | 是 |

| Relation Path | Max Depth |
|---|---:|
| `partner_id` | 1 |
| `order_line.product_id` | 2 |

此前一个共享浏览器快照显示了不同 checksum `418f5130172f5e4064c59f33c555bfaf4f0d6c03d8dee229d54e4f6a10bc870f`；本次新开授权页面重新读取同一 Published version 5 后得到 `4cd6…597b`，并在同一版本记录内读到上述字段和 Relation Paths。本 CC 以本次当前 UI 读取为本次实施基线，不将另一快照用作配置依据；若运行时 Published checksum 与此基线不同，实施须停止并重新核验。

当前 Sales Order 的 `name` 为 Exact/B-tree，客户和产品路径为 Contains/GIN trigram。多词自由文本会对上述已发布且获授权的 Char/Text 字段均执行 Contains；配置 operator 继续控制结构化条件。此处仅记录配置，不修改或发布配置。

### 2.4 实现缺口

1. 当前 Raw Query 路由执行单条 `name`/`ilike` 搜索，尚未把空格或 `+` 解析为合取 token。
2. 当前没有一个明确的内部 CQO，用于区分 query token 与字段条件，同时保持 SearchRequest 不变。
3. 当前 Searchable Field 身份是完整配置路径（例如 `partner_id.name`），不是 `partner_id` 或 `product_id` 这样的语义 alias。
4. 现有 `operator_set` 可能为 Exact、Prefix 或 Contains。新多词文本模式对已发布 Char/Text 字段统一执行 Contains；结构化条件仍遵循字段既有 `operator_set`。
5. 当前 Query Understanding 没有 token 级摘要约定。
6. §2.3 的当前 Published snapshot、Sales Order Search Fields 及 Relation Paths 已在同一授权 UI 版本记录中核验；运行时版本/checksum 不符时仍须停止。

### 2.5 既有契约支持

- CC-002 提供 SearchRequest、Effective Conditions、Count、分页、cursor、响应及错误边界。
- CC-003 提供当前用户权限契约。
- CC-005 提供 Raw Query/Refinement 分离及 Query Understanding。
- CC-012 提供 Resource 选择和 facet Count 语义。
- CC-014-2 提供有限字段路径校验及集合匹配语义。
- SRS BR-010/TDD §3.3–3.4 提供既有 AND/OR 规则；本 CC 保留它们，只对独立解析出的文本 token 增加 AND。

### 2.6 冻结文档保护与基线管理

本 CC 不修订 SRS、TDD、IMPLEMENTATION_PLAN 或任何既有 CC。§2.3 记录的是当前核验基线，不授权修改 Published 配置；如运行时版本/checksum 发生变化，或出现无法与冻结上游规则协调的行为，必须按 §19 停止并通过项目工作流升级。

## 3. 范围（Scope）

### 3.1 范围内

- §6–7 所定义的有界确定性多词文本解析器。
- 内部 CQO，用于归一化文本 token 与既有结构化字段条件。
- 共用结构校验、Published 字段解析、权限检查、执行、Count 和 Query Understanding 路径。
- 新多词文本语义对当前用户获准访问且 Published 的 Char/Text Searchable Fields 使用 Contains；非文本字段仅在配置允许 Exact 且 token 可按字段类型转换时参与精确匹配。
- 文本 token 之间 AND；不同结构化维度之间 AND；保留上游同维度 OR 和 `collection_match`。
- 对格式错误、未知字段或未授权的新多条件输入进行请求整体拒绝，不执行部分条件。
- 对既有 SearchRequest、Resource、Refinement、operator、Count、cursor、错误、Card 和导航行为提供可测回归要求。

### 3.2 范围外

- 用户可编写的 OR/NOT/括号/引号或任意布尔表达式。
- 自然语言解释、模糊匹配、拼写纠错、实体评分/消歧、LLM、向量搜索、Elasticsearch/OpenSearch 或外部搜索引擎。
- 任何 LLM adapter 或未来自然语言接口契约；需另行批准 CC。
- 新增 `/nl_search` 或其他路由、公开的顶层 `condition_query` 属性，或 `NOT_IMPLEMENTED` 等新响应状态。
- 日期/状态文本解析或词典变更；现有 CC-005/TDD 日期和状态 Refinement 契约继续有效。
- Resource Selector/facet 重设计（CC-012）、Refinement 行为（CC-005）、权限模型（CC-003）、错误协议（CC-007）、Card 渲染（CC-014/014-1）、导航（CC-013）或 Searchable Field 配置重设计（CC-014-2）。
- 任意字段 alias、客户端 Relation Path、ORM domain、表达式、model/action 名称或权限声明。
- 聚合计算、物理索引创建、数据库迁移或业务数据写入。

### 3.3 与 CC-002 / CC-005 / CC-012 的边界

CC-015 只负责新增文本 token 的归一化和内部 CQO。外层 SearchRequest、Raw Query/Refinement 分离与合并、Resource 选择、Count/facet、分页/cursor、响应、timeout 和错误状态，仍归既有契约负责。CC-015 不得重新解释空 `resources[]`、改写 Refinement 或替换 CC-002 的同维度 OR 规则。

## 4. 条件查询对象（Condition Query Object）

### 4.1 用途与边界

CQO 是服务器内部、进入现有搜索流程前使用的规范化条件输入。它不是新的公开请求 envelope，也不替代 `SearchRequest`、`EffectiveConditions` 或 Published Configuration snapshot。

### 4.2 逻辑结构

```text
ConditionQueryObject:
  combinator: AND
  keyword_terms: tuple[KeywordTerm, ...]
  field_conditions: tuple[FieldCondition, ...]
  source_metadata: 由服务端生成、仅供安全展示的来源信息

KeywordTerm:
  kind: keyword
  value: string
  source: raw_query

FieldCondition:
  kind: field
  dimension: 完整的 Published Searchable Field field_path
  value: 通过已配置末端类型校验的 JSON scalar
  operator: 既有 SearchRequest operator，或显式精确匹配 "="
  source: conditions
```

`source_metadata` 不得影响授权、search domain、Count、分页或配置选择。日志不得复制原始用户值。

每个 `KeywordTerm` 的展开规则见 §4.3：仅在当前 Resource/model 的 Published Searchable Fields 中，取 searchable 且当前用户可访问的字段。Char/Text 字段按 Contains 匹配；非文本字段仅在允许 Exact 时按类型精确匹配。字段展开是服务端内部匹配，不构成用户可选的 OR 条件。候选根记录须对每个 token 至少在一个合格字段上命中，所有 token 才满足文本查询。

### 4.3 文本 token 的含义

每个 `KeywordTerm` 在当前 Resource/model 下的合格 Published Searchable Fields 中展开。Char/Text 字段不论其结构化 `operator_set` 是 Exact、Prefix 还是 Contains，在多词 Raw Query 中均按字面子串 Contains 匹配；LIKE 元字符按普通文本处理。非文本字段仅在 `operator_set=exact` 且 token 可按末端类型转换时使用精确匹配。候选根记录只要在至少一个合格字段上匹配该 token，即满足该 token；只有所有 token 都在同一个候选根记录上匹配，该记录才满足文本查询。字段展开是服务端内部行为，不是用户可选择的 OR 表达式。

如果某 Resource/model 没有任何当前用户可用、且可参与 token 匹配的 Published Searchable Field，新多词模式必须通过 CC-002/CC-007 既有失败协议显式报告该 Resource 失败，不得静默返回成功的零 Count。

### 4.4 结构化条件的含义

外部 JSON 输入仍使用现有 `conditions[]` 列表。结构化 `dimension` 必须与当前用户可用的 Published Searchable Field `field_path` 完全一致。新精确结构化条件使用外部 operator `=`，且 Published 字段必须允许 Exact。旧有允许的 operator 仍按其 Published `operator_set` 和 CC-002 行为执行；归一化不得在 Exact/Contains/Prefix 之间静默转换。

本 CC 不接受 `{type: "entity", field: "partner_id", match: "exact"}` 来代替 `dimension="partner_id.name"`。CC-014-2 和目前核实到的 Published 配置均未确立这种 alias。

### 4.5 内部服务契约

既有外层 SearchRequest 仍承载传输、Resource 和分页参数。条件执行前，query 条件先归一化为一个 CQO；之后由 CC-002 既有 merger 合并适用的 Parsed 与 Refinement Conditions，生成 Effective Conditions。搜索执行只接收服务器验证过的维度和值，不接收客户端 domain 或 relation expression。

## 5. Search Request 外层参数（Search Request Outer Parameters）

### 5.1 既有外层结构

```json
{
  "query": "GS-CUSTOMER-001 GS-PRODUCT-005",
  "conditions": [
    {
      "dimension": "partner_id.name",
      "operator": "=",
      "value": "GS-CUSTOMER-001"
    }
  ],
  "refinement_conditions": [],
  "resources": ["sale_order"],
  "limit": 20,
  "offset": 0,
  "cursor": null
}
```

该示例只展示既有请求外壳；字段路径和 Resource 必须实际存在于 checksum 一致的 Published snapshot 中。`query` 与 `conditions` 按 CC-002 既有语义允许共存。不新增外层 `condition_query`，不增加新路由。

### 5.2 字段归属

| 请求数据 | 所属契约 | CC-015 规则 |
|---|---|---|
| `query` | CC-002 / CC-005 | 保留原始输入；新解析器只处理其定义的多词模式 |
| `conditions[]` | CC-002 | 沿用既有结构；dimension 必须解析到 Published 字段 |
| `refinement_conditions[]` | CC-005 | 原样交给既有合并协议 |
| `resources[]` | CC-012 | 原样传递；不得隐式扩展或改写选择 |
| `offset`、`limit`、`cursor` | CC-002 | 原样传递；绑定归一化后的有效条件身份 |
| user/company/groups/permissions | CC-003 | 只由服务器派生；不得接受客户端覆盖 |

### 5.3 禁止动态查询语言

请求不接受 ORM domain、SQL、`model`、`action`、任意 relation path、可执行表达式或调用方权限上下文。未支持的属性不能被默认为搜索条件。

## 6. 多条件语法（Multi-Condition Syntax）

### 6.1 语法

```ebnf
multi_query       := whitespace* token (separator token)+ whitespace*
separator         := whitespace+ | whitespace* "+" whitespace*
token             := 1..100 个 Unicode 字符；不得包含空白、"+"、控制字符、
                     引号或括号
```

- token 按 Unicode code point 计长，不按 UTF-8 字节数或用户感知的字素簇计数；只接受有效 Unicode scalar value。
- 不限制为 ASCII，也不对文本做大小写折叠或 Unicode 规范化；字母、组合标记、数字及其他普通可见字符可保留，精确比较遵循字段及 ORM 的 `=` 语义。
- 拒绝 Unicode 控制字符（Unicode `Cc`）、双向控制字符（包括 U+061C、U+200E–U+200F、U+202A–U+202E、U+2066–U+2069）、零宽字符 U+200B–U+200D、Word Joiner U+2060、BOM U+FEFF，以及无效 surrogate；空白、`+`、引号和括号继续按语法拒绝。
- Raw Query 继续遵守 CC-002 的 500 字符上限。
- 多词查询最多 10 个 token。
- `+` 和空白是分隔符，不是字面字符或转义语法。
- 连续多个空白仍属于 `whitespace+` 分隔符；本契约不新增“连续空格数量”限制。
- 每个 token 在 Char/Text 字段使用字面子串 Contains，大小写遵循 Odoo ORM `ilike` 语义；非文本字段在 `operator_set=exact` 时遵循 ORM `=` 语义。
- 重复/首尾 `+`、空 token、控制字符、引号、括号、独立的 `OR` 或独立的 `NOT` 均视为无效；不得静默丢弃或只执行部分条件。
- 不新增短语、分组、优先级、否定、通配符、函数、表达式或模糊语法。

### 6.2 单 token 兼容

没有多词分隔符的单 token 查询继续走 CC-002 既有 Raw Query 路径。只有合法的多词查询启用新的 Char/Text Contains token 行为。此约束保护旧单词搜索行为；如需改变，必须另行决策并完成回归影响评估。

### 6.3 字段展开与 AND

`A B+C` 规范化为三个 keyword term（`A`、`B`、`C`）。对每个 token，在合格字段中按 Contains（Char/Text）或类型化 Exact（非文本）匹配任一字段；token 组之间按 AND 组合。所有 token 必须在同一个候选 Resource/model/record 上匹配，不能把不同记录上的命中拼成一个结果。

解析器不推断某个 token 特指客户、产品、状态或日期。日期/状态筛选仍使用 CC-005 现有控件。

## 7. 文本入口——确定性解析器（Text Entry）

### 7.1 解析行为

解析器必须确定性且无副作用。它只接收有界 Raw Query 并产出 keyword terms；不读取业务记录、不检查未授权字段值、不解析实体、不选择 Resource，也不生成 ORM domain。

### 7.2 示例

| Raw Query | 结果 |
|---|---|
| `GS-CUSTOMER-001 GS-PRODUCT-005` | 生成两个 keyword term；两个词都必须在同一结果记录的合格字段中命中 |
| `Fremont+CA` | 两个 Contains token，按 AND 组合 |
| `SO-1001` | 单 token；使用 CC-002 既有路径 |
| `A++B` | 整个请求以 `INVALID_REQUEST` 拒绝 |
| `A OR B` | 拒绝；不支持 OR 连接词 |
| `"Acme Company"` | 拒绝；不推断带引号短语 |
| `A (B)` | 拒绝；不支持括号 |

### 7.3 失败行为

任何语法错误或超限输入都必须按 CC-002/CC-007 既有响应结构，以 `INVALID_REQUEST` 拒绝整个文本查询。不执行有效前缀或子集。既有 `message` 字段可使用服务端本地化的固定、可操作提示，指出语法错误、token 数量/长度超限或非法字符类别；不得包含 Raw Query、出错 token、用户输入片段或内部 relation path。错误类别只用于内部判定，不新增公开 subcode、字段或错误协议。

## 8. JSON 入口——结构化条件（JSON Entry）

### 8.1 既有 JSON 结构

JSON adapter 消费既有 `conditions[]` 对象（`dimension`、`operator`、`value`），并将其归一化为 CQO 的字段条件。不新增附件中的外部 `condition_query`、`type`、`field` 或 `match` envelope。

### 8.2 精确结构化条件示例

```json
{
  "conditions": [
    {
      "dimension": "partner_id.name",
      "operator": "=",
      "value": "GS-CUSTOMER-001"
    },
    {
      "dimension": "order_line.product_id.product_tmpl_id.name",
      "operator": "=",
      "value": "GS-PRODUCT-005"
    }
  ],
  "resources": ["sale_order"],
  "limit": 20,
  "offset": 0
}
```

只有当每个完整 dimension 都存在于适用的 Published Resource/model Searchable Fields 且当前用户权限检查通过时，请求才有效。上述路径只是示例，不代表当前 checksum 有争议的配置中确实存在这些字段。

### 8.3 Operator 兼容

- 新 CQO 精确字段条件使用 `operator="="`，并要求 Published 字段允许 Exact。
- 既有 Prefix/Contains 条件仍由其 Published `operator_set` 和 CC-002 行为约束。
- 客户端不能请求 Published 配置不允许的 operator。
- 同一请求混合新精确条件与旧 operator 条件时，必须在内部保留各条件来源/operator，再通过既有 Effective Conditions 契约组合。

## 9. 条件组合（Condition Combination）

### 9.1 规则

1. 有效多词文本查询中的每个 token 都必须命中；token 组之间为 AND。
2. 每个 token 可在服务器授权的字段集合中展开；这是服务器控制的字段匹配，不是用户编写的 OR 子句。
3. 不同结构化维度仍按 SRS BR-010 和 TDD §3.3 使用 AND。
4. 同一维度的多值仍按既有规则使用 OR。CC-015 不把状态/值集合改成 AND。
5. Many2many/One2many 路径继续使用 CC-014-2 中 Published 的 `collection_match=any/all`。
6. Parsed 与 Refinement Conditions 仍按 CC-002/CC-005 合并，包括既有 Refinement 优先级、去重和删除行为。
7. 每个已选 Resource/model 独立执行 token 和字段条件；不得跨不同根记录或 Resource 拼接 token 命中。各 Resource 的 `counts.by_resource` 分别对应本 Resource 的授权根记录集合；全局 Count 仍只按 CC-002/CC-012 既有规则汇总，不构成跨 Resource 匹配。
8. CC-015 请求中的无效/未授权条件不得静默丢弃；按既有请求、配置或权限错误协议拒绝，或失败对应 Resource。

### 9.2 查询路径等价

对受控 fixture，等价的多 token Raw Query 与结构化精确字段条件必须产生相同的已授权根 Result Identity 集合和 Count。fixture 必须能防止“不同记录分别命中不同 token”造成假等价。

## 10. Relation Path 推导（Relation Path Resolution）

- 结构化 `dimension` 必须与 Published Searchable Field 的完整 `field_path` 精确匹配；解析从 Resource 配置的根模型/model mapping 开始。
- 字段存在性、关系类型/深度、末端类型/存储属性和集合语义按 CC-014-2 及 Odoo ORM 元数据校验。
- 客户端提供的中间关系段不得未经验证直接交给 ORM。
- 每一关系跳转和末端字段均按 CC-003 在当前用户/公司上下文中授权。被阻挡的 hop 不能通过命中/不命中、Count、耗时或 Query Understanding 推断。
- 旧 Resource `Relation Paths` 配置不是 `partner_id`、`product_id` 等语义 alias 的自由映射表。如需未来 alias，必须另行明确定义 Published 模型并完成契约评审。
- 请求边界的 `relation_path`/`path` 限制仍为 2 段。CC-014-2 的配置字段路径深度不扩大客户端边界。
- 循环、未知字段、歧义映射、不可访问关系和无效末端字段均失败关闭。

## 11. Query Understanding

### 11.1 必须展示

Query Understanding 展示：

- 未改变的 Raw Query；
- 用户可见形式的解析 token；
- 可见的结构化条件及其有效 operator/value 摘要；
- 既有 Refinement Conditions、来源和最终有效合取关系；
- 多 token 查询的用户可见顶层 `AND`。

解析摘要仅在对应搜索请求完成后发布：搜索进行中不显示新请求的部分解析结果；成功或 EMPTY 时展示该请求的有效摘要；PARTIAL_SUCCESS 只展示已成功 Resource 的可见摘要并保留失败状态；请求整体失败或输入无效时不展示其未执行条件的摘要。Query 改变后，旧请求摘要不得冒充新请求结果。Raw Query 的呈现及 Workspace 状态仍遵守 CC-005。

### 11.2 禁止展示

不得暴露内部 relation path、不可访问的字段标签/值、隐藏 Resource 配置、model/record ID、内部配置 ID、SQL 或权限失败细节。仅在当前用户有权使用和查看字段时才显示字段标签。

### 11.3 响应兼容

使用现有 `effective_conditions` / metadata 响应结构。不得仅为 CQO 增加新的 response envelope。单 token 和仅 Refinement 请求仍遵循 CC-002/CC-005 的 Query Understanding 行为。

## 12. 权限边界（Permission Boundary）

- 搜索、Count、字段展开和关系遍历仅在当前用户的 Odoo 环境执行。
- 文本查询字段集合是 Published Searchable Fields、searchable 状态及当前用户模型/字段/关系授权的交集；Char/Text 字段采用 Contains，非文本字段仍须允许 Exact。
- 上述授权过滤须在字段展开和任何业务查询前完成，并在 Count 与 Query Understanding 生成前再次沿用同一有效字段集合；每个请求均按当前用户/公司上下文重新确定，不复用跨用户授权结果。
- 每条关联记录上的 Record Rule 和多公司域均须生效；关系命中不能让本身无权访问的根记录可见。
- Count 只统计已授权根记录，并使用与结果相同的谓词。
- 未授权字段不能通过条件摘要、结果差异、Count、错误、cursor 推断。
- 权限错误保留 CC-003/CC-007 的失败关闭语义。不新增用于业务数据的 `sudo()`、superuser、管理员环境、直接 SQL 或跨用户授权缓存。

## 13. Count 一致性（Count Consistency）

1. Count 和结果取回使用相同的归一化 token、字段条件、Refinement Conditions、选中 Resource scope、Published version 和当前用户权限上下文。
2. Count 在页切片前计算，不受 `offset`、`limit` 或当前页长度影响。
3. 结果 ID、每 Resource Count、总 Count 和 Query Understanding 对多 token 顶层 AND 的解释必须一致。
4. 集合语义按字段的 Published `collection_match`；匹配到多条关联行仍只计一个根结果。
5. Result Identity 去重及跨 Resource Count 沿用 CC-002/CC-012；CC-015 不改变 Resource facet counts。
6. 部分失败和未知 Count 保留 CC-007/CC-012 状态语义。失败 Resource 不得伪装成成功的零 Count。
7. Cursor 绑定归一化后的有效条件身份。query、conditions、Refinement、Resource 选择、用户上下文或 Published version 改变后，不得复用旧 cursor。

**继承的性能预算（软闸门）：**

| 场景 | 预算 | 来源 / 处理 |
|---|---:|---|
| 全局搜索响应 | P95 ≤ 2 秒 | CC-005 §10.2；多 token 不得放宽 |
| Refinement 响应 | P95 ≤ 1 秒 | CC-005 §10.2；既有 Refinement 行为不变 |
| Query Understanding 渲染 | P95 ≤ 500ms | CC-005 §10.2 |
| 结果列表渲染 | P95 ≤ 1 秒 | CC-005 §10.2 |
| 单 Resource Count | P95 ≤ 500ms | CC-012 §9 |
| Count 刷新 | P95 ≤ 1 秒 | CC-012 §9 |
| Count 与结果响应完成时间差 | ≤ 200ms | CC-012 §9 |
| 单 Resource / 总请求超时 | 3 秒 / 5 秒 | CC-002 §16.5；不得由客户端扩大 |

基线仍须按 CC-002 对单 Resource、多 Resource、20 并发记录 P50/P95/P99。任何超过软预算的观测须记录并评估，不得通过跳过授权检查解决；本 CC 不新增按 token 数量拆分的 P95 目标。

## 14. 错误处理（Error Handling）

| 失败情形 | 必须行为 |
|---|---|
| token 语法无效、Boolean 语法不支持、token/长度超限 | 通过 CC-002 既有响应结构整体返回 `INVALID_REQUEST` |
| 结构化 dimension 未发布或 operator 不支持 | 作为无效输入拒绝；不得猜测路径或回退到别的字段 |
| Published 路径/配置无效 | 按 CC-002/CC-007 返回 `CONFIGURATION_ERROR`；不得变成成功空结果 |
| 当前用户无权访问模型/字段/关系 | 按 CC-003 权限失败/字段过滤处理；不泄露记录、字段值或 Count |
| Resource timeout/失败 | 保留 CC-007 的 `PARTIAL_SUCCESS`/`FAILED`/`TIMEOUT` 语义及已知 Count 规则 |
| Cursor 不匹配 | 保留 CC-002 cursor 错误行为；不得静默换到另一查询重新执行 |

错误消息和日志不得包含 Raw Query、完整条件、业务值、SQL、Record Rule 内容、token 值或内部 relation 细节。不新增 `NOT_IMPLEMENTED` 响应。

## 15. 不变量（Invariants）

以下不变量已随 CC-015 v0.3 获批准冻结，并依 v0.4 的用户批准修订更新了 INV-029/030。第 1–3、24 项按保留 CC-002 的用户决定协调。

| ID | 不变量 |
|---|---|
| CC15-INV-001 | CQO 是 CC-015 query 条件的内部规范表示，不是新的外部 SearchRequest 字段。 |
| CC15-INV-002 | 确定性文本 adapter 将 token 输出为 CQO，且不改写 Raw Query。 |
| CC15-INV-003 | 结构化 JSON adapter 将既有 `conditions[]` 归一化为同一内部 CQO。 |
| CC15-INV-004 | V1 不存在 LLM adapter。任何未来 adapter 都必须另立并批准 CC；本契约不冻结 LLM 接口。 |
| CC15-INV-005 | CQO 条件必须经过同一请求校验、Published 配置解析、权限边界和执行器。 |
| CC15-INV-006 | 有效多词文本查询中的每个 token 都必须命中；token 组之间为 AND。 |
| CC15-INV-007 | 归一化对象的顶层 combinator 为 AND；文本匹配模式由服务端根据字段类型和 Raw Query 语义确定，不由客户端提供。 |
| CC15-INV-008 | 空白和 `+` 是唯一的多词文本分隔符。 |
| CC15-INV-009 | 不支持用户编写 OR、NOT、括号、引号或任意 Boolean expression。 |
| CC15-INV-010 | 结构化路径和文本字段展开仅由 Published 配置与 ORM 元数据确定。 |
| CC15-INV-011 | 每一关系跳转均按 CC-003 检查当前用户和公司上下文。 |
| CC15-INV-012 | Query Understanding 只展示用户可见且已授权的条件摘要。 |
| CC15-INV-013 | Count 与结果使用完全相同的有效谓词和授权候选集。 |
| CC15-INV-014 | CC-015 不绕过 Odoo access checks、Record Rules、公司规则或字段授权。 |
| CC15-INV-015 | 不得通过结果、Query Understanding、错误或 cursor 行为推断未授权记录、字段、关系或 Count。 |
| CC15-INV-016 | 解析失败时拒绝整个多词查询；不执行有效前缀或子集。 |
| CC15-INV-017 | Result Card 继续使用 CC-014/CC-014-1 渲染契约。 |
| CC15-INV-018 | 打开结果继续使用 CC-013 配置的导航 action。 |
| CC15-INV-019 | 多词查询最多包含 10 个 token。 |
| CC15-INV-020 | Raw Query 不超过 CC-002 的 500 字符；每个 token 不超过 100 字符。 |
| CC15-INV-021 | 当前用户语言/时区仍由服务器提供，只用于既有 CC-005/TDD 日期行为；CC-015 不发明日期 token 语义。 |
| CC15-INV-022 | 文本与结构化 adapter 在校验、权限和执行前汇入共同路径。 |
| CC15-INV-023 | 文本 adapter 负责解析 token；JSON adapter 验证结构化维度，不把其重新解释为 Raw Query。 |
| CC15-INV-024 | `query` 与 `conditions[]` 保留 CC-002 可共存语义；不规定 `query`/`condition_query` XOR。 |
| CC15-INV-025 | V1 不实现 LLM adapter、自然语言解析、向量搜索或外部搜索引擎。 |
| CC15-INV-026 | `resources[]`、`refinement_conditions[]`、分页和 cursor 保持既有 CC 职责与语义。 |
| CC15-INV-027 | 任何未来获批 adapter 只能补充 CQO，不能覆盖 Resource、Refinement、分页、cursor 或权限上下文。 |
| CC15-INV-028 | Query Understanding 不展示内部 relation path 或未授权字段名称。 |
| CC15-INV-029 | 新多词文本匹配只考虑当前用户可访问且 Published searchable 的字段；Char/Text 使用 Contains，非文本字段仅允许 Exact。 |
| CC15-INV-030 | 多词 Raw Query 的 Char/Text Contains 不改变单 token 或结构化条件的 CC-002 operator、CC-014-2 `operator_set`/`collection_match` 行为。 |
| CC15-INV-031 | 所有 token 必须命中同一个根 Result Identity；不得跨记录或 Resource 拼接命中。 |

## 16. 发布时校验（Publish-time Validation）

### 16.1 Published 配置检查

- 每个启用的 Resource/model 均有有效 Published Searchable Fields，且通过 CC-014-2 路径、类型、深度和末端字段校验。
- 每个 Resource/model 至少有一个可参与 token 匹配的 searchable Published Field。
- 所有已发布且授权的 Char/Text 字段均进入多词 Contains 字段集合；非文本字段仅允许 Exact，并按 ORM 字段类型精确匹配。
- 集合字段保留有效 `collection_match`，并符合 CC-014-2 路径形态。
- Relation Path 配置继续独立按既有契约校验，不重新解释成 alias 表。
- 消费 snapshot 前必须确认 Published version/checksum 一致。
- 无任何可参与 token 匹配的 Searchable Field 的 Resource 不得在新文本模式中静默作为成功空搜索参与。发布校验必须报告该 Resource 不支持此模式；运行时使用既有 `CONFIGURATION_ERROR`，不新增配置开关。

### 16.2 请求时检查

- Raw Query 类型、控制字符、总长度、分隔符语法、token 数量和 token 长度。
- 结构化条件对象形状、dimension、标量值类型、operator 和 Published 字段归属。
- Relation Path 推导、当前用户对各模型/字段/hop 的访问权，以及 Resource scope。
- Parsed/Refinement 合计数量和嵌套深度不超过 CC-002 限制。
- 无效 CQO 必须在任何业务查询或 Count 执行前失败关闭。

### 16.3 校验职责

发布时校验配置事实；请求时校验调用方输入和当前用户授权。任何一侧都不能接受客户端 ORM domain、客户端权限上下文或调用方指定的 relation expression。

## 17. 测试矩阵（Test Matrix）

下表每项均为可执行测试约定。测试使用隔离的 ORM fixture 和当前用户环境，不查询生产数据；浏览器验证使用既有 Workspace/API。

| 测试 ID | 准备 / 输入 | 必须断言 |
|---|---|---|
| CC15-TEST-001 | fixture 中一条记录在 Exact 配置的 Char 字段和 Contains 配置的 Text 字段分别包含两个词；提交 `A B` | 两个 token 均被归一化并按 Contains 匹配；只有同时满足两词的记录返回 |
| CC15-TEST-002 | 同一 fixture；分别提交 `A+B` 与 `A + B` | 两种写法产生相同 token 序列和结果 ID |
| CC15-TEST-003 | 提交两条含完整 Published dimension、`operator="="` 的既有 `conditions[]` | 两条均归一化为字段条件，不需要新增请求 envelope |
| CC15-TEST-004 | 提交单 token 查询 | CC-002 既有 Raw Query 行为和结果不变 |
| CC15-TEST-005 | 一条 fixture 记录的已发布文本字段分别包含 A、B；比较文本 `A B` 与使用相同字段、Contains operator 的等价 `conditions[]` | 两种入口产生相同的已授权 Result Identity 和 Count |
| CC15-TEST-006 | 单元测试构造合法及错误 CQO | 合法对象通过；类型错误、缺值、不支持的 combinator 及超限嵌套在执行前拒绝 |
| CC15-TEST-007 | 在有可读已配置字段的测试用户下归一化合法 CQO | 两种 adapter 使用同一权限服务提供的字段集合 |
| CC15-TEST-008 | 用受控 ORM fixture 将已验证 CQO 交给 executor | executor 直接使用归一化条件，不调用 parser |
| CC15-TEST-009 | 记录 1 同时命中 A/B，记录 2 只命中 A；提交 `A B` | 仅记录 1 返回；不同记录的命中不被拼接 |
| CC15-TEST-010 | 配置 dotted Searchable Field 并在 JSON 提交完整路径 | ORM 元数据按 Published 根模型/路径解析；不替换为 alias 或其他路径 |
| CC15-TEST-011 | 提交两个 token 和一个 Exact 结构化条件 | Query Understanding 显示词、条件和 AND 摘要，不泄露隐藏技术路径 |
| CC15-TEST-012 | 对相同多词请求比较 `search_count` 与分页结果 | Count 等于全部已授权根记录集合，且不受 page size 影响 |
| CC15-TEST-013 | 测试用户无权读取某个已配置末端字段 | 查询字段集合在匹配前排除该字段；结果/Count/摘要不泄露其存在性 |
| CC15-TEST-014 | 提交含有效前缀的错误文本，如 `A++B` | 整体返回 `INVALID_REQUEST`；不执行部分查询 |
| CC15-TEST-015 | 提交独立连接词 `A OR B` | 请求拒绝，不执行用户编写的 OR |
| CC15-TEST-016 | 提交独立连接词 `A NOT B` | 请求拒绝，不执行否定 |
| CC15-TEST-017 | 提交 `A (B)` | ORM 执行前拒绝 |
| CC15-TEST-018 | 提交 `"A B"` | 请求拒绝，不推断 quoted phrase |
| CC15-TEST-019 | 渲染受控多条件 fixture 的结果 | Result 使用现有 Published CC-014/CC-014-1 Card 和授权字段 |
| CC15-TEST-020 | 通过现有 Workspace action 打开匹配结果 | 使用 CC-013 配置的 Form Action，不接受 CQO 指定的导航目标 |
| CC15-TEST-021 | 更改 Resource 选择后重复查询 | `resources[]` 和 CC-012 Selector/facet-count 语义不变 |
| CC15-TEST-022 | 两名字段/记录权限不同的用户分别查询 | 各自只得到授权结果和 Count；不复用跨用户缓存 |
| CC15-TEST-023 | 强制一个 Resource 失败、另一个成功 | CC-007 状态/错误准确；失败 Resource 不伪装成成功零值 |
| CC15-TEST-024 | 通过既有 Search API 提交 query、conditions、resources、offset/limit、cursor | 既有请求/响应字段及类型兼容 |
| CC15-TEST-025 | 多 token Raw Query 与 Refinement 一起提交，再增删 Refinement | Raw Query 不变；Effective Conditions/结果遵守 CC-005 |
| CC15-TEST-026 | 在测试中启用请求/条件日志并搜索独特值 | 日志不包含 Raw Query、token 值、完整条件、SQL 或 relation path |
| CC15-TEST-027 | 分别提交 10 个和 11 个 token | 10 个通过；11 个作为整体拒绝 |
| CC15-TEST-028 | 分别提交 100 字符和 101 字符 token | 100 字符在其他条件有效时通过；101 字符拒绝 |
| CC15-TEST-029 | 多公司 fixture 及 Portal-like 受限用户执行查询 | 所有结果和 Count 遵守当前用户公司、ACL 和 Record Rules |
| CC15-TEST-030 | 两个 Resource 分别匹配不同记录 | 每 Resource/总 Count 对应各自授权根记录集合；不跨 Resource 拼接 token |
| CC15-TEST-031 | 配置一个可见字段和一个不可访问字段，并提交各自匹配值 | Query Understanding 只展示可见摘要；不命名或区分不可访问字段 |
| CC15-TEST-032 | 直接构造 CQO，在 parser 不可用时调用服务执行 | CQO 可独立执行，证明 executor 不依赖 parser |
| CC15-TEST-033 | 请求中附带 `uid`、`company_ids`、`groups` 或 permission 声明 | 服务端上下文保持权威；按 CC-003 忽略或拒绝，结果不改变 |
| CC15-TEST-034 | condition 对象中附带 client `model`、`action`、ORM `domain` 或 relation expression | 请求拒绝；这些值均不进入 ORM 执行 |
| CC15-TEST-035 | 同一请求同时提交 `query` 和 `conditions[]` | 保留 CC-002 共存语义，不引入 XOR 错误 |
| CC15-TEST-036 | 在变更前后对同一 fixture 提交空 query/空 conditions | CC-015 不新增必填错误；结果等于相同 Published 配置下所有已授权候选记录 |
| CC15-TEST-037 | 通过 `refinement_conditions[]` 提交日期筛选，并将 `this month` 单独作为 Raw token | Refinement 遵守 CC-005/TDD 日期语义；Raw token 不被静默转换成日期筛选 |
| CC15-TEST-038 | 提交 Published State Refinement，并将状态标签单独作为 Raw token | Refinement 遵守 Published State mapping；Raw token 不被静默转换为状态筛选 |
| CC15-TEST-039 | 先发布无效字段/operator/path 配置，再提交错误请求 | 发布拒绝无效配置；请求时错误与配置错误分离，不互相掩盖 |
| CC15-TEST-040 | 提交语法有效但未发布/有歧义的 dimension | 请求拒绝；不猜测、不部分执行、不泄露结果或 Count |
| CC15-TEST-041 | 在记录硬件、数据集、Resource 数及并发度的隔离环境中，分别执行 1/2/5/10 token、单/多 Resource 和 20 并发搜索；采集 P50/P95/P99 | 全局搜索、Query Understanding、Count 与渲染分别遵守 §13 继承的 CC-005/CC-012 软预算；单 Resource/总请求遵守 CC-002 超时；保留可复现的基线报告，不增加按 token 数量的新阈值 |
| CC15-TEST-042 | 分别提交中文/组合标记 token、Unicode 控制字符、双向控制字符、U+200B–U+200D、U+2060、U+FEFF 及无效 surrogate | 有效 Unicode 文本按 code point 规则进入 Contains 查询；禁止字符整体以 `INVALID_REQUEST` 拒绝，未执行查询且不回显输入 |
| CC15-TEST-043 | 对非法语法触发请求并检查响应与 observability 日志 | 响应保持既有 `INVALID_REQUEST` 结构，提示仅为安全固定类别文本；日志只含 CC-008 allowlist 字段，不包含 Raw Query、token 或完整条件 |

## 18. 回归要求（Regression Requirements）

- **CC-002：** 保留 SearchRequest 字段、路由、`resources[]`、Parsed/Refinement 合并、同维度 OR、不同维度 AND、Count、分页、cursor 和错误响应。
- **CC-003：** 保留当前用户/公司、模型/字段/关系授权、Record Rule 和失败关闭。
- **CC-005：** 保留 Raw Query 与 Refinement 分离、删除/重置行为、Query Understanding 及 Raw Query 展示；搜索/Refinement/Query Understanding/结果列表继续遵守 §13 引用的既有软性能预算。
- **CC-007：** 保留 `EMPTY`、`PARTIAL_SUCCESS`、`FAILED`、`TIMEOUT`、错误聚合和未知 Count 语义。
- **CC-008：** 保留日志字段 allowlist 和 audit 语义；不得增加 Raw Query 或业务值。
- **CC-009：** 保留服务端提供的 label、语言、时区及日期解释。
- **CC-012：** 保留 Resource Selector、多选、selection scope、精确结果 Count 和独立 facet-count 语义。
- **CC-013：** 保留 Result Card action 身份和 Native Form 导航。
- **CC-014 / CC-014-1：** 保留 Card template、关系字段显示、One2many 循环和渲染权限。
- **CC-014-2：** 保留完整 Searchable Field 路径语法、关系深度/类型限制、operator set、`collection_match` 和 Published 校验。
- **TD-001：** 保留 Raw Query 500 字符、条件总数 20、嵌套深度 3、请求 relation path 深度 2 及 invalid-request 处理。

## 19. 停止条件（Stop Conditions）

出现下列任一情况时停止实现并请求契约评审：

1. 无法识别 checksum 一致的 Published Configuration。
2. 无法通过授权 UI 核实当前 Published Resource/Searchable Field/Relation Path/operator 配置。
3. 文本 token 无法映射到确定、已发布且当前用户授权的可参与字段集合。
4. Resource 没有可参与 token 匹配的 Searchable Field，且没有获批的多词模式行为。
5. 结构化字段使用 `partner_id` 等语义 alias，且无法映射到唯一完整 Published `field_path`。
6. 无法从 ORM 元数据和 Published 配置确定 relation path、关系类型、末端类型或深度。
7. CC-003 无法校验任一关系 hop 或末端字段。
8. token AND 语义需要改变 SRS BR-010/TDD 同维度 OR 或 CC-002/CC-005 合并协议。
9. 多词 Raw Query 之外的路径需要改变旧 Prefix/Contains 条件或当前单 token Raw Query。
10. 无法证明 Count 使用同一有效谓词和授权结果集。
11. 多词匹配可能跨根记录、Resource、公司或用户拼接。
12. parser 需要使用 CC-005/TDD 所属的日期/状态语义，或需要未经批准的词典/配置。
13. 需要修改冻结 SRS、TDD、实施计划、CC、路由或响应结构，但尚无批准的影响评审。
14. 实现需要 `sudo()`、superuser/admin 业务环境、直接数据库读写或修改官方 Odoo 代码。
15. 实现需要 LLM、向量搜索、Elasticsearch/OpenSearch、外部搜索、`/nl_search` 或 `NOT_IMPLEMENTED`。
16. 错误输入或不可访问配置必须被静默丢弃、猜测，或伪装成成功空结果才能运行。

## 20. 完成定义（Definition of Done）

只有全部适用证据完成后，CC-015 才可关闭：

- 内部 CQO 与 adapter 边界有文档和测试，外部 SearchRequest 未改变。
- 多词语法、限制、授权文本字段 Contains 展开、token AND 和错误拒绝已实现。
- 结构化 JSON 条件使用完整 Published 字段路径，并保留既有 operator 兼容。
- 同维度 OR、不同维度 AND、Refinement 优先级及 `collection_match` 均正确。
- Relation Path 校验、当前用户字段/hop 授权、多公司过滤和失败关闭测试通过。
- Query Understanding 展示已授权有效摘要，不泄露内部路径。
- Count 在权限、Resource scope、Result Identity 和分页下与有效谓词一致。
- 从一个 UI checksum 一致的 snapshot 核验 Published version/operator 配置。
- CC15-TEST-001 至 CC15-TEST-043 及适用的既有回归套件通过并记录证据。
- CC-002/003/005/007/008/009/012/013/014/014-1/014-2 与 TD-001 回归要求通过。
- IHR、ATR 及所需 HVR 证据完成；人工搜索验证使用经过授权的用户账号。
- 未引入被禁止依赖、路由、权限绕过、官方 Odoo 修改或数据库捷径。
- 本 CC v0.3 于 2026-10-13 经用户批准冻结，v0.4 多词 Contains 修订亦于同日获用户批准；批准只建立契约基线，不代表实现、ATR、HVR 或 Coding Closure 已完成。

## 21. 决策（Decisions）

除经修订的决策外，以下决策随本 CC v0.3 获用户批准并冻结；实施不得擅自改变。

| Decision ID | 冻结决策 | 理由 / 状态 |
|---|---|---|
| CC15-DEC-001 | CQO 仅供内部使用，保留 CC-002 外层 SearchRequest 和路由。 | 避免静默改变冻结 API。 |
| CC15-DEC-002 | 多词文本输入在每个 token 的已发布且授权的 Char/Text 字段中按 Contains 匹配；非文本 Exact 字段类型化精确匹配；token 组做 AND。 | 用户于 2026-10-13 批准修订，以支持订单号与明细产品等跨字段搜索；不猜测语义 alias。 |
| CC15-DEC-003 | Contains-on-text 仅用于新增多词 Raw Query；旧单 token 和结构化 Prefix/Contains 行为保留。 | 用户于 2026-10-13 批准修订；兼容既有 operator 和客户端。 |
| CC15-DEC-004 | 文本和结构化 adapter 在共同校验、权限及执行前汇入同一 CQO。 | 防止重复实现安全和执行逻辑。 |
| CC15-DEC-005 | executor 不解析用户语法，只消费已验证的归一化条件。 | 隔离不可信输入，维持执行边界稳定。 |
| CC15-DEC-006 | CQO 表示 query 条件；Effective Conditions 仍由 CC-002 merger 负责。 | 保留 CC-002/CC-005 合并语义。 |
| CC15-DEC-007 | 不含多词分隔符的单 token 继续走现有 Raw Query 路径。 | 冻结兼容措施，防止单词查询语义整体变化。 |
| CC15-DEC-008 | 空白和 `+` 分隔多词；空项或不支持的语法整体拒绝。 | 语法确定且不静默执行部分条件。 |
| CC15-DEC-009 | 不支持 OR/NOT/括号/引号和自由 Boolean 语法。 | 限定语法，避免歧义解释。 |
| CC15-DEC-010 | 结构化条件使用完整 Published `field_path`，不使用短 alias。 | CC-014-2 以完整路径标识字段；尚无获批 alias 映射。 |
| CC15-DEC-011 | 新精确结构化条件以 `operator="="` 表示，且字段配置必须允许 Exact。 | 精确语义不能绕过配置或改写旧行为。 |
| CC15-DEC-012 | 保留既有同维度 OR 和不同维度 AND。 | 遵循 SRS BR-010 与 TDD §3.3–3.4。 |
| CC15-DEC-013 | 集合路径继续由 `collection_match=any/all` 决定。 | 遵循 CC-014-2；不让客户端控制集合策略。 |
| CC15-DEC-014 | CC-015 不解析日期/状态 token；既有 Refinement 继续由 CC-005/TDD 处理。 | 明确职责边界，避免重复词典。 |
| CC15-DEC-015 | 每个请求的权限和字段资格由当前用户及 Published 配置决定。 | 遵循 CC-003；不使用跨用户授权缓存。 |
| CC15-DEC-016 | Query Understanding 展示可见条件及 AND，但隐藏内部路径和不可访问字段。 | 提供可理解性且不泄露配置/权限信息。 |
| CC15-DEC-017 | Count 与结果使用相同条件、权限、Resource scope 和 Result Identity。 | 防止 Count/结果不一致及分页泄漏。 |
| CC15-DEC-018 | Card 与导航继续归 CC-014/014-1、CC-013 负责。 | 避免职责重复。 |
| CC15-DEC-019 | Raw Query 500 字符、CQO 最多 10 个 token、每个 token 最多 100 字符。 | 限制输入规模；CC-002 总条件数和嵌套限制继续生效。 |
| CC15-DEC-020 | 复用 CC-002/CC-007 错误码和响应结构。 | 不增加 API/error 协议；不引入 `NOT_IMPLEMENTED`。 |
| CC15-DEC-021 | 本 CC 不定义 LLM adapter 或未来 adapter 接口。 | V1 仅使用确定性逻辑；未来适配需另行批准范围。 |
| CC15-DEC-022 | 性能预算沿用 CC-002、CC-005、CC-012；不因 token 数量新增或放宽阈值。 | 避免与既有搜索、Count 和 UI 预算冲突；新增目标须经基线测量和正式影响评审。 |
| CC15-DEC-023 | token 允许 Unicode 普通文本，但拒绝控制/双向/指定零宽格式字符；不做 ASCII 白名单或隐式 Unicode 规范化。 | 支持国际文本并防止不可见控制字符改变语法或显示含义；明确按 code point 计数。 |
| CC15-DEC-024 | 不对既有 Published Snapshot 或业务数据做迁移；如需配置变更，仅通过既有正常 Publish 流程。 | CC-015 是运行时条件语义，不要求数据库/schema 迁移，保留旧配置可消费性。 |
| CC15-DEC-025 | 多条件诊断复用 CC-008 与现有 observability allowlist；不新增 token/condition 原文或未经批准的日志字段。 | 当前实现的日志字段采用严格 allowlist；新增字段须先做 CC-008 影响评审。 |
| CC15-DEC-026 | 测试 fixture 位置和模块拆分由现有测试结构及批准 IHR 决定。 | 本契约冻结测试覆盖和隔离原则，不提前固定目录或实现文件结构。 |

## 22. 实施结构（Implementation Structure）

以下是现有实现触点，不是必须新增文件的清单。具体方法边界应在本 CC 冻结后的批准实施计划/IHR 中确定。

| 现有位置 | 本契约下可能承担的职责 |
|---|---|
| `controllers/main.py` | 适配现有 `query` 和 `conditions[]`；保留路由和响应结构 |
| `services/types.py` | 如确有需要，表示内部 CQO |
| `services/conditions.py` | 归一化/去重，但不改变 CC-002 合并规则 |
| `services/request_boundary.py` | 校验多词语法及 CQO 限制 |
| `services/facade.py` | 将归一化与 Published snapshot、可见条件摘要、cursor 身份及现有服务流程集成 |
| `services/field_path.py` | 复用 CC-014-2 路径/operator 校验 |
| `services/permission_boundary.py` | 复用当前用户模型/字段/关系授权 |
| `services/executor.py` | 对已授权根查询应用 token 组和结构化条件 |
| `services/aggregator.py` | 保留精确 Count、Result Identity 和部分失败语义 |
| `static/src/js/preview.js` | 如需 UI 修改，在此显示授权后的 Query Understanding 摘要 |
| `tests/test_request_boundary.py`、`test_service_core.py`、`test_field_path.py`、`test_permission_boundary.py`、`test_configuration.py`、`test_i18n_timezone.py` | 扩展语法、字段资格、权限、路径、Count 及回归测试 |

本 CC 不要求新增 `services/query_object.py`、`services/parser.py`、配置模型、路由或外部 adapter。若实施证据证明需要新模块/Schema，应先按 §19 停止并完成影响评审，批准后更新实施结构。

## 23. 附录（Appendix）

### 23.1 SRS / TDD 追溯矩阵

| 来源 | 相关契约 | CC-015 处理方式 |
|---|---|---|
| SRS BR-006 | Raw Query 与 Refinement 分离 | 保留；CQO 不改写 Raw Query |
| SRS BR-007 | Effective Conditions 与冲突消解 | 复用既有合并、去重和 Refinement 优先级 |
| SRS BR-008 | 等价入口产生等价 Effective Conditions/结果 | 测试受控文本/结构化入口等价性 |
| SRS BR-010 | 不同维度 AND；同维度多值 OR；不支持任意 Boolean | 保留；仅增加 token 级 AND |
| SRS FR-QU-001 | 显示当前 Effective Conditions | 增加可见解析词摘要；不暴露隐藏路径 |
| SRS BR-012 | Published/configured relation path 将命中映射回根 Resource | 复用已授权根身份；不接受任意客户端路径 |
| TDD §2.2–2.3 | 请求生命周期、条件模型、当前用户执行 | 保留现有服务生命周期 |
| TDD §3.3–3.4 | Effective Conditions 及 Parsed/Refinement 合并 | 合并行为的权威来源 |
| TDD §3.5 | 时间及时区语义 | 不新增日期 parser；只复用既有 Refinement 路径 |
| TDD §3.6、§3.10 | Result Identity、Count、分页、cursor | 保留并绑定归一化条件身份 |
| TDD §4.3 | Searchable Field purpose/operator/path/index | 多词 Char/Text 字段集由 Published searchable 配置与当前用户授权决定 |
| TDD §4.5 | State 与 Vocabulary | 不新增 Raw Query 状态词典 |
| TDD §6 | 当前用户、字段、关系跳转、失败关闭 | 强制权限边界 |
| TDD §10.1–10.2 | 内部 Search API 与前端边界 | 复用既有逻辑接口 |
| TDD §12.1–12.5 | 单元、ORM、性能、权限、浏览器测试 | 按 §17 覆盖 |

### 23.2 接口契约摘要

```text
外部 SearchRequest：保持 CC-002 既有结构
  query
  conditions[{dimension, operator, value}]
  refinement_conditions
  resources
  offset / limit / cursor

内部 CQO：
  多 token 子句 combinator = AND
  keyword_terms = 对已授权 Published Char/Text 字段逐词 Contains 匹配；非文本 Exact 字段类型化匹配
  field_conditions = 既有完整路径结构化条件

Effective Conditions：
  由 CC-002/CC-005 既有合并生成
  不同维度 AND
  同维度多值 OR
  集合策略来自 CC-014-2 collection_match

SearchResponse：
  保持 CC-002/CC-007 既有响应结构和错误语义
```

### 23.3 术语表

| 术语 | 定义 |
|---|---|
| Raw Query | 用户输入的原始文本，按 CC-002/CC-005 保留 |
| Keyword Term | 有界多词文本语法产生的单个 token |
| Condition Query Object | 进入既有 Effective Conditions 执行前使用的内部规范化表示 |
| Searchable Field | Published Resource/model 的字段配置，包含完整路径和 operator set |
| 可参与多词文本字段 | 当前用户获准访问且 Published searchable 的 Char/Text 字段；Char/Text 按 Contains，非文本字段须允许 Exact |
| Effective Conditions | CC-002 规范化合并 Parsed 与 Refinement 条件后的结果 |
| Relation Path | 既有 Published 关联路径配置，不是客户端提交的字段 alias |
| Collection Match | CC-014-2 为配置的 Many2many/One2many Searchable Field 定义的 `any`/`all` 策略 |

### 23.4 版本历史

| 版本 | 日期 | 变更 | 状态 |
|---|---|---|---|
| v0.1 | 2026-10-12 | 核对 CC-002/003/005/012/014-2 与实现后形成初稿；记录 API、字段绑定和 operator 兼容决策 | Superseded |
| v0.2 | 2026-10-12 | 依据附件评审补充版本基线、只读范围、证据缺口跟进、Unicode/error/权限/展示时机、继承性能预算、迁移/日志/fixture/验收/HVR/浏览器与评审记录 | Superseded |
| v0.3 | 2026-10-13 | 写入当前授权 Odoo UI 核验的 Published v5/checksum、Sales Order Search Fields 与 Relation Paths；按用户批准冻结 | Superseded |
| v0.4 | 2026-10-13 | 按用户批准将多词 Char/Text 匹配改为 Contains-on-text；token AND 与单 token/结构化条件兼容边界不变 | AMENDED / APPROVED |

### 23.5 迁移与兼容验收

- 不改写、不自动迁移既有 Published Snapshot、Searchable Field 配置或业务记录；不存在 CC-015 专属数据库/schema migration。
- 单 token Raw Query 继续走 CC-002 既有路径；结构化条件仍按 Published `operator_set` 执行。
- 多 token 查询在当前 Published 且经当前用户授权的 searchable Char/Text 字段上使用 Contains；非文本 Exact 字段仍类型化精确匹配。Resource 缺少合格字段时按既有配置错误处理，不伪装为空结果。
- 如管理员确需改变 Published Searchable Fields，只能使用现有 Stage/Validate/Publish 工作流，并记录新的 Published version/checksum；不得由 Workspace 或本 CC 自动发布。

### 23.6 日志与错误消息验收

- 日志复用 CC-008 与现有 `services/observability.py` allowlist，例如 `request_id`、`config_version`、`resource`、`latency_ms`、`status`、`error_code`、`boundary` 和已批准的哈希字段；不得直接记录 Raw Query、token、完整条件、业务字段值、SQL、Record Rule 或权限令牌。
- `token_count`、`condition_count` 等当前 allowlist 未批准字段不得直接写日志；如有观测需要，先完成 CC-008 影响评审。
- 面向用户的输入错误沿用 `INVALID_REQUEST` 和现有响应形状；消息可指出安全的错误类别并提供修正方向，但不得回显输入或内部路径。不新增公开错误 subcode。
- 日志级别、调用点和额外指标由既有 observability 实现及后续批准 IHR 决定，不在此冻结新文件位置。

### 23.7 测试 Fixture 约定

- 复用仓库现有 Odoo ORM 测试 fixture/`TransactionCase` 模式；不要求新增固定目录。
- 通过唯一、非业务敏感的标记构造可控根记录，确保“同一记录命中所有 token”与“不同记录分别命中不同 token”两种情况可区分。
- 覆盖 Exact 与 Prefix/Contains 字段、1/2/5/10 token、token 长度 1/100/101、单/多 Resource（仅在 Published 配置已核实后）、有权/无权字段及多公司用户。
- Fixture 仅在隔离测试事务中创建并由测试框架回滚；不得使用生产数据或直接数据库写入。

### 23.8 验收场景与 HVR

**功能验收场景：**

1. 输入 2 个和 10 个 token，验证仅返回同一记录满足全部 token 的授权结果。
2. 输入 11 个 token，整体拒绝。
3. 输入不支持的 OR、引号、括号或连续 `+`，整体拒绝且不执行部分条件。
4. 单 token 查询继续使用旧行为；Prefix/Contains 结构化条件不变，多词 Char/Text token 使用 Contains。
5. 文本入口与等价 `conditions[]` 入口在受控 fixture 上得到相同 Result Identity/Count。
6. Query Understanding 仅在对应请求完成后显示授权摘要；错误/部分成功按 §11.1 处理。
7. Count 与已授权结果一致，Resource 间不拼接命中。
8. 无效 dimension、不可访问字段和权限变化均失败关闭，不泄露字段/记录/Count。
9. 输入长度、token 数、Unicode 字符政策和安全错误提示按 §6–7 执行。
10. CC-002/005/007/012 的 SearchRequest、Refinement、分页、cursor、部分失败和 Count 回归通过。

**HVR 场景：**

1. 人工输入 2 个 token，确认 AND 结果及同一记录命中规则。
2. 人工输入 10 个 token，再输入 11 个 token，确认边界和错误状态。
3. 人工输入 `OR`、引号、括号、连续 `+`，确认请求整体拒绝。
4. 人工验证单 token 和既有 Prefix/Contains 结构化条件无回归，并确认多词文本可跨 Char/Text 字段使用 Contains。
5. 人工验证查询完成后的 Query Understanding 摘要及 in-flight/失败状态。
6. 人工验证结果 Count、各 Resource Count、分页总数的一致性。
7. 以不同权限用户验证字段展开、结果及 Count 隔离。
8. 人工核验 `INVALID_REQUEST` 消息安全且可操作，不包含原始输入。
9. 人工验证 Resource 失败时保留 CC-007 状态，不显示伪造的零 Count。
10. 记录回归、控制台错误、请求响应与授权 UI 上 Published version/checksum。

**浏览器矩阵：** 继承 CC-005 §10.3 的首轮 HVR 矩阵；记录实际浏览器版本及各视口结果。此矩阵只验证 CC-015 相关搜索交互和状态展示，不改变 CC-005 响应式布局契约。

| 浏览器 | 版本 | 桌面 | 平板 | 窄屏 |
|---|---|---|---|---|
| Chrome | 最新稳定版 | 必测 | 必测 | 必测 |
| Firefox | 最新稳定版 | 必测 | 必测 | 必测 |
| Safari | 最新稳定版 | 必测 | 必测 | 必测 |
| Edge | 最新稳定版 | 必测 | 必测 | 必测 |

### 23.9 性能验收与评审记录

性能测试按 §13 的继承阈值执行，并记录受测环境、数据规模、Resource 数量、并发度及 P50/P95/P99。附件评审提出的“单 token 500ms、2–5 token 1 秒、6–10 token 2 秒、Count 1 秒”等新增分档目标未在 CC-002/005/012 中形成一致基线；本版本不将其设为规范阈值。若后续基线支持新增目标，须经测量和批准后增加版本决策。

| 评审记录 | 处理 |
|---|---|
| 2026-10-12 附件评审（评审人未注明） | 已采纳与冻结契约兼容的明确性和验收补充；对重复空格、公开错误 subcode、跨 Resource Count 禁止合并及新增分档性能阈值等冲突建议作兼容性修订。 |
| 2026-10-13 当前授权 Odoo UI 核验 | 新开 UI 页面读取 `global_search_baseline` Published v5/checksum `4cd6…597b`，并核验 Sales Order 全部 Search Fields 与 Relation Paths；据此更新 v0.3 并冻结。 |
