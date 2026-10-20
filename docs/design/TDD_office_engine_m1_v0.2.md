<!-- Skill bundle metadata
Source template: docs/skill/odoo-project-workflow/references/templates/Designing/TDD模板.md
Source version/status: v1.0.0; Frozen
Template synchronization check: PASS, 2026-10-19
-->

# Odoo 通用 Office 文档自动化引擎 M1 技术设计说明书（TDD）

| 项目 | 内容 |
|---|---|
| 文档编号 | TDD-OFFICE-ENGINE-M1 |
| 文档路径 | docs/design/TDD_office_engine_m1.md |
| 文档版本 | V0.2 |
| 状态 | **DRAFT — NOT APPROVED FOR IMPLEMENTATION** |
| 起草日期 | 2026-10-19 |
| 范围 | M1：通用 Office 文件操作底座 |
| 上游需求 | SRS_office_document_automation.md V1.0.0 Frozen |
| DDD | 未发现本项目 DDD；适用性判断尚待记录 |
| 技术验证 | TV Plan V1.0.0 Frozen；原始 TV V0.1 Partial；P0-A Partial、P0-B Partial、P0-C 本机 Queue Job 链路 PASS / 生产资源预算 INCONCLUSIVE |

> 本版确定 M1 Office 核心服务采用有界同步执行；Queue Job 不是核心依赖。聊天适配、格式引擎、附件事务落地和 M2 长任务交互仍有明确门禁。本文是设计草稿，不构成编码授权或实施基线。V0.1 草稿保留于 docs/design/TDD_office_engine_m1_v0.1.md。

## 1 文档控制、目标与范围

### 1.1 目标

定义 M1 Office 引擎的服务边界、输入契约、同步处理生命周期、Odoo 附件与事务边界、格式能力策略、资源限制和验收追溯。M1 负责已授权 Office 附件的结构读取、受控映射写入、后端回读校验、错误处理和结果交付。

本 TDD 不实现 AI 语义推断、业务记录读取、Skill、Office 导入、白名单治理或审计产品。冻结 SRS 和 TV Plan 是上游权威，本文件不得静默更改其业务范围。

### 1.2 本次复核的权威输入

| 输入 | 状态 | 用途 |
|---|---|---|
| docs/requirement/SRS_office_document_automation.md | V1.0.0 Frozen | FR、BR、NFR、AC、配置、OPEN 项和里程碑验收 |
| docs/verification/TV_Office_Engine_M1_Plan.md | V1.0.0 Frozen | TV 样本、方法、状态和安全验证要求 |
| docs/verification/TV_Office_Engine_M1_Report.md | V0.1 Partial | 合成文件、候选库、性能和异常行为的基础证据 |
| docs/verification/evidence/TV_Office_Engine_M1/P0_Followup/P0_Followup_Report_v0.2.md | P0-A BLOCKED、P0-B PARTIAL、P0-C BLOCKED | 真实 XLSX、队列配置检查 |
| docs/verification/evidence/TV_Office_Engine_M1/P0_Followup/P0_Followup_Report_v0.3.md | P0-A BLOCKED、P0-B PARTIAL、P0-C 本机链路 PASS / 生产预算 INCONCLUSIVE | Queue Job 本地运行事实及生产限制 |
| docs/verification/evidence/TV_Office_Engine_M1/P0_Followup/P0_Followup_Report_v0.4.md | P0-A PARTIAL、P0-B PARTIAL、P0-C 本机链路 PASS / 生产预算 INCONCLUSIVE | TARGET.docx 局部读写事实 |
| docs/verification/evidence/TV_Office_Engine_M1/P0_Followup/P0_Docx_Results_20261019_TARGET.json、P0_Xlsx_Results_20261019_RealSample.json、P0_QueueJob_Runtime_20261019.json | 结构化原始证据 | 样本、运行环境、结果、边界和状态 |
| docs/analysis/office_automation_source_review.md | 静态源码调查 Draft | Odoo-LLM 附件拒绝、Provider 格式化和扩展点现状 |

本次仅修订 TDD。未改 SRS、TV Plan、TV 报告或结构化证据。现有证据状态不因本版设计建议改变。

### 1.3 范围和非目标

| 本 TDD 范围 | 不属于 M1 |
|---|---|
| 处理单个用户授权的模板附件；识别格式、读取结构和按显式 Mapping Plan 写入 | Odoo 业务模型/记录查询，AI 对业务字段或模板指令的语义推断 |
| 服务端验证输入映射、写入目标和输出结构 | Mapping 编辑器、Skill 创建/复用/审核和企业白名单治理 |
| 同步、有资源上限的文件处理及授权结果附件交付 | 通用异步任务框架、自动重试、任务取消、死信队列或生产 Queue Job 容量设计 |
| 兼容后续 M2 异步调度的服务接口边界 | PDF、图片、PPT/PPTX、宏执行或业务数据导入 |

M1 首期不实现 Queue Job。异步增强在同步核心完成并验收后单独设计；SRS 将 AC-28 列入 M2 里程碑，M2 必须解决 NFR-OFFICE-12 的长耗时交互行为。

## 2 技术架构与处理数据流

### 2.1 总体边界

逻辑上分为聊天入口、Office 核心服务和 Odoo 附件存储三个边界。Office 核心服务可由不同 Odoo 调用方同步调用；不持有 HTTP controller、浏览器连接、LLM Provider 或 Queue Job 的对象/回调，不负责把文件内容发给模型。

<pre><code>Odoo Chat / authorized caller
        |
        | attachment reference + confirmed Mapping Plan
        v
M1 Request Boundary
  - current user / thread / attachment authorization
  - request record and format policy
        |
        v
Synchronous Office Service
  - validate container and resource budget
  - read structure / validate mapping
  - render to isolated temporary output
  - reopen and verify output
        |
        v
Short Odoo delivery boundary
  - recheck authorization and input identity
  - create private ir.attachment and link request
        |
        v
Authorized chat attachment</code></pre>

核心服务 API 以普通同步返回值/稳定错误结果表达处理结果，不依赖 HTTP 生命周期。上层可以在未来独立调度该 API，但 M1 不实现该调度器。

### 2.2 M1 同步执行决策（TD-008）

1. M1 首期通过同步调用执行 Office 核心流程，不要求 Queue Job、任务线程池或完整异步工作流。
2. 服务必须设置输入字节数、容器展开量、条目/结构规模、单任务墙钟时间和处理进程资源上限；具体数值按 SRS OPEN-OFFICE-05 在目标环境验证后批准。未配置有效限制的格式不得生产启用。
3. 预检已知超限的请求，在解析/转换前明确拒绝；处理期间触发硬时限或资源上限时，终止当前处理进程、清理临时输出并报告失败，不无限占用 Odoo Worker。
4. 同步请求只接受估算可在批准预算内完成的工作。M1 不自动把超限请求转入 Queue Job；返回可理解的受限/超时错误。
5. 核心服务不绑定请求、响应、SSE 或浏览器状态；异步增强可在后续由独立调度层调用同一服务契约。
6. 不实现自动重试、取消、进度恢复或并发调度。异常请求不能重试成伪成功，用户可重新提交新的请求。
7. SRS AC-28 属于 M2 里程碑验收；M1 的超预算拒绝不宣称满足 AC-28。M2 必须在其验收前提供连接恢复后的状态与唯一结果获取能力。NFR-OFFICE-12 的最终系统义务不因 M1 同步决策而取消。

P0-C 本机 Queue Job 只读任务 PASS，生产预算 INCONCLUSIVE。该生产异步证据不阻塞同步核心服务设计或开发；它只在后续选择 Queue Job 时成为对应阶段的输入。M1 同步生产启用仍须有目标主机 worker、代理/HTTP 时限和内存预算。

### 2.3 Addon 包装边界

逻辑边界确定，物理模块拆分未确定：

- Office 服务必须保持 Provider 中立，可单独进行纯 Python/服务层测试。
- 现有 Odoo-LLM 聊天路径在 Provider 调用前拒绝 Office MIME；OpenAI 附件格式化没有 Office 结构读写能力；其他 Provider 行为未完整调查。
- 不得只删除 Office MIME 拒绝，也不得允许原始 Office 二进制进入任何 Provider payload。
- 是否由一个 Addon 同时提供 Office 服务与聊天适配，或拆为核心 Addon + llm_thread 适配 Addon，须由安全扩展 Spike 决定。现有独立 Addon 扩展先例不能证明此 Office 路径可安全接入。
- 不修改 Odoo 官方源码或官方 Addon。Spike 若不能证明独立 Addon 可在 Provider 之前拦截并路由，聊天适配保持未启用；不得用上游改动作为隐式方案。

这项 Spike 阻塞聊天适配的实现，不阻塞 Office 核心服务的模块内纯服务设计。

## 3 服务接口与 Mapping Plan

### 3.1 服务职责与调用方

SRS FR-M1-003 定义读取能力 read_office_to_text(attachment_id)，FR-M1-004 定义渲染能力 render_office_template(template_id, json_mapping)。M1 核心服务接受被授权调用方提交的附件引用及 Mapping Plan，并验证后处理。

SRS 规定 M2 才通过权限网关与 AI 生成语义 Mapping Plan；M1 不调用 LLM、不查 Odoo 业务模型、不把模板指令自动解释成业务字段。M1 的终端 Mapping Plan 提供方及聊天中的人工编辑/确认界面没有在 SRS 中定义清楚。最小澄清问题为：

> 在 M1（AI Mapping 尚未交付）阶段，合法 Mapping Plan 由哪一调用方提供、用户在哪里确认？M1 是否只提供内部受控服务接口供集成/测试调用，还是要求面向业务用户的手工映射入口？

本 TDD 不擅自增加 Mapping 编辑器。该问题阻塞端到端聊天渲染交互，不阻塞 Mapping schema 和服务端校验设计。

### 3.2 接口契约

| 接口 | 输入 | 返回 | 服务端责任 |
|---|---|---|---|
| inspect_attachment | 当前用户环境、已授权 attachment 引用 | 格式、模板指纹、带稳定 ID 的结构元素、未知结构、警告 | 验证所有权/线程关联、格式签名、容器、资源预算；只读，不查询业务数据 |
| render_template_sync | 当前用户环境、request_id、模板引用、已确认 Mapping Plan | 新附件引用、格式、回读摘要；或稳定错误 | 重验授权、映射校验、受限渲染、强制回读、结果授权和失败清理 |
| get_request_status | 当前用户环境、request_id | 该用户可见的状态和授权结果 | 每次按当前用户重新执行所有权与附件权限检查；ID 不作为授权凭证 |

接口是核心服务契约，不规定公开 JSON-RPC/HTTP 路由。适配层负责从聊天消息恢复用户、线程和上传附件关系。核心服务不接受服务器路径、uid、任意模型名、命令行、任意代码或 Provider 对象。

用户/模型对 Mapping 的确认必须由可信调用上下文提供；Mapping JSON 本身不能声明“用户已确认”。当前 SRS 未定义 M1 的映射交互，确认凭证的 UI/API 表达待 3.1 澄清。

### 3.3 Mapping Plan V1 最小契约

本契约只表达显式目标和值，不包含业务字段解析、表达式、循环、动态行扩展、公式生成或文件操作指令。

<pre><code>{
  "schema_version": "1",
  "template_sha256": "server-computed-sha256",
  "writes": [
    {
      "element_id": "xlsx:Sheet1!A1",
      "operation": "set_value",
      "value": {"type": "string", "data": "示例文本"}
    }
  ]
}</code></pre>

验证规则：

| 项 | 规则 |
|---|---|
| 根对象 | 只接受 schema_version、template_sha256、writes；未知键拒绝 |
| 元素标识 | 必须来自本次 inspect_attachment 返回的元素目录；模板指纹须匹配当前附件；未知/重复/不可写目标拒绝 |
| operation | 首期只允许服务端注册的 set_value；任何其他动作、公式、宏、表达式、路径或任意文件选项拒绝 |
| value | value 与 type 必须同时存在且符合目标格式/元素类型；缺字段、显式 null、空字符串、数字零和类型错误分别判定 |
| 显式 null | 与缺失值、空字符串区分；M1 V1 暂不提供“清除单元格/段落”语义，显式 null 返回 NULL_NOT_SUPPORTED。若产品要求清空行为，须在实现前形成 SRS 澄清/决策 |
| 空字符串 | 只对声明支持字符串写入的目标有效；表示写入空文本，不隐式删除整个段落、格式或结构 |
| 公式/结构 | Excel 公式格不可写；合并区域非锚点或无法稳定定位的目标不可写；Word 只有解析器明确标记可写且写入不破坏结构的元素可接受 |
| 来源值 | M1 只接收显式 literal；M2 的 Odoo 字段来源及追踪单独扩展，不在本版 schema 中猜测 |

文档定位、Word run/样式保持和 .xls/.doc 元素 ID 只有经过相应格式门禁才可声明为可写。任何格式能力未开启时，schema 可以拒绝该格式的 render 请求。

### 3.4 返回和错误契约

成功返回 request_id、state、detected_input_format、output_format、input/output 指纹、readback_summary 和经当前用户权限校验的输出附件引用。失败返回稳定 error_code、failed_stage、可纠正的用户说明及无输出标记；不得向调用方返回 traceback、路径、Provider token 或未经校验的附件 URL。

## 4 Office 格式能力与启用策略

“已观察”只表示对应样本/版本的实测；“未验证”不等同于可用。文件能打开不代表结构、视觉或业务内容保真。未通过某项格式门禁时，应在格式准入/功能能力表中关闭相应读写能力并明确拒绝，不能静默损坏或转换。

| 格式 | 识别/读取证据 | 受控写入与回读证据 | 公式/高级结构证据 | M1 暂定策略 |
|---|---|---|---|---|
| .xlsx | 合成结构读取有局部证据；真实销售管理模板 4 sheet/89 公式等可被当前库读取 | openpyxl 3.0.9 写入后公式文本可回读，但 89/89 缓存消失；样本中 OOXML extension 节点 8→4，丢弃 custom.xml；整体状态 P0-B PARTIAL | 真实样本有公式、合并、条件格式、验证、图片；无人工视觉验收。不得把 openpyxl 3.1.x 或 Alpha LO 推定为已通过 | 仅开放已验证且在结构能力清单内的元素。遇到未知/不支持扩展结构拒绝写入；公式缓存状态单独报告，不承诺重算 |
| .docx | TARGET.docx 可结构检查；普通段落在 workspace Python 3.12.14 / python-docx 1.2.0 副本修改后重开，P0-A PARTIAL | 部件/关系/图片/表格/页眉页脚数量在该样本前后相同；Odoo venv 无 python-docx，计划候选 1.1.x 未测 | TARGET 没有文本框/VML；中文字体视觉 INCONCLUSIVE；不能外推高级对象 | 候选仅限目标运行时验证后的安全文本节点；文本框、VML、域、修订、嵌入对象、复杂分页按未支持拒绝或限制 |
| .xls | 合成文件上 xlrd 1.2.0 可读部分值/结构；LibreOffice Alpha 合成 .xls→.xlsx→.xls 可打开；无真实 XLS | 未取得真实样本的受控写回/回读证据；LibreOffice 合成回转有属性差异 | 合成回转合并范围和公式保留，但 XF 样式元数据变化；公式/缓存/样式一般性未验证 | 未验证真实模板前不启用生产写入；不能只凭可转换就开放。针对目标结构有证据后可逐类开放 |
| .doc | 仅由合成 DOCX 经 LibreOffice Alpha 转 .doc 再转回作探测；无真实 DOC 样本 | 无真实业务文档写回及回读证据；直接 python-docx 不支持 .doc | 合成回转 VML shape 1→0、DrawingML 1→2；文字可抽取不等于对象保留 | 在真实样本、稳定版转换器和版式验收前拒绝写入/格式转换 |

### 4.1 引擎角色

- openpyxl、python-docx、xlrd、xlwt 和 LibreOffice 仍是候选，尚未形成依赖锁定或生产选型。
- LibreOffice 只作为经格式门禁批准后的旧格式转换/公式重算候选；不得把它设为所有格式的隐式必经步骤。
- LibreOffice Alpha 26.8.0.0 的样本结果不能代表稳定版或目标 OS；用其转换前必须由服务端验证容器，退出码为 0 或文件存在不能证明有效。
- .xlsx 的公式表达式是强制保护对象；公式缓存和计算结果独立报告。SRS 不承诺本系统计算/刷新缓存。若业务依赖缓存，须先按 OPEN-OFFICE-03 明确可接受策略。
- 输出默认保持原扩展名。升级格式必须经用户明确告知和确认，并验证输出扩展名、内容格式一致；当前没有格式升级路径通过完整验收。
- .xlsm、宏执行、活动内容执行不准入。

### 4.2 结构能力表

实现时由服务端格式 adapter 提供有限 capability descriptor（允许的读取元素、写入操作、验证项、已知不支持对象）。capability 是实现常量/版本化技术配置，不向用户开放任意扩展；不能将未覆盖 OOXML part 自动标为可忽略。若库无法完整识别输入中可能影响保真的对象，失败关闭。

能力表、未知对象探测和回读校验应由同一格式策略驱动；不在 UI、Provider 或模型参数中复制另一套格式许可规则。

## 5 Odoo 请求模型与状态

### 5.1 最小持久请求模型

建议保留最小 office.document.request 记录，不将其设计成 Queue Job。依据是 SRS FR-M1-001/008 要求把附件、线程和处理状态关联，AC-10/17 要求按本次请求隔离授权结果，且后续 M2 AC-28 需要请求标识和结果可恢复。该模型不表示 M1 已实现异步或自动恢复。

| 字段 | 用途 | 约束 |
|---|---|---|
| request_uuid | 稳定请求关联键 | 服务端生成、唯一；非授权凭证 |
| owner_id | 发起用户 | 服务端由当前环境写入；不可由 Mapping 改写 |
| thread_id、input_message_id | 聊天来源 | 若调用来自聊天，保存经授权确认的上下文；非聊天内部调用允许为空，具体 ACL 待运行时验证 |
| source_attachment_id | 源模板 | 必须属于本次用户可访问的消息/线程 |
| output_attachment_id | 成功结果 | 仅验证和保存成功后设置；一请求最多一个有效输出 |
| state、error_code、failed_stage | 可见状态/稳定诊断 | 仅映射 SRS 状态；不新增业务状态语义 |
| input_sha256、output_sha256 | 文件身份和一致性校验 | 不存文件原文；留存期限按 OPEN-OFFICE-12 |
| started_at、finished_at | 请求时序 | UTC |

只建立实现查找必需的 request_uuid 唯一约束。其他索引以实际查询计划为依据再加。首期不添加 queue_job_id、retry_count、channel、progress_percent、cancel_requested、worker lease 或持久 Mapping Plan 字段。Mapping Plan 是否需要短时保存，取决于 M1 确认流程澄清；默认仅在受控请求内存中处理。

### 5.2 状态映射

| 技术状态 | SRS 状态语义 | 说明 |
|---|---|---|
| accepted | 已接收 | 请求和输入附件关系通过初步校验 |
| validating | 检查中 | 格式、安全和映射校验 |
| processing | 处理中 | 同步解析/渲染/回读 |
| generated | 已生成 | 私有结果附件提交成功 |
| failed | 失败 | 不存在可下载的成功结果 |

M1 不实现异步取消、自动恢复、后台重试或进度百分比。刷新后可以按 request_uuid 查询已提交状态/结果；同步调用在执行途中失去连接后的继续运行与状态恢复由 M2 AC-28 方案处理，M1 不声称具备。

## 6 同步生命周期与事务边界

### 6.1 请求阶段

1. **短事务 A — 建立请求与授权。** 按当前用户校验 thread/message/source attachment 关系和 ACL；创建 request_uuid 及 accepted 状态，记录源附件身份元数据。提交后不持有行锁进入文件处理。
2. **受控输入快照。** 通过 Odoo 授权的附件存储边界取得本次文件字节、校验大小与源指纹。不得接受客户端路径或绕过附件访问服务。附件存储读若无法在关闭/结束 DB 事务后安全完成，必须先验证 Odoo 支持的存储 adapter；不得假装“短事务”消除了事务外部 I/O。
3. **事务外同步处理。** 在请求专属临时目录内检查文件容器、解析结构、验证 Mapping Plan、执行允许写入、回读结果。不得持有业务记录锁；子进程/转换器有硬超时、资源限制和可清理边界。处理不访问业务模型或 Provider。
4. **短事务 B — 交付前重验。** 重新核实 owner、thread、消息、输入附件是否仍有效且可访问，输入身份未变，调用方确认上下文仍然有效。创建私有输出 attachment，关联 request，设置 generated；完成提交前不能暴露下载能力。
5. **失败路径。** 任一阶段失败，删除临时输出和转换 profile；用短事务将请求标为 failed、清除输出关联，返回稳定错误且不给出下载链接。若附件创建失败或事务回滚遗留存储文件，调用 Odoo 支持的附件清理能力并记录清理状态，不直接删除未知服务器路径。

该流程是待 Odoo Runtime 验证的设计，不是 TV 已证明的事实。标准 ir.attachment 的存储后端可能在记录创建/读取时执行 filestore I/O；实现 Spike 必须核实它与工程规则 T-TRX-002 的适用边界、回滚/孤儿清理语义和 Odoo API 支持。不得使用手动 commit 后继续访问旧 env/recordset，不得使用 sudo 访问用户附件，也不得为规避 Queue Job 而在 ORM 事务中运行长文件处理。

### 6.2 锁与幂等

- Office 子进程、格式转换和回读不跨越排他锁或业务记录锁。
- 同一 request_uuid 不得有多个有效 output_attachment_id；重复到达时读取该请求当前状态，不重新生成。
- M1 不执行自动重试。失败后用户发起新请求，新的请求 ID 与附件关联隔离。
- 附件创建成功但记录提交失败的补偿行为必须由 Odoo 集成测试确认；不可凭 ORM 事务回滚推断 filestore 已回滚。

## 7 安全、资源限制与错误处理

### 7.1 安全强制规则

1. 以当前用户环境验证消息、线程、附件和结果授权；附件 ID 不能取代 ACL/Record Rule，不用 sudo 扩大访问。
2. 同时检查声明扩展名、MIME、签名、ZIP/OLE 容器和必要部件；任何不一致、加密、损坏或未知活动结构按格式策略拒绝。
3. ZIP 检查限制条目数、单项/总体展开量、路径和 CRC/XML 读取；禁止无界 extractall。该包装层能力尚未由恶意文件完整覆盖。
4. 不执行宏、脚本、外链更新、嵌入代码；禁止来自输入的路径、命令行、动态代码或 LibreOffice profile。
5. 原模板只读；每次输出使用隔离临时目录及隔离 profile；失败与超时杀死处理子进程组并清理。
6. 输出在创建/关联附件前须完整通过解析、目标值、公式和预登记结构回读；不能以打开成功或转换成功代替验证。
7. 聊天适配在 Provider 之前处理 Office 附件；任何 Provider payload 不得包含 Office 二进制。适配 Spike 未通过前，聊天路径不得开放 Office 处理。

### 7.2 同步资源上限

| 资源 | 控制方式 | 阈值来源/缺口 |
|---|---|---|
| 输入文件大小、ZIP/OLE 元素数及展开字节 | 预检并有界读取 | OPEN-OFFICE-05，目标部署实测确定 |
| 工作表/单元格、段落/表格、图片/对象数量 | 格式解析器在遍历时计数并超过上限停止 | OPEN-OFFICE-05，代表性模板确定 |
| 单请求墙钟时间 | 服务端截止时间；子进程超时后终止整个进程组 | 对照 Odoo Worker 和代理时限；当前未取得 |
| 内存/CPU/并发 | 独立处理进程资源限制；首期限制同步并发 | 目标运行时测量；不能以 macOS 合成样本外推 |
| 临时磁盘 | 每请求独立目录、容量限额、完成/失败清理 | 部署盘空间及 OPEN-OFFICE-12 |
| Worker 占用 | 仅接收预算内请求；控制单用户/全局同步处理数 | 目标 Worker 数、软硬内存及请求时限待确认 |

**超预算行为：** 可在预检识别的超限输入立即拒绝并指出超限类别；运行中达到硬限制则终止、清理、标失败。M1 不排队等待资源或自动升级为异步任务。目标环境未确定有效阈值时，不开放对应格式生产处理。

### 7.3 稳定错误类别

| 错误码 | 含义 | 输出规则 |
|---|---|---|
| OFFICE_INVALID_OR_MISMATCHED | 容器无效、扩展名/MIME/签名不一致 | 无输出；提示格式错误 |
| OFFICE_UNSUPPORTED_FEATURE | 当前格式/结构不在能力清单 | 无输出；指出可理解的对象类别 |
| OFFICE_RESOURCE_LIMIT | 文件、结构、内存或时限超预算 | 终止并清理；不返回部分文件 |
| OFFICE_MAPPING_INVALID | 缺字段、类型错误、null 不支持、目标不存在/只读 | 不启动或停止渲染；返回字段/元素级校验错误 |
| OFFICE_INTEGRITY_FAILED | 公式、结构、目标值或输出格式回读不一致 | 无预览/下载 |
| OFFICE_ENGINE_FAILED | 解析器/转换器异常或非零退出 | 记录脱敏阶段诊断，用户收到处理失败 |
| OFFICE_DELIVERY_FAILED | 输出附件创建、提交或授权失败 | 不返回链接，执行清理/补偿 |

普通用户错误不得包含 traceback、文件系统绝对路径、其他用户附件 ID 或业务内容；内部记录只保留 request_uuid、格式、阶段、库版本、错误类别、耗时/资源与清理结果。

## 8 测试与需求追踪

### 8.1 验证原则

TV 报告只证明直接测量的库/运行行为，不替代 Odoo 用户权限、聊天附件路由、Mapping 校验、事务、附件提交和浏览器验收。TDD 可在 TV 总体 Partial 时进行评审；对未验证的格式采用关闭/拒绝策略，不要求把所有 TV 或 Queue Job 生产容量测试作为整个 TDD 的冻结前置。

### 8.2 M1 实现验收矩阵

| TEST | 需求 | Given / When / Then | 当前证据 | 实施证据状态 |
|---|---|---|---|---|
| TEST-OFFICE-001 | FR-M1-001 / AC-01 | 有权用户附加纳入格式并提交；附件与正确用户/线程/消息关联，状态可查 | 聊天附件关联仅静态确认 | Missing |
| TEST-OFFICE-002 | FR-M1-002 / AC-02、AC-07 | 空、伪装、损坏、加密、宏/活动内容；格式预检拒绝，不送 Provider/渲染器 | 部分合成异常可捕获；LO 对伪装文件可返回成功 | Missing |
| TEST-OFFICE-003 | FR-M1-003 / AC-03 | 受支持 XLSX 含多表、公式和合并；结构读取返回稳定元素及未知项 | 合成及真实 XLSX 有局部库级证据 | Missing |
| TEST-OFFICE-004 | FR-M1-003 / AC-04 | 受支持 DOCX 含段落/表格；读取保留顺序和层级 | TARGET 结构检查，不是 Odoo 运行时 | Missing |
| TEST-OFFICE-005 | FR-M1-004/007 / AC-05、AC-09 | 合法/缺失/null/空串/错类型/未知键/目标/公式目标；只允许通过映射渲染 | 无功能实现证据 | Missing |
| TEST-OFFICE-006 | FR-M1-005 / AC-06、AC-23 | XLSX 非公式目标写入；公式表达式、目标值、结构回读正确；缓存状态独立报告 | P0-B openpyxl 3.0.9 清空 89 缓存并丢扩展 | Missing |
| TEST-OFFICE-007 | FR-M1-005 / AC-29 | 声明支持范围内 XLS；公式、样式、合并和输出回读通过，否则拒绝 | 仅合成 XLS 转换；无真实 XLS 写回 | Missing |
| TEST-OFFICE-008 | FR-M1-006 / AC-08、AC-30 | 声明支持范围内 DOC/DOCX；结构和版式验证通过，否则拒绝 | P0-A 普通段落 Partial；TARGET 无文本框/VML | Missing |
| TEST-OFFICE-009 | FR-M1-008 / AC-10、AC-17、AC-31 | 成功、失败、升级格式及跨用户下载；只交付本次授权附件 | 无 Odoo ACL/附件交付运行证据 | Missing |
| TEST-OFFICE-010 | FR-M1-009 / AC-23 | 预览/最终输出；每次共享后端回读，任一差异均不交付 | 独立副本行为，不是产品功能 | Missing |
| TEST-OFFICE-011 | NFR-OFFICE-02/08 | 压缩膨胀、路径穿越、结构超限、资源超限；有界拒绝并清理 | 限额包装脚本局部通过；解析器全边界未测 | Missing |
| TEST-OFFICE-012 | NFR-OFFICE-11 / T-TRX-002 | 同步处理慢文件；处理阶段无业务锁，事务边界和附件存储副作用符合获批策略 | 未测试 Odoo 事务/filestore 组合 | Missing |
| TEST-OFFICE-013 | FR-M1-008 / ORM-DATA-001 | 同一请求重复提交；仅一条请求和一个有效结果附件 | 未测试业务幂等 | Missing |
| TEST-OFFICE-014 | NFR-OFFICE-06 | 文件名/解析器异常含内部信息；用户错误脱敏，内部诊断可关联 request | 未测产品错误层 | Missing |
| TEST-OFFICE-015 | 聊天安全边界 | Office 消息在 Provider 前拦截并进入受控工具；任一 Provider 请求不含 Office 二进制 | 静态源码有限，无真实 payload 验证 | Missing |
| TEST-OFFICE-016 | NFR-OFFICE-12 / AC-28（M2 gate） | 超交互时限、刷新/恢复；状态和唯一附件可恢复，异步策略通过 M2 验收 | Queue Job 本机只读 PASS；Office/生产 INCONCLUSIVE | Deferred to M2; not an M1 sync test |

### 8.3 需求追踪摘要

| SRS 编号 | TDD 位置/测试 | 说明 |
|---|---|---|
| FR-M1-001—003 | §§2、3、5、8 / TEST-001—004 | 附件上下文、格式识别、结构读取 |
| FR-M1-004/007 | §3 / TEST-005 | 受控渲染与映射结构/类型/目标验证；业务 Mapping 作者待澄清 |
| FR-M1-005/006 | §4、8 / TEST-006—008 | 四种格式分别按声明能力范围保护；TV Partial 不等于通过 |
| FR-M1-008/009 | §§3、5—8 / TEST-009、010、013 | 新附件、授权、状态、失败语义和强制回读 |
| NFR-OFFICE-01/02/03/04/06/08 | §§4、6、7 / TEST-001/002/005—011/014 | 权限、容器安全、数据最小化、完整性、资源与错误 |
| NFR-OFFICE-11 | §6 / TEST-012 | 快照有效性和无长业务锁；需 Odoo Runtime 验证 |
| NFR-OFFICE-12 / AC-28 | §§2、5、8 / TEST-016 | AC-28 在 SRS M2 gate；M1 API 保持可独立调度，不声称满足长请求恢复 |
| AC-01—AC-10、AC-17、AC-23、AC-29—AC-31 | TEST-001—015 | M1 功能门禁；所有产品运行证据仍 Missing |

SRS 其他 M2/M3/M4 功能和验收不由本 TDD实现；M2 必须另外追踪 AC-11—16、AC-18—28 与其权限/映射/异步语义。

## 9 部署前置与启用条件

| 条件 | 用途 | 当前状态/门禁 |
|---|---|---|
| Odoo 18 目标补丁版、Python、PostgreSQL、Worker/代理预算 | 确定同步安全预算和 Runtime 行为 | 未完整记录；生产同步处理启用前确认 |
| Office 包及系统工具精确版本/许可证 | 锁定每个格式的引擎 | 未选型，不得安装/部署推定版本 |
| .xlsx/.docx 依赖在目标 Odoo venv 的验证 | 确认本地TV库行为适用于运行时 | P0-A 使用 workspace Python 3.12.14/python-docx 1.2；项目 venv 无 python-docx；P0-B openpyxl 3.0.9 低于计划候选 |
| LibreOffice 稳定版、隔离 profile、字体 | 仅适用于获批转换/重算路径 | 当前 Alpha、字体视觉不确定；旧格式转换保持关闭 |
| 目标格式样本与结构 capability 清单 | 确认实际可读写/回读边界 | 各种格式仍有样本缺口，按第 4 章分别启用 |
| 容量、展开量、时限、内存和同步并发上限 | 防止 Worker 无界占用 | OPEN-OFFICE-05；缺失时对应格式不得生产启用 |
| 临时/结果附件保留和删除规则 | 限制业务数据留存 | OPEN-OFFICE-12；生产交付前确定 |
| 聊天 Provider 前安全路由 | 不将 Office 二进制外发 | 扩展 Spike 未通过；聊天适配不得开放 |

P0-C 的 Queue Job 生产容量、prefork/websocket 反代和 Office 负载不属于同步 M1 上线前置；如后续采用队列，则作为异步增强的单独部署门禁。同步 M1 仍需按目标 Odoo worker/HTTP 限制定安全阈值。

## 10 待决事项分级与责任

本表是 TDD 的唯一待决事项清单。历史 TV 事实见第 1/4/9 章，不在此复述测试细节。

| 类别 | 事项 | 责任 | 依据 | 阻塞范围 | 处理阶段 |
|---|---|---|---|---|---|
| A 核心设计冻结前 | M1 Mapping JSON 的终端提供者、人工确认入口及 null 是否仅拒绝 | 业务负责人 + TDD 技术负责人 | FR-M1-004/007、AC-05/09、BR-OFFICE-03/08 | 阻塞聊天端到端 render 交互/全 M1 业务契约；不阻塞内部 schema 设计 | 正式 TDD 冻结前说明调用方；如 SRS 不足则提出最小 SRS 澄清 |
| A 核心设计冻结前 | llm_thread Office MIME 拒绝前的独立 Addon 安全路由是否可实现 | 技术负责人 | FR-M1-001；NFR-OFFICE-01/03；源码调查 §3/5 | 阻塞聊天适配和其 Addon 依赖；不阻塞 Provider-neutral 核心服务 | Spike 后决定物理模块布局；不修改官方源码 |
| A 核心设计冻结前 | Odoo attachment storage 的读取/写入、副作用、事务和回滚边界 | 技术负责人/Odoo Runtime 验证人 | T-TRX-002、FR-M1-008/009、NFR-OFFICE-11 | 阻塞附件持久化/交付实现；不阻塞纯文件服务契约 | 正式冻结/创建持久层 CC 前进行 Odoo Runtime Spike |
| B 特定格式开放前 | XLSX 写回引擎、扩展 OOXML 拒绝边界、缓存语义 | Office 技术负责人 + 样本提供方 | OPEN-OFFICE-03/06/14；P0-B PARTIAL | 只阻塞未通过的 XLSX 写入特征；不阻塞架构评审或 Queue Job | 格式 adapter 选型与目标环境验证前 |
| B 特定格式开放前 | DOCX 目标运行时依赖、CJK 版式和高级对象边界 | Office 技术负责人 + 样本提供方 | OPEN-OFFICE-04/06/14；P0-A PARTIAL | 只阻塞未通过的 DOCX 特征 | 开放该结构/生产格式前 |
| B 特定格式开放前 | 真实 XLS 样本、公式/样式、稳定版转换和回读 | Office 技术负责人 + 业务样本负责人 | OPEN-OFFICE-03/06/14；原始 TV 合成结果 | 阻塞 XLS 的读写开放；不阻塞其他格式的核心设计 | XLS capability 打开前；若不能满足需求走 SRS 变更 |
| B 特定格式开放前 | 真实 DOC 样本、版式/占位内容、VML 和转换链路 | Office 技术负责人 + 业务样本负责人 | OPEN-OFFICE-03/04/06/14；原始 TV 合成结果 | 阻塞 DOC 的读写开放；不阻塞其他格式的核心设计 | DOC capability 打开前；若不能满足需求走 SRS 变更 |
| B 生产开放前 | 各启用格式的大小/结构/耗时/内存限值及临时文件保留 | 部署负责人 + 数据负责人 | OPEN-OFFICE-05/12；NFR-OFFICE-08 | 阻塞生产启用相应处理路径，不阻塞 TDD 技术评审 | 目标环境上线门禁 |
| C 异步阶段 | 超过同步预算的状态恢复、后台调度、失败恢复和并发 | M2 技术负责人 + 产品负责人 | NFR-OFFICE-12、AC-28；SRS 将 AC-28 列入 M2 gate | 不阻塞 M1 同步核心；阻塞 M2 AC-28 验收 | 同步 M1 验收后、M2 验收前设计并验证 |
| C 队列选型/容量 | queue_job prefork、websocket、Office 负载、全进程 RSS 与生产容量 | 平台/部署负责人 | P0-C 本机 PASS、生产预算 INCONCLUSIVE | 不阻塞 M1；只有选择 Queue Job 时阻塞该异步部署 | 异步增强选型及生产启用前 |

### 10.1 最小 SRS 澄清问题

若业务负责人无法从冻结 SRS 给出映射提供方和确认入口，应提交一条最小 SRS 澄清：**M1 是否只提供内部受控渲染接口，还是必须在 M1 聊天 UI 中允许用户创建/编辑/确认 Mapping JSON？** 不得以 TDD 增加 UI、调用 LLM 或引入 Skill 来代替该决策。

## 11 技术决策、风险与冻结门禁

### 11.1 技术决策记录

| 编号 | 决策 | 依据和边界 | 状态 |
|---|---|---|---|
| TD-001 | Office 核心服务与聊天适配保持逻辑分离；物理 Addon 是否拆分由扩展 Spike 决定 | 避免 Provider 与文件引擎耦合；不得修改官方源码 | Logical boundary decided; package open |
| TD-002 | Office 二进制必须在任何 Provider 调用之前被路由/拒绝 | 现有 Office MIME 路径拒绝；其他 Provider 未完整检查 | Open; blocks chat adapter |
| TD-003 | 不以 openpyxl 3.0.9 作为真实 XLSX 通用写回引擎 | P0-B 真实样本清空公式缓存并丢失不支持扩展；替代引擎未验证 | Open; per-feature gate |
| TD-004 | 不将 python-docx 1.2.0 的单样本结果外推为生产选型 | 目标 venv 无依赖；计划候选 1.1.x 未测；高级对象未覆盖 | Open; DOCX capability gate |
| TD-005 | 不将 LibreOffice Alpha 的旧格式往返作为生产支持依据 | 无真实 XLS/DOC；样式与对象结构存在变化 | Open; .xls/.doc gate |
| TD-006 | 公式表达式必须保持；公式计算/缓存刷新不作承诺 | SRS FR-M1-005；P0-B 的 89/89 缓存丢失事实和 Alpha 限制 | 表达式保护确定；缓存策略依 OPEN-OFFICE-03 |
| TD-007 | Mapping Plan V1 为显式值、结构目标和单一 set_value 操作；M1 不推断业务来源 | FR-M1-004/007；缺失/null/类型/目标必须区分 | Schema candidate; caller UX open |
| TD-008 | **首期同步执行；异步增强延期至同步核心验收后。Queue Job 不作核心前置。** 超预算同步请求明确拒绝；服务接口保持可异步调度 | 用户确认方向；SRS AC-28 在 M2 gate。P0-C 本机 Queue Job PASS、生产预算 INCONCLUSIVE | 已确定；异步设计另阶段处理 |
| TD-009 | 文件处理阶段不得持有业务记录锁；附件检查/结果创建使用短 Odoo 事务边界 | NFR-OFFICE-11 与 T-TRX-002；附件 storage side effects 未作 Runtime 验证 | 生命周期候选；Odoo Runtime Spike 前不实施 |
| TD-010 | 容量、时间和临时附件保留阈值必须来自目标环境/业务决策 | OPEN-OFFICE-05/12 | 数值待决；不阻塞服务接口评审，阻塞生产开放 |
| TD-011 | 保留最小持久请求记录作用户/消息/输入/输出/状态的授权关联；不添加队列调度字段 | FR-M1-001/008、AC-10/17；后续 AC-28 需请求关联 | 设计建议；确认数据留存和 ORM ACL 后冻结 |
| TD-012 | 默认输出格式等于输入；升级只可在明确告知及用户确认后进行 | SRS FR-M1-008、AC-31 | 业务规则已确定 |

### 11.2 风险登记

| 风险 | 状态 | 控制/关闭条件 |
|---|---|---|
| 未知 OOXML 扩展在保存时静默丢失 | 已有真实样本证据 | 解析并识别能力外对象；不确定即拒绝；每种写入路径跑结构回读 |
| 公式缓存失效或旧格式公式语义变化 | OPEN | 分别测试公式文本与缓存；不声称重算；按 SRS 澄清处理缓存依赖 |
| Word 文本框/VML/修订/域在转换或保存中改变 | 未验证 | 逐类样本；不支持即拒绝；不得宣称格式整体无损 |
| 处理进程超时/OOM/孤儿残留 | 部分观测不足 | 同步硬预算、子进程组终止和目标环境观测；预算缺失不开生产 |
| 聊天附件误送至 Provider | 静态源码显示拒绝点；安全扩展未验证 | Provider 前路由 Spike 和每 Provider payload 测试；不绕过拒绝点 |
| Odoo 事务与 filestore 副作用不一致 | 未验证 | Runtime 验证标准附件 API 的提交/回滚/清理；不直接操作任意路径 |
| M1 sync flow 被误认为满足 AC-28 | 可预见范围误读 | 标明 AC-28 为 M2 gate；M1 超预算拒绝，不声称长任务恢复 |

### 11.3 正式评审/冻结门禁

**可以开始 TDD 正式评审；TV 总体 Partial 本身不阻止评审。** 冻结应按范围处置：

1. 同步核心服务、Mapping schema/validation、有限能力和拒绝策略、状态模型与同步资源边界须在评审中确认。
2. Mapping Plan 终端提供者/确认入口应得到最小业务决策；若涉及 SRS 语义不清，先提交 SRS 澄清，不由实现方猜测。
3. 聊天适配路径未通过 Provider 前路由 Spike 时，可把 TDD 中核心服务范围作为可评审设计；不得冻结一个未经证实的聊天适配实现承诺。
4. 附件事务生命周期的 Odoo Runtime Spike 是附件持久化实施门禁。若证据显示无法满足 T-TRX-002，先解决技术/规范冲突，不以 Queue Job 自动替代。
5. TV 为 Partial 可通过逐格式 capability gate 管理；没有证据的格式/结构关闭且拒绝。相关格式写入在目标库/目标环境验证前不得启用；M1 SRS 阶段验收仍需满足其格式验收门禁。
6. Queue Job 生产容量不是 M1 同步核心 TDD 的冻结门禁；异步选择时再补生产拓扑、负载、RSS、代理与恢复验证。
7. TDD 冻结后仍须另行评审并基线化 Implementation Plan；其后才可建立 CC。任何 Draft 文件均不得作为编码授权。

## 附录 A 缩略语与测试状态

| 术语 | 含义 |
|---|---|
| Mapping Plan | 目标结构元素、允许操作及显式值组成的受控输入；不包含业务查询或可执行代码 |
| 公式表达式 | Office 文件中的公式文本，与其缓存计算值分开 |
| 能力清单 | 服务端按格式声明的、已实现且通过证据的可读取/写入/回读元素集合 |
| 同步核心 | 当前调用方等待同一服务调用完成；不使用后台队列调度 |
| Missing / Deferred | 尚无产品实现证据；Deferred 明确分配给后续里程碑 |

P0 原始状态快照：

| 项目 | 保留状态 | 对本 TDD 的使用 |
|---|---|---|
| M1 TV 总体 | Partial | 不宣称 M1 技术验证完成 |
| P0-A DOCX | Partial | 普通段落单样本有局部结构证据；目标 venv/候选版本、中文视觉、高级对象未验证 |
| P0-B XLSX | Partial | openpyxl 3.0.9 的公式缓存清空及 OOXML 扩展损失为真实样本证据；LibreOffice Alpha 视觉/样式不确定 |
| P0-C Queue Job | 本机只读任务链路 PASS；生产预算 INCONCLUSIVE | 只作为以后选 Queue Job 的输入，不决定同步核心是否可设计/开发 |

## 附录 B 版本记录

| 版本 | 日期 | 状态 | 变更 |
|---|---|---|---|
| V0.1 | 2026-10-19 | Draft — Not Approved for Implementation | 原始综合草案；副本保留于 TDD_office_engine_m1_v0.1.md |
| V0.2 | 2026-10-19 | Draft — Not Approved for Implementation | 确定 M1 同步核心、异步后置及 TD-008；分级待决项；澄清 Mapping Plan 调用方边界；重评模块/请求模型；定义同步事务生命周期；建立四格式证据矩阵和范围化冻结门禁 |

