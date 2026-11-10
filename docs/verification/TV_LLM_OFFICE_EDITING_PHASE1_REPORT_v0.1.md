# Office Engine M2 — TV Phase 1 报告 v0.1

| 项目 | 结果 |
|---|---|
| TV 状态 | **BLOCKED at G0; Candidate B workspace integration NOT SUPPORTED for XLSX editing** |
| 执行范围 | G0 只读门禁、Candidate B 源码/API 路径能力发现 |
| TV-LE-02 / 03 / 04 | **NOT RUN** |
| 数据范围 | 未访问业务数据；未向 Provider 发送任何文件或值 |
| Provider 调用 | 0 |
| 报告日期 | 2026-11-06 |

## 1. 结论

当前工作区接入的 OpenAI 聊天路径不能完成本 TV 所要求的实际 XLSX 编辑：它将 Office 文件附件显式判定为聊天 API 不支持并跳过；消息格式化没有将 XLSX 内容或文件 ID 传给推理请求；回复适配器提取文本和 function tool calls，没有候选工作簿字节/文件 ID 的处理。代码中找到的文件上传调用仅用于 fine-tuning。

这是对**当前检出的集成路径**的静态结论，不能扩大为“当前账户、模型或 OpenAI 的所有 API 均不支持文件编辑”。8091 当前实际配置 Provider/模型、正在运行进程加载的模块身份，以及是否存在未检出的外部路由均未能直接核实。因此，Provider 专属能力结论保持 `UNVERIFIED`；不能将静态路径发现冒充真实 Provider 测试。

G0 所需的独立 TV 执行批准、当前合成数据使用/留存政策证据、调用资源/费用与窗口批准均未在本次可读项目材料中找到。冻结 TV 计划明确声明冻结不等于执行批准。因此没有 Provider 请求，也没有创建新的测试夹具。按 TV-LE-02/03/04 的实际结果均为 `NOT RUN`，Candidate B 当前工作区路径对 XLSX 编辑为 `NOT SUPPORTED`，并非通过安全拒绝获得编辑通过。

## 2. G0 门禁检查

| 检查项 | 状态 | 证据与说明 |
|---|---|---|
| Git 分支、HEAD、工作区 | `PASS`（仅记录） | 分支 `main`；HEAD `f9801fca76f7c248a9cc823c583138ab0191b978`，相对 `origin/main` ahead 1。起始工作区已有 `.coverage`、历史审计/设计/计划等多个未跟踪文件；均予以保留。未清理、暂存、提交或推送。 |
| Python 环境 | `PASS`（当前命令环境） | `python3 --version` 为 3.11.9。当前 Python 中 OpenAI SDK 2.54.0、openpyxl 3.0.9 可导入。此结果不证明 8091 进程使用同一解释器/依赖。 |
| Odoo / Office Engine 运行身份 | `UNVERIFIED` | 工作区 Odoo 源码 `odoo/release.py` 声明 18.0；`lsof -nP -iTCP:8091 -sTCP:LISTEN` 仅显示 PID 4295、进程名 Python 监听 8091。进程命令行/实际加载模块未能直接读取（`ps` 被系统权限拒绝）；未以工作目录、启动时间或源码路径推断内存模块身份。不能证明 8091 加载代码等于当前工作树。 |
| 当前 Provider 与模型 | `UNVERIFIED` | 本次不访问数据库、认证 UI 或运行服务。历史环境记录 `docs/verification/evidence/TV_Office_Engine_M2/environment.txt` 于 2026-10-22 记录 OpenAI / `gpt-5.6-luna`，但其记录的 workspace commit 为 `38718eb...`，不是当前 HEAD，故仅作历史证据，不作当前配置证明。 |
| Provider API 路径（工作区源码） | `PASS`（静态路径识别） | 当前检出 `llm_openai` 的聊天调用是 `client.chat.completions.create(**params)`；见 §3。此为工作区源码证据，不能证明运行进程已加载该版本。 |
| TV 执行、候选路线、操作窗口及评估人员批准 | `BLOCKED` | 冻结计划要求负责人另行批准 TV 执行、候选方式、操作窗口和评估人员；见 `TV_LLM_OFFICE_EDITING_PLAN_v0.2.1.md` §4。当前可读材料中没有该项独立执行批准。用户本次明确指出任务提示不替代必要批准。 |
| 合成数据使用/留存政策及本次 Provider 资源/费用 | `BLOCKED` | 未找到针对本次测试、当前 Provider 的合成文件数据政策/留存确认及调用资源/费用批准记录。没有向 Provider 发送数据，也没有尝试调用。 |
| 合成 XLSX 夹具 | `BLOCKED`（不满足） | 现有 `synthetic_prompt_injection.xlsx` SHA-256=`dd85f325524d667a0a5e0a2aaa9a04dcc1757e95c9d0b4474bc33e3453697bf5`，独立只读检查显示仅 1 个工作表、1 行 × 2 列、无公式/合并/表格；不满足本阶段至少双工作表及值类型、公式、格式、保护区要求。未创建新夹具，因为执行门禁未通过。 |
| 独立读取工具 | `PASS`（可用性） | 当前 Python 可导入 openpyxl 3.0.9。未对任何候选输出执行回读，因为本阶段没有生成候选。 |

**G0 总判定：`BLOCKED`。** 可继续进行的只读源码能力发现已完成；Provider 调用和编辑测试未获放行。没有通过切换 Provider、模型或环境绕过门禁。

## 3. Phase 1A — Candidate B Provider 文件编辑能力发现

### 3.1 当前工作区调用链证据

1. `mymodules/odoo-llm/llm_openai/models/openai_provider.py:150-203`：`openai_chat()` 组装 `model`、`messages`、可选 function `tools`，实际调用 `self.client.chat.completions.create(**params)`。
2. `mymodules/odoo-llm/llm/models/mail_message.py:50-58` 将 Office MIME 定义为“NOT supported via chat API”，包括 XLSX MIME。该模块 `:390-420` 将 Office 附件标记为“must be converted to PDF first”的不支持附件。
3. `mymodules/odoo-llm/llm_openai/models/mail_message.py:24-58` 的 OpenAI 消息格式化仅提取文本附件；多模态路径仅另行格式化图片/PDF，未把 XLSX 字节或 provider file ID 加入消息。
4. `mymodules/odoo-llm/llm_openai/models/openai_provider.py:205-227` 的非流式响应适配器返回响应文本 `content` 和工具调用 `tool_calls`。检查范围内未见返回文件字节/生成文件 ID 的分支。
5. 同文件 `:522-525` 的 `openai_upload_file()` 默认 `purpose="fine-tune"`，调用 `client.files.create(...)`；它不把上传文件绑定到推理请求，也不生成/回传编辑后的 XLSX。它不能作为文件编辑能力证据。

### 3.2 能力判定

| 问题 | 当前工作区集成路径结论 | 当前在线 Provider 结论 |
|---|---|---|
| Odoo 聊天上传 XLSX 后，是否将 XLSX 送入当前推理请求？ | `NOT SUPPORTED`：附件处理明确拒绝 Office MIME，格式化路径不包含工作簿 | `UNVERIFIED`：8091 实际配置及运行路径未确认 |
| 模型能否通过该路径读取工作簿内容？ | `NOT SUPPORTED`：未发现 XLSX 到请求内容/文件引用的传递；附件会被报告为不支持 | `UNVERIFIED` |
| 是否有可执行的 XLSX 编辑能力？ | `NOT SUPPORTED`：当前生产调用契约只有聊天文本与 function tool calls；未发现受控文件编辑工具/执行接口 | `UNVERIFIED`；无真实请求 |
| 能否返回编辑后的 XLSX 字节或可审计文件 ID？ | `NOT SUPPORTED`：当前响应适配器只处理文本与 tool calls，未发现文件产物接收/发布链路 | `UNVERIFIED` |
| 是否能在第二轮继续编辑第一轮输出文件？ | `NOT SUPPORTED`：当前路径没有第一轮候选文件回传或二轮文件引用契约 | `UNVERIFIED` |
| 文件大小、Office MIME 限制、超时及返回文件上限 | 工作区有 Office MIME 拒绝；API 服务限制未由真实接口验证 | `UNVERIFIED` |
| 请求/响应 ID、文件 ID 审计 | 当前聊天代码未在本次静态检查中证明具有编辑文件 ID 链路 | `UNVERIFIED`；无请求 |

**Phase 1A 结论：** 当前检出的 Candidate B 聊天集成 `NOT SUPPORTED` 实际 XLSX 编辑。当前账户/模型通过某个其它原生 API 的文件编辑能力仍 `UNVERIFIED`，不据此声称 OpenAI 或 `gpt-5.6-luna` 全局不具备该能力。本次无 Provider 请求、响应、tool call、file ID、耗时或费用记录（均为 N/A；不是零耗时或零费用测量）。

因当前集成路径不支持目标能力且 G0 被阻断，按停止条件不进入后续编辑测试。

## 4. TV-LE-02 / 03 / 04 状态

| TV 项 | 功能能力 | 安全拒绝行为 | 产品必需能力 | 状态及证据 |
|---|---|---|---|---|
| TV-LE-02 单轮 Excel 编辑 | `NOT SUPPORTED`（当前工作区 Candidate B 路径） | `NOT RUN` | `UNSATISFIED`（未展示实际编辑能力） | `NOT RUN`。无 Provider 文件请求、候选文件或有效风险确认；不覆盖已有值。 |
| TV-LE-03 多轮连续编辑 | `NOT SUPPORTED`（当前工作区路径无文件输入/输出 lineage） | `NOT RUN` | `UNSATISFIED`（未验证） | `NOT RUN`。没有 V1–V4 候选，没有任何轮次 SHA、请求 ID 或实际差异。 |
| TV-LE-04 公式、格式与工作簿结构保真 | `NOT SUPPORTED`（当前路径无法执行 XLSX 编辑） | `NOT RUN` | `UNSATISFIED`（未验证） | `NOT RUN`。未生成候选；没有公式、格式、合并区、条件格式、验证规则、表格、命名区域或工作表属性 diff。没有公式重算结论。 |

注意：当前路径对 Office 文件的拒绝是输入能力限制，不是已通过 TV-LE-04 的安全拒绝测试。依计划 §7.2，安全拒绝不能作为编辑能力成功计入。

## 5. 文件与独立回读证据

- 现有合成候选输入：`docs/verification/evidence/TV_Office_Engine_M2/synthetic_prompt_injection.xlsx`，SHA-256 为 `dd85f325524d667a0a5e0a2aaa9a04dcc1757e95c9d0b4474bc33e3453697bf5`。此文件仅作为不满足夹具条件的既存证据；未上传给 Provider，未修改。
- 结构只读结果：工作表 `Sheet1`，1 行、2 列；没有公式、合并单元格或 Excel 表格。其提示注入文本不是本轮编辑目标。
- 本轮输出文件：无。
- 每轮输入/输出 SHA、API 请求/响应/工具/文件 ID、独立回读断言、公式计算、费用/耗时：`NOT RUN`，无可报告的实测数据。

## 6. 证据局限与历史记录

历史环境证据 `docs/verification/evidence/TV_Office_Engine_M2/environment.txt` 记载：2026-10-22 曾从已认证 Odoo UI 看到 OpenAI 与 `gpt-5.6-luna`，并记录当时 `client.chat.completions.create`、Python 3.11.9、SDK 2.54.0。该文件还记录当时没有把真实销售订单发送至 OpenAI。其时间及 commit 与当前状态不同，不能替代当前配置或本轮 Provider 调用证据，也未被改写。

8091 运行进程实际加载模块身份、Provider 当前配置、当前 API 请求模型、数据保留政策和请求限制均为 `UNVERIFIED`。本次没有读取数据库、ORM、认证浏览器状态、附件存储或进程环境/凭据；没有重启服务。

## 7. 建议与待补门禁

1. 不建议在现有 `chat.completions` 集成路径上继续声称或执行 Candidate B Excel 文件编辑；静态代码表明该路径不传入 XLSX，也不接收 Excel 产物。
2. 若继续评估 Candidate B，须先取得计划要求的独立 TV 执行批准（指定路线、窗口、评估人及资源），确认本次合成文件的数据使用/留存政策，再由获授权的只读配置核查确认当前 Provider/API/model。若实际测试路线不是已批准的现有路径，需先由负责人明确批准该路线；不得自行改用 Responses API、其它模型或 Provider。
3. Candidate C 不在本次范围，未开发或运行。只有负责人另行批准 Candidate C 原型后才可进入其测试；本报告不构成该授权。
4. 补齐 G0 后，应重新建立符合计划要求的中性双工作表 XLSX 夹具及输入/目标/非目标基线，再执行获批的 Phase 1 场景。本报告不代表测试通过或架构切换批准。

## 8. 执行边界与 Git 状态

本轮执行了只读源码、文档、进程监听端口及已存在合成工作簿的检查；未运行 Odoo 测试、未调用 Provider、未创建/修改 XLSX、未访问或修改 Odoo 数据、未操作浏览器、未修改正式代码、未重启/升级服务。

本报告为本任务唯一新建文件。除它以外，执行前已有的工作区改动均保留；没有清理、暂存、提交、推送或重置任何内容。
