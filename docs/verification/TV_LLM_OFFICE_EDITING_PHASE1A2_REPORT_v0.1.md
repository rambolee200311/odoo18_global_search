# Office Engine M2 — Candidate B Responses API / Code Interpreter 验证报告 v0.1

| 项目 | 结果 |
|---|---|
| 报告状态 | **G0 BLOCKED — 文档/SDK只读核查完成；真实 API 调用未执行** |
| 验证范围 | Candidate B API、模型与 SDK 能力发现；不含 Odoo 集成 |
| Responses API / XLSX 文档能力 | `SUPPORTED` |
| Code Interpreter / XLSX 文档能力 | `SUPPORTED` |
| `gpt-5.6-luna` 官方模型兼容性 | `SUPPORTED`（文档声明） |
| 当前 API Project 权限 | `UNVERIFIED` |
| 实际 XLSX 编辑 / 下载 / 独立回读 | `NOT RUN` |
| Provider 请求数 | 0 |
| 报告日期 | 2026-11-06 |

## 1. 结论摘要

官方 OpenAI 文档现在明确给出 Responses API 文件输入、Code Interpreter、XLSX MIME 支持及容器文件下载方式；官方 `gpt-5.6-luna` 模型页也列出 Responses endpoint 与 Code Interpreter 工具支持。当前安装的 OpenAI Python SDK 2.54.0 含 Responses、Files、Containers 资源以及容器文件内容下载方法。因此，Candidate B 的**公开接口和 SDK 路径在技术上可行，值得在门禁满足后继续最小 TV**。

但本次没有独立 TV 执行批准、针对独立 Responses/Code Interpreter 路径的 Project/资源/操作窗口批准，亦未能确认当前 Project 的工具权限及合成 XLSX 的发送/留存政策。`OPENAI_API_KEY` 不在当前 shell 环境中；没有访问数据库或其他凭据存储来检查密钥。按 G0 规则没有尝试调用 API、创建上传文件或 Code Interpreter 容器，也没有创建本轮输入夹具。故模型兼容性是**官方文档结论**，不是本 Project 的运行证明；本次实际 XLSX 编辑、文件下载和回读均为 `NOT RUN`，不得判 Phase 1A-2 PASS。

此前 `TV_LLM_OFFICE_EDITING_PHASE1_REPORT_v0.1.md` 的结论保持不变：当前 `odoo-llm` Chat Completions 集成路径拒绝 XLSX，且没有接收编辑文件的响应链路。本报告验证的是另一条公开 Responses API / Code Interpreter 路径，不推翻或改写前一报告。

## 2. G0 门禁

| 门禁 | 状态 | 证据与说明 |
|---|---|---|
| Git 状态 | `PASS`（仅记录） | 分支 `main`；HEAD `f9801fca76f7c248a9cc823c583138ab0191b978`，`origin/main` ahead 1。存在上一任务前已登记的 `.coverage` 及多个未跟踪审计/设计/TV 文档；均保留。没有暂存、提交、推送、清理或重置。 |
| 权威 TV 计划 | `FROZEN — NOT AUTHORIZED FOR EXECUTION` | `docs/verification/TV_LLM_OFFICE_EDITING_PLAN_v0.2.1.md` §4 和 §9 明确要求单独 TV 执行批准；计划冻结不等于执行授权。 |
| 本次 Responses API 路线执行批准 | `BLOCKED` | 当前材料没有找到明确批准本独立 API 路径、评估人员及操作窗口的记录。本次任务明确要求不得把自身作为绕过门禁的依据。 |
| 合成文件 Provider 数据政策/留存 | `BLOCKED` | 未取得允许上传合成 XLSX 到本 API Project、文件保留和删除方式的本次确认。官方文档说明文件默认会保留直至手动删除（除非设置过期策略）；容器不活跃 20 分钟后过期。此为供应商文档信息，不代表本项目数据政策批准。 |
| Provider Project 权限 | `UNVERIFIED` | 本次未请求 API，无法确认 Project 对 Responses、Code Interpreter、文件输入/输出或计费的权限/额度。当前 shell 未设置 `OPENAI_API_KEY`；未查询应用数据库/密钥存储。 |
| 测试资源、费用与窗口 | `BLOCKED` | 没有本次调用预算/费用上限及获批测试窗口的证据。实际请求数为 0；没有用量或账单结果，实际费用金额未核实。 |
| 模型基线 | `PARTIAL` | 冻结 TV 计划将批准模型定义为 `gpt-5.6-luna`；官方模型页确认此模型支持 Responses 和 Code Interpreter。但 8091/当前 Project 的实际配置模型尚未确认。没有切换模型。 |
| Python / SDK / XLSX 回读库 | `PASS`（本地可用性） | 当前 Python 为 3.11.9；OpenAI SDK 2.54.0、openpyxl 3.0.9 可导入。SDK 包含 `responses`、`files`、`containers` 资源和容器文件内容 `retrieve` 方法。没有创建 API 客户端发起请求。 |
| 测试夹具 | `NOT READY` | 已有 `docs/verification/evidence/TV_Office_Engine_M2/synthetic_prompt_injection.xlsx` 不符合本次双工作表/数据/公式夹具规格（前报告记录其 SHA-256 和结构）。本轮没有新建 `tv_phase1a2_input.xlsx`，也没有覆盖历史证据。 |

**G0 总判定：`BLOCKED`。** 允许并完成了公开官方文档及本地 SDK 的只读核查；不允许执行任何 Provider 请求。API Key 内容未读取、打印或记录。

## 3. 官方 API 与 SDK 能力核实

### 3.1 官方公开能力

| 能力层 | 结论 | 官方资料与边界 |
|---|---|---|
| Responses API 接口 | `SUPPORTED` | 官方 API 文件输入指南说明 Responses 支持 `input_file`，支持 `file_id`、`file_data` 等输入方式；Chat Completions 的文件内容仅支持 PDF。该资料不是本地 `odoo-llm` 集成已实现的证据。 |
| XLSX 输入 | `SUPPORTED` | 官方文件输入指南列明 `.xlsx` / Excel MIME；电子表格会经过专用解析增强，并且模型上下文解析每张表最多覆盖前 1,000 行。官方提示单文件及单请求所有文件合计上限为 50 MB。文件可作为 Responses `input_file` 的 `file_id` 或 `file_data` 提供；若用 Files API 预上传，官方建议 purpose=`user_data`。超过解析行范围的工作簿行为不能由本次文档能力推为已验证。 |
| Code Interpreter | `SUPPORTED` | 官方指南定义为 Responses API 中的沙箱工具，可处理文件并生成文件；明确列出 `.xlsx` 及其 MIME。官方说明可自动创建或复用容器，内存级别包括默认 1 GB 和 4/16/64 GB；容器 20 分钟不活跃后过期。 |
| 输入文件进入执行容器 | `SUPPORTED`（文档契约） | 官方指南说明模型输入中的文件会自动加入 Code Interpreter 容器；也可在容器配置中提供文件 ID。未在本次验证 Project 能否执行。 |
| 输出文件标识及下载 | `SUPPORTED`（文档契约） | Code Interpreter 产物通过助手消息的 `container_file_citation` 注解给出 `container_id`、`file_id`、`filename`；使用 `GET /v1/containers/{container_id}/files/{file_id}/content` 返回二进制内容。未实际取得任何文件 ID 或字节。 |
| `gpt-5.6-luna` 支持 | `SUPPORTED`（官方声明） | 官方模型页列出 `v1/responses` endpoint，以及 Code Interpreter 工具。此为模型目录能力声明，不代表当前 API Project 获准或本例成功。 |
| 当前 API Project 调用权限 | `UNVERIFIED` | 未发起认证请求，无法判断组织/Project 是否已启用该模型、工具、文件上传/下载或对应计费层级。 |

官方资料：

- [Responses API File inputs](https://developers.openai.com/api/docs/guides/file-inputs)
- [Code Interpreter tool](https://developers.openai.com/api/docs/guides/tools-code-interpreter)
- [GPT-5.6 Luna model page](https://developers.openai.com/api/docs/models/gpt-5.6-luna)
- [Upload file API](https://developers.openai.com/api/reference/resources/files/methods/create)
- [Retrieve container file content API](https://developers.openai.com/api/reference/resources/containers/subresources/files/subresources/content/methods/retrieve)

以上页面于 2026-11-06 只读查询。官方文档中描述的上传文件默认保留至手动删除，除非配置 `expires_after`；这使数据保留政策确认成为执行前门禁，而不是默认安全结论。

### 3.2 当前安装的 SDK 与仓库集成

- Python SDK `openai==2.54.0` 的本地类型/资源实现包含 `OpenAI.responses.create`、`OpenAI.files.create`、`OpenAI.containers.create`，以及 `containers.files.content.retrieve`（例如 `openai/resources/responses/responses.py`、`openai/resources/containers/containers.py`、`openai/resources/containers/files/content.py`）。仅证明 SDK 调用入口存在。
- 仓库当前 `mymodules/odoo-llm/llm_openai/models/openai_provider.py` 使用 `client.chat.completions.create()`；上传辅助方法使用 `client.files.create(... purpose="fine-tune")`。它没有将 XLSX 用 `user_data` 上传后接到 Responses/Code Interpreter，也没有解析 `container_file_citation` 或取回生成 XLSX 的实现。
- 前报告中 Office MIME 被当前 Chat Completions 消息路径拒绝的静态事实保持有效。Phase 1A-2 的 Responses 能力是**另一个尚未接入、尚未运行的接口路径**。

## 4. 模型、Project 权限和实际执行结果

| 判定层 | 结果 | 依据 |
|---|---|---|
| Responses API 接口可用性 | `SUPPORTED` | OpenAI 官方 Responses API 文档。 |
| Code Interpreter 工具可用性 | `SUPPORTED` | 官方 Code Interpreter 文档支持该工具及 XLSX MIME。 |
| `gpt-5.6-luna` 模型兼容性 | `SUPPORTED`（文档） | 官方模型页列出 Responses 和 Code Interpreter。没有实际请求验证。 |
| 当前 Project 权限 | `UNVERIFIED` / 执行 `BLOCKED` | 无安全可用凭据证据；未认证调用，无权限或额度响应。 |
| 实际 XLSX 编辑 | `NOT RUN` | 没有合成文件上传，没有模型/Code Interpreter 执行。 |
| 文件下载 | `NOT RUN` | 没有响应、容器 ID、容器文件 ID或输出字节。 |
| 独立回读 | `NOT RUN` | 没有输出候选；openpyxl 仅确认可用。 |

本次 Provider 请求 ID、Response ID、Code Interpreter 工具调用 ID、文件 ID、输入/输出 SHA-256、请求耗时、Token usage 及 API 费用均为 **N/A（未产生/未测量）**，不能解读为一次零耗时或零费用调用。

## 5. Phase 1A-2 最小编辑验收

没有执行测试指令“将 ITEM-A Quantity 从 10 改为 15”。没有输入/输出夹具，没有下载文件，没有断言可执行。以下均为 `NOT RUN`：

| 独立回读断言 | 预期 | 实际 |
|---|---:|---|
| `Inventory!B2` | 15 | N/A — no output |
| `Inventory!B3` | 20 | N/A — no output |
| `Inventory!D2` / `D3` | 原公式保留 | N/A — no output |
| `Notes!B2` / `B3` | 合成值保留 | N/A — no output |
| Sheet 名称、非目标内容、ZIP 有效性、格式/结构差异 | 保持预期 | N/A — no output |

因此本次不存在用于判定“实际 XLSX 编辑 PASS”的任何输出字节、文件哈希或回读断言。

## 6. Candidate B 决策与后续门禁

**建议：Candidate B 值得继续 TV，但目前不能进入真实调用。** 官方文档和本地 SDK 已证明技术调用表面存在，且官方文档声明 `gpt-5.6-luna` 兼容 Responses/Code Interpreter；但 Project 授权、配置凭据、测试资源和合成文件数据保留政策未证实。尚无证据说明 API Project 拒绝或成功调用，不能把当前阻塞定性为模型不支持。

继续最小测试前，需取得/记录：

1. 负责人对 Responses API / Code Interpreter 路径、测试人员和操作窗口的明确 TV 执行批准；
2. 本次合成 XLSX 上传、提供商保留/到期及清理方式的批准；
3. API Project 标识与模型/工具/Files 权限的只读确认，以及经安全配置可用的凭据检查（不显示密钥）；
4. 费用/用量上限及资源批准；
5. 获准的 evidence 目录、输入夹具预期清单和候选清理/保留要求。

以上条件满足后，才可依任务步骤创建合成夹具、发起一次真实请求、下载二进制文件并由 openpyxl 独立验证。未授权前不执行多轮编辑或 Candidate C。

## 7. 执行记录与工作区保护

- 已执行：读取三份指定基线文档；检查分支、HEAD、工作区；只读检查当前 OpenAI SDK 类型/资源入口及仓库 API 调用路径；查询 OpenAI 官方 API/模型文档；确认 Python 和 openpyxl 可导入；仅检查 `OPENAI_API_KEY` 环境变量是否存在（结果为否，未读取任何密钥值）。
- 未执行：API 请求、Project/权限探测请求、文件上传、容器创建、Code Interpreter 调用、输入夹具创建、输出下载、测试脚本运行、Odoo/数据库/浏览器操作、服务重启、Candidate C。
- 除本报告外，原有文件和工作区改动均未修改；没有暂存、提交、推送、清理或重置。
