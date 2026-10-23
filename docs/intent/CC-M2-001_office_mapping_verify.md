<!-- Skill bundle metadata
Source template: docs/skill/odoo-project-workflow/references/templates/Coding/Coding_Contract模板.md
Source version/status: v1.0.0; Frozen
Template synchronization check: PASS, 2026-10-22
-->

# CC-M2-001：纯 Python 映射校验器底座

## 0. 文档治理

### 0.1 执行元数据

| 字段 | 值 |
|---|---|
| Intent ID | `OFFICE-ENGINE-M2-001` |
| Coding Contract | `CC-M2-001` |
| 模块 | `office_mapping_verify` |
| 工作类型 | 新功能 / 独立 Python 包 |
| 变更类型 | 新增纯 Python 映射解析与校验底座 |
| 版本 | V1.0.0 |
| 状态 | FROZEN V1.0.0 |
| 目标 | 在 `mymodules/office_mapping_verify/` 实现无 Odoo、无网络、无数据库依赖的严格 Proposal 解析、字段/目标校验及必填完整性拦截。 |
| 背景 | TV-M2-001 中模型 4 次都返回可解析 JSON，但仅映射 5/20 个目标；修复提示后仍漏 15 项。系统必须由确定性后端校验拒绝不完整映射，不能让部分结果进入确认或渲染。 |
| TDD 基线 | `TDD-OFFICE-ENGINE-M2` V1.0.0 FROZEN |
| Implementation Plan 基线 | `IMPLEMENTATION_PLAN_office_engine_m2` V1.0.0 FROZEN，Phase 1 / CC-M2-001 |
| SRS 基线 | `SRS_office_engine_m2_ai_mapping` V1.0.0 FROZEN |
| DDD | N/A；依据见 TDD V1.0.0 |
| TV 基线 | M2 TV Report V1.1 FROZEN；TV-M2-001 维持 `FAIL`，作为本 CC 的回归输入 |
| 起草日期 | 2026-10-22 |
| 批准 / 冻结记录 | 负责人于 2026-10-23 批准实施，并批准本附录 B 四项裁定；状态更新为 FROZEN V1.0.0。 |

### 0.2 首 CC Gate 记录

负责人于 2026-10-22 批准冻结 M2 Implementation Plan V1.0.0，并明确授权解除首个 CC Gate、起草本 CC。计划 §13 的 OIP-M2-001/002 已按审批记录处置；OIP-M2-003/004/005 对本纯 Python CC 标记为 N/A。负责人随后于 2026-10-23 单独批准本 CC 冻结并实施；授权和裁定见本文件元数据及附录 B。

TV-M2-001 的原始状态仍是 `FAIL`，不改写为 PASS，也不豁免本 CC 的缺项拒绝测试。TV-M2-004 仍为 `INCONCLUSIVE`；本 CC 不证明 Provider 或 Prompt Injection 的产品级安全性。

### 0.3 文档目的与冻结规则

本 CC 冻结本次包内实现、文件范围、测试和完成门槛。它不得修改或重新解释 SRS、TDD 或实施计划。负责人于 2026-10-23 批准实施；本文件的冻结状态构成本 CC 的编码授权。冻结前测试状态为 `NOT RUN`。

## 1. 变更概述

### 1.1 目标

在 `mymodules/office_mapping_verify/` 建立独立 Python 包，提供严格 JSON Proposal 解析、Schema/字段/目标白名单校验、目标完整性检查和映射编辑后的重新校验。对 TV-M2-001 的 20 个服务端必填目标，仅收到 5 个映射时，必须准确报告其余 15 项缺失并阻止该 Proposal 进入可确认状态。

### 1.2 本 CC 的依据

- TV-M2-001：真实模型响应 4/4 可解析，但每次只覆盖 5/20 个目标，15 项遗漏；补救提示仍未补齐。原结果见 `docs/verification/TV_office_engine_m2_report.md` §4、§11.1 及其证据目录。
- M2 TDD V1.0.0：§§3–5、§13、§17–19，尤其是 `office_mapping_verify`、Proposal/TargetManifest、严格解析、必填完整性、手工修订复验和无 Odoo 依赖约束。
- M2 SRS V1.0.0：FR-M2-004、FR-M2-005、FR-M2-007；BR-M2-001、BR-M2-003、BR-M2-004；AC-05、AC-06、AC-08；NFR-M2-003。

## 2. 上游基线与追溯

### 2.1 SRS 引用

| SRS ID | 标题 | 与本 CC 的相关性 |
|---|---|---|
| FR-M2-004 | 生成受约束的结构化映射建议 | 校验合法 JSON 的提案，不将自然语言或未知内容当作可执行映射。 |
| FR-M2-005 | 歧义、缺失与冲突澄清 | 产生稳定的缺项/澄清结果；缺少必填目标时不能就绪。 |
| FR-M2-007 | 用户修改映射 | 编辑后的候选须再次经过同一确定性校验；本 CC 不实现 UI/RPC。 |
| BR-M2-001 / 003 | 字段来源与服务端校验 | 仅接受调用方传入的授权字段和服务器目标集合，不推断权限。 |
| BR-M2-004 | 映射问题未解决前不得生成 | 必填目标缺失、澄清未闭合或跳过未获准时，不得标为可确认。 |
| AC-05 / 06 / 08 | 非法映射拒绝、缺项澄清、非法用户编辑拒绝 | 对应纯函数的正向与负向单元测试。 |
| NFR-M2-003 | 结果可信 | 未知、非法或不完整提案不得静默修补或部分执行。 |

### 2.2 DDD 引用

N/A。负责人已在 TDD V1.0.0 中批准 DDD 不适用，本包不引入领域聚合或 Odoo 模型。

### 2.3 TDD 引用

| TDD ID / 章节 | 标题 | 本 CC 落实范围 |
|---|---|---|
| §§3.2、4.2–4.4 | Proposal schema、TargetManifest、纯 Python 校验器 | 解析/校验数据契约；只处理普通 Python 数据，不依赖 Odoo recordset。 |
| T-M2-SEC-003 | Proposal、前端字段与模板指令均不可信 | 拒绝额外键、未知字段/目标/操作和值类型；不执行任何指令或表达式。 |
| T-M2-MAP-001 | Proposal 与 M1 Mapping Plan 分离 | 本包不生成 M1 Mapping Plan、不提供文件写入操作。 |
| T-M2-MAP-002 | 必填范围来自服务器/用户确认清单 | 只按调用方传入的 TargetManifest 检查完整性；模型不能设置 required/optional/approved_to_skip。 |
| TDD §13.1 | 严格解析、allowlist、completeness 和手工编辑测试 | 本 CC 对包内纯 Python 行为执行 pytest。 |

### 2.4 TV / 事件证据

| 项 | 状态 | 证据与处置 |
|---|---|---|
| TV-M2-001 JSON 语法子项 | PASS（仅语法） | 4/4 响应可由严格 JSON parser 解析；不等于 Mapping 完整。 |
| TV-M2-001 Mapping 完整性 | FAIL | 每次响应 5/20，缺少 15 个服务端必填目标；修复响应仍缺项。本 CC 必须用确定性夹具复现并拒绝。 |
| TV-M2-004 Prompt Injection | INCONCLUSIVE | 不在本纯 Python CC 中宣称注入防御通过；由服务端授权/白名单和后续 CC 验证。 |

## 3. 范围冻结

### 3.1 范围内

- 在 `mymodules/office_mapping_verify/` 新建独立纯 Python 包。
- 提供 TDD 定义的 Proposal、TargetManifest、允许字段和稳定校验报告数据结构。
- 实现严格 JSON 解析：仅接受合法 JSON 对象；拒绝围栏、前后自然语言、重复 JSON key、错误根类型、超出显式输入限制的内容。
- 实现 Proposal Schema、精确键集合、字段/目标 allowlist、唯一目标、可写性、类型兼容及 required-target 完整性校验。
- 对调用方提交的人工修订执行相同的目标/字段/类型/完整性复验；不得信任修订来源。
- 生成确定性、可序列化、无 Odoo 依赖的校验结果和稳定错误类别。
- 为 TV-M2-001 的 5/20 失败样例建立纯 Python 回归夹具，精确断言 15 项缺失且不就绪。
- 以 pytest 执行测试；以分支覆盖率工具证明包自有生产代码 100% 语句及分支覆盖。
- 自动静态扫描包内所有 `.py` 文件，拒绝 Odoo/ORM、文件引擎、LLM SDK、HTTP、网络和数据库依赖导入。

### 3.2 范围外

- Odoo Addon、ORM、控制器、ACL、Record Rules、业务数据查询和 `odoo_record_retriever` 调用。
- OpenAI SDK、Prompt、Provider Usage、重试编排、网络/数据库访问。
- Owl 组件、聊天卡片、RPC、附件读写或 M1 渲染调用。
- 由模型或该包决定用户权限、安全字段基线、TargetManifest 必填性或 `approved_to_skip`。
- 生成 M1 Mapping Plan、写入 Office 文件、计算/修改公式或提供文件处理功能。
- 安装/升级 Odoo 模块、访问 `odoo18ce`、创建隔离数据库或更改 Odoo 服务。

### 3.3 非目标

- 本 CC 不证明 `gpt-5.6-luna` 能完整映射 20 个目标，也不提高模型输出成功率。
- 本 CC 不将 TV-M2-001 重新评为 PASS；它实现并验证后端在发现遗漏时拒绝继续。
- 本 CC 不单独证明 Prompt Injection 抵御、业务字段安全或生产性能。

### 3.4 范围内上游 ID

本 CC 纳入 SRS：FR-M2-004、FR-M2-005、FR-M2-007、BR-M2-001、BR-M2-003、BR-M2-004、AC-05、AC-06、AC-08、NFR-M2-003；TDD：T-M2-SEC-003、T-M2-MAP-001、T-M2-MAP-002 及 §13.1 的纯 Python 校验义务。以上每项均须在 §5 映射到 CC-CHANGE。

## 4. 变更边界

### 4.1 允许修改

本 CC 的所有实现文件、测试文件和包内测试配置必须且只能位于 `mymodules/office_mapping_verify/` 目录。

| 类型 | 允许路径 / 内容 |
|---|---|
| 新增包文件 | `mymodules/office_mapping_verify/__init__.py`、`contracts.py`、`parser.py`、`validator.py` |
| 新增测试 | `mymodules/office_mapping_verify/tests/**`；pytest 单元测试与静态依赖导入测试 |
| 包内测试配置 | 仅当确有必要，新增该目录内的 pytest / coverage 配置文件 |
| 包内测试依赖说明 | 新增 `requirements-test.txt`，只锁定 pytest 与覆盖率测试工具，不含运行时依赖；实施时允许将这些测试依赖安装到项目 `venv`，不修改生产依赖 |

文件列表是拟议最小边界。新增目录外文件、修改现有目录、依赖配置或运行时文件前必须停止并修订 CC。

### 4.2 禁止修改

| 类型 | 禁止范围 |
|---|---|
| Odoo / ORM | 禁止导入或修改 `odoo`、`odoo.addons`、模型、控制器、RPC、数据库或配置。 |
| 其他 Office 包 | 禁止导入或修改 `office_core`、`office_verify`；不共享其私有实现。 |
| Provider / 网络 | 禁止导入或修改 `openai`、其他 LLM SDK、`requests`、`httpx`、`urllib`、socket 或任何网络客户端。 |
| 计划外文件 | 禁止修改包目录外的项目文件、`mymodules/odoo-llm/` 或 Odoo 源码；本 CC 已授权的测试工具仅可按 `requirements-test.txt` 安装到项目 `venv`，不得加入生产依赖。 |
| 产品功能 | 禁止实现 UI/RPC、数据查询、重试、M1 渲染、附件交付或 Skill。 |
| 依赖安装 | 只允许按包内 `requirements-test.txt` 安装已锁定的测试工具到项目 `venv`；不得新增生产运行时依赖或安装其他包。 |

## 5. 必需的行为变更

| ID | 当前行为 / 缺口 | 期望行为 | CC-CHANGE ID |
|---|---|---|---|
| 1 | 目前没有独立 Proposal parser；直接使用不受限文本会允许格式歧义进入后续层。 | `parse_mapping_proposal(raw_text, limits)` 只返回符合精确 schema 的 Proposal 或稳定解析错误；拒绝重复键、额外内容、未知根结构及超限输入。 | CC-CHANGE-001 |
| 2 | 合法 JSON 不代表字段/目标可信；模型可遗漏必填项或虚构映射。 | `validate_proposal(proposal, target_manifest, allowed_fields)` 检查精确 schema、所有目标/字段成员资格、目标可写性、类型兼容、重复和必填完整性；不产生权限结论。 | CC-CHANGE-002 |
| 3 | 当前没有对 TV-M2-001 的 5/20 漏项作确定性阻断的代码。 | 在 20 个 required targets 中仅有 5 个 mapping 时，报告恰好 15 个 `missing_required`，结果为不完整且 `ready_for_review=False`；不得以部分命中就绪。 | CC-CHANGE-003 |
| 4 | 用户修订可能绕过模型提案校验或保留旧的校验通过状态。 | 对人工修订重新校验；输入有任何不合法项时返回稳定失败，旧结果不继承为当前修订通过。 | CC-CHANGE-004 |
| 5 | 纯 Python 依赖边界没有自动门禁。 | 测试静态扫描生产包及测试包，不允许 Odoo/ORM、Office 引擎、Provider、HTTP/网络或数据库模块导入。 | CC-CHANGE-005 |

## 6. 既有行为保留

| ID | 行为 / 契约 | 为什么不得改变 | CC-PRESERVE ID |
|---|---|---|---|
| 1 | M2 Proposal 与 M1 Mapping Plan 保持不同结构；Proposal 不含 M1 `writes` / 文件写入内容。 | T-M2-MAP-001；模型输出不得直接执行。 | CC-PRESERVE-001 |
| 2 | `schema_version`、`mappings`、`clarifications`、`skipped_targets` 是 Proposal 根对象允许且仅允许的键。 | TDD §4.2 的严格 schema。 | CC-PRESERVE-002 |
| 3 | `element_id`、`source_field`、`value_type` 必须来自调用方提供的服务端上下文；模型不能创建/改写 required、optional 或 approved-to-skip。 | T-M2-SEC-003 / T-M2-MAP-002。 | CC-PRESERVE-003 |
| 4 | 数据表示区分字段缺失、显式 JSON null、空字符串和数值 0；不得通过隐式转换绕过验证。 | TDD §4.2 与 M1 值契约。 | CC-PRESERVE-004 |
| 5 | 包不查询权限，不将 `allowed_fields` 成员资格误称为 Odoo ACL / Record Rule 验证。 | 授权判定属于 Odoo 编排层，不属于纯 Python 包。 | CC-PRESERVE-005 |

## 7. 适用的 TDD 防护栏

| TDD 防护栏 | 适用性 | 本次落实位置 | 验证方式 |
|---|---|---|---|
| T-M2-SEC-003 | 适用 | 严格 schema、目标/字段/操作/type 校验；所有外部数据视为不可信 | CC-TEST-001–006 |
| T-M2-MAP-001 | 适用 | 包只产生 Proposal 校验结果，不输出 M1 Mapping Plan | CC-TEST-003、006 |
| T-M2-MAP-002 | 适用 | required/approved-to-skip 只由输入 TargetManifest 决定；缺失 required 返回 incomplete | CC-TEST-004、005 |
| TDD §13.1-1/2/3 | 适用 | strict parse、schema/allowlist、完整性负向与正向路径 | CC-TEST-001–006 |
| TDD §4.4 / §13.1-5 依赖隔离 | 适用 | 静态导入分析和纯 Python pytest | CC-TEST-007、008 |

## 8. 数据 / 迁移影响

| 字段 | 值 |
|---|---|
| 需要迁移 | 否 |
| 迁移脚本 | N/A；本 CC 不创建 Odoo 模型或数据库结构 |
| 数据源 | 单元测试中的合成 JSON、TargetManifest 和允许字段集合 |
| 目标 | 纯 Python 校验报告对象；不持久化任何数据 |
| 恢复 / 回滚策略 | 删除本 CC 目录内新增包/测试即可回退；不触碰数据库或 filestore |
| 验证 | pytest 执行、100% statement/branch coverage 报告、静态导入扫描 |

## 9. API / 集成影响

| 字段 | 值 |
|---|---|
| 修改的端点 | 无 |
| 向后兼容 | 新增独立包 API；不修改现有接口 |
| Adapter 变更 | 无；后续 Odoo 编排层调用本包由后续 CC 实施 |
| 预计接口 | `parse_mapping_proposal(raw_text, limits)`；`validate_proposal(proposal, target_manifest, allowed_fields)`；`validate_user_revision(revision, edits, target_manifest, allowed_fields)`；兼容别名 `apply_manual_edits(...)` |
| API 兼容条件 | 按附录 B 保留 TDD §3.2 与 §4.4 的两个方法名并映射到同一实现；参数/结果不得改变 TDD 校验语义 |

## 10. 安全 / 权限影响

| 字段 | 值 |
|---|---|
| 新权限 | 无；此包不持有用户身份或 Odoo 权限 |
| 变更的 ACL | 无 |
| 敏感数据暴露检查 | 单元测试只使用合成内容；错误结果不得包含输入全文或未授权字段值 |
| 不可信输入 | 严格拒绝未知键、未知字段、未知目标、错误类型、重复映射、注入式字符串作为字段/操作/目标标识 |
| 导入约束 | 包内运行代码和测试不得导入 Odoo/ORM、`office_core`、`office_verify`、LLM SDK、HTTP/网络、数据库模块；不使用动态 import 绕过静态检查 |
| 数据处理 | 不联网、不记录原始 Prompt/Completion，不读写本地文件；测试代码可读取本 CC 包内静态 fixture，不得读取用户业务文件 |

## 11. 测试契约

所有测试均为独立 pytest 单元测试，禁止初始化 Odoo registry、连接数据库、调用网络或真实 Provider。测试输入由包内 fixture 即时构造或读取包内合成 fixture。

| 测试 ID | 对应变更 | 上游来源 | 测试类型 | 预期结果 | 人工验证 | 原因 |
|---|---|---|---|---|---|---|
| CC-TEST-001 | 合法 Proposal 解析 | FR-M2-004、TDD §4.2 | pytest 单元 | 精确合法对象被解析为 Proposal；根键、字段类型、数组结构与 schema version 符合契约；解析不修改输入语义。 | N/A | 验证正向 parser 路径。 |
| CC-TEST-002 | 非法 JSON 拒绝 | FR-M2-004、TDD §4.4 | pytest 单元 | 对非法/截断 JSON、Markdown fence、前后自然语言、重复键、NaN/Infinity 等非标准常量、深层嵌套、非 object 根、额外根键、错误 schema version、数组/文本/字节超限逐例返回明确解析失败；不抛未捕获异常。 | N/A | 防止格式容错把不可信响应误判为有效。 |
| CC-TEST-003 | 字段/目标/类型和精确 schema 拒绝 | BR-M2-001/003、AC-05、T-M2-SEC-003 | pytest 单元 | 对未知 `element_id`、未知 `source_field`、不可写目标、错误类型、重复目标、额外 Proposal/mapping 键、模型伪造 `required`/`approved_to_skip`、出现 `value`/`data`/`sample`、非法 operation 分别拒绝；允许的字段和目标不因失败被自动扩展。 | N/A | 证明模型输出只作为不可信提案。 |
| CC-TEST-004 | completeness 完整通过及澄清/跳过边界 | FR-M2-005、BR-M2-004、T-M2-MAP-002 | pytest 单元 | 所有服务端 required target 已映射且无未闭合澄清时才可进入 review；required target 缺失、澄清未解决、required 被跳过或 skip 未获批准时均 `incomplete` 且 `ready_for_review=False`；已批准的 optional skip 只对对应 manifest 项生效。 | N/A | 完整性权威必须来自 TargetManifest，而不是模型。 |
| CC-TEST-005 | TV-M2-001 5/20 漏填复现 | TV-M2-001 `FAIL`、AC-05/06、T-M2-MAP-002 | pytest 单元回归 | 构造与 TV evidence 一致的 20 个 required targets 和只含 5 个 mapping 的 Proposal；断言 `missing_required` 恰为其余 15 个 target ID、无重复/误报，校验结果不完整、`ready_for_review=False`；任何部分 mapping 都不得返回全量完整/可确认结果。不得调用模型、网络或 Odoo。 | N/A | 直接关闭本 CC 的核心业务缺口，同时保留 TV 原 FAIL 历史。 |
| CC-TEST-006 | 人工编辑及显式值边界 | FR-M2-007、AC-08、TDD §3.2/§4.4 | pytest 单元 | 每次编辑重新验证 target/field/type/required；非法编辑不会继承旧 PASS。缺键、显式 `null`、空字符串和数值 `0` 分别测试：Proposal 不接受 `value/data/sample`，不得隐式合并或转换；标识字段缺失/null/空值/非字符串均拒绝。最多 200 个 edits，超限拒绝。 | N/A | Proposal 不承载业务值，编辑路径不得绕过结构校验。 |
| CC-TEST-007 | 纯 Python 导入隔离 | TDD §4.4、T-M2-SEC-003 | pytest 静态 AST 检查 | 遍历包内所有 `.py` 文件，任何 `import` / `from` 导入 `odoo`、ORM、`office_core`、`office_verify`、OpenAI/LLM SDK、HTTP/网络或数据库模块时失败；禁止动态 import 规避。 | N/A | 以自动检查证明包不依赖 Odoo 或外部服务。 |
| CC-TEST-008 | pytest 和覆盖率总门槛 | Implementation Plan Phase 1 | pytest + branch coverage | `pytest` 测试全部通过；所有包自有生产代码达到 **100% 语句覆盖率和 100% 分支覆盖率**，不允许排除生产文件/分支或用整体均值掩盖文件未覆盖。报告须列出每个生产文件的语句/分支数字。 | N/A | 本 CC 的强制质量门槛。 |

### 11.1 测试环境与执行命令

- 运行环境：项目 Python `venv`，Python 3.11.9；不得使用 Odoo shell、`.venv`、系统 Python、真实数据库或网络。
- 基础测试：`venv/bin/python -m pytest -q mymodules/office_mapping_verify/tests`。
- 覆盖率：使用 `pytest-cov` branch measurement，命令为 `venv/bin/python -m pytest -q --cov=mymodules.office_mapping_verify --cov-branch --cov-report=term-missing --cov-fail-under=100 mymodules/office_mapping_verify/tests`；输出必须显示 100% statements 和 100% branches。
- 测试依赖锁定：`pytest==8.4.2`、`pytest-cov==7.1.0`、`coverage==7.16.2`，记录于包内 `requirements-test.txt`。负责人本轮授权安装这些测试依赖到项目 `venv`；生产依赖不变。
- CC 冻结时所有 CC-TEST 状态均为 `NOT RUN`；实施后由 ATR 记录实际命令、退出码、覆盖率报告和代码 commit。

## 12. 停止条件 / 升级闸门

| 触发条件 | 升级路径 |
|---|---|
| `office_mapping_verify` 的唯一允许目录需要扩展 | 停止，修订 CC 并重新审批；涉及 TDD 架构时先修订 TDD。 |
| 测试需要 Odoo、ORM、网络、数据库或 Provider | 停止；回 TDD/计划确认边界，不允许将依赖偷偷加入本包。 |
| 发现 TDD/M1 的 Proposal 或 value type 契约不足以判定合法性 | 停止受影响实现，提交 TDD 变更；不得在 CC 里猜测新增业务类型。 |
| TDD 人工编辑入口名称不一致 | 按附录 B 裁定：`validate_user_revision` 为规范入口，`apply_manual_edits` 为兼容别名；两者复用同一实现。 |
| JSON 最大字节数/集合数量限制 | 按附录 B 裁定：65,536 字节 / 200 mappings / 100 clarifications / 200 skipped targets，并覆盖边界测试。 |
| 覆盖率工具缺失 | 按附录 B 锁定 pytest-cov / Coverage.py 版本并授权安装测试依赖；仍未能达到 100% 时该门禁 FAIL。 |
| 类型兼容表不完整 | 按附录 B 只接受归一化 `string`、`number`、`boolean` 的字段与目标交集；不执行转换。 |
| 5/20 回归不能准确报告 15 个缺项、或校验器给部分映射 `ready_for_review=True` | 视为核心失败；停止后续阶段，修复本 CC 并重新执行 ATR。 |
| 需要修改 SRS/TDD 语义或把 TV 结果改成 PASS | 停止，交回对应权威文档流程；不得在实现或证据中静默改写。 |

## 13. 完成定义 / 关闭标准

| 标准 | 闸门类型 |
|---|---|
| 所有范围内实现均位于 `mymodules/office_mapping_verify/`，无其他文件变更 | 硬闸门 |
| `office_mapping_verify` 可独立 import 和 pytest 执行，不需要 Odoo、数据库、网络、LLM 或 M1 包 | 硬闸门 |
| CC-TEST-001 至 CC-TEST-008 全部通过；CC-TEST-005 精确证实 5/20 输入产生 15 项 missing required 并 fail closed | 硬闸门 |
| 100% statement + 100% branch coverage 证据绑定当前 commit，无排除项 | 硬闸门 |
| 静态导入扫描通过，覆盖生产代码与测试文件 | 硬闸门 |
| 不存在未登记的偏移；TDD API 命名/测试工具待决项在冻结前已完成处置 | 硬闸门 |
| IHR、ATR、FR 按项目模板记录并完成评审；HVR 明确标为 N/A（纯 Python，无用户界面） | 硬闸门 |

冻结时 CC-TEST-001–008 均为 `NOT RUN`；实施执行状态与实际结果以关联 IHR / ATR 为准。

## 14. 追溯矩阵

### 14.1 正向：纳入范围的上游需求 → CC

| 上游 ID | CC-CHANGE ID | 备注 |
|---|---|---|
| FR-M2-004 / AC-05 | CC-CHANGE-001、002 | 严格解析并拒绝非法/未知映射。 |
| FR-M2-005 / AC-06 / BR-M2-004 | CC-CHANGE-002、003 | 完整性报告与缺项澄清结果。 |
| FR-M2-007 / AC-08 | CC-CHANGE-004 | 用户修订须复用确定性校验。 |
| BR-M2-001/003 / T-M2-SEC-003 | CC-CHANGE-002、005 | allowlist 校验与依赖隔离。 |
| T-M2-MAP-001 | CC-CHANGE-001、002 | Proposal 与 M1 Plan 分离。 |
| T-M2-MAP-002 | CC-CHANGE-002、003 | required/skip 权威来自 TargetManifest。 |
| TV-M2-001 `FAIL` | CC-CHANGE-003 | 5/20 → 15 missing 的确定性回归。 |

### 14.2 反向：CC → 上游

| CC ID | 上游 ID | 类型 |
|---|---|---|
| CC-CHANGE-001 | FR-M2-004、T-M2-SEC-003 | SRS / TDD |
| CC-CHANGE-002 | FR-M2-004/005、BR-M2-001/003、T-M2-MAP-001/002 | SRS / TDD |
| CC-CHANGE-003 | FR-M2-005、BR-M2-004、TV-M2-001 | SRS / TV |
| CC-CHANGE-004 | FR-M2-007、AC-08 | SRS |
| CC-CHANGE-005 | T-M2-SEC-003、TDD §4.4 | TDD |

### 14.3 DDD

N/A。仅执行 SRS → TDD → CC → pytest/ATR 追溯链。

## 附录 A：实现决策

| CC-DEC ID | 决策 | 考虑的替代方案 | 理由 |
|---|---|---|---|
| CC-DEC-001 | 生产包只接受普通数据结构；职责限定为解析/校验，不访问权限或业务数据。 | 在包内查询 Odoo 或处理附件。 | TDD 明确要求纯 Python 隔离；权限由上层负责。 |
| CC-DEC-002 | 必填目标集合完全由调用方的 TargetManifest 决定，包只验证集合成员及完整性。 | 根据模板文本/模型响应自行猜 required。 | T-M2-MAP-002；避免遗漏时被模型弱化。 |
| CC-DEC-003 | 覆盖率统计仅计算包内生产代码；测试代码不计入 100% 生产覆盖率，但测试代码必须纳入导入隔离扫描。 | 用包目录的总覆盖率混合测试代码。 | 让门槛聚焦真实实现，同时约束所有包内代码不引入禁用依赖。 |

## 附录 B：已裁定事项

负责人于 2026-10-23 批准本 CC 实施，并授权将以下四项实施裁定写入本附录。它们仅细化已冻结 TDD 留给 CC 的接口和资源限制，不改变 SRS/TDD 业务语义。

| 项目 | 裁定 | 实施与验证 |
|---|---|---|
| TDD 人工编辑方法名 | `validate_user_revision` 为规范公共入口；为兼容 TDD §3.2，`apply_manual_edits` 导出为同一实现的别名。 | 两个名称均调用同一验证逻辑；单测证明结果一致。 |
| JSON / 数组规模上限 | UTF-8 原始 JSON 最大 65,536 字节；最多 200 mappings、100 clarifications、200 skipped targets、200 user edits；标识符最长 255 字符，clarification 问题最长 2,000 字符。reason code 仅允许 `missing_source`、`ambiguous_mapping`、`unsupported_target`、`conflicting_instruction`。 | 边界值与越界用例纳入 CC-TEST-002 / 006；reason code 不匹配时 fail closed。 |
| Coverage 工具与安装方式 | 锁定 `pytest==8.4.2`、`pytest-cov==7.1.0`、`coverage==7.16.2`。 | 仅作为测试依赖写入包内 `requirements-test.txt`；负责人授权安装到项目 `venv`，不加入生产依赖。 |
| 字段/目标类型兼容 | validator 只接受调用方归一化的 `string`、`number`、`boolean`；Proposal `value_type` 必须同时属于授权字段类型和目标 `allowed_value_types`。 | 不做隐式类型转换；date、关系字段等须由上层先归一化；越出集合则拒绝。 |

上述四项已关闭。若实现需要新增数据类型、转换语义或超出锁定测试依赖的安装，须停止并重新修订 CC/TDD。

## 附录 C：版本历史

| 版本 | 日期 | 状态 | 说明 |
|---|---|---|---|
| V0.1 | 2026-10-22 | Draft | 基于 M2 SRS V1.0.0、TDD V1.0.0、Implementation Plan V1.0.0 和 TV Report V1.1 起草纯 Python validator 首个实施契约。 |
| V1.0.0 | 2026-10-23 | FROZEN | 负责人批准实施；完成附录 B 四项裁定，冻结接口、输入限制、测试依赖和归一化类型交集。 |
