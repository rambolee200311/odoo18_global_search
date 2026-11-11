# CC-M2-CB-07 — Route B End-to-End Integration & Cross-layer Regression

| 项目 | 内容 |
|---|---|
| 项目 | Odoo 18 CE / Office Engine M2 |
| 契约编号 | CC-M2-CB-07 — Route B End-to-End Integration & Cross-layer Regression |
| 版本 | v0.2 |
| 状态 | **CLOSED — UAT PASSED** |
| 技术设计 | Frozen Office Engine M2 TDD V2.1.0；Route B ADR `ADR-OFFICE-20261110-001_v1.0.md` |
| 前置计划 | Implementation Plan V2.0.1 的 CB-07 Cross-layer Regression & Release Readiness；本 CC 将其与 Route B 集成验收合并为唯一 CC-M2-CB-07 |
| 范围 | CB-01～CB-06 兼容性回归、Route B 首次生成与多轮编辑、Accept/Reject、Finalize/附件交付及真实 Odoo UI 端到端集成 |

> 本 CC 已获负责人冻结并进入实施。按 §3 和 §13，实施首先完成 ADR/TDD/Implementation Plan 版本化同步；此授权不自动开启 Provider dispatch、不授权真实数据外发、服务/数据库操作或生产发布。既有工作区改动及历史证据不得清理或覆盖。

## 1. Contract Goal

> 以下首轮 HVR 结果为历史记录；最终关闭依据及当前状态以 §16 为准。

完成 Implementation Plan V2.0.1 原 CB-07 的 Cross-layer Regression & Release Readiness，并将 Route B 集成验收并入同一 CC-M2-CB-07，避免重复契约。范围内既包含 M1/M2 既有能力的跨层兼容回归，也包含 Route B 的 Odoo 产品闭环：用户上传 Office 文件，Agent 使用经授权的 Odoo 数据和 OpenAI Hosted Code Interpreter 生成首个 Candidate；用户明确接受后登记 V1；后续编辑始终以服务端 Accepted Current 的实际字节为输入；用户可接受、拒绝并最终 Finalize/下载正式附件。

本契约遵循 TDD V2.1.0：

- LLM 主导 Office 内容生产与多轮编辑；本地不以 Mapping、`repeat_rows`、模板行或单元格 DSL 作为通用编辑前提。
- Odoo 保留用户/Thread/附件权限、当前 ORM 查询、外发门禁、文件安全、确定性验证、Candidate/版本状态、接受、审计和交付。
- `VERIFIED` 与 `PARTIALLY_VERIFIED` 是独立验证等级。两者仅在当前用户明确 Accept 后才能成为 Current；Accept 不升高验证等级。已确认损坏或硬约束失败为 `FAILED`，不可由 Accept 绕过。
- M1 原有映射、渲染、附件和聊天能力按现有契约保持兼容。

## 2. 范围与复用基线

### 2.1 In Scope

- 接通已存在的 Responses Adapter 与当前获批的 OpenAI Provider/Hosted Code Interpreter。
- 首次原始上传文件 → Candidate → 本地技术验证/Receipt → 用户 Accept → 原子登记 V1/Current。
- 后续以 Accepted Current 实际 XLSX 字节为输入，连续生成下一 Candidate。
- 当前用户通过 Agent 使用独立 Odoo Retriever 读取数据，并将返回结果作为 Route B 编辑上下文；不复制 ORM 查询逻辑。
- 复用现有 Candidate Validator、Workbook Version Service、受控 Accept/Reject、Finalize、`ir.attachment` 和 Discuss Store。
- 真实 Odoo UI 两轮工作簿验收、必要自动化测试与 M1 回归。
- 原 CB-07 跨层回归与发布就绪检查：CB-06 单轮闭环兼容；真实多轮连续编辑（至少值、格式及一项在 TDD 能力矩阵允许的排序/结构操作）；经授权的数据读取后继续编辑；确认、验证、Finalize、下载；超时、损坏候选、验证失败、权限撤销和附件发布失败时 last-valid 保护；M1 Skills、Mappings、用户权限、RenderBridge/Document Request 和普通 Chat Completions 回归。上述是回归与验收，不重复开发 CB-01～CB-06 已交付组件。
- 依 TDD 支持矩阵记录文件特性能力与单次结果；原计划中的 M1 首轮能力作为兼容回归保留，Route B 首次文件内容生产以本 CC 的 LLM Candidate 流程验收，不要求 M1 Mapping 作为 Route B 前置。

### 2.2 Out of Scope

- 新建数据检索服务、Snapshot/CDC/Fingerprint、数据模型或第二套版本/Receipt/审批框架。
- 新建 Excel 编辑 DSL、在 Odoo Worker 执行模型生成代码、或将 Candidate C 作为隐式回退。
- 重写 CB-01～CB-06 已完成范围、M1 Mapping/RenderBridge、普通 Chat Completions 或 Retriever ORM 实现。
- 未获授权的真实业务数据外发、生产部署、生产发布或生产文件处理。
- 以 Mock/TransactionCase 结果替代真实 Provider 或真实 UI 验收。
- 生产发布、扩大既有 CC 的功能范围或重复实现其组件；本 CC 的 Release Readiness 结论不构成 Production Release。

### 2.3 实际代码基线（只读审计结论，不是本轮测试结果）

| 能力 | 状态 | 代码证据及本 CC 影响 |
|---|---|---|
| Responses XLSX transport | `IMPLEMENTED` | `mymodules/odoo-llm/llm_openai/services/responses_adapter.py::ResponsesAdapter.execute` 接收已授权 SDK client、模型、XLSX bytes、指令和资源限制；单次 Responses 请求、关闭自动重试、下载实际文件并作最小 ZIP/OOXML 检查。该 Adapter 不含 Odoo 调度/权限。 |
| Provider 生产调度 | `MISSING / GATED` | `office_engine_m2/services/edit_orchestrator.py::dispatch_office_action` 当前仅允许测试专用注入；其他调用返回 `provider_dispatch_disabled`。`EXTERNAL_PROVIDER_DISPATCH_ENABLED=False` 为 fail-closed。须新增可信服务端依赖装配，不能由 Agent/RPC 参数开启。 |
| `office` Facade | `PARTIAL` | `models/office_mapping_tools.py::office` 已有 `status/retrieve/plan/edit/accept/reject/finalize` action Schema；`dispatch_office_action` 承载动作路由。`retrieve` 与 TDD/ADR 的独立 Retriever 目标冲突，依 §3 先修订设计基线。 |
| Retriever | `IMPLEMENTED` | `llm_tool/models/llm_tool_record_retriever.py` 使用当前 `env` 的 ORM `search_read/read`，保留 ACL/字段权限/Record Rules；现有字段为 `model/domain/fields/limit/offset/order/include_pagination`，带稳定排序及可选分页结果。不得修改其 M1 默认输入输出。 |
| Thread 工具绑定/可见性 | `PARTIAL` | `office_engine_m2/models/llm_thread.py::_office_bind_tools` 绑定 Retriever、office 及历史 M1 工具；`_prepare_chat_kwargs` 在已有 versioned Current 时只向模型暴露 `office`。Route B 目标需要同时暴露既有 Retriever 和 `office`，且只在适用 M2 Thread 中隔离 M1 工具。 |
| 首次 Candidate/V1 | `MISSING` | `edit_orchestrator::_resolve_current` 要求已存在 Accepted Current；当前 `register_initial_v1` (`workbook_version_service.py`) 依赖 M1 验证证明。须新增受信任的初始 Candidate 与 Accept→V1 服务路径，不能伪造 M1 proof 或直写 Current。 |
| 后续 Candidate/接受 | `PARTIAL` | `register_candidate`、`accept_verified_candidate`、`reject_verified_candidate` 可复用；当前 `review_candidate` 从 Thread 工具历史取 Candidate 且适配后续 edit。需扩展支持初始 Candidate，并校验 CC-M2-CB-07 规定的 Candidate ID 与服务端绑定一致。 |
| Validator/Receipt | `IMPLEMENTED — LIMITED` | `candidate_validator.py` 及 `office_verify` 负责确定性安全/文件检查和 typed Receipt；须复用等级语义，不能扩张成内容生产器或通用自然语言证明器。 |
| Finalize/附件/UI 消息 | `IMPLEMENTED / VERIFY INTEGRATION` | `finalize_accepted_current`、`record_finalize_reference` 和 `llm_thread.py` 的 `office(action="finalize")` Store 消费路径已存在。复用并由本 CC 的端到端验收验证，不重写附件/版本系统。 |
| 当前 Candidate B 工具列表 | `CONFLICT` | 代码对已有 Current 过滤为仅 `office`，而本 CC 要求两个独立公开工具。需先完成 §3 的 TDD/ADR 修订，并随后调整 Thread 绑定及可见性。 |

## 3. 工具架构与上游最小修订（实施前置项）

本 CC 的目标为两个各司其职、均可由 Route B Agent 调用的既有公开工具：

1. `odoo_record_retriever`：只读 Odoo 查询。保持现有 `llm.tool.execute()`、ORM 权限、字段、domain、排序、分页和值序列化契约；不由 Office 重复查询。
2. `office`：文件 edit、Candidate 接受/拒绝和 Finalize/Delivery。Retriever 返回的数据通过原生 Tool 调用结果提供给 Agent，再由 Agent 决定是否将必要结果用于后续 Office 编辑。

这与当前冻结上游有直接冲突，不能靠 CC 静默覆盖：

| 冻结文件/条款 | 当前规则 | 本 CC 目标 | 实施前最小处置 |
|---|---|---|---|
| TDD V2.1.0 §0.2、§1.1、§1.2 | 对 Agent 仅公开 `office` | 保留独立 `office` 与 `odoo_record_retriever` 两个工具，各自职责不变 | 版本化 TDD amendment：修订工具数量/组件关系及架构图，不新增第三个工具或查询框架 |
| TDD V2.1.0 §2.1 | Agent 只见一个 `office` Tool | Route B Thread 同时向 Agent 提供 `office` 与既有 Retriever | 修订 Agent 可见工具边界；明确 M1 既有调用方式兼容 |
| TDD V2.1.0 §2.2、§2.3 | `office(action="retrieve")` 作为 Retriever 唯一公开路由 | Retriever 仍独立调用；`office` 不代理数据查询 | 删除/改写 `office.retrieve` 及其“唯一入口”表述，记录 Retriever 原生参数、返回与权限契约 |
| TDD V2.1.0 §10、§11.3、§14、§15 | 单一公开 Tool、Office 含 retrieve、不得另公开 Retriever | Office 文件生命周期与 Retriever 数据读取为两个既有工具 | 同步组件职责、两轮数据流、线程工具可见性、接口/验收表及禁止事项；保留不增加其他公开工具 |
| ADR v1.0 §ARCH-01 / §5 工具入口 | 只公开一个 `office` Tool | 两个既有公开工具独立并存 | 版本化 ADR amendment，限定仅解除“单一公开 office”约束并更新边界；其他 Route B 安全和治理决议保持 |
| Implementation Plan V2.0.1 §10 | 已有 `CC-M2-CB-07 — Cross-layer Regression & Release Readiness` | 将本次 Route B 集成和原 CB-07 范围合并为唯一 `CC-M2-CB-07` | 不另立 CC。实施前以版本化 Plan amendment 合并范围、依赖、验收和证据项，避免重复契约；Plan 不在本轮修改 |

在上述 ADR/TDD 修订及 Implementation Plan 合并 amendment 获批前，本 CC 只能用于评审，不得冻结或实施。双工具架构及合并 CC 编号已按本次负责人指示作为本草案目标；此表列出尚须版本化同步的文件和条款，不是本轮对冻结文件的修改。

## 4. 调用流程和权限边界

```text
认证用户在同一 Odoo Thread 上传/指定工作簿并提出编辑请求
   → Agent 可独立调用 odoo_record_retriever（仅需要 Odoo 数据时）
   → Retriever 按当前用户 ORM 权限返回原有 JSON/分页结果
   → Agent 将本轮意图、必要数据提交 office(action="edit")
   → 服务端从受信任 Thread/Session 解析唯一原始上传或 Accepted Current
   → Responses Adapter + Hosted Code Interpreter 产生真实 XLSX Candidate
   → 本地 Validator/Receipt 记录技术事实及未知项
   → 当前用户明确 Accept / Reject / Revise
   → Accept 通过 CB-02 原子推进；Reject 保持 Current
   → office(action="finalize") 交付同一 Accepted Current
```

- Thread、user、company、Session、source、Current、Candidate 与 attachment 身份由服务端认证上下文及 ORM 记录解析。模型输入不能自选权限主体、来源文件、Current、版本指针或交付附件。
- Retriever 只读；不使用 `sudo()`、不改变业务数据、不接受 Office 层重复实现的 ORM 查询逻辑。查询结果的外发仍受 §7 数据门禁约束。
- `edit` 首次生成：若该 Session 无 Accepted Current，服务端要求唯一且可读的原始 XLSX 上传；生成非 Current Initial Candidate。已有 Current 时，服务端只读实际 Current attachment bytes 并核对 SHA；忽略模型传入的旧版本/替代文件引用。
- Candidate 接受、拒绝、Revision 推进、Finalize 和附件投递均调用现有受控服务；不得通过 ORM 直接写 Candidate/Current/Last Valid/Receipt/delivery 指针。

## 5. Tool Interface Contract

### 5.1 `odoo_record_retriever`

`odoo_record_retriever` 是独立的已注册工具，本 CC 不改它的公开名称、执行方法、输入/输出格式或 M1 调用行为。现有参数为：

```json
{
  "model": "string",
  "domain": "array",
  "fields": "array<string>",
  "limit": "integer (1..500)",
  "offset": "integer (>=0)",
  "order": "string",
  "include_pagination": "boolean"
}
```

由当前用户执行 ORM `search_read/read`，沿用 ACL、字段访问权、Record Rules 和多公司约束；保留现有记录 ID、序列化值与分页回包。工具错误按现有错误处理返回，不通过 `office` 代理查询。

### 5.2 `office` JSON Schema

文件生命周期动作统一经现有 `office` Tool。Schema 须 `type=object`、`additionalProperties=false`；不能含 `user_id`、`thread_id`、`session_id`、`company_id`、原始附件 ID、Current ID、`confirmed=true`、Receipt 可信标志或任意 `delivered=true`。当前用户原始意图由认证 Thread 中最新用户消息取得，不采信模型传入的替代文本。

契约层输入形状（嵌套的 `interpretation`、`expected_effect`、`model_risk_claims` 子 Schema 复用 TDD V2.1.0/现有 `office` 定义，不另造 DSL）：

```json
{
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "action": {"type": "string", "enum": ["status", "plan", "edit", "accept", "reject", "finalize"]},
    "candidate_version_id": {"type": ["integer", "null"], "minimum": 1},
    "interpretation": {"type": ["object", "null"]},
    "expected_effect": {"type": ["object", "null"]},
    "model_risk_claims": {"type": ["array", "null"]},
    "confirmation_required": {"type": ["boolean", "null"]},
    "confirmation_reason": {"type": ["string", "null"], "maxLength": 2000}
  },
  "required": ["action"]
}
```

`candidate_version_id` 是不可信的选择/一致性断言，不是授权。服务端仍须从当前 Thread 的持久化 Office tool history 解析最新可审候选，并验证二者完全一致；不匹配、跨 Thread/Session、非最新 parent/revision、错误 SHA 或不可审状态均拒绝。用户 Accept/Reject 决定必须来自认证用户实际消息及现有绑定机制，不得由模型布尔值代签。若现有实现不能同时接受该 ID 并维持此校验，CC 实施须修改 Facade 的最小 schema/dispatch，不得放宽 `review_candidate` 信任边界。

| Action | 输入及解析 | 成功输出 | 主要状态/错误 |
|---|---|---|---|
| `edit` | 必要的 `interpretation`、适用的 TDD `expected_effect` 和风险声明；用户原文及初始上传/Accepted Current 均由服务端解析。首次与后续自动分支。 | Candidate ID/状态、验证等级、Receipt 引用、SHA、父版本/输入 SHA、未验证项、Current/Revision 摘要；候选仍非 Current | `candidate_received`、`verified`、`partially_verified`；歧义 `clarification_required`；权限/策略/技术硬限制 `blocked`；调用/下载/验证失败 `failed`；Provider 响应不明 `indeterminate` |
| `accept` | `candidate_version_id`；决定及必要风险授权由认证用户消息/现有确认记录证明 | 持久状态 `accepted_current`；返回 Candidate/Version、Current、Last Valid、Revision、SHA 和原验证等级 | `candidate_not_found`、`candidate_id_mismatch`、`candidate_not_reviewable`、`workbook_version_stale`、权限/确认绑定失败；拒绝错误不得推进 |
| `reject` | `candidate_version_id`；拒绝来自当前认证用户 | `rejected`；Current/Last Valid/Revision 不变 | Candidate 不存在/不匹配/非当前 Thread 时阻断；不修改有效版本 |
| `finalize` | 仅 `action`；版本、用户、Thread、附件从服务端 Accepted Current 解析 | Finalized/Delivered 状态、文件名、MIME、附件/消息 ID、SHA | 无 Current、权限/SHA/附件/Thread 关联失败时不报交付；重复请求复用既有附件/消息 |
| `status` / `plan` | 沿用既有只读状态和 CB-04 计划绑定行为，不因本 CC 重写 | 当前事实或已绑定计划结果 | 沿用既有 CB-04 状态/错误语义 |

`retrieve` 不再属于 `office` action；TDD/ADR amendment 生效后，数据查询只能通过独立 `odoo_record_retriever`。Office action 不能转发查询或复制 Retriever 逻辑。

### 5.3 输出 Envelope

复用现有公共 Envelope，不新建状态框架。每个结果至少具有：

```json
{
  "status": "completed | confirmation_required | clarification_required | blocked | failed | indeterminate",
  "operation_status": "action-specific string",
  "operation_executed": false,
  "action": "edit | accept | reject | finalize | status | plan",
  "artifact_state": "not_presented | candidate | accepted | finalized",
  "delivery_state": "not_finalized | pending | delivered | failed",
  "validation_result": "VERIFIED | PARTIALLY_VERIFIED | FAILED | null",
  "candidate_version_id": "integer or null",
  "version_id": "integer or null",
  "input_sha256": "hex or null",
  "output_sha256": "hex or null",
  "current_version_id": "integer or null",
  "last_valid_version_id": "integer or null",
  "document_revision": "integer or null",
  "verified_facts": [],
  "model_claims": [],
  "unverified_aspects": [],
  "error_code": "safe stable code or null"
}
```

实际字段应优先复用现有 `_public_result`、AdapterResult、CB-02/03/06 返回字段；缺失值使用 `null`/空列表，不伪造。`completed` 必须区分 Candidate 已生成、已接受、已 Finalize/Delivered；工具成功不等于用户文件已下载。

## 6. Candidate / Current 状态规则

| 状态或等级 | 约束 |
|---|---|
| `candidate_received` | 得到真实非空候选字节并完成 Adapter 最低容器检查；不代表验证完成或 Current |
| `verified` | 对应等级 `VERIFIED`；适用的确定性技术检查通过；仍须用户明确 Accept |
| `partially_verified` | 对应等级 `PARTIALLY_VERIFIED`；硬门通过但明确列出未知保真/效果；用户可知情 Accept/Reject/Revise；Accept 不升等 |
| `failed` | 有证据确认文件损坏、必要结构破坏或权限/策略/资源/SHA/版本等硬约束失败；不可接受、不可由用户确认放行 |
| `stale` | 输入 Current、父版本或 Document Revision 已改变；不可接受，必须基于新 Current 重新编辑 |
| `rejected` | 用户拒绝；Current/Last Valid/Revision 不变 |
| `accepted_current` | CB-02 原子接受后的持久状态；响应可称 accepted，但底层状态和验证等级保持准确 |
| `finalized` / `delivered` | CB-06 正式交付事实；不重新编辑、不重验、不升高验证等级 |

首次 Candidate 被接受后成为 V1 并设置 Current/Last Valid；后续 Candidate 接受后才推进 Current/Last Valid/Document Revision。任何 `edit`、Provider 成功、验证通过或模型声明都不自动 Accept。Reject、Failed、Stale 和并发失败不改变有效指针。V2+ 输入必须是当前服务端 Accepted Current 的实际附件字节，其 SHA 等于 parent output SHA。

## 7. Provider 与授权门禁

| 阶段 | 允许操作 | 必需授权 |
|---|---|---|
| 文档/本地开发 | 仅在未来独立 Coding Authorization 后修改白名单代码；外部 dispatch 保持关闭 | Coding Authorization；不处理真实文件、不调用 Provider |
| Mock/合成自动化测试 | 本地 Unit/TransactionCase/Browser Simulation；Mock 数据不得伪称真实 Provider | 指定测试库、服务/模块操作授权；数据不离开获批环境 |
| 真实 Provider 集成/HVR | Provider dispatch 默认关闭。取得本次真实集成测试的明确授权后，受控操作人员可通过受信任服务端配置临时启用测试路径，使用固定批准模型和生产适配器调用 Hosted Code Interpreter；测试结束关闭该路径。先核对请求限制、超时、SDK 重试关闭、Usage/费用记录和文件回读 | 单独明确模型/API Project、合成/真实数据范围、请求上限/预算、操作窗口、资源和留存授权；含真实 Odoo 数据时再取得相应数据外发授权。该配置不得由 Agent、RPC、用户或 Tool 参数开启，也不代表生产启用 |
| 生产启用/发布 | 处理正式用户文件/业务数据并开启公开 dispatch | SRS 正式对齐、适用外发/留存政策、运行门禁与 Release 批准；不属于本 CC |

`EXTERNAL_PROVIDER_DISPATCH_ENABLED=False` 是默认状态。未取得真实集成测试授权时保持关闭；取得授权后，只能由受信任操作人员通过受控服务端配置，在获批测试环境和时间窗内临时启用真实集成测试路径，并记录变更与恢复关闭状态。不得由 Agent、RPC、Thread 用户或 Tool JSON 打开；不得把测试启用等同于生产启用。Provider client、model、limits 只由受信任服务端 Provider 配置注入。无有效授权时，Mock/本地实现可按其独立授权验证，真实 API/UI Provider 场景标 `BLOCKED/NOT RUN`。

## 8. 实施范围与文件白名单

以下是预计最小白名单，实施前需以 TDD/ADR amendment 与实际接口审查收敛；不得借此重构无关模块：

| 文件/模块 | 允许范围 |
|---|---|
| `mymodules/office_engine_m2/models/office_mapping_tools.py` | `office` JSON Schema 与 facade action 输入/输出；保留既有权限上下文，移除 `retrieve` 路由仅在 TDD/ADR amendment 生效后 |
| `mymodules/office_engine_m2/models/llm_thread.py` | Route B Thread 的工具绑定/可见性改为两项既有工具；保持 M1 tool visibility、原生 tool loop 和 Discuss Store；不增加第三个公开 Office Tool |
| `mymodules/office_engine_m2/services/edit_orchestrator.py` | 服务端来源解析、初始/后续 edit 分支、可信 Provider dependency 注入、Candidate/accept/reject/finalize 分派及错误 Envelope；保留 closed-by-default gate |
| `mymodules/office_engine_m2/services/workbook_version_service.py` | 复用版本模型、Receipt、ACL/锁和 Accept/Reject；增加可信 Initial Candidate + Accept→V1 的最小事务入口 |
| `mymodules/office_engine_m2/services/candidate_validator.py`、`mymodules/office_verify/` | 仅支持 raw-upload 初始来源绑定和本 CC 所需 receipt 接口；维持 V2.1.0 的 PARTIAL/FAILED 语义，不扩大成内容引擎 |
| `mymodules/office_engine_m2/data/office_tools.xml` 或工具初始化定义（若实际必要） | 只修复两个既有工具可用/注册关系；不得复制 Retriever 或新增公开 action/tool |
| 相关 `tests/` | Adapter/服务/ORM/UI 集成和 M1 回归；仅添加本 CC 必要断言 |
| `docs/implementation/IHR-M2-CB-07.md`、`ATR-M2-CB-07.md`、`HVR-M2-CB-07.md`、`FR-M2-CB-07.md`、`evidence/CB-M2-CB-07/` | 原 Implementation Plan CB-07 的唯一实施证据位置；只追加本 CC 实际执行证据，不另建第二套 CC-07/CB-07 记录或覆盖历史记录 |

禁止修改 OpenAI Provider 普通 Chat Completions 语义、Retriever ORM 实现、M1 映射规则、数据策略管理、无关 manifest/schema、生产配置或上游冻结文件。若实际需要增加白名单外文件，停止该修改并提交最小变更申请。

## 9. 实施步骤（冻结/授权后执行）

1. 完成最小 TDD/ADR 修订，并通过版本化 Implementation Plan amendment 将 Route B 集成与原 Cross-layer Regression & Release Readiness 合并为唯一 CC-M2-CB-07；核对现有代码/API，不重复实现 CB-01～06 已完成能力。
2. 建立严格工具 JSON Schema 与 Thread tool visibility 回归：Route B 同时暴露 `office`、Retriever，M1 路径仍按既有规则提供工具。
3. 实现首次源解析及 Initial Candidate/Receipt；以服务端 Accept 一次原子创建 V1/Current/Last Valid，不改变源附件。
4. 将可信 Provider client/model/limits 接入 `office(action="edit")`；首次从原始上传读取，后续从 Current 读取；关闭门禁时明确 blocked，不自动退回 M1。
5. 复用 CB-03 验证及 CB-02 Accept/Reject；提供候选、未知项和显式用户决定；拒绝/失败/stale 不推进。
6. 复用 CB-06 Finalize/附件/Discuss Store；确认 Finalize 只交付 Accepted Current，重复调用幂等。
7. 运行本契约自动化测试和 M1 回归；取得真实 Provider/Runtime/Browser 独立授权后执行 HVR；更新 IHR/ATR/HVR/FR 和 evidence index。

## 10. 自动化测试与真实 Odoo UI 验收

### 10.1 Unit / Mock Contract

- JSON Schema 拒绝多余字段、伪造 user/thread/session/source/current、`confirmed=true` 和直接写指针字段。
- 两工具注册与可见性：Candidate B Thread 同时可调用独立 Retriever 和 Office；同一 Retrieve 输入/输出及权限与原 Retriever 完全一致；Office 不含 `retrieve`；M1 流程兼容。
- 首次原始 XLSX 只生成非 Current Candidate；Receipt/SHA/source owner/thread/session 绑定；无 M1 proof 伪装；明确 Accept 后原子登记 V1。
- 同一 `office(action="edit")` 在有/无 Current 时分别使用唯一原始上传/Current bytes；无唯一来源时澄清/阻断；无预置数据行可生成，不进入 Mapping/`repeat_rows`。
- `VERIFIED` 与 `PARTIALLY_VERIFIED` 均须明确 Accept 才能推进；PARTIAL 的未知项可见且等级不变；确证损坏和安全硬约束失败为 FAILED 且不可接受。
- Candidate ID 与 server-resolved latest candidate 不一致、跨 Thread/Session、旧 parent/revision、错误 SHA、receipt 伪造/重放、并发接受失败均拒绝推进。
- Reject、Provider failure/indeterminate、Validator failure、stale、接受事务/附件失败保持原 Current/Last Valid/Revision。
- V1→V2→V3 每轮 input SHA 对应前一 accepted output SHA；V3 保留 V2 实际字节中未修改内容。
- Finalize 只处理当前 accepted version；实际附件下载 SHA 匹配；重复 Finalize 不重复生成附件或消息。
- 原 M1 Mapping/RenderBridge/Document Request/附件权限/Finalize 和 Chat Completions content/tool_calls/streaming 回归。
- 原 Implementation Plan CB-07 的跨层回归项：M1 首轮功能兼容、CB-06 单轮闭环、读取授权数据后继续编辑、Candidate/确认/验证/Finalize/下载链路，以及超时、损坏候选、权限撤销和附件发布失败恢复。按所属契约与本 CC 的 Route B 影响范围分层报告，不重新实现既有组件。
- 原 CB-07 真实连续编辑场景：获批真实 Responses API 下 V1→V2→V3→V4；至少包含值修改、格式修改及一项 TDD 能力矩阵支持的排序/结构操作。每轮输入必须是上一轮已接受文件，并核对 SHA、实际差异、父链和独立回读；不支持或安全拒绝不算编辑成功。

### 10.2 Odoo TransactionCase / 集成

- 现有 `odoo18ce` 或负责人指定的非生产数据库；测试前核对连接目标并确认清理/事务边界，禁止假定可操作共享库。
- 当前用户 ACL、Record Rules、多公司、附件私有性、Retriever 只读和跨用户/thread/session 越权拒绝。
- Initial Candidate、Receipt、接受与版本事务；真实 Odoo ORM 状态证明 Current、Last Valid、Revision、input/output SHA 和父链正确。
- 失败事务、并发/Stale、重复调用幂等、消息投递失败后的 last-valid 恢复。
- 模块升级按独立运行授权执行，不把测试源码、Mock 或旧日志当本轮 PASS。

### 10.3 必需真实 Odoo UI / Agent 两轮闭环（HVR）

在获批非生产 Odoo、合法用户会话和真实 Responses/Hosted Code Interpreter 路径下，同一 Thread 完成：

1. 上传只有表头、没有数据行的中性合成 XLSX；用户要求填入已授权的测试数据（默认优先使用合成 Odoo 数据）。
2. Agent 直接调用 `odoo_record_retriever` 查询必要字段；检索结果 ID/值为真实工具返回，不由模型伪造或由 Excel 行号代替记录身份。
3. Agent 调用 `office(action="edit")`。服务端识别首次来源，Provider 生成真实 XLSX，Candidate 有 SHA/Receipt/未验证项；Candidate 不成为 Current。
4. 用户从实际 UI 查看/下载 Candidate，并明确 Accept。只读 ORM 证据证明 V1/Current、Last Valid、Revision 和字节 SHA 一致。
5. 同一 Thread 第二轮再次调用 Retriever（按第一轮记录 ID 精确查询补充数据）；随后调用 `office(action="edit")`，服务端读取 V1 Current 的真实字节生成 Candidate V2。
6. 独立回读 V2，检查用户要求的新增内容、原有内容、公式/工作表按已证能力矩阵；确认输入 SHA=V1 output SHA。用户明确 Accept 后，Current/Last Valid/Revision 推进至 V2，验证等级不改变。
7. 为覆盖原 CB-07 的多轮验收，同一 Thread 再以 V2 为输入请求一次格式调整，生成并接受 V3；独立检查 V2 的未修改内容保留和 SHA 父链。
8. 再以 V3 为输入请求一项 TDD 能力矩阵支持的排序或结构操作，生成并接受 V4；检查实际文件差异、父链和独立回读。若工作簿不具备适用结构或特性未获支持，记录 `NOT SUPPORTED/NOT RUN`，不得把安全拒绝算成功。
9. 生成另一个合成 Candidate 并由用户拒绝，验证 Current/Last Valid/Revision 保持 V4。对已接受 V4 执行 Finalize，在同一 Thread 看到附件卡并实际下载；下载 SHA 等于 V4 output SHA，独立解析通过。

不得用直接 ORM 写 Candidate/Current/接受/拒绝/Finalize 状态，不得以服务函数、Mock Provider、TransactionCase、模型回复或手工修正下载链接冒充 UI/真实 Provider HVR。UI 可用已授权的真实浏览器或 Playwright 合法测试会话；报告注明执行方式、是否自动模拟用户和每个阶段证据。不能安全获得登录态、外发授权或运行资源时，标记 BLOCKED/NOT RUN，不猜测密码、不复制未经批准的 Cookie、不绕过 Provider 门禁。

### 10.4 HVR 证据

每阶段记录：Thread/message/tool-call IDs、Retriever 参数与记录 ID、Candidate/version ID、parent、input/output SHA、ValidationReceipt/result、Current/Last Valid/Revision、用户 Accept/Reject 消息、Provider response/tool/file/container IDs（可得时）、Usage/费用可见性、附件/下载及独立回读、错误/清理状态。真实联系人或客户数据只有获得具体外发授权才可发往 Provider；未授权则使用合成数据。

### 10.5 合并后的 Cross-layer Regression HVR

§10.3 的同一段 V1→V4 UI 流程已经同时满足“两轮联系人/数据补充业务闭环”及原计划的真实多轮值、格式、结构验收，不重复执行。另执行并记录原 Implementation Plan CB-07 的其余综合回归：

- 回归 M1 Skills/Mappings/RenderBridge、Document Request、附件权限及普通 Chat Completions；报告历史失败影响，不删除历史证据或以跳过用例声称全绿。
- 对 Provider 超时/状态不明、损坏候选、验证失败、权限撤销和附件发布失败，使用获批故障注入/测试环境验证 last-valid 保护及恢复。不得人为制造不受控的真实 Provider 费用或破坏共享数据。

这些项目属于本合并 CC 的 Cross-layer Regression & Release Readiness，不另建 CC；真实 Provider、数据库、Runtime、Browser 和业务数据仍受各自授权门禁约束。

## 11. Acceptance Criteria

须全部满足，方可提交 `READY FOR FINAL ACCEPTANCE`：

1. TDD、ADR 和 Implementation Plan 已完成批准的版本化同步：明确双工具边界，删除/改写 `office.retrieve` 唯一入口条款，并将 Route B 集成与原 CB-07 跨层回归合并为唯一 CC-M2-CB-07；不存在未处置的冻结基线冲突。
2. Candidate B Agent Thread 可独立调用既有 `odoo_record_retriever` 和 `office`；M1 Retriever/Mapping/Chat Completions 兼容回归通过；Office 不重复执行 ORM 查询。
3. `office(action="edit")` 自动识别首次原始上传或后续 Accepted Current，首次及多轮都由真实 Provider 产生 XLSX Candidate；生产依赖仅由受信任服务端注入。
4. 首次和后续 Candidate 均不自动进入 Current；明确 Accept 才经 CB-02 原子推进；PARTIAL 原级接受，FAILED/损坏/security gate 不可绕过；Reject/Stale/失败 Current 不变。
5. Finalize 只交付 Accepted Current，重复交付幂等；Thread 附件卡可访问，实际下载 bytes SHA 与 accepted output SHA 一致。
6. 必要 Unit、TransactionCase、M1 回归通过且本轮测试数、失败、错误、跳过和数据库升级结果可复核；真实 Provider 与真实 UI 在同一连续 HVR 中完成 §10.3 的两轮数据补充、V1→V4 值/格式/结构编辑、拒绝、Finalize 和下载断言。
7. IHR、ATR、HVR、FR 与 evidence index 完整；区分 Contract/Mock、Odoo ORM、真实 Provider、Browser/UI、下载/独立回读层；未运行项不标 PASS。
8. 全程不修改 Odoo 业务数据；任何真实业务数据外发均有相应授权；没有改写历史证据、清理工作区或绕过 dispatch Gate。

`Contract Verified`、`Integration Pending` 与 `Final Accepted` 分层报告。真实 E2E 尚未运行时，即便单元/ORM 测试通过，也不得报告本 CC Final Accepted。负责人作出最终接受；Final Accepted 不等于 Production Release。

## 12. 回退与恢复

- Provider 调度保持 fail-closed。关闭新的 Route B dispatch 后，已有 M1 流程、Candidate、Accepted Current、历史附件和审计记录仍按原权限可读；不得删除版本链或把它伪装成 M1 Proposal。
- Provider 超时且状态不明时记录 `indeterminate`，不盲目重试。Candidate 生成、Validator、Accept、消息或下载失败时保护 last-valid；只在已证明幂等的阶段恢复。
- 接受/并发失败按现有 CB-02 事务/锁策略回滚；保留父版本，不覆盖源附件，不把失败 Candidate 作为下一轮输入。
- 已升级 Schema 后关闭 dispatch 仅关闭新入口，不自动回滚迁移；回退不得清理或重写数据。任何模块升级/运行实例回退须单独批准并核验兼容性。
- 已交付/下载的外部副本不能由关闭 Feature Gate 撤回；按正式治理流程处理。

## 13. Owner Decisions / 实施前置条件

1. **工具架构变更批准：**负责人须批准解除 ADR §ARCH-01 单一公开 `office` 限制的最小版本化 ADR amendment，以及 §3 所列 TDD V2.1.0 amendment；批准本 CC 草案本身不自动修改已冻结上游。
2. **合并计划生效：**已决定本工作并入原 CB-07，不另立契约。实施前须通过 Implementation Plan amendment，将原 Cross-layer Regression & Release Readiness 的依赖、验收和证据要求与 Route B 集成范围合并到唯一 CC-M2-CB-07；本草案不修改冻结 Plan。
3. **运行环境和实际 UI：**实施前明确非生产 Odoo 数据库、测试身份、浏览器/Playwright 登录方式、模块升级与服务重启授权；本草案不授权触碰任何实例。
4. **真实 Provider 调用：**实施前另行授权 API Project、固定模型、文件/数据范围、请求数、预算/费用边界、超时、操作时间窗及远端留存/删除条件。合成数据 API 调用与真实业务数据外发分开授权；真实集成测试须由受控服务端配置临时启用 dispatch。
5. **支持矩阵：**执行中遵循 Frozen TDD 的已验证/未验证分类；若实际工作簿特性触发“未知”或“损坏”分级争议，先记录具体事实，不在 CC 实施者层面扩大/缩小验证政策。

第 1、2 项属于冻结设计/计划的版本变更门；未完成前不得开始依赖双工具结构或合并范围的编码。第 3、4 项分别是运行环境和 Provider/数据外发门禁，不由 Coding Authorization 自动授予。

## 14. Stop Conditions and Handoff

遇到以下任一情况，停止对应子项并报告事实，不扩范围：冻结 TDD/ADR 冲突未批准；Retriever/Office 工具权限边界无法保持；SRS/Provider/数据外发授权缺失；Current/Receipt/SHA/Revision 不一致；已确认文件损坏；生产代码无法以当前可信配置创建 Provider client；UI 登录、数据库、运行服务或模块升级无授权；需要修改白名单外文件或新增安全/业务框架。

可以继续独立完成、不依赖外部 API/数据库/生产服务的 Mock 合同工作（仅在未来 Coding Authorization 覆盖后）。全部范围通过后提交 `READY FOR FINAL ACCEPTANCE` 和证据索引；不得自行标为 Final Accepted 或 Production Released。

## 15. 变更记录

| 版本 | 日期 | 状态 | 说明 |
|---|---|---|---|
| v0.1 | 2026-11-10 | **DRAFT — NOT AUTHORIZED FOR IMPLEMENTATION** | Route B 集成初稿，尚未并入原 CB-07。历史文件保留为 `CC-07_Route_B_End-to-End_Integration_v0.1.md`。 |
| v0.2 | 2026-11-10 | **FROZEN — AUTHORIZED FOR IMPLEMENTATION** | 按评审决定统一为 CC-M2-CB-07，合并原 Cross-layer Regression & Release Readiness；明确双工具所需 ADR/TDD 最小修订及授权后受控服务端 Provider 启用。负责人批准冻结并进入实施；上游基线通过独立版本化 amendment 同步。 |


## 16. Owner-Approved Closure Record — 2026-11-11

**最终状态：`CLOSED — UAT PASSED`**，依据负责人本轮明确关闭决定。

关闭标准按负责人决定收敛为：普通 XLSX 多轮编辑、用户 Accept/Reject、Finalize 与可交付文件链路通过；不要求本 CC 覆盖全部 Excel 特性。该关闭记录不改变已冻结 TDD/架构，不表示所有复杂工作簿结构均已验证，也不构成生产发布授权。

验收证据：

- Codex 真实 UI HVR V4、V5、Reject、Finalize：见 [`evidence/CB-M2-CB-07/ROUTE-B-SIMPLIFICATION-HVR-REPORT-2026-11-11.md`](evidence/CB-M2-CB-07/ROUTE-B-SIMPLIFICATION-HVR-REPORT-2026-11-11.md)，含 Candidate 3016–3018、独立回读和下载证据。
- 8091 真实人工 UAT 三轮联系人、地址和国家编辑：见 [`evidence/CB-M2-CB-07/HVR-RUN-010-8091-human-uat-20261111.md`](evidence/CB-M2-CB-07/HVR-RUN-010-8091-human-uat-20261111.md)。其中人工操作结论来自负责人报告，Thread/ORM 版本轨迹及 XLSX 字节回读作旁证。
- Odoo 全量回归：`tests.result` 为 236 tests、0 failed、0 errors，见 [`evidence/CB-M2-CB-07/ATR-RUN-042-full-regression.log`](evidence/CB-M2-CB-07/ATR-RUN-042-full-regression.log)。分模块 `tests.stats` 为 252 + 28，与最终计数 236 不一致，原因未解释，按已知限制保留。

已知限制继续有效：候选验证等级保持 `PARTIALLY_VERIFIED`；未覆盖的复杂 Excel 特性不因本次关闭而获得完整保真承诺；测试统计差异保持未解释。历史失败记录仍保留，不用本次成功结果覆盖。
