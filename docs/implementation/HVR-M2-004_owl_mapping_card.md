# HVR-M2-004：Owl 映射卡片与 RPC 服务端校验

## 1. 验证元数据

| 字段 | 值 |
|---|---|
| Intent ID | `OFFICE-ENGINE-M2-004` |
| CC | `CC-M2-004` V1.0.0 Frozen |
| IHR / ATR | [IHR-M2-004_owl_mapping_card.md](IHR-M2-004_owl_mapping_card.md) / [ATR-M2-004.md](ATR-M2-004.md) |
| 环境 | 本机 Odoo 18，`odoo18ce`，项目 `venv`，`odoo.conf` |
| 浏览器 | Codex 内置浏览器（IAB），已登录 `Mitchell Admin` |
| 初始代码基线 | 测试时工作树基于 `edb550105a43e3a172a1ef362087593348b33055`；所测代码现已原样提交为 `24d6d4c7a7b28172c156c0b58b46fa1ef78b869d` |
| 执行辅助 | Agent 准备测试卡片；负责人通过内置浏览器完成并确认人工验收 |
| 当前 HVR 状态 | **PARTIAL — 负责人确认的卡片展示、字段选择、保存和确认通过；CC 要求的 HVR-SCN-003/004 未完整由人类执行** |

## 2. 验证要求与场景

| 场景 | 要求 | 当前结果 |
|---|---|---|
| HVR-SCN-001 专用卡片 | 聊天消息流显示受控映射卡片、只读目标和字段下拉；普通附件仍正常显示 | **PASS（人类确认）**；用户确认当前内置浏览器中的附件、目标与字段下拉 |
| HVR-SCN-002 真实编辑保存 | 选择后端提供的合法字段并保存，刷新后仍显示保存值 | **PASS（人类确认）**；选择 `name`、保存，服务端 revision 更新；见 HVR-EVD-005 |
| HVR-SCN-003 确认/取消与澄清 | 完整/不完整映射确认、取消和澄清均符合状态契约 | **NOT RUN（未完整）**；人类实际确认了完整映射；取消与不完整卡片补项未由人类验证 |
| HVR-SCN-004 错误恢复 | 拒绝旧 revision 后，再发送普通聊天消息并确认 composer 恢复 | **NOT RUN（未完整）**；Agent 观察了 stale 提示与 composer 可输入，但未以人类验证完成普通消息发送和 console 检查 |

负责人于 2026-10-23 在本对话明确回复“人工验证通过”。该签认仅覆盖本次实际打开的卡片、字段选择、保存和确认交互；不扩展为 HVR-SCN-003 的取消/不完整映射或 HVR-SCN-004 的完整错误恢复场景均已验证。

## 3. HVR-RUN-001（Agent-assisted）

| 字段 | 值 |
|---|---|
| 时间 | 2026-10-23 |
| 验证主体 | Agent（非人类签认） |
| 验证类型 | Tool-assisted functional browser simulation |
| 页面 | `http://127.0.0.1:8091/odoo/action-631?active_id=llm.thread_492` |
| 测试 Thread / Session | `llm.thread_492` / `office.mapping.session 169`；均为唯一标记合成数据，验证后已通过 ORM 删除 |
| 结果摘要 | PARTIAL — 浏览器交互观察完成；等待人类确认 |

### HVR-SCN-001：卡片显示

- **预期**：专用助手消息显示映射卡片、模板目标和候选字段下拉；上传附件用户消息仍呈现为常规附件卡片。
- **实际观察**：内置浏览器显示 `Review document mapping`、目标 `xlsx:Sheet1!B1`、必填标记、下拉选项 `display_name` 与 `name`；同线程用户附件仍正常显示。卡片消息不再把内部 `<p>` 标签显示为文字。
- **Agent 结果**：观察通过；**人类签认待办**。
- **证据**：`HVR-EVD-001`、`HVR-EVD-002`。

### HVR-SCN-002：选择、保存、确认和刷新

- **预期**：选择合法字段后，RPC 成功保存并反馈新 revision；用户明确确认当前 mapping revision；刷新后映射仍存在。
- **实际观察**：在下拉选择 `name`，点击 Save 后显示 `Mapping saved.`；点击 Confirm 后显示 `Mapping confirmed.`；读取当前页面后再次刷新，字段仍为 `name`，服务端记录曾达到 `confirmed_revision == revision == 3`。
- **Agent 结果**：观察通过；**人类签认待办**。
- **证据**：`HVR-EVD-001`。

### HVR-SCN-003：stale revision 与交互恢复

- **预期**：客户端旧 revision 更新被拒绝并显示受控提示；控件不永久 loading/disabled，普通聊天编辑区仍可用。
- **执行**：服务端用同一测试 Session 完成一笔竞争更新，将 revision 从 3 推进到 4；随后在仍持有 revision 3 的浏览器卡片点击 Save。
- **实际观察**：卡片显示 `The request was rejected or the session changed. Reload the card and retry.`；下拉、Save、Confirm、Cancel 仍呈现，聊天输入区可输入测试文本，随后清除；未发送消息，也未调用 LLM Provider。
- **Agent 结果**：观察通过；普通聊天消息发送路径未实际发送，故此部分不宣称验证通过；**人类签认待办**。
- **证据**：`HVR-EVD-002`。

## 4. 证据清单

| ID | 类型 | 场景 / Run | 位置 | 说明 |
|---|---|---|---|---|
| HVR-EVD-001 | 内置浏览器截图 | SCN-001/002，RUN-001 | Codex 当前任务的内置浏览器工具输出 | 显示附件、映射卡片、选择值及 `Mapping confirmed.`；工具输出截图已在本轮展示，未导出为仓库文件。 |
| HVR-EVD-002 | 内置浏览器截图 | SCN-003，RUN-001 | Codex 当前任务的内置浏览器工具输出 | 显示 stale revision 反馈，卡片控件仍可使用；工具输出截图已在本轮展示，未导出为仓库文件。 |
| HVR-EVD-003 | Odoo ORM 只读快照 | SCN-002/003，RUN-001 | `/private/tmp` 临时命令输出与本报告记录 | revision 3 确认后竞争更新至 revision 4；最终清理测试 Session、Thread、Attachment。 |
| HVR-EVD-004 | 内置浏览器截图 | SCN-001，RUN-002 | 本轮 Codex 内置浏览器工具输出 | 人工验证前显示线程 `llm.thread_517`、合成 `.xlsx` 附件、映射目标和字段下拉；截图未另存为仓库文件。 |
| HVR-EVD-005 | 人工签认 + 内置浏览器截图 + ORM 状态 | SCN-002，RUN-002 | 本对话用户确认、当前任务浏览器工具输出及 Odoo ORM 只读快照 | 用户明确回复“人工验证通过”；截图显示下拉为 `name`、状态 `Mapping confirmed.`；Session 为 `awaiting_confirmation`，revision 与 confirmed_revision 均为 3。 |

截图留存在本次 Codex 任务的工具输出中，未生成本地截图文件；因此本仓库报告没有伪造文件路径。

## 5. 人类签认 / 交接

- 负责人已确认 HVR-EVD-005 所覆盖的卡片显示、字段选择、保存和确认。
- HVR-SCN-003 的取消/不完整映射及 HVR-SCN-004 的完整人工错误恢复仍未完成；不得将其标记为 PASS。
- 自动化 `HttpCase.browser_js` 因环境缺少 `websocket-client` 被跳过，见 ATR；没有安装额外依赖。
- HVR-RUN-001 的合成 Session、Thread、Attachment 已在验证后清理。为本轮人类签认重新准备的 HVR-RUN-002 数据有意保留，详情如下。

## 6. HVR-RUN-002：人工验收准备

上一轮清理后，负责人打开的 `llm.thread_492` 已不存在于数据库，因此页面没有卡片。为避免再次清理掉待验收对象，现已在同一开发库创建并保留新的独立验收线程：

| 字段 | 值 |
|---|---|
| 状态 | **PASS — 本次 RUN 覆盖的卡片展示、字段选择、保存和确认已由负责人确认；不是全部 HVR 场景通过** |
| 覆盖场景 | HVR-SCN-001、HVR-SCN-002；HVR-SCN-003/004 未由本次人类 RUN 完整覆盖 |
| 页面 | `http://127.0.0.1:8091/odoo/action-631?active_id=llm.thread_517` |
| Thread / Session | `llm.thread_517` / `office.mapping.session 188` |
| 上传消息 / 卡片消息 / 附件 | `27886` / `27887` / `ir.attachment 7327` |
| 唯一标记 | `CC-M2-004-HUMAN-afa8a67c` |
| Owner | Mitchell Admin（user 2） |
| 人工结果 | 选择字段 `name` 并保存、确认；页面显示 `Mapping confirmed.` |
| ORM 结果 | state `awaiting_confirmation`，revision `3`，confirmed_revision `3` |
| 外部调用 | 无；该卡片由 ORM 准备，不会调用 LLM |
| 清理 | 验收后测试数据仍保留，供本次审阅复核；后续清理应使用唯一标记执行 ORM 删除 |

浏览器截图、负责人签认及 ORM 状态共同构成本次所覆盖场景的 HVR 证据。HVR 当前汇总保持 PARTIAL；CC 关闭处置及未通过项授权分别见 CC 附录 C、授权登记册和 FR，原场景状态不变。
