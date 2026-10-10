# CC-001 Global Search 配置基础

## 0. 文档治理

| 项 | 内容 |
|---|---|
| Coding Contract | CC-001 |
| 版本 | v1.1 |
| 状态 | FROZEN — AMENDMENT |
| 上游 SRS | [SRS_global_search](../../requirement/SRS_global_search.md) V1.5 FROZEN |
| 上游 TDD | [TDD_global_search](../../design/TDD_global_search.md) V0.4 FROZEN — AMENDMENT |
| 实施计划 | [IMPLEMENTATION_PLAN_global_search](../../implementation/IMPLEMENTATION_PLAN_global_search.md) V0.3 FROZEN — AMENDMENT，Phase 0–1 |
| 模块 | `wd_global_search` |
| 目标代码基线 | 本 CC 执行开始时的工作分支 |

本 CC 已获批准冻结，进入实施。它只冻结本轮配置模型与配置发布基础的执行边界，不替代 SRS、TDD 或 Implementation Plan。最终执行结果由 IHR、ATR、HVR 和 FR 记录与判断。

## 1. 变更概述

| 字段 | 值 |
|---|---|
| Intent ID | `GS-CONFIG-FOUNDATION` |
| 工作类型 | 新功能 |
| 变更类型 | 结构变更 |
| 目标 | 建立 Global Search 的 Odoo 配置模型、管理员权限、发布生命周期、发布校验、快照 checksum 和审计基础，为后续 Search Service 消费 Published 配置提供稳定边界。 |
| 背景 | TDD 已冻结配置域、版本、资源、字段、关联路径、业务日期、状态、Snapshot、Vocabulary、评分和性能配置的逻辑边界；Implementation Plan 要求先完成配置基础，再进入 Search Service。 |

## 2. 上游基线与追溯

### 2.1 SRS 引用

| SRS ID | 标题 | 相关性 |
|---|---|---|
| BR-014 | 配置生命周期 | 在范围内 |
| BR-015 | 配置校验 | 在范围内 |
| CFG-001 | Business Resource 配置 | 在范围内 |
| CFG-002 | Searchable Fields 配置 | 在范围内 |
| CFG-003 | Snapshot 配置 | 在范围内 |
| CFG-005 | 配置权限 | 在范围内 |
| CFG-006 | 默认值配置 | 在范围内 |
| CFG-007 | 配置生命周期 | 在范围内 |
| CFG-010 | 实体评分配置 | 在范围内 |
| CFG-011 | 性能配置 | 在范围内 |
| CFG-012 | Vocabulary 配置 | 在范围内 |
| CFG-013 | Entity 字段配置 | 在范围内 |
| FR-PM-006 | 配置管理员权限 | 在范围内 |
| FR-ER-002 | 结果/错误状态 | 仅作为发布失败错误上下文 |
| NFR-001 | 搜索性能 | 仅作为配置上限和快照大小上下文 |
| NFR-002 | 数据新鲜度 | 仅作为配置发布生效上下文，本轮不宣称完成 |
| CON-010 | 配置变更立即生效 | 仅作为版本和缓存失效上下文 |
| AC-044 | 数据新鲜度 | 仅作为后续发布生效追踪上下文，本轮不宣称完成 |
| AC-045 | Vocabulary 配置生效 | 仅作为后续配置生效追踪上下文，本轮不宣称完成 |

### 2.2 DDD 引用

N/A。本项目当前没有冻结 DDD 文档；不得为本 CC 虚构领域对象或不变式编号。

### 2.3 TDD 引用

| TDD 章节 | 主题 | 相关性 |
|---|---|---|
| §4 | 配置模型设计 | 定义本轮模型范围和约束 |
| §5 | 配置版本与发布设计 | 定义生命周期、发布校验、快照、审计 |
| §6.1 | 当前用户原则 | 定义配置访问不得以 `sudo()` 绕过权限 |
| §11.1 | 配置模型 | 定义使用 Odoo `models.Model`、ACL 和 Record Rule |
| §12.2 | ORM 集成测试 | 定义配置模型验证方式 |
| §12.6 | 测试数据 | 定义隔离、可复现配置 fixture 要求 |

## 3. 范围冻结

### 3.1 在范围内

- 建立 Configuration Domain、Configuration Version 和 Phase 1 所需的 Odoo 配置模型；
- 建立 Business Resource、Technical Model Mapping、Searchable Field、Relation Path、Business Date、State、Snapshot、Vocabulary、Entity、Scoring 和 Performance 配置；
- 普通 Resource 以 Primary Model 定义结果模型，Searchable Fields 直接属于 Resource；Model Mapping 仅服务于显式 Composite Resource，关联子模型使用 Relation Path 搜索且不改变结果模型；
- 建立配置管理员组、ACL 和 Record Rule；
- 实现 Draft、Validating、Published、Retired、Rejected 生命周期；
- 实现发布前结构校验、权限边界校验、引用完整性校验、索引策略兼容性校验和有界配置校验；
- 实现发布失败保留 Draft、标记 Rejected、记录原因且不影响现有 Published 的行为；
- Published/Retired 业务配置修改及 Published 配置域 active 状态变更暂存，不改变当前运行配置；管理员执行 Apply Changes 时完整校验，并原子更新快照、大小、checksum、active 状态和审计；
- 状态、版本身份、运行快照和 checksum 等技术元数据只能由生命周期动作写入；配置域单一 Published 约束；
- 实现 JSON canonical snapshot、checksum、默认 1 MB 大小上限；
- 实现发布、停用、校验失败和缓存失效的审计事件基础；
- 实现配置模型版本兼容性边界：新模块版本可读取受支持的旧配置版本，并将不兼容配置标记为 `REJECTED`；
- 为后续 Search Service 提供只读 Published 配置读取边界和版本校验接口；
- 为上述行为建立 ORM 集成测试和权限回归测试。

### 3.2 超出范围

- Search Service 的条件合并、资源执行、结果去重、计数和错误聚合；
- 业务数据搜索、业务数据写入、业务数据迁移；
- Relation Path 的运行时搜索权限过滤；
- Preview 容器、Form View 加载和前端 Workspace；
- 搜索限流、并发执行、取消、分页 cursor 和搜索 API；
- PostgreSQL 索引创建、迁移和性能补测；
- Vocabulary 的真实搜索接入和 TV-03/TV-06 未完成项；
- 实际历史数据迁移脚本和破坏性迁移；
- 修改 `odoo/` 或官方 addons；
- Elasticsearch、OpenSearch、LLM、向量检索或独立缓存/队列技术。

### 3.3 非目标

- 不在本 CC 内定义新的业务语义；
- 不将配置模型做成业务数据读取的权限旁路；
- 不为普通用户开放配置模型直接读取；
- 不以配置模型完成 Search Service 的实现；
- 不宣称整个 Implementation Plan、TDD、SRS 或项目已完成。

## 4. 变更边界

### 4.1 允许

| 类型 | 详情 |
|---|---|
| Python | `mymodules/wd_global_search/__init__.py`、`models/__init__.py`、`models/*.py`、必要的 `models` 测试文件 |
| XML | `mymodules/wd_global_search/security/*.xml`、`mymodules/wd_global_search/views/*configuration*.xml`、必要的数据文件 |
| Manifest | `mymodules/wd_global_search/__manifest__.py` 的本模块依赖、数据和测试声明 |
| 测试 | `mymodules/wd_global_search/tests/test_configuration*.py` 及隔离测试 fixture |
| 文档 | 本 CC 对应的 IHR、ATR、HVR、FR；必要的配置管理员操作说明 |
| 模型 | 本 CC §3.1 所列配置模型及其约束、生命周期动作和只读 Published 读取边界 |

### 4.2 禁止

| 类型 | 详情 |
|---|---|
| 官方代码 | 禁止修改 `odoo/` 和官方 addons |
| 业务权限 | 禁止使用 `sudo()` 读取或写入业务数据，禁止以管理员环境代替当前用户 |
| 配置访问 | 禁止向普通用户授予配置模型直接读取或修改 ACL |
| 搜索实现 | 禁止在本 CC 内实现 Search Service、业务查询、结果聚合或权限猜测过滤 |
| 公共接口 | 禁止变更 TDD 未授权的前端搜索 API、Preview API 或外部 Adapter |
| 技术栈 | 禁止引入 Elasticsearch、OpenSearch、LLM、向量检索、独立缓存或独立任务队列 |
| 上游基线 | 禁止修改 SRS/TDD 语义以绕过本 CC 的验收失败 |

### 4.3 配置模型命名规范

配置模型统一使用 `wd.gs.` 前缀：

| 配置对象 | Odoo 模型名 |
|---|---|
| Configuration Domain | `wd.gs.config.domain` |
| Configuration Version | `wd.gs.config.version` |
| Business Resource | `wd.gs.business.resource` |
| Resource Model Mapping | `wd.gs.resource.model.mapping` |
| Searchable Field | `wd.gs.searchable.field` |
| Relation Path | `wd.gs.relation.path` |
| Business Date Mapping | `wd.gs.business.date.mapping` |
| State Mapping | `wd.gs.state.mapping` |
| Snapshot Field | `wd.gs.snapshot.field` |
| Vocabulary Entry | `wd.gs.vocabulary.entry` |
| Entity Scoring Config | `wd.gs.entity.scoring.config` |
| Performance Config | `wd.gs.performance.config` |
| Audit Event | `wd.gs.audit.event` |

字段默认使用 `id` 主键、`<model>_id` 外键、`active` 或 `is_<attribute>` 布尔字段、`<attribute>_at` 日期时间字段、`<attribute>_by` 用户字段和 `state` 状态字段。版本使用 `version`，校验和使用 `checksum`。

### 4.4 ACL、数据文件、视图和测试规范

- 配置管理员组为 `wd_global_search.group_config_manager`；对本 CC 配置模型授予明确的 read/write/create/unlink 权限。
- `base.group_user` 对本 CC 配置模型无直接 ACL；`base.group_system` 不因系统管理员身份获得额外的业务数据读取路径。
- Record Rule 仅允许配置管理员访问其授权配置记录；普通用户无配置模型记录可见性。
- 安全 XML 位于 `mymodules/wd_global_search/security/`；配置数据位于 `mymodules/wd_global_search/data/`，只允许组定义、非业务基础元数据和可选的基础 Vocabulary。
- 配置视图位于 `mymodules/wd_global_search/views/`，按模型提供 List、Form、Search、Action 和仅配置管理员可见的 Menu；不复制官方业务 View。
- 测试 fixture 位于 `mymodules/wd_global_search/tests/fixtures/` 或测试模块内，使用唯一标记隔离，并在测试结束验证不污染业务数据。

### 4.5 审计日志规范

审计事件使用 `wd.gs.audit.event` 记录发布、停用、拒绝和缓存失效，至少包含 `request_id`、`user_id`、`config_domain`、`version_id`、`checksum`、`action`、`error_code` 和时间戳。发布/停用使用 INFO，REJECTED 使用 WARNING，未预期失败使用 ERROR。审计不得记录业务字段值、记录数量、Record Rule 内容、SQL、令牌或文件路径。

## 5. 必需的行为变更

| ID | 当前行为 | 期望行为 | CC-CHANGE ID |
|---|---|---|---|
| 1 | 模块没有完整的版本化配置模型 | 配置域、配置版本及 Phase 1 配置实体使用 Odoo `models.Model` 持久化，并具有明确关联和约束 | CC-CHANGE-001 |
| 2 | 无受控配置生命周期 | 配置版本按 Draft → Validating → Published → Retired/Rejected 转换；Published/Retired 业务编辑仅暂存，Apply 完整校验后原子更新运行快照；同一域 Published 唯一 | CC-CHANGE-002 |
| 3 | 无发布前配置校验 | 发布前校验模型、字段、关系路径、Business Date、引用、优先级、索引策略和各项上限；失败关闭，不发布不完整版本 | CC-CHANGE-003 |
| 4 | 无配置访问边界 | 配置管理员可维护配置；普通用户不能直接读取或修改配置模型；Search Service 后续仅消费 Published 配置 | CC-CHANGE-004 |
| 5 | 无可验证快照 | Published 配置生成 canonical JSON、checksum，超过 1 MB 拒绝发布并记录审计 | CC-CHANGE-005 |
| 6 | 无发布审计 | 发布、停用、拒绝和缓存失效记录 request/user/version/checksum、错误码和受影响配置域等非业务数据元信息 | CC-CHANGE-006 |
| 7 | 缺少明确的数据完整性约束 | 配置域、版本、资源、映射、字段、关系路径、日期、状态和 Vocabulary 记录具有唯一性、引用完整性和必填约束 | CC-CHANGE-001 |
| 8 | 无配置版本兼容处理 | 读取配置时识别版本；受支持的旧版本可读取，不兼容配置进入 REJECTED 且不得静默降级 | CC-CHANGE-003 |

### 5.1 数据完整性约束

实现必须至少固化以下约束：

- Configuration Domain：`key` 唯一；
- Configuration Version：`domain_id + version` 唯一，同一 domain 同时只有一个 Published；
- Business Resource：`version_id + key` 唯一；
- Resource Model Mapping：`resource_id + model_name` 唯一，同一 resource 内 priority 唯一；
- Searchable Field：Primary Model 直接配置时 `resource_id + field_name` 唯一；Composite Resource 按 `mapping_id + field_name` 唯一；
- Relation Path：`resource_id + path` 唯一；
- Business Date Mapping：`resource_id + model_name` 唯一；
- State Mapping：`resource_id + business_state` 唯一；
- Vocabulary Entry：`version_id + lang + term` 唯一；
- 所有必需外键、状态字段、版本字段和配置引用不得为空；删除行为不得产生悬空配置。

## 6. 既有行为保留

| ID | 行为 / 契约 | 为什么不得改变 | CC-PRESERVE ID |
|---|---|---|---|
| 1 | 现有只读 Preview 路由及其当前用户权限行为 | 已有 TV-05 有条件通过结果，配置基础不应扩大 Preview 访问面 | CC-PRESERVE-001 |
| 2 | Preview 不提供业务写 API | TDD §7.2 的只读安全边界 | CC-PRESERVE-002 |
| 3 | 现有模块可被 Odoo 加载的 manifest 结构 | Phase 0 基础能力和后续安装路径依赖 | CC-PRESERVE-003 |
| 4 | 业务数据访问不使用 `sudo()` 绕过权限 | SRS/TDD 安全边界和项目纪律 | CC-PRESERVE-004 |

## 7. 适用的 TDD 防护栏

当前 TDD v0.3 未发布独立的 `T-xxx` 编号，本 CC 直接引用冻结章节；不得在实现中自行创建替代编号。

| TDD 防护栏 | 适用性 | 本次落实位置 | 验证方式 |
|---|---|---|---|
| §5.1 生命周期与单一 Published | 适用 | 版本模型约束和动作 | CC-TEST-002 |
| §5.2 发布失败语义 | 适用 | 发布校验与审计 | CC-TEST-003 |
| §5.3 快照版本/checksum | 适用 | Published snapshot provider | CC-TEST-004 |
| §5.4 审计 | 适用 | Audit Event 模型和动作 | CC-TEST-005 |
| §3.11 配置快照 | 适用 | canonical JSON、1 MB 上限和 checksum | CC-TEST-004 |
| §5.5 升级策略 | 部分适用 | 配置版本兼容性和 REJECTED 处理 | CC-TEST-008 |
| §6.1 当前用户原则 | 适用 | ACL、Record Rule、业务数据访问审查 | CC-TEST-006 |
| §11.1 Odoo 标准模型和 ACL | 适用 | `models.Model`、安全 XML、ORM 集成测试 | CC-TEST-001/006 |

## 8. 数据 / 迁移影响

| 字段 | 值 |
|---|---|
| 需要迁移 | 否 |
| 迁移脚本 | N/A |
| 数据源 | N/A；本 CC 仅新增配置模型 |
| 目标 | 新模块配置表和测试 fixture |
| 恢复 / 回滚策略 | 卸载测试模块或回滚本 CC 代码；不得删除或改写业务数据 |
| 验证 | 独立测试数据库安装、升级、卸载 smoke；确认业务模型记录和权限不受影响 |

## 9. API / 集成影响

| 字段 | 值 |
|---|---|
| 修改的端点 | 无；本 CC 不新增搜索或 Preview 端点 |
| 向后兼容 | 是；现有 Preview 端点保持兼容 |
| Adapter 变更 | N/A |
| 内部边界 | 新增仅供后续 Search Service 使用的 Published 配置读取接口，接口不得接受客户端权限上下文 |

## 10. 安全 / 权限影响

| 字段 | 值 |
|---|---|
| 新权限 | 配置管理员组；仅授予配置模型的明确读写权限 |
| 变更的 ACL | 新增配置模型 ACL 和必要的配置版本 Record Rule |
| 普通用户 | 无配置模型直接 ACL；通过后续 Search API 间接使用 Published 配置 |
| 业务数据 | 本 CC 不读取、不写入业务数据；不得使用 `sudo()` 绕过权限 |
| 敏感数据暴露检查 | 不记录业务字段值、记录数量、Record Rule 内容、SQL、令牌或文件路径到用户错误/审计消息 |

## 11. 测试契约

| 测试 ID | 对应变更 | 上游来源 | 测试类型 | 预期结果 | 人工验证 | 原因 |
|---|---|---|---|---|---|---|
| CC-TEST-001 | CC-CHANGE-001/004 | CFG-001~CFG-013、TDD §4/§11.1 | ORM 集成 | 配置管理员可创建配置；普通用户无直接读取/写入权限；模型关联和必填约束生效 | 否 | 核验配置模型和 ACL 基础 |
| CC-TEST-002 | CC-CHANGE-002 | BR-014、CFG-007、TDD §5.1 | ORM 集成 | 状态/版本/运行快照技术字段受保护；Published/Retired 业务修改仅暂存；重复 Published 和非法转换被拒绝 | 否 | 保留运行时版本边界，同时支持受控编辑 |
| CC-TEST-003 | CC-CHANGE-003 | BR-015、TDD §5.2 | ORM 集成 | 无效模型/字段/关系/Business Date/优先级/索引兼容性导致 REJECTED；Draft 保留，当前 Published 不变 | 否 | 固化失败关闭语义 |
| CC-TEST-004 | CC-CHANGE-005 | BR-014、CFG-007、TDD §3.11/§5.3 | 单元 + ORM 集成 | Published 快照为 canonical JSON；发布/Apply checksum 稳定；超 1 MB 拒绝且保留旧活动快照 | 否 | 防止配置不一致和静默截断 |
| CC-TEST-005 | CC-CHANGE-006 | BR-014、BR-015、TDD §5.4 | ORM 集成 | 发布、暂存、Apply 成功/失败、停用和缓存失效产生审计；Apply 记录旧/新 checksum；事件不含业务字段值 | 否 | 满足可追溯性 |
| CC-TEST-006 | CC-CHANGE-004、CC-PRESERVE-004 | CFG-005、TDD §6.1 | 权限回归 | 普通用户无法通过模型、关联或 RPC 直接读取配置；实现未使用 `sudo()` 读取业务数据 | 否 | 防止权限旁路 |
| CC-TEST-007 | CC-PRESERVE-001/002/003 | TV-05、TDD §7 | 回归 + smoke | 现有 Preview 路由加载、只读边界和模块安装路径不回归 | 是 | 保护既有实现 |
| CC-TEST-008 | CC-CHANGE-001/003 | CFG-001~CFG-013、TDD §5.5 | ORM 集成 | 唯一约束、外键/引用约束、必填约束生效；受支持旧配置可读取；不兼容配置为 REJECTED | 否 | 防止配置污染和升级回退 |

## 12. 停止条件 / 升级闸门

本 CC 执行中出现以下情况必须停止自行扩展：

| 触发条件 | 升级路径 |
|---|---|
| 需要改变配置字段的业务含义或新增 SRS 未定义语义 | 回到 SRS 修订 |
| TDD 配置模型无法表达某项 SRS MUST | 回到 TDD 修订 |
| 需要为配置读取使用 `sudo()`，或需要管理员环境读取业务数据 | 停止并进行安全评审；不得绕过 |
| 需要改变 Search Service、Preview 或公共 API | 新建/修订对应 CC，并回到 TDD 追溯 |
| 需要修改官方代码、引入外部搜索技术或独立基础设施 | 停止；不在本项目范围内 |
| 需要迁移既有业务数据 | 停止并建立独立迁移 CC |
| 需要从 RETIRED 恢复到 PUBLISHED 的业务回滚 | 进入后续 CC；若涉及技术边界变化则先修订 TDD；本 CC 只实现状态模型，不实现回滚 UI |

## 13. 完成定义 / 关闭标准

| ID | 标准 | 闸门类型 |
|---|---|---|
| 1 | 所有 CC-CHANGE-001 至 CC-CHANGE-006 均有实现和 IHR 记录 | 硬闸门 |
| 2 | CC-TEST-001 至 CC-TEST-008 均执行并有 ATR 证据；失败项未被静默忽略 | 硬闸门 |
| 3 | 配置管理员、普通用户、非法配置和 Published 隔离场景均有 ORM 测试证据 | 硬闸门 |
| 4 | 现有 Preview 和模块安装 smoke 未回归 | 硬闸门 |
| 5 | 无官方代码修改、无业务权限旁路、无超出 Scope 的文件变更 | 硬闸门 |
| 6 | 如测试或实现发现上游缺口，已按 §12 升级，不以 CC-DEC 私自改变上游语义 | 硬闸门 |
| 7 | 配置管理员操作说明已完成，覆盖 Draft 创建、校验、发布、停用和 REJECTED 处理 | 硬闸门 |

## 14. 追溯矩阵

### 14.1 正向：In-Scope 上游 → CC

| 上游 ID | CC-CHANGE ID | 备注 |
|---|---|---|
| BR-014 | CC-CHANGE-002/005/006 | 生命周期、版本和审计 |
| BR-015 | CC-CHANGE-003/006 | 发布校验和审计 |
| CFG-001/002/003 | CC-CHANGE-001/003 | Resource、字段和 Snapshot |
| CFG-005/006/007 | CC-CHANGE-002/004 | 权限、默认值和生命周期 |
| CFG-010/011/012/013 | CC-CHANGE-001/003/005 | 评分、性能、Vocabulary 和 Entity |
| TDD §4/§5 | CC-CHANGE-001/002/003/005/006 | 配置和发布技术边界 |
| TDD §6.1/§11.1 | CC-CHANGE-004 | ACL 与权限边界 |

### 14.2 反向：CC → 上游

| CC ID | 上游 ID | 类型 |
|---|---|---|
| CC-CHANGE-001 | CFG-001/002/003/010/011/012/013 | SRS |
| CC-CHANGE-002 | BR-014、CFG-007、TDD §5.1 | SRS/TDD |
| CC-CHANGE-003 | BR-015、TDD §5.2 | SRS/TDD |
| CC-CHANGE-004 | CFG-005、TDD §6.1/§11.1 | SRS/TDD |
| CC-CHANGE-005 | BR-014、TDD §3.11/§5.3 | SRS/TDD |
| CC-CHANGE-006 | BR-014/BR-015、TDD §5.4 | SRS/TDD |

### 14.3 无 DDD 路径

本 CC 执行 `SRS → TDD → CC → TEST → IHR/ATR/HVR → FR` 链路；DDD 为 N/A。

- SRS：需求来源；
- TDD：技术边界；
- CC：本轮执行契约；
- TEST：本节定义的测试契约；
- IHR（Implementation Handover Record）：记录实现过程中实际发生的变更与契约关系；
- ATR（Acceptance Test Report）：记录自动化验收测试在代码基线上的执行事实；
- HVR（Human Verification Report）：记录需要人工验证的行为和证据；
- FR（Final Report）：基于上述证据判断本 CC 是否闭环。

## 附录 A — 变更决策

| CC-DEC ID | 决策 | 考虑的替代方案 | 理由 |
|---|---|---|---|
| CC-DEC-001 | 将首轮范围限制为配置基础，不在同一 CC 实现 Search Service 或 Preview | 将 Phase 1–4 合并为一份大 CC | Implementation Plan 已定义阶段依赖；拆分可使权限、错误协议和浏览器证据分别闭环 |
| CC-DEC-002 | 普通用户不直接读取配置模型 | 给予普通用户 Published 配置只读 ACL | 与 TDD v0.4 的安全边界一致，减少配置元数据泄露面 |
| CC-DEC-003 | 本轮只建立索引策略配置校验，不创建 PostgreSQL 业务索引 | 在配置模型 CC 内同步执行索引迁移 | 索引迁移有独立性能、回滚和环境门禁，应由后续 CC 负责 |
| CC-DEC-004 | 直接引用 TDD 章节，不虚构当前尚未发布的 `T-xxx` 编号 | 为本 CC 临时创建 T-xxx | 保持 TDD 作为 Guardrail 的单一事实源 |
| CC-DEC-005 | 普通 Resource 直接配置 Primary Model 和 Searchable Fields；关联子模型只通过 Relation Path 搜索；Model Mapping 保留给显式合并多个独立结果模型的 Composite Resource | 要求所有 Resource 经 Model Mapping 配置，或把父子关系当作 Composite | 用户确认调拨单等结果应保持根业务模型；关系匹配不能改变返回记录类型 |
| CC-DEC-006 | Published/Retired 业务编辑暂存，只有显式 Apply 在全量校验后原子刷新快照/checksum | 直接修改运行快照或禁止 Published 编辑 | 用户批准的配置管理行为；Search 在 Apply 前保持旧快照 |

## 附录 B — 术语表

| 术语 | 含义 |
|---|---|
| Configuration Domain | 一组可独立发布的 Global Search 配置 |
| Published | Search Service 当前选择的版本；其已应用快照在下一次成功 Apply 前保持不变 |
| REJECTED | 发布校验失败但保留供管理员修订的版本状态 |
| Snapshot | Published 配置的 canonical JSON 表示及 checksum |

## 附录 C — 版本历史

| 版本 | 日期 | 变更说明 | 状态 |
|---|---|---|---|
| v0.1 | 2026-10-03 | 起草 CC-001，冻结 Phase 1 配置基础的范围、边界、测试和停止条件 | Draft |
| v0.2 | 2026-10-04 | 根据评审补充 SRS 上下文、版本兼容性、数据完整性、命名/ACL/视图/fixture/日志规范、CC-TEST-008、回滚闸门和文档完成闸门 | Draft |
| v1.0 | 2026-10-04 | 获批准冻结并进入 Phase 1 配置基础实施 | FROZEN |
| v1.1 | 2026-10-10 | 按用户批准修订 Published/Retired 暂存应用规则，并澄清 Primary Model、Relation Path 与可选 Composite Mapping | FROZEN — AMENDMENT |
