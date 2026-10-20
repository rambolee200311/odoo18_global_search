<!-- 使用 Coding/ATR 模板；记录 CC-OFFICE-M1-002 的实际自动化执行。 -->

# ATR — CC-OFFICE-M1-002

## 1. Execution Metadata

| 字段 | 值 |
|---|---|
| Intent ID | `OFFICE-ENGINE-M1-READBACK-VERIFICATION` |
| IHR | [IHR-OFFICE-ENGINE-M1-READBACK-VERIFICATION](IHR-OFFICE-ENGINE-M1-READBACK-VERIFICATION.md) |
| CC Version | `v1.0.0 Frozen` |
| Module | `mymodules/office_verify` |
| Environment | macOS 开发机；项目 `venv`；Python 3.11.9；lxml 4.9.3 |
| Test Framework | Python `unittest` |
| Base Commit | `d3045d43609bd7b3898f803074457e27f138dca5` |
| Current Code Baseline | `WT-office_verify:694ae1ee324d9dcfb7e100ba72f35a3c8f0a89f1cbb97459c1cf5fd1abddabfd`（包内 `.py/.txt` 哈希；未提交） |
| Executed By | Codex Agent |
| Execution Date | 2026-10-20 |

## 2. Test Contract Baseline

仅引用 [CC-OFFICE-M1-002](../../../context/intent/CC-OFFICE-M1-002.md) §11 `CC-TEST-001—009` 和 §6 `CC-PRESERVE-001—006`。测试输入均为本地合成 OOXML；未读取真实业务模板、未连接 Odoo、未创建文件附件。

## 3. Current Automated Test Status

| 指标 | 值 |
|---|---|
| Required Automated Tests | 9 项 CC 测试义务；15 个 unittest 用例 |
| PASS | 9 / 15 |
| FAIL | 0 |
| SKIPPED / BLOCKED / NOT RUN | 0（当前 15 个 unittest 均执行） |
| Latest Valid Run | `ATR-RUN-002` |
| Current Code Baseline | `WT-office_verify:694ae1ee324d9dcfb7e100ba72f35a3c8f0a89f1cbb97459c1cf5fd1abddabfd` |
| Evidence Baseline Match | Yes |

“PASS 9”表示 CC 的九项验证义务均有测试证据，不是 unittest 用例数。当前共 15 项 unittest，全部 PASS。

## 4. Core Test Contract Coverage Matrix

| CC Test | Automated Test / Evidence | Latest Run | Result | Evidence |
|---|---|---|---|---|
| CC-TEST-001 | venv 版本/许可证/直接依赖 pin；AST 包边界检查 | ATR-RUN-002 | PASS | `evidence/ATR-RUN-002-unittest.log`; `evidence/dependency-baseline.txt` |
| CC-TEST-002 | 空/伪装/截断/CRC/路径穿越/外部关系/DTD 内外部实体/预定义实体安全测试 | ATR-RUN-002 | PASS | `test_doctype_entities_rejected_and_predefined_entities_accepted`; `test_empty_fake_truncated_crc_and_path_traversal_fail`; `test_unknown_parts_external_links_and_old_format_are_rejected` |
| CC-TEST-003 | XLSX 目标值精确回读；DOCX 跨 run 分片纯文本及表格文本回读 | ATR-RUN-002 | PASS | `test_valid_xlsx_value_formula_cache_and_structure`; `test_docx_plain_text_is_compared_across_run_splits`; `test_docx_table_target_and_non_target_change` |
| CC-TEST-004 | 公式表达式更改失败；公式缓存变化按公式 ID 报告，不暴露缓存值 | ATR-RUN-002 | PASS | `test_xlsx_formula_change_fails_and_cache_value_not_exposed`; `test_valid_xlsx_value_formula_cache_and_structure` |
| CC-TEST-005 | 合并结构和样式差异级别、完整/失败语义 | ATR-RUN-002 | PASS | `test_merge_structure_and_required_parts_are_enforced`; `test_styles_are_warning_unless_policy_requires_them`; `test_docx_non_target_run_style_change_is_warning_or_fatal_by_policy` |
| CC-TEST-006 | 格式/结构拒绝、文件/展开/条目/XML/内存/时间预算；超限稳定失败 | ATR-RUN-002 | PASS | `test_unknown_parts_external_links_and_old_format_are_rejected`; `test_resource_budgets_are_enforced_without_partial_pass` |
| CC-TEST-007 | 仅开放基础 XLSX/DOCX；旧格式、未知活动部件拒绝 | ATR-RUN-002 | PASS | `test_unknown_parts_external_links_and_old_format_are_rejected`; `test_docx_unsupported_control_structure_fails_closed` |
| CC-TEST-008 | 未知映射键、未知/公式目标、null 和错误值失败且错误不含源内容 | ATR-RUN-002 | PASS | `test_xlsx_unknown_mapping_formula_target_and_null_fail`; `test_target_value_mismatch_and_non_target_mutation_fail` |
| CC-TEST-009 | 包不导入 `office_core`/Odoo/Provider/HTTP/Queue；输入候选字节哈希不变，无附件/文件写入 API | ATR-RUN-002 | PASS | `test_dependencies_and_package_boundary`; `test_valid_xlsx_value_formula_cache_and_structure` |

## 5. Test Run History（Append-only）

| Run ID | Invocation / Scope | 执行结果 | Result | 处理 / 证据 |
|---|---|---|---|---|
| ATR-RUN-001 | `PYTHONPATH=mymodules ./venv/bin/python -m unittest discover -s mymodules/office_verify/tests -v`；早期 13 项用例 | 8 FAIL、5 ERROR；所有需要启动回读子进程的路径因 macOS 拒绝把 `RLIMIT_AS` 降到 4 GiB 而在 XML 解析前返回资源限制 | FAIL（实施发现） | 原因和实现调整见 IHR-003；保留于 `evidence/ATR-RUN-001-unittest.log` |
| ATR-RUN-002 | `PYTHONPATH=mymodules ./venv/bin/python -m unittest discover -s mymodules/office_verify/tests -v`；当前完整 suite | 15 tests；15 PASS、0 FAIL、0 ERROR；2.213 秒 | PASS | `evidence/ATR-RUN-002-unittest.log`；RSS 监控实现的当前基线 |

附加检查：`./venv/bin/python -m compileall -q mymodules/office_verify` PASS；`git diff --check` PASS。后两项不计入 unittest 数量。

## 6. Regression Verification

| CC-PRESERVE | 验证 | 最新 Run | Result | 说明 |
|---|---|---|---|---|
| CC-PRESERVE-001 | API 只收 bytes/JSON/策略/预算，不接收文件路径或 Odoo 对象 | ATR-RUN-002 | PASS | 静态/公开 API 检查 |
| CC-PRESERVE-002 | 运行前后输入和候选哈希一致 | ATR-RUN-002 | PASS | 合成 XLSX 成功回读检查 |
| CC-PRESERVE-003 | 公式表达式不变；缓存差异隔离报告 | ATR-RUN-002 | PASS | 包含公式表达式变化失败场景 |
| CC-PRESERVE-004 | `.xls/.doc`、未知部件、高级 Word 控制结构拒绝 | ATR-RUN-002 | PASS | 未扩大格式能力 |
| CC-PRESERVE-005 | 不创建附件、链接、下载/交付状态 | ATR-RUN-002 | PASS | 纯 Python 包边界静态检查 |
| CC-PRESERVE-006 | 稳定脱敏错误、不输出文档原文 | ATR-RUN-002 | PASS | 恶意 XML / 公式更改错误断言 |

## 7. Issues

| ID | 测试/范围 | 类型 | 原因 | 状态 | Follow-up |
|---|---|---|---|---|---|
| ATR-I-001 | 生产资源预算 | 环境边界 | macOS 地址空间巨大，未将 `RLIMIT_AS` 当 RSS 预算；当前通过 Darwin 进程信息 API 轮询实际 RSS，部署环境尚未验证 | Open / 不阻塞纯 Python CC 测试 | 在目标平台和目标预算下另行验证；未知平台 fail closed |
| ATR-I-002 | 复杂真实 Office 模板 | 格式范围 | 本 CC 使用合成 OOXML；高级对象和真实复杂模板未被开放 | Expected Open | 需独立授权的能力验证，不外推当前通过结果 |

## 8. Special Verification

- Security：合成 DTD、内部实体、外部文件实体、路径穿越、外部关系、畸形/CRC 容器均执行 fail-closed 检查；未执行第三方安全扫描或生产渗透测试。
- Performance：仅记录当前 15 项小型测试用时 2.213 秒；不构成生产吞吐/容量基准。
- Odoo ORM / attachment / browser：N/A；本 CC 为纯 Python 服务。
- Integration：合成 OOXML 的 Python 单元测试；未组合调用 `office_core`，不宣称真实模板端到端通过。

## 9. Evidence Inventory

| Evidence ID | 类型 | 位置 | 对应 Run |
|---|---|---|---|
| E-001 | unittest 摘要日志 | `evidence/ATR-RUN-001-unittest.log` | ATR-RUN-001 |
| E-002 | unittest 完整输出 | `evidence/ATR-RUN-002-unittest.log` | ATR-RUN-002 |
| E-003 | Python/lxml/pip 基线 | `evidence/dependency-baseline.txt` | ATR-RUN-002 |
| E-004 | 包工作树哈希 | `evidence/code-baseline.txt` | ATR-RUN-002 |

## 10. Handoff to HVR / FR

CC 将人工验证标记为“否”；HVR 记录 N/A。ATR 只证明此处列出的自动化测试，不宣布 CC 已关闭、Office 文件可交付或生产容量已通过。
