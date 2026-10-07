# CC-010 Global Search 升级策略

## 0. 文档治理

| 项 | 内容 |
|---|---|
| Coding Contract | CC-010 |
| 版本 | v0.1 DRAFT |
| 状态 | DRAFT，待评审和批准冻结 |
| Intent ID | `GS-SEARCH-UPGRADE-STRATEGY` |
| 上游 SRS | [SRS_global_search](../../requirement/SRS_global_search.md) v1.4 FROZEN |
| 上游 TDD | [TDD_global_search](../../design/TDD_global_search.md) v0.3 FROZEN |
| 实施计划 | [IMPLEMENTATION_PLAN_global_search](../../implementation/IMPLEMENTATION_PLAN_global_search.md) v0.2 FROZEN，Phase 10 |
| 前置 CC | CC-001~CC-009；TD-001 |
| 模块 | `wd_global_search` |
| 目标 | 提供可验证、可回滚的配置、数据和索引升级流程 |

本 CC 只处理升级前检查、Odoo migration、配置/索引迁移、验证和回滚，不改变搜索语义、权限边界或业务数据所有权。

## 1. 范围与约束

### 1.1 在范围内

- Odoo 模块版本升级和 migration 入口；
- Global Search 配置模型和 Published Snapshot 的兼容迁移；
- 索引创建、变更、校验和失败恢复；
- 升级前备份清单与升级后验证清单；
- 隔离数据库上的升级与回滚演练；
- 迁移审计和可追踪结果。

### 1.2 超出范围

- 修改 `odoo/` 或官方 addons；
- 直接读写数据库或绕过 ORM 权限；
- 使用 `sudo()` 读取业务数据；
- 引入 Elasticsearch、OpenSearch、LLM 或向量检索；
- 无备份强制升级、不可审计的手工 SQL 或静默丢弃配置。

## 2. 升级不变量

1. 升级前必须确认数据库备份可恢复，并记录备份标识；
2. Published 配置、版本号和 checksum 在无迁移需求时保持不变；
3. 旧配置无法安全转换时进入显式 `REJECTED`，不得伪造为 Published；
4. ACL、Record Rule、字段权限和 Permission Boundary 不得放宽；
5. 索引迁移失败必须可识别，既有可用索引不得被静默删除；
6. 每个迁移步骤可重复执行，或明确记录为不可重复并阻止重入；
7. 升级失败必须保留错误码、迁移版本和审计事件。

## 3. Migration 契约

### 3.1 入口

- 使用 Odoo 模块标准 migration 目录和版本机制；
- migration 只调用模型、模块和受控索引 helper；
- 不接受来自请求体、环境变量或浏览器的迁移参数；
- 迁移版本由模块版本和服务端代码确定。

### 3.2 配置迁移

- 迁移 Domain、Resource、Field、State Mapping 和 Published Snapshot；
- 保留稳定业务 key、版本、状态和 checksum；
- 缺少必需字段、冲突 key 或非法关系时失败关闭并进入 `REJECTED`；
- 不自动发布未经验证的配置；
- 迁移前后执行配置完整性和 checksum 校验。

### 3.3 索引迁移

- 只为已发布且可验证的字段生成索引；
- 创建新索引后再切换使用，避免先删除旧索引；
- 索引名称、字段和策略必须可追踪；
- 部分失败时保留旧索引并报告失败，不返回成功形状；
- 索引迁移不改变 ORM 查询权限和业务结果语义。

## 4. 备份、验证与回滚

### 4.1 升级前

- 记录数据库、模块版本、Git commit、Published 配置 checksum 和索引清单；
- 完成可恢复性抽样验证；
- 确认维护窗口、停止写入策略和回滚负责人；
- 保存迁移计划、输入版本和审计 request id。

### 4.2 升级后

- 模块加载和 migration 状态为成功；
- 所有 Published 配置可读，checksum 与预期一致；
- ACL、权限失败关闭、Search/Cancel、分页和错误协议回归通过；
- 索引存在、策略正确且查询结果与基线一致；
- audit_log 记录迁移开始、成功、失败和回滚。

### 4.3 回滚

- 迁移失败立即停止后续步骤；
- 优先恢复备份并重新执行验证，不执行未经批准的临时修复；
- 若支持应用层回滚，必须按逆向版本明确恢复配置和索引；
- 回滚完成后必须重新验证 Published、ACL、checksum 和搜索结果；
- 回滚失败必须保持系统不可发布并显式告警。

## 5. 测试契约

| ID | 内容 | 类型 | 预期 |
|---|---|---|---|
| CC10-TEST-001 | 旧配置读取 | Odoo 集成 | 可读或显式 REJECTED |
| CC10-TEST-002 | 配置 checksum 保持 | Odoo 集成 | 升级前后符合预期 |
| CC10-TEST-003 | 索引迁移成功 | 隔离数据库 | 新索引可用，旧索引安全切换 |
| CC10-TEST-004 | 索引迁移失败 | 故障注入 | 旧索引保留，状态失败 |
| CC10-TEST-005 | ACL 与 Published 回归 | Odoo+TV | 不放宽权限 |
| CC10-TEST-006 | 完整升级演练 | 隔离数据库 | 升级、验证、回滚均有证据 |
| CC10-TEST-007 | 审计与日志 | Odoo | 不记录业务输入，事件完整 |

## 6. 验收与冻结门槛

- migration 通过 Odoo 标准加载；
- 升级前备份和恢复演练通过；
- 配置、索引、ACL、Published、checksum 验证通过；
- 故障注入后可恢复，且无静默成功；
- 不修改官方 addons；
- 完成 IHR、ATR、HVR 和隔离数据库报告；
- 未通过回滚演练不得进入发布状态。

未经用户批准冻结，不得实施 CC-010。
