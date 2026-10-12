# Global Search Searchable Fields 管理员操作手册

本手册说明配置管理员如何管理 Business Resource 的 Searchable Fields，配置有限的多级关系字段路径，并验证搜索结果。
Searchable Field 控制搜索匹配哪些字段；它不控制 Result Card 的显示内容，也不改变打开记录的导航行为。

| 项 | 内容 |
|---|---|
| 手册版本 | v0.2 |
| 文档状态 | FROZEN |
| 批准冻结 | 用户批准；2026-10-12 17:46 +08:00 |
| 适用模块 | `wd_global_search` 18.0.1.3.0（Odoo 18 CE） |
| 契约基线 | CC-014-2 v0.2 FROZEN |
| 更新日期 | 2026-10-12 |

**适用范围：** 本手册面向 Global Search Configuration Manager 配置管理员，以及受委托进行配置和验证的实施顾问。普通搜索用户只需按日常方式搜索，不负责编辑配置；开发工程师应以冻结 Coding Contract、实现代码和测试为准，不应把本手册当作技术实现规范。

## 0. 五分钟快速入门

1. 使用具有 **Global Search Configuration Manager** 权限的账号，打开 **Global Search → Configuration Domains**。
2. 进入目标 Domain、Version 和 Business Resource，核对 Resource 的技术 `key` 与主模型。
3. 在 **Search Fields** 页新增一行，填写技术字段路径及匹配设置。
4. 若路径总关系深度为 3，在 **Performance** 页为同一 `resource_key` 设置 `max_relation_depth=3`。
5. 保存后检查校验结果。Draft 版本按 **Validate / Publish** 流程发布；已发布版本的暂存修改按页面提示执行 **Apply Changes**。
6. 打开 `/wd_global_search`，用一个只存在于关联字段中的业务值搜索，并确认目标 Resource 返回预期记录。

仅保存表单不代表配置已进入 Published Snapshot。发布或应用失败时，先按错误信息修复；不要绕过校验。

## 1. 权限与配置位置

1. 登录正确的 Odoo 数据库，并使用 **Global Search Configuration Manager** 组中的账号。没有该权限或看不到菜单时，请联系 Odoo 系统管理员按正常流程授予权限；不要使用超级用户或 `sudo()` 绕过权限。
2. 打开 **Global Search → Configuration Domains**。
3. 选择目标 Configuration Domain 和 Version。
4. 在 **Business Resources** 中打开目标 Resource，并确认：
   - Resource `key` 是预期值；
   - **Primary Model** 是搜索结果所属模型；
   - 当前版本和状态是预期的。
5. 对普通单模型 Resource，打开 **Search Fields**。Composite Resource 的 Searchable Fields 位于对应的 **Model Mappings (advanced)** 中；每条路径从该 Mapping 的模型开始解析。

该配置组用于进入 Global Search 配置界面并按现有生命周期编辑、校验和应用配置；它不扩大业务数据的读取权限，也不绕过 Odoo ACL、字段权限、Record Rule 或公司范围。是否可 Validate、Publish 或 Apply 以当前版本状态和界面允许的操作为准。申请配置权限请联系 Odoo 系统管理员。

**Resource 与模型不是同一个配置范围。** 即使两个 Resource 使用相同的 Odoo 模型，也应分别确认各自的 Search Fields。

## 2. Search Fields 配置列

| 界面列 | 用途 | 配置提示 |
|---|---|---|
| **Field Name** | 字段技术名或完整关系路径 | 使用 Odoo 技术字段名，不使用界面标签；路径段以 `.` 分隔 |
| **Purpose** | 字段的业务类别 | 选择与字段含义相符的 Identifier、Entity、Location 或 Text；这不替代字段路径或匹配方式 |
| **Operator Set** | 字段匹配方式 | Exact、Prefix 或 Contains；必须与终端字段类型兼容 |
| **Collection Match** | Many2many / One2many 路径的集合语义 | Any related record 或 All query values；普通字段和 Many2one 路径使用 Any related record |
| **Index Strategy** | 对终端字段声明的索引策略 | 按操作符、字段类型及已批准的索引计划选择；保存/发布配置不会自行创建物理数据库索引 |
| **Searchable** | 是否将该字段作为搜索字段 | 启用的字段才可作为 Searchable Field 参与匹配；停用不会删除字段，也不会自动移除 Card Template 中对字段的引用 |

`Purpose` 选项的常见含义：

| 选项 | 适用内容示例 |
|---|---|
| **Identifier** | 订单号、外部引用、业务编码 |
| **Entity** | 客户、联系人、产品名称 |
| **Location** | 城市、国家、地址 |
| **Text** | 说明、备注等可搜索文本 |

请沿用同一 Resource 中既有字段的分类惯例；修改 Purpose 不会把普通字段自动变成关系路径，也不会改变 Operator Set。

新建行的常见初始值为 **Operator Set = Exact**、**Collection Match = Any related record**、**Index Strategy = None**、**Searchable = enabled**；Purpose 必须按字段业务含义选择。保存后请核对行内实际值，不要依赖未确认的默认值。

**停用 Searchable 后：** 该路径不参与字段匹配或由该路径产生的 Count；显式提交该路径的条件也不会被视为当前可用字段。它不会更改 Card Template。Query Understanding 展示的是本次请求中被接受的条件摘要，不是 Searchable Field 清单；不要仅凭摘要判断某配置字段是否启用。

## 3. 路径语法与支持范围

字段路径使用完整技术名：

```text
field_path := field_name ("." field_name)*
field_name := [A-Za-z_][A-Za-z0-9_]*
```

路径最长 100 个 ASCII 字符、最多 4 段（包含终端字段）；两项均为 CC-014-2 定义的配置结构上限，不是建议目标。超过字符数、段数、关系类型深度或 Resource 深度时，Validate / Publish / Apply 会拒绝配置；应按实际界面提示修正，不得通过改用标签或拆成表达式绕开限制。每个中间字段必须是受支持的关系字段，终端必须是存储且 ORM 可搜索的普通字段：Char、Text、Integer、Float、Date、Datetime、Boolean、Selection 或 Monetary。

| 路径形态 | 允许的关系结构 | 深度上限 |
|---|---|---:|
| 直接字段 | 一个普通终端字段 | 0 |
| Many2one | 最多 3 个 Many2one，随后是普通终端字段 | 3 |
| Many2many | 根模型的 Many2many，可接零或一个 Many2one，随后是普通终端字段 | 2（包含 Many2many） |
| One2many | 根模型的 One2many，可接零至两个 Many2one，随后是普通终端字段 | One2many 后最多 2 个 Many2one；总关系边最多 3 |

有效路径的结构示例（正式配置前仍须核对目标模型实际字段）：

```text
name                                  # 直接字段
partner_id.city                      # Many2one + 普通字段
partner_id.country_id.name           # 两个 Many2one + 普通字段
category_id.parent_id.name           # Many2many + Many2one + 普通字段
order_line.product_id.category_id.name # One2many + 两个 Many2one + 普通字段
```

以下语法或结构不支持：

```text
partner_id[0].city                   # 索引访问
partner_id.city|upper                # 表达式
partner_id.city()                    # 函数或方法调用
partner_id.city + "!"                # 计算
partner_id.country_id.region_id.zone_id.name  # 超出 Many2one 深度
```

路径各段必须来自目标根模型的 Odoo ORM 元数据。不能根据展示标签、相似模型或 Card Template 字段列表猜测技术名；重复关系边、循环路径、终端关系字段、Html/Binary/Reference 等不受支持终端都会被拒绝。

## 4. Operator Set 与字段类型

| Operator Set | 搜索含义 | 适用类型 |
|---|---|---|
| **Exact** | 精确匹配 | 所有受支持的终端类型 |
| **Prefix** | 文本前缀匹配 | Char、Text |
| **Contains** | 文本包含匹配 | Char、Text |

新建行的 Operator Set 默认是 **Exact**。根据业务字段用途选择不同操作符，不要根据 Purpose 自动推断操作符：订单号通常用 Exact；姓名、城市等需要局部文本查询时可以选 Contains 或 Prefix。数值、日期、Datetime、Boolean、Selection 和 Monetary 只能使用 Exact。Prefix / Contains 不会把非文本值隐式转换为文本。操作符和索引策略必须兼容；终端类型或策略不兼容时 Validate / Publish / Apply 会拒绝该配置。

## 5. Collection Match：Many2many 与 One2many

集合路径必须在同一 Searchable Field 行选择 **Collection Match**：

- **Any related record**：任意一条当前用户可读的关联记录匹配任意一个有效查询值，即匹配。
- **All query values**：每个不同的有效查询值都必须被匹配；不同关联记录可以分别满足不同查询值。

新建行默认 **Any related record**。选择 Any 或 All 应符合该集合字段的业务搜索要求；All 表示当前同一路径的每个不同有效查询值都需满足，不是要求同一条关联记录包含所有值。直接字段和 Many2one 路径没有集合语义，必须使用 **Any related record**。无可读的关联记录时，不应因为集合策略而退化为匹配关系字段的名称或 ID。缺少必需集合策略或策略不适用时，Validate / Publish / Apply 会拒绝配置。

## 6. Index Strategy 与性能设置

Index Strategy 应依字段终端类型、Operator Set 和 CC-006 已批准的索引策略选择。配置只声明搜索所需策略，不表示已创建或验证物理索引。

| 策略 | 常见匹配方式 | 注意事项 |
|---|---|---|
| **B-tree** | Exact；部分 Prefix 场景 | 以字段类型和查询计划为准 |
| **text_pattern_ops** | Prefix | 仅用于兼容的文本终端 |
| **GIN pg_trgm** | Contains | 需确认 PostgreSQL 扩展、索引及性能计划 |
| **GiST pg_trgm** | Contains | 非默认；仅在 CC-006 及部署实现明确支持并验证后使用 |
| **None** | 不声明物理索引 | 只能在性能证据支持时选择，不代表性能没有影响 |

不要只因下拉框中存在某个选项，就认为索引已经部署。Publish / Apply 不执行索引 DDL；索引创建、变更和维护应走项目批准的受控流程。

### 索引部署与验证

1. 配置管理员在 Searchable Field 中选择与字段类型、Operator Set 相容的策略，并记录选择理由。
2. 上线前由项目实现/运维按 [CC-006](../context/intent/CC-006_global_search_index_performance.md) 检查目标字段、扩展依赖、索引迁移方案和写入影响；配置管理员不直接在数据库建索引。
3. 物理索引变更由获授权的运维/DBA 按已批准的变更和维护窗口执行；不得由 Publish / Apply 或未经审查的 SQL 替代。
4. 部署后由项目技术人员验证索引定义、EXPLAIN/query plan、数据规模、性能及写入影响，并记录证据。
5. 若索引不可用或性能门槛未满足，不要将索引策略配置当成已完成的部署；暂停上线并交由项目维护者处理。

### 性能建议

- 只增加确有搜索需求的字段，优先使用最短且足够的关系路径。
- Exact、Prefix、Contains 按实际搜索需求选择；不要仅为“更容易搜到”把所有字段设为 Contains。
- 限制同时参与搜索的多级字段和集合路径数量；复用现有路径前先确认其字段类型、用途和权限。
- 索引策略按 CC-006 的选择依据和测量证据确定；B-tree 并非对每种路径或 Contains 查询都更快。
- 使用代表性数据和目标用户验证响应时间、结果数量和查询计划，不增加超出契约的超时或结果预算。

### `max_relation_depth`

在 Version 的 **Performance** 页按 Resource 配置 `max_relation_depth`：

- 没有对应配置行时默认值为 **2**；
- 可配置上限为 **3**；
- 深度按完整路径上的关系边数计算，One2many 起始边也计入总深度；
- 路径本身的 CC-014-2 类型上限仍然独立生效，Performance 配置不能放宽它；
- 若完整路径有 3 条关系边，`resource_key` 必须与 Business Resource 的 `key` 完全一致，且 `max_relation_depth` 至少为 3。

其它性能值不得超过 Search Service 限制（最多 200 条结果、Resource 3 秒、请求 5 秒）。不要通过提高预算掩盖路径设计或索引问题。

## 7. 完整示例：Sales Order 按客户和明细产品搜索

以下示例以 Odoo 18 CE 标准 `sale.order` / `product.product` 模型为背景；自定义模块、不同数据库数据模型或 Odoo 版本可能改变字段可用性。字段路径不能保证跨数据库或版本直接复制。使用前先核对当前 Resource 根模型和每段 ORM 技术字段，并通过 Validate / Publish 校验。

| Field Name | 字段含义 | Purpose | Operator Set | Collection Match | Index Strategy |
|---|---|---|---|---|---|
| `partner_id.name` | 客户名称 | Entity | Contains | Any related record | GIN pg_trgm（需有相应索引依据） |
| `order_line.product_id.product_tmpl_id.name` | 订单明细产品名称 | Entity | Contains | Any related record | GIN pg_trgm（需有相应索引依据） |

第二条路径由 `sale.order.order_line`（One2many）、`product_id`（Many2one）、`product_tmpl_id`（Many2one）组成，总深度为 3；在 **Performance** 页将 `sale_order.max_relation_depth` 明确设为 3。对 `product.product` 的名称搜索也可能需要使用存储的模板字段路径 `product_tmpl_id.name`，以满足终端字段存储和 ORM 可搜索要求。

配置说明：

- 新增 dotted Searchable Field 时，不需要为同一路径另建 **Relation Path**。
- **Relation Paths** 保留既有 `name` 关系扩展用途；不要为了添加 Searchable Field 而删除或改写既有 Relation Path。
- Searchable Field 只控制匹配与返回的根 Resource 记录；是否在 Result Card 中展示该字段值，仍由独立的 Card Template 决定。
- Index Strategy 需与当前部署和 CC-006 证据相符；表格中的 GIN 示例不是自动建索引的指令。

## 8. 保存、校验与发布

先确认目标 Domain、Version、Resource 和模型，再开始编辑。修改前记录当前 Published Version 与 checksum；共享环境变更应遵循项目授权和发布流程。

### Draft Version

1. 保存 Search Fields 和 Performance 设置。
2. 在版本页执行 **Validate**。
3. 校验通过后执行 **Publish**。
4. 确认状态为 **Published**、checksum 已生成，并记下版本信息。

### Published Version 的待应用修改

1. 保存资源表单和页面上的暂存修改。
2. 确认 Version 显示 **Pending Changes**。
3. 在目标 Version 上执行 **Apply Changes**。
4. Apply 会重新校验并更新该版本的 Published Snapshot / checksum。
5. 重新打开或刷新 Version，确认 Pending Changes 已清除、checksum 已更新。

Apply 失败时，界面会显示校验错误，旧 Published Snapshot 继续生效。按错误指出的模型、字段、类型、深度或策略修复后再试；不要把失败的待处理修改当成已经上线。Retired Version 不是当前生效配置，不应将其 Apply 当作重新激活。

### 发布或应用失败时

1. 留在当前 Domain / Version 页面，读取通知或版本页显示的具体错误消息；Draft 校验拒绝时也检查版本的 rejection 信息。
2. 根据消息定位字段路径、终端类型、Operator Set、Collection Match、Resource 深度或配置完整性问题；不要猜测错误码或隐藏错误。
3. 修复后重新保存，并按版本状态重试 **Validate → Publish** 或 **Apply Changes**。
4. 成功后刷新 Version，确认 Published 状态或 Apply 成功、Pending Changes 清除，并检查最新 checksum。
5. 失败时旧 Published Snapshot 仍生效；如果无法解释错误或仍不确定哪份配置生效，停止发布并联系项目维护者。

## 9. `/wd_global_search` 人工验证步骤

请使用目标数据库中确实存在、且普通搜索用户有权读取的数据。管理员预览或管理员搜索结果不能代替普通用户权限验证。

1. 以目标普通搜索用户登录后打开 `http://127.0.0.1:8091/wd_global_search`（其它环境替换为对应 Odoo 主机和端口）。
2. 在搜索框输入仅存在于关联字段中的客户名称，提交搜索。
3. 确认结果中出现对应 Sales Order，并记录订单号、客户名及结果数量。选取的客户名应不包含在订单编号或其他直接字段中，避免误判为直接字段命中。
4. 使用一条明细行中实际存在的产品名称重复搜索。
5. 确认结果中出现包含该产品的 Sales Order；检查 Query Understanding、Resource 分组、分页数量，并记录可复现的订单与产品名称。
6. 用一个不存在的关联值搜索，确认不会出现无关订单。
7. 使用不同公司或不同权限的目标用户重复关键验证，确认命中、计数和结果都遵循该用户的权限范围。
8. 记录数据库、Domain、Version、checksum、测试用户角色、搜索词、预期结果、实际结果和验证结论。

### 人工验证最小范围

- 对本次新增或修改的每条路径，至少有一个正向用例（关联值确实存在）和一个负向用例（不存在的关联值不应命中）。
- 至少验证一个目标 Resource 和本次变更涉及的关系形态；例如本手册的 Sales Order 示例应分别验证客户 Many2one 路径与订单明细 One2many 路径。
- 若配置了集合路径，应按实际选择的 Collection Match 验证其语义；若业务使用 Any 与 All 两种模式，则分别验证两种模式。没有配置 Many2many 或某种模式时，不要求为本次变更虚构该场景。
- 发布前建议至少使用两名访问范围不同的普通搜索用户验证；至少一名必须是本次配置的目标搜索用户。若数据库没有权限范围不同的可用测试账号，记录原因并提交项目维护者确认后再完成该项。普通搜索用户不需要配置管理员组。

**判定提示：** Workspace 的自由文本 Query Understanding 可能显示 `name=<搜索词>`。这表示界面提交的是普通文本搜索条件；仅看这行摘要不能证明某个 Searchable Field 路径被使用。应选择一个不在订单直接字段中、但确实存在于客户或订单明细产品上的值，并核对实际 Sales Order 结果。使用结构化测试请求时，SearchRequest 的 dimension 必须与 Published 配置的完整路径一致。

本地示例数据库此前可用于试查的值包括：

| 搜索值 | 关联字段 | 预期观察 |
|---|---|---|
| `GS05- Company 2 Secret` | 客户名称 | 出现该客户相关的 Sales Order（示例订单曾为 `S05051`） |
| `Desk` | 明细行产品名称 | 出现包含匹配产品的 Sales Order（示例订单曾为 `S00006`、`S00024`） |

示例数据可能随数据库重置、权限或配置变化而改变；请以人工验证当时的实际数据为准。本手册不把这些值视为验收结果。

### 人工验证记录

| 日期/环境 | Domain / Version / checksum | 用户角色/公司 | 搜索值与路径 | 预期结果 | 实际结果 / 记录数 | 结论 |
|---|---|---|---|---|---|---|
| 待填写 | 待填写 | 待填写 | 待填写 | 待填写 | 待填写 | 待人工验证 |

## 10. 常见问题

| 现象 | 检查方式 |
|---|---|
| 提示字段不存在 | 检查 Resource 根模型、字段技术名和每一段的 comodel；不要使用展示标签或猜测名称 |
| 终端字段不能搜索 | 检查终端字段是否为受支持、存储且 ORM 可搜索的普通字段；关系字段不能作为终端 |
| Contains / Prefix 不通过校验 | 确认终端字段为 Char 或 Text，并确认 Index Strategy 与 Operator Set 兼容 |
| 路径深度超限 | 逐段数清关系边；同时检查 CC-014-2 类型硬上限和 Resource 的 `max_relation_depth` |
| One2many / Many2many 搜索行为不符 | 检查 Collection Match 是 Any related record 还是 All query values |
| 搜索不到关联记录 | 检查是否已 Apply / Publish、字段行是否启用、目标用户是否有相关字段及记录的读取权限 |
| 搜索结果卡片未显示产品/客户字段 | Searchable Field 负责搜索，不负责卡片显示；检查对应 Resource 的 Card Template |
| 设置索引后仍然慢 | 索引策略不是物理索引已存在的证明；按 CC-006 受控流程检查部署索引、查询计划及性能证据 |
| Apply 失败或 checksum 未改变 | 读取界面错误，修复后重试；Apply 成功后刷新 Version，确认 Pending Changes 清除 |

### 权限差异排查

- 配置管理员组只用于配置管理；目标普通搜索用户不需要该组。
- 检查目标用户是否能访问 Global Search Workspace，以及是否属于预期业务组。
- 核对相关模型 ACL、字段组限制、关联记录 Record Rule 和当前公司范围。
- 使用目标用户本人登录验证；不要用管理员预览结果代替普通用户结果，也不要通过提权规避差异。
- 如果权限差异符合 ACL、字段组、Record Rule 或公司范围设计，这是预期访问控制，不应通过放宽 Searchable 配置隐藏。

### 校验失败诊断

当前没有稳定、细分到每种 Searchable Field 错误的公开错误码目录。配置 Validate / Publish / Apply 的失败一般以 `CONFIGURATION_ERROR` 记录，具体原因以当前界面的原始错误消息为准；以下是错误类别，不是可依赖的错误码：

| 错误类别 | 检查与处理 |
|---|---|
| 字段不存在 / 关系无法解析 | 核对根模型、每段技术字段名和关系目标模型 |
| 终端类型或存储性不支持 | 改用契约支持、存储且 ORM 可搜索的普通终端字段 |
| 路径语法或深度超限 | 检查字符/段数、关系类型结构、类型硬上限和 Resource `max_relation_depth` |
| Operator / Index Strategy 不兼容 | 核对终端字段类型和 CC-006 索引策略 |
| Collection Match 缺失或不适用 | 集合路径选择 Any 或 All；直接字段及 Many2one 使用 Any |

## 11. 发布前检查清单

配置管理员应在保存后、Validate / Publish 或 Apply 前，以及最终人工验证前使用本清单。所有适用项都应完成；不适用项需注明原因。建议将填写后的清单与版本/checksum 和验证记录一并保留。

- [ ] Domain、Version、Resource key 和根模型正确
- [ ] 字段名使用真实的 Odoo 技术字段名
- [ ] 关系结构、关系类型、路径长度和深度符合 CC-014-2
- [ ] 终端字段属于受支持、存储且 ORM 可搜索的普通字段
- [ ] Operator Set 与终端类型匹配
- [ ] 集合路径设置了正确的 Collection Match；非集合路径使用 Any related record
- [ ] Index Strategy 与操作符兼容，且没有误认为已经创建物理索引
- [ ] 三跳路径有匹配 Resource key 的 `max_relation_depth=3` 配置
- [ ] 保存后完成 Validate / Publish 或 Apply Changes，并检查状态与 checksum
- [ ] 使用普通目标用户在 `/wd_global_search` 验证客户、产品相关搜索；按本次权限范围完成第二名不同访问范围用户的对照验证，或记录其不适用原因
- [ ] 验证记录已填写；实际人工验证完成前，状态保持“等待人工验证”

## 12. 术语表

| 术语 | 定义 |
|---|---|
| Searchable Field | Published 配置中定义的搜索字段及其匹配属性 |
| Field Path | 从 Resource 根模型出发，以技术字段名和点号组成的有限路径 |
| Relation Path | 既有配置中用于关系范围内 `name` 搜索的配置；与 Searchable Field 路径不同 |
| Terminal Field | Field Path 最后一段，必须是支持、存储且 ORM 可搜索的普通字段 |
| Collection Match | Many2many / One2many 路径的 Any 或 All 匹配语义 |
| Operator Set | Exact、Prefix 或 Contains 字段匹配操作符 |
| Index Strategy | 针对终端字段声明的索引策略，不等同于物理索引已部署 |
| `max_relation_depth` | Resource Performance Config 允许的最大关系边数 |
| Published Snapshot | 搜索运行时消费的已发布配置快照及其 checksum |
| Pending Changes | 已暂存但尚未通过 Apply 更新到 Published Snapshot 的修改 |

## 13. 最佳实践

- 从能满足搜索需求的最短路径开始；不要为了方便把无关关系字段都加入配置。
- Identifier、客户/产品名称和说明文本分别考虑实际查询方式；Purpose 不应代替 Operator Set 的选择。
- Searchable 配置和 Card Template 分开验证：搜索能命中不代表卡片会显示该字段，卡片能显示也不代表字段已配置为可搜索。
- 每次只变更必要的 Resource / 字段，使用目标用户验证后再处理其它 Resource。
- 三跳路径同时检查类型深度上限和 Resource Performance Config。
- 发布前检查 Pending Changes、校验结果及 checksum；保存人工验证证据。
- 避免把敏感或无业务搜索需要的字段配置成 Searchable；运行时权限仍必须按搜索用户执行。

## 14. 版本兼容性

- 本手册对应 Odoo 18 CE、模块 `wd_global_search` 18.0.1.3.0 和 CC-014-2 v0.2。
- 模块升级或字段模型自定义后，应按 [CC-010 升级策略](../context/intent/CC-010_global_search_upgrade_strategy.md) 检查配置、checksum、索引和搜索回归。
- 不因旧 Snapshot 可读取就推断新版本行为已验证；升级后的 Searchable Field 路径应重新通过配置校验和目标用户搜索验证。

## 15. 相关契约和文档

- [CC-014-2：Searchable Field Multi-Level Resolution](../context/intent/CC-014-2_searchable_field_multi_level.md)
- [CC-002：Search API 契约](../context/intent/CC-002_global_search_service_core.md)
- [CC-003：搜索权限边界](../context/intent/CC-003_global_search_permission_boundary.md)
- [CC-006：索引与性能契约](../context/intent/CC-006_global_search_index_performance.md)
- [配置与搜索验证手册](./CC-001_configuration_admin_guide.md)
- [卡片模板设计器管理员操作手册](./CC-014_card_template_admin_guide.md)

本项目尚无本手册范围内的独立 Search Service 或权限边界管理员手册；操作时以以上冻结契约和现有配置手册为准。

**反馈渠道：** 配置或数据权限问题联系 Odoo 系统管理员；Search Service、索引或手册内容问题提交项目评审/维护者；安全问题走项目指定的安全报告渠道。不要在公开问题中粘贴业务记录、搜索值、用户凭据或权限数据。

## 16. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| v0.1 | 2026-10-12 | 创建 Searchable Fields 管理员操作手册，等待用户人工验证 |
| v0.2 | 2026-10-12 | 根据评审补充适用范围、权限、默认值、路径限制、索引流程、发布失败处理、验证范围、排障、术语和兼容性说明；用户批准冻结（2026-10-12 17:46 +08:00） |
