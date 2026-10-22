# ATR-RUN-002 — 自动化补测与 HVR ORM 模拟

日期：2026-10-22（Asia/Shanghai）

## 自动化补测

- 数据库：`odoo18ce`；配置：`odoo.conf`；Python：项目 `venv`。
- 命令：见上层 `ATR-OFFICE-ENGINE-M1-PRE-ROUTE-FIX.md` §2。
- 日志：`/tmp/office_engine_pre_route_fix_final_tests.log`。
- 退出码：`0`。
- 日志原文：`office_engine_odoo: 13 tests 0.47s 686 queries`；`0 failed, 0 error(s) of 11 tests when loading database 'odoo18ce'`。
- 新增测试：
  - `test_valid_minimal_ooxml_and_damaged_central_directory_fail_closed`：内存构造合法最小 OOXML，确认识别为 Office 候选；破坏 ZIP 中央目录后确认 `BadZipFile`，Odoo 闸门 fail closed 且未调用 ZIP parser。
  - `test_ordinary_attachments_reach_real_openai_message_serializer`：使用真实 OpenAI 消息格式化 dispatch 验证文本及 PNG 序列化形态。
  - 扩展 `test_filestore_header_read_returns_at_most_2048_bytes`：5 MiB 合成附件仍只读取 2048 字节，未调用 ZIP parser。
- Provider 外发：0。所有 LLM 调用均为本地 stub/格式化，不含真实凭据或外部请求。

## ORM 注入与内置浏览器 HVR

- 线程：`llm.thread_48`，专用空白验证线程。
- 当前用户经 ORM 创建伪装 Office 文件及关联消息；`thread.generate()` 抛出受控 `UserError`。
- Office 输入用户消息 ID `26195`，`is_error=True`；捕获异常后通过现有 `_post_error_message()` 创建机器人错误消息 ID `26196`，`is_error=True`。此错误机器人消息构造是为了 HVR 呈现验证，不是 `thread.generate()` 原生自动落库行为。
- Provider dispatch：Office 场景 `0`。
- 普通附件回归：用户消息 ID `26197`；text attachment ID `6310`；PNG attachment ID `6311`；本地 stub 机器人回复 ID `26198`；普通场景 stub dispatch `1`；真实 Provider 请求 `0`。
- 内置浏览器截图人工核对：页面显示 Office 拒绝提示、普通文本/PNG 附件及本地 stub 回复。截图由浏览器验证调用捕获并在任务对话中显示；未存成独立 PNG/JPEG 文件。曲别针上传草稿组件仍有缺陷，本 HVR 按用户授权以 ORM 注入绕过该组件。

## 清理

测试结束后以当前用户 ORM 删除以上 4 条消息和 3 个附件并提交事务；对精确 ID/测试名前缀的后续 ORM 查询均为 0。未直接触碰 filestore 文件。详情见 `cleanup-proof.txt`。
