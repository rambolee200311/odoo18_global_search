# ATR — M2 原生聊天最小重构

| 项目 | 结果 |
|---|---|
| 日期 | 2026-10-28 |
| 范围 | 恢复 `llm_assistant` 原生消息/工具循环；Office 文本与附件二进制分离；服务端工具和数据权限；单个 `.xlsx` 直接映射预览 |
| 状态 | 自动化验收通过；隔离真实 Provider 预览通过；浏览器人工验收未执行 |
| Provider | OpenAI `gpt-5.6-luna` |
| 数据库 | 隔离库 `m2_native_full_20261027_1`；合成联系人和合成 `.xlsx` |

## 执行摘要

M2 的 Office 消息现在进入原生 `llm.thread.generate()` 和 `llm_assistant.generate_messages()` 循环。模型通过原生工具调用识别业务记录、准备绑定当前 Thread 的映射 Session、提交 Proposal 并请求 M1 预览。后端继续负责用户/公司权限、获准字段、模板目标、Proposal Schema、revision、M1 回读验证和最终生成确认。

真实隔离运行中，`gpt-5.6-luna` 依次调用 `odoo_record_retriever`、`office_prepare_context`、`office_save_mapping_preview`，随后给出自然语言答复。生成的预览附件经 ORM 回读，`Sheet1!B1` 含合成联系人名称；文件名和 XLSX MIME 正确。用户文本中的 B4 条件回退被说明为首期不支持；测试没有调用正式生成。

过程中发现并修复了一个真实工具循环断链：M2 对 `_execute_tool_call()` 的扩展只转发事件，没有返回父类工具执行结果，原生循环因此停止在工具回复处。新增回归测试先失败（第二次 Provider 调用数为 1），修复后通过（第二次 Provider 调用数为 2）。真实 Provider 首次提交的映射还暴露了通用 `dict` 参数 Schema 过宽的问题；工具 Schema 已改为明确的 `m2.mapping-proposal.v1` 结构，并在下一次真实调用中成功生成预览。

## 新的调用链

```text
用户消息/Office 附件
  -> office_engine_odoo 预检（签名、宏、大小）
  -> llm.thread.generate（原生：只发布一次用户消息）
  -> llm_assistant.generate_messages（原生历史、Provider 与 Tool 循环）
  -> gpt-5.6-luna
      -> odoo_record_retriever（复用 ORM 检索并执行 M2 数据策略）
      -> office_prepare_context（绑定 Thread、用户、公司、模板和目标记录）
      -> office_save_mapping_preview（Schema/白名单/revision 校验 -> M1 -> office_verify）
  -> 原生助手根据工具结果回复
```

Office 文件仍附在原始用户消息上供服务端检查，但 `mail.message` 序列化边界排除 Office 附件内容。真实 Provider 请求保留了完整用户文字，未包含附件字节或 Base64。

## 代码改动

- `mymodules/office_engine_odoo/models/llm_thread.py`：移除“只检查并回复已接收”的专用生成分支。保留 Office 安全预检，合法文件交由原生助手；保留消息历史与用户正文，Office 附件在 Provider 序列化处剔除。
- `mymodules/office_engine_odoo/models/office_document_request.py`：提取可复用的服务端 Office 检查入口。
- `mymodules/office_engine_m2/models/llm_thread.py`：Office Thread 工具绑定、原生 Assistant handler、非流式 Usage 记录、Retriever 服务端策略及工具 Schema。修复 `_execute_tool_call()` 返回值传递；为 `gpt-5*` 工具调用设置 `reasoning_effort=none`。
- `mymodules/office_engine_m2/models/office_mapping_tools.py`：Prepare/Get Context、Save Mapping & Preview、Finalize 工具。预览只在规则发生变化且验证通过时创建；Finalizer 校验最新消息中的明确确认、Session 和 Proposal revision、数据新鲜度及幂等键。
- `mymodules/office_engine_m2/data/office_tools.xml`：以数据文件注册原生工具。
- `mymodules/odoo-llm/llm_openai/models/openai_provider.py`：将可选 `reasoning_effort` 转交 OpenAI Chat Completions SDK；这是项目自有 `odoo-llm` 扩展，不是 Odoo 官方源码。
- 测试：新增/更新 `test_native_chat_integration.py`、`test_conversational_preview.py`，覆盖正文与附件分离、工具 Schema、权限拒绝、原生工具循环和无预览副作用。

聊天入口不再做本地 question/correction/confirm/ambiguous 意图分类，也不在每条纯文本消息上拦截后自行调用 Provider。旧 `ai_orchestrator.run_mapping()` / `revise_mapping_from_chat()` 及其 Provider/helper 代码仍留在服务模块中，但当前 `llm.thread` 原生聊天路径没有调用它们；其他旧 RPC/服务是否仍由部署使用，需另行盘点，故本报告不宣称这些遗留代码已删除。

## 真实 Provider 证据

运行位置为隔离 Odoo DB 与独立 filestore，仅使用一条合成 `res.partner` 记录和内存生成的 `.xlsx`。安全策略仅允许 `res.partner.name`。真实 Provider 调用数为 4，四次请求均通过 SDK 边界检查：

```text
model=gpt-5.6-luna
original_instruction_in_actual_user_payload=true
office_attachment_bytes_present=false
base64_marker_present=false
reasoning_effort=none
tool responses: odoo_record_retriever -> office_prepare_context -> office_save_mapping_preview -> assistant text
tool result statuses: completed, completed, completed
finalize_called=false
```

最终助手实际解释：B1 已映射到 `name`，B4 条件回退不受支持；未调用正式生成工具。隔离库中预览复核结果：

```text
status=preview_ready
filename=preview_document_synthetic-office-context.xlsx
mimetype=application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
size=4982 bytes
Sheet1!B1=<本次合成联系人名称>
```

真实 Provider 运行日志：`/private/tmp/m2_native_live_preview_spike_v3.log`。SDK 边界的脱敏证据由本 ATR 记录；日志和输出均未包含 API Key。测试结束后，已清除隔离 Provider 记录中复制的 API 凭据。早期实测中，Provider 拒绝了缺少 `reasoning_effort=none` 的 GPT-5 工具请求；修正后真实请求成功。另一次模型提出不符合 Schema/模板清单的 Proposal 被拒绝，没有生成附件；工具 Schema 和清单指令修正后才通过，失败结果未被隐藏。

## 权限与能力边界

- Office Retriever 复用现有 `odoo_record_retriever` ORM 实现；Office Thread 上附加模型/字段策略、记录过滤、公司域、当前用户 ACL/字段访问及 Session 绑定检查，不以 Prompt 取代服务端授权。
- 当前真实 Provider 运行只授权合成数据的 `res.partner.name`，没有读取共享库业务记录。
- 首个预览切片是单个 `.xlsx` 的直接字段映射。空值回退、条件、公式、重复行和 `.docx` 映射未开放；模型提出 B4 条件回退时，服务端拒绝该规则，模型向用户说明。
- 正式生成代码要求用户在当前 Thread 发出精确确认文本，并检查 owner、company、revision、新鲜度和幂等。真实 Provider 测试明确禁止 Finalize；本次未生成正式文件。

## 自动化验证

| 验证 | 结果 | 证据 |
|---|---|---|
| `office_engine_m2` 全量 TransactionCase | PASS：`0 failed, 0 error(s) of 89 tests`；Addon stats 显示 117 tests、81.87s、7305 queries | `/private/tmp/m2_native_full_final_20261028_r2.log` |
| 原生工具循环返回值回归 | PASS；修复前新增断言失败（Provider 调用 1 次），修复后测试通过 | `/private/tmp/m2_native_return_regression.log`、`/private/tmp/m2_native_return_regression_pass.log` |
| 原生工具 Schema + Session/Thread 绑定 | PASS：定向 2 tests，0 failure/error | `/private/tmp/m2_native_schema_tests.log` |
| `office_mapping_verify` pytest + branch coverage | PASS：80 tests；351 statements、174 branches，100% statement/branch coverage | pytest 终端结果 |
| `office_core` Python tests | PASS：23 tests | pytest 终端结果 |
| `compileall` / `git diff --check` | PASS | 执行结束码 0 |

全量 Odoo suite 中一个已有 `HttpCase` 因环境缺少 `websocket-client` 被跳过；测试没有安装依赖。测试运行在隔离数据库 `m2_native_full_20261027_1` 和其 filestore 下，未对共享 `odoo18ce` 做测试写入。

## 尚未完成 / 证据边界

1. 未在 8091 聊天页面执行真实浏览器流程或截图；因此不宣称 UI 人工验收通过。原因是本轮硬门禁聚焦隔离 Provider/工具/数据边界，且全量 HttpCase 因缺少 `websocket-client` 跳过。
2. 未通过真实 Provider 执行最终确认/正式文件生成；生成需要独立、明确的人类确认。本次 Provider 提示明确禁止 Finalize。
3. 未验证其他 Provider。当前模型真实证据只对应 OpenAI `gpt-5.6-luna`。
4. 原有未提交工作树保持 dirty；没有 reset、stash、clean、commit、push，也没有修改官方 Odoo 源码或重启 8091 服务。

## Git 状态

变更仍在现有工作树中，未提交。工作树原先已有大量 M1/M2 未提交及未跟踪文件，本轮没有清理或回滚它们。`git diff --check` 通过。
