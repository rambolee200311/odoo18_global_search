# CC-M2-CB-08 — Integrated Regression & Release Readiness

## 文档信息

| 项目 | 内容 |
|---|---|
| 项目 | Odoo 18 CE / Office Engine M2 Route B |
| 契约编号 | CC-M2-CB-08 |
| 版本 | v0.1 |
| 状态 | **FROZEN — IMPLEMENTATION AUTHORIZED** |
| 依据 | Frozen [TDD V2.1.0](../design/TDD_office_engine_m2_v2.1.0_LLM_Native.md)；Route B [ADR v1.0](../design/ADR-OFFICE-20261110-001_v1.0.md)；[Implementation Plan V2.0.1](IMPLEMENTATION_PLAN_office_engine_m2_v2.0.1.md) + [approved V2.0.2 CB-07 amendment](IMPLEMENTATION_PLAN_office_engine_m2_v2.0.2_CB07_Amendment.md)；CC-M2-CB-07 `CLOSED — UAT PASSED` |
| 目的 | 只处理原计划中经证据审计确认仍未覆盖的集成验证；不重开 CC-07，不授权生产发布 |

本契约把原 Implementation Plan §10–11 拆为 **18 个可追踪核对项**：§10 的 11 个原子验收项（将 §10.F 五类故障分别列项）和 §11 的 7 个测试矩阵项。重复映射用于保持可追溯，不代表重复执行。

## 1. Contract Goal

复用 CC-07 已完成的真实 Provider、Odoo、Discuss、版本、Candidate、Accept/Reject、Finalize、下载和 M1 回归证据；只补充三个经核对未被现有证据直接证明的行为：

1. 真实 Provider 对普通 XLSX 执行一次常见格式修改，并将实际输出作为 Candidate 按现有正式服务接受及独立回读。
2. 同一 Thread 两次读取之间，合成 Odoo 记录发生变化后，第二次 Retriever 调用返回新值，并将该次读取结果交给后续编辑路径。
3. 第二次读取前撤销测试用户对合成记录的读取权限时，Retriever 拒绝读取，不发生 Provider 调用、Candidate 创建或 Current 推进。

除上述定向验证外，不增加功能，不因一般 Excel 特性未覆盖而扩大支持承诺。CC-08 是技术集成与就绪证据，不是生产发布批准，也不重复组织 CC-07 完整人工 UAT。

## 2. 当前代码与证据基线

### 2.1 文档和运行基线

- 设计基线为 [TDD V2.1.0](/Users/lijianqiang/Documents/odoo18_global_search/docs/design/TDD_office_engine_m2_v2.1.0_LLM_Native.md)；CC-07 期间的适用修订及负责人决定按 CC-07 关闭记录执行。原两阶段 Inspection/Plan 与 Effect Binding 草案不得覆盖 CC-07 最终简化结果。
- 计划基线为 [Implementation Plan V2.0.1 §10–12](/Users/lijianqiang/Documents/odoo18_global_search/docs/implementation/IMPLEMENTATION_PLAN_office_engine_m2_v2.0.1.md)，并受 [V2.0.2 CC-07 Consolidation Amendment](/Users/lijianqiang/Documents/odoo18_global_search/docs/implementation/IMPLEMENTATION_PLAN_office_engine_m2_v2.0.2_CB07_Amendment.md) 修订。
- CC-07 已按普通 XLSX 多轮编辑与交付标准关闭。当前工作区 `HEAD=a89cd7b`，并存在未提交源代码、测试和证据改动；不得把此工作区描述为干净或可仅凭 commit 重建的发布基线。
- `ATR-RUN-042` 在当前 Route B 主要源码改动之后记录 236 个 `Starting Test`，最终 `tests.result` 为 236 tests、0 failed、0 errors。Responses Adapter 独立测试日志和真实 UI HVR 在其后生成；其间 `responses_adapter.py` 仅移除一行空白。证据可用于本工作区行为验收，但 CC-08 记录必须同时保存执行时的 HEAD、工作树状态及相关源码文件 SHA-256。
- 本次只读发现项目 `odoo.conf` 文件值为 `office_engine_m2_external_provider_dispatch_enabled=True`、输出 Token 上限 4096、超时 120 秒、容器内存 `1g`（`odoo.conf:29-32`）；这不单独证明已运行进程已经加载该值。服务端读取配置并默认关闭的实现位于 `edit_orchestrator.py:44-81`；8091/8092 历史 HVR 提供了当时实际 Provider 调用证据。当前 Tool description 又保留“External Provider file processing remains disabled while the SRS/data-policy release gate is open”的静态文案；真实 HVR 已证明获批测试路径可以运行，因此将其记录为环境文案需避免混淆的非阻断项，不在本 CC 擅改 Tool 文案。以上均不代表生产配置或发布授权；本轮未检查生产配置。

### 2.2 当前实际调用链

| 阶段 | 当前实现及位置 | 与证据的关系 |
|---|---|---|
| Agent Tool | 单一 `office` facade schema/入口：[`office_mapping_tools.py:1535-1605`](../../mymodules/office_engine_m2/models/office_mapping_tools.py)；Thread Tool Loop：[`llm_thread.py:111-210, 582-650`](../../mymodules/office_engine_m2/models/llm_thread.py) | CC-07 HVR 实际经过 Discuss Agent Tool；M1 历史 tools 保持兼容 |
| 数据读取 | 现有 `odoo_record_retriever`：[`llm_tool_record_retriever.py:11-19`](../../mymodules/odoo-llm/llm_tool/models/llm_tool_record_retriever.py)；M2 Thread 绑定：[`llm_thread.py:111-174`](../../mymodules/office_engine_m2/models/llm_thread.py) | 8091 人工 UAT 多轮读取；CB-05 两阶段自动模拟及 Retriever ACL/分页测试 |
| Provider 调度 | 受信进程配置及 Thread Provider：[`edit_orchestrator.py:44-81, 871-`](../../mymodules/office_engine_m2/services/edit_orchestrator.py)；Responses Adapter：[`responses_adapter.py:130-360`](../../mymodules/odoo-llm/llm_openai/services/responses_adapter.py) | 8092 V4/V5 真实 Provider 证据；Adapter 28 项隔离测试 |
| 候选验证 | 服务端 Candidate 绑定：[`candidate_validator.py:29-180`](../../mymodules/office_engine_m2/services/candidate_validator.py)；OOXML/文件验证：[`office_verify/security.py:49-175, 231-427`](../../mymodules/office_verify/security.py)、[`verify.py:735-`](../../mymodules/office_verify/verify.py) | 34 项 office_verify 测试、Odoo Validator tests 与真实候选文件回读 |
| 版本及用户决定 | 首次/后续 Candidate、Accept/Reject：[`workbook_version_service.py:636-790, 1419-1490`](../../mymodules/office_engine_m2/services/workbook_version_service.py) | 实际 V1→V3、V4/V5、Reject 和 Current/Revision 读回 |
| Finalize / 下载 | 接受版本正式交付：[`workbook_version_service.py:1113-`](../../mymodules/office_engine_m2/services/workbook_version_service.py)、[`render_bridge.py:133-`](../../mymodules/office_engine_m2/services/render_bridge.py) | Discuss 附件、下载、独立 SHA/XLSX 回读及失败恢复测试 |

## 3. 原计划逐项证据映射

状态定义：`COVERED` 表示该计划行为已由适用于当前工作区的真实测试或实际文件证据证明；`PARTIAL` 表示行为有证据但仍有明确缺口；`GAP` 表示没有适用证据；`SUPERSEDED` 表示后续获批设计已替换该旧要求；`NOT APPLICABLE` 表示不适用于当前范围。处置含义：`REUSE` 复用已有证据；`VERIFY` 定向核验；`ADD TEST` 补窄测试；`DEFER` 后续明确范围；`NO ACTION` 不新增工作。

| ID | 原计划条款 | 当前技术基线 | 既有证据 | 证据适用性 | 覆盖状态 | 剩余缺口 | CC-08 处置 |
|---|---|---|---|---|---|---|---|
| IR-01 | §10.A M1 首轮上传、ORM 取数、Mapping、动态行、M1 V1 预览，作为整体 M1 路径 | M1 仍由 Mapping/RenderBridge/Office Core 提供；Route B 首次内容生产通过 `office(edit)` 生成 Initial Candidate，不以 M1 Mapping 为前置 | `ATR-RUN-042` 的 236-test 回归包含 `test_native_chat_integration`、`test_xlsx_row_expansion`、RenderBridge、Document Request 等；既有 M1 接受记录保留；CC-07 UAT 证明 Route B 首轮 Candidate | 当前回归运行在 Route B 修改后的工作区；CC-07 将 M1 定义为兼容路径，不是 Route B 生成路径 | **SUPERSEDED**（仅旧计划的“Route B 必须先经 M1”解释） | M1 自身兼容性由 IR-11/TM-07 覆盖；不重做完整 M1 UI 流程 | `REUSE` |
| IR-02 | §10.B 真实 Provider 编辑、Candidate 及 V1→V2 | Responses Adapter → Candidate Validator → Version Service；首次 Candidate Accept 后登记 V1，后续从 Accepted Current 输入 | 8091 UAT Version 3096/3097/3098；8092 HVR Candidate 3016/3017；真实 Provider Response/文件及 SHA 见 HVR 报告 | Provider/HVR、候选字节、服务端版本链均有直接证据 | **COVERED** | 无需重做完整 Provider 流程 | `REUSE` |
| IR-03 | §10.C 连续编辑，值、格式、排序或结构操作及版本一致性 | Current 字节为下一轮输入；本地记录可观察差异，未知特性保留 `PARTIALLY_VERIFIED` | 8091 三轮连续内容/列结构修改；8092 V4 新工作表、V5 表头改名；父子 SHA、Accept/Reject、Finalize 均有证据 | 真实编辑证明值与结构变化；未发现真实 Provider 对常见 cell style/number format 作出编辑并独立回读的证据 | **PARTIAL** | 原计划显式要求格式编辑；表头文字改名不等于样式或数字格式修改 | `ADD TEST`：一次中性 XLSX 常见样式修改真实 Provider 验证 |
| IR-04 | §10.D 同 Thread 再次查询授权 Odoo 数据，并应用到当前 Excel | 独立 Retriever 以当前用户 ORM 调用；Office 将本轮 Retriever 结果交给真实 Provider | CC-05 `test_automated_user_simulation_two_contact_reads_and_formal_accepts`；8091 人工 UAT 三轮取数；Native Chat 的 ACL、limit、稳定分页测试 | 重复独立查询、同一联系人 ID、地址/国家关系及结果落入后续 Candidate 已覆盖 | **PARTIAL** | 未证明同一记录在两次查询之间改变后，第二次读取与 Candidate 均使用新值；撤权场景列 IR-09 | `ADD TEST`：事务内合成记录更新后重新读取，并断言新值进入后续编辑输入 |
| IR-05 | §10.E 用户确认、Candidate 验证、Accept/Reject、Finalize、附件和下载 | Candidate/Receipt 与 Current 分离；Accept/Reject 经受控入口；Finalize 交付 Accepted Current | `HVR-RUN-010` 3096→3098；`ROUTE-B-SIMPLIFICATION-HVR-REPORT` 3016→3018、拒绝和最终下载；ATR Finalize/Store 测试 | 人工 Discuss 和 Codex UI 各自有真实证据；XLSX/ZIP/SHA 已独立读回 | **COVERED** | 无需再次组织完整人工业务流程 | `REUSE` |
| IR-06 | §10.F Provider timeout / 未知执行状态恢复 | Adapter 对连接/超时返回 `indeterminate` 且不自动重试；Orchestrator 在无 Candidate 时不推进 Current | `test_responses_adapter.py` timeout/connection cases；`test_edit_orchestration.py::test_provider_failure_and_dispatch_disabled_leave_current_unchanged`；ATR-RUN-047 | Mock/Contract 足以验证不确定状态与版本保护；真实超时不应人为制造 | **COVERED** | 无真实 timeout 请求；不影响错误分类/Current 不推进的确定性测试结论 | `REUSE` |
| IR-07 | §10.F Candidate XLSX 损坏恢复 | Adapter 容器检查与 Candidate Validator 文件安全/验证分层 | Adapter invalid/corrupt XLSX cases；`test_candidate_validator.py::test_malformed_candidate_registers_failed_receipt_and_keeps_parent_current`；office_verify 34 项 | 相关回归在当前代码工作区执行；失败候选不推进 Current 有断言 | **COVERED** | 无 | `REUSE` |
| IR-08 | §10.F Validator 失败保护 last-valid | typed Receipt 绑定 Candidate/输入；Failed 不可接受、版本指针不动 | Candidate Validator / Version State TransactionCase；`test_failed_receipt_and_attachment_write_do_not_mutate_last_valid`；真实拒绝/失败证据 | Odoo TransactionCase 与实际 Reject/Current 读回互补 | **COVERED** | 无 | `REUSE` |
| IR-09 | §10.F 权限撤销恢复 | Retriever 与 Version Service 每次按认证用户、Thread/Session/附件做权限控制 | `test_retrieve_rejects_a_user_who_does_not_own_the_thread`；`test_owner_only_version_and_attachment_access`；cross-company 和 current-user ACL tests | 证明初始无权时拒绝，不证明两轮操作之间撤销后再读时不会沿用旧授权结果 | **PARTIAL** | 撤销权限后第二次 Retriever 调用的具体结果、Provider 未被调用及 Current 不变没有专门断言 | `ADD TEST`：权限撤销后重试第二次读，断言无数据/Provider/Candidate/Current 副作用 |
| IR-10 | §10.F 附件发布失败恢复 | Finalize/Thread Store 返回结构化失败，可重试且复用幂等交付 | `test_m1_delivery_exception_returns_retryable_failure_and_preserves_preview`、`test_finalize_reports_generated_artifact_when_chat_delivery_is_pending`、`test_finalize_store_failure_updates_tool_result_and_live_message`；成功下载 HVR | 服务失败路径和实际成功交付均有适用证据 | **COVERED** | 无 | `REUSE` |
| IR-11 | §10.G M1 Skills、Mappings、权限和既有功能回归 | M1 tool、Mapping、Skill、RenderBridge、Document Request、附件/ACL 与 Route B 并存 | ATR-RUN-042 的 236 `Starting Test` 含 `TestPrivateOfficeExportSkill`、Native Chat、RenderBridge、Document Request；`tests.result` 0 failure/error | 完整 Odoo suite 在相关 Route B 源码变更后运行；历史 M1 专项证据作为行为基线保留 | **COVERED** | 不需要再跑整套 M1 或重做 M1 UI HVR；若 CC-08 代码变更影响这些文件，再按影响运行相关回归 | `REUSE` |
| TM-01 | §11 Chat Completions 兼容、Responses 文件收发、Usage/清理 | 原 Chat Completions 路径并存；Responses Adapter 独立 | `ATR-RUN-047` 28 passed，含非流式、tool_calls、streaming、Client 工厂；V4/V5 真实 Responses 文件输出、资源清理和用量记录 | Mock 合同覆盖普通 Chat 兼容；真实 Provider HVR 覆盖文件闭环 | **COVERED** | 无；真实账单金额未核实，不代表预算账单验证 | `REUSE` |
| TM-02 | §11 Version/hash/parent/current/last-valid | `workbook_version_service.py` 的初始/后续 Candidate、接受和 Finalize | 8091 3096→3097→3098；8092 3016→3017→3018；输入 SHA 等于父输出 SHA；Reject 保持 Current | 真实数据库状态与输出/下载字节已核对 | **COVERED** | 无；分模块 `tests.stats` 差异单独列为非阻断证据说明 | `REUSE` |
| TM-03 | §11 安全、结构及实际差异 | `office_verify/security.py` 与 `verify.py`；能力状态和单文件结果分开 | 34 office_verify tests；Candidate malformed/valid differences；真实普通 XLSX 输出 ZIP/openpyxl 回读 | 普通 XLSX 与硬安全拒绝有证据；复杂 Excel 保真不由文件可打开推断 | **PARTIAL** | 图表、Pivot、宏/外链、嵌入对象、复杂公式及所有样式组合未完整实测 | `DEFER`：按 TDD 特性矩阵另行明确范围，不纳入 CC-08 必测清单 |
| TM-04 | §11 Intent/风险确认/Reject/stale | 普通请求可单次 Edit；模型风险声明与用户确认、版本/消息绑定；Accept/Reject 独立 | Orchestrator risk test、stale confirmation native-chat tests、8092 用户 Reject 3018 与 Current 读回 | 确定性边界测试和真实 Accept/Reject 均有证据；无需重建旧 Expected Effect 机制 | **COVERED** | 不重复旧 Plan/Effect 绑定方案 | `REUSE` |
| TM-05 | §11 Data Tool JSON completeness、full/incremental、类型/分页/权限 | Frozen Existing Retriever Integration：当前用户 Retriever，保持既有值/身份/分页语义 | CB-05 两阶段模拟、Retriever ACL/关系/稳定分页 tests、8091 多轮查询 | 当前业务行为有证据；旧数据 Snapshot 结构不再是现行技术基线 | **SUPERSEDED**（仅 Snapshot/full/incremental/fingerprint 契约） | 数据更新后再次查询的 freshness 已列 IR-04；无需新增快照能力 | `REUSE`：只补 IR-04 窄场景 |
| TM-06 | §11 Preview/Finalize/附件卡片/timeout 恢复 | Finalize Store、附件权限、幂等重试和下载服务 | CC-07 8091/8092 HVR；Native Chat/RenderBridge/Workbook Version State tests | 实际附件卡、下载 SHA、服务失败/重试路径均有证据 | **COVERED** | 无 | `REUSE` |
| TM-07 | §11 整体闭环和首轮兼容回归 | `office(edit)` Route B + 独立 Retriever；M1 测试套件仍存在 | CC-07 真实三轮 UAT；真实 Provider V4/V5/Reject/Finalize；ATR-RUN-042 全量 Odoo 回归 | 当前普通 XLSX 路径有 UI/业务/文件证据；M1 通过同轮回归 | **COVERED** | 不重跑完整多轮业务流程 | `REUSE` |

### 3.1 覆盖汇总

18 项映射：`COVERED=12`，`PARTIAL=4`，`SUPERSEDED=2`，`GAP=0`，`NOT APPLICABLE=0`。`PARTIAL` 中 3 项进入 CC-08 窄验证（格式、数据刷新、撤权）；复杂特性矩阵为明确的 `DEFER`，不作为当前 CC-08 阻断项。

## 4. 已完成且必须复用的验收

1. **8092 真实 Provider/UI HVR**：V4 Candidate 3016 接受后 Revision 4；V5 Candidate 3017 以 V4 输出 SHA 为输入，接受后 Revision 5；Candidate 3018 Reject 后 Current/Last Valid 仍为 3017、Revision 5；Finalize 附件卡下载并通过 SHA/ZIP/XLSX 回读。详见 [Route B HVR 报告](evidence/CB-M2-CB-07/ROUTE-B-SIMPLIFICATION-HVR-REPORT-2026-11-11.md) 和其 Candidate/Finalize XLSX。
2. **8091 真实人工 UAT**：同一 Discuss Thread 真实用户完成姓名/电话/邮件、地址、国家三轮编辑；每轮 Candidate、Accept、Finalize。Version 3096→3097→3098；Current/Last Valid=3098，Revision=3；输出附件 SHA 和父子输入/输出 SHA 已核对。详见 [HVR-RUN-010](evidence/CB-M2-CB-07/HVR-RUN-010-8091-human-uat-20261111.md)。该报告明确区分 owner-reported 人工操作与 ORM/字节旁证，不声称存在截图录像。
3. **自动化回归**：`ATR-RUN-042` 的 `tests.result` 是 236 tests、0 failed、0 errors，日志含 236 `Starting Test`；`tests.stats` 报 M2=252、M1=28（合计 280），原因未解释。最终测试结果及开始记录一致，未发现计划目标类未执行的证据，因此计数差异不构成已证明的功能测试失败，也不将 280 计为通过数。
4. **独立包测试**：`office_verify` 34 passed；Responses Adapter/Chat Completions 兼容 28 passed。Adapter 最终日志时间晚于全量 Odoo 回归；未把隔离 Adapter 测试冒充 Odoo 或 UI 测试。

## 5. CC-08 最小范围

### In Scope

- 三项 IR-03、IR-04、IR-09 定向验证及其 IHR/ATR 记录。
- 复用现有 `office`、Retriever、Responses Adapter、Candidate Validator、Version Service 和 Finalize，不改变接口或验证语义。
- 真实 Provider 仅用于一个中性 XLSX 的常见格式编辑测试；输入仅含合成数据。必须使用当前受信配置和现有 Candidate/Accept 入口，记录调用 ID（可取得时）、输入/输出 SHA、验证等级和回读结果。
- 数据 freshness 与撤权测试使用事务隔离的合成 Odoo 联系人和现有 Retriever/Tool 路径，不向外部 Provider 发送数据。不得使用真实业务记录。
- 追加代码与证据基线清单：HEAD、dirty/clean 状态、被执行源码 SHA、Addon、测试命令、数据库身份、Provider 测试环境开关（不记凭据）。

### Out of Scope

- 再次执行 CC-07 完整 8091 人工 HVR、V1→V3 联系人流程、V4/V5 全链路或整个 M1 UI 流程。
- 新建 Snapshot、CDC、incremental、Fingerprint、第二查询框架或权限系统。
- 完整 Excel 保真产品；不把图表、Pivot、VBA、外链、嵌入对象、大型工作簿等未验证特性全部纳入本 CC。
- 删除或重写 M1 Mapping/Skills、重构 Route B、修改 CC-01～CC-07 已接受实现。
- 修改生产配置、生产数据、生产 Provider 策略或进行部署。
- 修复与三项目标无关的问题。若验证发现需要产品代码修改，停止该修复并提交精确缺陷与最小改动供单独授权；不在本 CC 草案中预先批准重构。

## 6. CC-08 验证矩阵

| 场景 | 层级 | 最小步骤 | PASS 判据 | 证据 |
|---|---|---|---|---|
| CB08-T1 常见样式编辑 | 真实 Responses Adapter + 合成 XLSX + Odoo Candidate/Accept 服务 | 用普通多单元格合成 XLSX，输入可为测试 Thread 的原始上传文件并走现有首次 Candidate 流程，或为既有 Accepted Current；两种来源均走当前合法服务路径。指令修改一项常见 cell style 或 number format；产生 Candidate，通过既有 Validator；经既有 `office(action="accept")` 入口接受；独立读回 | 不要求预先存在 Accepted Current。文件有效；目标格式实际变化；非目标值/公式未意外变化；Candidate SHA 与附件字节一致；Accept 后按来源正确登记/推进 V1 或后续 Current、Last Valid、Revision；验证等级不被提升 | 脱敏请求记录、来源类型、Candidate/Current IDs、输入/输出 SHA、独立 XLSX 回读、实际配置来源 |
| CB08-T2 数据 freshness | Odoo TransactionCase / existing Tool integration | 创建合成联系人；同一 Thread 第一次 Retriever 查询；仅修改测试 fixture；第二次对同一 ID 调 Retriever，再走测试 Adapter/现有 edit 接缝 | 第二次结果反映 fixture 新值；无缓存旧值；传给下一轮编辑的查询结果有该新值；业务记录测试事务回滚；未调用真实 Provider | 两次查询参数/脱敏结果摘要、record ID、候选父子 SHA、事务回滚结果 |
| CB08-T3 撤权后重读 | Odoo TransactionCase / existing Tool integration | 合法用户首次读取并建立合成工作簿上下文；通过测试 ACL/Record Rule fixture 撤销其对目标记录的读取权限；同一 Thread 再请求相同记录 | 按 Odoo 权限语义，第二次读取可以返回拒绝，也可以在 Record Rule 过滤下返回空结果；两种结果均不得包含受限记录字段或复用第一次读取缓存。不得调用 Provider、创建 Candidate 或改变 Current/Last Valid/Revision；不得回退到 sudo 或其他用户 | 撤权前后 user/groups/rule fixture 摘要、Tool 结果中的可见记录 ID/字段集合、Provider mock 调用数、Candidate 数及版本指针前后快照 |
| CB08-T4 证据基线封存 | 文档/只读记录 | 测试前后记录上述实际文件的工作树摘要和 SHA | 能将每项运行证据对应到一次明确的代码/配置工作区；不包含凭据、Cookie 或客户数据 | IHR/ATR 的执行元数据表 |

没有执行的场景必须记为 `NOT RUN`。T1 若因现有受信 Provider 配置/授权不可用而未执行，记 `BLOCKED`，不改用 Mock 宣称通过；T2/T3 的 Mock/TransactionCase 只证明其对应层级，不替代 T1 的真实 Provider 证据。

## 7. Superseded 旧要求

以下要求不得恢复为 CC-08 Gate：

| 旧要求 | 当前处置 | 依据 |
|---|---|---|
| Route B 普通编辑必须分成两次 `Plan → Edit`，或先独立调用 Inspection Provider | `SUPERSEDED BY CC-07`；当前普通编辑为单次 `office(action="edit")`，服务端解析实际上传文件/Accepted Current | CC-07 检查简化报告 RB-01；当前 `office` schema 和 Edit Orchestrator |
| LLM 必须预先提交精确 Expected Effect 坐标、Inspection ID | `SUPERSEDED BY CC-07`；不要求用户提供 Sheet/单元格坐标，实际差异由本地记录 | CC-07 RB-02/RB-03；最终 HVR |
| LLM 传入 effect_digest、SHA、Revision，或客户端计划重放/重复校验 | `SUPERSEDED BY CC-07`；文件 SHA、Revision 和 Candidate 来源由服务端绑定；不恢复模型参数契约 | CC-07 RB-02；当前 Orchestrator/Version Service |
| Candidate 的实际变化超出模型预先声明范围即拒绝 | `SUPERSEDED BY CC-07`；安全/完整性硬失败仍阻断，未完整验证但有效的工作簿可标 `PARTIALLY_VERIFIED` 并供用户决定 | CC-07 RB-03/RB-04；Candidate Validation Receipt |
| 第一次填写必须由 M1 Mapping/repeat_rows 主导，或按简单/复杂模板切换 Route | `SUPERSEDED BY TDD V2.1.0 + CC-07`；M1 仅作为保留的兼容能力，不是 Route B 内容生产前置 | TDD §0.1/§1.3；CC-07 HVR |
| Data Tool Snapshot、snapshot ID、full/incremental、CDC、query/content fingerprint、跨页点时快照 | `SUPERSEDED BY CC-05 Existing Retriever Integration`；复用每次当前用户 Retriever 查询，不新增快照平台 | CC-05 v0.2.2、TDD V2.1.0 §2.3 |
| 所有未验证 Excel 特性必须在本 CC 全部实现或验证 | 不恢复为范围；按 TDD §6.4 能力矩阵与 §11.4 逐项分类。普通 XLSX 本 CC 不承诺图表/Pivot/VBA/外链等完整保真 | TDD §6.4、§11.4；CC-07 关闭标准 |

## 8. 判定、证据与关闭

### PASS / FAIL / BLOCKED

- **PASS**：CB08-T1～T4 均有各自层级的实际执行证据；行为断言通过；未改动既有安全和版本服务语义。
- **FAIL**：目标场景出现错误数据、旧值复用、未授权 Provider 调用、权限绕过、损坏文件被接受、Candidate/Current 错误推进或 Candidate/Current/SHA 不一致。不得通过弱化断言或把 `FAILED` 改成 `PARTIALLY_VERIFIED` 规避。
- **BLOCKED**：测试环境、非生产 Provider 调度权限或所需 ORM 权限条件不可用。记录具体缺项与已完成的独立场景，不推导其余场景通过。
- 测试统计差异原因未找到时，继续标 `UNEXPLAINED`；除非原始 `Starting Test`/最终 `tests.result` 出现遗漏或失败，否则不要求仅为统计数字重跑全套测试。

### IHR / ATR / HVR / FR

- **IHR**：固定实际代码/配置基线、证据适用性、三项验证范围；记录配置文件值与进程内实际值的区别，并注明 Tool 文案与测试环境配置的环境语义；不得覆盖 CC-07 历史记录。
- **ATR**：仅记录本 CC 定向测试、必要的受影响回归和真实执行数；Mock、Odoo ORM、真实 Provider 分层写明。
- **HVR**：只记录 CB08-T1 的 targeted provider/file validation（若通过现有 UI 执行则注明 UI）；不重演三轮联系人 UAT，不称为完整人工 HVR。
- **FR**：对 18 项原计划映射逐项给出结果，保留计数差异、`PARTIALLY_VERIFIED` 和复杂特性边界；列出生产外发/发布仍需单独决策。

### 关闭条件与发布边界

1. 三项真实缺口逐项标为 `PASS`、`FAIL`、`BLOCKED` 或 `NOT RUN`。如负责人批准将某项移出范围，必须记录移除原因、未验证风险、后续责任人/责任批次及最终验收处置；该项保持 `DEFERRED`，不得计作 PASS。最终关闭结论必须准确说明哪些原目标未验证；有任何目标项被移除或未通过时，不得报告完整 `CLOSED — PASS`，只能使用明确体现 deferred/partial 的关闭状态并由负责人接受。
2. CC-07 已有 HVR/M1 回归不重跑、不重标；有直接受影响的代码变更时只补运行受影响回归。
3. 证据可区分 owner-reported Human UAT、真实 Provider、Odoo TransactionCase、Mock 和独立文件回读。
4. 统计差异原因可继续保留 `UNEXPLAINED`，但实际通过数只采用 `tests.result` 与对应的逐项测试日志；不得按模块统计合计重复计数。
5. CC-08 关闭仅表示本契约定义的集成证据完成；不宣称复杂 Excel 全保真，不改变 `PARTIALLY_VERIFIED`，不批准生产部署、生产 Provider 外发或生产 Release。

## 9. Remaining Risks / Non-Blocking Items

- `PARTIALLY_VERIFIED` 仍表示有功能/保真事项未确定；用户 Accept/Finalize 不提升该等级。
- CC-07 证明普通工作簿多轮编辑、格式/结构结果中的实际已测子集；TDD 未验证的图表、数据透视表、VBA/外部链接、嵌入对象、大型工作簿等仍按特性矩阵处理。
- Odoo `tests.stats` 252+28 与 `tests.result` 236 的统计口径差异原因仍未解释；目前没有测试失败、错误或遗漏目标测试的证据。
- `Browser HttpCase` 缺少 `websocket-client` 的历史 skip 不阻断：真实 8091/8092 Discuss UI HVR 已覆盖用户流程；不要求在 CC-08 重复安装依赖或重做完整浏览器验收。
- 项目测试配置 `odoo.conf` 的 Provider 参数仅适用于获批测试实例；生产配置、数据外发留存政策及正式发布决定不属于本 CC。

## 10. Owner Decisions / Coding Authorization Gate

1. 负责人已于 2026-11-11 批准冻结并进入实施。本次授权限于 CB08-T1～T4 规定的定向验证、合成夹具、必要测试代码和证据交付；不扩展为产品重构或生产发布。
2. 若验证发现必须修改产品代码才能通过目标场景，先记录直接根因、证据和最小改动；停止该产品代码修改，另行取得授权。测试夹具、定向测试及 IHR/ATR/HVR/FR 属本轮范围。
3. 完整最终集成业务人工验收不纳入 CC-08，由后续最终集成验收安排；CC-08 不重复组织 CC-07 已完成的三轮联系人人工 UAT。

## 11. 变更记录

| 版本 | 日期 | 状态 | 说明 |
|---|---|---|---|
| v0.1 | 2026-11-11 | **DRAFT — NOT AUTHORIZED** | 基于 Implementation Plan 与 CC-07 证据盘点形成；仅起草，未编码、未运行测试、未调用 Provider |
| v0.1 | 2026-11-11 | **FROZEN — IMPLEMENTATION AUTHORIZED** | 负责人批准冻结并进入实施；执行范围保持为本契约 CB08-T1～T4 |
