# ATR-GS-CC017-1-STRUCTURED-RESULT-CARD

## 0. 执行元数据

| 字段 | 值 |
|---|---|
| Intent ID | `GS-SEARCH-STRUCTURED-RESULT-CARD-TEMPLATE-OUTPUT` |
| CC | CC-017-1 v1.0.1 APPROVED / FROZEN |
| IHR | [IHR-GS-CC017-1-STRUCTURED-RESULT-CARD](./IHR-GS-CC017-1-STRUCTURED-RESULT-CARD.md) |
| Module | `wd_global_search` |
| Environment | macOS；Odoo 18 CE；测试 DB `odoo18ce` |
| Framework | Odoo `--test-enable`、Python compile、Node syntax |
| Code Baseline | `main @ bb6d3d9` + 未提交工作树 |
| Timestamp | 2026-10-14 |
| Result | 自动测试全绿；Chromium 结构化浏览器观察已完成；契约 HVR/多浏览器覆盖仍未闭环 |

## 1. 当前自动化状态

| 指标 | 值 |
|---|---:|
| Module tests | 103 |
| PASS | 103 |
| FAIL | 0 |
| ERROR | 0 |
| BLOCKED / SKIPPED | 0 |
| Latest Valid Run | ATR-RUN-003 |
| Evidence Baseline Match | Yes（仅对 `bb6d3d9` + 本次未提交工作树） |

## 2. Test Contract Baseline

引用 CC-017-1 §12 TEST-001–022 与 §13 regression requirements；不复制或重定义契约。

## 3. Coverage Matrix

| CC Test | Result | Evidence / 限制 |
|---|---|---|
| TEST-001 | PASS | `test_publish_accepts_structured_template`；发布 Snapshot 包含显式 schema |
| TEST-002 | PASS | `test_response_has_snapshot_card_schema`；完整 key/type shape |
| TEST-003 | PASS | `test_three_detail_limit_and_truncation`；0/1/3/4 行 |
| TEST-004 | PASS | `test_plain_text_template_payload_is_unchanged`；exact legacy payload |
| TEST-005 | PASS | `test_legacy_snapshot_fields_payload_is_unchanged`；fields serializer payload |
| TEST-006 | PASS | dual-mode 发布失败、schema/region/loop 无效输入拒绝及已发布 Snapshot 保留 |
| TEST-007 | PASS | `test_structured_card_template_enforces_aggregate_budgets` |
| TEST-008 | PARTIAL | 空 details/summary 覆盖；Boolean False、浏览器空节点未覆盖 |
| TEST-009 | PARTIAL | 不可读明细用授权结果 sentinel 测过滤；未构造真实受限用户/Record Rule 完整矩阵 |
| TEST-010 | NOT RUN | 跨公司用户隔离未专门执行 |
| TEST-011 | PARTIAL | 不同 Resource 模板分开执行；未验证同一聚合 Search response 多 Resource |
| TEST-012 | NOT RUN | structured composite mapping 未专门执行 |
| TEST-013 | PASS | structured/legacy 相同条件下 Count、分页身份、offset/limit 一致 |
| TEST-014 | PARTIAL | Chromium 中观察语义 DOM；恶意 HTML/script payload 与自动化 XSS 检查未运行 |
| TEST-015 | PARTIAL | 服务端 legacy payload 精确回归通过；浏览器交互未运行 |
| TEST-016 | PARTIAL | 100 次 parser、structured validation helper、单卡渲染及 executor Search service P95；未测完整 Publish/Apply 与 HTTP Preview API |
| TEST-017 | PARTIAL | 服务端拒绝未知 schema；前端未知 schema 安全提示未浏览器验证 |
| TEST-018 | PASS | 发布模式切换及失败时保留旧 Snapshot/checksum |
| TEST-019 | PARTIAL | French context 常量保持原文；未做多用户/多时区完整对照 |
| TEST-020 | NOT RUN | 新模式专属 allowlist 捕获检查未执行；既有 observability suite 随模块运行 |
| TEST-021 | PARTIAL | 结构化模式已在共享 Chromium 页面观察 1440×900 与 390×844；Firefox/WebKit 未验证 |
| TEST-022 | PASS | 用户于 2026-10-14 明确确认人工验证通过；专项未执行场景仍保持各自状态 |

## 4. Test Run History

### ATR-RUN-001

| 字段 | 值 |
|---|---|
| Timestamp | 2026-10-14 |
| Code Baseline | `main @ bb6d3d9` + 未提交工作树 |
| Invocation | `./venv/bin/python odoo-bin -c odoo.conf -d odoo18ce --http-port=0 --gevent-port=0 --test-enable --test-tags /wd_global_search --stop-after-init --log-level=test --logfile=/dev/stdout -u wd_global_search` |
| Scope | `wd_global_search` 全模块 Odoo tests |
| Executed | 99 |
| PASS / FAIL / SKIPPED / BLOCKED | 99 / 0 / 0 / 0 |
| Result | PASS（自动化运行范围） |
| Evidence | Odoo run 输出：`0 failed, 0 error(s) of 99 tests`；结构性能日志见 §5 |
| Follow-up | 浏览器矩阵及 HVR 见 HVR-GS-CC017-1-STRUCTURED-RESULT-CARD |

### ATR-RUN-002

| 字段 | 值 |
|---|---|
| Target | `http://127.0.0.1:8091/wd_global_search` |
| Database | 页面连接到共享 `odoo18ce` 环境；未直接读写数据库 |
| Browser | Chromium 150.0.7871.250 |
| Viewports | 1440×900、390×844；完成后恢复为 784×856 |
| Observation | 页面为 legacy `rendered_text` 卡片；原查询 `gemini chair lamp` 显示 Sales Order 2、2 条结果。该观察后为结构化 HVR 临时切换配置，并在完成后恢复原配置 |
| Result | PARTIAL；仅证明共享页面可访问及当时 legacy UI 状态 |
| Follow-up | 结构化浏览器观察与恢复记录见 ATR-RUN-003、§5.4 及 HVR |

### ATR-RUN-003

| 字段 | 值 |
|---|---|
| Timestamp | 2026-10-14 |
| Code Baseline | `main @ bb6d3d9` + 未提交工作树（含双向模式切换） |
| Invocation | `./venv/bin/python odoo-bin -c odoo.conf -d odoo18ce --http-port=0 --gevent-port=0 --test-enable --test-tags /wd_global_search --stop-after-init --log-level=test --logfile=/dev/stdout -u wd_global_search` |
| Scope | `wd_global_search` 模块升级与全模块 Odoo tests |
| Executed | 103 |
| PASS / FAIL / SKIPPED / BLOCKED | 103 / 0 / 0 / 0 |
| Result | PASS（自动化运行范围） |
| Evidence | Odoo 输出：`0 failed, 0 error(s) of 103 tests` |
| Follow-up | 此次运行后，共享配置先恢复 legacy；随后按用户要求将全部 7 个 Resource 配置为 structured，最终状态见 ATR-RUN-004 与 §5.4 |

### ATR-RUN-004

| 字段 | 值 |
|---|---|
| Timestamp | 2026-10-14 |
| Target | `http://127.0.0.1:8091/wd_global_search` |
| Database | 共享 `odoo18ce`；全部操作通过 Odoo 配置 UI |
| Browser | Chromium 150.0.7871.250 |
| Viewport | 1440×900 |
| Configuration | Published version 5；7 个 Resource 均配置 structured card；Result Card Template 管理页隐藏 |
| Observation | `office` 返回 Purchase Order 6 与 Sales Order 17（共 23，首屏 10）；`gemini chair lamp` 的 Sales Order 仍为 2 条；Contact、Storage Location、Stock Transfer、Warehouse、Product 各自查询均渲染结构化结果 |
| DOM | 观察到 title/meta/summary/details 独立节点；所有已测查询 legacy `.wd-card-template-text` 数量为 0 |
| Checksum | `1f6249ccec0415a47b5454d0ee76d3e66062dff38ffea13c88a6fae3f76c6815` |
| Result | PARTIAL；全部 Resource 配置及本次 Chromium 样例通过，Firefox/WebKit 与完整契约矩阵仍未完成 |

## 5. Special Verification

### 5.1 Performance

固定 Odoo 测试 fixture，分别采集 100 次并记录 P95：

| 阶段 | P95 ms | CC-014 软预算 | 判定/范围 |
|---|---:|---:|---|
| Parser | 0.007 | ≤10 | PASS |
| Structured template validation helper | 0.026 | Publish/Apply ≤100 | helper-only；非完整 ORM Apply |
| 单卡结构渲染 | 1.977 | ≤50 | PASS |
| Executor Search service | 1.720 | Preview API ≤500 | service-level；非 HTTP Preview API 端到端 |

数据来源：`CC17-1 PERF samples=100` Odoo 测试日志。记录环境与 fixture 为本地 Odoo 18 CE；测试未分别量测 cold/warm API 请求，也未提供生产负载性能结论。

### 5.2 Security / Permission

普通 Odoo TransactionCase 环境执行；details 不可读字段由 `_resolve_path` 的授权失败结果模拟，确认该明细不进入数组且不影响 `details_truncated`。该 mock 不等价于真实多用户/多公司 ACL 集成验收。

### 5.3 Syntax / Whitespace

- Python `py_compile`（模块和测试文件）：PASS
- `node --check mymodules/wd_global_search/static/src/js/preview.js`：PASS
- `git diff --check`：PASS

### 5.4 Structured Browser Observation and Configuration

- Environment: shared `127.0.0.1:8091`, database `odoo18ce`, Chromium 150.0.7871.250; all configuration changes were made through the Odoo UI.
- Final configuration: Published version 5 has structured templates for warehouse, storage_location, product, contact, stock_picking, sale_order, and purchase_order. The Result Card Template editor page is hidden; runtime support for existing legacy snapshots remains.
- Checksum: `1f6249ccec0415a47b5454d0ee76d3e66062dff38ffea13c88a6fae3f76c6815`.
- Search `office`: Purchase Order 6 and Sales Order 17 (23 combined); the first page showed 10 results, each rendered with semantic card nodes and no legacy text node.
- Resource-specific browser samples: Contact `Gemini Furniture` (1); Storage Location `WH/Stock` (4); Stock Transfer `WH/IN/00001` (1); Warehouse `NL Company` (1); Product `Office Lamp` (1); Sales Order `gemini chair lamp` (2). Each displayed structured title/meta/summary nodes; no `.wd-card-template-text` nodes were present.
- Sales Order and Purchase Order card details rendered with product/quantity summaries; a four-plus line Sales Order displayed three details followed by `...`.
- Earlier Chromium layout observations: 1440×900 had no horizontal overflow; at 390×844, document width was 375px and card width 317px, with no horizontal overflow. The 390px check was performed on the Sales Order sample, not all seven Resources.
- Evidence boundary: agent-assisted Chromium observations, not a committed automated browser test. A stable screenshot file was not archived; Firefox/WebKit, malicious-text testing, and human HVR signature remain outstanding.

## 6. Regression Verification

模块内既有配置、搜索服务、权限、模板、导航、observability、CC-015 contract 等测试随同一 Run 执行；103/103 PASS。详细未覆盖项仍按 §3 标为 PARTIAL / NOT RUN，不由全模块通过自动推定。

## 7. Issues

| ID | TEST | 类型 | 原因 | Status |
|---|---|---|---|---|
| ATR-ISSUE-001 | TEST-014、015、017、021、022 | PARTIAL / OPEN | 用户已于 2026-10-14 签署人工验收；8091 上 7 个 Resource 已切换 structured 并完成 Chromium 样例验证。Firefox/WebKit、恶意文本/XSS、完整 viewport 矩阵等专项覆盖仍未完成 | Open |
| ATR-ISSUE-002 | TEST-010、012、020 | NOT RUN | 本 Run 未构建跨公司/结构化 composite/log allowlist 专项 fixture | Open |
| ATR-ISSUE-003 | TEST-016 | PARTIAL | 测到 helper 与 Search service；未测完整 Apply/Preview HTTP endpoint | Open |

## 8. Handoff to HVR / FR

自动化测试运行范围 103/103 PASS；Chromium 结构化浏览器观察已记录，契约总体状态仍有 NOT RUN / PARTIAL 项。此 ATR 不宣布 CC-017-1 DoD 闭环、不得替代 HVR 或 FR。
