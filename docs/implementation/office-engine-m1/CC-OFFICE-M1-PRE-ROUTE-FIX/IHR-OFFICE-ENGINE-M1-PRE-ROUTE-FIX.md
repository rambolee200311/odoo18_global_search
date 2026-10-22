# IHR — CC-OFFICE-M1-PRE-ROUTE-FIX

## 1. 实施记录

| 字段 | 值 |
|---|---|
| Intent ID | `OFFICE-ENGINE-M1-PRE-ROUTE-FIX` |
| Coding Contract | `CC-OFFICE-M1-PRE-ROUTE-FIX v1.0.0 Frozen` |
| 实施基线 | 根仓库 HEAD `e91bf5a502b8970bfa9c795335e5ee2dce0e57b7`；工作区另有既存未提交变更 |
| Odoo 数据库 | `odoo18ce`（通过 `odoo-bin shell -c odoo.conf` 只读核验） |
| Python | 项目 `venv` |
| 实施日期 | 2026-10-21 至 2026-10-22 |
| 结果 | 代码及自动化测试完成；用户批准的 ORM 注入 + 内置浏览器 HVR 已完成；负责人于 2026-10-22 批准关闭 CC，FR SATISFIED |

## 2. 实施变更

在现有 `office_engine_odoo` 独立 Addon 中增加无状态附件身份分类 helper，并通过 `_inherit = "llm.thread"` 在新消息检查及 Provider 参数准备前复核历史附件。Office 扩展名、MIME 或 ZIP/OLE 签名任一表明可能属于 Office 的附件，都不会进入 Provider；身份冲突、无法安全读取或内容签名不匹配时以脱敏 `UserError` fail closed。拒绝消息设置现有 `is_error` 标志，避免下一轮历史上下文再次携带该消息。

签名读取仅通过当前用户可读的 Odoo 附件 filestore 路径读取最多 2048 字节；不调用 `sudo()`、`raw`、`datas`、完整 Base64 编码或 ZIP 解压。非 Office 普通附件通过闸门。

本次任务直接新增/修改的产品代码仅位于：

- `mymodules/office_engine_odoo/services/attachment_identity.py`
- `mymodules/office_engine_odoo/services/__init__.py`
- `mymodules/office_engine_odoo/models/llm_thread.py`
- `mymodules/office_engine_odoo/models/__init__.py`
- `mymodules/office_engine_odoo/tests/test_attachment_identity.py`
- `mymodules/office_engine_odoo/tests/__init__.py`
- `mymodules/office_engine_odoo/__manifest__.py`（版本升至 `18.0.1.1.0`）

没有为本 CC 修改 Odoo 官方源码、`mymodules/odoo-llm/**` 或其他 Addon。工作区在本次任务开始前已包含其他未提交变更；本记录不把它们归因于本 CC，也未对它们执行清理、暂存或提交。

## 3. 运行时与范围边界

当前 `odoo18ce` 中 `office_engine_odoo` 状态为 `installed`，`installed_version` 与 `latest_version` 均为 `18.0.1.1.0`；ORM 注册的 `_check_unsupported_attachments` 与 `_prepare_chat_kwargs` 扩展可见。模块升级通过既有 Odoo 界面完成，随后同一开发库上的模块测试通过。

本 CC 只拒绝 Office 附件，不提供 Office 内容读取、内部路由、文件转换或生成。CC-004 的 spawn/import 缺陷及其 FR 状态不在本次评估范围。CC-005 原有 handoff 测试状态仍为 BLOCKED / INCONCLUSIVE。

## 4. 后续验证补记（2026-10-22）

按负责人要求，补齐 CC-TEST-003 的有效最小 OOXML 与坏中央目录场景、CC-TEST-004 的真实 OpenAI message serializer 断言，并使用用户批准的服务端 ORM 注入方式完成 HVR：在空白线程 `llm.thread_48` 中构造伪装 Office 附件及消息，调用 `thread.generate()`，捕获 `UserError`、确认用户消息 `is_error=True`；为验证 UI 呈现，捕获异常后调用现有 `_post_error_message()` 创建 `is_error=True` 的机器人错误消息。内置浏览器截图中可见 Office 拒绝消息及普通附件/本地 stub 回复。普通附件未发给真实 Provider。

前端曲别针上传组件仍导致附件不进入草稿，因此 HVR 的 ORM 注入路径绕过了该前端行为。该偏差已在 HVR 中明确记录，不把它描述为上传链路 E2E 通过。HVR 结束后测试消息和附件均通过当前用户 ORM 删除；清理证明及精确 ID 见 `evidence/cleanup-proof.txt`。本轮没有清除或提交工作区内既存的无关修改；只会在提交时暂存本 CC 所属的明确文件。

## 5. 关闭记录（2026-10-22）

负责人批准关闭 `CC-OFFICE-M1-PRE-ROUTE-FIX`。批准依据为 ATR 中冻结测试矩阵 PASS、HVR 中经授权的 ORM 注入与内置浏览器可见性模拟，以及 FR 的 SATISFIED 判定。关闭不扩展 CC 范围、不代表上传组件缺陷已修复，不改变 CC-004/005 其他状态。
