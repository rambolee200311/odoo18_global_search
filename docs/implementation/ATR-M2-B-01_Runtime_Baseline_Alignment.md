# ATR-M2-B-01 — Runtime & Baseline Alignment

| 项目 | 记录 |
|---|---|
| 关联 CC | `CC-M2-B-01_Runtime_Baseline_Alignment_v0.2.md` |
| 执行状态 | **只读审计记录完成；本 CC 未执行测试** |
| 证据范围 | G2 批准的工作区文件及只读 Git 元数据；工作区外来源未获授权 |
| 测试结果 | 本 CC 自动化测试、Odoo TransactionCase、Provider/Browser E2E、文件回读均为 `NOT RUN` |
| Git 写入 | 无；未暂存、提交、推送、重置、清理或恢复 |

## 1. 目的与判读规则

本 ATR 记录本次 CC-01 可见的测试资产、既有验证报告和未执行范围。它不是一次新的测试运行，也不把历史报告中的结果转换为本轮结果。

- `SOURCE PRESENT — NOT EXECUTED` 表示测试源码存在，本 CC 未运行。
- `HISTORICAL RESULT` 表示另一轮报告曾记录该结果，本 CC 只读引用，不重新背书。
- `OPEN` / `UNVERIFIED` 保持原状态；缺少日志时不推测统计口径或根因。
- 测试实现、测试源码和工具返回的成功消息均不等价于当前运行验收。

## 2. 本轮执行记录

### 2.1 只读核查命令与结果

本轮仅执行了工作区文件读取、静态搜索和 Git 只读元数据查询。关键 Git 命令输出：

```text
$ git status --short --branch
## main...origin/main
?? .coverage
?? docs/A审计报告.md
?? docs/A2审计报告.md
?? docs/B技术设计草案.md
?? docs/implementation/CC-M2-B-01_Runtime_Baseline_Alignment_v0.1.md
?? docs/implementation/CC-M2-B-01_Runtime_Baseline_Alignment_v0.2.md
?? docs/implementation/IHR-M2-B-01_Runtime_Baseline_Alignment.md
?? docs/implementation/IMPLEMENTATION_PLAN_office_engine_m2_state-continuity_v0.1.md
?? docs/implementation/IMPLEMENTATION_PLAN_office_engine_m2_state-continuity_v0.2.md

$ git rev-parse HEAD
3ccb863430cd33b70952fd57cadc7624d284e3cf
```

以上是生成 ATR 前的工作区快照；IHR、ATR 和 CC v0.2 均处于本次获准的文档输出范围。审计收尾状态将在 IHR §9 和最终答复中记录。

### 2.2 本轮禁止且未执行的测试/验证

| 验证层 | 本轮结果 | 未执行原因 |
|---|---|---|
| 独立 Python / pytest | `NOT RUN` | CC-01 明确禁止任何自动化/手工功能测试 |
| Odoo TransactionCase | `NOT RUN` | 不得连接数据库、启动测试服务器、运行 Odoo shell 或改动数据库状态 |
| M2 集成测试 | `NOT RUN` | 属于测试执行，超出只读审计授权 |
| Provider / Browser E2E | `NOT RUN` | 未发 Provider 请求、HTTP/RPC 请求或浏览器操作 |
| XLSX 独立回读 | `NOT RUN` | 不创建或读取本轮新生成的附件/文件，不执行文件操作验证 |
| 8091 进程及 Loaded Module 核验 | `NOT RUN` | 工作区外进程/服务来源未列入 G2；不得扩大权限 |
| Thread 12063 持久化取证 | `NOT RUN` | 禁止数据库、ORM 或 Thread 持久化记录读取 |

本轮没有测试命令、测试退出码、测试运行日志或当前测试 PASS 数量。上面的 `git status` / `git rev-parse` 是只读基线命令，不是测试。

## 3. 历史验证记录（未重跑）

| 来源 | 历史条目 | 原报告结果 | 本轮处置 |
|---|---|---|---|
| `docs/verification/TV_office_engine_m2_report.md:18` | TV-M2-001 结构化 JSON 与 Mapping 完整性 | `FAIL`：JSON 解析格式子项成功，但多轮响应仍遗漏目标映射，整体验收失败 | 保留历史 `FAIL`；未重跑、未豁免 |
| 同上 `:19` | TV-M2-002 单次 Token/延迟及真实数据路径 | `INCONCLUSIVE`：合成 Provider usage 有记录，但未完成计划中的真实 50 行 Retriever→Provider 链路 | 保留历史 `INCONCLUSIVE`；未重跑 |
| 同上 `:20` | TV-M2-003 Owl 卡片与 RPC Spike | `PASS`：仅其报告定义的最小技术链路 | 保留历史 `PASS`，不外推到正式确认卡片或当前运行环境 |
| 同上 `:21` | TV-M2-004 Prompt Injection | `INCONCLUSIVE`：历史可见回复无秘密披露，但缺确定性服务端拦截证据 | 保留历史 `INCONCLUSIVE`；未重跑 |
| `docs/implementation/ATR-M2-PHASE-C-DOCUMENT-OPERATIONS-20261103.md:150–170` | Odoo TransactionCase | 历史报告记录 `office_engine_m2: 166 tests`、`office_engine_odoo: 26 tests`，摘要为 `0 failed, 0 error(s) of 160 tests` | 数量不一致，批准来源未提供可调和的原始 runner 日志；登记 `OPEN`，不推测原因、不重跑 |
| 同上 `:174–190` | Sales/Purchase Provider 与浏览器文件流程 | 历史报告记录两个场景的真实 Provider、Thread、预览/正式附件及 Python 回读断言 | 仅引用为历史记录，不代表本轮或当前 8091 的复验 |
| 同上 `:208` | 浏览器附件发布失败注入后的恢复 | 历史报告明确本轮未做真实浏览器故障注入；只有 TransactionCase retry 覆盖 | 历史边界继续保留；本轮未执行 |

### 3.1 测试数量差异

既有 ATR 同时列出两个模块发现数 `166 + 26`，并列出最终汇总 `160`。在 CC-01 批准来源中未发现完整的发现/筛选/执行清单或原始 runner 日志来说明统计口径，因此：

- 差异状态：`OPEN`。
- 根因：`UNVERIFIED`，不猜测是汇总错误、过滤、计数范围或其他原因。
- 后续影响：依赖“160 项覆盖全部 166 + 26 项”的验收结论不能以当前记录确认。
- 本 CC 处置：不运行测试，不改写原 ATR，不以重新运行绕过只读边界。

## 4. 当前测试源码资产清单（未执行）

以下是静态源码核查结果。具体用例存在不表示本轮运行通过；用例中的合成数据和 patch/mock 也不构成真实 Provider/Browser E2E。

| 覆盖主题 | 测试资产（源码路径与用例） | 源码位置 | 本轮状态 / 证据边界 |
|---|---|---|---|
| repeat-row 风险确认前不写 | `test_repeat_rows_single_object_is_normalized_before_tool_validation` | `mymodules/office_engine_m2/tests/test_native_chat_integration.py:284–352` | `SOURCE PRESENT — NOT EXECUTED`；断言包含 `needs_confirmation`、无预览、revision 和 Mapping 未变化 |
| 一次 repeat-row 确认覆盖其派生单元格和公式 | `test_repeat_row_confirmation_authorizes_its_derived_cells_and_formulas` | 同文件 `:354–355` 起 | `SOURCE PRESENT — NOT EXECUTED` |
| 排序后按稳定记录目标编辑 | `test_record_targeted_cell_edit_follows_repeat_row_after_sort_and_confirmation` | 同文件 `:587–588` 起；后续断言约 `:827–854` | `SOURCE PRESENT — NOT EXECUTED` |
| 预览字节改变导致旧确认失效 | `test_confirmation_is_invalidated_when_preview_file_changes` | 同文件 `:1756–1804` | `SOURCE PRESENT — NOT EXECUTED`；源码断言要求旧确认返回 `confirmation_scope_changed` 且不执行 |
| force override 不可扩展到 Manifest 外 | `test_force_override_cannot_expand_to_target_outside_manifest` | 同文件 `:1806–1826` | `SOURCE PRESENT — NOT EXECUTED` |
| Mapping 范围改变使确认失效 | `test_confirmation_cannot_be_reused_after_mapping_scope_expands` | 同文件 `:1828` 起 | `SOURCE PRESENT — NOT EXECUTED`；本轮未读取完整函数之外的运行结果 |
| Finalize 已完成后的幂等重放 | `test_finalize_replay_returns_same_committed_delivery_after_session_completed` | 同文件 `:2524–2568` | `SOURCE PRESENT — NOT EXECUTED`；为源码构造的测试场景 |
| Finalize revision 过期 | `test_finalize_stale_revision_returns_structured_failure` | 同文件 `:2570–2599` | `SOURCE PRESENT — NOT EXECUTED` |
| Finalize 工件生成但聊天交付待完成 | `test_finalize_reports_generated_artifact_when_chat_delivery_is_pending` | 同文件 `:2601` 起 | `SOURCE PRESENT — NOT EXECUTED` |
| Store 附件读取失败传播到 Tool Message | `test_finalize_store_failure_updates_tool_result_and_live_message` | 同文件 `:2693–2741` | `SOURCE PRESENT — NOT EXECUTED`；该用例有意 mock Store 失败 |
| 当前 Proposal restore | `test_restore_current_proposal_returns_existing_preview_instead_of_history_error` | 同文件 `:3155–3198` | `SOURCE PRESENT — NOT EXECUTED` |
| 历史 Proposal restore 生成新 revision 并发布预览 | `test_historical_restore_creates_new_revision_and_publishes_restored_preview` | 同文件 `:3200–3269` | `SOURCE PRESENT — NOT EXECUTED`；源码验证消息/附件关联，不等于本轮 UI 可见性验证 |
| M1 交付异常保留 Preview 且可重试 | `test_m1_delivery_exception_returns_retryable_failure_and_preserves_preview` | `mymodules/office_engine_m2/tests/test_render_bridge.py:407–429` | `SOURCE PRESENT — NOT EXECUTED`；M1 异常通过测试替身注入 |
| Finalize 失败后使用新幂等键重试 | `test_failed_finalize_can_retry_with_a_new_idempotency_key` | 同文件 `:431–455` 起 | `SOURCE PRESENT — NOT EXECUTED` |
| 已完成 Finalize 的持久请求身份 | `test_completed_finalize_uses_persisted_request_identity` | 同文件 `:531` 起 | `SOURCE PRESENT — NOT EXECUTED` |
| 已完成卡片重载恢复下载链接 | `test_completed_card_reload_restores_verified_download_link` | 同文件 `:615` 起 | `SOURCE PRESENT — NOT EXECUTED` |

备注：表中行号用于定位源码，不代表测试被本轮实际发现或执行。部分测试只覆盖合成数据、测试替身或特定调用层；不能据此推断真实 Provider/Browser、当前 8091 Loaded Module 或实际用户下载已通过。

## 5. 自动化与端到端覆盖状态矩阵

| 验收类别 | 当前工作区是否有相关测试源码 | 当前 CC 是否执行 | 当前 CC 结果 |
|---|---:|---:|---|
| Proposal patch、Revision、Restore | 是 | 否 | `NOT RUN` |
| repeat-row 风险确认与派生 Effect | 是 | 否 | `NOT RUN` |
| 排序后稳定目标解析 | 是 | 否 | `NOT RUN` |
| Confirmation 文件/范围变更失效 | 是 | 否 | `NOT RUN` |
| Finalize 重放、失败重试及 Store 失败传播 | 是 | 否 | `NOT RUN` |
| 原生 Provider 工具循环与 Provider 超时后的真实恢复 | 有集成源码/历史报告，但无本轮运行证据 | 否 | `NOT RUN`；当前真实超时链路未验证 |
| 当前 8091 Browser 附件卡片可见性 | 有历史 E2E 记录 | 否 | `NOT RUN`；本轮运行身份及 UI 状态未验证 |
| 当前真实 XLSX 目标结果回读 | 有历史回读报告与测试源码 | 否 | `NOT RUN` |
| 当前 ACL/Record Rule 真实集成 | 有 Odoo 测试源码 | 否 | `NOT RUN` |

## 6. 证据索引

| ID | 证据来源 | 本 ATR 用途 | 证据性质 |
|---|---|---|---|
| ATR-B01-E01 | `git status --short --branch` 与 `git rev-parse HEAD` 输出 | 审计起始 Git/工作区基线 | 本轮只读命令输出 |
| ATR-B01-E02 | `docs/verification/TV_office_engine_m2_report.md:18–21` | TV-M2-001..004 历史结果 | 既有报告，未重跑 |
| ATR-B01-E03 | `docs/implementation/ATR-M2-PHASE-C-DOCUMENT-OPERATIONS-20261103.md:150–170` | 历史 Odoo 测试命令及数量矛盾 | 既有报告，原始统计差异 OPEN |
| ATR-B01-E04 | 同上 `:174–190, :208` | 历史跨模型 E2E、回读和恢复边界 | 既有报告，未重跑 |
| ATR-B01-E05 | `mymodules/office_engine_m2/tests/test_native_chat_integration.py` | Confirmation、repeat-row、排序、Finalize、Restore、Store 测试源码 | 静态源码，未执行 |
| ATR-B01-E06 | `mymodules/office_engine_m2/tests/test_render_bridge.py` | 失败保护、retry、幂等性测试源码 | 静态源码，未执行 |
| ATR-B01-E07 | `docs/A审计报告.md`、`docs/A2审计报告.md` | 历史 Runtime / Thread 12063 审计记录 | 既有报告；历史 pending payload 不可恢复，不访问持久化记录 |
| ATR-B01-E08 | `docs/implementation/IHR-M2-B-01_Runtime_Baseline_Alignment.md` §§3–8 | Runtime 三层状态、Thread 事件、Phase B/TDD 矩阵与发现 | 本 CC 同范围的审计综合记录 |

## 7. 交付判定与开放项

### 7.1 CC-01 审计交付

`COMPLETE WITH OPEN / UNVERIFIED ITEMS`：获准工作区只读范围内的测试资产、历史测试记录和统计差异已记录。这里的 Complete 指本次审计文档交付，不表示测试、代码、运行时或产品行为通过。

### 7.2 测试与历史问题

- 本 CC 测试执行：`NOT RUN`。
- 历史 TV-M2-001：`FAIL`；TV-M2-002：`INCONCLUSIVE`；TV-M2-003：`PASS`（仅限原报告定义）；TV-M2-004：`INCONCLUSIVE`。
- 历史 Odoo 测试发现数与最终数：`OPEN`，`166 + 26` 对 `160` 无证据解释。
- Thread 12063 历史根因：`UNVERIFIED`，缺少原始 pending payload/完整关联调用证据；任何当前代码测试都只能验证当前行为，不能补造历史事实。
- 当前 8091 Loaded Module 身份和浏览器附件展示：`UNVERIFIED` / `NOT RUN`。

### 7.3 后续门禁

CC-01 的审计交付关闭不自动放行 CC-02 至 CC-05 编码，不授予 Runtime Validation 或 Production Release。受影响 CC 须按 IHR Phase B/TDD 差异矩阵记录经批准的基线处置，并满足各自独立 G3/G4/G5 门禁；不得将本 ATR 的源码用例清单当作运行通过证据。
