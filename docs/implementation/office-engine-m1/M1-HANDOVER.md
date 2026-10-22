# M1 阶段交付清单 — Office Engine

**交付状态：M1 整体验收仍为部分完成。负责人于 2026-10-22 确认人工验收通过并批准 CC-006 关闭；后续复杂 XLSX 样本的聊天生成/下载闭环通过，复杂 DOCX 服务端生成/回读通过但浏览器上传/下载未验证。**
**依据：** CC-OFFICE-M1-006 按负责人批准的 MVP 范围关闭，ATR/HVR/FR 已记录。CC-004 与 CC-005 历史状态保持原样。

## 已交付能力

1. **纯 Python 文件引擎底座**：功能探针能读 A1、写 B1 并通过 `office_verify`，但需 2 TB TV 专用预算；当前产品 4 GiB worker 预算在 macOS 返回 `OFFICE_RESOURCE_LIMIT`，不能据此宣告产品链路通过。
2. **Odoo Provider 前拦截钩子**：自有 `office_engine_odoo` Addon 可识别并安全拒绝当前不允许交给 Provider 的 Office 附件；拒绝路径不将文件字节发送给 Provider。
3. **聊天 UI 报错展示**：真实上传后，错误在当前线程以红色气泡呈现；刷新后仍显示，输入框恢复可编辑；拒绝消息不污染自动化验证的下一轮 Provider 上下文。
4. **普通附件回归**：自动化覆盖普通 `.txt` 和有效 `.png` 的 serializer / stub 路径。

## 遗留技术债与下一阶段

| 技术债 | 当前事实 | 后续处置 |
|---|---|---|
| 资源预算与 `spawn` 启动 | 早期请求 61 记录 `OFFICE_RESOURCE_LIMIT` / `ModuleNotFoundError`；后续复杂 XLSX 请求已 `generated`，并通过独立回读、聊天附件下载和内容断言 | 后续成功样本证明当前开发环境该链路已跑通；生产资源预算及更多样本/运行条件仍需分别验证 |
| Office 路由与 Provider 隔离 | 后续复杂 XLSX 在聊天中完成内部生成并交付；CC-005 的通用 Provider 路由 Spike 历史状态仍为 `NOT SATISFIED`，其他 Provider 未覆盖 | 保留 CC-005 原状；扩展 Provider 或改变路由前按其独立门禁补验 |
| 完整 M1/CC-004 验收 | 已有单个复杂 XLSX 端到端成功样本；复杂 DOCX 的服务端生成/回读通过，但浏览器上传/下载未由报告证明；旧版 `.xls/.doc` 仍未开放 | 按每个格式/结构的 capability gate 补验；完成 Mapping UI、权限矩阵和全量验收后再处置 CC-004/M1 状态 |

这些工作在本清单中列为 M2 后续任务；CC-004/CC-005 原始状态没有改写为 PASS，也没有通过本次 M1 MVP 关闭宣告其已完成。

## 本次验证与清理

- Odoo 18 自动化：项目 `venv`、`odoo.conf`、现有 `odoo18ce` 数据库；`TestAttachmentIdentity` 11 项测试通过。
- 内置浏览器验证合法文件真实上传、消息附件卡片、拒绝气泡、输入框恢复及刷新后持久性；负责人正式驳回其作为 M1 正常文件读写验收。截图在 Codex CUA 工具结果中显示，尚未导出为工作区 PNG。
- 功能探针 JSON：`CC-OFFICE-M1-006/evidence/real_valid_xlsx_core_probe.json`；产品请求失败和清理复核见同目录 shell 证据。
- 验收后以 `odoo-bin shell` ORM 删除合成附件及其用户/错误消息并提交；新 shell 会话确认目标记录数为 0。
- Odoo 服务按 `odoo.conf` 在 8091 端口运行。
