# IHR-M2-CB-07 — Route B Integration

**状态：IMPLEMENTATION IN PROGRESS — VALIDATOR FIX COMPLETE; ROUTE B HVR FAILED BEFORE FILE DISPATCH**
**契约：** `CC-M2-CB-07_Route_B_End-to-End_Integration_v0.2.md`
**记录日期：** 2026-11-10

## 本轮完成

- 保留单一文件生命周期入口 `office`，并让 Route B Thread 同时向 Agent 暴露现有 `office` 与独立 `odoo_record_retriever`；Retriever 查询仍走既有工具和 ORM 权限路径。
- 初始上传现在可以从原始私有 XLSX 建立非 Current Candidate。Candidate 通过现有 Validator/Receipt 与 CB-02 受控 Accept 流程后才登记为 V1/Current；拒绝或验证失败不推进版本指针。
- 后续编辑继续从服务端解析 Accepted Current 的实际字节。当前用户同一轮成功 Retriever 结果由服务端绑定到 Provider 指令上下文。
- Provider 依赖仅从 Thread 的现有 OpenAI Provider 和受信任进程配置构造；真实调度默认关闭，不读取 Agent/RPC 参数来开启。
- 识别并修正初始 Candidate 待接受期间的路由连续性：初始 Route B Session 使用 `ir.attachment` 目标绑定进行识别，避免其 `analyzing` 状态触发 M1 路由。
- 新增/调整初始 Candidate 接受、工具可见性及联系人两阶段自动模拟测试源码。该 TransactionCase 尚未运行，不能作为 HVR 结果。

## 范围内代码

- `mymodules/office_engine_m2/models/llm_thread.py`
- `mymodules/office_engine_m2/models/office_mapping_tools.py`
- `mymodules/office_engine_m2/services/edit_orchestrator.py`
- `mymodules/office_engine_m2/services/candidate_validator.py`
- `mymodules/office_engine_m2/services/workbook_version_service.py`
- `mymodules/office_engine_m2/tests/test_edit_orchestration.py`
- `mymodules/office_engine_m2/tests/test_native_chat_integration.py`
- `mymodules/office_engine_m2/tests/test_office_retriever_integration.py`

上述文件可能包含本 CC 之前已存在的工作区改动；本记录不把那些既有改动重新归因于本轮，也未清理或覆盖它们。

## 未完成门禁

- Odoo TransactionCase / M1 Odoo 回归、模块升级与 Runtime 检查：`NOT RUN`，依 CC §10.2、§13.3、§14 需要单独运行环境授权。
- 真实 Responses Provider 集成：`NOT RUN`；外发门保持关闭，需 CC §7/§13.4 所述单独授权。
- 真实 Odoo UI 两轮 HVR、Finalize、Discuss 附件卡及下载：`NOT RUN`，需获批 Runtime、Provider 和 Browser 会话。
- 未提交 `READY FOR FINAL ACCEPTANCE`；实施尚未完成最终验收。

## 验证证据

本地语法、共享 Office Core/Verifier 自动化结果见 [`ATR-M2-CB-07.md`](ATR-M2-CB-07.md) 和 [`evidence/CB-M2-CB-07/LOCAL-VALIDATION.md`](evidence/CB-M2-CB-07/LOCAL-VALIDATION.md)。

## 2026-11-11 — Candidate Validator 误拦截修复与 HVR 复验

- 复核 Candidate 2353 与 2354 的真实文件、输入/输出 SHA、绑定信息及重建的 Actual Effects。2353 文件与输入相同，`Contacts!A2` 仍为空，真实失败是 Expected Effect 不匹配；不是 `docProps/core.xml` 阻断。2354 的 9 个联系人单元格均与已记录 Expected Effect 一致；源/候选均通过受限 OOXML 解析。唯一候选包差异是 `docProps/core.xml` 中 `dcterms:modified` 时间戳变化。
- `office_verify.verify_candidate_inline()` 现在对 core properties 做严格语义比较：只将合法 `dcterms:modified` 值视为易变元数据；其他属性、字段、结构和格式继续比较或拒绝。未知部件、未授权单元格、危险结构仍被拒绝。错误 Receipt 包含错误码、阶段、目标/部件、规则和实际变化摘要；普通用户结果仍为通用失败消息。
- 以固定 Validator 重放历史候选：2353 仍为 `FAILED`（正确）；2354 为 `VERIFIED`，9 个 `cell_value` Actual Effects，无错误。历史数据库状态未被改写，也未接受 Candidate 2433。
- 真实 UI HVR 在新 Thread `llm.thread_18271` 以普通用户指令执行一次。Retriever 成功读取 3 条合成联系人。随后模型提交的 `office(action="edit")` Expected Effect 使用 `workbook_structure` 全工作簿目标以及占位表名/单元格地址（例如 `<uploaded workbook>`、`<contact name cell>`）；服务端按 CB-03 契约拒绝为 `expected_effect_invalid`，`operation_executed=false`，未调用 Responses/Hosted Code Interpreter 编辑路径，未生成 Candidate。没有重试 Provider。
- 本次实际 HVR 未通过；未发生 Accept、Current/V1 推进、Candidate 下载或文件回读。直接阻断位于 Intent/Expected Effect 契约输入，不是已修复的核心元数据 Validator 误判。证据见 [`evidence/CB-M2-CB-07/HVR-RUN-002-ui-failure.json`](evidence/CB-M2-CB-07/HVR-RUN-002-ui-failure.json) 与 [`evidence/CB-M2-CB-07/HVR-RUN-001-provider-ui-server.log`](evidence/CB-M2-CB-07/HVR-RUN-001-provider-ui-server.log)。
- HVR TestCase 类级运行另有 1 个测试辅助器错误：测试模拟器对不存在的 ZIP 目录项 `docProps/` 做索引并触发 `KeyError`（24 tests, 0 failures, 1 error）。该错误不是 Candidate Validator 的失败；未扩大范围修复。单个初始版本接受 TransactionCase 通过。完整 CC-07/真实 UI 验收仍未完成。
