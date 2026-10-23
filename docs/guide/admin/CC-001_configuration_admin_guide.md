# Global Search 配置与搜索验证手册

本手册面向配置管理员和验收人员，覆盖配置发布、搜索验证和常见失败排查。
配置基础契约见 [CC-001](../../context/intent/CC-001_global_search_configuration_foundation.md)；
本手册不改变任何 Coding Contract。

## 权限

配置管理员需要 `Global Search Configuration Manager` 组。普通用户不直接读取配置模型；搜索运行时由后续 Search Service 消费 Published 配置。

## 一、创建 Draft

1. 打开 **Global Search → Configuration Domains**。
2. 创建唯一的 Configuration Domain `key` 和名称。
3. 在 Domain 的 Versions 中创建新的版本号。
4. 在版本中配置 `schema_version=1`，状态保持 `Draft`。
5. 在版本中配置至少一个 Business Resource。
6. 为每个 Resource 配置：
   - Technical Model Mapping；
   - 至少一个 Searchable Field（技术字段名或本手册 §5.4 所述的有限关系路径）；
   - 一个 Business Date Mapping；
   - 必要的 Relation Path、State、Snapshot、Vocabulary 和 Performance 配置。
7. 保存后确认版本仍为 `Draft`。

配置 key、版本号、Resource key、模型映射、字段、关系路径、Business Date 和 Vocabulary 的唯一性由 ORM 约束保护。

## 二、校验和发布

- 校验动作检查模型、Searchable Field 路径及类型、Relation Path、Business Date、索引策略、
  优先级、评分和性能上限。
- 校验失败时版本进入 `REJECTED`，错误码和原因保存在版本及 Audit Event；当前 Published 版本不受影响。
- 校验通过后发布版本。Published 版本生成 canonical JSON snapshot、SHA-256 checksum，并受 1 MB 大小上限保护。
- 同一 Configuration Domain 同时只能有一个 Published 版本；发布新版本会将旧版本置为 `RETIRED`。
- Published 和 Retired 版本不可原地修改。需要修订时创建新版本。

发布后记录以下信息，供搜索验证和问题定位使用：

- Domain key；
- Published version；
- Published checksum；
- Published 时间和操作用户；
- Audit Event 中的 `publish` 动作。

## 三、停用和修订

对 Published 版本执行停用后，版本进入 `RETIRED`。本 CC 不提供从 Retired 直接恢复为 Published 的回滚 UI；此类需求必须进入后续 Coding Contract。

## 四、审计

发布、停用、拒绝和缓存失效会记录 Audit Event。审计只记录请求、用户、版本、checksum、动作和错误元数据，不记录业务字段值、记录数量、SQL 或权限规则内容。

## 五、搜索验证

### 5.1 前置检查

1. 使用具有业务数据读取权限的测试用户登录 Odoo。
2. 确认配置 Domain 存在 Published 版本，并记录其 version/checksum。
3. 打开 Global Search Workspace：
   `http://<odoo-host>:<port>/wd_global_search`
4. 确认浏览器使用当前 Odoo 用户的语言和时区；请求体中的 `lang`、`tz`、
   `uid` 和 `company_id` 不作为上下文来源。

### 5.2 基础搜索

使用一个已知业务值执行搜索，例如 `Acme`：

1. 在 Search query 输入 `Acme` 并提交；
2. 确认 Query Understanding 显示结构化条件，例如 `name=Acme`；
3. 确认结果按 Business Resource 分组；
4. 确认结果数量和分页信息存在；
5. 点击一条结果，确认右侧显示 `READ ONLY · FORM VIEW`；
6. 确认 Preview 显示字段标签和值，但没有编辑、保存、删除、Chatter、
   附件或活动写入口。

### 5.3 Refinement 验证

分别验证以下场景，并记录返回结果：

| 场景 | 操作 | 预期 |
|---|---|---|
| Resource | 选择 Contacts、Sales Orders 或 Transfers | 只显示所选资源 |
| Date | 选择 Today、This week 或 This month | 使用当前用户时区计算范围 |
| State | 选择 Draft、Confirmed 或 Done | 只显示映射后的业务状态 |
| 清空 | 修改 Raw Query | 旧 Refinement 被清空 |
| 空结果 | 输入不存在的值 | 显示 `EMPTY`，不显示虚假结果 |
| 部分失败 | 注入/模拟不可用资源 | 显示 `PARTIAL_SUCCESS` 和安全错误信息 |

### 5.4 多级 Searchable Field 路径

Searchable Field 可以是根模型上的直接字段，也可以是配置中完整、有限的关系路径，例如：

| Resource 根模型 | `field_name` 示例 | 路径含义 |
|---|---|---|
| `sale.order` | `partner_id.city` | 客户城市 |
| `sale.order` | `partner_id.country_id.name` | 客户国家名称 |
| `sale.order` | `order_line.product_id.name` | 任意订单明细产品名称 |
| `res.partner` | `category_id.name` | 任意联系人标签名称 |

路径必须使用真实 Odoo 技术字段名；Sale Order 的 One2many 字段是 `order_line`，不是
展示名或自行猜测的 `order_line_ids`。路径末端必须是受支持、已存储的普通字段。只允许
有限的 Many2one、Many2many、One2many 形态；不支持索引、条件、表达式、函数或方法调用。

Many2many / One2many 路径在同一行的 **Collection Match** 中选择：

- **Any related record**：至少一条当前用户可读的关联记录满足任一查询值；
- **All query values**：每个不同查询值都必须匹配，可由不同关联记录分别满足。

集合策略属于该 Searchable Field 的 Published 配置；不需要为新字段路径另建 Relation Path。
既有 Relation Path 仍保留 `name` 搜索扩展用途。`max_relation_depth` 默认是 2；三条关系边
的路径必须在该 Resource 的 Performance Config 中明确配置至少 3，并仍受 Search Service
时间和结果预算限制。

在版本的 **Performance** 页新增一行，`resource_key` 必须与 Business Resource 的 key 完全
一致；将 `max_relation_depth` 设为 3 才能发布总关系深度为 3 的路径。其余预算值只能收紧
服务端上限，不能扩大结果数或超时预算。默认没有配置行时，`max_relation_depth=2`。

结构化条件继续使用既有 SearchRequest 的 dimension，例如 `dimension="partner_id.city"`、
`value="Fremont"`；dimension 必须与已发布配置中的完整 `field_name` 完全一致。客户端不得
提供 ORM domain、拆解路径或添加新的 API 路由。

路径搜索、Count 与结果取回均按当前搜索用户权限执行。关联模型 Record Rule 必须实际约束
匹配；配置预览或管理员可见不代表普通用户可见。索引策略只声明策略，不表示 Publish 会
创建物理索引；索引部署仍须遵循 CC-006 的受控流程。

### 5.5 边界验证

以下请求应返回 `INVALID_REQUEST`，且错误消息不得回显原始输入：

- Raw Query 超过 500 字符；
- 条件总数超过 20；
- 条件嵌套超过 3 层；
- Relation Path 超过 2 层；
- 多级 Searchable Field dimension 超过 100 字符或不是已发布、当前用户可用的字段路径；
- `query` 不是服务端定义的文本类型；
- Query 包含被边界协议禁止的控制字符。

Model、Field、Operator、Domain Structure 和 Permission Context 必须来自服务端
Published Configuration / UserContext；客户端不得通过请求体指定这些内容。

### 5.6 权限和 Preview 验证

使用普通用户、不同公司用户或 Portal 用户重复执行基础搜索：

- 无权资源不应泄露结果；
- 无权字段不应出现在结果或 Preview；
- 记录被删除或失去权限时显示 `PERMISSION_OR_DELETED`；
- 不使用 `sudo()` 绕过业务权限；
- 不应出现跨用户、跨公司或跨字段的数据泄露。

## 六、失败排查

| 现象 | 优先检查 |
|---|---|
| Search unavailable | Odoo 服务、模块升级、JSON-RPC envelope 和浏览器 Network |
| 没有结果 | Published version、Resource scope、用户权限、Business Date |
| 配置被拒绝 | rejection code/message、模型字段、Relation Path 和 index strategy |
| Preview 不可用 | 当前用户权限、记录是否仍存在、资源 key 是否匹配 |
| 日期结果异常 | Odoo 用户 `tz`、Business Date Mapping 和语言周起始 |
| 需要修改 Published | 创建新版本，不要直接写入 Published/Retired 记录 |

## 七、验证记录

每次验证至少记录：

- 数据库名、模块版本和 Git commit；
- 测试用户角色、公司、语言和时区；
- Domain key、Published version 和 checksum；
- Query、Resource、Date、State refinement；
- 结果状态、错误码、Preview 安全状态；
- 浏览器、viewport 和截图/日志位置。

本项目 CC-011 验收数据集和实际生成报告见：

- [TV-07 README](../../../mymodules/wd_tv_global_search/tv_07_final_acceptance_dataset/README.md)
- [TV-07 REPORT](../../../mymodules/wd_tv_global_search/tv_07_final_acceptance_dataset/reports/REPORT.md)

详细协议和最终验收状态见：

- [CC-007 错误与部分失败](../../context/intent/CC-007_global_search_error_partial_failure.md)
- [CC-009 国际化与时区](../../context/intent/CC-009_global_search_i18n_timezone.md)
- [CC-011 最终验收](../../context/intent/CC-011_global_search_final_acceptance.md)
