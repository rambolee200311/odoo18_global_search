# CC-M2-CB-04 — Intent / Confirmation / Edit Orchestration

## 文档信息

| 项目 | 内容 |
|---|---|
| 项目 | Odoo 18 CE / Office Engine M2 — Candidate B |
| 契约 | CC-M2-CB-04 — Intent / Confirmation / Edit Orchestration |
| 版本 | v0.2 |
| 状态 | **FROZEN V0.2 — IMPLEMENTATION BLOCKED PENDING UPSTREAM AMENDMENTS** |
| 权威设计基线 | `docs/design/TDD_office_engine_m2_v2.0.2.md` — FROZEN，待本 CC 列明的正式 Amendment 生效 |
| 实施编排基线 | `docs/implementation/IMPLEMENTATION_PLAN_office_engine_m2_v2.0.1.md` — FROZEN，待本 CC 列明的正式 Amendment 生效 |
| 上游需求 | `docs/requirement/SRS_office_engine_m2_ai_mapping_v1.1.0.md` — FROZEN；真实 Candidate B Provider 外发范围待正式对齐 |
| DDD | 未发现独立冻结的 Office Engine DDD；TDD 将 DDD 记录为 N/A |
| 前置组件 | CC-01 Final Accepted；CC-02 Final Accepted（技术范围）；CC-03 Final Accepted（技术实现范围） |
| 实施授权 | 负责人于 2026-11-08 批准冻结并要求进入实施；但 §12.2 A–C 的 TDD/Plan/CB-02 Amendment 尚未生效，且尚无 CC-04 专项非生产数据库/模块测试授权，故代码执行门仍关闭。 |

> 本版本采纳已确定的 D-01 至 D-07 设计方向，不再把这些方向作为开放选项。它记录需要版本化修订的上游契约，但不修改或替代冻结文件，也不把尚未生效的 Amendment 当作已生效能力。

## 1. 治理、权威依据与当前实现审计

### 1.1 权威依据与范围

| 来源 | 当前基线 | CC-04 约束 |
|---|---|---|
| SRS M2 V1.1.0 | FROZEN；以 Mapping/M1 为现行产品基线，并保留文件处理、安全和数据最小化要求 | Candidate B 的真实文件外发及连续编辑须正式对齐。SRS 事项保留，但不阻止本 CC 起草或经单独授权的 Mock/合成数据本地验证；不构成真实 Provider 外发许可。 |
| TDD V2.0.2 | FROZEN；§4 意图/风险确认，§5 版本状态，§6 验证及接受，§8 逻辑接口 | 作为当前行为语义，直到 Amendment 生效。尤其 TDD 目前允许 `VERIFIED` 后接受为 Current；CC-04 将按 D-01 改为条件式接受，须先修订 TDD。 |
| Implementation Plan V2.0.1 | FROZEN；§7 定义 CB-04；CB-04 多轮编排使用 Mock Provider + 实际 Version Service；真实 Provider 多轮归 CB-07；CB-06 负责 Preview/Finalize/Delivery | 本 CC 复用该轮次划分。Plan 需补充条件式接受、审阅/交付边界以及分阶段 Tool Facade/M1 兼容口径。 |
| CC-01 v0.2 | Final Accepted | Responses Adapter 只负责 Provider transport、候选字节和调用元数据；不作业务授权、Validator 验收或 Current 推进。 |
| CC-02 v0.3 / v0.3.1 | Final Accepted — CB-02 技术范围 | Version、附件、SHA、父链、Receipt、Current/Last Valid 和原子接受仍由 CB-02 权威服务管理。每轮 Intent 绑定与条件式接受需要最小 CB-02 Amendment。 |
| CC-03 v0.2 | Final Accepted — CB-03 技术实现范围 | 使用当前冻结 Validator 和 typed ValidationReceipt；CC-04 不重写 Validator，不把 `VERIFIED` 降格为纯 ZIP/解析检查。 |
| Lightweight Validator Architecture Change Proposal v0.1 | DRAFT，未授权 | 不改变 TDD/CC-03；本 CC 仍使用现行冻结验证语义。 |

### 1.2 当前调用链与能力状态

以下为仓库实现核查，不是本 CC 的测试结果。

| 能力 | 状态 | 代码证据与边界 |
|---|---|---|
| M1 Thread、用户消息与 Session 绑定 | `IMPLEMENTED` | `mymodules/office_engine_m2/models/llm_thread.py::_office_active_session`, `generate`, `_prepare_chat_kwargs`, `_execute_tool_call`。 |
| M1 `prepare_context` / Mapping Preview / Proposal Restore / Finalize | `IMPLEMENTED` | `models/office_mapping_tools.py::office_prepare_context`, `office_save_mapping_preview`, `office_restore_proposal_revision`, `office_finalize`；这些是 M1 Mapping/Proposal 行为，不是 Candidate B 编排。 |
| M1 覆盖确认 Gate | `IMPLEMENTED`（仅 M1） | `models/office_mapping_tools.py::_cell_override_confirmation_gate` 绑定消息、用户、Thread/Session revisions、预览/内容指纹及编辑范围；不证明 Candidate B 风险授权已接通。 |
| CB-01 Responses Adapter | `IMPLEMENTED`（组件） | `mymodules/odoo-llm/llm_openai/services/responses_adapter.py::ResponsesAdapter.execute` 可返回 Candidate bytes、SHA 和 Provider 元数据；未从当前 Office Thread 路由调用。 |
| CB-02 Version/Artifact Service | `IMPLEMENTED`（组件） | `mymodules/office_engine_m2/services/workbook_version_service.py::{register_initial_v1,register_candidate,record_validation_receipt,accept_verified_candidate}`；附件权限、父链、SHA、幂等及 revision 由服务维护。 |
| CB-03 Candidate Validator/Receipt | `IMPLEMENTED`（组件） | `services/candidate_validator.py::validate_workbook_candidate` 绑定 Session/Candidate/Parent/Revision 和真实附件字节 SHA，并登记 typed Receipt；没有 Agent 意图解析职责。 |
| Candidate B Thread/Intent/Confirmation/Orchestration 路由 | `MISSING` | `models/llm_thread.py::_OFFICE_TOOL_NAMES` 没有 Candidate B 入口；未发现生产调用 `ResponsesAdapter.execute` 或 `validate_workbook_candidate` 的 Thread 编排。 |
| 每轮用户 Intent 与 Candidate 的持久绑定 | `MISSING` | `office.workbook.version.source_message_id` 在 CB-02 创建时绑定 Session 原始上传消息，不是每轮编辑消息；目前没有专用 `intent_message_id`。 |
| 按授权条件决定是否接受 Candidate | `MISSING`（编排层） | CB-02 `accept_verified_candidate(env, candidate_id)` 在核验 Receipt 后直接进入接受路径，不接收本轮人类授权/确认凭证；无 CC-04 条件式接受决策。 |
| Candidate 拒绝且 Current 不动 | `PARTIAL` | `rejected` 状态存在；但 `office_workbook_version.py::_TRANSITIONS` 不允许 `verified → rejected`，也未发现用于已验证 Candidate 的受控拒绝接口。 |
| Candidate Review / Accept / Reject UI、预览附件、下载和正式交付 | `MISSING`（Candidate B） | `llm_thread.py` 目前转换的是 M1 Preview/Finalize 消息附件卡。候选审阅/浏览器交付归 CB-06；CB-04 只提供受控服务接口和状态数据。 |
| 单一 `office` Tool Facade | `MISSING`（当前 Registry） | `data/office_tools.xml` 注册多个 M1 工具，`llm_thread.py::_OFFICE_TOOL_NAMES` 也列出多个工具；Candidate B 不应再增加长期独立公开 Tool。 |
| Candidate B 全链路 ACL/RPC/附件体验 | `UNKNOWN` | 组件层有当前 ORM/附件权限检查，但没有 Candidate B Thread/UI 路径可验证端到端访问行为。 |

相关 `llm.tool` 实际机制：`mymodules/odoo-llm/llm_tool/models/llm_tool.py` 以 `decorator_model` / `decorator_method` 解析受装饰方法，并按方法签名校验参数；`mail.message::_execute_tool_with_context` 从当前 Thread 的 `tool_ids` 查找工具并以消息上下文执行；Office 的 `models/llm_thread.py` 再按 `_OFFICE_TOOL_NAMES` 过滤可见工具。因此可用一个已注册的 `office` 方法作为 Candidate B Facade，由服务端对有限动作分派到内部服务，不需要把 Validator、Version Service 暴露为额外 Agent Tool。具体 schema/注册改动须纳入获批白名单与测试。

## 2. 目标与非目标

### 2.1 目标

建立一个可执行的通用编排契约：保留并绑定用户本轮意图；由 Agent 产生可审查的解释而非权限证明；由本地 ORM/服务解析当前上下文、检查确认和风险边界；用 CB-01 生成 Candidate、CB-02 登记版本、CB-03 验证实际文件；仅当原始明确授权或有效确认覆盖已验证的实际 Effect 时才自动接受，否则将验证事实交给 CB-06 供人类决定；拒绝、失败或不确定时保护当前有效版本。

### 2.2 非目标

- 不重写 CB-01、CB-02 或 CB-03；只提出本 CC 正确实施必需的最小版本化 CB-02 Amendment。
- 不实现复杂 Expected Effect/Workbook Diff、通用 Excel DSL、任意 Python 执行或新的全局授权框架。
- 不实现 Browser/Preview UI/下载/Finalize；由 CB-06 实现。CC-04 为其提供审阅数据和受控 Accept/Reject/Revise 服务契约。
- 不在 CC-04 执行真实 Provider 多轮验证；Mock Provider + 合成 XLSX + 实际 CB-02/03 Service + 经授权的非生产 TransactionCase 足以构成本 CC 目标验收；真实多轮 Provider 归 CB-07。
- 不把单一 `office` Facade 的逐步迁移扩大为 M1 Tool Registry 全面改造；不把当前仍有多个 M1 工具描述成已达到最终单工具状态。
- 不修改冻结 SRS/TDD/Plan/CC-01/02/03，不改变 M1 Mapping 业务行为。

## 3. 七项已确定设计决议

| 决议 | CC-04 v0.2 采用的契约 |
|---|---|
| D-01 条件式接受 | `VERIFIED` 不是 `ACCEPTED`；明确、低风险且实际 Effect 可证明完全符合授权的 Candidate 可自动接受；需要业务裁决或无法证明匹配的 Candidate 保持非 Current，交由人类选择。绝不对全部 Candidate 强制人工 Accept，也不对全部 `VERIFIED` 无条件自动接受。 |
| D-02 最小 CB-02 Amendment | 复用 `verified` 表示已验证且尚可能非 Current；不新增 `pending_review` 除非现有字段组合不足。增加最小受控接受授权绑定与 verified Candidate 拒绝接口/状态转移；拒绝不改 Current、Last Valid、Document Revision。候选不可成为后续有效父版本。 |
| D-03 每轮 Intent Binding | 保持 `source_message_id` 为首个上传来源；对 Candidate 增加 `intent_message_id` 或等价受控引用。服务端验证 `mail.message` 作者、Thread、Session/公司及可见性。一条 Intent 可有多个 Candidate；消息 ID 不充当幂等键；不重复存全文，不引入 Intent 数据库子系统。 |
| D-04 单一对外 Facade | Candidate B 只通过外部 `office` Tool 的有限动作 schema 调用。内部仍拆分 Intent、Gate、Orchestrator、Adapter、Version、Validator、CB-06。既有 M1 工具继续兼容；其全面迁移单独处理，过渡期间不声称全系统只剩一个公开 Office Tool。Agent 不直接调用内部 Validator/Version Service。 |
| D-05 本地验证边界 | CC-04 目标测试为 Mock Provider、合成 XLSX、真实 CB-02/03 Service 和非生产 Odoo TransactionCase。此契约范围不授权实际数据库操作；每轮 Coding Authorization 必须单列数据库/模块/测试范围。真实 Provider 外发、Browser/UI 和生产数据/留存政策是独立门禁；真实 Provider 多轮归 CB-07。 |
| D-06 Review UI | UI、预览、下载、正式附件交付继续归 CB-06。CC-04 提供 Candidate/Receipt/Verified Facts/Model Claims/Unverified Items/风险授权状态以及 Accept/Reject/Revise 的服务契约。 |
| D-07 不重复确认 | 明确原始请求或确认已涵盖的授权，在 Candidate Effect 独立验证为完全匹配时可直接接受，不再要求同一授权的第二次 Accept。Effect 超范围、存在实质歧义或无法证明符合时，不自动接受，交人类决定。模型不能自称已确认；不信任 `confirmed=True`、`force_override=True`、模型 `user_id` 或任意上下文布尔值。 |

## 4. Intent Contract

### 4.1 最小模型

Intent 不是第二套版本系统或 Excel DSL。它只保存本轮用户请求与服务端上下文的绑定，以及模型提出的解释/未知事项。

```json
{
  "schema_version": "1",
  "intent_message_id": "server-verified-mail-message-id",
  "thread_id": "server-resolved-thread-id",
  "session_id": "server-resolved-session-id",
  "parent_version_id": "server-resolved-current-version-id",
  "intent_digest": "server-computed-canonical-digest",
  "interpretation": {
    "summary": "plain-language interpretation",
    "target_scope": {"description": "generic target/range", "basis": "explicit|inferred|ambiguous"},
    "expected_effect": {"description": "only the stated, verifiable expectation"},
    "assumptions": [],
    "unknowns": []
  },
  "authorization_ref": null,
  "candidate_ids": []
}
```

CB-02 仍是文件版本、父链、真实字节 SHA、revisions、附件和幂等的权威来源；Intent 不复制这些值来建立另一套权威。编排器可读取并传递 CB-02 当前身份用于检查，但持久 Intent 引用使用 CB-02 Candidate 上的 `intent_message_id` / 等价字段以及现有 request/effect digest。

### 4.2 原话、解析和事实来源

- `intent_message_id` 必须由服务端依据当前 Thread 的真实用户消息确定；核验 `env.uid`、消息作者、Thread 归属、Session/公司和访问权限。不要接受模型或 RPC 任意指定的用户/Thread/消息身份。
- 原始用户文字留在已授权的 `mail.message` 中，以引用为准；不另存整段正文。
- `interpretation` 是模型提出的意图解释，不是已验证事实。每个目标/范围应标示其依据为 `explicit`、`inferred` 或 `ambiguous`；模型摘要不能改写成用户原话。
- Verified Facts 仅来自 Odoo ORM、CB-02 实际版本/附件字节或 CB-03 Candidate ValidationReceipt/实际差异。Model Claims 来自 Adapter/Agent 声明；Unverified Items 是未能通过确定性检查的事项。三者对外分别呈现。
- Intent digest 由服务端对规范化的消息引用、解析版本、范围、预期和基线引用计算；它不是授权凭证，不能取代 CB-02 的 SHA/revision/父版本检查。
- 用户下一轮补充或修正产生新的意图请求/digest。历史对话用于理解语境，不是文件内容的权威来源；文件内容只以当前已接受版本为准。

### 4.3 目标范围和预期

- 目标范围表达用户要求和解释精度；实际影响范围由 CB-03 根据真实输入/候选文件核验。
- 可引用用户明确说出的目标位置，但底层不得假设固定坐标、Sheet 名、模板、Odoo 模型或业务字段。
- Expected Effect 复用冻结 CB-03 的只读结构化描述：目标、允许变化、可验证预期及 unknowns。它不描述遍历/计算/写入过程，不成为 Excel 编辑 DSL。
- 如果必要效果未结构化、目标有多解，返回 `clarification_required`；如果文件/差异能验证但业务效果不够精确，依冻结 TDD/CC-03 结果返回 `PARTIALLY_VERIFIED`，不得声称完整语义已验证或据此推进 Current。

## 5. Confirmation Gate 与条件式接受

### 5.1 五种外部结果

| Outcome | 判据 | 行为 |
|---|---|---|
| `completed` | 本次明确阶段已由服务端事实完成；若声称编辑已完成，需 Candidate 验证且符合接受条件；若声称已交付，还需 CB-06 Delivery 事实 | 同时返回真实的 Candidate/version/validation/artifact/delivery 状态；不能只依据工具消息状态或模型回复。 |
| `confirmation_required` | 目标与风险范围明确，但业务影响未由用户原始请求/既有有效授权覆盖 | 显示风险和范围；确认前不启动对应风险编辑，不产生正式副作用。 |
| `clarification_required` | 目标、范围、必要参数或含义有会改变结果的多种合理解释 | 不调用编辑 Provider、不登记可接受 Candidate；请求用户补充。 |
| `blocked` | ACL、Record Rules、公司隔离、外发授权、附件/文件安全、版本、资源或不支持能力失败 | 不得由确认、模型参数或 Tool 参数绕过。 |
| `failed` | 操作失败或结果无法可靠确认 | 保留准确的已知副作用/恢复状态；不得伪报成功或盲目重试。 |

### 5.2 自动执行/接受矩阵

| 条件 | Provider 执行 | Candidate 验证后接受 | 用户操作 |
|---|---|---|---|
| 请求明确、低风险、范围受支持；原始请求可证明授权该修改 | 可执行 | 仅当 CB-03 `VERIFIED` 且实际 Effect 完全匹配服务端绑定的 Intent/授权、当前父版本仍有效、无其他未决风险时，由 CB-02 原子自动接受 | 不额外确认或重复 Accept；随后由 CB-06 按现有范围展示/交付，并准确说明阶段 |
| 风险明确、范围可界定，且尚未授权 | 未确认前不得执行该风险编辑；取得有效确认后可执行 | 若验证后 Effect 完全处于已确认范围，且确认语义已包括该匹配结果的接受授权，可自动接受；若授权只允许尝试编辑而未授权使其成为 Current，则候选保留，交 CB-06 供人选择 | 一次确认即可覆盖执行及其后果的条件必须在确认问题中明示，避免同一事项重复确认 |
| 实际 Effect 超授权、发生实质变化或未能证明匹配 | 候选可以保留为已验证的非 Current Candidate（仅当 CB-03 结果允许并绑定无误） | 不自动接受 | CB-06 展示实际差异和未决事实，由人类 Accept/Reject/Revise；若 `PARTIALLY_VERIFIED`/`FAILED`，受冻结 TDD 限制，不可接受 |
| 意图歧义、必要信息不足 | 不执行 | 不接受 | Clarify；确认不能替代澄清 |
| 权限/安全/资源/损坏/版本/不支持能力失败 | 不执行对应受限动作 | 不接受 | `blocked`；确认绝不绕过 |

自动接受的决定必须来自确定性服务端条件，不由 LLM 自评风险级别或声称 Intent 已被满足。`VERIFIED` 只证明 CB-03 冻结契约范围，既非授权，也非自动接受的充分条件。

### 5.3 确认绑定及执行前重验

对需要业务确认的操作，服务端确认记录至少绑定：

- 从已认证环境得到的用户、Thread、Session、公司范围；
- 当前父版本、其真实附件 SHA、Session/Document revision（由 CB-02 查询并在执行前重验）；
- 每轮用户 Intent 消息引用与服务端 Intent/effect digest；
- 目标/影响范围、操作类别、允许变化、预期及已说明风险；
- 确认所授权的行为：仅允许执行，或在候选效果完全匹配时同时允许接受。

确认由当前 Thread 上用户实际消息/受信服务端交互获得，消息作者和顺序须核实。确认不能是模型参数、`user_id`、任意 context、`confirmed=True` 或 `force_override=True`。确认不可跨用户、Thread、Session、Intent、Candidate、父版本、文件 SHA、revision、效果或范围复用。

执行前必须重新核验用户权限、公司、Thread/Session 绑定、当前父版本/附件真实 SHA、revisions、目标/Effect、确认和资源/数据外发策略。任一绑定变化使确认失效；执行过程中实际候选超出已授权范围时不得接受。`force_override` 如仍作为兼容提示存在，只能触发重试检查，不是授权。

### 5.4 Confirm 与 Accept 不重复

Confirmation 是对风险操作的授权；Accept 是选择让某个具体、真实且已验证的 Candidate 成为 Current。用户原始明确指令本身可构成授权，且在实际 Effect 精确符合该授权时，条件式自动接受，不再多问同一内容。对于风险确认，确认提示必须说明其范围及“若候选经验证完全符合，是否允许成为当前版本”；用户一次决定即可绑定该结果。若真实 Effect 与确认边界不符或事实未知，系统不猜测，应保留 Candidate 并由 CB-06 向人类呈现实际结果供进一步决定。

## 6. Edit Orchestration

### 6.1 服务链及契约

```text
User Intent
  → Intent Binding / Context Resolution
  → Clarification or Confirmation Gate
  → CB-01 Responses Adapter (CC-04 tests use Mock)
  → CB-02 Register Candidate
  → CB-03 Validate Candidate / typed Receipt
  → Authorization & Actual-Effect Assessment
      ├─ explicit/confirmed authorization covers verified effect → CB-02 Accept
      ├─ needs human business decision → keep non-current; hand off to CB-06
      └─ technical/security failure → blocked/failed; Current unchanged
  → CB-06 Review / Finalize / Delivery
```

| 阶段 | 负责方 | 输入/输出 | 失败与权威边界 |
|---|---|---|---|
| Intent Binding | Agent 提出解释；Thread/本地服务核验用户消息与归属 | 当前消息、Thread/Session、模型 interpretation → 带 provenance 的 Intent | 模型不能指定可信用户/Session；消息不可见或不属于当前 Thread 为 blocked。 |
| Context Resolution | Odoo 编排服务 + 当前用户 ORM + CB-02 | 解析 owner/company/Session/current parent/file bytes/hash/revision | ACL/Record Rules/附件不可读或 stale 时停止；不得退回上传原件或模型记忆。 |
| Plan（必要时） | LLM 可只读分析；本地 Gate 判断是否足够 | 当前文件副本和 Intent → 操作类别、目标范围、影响规模、assumptions/unknowns | 复杂请求可增加计划调用；简单明确单目标无需额外 Provider 往返。只读计划不写正式附件，不产生 Candidate。 |
| Confirmation Gate | 受信 Odoo 编排服务读取实际用户消息并检查绑定 | 计划/风险 + Intent/父版本 → 允许执行、confirmation_required、clarification_required 或 blocked | 需要确认时不可先提交风险编辑请求；服务端重验证所有绑定。 |
| Candidate Edit | CB-01 Adapter，由本地编排以获批凭据调用 | 当前已接受父版本 bytes + 用户意图/计划 + 资源限制 → 实际输出字节、SHA、Response/tool/file metadata | 返回文本/代码不是文件；异常/indeterminate 不盲重试；Current 不变。 |
| Candidate Registration | CB-02 `register_candidate` 或 Amendment 后的同一受控入口 | 真实 input/output bytes/SHA、parent、Intent 消息引用/digest、幂等键、当前 revisions → `candidate_received` | 父版本/revision/SHA/权限不符拒绝；Intent 消息绑定不可由客户端伪造。 |
| Candidate Validation | CB-03 `validate_workbook_candidate` + CB-02 typed Receipt 登记 | candidate_id、只读 Expected Effect、绑定父/候选字节 → Validation Result、Risk Facts、Receipt | Receipt 仅 CB-03/CB-02 服务端内部注册；`FAILED`/`PARTIALLY_VERIFIED` 不自动接受。 |
| Authorization & Effect Assessment | 本地编排服务 | 用户原始/确认授权、验证后实际 Effect、risk_facts、receipt → auto-accept / review-required / blocked | 使用确定性匹配；未覆盖、不确定或 Effect 越界时不自动接受。 |
| Accept / Reject / Revise | 用户通过聊天；CB-04 仅形成受控服务请求，CB-02 执行权威变更 | Candidate、当前身份、用户选择、绑定授权 → accepted_current 或 rejected | 受当前用户、Thread、Session、父版本、hash、revision、receipt 校验；拒绝不改 Current。Agent 不可自行确认。 |
| Review / Finalize / Delivery | CB-06 | Candidate + Verified Facts + Model Claims + Unverified Items + 决策/授权引用 → 私有预览、正式文件与交付状态 | UI/正式附件仅 CB-06；发布失败不重新编辑、不重复接受，重试同一字节。 |

### 6.2 `office` Tool Facade

- Candidate B 的 Agent 调用只有一个外部 Tool：`office`。Tool 参数使用有限、版本化的动作 schema；每个动作调用内部受控服务，不接收 Candidate Validator 或 Version Service 的裸方法名/任意路由字符串。
- 基于当前 `llm.tool` 实现，最小实现路径是在现有 `office.mapping.tool` 模型增加一个 `@llm_tool(name="office")` 方法；现有 decorator registry 会扫描并同步 Function Tool，按 `(decorator_model, decorator_method)` 和唯一 Tool 名登记。不要同时在 `office_tools.xml` 添加同一方法的重复记录。Thread 以 `tool_ids` 绑定，`mail.message::_execute_tool_with_context` 根据 Tool 名从该 Thread 的工具集查找并调用绑定方法。`llm_thread.py` 的 allowlist/schema/prompt 应按 Candidate B 会话只绑定此 Facade；继续让 M1 会话按现有方式绑定旧 M1 工具，避免破坏兼容性。
- 首期 Candidate B Facade 只接受有限 `action="edit"` 及当前消息的结构化解释/验证描述；不提供模型可调用的 `confirm`、`accept` 或 `reject` 动作。确认和候选决策从真实用户消息/受信 CB-06 交互解析，之后由本地服务生成受控授权。未来动作需独立契约和测试，不接受任意服务名或 payload dispatch。
- Agent 不可直接选择任意内部 Python 方法、传 `env.uid` 或跨 Thread 的资源 ID。Facade 解析身份始终由服务端当前 `env` 和 Thread 消息完成。
- 保留 M1 现有工具方法和既有客户端调用兼容性。新 Candidate B 路径不增加 `office_edit_candidate`、`office_validate_candidate` 等独立公开工具。M1 Tool Registry 的完整迁移为独立后续工作；迁移期间明确记录现存多个旧 M1 工具，不宣称全局 Registry 已经单一化。
- 此 Facade 不实现 CB-06 UI、Finalize、附件下载或 Browser 操作。跨 CC 调用必须使用 CB-06 受控服务接口。

### 6.3 多轮、重试与恢复

- 唯一后续编辑输入是 CB-02 当前已接受版本的真实附件字节；会话文字/Provider previous response id 不得重建文件。
- 每轮用户请求绑定独立 `intent_message_id` / intent digest 和父版本。一个 Intent 可有多个候选；每个候选有独立的幂等键，消息 ID 不能当唯一幂等键。
- 只有已接受 Candidate 成为后续父版本。等待 Review、被拒绝、`PARTIALLY_VERIFIED`、`FAILED`、indeterminate 的 Candidate 均不能成为下一轮文件基线。
- 业务确认与自动接受授权随候选绑定。用户修改目标、范围或预期时，重新计算 Intent digest；旧授权不能因旧 session/thread 状态继续适用。
- Provider 结果不明时，复用 CB-01/CB-02 可核验的请求/候选引用；无可审计结果或安全幂等依据，不自动重新发起。相同 idempotency key + digest 返回既有结果；相同 key 不同 digest 拒绝。
- 用户拒绝：CB-02 只将 Candidate 记为 rejected/终止，Current、Last Valid、Document Revision 不变；后续编辑以当前仍有效版本新建 Intent/Candidate。
- 接受并发竞争：由 CB-02 行锁/原子检查父版本和 revision；一旦 stale，旧 Accept 不得推进，编排返回 stale/blocked 并要求从新 current 重新构造。

## 7. Trust Boundaries 与安全不变量

1. **用户意图**：原始 Thread 用户消息为意图来源；模型 interpretation 是待核实主张，不能授予权限。
2. **身份/ORM**：仅当前 Odoo `env.uid`、ACL、Record Rules、allowed companies、Thread 和附件访问共同决定可读写范围；不使用 `sudo()` 或模型/客户端身份字段绕过。
3. **风险确认**：确认是受信服务端绑定的用户授权，不接受任意 boolean、模型声称或可由客户端注入的 context 作为凭据。
4. **Provider**：按最小化策略只向经批准 Provider 外发当前授权文件；本 CC 默认测试 Mock + 合成数据，不扩大留存/数据政策。
5. **Candidate/Receipt**：Provider 文件是 Candidate，不是 Current；CB-03 Receipt 是独立验证事实，不是用户授权；模型声明不是 Receipt。
6. **版本权威**：只有 CB-02 受控服务能接受/拒绝 Candidate 或推进 Current/Last Valid/Document Revision；Facade 不写这些字段。
7. **交付权威**：只有 CB-06 处理 Preview、正式文件、Thread 附件及 Delivery 状态。`candidate_received`、`verified`、工具 `completed` 均不表示已交付。
8. **结果反馈**：对用户分列 Verified Facts、Model Claims、Unverified Items；服务端 outcome 不能被 Agent 自由文本升格。
9. **可确认性边界**：用户决策可解除已明确范围内的业务风险，不解除 ACL、Record Rule、公司、路径/文件、资源、版本、Validator 或数据外发安全门。

## 8. 状态与失败语义

### 8.1 状态责任

| 事实 | 权威组件 | CC-04 处理 |
|---|---|---|
| Intent 来源、解释、授权引用 | CB-04 Thread/Intent service；用户原文仍在 `mail.message` | 绑定消息身份与版本引用；不复制 CB-02 版本状态。 |
| Provider 请求/候选字节 | CB-01 | 只记录真实执行结果；indeterminate 不视为失败文件或可重发授权。 |
| Candidate、父版本、SHA、文档修订、幂等、Current/Last Valid | CB-02 | 只调受控服务；不 direct ORM write。 |
| Validation Result、Risk Facts、typed Receipt | CB-03/CB-02 | 分开消费；确认/接受不改变验证等级。 |
| 风险授权与条件式接受判定 | CB-04 Gate | 依据真实用户意图/确认与验证后 Effect；需把接受授权作为可信参数交 CB-02。 |
| Preview/UI/正式附件/Delivery | CB-06 | 提供确实已验证的 candidate facts 和受控决定接口；不伪造交付状态。 |

### 8.2 条件式 Candidate 生命周期

```text
candidate_received → verified
verified + matching explicit/confirmed authorization → CB-02 atomic accept → accepted_current
verified + unresolved business choice → remains verified/non-current → CB-06 review
verified/non-current + user reject → CB-02 controlled reject → rejected
partially_verified / failed / stale → never accepted_current
accepted_current → CB-06 finalize/delivery lifecycle
```

CB-02 当前已支持 Candidate 注册、Receipt、Current 原子接受及 `rejected` 枚举，但其 v0.3 接受服务没有授权参数，`verified → rejected` 不在允许迁移中。D-02 的最小 CB-02 Amendment 应优先保留 `verified` 为已验证但可能尚未接受状态，避免无必要的 pending 状态；新增受控条件式接受授权及对已验证非当前 Candidate 的拒绝路径，并核验拒绝前版本/Receipt/权限，确保指针和 revision 不变。若最终实现发现 `verified` 状态不能安全承载待决 Candidate，才提出最小状态补充，不在 CC-04 自行扩表。

### 8.3 失败映射

| 条件 | Outcome | Candidate/Current | 恢复 |
|---|---|---|---|
| 意图/目标歧义 | `clarification_required` | 不调编辑 Provider，不创建 Candidate；Current 不变 | 新用户消息形成新 Intent。 |
| 风险待授权 | `confirmation_required` | 不调相应风险编辑 Provider，不登记 Candidate | 仅收到并验证绑定当前用户的有效确认后重新核验。 |
| 权限/Record Rule/公司/附件/外发安全失败 | `blocked` | 无受限编辑，Current 不变 | 安全条件改变后由用户重新请求；旧授权不复用。 |
| 模型可读但意图不受支持 | `blocked` 或 `clarification_required`（按原因） | 不得降级成窄化操作后称完成 | 明确说明支持边界。 |
| Provider 明确失败 | `failed` | 无接受；Current 不变 | 只有可证明安全的受控重试。 |
| Provider 状态不明 | `failed`，内部标 `indeterminate` | 不盲重试，不伪造 Candidate；Current 不变 | 查询可审计 Response/文件 ID；不能确定则保留父版本。 |
| Candidate SHA/父版本/revision/Intent 绑定失败 | `blocked`/`failed`/stale | 不登记可接受候选，不推进 | 新鲜 context 后新请求。 |
| CB-03 `FAILED` | `failed` | 拒绝，Current/Last Valid 不变 | 修改 Intent/文件后新 Candidate；不得放宽断言。 |
| CB-03 `PARTIALLY_VERIFIED` | `blocked` 或等待澄清（依冻结 TDD） | 不自动接受/正常交付 | 只按冻结 TDD 和另行批准的诊断路径处理。 |
| Candidate Effect 不匹配授权 | `confirmation_required`/Review required | 保持非 Current | CB-06 展示实际 Effect；取得新授权前不接受。 |
| 用户拒绝 Candidate | 用户拒绝终态 | CB-02 标记 rejected；Current/Last Valid/Document Revision 不变 | 后续编辑从仍有效 Current 产生新 Candidate。 |
| CB-02 接受发生 stale/并发失败 | `blocked`/`failed` | 原 Current 仍有效 | 刷新后重新绑定；不能重用过期确认。 |
| Preview/Finalize/交付失败 | `failed`，artifact/delivery 单独记录 | 已接受 Current 不回滚；没有已接受 Candidate 则不造正式附件 | CB-06 对同一已接受版本/字节幂等重试。 |
| Provider 后续 LLM 回复超时 | 依据已持久化阶段报告 | 不回写或抹除已经发生的真实版本事实 | 下一轮从 Odoo 持久状态恢复，不重放已成功编辑。 |

## 9. 与冻结上游的 Amendment 清单

下表是落实已决定方向所需的最小版本化变更，不表示这些变更已获批准/生效。

| 文件/条款 | 当前冻结内容 | 冲突/必要调整 | 最小 Amendment | 发生时点 |
|---|---|---|---|---|
| `docs/design/TDD_office_engine_m2_v2.0.2.md` §5.2、§6.3、§8.1、§8.2 | `VERIFIED` Candidate 可成为 `accepted_current` 并生成 Preview；接口把 verify/accept 合并描述 | 不区分已验证与是否已获授权；没有条件式 Current 推进 | 版本化 TDD：明确 `VERIFIED ≠ ACCEPTED`；只在 Effect 完全被原始明确/有效确认授权覆盖时自动接受；其余保持非 Current 交 CB-06 审阅；拆分验证、接受、交付结果语义。 | **CC-04 Coding Authorization 前** |
| `docs/implementation/IMPLEMENTATION_PLAN_office_engine_m2_v2.0.1.md` §7、§9、M2-BASIC-EDIT/流程图 | Candidate 验证/接受与 Preview/Finalize 的轮次次序依照当前 TDD；CC-06 有 Preview/Finalize/Delivery | 需要体现条件式接受、待 Review Candidate 和对 CB-06 的 handoff，且保持真实多轮 Provider 在 CB-07 | 版本化 Plan：将“自动接受”限定为 authorization+effect match；给需裁决 Candidate 规定非当前 Review；明确 CB-06 只处理显示/最终交付，不重做 Gate。 | **CC-04 Coding Authorization 前** |
| `CC-M2-CB-02_Workbook_Version_Artifact_Service_v0.3.md` / v0.3.1 + `models/office_workbook_version.py`, `services/workbook_version_service.py` | Candidate 只绑 Session 首始消息；`accept_verified_candidate(candidate_id)` 无授权参数；`verified → rejected` 不可迁移 | 缺每轮 Intent 来源与条件式接受/拒绝的原子接口 | 版本化 CB-02 Amendment：新增受控 `intent_message_id` 引用；接受调用接收内部 typed、服务端核验的接受依据（绑定当前 user、Thread/Session、Candidate、parent/SHA/revision、Intent/effect 与授权）；拒绝 verified 非当前 Candidate 的受控接口；拒绝不推进任何 current pointer/revision。复用现有 `verified`，除非不可安全区分。 | **CC-04 Coding Authorization 前；先修订/批准并实现 CB-02 Amendment** |
| `docs/implementation/CC-M2-CB-04...v0.2.md` + `llm_thread.py`, `office_tools.xml`/decorator registry | 当前 Office Thread 提供多个 M1 Tools，没有 Candidate B 入口 | 新路线必须单一 Candidate B `office` facade，同时兼容既有 M1 | 本 CC 新增一个受限 `office` 外部方法/动作 schema；Thread 在 Candidate B 路径只绑定此 Facade；旧 M1 工具保留供既有调用，不在本 CC 做全量迁移。Plan/CC 记录过渡期不等于全局工具已唯一。 | **在本 CC 冻结/编码前固化 Facade 白名单；不是另开完整 M1 迁移** |
| `docs/requirement/SRS_office_engine_m2_ai_mapping_v1.1.0.md` | 冻结的 M1/M2 当前文件处理与数据安全边界；Candidate B 外部文件编辑路线有待正式对齐 | 真实 Candidate B Provider 外发和后续用户编辑需符合正式产品/数据政策 | 版本化 SRS 对齐及数据外发/留存/删除政策批准。此项不阻止 CC-04 起草或在独立授权下进行 Mock/合成文件本地验证；未生效前禁止真实业务文件/数据 Provider 外发。 | **真实 Provider/真实数据外发之前；本地 Mock 代码范围按单独 Coding Authorization** |
| M1 Tool Registry 兼容说明 | XML 有多个 M1 tools；架构目标是一个外部 `office` tool | 不应将完整旧工具迁移拖入本轮，也不能声称已经统一 | Plan/CC 版本化记录 staged coexistence：Candidate B 只用 `office`；旧 M1 tools 暂存兼容；全局 M1 facade migration 独立后续范围。 | 本 CC 冻结前纳入当前 CC 与必要 Plan Amendment；全面迁移后续 |

## 10. 测试矩阵

测试目标为 Mock Provider、合成 XLSX、实际 CB-02/03 service、非生产 Odoo TransactionCase。该计划不等于已授权运行或测试通过。

| ID | 场景 | 必要断言 | 层次 |
|---|---|---|---|
| C04-01 | 明确授权且效果完全匹配 | Candidate 独立验证后自动接受；不重复要求 Confirmation/Accept；当前版本只通过 CB-02 原子接口变化 | Contract + TransactionCase + Mock |
| C04-02 | 实际 Effect 超出用户授权 | 不自动接受；Candidate 非当前；状态及实际差异交 Review/澄清 | CB-02/03 Integration TransactionCase |
| C04-03 | 效果无法充分验证 | CB-03 按冻结策略返回非 `VERIFIED`；不能以模型声明、用户确认或文件可打开冒充完整验证/接受 | Candidate Validator + Orchestrator TransactionCase |
| C04-04 | 意图/目标歧义 | `clarification_required`；不调用编辑 Provider、不登记 Candidate、不改 Current | Contract + Mock |
| C04-05 | 可确认风险未确认 | `confirmation_required`；不发风险编辑请求，不创建可接受 Candidate | Contract + TransactionCase + Mock |
| C04-06 | 有效风险确认 | 绑定用户/Thread/Session/Intent/父版本/hash/revision/scope；执行前重验；只在确认范围运行；匹配授权时不再重复 Accept | TransactionCase + Mock |
| C04-07 | 权限/安全失败 | ACL、Record Rules、公司/附件权限或安全失败不能由任何确认、`force_override`、`confirmed` 或模型身份绕过 | TransactionCase |
| C04-08 | 用户拒绝 | CB-02 受控 rejection；Current、Last Valid、Document Revision 不变；拒绝 Candidate 不可作父版本 | CB-02 Amendment TransactionCase |
| C04-09 | 旧确认、版本/文件 SHA/revision/目标变化 | 原授权失效；执行前阻断或重新确认；不放大授权范围 | TransactionCase |
| C04-10 | Provider 明确失败或 `indeterminate` | Current 不变；无盲重试、重复 Candidate 或伪造文件；状态与费用事实分离 | Mock Adapter + TransactionCase |
| C04-11 | 多轮编辑 | 下一轮使用上一轮已接受的真实 Candidate bytes/ID 为父；旧/被拒 Candidate 不会成为基线 | Mock Provider + 实际 Version Service |
| C04-12 | 重复请求/并发 Accept | 相同幂等键+同 digest 返回同事实；同键不同 digest 拒绝；至多一个 Current 接受 | CB-02 service integration / approved DB transaction tests |
| C04-13 | 每轮 Intent 消息引用 | 原始消息可追溯；校验用户、Thread、Session、公司；伪造/跨 Thread/跨用户消息拒绝；一个 Intent 可多 Candidate；message id 非幂等键 | TransactionCase |
| C04-14 | Verified Facts / Model Claims / Unverified Items | Receipt/diff/ORM facts 与 Adapter/LLM 声明分开；未知/遗漏不能被模型文本转成验证事实 | Contract + TransactionCase |
| C04-15 | 单一 `office` Facade | Candidate B tool schema 只有一个外部 `office` 入口；不暴露 Validator/Version Service；所有动作通过 allowlist 与服务端权限校验 | Tool Registry/Thread TransactionCase |
| C04-16 | M1 回归 | M1 Mapping/Proposal/确认/Restore/RenderBridge/Document Request/现有调用保持；未迁移的旧工具被如实记录，不把新 Facade 误称全局唯一 | Odoo M1 regression |
| C04-17 | 通用性 | 中性输入下无模板、Sheet、坐标、业务模型、业务字段或客户特例；显式用户坐标只作为输入数据 | Contract + static/behavior test |
| C04-18 | Accept/Finalize 重试 | CB-04 重复 Accept 不重复推进；最终交付由 CB-06 对同一接受版本幂等，CB-04 不重复生成正式文件 | CB-02 acceptance test + CB-06 integration handoff test |

分层报告 `Contract Verified` / `Odoo Integration Verified` / `Provider Integration` / `Browser & Delivery`。本 CC 默认只要求前两层在获批的合成环境中完成；Provider 多轮归 CB-07，Browser/UI/下载和正式交付归 CB-06。安全拒绝不统计为编辑功能成功；未运行项必须标记 `NOT RUN`。

## 11. 文件白名单与禁止范围

下列清单为待冻结的最小实现白名单。所有数据库、模块升级、TransactionCase 执行范围仍须单独授权。

| 文件/目录 | 用途 | 限制 |
|---|---|---|
| `mymodules/office_engine_m2/services/intent_contract.py`（新增） | 验证消息引用、规范化通用 Intent、provenance、Intent digest/范围结构 | 不复制 CB-02 文件 SHA/version authority；不做 Excel DSL。 |
| `mymodules/office_engine_m2/services/edit_orchestrator.py`（新增） | 受控串联 Context/Gate、Mock/Responses Adapter 调用、Candidate 注册、CB-03 验证、条件式接受或 Review handoff | 不复制 Provider transport、Version model、Validator、UI/Finalize。 |
| `mymodules/office_engine_m2/models/office_mapping_tools.py` | 添加单一 `office` facade method/动作分派，复用既有 M1 内部方法和服务 | 不扩大或破坏现有 M1 语义；内部子服务不注册为额外公开 tools。 |
| `mymodules/office_engine_m2/models/llm_thread.py` | Candidate B Thread 工具绑定/allowlist、用户消息来源和结果投影 | 只接线 `office` facade；保留 M1 compatibility route；不重写 Odoo-LLM 循环。 |
| `mymodules/office_engine_m2/data/office_tools.xml` | 默认不修改；只有实测/代码核查证明现有 decorator registry 无法注册 Facade 时，先提交最小变更申请 | 当前优先采用 `@llm_tool(name="office")` 自动注册；禁止为同一方法同时建 XML-managed 重复记录。 |
| **条件性** `mymodules/office_engine_m2/models/office_workbook_version.py`、`services/workbook_version_service.py` | CB-02 Amendment：每轮 `intent_message_id`、可信条件式接受授权、拒绝接口/迁移 | 仅在 CB-02 Amendment 正式批准后修改；维持实际附件/SHA/ORM/锁不变量；禁止由 CB-04 直接写字段。 |
| `mymodules/office_engine_m2/tests/test_intent_contract.py`, `tests/test_edit_orchestration.py`, 必要扩展 `tests/test_candidate_validator.py`/Version tests | 中性 Contract、Mock、CB-02/03 实际 Service 和 TransactionCase | 仅合成数据；不得修改基线测试来降低要求。 |
| `docs/implementation/IHR-M2-CB-04.md`, `ATR-M2-CB-04.md`, `evidence/CB-M2-CB-04/` | 未来实施事实与证据 | 只在 Coding Authorization 后创建/追加真实结果。 |

禁止修改：Odoo 官方 addon、普通 Chat Completions/Provider 配置、CC-01 Adapter、CC-03 Validator/`office_verify`、冻结 SRS/TDD/Plan/CC-01/02/03、CB-06 UI/Finalize/Delivery、M1 Mapping 业务语义、真实业务数据/附件与生产服务。条件式 CB-02 Amendment 未生效前不得触碰 CB-02 生产版本接口实现。

## 12. Acceptance Criteria / Coding Authorization Gate

### 12.1 实施正确性

1. 服务端从当前认证 Thread 确定用户、消息、Session、公司和版本；模型推断永不充当权限、用户消息或事实。
2. 本轮 Intent 通过 Candidate 的 `intent_message_id`/获批等价字段可追溯；一个 Intent 可以生成多个候选，而幂等身份独立。
3. Clarification、Confirmation、Blocked、Failed 与 Completed 由服务端事实区分；所有实际副作用/已到阶段如实呈现。
4. 当前版本仅由 CB-02 受控接口变化。`VERIFIED` 单独不足以接受；普通明确授权且实际 Effect 完全匹配时可条件式自动接受；未授权/超范围/未知的候选保持非当前并移交 CB-06；`PARTIALLY_VERIFIED`/`FAILED` 不接受。
5. 拒绝不改变 Current、Last Valid、Document Revision；待审/拒绝候选不能作为后续父版本。
6. 用户/确认/候选的 Thread、Session、公司、parent、hash、revision、Intent/Effect 和权限在执行前重新核验；所有 stale/篡改/越权测试通过。
7. 候选处理只调用一个外部 `office` Tool Facade；内部服务不作为 Agent Tool 暴露。M1 既有调用保持兼容，过渡期未达到全局单一 Registry 必须如实记录。
8. CB-01/02/03/06 权责不重复实现；M1 回归维持。Provider 请求不确定不盲重试，错误不伪造成文件或成功。
9. IHR/ATR 区分 Contract、Odoo TransactionCase、Provider、Browser/UI、Final Delivery 证据等级；不将 Mock 或静态检查表述为真实 Provider/Browser PASS。

### 12.2 Coding Authorization 前必须已生效的契约

- **A. TDD Amendment**：条件式接受、`VERIFIED ≠ ACCEPTED`、Candidate 可非当前等待人类裁决及相应 Outcome/Finalize 次序。
- **B. Implementation Plan Amendment**：与 A 一致，明确 CB-04 条件式接受逻辑、CB-06 Preview/Review/Finalize handoff、真实 Provider 多轮继续属于 CB-07、M1 Facade staged coexistence。
- **C. CB-02 Amendment**：`intent_message_id` 受控写入；服务端 typed/可信接受依据；verified Candidate 拒绝入口；Current 指针/锁/hash/revision/附件权限保证不变。该 Amendment 要先冻结、授权并完成必要的组件级验收，再授权依赖它的 CC-04 编码。
- **D. CC-04 冻结及独立 Coding Authorization**：白名单、测试矩阵、接口/状态语义定稿。明确允许的数据库、模块升级和 TransactionCase 测试数据库/范围。
- **E. SRS/Data Policy 外发门**：本地 Mock/合成数据测试可由上述 Coding Authorization 单独授权；任何真实 Provider 请求或真实业务文件/数据外发前，SRS Candidate B 对齐及数据处理/留存批准必须生效。不得把 CB-02/03 的局部合成测试例外扩展为真实文件外发许可。

除 E 外，A–D 是 Candidate B 条件式接受/Intent 编排正确实现所需的编码前置。E 是 Provider/数据外发的独立门禁，不阻止独立的本地 Mock/合成编排契约实现。

## 13. Amendment 交付和责任边界

| Amendment | 目标文件 | 建议状态/先后 | CC-04 允许承担的工作 |
|---|---|---|---|
| TDD 生命周期收敛 | 新版本 `TDD_office_engine_m2`，保留 v2.0.2 | 先评审、冻结，再授权 CC04 | 本 CC 不编辑冻结 TDD；实施只消费已生效条款。 |
| Plan 流程/Tool 迁移边界收敛 | 新版本 Implementation Plan，保留 v2.0.1 | 随 TDD 变更或之后、CC04 Coding Authorization 前 | 不在本 CC 内实施完整 M1 Registry migration。 |
| CB-02 Candidate accept/reject + Intent binding | 新版本 `CC-M2-CB-02` amendment 与对应组件验收材料 | 独立修订、批准、编码/验收；完成后才授权依赖代码 | CC04 只调用正式接口；不得临时绕过。 |
| SRS Candidate B/data-processing alignment | 新 SRS 版本及适用数据/安全决策 | 真实 Provider/业务文件外发前 | CC04 本地 Mock/合成验证可另有狭窄授权。 |
| Staged `office` Facade | 本 CC v0.2 冻结及 Plan 对接 | CC04 范围内最小实现；全局 M1 工具迁移另立工作项 | 为 Candidate B 提供唯一 Agent 入口，保留 M1 兼容。 |

## 14. Stop Conditions 与实施交接

以下任一情况停止相应操作，Current 保持不变：Intent 消息/身份无法验证；Session/公司/附件权限失败；意图歧义；风险未授权；SRS/数据政策不允许外发；Candidate 的 parent/SHA/revision/Intent binding 不匹配；Confirmation 失效；Provider 状态不明；文件损坏/超资源；CB-03 非 `VERIFIED`；实际 Effect 不被授权覆盖；CB-02 接受/拒绝原子操作失败；CB-06 Preview/Finalize/Delivery 失败。

本稿通过评审后仍须分别批准所列上游 Amendment、冻结 CC-04 和签发 Coding Authorization。实施范围默认使用 Mock Provider、合成 XLSX、实际 CB-02/03 服务以及明确批准的非生产 Odoo TransactionCase；**当前没有非生产数据库或模块升级授权**。没有额外授权不得运行数据库测试、升级模块、调用 Provider、接触真实业务文件、重启服务、部署或 Git stage/commit/push/reset/clean。

如果实际技术发现证明 Odoo-LLM Facade 无法按 §6.2 安全注册或分派，保留最小代码/接口证据，停止 Facade 接线并提交对本 CC/Plan 的变更申请；不得通过为 Candidate B 新增多个公开工具或直接暴露 Version/Validator 服务绕过单一入口。

## 15. 修订记录

| 版本 | 状态 | 说明 |
|---|---|---|
| v0.1 | DRAFT — NOT AUTHORIZED | 初稿，文件：`CC-M2-CB-04_Intent_Confirmation_Edit_Orchestration_v0.1.md`；保留不覆盖。 |
| v0.2 | FROZEN V0.2 — IMPLEMENTATION BLOCKED PENDING UPSTREAM AMENDMENTS | 负责人于 2026-11-08 批准冻结并要求进入实施。冻结记录不解除 §12.2 所列编码前置：TDD 与 Implementation Plan Amendment、CB-02 Amendment 及其组件验收尚未正式生效；非生产数据库/模块升级/TransactionCase 范围也未获得 CC-04 专项授权。未修改代码、冻结上游、数据库或服务，未执行测试。 |
