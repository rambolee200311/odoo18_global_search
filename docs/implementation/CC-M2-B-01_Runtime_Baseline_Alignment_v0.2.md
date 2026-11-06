<!--
Source template: docs/skill/odoo-project-workflow/references/templates/Coding/Coding_Contract模板.md
Source version/status: v1.0.0; Frozen
Template synchronization check: PASS, 2026-11-06
Contract status: FROZEN — G2 AUTHORIZED FOR WORKSPACE-ONLY READ-ONLY AUDIT
-->

# CC-M2-B-01 — Runtime & Baseline Alignment (v0.2 Frozen)

## 文档信息

| 项目 | 内容 |
|---|---|
| Intent ID | M2-B-01-RUNTIME-BASELINE |
| 模块 | Odoo 18 CE / `office_engine_m2`（仅审计目标；不实施代码） |
| 工作类型 | 只读技术审计 / 基线核查，文档证据交付 |
| 变更类型 | 只读证据收集 |
| 状态 | **FROZEN — G2 WORKSPACE-ONLY READ-ONLY AUDIT AUTHORIZED** |
| 目标 | 在不改变工作区、服务、数据库或测试状态的前提下，形成当前运行身份、历史异常、测试基线及 Phase B/TDD 对齐的可审计证据。 |
| 背景 | 已冻结的后续范围计划要求 CC-01 先完成只读核查；Phase A/A2 留有 Runtime 模块身份、Thread 12063 与 Odoo 测试统计等未验证事项。 |
| 实施计划基线 | `docs/implementation/IMPLEMENTATION_PLAN_office_engine_m2_state-continuity_v0.2.md` — FROZEN（G1 已批准）；`Baseline validity: IMPACT REVIEW REQUIRED` |
| 单独执行门禁 | G2 — **已批准，仅限 §3.1 工作区来源与 §4.1 IHR/ATR 输出**；无外部进程、服务或日志路径授权。 |
| 版本 / 日期 | v0.2 / 2026-11-06 |

> 本文件为冻结的 CC-01 执行契约。G2 仅授权 §3.1 的工作区只读审计和 §4.1 的 IHR/ATR 文档交付；未授权任何工作区外路径、进程/服务检查、运行日志读取、数据库访问、测试执行、服务操作或代码实施。

---

## 0. 文档治理与编号

本 CC 遵循组织级 Coding Contract 模板 v1.0.0。CC 自有编号仅使用 `CC-CHANGE`、`CC-PRESERVE`、`CC-TEST`、`CC-DEC` 前缀；本 CC 已冻结，仅授权只读审计，不包含实现级决策。

本轮为只读审计，不改变 SRS、DDD、TDD、Phase B 语义，也不产生产品行为。审计输出只记录现状、证据及未验证项，不代替后续实现 CC 或用户决策。

## 1. 上游基线与追溯

### 1.1 SRS 引用

| SRS ID | 标题 / 版本 | 与本 CC 的相关性 |
|---|---|---|
| FR-M2-006、FR-M2-007、FR-M2-008 | 自然语言映射、用户修改及确认 / SRS M2 V1.1.0 | 只作为审计现行行为的业务基线；本 CC 不修改需求行为 |
| FR-M2-013、NFR-M2-006、NFR-M2-008 | Provider 失败、数据最小化、结果可理解 / SRS M2 V1.0.0（由 V1.1.0 变更范围规则适用） | 检查现有证据与数据外发/用户结果边界；不进行 Provider 请求 |

### 1.2 DDD 引用

N/A。冻结的 M2 TDD V1.0.0/V1.1.0 已记录本项目 DDD 不适用的决定；本 CC 不创建领域模型或 DDD 占位项。

### 1.3 TDD 与设计基线

| 基线 | 条款 | 与本 CC 的相关性 |
|---|---|---|
| `docs/design/TDD_office_engine_m2.md` V1.0.0 FROZEN | Session / M2 职责和安全边界 | 只读对照，不变更 |
| `docs/design/TDD_office_engine_m2_v1.1.0.md` V1.1.0 FROZEN | §§1–5、§§9–10：原生聊天、Session/Proposal、Preview/Finalize、附件及 Phase C 生产链 | 与审计调用链及状态证据逐项对照 |
| `docs/design/TDD_office_engine_m2_dynamic_rows_addendum_v1.1.0.md` V1.1.0 FROZEN | §§1–5：有限重复行、授权列表与失败行为 | 对照动态目标和当前范围，不执行写入 |
| `docs/B技术设计草案.md` Phase B v0.3 FROZEN | §§3–7、§10、§14 | 当前冻结的补充契约；审计其与 TDD 的对应/差异，不重开已冻结语义 |
| `docs/implementation/IMPLEMENTATION_PLAN_office_engine_m2_state-continuity_v0.2.md` FROZEN | §4 Phase 0 / CC-M2-B-01；§§5、7、13 | 本 CC 的范围、证据门禁和停止条件 |

当前冻结 M2 TDD 文件未定义可直接裁剪到本 CC 的命名 `T-xxx` 防护栏清单。本 CC 不虚构 TDD 编号；按上表准确章节、项目架构边界 `docs/AGENTS.md` 和相关 SRS NFR 进行只读核查。若评审发现应存在而缺少的 TDD 技术约束，记录为基线差异，不在本 CC 补写。

### 1.4 问题证据（非权威需求）

- `docs/A审计报告.md`、`docs/A2审计报告.md`：Phase A/A2 只读审计及其 `UNVERIFIED` 项。
- `docs/verification/TV_office_engine_m2_report.md`：保留原有 `PARTIAL`、`FAIL`、`INCONCLUSIVE`、`UNVERIFIED` 状态。
- Thread 12063 既有对话摘录：确认后再次失败的观察事实；摘录不能替代原始工具参数或 pending payload。

这些材料只用于定位证据问题，不得被解释为新增业务语义、历史根因证明或自动放行依据。

## 2. 目标与范围边界

### 2.1 范围内

仅执行本次 G2 已批准范围内的只读核查：

1. 固定审计起始的 Git HEAD 与工作区状态；审计结束再次记录，确认除获准的审计报告文档外没有工作区变化。
2. 按 §3.3 的三级证据分别核查 Workspace、Process 与 Loaded Module 身份。只有直接可信的已加载模块证据可以支持 Loaded Module `MATCH` 或 `MISMATCH`；若当前只读授权范围内无法取得该证据，记录 `UNVERIFIED`，不得扩大访问权限，也不得用路径或进程旁证推断内存代码身份。
3. Thread 12063 仅检查 G2 明确批准的既存日志、导出材料和文档；不得连接数据库、ORM、SQL/cursor、Odoo shell，不得读取 Thread/Session 持久化记录。原始 pending payload 或关联证据缺失时，记录缺项并将历史根因标记 `UNVERIFIED`；同时在 IHR 提出一个由后续 CC-03 基于当前代码执行的验证案例，不将其描述为历史复现。
4. 只读追踪当前工作树的确认生成、持久化、匹配/失效、执行前重验调用链，检查相关测试源码及既有日志；不运行测试。提出供 CC-03 使用的当前代码行为验证案例，不代替 CC-03 执行。
5. 对 Phase B v0.3 冻结条款与正式 TDD V1.1.0 / 动态行补充逐项制作映射，并在 IHR 提供 §5.1 所列差异处置矩阵。`GAP` 本身不自动意味着必须修订 TDD；按证据区分实现差距、测试/追溯缺口、未验证项或真正的冻结语义冲突。冻结语义不得由本 CC 改写。
6. 只读核对测试入口、测试选择器、已有日志中的发现数和最终汇总数；特别核查历史的 `166 + 26` 与 `160` 差异。无法解释时保留 `OPEN`，不猜测、不改测试标准。
7. 逐项登记 TV 报告中的历史失败、跳过、阻塞和缺证据项；不得修改原始 TV/IHR/ATR/HVR。
8. 生成一份 CC-01 只读审计 IHR，给出证据路径/时间/摘要、结论状态、owner、后续门禁和未验证原因。

### 2.2 明确超出范围

- 任何 Python/XML/JS/SCSS/配置/测试代码、SRS/DDD/TDD/Phase B 或计划之外文档的修改；仅可创建 §4.1 明确列出的 CC-01 IHR 与 ATR。
- 任何数据库、ORM、SQL、cursor、业务数据、附件、Session、Thread、Proposal 或库存记录读取/写入；不连接 `odoo18ce`，不读取历史 Thread 的数据库持久化记录。
- 运行任何自动化/手工功能测试、测试服务器、Odoo shell、Provider 请求或 Browser 操作。
- 启动、停止、重启、升级、部署、reload、注入或附加调试器到 8091/Odoo 进程；触发任何 HTTP/RPC 请求。
- 暂存、提交、推送、重置、清理、恢复或改写 Git 工作区；不得删除或覆盖用户的未提交文件。
- 替历史 Thread 12063 确认根因；无法取回的原始 pending payload 一律保留 `UNVERIFIED`。
- 决定 Phase B §13 真正未决产品/API 事项、重新选择冻结表达式语义、修改业务规则，或代替审批人批准 TDD 变更。
- 以 CC-01 结果授权 CC-02 至 CC-05 编码、G4 Runtime Validation 或 G5 Production Release。

### 2.3 非目标

CC-01 不是修复任务、实现阶段、数据库审计任务或端到端验收。它不证明工具链当前功能通过，也不保证历史事件能被完整复原。

## 3. 只读操作约束与证据方案

### 3.1 G2 授权所需的精确来源清单

本次 G2 对非工作区来源的授权清单为：**NONE**。因此不得读取 OS 进程元数据、8091 服务日志或其他工作区外证据；Process 与 Loaded Module 身份按本 CC 规则记录为 `UNVERIFIED`，不以此扩大授权。

本次 G2 批准的工作区只读来源限于：`docs/A审计报告.md`、`docs/A2审计报告.md`、`docs/B技术设计草案.md`、`docs/requirement/SRS_office_engine_m2_ai_mapping_v1.1.0.md`、`docs/design/TDD_office_engine_m2_v1.1.0.md`、`docs/design/TDD_office_engine_m2_dynamic_rows_addendum_v1.1.0.md`、`docs/verification/TV_office_engine_m2_report.md`、冻结实施计划 v0.2、本 CC v0.1/v0.2、`docs/implementation/` 下与 M2 直接相关的既有 IHR/ATR/HVR，以及代码/测试目录 `mymodules/office_core/**`、`mymodules/office_engine_m2/**`、`mymodules/odoo-llm/llm_assistant/models/**`、`mymodules/odoo-llm/llm_assistant/tests/**`。Git 只读元数据限于 HEAD、branch、status 和上述来源文件的历史/差异。不得读取未列明路径。

### 3.2 脱敏与保存

- 只记录能回答审计问题的最小元数据；不复制业务内容、个人数据、Provider payload 正文、令牌、密钥、完整环境变量或附件字节。
- 进程环境如必须确认配置项是否存在，只记录变量名和“存在/不存在”，对值完全省略；任何 token/secret 立即排除，不写入 IHR。
- 日志引用用受控路径、时间/行号或不可逆摘要定位；如包含敏感内容，只记录错误类别和必要上下文，不复制原文。
- IHR/ATR 仅写入 G2 批准的上述文档路径。不得把证据上传 Provider、Thread、Issue 或外部存储。

### 3.3 Runtime 身份三级证据与状态判定

| 证据层 | 可记录事实 | 能支持的结论 | 明确不能据此推出 |
|---|---|---|---|
| Workspace | 工作区路径、Git HEAD、工作树状态及当前磁盘源码指纹（仅在授权范围内） | 当前工作区的源码基线 | 8091 进程实际使用该工作区或已加载相同代码 |
| Process | 可见 PID、可执行文件、命令行、工作目录、配置/addons 路径等经批准可见元数据 | 被检查进程及其启动上下文 | 进程内存中的 Python 模块内容与当前磁盘源码相同 |
| Loaded Module | 来自直接、可信且经 G2 批准的现存运行诊断证据，能识别进程中实际加载模块及对应代码身份/指纹 | 在证据覆盖范围内判定 Loaded Module `MATCH` 或 `MISMATCH` | 超出该证据覆盖范围的模块、未采样 worker 或其他运行实例状态 |

只有第三层的直接可信证据可以证明 Loaded Module `MATCH`。Workspace/Process 的路径相同、进程启动时间、日志时间、Registry reload、模块版本号或可见源码路径均不能单独或组合推断内存代码一致。若要取得 Loaded Module 证据必须注入、附加调试器、发起未授权请求、扩大路径/权限，或当前 G2 没有批准可用来源，则停止该取证路径并记为 `UNVERIFIED`；不得为补证扩大授权。

IHR 应分别记录三层的证据来源、覆盖范围和状态。每层使用 `MATCH / MISMATCH / UNVERIFIED`；历史事件证据项记录 `AVAILABLE / UNAVAILABLE / UNVERIFIED`；基线条款记录 `MATCH / GAP / CONFLICT / UNVERIFIED`；测试历史按原始 `PASS / FAIL / SKIPPED / BLOCKED / NOT RUN` 保持。不能将源代码推断、测试源码或模型叙述写成运行时事实。

## 4. 变更边界

### 4.1 允许

| 类型 | 详情 |
|---|---|
| 本次评审稿 | `docs/implementation/CC-M2-B-01_Runtime_Baseline_Alignment_v0.2.md`（保留 v0.1 历史草稿） |
| 审计产物 | `docs/implementation/IHR-M2-B-01_Runtime_Baseline_Alignment.md` 与 `docs/implementation/ATR-M2-B-01_Runtime_Baseline_Alignment.md`；G2 已明确授权创建。ATR 只记录审计可见的测试资产/历史结果及本次 NOT RUN，不执行测试。 |
| 只读输入 | §3.1 所列工作区文件与 G2 明确列出的进程/日志来源 |

### 4.2 禁止

| 类型 | 详情 |
|---|---|
| 生产实现 | 所有 addon、模块、Python、XML、JS、CSS、配置、资产与迁移脚本 |
| 测试与执行 | 测试源码、测试数据库、测试运行、Odoo shell、Provider、HTTP/RPC、Browser 操作 |
| 数据 / 外部状态 | 数据库及业务记录、附件、Thread、Session、Proposal、文件内容、模块状态和服务状态 |
| 版本控制 | `git add`、commit、push、reset、clean、stash、checkout/restore 或任何覆盖式操作 |
| 文档 | 除本 CC 与上述 IHR、ATR 外的全部文档与证据文件 |

## 5. 必需的审计交付（非生产行为变更）

| ID | 当前已知状态 | 期望审计结果 | Contract Item |
|---|---|---|---|
| 1 | Phase A/A2 未能证明进程内 Python 模块身份 | 分别报告 Workspace、Process、Loaded Module；仅直接可信的 Loaded Module 证据支持其 MATCH/MISMATCH，否则 UNVERIFIED，不扩大取证权限 | CC-CHANGE-001 |
| 2 | Thread 12063 有“确认后失败”的对话摘录，原始 pending payload 可能不可恢复 | 仅核对 G2 批准的既存日志、导出和文档；不访问数据库/ORM/Thread 持久化记录；缺证时历史根因 UNVERIFIED，并提出 CC-03 当前代码验证案例 | CC-CHANGE-001 |
| 3 | 既有 Odoo 记录中的计数 166 + 26 与最终 160 未解释 | 找到并引用能够调和统计口径的原始证据；否则登记 OPEN 和责任方 | CC-CHANGE-001 |
| 4 | Phase B v0.3 已冻结，但与 TDD 对齐尚未完成 | 产生逐条映射和 GAP/CONFLICT 项；冻结语义保持不变，设计缺口转上游变更流程 | CC-CHANGE-001 |
| 5 | TV 历史报告包含 FAIL/INCONCLUSIVE/UNVERIFIED | 保留原状态并说明受影响的后续阶段；不得重写或豁免 | CC-CHANGE-001 |

### 5.1 IHR：Phase B / TDD 差异处置矩阵

IHR 必须提供逐条矩阵，至少包含以下列；条款对应应精确到文档章节/契约项，结论只依赖已记录证据：

| Phase B 冻结条款 | 对应 TDD / 动态行条款 | 状态（MATCH/GAP/CONFLICT/UNVERIFIED） | 实际差异与证据 | 受影响 CC | 建议处置 | 责任人/角色 | 阻塞范围 |
|---|---|---|---|---|---|---|---|

处置判据：`MATCH` 记录映射即可；`UNVERIFIED` 列明缺失证据，不下语义结论；`GAP` 需说明是实现、测试/追溯或规范覆盖差异，并由责任人判断现有冻结语义是否足以指导对应 CC；不得自动要求 TDD 修订，也不得自动视为无影响。只有证据显示冻结规范之间存在真实 `CONFLICT`，或冻结设计无法满足既定要求时，才提交相应设计变更审批。矩阵必须指出具体受影响 CC 与阻塞范围，不得以“存在 GAP”笼统阻塞所有后续 CC，也不得由 CC-01 自行批准放行。

上述 `CC-CHANGE-001` 是只读审计交付项，不改变任何业务行为或生产代码。

## 6. 既有行为与证据保留

| ID | 保留项 | 为什么不得改变 | Contract Item |
|---|---|---|---|
| 1 | 当前 Git HEAD、所有未提交/未跟踪文件与用户数据 | 工作区保护要求 | CC-PRESERVE-001 |
| 2 | 8091 服务、数据库、附件及 Session/Proposal/Thread 状态 | 本 CC 是只读，不授权变更运行状态 | CC-PRESERVE-002 |
| 3 | A/A2、TV、IHR/ATR/HVR 的原始失败和不确定结论 | 新证据只能追加，不能覆盖历史事实 | CC-PRESERVE-003 |
| 4 | SRS、TDD、Phase B v0.3 的冻结文本与含义 | CC 不具备更改上游设计/需求的权限 | CC-PRESERVE-004 |

## 7. 适用的 TDD 防护栏

本 CC 不运行会写状态的流程，不调用生产入口。以冻结 TDD V1.1.0 §§1–5、§§9–10 和动态行补充 §§1–5 作为只读审计目标；不改写章节内容。适用的安全约束以 SRS NFR-M2-006、项目 `docs/AGENTS.md` 和审计来源授权范围为准。

当前 TDD 未见可引用的命名 T-xxx Guardrail 列表；故不填虚构 ID。若后续需要实际实现或测试某项技术防护，须在 G3 前完成 TDD 基线核对并将适用 Guardrail 正确追溯。

## 8. 数据 / 迁移影响

| 字段 | 值 |
|---|---|
| 需要迁移 | 否 |
| 数据库访问 | 不允许 |
| 数据源 | 已存在的只读文档、测试日志及 G2 明确批准的进程/日志元数据 |
| 目标 | 经授权的 CC-01 IHR 文档 |
| 恢复 / 回滚策略 | 不改数据库或运行状态；若发现写操作必要，立即停止该分支并报告，不能扩大 G2 |
| 验证 | 记录审计前后 Git HEAD/status；核对仅有本 CC 获准报告文件新增 |

## 9. API / 集成影响

不调用或修改任何 API、Odoo ORM、Provider、Browser、附件或 Thread 消费链。无兼容性变更。

## 10. 安全 / 权限影响

| 字段 | 值 |
|---|---|
| 新权限 | 无；仅 G2 对明确来源提供只读检查授权 |
| 变更的 ACL | 无 |
| 数据访问 | 禁止数据库/ORM；仅读取 G2 明确列出的现存文档、日志及进程元数据 |
| 敏感数据暴露 | 遵守 SRS NFR-M2-006；不向 Provider/聊天/外部服务传输审计数据；按 §3.2 脱敏；密钥/Token 不写日志 |
| 安全边界 | 不注入或调试进程、不访问未授权路径、不绕过 OS/Odoo 权限；源无法读时标记 UNVERIFIED |

## 11. 测试契约

| 检查 ID | 对应交付 | 上游来源 | 检查类型 | 预期结果 | 实际执行 | 原因 |
|---|---|---|---|---|---|---|
| CC-TEST-001 | Runtime 三级身份分类 | Plan Phase 0；Phase A/A2 | 只读证据核查（非测试） | 分别报告 Workspace/Process/Loaded Module；仅直接可信 Loaded Module 证据支持 MATCH/MISMATCH，否则 UNVERIFIED；无推断、无扩权 | 冻结时状态为 NOT RUN；本轮实际核查状态见 IHR/ATR | 路径、启动时间等不能证明内存模块身份 |
| CC-TEST-002 | Thread 12063 既存材料核查 | Phase A2；Phase B v0.3 §10 | 只读 G2 批准的日志/导出/文档核查（非测试） | 不访问数据库/ORM/Thread 持久化记录；payload 缺失则历史根因 UNVERIFIED，并提出 CC-03 当前代码验证案例 | 冻结时状态为 NOT RUN | 不因历史材料缺失无限期阻塞 CC-01；不反推历史根因 |
| CC-TEST-003 | Phase B/TDD 差异处置矩阵 | Frozen Phase B v0.3；TDD V1.1.0 | 文档交叉核对（非测试） | 逐条给出对应、四态、证据差异、受影响 CC、建议、责任人和阻塞范围；GAP 不自动触发 TDD 修订 | 冻结时状态为 NOT RUN | 真实冲突/设计缺口走变更审批；不得由实施者改写冻结语义 |
| CC-TEST-004 | 测试数量/历史失败核查 | 原始 IHR/ATR/TV | 只读记录核对（非测试） | 有原始日志则调和；无证据则 OPEN/UNVERIFIED，保持历史状态 | 冻结时状态为 NOT RUN | 避免猜测 166 + 26 与 160 差异 |

**本 CC 明确禁止执行功能测试、自动化测试、Odoo TransactionCase、pytest 或浏览器/Provider 验证。** 只记录现有测试源码/测试选择器和既有运行日志；为 CC-03 列出的当前路径回归只作为后续测试设计输入，需在 G3 后执行。

## 12. 停止条件 / 升级闸门

| 触发条件 | 处理 |
|---|---|
| G2 只读授权未取得、授权来源/路径不明确 | 不开始读取外部运行材料；仅可由后续授权补齐 |
| 需要数据库/ORM、Provider、HTTP/RPC、Browser、测试执行或服务变更才能继续 | 停止该分支并标记 BLOCKED；申请独立授权，不扩大本 CC |
| 需要读取/保存密钥、个人数据、完整业务内容或未批准业务 payload | 立即停止并报告；不落盘、不复制 |
| 进程内模块身份无法直接证明 | 标 UNVERIFIED；不得用启动时间、目录、reload 或版本号替代证明 |
| Thread 12063 原始 pending payload/参数不可从获准的既存材料恢复 | 历史根因标 UNVERIFIED；IHR 记录具体缺项并提出后续 CC-03 当前代码验证案例；不访问数据库/持久化 Thread，不无限期阻塞本 CC |
| Phase B 与 TDD 有真实语义冲突/设计缺口 | 保留证据并转 TDD/设计变更流程；不在 CC 中调和、不改变冻结文本 |
| 发现有文件/运行状态改动超出获准审计报告 | 立即停止，不自行恢复/覆盖；记录差异并向负责人报告 |

## 13. 完成定义 / 关闭标准

本节定义未来执行完成标准；本草稿没有任何实际核查结果。

1. G2 授权记录与准许读取的来源路径一并保存在项目授权登记册；不超出范围。
2. IHR 记录执行起止时间、操作者、代码 HEAD、审计前后 Git status、所有证据路径/摘要及每项原生证据状态。
3. Workspace、Process、Loaded Module 三层身份分别给出有证据的状态；Loaded Module 只有直接可信证据才能判 MATCH/MISMATCH，否则标 `UNVERIFIED` 并列明 G4 可能需要的后续模块身份核验；不得推断或扩大 CC-01 取证权限。
4. Thread 12063 仅依据 G2 批准的既存日志、导出和文档核查。不得访问数据库、ORM 或 Thread 持久化记录。历史根因只有原始调用参数、pending payload、确认绑定和后续判定均有证据时才可确认；否则为 `UNVERIFIED`，并给出 CC-03 当前代码验证案例。
5. IHR 包含 Phase B/TDD 差异处置矩阵。差异按证据分类；`GAP` 不自动要求 TDD 修订。真实语义冲突或冻结设计缺口按变更审批；明确受影响的 G3 CC 在所需决定/证据未闭合时保持阻塞。
6. 166 + 26 与 160 的差异若无法从获准的现存证据解释，则登记 OPEN，且不阻断只读 CC-01 关闭；依赖错误计数的验收声明仍不得通过。
7. TV / 旧失败状态逐项保留；不得重写为 PASS、删除或代为豁免。
8. 未改变代码、测试、数据库、服务、附件、Provider 状态及 Git 版本控制索引；审计前后差异仅限已授权的 IHR 与 ATR 报告新增。
9. 分别作出三个判断： (a) CC-01 审计交付是否按授权范围完成；(b) 历史问题是否已被直接历史证据解决；(c) 后续 CC 是否达到独立放行条件。历史证据不可恢复时，(a) 可按实际审计证据关闭，而 (b) 必须保持 OPEN/UNVERIFIED；(c) 不因 (a) 自动通过，受影响 CC 按差异矩阵维持阻塞或另行授权。CC-01 关闭不代表行为、运行身份、E2E 或需求通过，G2 不授权后续 G3/G4/G5。

最终实际结果由 IHR 与其引用证据记录；不得在本 CC 中预填 PASS。

## 14. 追溯矩阵

### 14.1 正向：上游范围 → CC

| 上游 / 计划项 | CC-CHANGE | 备注 |
|---|---|---|
| Implementation Plan v0.2 §4 Phase 0 / CC-M2-B-01 | CC-CHANGE-001 | 形成只读基线核查 IHR；无生产行为变更 |
| Phase B v0.3 §§3–7、§10 与 M2 TDD V1.1.0 / 动态行补充 | CC-CHANGE-001 | 只读映射；发现冲突仅报告并升级 |
| Phase A/A2、TV 历史证据 | CC-CHANGE-001 | 保留原状态，补充可核验引用，不改原报告 |

### 14.2 反向：CC → 上游

| CC 项 | 上游 | 类型 |
|---|---|---|
| CC-CHANGE-001 | Implementation Plan v0.2 §4 Phase 0 | Plan |
| CC-CHANGE-001 | Phase B v0.3 §§3–7、§10 | Frozen design evidence |
| CC-PRESERVE-001–004 | SRS NFR-M2-006；TDD V1.1.0 §§1–5、§9–10；`docs/AGENTS.md` | Preserve / security boundary |
| CC-TEST-001–004 | Phase A/A2 与 TV report | Evidence requirements (not behavior acceptance) |

### 14.3 DDD

N/A；遵循 §1.2，不虚构 DDD 编号。

## 附录 A — 变更决策（CC-DEC）

无。本 CC 不作实现级或产品级新决策。

## 附录 B — 当前执行授权记录

| Gate | 状态 | 说明 |
|---|---|---|
| G1 Plan Approval | PASSED | 用户于 2026-11-06 批准冻结 Implementation Plan v0.2 |
| G2 CC-01 Read-only Authorization | GRANTED — WORKSPACE ONLY | 用户于 2026-11-06 批准冻结并执行 CC-01；仅限 §3.1 工作区来源，非工作区来源清单为 NONE；交付 IHR 与 ATR |
| G3 Coding Authorization | NOT GRANTED | 本 CC 无代码实现范围 |
| G4 Runtime Validation | NOT GRANTED | 不运行或触碰服务/数据库 |
| G5 Production Release | NOT GRANTED | 不适用本 CC |

## 附录 C — 术语

- **CC-01 只读核查**：在 G2 明确授权来源范围后，以不改变运行状态的方式检查现有代码、文档、日志和可见进程元数据。
- **历史根因 UNVERIFIED**：缺少直接历史证据，不能由当前代码或对话摘要反推过去实际执行路径。
- **当前代码路径验证**：CC-03 在获得 G3 后以当前基线建立的可复现行为测试；不等同历史 Thread 根因确认。

## 附录 D — 版本历史

v0.2 由用户批准冻结；v0.1 保留为历史草稿。G2 来源范围和输出限制详见 §3.1、§4.1 与附录 B。

| 版本 | 日期 | 变更说明 | 状态 |
|---|---|---|---|
| v0.1 | 2026-11-06 | 首次起草 CC-M2-B-01 只读 Runtime / Baseline Alignment 契约；未执行 CC-01 | DRAFT — NOT AUTHORIZED FOR EXECUTION |
| v0.2 | 2026-11-06 | 最小评审修订并经用户批准冻结；G2 限定为工作区只读审计，交付 IHR/ATR；不含运行时或数据库访问 | FROZEN — G2 WORKSPACE-ONLY READ-ONLY AUDIT AUTHORIZED |
