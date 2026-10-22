# CC-OFFICE-M1-PRE-ROUTE-FIX — Provider 前 Office 类型伪装拦截修复

## 0. 文档治理

| 字段 | 值 |
|---|---|
| Coding Contract | `CC-OFFICE-M1-PRE-ROUTE-FIX` |
| 版本 | `v1.0.0 Frozen` |
| 状态 | **FROZEN — 负责人于 2026-10-21 批准冻结并进入实施** |
| Intent ID | `OFFICE-ENGINE-M1-PRE-ROUTE-FIX` |
| 工作类型 | Bug 修复 / 安全边界修复 |
| 模块 | 现有独立 Odoo Addon `office_engine_odoo`，通过标准模型继承扩展 `llm.thread` |
| 目标 | 阻止被识别为 Office 候选但内容签名或 MIME/扩展名不一致的附件作为普通文本进入 Provider payload，并保持普通 `.txt` / `.png` 路径不变 |
| 上游 SRS | V1.0.0 Frozen |
| 当前上游 TDD | TDD V0.4 Frozen + Provider 前修复补充 V1.0.0 Frozen |
| 当前计划 | Implementation Plan V0.4 Frozen；本修复 CC 已纳入 Phase 5R 映射 |
| 问题证据 | CC-005 ATR-RUN-001：CC-TEST-006 FAIL；`ISSUE-005-01` |

### 0.1 当前前置与状态

负责人于 2026-10-21 批准本 CC 冻结并进入实施。CC-005 已证明 `.xlsx` 文件名配合合成纯文本、Odoo MIME 为 `text/plain` 时，附件预检未拒绝，文本进入本地 Provider mock payload。CC-005 的原始报告和 ATR 是 append-only 证据，不在本 CC 中改写。

上游技术与计划基线已经闭环：TDD V0.4 + 专项补充 V1.0.0 均 Frozen；Implementation Plan V0.4 Frozen 已将本 CC 列为 Phase 5R。本 CC 已获负责人批准冻结并实施；实施结果按独立 IHR/ATR/HVR/FR 记录，不改变 CC-004/005 的历史状态。

## 1. 变更概述

| 字段 | 内容 |
|---|---|
| 背景 | CC-005 的 CC-TEST-006 发现 MIME-only 过滤可被扩展名/内容不一致绕过：伪装为 `.xlsx` 的纯文本被 Odoo 识别成 `text/plain`，可能进入 Provider 的文本附件格式化路径。 |
| 修复目标 | 在 Odoo Provider 参数构造前，通过独立 Addon 对 Office 扩展名、规范化 MIME 与 ZIP/OLE/OOXML 内容特征做一致性校验；不确定或不匹配时抛出脱敏 `UserError` 并阻止 dispatch。 |
| 完成边界 | 仅修复 `ISSUE-005-01` 并重跑前序 CC-005 `CC-TEST-006`；保留正常 `.txt` / `.png` 透传。 |

## 2. 上游基线与追溯

### 2.1 SRS 引用

| SRS ID | 相关性 |
|---|---|
| FR-M1-001 聊天附件接收 | 部分；保持用户上传/消息关联，不改变交互业务流程 |
| FR-M1-002 文件类型与安全结构识别 | 适用；类型伪装与不确定身份必须拒绝 |
| NFR-OFFICE-02 文件安全 | 适用；格式伪装、损坏或身份不能确认时不得继续处理 |
| NFR-OFFICE-06 错误处理 | 适用；拒绝通过可见且不泄露内部信息的错误反馈 |

### 2.2 DDD

N/A；按已批准的 M1 决策，不涉及新的业务聚合或领域状态。

### 2.3 TDD 引用

| 来源 | 相关性 |
|---|---|
| TDD V0.4 §2、§7.1、§7.3、§8.2 `TEST-OFFICE-015`、TD-002、TD-014 | Frozen 基线：Provider 前检查、类型不一致拒绝、不得修改 Odoo 官方源码 |
| [Provider 前修复 TDD 补充 V1.0.0](../../design/TDD_office_engine_m1_pre_route_fix_addendum_v1.0.0.md) | Frozen 专项技术基线；规定 MIME/扩展名/签名一致性、2048 字节头部读取、可选 OOXML 解压上限及跨轮次隔离 |
| [Implementation Plan V0.4](../../implementation/IMPLEMENTATION_PLAN_office_engine_m1_v0.4.md) | Frozen 当前计划；Phase 5R 映射本修复 CC；不替代本 CC 单独冻结和授权 |

### 2.4 缺陷证据

| 证据 | 事实 |
|---|---|
| [CC-005 ATR](../../implementation/office-engine-m1/CC-OFFICE-M1-005/ATR-OFFICE-ENGINE-M1-PROVIDER-ROUTE-SPIKE.md) ATR-RUN-001 / CC-TEST-006 | Office 扩展名配纯文本内容后 Odoo MIME 为 `text/plain`；拒绝数 0；本地 Provider mock dispatch 1 次；未发真实 HTTP 请求 |
| [CC-005 FR](../../implementation/office-engine-m1/CC-OFFICE-M1-005/FR-OFFICE-ENGINE-M1-PROVIDER-ROUTE-SPIKE.md) | CC-TEST-006 未满足，聊天文件能力保持关闭 |

### 2.5 当前有效计划门禁

Implementation Plan V0.4 Frozen 已登记 CC-005 的实际 FAIL/BLOCKED 结果，并将本修复 CC 列为 Phase 5R。该计划建立合法阶段映射，但不替代本 CC 的独立冻结与实施授权。CC-005 handoff 测试仍为 BLOCKED/INCONCLUSIVE，CC-004 FR 仍为 NOT SATISFIED；本修复不改变这些状态。

## 3. 范围冻结

### 3.1 In Scope

- 在现有 `office_engine_odoo` Addon 内，使用 Odoo 标准 `_inherit = "llm.thread"`；通过服务端附件预检识别 Office 扩展名、规范化 MIME 和内容签名；本期默认不解压 OOXML。
- Office 候选的扩展名、MIME 和预期容器不一致、签名失败、截断/损坏或检测不确定时，在 Provider dispatch 之前抛脱敏 `UserError` 并 fail closed。
- 在新消息预检与最终 Provider 参数构造前检查历史消息两处设防；不允许异常退化为普通文本路径。
- 对拒绝消息按现有 `is_error=True` 语义从后续 LLM 上下文排除，验证此行为不会让同一附件在下一轮继续进入 Provider。
- 以本地 Provider stub 和零真实网络调用验证：重跑前序 `CC-TEST-006`；验证 MIME/扩展/签名不一致矩阵；对正常 `.txt` 和有效 `.png` 做回归。
- 在当前开发库 `odoo18ce`、项目 `venv`、`odoo.conf` 上完成 Odoo 模块升级和运行时测试；不创建隔离数据库。
- 使用 Codex 内置浏览器对错误提示及普通附件回归执行人工模拟，并记录 HVR；真实 Provider 必须保持未调用。

### 3.2 Out of Scope

- 任何 Office 文件解析、文本读取、转换、Mapping、生成或附件下载；Office 文件仍由现有聊天路径拒绝。
- `office_engine_odoo` 内部路由服务的建立、授权引用 handoff、Provider 到内部 Office 服务的转交。
- 修复 CC-004 spawn/import 缺陷或修改其 FR 状态；CC-004 的 FR 继续为 `NOT SATISFIED`。
- 将 CC-005 CC-TEST-005 或 CC-TEST-008 标为通过；这两项服务 handoff 验证在本 CC 后仍保持 `BLOCKED` / `INCONCLUSIVE`。
- 修改 `mymodules/odoo-llm/` 中任何代码、Odoo 官方源码/Addons、数据库 schema、Provider 配置、全局 Odoo 配置或新增依赖。
- 增加新 UI、通用文件安全平台、附件清洗机制、队列/后台任务、白名单设置界面或新业务状态。
- 向 OpenAI、DeepSeek 或任意外部 Provider 发出测试请求；使用真实业务文件、业务附件或真实 API 密钥。

### 3.3 Non-Goals

- 证明任意格式的 Office 文件均有效或安全；签名/包特征检查只做 Provider 前类型识别，不替代 `office_core` 完整容器验证。
- 证明所有未安装 Provider 的行为；当前开发实例验证只对实际安装/启用 Provider 配置范围作结论。
- 关闭 CC-005 全部未通过项、进入聊天适配 Phase 6 或开放用户 Office 文件生成。

## 4. 变更边界

### 4.1 允许修改

| 文件 | 允许内容 |
|---|---|
| `mymodules/office_engine_odoo/services/attachment_identity.py`（新增） | 无状态、受限输入的 MIME/扩展名/ZIP-OLE 文件头签名预检；不导入 Odoo、不解压 OOXML、不做 Provider/文件渲染 |
| `mymodules/office_engine_odoo/services/__init__.py`（新增） | 暴露上述内部 helper |
| `mymodules/office_engine_odoo/models/llm_thread.py`（新增） | 标准模型继承；新消息校验与 Provider 参数准备前的历史附件复核；转换成脱敏 `UserError` |
| `mymodules/office_engine_odoo/models/__init__.py` | 注册新增模型扩展 |
| `mymodules/office_engine_odoo/__init__.py` | 如当前模块导入结构需要，注册服务/模型包 |
| `mymodules/office_engine_odoo/tests/test_attachment_identity.py`（新增） | MIME/扩展名/签名判定单元测试 |
| `mymodules/office_engine_odoo/tests/test_llm_thread_attachment_gate.py`（新增） | Odoo 集成测试、stub Provider dispatch 和普通附件回归 |
| `mymodules/office_engine_odoo/tests/__init__.py` | 注册新测试 |
| `docs/design/TDD_office_engine_m1_pre_route_fix_addendum_v1.0.0.md` | Frozen 专项设计基线；本 CC 不修改 |
| `docs/context/intent/CC-OFFICE-M1-PRE-ROUTE-FIX.md` | 本 CC 的评审修订 |
| `docs/implementation/office-engine-m1/CC-OFFICE-M1-PRE-ROUTE-FIX/`（新增） | IHR、ATR、HVR、FR 与脱敏证据 |

`office_engine_odoo/__manifest__.py` 当前已依赖 `llm_thread`；若实现发现必须改变模块依赖、安装额外模块或改变产品架构，停止并先更新 TDD/计划，不得自行扩大本 CC。

### 4.2 禁止修改

| 区域 | 约束 |
|---|---|
| `mymodules/odoo-llm/**` | 完全禁止修改上游副本中的 `llm_thread`、`llm`、`llm_openai` 或其他代码 |
| `odoo/**`、`addons/**` | 不修改 Odoo 官方代码或官方 Addon |
| `mymodules/office_core/**`、`mymodules/office_verify/**` | 不修改文件读写/回读核心；本 CC 只做 Provider 前拒绝 |
| 其他自定义 Addon、配置、模型字段/数据库 schema | 不在本 CC 范围 |

## 5. 必需行为变更

| 当前行为 | 期望行为 | CC-CHANGE |
|---|---|---|
| 聊天入口仅按 `ir.attachment.mimetype` 检查 Office；被判为 `text/plain` 的 `.xlsx` 可继续到文本格式化 | Office 候选依据扩展名、MIME、内容签名/OOXML 包特征识别；声明冲突、签名/包不符、读取失败或不确定时抛 `UserError`，Provider dispatch 计数为 0 | CC-CHANGE-001 |
| 只对新消息的现有 MIME 检查，不在最终发送参数构造处复核整个历史附件集合 | 新消息检查及 `_prepare_chat_kwargs()` 前的历史附件检查共用同一判定 helper；任何候选不通过均不构造/发送 Provider 参数 | CC-CHANGE-002 |
| 被拒绝的身份不明消息可能留在后续模型上下文 | 被拒绝消息以现有 `is_error=True` 语义排除，避免下一轮重发；拒绝不创建输出附件或调用内部 Office handoff | CC-CHANGE-003 |

判定算法、错误边界和具体继承方法须先进入并冻结于递增 TDD 版本。本表不单独授权超出新 TDD 具体条款的设计。

## 6. 既有行为保留

| 行为 | 约束 | CC-PRESERVE |
|---|---|---|
| 普通 `.txt` / `text/plain` 附件经 OpenAI 文本路径处理 | 正常内容可进入本地 mock；不得被 Office 判定误拦截或重写 | CC-PRESERVE-001 |
| 有效 `.png` / `image/png` 附件的现有多模态格式化 | 保留原有图片识别和消息结构；不改写附件字节或 MIME | CC-PRESERVE-002 |
| 正常声明的 Office MIME 目前不送入 Provider | 继续保持不支持/拒绝；本 CC 不开放 Office 聊天读取 | CC-PRESERVE-003 |
| 用户消息的错误排除语义 | 拒绝消息不得进入后续 LLM context；不新建业务状态枚举 | CC-PRESERVE-004 |
| Provider 网络边界 | 所有自动化和人工验证均 mock；真实外发 HTTP 请求为 0 | CC-PRESERVE-005 |

## 7. 适用的 TDD 防护栏

| TDD 来源 | 落实 | 验证 |
|---|---|---|
| TDD V0.4 §7.1(1)：当前用户上下文/权限，不用 sudo 扩大访问 | 附件读取使用当前请求用户环境；拒绝权限/访问异常 | 集成权限测试、ATR payload/身份记录 |
| TDD V0.4 §7.1(2)：扩展名、MIME、签名/容器一致；不确定时拒绝 | 独立 Addon 的类型一致性闸门 | CC-TEST-001—005、008 |
| TDD V0.4 §7.1(7)、TD-002：Provider 前拒绝，payload 不含 Office | `_check_unsupported_attachments` 与 `_prepare_chat_kwargs` 两处服务端复核 | mock dispatch 计数、格式化 payload sentinel 检查 |
| TDD V0.4 §7.3 `OFFICE_INVALID_OR_MISMATCHED`：用户错误脱敏 | 稳定、非敏感 `UserError`；无路径、原文、traceback | 异常消息断言及 HVR |
| 拟议 TDD 补充 `SEC-MIME-001` / `ADPT-CHAT-001` | 仅在该补充进入新冻结 TDD 后适用 | 新基线 CC-TEST-001—005、008 |

## 8. 数据、事务与 API 影响

| 项 | 影响 |
|---|---|
| 数据迁移 / 字段 / schema | 无 |
| 公共 HTTP/JSON-RPC API | 无；复用现有聊天生成入口 |
| 消息事务 | 可能给拒绝消息写入现有 `is_error=True`；必须用当前 Odoo 运行时验证提交/错误展示，不得新增状态字段 |
| Provider 配置 | 不变；测试 Provider dispatch 替身在进程内注入，退出后必须消失 |
| 附件内容 | 只做有界身份预检；不持久化副本、不返回附件、不触发 Office 内部服务 |

## 9. 安全与权限要求

- 不调用 Provider 外网；自动化测试必须证明 HTTP 外发计数为 0。
- 不使用 `sudo()`、`env(su=True)`、共享 token 或绕过 Record Rules 读取附件。
- 先检查附件记录可读权限与长度元数据，再通过当前用户授权的有界读取取得文件头；不拼接/读取任意磁盘路径。
- **签名校验最多读取文件头 2048 字节。禁止为校验魔数调用会完整物化附件的 `raw`、`datas` 等接口；禁止完整附件 Base64 编码或复制。**若目标运行时无法有界读取，必须 fail closed，不得退化为完整读取。
- 若实现对 OOXML 做初步 ZIP 结构检查：单条目实际解压读取不得超过 **1 MiB**，全部条目累计实际解压不得超过 **5 MiB**；应在读取前核查目录声明大小，并用 `limit + 1` 有界读取发现超限。禁止 `extractall()`、无界解压、无界 XML 解析。超限、加密、损坏或异常均拒绝。
- 未实施 OOXML 初步解析时，只做文件头签名识别；不得将 ZIP 魔数声称为 OOXML 完整性或安全证明。
- 错误文案不回显附件正文、文件路径、异常堆栈、密钥或未经授权的附件标识。
- 先检查整段实际待发送 `message_history`；确保任一被识别 Office 候选未进入 Provider formatter、payload、tools loop 或多模态内容。
- 任何没有通过身份闸门的消息不得进入后续 LLM 上下文；不得创建 Office 请求、输出附件或内部服务 handoff。

## 10. 测试契约

| 测试 ID | 对应变更 / 上游回归 | 预期结果 | 人工验证 |
|---|---|---|---|
| CC-TEST-001 | 类型矩阵：Office 后缀但 `text/plain` 内容；Office MIME 配纯文本/错误容器；互相冲突的 Office 后缀/MIME | 每种 Office 候选均抛 `UserError`；Provider mock dispatch=0；无正文/路径泄露 | 否 |
| CC-TEST-002 | **重跑 CC-005 的 CC-TEST-006 原始失败场景**：`.xlsx` 名称 + `text/plain` + 合成纯文本 | 原缺陷修复；服务端预检前置于 Provider；dispatch=0；判定/错误在 ATR 绑定精确源码与运行基线 | 否 |
| CC-TEST-003 | Office 候选容器签名/包身份：有效 OOXML 最小包、截断 ZIP、坏目录、OLE magic、错误 ZIP/OLE 家族 | 任何冲突/损坏/检测异常 fail closed；本 CC 仍拒绝把 Office 发送给 Provider；魔数读取最多 2048 字节，不完整读取附件 | 否 |
| CC-TEST-004 | 普通附件回归：正常 `.txt`/`text/plain` 与有效 `.png`/`image/png` | 本地 stub 收到与既有路径等价的文本/图片结构；没有错误 `UserError` 或 Office 误分类 | 是：聊天 UI 检查可见结果 |
| CC-TEST-005 | 同线程跨轮次：第一轮发送伪装 `.xlsx`（`text/plain`）并触发拒绝；随后在同一线程发送正常文本；同时覆盖新消息/历史消息的拦截与附件权限 | 第一轮在 Provider 前拒绝且 dispatch=0；第二轮 Provider mock `message_history` 不包含第一轮附件引用/正文，也不包含第一轮拒绝消息或错误提示；无权/读取失败受控拒绝；未用 `sudo()` | 否 |
| CC-TEST-006 | stub Provider 及真实 HTTP 观察 | 所有测试均未连接真实 Provider；HTTP 外发=0；所有临时 monkey patch/hook 在测试后清理 | 否 |
| CC-TEST-007 | 模块升级、现有正常线程回归与内置浏览器人工验证 | 当前 `odoo18ce` 中模块安装/升级成功；异常提示可见；普通文本与 PNG 交互可用；不提供 Office 处理/下载 | 是：Codex 内置浏览器 HVR |
| CC-TEST-008 | 安全资源边界：伪装大附件、可选 OOXML 高压缩/超限包 | 魔数校验读取字节数 ≤2048 且未读完整附件；若进行 ZIP 初步解析，单条解压 ≤1 MiB、累计 ≤5 MiB，超限受控拒绝、Provider dispatch=0；若未启用解析，测试/报告证明未触发解压 | 否 |

原 CC-005 的 CC-TEST-005/008 handoff 项不属于本 CC 的回归 PASS 范围。它们仍保持 BLOCKED / INCONCLUSIVE；本 CC 自己的 `CC-TEST-005` 是跨轮次上下文隔离测试，与前序 CC-005 同名测试项需在 ATR 中以完整 CC ID 区分。新 ATR 只记录本次重跑事实，不篡改 ATR-RUN-001。

## 11. 停止条件 / 升级闸门

| 触发条件 | 处理 |
|---|---|
| 本修复 CC 未经负责人单独冻结和实施授权 | 停止代码、模块升级和修复测试；先完成本 CC 审批 |
| 需要修改 `mymodules/odoo-llm/**`、官方 Odoo 源码/Addon | 立即停止，回到 TDD/TV 评审；本 CC 不允许上游补丁 |
| 需要建立/测试内部服务 handoff 或打开 Office 内容处理 | 停止并另立技术设计与 CC；本 CC 不授权 |
| 普通 `.txt` / `.png` 回归失败，或检测异常能继续发 Provider | 判为 FAIL，阻塞 FR/关闭，不得绕过校验 |
| 环境要求创建隔离 DB、真实 Provider 请求或读写真实业务附件 | 停止该测试；仅使用已批准开发库与合成文件，并确保无外发 |

## 12. 完成定义 / 关闭标准

- 所有 CC-CHANGE 均在 `office_engine_odoo` 独立 Addon 中完成，未触及任何禁止目录。
- 旧 CC-005 CC-TEST-006 原始失败场景已重跑并通过；ATR 明确记录 mock dispatch=0、无真实网络外发及当前代码基线。
- Office MIME/扩展/签名失配、损坏与检测不确定样例均 fail closed，且在 Provider 参数构造前拒绝。
- 正常 `.txt` / `.png` 既有透传路径在自动化与内置浏览器 HVR 中通过。
- 新消息和历史消息上下文路径均被覆盖；权限检查不使用 sudo；拒绝消息不被下一轮重发；同线程第二轮 `message_history` 同时不含被拒绝附件及拒绝/错误消息。
- 魔数校验只读取最多 2048 字节且未完整读取附件；可选 OOXML ZIP 初步检查满足单条 1 MiB、总计 5 MiB 解压硬上限，并有超限拒绝证据。
- IHR、ATR、HVR、FR、脱敏证据、依赖/模块变更说明和清理证明完整；原 ATR-RUN-001 不变。
- CC-005 的 CC-TEST-005/008 仍明示 BLOCKED / INCONCLUSIVE；不得宣称内部 handoff 已验证或 Phase 5 整体通过。
- TDD V0.4、专项补充 V1.0.0、Implementation Plan V0.4 及本 CC 均为 Frozen；本 CC 的实施状态只由本次独立 IHR/ATR/HVR/FR 记录。
- 所有自动化和人工验收均 PASS，才可将此修复 CC 的 FR 标为 SATISFIED；任何失败/缺证据按工作流报告原生状态并阻止关闭。

## 13. 追溯矩阵

### 13.1 正向追溯

| 上游需求/设计 | CC-CHANGE | 验证 |
|---|---|---|
| FR-M1-002、NFR-OFFICE-02 | CC-CHANGE-001 | CC-TEST-001/002/003 |
| TDD V0.4 §7.1(2)、§7.1(7)、TD-002 / 专项 TDD 补充 V1.0.0 TD-PRF-001—005 | CC-CHANGE-001/002 | CC-TEST-001—006、008 |
| NFR-OFFICE-06、TDD V0.4 §7.3 | CC-CHANGE-001/003 | CC-TEST-001/002/005/007 |
| 既有文本/图像路径 | CC-PRESERVE-001/002 | CC-TEST-004/007 |

### 13.2 反向追溯

| CC-CHANGE / PRESERVE | 上游来源 | 验证 |
|---|---|---|
| CC-CHANGE-001 | FR-M1-002、NFR-OFFICE-02、TDD §7.1(2) | CC-TEST-001—003、008 |
| CC-CHANGE-002 | TDD §7.1(7)、§8.2 TEST-OFFICE-015、专项 TDD 补充 TD-PRF-004 | CC-TEST-002/005/006 |
| CC-CHANGE-003 | NFR-OFFICE-06、专项 TDD 补充 TD-PRF-004、既有 `is_error` 错误排除行为 | CC-TEST-005/007 |
| CC-PRESERVE-001/002 | 既有 Odoo-LLM 普通文本/图像格式化行为 | CC-TEST-004/007 |
| 资源边界 | 专项 TDD 补充 TD-PRF-002/003 | CC-TEST-003/008 |

## 附录 A — 实现决策

| CC-DEC | 提案 | 依据 |
|---|---|---|
| CC-DEC-001 | 使用现有 `office_engine_odoo` 的 Odoo 标准模型继承，不修改上游 `llm_thread` | 用户限定独立 Addon/标准继承；TDD 禁止修改官方源码 |
| CC-DEC-002 | 同一身份校验 helper 同时用于新消息预检和 Provider 参数准备前复核 | 覆盖新附件及历史 context；针对 CC-005 实际缺口 |
| CC-DEC-003 | 本 CC 默认仅检查固定文件头；若另行启用 OOXML 初步检查，须遵守单条 1 MiB、累计 5 MiB 解压上限；两者都不等同于完整 Office 安全解析 | 防止将 ZIP 魔数误报为文件整体安全 |
| CC-DEC-004 | 验证只使用进程内 Provider stub 和合成附件 | 避免真实外发与业务数据暴露 |

## 附录 B — 版本历史

| 版本 | 日期 | 状态 | 说明 |
|---|---|---|---|
| v0.1 | 2026-10-21 | Draft — 历史版本 | 根据 CC-005 ATR-RUN-001 的 CC-TEST-006 FAIL 起草。 |
| v0.2 | 2026-10-21 | Draft — 重新提交负责人评审 | 采用 Frozen TDD 补充 V1.0.0 和 Implementation Plan V0.4；增加跨轮次上下文污染测试、2048 字节头部读取硬限制及 OOXML 单条 1 MiB/累计 5 MiB 解压上限。 |
| v1.0.0 | 2026-10-21 | Frozen — 负责人批准实施 | 负责人批准冻结并进入实施；冻结范围与测试契约不变。 |
