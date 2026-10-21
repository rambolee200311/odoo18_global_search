<!-- 使用 Coding/CC 模板；负责人于 2026-10-21 批准冻结并授权实施。 -->

# CC-OFFICE-M1-004 — Odoo 请求模型与 Office 附件封装

## 0. Governance

| 字段 | 值 |
|---|---|
| Coding Contract | `CC-OFFICE-M1-004` |
| 版本 | `v0.3 Frozen` |
| 状态 | **CLOSED BY OWNER — 负责人于 2026-10-21 批准关闭；实现证据含未解决失败项，详见 FR** |
| Intent ID | `OFFICE-ENGINE-M1-ODOO-REQUEST-PERSISTENCE` |
| 模块 | Odoo 18 Office 请求/附件服务封装；Addon 路径 `mymodules/office_engine_odoo/` |
| 工作类型 | 新功能 / Odoo 持久层集成 |
| 上游 SRS | [SRS Office 文档自动化](../../requirement/SRS_office_document_automation.md) `V1.0.0 Frozen` |
| 上游 DDD | N/A；M1 DDD 不适用决定已由负责人确认 |
| 唯一上游 TDD 基线 | [TDD Office Engine M1 V0.4](../../design/TDD_office_engine_m1_v0.4.md) `Frozen`，2026-10-21 批准 |
| 唯一上游 Implementation Plan 基线 | [Implementation Plan Office Engine M1 V0.3](../../implementation/IMPLEMENTATION_PLAN_office_engine_m1_v0.3.md) `Frozen`，2026-10-21 批准；Phase 3 PASS，Phase 4 前置条件已记录 |
| 前置 CC | `CC-OFFICE-M1-001`、`CC-OFFICE-M1-002`、`CC-OFFICE-M1-003` 均已批准关闭并有 SATISFIED FR；CC-003 的 [FR](../../implementation/office-engine-m1/CC-OFFICE-M1-003/FR-OFFICE-ENGINE-M1-ATTACHMENT-SPIKE.md) 记录附件事务 Spike 边界 |
| 目标 | 在不耦合 Office 纯 Python 引擎与聊天/Provider 的前提下，以当前 Odoo 用户权限验证输入附件、调用 `office_core` 并独立调用 `office_verify`，将请求状态和唯一已验证输出附件安全持久化。 |
| 起草依据 | 负责人 2026-10-21 最终修订要求；上游基线仅采用 TDD V0.4 Frozen 与 Implementation Plan V0.3 Frozen。 |

**阶段门禁状态：** 上游唯一计划基线 V0.3 已获批准并冻结，记录 CC-003 FR SATISFIED、Phase 3 PASS 和 Phase 4 前置条件。本 CC 按该基线及 TDD V0.4 编制；不引用 V0.2 计划或 TDD V0.3 作为当前实施依据。

**冻结与授权记录：** 负责人于 2026-10-21 明确批准本 CC 冻结并进入实施。冻结范围、测试契约和 Addon 路径以本版本为准；本批准不代表自动化验证通过、人工验收完成或 CC 已关闭。

**CC-003 清理语义决策：** Spike 实测回滚/ORM unlink 不会同步删除 filestore 文件；Odoo 原生 GC 为延迟路径，本次没有执行全局 GC。业务负责人已于 2026-10-21 确认：失败/回滚时数据库附件记录和下载授权立即失效，物理文件由 Odoo 原生 GC 延迟回收，不承诺即时物理擦除。不得直接删除 filestore 文件或在请求失败路径调用全局 GC。

**UUID 技术基线：** 按 TDD V0.4 §5.1，`request_uuid` 由调用方生成并传入；数据库唯一约束处理并发。重复键时按冻结设计回滚当前事务，并在新事务中以当前用户权限读取既有请求状态。

**Mapping / AC-05 边界：** 负责人已决定 M1 不提供 Mapping 前端，只提供内部同步服务接口，由 Python 测试或内部调用方触发。调用方提供显式、已确认的 Mapping Plan；本 CC 不实现用户确认 UI，不得将内部调用或测试记录宣称为最终用户已确认。冻结计划要求在 M1 关闭前完成 AC-05 追溯备忘录；该备忘录仍是 M1 整体关闭事项。

## 1. 变更概述

**目标：** 按冻结 TDD V0.4 §§5—7 实现最小 Odoo 持久层封装：建立所有者隔离的请求记录和 `request_uuid` 数据库唯一约束；授权读取源附件并形成有界字节快照；在不持有长数据库事务的处理阶段依次调用 `office_core` / `office_verify`；仅在回读成功及交付前重新授权后创建私有输出附件并关联请求；失败时保证无可下载输出记录，并按负责人确认的延迟 GC 语义记录文件清理结果。

**背景：** CC-001 建立了纯 Python 同步候选生成核心，CC-002 建立了独立回读引擎，CC-003 证明 Odoo 附件 ORM/filestore 的有限事务副作用及访问控制。现在需要以当前用户环境组合这些层，并在同一请求中持久化状态和唯一结果。当前不实现聊天拦截；该能力属于后续 Provider 前路由 Spike 和独立 CC。

## 2. 上游基线与追溯

### 2.1 SRS 引用

| SRS ID | 标题 | 与本次 CC 的相关性 |
|---|---|---|
| FR-M1-001 / FR-M1-008 | 接收请求、关联附件与输出交付 | 部分：只覆盖内部 Odoo 服务的请求/附件关系和输出持久化，不含聊天入口 |
| FR-M1-004 / FR-M1-007 | 显式映射和映射数据校验 | 部分：Mapping Plan 由调用方提供；本层拒绝无效输入并调用纯 Python 核心，不推断语义 |
| FR-M1-005 / FR-M1-006 / FR-M1-009 | 公式、文档完整性与输出回读 | 部分：只在 `office_verify` PASS 后允许输出附件创建；受支持格式/结构仍限既有能力白名单 |
| BR-OFFICE-01/02/03/04/06/10/15/16 | 实时授权、文件安全、模板只读、公式与回读、越权隔离、失败处理 | 仅覆盖本次请求封装及附件授权边界；不查询业务模型、不调用 LLM |
| NFR-OFFICE-01/02/03/04/06/08/11 | 权限、文件安全、数据最小化、完整性、错误、资源和事务边界 | 按同步有界处理、当前用户、失败关闭约束裁剪 |
| AC-02/05/06/09/10/17/23/27 | 输入/映射/公式验证、跨用户授权、失败安全及并发变化 | 只覆盖内部 API 和附件持久层适用部分；不宣称完成用户确认 UI、M2 实时业务取数或聊天 E2E |

**SRS 范围限制：** AC-05 描述最终用户确认。内部服务测试仅能验证 Mapping Plan 契约和调用顺序，不得标记 AC-05 用户交互已通过。AC-28 属于 M2，不在本 CC 中实现刷新恢复、异步状态恢复或重复聊天提交恢复。

### 2.2 DDD 引用

N/A。M1 DDD 不适用已由负责人确认；不得在本 CC 新增虚构的领域聚合或领域状态。

### 2.3 TDD 引用

本节仅引用 [TDD V0.4](../../design/TDD_office_engine_m1_v0.4.md) Frozen 与 [Implementation Plan V0.3](../../implementation/IMPLEMENTATION_PLAN_office_engine_m1_v0.3.md) Frozen 当前基线；更早版本仅供历史追溯，不作为本 CC 的实施依据。

| TDD 条款 | 标题 | 本次适用内容 |
|---|---|---|
| TD-001、TD-008、TD-013 | 分层、同步首期、实施顺序 | Odoo 封装置于 `office_core` 与 `office_verify` 之后；无 Queue Job/异步任务；保留服务边界 |
| TDD §3.2—3.4 | 核心 API、Mapping Plan、错误契约 | 只调用冻结公开 API；不修改纯 Python 核心契约 |
| TDD §5.1—5.2 | 最小请求模型与状态映射 | 最小字段集、唯一 `request_uuid`、状态/结果约束；不新增队列字段 |
| TDD §6.1—6.2 | 同步生命周期、事务边界、幂等 | 短事务授权/快照、事务外处理、短事务交付重验、失败路径和唯一结果 |
| TDD §7.1—7.3 | 权限、安全、资源限制和错误 | 当前用户环境、附件归属、资源超限拒绝、稳定脱敏错误、无失败下载 |
| TDD §8 / TEST-OFFICE-001/009/012/013/014 | M1 验收追踪 | 本 CC 负责 Odoo ACL/事务/失败/唯一性适用验证，不覆盖未到阶段的聊天或 M2 行为 |
| Implementation Plan V0.3 Frozen Phase 4 | Odoo 请求模型与附件封装 | 当前阶段基线；Addon 路径为 `mymodules/office_engine_odoo/` |

### 2.4 事件报告

不适用；本 CC 是新增 Odoo 持久层封装。CC-003 Spike 报告是附件事务边界证据，不是新的业务或技术权威。

### 2.5 追溯规则

本 CC 仅授权实现 §3.1 的内部同步 Odoo 服务。不得新增用户界面、聊天消息钩子、Provider 路由、业务模型读取、AI 调用、Skill、异步执行或超出既有格式能力的支持。发现冻结 SRS/TDD 未定义的事务、清理、权限、请求去重或输出可见性语义时，必须停止并升级。

## 3. 范围冻结

### 3.1 在范围内（In Scope）

- 在 `mymodules/office_engine_odoo/` 提供最小 `office.document.request` 持久模型和内部同步服务；此模块只承载 Odoo 模型封装，不实现聊天适配或 Provider 路由。
- 按 TDD V0.4，`request_uuid` 由可信调用方/上层 API 在首次请求前生成并传入，重试必须复用同一个 UUID；Odoo 服务校验格式/长度并持久化，不将其视作授权凭证。数据库唯一约束兜底；创建遇到唯一键 `IntegrityError` 时，回滚当前事务/游标，再以当前用户权限在新游标中读取同一 UUID 的既有请求并返回其现有状态，不重新渲染。
- 最小持久字段限于 TDD §5.1：`request_uuid`、`owner_id`、可选 `thread_id` / `input_message_id`、`source_attachment_id`、`output_attachment_id`、`state`、`error_code`、`failed_stage`、`input_sha256`、`output_sha256`、`started_at`、`finished_at`。只有实施证明 TDD 已批准字段不足时才可停止并升级；不得顺手增加字段或索引。
- 只保存 TDD §5.2 定义的技术状态：`accepted`、`validating`、`processing`、`generated`、`failed`，不增加重试/取消/排队/进度等产品状态。
- 使用当前调用用户的 Odoo `env` 校验请求模型访问权、源附件读取权和必要的 owner/message/thread 关联。不得调用 `sudo()`、`with_user(SUPERUSER_ID)` 或以 public attachment token 暴露结果。
- 受限获取输入附件字节和指纹；确认文件访问权、扩展名/能力策略及资源预算后，将显式 Mapping Plan 和有界字节交给 `office_core`；候选仅交给独立 `office_verify`。核心与回读服务均不得获得 Odoo `env`、记录 ID、服务端路径或业务数据访问能力。
- `office_verify` 未完整 PASS、格式/结构未启用、输入身份/权限重验失败、资源预算超限或附件持久化失败时，不创建/关联可下载成功输出；请求以稳定失败状态结束，普通用户错误脱敏。
- 仅当候选完整通过回读、短事务 B 交付前重验通过后创建结果附件；在同一个数据库事务中关联输出、设置 `generated` 及摘要字段。输出保持与源格式相同；本 CC 不启用 `.xls/.doc` 或其他未验证能力。
- 输出附件必须与本次请求所有者及请求记录绑定，默认非公开；以用户 A/B 的实际 ORM / 附件访问路径验证 A 有权读取、无关用户 B 不可读取。附件 ID/URL 不构成授权。
- 文件渲染阶段不持有 Odoo 请求/记录数据库锁。根据 CC-003 证据，附件创建本身会同步进行 filestore I/O；请求/附件记录回滚不能同步撤销磁盘文件。按本 CC 冻结前批准的策略使用 Odoo 原生延迟 GC；失败输出必须无数据库附件记录/可下载权限，并将 GC 延迟语义如实记录。
- 保持纯 Python 服务与 ORM 协调层独立；Odoo 包装仅负责认证后的附件快照、Mapping Plan 传入、核心调用、结果复核、状态与附件关联。
- 为新模型、字段权限/记录规则、SQL 唯一约束、状态迁移、成功/失败事务、并发 UUID 冲突、附件访问、重复请求和数据库升级提供 Odoo 集成验证；只使用获准开发环境 `odoo18ce`、项目 `venv` 和 `odoo.conf`，不得创建隔离数据库。

### 3.2 超出范围（Out of Scope）

- 聊天窗口上传/消息拦截、`llm_thread` 扩展、Provider 调用前路由、Provider payload 过滤、LLM Mapping Plan 生成；须先完成 Phase 5 Provider 路由 Spike 并另立 CC。
- Mapping 编辑器、用户确认 UI、预览 UI、技能管理和业务用户交互；内部测试不替代这些需求。
- Odoo 业务模型或记录查询、业务字段值读取、`odoo_record_retriever`、权限网关以外的数据访问、Office 内容外发给 LLM。
- Queue Job、异步任务、轮询/WebSocket、自动重试、恢复、取消、排队/并发调度；AC-28 归 M2。
- 修改 `office_core`、`office_verify` 的纯 Python 契约或支持能力；安装/升级依赖；使用 LibreOffice 或开放未验证格式/结构。
- 同步擦除 filestore 对象、手工删除存储文件、在请求失败路径调用全局 Odoo GC、实现新的孤儿回收任务。
- 修改 Odoo 官方源码/Addon、冻结 SRS/TDD、TV 原始报告/证据或其他既有 CC/FR。
- 生产容量承诺、长任务吞吐或任何 UI / 浏览器 E2E。

### 3.3 非目标（Non-Goals）

- 本 CC 不完成 M1 全部需求、聊天工作流或最终用户确认；不因状态为 `generated` 就自动宣称满足所有 SRS 验收。
- 本 CC 不保证任意 `.xlsx/.docx` 模板无损；仅开放 `office_core` 和 `office_verify` 当前已准入的能力。
- 回读 PASS 不替代 Odoo 权限、交付前重验和附件记录事务；请求数据库记录不存在不等于 filestore 物理擦除完成。
- `request_uuid` 唯一约束不单独保证端到端重试幂等；必须通过明确的 UUID 重用路径和竞争测试证明。

### 3.4 仅限范围追溯

本 CC 纳入的每个 SRS/TDD/Plan ID 必须至少对应一个 CC-CHANGE。未列入范围的业务需求、M2 AC 或聊天能力不得因本 CC 自动获得授权。

## 4. 变更边界

### 4.1 允许

| 类型 | 详情 |
|---|---|
| Odoo Addon 边界 | 新增/修改仅限 `mymodules/office_engine_odoo/` 下实现 Phase 4 模型封装所需的最小自有 Addon 文件；不得修改现有官方 Addon |
| Odoo 模型 | `office.document.request`；字段严格限 TDD V0.4 §5.1；模型定义位于上述自有 Addon |
| Odoo 服务 | 内部同步服务入口；负责当前用户授权、附件快照、`office_core`/`office_verify` 调用及最终附件关联 |
| 权限文件 | 仅请求模型最小 ACL、owner Record Rule 和必要的菜单/视图禁用配置；不创建面向用户的菜单或 UI |
| 自动化测试 | 自有 Addon 的模型、ORM、ACL、事务、唯一约束、幂等和附件访问测试 |
| 实施证据 | `docs/implementation/office-engine-m1/CC-OFFICE-M1-004/**` |
| 本 CC | `docs/context/intent/CC-OFFICE-M1-004.md`；按正式修订流程更新 |

### 4.2 禁止

| 类型 | 详情 |
|---|---|
| 上游文档 | 禁止未经正式变更流程修改 Frozen SRS、TDD、TV Plan/报告；Implementation Plan 必须独立维护和重新批准，不在本 CC 实施中静默改写 |
| 官方源码 | 禁止修改 Odoo 核心或官方 Addon |
| Office 核心 | 禁止更改 `office_core`、`office_verify` 和格式 capability 白名单 |
| 聊天与 AI | 禁止改 `llm_*`、Provider、聊天 JS/XML、工具配置或增加 LLM 调用 |
| 额外数据模型 | 禁止 Mapping Plan 持久化模型、任务/队列模型、附件清理任务或无 TDD 依据的核心模型 |
| 额外字段/索引 | 除 TDD §5.1 字段及 `request_uuid` 唯一约束外，禁止增加无依据字段、存储业务内容或添加索引 |
| 外部能力 | 禁止网络请求、服务器任意路径、宏/脚本执行、公开 token 链接、无界同步处理和全局 GC |
| 环境 | 不创建隔离数据库；不得安装/升级依赖；模块安装/升级仅在冻结 CC 明确授权后按 `odoo.conf` / `odoo18ce` 运行 |

## 5. 必需的行为变更

| ID | 当前行为 | 期望行为 | CC-CHANGE ID |
|---|---|---|---|
| 1 | Odoo 尚无受所有者权限保护的 Office 请求记录 | 建立 TDD §5.1 的最小请求模型、唯一 `request_uuid` 约束与限定状态；拒绝未授权读取/修改他人请求 | CC-CHANGE-001 |
| 2 | Office 纯 Python 核心尚未由 Odoo 当前用户附件输入调用 | 内部服务按当前 `env` 校验附件权限/关系，获取受限 bytes 与摘要后调用既有核心，不把 ORM/路径带入核心 | CC-CHANGE-002 |
| 3 | Mapping Plan 没有通过 Odoo 包装层进行结构验证和安全协调 | 只接受内部调用方提供的显式 Mapping Plan；缺失、未知、非法或类型不符按核心契约拒绝，不做语义推断/AI 调用 | CC-CHANGE-003 |
| 4 | 候选文件尚无 Odoo 服务层的独立最终回读和结果准入 | 仅在 `office_verify` 完整 PASS 且交付前重验成功后创建输出附件；任何失败均不关联可下载输出 | CC-CHANGE-004 |
| 5 | 请求状态和处理步骤缺少短事务/事务外处理协调 | 按 TDD 生命周期执行短事务授权和请求创建、事务外有界处理、短事务重验和附件关联；失败通过独立短事务落 `failed` | CC-CHANGE-005 |
| 6 | 同一请求标识的并发唯一性和结果唯一性未经 Odoo 持久层验证 | 数据库唯一约束兜底；重复同一 UUID 读取既有状态或受控冲突，不产生多个有效结果；明确并验证 UUID 重用方 | CC-CHANGE-006 |
| 7 | filestore 回滚残留与失败清理之间的物理回收时效 | 负责人已确认延迟 GC 语义；失败输出不可访问，保留 GC marker 事实且不调用全局 GC；实现仍须通过产品失败路径测试 | CC-CHANGE-007 |
| 8 | 错误/资源超限可能被错误表示为成功或泄露内部细节 | 错误阶段和稳定码可审计；用户消息脱敏；资源超预算、核心/回读失败、权限变化和存储失败均无 `generated` 状态/输出附件 | CC-CHANGE-008 |

## 6. 既有行为保留（回归边界）

| ID | 行为 / 契约 | 为什么不得改变 | CC-PRESERVE ID |
|---|---|---|---|
| 1 | `office_core`、`office_verify` 继续为独立纯 Python 层，不导入 Odoo/Provider/HTTP/Queue | 冻结 TDD 分层 | CC-PRESERVE-001 |
| 2 | 当前格式与结构能力白名单保持不变，未验证能力 fail closed | TV 为 Partial，CC-001/002 未开放的结构不可扩张 | CC-PRESERVE-002 |
| 3 | 用户附件读取和结果访问始终使用当前 Odoo ACL/Record Rules，不用 sudo 扩权 | NFR-OFFICE-01；跨用户数据隔离 | CC-PRESERVE-003 |
| 4 | 输出候选只有回读 PASS 后才可能持久化；失败状态没有可访问的输出附件 | FR-M1-009、BR-OFFICE-15、AC-17/23 | CC-PRESERVE-004 |
| 5 | 不改变源附件；文件处理不持有业务记录长事务/锁 | BR-OFFICE-03、NFR-OFFICE-11、T-TRX-002 | CC-PRESERVE-005 |
| 6 | 同步首期，不引入 Queue Job、重试、取消或异步恢复 | TDD TD-008、SRS AC-28 属 M2 | CC-PRESERVE-006 |
| 7 | 错误对普通用户不泄露路径、模板原文、业务内容、traceback 或他人附件信息 | NFR-OFFICE-06 | CC-PRESERVE-007 |

## 7. 适用的 TDD 防护栏（裁剪，不复制）

| TDD 防护栏 | 适用性 | 本次落实位置 | 验证方式 |
|---|---|---|---|
| TDD §§5.1—5.2 最小请求模型/状态 | 适用 | ORM 模型字段/状态约束 | CC-TEST-001—003 |
| TDD §6.1 短事务 A/B、事务外处理 | 适用 | 请求服务生命周期 | CC-TEST-006/007/011 |
| TDD §6.2 UUID 唯一与输出唯一 | 适用 | SQL 唯一约束、幂等处理 | CC-TEST-004/005 |
| TDD §7.1 当前用户与附件安全 | 适用 | ACL、Record Rule、源/输出 attachment 关系 | CC-TEST-008/009 |
| TDD §7.2 有界同步资源策略 | 适用 | 调核心前策略校验、超限失败 | CC-TEST-010 |
| TDD §7.3 稳定错误与失败清理 | 适用 | 错误状态、输出隔离、GC 延迟记录 | CC-TEST-011/012 |
| TDD §3.2—3.4 Office API/Mapping/Error 契约 | 适用 | 只组合冻结公开接口，不变更契约 | CC-TEST-006/007/010 |
| TDD §2.3 Addon 聊天边界 | 部分适用 | 核心 Odoo 封装位于 `mymodules/office_engine_odoo/`；不实现聊天；后续聊天适配仍须先通过 Provider 前路由 Spike | CC-TEST-013 |
| `office_core` / `office_verify` 纯 Python 隔离 | 强制适用 | 在关闭前自动扫描两个目录中全部 Python 文件，禁止 Odoo/ORM import | CC-TEST-016；ATR 必须保存命令和退出状态 |

**强制静态隔离检查：** 关闭前必须运行以下命令，并将命令、扫描目录、运行日期和退出状态记录到 ATR。命令返回 `0` 表示发现禁止导入、测试失败；返回 `1` 表示无匹配、此项通过；其他退出码表示检查未完成，记为 `NOT RUN`，不得关闭 CC。

```sh
rg -n --glob '*.py' '^[[:space:]]*(from[[:space:]]+odoo([.]|[[:space:]]|$)|import[[:space:]]+odoo([.]|,|[[:space:]]|$))' mymodules/office_core mymodules/office_verify
```

## 8. 数据 / 迁移影响

| 字段 | 值 |
|---|---|
| 需要迁移 | 是；新增请求表与最小必要字段，不改现有业务表 |
| 迁移脚本 | Odoo 模块标准 schema 初始化/升级；位于 `mymodules/office_engine_odoo/` |
| 数据源 | 当前用户已授权的 `ir.attachment`；显式 Mapping Plan；不读取任何业务模型记录 |
| 目标 | `office.document.request` 状态和授权附件关联；不存 Office 原始 bytes 或 Mapping Plan 正文 |
| 唯一约束 | `request_uuid` 数据库唯一；不得只依赖 Python 前置查询 |
| 恢复 / 回滚策略 | 按 Odoo 模块升级/卸载规则处理；不删除既有用户附件。迁移失败时停止并保留数据库状态，依 Odoo 标准恢复流程处置；具体升级/回滚步骤在冻结 CC 前补齐 |
| 验证 | 在获准 `odoo18ce` 上验证字段/约束存在、重复键拒绝、ACL、ORM/附件事务和失败回滚；不建隔离 DB |

## 9. API / 集成影响

| 字段 | 值 |
|---|---|
| 新接口 | 仅内部同步 Odoo Python 服务；公开 HTTP/JSON-RPC 无 |
| 输入 | 当前调用环境、调用方生成并传入的 `request_uuid`、已授权源附件引用、显式 Mapping Plan、受限服务端资源策略 |
| 输出 | 请求状态和通过独立回读后的私有 `ir.attachment`；失败只返回稳定脱敏错误 |
| Provider/LLM | 无调用；不向模型传 Office bytes 或附件路径 |
| 聊天适配 | 无；先完成 Phase 5 Provider 前路由 Spike 后另立 CC |
| 幂等契约 | 调用方重试时复用同一个 UUID；唯一键冲突后回滚并用新游标按当前用户权限读取既有请求；不得重跑核心渲染 |

## 10. 安全 / 权限影响

| 字段 | 值 |
|---|---|
| 新权限 | 仅请求记录所有者访问其请求和结果；管理角色额外访问规则须有 SRS/TDD 依据，否则不增加 |
| 变更 ACL | 新模型最小 ACL 与 owner Record Rule；附件仍按标准当前用户授权检查 |
| 输入附件 | 必须由当前用户读取；校验 message/thread/owner 关联（若上游确实提供上下文）；不能仅因知道 ID 即访问 |
| 输出附件 | 非公开、绑定 request/owner；A/B 用户切换实测访问权，禁止使用公开 URL/token 作为绕过 |
| 业务数据 | 不访问 Odoo 业务模型；业务数据/记录选择属于后续 M2，经 Odoo 权限网关处理 |
| 文档与日志 | 不记录文件 bytes、业务内容、映射值、绝对路径或完整 traceback；保留必要 request UUID、阶段、稳定错误码和摘要哈希 |
| 清理 | 数据库/附件记录失败时使用 ORM 事务和 Odoo 原生 GC 标记语义；本 CC 不直接删除 filestore、不手工运行全局 GC |

## 11. 测试契约

所有测试起始为 `NOT RUN`；实际状态仅由 ATR/IHR/HVR 记录。本 CC Draft 不预填通过。所有 ORM/附件验证使用现有 `odoo18ce`、项目 `venv`、`odoo.conf` 和合成数据。

| 测试 ID | 对应变更 | 上游来源 | 测试类型 | 预期结果 | 人工验证 | 原因 |
|---|---|---|---|---|---|---|
| CC-TEST-001 | CC-CHANGE-001 | TDD §5.1；Plan Phase 4 | ORM/model | 模型字段仅含冻结最小清单；owner/request 状态字段合法；无额外业务数据字段或 queue 字段 | 否 | 验证最小持久请求形状 |
| CC-TEST-002 | CC-CHANGE-001 | TDD §5.2 | 状态机 | accepted→validating→processing→generated/failed 的合法路径可写；非法状态跳转拒绝；失败请求无 output_attachment_id | 否 | 防止状态伪成功 |
| CC-TEST-003 | CC-CHANGE-001/008 | NFR-OFFICE-01；AC-10/17 | ACL/Record Rule | 用户 A 可读取自己的请求；用户 B 无法搜索、读取、修改 A 的请求及字段；不以 sudo 测试替代 | 否 | 验证请求记录所有者隔离 |
| CC-TEST-004 | CC-CHANGE-006 | TDD §6.2；Plan Phase 4 | DB constraint | 数据库 schema 中实际存在 `request_uuid` UNIQUE；重复键在 ORM 并发/重复创建场景不产生两条请求 | 否 | Python 前置查重不能防并发 |
| CC-TEST-005 | CC-CHANGE-006 | TDD §6.2；AC-28（仅同 UUID 防重边界） | 并发/幂等 | 用 Python `threading` 或等效真实并发方式，在两个独立 cursor/env 中同时提交完全相同的调用方 `request_uuid`；断言仅一条请求记录插入成功，另一方捕获唯一键 `IntegrityError`、回滚旧事务并以新 cursor 按当前用户权限读回同一请求。待胜出请求完成后，两路调用均重新读取该唯一请求，断言最终获得相同 `output_attachment_id` 且只渲染一次；处理中重放不得提前报告成功或暴露尚未生成的附件。测试等待必须有界且不得持有数据库锁。此测试不替代 AC-28 全连接恢复 | 否 | 覆盖唯一键竞态及最终同一附件；不将未完成状态当作成功 |
| CC-TEST-006 | CC-CHANGE-002/003 | FR-M1-004/007；TDD §§3、6 | 服务/输入校验 | 服务只接收显式合法 Mapping Plan；空/未知/类型错误/公式目标遵循核心稳定错误；无 LLM/业务模型查询；源模板哈希不变 | 否 | 保持内部映射服务边界 |
| CC-TEST-007 | CC-CHANGE-003/004 | FR-M1-005/006/009；AC-23 | 组合/回读 | 通过冻结公开 API 调 `office_core` 后必须调 `office_verify`；mock 或真实合成失败均不能创建输出附件；PASS 后才进入交付事务 | 否 | 证明回读是输出准入条件 |
| CC-TEST-008 | CC-CHANGE-002/004 | FR-M1-001/008；NFR-OFFICE-01 | 附件 ACL | 输入附件未授权、已删除、归属变化时拒绝；成功输出为非公开并绑定请求，当前 owner 可读，其他用户读失败 | 否 | 防止 ID/URL 替代授权 |
| CC-TEST-009 | CC-CHANGE-004/005 | AC-10/17/23 | 附件交付/失败注入 | `office_verify` FAIL、交付重验失败、输出 attachment 创建/提交失败、回滚时均无 `generated` 状态或可下载 output attachment；新 cursor/新 shell 查询确认记录关系不可见 | 否 | 验证数据库授权失效与失败安全 |
| CC-TEST-010 | CC-CHANGE-002/008 | NFR-OFFICE-02/08；TDD §7.2 | 资源/拒绝 | 输入文件大小或展开预算超限时在受控边界拒绝；不无限占用 Odoo worker，不转 Queue Job，不留下候选/附件结果 | 否 | 确保同步有界处理 |
| CC-TEST-011 | CC-CHANGE-005/008 | NFR-OFFICE-11；TDD §6.1 | 事务/锁/耗时 | 验证核心解析/渲染/回读不持有 DB 游标/业务行锁；分开记录附件快照与结果附件 I/O 的事务位置。对结果附件，在同一受控 Odoo cursor/事务中，于调用 `ir.attachment.create()` 前记录 `create_started_at` 并启动单调时钟；`create()` 返回后继续计时，直至同一事务的 `commit()` 成功返回，记录 `commit_completed_at`、`elapsed_ms`、数据库/运行时标识。该值定义为 create-to-commit 实际耗时，ATR 必须如实记录。超过 1000 ms 仅记录 `Warning — TDD §6.1 长事务风险` 及风险审计，不使本测试失败；功能和事务断言仍独立判定。不得手工 commit 后复用旧 env/recordset | 否 | 1 秒是风险审计提示，不是测试失败阈值或 SRS 性能承诺 |
| CC-TEST-012 | CC-CHANGE-007 | CC-003 FR；TDD §6.1/§7.3 | 回滚/GC/清理 | 回滚/失败输出无 DB attachment 行、无 request 输出关联、用户不能下载；精确记录 Odoo GC marker/延迟 GC，不运行全局 GC、不直接删除磁盘文件 | 否 | 验证负责人确认的延迟 GC 语义在产品失败路径成立 |
| CC-TEST-013 | CC-CHANGE-001/002/005 | TDD §2.3、§5.1 | 安装/升级/隔离 | 自有 Odoo 模型集成不修改官方源码；不包含聊天拦截/Provider/LLM；按计划确定的 Addon 安装/升级流程在获准开发库验证 | 否 | 验证 Odoo 包装边界，不验证聊天 |
| CC-TEST-014 | CC-PRESERVE-001/002/006 | TD-001/008/013 | 回归/依赖 | 核对纯 Python 两个包未增加 ORM/Provider/Queue 导入和代码变更；没有 Queue Job 字段、依赖或后台执行 | 否 | 保持已交付底座边界 |
| CC-TEST-015 | CC-PRESERVE-003/004/005/007 | NFR-OFFICE-01/06/11；AC-10/17/23/27 | 权限/故障回归 | 当前用户权限、回读后交付、无长业务锁、错误脱敏和输入只读均有当前基线证据 | 否 | 验证保留的关键安全行为 |
| CC-TEST-016 | CC-PRESERVE-001 | TDD TD-001/013；§2.4；Plan Phase 4 | 静态隔离检查 | 自动扫描 `mymodules/office_core` 与 `mymodules/office_verify` 下全部 `*.py`；上述 §7 命令不得发现 `import odoo` / `from odoo...` 语句。ATR 保存精确命令、运行日期、扫描目录与退出码；命令退出码 0 为 FAIL、1 且零匹配为 PASS、其他退出码为 NOT RUN | 否 | 强制可重复门禁，口头声明不构成证据 |

## 12. 停止条件 / 升级闸门

| 触发条件 | 处置 |
|---|---|
| 实际发现 TDD V0.4 / Implementation Plan V0.3 基线失效或被后续批准版本取代 | 暂停受影响 CC；先按工作流更新并批准计划基线和追溯，再继续 |
| Odoo 延迟 GC 语义未落实，或失败输出仍可访问 | 停止受影响实现；按已确认策略修复 DB 记录/下载授权失效，不直接删除物理文件；如需求改为即时擦除，先变更 SRS/TDD 并另行验证 |
| `mymodules/office_engine_odoo/` 与运行时 addons 路径或已批准 TDD 约束不兼容 | 暂停受影响实施，提交基线变更评审；不得静默迁移到其他 Addon 路径 |
| 需要读取业务模型/调用 LLM/聊天 Provider/增加 UI | 超出范围；交由 M2/Phase5 或独立 CC |
| 需要 sudo、公共附件 token、跨公司或跨用户授权扩展 | 立即停止，退回 SRS/TDD 权限设计；不绕过 ACL |
| 请求模型字段、状态、Mapping 持久化或索引超出 TDD §5 | 停止并修订 TDD；不能在实现时顺手扩展 |
| 附件 I/O / 事务行为与 CC-003/TDD 不一致，或失败文件仍可下载 | 停止受影响实现，保持现场；更新 TDD/计划并重新授权验证 |
| 资源限额未获得服务端批准、超预算路径无界或需要异步处理 | 按稳定错误拒绝；异步属于 M2，不在本 CC 擅自实现 |
| 需要创建隔离数据库、安装/升级依赖或修改 Odoo 官方代码 | 停止；需单独授权及相应计划/CC变更 |

## 13. 完成定义 / 关闭标准

不得在起草阶段填写执行结果。只有 CC 冻结和授权后才执行；FR 按 IHR/ATR/HVR 证据逐项关闭。

1. 上游 TDD V0.4 与 Implementation Plan V0.3 均为有效 Frozen 基线；计划记录 CC-003 完成及 Phase 4 前置条件；Addon 路径严格为 `mymodules/office_engine_odoo/`，安装/升级路径与资源策略按 CC 得到验证。
2. 延迟 GC 产品语义已由负责人确认；产品失败路径验证数据库记录/下载授权立即失效，GC 延迟状态准确记录；不承诺物理文件即时擦除。
3. `request_uuid` 唯一约束真实存在，重复/并发请求结果唯一，UUID 的重用方和授权语义已明确定义。
4. 当前用户 ACL / Record Rule、源附件关系、输出附件私有性和跨用户拒绝有 Odoo Runtime 证据；未使用 sudo 或公共链接绕过。
5. 核心处理在事务外有界执行；附件读取/创建 I/O 的事务事实已在目标运行时确认；不持有长业务锁。
6. 只有 `office_verify` 完整 PASS 且交付前重验通过才创建/关联输出；所有失败场景均无可访问结果附件或伪 `generated` 状态。
7. 资源超限、失败阶段、脱敏错误和 ORM/filestore GC 副作用均有当前基线证据；失败清理不直接删文件、不调用全局 GC。
8. CC-PRESERVE-001—007 与 CC-TEST-001—016 均有显式结果；CC-TEST-016 的自动静态扫描必须零匹配且 PASS，并在 ATR 留存命令和退出状态；所有 SRS AC 仅按本 CC 覆盖范围报告，AC-05 最终用户确认和 AC-28 恢复不得误标通过。
9. IHR、ATR、HVR（预计 UI HVR 为 N/A）、FR 完整；FR Closure SATISFIED；没有未批准偏离或缺失的强制证据。
10. `office_core` 和 `office_verify` 目录下所有 Python 文件均完成自动静态隔离扫描，未发现 Odoo/ORM import；无该自动化证据不得关闭 CC。

## 14. 追溯矩阵

### 14.1 正向：上游 → CC

| 上游 | CC 项 | 备注 |
|---|---|---|
| Implementation Plan V0.3 Frozen Phase 4 | CC-CHANGE-001—008；CC-TEST-001—016 | 请求模型与附件同步封装；Addon 固定为 `mymodules/office_engine_odoo/` |
| SRS FR-M1-001/004/007/008/009；AC-02/05/06/09/10/17/23 | CC-CHANGE-001—006 | 仅内部 API、请求/附件和回读交付适用部分；不含用户 UI |
| SRS BR-OFFICE-01/02/03/04/06/10/15；NFR-OFFICE-01/02/03/04/06/08/11 | CC-CHANGE-002—008；CC-PRESERVE-001—007 | 当前用户权限、只读核心、资源限制、错误和事务安全 |
| TDD V0.4 TD-001/008/013/015、§§5—7 | CC-CHANGE-001—008；CC-TEST-001—016 | 请求字段/状态、事务、调用方 UUID 幂等、权限、同步、失败和隔离边界 |
| CC-003 FR / Spike 报告 | CC-CHANGE-007；CC-TEST-009/012 | filestore rollback/unlink 延迟 GC 的实测证据，不改变其状态 |

### 14.2 反向：CC → 上游

| CC 项 | 上游 | 类型 |
|---|---|---|
| CC-CHANGE-001/006 | TDD §5、§6.2；Plan Phase 4 | 请求模型、数据库唯一性及结果幂等 |
| CC-CHANGE-002/003 | SRS FR-M1-004/007；TDD §§3、6 | 授权附件快照和显式 Mapping Plan 服务调用 |
| CC-CHANGE-004/005 | SRS FR-M1-008/009、AC-17/23；TDD §6 | 回读 PASS 后附件交付、事务/状态生命周期 |
| CC-CHANGE-007/008 | SRS BR-OFFICE-10、NFR-OFFICE-06/08；TDD §7；CC-003 FR | 延迟 GC 处置、资源和错误安全 |
| CC-PRESERVE-001—007 | TDD TD-001/008/013、§§4/6/7 | 底座隔离、权限、格式、事务和失败语义 |

## 15. 附录 A — 本次局部决策记录

| CC-DEC ID | 决策提案 | 替代方案 | 理由 / 状态 |
|---|---|---|---|
| CC-DEC-001 | 内部同步服务由当前用户 env 驱动，不接受客户端 uid/domain/path | 用 sudo 服务账号或任意路径 | 符合 TDD 权限网关；本 CC 契约 |
| CC-DEC-002 | 只保存 TDD §5.1 的最小字段 | 保存文件内容、Mapping Plan、队列字段 | 数据最小化；本 CC 契约 |
| CC-DEC-003 | 只调用 `office_core` / `office_verify` 的公开 API | 在 ORM 层复制解析或回读逻辑 | 保持分层和独立验证；本 CC 契约 |
| CC-DEC-004 | 输出数据库记录在校验和交付重验后才持久化 | 先公开生成临时附件再检查 | 失败无下载结果；须以 ORM/filestore 测试验证 |
| CC-DEC-005 | **业务负责人已确认：失败/回滚场景下，数据库记录立即失效（不可下载），物理文件由 Odoo 原生 GC 延迟回收，不承诺即时物理擦除。** | 请求失败时同步擦除磁盘，或调用全局 GC | 业务负责人 2026-10-21 决策；符合 CC-003 实测。只允许 ORM/原生延迟 GC，不直接删文件、不在请求内运行全局 GC |
| CC-DEC-006 | 本 CC Odoo 模型封装 Addon 路径固定为 `mymodules/office_engine_odoo/`；聊天适配路径由独立 Provider 前 Spike 后决定 | 在本 CC 中同时确定聊天适配物理布局 | 与 Plan V0.3 Phase 4 一致；不预决后续聊天 Addon 拆分 |
| CC-DEC-007 | 调用方生成并传入 `request_uuid`；唯一键冲突后回滚并以新游标读取现有请求 | 每次服务端调用生成新的随机 UUID | TDD V0.4 TD-015 Frozen，唯一当前技术基线 |

## 16. 版本历史

| 版本 | 日期 | 变更说明 | 状态 |
|---|---|---|---|
| v0.1 | 2026-10-21 | 根据冻结 TDD V0.3、Implementation Plan V0.2 Phase 4 和 CC-003 运行证据起草；明确 Draft 门禁、GC 决策、计划维护和 UUID 重用问题。 | Draft |
| v0.2 | 2026-10-21 | 按评审修订：调用方 UUID、IntegrityError 后新游标读取、并发与完成后重放测试、输出附件事务耗时风险记录；记录负责人接受原生延迟 GC。 | Draft |
| v0.3 | 2026-10-21 | 按最终评审意见闭环上游冻结基线、固定 Odoo Addon 路径、增加纯 Python 目录自动隔离静态检查，并明确 create-to-commit 的计时及 Warning-only 语义；负责人批准冻结并授权实施。 | Frozen |
| v0.4 | 2026-10-21 | 按负责人明确批准关闭本 CC；保留 `CC-TEST-007` 原生 FAIL、其他未运行/受阻项及其功能影响，不据此宣称 Phase 4 或 Office 成功生成能力已验收。 | Closed by owner with unresolved evidence gaps |

## 17. 负责人关闭处置（不改写测试结果）

负责人于 2026-10-21 明确批准关闭 `CC-OFFICE-M1-004`。该治理决定仅关闭本轮 Coding Contract，不改变 ATR 中 `CC-TEST-007 = FAIL`、`CC-TEST-005/010/012 = NOT RUN`、`CC-TEST-006/011 = BLOCKED` 等原生结果，也不将 FR 判为 SATISFIED。

已知功能缺口：Odoo `multiprocessing` spawn 子进程无法导入动态注册的 `odoo.addons.office_core`，成功的 Office 文件生成与输出附件交付未得到验证。此关闭不代表 Phase 4 阶段验收通过、不代表 M1 完成或可向用户开放文件生成；后续实现须先通过新的批准基线解决该缺口并补充证据。冻结的 Implementation Plan V0.3 未被本次关闭静默修改，仍保留其原始阶段/CC 映射。
