# HVR — OFFICE-ENGINE-M1-SPAWN-REMEDIATION

## 状态

**未通过 / 未完成。** 本轮验证修复后的 Odoo 服务层生成链路；没有完成聊天界面“上传 → 内部 handoff → 生成 → 下载”的人工验收。

## 已观察到的界面状态

2026-10-22 在 Codex 内置浏览器查看现有 `llm.thread_48` 页面，页面仍显示先前上传的 `real_valid.xlsx` 消息及 “Attachment rejected / Office attachments are not available in this chat.” 错误。该消息属于既有验证记录；本轮未重新上传文件，也未点击发送或下载，因此不将其记为新一轮 UI HVR。

## 未通过原因与边界

- 本轮修复证明 `office.document.request` 能在 uid=2 的当前用户环境中完成读取、写入、独立回读和私有附件交付。
- `mymodules/office_engine_odoo/models/llm_thread.py` 仍按已冻结的 M1 MVP 设计，在 Provider 前拒绝所有 Office 附件。它尚未把聊天消息路由到请求服务。
- 当前聊天层没有从本轮自然语言请求生成合法 Mapping Plan 并触发生成的交互闭环。因此不能通过注入内部 Mapping 或绕过拒绝钩子来伪造 UI 成功。

## 后续验收需要

须先批准并实现聊天到内部 Office 服务的受控路由及 Mapping 输入来源；之后再用真实浏览器重新上传合成 XLSX，确认附件状态、生成结果下载入口、刷新持久性、错误/恢复行为及当前用户权限。服务层 shell PASS 不能替代该 HVR。
