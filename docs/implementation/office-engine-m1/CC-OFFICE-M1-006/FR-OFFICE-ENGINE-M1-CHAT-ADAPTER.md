# FR — CC-OFFICE-M1-006 聊天适配

## 状态

**CC-006 MVP 子范围 CLOSED（负责人批准，2026-10-22）；完整 SRS/M1 能力仍 PARTIAL。** 负责人确认人工验收通过。后续复杂 XLSX 样本的聊天生成/下载与回读通过；DOCX 服务端生成/回读通过，但对应报告未验证浏览器上传/下载。仍不据此宣称全格式、全结构或 M1 整体验收完成。

此前接受的子范围仅覆盖安全拒绝与错误 UI 适配。负责人随后正式驳回该 HVR 作为 M1 正常文件处理的验收证据。当前合法 `.xlsx` 已实际上传，但聊天仍在 handoff 前拒绝；产品预算下 core worker 失败，Odoo 请求封装 spawn 导入失败，未产生结果附件。

## 已验收

- 合成 Office 伪装文件通过 Odoo 聊天真实上传；草稿及消息流显示附件卡片。
- 服务端拒绝未通过安全校验的 Office 附件；拒绝路径不调用 Provider。
- 拒绝以当前线程可见的红色错误气泡呈现；刷新后仍可见。
- 错误后输入框恢复可编辑/可发送。
- 自动化测试证明被拒绝用户消息及错误回复不进入下一轮 Provider 上下文；普通 `.txt`/`.png` serializer 回归通过。
- 负责人已完成 HVR 人工确认；本轮合成消息、错误回复与附件已由 ORM 清理并在新 shell 会话复核。

## 明确移交 M2，不纳入本次 FR 关闭

- Mapping Plan 的用户输入/确认 UI。
- Provider 前到内部 Office 服务的成功 handoff 及跨用户全链路隔离。
- Office 结构读取、文件渲染、回读校验和结果附件回传。
- 多 Provider、成功生成场景、跨用户结果链接及相应端到端 UI 自动化。

## 保留的上游状态

CC-004 FR 仍为 `NOT SATISFIED`。CC-005 原始 FR 仍为 `NOT SATISFIED`，其 handoff 相关测试继续保留 `BLOCKED/INCONCLUSIVE`。本 FR 的 MVP 关闭不改变或覆盖上述状态，也不表示 Office 文档生成链路已完成。


## 当前正常文件链路状态

早期 `real_valid.xlsx` 运行在产品 4 GiB 预算下失败并记录于 ATR，结论不删除。随后 [复杂 Excel E2E](../../../verification/Complex_Excel_Chat_Render_E2E_20261022.md) 记录另一个合法复杂 XLSX 样本完成聊天上传、服务端读取/写入、独立回读和下载；[复杂 Word E2E](../../../verification/Complex_Word_Chat_Render_E2E_20261022.md) 记录 DOCX 服务端生成/回读通过，但浏览器上传/下载未验证。故单个 XLSX 样本的闭环有通过证据，完整 SRS/M1 FR 仍 **PARTIAL**，不能将样本结果推广至所有格式或结构。

## 负责人关闭批准

负责人于 2026-10-22 确认人工验收通过，批准按 CC-006 MVP 范围关闭本 FR。早期 `real_valid.xlsx` 失败、复杂 XLSX 后续成功样本以及 DOCX 验证限制均作为独立证据保留；本次关闭不改变 CC-004/CC-005 的原始状态，也不把未验证的格式能力标为通过。
