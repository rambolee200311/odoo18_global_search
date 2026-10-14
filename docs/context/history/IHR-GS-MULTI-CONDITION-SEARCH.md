# IHR-GS-MULTI-CONDITION-SEARCH

## 0. 文档治理

| 项 | 内容 |
|---|---|
| 文档类型 | Implementation History Record |
| Intent ID | `CC-015` |
| 状态 | Implementation Complete；FR v0.1 评估为 SATISFIED |
| 上游模板 | IHR Standard Template v1.0.0 FROZEN |
| 维护原则 | Current Snapshot 可更新；Implementation History 与 Stop/Deviation 记录仅追加 |

## 1. 执行元数据（Execution Metadata）

| 字段 | 值 |
|---|---|
| IHR 文档 | `IHR-GS-MULTI-CONDITION-SEARCH.md` |
| Intent ID | `CC-015` |
| CC | [CC-015 v0.5 AMENDED / APPROVED](../intent/CC-015_multi_condition_search.md) |
| 模块 | `wd_global_search` |
| 工作类型 | 多条件搜索功能 |
| 实施负责人 | Copilot assistant |
| 开始时间 | 2026-10-13 |
| 最后更新 | 2026-10-14 |
| 当前实施状态 | Implementation Complete；FR v0.1 评估为 SATISFIED |
| Branch / Base Commit | `main` / `63a2df2` |
| Implementation Commit | `0e43bff` |

## 2. Coding Contract 基线

- CC-015 v0.3 曾冻结 Exact-only 多词语义；用户于 2026-10-13 批准 v0.4 修订：Char/Text 字段对多词 token 使用 Contains，token AND、权限边界、单 token 和结构化条件兼容仍保留。
- 用户于 2026-10-14 批准 v0.5 修订，豁免本轮 CC15-TEST-041 执行，保留 SKIPPED 且不声明性能基线。
- 外部 SearchRequest、路由、响应形状、Resource、Refinement、分页和 cursor 继续遵守 CC-002/005/012；权限遵守 CC-003；错误遵守 CC-007；日志遵守 CC-008。
- 具体行为、不变量、测试、停止条件和完成定义引用 [CC-015](../intent/CC-015_multi_condition_search.md) §§3–20；实施触点引用 §22。
- CC-015 使用 `CC15-INV-*`、`CC15-TEST-*` 与 `CC15-DEC-*` 作为本轮追溯 ID；不在 IHR 中另造 CC-CHANGE/CC-PRESERVE 语义。
- Published 配置基线：`global_search_baseline` version 5，checksum `4cd6cb4e0e59b2116bd7261bb8f9e8f504c1970e3bee90ea7b07dd510f00597b`；Sales Order 的字段/Relation Paths 证据见 CC-015 §2.3。

## 3. 当前实施状态摘要（Current Implementation Status Summary）

| 项 | 当前状态 |
|---|---|
| CC-015 实施行为 | v0.4 搜索语义已接入；v0.5 豁免本轮 TEST-041 执行；日期/状态 Refinement 使用默认收起的原生折叠组，8091 已验证初始收起及鼠标/键盘切换 |
| Preservation Impact | 聚焦 harness 60 项通过；定向 Odoo 模块套件 77 项全部通过，其中新增 14 项 CC15 TransactionCase 关闭所有此前 NOT RUN 场景；audit-event 精确断言包含在 RUN-028 77 项模块套件中；TEST-041 按 DEC-027 豁免且无性能通过声明 |
| Deviation | None |
| Stop Condition 触发 | No；开始实施前已完成 Published snapshot 核验 |
| Open Issues | 无阻塞 CC-015 收口的事项；TEST-041 依 CC15-DEC-027 豁免且没有性能基线；人工 HVR 已由用户确认通过 |
| Revert 发生 | No |
| 当前状态 | Implementation Complete；Closure Assessment 见 FR v0.1 |

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
- **Follow-up：** 当时数据库型 `TransactionCase`、完整模块/性能回归及 FR 仍待完成；后续验证进展见 IHR-008。

### IHR-008 — 完成模块回归并复核 8091 搜索行为

- **时间：** 2026-10-13
- **阶段：** Verification
- **Action：** 修复导航测试 fixture，使其包含有效 Published Exact/B-tree `name` Searchable Field；将 request-boundary、index、i18n、observability 测试注册到模块测试入口；修正 observability logger mock 的 Odoo addons namespace。随后运行完整 `wd_global_search` Odoo 模块套件和聚焦 harness，并在已有 8091 页面只读复核 `001 chair`、`001`、`001 OR chair`。
- **Reason：** 使既有 TransactionCase 与模块测试在 CC-015 发布校验约束下可执行，并补充模块回归及当前部署行为证据；不将整体测试结果扩大解释为全部 43 项契约测试通过。
- **Files / Components：** `mymodules/wd_global_search/tests/__init__.py`、`tests/test_navigation.py`、`tests/test_observability.py`、现有 `odoo18ce` 模块测试环境、8091 Workspace、[ATR-GS-MULTI-CONDITION-SEARCH.md](./ATR-GS-MULTI-CONDITION-SEARCH.md) RUN-014~RUN-016。
- **Contract Reference：** CC-015 §§16–18；CC15-TEST-001/004/012/015/019/023/043；CC-003、CC-014-2、TD-001 回归边界。
- **Validation：** 第一次模块运行有 3 项导航测试因 fixture 不满足 Publish-time Searchable Field 校验而失败；修复后完整 Odoo 模块套件 63/63 通过（0 FAIL、0 ERROR，包含 TransactionCase）。Odoo addons namespace 聚焦 harness 60/60 通过。8091 页面 `001 chair` 显示 token AND、Sales Order Count 11；每页 10 条时为 `1–10 of 11`，改为 20 条时为 `1–11 of 11`；首项 S00001 含 Office Chair。单词 `001` 显示 Count 1190；`001 OR chair` 显示 `FAILED` / `No conditions`。详细证据见 ATR。
- **Result：** 完整模块测试及本轮只读浏览器复核通过；ATR 更新为 14/43 项 PASS、29 项 NOT RUN，状态仍为 PARTIAL。
- **Deviation：** None。只调整测试注册和测试 fixture/mock；浏览器只读，不修改业务记录或 Published 配置。
- **Follow-up：** 剩余契约级自动化、专门的 Contains 跨字段 ORM fixture、性能/日志运行时/多用户验证及 FR 仍待完成；RUN-016 是 Playwright 复核，不是新的人工 HVR。

### IHR-009 — 探测 20 并发性能测试的用户限流边界

- **时间：** 2026-10-13 15:26 +08:00
- **阶段：** Verification
- **Action：** 在现有 8091 已认证会话中，通过 Search API 同时发送 20 个只读请求（`query=001`、Sales Order、`limit=1`），观察状态和响应时间；不修改业务记录或配置。
- **Reason：** 按用户批准开始 CC15-TEST-041 受控并发验证，先确认实际并发是否受当前用户限流约束。
- **Files / Components：** 现有 `odoo18ce` / 8091 Search API、`services/limiter.py`、[ATR-GS-MULTI-CONDITION-SEARCH.md](./ATR-GS-MULTI-CONDITION-SEARCH.md) RUN-017。
- **Contract Reference：** CC-015 §13、CC15-TEST-041；CC-002 超时预算。
- **Validation：** 20 个请求中 3 个返回 `SUCCESS`、Count 1190 和 1 条结果，响应约 130ms；17 个返回 `FAILED/RATE_LIMITED`。现有 `UserLimiter` 每用户最多 3 并发，因此混合响应不能作为 20 个实际搜索并发的性能样本；没有据此计算 P50/P95/P99。
- **Result：** CC15-TEST-041 状态 BLOCKED；观察到同一用户的限流行为，不代表整体搜索性能基线完成。
- **Deviation：** None。使用现有登录用户和已授权数据库，只读请求；未更改限流配置、使用管理员权限或新建数据库。
- **Follow-up：** 需至少 7 个已授权测试用户会话（每人最多 3 个并发）或等价隔离测试安排，才能执行 20 个有效并发搜索；不得在聊天中传递密码。

### IHR-010 — Search API 条件共存补测与执行字段边界修复

- **时间：** 2026-10-13
- **阶段：** Verification / Fix
- **Action：** 使用现有 8091 已认证会话执行只读 Search API 探测：多条结构化条件、完整 `partner_id.name` Contains 路径、`query` 与条件共存，以及条件对象附加 `model`。发现 API 接受 `model: res.users` 后，在 `request_boundary.py` 增加对 `model`、`action`、`domain`、`relation_expression` 的拒绝校验，并为四类字段增加回归断言；用户授权重载 8091 后，通过相同会话重放四种负例。
- **Reason：** 补齐 CC-015 §8.2 / CC15-TEST-003、010、034、035 的公开 API 证据，并修复发现的请求边界缺口。
- **Files / Components：** `services/request_boundary.py`、`tests/test_request_boundary.py`、现有 8091 Search API、[ATR-GS-MULTI-CONDITION-SEARCH.md](./ATR-GS-MULTI-CONDITION-SEARCH.md) RUN-018。
- **Contract Reference：** CC-015 §§8.2、12、17；CC15-TEST-003/010/034/035；TD-001 请求边界。
- **Validation：** 两条 `name = ...` 条件返回 `SUCCESS`、Count 2、IDs 1 和 19；完整 `partner_id.name` Contains 返回 `SUCCESS`、Count 5；`query=001` 与不同维度 `partner_id.name contains Acme` 共存并返回 `SUCCESS`、Count 1、ID 1。API 修复前接受 `model: res.users`。修复后在 Odoo addons namespace unittest harness 执行 `test_request_boundary` 全部 12 项，12 PASS、0 FAIL。重载后四种字段负例均返回业务状态 `FAILED` 和错误 `INVALID_REQUEST`。Odoo CLI 的定向 tag 命令未收集这些 `unittest.TestCase` 用例（报告 0 tests），因此改用 namespace unittest harness 验证。
- **Result：** CC15-TEST-003、010、034、035 均有通过证据；TEST-034 修复前的边界缺口已通过 8091 运行时复验关闭。
- **Deviation：** None。Search API 探测为只读；未修改业务记录、Published 配置、限流、权限或数据库内容。
- **Follow-up：** TEST-034/ATR-ISSUE-007 已关闭；继续补充其余 CC15-TEST 证据。性能基线仍需至少 7 个已授权用户会话或等价隔离安排。

### IHR-011 — Resource/API/Refinement 补测与 dimension 失败关闭修复

- **时间：** 2026-10-13
- **阶段：** Verification / Fix
- **Action：** 使用现有 8091 已认证 Workspace/Search API 补测 CC15-TEST-021/024/025/033/037/038/040。Playwright 验证首次搜索全选授权 Resource、多选切换、selection scope 和 Facet Count；API 验证 offset/cursor、Raw Query 与日期 Refinement 共存、伪造请求权限声明不改变结果。发现运行中的 8091 接受未发布直接 dimension，遂在 `facade.py` 增加未知 dimension 失败关闭，并在 `test_service_core.py` 增加回归测试。未重载服务；该运行时失败仍待复验。另发现 `state=sale` 被静默忽略；因 Published State Mapping 的值编码/映射规则未形成可执行定义，未猜测并改写服务语义。
- **Reason：** 补充 CC-015 测试矩阵的目标端证据，并修复 TEST-040 的本地实现缺口；隔离记录无法据现有契约安全修复的 State Refinement 问题。
- **Files / Components：** `services/facade.py`、`tests/test_service_core.py`、现有 8091 Workspace/Search API、[ATR-GS-MULTI-CONDITION-SEARCH.md](./ATR-GS-MULTI-CONDITION-SEARCH.md) RUN-019。
- **Contract Reference：** CC-015 §§8、11、12、17；CC15-TEST-021/024/025/033/037/038/040；CC-005 Refinement；CC-012 Selector/Facet Count。
- **Validation：** Playwright：首次 `Acme` 请求提交 7 个授权 Resource；Contact/Purchase Order/Sales Order Facet Count 分别为 1/4/5；取消 Contact 后结果 count 从 10 降至 9，Facet Count 不变。API：`001` count 1190，首屏 IDs `[1,10]`，offset/cursor 第二页均为 `[11,12]`；`001 chair` 加/删 `date=this_month` 得到 count 11/5/11，`this month` token 与日期条件并存；附加伪造 uid/company/groups/permissions 后结果与基线一致。State Refinement 加入前后均 count 1190 且 Effective Conditions 不含 state。未发布 dimension 在当前线上进程返回 SUCCESS/count 5129；本地 request-boundary + Search Core 定向测试 38 项全部通过，`git diff --check` 通过，但不能替代运行时复验。
- **Result：** TEST-021/024/025/033/037 PASS；TEST-038/040 在当前目标端 FAIL。TEST-040 本地修复已通过定向回归，需在授权重载后再次验证；State Refinement 需先澄清 Published State Mapping 契约语义。
- **Deviation：** None。所有线上请求只读；未修改业务记录、Published 配置、权限、限流或数据库数据。
- **Follow-up：** 请求用户授权重载 8091 后复验 TEST-040；不在 State Mapping 值格式未定义时擅自实现 TEST-038。

### IHR-012 — TEST-040 授权重载后复验

- **时间：** 2026-10-13
- **阶段：** Verification
- **Action：** 用户授权重载现有 8091 Odoo 服务，并通过原已认证只读 Workspace 会话重放 `not_published_dimension` 直接 Refinement 请求。
- **Reason：** 验证 IHR-011 中本地失败关闭修复是否已由目标服务加载，并满足 CC15-TEST-040 的运行时拒绝要求。
- **Files / Components：** 8091 Odoo 服务、[ATR-GS-MULTI-CONDITION-SEARCH.md](./ATR-GS-MULTI-CONDITION-SEARCH.md) RUN-020。
- **Contract Reference：** CC-015 §§8、12、17；CC15-TEST-040；TD-001 失败关闭边界。
- **Validation：** TEST-040 Search API 返回业务状态 `FAILED`、`INVALID_REQUEST`、count=0、results 长度 0；Effective Conditions 为空。重载后多词正例 `001 chair` 仍为 SUCCESS/count=11；`model`、`action`、`domain`、`relation_expression` 四种 client 字段仍返回 FAILED/INVALID_REQUEST、count=0、无结果。Workspace HTTP 入口响应正常。
- **Result：** TEST-040 PASS；ATR-ISSUE-008 已解决。
- **Deviation：** None。只执行失败请求；未修改业务记录、Published 配置、权限或限流。
- **Follow-up：** TEST-038 State Refinement 仍未通过；按 TDD 的 `business_state -> technical_values[]` 映射核实 Published 配置与当前 UI 值后再实施，不猜测值编码。

### IHR-013 — Published State Mapping 与 Refinement 边界核验

- **时间：** 2026-10-13
- **阶段：** Verification / Contract Gap
- **Action：** 在授权重载后的服务上以 CC-005 示例值 `draft` 和当前 UI 值 `sale` 重放 State Refinement；再通过当前用户的 Odoo ORM 只读读取 Published version 5 的 Sales Order State Mapping。没有使用 `sudo()` 或直接数据库访问。
- **Reason：** 判定 TEST-038 是否使用有效 Published State Refinement，并避免因 TEST-040 失败关闭修复误将合法状态维度作为未发布 dimension。
- **Files / Components：** 8091 Search API、Published `wd.gs.business.resource` / `wd.gs.state.mapping` ORM records、[ATR-GS-MULTI-CONDITION-SEARCH.md](./ATR-GS-MULTI-CONDITION-SEARCH.md) RUN-021。
- **Contract Reference：** CC-005 §§2–3；TDD §4.5 `business_state -> technical_values[]`；CC-015 §17 / CC15-TEST-038。
- **Validation：** `state=draft` 和 `state=sale` 均被当前 Search API 返回 `FAILED/INVALID_REQUEST`、count=0、无结果。Published `sale_order` mappings 为 `Quotation → draft,sent`、`Sales Order → sale`、`Cancelled → cancel`；静态 Workspace 选项则是 `Draft/draft`、`Confirmed/sale`、`Done/done`。
- **Result：** TEST-038 FAIL。Raw Query 文本本身不被改写，但 Published business-state label 与静态 UI option 不协调，State Mapping 未进入执行；需要决定多 Resource 的 state option 合并和不支持状态处理。
- **Deviation：** None。只读 ORM/API 检查；未修改数据、配置、契约或代码。
- **Follow-up：** 向用户确认状态选择器应动态使用选中 Resource 的 Published `business_state`，以及没有共同状态/Resource 未配置状态映射时的筛选行为；确认前不实现猜测逻辑。

### IHR-014 — CC15-TEST-038 State Refinement mapping 实施与运行时验证

- **时间：** 2026-10-13
- **阶段：** Implementation / Verification
- **Action：** 按用户确认的规则，从已选 Resource 的 Published mappings 生成共同 business-state 选项；无共同状态时禁用状态筛选。将业务状态标签交由服务端映射到 Published technical values，并增加字段权限校验和回归测试。
- **Reason：** 解决 IHR-013 核实的 Published business-state 与旧静态 UI 选项不一致，以及 State Refinement 被失败关闭校验拒绝的问题；保持 Raw Query、Refinement 和查询语义边界。
- **Files / Components：** `services/facade.py`、`services/conditions.py`、`services/executor.py`、`controllers/main.py`、`static/src/js/preview.js`、`tests/test_service_core.py`、[ATR-GS-MULTI-CONDITION-SEARCH.md](./ATR-GS-MULTI-CONDITION-SEARCH.md) RUN-022。
- **Contract Reference：** CC-005 §§2–3；TDD §4.5 `business_state -> technical_values[]`；CC-015 §§8–12、17 / CC15-TEST-038；用户确认的多 Resource 共同状态规则。
- **Validation：** 58 项 request-boundary、service-core、field-path、permission-boundary、index-strategy 单测通过；Python compileall、`node --check`、`git diff --check` 通过。Playwright 在 8091 验证全选 Resource 时无共同状态、状态筛选禁用；仅选 Sales Order 时选项为 Published `Quotation`、`Sales Order`、`Cancelled`。`query=001` 的 Sales Order count 从无状态 Refinement 时 1190 收窄至选择 `Sales Order` 后 46；Query Understanding 显示 `name=001 · state=Sales Order`。
- **Result：** TEST-038 PASS；ATR CC15-TEST 状态更新为 PASS 25、FAIL 0、BLOCKED 1、NOT RUN 17。
- **Deviation：** None。经用户授权重启 8091 加载工作区代码，未执行模块升级；未使用 `sudo()`、直接数据库访问，也未修改业务记录或 Published 配置。
- **Follow-up：** 继续处理 17 项 NOT RUN、1 项 BLOCKED、专用 Contains 跨字段 ORM fixture、日志/多用户运行时验证及 FR。

### IHR-015 — 剩余 CC15-TEST 补测启动与证据边界

- **时间：** 2026-10-13
- **阶段：** Verification / Test Gap
- **Action：** 在 `test_service_core.py` 增加 parser 被禁用时 executor 直接消费规范化条件的 fake-model 单测；执行 30 项 Search Core 测试。另从 Workspace 卡片取得 `open_result` 路由并在已认证浏览器中验证其重定向结果。
- **Reason：** 启动对剩余 CC15-TEST NOT RUN 项的逐项补测，同时区分支持性单测与 Coding Contract 明确要求的受控 ORM/浏览器证据。
- **Files / Components：** `tests/test_service_core.py`、8091 Workspace `open_result` route、[ATR-GS-MULTI-CONDITION-SEARCH.md](./ATR-GS-MULTI-CONDITION-SEARCH.md) RUN-023。
- **Contract Reference：** CC-015 §§4.5、17（CC15-TEST-008/020/032）。
- **Validation：** `test_service_core` 30/30 PASS；executor/parser-isolation 用 fake model 证明 executor 不调用 parser，但尚未满足 TEST-008/032 的受控 ORM fixture 要求。`open_result?resource_key=sale_order&record_id=1` 重定向至 `/odoo/action-499/1?action=499&model=sale.order&resId=1`；浏览器工具未捕获双击产生的新标签。
- **Result：** 本次未关闭任何 CC15-TEST ID；TEST-020、TEST-008、TEST-032 仍保持 NOT RUN。
- **Deviation：** None。测试未修改业务数据或 Published 配置。
- **Follow-up：** 继续建立隔离 ORM fixtures 并补测其余 NOT RUN 项；只有完整满足 CC 定义的断言后才更新 ATR 状态。

### IHR-016 — CC15-TEST-020 Workspace Form Action 导航

- **时间：** 2026-10-13
- **阶段：** Verification
- **Action：** 从 Workspace 中 `S00001` 结果卡确认生成的 `open_result` 资源/记录参数，并在现有已认证浏览器会话打开相同路由。
- **Reason：** 验证导航由 Published Form Action 决定，且导航记录与匹配结果一致，不接受客户端指定 action/model。
- **Files / Components：** Workspace Result Card、`controllers/main.py` `open_result`、[ATR-GS-MULTI-CONDITION-SEARCH.md](./ATR-GS-MULTI-CONDITION-SEARCH.md) RUN-024。
- **Contract Reference：** CC-013 Navigation Contract；CC-015 §§12、17 / CC15-TEST-020。
- **Validation：** `/wd_global_search/open_result?resource_key=sale_order&record_id=1` 重定向到 `/odoo/action-499/1?action=499&model=sale.order&resId=1`，model 和 record ID 与 Workspace card 一致。
- **Result：** TEST-020 PASS；ATR 当前为 PASS 26、FAIL 0、BLOCKED 1、NOT RUN 16。
- **Deviation：** None。仅导航至已授权的只读 Odoo form；未修改记录。
- **Follow-up：** 继续补测 16 项 NOT RUN 及独立性能阻塞项。

### IHR-017 — CC15-TEST-026 敏感日志运行时检查

- **时间：** 2026-10-13
- **阶段：** Verification
- **Action：** 从已认证 Workspace 提交包含唯一 token 的只读搜索请求，按 API 返回的 request ID 定位 Odoo observability event，并核对日志字段。
- **Reason：** 验证 CC-008 日志 allowlist 在真实 Search API 请求下不记录 Raw Query、token、完整条件、SQL 或 relation path。
- **Files / Components：** Search Workspace、`/wd_global_search/api/search`、`services/observability.py`、`/tmp/odoo_cc014_2_server.log`、[ATR-GS-MULTI-CONDITION-SEARCH.md](./ATR-GS-MULTI-CONDITION-SEARCH.md) RUN-025。
- **Contract Reference：** CC-008 Logging Contract；CC-015 §17 / CC15-TEST-026。
- **Validation：** `ATR026_MARKER_20261013_1730` 搜索返回 HTTP 200、`EMPTY` 和 request ID `840ab118-4af7-470e-acc4-de06ce3c1e48`；对应 `gs.search.completed` 日志仅含 allowlist 元数据及 query/conditions hash，不含唯一 token 或其他敏感原文。
- **Result：** TEST-026 PASS；ATR 当前为 PASS 27、FAIL 0、BLOCKED 1、NOT RUN 15。
- **Deviation：** None。探针只读，未修改业务数据、配置或代码。
- **Limitation：** 请求未含非空结构化 conditions；audit event 语义未单独验证。
- **Follow-up：** 继续补测 15 项 NOT RUN、1 项并发性能阻塞及 audit event 语义。

### IHR-018 — CC15-TEST-006 CQO 边界验证

- **时间：** 2026-10-13
- **阶段：** Implementation / Verification
- **Action：** 在请求边界增加 CQO 类型、AND combinator、关键词/字段条件形状及必需字段验证；补充合法和非法 CQO 单元测试。
- **Reason：** CC15-TEST-006 明确要求在执行前拒绝错误类型、缺失值、不支持 combinator 和超限嵌套；原有测试未覆盖完整 CQO 负例。
- **Files / Components：** `services/request_boundary.py`、`tests/test_request_boundary.py`、[ATR-GS-MULTI-CONDITION-SEARCH.md](./ATR-GS-MULTI-CONDITION-SEARCH.md) RUN-026。
- **Contract Reference：** CC-015 §§4.2、4.5、17 / CC15-TEST-006。
- **Validation：** `test_request_boundary` 与 `test_service_core` 共 44 项 PASS；涵盖合法 CQO、错误对象类型、缺维度/值、非标量值、OR combinator 和过深嵌套。
- **Result：** TEST-006 PASS；ATR 当前为 PASS 28、FAIL 0、BLOCKED 1、NOT RUN 14。
- **Deviation：** None。缺维度/值现在显式失败关闭，避免条件合并时静默丢弃无效条件。
- **Limitation：** 该测试不替代 ORM Contains fixture、权限隔离或其他未运行项。
- **Follow-up：** 继续补测 14 项 NOT RUN 和 1 项并发性能阻塞。

### IHR-019 — 按用户指示跳过 CC15-TEST-041

- **时间：** 2026-10-13
- **阶段：** Scope Decision
- **Action：** 按用户要求不再执行并发性能测试，将 CC15-TEST-041 从 BLOCKED 更新为 SKIPPED。
- **Reason：** 用户明确表示“并发测试就忽略”；保留 RUN-017 的限流历史，但不把它当成性能通过证据。
- **Files / Components：** [ATR-GS-MULTI-CONDITION-SEARCH.md](./ATR-GS-MULTI-CONDITION-SEARCH.md) 测试矩阵、状态摘要及 Run History。
- **Contract Reference：** CC-015 §17 / CC15-TEST-041。
- **Validation：** 43 项矩阵统计为 PASS 28、FAIL 0、SKIPPED 1、BLOCKED 0、NOT RUN 14。
- **Result：** 并发测试不属于当前验收范围；性能基线仍未建立。
- **Deviation：** None。该项明确标记为 SKIPPED，不声称性能通过。
- **Follow-up：** 无；只有用户重新要求时才恢复 TEST-041。

### IHR-020 — 完成剩余 14 项 CC15 TransactionCase

- **时间：** 2026-10-14
- **阶段：** Verification
- **Action：** 新增 14 个 CC15 契约 TransactionCase，覆盖真实 ORM Contains/结构化条件、adapter 权限集合、parser 隔离、根记录 AND、Query Understanding、字段组授权、两用户/多公司、Portal Record Rules、跨 Resource、空查询 ORM Count 基线、无效配置发布错误区分及 Unicode。
- **Reason：** 按 CC-015 §17 关闭先前保留为 NOT RUN 的 14 个契约测试，不以已有单元测试替代 ORM/ACL 证据。
- **Files / Components：** `mymodules/wd_global_search/tests/test_cc015_contract.py`、`mymodules/wd_global_search/tests/__init__.py`、[ATR-GS-MULTI-CONDITION-SEARCH.md](./ATR-GS-MULTI-CONDITION-SEARCH.md)。
- **Contract Reference：** CC15-TEST-005/007/008/009/011/013/022/029/030/031/032/036/039/042。
- **Validation：** `./odoo-bin -c odoo.conf -d odoo18ce --test-enable --test-tags /wd_global_search --stop-after-init --http-port=0 --max-cron-threads=0 --log-level=test`；`wd_global_search` 共 77 tests，0 failures、0 errors；`python3 -m compileall` 与 `git diff --check` 通过。
- **Result：** 14/14 previously NOT RUN CC15 tests PASS；矩阵更新为 42 PASS、1 SKIPPED、0 NOT RUN。
- **Deviation：** None。数据库型 fixture 使用 TransactionCase 回滚；未使用直接 SQL、未升级模块、未更改 Published 配置或业务记录。
- **Limitation：** 首次使用 `--test-file` 的尝试观察到运行范围扩展至 `account` addon 后停止，不作为证据；最终有效运行使用 `/wd_global_search` test tag 精确限定。TEST-041 仍按用户指示跳过。
- **Follow-up：** 完成 audit-event 回归并生成 FR；只有用户重新要求时才恢复 TEST-041。

### IHR-021 — 将日期与状态 Refinement 设为默认收起组

- **时间：** 2026-10-14
- **阶段：** Implementation
- **Action：** 使用原生 `<details>/<summary>` 将日期预设、起止日期和状态控件组合为默认收起的筛选组；保留原有控件 ID，将活动筛选标签留在组外可见，并更新响应式样式与 CSS 缓存版本。
- **Reason：** 按用户要求减少 Workspace 初始筛选区占用，同时保留键盘可操作性、活动条件可见性和既有筛选行为。
- **Files / Components：** `mymodules/wd_global_search/controllers/main.py`、`mymodules/wd_global_search/static/src/css/preview.css`。
- **Contract Reference：** CC-005 Refinement；用户确认的展示交互要求。未改变 Search API、筛选字段或搜索语义。
- **Validation：** Controller `compileall`、`preview.js` `node --check`、`git diff --check` 通过；模板结构检查确认控件位于无 `open` 属性的折叠组内，活动筛选标签位于组外。
- **Result：** 工作区模板、样式和缓存版本已更新。
- **Deviation：** None。
- **Limitation：** 未重载 8091 Odoo 服务，尚未在已认证 Workspace 中验证渲染后的展开/收起交互。
- **Follow-up：** 重载使用当前工作区代码的 Odoo 服务后，确认初始收起、点击/键盘展开和日期/状态筛选联动。

### IHR-022 — 重载 8091 并验证日期/状态筛选组

- **时间：** 2026-10-14
- **阶段：** Verification
- **Action：** 按用户要求以原启动参数重启 8091 Odoo 服务，重载已认证 Workspace 页面；检查 disclosure 初始状态、控件可见性及鼠标/键盘切换。
- **Reason：** 完成 IHR-021 留下的运行时 UI 验证。
- **Files / Components：** Odoo 8091 Search Workspace、`mymodules/wd_global_search/controllers/main.py`、`mymodules/wd_global_search/static/src/css/preview.css`。
- **Contract Reference：** CC-005 Refinement；IHR-021；用户重载指令。
- **Validation：** `GET /web/login` 返回 HTTP 200；浏览器实测初始 `details.open=false` 且日期控件不可见，点击 summary 后 `open=true` 且控件可见，再按 Enter 后折叠。
- **Result：** 8091 服务与 Workspace 页面正常响应；默认收起、点击展开和键盘收起均通过。
- **Deviation：** None。
- **Follow-up：** None for the disclosure interaction。

### IHR-023 — 批准 CC-015 v0.5 测试范围修订

- **时间：** 2026-10-14
- **阶段：** Contract Amendment
- **Action：** 用户明确选择正式修订 CC-015 并接受本轮 CC15-TEST-041 跳过后关闭；在 CC-015 v0.5 / DEC-027 中记录该豁免，保留 SKIPPED 和无性能基线事实。
- **Reason：** 形成对并发性能测试豁免的明确契约授权，避免将未执行测试误记为 PASS 或 N/A。
- **Files / Components：** `docs/context/intent/CC-015_multi_condition_search.md`。
- **Contract Reference：** CC-015 v0.5 §20、CC15-DEC-027。
- **Validation：** 用户在本会话明确选择“正式修订 CC-015，接受 TEST-041 跳过后关闭”；本轮性能符合性仍未验证。
- **Result：** v0.5 amendment approved; the remaining 42 required test IDs retain PASS evidence, while TEST-041 remains SKIPPED.
- **Deviation：** Approved amendment. No performance baseline or performance compliance claim.
- **Follow-up：** 将豁免、回归证据与当前实现基线纳入 FR。

### IHR-024 — 追溯 audit-event 回归证据

- **时间：** 2026-10-14
- **阶段：** Verification
- **Action：** 将 `TestGlobalSearchConfiguration.test_publish_creates_canonical_snapshot_and_audit` 映射至 RUN-028 的 77/77 模块套件结果；测试断言 publish 后恰有一个对应 domain/action 的 `wd.gs.audit.event`。
- **Reason：** 关闭此前将 configuration audit-event 语义列为待验证的证据映射缺口。
- **Files / Components：** `mymodules/wd_global_search/tests/test_configuration.py`、`mymodules/wd_global_search/tests/__init__.py`、[ATR-GS-MULTI-CONDITION-SEARCH.md](./ATR-GS-MULTI-CONDITION-SEARCH.md)。
- **Contract Reference：** CC-015 §18 / CC-008；RUN-028。
- **Validation：** `test_configuration` 已由测试入口注册；RUN-028 记录该 Odoo 模块套件 77 tests、0 failures、0 errors。
- **Result：** Configuration audit-event creation/count regression 有 RUN-028 PASS evidence；不将其扩大解释为搜索 observability log 测试。
- **Deviation：** None。
- **Follow-up：** 在 ATR 回归矩阵中明确映射此测试，完成 FR。

### IHR-025 — 验证 Search API 使用服务端用户语言/时区上下文

- **时间：** 2026-10-14 10:03 +08:00
- **阶段：** Verification
- **Action：** 在重载后的 8091 已认证页面，对同一只读 Search API 请求执行基线与伪造客户端 `lang`、`tz`、`locale`、`timezone` 字段的对照；请求包含 `001 chair` 和 `date=this_month`。
- **Reason：** 关闭 CC-015 §18 中 CC-009 服务端用户语言/时区及日期 Refinement 回归的证据缺口。
- **Files / Components：** `controllers/main.py`、`services/facade.py`、[ATR-GS-MULTI-CONDITION-SEARCH.md](./ATR-GS-MULTI-CONDITION-SEARCH.md) RUN-030。
- **Contract Reference：** CC-015 §18；CC-009 §§2.1、2.3；ATR RUN-030。
- **Validation：** 两次响应均为 `SUCCESS`、Count 5、effective conditions 与 record IDs 一致；代码路径由 `request.env` 构造上下文，`user_context` 仅从 `env.user` 读取语言及时区。
- **Result：** PASS for the CC-015 regression scope; does not claim full CC-009 acceptance.
- **Deviation：** None。使用现有用户和只读 API 请求，未修改配置或业务数据。
- **Limitation：** 本验证仅覆盖 CC-015 相关的客户端上下文边界和日期筛选，不替代 CC-009 的完整 i18n/HVR 验收。
- **Follow-up：** None for the CC-015 regression scope。

### IHR-026 — 提交实现基线并完成收口评估

- **时间：** 2026-10-14
- **阶段：** Closure
- **Action：** 将已验证的实现、契约修订和证据记录提交为 `0e43bff`；对比提交前后代码基线一致性后，依据 CC-015 v0.5、IHR 与 ATR 生成 FR v0.1。
- **Reason：** 固定当前实现 baseline，并完成用户已批准的 CC-015 收口评估。
- **Files / Components：** CC-015 实现与契约变更、[ATR-GS-MULTI-CONDITION-SEARCH.md](./ATR-GS-MULTI-CONDITION-SEARCH.md)、本 IHR、[FR-GS-MULTI-CONDITION-SEARCH.md](./FR-GS-MULTI-CONDITION-SEARCH.md)。
- **Contract Reference：** CC-015 v0.5 §20；CC15-DEC-027；FR §§1–14。
- **Validation：** 被测代码原样包含在提交 `0e43bff`；提交后未修改运行时代码；静态检查和 RUN-028/RUN-029/RUN-030 证据均映射到该实现基线。
- **Result：** FR v0.1 判定 CC-015 `SATISFIED`；不构成 Merge 或 Release 批准。
- **Deviation：** None。
- **Limitation：** CC15-TEST-041 依批准的 DEC-027 保留 `SKIPPED`；未取得性能基线且不声称性能符合性。
- **Follow-up：** Human Review；后续独立性能验收另行安排。

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
| `tests/__init__.py` | Modified | 注册 request-boundary、index、i18n、observability 测试模块 | CC-015 §17 / module regression | IHR-008 |
| `tests/test_navigation.py` | Modified | 为导航 TransactionCase fixture 配置有效 Exact/B-tree `name` Searchable Field | CC-015 §16 / Publish-time Validation | IHR-008 |
| `tests/test_observability.py` | Modified | 使用 `odoo.addons.wd_global_search...` 标准 addons namespace mock logger | CC-008 / module regression | IHR-008 |
| `docs/context/history/ATR-GS-MULTI-CONDITION-SEARCH.md` | Modified | 追加 63 项模块套件、60 项聚焦测试和 8091 浏览器复核证据；维持逐项覆盖缺口 | ATR Standard v1.0.0 | IHR-008 |
| `docs/context/history/IHR-GS-MULTI-CONDITION-SEARCH.md` | Modified | 记录模块测试修复、回归结果和剩余验证范围 | IHR Standard §4 | IHR-008 |
| `docs/context/history/ATR-GS-MULTI-CONDITION-SEARCH.md` | Modified | 追加 20 并发限流探测；将 CC15-TEST-041 记为 BLOCKED，而非性能 PASS | ATR Standard v1.0.0 | IHR-009 |
| `docs/context/history/IHR-GS-MULTI-CONDITION-SEARCH.md` | Modified | 记录每用户并发限制、有效性能测试前置条件和用户协助需求 | IHR Standard §4 | IHR-009 |
| `docs/context/history/ATR-GS-MULTI-CONDITION-SEARCH.md` | Added | 按 CC-015 测试矩阵记录 51 项单测和 Playwright 执行证据、缺口及 HVR 移交 | ATR Standard v1.0.0 | IHR-003 |
| `docs/context/history/ATR-GS-MULTI-CONDITION-SEARCH.md` | Modified | 追加 8091 `001` 数据诊断，并标识其运行版尚未加载 CC-015 代码 | CC-015 §17 / ATR RUN-009 | IHR-004 |
| `services/request_boundary.py` | Modified | 拒绝条件对象中的 client `model`、`action`、`domain`、`relation_expression` 执行字段 | CC-015 §§8.2、12；CC15-TEST-034 | IHR-010 |
| `tests/test_request_boundary.py` | Modified | 覆盖四类 client execution fields 必须失败关闭 | CC-015 §17；CC15-TEST-034 | IHR-010 |
| `docs/context/history/ATR-GS-MULTI-CONDITION-SEARCH.md` | Modified | 记录 API 正例、TEST-034 修复前失败及修复后的单测证据；等待 live API 复验 | ATR Standard v1.0.0 | IHR-010 |
| `docs/context/history/IHR-GS-MULTI-CONDITION-SEARCH.md` | Modified | 记录 API 补测、请求边界修复及其运行时复验缺口 | IHR Standard §4 | IHR-010 |
| `services/facade.py` | Modified | 对所有未发布/未知 dimension 失败关闭，不再静默忽略无点号的直接字段名 | CC-015 §§8、12；CC15-TEST-040 | IHR-011 |
| `tests/test_service_core.py` | Modified | 覆盖未发布直接 dimension 的拒绝行为 | CC-015 §17；CC15-TEST-040 | IHR-011 |
| `docs/context/history/ATR-GS-MULTI-CONDITION-SEARCH.md` | Modified | 记录 TEST-021/024/025/033/037 PASS、TEST-038/040 FAIL 及重载前置条件 | ATR Standard v1.0.0 | IHR-011 |
| `docs/context/history/IHR-GS-MULTI-CONDITION-SEARCH.md` | Modified | 记录 Selector/API 补测、TEST-040 本地修复和 State Refinement 未决语义 | IHR Standard §4 | IHR-011 |
| `docs/context/history/ATR-GS-MULTI-CONDITION-SEARCH.md` | Modified | 追加授权重载后的 TEST-040 运行时通过证据，更新状态统计与遗留项 | ATR Standard v1.0.0 | IHR-012 |
| `docs/context/history/IHR-GS-MULTI-CONDITION-SEARCH.md` | Modified | 记录 TEST-040 目标端复验通过及 TEST-038 后续边界 | IHR Standard §4 | IHR-012 |
| `docs/context/history/ATR-GS-MULTI-CONDITION-SEARCH.md` | Modified | 记录 Published State Mapping 核验、TEST-038 失败和待澄清的多 Resource 状态行为 | ATR Standard v1.0.0 | IHR-013 |
| `docs/context/history/IHR-GS-MULTI-CONDITION-SEARCH.md` | Modified | 记录 State Refinement 边界核验及需用户决定的实现语义 | IHR Standard §4 | IHR-013 |
| `services/facade.py` | Modified | 公开可读 Published business-state 标签、计算所选 Resource 的共同状态并校验请求状态 | CC-015 §§8、11；CC15-TEST-038 | IHR-014 |
| `services/conditions.py`、`services/executor.py` | Modified | State Refinement 使用等值运算；按 Published `business_state → technical_values[]` 构造状态域并校验 state 字段可读 | CC-005 §§2–3；TDD §4.5；CC-015 §§9、12 | IHR-014 |
| `controllers/main.py`、`static/src/js/preview.js` | Modified | Resource tabs 提供已发布状态描述；Workspace 仅展示所选 Resource 的共同 business-state，空交集时禁用 | CC15-TEST-038；用户确认的交互规则 | IHR-014 |
| `tests/test_service_core.py` | Modified | 覆盖 Published 状态技术域映射、可读状态描述、共同状态接受/拒绝 | CC-015 §17；CC15-TEST-038 | IHR-014 |
| `docs/context/history/ATR-GS-MULTI-CONDITION-SEARCH.md` | Modified | 记录 TEST-038 运行时通过、回归证据及更新后的矩阵统计 | ATR Standard v1.0.0 | IHR-014 |
| `docs/context/history/IHR-GS-MULTI-CONDITION-SEARCH.md` | Modified | 记录 State Refinement 实施与运行时验证 | IHR Standard §4 | IHR-014 |
| `tests/test_service_core.py` | Modified | 增加 fake-model executor/parser isolation 支持性测试；尚不替代 CC15-TEST-008/032 的受控 ORM fixture | CC-015 §§4.5、17 | IHR-015 |
| `docs/context/history/ATR-GS-MULTI-CONDITION-SEARCH.md` | Modified | 记录剩余矩阵补测启动及未关闭契约测试的证据边界 | ATR Standard v1.0.0 | IHR-015 |
| `docs/context/history/IHR-GS-MULTI-CONDITION-SEARCH.md` | Modified | 记录补测启动、支持性单测和浏览器路由的限制 | IHR Standard §4 | IHR-015 |
| `docs/context/history/ATR-GS-MULTI-CONDITION-SEARCH.md` | Modified | 记录 TEST-020 Workspace Form Action 导航通过并更新矩阵统计 | ATR Standard v1.0.0 | IHR-016 |
| `docs/context/history/IHR-GS-MULTI-CONDITION-SEARCH.md` | Modified | 记录 TEST-020 导航证据和剩余测试状态 | IHR Standard §4 | IHR-016 |
| `docs/context/history/ATR-GS-MULTI-CONDITION-SEARCH.md` | Modified | 记录 TEST-026 唯一 token Search API 日志检查通过并更新矩阵统计 | ATR Standard v1.0.0 | IHR-017 |
| `docs/context/history/IHR-GS-MULTI-CONDITION-SEARCH.md` | Modified | 记录 TEST-026 运行时日志证据、限制及当前矩阵状态 | IHR Standard §4 | IHR-017 |
| `services/request_boundary.py` | Modified | 验证 CQO combinator、条件类型、必需 dimension/value、标量值和嵌套边界 | CC-015 §§4、17 | IHR-018 |
| `tests/test_request_boundary.py` | Modified | 增加 CQO 合法/非法对象、缺字段、错误值、combinator 与深度用例 | CC15-TEST-006 | IHR-018 |
| `docs/context/history/ATR-GS-MULTI-CONDITION-SEARCH.md` | Modified | 记录 TEST-006 的 CQO 边界测试通过并更新矩阵统计 | ATR Standard v1.0.0 | IHR-018 |
| `docs/context/history/IHR-GS-MULTI-CONDITION-SEARCH.md` | Modified | 记录 CQO 边界实现、回归和限制 | IHR Standard §4 | IHR-018 |
| `docs/context/history/ATR-GS-MULTI-CONDITION-SEARCH.md` | Modified | 按用户要求将 TEST-041 从 BLOCKED 更新为 SKIPPED，保留性能未验证说明 | ATR Standard v1.0.0 | IHR-019 |
| `docs/context/history/IHR-GS-MULTI-CONDITION-SEARCH.md` | Modified | 记录并发测试范围决定和更新后的矩阵统计 | IHR Standard §4 | IHR-019 |
| `tests/test_cc015_contract.py`、`tests/__init__.py` | Modified | 注册并实现 14 个真实 ORM/权限 TransactionCase，逐项覆盖此前 NOT RUN 的 CC15-TEST IDs | CC-015 §17 | IHR-020 |
| `docs/context/history/ATR-GS-MULTI-CONDITION-SEARCH.md` | Modified | 追加 RUN-028，14 项均记为 PASS；更新 43 项状态及遗留问题 | ATR Standard v1.0.0 | IHR-020 |
| `docs/context/history/IHR-GS-MULTI-CONDITION-SEARCH.md` | Modified | 记录测试 runner 范围修正、77 项通过结果与回滚边界 | IHR Standard §4 | IHR-020 |
| `controllers/main.py` | Modified | 将日期预设、起止日期和状态控件放入默认收起的原生 disclosure group，并递增 CSS 缓存版本 | CC-005 Refinement；用户交互要求 | IHR-021 |
| `static/src/css/preview.css` | Modified | 添加折叠组、控件区、活动筛选标签与窄屏布局样式 | CC-005 Refinement；用户交互要求 | IHR-021 |
| `docs/context/history/IHR-GS-MULTI-CONDITION-SEARCH.md` | Modified | 记录 Refinement 折叠组实现及尚未完成的 live UI 验证 | IHR Standard §4 | IHR-021 |
| `docs/context/intent/CC-015_multi_condition_search.md` | Modified | v0.5 正式豁免本轮 CC15-TEST-041 执行；保留 SKIPPED 与无性能符合性声明 | User-approved amendment / CC15-DEC-027 | IHR-023 |
| Odoo 8091 Workspace | Verified | 重载后确认日期/状态组初始收起、点击展开、Enter 收起 | CC-005 Refinement | IHR-022 |
| `mymodules/wd_global_search/tests/test_configuration.py` | Verified | 映射 publish audit-event 唯一性断言至 RUN-028 77/77 模块套件 | CC-008 / CC-015 §18 | IHR-024 |
| 8091 Search API | Verified | 对照基线及伪造客户端 lang/tz/locale/timezone 后结果和日期 Refinement 一致 | CC-009 regression scope | IHR-025 |
| `docs/context/history/FR-GS-MULTI-CONDITION-SEARCH.md` | Added | 基于 CC-015 v0.5 及当前有效 IHR/ATR/HVR 证据形成 Closure Assessment | FR Template v1.0.0 | IHR-026 |
| Implementation baseline | Committed | 被验证工作区代码原样提交为 `0e43bff`；后续收口变更限于文档 | CC-015 §20 | IHR-026 |

## 6. 偏离与停止条件记录（Deviation / Stop Condition Record）

- **Deviation：** None。
- **Stop Conditions：** None triggered. The 14 previously unrun CC15 contract cases passed in RUN-028; audit-event regression is covered by RUN-028 and IHR-024. TEST-041 is waived for this iteration by CC15-DEC-027; no performance baseline is claimed. FR v0.1 records the closure assessment.
- 后续若 Published version/checksum 与 CC-015 §2.3 不符，或实现要求改变冻结范围，必须停止并追加记录；不得以 IHR 替代契约修订与批准。

## 7. 遗留问题与后续（Open Issues / Follow-up）

Open Issues: No blocking issue remains for CC-015 closure. CC15-TEST-041 is SKIPPED under user-approved CC15-DEC-027; no performance baseline or performance-compliance claim exists, and independent performance acceptance remains future work. The 14 formerly NOT RUN CC15 IDs passed via IHR-020 / ATR-RUN-028; audit-event regression is covered by RUN-028 / IHR-024; the IHR-021 disclosure group passed live UI verification in IHR-022; CC-009 regression scope passed in RUN-030 without claiming full CC-009 acceptance. TEST-006/ATR-RUN-026, TEST-020/ATR-RUN-024, TEST-026/ATR-RUN-025, TEST-034/ATR-ISSUE-007, TEST-040/ATR-ISSUE-008, and TEST-038/ATR-ISSUE-009 were resolved by tests or authorized 8091 runtime verification. A same-user 20-request attempt hit the per-user limiter and did not produce a valid performance baseline; the user-approved amendment accepts that gap for this contract only. The Odoo module suite passed 77/77 in IHR-020 / ATR RUN-028; human HVR passed per IHR-007 / ATR-RUN-013 and was reaffirmed in this session.

实现中发现的配置、兼容性、安全或上游设计问题应按本节新增条目，并在解决后将状态更新为 Resolved；不得删除历史问题记录。

## 8. 移交摘要（Handoff）

```text
Implemented：核心多词搜索调用链已接入；日期/状态筛选已加入默认收起组并经 8091 live UI 验证（IHR-021/022）；Odoo 模块套件 77 PASS（含 14 项 CC15 TransactionCase，包含 audit-event 唯一性断言）；CC-009 相关服务端上下文/日期回归由 RUN-030 验证；此前 14 项 NOT RUN 已全部关闭；TEST-041 按 CC-015 v0.5 / DEC-027 豁免且无性能通过声明；测试代码基线已提交为 `0e43bff`；FR v0.1 评估为 SATISFIED
Actual Files：见 §5
Open Issues：无阻塞 CC-015 收口的事项；TEST-041 依 CC-015 v0.5 / DEC-027 豁免且没有性能基线，后续独立性能验收另行安排；此前未完成的 CC15-TEST 已由测试或对应运行时证据关闭；audit-event 回归由 RUN-028 覆盖；CC-009 回归范围由 RUN-030 覆盖但不代表完整 CC-009 验收；人工 HVR 已确认
Deviation：None
Stop Conditions Triggered：None
ATR：见 [ATR-GS-MULTI-CONDITION-SEARCH.md](./ATR-GS-MULTI-CONDITION-SEARCH.md)；状态 PARTIAL，HVR 已通过。FR：见 [FR-GS-MULTI-CONDITION-SEARCH.md](./FR-GS-MULTI-CONDITION-SEARCH.md)，Closure Status SATISFIED；不构成 Merge/Release 批准。
```

IHR 仅记录实施事实；测试通过、人工验收及 CC Closure 由 ATR、HVR、FR 分别处理。
