# CC-014-2 — Searchable Field Multi-Level Resolution

## 0. Governance

| 项 | 内容 |
|---|---|
| Coding Contract | CC-014-2 |
| 版本 | v0.2 |
| 状态 | FROZEN；用户批准冻结并进入实施 |
| Intent ID | `GS-SEARCH-SEARCHABLE-FIELD-MULTI-LEVEL` |
| 上游 SRS | [SRS_global_search](../../requirement/SRS_global_search.md) v1.5 FROZEN |
| 上游 TDD | [TDD_global_search](../../design/TDD_global_search.md) v0.4 FROZEN |
| 实施计划 | [IMPLEMENTATION_PLAN_global_search](../../implementation/IMPLEMENTATION_PLAN_global_search.md) v0.3 FROZEN |
| 前置 CC | CC-001 ~ CC-014；CC-014-1；TD-001 |
| 相关冻结契约 | CC-002、CC-003、CC-006、CC-012、CC-013、CC-014、CC-014-1 |
| 模块 | `wd_global_search` |
| DDD | N/A；项目没有冻结 DDD，本契约不虚构聚合、实体、值对象或领域不变量 |
| 目标 | 让 Published Searchable Field 支持有限、可验证、受当前用户权限约束的多级关系路径搜索 |
| 批准冻结 | 用户批准；2026-10-12 15:49 +08:00 |

本契约是 CC-014 的 Searchable Field 搜索扩展，不修改 SRS、TDD、实施计划或既有冻结
CC。用户已批准 CC-014-2 冻结并进入实施；实施必须遵守本文范围、Stop Conditions 和
Definition of Done。

### 0.1 版本基线

- 本草案以 SRS v1.5、TDD v0.4 和 Implementation Plan v0.3 为规范基线。
- CC-014 与 CC-014-1 已冻结；本契约只扩展 Searchable Field 搜索，不改写 Card 或既有
  权限、Resource、Search API 语义。
- 如评审要求修改 CC-014、CC-014-1 或其他冻结契约，必须先完成正式影响评审并取得批准；
  不得仅改写版本号或在本契约中覆盖其冻结要求。

## 1. Contract Goal

CC-014 支持单级搜索字段；CC-014-1 支持 Result Card 字段多级解析；CC-014-2 支持
Published Searchable Field 的有限多级搜索。

```text
Published Configuration
  Business Resource: Sales Order
  Searchable Fields:
    - name
    - partner_id.city
    - partner_id.country_id.name
    - order_line.product_id.name
        │
        ▼
从 Odoo ORM 元数据验证 field_path 并推导 relation path
        │
        ▼
SearchRequest.conditions[].dimension 命中已发布的 Searchable Field
        │
        ▼
Search Service 按当前用户 ACL、字段权限、Record Rule 与公司范围执行
        │
        ├── Search Results
        ├── 与同一授权查询条件一致的 Count
        └── 可见且安全的 Query Understanding
                │
                ▼
        CC-014-1 Result Card 渲染
                │
                ▼
        CC-013 Native Form 导航到根 Resource 记录
```

字段路径是配置期定义的搜索维度，不是客户端提供的可执行 domain，也不改变
SearchRequest、`resources[]`、Search API 路由或返回的 Resource 身份。

## 2. Background and Acceptance Findings

### 2.1 起草前核对方法

起草前核对了下列冻结契约、服务代码、配置模型、测试和 Published Configuration：

核对范围仅限只读文档、源代码、测试及当前已认证 Odoo 会话中的 ORM metadata/configuration
查询；未使用 SQL 或直接读写数据库，未修改配置、业务记录、官方代码或既有冻结文档。

| 核对项 | 核对位置 / 方法 | 结论摘要 |
|---|---|---|
| CC-014 §4、§8、Invariants | [CC-014](./CC-014_result_card_template_designer.md) | Card 模板路径、生产搜索路径职责分离；当前用户权限及纯文本安全边界必须保留 |
| CC-014-1 §4–§7 | [CC-014-1](./CC-014-1_relation_field_multi_level.md) | Card 的 M2O/M2M 路径和 O2M 循环已有单独契约；不能将其解析器或深度限制混同为 Search 解析器 |
| CC-002 SearchRequest、Search API、资源语义 | [CC-002](./CC-002_global_search_service_core.md)、TDD §3/§4/§16 | SearchRequest 字段、Published 快照、条件合并、Search/Count/分页/cursor 契约已有定义 |
| CC-003 权限边界 | [CC-003](./CC-003_global_search_permission_boundary.md) | 当前用户、模型、字段、Record Rule、公司范围、Relation Path 和失败关闭均为硬边界 |
| CC-006 索引策略 | [CC-006](./CC-006_global_search_index_performance.md)、TDD §8/§11.4 | Exact、Prefix、Selective Contains 的索引策略及性能证据已有基线 |
| CC-012 Resource 及 Count | [CC-012](./CC-012_global_search_dynamic_resource_selector_counts.md) | 稳定 Resource key、多选、授权 Facet Count 与 `resources[]` 结果范围不能改变 |
| 代码结构 | `mymodules/wd_global_search/services/`、`models/configuration.py`、`controllers/main.py`、`tests/` | 当前执行器只直接搜索 Searchable Field；显式 Relation Path 另行配置 |
| 当前 Published Searchable Fields / Relation Paths | 通过已认证 Odoo 页面使用 ORM `fields_get`、`search_read` 只读核对；未直接读写数据库 | `global_search_baseline` Published Version 5 有 7 个活动 Resource；Searchable Field 全为单级字段，关系搜索另有 7 条 Relation Path |
| 当前索引配置 | Published Version 5 的 Searchable Field `operator_set` / `index_strategy` | Exact/B-tree、Prefix/pattern_ops、Contains/GIN trigram；当前配置未证明数据库中对应物理索引已存在 |
| 当前性能配置 | Published Version 5 的 `performance_ids` 只读核对；模型和服务代码 | 该版本没有 Resource Performance Config；配置模型默认 `max_relation_depth=2`；当前服务没有消费 Published Performance Config 的证据 |

核对过程未修改配置、业务数据或既有文档。

代码结构核对明细：

| 文件/组件 | 核对内容 | 现状 |
|---|---|---|
| `services/executor.py` | Resource 搜索、domain、Count 和结果 | 直接字段及既有 Relation Path；未编译显式 Searchable Field 多级维度 |
| `services/conditions.py` | Parsed/Refinement 合并 | 按现有 Effective Conditions 去重；没有集合 ANY/ALL 逻辑 |
| `services/request_boundary.py` | SearchRequest 限制 | 只对 condition 中显式 `relation_path` / `path` 限深 |
| `services/permission_boundary.py` | Resource、字段、Relation Path 授权 | 有现有 helper；不足以证明多级路径每一段及目标记录规则均受保护 |
| `services/index_strategy.py` | operator/index 策略 | 支持 B-tree、pattern_ops、GIN trigram、none；不支持配置模型允许的 gist_trgm |
| `models/configuration.py` | Searchable Field、Relation Path、Published Snapshot | Searchable Field 校验当前是直接字段；Relation Path 单独存储 |
| `controllers/main.py` | Search/Cancel 入口及 conditions 响应 | 已有接口；本契约不新增路由或 Request 字段 |
| `tests/test_configuration.py` | Relation Path 与 Sale Order 根模型 | 已有 `order_line.product_id` 关系路径证据；根记录仍为 `sale.order` |

当前配置版本说明：在 2026-10-12 起草核对时，通过已认证 ORM 按 Published 状态及版本号
倒序查询到 `global_search_baseline` 最新 Published Version 5。其 ORM `published_at` 返回值为
`2026-10-08 00:51:19`（未在本契约中擅自换算时区），本次核对日期为 2026-10-12。该版本有
7 个活动 Resource；“最新”仅指本次查询时该配置域的最高 Published 版本，不保证其他数据库
或未来部署相同。

> 章节引用校正：CC-014 的 Invariants 实际位于 §9；其 §14 是 Definition of Done。
> 本契约核对的是 CC-014 实际 §9 Invariants，未把 §14 误读为不变量章节。

### 2.2 现有契约与代码核对结果

#### CC-014 与 CC-014-1

- CC-014 §4 定义的是 Card Template 语法；其变量最终值不得通过模板代码、任意关系遍历或
  绕过权限取得。
- CC-014 §8 要求按当前用户权限读取业务记录和字段，不使用超级用户权限绕过，并保证
  Card 纯文本及 HTML escaping。
- CC-014 §9 的不变量要求模板来自 Published Snapshot，Publish 对 Resource 模型字段验证，
  运行时按搜索用户权限处理。
- CC-014-1 §4–§6 对 Card 用 M2O 最多 3 跳、M2M 最多 2 跳；§7 的 O2M 是模板循环，最多
  两层嵌套。以上均不自动成为 Searchable Field 的实现或 API 承诺。
- Search 命中后返回的仍是根 Resource 记录。卡片取值复用 CC-014/CC-014-1，打开记录
  复用 CC-013；本契约不将关系目标记录替换为搜索结果身份。

#### CC-002 SearchRequest、资源数组及 Search API

既有 SearchRequest 结构为 `raw_query`、`parsed_conditions`、`refinement_conditions`、
`resource_scope`、`offset`、`limit`、`cursor`。HTTP/RPC Search API 将 `resources[]`
映射为 `resource_scope`；该数组限定实际结果范围，Facet Count 仍遵循 CC-012。

CC-002 规定同一维度条件按既有规则合并、不同维度组合，Count 在分页前以搜索 domain
计算，cursor 绑定 Published 配置版本、条件摘要和当前用户上下文。请求校验限制原始查询
500 字符、最多 20 个条件、条件嵌套深度 3、客户端 `relation_path` / `path` 最多 2 段；
这些边界不因本契约增加客户端 path 参数而放宽。

多级字段路径来自 Published Searchable Field，并通过既有 `dimension` 识别。客户端不能
传任意 ORM domain、relation path、字段元数据、权限声明或动态代码。配置中的多级字段
段数与 CC-002 对客户端条件对象 `relation_path` / `path` 的限制是不同输入边界。

#### CC-003 权限边界

CC-003 要求未授权 Searchable Field 不参加搜索或结果上下文；关系路径每一段都必须可
验证；模型、字段、Record Rule、公司域和权限异常均失败关闭。实现必须在路径根字段、
每个关系字段、中间模型和终端字段上作当前用户授权检查，并证明关联记录的 Record Rule
不会因多级匹配而被绕过或通过命中结果、Count、Query Understanding、错误差异或 timing
泄露。

当前 `permission_boundary.authorize_relation_path()` 检查关系字段及目标模型 read ACL，
而 `authorize_fields()` 只对传入模型上的字段名执行字段 ACL。它并非多级 Searchable
Field 的完整逐段授权实现；本契约要求补齐并以集成测试证明，不把现有 helper 名称当作
安全证据。

#### CC-012 Resource 与配置模型

CC-012 保持 Resource key、Published 版本、多选资源范围和授权 Count 语义。CC-014-2
仅在同一 Resource 的模型上下文内解析路径；Composite Resource 的每条路径只能针对其
对应的 Model Mapping，不得跨模型猜测字段或合并不同模型的关系图。

`wd.gs.searchable.field` 已包含 `field_name`、`purpose`、`operator_set`、
`searchable`、`readable_required`、`index_strategy`、`weight`；`field_name` 当前允许
的代码校验是单级直接字段。`wd.gs.relation.path` 单独保存 `path` / `max_depth`。
Published Snapshot 当前序列化 Searchable Field 的 name、purpose、operator_set、
index_strategy，但没有序列化 `searchable` / `readable_required`。

#### 服务、路由与测试现状

- `services/executor.py` 按配置字段名构建 ORM domain；`name` 维度另行扩展至显式
  Relation Path 的名称类字段。它没有将每个 Searchable Field 作为可独立配置的多级维度
  编译，也未使用每个字段配置的 `operator_set` 限定客户端 operator。
- `services/conditions.py` 合并 parsed/refinement 条件；`SearchRequest` 与
  `controllers/main.py` 已提供 Search/Cancel 接口和 `effective_conditions` 响应字段。
- `services/request_boundary.py` 只对 condition 内显式 `relation_path` / `path` 属性
  限深，不会验证 Published Field Path。
- `services/permission_boundary.py` 提供 Resource、字段和显式 Relation Path 的现有权限
  helper；新路径必须在既有当前用户 ORM 边界内扩展。
- `services/index_strategy.py` 目前默认 exact→B-tree、prefix→pattern_ops、
  contains→GIN；它的可用策略集合不包含 `gist_trgm`，而配置模型的 Contains 校验允许
  `gist_trgm`，两者存在待对齐差异。
- `tests/test_configuration.py` 已证明 Sale Order 当前 Relation Path 包含
  `order_line.product_id`，并以根 `sale.order` 执行关系搜索。Odoo 18 Sale Order 的真实
  技术字段名是 `order_line`，不是 `order_line_ids`。
- 当前模块代码没有 Searchable Field 多级解析器，也没有在 Search 请求中为多级路径创建
  物理数据库索引的服务。`search_count(domain)` 与记录搜索使用同一 domain 的模式应保留。

#### 当前 Published Configuration：`global_search_baseline` Version 5

当前活动单模型 Resource、Searchable Fields 和 Relation Paths 的只读结果如下。所有列出
的 Searchable Field 均为 `searchable=true`、`readable_required=true`、`weight=1.0`；
下表中的关系路径是既有独立 Relation Path，不是 Searchable Field。

| Resource key | 根模型 | 当前 Searchable Field（operator / index） | 当前独立 Relation Path |
|---|---|---|---|
| `warehouse` | `stock.warehouse` | `name` (contains / gin_trgm)；`code` (exact / btree) | 无 |
| `storage_location` | `stock.location` | `complete_name` (contains / gin_trgm)；`barcode` (exact / btree)；`name` (prefix / pattern_ops) | 无 |
| `product` | `product.product` | `name` (contains / gin_trgm)；`default_code` (prefix / pattern_ops)；`barcode` (exact / btree) | 无 |
| `contact` | `res.partner` | `name`、`email`、`phone` (contains / gin_trgm)；`ref` (exact / btree) | 无 |
| `stock_picking` | `stock.picking` | `name` (exact / btree)；`origin` (prefix / pattern_ops) | `partner_id`；`purchase_id`；`sale_id`，各 max_depth=1 |
| `sale_order` | `sale.order` | `name` (exact / btree)；`client_order_ref`、`origin` (prefix / pattern_ops) | `partner_id` max_depth=1；`order_line.product_id` max_depth=2 |
| `purchase_order` | `purchase.order` | `name` (exact / btree)；`partner_ref`、`origin` (prefix / pattern_ops) | `partner_id` max_depth=1；`order_line.product_id` max_depth=2 |

该版本没有配置 dotted Searchable Field，也没有 `wd.gs.performance.config` 记录。
以上清单是起草时对该 Published Version 的证据快照，不是要求其他部署或后续版本保持
相同字段列表。

### 2.3 Implementation Gap

1. Searchable Field 发布校验只接受根模型直接字段；关系字段路径作为单独 Relation Path
   配置，不能作为终端普通字段的可搜索维度。
2. 没有由 Odoo ORM 元数据验证并推导“关系前缀 + 终端字段”的 Search Field Path 编译。
3. 现有 Request Boundary 不负责验证 Published Field Path；Publish-time validation 也没有
   多级类型、深度、集合匹配策略和 cycle 校验。
4. 现有搜索授权函数不能证明目标模型的字段 ACL 和关联记录 Record Rule 覆盖完整。
5. 配置模型具有 Performance Config，但当前 Version 5 无性能行；服务对 Published
   Performance Config 的实际消费尚未实现/证明。3 跳路径不能只因语法通过就绕过该预算。
6. 索引策略字段和 helper 的 GiST 支持不一致；物理索引、关系边索引及查询计划没有由
   Searchable Field path 验证的证据。
7. 当前 Query Understanding 将原始 `dimension=value` 文本写入可见摘要；Search 响应
   `effective_conditions` 不能在权限检查前泄露未知或不可访问的路径。
8. Odoo 18 `sale.order` 的 O2M 技术字段是 `order_line`。`order_line_ids` 只可作为
   语法示意中的示例字段名，不能用于该模型的可发布配置。

### 2.4 Existing Contract Support

- CC-002 已提供 Published Snapshot、SearchRequest、条件合并、Resource 执行、分页、
  Count、错误聚合和 cursor 的既有服务边界。
- CC-003 已规定当前用户 ACL、字段 ACL、Record Rule、公司范围和失败关闭。
- CC-006/TDD 已规定 Exact、Prefix、Selective Contains 的索引策略、性能指标和隔离验证。
- CC-012 已规定 Resource 选择与授权 Facet Count 语义。
- CC-014/CC-014-1 已规定 Card 解析和关系显示；CC-013 已规定根记录导航。
- 现有 `field_name` 是 Char 配置值，可存完整技术路径；实施仍须改造其校验、Published
  Snapshot 消费、Search 条件编译和权限检查。

### 2.5 冻结文档保护

本契约不修改 SRS v1.5、TDD v0.4、Implementation Plan v0.3、CC-001~CC-014、
CC-014-1、TD-001 或 CC-006。若实现需要改变既有冻结 SearchRequest、Relation Path、
授权或索引策略，必须先走正式影响评审，不得以本 CC 隐式覆盖。

## 3. Scope

### 3.1 In Scope

- Searchable Field 的有限关系多级路径解析与 Publish-time 校验；
- 从 Odoo ORM 元数据推导关系边和终端字段；
- Many2one、Many2many、One2many 的深度与类型限制；
- Many2many / One2many 的 Published `any` / `all` 匹配策略；
- 在既有 SearchRequest 和 Search API 中以 Published 字段路径作为 `dimension` 执行搜索；
- 当前用户对根模型、每段关系、关联模型、终端字段和关联记录的权限边界；
- 保持 Count、分页、Resource scope、Query Understanding、Card 和导航契约；
- 每个字段路径的 operator/index metadata、关系边索引需求和隔离性能验证；
- 既有 Relation Path 的兼容及 Searchable Field 配置迁移。

### 3.2 Out of Scope

- 任意/递归关系图遍历、客户端提供关系图或任意 ORM domain；
- 条件语句、函数调用、算术/字符串表达式、变量赋值或变量计算；
- 聚合值或计算字段（L4）、自然语言解析、模糊匹配的新语义；
- Reference、Binary、Html 及未列入允许清单的终端类型；
- 多个集合关系在同一路径串接、M2M 后接 O2M、M2O 路径中接集合关系；
- 新建 Search API 路由、`/nl_search`、新的 SearchRequest 权限字段；
- Elasticsearch、OpenSearch、全文搜索服务、LLM、向量检索或外部搜索引擎；
- 修改 `odoo/` 或官方 addons、对业务查询使用 `sudo()`、绕过当前用户权限；
- 本契约草案阶段对配置、业务数据、数据库索引或服务代码作变更。

### 3.3 与既有契约的边界

| 既有契约 | CC-014-2 关系 |
|---|---|
| CC-014 | 只影响搜索条件命中的根记录集合；不改模板语法、Preview 或 Published Card 渲染 |
| CC-014-1 | Card 的多级取值和 O2M 循环继续由 CC-014-1 处理；不复用其 Search 查询解析器 |
| CC-002 | 不改 SearchRequest 字段、Search/Cancel 路由、`resources[]`、分页、cursor、状态或错误结构 |
| CC-003 | 复用并加强同一权限边界；任何授权差异都是 Stop Condition |
| CC-006 | 复用索引/性能政策；不在 Search 请求期间创建索引 |
| CC-012 | 不改 Resource selector、多选、未选资源 Facet Count 或 Count 授权范围 |
| CC-013 | 多级搜索命中后仍导航到根 Resource 记录的已配置 Form Action |

## 4. Searchable Field Multi-Level Syntax

### 4.1 语法

```ebnf
field_path := field_name ( "." field_name )*
field_name := [A-Za-z_][A-Za-z0-9_]*
```

路径各段必须是 Odoo 模型上的技术字段名。路径是否有效由 Published Resource 根模型/
Model Mapping 的 ORM 元数据决定；语法通过不代表路径一定可发布。

结构上限（段数包含终端字段）：

| 路径形态 | 最大关系跳转 | 最大路径段数 |
|---|---:|---:|
| 单级字段 | 0 | 1 |
| Many2one | 3 | 4 |
| Many2many | 2（包含起始 M2M） | 3 |
| One2many | 起始 O2M 后最多 2 个 M2O | 4 |

所有完整 `field_path` 的 ASCII 字符长度不得超过 100；超过字符数、段数或相应关系深度
时均在 Publish/Apply 拒绝。该路径长度上限是配置结构限制，不放宽 CC-002 的客户端条件
长度、嵌套或 Relation Path 请求边界。

| 类别 | 示例 | 说明 |
|---|---|---|
| 单级字段 | `name` | 兼容现有直接字段 |
| Many2one | `partner_id.city` | M2O 关系字段后接普通字段 |
| Many2one | `partner_id.country_id.name` | 两个 M2O 关系跳转后接普通字段 |
| Many2many | `category_id.name` | M2M 后接普通字段，须由根模型元数据证实 |
| One2many | `order_line_ids.product_id.name` | 语法示意；必须由对应模型实际字段元数据证实 |
| Odoo 18 Sale Order | `order_line.product_id.name` | `sale.order.order_line` 是实际 O2M 字段名 |

以下均拒绝，不得作为常量、自动修复路径或交给 ORM 执行：

```text
partner_id[0].city              # 索引访问
partner_id.city|upper           # 表达式 / formatter
partner_id.city()               # 函数或方法调用
partner_id.city + "!"           # 算术/字符串表达式
partner_id..city                # 空路径段
partner_id.city name            # 空格/多个字段名
```

### 4.2 根模型与字段身份

- 单模型 Resource 的根是 `primary_model_id`；Composite Resource 的根是各自独立的
  Model Mapping。
- Searchable Field Path 只在所属根模型中解析。不可从另一模型推断缺失字段或复用其
  relation path。
- Search API 使用既有 `conditions[].dimension` 表示查询维度；对多级搜索，该值必须与
  当前 Published Snapshot 中、当前 Resource/模型映射下的完整 `field_path` 完全匹配。
- 客户端路径不得被拆解后直接传给 ORM；解析所得元数据来自服务器 Published Snapshot
  与 Odoo ORM metadata。

## 5. Many2one Multi-Level Search

1. 路径前缀的每个关系字段必须为 Many2one；路径最多 3 个 Many2one 关系跳转，末端普通
   字段不计入跳转数。
2. 最后一段必须为 ORM 可搜索、非关系且受支持的普通字段：Char、Text、Integer、Float、
   Date、Datetime、Boolean、Selection 或 Monetary。Html、Binary、Reference、关系字段、
   未知类型和不能用于 ORM 搜索的非存储字段拒绝。
3. 文本 Char/Text 可由 Published operator 选择 exact、prefix 或 contains。数值、日期、
   Datetime、Boolean、Selection 和 Monetary 仅允许 exact；不把字符串前后缀匹配隐式转换
   为计算表达式或 Python 格式化。
4. 关系字段或任一中间记录为空时，该路径谓词不命中；不得退化到该关系字段的显示名称、
   数据库 ID 或其他字段。
5. 每一段 Many2one 关系字段及对应中间模型/记录均须按 §9 检查当前用户权限。任一关系
   字段、终端字段或关联记录不可读时，该路径不得参与搜索、Count 或 Query Understanding；
   不得通过命中与否、错误、计数或 timing 泄露字段/记录存在性。
6. 例子（每跳的字段类型及 comodel 必须从对应 Odoo 18 模型元数据验证）：

```text
partner_id.city                         # 1 个 Many2one 跳转
partner_id.country_id.name              # 2 个 Many2one 跳转
partner_id.country_id.region_id.name    # 3 个 Many2one 跳转
partner_id.country_id.region_id.zone_id.name  # 4 跳，拒绝
```

7. 路径不得在 M2O 链后切换到 Many2many 或 One2many；此类组合不属于本节搜索形态。

## 6. Many2many Multi-Level Search

1. 路径必须以根模型的 Many2many 字段开始，随后可接零或一个 Many2one，再以受支持的
   普通字段结束。最多 2 个关系跳转（M2M 自身计 1 跳）。
2. 禁止第二个 Many2many、One2many、M2M 之后的递归关系展开及 M2M 后接 O2M。
3. `collection_match` 是同一 Searchable Field 配置及 Published Snapshot 中的匹配策略，
   取值为 `any` 或 `all`；不是客户端条件属性，不另建 Relation Path 配置。
4. 多值语义：
   - `any`：同一字段路径的至少一个有效查询值，能在至少一条授权关联记录上匹配，即命中。
   - `all`：同一字段路径的每个不同有效查询值，均须至少由一条授权关联记录匹配；不同
     关联记录可以分别满足不同查询值。
   - 条件去重遵循 CC-002 Effective Conditions 规则；同一路径无有效值时不生成谓词。
     有有效值但关联集合为空时，`any` 与 `all` 均不命中。
   - `all` 仅改变该已配置集合字段上同路径多值的组合；不同 Searchable Field 之间仍按
     CC-002 的 AND 语义组合。直接字段和 M2O 字段的既有同维度 OR 语义不改变。
5. 示例：

```text
category_id.name                 # M2M + 普通字段，1 跳
category_id.parent_id.name       # M2M + M2O + 普通字段，2 跳
category_id.parent_id.parent_id.name  # 3 跳，拒绝
```

6. 生产搜索只返回根 Resource 记录；不得把 M2M 目标记录作为 Search Result 或 Card
   导航身份。关系记录读取、字段值及命中判断均受 §9 权限规则约束。
7. 搜索命中按集合语义计算，不格式化或返回关联值，因此关联行顺序不影响命中、Count、
   分页或根记录排序。若 Card 展示 M2M 值，其显示顺序继续遵循 CC-014-1，不由本节定义。

## 7. One2many Multi-Level Search

1. 路径必须以根模型的 One2many 字段开始；其后只能有零至两个 Many2one 跳转，最终以
   受支持的普通字段结束。One2many 集合起始边不计入“其后最多两个 Many2one 跳转”；
   对总路径性能深度仍按 §11 计数。
2. One2many 后禁止再接 Many2many 或第二个 One2many；不支持两个集合关系串接。
3. `collection_match` 使用 §6 同一 Published 配置策略：
   - `any`：同一字段路径的至少一个有效查询值可由至少一条授权行匹配；
   - `all`：同一字段路径的每个不同有效查询值都须由至少一条授权行匹配；各值可由不同
     行满足；
   - 有效查询值非空但授权关联行集合为空时，均不命中。
4. 示例：

```text
order_line_ids.product_id.name               # 1 个 Many2one 跳转，允许
order_line_ids.product_id.category_id.name   # O2M 后 2 个 Many2one 跳转，允许
order_line_ids.product_id.category_id.parent_id.name
                                               # O2M 后 3 个 Many2one 跳转，拒绝
```

对于 Odoo 18 `sale.order`，上例中的 `order_line_ids` 必须替换为真实技术字段 `order_line`；
有效示例为 `order_line.product_id.name` 及（经模型元数据核验后）
`order_line.product_id.categ_id.name`。展示名或常见命名不能代替 ORM 字段校验。

5. 本搜索路径不等于 CC-014-1 的 One2many For Loop；不读取/输出每行 Card 内容，也不改变
   Card 循环数量、顺序或渲染限制。
6. 搜索命中按集合语义计算，不格式化或返回关联行，因此行顺序不影响命中、Count、分页
   或根记录排序。Card 的循环顺序继续遵循 CC-014-1。

## 8. Relation Path Derivation

### 8.1 推导规则

对每个 Published Searchable Field `field_path`：

1. 用所属 Resource 根模型解析 `field_path.split(".")`；每段必须存在于当前 Odoo Model
   `_fields`。
2. 所有非末端段必须是 §5、§6 或 §7 所规定的关系类型，并通过其 `comodel_name` 继续解析。
3. 最后一段必须是 §5–§7 允许的 ORM 可搜索普通字段。
4. `relation_path = field_path.split(".")[:-1]`；末端段是 `terminal_field`。关系路径由
   模型元数据推导，不从客户端接受或从字符串猜测 comodel。
5. 发布快照需包含足以在运行时确定 field path、终端字段、匹配/operator/index 策略和
   所属模型映射的白名单元数据。快照不得包含业务记录值、权限规则内容或当前用户授权
   结果。

### 8.2 冲突与兼容

- 同一 Resource/model 的完整 `field_path` 只能有一个生效的 Published Searchable Field
  配置。重复路径或互相冲突的 operator、collection_match、index_strategy 在 Publish
  时拒绝。
- 两条不同路径可以共享相同关系前缀；推导元数据可按同一 Published version/model/path
  去重，不得因此合并不同终端字段的权限或 operator。
- 现有 `relation_path_ids` 继续用于既有 `name` 搜索扩展；它们与新的显式 Searchable
  Field 路径是两种不同语义。新字段路径不要求新增 Relation Path 记录，也不自动删改、
  转换或覆盖旧 Relation Path。
- 老 Published Snapshot 按原 schema 和行为消费。读取新 Snapshot 时若必需的 path metadata
  缺失或不兼容，返回既有 `CONFIGURATION_ERROR`，不回退到根字段、Relation Path 或空结果。

### 8.3 循环检测与缓存

- 只解析显式、有限、深度受限路径，不枚举任意关系图、不递归展开 comodel 的全部字段。
- 路径中重复同一个 `(model_name, relation_field_name)` 边视为 cycle 并拒绝；允许有界的
  自关联模型经过不同关系字段的显式路径，例如伙伴的父伙伴路径，只要不重复关系边且
  满足深度限制。
- 可缓存纯 ORM 字段元数据，缓存键至少绑定 Published version/checksum、根模型与完整
  field_path；不得缓存跨用户的授权结论、业务值、记录 ID 或命中结果。每个 Search 请求
 仍重新执行当前用户权限检查。

## 9. Permission Boundary

1. UserContext 只由既有 Search Facade 从当前 `request.env` 建立；SearchRequest 不接受
   客户端 `uid`、groups、公司范围、可读字段或权限标记。
2. Resource 根模型、每个关系字段、每个中间模型、终端字段和关联记录均按当前用户环境
   验证 ACL、字段组权限、Record Rule 和公司范围。业务查询不得使用 `sudo()`、超级用户
   或 admin environment。
3. 关联模型/记录的 Record Rule 必须实际约束该路径的匹配。仅检查关系字段的 read ACL
   或仅对根模型运行 `search_count` 不足以证明安全。若 Odoo ORM 对关联路径的 domain
   不自动应用目标记录规则，实施必须以当前用户可读的安全 ORM 方案实现等价约束；不得
   先以无权限上下文枚举 ID，再在 Python 中模拟 Record Rule。
4. 不可读字段/关系路径不参与搜索、Count、卡片、错误详情或 Query Understanding；
   若过滤后 Resource 无可用的已配置 Searchable Field，按 CC-003/CC-007 失败关闭。
5. Search Results 和 Count 必须仅代表当前用户获授权的根记录。结果条数、是否命中、
   pagination/cursor、错误差异、Query Understanding、延迟和日志不得作为旁路推断无权
   关系记录或字段值。
6. Query Understanding 使用已验证且对当前用户可用的 Effective Conditions；不回显未配置、
   不可读、被权限过滤或无效的关系路径。显示值按 CC-008 日志边界处理，不写入日志。
7. Preview / Result Card 的字段读取继续遵循 CC-014 / CC-014-1；打开根记录继续遵循
   CC-013；本契约不增加任何权限。
8. CC-002 Provider 对 Published 配置控制面元数据的隔离读取方式不授权 `sudo()` 读取
   业务模型、关联记录或字段。
9. 日志复用 CC-008 已批准的字段白名单；只可记录允许的 request/config/resource/status/
   latency/error metadata。不得把原始 field_path、搜索值、业务字段值、关联记录 ID、
   Record Rule 内容或新的未批准路径元数据加入日志。新增日志字段必须先完成 CC-008 影响评审。

## 10. Index Strategy

### 10.1 策略映射

每条 Searchable Field 的 Published `operator_set` / `index_strategy` 控制终端字段的
查询策略。策略应用在 ORM 元数据解析出的终端模型/字段；不得错误地在 Resource 根模型上
创建同名字段索引。

| Operator | CC-006 基线 | 适用说明 |
|---|---|---|
| Exact | B-tree | 高选择率 identifier 的精确匹配 |
| Prefix | B-tree `text_pattern_ops` | 遵循数据库排序规则与 CC-006 选择条件 |
| Selective Contains | GIN `gin_trgm_ops` | 只在需要且选择性/性能证据支持时采用 |
| 无物理索引 | `none` | 仅在有性能证据并符合已批准配置策略时使用 |
| GiST trigram | 非默认；需 CC-006/TV 明确证据 | 配置模型目前允许 `gist_trgm`，但 `services/index_strategy.py` 不支持，必须先在实施阶段对齐校验、索引创建和测试，不能静默认为可用 |

### 10.2 关系边与物理索引

- Many2one、One2many 和 Many2many 的关系边/关联表索引与终端字段索引是不同需求；每条
  查询路径应由 query plan 及代表性数据量证明，不得只凭 ORM 字段类型宣称已索引。
- 路径核对至少分别评估：M2O 外键关系边与终端字段；M2M 双向关联表键与终端字段；
  O2M 反向外键与终端字段。若某边或末端字段没有有效索引，需在 CC-006 流程中证明现有
  数据规模与预算仍可接受，或通过受控迁移补齐。
- `operator_set` 和 `index_strategy` 是 Published 配置声明，不等同于物理索引已创建。
- Publish/运行时不得执行索引 DDL。所需索引只能遵循 CC-006、TDD 和实施计划既有的受控
  创建、验证、维护窗口、写入影响评估及回滚流程；不得在本草案引入新的索引服务架构。
- 若目标字段的索引策略与路径 operator 不兼容、关联边索引缺失且性能门槛无法满足、
  PostgreSQL 扩展不可用或计划无法验证，必须阻止发布/上线，不能返回成功形状降级。
- 高选择率查询允许 Seq Scan；不得强制使用低效索引以满足形式化索引要求。

## 11. Performance Considerations

### 11.1 预算

所有 Published 配置只能收紧、不允许客户端扩展现有预算。适用基线为：

| 项目 | 基线 | 多级字段约束 |
|---|---:|---|
| SearchRequest Relation Path | CC-002 最多 2 段 | 继续限制客户端条件中的 `relation_path` / `path`；不修改 |
| M2O Searchable Field | 硬上限 3 个关系跳转 | 还必须满足 Resource 的 Published `max_relation_depth` |
| M2M Searchable Field | 硬上限 2 个关系跳转 | M2M 自身计 1 跳 |
| O2M Searchable Field | O2M 后最多 2 个 M2O 跳转 | Resource Performance Config 以整条路径关系边数计深度；示例总计 3 跳时需 max depth ≥3 |
| Resource / request timeout | CC-002：3 秒 / 5 秒 | 适用于 Count 与结果查询合计，不因多级路径延长 |
| 最大结果 / 条件 / 字段 | CC-002 既有 200 / 20 / 50 | 一个完整 Searchable Field Path 计一个字段 |
| Workspace 搜索性能 | CC-005：50k 首屏 P95 ≤2 秒软门禁；CC-006：5 万级首次结果 P95 ≤2 秒硬门禁、5 并发错误率 ≤1% | 多级路径必须在隔离性能验证中达到适用门禁 |

Published `wd.gs.performance.config.max_relation_depth` 是每 Resource 的额外上限，不得突破
上述关系类型硬上限。无配置行时遵循现有默认值 2；因此需要 3 条关系边的路径只有在
Published Resource Performance Config 明确允许深度至少 3 且其余预算仍满足时才可发布。
CC-002 的客户端 Relation Path 深度 2 仍独立生效，不被此配置覆盖。

预算适用范围：既有单级搜索不因本契约增加单字段的独立 timeout；每个 Search Request 中
所有直接及多级条件、关联路径、Count 和结果取回共享既有 Resource/Request 预算。多个
多级字段不各自获得完整 timeout，也不把每个字段的候选时间简单相加后重置预算。性能
验证分别测量单字段路径和包含多个条件的完整请求；字段数仍按完整 Searchable Field
计数。

评审提出的更细分 P95 目标（单级 500ms、M2O 1s、集合 ANY 1.5s、集合 ALL 2s）尚无对应
路径基准证据。本草案暂将其作为候选软目标：仅在隔离环境按 CC-006 方法实测并批准后
才能升级为验收门槛；当前 DoD 以 CC-002/CC-005/CC-006 已有总体预算为准。

### 11.2 查询执行要求

- 优先使用 Odoo ORM 的有限 domain/path 能力；不全量读取相关模型记录后在 Python 中筛选。
- Count、分页和结果查询必须使用同一组经过授权的 Effective Conditions、operator、
  collection_match 和权限约束。
- 每个根记录只计数一次；One2many/Many2many 多行命中不得导致重复 Result Identity 或
  Count。
- Search Count 不得为分页后的 `len(results)`；仍按 CC-002 在同一授权 domain 上独立计算。
- 运行时不得按用户输入形成无限 join、递归展开路径、增加未经批准的 prefetch 或放大结果集。
- 缓存仅可缓存经版本/checksum 绑定的静态路径元数据；授权与业务查询按每次请求执行。

### 11.3 预算测量与失败

- 既有 Search API 的 `resource_timeout` / `request_timeout` 计时覆盖该 Resource 的授权、
  多级条件、Count 与结果查询；在执行第二个路径或 Count 前不得重置时间预算。
- 超时按 CC-002/CC-007 状态与错误协议返回，不以部分查询结果伪装完整 Count。
- 性能报告记录数据规模、路径形态、collection_match、operator、配置版本、并发、P50/P95/P99、
  错误率、EXPLAIN 和索引大小；不得记录业务搜索值或关联记录 ID。

## 12. Simplification of Configuration

### 12.1 新配置方式

配置管理员在既有 Business Resource / Model Mapping 的 Searchable Fields 中配置完整
`field_name` 路径，并在同一行选择已有 operator/index 策略；集合路径再选择
`collection_match`：

| 配置项 | 示例 |
|---|---|
| Resource | `sale_order` |
| 根模型 | `sale.order` |
| Searchable Field `field_name` | `partner_id.city` |
| `operator_set` | `contains` |
| `index_strategy` | 按字段类型及 CC-006 选择，例如 `gin_trgm` 或有证据的 `none` |
| Collection `collection_match` | 非集合路径不适用；O2M/M2M 路径必填 `any` 或 `all` |

管理员不需要再为这个 Searchable Field 单独创建 `wd.gs.relation.path`；路径解析、关系边、
终端模型/字段均从 Published path 与 Odoo 元数据推导。

### 12.2 与既有 Relation Path 的关系

- 既有 `RelationPath` 继续提供 CC-002 的 `name` 搜索关系扩展，保留原配置和原行为。
- 一个显式 Searchable Field Path 是有明确终端字段、operator 和匹配策略的独立维度；
  `RelationPath` 是 `name` 搜索的关系范围，两者不可自动互相转换。
- 同一关系前缀可同时用于既有 `name` 搜索和显式 Searchable Field，不要求复制一条新的
  Relation Path，也不得因路径相同而丢弃其中一种搜索语义。

### 12.3 迁移策略

1. 既有 Published Snapshot 保持可消费；不在原 Snapshot 上写入 dotted path。
2. 升级仅扩展配置校验/序列化能力；若实现增加 `collection_match` 配置字段，旧直接字段
   配置保持兼容，集合路径在 Publish 前必须有确定策略。
3. 由管理员在新 Draft 中逐项添加完整字段路径、operator、index strategy 和（如适用）
   collection_match，经过 Check/Publish/Apply 的既有流程后才生效。
4. 不把旧 Relation Path 自动迁移成 Searchable Field；不删旧路径、不改变旧字段集合、
   Resource key、Published checksum 或 Card Template。
5. 配置无效、索引未准备或 Apply 失败时，旧 Published Configuration 保持有效；不得静默
   激活待处理字段。

## 13. Invariants

| ID | 冻结不变量 |
|---|---|
| CC14-2-INV-001 | 搜索字段多级解析只支持 Many2one、Many2many、One2many 及其本契约明示的有界路径形态。 |
| CC14-2-INV-002 | Many2one 路径最多 3 个 Many2one 关系跳转，末端字段不计入深度。 |
| CC14-2-INV-003 | Many2many 路径最多 2 个关系跳转；起始 M2M 后最多一个 M2O。 |
| CC14-2-INV-004 | One2many 路径起始 O2M 后最多 2 个 M2O 跳转；不得接第二个集合关系。 |
| CC14-2-INV-005 | 终端字段必须是受支持、非关系且可由 Odoo ORM 搜索的普通字段。 |
| CC14-2-INV-006 | 不支持无限或递归路径；同一 `(model_name, relation_field_name)` 边不得在一条路径重复。 |
| CC14-2-INV-007 | 不支持索引访问、表达式、函数/方法调用、赋值或计算。 |
| CC14-2-INV-008 | 关系路径与终端字段由 Odoo ORM 字段元数据推导。 |
| CC14-2-INV-009 | 配置多级 Searchable Field 不需要单独新增 Relation Path。 |
| CC14-2-INV-010 | Search 执行使用当前用户 ORM 环境，遵守 CC-003 的权限边界。 |
| CC14-2-INV-011 | 路径每段字段和关联模型权限由当前请求用户检查；不可读字段不参与搜索。 |
| CC14-2-INV-012 | Result Card 继续按 CC-014/CC-014-1 的当前用户权限读取。 |
| CC14-2-INV-013 | 根记录导航继续由 CC-013 的 configured Form Action 决定。 |
| CC14-2-INV-014 | 多级搜索不得引入新权限旁路；无法证明关联记录 Record Rule 时停止。 |
| CC14-2-INV-015 | Many2many 支持 Published 配置的 `any` 与 `all`。 |
| CC14-2-INV-016 | One2many 支持 Published 配置的 `any` 与 `all`。 |
| CC14-2-INV-017 | 多级字段 operator 与集合匹配语义由 Published Configuration 决定，客户端不得扩大。 |
| CC14-2-INV-018 | 索引策略由 Published Searchable Field 配置决定并遵守 CC-006；策略声明不等于物理索引存在。 |
| CC14-2-INV-019 | 多级搜索预算遵循 CC-002/CC-005/CC-006；Published Performance Config 只能收紧预算。 |
| CC14-2-INV-020 | 多级搜索结果是经过当前用户授权的根 Resource 记录。 |
| CC14-2-INV-021 | Search Count 与结果查询使用相同有效条件、集合匹配、权限范围和根记录去重语义。 |
| CC14-2-INV-022 | Query Understanding 只展示当前用户可见、已验证的条件摘要，不泄露无权路径和值。 |
| CC14-2-INV-023 | 多级搜索的 Card 渲染继续使用 CC-014/CC-014-1，不借搜索授权缓存跳过 Card 授权。 |
| CC14-2-INV-024 | 多级搜索的导航继续使用 CC-013，目标是根 Resource 记录。 |
| CC14-2-INV-025 | 自动化测试覆盖单级、多级、混合 Resource、ANY/ALL、权限、Count 和集成回归。 |
| CC14-2-INV-026 | SearchRequest、Search API route、`resources[]`、错误协议、分页和 cursor 结构不变。 |
| CC14-2-INV-027 | Published Snapshot 是运行时唯一配置来源；Draft/Rejected/待 Apply 修改不进入生产搜索。 |
| CC14-2-INV-028 | 路径元数据缓存不得缓存跨用户授权结论、记录值或搜索命中结果。 |
| CC14-2-INV-029 | Published Field Path 未命中已授权配置时不得交给 ORM，也不得回显路径存在性。 |
| CC14-2-INV-030 | 所有 Search、Count、Query Understanding 和错误输出均不得泄露未经授权的关联记录或字段。 |

## 14. Publish-time Validation

### 14.1 结构检查

Publish/Apply 前必须完成 Searchable Field Path 的结构检查，其性质类似配置静态检查：

- 只读取 Published 候选配置和 Odoo 字段 metadata；不读取业务记录试探匹配结果；
- 不读取、枚举或序列化 ACL/Record Rule 定义；
- 检查路径语法、段数、关系类型、终端字段、operator、collection_match、循环及配置预算；
- 结构检查通过不代表当前用户可以读取路径；每次 Search 仍须执行 §9 运行时授权；
- 结构检查使用既有配置校验/发布生命周期，不定义新的 Search API 或独立的写入接口。

### 14.2 发布校验清单

对每个 Business Resource / Model Mapping 的 Searchable Field，Publish / Apply 至少执行：

| 校验 | 拒绝条件 |
|---|---|
| 路径语法 | 空段、非允许字符、空格、索引、冒号、运算符、函数调用或表达式 |
| 根模型与字段 | 根模型/Mapping 不存在；任一字段名不在该层 Odoo `_fields` |
| 关系类型 | 中间字段类型不符合 M2O、M2M、O2M 专属形态 |
| 深度 | 超过相应关系族深度，或超过该 Resource Published `max_relation_depth` |
| 终端字段 | 是关系字段、非支持类型、Html/Binary/Reference、非 ORM 可搜索字段或不满足存储/搜索条件 |
| operator/type | operator 与终端字段类型不兼容；数值/日期等字段使用 prefix/contains |
| 集合语义 | M2M/O2M 路径缺少有效 `collection_match`，或直接字段错误配置集合匹配 |
| 重复/冲突 | 同一 Resource/model 同一完整路径重复或 operator、strategy、match 语义冲突 |
| cycle | 关系边重复、元数据解析出现循环或违反有界路径规则 |
| 索引策略 | 不在批准的 operator/index 兼容集合内；GiST 等策略未完成 CC-006 对齐 |
| Snapshot | 不能序列化或消费必需路径/operator/match/index 元数据 |
| 性能配置 | 字段路径超过 Published Performance Config 限制；三跳路径没有足够配置与性能证据 |

Publish-time validation 只读取配置和模型元数据，不读取业务记录来试探路径结果，不读取或
序列化 Record Rule 内容，也不替代每次 Search 的运行时授权。物理索引存在性及查询计划
须通过 CC-006 的受控索引/性能证据验证，不在 Publish 事务中创建索引。

校验失败必须显示明确的字段路径及错误类别；不得将错误字段路径静默删除、转换为常量、
映射到 `name`、忽略 operator 或让旧/草稿配置表现为成功。

## 15. Test Matrix

测试使用隔离 Odoo 测试数据库、受控 ORM fixtures 与专用性能环境；不得在共享业务库进行
临时 DDL、批量业务数据读取或测试索引创建。以下名称是可执行测试的命名契约，实施时可
使用等价测试框架，但每项断言不可省略。

| ID | 可执行测试名 / 类型 | Arrange / Act | 必须断言 |
|---|---|---|---|
| CC14-2-TEST-001 | `test_many2one_one_hop_search` / ORM integration | 配置 `partner_id.city`，创建两城市联系人及订单，按其中一城搜索 | 只命中授权且关联城市相同的根订单；Count 相等 |
| CC14-2-TEST-002 | `test_many2one_two_hop_search` / ORM integration | 配置 `partner_id.country_id.name`，匹配国家 | 两跳关系正确解析；不匹配国家的根记录不出现 |
| CC14-2-TEST-003 | `test_many2one_three_hop_search_with_budget` / ORM integration | 配置三跳 M2O 路径，并发布 `max_relation_depth=3` | 三跳命中正确；不超过 CC-002/CC-006 运行时预算 |
| CC14-2-TEST-004 | `test_many2one_four_hops_rejected` / configuration | 配置四个 M2O 边后接终端字段 | Publish/Apply 明确拒绝；旧 Published Snapshot 保持有效 |
| CC14-2-TEST-005 | `test_many2many_one_hop_search` / ORM integration | 配置 `category_id.name`，至少两个 category | 按终端值命中根记录，不返回 category 作为结果 |
| CC14-2-TEST-006 | `test_many2many_two_hops_search` / ORM integration | 配置 `category_id.parent_id.name` | M2M 后单个 M2O 正确命中 |
| CC14-2-TEST-007 | `test_many2many_three_hops_rejected` / configuration | 配置 M2M 后两个 M2O | 超过两跳时 Publish 拒绝 |
| CC14-2-TEST-008 | `test_one2many_collection_then_one_many2one` / ORM integration | 配置真实 O2M 后一个 M2O 的路径，如 `order_line.product_id.name` | 关联行匹配返回根 Sale Order；重复行不重复计根记录 |
| CC14-2-TEST-009 | `test_one2many_collection_then_two_many2one` / ORM integration | 配置 O2M 后两个 M2O 路径，并允许总深度3 | 按已确认深度语义通过 Publish 并命中正确根记录 |
| CC14-2-TEST-010 | `test_one2many_collection_then_three_many2one_rejected` / configuration | 配置 O2M 后三个 M2O | Publish 拒绝；返回可定位的深度错误 |
| CC14-2-TEST-011 | `test_relation_terminal_field_rejected` / configuration | 将 Many2one/Many2many/One2many 作为路径末端 | Publish 拒绝，不能隐式搜索 `display_name` |
| CC14-2-TEST-012 | `test_repeated_relation_edge_cycle_rejected` / configuration | 创建含重复 `(model, relation field)` 边的自关联路径 | Publish 拒绝；不同边的有界自关联路径仍可通过 |
| CC14-2-TEST-013 | `test_index_syntax_rejected` / configuration | Searchable Field 为 `partner_id[0].city` | Publish 拒绝语法，不传给 ORM |
| CC14-2-TEST-014 | `test_expression_syntax_rejected` / configuration | Searchable Field 为 `partner_id.city|upper` 或算术表达式 | Publish 拒绝，不将表达式输出成常量 |
| CC14-2-TEST-015 | `test_function_call_syntax_rejected` / configuration | Searchable Field 为 `partner_id.city()` | Publish 拒绝且不调用方法 |
| CC14-2-TEST-016 | `test_relation_path_derived_from_orm_metadata` / unit + Odoo integration | 校验 `partner_id.country_id.name` 对应模型/边/末端 | 推导 comodel 序列与 ORM metadata 一致；输入字符串不能替代 metadata |
| CC14-2-TEST-017 | `test_searchable_path_does_not_require_relation_path_row` / integration | 只发布 `partner_id.city` Searchable Field，不创建 RelationPath | 新维度搜索成功；旧 RelationPath 配置可独立保留 |
| CC14-2-TEST-018 | `test_each_path_segment_obeys_current_user_permissions` / multi-user ORM integration | 用户无权读中间关系字段/终端字段或目标模型 | 路径不参与搜索；无字段值、记录、Count 或路径存在性泄漏 |
| CC14-2-TEST-019 | `test_related_record_rules_filter_multi_level_search_and_count` / multi-user ORM integration | 关联模型 Record Rule 隐藏匹配行 | 隐藏行不能使根记录命中或增加 Count；不得用 sudo/Python 规则模拟 |
| CC14-2-TEST-020 | `test_count_matches_multi_level_conditions_before_pagination` / integration | 用同一路径匹配多根记录，使用 limit/offset 多页 | Count 不随分页变化，且等于授权、去重后的根记录总数 |
| CC14-2-TEST-021 | `test_query_understanding_shows_only_authorized_field_summary` / controller + browser | 搜索有效、未知和不可读路径 | 只显示已验证且当前用户可用的条件摘要；未知/拒绝路径不回显 |
| CC14-2-TEST-022 | `test_card_template_renders_with_cc014_1_after_path_search` / integration + browser | 多级 Search 命中根记录，Card 使用 CC-014-1 模板变量/循环 | 过滤结果与 Card 值各用自身契约授权；显示正确且无控制台错误 |
| CC14-2-TEST-023 | `test_many2many_any_matches_one_query_value` / ORM integration | 配置 M2M `any`，两个条件值中仅一个由关联项满足 | 根记录命中；Count 与结果一致 |
| CC14-2-TEST-024 | `test_many2many_all_requires_each_query_value` / ORM integration | 配置 M2M `all`，两个不同关联项分别满足两个条件值 | 根记录命中；缺少任一个值时不命中 |
| CC14-2-TEST-025 | `test_one2many_any_matches_one_query_value` / ORM integration | 配置 O2M `any`，一行满足任一查询值 | 根记录命中；其他不匹配根记录不出现 |
| CC14-2-TEST-026 | `test_one2many_all_requires_each_query_value_across_rows` / ORM integration | 配置 O2M `all`，不同订单行分别匹配两个值 | 两值皆有授权匹配行才命中；空行集不命中 |
| CC14-2-TEST-027 | `test_terminal_index_strategy_matches_published_operator` / config + isolated DB | Exact/Prefix/Contains 分别校验配置与目标终端字段索引策略 | 策略落在终端模型字段，兼容 CC-006；不兼容策略 Publish/检查失败 |
| CC14-2-TEST-028 | `test_multilevel_search_meets_published_performance_budget` / isolated performance | CC-006 5 万级数据集、代表性路径、5 并发 | 首次结果 P95 ≤2 秒、并发错误率 ≤1%；保存 P50/P95/P99 与 EXPLAIN 证据 |
| CC14-2-TEST-029 | `test_multi_level_search_preserves_cc014_1_behavior` / regression integration | 同一 Resource 配置 Search Field Path 与 Card 关系路径/循环 | Card 语法、值、分隔符和渲染行为与 CC-014-1 一致 |
| CC14-2-TEST-030 | `test_multi_level_search_navigation_targets_root_resource` / browser integration | 搜索命中有关联字段的根记录并打开结果 | CC-013 configured Form Action 打开根模型记录，不打开关联目标记录 |

## 16. Regression Requirements

- **CC-014：** Card Template Designer、Live Preview、Published Snapshot 和 rendering 行为不变。
- **CC-014-1：** Card 关系路径深度、M2M separator、One2many For Loop 和权限规则不变。
- **CC-013：** Result Card 导航仍打开根 Resource 的 Native Form。
- **CC-012：** Resource Selector、多选、空选、已选结果范围及所有授权 Resource Facet Count 不变。
- **CC-003：** 当前用户、公司、字段、关系、Record Rule 和失败关闭不变且覆盖新路径。
- **CC-007：** EMPTY、PARTIAL_SUCCESS、FAILED、TIMEOUT、取消和错误聚合语义不变。
- **CC-008：** 日志字段白名单、Audit 语义及不记录业务值的要求不变。
- **CC-009：** label、语言、时区仍以服务端来源为准。
- **CC-010：** Published checksum/config version 不可由 Workspace 修改；旧 Snapshot 失败时不被新草稿替代。
- **CC-002：** SearchRequest、Search API、`resources[]`、cursor、Count、分页、错误结构和客户端
  Relation Path 深度校验不变。
- **CC-006：** 索引创建受控、查询计划可追溯、权限不变；高选择率 Seq Scan 仍可接受。

## 17. Stop Conditions

出现下列任一情况，停止实现/发布并提交影响评审，不得自行放宽契约：

1. 无法在 Publish 时确定路径语法、各段 Odoo 字段类型或终端字段类型。
2. 路径深度计数不能区分 M2O、M2M、O2M 规则，或超出 Published Performance Config。
3. ORM metadata 不能无歧义推导关系路径、目标模型或终端字段。
4. 终端字段是关系、Reference、Binary、Html、非 ORM 可搜索或不支持的类型。
5. 路径含重复关系边、多个集合关系或任何需要递归展开的关系。
6. 无法为每个中间关系字段/目标模型/终端字段建立当前用户授权检查。
7. 无法证明目标关联记录 Record Rule 和公司范围约束参与搜索与 Count。
8. 必须使用 `sudo()`、superuser、admin env、请求体权限声明或直接读取业务数据库才能完成。
9. Search Count、分页、去重和结果集合不能保持同一授权谓词。
10. ANY/ALL 的有效条件、空集合行为或跨字段 AND 语义无法确定或无法一致执行。
11. Query Understanding 仍可能显示未授权或无效的 path/value。
12. 需要修改 SearchRequest、Search API route、`resources[]` 或 CC-002 错误/分页协议但尚未完成正式影响评审。
13. 需要删除、自动转换或覆盖既有 Relation Path 才能提供新 Searchable Field。
14. 索引策略与 operator 不兼容、必需索引无法受控创建/维护，或查询计划/性能预算不达标。
15. 需要修改 SRS/TDD/既有冻结 CC 而未完成影响评审和重新批准。
16. 需要引入 LLM、向量检索、Elasticsearch/OpenSearch、外部搜索引擎、`/nl_search` 或
    `NOT_IMPLEMENTED` 响应。
17. 需要修改官方 `odoo/` 或 addons，或直接修改共享/生产配置及业务数据；测试配置只能
    在隔离 Odoo 测试数据库中建立和清理。
18. 静态结构检查失败、无法完成或结果不确定时，不得进入 Publish/Apply 或实施验收；
    不得用空结果、静默忽略字段或默认成功继续。

## 18. Definition of Done

- [ ] 通过治理和范围评审；本契约获用户批准冻结后才进入实施。
- [ ] M2O/M2M/O2M 语法、深度、字段类型、operator 与集合匹配校验可执行。
- [ ] 路径完全由 ORM 元数据推导；没有独立 Relation Path 配置依赖或客户端任意 path。
- [ ] Published Searchable Field、collection_match 和 index metadata 序列化/读取兼容明确。
- [ ] 当前用户 ACL、字段组、关联模型 Record Rule、公司范围和失败关闭有集成证据。
- [ ] Search Result 是根 Resource 记录；关系多行正确去重。
- [ ] Search Count 与授权条件一致，不受 limit、offset、cursor 或重复关系行影响。
- [ ] Query Understanding 只显示当前用户可见的已验证条件摘要。
- [ ] Many2many/One2many `any` 与 `all` 的多值、空集行为分别通过测试。
- [ ] CC-006 索引策略兼容性、物理索引部署流程、查询计划和写入影响经受控验证。
- [ ] CC-002/CC-005/CC-006 适用性能预算通过；保存 P50/P95/P99、并发错误率和 EXPLAIN。
- [ ] CC-014、CC-014-1、CC-013、CC-012、CC-003、CC-007~CC-010 回归通过。
- [ ] 至少 CC14-2-TEST-001~030 自动化测试通过，并有测试报告证据。
- [ ] Search Workspace 浏览器 HVR 覆盖路径查询、权限差异、Query Understanding、Count、
  Result Card 和根记录导航。
- [ ] IHR、ATR、HVR 及必要的性能证据记录配置版本、commit、环境和测试结果。
- [ ] 失败的 Publish/Apply 保留原 Published Configuration；不静默启用 Draft。
- [ ] 无 `/nl_search`、新 Search API 路由、NOT_IMPLEMENTED 响应、外部搜索引擎或官方代码改动。

## 19. Decisions

| ID | 决策 | 理由 |
|---|---|---|
| CC14-2-DEC-001 | 搜索多级解析只支持 M2O、M2M、O2M | 覆盖既有 Odoo 关系类型且边界可验证 |
| CC14-2-DEC-002 | M2O 最大 3 个关系跳转 | 与受控深度及既有关系字段能力一致 |
| CC14-2-DEC-003 | M2M 最大 2 跳：M2M 加最多一个 M2O | 避免多集合 join 膨胀 |
| CC14-2-DEC-004 | O2M 起始集合之后最多 2 个 M2O | 与评审确认的示例一致；O2M 自身不计入该后续深度 |
| CC14-2-DEC-005 | 终端必须是受支持、ORM 可搜索的普通字段 | 禁止依赖隐式 display_name 或动态计算 |
| CC14-2-DEC-006 | 不允许递归关系图；重复同一模型字段关系边即为 cycle | 路径有限且可静态验证，同时允许有界自关联的不同关系边 |
| CC14-2-DEC-007 | 拒绝索引、函数、表达式和方法调用 | 避免执行动态输入或建立隐式计算语义 |
| CC14-2-DEC-008 | 关系路径从 Odoo ORM 元数据推导 | 保证模型/字段身份与实际 Resource 一致 |
| CC14-2-DEC-009 | 新 Searchable Field path 不需要单独 Relation Path | 避免重复配置并绑定明确终端字段 |
| CC14-2-DEC-010 | 既有 Relation Path 保留其 `name` 搜索用途 | 新旧语义不同，删除/自动转换会破坏既有搜索行为 |
| CC14-2-DEC-011 | 搜索只使用当前用户 ORM 环境 | 延续 CC-002/CC-003 权限边界 |
| CC14-2-DEC-012 | 路径每段字段与关联模型都执行权限验证 | 单独检查根字段无法保护多级路径 |
| CC14-2-DEC-013 | 关联记录 Record Rule 必须约束关系匹配 | 防止通过根记录命中或 Count 推断隐藏关联记录 |
| CC14-2-DEC-014 | 目标 Card 字段权限继续由 CC-014/CC-014-1 管理 | Search 授权不应成为 Card 字段读取的授权凭据 |
| CC14-2-DEC-015 | 导航只到根 Resource 记录 | 遵守 CC-013 的身份和 Action 语义 |
| CC14-2-DEC-016 | M2M `any` 表示至少一个查询值命中授权关联项 | 适合默认集合搜索且不要求所有值都存在 |
| CC14-2-DEC-017 | M2M `all` 表示每个不同查询值都由至少一个授权关联项满足 | 允许不同关联记录分别满足不同值，便于精确集合筛选 |
| CC14-2-DEC-018 | O2M `any` / `all` 使用与 M2M 相同的查询值语义 | 使多值匹配规则在两种集合关系间一致 |
| CC14-2-DEC-019 | 有条件但集合为空时 `any` 与 `all` 均不命中 | 避免逻辑全称的空集真值导致无关联记录被选中 |
| CC14-2-DEC-020 | 集合匹配策略保存在同一 Searchable Field Published 配置中 | 策略由发布版本固定，不增加独立 Relation Path 注册表 |
| CC14-2-DEC-021 | 搜索 operator 由 Published `operator_set` 约束 | 请求不能扩大 exact/prefix/contains 策略 |
| CC14-2-DEC-022 | 索引策略遵守 CC-006；配置声明不视为物理索引证据 | 区分配置、部署和查询计划 |
| CC14-2-DEC-023 | `gist_trgm` 在代码/配置校验对齐前不得视作运行时已支持 | 处理现有配置模型与 helper 的不一致 |
| CC14-2-DEC-024 | Published `max_relation_depth` 作为每 Resource 上限；缺省 2，最高仍受路径类型硬上限 | 保留 CC-002 预算并允许显式批准更深配置 |
| CC14-2-DEC-025 | Count 与结果共享相同授权条件和根记录去重语义 | 防止分页或集合 join 改变 Count/泄露信息 |
| CC14-2-DEC-026 | Query Understanding 使用已验证且可见的 Effective Conditions | 保持 CC-005 可解释性并消除 path 泄漏 |
| CC14-2-DEC-027 | Card rendering 继续使用 CC-014/CC-014-1 | 搜索路径和展示路径职责分离 |
| CC14-2-DEC-028 | 不新增 Search API 路由或请求字段 | 通过既有 `dimension` 和 Published Snapshot 表达能力 |
| CC14-2-DEC-029 | 不自动迁移/删除既有 Relation Paths 或 Searchable Fields | 保持已发布配置及搜索回滚能力 |
| CC14-2-DEC-030 | 单元、ORM、安全、性能、浏览器及回归证据全部作为 DoD | 关系查询同时影响语义、权限、Count、UI 和数据库计划 |

## 20. Implementation Structure

以下是基于现有代码边界的责任划分，不是冻结文件清单或新增架构要求。实施评审决定是否
扩展现有模块或抽取内部 helper；不得因此新增 API 路由或外部服务。

| 现有职责边界 | CC-014-2 需要的实现 |
|---|---|
| `models/configuration.py` | 扩展 Searchable Field 校验、Published Snapshot 白名单元数据和适用的集合匹配配置；兼容旧单级配置 |
| `services/provider.py` | 继续只提供当前 Published Snapshot/version/checksum；不向普通用户开放配置模型 |
| `services/conditions.py` | 保持 CC-002 条件合并；为 Published collection_match 形成可确定的路径条件组 |
| `services/executor.py` | 将已验证的完整 field_path 编译为 ORM 查询；同一权限条件用于搜索与 Count |
| `services/permission_boundary.py` | 对路径根字段、每个关系段、关联模型、目标记录及终端字段执行当前用户授权 |
| `services/request_boundary.py` | 继续检查既有请求形状和客户端 path 上限；不把任意 field_path 输入变成新执行能力 |
| `services/index_strategy.py` 与既有索引流程 | 对齐策略可用集合、目标终端字段、CC-006 索引生命周期和错误处理 |
| `controllers/main.py` 与 Workspace JS | 复用现有 Search API、`effective_conditions` 和 Query Understanding；过滤无效/无权摘要 |
| 现有 `tests/` | 扩展配置、Request、Executor、Permission、Count、索引策略、浏览器和性能测试 |

不得将建议的新 helper 文件名视为预先固定的架构；必须由已有代码结构和批准后的实现评审
确定最小改动位置。

## 21. Appendix

### 21.1 SRS / TDD 追溯矩阵

| 上游 / 冻结契约 | CC-014-2 落实位置 |
|---|---|
| SRS v1.5 Search / permission / performance requirements | §3、§5–§11、§15–§18 |
| TDD v0.4 SearchRequest / Effective Conditions / Resource execution | §2、§3、§4、§8、§11、§16 |
| TDD §8 / §11.4、CC-006 | §2、§10、§11、TEST-027、TEST-028 |
| CC-002 Search API / Count / paging / `resources[]` | §2、§3、§9、§11、INV-026、§16 |
| CC-003 Permission Boundary | §2、§9、TEST-018、TEST-019 |
| CC-012 Resource Selector / authorized counts | §2、§3、§16 |
| CC-014 / CC-014-1 Card rendering | §3、§5–§7、§9、TEST-022、TEST-029 |
| CC-013 Navigation | §3、§9、TEST-030 |

### 21.2 接口契约

本契约复用现有 SearchRequest / Search API，不固定或新增路由：

```text
SearchRequest:
  raw_query
  parsed_conditions[{dimension, operator, value}]
  refinement_conditions[{dimension, operator, value}]
  resource_scope
  offset / limit / cursor

Published Searchable Field:
  model_name
  field_path
  purpose
  operator_set
  index_strategy
  collection_match (仅适用于 M2M / O2M)

SearchResponse:
  status / request_id / results / counts / errors / meta
  effective_conditions (仅包含有效且对当前用户可见的条件)
```

- `dimension` 必须映射到 Published Field Path；不匹配的值不得执行。
- `resource_scope` 继续映射既有 `resources[]`；不改空选、多选或 Facet Count 语义。
- 结果身份为根 Resource；count、分页、cursor、状态和错误协议遵循 CC-002/CC-007。
- 不增加 `relation_path` 请求字段、动态 domain、客户端 match mode 或权限参数。

### 21.3 术语表

| 术语 | 定义 |
|---|---|
| Searchable Field Path | Published Configuration 中绑定到根模型/Mapping 的完整技术字段路径 |
| Relation Path | Searchable Field Path 中终端字段之前、由 ORM metadata 推导出的关系字段前缀 |
| Terminal Field | 路径末尾的普通、可搜索字段 |
| Collection Relation | Many2many 或 One2many 字段 |
| `any` | 同一路径至少一个不同查询值由至少一条授权关联记录匹配 |
| `all` | 同一路径每个不同查询值均由至少一条授权关联记录匹配 |
| Published Performance Config | 已发布的 per-Resource timeout、result 和 relation depth 上限 |
| Root Resource Record | Search Result、Count 和 CC-013 导航所表示的业务记录 |

### 21.4 版本历史

| 版本 | 日期 | 状态 | 变更 |
|---|---|---|---|
| v0.1 | 2026-10-12 | DRAFT | 初稿；核对冻结契约、代码结构、Published Version 5，并冻结路径/匹配语义提案 |
| v0.2 | 2026-10-12 | FROZEN | 根据用户提供的评审意见补充版本基线、核对范围、路径限制、权限说明、预算适用范围、结构检查、验收与证据规范；用户批准冻结并进入实施 |

### 21.5 实施阶段需验证的证据

1. 多级关系匹配如何在当前用户环境下完整应用中间模型/关联记录 Record Rule。
2. `gist_trgm` 与 `services/index_strategy.py` 的策略兼容集合如何依据 CC-006/TV 证据对齐。
3. Search Service 如何消费每 Resource Performance Config，尤其是三跳路径与 3 秒/5 秒预算。
4. 所需关系边与终端字段物理索引的创建、验证、维护窗口和回滚证据。
5. Odoo 18 中每个目标模型的实际 technical field、field type、store/search capability。

以上实现证据不得通过放宽 CC-003、直接访问共享数据库或修改既有冻结契约来替代。

### 21.6 评审记录与修订清单

| 日期 | 评审来源 | 结论 | 处理状态 |
|---|---|---|---|
| 2026-10-12 | 用户提供的《对 CC-014-2 Searchable Field Multi-Level Resolution 的评审》（未署名） | 肯定草案完整性；建议补充后进入 Freeze 流程 | 已吸收有证据支持的补充 |
| 2026-10-12 15:49 +08:00 | 用户批准 | 批准冻结 CC-014-2 并进入实施 | FROZEN |

| 修订项 | 处理 |
|---|---|
| §0 版本基线、§2.1 只读范围/代码结构/Published 版本时点 | 已补充 |
| §4 路径段数和长度限制、§5 中间段权限 | 已补充 |
| §6/§7 关系行顺序 | 搜索是集合匹配且不渲染关系值，明确顺序不影响搜索；Card 顺序仍由 CC-014-1 定义 |
| §11 预算适用范围、§14 结构检查、§17 结构检查失败停止条件 | 已补充 |
| 评审记录、测试 fixture、验收/HVR、浏览器矩阵和日志规范 | 已补充至本附录 |
| 细分 P95 目标 | 暂列候选软目标，不作为当前 DoD 门槛；需隔离性能证据和批准后方可冻结 |

### 21.7 测试 Fixture 规范

- 使用 Odoo 隔离测试数据库及现有测试框架/fixture 约定；最终文件位置由实施评审决定，
  本契约不预设新增目录或文件结构。
- Fixture 覆盖 Contact、Sales Order、Purchase Order 等多 Resource；M2O、M2M、O2M；
  允许/超限深度；有权、无权、部分可读用户；`any` / `all`；exact、prefix、contains。
- 每个测试套件使用唯一标记，确保断言只涉及本测试创建的记录；使用测试框架的事务回滚/
  teardown 清理。不得在共享数据库中验证“fixture 总数为零”或执行清理 SQL。
- 权限 fixture 应覆盖根模型 Record Rule 与关联目标 Record Rule 不同的情形；性能 fixture
  只在隔离性能环境创建，不复用生产/共享业务数据。

### 21.8 验收场景

1. 配置管理员在 Draft 中配置一条简单 M2O Searchable Field Path，Publish 后能按终端值搜索。
2. 配置管理员配置三跳 M2O 路径，只有在 Published depth 预算允许且性能证据合格时可搜索。
3. M2M `any` 在任一不同查询值由关联项匹配时命中。
4. M2M `all` 仅在每个不同查询值都由授权关联项匹配时命中。
5. O2M `any` / `all` 分别遵循相同查询值语义。
6. 有有效查询值但授权关联集合为空时，ANY/ALL 均不命中。
7. 中间字段、终端字段或关联模型/记录权限不足时，不搜索、不计数、不显示条件摘要。
8. Count、分页和结果对同一授权谓词及根记录去重保持一致。
9. Query Understanding 显示已验证且当前用户可见的条件，不回显拒绝路径。
10. 多级搜索后 Card 按 CC-014-1 渲染，打开动作按 CC-013 导航至根记录。

### 21.9 HVR 场景

| HVR | 人工操作 | 预期 |
|---|---|---|
| HVR-001 | 配置并发布 M2O 多级 Searchable Field，使用终端值搜索 | 只显示匹配且当前用户授权的根记录 |
| HVR-002 | 对同一路径配置 `any`，输入多个查询值 | 任一值匹配时命中 |
| HVR-003 | 对同一路径配置 `all`，让不同关联行分别满足各查询值 | 全部值满足才命中；缺任一值不命中 |
| HVR-004 | 使用无关联记录的根记录搜索 | 有效查询条件下不命中 |
| HVR-005 | 使用受限关联模型/记录的目标用户重复搜索 | 无权关系不影响结果/Count，不泄露其存在 |
| HVR-006 | 比较不同 limit/offset 页和 Count | Count 不随分页变化且根记录不重复 |
| HVR-007 | 检查 Query Understanding | 只显示有效且可读的条件摘要 |
| HVR-008 | 打开多级搜索结果 | Card 正常渲染，导航打开根 Resource Form |

### 21.10 浏览器兼容性验证矩阵

浏览器版本应记录实施验证时 Odoo 18 支持的实际版本；本矩阵是待验证范围，不表示当前
已通过，也不扩大 Odoo 上游支持承诺。

| 浏览器 | 版本记录 | Desktop | Tablet | Narrow |
|---|---|---|---|---|
| Chrome | HVR 时记录 Odoo 支持版本 | 待验证 | 待验证 | 待验证 |
| Firefox | HVR 时记录 Odoo 支持版本 | 待验证 | 待验证 | 待验证 |
| Safari | HVR 时记录 Odoo 支持版本 | 待验证 | 待验证 | 待验证 |
| Edge | HVR 时记录 Odoo 支持版本 | 待验证 | 待验证 | 待验证 |

至少完成项目既有 Chromium HVR；其他浏览器仅在属于目标部署支持范围时列入验收。

### 21.11 Logging Contract

- 复用 CC-008 的日志字段白名单和审计语义，不新增日志服务或任意字段。
- 仅记录 CC-008 已批准的 request/config/resource/status/latency/error metadata。
- 不记录 `field_path`、原始 query/condition value、业务字段值、关联记录 ID、Record Rule
  内容、Action XML ID、令牌或完整异常详情。若后续确需新增路径级诊断字段，先作 CC-008
  影响评审并以脱敏/白名单设计批准。
