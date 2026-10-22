# IHR — CC-OFFICE-M1-006 聊天适配

## 记录信息

| 项 | 值 |
|---|---|
| Intent | `CC-OFFICE-M1-006` |
| 实施状态 | CLOSED（负责人批准的 M1 MVP 范围） |
| 日期 | 2026-10-22 |
| 代码范围 | `mymodules/office_engine_odoo/` |
| Odoo 环境 | 项目 `venv`、`odoo.conf`、现有数据库 `odoo18ce`、HTTP 8091 |
| 阶段边界 | 本次 MVP 不开放 Office handoff、生成成功状态或结果链接；CC-004/005 仍按原历史状态记录并移交 M2 |

## 本轮实现

1. 在 `llm.thread.generate()` 的自有 Addon 扩展中捕获 Office 类型/签名拒绝，避免异常逃逸为未处理 SSE 错误；通过现有 `_post_error_message()` 写入当前线程的脱敏 `is_error` 助手消息。
2. 将 `is_error` 放入 `mail.message` store 数据，并在聊天消息组件上显示红色错误样式。
3. 保留拒绝用户消息及助手错误消息的上下文隔离；Office 字节不会交给 Provider。
4. 扩展 Odoo TransactionCase，覆盖拒绝消息、错误消息、Provider stub 零调用、下一轮正常文本不包含被拒绝消息/附件。
5. 更新 Addon 版本并注册前端资源；未修改 `mymodules/odoo-llm/**`、官方 Odoo 或官方 Addon。
6. 负责人已人工确认红色错误 UI 与输入框恢复；CC-006 按批准的 M1 MVP 范围关闭。
7. 用项目 `venv` 的 `odoo-bin shell -c odoo.conf -d odoo18ce` 清理 `llm.thread_48` 的合成附件、用户测试消息和错误回复，执行 `env.cr.commit()`；新 shell 会话确认附件/错误回复均为 0。

## 负责人关闭批准（2026-10-22）

负责人确认人工验收通过，批准按冻结 CC 的范围关闭 CC-006。后续复杂 XLSX 报告补充了上传、生成、回读和下载样本证据；复杂 DOCX 服务端生成与回读有证据，浏览器上传/下载仍按报告标为未验证。早期失败结果和 CC-004/CC-005 历史状态保持原样，不改写为 PASS。

## 移交 M2（不属于本次 MVP 关闭范围）

- Office 附件到内部 `office.document.request` 的成功 handoff、Mapping Plan 生成、文档渲染和结果附件回传。
- 跨 Provider 全量 payload 验证、全量权限验收、结果链接验收。
- 持久化 Playwright 测试套件及成功生成、跨用户结果链接等场景；本轮通过内置浏览器完成 MVP HVR。

## 实施基线说明

仓库工作树存在本任务之前的其他未提交改动。此次只修改 CC 允许的 `office_engine_odoo` Addon 与本 CC 文档；未清理、暂存或覆盖其他改动。具体文件状态以 `git status --short` 为准。
