# HVR-M2-CB-07 — 真实 Odoo UI / Agent 验收

**状态：PASS — CODEX REAL UI HVR + OWNER-REPORTED 8091 HUMAN UAT**
**契约：** `CC-M2-CB-07_Route_B_End-to-End_Integration_v0.2.md`
**记录日期：** 2026-11-10

## 2026-11-11 Validator 修复后的一次真实 UI 复验

环境为非生产数据库 `odoo18ce` 的 Odoo 8092 测试实例。新建 Thread `llm.thread_18271`，模型为 `gpt-5.6-luna`，仅绑定 `odoo_record_retriever` 和 `office`。上传合成文件 `cc07-route-b-v1-input-42f92959aa.xlsx`，输入 SHA-256：`97b0c50c4bee214f469f03a1a5dcd70ff6c58266e9fb8d6ea9b6a4a219ae81da`；其唯一工作表 `Contacts` 有 `Name`、`Phone`、`Email` 表头。

实际用户指令未提供工作表坐标、Expected Effect 或 Tool 名称：

> 请从 Odoo 联系人中选择本次测试专用的 3 条合成联系人记录（名称以 CC07-SYN-42f92959aa 开头），将姓名、电话和邮箱填写到我上传的工作簿中，保留原有表头及其他内容，生成文件让我查看。不要修改 Odoo 联系人数据。

### 场景结果

| 步骤 | 结果 | 实际证据 |
|---|---|---|
| 用户在 UI 上传文件并发送普通指令 | PASS | Thread `llm.thread_18271`；输入附件 ID `45075`，见服务器日志 |
| Agent 调用 Retriever | PASS | Tool call `call_wZJ76wkNCxo44yLiQnBnCD6T`，读取 `res.partner`，domain 为 `name like CC07-SYN-42f92959aa%`，字段 `id/name/phone/email`，limit 3，order `id asc` |
| Retriever 返回合成记录 | PASS | 31335 Ava、31336 Noah、31337 Mia；数据仅为本次合成测试记录 |
| Agent 调用 Office 并创建 Candidate | FAIL | Tool call `call_xD5ROm0hh13iGApJDqMycjFA` 返回 `clarification_required`、`error_code=expected_effect_invalid`、`operation_executed=false` |
| Candidate / Accept / Current V1 | NOT RUN | 服务端未创建 Candidate；没有接受动作或 Current 推进 |
| Candidate 下载及 XLSX 回读 | NOT RUN | 无候选文件可供下载或回读 |

Office 调用的 Expected Effect 使用全工作簿 `workbook_structure` 目标，断言中将 Sheet/单元格填写为 `<uploaded workbook>`、`<contact name cell>` 等占位符，并把具体地址描述为 unknown。CB-03 依据冻结契约拒绝该结构。因失败发生在 Expected Effect 规范化阶段，Responses API + Hosted Code Interpreter 文件编辑没有被调用。真实 Odoo 服务日志显示本轮是 OpenAI Chat Completions Agent 工具循环；没有 Responses/Code Interpreter 请求 ID 或文件 ID。

本轮只尝试一次，按执行要求未重试 Provider。Odoo 联系人保持只读；没有 Candidate、Accept、V1、下载或 Finalize 副作用。证据见 [`evidence/CB-M2-CB-07/HVR-RUN-002-ui-failure.json`](evidence/CB-M2-CB-07/HVR-RUN-002-ui-failure.json) 和 [`evidence/CB-M2-CB-07/HVR-RUN-001-provider-ui-server.log`](evidence/CB-M2-CB-07/HVR-RUN-001-provider-ui-server.log)。

## 历史场景状态

| HVR 场景 | 状态 | 证据/说明 |
|---|---|---|
| 原始 XLSX → 首个 Candidate → 用户接受 V1 | NOT RUN | Route B TransactionCase 已编写/调整但未运行；真实 UI/Provider 路径未执行。 |
| 同一 Thread 第二次 Retriever → Candidate V2 → 接受 | NOT RUN | 未执行真实用户轮次或真实 Provider 调用。 |
| 连续值/格式/结构编辑 V1→V4 | NOT RUN | 未执行。 |
| 用户拒绝并保持 Current | NOT RUN | 未执行真实 UI 流程。 |
| Finalize、Discuss 附件卡、下载及 SHA 回读 | NOT RUN | 未执行。 |

**明确区分：** 历史 `ExpectedEffectWorkbookAdapter` / TransactionCase 测试和 Candidate 2354 的离线重放不能代替本轮真实 UI HVR。真实 UI 已运行，但在 Candidate 生成前失败；本报告不标记为 HVR PASS。


## 2026-11-11 — 8091 三轮真实人工 UAT

**验证方式：**真实用户在 Odoo Discuss 手工输入并接受/Finalize；明确标记为 `Human UAT`，不是 Automated User Simulation。人工操作结果依据负责人本轮提交的验收记录；后端 Thread/Tool/Version 记录及本地 ORM/XLSX 回读作旁证。未提供截图/录屏，本报告不声称存在截图证据。

三轮实际业务结果：

| 轮次 | 用户任务 | Retriever / Office 记录 | Candidate 与决定 | 验证结果 |
|---|---|---|---|---|
| 1 | 查询 3 条真实联系人，填写姓名、电话、邮件 | Retriever `call_CS46KGR5PjSc6kGIqBZXA8fY`；Office edit `call_BPDKf3Rr34Qeb8VN5WAWerHD` | V1/版本 3096；Accept `call_p0hfRlqD78BW2tHbhnlyOUqF`；Finalize `call_ZS8e2HrzsDAqEJbUJTIf4SgD` | PASS；PARTIALLY_VERIFIED；SHA `73fbbdc7fd5a5c4b26c5d7f4331235518589305b9c3bd22700f8fbde233df595` |
| 2 | 基于已接受文件增加地址列并填写地址 | Retriever `call_xzBvOwM33buVkNR6oeQEpLPk`；Office edit `call_s1mHyySSmopTvwRBCKLiKDM0` | V2/版本 3097，parent 3096；Accept `call_B1TSZo5WYtqmPGkAmu8TsTP4`；Finalize `call_9asP9n5bnqzNu2B6mBSLuvHE` | PASS；PARTIALLY_VERIFIED；SHA `8eeff835417e8add4f76e3ea3571b2b2f1cdac2b856987cdaae6261711a3f9ec` |
| 3 | 基于已接受文件增加国家列，写入国家名称与编码 | Retriever `call_6oOuSDSA2g7vA5uiLafk57nF`、`call_aSTt7LVj0MUbxWfkJped4pqr`；Office edit `call_ZHiaXq58Yp3FRaMMMD0JjnL8` | V3/版本 3098，parent 3097；Accept `call_9yuxZlBKGEUYQNRoHePEKwby`；Finalize `call_x2m4cyfFsMaAmHVbVUllattO` | PASS；PARTIALLY_VERIFIED；SHA `ce0fbc36a83bbf8c92984aff3721a14caa1c3f1cd8803af474ce94e8333d8d20` |

### 版本与文件回读

- Thread `llm.thread_19293`，Session 14951，原始上传附件 48038；用户消息及工具结果保存在同一 Thread。
- V1、V2、V3 均为真实 Provider Candidate 经正式 `office(action="accept")` 接受，再由 `office(action="finalize")` 交付；没有直接 ORM 写入状态。
- V1→V2、V2→V3 的 `input_sha256` 均等于 parent `output_sha256`；openpyxl 回读确认 V1 原有单元格值在 V2 保留，V2 原有单元格值在 V3 保留。
- Sheet1 表头依次从 `index / 姓名 / 电话 / 邮件地址` 扩展为增加 `地址`，再增加 `国家`；三个数据行保留，最终国家列 3 行均非空。该只读回读不输出联系人个人信息。
- Current=Last Valid=3098；Document Revision=3；V3 状态 `finalized`、delivery=`delivered`。最终附件 48041、消息 112970；附件字节 SHA 与 V3 output SHA 相同：`ce0fbc36a83bbf8c92984aff3721a14caa1c3f1cd8803af474ce94e8333d8d20`。
- 内容业务正确性和三轮真人接受/Finalize 由负责人 UAT 记录确认；本地独立回读确认文件、版本父链、原有内容连续性和附件 SHA。未对真实联系人数据作额外展示或外发。

## CC-07 关闭口径与保留限制

负责人于 2026-11-11 明确作出 `CLOSED — UAT PASSED` 决定：以普通 XLSX 多轮编辑与交付通过为完成标准，不要求覆盖全部 Excel 特性。此前 2026-11-11 的 Expected Effect 失败尝试仍保留为历史；后续 Route B 简化 HVR 与本节 8091 人工 UAT 完成了关闭依据。`PARTIALLY_VERIFIED` 未升级；复杂 Excel 特性未覆盖；`tests.stats` 与最终测试计数差异未解释。证据汇总见 [`evidence/CB-M2-CB-07/HVR-RUN-010-8091-human-uat-20261111.md`](evidence/CB-M2-CB-07/HVR-RUN-010-8091-human-uat-20261111.md)。
