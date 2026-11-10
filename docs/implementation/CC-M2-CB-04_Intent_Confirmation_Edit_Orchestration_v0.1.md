# CC-M2-CB-04 — Intent / Confirmation / Edit Orchestration

## 文档信息

| 项目 | 内容 |
|---|---|
| 项目 | Odoo 18 CE / Office Engine M2 — Candidate B |
| 契约 | CC-M2-CB-04 — Intent / Confirmation / Edit Orchestration |
| 版本 | v0.1 |
| 状态 | **DRAFT — NOT AUTHORIZED** |
| 权威设计基线 | `docs/design/TDD_office_engine_m2_v2.0.2.md` — FROZEN |
| 实施编排基线 | `docs/implementation/IMPLEMENTATION_PLAN_office_engine_m2_v2.0.1.md` — FROZEN |
| 上游需求 | `docs/requirement/SRS_office_engine_m2_ai_mapping_v1.1.0.md` — FROZEN；Candidate B 对齐事项仍须正式处理 |
| DDD | 未发现独立的冻结 Office Engine DDD；现有 TDD 将 DDD 记为 N/A |
| 前置组件 | CB-01、CB-02、CB-03 的既有接受基线；本契约不重开其已接受范围 |
| 授权 | 本文件仅供评审；不授权编码、模块升级、数据库操作、Provider 调用、服务重启、生产处理或发布 |

> 本稿描述 CC-04 候选实现契约，不声称下文的 Candidate B 编排已接入当前 Odoo Thread。冻结上游的生命周期语义与本任务提出的“审阅/拒绝前不得推进 Current”之间存在 P0 差异，须先由负责人按 §13 决定正式处置。该差异不能由本草案静默覆盖。

## 1. 治理、依据与审计结论

### 1.1 权威基线

| 来源 | 实际状态与本 CC 的约束 |
|---|---|
| SRS M2 V1.1.0 | 冻结的 Mapping/M1 产品基线。其文件处理边界与后续 LLM/Code Interpreter 编辑路线存在正式对齐事项；此前对 CB-02 及 CB-03 合成 Validator 工作的特定裁定，不自动授权 CB-04 Provider 文件编辑链。 |
| TDD V2.0.2 | 冻结设计基线。§4 定义必要时的计划/检查、风险确认与结果覆盖边界；§5 定义父子版本和状态；§6 定义 Candidate 验证及状态规则；§8 是逻辑接口而非现存 API。 |
| Implementation Plan V2.0.1 | 冻结计划基线。§7 将 CB-04 定义为 Intent、Confirmation、Edit Orchestration；依赖 CB-01/02/03。明确 CB-04 多轮编排用 Mock Provider + 实际 Version Service 验证，真实多轮 Provider 验收归 CB-07。CB-06 单独负责 Preview/Finalize/Delivery。 |
| CC-01 v0.2 | Final Accepted。Responses Adapter 承担 Provider 请求、响应和候选字节获取；不承担 Odoo 业务授权或 Candidate 验收。 |
| CC-02 v0.3 / v0.3.1 | Final Accepted — CB-02 技术范围。版本、附件、SHA、父链、Current/Last Valid、Receipt 登记及受控接受由 CB-02 管理；不包含 CB-04 用户意图/风险判断或 CB-06 UI 交付。 |
| CC-03 v0.2 | Final Accepted — CB-03 技术实现范围。当前验证器按冻结契约生成 typed ValidationReceipt；不实现 Agent 路由、用户确认或 Preview/Finalize。 |
| Lightweight Validator Architecture Change Proposal v0.1 | DRAFT，尚未授权。它不替代冻结 TDD/CC-03。CC-04 依赖当前冻结 Validator 契约；如负责人另行批准该提案，应通过版本控制评估影响。 |

### 1.2 当前调用链和能力状态

状态仅表示本次只读核查的当前仓库实现，不代表该行为已经在此 CC 中测试或验收。

| 能力/调用链 | 状态 | 代码证据 / 当前边界 |
|---|---|---|
| M1 Thread 工具与 Session 绑定 | `IMPLEMENTED` | `mymodules/office_engine_m2/models/llm_thread.py::_office_active_session`, `generate`, `_prepare_chat_kwargs`, `_execute_tool_call`；将原生 Odoo-LLM 循环与既有 M1 工具关联。 |
| M1 准备上下文、Mapping 预览、Proposal 恢复、Finalize | `IMPLEMENTED` | `models/office_mapping_tools.py::office_prepare_context`, `office_save_mapping_preview`, `office_restore_proposal_revision`, `office_finalize`；现有语义属于 Mapping/Proposal 流程，不是 Candidate B 编辑接口。 |
| M1 确认门 | `IMPLEMENTED`（限既有 M1 范围） | `office_mapping_tools.py::_cell_override_confirmation_gate` 绑定 Thread、用户、Session/Proposal revision、预览/模板/内容指纹、目标及操作签名；执行前核验。不能据此推断 Candidate B 的确认已实现。 |
| Candidate B Responses Adapter | `IMPLEMENTED`（CB-01 范围） | `mymodules/odoo-llm/llm_openai/services/responses_adapter.py::ResponsesAdapter.execute` 返回 Provider 候选字节及调用元数据；没有被当前 Office Thread 路由调用。 |
| Candidate/V1/Vn 登记、哈希、父链与附件边界 | `IMPLEMENTED`（CB-02 范围） | `services/workbook_version_service.py::register_initial_v1`, `register_candidate`, `record_validation_receipt`, `accept_verified_candidate`; `models/office_workbook_version.py` 维护版本状态、附件及 revision 绑定。 |
| Candidate Validator → typed CB-02 Receipt | `IMPLEMENTED`（CB-03 技术范围） | `services/candidate_validator.py::validate_workbook_candidate` 检查 Session/Candidate/Parent/Revision/实际字节 SHA 与 Expected Effect，再调用 CB-02 Receipt 登记；自身不作 Agent 意图解释。 |
| 从当前用户本轮消息解析并持久化通用 Intent | `MISSING` | 现有 Candidate `source_message_id` 被 CB-02 服务设为 Session 原始上传消息；当前没有 Candidate B 每轮意图的持久绑定。CB-04 需要在获批范围内设计来源引用，若触碰 CB-02 不可变模型则须先修订 CB-02 契约。 |
| Thread 中 Candidate B 编辑/计划/澄清/确认路由 | `MISSING` | `llm_thread.py::_OFFICE_TOOL_NAMES` 仅含 `office_prepare_context`, `office_save_mapping_preview`, `office_restore_proposal_revision`, `office_finalize`, `odoo_record_retriever`；未发现调用 `ResponsesAdapter.execute` 或 `validate_workbook_candidate` 的生产 Thread 编排路径。 |
| 唯一对外 `office` Tool | `MISSING`（现状与目标差异） | `data/office_tools.xml` 仍注册多个历史外部工具；用户明确其不是本轮核心实现。此差异单独追踪；但 CB-04 的 Candidate B 可调用入口必须由负责人确定，不能把不存在的入口写成已接通。 |
| Candidate 进入用户审阅前的受控状态 | `MISSING`（当前编辑 Candidate 接受语义） | CB-02 `accept_verified_candidate()` 对 `VERIFIED` Candidate 调用接受路径推进 Current；`_TRANSITIONS` 不允许 `verified → rejected`。当前没有 Candidate B 的待人工接受状态/用户拒绝调用路径。 |
| Candidate 预览/Accept/Reject UI 与下载卡片 | `MISSING`（Candidate B） | `llm_thread.py` 只将 M1 Preview/Finalize 结果转换为现有附件卡；Candidate B 版本没有独立的审阅/决定 UI 接线。此类交付实现归 CB-06；CB-04 仅定义交接。 |
| Candidate B Finalize 与幂等交付 | `MISSING`（Candidate B 接线） | M1 `office_finalize` / `render_bridge.py` 有既有 Mapping/Document Request 幂等逻辑；CB-02 有 `record_finalize_reference`。二者均不证明 Candidate B 当前版本已经可 Finalize。正式交付归 CB-06。 |
| UI/RPC/附件侧访问控制 | `PARTIAL` | M1 使用当前 Odoo ORM、Thread 所有权和附件权限；CB-02/03 对 Candidate/Attachment 做当前环境权限与绑定核验。未发现 Candidate B 用户审阅入口，故其端到端权限链未知。 |
| 外部 Tool Registry 收敛 | `MISSING`（目标架构） | 当前多个历史 Tool 仍公开。整体迁移不纳入 CC-04 核心编码；如复用现有入口不能安全承载 Candidate B，须由负责人批准最小兼容入口或另开范围。 |

证据位置：`models/llm_thread.py`、`models/office_mapping_tools.py`、`services/workbook_version_service.py`、`models/office_workbook_version.py`、`services/candidate_validator.py`、`services/render_bridge.py`、`data/office_tools.xml`、`mymodules/odoo-llm/llm_openai/services/responses_adapter.py`。

## 2. 目标与非目标

### 2.1 目标

在现有 Odoo-LLM、CB-01 Adapter、CB-02 Version/Artifact Service 与 CB-03 Validator 上，定义最小的通用 Intent 表达、风险确认、Candidate 编排及状态结果接口，使一轮用户编辑从受权的 Thread 请求到可验证 Candidate 的责任边界可审计、可恢复、可测试。

### 2.2 非目标

- 不重写或扩展 CB-03 的工作簿 Diff、Expected Effect、特性能力矩阵或 Receipt。
- 不开发本地 Excel 编辑 DSL、任意 Python 执行器或业务模型/模板专用意图语法。
- 不改变 CB-01 Provider 协议或再次验证 Provider 能力。
- 不实现 CB-05 Data Tool JSON Refresh。
- 不实现 CB-06 Preview、附件 UI、Finalize 或下载；只定义与之交接的状态及调用契约。
- 不把单一 `office` Tool Registry 迁移纳入本轮核心目标。
- 不修改 SRS/TDD/实施计划或既有接受 CC。
- 不把模型声明、用户确认、工具返回或附件存在任一单独信号当作完整业务意图已满足的证明。

## 3. Scope / Out of Scope

### 3.1 范围内

1. 保留当前用户原始请求的受控消息引用，并建立每轮编辑 Intent 与 Thread/Session/父版本的关联。
2. 解析结果区分用户明确内容、模型推断、服务端观测和未知事项。
3. 支持明确操作的低风险直达；对需要用户选择的歧义请求澄清；对可确认业务风险进行有范围的确认。
4. 在 Provider 调用前重验用户、Thread、Session、公司、当前 Candidate 父版本、SHA、revision、资源/数据策略和确认绑定。
5. 调用 CB-01 取得真实 Candidate；调用 CB-02 登记 Candidate；调用 CB-03 验证并登记 typed Receipt；处理失败、过期、拒绝及重试。
6. 将 Candidate、验证事实、模型声明和用户决策分开传递给 CB-06；不伪报已预览、已接受、已正式化或可下载。
7. 通过授权的纯 Python/TransactionCase 与 Mock Provider + 实际 CB-02 服务验收 CC-04 编排；不要求本 CC 完成 Browser/真实 Provider/生产验收。

### 3.2 范围外

详细见 §2.2。尤其不允许借本 CC 将 `VERIFIED` 改为“仅技术安全”，也不允许将现有已接受 CB-03 Validator 代码静默旁路。

## 4. Intent Contract

### 4.1 设计规则

- Intent 保留用户原话的受控 `mail.message` 引用；不把模型改写的摘要取代原话，也不在日志重复保存不必要的文件/业务正文。
- 每轮用户补充或更正形成新的 Intent revision/请求身份；已被接受的文件版本是内容基线，对话历史仅用于解释，不用于重建 XLSX。
- 解析结果是模型提出的结构化主张；除非服务端按 ORM/附件实际读取验证，否则不得标记为事实。
- Intent 不描述如何执行 Excel 运算，不含固定 Sheet/坐标规则、业务模型字段或模板专用词典。可以在单次请求中引用自然语言中明确的目标位置，但这只是用户目标数据，不构成通用 DSL。
- 缺少可验证预期不等于可猜测补全；可继续生成受限候选的范围必须符合 TDD/CB-03 的 Expected Effect 与验证等级规则，否则澄清或按 `PARTIALLY_VERIFIED` 阻断 Current 推进。

### 4.2 最小结构（提案，不代表现有持久化 Schema）

```json
{
  "schema_version": "1",
  "intent_id": "server-issued-id",
  "source_message_ref": "authorized-mail-message-reference",
  "thread_ref": "server-resolved-thread",
  "session_ref": "server-resolved-session",
  "base": {
    "version_id": "server-resolved-current-version",
    "sha256": "sha256-of-current-bytes",
    "session_revision": 0,
    "document_revision": 0
  },
  "user_text_ref": "same-as-source-message-ref",
  "model_interpretation": {
    "summary": "plain-language summary",
    "operation_class": "edit-class-or-unknown",
    "target_scope": {"description": "generic scope", "precision": "explicit|inferred|ambiguous"},
    "expected_effect": {"description": "only what can be stated and verified"},
    "assumptions": [],
    "unknowns": []
  },
  "claims": [
    {"claim": "...", "provenance": "user_explicit|model_inferred|server_observed|unknown"}
  ],
  "risk_facts": [],
  "intent_digest": "server-computed-canonical-digest"
}
```

字段含义：

| 字段/概念 | 要求 |
|---|---|
| `source_message_ref` | 服务端从当前 Thread 与 `env.uid` 解析；不得信任模型/RPC 任意传入的用户 ID 或任意消息 ID。消息需满足 Thread、作者、公司/可见性与当前会话绑定。 |
| `base` | 从 CB-02 当前状态及受 ACL 保护的真实附件字节取得；模型不可选择一个未授权旧版作为隐式基线。 |
| `target_scope` | 表达“用户说了什么范围、其精确度如何”；不等同已经核实的实际 Diff 范围。 |
| `claims.provenance` | `user_explicit` 是来自原始请求的可核对文字；`model_inferred` 仍是推断；`server_observed` 需附服务端证据引用；`unknown` 不可被提升为事实。 |
| `expected_effect` | 复用 CB-03 只读验证契约：目标、允许变化类别及可验证预期；不增加执行 DSL。缺少精确预期的部分不得宣称完整语义验证。 |
| `risk_facts` | CB-03 报告的客观事实与计划阶段风险描述分开保存。事实包含来源/阶段；不直接代替 Gate 的风险政策决定。 |
| `intent_digest` | 服务端对规范化请求与基线引用计算。模型提供的摘要或 digest 不作为授权证明。 |

### 4.3 意图更新与歧义

- 后续用户消息是独立增量意图；编排层将其与当前已接受版本及现存会话上下文对齐，不能默默把旧操作重新执行。
- 可唯一解释且在当前能力/授权内的请求可继续；若对象身份、范围、条件或预期存在会改变结果的多种合理解释，返回 `clarification_required`，不调用编辑 Provider、不登记 Candidate。
- 新 Intent 修订使任何依赖旧目标/Effect 的未消费确认失效。已有 Candidate 是否保留为隔离失败/历史记录由 CB-02 不可变规则管理，不得悄悄变成新请求输入。
- 用户明确要求未被结构化表达能力支持时，说明未覆盖部分，不用更窄操作冒充完整执行。

## 5. Confirmation Contract

### 5.1 对外结果

| Outcome | 服务端判据 | 正式副作用 |
|---|---|---|
| `completed` | 被授权的操作已按适用规则执行，Candidate 经 CB-03 验证且版本/交付步骤各自达到其状态定义；不得由 Provider 文本单独触发 | 仅报告真实到达的阶段；`completed` 不能混同“正式附件已交付” |
| `confirmation_required` | 目标和风险范围足够明确，存在尚未由用户原始明确授权覆盖的可确认业务风险 | 确认前不得启动该风险编辑或执行相应持久化状态迁移 |
| `clarification_required` | 意图、目标、范围或必要参数有多种会影响结果的解释 | 不启动编辑；不创建可接受 Candidate |
| `blocked` | ACL、Record Rules、公司隔离、附件/文件安全、版本冲突、资源上限、技术完整性或不支持能力不允许继续 | 用户确认、模型参数或 `force_override` 均不能绕过 |
| `failed` | 实际执行失败或结果无法可靠确认 | 返回已知副作用与恢复状态；Current/Last Valid 按 CB-02 不变量保持，除非受控原子接受已成功 |

内部诊断码与面向用户的安全说明分离。用户反馈依据服务端结果，模型可翻译/概述但不可升级结果类别。

### 5.2 自动执行、确认与澄清判据

1. **直接执行**：用户要求明确、目标与预期可表达、范围有限、在已验证能力/权限内，且没有超出请求含义的可确认风险。普通明确的单目标替换不因旧值非空而机械增加一次确认。
2. **请求确认**：操作涉及未被用户明确授权的批量覆盖/清除、公式/依赖范围变化、不可逆结构变更或其他按已批准风险政策必须由用户裁决的影响；必须描述对象、范围、原状态/可观测风险、拟执行效果及建议，并提供可检查的唯一确认引用。
3. **请求澄清**：目标身份/范围/记录集合/操作方式存在实质歧义；确认不能替代澄清，模型不能先自行选择。
4. **阻断**：权限、安全、文件、版本、资源或不支持结构问题。任何业务确认均无效。
5. **执行后风险事实**：CB-03 `risk_facts` 与 `validation_result` 独立。某单元格原有内容或表头被修改本身不自动意味着技术失败；是否属于用户已授权效果由受信任编排逻辑按原始 Intent、有效确认和实际验证事实判断，不能由 LLM 自报覆盖。

### 5.3 授权绑定、有效期与重验

需要确认时，确认记录必须由服务端关联并绑定：

- 当前 Odoo 用户身份（从认证环境取得）、Thread、Session、公司范围；
- 当前有效父版本 ID、附件实际 SHA-256、Session/Document revision；
- 原始用户消息引用及服务端规范化 Intent/Intent digest；
- 目标范围、允许变化类别、可验证预期、风险事实/风险说明及确认操作类型；
- 如针对已生成 Candidate 的最终选择，还需 Candidate ID、父版本、Candidate 实际 SHA-256、Receipt/验证报告引用与实际 Effect digest。

Agent 提交的 `confirmed=True`、模型传入 `user_id`、上下文布尔标记或 `force_override=True` 均不构成确认。接受确认只能从当前用户在绑定 Thread 中的实际消息/受信服务端交互取得，并核验作者、消息顺序和单次待确认状态。

执行前重新读取 ORM 权限、Thread/Session 绑定、Current/父版本、附件字节/SHA、revision、Intent/Effect digest、目标范围、资源/外发政策和权限公司上下文。任何改变使旧确认失效；对新范围重新说明并确认。授权不得扩大，不得复用到不同 Candidate、Session、用户、版本或操作。

### 5.4 决策与 Accept 的关系

Confirmation 和 Accept 不应被重复问成对同一事实的两次相同问题：

- **确认**回答“是否允许尝试这一项尚未明确授权、但风险已说明且范围确定的编辑”。
- **接受 Candidate**回答“是否让这个已生成、已验证、其真实字节/Effect 已知的 Candidate 成为权威 Current 版本”。
- 用户原始明确意图可以作为普通、低风险操作的授权，不需额外预编辑确认；若产品决定由该明确意图连同严格匹配的验证 Effect 同时授权版本接受，则必须记录这一语义，且不能在执行后再把同一选择伪装成必须重复确认。若实际 Effect 超出或无法证明与用户授权一致，须停止并重新澄清/确认。
- 高风险操作的预确认仅授权其绑定范围。若确认不包含对实际 Candidate 的接受，或实际候选 Effect 无法与授权范围确定匹配，Candidate 应保留为非当前候选，交 CB-06 提供一次针对实际结果的接受/拒绝决策。

具体采用“用户原始明确请求可否直接授权 Current 推进”与 Candidate 是否必须经 UI Accept 才成为 Current，受 TDD 生命周期决议约束，见 §13 O-01；在其冻结差异解决前不得由实现者自行选择。

### 5.5 并发、重复请求与幂等

- 每个用户意图使用服务端生成/验证的 idempotency key，并绑定请求 digest、父版本、输入 SHA、Intent digest 和风险授权引用。相同 key 与完全相同请求返回既有结果；同 key 不同请求必须拒绝。
- Provider 结果不明时不得盲目重试；按 CB-01 的 `indeterminate` 语义查询可用状态或阻止重复执行。成功候选不得因重复工具调用再插入/覆盖版本链。
- Candidate 接受/Current 推进由 CB-02 受控原子操作负责；stale parent、revision、授权或重复 Finalize 必须幂等返回或拒绝，不得双重副作用。
- 本 CC 不重新实现 CB-02 并发锁或幂等算法，仅集成并测试其接口语义。

## 6. Edit Orchestration Contract

### 6.1 调用链与责任

目标路径按冻结基线及待裁定生命周期差异表示。步骤字段是契约目标，不代表当前已实现：

| 顺序/步骤 | 责任组件 | 输入 | 成功输出 | 失败语义/副作用边界 |
|---|---|---|---|---|
| 1. Intent | Agent + Thread 调用层 | 本轮用户消息、现有 Thread/Session | 原始消息引用；模型候选解析与 provenance | 缺少/不可信用户请求时澄清或 blocked；不得创建 Candidate |
| 2. Resolve Context | Odoo 服务 + 当前用户 ORM | Thread、当前用户、Session | 经 ACL/Record Rules 核实的公司、Session、当前版本、真实附件 SHA、revisions | 越权、不可见、版本缺失为 blocked/failed；不可由模型选历史输入替代 |
| 3. Plan Edit（必要时） | Agent/受控 Provider 只读检查 | 当前版本副本 + Intent | 操作类别、目标/范围描述、假设、规模、未知项；不产生可用文件 | 需要选择则 clarification；未授权风险返回 confirmation_required；规划不得写 Odoo 附件或形成 Candidate |
| 4. Confirmation Gate | 受信 Odoo 编排 + Thread 用户消息核验 | Intent、计划/风险、当前版本绑定 | 窄范围授权引用，或允许低风险执行 | 未确认不调用风险编辑 Provider；权限、安全、资源失败为 blocked |
| 5. Execute Candidate Edit | CB-01 Adapter，由受信编排调用 | 被确认/授权的 Intent，当前 Current 文件真实 bytes/hash，资源策略 | Provider 请求事实与候选 XLSX bytes、SHA、元数据 | `failed`/`indeterminate` 保持 Current 不变；不得把文本/代码建议转成文件成功 |
| 6. Register Candidate | CB-02 Version Service | 当前授权 Session、父版本、input/output bytes/SHA、幂等键、Intent 效果绑定 | `candidate_received` 版本记录 | 父版本或 revision 失效时拒绝/标 stale；Candidate 不自动成为 Current |
| 7. Validate Candidate / Register Receipt | CB-03 Validator + CB-02 受控 Receipt 接口 | 当前用户 ORM 可读的 parent/candidate、Effect、版本与实际附件 | `VERIFIED`/`PARTIALLY_VERIFIED`/`FAILED`、Risk Facts、typed Receipt（若可登记） | Receipt 错绑/无效则不得接受；`PARTIALLY_VERIFIED`/`FAILED` 不推进 Current；业务确认不能覆盖技术失败 |
| 8. Present Review | CB-06 | Candidate 实际附件、Validator 事实、Effect/风险、模型说明 | 私有候选预览/下载信息、服务端事实与模型声明分栏展示 | UI/附件生成失败不得报告可下载；不修改 Current 或事实状态 |
| 9. Revise / Accept / Reject | 用户通过受信 Thread/CB-06 交互；Odoo 编排校验 | 有效 Candidate 及 Review 数据 | revise 创建以当前 Current 为父的新意图；accept 请求 CB-02 原子接受；reject 将候选标记为拒绝/隔离 | reject 不改变 Current/Last Valid；旧 Candidate/确认不可复用；仅在无副作用情况下允许安全重试 |
| 10. Controlled Finalize | CB-06 + CB-02 | 已接受 Current、附件/消息、有效绑定 | 与接受字节一致的正式附件/消息及 Delivery Receipt | 发布失败保留 Current 与可重试交付状态；不得重跑 Provider；重复 Finalize 幂等 |

### 6.2 多轮基线

- 每轮以 CB-02 当前已接受的版本字节作为唯一输入。对话历史用于理解上下文但不能重建文件内容。
- 新一轮用户指令更新/补充 Intent；不得从原始 V1 重放前轮编辑，不得将旧 Candidate 当作 current。
- 修改意见改变目标或 Effect 时，生成新的 Intent digest 和幂等键；旧确认失效。Provider 请求失败或候选验证失败时，Last Valid/Current 不变。
- 已被用户接受的 Candidate 是下一轮父版本；未接受/被拒绝 Candidate 不得成为后续输入。
- Data Tool 刷新在 CB-05 管理；本 CC 不把数据查询或 JSON 转坐标纳入编排实现。

### 6.3 版本状态与用户选择

服务端保存的 Intent、确认、Candidate、Validation Receipt、接受、Finalize、Delivery 是独立事实。不得把它们压成单个“成功”标志。外层结果至少映射：

`operation_outcome × validation_result × candidate/version_state × artifact_state × delivery_state`

Candidate 来源与版本必须通过 CB-02 `parent_version_id`、真实输入/输出 SHA、Session/Thread/company/revisions、Intent 绑定及 CB-03 typed Receipt 关联。Receipt 证明 Validator 的文件级判断，不证明模型解释忠实或用户完整任务语义已经满足。

## 7. 信任边界与安全不变量

1. **用户/Agent 边界**：原始用户消息是用户意图的权威来源；模型结构化解析是候选解释，不是权限凭据。
2. **ORM 边界**：当前 `env.uid`、ACL、Record Rules、allowed companies 和附件 read/write 权限贯穿 Resolve、Candidate 注册、验证、Review 和 Finalize；不使用 `sudo()` 或客户端传入模型/记录/公司身份绕过。
3. **Provider 边界**：只有业务权限、外发/数据策略、资源政策与所需确认通过后，才向获批 Provider 提交最小必要的当前文件和指令；Adapter 的 provider result 不会接受 Candidate。
4. **Version 边界**：只有 CB-02 服务可改变 Current/Last Valid/Document Revision；Candidate/receipt/Preview/UI 均不等于接受。普通 ORM/RPC/LLM 不得直接写受保护字段或 Receipt。
5. **Validator 边界**：只有 CB-03 独立校验的实际文件事实可形成 typed Receipt；模型声明、文件名、HTTP 成功和用户确认均不能替代。
6. **确认边界**：确认是服务端按当前真实用户消息、Thread、Session、Candidate/父版本、文件 hash、revision、Effect 和影响范围验证的业务授权；`force_override`、`confirmed=True`、用户 ID 参数或任意 context 不构成证明。
7. **交付边界**：仅 CB-06 在引用已接受版本和服务端状态后创建/关联正式附件；预览失败、发布失败、Provider 超时不得使候选伪装为完成。
8. **日志边界**：保存最小必要的 ID、hash、状态、错误分类及资源记录；业务文件正文、密钥和未经授权的模型/用户数据不得写入普通日志。

## 8. 状态与失败语义

### 8.1 核心状态推进

按当前 CB-02/03 已实现状态，候选可从 `candidate_received` 经验证成为 `verified`，再由 `accept_verified_candidate()` 推进为 `accepted_current`；失败/部分验证不可推进。拒绝/未完成候选应保持与有效版本隔离。

本任务希望的审阅后接受顺序与上述现状不同：候选应在 Review 时保持非 Current，用户接受才由 CB-02 原子推进；用户拒绝则维持 Current。这要求新增/确认可持久化的 pending-review 状态与 `verified → rejected`/接受状态转移，并更新 CB-02 接受接口。除非冻结契约变更获批，CC-04 不得以服务层私有调用、ORM 直写或局部状态伪造实现该顺序。

### 8.2 失败映射

| 失败 | 对外结果 | 候选与 Current 规则 | 恢复 |
|---|---|---|---|
| Intent 目标/范围歧义 | `clarification_required` | 不创建/不接受 Candidate，Current 不变 | 用户补充后创建新 Intent |
| 需确认但未确认/明确拒绝 | `confirmation_required` / 用户拒绝结果 | 不调用需确认的编辑；任何已存在 Candidate 不推进 Current | 明确确认后完整重验，或安全关闭待确认记录 |
| ACL、公司、附件权限、外发政策失败 | `blocked` | 不 Provider 调用/不接受；Current 不变 | 权限或政策状态变化后重新发起，不复用旧确认 |
| 资源/预算或不支持结构 | `blocked` | 不接受 Candidate；Current 不变 | 更换受支持请求需用户新意图；不得转模型绕过 |
| Provider API 结果不明 | `failed`（内部 `indeterminate` 保留） | 保留父 Current，不盲目重试/不生成伪文件 | 查可审计 Response/文件引用；只有状态可证且幂等可行时重试 |
| Candidate 注册/哈希/绑定失败 | `failed` 或 stale `blocked` | 不登记有效 Candidate/不推进 | 修复实际输入或重新生成新请求 |
| Validator `FAILED` | `failed` | 拒绝/隔离候选；Current 不变 | 修订意图或输入后新候选，不降低验证规则 |
| Validator `PARTIALLY_VERIFIED` | `blocked` 或待人工澄清（依冻结 TDD） | 不推进 Current/不正常交付 | 明确未验证范围后按允许路径处理 |
| Candidate 过期或 parent/revision 改变 | `blocked`/stale | 旧 Candidate/确认不可复用 | 以新的 Current 构造新 Intent/Candidate |
| 用户拒绝 Candidate | 用户拒绝（可映射为非错误终态） | Current/Last Valid 不变；候选状态应保留为拒绝/历史 | 后续编辑从当前有效版本创建新子候选 |
| 用户接受后 CB-02 原子接受失败 | `failed`/stale | 原 Current 保持；不得表示接受成功 | 刷新状态后由用户重试，幂等防重 |
| 正式附件创建/关联失败 | `failed`，delivery pending/failed | 已接受 Current 不回滚；不得重复编辑或变更字节 | CB-06 对同一接受版本安全重试交付 |
| Provider 后续回复超时 | 取决于已持久化阶段 | 不回写已验证/已接受事实；从数据库事实恢复 | 下一轮重新读取真实状态，防重复执行 |

工具原生 `completed` 仅表示某次函数完成。Office 用户结果由服务端持久化 Candidate/Validation/Accept/Delivery 状态确定。模型输出不得把 `candidate_received` 或 `verified` 映射成完整任务已完成。

## 9. 现有组件复用与兼容

| 组件 | CC-04 复用 | 本 CC 不得改变 |
|---|---|---|
| Odoo-LLM 原生循环和 `llm.thread` | Thread、消息作者/顺序、当前用户、对话输出和 M1 路由；按批准范围增加 Candidate B 调用编排 | 不另建通用事件总线或聊天循环 |
| CB-01 `ResponsesAdapter` | 受信编排调用 `execute()`；验证其返回事实并按 indeterminate 策略处理 | 不修改普通 Chat Completions、凭据、模型或 Provider 配置 |
| CB-02 Version/Artifact Service | V1/current/parent/Candidate/Receipt/原子推进/幂等/Finalize 引用 | 不复制版本表、SHA 服务、Current 指针或锁 |
| CB-03 Candidate Validator | Candidate 的当前技术/Effect/能力检查及 typed Receipt | 不旁路、不减弱、不重写 Validator；风险事实与验证结果保持分离 |
| M1 Mapping/RenderBridge/Document Request | 首轮 M1 行为和已有 Proposal/确认/预览/Finalize 流程兼容 | 不改变字段映射、权限、确认与历史附件语义 |
| CB-06 | Candidate Preview、Review UI、Accept/Reject、正式附件和浏览器交付 | CC-04 不实现 UI/附件投递，不重复 Finalize |
| 外部 Tool Registry | 只实现负责人批准且当前调用链确实需要的最小接入点 | 不将全量迁移成单一 `office` Tool 作为 CC-04 的默认核心编码任务 |

### 独立架构差异

1. **工具注册差异**：产品目标要求单一外部 `office` Tool，现存 XML/Thread 仍使用多个历史工具。该迁移不是本轮核心范围。由于当前没有 Candidate B Thread 入口，需负责人先选择：授权一个最小内部/外部兼容入口供 CB-04 调用，或将 Tool Registry 变更单独授权并安排。无批准入口时，不得声称 Candidate B 已接入。
2. **Validator 架构提案**：Lightweight Validator v0.1 仍是未批准草案。当前 CC-04 必须按冻结 TDD 和已接受 CB-03 的 Validation Result/Receipt 语义，不可选择性跳过 Expected Effect 或降级 `VERIFIED`。

## 10. CC-04 测试契约

所有案例用中性 XLSX/Office 文件和合成 Thread/会话数据表达，不写死模板、Sheet、坐标、Odoo 业务模型或客户。下表为未来 Coding Authorization 后的验收要求，本轮未执行测试。

| ID | 场景 | 必要断言 | 适用层 |
|---|---|---|---|
| C04-01 | 清晰、明确、支持的普通 Intent | 解析保留原消息引用与 provenance；从服务端 current 取基线；不多余确认；产生真实 Candidate 流程 | Contract + TransactionCase + Mock Adapter |
| C04-02 | 目标/条件多解或必要参数缺失 | `clarification_required`；不调用 Provider、不登记 Candidate、不变 Current | Contract + TransactionCase |
| C04-03 | 计划发现可确认风险 | 风险/范围说明可理解且精确；未确认不启动风险编辑/不产生正式副作用 | Contract + TransactionCase |
| C04-04 | 明确窄范围授权的普通修改 | 按冻结 TDD 不因旧值自动二次询问；只验证并执行明确范围 | Contract + TransactionCase |
| C04-05 | ACL、Record Rule、公司或附件权限失败 | `blocked`；确认参数、`force_override`、模型 ID 均不能绕过；不外发数据 | TransactionCase |
| C04-06 | 旧确认、错误用户/Thread/Session/父版本/hash/revision/Effect | 执行前拒绝；重新形成确认；不得写入/调用 Provider | Contract + TransactionCase |
| C04-07 | 确认后文件/目标/实际 Effect 变化 | 旧确认失效；越范围 Effect 不接受；Current 保持 | CB03+CB02 Integration TransactionCase |
| C04-08 | 未确认前副作用审计 | 不调用风险编辑 Provider、不登记可接受 Candidate、不推进 Current；只允许不持久化的授权范围读取/计划 | Mock Adapter + TransactionCase |
| C04-09 | Candidate/Receipt 绑定 | 输入来自当前 accepted parent；Receipt 精确绑定 Candidate bytes/sha/Session/Revision；模型声明不替代 Receipt | CB02/CB03 Integration TransactionCase |
| C04-10 | Provider 失败、indeterminate、非法文件、Candidate 注册失败 | Current/Last Valid 不变；错误类别真实；无盲重试和伪成功附件 | Mock Adapter + TransactionCase |
| C04-11 | 用户修改意见构成下一轮 | 使用实际 accepted Candidate 作为父文件；意图/确认重新绑定；失败不污染 last-valid | Mock Adapter + 实际 Version Service |
| C04-12 | 用户拒绝候选 | Current/Last Valid/Document Revision 不推进；Candidate 记录保持可审计拒绝状态且不可成为后续基线 | TransactionCase；依赖 O-01 / CB02 状态修订 |
| C04-13 | 重复 Candidate 请求与重复接受/Finalize | 同 key/同 digest 返回同结果；同 key/不同 digest 拒绝；单一版本接受；交付幂等由 CB-06 验证 | CB02 Integration；Finalize 外部副作用归 CB06 |
| C04-14 | Candidate 验证事实与模型声明分离 | 展示/结果分别记录 Agent intent coverage、Provider 声明和 CB03 事实；未知/未覆盖时不得声称完整任务完成 | Contract + TransactionCase |
| C04-15 | M1/M2 回归兼容 | M1 Mapping/Proposal/restore/RenderBridge/Document Request/既有确认不回归；M1 错误不会伪装成 Candidate B Outcome | Odoo regression suite |
| C04-16 | 架构通用性 | 不存在模板/Sheet/单元格/Odoo 业务模型分支；Candidate 仅走批准的统一受控编排及 CB02/CB03 服务 | 架构静态检查 + 行为测试 |

验收层级：纯 Python/Mock 只能证明契约和编排路径；TransactionCase 才证明 Odoo ORM/服务边界；真实 Provider、Browser、下载及生产附件政策不属于本 CC 的默认范围，除非另有明确授权。任何未运行层必须标 `NOT RUN`，不得据低层测试推断通过。

## 11. 建议文件白名单（须在冻结前核实）

白名单是评审候选，不授权修改：

| 路径 | 预期用途 | 边界 |
|---|---|---|
| `mymodules/office_engine_m2/services/intent_contract.py`（新增） | 规范化 Intent、provenance、digest、结构校验，不解析任意 Excel 语言 | 纯契约逻辑，不持久化 Odoo 业务副作用 |
| `mymodules/office_engine_m2/services/edit_orchestrator.py`（新增） | 连接 Thread/Session、CB01 Adapter、CB02 Version Service、CB03 Validator；输出受控 outcome | 不实现版本表、Validator、Provider 传输或 UI |
| `mymodules/office_engine_m2/models/llm_thread.py` | 从受信当前消息解析 Thread/用户/Session，接线必要 Candidate B 路由及结果映射 | 保留 M1 原生循环和兼容；工具路由具体修改待 O-04 批准 |
| `mymodules/office_engine_m2/models/office_mapping_tools.py` 或经批准的新 internal service facade | 仅在需复用 ORM 当前用户/Thread 权限门时接入受信调用点 | 不把服务伪装为公共 RPC 权限边界 |
| `mymodules/office_engine_m2/models/office_workbook_version.py`、`services/workbook_version_service.py` | **条件性**：只有 O-01/O-02 批准修改 verified→pending-review/rejected 或 typed 用户接受收据时，纳入修订白名单 | 需先版本化修订 CB-02；当前 v0.3 Final Accepted 接口不得由 CB04 静默扩写 |
| `mymodules/office_engine_m2/tests/test_intent_contract.py`（新增）及 `tests/test_edit_orchestration.py` / `tests/test_candidate_validator.py`（必要时扩展） | Contract/Mock/TransactionCase 回归 | 测试数据合成；不修改既有断言来降低标准 |
| `mymodules/office_engine_m2/data/office_tools.xml` | **条件性/待 O-04 决策**：若唯一可行的批准 Candidate B 路由需要 Tool entry，只作最小兼容接线 | 不默认进行全量单一 Tool Registry 迁移 |
| `docs/implementation/IHR-M2-CB-04.md`、`ATR-M2-CB-04.md`、`evidence/CB-M2-CB-04/` | 编码授权后记录事实、命令和证据 | 不在本轮创建或伪造测试证据 |

### 明确禁止的修改

- Odoo 官方 addon、OpenAI Provider 普通 Chat Completions/配置、CB-01 Adapter；
- `office_verify`/CB-03 Validator 规则、结果等级、Receipt 语义；
- M1 Mapping parser/Skill/RenderBridge 的既有业务行为，除必要兼容回归外；
- CB-02 版本/接受/附件权限逻辑，除经 O-01/O-02 正式版本化批准后列明的最小接口修订；
- CB-06 UI/附件/Finalize/Browser 实现；
- 冻结 SRS、DDD（若存在）、TDD、Implementation Plan、CC-01/02/03；
- 数据库 Schema、配置、真实业务文件或生产数据处理路径。

## 12. 验收标准与授权门

### 12.1 Coding Authorization 前置项

以下事项必须在 CC-04 冻结/授权前书面裁定：

1. §13 O-01：处理 TDD/实施计划与人类 Review 前推进 Current 的冲突；
2. §13 O-02：如果要求审阅后再接受，批准最小 CB-02 状态/接受接口变更方案；
3. §13 O-03：确定 Candidate 与本轮原始用户消息的权威绑定方式；
4. §13 O-04：确定 Candidate B Thread 可调用入口；
5. §13 O-05：确认 SRS 对 Candidate B 外发及后续编辑的适用范围/正式变更路径；
6. 同意本 CC 的范围、白名单、状态语义和测试层级，并签发单独 Coding Authorization。CC 冻结本身不等于实施授权。

### 12.2 技术验收

- Intent、来源、用户、Thread、Session、Current parent/hash/revision 可由服务端真实绑定；模型推断不会升级成事实。
- 明确/歧义/需确认/blocked/failed 五类结果均具可观察且不可混淆的服务端条件。
- 需要确认的操作在有效授权前无 Provider 风险编辑请求或可接受 Candidate 副作用；确认后只重验并执行同一范围。
- 权限、安全、Record Rules、公司范围、附件绑定、资源约束不可被用户确认或模型参数绕过。
- CB-01/02/03 以实际受控接口串联，不复制组件责任；失败 Candidate 不推进 Current。
- 用户拒绝、陈旧版本、失败候选及重复提交满足冻结/获批的版本不变量；Current 与 Last Valid 保持一致。
- M1 路径行为不回归；不声称完成单一 `office` Tool Registry 迁移或 Browser/Provider 全链路验收。
- IHR/ATR/evidence 记录实际命令、数据库/Provider/Browser 层级、测试发现数、状态和 Git 状态；不提交代码，除非另行授权。

### 12.3 关闭范围

`Final Accepted — CB-04 scope only` 仅在冻结 CC 的自动化/TransactionCase 和授权范围内集成验收满足并由负责人接受后登记。它不代表真实多轮 Provider、Browser/用户附件下载、CB-05 JSON refresh、CB-06 最终交付、生产部署或 Release Gate 关闭。

## 13. Owner Decisions / Open Questions

| ID | 决策事项 | 证据与建议 | 阻塞范围 |
|---|---|---|---|
| O-01 — P0 | **Candidate 何时成为 Current？** TDD V2.0.2 §5.2/§6.3/§8.1 与 Plan CB-06 要求 `VERIFIED` 后可推进 Current、再生成 Preview；HGIAL/本任务要求候选未经用户授权不得推进，且需支持审阅后 Reject 保持 Current 不变。建议把候选先验证并私有展示，用户接受后 CB-02 原子推进；未经接受的普通 Candidate 保持非 Current。须由负责人批准版本化 TDD/Plan 变更，不能在 CC-04 覆盖冻结文档。 | TDD §5.2、§6.3、§8.1；Plan §7/§9/M2-BASIC-EDIT | **阻断 CC-04 实施**，直到正式解决 |
| O-02 — P0 | 若 O-01 采用审阅后接受，CB-02 当前 `accept_verified_candidate(candidate_id)` 会直接接受，状态表不支持 `verified→rejected`。是否授权提交/冻结最小 CB-02 amendment，增加 pending-review 与绑定用户接受/拒绝的 typed、服务端验证接口，并保留当前锁、Receipt、SHA 与 ORM 权限？不得由 CB-04 直接写版本字段。 | `workbook_version_service.py::accept_verified_candidate`; `office_workbook_version.py::_TRANSITIONS`; CC-02 v0.3 §6 | **阻断审阅/拒绝实现** |
| O-03 — P1 | 本轮 Intent 如何持久、不可伪造地绑定到 Candidate？当前 Candidate `source_message_id` 指向 Session 原始上传消息，不是每轮用户编辑消息；当前只有 request/effect digest。建议增加最小的 per-version source intent/message binding，并通过 CB-02 amendment 纳入唯一受控创建接口；避免重复存完整正文。 | `office_workbook_version.py::source_message_id`; `workbook_version_service.py::register_candidate` | 若无安全替代方案，**阻断可审计多轮 Intent** |
| O-04 — P0 | Candidate B 的 Thread 入口采用什么批准方式？当前 M1 公开多个工具，Candidate B 无生产 Thread 路由；唯一外部 `office` Tool 目标没有落地。建议本 CC 只取得一个最小安全 Candidate B 入口授权，完整 Registry 迁移单独追踪。 | `data/office_tools.xml`; `llm_thread.py::_OFFICE_TOOL_NAMES`; 无 Adapter/Validator 调用点 | **阻断 Candidate B 端到端编排** |
| O-05 — P0 | SRS v1.1.0 的 AI 文件处理边界如何与 Candidate B Provider 外发及后续编辑对齐？此前 CB-02/CB-03 的专项授权是范围受限例外，不自动覆盖 CB-04 文件外发和用户连续编辑。建议走 SRS 正式版本化变更/数据处理批准，再签发 CC-04 Coding Authorization。 | SRS v1.1.0 §1 与 TDD §0.1/§12.3；CC-03 的明确范围限制 | **阻断任何真实 Candidate B Provider 路径**；可否仅做纯契约代码须负责人明示 |
| O-06 — P1 | Candidate Review 是否由 CB-06 提供预览及 Accept/Reject UI，或本地 Thread 提供最小交互？建议继续归 CB-06；CC-04 只约定调用接口和服务事实。 | Plan §9；当前无 Candidate UI | 不阻断 CB-04 内部 Contract 测试；阻断真实用户 Review 验收 |
| O-07 — P1 | 对精确的低风险用户指令，是否把原始指令视为对匹配 Candidate 的 Current 接受授权，从而不另行请求 Accept？建议直接授权仅在验证后的实际 Effect 与明确 Intent 完全匹配且服务端可证明时适用；任何未知/扩大效果转 Review/澄清。需与 O-01 一并决定，避免每操作重复确认。 | TDD §4.2（明确单目标不重复确认）、§6.3（Verified 可接受）；HGIAL 最终业务裁决原则 | 与 O-01 一并阻断状态契约冻结 |

## 14. Stop Conditions 与实施交接

出现下列情况应停止对应编辑请求、保留 Current 并返回准确结果：意图歧义、权限/公司/附件失败、SRS/数据政策未授权、父版本/文件 SHA/revision 改变、确认过期、Provider 状态不明且无法安全重试、候选损坏/超资源、Receipt 未绑定、Validator 非 VERIFIED，或版本接受/正式附件步骤失败。

本草案评审通过不自动冻结 CC，也不授权编码。满足 §12.1 后，须另行签发针对已冻结版本的 Coding Authorization；在此之前不得修改代码、运行 TransactionCase、升级模块、重启服务、调用 Provider、访问真实业务附件或改变数据库/版本状态。实施阶段如发现需改变 SRS/TDD/Plan/CB-02/CB-03 契约的真实缺口，先停在相关边界并提交版本化变更申请；不得用测试替身或私有服务调用绕过。

## 15. 修订记录

| 版本 | 状态 | 说明 |
|---|---|---|
| v0.1 | DRAFT — NOT AUTHORIZED | 首次起草；基于冻结 SRS/TDD/Implementation Plan、已接受 CB-01/02/03 与当前仓库只读调用链审计。列出生命周期、SRS、意图来源及调用入口差异；不修改任何实现或冻结基线。 |
