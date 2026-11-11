# HVR-M2-CB-07 — 真实 Odoo UI / Agent 验收

**状态：FAILED BEFORE CANDIDATE — ONE REAL UI ATTEMPT; NO ACCEPT / DOWNLOAD**
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
