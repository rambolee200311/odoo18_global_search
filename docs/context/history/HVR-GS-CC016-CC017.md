# HVR-GS-CC016-CC017

## 0. 验证治理

本记录区分人类实际确认与 agent-assisted 浏览器观察。不得以自动化测试或 agent 观察冒充用户人工验收；No observation, no PASS。

## 1. 元数据

| 字段 | 值 |
|---|---|
| Intent | CC-016 v0.2；CC-017 v0.4 UI 子目标 |
| 环境 | 本地 Odoo 18 CE，授权共享 Search Workspace |
| 页面 | `http://127.0.0.1:8091/wd_global_search` |
| 浏览器 | Chromium 150.0.7871.250（agent-assisted 页面观察） |
| 视口 | 曾观察 1600×1800；CC-017 窄屏观察 375px |
| 页面配置版本 | 191 |
| 实现基线 | `main @ 2a360d0`（浏览器观察工作树原样提交，期间运行代码未改变） |
| Published checksum | 未提供/未记录 |
| 人类验证者身份 | 未提供可审计身份 |
| 证据日期 | 2026-10-14 |

## 2. 人类验证基线与状态

| 契约 | 已收到的用户陈述 | 正式 HVR 状态 |
|---|---|---|
| CC-016 §14.2 | 用户概括确认 CC-016 HVR 总体通过；没有逐场景步骤、预期/实际、请求结果、浏览器视口和 Published checksum 的记录。 | **BLOCKED / INSUFFICIENT EVIDENCE**；不得将 10 个场景逐一标 PASS |
| CC-017 页面验收 | 用户概括确认页面验收通过；没有完整 CC17-UI-TEST 矩阵签署记录。 | **BLOCKED / INSUFFICIENT EVIDENCE**；保留下方 agent-assisted 观察，不记为人类 PASS |

## 3. Agent-assisted 浏览器观察

以下是实际记录的页面观察，不是正式人类 HVR PASS：

1. 查询 `gemini chair lamp` 返回 2 条结果。
2. Resource Selector 位于 Search query 下方；七个 Workspace 区域顺序符合 CC-017 v0.4。
3. Search by field、Date and state filters、Query Understanding 首次均收缩；键盘 Enter/Space 可切换 disclosure。
4. 仅切换 disclosure 观察到 0 个 Search API 请求。
5. Chromium 1600×1800 与 375px 窄屏未见横向溢出。
6. 实测已存在角色包括 H1 32px、H2 20px、Query Understanding 14px、结果摘要 14px、Meta 12px；所测控件统一字体栈；卡片间距 28px、无边框/阴影。
7. 仅两条结果的页面没有分页按钮；未观察实际翻页。
8. 卡片节点仍为单一 `snapshot.rendered_text`；字段 Label/Value 与明细摘要无法安全区分。按 CC-017 §17 停止，没有解析 rendered text。

## 4. HVR 场景覆盖快照

| 范围 | 结果 | 证据缺口/限制 |
|---|---|---|
| CC16-HVR-001~010 | NOT EVIDENCED individually | 用户总体确认不能替代逐场景执行记录；无 checksum |
| CC17-UI-TEST-001 | PARTIAL | 只测量现有角色 |
| CC17-UI-TEST-002~004 | BLOCKED | rendered_text 单节点；契约禁止猜测 |
| CC17-UI-TEST-005 | NOT SATISFIED | 未实现 About X results/响应 Count |
| CC17-UI-TEST-006~009 | PARTIAL / PASS as specified in ATR | 仅对已存在节点及 Chromium 已观测样式 |
| CC17-UI-TEST-010 | NOT RUN | 无分页按钮可操作 |
| CC17-UI-TEST-011~012 | PARTIAL | 未完成完整语义、错误和权限矩阵 |
| CC17-UI-TEST-013 | NOT RUN | Firefox、Safari、Edge 未运行 |
| CC17-UI-TEST-014~016 | Agent observation PASS | disclosure 默认状态、区域顺序和零请求切换；不是人类签署 |

## 5. 人工处置

用户于本会话批准“带例外关闭并如实记录”。该批准作为处置指示记录；它不补造缺失的人类观察，也不把 BLOCKED、NOT RUN 或未满足项转为 PASS。后续如需严格满足冻结 CC，应补齐缺失证据并解决相应实现阻塞。
