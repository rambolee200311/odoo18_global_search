# IHR-GS-MULTI-CONDITION-SEARCH

## 0. 文档治理

| 项 | 内容 |
|---|---|
| 文档类型 | Implementation History Record |
| Intent ID | `CC-015` |
| 状态 | In Progress |
| 上游模板 | IHR Standard Template v1.0.0 FROZEN |
| 维护原则 | Current Snapshot 可更新；Implementation History 与 Stop/Deviation 记录仅追加 |

## 1. 执行元数据（Execution Metadata）

| 字段 | 值 |
|---|---|
| IHR 文档 | `IHR-GS-MULTI-CONDITION-SEARCH.md` |
| Intent ID | `CC-015` |
| CC | [CC-015 v0.4 AMENDED / APPROVED](../intent/CC-015_multi_condition_search.md) |
| 模块 | `wd_global_search` |
| 工作类型 | 多条件搜索功能 |
| 实施负责人 | Copilot assistant |
| 开始时间 | 2026-10-13 |
| 最后更新 | 2026-10-13 |
| 当前实施状态 | In Progress |
| Branch / Base Commit | `main` / `63a2df2` |

## 2. Coding Contract 基线

- CC-015 v0.3 曾冻结 Exact-only 多词语义；用户于 2026-10-13 批准 v0.4 修订：Char/Text 字段对多词 token 使用 Contains，token AND、权限边界、单 token 和结构化条件兼容仍保留。
- 外部 SearchRequest、路由、响应形状、Resource、Refinement、分页和 cursor 继续遵守 CC-002/005/012；权限遵守 CC-003；错误遵守 CC-007；日志遵守 CC-008。
- 具体行为、不变量、测试、停止条件和完成定义引用 [CC-015](../intent/CC-015_multi_condition_search.md) §§3–20；实施触点引用 §22。
- CC-015 使用 `CC15-INV-*`、`CC15-TEST-*` 与 `CC15-DEC-*` 作为本轮追溯 ID；不在 IHR 中另造 CC-CHANGE/CC-PRESERVE 语义。
- Published 配置基线：`global_search_baseline` version 5，checksum `4cd6cb4e0e59b2116bd7261bb8f9e8f504c1970e3bee90ea7b07dd510f00597b`；Sales Order 的字段/Relation Paths 证据见 CC-015 §2.3。

## 3. 当前实施状态摘要（Current Implementation Status Summary）

| 项 | 当前状态 |
|---|---|
| CC-015 实施行为 | 多词解析、CQO、文本 Contains 搜索域、Count/cursor 身份及 Query Understanding 已接入；8091 v0.4 Playwright 实测 `001 chair` 返回 11 个 Sales Order |
| Preservation Impact | 53 项服务层、字段路径、权限和索引测试通过；配置 TransactionCase、完整 Odoo 回归和性能验证待运行 |
| Deviation | None |
| Stop Condition 触发 | No；开始实施前已完成 Published snapshot 核验 |
| Open Issues | 数据库型 Contains 跨字段 fixture、完整回归和性能验证待完成；人工 HVR 已由用户确认通过，FR 仍待完成 |
| Revert 发生 | No |
| 当前状态 | In Progress |

当前 Published Sales Order 配置中 `name` 为 Exact，客户与产品路径为 Contains。按 v0.4，多词自由文本会对这些已发布且授权的 Char/Text 字段统一使用 Contains；本轮尚未修改或发布配置。

## 4. 实施历史条目（Implementation History Entries）

### IHR-001 — 冻结 CC-015 并核验 Published 基线

- **时间：** 2026-10-13
- **阶段：** Implementation
- **Action：** 按用户批准将 CC-015 更新为 v0.3 FROZEN；通过新打开的授权 Odoo UI 核验 `global_search_baseline` Published version 5、checksum，以及 Sales Order Search Fields 和 Relation Paths。
- **Reason：** 建立实施前冻结契约与配置证据基线。
- **Files / Components：** `docs/context/intent/CC-015_multi_condition_search.md`、Odoo 授权配置 UI（只读）。
- **Contract Reference：** CC-015 §0、§2.3、§19、§20；CC15-DEC-001~026。
- **Result：** Completed。
- **Deviation：** None。
- **Follow-up：** 按 CC-015 §22 检查现有服务与测试，再实现并持续追加记录。

### IHR-002 — 接入多词 CQO 与 Exact 搜索执行

- **时间：** 2026-10-13
- **阶段：** Implementation
- **Action：** 新增受限多词解析和内部 CQO；将每个 token 编译为当前授权 Exact Searchable Fields 的 OR 域，再将 token 组与既有结构化条件 AND；同步加入 token 条件身份、成功执行后的 Query Understanding、失败摘要清空、Exact 发布校验及前端请求状态处理。
- **Reason：** 实现 CC-015 冻结的多词确定性搜索语义，同时保留单词 Raw Query、CC-002 请求形状、权限、Count、分页及 cursor 兼容。
- **Files / Components：** `services/types.py`、`services/request_boundary.py`、`services/conditions.py`、`services/executor.py`、`services/facade.py`、`models/configuration.py`、`controllers/main.py`、`static/src/js/preview.js` 及对应测试。
- **Contract Reference：** CC-015 §§3–18、CC15-INV-001~031、CC15-TEST-001~043。
- **Validation：** 50 项定向服务、字段路径、权限和索引测试通过；`compileall`、`node --check`、`git diff --check` 通过。数据库型 `TransactionCase`、完整模块回归及 HVR 尚未执行。
- **Result：** Core implementation completed; integration/HVR pending。
- **Deviation：** None。对 Exact 数值、日期、日期时间和布尔字段将文本 token 转为相应 ORM 值；不兼容的字段不参与该 token 的 OR 域。若一个 token 对所有 Exact 字段均无可转换值，使用确定的空匹配域；未增加 API 或错误类型。
- **Follow-up：** 在安全测试数据库运行配置发布和模块回归，再完成 ATR/HVR；人工 HVR 通过前不得声明 Coding Closure。

### IHR-003 — 记录 ATR 并完成 Playwright 串行模拟

- **时间：** 2026-10-13
- **阶段：** Verification
- **Action：** 创建 ATR，记录 CC15-TEST-001~043 的当前状态；在临时 Odoo 8092 实例及内置浏览器中串行执行单词、多词、分隔符等价、Contains 排除和非法 OR 场景。
- **Reason：** 按 ATR 标准保存真实测试执行证据，区分自动化浏览器模拟、数据库型自动化测试与用户人工 HVR。
- **Files / Components：** `docs/context/history/ATR-GS-MULTI-CONDITION-SEARCH.md`、当前 Search Workspace/Search API、已有 Sales Order `S00001`。
- **Contract Reference：** CC-015 §§17–20；ATR Standard v1.0.0。
- **Result：** 51 项定向单元测试通过；Playwright 5 个串行只读场景通过。ATR 为 PARTIAL；数据库型测试、完整模块回归和人工 HVR 未完成。
- **Deviation：** None。临时实例使用当前工作区代码，不执行 module upgrade；没有发布配置、直接数据库操作或业务数据写入。
- **Follow-up：** 当时计划的双 Exact 字段 fixture 已由 IHR-005 的 v0.4 Contains-on-text 修订取代；TransactionCase/模块回归及人工 HVR 仍待完成。Playwright 模拟不等同用户验收。

### IHR-004 — 在 8091 核查 `001` 数据结果

- **时间：** 2026-10-13 10:48 +08:00
- **阶段：** Verification
- **Action：** 使用现有内置浏览器访问 8091，先用 `001` 获得资源计数，再分别查询 `chair` 和 `001 chair`；结果范围收敛到 Sales Order。
- **Reason：** 核实用户报告的“001 无结果”是否由缺少业务数据引起，并区分部署运行版与当前工作区代码。
- **Files / Components：** 用户现有 8091 Workspace；[ATR-GS-MULTI-CONDITION-SEARCH.md](./ATR-GS-MULTI-CONDITION-SEARCH.md) RUN-009。
- **Contract Reference：** CC-015 §2.3、§17 TEST-004/036；ATR §8。
- **Result：** `001` 在 Sales Order 返回 1190 条；`chair` 返回 16 条，其中 `sale_order:1` 明细包含 `Office Chair`；`001 chair` 返回 0，Query Understanding 显示 `name=001 chair`。零结果后 Sales Order resource tab 被隐藏。该页面加载 `preview.js?v=cc013-v07`，而当前工作区已改为 `cc015-v01`。
- **Diagnosis：** 数据存在；8091 旧运行版将 `001 chair` 作为单一完整条件处理，并非 CC-015 token AND，因此不能跨订单号和明细产品字段匹配。运行时所用 CC-015 v0.3 Exact-only 限制随后由 IHR-005 按用户批准修订为 Contains-on-text。
- **Deviation：** None。只读查询，未改数据或配置；本次验证旧运行版行为，不验证 CC-015 新代码。
- **Follow-up：** 跨字段 Contains token AND 语义已由用户批准并在 IHR-005 实施；目标端运行版及结果已由 IHR-006 验证。

### IHR-005 — 按用户批准修订多词文本匹配

- **时间：** 2026-10-13
- **阶段：** Implementation
- **Action：** 按用户批准将多词查询改为对已发布且当前用户可访问的 Char/Text Searchable Fields 使用字面 Contains 匹配；每词 OR 字段、词间 AND。非文本字段仅在 operator_set=exact 时继续类型化等值匹配。
- **Reason：** `001` 命中订单编号、`chair` 命中明细产品时，跨字段 token AND 应返回同一销售订单。
- **Files / Components：** `services/executor.py`、`services/types.py`、`services/facade.py`、`models/configuration.py`、对应测试、[CC-015 v0.4](../intent/CC-015_multi_condition_search.md)、ATR。
- **Contract Reference：** CC-015 v0.4 §4.3、§6、§9、§12、§16、§17；修订后的 DEC-002/003、INV-029/030。
- **Validation：** 53 项定向服务、字段路径、权限和索引测试通过；数据库型 Configuration `TransactionCase`、完整模块套件、8091 新代码 Playwright、性能回归和人工 HVR 尚未执行。
- **Result：** Implementation complete for approved text matching semantics; deployment/integration pending。
- **Deviation：** None；这是用户明确批准的 CC-015 v0.4 契约修订。单 token 与结构化 operator 不变；LIKE 元字符按字面文本转义。
- **Follow-up：** `001 chair` 目标端验证已由 IHR-006 完成；补测 transaction fixture、性能与 HVR。

### IHR-006 — 在 8091 验证 v0.4 `001 chair`

- **时间：** 2026-10-13
- **阶段：** Verification
- **Action：** 按用户授权升级并重启现有 8091 Odoo 服务，在内置浏览器串行搜索 `001` 和 `001 chair`。
- **Reason：** 验证用户批准的 Contains-on-text 规则已加载至用户指定环境，并确认单 token 兼容。
- **Files / Components：** 8091 `odoo18ce`、当前工作区 `wd_global_search`；[ATR-GS-MULTI-CONDITION-SEARCH.md](./ATR-GS-MULTI-CONDITION-SEARCH.md) RUN-012。
- **Contract Reference：** CC-015 v0.4 §§4.3、6、9、17；CC15-TEST-001/004/019。
- **Result：** 页面加载 `preview.js?v=cc015-v01`。`001` 在 Sales Order Count 1190；`001 chair` 摘要为 `keywords: 001 AND chair`、Sales Order Count 11、显示 `1–10 of 11`。首个结果 S00001 (`sale_order:1`) 的明细含 Office Chair。
- **Deviation：** None。只执行只读搜索；没有修改业务记录或 Published 配置。模块按用户授权升级并重启。
- **Follow-up：** 当时人工 HVR 尚待完成，后由 IHR-007 / ATR RUN-013 记录通过；数据库型 `TransactionCase`、完整模块和性能回归仍待完成。

### IHR-007 — 记录用户人工 HVR 通过

- **时间：** 2026-10-13 11:20 +08:00
- **阶段：** Verification
- **Action：** 记录用户对 8091 搜索验收步骤的人工通过确认。
- **Reason：** 区分 Playwright 模拟结果与用户实际人工验收；仅将用户明确确认的 HVR 项标记为通过。
- **Files / Components：** [ATR-GS-MULTI-CONDITION-SEARCH.md](./ATR-GS-MULTI-CONDITION-SEARCH.md) RUN-013。
- **Contract Reference：** CC-015 v0.4 §§17–18；ATR Standard v1.0.0。
- **Result：** 用户在获知并执行 `001 chair` 应返回 11 条、S00001 明细包含 Office Chair，且单词 `001` 保持 1190 条的验收步骤后回复“通过”。ATR 已按用户确认记录 HVR PASS。
- **Deviation：** None。未将该确认扩展为数据库、完整模块、性能、多用户或日志测试通过。
- **Follow-up：** 数据库型 `TransactionCase`、完整模块/性能回归及 FR 仍待完成。

## 5. 实际变更清单（Actual Change Inventory）

| 文件 / 组件 | 动作 | 实际变更 | CC 来源 | IHR |
|---|---|---|---|---|
| `docs/context/intent/CC-015_multi_condition_search.md` | Modified | 加入当前 Published UI 核验结果并冻结为 v0.3 | CC-015 §0、§2.3 | IHR-001 |
| `docs/context/history/IHR-GS-MULTI-CONDITION-SEARCH.md` | Added | 建立本轮实施历史记录 | IHR Standard §0–8 | IHR-001 |
| `services/types.py`、`services/conditions.py` | Modified | 增加内部 CQO、KeywordTerm 和 EffectiveConditions token 表示 | CC-015 §§4–7 | IHR-002 |
| `services/request_boundary.py` | Modified | 多词语法、Unicode/token 限制、总条件数和单词旧路径兼容 | CC-015 §§5–8、16 | IHR-002 |
| `services/executor.py` | Modified | 授权 Exact 字段 OR、token AND、类型转换及空匹配域 | CC-015 §§9–12 | IHR-002 |
| `services/executor.py` | Modified | 多词 Char/Text Contains 字段 OR 与 token AND；保留非文本 Exact 类型转换和空匹配域 | CC-015 v0.4 §§4.3、9、12 | IHR-005 |
| `services/facade.py` | Modified | CQO 接入、Contains 语义 cursor 身份、Query Understanding operator 和失败清空 | CC-015 v0.4 §§9–12 | IHR-005 |
| `services/types.py` | Modified | KeywordTerm 改为单纯 token 数据，不再暴露 Exact match 标记 | CC-015 v0.4 §§4、7 | IHR-005 |
| `models/configuration.py` | Modified | Publish-time 要求每个 Resource model 至少有一个 searchable field | CC-015 v0.4 §16 | IHR-005 |
| `controllers/main.py` | Modified | Search API 原样传递 Raw Query，并更新前端脚本缓存版本 | CC-015 §§3–4 | IHR-002 |
| `static/src/js/preview.js` | Modified | 保留输入文本；展示 token AND 摘要及 in-flight/失败状态 | CC-015 §§11–12 | IHR-002 |
| `tests/test_request_boundary.py`、`tests/test_service_core.py`、`tests/test_configuration.py` | Modified | 增加解析、域、cursor、摘要和发布校验覆盖 | CC-015 §17 | IHR-002 |
| `tests/test_service_core.py`、`tests/test_configuration.py` | Modified | 覆盖多词 Char/Text Contains、字面 LIKE 元字符及 Contains-only 发布校验 | CC-015 v0.4 §17 | IHR-005 |
| `docs/context/intent/CC-015_multi_condition_search.md` | Modified | 记录经批准的 v0.4 Contains-on-text 修订 | User-approved CC amendment | IHR-005 |
| `docs/context/history/ATR-GS-MULTI-CONDITION-SEARCH.md` | Modified | 追加 53 项测试结果并更新目标端部署缺口 | CC-015 v0.4 §17 | IHR-005 |
| `docs/context/history/ATR-GS-MULTI-CONDITION-SEARCH.md` | Modified | 追加 8091 v0.4 `001 chair` 正例、单词兼容和资产版本证据 | CC-015 v0.4 §17 | IHR-006 |
| `docs/context/history/ATR-GS-MULTI-CONDITION-SEARCH.md` | Modified | 追加用户人工 HVR 通过记录 RUN-013，并更新当前缺口状态 | ATR Standard v1.0.0 | IHR-007 |
| `docs/context/history/IHR-GS-MULTI-CONDITION-SEARCH.md` | Modified | 记录用户人工 HVR 通过和剩余自动化/集成缺口 | IHR Standard §4 | IHR-007 |
| `docs/context/history/ATR-GS-MULTI-CONDITION-SEARCH.md` | Added | 按 CC-015 测试矩阵记录 51 项单测和 Playwright 执行证据、缺口及 HVR 移交 | ATR Standard v1.0.0 | IHR-003 |
| `docs/context/history/ATR-GS-MULTI-CONDITION-SEARCH.md` | Modified | 追加 8091 `001` 数据诊断，并标识其运行版尚未加载 CC-015 代码 | CC-015 §17 / ATR RUN-009 | IHR-004 |

## 6. 偏离与停止条件记录（Deviation / Stop Condition Record）

- **Deviation：** None。
- **Stop Conditions：** None triggered. Database-backed validation is pending; this is not a contract deviation or permission to bypass the validation gate.
- 后续若 Published version/checksum 与 CC-015 §2.3 不符，或实现要求改变冻结范围，必须停止并追加记录；不得以 IHR 替代契约修订与批准。

## 7. 遗留问题与后续（Open Issues / Follow-up）

Open Issues: Database-backed Contains cross-field fixtures; complete module and performance regressions; FR. Human HVR passed per IHR-007 / ATR RUN-013.

实现中发现的配置、兼容性、安全或上游设计问题应按本节新增条目，并在解决后将状态更新为 Resolved；不得删除历史问题记录。

## 8. 移交摘要（Handoff）

```text
Implemented：核心多词搜索调用链已接入；ATR 有条件完成，Playwright 模拟已执行
Actual Files：见 §5
Open Issues：数据库型 Contains 跨字段 fixture、完整/性能回归、FR；人工 HVR 已通过
Deviation：None
Stop Conditions Triggered：None
ATR：见 [ATR-GS-MULTI-CONDITION-SEARCH.md](./ATR-GS-MULTI-CONDITION-SEARCH.md)；状态 PARTIAL，HVR 已通过。FR：待完成。
```

IHR 仅记录实施事实；测试通过、人工验收及 CC Closure 由 ATR、HVR、FR 分别处理。
