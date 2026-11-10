# CC-M2-CB-03 — Workbook Validator

## 0. 文档治理

| 项目 | 内容 |
|---|---|
| 版本 | v0.1 |
| 状态 | **DRAFT — NOT AUTHORIZED FOR IMPLEMENTATION** |
| Coding Authorization | 未授权 |
| 模块 | `office_verify`, `office_engine_m2` |
| 目标 | 为 LLM 编辑产生的 XLSX Candidate 建立唯一的本地独立验证入口，并通过 CB-02 的受控接口登记绑定 Candidate 的 Validation Receipt。 |
| 本轮授权 | 只读架构核查与本 CC 起草；不编码、不测试、不访问 Provider、数据库、服务或真实附件。 |

### 0.1 权威基线

| 来源 | 状态 | 本 CC 的用法 |
|---|---|---|
| `docs/design/TDD_office_engine_m2_v2.0.2.md` | FROZEN | 以 §2、§4、§5、§6、§7、§8 为技术权威。 |
| `docs/implementation/IMPLEMENTATION_PLAN_office_engine_m2_v2.0.1.md` | FROZEN | §6 定义 CB-03 范围、依赖、验收和特性/候选结果双层状态。§0.2 编码前置门仍有效。 |
| `docs/requirement/SRS_office_engine_m2_ai_mapping_v1.1.0.md` | FROZEN | 保留既有首轮 Mapping/M1 业务行为。TDD 中 Candidate B 与 SRS 的规范差异仍待正式版本化 SRS 修订；本 CC 不解除该 Gate。 |
| `CC-M2-CB-01_Responses_Provider_Adapter_v0.2.md` + IHR/ATR | FINAL ACCEPTED | Adapter 返回候选字节不等于候选通过验证；不修改 Provider/Chat Completions。 |
| `CC-M2-CB-02_Workbook_Version_Artifact_Service_v0.3.md` + v0.3.1 amendment | v0.3 冻结；v0.3.1 并发修订获负责人批准 | CB-02 版本模型、父链、附件、权限和 Receipt 登记接口为依赖。CB-02 证据已具备 `READY FOR FINAL ACCEPTANCE`，其单独 `Final Accepted` 记录仍待负责人；本 CC 不代签、不重开 CB-02。 |
| DDD | N/A | 本次基线清单未发现独立的 Office Engine 冻结 DDD；不虚构领域编号。 |

### 0.2 当前代码对照（只读核查）

- `mymodules/office_verify/verify.py::verify_output` 接受源/候选字节和严格的 M1 `mapping_plan`，检查已声明写入、公式文本、样式及结构；不是 Candidate B 的 Expected Effect / 全候选差异接口。
- `mymodules/office_verify/service.py::verify_output` 在受限子进程中调用上述 M1 校验；其资源预算和隔离可复用，但不能仅凭 M1 映射校验宣称完成 Candidate 验证。
- `office_document_request.py` 调用 `office_verify.verify_output` 完成现有 M1 流程；该路径不得改变。
- `mymodules/office_engine_m2/services/workbook_version_service.py` 已定义 `ValidationReceipt`、`record_validation_receipt()` 与 `accept_verified_candidate()`。Receipt 登记会核对 Candidate/附件字节/Session 与 revision 绑定，并把结果登记到版本；只有后续受控的 CB-02 接受操作推进 current。二者不可在 CB-03 中合并成可绕过的写入。
- `office.workbook.version` 保存输入/输出附件、SHA、父版本、Session/Proposal/Document revision、Effect digest、确认引用及验证状态。CB-03 应通过当前用户 ORM 与附件 ACL 读取，不复制版本/附件状态模型。
- 上述代码未显示已实现的 Candidate B 验证入口。该结论仅为源码核查，不代表运行时测试结果。

## 1. Contract Goal

验证已经由 CB-02 登记的真实 XLSX Candidate：确认附件字节与版本链一致、工作簿结构可安全解析、实际差异处于已声明/已授权范围、明确 Expected Effect 得到满足；生成 CB-02 可接受的进程内 typed `ValidationReceipt`。除登记验证结果外，验证服务不改变版本链指针。

## 2. Scope

### 2.1 In Scope

- 只处理 TDD V2.0.2 Candidate B 路径的 `.xlsx` Candidate。
- 以 CB-02 当前用户 ORM 记录为版本、源附件和 Candidate 的权威来源；重读字节并独立重算 SHA-256。
- 对源版本与候选工作簿进行有界、只读解析及实际结构/内容差异检查。
- 按 TDD 规定的类型、公式文本/引用、样式、工作表结构和能力矩阵核验 Candidate；不运行任意代码。
- 消费由受信任调用方提供的结构化、版本化 Effect/授权范围；确定性检查超范围变化与显式 Expected Effect。
- 生成可审计、最小必要的报告和 CB-02 typed `ValidationReceipt`，调用既有 `record_validation_receipt()` 登记结果。
- 为业务可确认风险返回具体风险事实，供后续 CB-04 决策；本 CC 不请求用户确认。
- 对输入绑定错误、损坏、资源超限、未受支持结构、Expected Effect 不匹配等明确分类；不能验证的文件不得输出 `VERIFIED`。

### 2.2 Out of Scope

- 自然语言意图解析、`coverage_declared`、用户确认对话、策略层确认判定、`force_override` 或操作执行。
- OpenAI/Provider 调用、文件编辑、Data Tool、M2 Agent Tool Registry 或新的外部工具。
- Odoo 版本/Proposal/Session 状态管理、附件创建/删除、原子接受、Finalize、交付或回滚；这些归 CB-02/CB-04/CB-06。
- 首轮 Mapping/M1 行为、现有 `office_document_request` 写入与验证路径。
- 任意 Excel 编辑 DSL、通用自然语言/业务语义验证、任意 Python/eval、公式计算/重算。
- DOCX、XLS、XLSM/VBA、宏执行、外部数据连接、第三方库对象编辑。
- 图表、数据透视表、切片器、嵌入对象等超出已裁定并验证的特性保真承诺。
- 新数据库模型、ACL、Record Rule、生产发布或生产附件留存政策实现。

## 3. Preservation Constraints

| ID | 必须保持的行为 | 原因 |
|---|---|---|
| CC-PRESERVE-001 | M1 首轮 Mapping→受控写入→既有 `office_verify` 回读链路和其公开结果语义不变。 | SRS V1.1.0 与既有生产调用方依赖。 |
| CC-PRESERVE-002 | CB-02 是版本、附件与 current/last-valid 的唯一权威；CB-03 只通过 `record_validation_receipt` 登记校验结果，不调用 `accept_verified_candidate`，也不直接写状态/指针。 | 避免双重版本引擎及未经验证的 Candidate 晋升。 |
| CC-PRESERVE-003 | 当前用户 ACL、Record Rules、公司、Thread、Session、Candidate 与附件所有权检查必须先于读取；禁止 `sudo()`、superuser mode、直接 SQL/cursor/驱动访问业务数据或用户可控 context 作为授权。 | CB-02 安全边界与 Odoo 权限。 |
| CC-PRESERVE-004 | `VERIFIED` 只表示文件完整性、结构化 Effect、范围与支持策略验证通过；不表示公式重算或全部自然语言意图被证明。 | TDD §6.3、§4.3。 |
| CC-PRESERVE-005 | Candidate 验证失败、部分验证、权限拒绝、过期或异常都不得推进 current/last-valid/Document Revision；last-valid 保持可用。 | TDD §5–§7 与 CB-02 状态契约。 |
| CC-PRESERVE-006 | 用户明确要求修改表头或既有值时，非空/表头事实本身不得变成永久拒绝；Validator 报告差异/风险事实，是否需要确认由上层 Gate 决定。 | 用户最终决策权与 TDD §4.2。 |
| CC-PRESERVE-007 | 不新增 Agent Tool。产品面现有唯一 Office 工具仍为 `office`；Candidate Validator 是 Odoo 内部受信任能力。 | 本任务明确约束及 TDD 分层。 |

## 4. Validator Input / Output Contract

### 4.1 输入

内部入口仅接受由受信任 Odoo 服务构造的类型化请求，不直接接受 Agent/RPC 原始 JSON 作为权限或证明。最小信息：

| 信息 | 来源与检查 |
|---|---|
| `session_id`, `candidate_version_id` | 当前用户 ORM 可访问的 CB-02 记录；不可只相信调用方 ID。 |
| 源版本/输入附件、Candidate 输出附件 | 从 Candidate 父链读取；检查 owner/company/Thread/Session 关联、附件私有性及 ACL。 |
| `expected_effect` | 结构化、受限的数据对象，包含 schema version、当前输入/父版本绑定、目标/条件/允许影响范围、可确定的预期值/结构结果及不确定项；不得含 Python、表达式代码或任意执行字段。 |
| `authorized_effect_scope` | 由受信任上层传入的范围快照；Validator 不把普通用户布尔值或模型声称当作批准。无须确认的明确单目标操作可为空；如需确认，须同时提供与 Candidate、用户、当前版本和 Effect digest 一致的服务端授权上下文。 |
| 文件策略/预算 | 受控版本化能力策略和 `office_verify` 资源预算。无效/缺失/超限策略不得回退到无界处理。 |

`expected_effect` 是**只读验证描述**，不是编辑/映射 DSL。最小 v1 字段如下；未知键、无效类型或版本不匹配一律拒绝：

| 字段 | 结构与语义 |
|---|---|
| `schema_version` | 固定字符串版本，例如 `1`。 |
| `parent_version_id`, `input_sha256` | 绑定输入工作簿的 CB-02 父版本与真实字节。 |
| `target_scopes[]` | 每项至少含 `scope_kind`（`cell`、`range`、`worksheet`、`workbook_structure`）、可适用的工作表标识与 A1 目标范围/结构目标。不能用历史行号替代当前输入版本的范围。 |
| `allowed_change_kinds[]` | 封闭枚举：`value`、`formula_text`、`style`、`worksheet_structure`、`workbook_structure`；不得执行这些描述。 |
| `expected_assertions[]` | 可验证时提供精确的目标/类型化预期值或结构摘要；没有精确值时允许为空，但此时仅验证范围和声明的粗粒度效果，不能宣称该范围内的业务条件已被穷尽验证。 |
| `selector_digest` / `condition_summary` | 可选的上层选择条件摘要及其 digest；Validator 不解释自然语言或业务谓词，也不凭摘要确认行选择完整。 |
| `unknowns[]` | 尚不确定的目标、效果或结构范围；非空且影响实际 diff 时不得 `VERIFIED`。 |
| `effect_digest` | 上述规范化对象的 SHA-256；必须与 CB-02 Candidate 的 `intent_effect_digest` 一致。 |

`target_scopes` 仅描述可检查的允许范围；禁止操作序列、任意表达式、Python、SQL、映射转换及 Provider 代码。若某个条件不能转成可比较的 workbook scope，按 TDD 语义报告部分验证/澄清需求，不能扩大为新的本地编辑语言。

Validator 必须核对 Candidate 仍是 `candidate_received`、parent 是其记录的输入版本、Session 与 Proposal/Document revision 匹配、附件实际 SHA 与 CB-02 记录相符、Expected Effect canonical digest 与 `intent_effect_digest` 相符。必要绑定不成立时不得登记 Receipt。

### 4.2 输出

`CandidateValidationResult` 为内部结果，至少包括：

| 字段 | 语义 |
|---|---|
| `validation_result` | 仅 `VERIFIED`、`PARTIALLY_VERIFIED`、`FAILED`，符合 TDD §6.3；CB-02 既有 `REJECTED` 状态不作为本 Validator 的新增业务结果。 |
| `feature_results[]` | 每个受检特性的 `SUPPORTED` / `PARTIALLY_SUPPORTED` / `UNSUPPORTED`、实际检查结果与证据引用。特性能力状态与单个 Candidate 结果分开。 |
| `actual_effects[]` | 由本地输入/候选 diff 得到的目标、操作类型及类型化 before/after（按最小必要与访问控制存储/返回）。不保存整个工作簿副本到日志。 |
| `risk_facts[]` | 可确认业务风险事实及目标、原值/新值摘要、影响范围；不作确认决策。 |
| `unclassified_changes[]` | 无法映射到已声明范围的差异；非空时不得为 `VERIFIED`。 |
| `error_code`, `failed_stage`, `safe_message` | 对实际阻断/失败作稳定、脱敏分类；不得泄露文件正文、SQL、路径或凭据。 |
| `receipt` | 只有校验报告完成并由 CB-02 接口成功登记时存在。 |

`VERIFIED`：文件与结构化 Effect 均在明确支持范围内通过。`PARTIALLY_VERIFIED`：文件可解析但至少一项适用结构/效果未能可靠判定，禁止接受为 current/Preview/Finalize。`FAILED`：文件损坏、绑定/哈希错误、未授权差异、越权、资源或安全失败、明确 Effect 失败。调用前 ACL/Record Rule/Session 授权或 stale Gate 失败为 `blocked`/受控 Odoo 错误且不创建验证 Receipt，不伪装成文件内容 FAIL。

## 5. Validation Receipt Schema

CB-03 不创建第二套持久化版本/证明模型，使用 CB-02 的 `workbook_version_service.ValidationReceipt` typed dataclass，并交给既有 `record_validation_receipt(env, candidate_id, receipt)`。字段与 CB-02 v0.3 当前实现一致：

| 字段 | 值来源/绑定 |
|---|---|
| `candidate_version_id` | 当前已授权 Candidate ID。 |
| `candidate_output_sha256` | 从实际输出附件字节独立计算，必须等于 Candidate 的 SHA。 |
| `validator_policy_version` | 显式版本化的候选校验策略标识（建议初始值 `office_verify.candidate.xlsx.v1`；实现前在代码/测试中固定）。 |
| `validation_report_id`、`validation_report_sha256` | 同一 canonical、脱敏验证报告内容的 SHA-256；遵循 CB-02 当前约束，两者相等。 |
| `validation_result` | 仅 `VERIFIED` / `PARTIALLY_VERIFIED` / `FAILED`。 |
| `session_id`, `session_revision`, `proposal_revision`, `document_revision` | 从重新读取的 Candidate/Session 元数据复制并交 CB-02 复验。 |
| `parent_version_id` | Candidate 当前父版本（初始无父版本的 V1 仍由 CB-02 的 M1 proof 规则管理，不走本 CC 编辑 Candidate 路径）。 |
| `input_sha256` | 当前父版本的实际附件字节摘要。 |
| `effect_digest` | 实际验证的 canonical Expected Effect digest，须等于 Candidate 的 `intent_effect_digest`。 |

报告至少记录 schema/policy version、源/Candidate SHA、版本绑定字段、能力特性状态、声明 Effect 摘要、实际 diff 摘要、风险事实、错误/警告、运行预算与完成时间。报告不包含凭据、完整 Prompt 或未经必要性评估的文件正文。验证报告 ID 不是权限令牌；权威性来自 CB-02 受控的进程内 typed receipt + 再校验的附件/版本绑定。

## 6. 校验规则、错误与风险语义

### 6.1 必须校验

1. 输入、候选必须是非空、大小在预算内的实际 XLSX 字节；验证文件名/MIME 声明、ZIP/OOXML 容器与包关系，独立重新打开候选。
2. 比较源和候选工作簿的 Sheet 名、顺序、可见性、维度以及能力策略所列结构；逐单元格比较值/类型（区分 `None`、`False`、空文本、`0`、`0.0`、日期）、公式文本/引用和格式；不宣称公式已计算/重算。
3. 对照 Expected Effect：确定性校验其明确要求实现；对照允许影响范围识别所有实际变化；任何未声明或未确认的范围外变化不得为 `VERIFIED`。
4. 结构操作（Sheet/行列/合并/名称/表格等）只有在输入 Effect 范围明确、对应特性被当前策略声明支持且 diff 可可靠比较时才可能 `VERIFIED`。否则按事实记 `PARTIALLY_VERIFIED` 或 `FAILED`，不得静默忽略。
5. Validator 的比较是输入/候选级，不采用聊天记忆、Provider 文本或 Candidate 声明的 diff 作为真实结果。
6. 任何版本、源字节、候选字节、Effect digest、确认作用域或 Session revision 变化导致绑定不一致时，旧输入/确认不得复用；不得登记与当前 Candidate 不匹配的 Receipt。

### 6.2 能力矩阵执行边界

以冻结 TDD V2.0.2 §6.2 为唯一支持范围来源。本 CC 不把“可由 openpyxl 打开”当作已支持：

| TDD 特性 | CC-03 处理 |
|---|---|
| 基本值/类型、常见样式、常规公式文本/引用 | 作为候选目标能力逐项提供正反例测试；仅实际通过后才可在版本化 policy 标 `SUPPORTED`。公式重算仍不在范围。 |
| 排序、插入/删除、Sheet 增删/移动、合并/冻结窗格、表格/命名范围/条件格式/数据验证 | 必须按最终批准的首期能力矩阵分类；未获裁定或无法证明差异时不得返回 `VERIFIED`。不要求 CC-03 一次支持所有项目。 |
| 图表、数据透视表、切片器、嵌入对象 | 不声称通用保真；无法独立检查且 Candidate 影响到该结构时不得 `VERIFIED`。 |
| VBA/宏、外部连接和外部链接 | 按 TDD 默认拒绝边界；没有单独批准及对应 TV 时不得默认为安全、不得 `VERIFIED`。 |

每个特性的 `SUPPORTED/PARTIALLY_SUPPORTED/UNSUPPORTED` 与单次 `VERIFIED/PARTIALLY_VERIFIED/FAILED` 分别记录。安全拒绝不计作编辑能力 PASS。新增、放宽或改变特性范围须先申请上游设计/矩阵变更。

### 6.3 风险与确认边界

- Validator 只报告可复核事实：现有值被替换、公式文本/引用变化、用户计划声明的 header/data target 发生变化、结构增删/重命名、作用域外变化等；每项带实际目标、旧/新类型化摘要和影响范围。
- 明确单目标和新值的操作可以在非空目标上正常 `VERIFIED`，不因“有旧值”本身拒绝或强制二次确认。
- 批量/删除/公式或结构变化等风险是否需确认，由 TDD §4.2 的上层 Confirmation Gate 决定。CB-03 不作业务取舍、不与用户对话、不写 `force_override`，也不允许确认绕过安全、完整性、权限、资源和真实越界变化。
- 表头、数据区域角色不可由固定行号、Sheet 名、客户模板或字符串猜测。若角色来自调用方的已绑定结构/Effect 描述，应在风险事实中标明该角色是声明信息；无法可靠识别时只报告坐标及实际差异，并记语义角色 `UNKNOWN`。是否要求标准化结构描述是本稿 Open Question。
- 若 Candidate 实际 diff 超出有效确认/声明范围，验证结果不得 `VERIFIED`；不得用用户事后确认或模型解释覆盖已经产生的越界 Candidate。

### 6.4 错误分类

优先复用 `office_verify` 的既有错误代码（例如 `OFFICE_INVALID_OR_MISMATCHED`、`OFFICE_RESOURCE_LIMIT`、`OFFICE_UNSUPPORTED_FEATURE`、`OFFICE_STRUCTURE_MISMATCH`、`OFFICE_TARGET_MISMATCH`）。CB-02/ORM 的 ACL 错误与 `WORKBOOK_VERSION_STALE` 维持其原语义。只有现有代码无法区分 Candidate 绑定或超范围 Effect 时，才可增加最小、稳定、脱敏的 Candidate 错误代码，并在 IHR/ATR 记录映射；不得把内部错误原文直接交给普通用户。

## 7. CB-02 集成接口与信任边界

1. 入口在 `office_engine_m2` 内部 Python service，不是 Odoo 模型的 Agent/RPC 方法，不注册新的 Tool；最终 Agent 产品工具仍唯一为 `office`。
2. CB-03 通过当前用户 ORM 读取 `office.workbook.version`、Session、parent 及对应附件。访问前检查模型/记录 ACL、Record Rules、owner/company/Thread/Session 关系，附件执行 `check('read')`，以 ORM Binary 字段取得真实字节；禁止 `sudo()`、Raw SQL 或直接文件存储旁路。
3. Before validation：校验 source、candidate 和 version metadata 绑定、SHA、state、Session/Proposal/Document revision、parent/current 一致；Candidate 已过期或访问不允许时不运行 parser、不生成 Receipt。
4. 执行本地有界只读验证后，canonicalize 受限报告并构造 CB-02 既有 `ValidationReceipt`。仅调用 `record_validation_receipt`。CB-02 会重新读取附件实际字节、复核 SHA 和版本绑定；若其复验失败，整个登记事务不成功。
5. `record_validation_receipt` 成功后，Candidate 状态依结果转成 CB-02 对应状态。CB-03 不调用 `accept_verified_candidate`，不修改 `current_version_id` / `last_valid_version_id` / `document_revision`。测试必须证明登记前后当前有效版本相同。
6. 伪造/跨候选/跨 Session receipt、SHA/revision/effect 不匹配、重复 receipt、Candidate 与授权范围不同均不得登记。Receipt 不从 RPC 字符串反序列化，不由用户/LLM传入可信标记或 report ID。
7. Receipt 的用户确认上下文由后续受信任 Confirmation Gate 提供；CC-03 只接收并验证其绑定，不实现确认状态存储/交互。当前 CB-02 的 `ConfirmationReceipt` 用途以恢复操作为主；普通编辑确认的精确 typed interface 须在 CB-04 设计评审中与本契约对齐，不能静默冒用 restore receipt。

## 8. 实现白名单与禁止修改范围

### 8.1 允许新增/修改

| 操作 | 文件 | 目的 |
|---|---|---|
| 新增 | `mymodules/office_engine_m2/services/candidate_validator.py` | Odoo ORM/附件访问适配、版本绑定校验、风险事实汇总、typed Receipt 生成与 CB-02 登记调用；不实现接受/确认。 |
| 修改 | `mymodules/office_engine_m2/services/__init__.py` | 仅增加内部服务导出；不得注册 Agent Tool。 |
| 修改 | `mymodules/office_verify/models.py` | 增加候选差异策略/报告的纯 Python typed data contracts（若现有报告足够则不改）。 |
| 修改 | `mymodules/office_verify/verify.py` | 增加复用现有 OOXML parser 的 Candidate diff/Effect 校验入口；保持现有 `verify_output` 行为兼容。 |
| 修改 | `mymodules/office_verify/service.py` | 为 Candidate 校验复用现有受限 worker/资源预算入口；不增加文件路径或文件系统输入。 |
| 修改 | `mymodules/office_verify/__init__.py` | 暴露纯 Python 候选验证 API，不暴露 Odoo 权限或状态操作。 |
| 新增 | `mymodules/office_verify/tests/test_candidate_verify.py` | 中性 XLSX 夹具的独立 Parser/Effect/支持矩阵测试。 |
| 修改 | `mymodules/office_verify/tests/__init__.py` | 注册新纯 Python 测试模块。 |
| 新增 | `mymodules/office_engine_m2/tests/test_candidate_validator.py` | Odoo TransactionCase：ORM/ACL、Receipt 登记和不推进 current 的集成行为。 |
| 修改 | `mymodules/office_engine_m2/tests/__init__.py` | 注册 Candidate Validator TransactionCase。 |
| 新增/追加 | `docs/implementation/IHR-M2-CB-03.md`, `docs/implementation/ATR-M2-CB-03.md`, `docs/implementation/evidence/CB-M2-CB-03/` | 只记录实施后实际基线、运行命令、证据与未完成项；本 CC 起草阶段不创建空 IHR/ATR。 |

仅当实现前的代码审查证明白名单不足以复用现有 `office_verify` 解析器时，停止并申请 CC 修订。不得以“测试方便”为由扩展生产权限、ORM 模型或运行路径。

### 8.2 禁止修改

- 冻结 SRS、TDD V2.0.2、Implementation Plan V2.0.1、CC-01、CC-02 v0.3/v0.3.1及其 IHR/ATR。
- `mymodules/office_engine_odoo/models/office_document_request.py`、M1 Renderer/Mapping/RenderBridge 的业务语义。
- `mymodules/office_engine_m2/services/workbook_version_service.py`、`models/office_workbook_version.py`、Session revision、版本字段、ACL/Record Rules；需要更改即停止并升级 CC/上游设计。
- Provider Adapter/配置、真实外部调用、Chat Completions、Agent Tool Registry、用户界面/确认交互、CB-04..07 文件或功能。
- Odoo 官方模块、Manifest/依赖/数据库 schema/ACL/Record Rule/附件留存设置。
- 真实业务数据或附件；Provider 或网络调用；服务重启/模块升级/数据库写入（编码授权后适用的 Odoo TransactionCase 除外，且需另有环境授权）。

## 9. 测试矩阵与验收标准

所有测试使用中性合成 XLSX 和类型化 Effect；不得使用固定业务模型、客户、模板名或业务值定义 Validator 规则。

| ID | 测试行为 | 预期 |
|---|---|---|
| CC-TEST-001 | 有效 XLSX：在声明范围内把现有值从 10 改为 15，非目标 Sheet/单元格、公式、格式不变 | 支持能力实测后才可 `VERIFIED`；回读目标与实际 diff 均符合，RiskFact 如实描述旧值替换，不因非空自动失败。 |
| CC-TEST-002 | 用户意图明确声明 Sheet 中 header target 改名 | 验证器允许在授权范围内检查/验证该修改；风险事实含实际目标和前后类型化值。无 header metadata 时不得按固定行/模板猜角色，应标 `UNKNOWN`。 |
| CC-TEST-003 | 覆盖非空文本、数字、公式 | 确定性报告 before/after、公式文本差异与目标范围；是否要求用户确认由上层 Gate 决定。 |
| CC-TEST-004 | Candidate 在授权单元格/区域外额外改值或格式 | `FAILED` 或安全阻断；不得登记 `VERIFIED` Receipt。 |
| CC-TEST-005 | 明确授权且当前能力策略支持的 Worksheet 新增、删除、重命名/移动 | 只验证精确声明的结构 Effect；实际结果符合时可按策略验证；同类未声明变化不能被忽略。未批准/不支持能力不得标 `SUPPORTED`。 |
| CC-TEST-006 | 非法 XLSX、损坏 ZIP、OOXML 关系错误、无法读取工作簿 | 分类为技术失败，永不 `VERIFIED`，不升级 current。 |
| CC-TEST-007 | 输入附件/输出附件字节 SHA 与 CB-02 元数据不一致 | Receipt 不登记；Candidate 状态/current 按 CB-02 不变量保持安全。 |
| CC-TEST-008 | Candidate 属于其他 Session、parent、owner/company/Thread，或 Session/Proposal/Document revision 已变化 | ACL/Record Rule 或 stale 拒绝；不调用接受、不推进指针、不泄露不可访问记录内容。 |
| CC-TEST-009 | 伪造 dict/string Receipt、报告 ID、policy 或他 Candidate 的 typed Receipt 重放 | 被 CB-02 typed interface 与绑定检查拒绝；不得改变 Candidate/current。 |
| CC-TEST-010 | Receipt 登记后立即读 Session current/last-valid/revision | Candidate 仅为验证状态；current/last-valid/Document Revision 与验证前完全一致。 |
| CC-TEST-011 | `PARTIALLY_VERIFIED`、`FAILED` 或不支持结构 | Receipt/结果按 TDD 区分；均不能进入 accepted/current/普通 Preview/Finalize。公式文本正确不得写成重算通过。 |
| CC-TEST-012 | `None`、`False`、`""`、`0`、`0.0`、日期及日期时间变化 | 独立解析保留类型与空值语义；零值不与 False 混淆。 |
| CC-TEST-013 | 文件大小、压缩比、ZIP entries、XML 节点、Cell 数、内存/时限超预算或恶意 XML | 资源/安全失败关闭；不回退到无界解析、不产生成功 Receipt。 |
| CC-TEST-014 | M1 和 CB-02 兼容回归 | 既有 M1 `verify_output`/`office.document.request`/RenderBridge 行为不变；CB-02 版本链接受测试保持通过；新 Validator 只登记结果，不自行接受。 |
| CC-TEST-015 | Agent 工具架构静态/行为核查 | 仍只有外部 `office` Tool；CB-03 内部函数不被 Odoo RPC/Agent Tool Registry 暴露。 |

### 9.1 分层验收

- **Contract Verified**：纯 Python 中性夹具对解析、diff、类型、Effect、能力/候选双状态及错误分类有完整行为断言。不得将安全拒绝计为编辑功能 PASS。
- **Integration Pending**：ORM、真实私有附件 bytes、Candidate/Session/revision 绑定、typed Receipt 登记、当前指针不推进、ACL/Record Rules 与 TransactionCase 尚未有真实运行证据。
- **Final Accepted — CB-03 scope only**：契约测试、Odoo TransactionCase、CB-02 交接、M1 兼容回归及 IHR/ATR 证据全部满足，且负责人接受。不得宣称 Provider/Browser/Finalize 或 CB-04/CB-06 全链路通过。
- **HVR**：本 CC 不修改用户界面或用户可见交互；除非后续实现增加 UI 范围，否则不要求人工 HVR。

预期命令（执行授权后根据项目测试入口核实；本轮不运行）：

```sh
./venv/bin/python -m pytest mymodules/office_verify/tests/test_office_verify.py mymodules/office_verify/tests/test_candidate_verify.py
./venv/bin/odoo-bin -c odoo.conf -d <approved_nonproduction_db> -u office_engine_m2 --test-enable --stop-after-init --test-tags /office_engine_m2
```

TransactionCase 与 Odoo runtime 结果须记录数据库类型、升级结果、实际测试发现数、PASS/FAIL/ERROR/SKIP；不以测试源码数、纯 Python 测试或 CB-02 旧报告替代本 CC 运行证据。并发验证不是 CB-03 重复验收；复用 CB-02 的已接受版本服务测试，不重新运行其 race。

## 10. Stop Conditions

任一项成立即停止相关实现，不放宽断言、不绕过边界：

1. Implementation Plan §0.2 的正式 SRS 变更/数据安全门未满足，或 CB-02 尚未由负责人 Final Accepted；不得以本 CC 冻结替代 Coding Authorization。
2. TDD §6.2 对影响本 CC 验收的首期特性矩阵尚无产品/安全裁定，且不能在该项明确 `UNSUPPORTED`/`PARTIALLY_SUPPORTED` 的条件下安全验收。
3. Expected Effect/authorization scope 无版本化类型或其与 CB-02 digest 无法绑定；不得自行建 DSL/Receipt 框架。
4. Header/data area 等语义角色没有可信来源；不得通过模板名、固定行列、表头词汇或 fixture 加特例推断。
5. 附件必须通过 sudo、SQL/游标、直接文件存储或绕过 Odoo ACL 才能读取。
6. 需要修改 CB-02 版本服务/字段/权限、M1 行为、Provider/Tool 或名单外文件。
7. 已实现 Validator 无法可靠枚举某个影响候选结果的文件结构；不得把 UNKNOWN 静默当安全。
8. 发现外部数据处理、真实业务附件、服务/DB 变更或任何本 CC 明确禁止的副作用。

## 11. Open Questions / Owner Decisions

1. **首期 Excel 特性矩阵**：按 TDD §6.2，哪些可进入首个 `SUPPORTED` policy，哪些明确保留 `PARTIALLY_SUPPORTED/UNSUPPORTED`？排序/插删/Sheet 增删移动、合并/冻结、表格/命名范围/条件格式/数据验证必须以负责人/产品安全裁定和测试证据为准；图表/透视表/宏等不得默认纳入。
2. **Header/data-region 语义来源**：TDD 要求结构/目标比较，但未定义从何处得到可审计的 Header/Data Range 身份。建议由受信任、绑定到父版本的 Effect/Structure 描述显式提供；在负责人确认前不采用自动启发式，不对语义角色做 `VERIFIED` 判断。
3. **普通编辑确认上下文**：CB-02 当前 `ConfirmationReceipt` 主要绑定恢复操作。CB-03 需接收将来 CB-04 的受信任编辑授权上下文；需要 CB-04 在不改 CB-02 权威边界的前提下提供其 typed binding。若需要修改 CB-02 字段或用户交互设计，先提交跨 CC 变更申请。
4. **TDD/SRS 门禁**：TDD V2.0.2 §0.4 对 SRS 的 Candidate B 变更仍是提案；Implementation Plan §0.2 要求正式版本化 SRS 变更后才开始受影响编码。仅影响本地 Candidate 验证的具体范围由负责人确认是否受此 Gate 全量约束。
5. **CB-02 正式状态**：当前证据为 `READY FOR FINAL ACCEPTANCE`；负责人完成并记录 Final Accepted 后，才满足 Plan 的 CB-02→CB-03 依赖门。此事项不构成 CB-02 技术证据失败，也不在本 CC 中重复设计或测试 CB-02。

## 12. Implementation Handoff Criteria

本 CC 通过文档评审后，也只有在以下条件全满足时才可另行签发 Coding Authorization：

- 负责人记录 CB-02 `Final Accepted`；CC-02 的 `Release Gate OPEN` 仍独立限制生产发布，不自动阻断合成数据开发。
- 按 Implementation Plan §0.2 处理本 CC 适用的 SRS / 数据安全 / TDD §6.2 产品决策 Gate。
- 负责人冻结本 CC v0.1（或后续审定版本）并单独授权实现。
- 编码前做一次仅限白名单的实现审查，确认 CB-02 `ValidationReceipt`、Attachment ORM read、`office_verify` API 与模块加载方式未变化；若变化则更新 CC/计划而非猜测。
- 明确批准 Odoo TransactionCase 数据库及运行/升级操作。不得继承前 CC 的数据库写入或服务操作授权。
- 实施者确认本次不调用 Provider、不用真实业务文件，且没有新增外部 Agent Tool。

## 13. Traceability

| 本 CC 项 | 上游依据 | 验证 |
|---|---|---|
| CC-CHANGE-001：独立读取 Candidate/parent、字节哈希与版本绑定 | TDD §5.1、§6.1；CB-02 v0.3 §§4–7 | CC-TEST-007/008 |
| CC-CHANGE-002：本地受限 XLSX diff、结构/类型/公式/格式与 Effect 校验 | TDD §4.1、§6.1–6.3；Implementation Plan §6 | CC-TEST-001–006、011–013 |
| CC-CHANGE-003：构造并登记 CB-02 typed ValidationReceipt，不推进 current | TDD §5.2、§6.3、§8.1；CB-02 v0.3 §§4.1、6 | CC-TEST-009/010/014 |
| CC-CHANGE-004：输出业务风险事实而不代做确认决定 | TDD §4.2、§6.1、§8.2；`docs/AGENTS.md` | CC-TEST-002/003/005 |
| CC-PRESERVE-001..007：M1、CB-02、安全、验证等级与唯一 Tool 边界 | SRS V1.1.0；TDD §§2、4–8；CB-01、CB-02 | CC-TEST-004/008–015 |

## 14. Stop / Review Disposition

本文件是执行契约草案，不是编码授权。不得因 Draft 包含测试命令、白名单或技术建议而执行修改、测试、Provider 调用、Odoo 模块升级或数据库操作。若 CC-03 评审要求改变冻结 TDD/SRS，先走独立的上游版本变更。

## 15. 版本记录

| 版本 | 日期 | 说明 | 状态 |
|---|---|---|---|
| v0.1 | 2026-11-08 | 基于冻结 TDD V2.0.2、实施计划 V2.0.1、CC-01/CB-02 实际接口和 `office_verify` 只读核查形成首稿。 | **DRAFT — NOT AUTHORIZED FOR IMPLEMENTATION** |
