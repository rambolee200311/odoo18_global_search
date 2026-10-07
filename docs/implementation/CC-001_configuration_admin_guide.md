# Global Search 配置与搜索验证手册

本手册面向配置管理员和验收人员，覆盖配置发布、搜索验证和常见失败排查。
配置基础契约见 [CC-001](../context/intent/CC-001_global_search_configuration_foundation.md)；
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
   - 至少一个 Searchable Field；
   - 一个 Business Date Mapping；
   - 必要的 Relation Path、State、Snapshot 和 Vocabulary。
7. 保存后确认版本仍为 `Draft`。

配置 key、版本号、Resource key、模型映射、字段、关系路径、Business Date 和 Vocabulary 的唯一性由 ORM 约束保护。

## 二、校验和发布

- 校验动作检查模型、字段、Relation Path、Business Date、索引策略、优先级、评分和性能上限。
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

### 5.4 边界验证

以下请求应返回 `INVALID_REQUEST`，且错误消息不得回显原始输入：

- Raw Query 超过 500 字符；
- 条件总数超过 20；
- 条件嵌套超过 3 层；
- Relation Path 超过 2 层；
- `query` 不是服务端定义的文本类型；
- Query 包含被边界协议禁止的控制字符。

Model、Field、Operator、Domain Structure 和 Permission Context 必须来自服务端
Published Configuration / UserContext；客户端不得通过请求体指定这些内容。

### 5.5 权限和 Preview 验证

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

详细协议和最终验收状态见：

- [CC-007 错误与部分失败](../context/intent/CC-007_global_search_error_partial_failure.md)
- [CC-009 国际化与时区](../context/intent/CC-009_global_search_i18n_timezone.md)
- [CC-011 最终验收](../context/intent/CC-011_global_search_final_acceptance.md)
