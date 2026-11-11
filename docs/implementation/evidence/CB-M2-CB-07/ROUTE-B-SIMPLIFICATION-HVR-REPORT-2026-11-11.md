# Route B 检查简化与端到端验收报告

日期：2026-11-11
环境：Odoo 18 CE，非生产数据库 `odoo18ce`，测试实例 8092
HVR Thread：`llm.thread_18804`
模型/Provider：`gpt-5.6-luna` / OpenAI Responses API + Hosted Code Interpreter

## 结果摘要

真实 Odoo UI 中完成了 V4 结构编辑、V5 连续编辑、Candidate 接受、Candidate 拒绝、Finalize 和下载。V4/V5 文件均经 ZIP 与 `openpyxl` 独立回读。Odoo 全量测试结果为 236 tests、0 failed、0 errors；`office_verify` Python 测试为 34 passed。候选验证等级保持 `PARTIALLY_VERIFIED`，接受和 Finalize 没有提升该等级。

## 检查项处置

下列 ID 是本报告的交叉索引，按本次实际代码变更命名；不表示另造检查机制。

| ID | 处置 | 实际变更与代码位置 | 功能影响 |
|---|---|---|---|
| RB-01 | REMOVE | 单次 `office(action="edit")` 取代必须先 `plan` 再 `edit`；Tool Schema 不再暴露 `plan`。同时删除未被现有 Office 调用链使用的独立 `ResponsesAdapter.inspect_workbook()` 路径及专属报告 Schema/测试。`models/office_mapping_tools.py:1549-1602`、`services/edit_orchestrator.py:376-486`、`llm_openai/services/responses_adapter.py` | 每轮普通编辑只走实际文件编辑调用，不再要求独立的只读 Workbook Inspection Provider 请求；Candidate、Accept/Reject 保留。 |
| RB-02 | REMOVE | 移除 Agent 提交的 Inspection ID、精确 Expected Effect、effect digest、输入 SHA 与版本字段；服务端自行解析可信 Thread/Current、读取文件字节并绑定版本。`models/office_mapping_tools.py:1549-1602`、`services/edit_orchestrator.py:376-486, 630-660`、`services/intent_contract.py` | 不再要求用户提供坐标或维护内部摘要契约；源文件和 Revision 仍由服务端核验。 |
| RB-03 | DOWNGRADE | 由“超出模型预声明效果即拒绝”改为记录实际 `actual_effects`、`risk_facts` 和特性结果；不完整语义保留为 `PARTIALLY_VERIFIED`，交给用户审阅。`office_verify/verify.py:735-`、`office_verify/models.py:90-120`、`services/candidate_validator.py:99-` | 合法结构/内容修改可形成 Candidate；实际效果与验证未知项可见。验证器不宣称自然语言意图已完全证明。 |
| RB-04 | DOWNGRADE | Candidate XLSX 不再仅因安全范围内、未分类的标准工作簿部件而按严格 M1 白名单拒绝；仍检查 OOXML/ZIP，并拒绝活动内容、宏、外部链接等危险部件。`office_verify/security.py:87-103, 231-374`、`office_verify/verify.py:735-` | 增加标准 Excel 特性的处理空间；危险结构仍硬阻断，未知语义按验证能力标注。M1 严格验证路径未改为 Candidate 宽松路径。 |
| RB-05 | KEEP | 用户/Thread/附件权限、当前来源与版本绑定、真实 XLSX 有效性及资源限制、Candidate 非 Current、Accept/Reject、Current/Last Valid/Revision 推进、Finalize 保持。`services/edit_orchestrator.py:90-190, 376-486, 630-730`、`services/workbook_version_service.py`、`office_verify/security.py` | 保持授权边界、版本一致性和用户决策权。 |

## 新的普通编辑调用链

用户自然语言 → Agent 调用唯一 `office(action="edit")` → 服务端解析当前 Thread 中的上传文件或 Accepted Current → 绑定实际文件字节哈希和 Revision → 将真实工作簿与该用户本轮授权 Retriever 结果交给 Responses Adapter → 下载 Provider 返回的 XLSX → 安全读取并生成实际差异/验证结果 → 登记非 Current Candidate → 用户审阅后 Accept 或 Reject → Finalize Accepted Current 并将附件发布到 Thread。

失败候选不会推进 Current；Accept 保持原验证等级。Finalize 交付的附件直接回读核对其 SHA。

## 自动化回归

| 验证 | 结果 | 证据 |
|---|---|---|
| Odoo 模块升级及 `office_engine_m2`、`office_engine_odoo` 全量测试 | PASS：`tests.result` 236 tests，0 failed，0 errors；日志中 `Starting Test` 236 项 | [ATR-RUN-042-full-regression.log](ATR-RUN-042-full-regression.log) |
| Responses Adapter SDK Mock 与 Chat Completions 兼容回归 | PASS：删除独立 Inspection 路径后 28 passed | [ATR-RUN-047-responses-adapter-isolated.log](ATR-RUN-047-responses-adapter-isolated.log) |
| `tests.stats` 分模块汇总 | 统计差异未解释：模块分别报告 252 与 28，合计 280；最终结果及 `Starting Test` 均为 236。未将 280 宣称为通过数。 | 同上 |
| `office_verify` Python 测试 | PASS：34 passed | [ATR-RUN-043-office-verify-unit.log](ATR-RUN-043-office-verify-unit.log) |
| Python 语法编译 | PASS：本轮修改的 Python 文件通过 `py_compile` | 执行结果记录于本次任务日志 |
| Browser HttpCase | SKIP：缺少 `websocket-client`；不影响本次真实 UI HVR | ATR-RUN-042 |

Odoo 全量测试执行于删除未使用 Inspection helper 之前；该 helper 没有生产调用点，删除未改动 `ResponsesAdapter.execute()`。删除后 Adapter 全部 28 项测试通过，覆盖实际 `execute` 与 Chat Completions 兼容行为。Odoo 测试期间的其他模块加载警告与既有测试清理子进程警告按原日志保留；最终测试结果仍为 0 failed、0 errors。`git diff --check` 全仓结果包含已捕获 Odoo 日志行尾空格；针对源码目录检查未发现代码差异空白错误。

Adapter 测试第一次直接从 Odoo Addon 包路径收集时触发 Odoo 模型导入断言；改用隔离临时测试路径并带上现有 Provider 模型源文件后，最终 28 项通过。最终结果见 ATR-RUN-047。CB-02 的 `intent_effect_digest` 存储/接口仍服务既有历史恢复确认路径；普通 Route B edit 不接收该字段，服务端写入空值，不生成或比较模型提供的摘要。

## 真实 UI HVR

| 场景 | 结果与实际状态 |
|---|---|
| V4 真实结构编辑 | PASS。真实 Retriever 读取 `res.partner` ID 1、3、7 及其 `country_id`，再读取对应 `res.country`：Netherlands/NL、United States/US。Provider 新增 `Country Lookup` 工作表。Candidate 3016，父版本 2891；接受后 Current/Last Valid=3016，Document Revision=4。 |
| V4 下载及独立回读 | PASS。下载文件 ZIP 校验通过，工作表为 `Contacts`、`Country Lookup`；新表为 4 列、3 条真实查询结果。SHA-256 `3f16686b8100ee2789f56d83102187e6a3e3f4e4ce4b18925cd697137202d486`。 |
| V5 连续编辑 | PASS。以已接受 V4 字节（SHA `3f16686b...`）为输入，将 `Country Lookup` 表头改为中文。Candidate 3017，父版本 3016；接受后 Current/Last Valid=3017，Revision=5。Contacts 工作表及国家数据行保持不变。 |
| V5 下载及独立回读 | PASS。ZIP 校验通过；两张工作表及值均可读取，V4 国家数据行一致。SHA-256 `e2b08a1d46a93e82d4cc25a82186996a0cbfd466ab8aaf032d9653a6c83093c1`。 |
| Reject | PASS。Candidate 3018（父版本 3017）由用户在同一 Thread 明确拒绝。状态为 `rejected`；Current=Last Valid=3017，Revision=5。被拒绝的 A5 备注没有进入当前文件。 |
| Finalize / Discuss 附件 / 下载 | PASS。Finalize 版本 3017，消息 ID 111988，附件 ID 47515，delivery_state=`delivered`。用户从 Discuss 附件卡下载，文件可打开且 SHA 与版本 3017 一致：`e2b08a1d46a93e82d4cc25a82186996a0cbfd466ab8aaf032d9653a6c83093c1`。 |
| Odoo 业务数据 | PASS（只读路径）。Retriever 仅查询联系人和国家；编辑过程写入工作簿 Candidate/消息附件，未调用业务记录写入操作。 |

### Provider 请求与文件证据

| 操作 | Response / Request / Download ID | Provider 文件 / 容器 | 用量及结果 |
|---|---|---|---|
| V4 | `resp_02983a3074ffc549016af413b8e37c87d2bf2ad0d03544c883` / `req_8eee6507e6664981be8ded9f2604dd08` / `req_16acd9065a474957bfa76587feb23f01` | `cfile_6af413dae4dc8191b4026d3108f6177b` / `cntr_6af413bb13f48191bbaa684252ab84ce0654b1a85b4e6801` | 12,604 tokens；Candidate 3016；清理完成 |
| V5 | `resp_04a415ed6a377f20016af416987dc887d08e383c6d6a7feaaa` / `req_15fc621b43a548deaca0d042e86a4543` / `req_cc68e99f01bc40d28e29a6790db149f1` | `cfile_6af416a441b48191b0fd704566fc8d31` / `cntr_6af4169b23b88198ae784d6992ae24ec0c5804a62caaebb7` | 3,298 tokens；Candidate 3017；清理完成 |
| Reject Candidate | `resp_0e7a6162d5a0af01016af416ee772c87d09d0c36b04ed33b10` / `req_e911434221e447a29dd4a26fec7f5011` / `req_0f9da87b07744f0d88a2c4c5e41e479f` | `cfile_6af41713bd788191b2826838e37bdd51` / `cntr_6af416f132e081989612536b9d420f1d05bde8e06281b100` | 12,636 tokens；Candidate 3018 被拒绝；清理完成 |

实际 Provider 用量合计 28,538 tokens；本次未取得可核对的账单金额。一次 V4 生成在回执序列化时遇到 bytes JSON 编码错误，未形成可接受 Candidate；最小修复将验证回执中的 OOXML 证据递归规范化为 JSON 字符串，详见 `office_verify/models.py:9-17, 117-119`，并由定向测试和后续真实 V4 重试验证。

## 文件与版本证据

- [Candidate 3016 — V4](HVR-RUN-008-candidate-3016.xlsx)
- [Candidate 3017 — V5](HVR-RUN-008-candidate-3017.xlsx)
- [Finalized 3017](HVR-RUN-008-finalized-3017.xlsx)
- [8092 服务日志](HVR-RUN-008-route-b-server.log)

三个 XLSX 均已在本地用 ZIP 完整性检查和 `openpyxl` 独立读取；Candidate 3017 与 Finalize 附件 SHA 一致。

## 当前结论

用户可在同一 Thread 通过自然语言连续编辑工作簿、审阅真实 Candidate、决定接受或拒绝、Finalize 并下载最终 XLSX：本次真实 UI HVR **PASS**。自动化回归 **PASS**（模块统计数字差异保留为未解释事项）。验证等级依候选保持 `PARTIALLY_VERIFIED`；此结果不声称模型完全实现了每条自然语言业务意图。
