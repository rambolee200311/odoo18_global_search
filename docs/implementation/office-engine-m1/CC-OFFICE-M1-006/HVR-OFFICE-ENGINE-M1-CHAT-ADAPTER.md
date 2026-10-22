# HVR — CC-OFFICE-M1-006 聊天适配

## 验收记录

| 项 | 值 |
|---|---|
| 状态 | **负责人确认人工验收通过，CC-006 按 MVP 范围关闭；早期失败由后续复杂 XLSX 成功样本补充，适用范围仍限于已验证样本** |
| 验证日期 | 2026-10-22 |
| 人工确认日期 | 2026-10-22 |
| 验证页面 | `http://127.0.0.1:8091/odoo/action-631?active_id=llm.thread_48` |
| 浏览器 | Codex 内置浏览器；真实 Odoo 登录会话；通过 Playwright API 操作 |
| 历史 MVP 文件 | `cc006-spoofed.xlsx`（旧轮合成伪装文件；本轮未测试该文件） |
| 本轮正常文件 | `real_valid.xlsx`（合成合法 OOXML；A1=客户名称、B1=待填客户名称） |

## 已执行场景

1. 点击聊天曲别针，使用真实文件选择器选取合成文件。
2. 确认草稿区出现 `cc006-spoofed.xlsx` 文件名、XLSX 图标与卡片。
3. 输入“请读取这个附件并说明内容”并发送。
4. 确认消息流内出现用户消息和附件卡片；助手显示红色 `Attachment rejected` 错误气泡，并给出受控拒绝文案。
5. 确认拒绝后输入框仍可编辑，填写普通文本时 Send 按钮启用。为避免调用真实 OpenAI Provider，未点击发送；后续轮次上下文隔离由 Odoo Provider stub 自动化测试验证。
6. 刷新页面，错误气泡仍显示；输入框可继续使用。
7. 负责人已人工确认报错 UI 和输入框恢复，接受该行为作为 M1 MVP 聊天安全拦截交付。
8. 人工确认后按批准要求通过 `odoo-bin shell` ORM 清理本轮测试消息和附件，并在新 shell 会话复核清理结果。

## 验收范围与边界

本 HVR 只验收 M1 MVP 的真实上传、附件卡片、Provider 前拒绝、红色错误气泡、刷新持久性和输入框恢复。未验证且不纳入本次 HVR 的事项：合法 Office handoff、结构读取、Mapping Plan、文件生成/回读、结果附件、跨用户路由或真实 Provider 后续调用；这些仍按 M2/对应依赖 Gate 处理。

历史 MVP 人工确认记录：负责人此前确认报错 UI 和输入框恢复；该子范围记录不改变本轮 HVR `REJECTED` 结论，也不改变 CC-004/CC-005 原始记录。


## 2026-10-22 正常合法 XLSX 黄金链路复验（当前有效验收结论）

负责人正式驳回此前仅覆盖安全拒绝路径的 HVR 通过结论。本节记录本轮唯一测试输入 `real_valid.xlsx`；本轮没有运行任何伪装/异常文件测试。

| 步骤 | 实际结果 | 判定 |
|---|---|---|
| Python 生成合法工作簿并上传到内置 Odoo 聊天 | 草稿出现 `real_valid.xlsx` 附件卡片；发送后消息流保留该附件卡片 | PASS（上传与消息关联） |
| 聊天端正常 Office 处理 | Assistant 显示红色 `Attachment rejected`，文案为 “Office attachments are not available in this chat.”；调用未到内部 Office 服务，无处理状态或下载结果 | FAIL（黄金链路未通过；当前 fail-closed hook 在 handoff 前拒绝合法文件） |
| 拒绝后 UI | 输入框可编辑；浏览器 console error 为 0；刷新后用户消息、附件卡片和错误消息仍可见 | PASS（拒绝 UI 与持久性） |
| `office_core.inspect_document` 产品预算调用 | 当前 4 GiB 产品预算下返回 `OFFICE_RESOURCE_LIMIT`，macOS worker 无法落实地址空间上限 | FAIL（产品环境可运行性） |
| `office_core` / `office_verify` 功能探针 | 仅在 TV 功能探针的 2 TB 虚拟地址预算下，A1 读取、B1 写入、独立回读均 PASS | PASS（仅证明核心读写逻辑；不代表产品预算或 Odoo 请求封装通过） |
| `office.document.request` 同步封装 | 请求 `61` 持久化为 `failed / OFFICE_ENGINE_FAILED / inspect`，spawn 子进程报 `ModuleNotFoundError: No module named 'odoo.addons.office_core'`；无输出附件 | FAIL |

本轮完整 shell 结果见 [real_valid_xlsx_shell.log](evidence/real_valid_xlsx_shell.log)、[核心功能探针 JSON](evidence/real_valid_xlsx_core_probe.json) 和 [新 shell 清理复核](evidence/real_valid_xlsx_fresh_shell_postcheck.json)。内置浏览器已捕获上传草稿及提交后错误状态截图并在本轮 Codex 工具输出中呈现；当前 CUA 接口没有将图像字节导出到工作区文件的能力，因此仓库中没有伪造 PNG 路径。

**早期结论（保留）：** `real_valid.xlsx` 的该次正常文件链路复验为 `REJECTED`，其上传后被拒绝、未生成附件的结果不被改写。后续运行有新的成功证据，见下文；因此早期失败不再代表本次所有已验证样本的当前状态，也不能据后续单样本成功宣告 M1 整体验收通过。

## 负责人最终验收处置（2026-10-22）

负责人确认人工验证通过，并批准关闭 `CC-OFFICE-M1-006`。该决定作为 CC-006 冻结 MVP 范围的人工验收与关闭批准记录；本文件中前述特定自动/运行证据及其 `FAIL` / `REJECTED` 判定原样保留，不回填为 PASS。该批准不宣告 M1 整体、CC-004 成功生成路径或 CC-005 handoff 已通过。若后续阶段需要声明正常 Office 文件链路通过，仍须以对应修复后的新运行证据另行验收。

## 后续样本验证证据（2026-10-22）

- [复杂 Excel E2E 报告](../../../verification/Complex_Excel_Chat_Render_E2E_20261022.md)：记录真实浏览器上传、显式 Mapping、服务端生成与独立回读、聊天附件下载；公式、目标值、合并样式和隐藏工作表断言通过。原生 WPS/Excel 打开检查未验证。
- [复杂 Word E2E 报告](../../../verification/Complex_Word_Chat_Render_E2E_20261022.md)：记录服务端 DOCX 生成与回读通过，聊天页面显示输入/输出卡片；该报告明确浏览器别针上传、点击下载和原生 Word/WPS 打开未验证。
- 负责人已确认人工验收通过。上述证据仅支持各自报告中的样本和交互范围，不扩展为所有 DOCX 高级对象或旧版 `.xls/.doc` 均受支持。
