# CC-M2-CB-09 — Fileless Office Generation

## 文档信息

| 项目 | 内容 |
|---|---|
| 契约编号 | CC-M2-CB-09 — Fileless Office Generation |
| 版本 | v0.1 |
| 状态 | **DRAFT — NOT AUTHORIZED** |
| 项目 | Odoo 18 CE / Office Engine M2 / Route B |
| 设计基线 | Frozen TDD V2.1.0; Route B ADR v1.0; CC-M2-CB-07 CLOSED — UAT PASSED; CC-M2-CB-08 APPROVED / CLOSED |
| 需求基线 | Frozen SRS V1.1.0；Route B 与 SRS 的规范对齐仍按 TDD V2.1.0 §0.3 处理 |
| 实施计划 | Frozen Implementation Plan V2.0.1 and approved V2.0.2 CB-07 amendment |
| 本轮权限 | 只读审查与契约起草；不授权编码、测试、Provider 请求、服务操作或基线修改 |

> 本契约草案只定义“没有上传文件或模板时创建 XLSX，并在 Odoo 中交付及继续编辑”的最小能力。它不修改或覆盖任何冻结基线，也不构成实施、真实 Provider 调用、数据外发或生产发布授权。

## 1. Contract Goal

让用户在 Odoo Office Thread 中仅用自然语言创建 XLSX，无需先上传文件或模板。用户可选择让 Agent 通过现有 `odoo_record_retriever` 读取当前用户有权访问的数据。Route B 模型负责工作簿内容和结构的生产；Odoo 负责用户/Thread 权限、外发授权、文件安全与完整性、版本登记、交付和后续版本来源。

创建成功后，用户应能从当前 Thread 取得 XLSX，并可在同一 Thread 继续用自然语言修改该文件。不得要求用户先建立空白模板、Mapping、样式原型行或固定坐标。

## 2. Frozen Baseline 与实际能力

以下结论依据冻结文档及本工作区当前源码。当前工作区存在未提交的 Route B 代码、测试和证据改动；此草案不将 dirty worktree 描述为干净发布基线，也不把未冻结的 Amendment 当作权威设计。

| 能力 | 当前状态 | 依据及 CC-09 影响 |
|---|---|---|
| Route B 内容生产 | 已有 | Responses API + Hosted Code Interpreter 已用于真实 XLSX 编辑；不证明无输入文件的创建链已经可用。 |
| SRS 对齐 | 未完成 | Frozen SRS V1.1.0 保留 Mapping/M1 交互基线；Frozen TDD V2.1.0 §0.3 已将 Route B 正式规范对齐列为待完成事项。无源文件创建超出现有 SRS/TDD 明确输入范围，须在实施前走版本化变更。 |
| 唯一 `office` Tool | 已有 | `office_mapping_tools.py` 当前公开 `status/edit/accept/reject/finalize`。Agent 仍通过一个 Office Tool 进入生命周期。 |
| 初次编辑输入解析 | 已有但要求文件 | `edit_orchestrator.py::_resolve_edit_source` 选择已接受 Current 或 Thread 最新上传；无上传且无 Current 时会失败。 |
| Responses 文件输入 | 已有但要求文件 | `responses_adapter.py::ResponsesAdapter.execute` 要求 `input_xlsx: bytes`，并按输入文件执行校验及请求。没有无源创建参数/分支。 |
| Session 源文件绑定 | 已有但要求文件 | `office.mapping.session.source_attachment_id` 与 `source_message_id` 为必需绑定；现有创建服务验证并登记源附件。 |
| 初始版本登记 | 已有但要求文件并须 Accept | `register_initial_candidate` 从 Session 源附件读取非空输入字节并绑定输入 SHA；首个 Candidate 必须经过现有接受流程才登记 V1/Current。 |
| Candidate 验证 | 已有 | 当前 Validator 将输入附件、Candidate 输出附件、SHA、Session/父版本关系绑定；尚未证明对没有输入附件的创建结果能签发权威 Receipt。 |
| Accept / Current / Finalize | 已有 | Version Service 负责受控 Candidate 决定与版本指针；Finalize 只交付已接受的 Current 并复用附件/消息服务。 |
| Retriever | 已有 | 独立 `odoo_record_retriever` 按当前 Odoo 用户权限只读取数；Office 不应复制 ORM 查询。 |
| 无源创建后的后续编辑 | 未实现/未证明 | Current 解析当前依赖 Thread 上传及绑定 Session；必须证明新建版本能成为后续 `edit` 的唯一字节来源，而不伪造上传。 |
| OpenAI API 无文件输入生成文件 | 未验证 | 本地 Adapter 不支持该调用形态；本轮没有调用 Provider，不能据此声称 API 或 Hosted Code Interpreter 不支持，也不能声称已验证。 |

相关实现位置：

- `mymodules/office_engine_m2/models/office_mapping_tools.py`：唯一 `office` Tool schema 与 facade。
- `mymodules/office_engine_m2/services/edit_orchestrator.py`：服务端来源解析、编辑调度、Accept/Reject/Finalize 路由和 Provider gate。
- `mymodules/odoo-llm/llm_openai/services/responses_adapter.py`：Responses XLSX 输入/输出。
- `mymodules/office_engine_m2/models/office_mapping_session.py`：Session 与源附件绑定。
- `mymodules/office_engine_m2/services/candidate_validator.py`、`mymodules/office_verify/`：Candidate 与文件验证。
- `mymodules/office_engine_m2/services/workbook_version_service.py`：版本登记、接受、Current/Last Valid 与 Finalize。
- `mymodules/odoo-llm/llm_tool/models/llm_tool_record_retriever.py`：现有只读 Retriever。

## 3. In Scope

1. 通过现有单一 `office` Tool 支持无源文件创建 XLSX；不增加公开 Office Tool。
2. LLM + Responses API + Hosted Code Interpreter 负责创建工作簿内容；本地服务不得通过模板、mapping、`repeat_rows`、单元格 DSL 或业务专用代码决定工作簿内容。
3. 需要 Odoo 数据时，Agent 使用现有 `odoo_record_retriever`，不得复制查询实现、提高权限或修改业务记录。
4. 按现有 Odoo 身份、外发授权、文件安全与完整性能力验证真实输出，并登记为可交付、可继续编辑的版本。
5. 在 Odoo Thread 交付文件；同一 Thread 后续编辑必须以该版本实际附件字节及 SHA 为输入，继续使用现有 Candidate、Accept/Reject、Current、Finalize 和交付路径，但遵循 §4 中经负责人裁定并完成上游修订后的创建语义。
6. 保持 M1 上传、Mapping、RenderBridge、附件、普通 Chat Completions 及现有 Route B 文件编辑兼容。

## 4. Creation, Delivery and Version Semantics

### 4.1 入口

继续使用唯一公开 `office` Tool。建议在现有 `office` action schema 内增加语义明确的 `create` action；不另建 Tool。输入仅包含自然语言任务所需内容及必要的现有确认信息。Provider client、模型、输入/输出限制、用户身份、Thread、Session、版本号、SHA、Receipt 和授权标记均由可信服务端解析，不从 Agent 参数信任。

`create` 只用于当前 Thread 没有可作为编辑来源的上传工作簿、也没有 Accepted Current，且用户意图是新建工作簿的情形。存在可用 Current 时，继续调用现有 `edit`；若用户要求编辑但当前文件来源不可解析，返回澄清/阻断，不得将其静默改作新建。

若评审决定不增加 action，实施前必须给出在现有 `edit` schema 内无歧义地区分“新建”与“编辑”的最小契约；不能靠本地业务 NLP 猜测用户意图。

### 4.2 创建与 Odoo 数据读取

1. Agent 保留用户原始自然语言指令，并判断是否需要 Odoo 数据。没有数据请求时，直接将创建指令交给 `office`。
2. 需要业务数据时，Agent 先调用当前 Thread 已有的 `odoo_record_retriever`。Retriever 使用当前 Odoo 用户 ORM、ACL、字段权限、Record Rules 和公司边界，只返回获准数据；Office 不查询或修改业务记录。
3. 真实数据进入外部 Provider 前，须通过当时适用的外发授权。授权不满足、Provider dispatch 关闭或调用资源策略不可用时，在发送前阻断；用户确认业务内容不能解除权限、安全或数据外发限制。
4. 服务端向 Responses Adapter 提供创建指令和获准数据，不提供虚构的空白 XLSX、示例模板或伪造输入 SHA。Hosted Code Interpreter 产出实际 XLSX 文件字节。
5. Agent 的自然语言声明不能替代服务端取得的文件、验证事实或版本状态。

### 4.3 验证及直接交付建议

当前冻结 TDD 要求首次及后续 Candidate 均经显式用户 Accept 后才成为 Current；它没有文件less 来源，也没有允许绕过 Candidate/Accept 的直接创建路径。

本 CC 建议将**新文件创建**与**对现有 Current 的编辑**区分：用户明确发出新建并交付文件的请求后，若 Provider 返回有效 XLSX 且现有硬性文件安全、完整性、身份及外发检查通过，服务端可直接将输出登记为该 Session 的初始 V1/Current，并复用现有 Finalize/附件交付，不额外要求 Candidate 预览/Accept。此创建请求只授权产出新文档，不授权修改 Odoo 业务数据。`FAILED`、缺失/损坏文件、权限或外发 gate 失败均不得登记 Current 或交付；用户要求创建不构成对这些限制的豁免。

这是**建议语义，不是当前冻结设计已允许的行为**。实施前必须通过 TDD 和必要的计划版本化 Amendment 明确：直接创建路径是否构成初始版本的受控发布授权；验证为 `PARTIALLY_VERIFIED` 时是否可直接交付，以及如何标明未验证事项。未经该修订，按 Frozen TDD 现行显式 Accept 规则执行，不得实施本节的直接发布路径。

创建结果须有实际 XLSX 输出字节、输出 SHA、文件名/MIME、Thread/owner/company、创建指令、Provider 诊断信息（可取得时）、typed Validation Receipt、验证等级和交付引用。不存在的输入文件 ID/SHA 记为空且注明 fileless origin，不得伪造源附件、父版本或输入哈希。只有可确认为 XLSX 且通过既有技术硬约束的文件可交付；未知保真按现有验证等级如实披露，不新增业务语义验证器。

### 4.4 Version and subsequent edit

- 第一个真实生成文件成为该 Thread 的 V1；若 §4.3 的直接创建语义获批，则由服务端受控事务登记 V1、Current、Last Valid 和 Revision，并链接创建意图及输出附件。创建失败不得留下可被解析为 Current 的半成品。
- V1 必须能在同一 Thread 中由现有 `office(action="edit")` 解析为当前版本。后续 Provider 输入必须是 V1 的实际附件字节，输入 SHA 必须等于 V1 输出 SHA。
- V2 及后续编辑继续走现有 Candidate → 本地验证 → 用户 Accept/Reject；Accept 才推进 Current/Last Valid/Revision，Reject、Failed、Stale 不推进。创建例外不得被扩张为对现有文件编辑的自动接受。
- Session/Version 需准确表示无用户源上传的创建来源。可复用现有表和权限/状态机制；若当前必需字段或约束不能表达该事实，仅允许为 fileless origin 所需的最小可审计表示作版本化 schema/service 扩展，不建立第二套 Session、版本或附件系统。
- 初始创建和同版本 Finalize/Delivery 应幂等；重试不得产生重复 V1、重复 Current 或无故重复的正式附件。Finalize 继续交付与 Current SHA 一致的现有版本字节，不重新调用 Provider。

## 5. Trust and Safety Boundaries

- 用户/Thread 身份从 Odoo 认证上下文取得；不能接受 Agent/RPC 提供的 `user_id`、公司、权限或 trusted flag。
- Retriever 以当前用户权限读取数据；Office 仅消费同一任务已授权的结果，不用 `sudo()`、服务账号或另一查询路径扩大权限。
- Provider client/model/resource limits 从可信服务端配置装配。Agent 参数不得启用外发 dispatch、选择 Provider、提高限制或注入密钥。
- 现行外发授权、留存约束及 closed-by-default Provider gate 保持有效。CC-09 不新增数据分类、策略审批或留存管理系统。
- XLSX 文件完整性、安全及大小/资源限制复用现有机制；损坏或无法安全解析的文件不可交付/成为 Current。未知保真与已确认损坏分别按现有 PARTIAL/FAILED 语义处理。
- Candidate、Receipt、SHA、Current 指针和正式附件仅由受控服务端入口管理。除经批准的 fileless initial-create 语义外，生成、验证或模型声称完成均不能推进 Current。
- 用户是业务内容的最终判断者。需要确认的可确认业务风险应在外发/执行前按现行确认机制处理；确认不能解除权限、安全、文件完整性或外发授权限制。

## 6. Minimal Implementation Scope and File Whitelist

冻结后实施者先核对当前文件和接口；仅在以下范围内作能完成 fileless create 的最小修改：

| 文件/模块 | 允许修改范围 |
|---|---|
| `mymodules/office_engine_m2/models/office_mapping_tools.py` | 在单一 `office` schema/facade 中增加经批准的创建语义；保持其他 action 及 M1 工具兼容。 |
| `mymodules/office_engine_m2/services/edit_orchestrator.py` | 可信 Thread/Session 来源分流；fileless create 的 Provider 调度、失败保护及进入版本/交付服务；不得重构现有 edit 流程。 |
| `mymodules/odoo-llm/llm_openai/services/responses_adapter.py` | 在既有 Hosted Code Interpreter 适配器中支持无文件输入的创建请求及真实 XLSX 输出；保留普通 Chat Completions 和现有文件编辑接口。 |
| `mymodules/office_engine_m2/models/office_mapping_session.py` | 仅在必需时扩展受控 session 来源表示/创建服务，以准确表示 fileless origin；保留 ACL 和内部创建入口。 |
| `mymodules/office_engine_m2/services/workbook_version_service.py` | 仅扩展初始 V1 注册/幂等及受控发布语义；复用现有 Current/Last Valid/Revision、附件与 Finalize，不引入第二套版本系统。 |
| `mymodules/office_engine_m2/services/candidate_validator.py`、`mymodules/office_verify/` | 仅在现有验证契约不能处理无输入文件时补充 source-less initial artifact 的技术验证/Receipt 绑定；不新增内容或业务正确性规则。 |
| 相关 Agent 指引、测试及 manifest（仅确有必要时） | 更新 create/edit 调用说明和 CC-09 必要自动化断言；不新增公开 Tool，不改 Retriever 查询实现。 |
| `docs/implementation/IHR-M2-CB-09.md`、`ATR-M2-CB-09.md`、`HVR-M2-CB-09.md`、`FR-M2-CB-09.md`、`evidence/CB-M2-CB-09/` | 实施后保存分层执行记录，不覆盖 CC-07/08 历史证据。 |

需要超出白名单、修改 Odoo 官方模块、改动 M1 内容生成、建立本地 Excel 内容引擎或改变 Provider 策略时，停止并另提授权。测试夹具目录按实际 addon 约定细化；不为形式统一新增目录或框架。

## 7. Automated Tests / HVR

### 7.1 Automated tests

1. 单一 `office` Tool schema 接受 fileless create 请求；不增加第二个公开 Office Tool。
2. 无上传、无 Current 时，经获批创建路径可调用 Adapter；Adapter 未收到伪造 XLSX 输入，返回真实非空 XLSX 字节方可继续。
3. 适配器错误、超时/indeterminate、dispatch 关闭、外发权限不足、无输出/无效 XLSX 时，不创建可接受/Current 版本，不交付文件。
4. Retriever 数据使用当前用户权限；禁止业务记录写入；无可授权记录时不编造记录内容。
5. 初始版本登记与线程/用户/公司/意图/输出字节绑定，输出 SHA 可复核；幂等重试不重复建版本/附件。
6. 直接创建交付语义（如经上游批准）不能改变既有文件编辑的 Candidate/Accept/Reject 规则；`FAILED` 不可接受；`PARTIALLY_VERIFIED` 不得升等。
7. 创建后同 Thread `edit` 使用已登记 V1 的真实输出字节及相同 SHA 作为输入；V2 Accept 正常推进，Reject/失败/stale 保持 V1。
8. Finalize 与附件交付复用现有服务；下载 SHA 等于 Accepted Current SHA；重复交付幂等。
9. M1 上传、Mapping/RenderBridge、Retriever、Chat Completions 及 CC-07/08 相关回归按实际受影响范围运行并报告。

### 7.2 Odoo integration / HVR

**Fileless two-turn HVR（同一非生产 Odoo Thread）：**

1. 以普通用户自然语言请求创建一个 XLSX；Thread 中无先前上传工作簿或模板。
2. 使用 `odoo_record_retriever` 读取当前用户获准的合成或已单独授权测试数据（如果指令需要）；不修改 Odoo 业务记录。
3. 经获批的真实 Responses API + Hosted Code Interpreter 生成非空 XLSX。记录脱敏请求/Response/Tool/File ID、usage/时长（可得时）和文件 SHA；无法调用真实 Provider 时，本项为 BLOCKED/NOT RUN，不用 Mock 替代真实 HVR。
4. 以独立读取检查 XLSX 可打开、实际内容与测试数据相符、文件 SHA 与服务端版本附件相符；记录验证等级及未验证项。
5. 按 §4 已批准的直接交付或 Candidate/Accept 语义，检查 V1、Current、Last Valid、Revision、Session/Thread 绑定和 Discuss 附件下载。
6. 在同一 Thread 继续以自然语言修改刚创建的文件。证明第二轮使用 V1 实际字节（Round 2 input SHA = V1 output SHA），生成 V2，原有用户指定内容保留且新修改可独立回读。
7. 对 V2 执行现行 Accept/Reject。Accept 后当前版本推进；Reject 后 Current/Last Valid/Revision 保持。按用户要求 Finalize，下载文件并独立回读，SHA 与被交付 Accepted Current 一致。
8. 核实 Retriever 只读、无 Odoo 业务数据变化；不得用直接 ORM 写 Current/Candidate、Mock Provider、内部 service 调用或聊天回复替代真实 UI/Agent/Tool/Provider/下载证据。

Unit/Mock、TransactionCase、真实 Provider、Odoo UI、实际下载和独立 XLSX 回读分别记录。Automated User Simulation 可用于对应自动化层；若使用真实 Discuss UI，说明其自动化/真人属性。证据不得含密钥、cookie 或不必要的真实个人数据。

## 8. Acceptance Criteria

CC-09 可提交 `READY FOR FINAL ACCEPTANCE` 的条件：

1. 与 fileless creation 冲突的 TDD/Implementation Plan 条款已完成批准的版本化修订；直接创建或显式 Accept 的决策已在上游明确，不存在静默偏离。
2. 无上传、无模板时，真实用户可通过唯一 `office` Tool 触发 LLM 主导的 XLSX 创建；真实 Adapter 成功取得实际 XLSX 输出字节。
3. 需要 Odoo 数据时只通过现有 Retriever，保留 ACL/Record Rules/多公司/字段权限及只读语义；未经授权不向 Provider 发送数据。
4. 文件安全/完整性、版本归属、输出 SHA 和失败保护均通过自动化与 Odoo 集成测试；失败时没有虚假成功、Current 推进或错误交付。
5. 新建文件在服务端有真实、可继续编辑的 V1/Current 版本来源；同 Thread 第二轮确实以其输出 SHA 为输入，并正确完成 Accept/Reject。
6. 最终 Odoo Thread 附件可访问、可下载，独立回读内容正确，下载 SHA 与对应交付版本一致；重复操作遵守幂等性。
7. M1 和现有 Route B 未受影响的回归证据适用；测试数量、失败、错误、跳过、数据库/Provider/UI 层级及代码基线可核对。
8. IHR、ATR、HVR、FR 和 evidence index 完整；未执行项目标为 `NOT RUN`/`BLOCKED`，不得用组件 Mock 或 Provider 单测宣称 HVR PASS。

`Final Accepted` 由负责人决定。CC-09 关闭不构成生产 Provider 开启、真实业务数据外发或生产发布批准。

## 9. Failure and Stop Conditions

| 失败 | 处理 |
|---|---|
| 用户/Thread 权限、业务数据 ACL 或外发授权不通过 | 在 Provider 上传前阻断；不降权、不改用别的身份。 |
| Provider 未响应/结果不确定 | 记录 failed/indeterminate；不盲目重试，不登记 V1/Current，不交付。 |
| Provider 未返回真实 XLSX、XLSX 无效或安全检查失败 | 阻断版本登记和交付；不本地补造文件冒充模型结果。 |
| 初始版本提交、附件保存或 Thread 交付失败 | 维持一致状态；按现有事务/幂等恢复；不得留下虚假 Current 或成功消息。 |
| 后续版本父 SHA/Current/revision 不符 | 按现有 stale/并发规则拒绝；保留最后有效版本。 |
| 需要更改冻结 TDD、SRS、数据策略或计划以外的基线 | 停止依赖该改动的实施项，提交最小 Amendment 决策，不自行修改上游。 |

## 10. Dependencies, Risks and Owner Decisions

### 10.1 Dependencies

- TDD/Implementation Plan 的版本化范围修订及其负责人批准。
- 独立 CC-09 冻结与 Coding Authorization。
- 运行测试时的非生产 Odoo 数据库、服务、模块升级授权。
- 真实 Provider/Hosted Code Interpreter 测试授权、请求/费用/数据类别/留存边界；真实 Odoo 数据外发另须对应授权。开发授权不能自动开启 Provider dispatch。
- 既有 CC-07/08 实现及证据作为复用基线，不重做无关功能。

### 10.2 Owner Decisions Required Before Freeze

1. **首次无源创建的发布语义：**是否批准用户明确的“创建并交付”指令在技术硬验证通过后直接登记 V1/Current 并交付，不生成待 Accept 的 Candidate；还是沿用 TDD V2.1.0 对所有首次输出的 Candidate → 用户 Accept → V1 规则？这是与冻结 TDD 的实质冲突，不能由 CC 草案自行裁定。
2. **部分验证创建结果：**若创建文件技术硬约束通过但仍为 `PARTIALLY_VERIFIED`，是否允许同一直接交付规则，或保留用户先审阅/接受的要求？`FAILED` 始终不可绕过。
3. **Tool action 表达：**是否同意在现有 `office` Tool 内增加 `create` action（推荐，便于明确区分新建与编辑且不增加公开 Tool），或要求保持现有 action schema 并由 TDD amendment 明确无歧义的等价表达？
4. **上游需求与计划对齐：**确认无源文件创建是否纳入正式 SRS 范围，以及现有 Route B SRS 变更门如何收口；批准后另行修订 TDD §0.2、§2.1–2.2、§3.1、§4、§7、§11，并以最小 Implementation Plan Amendment 纳入本工作。CC-09 不授权直接编辑这些文件。

## 11. Evidence and Handoff

实施获批后按项目既有格式维护：

- `docs/implementation/IHR-M2-CB-09.md`：实际代码、模块和运行环境基线、实现范围及未决事项。
- `docs/implementation/ATR-M2-CB-09.md`：Unit/TransactionCase/回归测试命令、数量、结果与原始日志。
- `docs/implementation/HVR-M2-CB-09.md`：同 Thread fileless create → V1 → 第二轮 edit/Accept → Finalize/下载的真实 UI/Provider 证据。
- `docs/implementation/FR-M2-CB-09.md`：验收映射、PASS/FAIL/BLOCKED/NOT RUN 和负责人最终决定。
- `docs/implementation/evidence/CB-M2-CB-09/`：脱敏文件、SHA、版本快照和调用证据；仅保留获准测试数据。

分别标注 Contract/Mock、Odoo ORM、真实 Provider、Odoo UI、下载及独立回读层级。凡未经实际执行的结论必须标为 `NOT RUN` 或 `UNVERIFIED`，不从 CC-07/08 的既有 PASS 推导 fileless 创建已通过。

## 12. Change Record

| 版本 | 日期 | 状态 | 说明 |
|---|---|---|---|
| v0.1 | 2026-11-11 | **DRAFT — NOT AUTHORIZED** | 基于 Frozen TDD V2.1.0、Route B ADR、Implementation Plan、CC-07/08 与当前 Route B 源码起草。新增无上传文件创建 XLSX、Odoo 交付及后续编辑的最小契约；明确直接交付语义与冻结 Accept 规则冲突并列出负责人裁决项。 |
