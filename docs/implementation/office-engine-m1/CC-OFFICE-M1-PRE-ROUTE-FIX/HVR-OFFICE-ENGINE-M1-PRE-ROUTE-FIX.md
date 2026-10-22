# HVR — CC-OFFICE-M1-PRE-ROUTE-FIX

## 1. 验证信息

| 字段 | 值 |
|---|---|
| 验证入口 | Codex 内置浏览器（IAB） |
| Odoo 页面 | `http://127.0.0.1:8091/odoo/action-631?active_id=llm.thread_48` |
| 测试线程 | `llm.thread_48`，此前确认为空白的专用验证线程；未操作用户原有业务对话 |
| Odoo 环境 | 数据库 `odoo18ce`，`odoo-bin shell -c odoo.conf`，项目 `venv`，当前用户 ORM |
| Provider | OpenAI 配置；真实 Provider 未调用。普通附件场景使用进程内 stub |
| 合成 Office 附件 | 名称前缀 `HVRPREROUTE`，纯文本伪装为 `.xlsx`；记录 ID 6309 |
| HVR 结果 | **PASS（按用户批准的 ORM 注入 + 浏览器可见性模拟）** |
| 验证日期 | 2026-10-22 |

## 2. 执行方式与偏差说明

内置浏览器曲别针上传组件仍存在缺陷：文件选择后服务端创建暂存附件，但聊天草稿不显示/保留附件。为了继续验证本 CC 的 Provider 前拦截和用户可见提示，按负责人明确指示绕过上传组件，使用当前用户的 Odoo ORM 在专用空白线程中创建合成附件及 `mail.message`，然后调用 `thread.generate()`。

`thread.generate()` 对伪装 Office 附件实际抛出 `UserError`，并将用户消息标记为 `is_error=True`；该执行路径不会自动持久化机器人错误消息。为完成 HVR 的可视化检查，脚本捕获异常后调用已有的 `_post_error_message()` 生成 `is_error=True` 的机器人错误消息，再在内置浏览器刷新线程核对渲染。因此本 HVR 证明“后端拒绝结果可由现有错误消息 helper 呈现在聊天 UI”，不证明曲别针上传 Bug 已修复，也不把手动错误消息构造描述为自然聊天请求的自动 E2E 行为。

普通附件回归同样由 ORM 构造当前用户消息（`text/plain` + `image/png`），通过真实 OpenAI 消息序列化断言，并使用进程内 Provider stub 运行生成路径；没有把消息发送到真实 Provider。

## 3. 浏览器可见结果

内置浏览器截图中可见：

- 用户伪装附件 `HVRPREROUTE…xlsx`；
- 机器人 `❌ Office attachment rejected` 错误回复，提示 Office 附件当前不支持；
- 普通文本与 PNG 附件卡片，以及本地 stub 的 `Local response okay` 回复；
- 页面无凭据、业务记录或真实附件内容泄露。

截图由本次 Codex 内置浏览器验证过程捕获并在验证会话中人工查看。截图没有作为独立二进制文件写入仓库；本 HVR 记录观察内容和对应 ORM 记录 ID，避免把当前已清理的空线程截图误作验证截图。

## 4. 断言结果

| 场景 | 结果 | 观察/证据 |
|---|---|---|
| ORM 创建伪装 `.xlsx`，调用 `thread.generate()` | PASS | 捕获脱敏 `UserError`：`This attachment is an Office file or its type could not be verified safely. Office attachments are not available in this chat.`；Provider dispatch 为 0 |
| 被拒绝的用户消息状态 | PASS | 消息 `26195` 的 `is_error=True` |
| 机器人错误回复状态 | PASS（模拟呈现） | 通过现有 `_post_error_message()` 创建消息 `26196`，`is_error=True`；内置浏览器可见错误回复。此 helper 是为 HVR 可视化而显式调用 |
| 普通文本与 PNG 附件 | PASS（stub 模拟） | 消息 `26197` 关联 text attachment `6310` 与 PNG attachment `6311`；真实序列化结构另由 CC-TEST-004 自动测试断言；stub dispatch 计数为 1 |
| 真实 Provider 外发 | PASS（未发生） | 未请求外部 Provider；只有测试进程内 stub |
| 曲别针上传草稿路径 | **仍有缺陷 / 不在本次 PASS 结论内** | 先前浏览器复测确认上传后草稿不呈现附件。本轮通过 ORM 注入绕过该路径，未验证其修复 |

## 5. 测试数据清理

HVR 完成后，使用 `odoo-bin shell -c odoo.conf` 当前用户 ORM 删除本次专用测试消息和附件并提交事务。消息 IDs `26195`–`26198`、附件 IDs `6309`–`6311` 的精确后查均为 0。未直接删除 filestore 文件；完整记录见 `evidence/cleanup-proof.txt`。

浏览器刷新后线程显示 `The conversation is empty.`。因此当前页面为空是预期清理结果，不代表 HVR 未运行。

## 6. 结论

在负责人批准的 ORM 注入替代路径下，服务器拒绝、用户消息错误状态、机器人错误回复记录、普通附件序列化/本地 stub 路径及浏览器可见错误均已验证。CC-TEST-007 按该受控模拟范围记为 **PASS**。负责人于 2026-10-22 批准关闭 CC。

仍需单独修复并验证 Odoo-LLM 前端附件上传草稿 Bug；本次 HVR 不覆盖该缺陷。真实 Provider 请求始终为零。
