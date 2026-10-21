# CC-OFFICE-M1-005 — Provider 前 Office 附件路由与 payload 隔离 Spike

## 0. 文档治理

| 字段 | 值 |
|---|---|
| Coding Contract | `CC-OFFICE-M1-005` |
| 版本 | `v0.1 Draft` |
| 状态 | **DRAFT — 仅供评审；未授权实施** |
| Intent ID | `OFFICE-ENGINE-M1-PROVIDER-PRE-ROUTE-SPIKE` |
| 类型 | 验证性 Spike；不交付产品功能 |
| 上游 SRS | [Office 自动化 SRS](../../requirement/SRS_office_document_automation.md) `V1.0.0 Frozen` |
| 上游 TDD | [Office Engine M1 TDD](../../design/TDD_office_engine_m1_v0.4.md) `V0.4 Frozen` |
| 上游计划 | [Office Engine M1 Implementation Plan](../../implementation/IMPLEMENTATION_PLAN_office_engine_m1_v0.3.md) `V0.3 Frozen`，Phase 5 |
| 相关 CC | CC-001/002/003 已关闭；CC-004 已按负责人指示行政关闭，但其 FR 为 `NOT SATISFIED`，成功生成链路仍失败 |
| 目标 | 验证 Odoo-LLM 在 Provider 请求发出前能否以独立 Addon 扩展点识别 Office 附件、阻止 Office 内容进入 Provider payload，并在当前用户权限上下文中路由到受控 Odoo 服务或安全拒绝 |

### 0.1 冻结前置状态

本 CC 现在仅为 Draft。Implementation Plan V0.3 Phase 5 的正式前置条件是 Part I 模型封装已通过阶段验收；当前 CC-004 的成功处理探针因 spawn 子进程无法导入 `odoo.addons.office_core` 而失败，且冻结计划仍列 CC-004 为 Draft。CC-004 的负责人行政关闭不改变此证据，也不等于 Phase 4 PASS。

因此，本 CC 可供技术评审和 Spike 范围澄清；**不得在上述前置条件未解决、计划基线未完成影响复核前冻结或执行**。解除方式须通过新批准基线明确：修复并验证 Part I 成功路径、更新实施计划阶段映射，或由负责人正式修订并批准相应阶段准入规则。不得在本 Draft 内自行豁免冻结计划门禁。

## 1. 目标与问题

Odoo-LLM 当前聊天链路可能在附件被分类、解析或序列化后交给不同 Provider。静态源码分析只能定位候选扩展点，不能证明运行时方法顺序、实际 payload 或用户权限上下文。Spike 必须用脱敏、可复现的运行证据回答：

1. Office 附件最早在哪个服务端钩子可识别，且该钩子是否早于任何 Provider 请求构造/发送；
2. 是否能在不修改 Odoo 官方源码/Addons 的前提下拦截并阻止二进制、Base64、抽取文本或可重建内容进入任一 Provider 请求；
3. 识别 Office 附件后，当前用户、线程及附件授权上下文能否传递到 `office_engine_odoo` 内部服务，或在授权失败/路由不确定时 fail closed；
4. 多 Provider、工具调用、消息附件格式及异常路径是否都遵守同一隔离边界。

本 Spike 不解决 Office 文件生成成功路径；该问题受 CC-004 遗留 spawn 导入失败影响，需先依 §0.1 闭环。

## 2. 基线与环境约束

| 输入 | 基线 / 约束 |
|---|---|
| SRS / TDD / Implementation Plan | 仅使用 §0 列出的冻结版本；若任何版本被替换，暂停并执行影响复核 |
| Odoo-LLM 源码 | 当前仓库子目录 `mymodules/odoo-llm/` 的 HEAD 记录为 `609ec6dda3645165f6a4a843d7af5d286081a29d`；检查时工作树有未提交修改，本值仅作导航，不是可复现 Spike 基线。冻结前必须记录准确文件快照/提交并确认目标实例加载的是同一代码 |
| Odoo 实例 | 仅获准的 Odoo 18 开发实例 `odoo18ce`、项目 `venv` 和 `odoo.conf`；不得创建隔离数据库 |
| Provider 验证 | 使用本地 mock/stub 或具备脱敏请求捕获能力的受控端点；默认禁止向真实外部 Provider 发送测试附件或内容 |
| 数据 | 仅使用合成 Office 附件与合成消息；不得记录 API Key、客户数据、文件原文、完整 Base64 或可恢复的文档片段 |
| 变更 | 不修改 Odoo 官方源码/Addon、冻结纯 Python `office_core`/`office_verify`，不实现产品聊天路由或 UI |

## 3. 范围冻结

### 3.1 In Scope

- 对 Odoo-LLM 当前实现做运行时扩展点验证，覆盖接收聊天附件、构造 Provider 请求、工具循环及 Provider 调用前后相关路径。
- 使用独立验证代码/受控测试钩子记录调用顺序、当前用户与线程上下文、附件引用、请求字段名/类型和内容摘要；证据不得保存原始 Office 内容。
- 对每种实际纳入验证的 Provider/请求路径检查 Office 二进制、Base64、解析出的 Office 文本及可重建内容均未进入模型输入或 Provider payload。
- 验证无权/跨用户附件、缺失上下文、钩子异常、Provider 路径未覆盖、路由目标不可用时系统在 Provider 调用前拒绝或安全终止。
- 对普通非 Office 附件做必要回归对照，确认 Spike 的观察/临时验证手段未改变既有行为。
- 形成 `OFFICE-ENGINE-M1-PROVIDER-ROUTE-SPIKE-REPORT.md`、脱敏运行证据、目标源码基线和结论（PASS / FAIL / INCONCLUSIVE）。

### 3.2 Out of Scope

- 生产聊天适配器、聊天 UI、上传控件、状态轮询、结果卡片或真实用户交互。
- 生成 Mapping Plan、调用 LLM 理解模板、访问 Odoo 业务模型/记录、Skill 或白名单治理。
- 将文件内容发送给 OpenAI、DeepSeek 或其他外部 Provider；Spike 只能使用 mock/stub 或受控脱敏端点。
- 修改官方 `llm_thread`、`llm_assistant`、`llm_tool`、Provider Addon 或 Odoo 源码；若运行时证据证明必须修改上游，停止并提交上游变更提案，不在 Spike 中实施。
- 修复 CC-004 的 spawn/import 问题、Office 文件读写/回读、附件持久化或 CC-006 聊天适配。

## 4. 验证设计与测试契约

所有测试冻结时均为 `NOT RUN`。本文件仍为 Draft，以下预期不能当作已验证事实。

| 测试 ID | 验证项 | 方法与通过判据 | 人工验证 |
|---|---|---|---|
| CC-TEST-001 | 目标代码/运行时基线 | 记录 Odoo、Python、Odoo-LLM commit 与工作树快照、已安装 Addons/Provider 路径；运行实例与被检查源码一致，否则 BLOCKED | 否 |
| CC-TEST-002 | 钩子顺序 | 以合成 Office 附件触发消息路径，采集服务端有序事件；识别/拒绝钩子严格早于序列化和 Provider dispatch，否则 FAIL | 否 |
| CC-TEST-003 | Office payload 排除 | 对每个目标 Provider 捕获脱敏请求 schema 与内容指纹；不得包含二进制、Base64、全文抽取、片段或可重建 Office 内容；命中即 FAIL | 否 |
| CC-TEST-004 | Provider 路径覆盖 | 覆盖运行实例中每种启用 Provider、工具调用/普通聊天路径及附件表示；未覆盖路径逐项标 BLOCKED/MISSING，不得由单一 Provider 推广 | 否 |
| CC-TEST-005 | 用户/线程/附件授权上下文 | 使用真实低权限 Odoo 用户与两个用户/线程的合成附件，验证内部路由只接收当前授权引用；跨用户、缺上下文或授权撤销均在 Provider 请求前拒绝 | 否 |
| CC-TEST-006 | 安全失败行为 | 注入未知 MIME/扩展名、解析异常、钩子异常、路由服务不可用、Provider 配置缺失；任何不确定/异常 Office 路径均不得继续外发 | 否 |
| CC-TEST-007 | 非 Office 回归 | 对普通文本及明确允许的非 Office 附件运行对照；Spike 不改变既有 Provider 路径，也不误拦截不相关请求 | 否 |
| CC-TEST-008 | 扩展实现边界 | 验证独立 Addon 是否可在 Provider 调用前完成识别、阻断及受权转交；若依赖官方源码改动或无法证明全部路径，结论 FAIL/INCONCLUSIVE，不实现聊天功能 | 否 |
| CC-TEST-009 | 证据脱敏与复现 | 检查报告/日志不含密钥、文件内容、Base64、敏感字段或绝对临时路径；另一轮运行可由记录的 commit、配置与步骤复现 | 否 |

### 4.1 结果判定

- **PASS**：所有目标 Provider/消息路径均有当前运行时证据；Office 内容在 Provider 前被阻断；授权上下文与失败关闭行为通过；无需改官方代码；证据脱敏且可复现。
- **FAIL**：任一路径已证实 Office 内容可能外发、调用顺序晚于 Provider、权限可被扩大，或独立 Addon 无法满足隔离要求。
- **INCONCLUSIVE**：基线不一致、路径/Provider 未覆盖、捕获不完整或安全结论依赖推断。
- 任意 FAIL/INCONCLUSIVE 均阻塞后续聊天适配 CC-006；不影响已完成的纯 Python CC-001/002，也不改变 CC-004 原生证据。

## 5. 允许变更与产出

| 类别 | 允许 |
|---|---|
| 验证资料 | 新建 `docs/implementation/office-engine-m1/CC-OFFICE-M1-005/` 下 IHR、ATR、HVR（若适用）、运行脚本、脱敏日志及 Spike 报告 |
| 临时验证钩子 | 仅本地、测试专用、可撤销；不得作为产品功能启用，不得改变用户数据或持久化业务数据 |
| 产品代码 | 不在范围内；若验证必须修改产品/上游源码，停止并升级到新 TDD/CC |
| 配置/数据库 | 不改 Odoo 全局配置或 schema，不新增数据库/模块；仅使用既有批准开发环境和已安装的测试模块 |

必需交付物：IHR、ATR、Spike 报告、基线快照、脱敏 payload 核验产物、当前 Provider/路径覆盖矩阵、未决项和推荐结论。HVR 是否 N/A 按本 CC 冻结时的验证方式确定；不得以浏览器观察替代 Provider payload/权限运行证据。

## 6. 安全与数据治理

- 不启用或调用真实外部模型来处理测试附件；如需任何真实 Provider 网络请求，须先另获明确授权并使用无敏感合成文件与脱敏代理。
- 任何日志只记录字段名、长度、哈希/内容类型及路由结果，不记录文件字节、Base64、抽取文本或 secret。
- 禁止 `sudo()`、超级用户环境、公开附件 token、服务端任意路径及绕过 ACL 的临时工具。
- Office 附件识别不可靠、文件身份不一致或 Provider 路径不能完全覆盖时，统一 fail closed。
- 所有临时合成附件和记录使用唯一标记，通过 ORM 清理；不得直接删除 filestore 对象。

## 7. 完成定义与 Gate

1. 先关闭 §0.1 的 Part I/计划基线门禁，随后重新审查并冻结本 CC；Draft 不授权运行 Spike。
2. `CC-TEST-001—009` 均有原生状态、命令/步骤、环境和当前代码基线证据；没有 PASS 外推或遗漏 Provider 路径。
3. IHR、ATR、Spike 报告及证据目录完成，payload 检查不含 Office 内容或 secret；保留所有 FAIL/BLOCKED/NOT RUN。
4. 结论明确回答独立 Addon 可否安全路由；若失败，记录所需上游技术变更，不实施聊天功能。
5. 负责人审阅并决定是否允许进入 Phase 6；Spike PASS 本身不授权 CC-006 实施。

## 8. 版本历史

| 版本 | 日期 | 状态 | 说明 |
|---|---|---|---|
| v0.1 | 2026-10-21 | Draft | 按 Implementation Plan V0.3 Phase 5 起草；明示 CC-004 成功路径 FAIL 与冻结计划前置条件，未授权实施。 |
