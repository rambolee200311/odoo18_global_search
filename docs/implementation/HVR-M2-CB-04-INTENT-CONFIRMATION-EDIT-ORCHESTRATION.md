# HVR — CC-M2-CB-04 Intent / Confirmation / Edit Orchestration

## 0. 文档治理

| 项目 | 内容 |
|---|---|
| 文档状态 | **DRAFT — PENDING REAL HUMAN VALIDATION** |
| 验收范围 | CC-M2-CB-04 的 5 个自然语言编辑、确认和连续编辑场景；仅覆盖当前 CC 的本地编排能力 |
| 权威契约 | `docs/implementation/CC-M2-CB-04_Intent_Confirmation_Edit_Orchestration_v0.2.md` |
| 实施记录 | `docs/implementation/IHR-M2-CB-04.md` |
| 自动化记录 | `docs/implementation/ATR-M2-CB-04.md` |
| 当前运行基线 | `main` / `f9801fca76f7c248a9cc823c583138ab0191b978` + 未提交的 CC-04 工作区修改；人工运行时须重新记录实际基线 |
| 当前正式人工结果 | 0 PASS / 0 FAIL / 0 BLOCKED / **5 PENDING_MANUAL_VALIDATION** |
| 浏览器预演结果 | 历史首次预演与 2026-11-09 后续合成 UI 模拟见 §1.3/§1.4；whole-workbook clear 实际未生效。v3.0 focused TransactionCase 和文件回读见 §1.5；2026-11-09 后续自动化修复证据见 §6。Playwright 场景未运行；正式人工结果仍为 0 PASS / 0 FAIL / 0 BLOCKED / 5 PENDING。 |
| 人工验证者 / 执行时间 | 尚未执行，留待真实验证人填写 |

本文件将代码和自动化测试用于预演五个场景的预计分支，只作为模拟分析。随后使用 Odoo 内置浏览器进行了两次合成数据 UI 预演；这不是人工验证，不能计入 HVR PASS。人工验证者与正式人工结果仍留空。

## 1. 模拟边界与当前前置条件

### 1.1 可用的模拟证据

| 场景 | 模拟依据 | 模拟结论 |
|---|---|---|
| 1. 明确修改 | v3.0 `test_explicit_edit_uses_current_version_and_accepts_only_after_cb03_receipt`、`test_explicit_header_replacement_has_no_extra_risk_confirmation`，以及 `edit_orchestrator.py::execute_planned_edit` | 明确指令不因原值非空、表头或 CB-03 的风险标签触发本地业务确认；候选仍通过独立的 `candidate_review_required` 结果交给用户接受/拒绝。TransactionCase 覆盖已有表头修改、Candidate 回读及 VERIFIED 接受；内置浏览器亦有 §1.4 合成模拟。正式人工及 Playwright 验证仍未完成。 |
| 2. 模糊修改 | v3.0 `test_ambiguous_intent_requests_clarification_without_candidate`、`edit_orchestrator.py::_build_plan`；内置浏览器 Thread `llm.thread_15101` 及后续模拟 | 首次浏览器调用因无已接受版本报错，后续内置浏览器模拟中模型先澄清且未发编辑调用；v3.0 TransactionCase 覆盖无 Candidate 澄清。Playwright 未运行，结论仅为自动化/内置浏览器模拟支持。 |
| 3. 覆盖风险 | `test_confirmed_broad_scope_runs_only_after_exact_reply_and_keeps_receipt_bound` | 合成的多单元格范围在计划阶段要求确认，确认前没有 Provider 调用且 Current 不变。测试不是“清空所有现有数据”的精确操作；该用户场景为 **PARTIAL**。 |
| 4. 用户确认 | v3.0 `test_llm_confirmation_request_gates_even_an_explicit_single_cell_edit`、`test_confirmation_decision_cannot_be_changed_between_plan_and_edit`；`intent_contract.py::confirmation_receipt_id` | 模拟以真实 Thread 用户消息、当前用户及 Effect/revision 绑定确认；未确认、拒绝或绑定变化不会执行 Candidate。全工作簿清空的旧浏览器场景确认后候选未实际清空，见 §1.4。**MOCK / TRANSACTIONCASE SUPPORT ONLY**。 |
| 5. 连续编辑 | `test_two_successive_edits_use_successive_accepted_workbook_versions` | 模拟 V1→V2→V3：第二轮以 V2 附件字节为输入，且 V3 保留第一轮修改。**AUTOMATED SIMULATION SUPPORT**，不是人工聊天验证。 |

证据文件：

- 专项 Odoo 运行：`docs/implementation/evidence/CB-M2-CB-04/odoo-orchestration-run6.log`、`odoo-orchestration-run7.log`。
- 全量 Odoo 运行：`docs/implementation/evidence/CB-M2-CB-04/odoo-final-regression.log`。
- 结果和范围说明：`docs/implementation/IHR-M2-CB-04.md`、`docs/implementation/ATR-M2-CB-04.md`。
- 对应实现/测试：`mymodules/office_engine_m2/services/edit_orchestrator.py`、`intent_contract.py`、`tests/test_edit_orchestration.py`、`tests/test_intent_contract.py`。

### 1.2 真实人工验证的前置条件

- 使用仅含合成数据的 XLSX，并通过当前 Odoo 用户的正常 Thread 操作。**仅将原始 XLSX 附加到聊天不等于建立当前版本。**必须先经受支持的流程登记并接受 V1，且能核验 current/last-valid、Document Revision、附件字节和 SHA-256。
- 需要能够在受批准的环境中生成并下载真实 Candidate。
- CC-04 当前公开 Facade 的 `EXTERNAL_PROVIDER_DISPATCH_ENABLED` 为 `False`，IHR 记录外部 Candidate 处理授权 Gate 仍未开放。按用户要求，本轮仅通过 Odoo 内置聊天 UI 向已配置模型发送了上述合成测试附件及两条场景指令；这没有启用 Responses/Code Interpreter Candidate 编辑路径，也没有产生 Candidate。不得为本 HVR 打开该 Gate、绕过 Facade 或更改部署配置。
- Gate 满足且人工执行获准后，记录 Thread、输入/输出版本 SHA、工具结果、候选/回执/附件 ID；如无法取得下载文件，则该次不得登记为 PASS。

本轮内置浏览器预演确认了原始附件不能代替已接受 V1：工具返回“当前没有可操作的已接受、版本化工作簿”。因此本轮未尝试清空、确认、连续编辑或任何正式文件推进。

### 1.3 内置浏览器预演记录（非人工验收）

| 项目 | 实际记录 |
|---|---|
| 时间 | 2026-11-09，Odoo UI 显示 10:17 AM 与 10:40 AM（本地界面时间） |
| 环境 | Odoo `http://127.0.0.1:8091`，数据库徽标 `odoo18ce`，内置浏览器，用户 `Mitchell Admin`，模型 `gpt-5.6-luna` |
| Thread | `llm.thread_15101`（界面标题 `Chat 11/9/2026, 10:14:04 AM`） |
| 合成附件 | `hvr-cb04-synthetic.xlsx`，SHA-256 `02c0e438a5a9c3e28187431f74ab9136ec6656281676f354e43696d41cd22a62` |
| SCN-001 输入 | `把 A1 的表头改成产品编码` |
| SCN-001 调用与结果 | `office` tool call `call_9GVnUf7eDNHHBnhku4UcJHAW`；工具报错，模型回复当前没有可操作的已接受、版本化工作簿，并要求先上传并接受工作簿。未观察到 Candidate、预览或下载结果。状态：`BLOCKED_PRECONDITION`；未验证表头编辑行为。 |
| SCN-002 输入 | `帮我调整一下表格` |
| SCN-002 调用与结果 | `office` tool call `call_or0cWTmTwUQ0cBk8kM1IcGY4`；工具同样报错。模型随后要求先上传并接受工作簿，并给出具体修改示例。没有 Candidate、预览或下载结果。状态：`PARTIAL`；澄清回复有实际 UI 证据，但工具在澄清前已被调用，且缺少有效 V1。 |
| 截图 | 本轮内置浏览器画面已通过 CUA 截取并显示在会话工具输出中；未保存为仓库截图文件，故不作为可独立归档的 HVR 截图证据。 |
| 副作用边界 | 上传了仅含合成值的测试文件并发送上述两条测试消息；没有取得编辑候选或正式版本接受结果。未检查或声称任何其他 Odoo 业务数据状态。 |

### 1.4 后续内置浏览器模拟记录（非人工验收）

本节追加 2026-11-09 的后续预演事实，不覆盖 §1.3 的历史失败记录。正式人工填写栏仍为空，五项状态仍为 `PENDING_MANUAL_VALIDATION`。

| 项目 | 实际记录 |
|---|---|
| 时间 / 环境 | 2026-11-09，Odoo UI 本地时间约 4:23–4:28 PM；专用 Odoo 8092 浏览器模拟进程，数据库 `odoo18ce`，用户 `Mitchell Admin`，Thread `llm.thread_15154`，模型界面显示 `gpt-5.6-luna`。 |
| 数据与编辑边界 | 使用合成 `Inventory`、`Notes` 工作簿。Candidate 编辑由专用进程内 `CC-04 browser simulation adapter` 产生，未调用 Responses API / Hosted Code Interpreter 处理文件；此事实不等于未调用聊天模型服务。未使用真实业务附件。 |
| 场景 1 — 明确表头修改 | 输入“把 A1 的表头修改为产品编码。”。`office` 返回 `VERIFIED`，Candidate 687 从父版本 680 成为 `accepted_current`，授权类型 `explicit_intent`，Document Revision 变为 2。工具回执 SHA `f907c8cc0930c4ad689a9c0c4db4960671cec0faad3f04aa19e55184b930eb51`；输入 SHA `0f2f5ecc31a92831006495737f50d43dd44bed60ea73b952921a8dfc88eb5028`，候选 SHA `82607bc498439cebe5a5b0cfd94a1ca182726b3127ad71d10d3b8922f4c8f092`。ORM/openpyxl 回读仅发现 `Inventory!A1` 从 `Legacy Header` 改为 `产品编码`，其他值、公式、样式和工作表结构保持。模拟结论：`PASS`；不是人工验证。 |
| 场景 2 — 模糊修改 | 输入“帮我调整一下表格。”。模型要求说明工作表/单元格或范围、目标值/表头/公式、格式或结构要求；未出现后续 `office` 编辑调用。下一计划仍绑定版本 687，说明此前 Current 未变化。模拟结论：`PASS`（澄清且不编辑）；不是人工验证。 |
| 场景 3 — 全工作簿清空风险计划 | 输入“把现有数据全部清空”后，模型先区分整个工作簿和当前 `Inventory` 工作表；用户选择整个工作簿。`office` 调用 `call_2EJRvGgErDU3NSOQX6g72Mja` 返回 `status=confirmation_required`、`operation_status=plan_ready`、`operation_executed=false`，绑定父版本 687 及其文件 SHA，说明清空所有工作表单元格值与公式、保留工作表/行列结构及格式。确认前未生成 Candidate。模拟结论：`PASS`（范围澄清、风险说明和确认门）；不是人工验证。 |
| 场景 4 — 确认后精确执行 | 用户对上述计划回复“确认”。`office` 调用 `call_rPr95SZUsMYFbTY9x0K2abib` 产生 Candidate 688，但结果为 `PARTIALLY_VERIFIED`，回执 SHA `b0e70cc901d0d76f4fac84b6adb4e22321a0d5b0e65cc637c72faf4c3ae13e47`。Current/Last Valid 仍为 687、Document Revision 仍为 2。独立 ORM/openpyxl 回读核对 Candidate SHA `77cffdefa4da4d9a7e7c6d419d1e7e2fb175b5442371b3ea955fb11653e0fb36` 与附件一致、ZIP 完整；与父版本相比单元格差异数为 0，清空未实际发生。模型如实报告未通过验证、Current 未改变。模拟结论：`PARTIAL / FUNCTIONAL FAIL; SAFETY GATE HELD`。该失败保留，不以确认成功或候选可读替代目标完成。 |
| 场景 5 — 连续编辑 | 浏览器 composer 保留了上次的“确认”文字，实际提交内容为“确认把 Inventory 工作表的 B2 修改为 15，保留其他内容。”；结构化 Intent 仅解析为 `Inventory!B2=15`。Candidate 689 以已接受版本 687 为父，`VERIFIED` 并成为 Current，Document Revision 变为 3。Receipt SHA `9a1fc6f0d068c440e8cc90f37e433ea1fd9aec5e78391524479ad7feaf2e1296`；输入 SHA `82607bc498439cebe5a5b0cfd94a1ca182726b3127ad71d10d3b8922f4c8f092`，候选 SHA `32e589004fa12e9b5907e419f58ae7b38cc9143e1c1c464300e8f38bfd505704`。独立 ORM/openpyxl 回读仅发现 B2 从数值 10 改为 15，格式/样式不变；A1 表头修改仍保留，公式及 Notes 数据不变。模拟结论：`PASS`（连续版本与效果范围）；composer 前缀作为 UI 自动化瑕疵如实记录。不是人工验证。 |
| 附件交付 | Scenario 1/5 的 `artifact_state=not_presented`、`delivery_state=not_finalized`；未执行 Finalize、浏览器下载或下载文件回读。因此本次仅验证版本接受和 Odoo 附件回读，不宣称交付/下载通过。 |
| 可复核证据 | `docs/implementation/evidence/CB-M2-CB-04/browser-simulation/browser-scenarios-2-to-5-run.md`；`browser-scenario-independent-readback.log`；`read_back_browser_scenarios.py`；场景 1 原回读 `scene-1-accepted-version-diff-detail.txt`。场景 5 浏览器截图已在 CUA 工具输出中捕获显示，但未落盘为仓库文件；不把它列作可独立归档的截图证据。 |

### 1.5 CC-04 v3.0 自动化与浏览器状态（非人工验收）

本节追加 v3.0 的真实执行证据，不覆盖前两次内置浏览器模拟。人工 HVR 的五项结果继续全部留空、保持 `PENDING_MANUAL_VALIDATION`。

| 项目 | 结果 |
|---|---|
| CC-04 专项自动化 | `v3-edit-orchestration-run5.log`：21 项 `TestEditOrchestration`，最终结果 0 failed、0 errors。另有通用目标测试 1 项通过，见 `v3-generic-target-run1.log`。 |
| 全量 Odoo 回归 | `v3-full-regression-run1.log`：239 tests，2 failed、0 errors；因此自动化全量回归未通过。两个失败分别见 IHR §6.2 / ATR §6.2，涉及 M1 Document Request 的错误绑定路径和 M1 RenderBridge 在 TransactionCase 中执行 `env.cr.commit()`。没有修改相关 M1 逻辑。 |
| 文件证据 | `v3-t01-parent.xlsx` / `v3-t01-candidate.xlsx` 与 `v3-t02-v1.xlsx`–`v3-t02-v3.xlsx` 均通过 ZIP 完整性及 `openpyxl` 回读；哈希、版本父链及结果见 `v3-t01-version-evidence.json`、`v3-t02-version-chain.json`。均为合成数据与 Mock Candidate adapter，不能代表真实 Provider。 |
| PARTIALLY_VERIFIED | 自动化确认可进入带 `verified_facts`、`model_claims`、`unverified_aspects` 的审阅结果；CB-02 当前接口不能持久化该级别的 Accept/Reject，Candidate 保持 PARTIAL，Current 不变。不得称其已接受。 |
| Playwright | **NOT RUN**。Python Playwright 已安装，但未建立它与 Codex 内置浏览器已认证会话之间的受支持绑定。未提取/更改凭据，未调用聊天模型。 |
| 内置浏览器 smoke | 专用 Odoo 8092 页面在现有登录态下加载成功；没有发送聊天指令、没有 Candidate 操作。日志 `v3-odoo-8092-playwright.log` 仅支持页面加载，不支持任何 T01–T15 浏览器 PASS。随后已停止 8092；8091 未重启。尝试边界见 `v3-playwright-attempt.md`。 |
| Provider / 正式交付 | Responses/Code Interpreter、Preview/Finalize、浏览器下载均未运行。外部处理 gate 保持关闭。 |

T01–T15 的自动化结果、边界及 CB-02 接口限制另见 [`v3-test-matrix.md`](evidence/CB-M2-CB-04/v3-test-matrix.md)。所有五项真实人工结果仍为 PENDING。

## 2. 覆盖矩阵

| 要求 | 场景 | 自动化/模拟证据 | 人工结果 | 当前状态 |
|---|---|---|---|---|
| 明确修改不重复确认，验证后接受 | HVR-SCN-001 | v3.0 TransactionCase 覆盖明确值编辑及已有表头替换；verified Candidate 通过 CB-02 接受。既有内置浏览器也有合成表头模拟，但不是 Playwright |  | `PENDING_MANUAL_VALIDATION` |
| 模糊要求先澄清 | HVR-SCN-002 | v3.0 `test_ambiguous_intent_requests_clarification_without_candidate` 通过；以前内置浏览器澄清记录见 §1.4。Playwright 未运行 |  | `PENDING_MANUAL_VALIDATION` |
| 宽范围清空先说明影响并确认 | HVR-SCN-003 | v3.0 TransactionCase 验证模型请求确认前不执行；旧内置浏览器确认前计划通过，但随后执行候选未产生清空效果（§1.4） |  | `PENDING_MANUAL_VALIDATION` |
| 仅按已确认范围执行 | HVR-SCN-004 | 历史 v3.0 首版的旧浏览器清空场景执行后实际效果为零，完整 UI 结果未通过。2026-11-09 的自动化修复现已验证 PARTIALLY_VERIFIED Candidate 可接受/拒绝且不扩大确认范围；证据见 §6。人工与 Playwright 仍未验证 |  | `PENDING_MANUAL_VALIDATION` |
| 第二轮继承首轮已接受文件 | HVR-SCN-005 | v3.0 V1→V2→V3 TransactionCase + XLSX SHA / openpyxl 回读；旧内置浏览器模拟 V2 延续也有记录。Playwright 未运行 |  | `PENDING_MANUAL_VALIDATION` |

## 3. 人工验证场景

所有场景的“实际观察”“证据”和“人工结果”均刻意留空，供真实验证者填写。不要将 §1 的模拟结果复制到这些字段作为人工证据。

### HVR-SCN-001 — 明确修改已有表头

| 字段 | 内容 |
|---|---|
| 验证目的 | 确认用户明确指定单一目标与新值后，不会被重复询问；候选经验证并获授权后成为 Current。 |
| 前置条件 | 有权访问的 Odoo 测试 Thread；含合成内容且 `A1` 已有表头文本的 XLSX；该文件已通过受支持流程登记并接受为 V1，可核对版本与 SHA；当前用户已登录；经批准的 Candidate 编辑路径可用。 |
| 操作步骤 | 1. 上传合成工作簿。 2. 输入：“把 A1 的表头改成产品编码”。 3. 观察是否出现确认提问。 4. 如生成候选，查看验证结果及 Current 版本变化。 5. 下载实际文件并独立检查 A1 及非目标内容。 |
| 预期结果 | 不重复询问；确实生成候选；验证通过后接受 Candidate；文件中 `A1=产品编码`，其他未授权内容未变。 |
| 模拟观察（非人工） | §1.3 的首次浏览器请求因无已接受版本被阻断；§1.4 的后续内置浏览器模拟将已有 `Inventory!A1` 表头改为“产品编码”，通过 `VERIFIED` Candidate 成为 Current。v3.0 TransactionCase 也覆盖明确单元格及已有表头替换；空 `risk_facts` 不会触发额外的业务风险确认，但 Candidate 仍需用户审阅/接受。**Playwright 场景未运行；人工结果仍待验证。** |
| 实际观察（人工填写） |  |
| 证据：Thread / 时间 / 版本 SHA / 下载回读 / 截图 |  |
| 人工结果 | `PENDING_MANUAL_VALIDATION` |

### HVR-SCN-002 — 模糊修改要求

| 字段 | 内容 |
|---|---|
| 验证目的 | 确认目标不明确时先向用户澄清，不自行选择修改内容。 |
| 前置条件 | 可用的测试 Thread、合成 XLSX 及已接受 V1；记录操作前 Current 版本及 SHA。 |
| 操作步骤 | 1. 上传合成工作簿。 2. 输入：“帮我调整一下表格”。 3. 查看回复与工具状态。 4. 检查是否生成 Candidate、是否改动 Current 或文件。 |
| 预期结果 | 返回 `clarification_required` 并询问需要调整的对象/目标；不发起文件编辑；Current、Last Valid 和文件 SHA 不变。 |
| 模拟观察（非人工） | §1.3 的首次请求先有无版本工具错误，之后模型给出澄清；§1.4 的后续内置浏览器模拟中模型请求了具体目标且未再调用编辑工具。v3.0 TransactionCase `test_ambiguous_intent_requests_clarification_without_candidate` 通过。Playwright 未运行；人工结果仍待验证。 |
| 实际观察（人工填写） |  |
| 证据：Thread / 时间 / 工具结果 / 前后版本 SHA / 截图 |  |
| 人工结果 | `PENDING_MANUAL_VALIDATION` |

### HVR-SCN-003 — 清空全部现有数据的覆盖风险

| 字段 | 内容 |
|---|---|
| 验证目的 | 确认宽范围清空被说明其影响范围，并在确认前不执行风险编辑。 |
| 前置条件 | 合成 XLSX 中有多处非空值，且已接受为 V1；记录清空前 Current、文件 SHA 与代表性内容；可用测试 Thread。 |
| 操作步骤 | 1. 输入：“把现有数据全部清空”。 2. 检查系统报告的目标范围、风险和确认问题。 3. 暂不回复确认，检查未产生候选、Current 未变且文件未被改写。 |
| 预期结果 | 系统明确列出它识别到的范围及清空风险；如“全部”的边界不明确，应先澄清。确认前不得执行清空。 |
| 模拟观察（非人工） | §1.4 的内置浏览器先询问“全部”的范围，再给出全工作簿影响说明并在确认前不生成 Candidate；确认后的候选实际未清空内容（见 SCN-004）。v3.0 TransactionCase 覆盖有限范围的模型确认门。Playwright 未运行；全工作簿清空效果未通过。 |
| 实际观察（人工填写） |  |
| 证据：Thread / 时间 / 影响范围 / 确认前版本 SHA / 截图 |  |
| 人工结果 | `PENDING_MANUAL_VALIDATION` |

### HVR-SCN-004 — 对明确范围确认后执行

| 字段 | 内容 |
|---|---|
| 验证目的 | 确认用户明确确认后只执行所展示的范围；确认不能扩大范围或绕过技术/权限限制。 |
| 前置条件 | 先完成 SCN-003 并取得服务端显示的具体目标范围、风险说明和预期效果；确认绑定到当前用户、Thread、文件版本与 Effect。当前没有有效待确认操作，不得单独发送“确认”以模拟通过。 |
| 操作步骤 | 1. 对 SCN-003 展示的范围回复“确认”。 2. 检查候选实际改动。 3. 下载文件并核对目标与非目标范围。 4. 核对 Candidate 的父版本和验证回执。 |
| 预期结果 | 仅执行确认所绑定的目标范围；Effect 或文件版本发生变化时旧确认失效并重新询问；越权变化不接受为 Current。 |
| 模拟观察（非人工） | TransactionCase 对明确范围证明未确认时无 Candidate 执行、确认消息绑定后调用 Adapter，且 Intent/Effect/revision 改变会使确认摘要不同。§1.4 的全工作簿清空在确认后生成 `PARTIALLY_VERIFIED` Candidate，但独立读取发现单元格变化数为零，故该浏览器目标没有完成；Current 保持不变。历史 v3.0 首版当时 CB-02 不支持 PARTIAL 持久化 Accept/Reject；该限制已由 §1.6 自动化修复覆盖。不是 Playwright/真实 Provider 验证。 |
| 实际观察（人工填写） |  |
| 证据：确认消息 / Thread / 输入输出 SHA / 回读 / 截图 |  |
| 人工结果 | `PENDING_MANUAL_VALIDATION` |

### HVR-SCN-005 — 两轮连续编辑

| 字段 | 内容 |
|---|---|
| 验证目的 | 确认第二轮以第一轮已接受版本为基线，且保留第一轮的修改。 |
| 前置条件 | 合成 XLSX，至少两个独立可编辑单元格且已接受为 V1；可用测试 Thread 和获准的 Candidate 编辑路径。 |
| 操作步骤 | 1. 上传 V1。 2. 将一个目标改为指定值并完成接受，记录 V2 SHA。 3. 在同一 Thread 要求修改另一个目标，完成接受，记录 V3 SHA。 4. 下载 V3，核对两次修改及非目标内容。 |
| 预期结果 | 第二轮输入 SHA 等于已接受 V2 的 SHA；V3 同时保留第一轮与第二轮修改；失败或拒绝的候选不改变 Current。 |
| 模拟观察（非人工） | 专项 Odoo TransactionCase 与 `v3-t02-version-chain.json` 验证 V1→V2→V3、第二轮输入 SHA 等于 V2，并独立回读 V3 保留两轮修改；§1.4 也记录过内置浏览器模拟。没有 Playwright 或真实 Provider 文件编辑。 |
| 实际观察（人工填写） |  |
| 证据：Thread / V1-V2-V3 SHA / 工具与候选 ID / 下载回读 / 截图 |  |
| 人工结果 | `PENDING_MANUAL_VALIDATION` |

## 4. Run History 与人工证据

当前没有真实人工执行记录，因此不创建正式人工 `HVR-RUN`，不登记人工 `PASS`、`FAIL` 或截图证据。§1.3 是单独标识的浏览器预演事实记录，不替代人工结果。完成真实验收后，以追加方式新增 Run，至少记载：可识别的验证者、时间、环境、当前代码基线、场景、实际观察、结果、证据位置和后续问题。自动化测试仍归 ATR，不转写为 HVR 人工结果。

## 5. 待真实执行 / 问题

1. 五个场景的正式人工结果均待填写。当前只尝试了前两个 UI 场景；第一个被版本前置条件阻断，第二个仅得到澄清回复且在此前发生工具错误。由于缺少已接受 V1 且外部 Candidate 路径仍关闭，场景 1、3、4、5 无法继续完成真实编辑与下载验证。
2. HVR-SCN-001 的明确已有表头覆盖，与当前候选风险审阅分支之间存在可见差异。人工操作前需由负责人明确该场景是否要求“明确单格请求本身覆盖原值风险授权”，并据此决定是否另行修改实现/契约；本 HVR 不擅自改写预期或报告通过。
3. SCN-003 的“全部现有数据”是否足以唯一确定范围，取决于实际工作簿和用户所指范围；范围不能明确时，符合预期的结果是澄清，而非执行确认。

### 当前结论

**模拟核对已完成；真实人工验证尚未执行。** 五项均保持 `PENDING_MANUAL_VALIDATION`。初始 v3.0 自动化全量回归 FAIL 的事实保留；§6 记录的后续完整自动化回归 PASS。Playwright 场景未运行。自动化/内置浏览器证据只支持本文件明确标注的结论，不替代人工操作、真实 Provider 文件编辑、正式文件下载和独立回读。

## 6. 2026-11-09 部分验证候选自动化补充（非人工验收）

本节只追加 Odoo TransactionCase、Mock Provider 和合成 XLSX 证据；不生成正式 HVR-Run，不改变五个场景的人工状态。

| 项目 | 证据与结果 |
|---|---|
| 部分验证候选接受 | `v3-partial-review-focused-run1.log` 与 `test_partial_candidate_can_be_accepted_without_changing_its_validation_grade`：真实 Odoo TransactionCase 将 Candidate 推进为 Current/Last Valid，Document Revision 到 2；验证等级保持 `PARTIALLY_VERIFIED`；实际文件 SHA 与下载元数据绑定。独立回读 A1=15，C1=`=A1*2`。 |
| 部分验证候选拒绝 | `test_partial_candidate_can_be_rejected_without_advancing_current`：Candidate 标记为 rejected，Current、Last Valid 和 Document Revision 不变；验证等级仍为 `PARTIALLY_VERIFIED`。 |
| 连续编辑 | `test_two_successive_edits_use_successive_accepted_workbook_versions` 与 `v3-partially-verified-version-chain.json`：第二轮输入为已接受 V2 字节，V3 保留 A1=15 并写入 A2=20。文件 SHA、ZIP 完整性与 openpyxl 读取结果见 `v3-partial-review-artifact-readback.txt`。 |
| 全量自动化回归 | `v3-partial-review-full-run2-no-upgrade.log`：240 tests，0 failed，0 errors，退出码 0。此运行没有再次升级模块。首次升级型全量运行的 SerializationFailure 保留在 `v3-partial-review-full-run1.log`。 |
| Playwright / Provider | Playwright 场景 **NOT RUN**；无已支持的 Playwright 到认证 in-app session 桥接。无真实 Provider 请求。 |
| 人工 HVR 状态 | 0 PASS / 0 FAIL / 0 BLOCKED / **5 PENDING_MANUAL_VALIDATION**。本节不能替代人工点击、候选下载和实际业务审阅。 |

## 7. 2026-11-09 Odoo UI → Agent → Candidate 闭环实测（测试适配器，非人工独立复核）

本节追加本轮实际 UI 与 Odoo ORM 证据，不覆盖 §1–§6 的历史结果。浏览器由当前已登录的 Mitchell Admin 用户操作；文件编辑使用仅对本次合成 Thread `llm.thread_15880` 开放的 CC-04 测试注入适配器。OpenAI Chat Completions 仅处理对话文本和 Tool 选择；没有向 Provider 上传 XLSX，也没有调用 Responses API / Code Interpreter。`EXTERNAL_PROVIDER_DISPATCH_ENABLED=False` 保持不变。

| 项目 | 本轮实际记录 |
|---|---|
| 时间与运行环境 | 2026-11-09，Odoo UI 本地时间约 18:25–18:54。HVR 在专用 Odoo `127.0.0.1:8092` 测试进程（PID 76323）和非生产数据库 `odoo18ce` 上运行；8091（当时观测 PID 59424）未被重启或修改，进程内已加载模块身份未直接证明（`UNVERIFIED`）。8092 加载当前工作区源码，测试注入仅允许 Thread 15880。浏览器 UI 显示 Mitchell Admin、模型 `gpt-5.6-luna`。这是真实 Odoo UI/Tool 交互，但 Candidate XLSX 由测试适配器生成，不是 Candidate B Provider 文件编辑验收。 |
| 合成输入 | `evidence/CB-M2-CB-04/browser-simulation/hvr-live-synthetic-v1.xlsx`。`Inventory!A1=10`、`A2` 为空、`C1` 公式 `=A1*2`；`Notes` 含固定合成文本。输入 SHA-256：`210ce0f0ae522067bb55b4fcd47aab0e9738b7728fa886a11773f9f04955f663`。附件 ID 38108，由当前用户 ORM 回读，字节与本地输入 SHA 一致。 |
| V1 基线 | 通过 UI 调用 M1 `office_prepare_context`（Session 12212）、显式同值写入 `Inventory!A1=10` 生成预览 38109，并由用户在 UI 明确接受后调用 `office_finalize`。首次 Finalize 未带精确短语而被拒绝；用户随后发送“确认并生成正式文件”，Tool call `call_wAGsDCIW93W4NLjf613SyW5T` 成功。初始版本 ID 1175，V1 `VERIFIED`，当前/last-valid=1175，Document Revision=1，父版本为空，输出附件 38111，SHA-256 `7d4b731af6e2905241f4f70457dc82867722cfc5b761be2312cb0d801cd6f2d8`。独立 OpenPyXL/ZIP 回读确认初始值和公式。 |
| HVR-01 用户要求 / Agent Tool | 首次发送核心要求时因尚无已接受的版本化 Workbook，被 `office` Tool `call_VV8u63mneLdUG5r1JPFqceg8` 阻断；没有改动。V1 登记后重试核心要求（并附“不要走 M1/Finalize、只生成候选”的测试边界），Agent 通过 `office` Tool `call_4ummvAHCsh9peoUd0NJhcfpF` 产生绑定 V1 的计划，再经 `call_HkyFQ532rM5aNwiKPqK63tcH` 产生 Candidate 1176。`operation_status` 从 `plan_ready` 到候选生成；没有未经授权推进 Current。结果：**PASS（重试后候选生成；首次阻断保留记录）**。 |
| HVR-02 候选查看 / 下载 | UI 展示 Candidate 下载链接，Candidate 1176 的附件 38112 可由当前用户 ORM 读取，SHA-256 `5c5c35508f076884f6450ee04409a59796920ef3540297e268bd84a69efa95f4`。独立读取确认 ZIP 完整、工作表 `Inventory`/`Notes` 存在、A1=15、A2 空、C1=`=A1*2`、Notes 合成值保持。实际点击 UI 提供的链接时，`download=true%20` 返回 HTTP 500；日志显示 `str2bool` 因尾随空格抛 `ValueError`。不带空格的同一下载路由返回 HTTP 200，但不能替代错误 UI 链接的验收。结果：**FAIL（候选内容与绑定可回读；用户可见下载链接损坏）**。 |
| HVR-03 用户接受 | UI 用户先发送“我已经查看修改后的文件，接受这个候选版本。”，Agent 请求精确回复“接受”；用户再发送“接受”，Agent 通过 `office` Tool `call_TzYomiNqomqJg0y6V3ImmbCZ` 接受版本 1176。ORM 回读：Current=Last Valid=1176，Document Revision=2；V2 父版本=1175，输入 SHA 等于 V1 输出 SHA；`validation_result/state` 保持 `PARTIALLY_VERIFIED/accepted_current`，没有伪装成 `VERIFIED`。接受动作及版本推进通过；但 HVR-02 的 UI 下载入口失败，故真实查看候选这一前置条件未证实。结果：**PARTIAL（接受路径通过；完整“查看后接受”场景未通过）**。 |
| HVR-04 连续编辑 | UI 用户要求基于已接受文件将 `Inventory!A2` 设为数值 20。Agent 两次调用 `office`（`call_fR9MPZ6dRGsNtYZulg77iIBa`、`call_t1RM9Hk7PR8SRRdHX2GevBZJ`），候选版本 1177 的父版本确为 1176，输入 SHA=`5c5c35508f076884f6450ee04409a59796920ef3540297e268bd84a69efa95f4`。实际 Candidate SHA=`674a9c72216b7be6eb5be138461b845f92972cc93954a64f7df2a52da89d5b7a`，ZIP 可读；回读 A1=15、A2=20、C1=`=A1*2`，Notes 值保持。V2→失败候选的独立差异：除 A2 值外，目标空白格从无显式样式变为默认 `StyleArray`；`Inventory` 尺寸从 A1:C1 扩至 A1:C2。CB-03 返回 `FAILED`，版本 1177 未接受；Agent 明确报告失败，Current/Last Valid 仍为 1176，Document Revision 仍为 2。结果：**FAIL（文件编辑效果正确，但本地技术验证拒绝，未得到被接受的 V3）**。 |
| HVR-05 用户拒绝 | 未运行。前置 HVR-04 Candidate 未通过 CB-03，也未成为 Current V3，不能按要求从 V3 生成并拒绝 V4。状态：**BLOCKED / NOT RUN（依赖 V3 不存在）**。当前状态仍为 Current/Last Valid 1176；没有以失败版本冒充 V3。 |
| HVR-06 Agent 多轮 Tool 行为 | 实际观察到用户消息→Agent `office` 计划→Agent `office` 候选→结果说明；接受意图后 Agent 要求简短确认，再调用 `office` 完成接受；第二轮编辑验证失败后 Agent 如实报告 Candidate 失败及 Current 不变，没有宣称成功。结果：**PASS（UI/Agent 与测试适配器调用链；不等于 Candidate B Provider 集成）**。 |
| Provider、数据库及业务副作用 | 多轮对话向当前配置的 OpenAI Chat Completions 发送合成指令文本；没有发送 XLSX 字节。Candidate 使用测试注入路径。未修改 Odoo 业务记录；只产生合成测试 Thread/Session、Workbook Version、Document Request、消息与附件。未调用 Responses/Code Interpreter。 |
| 日志与回读证据 | 服务器追踪：`docs/implementation/evidence/CB-M2-CB-04/hvr-live-8092-20261109.log`；只读 ORM/独立 XLSX 回读脚本与输出：`docs/implementation/evidence/CB-M2-CB-04/browser-simulation/readback_live_hvr_v1.py`、`readback_live_hvr_v1-20261109.log`；合成夹具：`evidence/CB-M2-CB-04/browser-simulation/hvr-live-synthetic-v1.xlsx`。浏览器截图在交互过程中展示，但未保存为仓库文件。 |

### 本次 UI HVR 汇总

| HVR | 结果 |
|---|---|
| HVR-01 | **PASS**（先前无 V1 的阻断尝试保留；V1 建成后的候选生成成功） |
| HVR-02 | **FAIL**（实际 Candidate 下载链接尾随编码空格并返回 500；ORM 字节回读成功） |
| HVR-03 | **PARTIAL**（接受动作使 V2 成为 Current，`PARTIALLY_VERIFIED` 原样保留；UI 下载失败，未证实用户先实际查看） |
| HVR-04 | **FAIL**（Candidate V3 文件生成且目标值正确，但 CB-03 因 A2 默认样式/结构差异返回 FAILED，Current 未推进） |
| HVR-05 | **BLOCKED / NOT RUN**（V3 未接受，缺少其要求的当前基线） |
| HVR-06 | **PASS（限定范围）**（Agent UI/Tool 多轮与失败反馈实际发生；文件编辑使用测试适配器） |

因此本次 **CC-04 用户闭环 HVR 未通过**：用户接受 Candidate 的 Current 推进闭环已通过，但下载入口和连续编辑验证/接受仍失败；不能报告整条 UI→Candidate→连续接受/拒绝闭环 PASS。此前 §1–§6 的历史状态不变。 |

## 8. 2026-11-10 HVR-02 / HVR-04 缺陷修复与复测

本节追加修复后证据，不覆盖 2026-11-09 的 HVR 结果。修复只针对内部 Candidate 下载链接序列化和 XLSX 派生元数据的语义比较。8091 未重启；本次使用非生产 `odoo18ce`、合成工作簿和 8092 专用 UI 测试进程。没有向 Provider 发送 XLSX 文件；`EXTERNAL_PROVIDER_DISPATCH_ENABLED=False`。

### 修复与自动化结果

| 项目 | 实际结果 |
|---|---|
| 下载链接修复 | 根因在 `llm_thread._process_llm_body`：对内部 `/web/content/<id>?download=true` href 的尾随空格/`%20` 做定向规范化；正则替换后保留 Odoo 已净化的 HTML `Markup`，避免链接被作为纯文本转义。未改下载 Controller、附件身份或权限检查。聚焦 TransactionCase `test_office_candidate_download_href_trailing_space_is_normalized`：1 test，0 failed，0 errors，退出码 0，见 `evidence/CB-M2-CB-04/hvr-fix-download-focused-20261110-final.log`。 |
| XLSX Validator 修复 | 原因是工作表 `<dimension>` 随已用坐标派生变化、空白格显式默认样式序列化，以及无内容行索引等价表示被当作独立结构/样式变化。验证器现按默认样式语义比较，并忽略由单元格坐标推导的 dimension 和无意义空行索引；ZIP/OOXML 可读性、有效结构、实质样式变化和损坏文件拒绝仍保留。通用测试覆盖空白格写值、公式、派生 dimension/default-style 变化及损坏 XLSX。 |
| Validator 回归 | `PYTHONPATH=mymodules ./venv/bin/python -m pytest -q mymodules/office_verify/tests`：46 passed，1 warning。 |
| 完整 Odoo 回归 | `hvr-fix-full-regression-20261110.log`：241 个 `Starting Test`，最终 `0 failed, 0 error(s) of 241 tests`，退出码 0；1 项 HTTP/browser 测试因缺少 `websocket-client` 而 skipped。`tests.stats` 合计 283（255+28）与最终 241 的口径差异仍为 **UNEXPLAINED**，不将 283 视作执行通过数。未执行模块升级。日志还保留了 worker 子进程清理警告及 3 个无关 addon 未加载信息。 |
| 静态检查 | 本次变更 Python `py_compile` 与受影响代码 `git diff --check` 均通过。 |

### 修复后 UI 与 Candidate 复测

Candidate 1464 是通过 8092 的真实 Odoo UI → Agent `office` Tool → 本地测试注入编辑适配器生成的合成 Candidate；不是 Responses API / Code Interpreter 文件编辑。ORM 只读回读证实：父版本为已接受 V2 1176；输入 SHA 与 V2 输出 SHA 一致；Candidate 附件 39747 的 SHA 与 Candidate 输出 SHA 一致；ZIP 可读；A1=15、A2=20、C1=`=A1*2`；验证等级为 `PARTIALLY_VERIFIED`，没有被改写为 `VERIFIED`。证据见 `hvr-fix-current-readback-20261110.txt`、`readback_hvr_rerun_20261110.txt`、`hvr-rerun-v2-current-20261110.xlsx`、`hvr-rerun-v3-candidate-20261110.xlsx`。

旧的 Candidate 消息是在 Markup 保留修复之前生成的。浏览器 DOM 中没有实际 `<a href="/web/content/...">`，消息只显示转义后的链接文本；随后请求 Agent 重新呈现该链接时，Chat Completions 请求达到 Odoo 实时超时，未产生可点击的新消息。因此没有点击 UI 原始 Candidate 链接，也没有取得该次 UI HTTP 200。ORM 读取附件和手工 URL 均不替代这一验收。

| 场景 | 结果 | 证据与边界 |
|---|---|---|
| HVR-02 候选查看与 UI 下载 | **BLOCKED / NOT RUN（修复代码与自动化测试 PASS）** | 新消息中的 HTML 链接渲染未能在 UI 重现；没有 post-fix 原始 href 点击、HTTP 200、下载字节 SHA 及用户实际查看证据。观察记录：`hvr-fix-browser-observation-20261110.txt`。 |
| HVR-03 先查看再接受 | **BLOCKED** | Candidate 1464 可由当前用户 ORM 读取并独立回读，但用户没有通过 UI 下载/打开后审阅，也没有接受该 Candidate。Current/Last Valid 仍为 1176。 |
| HVR-04 连续编辑 | **PARTIAL** | 修复后 UI 调用链生成 Candidate 1464；V2→Candidate 的父版本、输入/输出 SHA、实际值、公式及 ZIP 回读正确，Validator 返回 `PARTIALLY_VERIFIED` 而非旧的误判 `FAILED`。但候选未被用户查看和接受，故 V3 Current 推进未验证。 |
| HVR-05 拒绝 Candidate | **NOT RUN / BLOCKED** | 没有已接受的 V3 作为拒绝 V4 的基线；未生成/拒绝 V4。 |
| HVR-06 Agent 多轮工具调用 | **历史限定 PASS** | 2026-11-09 的 UI/测试适配器观察仍有效；本轮重呈现链接请求超时，不能据此宣称本轮多轮 UI 链路通过。 |

### 版本状态与结论

本轮没有接受或拒绝 Candidate 1464，也没有正式推进版本。只读 ORM 状态：Current=Last Valid=1176，Document Revision=2；Candidate 1464 保持 `partially_verified`，父版本 1176。失败历史 Candidate 1368 仍为 `failed`。因此 2026-11-10 修复减少了下载格式化和合法 XLSX 变更的自动化缺陷，但 **HVR-02/03/04/05 全闭环验收未通过**；HVR-02、03 与 05 仍未完成，HVR-04 仅 Candidate 生成及文件回读通过。

## 9. 2026-11-10 CB-06 合成 UI 接受/拒绝闭环补充

本节记录当前任务执行的本地合成 UI 闭环，不覆盖前述失败记录。使用非生产数据库 `odoo18ce`、专用 Odoo 8092 测试进程及已登录 Mitchell Admin 浏览器会话；Thread `llm.thread_15880`，Session `12212`。候选 XLSX 由既有 CC-04 测试适配器在本地生成；没有调用 Responses API / Code Interpreter，也没有向外部发送 XLSX 字节。Agent 对合成文本的聊天和 `office` Tool 编排仍走当前聊天模型路径，因此本记录不声称“完全没有外部模型请求”。未修改业务记录、代码、8091 服务或模块。

| 步骤 | UI 操作与调用 | 版本、文件及状态 | 结果 |
|---|---|---|---|
| 基线 V1 | 2026-11-09 已记录的 UI 初始化；Thread `15880`，Session `12212`。预览 38109 经用户确认/Finalize（`call_wAGsDCIW93W4NLjf613SyW5T`）。 | V1 `1175`；SHA-256 `7d4b731af6e2905241f4f70457dc82867722cfc5b761be2312cb0d801cd6f2d8`；A1=10、A2 空、C1=`=A1*2`。 | 历史 UI 基线。 |
| A1 修改与接受 V2 | 历史 UI 计划/编辑调用 `call_4ummvAHCsh9peoUd0NJhcfpF`、`call_HkyFQ532rM5aNwiKPqK63tcH`；用户在 UI 明确接受，调用 `call_TzYomiNqomqJg0y6V3ImmbCZ`。 | V2 `1176`，父版本 1175；SHA-256 `5c5c35508f076884f6450ee04409a59796920ef3540297e268bd84a69efa95f4`；A1=15、A2 空、C1 公式保留。Current=Last Valid=1176，Revision=2。 | **接受路径 PASS**。 |
| A2 修改候选并接受 V3 | 本轮在同一 UI Thread 回复“接受”，Agent 调用 `office`，Tool ID `call_B095VQIjhRMNRQDPUz3lM4mC`。该 Candidate 1464 先前由同一 UI Thread 的测试适配器基于 V2 生成。 | V3 `1464`，父版本 1176；输入 SHA=`5c5c35508f076884f6450ee04409a59796920ef3540297e268bd84a69efa95f4`；输出/附件 SHA=`f97014323e07563f7cbee3d0c37c3fd831e3cba48cbeaa8afc431ed312e909e9`；回读 A1=15、A2=20、C1=`=A1*2`。ORM 只读核实 `accepted_current`、`PARTIALLY_VERIFIED`、Current=Last Valid=1464、Revision=3。 | **接受及连续版本推进 PASS**；验证等级未被改写。 |
| 生成拒绝候选 V4 | 用户在 UI 请求基于 Current 1464 将 `Inventory!A3` 设为 30；Agent 对 `office` 的 plan/edit 调用分别为 `call_TPZVDDNjKf5sBejDF3rPLqax`、`call_Qm3agQSzjfuDkEJ6Qmz83qDZ`。 | Candidate `1561`，父版本 1464；输入 SHA=`f97014323e07563f7cbee3d0c37c3fd831e3cba48cbeaa8afc431ed312e909e9`；输出/附件 SHA=`8bb6257f8c3df1350b203053d175dbb793c69f3c0eceaa2d1233df6ac5721fbb`；独立回读 A1=15、A2=20、A3=30、C1=`=A1*2`，ZIP 可读；等级 `PARTIALLY_VERIFIED`。 | Candidate 实际生成，未在生成时推进 Current。 |
| UI 拒绝 V4 | 用户先在 UI 表示拒绝；Agent 要求明确回复“拒绝”；用户回复后，Agent 调用 `office` Tool `call_EC1WAltBjkFlN0peF1sL4oYk` 并报告拒绝。 | ORM 只读核实 V4 `1561` 状态 `rejected`；Current=Last Valid=1464；Document Revision=3；V3 仍 `accepted_current`。 | **拒绝路径 PASS**；Current、Last Valid 与 Revision 均未推进。 |
| 用户下载/查看候选 | Candidate 1464 的 UI 消息没有形成可点击的附件链接（此前观察到链接 HTML 以文本显示）。本轮未取得 UI 下载 HTTP 200 或用户打开文件的证据。按授权使用 ORM 字节回读核对 Candidate 附件 SHA 与版本 SHA 一致，并验证 XLSX 内容。 | V3 附件字节 SHA 与 `f9701432…e909e9` 一致；V4 附件字节 SHA 与 `8bb6257f…21fbb` 一致。 | **HVR-02 FAIL**：ORM 回读可证明候选字节与记录绑定，但不能代替 UI 下载/查看。没有把它记为 PASS。 |

### 本节判定

- A1→V2 接受、A2→V3 接受，以及基于 V3 生成并拒绝 V4：**PASS（合成 Odoo UI/Agent/`office` Tool 链路，文件编辑为本地测试适配器）**。
- 当前最终指针：Current=Last Valid=`1464`；Document Revision=`3`。V4=`1561` 为 `rejected`，不影响有效版本。
- UI 下载/实际查看：**FAIL**。候选附件的 ORM SHA 与独立 XLSX 回读已记录，但没有可用的 UI 下载链接及 HTTP 成功证据。
- 因 HVR-02 未通过，不能宣称包含“用户实际查看后接受”的完整 UI 闭环全部通过。真实 Responses Provider 文件编辑仍未在本次执行。
- 本轮使用了真实聊天模型处理合成指令和 Tool 编排；没有向该模型发送 XLSX 文件字节。若“完全不接真实 Provider”被解释为连聊天文本模型请求也禁止，则这一点不满足该更严格解释；本轮文件编辑本身仍由本地测试适配器完成。

证据日志：`docs/implementation/evidence/CB-M2-CB-04/cb06-hvr-synthetic-ui-20261110.log`。本轮最终拒绝状态 ORM 查询结果记录于 `docs/implementation/evidence/CB-M2-CB-04/cb06-hvr-synthetic-ui-20261110.md`。
