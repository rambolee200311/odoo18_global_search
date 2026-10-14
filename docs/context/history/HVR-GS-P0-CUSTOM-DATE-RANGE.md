# HVR-GS-P0-CUSTOM-DATE-RANGE

## 0. 验证状态

| 字段 | 值 |
|---|---|
| 问题 | P0-01 自定义日期范围 |
| CC / 上游 | CC-005；SRS_global_search v1.5；TDD_global_search v0.4 |
| 状态 | Agent-assisted browser observation recorded; human sign-off pending |
| 环境 | Odoo 18 CE，本地授权 Workspace |
| 浏览器 | Integrated Chromium；本次观察未留存完整版本号 |
| 基线 | `main @ 878a2f7` + 本次工作树 |
| 日期 | 2026-10-14 |

## 1. 场景观察

| 场景 | 操作与观察 | Agent-assisted 结果 |
|---|---|---|
| 合法自定义范围 | 提交 `2026-06-01` 至 `2026-07-01`；请求为 date/between 且带 start/end；结果页成功显示 3247 条 | PASS |
| 不完整范围不扩大 | 已应用范围后只清空 From；提示必填两端；Search API 请求数为 0；原日期 chip 和结果摘要保持不变 | PASS |
| 倒序范围 | 设置 To 早于 From；提示结束日必须晚于起始日；Search API 请求数为 0 | PASS |

以上观察由 agent 操作浏览器完成，不冒充人类验证者，也不自动满足 CC-005 所需的正式 HVR。人工 verifier、完整浏览器版本及明确签署待补。

## 2. 人工交接

请人类验收者在目标浏览器确认合法范围结果，以及不完整/倒序范围不会触发搜索且已有过滤结果保持不变；记录验证者、浏览器版本、运行时配置版本和实际观察后，方可将 HVR 升级为正式 PASS。
