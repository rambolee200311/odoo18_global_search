# ATR — CC-OFFICE-M1-PRE-ROUTE-FIX

## 1. 自动验证环境

| 字段 | 值 |
|---|---|
| 数据库 | `odoo18ce`（使用既有开发库） |
| 配置入口 | `odoo.conf` |
| Python | 项目 `venv` |
| Odoo HTTP 测试端口 | `8092`，`--stop-after-init` 结束后进程退出；开发服务 `8091` 未停止 |
| 本次自动测试源码起点 | 根仓库 HEAD `e91bf5a502b8970bfa9c795335e5ee2dce0e57b7`；验证期间工作树含本任务和其他既存未提交变更 |
| 模块版本 | `office_engine_odoo 18.0.1.1.0`，已安装且运行时继承方法可见 |
| Provider 验证 | 测试进程内 stub；无真实 Provider 请求 |
| 测试日志 | `/tmp/office_engine_pre_route_fix_final_tests.log` |

## 2. 执行记录

执行命令：

```sh
./venv/bin/python odoo-bin -c odoo.conf --http-port=8092 --stop-after-init \
  --test-enable --test-tags /office_engine_odoo:TestAttachmentIdentity \
  -u office_engine_odoo --max-cron-threads=0 \
  --log-handler=odoo.tests:INFO \
  --logfile=/tmp/office_engine_pre_route_fix_final_tests.log
```

进程退出码为 `0`。最新日志记录：`office_engine_odoo: 13 tests 0.47s 686 queries`，测试结果为 `0 failed, 0 error(s) of 11 tests`。统计行和结果行的用例数不同，原样记录日志口径，不据此推断额外测试数。Odoo 启动日志含三个与本 CC 无关的缺失模块警告：`wd_advanced_m2o_record_panel`、`wd_evidence_album`、`wd_qooling_app`；目标模块测试通过。

静态 Python 编译和目标文件 `git diff --check` 通过。测试只使用合成附件和 stub，不读写真实业务附件，不调用真实 Provider。

## 3. 测试结果矩阵

| 冻结 CC 测试 | 结果 | 证据与限制 |
|---|---|---|
| CC-TEST-001 类型矩阵 | PASS（已覆盖组合） | `test_identity_matrix` 覆盖 `.xlsx` + `text/plain` 纯文本失配、ZIP 文件头 Office 候选、`.txt` 与 PNG 不误判及扩展名/MIME 冲突；未穷尽所有扩展名/MIME 组合 |
| CC-TEST-002 重跑 CC-005 原始失败样例 | PASS | `test_spoofed_office_is_rejected_and_error_message_isolated`：合成 `.xlsx` + `text/plain` 纯文本在 Provider stub dispatch 前被 `UserError` 拒绝，dispatch 为 0，错误不回显正文 |
| CC-TEST-003 真实 OOXML 与坏中央目录 | PASS（按冻结范围） | `test_valid_minimal_ooxml_and_damaged_central_directory_fail_closed` 用标准库 `zipfile` 在内存创建含 `[Content_Types].xml`、`xl/workbook.xml` 的最小 `.xlsx`。网关将合法 ZIP/OOXML 文件头识别为 Office 候选而非 MIME/签名失配；按本 CC 的“Office 仍拒绝外发”策略在 Provider 前拒绝。随后破坏 Central Directory 签名，Python `zipfile` 独立读取验证抛 `BadZipFile`；闸门 fail closed，且通过 patch 断言未调用 ZIP parser。此测试验证候选识别和安全拒绝，不宣称对任意 OOXML 做完整解析 |
| CC-TEST-004 普通附件真实序列化 | PASS（serializer 自动化） | `test_ordinary_attachments_reach_real_openai_message_serializer` 创建普通 `text/plain` 与 `image/png` 上下文，调用真实 OpenAI `format_messages` dispatch，断言文本内容及 `data:image/png;base64,...` 图片结构正确，且未触发附件闸门错误。另由 HVR ORM 模拟显示普通附件路径；未调用真实 Provider |
| CC-TEST-005 跨轮次隔离/权限 | PASS（自动化路径） | 伪装附件拒绝后，同线程下一轮 mock history 不含拒绝消息、错误提示、附件引用或正文；门户用户读取私有附件得到 `AccessError`；未使用 `sudo()` |
| CC-TEST-006 外发及临时 hook | PASS（本地测试边界） | Provider 调用使用进程内 stub；无真实 Provider 凭据调用或外发请求。临时 patch 位于 `unittest.mock.patch` 上下文，测试退出后恢复 |
| CC-TEST-007 模块升级及浏览器 HVR | PASS（负责人指定的 ORM 注入模拟） | 当前 `odoo18ce` 模块版本和继承方法核验通过。经当前用户 ORM 创建伪装附件与消息后调用 `thread.generate()`，捕获 `UserError`、确认拒绝用户消息 `is_error=True`；再调用现有 `_post_error_message()` 生成错误机器人消息以验证 UI 呈现。IAB 截图中可见拒绝消息和普通附件/本地 stub 回复。此 HVR 绕过了仍有缺陷的前端文件上传草稿流程，不能证明曲别针上传已修复，也不是 UI 原生自动生成错误回复的端到端证明 |
| CC-TEST-008 有界读取/压缩限制 | PASS（头部读取范围） | `test_filestore_header_read_returns_at_most_2048_bytes` 使用 5 MiB 合成附件，断言仅读取 2048 字节；并确认拒绝路径不调用 `zipfile.ZipFile`。当前实现不做 ZIP 解压，因此单条 1 MiB/总计 5 MiB 解压上限路径未启用；不宣称验证了解压预算 |

## 4. 本轮新增自动化证据

- `test_valid_minimal_ooxml_and_damaged_central_directory_fail_closed`：有效最小 OOXML 不被当成纯文本类型冲突；破坏中央目录的候选被受控拒绝且不进入 ZIP 解析。
- `test_ordinary_attachments_reach_real_openai_message_serializer`：普通文本与图片通过真实 OpenAI 消息格式化函数，断言序列化字段和图片 data URL。
- `test_filestore_header_read_returns_at_most_2048_bytes`：改为 5 MiB 合成附件，仍只读取最多 2048 字节。
- 最新完整执行记录见 `evidence/ATR-RUN-002.md`；HVR 截图及实际 ORM/UI 观察见 HVR 文档。

## 5. 外部副作用、清理和工作树

- 无真实 Provider 请求；本地 stub 的 dispatch 仅按各测试断言执行。
- HVR 使用专用空白线程 `llm.thread_48`。合成 Office 测试消息/附件为 message IDs `26195`、`26196` 和 attachment ID `6309`；普通附件模拟消息 IDs `26197`、`26198` 和 attachment IDs `6310`、`6311`。HVR 测试专用记录及附件均已通过 ORM 清理并提交事务，精确后查均为 0；清理证据见 `evidence/cleanup-proof.txt`。未直接删除 filestore 文件。
- HVR 不发送真实用户消息；错误机器人消息由现有 `_post_error_message()` 在捕获 `UserError` 后用于 UI 可见性模拟。
- 整个仓库仍有本任务开始前存在的其他修改/删除/未跟踪内容。本次未清理、暂存或覆盖这些无关改动；因此不能声明全仓库工作树干净。仅在后续提交中纳入经核对属于本 CC 的文件。
- CC-005 handoff 项的 BLOCKED / INCONCLUSIVE 状态不由本 ATR 改写。

## 6. 结论

CC-TEST-003、004、007、008 的本次缺口已按用户指定的自动化测试及 ORM 注入 + 内置浏览器视觉模拟补齐；本 ATR 对这四项记为 PASS，并明确了 HVR 的模拟边界。负责人于 2026-10-22 批准关闭本 CC；FR 记为 SATISFIED。

仍需单独跟踪：Odoo-LLM 前端附件上传后草稿不渲染的问题；本次通过 ORM 注入绕过该路径，不构成其修复或验收。CC 关闭不改变 CC-005 内部 handoff 相关 BLOCKED / INCONCLUSIVE 和 CC-004 的既有 FR 状态。
