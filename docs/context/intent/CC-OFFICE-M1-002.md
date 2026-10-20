<!-- 使用 Coding/CC 模板；v1.0.0 Frozen，业务负责人已批准实施。 -->

# CC-OFFICE-M1-002 — Office 独立回读校验引擎

## 0. Governance

| 字段 | 值 |
|---|---|
| Coding Contract | `CC-OFFICE-M1-002` |
| 版本 | `v1.0.0` |
| 状态 | **Frozen — 业务负责人于 2026-10-20 批准；允许按本 CC 实施** |
| Intent ID | `OFFICE-ENGINE-M1-READBACK-VERIFICATION` |
| 模块 | `office_verify`（纯 Python 独立回读包） |
| 工作类型 | 新功能 / 文件完整性验证 |
| 上游 SRS | [SRS_office_document_automation](../../requirement/SRS_office_document_automation.md) V1.0.0 Frozen |
| 上游 DDD | N/A；沿用 M1 DDD N/A 决策 |
| 上游 TDD | [TDD_office_engine_m1](../../design/TDD_office_engine_m1.md) V0.3 Frozen |
| 上游 Implementation Plan | [IMPLEMENTATION_PLAN_office_engine_m1](../../implementation/IMPLEMENTATION_PLAN_office_engine_m1.md) V0.2 Frozen |
| 前置 CC | `CC-OFFICE-M1-001`；关闭评估 [FR-OFFICE-ENGINE-M1-CORE-FOUNDATION](../../implementation/office-engine-m1/CC-OFFICE-M1-001/FR-OFFICE-ENGINE-M1-CORE-FOUNDATION.md) SATISFIED |
| 目标 | 增加与 `office_core` 写入引擎独立的同步回读校验服务；候选文件只有通过校验才具备后续交付评估资格。 |
| 批准 / 冻结 | 业务负责人于 2026-10-20 批准冻结并进入实施；依赖固定为当前 `venv` 已安装的 `lxml==4.9.3`，不得升级或新增依赖。 |

**阶段门禁：** 本 CC 对应 Implementation Plan V0.2 Phase 2。已获批准并冻结，可实施 §3 范围；不得安装/升级依赖或开放未准入格式能力。

## 1. 变更概述

**目标：** 对原始 Office 字节、`office_core` 生成的候选字节、显式 Mapping Plan 和已启用格式策略进行独立回读；验证输出容器和结构、映射目标值、公式表达式及本次明确要求保留的结构。完整性关键检查失败或无法完成时，返回稳定失败结果；允许的非关键差异可作为结构化 Warning 随完整 PASS 返回。

**背景：** `office_core` 会生成隔离候选，但候选尚未经过独立完整性检查，不可交付。M1 Phase 2 需要不同于写入库高层对象模型的回读路径，主动发现目标值错误、公式变化、结构损坏和伪成功输出。

## 2. 上游基线与追溯

### 2.1 SRS 引用

| SRS ID | 标题 | 与本次 CC 的相关性 |
|---|---|---|
| FR-M1-005 | Excel 完整性与公式保护 | 回读验证公式表达式、目标值和明示结构；不计算公式或承诺缓存刷新。 |
| FR-M1-006 | Word 完整性保护 | 对启用的 `.docx` 结构检查目标值和结构完整性；未启用对象保持拒绝。 |
| FR-M1-009 | 输出回读验证 | 本 CC 建立纯 Python 验证核心，不含附件交付或 UI。 |
| BR-OFFICE-02/03/04/10 | 文件安全、原件保护、公式保护及失败处理 | 仅覆盖回读检查、失败关闭和原件只读。 |
| NFR-OFFICE-02/04/08 | 安全、完整性、资源限制 | 有界读取及不确定时拒绝；生产资源阈值仍按目标环境另定。 |
| AC-06/08/23/29/30/31 | 格式、公式、回读与输出要求 | 只证明本 CC 声明的格式/结构能力；不代表端到端结果交付或任意模板兼容。 |

AC-05 的用户确认、AC-10/17 附件持久化与授权交付不属于本 CC。

### 2.2 DDD 引用

N/A。该独立纯 Python 回读服务不定义业务聚合或领域状态。

### 2.3 TDD 引用

| TDD ID / 章节 | 标题 | 相关性 |
|---|---|---|
| TD-003—006、TD-013 | 格式能力、公式语义、实施顺序 | 作为回读的格式和保留基线；未验证结构继续关闭。 |
| TDD §§3.2、3.4 | `office_verify.verify_output` 与稳定结果/错误契约 | 回读接口的权威技术契约。 |
| TDD §4 | 格式能力及启用策略 | 仅检查当前明确启用的能力；旧格式和高级对象不默认开放。 |
| TDD §§6—7 | 同步生命周期、资源限制和错误处理 | 有界、同步、无附件副作用；失败不产生交付结果。 |
| TDD §8 / TEST-OFFICE-006—008、010、011、014 | 验收与追踪 | 按本 CC 明确选定的验证行为裁剪。 |
| Implementation Plan Phase 2 | 独立回读校验引擎 | 要求不同于写入引擎的检查路径、篡改检测及格式回读矩阵。 |

### 2.4 事件报告

不适用；本 CC 为 Phase 2 新功能。

### 2.5 追溯规则

本 CC 仅授权对已生成候选做回读检查。不实现映射推断、写入、附件持久化或用户交付。如回读需要改变 TDD/SRS 的映射语义、格式范围、缓存承诺或事务流程，必须停止并升级。

## 3. 范围冻结

### 3.1 在范围内（In Scope）

- 在 `mymodules/office_verify/` 建立独立纯 Python 包和同步 `verify_output` 公开接口；输入为有界源字节、候选字节、TDD Mapping Plan V1、格式/结构策略及资源预算；输出仅为可序列化回读报告或稳定失败。
- 使用独立 ZIP/XML 回读路径，重新打开并验证容器完整性、XML 安全边界、声明格式、目标值及基线策略中明确列出的结构。
- 所有 XML 解析器必须显式使用安全设置：`resolve_entities=False`、`load_dtd=False`、`no_network=True`、`huge_tree=False`、`recover=False`；检测到 DOCTYPE/DTD、实体声明或未解析的自定义实体引用时拒绝该文件。XML 规范预定义的 `amp`、`lt`、`gt`、`apos`、`quot` 转义按正常 XML 语法接受。安全设置不得依赖 lxml 默认值。
- 对 `.xlsx`：仅覆盖 CC-001 首期白名单中的基础单元格目标回读，以及 workbook/sheet 关系、公式表达式和明确声明的结构检查。逐一读取 Mapping Plan 目标；公式表达式须与源文件一致。缓存单独报告状态，不把缓存值当公式值，不计算/刷新缓存。
- 对 `.docx`：仅覆盖 CC-001 首期白名单中的正文基础段落/表格文本目标回读。目标段落文本按 XML 文档顺序串接其 `<w:t>` 节点文本，比较 Unicode 纯文本，不比较 run/DOM 切分；表格按段落目标逐项校验，不把整张表格 DOM 当作目标值。目标内出现当前白名单未定义的制表符、换行控制、域、修订或其他活动结构时拒绝，不静默丢弃。未验证的文本框、VML、图片、页眉页脚、批注、嵌入对象等不得因回读模块存在而自动开放。
- 对 Mapping Plan：检查 schema/version/template fingerprint 的形状与目标；验证每个受支持目标的实际输出值与映射 `type/data` 语义一致；区分字符串空值、数字零、布尔 false 与显式 null；未知、重复、缺失或无法定位的目标失败关闭。
- 对公式：任何原公式表达式缺失、改变、新增或目标公式被写入时失败；公式缓存以单独状态报告（存在/缺失/变化），不得声称已经计算。缓存变化本身不使本 CC 的完整性校验失败：公式表达式未变时返回 PASS，并对对应公式设置 `cached_value_changed: true`；不返回缓存明文。该 PASS 仅表示公式/结构完整性检查通过，不代表缓存适合业务交付或已完成计算；后续调用方按 TDD §4、SRS OPEN-OFFICE-03 的策略决定交付适用性。本 CC 不自行决定重算或拒绝交付。
- 差异分级：完整性关键差异为 Fatal，导致验证失败且不得返回完整 PASS；不影响已声明语义/结构契约的差异可作为 Warning 随 PASS 返回。Warning 至少包含稳定差异类别和元素标识，不含文档原文。无法判断差异是否影响已声明契约时一律按 Fatal 处理。
- Fatal 示例：目标值缺失/错误、公式新增/删除/表达式变化、已声明必须保留的合并区域或关系结构丢失、策略要求保留的部件/图片/页眉缺失、容器/XML 损坏、未知活动部件、解析或资源预算失败。
- Warning 示例：不在本 CC 保留契约内的非目标字体/颜色等样式变化、非目标属性/节点的无语义重排，或 XML `xml:space` 属性不同但目标纯文本逐字相同且策略结构不变。若样式/属性/部件已在输入 capability policy 中声明为必须保留，则其变化提升为 Fatal。
- 对格式和结构：输出格式必须与输入相符；本 CC 不支持格式升级。`.xls/.doc`、宏格式及未启用结构继续明确拒绝。两个 CC-001 已提供真实样本仍按既有 capability 策略拒绝，不将被拒绝的样本包装为验证通过。
- 回读错误和差异使用稳定、脱敏的错误码/摘要；报告不含 Office 原文、绝对路径、完整异常回溯或业务数据。
- 只读处理源字节和候选字节；不修改候选，不生成第二份输出，不创建 `ir.attachment`、下载链接或“已交付”状态。
- 资源预算至少包含输入/输出文件大小、展开字节、条目数、单条目大小、XML 节点量和墙钟限制；超过限制或无法完整回读时拒绝，不留下部分 PASS。
- 建立纯 Python 测试、失败注入和格式能力矩阵；IHR/ATR 证据放于 `docs/implementation/office-engine-m1/CC-OFFICE-M1-002/`。

### 3.2 超出范围（Out of Scope）

- 修改、导入或复用 `office_core` 的私有函数、解析器对象、内部状态或缓存；回读模块作为独立包，不依赖 `office_core` 包代码。测试层可组合两个公开服务来构造端到端测试输入，但 `office_verify` 本体不得导入 `office_core`。
- 修改 `office_core` 写入行为、Mapping schema、资源预算语义或支持结构。
- Odoo Addon、ORM、`env`、业务模型查询、ACL、聊天、Provider、Queue Job、HTTP、前端、附件创建/删除、事务、任务状态或下载链接。
- LibreOffice、Office 桌面程序、PDF 转换、宏/脚本执行、网络或服务器路径访问。
- 启用 `.xls/.doc/.xlsm`、公式计算/缓存重算、条件格式、外链、图片、文本框/VML、页眉页脚、嵌入对象或其他未验证结构。
- 生产容量/并发承诺；不重新执行 TV，也不覆盖原始 TV/P0 报告和证据。
- 修改 SRS、TDD、Implementation Plan、官方 Odoo 源码/Addons，或关闭 M1/其他 CC。

### 3.3 非目标（Non-Goals）

- 本 CC 不证明候选文件满足业务内容正确性或用户已确认 Mapping Plan。
- 回读 PASS 只表示当前策略中所声明的完整性检查通过；它不授予用户/附件访问权、不创建交付授权，也不等同于 Odoo 最终可下载。
- 不以“ZIP 可打开”“XML 可解析”或“Office 客户端能打开”代替目标值、公式和结构逐项检查。
- 不支持对任意未声明结构做通用字节相等比较；只比较稳定、明确纳入 capability 的语义结构。

### 3.4 仅限范围追溯

本 CC 纳入的 SRS/TDD 编号均须映射到 `CC-CHANGE`。未纳入的 M1 需求不因本 CC 获得实施授权。

## 4. 变更边界

### 4.1 允许

| 类型 | 详情 |
|---|---|
| 新包 | `mymodules/office_verify/**`；仅独立 Python 回读服务、测试和直接依赖清单。 |
| 实施证据 | `docs/implementation/office-engine-m1/CC-OFFICE-M1-002/**`。 |
| 本 CC | `docs/context/intent/CC-OFFICE-M1-002.md`；仅按正式修订流程修改。 |

冻结依赖：`lxml==4.9.3`，作为 `office_verify` 的直接依赖；当前项目 `venv` 已安装该版本，元数据许可证为 BSD-3-Clause。按负责人决定不升级、不试装其他版本。实现只使用显式配置的 `lxml.etree.XMLParser`，固定传入 `resolve_entities=False`、`load_dtd=False`、`no_network=True`、`huge_tree=False`、`recover=False`；拒绝 DOCTYPE/DTD 和未解析的自定义实体引用，不使用 `iterparse` 或 `ETCompatXMLParser`。此选择不构成对 lxml 其他默认 parser/API 安全性的通用保证。

### 4.2 禁止

| 类型 | 详情 |
|---|---|
| 其他模块 | 禁止改动 `office_core`、Odoo 核心或 Addons、`llm_*`、Global Search、Queue。 |
| Odoo / 产品集成 | 禁止 ORM、数据库、附件、聊天、Provider、HTTP、UI、队列或业务数据访问。 |
| 文件输出 | 禁止改写候选、生成可下载结果、持久化、链接或交付状态。 |
| 格式能力 | 禁止将拒绝的真实模板或未验证高级部件改成“最佳努力通过”；禁止支持旧格式、宏及公式缓存重算。 |
| 安全 | 禁止无界 ZIP/XML 读取、外部资源解析、网络/路径访问、忽略差异或异常。 |
| 依赖 | 冻结前禁止安装；实施时不得引入未冻结依赖或修改根 Odoo requirements。 |
| 上游基线 | 禁止修改冻结 SRS/TDD/Implementation Plan、TV 和 CC-001。 |

## 5. 必需的行为变更

| ID | 当前行为 | 期望行为 | CC-CHANGE ID |
|---|---|---|---|
| 1 | 候选文件尚无独立回读服务 | 提供同步、无状态、纯 Python `verify_output` 契约；返回独立验证报告或稳定失败 | CC-CHANGE-001 |
| 2 | 写入引擎输出尚无独立容器/结构回读 | 用 ZIP/XML 独立路径有界重开，检查输出容器、格式及能力策略声明的结构 | CC-CHANGE-002 |
| 3 | 映射目标值没有从候选文件独立读取确认 | 对每个支持的 Mapping Plan 目标回读输出值；值缺失/不符/无法定位即失败 | CC-CHANGE-003 |
| 4 | 公式表达式和缓存未由回读路径分别核验 | 比较源/候选公式表达式并报告缓存状态；表达式变化失败；缓存变化不单独失败，设置 `cached_value_changed`；不执行计算/刷新 | CC-CHANGE-004 |
| 5 | 校验结果可能把部分检查误报为成功 | 全部关键检查完成且通过时返回完整 PASS，可附带受控 Warning；Fatal/解析/预算失败或差异分类不确定时失败关闭，错误摘要脱敏 | CC-CHANGE-005 |
| 6 | 回读模块的格式边界和依赖/模块隔离未固定 | 建立 `.xlsx/.docx` 已启用结构的能力矩阵；旧格式和未准入对象拒绝；无 `office_core` 导入依赖 | CC-CHANGE-006 |

## 6. 既有行为保留（回归边界）

| ID | 行为 / 契约 | 为什么不得改变 | CC-PRESERVE ID |
|---|---|---|---|
| 1 | 输入源和候选内容只读 | 回读不得掩盖或修复候选差异 | CC-PRESERVE-001 |
| 2 | `office_verify` 与 `office_core` 独立，且不导入 Odoo/Provider/HTTP/Queue | TDD 分层；保持核心可独立验证 | CC-PRESERVE-002 |
| 3 | 未验证格式/结构保持关闭 | TV 仍为 Partial；回读不能提升未验证能力 | CC-PRESERVE-003 |
| 4 | 公式文本不得被覆盖；公式缓存不被当作计算结果，缓存改变单独报告 | SRS FR-M1-005 / TDD TD-006 | CC-PRESERVE-004 |
| 5 | 失败输出不得被视为可交付 | 回读 PASS 不等于权限或附件交付 | CC-PRESERVE-005 |
| 6 | 错误和报告不泄露模板业务内容、路径或 traceback | 文件内容可能包含敏感业务数据 | CC-PRESERVE-006 |

## 7. 适用的 TDD 防护栏

| TDD 来源 | 适用性 | 本次落实 | 验证 |
|---|---|---|---|
| TDD §3.2 `verify_output` 契约 | 适用 | 输入/输出、Mapping、格式策略和稳定结果 | CC-TEST-001—003 |
| TDD §§3.3—3.4 Mapping 与错误契约 | 适用 | 只验证显式 Mapping，不推断业务来源；未知/重复/类型边界拒绝 | CC-TEST-003/008 |
| TDD §4 格式能力表 | 适用 | 只验证当前 enabled 结构；未启用格式 fail closed | CC-TEST-007 |
| TDD §7.1 有界 ZIP/XML 与安全解析 | 适用 | 限制容器、路径、条目、展开量；所有 lxml parser 显式禁用实体解析、DTD、网络和恢复模式，并拒绝 DTD/entity | CC-TEST-002/006 |
| TDD §7.2 同步资源预算 | 适用 | 同步运行、有界超时、超限即拒绝 | CC-TEST-006 |
| TDD §7.3 错误与失败安全 | 适用 | 结构/公式/映射差异稳定失败；无部分通过 | CC-TEST-008 |
| TDD TD-013 / Plan Phase 2 | 适用 | 独立模块和不同于写入高层库的 XML 回读路径 | CC-TEST-001/004/005 |

## 8. 数据 / 迁移影响

| 字段 | 值 |
|---|---|
| 需要迁移 | 否 |
| 迁移脚本 | N/A |
| 数据源 | 调用方传入的有界源字节、候选字节和 Mapping Plan；不读取 Odoo/业务数据 |
| 目标 | 内存中的验证报告；不持久化、不改写文件 |
| 恢复 / 回滚 | 移除独立新包即可；不得变更 `office_core` 数据或行为 |
| 验证 | 单元测试确认源/候选字节哈希不变、验证器无写文件副作用 |

## 9. API / 集成影响

| 字段 | 值 |
|---|---|
| 新接口 | `office_verify.verify_output`（仅内部同步 Python API） |
| 公开 HTTP/JSON-RPC | 无 |
| `office_core` 修改 | 无；测试可组合公开 API，验证器运行包不导入 `office_core` |
| 向后兼容 | 不改现有 API；独立包由后续封装方显式调用 |
| 交付语义 | 验证通过不是最终附件交付或用户授权 |

## 10. 安全 / 权限影响

| 字段 | 值 |
|---|---|
| 新权限 / ACL | 无；纯 Python 不负责身份或授权 |
| 输入 | 只接收有界 `bytes`、显式结构化 Mapping/策略；不接收路径/命令/URL |
| XML/ZIP | 禁用实体解析、外部网络和 DTD；不得无界展开或 `extractall` |
| 敏感数据 | 报告仅返回检查状态、稳定元素标识和脱敏差异类别；错误不包含原文、绝对路径或 traceback |
| 输出 | 无写入/持久化，不生成候选或下载链接 |

## 11. 测试契约

测试执行前的初始状态为 `NOT RUN`；表中定义冻结后的测试契约。本次实施结果只通过 ATR 记录，不回写为预设 PASS。

| 测试 ID | 对应变更 | 上游来源 | 类型 | 预期结果 | 人工验证 | 原因 |
|---|---|---|---|---|---|---|
| CC-TEST-001 | CC-CHANGE-001/006 | TDD §3.2；Plan Phase 2 | 静态/单元 | `office_verify` 不导入 `office_core`、Odoo、Provider、HTTP 或 Queue；只暴露有版本契约的纯函数；直接依赖精确 pin 为 `lxml==4.9.3`，当前目标 venv 导入、Python 3.11.9、依赖闭包和 BSD-3-Clause 许可证据记录齐全；不安装或升级依赖 | 否 | 证明物理隔离、解析依赖基线和运行基线 |
| CC-TEST-002 | CC-CHANGE-002/005 | NFR-OFFICE-02；TDD §7 | 单元/安全 | 空、伪装、截断/CRC 错误 ZIP、路径异常、超限、DOCTYPE/DTD、内部/外部自定义实体、网络实体、未知活动部件均稳定拒绝；标准 XML 预定义实体转义可正常读取。测试证据确认 parser 显式配置 `resolve_entities=False`、`load_dtd=False`、`no_network=True`、`huge_tree=False`、`recover=False`；无本地文件读取、网络请求或部分报告 | 否 | 验证独立解析路径的安全边界 |
| CC-TEST-003 | CC-CHANGE-003 | FR-M1-009；AC-23；TDD §4 | 单元 | 合法 XLSX/DOCX Mapping 目标回读语义值；缺失、错误值、重复/未知/不可解析目标失败。DOCX 文本跨多个 `<w:r>/<w:t>` 分片时，按顺序串接纯文本后精确匹配，不要求 DOM/run 切分一致 | 否 | 防止写入库成功但目标值不正确，并避免 XML 节点划分引发假失败 |
| CC-TEST-004 | CC-CHANGE-004 | FR-M1-005；AC-06/23 | 单元/篡改 | 公式新增、删除、表达式变化或公式目标写入均 Fatal；公式未变而缓存变化时验证状态 PASS，报告 `cached_value_changed: true`，不报告缓存明文、不执行重算且不以缓存代替公式 | 否 | 检出公式破坏并将缓存变化与公式完整性分离 |
| CC-TEST-005 | CC-CHANGE-002/004/005 | TDD §4；Plan Phase 2 | 单元/篡改 | 必需结构/目标/公式丢失或改变为 Fatal；不在保留契约内的非目标样式属性差异、以及纯文本相同且结构语义不变的 `xml:space` 差异为 Warning 并可随完整 PASS 返回；未知/无法分类差异一律 Fatal；至少一项回读使用不同于写入高层库的路径 | 否 | 明确结构差异严重级别，防止误报或漏报 |
| CC-TEST-006 | CC-CHANGE-005 | TDD §§7.2—7.3 | 资源/失败注入 | 文件/展开/条目/XML/时间超预算或解析中断时稳定失败，无超时悬挂和部分 PASS；不启动转换器 | 否 | 保证同步资源边界 |
| CC-TEST-007 | CC-CHANGE-006 | FR-M1-005/006；TDD §4；CC-001 §3.1/CC-DEC-003 | 格式矩阵 | 初始能力严格限于 `.xlsx` 基础单元格值和非公式目标、`.docx` 正文基础段落/表格文本目标；回读仅检查对应值及本 CC 明确列出的结构。`.xls/.doc/.xlsm`、公式格写入、未知 OOXML 扩展及条件格式、外链、图片、文本框/VML、页眉页脚、批注、嵌入对象等未准入对象按策略拒绝，不因本 CC 开放 | 否 | 与 CC-001 首期候选能力一致，保持 TV 未验证能力关闭 |
| CC-TEST-008 | CC-CHANGE-003/005 | TDD §3.3—3.4 | 映射/错误边界 | 缺字段、未知键、显式 null、空串、0/false、类型不符、公式目标、哈希不符分别结果明确；报告错误脱敏且不能表示交付成功 | 否 | 验证错误契约和数据最小化 |
| CC-TEST-009 | CC-PRESERVE-001/002/005 | TDD §§2、3、6 | 回归/静态 | 源和候选哈希不变；验证器不创建文件、不依赖 `office_core`，不得返回下载/附件或权限结论 | 否 | 验证只读和模块隔离 |

### 11.1 依赖与目标运行时基线（Frozen）

| 包 | 锁定版本 | 用途 | 锁定状态 |
|---|---|---|---|
| `lxml` | `4.9.3`（冻结精确 pin） | 独立 XML 回读；直接依赖而非依赖 `office_core` 的传递安装 | 项目目标 `venv` 已安装；Python 3.11.9 导入和 BSD-3-Clause 元数据已确认。不得升级；实施仅使用 CC 指定的显式安全 `XMLParser` 配置，并运行 DTD/XXE 拒绝测试。 |

不引入 `openpyxl`、`python-docx` 或 LibreOffice 作为验证主路径，以维持与写入器的解析路径独立。本 CC 冻结后也不得变更 lxml 版本；如实施中证明 4.9.3 与显式安全配置无法满足契约，按 §12 停止并提交上游评审，不在本 CC 内试升级。

## 12. 停止条件 / 升级闸门

| ID | 触发条件 | 升级路径 |
|---|---|---|
| 1 | 回读语义无法由冻结 Mapping Plan/格式策略明确决定，或 XML 差异无法归类为 Fatal/Warning | 停止相关检查；按 Fatal 拒绝；如需改变 TDD/SRS 语义则提交上游澄清，不自行猜测 |
| 2 | 需要导入 `office_core` 私有解析状态或让 `office_verify` 修改候选 | 停止；重新评审 TDD/CC 边界 |
| 3 | `lxml==4.9.3` 的显式安全解析设置、DTD/XXE 测试、依赖闭包或许可证证据未通过 | 保持能力关闭并停止受影响实现；不得升级依赖。提交 CC/TDD 变更评审，另行授权后处理 |
| 4 | 真实样本/格式对象未通过验证，或公式缓存必须重算才能满足契约 | 拒绝该 capability；若业务要求必须支持，回 SRS/TDD 变更 |
| 5 | 资源限制、错误脱敏、完整性差异分级、Warning 约束或失败关闭不可可靠实现 | 停止相应格式能力，保留证据并回评技术设计 |
| 6 | 需要附件持久化、Odoo/聊天/Provider/队列或公开接口 | 超出本 CC；移交对应计划阶段，不得扩展 |

## 13. 完成定义 / 关闭标准

| ID | 标准 | 闸门类型 |
|---|---|---|
| 1 | 所有 CC-CHANGE 完成，只有本 CC 允许文件变化 | 硬闸门 |
| 2 | CC-TEST-001—009 在目标 venv 有当前基线 ATR；失败/跳过项有合法处置 | 硬闸门 |
| 3 | `office_verify` 无 `office_core`/Odoo/Provider/HTTP/Queue 运行导入依赖，且用于关键检查的回读路径与写入高层库独立 | 硬闸门 |
| 4 | 输出格式、目标值、公式表达式、必需结构和不支持对象策略均有明确回读证据 | 硬闸门 |
| 5 | 公式缓存与公式表达式分开报告；缓存变化按约定输出 `cached_value_changed`；无重算或缓存保证的虚假声明 | 硬闸门 |
| 6 | 安全 parser 设置和恶意 XML 测试通过；安全预算、脱敏错误、无 Fatal 的完整 PASS/受控 Warning、输入/候选只读证据齐全 | 硬闸门 |
| 7 | `.xls/.doc/.xlsm`、未验证真实模板与高级对象没有被意外开放 | 硬闸门 |
| 8 | IHR、ATR、HVR（按 CC 为 N/A）和 FR 均绑定本 CC/基线；不声称 Odoo 附件交付或用户验收完成 | 硬闸门 |

## 14. 追溯矩阵

### 14.1 正向：上游 → CC

| 上游 ID | CC-CHANGE | 备注 |
|---|---|---|
| FR-M1-009；AC-23；TEST-OFFICE-010 | CC-CHANGE-001/002/005 | 独立回读 API、差异报告及失败关闭 |
| FR-M1-005；BR-OFFICE-04；AC-06/23 | CC-CHANGE-003/004 | 目标值、公式表达式与缓存状态分别验证 |
| FR-M1-006；AC-08/30 | CC-CHANGE-002/006 | 仅当前 enabled Word 结构；高级对象保持关闭 |
| FR-M1-008；AC-31 | CC-CHANGE-005 | 校验范围不涵盖格式升级或附件交付 |
| NFR-OFFICE-02/04/08；TDD §§6—7 | CC-CHANGE-002/005 | 有界解析、敏感数据最小化和安全拒绝 |
| TD-003—006/013；Implementation Plan Phase 2 | CC-CHANGE-001—006 | 独立模块、回读路径与 Phase 2 门禁 |

### 14.2 反向：CC → 上游

| CC ID | 上游 ID | 类型 |
|---|---|---|
| CC-CHANGE-001 | TDD §3.2；TD-013 | API/分层 |
| CC-CHANGE-002 | TDD §§4、7；NFR-OFFICE-02 | 容器/结构安全 |
| CC-CHANGE-003 | FR-M1-009；AC-23；TEST-OFFICE-010 | 目标值回读 |
| CC-CHANGE-004 | FR-M1-005；AC-06/23；TD-006 | 公式表达式/缓存 |
| CC-CHANGE-005 | TDD §§3.4、6—7；BR-OFFICE-10 | 失败关闭和稳定报告 |
| CC-CHANGE-006 | TDD §4；TV P0-A/B 状态 | 格式准入和能力关闭 |

### 14.3 无 DDD 路径

DDD 为 N/A；不创建占位领域编号。

## 附录 A — CC-DEC

| CC-DEC ID | 拟议决策 | 替代方案 | 理由/状态 |
|---|---|---|---|
| CC-DEC-001 | 回读包只用公开字节/JSON 契约，不从 `office_core` 导入任何代码 | 重用 `office_core` parser/inspection 私有对象 | 保证真正独立；已冻结 |
| CC-DEC-002 | 用独立 ZIP/XML 解析完成关键回读；依赖固定为当前 venv 已安装的 `lxml==4.9.3`；每个 parser 显式禁用实体/DTD/网络解析并拒绝 DTD/entity | 用 openpyxl/python-docx 重新打开文件；升级 lxml | 负责人明确要求不升级；以不调用默认易受影响 parser、固定安全参数及 DTD/XXE 自动化测试满足本 CC 安全边界。未通过测试即停止，不在本 CC 内变更依赖 |
| CC-DEC-003 | 公式表达式必须相同；缓存变化不单独导致验证失败，报告 `cached_value_changed`，不重算 | 将缓存当成公式文本；缓存变化自动失败或自动重算 | 遵循 SRS/TDD 的表达式保护和缓存非承诺；完整性 PASS 不代表缓存可交付，交由调用方策略 |
| CC-DEC-004 | DOCX 目标值按段落文本目标抽取有序 `<w:t>` 纯文本比对，不比 DOM/run 结构 | 要求 Word XML/run/DOM 完全相同 | 允许 run 分片和序列化差异，同时保持目标文本语义可验证 |
| CC-DEC-005 | Fatal 差异失败；契约外非目标格式属性变化可作为 Warning 随完整 PASS 返回；无法分类按 Fatal | 所有字节/属性变化一律失败，或所有未识别变化忽略 | 将强制保真对象与非目标序列化差异分开；不扩大 capability |
| CC-DEC-006 | 初始验证范围继承 CC-001：`.xlsx` 基础单元格/非公式目标、`.docx` 正文基础段落/表格文本；其他能力继续关闭 | 仅按扩展名开放整个格式 | 格式名不等于结构通过；保持与 CC-001 及 TV 状态一致 |

## 附录 B — 版本历史

| 版本 | 日期 | 变更说明 | 状态 |
|---|---|---|---|
| v0.1 | 2026-10-20 | 基于 TDD V0.3、Implementation Plan V0.2 与 CC-001 FR 起草 Phase 2 独立回读范围。 | Draft — 待评审；未授权实施 |
| v0.2 | 2026-10-20 | 吸收评审意见：明确 lxml 安全解析设置、初始格式能力、DOCX 目标纯文本比对、Fatal/Warning 和公式缓存变化报告语义。 | Draft — 待评审；未授权实施 |
| v1.0.0 | 2026-10-20 | 负责人批准冻结并进入实施；依赖精确锁定为现有 `lxml==4.9.3`，禁止升级；显式安全 parser 配置及拒绝 DTD/XXE 作为实施与自动化验收门禁。 | Frozen — 已批准实施 |
