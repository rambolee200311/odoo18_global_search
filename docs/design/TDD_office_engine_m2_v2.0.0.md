# Odoo Office Engine M2 技术设计说明书（TDD）— LLM 主导的后续 Excel 编辑

| 项目 | 内容 |
|---|---|
| 文档编号 | TDD-OFFICE-ENGINE-M2 |
| 版本 | V2.0.0 |
| 状态 | **DRAFT — AUTHORIZED FOR REVIEW — NOT AUTHORIZED FOR IMPLEMENTATION** |
| 日期 | 2026-11-06 |
| 上游需求 | M2 SRS V1.0.0 Frozen；V1.1.0 Frozen change baseline（业务范围不变，技术路线存在待正式变更差异） |
| 上游技术设计 | `TDD_office_engine_m2.md` V1.0.0 Frozen；`TDD_office_engine_m2_v1.1.0.md` Frozen；动态行补充 V1.1.0 Frozen |
| 架构评估 | `ARCHITECTURE_CHANGE_IMPACT_ASSESSMENT_M2_v0.2.md` Frozen review baseline |
| TV 依据 | Candidate B Phase 1A-2 Report V0.2；Phase 1B–1D Report V0.2；TV Plan V0.2.1 |
| DDD | N/A 既有决定保留；本设计不新增 DDD。若实施揭示稳定领域不变量，按变更控制重评 |
| 授权边界 | 仅授权形成 TDD 评审稿；不授权编码、部署、服务重启、模块升级或 TV 重跑 |

> 本文是新路线的技术设计草案，不是实现或 TV 通过报告。V1.0.0、V1.1.0 和动态行补充均保留为历史冻结文件。本版只有在人工评审、正式基线变更以及另行实施授权后，才可成为实施依据。

## 0. 设计目的、范围和变更控制

### 0.1 目的

本版将 **Candidate B：OpenAI Responses API + Code Interpreter** 设为开放式后续 Excel 编辑的目标技术路线，同时保留 M1 和 M2 初始模板填充。本地 Office Engine 负责首轮 Odoo 数据填充；首轮后，LLM 在受控托管文件编辑环境中操作当前有效工作簿。本地 Odoo 继续拥有权限、安全、业务风险确认、版本接受、独立验证和交付决定权。

这改变的是**技术实现路线**，不是新增“首轮数据填充”或“用户连续修改 Office 文件”的产品需求。新路线仍须与冻结 SRS 的现有 AI 文件读写边界完成正式的版本化对齐；本 TDD 不覆盖或静默修改 SRS。

### 0.2 范围

本 TDD 定义：初始填充与后续编辑的职责分界、Data Tool JSON 边界、Responses/Code Interpreter Provider Adapter、工作簿版本谱系、编辑前确认、编辑后本地验证、预览/正式交付门禁、失败恢复及后续验收要求。

本 TDD 不定义任意代码执行、Candidate C、完整自然语言语义验证器、通用 Excel 编辑 DSL 或第二套本地文件编辑器。初始数据映射仍使用已经批准且经现有 M1 验证的 Mapping/Canonical Operations 能力；不得为开放式后续编辑继续扩张本地 Excel DSL。

### 0.3 规范优先级与未解决的上游差异

1. 冻结 SRS 仍是业务需求权威。SRS 中“AI 仅提出受约束 Mapping Proposal、不得直接读写文件/执行代码”的条款与本路线不一致。该冲突必须在实施前通过正式 SRS 变更解决；本 TDD 草案不能单方面解除它。
2. 本路线不降低既有 Odoo ACL、Record Rules、附件访问、文件安全、资源预算、用户确认及失败关闭要求。
3. 现有 TDD 版本、Implementation Plan 与 CC 均不因本稿自动改变。批准本 TDD 后，还须单独修订受影响的实施计划和 CC 契约。
4. 证据状态按实际 TV 报告保留。接口文档/SDK 方法存在不等于模型、当前 Provider 凭据、工作簿编辑、集成和交付均通过。

## 1. 设计结论与 TV 证据边界

### 1.1 保留、替换与新增

| 处理 | 组件/能力 | 本版职责 |
|---|---|---|
| 保留 | M1 文档安全检查、资源限制、Worker、初始文件生成及验证 | 继续执行首轮模板填充；后续编辑候选仍须经过本地独立验证边界 |
| 保留 | M2 当前用户 ORM Retriever、ACL/Record Rules、Session/Thread、私有附件、原生附件卡和 OnlyOffice 预览路径 | 负责首轮授权数据、后续 Data Tool 查询、会话所有权与交付；新路线不得擅自替换既有附件/预览界面 |
| 保留 | 现有 Proposal、初始 Mapping 校验和 Canonical Operations | 限于首轮填充和已有兼容流程；不把它们作为后续任意自然语言编辑的执行器 |
| 保留 | Odoo 普通聊天的 Chat Completions Provider 路径 | Responses Adapter 与普通聊天并存；不得替换或破坏原有聊天调用 |
| 替换（经正式基线变更后） | 首轮之后的本地 Mapping/Operation 再编译并写入 Excel | 改由 Responses API + Code Interpreter 对当前有效 XLSX 执行编辑；Odoo 不执行模型生成的代码 |
| 新增（设计目标） | Responses Provider Adapter、工作簿版本清单、编辑前确认与本地候选验证/接受衔接 | 连接 Provider 输出与 Odoo 权威状态，不让远端响应直接成为有效版本 |
| 新增（契约） | 仅返回授权 JSON 的后续数据刷新 Data Tool | 不映射 Excel 坐标、不生成文件操作、不写入工作簿 |
| 不新增 | 本地通用表达式编辑器、任意 Python/eval、DAG/事件总线、Candidate C | 不属于本轮目标 |

### 1.2 已有 TV 事实

| 能力 | 当前证据 | 结论边界 |
|---|---|---|
| Responses API + Code Interpreter 对简单合成 XLSX 的单轮编辑和真实文件返回 | Phase 1A-2 V0.2：实际响应、实际输出字节、下载和独立 `openpyxl` 回读；目标值与所检查的非目标值、公式文本、样式及 ZIP 结构断言通过 | 仅证明该合成小文件的一次简单编辑闭环，不证明多轮、复杂结构、Odoo 集成或用户交付 |
| `gpt-5.6-luna` 与所用当前凭据的该次调用 | Phase 1A-2 有三次真实请求，第三次产生经回读验证的文件 | Odoo Provider 的 Project ID 未记录；不能据此证明全部部署环境或长期可用性 |
| TV-LE-02 单轮扩展用例、TV-LE-03 多轮、TV-LE-04 复杂保真 | Phase 1B–1D V0.2：两次 Responses 调用均在收到 Response 前 `APIConnectionError`；无候选输出。第一轮后加入重试时，预算预留未重新纳入完整重试次数；精确费用/预算合规未能核实 | `BLOCKED/UNVERIFIED`，不是模型编辑能力 `FAIL`，也不是 PASS。保留原报告记载，不覆盖历史事实 |
| 复杂公式重算、大规模工作簿、附件/浏览器集成、刷新后保留编辑、失败恢复 | 当前所引 TV 未覆盖 | `UNVERIFIED` |

任何后续验收均须区分：API 路由可用、模型支持、当前 Provider/Project 可调用、真实编辑产物返回、文件独立验证、Odoo 状态接受、附件交付、浏览器下载。这些不是同一 PASS。

## 2. 架构与职责边界

### 2.1 组件职责

| 层 | 责任 | 明确禁止 |
|---|---|---|
| Odoo Chat / M2 Orchestrator | 将 Thread 消息、当前有效版本、授权上下文和执行结果关联；路由首轮填充、后续编辑、确认、澄清及交付 | 以模型自由文本覆盖服务端执行事实 |
| Initial Mapping Pipeline | 当前用户 ORM 读取业务数据；将用户映射意图和模板目标变为现有受限 Mapping；调用 M1 生成首轮文件并回读验证 | 扩大 ACL；把首轮功能未经校验地用于后续开放式编辑 |
| Odoo Data Tool | 按当前用户 ORM / ACL / Record Rules 查询，返回带记录身份、业务键、类型、快照范围、分页/完整性和来源信息的 JSON | 指定工作表/单元格；产生编辑指令；写 XLSX；用行号识别业务记录 |
| Intent/Confirmation Gate | 对 Agent 提交的本轮目标/预期 Effect 做可核验解析；检查文件访问、可确认业务风险和不可绕过约束；在必要时向用户说明风险并取得绑定授权 | 让确认绕过 ACL、安全/完整性限制；把不明确范围当成已确认 |
| Responses Provider Adapter | 使用现有 OpenAI Provider 的受控凭据，通过 Responses API 提交当前 XLSX、用户意图及批准数据；读取调用/工具/文件结果与 usage 元数据；施加预算、超时和重试规则 | 暴露凭据；改变普通 Chat Completions；把文本/代码块伪装成 XLSX |
| Hosted Code Interpreter | 在 Provider 托管的隔离工具环境中，按 LLM 计划检查并编辑工作簿，返回真实候选文件；用于模型驱动的文件编辑 | 访问 Odoo 凭据或业务 ORM；获得 Odoo 服务进程任意代码执行；决定权限、确认或最终接受 |
| Candidate Validator | 在 Odoo 本地对真实输出字节做格式、安全、结构、声明 Effect、输入输出差异和非目标变化的独立检查 | 信任模型声称的已修改范围；重写候选文件来“修复”不合格结果 |
| Version/Artifact Service | 保存私有输入/候选/有效/正式附件及哈希、父版本、确认、验证、Provider 与交付元数据；仅接受符合门禁的候选 | 将失败候选提升为当前有效版本；让旧确认适用于新文件/Effect |
| Attachment/Delivery | 将已接受的 Preview/Finalize 附件关联到正确 Session、Thread 和消息；记录实际发布及下载状态 | 将 Provider 返回文件 ID 或原生工具消息 `completed` 等同于用户已收到正式文件 |

### 2.2 分离的两条文件路径

**首轮填充（保留）：**

`用户指令 + 模板 → 当前用户 ORM Data Retrieval → 首轮 Mapping/Proposal 校验 → M1/office_core 初始填充 → 本地独立回读 → V1 私有预览`

**首轮后编辑（新目标路线）：**

`用户指令 + 当前有效版本 → 预期 Effect/确认门 → Responses API + Code Interpreter → 真实候选字节 → 本地独立验证 → 有效版本升级 → Preview/Finalize 附件`

初始 Mapping 与后续 LLM 编辑可以在同一 Thread/Session 中，但不得共用一条会令后续内容写回走本地 Mapping 执行器的隐式路径。M1 初始生成仍须通过既有资源/格式门禁。

### 2.3 后续 Odoo 数据补充/刷新

`用户要求刷新数据 → Data Tool 当前用户 ORM 查询 → typed JSON snapshot → LLM/Code Interpreter 按业务键/稳定记录身份匹配当前工作簿 → 本地候选验证/确认 → 新版本`

Data Tool 只负责数据及来源/快照契约。JSON 不包含 Excel 坐标、工作表名、行号或“写到某格”的动作。由 LLM 理解业务意图并应用 JSON 至当前工作簿；本地不执行第二轮填表。记录无法唯一关联、快照不完整或存在未确认覆盖风险时，必须澄清、阻断或请求确认，不得按当前行号猜测。

至少表达 `snapshot_type`（`full`/`incremental`）、查询域、查询时间、页数/游标/总量或可验证完整性标记、稳定身份与业务键、字段类型/来源及区分 `null`、`false`、`0`、`0.0`、`""` 的值表示。`full` 仅覆盖明确查询域；`incremental` 未返回记录不代表删除；不完整分页的 `full` 不可用于依赖完整集合的同步。具体 JSON Schema 由后续 CC 在本 TDD 冻结后细化，不得在本地追加单元格 Mapping DSL。

## 3. Provider 与受控文件编辑契约

### 3.1 Adapter 边界

在现有 OpenAI Provider 客户端外增加可替换的 Responses 调用适配层。适配器消费 Provider 既有凭据/API 配置，不复制或明文持久化 Secret；普通 `client.chat.completions.create()` 聊天适配器继续原样可用。Responses API 的文件输入/工具执行/文件下载按当前获准 Provider 配置封装；Odoo 编排层不依赖 SDK 的原始响应对象。

输入必须绑定：Session、当前有效版本 ID 与 SHA-256、用户消息 ID/指令、必要的经授权 JSON、声明的预期 Effect、有效确认收据、模型/工具策略、资源和费用上限。输出至少包括真实 XLSX bytes 或可安全下载引用、Response/请求 ID（可得时）、工具执行状态、文件引用、token/usage（可得时）、耗时、清理状态及结构化错误分类。所有第三方 ID 均作为不可信元数据，不能替代本地版本校验。

### 3.2 隔离、资源与成本

- Code Interpreter 在 Provider 托管执行环境处理输入文件；不得把模型生成 Python 发送给 Odoo 执行。Odoo 本地仅下载候选并验证。
- 不向 CI 提供 Odoo API Key、数据库连接、文件系统路径或其他本地密钥。外部联网、工具权限、文件大小/膨胀、输出数量、响应时长和容器资源应按 Provider 可配置能力最小化；若必要边界无法实施或观察，候选不得自动接受，列为阻断条件。
- 调用前根据输入上限、输出上限、CI 资源单价/时长和重试预留计算保守预算；超出 Session/组织预算时不发请求。记录可获取的实际 usage 与成本估算，明确账单金额是否真实可得。
- Phase 1A-2 的 `max_tool_calls=1` 请求参数未能可靠限制实际 CI 调用次数；不得把该参数单独当成硬预算门。后续实施必须有可验证的总请求/工具调用/容器资源计量或安全上限，无法保证上限时应在远端执行前阻断。
- SDK 隐式重试关闭。连接失败若无法判定远端是否受理，不得盲目重发；先按请求/响应/远端文件引用核对可恢复状态。只有在调用具有可验证幂等键、确认未执行且剩余预算允许时才重试；否则保留歧义状态，提示可恢复的失败/待核查结果。
- 清理容器及远端文件为尽力且可审计的资源回收。清理失败不把文件编辑伪报成功或失败；记录 `cleanup_pending`，依据留存策略重试清理。若数据政策/远端留存要求不能满足，则在上传前阻断。

### 3.3 Provider 结果判定

只有从受支持的文件引用成功取回非空字节、并通过本地候选文件初步检测，才能将 Provider 阶段记为 `candidate_received`。模型文本声称完成、返回代码、工具调用成功或只有远端容器文件名，都不能满足此条件。未收到真实 XLSX、下载失败或响应与当前版本/请求不匹配时，状态保持失败/待核查；不得生成虚假附件。

## 4. 意图、Effect、确认与用户决策权

### 4.1 意图与预期 Effect

LLM 负责将本轮自然语言解释为本地可审阅的目标/预期变化描述：工作表/区域或目标集合、修改类别、旧值状态或覆盖范围、预期新值/公式/格式/结构结果、受影响范围及未能解析部分。它是操作意图的结构化声明，不是执行命令授权，也不构成语义理解完整性的证明。

若目标或数据身份不唯一、预期效果无法表达或影响范围无法确定，结果是澄清/阻断，不是让 Provider 自行扩大范围。系统必须将未结构化的用户要求显式反馈，不得静默略过。

### 4.2 确认门

本地在发送编辑请求前评估安全约束和可确认的业务风险。未涉及可确认风险且目标/预期清楚的操作可直接执行；覆盖已有值、公式、结构或其他已定义业务风险，应把实际对象、旧值/公式摘要、拟议效果、影响范围与风险说明给用户确认。确认前不启动相应写入。

确认收据绑定至少：当前用户、Thread/Session、当前有效版本与源文件 SHA-256、Session/文档 revision、目标范围、规范化预期 Effect、操作类别及需确认的业务风险。确认前执行时重新校验权限、当前文件哈希/版本、授权数据快照和范围。任一相关目标、Effect、文件版本或风险范围改变，旧确认失效，须重新向用户说明并确认。确认不解除 ACL、Record Rules、文件安全、资源预算、损坏格式或无法验证等约束。

实际影响可能只能在候选返回后完整得知。若候选超出已确认/声明范围，拒绝接受且不发布；原有效版本保留。不得以 `force_override` 或模型解释扩大确认。

### 4.3 自然语言完成声明边界

保留 Phase B v0.3 的三层语义：`execution_verified` 由本地 Validator 对已声明 Effect 给出；`coverage_declared` 是 Agent 对用户本轮要求的覆盖清单；`task_completed` 是 Agent 基于两者形成的用户反馈。`coverage_declared` 不能证明清单没有漏掉用户原话，因此 `task_completed` 不是独立自然语言语义证明。任何无法结构化、未覆盖或不确定要求必须明确告诉用户；不得在此类项存在时声称全部完成。

## 5. 工作簿版本、状态与多轮生命周期

### 5.1 版本链

有效版本按父子链演进：`V1 → V2 → V3 …`。V1 是首轮 M1 填充后通过适用本地验证的工作簿。后续每次编辑输入必须是 Session 当前有效的最高版本；禁止默默从上传模板或较早版本重新生成来冒充连续编辑。成功候选在完成适用验证和服务端并发校验前仍是 `candidate`，不成为下一轮输入。失败、未确认、待核查或被拒绝候选不得升级 last-valid。

每个已登记候选/版本 manifest 记录：

| 字段 | 语义 |
|---|---|
| `session_id`, `version_id`, `parent_version_id`, `version_no` | Session 内唯一身份及来源链；初始 V1 没有父编辑版本 |
| `input_attachment_id`, `input_sha256`, `output_attachment_id`, `output_sha256` | 实际输入/输出私有附件及真实字节哈希；候选失败也保留受控审计引用或失败摘要 |
| `user_message_id` | 关联用户原始指令，不重复存储不必要的提示全文 |
| `intent_effect_digest`, `confirmation_receipt_id` | 预期 Effect 和适用确认的指纹/引用；受保护的目标/值明细按最小必要原则留存 |
| `provider/model/request/response/tool/file ids` | 可获得的调用追踪、模型、远端资源引用；不可得的字段明确为空/unknown，不伪造 |
| `usage/cost estimate`, `started_at`, `finished_at`, `cleanup_state` | 资源审计、估算及远端清理状态；不把估算标为账单 |
| `validation_level`, `validation_report_digest`, `version_state`, `delivery_state` | 独立验证等级、报告、候选/有效/失败状态和附件交付事实 |

文件内容只放在受访问控制的 Odoo attachment/受控存储。Session 版本号、Proposal revision、Provider response id 各有不同含义，不能互相替代。并发提交使用当前 Session/文档 revision；只有仍匹配父版本的候选可提交。

### 5.2 状态

版本记录至少区分：`candidate_requested`、`awaiting_confirmation`、`provider_running`、`candidate_received`、`verifying`、`verified`、`partially_verified`、`rejected`、`failed`、`accepted_current`、`superseded`、`finalized`。Session 的交互状态与单个版本状态分开；状态只能由服务端受控迁移，并保留当前 last-valid 引用。该枚举是本 TDD 设计提案，实施前由 CC 核实既有模型可复用字段/状态；不得因复用困难而静默更改语义。

只有 `verified` 可被接受为 `accepted_current` 并用于后续编辑/Finalize。`partially_verified` 与 `failed/rejected` 均不得覆盖 last-valid 或触发正式发布；文件是否以显著标注的隔离诊断附件提供给用户属待审批产品决策，默认不作为正常 Preview 发布。

### 5.3 多轮修改与数据刷新

普通编辑按当前有效文件字节继续：V(n) 为唯一输入，输出验证成功后形成 V(n+1)。失败候选不成为输入，重试引用原 V(n)，但必须使用新的/可核实的请求标识与费用预算；不重复应用上一次成功版本。

刷新数据不创建本地 Excel 写操作。Data Tool 返回当前用户有权查询的 typed JSON 与快照信息；LLM 根据业务键/记录身份在当前工作簿中应用。若身份歧义、`full` 快照不完整、增量快照被错误理解为删除、或覆盖效果改变，澄清/确认后才能请求候选。刷新后的工作簿须作为新版本通过同一候选验证及提交流程。

### 5.4 Finalize 与恢复

Finalize 只引用明确的 `accepted_current` 版本及其 SHA-256、有效确认和独立验证报告。正式文件字节必须与被接受版本一致（允许有经明确、可验证且不改变内容的封装差异时，必须预先定义并核验；默认要求哈希一致）。正式附件创建/消息关联/交付状态分别记录。附件发布失败时保留有效 Preview 和版本，可对同一版本安全重试发布；不得重跑编辑或用旧版冒充当前版。

恢复历史版本是一个显式版本切换：重新检查 Thread/Session 所有权、附件权限、当前用户权限、来源及哈希；把选定版本标为新的当前指针或生成明确的恢复版本；任何旧确认不随恢复自动复活，需按当前文件与 Effect 重新验证/确认。历史版本只读，不覆盖删除。

## 6. 本地独立验证与发布门禁

### 6.1 验证输入与验证项

Validator 接收不可变输入版本字节、候选真实字节、当前结构基线、声明的目标/Effect、有效确认范围（如需）和格式支持策略。先验证字节来源、SHA、非空/大小、ZIP/OOXML 可读性、恶意或超限结构；再独立重开候选，并比较：

- 工作表名称、次序、可见性、维度及适用的合并区域/命名区域/表格/数据验证/条件格式等结构；
- 单元格值、数据类型（区分 `None`、空文本、`False`、0/0.0、日期）、公式文本及引用；
- 样式、数字格式及非目标区域差异；
- 声明/确认的目标是否实际达到，是否发生声明外变化；
- 文件 SHA 与父版本、Session revision、provider call/artifact lineage 的一致性。

结构超出已验证支持范围、无法可靠计算影响范围或独立解析失败时不得默默忽略；按能力矩阵阻断或部分验证。公式文本/引用正确不代表公式已计算/重算。公式计算只可在确有已批准计算引擎、与目标文件内容等价并完成独立验证时单独报告；否则记 `UNVERIFIED`。

### 6.2 结果等级与交付规则

| 等级 | 判定 | 版本/交付规则 |
|---|---|---|
| `VERIFIED` | 候选可安全重开；声明效果逐项回读匹配；目标范围/确认范围匹配；受保护非目标内容无未解释变化；版本来源一致 | 可进入 `accepted_current`，生成 Preview；Finalize 仍需其业务确认及正式附件链成功 |
| `PARTIALLY_VERIFIED` | 文件可打开且部分明确断言通过，但至少一项结构/Effect/非目标变化不能确定或不在验证能力内 | 不升级 last-valid，不允许 Finalize/完成声明；默认不作为普通 Preview 附件发布。报告明确未验证项，等待产品决定是否需诊断性隔离展示 |
| `FAILED` | 字节/ZIP/解析损坏、明确目标错误、确认外副作用、来源冲突、越权、资源/安全规则失败或可证明的非目标破坏 | 拒绝候选、隔离/按留存规则处置，不作为附件交付；last-valid 保持不变 |

Validator 判定的是结构化声明效果和已实现保护清单，不是全部自然语言意图。LLM 声明/自检不能替代本地独立回读。

### 6.3 预览、正式文件与用户结果

状态分开记录：操作结果（如完成/需确认/需澄清/阻断/失败）、验证等级、artifact 阶段（预览/正式）、交付状态（未发布/附件已关联/浏览器可下载/失败/待重试）。原生工具消息返回 `completed` 只说明工具函数结束，不代表 Office 任务完成。用户只能在工具结果和附件状态确证后收到相应自然语言反馈；模型 Provider 后续超时不得回写或抹除已持久化的成功产物，恢复时从 Session 读取实际状态而非盲目重放。

## 7. 安全与故障处理

| 故障 | 本地行为 | 是否重试/是否能发布 |
|---|---|---|
| Provider/API `APIConnectionError`，是否受理不明 | 标记 `outcome=failed/indeterminate` 或专门待核查内部状态；保留 V(n)，记录尝试及预算消耗；查询可用远端状态/幂等引用 | 禁止盲目自动重发；有可验证未执行/幂等条件且预算允许才重试；无候选不得发布 |
| Provider 明确超时 | 先核查已持久化 Response/文件引用与当前版本。若产物可取得则进入候选验证；否则保留 last-valid | Provider 请求幂等性未验证前不自动重放；不伪造失败文件 |
| 无真实 XLSX、下载失败、零字节/不合法 XLSX | 保留错误类别、Response/Tool ID（如有），拒绝候选 | 不升级、不交付；按安全条件可重试 |
| 非目标变化/预期 Effect 未实现 | 记录差异；拒绝候选；保留前版 | 不接受，不 Finalize；修改意图或确认范围后重新走流程 |
| 权限撤销、Record Rule 不通过、附件无权 | 当前用户权限下拒绝并最小化披露 | 确认不可绕过；不调用远端/不发布 |
| 确认失效/源版本冲突 | 重新计算意图/Effect/风险并请求新确认；并发旧候选作废 | 不扩大旧确认，不提交旧父版本候选 |
| 资源/预算超限或外部处理政策不满足 | 请求前阻断；若在运行中超时则按候选/费用未知处理 | 不超预算继续、不转模型；失败候选不得发布 |
| 远端容器/文件清理失败 | 记录 `cleanup_pending`、远端 ID 和安全重试状态；不写入密钥或业务文件正文日志 | 已通过的本地候选是否可继续由数据政策/留存门决定；不把清理失败伪装成已清理 |
| Odoo 附件保存/消息关联失败 | 保持已验证本地候选及 Preview 状态；将交付标为失败/待重试 | 对相同已验证字节幂等重试关联，不重跑 Provider 编辑 |

日志仅保存最小必要元数据：Session/version/request IDs、错误类别、时间、耗时、usage/cost 状态、SHA、验证结论及清理状态。Prompt、响应原文、业务数据和访问令牌遵守既有数据最小化策略；必要审计内容以受访问控制的消息/附件引用保存。

## 8. 公开接口与数据/状态流

### 8.1 逻辑接口（设计契约，不是现有已实现 API）

| 入口 | 输入 | 输出与门禁 |
|---|---|---|
| `initial_fill(thread, source_attachment, user_intent)` | 用户当前权限、模板、首轮填充意图 | 使用既有 Mapping→M1→独立回读；成功生成 V1 Preview，否则保留原文件/明确失败 |
| `get_authorized_data(thread/session, query_spec)` | 模型/域/筛选/所需字段及分页语义；由工具契约限制并由 ORM 再验证 | typed JSON snapshot、稳定身份、query scope/time、pagination/completeness、来源 fingerprint；不含 Excel 坐标或写入命令 |
| `request_edit(session, current_version, user_message, expected_effect)` | 当前 Session/版本/哈希、用户消息、效果声明 | outcome 与确认/澄清结果；只在门禁通过后创建 Provider 请求 |
| `execute_edit(approved_request)` | 已核验父版本、有效确认/风险评估、预算和 Provider 配置 | Provider 调用收据及真实候选字节引用；不是接受或完成结果 |
| `verify_and_accept(candidate, parent_version, expected_effect)` | 父/候选文件、版本及确认快照 | 验证等级、差异摘要；只有 VERIFIED 可原子成为 current |
| `finalize(current_version, confirmation)` | accepted version、当前用户确认 | 正式 attachment/message/delivery 收据；必须与被确认字节一致 |
| `restore_version(session, version_id)` | 用户可访问的历史版本引用 | 权限/哈希复核后新的 current 指针或恢复版本；旧确认失效 |

工具面向 Agent 的外层字段应兼容现有 M2 工具，但语义以服务端事实为准，最少包含结果类别、版本标识、验证等级、artifact 阶段、交付状态、确认/澄清对象或可理解错误摘要及诊断引用。是否需要新增持久字段需在实施 CC 先核查现有 `status`、`operation_status`、`artifact_state`、`delivery_state` 与附件元数据；不得仅为名称统一而造第二套状态框架。

### 8.2 Outcome 语义

| Outcome | 服务端条件 |
|---|---|
| `completed` | 本地独立验证为 VERIFIED，声明目标满足且版本提交成功。`artifact_stage` 另外标明仅预览或正式文件；`delivery_state` 另外标明附件/下载事实 |
| `confirmation_required` | 目标和 Effect 范围明确，存在可确认业务风险，尚未执行风险写入 |
| `clarification_required` | 目标、记录身份、意图、范围或必要参数无法唯一确定 |
| `blocked` | ACL/Record Rules、安全、隐私、格式/资源预算或不可绕过技术边界不允许继续 |
| `failed` | 执行失败或完成状态不能可靠确认；last-valid 状态不变 |

Agent 将这些结果翻译为清楚的用户语言，不得把诊断码原样作为产品答案，也不得由自由文本提升服务端 Outcome。

## 9. 实施模块影响（供后续计划使用）

以下是评审后可能涉及的边界，不是已批准文件修改清单或编码任务：

| 模块/职责 | 未来影响 |
|---|---|
| `office_engine_m2` Thread/Orchestrator/工具服务 | 分离 initial fill、Data Tool、后续编辑请求、确认、版本恢复与真实结果传播；维持 ORM 访问和当前用户隔离 |
| `llm_openai` Provider 层 | 添加独立 Responses Adapter、文件传输/输出取得、usage/error 归一化；保持 Chat Completions 路径兼容 |
| `office_core` / M1 | 保留初始 Mapping 写入、格式/资源/基础文件安全边界；不为后续开放式编辑添加新 DSL。只提供本地候选解析/格式化验证所需的受控接口，是否可复用现有 validator 须由实现前审计确认 |
| M2 Session/数据模型 | 增加或复用文档版本清单、确认和交付元数据；先检查现有 ORM 字段是否足够，避免重复状态模型 |
| 附件/聊天层 | 候选/Preview/Finalize 私有绑定 Thread 与 Session；根据真实附件机制关联消息，分别记录生成、关联和下载状态 |
| TV/evidence | 延续原 TV 历史，新增门禁、预算完整性、单轮、多轮、复杂结构、刷新、集成、交付和失败恢复证据 |

## 10. 测试与验收要求（仅定义，不表示已通过）

| 测试层 | 必需覆盖 | 验收证据 |
|---|---|---|
| Provider Adapter 合约 | Chat Completions 不回归；Responses 请求/文件输入与输出；usage/request IDs；超时/连接错误；隐式重试关闭；预算门；远端清理和脱敏日志 | SDK/Provider 实际调用记录、输入输出哈希、资源/费用预算、重试/清理记录 |
| 初始填充回归 | 原模板映射、当前 ORM ACL、M1 初始文件生成、动态行/公式适用规则、Preview 与附件 | TransactionCase/模块测试与实际回读；不因新路线重写 M1 |
| 单轮 LLM 编辑 | 当前 V1 输入、修改值/清空/格式/结构操作；覆盖确认；无确认不写；真实文件字节和目标/非目标 diff | Responses/Tool IDs、用户确认范围、实际下载候选 SHA、独立回读。Phase 1B 重跑必须补全预算重试余量后再执行 |
| 多轮连续编辑 | V1→V2→V3→V4 基于前一有效文件；前轮修改保留；每轮失败不污染；稳定排序/结构操作后目标语义；重复请求不重复效果 | 每轮父/子 SHA、Provider 执行记录、验证 diff、状态和重试轨迹；不能用从 V1 重新生成冒充 |
| 保真/结构 | 多工作表、类型/空值/零/False、公式文本及引用、样式、格式、合并、隐藏、表格、命名范围、条件格式、数据验证等能力矩阵 | 独立 OOXML/XLSX 回读及受保护结构差异；公式重算单独的实际计算引擎证据，否则仅报告文本/引用 |
| 数据刷新 | ORM ACL/Record Rules、full/incremental、分页完整性、身份/业务键、类型和空值；返回 JSON 无坐标/编辑动作；LLM 将快照应用到当前 Vn 且保留既有修改 | 当前用户真实 Odoo 集成记录、JSON schema/来源/快照指纹、Vn→Vn+1 文件 diff；无业务写入 |
| Confirmation Gate | 目标/预期 Effect 绑定；确认前不调用编辑；确认后重验权限、版本、范围；Effect 改变失效；无关变化按冻结指纹契约判定 | 确认前后参数、文件哈希、预期/实际 Effect 和不匹配的拒绝结果 |
| Validator/发布 | VERIFIED/PARTIAL/FAILED 准确分类；未通过不升级 current、不 Finalize；附件字节与接受版本一致；Thread 消息关联及真实下载 | 文件/附件/message/thread ID、哈希、验证报告、浏览器下载字节独立读取 |
| 恢复与 Provider 超时 | Provider 响应后 Agent 超时；附件关联失败；版本冲突；连接状态不明；资源清理失败；安全重试幂等 | 逐步状态、last-valid SHA、不重复编辑/附件的证据和最终恢复下载 |

真实 Provider/Browser 端到端、Odoo TransactionCase、纯 Python 验证和静态检查分开报告。APIConnectionError 只证明调用路径受阻；不得降格断言把连接失败转写为模型能力失败或测试 PASS。

## 11. 旧 TDD 差异与上游变更清单

### 11.1 与 V1.0.0 / V1.1.0 的差异

| 主题 | V1.x 冻结设计 | V2.0.0 评审稿 | 处置 |
|---|---|---|---|
| 文件编辑责任 | M2 产出 Mapping Proposal，服务端编译并调用 M1 写 Excel；AI 不直接读写文件/执行代码 | M1 只负责首轮填充；首轮后由 LLM 驱动 Responses + Code Interpreter 编辑当前 XLSX；Odoo 下载验证和接受 | 路线替换；需经 SRS 正式变更及本 TDD 冻结后实施 |
| 多轮基线 | 完整 Proposal 基于原始模板/授权数据重编译 | 每次后续编辑基于当前 accepted version；新文件成为下一输入前须本地验证 | 版本基线改变；既有 Proposal 修订历史仍服务首轮映射，不冒充文件内容版本 |
| Data Tool | Retriever 给 Mapping 提供字段值/授权样例 | 首轮继续供初始 Mapping；之后 refresh 返回带身份与完整性信息 JSON，由 LLM 应用到当前文件 | Data Tool 不定位 Excel 坐标、不执行后续 Excel 写入 |
| 预览/确认/正式交付 | Proposal revision/数据指纹/预览绑定确认，再由 M1 渲染正式文件 | 文件 version/hash/目标/预期 Effect/确认收据绑定；Validator 通过后接受，Finalize/交付独立记录 | 保留用户决策权和 M1 初始路径；需适配后续文件版本 |
| Validator | M1 `office_verify` 验证本地生成候选 | 本地 Validator 独立验证 Provider 返回的原始 XLSX、目标与非目标差异、lineage | 保留当前实现审计；格式覆盖能力必须 TV，不假定已有 |
| Provider | OpenAI Chat Completions 为普通对话和映射建议 | 保留普通聊天；新 Responses Adapter 专用于受控 XLSX 文件编辑 | 并行新增，不更改普通聊天契约 |

V2.0.0 不废止旧冻结文档。若本版批准，需建立正式的 TDD 修订关系，说明 V1.x 中哪些章节仍然适用、哪些被新版本明确取代；不得依靠“最新版覆盖旧版”而丢失历史审计。

### 11.2 SRS、Implementation Plan 和 CC 后续调整

| 基线 | 影响建议（本轮不修改） |
|---|---|
| SRS M2 V1.0.0 / V1.1.0 Frozen | 首轮数据填充和连续修改仍是原产品目标；需提正式变更，解除“AI 不读写/不执行代码、仅 Proposal”的实施限制，定义受控编辑、数据政策、确认/独立验证与不支持范围。未完成前不得按本 TDD 进入实现 |
| DDD | 当前 N/A 决议保留；不因为增加 Provider Adapter 自动新增 DDD |
| Implementation Plan V1.0.0 Frozen | 需另起版本化影响修订：重排 CC 依赖与验收门，保留已完成基础设施；把 Candidate B TV 未完成能力作为前置/阶段验收；明确 Schema/会话迁移和回滚；本 TDD 不修改该计划 |
| State-continuity Implementation Plan V0.2 | 草案已标为架构影响待审；需在后续计划修订时逐项决定 Proposal Expression/patch 哪些保留在首轮、哪些缩窄/延期；不据此继续实现开放式后续编辑 DSL |
| CC-M2-B-01 / CC-01 | 保持既有审计范围/结论，不重开、不据架构路线抹除 OPEN/UNVERIFIED |
| CC-M2-002 Provider Usage | 未来评估 Chat Completions 与 Responses usage、文件/容器成本、预算门和数据最小化的影响；不修改现有 CC |
| CC-M2-003 Mapping Session | 评估 session/version artifact lineage、消息引用、乐观并发、私有附件及恢复；首轮 Proposal revision 与后续 workbook revision 分离 |
| CC-M2-004 Owl Mapping Card | 依据现有职责决定保留/缩窄或结束；新路线仍以原生 Thread/附件交互为主，不凭 TDD 自行删除生产 UI |
| CC-M2-005 AI→M1 / Dynamic Mapping | 保留首轮 AI→Mapping→M1 初始填充；后续编辑不能再经 M1 Mapping 写入。其验收边界需拆分首轮与后续文件版本流 |
| CC-M2-006 Private Skill | 需评估 Skill 是首轮映射复用、编辑偏好还是两者；未经变更批准不得将业务内容/工作簿自动上传或改变权限范围 |
| 后续新增/修订 CC | 候选主题：Responses Adapter；版本/确认/本地 Validator；Data Tool JSON refresh；Session/附件/Finalize；多轮与失败恢复。仅用于计划修订建议，不在本轮创建/授权 |

## 12. 风险、回退及人工待决事项

### 12.1 主要风险

1. **规范冲突：** SRS 冻结条款与文件编辑路线冲突，构成实施阻断，不能只靠 TDD 批准消除。
2. **TV 不完整：** Phase 1B–1D 因调用连接异常未得到 Response/候选文件，费用门控也存在报告记录的重试预留偏差。须先制定合规预算和运行门，再重新验证。
3. **远端执行及数据留存：** 真实 Odoo 业务数据能否发送到 Provider、适用数据驻留/留存和容器网络边界需要负责人/安全策略明确；合成 TV 不代表真实数据授权。
4. **格式覆盖：** 能打开 XLSX 不代表保留所有 OOXML 特性；须定义可支持/部分验证/拒绝矩阵。
5. **效果比对：** 大工作簿的全量值/样式/结构 diff 有时间和内存成本；应量化边界，不能将未知结构默认为无变化。
6. **语义遗漏：** 本地只能确定性验证 Agent 声明的效果，不证明自然语言被完整理解。用户反馈应明确这一边界。
7. **工具/远端超时：** 请求可能在客户端错误前已执行；自动重试可能重复编辑/耗费预算，需可靠 request lineage 和恢复测试。

### 12.2 回退边界

| 状态 | 允许的回退 |
|---|---|
| 未启用 Responses 新入口 | 可关闭新路由，已有 Chat Completions 和首轮 M1 填充继续使用 |
| 新路由已产生候选但尚未验证/接受 | 丢弃或隔离候选；current 仍指向最后一个已接受版本 |
| 新版本已验证接受但尚未交付 | 通过受控版本恢复显式切回先前有效版本；不直接改写/删除历史链 |
| 已生成正式附件/已向用户交付 | 不能靠关闭 feature flag 撤销已交付结果；需保留审计并按现有业务撤回/替换流程处理 |
| Responses 请求状态不明或 Provider 未清理远端数据 | 关闭新请求入口并阻止盲目重试；保留状态与清理待办。关闭入口不等于远端资源已删除 |
| 数据库 schema/版本记录已升级 | 关闭新入口只是路由回退；schema 回退需独立兼容性/备份/迁移计划，不能删除已形成 lineage 或降低访问控制 |

**关闭新入口不等于完整回退。** 不允许通过回滚文件版本、删除审计或将已编辑 Workbook 强行重新解释成旧 Proposal 来实现表面回退。

### 12.3 待人工决定

1. 正式 SRS 变更应如何限定 Responses/Code Interpreter 的“受控文件编辑”、外部数据政策和不可支持内容？
2. 哪些真实 Odoo 字段/业务数据允许上传 Provider？哪些模型/公司/文件类别禁止远端处理？
3. Candidate B 的容器外联网、最大文件大小/时长/费用、远端留存/删除时限以及费用归属门槛是什么？
4. `PARTIALLY_VERIFIED` 候选是否允许作为明确标记的隔离诊断附件展示？当前设计默认不成为普通预览/正式版本。
5. 哪些结构/公式/图表/宏/外部连接等列入第一版支持矩阵，哪些一律阻断？公式计算若需要，采用何种已批准计算环境？
6. 版本附件和 effect 摘要的保留期限、删除/撤回、用户可见历史及跨公司隔离规则需由安全/产品负责人确认。
7. Provider Adapter 是否在实现范围内只支持 OpenAI Responses，还是需提前定义通用 Adapter 接口？本版只指定现有 OpenAI 路线，不推断其他 Provider 能力。

## 13. 本稿明确不实施

- 不运行 TV、不调用 Provider、不操作 Odoo 服务/数据库/真实附件。
- 不修改 SRS、Implementation Plan、CC、代码、测试、配置或数据。
- 不在 Odoo 进程执行 LLM 生成代码，不启用 Candidate C。
- 不移除现有 Chat Completions，不把已验证的简单单轮 TV 扩大解释为完整能力。
- 不创建任意代码/Excel DSL、不新增 DAG、事件总线或通用语义理解引擎。
- 不将 `execution_verified` 或 Agent 的 `coverage_declared` 误称为独立自然语言语义证明。

## 14. 评审完成条件

本稿供人工评审；冻结前至少应裁定 §12.3 的外部数据/保留门、部分验证发布策略、第一版文件结构支持范围及 TDD/SRS 变更顺序。评审批准不自动构成编码、部署、Provider 调用或真实业务数据外发授权。

| 版本 | 日期 | 状态 | 说明 |
|---|---|---|---|
| V2.0.0 | 2026-11-06 | DRAFT — AUTHORIZED FOR REVIEW — NOT AUTHORIZED FOR IMPLEMENTATION | 经用户授权形成新路线 TDD 评审稿；保留 V1.0.0/V1.1.0 及动态行补充历史版本；未执行代码/Provider/服务操作 |
