# Office Engine M2 TDD V2.1.2 Amendment — Fileless XLSX Creation (CC-09 As Built)

| 项目 | 内容 |
|---|---|
| 基线 | `TDD_office_engine_m2_v2.1.0_LLM_Native.md`（冻结基线，原文保留） |
| 相关既有修订 | V2.1.1 Tool Boundary amendment；CC-07 Route B simplification 已验收 |
| 适用范围 | 仅限 CC-M2-CB-09 无源 XLSX 创建及其同 Thread 后续编辑 |
| 状态 | **VERSIONED AS-BUILT AMENDMENT — CC-09 OWNER ACCEPTED / CLOSED** |
| 记录日期 | 2026-11-11 |
| 效力边界 | 记录 CC-09 已实施并由负责人验收的行为；不授权生产部署或扩大外发权限 |

## 1. 变更记录与基线保护

本文件是对冻结 TDD V2.1.0 的版本化增补，不改写、不覆盖 V2.1.0、V2.1.1 修订或其历史记录。除本增补明确说明的“没有源工作簿时创建新 XLSX”分支外，原有 Route B、M1 兼容、权限、安全、版本、确认、验证和交付设计继续有效。

CC-07 已关闭的 Route B 简化已由 `docs/implementation/evidence/CB-M2-CB-07/ROUTE-B-SIMPLIFICATION-HVR-REPORT-2026-11-11.md` 记录。普通文件编辑使用一次 `office(action="edit")` 调用，不要求先执行 `plan`/inspection，也不要求 Agent 提交精确 Expected Effect、effect digest、SHA 或 Revision。服务端仍从可信 Thread/Session 解析当前来源，并负责文件字节、权限、版本和 Candidate 绑定。CB-02 中供历史恢复/确认路径使用的 `intent_effect_digest` 存储字段并未整体删除；它不是普通 Route B edit 的模型输入契约。

本增补仅描述 CC-09 的 fileless 创建，不把 CC-07 简化改写为新的架构，也不改变已验收的上传文件编辑路径。

## 2. 无源文件创建语义

### 2.1 工具选择与激活

对用户在 Office Thread 中提出、且没有源附件或已有 Current 的 XLSX 创建请求，Thread 在构造 Agent Provider 请求前启用既有 Route B 工具与指引。公开工具仍为既有 `office` 和独立 `odoo_record_retriever`；不新增 Tool、查询服务或文件生成引擎。需要 Odoo 数据时，Agent 仍以当前用户身份调用 Retriever；Retriever 只读并遵守 Odoo ORM 权限。

### 2.2 `office(action="create")`

Agent 将新建 XLSX 的自然语言任务及已授权的 Retriever 结果交给现有 `office` Facade 的 `create` action。可信服务端完成 Provider 装配、请求约束、文件接收、安全/完整性检查和版本操作。Agent 不提供或决定用户、Thread、Session、Provider 凭据、input SHA、父版本或 Current 指针。

对该来源为空的创建请求：

- 不要求上传模板、M1 Mapping、`repeat_rows`、预置数据行或固定单元格坐标。
- Responses + Hosted Code Interpreter 返回的实际 XLSX 字节是初始文件内容；Odoo 不代替模型决定表格内容。
- 不创建虚构源附件，不记录虚构的输入文件 SHA 或父版本；初始版本准确记录为无父来源的 fileless 创建。
- XLSX 容器/可读性及现有安全、资源和版本绑定检查按既有能力执行。`FAILED`、无效或危险文件不得登记或交付。
- 必要技术检查通过后，服务端将实际输出登记为 V1、Current 和 Last Valid，设置初始 Revision，并沿用现有附件及 Thread 交付机制；fileless 创建不要求再走 Candidate/Accept。
- `PARTIALLY_VERIFIED` 可按 CC-09 已接受范围交付，但必须披露验证等级及未验证范围。直接创建、用户查看或后续 Finalize 均不得提升原始验证等级，也不能将模型声明当作业务正确性证明。

### 2.3 后续编辑

同一 Thread 后续要求修改该工作簿时，服务端以已登记 V1/当前 Accepted Current 的真实附件字节作为输入，校验其来源版本及 SHA。后续修改继续沿用既有 Route B 规则：Provider 输出非 Current Candidate；用户 Accept 才推进 Current/Last Valid/Revision，Reject、失败或 stale 不推进。创建路径的直接 V1 登记是仅适用于无源新建的已裁决语义，不改变已有文件的 Candidate → Accept/Reject 生命周期。

Finalize 继续只交付对应 Accepted Current 的真实文件字节，不重新生成内容；既有附件权限与 Thread 交付机制保持不变。

## 3. Trust Boundaries

- 用户、Thread、Retriever 权限和公司隔离来自 Odoo 认证上下文及既有 ORM 规则。
- Agent/RPC 输入不能开启外发、指定 Provider、伪造附件/哈希/父版本或推进 Current。
- 通过 Retriever 获得数据不自动等于允许将其发送给外部 Provider；适用的数据外发授权仍须满足。CC-09 不新增外发策略管理系统，也不解除现有门禁。
- Provider 成功返回不等于验证成功；验证通过不等于用户接受；fileless 初始登记是 CC-09 对无源创建的明确受控流程，不构成一般编辑 Candidate 的自动接受。
- 已确认损坏、权限失败及其他不可绕过技术约束必须阻断；对无法完整验证的工作簿如实保留 `PARTIALLY_VERIFIED`。

## 4. 与冻结 TDD 条款的最小关系

本增补对冻结 TDD 的适用方式如下：

| 基线主题 | CC-09 增补后的适用语义 |
|---|---|
| V2.1.0 §0.2、§1.1–1.2：原始上传文件的首轮编辑及 Candidate/Accept | 对有源上传编辑保持原文；增加独立的无源 `create` 分支，不把两种来源混为一条生命周期。 |
| V2.1.0 §2：`office` 与 Retriever | 继续复用现有工具；`office` 加入 `create` action。无需新增公开 Tool。 |
| V2.1.0 §4、§8：Candidate、Accept、Current 和 Finalize | 有源编辑和所有后续编辑维持原规则；仅无源创建可在技术门禁通过后直接登记 V1/Current 并交付。 |
| V2.1.0 文件来源及版本绑定 | Fileless V1 明确无输入附件、输入 SHA 和父版本；后续编辑仍必须绑定其实际输出附件和 SHA。 |

更早的 SRS/TDD/Implementation Plan 文件仍按原样保留；CC-09 的范围豁免和验收结果见冻结的 CC-09 及 `FR-M2-CB-09.md`。本文件不追溯修改既有基线，不声明所有上游文件已被重写或重新冻结。

## 5. 实际实现与验收依据

实现对应 `office_engine_m2` 的既有单一 `office` Facade、Thread 工具激活、fileless Session/版本服务、Responses Adapter 和当前验证/交付路径，主要入口为：

- `mymodules/office_engine_m2/models/llm_thread.py:116-220, 290-310`：识别无附件的工作簿请求，在 Agent Provider schema 构造前绑定现有 Office/Retriever 工具，并保持后续 Thread 上下文激活。
- `mymodules/office_engine_m2/models/office_mapping_tools.py:1540-1585`：在同一 `office` Schema 和说明中提供 `create` action。
- `mymodules/office_engine_m2/services/edit_orchestrator.py:150-190, 423-616, 1170-1190`：解析实际 Current、执行无源创建、验证输出并进入 V1 登记/交付；Provider 不可用或文件失败时不创建 Current。
- `mymodules/odoo-llm/llm_openai/services/responses_adapter.py`：承载 Responses API + Hosted Code Interpreter 请求与真实返回文件下载。
- `mymodules/office_engine_m2/services/workbook_version_service.py` 与 `candidate_validator.py`：复用现有版本、SHA、typed Receipt 和 Candidate/Current 服务边界。

实现文件及边界详见 `IHR-M2-CB-09.md`。自动化结果见 `ATR-M2-CB-09.md`；真实 Provider/UI 和 XLSX 回读证据见 `HVR-M2-CB-09.md` 与 `evidence/CB-M2-CB-09/`。

已记录的两组主要端到端证据：

1. 合成文件less 创建 V1 → 同 Thread edit Candidate V2 → 用户 Accept → Finalize/附件下载。V2 的 Provider 输入 SHA 与 V1 输出 SHA 相同，Candidate 阶段不提前推进 Current；验证等级为 `PARTIALLY_VERIFIED`。
2. 真实 Discuss 用户请求读取 5 条当前用户可访问的产品记录并生成文件：现有 Retriever → `office(create)` → 真实 Responses/Hosted Code Interpreter → V1/Current → Discuss 附件下载和独立 XLSX 对比。记录的输出 SHA 为 `f84d034b2e3a7cb2d3a010a53dffa02fb169ee9027e4902a5d5a0e98bbd4d8e9`，验证等级仍为 `PARTIALLY_VERIFIED`。

负责人于 2026-11-11 明确作出 CC-09 人工验收通过决定；最终关闭状态记录在 `FR-M2-CB-09.md`。该决定不扩展复杂 Office 特性的全保真声明，也不构成生产发布批准。

## 6. 明确不变的范围

- M1 上传、Mapping、模板填充、预览、附件和 Chat Completions 兼容能力。
- 普通 Route B 文件编辑的 Candidate → Accept/Reject → Current 规则。
- Retriever 的既有只读查询接口及 Odoo ACL/Record Rules。
- Odoo 的文件安全、可信 SHA/版本绑定、Candidate 验证、Finalize 和附件权限。
- 不引入业务语义验证器、Excel DSL、Snapshot/CDC、第二套版本服务或新增公开 Tool。
- 本地验证能力范围和 `PARTIALLY_VERIFIED`/`FAILED` 边界。
