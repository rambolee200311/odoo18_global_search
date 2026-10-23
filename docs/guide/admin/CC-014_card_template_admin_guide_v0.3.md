# Global Search Structured Result Card 管理员操作手册（v0.3）

本手册说明配置管理员如何配置 Structured Result Card，并按普通搜索用户权限验证结果。
新建或更新 Resource 应优先使用结构化卡片区域。历史纯文本模板仍受运行时兼容支持，但不应把旧设计器流程当作新配置的默认路径。

| 项 | 内容 |
|---|---|
| 手册版本 | v0.3 |
| 文档状态 | FROZEN |
| 批准冻结 | 用户批准；2026-10-15 18:22 +08:00 |
| 适用模块 | `wd_global_search` 18.0.1.3.0（Odoo 18 CE） |
| 契约基线 | CC-014 v0.1、CC-014-1 v0.1、CC-017-1 v1.0.1 |
| 代码核对基线 | CC-018 完成后的 `09a96a7` |
| 更新日期 | 2026-10-15 |

**适用范围：** 本手册面向 Global Search Configuration Manager 配置管理员及受委托的实施顾问。普通搜索用户只验证搜索结果，不编辑配置。开发工程师应以冻结 Coding Contract、实现代码和测试为准。

**代码核对说明：** 已根据 CC-018 后的 Resource 表单、卡片校验与序列化代码核对本手册。CC-018 是结构重构；卡片的新旧模式和用户可见行为以 CC-017-1 及当前代码为准。

相关实现：[configuration_views.xml](../../../mymodules/wd_global_search/views/configuration_views.xml)、[business_resource.py](../../../mymodules/wd_global_search/models/business_resource.py)、[template.py](../../../mymodules/wd_global_search/services/template.py)、[card.py](../../../mymodules/wd_global_search/services/card.py)、[workspace_results.js](../../../mymodules/wd_global_search/static/src/js/workspace_results.js)。

## 0. 五分钟快速入门

1. 使用具有 **Global Search Configuration Manager** 权限的账号，打开 **Global Search → Configuration Domains**。
2. 进入目标 Domain 和 Version，再打开 **Business Resources** 中的目标 Resource。
3. 选择 **Structured Result Card** 区域。
4. 在 **Structured Card Title** 中填写包含字段变量的标题；按需要填写 **Structured Card Meta**、**Structured Card Summary** 和 **Structured Card Details**。
5. 保存 Resource。Draft 版本按 **Validate / Publish** 流程发布；Published/Retired 版本有待应用修改时，在 Version 上执行 **Apply Changes**。
6. 发布或应用成功后，以普通搜索用户打开 `/wd_global_search`，搜索该 Resource 的记录并检查卡片内容。

Structured Result Card 表单没有单独的 **Live Preview** 或 **Check Template** 按钮。不要把表单保存等同于发布；以 Validate/Publish 或 Apply 成功及目标用户搜索验证为准。

## 1. 权限与配置位置

1. 使用 Global Search Configuration Manager 账号。该配置组允许维护配置，不扩大业务记录或字段的读取权限。
2. 打开 **Global Search → Configuration Domains**，选定目标 Domain 和 Version。
3. 在 **Business Resources** 中打开 Resource，核对 `key`、Primary Model 或 Model Mappings，以及当前 Version 状态。
4. 在 Resource 表单的 **Structured Result Card** 区域编辑 **Structured Card Title**、**Structured Card Meta**、**Structured Card Summary** 和 **Structured Card Details**。

配置管理员预览或配置时可读取的内容，不代表普通搜索用户也有权读取。生产卡片仍按执行搜索的用户权限生成。

## 2. 选择卡片模式

一个 Resource 必须使用且只能使用一种卡片配置模式：

| 模式 | 用途 | 当前行为 |
|---|---|---|
| **Structured Result Card** | 新建或更新 Resource 的首选模式 | 显式配置 Title、Meta、Summary、Details；Search API 返回结构化 `snapshot.card` |
| **Legacy plain-text template** | 兼容既有配置 | 既有 `card_template` 继续按纯文本语义渲染；不自动转换为结构化区域 |

新建 Resource 请填写 Structured Result Card 的 **Title**。Title 不能为空，且必须至少包含一个字段变量。不要同时保留有效的 Legacy Template 和 Structured Result Card 配置。

已有 Legacy Resource 的配置转换规则：

1. 在目标 Resource 中填写并保存有效的 Structured Result Card 字段。
2. 检查出现的 **Use Structured Result Card** 按钮及其确认提示。该操作会清除暂存配置中的 Legacy Template；继续前确认目标 Resource、Version 和变更范围。
3. 按 Version 状态执行 Validate/Publish 或 Apply Changes。
4. 只有校验和发布/应用成功后，结构化模式才成为活动配置；失败时不要假设切换已生效。

Legacy Template 的运行时兼容不等于所有旧设计器操作入口仍适用于新模式。旧版手册 [CC-014 v0.2 卡片模板设计器指南](./CC-014_card_template_admin_guide.md) 仅供核对历史纯文本设计器行为；本手册的标准配置路径是 Structured Result Card。

## 3. 结构化卡片区域

| 区域 | Resource 表单字段 | 要求和用途 |
|---|---|---|
| **Title** | **Structured Card Title** | 必填；必须包含字段变量。显示为卡片标题 |
| **Meta** | **Structured Card Meta** | 可选；用于短元数据，如单号、日期或状态 |
| **Summary** | **Structured Card Summary** | 可选；用于一行或多行摘要 |
| **Details** | **Structured Card Details** | 可选；内容必须位于一个顶层 One2many 循环中，用于显示关联明细 |

各区域使用既有卡片模板语法。字段名应以当前 Resource 的模型字段为准，不要根据示例猜测字段是否存在或可读。

示例（字段适用于 `sale.order` 时）：

```text
Title:   {name}
Meta:    Sales Order · {date_order:datetime}
Summary: {partner_id.name} · {amount_total:monetary}
Details: {order_line}{product_id.name} × {product_uom_qty}{/order_line}
```

管理界面分别提供表中列出的字段；区域名称仅用于说明用途，不是应输入到模板中的前缀。

## 4. 语法、限制与呈现

- 使用 `{field_name}` 插入字段，关系字段按既有 CC-014-1 路径规则访问。
- 可使用已有格式键，例如 `{date_order:datetime}`、`{amount_total:monetary}`；字段类型和格式键必须兼容。
- 只允许常量文本、字段变量和获准的 One2many 循环。模板不执行 HTML、JavaScript、Python、函数调用或计算表达式。
- 只有 **Details** 可以包含循环；非空 Details 必须包含一个顶层 One2many 循环。
- Structured Result Card 的各区域合计不得超过 8 KiB、最多 50 次变量引用；还须通过字段、类型、路径和权限校验。
- Details 最多输出前三个当前用户可读的明细项。若还有更多可读项，卡片显示 `...` 截断标记；这只影响卡片展示，不改变搜索结果、Count 或分页。
- Many2many 路径使用 Resource 级纯文本 separator，默认值为 `, `。当前 Structured Result Card 表单不显示 separator 输入框；除非已有获准配置流程明确提供该操作，否则保留默认值，不要通过数据库或隐式提权修改。
- 字段值使用纯文本呈现。Meta 或 Summary 为空时不显示对应区域；无权字段和无权明细不得通过卡片内容或截断行为泄露。

更完整的模板语法、关系路径和格式规则见 [CC-014](../../context/intent/CC-014_result_card_template_designer.md)、[CC-014-1](../../context/intent/CC-014-1_relation_field_multi_level.md) 和 [CC-017-1](../../context/intent/CC-017-1_structured_result_card_template_output.md)。

## 5. 保存、校验和发布

先确认目标数据库、Domain、Version 和 Resource。共享或生产配置变更须按项目授权流程执行。

### Draft Version

1. 保存 Resource 上的 Structured Result Card 字段。
2. 返回 Version，执行 **Validate**。
3. 校验成功后执行 **Publish**。
4. 刷新 Version，确认状态为 Published，并记录 checksum。

### Published/Retired Version 的暂存修改

1. 保存 Resource 修改，并确认 Version 显示 **Pending Changes**。
2. 在目标 Version 执行 **Apply Changes**。
3. Apply 会重新校验并更新活动 Snapshot/checksum。
4. 刷新 Version，确认操作成功、Pending Changes 清除，并记录新 checksum。

Apply/Publish 失败时，旧 Published Snapshot 继续生效。读取界面显示的原始错误信息并修正；不要把待处理修改视为已上线，也不要通过超级用户、`sudo()` 或直接数据库写入绕过校验。

## 6. 普通搜索用户验证

配置管理员的权限预览不能替代搜索用户验证。发布或 Apply 后，使用目标普通搜索用户检查：

1. 打开 `http://<odoo-host>:<port>/wd_global_search`。
2. 搜索目标 Resource 中可读的业务值。
3. 检查结果卡片的 Title、Meta、Summary 和 Details；确认无权或空值字段没有意外暴露。
4. 对 Details 使用的 One2many 关系，检查当前用户可见明细及超过三项时的截断标记。
5. 选择结果打开配置的 Odoo Form，确认导航仍按 Resource 的现有设置工作。
6. 记录数据库、Domain、Version、checksum、用户角色、搜索输入、预期与实际结果。

验证数据应为目标用户有权读取的实际业务数据；不要为了验证修改共享业务记录或放宽 ACL、字段组、Record Rule、公司范围。

## 7. 常见问题

| 现象 | 检查方式 |
|---|---|
| Validate/Apply 提示缺少模板 | 检查 Title 是否填写且包含字段变量；确认没有同时启用 Legacy 和 Structured 两种模式 |
| 字段或关系路径校验失败 | 检查技术字段名、当前模型、字段类型及 CC-014-1 路径限制 |
| Details 校验失败 | 确认循环位于 Details，使用 One2many，且只配置一个顶层循环 |
| Preview 看不到结构化结果 | Structured Result Card 配置页没有独立 Preview；完成 Publish/Apply 后用目标搜索用户搜索验证 |
| 卡片没有显示刚才的更改 | 检查 Version 状态、Pending Changes 和 checksum；Published/Retired 修改需要 Apply |
| 用户看到的字段与管理员不同 | 按搜索用户的 ACL、字段组、Record Rule 和公司范围排查；不要用管理员权限验证代替 |
| 旧卡片模板仍在运行 | Legacy 模板有运行时兼容支持；先确认目标 Resource 的实际模式及 Published Snapshot，不要假设它已自动迁移 |

## 8. 相关文档

- [CC-014：卡片模板设计器与实时预览](../../context/intent/CC-014_result_card_template_designer.md)
- [CC-014-1：关系字段多级解析](../../context/intent/CC-014-1_relation_field_multi_level.md)
- [CC-017-1：Structured Result Card 输出](../../context/intent/CC-017-1_structured_result_card_template_output.md)
- [CC-003：搜索权限边界](../../context/intent/CC-003_global_search_permission_boundary.md)
- [CC-013：Result Card 与 Native Form 导航](../../context/intent/CC-013_search_result_card_native_form_navigation.md)
- [CC-010：升级策略](../../context/intent/CC-010_global_search_upgrade_strategy.md)
- [Searchable Fields 管理员操作手册 v0.3](./CC-014-2_searchable_fields_admin_guide_v0.3.md)
- [配置与搜索验证手册](./CC-001_configuration_admin_guide.md)

## 9. 版本历史

| 版本 | 日期 | 变更 |
|---|---|---|
| v0.3 | 2026-10-15 | 按 CC-018 后当前代码更新为 Structured Result Card 首选操作流程，说明 Legacy 兼容边界、区域语法、发布和普通用户验证；用户批准冻结（2026-10-15 18:22 +08:00）。 |
