# HVR — M2 原生聊天真实 Provider 预览验收

| 项目 | 记录 |
|---|---|
| 状态 | **模拟验证通过；等待负责人人工验收** |
| 日期 | 2026-10-28 |
| Odoo | 本机开发库 `odoo18ce`，HTTP 8091 |
| Thread | `llm.thread_4404` |
| Provider / Model | OpenAI / `gpt-5.6-luna` |
| 范围 | 合成 XLSX、单个当前公司名称字段、真实 Provider Tool Calling、M1 预览及回读 |
| 正式生成 | 未执行 |

## 验证摘要

在 8091 的真实聊天页面输入自然语言请求。日志确认请求实际发送到 `https://api.openai.com/v1/chat/completions` 并返回 HTTP 200；未使用本地 Mock Provider。模型在原生聊天循环中依次调用 `odoo_record_retriever`、`office_prepare_context` 和 `office_save_mapping_preview`。最后一个工具返回 `status=preview_ready`，聊天消息中出现了绿色 XLSX 附件卡片。

M1 预览附件为 `preview_document_office-openai-hvr-template-styled.xlsx`（附件 ID `14340`，MIME `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`）。通过当前用户的只读 ORM 回读该 XLSX，确认 `Sheet1!B1` 为 `My Company (San Francisco)`。Session `3782` 处于 `confirmation_required`，`revision=4`、`proposal_revision=1`、`preview_proposal_revision=1`。没有调用 Finalize，也没有生成正式交付文件。

## 测试输入与数据范围

- 本地合成模板：`/private/tmp/office-openai-hvr-template-styled.xlsx`；A1 是“公司名称”，B1 是显式序列化且带样式的空白目标。
- Provider 可见的业务值仅为当前公司 `name`；另有 Odoo 工具绑定所需的技术记录 `id`。未读取或发送销售订单、客户、地址或订单明细。
- 本次 Odoo 进程临时外发字段基线为 `res.company: id, name`；没有改写项目配置文件。

## 执行经过与真实结果

1. Thread 4404 显示 Provider `OpenAI`、Model `gpt-5.6-luna`。初次真实调用时，服务端外发字段基线仅允许 `name`，拒绝 Retriever 要求的技术字段 `id`；未读取数据。
2. 将本机 8091 进程的临时策略范围调整为 `res.company.id` 与 `res.company.name`，业务字段仍仅为公司名称。随后模型先因空检索域被服务端拒绝；没有扩大查询。
3. 为使模板具有真实可写目标，合成模板改为显式包含带样式的空白 B1。该合成文件通过 Odoo ORM 挂载到 Thread 4404；浏览器附件选择按钮未打开文件选择器，因此**附件上传并非浏览器实操**。
4. 用户指令通过 8091 页面输入并发送。真实 OpenAI Tool Calling 成功读取当前公司，准备模板上下文，提交直接字段 Proposal，调用 M1 渲染并完成回读验证。最终聊天中显示预览附件卡片；生成文件实测 B1 值正确。

## 验收证据

- Odoo 日志：`/private/tmp/office_engine_8091_real_hvr_20261028_r2.log`。含真实 OpenAI 请求的 HTTP 200、Retriever 实际参数及生成循环结束记录。
- 聊天页面：当前 Codex 会话中已展示 8091 的真实 Tool Call 成功状态、`preview_ready` 返回 JSON 和 XLSX 附件卡片。截图是本轮会话中的浏览器捕获，未另存为仓库文件。
- 持久化回读：Thread `4404`、Session `3782`、预览附件 `14340`；`Sheet1!B1 = My Company (San Francisco)`。
- 8909 Mock 端口：验收完成后没有监听进程；8091 由 PID `42005` 保持监听。

## 结论与人工验收范围

真实 Provider → 原生 Tool Calling → Odoo Retriever → Office Context → Mapping Preview → M1 写入/回读的合成单字段路径，**模拟验证通过**。本结果不代表真实 CMR 模板、销售订单、复杂映射或浏览器文件选择上传通过。

请负责人在 8091 当前 Thread `4404` 检查并下载预览附件，确认聊天表现和文件内容。当前页面保留在附件卡片处；人工确认尚未收到。
