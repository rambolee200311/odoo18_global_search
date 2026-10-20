<!-- 使用 Coding/ATR 模板；模板同步检查 PASS（2026-10-20） -->

# ATR — CC-OFFICE-M1-001

## 1. Execution Metadata

| 字段 | 值 |
|---|---|
| Intent ID | `CC-OFFICE-M1-001` |
| IHR | [IHR-OFFICE-ENGINE-M1-CORE-FOUNDATION](IHR-OFFICE-ENGINE-M1-CORE-FOUNDATION.md) |
| CC Version | `v1.0.0 Frozen` |
| Module | `mymodules/office_core` |
| Environment | macOS 开发机；项目 `venv`；Python 3.11.9 |
| Test Framework | Python `unittest` |
| Base Commit | `ae9e42e7e46394ed3d5c212b7779ee05c3882db9` |
| Current Code Baseline | 工作树内容清单 SHA-256：`5430736474b92ddb2d0dc928e478621db877b4a8aedeeb546887d55e398eaf78`（`mymodules/office_core` 内 `.py/.txt` 按相对路径排序，以 `path + NUL + byte_length + NUL + file_bytes` 更新 SHA-256） |
| Executed By | Codex Agent |
| Execution Date | 2026-10-20 |

本次实现尚未提交；代码基线使用可复核的工作树哈希，并非 Git commit。其他已有工作树修改不属于本 ATR 测试范围。

## 2. Test Contract Baseline

仅引用 [CC-OFFICE-M1-001](../../../context/intent/CC-OFFICE-M1-001.md) §11 的 `CC-TEST-001`—`009` 和 §6 `CC-PRESERVE-001`—`006`。不覆盖 `office_verify`、Odoo ORM/附件、聊天、Provider、队列或浏览器产品验收。

## 3. Current Automated Test Status

| 指标 | 值 |
|---|---|
| Required Automated Tests | 9 个 CC 测试义务 |
| PASS | 9（最新有效 Run `ATR-RUN-011`） |
| FAIL | 0（当前基线） |
| SKIPPED / BLOCKED / NOT RUN | 0（CC-TEST-001—009 当前映射均有执行证据） |
| Latest Valid Run | `ATR-RUN-011` |
| Current Code Baseline | `WT-office_core:5430736474b92ddb2d0dc928e478621db877b4a8aedeeb546887d55e398eaf78` |
| Evidence Baseline Match | Yes |

历史失败 Run 保留在 §5；仅最新工作树基线 Run 用于当前状态。PASS 只覆盖列出的有限结构和测试夹具，不代表真实模板普遍兼容或生产资源预算通过。

## 4. Core Test Contract Coverage Matrix

| CC Test | Automated Test / Evidence | Latest Run | Result | Evidence |
|---|---|---|---|---|
| CC-TEST-001 | 目标 `venv` Python 3.11.9；三项锁定依赖安装；传递依赖版本、许可证、`pip check`、合成 `.xlsx/.docx` 读写 | CC-TEST-001 gate | PASS | `evidence/CC-TEST-001-dependencies.txt`; `evidence/CC-TEST-001-pip-check.log` |
| CC-TEST-002 | 空/伪装/损坏/CRC 错误/旧格式 OLE/宏部件/外部关系/DTD 与活动结构拒绝；真实样本拒绝另有本机历史证据 | `ATR-RUN-011` | PASS（限定于有证据的输入类别） | `test_container_rejects_empty_mismatch_truncated_and_unknown_parts`; `test_disabled_legacy_and_macro_formats_are_refused`; `test_external_relationship_is_rejected`; `test_hostile_xml_doctype_is_rejected_without_entity_resolution`; `test_docx_textbox_is_rejected_as_unverified_structure`; `test_synthetic_xlsx_extension_structure_fails_closed` |
| CC-TEST-003 | 基础 XLSX 单元格、公式只读标记、DOCX 段落/单元格层级读取；未准入高级结构拒绝 | `ATR-RUN-011` | PASS | `test_xlsx_inspection_identifies_cells_and_formulas_as_read_only`; `test_docx_inspection_and_candidate_render_for_plain_paragraph_and_table` |
| CC-TEST-004 | 根/条目/value schema、未知键、版本/指纹、重复/未知/公式目标、操作/type/null、空字符串与零值 | `ATR-RUN-011` | PASS | `test_mapping_rejects_unknown_missing_null_duplicate_and_formula_targets`; `test_mapping_distinguishes_empty_string_zero_and_invalid_null` |
| CC-TEST-005 | 白名单候选生成、原始输入哈希不变、结果标记为非交付候选；含公式工作簿拒绝渲染以免缓存损失 | `ATR-RUN-011` | PASS | `test_xlsx_candidate_render_preserves_source_and_uses_new_bytes`; `test_docx_inspection_and_candidate_render_for_plain_paragraph_and_table`; `test_formula_workbook_candidate_is_disabled_to_avoid_cache_loss` |
| CC-TEST-006 | `.xlsx/.docx` 基础候选能力；`.xls/.doc` 与高级对象保持关闭；真实样本拒绝由 ATR-RUN-010 本机验证记录 | `ATR-RUN-011` | PASS | `test_disabled_legacy_and_macro_formats_are_refused`; `test_synthetic_xlsx_extension_structure_fails_closed`; 本机真实样本见 ATR-RUN-010 |
| CC-TEST-007 | 输入/展开/条目/XML 结构预算，墙钟超时、工作进程终止及 macOS 无法落实小内存上限时稳定拒绝 | `ATR-RUN-011` | PASS | `test_declared_file_expanded_entry_and_count_budgets`; `test_invalid_policy_and_timeout_are_stable_and_cleanup_worker` |
| CC-TEST-008 | 稳定错误码、脱敏错误、无 traceback/路径输出；解析/映射失败不返回候选 | `ATR-RUN-011` | PASS | `test_public_errors_are_stable_and_sanitized`; mapping、容器错误用例 |
| CC-TEST-009 | 纯 Python 边界静态检查；警告收集及 unsupported/extension 警告失败关闭；无 `simplefilter("ignore")` | `ATR-RUN-011` | PASS | `test_package_boundary_has_no_forbidden_imports_or_ignore_warning`; `test_warning_classifier_fails_closed` |

## 5. Test Run History（Append-only）

| Run ID | 命令 / 范围 | 实际结果 | Result | 处理/证据 |
|---|---|---|---|---|
| ATR-RUN-001 | 初次 unittest 导入尝试；未配置 `PYTHONPATH=mymodules` | 测试发现器无法导入 `office_core`，执行测试数 0 | FAIL（测试入口） | 后续按包路径重跑；此失败不删除 |
| ATR-RUN-002 | 定向 XLSX 检查；设置 `PYTHONPATH=mymodules` | 关系目标 `/xl/...` 被误判为非法，1 项失败 | FAIL（实现缺陷） | IHR-003 修复包内绝对 URI 解析 |
| ATR-RUN-003 | 第一轮完整 unittest suite | 14 项：12 PASS、1 FAIL（空字符串回读断言）、1 ERROR（python-docx 夹具含未准入默认部件） | PARTIAL | 修正空字符串 OOXML 断言、用严格最小包夹具；失败已保留于此记录 |
| ATR-RUN-004 | 第二轮完整 unittest suite | 14 项：13 PASS、1 ERROR（测试夹具缺少 `ZipFile` 导入） | PARTIAL | 修正测试导入 |
| ATR-RUN-005 | 定向 DOCX 结构/候选生成 | 1 项 PASS | PASS | 作为局部证据，不替代完整套件 |
| ATR-RUN-006 | 完整 unittest suite，早期代码基线 | 14 项 PASS | PASS | `evidence/ATR-RUN-006-unittest.log`；后续代码更改后不继承为当前有效 Run |
| ATR-RUN-007 | 完整 unittest suite，早期代码基线 | 14 项 PASS | PASS | `evidence/ATR-RUN-007-unittest.log`；保留历史 |
| ATR-RUN-008 | 损坏 ZIP CRC 定向测试 | 首次变异未损坏压缩流；修正夹具后发现 `zlib.error` 未分类，断言失败 | FAIL（测试发现实现缺陷） | IHR-003 将 zlib 解析错误映射为 `OFFICE_INVALID_OR_MISMATCHED`；原失败保留 |
| ATR-RUN-009 | 完整 unittest suite，16 项 | 16 PASS | PASS | `evidence/ATR-RUN-009-unittest.log`；后续增加错误脱敏断言，不继承到最新基线 |
| ATR-RUN-010 | `PYTHONPATH=mymodules ./venv/bin/python -m unittest discover -s mymodules/office_core/tests -v` | 17 项 PASS，0 FAIL，0 ERROR；耗时 8.009 秒 | PASS | `evidence/ATR-RUN-010-unittest.log`；旧测试基线有效，真实样本拒绝事实保留 |
| ATR-RUN-011 | 同一命令；改用合成 OOXML 扩展结构，不依赖仓库内用户 Office 样本 | 17 项 PASS，0 FAIL，0 ERROR；耗时 7.709 秒 | PASS | `evidence/ATR-RUN-011-unittest.log`；当前可提交基线有效 |

ATR-RUN-001—005、008 的命令结果为实施期间的实际测试观察；其详细修正事实另见 IHR-003。ATR-RUN-010 记录了本机真实样本拒绝测试；真实样本未纳入 Git，当前最新可复现套件 ATR-RUN-011 使用合成扩展结构测试相同 fail-closed 边界。

## 6. Regression Verification

| CC-PRESERVE | 验证 | 最新 Run | Result | 说明 |
|---|---|---|---|---|
| CC-PRESERVE-001 | AST 检查无 Odoo/Provider/HTTP/外部命令导入 | `ATR-RUN-011` | PASS | 仅包内 Python |
| CC-PRESERVE-002 | XLSX/DOCX 候选生成后输入字节哈希保持不变 | `ATR-RUN-011` | PASS | 候选在内存隔离 |
| CC-PRESERVE-003 | 公式目标只读；含公式工作簿本阶段拒绝渲染 | `ATR-RUN-011` | PASS | 不承诺公式缓存或计算 |
| CC-PRESERVE-004 | 旧版/含活动部件/未验证结构被拒绝 | `ATR-RUN-011` | PASS | 未扩大格式能力；真实样本拒绝见 ATR-RUN-010 |
| CC-PRESERVE-005 | 静态边界无 Odoo、业务数据、Provider、HTTP 或 Queue 导入 | `ATR-RUN-011` | PASS | CC-001 为纯 Python |
| CC-PRESERVE-006 | 容器、XML、映射、超时失败抛稳定错误而无候选交付 | `ATR-RUN-011` | PASS | 候选状态明确为非交付 |

## 7. Issues

| ID | 测试/范围 | 类型 | 原因 | 状态 | Follow-up |
|---|---|---|---|---|---|
| ATR-I-001 | CC-TEST-007 | 环境限制 | 当前 macOS Python 地址空间基线使 4 GB `RLIMIT_AS` 无法设置；请求按安全策略拒绝 | Open | 后续在目标 Linux/Odoo 部署环境验证限制与资源预算；当前不作生产能力声明 |
| ATR-I-002 | CC-TEST-002/006 | 格式范围/样本保密 | 两个用户提供的真实 Office 样本在本机 ATR-RUN-010 测试中因未准入 OOXML 结构被拒绝；自动化套件改用合成 OOXML 结构，避免提交用户文档 | Open（预期安全拒绝） | 后续针对具体结构另立验证与能力准入；原样本和其渲染件不进入 Git |
| ATR-I-003 | Odoo UI | 范围外 | 本 CC 未交付 Odoo Addon 或 Office UI，不能完成端到端文件流程 | N/A by CC；非关闭阻塞 | 见 HVR；未将浏览器页面可访问等同于产品验收 |

## 8. Special Verification

- **Security:** 已执行合成恶意/畸形容器、DTD、外部关系和活动对象 fail-closed 测试；未执行生产渗透测试或第三方扫描。
- **Performance:** `N/A / Not Required`（CC-001 未声明生产性能阈值）。17 项套件耗时不是生产基准。
- **Odoo ORM / migration / browser integration:** `N/A`（本 CC 明确不含 Odoo 模型/数据库/聊天适配）。浏览器 UI 观察记录在 HVR，不作为 ATR 通过证据。
- **Integration level:** 合成文件单元测试 + 独立 Python 子进程；不代表真实 Odoo/Office 客户端或生产集成。
- **加密样本边界:** `test_disabled_legacy_and_macro_formats_are_refused` 使用具备 CFB/OLE 签名字节的合成容器（命名为 `encrypted.xlsx`）验证 CFB 被拒绝；没有有效、口令保护的 Office 文件样本。实现遇到 CFB/OLE 签名即拒绝，因此该测试覆盖的是签名门禁，不证明密码学解密或所有加密文件变体的识别能力。

## 9. Evidence Inventory — CC-TEST-001 依赖与许可

| 依赖 | 实测版本 | 许可记录 |
|---|---|---|
| openpyxl | 3.1.5 | MIT；元数据许可字段；保留版权/许可声明 |
| python-docx | 1.1.2 | MIT；venv 的 `python_docx-1.1.2.dist-info/LICENSE` |
| xlrd | 2.0.1 | BSD；venv 的 `xlrd-2.0.1.dist-info/LICENSE` 含两份许可文本；源码/二进制再分发需保留版权、条件、免责声明，且不得未经许可用于背书 |
| lxml（python-docx 传递依赖） | 4.9.3 | BSD-3-Clause；保留 `LICENSE.txt` 及 `LICENSES.txt` 中第三方许可信息 |
| typing-extensions（python-docx 传递依赖） | 4.16.0 | Python Software Foundation License；venv 含 `licenses/LICENSE` |
| et-xmlfile（openpyxl 传递依赖） | 2.0.0 | MIT |

目标解释器为 `/Users/lijianqiang/Documents/odoo18_global_search/venv/bin/python`，Python 3.11.9。`pip check` 输出 `No broken requirements found.`；pip 缓存目录不可写警告仅导致缓存关闭，不影响安装。合成 xlsx/docx read-write smoke 均 PASS。证据：`evidence/CC-TEST-001-dependencies.txt`、`evidence/CC-TEST-001-pip-check.log`。这里是依赖与 notice 义务盘点，不是法律意见，也未生成可分发包的第三方 NOTICE bundle。

## 10. Handoff to HVR / FR

CC-TEST-001—009 在当前工作树均有最新自动化证据。HVR 按冻结 CC 为 N/A；内置浏览器只确认 Odoo Chat 页面可访问，未证明 Office 业务流程。FR 对 CC Closure 的评估单独记录；本 ATR 不作关闭或发布判断。
