# FR-M2-CB-08 — Integrated Regression & Release Readiness

**建议状态：READY FOR FINAL ACCEPTANCE — CC-08 技术范围完成**
**契约：** [CC-M2-CB-08 v0.1](CC-M2-CB-08_Integrated_Regression_Release_Readiness_v0.1.md)
**实施记录：** [IHR-M2-CB-08](IHR-M2-CB-08.md)
**测试记录：** [ATR-M2-CB-08](ATR-M2-CB-08.md)
**定向 HVR：** [HVR-M2-CB-08](HVR-M2-CB-08.md)

## Final Review

### CC-08 原计划映射更新

CC-08 §3 的 18 项逐项映射及旧基线已记录在冻结契约。实施后汇总为：

| 覆盖状态 | 数量 | 处置 |
|---|---:|---|
| COVERED | 15 | 复用既有 CC-07/M1 证据或由本 CC T1/T2/T3/T4 完成 |
| PARTIAL | 1 | TM-03：复杂 Excel 特性完整保真未验证，按现有能力矩阵延期，不计 PASS |
| SUPERSEDED | 2 | 旧 Snapshot/full-incremental 等设计及旧规划要求由后续基线替换 |
| GAP | 0 | 本 CC 定义的窄验证项均有结果 |

原始覆盖基线为 12 COVERED、4 PARTIAL、2 SUPERSEDED。IR-03（常见格式）、IR-04（数据 freshness）、IR-09（撤权后二次查询）已由 T1/T2/T3 定向验证覆盖；复杂特性保真保持 PARTIAL/DEFERRED。

### 验收矩阵

| 项目 | 结果 | 证据与边界 |
|---|---|---|
| T1 — 常见样式编辑 | PASS（分段证据） | 一次真实 Provider 请求生成 XLSX；精确 SHA 的同一输出经正式 Candidate/Validator/Accept 服务回放接受。Candidate 验证等级为 `PARTIALLY_VERIFIED` 且未提升。Provider 生成事务与 Accept 回放事务不是同一数据库交易；报告如实说明。 |
| T2 — 同 Thread 数据刷新 | PASS | TransactionCase 证明第二次同 ID Retriever 查询返回新值并进入 Office Edit Adapter seam；Mock 仅用于 edit seam，不代替 Provider HVR。 |
| T3 — Record Rule 撤权后重读 | PASS | 第二次读取为空且无旧数据复用、Provider 调用、Candidate 或版本推进；合成记录与规则在事务回滚。 |
| T4 — 代码/证据基线 | PASS | HEAD、dirty 状态、源码/测试 SHA、数据库及外发开关布尔状态见 [`T4-baseline.json`](evidence/CB-M2-CB-08/T4-baseline.json)。 |

### 可复用证据

- CC-07 Route B 真实 UI HVR：V4/V5/Reject/Finalize 与下载 SHA/回读，见 [`ROUTE-B-SIMPLIFICATION-HVR-REPORT-2026-11-11.md`](evidence/CB-M2-CB-07/ROUTE-B-SIMPLIFICATION-HVR-REPORT-2026-11-11.md)。
- 8091 真实用户多轮 UAT：姓名、电话、邮箱、地址、国家三轮编辑及接受/Finalize，见 [`HVR-RUN-010-8091-human-uat-20261111.md`](evidence/CB-M2-CB-07/HVR-RUN-010-8091-human-uat-20261111.md)。
- CC-07 最终 Odoo 回归：236 tests、0 failed、0 errors；`office_verify` 34 passed；Responses Adapter/Chat compatibility 28 passed。未在本轮重复完整回归或 M1 UI。

### 未通过或限制

- 本轮最初 T1 回读脚本错误地比较跨工作簿 `StyleProxy` 对象并回滚 Candidate 3107。以 style ID 重做独立比较后确认差异仅为指定 B2 格式。自动审查拒绝第二次 Provider 请求；因此正式 Accept 使用真实输出字节的零请求回放 Candidate 3109 完成，无法声称 Provider 生成和接受在同一个活跃事务/真实 UI 中连续发生。
- 专项 Odoo 最终日志启动了 2 个 TransactionCase，进程退出码 0；`--test-file` 未打印最终 `tests.result` 汇总。早期尝试的错误、一次模块状态序列化失败和旧 Retriever 集成文件失败均保留在 ATR；不把它们计为最终两项测试结果，也不隐藏其日志。
- `tests.stats` 252+28 与 `tests.result` 236 差异原因仍 `UNEXPLAINED`；实际全量回归以 236 为证据，不把 280 当通过数。
- `PARTIALLY_VERIFIED` 不变；图表、数据透视表、VBA/外链、嵌入对象和大型工作簿的完整保真未验证。该项是明确延期风险，不计为 PASS。
- Provider 实际账单费用未核实；响应 Usage 有记录。生产外发/发布仍不在 CC-08 范围。
- 本轮没有 Odoo UI、真实 Agent Loop 或 M1 回归重跑；这些用 CC-07 已有有效证据复用，不伪称为本轮执行。

## 结果与建议

CC-08 的 T1–T4 窄范围证据已完成，且没有发现需要产品代码修复的缺陷。没有改变产品代码或 CC-07 技术语义。建议负责人作出 Final Acceptance；该建议不等于本文件替负责人关闭 CC。
