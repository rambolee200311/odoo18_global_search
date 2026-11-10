<!--
Source template: docs/skill/odoo-project-workflow/references/templates/Planning/IMPLEMENTATION_PLAN_TEMPLATE.md
Source version/status: v0.1; Draft
Template synchronization check: PASS, 2026-11-06
-->

# Office Engine M2 — Expression, State Continuity and Outcome Implementation Plan

## 文档信息

| 项目 | 内容 |
|---|---|
| 文档 | IMPLEMENTATION_PLAN_office_engine_m2_state-continuity |
| 版本 | v0.1 |
| 状态 | DRAFT — NOT AUTHORIZED |
| 基线有效性 | IMPACT REVIEW REQUIRED |
| 项目 / 模块 | Odoo 18 CE / Office Engine M2 |
| 计划负责人 | 待指定 |
| 创建日期 | 2026-11-06 |
| 基线日期 | 2026-11-06 |
| 批准 / 基线记录 | Phase B v0.3 已由用户于 2026-11-06 批准冻结；本计划尚未审批、未冻结，不授权 CC 创建或编码 |

### 冻结门禁

本文件是根据冻结的 Phase B v0.3 与当前 M2 代码起草的后续范围计划。它不替换既有 FROZEN 的 IMPLEMENTATION_PLAN_office_engine_m2 V1.0.0，也不修改 SRS、TDD、TV 或业务规则。计划范围仅覆盖表达式、Proposal 连续性、意图覆盖/结果核验和用户结果契约的后续实现。

本计划引用既有冻结的 SRS、TDD 与 Phase B 设计；但当前正式 TDD V1.1.0 / 动态行补充文档尚未显式记录 Phase B v0.3 的全部契约。本计划因此标为 IMPACT REVIEW REQUIRED：CC-M2-B-01 必须完成逐条对齐，确认无需 TDD 修订，或按 TDD 变更流程先完成必要修订并重新冻结。未完成前不得创建后续 CC 或实施。

### 首个 CC Gate 检查表

- [x] M2 SRS V1.0.0 与交互补充 V1.1.0 均为冻结输入；更早的总体 Office SRS 按 TDD 引用的版本适用。
- [x] DDD 适用性为 N/A；依据为冻结的 M2 TDD V1.0.0/V1.1.0 决策。
- [ ] TV 未通过项、历史失败及其与本计划范围的关系已逐项核对；保留 TV 报告原始 FAIL / INCONCLUSIVE 状态，不以计划替代豁免或重测。
- [ ] TDD V1.1.0、动态行补充和 Phase B v0.3 的条款对应关系已完成并留证；必要的 TDD 修订已获批、冻结，或记录为无冲突。
- [ ] 本 Implementation Plan 获评审批准并基线化。
- [x] 本计划每个阶段已映射到拟建 CC ID，且每个拟建 CC 映射回本计划阶段；实际 CC 尚未创建。
- [ ] 首个 CC 的环境、测试启动方式、已知测试统计差异和剩余未通过项处置已登记。

**Gate 结果：BLOCKED — 本文件仍为草案，且基线影响审查、测试证据核对及计划批准尚未完成。不得据此创建 CC 或开始实施。**

## 1. 上游基线

| 权威 / 输入 | 版本 / ID | 状态 | 位置 / 本计划用途 |
|---|---|---|---|
| M2 SRS 主基线 | V1.0.0 | FROZEN | docs/requirement/SRS_office_engine_m2_ai_mapping.md；业务需求权威 |
| M2 SRS 交互补充 | V1.1.0 | FROZEN | docs/requirement/SRS_office_engine_m2_ai_mapping_v1.1.0.md；覆盖多轮自然语言修改、版本绑定确认与预览新鲜度 |
| DDD | N/A | 已由负责人批准 | 由冻结 M2 TDD 记录；若实施发现新稳定领域不变量，应按变更流程重新评估 |
| M2 TV Plan / Report | V0.2 / V1.1 | 冻结输入；报告结论 PARTIAL，保留各项实际状态 | docs/verification/TV_office_engine_m2_plan.md、docs/verification/TV_office_engine_m2_report.md；历史 Spike 失败及不确定结论不得改写 |
| M2 TDD 主文档 | V1.0.0 | FROZEN | docs/design/TDD_office_engine_m2.md；既有 M2 架构和上游边界 |
| M2 TDD 交互补充 | V1.1.0 | FROZEN | docs/design/TDD_office_engine_m2_v1.1.0.md；Session、Proposal、Preview / Finalize 与原生聊天基线 |
| M2 动态行 TDD 补充 | V1.1.0 | FROZEN | docs/design/TDD_office_engine_m2_dynamic_rows_addendum_v1.1.0.md；repeat-row 数据授权和执行语义 |
| Phase B 技术设计 | v0.3 | FROZEN — 用户于 2026-11-06 批准 | docs/B技术设计草案.md；本计划的补充契约基线，批准不代表编码授权 |
| 既有 M2 Implementation Plan | V1.0.0 | FROZEN | docs/implementation/IMPLEMENTATION_PLAN_office_engine_m2.md；初始 M2 / Skill 范围，保持不变，本计划只规划后续连续性范围 |
| Phase A / A2 审计 | Phase A / A2 | 只读审计报告；含 UNVERIFIED 项 | docs/A审计报告.md、docs/A2审计报告.md；运行身份、Thread 12063、表达式和结果传递证据限制 |

本计划使用的当前源码快照为分支 main、HEAD 3ccb863430cd33b70952fd57cadc7624d284e3cf。计划起草时工作区含既存未跟踪的 .coverage、Phase A / A2 报告及 Phase B 文档；它们均予保留。本计划本身为新文档，起草时没有暂存或提交。

### 基线解释与未决事项

Phase B v0.3 的用户冻结记录已经写入该设计文档。设计中仍保留的 §13 产品/技术问题并未因整体冻结而被默认为某个选项已获单独决定：表达式兼容/空值细则、资源限制、Outcome 到既有字段的投影与兼容窗口、Provider 超时后的界面体验、真实验收环境仍按开放决策跟踪。各问题应在受影响 CC 进入前有明确处置；不得由实施者临时选择。

SRS OPEN-M2-002 / OPEN-M2-003 继续阻止未获批业务字段、模板内容或真实业务样例发送给外部 Provider；合成数据验证不因此被禁止。OPEN-M2-005 阻止未经批准的性能目标承诺。OPEN-M2-006 的 Skill 删除/历史策略不属于本计划范围。TV-M2-001 的 FAIL、TV-M2-002 / 004 的 INCONCLUSIVE 等历史结论保持原样，是否为本计划的适用未通过项须在 CC-M2-B-01 中依据原证据判断。

## 2. 目标与范围

### 2.1 目标

在不改写现有完整 Proposal 重编译架构、不新增并行文件引擎的前提下，将冻结 Phase B v0.3 中的有限类型表达、Proposal 多轮状态、确认最终 Effect、Intent Coverage / Execution Verification 分离及用户可理解结果契约接入现有 M2 工具链。

最终应能从当前用户请求追踪到结构化操作、表达式求值上下文、Proposal revision、确认 Effect、保存后文件回读、Preview / Finalize 附件事实和 Agent 对用户的结果说明；无法结构化的请求须显式报告，不能静默忽略。

### 2.2 范围内

- 现有 office_mapping_verify 表达式/Transform 契约的有限扩展与旧 Mapping 读取兼容。
- 基于当前授权数据、逐目标上下文的类型安全求值和确定性文件回读断言。
- 当前完整 Proposal 的 patch、规则身份、历史恢复、dormant 规则不自动激活及确认失效。
- 绑定规范化表达式、求值数据基线、解析目标集合、具体写入值/结构 Effect、原值与覆盖范围的确认范围。
- Intent 的 Agent 声明清单、Operation / Expected Effect 对应检查、执行验证及未覆盖要求的显式反馈。
- 复用现有结果字段的 outcome 适配、Preview/Finalize 与 delivery 区分、超时后的状态恢复和安全幂等。
- 保持原生 llm.thread 工具循环、当前用户 ORM ACL / Record Rules、office_core 单一执行入口和保存后 Validator 门禁。
- 中性 Office 文件单元测试、Odoo TransactionCase、真实 Provider / 浏览器 E2E 与最终附件文件回读证据的分层规划。

### 2.3 范围外

- Operation DAG、事件总线、事件溯源、新版本引擎或独立工作流平台。
- 任意 Python、eval、任意业务脚本或不受限公式执行。
- 改写 Odoo 官方 Addon、绕过 ORM 权限或使用 sudo()。
- 新建另一套可执行生产 Mapping Writes 的路径，或直接暴露临时路径文件 API。
- 重新设计 Office Core / Adapter；若计划阶段发现其不满足冻结约束，停止受影响 CC 并回到 TDD / TV。
- 模板、坐标、业务模型、字段、客户、产品、联系人或库存特例。
- 私有 Skill 生命周期扩展、M1/M3 业务范围扩张、DOCX 新操作、任意 Provider 启用。
- 在本计划阶段实际编码、测试执行、数据库修改、模块升级、服务重启、提交或推送。

### 2.4 约束

- 保留原始 Office 文件 + 当前授权数据 + 当前完整 Proposal → Canonical Operation List → 模拟/确认 → 执行 → 保存后验证 → Preview / Finalize → 用户结果反馈的既有主链。
- 继续使用线性操作顺序；repeat_rows 结构展开及其公式/派生写入仍在现有统一执行链内。
- 用户确认仅解除精确 Effect 范围的可确认业务风险，不绕过权限、文件安全、资源预算和验证失败门禁。
- 不将 LLM 对自然语言的理解、覆盖清单或工具调用完成消息表述为独立语义证明。
- 公式表达式读回不得描述为 Excel 重算；若预期结果要求公式计算，须另有真实公式引擎证据。
- 设计建议、计划的测试和历史测试记录不能写成当前实现或本次测试已通过。

## 3. 就绪前置条件

| 前置项 | 所需状态 / 证据 | 责任方 | 优先级 | 当前状态 |
|---|---|---|---|---|
| Phase B 冻结 | v0.3 文件包含批准记录、状态 FROZEN，且批准范围明确 | 技术负责人 / 审批者 | P0 | 已由本轮用户批准并记录 |
| SRS / DDD | SRS V1.0.0 + V1.1.0 Frozen；DDD N/A 依据留档 | 需求负责人 | P0 | 文件显示已冻结；未重新审查全文所有需求 |
| TDD 基线对齐 | M2 TDD V1.1.0、动态行补充与 Phase B v0.3 的逐条适配；如果冲突/缺失，先走 TDD 修订审批 | 技术负责人 | P0 | OPEN；计划基线有效性 IMPACT REVIEW REQUIRED |
| TV 历史结果 | 核查 TV-M2-001 FAIL、TV-M2-002 / 004 INCONCLUSIVE 等是否进入本计划验收，明确回归或已授权处置 | QA / 技术负责人 | P0 | OPEN；原结果保留 |
| Odoo Runtime 身份 | 当前 PID、解释器、addon path 与导入模块身份/指纹；源码与运行代码差异可判定 | 环境负责人 | P0 | UNVERIFIED（Phase A / A2）；本轮未连接或重启服务 |
| 测试运行基线 | 复核现有 Python 和 Odoo 测试选择器/测试加载方式，产生不含臆测的基准命令与统计 | QA / 技术负责人 | P0 | 未执行；未来 CC-M2-B-01 |
| Odoo 测试环境 | 隔离数据库和 filestore，或每个实施 CC 对共享开发库的明确测试授权及回滚/清理证明 | 环境负责人 / 审批者 | P0 | 未确认；不得假定共享库可写 |
| Provider 数据政策 | 真实用户数据发给 Provider 前关闭 SRS OPEN-M2-002 / 003；否则使用合成 Provider 输入 | 数据 / 隐私负责人 | P0（真实数据） | OPEN；仅阻塞真实业务内容外发 |
| Provider / Browser 凭据 | 可用当前获准 OpenAI Provider gpt-5.6-luna、独立验收 Thread、附件下载权限；运行窗口记录到 HVR | 环境 / QA | P1 | 未验证 |
| Odoo 测试统计差异 | 解释或登记历史日志 office_engine_m2: 166、office_engine_odoo: 26 与 runner 最终 160 的差异，不猜测原因 | QA / 技术负责人 | P0（基线可信度） | OPEN；现有 ATR/IHR 有该计数差异但未解释 |
| 当前代码与未提交内容 | 以 CC 开始时的 Git SHA 和状态重建计划基线，避免覆盖当前及后续未提交文件 | 实施负责人 | P0 | 本轮观察到 main@3ccb863…；存在未跟踪文件 |

P0 环境缺口不会被计划文本视为已解决。计划评审可进行；任何依赖未满足前置项的 CC 必须维持 BLOCKED。

## 4. 实施阶段与拟建 Coding Contracts

以下 CC ID 均为拟建编号，不代表 CC 已创建、批准或授权实施。阶段顺序基于实际依赖，而非 Phase B 章节机械排序。所有实现均须先按各 CC 单独冻结的契约执行。

### Phase 0 — Runtime、基线与 TDD 对齐

**拟建 CC：** CC-M2-B-01 — Runtime & Baseline Alignment

**目标与输入依赖**

以冻结 SRS、TDD、Phase B v0.3 和当前 HEAD 为只读基线；对 8091 模块身份、已有失败证据、测试选择器、计数差异及 TDD 对齐作出可审计判断。此阶段不实现新行为。

**Entry Criteria**

- 本 Implementation Plan 完成评审批准并标记有效基线。
- 明确可读取日志、测试环境和运行身份所需权限；不重启服务。
- 既有工作区未提交内容已记录，CC 给出精确允许检查范围。

**In Scope**

- 导入路径、当前 addon 路径、测试入口和既有调用图取证。
- 核对历史 Thread / 确认异常的持久化证据可用性；证据缺失就标 UNVERIFIED。
- 对 B v0.3 与 TDD V1.1.0 / 动态行补充做逐条覆盖映射。
- 核查 TV 与旧计划中的未通过项、skipped 项和测试计数差异。

**Out of Scope**

- 不重启 Odoo、不升级模块、不修运行环境、不修改代码或测试。
- 不追查或修补未经证据确认的历史生产异常。
- 不将测试源码或旧 ATR 结果替代当前运行证据。

**契约 / 代码影响**

只产生基线审查和测试命令清单，不改变产品接口或代码。预期证据位置为本计划目录下的新 IHR/基线附件（实际名称由 CC 冻结）；不写入业务数据库。

**测试要求**

不运行功能测试；核对可复现命令、测试收集范围、Odoo addon 导入限制、历史统计来源和当前失败/skip 列表。

**验收证据**

- 运行模块身份结论为 MATCH / MISMATCH / UNVERIFIED，附直接证据。
- 每个 B 契约映射到正式 TDD 条款或有审批的 TDD 变更需求。
- 166 + 26 与 160 若不能解释，保持 OPEN，禁止推测。
- 逐项记录历史失败的实际状态和本计划处置；不得修改历史报告。

**停止 / 回退**

发现 TDD 与冻结 B 有实质冲突，或测试环境操作会触及共享业务数据时，停止受影响工作并退回设计基线/环境负责人；保留审计材料，不改服务或数据库。

**Exit Criteria**

Phase 0 证据完成并评审通过；未解释的统计差异和历史失败有明确 owner / 状态；TDD 对齐完成或计划中对应实施阶段仍为 BLOCKED。该阶段本身不能放行后续代码 CC，除非计划基线有效并且各自 Entry Criteria 满足。

### Phase 1 — Typed Expression Contract

**拟建 CC：** CC-M2-B-02 — Typed Value Expression

**上游依赖：** CC-M2-B-01；Phase B v0.3 §3；TDD 对齐记录。

**Entry Criteria**

- concat、coalesce、arithmetic、date_offset、null_result、隐式类型转换的产品语义已按 B §13 决定或以批准的解释记录。
- 旧 Proposal 的解析与兼容策略已明确。
- 使用中性数据夹具；不引入具体 Odoo 业务模型或字段作为单位测试前提。

**In Scope**

- literal、field、concat、coalesce、arithmetic、date transform 的受限类型化表达与规范化。
- Decimal、日期、None、False、空字符串、0、0.0 的区分。
- 按每个实际目标上下文求值，生成可回读的 expected typed value。
- 表达式错误的目标、表达式路径和安全诊断。
- 冻结 B 要求的资源上限仅在中性边界/压力测试后定值。
- 保持 XLSX 公式与 Mapping 表达式边界。

**Out of Scope**

- eval、任意 Python、任意 Excel 函数、变量动态取代码、模型生成代码。
- 由核心表达式解析器调用 Odoo ORM；字段数据仍由现有授权检索链准备。
- 货币汇率、隐式币种精度、公式重算。

**契约变化**

以 B §3 的版本化表达树和现有 Proposal 字段为基准；由本 CC 冻结实际 JSON Schema、向后读取旧 Proposal 的规则及字段型别转换表。Canonical Document Operation List 仍是唯一执行输入，不引入平行渲染接口。

**Code Impact**

优先核实及可能涉及：
- mymodules/office_mapping_verify/contracts.py、parser.py、transforms.py、validator.py；
- mymodules/office_engine_m2/services/render_bridge.py 中 _m1_value、_compile_plan 及逐行上下文求值；
- mymodules/office_mapping_verify/tests/test_parser.py、test_validator.py；
- mymodules/office_engine_m2/tests/test_render_bridge.py、test_native_chat_integration.py。
仅在验收证明操作契约无法承载结构化值时，才可提案调整 canonical schema；须先评估 TDD/office_core 影响并单独批准，不得从此 CC 自动扩围。

**Test Requirements**

- literal/field/组合/嵌套与类型拒绝；
- 逐目标求值，不同记录值互不串行；
- False、0、0.0、None、空字符串和日期序列化边界；
- 表达式执行结果与保存后文件读回值比较；
- 公式读取不宣称重算；
- 同类不同输入、类型反例、资源边界和旧 Proposal 回归。

**Acceptance Evidence**

pytest 命令、实际通过/失败/skip 数及 ATR；至少一个保存后重开真实 XLSX 的中性回读文件/断言；旧 Proposal 读取兼容结果；未验证的资源限制及类型限制明确记录。

**Rollback / Stop**

表达式 Schema 不兼容旧 Proposal、求值差异不能被 readback 证明或资源限制未定时，关闭新表达式写入入口并保留旧 Proposal 只读/执行兼容路径；不得删除既有字段映射。发现需要任意表达式能力时停止并回到 Phase B/TDD。

**Exit Criteria**

冻结表达式 Schema 及边界测试通过，旧方案可安全读取；所有值型别保持区分；目标级求值与文件回读通过。此 CC 不含 Odoo 集成或浏览器验收声明。

### Phase 2 — Proposal Patch、连续状态与确认 Effect

**拟建 CC：** CC-M2-B-03 — Proposal State & Exact Confirmation

**上游依赖：** CC-M2-B-01、CC-M2-B-02；B §5；SRS V1.1.0。

**Entry Criteria**

- Expression/rule identity 稳定定义。
- TDD 对 Session/Proposal revision 和 pending confirmation 的兼容影响已审查。
- 测试数据库/filestore 及测试用户 ACL 已准备并记录。

**In Scope**

- 以完整 Proposal 重编译保留 set/remove/clear/整份 restore 语义。
- dormant/out_of_scope 规则保留于历史但不执行；重新进入范围不自动激活；只有用户明确引用规则重新启用或恢复整份已确认 Proposal 才重新纳入当前编译。
- 不支持局部 Restore；历史 Restore 后创建新当前 revision 并重新编译、授权、验证。
- 确认绑定规范化表达式、数据求值基线、解析目标集合、具体写入值/结构 Effect、原值和覆盖范围。
- 基线或 Effect 变化后使旧确认失效并重算风险；确认答复/force_override 不扩大范围。
- 重复 Patch 的幂等识别与失败/待确认时的旧 Preview 保护。

**Out of Scope**

- 对上一 Preview 进行隐式字节增量修改。
- 新建事件溯源或 Effect event ledger。
- 业务数据写入、ACL 绕过和模板专用重定位。

**契约变化**

仅按 B §5 和本 CC 冻结的既有 Session/Proposal 扩展。优先使用 session revision、proposal revision、历史 snapshot、pending confirmation 和 preview binding；任何新持久化列必须说明无法复用的现有状态证据及升级/兼容策略。

**Code Impact**

- mymodules/office_engine_m2/models/office_mapping_session.py：_save_mapping_from_service、pending confirmation、preview/confirmation 状态服务方法。
- mymodules/office_engine_m2/services/mapping_service.py：restore_proposal_revision、当前 Proposal 与规则读取。
- mymodules/office_engine_m2/models/office_mapping_tools.py：_merge_mapping_patch、_cell_override_confirmation_gate、_office_save_mapping_preview_impl、office_restore_proposal_revision。
- mymodules/office_engine_m2/services/render_bridge.py：完整 Proposal 重编译及数据/目标指纹输入。
- mymodules/office_engine_m2/tests/test_mapping_session.py、test_native_chat_integration.py、test_conversational_preview.py、test_render_bridge.py。

**Test Requirements**

确认前无写入；确认后精确执行；表达式不变但数据变化使实际值变化时旧确认失效；目标集、文件、原值、Effect 范围变化失效；范围外额外目标拒绝/重新确认；dormant 目标重新入范围不自动应用；显式重新启用/整份已确认 Proposal Restore 后重新计算；失败不污染最后有效 Preview；重复请求不重复插行/副作用；ACL、路径和文件完整性限制仍有效。

**Acceptance Evidence**

Odoo TransactionCase 与中性 Python 回归分别记录；Session/Proposal revision、confirmation digest、目标集和 Effect 证据；候选 XLSX 回读与失败路径的前后有效版本证明。不能以模拟状态字段代替 ORM 和真实文件验证。

**Rollback / Stop**

持久化迁移失败、旧 Proposal 状态不可确定或确认签名不能覆盖精确 Effect 时停止相关数据写入；保留现有有效 Preview/Proposal，回退新入口但不得把失效确认恢复为有效。必要的 TDD 偏移须先获批并反向冻结。

**Exit Criteria**

多轮成功/待确认/失败/恢复路径均从原始模板 + 当前完整 Proposal 重编译；确认后最终 Effect 完全匹配且范围外不写；历史失败与未验证项保留。

### Phase 3 — Intent Coverage 与 Execution Verification

**拟建 CC：** CC-M2-B-04 — Declared Coverage & Readback Effects

**上游依赖：** CC-M2-B-02、CC-M2-B-03；B §4；现有 office_core/Validator 保存后验证链。

**Entry Criteria**

- 三层结果的接口和消费方已冻结：execution_verified、coverage_declared、task_completed。
- Coverage 清单不能被描述为自然语言完整性证明。
- Expected Effect 可被映射至规范操作和文件回读方法；无法结构化要求有显式反馈通道。

**In Scope**

- Agent 声明本轮识别要求及 covered / not_covered / uncertain 状态、来源消息引用和对应 operation/effect。
- 服务端验证声明结构与操作/结果引用，不独立声称识别所有自然语言意图。
- 文件回读按结构化预期检查目标、类型化值、公式文本/结构和非目标保持。
- 无法结构化、未覆盖或不确定的用户要求显式进入 Agent 反馈，阻止 task_completed。
- 把 Execution Verification 与 Agent 对要求的 Coverage 声明分别保存/返回。

**Out of Scope**

- 第二个 LLM 审核器、完整自然语言语义验证、自动补造缺失要求。
- 让 LLM 判定 ACL、文件验证成功或用户确认有效。
- 修改 office_core 的统一执行入口或绕过 office_verify / 既有保存后验证。

**契约变化**

复用 Phase B §4 的最小结构；若现有工具参数/结果无法带入声明，限定增加兼容字段并保留旧消费者过渡方式。工具 success 仍仅说明结构化操作结果，不等同 task_completed。

**Code Impact**

- mymodules/office_engine_m2/models/office_mapping_tools.py：office_prepare_context、office_save_mapping_preview 及结果构造。
- mymodules/office_engine_m2/services/render_bridge.py：Expected Effect 与编译/回读结果绑定。
- mymodules/office_engine_m2/models/llm_thread.py 与 M2 Tool Schema/Prompt 消费链：Agent coverage 和用户解释。
- mymodules/office_mapping_verify/validator.py 与 mymodules/office_verify/verify.py：仅核实既有回读契约是否可复用；不建立并行 Validator。
- mymodules/office_engine_m2/tests/test_response_compatibility.py、test_render_bridge.py、test_native_chat_integration.py。

**Test Requirements**

意图条目缺失/未结构化时不得 task_completed；已声明 requirement 不映射操作时拒绝完成声明；工具 success 但 readback 不满足 Expected Effect 时失败；公式文本和数字类型真实回读；非目标值/格式保护；Agent 文案不得把部分完成改写成整体完成。测试只能证明结构化声明行为，不能声称证明没有遗漏原话。

**Acceptance Evidence**

包含 Intent/Operation/Result 关联的脱敏工具结果、验证报告、生成文件独立回读、未覆盖要求示例反馈，以及旧工具消费端兼容测试的 ATR。无自然语言语义证明的限制必须出现在用户结果和报告中。

**Rollback / Stop**

如果确定性 readback 无法表达某种 Expected Effect，阻断该类完成声明并报告能力边界；不得降低 Validator 或把验证责任移交模型。

**Exit Criteria**

Engine 只对结构化操作给出 execution_verified；Agent 分别声明 coverage_declared；未覆盖/不确定/无法结构化项显式反馈；task_completed 不能由工具消息单独产生。

### Phase 4 — Outcome、交付与 Provider 超时恢复

**拟建 CC：** CC-M2-B-05 — Outcome & Recovery

**上游依赖：** CC-M2-B-01、CC-M2-B-03、CC-M2-B-04；B §6；原生工具循环证据。

**Entry Criteria**

- 五类 outcome 条件与业务消息映射已冻结。
- 旧 Tool Schema、内部 error_code、历史 Proposal 和附件消费端的兼容窗口已决定。
- Provider 超时后的产品行为（展示既有工具结果 / 附件，或恢复模型说明）已有负责人决策。
- 涉及外部 Provider 的数据类型已确认符合 SRS OPEN-M2-002 / 003；否则仅使用合成输入。

**In Scope**

- 从现有嵌套状态映射 completed / confirmation_required / clarification_required / blocked / failed。
- outcome、artifact_stage、delivery_state 分别表示操作结果、Preview/Finalize 阶段和聊天附件交付事实。
- 内部错误码留在诊断字段；对用户给出安全、可行动的摘要。
- 工具成功后 Provider 超时保留已提交的工具/文件事实，后续恢复读取 Thread/Session 状态。
- 结合现有 request UUID / operation fingerprint 证明重试不会重复非幂等执行或混淆旧附件。

**Out of Scope**

- 新建全局状态机、事件总线或事件账本。
- 把附件已生成等同已发布/用户已看到。
- 改写原生 llm_assistant 的上游实现；如确认必须修改外部消费链，停止并单独提交影响审查。

**Contract Changes**

优先适配 status、operation_status、artifact_state、delivery_state 和附件元数据。只有现有字段不能无歧义表达冻结的结果时才提出最小字段扩展；不得让原生 Tool message completed 冒充 Office 完成状态。

**Code Impact**

- mymodules/office_engine_m2/models/office_mapping_tools.py：_normalize_office_mapping_result、Preview/Finalize 结果返回及附件 metadata。
- mymodules/office_engine_m2/models/llm_thread.py：_execute_tool_call、Office Tool 输出到原生 Thread Store、非流式 Provider 失败/恢复路径。
- mymodules/office_engine_m2/services/render_bridge.py：稳定 request UUID、Preview artifact 状态及发布结果。
- mymodules/office_engine_m2/tests/test_response_compatibility.py、test_native_chat_integration.py、test_conversational_preview.py、test_chat_entrypoint.py。

**Test Requirements**

五类状态映射、错误码对用户脱敏、Preview 与 Finalize 区分、生成成功但附件 pending 的诚实反馈、Provider 超时后读取已持久化工具结果、同请求重试返回已提交 artifact 而不重复插行/写入、失败恢复仍保留最后有效 Preview、附件消息/Thread 关联与下载字节摘要一致。

**Acceptance Evidence**

对每种状态保留真实工具结构和消费后输出；超时故障注入的可重复日志；重复请求前后 revision、操作数和 artifact 指纹；Odoo 消息附件关联记录。此 CC 的自动化结果不单独证明真实浏览器可见性。

**Rollback / Stop**

消费者无法区分 artifact 与 delivery 时，不得返回 success 或宣称附件已交付；保持旧字段同时阻止新消费者使用。若重试幂等性无法证明，停止自动重放并要求安全恢复，不删除已生成候选。

**Exit Criteria**

服务端结果、Thread 工具结果、Agent 回复及附件实际状态一致；Provider 超时不会把已完成 Office 操作倒写为失败，也不会重复执行。

### Phase 5 — 真实集成验收与证据收口

**拟建 CC：** CC-M2-B-06 — Odoo / Provider / Browser Acceptance

**上游依赖：** CC-M2-B-01 至 CC-M2-B-05 均独立关闭；环境与数据政策门禁满足。

**Entry Criteria**

- 隔离/授权 Odoo 测试数据库、filestore、当前用户权限、模块升级窗口和清理办法已记录。
- 真实 Provider 使用合成或已批准数据；OPEN-M2-002 / 003 未关闭时不得外发业务值。
- Browser E2E 使用独立 Thread 和源文件副本；失败不覆盖唯一有效文件。
- 未解释 Odoo 测试数量差异或历史结果仍 open 时，先记录真实状态并由批准者决定验收门槛，不可当作通过。

**In Scope**

- 当前用户 ORM ACL / Record Rules、Session/Proposal 状态和动态行重编译的 Odoo TransactionCase。
- 当前获准的 gpt-5.6-luna Provider 和原生 llm.thread 连续对话。
- Preview、确认、修改、失败恢复、Finalize、附件卡片展示与实际下载回读。
- 独立 Python 对最终文件做值/公式/结构/非目标区域断言。
- 分开记录 Python、TransactionCase、Provider、Browser/HVR、附件回读证据。
- 原 M2 关键场景的最小回归，不扩大为所有 Office 格式或任意模型。

**Out of Scope**

- 任意 Provider/模型互换已通过证明。
- 全格式能力声明、公式引擎重算声明、公开生产上线和不在 TDD/SRS 的性能 SLO。
- 在共享生产或未经明确授权数据库中进行破坏性故障注入。

**Code Impact**

本阶段按前五个 CC 的既有生产调用链集成：office_engine_m2、office_mapping_verify、office_core、office_document_operations、office_verify 和原生 llm_assistant。任何绕过 office_core / Validator 的执行路径均为验收失败；适用测试文件包括 office_engine_m2/tests/test_native_chat_integration.py、test_response_compatibility.py、test_mapping_session.py 和 office_core / document_operations 回归套件。

**Test Requirements**

完整重跑与本次合同相关的纯 Python 测试和 Odoo TransactionCase；真实 Provider/浏览器至少证明结构化任务连续多轮、确认绑定变化失效、Preview 成功后 Provider 超时恢复、Finalize 后可见附件下载、最终文件回读与确认版本相同。人工验证由人类执行，HVR 留空直到执行，禁止代填 PASS。

**Acceptance Evidence**

每轮 IHR/ATR；真实 provider/tool call 日志脱敏副本；session/proposal/revision/effect 摘要；Preview/Finalize 附件身份和实际下载文件摘要；Python/openpyxl 回读断言；浏览器截图/HVR；环境与权限清理记录。自动化测试不得替代人工验证。

**Rollback / Stop**

Provider、浏览器、DB、附件服务任一外部条件不可用时，将相应项记为 BLOCKED / NOT RUN，保留最后有效 Preview；不伪造 E2E。生产变更在独立审批前不部署；模块升级仅在 CC 明确授权环境内执行。

**Exit Criteria**

逐 CC 的 FR 只基于实际证据；所有预期场景、旧失败、跳过、阻塞及未覆盖范围如实进入 ATR/HVR；项目级 PVR/PCR 分别评审后才能做最终项目结论。本计划本身不能宣布阶段完成。

## 5. 阶段顺序、依赖与接口稳定性

依赖顺序：

Phase 0 / CC-M2-B-01 → Phase 1 / CC-M2-B-02 → Phase 2 / CC-M2-B-03 → Phase 3 / CC-M2-B-04 → Phase 4 / CC-M2-B-05 → Phase 5 / CC-M2-B-06

关键接口先后：
- 表达式 Schema、值类型、null 语义和规范化指纹先在 CC-M2-B-02 稳定；后续 Proposal、Expected Effect 与确认签名只引用该规范化表示。
- 规则 ID、Patch 操作和确认 Effect 绑定在 CC-M2-B-03 稳定；CC-M2-B-04 复用 operation/effect ID，不另造另一套规则身份。
- 文件读取验证复用 office_core 候选结果和现有 office_verify；CC-M2-B-04 不新增第二个权威 Validator。
- outcome 投影在 CC-M2-B-05 基于 execution_verified、artifact_stage、delivery_state；CC-M2-B-06 只验收实际消费。
- 超时恢复字段/幂等标识在 CC-M2-B-01 先审计。只有发现现有 revision / request UUID / attachment 关联无法表达恢复时，CC-M2-B-05 才提案最小扩展。
- 旧 Proposal、Session 与确认数据兼容由 CC-M2-B-02 / B-03 先定义迁移行为；CC-M2-B-06 验证升级前后读取。

并行工作：本计划不安排实现并行；各 CC 共享表达式/Session/结果接口，必须串行冻结。独立审阅文档或准备中性测试夹具可并行，但不创建代码变更或下游 CC。

## 6. 里程碑

| 里程碑 | 阶段 / 交付 | 退出条件与证据 | 目标 / 状态 |
|---|---|---|---|
| M0 — 基线有效 | Phase 0 / CC-M2-B-01 | TDD 对齐、Runtime 结论、测试选择器和 open items 有记录 | 日期 TBD / 未开始 |
| M1 — 值表达可验证 | Phase 1 / CC-M2-B-02 | 类型与逐目标求值、文件回读、旧 Proposal 兼容证据 | 日期 TBD / 未开始 |
| M2 — 多轮状态安全 | Phase 2 / CC-M2-B-03 | dormant/restore、确认 Effect 变化失效、旧 Preview 保护证据 | 日期 TBD / 未开始 |
| M3 — 意图与结果可审计 | Phase 3 / CC-M2-B-04 | 三层结果和 Expected Effect/readback 对应证据 | 日期 TBD / 未开始 |
| M4 — 用户结果可恢复 | Phase 4 / CC-M2-B-05 | outcome、Provider timeout、idempotent recovery 证据 | 日期 TBD / 未开始 |
| M5 — 实际闭环 | Phase 5 / CC-M2-B-06 | Odoo + Provider + Browser + 下载回读及人工 HVR | 日期 TBD / 未开始 |

无估算依据，不填日期或时长。里程碑通过不替代需求与 TDD 追溯核验。

## 7. 验收与验证矩阵

| 需求 / 设计义务 | 阶段 | 验收标准 | 验证方式与证据 | 拟建 CC / FR | 当前状态 |
|---|---|---|---|---|---|
| SRS FR-M2-006 / TDD 原生 Tool → M1 Preview | 0、5 | 失败和已验证结果准确区分，只有当前校验通过候选可发布 | Odoo + core tests、artifact SHA、Thread 记录 | B-01 / B-06 | Planned |
| SRS FR-M2-007 / Phase B §5 | 2 | 增量 Patch 保留未改规则；目标出范围不执行且不自动激活；整份确认 Proposal 恢复 | Session/Proposal 测试、真实 XLSX 回读、revision 证据 | B-03 | Planned |
| SRS FR-M2-008 / B §5.4–5.5 | 2、5 | 确认绑定数据求值基线和最终 Effect；变更后旧确认失效 | Odoo TransactionCase、confirmation digest 对比、无写入断言 | B-03 / B-06 | Planned |
| Phase B §3 Expression Contract | 1 | literal/field/composition/date/Decimal/False/zero/null 按冻结规则逐目标求值 | 中性 pytest + 保存后独立 XLSX 回读 | B-02 | Planned |
| Phase B §4 Intent / Operation / Result | 3 | execution_verified 与 coverage_declared 分离；无法结构化/未覆盖请求明确反馈，不形成 task_completed | Tool contract tests、readback mismatch cases、Agent response evidence | B-04 | Planned |
| Phase B §6 User-facing Outcomes | 4 | 五类 outcome、artifact_stage、delivery_state 不混淆；内部错误不裸露；Provider 超时可恢复 | result mapping tests、故障注入、真实 Thread/provider trace | B-05 | Planned |
| Phase B §7 完整数据流 | 1–5 | 全生产写入继续使用统一 operation list、office_core、Validator 和 M2 Session 生命周期 | 静态调用链检查 + 行为测试 + Odoo/Browser evidence | B-02–B-06 | Planned |
| Phase B §10 环境与历史异常 | 0、5 | 不以当前进程路径推断内存模块身份；Thread 12063 保持 evidence-driven | 只读 module identity probe、历史记录与当前路径对照 | B-01 / B-06 | Planned |
| TDD V1.1 / Phase C core integration | 1–5 | operation schema、候选验证、附件门禁不绕行、不削弱资源/安全校验 | office_core / operations / office_verify regression suites | B-02–B-06 | Planned |
| TV-M2-001 / TV-M2-004 历史结果 | 0、5 | 原 FAIL / INCONCLUSIVE 保持原状态；逐项标记本计划回归/非适用/需授权处置 | 原 TV 证据、复测命令和 ATR 对照；不改原报告 | B-01 / B-06 | OPEN |
| OPEN-M2-002 / 003 数据政策 | 5 | 未关闭前仅合成 Provider 输入；批准后才按审批范围真实数据 | Provider payload 审计与授权记录 | B-06 | OPEN / 阻止真实业务数据外发 |
| Odoo 测试统计差异 166+26 vs 160 | 0 | 取得能解释统计口径的日志或明确记录仍 OPEN，不猜原因 | Odoo runner 日志、测试发现摘要、ATR | B-01 | OPEN |

## 8. 质量与验证策略

| 验证领域 | 适用范围 | 证据门禁 |
|---|---|---|
| 自动化 / pure Python | B-02 至 B-05 的中性契约 | 计划在各 CC 评审时冻结精确命令；候选命令为 PYTHONPATH=mymodules venv/bin/python -m pytest -q，并显式列出纯 Python 包测试目录；分离 Odoo TransactionCase |
| Odoo ORM / ACL | B-03、B-06 | Odoo 18 TransactionCase；测试用户与实际 Record Rules；测试前后业务记录不变；不得 sudo 或 SQL |
| Document Core / Validator | B-02 至 B-06 | 统一执行入口、完整操作列表 preflight、回读失败阻止附件发布、文件/结构/非目标区域断言 |
| Browser / Provider / Human | B-05、B-06 | 独立 Thread、当前获准模型、Provider 原始工具参数与响应、截图、附件实际下载；HVR 由人工填写 |
| 文件回读 | B-02、B-03、B-04、B-06 | openpyxl/格式 Adapter 独立读取，文件非空、XLSX ZIP 完整；公式文本与公式引擎计算结果严格分开 |
| 权限与安全 | 全部 CC | ACL、Record Rules、字段访问、确认范围、路径、资源限制、worker 隔离、错误脱敏均有正反例 |
| 升级 / 迁移 / 回退 | B-03、B-06 | 仅在获批隔离数据库执行；验证历史 Proposal 可读，新字段缺省迁移；保留最后有效 Preview；记录升级与恢复日志 |
| 性能 / 容量 | B-02、B-05 | 不设未获批 SLO；B §13 资源限值通过中性压力测试给出证据后再冻结 |
| 项目级回归 | B-06 | 分别报告 pytest、Odoo TransactionCase、真实 Provider、Browser/HVR、下载文件回读；不得合并成一个“测试通过”声明 |

候选命令仅用于计划阶段说明验证类别，不代表已执行或已验证可运行。现有记录中的 Odoo 命令与统计差异须由 CC-M2-B-01 核实后，才作为后续 CC 的冻结命令。

## 9. 风险与应变

| 风险 | 概率 / 影响 | 缓解 / 检测 | 回退 / 决策责任人 | 状态 |
|---|---|---|---|---|
| Frozen Phase B 与正式 TDD 条款不一致 | 中 / 高 | CC-B-01 建立逐条矩阵；必要时按 TDD 变更流程修订并反向冻结 | 停止受影响 CC；技术设计负责人 | OPEN |
| 旧 Proposal 无法按新表达 Schema 安全读取 | 中 / 高 | 中性旧样本和当前历史 Proposal 读取回归；迁移前备份/指纹 | 关闭新写入，仅保留安全读取；技术负责人 | OPEN |
| False/0/null 序列化被混淆 | 中 / 高 | 类型化求值 + 保存后真实文件回读 | 阻断相关表达式；不得输出候选成功 | OPEN |
| confirmation 只绑定表达式而非最终值/目标/原值 | 中 / Critical | 变更数据、目标、Effect、原值的故障测试 | 旧确认一律失效；不得强制执行 | OPEN |
| Coverage 清单漏掉原话的一项需求 | 中 / 高 | 明示其非独立证明；未结构化项显式报告；HVR人工检查 | 不作 task_completed 全部完成声明 | OPEN |
| Provider 工具成功后超时，重试重复执行 | 中 / High | 故障注入 + request fingerprint/附件版本验证 | 禁止自动重放，恢复已提交结果 | OPEN |
| SRS 数据使用政策未关闭 | 已知 / 高 | 真实 Provider 仅合成数据，直到批准业务数据范围 | 阻断业务数据外发 | OPEN |
| Runtime 或数据库测试基线不安全 | 中 / Critical | 进程模块身份、DB/filestore隔离、清理与 ACL 预检 | 不重启/不升级/不写共享数据 | OPEN |
| 统计总数无法调和、旧 skipped / fail 被漏报 | 已知 / 中 | 在 ATR 中分别记录测试发现和 runner 汇总；保持原状态 | 验收阻断或按有效授权处置 | OPEN |
| 上游模块依赖需改 llm_assistant 或官方模块 | 低 / High | 优先 M2 适配；若必要，另行审批并评估上游基线 | 不扩展当前 CC 范围 | OPEN |

## 10. 资源与环境

| 资源 / 环境 | 要求 | 负责人 | 可用性 / 状态 |
|---|---|---|---|
| Workspace | 基于 CC 开始时 clean/记录的 HEAD 与完整 status；本计划起草基线 main@3ccb863… | 实施负责人 | 当前存在既存未跟踪文件；未来 CC 重新快照 |
| Odoo Runtime | Odoo 18 CE、项目 Python venv、odoo.conf、addon paths；记录实际 import path/hash | 环境负责人 | 8091当前模块身份 UNVERIFIED |
| Odoo Test DB / filestore | 隔离副本优先；共享 odoo18ce 只有逐 CC 取得明确授权并证明回滚 | DB / 环境负责人 | 未确认 |
| Provider | 当前正式基线 OpenAI gpt-5.6-luna；输入使用合成/获批数据 | Provider 管理员 / 隐私负责人 | 凭据和额度未验证 |
| Browser | 可打开真实 llm.thread，查看并下载私有附件 | QA | 需在 CC-B-06 预检 |
| 中性 Office fixtures | 不含业务特例的 XLSX，类型/格式/结构声明固定 | QA / 技术负责人 | CC-B-02 前准备 |
| 日志与产物 | 脱敏工具日志、运行日志、下载 XLSX、hash、截图、ATR/HVR | QA / 实施负责人 | 未来按每 CC 新建证据目录 |
| 私有附件 / 业务数据 | 附件权限继承当前用户与 Thread；不以测试为由扩大可见性 | Odoo 安全负责人 | 现有 ACL 保持 |

## 11. 变更控制

- SRS、TDD、Phase B 冻结语义变化：返回权威文档维护者；审批并更新受影响基线、追溯矩阵和 CC 映射后，方可继续受影响阶段。
- 若实施发现与冻结 Phase B 或现有 TDD 冲突，停止受影响 CC；不得通过计划或代码自行调和。
- Implementation Plan 本轮为 DRAFT；任何 CC、IHR/ATR/HVR 或实现都不得引用其作为冻结基线。
- 计划阶段顺序、CC 范围或证据门禁变更时，记录原因、受影响阶段与审批状态；不为方便测试降低验收标准。
- 每个 CC 单独批准和冻结；本计划不自动授权创建 CC、编码、数据库测试、模块升级或服务重启。
- 保留所有历史失败、测试跳过和未验证事实；状态更新只通过追加证据，不覆盖历史。

## 12. 交付物与移交

| 交付物 | 阶段 | 验收证据 | 位置 / 状态 |
|---|---|---|---|
| Runtime / test baseline report | Phase 0 | 运行身份、测试选择器、历史问题对照 | CC-M2-B-01 / 未创建 |
| Typed Expression Contract 与中性测试 | Phase 1 | Schema、兼容、类型和文件回读 ATR | CC-M2-B-02 / 未创建 |
| Proposal continuity / confirmation implementation | Phase 2 | revisions、Effect binding、恢复和确认回归 | CC-M2-B-03 / 未创建 |
| Coverage / Expected Effect result contract | Phase 3 | execution_verified、coverage_declared、task_completed 三层证据 | CC-M2-B-04 / 未创建 |
| Outcome / timeout recovery | Phase 4 | 五类结果、delivery 独立性、幂等重试证据 | CC-M2-B-05 / 未创建 |
| Odoo/Provider/Browser final acceptance | Phase 5 | ATR、HVR、下载回读与 FR/PVR 证据 | CC-M2-B-06 / 未创建 |
| Phase B 技术设计基线 | Phase 0 | 用户批准冻结记录 | docs/B技术设计草案.md / FROZEN v0.3 |
| 原始 M2 实施计划 | 不属于本计划交付 | 仅作既有范围参考 | docs/implementation/IMPLEMENTATION_PLAN_office_engine_m2.md / FROZEN V1.0.0，不修改 |

## 13. 开放决策与跟进

| ID | 问题 / 待办 | 阻塞阶段 | 责任方 | 状态 |
|---|---|---|---|---|
| OIP-B-001 | Phase B §13.1：concat / coalesce 的严格类型及 null_policy 默认组合是否按草案冻结 | Phase 1 | 产品 / 技术负责人 | OPEN |
| OIP-B-002 | Phase B §13.2–3：Decimal、除法精度/舍入、Boolean 数值拒绝、null_result 默认值及 clear/remove 序列化 | Phase 1 | 产品 / 技术负责人 | OPEN |
| OIP-B-003 | 表达式深度/节点/concat 上限；依 B 要求先以中性压力与边界测试确定，不预设 8/64/32 为通过门槛 | Phase 1 | 技术负责人 / QA | OPEN |
| OIP-B-004 | Phase B §13.5：outcome → 现有 status/operation/artifact/delivery 字段适配及旧 Tool Schema / Proposal 兼容窗口 | Phase 4 | 技术负责人 / API 消费方 | OPEN |
| OIP-B-005 | Phase B §13.6：Provider 超时后的用户体验和恢复提示方式 | Phase 4–5 | 产品负责人 | OPEN |
| OIP-B-006 | Phase B §13.7：真实浏览器、Provider、测试 DB 和独立验收 Thread 的可用环境 | Phase 0、5 | 环境负责人 / QA | OPEN |
| OIP-B-007 | TDD V1.1.0 / 动态行补充与 Phase B v0.3 的正式基线映射；是否需另发 TDD 修订 | Phase 0 | 技术负责人 | IMPACT REVIEW REQUIRED |
| OIP-B-008 | SRS OPEN-M2-002 / 003 的业务字段与 Provider 数据使用/留存批准 | 使用真实业务字段的 Phase 5 | 数据 / 隐私负责人 | OPEN；合成数据不受阻 |
| OIP-B-009 | 既有 Odoo 报告统计 166 + 26 与最终 160 的差异及所有历史 FAIL / INCONCLUSIVE 的本计划处置 | Phase 0、5 | QA / 技术负责人 | OPEN；不得推测 |
| OIP-B-010 | 文件名旧 Frozen Plan V1.0 与本后续范围计划的关系确认；必要时按治理规则登记后续计划为独立 scope 或正式 amendment | Plan review / Phase 0 | 审批者 / 文档负责人 | OPEN |

## 14. 追溯

### 14.1 Authority to Plan

| SRS / TDD / Phase B 约束 | 阶段 | 计划验收 / 证据 |
|---|---|---|
| SRS FR-M2-006：校验后生成真实 Preview；失败不得交付不合格候选 | 0、3、5 | M2 → office_core → Validator → attachment 链，回读与交付状态分别证明 |
| SRS V1.1 FR-M2-007：多轮自然语言修改、完整有效 Proposal 保留和版本化 Preview | 2、5 | 多轮 revision 与内容回读，未改规则保持 |
| SRS V1.1 FR-M2-008：确认绑定当前 Session/Proposal/Preview，数据变化需刷新确认 | 2、5 | 确认失效/重预览/再确认测试及真实 Thread 证据 |
| TDD V1.1 §§2–5：Session、完整 Proposal、M1 Preview/Finalize、附件与并发 | 0–5 | 使用现有状态和服务；新增字段须由 CC 证明必要 |
| TDD V1.1 §9–10 / Phase C 记录：office_core 候选执行、Validator 回读、M2 生产调用路径 | 1–5 | 操作只经过统一生产链，失败验证禁止附件发布 |
| Phase B v0.3 §3：有限类型表达和逐目标求值 | 1 | 中性类型契约 + 保存后 XLSX 回读 |
| Phase B v0.3 §4：三层结果与未覆盖要求必须显式反馈 | 3–4 | execution_verified / coverage_declared / task_completed 证据及明确限制 |
| Phase B v0.3 §5：Proposal Patch、dormant、整份 Restore、Effect 绑定确认 | 2 | 状态/确认回归和真实文件变化测试 |
| Phase B v0.3 §6–7：五类 outcome 与附件/Thread/Provider 结果连续性 | 4–5 | Provider 超时、附件 pending、Finalize 和 Browser 下载证据 |
| Phase B v0.3 §10 / Phase A2 未验证项 | 0、5 | 环境核验、历史确认与 Provider 超时恢复证据；缺失项仍标 UNVERIFIED |

### 14.2 Plan to Coding Closure

| 计划阶段 / 交付物 | 拟建 CC | IHR / ATR / HVR | FR | PVR 证据 |
|---|---|---|---|---|
| Phase 0 Runtime & Baseline | CC-M2-B-01 | IHR/ATR；不适用人工 UI 时记录 N/A 理由 | FR-M2-B-01 | 基线身份、测试选择器、Open items |
| Phase 1 Typed Expression | CC-M2-B-02 | IHR/ATR；需要人工确认交互才建 HVR | FR-M2-B-02 | 中性表达式/文件回读与兼容矩阵 |
| Phase 2 Proposal/Confirmation | CC-M2-B-03 | IHR/ATR/HVR（人工确认流程适用时） | FR-M2-B-03 | 多轮和确认范围证据 |
| Phase 3 Intent / Effect verification | CC-M2-B-04 | IHR/ATR/HVR | FR-M2-B-04 | Operation/Effect/readback/coverage evidence |
| Phase 4 Outcome / Recovery | CC-M2-B-05 | IHR/ATR/HVR | FR-M2-B-05 | Provider 超时、附件发布和幂等恢复 |
| Phase 5 Integration acceptance | CC-M2-B-06 | IHR/ATR/HVR | FR-M2-B-06 | Odoo、Provider、Browser、最终下载回读、PVR |

当前所有 CC 均为拟建项。各 CC 的文件路径、测试状态和证据状态须在其单独获批的 Coding Contract 中冻结。Workflow Evidence Status 必须分别填写 Passed / Failed / Skipped / Blocked / Missing；不允许空白或用总体 PARTIAL 隐藏未通过项。计划通过不等于需求验证通过。

## 15. 变更历史

| 版本 | 日期 | 状态 | 变更与原因 | 影响范围 / 基线 |
|---|---|---|---|---|
| v0.1 | 2026-11-06 | DRAFT — NOT AUTHORIZED | 首次依据冻结 Phase B v0.3 和当前 M2 代码起草后续表达式、状态连续性和结果契约计划；未创建 CC | SRS V1.0.0/V1.1.0、TDD V1.1.0、Phase B v0.3；基线有效性 IMPACT REVIEW REQUIRED |

---

## 当前实施准备度

**结论：DRAFT — NOT AUTHORIZED；首个 CC Gate 当前 BLOCKED。**

已完成上游 Phase B v0.3 冻结记录和计划草案。尚需完成：计划评审批准；B v0.3 与正式 TDD 的基线对齐；B §13 开放决策的逐阶段处置；Runtime 身份证据；测试命令和既有测试失败/跳过核对；166 + 26 与 160 的统计差异核对；测试环境与 Provider 数据政策。以上事项未解决前，不得起草 CC、编码、执行测试或部署。
