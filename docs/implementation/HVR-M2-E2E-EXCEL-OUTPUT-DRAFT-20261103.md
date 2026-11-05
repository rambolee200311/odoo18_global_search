# HVR-M2-E2E-EXCEL-OUTPUT（草稿）

| 项目 | 内容 |
|---|---|
| 文档状态 | 草稿；HV-01～HV-03 已由用户确认通过，HV-04 部分通过，仍有待验证项 |
| 日期 | 2026-11-03 |
| 最近更新 | 2026-11-05：登记 HV-04（联系人模板）部分通过；补录 Thread 13139 批量摘要更新的真实聊天、附件及 XLSX 回读证据 |
| 验收范围 | M2 通用 AI Excel 工具的 Excel 输出流程；不覆盖 DOCX 或全部 Document Operations 能力 |
| SRS 基线 | [SRS_office_engine_m2_ai_mapping_v1.1.0.md](../requirement/SRS_office_engine_m2_ai_mapping_v1.1.0.md) |
| 实施记录 | [IHR-M2-PHASE-C-DOCUMENT-OPERATIONS-20261103.md](IHR-M2-PHASE-C-DOCUMENT-OPERATIONS-20261103.md) |
| 自动化记录 | [ATR-M2-PHASE-C-DOCUMENT-OPERATIONS-20261103.md](ATR-M2-PHASE-C-DOCUMENT-OPERATIONS-20261103.md) |
| 最终阶段结论 | **未作最终验收判定**：Sales / Purchase 自动化浏览器 E2E 有 PASS 证据；HV-01～HV-03 用户确认通过，HV-04 部分通过；Odoo 测试数量差异仍为 OPEN |

## 1. 目的与判定边界

本 HVR 为人工验证记录草稿。HV-01～HV-03 的实际结果依据用户明确确认记录；这些确认未附完整的工具调用、下载文件或独立回读材料。本草稿不把已有自动化证据转写成人工 PASS。HV-04 已登记为部分通过；其未通过或尚未覆盖的操作仍明确列出，不扩写为完整 PASS。

自动化证据仅覆盖已有报告中明确记录的真实 OpenAI Provider `gpt-5.6-luna` Sales→CRM 风格模板和 Purchase→Reconciliation 模板流程，以及 Python 和 Odoo 自动化测试。库存模板没有已记录的 Provider / 浏览器 E2E 日志；联系人模板有 Thread `13139` 的真实聊天与文件回读证据，但仅覆盖批量摘要映射，清空 Acme 备注仍未通过。HV-03 的用户人工确认单独登记在第 3 节。

## 2. 已有证据基线

### 2.1 SRS 范围

SRS V1.1.0 的 FR-M2-006、FR-M2-007、FR-M2-008 分别规定：有效 Proposal 生成真实预览；多轮修改产生新 Proposal / Preview 版本并保留未修改映射；正式生成绑定当前确认版本并重新检查权限和数据新鲜度。该 SRS 是需求证据，不等同于测试结果。

### 2.2 自动化和真实 E2E 证据

| 类别 | 现有证据 | 当前记录 |
|---|---|---|
| Python Document Operations / `office_core` / `office_verify` | `/private/tmp/phase_c_final_python_tests_after_opsfix.log` | `97 passed in 13.05s`。这是自动化测试，不是 Odoo 或人工 E2E。 |
| Odoo TransactionCase | `/private/tmp/phase_c_odoo_transactioncases_final.log` | 最终行报告 `0 failed, 0 error(s) of 160 tests`；同一 PID 的模块统计分别为 `office_engine_m2: 166 tests`、`office_engine_odoo: 26 tests`，测试启动日志有 160 条。现有证据未解释统计数量差异，登记为 **OPEN**，不推测原因。 |
| Sales → CRM 风格 Excel | IHR / ATR 记录真实 OpenAI Provider、Thread `10004`、销售订单 GS-SO-0001..0003（记录 ID 5052..5054）、预览和正式下载、openpyxl 回读。 | **AUTOMATED E2E PASS**：编号顺序、金额、`0.00` 格式、M 列数据区清空、标题/表头及 ZIP 完整性有报告证据。它不是本 HVR 的人工验证结果。 |
| Purchase → Reconciliation Excel | IHR / ATR 记录真实 OpenAI Provider、Thread `10125`、Session `7872`、P00001/P00002、Preview / Finalize Tool Call、附件/消息 ID、下载和文件回读。 | **AUTOMATED E2E PASS**：Preview 附件 25658 / 消息 68379；Finalize 附件 25659 / 消息 68384；下载 HTTP 200；订单、供应商、金额、币种、格式、清空列和 ZIP 校验均有报告证据。它不是本 HVR 的人工验证结果。 |
| Inventory / Contacts | HV-03 库存模板：用户在 2026-11-05 明确确认通过，当前记录未附独立文件回读。HV-04 联系人模板：Thread `13139` 的真实 `gpt-5.6-luna` 聊天完成排序后的批量摘要 `comment + name` 更新，预览附件 `31137` 发布到消息 `83145`；已独立回读 XLSX。此前 Acme 备注清空失败仍保留，没有被这次不同操作改写为成功。 | HV-03：**USER-CONFIRMED MANUAL PASS**；HV-04：**PARTIAL**。回读支持批量映射、联系人顺序、数值零保留和非目标内容保护；不证明“清空 Acme 备注”已成功。 |

现有下载文件证据路径：

- Sales 预览：`/Users/lijianqiang/Downloads/preview_GS-SO-0001_sales_crm_template.xlsx`
- Sales 正式文件：`/Users/lijianqiang/Downloads/office-output-fe5e854c-f847-5f8f-a015-5a805fe45ae7.xlsx`
- Purchase 预览：`/Users/lijianqiang/Downloads/preview_P00001_purchase_reconciliation_template (2).xlsx`
- Purchase 正式文件：`/Users/lijianqiang/Downloads/office-output-a1de374a-0d59-5107-89e3-ed64fa40945e.xlsx`

### 2.3 历史失败、根因、修复和回归

以下历史事实保留，不能用后续通过结果覆盖：

1. **较早 Purchase 预览虽显示工具成功，独立回读不符合要求。** `D4:E5` 为 `General`，`M4` 仍是 `REMOVE AFTER IMPORT`。根因已在 IHR / ATR 记录：Provider 把 `format_patches` 和 `clear_columns` 放在 `proposal` 顶层，而 `office_save_mapping_preview()` 当时没有接收这些顶层参数，执行阶段未应用请求的文档操作。之后修改了 Schema 和方法签名、显式合并操作，并加入 TransactionCase；最终修复后的真实下载回读通过。
2. **较早 Purchase 修改请求返回 `invalid/type_mismatch`。** 当时 repeat-row 把目标列限制为公式类型，阻止了后续明确的数字赋值。之后调整了允许值类型的合并逻辑，并以不把 E 列声明为 repeat-row 公式列、直接写入数值的真实预览流程验证恢复。失败请求仍作为历史记录保留。
3. **初始 Phase C 报告曾将 Odoo 和浏览器验收标记为 BLOCKED / 未运行。** 用户授权在共享开发库测试后，随后补做 TransactionCase 和真实浏览器验收；当前状态以 IHR / ATR 后附的后续记录为准。最初的失败/阻塞记录仍保留。
4. **Odoo 测试数量差异尚无解释。** 日志在相同测试进程 PID `49444` 下记录模块统计 166 与 26，最终汇总 160；该进程有 160 条 `Starting Test` 记录。现有日志没有给出为何模块统计合计与最终汇总不同的说明，问题保持 **OPEN**，不猜测去重或统计规则。
5. **库存模板曾有多次未成功尝试，保留其失败事实。** Thread `12063` 的历史对话先后记录了：19 条记录超过模板初始 2 行明细容量；`repeat_rows` 曾以对象而非列表提交；一次 Provider 请求超时；用户确认扩展至第 20 行、汇总行移至第 21 行后，执行又因确认范围与写入检查不匹配而未生成预览。随后用户于 2026-11-05 明确确认库存模板验证通过。该人工通过结论不覆盖上述失败记录；本次确认未附最终文件、下载回读断言或库存前后值，因此这些细节仍不能由本 HVR 独立核实。
6. **联系人模板“清空 Acme 备注”失败及后续批量更新。** Thread `13139` 的初始填充和排序工具返回成功；清空备注的两次提交均失败，既有预览未更新。只读 ORM 检查显示，两次请求都同时带有 `repeat_rows`（含备注列 I）和对 `xlsx:联系人清单!I2` 的明确空值 `cell_edits`，服务端返回 `target_mapped_and_cell_edited:xlsx:联系人清单!I2`。根因是重复行派生映射与显式坐标编辑被当作冲突写入。后来加入了通用优先级处理及 TransactionCase 回归，并在同一 Thread 的真实聊天中执行了新的批量摘要映射；该次操作成功，但它不是“清空 Acme 备注”的重试或成功证据。批量结果和回读详见 HV-04；原始清空失败事实保留。

## 3. 人工验证记录

### HV-01：销售订单 → CRM 跟进模板

| 项目 | 内容 |
|---|---|
| 验证目的 | 在真实 Odoo 聊天中，以当前用户有权读取的销售订单填充 CRM 跟进 Excel；人工确认自然语言请求、预览附件、下载文件和单元格结果一致。 |
| 前置条件 | 登录本地 Odoo 8091；OpenAI Provider `gpt-5.6-luna` 可用；当前用户可通过原生 ORM/Record Rules 读取所选销售订单；模板 `M2_Test_Template_01_SalesOrder_to_CRM.xlsx` 可上传。现有模板副本位于 `/Users/lijianqiang/Downloads/M2_Office_AI_Test_Pack/M2_Test_Template_01_SalesOrder_to_CRM.xlsx`。 |
| 操作步骤 | 1. 在新建或指定的人工验收 Thread 上传模板。 2. 用自然语言说明要使用哪笔（或哪些）真实销售订单及需填字段。 3. 检查助手回复和实际附件卡片。 4. 下载预览；用 Excel 或其他独立阅读方式核对订单标识、字段值、格式及未要求修改的模板区域。 5. 若要验正式输出，按产品流程确认并下载正式文件，核对其与预览一致。 |
| 预期结果 | 只使用当前用户可访问的真实订单；模板目标与真实记录字段对应；预览/正式文件可下载；检查的内容正确，非目标区域没有意外变化。实际字段和预期值由验收人根据上传模板及所选订单记录填写。 |
| 实际结果（用户填写） | 用户确认“验证1，销售订单，通过”。本次确认未附具体订单编号、Thread、附件下载或独立回读详情。 |
| 证据（用户填写：Thread/时间、工具调用、附件、下载文件、回读结果或截图） | 用户于 2026-11-04 在本 Codex 对话中明确确认 HV-01（销售订单）通过。该确认是人工验收结论；本次消息未提供可单独复核的 Thread、文件或截图。已有 Sales→CRM 自动化 E2E 证据仍按第 2.2 节单独列示，不作为人工证据替代。 |
| 状态 | `PASS`（用户确认；详细复核材料未随确认提供） |

### HV-02：采购订单 → 采购对账模板

| 项目 | 内容 |
|---|---|
| 验证目的 | 在真实 Odoo 聊天中，以当前用户有权读取的采购订单填充不同结构的对账 Excel；核对采购字段和金额口径，并检查可下载交付。 |
| 前置条件 | 登录本地 Odoo 8091；Provider 可用；当前用户可读取所选采购订单及需用关联字段；模板 `M2_Test_Template_02_Purchase_Reconciliation.xlsx` 可上传。现有模板副本位于 `/Users/lijianqiang/Downloads/M2_Office_AI_Test_Pack/M2_Test_Template_02_Purchase_Reconciliation.xlsx`。之前自动化 E2E 使用 P00001/P00002，但本次人工验证需记录本次实际可访问记录，不默认复用旧状态。 |
| 操作步骤 | 1. 在人工验收 Thread 上传模板。 2. 用自然语言指定真实采购订单及填表字段；如要求计算金额，明确倍率、币种精度及舍入要求。 3. 查看助手的工具调用与预览附件。 4. 下载预览并核对供应商、订单号、订单金额、币种和计算结果。 5. 需要正式文件时完成确认，再下载并核对正式文件与确认的预览一致。 |
| 预期结果 | 只读取有权限的采购数据；金额来源与计算口径明确；预览/正式 Excel 可下载且内容正确；不相关模板内容保留。 |
| 实际结果（用户填写） | 用户明确确认“采购订单验证，通过”。未提供本次人工操作的订单编号、Thread、附件下载或独立回读细节。 |
| 证据（用户填写：Thread/时间、记录编号、工具调用、附件、文件回读或截图） | 用户于 2026-11-05 在本 Codex 对话中明确确认 HV-02（采购订单）通过。该签认记录为人工验收结论；本次消息未附可单独复核的 Thread、文件或截图。已有 Purchase→Reconciliation 自动化 E2E 证据仍单独列于第 2.2 节，不替代本次人工确认。 |
| 状态 | `PASS`（用户确认；详细复核材料未随确认提供） |

### HV-03：只读库存数据 → 库存模板

| 项目 | 内容 |
|---|---|
| 验证目的 | 验证从当前用户可访问的真实库存数据生成 Excel 输出时只读，不触发任何库存业务写入。 |
| 前置条件 | 登录本地 Odoo 8091；当前用户有权读取本次所选库存记录；模板 `M2_Test_Template_03_Inventory.xlsx` 可上传。现有模板副本位于 `/Users/lijianqiang/Downloads/M2_Office_AI_Test_Pack/M2_Test_Template_03_Inventory.xlsx`。先记录所选产品/库位/记录范围及验收前可见的库存数值。 |
| 操作步骤 | 1. 在验收 Thread 上传模板。 2. 用自然语言要求读取当前用户有权访问的库存记录并填入模板。 3. 检查执行过程没有收货、发货、调拨、库存调整、预留或其他库存写操作。 4. 下载预览；将其与验收前记录的 ORM 可见值逐项核对。 5. 再检查同一库存记录的数量/状态未因本次测试变化。 |
| 预期结果 | 生成的 Excel 与可访问库存数据一致；只发生读取和文件输出；库存数量、预留及业务状态未被本次测试修改。若任一写入动作出现，立即停止并记录，不继续 Finalize。 |
| 实际结果（用户填写） | 用户于 2026-11-05 明确确认：“验证3，库存数据填充库存模板，通过”。按用户的人工验收结论登记为通过。本次确认没有列出实际记录范围、逐字段结果、公式回读或库存前后值。 |
| 证据（用户填写：Thread/时间、选定记录、工具调用、前后数据核对、下载文件或截图） | 用户在本 Codex 对话中作出的明确验收确认；当时浏览器上下文为 Odoo Thread `12063`。未随确认附最终附件 ID、下载文件、截图、独立回读输出或库存前后值记录。历史失败过程见第 2.3 节第 5 项。 |
| 状态 | `PASS`（用户确认；详细文件与库存前后核验材料未随确认提供） |

### HV-04：通用联系人模板（Many2one、空值和零值）

| 项目 | 内容 |
|---|---|
| 验证目的 | 验证通用联系人 Excel 流程能正确输出 Many2one 关联值、空值和数值零，尤其确认 `0` 不会被误当成空白。 |
| 前置条件 | 登录本地 Odoo 8091；当前用户可读取被选中的真实 `res.partner` 联系人/公司及所需关联字段；模板 `M2_Test_Template_04_Contacts.xlsx` 可上传。现有模板副本位于 `/Users/lijianqiang/Downloads/M2_Office_AI_Test_Pack/M2_Test_Template_04_Contacts.xlsx`。模板和可访问数据中须存在可观察的关联、空值和有效零值；若实际数据没有该组合，不得编造或修改源业务数据，应记录无法覆盖的条件。 |
| 操作步骤 | 1. 选择当前用户可访问的真实联系人/公司记录，并先确认关联字段、一个空值和一个真实数值 `0` 的来源。 2. 上传模板，用自然语言说明需填字段及联系人范围。 3. 查看工具调用和附件卡片。 4. 下载预览，用独立方式核对 Many2one 展示值、空单元格与数字 `0` 的类型和值。 5. 如执行正式生成，确认后下载并重复核对。 |
| 预期结果 | Many2one 输出对应的关联显示值；真实空值仍为空；数值零保留为数值 `0` 而不是空白；其他联系人和模板内容没有意外改动。 |
| 实际结果（用户填写） | 用户于 2026-11-05 登记“验证4，联系人，部分通过”。真实 Thread `13139` 中，初始联系人填充和按联系人姓名排序曾返回预览；之后执行“在这个预览文件基础上，批量修改摘要=remark+联系人名称”，真实 Provider 以 `comment + name`、分隔符 `+` 提交批量重复行映射，服务器返回 `status=success` 并生成新预览。独立回读显示联系人顺序为 Acme Corporation、Addison Olson、Sandra Neal；公司关系值正确；信用额度列的数值 `0` 保留为数值零；当前三条记录的 `comment` 在 ORM 中均为空，因此摘要列结果分别只有联系人名称。相对前一预览，只有 `I2:I4` 的值改变，其他单元格值和样式、合并区域及工作表控件均保留。此前“清空 Acme 备注”两次失败；后续批量映射写入了 `I2 = Acme Corporation`，所以不能将清空操作登记为通过。 |
| 证据（Thread/时间、记录编号/字段来源、工具调用、附件、文件回读或截图） | 真实聊天 Thread `13139`；Provider `gpt-5.6-luna`；工具 `office_prepare_context` 后调用 `office_save_mapping_preview`，参数包含 `repeat_rows` 列 I 的 `concat_fields: ["comment", "name"]`、`separator: "+"`。成功返回预览附件 ID `31137`、消息 ID `83145`，且 `attachment_posted_to_thread=true`。独立回读文件 `/private/tmp/m2-thread-13139-preview.xlsx`（SHA-256 `085c4319767648444ebfb723b90fd24efe5297e84655579e710ac2fb689a08be`）；比较基线 `/private/tmp/m2-thread-13139-preview-before.xlsx`。回读断言：XLSX ZIP 有效、排序与当前 ORM 名称一致、空 comment 被略过、仅 `I2:I4` 值改变、非目标值与样式及工作表结构保留。回归测试：`PYTHONPATH=. ./venv/bin/pytest -q mymodules/office_mapping_verify/tests`（`141 passed`）；定向 Odoo TransactionCase 2 项通过；失败复现日志 `/private/tmp/m2_concat_empty_comment_red.log`，修复后日志 `/private/tmp/m2_concat_empty_comment_green.log`。清空 Acme 的既有失败工具消息及事务测试证据继续保留，批量摘要成功不替代该清空场景的验证。 |
| 状态 | `PARTIAL`（批量摘要映射、预览交付及回读通过；显式清空 Acme 摘要仍未验证为成功） |

## 4. 待关闭问题与最终结论

1. HV-01 销售订单 → CRM 跟进模板、HV-02 采购订单 → 采购对账模板、HV-03 只读库存数据 → 库存模板：用户均已确认通过；三项确认均未提供完整的独立复核材料。HV-04 的批量摘要映射已有真实 Thread、附件和 XLSX 回读证据，用户登记为部分通过；此前“清空 Acme 备注”失败，尚无该明确清空操作成功后的浏览器和文件回读证据，故 HV-04 保持 `PARTIAL`。
2. Odoo 日志测试数量差异为 **OPEN**：同一进程的模块 stats 为 166 和 26，最终汇总为 160，另有 160 条测试启动记录；联系人清空修复的定向日志也显示模块 stats 为 3、最终汇总为 1。现有日志没有解释这些统计差异。
3. 既有自动化 E2E 的 Sales→CRM 与 Purchase→Reconciliation 为 **PASS**；HV-03 是用户确认的人工 PASS，但缺少可随报告独立复核的文件证据。HV-04 仅为 **PARTIAL**。自动化结果不能替代人工验证，也不能填补 HV-03 的文件回读证据缺口或 HV-04 的清空操作缺口。

**本 HVR 草稿不宣布整体阶段最终验收通过。** HV-01～HV-03 的人工状态依据用户明确确认记录；HV-04 批量摘要更新部分通过，但显式清空操作仍待验证。库存项目的用户判定为 PASS，但最终文件回读、库存前后不变证据仍未附于本报告。整体阶段结论仍待后续评审和证据核对。
