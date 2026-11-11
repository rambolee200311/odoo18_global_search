# Odoo Office Engine M2 技术设计说明书（TDD）— LLM 主导 Office 内容生产

| 项目 | 内容 |
|---|---|
| 文档编号 | TDD-OFFICE-ENGINE-M2 |
| 版本 | V2.1.0 |
| 状态 | **FROZEN — APPROVED DESIGN — NOT AUTHORIZED FOR IMPLEMENTATION** |
| 日期 | 2026-11-10 |
| 冻结技术路线决议 | `docs/design/ADR-OFFICE-20261110-001_v1.0.md` — FROZEN；选定 Route B，不授权实施或生产发布 |
| 技术验证 | `docs/verification/TV_LLM_Native_Excel_Production.md` — 两轮文件级验证通过；Odoo Candidate/Accept/UI 闭环未验证 |
| 设计基线 | TDD V2.0.3 FROZEN；Frozen CB-05 Existing Retriever change；CB-06 Finalize alignment amendment |
| 适用范围 | Odoo 18 CE / Office Engine M1、M2 / AI Agent |
| SRS | 当前有效冻结版本保持不变；与托管文件编辑路线的正式规范对齐仍为实施前置事项 |

> 本版本经负责人批准冻结，是 Office Engine M2 的技术设计基线；它替代并整合 M2 TDD V2.0.3 与其当前有效的 CB-05、CB-06 补充条款，不覆盖历史文件。冻结不构成编码、Provider 生产调用、服务操作、模块升级、真实数据外发、部署或生产发布授权；SRS、Implementation Plan 与 CC 的后续版本化对齐仍按本文门禁执行。

## 0. 设计目标、范围与基线

### 0.1 目标

Office Engine M2 采用已冻结的 Route B：**LLM + OpenAI Hosted Code Interpreter 负责 Office 内容生成与多轮编辑，Odoo 本地负责治理。** LLM 理解用户意图、读取当前工作簿、决定内容与编辑方式，并在托管执行环境中生成真实 XLSX。Odoo 控制当前用户授权数据、文件安全、Candidate、验证事实、用户决策、版本状态、审计及交付。

通用内容生产不得以 Mapping、`repeat_rows`、`cell_edits`、样式原型行、固定表头、工作表名、单元格坐标或特定 Odoo 模型为前置条件。不得按模板简单/复杂程度自动切换路线。既有 M1 Mapping 路径为兼容能力，不再是 Office 通用内容生产的必经主路径。

### 0.2 范围

本 TDD 定义：

- 原始上传文件的首次 LLM 内容生成、Candidate、用户 Accept 与 V1/Current 登记；
- 单一 `office` Tool 对 Responses Adapter、Retriever、候选审阅与 Finalize 的服务端调度；
- 以当前 Accepted Current 为唯一多轮文件状态；
- 修改前确认、修改后本地验证、Candidate 接受、失败恢复及最终附件交付；
- M1 兼容边界、支持能力证据、测试层次及实施前置问题。

本 TDD 不要求建设本地通用 Excel 编辑 DSL、第二套 ORM 查询服务、代码执行沙箱、Snapshot/CDC 框架、事件总线、DAG、通用自然语言语义证明器或新的审批/安全策略管理系统。

### 0.3 决策效力及上游边界

1. Route B 技术选型已由 ADR 冻结。本 TDD 不重新比较路线，也不以当前 M1/M2 实现限制该目标。
2. ADR 冻结是技术路线决定，不等于 TDD 冻结、编码授权、生产 Provider 外发授权或生产发布批准；本 TDD 的冻结来自负责人对本版本的单独批准，仍不等于上述授权。
3. 本稿不修改原冻结 SRS、实施计划或 CC。SRS 与外发数据授权分别按环境/用途控制，不能混为一个“开发阻断”：

| 阶段 | 允许范围 | SRS / 外发门禁 |
|---|---|---|
| 文档、实现开发 | 可在独立 Coding Authorization 覆盖范围内编写服务接线、保持外部 dispatch 关闭；不处理真实文件、不调用 Provider | SRS 差异不阻止纯本地开发；不得以开发授权开启外发 |
| 本地 Mock / 合成数据测试 | 可按 CC 授权运行本地单元、TransactionCase、UI 模拟；数据不离开获批本地环境 | 不触发真实 Provider 外发；仍遵守 Odoo 测试库、服务和数据操作授权 |
| 真实 Provider 技术验证 | 必须有明确、限模型/请求数/费用/文件/数据范围的 Provider 测试授权；使用真实业务数据时还须有对应数据外发授权 | 单次 TV 授权只覆盖所列测试；若现行 SRS 也限制该类测试处理，必须有正式版本化例外/变更或相符的测试授权，不得绕过 |
| 生产外发与发布 | 处理获批的真实文件/业务数据并启用公开 dispatch | 需要正式 SRS 版本化对齐、数据分类/处理/留存政策、运行门禁及 Production Release 批准；未完成前保持 dispatch 关闭 |

4. 代码中的 `EXTERNAL_PROVIDER_DISPATCH_ENABLED=False` 继续作为生产路径 fail-closed 状态。本 TDD 不修改该配置，也不授权开启。纯本地实现与 Mock 测试可先行；真实 API 测试和生产外发各自按上表取得授权。
5. 已冻结 CB-05 Existing Retriever change 与 CB-06 Finalize amendment 在本稿中整合。其他已验收能力只在原验收范围内复用；本稿不将其扩大解释为整条产品链已通过。

### 0.4 TV 证据状态

2026-11-10 TV 对同一 `contact1.xlsx` 和同一批当前用户有权读取的 Odoo 联系人，完成两种 LLM 主导路线的连续文件级试验：

| 能力 | 结果 | 边界 |
|---|---|---|
| Route B：Responses API + Hosted Code Interpreter，原始 XLSX → 填充联系人 XLSX | **VERIFIED** | 真实请求、真实输出字节、独立 XLSX 回读；无预置数据行，无 M1 repeat_rows/Mapping |
| Route B：上一轮输出 → 新增地址列 XLSX | **VERIFIED** | 第二轮输入 SHA 与第一轮输出 SHA 一致；A–C 保持，D 列地址与第二次 Retriever 查询匹配 |
| Route C：模型生成完整表格内容 + 通用 Artifact Tool 序列化 | **VERIFIED（小型表格）** | 连续两轮回读通过；不作为通用主路线，不证明复杂 OOXML 保真 |
| Route A：无执行工具的模型原生 XLSX 二进制输入/输出 | **UNVERIFIED** | XLSX 文件输入能力有官方接口依据；未验证无工具二进制输出路径 |
| Odoo UI → Candidate → Accept → Current → Finalize/下载 | **UNVERIFIED** | 本次 TV 没有创建或接受 Odoo Candidate，也没有运行完整 UI 链 |
| 多工作表、复杂公式、格式、图表、命名区域、大型工作簿等保真 | **UNVERIFIED** | 简单单表联系人文件不提供这些能力的证据 |
| API 用量 | **VERIFIED** | 4 次 Responses 请求，15,349 输入、4,901 输出、20,250 总 Token；账单金额未核实 |

详细请求 ID、文件 SHA-256、独立回读和限制见 TV 报告。一次技术验证的真实 Odoo 数据授权不构成未来生产数据外发的通用授权。

## 1. 架构决策与职责

### 1.1 目标逻辑流程

```text
用户上传文件并提出内容目标
       ↓
唯一公开 office Tool：当前用户/Thread/附件授权和上下文
       ↓
必要时 office.retrieve：复用当前 Thread 绑定的 Odoo Retriever
       ↓
Odoo 按当前用户 ORM 权限返回最小所需数据
       ↓
Responses Adapter：把当前工作簿、指令和已授权数据交给 Route B
       ↓
Hosted Code Interpreter 由 LLM 主导生成/编辑真实 XLSX
       ↓
Odoo 下载候选字节、绑定 SHA/来源并执行本地技术验证
       ↓
Candidate 向用户审阅；当前用户明确 Accept 后才成为 Current
       ↓
后续编辑始终以最新 Accepted Current 为输入
       ↓
用户请求正式交付 → Finalize → 私有附件/Discuss 消息交付
```

工具调用、候选文件生成、Candidate 登记、用户 Accept、Current 推进、Finalize 和实际下载是不同事实，必须分别报告。其唯一状态语义见 §4 与 §8。

### 1.2 组件职责

| 组件 | 权威职责 | 不负责 |
|---|---|---|
| Agent / LLM | 理解用户自然语言；分析工作簿内容；决定布局、数据应用和编辑操作；产生内容并说明声明与不确定项 | Odoo ACL、Current 指针、候选接受、权限批准、最终业务决定的替代者 |
| Odoo `office` Facade / Orchestrator | 从认证 Thread/用户派生身份；检查调用上下文与政策；调用 Retriever、Responses Adapter、Validator、版本和交付服务；规范化实际结果 | 由客户端提供可信 `user_id`、直接信任模型成功描述、在本地重写工作簿内容 |
| `odoo_record_retriever` | 在当前用户 ORM、ACL、字段权限、Record Rules 和多公司范围下只读查询；保留记录 ID、现有分页和值序列化语义 | 选择 Excel 坐标、写工作簿、改变业务记录、建立第二套查询框架 |
| Responses Adapter | 调用现有配置的 OpenAI Responses API；传输工作簿及获准数据；调用托管 Code Interpreter；取得真实文件字节和调用元数据 | Odoo ORM/权限、版本接受、业务语义裁决、普通 Chat Completions 的替换 |
| Hosted Code Interpreter | 在 Provider 托管执行环境中运行模型决定的文件处理，返回真实文件 | 取得 Odoo 凭据、访问 Odoo 内网/数据库、执行 Odoo Worker 任意代码或决定文件接受 |
| Candidate Validator / `office_verify` | 读取输入/输出实际字节；执行明确且有证据支持的文件完整性、安全、SHA、版本绑定和可证明差异检查；生成 typed Receipt 和未验证项 | 创作/修复工作簿内容；证明自然语言意图绝无遗漏；以旧 Mapping 假设限制可编辑区域 |
| Workbook Version Service / CB-02 | 管理私有附件、版本 lineage、并发、幂等、验证回执绑定、Candidate 接受/拒绝和 Current/Last Valid/Revision | 接受由 LLM/RPC 直接传入的可信标记或自行判断业务正确性 |
| Thread/附件/Finalize 服务 | 将已接受版本正式化并关联私有附件和当前 Thread 消息；记录交付状态并支持幂等重试 | 重跑编辑、变更工作簿字节或使未接受 Candidate 正式交付 |
| 用户 | 审查内容、决定可确认风险和业务结果，接受/拒绝/要求修订 | 绕过权限、安全、资源、完整性和版本硬约束 |

### 1.3 文件生产路线

- **主路线 Route B：**原始或当前 XLSX + 自然语言意图 + 已授权数据 → Responses API / Hosted Code Interpreter → 真实 XLSX 字节。由 LLM 决定并生产内容；本地不生成 `cell_edits` 再逐格执行。
- **Route C：**只保留本次已验证的实验记录，不作为主路线或隐式回退。不得因 Route B 文件复杂而自动切换。
- **Route A：**未验证，不作为设计依赖。
- **Route D：**本轮不建设。禁止在 Odoo Worker 运行模型生成 Python；以后要建本地隔离执行须另行 ADR/授权。
- M1 Mapping / `repeat_rows` / `cell_edits` 可用于历史/显式兼容的 M1 工作流，不是新通用内容生产的前置条件，不得自动按模板复杂度分流。

## 2. 单一 `office` Tool 与内部接口

### 2.1 对外工具边界

AI Agent 只见一个公开 `office` Tool。Responses Adapter、Retriever、Validator、Version Service、Orchestrator 和 Finalize 均为内部组件，不新增公开 Agent Tool。现有 Chat Completions 路径保持并存，不能因 Responses Adapter 改变普通聊天结果格式或流式行为。

`office` 继续使用 `retrieve`、`plan`、`edit`、`accept`、`reject`、`finalize` 等现有动作。首次创建和后续编辑统一调用 **`office(action="edit")`**；由服务端根据认证 Thread、Session、授权附件和版本记录识别来源：

- 当前文件 Session 尚无 Accepted Current，且有唯一、可访问的原始上传附件时，按首次创建处理。
- 当前 Session 已有 Accepted Current 时，以服务端 Current 字节为唯一输入，按后续编辑处理；不得由模型参数指定旧版本或替换当前附件。
- 缺少/多义原始附件、Session 归属不一致或来源冲突时，要求澄清/阻断，不猜测来源，不静默创建另一条版本链。

初始/后续分支是同一 edit 服务内的源文件解析与生命周期处理，不新增公开 Tool 或由客户端控制的 `create` 绕过入口。参数名和 Thread/Session 解析须由实现 CC 在现有 Facade 上核定。

### 2.2 首次创建与后续编辑的输入

| 编辑来源 | 文件来源 | Odoo 数据 | Provider 输入 | 限制 |
|---|---|---|---|---|
| 首次创建 | 当前 Thread/Session 中唯一且用户有权访问的原始上传附件及其 SHA | 只有用户目标需要且当前用户可读的数据；经外发政策允许时最小化提供 | 原始 XLSX bytes、用户原始指令、必要授权数据 | 不要求 M1 Mapping/V1、A2/样式原型行；不能修改源附件或直接设 Current |
| 后续编辑 | 服务端查出的 Session Accepted Current 私有附件与 SHA | 可按需多次调用 `office.retrieve`；保持业务数据只读 | 当前 Current XLSX bytes、当前指令、必要授权数据和适用确认上下文 | 不得用原模板、旧版本或聊天记忆替代 Current 文件 |
| Finalize | 服务端解析的 Accepted Current | 不需要重新查询或编辑 | 不调用 Provider | 仅正式化并交付同一 Accepted Current 字节 |

Provider 输入及响应中的文件 ID、Response ID、Tool ID 均是不可信诊断元数据；附件实际字节、SHA、Session/Thread/用户关系由 Odoo 复核。

### 2.3 `office.retrieve` — Existing Retriever Integration

同一 Office Thread 允许按需多次查询。唯一公开入口为 `office(action="retrieve")`，内部首选从当前 Thread 的 `thread.tool_ids` 取得已绑定 `odoo_record_retriever`，并复用既有 `llm.tool.execute()` 调用链。不得复制 ORM 搜索或另建查询服务。若绑定生命周期不符，应由实现 CC 提交最小兼容处理，不得回退管理员权限或直接跳过当前 Retriever。

查询沿用 Retriever 的 `model`、`domain`、`fields`、`order`、`limit`、`offset`、`include_pagination`。返回现有 `records` 或分页对象；保留稳定 `id`、现有类型和值语义、分页信息及轻量查询范围/读取时间（若可从原调用直接取得）。分页是独立 ORM 查询，不构成点时一致快照。此动作只读 Odoo，不要求 Accepted Current，不修改工作簿或版本指针。取数成功不等于 Excel 已更新。

不新增 Snapshot、snapshot_id、content/query fingerprint、Full/Incremental/CDC、删除推断、跨页一致性快照、Workbook 读取锁或外发规则管理。现有 ORM ACL、Record Rules、公司隔离、字段访问权、M1 Retriever 输入/输出兼容及当前有效外发授权继续适用。

## 3. Responses Adapter 与 Hosted Code Interpreter

### 3.1 Adapter 请求契约

Odoo Facade 先完成 Thread/用户/附件权限、必要确认、资源上限和外发政策判断；然后才允许调用 Adapter。Adapter 使用现有 OpenAI Provider client/endpoint/credentials 和获批模型，接收：

- 实际输入 XLSX bytes、输入 SHA-256、文件名及 MIME；
- 用户本轮原始指令及必要 Agent 上下文；
- 当前用户允许读取且本次任务必要的数据；
- 当前版本/初始来源绑定、确认范围摘要（如适用）；
- 请求次数、超时、文件大小、输出 Token、容器资源和重试策略。

Adapter 返回真实候选字节，及可获得的模型、Response/Request/Tool/File/Container ID、usage、时长、输出 SHA、资源清理状态与结构化错误。不存在可下载 XLSX 时，不得构造伪文件或成功状态。

### 3.2 执行和资源边界

- 模型生成/执行的工作簿处理代码只在 Provider Hosted Code Interpreter 内运行，不在 Odoo 服务进程、本地 shell 或 Odoo Worker 执行。
- Code Interpreter 不获得 Odoo 凭据、ORM、数据库连接、服务器路径或本地密钥；按获批策略关闭不必要的网络能力。
- 每次调用设置明确超时、SDK 隐式重试关闭、输出 Token、输入/输出字节限制及容器资源。请求次数按调用方逐次计数，不静默重试、不自动循环至成功。
- 费用记录区分 Token usage、工具/容器用量、估算和实际账单。未能核实的费用必须标记 `UNVERIFIED`；估算不能伪称账单或账户级硬限制。
- 未收到服务端响应的连接/超时结果为 `indeterminate`，不得盲目重发；先利用已知请求/响应/文件关联核实可恢复状态。清理失败记 `cleanup_pending`，不得把“已请求清理”写作“已删除”。
- 外发策略、数据处理/留存授权不满足时，在上传前阻断。用户确认业务内容不能绕过数据外发政策。

### 3.3 真实输出条件

`candidate_received` 表示 Provider 已返回并成功下载非空 XLSX 字节，且最低 ZIP/OOXML 容器检查通过。它不表示内容正确、结构保真、业务意图完成或文件已接受。必须记录候选 SHA 并关联当前用户指令、输入附件/父版本、Session/Thread 及 Provider 调用 lineage。

## 4. 首次 Candidate、Accept、V1 与后续版本

### 4.1 首次生成生命周期

首次文件生产不调用 M1 Mapping 作为必经步骤。其逻辑流程为：

```text
Raw Upload (源附件及 SHA)
   → LLM/Hosted Code Interpreter 生成真实 XLSX
   → 创建非 Current 的 Initial Candidate
   → 本地绑定/安全验证并形成 typed Receipt
   → 将实际 Candidate 呈现给用户审阅
   → 当前用户经受控 Accept 入口明确接受
   → 在同一原子版本服务操作中登记 V1，并设 Current / Last Valid
```

Initial Candidate 必须引用源附件 SHA、实际输出字节 SHA、Thread/Session/owner、用户指令、验证 Receipt 和必要的授权/确认范围。Candidate 生成、下载、技术验证或 Agent 文本均不得直接创建 Accepted Current。首次 Accept 前不得推进 Current/Last Valid/Document Revision；用户拒绝或候选失败时，保留源附件和既有状态。初始与后续 Candidate 的统一 Accept 规则及服务端重验条件见 §4.3。

现有 `register_initial_v1` 只接受有持久 M1 验证证明的 M1 输出，不能直接用于 LLM 初始文件。实现需要在现有 Version Service 中增加或扩展最小的受信任 Initial Candidate/Accept 路径。其数据模型/方法名应在实现前核对现有字段并通过服务端内部入口完成；不新增另一套版本系统，不暴露可由 RPC/LLM 写 Current 指针的入口，不伪造 M1 proof。

初始 Candidate 的验证等级及可接受边界见 §4.3、§6.2；首次和后续 Candidate 均适用相同 Accept 规则。

### 4.2 后续多轮版本链

```text
V1 accepted_current
   → User intent / optional Odoo retrieve
   → Responses + Code Interpreter 读取 V1 实际字节
   → Candidate V2 (parent=V1, input_sha=V1 SHA)
   → Validator Receipt / 必要的事前风险确认
   → 当前用户明确 Accept / Reject / Revise
   → V2 accepted_current 或保持 V1
   → 后续 V3 必须以实际 Accepted V2 bytes 为输入
```

每轮只以服务端当前 `accepted_current` 为输入；拒绝、失败、过期或未接受候选不会成为下一轮输入。通过现有父版本、SHA、Document Revision、Proposal/Session Revision 及幂等约束防止分叉候选同时推进。对话上下文帮助理解任务，但不能替代当前工作簿字节；不得用 Provider conversation ID 或历史 Prompt 重建工作簿。

### 4.3 状态与接受等级

版本验证等级与版本生命周期状态是独立维度。每个 Candidate（包括首次和后续）都必须经同一受控用户 Accept 才能成为 Current；风险确认（如需）用于授权执行限定范围的操作，不替代 Candidate Accept。Accept 不改变验证等级。各验证结果的判定证据见 §6.2：

| 验证等级/状态 | 语义 |
|---|---|
| `VERIFIED` | 适用的文件技术检查及可确定验证项通过；不是自然语言意图完整性证明或用户授权 |
| `PARTIALLY_VERIFIED` | 未知保真或可观察的效果差异尚未满足完全验证条件；硬安全门通过，事实/未知项须披露；详细边界见 §6.2 |
| `FAILED` | §6.2 所列已确认损坏或不可绕过硬约束失败；不得接受，用户决定不能放行 |
| `candidate_received` / `verified` / `partially_verified` | Candidate 仍非 Current；所有等级均须经同一 CB-02 受控用户 Accept 后才能推进 |
| `accepted_current` | 服务端已经原子接受并推进指针；可保留 `VERIFIED` 或 `PARTIALLY_VERIFIED` 原等级 |
| `rejected` / `stale` / `failed` | 不推进 Current/Last Valid/Revision |
| `finalized` / `delivered` | CB-06 已正式化或实际交付的独立状态，不等于文件验证或 Accept |

按 CB-02/CB-06 的受控入口，用户可接受 `VERIFIED` 或知情后明确接受的 `PARTIALLY_VERIFIED`；不提升验证等级。`FAILED`、过期或未接受 Candidate 不得成为 Current 或 Finalize。拒绝不改变 Current、Last Valid、Document Revision 或历史附件字节。

## 5. 用户意图、确认和决策权

### 5.1 意图与计划

Agent 保留本轮用户原始指令，并可给出便于 Odoo 和用户理解的目标/影响计划。该计划是模型声明，不是本地代码执行计划，也不能用固定模板/坐标规则决定内容写入能力。简单明确操作不强制增加一次 Provider 计划调用。只有当目标歧义、数据关联不明或业务风险范围不能让用户知情决定时，才请求澄清/确认。

### 5.2 确认语义

- 用户明确指定的普通修改可直接进入 Candidate 生成，不因“单元格已有值”机械增加事前风险确认；但所有 Candidate 均须经 §4 规定的同一明确 Accept 才能成为 Current。
- 批量覆盖/清空、破坏性操作、重大公式或结构影响、超出用户表述的业务风险，仍须按现行规则说明影响，并在执行风险操作前取得绑定确认。该事前风险确认授权的是限定操作范围，不替代生成 Candidate 后对实际文件的 Accept。
- 确认绑定当前认证用户、Thread/Session、源附件或父版本 SHA、revision、原始意图、具体风险及允许范围；执行前重新校验。任一绑定实质变化则旧确认失效。
- Accept 是对实际 Candidate 的用户决定；它不是重复事前风险确认。Finalize 是对已接受 Current 的正式交付请求，不重复要求 Accept，也不增加固定口令。
- 用户确认、Accept 或 Agent 自述均不能绕过 ACL、Record Rules、公司隔离、附件授权、外发政策、资源限制、文件完整性、来源绑定或版本冲突。

### 5.3 意图完成声明

分别表示：

- `execution_verified`：服务端验证过的文件/来源/版本/结构化效果事实；
- `coverage_declared`：Agent 对识别到的用户要求及已覆盖/未覆盖/不确定项所作的声明，不构成独立自然语言语义证明；
- `task_completed`：Agent 面向用户的结果描述，必须与服务端结果一致，并明确任何已知未覆盖或未验证内容。

模型声称“完成”、Tool 返回成功或 Candidate 存在，都不能提升为已接受、已交付或自然语言意图完整证明。

## 6. 本地验证与支持能力

### 6.1 验证目标与不可替代职责

本地 Validator 的职责是发现、分类并留证文件和流程事实，不决定业务内容应是什么，也不替用户判断是否满足业务目标。它应接收真实输入/输出字节、当前源 SHA、候选 SHA、父版本/初始源、Thread/Session/user/revision、Expected Effect（若存在）及能力策略。

至少检查：附件所有权/ACL、输入输出 SHA、XLSX ZIP/OOXML 可读性、文件大小/解压与资源预算、候选版本绑定、当前父版本/revision、返回字节与登记文件一致。按实际支持能力检查工作表/单元格/类型/公式/格式/结构差异并记录证据；不得让模型声称替代独立回读。

`Expected Effect` 是只读结构化目标/条件/允许影响范围说明，不是本地编辑 DSL，也不要求精确列出所有单元格。验证粒度按已能确定的证据报告。效果未完全匹配但 XLSX 仍安全可读时，说明实际差异及未验证项，可要求模型重试、澄清或向用户展示；不能仅因业务内容与模型计划不同就误报文件损坏。真正的权限、安全、字节、来源或技术完整性失败继续硬阻断。

### 6.2 结果与用户决定分离

| 结果 | 判定和后续 |
|---|---|
| `VERIFIED` | 所声明且适用的确定性文件检查通过；可进入现有授权接受流程，但不自动证明业务意图完整 |
| `PARTIALLY_VERIFIED` | 权限、安全、资源、字节、来源、SHA 和版本硬检查通过，但某项保真、复杂结构或内容效果无法确定，或有可观察的效果差异尚未解决；列明未知项/差异和已有证据，交用户决定接受、拒绝或要求重做。未知保真本身不是损坏 |
| `FAILED` | 有证据确认 XLSX/OOXML 损坏、必要结构不可读/已破坏、被要求保留的内容确已丢失/破坏，或权限、安全、外发授权、资源、来源、SHA、版本等硬约束失败；必须阻断，用户确认不可绕过 |

验证结果、Risk Facts、Confirmation Gate 与 User Accept 是不同事实。合法覆盖非空值/表头不自动构成失败；是否需要事前确认按现行风险判据。工作簿可读且未发现损坏、但效果是否正确或某特性是否保真未知时，不得误标为 `FAILED`；相反，已确认损坏不得降为 `PARTIALLY_VERIFIED`，也不得因用户 Accept 放行。可被确定性观察到的内容差异应如实报告，并将其与文件损坏区分；有差异时不得宣称任务目标已完成。Validator 不新增业务判断规则，不因用户选择接受而把验证等级改成 `VERIFIED`。

### 6.3 首期文件能力证据矩阵

以下矩阵报告当前事实，不等于承诺未经验证的普遍保真。文件复杂度不得触发 Mapping/Route C 等替代生产路线；只有对实际文件或变更能力不足时，才按具体技术风险标注部分验证、失败或请求用户选择。

| 特性 | 本 TV 状态 | 处理原则 |
|---|---|---|
| 单表基础值及新增数据行 | **VERIFIED（contact1 小型工作簿）** | 不依赖数据行预置或样式原型行 |
| 新增地址列，保留 A–C | **VERIFIED（两轮连续文件级）** | Round 2 输入 SHA 必须与 Round 1 输出 SHA 对应 |
| 多工作表 | **UNVERIFIED（本次路线 TV）** | 后续集成前须对实际候选读取和非目标保真做有证据测试 |
| 公式/跨表引用/公式重算 | **UNVERIFIED（本次路线 TV）** | 明确区分公式字符串保持、引用正确、计算结果重算；无计算引擎证据不得宣称重算正确 |
| 样式/数字格式/条件格式 | **UNVERIFIED（本次路线 TV）** | 合法序列化变化不得自动视为损坏；真实格式破坏应报告并保护前版 |
| 合并、冻结窗格、Excel Table、名称区域、隐藏行列 | **UNVERIFIED** | 需逐类证明解析与回读能力 |
| 图表、数据透视表、切片器、嵌入对象、宏/VBA、外部连接 | **UNVERIFIED** | 不宣称完整保真；有安全风险或无法保证文件可用时阻断，普通业务未知应准确披露，不丢弃对象后伪报通过 |
| 大型工作簿 | **UNVERIFIED** | 受 Provider/API、文件解析、工具容器及 Odoo 资源预算限制；拒绝或阻断需说明具体限制 |

Responses 文件输入对 XLSX 有支持，官方指南提及其表格解析范围；这不证明任意复杂文件均完整呈现或往返保真。详细单次 TV、模型/SDK/Provider 使用证据见 TV 报告及官方能力链接。

## 7. 版本、Accept、Finalize 与交付

### 7.1 版本权威

Odoo 保存 Session/Thread 作用域内的私有源附件、Candidate、接受版本及正式交付引用。每个 Candidate 至少绑定 source/parent version、输入和输出 SHA、用户意图消息、revision、typed Validation Receipt、Provider/Response/Tool/File IDs（若有）、usage、耗时、清理状态、验证等级、用户决定和交付状态。不存在的远端字段明确记为 unknown/empty，不伪造。

Session Revision、Proposal Revision、Document Revision、Workbook version 与 Provider response ID 含义不同，不能互相替换。只由服务端授权方法创建/更新 Candidate 和 Current；普通用户、模型、RPC 参数不能写入验证证明或指针。并发候选只能有一个符合 parent/revision 条件而推进 Current。

### 7.2 Accept 与 Candidate 决策

版本服务按 §4.3 执行统一 Accept 规则：首次接受登记 V1，后续接受推进版本；拒绝不推进。`VERIFIED` 和 `PARTIALLY_VERIFIED` 保留原等级；`FAILED`、stale 或已拒绝 Candidate 永不成为 Current。Finalize 见 §7.3。

### 7.3 Finalize

Finalize 仅处理服务端解析的 Accepted Current。用户明确要求正式生成或交付文件即可作为 Finalize 指令，不需要重复 Accept 或固定确认短语。Finalize 复用版本附件字节，按版本 SHA 关联私有 `ir.attachment` 与当前 Thread 消息；重复调用同一版本应复用附件/消息，失败可幂等重试。

Finalize 不重新运行 Validator、不提升 `PARTIALLY_VERIFIED`、不更改 Current/Last Valid/Document Revision/SHA、不重新编辑文件。只有真实下载/附件服务证据存在时才声明交付完成。被接受的 `PARTIALLY_VERIFIED` Current 可按已冻结 CB-06 amendment 正式交付并继续显示未验证事项；未接受或 `FAILED` 不能 Finalize。

## 8. 单一 Tool 结果与状态语义

保持现有兼容字段并复用服务端事实：`status`、`operation_status`、`artifact_state`、`delivery_state`、版本 ID、验证等级、SHA、Receipt、model claims、verified facts、unverified aspects。除确有不可表达差异，不新增全局状态框架。

| 对外结果 | 服务端语义 |
|---|---|
| `completed` | 本次明确阶段已完成；须用 artifact/version/delivery 字段说明是 Candidate 已生成、接受已完成还是附件已交付。不能泛称用户自然语言任务已被独立证明 |
| `confirmation_required` | 目标可理解，存在可确认业务风险；风险写入尚未执行 |
| `clarification_required` | 目标、范围、关联记录或必要参数不明确 |
| `blocked` | ACL/Record Rules、外发政策、安全、资源或不可绕过技术边界不允许继续 |
| `failed` | 已执行操作失败或完成状态不能可靠确认；保留已有有效版本并报告实际副作用 |
| `indeterminate` | 请求可能已送达但没有可信响应/产物状态；禁止盲目自动重试，待核实恢复 |

Agent 只把服务端实际状态翻译为用户语言；不能依据模型自由文本更改 Outcome。业务用户不能看到密钥、敏感系统错误或未经授权的他人数据。

## 9. 安全与数据处理约束

- 所有 Odoo 读取、附件访问和状态变更均以认证用户及 ORM ACL、字段权限、Record Rules、公司范围和附件权限为准；不得使用 `sudo()` 绕过访问控制。
- Hosted Code Interpreter 只接收获准的工作簿及完成本次任务所需的最小数据，不得取得 Odoo 凭据、ORM、数据库连接、本地路径或密钥；按有效政策限制网络能力。
- 文档、代码开发和本地 Mock/合成数据测试不等于真实 Provider 外发授权。真实 Provider 测试和生产处理分别遵守 §0.3 的门禁；任何用户 Accept 均不能绕过外发授权。
- 远端处理、留存与删除须按获批的数据政策执行。审计记录只保存完成追溯所需的引用、SHA、请求 ID、错误分类、用量及验证事实；不得记录凭据、完整用户数据、完整提示或不必要的工作簿内容。

各阶段的失败、状态保持和恢复规则集中定义于 §12，避免重复维护两套失败矩阵。

## 10. 与现有资产的兼容和变更分类

| 当前设计/能力 | 本 TDD 处置 | 说明 |
|---|---|---|
| M1 Mapping、Canonical Operations、`repeat_rows` | **保留为兼容；从通用主路径移除** | M1 原有明示流程不重写；新通用内容生产不依赖 Mapping、原型行或模板预设 |
| M1 Retriever | **保留** | 原 ORM 权限、M1 Tool 输入/返回和默认行为兼容 |
| M2 `office` Facade | **保留并作为唯一公开入口扩展** | 接入 initial create/Responses/现有 retrieve/accept/reject/finalize 路由；不加第二个 Agent Tool |
| OpenAI Chat Completions | **保留不变** | Responses Adapter 独立并行 |
| CB-01 Responses Adapter | **保留并接入** | 已经能完成简单 XLSX 两轮真实编辑；公众 Facade 当前仍关闭 |
| CB-02 Version/Current/Last Valid/Accept/Reject | **保留，最小扩展初始 Candidate 注册/Accept** | 现有 `register_initial_v1` 需 M1 proof；不能用它伪装 LLM 初始 Candidate |
| CB-03 Candidate Validator/Receipt | **保留治理事实与可信 Receipt** | 不作为内容生产引擎；部分验证语义与实施策略须按本 TDD 评审并由后续 CC 版本化对齐 |
| CB-04 Intent/Confirmation/Orchestration | **保留职责，适配初始 Route B 和外部调度** | 不增加通用意图 DSL；用户授权、澄清和候选决策按既有边界 |
| CB-05 `office.retrieve` | **保留现有 Retriever 复用** | 无 Snapshot/CDC/Fingerprint 新框架；取数只读且不锁 Workbook version |
| CB-06 Finalize/附件/Discuss | **保留** | 只交付 Accepted Current；支持 accepted `PARTIALLY_VERIFIED` 且不重新验证/升级等级 |

### 10.1 预计受影响组件（设计影响，不是实现白名单）

- `mymodules/office_engine_m2/models/office_mapping_tools.py`：保持单工具 schema，允许初始创建和现有动作。
- `mymodules/office_engine_m2/services/edit_orchestrator.py`：原始文件初始化分支、可信 Adapter 注入、外发 Gate 和实际状态编排。
- `mymodules/office_engine_m2/services/workbook_version_service.py`：Initial Candidate/Accept 的服务端原子入口；复用既有版本表/Receipt/附件能力。
- `mymodules/office_engine_m2/services/candidate_validator.py` 与 `mymodules/office_verify/`：只按 TDD 的差异/事实验证职责调整，须保留安全硬门及 CB-02 Receipt 信任边界。
- `mymodules/office_engine_m2` Retriever 路由及 M2 Agent 指引：沿用冻结 CB-05 `retrieve`。
- `mymodules/odoo-llm/llm_openai/services/responses_adapter.py`：已存在，优先复用，不重写 Chat Completions。
- `mymodules/office_engine_m2` 的现有 Candidate/Finalize/UI 测试与版本记录：按后续 CC 验收，不在本轮修改。

具体文件、manifest/schema 迁移、ACL 和测试白名单须由版本化 Implementation Plan/CC 明确；本稿不修改它们。

## 11. 验收与测试契约

所有证据须区分 Unit/Mock、Odoo TransactionCase、真实 Provider、Odoo UI、文件下载/独立回读。Mock 不冒充 Provider；独立 Provider 文件测试不冒充 Odoo E2E；浏览器页面加载不冒充真实业务成功。所有未执行的场景标为 `NOT RUN/UNVERIFIED`。

### 11.1 单元与服务契约测试

- Responses Adapter 请求模型、XLSX 输入/输出引用解析、SHA、错误和 timeout 分类、关闭 SDK 自动重试、文件限制、容器清理和 usage 记录。
- M1 Chat Completions `content`、`tool_calls`、streaming 与普通 Provider 配置兼容。
- 首次与后续 Candidate 使用同一 Accept 规则：生成/验证后均不自动推进；只有明确 Accept 才原子更新 Current；Reject/FAILED/权限失败不推进；跨 Thread/用户/公司、错误 SHA、伪造 Receipt 被拒绝。
- `PARTIALLY_VERIFIED` 明确列出未知项并可在知情后接受，接受不升等；未知保真不误报为损坏；确认损坏及硬约束失败保持 `FAILED` 且不可由 Accept 绕过。
- Current 后续 Candidate 的 parent/input SHA/revision、失败恢复、重复请求幂等。
- Retrieve 多次调用复用 Thread 绑定 Retriever；权限与 M1 输入/输出兼容；取数不要求 Current 且不写业务记录。
- Finalize 不编辑/接受/重验文件，重复交付复用附件和消息，失败不伪报 delivered。

### 11.2 Odoo TransactionCase 与集成测试

- 使用当前用户 ORM 验证附件、Thread、Session、Candidate 权限、Record Rules、公司隔离、只读联系人数据。
- 原始上传 → Initial Candidate → typed Receipt → 用户接受 → 原子登记 V1/Current；Candidate SHA 和实际附件字节一致。
- 用户拒绝/文件损坏/权限失败/Provider 无文件时，Current/Last Valid/Revision 保持原值。
- 初始 Candidate 与后续 Candidate 都必须显式 Accept；不得只因低风险、先前意图授权、Provider 成功或 Validator 通过而自动推进。
- 结构安全但保真未知的 Candidate 可保持 `PARTIALLY_VERIFIED` 并进入知情决策；验证确证损坏时为 `FAILED` 且不得接受。
- V1→V2→V3 中每轮输入 SHA 与前一已接受版本 SHA 相等；仅接受有效父版本，过期候选不能推进。
- Provider 成功后 Odoo 事务/Thread 回复失败时，从真实持久化状态恢复，不重复产生不同版本或附件。
- 既有 M1 Mapping/RenderBridge/Private Attachment 和 Document Request 回归不退化。

### 11.3 必需真实两轮 Odoo 端到端验收

M2 正式验收至少有一次同一非生产 Odoo Thread 的真实闭环，不能仅引用 2026-11-10 隔离文件级 TV：

1. 使用真实用户 UI/Agent 上传一个只有表头、无预置数据行的 XLSX；按当前用户 ORM 权限查询本次必要的数据，并在外发政策批准时调用真实配置的模型。
2. 模型读取原文件并产生真实 XLSX Candidate；独立回读对照用户授权数据。无需 M1 Mapping、`repeat_rows` 或用户预建 A2/样式行。
3. 用户审阅 Candidate 并按正式 Accept 机制接受；ORM 只读证明 Accepted Current/V1、Last Valid、Revision、SHA 和附件一致。
4. 同 Thread 明确要求为相同记录补充第二轮数据；Agent 再次调用 `office.retrieve`，使用稳定记录 ID；Responses/Code Interpreter 以第一轮实际 Accepted Current 字节为输入生成第二个 Candidate。
5. 独立验证原有列内容未变化、新列/新值与二次授权数据一致；用户接受，证明版本链 V1→V2 与输入/输出 SHA 正确。
6. 用户请求正式交付；Finalize 附件卡可用，实际下载字节 SHA 与 Accepted Current 相符，独立 XLSX 回读通过。
7. 另验证一次用户拒绝 Candidate 后 Current/Last Valid/Revision 不变。全程不修改 Odoo 业务记录。

本 TV 的模型文件生成两轮仅为 **isolated Provider/file PASS**，不能代替以上 Odoo UI/Candidate/Accept/Current/Finalize/Download PASS。真实联系人数据须有特定测试授权或选用获批数据集；不能因为本次 TV 已上传过真实联系人，就认为生产外发已获批。

### 11.4 复杂工作簿与保真测试

按结构能力矩阵逐步以中性/获批工作簿验证：多 Sheet、公式/跨表引用、样式、合并、表格、名称区域、条件格式、数据验证、隐藏行列、图表、宏/外部链接、大文件。每项报告原始 SHA、候选 SHA、文件结构、值/公式/样式差异、未验证范围和 Provider/本地资源。没有真实计算引擎时只验证公式文本/引用，不宣称重算。未覆盖功能不得因 XLSX 可打开而判定完整保真；也不得通过复杂度选择回到 Mapping 路线。

## 12. 故障语义、回退与恢复

| 所处阶段 | 安全状态与恢复 |
|---|---|
| 外发前 Gate 不通过 | 不上传；返回 blocked 和可行动原因 |
| Provider 请求中断且结果不明 | indeterminate；不自动重试；Current 保持；核实远端请求与资源后决定是否恢复 |
| Provider 有响应但无可下载 XLSX | failed；不伪造文件，不登记有效 Candidate |
| 候选验证/Receipt失败 | Candidate 不接受；用户可修改指令或模型重新生成；不能把失败作为新基线 |
| Candidate 等待用户决定 | Current/Last Valid 保持原版本；Candidate 私有且与原版分开 |
| 用户拒绝 | 保留拒绝记录与原 Current；下一轮基于原 Current |
| Accept/并发失败 | 服务端事务不推进；保留原 Last Valid；重新针对当前 parent 生成/验证，不复用旧确认 |
| 已接受但尚未 Finalize | Candidate 已是 Current；可继续编辑或按用户指令 Finalize |
| Finalize/附件发送失败 | 版本接受不撤销；delivery 标记 failed/pending，同一版本幂等重试 |
| 新入口关闭 | 禁止新的 Route B 请求；保留历史 Candidate、版本、Receipt、审计和附件，只读访问按既有 ACL；不将现存工作簿伪装为旧 Mapping Proposal |
| Schema 已升级 | 关闭入口只是路由回退，不代表 schema/数据已回滚；数据库迁移的反向兼容另需验证，不删除/断开版本链 |
| 已交付文件 | feature flag 关闭不能撤回用户已下载副本；按既有业务撤回/替换流程处理并保留审计 |

关闭新入口不等于安全回退；不得删除历史证据、覆盖 accepted bytes、重写版本父链、降低权限或直接 SQL 调整 current 指针。

## 13. 风险及待评审问题

### 13.1 已知风险

1. Hosted Code Interpreter 外发与留存边界、数据驻留、保留/删除及外联网控制仍需按正式政策批准。
2. 简单文件两轮通过，不证明复杂 OOXML 保真、公式计算正确或大型文件能力。
3. Candidate Validator 的 `FAILED` 必须对应已确认的损坏或硬约束失败；需避免把未知保真或正常序列化差异误归类为损坏。它可以报告可观察的业务差异，但不能通过增加本地 Mapping 条件取代模型内容生产。
4. 首次 V1 的 M1 proof-only 入口是明确代码缺口；需要新受信任初始路径，不得跳过 Receipt/附件/权限绑定。
5. Odoo 公共 `office` edit 目前被 `EXTERNAL_PROVIDER_DISPATCH_ENABLED=False` 关闭；测试 adapter 注入或独立 API 测试不等于生产调度开通。
6. 本地验证和 Agent coverage 不能证明自然语言要求绝对没有遗漏；输出必须按实际证据表述。

### 13.2 实施或生产前仍需完成的事项

1. **SRS 与外发政策：**本地开发/Mock 测试可按独立代码和测试授权进行；真实 Provider 测试及生产外发仍需分别满足 §0.3。负责人需确定托管处理、数据范围、留存/删除及正式 SRS 对齐的具体批准路径。该决定不改变 fail-closed 默认值。
2. **首期支持矩阵：**Implementation Plan/CC 应明确哪些复杂文件对象在不能证明保真但文件安全可读时，可作为 `PARTIALLY_VERIFIED` 交用户决定；哪些确有证据表明会损坏文件时必须硬阻断。不以路线/模板复杂度分流。
3. **后续基线同步：**统一显式 Accept 规则已随本 TDD 冻结；Implementation Plan 和受影响的 CC-01～CB-06 须通过独立版本修订与其对齐后，方可按各自授权进入实施。本轮不修改或新建这些文件。

上述事项不改变本 TDD 的冻结状态；它们是相关实施或生产步骤的前置工作，不构成当前代码实施授权。

## 14. 明确不实施事项

- 不改 SRS、Implementation Plan、CC、代码、配置、数据库或服务。
- 不重开 Route A/C/D 比选；Route B 已由 ADR 冻结选定。
- 不新增公开 Agent Tool；不建立独立 Retriever、Snapshot、CDC、Fingerprint、策略/审批框架。
- 不将 Mapping、`repeat_rows`、`cell_edits` 设回通用 Office 生产前置条件。
- 不在 Odoo 进程执行模型生成代码，不开发本地脚本沙箱，不启用未经批准的 Provider 路径。
- 不把本次独立 TV 结果写为完整 Odoo E2E、UI HVR、复杂文件保真或生产验收通过。
- 不以 Validator、测试断言或模型回答替用户决定业务结果。

## 15. 与既有基线的变更对照

| 主题 | 既有冻结设计 | V2.1.0 处置 |
|---|---|---|
| 首轮内容生产 | 必须由 Mapping/Proposal → M1 产生 V1 | **替换为 Route B 初始 Candidate → 本地验证 → 用户 Accept → 原子登记 V1/Current**；M1 保留兼容，不作通用必经路径 |
| 后续编辑 | Route B + 当前 Current | **保留并强化**：实际 Current 字节为每轮输入 |
| 数据刷新 | 早期 V2.0.3 存在 typed Snapshot/Full/Incremental | **以冻结 CB-05 Change 替换**：`office.retrieve` 薄路由，复用现有 Retriever；不新增 Snapshot/CDC/Fingerprint |
| Provider | Chat Completions + 独立 Responses Adapter | **保留并接线**；普通 Chat Completions 不变；公共 edit Gate 当前关闭 |
| Candidate 验证 | 本地 Validator/Receipt | **保留治理职责**，限定事实与技术安全；不替代 LLM 内容生产或用户业务裁决 |
| 验证/接受关系 | V2.0.3 附录 A 及既有 CB-04 允许低风险条件式接受 | **拟替换**：首次和后续 Candidate 均须明确 Accept 后才成为 Current；PARTIAL 可在知情后接受且不升等；确认损坏/硬失败不可接受。需同步修订受影响的 Plan/CC |
| Finalize | 已接受版本才正式化/交付 | **按冻结 CB-06 amendment 保留**；可交付已接受的 PARTIALLY_VERIFIED，不能重验/升等；附件/Discuss 幂等 |
| TV 证据 | 早期单轮成功；Phase 1B–1D 曾被连接错误阻断 | **追加 2026-11-10 文件级两轮实测**；Odoo 产品闭环、复杂能力仍 UNVERIFIED |

## 16. 修改模块影响与后续工作边界

本 TDD 仅给出设计影响，具体 CC 白名单、字段/schema 和验收分工留待本稿评审后版本化调整：

1. 在单一 `office` Facade 和 `edit_orchestrator` 中接通 Responses Adapter，并支持 raw upload 初始创建分支。
2. 在 `workbook_version_service` 复用版本模型/Receipt，增加可信 Initial Candidate 登记和 Accept 后原子 V1 初始化；保留 M1 proof 路径。
3. 调整 Candidate Validator/Receipt 与新候选来源绑定，使 raw upload 无 parent version 时仍能通过受信任验证契约；不新增公开验证工具。
4. 保持现有 Retriever、Current/Last Valid、CB-02 受控 Accept/Reject、CB-06 Finalize/附件链，不重做存储、版本或普通聊天。
5. 本地开发和 Mock/合成测试按各自授权门禁执行；真实 Provider 测试需满足 §0.3 的测试授权及适用数据授权；生产启用/外发前必须完成正式 SRS/数据政策对齐、生产门禁与 Release 批准。本 TDD 冻结后，仍须版本化修订 Implementation Plan 和相关 CC，并为 Odoo TransactionCase 与真实两轮 UI E2E 提供独立授权和资源计划。

## 17. 变更记录

| 版本 | 日期 | 状态 | 变更说明 |
|---|---|---|---|
| V2.0.3 | 2026-11-08 | FROZEN — HISTORICAL BASELINE | 原冻结 TDD，保留不覆盖 |
| V2.0.4 CB-05 Change | 2026-11-10 | FROZEN — EFFECTIVE | 冻结 Existing Retriever Integration，取代 Data Tool Snapshot 设计 |
| V2.0.4 CB-06 Amendment | 2026-11-10 | AUTHORIZED IMPLEMENTATION AMENDMENT | 对齐 Finalize/已接受 PARTIALLY_VERIFIED 交付语义 |
| V2.1.0 | 2026-11-10 | **FROZEN — APPROVED DESIGN — NOT AUTHORIZED FOR IMPLEMENTATION** | 整合 Route B 冻结决策与两轮 TV；明确环境分层门禁、统一首次/后续 Candidate 显式 Accept、区分保真未知与确认损坏、统一 `office(action="edit")` 服务端源解析并合并重复失败章节；负责人已批准冻结；未修改代码/上游文件 |
