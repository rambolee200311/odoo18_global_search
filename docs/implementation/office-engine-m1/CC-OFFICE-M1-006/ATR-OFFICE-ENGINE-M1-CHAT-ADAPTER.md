# ATR — CC-OFFICE-M1-006 聊天适配

## 状态

**CC-006 状态：CLOSED（负责人批准，MVP 范围）。** 负责人于 2026-10-22 确认人工验收通过并批准关闭 CC-006。后续补充的复杂 XLSX 聊天生成/下载验证报告记录该样本链路通过；复杂 DOCX 服务端生成与聊天卡片可见，但其浏览器文件选择器和下载在报告中仍为未验证。该关闭不代表全部格式、全部模板或 M1 整体验收通过。

**技术证据按运行时间和范围分别保留：** `real_valid.xlsx` 的早期运行失败仍是历史记录；后续复杂 XLSX 正常上传、生成、下载与结构回读通过，见 [复杂 Excel E2E 报告](../../../verification/Complex_Excel_Chat_Render_E2E_20261022.md)。复杂 DOCX 的受控写入/回读及聊天附件卡片有服务端证据，浏览器上传/下载细节见 [复杂 Word 报告](../../../verification/Complex_Word_Chat_Render_E2E_20261022.md)。本次关闭不改写 CC-004/CC-005 历史状态，也不把单个样本结果推广为通用格式兼容承诺。

## 环境

- Odoo 18，项目解释器 `./venv/bin/python`。
- 配置 `odoo.conf`；数据库 `odoo18ce`；HTTP 端口 8091。
- 自动化命令：`./venv/bin/python odoo-bin -c odoo.conf -d odoo18ce -u office_engine_odoo --test-enable --test-tags /office_engine_odoo:TestAttachmentIdentity --stop-after-init --log-level=info --logfile=/dev/stdout`
- 浏览器：Codex 内置浏览器，真实已登录 Odoo 会话，线程 `llm.thread_48`。
- 合成测试文件：`cc006-spoofed.xlsx`，纯文本伪装文件，无业务数据。

## 自动化结果

Odoo 测试命令退出码为 `0`；`TestAttachmentIdentity` 共 11 项测试，`0 failed, 0 error`。覆盖 2048 字节头部读取限制、当前用户附件 ACL、MIME/签名矩阵、坏 ZIP/中央目录 fail-closed、真实 OpenAI message serializer 的 `.txt`/`.png` 结构、拒绝消息上下文隔离及普通附件 stub 路径。

| CC 测试 | 关闭状态 | 证据 / 处置 |
|---|---|---|
| CC-TEST-001 | ACCEPTED DEFERMENT | 负责人批准以 M1 UI 安全拦截 MVP 先行关闭 CC-006；CC-004、CC-005 原始门禁状态不变，Office handoff 和成功交付移交后续阶段。 |
| CC-TEST-002 | PASS | 内置浏览器真实选择并上传文件；草稿区显示准确文件名与 XLSX 卡片，提交后线程显示同一附件卡片。 |
| CC-TEST-003 | PASS（MVP 限定） | Office 伪装附件在 Provider 前被拒绝，自动化 Provider stub 调用为 0；内部 handoff 不属于本次 MVP，移交 M2。 |
| CC-TEST-004 | OUT OF SCOPE | M1 不提供用户 Mapping 输入 UI；文件生成与回读交付链路移交 M2 阶段验收。 |
| CC-TEST-005 | DEFERRED TO M2 | 跨用户请求状态、内部 handoff 与结果链接隔离随 M2 路由/生成链路验证；不声称本轮通过。 |
| CC-TEST-006 | PASS（MVP 场景） | 内置浏览器显示红色错误气泡；输入框恢复可编辑。自动化 Provider stub 验证拒绝消息及错误回复不进入下一轮上下文。未向真实 Provider 发送普通文本。 |
| CC-TEST-007 | OUT OF SCOPE | M1 阶段不提供用户 Mapping 输入 UI；文件生成与回读交付链路移交 M2 阶段验收。 |
| CC-TEST-008 | PASS（自动化回归范围） | `.txt`/`.png` 真实 serializer 与普通附件 stub 测试通过；未向真实 Provider 发送 UI 消息。 |
| CC-TEST-009 | NOT APPLICABLE | 当前开发环境仅启用 OpenAI Provider，其他 Provider 未安装，按规则不做覆盖推演。 |
| CC-TEST-010 | PASS（MVP UI 场景） | 用内置浏览器 Playwright API 完成真实上传、提交、错误显示、输入恢复和刷新后复查；本 MVP 不包含成功生成/跨用户结果链接场景。 |
| CC-TEST-011 | PASS | 负责人查看 UI 报错后，使用 ORM 清理本轮合成用户消息、错误回复及附件并 `env.cr.commit()`；新 shell 会话复核目标附件和错误消息均为 0。无临时 hook。 |
| CC-TEST-012 | PASS | 负责人已人工确认红色报错 UI 和输入框恢复。确认范围仅为本 MVP UI 场景。 |

## ORM 清理记录

- 使用 `./venv/bin/python odoo-bin shell -c odoo.conf -d odoo18ce`，未使用 `sudo()`。
- 线程 `llm.thread_48`：删除本轮合成用户消息 1 条、对应 `Attachment rejected` 回复 1 条，以及 `cc006-spoofed.xlsx` 附件 1 个。
- 显式执行 `env.cr.commit()`。
- 在新的 `odoo-bin shell` 会话验证：目标附件 0 条、对应错误回复 0 条；线程本身保留。

## 安全与上游状态

- 伪装附件拒绝不调用 Provider；测试未使用真实 Provider 请求或产生外部费用。
- 未记录 API key、文件正文、Base64 或绝对路径到聊天消息。
- CC-004 仍为 FR `NOT SATISFIED`；CC-005 原始 FR 仍为 `NOT SATISFIED`，handoff 测试仍保留 `BLOCKED/INCONCLUSIVE` 历史状态；均未改写为 PASS。
- 本次“特批先行”只关闭 CC-006 的 MVP 子范围，不授权开放 Office handoff 或宣告 M1 文档生成闭环完成。

## 结论

CC-006 按负责人批准的范围 **CLOSED**。负责人于 2026-10-22 确认人工验收通过。后续复杂 XLSX 报告补足了一个真实聊天上传→生成→下载样本的通过证据；复杂 DOCX 报告证明服务端生成/回读及聊天卡片显示，但报告所列浏览器上传/下载仍未验证。早期失败记录和各报告的限制均保留。单个样本通过不代表所有 Office 结构已支持；CC-004/CC-005 的正式状态仍不变。


## 补充运行：正常合法 XLSX 黄金链路（2026-10-22）

唯一输入为本轮生成的合法 `real_valid.xlsx`；未运行伪装或损坏文件测试。完整命令输出整理于 [shell log](evidence/real_valid_xlsx_shell.log)。

| 检查项 | 结果 |
|---|---|
| 内置浏览器选择文件、草稿显示、发送及消息附件卡片 | PASS；用户消息/附件持久化；刷新后仍可见 |
| 聊天正常 Office handoff | FAIL；当前 `llm.thread` 扩展在调用内部服务之前拒绝所有 Office 附件，返回红色 Attachment rejected；没有处理状态或结果下载链接 |
| 错误后可继续输入 | PASS；实际填写后清空验证可编辑；浏览器 console errors=0 |
| 产品预算下 `office_core.inspect_document` | FAIL；实际 4 GiB `ResourceBudget` 返回 `OFFICE_RESOURCE_LIMIT`，macOS 环境不能落实该地址空间限制 |
| `office_core` / `office_verify` 纯功能探针 | PASS（受限声明）；使用 TV 探针 2 TB 虚拟地址预算读取 A1、写入 B1 并 `office_verify=PASS`；不是产品安全预算证据 |
| Odoo 请求封装 | FAIL；记录 `request_id=61`，`failed_stage=inspect`，`OFFICE_ENGINE_FAILED`；spawn traceback 为 `ModuleNotFoundError: No module named 'odoo.addons.office_core'`，`output_attachment_id=False` |
| 清理 | 合成输入附件 6405 已以 uid 2 ORM 删除并提交；新 shell 复核附件不存在。失败请求 61 因 uid 2 无 `office.document.request.unlink` ACL 而保留作审计，状态 failed 且无输出附件；未使用 sudo |

截图已由内置浏览器工具捕获并在 Codex 对话工具结果中展示。该 CUA 运行时只返回图像对象，未提供本地 PNG 导出 API；因此截图尚未落盘到 `evidence/`，不伪称已保存文件。

### 当前总体判定

正常文件黄金链路为 **FAIL / NOT SATISFIED**：核心读写逻辑在功能探针预算下可工作，但当前 Odoo 产品预算、spawn 导入和 Provider 前聊天 handoff 三项均未通过；没有成功生成或交付的 Odoo 结果附件。原 CC-004 `NOT SATISFIED`、CC-005 handoff `BLOCKED/INCONCLUSIVE` 历史状态不变。
