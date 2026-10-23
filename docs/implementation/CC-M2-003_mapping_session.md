<!-- Skill bundle metadata
Source template: docs/skill/odoo-project-workflow/references/templates/Coding/Coding_Contract模板.md
Source version/status: v1.0.0; Frozen
Template synchronization check: PASS, 2026-10-23
-->

# CC-M2-003：Odoo 编排层基础与 Mapping Session

## 0. 文档治理

### 0.1 执行元数据

| 字段 | 值 |
|---|---|
| Intent ID | `OFFICE-ENGINE-M2-003` |
| Coding Contract | `CC-M2-003` |
| 模块 | `office_engine_m2` |
| 工作类型 | 新功能 / Odoo ORM 与权限隔离 |
| 变更类型 | 在现有 Addon 中增加 Mapping Session 模型、内部服务及访问规则 |
| 版本 | V1.0.0 |
| 状态 | **CLOSED — 负责人批准关闭；冻结契约版本仍为 V1.0.0** |
| 目标 | 建立绑定当前用户、公司、聊天线程、源附件、目标模型/记录的最小映射会话，并提供权限受控的创建、读取和状态迁移服务。 |
| 背景 | M2 后续 AI 映射卡片和 M1 渲染需要一个由服务端管理、按用户和公司隔离、可用 revision 做并发控制的 Odoo 会话上下文。 |
| SRS 基线 | `SRS_office_engine_m2_ai_mapping.md` V1.0.0 Frozen |
| TDD 基线 | `TDD_office_engine_m2.md` V1.0.0 Frozen |
| Implementation Plan 基线 | `IMPLEMENTATION_PLAN_office_engine_m2.md` V1.0.0 Frozen，阶段 3 / 拟议 CC-M2-003 |
| DDD | N/A；依据见 M2 TDD V1.0.0 |
| 起草日期 | 2026-10-23 |
| 批准记录 | 负责人于 2026-10-23 裁定采用冻结 TDD V1.0.0 §8.2 的 8 个状态，批准冻结、实施及关闭。 |

### 0.2 上游基线门禁

- 本 CC 仅扩展已存在的 `mymodules/office_engine_m2/` Addon，不新建平行 Addon；不得改变 CC-M2-002 已交付的 Usage Provider 路径、数据模型、权限或行为。
- 本 CC 只覆盖 Implementation Plan 阶段 3 的编排基础与 Mapping Session，不实现 AI 请求、Retriever 数据读取、映射卡片 UI、RPC 卡片交互、M1 文件渲染或 Skill。
- 会话必须从当前请求用户的 Odoo `env` 创建和读取。会话服务、线程/消息、附件和目标业务记录访问均不得使用 `sudo()` 或 `env(su=True)`。
- ACL 与 Record Rule 必须同时生效。普通用户仅能访问本人且处于当前允许公司范围内的会话；管理员身份不自动穿透他人会话或业务记录权限。
- 仅持久化会话关系、受控状态、revision 和必要的稳定错误类别。不得持久化模板完整文本、Prompt、LLM 原始输出、业务字段样例明文、附件 bytes 或其他业务数据快照。
- 本 CC 已按负责人裁定采用冻结 TDD V1.0.0 §8.2 的 8 个技术状态；不采用原任务中提出的 6 个值，也不增加别名。

### 0.3 状态机裁定（已解决）

负责人已裁定：本 CC 严格采用冻结 TDD V1.0.0 §8.2 的以下 8 个技术状态，并与冻结 SRS §7.1 的业务状态映射保持一致：

| 技术状态 | SRS 业务状态 | 本 CC 允许的后继状态 |
|---|---|---|
| `collecting` | 信息收集中 | `needs_clarification`、`awaiting_confirmation`、`failed`、`cancelled` |
| `needs_clarification` | 待澄清 | `collecting`、`editing`、`failed`、`cancelled` |
| `awaiting_confirmation` | 待确认 | `editing`、`rendering`、`failed`、`cancelled` |
| `editing` | 待确认（技术子态） | `awaiting_confirmation`、`needs_clarification`、`failed`、`cancelled` |
| `rendering` | 处理中 | `completed`、`failed` |
| `completed` | 已完成 | 终态 |
| `failed` | 失败 | 终态；重新发起使用新的 Session |
| `cancelled` | 已取消 | 终态 |

负责人裁定记录：采用以上 TDD 8 状态；原任务中的 `draft`、`processing`、`waiting_confirm` 不作为 ORM 值，分别不另设状态别名；TDD/SRS 上游文件不作修改。本 CC 实施必须遵守上述允许转换，任何未列出的转换均拒绝。

## 1. 变更概述

### 1.1 目标

在 `office_engine_m2` 中建立最小、可授权、可隔离的 `office.mapping.session`，并通过 `office_engine_m2/services/mapping_service.py` 提供 `create_session(...)`、`get_session_context(...)` 及受控状态迁移入口。用户和公司身份由当前服务端 `env` 决定；任何客户端身份声明都不可信。

### 1.2 实施理由

阶段 4 的映射卡片需要持久化会话身份及 revision，并在每次读取或后续操作时重新校验用户、公司、线程、附件与目标记录关系。该 CC 先提供阶段 3 的服务端持久化与安全边界，不预先开发用户界面。

## 2. 上游基线与追溯

### 2.1 SRS 引用

| SRS ID | 标题 | 与本次 CC 的相关性 |
|---|---|---|
| FR-M2-001 | 自然语言导出请求识别 | 部分：Session 关联当前请求的线程、模板附件和目标记录；不做自然语言解析。 |
| FR-M2-003 | 通过授权查询能力取得数据字典 | 部分：本 CC 只验证目标记录的当前用户访问权并绑定记录，不调用 Retriever 或读取业务值。 |
| NFR-M2-002 | 权限与数据隔离 | 在范围内：用户、公司、线程、附件和 Session 隔离。 |
| NFR-M2-006 | 隐私最小化 | 在范围内：会话持久化不得保存业务值、样例、模板全文或文件内容。 |
| AC-01 | 唯一目标请求建立 | 部分：合法线程、模板附件、模型/记录上下文可创建 Session；不能唯一确定时的聊天澄清 UI 属后续 CC。 |
| AC-20 | 用户/公司数据隔离 | 在范围内：其他用户/公司不可读取或操作 Session。 |
| BR-M2-002 | 当前权限与安全字段基线交集 | 部分：此处只校验目标记录权限，不定义安全字段基线或向 Provider 暴露字段。 |

### 2.2 DDD 引用

N/A。项目负责人已批准 M2 DDD 适用性 N/A，依据见冻结 TDD V1.0.0。

### 2.3 TDD 引用

| TDD 引用 | 标题 / 条款 | 与本次 CC 的相关性 |
|---|---|---|
| §8.1 | `office.mapping.session` 拟议模型与数据最小化 | 本 CC 实现会话关系和 revision；禁止写入业务值、样例、Prompt、附件 bytes。 |
| §8.2 | 映射会话状态映射 | 会话状态权威基线；本 CC 不得擅自采用与其冲突的枚举。 |
| §9 | 同步生命周期、事务与并发 | 当前用户环境、短事务、revision 乐观并发；本 CC 只实现阶段 3 所需会话持久化，不处理 Office/LLM 长耗时流程。 |
| §10.3 | RPC 服务端验证 | 本 CC 建立后续服务端验证所需身份/关联边界；不交付 Owl 卡片或用户映射 RPC。 |
| §11 | 数据访问控制 | owner/company 隔离；业务记录访问按当前用户授权。 |
| §17 `T-M2-SEC-003` | 不可信输入服务端校验 | 所有客户端字段、关联 ID 和状态值都必须校验。 |
| §17 `T-M2-SEC-004` | Retriever / 当前用户环境 | 本 CC 使用当前用户 `env`，不接受 UID 或权限声明，不以 `sudo()` 查询业务记录。 |
| §17 `T-M2-UI-001` | 服务端状态与 revision 校验 | 仅落实后端状态与 revision 核验入口；UI/RPC 卡片由阶段 4 处理。 |
| §17 `T-M2-BASE-001` | 上游基线与偏移控制 | 发现状态机或权限语义冲突时停止，退回上游设计，不在 CC 内偏移。 |

### 2.4 Implementation Plan 引用

`IMPLEMENTATION_PLAN_office_engine_m2.md` V1.0.0 Frozen，阶段 3“ Odoo 编排层基础与 Mapping Session”。阶段门禁要求在既有 `odoo18ce` 上升级验证，使用 `TransactionCase` 覆盖创建、状态迁移、revision、伪造身份及跨用户/公司拒绝；本 CC 不声称计划阶段 Gate 已通过。

### 2.5 追溯边界

本 CC 只纳入上述 SRS/TDD 条款中的会话持久化和权限部分。AI 映射、样例展示、字段白名单、卡片交互和 M1 生成链路不因本 CC 获得实施授权。

## 3. 范围冻结

### 3.1 在范围内

- 在现有 `office_engine_m2` Addon 中新增 `office.mapping.session`。
- 新增 owner/company/thread/source message/source attachment/target model/target record/state/revision 等最小必要字段；具体字段约束见 §5。
- 新增当前用户环境下的 `create_session(...)`、`get_session_context(...)` 和受控状态迁移服务。
- 校验当前用户对线程、源消息、源附件和目标业务记录的读取权限及彼此关联；校验目标模型属于服务端允许的范围。
- 建立普通用户 ACL、owner/company Record Rule 和服务端不可伪造字段保护。
- 以 Odoo `TransactionCase` 验证正常创建、跨用户/跨公司隔离、无权附件拒绝、非法状态跳转拒绝、revision 过期拒绝及数据最小化。

### 3.2 超出范围

- Provider 调用、`odoo_record_retriever` 的数据查询、模板分析、Mapping Proposal 生成或修复重试。
- Mapping Card、Owl/JS、聊天消息渲染、面向用户的编辑/确认 RPC；归阶段 4 及后续 CC。
- M1 `office_core`/`office_verify` 的文件读取、渲染、附件生成与交付。
- Skill 模型、保存/匹配/复用、公共 Skill 或审计治理。
- 任意模型/domain 查询接口、任意动态目标模型访问、对业务记录的创建或写入。
- 修改 `office.llm.usage`、CC-M2-002 的 Provider 代码或已有 Usage ACL。
- 修改冻结 SRS、TDD 或 Implementation Plan；新增字段/状态/权限语义若上游未定义，必须先升级处理。

### 3.3 非目标

- 本 CC 不构成端到端 Office 文件生成功能已完成的证明。
- 本 CC 不向 LLM、聊天正文或持久化模型提供业务字段值或样例。
- 本 CC 不实现完整 Session 过期清理、异步恢复或任务队列。

## 4. 变更边界

### 4.1 允许修改

代码必须且只能位于现有 `mymodules/office_engine_m2/` Addon 中。允许新增或修改：

| 路径 | 允许内容 |
|---|---|
| `mymodules/office_engine_m2/__manifest__.py` | 仅在需要时增加本 Addon 自身的安全数据文件声明；不得新增未经 TDD 批准的核心依赖。 |
| `mymodules/office_engine_m2/models/__init__.py` | 导入本 CC 新增 Session 模型。 |
| `mymodules/office_engine_m2/models/office_mapping_session.py` | 新增 `office.mapping.session`、字段约束、访问保护和受控状态/修订校验。 |
| `mymodules/office_engine_m2/services/__init__.py` | 暴露本 Addon 内部服务模块。 |
| `mymodules/office_engine_m2/services/mapping_service.py` | 新增 `create_session(...)`、`get_session_context(...)`、必要的受控 transition/revision 服务。 |
| `mymodules/office_engine_m2/security/ir.model.access.csv` | 增加 Session 模型 ACL；保留 Usage ACL 原行和语义。 |
| `mymodules/office_engine_m2/security/office_engine_m2_groups.xml` | 仅在实现所需、且符合 TDD 时增加 Session 用户权限配置；不得扩大 Usage 组权限。 |
| `mymodules/office_engine_m2/security/office_mapping_session_rules.xml` | 新增 owner/company 记录规则，并在 manifest 中声明。 |
| `mymodules/office_engine_m2/tests/test_mapping_session.py` | 新增 `TransactionCase`。 |
| `mymodules/office_engine_m2/tests/__init__.py` | 注册新增测试。 |

若实现需要修改上述清单以外文件、添加新的 Addon、字段、外部依赖、控制器或 UI，必须暂停并先修订本 CC 或上游 TDD/Plan。

### 4.2 禁止修改

| 类型 | 禁止事项 |
|---|---|
| 其他模块 | 禁止修改 `mymodules/odoo-llm/`、`office_engine_odoo/`、Odoo 官方源码或其他 Addon。 |
| 既有 Usage | 禁止修改 `office.llm.usage`、Usage 服务、Provider 标准化逻辑、权限组含义及 CC-M2-002 现有测试。 |
| 权限绕过 | 禁止在 Session、thread、mail.message、ir.attachment、目标业务模型的读取/写入路径使用 `sudo()`、`env(su=True)` 或提升 UID。不得把已存在的 Usage 专用受限创建提权扩展到其他模型。 |
| 状态语义 | 状态冲突已按 §0.3 负责人裁定关闭；实施必须严格采用其批准的 8 状态及转换，不得增加别名或偏离上游基线。 |
| 文件/AI | 禁止在本 CC 调用 Provider、读写模板内容、生成业务值或创建下载附件。 |
| 敏感数据 | 禁止新增保存 Prompt、模板完整文本、业务样例明文、附件 bytes、LLM 原始响应的字段/日志。 |

## 5. 必需的行为变更

| ID | 当前行为 | 期望行为 | CC-CHANGE ID |
|---|---|---|---|
| 1 | `office_engine_m2` 尚无受控的 Mapping Session 模型。 | 新增最小 Session 模型，保存当前用户/公司、线程、上传消息/附件、目标模型/记录、上游批准的状态及 revision；身份和初始状态由服务器确定。 | CC-CHANGE-001 |
| 2 | 尚无统一服务校验 Session 关联对象权限与关系。 | `create_session(...)` 使用调用方当前 `env`，验证 thread/source message/source attachment/target record 的读取权、公司边界和关联关系；任一不满足时拒绝且不留下 Session。 | CC-CHANGE-002 |
| 3 | 尚无按当前所有者读取 Session 上下文的内部接口。 | `get_session_context(...)` 仅返回当前用户有权访问的最小会话元数据及 revision；跨用户/跨公司不可见，不返回模板文本、Prompt 或业务样例。 | CC-CHANGE-003 |
| 4 | Session 状态/修订尚无服务端保护。 | 通过内部服务执行上游状态机允许的转移；非法直接跳转、直接写状态或使用旧 revision 均拒绝且不改变状态/revision。 | CC-CHANGE-004 |
| 5 | Usage Addon 尚无 Session 数据 ACL / owner Record Rule。 | 普通用户可在本人授权边界内创建、读取和经服务修改自己的 Session；不能读取/写入/删除其他用户 Session，不能删除 Session；现有 Usage ACL 不变。 | CC-CHANGE-005 |
| 6 | Session 模型需要最小化数据契约尚未有自动化保护。 | 明确拒绝未定义字段及 Prompt/模板全文/样例明文/附件内容等敏感输入；模型字段和服务返回均不包含上述业务内容。 | CC-CHANGE-006 |

### 5.1 Session 字段契约

| 字段 | 要求 |
|---|---|
| `owner_id` | 必填；服务端从 `env.user` 派生，不接受客户端赋值。 |
| `company_id` | 必填；服务端从当前请求的 `env.company` 派生；不接受客户端赋值，并验证其处于当前用户允许公司范围。 |
| `thread_id` | 必填，关联现有 `llm.thread`；当前用户须有读取权。 |
| `source_message_id` | 按冻结 TDD/阶段 3 计划保存上传来源消息关联；如线程/附件关系无法由现有模型可靠验证，停止并升级，不得省略验证。 |
| `source_attachment_id` | 必填，关联 `ir.attachment`；当前用户须有读取权，且附件必须与指定源消息/线程一致。 |
| `target_model` | 必填技术模型标识；必须来自服务端允许范围，不接受任意客户端模型名。 |
| `target_record_id` | 必填正整数；与 `target_model` 成对校验，记录必须存在、当前用户可读且通过记录规则/公司边界。 |
| `state` | 由服务端初始化和转换；仅使用 §0.3 解决后确认的冻结状态枚举；客户端不能直接设置。 |
| `revision` | 服务端管理的正整数，创建初值为 1；有效映射/状态修改按冻结 TDD 的规则递增，期望 revision 不匹配时拒绝。 |
| `error_code` | 可选稳定错误类别，仅允许无正文的代码；不得保存堆栈、Prompt、模板文字或业务字段值。实施计划阶段 3 明确包含错误类别，因此本 CC 按该上游范围实现。 |

不得增加模板文本、Prompt、Mapping Plan 明文、样例值、文件内容或任意模型字段序列化快照字段。对于 M2 后续映射规则的存储方式，本 CC 不作定义。

### 5.2 服务契约

#### `create_session(...)`

- 只能由本地 Python 服务调用路径使用，不新增对外 Controller / RPC / 公共模型动作。
- 使用调用者传入的当前用户 `env`；拒绝任何 `uid`、owner、company、权限布尔值、记录规则结论、任意 domain 或 `sudo` 参数。
- 接收必要的 thread、源 message、source attachment、target model/record 引用；先进行当前用户访问检查和对象间关系检查，再创建 Session。
- `owner_id`、`company_id`、初始 `state`、`revision` 只能由服务端确定。客户端额外传入未白名单字段应拒绝，不得静默透传。
- 创建失败必须保持数据库无 Session 残留；错误不得泄露无权附件、线程或业务记录是否存在。

#### `get_session_context(...)`

- 按当前用户环境读取；查询应受 ACL 与 owner/company Record Rule 双重限制。
- 返回仅含本 CC 允许字段的受控字典；不得包含附件 `datas`、模板正文、Prompt、记录字段值/样例或无权对象名称。
- 用户 B 请求用户 A 的 Session 时，采用不泄露存在性的受控拒绝/未找到结果；不得通过 `sudo()` 后再在 Python 中过滤。

#### 受控状态与 revision 服务

- 状态转换由本地服务入口执行；模型 `write()` 必须拒绝客户端对 `state`、`owner_id`、`company_id`、`revision` 的任意直接更改。
- 每次变更必须验证调用人、当前状态、允许的转换和 `expected_revision`；过期 revision 或非法转换不写库。
- 状态集合和转换严格遵循 §0.3 已裁定的 8 状态映射；不得采用任务原始 6 状态，也不得增加别名。

## 6. 既有行为保留

| ID | 行为 / 契约 | 为什么不得改变 | CC-PRESERVE ID |
|---|---|---|---|
| 1 | CC-M2-002 Provider Usage 标准化、Usage 计量和管理员/运维只读权限保持不变。 | 已关闭 CC 的交付契约；Session 不能改变 Provider 响应或 Usage ACL。 | CC-PRESERVE-001 |
| 2 | 使用当前 Odoo 用户环境访问业务记录、线程、消息和附件；不以管理员身份扩大权限。 | TDD `T-M2-SEC-004` 与 SRS 数据隔离要求。 | CC-PRESERVE-002 |
| 3 | M2 Session 不存储 Prompt、模板正文、业务数据样例或附件 bytes。 | SRS `NFR-M2-006`、TDD §8.1 数据最小化。 | CC-PRESERVE-003 |
| 4 | M1 与阶段 1 `office_mapping_verify` 契约及既有权限不变。 | 本 CC 只建立编排上下文，不改文件引擎或纯 Python 校验器。 | CC-PRESERVE-004 |
| 5 | M2 没有 Mapping Card / AI / M1 渲染的阶段边界。 | 计划阶段 3 不含阶段 4/5 行为。 | CC-PRESERVE-005 |

## 7. 适用的 TDD 防护栏

| TDD 防护栏 | 适用性 | 本次落实位置 | 验证方式 |
|---|---|---|---|
| `T-M2-SEC-003` | 适用 | 所有关联 ID、状态、revision、额外字段服务端白名单校验 | CC-TEST-001–006 |
| `T-M2-SEC-004` | 适用 | 当前用户 `env` 访问 thread/message/attachment/target record；无 `sudo()` | CC-TEST-002–006；静态检查 |
| `T-M2-UI-001` | 部分适用 | 后端限制状态直接写入并验证 revision；不实现 UI/RPC | CC-TEST-004、005 |
| `T-M2-DATA-002` | 适用 | 只保存关联与状态元数据，不记录 Prompt/Completion/模板/样例 | CC-TEST-006 |
| `T-M2-BASE-001` | 适用 | 状态冲突、模型/字段需求与上游不一致时停止；严格按基线实施 | 评审确认 §0.3；变更范围审查 |

## 8. 数据与迁移影响

| 字段 | 值 |
|---|---|
| 需要迁移 | 是；新增 `office.mapping.session` ORM 表及 ACL/Record Rule 数据。 |
| 迁移脚本 | N/A；使用 Odoo Addon 标准模块升级创建新模型。 |
| 数据源 | 当前请求环境中的 thread、source message、`ir.attachment` 与目标模型/记录 ID。 |
| 目标 | `office.mapping.session` 最小关系字段与状态元数据。 |
| 恢复 / 回滚策略 | 新模型尚无生产数据；升级失败按 Odoo 模块升级失败处理并修正/向前升级。若目标开发数据库出现本 CC 测试记录，使用 TransactionCase 回滚或通过 ORM 按唯一测试标记清理；禁止直接删除 filestore 文件。 |
| 验证 | 在既有 `odoo18ce` 执行模块升级和 `TransactionCase`；核对模型/列/ACL/规则，确认未产生持久测试 Session。 |

不得重建或迁移 `office.llm.usage` 表，不得更改其数据。

## 9. API / 集成影响

| 字段 | 值 |
|---|---|
| 修改的端点 | 无；本 CC 不新增 HTTP、JSON-RPC 或 Controller 路由。 |
| 向后兼容 | 是；仅在现有 `office_engine_m2` Addon 中增加模型和内部服务。 |
| Adapter 变更 | 无；不修改 Provider、Retriever、聊天适配或 M1 Adapter。 |
| 内部接口 | Python 内部服务 `create_session(...)`、`get_session_context(...)`、受控状态/revision 入口；不得暴露为模型公开 RPC。 |

## 10. 安全 / 权限影响

| 字段 | 值 |
|---|---|
| 新权限 | 普通内部用户在 Record Rule 限制下可创建/读取/修改本人 Session 的允许字段；不得 unlink；运维/管理员不自动读取其他用户 Session。 |
| 变更的 ACL | 新增 `office.mapping.session` ACL 和 owner/company Record Rule；保留 `office.llm.usage` 现有 ACL，不扩权。 |
| 访问边界 | `owner_id = env.user.id` 且 `company_id` 必须处于当前用户允许公司集合；跨用户或跨公司 Session 默认拒绝。 |
| 敏感数据暴露检查 | 仅返回最小会话元数据；错误统一化以避免披露无权对象存在性；禁止持久化 Prompt、模板全文、样例明文和附件内容。 |
| 提权规则 | Session、thread、message、attachment、target record 全路径禁止 `sudo()` / su 环境；CC-M2-002 的 Usage 专用提权逻辑保持原样且不得复用。 |

实现须防止直接 ORM/RPC 调用绕过业务服务：`create()` 必须从环境派生 owner/company 并验证关系；`write()` 必须拒绝客户端修改受保护字段或非法 transition；访问控制不能仅靠视图 `readonly` 属性。

## 11. 测试契约

全部 Odoo 集成测试使用现有 `odoo18ce` 的 `TransactionCase` 和合成 fixture，不调用真实 LLM/外网，不创建隔离数据库。运行前记录 Odoo、Python、PostgreSQL 与 `office_engine_m2` 版本；测试完成后确认事务回滚/ORM 清理。

| 测试 ID | 对应变更 | 上游来源 | 测试类型 | 预期结果 | 人工验证 | 原因 |
|---|---|---|---|---|---|---|
| CC-TEST-001 | CC-CHANGE-001 | TDD §8.1；Plan 阶段 3 | TransactionCase | 具备有效当前用户、公司、线程、源消息/附件及可读目标记录时，创建一条 Session；owner/company 从环境派生，初始 revision 为 1；Session 不含禁止字段。 | 否 | 验证正常创建链路和最小模型契约。 |
| CC-TEST-002 | CC-CHANGE-002 | FR-M2-001；NFR-M2-002；TDD §10.3/§11 | TransactionCase | 当前用户无 thread 或 source message 读取权、附件读取权或目标记录读取权时，创建失败；失败后无 Session；异常不泄露无权对象是否存在。 | 否 | 验证每个绑定对象都服从调用用户权限。 |
| CC-TEST-003 | CC-CHANGE-002 | TDD §8.1；Plan 阶段 3 | TransactionCase | 附件未关联给指定消息/线程、消息属于另一线程、目标模型与记录不匹配、目标记录不存在或不在允许模型范围时拒绝创建。 | 否 | 防止跨线程拼接附件或任意模型/记录注入。 |
| CC-TEST-004 | CC-CHANGE-004 | TDD §8.2；`T-M2-UI-001` | TransactionCase | 试图从初始化状态直接转为 `completed`（或上游确定的等价非法跳转）被拒绝；state 与 revision 均保持原值。 | 否 | 验证不能绕过正常映射/确认/渲染生命周期。 |
| CC-TEST-005 | CC-CHANGE-004 | TDD §8.2/§9 | TransactionCase | 合法状态转换通过；过期 `expected_revision`、客户端直接 write state/owner/company/revision、非法转换均拒绝，revision 不被静默覆盖。 | 否 | 验证并发控制和服务端状态权威。 |
| CC-TEST-006 | CC-CHANGE-003/005/006 | NFR-M2-002/006；AC-20；TDD §8.1/§11 | TransactionCase / 安全断言 | 用户 A 创建 Session 后，用户 B 的搜索、读取、写入与 `get_session_context` 均无法访问该记录；不泄露 Session 内容。A 不可跨越公司边界；普通用户不能 unlink。使用禁止键/样例哨兵值创建时拒绝且不持久化。 | 否 | 验证 owner/company 隔离、禁止数据持久化和访问面。 |
| CC-TEST-007 | CC-CHANGE-001/005 | Plan 阶段 3 Gate | Odoo 模块升级 | 在 `odoo18ce` 上升级 `office_engine_m2` 成功；Session 模型、ACL、Record Rule 加载；原 Usage 模型及 ACL 无回归。 | 否 | 证明真实 Odoo Registry/数据库层安装可用。 |
| CC-TEST-008 | 全部 | §4 文件白名单；`T-M2-SEC-004` | 静态范围检查 | 变更仅在 §4.1 文件白名单；Session 模型/服务无 `sudo()`、su 环境或 uid 切换；Provider/Usage 原有代码差异为空；`git diff --check` 通过。 | 否 | 防止权限旁路或越界改动。 |

**测试状态规则：** 本 CC 已冻结并获准实施；CC-TEST-004/005 的状态值和转换矩阵以 §0.3 为准。ATR 只记录实际执行证据和真实结果。

## 12. 停止条件 / 升级闸门

| 触发条件 | 升级路径 |
|---|---|
| Odoo `llm.thread`、message、attachment 的关系结构无法按当前用户权限可靠核验 | 暂停，不猜字段/模型关系；回到 TDD 补充明确接口或验证计划。 |
| 普通用户需依赖 `sudo()` 才能创建/读取 Session 或校验关联对象 | 停止；按 TDD/SRS 调整权限设计，不允许以“内部服务”为理由提权。 |
| 需要新增状态、字段、权限组、公开模型方法、Controller、UI 或新 Addon 才可满足契约 | 暂停并评估是否属于 TDD/Plan 基线变更；按上游变更流程重新批准。 |
| Record Rule 导致本用户无法访问本人有效会话，或管理员意外可读他人会话 | 暂停安装/交付；修正设计并重跑完整权限矩阵。 |
| 线程/附件/业务记录结构出现无法确认的跨公司语义 | 暂停受影响验证，按 SRS 公司隔离规则回到上游澄清。 |

## 13. 完成定义 / 关闭标准

本 CC 已由负责人评审、冻结并授权实施。关闭前仍须满足：

- §0.3 状态基线冲突已由负责人正式解决；本 CC 与当前冻结 SRS/TDD/Plan 一致。
- CC-CHANGE-001–006 已完成；CC-PRESERVE-001–005 无回归。
- CC-TEST-001–008 按实际运行记录在 ATR；所有要求 PASS，未通过项按工作流授权流程处理，不能改写原始失败状态。
- `TransactionCase` 证明用户 A 创建、用户 B 完全不能读取或操作；非法状态转移、旧 revision、无权附件/记录均拒绝且无残留 Session。
- Odoo 模块升级及模型、ACL、Record Rule 证据记录于 ATR；清理/事务回滚结果可核验。
- IHR、ATR 和基于证据的 FR 已按工作流建立；因本 CC 不交付用户可见 UI，HVR 如适用性判断为 N/A，须在 FR/记录中给出理由。
- 变更范围和 `git diff --check` 检查通过；CC-M2-002 Provider/Usage 路径未被改动。

完成定义与关闭批准记录分开管理。负责人于 2026-10-23 明确批准关闭；关闭评估见 [`FR-M2-003_mapping_session.md`](FR-M2-003_mapping_session.md)。冻结契约版本保持 V1.0.0，不因关闭而改写。

### 13.1 关闭记录

| 项目 | 结果 |
|---|---|
| 关闭批准 | 负责人于 2026-10-23 批准关闭 CC-M2-003 |
| FR | [`FR-M2-003_mapping_session.md`](FR-M2-003_mapping_session.md)，`SATISFIED` |
| ATR / IHR | [`ATR-M2-003.md`](ATR-M2-003.md) / [`IHR-M2-003_mapping_session.md`](IHR-M2-003_mapping_session.md) |
| 实施代码基线 | `1e33a25`（完整 hash 记录于 IHR/FR） |
| M2 阶段 3 计划门禁 | CC 本身关闭；Implementation Plan 阶段 3 的 XML-RPC 安装/升级证据尚未提供，阶段门禁保持未关闭，不据此宣称阶段 3 Gate 全部通过 |

## 14. 本稿未决项与决策记录

### 14.1 未决项

| 编号 | 事项 | 当前状态 | 关闭责任 | 影响 |
|---|---|---|---|---|
| `CC-M2-003-OPEN-001` | 用户要求状态名与 TDD/SRS 状态集合、语义的对应关系 | RESOLVED — 负责人裁定采用 TDD V1.0.0 §8.2 的 8 状态 | 负责人已裁定（2026-10-23） | 不修改 TDD/SRS；按 §0.3 实施。 |
| `CC-M2-003-OPEN-002` | `llm.thread`、上传消息、`ir.attachment` 的关系模型 | RESOLVED — 源码确认 `llm.thread.message_ids` 与 `mail.message.attachment_ids`；消息以 `model='llm.thread'`、`res_id=thread.id` 关联。 | 源码核查，实施时由 CC-TEST-002/003 验证 | `create_session` 必须同时验证 thread owner、message relation、attachment membership 与当前用户访问权。 |
| `CC-M2-003-OPEN-003` | `error_code` 是否属于阶段 3 Session 最小字段 | RESOLVED — Implementation Plan 阶段 3 明确要求错误类别 | 冻结 Implementation Plan V1.0.0 §3 | 仅持久化稳定非敏感类别，不存错误正文/堆栈。 |

### 14.2 CC 决策记录

| 编号 | 决策 | 依据 | 状态 |
|---|---|---|---|
| CC-DEC-001 | 仅扩展既有 `office_engine_m2`，不新增平行 Addon。 | 当前 Addon 已由 CC-M2-002 创建，Plan 阶段 3 明确在其上建立编排基础。 | APPROVED — 本 CC 冻结基线 |
| CC-DEC-002 | Session owner/company 必须由当前 `env` 派生，ACL 与 owner/company Record Rule 双重约束；不为 Session/thread/attachment/业务记录使用 `sudo()`。 | SRS NFR-M2-002、TDD §§10–11 与 `T-M2-SEC-004`。 | APPROVED — 本 CC 冻结基线 |
| CC-DEC-003 | 禁止存储 Prompt、模板全文、业务样例明文、LLM 原文或附件 bytes；只存最小关系与受控状态元数据。 | SRS NFR-M2-006、TDD §8.1。 | APPROVED — 本 CC 冻结基线 |
| CC-DEC-004 | Session 状态严格采用冻结 TDD V1.0.0 §8.2 的 8 个技术状态及 §0.3 转换矩阵；原 6 状态请求不形成实现值。 | 负责人明确裁定；保持 TDD/SRS 基线不变。 | APPROVED |

### 14.3 版本历史

| 版本 | 日期 | 状态 | 说明 |
|---|---|---|---|
| V0.1 | 2026-10-23 | Draft | 起草 Mapping Session、内部服务、ACL/Record Rule 与 TransactionCase 契约；记录状态机基线冲突。 |
| V1.0.0 | 2026-10-23 | FROZEN | 负责人裁定采用 TDD V1.0.0 §8.2 的 8 个状态并批准实施；关闭源码关系与 error_code 字段 OPEN 项。 |
| Implementation | 2026-10-23 | FROZEN baseline retained | 实施记录转入 ATR/IHR；同步修正文内与已裁定状态基线冲突的 Draft 残留措辞。 |
| Closure | 2026-10-23 | CLOSED | 负责人批准关闭；基于 ATR/IHR 形成 FR。Frozen V1.0.0 契约内容不变。 |
