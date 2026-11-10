# IHR — CC-M2-CB-03 Workbook Validator

## 0. 治理与范围

- Coding Contract：`CC-M2-CB-03_Workbook_Validator_v0.2.md`（负责人冻结）。
- 状态（实施开始时）：Implementation in progress；当前正式验收状态见追加记录 IHR-007。
- 基线：仓库 `main`，HEAD `f9801fca76f7c248a9cc823c583138ab0191b978`；开始时工作区已有大量用户/历史未提交文件，全部保留。
- 范围：仅 CC-03 白名单内的本地 XLSX Candidate 验证与 typed Receipt 登记；不调用 Provider、不接触真实业务附件、不实现 UI/Confirmation Gate/CB-04，不提交 Git。

## 1. Owner Decisions / Execution Gates

### IHR-001 — 实施前置门记录

- 日期：2026-11-08。
- CC-02 Final Acceptance：负责人明确选择批准。CC-02 IHR/ATR 已追加 `Final Accepted — CC-02 technical scope`；生产附件留存/删除 `Release Gate OPEN` 和 browser-backed RPC 未验证状态保持原样。
- SRS 窄范围例外：负责人明确批准仅实施本地 Candidate Validator，并使用合成 XLSX 与非生产合成 Validation Receipt 进行测试；不包含 Provider 调用、真实业务数据/附件或生产处理。SRS/TDD/Implementation Plan 文件不修改。
- Odoo 集成环境：负责人明确授权在非生产 `odoo18ce` 执行 `office_engine_m2` 模块升级与 TransactionCase，仅使用合成数据。按 Odoo 原生测试事务回滚；不得操作真实业务记录。未获授权重启 8091，故若 CLI 测试运行不依赖服务重启则使用一次性 Odoo runner；遇到需要重启服务或超出数据库授权的动作即停止并报告。
- CC 冻结与 Coding Authorization：CC-M2-CB-03 v0.2 为冻结版本，负责人已授权进入实施。上述三项决定关闭 CC §10/§12 相应门禁；不修改冻结 CC。
- Release Gate：外部文件处理与生产留存策略与本地合成验证无关，继续 OPEN；不得扩展本轮处理范围。

## 2. Implementation Log

实现前原有 `office_verify.verify_output` / 受限 worker 只支持 M1 mapping-plan 验证；CB-02 提供 typed `ValidationReceipt` 与受控 `record_validation_receipt()`，但未有 Candidate Expected Effect diff/Receipt 生成调用入口。修复按 CC-03 的通用、只读 Candidate 比较契约进行，不按业务模型、模板名称、固定坐标或 fixture 值分支。

| 记录 | 日期 | 动作/证据 | 结果 |
|---|---|---|---|
| IHR-001 | 2026-11-08 | 负责人决定与数据库授权记录；CC v0.2 保持冻结 | 前置门已满足 |

后续实现文件、命令、实际结果、测试失败与修复逐项追加；不得覆盖任何历史失败证据。

## 3. 实施与验收记录（追加，2026-11-08）

### IHR-002 — 实现范围与信任边界

- `office_verify.verify_output` 的 M1 mapping-plan 接口及返回契约保持不变；新增 Candidate 输入比较 API、typed report 和候选专用执行指标入口，共用原有受限 worker。候选验证不执行公式、不推断业务模板角色，也不宣称自然语言意图完整性已获证明。
- 新增内部 `office_engine_m2.services.candidate_validator.validate_workbook_candidate()`：使用调用方当前 ORM 环境读取 Session、版本及私有附件；绑定公司/owner/Thread/Session/revision、输入/候选实际附件字节与 SHA、父版本和 Expected Effect digest；只登记 CB-02 typed `ValidationReceipt`，不接受版本、不推进 Current/Last Valid/Document Revision。
- 静态检查确认该入口无 `sudo()`、`env.cr`、cursor/SQL 调用；未添加模型/RPC 方法、Agent Tool Registry 项或对 Provider 的调用。`services/__init__.py` 的导出仅供 Python 内部调用。
- **边界差异**：现有 `mymodules/office_engine_m2/data/office_tools.xml` 与 M1 测试仍定义/断言 `office_prepare_context`、`office_save_mapping_preview`、`office_finalize` 等多个已存在工具名。本 CC 未修改工具注册（白名单外），也没有增加工具。冻结 CC 中“外部唯一 `office` Tool”的基线与当前源码不一致，需负责人决定是否作为既有兼容架构接受、转由后续 CC 迁移，或先修订契约；本轮不将其写成已满足。
- Expected Effect 序列化预算按 CC §6.4 单独复核：新增 `max_expected_effect_bytes`，不再读取 M1 的 `max_mapping_bytes`。当前初值 1 MiB 与仓库已有受控序列化输入上限相同，仅作为独立 Candidate 元数据边界，不表达 Mapping DSL 限制；两者可分别设定并以回归测试验证。没有基准证据支持其他数值，故不声称这是吞吐量/SLA 阈值。实际值和源文件大小写入审计报告。
- 修改/新增文件限于 CC §8.1：

| 文件 | 变化 |
|---|---|
| `mymodules/office_verify/models.py` | Candidate typed report 与独立 Expected Effect 字节预算。 |
| `mymodules/office_verify/verify.py` | 有界 XLSX Candidate 差异、类型化值/日期、常规公式/样式/基础结构和范围校验；M1 `verify_output` 保持原语义。 |
| `mymodules/office_verify/service.py`、`__init__.py` | 复用隔离 worker；新增 Candidate API 和执行指标入口。 |
| `mymodules/office_verify/tests/__init__.py`、`tests/test_candidate_verify.py` | 中性 XLSX 行为、类型、差异、日期和资源边界测试。 |
| `mymodules/office_engine_m2/services/candidate_validator.py`、`services/__init__.py` | 内部 ORM/附件绑定、Receipt 登记服务。 |
| `mymodules/office_engine_m2/tests/__init__.py`、`tests/test_candidate_validator.py` | 合成数据 TransactionCase、Receipt 与资源指标证据。 |

### IHR-003 — 失败优先与修复记录

- 首轮候选资源指标回归因 `verify_candidate_output_with_metrics` 尚未实现而失败；随后补上兼容 M1 API 的候选专用指标入口。
- 日期类型反例曾暴露两个问题：General 格式数字可被误判为日期，OOXML `t="d"` ISO 日期/日期时间未正确读取。修复后要求数值日期有日期型格式，并覆盖日期、日期时间、时间格式反例及常见内建日期格式。
- 本轮追加的预算边界测试先以旧的 `max_mapping_bytes` 判定执行，真实失败为 `OFFICE_RESOURCE_LIMIT`；完整失败输出保存在 `evidence/CB-M2-CB-03/failure_expected_effect_uses_mapping_budget.log`。改为独立 Expected Effect 预算后同一测试通过。
- 前两项早期 pytest 失败输出只在当时执行会话中展示，没有保留原始日志文件；失败命令与真实结果摘要登记于 `evidence/CB-M2-CB-03/failure_first_history.md`，不把摘要冒充完整日志。

### IHR-004 — 当前证据与边界

- 纯 Python `office_verify` 全部测试：43 passed；Odoo `TestCandidateValidator`：6/6；完整 `office_engine_m2` 回归：186 个 `Starting Test`，最终 `odoo.tests.result` 为 0 failed/0 errors。具体命令、统计差异和日志索引见 ATR 与 `evidence/CB-M2-CB-03/README.md`。
- 完整模块升级/测试使用经批准的非生产 `odoo18ce`，测试只使用合成 fixture 和 Odoo TransactionCase 回滚；`office_engine_m2` 加载/升级成功。未重启 8091、未调用 Provider、未读取真实业务附件、未改动业务数据。
- 资源实测样本：源/候选各 4,853 字节；独立 worker elapsed 0.259099s，观测到最大 RSS 87,851,008 bytes（父进程采样值，不是连续硬件峰值），15s timeout 内完成，`worker_exited=True`。不据此推导 P95 或生产吞吐 SLA。
- Odoo 汇总器存在未解释的统计差异（完整模块 222 vs `tests.result` 186；专类 8 vs 6）。不推测原因。日志还含测试框架检测到 Python 子进程并提示可能挂起的警告；Candidate worker 的退出断言通过，但该额外进程身份/最终清理状态未经证明。
- `wd_qooling_app`、`wd_advanced_m2o_record_panel`、`wd_evidence_album` 在该数据库环境被报告为不可安装/未加载；它们不属于本 CC 测试目标。M2 全量用例覆盖既有 RenderBridge/Document Request 调用路径。
- Provider、Browser、Finalize/交付 E2E、真实附件/生产文件及外部文件留存政策均未验证；`Release Gate OPEN` 继续有效。CB-02 的正式 Final Accepted 已记录在 CB-02 IHR/ATR 中。

截至本记录：CC-03 本地实现和已执行测试完成；因外部 Tool 基线不一致、统计口径未解释及子进程清理警告，状态提交负责人评审，Codex 未签署 CC-03 Final Accepted。

### IHR-005 — M1 独立 TransactionCase 补充结果

- 在 IHR-004 记录后，按 CC-03 的 M1/`office.document.request` 回归范围，使用非生产 `odoo18ce` 单独运行现有 `office_engine_odoo` 测试标签，未升级该模块；使用合成 fixture 和 TransactionCase。
- `test_office_document_request` 与 `test_attachment_identity` 共 23 个 `Starting Test`，进程退出 0，`odoo.tests.result` 为 0 failed/0 errors of 23；`odoo.tests.stats` 显示 27，计数差异仍未解释。日志：`evidence/CB-M2-CB-03/odoo_office_engine_odoo_m1.log`。
- 日志内对拒绝写入、模拟附件发布失败、模拟 Provider 错误和唯一约束冲突的 ERROR/异常为测试构造的路径；以最终 Odoo 测试汇总为执行结果，并保留原始日志，不把预期错误日志删除。
- 此补充关闭了 IHR-004 中“未运行独立 `office_engine_odoo` 测试模块”的当时状态；其他开放项（工具注册基线、测试计数差异、Odoo runner 子进程清理、Provider/Browser/生产发布范围）不变。

## 4. IHR-006 — Technical Acceptance Evidence Review (2026-11-08)

This entry reviews the existing logs against frozen CC-M2-CB-03 v0.2. No tests were rerun for this review.

| Acceptance evidence | Reviewed result | Evidence |
|---|---|---|
| `office_verify` Python tests | 43 passed | `evidence/CB-M2-CB-03/pytest_office_verify_final.log` |
| Expected Effect budget regression after fix | 1 passed, 18 deselected | `evidence/CB-M2-CB-03/pytest_expected_effect_budget_final.log` |
| Candidate Validator TransactionCase after the final budget change | 6 `Starting Test`; `tests.result` 0 failed, 0 errors of 6 | `evidence/CB-M2-CB-03/odoo_candidate_validator_final.log` |
| `office_engine_m2` module upgrade and full regression | 186 `Starting Test`; `tests.result` 0 failed, 0 errors of 186; module load/update succeeded | `evidence/CB-M2-CB-03/odoo_office_engine_m2_full.log` |
| M1 `office.document.request` / attachment regression | 23 `Starting Test`; `tests.result` 0 failed, 0 errors of 23 | `evidence/CB-M2-CB-03/odoo_office_engine_odoo_m1.log` |
| Syntax and whitespace checks | `py_compile` exit 0; `git diff --check` no output | Commands and file list in ATR-M2-CB-03 §3.1 |

### Scope disposition and remaining observations

- The Candidate Validator was not registered as an Agent Tool or RPC model method. Existing `office_tools.xml` still contains the legacy `office_prepare_context`, `office_save_mapping_preview`, and `office_finalize` tools. Per the owner’s current instruction, this is recorded as pre-existing architecture debt for CB-04; CC-03 did not add or alter those entries. This disposition does **not** claim that the single external `office` Tool architecture is already implemented.
- Odoo `tests.stats` differs from test-method evidence and `tests.result`: full M2 222 vs 186; Candidate class 8 vs 6; M1 module 27 vs 23. The cause remains **UNEXPLAINED**. No reason is inferred and no full suite rerun was made solely to reconcile the counters.
- Odoo emitted child-process cleanup warnings. The Candidate worker reported `worker_exited=True`; the identity and final cleanup of the additional process were not established. This remains an environment observation, not a demonstrated Candidate Validator failure or leak.
- The one-sample resource evidence remains limited to the values in IHR-004/ATR-003; it does not establish a production SLA or percentile bound.
- Provider, Browser, Finalize/download E2E, real business attachments, formula recalculation, and production external-file retention remain unverified/out of this CC. Production attachment retention/deletion remains `Release Gate OPEN`.

### Current technical disposition

The required CB-03 implementation and test evidence in frozen v0.2 is present in the referenced logs and reports. The pre-existing Tool Registry discrepancy is carried to CB-04 under the owner’s scope disposition above; the unexplained counters and process warning remain visible observations and were not treated as evidence of a failing CC-03 test.

**CC-M2-CB-03: READY FOR FINAL ACCEPTANCE — CB-03 technical implementation scope only.** This is a submission for the owner’s decision, not a Codex-signed `Final Accepted` state. No claim is made for Provider, Browser, Preview/Finalize delivery, production files, or the single-tool migration. The production `Release Gate OPEN` remains in force.

## 5. IHR-007 — Owner Final Acceptance (2026-11-08)

The owner approved CC-03 technical acceptance with the following explicit boundary:

- **Status: Final Accepted — CB-03 technical implementation scope only.**
- Accepted scope: local XLSX Candidate Validator, deterministic validation, resource boundaries, and registration of the CB-02 typed `ValidationReceipt`.
- Excluded: Provider, Browser, user preview, Finalize, real business attachments, and production deployment.
- Production file retention/deletion remains **Release Gate OPEN**.

This owner decision supersedes the pending owner-decision status in IHR-006 only for the scope listed above. It does not close any excluded integration or production gate and does not claim that the legacy Agent Tool Registry has already migrated to a single `office` Tool.
