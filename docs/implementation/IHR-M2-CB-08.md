# IHR-M2-CB-08 — Integrated Regression & Release Readiness

**状态：READY FOR FINAL ACCEPTANCE — CC-08 定向技术范围**
**契约：** [CC-M2-CB-08 v0.1](CC-M2-CB-08_Integrated_Regression_Release_Readiness_v0.1.md)
**记录日期：** 2026-11-11

## 结论

CC-08 的三个目标缺口已完成定向验证。未发现需要修改产品代码的缺陷。本轮只新增两项 CB-08 TransactionCase、测试注册及验证脚本/证据；没有改变 Route B、Retriever、Validator、Version Service 或 Provider 实现。

### T1 — 真实 Provider 常见样式编辑

一次真实 OpenAI Responses API + Hosted Code Interpreter 调用通过现有 `office(action="edit")` 路径处理合成 XLSX，并返回 Candidate 字节。Odoo 进程受信配置开关为 `True`；使用的现有 Provider/模型为 OpenAI / `gpt-5.6-luna`。没有读取参考 Thread 的消息或附件，也没有发送 Odoo 业务数据。

真实请求结果：

- Provider Response：`resp_0cb5523293f2196f016af433cfe4f887d2aedab066b798ba18`
- 创建请求：`req_5f111368bb8c4e2683a0ba3bd06042f7`
- 文件下载请求：`req_c167a0ce22d240d5a0d9a8fe33a20ea7`
- Hosted Code Interpreter Container：`cntr_6af433d5ef1881918eadf68016d66a4404fdc3c730e04bfb`
- Usage：9,949 input、1,988 output（其中 reasoning 986）、总计 11,937 tokens；耗时 45,856 ms；资源清理状态 `completed`。实际账单金额不可由本次响应核实。
- 输入 SHA-256：`2315994a4e2514d61ef2ba69ca0db942802d4b217d3b385864fc068a8fd0ba58`
- Provider 输出 SHA-256：`8f8e06a6f6f3e5cc1cf8888c0c35f7d505119ec79e435975332a1d9d0289d88a`

Provider 路径创建了 Candidate 3107，状态 `partially_verified`。首个后处理脚本因用跨工作簿的 `openpyxl StyleProxy` 对象直接比较而提前回滚，未执行 Accept。独立检查改为比较工作簿中的解析样式 ID 后确认：B2 的 USD 两位小数格式改变；非目标单元格样式 ID、全部单元格值、公式 `C2 =B2*2` 及工作表名称保持不变；ZIP 和 XLSX 均可读取。

自动审查不批准第二次真实 Provider 请求，因此没有重发。随后将**完全相同且 SHA 一致**的 Provider 输出字节通过测试专用 ReplayAdapter 送入现有 `office(action="edit")`、Candidate Validator 和正式 `office(action="accept")` 流程。该事务中 Candidate 3109 保持 `PARTIALLY_VERIFIED`，Accept 后 Current/Last Valid 均为 3109、Document Revision 为 1，接受字节 SHA 与真实 Provider 输出完全相同。该回放不被描述为第二次真实 Provider 调用或真实 UI 操作。

两次 Odoo shell 场景均在结束时回滚合成用户、Thread、附件、Candidate 和版本记录；保留本地输入、真实 Provider 输出和证据文件。T1 为真实 Provider 文件处理 + 正式 Odoo 候选/接受服务的分段证据，不是 Agent 对话循环或浏览器 HVR。

### T2 — 同 Thread 数据刷新

同一 Thread 对同一个合成 `res.partner` ID 查询两次。两次间只修改测试 fixture；第二次 Retriever 结果中的更新名称到达实际 `office(action="edit")` 的测试 Adapter 接缝。Candidate 输入 SHA 与 Current 一致，版本指针/Revision 未提前推进。测试事务回滚，不调用真实 Provider。

### T3 — 查询期间撤权

首次 Retriever 调用可见合成记录；测试 Record Rule 随后隐藏该记录。第二次调用合法返回空结果，未复用旧查询结果。没有向 Provider 提交旧值、没有创建 Candidate，Current、Last Valid、Revision 不变。测试事务回滚。

### T4 — 代码与证据基线

记录 HEAD、dirty worktree、实际测试文件和 Route B 关键源码 SHA、数据库和 Provider 开关状态，见 [`T4-baseline.json`](evidence/CB-M2-CB-08/T4-baseline.json)。工作区在本轮开始时已存在大量其他未提交改动；本轮未清理或提交这些改动。

## 修改范围

- `mymodules/office_engine_m2/tests/test_cb08_integrated_readiness.py`：新增 T2/T3 定向 TransactionCase。
- `mymodules/office_engine_m2/tests/__init__.py`：注册该测试文件。
- `docs/implementation/CC-M2-CB-08_Integrated_Regression_Release_Readiness_v0.1.md`：记录冻结/实施授权状态。
- `docs/implementation/evidence/CB-M2-CB-08/`：合成文件、脚本、原始日志及结构化结果。

没有产品服务、模型、ACL、Provider 配置、数据库 schema 或 Odoo 官方模块代码变更；未升级模块、未重启 8091、未调用真实业务联系人数据。

## 复用的既有证据

- CC-07 完整 Odoo 回归：236 tests、0 failed、0 errors；M1 路径在该回归中复用，不重跑。
- `office_verify`：34 passed；Responses Adapter / Chat Completions 兼容测试：28 passed。
- 8091/8092 的既有 CC-07 HVR 与真实 UAT 维持原记录，不在本轮重复。
- `tests.stats` 的 252+28 与 `tests.result` 的 236 差异仍为 `UNEXPLAINED`；没有把 280 宣称为实际通过数。

## 最终状态

CC-08 定向实施证据已齐备，提交负责人进行 Final Acceptance。该状态不是负责人签署的最终关闭，也不表示复杂 Excel 全保真、生产发布、生产 Provider 外发或真实浏览器 HVR 已通过。
