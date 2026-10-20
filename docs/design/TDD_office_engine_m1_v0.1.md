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
| 范围 | Office 引擎底座（M1） |
| 文档版本 | V0.1 |
| 状态 | **DRAFT — NOT APPROVED FOR IMPLEMENTATION** |
| 起草日期 | 2026-10-19 |
| 技术负责人 | 待指定 |
| 上游 SRS | Odoo 通用 Office 文档自动化引擎 SRS V1.0.0 Frozen |
| 上游 DDD | 未发现 Office Engine DDD；适用性判断尚未记录 |
| TV 基线 | TV Plan V1.0.0 Frozen；原始报告 V0.1 Partial；P0 补验报告 V0.4 |

> 本文只定义 M1 的技术设计候选与门禁。尚未作出最终 Office 库、旧版格式转换、聊天接入和异步部署决策；本文不是编码授权，也不是实施基线。

## 0 文档说明

### 0.1 文档定位

本文将冻结 SRS 映射到 M1 的技术组件、接口、文件安全策略、输出校验、运行时状态、测试与实现防护栏。M1 提供 Office 文件接收、结构读取、受控写入、回读验证、失败处理和附件交付；不实现 AI 语义映射、Odoo 业务记录查询、Skill 或企业治理。

### 0.2 上游基线及证据

| 材料 | 版本 / 状态 | 本 TDD 使用范围 |
|---|---|---|
| docs/requirement/SRS_office_document_automation.md | V1.0.0 Frozen，基线日期 2026-10-19 | M1 范围、FR、BR、NFR、AC、CFG 和 OPEN 项的唯一需求来源 |
| docs/verification/TV_Office_Engine_M1_Plan.md | V1.0.0 Frozen | TV 方法、候选版本范围和安全验证标准 |
| docs/verification/TV_Office_Engine_M1_Report.md | V0.1 Partial | 合成样本及当前开发环境的基础 TV 证据 |
| docs/verification/evidence/TV_Office_Engine_M1/P0_Followup/P0_Followup_Report_v0.2.md | V0.2，P0-B Partial | 真实 XLSX 样本、公式缓存、OOXML 和样式差异 |
| docs/verification/evidence/TV_Office_Engine_M1/P0_Followup/P0_Followup_Report_v0.3.md | V0.3，队列本机链路 Pass、生产预算 Inconclusive | queue_job 开发环境运行证据和生产限制 |
| docs/verification/evidence/TV_Office_Engine_M1/P0_Followup/P0_Followup_Report_v0.4.md | V0.4，P0-A Partial | 用户指定 DOCX 的隔离读写和结构回读 |
| docs/verification/evidence/TV_Office_Engine_M1/P0_Followup/P0_Xlsx_Results_20261019_RealSample.json | P0-B 结构化证据 | 真实工作簿各对象、缓存和结构差异 |
| docs/verification/evidence/TV_Office_Engine_M1/P0_Followup/P0_Docx_Results_20261019_TARGET.json | P0-A 结构化证据 | TARGET.docx 样本范围、包差异和视觉限制 |
| docs/verification/evidence/TV_Office_Engine_M1/P0_Followup/P0_QueueJob_Runtime_20261019.json | P0-C 结构化证据 | queue_job 本机任务及生产部署限制 |
| docs/analysis/office_automation_source_review.md | 2026-10-19 源码调查 Draft | 当前 Odoo-LLM 附件、工具与 Provider 扩展现状；静态调查不代替运行时验证 |

不得将上述 Partial、Inconclusive、未运行或缺样本结果改写为通过。冻结 SRS 和 TV Plan 不在本 TDD 中修改。

### 0.3 DDD 适用性

仓库已检查路径中未发现 Office Engine 的 DDD。SRS 元信息仅称 DDD/TDD 尚未建立，不能据此推定 DDD 已获批为“不适用”。本草案按 SRS 直接组织 M1 技术设计，不创建 AGG、ENT、INV、DS 或 DV 编号；是否需要 DDD 仍须由项目负责人记录判断后，方可冻结 TDD。

### 0.4 本文范围与边界

| 属于本 TDD | 不属于本 TDD |
|---|---|
| M1 Office 类型识别、结构读取、受控填充、输出回读、附件交付及技术状态 | M2 Odoo 业务模型准入、记录读取、字段白名单、AI Mapping Plan 生成与语义确认 |
| M1 与 Odoo-LLM 聊天附件的安全接入边界 | M3 私有/公共 Skill 生命周期和审核 |
| M1 的 Office 处理候选库、旧格式策略、任务执行与资源限制 | M4 企业策略管理、白名单版本治理和审计产品界面 |
| M1 生成的映射载荷和服务接口候选 | V2 文件导入、业务记录写入、PDF/图片/PPT 处理 |

### 0.5 决策状态与规范措辞

“已确认”仅表示有 SRS 或 TV 直接依据；“暂定建议”表示此草案推荐但未获批准；“待决”表示证据不足或业务/技术负责人尚未决策。本文中的“必须/不得”只重述冻结 SRS 或组织工程准则，不表示当前代码已满足。所有技术选择待 TDD 评审批准后才能成为实施基线。

### 0.6 编号与单一事实来源

沿用组织 TDD 模板编号：T、ORM、SVC、ADPT、Q、API、UI、SEC、ERR、TEST、TD。新编号只用于本文件，不分配 DDD 领域编号。编号冻结后不重排。

| 实现事实 | 本文定义位置 |
|---|---|
| 运行平台和依赖 | 第 1 章 |
| 持久化请求模型候选 | 第 3、4 章 |
| 结构及渲染报文 | 第 5 章 |
| 服务行为 | 第 6 章 |
| LibreOffice 子进程边界 | 第 7 章 |
| 同步/异步选择条件 | 第 8 章 |
| 技术执行状态 | 第 9 章 |
| 事务、并发与幂等 | 第 10 章 |
| 错误和重试 | 第 11 章 |
| 权限及文件安全 | 第 12、18 章 |

其他章节通过编号引用，不重复定义规范规则。

## 1 技术上下文与基线

### 1.1 技术栈

| 层次 | 当前检查所得 | 对目标实现的含义 |
|---|---|---|
| Odoo | 项目为 Odoo 18 Community Edition | 具体补丁版/目标部署 commit 需在 TDD 冻结前记录 |
| Python | TV 使用项目 venv Python 3.11.9 | 目标服务器 Python 版本尚未确认 |
| PostgreSQL | TV 未记录精确版本 | 目标版本待部署负责人确认，不推断 |
| XLSX 库 | TV venv 为 openpyxl 3.0.9；Plan 候选 3.1.x | 不批准直接写回真实模板；3.1.x 尚未验证 |
| XLS 读取/写入 | TV venv 有 xlrd 1.2.0、xlwt 1.3.0 | 读取/写回及样式保留不能由版本存在推定；xlrd 仅作读取探底 |
| DOCX 库 | P0-A 使用工作区 Python 3.12.14、python-docx 1.2.0；Odoo venv 未安装 | 计划候选 1.1.x 未测；目标 venv 集成未验证 |
| OOXML/XML | P0-A 使用 lxml 6.1.1 | 不是已选依赖；是否纳入生产依赖待批准 |
| LibreOffice | TV 使用 LibreOfficeDev 26.8.0.0.alpha0 | Alpha 不是生产稳定版或目标 OS 证据，不得作为生产选型已验证事实 |
| 后台队列 | OCA queue_job 18.0.3.1.3；开发库 workers=0 下两条只读任务完成 | 生产 prefork、Office 负载、总进程树 RSS 和预算均未验证 |
| 聊天宿主 | odoo-llm 分支 18.0，commit 609ec6dda3645165f6a4a843d7af5d286081a29d；检查时工作树另有未提交改动 | Commit 不是该次调查的完整工作树快照；实现前须重新确认上游差异 |

TV 主机为 macOS 27.0.1 arm64，16 GiB 内存；它不是目标生产环境。当前 odoo.conf 的 workers=0、8091 直连及 queue_job 配置只作为本地开发运行事实，不写成生产配置。目标 OS、PostgreSQL、worker/代理时限和内存限额均为待确认变量。

### 1.2 依赖策略

| 依赖候选 | 类别 | 拟解决问题 | 状态 |
|---|---|---|---|
| Odoo base / mail | 平台模块 | 附件、消息、当前用户和聊天关系 | 现有能力已由源码静态确认；ACL/线程隔离仍须运行时验证 |
| llm_thread / llm_tool | 可选聊天接入模块 | 聊天动作与工具注册 | M1 核心不得依赖 Provider；安全扩展点尚待 Spike |
| openpyxl | Python 包 | OOXML 表格对象模型修改 | 不批准当前直接保存路径；候选版本及扩展对象风险未关闭 |
| python-docx | Python 包 | DOCX 常规段落/表格读写 | TARGET 样本在 1.2.0 上取得局部证据；目标运行时与 1.1.x 未验证 |
| LibreOffice | 系统进程 | 旧格式转换、可能的公式重算/渲染 | Alpha 样本部分可用但结构/样式差异、稳定版和生产隔离未确认 |
| xlrd / xlwt | Python 包 | XLS 读取/生成候选 | 不作为保真既有 XLS 工作簿的已确认方案 |
| queue_job | OCA 模块 | 候选异步执行器 | 开发环境链路通过；生产容量和运行拓扑未通过验证 |

依赖精确锁定、许可证审查、部署包及模块依赖写入属于实现准备；任何包不得在本 TDD 草案中被描述为已批准或要求现在安装。

### 1.3 SRS 非功能约束的技术落点

| SRS 条款 | 技术落点 |
|---|---|
| NFR-OFFICE-01/03 | 当前用户附件访问检查、最小化结构输出、避免日志/Provider 中出现不必要文件内容 |
| NFR-OFFICE-02 | 扩展名与文件签名/容器联合判别、加密/损坏拒绝、无宏/脚本执行 |
| NFR-OFFICE-04 | 所有渲染共用后端读回校验；每种格式单独定义可验证结构指纹 |
| NFR-OFFICE-06 | 面向用户的错误阶段与是否有输出明确区分，内部日志脱敏 |
| NFR-OFFICE-08 | 文件/结构/时间阈值由代表性测试确定；未定前不得作为生产开放准入 |
| NFR-OFFICE-11 | 不持有业务记录锁跨越长时文件处理；快照有效性在交付前复核的后续层职责 |
| NFR-OFFICE-12 | 不能依赖一次 HTTP SSE 始终连通；任务恢复与唯一输出的持久状态机制待运行预算决策 |

## 2 总体架构

### 2.1 组件边界

暂定建议采用两个依赖边界，而非把整个功能塞入一个与 AI Provider 耦合的 Addon：

1. **Office 引擎核心 Addon（模块技术名待评审，例如 wd_office_engine）**：只依赖 Odoo 附件/消息基础能力和经评审的 Office 运行库，负责文件准入、解析、映射载荷校验、渲染、回读、请求状态和结果附件。不得查询业务模型或调用 LLM。
2. **聊天接入 Addon（模块技术名待评审，例如 wd_office_engine_llm）**：可依赖 llm_thread/llm_tool，负责在聊天请求中识别已授权 Office 附件并路由到核心服务，显示状态和返回附件。必须证明 Office 原始二进制不会被任何 Provider 读取或发送；不得以放宽 unsupported attachment 检查代替安全路由。

拆分是为满足 SRS M1 不依赖 AI 映射/业务数据、同时使用 Odoo-LLM 聊天附件的边界。是否需要两个可安装模块、现有聊天能否安全扩展，仍是 TD-001/002 待决；在扩展点验证通过前，不得冻结目录和依赖。

### 2.2 M1 组件职责

| 组件 | 输入 / 输出 | 职责与边界 | 证据 / 风险 |
|---|---|---|---|
| 附件入口与权限检查 | 当前用户、线程消息、附件 ID → 已授权附件引用 | 校验附件确属当前用户可访问线程；禁止接受任意路径；不读业务记录 | llm_thread 可关联附件已静态确认；真实 ACL/跨用户场景未测 |
| Office 文件识别器 | 附件字节、文件名、MIME → 格式、容器类型、准入结论 | 同时判断扩展名、MIME、签名和必需容器部件；识别加密/损坏/不支持对象 | 异常样本仅有限测试，安全策略需完整重测 |
| 结构读取器 | 通过准入的只读文件副本 → 有结构标识的读取结果 | 读取工作表/单元格/公式/合并区，或段落/表格/层次；报告未识别对象，不推断业务映射 | XLSX、DOCX 有局部证据；旧格式和高级对象不完整 |
| Mapping Plan 校验器 | 文件指纹、解析元素目录、JSON → 已校验写入指令或位置错误 | 校验版本、目标存在、可写类型、操作许可、公式保护和缺失/空值区别 | 当前无现成 Mapping Plan 实现；契约见第 5 章草案 |
| 渲染执行器 | 原模板副本、已校验映射 → 候选新文件 | 每个任务独立临时目录，服务端确定输出名/路径，不覆盖原件 | 多个库行为存在风险；各格式引擎待决 |
| 输出回读器 | 候选输出及原模板摘要 → 通过/失败及差异 | 验证可解析性、格式、映射目标值、公式和预登记结构指纹 | 所有格式验证细节待 M1 TV 补齐 |
| 请求与结果交付 | 当前请求、校验结论 → 状态及新附件 | 仅在完整验证成功后创建并关联结果；刷新后可恢复状态的模型方案与异步策略相关 | NFR-OFFICE-12 要求；持久化/队列方案待决 |
| 临时资源管理 | 请求 ID → 受限临时目录/进程/文件 | 自动清理成功、失败、取消、超时后的临时文件和进程；无法确认清理时告警 | 全进程树及生产资源隔离未验证 |

M1 不创建通用文件框架，不引入与本期无关的插件系统、通用 ORM 抽象、缓存或消息总线。按格式拆分处理方法只有在选定实现库后证明必要时才建立。

### 2.3 模块目录候选

下列为实现组织建议，不表示已创建或批准。结构以 Odoo 原生 Manifest、模型、访问规则和测试为主：

<pre><code>wd_office_engine/
  __manifest__.py
  models/
  services/
  security/
  data/
  tests/

wd_office_engine_llm/     # 仅在安全聊天接入 Spike 证明需要时保留
  __manifest__.py
  models/
  data/
  tests/</code></pre>

不预设必须使用 adapters/、schemas/、queue/ 独立子框架；JSON Schema 和库调用可先留在核心模块的少量清晰文件中。

## 3 ORM 模型设计

### 3.1 模型映射候选

| 上游对象 | 来源 | ORM 模型候选 | 职责 | 决策状态 |
|---|---|---|---|---|
| 单次 Office 请求 | SRS FR-M1-001、008、009；NFR-OFFICE-06、12 | office.document.request | 记录发起用户、线程/消息、源附件、结果附件、格式、校验状态和错误码；不保存持久业务字段快照 | 暂定建议；与同步/异步决策绑定 |
| 原模板和生成文件 | SRS FR-M1-001、004、008 | ir.attachment | 存原模板和独立输出；遵守现有附件授权，不以附件 ID 作为访问令牌 | 复用现有模型；访问规则待运行时验证 |
| 工作队列 | SRS NFR-OFFICE-12（条件） | queue.job（若获准且生产配置通过） | 技术调度、重试和执行信息；请求业务状态仍由 request 记录权威表达 | 候选而非已选 |

若明确只支持短时同步且同步可满足目标超时、状态恢复和失败语义，可重新评估是否不新增请求模型。若需要刷新后状态恢复或异步，长期仅依赖 SSE 流不够，必须有持久请求标识和所有权校验。

### 3.2 office.document.request 字段候选

| 字段候选 | 类型 | 约束 / 权威关系 | 上游 |
|---|---|---|---|
| request_uuid | Char / UUID | 服务端生成、唯一；用于请求去重，不由模型或浏览器提供 | NFR-OFFICE-12、AC-28 |
| owner_id | Many2one(res.users) | 创建时绑定当前用户；不可由工具参数改写 | NFR-OFFICE-01、AC-10 |
| thread_id / input_message_id | Many2one | 仅保存已验证当前用户可访问的 Odoo 聊天上下文；适配模块是否使用尚待决 | FR-M1-001、008 |
| source_attachment_id | Many2one(ir.attachment) | 只读引用；请求开始及交付时验证附件和线程关系 | FR-M1-001、002 |
| output_attachment_id | Many2one(ir.attachment) | 仅验证通过且交付成功后写入；最多绑定本请求一个有效结果 | FR-M1-008、009 |
| input_format / output_format | Selection | 实际内容检测所得；默认输出与输入同格式，升级需用户确认 | FR-M1-008、AC-31 |
| input_sha256 / output_sha256 | Char | 文件完整性诊断，不包含原文；是否长期保留待保留策略决策 | FR-M1-009 |
| state | Selection | 仅使用 SRS 中适用于 M1 的“已接收/检查中/处理中/已生成/失败/已取消”语义；不得重定义 | SRS §7 |
| error_code / failed_stage | Char/Selection | 面向稳定错误分类，不存 traceback 或业务内容 | NFR-OFFICE-06 |
| started_at / finished_at | Datetime | 技术时序；时区按 Odoo UTC 存储规则 | NFR-OFFICE-12 |

Schema/Mapping 内容是否需要短期保存由异步决策决定。若须持久化，不得写入不受访问规则保护的队列参数或普通日志；必须在实现前批准访问、加密/脱敏、保留期限和清理失败策略。字段细节仍是评审候选，不是冻结 ORM 契约。

## 4 数据约束与索引

| 编号 | 对象 | 约束候选 | 来源 / 状态 |
|---|---|---|---|
| ORM-DATA-001 | office.document.request.request_uuid | 唯一约束，防重复创建同一请求标识 | NFR-OFFICE-12；暂定实现建议 |
| ORM-DATA-002 | office.document.request.output_attachment_id | 单请求最多有一个对用户交付的最终结果；具体并发控制和可重试覆盖策略待验证 | FR-M1-008、NFR-OFFICE-12；待决 |
| ORM-DATA-003 | office.document.request owner/thread/source 关系 | 所有权和附件关系由 ORM 校验与 Record Rule 共同保护，不依赖前端 | NFR-OFFICE-01；具体域待真实运行时验证 |

暂不增加基于模板内容、单元格值或业务数据的索引。ORM-DATA 不应只因“可能有用”而新增。

## 5 JSON / 报文 Schema

### 5.1 调用边界

SRS 的逻辑能力名为 read_office_to_text(attachment_id) 和 render_office_template(template_id, json_mapping)。服务接口必须把附件授权、格式检测和当前请求上下文绑定在 Odoo 端执行。附件 ID 是业务对象引用，不是授权凭证；服务器路径、任意模型名、业务记录 ID、Python 代码和宏命令不属于 M1 输入。

读取结果由核心服务返回给 Odoo 调用方。只有聊天适配层经单独审批并通过数据策略后，才能决定哪些提取内容进入 LLM 上下文；核心服务不得调用 Provider，也不得默认把整个文档文本发往 LLM。

### 5.2 Mapping Plan 最小候选

以下为待评审契约形状，避免引入复杂 DSL。M1 只处理经校验的目标位置和显式值，不包含 Odoo 模型/字段查询、Skill、可执行表达式或文件路径。Mapping Plan 仅针对已解析模板指纹有效：

<pre><code>{
  "schema_version": "1",
  "source_sha256": "&lt;服务端检测的输入指纹&gt;",
  "writes": [
    {
      "target": {"element_id": "xlsx:Sheet1!A1"},
      "operation": "set_value",
      "value": {"type": "string", "data": "示例文本"}
    }
  ]
}</code></pre>

约束候选：

- element_id 必须来自同一输入文件的结构读取结果；不可由映射内容自行创造新坐标。
- XLSX/XLS 的解析元素可表示工作表与单元格地址；DOCX/DOC 使用服务端生成的段落/表格层级元素标识。DOCX/DOC 的定位稳定性尚无完整证据。
- operation 仅允许经过格式引擎白名单验证的值写入动作；不允许公式、宏、字段代码、外部链接、文件路径或任意转换脚本。
- value 必须存在，且显式携带类型；遗漏、显式 null、空字符串、零值和类型错误必须分别校验。当前是否允许 null 清空目标单元格/段落尚未由 SRS 明确，故在决策前拒绝 null 写入。
- formula cell 不是可写目标；尝试写入时返回稳定的目标冲突错误。
- Schema 版本不支持或 source_sha256 与当前模板不符时拒绝，不做自动猜测或迁移。

M2 若需要从 Odoo 字段取值，应另行扩展并评审版本化 Mapping Plan；M1 不定义模型/字段表达式，也不为未来 DSL 预留任意字段。

### 5.3 读取响应与渲染响应候选

读取响应至少区分 detected_format、source_sha256、elements、unsupported_elements、warnings 和 complete 标志。不得把未解析对象藏在完整文本摘要中。渲染响应至少包含 request_id、status、input_format、output_format、validation_summary、error（失败时）及通过授权校验后的 output_attachment_id。不能把输出文件字节、任意路径或访问令牌返回给模型。

稳定错误结构候选：

<pre><code>{
  "error": {
    "code": "OFFICE_OUTPUT_READBACK_FAILED",
    "stage": "readback",
    "retryable": false,
    "safe_message": "生成文件未通过完整性检查，未提供下载。"
  }
}</code></pre>

内部异常类型、traceback、服务器路径和原始文件文本不得放入用户可见字段。

## 6 领域行为实现

### 6.1 服务映射

| 上游行为 | 来源 | TDD 实现候选 | 事务 / 权限边界 |
|---|---|---|---|
| 接收并检查 Office 附件 | FR-M1-001/002 | attachment 入口检查 + 文件识别器 | 当前用户环境；检查附件及线程授权 |
| 结构读取 | FR-M1-003 | OfficeDocumentService.inspect/read | 只处理获准附件；报告未知对象 |
| Mapping 校验 | FR-M1-007 | MappingValidator.validate | 所有客户端/LLM 字段均视为不可信输入 |
| 生成模板副本 | FR-M1-004/005/006 | OfficeDocumentService.render_candidate | 原附件只读；临时路径由服务端创建 |
| 输出回读及交付 | FR-M1-008/009 | OutputVerifier + 请求完成动作 | 验证失败不创建或不关联成功输出 |

不建立访问 Odoo 业务记录的 Service。M2 的权限网关不属于此 M1 TDD。

### 6.2 处理伪代码契约

<pre><code>def process_request(request_id, current_user):
    request = load_request_as_owner(request_id, current_user)
    validate_source_attachment_and_thread(request, current_user)
    snapshot = read_authorized_attachment_bytes(request)
    detected = inspect_format_and_container(snapshot)
    require_supported_format_and_within_configured_limits(detected)
    structure = parse_in_isolated_workspace(detected)
    mapping = load_or_receive_mapping_for_same_source(request, structure)
    validated = validate_mapping(mapping, structure)
    candidate = render_to_new_temporary_file(snapshot, validated)
    verification = read_back_and_compare(candidate, structure, validated)
    if not verification.passed:
        discard_candidate_and_fail(request, verification.safe_error)
    recheck_request_owner_and_delivery_context(request, current_user)
    create_private_result_attachment_and_complete(request, candidate)
    cleanup_temporary_workspace_and_children(request)</code></pre>

伪代码描述顺序，不授权在普通请求中长时间保持 Odoo 事务或行锁。文件处理进程、事务切分和异步执行方案按第 8、10 章和 TD-008/009 评审。

## 7 外部服务与处理引擎

### 7.1 Adapter / 子进程契约

M1 不调用外部 LLM Provider 或业务 HTTP API。若最终选 LibreOffice，则它是本机处理子进程，不是已确认依赖。

| 编号 | 外部对象 | 超时 | 重试 | 失败处理 / 降级 | 状态 |
|---|---|---|---|---|---|
| ADPT-OFFICE-001 | LibreOffice headless 子进程 | 必须设置墙钟上限；具体秒数由 OPEN-OFFICE-05 及目标预算验证后确定；未配置时不得开放生产转换 | 默认不对格式/解析错误重试；仅进程启动或临时 I/O 类瞬时失败可评估一次有限重试 | 捕获退出码、stdout/stderr 摘要；终止整个进程组、清理 profile；不以退出码 0 或文件存在判成功 | 候选，未选型 |
| ADPT-OFFICE-002 | Python 文件解析库 | 进程级墙钟/资源限制待目标环境验证 | 非确定性解析错误不重试 | 捕获已分类异常；严重解析放独立子进程候选；资源限制未验证前不得声称不会影响 Worker | 实现位置与隔离方式待决 |

不调用网络时无需定义 HTTP 幂等键；文件任务幂等和单输出约束见 T-CONC-002。

### 7.2 各格式处理策略

| 格式 | 当前证据 | 本草案建议 | 未关闭风险 |
|---|---|---|---|
| .xlsx | 真实模板上 openpyxl 3.0.9 保留 89 个公式文本但清空全部缓存；同时移除扩展 OOXML 节点并移除 custom.xml。LibreOffice Alpha 恢复该样本缓存但样式属性变化广泛且未人工验收 | 不批准当前 openpyxl 直接保存用于任意真实模板；须比较经 TV 验证的稳定 LibreOffice、限定 OOXML 修改或其他兼容路径，逐项回读 | 3.1.x、目标 OS、公式缓存含义、扩展对象和视觉保真 |
| .docx | TARGET.docx 在 python-docx 1.2.0 隔离副本中普通段落写回通过，包部件/图片/关系/表格/页眉页脚数量未变；无文本框/VML。目标 venv 无 python-docx，CJK 视觉 Inconclusive | 暂只认为普通段落写回有局部证据，不承诺高级对象或目标运行时保真；按结构能力策略拒绝未验证对象 | 1.1.x/目标 venv、文本框/VML、字体/分页和大型文档 |
| .xls | 合成样本中 openpyxl 不能直接处理；xlrd 1.2.0 读取了表格/合并/样式索引但公式值为空；LibreOffice Alpha 简单往返可打开但 XF 样式记录变化 | xlrd 不作为写入引擎；LibreOffice 稳定版真实样本往返为候选，未通过前不得宣称旧版普遍保真 | 无真实 .xls 样本、复杂样式、公式/缓存和稳定版结果 |
| .doc | 合成旧格式往返中 VML shape 数量改变，文本虽可提取但对象实现改变 | LibreOffice 转换仅为候选，先按对象类型拒绝未验证结构；不得静默转为 .docx | 无真实 .doc、目标稳定版、版式/文本框/占位内容回转 |

本表不得用于静默缩减 SRS 的四格式范围。若代表性验证后无法满足冻结要求，先走 SRS 变更；TDD 不能自行把某纳入格式改为“不支持”。

### 7.3 回读校验分层

| 校验维度 | XLSX / XLS 检查候选 | DOCX / DOC 检查候选 | 判定边界 |
|---|---|---|---|
| 可成功打开 | ZIP/OLE 容器及必需结构、解析器重开 | ZIP/OLE 容器、必需部件、解析器重开 | 不能推断其余维度通过 |
| 映射目标值 | 读取目标地址并与已校验显式值比较 | 读取目标 element_id 并与显式值比较 | 缺值/空值按 schema 明确区别 |
| 公式表达式 | 工作表、坐标、公式文本摘要逐格比较；公式格不可写 | 不适用 | 公式文本保留不等于计算正确 |
| 公式缓存/重算 | 以 data_only/OOXML 缓存独立读取；如不支持则报告具体变化 | 不适用 | SRS 不承诺计算或刷新缓存；缓存风险尚属 OPEN-OFFICE-03 |
| 结构关系 | sheet 顺序、合并区域、行列布局、关系、图片、命名区和已声明样式 | 文本/表格顺序、sections、headers/footers、媒体关系、字段和高级对象计数 | 仅比较预登记且已声明支持的结构 |
| 视觉排版 | PDF/PNG 人工复核为补充 | PDF/PNG 人工复核为补充 | 文件可打开、XML相等或像素相似不能单独证明视觉保真 |
| 高级 OOXML / OLE 对象 | 按预登记对象指纹验证 | text box、VML、浮动对象、域、修订、嵌入对象等逐类核验 | 无代表样本/目标字体时为 Inconclusive |

输出验证采用“可解析 + 目标值 + 已声明结构指纹”联合条件。失败时丢弃候选文件，不显示预览、不创建可下载的成功附件。

## 8 异步队列、Worker 与执行预算

### 8.1 执行方式评估

SRS NFR-OFFICE-12 禁止依赖单一前端请求始终保持连接；NFR-OFFICE-08 未定义文件/时限阈值。当前 TV 对 50,000 行合成 XLSX 测得 Python 处理约 1.3888–2.1599 秒，但样本约 0.98 MB，进程 RSS 约 123–130 MiB，不能直接外推真实文件或 Odoo Worker；约 9.73 MB DOCX 仅做 ZIP/XML 检查，未测试 python-docx 完整读写。真实 Office 处理的生产预算仍 Inconclusive。

| 工作 | 暂定执行策略 | 依据 / 门槛 |
|---|---|---|
| 附件权限、格式签名和小型结构预检 | 可在请求中同步，但必须在已批准阈值内 | 阈值未定；实现前依 OPEN-OFFICE-05 完成目标环境测量 |
| 完整解析/渲染/转换/回读 | 对可能超出请求时限的工作须异步并有持久状态；当前不强制所有输入异步 | 具体同步门槛、队列产品与并发上限未决定 |
| LibreOffice 转换 | 若经稳定版/目标 OS 选入，优先隔离子进程；是否通过 queue_job 调度仍待决 | P0-C 只证明本机 threaded queue_job 只读链路 |

结论：**是否所有生成任务必须异步为 Inconclusive；不能选择“同步安全”或“queue_job 必须”的最终答案。** TDD 冻结前要取得目标 Odoo/反向代理 HTTP 时限、worker 数、CPU/内存软硬限制、并发目标、稳定版 Office 文件耗时/总进程 RSS。

### 8.2 Queue Job 候选

P0-C 已在现有 odoo18ce 开发环境以 Odoo ORM 安装 queue_job 18.0.3.1.3，并在 workers=0 下完成只读后台方法；创建到完成约 0.049 秒。此任务未处理 Office 文件。workers=2 试运行受当前浏览器 websocket 拓扑影响而回退 workers=0；生产 prefork、反向代理、Office 工作负载、子进程 RSS 和资源预算均未测。

因此 queue_job 仅是候选。若目标生产选择它，前置要求包括：目标 addons_path/server_wide_modules/workers/channels/runner host 及反向代理配置已核验；实际任务执行用户保留并再次校验；失败重试边界与请求幂等已实现；清理孤儿进程和临时文件有验证证据。不能把现有本机 PASS 当生产验收。

### 8.3 Job 可靠性与重试

文件结构错误、签名不符、加密、映射不合法、对象不支持和回读差异均不可自动重试。仅可对经过分类的短暂进程启动/临时文件系统错误评估有限重试；每次重试复用同一 request_uuid，成功附件只能提交一次。最大次数、退避、队列通道和死信处理须结合目标预算具体评审，当前不填造数值。

### 8.4 Cron / 可靠投递

M1 不需要业务定时任务。若异步任务在 Odoo 请求事务提交前投递，需保证请求记录与 Job 不会出现“用户看到已接收但任务丢失”；采用事务后入队、queue_job 集成保证或等价机制由实现 Spike 证明。当前未发现需单独 Outbox 的事实，不能仅为模板完整性新增 Outbox。

## 9 状态技术态

SRS §7 的业务状态语义为权威。本 TDD 不定义 M2“待澄清/待确认”等流程行为。M1 如创建持久请求记录，只映射 M1 会实际使用的状态。

| SRS 业务状态 | 技术承载候选 | 说明 |
|---|---|---|
| 已接收 | office.document.request.state=received | 请求和附件关联完成 |
| 检查中 | state=checking | 类型/容器及授权预检 |
| 处理中 | state=processing | 读取、渲染或回读进行中 |
| 已生成 | state=generated | 回读验证及附件授权成功后 |
| 失败 | state=failed | 可见稳定错误码，无成功附件 |
| 已取消 | state=cancelled | 任务取消后无可下载候选 |

queue_job 的 pending/enqueued/started/done/failed 是执行器技术状态，不覆盖 SRS 业务状态。两者如发生差异，业务请求状态由 office.document.request 决定；若该模型/队列未获准，则须在同步方案中明确相同的状态恢复行为。

## 10 并发、事务与幂等

### 10.1 并发控制

源模板不可被本功能写回；每个请求独立工作目录和唯一临时输出名。相同 request_uuid 重复提交不得产生多个可交付结果。避免通过全局文件名、共享 LibreOffice profile 或共享输出目录协调任务。是否允许相同附件并发被处理不影响模板正确性，但必须按目标进程内存预算限流。

### 10.2 事务策略与业务快照

M1 不读取业务记录，因此业务数据变化一致性由后续 M2 权限网关承担。M1 处理的文件快照由服务端从用户可访问附件读取并固定输入哈希；在创建结果附件前复核请求用户和交付线程仍有效。

文件解析、转换和渲染不得持有 Odoo 业务记录排他锁。Odoo 工程准则 T-TRX-002 规定事务边界不得包含外部 I/O（含文件/进程 I/O），而 queue_job 方法本身在 Odoo 事务中运行。如何把文件子进程与 ORM 提交/授权复核分成安全事务阶段，当前设计未能证明 queue_job 单独即可满足；必须通过架构 Spike 明确，禁止用长事务加“没有显式行锁”绕过该准则。

建议阶段为：短事务验证请求并取得受控输入快照/标记处理中；事务外完成文件处理；新短事务重验所有者、线程、附件权限并保存唯一有效结果。Odoo cursor/事务生命周期、失败补偿和队列重试下的落地方式必须在 TDD 冻结前用真实 Runtime 验证。不得在普通请求中自行 commit 后继续使用过期记录集。

### 10.3 幂等

T-CONC-002 要求请求 UUID 服务端生成。唯一输出关联和状态迁移须原子执行；若重试时请求已 generated，返回该请求已有且当前用户仍有权访问的结果，不重复创建附件。附件创建成功但请求状态提交失败时需有补偿/清理方案，具体事务边界待 Spike。

## 11 异常、错误码与诊断

### 11.1 错误分类

| 编号 | 稳定码候选 | 类别 | 可重试 | 用户可见行为 |
|---|---|---|---|---|
| ERR-OFFICE-001 | OFFICE_FORMAT_MISMATCH | 扩展名/MIME/签名不匹配 | 否 | 拒绝，不送解析器 |
| ERR-OFFICE-002 | OFFICE_CORRUPT_PACKAGE | ZIP/OLE/OOXML损坏或必需部件缺失 | 否 | 文件无法安全读取 |
| ERR-OFFICE-003 | OFFICE_ENCRYPTED | 加密/受保护文件当前不可处理 | 否 | 要求用户提供允许处理的未加密副本 |
| ERR-OFFICE-004 | OFFICE_RESOURCE_LIMIT | 容量、膨胀、条目或时间超过已批准上限 | 否 | 停止处理并说明资源边界 |
| ERR-OFFICE-005 | OFFICE_UNSUPPORTED_STRUCTURE | 未验证结构或宏/活动内容 | 否 | 要求人工处置或安全格式 |
| ERR-OFFICE-006 | OFFICE_MAPPING_INVALID | 缺失、null、类型错误、目标不存在或公式冲突 | 否 | 标出安全的位置级问题 |
| ERR-OFFICE-007 | OFFICE_PROCESS_TIMEOUT | 解析/转换子进程超时 | 视类别而定 | 停止并清理；不得提供部分文件 |
| ERR-OFFICE-008 | OFFICE_OUTPUT_READBACK_FAILED | 文件、结构或目标值校验失败 | 否 | 失败，无预览/下载 |
| ERR-OFFICE-009 | OFFICE_DELIVERY_FAILED | 输出附件创建/授权失败 | 视瞬时错误而定 | 不返回成功链接 |
| ERR-OFFICE-010 | OFFICE_CANCELLED | 用户取消或任务取消 | 否 | 状态已取消，无结果 |

对用户呈现阶段和可纠正动作；内部保存异常类别、request_uuid、库/转换器版本和脱敏日志。不得把原文、单元格值、客户字段、token、完整本地路径或 traceback 放入聊天。

### 11.2 失败清理与重试

失败时不返回候选文件；删除临时结果和隔离 profile，终止子进程组。若清理失败，记录清理告警并通过受控定期清扫处理；该清扫的频率/保留时长待 OPEN-OFFICE-12。只重试第 8.3 节允许的瞬时类别，且须证明幂等。

## 12 安全与权限

### 12.1 权限映射候选

| SRS 角色/上下文 | M1 权限落点 | 必须拒绝 |
|---|---|---|
| ROLE-OFFICE-01 业务用户 | 只能提交本人有权访问的聊天附件；读取/渲染服务用当前 env；结果关联同一请求/线程 | 修改 owner/thread/attachment 引用以读取他人数据 |
| llm.thread 当前用户 | 聊天接入层先验证线程归属和消息附件关系，再调用核心服务 | 仅凭客户端传入的 thread_id 或 attachment_id 放行 |
| ROLE-OFFICE-03 管理员 | M1 无自动读取业务附件的额外授权 | 管理身份不扩大附件、线程或业务记录权限 |
| M2/M3/M4 角色 | 本 M1 TDD 不分配额外能力 | 不把审核员/管理员权限提前引入 M1 |

新增 ORM ACL 和 Record Rule 的准确组 ID、域和运行时行为须基于 Odoo 18 当前权限实现及真实用户测试确定。M1 核心处理函数不得依赖 sudo；若技术初始化确需系统权限，不可用于读取用户输入文件或保存业务数据。

### 12.2 输入与内容安全

- 扩展名不能作为唯一判定依据；联合核对声明格式、MIME、文件签名和格式必需部件。OOXML ZIP 与 OLE Compound File 分别校验。
- ZIP 检查必须先检查条目数量、单项/总声明展开大小、重复路径、绝对路径和 .. 路径；有界分块检查 CRC/XML，不调用无界 extractall。
- 解析器/转换器对恶意或损坏输入必须有进程级超时、CPU/内存限制和可终止的进程组。当前 TV 只证实包装脚本的 1 MiB 限读能拒绝 16 MiB 高压缩样本；不代表库内部解压安全已验证。
- 加密文件、宏启用格式、宏/脚本、嵌入活动内容和不支持 OOXML 对象默认拒绝或按获批结构策略拒绝；不得执行宏、脚本、外链更新。
- 临时目录由服务端为每个请求创建，权限最小；客户端和 LLM 不能提供服务器路径。
- LLM 返回值（未来 M2）与模板自然语言指令均不可信，不能控制文件路径、进程参数、库选项、访问权限或目标模型。
- 只在成功通过回读校验后创建/关联结果附件；附件为私有，按现有 Odoo 权限解析，不生成公开可猜链接。

### 12.3 Chat Provider 安全边界

源码调查显示 llm_thread 在调用 Provider 前对 Office MIME 做 unsupported 检查；llm_openai formatter 只格式化文字、图片、PDF 和音频，没有 Office 结构解析。不能由此推断其他 Provider 都不会触及附件。聊天接入不得只绕过 unsupported 检查，而必须通过真实请求构造测试证明：Office 二进制不进入任一 Provider 请求；只有经用户/部署策略允许的提取结果可进入对话上下文。该项在未验证前是阻断性技术决策，不修改 Odoo-LLM 上游核心代码。

## 13 UI 契约

| 编号 | UI/动作候选 | 类型 | 行为 | 状态 |
|---|---|---|---|---|
| UI-OFFICE-001 | 聊天文件接收 | 复用 llm_thread 现有附件上传 | 现有附件关联机制可复用；Office 专用路由/处理状态扩展点需验证 | 候选 |
| UI-OFFICE-002 | 结构读取结果 | 聊天消息或受控面板 | 展示格式、可识别结构和未识别对象；不能把整篇文档默认发送至 Provider | 界面承载尚未决定 |
| UI-OFFICE-003 | 映射输入/确认 | 不预设自定义 Owl | M1 需要确定谁提供 render 的 Mapping JSON；SRS 未定义 M1 手工映射编辑器，不能擅自新增复杂 UI | 阻断项 |
| UI-OFFICE-004 | 处理状态/结果 | 优先复用聊天消息及附件列表 | 显示处理中、成功/失败阶段、同请求的唯一附件；刷新后恢复能力取决于请求模型/异步方案 | 待决 |

是否开发专属面板、向导或前端轮询须先证明 Odoo 标准视图和现有聊天 UI 不足。M1 UI 不能引入 AI Mapping 确认流程；如 M1 AC 要求用户确认 JSON 映射，需业务负责人澄清其手工操作语义。

## 14 测试设计

### 14.1 分层

| 层级 | 覆盖 | 方式 |
|---|---|---|
| 纯 Python 单元 | 结构摘要、Mapping schema、格式判别、公式/目标保护 | Odoo 外小型单元测试；不替代集成 |
| Odoo TransactionCase | 附件授权、请求模型、状态、附件关联、重复提交 | 当前 Odoo 18 Runtime、真实 ACL/Record Rule |
| 隔离进程集成 | LibreOffice/解析库启动、超时、输出与清理 | 隔离临时目录、独立 profile 和可控样本 |
| 浏览器/E2E | 上传、状态、失败提示、成功附件与刷新恢复 | 在完成 UI 决策后定义；本 TDD 不声称已运行 |
| 目标环境验证 | 目标 Linux/字体/Worker/反向代理/内存 | M1 生产启用前按真实部署拓扑执行 |

### 14.2 需求与实现测试矩阵

以下实现验收均尚未执行；Workflow Evidence Status = Missing。引用 TV 为有限技术证据，不将它映射成业务 AC 的 Passed。

| TEST | SRS / TDD | Given / When / Then | 现有 TV 证据 | Workflow Evidence Status |
|---|---|---|---|---|
| TEST-OFFICE-001 | FR-M1-001, AC-01 | 当前用户上传四种准入格式 / 提交 / 当前消息和线程关联正确；确认格式变化时按规则提示 | 仅源码静态确认聊天附件关联 | Missing |
| TEST-OFFICE-002 | FR-M1-002, AC-02、AC-07 | 扩展名伪装、空文件、损坏 ZIP/OLE / 请求读取 / 在解析器前拒绝且无 Provider 调用 | 合成异常被 Python 捕获；LO 可误对伪装生成 PDF | Missing |
| TEST-OFFICE-003 | FR-M1-003, AC-03 | 多工作表含公式/合并区 / 读取 / 返回工作表、坐标、公式和未知结构标记 | 合成与真实 XLSX 有部分对象证据 | Missing |
| TEST-OFFICE-004 | FR-M1-003, AC-04 | 有段落/多层表格 DOCX / 读取 / 顺序和表格层次可回读 | TARGET DOCX 有段落/表格结构检查 | Missing |
| TEST-OFFICE-005 | FR-M1-004/007, AC-05、AC-09 | 合法/缺失/null/错误类型/未知 element/公式格映射 / 渲染 / 仅合法写入，错误分类明确 | 无 Odoo 功能证据 | Missing |
| TEST-OFFICE-006 | FR-M1-005, AC-06/23 | XLSX 公式和缓存 / 修改非公式格并回读 / 公式文本不变、目标正确，缓存另行报告 | P0-B 证明 openpyxl 3.0.9 清缓存 | Missing |
| TEST-OFFICE-007 | FR-M1-005/009, AC-29 | 真实 .xls 公式和样式 / 受控写回/回读 / 支持范围完整，否则安全失败 | 仅合成旧格式部分转换证据 | Missing |
| TEST-OFFICE-008 | FR-M1-006/009, AC-08、AC-30 | DOCX/DOC 高级对象 / 写回/回读 / 按声明策略保留或拒绝，无伪成功 | TARGET 不含文本框/VML；旧 DOC 合成 VML 改变 | Missing |
| TEST-OFFICE-009 | FR-M1-008/009, AC-10/17/31 | 渲染成功、失败、升级格式及跨用户下载 / 请求/下载 / 原格式默认、新结果授权、失败无链接 | 无聊天交付/ACL 运行证据 | Missing |
| TEST-OFFICE-010 | BR-OFFICE-03/04/10/15, AC-23 | 模板含公式与结构 / 预览和最终生成 / 两条路径共用强制回读，失败不交付 | TV 仅独立脚本/副本行为 | Missing |
| TEST-OFFICE-011 | NFR-OFFICE-02, T-SEC-002/004 | 高膨胀、路径穿越条目、加密文件 / 解析 / 限额拒绝，不无界展开或越权写路径 | 仅包装层有界读取部分通过；加密未运行 | Missing |
| TEST-OFFICE-012 | NFR-OFFICE-12, T-Q-001 | 超时、刷新、重试、重复请求 / 查询状态和结果 / 状态可恢复且单一授权附件 | queue_job 本机只读链路通过；Office 负载/生产 Inconclusive | Missing |
| TEST-OFFICE-013 | T-CONC-002, ORM-DATA-001/002 | 同一请求重复提交/队列重试 / 并发完成 / 仅一个有效输出关联 | 未测业务请求幂等 | Missing |
| TEST-OFFICE-014 | T-ERR-001 | 文件名/库异常含内部路径 / 触发错误 / 用户消息脱敏、日志最小化 | 未测产品错误层 | Missing |
| TEST-OFFICE-015 | T-LOCK-001/002, T-TRX-002/003 | 慢文件任务并发 / 完整执行 / 无长业务锁且文件进程不跨越违规事务 | 未测 Odoo 集成事务 | Missing |
| TEST-OFFICE-016 | Chat Provider Boundary | 各 Provider / 聊天 Office 附件 / 外发请求不包含 Office 二进制 | 静态源码有限；无请求外发证据 | Missing |

### 14.3 测试追踪

每个 M1 AC 至少一项实际实现测试。TV 脚本只证明其直接测量的库行为；不能替代 Odoo 用户 ACL、聊天路由、状态恢复、附件访问和最终输出验收。测试失败、跳过或阻塞须保留原状态，不得因 TDD 草案中的方案描述而改成通过。

## 15 可观测性

技术日志允许记录 request_uuid、阶段、格式、输入/输出大小、哈希摘要、库/转换器版本、耗时、资源限额命中、退出码、错误码、重试计数和清理结果。不得记录模板原文、单元格业务值、完整 mapping 值、token、公开附件 URL 或用户无关字段。

M1 只记录完成安全运行和故障诊断所需的技术事件；SRS FR-M4-002 的企业治理审计属于 M4，不在 M1 建立完整治理审计模块。任务状态和附件授权结果仍须可按请求关联。

## 16 部署与运行前置

### 16.1 运行前置

| 项 | 前置要求 | 当前状态 |
|---|---|---|
| Odoo 版本/commit | Odoo 18 CE，记录实施目标实例准确版本 | 精确目标版本待核 |
| Python/PostgreSQL | 与实际 Odoo 部署匹配并锁定 | Python TV 3.11.9；目标 Postgres/部署 Python 未核 |
| Office Python 包 | 精确版本、许可证、目标 venv 安装和安全审查 | 尚未决策/不得安装 |
| LibreOffice | 仅当选型通过；稳定版本、目标 OS、字体和进程隔离验证 | 当前仅 LibreOfficeDev Alpha |
| queue_job | 仅异步方案选中时；生产模块路径、worker、runner、proxy、channels | 本地 threaded 通过；生产未验证 |
| 容量及超时 | CFG-OFFICE-02 数值、展开大小、条目数、worker/进程限制 | OPEN-OFFICE-05，缺失即不能生产启用 |
| 文件保留 | 结果附件/临时文件保留、清理、聊天归档策略 | OPEN-OFFICE-12 |
| 字体 | 视觉验收主机具备目标所需 CJK 字体并记录许可/版本 | 当前环境视觉 Inconclusive |

### 16.2 SRS 配置映射

| SRS CFG | TDD 实现建议 | 默认 / 可维护角色 | 生效范围 |
|---|---|---|---|
| CFG-OFFICE-01 支持格式 | 服务端固定 allowlist，严格按实际内容判别 | 固定 M1 准入列表；不能由用户自扩展 | 新请求 |
| CFG-OFFICE-02 容量/时限 | 通过经评审配置或部署配置给出所有限制 | 数值待 TV/目标预算，责任角色待指定；未配置时拒绝生产处理 | 新请求；变更不改变已运行任务边界 |
| CFG-OFFICE-05 LLM 数据策略 | M1 核心不调用 Provider；聊天适配发送内容须按部署政策决定 | M2 启用Provider前批准 | M1 不扩展该业务决策 |

配置载体（system parameter、受限配置模型或部署变量）和权限需通过 Odoo 原生设置评估，尚未冻结。

### 16.3 数据迁移

当前未实现、未建立 Office M1 ORM 模型，暂无已知 Office 历史请求数据需要迁移。若最后选择新建请求模型，初次安装无历史记录可迁；实施前仍须再次确认数据库是否已有该模型/试验数据。结论为暂定 No Migration，理由是 M1 为新能力且当前源码调查未发现对应模型；不能据此删除任何现存附件或记录。

## 17 技术风险与防护

| 编号 | 风险 | 触发条件 | 当前证据/状态 | 防护与兜底 |
|---|---|---|---|---|
| RISK-OFFICE-001 | XLSX 写回丢扩展 | openpyxl 处理不支持 OOXML | 真实样本证实 3.0.9 丢扩展节点、custom.xml | 选引擎前扩展结构差异通过硬门禁；不通过就拒绝该路径 |
| RISK-OFFICE-002 | 公式缓存无效 | 库保存或转换后缓存被清空/过期 | 89/89 缓存在 openpyxl 保存后丢失；LO Alpha 恢复样本缓存 | 公式表达式和缓存分别校验；SRS 仅不承诺重新计算，是否允许缓存丢失仍待 OPEN-03 |
| RISK-OFFICE-003 | DOCX 高级对象丢失 | python-docx 保存含文本框/VML | TARGET 无此对象；另有旧 DOC 转换 VML 改变 | 对象能力白名单需样本支撑；不支持时拒绝，不声称无损 |
| RISK-OFFICE-004 | 旧格式误承诺 | .xls/.doc 真实样本不足 | 当前主要为合成转换证据 | 真实样本及稳定版/目标 OS 前不冻结兼容范围；需求变化走 SRS |
| RISK-OFFICE-005 | Worker OOM/超时 | 大文件/LO 高 RSS/并发 | 仅可见进程的局部数据，生产预算 Inconclusive | 目标预算和进程树测量前不定阈值、不开放生产 |
| RISK-OFFICE-006 | Provider 获得原始文件 | 仅放宽聊天附件拒绝逻辑 | 当前多 Provider 行为未完整验证 | Provider payload 回归必须证明 Office 二进制不外发 |
| RISK-OFFICE-007 | 临时数据残留 | 超时/异常/强杀 | 全进程树/生产清理未测 | 独立临时目录、finally 清理、失败告警和受控清扫 |
| RISK-OFFICE-008 | Mapping authoring 未定义 | M1 渲染需 JSON 但 SRS 未定义谁如何输入 | SRS FR-M1-004/AC-05要求渲染，M2才实现AI映射 | 评审澄清 M1 手工输入/技术测试边界；不擅自增加产品 UI |
| RISK-OFFICE-009 | 长事务约束冲突 | queue_job job 中同步执行子进程 | queue_job 本机链路不验证事务+文件 I/O 分离 | 先完成事务/子进程 Spike；未通过不得实现该运行路径 |

## 18 Implementation Guardrails / Coding Contract Baseline

以下门禁只有冻结 TDD 后才能被首个 CC 引用。当前仅是草案编号，不授权实施。

| 编号 | 规则 | 强度 | 来源 |
|---|---|---|---|
| T-SEC-001 | 不在日志/聊天写入模板原文、业务值、凭据或访问 token | 强制 | Odoo 工程准则、NFR-OFFICE-03 |
| T-SEC-002 | 所有外部输入和 Mapping Plan 必须服务端 schema 校验；未知字段/操作默认拒绝 | 强制 | FR-M1-002/007、BR-OFFICE-06 |
| T-SEC-003 | 不使用 sudo 绕过附件、线程或业务访问权限；所有操作绑定当前授权用户 | 强制 | NFR-OFFICE-01、BR-OFFICE-05 |
| T-SEC-004 | 文件扩展名不是信任来源；联合检查签名、MIME、容器和必需部件 | 强制 | FR-M1-002、BR-OFFICE-02 |
| T-SEC-005 | 限制文件大小、展开大小、条目数、处理时间和进程资源；上线阈值必须来自 OPEN-OFFICE-05 验证 | 强制 | NFR-OFFICE-02/08 |
| T-SEC-006 | 不执行宏、脚本、外链更新或任意服务器路径；失败输入不调用渲染器 | 强制 | SRS §1.3、BR-OFFICE-06 |
| T-DATA-001 | 模板原件不可覆盖；输出为本次新结果且格式符合已确认的选择 | 强制 | FR-M1-004/008、BR-OFFICE-03 |
| T-DATA-002 | 公式格不可成为写入目标；公式文本、缓存和计算结果分项回读，不互相推定 | 强制 | FR-M1-005、BR-OFFICE-04 |
| T-VERIFY-001 | 每次渲染（预览/测试/最终）必须通过同一后端读回验证 | 强制 | FR-M1-009、BR-OFFICE-15 |
| T-VERIFY-002 | 文件可打开不等于结构、公式缓存、视觉或高级对象通过 | 强制 | SRS FR-M1-005/006/009 |
| T-ERR-001 | 用户错误不暴露 traceback、内部路径、库实现细节或其他请求数据 | 强制 | NFR-OFFICE-06、Odoo 工程准则 |
| T-LOCK-001 | 不跨外部文件/进程 I/O 持有排他锁 | 强制 | Odoo TDD 工程模板 |
| T-LOCK-002 | 文件处理不得长时间持有业务记录锁；短事务与处理阶段隔离 | 强制 | NFR-OFFICE-11 |
| T-TRX-001 | 聚合内部需要原子维护的不变量及其内聚数据修改，必须在同一事务一致性边界内完成；本 M1 不定义额外聚合边界 | 强制 | Odoo 工程模板 T-TRX-001 |
| T-TRX-002 | 事务边界不得包含外部 I/O（包括文件/进程 I/O）；队列任务不得在 ORM 事务中直接执行 Office 文件处理 | 强制 | Odoo 工程模板 T-TRX-002、NFR-OFFICE-11 |
| T-TRX-003 | M1 必须明确短事务、文件处理阶段和结果提交阶段的隔离方式；不得用长事务解决映射一致性 | 强制 | NFR-OFFICE-11/12 |
| T-Q-001 | 异步任务状态/错误/重试可观察，重试策略明确；不允许重复有效交付 | 强制 | NFR-OFFICE-12 |
| T-CONC-001 | 临时文件、LibreOffice profile、输出目标按请求隔离 | 强制 | TV Plan §3.3/4.3 |
| T-CONC-002 | 同 request_uuid 和队列重试最多有一个有效输出附件 | 强制 | NFR-OFFICE-12、AC-28 |
| T-OBS-001 | 技术事件可关联请求 ID、阶段、版本、错误和清理状态，且不存不必要业务值 | 强制 | NFR-OFFICE-06/07 |
| T-MIG-001 | 首次安装与既有数据迁移结论需在 CC 前复核 | 强制 | Odoo TDD 工程模板 |

## 19 需求追溯矩阵

### 19.1 M1 SRS → TDD

| SRS 编号 | TDD 落地 | 验证覆盖 | Workflow Evidence Status |
|---|---|---|---|
| FR-M1-001 | §2、3、12、13 | TEST-OFFICE-001/009 | Missing：未实现 |
| FR-M1-002 | §6、7、12 | TEST-OFFICE-002/011 | Missing：未实现；仅有解析器探测 |
| FR-M1-003 | §2、6、5 | TEST-OFFICE-003/004 | Missing：未实现 |
| FR-M1-004 | §5、6、7、13 | TEST-OFFICE-005/010 | Missing：Mapping UI/调用者待决 |
| FR-M1-005 | §7.2/7.3、18 | TEST-OFFICE-006/007 | Missing：P0-B Partial 不等于业务验收 |
| FR-M1-006 | §7.2/7.3、18 | TEST-OFFICE-008 | Missing：P0-A Partial 不覆盖高级对象/目标环境 |
| FR-M1-007 | §5、6、11 | TEST-OFFICE-005 | Missing：无实现 |
| FR-M1-008 | §3、5、6、9、12 | TEST-OFFICE-009/012/013 | Missing：附件 ACL 和刷新恢复未运行 |
| FR-M1-009 | §7.3、14、18 | TEST-OFFICE-010 | Missing：无 Odoo 输出读回实现 |
| BR-OFFICE-02/03/04/06/10/15 | §5、7、11、12、18 | TEST-OFFICE-002/005/006/010/011 | Missing：设计约束未执行 |
| NFR-OFFICE-01/02/03/04/06/08/11/12 | §1、7—18 | TEST-OFFICE-009—016 | Missing：运行时、预算和 UI 未验证 |
| CFG-OFFICE-01/02 | §7、16 | TEST-OFFICE-001/002/011/012 | Missing：限额值尚未确定 |
| AC-01—AC-10、AC-17、AC-23、AC-28—AC-31 | §14 | TEST-OFFICE-001—015 | Missing：无实现验收执行 |

### 19.2 M2—M4 边界

FR-M2-001 至 FR-M2-005、FR-M3-001、FR-M4-001/002、FR-PERM-001—004、BR-OFFICE-01/05/07/08/09/11/12/13/14/16 及 AC-11—AC-27 的业务逻辑不由本 M1 TDD 实现。M1 仅确保架构边界不阻碍后续阶段：不写业务记录、不直连业务模型、不引入 Skill 或治理对象。未来 M2/M3/M4 TDD 必须重新追溯并独立验收；本表不表示这些要求已满足。

### 19.3 TDD 契约 → 测试

| 契约 | 测试 |
|---|---|
| T-SEC-001—006 | TEST-OFFICE-002、011、014、016 |
| T-DATA-001/002 | TEST-OFFICE-005—010 |
| T-VERIFY-001/002 | TEST-OFFICE-006—010 |
| T-LOCK-001/002、T-TRX-002/003 | TEST-OFFICE-015 |
| T-Q-001、T-CONC-001/002 | TEST-OFFICE-012/013 |
| T-ERR-001、T-OBS-001 | TEST-OFFICE-014 |
| ORM-DATA-001/002/003 | TEST-OFFICE-001、009、013 |

当前所有测试 Workflow Evidence Status 均为 Missing；结构性 TV 证据列在各行备注中，不代替实现测试。

## 附录 A 术语

| 术语 | 含义 |
|---|---|
| 结构读取 | 输出有层次标识的单元格、段落、表格等文件内容，不等于 AI 字段映射 |
| Mapping Plan | 受控目标位置与显式值/来源的结构化写入请求；M1 只定义有限写入接口候选 |
| 公式表达式 | 工作簿中的公式文本，不等同于当前缓存计算值 |
| 公式缓存 | 文件中保存的上次计算结果；公式文本存在不代表缓存存在或正确 |
| 回读校验 | 重新打开候选输出并核对内容及预登记结构，不等于视觉版式验收 |
| 当前用户环境 | 与 Odoo 当前请求用户一致的权限上下文；不得由模型参数替换 |

## 附录 B 技术决策记录

| 编号 | 决策主题 | 候选 / 当前建议 | 依据与取舍 | 状态 |
|---|---|---|---|---|
| TD-001 | 核心与聊天接入模块边界 | 建议核心 Office addon 与聊天适配分开；适配不依赖 Provider | SRS M1 独立于 AI/业务数据；现有 llm_thread 处理 Office 为不支持，安全路由需验证 | Open |
| TD-002 | 聊天扩展路径 | 只接受经 Spike 证明不会将原始 Office 二进制送入任一 Provider 的路径 | 当前源码检查为静态且仅部分 Provider；不修改 Odoo-LLM 上游核心 | Open，实施阻断 |
| TD-003 | XLSX 写入库 | 暂不选 openpyxl 3.0.9；重测 3.1.x、LibreOffice 稳定版及其他保结构候选 | 实际模板上缓存丢失和扩展 OOXML 移除；LO Alpha 样式属性差异广泛 | Open |
| TD-004 | DOCX 写入库/对象范围 | python-docx 1.2.0 仅普通段落局部可行；部署依赖与复杂对象逐项测试后决定 | 目标 venv 无库；计划候选 1.1.x 未测；样本无文本框/VML | Open |
| TD-005 | XLS/DOC 旧版转换 | 暂将 LibreOffice 稳定版作为候选，不承诺通用保真 | 合成往返部分可打开但存在样式/VML变化；无真实旧格式文件证据 | Open |
| TD-006 | Excel 公式缓存 | 确认公式文本保护是硬要求；缓存/重算单独测量；不声称本引擎计算公式 | SRS 明确不承诺公式计算/刷新；openpyxl 清缓存，LO Alpha 曾恢复样本缓存 | Open，须关闭 OPEN-OFFICE-03/14 |
| TD-007 | Mapping Plan schema 与编辑者 | 本文 5.2 为最小候选；明确服务端元素 ID 和显式值，拒绝代码/路径 | 避免任意 DSL；SRS 未定义 M1 谁提供 JSON/人工映射 UI | Open，实施阻断 |
| TD-008 | 同步/异步及队列 | 不选最终方案；按目标资源预算决定；queue_job 仅候选 | 本机 queue_job 只读任务 Pass；生产预算、prefork 和 Office 负载 Inconclusive | Open |
| TD-009 | 文件/事务生命周期 | 建议短事务检查—事务外文件处理—短事务复核/交付；必须真实验证 Odoo cursor/queue 语义 | 组织规则禁止事务含文件 I/O；当前 queue_job 单独不能证明满足 | Open，实施阻断 |
| TD-010 | 配置阈值和临时文件策略 | 数值由样本/目标环境验证；结果/临时附件生命周期由业务方确定 | OPEN-OFFICE-05/12 尚未关闭 | Open |
| TD-011 | 请求模型及状态恢复 | 异步或刷新后状态恢复需要最小持久请求对象；若同步充分，可评估不创建 | NFR-OFFICE-12及状态恢复；需与 TD-008 一起决策 | Open |
| TD-012 | 格式升级和输出扩展名 | 默认保留输入格式；任何升级先明确告知并确认 | SRS FR-M1-008/AC-31 | SRS 已定；实现细节待定 |

## 附录 C 版本记录

| 版本 | 日期 | 状态 | 变更 |
|---|---|---|---|
| V0.1 | 2026-10-19 | Draft — Not Approved for Implementation | 基于 SRS V1.0.0、Frozen TV Plan、原始 TV 报告及 P0 补验 V0.2/V0.3/V0.4 起草；保留所有未验证限制与技术待决项 |

## 附录 D TDD 草案自检

| 自检项 | 结论 | 说明 |
|---|---|---|
| 追溯到冻结 SRS | 部分完成 | M1 FR/BR/NFR/AC 已映射；M2—M4 明确排除本范围，不声称实现 |
| TV 事实与设计假设分开 | 通过 | 各依赖标出现有证据和限制；P0 状态保留原值 |
| 无 SRS 范围外功能 | 需评审 | office.document.request 和两模块拆分是技术建议，尚未批准 |
| 安全/权限后端边界 | 草案完整、实现未验证 | 无 sudo 绕权、容器校验、Provider payload 和附件 ACL 均列出门禁 |
| 四种 Office 格式边界 | 未关闭 | .xls/.doc 真实样本、稳定版转换和高级对象仍缺证据 |
| 无虚构性能承诺 | 通过 | 不将合成样本测量外推为目标预算；阈值留待 TV |
| 同步/异步策略 | 未决 | queue_job 仅本机基础链路通过，生产资源 Inconclusive |
| 接口是否可直接实现 | 部分 | 结构读取/Mapping 最小契约已提出；DOCX element_id、null 清空和 M1 映射提供者待定 |
| 重要事务问题 | 未决且阻断 | queue_job 事务、子进程 I/O 与 Odoo cursor 的安全切分未证明 |
| DDD 适用性 | 未决 | 未找到 Office DDD，但负责人未记录“不适用”判断 |

### 评审前置问题

1. 明确 M1 的 Mapping JSON 由谁提供，以及 SRS 中 AC-05/FR-M1-004 在无 M2 AI 映射时的 M1 用户交互；不得默认新增编辑器。
2. 完成安全聊天路由 Spike，确认现有 llm_thread/各启用 Provider 的请求链不会收到 Office 原始二进制，也不需修改上游核心。
3. 决定并验证解析/转换进程如何在满足 Odoo 事务规则的同时保存附件和状态。
4. 补齐真实 XLS/DOC 样本、目标稳定版 LibreOffice、CJK 字体和目标运行时 P0-A/B 验证；若发现违反冻结 SRS 的不可实现点，走 SRS 变更而非 TDD 降级。
5. 提供目标部署 Worker/代理/内存预算、文件容量边界和临时/结果附件保留策略，关闭 OPEN-OFFICE-05/12 的 M1 门禁。
6. 负责人记录 DDD 适用性判断并评审 TD-001 至 TD-011。

### 是否可以制定 Implementation Plan

可以开始编写**仅供评审的 Draft Implementation Plan**，把以上问题安排为验证/决策前置工作，并准确引用 SRS、TV 和本 TDD V0.1 Draft；该计划不得称为已基线化或批准，不得用于创建 CC 或开始实施。按项目工作流，只有 TDD 评审通过并冻结、Implementation Plan 完成评审并基线化后，才能创建首个 CC 和进入实施。

