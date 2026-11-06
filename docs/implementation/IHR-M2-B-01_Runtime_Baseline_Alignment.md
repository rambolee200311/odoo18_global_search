# IHR-M2-B-01 — Runtime & Baseline Alignment

| 项目 | 记录 |
|---|---|
| CC | `CC-M2-B-01_Runtime_Baseline_Alignment_v0.2.md`，FROZEN；G2 仅批准工作区只读审计 |
| 日期 | 2026-11-06 |
| 审计范围 | 当前工作区、契约列明的源码/测试源码、规范与既有 M2 报告；不包括进程、8091 服务、外部日志、数据库/ORM、Provider、Browser 或测试执行 |
| IHR 结论 | **CC-01 审计交付：COMPLETE WITH OPEN / UNVERIFIED ITEMS**；不代表运行或功能验收 PASS |
| 历史问题解决 | Thread 12063 根因仍为 `UNVERIFIED` |
| 后续 CC 放行 | **未自动放行**；受影响范围仍需单独基线影响决策和相应门禁 |

## 1. 授权与证据边界

用户于 2026-11-06 批准冻结 CC-01 并进入执行。本轮按 CC §3.1 将 G2 限定为该契约列出的工作区源文件、测试源码、规范、既有审计/验证报告和 Git 只读元数据；工作区外来源清单为 `NONE`。IHR 与 ATR 作为用户明确要求的审计交付物记录在 CC 执行授权中。

未连接数据库或 ORM，未读取 Thread / Session 持久化记录；未检查 OS 进程、8091 服务状态或外部日志；未运行测试、Provider、HTTP/RPC 或浏览器操作；未读写业务数据；未重启服务、升级模块、暂存或提交 Git。无法由批准来源直接证明的事项标记为 `UNVERIFIED`。ATR 记录历史测试证据和本轮 `NOT RUN`，不构成测试执行。

## 2. 工作区基线

| 项目 | 审计开始记录 |
|---|---|
| 仓库分支 | `main`，与 `origin/main` 同步（当时 `git status --short --branch` 显示 `## main...origin/main`） |
| HEAD | `3ccb863430cd33b70952fd57cadc7624d284e3cf` |
| 已存在未跟踪项 | `.coverage`、`docs/A审计报告.md`、`docs/A2审计报告.md`、`docs/B技术设计草案.md`、CC v0.1/v0.2 草稿、Implementation Plan v0.1/v0.2 |
| 本轮授权新增/更新文档 | 冻结登记 CC v0.2；本 IHR；配套 ATR |
| 版本控制写操作 | 无；未 stage、commit、push、reset、clean 或恢复文件 |

文件处于未跟踪状态，Git 不会显示这些文件的内容差异；上表如实记录了命令输出和本轮允许的文档交付。审计结束状态见 §9。

## 3. Runtime 身份证据

| 层级 | 证据与结论 | 状态 |
|---|---|---|
| Workspace | 本轮读取的源码与文档位于 `/Users/lijianqiang/Documents/odoo18_global_search`，Git HEAD 为上表 SHA。这里确认的是当前工作区身份。 | `MATCH`（仅对被读取的工作区基线） |
| Process | 本轮 G2 未批准 OS 进程元数据来源；未查询 PID、可执行文件、命令行、工作目录或 addons 路径。Phase A/A2 的旧报告曾记载 PID/路径，但不是本轮直接证据。 | `UNVERIFIED` |
| Loaded Module | 本轮没有经 G2 批准的直接运行诊断可证明进程中实际加载模块及其代码指纹。源码路径、历史进程信息、启动时间、日志时间、Registry reload 均不能证明内存模块与工作区相同。 | `UNVERIFIED` |

**结论：不能报告 `Runtime Code != Workspace Code`，也不能报告运行代码匹配。** Phase A2 记录过旧错误行为与当前工作区逻辑不一致，但这只是历史报告中的行为差异，不能替代直接 Loaded Module 身份证据。由于缺乏外部取证授权，本轮不扩大权限补证。

## 4. Thread 12063 历史事件

本轮只读了获准的既有文档和工作区源码，没有查询数据库或 Thread 持久化记录。`docs/A2审计报告.md` §1 记录：Session 9870 首次请求返回 `needs_confirmation`；用户回复“确认”；其后两次相同参数摘要的调用返回 `force_override_flag_required`、`operation_executed=false`；完整 pending payload 未保留。A2 还记录另一 Session 后来成功，但其不能证明原 Session 9870 已恢复。

本轮静态检查当前 `mymodules/office_engine_m2`、`mymodules/office_core` 与 `mymodules/odoo-llm/llm_assistant` 时，未发现 `force_override_flag_required` 字符串。当前工作区的 `_cell_override_confirmation_gate()` 在 [office_mapping_tools.py:1542–1617] 中核对 Thread、用户、Session revision、Proposal revision、预览附件、模板/上下文/文件指纹、观察值及操作范围；确认消息和拒绝分支见 [office_mapping_tools.py:1618–1687]。重复行扩展与派生写入进入同一 Gate 的调用见 [office_mapping_tools.py:3028–3073]。

| 判断 | 结果 |
|---|---|
| 对话摘录是否显示确认后再次失败 | 是；由 Phase A2 既有报告记录 |
| 当前源码是否含历史错误码 | 本次工作区静态搜索未发现；搜索范围受 CC 限定 |
| 是否已证明 8091 当时加载了不同代码 | 否；Loaded Module 身份 `UNVERIFIED` |
| 是否能恢复原 pending payload 并确认具体失败分支 | 否；历史根因 `UNVERIFIED` |
| 是否用另一 Session 的成功替代原 Session 恢复证明 | 否 |
| 替代验证输入 | 后续 CC-03 在独立授权后，以当前代码覆盖“确认前不写、有效确认精确执行、范围/版本变化令旧确认失效、同 Session 失败后安全重试”的行为用例；这只能验证当前代码，不能改写历史根因 |

## 5. 当前工作区调用链与状态证据

```text
原生 llm.thread / llm_assistant
  → Provider assistant tool_calls
  → llm_tool 执行并持久化 tool message
  → office_prepare_context / office_save_mapping_preview / office_finalize
  → Proposal 校验、revision 与确认 Gate
  → render_bridge 从源附件和当前授权数据编译完整 Proposal
  → office_core / office_verify 执行、保存后回读
  → Preview/Finalize artifact 与聊天消息/Store 元数据
  → 原生循环继续 Provider 请求；最终自然语言由模型生成
```

主要源码位置：

- 原生工具循环在 `mymodules/odoo-llm/llm_assistant/models/llm_thread.py:259–284`；每个工具消息后 commit，后续 Provider 请求在 `:289–328`。因此“工具调用消息完成”与“下一次模型回复成功”是不同阶段。
- Office 工具消息外层及 tool-call ID 构造在 `mymodules/odoo-llm/llm_tool/models/mail_message.py:40–69`；原生框架的外层完成状态不等于 Office 业务成功。Phase A 报告也记录该层级区别。
- Session 中保存 `revision`、`proposal_revision`、完整 `mapping_rules_json`、最多 20 个 Proposal 历史快照、确认 revision、预览附件及数据/模板指纹，见 `mymodules/office_engine_m2/models/office_mapping_session.py:107–143, 455–509`。该快照是 Proposal 规则历史，不是逐操作 Effect 账本。
- `render_bridge` 的编译从源附件读取并按当前授权数据形成完整候选，见 `mymodules/office_engine_m2/services/render_bridge.py:133–319`；Finalization 重检模板/数据和确认版本见 `:572–658`。实现沿用完整 Proposal 重编译，不以上一 Preview 字节为下一轮文件基线。
- `office_finalize()` 检查当前 Proposal/Session revision 与精确用户确认，成功需有输出附件、消息、文件名和 MIME 元数据，见 `mymodules/office_engine_m2/models/office_mapping_tools.py:3238–3349`。
- M2 Thread 预览附件 Store 发布和 Finalize Store 读取/失败回写见 `mymodules/office_engine_m2/models/llm_thread.py:420–505`。源码能说明预期处理路径；本轮未浏览器验证附件可见性。

上述是当前工作区的源码证据，不代表本轮已执行这些路径，也不证明 8091 正在运行同一代码。

## 6. Phase B v0.3 / TDD 差异处置矩阵

状态含义：`MATCH` 表示条款语义在两份冻结设计间可对应；`GAP` 表示 Phase B 已冻结的补充契约在当前 TDD 文本中没有对应定义，不等同于代码缺陷，也不自动要求修订 TDD；`UNVERIFIED` 表示参数/证据未定；本轮未发现有证据支持的规范互斥 `CONFLICT`。

| Phase B 条款 | 对应 TDD / 动态行条款 | 状态 | 实际差异及工作区证据 | 受影响 CC | 建议处置 | 责任人 | 阻塞范围 |
|---|---|---|---|---|---|---|---|
| §1、§5.1：原始文件 + 当前授权数据 + 当前完整 Proposal 重编译；线性操作，不隐式以 Preview 作基线 | TDD v1.1 §§2–4：Session/revision、完整 Proposal 更新、从源附件重新渲染 | `MATCH` | TDD 明确源附件/当前数据、Proposal revision 和重新编译；当前 `render_bridge.py:133–319` 与此相符 | B-03、B-04、B-05 后续变更仍须按各自 CC | 沿用既有基线；若后续实现偏离，应在相应 CC 说明 | 技术负责人 | 本项不单独阻塞 |
| §3：类型化 Expression AST（literal/field/concat/coalesce/arithmetic/date_offset），False/0/null 语义及确定性求值 | TDD v1.1 §3.1–3.2：`m2.mapping-proposal.v1`、字段/目标映射与增量完整 Proposal；动态行补充 §§1–4：scalar `source_field` | `GAP` | 冻结 Phase B 规定的组合表达式契约在 TDD/动态行正文无对应结构；这是已批准补充设计的基线覆盖差异，不证明当前实现运行失败 | B-02；依赖表达式的 B-03/B-04/B-05 | 审批者/技术负责人决定 Phase B v0.3 是否作为补充权威基线，或是否需要正式 TDD 补充；不得由 CC 实施者自行选择。不能仅因有 GAP 就自动改 TDD | 技术负责人、审批者 | B-02 的 G3 前需完成该条款的权威映射/处置；仅影响依赖此语义的 CC |
| §4：`execution_verified`、`coverage_declared`、`task_completed` 分离；结构化预期效果与回读比对 | TDD v1.1 §§3.1–4：Proposal 完整性、M1 回读及 Preview；没有覆盖清单不能证明自然语言完整性的规则 | `GAP` | TDD 提供结构化映射校验和文件回读，但未定义三层结果声明及未覆盖要求的反馈语义 | B-04；用户反馈适配关联 B-05 | 明确 Phase B 补充设计的适用权威及与 TDD 的追溯；只有审批认定 TDD 冻结文本需承载该规范时才提出 TDD amendment | 产品/技术负责人 | B-04 G3 前完成条款归属；不因此阻塞无关 CC |
| §5.2–5.5：Patch `set/remove/clear/restore`、dormant 规则不自动激活、排序/范围变化后重解析、完整 Restore | TDD v1.1 §§2–3：proposal_revision、受控增量更新、数据/模板改变时重建；无 dormant 和逐项 Patch 动作语义 | `GAP` | TDD 覆盖整体 Proposal revision 与当前重编译；Phase B 细化了新增的 patch 状态/重激活边界。动态行补充只定义有限目标目录，不等于 dormant 恢复契约 | B-03；后续 B-04 | 将既有 TDD 行为与新增的冻结语义逐条区分；确定是否用新增 CC 契约承载或走规范补充，不默认局部 Restore | 产品/技术负责人 | B-03 G3 前必须明确，不阻塞 B-01 关闭 |
| §5.4–5.5：确认绑定规范化表达式、求值数据基线、最终目标、实际 Effect/写入值、旧值与覆盖范围 | TDD v1.1 §§2、4.2：session/proposal revision、模板/数据指纹、当前值重读与重新确认；未定义表达式 Effect 指纹（当前 TDD 无新表达式） | `GAP`（扩展契约） | 对既有映射/模板/数据 revision 的确认约束可对应；表达式求值后的值/Effect 是新契约，TDD 未逐项写出。当前 Gate 的字段与操作范围匹配在 `office_mapping_tools.py:1595–1617`；本轮未执行其行为 | B-03、B-04 | 先映射当前 Gate 可覆盖范围与新表达式新增范围，再由设计负责人判定需补充 TDD 还是由 CC 明确追溯；不要在 CC-01 裁定运行缺陷 | 技术负责人 | 涉及表达式 Effect 的 B-03/B-04 G3 前完成；其余现有 Gate 语义可独立审查 |
| §6：Outcome + `artifact_stage` + `delivery_state` 兼容现有结果；五类用户结果语义 | TDD v1.1 §2 状态机、§4 Preview/Finalize 与附件失败行为；未统一五类 Office 对外 outcome | `GAP` | TDD 覆盖 Session 状态和文件/附件路径，Phase B 另外要求服务端适配层统一结果语义；当前 `_normalize_office_mapping_result()` 仍使用 `success/needs_confirmation/blocked/error/incomplete` 等，见 `office_mapping_tools.py:61–105` | B-05 | 评审并确认兼容适配不改变冻结 TDD 的状态语义；GAP 不自动等于新增全局状态框架或 TDD amendment | 技术负责人 | B-05 G3 前完成接口映射决策；不阻塞本次只读报告 |
| §3.1：表达树深度 8、节点 64、concat 32 仅为待测建议，不是冻结限制 | TDD v1.1 未规定这些数值；B v0.3 §3 明确需中性测试后校准 | `UNVERIFIED`（待测参数） | 本轮未运行压力/边界测试；这些阈值不可写为当前强制限制 | B-02 | 由 B-02 在授权测试中取证并提交参数建议；保持 OPEN，不能由实施者按建议值直接冻结 | QA/技术负责人 | 仅阻塞以这些具体阈值作出的验收，不阻止 B-01 交付 |
| §5.5/§6.1：目标不明确需 clarification；用户确认仅解除业务风险，不绕过 ACL、安全和技术限制 | TDD v1.1 §§1、3、4：自然语言澄清、强校验、权限重读、精确确认和版本一致性 | `MATCH`（原则层） | 两份设计的用户确认与安全权限边界一致；动态行补充也要求当前用户权限与服务端目标目录 | B-02–B-06 | 保留此原则，具体实现证据在后续 CC 验证 | 技术负责人 | 无独立阻塞 |

矩阵是基线对齐记录，不是 TDD 修改申请或修改决定。当前实施计划 OIP-B-007 仍为 `IMPACT REVIEW REQUIRED`；受影响的编码 CC 必须在各自 G3 前记录已批准的处置，不能把 CC-01 关闭当成放行。

## 7. 既有测试和历史验证证据

本轮只检查测试源码和已存在报告，没有执行测试。测试源代码中的确认、重试、恢复和附件用例只能证明覆盖意图/存在，不能声明本轮通过。具体测试资产及历史数字见配套 [ATR-M2-B-01](ATR-M2-B-01_Runtime_Baseline_Alignment.md)。

`docs/verification/TV_office_engine_m2_report.md` 保留的历史结论为 TV-M2-001 `FAIL`、TV-M2-002 `INCONCLUSIVE`、TV-M2-003 `PASS`、TV-M2-004 `INCONCLUSIVE`。本轮未重跑，不改写历史状态。

现有 Phase C ATR 报告分别记录模块统计 `office_engine_m2: 166 tests`、`office_engine_odoo: 26 tests`，最终 runner 汇总 `0 failed, 0 error(s) of 160 tests`。当前批准范围内未找到能调和这三个数字口径的原始日志说明，故统计差异保持 `OPEN`；不推测原因，也不重跑。依赖“160 项”作为完整覆盖数的声明不能据此确认。

## 8. Findings 与状态

| ID | 状态 | 判断 | 责任 / 影响 |
|---|---|---|---|
| IHR-B01-01 | `UNVERIFIED` | Process 与 Loaded Module 身份无获准直接证据；没有证据可宣布运行代码和工作区相同或不同 | 环境/运行负责人；影响任何依赖 8091 运行身份的声明 |
| IHR-B01-02 | `UNVERIFIED` / `OPEN` | Thread 12063 的对话结果由 Phase A2 记录，但本次未访问持久化记录，且原始 pending payload 缺失；具体历史根因无法还原 | QA/技术负责人；不无限期阻塞 CC-01 审计交付，当前行为须后续验证 |
| IHR-B01-03 | `GAP` | Phase B 类型化表达式、Effect 和空值契约没有对应 TDD 结构 | 技术负责人/审批者；阻塞依赖该语义的 B-02 及其下游 G3，处置不自动等于 TDD 修订 |
| IHR-B01-04 | `GAP` | Intent Coverage 与 Execution Verification 分离未在 TDD 定义 | 产品/技术负责人；影响 B-04 基线对齐 |
| IHR-B01-05 | `GAP` | dormant、完整 Restore 与 set/remove/clear 生命周期细节未在 TDD 定义 | 产品/技术负责人；影响 B-03 基线对齐 |
| IHR-B01-06 | `GAP` | 五态 Outcome 适配语义在 Phase B 比当前 TDD 更具体 | 技术负责人；影响 B-05 基线对齐 |
| IHR-B01-07 | `OPEN` | 166 + 26 与 160 的历史统计差异无本轮可核对的解释 | QA；仅依赖该计数的验收声明受阻 |
| IHR-B01-08 | `NOT RUN` | 当前代码行为测试、Odoo TransactionCase、Provider/Browser E2E 未执行 | 各后续 CC 的单独门禁控制 |

## 9. 三项关闭判断与工作区结束状态

1. **CC-01 审计交付：COMPLETE WITH OPEN ITEMS。** 已对 G2 批准的工作区范围完成只读核查，并记录证据边界与未验证项。无法取得历史材料或外部 Runtime 证据没有阻止本范围交付。
2. **历史问题解决：NO。** Thread 12063 根因继续 `UNVERIFIED`；统计差异继续 `OPEN`；不得把当前源码审阅或另一 Session 成功写成历史问题已解决。
3. **后续 CC 放行：NO。** CC-01 完成不通过 G3。B-02/B-03/B-04/B-05 的相关 GAP 和决定必须按矩阵逐项处置；CC-06 还需 G4。G5 Production Release 未授权。

审计结束执行 `git status --short --branch`：分支仍为 `main...origin/main`；无 tracked file change；既有未跟踪文件仍在，本轮授权输出为 CC v0.2 冻结状态登记、IHR 与 ATR。未运行任何测试，也未运行 `git diff --check`；本次未做 Git 暂存或其他版本控制写入。最终状态快照与 HEAD 见配套 ATR §2.1；该快照包含本轮授权创建的 ATR 文件。

