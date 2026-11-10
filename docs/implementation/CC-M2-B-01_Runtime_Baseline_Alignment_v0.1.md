<!--
Source template: docs/skill/odoo-project-workflow/references/templates/Coding/Coding_Contract模板.md
Source version/status: v1.0.0; Frozen
Template synchronization check: PASS, 2026-11-06
Contract status: DRAFT — NOT AUTHORIZED FOR EXECUTION
-->

# CC-M2-B-01 — Runtime & Baseline Alignment

## 文档信息

| 项目 | 内容 |
|---|---|
| Intent ID | M2-B-01-RUNTIME-BASELINE |
| 模块 | Odoo 18 CE / `office_engine_m2`（仅审计目标；不实施代码） |
| 工作类型 | 只读技术审计 / 基线核查，文档证据交付 |
| 变更类型 | 只读证据收集 |
| 状态 | **DRAFT — NOT AUTHORIZED FOR EXECUTION** |
| 目标 | 在不改变工作区、服务、数据库或测试状态的前提下，形成当前运行身份、历史异常、测试基线及 Phase B/TDD 对齐的可审计证据。 |
| 背景 | 已冻结的后续范围计划要求 CC-01 先完成只读核查；Phase A/A2 留有 Runtime 模块身份、Thread 12063 与 Odoo 测试统计等未验证事项。 |
| 实施计划基线 | `docs/implementation/IMPLEMENTATION_PLAN_office_engine_m2_state-continuity_v0.2.md` — FROZEN（G1 已批准）；`Baseline validity: IMPACT REVIEW REQUIRED` |
| 单独执行门禁 | G2 — CC-01 Read-only Authorization **尚未批准**。本稿不构成只读执行授权。 |
| 版本 / 日期 | v0.1 / 2026-11-06 |

> 本文件是 CC-01 执行契约草稿。未经单独 G2 书面授权，不得开始 CC-01 核查。计划冻结仅通过 G1，不批准读取未列明的运行日志、访问数据库、运行测试、重启服务或实施代码。

---

## 0. 文档治理与编号

本 CC 遵循组织级 Coding Contract 模板 v1.0.0。CC 自有编号仅使用 `CC-CHANGE`、`CC-PRESERVE`、`CC-TEST`、`CC-DEC` 前缀；本次没有已获批的实现级决策。所有编号均属于本 Draft；只有本契约获评审和执行授权后才冻结。

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

仅在 G2 获批后执行下列只读核查：

1. 固定审计起始的 Git HEAD 与工作区状态；审计结束再次记录，确认除获准的审计报告文档外没有工作区变化。
2. 核查 8091 进程的可见 PID、可执行文件、命令行、工作目录、配置/addons 路径及可安全取得的 Python 模块路径/身份信息。若不能直接证明进程内已加载模块与工作区源码一致，结论必须是 `UNVERIFIED`；不得根据进程启动时间、目录路径、日志时间、Registry reload 或模块版本号推断匹配。
3. 只读检查 G2 明确列出的既有日志/导出证据；核查 Thread 12063 的原始调用参数、工具结果、pending confirmation、Session/Proposal/Preview 身份与确认后执行范围。只要原始证据无法从已批准来源恢复，就记录具体缺项并保持历史根因 `UNVERIFIED`。
4. 只读追踪当前工作树的确认生成、持久化、匹配/失效、执行前重验调用链，检查相关测试源码及既有日志；不运行测试。提出供 CC-03 使用的当前代码行为验证案例，不代替 CC-03 执行。
5. 对 Phase B v0.3 冻结条款与正式 TDD V1.1.0 / 动态行补充逐项制作映射，标为 `MATCH / GAP / CONFLICT / UNVERIFIED`，列出文档条款和代码/测试位置。冻结语义不得由本 CC 改写；真实缺口或冲突提交 TDD/设计变更路径。
6. 只读核对测试入口、测试选择器、已有日志中的发现数和最终汇总数；特别核查历史的 `166 + 26` 与 `160` 差异。无法解释时保留 `OPEN`，不猜测、不改测试标准。
7. 逐项登记 TV 报告中的历史失败、跳过、阻塞和缺证据项；不得修改原始 TV/IHR/ATR/HVR。
8. 生成一份 CC-01 只读审计 IHR，给出证据路径/时间/摘要、结论状态、owner、后续门禁和未验证原因。

### 2.2 明确超出范围

- 任何 Python/XML/JS/SCSS/配置/测试代码、SRS/DDD/TDD/Phase B 或计划之外文档的修改；唯一未来可写交付物是 G2 明确允许的 CC-01 IHR。
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

实际执行前，G2 授权记录必须列出可读取的非工作区日志/进程元数据来源及路径范围。当前契约草案不预设具体日志文件或 OS 进程检查命令。授权未列出的路径、进程数据或敏感字段不可读取。

工作区读取限于本 CC 引用的源代码、测试源码、SRS/TDD/Phase B/计划、既有审计/测试报告及 Git 元数据。外部来源只限 G2 明确批准的既有日志与进程元数据。

### 3.2 脱敏与保存

- 只记录能回答审计问题的最小元数据；不复制业务内容、个人数据、Provider payload 正文、令牌、密钥、完整环境变量或附件字节。
- 进程环境如必须确认配置项是否存在，只记录变量名和“存在/不存在”，对值完全省略；任何 token/secret 立即排除，不写入 IHR。
- 日志引用用受控路径、时间/行号或不可逆摘要定位；如包含敏感内容，只记录错误类别和必要上下文，不复制原文。
- IHR 只写入 G2 批准的文档目录。不得把证据上传 Provider、Thread、Issue 或外部存储。

### 3.3 状态判定

运行身份分别记录 `MATCH / MISMATCH / UNVERIFIED`；历史事件每个证据项记录 `AVAILABLE / UNAVAILABLE / UNVERIFIED`；基线条款记录 `MATCH / GAP / CONFLICT / UNVERIFIED`；测试历史按原始 `PASS / FAIL / SKIPPED / BLOCKED / NOT RUN` 保持。不能将源代码推断、测试源码或模型叙述写成运行时事实。

## 4. 变更边界

### 4.1 允许

| 类型 | 详情 |
|---|---|
| 本次草稿文件 | `docs/implementation/CC-M2-B-01_Runtime_Baseline_Alignment_v0.1.md`（仅本轮形成草案） |
| G2 后唯一审计产物 | `docs/implementation/IHR-M2-B-01_Runtime_Baseline_Alignment.md`（如 G2 授权执行并生成；当前未创建） |
| 只读输入 | §3.1 所列工作区文件与 G2 明确列出的进程/日志来源 |

### 4.2 禁止

| 类型 | 详情 |
|---|---|
| 生产实现 | 所有 addon、模块、Python、XML、JS、CSS、配置、资产与迁移脚本 |
| 测试与执行 | 测试源码、测试数据库、测试运行、Odoo shell、Provider、HTTP/RPC、Browser 操作 |
| 数据 / 外部状态 | 数据库及业务记录、附件、Thread、Session、Proposal、文件内容、模块状态和服务状态 |
| 版本控制 | `git add`、commit、push、reset、clean、stash、checkout/restore 或任何覆盖式操作 |
| 文档 | 除本 CC 草稿及获批后唯一的 CC-01 IHR 外的全部文档与证据文件 |

## 5. 必需的审计交付（非生产行为变更）

| ID | 当前已知状态 | 期望审计结果 | Contract Item |
|---|---|---|---|
| 1 | Phase A/A2 未能证明进程内 Python 模块身份 | 以直接可得证据判定 MATCH/MISMATCH；否则明确 UNVERIFIED 并列出最小后续 Runtime 验证条件 | CC-CHANGE-001 |
| 2 | Thread 12063 有“确认后失败”的对话摘录，原始 pending payload 可能不可恢复 | 保留历史根因状态；当前代码生成/绑定/重验链有源码证据；建议 CC-03 当前行为用例；缺失事实不推断 | CC-CHANGE-001 |
| 3 | 既有 Odoo 记录中的计数 166 + 26 与最终 160 未解释 | 找到并引用能够调和统计口径的原始证据；否则登记 OPEN 和责任方 | CC-CHANGE-001 |
| 4 | Phase B v0.3 已冻结，但与 TDD 对齐尚未完成 | 产生逐条映射和 GAP/CONFLICT 项；冻结语义保持不变，设计缺口转上游变更流程 | CC-CHANGE-001 |
| 5 | TV 历史报告包含 FAIL/INCONCLUSIVE/UNVERIFIED | 保留原状态并说明受影响的后续阶段；不得重写或豁免 | CC-CHANGE-001 |

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
| CC-TEST-001 | 运行身份与工作区身份分类 | Plan Phase 0；Phase A/A2 | 只读证据核查（非测试） | 直接证据支持 MATCH/MISMATCH；否则 UNVERIFIED；无推断 | 本草稿阶段 NOT RUN；G2 后按范围执行 | 不能把路径/启动时间等旁证当成内存模块身份 |
| CC-TEST-002 | Thread 12063 证据核查 | Phase A2；Phase B v0.3 §10 | 只读既有日志核查（非测试） | 原始 payload 可得则逐项引用；否则根因 UNVERIFIED，转列 CC-03 当前代码行为测试 | 本草稿阶段 NOT RUN | 历史数据缺失不能凭模型回复反推根因 |
| CC-TEST-003 | Phase B/TDD 条款映射 | Frozen Phase B v0.3；TDD V1.1.0 | 文档交叉核对（非测试） | 每条语义有准确出处及 MATCH/GAP/CONFLICT/UNVERIFIED；不改变冻结语义 | 本草稿阶段 NOT RUN | TDD 对齐影响后续 G3，但不阻止 CC-01 草案准备 |
| CC-TEST-004 | 测试数量/历史失败核查 | 原始 IHR/ATR/TV | 只读记录核对（非测试） | 有原始日志则调和；无证据则 OPEN/UNVERIFIED，保持历史状态 | 本草稿阶段 NOT RUN | 避免猜测 166 + 26 与 160 差异 |

**本 CC 明确禁止执行功能测试、自动化测试、Odoo TransactionCase、pytest 或浏览器/Provider 验证。** 只记录现有测试源码/测试选择器和既有运行日志；为 CC-03 列出的当前路径回归只作为后续测试设计输入，需在 G3 后执行。

## 12. 停止条件 / 升级闸门

| 触发条件 | 处理 |
|---|---|
| G2 只读授权未取得、授权来源/路径不明确 | 不开始读取外部运行材料；仅可由后续授权补齐 |
| 需要数据库/ORM、Provider、HTTP/RPC、Browser、测试执行或服务变更才能继续 | 停止该分支并标记 BLOCKED；申请独立授权，不扩大本 CC |
| 需要读取/保存密钥、个人数据、完整业务内容或未批准业务 payload | 立即停止并报告；不落盘、不复制 |
| 进程内模块身份无法直接证明 | 标 UNVERIFIED；不得用启动时间、目录、reload 或版本号替代证明 |
| Thread 12063 原始 pending payload/参数不可恢复 | 历史根因标 UNVERIFIED；以当前源码链审阅和 CC-03 当前回归作为替代路径，不无限期阻塞本 CC |
| Phase B 与 TDD 有真实语义冲突/设计缺口 | 保留证据并转 TDD/设计变更流程；不在 CC 中调和、不改变冻结文本 |
| 发现有文件/运行状态改动超出获准审计报告 | 立即停止，不自行恢复/覆盖；记录差异并向负责人报告 |

## 13. 完成定义 / 关闭标准

本节定义未来执行完成标准；本草稿没有任何实际核查结果。

1. G2 授权记录与准许读取的来源路径一并保存在项目授权登记册；不超出范围。
2. IHR 记录执行起止时间、操作者、代码 HEAD、审计前后 Git status、所有证据路径/摘要及每项原生证据状态。
3. Runtime 身份给出有直接证据的 `MATCH/MISMATCH`，或诚实标为 `UNVERIFIED` 并列明 G4 需要的当前模块身份核验；不得推断。
4. Thread 12063 的历史根因只能在原始参数、pending payload、确认绑定和后续判定均有证据时标为已确认；否则维持 `UNVERIFIED`，同时给出 CC-03 当前路径的具体回归点。
5. Phase B v0.3 与 TDD 的映射完整；语义差异/缺口标出来源和责任门禁。未完成对齐的项不得放行其受影响 G3 编码 CC。
6. 166 + 26 与 160 的差异若无法从实际日志解释，则登记 OPEN，且不阻断只读 CC-01 关闭；依赖错误计数的验收声明仍不得通过。
7. TV / 旧失败状态逐项保留；不得重写为 PASS、删除或代为豁免。
8. 未改变代码、测试、数据库、服务、附件、Provider 状态及 Git 版本控制索引；审计前后差异仅限已授权的 IHR 报告新增。
9. CC-01 关闭状态只说明只读证据已记录，不代表任何代码行为、运行身份、E2E 或需求已通过；G2 不授权后续 G3/G4/G5。

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

无。本草案不作实现级或产品级新决策。

## 附录 B — 当前执行授权记录

| Gate | 状态 | 说明 |
|---|---|---|
| G1 Plan Approval | PASSED | 用户于 2026-11-06 批准冻结 Implementation Plan v0.2 |
| G2 CC-01 Read-only Authorization | NOT GRANTED | 当前用户要求起草契约；未授权执行只读核查 |
| G3 Coding Authorization | NOT GRANTED | 本 CC 无代码实现范围 |
| G4 Runtime Validation | NOT GRANTED | 不运行或触碰服务/数据库 |
| G5 Production Release | NOT GRANTED | 不适用本 CC |

## 附录 C — 术语

- **CC-01 只读核查**：在 G2 明确授权来源范围后，以不改变运行状态的方式检查现有代码、文档、日志和可见进程元数据。
- **历史根因 UNVERIFIED**：缺少直接历史证据，不能由当前代码或对话摘要反推过去实际执行路径。
- **当前代码路径验证**：CC-03 在获得 G3 后以当前基线建立的可复现行为测试；不等同历史 Thread 根因确认。

## 附录 D — 版本历史

| 版本 | 日期 | 变更说明 | 状态 |
|---|---|---|---|
| v0.1 | 2026-11-06 | 首次起草 CC-M2-B-01 只读 Runtime / Baseline Alignment 契约；未执行 CC-01 | DRAFT — NOT AUTHORIZED FOR EXECUTION |
