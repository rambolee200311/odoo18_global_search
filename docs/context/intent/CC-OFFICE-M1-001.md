<!-- Skill bundle metadata
Source path: docs/context/cognition/template/Coding/Coding_Contract模板.md
Source version/status: v1.0.0; Frozen
Synced: 2026-10-20
-->

# CC-OFFICE-M1-001 — Office Core 纯 Python 同步底座

## 0. Governance

| 字段 | 值 |
|---|---|
| Coding Contract | `CC-OFFICE-M1-001` |
| 版本 | `v1.0.0` |
| 状态 | **Frozen — 已由业务负责人批准（2026-10-20）；允许按本 CC 实施** |
| Intent ID | `OFFICE-ENGINE-M1-CORE-FOUNDATION` |
| 模块 | `office_core`（纯 Python 包；不创建 Odoo 模型） |
| 工作类型 | 新功能 / 安全底座 |
| 上游 SRS | [SRS_office_document_automation](../../requirement/SRS_office_document_automation.md) V1.0.0 Frozen |
| 上游 DDD | N/A；业务负责人于 2026-10-20 确认 M1 无状态文件引擎不需要领域模型 |
| 上游 TDD | [TDD_office_engine_m1](../../design/TDD_office_engine_m1.md) V0.3 Frozen |
| 上游 Implementation Plan | [IMPLEMENTATION_PLAN_office_engine_m1](../../implementation/IMPLEMENTATION_PLAN_office_engine_m1.md) V0.2 Frozen |
| 上游 TV | [TV Plan](../../verification/TV_Office_Engine_M1_Plan.md) V1.0.0 Frozen；报告与 P0 状态按 TDD §1.2 保留 |
| 前置 CC | 无；First CC Gate 为 READY，可起草本 CC |
| 相关 CC | `CC-OFFICE-M1-002`（拟建，独立回读校验） |
| 目标 | 建立无 Odoo 依赖的同步 Office 核心：安全识别和读取受限文件结构、校验显式 Mapping Plan、按允许能力写出隔离候选文件。 |
| 批准 / 冻结 | 业务负责人于 2026-10-20 明确批准冻结并进入实施；依赖选择、安装和锁版限于本 CC §11.1，安装及 smoke test 先于核心代码。 |

**首 CC 门禁核对：** Implementation Plan V0.2 Frozen 的 First CC Gate 结果为 `READY — 可起草 CC-OFFICE-M1-001`。该结果不是本 CC 的批准或实施授权。不得在本 CC 冻结前安装依赖或修改代码。

**依赖决策状态：** 本 CC 冻结了 §11.1 的精确直接依赖版本和许可证元数据；Python 3.11.9 元数据兼容不等于已在项目 `venv` 实际验证。现在可按冻结清单安装依赖；`pip check`、导入和合成读写 smoke test 必须先于核心代码。任何失败都阻塞后续实现。

## 1. 变更概述

**目标：** 按 TDD V0.3 §2—4 和 Implementation Plan Phase 1，实现有界输入/输出的纯 Python `office_core`。候选文件只供后续 `office_verify` 检查，不是成功结果、预览或可下载附件。

**背景：** 当前 TV 对真实 `.xlsx` 和 `.docx` 只提供 Partial 证据，对真实 `.xls/.doc` 的保真写回没有充分证据。M1 必须先建立可拒绝不安全输入、限制资源、读取受支持结构并受控写入候选的核心；文件可打开不等于保真。每种格式/结构只有通过相应能力门禁后才可启用。

## 2. 上游基线与追溯

### 2.1 SRS 引用

| SRS ID | 标题 | 与本次 CC 的相关性 |
|---|---|---|
| FR-M1-002 | 文件类型与安全结构识别 | 本次范围；对扩展名、MIME/签名及容器进行一致性检查，拒绝损坏、加密、伪装、超限和未支持输入。 |
| FR-M1-003 | Office 结构读取工具 | 本次范围；只读取并表达经能力门禁允许的结构，不推断业务字段映射。 |
| FR-M1-004 | 受控模板渲染工具 | 部分范围；只接受显式合法 Mapping Plan 并产生新候选，不交付、不预览。 |
| FR-M1-005 | Excel 完整性与公式保护 | 部分范围；已启用能力中不得写公式格；不承诺公式重算或缓存刷新。最终输出完整性回读属于 CC-002。 |
| FR-M1-006 | Word 完整性保护 | 部分范围；只允许通过能力门禁的结构；未验证高级对象拒绝。 |
| FR-M1-007 | 映射数据校验 | 本次范围；按 TDD Mapping Plan V1 校验结构、目标、操作和值类型。 |
| BR-OFFICE-02/03/04/06/10 | 文件格式安全、源模板不覆盖、公式保护、不可信输入和失败处理 | 仅落实本 CC 涉及的核心行为；不扩展业务语义。 |
| NFR-OFFICE-02/04/08 | 文件安全、完整性、容量与时限 | 本次范围；资源限制来自调用方策略；超限拒绝或受控终止。 |
| AC-02/03/04/05/06/07/08/09 | 畸形文件、结构读取、受控写入、公式和 Mapping 校验 | 只覆盖纯核心可验证部分。AC-05 的最终用户确认交互不在本 CC 内，也不得由内部测试宣称已通过。 |

FR-M1-001、FR-M1-008、FR-M1-009 及 AC-01/10/17/23/29/30/31 的聊天接收、附件持久化、最终回读与交付不属于本 CC；由后续阶段/CC 验收。

### 2.2 DDD 引用

N/A。不得为本 CC 创建虚构的 DDD 编号。

### 2.3 TDD 引用

| TDD ID / 章节 | 标题 | 相关性 |
|---|---|---|
| TD-001、TD-003—TD-008、TD-013 | 分层、格式能力、公式、Mapping Plan、同步执行和实现顺序 | 本 CC 必须遵守；特别是同步、有限能力、失败关闭和 Provider/ORM 解耦。 |
| TDD §3.2—3.4 | 核心服务接口、Mapping Plan V1、错误契约 | 本次服务输入、输出和校验的唯一技术基线。 |
| TDD §4—4.2 | Office 格式能力与启用策略 | 未通过能力门禁的格式/对象必须保持关闭并明确拒绝。 |
| TDD §7.1—7.3 | 安全、资源限制、稳定错误类别 | 本次容器校验、限制、错误和临时资源处理的强制设计约束。 |
| TDD §8.2 / TEST-OFFICE-002—008、011、014 | M1 测试追踪 | 按本 CC 适用部分执行；回读类断言属于后续 CC。 |
| TDD §11 / TD-008 | 首期同步，异步后置 | 不加入 Queue Job、后台任务或请求生命周期耦合。 |

### 2.4 Bug Report / 事件报告

不适用；本 CC 为新功能底座。

### 2.5 追溯规则

本 CC 只授权 §3.1 声明纳入的 SRS/TDD 范围。凡发现技术设计不足、依赖无法满足已冻结要求、需要改变 SRS/TDD 或开放未验证格式能力，必须按 §12 停止并升级。

## 3. 范围冻结

### 3.1 在范围内（In Scope）

- 在 `mymodules/office_core/` 新建可独立导入的纯 Python 包；核心不得导入 Odoo、ORM、`env`、HTTP、Provider、Queue Job 或聊天模块。
- 在该包中实现 TDD §3.2 定义的同步 `inspect_document` / `render_candidate` 服务契约及稳定结果/错误类型；接口接收有界字节和服务端能力/资源策略，不接受服务器路径、任意命令或动态代码。
- 实现格式/内容一致性和容器安全预检；在四种格式 `.xlsx/.docx/.xls/.doc` 上区分格式识别与实际处理能力。未通过能力门禁的格式/对象明确拒绝。
- **首期能力白名单：** 仅将 `.xlsx` 的基础单元格读取及非公式单元格 `set_value`、`.docx` 的基础段落/表格文本读取及受控文本写入列为候选能力；只有 CC 测试和指定样本通过后才可逐项启用。`.xls`、`.doc` 的写能力在本 CC 全程关闭；`.doc` 内容读取也关闭；`.xls` 仅可在独立 read-only 样本测试通过后启用受限读取。公式、公式缓存、未知/不支持 OOXML 扩展、宏、外部活动内容、文本框/VML、批注、嵌入对象及其他未列入白名单的结构均拒绝或保持关闭。
- 实现已启用能力内的结构读取、稳定元素 ID、未知结构标记及格式能力描述；不声称覆盖解析器未识别对象。
- 实现 TDD §3.3 Mapping Plan V1 的结构校验：根字段白名单、版本、模板指纹、写入集合、元素 ID、操作、类型和值边界；缺失、显式 `null`、空字符串、零值和类型错误须区分。
- 只允许 `set_value` 白名单操作。公式目标、重复/未知/不可写目标、未知键和不支持的显式 `null` 拒绝。
- 对通过能力门禁的映射生成新候选字节；原始模板不变，候选不进入附件、不生成下载链接，也不被宣称为已通过完整性回读。
- 为压缩容器、OLE 容器、损坏/加密/伪装/空文件、展开限制、结构数量限制及处理时限提供有界检查和稳定错误类别；具体资源数值由服务端传入策略，不在代码中猜测生产阈值。
- 按 §11.1 直接依赖 pin 安装并记录解析后的依赖闭包、许可证/NOTICE 与目标 Python 3.11 `venv` 运行验证；清单仅写在 `mymodules/office_core/requirements.txt`，不修改仓库根 `requirements.txt`。
- 在 `mymodules/office_core/tests/` 建立纯 Python 自动化测试；实施证据存放于 `docs/implementation/office-engine-m1/CC-OFFICE-M1-001/`。

**格式准入规则：** 当前可用 TV 事实为 P0-A `.docx` PARTIAL、P0-B `.xlsx` PARTIAL；合成/旧格式证据不能外推至真实 `.xls/.doc`。本 CC 首期候选白名单限于上列 `.xlsx` 基础单元格和 `.docx` 基础段落/表格文本能力；它们不是预先宣告已支持，须有目标运行时、样本与测试证据后逐项启用。`openpyxl` 报告 unsupported/extension 丢弃或降级时，该文件拒绝渲染，不能因目标单元格简单而忽略警告。未满足门禁时测试验证安全拒绝，不得把“当前关闭”写成“格式已支持”。

### 3.2 超出范围（Out of Scope）

- `office_verify` 独立回读引擎和完整输出结构/公式/目标值校验；属于 `CC-OFFICE-M1-002`。
- 任何 Odoo Addon/Manifest 安装、ORM 模型、`ir.attachment`、请求状态持久化、数据库迁移、附件回滚/清理或 `request_uuid`。
- 聊天消息钩子、Provider 路由、Office 二进制防外发实现、工具注册或 LLM 调用；需先完成独立 Spike。
- Mapping 编辑器、用户确认 UI、AI 语义推断、Odoo 业务模型/记录查询、Skill 和安全字段白名单。
- PDF、图片、PPT/PPTX、`.xlsm`、宏/脚本/外部活动内容执行、任意路径读写。
- `.xls/.doc` 的一般性无损支持；`.xlsx/.docx` 未通过验证的高级对象、公式缓存刷新、公式计算、未知 OOXML part、外部链接/宏/嵌入对象保证。
- LibreOffice Alpha 或未经锁版、超时隔离和真实样本验证的转换路径。
- Queue Job、异步任务框架、重试/取消/恢复/并发调度、生产容量承诺。
- 修改 Odoo 官方源码/官方 Addon、SRS、冻结 TDD、Implementation Plan、TV 报告或结构化 TV 证据。
- 在 CC 冻结前安装依赖或开始代码实现；本次起草不执行依赖安装、Odoo 操作或业务功能测试。

### 3.3 非目标（Non-Goals）

- 本 CC 不完成整个 M1；其候选输出必须等待 CC-002 回读后才可能进入 Odoo 封装。
- 不通过放宽资源限制、忽略警告或静默转换来提高“成功率”。
- 不以单个模板或“能打开”证明某格式/结构普遍保真。
- 不声称 SRS AC-05 用户确认、AC-23 回读或任何未运行测试已经通过。

### 3.4 仅限范围追溯

本 CC 纳入的每个 SRS/TDD ID 均在 §14.1 映射到至少一个 `CC-CHANGE`。被排除的上游需求不因本 CC 获得实施授权。

## 4. 变更边界

### 4.1 允许

| 类型 | 详情 |
|---|---|
| 新 Python 包 | `mymodules/office_core/**`；仅纯 Python 核心及其测试，不包含 Odoo Manifest、模型、视图或控制器。 |
| 依赖清单 | `mymodules/office_core/requirements.txt`；仅写入本 CC §11.1 批准的精确顶层依赖 pin；解析后的传递依赖版本另记入 ATR。 |
| 自动化测试 | `mymodules/office_core/tests/**`；不访问 Odoo 数据库或业务模型。 |
| 实施证据 | `docs/implementation/office-engine-m1/CC-OFFICE-M1-001/**`；IHR/ATR 及依赖、格式能力和测试证据。 |
| 契约文档 | 本文件 `docs/context/intent/CC-OFFICE-M1-001.md`；仅经正式 CC 修订流程编辑。 |

目录内部的文件/类/方法由实现选择，但不得改变本 CC 的纯 Python 边界、服务输入/输出、受限 Mapping 契约或能力关闭规则。依赖版本须在本 CC 冻结时明确，不得留作实施者自行决定。

### 4.2 禁止

| 类型 | 详情 |
|---|---|
| 冻结基线 | 禁止修改 SRS V1.0.0、TDD V0.3、Implementation Plan V0.2、TV Plan/报告和结构化证据。 |
| 其他模块 | 禁止修改 Odoo 核心、官方 Addon、`llm_*`、`wd_global_search`、`wd_global_search_llm` 及 `queue`。 |
| Odoo 持久层 | 禁止 ORM 模型、`ir.attachment`、ACL、Record Rule、字段、SQL/schema、Addon Manifest 和数据库状态变化。 |
| 文件安全边界 | 禁止 `sudo`/业务权限扩展、服务器任意路径、无界解压、执行宏/脚本、输入命令/代码、全局忽略 warning 或忽略解析器丢失警告。 |
| 依赖范围 | 禁止修改根 `requirements.txt`、全局升级 Odoo 依赖、安装未在冻结 CC 清单列出的包或系统工具。 |
| 产品范围 | 禁止 AI/业务取数、Mapping UI、用户确认状态、技能、异步调度和输出附件交付。 |

## 5. 必需的行为变更

| ID | 当前行为 | 期望行为 | CC-CHANGE ID |
|---|---|---|---|
| 1 | 无 `office_core` 独立服务契约 | 提供同步、无状态的 inspect/render 候选接口；只接受有界数据和受控策略，不依赖 Odoo/HTTP/Provider | CC-CHANGE-001 |
| 2 | Office 文件内容/格式不能由安全核心可信识别 | 核对扩展、MIME/签名及容器；拒绝损坏、伪装、加密、空、超限、宏或未启用结构 | CC-CHANGE-002 |
| 3 | 无受控结构读取能力 | 对每个 enabled capability 返回稳定结构 ID、必要文本/值/公式/关系，并显式报告未识别项；能力外对象 fail closed | CC-CHANGE-003 |
| 4 | 无受校验的显式映射输入 | 严格执行 TDD Mapping Plan V1，区分缺失/null/空字符串/零值/类型错误，拒绝未知或不可写目标 | CC-CHANGE-004 |
| 5 | 无安全的模板候选写入边界 | 只执行 `set_value` 白名单，在输入模板副本上生成隔离候选；不覆盖原始字节、不创建可交付结果 | CC-CHANGE-005 |
| 6 | 解析器告警和资源超限可能被静默吞掉或无界处理 | 在窄解析作用域用 `warnings.catch_warnings(record=True)` 采集；不使用 `warnings.simplefilter("ignore")`；任何已知结构丢弃/unsupported 告警失败关闭；超预算稳定拒绝/终止并清理 | CC-CHANGE-006 |
| 7 | 核心依赖版本/许可证/目标运行时兼容性未锁定 | 按 §11.1 冻结的直接依赖 pin 生成专用清单；先安装并验证项目 `venv`，通过依赖门禁后再实现核心 | CC-CHANGE-007 |

## 6. 既有行为保留（回归边界）

| ID | 行为 / 契约 | 为什么不得改变 | CC-PRESERVE ID |
|---|---|---|---|
| 1 | 不存在任意服务器文件路径、外部命令和动态 Python 执行入口 | TDD §3、§7 的核心隔离边界及 BR-OFFICE-06 | CC-PRESERVE-001 |
| 2 | 输入模板为只读；处理生成独立候选，不覆盖输入 | BR-OFFICE-03；后续用户原模板必须保留 | CC-PRESERVE-002 |
| 3 | Excel 公式单元格不能成为普通映射写入目标；公式不由本系统计算/刷新 | FR-M1-005、BR-OFFICE-04、TD-006 | CC-PRESERVE-003 |
| 4 | 未验证格式/结构保持关闭并安全拒绝；扩展名或“成功打开”不构成准入 | TDD §4 与 TV Partial 状态 | CC-PRESERVE-004 |
| 5 | 核心不访问 Odoo 数据、用户身份、Provider、HTTP 或 Queue Job | TDD §2、TD-001/008/013 | CC-PRESERVE-005 |
| 6 | 任何失败不得产生或返回可被当成成功交付的部分文件 | BR-OFFICE-10、TDD §7.3 | CC-PRESERVE-006 |

## 7. 适用的 TDD 防护栏（裁剪，不复制）

| TDD 防护栏 / 条款 | 适用性 | 本次落实位置 | 验证方式 |
|---|---|---|---|
| TDD §3.2—3.3 服务契约与 Mapping Plan V1 | 适用 | `office_core` 输入校验/服务结果 | CC-TEST-004/005 |
| TD-003—TD-006 格式及公式约束 | 适用 | capability allowlist、公式目标拒绝、缓存不承诺 | CC-TEST-003/005/006 |
| TD-007 显式 Mapping Plan | 适用 | 仅内部 Python 调用/测试提交；不推断语义 | CC-TEST-004 |
| TD-008 同步有界执行 | 适用 | 资源预算参数、截止时间、超限拒绝；无后台队列 | CC-TEST-007 |
| TDD §7.1 文件安全规则 | 适用 | 容器预检、路径/活动内容拒绝、有限输入及临时清理 | CC-TEST-002/007/008 |
| TDD §7.1 告警处理约束 | 适用 | 不用全局 warning suppression；采集并分类，潜在结构丢失 fail closed | CC-TEST-009 |
| T-TRX-002 / TDD §6 事务边界 | 不适用 | 本 CC 无 ORM/附件/数据库事务 | — |
| Provider payload / TD-002 | 不适用 | 不实现聊天或 Provider 路由 | — |

本 CC 只引用冻结 TDD 的既有条款，不新建技术防护栏或修改防护栏正文。

## 8. 数据 / 迁移影响

| 字段 | 值 |
|---|---|
| 需要迁移 | 否 |
| 迁移脚本 | N/A |
| 数据源 | 有界调用方输入字节和显式 Mapping Plan；不读 Odoo 业务数据 |
| 目标 | 新候选字节和结构摘要；不持久化 |
| 恢复 / 回滚策略 | 仅新增独立包和专用依赖清单；若依赖兼容验证失败，停止并按冻结 CC 的版本变更流程处理，不修改共享根依赖 |
| 验证 | 纯 Python 测试验证输入不变、候选隔离、失败无残留；核对最终锁文件和虚拟环境版本 |

## 9. API / 集成影响

| 字段 | 值 |
|---|---|
| 修改的端点 | 无；不新增公开 API、JSON-RPC 或 HTTP 路由 |
| 向后兼容 | 不改既有运行接口；新增内部 Python 服务契约，不连接任何生产调用者 |
| Adapter 变更 | 无；`office_verify` 和 Odoo/聊天 adapter 归后续 CC |

## 10. 安全 / 权限影响

| 字段 | 值 |
|---|---|
| 新权限 | 无；纯 Python 核心不负责身份认证或权限提升 |
| 变更的 ACL | 无 |
| 敏感数据暴露检查 | 不读取 Odoo 业务数据或凭据；错误中不得包含绝对路径、完整异常回溯、模板业务内容或 Provider 信息。临时数据必须限制在调用方提供的受控内存/临时边界并清理。 |

## 11. 测试契约

测试只证明本 CC 范围内的核心行为；不替代 `office_verify`、ORM/附件、Provider 或浏览器验收。所有测试开始时均为 `NOT RUN`，结果由 ATR/IHR 记录，不在本 CC 草稿中预填通过。

| 测试 ID | 对应变更 | 上游来源 | 测试类型 | 预期结果 | 人工验证 | 原因 |
|---|---|---|---|---|---|---|
| CC-TEST-001 | CC-CHANGE-007 依赖锁定 | Implementation Plan Phase 1；TDD §9 | 环境/依赖审计 | 仅在 CC 冻结后执行：按 §11.1 清单安装；记录 `venv` 解释器路径与 Python 3.11.9、解析后的全部依赖版本；`pip check`、导入和最小合成 `.xlsx/.docx` 读写 smoke test 通过；记录许可证/NOTICE。任何失败阻塞 CC-TEST-002 及核心代码实现 | 否 | 元数据不替代目标 `venv` 实测；防止把 workspace/TV 环境误当成项目运行时 |
| CC-TEST-002 | CC-CHANGE-002 格式与容器安全 | FR-M1-002；AC-02/07；TEST-OFFICE-002 | 单元/安全 | 空、扩展/MIME/签名不一致、截断 ZIP/OLE、损坏/加密/宏/`.xlsm`、未知活动结构和受控 hostile-XML/entity-expansion 样本按稳定错误拒绝或在安全解析后通过；无法证明安全边界时关闭对应 capability | 否 | 验证格式真实性、解析器输入边界和 fail-closed |
| CC-TEST-003 | CC-CHANGE-003 结构读取 | FR-M1-003；AC-03/04；TEST-OFFICE-003/004 | 单元 | 仅 enabled 样本返回稳定 ID、顺序/层级及白名单值；公式只在判定目标不可写所必需时返回标记，不承诺公式缓存；未知对象有标记；关闭 capability 的格式明确拒绝 | 否 | 防止把未解析内容说成完整读取 |
| CC-TEST-004 | CC-CHANGE-004 Mapping schema | FR-M1-007；AC-09；TEST-OFFICE-005 | 单元/边界 | 合法映射可校验；缺键、未知键、版本/指纹错误、重复/未知目标、非法操作、显式 null、类型错误均分类拒绝；空串和零值按契约区分 | 否 | 避免默认值和隐式操作 |
| CC-TEST-005 | CC-CHANGE-001/005 服务契约与候选写入 | FR-M1-004/005；AC-05/06；BR-OFFICE-03/04 | 单元 | 只允许 `set_value`；公式格/不可写目标拒绝；只改候选，输入字节保持不变；候选不返回为可下载/可交付对象；不检验 CC-002 的最终回读结论 | 否 | 验证写入边界而不冒充完整性回读 |
| CC-TEST-006 | CC-CHANGE-003/005 分格式准入 | FR-M1-005/006；AC-06—08；AC-29/30 | 单元/格式矩阵 | 初始候选仅 `.xlsx` 基础单元格和 `.docx` 基础段落/表格文本读写，逐项以样本测试决定是否启用；`.xls/.doc` 写入关闭，`.doc` 读取关闭，`.xls` 仅可按 read-only 测试开放；公式/缓存、扩展、文本框/VML、批注、嵌入对象等均不得默认放行 | 否 | 让能力声明与真实证据一一对应 |
| CC-TEST-007 | CC-CHANGE-006 资源边界/超时 | NFR-OFFICE-08；TEST-OFFICE-011；TDD §2.2/7.2 | 单元/受控进程 | `render_candidate` 必须接收调用方传入的资源预算，其中 `max_file_size` 与 `max_expanded_size` 均为必需正值。容器预检同时核对声明展开大小与实际分块读取累计字节；任一超限即中止，不调用无界 `extractall`，并清理本次临时目录/候选。用小型测试预算验证超限、超时和清理；不在 CC 中猜生产数值 | 否 | 测试限制机制而不把夹具阈值冒充生产预算 |
| CC-TEST-008 | CC-CHANGE-006 失败安全 | BR-OFFICE-10；TDD §7.3 | 单元/失败注入 | 解析器异常、写入/序列化失败、超时或 Mapping 失败均无伪成功、部分候选泄漏或路径/traceback 出现在用户级错误 | 否 | 验证失败关闭和稳定错误 |
| CC-TEST-009 | CC-CHANGE-001/002 纯 Python 边界与告警 | TDD §§2.1/7.1 | 静态检查/单元 | `office_core` 不导入 Odoo/Provider/HTTP/Queue；在最窄解析作用域用 `warnings.catch_warnings(record=True)` 和 `simplefilter("always")` 捕获；`UserWarning` 文本大小写不敏感地包含 `extension` 或 `unsupported`（包括“will be removed/dropped”）时映射为 `OFFICE_UNSUPPORTED_FEATURE` 并不产生候选；其他可能影响结构完整性的未知 warning 默认拒绝，只有显式列入无损白名单的 warning 才可继续；静态检查禁止 `simplefilter("ignore")` | 否 | 防止解析器已告知结构丢失时仍返回成功 |

### 11.1 依赖与格式能力基线

下表是本 CC 冻结的**直接依赖 pin 清单**，不是已安装或已在目标 `venv` 运行通过的证明。版本与 Python/许可证信息依据包发布元数据；安装、解析依赖记录及 smoke test 是任何核心实现的首个门禁。`openpyxl 3.1.5` 不提供未知 OOXML 扩展保留保证；上游长期记录会对 unsupported extensions 发出将被丢弃的 warning，本 CC 必须按 CC-TEST-009 拒绝。

| 包 | 冻结版本 | 用途/格式范围 | 许可与 Python 3.11.9 元数据 | 限制/验证要求 |
|---|---|---|---|---|
| `openpyxl` | `3.1.5` | `.xlsx` 基础单元格读取及非公式单元格受控写入 | MIT；Requires-Python `>=3.8`，发布分类器含 Python 3.11；元数据兼容 3.11.9 | 不承诺保留未知/unsupported OOXML 扩展，不承诺公式缓存；相关 warning 必须拒绝。上游说明默认不防护 XML quadratic blowup / billion laughs；须由有界 XML 预检或经评审的安全解析控制通过 CC-TEST-002/007 证明，不能证明则对应 capability 保持关闭，新增依赖需先走 CC 变更评审。来源：[PyPI 3.1.5](https://pypi.org/project/openpyxl/3.1.5/)、[上游变更记录](https://openpyxl.readthedocs.io/en/stable/changes.html)。 |
| `python-docx` | `1.1.2` | `.docx` 基础段落/表格文本读取及受控写入 | MIT；Requires-Python `>=3.7`，发布分类器含 Python 3.11；元数据兼容 3.11.9 | 元数据兼容不等于目标样本结构保真；拒绝未白名单 OOXML part/文本框/VML等对象。声明依赖 `lxml>=3.1.0` 和 `typing_extensions>=4.9.0`；不作为直接依赖 pin，实际解析版本必须记入 ATR。来源：[PyPI 1.1.2](https://pypi.org/project/python-docx/1.1.2/)、[v1.1.2 上游 pyproject](https://github.com/python-openxml/python-docx/blob/v1.1.2/pyproject.toml)。 |
| `xlrd` | `2.0.1` | `.xls` 只读探测/受限数据读取候选；不用于写入 | PyPI 标记 BSD；Requires-Python 排除至 3.5 的旧版本且允许 3.11，但发布分类器最高列至 3.9；因此只有元数据范围兼容，未得到 3.11.9 分类器或目标运行时实测证明 | 上游明确只读 `.xls`；公式只提取计算结果，不保留公式表达式；宏、图片、图表、嵌入对象、批注、超链接、筛选、透视表、条件格式、数据验证和密码保护不支持。上游许可证文档列出两项许可/署名要求，部署前须把 NOTICE/版权义务核查记录入 ATR。来源：[PyPI 2.0.1](https://pypi.org/project/xlrd/2.0.1/)、[xlrd 格式限制](https://xlrd.readthedocs.io/en/latest/)、[xlrd 许可](https://xlrd.readthedocs.io/en/stable/licenses.html)。 |

`lxml` 和 `typing_extensions` 由 `python-docx` 依赖解析安装；本 CC 不对其另作顶层 pin，但必须将解析后的精确版本记录在依赖 ATR。`xlwt` 不纳入本 CC，因为 `.xls` 写入关闭。`requirements.txt` 应使用上述三项直接依赖精确 pin；实现前只允许用 `./venv/bin/python -m pip install -r mymodules/office_core/requirements.txt` 安装，不得用其他解释器、全局 pip 或临时手动安装命令。该命令在冻结前不得执行。

### 11.2 格式/运行时验证门禁

| 能力/依赖 | 当前已知事实 | 核心实现前必须取得的证据 | 未满足时行为 |
|---|---|---|---|
| 项目 venv | TV/Plan 记录 Python 3.11.9；目标实际路径和版本尚未在本 CC 执行 | 冻结后、代码前核实解释器路径/版本并执行 CC-TEST-001 | 不匹配或 smoke test 失败时停止核心实现 |
| `.xlsx` | 项目库存 `openpyxl 3.0.9`；P0-B 真实样本有缓存清空和未知 OOXML part 丢失 | 依赖 pin 见 §11.1；具体基础单元格读写样本与 warning 行为由 CC-TEST-003/005/006/009 证明 | 只允许通过样本和 warning 门禁的具体结构；其余关闭 |
| `.docx` | 项目 `venv` 无 `python-docx`；workspace Python 3.12 的 1.2.0 单样本结果不能外推 | 依赖 pin 见 §11.1；基础段落/表格读写及未知对象拒绝由 CC-TEST-001/003/005/006 证明 | 未通过具体结构测试的元素拒绝 |
| `.xls` | 当前库存 `xlrd 1.2.0`、`xlwt 1.3.0`；无真实写回证据 | xlrd 2.0.1 只读候选按 §11.1；只有独立读样本测试通过才可启用受限读取；本 CC 中写能力保持关闭 | 默认关闭内容读取；不得写回 |
| `.doc` / LibreOffice | 仅有合成/Alpha 转换证据，未证明真实业务保真 | 本 CC 不引入转换器，不开放内容读写 | 拒绝处理；不得调用 Alpha fallback |
| 依赖闭包 | python-docx 会解析安装 `lxml`、`typing_extensions`；版本未在目标 `venv` 锁定 | 冻结后安装并把解析出的所有版本、许可证/NOTICE 记录到 ATR；不得绕过 requirements 清单 | 依赖安装/许可审计不通过时停止 |

依赖精确版本与元数据证据现已列出；项目 `venv` 的实际安装/导入/read smoke test 是冻结后的代码前门禁，不需要越过冻结门禁提前安装。已知 TV 状态保持 Partial/INCONCLUSIVE 原样，不得在本 CC 中改写。真实样本未通过的格式或结构必须关闭，不得以包可安装代替能力验证。

## 12. 停止条件 / 升级闸门

| ID | 触发条件 | 升级路径 |
|---|---|---|
| 1 | SRS/TDD 对可解析结构、目标位置、类型或输出行为存在冲突 | 停止相关实现；提交 SRS/TDD 正式修订，不在代码中猜测 |
| 2 | 为保留 `.xlsx/.docx/.xls/.doc` 的需求能力必须接受已知数据/结构丢失，或无样本/回读依据开放能力 | 该能力保持关闭；提交技术证据及 SRS 变更需求；不得改成“最佳努力成功” |
| 3 | §11.1 拟锁版本在目标 `venv` 安装/import/read smoke test 失败、许可证/NOTICE 未记录、XML 解析安全需要未列依赖，或要求修改共享 Odoo 根依赖 | 停止核心实现；保持 capability 关闭；按 CC 变更流程评审依赖/安全方案；涉及架构/引擎变更时回到 TDD |
| 4 | 需要导入 Odoo、访问业务模型、增加 addon/ORM、Provider 或队列 | 违反本 CC/TDD 分层；停止并修订 CC 或回到 TDD 评审 |
| 5 | 安全预检、资源预算、超时终止或清理无法可靠实现 | 拒绝该格式/capability；报告证据并暂停受影响实现 |
| 6 | 需要忽略 warning、允许宏/脚本或接受部分成功输出 | 立即停止；不能通过 CC 决策豁免安全边界 |
| 7 | 需要实现 `office_verify`、Odoo 模型、附件读写或聊天确认 | 超出本 CC；交由对应后续阶段 CC，不得提前扩展 |
| 8 | 发现 TDD 技术设计不足或需要改变冻结需求/技术边界，包括现有 XML 解析安全控制不足以满足恶意 XML/资源限制验收 | 停止受影响工作，保持相关格式 capability 关闭；依 workflow 建立授权和上游变更，不在本 CC 中补设计 |

## 13. 完成定义 / 关闭标准

| ID | 标准 | 闸门类型 |
|---|---|---|
| 1 | 本 CC 全部 `CC-CHANGE` 完成，允许文件范围无越界 | 硬闸门 |
| 2 | 所有适用 `CC-TEST` 在目标项目 `venv` 实际运行并有 ATR；无虚构 PASS；适用 TV/样本缺口和关闭 capability 已明确记录 | 硬闸门 |
| 3 | 依赖清单按 §11.1 精确 pin；目标 `venv` 安装、Python 3.11.9 路径、`pip check`、导入/smoke test 及许可证/NOTICE 有证据；不改根 Odoo requirements | 硬闸门；须在核心实现前通过 |
| 4 | `office_core` 纯 Python 静态边界成立；无 ORM、Provider、HTTP、队列和业务访问 | 硬闸门 |
| 5 | 源输入不变；失败不泄漏候选；资源超限、错误类别、告警分类及临时资源清理验证完成 | 硬闸门 |
| 6 | 已启用的每项 capability 有目标样本、允许结构和实测证据；未通过项保持关闭。P0-A/B 的原生 Partial 及 P0-C 的生产资源 INCONCLUSIVE 不被改写 | 硬闸门 |
| 7 | `office_verify`、附件交付或用户 UI 不因本 CC 被声称完成；结果只允许作为未验证候选 | 硬闸门 |
| 8 | IHR、ATR、FR 草稿/关闭结果绑定本 CC、代码基线和上游版本；如有失败/缺失项，按 workflow 完成有效处置后才能冻结 FR | 硬闸门 |

## 14. 追溯矩阵

### 14.1 正向：In-Scope 上游 → CC

| 上游 ID | CC-CHANGE ID | 备注 |
|---|---|---|
| FR-M1-002、BR-OFFICE-02、NFR-OFFICE-02；AC-02/07；TEST-OFFICE-002/011 | CC-CHANGE-002、006 | 容器真实性、恶意/异常输入、资源安全与失败拒绝 |
| FR-M1-003；AC-03/04；TEST-OFFICE-003/004 | CC-CHANGE-003 | 仅声明 enabled 的结构读取 |
| FR-M1-004、FR-M1-007；AC-05/09；TEST-OFFICE-005 | CC-CHANGE-004/005 | 显式 Mapping 验证和候选写入；不含 AC-05 用户确认界面 |
| FR-M1-005、BR-OFFICE-04；AC-06/07；TEST-OFFICE-006/007 | CC-CHANGE-003/005/006 | 公式目标拒绝及逐结构格式准入；最终回读留给 CC-002 |
| FR-M1-006；AC-08/30；TEST-OFFICE-008 | CC-CHANGE-003/006 | Word 仅允许通过验证的结构，未知高级对象拒绝 |
| BR-OFFICE-03/06/10；NFR-OFFICE-04/08 | CC-CHANGE-001/002/005/006 | 原件只读、不可信输入、失败安全、有限资源 |
| TD-001/003—008/013；TDD §§3/4/7；TEST-OFFICE-002—008/011/014 | CC-CHANGE-001—007 | 技术分层、格式门禁、Mapping、同步上限和稳定错误 |

### 14.2 反向：CC → 上游

| CC ID | 上游 ID | 类型 |
|---|---|---|
| CC-CHANGE-001 | TDD §§2.1/3.2；TD-001/008 | TDD / 核心接口及依赖基线 |
| CC-CHANGE-002 | FR-M1-002；BR-OFFICE-02；NFR-OFFICE-02 | SRS / 容器安全 |
| CC-CHANGE-003 | FR-M1-003/005/006；TDD §§3/4 | SRS / TDD / 结构读取和能力门禁 |
| CC-CHANGE-004 | FR-M1-007；TDD §3.3 / TD-007 | SRS / TDD / Mapping schema |
| CC-CHANGE-005 | FR-M1-004/005；BR-OFFICE-03/04；TDD §§3/4 | SRS / TDD / 白名单候选写入 |
| CC-CHANGE-006 | BR-OFFICE-10；NFR-OFFICE-02/08；TDD §7 | SRS / TDD / 失败关闭与限制 |
| CC-CHANGE-007 | TDD §9；Implementation Plan Phase 1 | 技术依赖及已授权项目范围 |

### 14.3 无 DDD 路径

DDD 为 N/A；仅执行 SRS → TDD → CC → TEST 链路，不创建占位 DDD 编号。

## 附录 A — 变更决策（CC-DEC）

| CC-DEC ID | 决策 | 考虑的替代方案 | 理由 |
|---|---|---|---|
| CC-DEC-001 | 将无状态纯 Python 核心放在独立根 `mymodules/office_core/`；首 CC 不建立 Odoo addon manifest 或模型 | 将核心直接写进某个现有 Odoo Addon | 保持 TDD 规定的核心无 ORM/业务生命周期；允许纯 Python 独立测试。若运行时 import/package 布局无法成立，停止并提交 TDD 评审，不自行移入 addon。 |
| CC-DEC-002 | 直接依赖精确 pin 仅置于 `mymodules/office_core/requirements.txt`，不改 Odoo 根依赖文件；冻结版本见 §11.1，传递依赖版本记入 ATR | 将依赖并入根 `requirements.txt` 或在本 CC 中另造完整锁工具链 | 限定变更和安装面；目标 venv 安装和 smoke test 先于核心代码作为硬门禁。 |
| CC-DEC-003 | 初始候选能力仅为 `.xlsx` 基础单元格与 `.docx` 基础段落/表格文本读写；逐项通过样本后才开放，`.xls/.doc` 写能力关闭 | 对扩展名整体启用库默认行为 | TV 仍为 Partial 且旧格式未验证；格式名不能代替结构保真证据。 |
| CC-DEC-004 | 捕获/分类解析器 warnings；明确的 unsupported/extension 丢弃或降级告警触发 `OFFICE_UNSUPPORTED_FEATURE`；不使用全局忽略 warning | 忽略所有 warning 以减少噪声 | 静默吞掉丢失证据会破坏文件完整性要求。 |
| CC-DEC-005 | `render_candidate` 使用必填资源预算对象，其中包括 `max_file_size` 与 `max_expanded_size`；ZIP 容器同时校验声明与实际读取量，超限立即中止清理 | 从代码常量推测生产阈值或无界解压 | 由调用方策略提供阈值；CC 只验证执行机制，不虚构生产资源预算。 |

## 附录 B — 模板使用指南

本 CC 是纯 Python 新功能/安全底座；重点验收 SRS FR、格式 fail-closed、资源边界、错误契约及 TDD 层次。人工 UI 验证不适用；性能/目标运行时证据只覆盖 CC 实际声明启用的能力，不外推生产容量。

## 附录 C — 术语表

| 术语 | 定义 |
|---|---|
| Candidate | `office_core` 写出的隔离候选字节，尚未通过独立 `office_verify`，不可预览、下载或交付。 |
| Capability | 对某格式/对象/读写操作的显式服务端允许声明；需由目标环境和样本证据支撑。 |
| Fail closed | 检查不确定、超限、未识别或能力未启用时停止，不返回成功输出。 |
| Mapping Plan | TDD §3.3 定义的显式目标与值输入；不是业务字段映射推断或可执行脚本。 |

## 附录 D — 版本历史

| 版本 | 日期 | 变更说明 | 状态 |
|---|---|---|---|
| v0.1 | 2026-10-20 | 基于 SRS V1.0.0、TDD V0.3 和 Implementation Plan V0.2 起草。 | Draft |
| v0.2 | 2026-10-20 | 吸收评审意见：补充拟锁依赖及上游证据、首期格式候选白名单、解析 warning 失败关闭规则、资源预算契约和项目 `venv` 安装门禁；明确包元数据兼容不等于目标运行时实测，未通过样本能力继续关闭。 | Draft — 待评审；未授权实施 |
| v1.0.0 | 2026-10-20 | 业务负责人批准冻结；确认直接依赖 pin 为 `openpyxl==3.1.5`、`python-docx==1.1.2`、`xlrd==2.0.1`，实际 venv smoke test 作为核心代码前门禁。 | Frozen |
