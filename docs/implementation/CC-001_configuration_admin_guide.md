# CC-001 配置管理员操作说明

本说明对应已冻结的 [CC-001](../context/intent/CC-001_global_search_configuration_foundation.md)，仅覆盖配置基础。它不提供搜索、Preview 或业务数据操作说明。

## 权限

配置管理员需要 `Global Search Configuration Manager` 组。普通用户不直接读取配置模型；搜索运行时由后续 Search Service 消费 Published 配置。

## 创建 Draft

1. 打开 **Global Search → Configuration Domains**。
2. 创建唯一的 Configuration Domain `key` 和名称。
3. 在 Domain 的 Versions 中创建新的版本号。
4. 在版本中配置至少一个 Business Resource。
5. 为每个 Resource 配置：
   - Technical Model Mapping；
   - 至少一个 Searchable Field；
   - 一个 Business Date Mapping；
   - 必要的 Relation Path、State、Snapshot 和 Vocabulary。
6. 保存后，版本保持 `Draft`。

配置 key、版本号、Resource key、模型映射、字段、关系路径、Business Date 和 Vocabulary 的唯一性由 ORM 约束保护。

## 校验和发布

- 校验动作检查模型、字段、Relation Path、Business Date、索引策略、优先级、评分和性能上限。
- 校验失败时版本进入 `REJECTED`，错误码和原因保存在版本及 Audit Event；当前 Published 版本不受影响。
- 校验通过后发布版本。Published 版本生成 canonical JSON snapshot、SHA-256 checksum，并受 1 MB 大小上限保护。
- 同一 Configuration Domain 同时只能有一个 Published 版本；发布新版本会将旧版本置为 `RETIRED`。
- Published 和 Retired 版本不可原地修改。需要修订时创建新版本。

## 停用

对 Published 版本执行停用后，版本进入 `RETIRED`。本 CC 不提供从 Retired 直接恢复为 Published 的回滚 UI；此类需求必须进入后续 Coding Contract。

## 审计

发布、停用、拒绝和缓存失效会记录 Audit Event。审计只记录请求、用户、版本、checksum、动作和错误元数据，不记录业务字段值、记录数量、SQL 或权限规则内容。
