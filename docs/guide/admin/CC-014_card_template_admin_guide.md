# Global Search 卡片模板设计器管理员操作手册

本手册说明配置管理员如何为 Business Resource 编写、预览、保存和发布 Result Card 模板。
卡片模板只控制搜索结果卡片的摘要内容，不改变搜索条件、结果模型或打开记录的 Action。

| 项 | 内容 |
|---|---|
| 手册版本 | v0.2 |
| 适用模块 | `wd_global_search` 18.0.1.3.0 |
| 契约基线 | CC-014 v0.1、CC-014-1 v0.1 |
| 更新日期 | 2026-10-12 |

## 0. 五分钟快速入门

1. 确认登录的是目标 Odoo 数据库，并打开目标 Business Resource。
2. 点击 **Edit Template**。
3. 在预览来源中选择 **Synthetic example**，输入 `联系人：{name}`。
4. 点击 **Check Template**；确认 **Live Preview** 显示示例联系人名称。
5. 点击 **Save**。
6. 如果界面提示待应用修改，对已发布配置点击 **Apply Changes**；Draft 配置则回到版本页面完成 **Validate / Publish**。
7. 使用普通搜索用户执行一次搜索，检查生产卡片显示。

快速入门只演示最简单的单字段模板；下文给出关系路径、循环和多值实例。

## 1. 打开卡片设计器

1. 登录正确的 Odoo 数据库，并使用具有 **Global Search Configuration Manager** 权限的账号。此权限由 Odoo 系统管理员授予；如果看不到该组或配置菜单，请联系系统管理员将你的用户加入 **WD Global Search** 分类下的 **Global Search Configuration Manager** 组。不要使用超级用户或提升为管理员来绕过权限。
2. 打开 **Global Search → Configuration Domains**。
3. 打开目标 Domain 和 Version，再进入 **Business Resources**。
4. 打开要配置的 Resource，确认它的主模型是预期的结果模型。
5. 在 **Result Card Template** 区域检查当前预览，点击 **Edit Template**。
6. 设计器会覆盖在当前页面上。编辑完成后，点左上角 **Back to Resource** 返回 Resource。

> 模板属于 Resource，而不是整个模型。不同 Resource 即使使用相同模型，也可以有不同卡片。

## 2. 设计器界面

| 区域 | 用途 |
|---|---|
| Template | 输入常量、字段变量和循环块 |
| Many2many value separator | 设置 Many2many 字段多个值之间的分隔符，默认 `, ` |
| Live Preview | 随编辑刷新预览；可切换预览数据来源 |
| Available fields | 显示当前 Resource 模型的直接字段，包含技术名、类型和标签 |
| Check Template | 检查语法、模型字段和类型限制，不读取业务记录 |
| Save | 保存当前编辑；对已发布版本的修改仍可能处于待应用状态 |
| Apply Changes | 将待应用修改重新校验并更新 Published Configuration |

字段插入方法：

- 点击字段，或将字段拖到编辑区的光标/选区位置；
- 在字段列表中选择字段并按 **Enter**；
- 也可以手动输入变量和常量。

字段列表只显示当前模型的直接字段，不展开关联模型的字段树。点击关系字段时：

- Many2one 会插入 `{partner_id}`，需要多级字段时可手动改为 `{partner_id.name}`；
- Many2many 会插入带点号的路径起始骨架，例如 `{category_id.}`；
- One2many 会插入开闭标签骨架，例如 `{order_line} ... {/order_line}`。

**权限提示：** 设计器顶部显示预览账号权限可能与搜索用户不同的全局警告。每个字段按钮还显示当前预览用户可读状态；受字段组约束的字段会标记 **Group-restricted; visibility may vary by user**。列表只包含当前用户可读的字段元数据；组约束标记不代表其他搜索用户也能读取该字段。最终权限仍由搜索用户的 ACL、字段权限、Record Rule 和公司范围决定。

## 3. 基本语法速查

| 写法 | 含义 |
|---|---|
| `{name}` | 插入字段值 |
| `{amount_total:monetary}` | 用指定格式显示字段 |
| `\n` | 换行 |
| `\t` | 制表符 |
| `{{`、`}}` | 输出字面量 `{`、`}` |
| `{partner_id.country_id.name}` | 按有限关系路径读取关联字段 |
| `{order_line}...{/order_line}` | 遍历 One2many 的每一行 |

常量文字、空格、标点会原样显示。模板不支持条件语句、计算表达式、函数调用或 Python
代码。格式键只能使用内建格式：`text`、`integer`、`float`、`date`、`datetime`、
`boolean`、`selection`、`many2one`、`monetary`；字段类型与格式不兼容时，Check 会报错。

### 格式键与字段类型

| 格式键 | 适用类型 | 示例 |
|---|---|---|
| `text` | Char、Text、Html；也可用于其他受支持的标量类型作文本显示 | `{name:text}` |
| `integer` | Integer | `{sequence:integer}` |
| `float` | Float、Monetary | `{product_uom_qty:float}` |
| `date` | Date | `{invoice_date:date}` |
| `datetime` | Datetime | `{date_order:datetime}` |
| `boolean` | Boolean | `{active:boolean}` |
| `selection` | Selection | `{state:selection}` |
| `many2one` | 直接 Many2one 字段 | `{partner_id:many2one}` |
| `monetary` | Monetary，使用字段关联币种 | `{amount_total:monetary}` |

格式键必须和字段类型兼容。关系路径的末端必须是契约允许的普通字段；不能用
`{partner_id.name:many2one}` 把关系路径末端变成关系对象。实际可用字段和类型以
**Available fields** 与 **Check Template** 为准。

## 4. 可直接参考的模板实例

下列示例按各自标注的 Resource 主模型编写。请以 **Available fields** 中的实际技术字段名
为准；若 Resource 的模型不同，不能照搬字段名。

### 示例 A：联系人卡片（`res.partner`）

```text
联系人：{name}
电话：{phone}
邮箱：{email}
公司：{parent_id.name}
国家：{country_id.name}
```

`name`、`phone`、`email` 是联系人直接字段；`parent_id.name` 和 `country_id.name` 是
Many2one 关系路径。

### 示例 B：仓库名称和地址（`stock.warehouse`）

```text
仓库：{name}（{code}）
地址：{partner_id.city} {partner_id.street}
国家：{partner_id.country_id.name}
```

仓库的地址来自 `partner_id`。`partner_id.city` 是一跳路径；`partner_id.country_id.name`
是两跳路径。`partner_id` 是指向 `res.partner` 的 Many2one，`country_id` 是联系人上的
Many2one；每一段字段和目标记录都按当前用户权限检查。

### 示例 C：销售订单摘要（`sale.order`）

```text
订单：{name}
客户：{partner_id.name}
下单时间：{date_order:datetime}
状态：{state:selection}
总额：{amount_total:monetary}
```

日期、时间、数字、货币和 Selection 标签由服务端按当前用户的语言、时区及货币格式化。

### 示例 D：订单行（`sale.order`）

```text
订单明细：
{order_line}
- {product_id.name} × {product_uom_qty} = {price_subtotal:monetary}
{/order_line}
```

`order_line` 必须是当前模型上的 One2many。循环体以内的字段属于当前订单行，因此可以
写 `{product_id.name}`、`{product_uom_qty}` 和 `{price_subtotal:monetary}`。

### 示例 E：联系人标签（`res.partner`）

模板：

```text
联系人：{name}
标签：{category_id.name}
```

在 **Many2many value separator** 中输入 ` | ` 后，多个标签示例显示为：

```text
联系人：Ada
标签：客户 | 供应商 | VIP
```

separator 属于 Resource 配置；已发布 Resource 修改后仍需 **Apply Changes** 才会更新运行
时 Published Configuration。

separator 是 Resource 级纯文本，不是模板片段，不会展开变量或转义。例如输入 `\n` 会显示
这两个字符，不会自动换行；输入 `{name}` 也不会读取联系人姓名。建议使用 ` | `、`、 ` 等
清晰的纯文本标点，并在 Apply 后确认结果。

### 示例 F：两层联系人子级（`res.partner`）

```text
下级联系人：
{child_ids}
- {name}
  下一级联系人：
  {child_ids}
  -- {name}
  {/child_ids}
{/child_ids}
```

内层循环的 `{name}` 表示内层当前联系人，不是外层或最上层记录。循环体不能引用 root
记录字段或父循环项字段；需要展示 root 信息时，把它写在循环块外。

### 示例 G：采购订单（`purchase.order`）

```text
采购单：{name}
供应商：{partner_id.name}
下单时间：{date_order:datetime}
状态：{state:selection}
总额：{amount_total:monetary}
```

### 示例 H：产品（`product.product`）

```text
产品：{product_tmpl_id.name}
内部编码：{default_code}
条码：{barcode}
```

产品名称通过 `product_tmpl_id` Many2one 路径读取产品模板上的 `name`。

### 示例 I：库存移动（`stock.move`）

```text
物料：{product_id.name}
需求数量：{product_uom_qty}
来源位置：{location_id.complete_name}
目标位置：{location_dest_id.complete_name}
状态：{state:selection}
```

### 示例 J：客户发票或供应商账单（`account.move`）

```text
凭证：{name}
客户/供应商：{partner_id.name}
发票日：{invoice_date:date}
到期日：{invoice_date_due:date}
总额：{amount_total:monetary}
状态：{state:selection}
```

以上示例要求相应模型已安装、成为 Resource 主模型，并且列出的字段通过当前配置校验。
不同 Odoo 数据库的模块、字段访问组和标签可能不同；如果字段列表或 Check 不接受某个字段，
请以当前模型元数据和权限为准，不要强行套用示例。

## 5. 关系深度、循环与限制

- Many2one：最多 3 个关系跳转，末端必须是受支持的普通字段。
- Many2many：最多 2 个关系跳转；Many2many 必须是路径第一段，后面最多再接一个
  Many2one。
- Many2many 的多个可读值使用 Resource separator 连接。
- One2many 只能通过循环块展示；最多嵌套 2 层。
- 单个模板最多 5 个循环块；单个循环体最多 1000 个 Unicode 字符。
- 模板沿用 CC-014 的总长度不超过 8 KiB、变量最多 50 次限制。
- 空字段值显示为 `—`；没有关联行的 One2many 循环不显示循环体。

以 `stock.warehouse` 上 `partner_id` 为例，关系跳数只计算关系字段，不计算末端普通字段：

| 跳数 | 示例 | 结果 |
|---|---|---|
| 1 | `{partner_id.name}` | 接受 |
| 2 | `{partner_id.country_id.name}` | 接受 |
| 3 | `{partner_id.parent_id.country_id.name}` | 接受 |
| 4 | `{partner_id.parent_id.parent_id.country_id.name}` | 拒绝，超过 Many2one 深度 |

以下写法会被拒绝：

```text
{partner_id.parent_id.parent_id.country_id.name}  # stock.warehouse 上超过 3 跳
{category_id.parent_id.grandparent_id.name}       # Many2many 路径超过 2 跳
{order_line.product_id.name}                      # One2many 不能写成变量路径
{partner_id.category_id.name}                      # Many2one 后不能接 Many2many
{amount_total * 1.1}                               # 不支持表达式
{method()}                                         # 不支持函数/方法调用
```

## 6. 预览与权限提示

**Live Preview** 提供三种来源：

- **Latest readable record**：配置管理员当前权限下最新可读记录；
- **Select a readable record**：从配置管理员当前可读记录中选择；
- **Synthetic example**：合成示例值，不代表真实业务记录。

合成示例的用途是在没有可读记录时检查模板布局；系统根据模型字段类型生成示例值，不读取
业务记录或真实关系数据。因此它不证明真实字段值、关系内容或目标搜索用户的权限结果。

模板或 separator 修改后预览自动刷新；切换来源或所选记录也会刷新。**Check Template**
只检查模板结构和模型元数据，不读取业务记录；要看真实值请选前两种预览来源。

预览使用当前配置管理员账号的 ACL、Record Rule 和公司范围。普通搜索用户的权限可能不同；
管理员预览可见的字段或记录不代表普通用户一定可见。生产搜索卡片仍按搜索用户权限读取，
不能通过模板绕过权限。

字段按钮上的可读状态只针对当前配置管理员账号；组约束徽标提示该字段对不同用户可能
可见性不同。它不是目标用户授权检查，仍须按 §8 进行实际用户验证。

模板内容按纯文本显示。不要把 HTML、脚本或代码作为模板功能使用；HTML 标签不作为可执行
或格式化标记。

## 7. 检查、保存和应用

建议按以下顺序操作：

1. **选择预览来源**，先确认 Resource 和示例记录正确。
2. **输入模板**，必要时通过字段列表插入变量；写关系路径或 One2many 循环时核对当前
   Resource 的主模型和字段类型。
3. **设置 separator**（仅当模板使用 Many2many 时需要）。
4. 点击 **Check Template**。有语法、路径、字段类型或深度错误时，先按提示修正。
5. 检查 Live Preview：切换一条记录，确认空值、换行、货币格式和多值顺序符合预期。
6. 点击 **Save**。
7. 若 Resource 属于 Published/Retired Version 且出现待应用变更，点击 **Apply Changes**。
   Apply 会再次校验配置；失败时旧 Published Configuration 保持生效，待处理修改不会静默
   成为线上模板。
8. 若 Resource 属于 Draft Version，按版本页面现有 **Validate / Publish** 流程完成发布；
   不要把保存 Draft 当成已发布。
9. 返回 Resource，确认摘要预览和 pending 状态符合预期；再用普通搜索用户验证生产卡片。

对共享或生产配置进行 Apply 前，先确认数据库、Domain、Version 和 Resource，并按项目发布
流程取得授权。不要用临时模板覆盖正在使用的共享 Resource 进行试验。

### 校验或发布失败时

以设计器或配置页面实际显示的错误消息为准。当前手册不定义稳定错误码目录；不要根据
错误文本猜测或填写未在界面中出现的代码。根据消息修复字段名、字段类型、关系跳数、
循环标签或权限问题，然后重新执行 **Check Template**、检查 Live Preview，并重试
**Save / Apply Changes**。Apply 失败时旧 Published Configuration 保持生效；确认页面显示
成功和 pending 状态清除后，再用目标用户验证。

## 8. 常见问题

| 现象 | 检查方法 |
|---|---|
| Check 提示字段不存在 | 确认 Resource 主模型和技术字段名；显示标签不能替代技术名 |
| 拖入 One2many 后无法通过 Check | 确认循环标签成对匹配，且字段在当前模型上确实是 One2many |
| 循环内字段提示无效 | 使用当前循环项模型的字段；不要引用 root 或父循环项字段 |
| 关系路径被拒绝 | 检查每段字段的关系类型、跳数及末端字段类型 |
| 预览与普通用户结果不同 | 这是权限边界的预期可能性；使用目标用户做最终搜索验证 |
| Save 后卡片没有变化 | 检查是否有 pending changes；Published/Retired 配置还需 Apply Changes |
| 金额格式校验失败 | 确认目标 Monetary 字段存在有效的 `res.currency` 字段及权限 |
| 返回 Resource 没反应 | 点击设计器左上角 **Back to Resource**；必要时使用浏览器返回，不要直接关闭 Odoo 服务 |

### 多用户权限验证

1. 使用具有预期搜索角色和公司范围的目标用户登录；不要共享配置管理员的凭据。
2. 对同一 Resource 执行与日常使用相同的搜索。
3. 检查卡片字段是否按预期显示、隐藏或留空，以及该用户是否只看到其可访问的记录。
4. 如结果不同，核对该用户的字段组权限、ACL、Record Rule 和当前公司；需要时由系统管理员
   按正常授权流程调整权限，再重复验证。
5. 在模板或权限变更后、正式发布前完成验证，并保存验证结果作为发布证据。

卡片预览和 Available fields 列表不能替代以上目标用户验证。

### 发布前检查清单

- [ ] Resource 的主模型和目标 Domain / Version 正确
- [ ] 模板语法、字段名及关系路径通过 **Check Template**
- [ ] 关系类型、跳数、末端字段类型和循环范围符合限制
- [ ] separator 是预期的纯文本，且 Many2many 示例符合预期
- [ ] Live Preview 已检查真实可读记录（若可用）及空值/多值情况
- [ ] **Save** 已成功；需要时 **Apply Changes** 或完成 **Validate / Publish**
- [ ] Published 状态和 pending 状态符合预期
- [ ] 普通目标用户已完成实际搜索验证
- [ ] 模板未包含不应暴露的敏感字段

## 9. 相关契约和手册

- [CC-014：卡片模板设计器与实时预览](../../context/intent/CC-014_result_card_template_designer.md)
- [CC-014-1：关系字段多级解析](../../context/intent/CC-014-1_relation_field_multi_level.md)
- [CC-003：搜索权限边界](../../context/intent/CC-003_global_search_permission_boundary.md)
- [CC-013：Result Card 与 Native Form 导航](../../context/intent/CC-013_search_result_card_native_form_navigation.md)
- [配置与搜索管理员手册](./CC-001_configuration_admin_guide.md)

版本兼容性：本手册以 Odoo 18 CE、`wd_global_search` 18.0.1.3.0 和 CC-014 / CC-014-1
v0.1 为基线。升级模块或配置格式时，先按 [CC-010 升级策略](../../context/intent/CC-010_global_search_upgrade_strategy.md)
执行升级和回归确认；不要仅凭旧版模板可打开，就推断新版本中的发布和渲染行为完全相同。

## 10. 性能与最佳实践

### 性能建议

- 只展示帮助用户识别结果所需的标题和摘要字段。
- 关系路径保持在契约允许的深度内；不要重复展示大量关联信息。
- 控制模板变量和循环数量，并避免不必要的嵌套循环。
- 列表字段只输出必要内容；多值 separator 使用简洁分隔符。
- 如卡片渲染变慢，先用较短模板逐步恢复字段和循环，定位成本较高的部分，再按项目流程验证。

### 模板最佳实践

- 把主标识字段放在第一行，辅助信息放在后续行。
- 明确标注状态、日期和金额，使用合适的格式键。
- 使用一致的纯文本 separator 展示 Many2many 多值。
- 避免卡片堆叠过多字段；不要加入业务用户无权查看的敏感信息。
- 每次仅改动一个 Resource 的模板，完成预览、发布和目标用户验证后再继续。

## 11. 术语表

| 术语 | 含义 |
|---|---|
| Business Resource | 配置中的业务资源；卡片模板按 Resource 保存 |
| Result Card | 全局搜索结果中的摘要卡片 |
| Card Template | 用常量、字段变量和受限循环定义卡片内容的模板 |
| Field Variable | 以花括号表示的字段引用，例如 `{name}` |
| Format Key | 字段值的内建显示格式，例如 `date` 或 `monetary` |
| Relation Path | 以点号连接的受限关系字段路径，例如 `{partner_id.city}` |
| One2many Loop | 使用开闭标签遍历关联行的循环块 |
| Separator | Resource 级纯文本 Many2many 多值分隔符 |
| Published Configuration | 搜索运行时使用的已发布配置快照 |
| Synthetic example | 依据字段类型生成、不读取真实业务记录的预览示例 |

## 12. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| v0.1 | 2026-10-12 | 初始管理员操作手册 |
| v0.2 | 2026-10-12 | 根据评审增加快速入门、格式键说明、更多实例、深度示例、预览/权限说明、发布排障、检查清单和最佳实践 |
