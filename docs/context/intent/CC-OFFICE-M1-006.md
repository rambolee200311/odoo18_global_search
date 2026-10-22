<!-- 使用 Coding/CC 模板；负责人于 2026-10-22 批准冻结并实施；未通过的集成验收仍按原状态保留。 -->

# CC-OFFICE-M1-006 — Office Engine M1 聊天适配与用户场景验证

## 0. 文档治理

| 字段 | 值 |
|---|---|
| Coding Contract | `CC-OFFICE-M1-006` |
| 版本 | `v0.3 Frozen (MVP)` |
| 状态 | **FROZEN (MVP) / CLOSED — 负责人批准的阶段性交付范围已验收关闭；剩余能力移交 M2** |
| Intent ID | `OFFICE-ENGINE-M1-CHAT-ADAPTER` |
| 类型 | 独立 Odoo 聊天适配与 UI 验证 |
| 模块 | `mymodules/office_engine_odoo/`；本 CC 代码唯一允许目录 |
| 目标 | 在已验证的 Provider 前安全路由和 Odoo 请求封装之上，连接现有 Odoo-LLM 聊天入口与同步 Office 服务，展示受授权的读取状态、失败信息及已验证结果附件入口；不让 Office 内容进入 LLM Provider payload |
| 上游 SRS | [Office 自动化 SRS](../../requirement/SRS_office_document_automation.md) `V1.0.0 Frozen` |
| 上游 DDD | N/A；按负责人已确认的 M1 决策 |
| 上游 TDD | [Office Engine M1 TDD V0.4](../../design/TDD_office_engine_m1_v0.4.md) `Frozen`；Provider 前修复补充 V1.0.0 Frozen（仅用于已完成的 pre-route 修复，不替代聊天路由 Spike） |
| 上游计划 | [Implementation Plan V0.5](../../implementation/IMPLEMENTATION_PLAN_office_engine_m1_v0.5.md) `Frozen`；允许开始 Phase 6 实施，保留 Phase 5/CC-004 验收门禁 |
| 相关证据 | CC-005 FR `NOT SATISFIED`；独立 PRE-ROUTE-FIX FR `SATISFIED`（仅限该修复 CC 范围）；CC-004 FR `NOT SATISFIED` |

### 0.1 当前前置门禁与实施授权边界

负责人于 2026-10-22 批准本 CC 的 M1 MVP 范围关闭：真实上传、Provider 前拒绝、错误气泡、输入框恢复、普通附件回归和人工确认。此为本 CC 的明确范围处置，不把未完成能力伪记为通过。CC-004/CC-005 的历史失败与阻塞状态完全不变；Office handoff、Mapping 输入、文档生成/回读和结果附件交付从本次 CC 关闭范围移出，移交 M2 验收。在这些依赖关闭前，不开放未经验证的 Office 路由。

| 前置项 | 当前证据状态 | 对本 CC 的影响 |
|---|---|---|
| CC-005 原始 Provider 路由 Spike | 行政关闭；FR `NOT SATISFIED`；原 ATR 为 7 PASS、1 FAIL、2 BLOCKED | 保留历史状态；handoff 相关验收仍 BLOCKED |
| `ISSUE-005-01` 伪装 Office 附件拦截 | 独立 `CC-OFFICE-M1-PRE-ROUTE-FIX` FR `SATISFIED` | 仅证明该修复 CC 范围，不回写 CC-005 历史测试 |
| CC-005 CC-TEST-005/008 内部 handoff | `BLOCKED / INCONCLUSIVE` | 开发可继续；Provider handoff 及依赖验收不得开放或关闭 |
| CC-004 请求模型成功生成/附件交付 | FR `NOT SATISFIED` | UI/错误呈现等独立工作可继续；成功状态和结果链接保持关闭 |
| AC-05 用户 Mapping 确认 | 负责人批准移交 M2 | 不阻塞本次无 Mapping UI 的 M1 MVP 关闭；M2 仍须按 SRS 验收 |

Implementation Plan V0.5 记录了负责人对 Phase 6 开工顺序的明确决定：允许 CC-006 独立实现先行，CC-004/005 修复与验证并行推进。此为开工授权，不是测试豁免或通过结论。
## 1. 变更概述

### 1.1 背景

M1 的纯 Python `office_core`、独立 `office_verify` 与 Odoo 请求/附件封装已按各自 CC 交付其声明范围。负责人批准并确认 CC-006 的 M1 MVP：聊天真实上传、Provider 前安全拒绝、错误气泡、输入框恢复及普通附件回归。CC-005 handoff 与 CC-004 成功服务路径未通过，故 Office 路由、成功状态和结果附件入口继续关闭，相关工作移交 M2。

### 1.2 本 CC 的 M1 MVP 目标

实现聊天安全拦截 MVP：真实附件上传和消息关联、Provider 前伪装/不允许 Office 附件拒绝、当前线程红色错误展示、错误后输入框恢复，以及普通附件不被误拦。聊天适配不得将 Office 二进制、Base64、抽取文本或可重建内容交给 Provider。内部 Office handoff、Mapping 输入、文件生成/回读和结果附件展示移交 M2。

### 1.3 负责人批准的 M1 MVP 范围处置

2026-10-22 负责人批准：本 CC 以已实施并人工确认的 UI 安全拦截路径作为 M1 阶段性交付关闭范围；用户 Mapping 输入 UI、内部 handoff、Office 文件生成与回读交付移交 M2。该决策仅处置 CC-006 的交付范围，不修改 SRS/TDD 基线，不将 CC-004 FR `NOT SATISFIED` 或 CC-005 FR/handoff 历史状态改为 PASS。M2 必须重新验收移交能力。

## 2. 上游基线与追溯

### 2.1 SRS 引用

| SRS ID | 标题 | 与拟议范围的关系 |
|---|---|---|
| FR-M1-001 / AC-01 | 聊天附件接收 | 关联当前用户、线程和消息；显示已接收/处理状态 |
| FR-M1-002 / AC-02、AC-07 | 类型及安全结构识别 | 识别失败或格式不支持时拒绝，且不进入模型/渲染路径 |
| FR-M1-003 / AC-03、AC-04 | Office 结构读取 | 调用已验证的内部读取服务；不得声称未识别对象已完整读取 |
| FR-M1-008 / AC-10、AC-17 | 附件回传及失败状态 | 仅显示本请求、当前用户可访问的结果；失败不得伪成功 |
| FR-M1-009 / AC-23 | 输出回读校验 | 只有后端回读成功的结果才能在聊天展示/下载 |
| NFR-OFFICE-01 / BR-OFFICE-15 | 权限与数据隔离 | 当前用户权限、记录规则和本请求授权不可被聊天适配扩大 |
| NFR-OFFICE-03 / NFR-OFFICE-06 | 最小披露与错误处理 | 不泄露附件内容、路径、traceback、其他用户信息 |
| NFR-OFFICE-11 | 事务与并发 | 聊天适配不持有长业务事务；状态与附件由服务层按 TDD 管理 |

AC-05 的用户 Mapping 确认不纳入本次 M1 MVP。负责人于 2026-10-22 明确将用户 Mapping 确认及其验收移交 M2；SRS 中的需求仍有效，M2 必须纳入其验收，不得将内部测试写成用户确认。

### 2.2 TDD 引用

仅引用 TDD V0.4 Frozen，不复制或扩展其技术方案：

| TDD 来源 | 本 CC 的 M1 MVP 落实 |
|---|---|
| §2.3、TD-001、TD-014 | 聊天适配作为独立第二部分；不改 Odoo 官方源码/Addons；仅在 Provider 前安全路由验证通过后开放 |
| §3.2—3.4 | 调用已定义的 Odoo 服务边界；聊天层不解析二进制、不传任意路径/uid/模型名/代码 |
| §6.1—6.2 | 使用短事务与同步有界服务；不新增 Queue Job、重试、取消或异步任务状态 |
| §7.1、§7.3 | 当前用户授权、fail-closed、脱敏稳定错误；Provider payload 不得含 Office 内容 |
| §8 TEST-OFFICE-001/002/003/004/009/014/015 | 上传关联、拒绝场景、结构读取、交付权限、错误脱敏及 Provider 隔离验证 |
| §9 与 §11.3 | 未验证能力保持关闭；本 MVP 关闭不视为聊天路由 Spike 或文件生成 PASS |

### 2.3 计划基线与负责人的实施决定

Implementation Plan V0.4 原先把 Phase 5 Resume Gate 设为 Phase 6 开工前置。负责人于 2026-10-22 批准先推进 CC-006 的独立实现，再并行闭环 CC-004/005；该决定已纳入 Implementation Plan V0.5。Phase 5 Gate 仍是 Office 路由开放和本 CC 验收关闭的前置，历史 FAIL/BLOCKED 状态保持原样。

## 3. 范围冻结

### 3.1 实施范围

- 通过已经验证的服务端入口把当前 Odoo 用户、线程、消息及附件引用关联到本次 Office 请求；身份和授权由 Odoo 服务端验证。
- 在 Provider 请求构造/发送前检查聊天上下文中的 Office 候选；任何身份不明、格式冲突、拒绝或路由异常均安全终止，不得退化为普通附件文本。
- 仅将附件授权引用交给已验证的内部 Odoo Office 服务；Office 原始字节、Base64、抽取全文和可重建内容不得进入任意 Provider payload 或工具循环。
- 对用户显示当前请求的接收、处理中/成功/失败状态和稳定的脱敏错误；不新增未经 SRS/TDD 授权的业务状态。
- 仅在内部服务返回当前用户有权访问、且回读通过的结果附件时，展示本请求的结果入口；无结果、失败、权限变化或关联校验失败时不显示可下载链接。
- 按 Implementation Plan 及项目 E2E 规范，使用标准浏览器人工验证并执行 Playwright UI 回归；API/ORM 注入不得替代聊天 UI E2E。

### 3.2 明确排除

- 在 Phase 5 Resume Gate 通过前开放 Office handoff 或 Provider Office 路由；开发期必须维持 fail-closed。
- AI 语义映射、LLM Provider 工具/函数调用、读取 Odoo 业务模型/业务记录、Skill、Mapping 编辑/确认 UI；M1 TDD 明确排除这些能力。
- 普通聊天用户通过本 CC 选择任意模板字段、业务模型或记录并生成文件；相关映射交互由后续批准阶段决定。
- 修改 `mymodules/odoo-llm/**`、`odoo/**`、官方 `addons/**`；绕过或删除上游附件安全检查；把 Office 内容转为文本发送给 Provider。
- 新增队列/异步任务、轮询/WebSocket、自动重试、请求恢复、取消或新任务模型。
- 开放未通过能力 Gate 的 `.xls`、`.doc`、复杂 OOXML/Word 对象或未准入格式。
- 更改 CC-004、CC-005 的原始 ATR/FR 结果；独立修复证据只能用于其自身限定范围。

### 3.3 非目标

- 本 CC 不把 CC-004 / CC-005 的历史失败改写为通过；其修复和真实运行证据仍需单独闭环，可与本 CC 的独立适配工作并行。
- 本 CC 不声明普通用户可在聊天中完成任意 Office 文档自动生成；Mapping Plan 的语义生成/用户确认不在 M1 TDD 范围内。
- 本 CC 不以当前修复 CC 的成功替代全量 Provider handoff、每 Provider payload 或 Phase 5 完整验收。

## 4. 代码与文档变更边界（唯一允许路径）

本 CC 涉及的所有产品代码、测试代码及 Odoo 扩展代码必须且只能存在于 `mymodules/office_engine_odoo/`。不得新增第二个 Addon，不得在该目录外放置实现或测试代码。

允许新增或修改的文件仅限以下类型和目录：

| 允许路径/类型 | 用途 |
|---|---|
| `mymodules/office_engine_odoo/__init__.py`、`__manifest__.py`、`models/__init__.py` | Addon 引导、依赖及模型扩展注册 |
| `mymodules/office_engine_odoo/models/llm_thread.py` | 通过 Odoo 标准模型继承适配当前线程的服务端消息/错误处理；不得改上游 `llm_thread` 源码 |
| `mymodules/office_engine_odoo/views/llm_thread_views.xml` | 仅在确有必要时继承现有视图并挂载自有前端资源 |
| `mymodules/office_engine_odoo/static/src/**` | 自有 JS/Owl、模板、SCSS 与资源声明，用于附件草稿、消息卡片及错误状态呈现 |
| `mymodules/office_engine_odoo/tests/**` | 本 CC 自动化测试及测试初始化文件 |
| `docs/implementation/office-engine-m1/CC-OFFICE-M1-006/` | 仅在 CC 冻结并获实施授权后保存 IHR/ATR/HVR/FR 和证据；不属于代码目录 |

除表列路径外，`mymodules/office_engine_odoo/` 内的其他文件类型也不自动获准；若实现需要新增路径类别，须先修订并重新评审本 CC。`mymodules/odoo-llm/**`、`odoo/**`、官方 `addons/**` 及其他任何产品/测试代码目录均禁止修改。若无法仅通过上述自有 Addon 扩展实现，停止并更新 TDD/计划，不得越界修改上游代码。

## 5. 批准的行为变更

| ID | 当前行为 | 期望行为 | CC-CHANGE |
|---|---|---|---|
| 1 | 聊天消息与已授权 Office 请求服务之间没有已验证的端到端适配链路 | 独立适配可先开发；只有在 Phase 5 完整 PASS 且 CC-004 成功路径闭环后，聊天适配才可把当前用户授权的附件引用交给内部服务，禁止 Provider 获取 Office 内容 | CC-CHANGE-001 |
| 2 | 上传/读取/请求状态无法在 Odoo-LLM 聊天中按当前请求可靠呈现 | 后端 `UserError` 必须由聊天适配层转成当前线程可见的红色错误气泡（`is_error` 消息）或受控错误通知；不得只留在日志/未处理 RPC 弹窗，不得泄露其他请求状态；错误呈现后输入框恢复可用并可继续发送普通文本 | CC-CHANGE-002 |
| 3 | 结果附件的聊天入口尚无端到端验证 | 只有服务端返回回读通过且当前用户有权访问的本请求结果时才显示入口；失败时不返回链接 | CC-CHANGE-003 |
| 4 | 当前没有标准浏览器端到端证据 | 对获准的用户场景建立 Playwright 回归和标准浏览器人工 HVR；真实上传与对话 UI 必须实际操作验证 | CC-CHANGE-004 |

## 6. 既有行为保留

| 行为/契约 | 保留要求 | CC-PRESERVE |
|---|---|---|
| Provider 前 Office 安全边界 | Office 二进制、Base64、抽取文本及可重建内容不得进入任何 Provider 请求 | CC-PRESERVE-001 |
| 普通附件聊天 | `.txt`、有效 `.png` 等非 Office 路径保持现有行为，不因 Office 安全闸门被误拒 | CC-PRESERVE-002 |
| 当前用户访问控制 | 使用当前请求用户 ACL/Record Rules；附件 ID 或消息引用本身不授予权限，不使用 `sudo()` 扩权 | CC-PRESERVE-003 |
| Office 服务与验证 | 继续使用现有 `office_core` / 独立 `office_verify` / Odoo 请求封装；不改变其数据契约 | CC-PRESERVE-004 |
| 同步首期 | 不引入 Queue Job、自动重试、取消、后台恢复或长业务锁 | CC-PRESERVE-005 |
| 错误和结果完整性 | 只有当前请求有效结果可展示；任何失败不显示伪成功/可下载附件 | CC-PRESERVE-006 |

## 7. 适用的 TDD 防护栏

| TDD 防护栏 / 条款 | 本 CC 适用位置 | 验证方法 |
|---|---|---|
| TDD §2.3、TD-014：Provider 前安全路由 | 聊天请求进入 Provider 前的服务端调用链 | 每个实际启用 Provider/消息路径 payload 断言；Phase 5 Resume Gate PASS |
| TDD §7.1：当前用户权限、输入身份和失败关闭 | 附件引用校验及内部服务调用 | 当前用户/跨用户、权限撤销、未知身份、内部服务不可用测试 |
| TDD §7.3：稳定错误且无敏感细节 | 聊天失败消息 | 用户可见错误文案断言及日志脱敏检查 |
| TDD §6：同步有界请求与事务边界 | 调用服务及显示状态 | 不持有长事务；超预算/超时终止且无下载结果 |
| TDD §8 TEST-OFFICE-015 | Office payload 隔离 | Mock/本地捕获证据；外部 Provider HTTP 计数为 0，除非另获授权 |

## 8. 数据与迁移影响

| 项 | 影响 |
|---|---|
| 数据库字段/迁移 | 预期无新增字段；若现有请求模型不足以满足冻结 TDD，停止并上报，不在本 CC 自行扩字段 |
| 附件/消息 | 复用现有 Odoo 消息、附件和 `office.document.request`；每次访问按当前用户重新授权 |
| 状态 | 只映射 TDD/SRS 已定义状态；不增加新业务状态 |
| 回滚 | 代码回退按模块升级策略处理；不得手工删除 filestore 文件。具体升级/恢复步骤待冻结 CC 中给出 |

## 9. API / 集成影响

| 字段 | 值 |
|---|---|
| 修改的公开 HTTP/JSON-RPC API | 无；除非冻结 TDD/计划批准，否则不新增公开路由 |
| Odoo-LLM 集成 | 仅通过已验证的独立 Addon 扩展路径；不得直接改上游代码 |
| Provider | 不新增 Provider 能力；Provider 请求只允许接收非 Office 普通聊天内容 |
| Browser/UI | 现有聊天窗口；仅通过 `mymodules/office_engine_odoo/views/llm_thread_views.xml` 与 `static/src/**` 扩展；不得改上游聊天组件。附件草稿显示、消息附件卡片和错误呈现均为验收对象 |

## 10. 安全 / 权限影响

- 当前用户环境是唯一数据授权依据；不接受模型或客户端提供的 uid、任意 attachment ID 作为访问授权。
- Office 内容不得交给 LLM、Provider、工具调用消息历史或日志；只有经授权的内部 Odoo 服务能读取文件内容。
- 未知、拒绝、解析失败或 Provider 路径未覆盖时 fail closed；不得退化为通用文本/图像序列化。
- 生成结果必须通过请求所有权、线程/消息关系、附件访问权和回读结果验证后再展示。
- 普通非 Office 附件须保持正确序列化和 UI 行为。
- `UserError` 必须在当前聊天线程呈现为可见的红色错误气泡或受控错误通知；呈现后 composer/输入框必须解除忙碌状态、恢复可编辑和可发送，不得要求刷新页面才能继续。
- 不记录 API Key、文件原文、Base64、业务字段值、服务器绝对路径或 traceback。

## 11. 测试契约

| 测试 ID | 验证项 | 方法与通过判据 | 人工验证 |
|---|---|---|---|
| CC-TEST-001 | Phase Gate/运行基线 | 运行实例、Odoo-LLM commit、Addon 列表与冻结计划一致；Phase 5 完整 Gate、CC-004 成功路径均有有效 PASS 证据，否则 BLOCKED | 否 |
| CC-TEST-002 | Office 上传与聊天消息关联 | 使用标准浏览器通过文件选择器实际选择并上传已获准合成模板。发送前断言聊天草稿 DOM 中可见该文件的准确文件名及附件图标/卡片；发送后断言当前线程消息流出现同一附件卡片并关联到该用户、线程和消息，状态正确；上传及发送期间浏览器 JS 控制台无 error/未捕获异常。不以 ORM/API 注入替代 UI。任一草稿或消息附件 DOM 断言失败即 FAIL，先修复本 Addon 内的 UI 扩展再继续验收 | 是 |
| CC-TEST-003 | Provider 前拦截与内部 handoff | Office 请求只到受控 Odoo 服务；当前用户/附件引用保持不变；每 Provider payload 无 Office 字节、Base64、抽取文本或可重建信息 | 否，ATR + mock/脱敏捕获 |
| CC-TEST-004 | 结构读取和受限结果展示 | 仅针对能力清单已启用的 `.xlsx`/`.docx` 场景，读取结构由服务端产生并可区分未知对象；不声称 AI 语义理解或全结构覆盖 | 是 |
| CC-TEST-005 | 权限与隔离 | 跨用户线程、附件、请求状态和结果链接均拒绝；当前用户可访问的本请求信息正常显示；无 `sudo()` | 否 |
| CC-TEST-006 | 失败与错误展示 | 伪装/损坏/不支持附件、服务不可用、权限撤销、超时、回读失败时，后端 `UserError` 或受控失败结果必须在当前线程渲染为可见的红色 `is_error` 错误气泡或受控错误通知，并显示稳定、脱敏的文案；不产生可下载失败结果。断言不是仅有未处理 RPC 弹窗/控制台错误；错误后输入框恢复可编辑、可发送，且可成功发送下一条普通文本；浏览器 JS 控制台无 error/未捕获异常 | 是 |
| CC-TEST-007 | 结果附件交付 | 只显示回读 PASS、附件提交成功且当前用户可读的本次输出；A/B 用户隔离生效，旧请求/其他线程附件不可串用 | 是 |
| CC-TEST-008 | 非 Office 附件回归 | `.txt` 和有效 `.png` 仍按既有聊天路径处理；真实 OpenAI serializer/mock payload 结构正确；无误拦截 | 是 |
| CC-TEST-009 | Provider 范围覆盖 | 覆盖目标实例启用的每个 Provider、普通对话/工具循环/附件路径；未覆盖项逐项 BLOCKED，不得外推 | 否 |
| CC-TEST-010 | Playwright UI 回归 | 覆盖真实文件选择、草稿附件 DOM、提交后的消息附件卡片、处理中/失败/成功状态、结果链接、跨线程刷新/恢复可见性，以及 CC-TEST-006 的错误呈现和 composer 恢复；记录浏览器 JS console，存在 error/未捕获异常即 FAIL。若 AC-28 行为超出 M1 TDD 范围则停止并升级，不自行实现异步 | 否 |
| CC-TEST-011 | 脱敏和清理 | 证据无密钥/正文/Base64/绝对路径；合成消息/附件经 ORM 清理；临时 hook/Provider stub 清理且无残留 | 否 |
| CC-TEST-012 | 用户人工场景 HVR | 人工在标准浏览器完成至少一个允许成功场景及每类拒绝/错误场景；留存可审计截图、用户/页面/步骤和结果；不以截图替代服务端证据 | 是 |

### 11.1 拟议 HVR 场景

1. 业务用户通过真实文件选择器上传准入范围内的合成 Office 文件：发送前，草稿区域可见准确文件名及附件图标/卡片；提交后，消息流可见同一附件卡片并显示受控读取状态；全程无 JS 控制台错误。不要求 AI 推断映射。
2. 上传伪装或损坏 Office 文件，断言当前线程 DOM 中出现红色错误气泡（`is_error`）或受控错误通知，且包含脱敏拒绝提示；不得只出现未处理 RPC 错误弹窗。Provider 未调用；composer DOM 恢复可编辑、可发送；随后发送普通文本并确认成功，且后续 Provider 轮次不包含被拒绝附件或错误消息；浏览器 JS 控制台无 error/未捕获异常。
3. 上传 `.txt` 和有效 `.png`，确认既有聊天路径可用且未被 Office 闸门误拦。
4. 对已有已回读通过且授权的请求结果，确认聊天展示的链接只指向当前线程/请求的附件；无权用户不可打开。

如冻结范围未提供可由普通用户产生的合法 Mapping Plan，则不得伪造端到端“生成成功”场景；该 HVR 项保持 `BLOCKED / N/A`，并按 SRS/计划确定处置。

## 12. 停止条件 / 升级闸门

| 触发条件 | 处理 |
|---|---|
| Phase 5 handoff 未取得全量 PASS | Office Provider 路由维持 fail-closed；handoff 验收保持 BLOCKED 并移交 M2。本 CC 仅可按负责人批准的无 handoff MVP 范围关闭 |
| CC-004 FR 仍 NOT SATISFIED，或当前服务不能稳定完成本请求/附件交付 | 不展示成功状态/结果链接；成功服务验收移交 M2。本 CC 仅可按负责人批准的无生成交付 MVP 范围关闭 |
| 独立 Addon 无法在所有 Provider 路径前拦截/授权路由，或需改 Odoo-LLM 官方源码 | 停止；更新 TDD/计划并重新评审，不得自行改上游 |
| Mapping Plan、用户确认或业务模型读取需求超出冻结 TDD | 停止；退回 SRS/TDD/计划，不加入 LLM 或业务查询功能 |
| 目标格式/结构没有通过对应 capability gate | 对该格式/结构关闭并明确拒绝，不把未验证样本标为支持 |
| 发现需要新字段、状态、接口、依赖或异步任务 | 停止；先更新并批准 TDD/计划 |
| 人工 UI 上传链路或 DOM 附件呈现本身故障 | 当前 CC 的 UI 验收为 FAIL；先在 `mymodules/office_engine_odoo/static/src/**` 或允许的自有视图扩展内修复，再重跑上传与 DOM 断言。不得以 ORM 注入、截图或 API 请求冒充 UI E2E；若只能改上游 Odoo-LLM/官方代码才能修复，则停止并更新 TDD/计划 |

## 13. 完成定义

1. 本 CC 经过单独评审、冻结并获明确实施授权；本次关闭范围经负责人于 2026-10-22 批准限定为聊天安全拦截 MVP。Office handoff/成功交付 Gate 未通过的部分不宣称通过，明确移交 M2。
2. 所有 CC-CHANGE 已实现；无越界修改或官方源码改动。
3. 所有适用 TDD 防护栏均有当前代码基线的自动化证据；每个目标 Provider 路径都已覆盖或明确受限。
4. M1 MVP 必需的标准浏览器 HVR 有明确证据并由负责人确认；不得以 ORM/API 模拟替代最终用户 UI 场景。更广泛的成功/跨用户 UI 自动化移交 M2。
5. 普通附件回归、当前用户附件校验、拒绝/错误 UI 场景通过；Office 内容未进入 Provider payload。handoff 与跨用户结果链接验收移交 M2。
6. 负责人已明确批准将 AC-05 用户 Mapping 确认移交 M2；M2 仍须按 SRS 取得真实用户确认，不得把内部调用描述成用户确认。
7. IHR/ATR/HVR/FR 完整；M2 移交项明确列出；负责人批准范围处置已登记。CC-004/005 历史 FAIL/BLOCKED 状态不得改写为通过。

## 14. 追溯矩阵

| 上游 ID | CC 落地项 | 备注 |
|---|---|---|
| FR-M1-001 / AC-01 | CC-CHANGE-001；CC-TEST-002 | 聊天附件接收/关联 |
| FR-M1-002 / AC-02 / AC-07 | CC-TEST-003、006 | 类型与安全拒绝；继承已验证路由 |
| FR-M1-003 / AC-03 / AC-04 | CC-CHANGE-002；CC-TEST-004 | 只调用内部结构读取能力；具体格式 Gate 仍适用 |
| FR-M1-008 / AC-10 / AC-17 | CC-CHANGE-002/003；CC-TEST-005—007 | 状态、授权结果和失败处理 |
| FR-M1-009 / AC-23 | CC-CHANGE-003；CC-TEST-007 | 只展示后端回读通过结果 |
| NFR-OFFICE-01 / NFR-OFFICE-03 / NFR-OFFICE-06 | CC-PRESERVE-001/003/006；CC-TEST-003/005/006/011 | Provider 隔离、权限、错误最小披露 |
| NFR-OFFICE-11 / TDD §6 | CC-PRESERVE-005；CC-TEST-001/006 | 同步服务边界、无长业务锁 |
| TDD TEST-OFFICE-015 | CC-TEST-003/009 | Provider 前路由及 payload 证据 |

**不纳入追溯：** AC-05 用户 Mapping 确认、FR-M2、Skill、业务模型/记录读取、AC-28 异步恢复；本 CC 不得据此扩展范围。

## 附录 A — 评审决策

| ID | 决策 | 状态 |
|---|---|---|
| CC-DEC-001 | CC-006 只接入已验证的内部 Office 服务，不在 Provider 中解释/处理 Office 文件 | Approved |
| CC-DEC-002 | 不提供 AI Mapping 或 Mapping 编辑/确认 UI | Approved；与 M1 TDD 边界一致 |
| CC-DEC-003 | 负责人批准 Phase 6 独立实现可在 CC-004/005 Gate 未关闭时开始；Office handoff 和成功交付保持关闭，直到相关 Gate 通过 | Approved 2026-10-22；不豁免任何测试，也不把 FAIL/BLOCKED 改为 PASS |
| CC-DEC-004 | 若缺乏合法 Mapping Plan 的用户确认来源，不伪造生成成功验收 | Frozen；用户 Mapping 确认由负责人移交 M2 验收 |
| CC-DEC-005 | 负责人批准将 CC-006 按 M1 聊天安全拦截 UI MVP 范围关闭；Mapping UI、handoff、生成/回读和结果交付移交 M2 | Approved 2026-10-22；不改写 CC-004/005 历史状态 |

## 附录 B — 版本历史

| 版本 | 日期 | 状态 | 说明 |
|---|---|---|---|
| v0.1 | 2026-10-22 | Draft | 按负责人要求起草；保留 CC-005 行政关闭但 FR NOT SATISFIED、PRE-ROUTE-FIX 限定范围 PASS、CC-004 FR NOT SATISFIED 与 Plan V0.4 Phase 5 Gate 未通过事实。 |
| v0.2 | 2026-10-22 | Frozen — approved for implementation | 按负责人批准推进 CC-006 独立适配工作，更新实施计划至 V0.5；不豁免验收、不开放未经验证的 Office handoff，CC-004/005 失败/阻塞事实保持原状。 |
| v0.3 | 2026-10-22 | Frozen (MVP) / Closed | 负责人批准以聊天安全拦截 UI 作为 M1 阶段交付关闭范围；CC-TEST-004/007 移交 M2，CC-TEST-009 标为 N/A；CC-004/005 原状态不变。ATR/HVR/FR 与 ORM 清理证据更新。 |
