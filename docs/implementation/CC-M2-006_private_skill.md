<!-- Skill bundle metadata
Source template: docs/skill/odoo-project-workflow/references/templates/Coding/Coding_Contract模板.md
Source version/status: v1.0.0; Frozen
Template synchronization check: PASS, 2026-10-23
-->

# CC-M2-006：私有导出 Skill 保存、精确匹配与复用

## 0. 文档治理

### 0.1 执行元数据

| 字段 | 值 |
|---|---|
| Intent ID | `OFFICE-ENGINE-M2-006-PRIVATE-SKILL` |
| Coding Contract | `CC-M2-006` |
| 模块 | `office_engine_m2` |
| 工作类型 | 新功能 / 私有映射规则复用 |
| 变更类型 | 私有 ORM 模型、受控保存/匹配服务、生成后提示和复用编排 |
| 版本 | `V0.1` |
| 状态 | **DRAFT — 待评审与冻结；不授权编码** |
| 目标 | 用户在一次生成成功后可自愿保存当前确认映射为个人私有 Skill；后续精确匹配时跳过 LLM 映射推理，仍实时取数、重新校验并经用户确认后调用 M1。 |
| SRS 基线 | `SRS_office_engine_m2_ai_mapping.md V1.0.0 Frozen` |
| DDD | N/A；沿用 M2 TDD 判定 |
| TDD 基线 | `TDD_office_engine_m2.md V1.0.0 Frozen`；动态列表补充 `TDD_office_engine_m2_dynamic_rows_addendum_v1.1.0.md` |
| Implementation Plan 基线 | `IMPLEMENTATION_PLAN_office_engine_m2.md V1.0.0 Frozen` 阶段 6；动态列表补充 V1.1.0 作为当前 CC-M2-005 的范围补充 |
| 前序工作 | CC-M2-001 至 CC-M2-005；CC-M2-005 执行处置为 `CONDITIONALLY CLOSED`，不代表 M2 全量 E2E 已满足 |
| 起草日期 | 2026-10-23 |

### 0.2 基线与状态约束

- 本文仅冻结 CC-M2-006 的评审范围；`DRAFT` 不授权实现。
- 私有 Skill 的业务语义来自冻结 SRS `FR-M2-009/010/011`、`BR-M2-004/005/006/007/008` 和 `AC-12–17/22/24`；技术边界来自 M2 TDD §8、§11、§13、§18 及 `T-M2-DATA-001` 等防护栏。
- CC-M2-005 的条件关闭、动态行证据及全量回归失败按原记录保留。Skill 实现不得将这些状态覆盖为 PASS，也不得扩大 M1 格式开放范围。
- 本 CC 按冻结 SRS 解释“绑定模型”为 Odoo 技术模型（如 `sale.order`），而不是固定某条业务记录。每次新请求仍须由用户/受信服务指定当前目标记录；Skill 不保存 `target_record_id`。如要求将 Skill 固定绑定到特定业务记录，必须先修改上游需求与数据设计。
- Skill 命中跳过的是 AI 映射推理，不跳过本次明确确认、授权检查、实时取数、Mapping 校验、M1 回读校验或附件隔离。冻结 SRS `FR-M2-010` / `BR-M2-004` 要求用户确认 Skill、模型及本次目标记录后方可生成；因此本 CC 不授权无确认自动渲染。

## 1. 变更概述

### 1.1 背景

M2 已具备经校验的映射规则、聊天确认、当前用户授权取数和 M1 渲染链路。用户需要在某次文件成功生成后，将已确认的规则保存为个人私有资产，避免相同模板及目标模型下重复调用 LLM 推理。

### 1.2 目标行为

建立 `office.export.skill`，由服务端仅从**已完成且已验证的 M1 请求**及其 Mapping Session 保存必要规则。后续请求由服务端计算模板指纹并按当前用户、公司、模板指纹和目标模型查找有效 Skill。唯一匹配时跳过 Provider/LLM 映射调用，按当前权限重新获取最新业务值，重新验证 Skill 规则，显示本次匹配信息并等待用户确认，再调用现有 M1 服务。

## 2. 上游基线与追溯

### 2.1 SRS 引用

| SRS ID | 相关要求 |
|---|---|
| `FR-M2-009` | 文件已成功生成且通过 M1 校验后，用户可显式保存为个人私有 Skill；只保存映射、模板特征和模型关联。 |
| `FR-M2-010` | 精确匹配本人有效 Skill 后可跳过 AI 映射推理；展示命中 Skill、模型和本次目标摘要，取得本次确认后用最新授权数据生成。 |
| `FR-M2-011` | Skill 仅所有者可访问/使用；停用或待验证规则不得自动匹配。 |
| `BR-M2-004/005` | 仍须本次确认；每次生成实时读取当前授权值。 |
| `BR-M2-006/007/008` | Skill 仅保存规则、不保存业务值；按用户/公司隔离；匹配不得绕过权限、校验和 M1。 |
| `NFR-M2-002/006/007` | 用户/公司隔离、数据最小化、可观察性能；不承诺固定秒级 SLA。 |
| `AC-12–17/22/24` | 保存条件、唯一/多重匹配、跨用户拒绝、停用、禁止敏感数据持久化及命中时跳过 AI。 |

### 2.2 DDD

N/A。沿用冻结的 SRS/TDD，不新增领域聚合或业务状态。

### 2.3 TDD 引用

| TDD 约束 | 应用 |
|---|---|
| §8.1 `office.export.skill` 最小模型 | 用户/公司隔离；只保存规则和模板/模型关系；不保存业务数据、样例、模板或输出文件。 |
| §8.2 Skill 状态 | 仅 `active` Skill 可匹配；新增/修改规则须先成功验证才有效。 |
| §11 私有 Skill 权限 | 每次匹配重验 owner、company、模型、指纹、状态、字段白名单和 M1 能力；无公共发布。 |
| `T-M2-DATA-001` | Skill 仅存规则；不存记录 ID、字段实际值、样例、附件 ID 或文件 bytes。 |
| `T-M2-SEC-004` | 所有业务数据读取使用当前用户 `env` 和权限。 |
| `T-M2-MAP-001/002` | 保存及命中规则均通过同一纯 Python Validator / 服务端目标目录校验。 |
| TDD §9、§10 | 同步有界调用；认证 RPC；状态/revision 和错误响应由服务端控制。 |

### 2.4 实施计划追溯

`IMPLEMENTATION_PLAN_office_engine_m2.md V1.0.0 Frozen` 阶段 6 / 拟建 `CC-M2-006`：Skill 用户/公司隔离、实时取数、命中不调用 LLM 和 M1 复用闭环。本 CC 不改计划定义的阶段范围。

## 3. 范围冻结

### 3.1 在范围内

1. 新建 `office.export.skill`，至少包含 TDD §8.1 规定的 `name`、`owner_id`、`company_id`、`template_fingerprint`、`model_name`、`mapping_rules_json`、`state`、`revision` 及 Odoo 必需时间戳。
2. 通过受控服务保存 Skill：只有原生成请求已 `generated`、M1 回读已通过、输出已关联交付且 Session 属于当前用户/公司时，才允许显示和执行“保存为技能”。用户须主动确认并提供名称。
3. Skill 数据只包含服务端确认的目标元素 ID、来源字段 ID、允许操作/值类型及当前已批准的有限列表映射规则。不得包含任何本次业务值或预览样例。
4. 从 M1 服务端检查结果取得 `template_fingerprint`；客户端不得自行提供/覆盖指纹。当前基线使用 M1 `template_sha256`（源附件 bytes 的服务端 SHA-256）；模板任何字节变化均导致指纹不匹配，不承诺不同二进制但结构相同的文件等价。
5. 匹配条件至少为：当前用户 owner、当前公司、服务端当前模板指纹、Odoo 目标模型技术名相同、Skill 状态为 `active`。不固定绑定业务记录 ID。
6. 匹配唯一 Skill 后跳过 LLM 映射推理；用当前用户权限重新读取目标记录最新数据，验证现有字段/目标权限及 Mapping Plan，向用户展示命中 Skill、目标模型和本次目标记录摘要，并取得本次确认，再调用 M1 同步生成、回读和交付。
7. 处理无匹配、多个匹配、指纹变更、模型不同、规则失效、权限变化、已停用/待验证 Skill 等情况；不得静默选取或强行复用。
8. 验证 Skill 命中分支的 Provider 调用数为 0，同时 Retriever 和 M1 仍按本次请求正常调用。
9. 按当前 Owl/RPC 体系展示生成成功后的“保存为技能”操作；一般聊天消息不可触发此动作。

### 3.2 超出范围

- 公共 Skill、跨用户/跨公司共享、发布审核、企业级治理或管理界面。
- Skill 导入/导出、版本历史 UI、删除/物理擦除策略、审计留存扩展；删除和历史保留按 SRS `OPEN-M2-006` / `OIP-M2-007` 另行评审。
- Skill 对业务记录 ID 的绑定、保存值快照、离线/缓存业务数据或跳过实时读取。
- Skill 自动绕过当前请求确认，或绕过现有映射确认/完整性校验、Retriever、M1 `office_core` / `office_verify`、M1 请求幂等或附件权限。
- 更改 M1、`office_mapping_verify` 契约、Provider 层、Odoo-LLM 上游、SRS/TDD/实施计划或已冻结状态机。
- 未经上游准入的 `.xls`、`.doc`、复杂 `.docx` 对象或其他格式。

### 3.3 非目标

- 以 Skill 命中作为永久授权凭证；它只是用户规则，不代表记录/字段权限。
- 保证所有模板版本或所有相同结构文件都能命中；本 CC 只采用当前服务端模板 SHA-256 精确指纹。
- 对 Skill 匹配声明固定“秒级”性能指标；只记录耗时，不引入未经批准的 SLA。

## 4. 变更边界

### 4.1 允许修改 / 新增

实现代码必须且只能存在于 `mymodules/office_engine_m2/`；项目 CC/IHR/ATR/HVR/FR 记录放在 `docs/implementation/`。

| 路径 | 允许内容 |
|---|---|
| `mymodules/office_engine_m2/models/office_export_skill.py` | 新建 Skill ORM 模型、字段保护、服务入口及 owner/company 权限约束。 |
| `mymodules/office_engine_m2/models/__init__.py` | 注册 `office.export.skill`。 |
| `mymodules/office_engine_m2/security/ir.model.access.csv` | 为普通业务用户配置所需的最小模型权限。 |
| `mymodules/office_engine_m2/security/office_export_skill_rules.xml` | 仅所有者/当前公司可读写规则；不得设置跨用户规则。 |
| `mymodules/office_engine_m2/services/private_skill_service.py` | `save_from_success()`、`match_for_request()`、规则重验和实时取数编排。 |
| `mymodules/office_engine_m2/services/__init__.py` | 导出私有 Skill 服务。 |
| `mymodules/office_engine_m2/controllers/mapping_controller.py` | 认证的保存/匹配必要动作；不得接受 UID、owner/company、模板指纹或权限声明作为可信事实。 |
| `mymodules/office_engine_m2/static/src/components/office_mapping_card/office_mapping_card.js` | M1 成功后显示保存为 Skill 的可选动作；处理 Skill 名称和保存结果。 |
| `mymodules/office_engine_m2/static/src/components/office_mapping_card/office_mapping_card.xml` | Skill 保存按钮/对话卡片及已命中 Skill/目标摘要。 |
| `mymodules/office_engine_m2/views/office_export_skill_views.xml` | 仅当 TDD 所需最小所有者视图确需新增时，提供本人 Skill 的受控查看；不实现公共管理界面。 |
| `mymodules/office_engine_m2/__manifest__.py` | 注册新增自有安全、视图或资产文件并按需升版本。 |
| `mymodules/office_engine_m2/tests/test_private_skill.py` | 模型、保存条件、精确匹配、隔离、数据最小化及无 LLM 调用测试。 |
| `mymodules/office_engine_m2/tests/test_private_skill_http.py` | authenticated RPC 用户隔离、伪造参数及卡片动作测试（如需 HTTP 层覆盖）。 |
| `mymodules/office_engine_m2/tests/__init__.py` | 注册本 CC 测试。 |
| `docs/implementation/CC-M2-006_private_skill.md` | 本契约及经评审后的状态/历史。 |
| `docs/implementation/IHR-M2-006_private_skill.md` | 实施记录。 |
| `docs/implementation/ATR-M2-006_private_skill.md` | 自动化测试记录。 |
| `docs/implementation/HVR-M2-006_private_skill.md` | 适用的内置浏览器人工验证。 |
| `docs/implementation/FR-M2-006_private_skill.md` | 需求证据评估。 |

`office.export.skill` 是 TDD 已明确的模型，不得据本 CC 新增业务字段。若实现必须改其他 Addon、修改 TDD 字段/接口或变更上游策略，停止并升级评审。

### 4.2 禁止修改

| 类型 | 禁止事项 |
|---|---|
| 其他 Addon / 官方源码 | 不修改 `odoo/`、`addons/`、`mymodules/odoo-llm/`、`office_core/`、`office_verify/`、`office_engine_odoo/` 或 `office_mapping_verify/`。 |
| 数据权限 | 不使用 `sudo()`、`env(su=True)`、`with_user()` 或客户端传入的用户/公司标识读取业务数据或 Skill。 |
| 数据内容 | 不存/记录 Prompt、Completion、样例值、业务记录实际值、业务记录 ID、附件 ID、模板/输出文件或其 bytes。 |
| 映射执行 | 不接受任意 ORM 模型/字段/domain、文件路径、代码、坐标偏移或模型生成的执行指令。 |
| 交付流程 | 不自行创建输出附件或消息；只调用既有 M1 同步渲染/回读/交付入口。 |
| 需求与上游 | 不修改 SRS、TDD、TV 或实施计划；不扩大格式和 Provider 范围。 |

## 5. 必需的行为变更

| ID | 当前行为 | 期望行为 | CC-CHANGE |
|---|---|---|---|
| 1 | 成功生成后没有受控的私有 Skill 持久模型。 | 建立仅含模板指纹、目标模型、映射规则和所有者/公司边界的 `office.export.skill`；状态受服务器控制。 | `CC-CHANGE-001` |
| 2 | 用户确认映射并成功生成后不能显式保存为本人规则。 | 只有 M1 已成功验证并交付后，用户主动选择保存，服务端从已完成请求绑定的 Session 读取/重验规则并创建 Skill。 | `CC-CHANGE-002` |
| 3 | 后续相同模板与模型仍会重复调用 AI 映射。 | 服务端精确匹配本人当前公司 active Skill；唯一匹配时 Provider/LLM 映射调用数为 0，复用规则进入当前请求确认流程。 | `CC-CHANGE-003` |
| 4 | 复用映射可能使用陈旧值或过期权限。 | 每次复用都通过当前用户权限实时取数、重新校验规则和 M1 模板指纹；通过本次明确确认后才调用 M1。 | `CC-CHANGE-004` |
| 5 | Skill 访问隔离和无匹配/多匹配路径没有专门闭环。 | 用户 B 不可见/不可用 A 的 Skill；模板变更、模型不符、多匹配或无效规则不得自动执行。 | `CC-CHANGE-005` |
| 6 | 成功生成卡片没有 Skill 保存提示。 | 在成功交付状态展示可选“保存为技能”动作；未生成成功时不展示可创建的 Skill 动作。 | `CC-CHANGE-006` |

## 6. 既有行为保留

| 行为/契约 | 保留要求 | CC-PRESERVE |
|---|---|---|
| CC-M2-001 Validator | Skill 规则使用同一严格解析与字段/目标/类型/完整性校验；未知字段、重复目标和失效规则拒绝。 | `CC-PRESERVE-001` |
| CC-M2-003 Session | owner/company/thread/attachment、八状态及 revision 由服务端保证；Skill 保存必须关联成功的原 Session。 | `CC-PRESERVE-002` |
| CC-M2-004 Owl/RPC | 仅 M2 专用消息显示卡片；`rpc` 路径和后端 revision/owner 检查不放宽。 | `CC-PRESERVE-003` |
| CC-M2-005 M1 渲染 | M1 是唯一写入/回读/附件交付通道；Skill 命中不绕过确认、幂等和下载权限。 | `CC-PRESERVE-004` |
| 普通 Odoo 聊天/附件 | 普通消息及非 Office 附件功能不受影响。 | `CC-PRESERVE-005` |
| 数据最小化 | 不将业务数据、样例或文件内容写入 Skill、日志或 Provider Usage。 | `CC-PRESERVE-006` |

## 7. 适用的 TDD 防护栏

| TDD 防护栏 | 本 CC 落实位置 | 验证方式 |
|---|---|---|
| `T-M2-SEC-004` 当前用户授权 | 命中和生成的 Retriever/M1 路径 | 用户 A/B、不同公司 ACL/Record Rule 测试；无 sudo。 |
| `T-M2-DATA-001` Skill 数据最小化 | 模型字段、序列化规则、日志 | 将秘密哨兵值注入业务样例，扫描 Skill 持久值与日志，不得出现。 |
| `T-M2-MAP-001/002` 映射确定性校验 | 保存与命中复用规则 | Validator 对目标、字段、操作、类型、完整性重新校验；非法 Skill 不进入 M1。 |
| `T-M2-UI-001` 状态/revision/用户确认 | 命中展示与确认 RPC | 旧 revision、取消、重复点击和跨用户 Session 拒绝。 |
| TDD §8.2 / §11 Skill state & isolation | active 匹配、owner/company 限定 | disabled/pending_validation 不命中；同名不同用户互相不可见。 |
| TDD §9 同步执行边界 | 实时取数与 M1 调用 | Provider 命中路径无调用；Retriever/M1 有界调用失败时安全失败且无输出。 |

## 8. 数据与迁移影响

| 项目 | 处理 |
|---|---|
| 新模型 | `office.export.skill`，按 TDD §8.1 最小字段；不扩展业务数据字段。 |
| 新字段 | `name`、`owner_id`、`company_id`、`template_fingerprint`、`model_name`、`mapping_rules_json`、`state`、`revision` 及 Odoo 必要审计时间戳。 |
| `mapping_rules_json` | 仅存完整性校验通过的规则引用：目标元素 ID、source field ID、operation/value type、已批准的动态列表分组/有限行槽位标识；不存实际 value、示例、record/attachment ID 或任意表达式。 |
| 指纹 | 从服务端 M1 inspection 获取 `template_sha256`；不保存模板内容。仅完全相同 bytes 命中；内容字节变化必须不匹配。 |
| 默认状态 | 首次创建仅来自成功 M1 交付的规则，状态可为 `active`；若后续允许修改规则，依 TDD 转 `pending_validation`，但修改/停用 UI 不属于本 CC。 |
| 迁移/历史数据 | 新 Addon 模型首次安装/升级；无历史 Skill 回填。既有 Session/Usage 数据不变。 |
| 回滚 | 移除本 CC Addon 数据/模块代码按 Odoo 模块回滚流程处理；不直接删除 filestore，不影响已生成的 M1 附件。实际生产数据备份/恢复方式须在实施 ATR 记录。 |

## 9. API / 集成影响

| 字段 | 规定 |
|---|---|
| 新服务 | 内部 `save_from_success(session_id, expected_revision, name)` 与 `match_for_request(template_attachment_id, target_model)`；具体方法名实现时可在此接口语义内调整，不公开模型 CRUD RPC。 |
| 保存入口 | authenticated RPC 只接收 session ID、expected revision 和用户给定名称；owner/company、状态、请求 UUID、附件指纹和映射规则均由服务端读取。 |
| 命中入口 | 使用服务端当前上传附件、当前明确目标模型和当前用户/公司推导匹配条件；客户端不可传 Skill owner、company、指纹或 `target_record_id` 来改变 Skill 绑定。 |
| 命中响应 | 返回本人可见的 Skill 名称、目标模型、当前请求目标摘要、映射摘要、当前 revision 与确认提示；不返回其他用户的候选/存在性。 |
| LLM 调用 | Skill 唯一匹配且规则复验通过时，AI 映射 Provider 调用数必须为 0。规则不匹配或无效进入正常重新映射/澄清路径，不伪装为 Skill 命中。 |
| 数据读取 | 当前用户确认命中 Skill 及本次目标后，按当前用户 env 实时读取最新值；不得从 Skill/Session 样例读取业务值。 |
| M1 | 仅调用既有 `_render_request_sync`；以当前 request/session 的稳定幂等键渲染并由 M1 回读及交付。 |
| 多匹配 | 多个相同用户/公司/指纹/模型的 active Skill 不增加唯一约束；必须列出本人可用候选并请求用户选择，不得任意取第一条。 |

## 10. 安全 / 权限影响

- 普通用户只访问本人且属于当前允许公司范围的 Skill；`owner_id`/`company_id` 从当前 `env` 派生，客户端不能伪造。
- Record Rule 至少限制 `owner_id = user.id` 且遵循 TDD/SRS 当前公司语义。用户 A 的 Skill 不得出现在用户 B 的列表、命中、错误详情、日志或 RPC 响应中。
- 保存仅能由 Skill 服务从本用户本人成功且已交付的 M1 请求构建；禁止直接接受客户端 `mapping_rules_json` 或 ORM 原始 create/write 字典。
- 每次命中重新验证 owner/company、active 状态、当前 `template_sha256`、目标 `model_name`、字段 allowlist、目标 manifest、当前业务记录 ACL/Record Rules、Mapping Validator 和 M1 capability。
- Skill 不作为授权凭证。任何字段或记录权限变化、目标模型不匹配、模板指纹不匹配、规则失效时，必须拒绝复用或转正常映射流程。
- 日志仅记录 Skill ID（本用户范围）、命中/未命中类别、耗时、模型标识和错误分类；不得记录规则 JSON 全文、业务值、Prompt、样例或文件 bytes。
- 用户确认前不得调用 M1。取消、RPC 重放、过期 revision、无效 Skill 均不得生成附件。

## 11. 测试契约

| 测试 ID | 对应行为 | 测试类型 | 预期断言 | 人工验证 |
|---|---|---|---|---|
| `CC-TEST-001` | 保存资格与正常 Skill 创建 | TransactionCase | 仅当前用户/公司、状态 completed 且关联 M1 `generated`、已验证并交付结果的 Session 可保存；名称、服务端模板 SHA-256、目标模型及规则正确；owner/company 从 env 派生。 | 否 |
| `CC-TEST-002` | 未成功时拒绝保存 | TransactionCase | M1 failed/未回读/未交付、Session 非 completed、过期 revision 或用户未显式确认保存时均不创建 active Skill。 | 否 |
| `CC-TEST-003` | 敏感业务值不持久化 | TransactionCase + 存储扫描 | 将唯一业务值哨兵放入 Retriever 样例及 M1 输入；Skill 所有字段、mapping JSON、message、usage 和日志均不含该值、Prompt、文件 bytes、记录/附件 ID。 | 否 |
| `CC-TEST-004` | 用户隔离 | TransactionCase / HttpCase | A 保存后，B 的列表、read、match 和尝试使用均被拒绝/视为无匹配；不泄露 Skill 是否存在或规则；A 的记录保持不变。 | 否 |
| `CC-TEST-005` | 精确指纹与模型匹配 | TransactionCase | 同一当前用户、公司、模板 `template_sha256` 和同一 Odoo model 的唯一 active Skill 可命中；改动模板任一字节或改变模型必须不命中；伪造客户端 fingerprint 不影响服务端计算结果。 | 否 |
| `CC-TEST-006` | 命中跳过 AI，但实时取数和确认保留 | Provider Mock + TransactionCase | 命中 Skill 时 AI Provider 调用计数严格为 0；Retriever 被当前用户权限调用并返回本次最新合成值；卡片展示 Skill/model/本次目标并要求确认；未确认时 M1 调用数=0，确认后才按已校验规则调用 M1。 | 否 |
| `CC-TEST-007` | 映射规则复验 | Validator/Odoo integration | 规则中的未知字段、目标、operation、值类型、重复目标、不完整必填项、超界列表槽位或旧模板 hash 均拒绝；M1 调用数=0。 | 否 |
| `CC-TEST-008` | 多 Skill 匹配 | TransactionCase | 同一 fingerprint/model 下多个 active Skill 不任意选取；只返回当前用户可见候选并等待选择；他人候选不可见。 | 否 |
| `CC-TEST-009` | 停用/待验证规则不自动复用 | TransactionCase | `disabled`、`pending_validation` 不参与自动匹配；状态由服务端控制，客户端直接写状态被拒绝。 | 否 |
| `CC-TEST-010` | M1 复用和失败安全 | M1 integration + Odoo test | 用户确认后以实时最新值调用真实 M1 渲染及独立回读；生成失败/校验失败/附件交付失败均无成功 Skill 状态副作用或可下载输出。 | 是 |
| `CC-TEST-011` | UI 保存与命中路径 | 内置浏览器 HVR + 自动 UI | 成功下载卡片显示“保存为技能”；用户显式保存后看到成功反馈；同模板新请求显示命中 Skill 和本次确认信息；普通消息无该卡片、无 JS 错误。 | 是 |
| `CC-TEST-012` | 新鲜数据无缓存 | Retriever/M1 integration | 保存后改变测试业务记录；Skill 命中输出反映本次实时值，而非第一次保存时值或预览样例。 | 否 |
| `CC-TEST-013` | 并发/重复提交安全 | Odoo transaction test | 重复保存动作在 revision/幂等机制下不创建不受控重复记录；并发命中仍遵循唯一选择/确认，不重复生成同一 request UUID 输出。 | 否 |

测试仅使用可清理的合成用户、记录、模板和附件；Provider 以 Mock 验证调用计数，不访问真实外网。真实 M1 Python 引擎/`office_verify` 的集成测试使用有效合成 `.xlsx`。开发环境使用项目 `venv`、`odoo.conf`、既有 `odoo18ce`，不创建隔离数据库；测试后按 ORM 精确清理自己的标记数据。

## 12. 停止条件 / 升级闸门

| 触发条件 | 处理 |
|---|---|
| 冻结 SRS `FR-M2-010` 的本次用户确认与本 CC 希望直接自动渲染发生冲突 | 以 SRS 为准：保留用户确认。若业务要求免确认，停止并先走 SRS 变更评审；本 CC 不得自行豁免。 |
| M1 inspection 不能在当前已准入格式上提供服务端模板 SHA-256 | 停止匹配实现，升级 TDD/TV；不得接受客户端哈希或用文件名代替。 |
| Skill 要求存入记录 ID、样例值、模板文件或实际业务值 | 停止；违反 SRS/TDD 数据最小化。 |
| 规则无法由当前 Validator/TargetManifest 安全复验 | 停止复用；不为 Skill 绕过 Validator 扩 schema，先升级 TDD/CC。 |
| 需要跨用户/跨公司复用、公共发布、审批或删除/历史承诺 | 超出本 CC；转 M3 或另行修订 SRS/TDD。 |
| Record Rule 阻止当前用户按设计访问 Skill 或业务数据 | 停止并报告；禁止 `sudo()`、系统用户或其它用户上下文绕过。 |
| 需要修改 M1、Provider、`office_mapping_verify`、Session 八状态或其他 Addon | 停止并升级对应上游 TDD/Implementation Plan/CC。 |
| M1 条件关闭仍遗留的上传/启动链路导致本 CC 无法从既有可信 Session 进入匹配测试 | 仅可通过现有受控内部调用与合成 fixtures 验证 Skill 服务；若用户可见 M2 入口验收依赖缺失入口，标为 BLOCKED/MISSING，不得虚报 UI E2E PASS。 |

## 13. 完成定义 / 关闭标准

1. 仅在已成功、已验证并已交付结果后，用户可显式保存 private Skill；未成功时无可匹配 Skill。
2. `office.export.skill` 字段、ACL、Record Rule 和内部服务满足本 CC；跨用户/公司拒绝由自动化证据证明。
3. Skill 数据扫描证明不包含实际业务值、样例、Prompt/Completion、业务记录 ID、附件 ID 或模板/输出 bytes。
4. 相同用户/company、指纹和 Odoo model 的唯一 active Skill 命中；模板任何字节变化、模型不同或状态不 active 均不命中。
5. 命中路径 AI Provider 调用数为 0；Retriever 使用当前用户权限实时读取当前值，用户确认后调用 M1，M1 独立回读通过并安全交付。
6. 多匹配请求用户选择；失败、权限变化、撤销或规则失效无自动执行/下载附件。
7. 所有适用 TransactionCase、RPC/UI 测试通过；内置浏览器 HVR 记录 Skill 保存和命中/确认路径。失败/跳过/未运行按授权记录处理，不改写原状态。
8. 代码仅在 §4.1 白名单；IHR/ATR/HVR/FR 与本 CC 和当前基线一致。该 CC 关闭不代表 M2 项目级 PCR 完成。

## 14. 追溯矩阵

### 14.1 正向追溯

| 上游 | CC 变更 | 覆盖 |
|---|---|---|
| `FR-M2-009`、`BR-M2-006`、`AC-12/13/22` | `CC-CHANGE-001/002/006` | 保存资格、用户主动保存、规则最小化及不保存值/文件。 |
| `FR-M2-010`、`BR-M2-004/005/008`、`AC-14/15/24` | `CC-CHANGE-003/004` | 唯一匹配跳过 AI、明确确认、实时取数、继续 M1 校验。 |
| `FR-M2-011`、`BR-M2-007`、`AC-16/17/20` | `CC-CHANGE-001/005` | owner/company 隔离、非 active 不命中。 |
| `NFR-M2-002/006/007` | `CC-CHANGE-001/003/004/005` | 数据隔离、最小化和耗时观察。 |
| TDD §§8/11、`T-M2-DATA-001`、`T-M2-SEC-004` | `CC-CHANGE-001–005` | Skill 模型/状态、权限、实时数据与服务端复验。 |

### 14.2 反向追溯

| CC | 上游 | 类型 |
|---|---|---|
| `CC-CHANGE-001/002/006` | `FR-M2-009`、`AC-12/13/22`、TDD §8.1 | SRS/TDD |
| `CC-CHANGE-003/004` | `FR-M2-010`、`BR-M2-004/005/008`、`AC-14/24`、TDD §§9/11 | SRS/TDD |
| `CC-CHANGE-005` | `FR-M2-011`、`BR-M2-007`、`AC-16/17/20`、TDD §11 | SRS/TDD |
| `CC-PRESERVE-001/006` | CC-M2-001/002；`T-M2-DATA-001` | 前序 CC/TDD |
| `CC-PRESERVE-002/003` | CC-M2-003/004；TDD §§8/10 | 前序 CC/TDD |
| `CC-PRESERVE-004/005` | CC-M2-005；M1 TDD / M2 TDD §§9/10 | 前序 CC/TDD |

### 14.3 无 DDD

N/A；追溯链为 `SRS → TDD → Implementation Plan → CC → IHR/ATR/HVR → FR`。

## 附录 A — 实现级决策

| CC-DEC | 决策 | 依据 |
|---|---|---|
| `CC-DEC-001` | Skill `model_name` 是 Odoo 技术模型名；不存储当前目标记录 ID。 | TDD §8.1；`FR-M2-009/010` 绑定模型且每次请求重新指定/授权目标。 |
| `CC-DEC-002` | 使用 M1 服务端 `template_sha256` 做精确文件指纹；任何 bytes 变化均不命中。 | M1 Mapping Plan 的服务端 hash；TDD 要求服务端模板指纹，不信任客户端。 |
| `CC-DEC-003` | Skill 命中只跳过 LLM 映射推理，仍展示匹配信息并要求当前请求确认后生成。 | 冻结 SRS `FR-M2-010`、`BR-M2-004`。 |
| `CC-DEC-004` | 同一 owner/company/fingerprint/model 允许多个 Skill；多重匹配由用户选择，不加唯一约束。 | SRS `AC-15` 与 TDD §8.1。 |
| `CC-DEC-005` | 本 CC 不实现删除/历史保留产品语义。 | SRS `OPEN-M2-006` / Implementation Plan `OIP-M2-007`。 |

## 附录 B — 评审问题 / 待决事项

| 项 | 状态 | 处置 |
|---|---|---|
| `OIP-M2-007` Skill 删除/历史保留 | OPEN（沿用上游） | 本 CC 不实现删除/永久擦除/历史 UI，因此不阻塞保存和匹配；未来涉及该行为前须先关闭 SRS OPEN。 |
| 用户所说“同一模型记录”是否要求固定绑定同一业务记录 | 本 CC 按冻结 TDD 处理 | `model_name` 为技术模型名；Skill 不保存 record ID，每次由当前请求提供目标记录并重新授权。若要求固定绑定则回到 SRS/TDD 变更。 |
| 生产“秒级”性能阈值 | 不作为本 CC 门槛 | 仅记录命中分支 Provider 调用数为零及耗时观察值；不设未经批准 SLA。 |

## 附录 C — 版本历史

| 版本 | 日期 | 状态 | 说明 |
|---|---|---|---|
| V0.1 | 2026-10-23 | Draft | 基于冻结 M2 SRS/TDD 与实施计划阶段 6，起草个人私有 Skill 保存、精确匹配、跳过 LLM 映射、实时授权取数、用户确认和 M1 复用契约；不授权实施。 |
