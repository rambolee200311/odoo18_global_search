# CC-014-1 — Relation Field Multi-Level Resolution

## 0. Governance

| 项 | 内容 |
|---|---|
| Coding Contract | CC-014-1 |
| 版本 | v0.1 |
| 状态 | FROZEN |
| Intent ID | `GS-SEARCH-RESULT-CARD-RELATION-FIELD-MULTI-LEVEL` |
| 上游 SRS | [SRS_global_search](../../requirement/SRS_global_search.md) v1.5 FROZEN |
| 上游 TDD | [TDD_global_search](../../design/TDD_global_search.md) v0.4 FROZEN |
| 实施计划 | [IMPLEMENTATION_PLAN_global_search](../../implementation/IMPLEMENTATION_PLAN_global_search.md) v0.3 FROZEN |
| 前置 CC | CC-001 ~ CC-014；TD-001 |
| 模块 | `wd_global_search` |
| 目标 | 在 CC-014 已发布卡片模板中支持受约束的关系字段多级解析和 One2many 循环 |
| 批准冻结 | 用户批准；2026-10-12 10:57 +08:00 |
| 版本基线 | SRS v1.5、TDD v0.4、实施计划 v0.3；CC-014 v0.1 FROZEN |

本 CC 仅扩展 Result Card 模板的关系路径解析与 One2many 循环语法。它不修改或取代
SRS、TDD、实施计划、CC-003 权限边界、CC-013 导航契约或 CC-014 的模板设计器/预览/
配置生命周期。若本 CC 与既有冻结契约冲突，以既有契约为准，并触发影响评审。

版本基线处理：本文采用仓库当前冻结的 SRS v1.5、TDD v0.4 和实施计划 v0.3；CC-014
已冻结，本 CC 只增加关系路径与循环扩展，不改写 CC-014 原语义。若评审要求改变任何
上游或既有 CC 的冻结要求，必须先完成影响评审，不得通过修改版本号规避。

## 1. Contract Goal

CC-014 支持单级字段；CC-014-1 在相同 Published Configuration、格式化及权限边界内，
支持有限深度的 Many2one/Many2many 解析和最多两层嵌套的 One2many 循环。

```text
配置管理员
    │
    ▼
Business Resource.card_template（暂存配置）
    │  手写关系路径 / One2many 循环
    │  字段选择器仅显示当前模型直接字段
    ▼
结构检查 → 显式 Apply / Publish 校验
    ▼
Published Configuration Snapshot
    ▼
Search Service 查得的当前用户可读主记录
    ▼
当前用户 ORM 环境下解析关系路径 / 读取循环项
    ▼
CC-014 共用格式化与纯文本渲染
    ▼
Result Card
```

```text
Order Lines:
{order_line}
  {product_id.name} × {product_uom_qty} = {price_subtotal}
{/order_line}
```

实际字段名必须以目标 Resource 当前映射模型的 Odoo 字段定义为准；以上销售订单字段
名称对应 `sale.order`，不得将示例名称当成所有 Resource 的通用字段。

## 2. Background and Acceptance Findings

### 2.1 起草前核对范围与方法

核对只读完成，未修改任何既有冻结文档、官方代码或数据库：

1. 对照 CC-014 §4~§8 的语法、设计器、Preview、Rendering、安全契约，以及其实际
   `## 9. Invariants`。CC-014 §14 实际是 Definition of Done；“§14 Invariants”是
   原始核对指令中的章节号偏差，本 CC 按实际标题追溯。
2. 检查现有 parser/renderer、Card serializer、Resource 配置模型和模板/配置测试。
3. 在已认证 Odoo 配置界面只读核对当前 Published Version 5 的 Resource→模型映射；
   关系类型示例取自仓库对应 Odoo 18 模型字段声明。字段示例仅证明模型存在该类型字段，
   不代表每个字段都已配置为 Searchable Field/Card 字段或当前用户均有权读取。
4. 对照 CC-003、TDD v0.4 及 CC-013，核实搜索、关系读取和打开记录的权限边界。
   没有直接查询或修改数据库。

| 核对对象 | 核对方法 |
|---|---|
| CC-014 现有契约 | 只读检查模板语法、Designer、Preview、Rendering、Security 和实际不变量章节 |
| 现有代码 | 只读检查 `services/template.py`、`services/card.py`、`services/executor.py`、`models/configuration.py` 及相关测试 |
| Published Configuration | 通过已认证 Odoo 配置界面只读检查当前 Published Version 5 的 Resource→模型映射；不直接读写数据库 |
| 模型关系字段 | 检查仓库 Odoo 18 模型字段声明，作为 Resource 模型关系类型示例 |
| CC-003 权限边界 | 只读检查 CC-003、TDD v0.4、CC-013 及现有 permission boundary/serializer 代码 |

### 2.2 CC-014 现有契约

核对对象为 [CC-014](./CC-014_result_card_template_designer.md)：

| 部分 | 现有冻结语义 | 对本 CC 的约束 |
|---|---|---|
| §4 Card Template Syntax | `{field_name[:format_key]}`；拒绝点号路径及循环 | 新增语法必须由本 CC 明确限定；不能改变已有单级 token 语义 |
| §5 Designer UI | 字段列表显示技术名、类型、标签；可拖放/手输 | 本 CC 的字段选择器只显示当前模型直接字段，不展开关联模型字段 |
| §6 Preview | 配置管理员普通 session；与生产共用 parser、授权、formatter 和 renderer | Preview 不得使用另一套关系解析或权限语义 |
| §7 Rendering | Published Snapshot 模板；使用服务端 locale/tz；纯文本；按既有空值/无权策略输出 | 关系值和循环项须遵循相同规则 |
| §8 Security | 不执行代码；关系读取须遵守当前用户 ORM ACL、Record Rule、公司边界；HTML 输出安全 | 不得把“来自 Search Service”解释成跳过关系读取授权 |
| §9 Invariants | 现有不变量编号为 CC14-INV-001~023 | 本 CC 仅增加关系扩展不变量，不重编号、不修改原文 |

### 2.3 现有代码与测试

| 位置 | 核查结果 | Implementation Gap |
|---|---|---|
| `mymodules/wd_global_search/services/template.py` | `_FIELD_NAME` 只接受单个字段名；parser 支持既有格式键、`\n`、`\t`、双花括号转义；变量校验逐个映射模型检查字段、类型、存储/related 属性及字段读取权限 | 拒绝点号路径、Many2many 展开、循环块；没有关系路径 AST/作用域验证 |
| `mymodules/wd_global_search/services/card.py` | `read_card_values` 读取当前模型标量字段；直接 Many2one 会读取关联记录并检查读取权限，之后由 `serialize_card_template` 格式化/渲染 | 不解析多级关系路径；不序列化 Many2many 值或 One2many 循环项 |
| `mymodules/wd_global_search/models/configuration.py` | `BusinessResource.card_template` 已进入快照；`_validate_configuration` 在 Apply/Publish 路径验证模板；快照和 checksum 受既有版本生命周期管理 | 校验只接受 CC-014 当前单级语法；没有本 CC 的关系类型、深度、循环限制和检查结果 |
| `mymodules/wd_global_search/services/executor.py` | Search 结果由当前用户 ORM 环境构造，调用 Card 取值/序列化路径 | 必须让新增解析复用此请求上下文，不能另起任意模型/记录读取入口 |
| `mymodules/wd_global_search/tests/test_template.py` | 有直接字段、格式化、转义、无权字段和直接 Many2one 读取测试 | 没有多级路径、关系集合、循环、作用域或关联行授权测试 |
| `mymodules/wd_global_search/tests/test_configuration.py` | 有 `stock.picking` Search Relation Path `move_ids.product_id`、`move_line_ids.lot_id` 用例 | 这些路径用于 Search 匹配子模型后返回主记录，不代表 Card 模板已有关系路径能力 |

CC-014 当前模板的 8 KiB UTF-8 长度上限、50 个变量 occurrence 上限、格式键 allowlist、
服务端 locale/tz、权限与 escaping 规则继续适用；本 CC 不提高或替代这些限制。

### 2.4 当前 Published Resource 模型与关系字段核对

当前 Published Version 5 在 Odoo 配置界面列出下列七个 Resource。表中的字段是对应
Odoo 18 模型定义中的代表性字段；不是对每个字段的发布可用性、字段 ACL 或数据可读性
作保证，且**仅为示例，不是完整字段清单**。字段选择器不得使用此静态示例表作为字段
allowlist；实际 Check/Publish 必须读取当前 Resource 模型元数据并逐段验证，不得硬编码
这些示例字段。

| Resource | 当前映射模型 | Many2one 示例 | Many2many 示例 | One2many 示例 |
|---|---|---|---|---|
| `warehouse` | `stock.warehouse` | `partner_id`、`company_id` | `route_ids`、`resupply_wh_ids` | `resupply_route_ids` |
| `storage_location` | `stock.location` | `location_id`、`company_id` | `child_internal_location_ids` | `child_ids`、`putaway_rule_ids` |
| `product` | `product.product` | `product_tmpl_id` | `product_template_attribute_value_ids` | `product_document_ids`、`packaging_ids` |
| `contact` | `res.partner` | `parent_id`、`country_id` | `category_id` | `child_ids`、`bank_ids` |
| `stock_picking` | `stock.picking` | `partner_id`、`location_id` | `favorite_user_ids` | `move_ids`、`move_line_ids` |
| `sale_order` | `sale.order` | `partner_id`、`currency_id` | `invoice_ids`、`tag_ids` | `order_line` |
| `purchase_order` | `purchase.order` | `partner_id`、`currency_id` | `invoice_ids` | `order_line` |

字段声明核对来源包括 Odoo 18 的 `addons/stock/models/stock_warehouse.py`、
`addons/stock/models/stock_location.py`、`addons/product/models/product_product.py`、
`odoo/addons/base/models/res_partner.py`、`addons/stock/models/stock_picking.py`、
`addons/sale/models/sale_order.py` 和 `addons/purchase/models/purchase_order.py`。
字段列表不得据此推定用户权限；发布校验和运行时读取仍需逐字段/逐关系检查。

### 2.5 CC-003 权限边界

[CC-003](./CC-003_global_search_permission_boundary.md) 和 [TDD §6](../../design/TDD_global_search.md)
建立以下既有规则：

- Search 主模型、记录、字段以及当前公司均使用当前用户环境和既有 ACL/Record Rule。
- `authorize_relation_path` 按路径逐段验证关系字段及目标模型读取权限；权限异常失败关闭。
- ORM 关系记录的读取仍须服从关联模型的 ACL、Record Rule 和公司边界。
- CC-013 打开原生 Form 时按当前用户重新授权；卡片模板不能替代或放宽导航授权。
- Search 的 Relation Path 是查询时匹配关联模型字段、命中后仍返回主模型记录；它不是
  可供 Card 模板任意遍历或绕过权限的预取数据。

因此，“关系数据来自 Search Service”“不新增权限过滤”只可定义为**不建立第二套模板
专属权限模型**。它不能取消新增关系读取所需的 CC-003 逐段字段/模型授权和普通 ORM
Record Rule 检查。任何无法证明安全的实现均不得 Publish。

### 2.6 Implementation Gap

模型元数据具备 Many2one、Many2many、One2many 字段，但 CC-014 模板 parser 当前只接受
单级字段；Card serializer 只处理其现有标量/直接 Many2one 情况。Search Relation Path
配置也不等于模板关系路径。当前缺少受限的关系类型解析、One2many 循环语法/作用域、
关联数据读取、关联字段格式化、安全测试以及对应 Publish 校验。

### 2.7 Existing Contract Support

- CC-001 的 Business Resource、Published Snapshot、显式 Apply/Publish 和 checksum 是唯一
  配置生命周期；本 CC 不增加第二套 Registry 或发布机制。
- CC-002 Search 返回的主记录、分页、cursor、counts 和错误协议不变。
- CC-003 是关系字段/记录读取的唯一权限边界。
- CC-007 继续处理 Search/渲染异常；本 CC 不定义新 API error envelope。
- CC-009 的服务端语言/时区格式化继续适用于关系值。
- CC-010 的 Published Snapshot/checksum 不可由 Workspace 改写。
- CC-012 的 Resource 选择、多选和 counts 不变。
- CC-013 的 Result Card 摘要与 Native Form 导航不变；打开记录仍重新授权。

本节为起草验收发现，不修改任何既有冻结文档。

## 3. Scope

### 3.1 In Scope

- Many2one 路径最多 3 个关系跳转，末端是支持的普通字段。
- Many2many 展示路径最多 2 个关系跳转：起始 Many2many，之后可有一个 Many2one，
  最终为普通字段；多值以 Resource 配置的分隔符连接。
- One2many `for` 块，最多 2 层嵌套；循环中允许常量、格式键以及受限的 Many2one/
  Many2many 字段路径。
- 路径/循环语法、作用域、关系类型、深度、模板循环块数、循环体长度及格式键的结构检查。
- 可见的模板结构检查操作，以及 Apply/Publish 时对完整配置重新执行服务端检查。
- 生产 Card 与 CC-014 Preview 共用 parser、权限边界、formatter 和 renderer。
- 关系字段的安全读取、空值行为、纯文本渲染、HTML 呈现边界 escaping 和测试。

### 3.2 Out of Scope

- 条件语句、分支、表达式、赋值、变量计算、函数调用、方法调用、索引或代码执行。
- 任意模型遍历、任意深度关系、Reference/Binary 关系、多模型模板选择。
- Many2many/Many2one 循环、One2many 变量路径或 Many2one→Many2many 混合路径。
- 修改搜索语义、Search Relation Path、Resource 选择、Action 导航、权限架构或错误协议。
- 修改 SRS、TDD、实施计划、CC-001~CC-014、官方 Odoo 核心或官方 addons。
- Elasticsearch、OpenSearch、LLM、向量检索、外部搜索引擎、`/nl_search`、新架构或
  `NOT_IMPLEMENTED` 响应。
- 根据真实业务数据预估循环/集合基数。按用户选择，本 CC 不设置每次关系展开的行数上限、
  截断或基数警告；结构检查不查询/展开业务数据。运行时性能仍受 CC-014 的性能门禁约束，
  不能以移除权限检查或静默截断来规避。

### 3.3 与 CC-014 的边界

CC-014 继续定义单级字段模板、设计器、Preview、基础格式化、HTML 安全和配置生命周期。
CC-014-1 只为其增加本文件明确定义的关系路径和 One2many 循环语法。原有变量、转义、
格式键、权限失败行为和序列化接口保持兼容。字段选择器只呈现当前模型直接字段；关联模型
的字段不得自动展开或作为字段树展示，关系路径由管理员手动输入并由服务端检查。

### 3.4 Compatibility and Migration

- 所有只使用 CC-014 单级语法的已发布模板必须继续有效，含义、格式化和权限行为不变；
  本 CC 不要求重写既有模板内容。
- 本 CC 新语法仅在对应实现通过完整验证并经现有配置生命周期显式 Apply/Publish 后生效；
  不自动发布、不迁移业务记录。
- 已有 Published Snapshot 若尚无 Many2many separator 值，按 CC-014-1 默认 `", "` 解释，
  不因升级而静默改写快照或 checksum。管理员显式保存/Apply separator 后才写入配置版本。
- 关系路径由管理员按 Odoo 技术字段名手动配置；不从 Search Relation Path 自动生成
  Card 模板，不迁移/复制 Search Relation Path。
- 任何无法保留旧单级模板行为的实现均触发 Stop Condition；旧活动 Snapshot 在失败时保持
  有效。

## 4. Relation Field Syntax

### 4.1 Grammar

```ebnf
template   := (text | variable | loop_block)*
variable   := "{" field_path [ ":" format_key ] "}"
loop_block := "{" field_name "}" loop_body "{/" field_name "}"
loop_body  := (text | variable | loop_block)*
field_path := field_name ( "." field_name )*
field_name := [A-Za-z_][A-Za-z0-9_]*
```

附加约束：

1. `loop_block` 的开/闭标签只接受单个字段名；该字段必须是当前作用域模型的直接
   One2many 字段。循环标签不能带点号路径或格式键。
2. 所有开/闭标签按栈匹配；同名嵌套标签按最近的未闭合标签配对。
3. `format_key` 必须是 CC-014 已定义的格式 allowlist；仅适用于末端普通字段。
4. 保留 CC-014 的常量语法：`\n` 为换行、`\t` 为制表符、`{{`/`}}` 为字面花括号；
   循环体内相同规则生效。
5. 模板仍遵守 CC-014 的 8 KiB UTF-8 长度及 50 个变量 occurrence 上限。
6. 不支持模板注释；注释样式文本若不属于合法变量/循环标签，只能作为普通常量显示，
   不具有屏蔽解析或绕过校验的作用。
7. 空格及其他未转义普通空白按常量原样保留；只有 CC-014 明确规定的 `\n`、`\t` 和
   花括号转义会转换。变量/循环标签内部不接受额外空白，模板全空白仍按 CC-014 规则拒绝。

### 4.2 Examples

```text
单级字段：{name}
Many2one 多级：{partner_id.city}
Many2one 三跳（`stock.warehouse`）：{partner_id.parent_id.country_id.name}
Many2many 多值：{category_id.name}
Many2many 后接 Many2one：{category_id.parent_id.name}
One2many 循环：{order_line}...{/order_line}
嵌套循环：{child_ids}...{child_ids}...{/child_ids}...{/child_ids}
带格式键：{order_line.price_subtotal:monetary}
```

`tax_ids` 只有在该 Resource 当前作用域中的字段类型确为 One2many 时才能作为循环字段；
Many2many `tax_ids` 不能写成 `for` 循环。关系路径字段名始终是 Odoo 技术字段名，不使用
显示标签。

### 4.3 Explicitly Rejected Syntax

以下均拒绝，不能按常量静默输出或退化为 Python 字符串：

```text
{partner_id.parent_id.parent_id.country_id.name} # stock.warehouse 上超过 Many2one 深度
{category_id.parent_id.grandparent_id.name}      # 超过 Many2many 深度
{order_line.product_id.name}                      # One2many 不能作为变量路径
{partner_id.category_id.name}                     # Many2one 后接 Many2many
{field if condition}                              # 条件/表达式
{method()}                                        # 函数/方法调用
```

## 5. Many2one Multi-Level Resolution

1. 路径从当前作用域模型的 Many2one 字段开始；后续每个非末端字段也必须为 Many2one。
2. **最大深度为 3 个 Many2one 关系跳转**；末端普通字段不计入关系深度。
3. 末端必须为 CC-014 支持且具有明确 formatter 的普通字段：Char、Text、Integer、
   Float、Date、Datetime、Boolean、Selection 或 Monetary。HTML、Binary、Reference、
   未知类型及任何关系字段不得作为路径末端。
4. 空的任一中间 Many2one 使该变量按 §10 空值规则显示 `—`。
5. 示例：
   - `{partner_id.city}`：1 次关系跳转。
   - `{partner_id.country_id.name}`：2 次关系跳转。
   - `{partner_id.parent_id.country_id.name}`（`stock.warehouse`）：3 次关系跳转。
6. `{partner_id.parent_id.parent_id.country_id.name}`（`stock.warehouse`）有 4 次关系跳转，Publish/Apply 必须
   拒绝。
7. 所有路径字段和目标模型必须在模板所属 Resource 的每个模型映射上可验证；不得按运行
   时结果模型猜测缺失字段或 formatter。
8. 每一段 Many2one 关系字段均须检查当前用户字段读取权限；每个目标模型/记录读取均须
   遵守 CC-003 和普通 ORM ACL/Record Rule/公司边界。若某段字段或中间记录无权访问，生产
   Card 按 CC-014 未授权变量规则输出空字符串，Preview 显示既有 `[无权访问]` 标记及权限
   警告；不得读取字段值或泄露无权节点的存在性。授权检查自身发生非预期错误时按既有
   失败关闭协议处理。

## 6. Many2many Multi-Level Resolution

1. Many2many 路径必须从当前作用域模型的 Many2many 字段开始；不允许在 Many2one 路径
   后接 Many2many。
2. 路径最多有 2 个关系跳转：Many2many 本身可直接到达普通字段，或之后经过最多一个
   Many2one 到达普通字段。
3. 多值按稳定关系记录顺序逐项格式化，以 Resource 的 Many2many separator 连接；默认值
   为 `", "`。管理员可在同一 Business Resource 配置其他纯文本分隔符；separator 作为
   此 Resource 的 Published Configuration 数据随既有 Snapshot/checksum 一起 Apply，
   不建立新的字段 Registry。
4. 若路径是 `{category_id.name}`，对每个可读 category 读取普通字段 `name` 并连接。
   `{category_id.parent_id.name}` 允许一个 Many2one 跳转。
5. `{category_id.parent_id.grandparent_id.name}` 包含 3 次关系跳转，拒绝。
6. 不允许一个变量路径含有两个 Many2many，也不允许 Many2many 后再接 One2many。
   Many2many 记录中的无权记录不得输出 ID、名称或数量；具体空值行为见 §10。
7. Many2many 成员顺序使用目标模型的既有 `_order`，同序时以 `id` 升序；不接受未定义的
   ORM 返回顺序，也不接受客户端提供的排序条件。

## 7. One2many For Loop

### 7.1 Loop Contract

- 循环字段只能是当前作用域模型上的直接 One2many 字段；Many2one 和 Many2many 不可循环。
- 循环字段本身必须检查当前用户字段读取权限。生产用户不能读取该字段时，不输出循环体；
  Preview 按 CC-014 显示 `[无权访问]` 并提示权限范围可能不同。不得通过集合长度、记录 ID、
  错误差异或 timing 泄露隐藏行是否存在。
- 每个循环项均须在当前用户普通 ORM 环境通过 ACL、Record Rule 和公司边界；不可读行不
  输出。若授权/过滤无法可靠完成，失败关闭，不得改用管理员环境或以宽松结果继续。
- 单层循环体的字段以该 One2many 子模型为当前作用域；支持常量、当前子模型字段及
  §5/§6 合法的关系字段路径。
- 嵌套循环只能引用当前循环项上的直接 One2many 字段；最多 2 层，包括外层和内层。
- 外层模板/当前循环作用域以外的字段不得出现在循环体中；嵌套循环体不得读取其父循环项
  的字段。循环体中的常量、转义和格式键按 §4 处理。
- 开闭标签字段名必须精确相同；未闭合、额外闭合、交叉配对或非 One2many 标签均拒绝。
- 每份模板最多 5 个静态 `loop_block`；循环体源文本最多 1000 个 Unicode code point。
  长度从开标签之后到匹配闭标签之前计算，包含嵌套块文本/标签，不含本层开闭标签，
  且在转义解码前计数。
- 每次循环处理所有当前用户可读的关联行；本 CC 不设运行时迭代行数上限，不截断，也不
  在 Preview/Publish 时读取业务记录来估算行数。适用的性能门禁及 Odoo ORM/请求超时仍
  生效。

### 7.2 Examples

简单循环（`sale.order.order_line` 为 One2many）：

```text
订单行：
{order_line}
- {product_id.name} × {product_uom_qty} = {price_subtotal:monetary}
{/order_line}
```

带循环外标题与常量：

```text
订单明细：
{order_line}
  - 产品：{product_id.name}；数量：{product_uom_qty}
{/order_line}
```

嵌套循环示例使用 `res.partner.child_ids`，其当前循环项仍是 `res.partner`：

```text
下级联系人：
{child_ids}
- {name}
  下级联系人：
  {child_ids}
  -- {name}
  {/child_ids}
{/child_ids}
```

循环中多级解析与格式键：

```text
{order_line}
- {product_id.name}，小计 {price_subtotal:monetary}
{/order_line}
```

实际 Publish 校验须针对 Resource 当前模型字段元数据；若字段不存在、类型不符合或不在
当前作用域，则拒绝，不能因示例有效而放宽。

## 8. Depth and Type Limitation

| 表达式类型 | 最大关系深度 | 可接受路径/作用域 |
|---|---:|---|
| Many2one | 3 个关系跳转 | 仅 Many2one 中间字段，普通字段末端 |
| Many2many | 2 个关系跳转 | 起始 Many2many，可接最多 1 个 Many2one，普通字段末端 |
| One2many | 2 层循环嵌套 | 循环字段须为当前作用域直接 One2many |
| Many2one 后接 Many2many | 不支持 | 拒绝 |
| Many2many 后接第二个 Many2many | 不支持 | 拒绝 |
| Many2many 后接 One2many | 不支持 | 拒绝 |
| One2many 循环项内 Many2one/Many2many 路径 | 依 §5/§6 | 以当前循环项模型作为路径根 |
| One2many 变量路径（不在循环块中） | 不支持 | 拒绝 |

Many2many→Many2one 的示例 `category_id.parent_id.name` 是唯一被允许的跨类型多值路径
形态之一；“Many2one + Many2many 不允许”具体指路径先从 Many2one 开始后再遇到
Many2many。

## 9. Rendering

1. 生产模板只从当前 Resource 的活动 Published Snapshot 读取；Preview 使用 CC-014 规定
   的待检查草稿输入，但调用相同 parser、权限、formatter 和 renderer。
2. 常量按模板顺序输出；变量先按作用域解析路径，再格式化末端普通字段；循环按
   One2many 记录集的确定顺序逐项渲染并拼接。
3. 关系记录使用 Odoo 模型既有 `_order`；同序时以 `id` 升序作为确定性次序。不得依赖
   未定义的数据库返回顺序。
4. Many2many 各可读成员的格式化文本使用 §6 的 separator 连接；不得使用客户端语言/
   时区或 Python 对象 `repr()`。
5. 格式键、空值、布尔值、货币、日期、时间和 Selection 标签复用 CC-014 formatter，
   使用当前服务端用户 `lang`/`tz`。
6. 关系字段、关联记录和字段值只通过当前用户普通 ORM 环境读取；无权值不得进入模板
   中间输出、缓存、日志或错误详情。
7. 空循环不输出任何循环体文本；循环外常量仍按其原位置显示。
8. 渲染为纯文本。数据进入 HTML 呈现边界时按 CC-014 规则 escape 一次，前端以文本节点
   显示；JSON/plain-text 层不得提前或重复 escape。
9. 解析/读取/格式化异常沿用 CC-007/CC-014 的安全错误处理；不得回退到原始 ID、异常
   字符串、Python `str()` 或成功形状默认值。

### 9.1 Performance Verification

本 CC 不另设或放宽性能阈值，继承 CC-014 §7.3：模板解析 P95 ≤10 ms、单 Card 模板渲染
P95 ≤50 ms、Publish/Apply 校验 P95 ≤100 ms、Preview 端到端 P95 ≤500 ms。关系读取和循环
渲染计入对应阶段，不得把单 Card 预算改为更宽的阈值。每项性能验证至少采集 100 次样本，
记录环境、fixture 数据量、冷/热状态及 P95；若关系数据量导致预算不满足，触发 Stop
Condition 和影响评审，不得临时截断数据或跳过权限检查。

## 10. Empty Handling

| 情况 | Search Result Card | Preview |
|---|---|---|
| Many2one 中间关系为空 | 该变量显示 `—` | `—` |
| Many2one 路径末端字段为空 | `—`；Boolean `False` 除外 | 同生产 formatter |
| Many2many 没有可读成员 | `—` | `—` |
| Many2many 有部分不可读成员 | 只连接可读成员，不输出隐藏成员/ID/数量 | 同当前管理员权限；显示既有权限警告 |
| One2many 循环为空 | 不输出循环体；循环外常量保留 | 同生产语义 |
| One2many 有部分不可读记录 | 仅迭代当前用户 ORM 可读记录；不输出隐藏记录占位/数量 | 同当前管理员权限 |
| 当前用户无权读取某字段/关系 | 生产按 CC-014 未授权变量规则输出空；不读值、不泄露拒绝细节 | 按 CC-014 显示 `[无权访问]` 并保留权限警告 |
| Boolean 值为 `False` | 按当前语言格式化为“否”，不是空值 | 同生产 formatter |

Record Rule 过滤后的零条记录与真实空集合均不得通过计数、ID、错误形状或隐藏 metadata
区分。对权限拒绝不做静默宽松回退；权限异常与系统异常按既有安全错误契约处理。

## 11. Interaction with Other Features

- **循环中的多级解析：** 路径根是当前循环项模型；路径深度/类型仍分别受 §5/§6 约束。
- **循环中的格式键：** 格式键只作用于路径末端普通字段，使用 CC-014 服务端 formatter。
- **循环中的常量和转义：** 常量顺序、`\n`、`\t`、`{{`、`}}` 与循环外语义相同。
- **多级解析中的格式键、常量和转义：** 保持 CC-014 的既有定义；未知格式键拒绝。
- **设计器字段列表：** 仅展示当前 Resource 当前作用域模型的直接字段名、字段类型、标签；
  不展开或枚举关联模型字段。管理员可手动输入点号路径，Check/Publish 对每一段验证。
- **结构检查：** `Check Template` 只解析/校验语法、字段路径、字段类型、作用域和静态
  限制；不读取真实业务记录、不计算关联基数。Apply/Publish 再次执行相同服务端检查。
- **Preview：** 仍使用配置管理员当前 session 和 CC-014 的权限警告；记录切换/模板变化时
  用共享 renderer 刷新，不访问 Action XML ID。
- **Search Relation Path：** 仍仅负责查询时关系匹配及主记录返回；不能与 Card 的
  `{field_path}` 混为同一个配置或权限入口。
- **导航与 Resource：** CC-012 Resource Selector 和 CC-013 Native Form 导航/打开时授权
  完全不变；卡片模板不能改变 Result Identity、Action 或目标记录。

## 12. Security

1. 多级解析和循环只从 Search Service 已选中的主记录出发；模板不能提交模型名、记录 ID、
   domain、context、Action XML ID 或关系目标 ID。
2. 关系数据虽由 Search Service 请求触发，但 CC-003 当前授权的主记录不等于其所有关联
   记录自动获准。每个关系字段必须检查当前用户字段读取权限；每个目标模型须有 read ACL；
   关联记录读取必须通过普通 ORM 并服从 Record Rule 和公司边界。
3. 复用 CC-003 的既有权限边界与 Odoo ORM 访问控制，不建立独立模板权限体系。禁止
   `sudo()`、superuser/admin env、绕过 Record Rule 的读取或直接数据库读取。
4. 当前用户不能读取某关系字段/目标记录时，不访问或输出该值；Many2many/One2many 仅
   序列化授权可见记录。任何授权检查无法完成时失败关闭，不能以空值掩盖非授权异常或泄露
   部分未授权数据。
5. 配置管理员 Preview 只使用其普通 session 权限；Preview 不读取/返回 Record Rule
   定义，不绕过规则，不访问 Action XML ID，不产生业务写入/副作用。
6. 模板只作纯文本替换；禁止 `eval`、`safe_eval`、Python/QWeb/Jinja 表达式、JavaScript、
   SQL、条件、函数、方法和任意对象属性访问。
7. 所有常量和字段值均视为不可信文本；HTML 呈现边界 escaping，客户端只用文本节点/
   `textContent`，禁止 `innerHTML` 或可执行标记。
8. 关系读取新增的查询/渲染工作不得以删除权限检查、缓存跨用户值或泄漏模板内容/字段值
   到日志来满足性能目标；日志继续遵循 CC-008 allowlist。

## 13. Invariants

| ID | 冻结不变量 |
|---|---|
| CC14-1-INV-001 | 变量多级路径只支持 Many2one 与 Many2many；One2many 只能使用循环块。 |
| CC14-1-INV-002 | Many2one 路径最多 3 个关系跳转，末端字段不计入深度。 |
| CC14-1-INV-003 | Many2many 路径最多 2 个关系跳转，且最多包含一个 Many2many。 |
| CC14-1-INV-004 | 每个多级路径末端必须是 CC-014 支持且有确定 formatter 的普通字段。 |
| CC14-1-INV-005 | 变量路径不得包含 One2many、循环标签或任意未允许的关系类型。 |
| CC14-1-INV-006 | Many2many 可读值使用 Resource 的 separator 连接，默认 `", "`。 |
| CC14-1-INV-007 | For 循环字段只允许当前作用域的直接 One2many 字段。 |
| CC14-1-INV-008 | One2many 循环最大嵌套深度为 2 层。 |
| CC14-1-INV-009 | 循环体变量只引用当前循环项模型的字段或其允许路径。 |
| CC14-1-INV-010 | 循环体不得引用循环外/root 字段或父循环项字段。 |
| CC14-1-INV-011 | 单个模板静态循环块最多 5 个。 |
| CC14-1-INV-012 | 单个循环体最多 1000 个 Unicode code point，按 §7.1 计数。 |
| CC14-1-INV-013 | 空循环不输出任何循环体内容。 |
| CC14-1-INV-014 | 循环只从 Search Service 选出的主记录出发，并在同一请求的当前用户 ORM 环境解析。 |
| CC14-1-INV-015 | 不建立循环专属/平行权限模型；循环读取仍必须通过 CC-003 既有逐段授权及 ORM 规则。 |
| CC14-1-INV-016 | 多级解析以 Search Service 选出的主记录为根，不接受模板/客户端提供的任意 root。 |
| CC14-1-INV-017 | 多级解析不建立新的权限系统，但不得跳过 CC-003 字段、模型、记录规则和公司边界检查。 |
| CC14-1-INV-018 | 每个循环开始与结束标签必须按栈精确匹配。 |
| CC14-1-INV-019 | 模板不得含有未闭合、额外闭合或交叉匹配的循环。 |
| CC14-1-INV-020 | 允许循环体与受限多级解析、格式键、常量和转义交互。 |
| CC14-1-INV-021 | 多级解析及循环结果为纯文本，不执行模板内容。 |
| CC14-1-INV-022 | 多级解析及循环结果在 HTML 呈现边界必须 HTML-escape，客户端以文本节点显示。 |
| CC14-1-INV-023 | 本 CC 不新增权限授予路径；不能证明沿用 CC-003 时不得发布。 |
| CC14-1-INV-024 | 每次关系展开不设迭代行数上限、不截断；遵循既有请求/性能门禁。 |
| CC14-1-INV-025 | 字段选择器仅显示当前作用域模型的直接字段，不展开关联模型字段。 |
| CC14-1-INV-026 | 结构检查不读取业务数据、不估算真实关系基数；Apply/Publish 必须重复服务端结构校验。 |
| CC14-1-INV-027 | CC-014 的 8 KiB 模板字节限制、50 个变量 occurrence 上限、formatter 和 Published 生命周期不变。 |

“不需要额外权限过滤”在 INV-015/017 中仅表示不新建平行/模板专属授权方案；其绝不表示
取消关联字段、目标模型或关联记录的既有授权与 Record Rule 检查。

## 14. Publish-time Validation

草稿可保留不完整文本继续编辑。`Check Template`、Apply 和 Publish 均调用服务端验证；
Apply/Publish 对完整 Resource 配置重复验证。存在任一错误时，不得更新 Published
Snapshot/checksum，pending change 保留，旧活动快照继续生效，按既有配置错误语义返回
明确、可操作诊断。

1. 模板非空；UTF-8 长度不超过 CC-014 的 8 KiB。
2. 变量 occurrence 不超过 CC-014 的 50；静态循环块不超过 5。
3. 字段名、格式键、常量转义、循环开始/结束标签均符合语法。
4. 每段字段在当前作用域模型存在；路径每一段的 relation type 与深度符合 §5/§6/§8。
5. 每条路径末端为允许的普通字段；字段类型、格式键和 formatter 策略完整。
6. 每个关系字段和目标模型有适用的 CC-003 权限检查策略；运行时仍按当前 Search 用户
   重新授权。
7. One2many 循环字段是当前作用域的直接 One2many；嵌套深度不超过 2；变量作用域合法。
8. 每个循环体按 §7.1 计数不超过 1000 个 Unicode code point。
9. Resource 的每个模型映射均能解析同一模板的路径、字段类型与格式；不能通过运行时
   `_model` 动态猜字段。
10. Many2many separator 是配置中允许的纯文本值；不能被解析为模板代码/格式表达式。
11. 新模板仍符合 CC-014 的字段权限、空值、安全、escaping、Snapshot 和迁移规则。
12. 结构检查、Preview 和 Publish **不**读取业务记录、不展开 Many2many/One2many、不估算
    关联行数，也不针对关联数据量给出警告。实际循环展开量遵循 INV-024；性能验证按
    §15/§18 进行，若超过既有性能门禁则停止并评审，不得私自加入截断或跳过权限的 fallback。

### 14.1 Structure Check Contract

`Check Template`、Apply 和 Publish 必须调用同一服务端结构 validator；Check 结果不得替代
Apply/Publish 对完整 Resource 配置的重新校验。结构检查逐项验证：

- 模板语法、常量转义、注释/空白处理及 CC-014 长度/变量 occurrence 上限；
- 每个字段路径段的存在性、当前作用域、关系类型、深度和目标模型；
- 末端字段类型、格式键兼容性及 formatter/权限策略完整性；
- 循环标签匹配、循环字段 One2many 类型、静态循环块数、嵌套深度和循环体长度；
- 循环变量的当前项作用域，拒绝 root/父循环项字段；
- Many2many separator 为允许的纯文本配置，并参与同一 Resource 的 Published 生命周期；
- Resource 的每个映射模型都能验证同一模板。

结构检查只读取配置与模型字段元数据，不执行业务模型 `search`/`search_read`/`read`，不
实例化关系记录，不读取业务记录、不展开集合、不估算实际行数。字段权限策略的完整性可以
按既有配置/模型元数据检查；实际用户的读取授权仅在 Preview/Search 渲染时按当前用户执行。

## 15. Test Matrix

所有测试使用隔离 ORM fixture 和当前用户环境；权限测试不得使用 `sudo()` 证明结果。模板
结构用例应同时执行 validator 和 Apply/Publish 入口，确认无效配置不更新 Snapshot/checksum。

| ID | 可执行场景 | 通过标准 |
|---|---|---|
| CC14-1-TEST-001 | 以 `stock.warehouse` fixture 渲染 `{partner_id.name}` | 1 跳 Many2one 返回已授权 `name`，格式正确 |
| CC14-1-TEST-002 | 渲染 `{partner_id.country_id.name}` | 2 跳结果匹配当前用户可读关系 |
| CC14-1-TEST-003 | 渲染 `{partner_id.parent_id.country_id.name}` | 3 跳可发布并正确渲染 |
| CC14-1-TEST-004 | 尝试 4 跳 `{partner_id.parent_id.parent_id.country_id.name}` | Check/Publish 明确拒绝，Snapshot/checksum 不变 |
| CC14-1-TEST-005 | 以 `res.partner.category` fixture 渲染 `{category_id.name}` | 单 M2M 跳转的所有可读名称按 separator 拼接 |
| CC14-1-TEST-006 | 渲染 `{category_id.parent_id.name}` | M2M+1 M2O 合法，结果顺序及格式确定 |
| CC14-1-TEST-007 | 尝试 `{category_id.parent_id.parent_id.name}` | 超 2 跳拒绝 |
| CC14-1-TEST-008 | 尝试从 Many2one 起始后继续 Many2many 的路径 | 类型组合拒绝，错误定位到具体路径 |
| CC14-1-TEST-009 | 将 Many2one/Many2many/One2many 关系字段作为多级变量末端 | 全部拒绝；只接受允许的普通字段末端 |
| CC14-1-TEST-010 | 将 One2many 写成 `{order_line.product_id.name}` | 拒绝变量路径，提示须使用循环块 |
| CC14-1-TEST-011 | 用两个 `sale.order.line` fixture 执行简单 `{order_line}...{/order_line}` | 两行均按确定顺序渲染 |
| CC14-1-TEST-012 | 在循环前写标题常量，再渲染 `order_line` | 标题原位置保留；循环为空时标题仍在、循环体不出现 |
| CC14-1-TEST-013 | 用 `res.partner.child_ids` 嵌套 `child_ids` 两层 | 内外层各自渲染正确，标签按栈配对 |
| CC14-1-TEST-014 | 构造三层 One2many 循环 | Check/Publish 拒绝，活动 Snapshot 不变 |
| CC14-1-TEST-015 | 在循环体引用子模型存在字段及其合法关系路径 | 按当前循环项渲染，不能误用 root 模型解析 |
| CC14-1-TEST-016 | 在循环体引用 root-only 字段或父循环项字段 | Check/Publish 拒绝并指出作用域错误 |
| CC14-1-TEST-017 | 对 One2many 空集合渲染循环块 | 循环体输出长度为零，外部常量仍可见 |
| CC14-1-TEST-018 | 在循环项中使用 `{product_id.name}` | 与当前行 product 关联匹配，不跨行/跨 Resource |
| CC14-1-TEST-019 | 在循环项中对金额变量指定 `:monetary` | 使用当前用户 locale/currency helper，错误格式拒绝 |
| CC14-1-TEST-020 | 循环体含常量、`\n`、`\t`、`{{`、`}}` | 转义行为与 CC-014 一致，常量不被解释为模板代码 |
| CC14-1-TEST-021 | 循环体含 `<script>` 文本及含 HTML 特殊字符的字段值 | renderer 保留纯文本语义；HTML 展示不执行标记 |
| CC14-1-TEST-022 | 生成 6 个静态循环块（即使对应数据为空） | Check/Publish 因块数超限拒绝 |
| CC14-1-TEST-023 | 构造循环体 1001 个 Unicode code point（包括嵌套标签计数规则） | 拒绝；1000 code point 边界样例可通过 |
| CC14-1-TEST-024 | 开标签和闭标签名称不同或顺序不匹配 | Check/Publish 拒绝，错误指出标签 |
| CC14-1-TEST-025 | 缺失闭标签或多余闭标签 | Check/Publish 拒绝，不将标签输出为常量 |
| CC14-1-TEST-026 | 将多级变量/循环输出送入真实 HTML 呈现边界 | 每个文本节点安全显示，escape 恰好一次，无执行/双重实体显示 |
| CC14-1-TEST-027 | 通过 Search Service 搜索根记录并渲染已发布模板 | 根记录来自当前 Search 结果及 Published Snapshot，不接受客户端 root ID |
| CC14-1-TEST-028 | 使用搜索到的订单执行 `order_line` 循环 | 子行从同一 Search 请求/用户 ORM 环境解析；不可提交任意 relation ID/domain |
| CC14-1-TEST-029 | 普通用户不可读某个中间模型或中间字段 | 不读取/输出被拒绝值；遵守 CC-014/CC-003 安全结果，不以管理员权限回退 |
| CC14-1-TEST-030 | 为 One2many 子记录配置用户 Record Rule，仅允许部分行 | 只渲染 ORM 可读行；不输出被屏蔽行 ID、字段或计数；异常失败关闭 |
| CC14-1-TEST-031 | 对同一模板分别运行 Preview 和生产 Search Card | 两者复用 parser/formatter/权限语义；Preview 仅有 CC-014 管理员权限警告差异 |
| CC14-1-TEST-032 | 从含循环 Card 双击/快捷打开结果 | CC-013 仍按 Resource/record 重新授权并打开 configured Native Form；模板不改 Action |
| CC14-1-TEST-033 | 多级关系中间节点、末端字段及 M2M 集合分别为空 | 按 §10 显示 `—`；Boolean False 仍格式化为“否” |
| CC14-1-TEST-034 | 对同一 Many2many 设置默认及 Resource 自定义 separator，含等序记录 | 使用配置 separator、稳定 `_order`/id 顺序；separator 随 Snapshot/checksum Apply |
| CC14-1-TEST-035 | 组合合法 M2O、M2M、O2M 及非法混合路径矩阵 | 所有 §8 允许项通过、拒绝项明确失败；Search counts/pagination/error envelope 不变 |
| CC14-1-TEST-036 | 对 Check Template 使用仅有模型元数据、业务模型 `search/read` 被测试 spy 拒绝调用的 fixture | 合法模板仍完成结构检查，spy 确认未读取/展开业务记录；无效语法/路径得到明确诊断 |
| CC14-1-TEST-037 | 对相同 Resource/template 分别执行 Check Template 与 Apply/Publish | 模板结构诊断一致；无效模板不能更新活动 Snapshot/checksum；有效模板通过完整配置校验后仅由显式 Apply/Publish 生效 |
| CC14-1-TEST-038 | 对关系路径、Many2many 和 One2many 循环分别采集至少 100 次渲染样本 | 记录 fixture 量、环境和冷/热状态；各阶段 P95 符合 §9.1 继承的 CC-014 预算，否则触发 Stop Condition |

## 16. Regression Requirements

- **CC-014：** 单级字段、模板编辑/插入、实时 Preview、渲染、格式键、权限警告、空值和
  HTML escaping 保持；关系支持不改变原单级语义。
- **CC-013：** Result Card identity、单击选择、双击/快捷打开、新 Tab、Native Form 及打开时
  当前用户重新授权保持。
- **CC-012：** Resource Selector、多选、资源顺序和 count 语义不变。
- **CC-003：** 当前用户、公司、模型/记录/字段/逐段关系权限、Record Rule、失败关闭保持；
  不通过 `sudo()` 或自建权限捷径。
- **CC-007：** EMPTY、PARTIAL_SUCCESS、FAILED、TIMEOUT、错误唯一性和安全错误结构保持。
- **CC-008：** 日志字段 allowlist、audit 语义保持；不记录模板原文、关系值、记录 ID 或
  权限拒绝详情。
- **CC-009：** label、Selection、数字、货币、日期/时间的服务端语言/时区来源唯一。
- **CC-010：** Published checksum、版本及不可由 Workspace 改写的语义保持；separator 与
  模板一起进入现有 Snapshot。
- **CC-002：** resources 数组、分页、cursor、counts、Result Identity 和错误结构兼容；
  关系模板不扩张/收缩 Search 命中集合。
- **TDD v0.4 Relation Path：** Search 的关联字段匹配仍返回 Primary Model，不与模板路径
  解析混用。

## 17. Stop Conditions

遇到任一情形不得直接实施或 Publish，须停止并进行对应安全/影响评审：

1. 无法在 Apply/Publish 时对模板路径、字段类型、标签、深度或作用域进行完整验证。
2. 任一关系跳转的模型/字段类型无法从当前 Resource 模型元数据确定。
3. 路径超过既定深度、末端是关系/不支持字段，或混合关系类型不在 §8 allowlist。
4. 循环不是直接 One2many、循环嵌套/块数/体长度超限或标签不匹配。
5. 循环体出现 root/父循环作用域外字段，且无法被服务端可靠拒绝。
6. 无法证明每段关系字段、目标模型及关联记录均遵循 CC-003/普通 ORM 权限。
7. 需要 `sudo()`、superuser/admin env、直接数据库读写、绕过 ACL/Record Rule 或增加
   未批准业务权限。
8. 需要修改 SRS、TDD、实施计划或既有冻结 CC 才能满足要求，且未完成影响评审。
9. 需要引入 LLM、向量检索、外部搜索引擎、任意代码执行、`/nl_search` 或新架构。
10. 无法复用 CC-014 formatter、Published Snapshot、错误协议或 HTML escaping。
11. 不受限展开使既有 CC-014 性能预算/CC-002 请求时限无法满足。不得自行截断或移除
    权限检查来通过；应停止并请求影响评审。
12. 无法证实关系数据来自当前 Search root 且同一用户 context，或实现依赖客户端提供关系
    ID/domain/model/Action。
13. `Check Template` 的结构检查调用业务记录查询/读取、检查与 Apply/Publish 使用不同且不
    一致的 validator，或任一结构校验失败仍允许更新活动 Snapshot。

## 18. Definition of Done

- Many2one 最多 3 跳、Many2many 最多 2 跳及末端普通字段规则可验证、可渲染。
- One2many 循环仅支持直接关系字段，最多 2 层嵌套，字段作用域严格。
- 每模板最多 5 个循环块、每循环体最多 1000 Unicode code point；现有模板字节/变量上限
  保持。
- Many2many separator 可配置、默认 `", "` 并随 Published Snapshot/checksum 生效。
- 字段选择器只显示当前模型直接字段；Check/Apply/Publish 服务端检查语法/字段/结构，
  不展开关联字段、不读取业务数据、不估算基数。
- 按本 CC 用户决定，不设置每次关系展开行数上限、不截断；在既有性能门禁及当前用户
  权限边界内读取。
- 关系查询/循环渲染的 P95 性能验证继承 CC-014 §7.3 阈值，至少 100 个样本并记录环境/
  fixture/冷暖状态；未达标时停止评审，不擅自放宽预算。
- 空关系、无权字段、Record Rule、formatter、locale/tz、HTML-escape 和错误行为正确。
- CC14-1-TEST-001~038 全部通过并保存可复验测试证据。
- CC-002~CC-014 回归通过，尤其 CC-003、CC-007、CC-010、CC-012、CC-013。
- 完成 IHR、ATR、HVR；不修改 SRS/TDD/实施计划/既有 CC，不改官方代码或直接访问数据库。

## 19. Decisions

| ID | 决策 | 替代方案 | 理由 |
|---|---|---|---|
| CC14-1-DEC-001 | 多级变量只支持 Many2one/Many2many | 任意关系遍历 | 限定读取范围并可静态验证 |
| CC14-1-DEC-002 | Many2one 最多 3 个关系跳转 | 无限制或按环境动态 | 有界解析、审查和测试 |
| CC14-1-DEC-003 | Many2many 最多 2 个关系跳转 | 允许任意多值链 | 限定组合与多值扩张 |
| CC14-1-DEC-004 | 末端必须是受支持普通字段 | 直接显示关系对象/任意对象 | formatter 输入类型确定 |
| CC14-1-DEC-005 | One2many 不能写成变量路径 | 当作 Many2many 拼接 | 多行内容必须显式使用循环结构 |
| CC14-1-DEC-006 | Many2many 值用 Resource separator 连接，默认 `", "` | 固定不可配置分隔符 | 满足可读展示并允许业务配置 |
| CC14-1-DEC-007 | For 循环只允许直接 One2many | 允许任意关系循环 | One2many 语义唯一且可验证 |
| CC14-1-DEC-008 | 循环最多 2 层嵌套 | 任意递归循环 | 防止模板结构不可控 |
| CC14-1-DEC-009 | 循环体以当前循环项作为字段作用域 | 隐式继承 root 所有字段 | 防止作用域歧义与跨行混读 |
| CC14-1-DEC-010 | 循环体不引用 root 或父循环项字段 | 任意外层变量捕获 | 作用域简单、静态可验证 |
| CC14-1-DEC-011 | 单模板最多 5 个静态循环块 | 不限循环块 | 限制语法复杂度 |
| CC14-1-DEC-012 | 单循环体最多 1000 Unicode code point | 仅使用模板总长度限制 | 对循环内复杂度给出单独可测约束 |
| CC14-1-DEC-013 | 空循环不输出循环体 | 输出占位文本/错误 | 保持模板文本可组合且不伪造数据 |
| CC14-1-DEC-014 | 循环项仅从 Search root 的当前用户 ORM 环境解析 | 客户端传入关联 ID | 保持数据来源与请求身份可信 |
| CC14-1-DEC-015 | 不新增循环专属权限系统，沿用 CC-003/ORM | 由模板自行授予或检查另一套角色 | 避免平行权限架构，但不免除逐段授权 |
| CC14-1-DEC-016 | 多级解析以 Search Service 选中主记录为唯一 root | 模板任意选记录/模型 | 不扩张 Search 结果或数据范围 |
| CC14-1-DEC-017 | 不增加模板专属字段授权机制；现有授权仍必须执行 | 假定关联数据自动可读 | 与 CC-003 当前用户边界兼容 |
| CC14-1-DEC-018 | 循环开始/结束标签必须精确匹配 | 宽松恢复/输出标签 | 解析失败必须显式，不产生成功形状错误内容 |
| CC14-1-DEC-019 | 未闭合/额外闭合/交叉循环均拒绝 | 自动补齐或忽略 | 防止意外渲染及绕过校验 |
| CC14-1-DEC-020 | 循环可与受限多级解析、格式键、常量、转义交互 | 限制循环为纯变量 | 满足 Card 实际表达需求且沿用既有安全语法 |
| CC14-1-DEC-021 | 输出继续为纯文本 | 允许模板 HTML | 防止 XSS 与可信标记注入 |
| CC14-1-DEC-022 | HTML 呈现边界 escaping，复用 CC-014 | 在 renderer/API 多次转义 | 防止执行标记和双重编码 |
| CC14-1-DEC-023 | 不建立新的权限授予路径 | 模板权限绕过 | 保持 CC-003 唯一安全边界 |
| CC14-1-DEC-024 | 不设置实际关联行数上限、不截断；结构检查不算基数 | 静态/运行时上限或基数警告 | 用户选择不限制展开数据量；性能超门禁时停下评审，不私自降级 |
| CC14-1-DEC-025 | 字段选择器只列当前模型直接字段，不展开关系字段 | 自动展开关联模型字段树 | 用户明确要求保持列表只显示当前模型字段；路径由管理员手写并验证 |
| CC14-1-DEC-026 | 增加结构 Check；其不读取业务数据，Apply/Publish 重复校验 | Check 时扫描关系数据或只在运行时发现 | 管理员可主动发现语法/字段/循环错误且无额外数据读取 |
| CC14-1-DEC-027 | Many2many separator 与模板同属 Resource Published Configuration | 独立 separator registry 或客户端配置 | 保持配置生命周期和 checksum 单一权威 |
| CC14-1-DEC-028 | 稳定关系顺序用目标模型 `_order`，同序以 `id` 升序 | 依赖未定义 ORM 返回顺序 | Preview/生产同输入可重复得到同序文本 |
| CC14-1-DEC-029 | Check、Apply、Publish 共享结构 validator；Check 仅读配置/元数据，绝不读取业务记录 | 只在运行时发现或检查时扫描关联记录 | 同一规则可提前反馈且不会额外读取业务数据 |

## 20. Implementation Structure

按起草时已核实的代码结构，以下是**现有接线点建议**，不是冻结文件清单、新 API 路径或
新架构要求：

| 现有接线点 | 建议职责 |
|---|---|
| `services/template.py` | 扩展 parser/AST、关系路径语法、作用域、深度/循环限制和结构诊断；复用现有 format allowlist |
| `services/card.py` | 扩展 `read_card_values`/serializer，在当前 ORM 环境解析关系值、集合顺序、循环项、separator 和既有 formatter |
| `services/permission_boundary.py` | 优先复用现有逐段授权 helper；仅在证明接口覆盖不足时做最小扩展，不形成第二套授权系统 |
| `services/executor.py` | 将 Search 当前用户环境与 root record 传给既有 Card 序列化链路；不接受客户端关系 ID/domain |
| `models/configuration.py` | 扩展现有 Resource 模板校验/Published Snapshot；Apply/Publish 复用结构 validator；若需持久化 separator，将其置于同一 Resource/Snapshot lifecycle，不建新 Registry |
| 现有 Designer/Preview 接线 | 字段选择器显示当前作用域模型直接字段；提供结构 Check，并继续调用 CC-014 共享 Preview/renderer；Check 仅校验配置与模型元数据 |
| 现有模板/配置/权限测试 | 在既有测试结构扩展关系/循环测试；只有维护性需要时才增设聚焦测试文件 |

实现不得提前冻结 API URL、Controller 路由、具体新文件名、ORM 查询策略或前端组件结构；
必须遵守 CC-001~CC-014 接口和停机条件。

## 21. Appendix

### 21.1 Traceability Matrix

| 来源/接口 | 本 CC 追溯 |
|---|---|
| SRS v1.5 / TDD v0.4 / Implementation Plan v0.3 | 采用当前冻结配置、Search、权限和版本生命周期；不改其文本 |
| CC-001 / CC-010 | §2、§9、§14、§16、§19：同一 Published Snapshot/Apply/checksum |
| CC-002 | §2、§12、§15、§16：根记录、分页、cursor、counts 和错误结构不变 |
| CC-003 | §2、§12、§13、§15、§16：当前用户、逐跳关系、记录规则、公司边界、失败关闭 |
| CC-007 / CC-008 | §9、§12、§15~§17：错误和日志协议不变 |
| CC-009 | §9~§11、§15~§16：服务端语言/时区 formatter 唯一 |
| CC-012 / CC-013 | §2、§11、§15~§16：Resource selection 和重新授权导航不变 |
| CC-014 §4~§9 | §2~§4、§9~§14、§16：在单级语法、设计器、Preview、安全和格式化之上做受限扩展 |
| DDD | N/A：本 CC 不引入新架构或独立服务 |

### 21.2 Interface Contract

- **输入：** 当前 Published Resource 模板、Resource 模型映射、当前 Search 用户 ORM 环境、
  Search Service 选中的 root record。
- **关系解析：** 按已验证路径/循环 AST 读取；关系字段、关联模型和记录均按 CC-003/ORM
  当前权限处理。
- **输出：** 纯文本渲染结果；只有已授权值；沿用 CC-014 formatter、空值语义和 HTML
  呈现边界 escaping。
- **失败：** 配置结构错误在 Check/Apply/Publish 显式报告且不改活动 Snapshot；运行时错误
  使用 CC-007/CC-014 既有安全错误处理，不返回内部 traceback/值/权限详情。
- **不变量：** 不接受客户端 model、domain、context、record ID、权限身份或 Action XML ID；
  不改变 Search 结果集合、分页、counts 或导航。

### 21.3 Glossary

| 术语 | 定义 |
|---|---|
| Relation path | 从当前作用域模型字段出发、按本 CC 类型/深度约束到达普通字段的点号路径 |
| Relation hop | 一次从关系字段跳转到其 comodel；末端普通字段不计入 hop |
| Loop scope | One2many 当前循环项的模型字段作用域 |
| Static loop block | 模板源中一个开标签与匹配闭标签构成的循环块；不等于实际数据行数 |
| Structure Check | 不读取业务记录，只验证语法、字段元数据、作用域、类型及静态限制 |
| Published Snapshot | CC-001 配置版本按既有 Apply/Publish 生命周期生成的活动配置快照 |

### 21.4 Version History

| 版本 | 日期 | 状态 | 说明 |
|---|---|---|---|
| v0.1 | 2026-10-12 | FROZEN | 基于 CC-014、当前实现/配置及 CC-003 边界起草，经评审修订并由用户批准冻结 |

### 21.5 Test Fixture Policy

- 使用现有 Odoo 测试结构及 ORM fixture；不强制新增目录或 fixture 框架。
- fixture 覆盖 Contact、Sales Order、Purchase Order 等实际 Resource 模型；覆盖 M2O/M2M/O2M
  不同深度、空值、格式键、简单/嵌套/空循环和 separator。
- 权限 fixture 覆盖有权、无权、部分有权、跨公司及 Record Rule 屏蔽的关联记录。
- 每个用例使用可区分的合成标记，断言只含预期授权值；依赖 Odoo 测试事务回滚/既有
  teardown 清理，不直接读写数据库，不使用 `sudo()` 证明业务权限行为。
- 结构检查测试使用调用 spy/测试替身阻止业务模型 `search`/`read`，验证 validator 只读
  配置和模型元数据。

### 21.6 Acceptance Scenarios

验收至少人工确认以下行为，并与自动测试结果一致：

1. 管理员输入有效 Many2one 路径，Check 和 Preview 显示格式化值。
2. 管理员输入 3 跳 Many2one 路径成功；第 4 跳在 Check/Publish 被拒绝。
3. Many2many 多值按配置 separator 和稳定顺序显示。
4. 管理员创建简单及嵌套 One2many 循环，行和嵌套作用域正确。
5. 循环中的多级解析、格式键、常量和转义正确。
6. 空循环不显示循环体；空字段显示 `—`。
7. 不可读字段/记录不泄露值、ID、数量或存在性；权限警告符合 CC-014。
8. HTML 特殊字符以文本显示，不执行标记。
9. Check Template 不读取业务记录；结构错误不更新 Published Snapshot/checksum。
10. Apply 后生产 Card 使用已发布模板；暂存未 Apply 时活动模板不变。
11. 双击打开 Card 仍由 CC-013 按当前用户重新授权并打开原生 Form。

### 21.7 HVR Scenarios

人工 HVR 至少记录用户/权限组、Resource、Snapshot 版本、模板、预览记录、语言/时区、
浏览器/版本、窗口尺寸、结果、Console/Network 异常及证据：

1. 打开设计器，确认字段列表仅显示当前模型直接字段，不出现关联模型展开树。
2. 手动输入有效 Many2one 路径，执行结构 Check 并观察 Preview。
3. 输入超深/错误类型路径，确认诊断明确且不会改变 Published 配置。
4. 输入 Many2many 路径，核对自定义 separator 和稳定顺序。
5. 输入简单及嵌套 One2many 循环，核对当前循环项作用域和行顺序。
6. 核对空循环、空值、Boolean False 及无权关系字段行为。
7. 核对关系字段格式键、常量、换行/制表符、字面花括号。
8. 输入 HTML 特殊字符，确认预览和生产 Card 均以文本安全呈现。
9. 运行 Check Template，确认没有读取/展开业务记录；再 Apply/Publish 并验证版本生命周期。
10. 从含关系模板的 Result Card 打开 Native Form，确认 CC-013 重新授权与导航未变。

### 21.8 Browser Verification Matrix

本表是 HVR 覆盖矩阵，不预先宣称尚未执行的浏览器/设备支持。记录实际验证的浏览器版本、
操作系统和视口；执行前状态保持“待验证”。

| 浏览器 | 版本/OS | 桌面设计器/Check/Preview | 窄屏布局 | 平板（如属于目标支持范围） |
|---|---|---|---|---|
| Chrome | HVR 时记录 | 待验证 | 待验证 | 待验证 |
| Firefox | HVR 时记录 | 待验证 | 待验证 | 待验证 |
| Safari | HVR 时记录 | 待验证 | 待验证 | 待验证 |
| Edge | HVR 时记录 | 待验证 | 待验证 | 待验证 |

只记录实际测试结果；目标浏览器范围按项目支持的 Odoo 18 客户端范围确定，不将“最新”
版本或未测设备自动视为已支持。

### 21.9 Review Change Log

| 日期 | 评审输入 | 本稿处理 |
|---|---|---|
| 2026-10-12 | CC-014-1 草案评审意见 | 补充版本基线、核对方法、字段示例边界、关系权限细则、结构检查一致性/测试/停止条件/决策/实现接线、兼容迁移、性能与日志继承规则、fixture、验收、HVR 和浏览器验证矩阵 |
| 2026-10-12 10:57 +08:00 | 用户批准冻结 | CC-014-1 v0.1 状态更新为 FROZEN；进入实施 |
| 2026-10-12 | 用户批准 Erratum | 将 Many2one 深度示例和 TEST-001~004 统一到 `stock.warehouse.partner_id` 的可验证字段链；不改变深度或类型语义 |

评审建议的单独关系解析性能阈值（包括放宽单 Card 预算）未采纳：本 CC 继承 CC-014
§7.3 的 parser P95 ≤10 ms、单 Card 模板渲染 P95 ≤50 ms、Publish/Apply 校验 P95 ≤100 ms、
Preview 端到端 P95 ≤500 ms；关系查询与循环计入对应现有预算。超预算需分析并停止评审，
不得未经批准改预算或加入截断。

评审建议增加 `template_hash`、`path_depth`、`loop_count` 等日志字段未采纳：日志严格
复用 CC-008 allowlist 和 CC-014 §8.4；本 CC 不授权新增字段，不记录模板原文、渲染值、
关系值、记录 ID 或权限拒绝细节。
