# HVR-M2-CB-09 — Fileless Office Generation

## 当前验收状态

**PASS — REAL PROVIDER + AUTOMATED ODOO UI SIMULATION; READY FOR FINAL ACCEPTANCE**

原两轮 V1→V2 验证使用合成工作簿及数据。另有 2026-11-11 补充的真实产品档案创建场景：在负责人授权指定字段外发后，通过真实 Odoo Discuss、Retriever、Responses API、Hosted Code Interpreter 和附件下载完成；未修改 Odoo 产品记录。详见 [产品档案 HVR 补充记录](evidence/CB-M2-CB-09/HVR-products-discuss-20261111.md)。

## 环境

| 项 | 值 |
|---|---|
| Odoo | Odoo 18 CE，项目 `odoo.conf`，HTTP 8091 |
| 数据库 | 非生产 `odoo18ce` |
| Thread | `llm.thread_19720` / ID `19720` |
| Odoo 用户 | Mitchell Admin（当前已登录 UI 用户） |
| Provider | 已配置的 OpenAI Responses API + Hosted Code Interpreter，模型 `gpt-5.6-luna` |
| Tool | 单一现有 `office` Tool；未增加公开工具 |

执行前新 Thread 未选中 `office` Tool；第一次用户消息没有调用 Office，Agent 如实答复无可用文件工具。随后通过 Thread 现有 Tool 选择器启用 `office`，在**同一 Thread**重发请求后完成真实创建。未改 Tool Registry 或配置。

## 两轮执行记录

### 第一轮 — 从零创建并交付 V1

实际用户指令创建 `CC09_Synthetic.xlsx`，仅含 `Items` 工作表、`Item` / `Quantity` 表头及两行合成标记。没有上传文件、模板或 Odoo 数据。

| 字段 | 结果 |
|---|---|
| 用户可见 Office Tool 调用 | `call_sVHez1LAJ25OoE1gKKdlGRDI`，`action=create` |
| Provider Response / request | `resp_068aa06d02542bb6016af452e6516487d2a5cb12a323b07187` / `req_6faa4df659fb4273867674f9ca02cc2e` |
| Code Interpreter | 3 个 tool call；容器 `cntr_6af452e69afc81919fe6d97a0ee82d4c03e39a44a560e27b` |
| Provider 文件 | `cfile_6af452f525108191a01fecaa197681d7` |
| Provider usage / 耗时 | 2,329 input + 926 output = 3,255 tokens；21.157 s |
| Provider 清理 | `cleanup_state=completed` |
| Odoo 状态 | Session 15301；V1 `version_id=3281`；Current=Last Valid=3281；Revision=1；`PARTIALLY_VERIFIED` |
| 源文件绑定 | `input_attachment_id=false`、`input_sha256=false`、`parent_version_id=false`；未伪造源附件或父版本 |
| 输出附件 | 49336，delivery message 115183，已附加到 Thread |
| SHA-256 | `2c723f7cc28c0fec0bc48148e0e1f07afa5017114ead897e99f1327aad565807` |

独立回读 [CC09_Synthetic_V1.xlsx](evidence/CB-M2-CB-09/CC09_Synthetic_V1.xlsx)：ZIP 校验通过；openpyxl 可读；工作表为 `Items`；A1/B1=`Item`/`Quantity`，A2/B2=`Synthetic Marker A`/2，A3/B3=`Synthetic Marker B`/5；文件 SHA 与 Provider/Odoo 返回值一致。

用户原始指令：

> 请从零创建一个 XLSX 工作簿，不使用上传文件或模板，文件名为 CC09_Synthetic.xlsx。工作表名为 Items，A1:B1 表头为 Item、Quantity；A2 为 Synthetic Marker A、B2 为 2；A3 为 Synthetic Marker B、B3 为 5。请生成可交付的 Excel 文件并附在本 Thread，说明实际验证范围。不要读取或修改任何 Odoo 业务数据。

### 第二轮 — 以 V1 字节编辑为 V2 Candidate 并接受

用户在同一 Thread 要求把 `Items!B2` 从 2 改为 3，保留其余内容。

用户原始指令：

> 在刚刚创建并交付的 CC09_Synthetic.xlsx 基础上，将 Synthetic Marker A 的 Quantity 从 2 改为 3，保持 Synthetic Marker B 及其他工作簿内容不变。请通过 office 编辑当前已登记的 V1，生成 Candidate 让我查看；不要读取或修改任何 Odoo 业务数据。

| 字段 | 结果 |
|---|---|
| 用户可见 Office Tool 调用 | `call_LoOLpT7ISOGXddVnaFUEhshV`，`action=edit` |
| Provider Response / request | `resp_08d446786fe68e1f016af4533418c087d29f8654b3be542476` / `req_7f4a1817935549d4a9ddc6f0cb354394` |
| Code Interpreter 容器 / 文件 | `cntr_6af453361a9c8191bd5ee40127eea41e0a8b59f3bd8af61d` / `cfile_6af4535659bc8191b1483f94eb6f3413` |
| Provider usage / 耗时 | 9,245 input + 1,561 output = 10,806 tokens；40.552 s |
| Provider 清理 | `cleanup_state=completed` |
| 输入绑定 | Provider input SHA = V1 SHA `2c723f7c…565807` |
| Candidate | V2 candidate version 3282；attachment 49337；SHA `595976044944a600094190d0fadb69ffa080eb1c8ab9cda2f12d4c3f5e9a5586` |
| Candidate 状态 | `PARTIALLY_VERIFIED`；Current 仍为 V1，Revision=1；未自动推进 |
| 用户 Accept | 先有一次未指明 Candidate ID 的请求，被服务端要求澄清；用户随后明确指出 Candidate 3282 并完成接受确认。成功 Tool call `call_6XVZORX2X1PSmAerWDV8MFkC` |
| 接受后状态 | Candidate 3282=`accepted_current`；Current=Last Valid=3282；Revision=2；验证等级仍为 `PARTIALLY_VERIFIED` |

独立回读 [CC09_Synthetic_Final_V2.xlsx](evidence/CB-M2-CB-09/CC09_Synthetic_Final_V2.xlsx)：ZIP 校验通过；工作表 `Items`；A1/B1、A2、A3、B3 保持不变，B2=3；SHA 与 Candidate、接受结果及 Finalize 结果一致。

## Finalize、交付和下载

首次在接受 V2 后 Finalize 返回 `context_unavailable`，没有改变 Current。服务端 traceback 将问题定位到 `edit_orchestrator.py::_resolve_current()`：fileless 分支只接受 `version_kind="initial"`，拒绝了合法的、带父版本的 accepted V2。最小修复和完整回归见 IHR/ATR；没有放宽权限或文件校验。

修复后在同一 Thread 再次发送“请将当前已接受的工作簿版本正式 Finalize 并交付到这个 Thread，供我下载。”

| 字段 | 结果 |
|---|---|
| `office(action="finalize")` 调用 | `call_ew1P3LIXyPKFTIr4S4jKdBEv`，状态 `finalized` / `delivered` |
| 最终版本 | V2 / version 3282；Current=Last Valid=3282；Revision=2 |
| 验证等级 | `PARTIALLY_VERIFIED`，未被 Finalize 提升 |
| 正式 Thread 附件 | 49337；delivery message 116185；`attachment_posted_to_thread=true` |
| SHA | `595976044944a600094190d0fadb69ffa080eb1c8ab9cda2f12d4c3f5e9a5586`，与已接受 V2 一致 |
| Odoo UI 下载 | Discuss 附件卡下载控件已点击；8091 日志中 `/web/content/49337?...&download=true` 返回 HTTP 200（3 次请求） |
| 回读 | 相同附件的原始字节保存于 Evidence；openpyxl 内容断言、ZIP 测试与 SHA 均通过 |

内嵌浏览器未提供本地下载路径，因此 Evidence 保存的是通过 Odoo ORM 对**相同交付附件 ID 49337**只读取得的原始字节，而非声称取得浏览器下载目录中的本地文件。下载控制器的真实 UI 请求已返回 HTTP 200；回读附件与交付 SHA 一致。

## 结果矩阵

| 验收项 | 结果 | 证据 |
|---|---|---|
| 真实 Agent/UI 调用现有 `office` Tool | PASS | Thread 19720；Tool calls 见上 |
| 真实无源 XLSX 创建并登记 V1/Current | PASS | V1 result、attachment 49336、独立回读 |
| 不伪造输入文件/父版本/输入 SHA | PASS | V1 Tool result |
| 第二轮基于已接受 V1 的真实字节 | PASS | Input SHA 与 V1 output SHA 一致 |
| Candidate 与 Current 分离 | PASS | V2 Candidate 时 Current 仍为 3281 |
| 经 Agent 正式接受 V2 | PASS | call `call_6XVZORX2X1PSmAerWDV8MFkC`；Current 推进到 3282 |
| Finalize 及 Thread 附件交付 | PASS（修复后） | call `call_ew1P3LIXyPKFTIr4S4jKdBEv`；attachment 49337 |
| UI 下载控制器 | PASS | 8091 `/web/content/49337` HTTP 200 |
| XLSX 文件和内容独立回读 | PASS | 两个 XLSX Evidence、ZIP/openpyxl/SHA 检查 |
| 业务数据只读 | PASS | 全程未调用 Retriever 或访问 Odoo 业务数据 |
| Reject、真实 Provider 失败/超时 HVR | NOT RUN | 不属于本两轮正向 HVR；故障保护由自动化回归覆盖，不宣称真实 Provider 故障通过 |
| 成本金额 | UNVERIFIED | Provider usage 已记录，账户账单未核实 |

## 证据索引

- Provider 请求脱敏摘要：`evidence/CB-M2-CB-09/HVR-provider-calls.json`
- Odoo 8091 服务日志及附件下载 HTTP 状态：`evidence/CB-M2-CB-09/HVR-odoo-8091.log`
- V1：`evidence/CB-M2-CB-09/CC09_Synthetic_V1.xlsx`
- Final V2：`evidence/CB-M2-CB-09/CC09_Synthetic_Final_V2.xlsx`
- 聚焦与完整 Odoo 测试：见 [ATR-M2-CB-09.md](ATR-M2-CB-09.md)
- 最终报告：`FR-M2-CB-09.md`

**结论：** CC-09 的真实 Provider、同 Thread 两轮创建/编辑、用户接受、Finalize、附件交付、下载 HTTP 成功及文件回读验收通过；工作簿仍标注 `PARTIALLY_VERIFIED`。提交 `READY FOR FINAL ACCEPTANCE`，不在此报告中自行关闭 CC。

Usage 数字仅对应上表两次 Responses 文件创建/编辑请求；Agent 普通对话轮次的 Chat Completions usage 未纳入这两个数字，账户账单金额也未核实。

## 补充 HVR — 真实 Odoo 产品档案无模板创建（2026-11-11）

同一 Thread `llm.thread_19915` 中，先前的 9:02–9:03 请求没有触发 Retriever 或 Office 调用。源码核对发现，无附件、无 Office Session、无 Current 的 fileless 创建请求不会使 M2 Thread 激活并绑定 Office 工具；模型因此没有收到相关 Tool schema/Route B 指引。修复后，用户在同一 Thread 发出普通产品导出请求，真实 Agent 顺序调用 `odoo_record_retriever` 和 `office(action="create")`，成功创建并交付 V1。

- Retriever：`call_AhSSeFxCYyRrlM0ybw55Vi4E`；查询 `product.template` 的 `name/list_price/weight/tracking`，`limit=5`，返回 5 条记录（ID 1–5）。
- Office：`call_5FqqU4hXfxJ5dPbITqa2JlWK`；真实 Responses API + Hosted Code Interpreter 返回 XLSX。Response `resp_058f906fb0cb7b64016af46c7278bc87d2a362ec2acd13174c`，request `req_9a26f37e14d94768a9c050ac0b1dcb23`，usage 9,700 input + 2,748 output = 12,448 tokens，42.778 秒，远端清理 `completed`。
- 交付状态：Session 15457；V1/Current/Last Valid version 3369；Revision 1；attachment 49900；message 116235；`PARTIALLY_VERIFIED`；无输入附件、输入 SHA 或父版本。
- Discuss 附件卡下载控件在真实 UI 中触发下载，文件保存并独立回读。ZIP、openpyxl 和 5 条 Retriever 数据逐字段比较均通过；7,160 bytes；SHA-256 `f84d034b2e3a7cb2d3a010a53dffa02fb169ee9027e4902a5d5a0e98bbd4d8e9`。本地检查证明所请求字段与 Retriever 结果一致；服务自身仍如实保持 `PARTIALLY_VERIFIED`，不宣称业务完整性已由 Validator 证明。
- 修复：在 `llm_thread.py` 对用户拥有的无源工作簿请求识别现有 Office 工具并在 Provider schema 构建前绑定；同一 Thread 后续省略“Excel”的用户指令沿用最近的工作簿请求。没有新增 Tool、修改 Provider Dispatch 开关或绕过 ACL。
- 自动化：fileless Tool 绑定/指引及 fileless Current 回归共 2 项 TransactionCase 通过，见 `ATR-fileless-tool-binding-and-current-20261111-rerun.log`。结构化结果见 `HVR-products-readback-20261111.json`。

本补充场景证明本次产品数据请求的 UI→Agent→Retriever→Responses/Code Interpreter→V1/Current→Thread 附件下载链路成功；它不是对原两轮合成 HVR 的替代，也不改变 `PARTIALLY_VERIFIED` 边界。
