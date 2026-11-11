# CC-M2-CB-09 — Fileless Office Generation

## 文档信息

| 项目 | 内容 |
|---|---|
| 契约编号 | CC-M2-CB-09 — Fileless Office Generation |
| 版本 | v0.2 |
| 状态 | **FROZEN — IMPLEMENTATION AUTHORIZED (CC-09 SCOPE WAIVER)** |
| 项目 | Odoo 18 CE / Office Engine M2 / Route B |
| 设计基线 | Frozen TDD V2.1.0; Route B ADR v1.0; CC-M2-CB-07 CLOSED — UAT PASSED; CC-M2-CB-08 APPROVED / CLOSED |
| 需求基线 | Frozen SRS V1.1.0；Route B 与 SRS 的规范对齐仍按 TDD V2.1.0 §0.3 处理 |
| 实施计划 | Frozen Implementation Plan V2.0.1 and approved V2.0.2 CB-07 amendment |
| 本轮权限 | 仅授权 CC-09 范围内编码及本地/Mock 自动化验证；不授权真实 Provider 请求、服务操作、模块升级、生产数据处理或基线修改 |

> 本契约定义“没有上传文件或模板时创建 XLSX，并在 Odoo 中交付及继续编辑”的最小能力。负责人已裁决：在现有单一 `office` Tool 中增加 `create` action；必要技术检查通过后，初始文件直接登记 V1/Current 并交付；`PARTIALLY_VERIFIED` 可以交付但须披露未验证范围。已有文件编辑仍保持 Candidate → Accept/Reject。

### 本批次上游对齐豁免

负责人明确指示“忽略 SRS、TDD、Plan 对齐，冻结 CC-09，进入实施”。因此上游对齐不再是 CC-09 编码的前置阻断项，本 CC 作为仅适用于 fileless generation 的范围授权和契约豁免。SRS、TDD、Implementation Plan 原文件保持不变；本豁免不表示其已与 CC-09 语义一致，也不扩展到其他 CC、真实业务数据外发、生产部署或生产发布。

## 1. Contract Goal

让用户在 Odoo Office Thread 中仅用自然语言创建 XLSX，无需先上传文件或模板。用户可选择让 Agent 通过现有 `odoo_record_retriever` 读取当前用户有权访问的数据。Route B 模型负责工作簿内容和结构的生产；Odoo 负责用户/Thread 权限、外发授权、文件安全与完整性、版本登记、交付和后续版本来源。

创建成功后，用户应能从当前 Thread 取得 XLSX，并可在同一 Thread 继续用自然语言修改该文件。不得要求用户先建立空白模板、Mapping、样式原型行或固定坐标。

## 2. Frozen Baseline 与实际能力

以下结论依据冻结文档及本工作区当前源码。当前工作区存在未提交的 Route B 代码、测试和证据改动；本契约不将 dirty worktree 描述为干净发布基线，也不把未冻结的 Amendment 当作权威设计。

| 能力 | 当前状态 | 依据及 CC-09 影响 |
|---|---|---|
| Route B 内容生产 | 已有 | Responses API + Hosted Code Interpreter 已用于真实 XLSX 编辑；不证明无输入文件的创建链已经可用。 |
| SRS/TDD 对齐 | 未完成；本 CC 已豁免 | Frozen SRS V1.1.0 与 Frozen TDD V2.1.0 未定义无源创建及直接登记 V1/Current。负责人明确豁免此项作为 CC-09 实施门槛；差异仍如实记录，上游文件不在本轮修改。 |
| 唯一 `office` Tool | 已有 | `office_mapping_tools.py` 当前公开 `status/edit/accept/reject/finalize`；v0.2 仅在同一 Tool 中增加 `create` action。 |
| 初次编辑输入解析 | 已有但要求文件 | `edit_orchestrator.py::_resolve_edit_source` 选择已接受 Current 或 Thread 最新上传；无上传且无 Current 时会失败。 |
| Responses 文件输入 | 已有但要求文件 | `responses_adapter.py::ResponsesAdapter.execute` 要求 `input_xlsx: bytes`，并按输入文件执行校验及请求。没有无源创建参数/分支。 |
| Session 源文件绑定 | 已有但要求文件 | `office.mapping.session.source_attachment_id` 与 `source_message_id` 为必需绑定；现有创建服务验证并登记源附件。 |
| 初始版本登记 | 已有但要求文件并须 Accept | `register_initial_candidate` 从 Session 源附件读取非空输入字节并绑定输入 SHA；当前实现没有直接创建 V1/Current 的无源登记入口。 |
| Candidate 验证 | 已有 | 当前 Validator 将输入附件、Candidate 输出附件、SHA、Session/父版本关系绑定；尚未证明对没有输入附件的创建结果能签发权威 Receipt。 |
| Accept / Current / Finalize | 已有 | Version Service 负责受控 Candidate 决定与版本指针；Finalize 只交付已接受的 Current 并复用附件/消息服务。 |
| Retriever | 已有 | 独立 `odoo_record_retriever` 按当前 Odoo 用户权限只读取数；Office 不应复制 ORM 查询。 |
| 无源创建后的后续编辑 | 未实现/未证明 | Current 解析当前依赖 Thread 上传及绑定 Session；必须使创建所得 V1 能成为后续 `edit` 的唯一字节来源，而不伪造上传。 |
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

继续使用唯一公开 `office` Tool，并增加 `action="create"`。它仅表示“按本条用户指令新建 XLSX”；不新增公开 Tool。输入包含原始用户任务及按现有确认契约所需的信息。Provider client、模型、资源限制、认证用户、Thread、版本号、SHA、Receipt 和授权标记均由可信服务端解析，不能由 Agent 参数指定或伪造。

`create` 只在当前 Thread 没有作为编辑来源的用户上传文件且没有可用 Current 时执行。存在 Current 时使用 `edit`；用户要求修改但当前来源不可解析时，应澄清/阻断，不得静默退化为新建。`create` 不接受文件、模板、用户声明的 input SHA、父版本或 Current 指针。

### 4.2 创建与 Odoo 数据读取

1. Agent 保留用户原始自然语言指令，并判断是否需要 Odoo 数据。没有数据请求时，直接将创建指令交给 `office`。
2. 需要业务数据时，Agent 先调用当前 Thread 已有的 `odoo_record_retriever`。Retriever 使用当前 Odoo 用户 ORM、ACL、字段权限、Record Rules 和公司边界，只返回获准数据；Office 不查询或修改业务记录。
3. 真实数据进入外部 Provider 前，须通过当时适用的外发授权。授权不满足、Provider dispatch 关闭或调用资源策略不可用时，在发送前阻断；用户确认业务内容不能解除权限、安全或数据外发限制。
4. 服务端向 Responses Adapter 提供创建指令和获准数据，不提供虚构的空白 XLSX、示例模板或伪造输入 SHA。Hosted Code Interpreter 产出实际 XLSX 文件字节。
5. Agent 的自然语言声明不能替代服务端取得的文件、验证事实或版本状态。

### 4.3 验证、V1 与直接交付

新建指令本身授权创建并交付一个新工作簿。Provider 返回非空 XLSX 后，服务端执行现有必要技术检查：输出字节/类型、XLSX 容器与安全边界、资源限制、当前用户/Thread 归属及外发 gate。检查结果为 `VERIFIED` 或 `PARTIALLY_VERIFIED` 时，服务端直接将真实输出登记为 V1/Current/Last Valid，并调用现有 Finalize/附件交付；不向用户呈现待审 Candidate，也不要求用户再执行 Accept。为保持 CB-02 typed Receipt 的受控绑定，允许在既有 Version 表中使用仅服务端可见的内部初始版本验证记录绑定实际输出字节和 Receipt；该记录不进入用户 Candidate 审阅流程。验证成功后由同一受控 create 服务直接提交为 V1/Current。该内部记录不代表用户接受过 Candidate，不得伪造 Accept 消息或接受事件。`PARTIALLY_VERIFIED` 可交付，回复和附件信息必须显示验证等级及具体未验证范围，不得称为完全验证或业务正确性已证明。`FAILED`、无文件、已确认损坏、权限/外发/安全硬约束失败均阻断登记和交付。

创建不是对既有文件的编辑，也不改变后续编辑规则：当前用户的下一轮修改仍生成 Candidate；只有通过既有受控 Accept 才推进 Current，Reject/失败/stale 不推进。创建动作不得伪造 `candidate_accepted` 事件、Accept 消息或用户已审阅文件的声明。版本记录须准确表示其来源为用户创建指令及直接发布结果；可复用现有版本表和状态，但若当前状态/Receipt 字段会错误表示发生过 Candidate Accept，实施时只增加区分直接创建来源所必需的最小审计元数据，不建立新状态机。

Validator 对无输入文件的创建结果，只执行现有确定性文件安全、完整性及 Receipt 可信绑定所需的检查；不要求比较不存在的源文件，不新增内容语义校验。Receipt 绑定内部验证记录/最终 V1、创建请求/用户消息、Thread/Session、实际输出附件字节 SHA、Validator policy/version、报告及结果；输入附件、输入 SHA 和父版本均为明确的空值/无父来源，不制造占位记录。`PARTIALLY_VERIFIED` 的披露不要求用户再确认，但其未知项必须随交付记录。

### 4.4 Version and subsequent edit

- 第一个真实生成文件由服务端受控入口直接登记为该 Thread 的 V1、Current 和 Last Valid，初始 Document Revision 为 1；登记记录链接创建用户指令及实际输出附件。创建失败不得留下可解析为 Current 的半成品。
- V1 必须能在同一 Thread 中由 `office(action="edit")` 解析为当前版本。后续 Provider 输入必须是 V1 的实际附件字节，输入 SHA 必须等于 V1 输出 SHA。
- V2 及后续编辑继续走现有 Candidate → 本地验证 → 用户 Accept/Reject；Accept 才推进 Current/Last Valid/Revision，Reject、Failed、Stale 不推进。创建例外不得被扩张为对现有文件编辑的自动接受。
- Session/Version 需准确表示无用户源上传的创建来源。不得把生成结果伪装成输入附件；输入附件、input SHA 和 parent version 保持空/无。若现有必需字段或验证约束无法表达该事实，仅允许作 fileless origin 所必需的最小 schema/service 扩展，不建立第二套 Session、版本或附件系统。
- 后续编辑解析须以该 Session 的 Current 为准，不得要求原始用户上传作为查找前提。V1 输出附件保存在现有私有附件机制中，且后续编辑读取其真实字节。
- 初始创建和同版本交付应幂等；重试不得产生重复 V1、Current 或无故重复的正式附件。Finalize 继续交付与 Current SHA 一致的版本字节，不重新调用 Provider。

## 5. Trust and Safety Boundaries

- 用户/Thread 身份从 Odoo 认证上下文取得；不能接受 Agent/RPC 提供的 `user_id`、公司、权限或 trusted flag。
- Retriever 以当前用户权限读取数据；Office 仅消费同一任务已授权的结果，不用 `sudo()`、服务账号或另一查询路径扩大权限。
- Provider client/model/resource limits 从可信服务端配置装配。Agent 参数不得启用外发 dispatch、选择 Provider、提高限制或注入密钥。
- 现行外发授权、留存约束及 closed-by-default Provider gate 保持有效。CC-09 不新增数据分类、策略审批或留存管理系统。
- XLSX 文件完整性、安全及大小/资源限制复用现有机制；损坏或无法安全解析的文件不可交付/成为 Current。未知保真与已确认损坏分别按现有 PARTIAL/FAILED 语义处理。
- Version/Receipt、SHA、Current 指针和正式附件仅由受控服务端入口管理。`create` 是本 CC 明确获裁决的初始版本直接登记路径；Provider 生成、验证结果或模型声称本身不能触发登记。后续既有文件编辑仍必须走 Candidate 与用户 Accept/Reject。
- 用户是业务内容的最终判断者。需要确认的可确认业务风险应在外发/执行前按现行确认机制处理；确认不能解除权限、安全、文件完整性或外发授权限制。

## 6. Minimal Implementation Scope and File Whitelist

仅在以下范围内作能完成 fileless create 的最小修改：

| 文件/模块 | 允许修改范围 |
|---|---|
| `mymodules/office_engine_m2/models/office_mapping_tools.py` | 在单一 `office` schema/facade 中增加 `create` action；保持其他 action 及 M1 Tool 兼容。 |
| `mymodules/office_engine_m2/services/edit_orchestrator.py` | 可信 Thread/Session 来源分流；无文件 `create` 调度、失败保护和交付；后续 `edit` 能解析 create 产生的 Current；不重构既有 edit 流程。 |
| `mymodules/odoo-llm/llm_openai/services/responses_adapter.py` | 在现有 Hosted Code Interpreter Adapter 支持无 XLSX 输入的创建请求并取得真实 XLSX 输出；保留普通 Chat Completions 和现有文件编辑接口。 |
| `mymodules/office_engine_m2/models/office_mapping_session.py` | 仅在必需时允许不绑定伪造源附件的受控 Session 创建，并准确表示创建意图来源；保留 ACL 和内部创建入口。 |
| `mymodules/office_engine_m2/services/workbook_version_service.py` | 增加受控、幂等的直接 V1/Current 登记；链接真实创建意图和输出附件，不登记虚假 input SHA/parent 或 Accept 事件；复用 Current/Last Valid/Revision、附件和 Finalize。 |
| `mymodules/office_engine_m2/services/candidate_validator.py`、`mymodules/office_verify/` | 支持没有输入文件的输出安全/完整性验证及 typed Receipt 绑定；不增加内容语义或业务正确性规则。 |
| 相关 Agent 指引及测试 | 说明何时调用 `office(action="create")`；增加 fileless create/后续 edit 的必要断言；不新增公开 Tool，不改 Retriever 查询实现。 |
| `docs/implementation/IHR-M2-CB-09.md`、`ATR-M2-CB-09.md`、`HVR-M2-CB-09.md`、`FR-M2-CB-09.md`、`evidence/CB-M2-CB-09/` | 实施后保存分层执行记录，不覆盖 CC-07/08 历史证据。 |

需要超出白名单、修改 Odoo 官方模块、改动 M1 内容生成、建立本地 Excel 内容引擎或改变 Provider 策略时，停止并另提授权。测试夹具目录按实际 addon 约定细化；不为形式统一新增目录或框架。

## 7. Automated Tests / HVR

### 7.1 Automated tests

1. 单一 `office` Tool schema 接受 `create`；无源请求不会错误落入 `edit`，且不增加第二个公开 Office Tool。
2. 无上传、无 Current 时，经获批创建路径可调用 Adapter；Adapter 未收到伪造 XLSX 输入，返回真实非空 XLSX 字节方可继续。
3. 适配器错误、超时/indeterminate、dispatch 关闭、外发权限不足、无输出/无效 XLSX 时，不登记 Current，不交付文件。
4. Retriever 数据使用当前用户权限；禁止业务记录写入；无可授权记录时不编造记录内容。
5. 初始版本登记与线程/用户/公司/意图/输出字节绑定，输出 SHA 可复核；需要内部 Receipt 绑定记录时，它不可由 Agent/RPC 接受；幂等重试不重复建版本/附件。
6. `VERIFIED` 与 `PARTIALLY_VERIFIED` 创建输出均可直接登记/交付；Partial 的验证等级和未验证范围如实保留/展示；`FAILED` 不得登记或交付。不得生成虚假的 Candidate Accept/用户 Accept 记录。
7. 创建后同 Thread `edit` 使用已登记 V1 的真实输出字节及相同 SHA 作为输入；V2 Accept 正常推进，Reject/失败/stale 保持 V1。
8. Finalize 与附件交付复用现有服务；下载 SHA 等于 Current 输出 SHA；重复交付幂等。
9. M1 上传、Mapping/RenderBridge、Retriever、Chat Completions 及 CC-07/08 相关回归按实际受影响范围运行并报告。

### 7.2 Odoo integration / HVR

**Fileless two-turn HVR（同一非生产 Odoo Thread）：**

1. 以普通用户自然语言请求创建一个 XLSX；Thread 中无先前上传工作簿或模板。
2. 使用 `odoo_record_retriever` 读取当前用户获准的合成或已单独授权测试数据（如果指令需要）；不修改 Odoo 业务记录。
3. 经获批的真实 Responses API + Hosted Code Interpreter 生成非空 XLSX。记录脱敏请求/Response/Tool/File ID、usage/时长（可得时）和文件 SHA；无法调用真实 Provider 时，本项为 BLOCKED/NOT RUN，不用 Mock 替代真实 HVR。
4. 以独立读取检查 XLSX 可打开、实际内容与测试数据相符、文件 SHA 与服务端版本附件相符；记录验证等级及未验证项。
5. 不产生首轮待审 Candidate/Accept；检查 V1/Current/Last Valid、初始 Document Revision=1、Session/Thread 绑定、验证等级披露和 Discuss 附件下载。验证为 Partial 时确认用户可见的说明准确列出未验证范围。
6. 在同一 Thread 继续以自然语言修改刚创建的文件。证明第二轮使用 V1 实际字节（Round 2 input SHA = V1 output SHA），生成 V2，原有用户指定内容保留且新修改可独立回读。
7. 对 V2 执行现行 Accept，使 Current 推进；再生成一个后续 Candidate 并 Reject，验证 Current/Last Valid/Revision 不变。按用户要求 Finalize，下载文件并独立回读，SHA 与交付的 Current 一致。
8. 核实 Retriever 只读、无 Odoo 业务数据变化；不得用直接 ORM 写 Current/Candidate、Mock Provider、内部 service 调用或聊天回复替代真实 UI/Agent/Tool/Provider/下载证据。

Unit/Mock、TransactionCase、真实 Provider、Odoo UI、实际下载和独立 XLSX 回读分别记录。Automated User Simulation 可用于对应自动化层；若使用真实 Discuss UI，说明其自动化/真人属性。证据不得含密钥、cookie 或不必要的真实个人数据。

## 8. Acceptance Criteria

CC-09 可提交 `READY FOR FINAL ACCEPTANCE` 的条件：

1. 遵循本 CC 的无源创建及直接 V1/Current 语义；如与冻结上游文件不同，以本 CC 仅在 CC-09 范围内的明确负责人豁免为依据，且不得声称上游文件已同步。
2. 无上传、无模板时，真实用户可通过唯一 `office` Tool 触发 LLM 主导的 XLSX 创建；真实 Adapter 成功取得实际 XLSX 输出字节。
3. 需要 Odoo 数据时只通过现有 Retriever，保留 ACL/Record Rules/多公司/字段权限及只读语义；未经授权不向 Provider 发送数据。
4. 文件安全/完整性、版本归属、输出 SHA 和失败保护均通过自动化与 Odoo 集成测试；失败时没有虚假成功、Current 推进或错误交付。
5. 新建文件在服务端有真实、可继续编辑的 V1/Current 版本来源；同 Thread 第二轮确实以其输出 SHA 为输入，并按现有 Candidate Accept/Reject 规则完成后续编辑。
6. 最终 Odoo Thread 附件可访问、可下载，独立回读内容正确，下载 SHA 与对应 Current 输出一致；重复操作遵守幂等性。
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
| 需要超出 CC-09 豁免范围的上游或安全策略变更 | 停止依赖该变更的部分并提交最小 Amendment；本 CC 的既定 fileless-create 语义不再以 TDD/SRS/Plan 对齐为前置门槛。 |

## 10. Dependencies and Recorded Baseline Differences

### 10.1 Frozen baseline differences (waived as CC-09 implementation gates)

以下是冻结基线与负责人已裁决行为之间的实际冲突。CC-09 只提出变更范围，不修改这些文件：

| 基线 | 冲突 | 本次处置 |
|---|---|---|
| Frozen SRS V1.1.0 | 未定义无上传文件的 LLM 主导 XLSX 创建和直接交付。 | 负责人已豁免对齐作为 CC-09 实施门槛；保留 SRS 原文，不作本次变更，也不把 CC-09 行为宣称为 SRS 已覆盖。 |
| Frozen TDD V2.1.0 | 对输入 XLSX、首次 Candidate/Accept 与 Current 推进有不同规定，与无源输入、直接 V1/Current、PARTIALLY_VERIFIED 可交付不同。 | 负责人已豁免对齐作为 CC-09 实施门槛；保留 TDD 原文，仅在 CC-09 范围依本契约实施并如实记录差异。 |
| Frozen Implementation Plan V2.0.1 + approved V2.0.2 amendment | 未列出 fileless create 实施批次。 | 负责人已豁免对齐作为 CC-09 实施门槛；保留 Plan 原文，不重开或扩大 CB-01～CB-08。 |

负责人已裁决产品行为：在单一 `office` Tool 增加 `create`；技术硬检查通过后直接登记 V1/Current 并交付；`PARTIALLY_VERIFIED` 可以交付且须披露；后续文件编辑仍走 Candidate→Accept/Reject；不伪造源附件、input SHA 或父版本。上述不再列为待裁决项。

### 10.2 Remaining execution boundaries

1. CC-09 编码已由本次明确授权；不得再以 SRS/TDD/Plan 对齐未完成为由阻断本 CC 工作。
2. 本授权不启用 Provider dispatch、不构成真实 Provider 外发、生产数据处理、服务重启/模块升级或生产发布授权；这些操作继续遵守现有独立门禁。
3. Odoo TransactionCase/模块升级、非生产服务操作须按届时 CC 单独授权。
4. 真实 Responses API + Hosted Code Interpreter HVR 必须有明确 Provider 测试授权。若使用真实 Odoo 数据，仍须适用的数据外发授权；测试授权不能自动开启 Provider dispatch。可先用合成数据，不得为完成 HVR 绕过现行 gate。
5. 无输入文件的 Hosted Code Interpreter 生成模式尚未由现有 Adapter 或 CC-07/08 证据证明，须在 CC-09 的真实 Provider 验收中验证；不预设支持或不支持。

## 11. Evidence and Handoff

实施期间按项目既有格式维护：

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
| v0.2 | 2026-11-11 | **FROZEN — IMPLEMENTATION AUTHORIZED (CC-09 SCOPE WAIVER)** | 按负责人裁决，批准同一 `office` Tool 增加 `create`；创建输出通过必要技术检查后直接登记初始 V1/Current 并交付，允许披露范围内的 `PARTIALLY_VERIFIED` 交付；后续编辑保持 Candidate→Accept/Reject。负责人豁免 SRS/TDD/Implementation Plan 对齐作为 CC-09 实施前置条件；上游文件保持原样，差异仅在 CC-09 范围内按本契约处理。无源创建不得伪造输入附件/SHA/父版本。保留 v0.1 历史文件。本冻结不授权真实 Provider 外发、生产数据、服务重启、模块升级或生产发布。 |
