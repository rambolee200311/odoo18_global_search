# HVR-M2-CB-08 — 定向 Provider / XLSX 验证

**状态：PASS — AUTOMATED TARGETED FILE VALIDATION; NOT UI HVR**
**契约：** [CC-M2-CB-08 v0.1](CC-M2-CB-08_Integrated_Regression_Release_Readiness_v0.1.md)
**记录日期：** 2026-11-11

## 验证方式

本项是 CC-08 定义的 targeted Provider/file validation：通过 Odoo shell、既有 `office(action="edit")` 服务、真实 OpenAI Responses API + Hosted Code Interpreter、Candidate Validator 与正式 Accept 服务验证一份合成 XLSX。不是 Discuss Agent 对话循环、Playwright 或真人浏览器 HVR。

合成工作簿：`Ledger` 页包含 `Description`、`Amount`、`Double` 表头；B2 为 `1234.5`，C2 为 `=B2*2`。用户指令只请求把 Amount 显示为两位小数 USD，保持内容、公式与工作表。

## 结果

| 步骤 | 结果 | 证据 |
|---|---|---|
| 受信配置选中当前已配置 OpenAI / `gpt-5.6-luna` | PASS | dispatch config 在 Odoo shell 为 `True`；只记录 Key/Base 是否存在，不记录凭据值 |
| 真实 Responses + Hosted Code Interpreter 请求 | PASS | Response `resp_0cb5523293f2196f016af433cfe4f887d2aedab066b798ba18`；工具调用 ID、Container、文件 ID、请求 ID和 Usage 见 JSON |
| Candidate 生成及技术验证 | PASS | 真实调用事务内 Candidate 3107 为 `PARTIALLY_VERIFIED`；输出是非空、有效 XLSX |
| 独立文件检查 | PASS | B2 格式为 `"$"#,##0.00`；C2 公式保留；全部值、Sheet 名称和非目标 style IDs 保留；ZIP 检查通过 |
| 正式 Accept / V1 状态 | PASS（相同字节的分段回放） | Candidate 3109 通过现有 Candidate/Validator/Accept 服务；状态仍为 `PARTIALLY_VERIFIED`，Current=Last Valid=3109，Revision=1，接受 SHA 与 Provider 返回文件一致 |
| UI/Agent/browser | NOT RUN | CC-08 只要求 targeted Provider/file HVR；完整业务 UI 验收已由 CC-07 证据覆盖，不在本轮重做 |

真实 Provider Candidate 3107 的创建事务因初始回读 harness 对跨工作簿 `StyleProxy` 做对象直接比较而回滚；修正为解析样式 ID 后，所有文件断言通过。由于安全审查拒绝第二次外部请求，本报告将原 Provider 字节原样回放到新的隔离 Odoo shell 事务，完成正式 Candidate/Accept 路径验证。Provider Response ID、请求数和回放 Candidate ID 分开记录，不能把该回放描述为一次连贯的真人或真实 Agent UI 操作。

输入 SHA-256：`2315994a4e2514d61ef2ba69ca0db942802d4b217d3b385864fc068a8fd0ba58`
Provider 输出 / 接受回放 SHA-256：`8f8e06a6f6f3e5cc1cf8888c0c35f7d505119ec79e435975332a1d9d0289d88a`

## 用量与清理

- 真实 Provider 请求：1 次；无自动重试。
- 用量：9,949 input tokens、1,988 output tokens（其中 reasoning 986）、总计 11,937 tokens；耗时 45,856 ms。
- Provider Container 清理状态：`completed`。
- 实际账单金额不可由该响应核实。
- Odoo shell 在结束时回滚测试用户、Thread、附件、Candidate 和版本状态；本地合成 XLSX 及脱敏证据保留。

## 证据

- [真实 Provider 响应元数据](evidence/CB-M2-CB-08/T1-real-provider-result-attempt-01.json)
- [校正后的独立 XLSX 回读](evidence/CB-M2-CB-08/T1-corrected-readback.json)
- [正式 Candidate/Accept 字节回放结果](evidence/CB-M2-CB-08/T1-replay-accept-result.json)
- [真实 Provider 输入](evidence/CB-M2-CB-08/T1-input.xlsx)
- [真实 Provider Candidate](evidence/CB-M2-CB-08/T1-candidate.xlsx)
- [Accept 回放文件](evidence/CB-M2-CB-08/T1-accepted-v1.xlsx)
