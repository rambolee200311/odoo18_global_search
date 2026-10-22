# Odoo Office Engine M1 TDD 补充：Provider 前附件类型与签名校验

| 字段 | 内容 |
|---|---|
| 补充编号 | `TDD-OFFICE-ENGINE-M1-PRE-ROUTE-FIX` |
| 版本 | `V1.0.0` |
| 状态 | **Frozen — 负责人依据 2026-10-21 明确指示批准冻结** |
| 适用基线 | Office Engine M1 TDD V0.4 Frozen；SRS V1.0.0 Frozen |
| 计划基线 | M1 Implementation Plan V0.4 Frozen |
| 关联问题证据 | CC-OFFICE-M1-005 / `ISSUE-005-01` / CC-TEST-006 FAIL |
| Intent | `OFFICE-ENGINE-M1-PRE-ROUTE-FIX` |

> 本补充只补充 Provider 前附件身份预检的技术契约，不修改或覆盖 TDD V0.4，也不代表修复 CC 已冻结或授权实施。两份 TDD 文件共同构成本专项修复的技术基线。

## 1. 目的与范围

修复 CC-005 发现的类型伪装缺口：文件名为 `.xlsx`、内容为纯文本、Odoo MIME 为 `text/plain` 时，现有 MIME-only 检查未拒绝，文本可能被 OpenAI 文本附件格式化路径加入 Provider 消息。

本补充规定独立 Addon 中的 MIME、扩展名与文件签名一致性闸门及其资源边界。Office 文件在当前阶段仍不得进入 Provider；有效 Office 附件继续按现有能力边界拒绝。本补充不启用 Office 聊天读取、解析、路由、渲染或生成，也不处理 CC-004 的 spawn/import 缺陷。

## 2. 执行链与缺陷定位

源码调查基线为 Odoo-LLM commit `609ec6dda3645165f6a4a843d7af5d286081a29d`；CC-005 ATR-RUN-001 在该源码基线上复现：

1. `llm.thread.generate()` 先通过 `message_post()` 关联新消息和附件，再调用 `_check_unsupported_attachments(last_message)`，随后进入消息生成。
2. 上游检查经 `mail.message._get_unsupported_attachments()` 按 `ir.attachment.mimetype` 分类，没有交叉检查文件名扩展名和内容签名。
3. `.xlsx` 名称但纯文本内容可被识别为 `text/plain`，因此未进入 Office MIME 拒绝分支。
4. `llm_assistant` 后续生成历史并调用 `_prepare_chat_kwargs()`，之后才调用 Provider。
5. `llm_openai` 对 `text/*` MIME 附件进行文本格式化，故伪装附件可能进入 Provider payload。

独立 Addon 通过 Odoo 标准模型继承实现服务端检查，不修改 `mymodules/odoo-llm/`、Odoo 官方源码或官方 Addon。

## 3. 技术设计

### 3.1 扩展边界

在既有 `mymodules/office_engine_odoo/` Addon 中使用 `_inherit = "llm.thread"`。提供无状态附件身份 helper；helper 不调用 Provider、不访问任意文件系统路径、不读取业务模型，不调用 `sudo()`，不触发 Office 内部 handoff。

同一 helper 必须覆盖两个时点：

1. 新消息的 `_check_unsupported_attachments(message=None)` 检查，完成身份预检后保留 `super()` 的既有拒绝语义。
2. `_prepare_chat_kwargs(message_history, use_streaming)` 前重新检查实际待发送历史中的附件，避免历史消息、模型切换或调用路径变化绕过新消息预检。

检查不通过、附件无权读取、读取失败或无法完成有界检查时，抛出脱敏 `UserError`，并且不得构造或 dispatch Provider 请求。被拒绝消息按既有 `is_error=True` 语义从后续 LLM 上下文排除。

### 3.2 Office 候选与 MIME/扩展名/签名一致性

下列任一信号将附件归为 Office 候选：Office 扩展名、Office MIME，或头部可识别的 Office ZIP/OLE 签名。候选必须验证声明和签名彼此一致；任何冲突、空内容、截断、签名不匹配、读取失败或无法判定均 fail closed。

- OOXML 扩展名/MIME 的文件头须为 ZIP local-file signature（`PK\x03\x04`）；此签名只证明 ZIP 容器候选，不证明其为有效或安全的 OOXML。
- 旧版 Office 扩展名/MIME 的文件头须为 OLE Compound File signature（`D0 CF 11 E0 A1 B1 1A E1`）。
- MIME 参数先规范化后再与扩展名声明的 Office 家族比对；Office 声明互相冲突时拒绝。
- 非 Office `.txt`/`text/plain` 和 `.png`/`image/png` 且没有 Office 签名时维持原有处理路径。
- 任何 Office 候选在本阶段都不送 Provider，包括身份一致的 Office 文件；本闸门不是 Office 处理能力的开放开关。

用户错误只说明附件类型与内容不一致或无法安全识别并已拒绝；不得回显附件正文、路径、堆栈、凭据或未授权标识。

### 3.3 固定头部读取限制

魔数/文件签名校验只允许从当前用户授权的附件读取固定头部，最大 **2048 字节**。签名校验不得调用 `attachment.raw`、`datas` 或其他会将完整附件物化到 Python 内存的接口；不得对完整内容执行 Base64 编码或复制。

实现必须使用能提供有界读取的受控附件读取方式。若目标 Odoo 运行时无法在不读取完整附件的情况下取得头部，或读取权限/长度信息不可靠，则拒绝该 Office 候选并记录受控错误；不得退化为完整读取。对附件声明长度进行预检，空附件及无法确认长度/读取边界的 Office 候选 fail closed。此项不定义新的通用上传容量产品策略。

### 3.4 可选 OOXML 初步结构检查的上限

本 CC 的默认身份判定不要求解压或遍历 OOXML；ZIP 魔数只用于容器家族一致性。若实现为确认 OOXML 部件而进行初步 ZIP/OOXML 检查，必须同时满足：

- 任一 ZIP 条目的实际解压读取上限为 **1 MiB**；通过读取至 `limit + 1` 检测超限后立即拒绝。
- 全部条目的累计实际解压读取量上限为 **5 MiB**；达到上限即拒绝。
- 在读取条目内容前核对中央目录声明的单项及累计大小；声明超限立即拒绝。
- 禁止 `extractall()`、无界解压、将条目全部读入内存或对整包执行无界 XML 解析。
- ZIP 条目损坏、加密、目录异常或检查异常均 fail closed。

超过任一上限不是“部分检查通过”，而是拒绝发送。该有界预检不替代 `office_core` 的完整文件安全与能力校验。

### 3.5 普通附件与历史上下文

普通 `.txt`、有效 `.png` 等非 Office 附件必须保持原有语义。拒绝伪装 Office 附件后，当前线程继续发送普通文本时，第二轮 Provider mock 的 `message_history` 不得包含第一轮被拒绝附件、附件正文或该拒绝产生的错误提示。

## 4. 验证契约

所有 Provider 测试使用进程内 stub/mock，真实外发 HTTP 为零。测试使用合成附件和获准开发库 `odoo18ce`，不得读取真实业务文件或真实 Provider 凭据。

最低验证包括：

1. 重跑 CC-005 `CC-TEST-006` 原始失败样例（`.xlsx` 名称、`text/plain`、合成纯文本）：应抛 `UserError`、Provider dispatch 为 0。
2. Office MIME/扩展名与纯文本、错误容器或彼此冲突的声明组合均拒绝；有效 `.txt`/`.png` 仍到达本地 mock，结构等价于原路径。
3. 魔数校验只读取最多 2048 字节；测试必须证明完整附件读取/Base64 编码未发生。超过读取边界、读取异常或附件不可读均拒绝。
4. 同一线程跨轮次回归：第一轮发送伪装 `.xlsx` 并得到拒绝；随后发送普通文本；断言第二轮 Provider mock `message_history` 不包含第一轮附件、附件正文或拒绝/错误消息。
5. 如实现执行可选 OOXML 初步解析，覆盖单 ZIP 条目超过 1 MiB、累计解压超过 5 MiB、损坏/加密 ZIP；确认超限前不发生无界解压且 Provider dispatch 为 0。若实现不做该解析，记录其未启用，并仍对本补充规定的 helper 上限做静态/单元级测试。
6. 新消息和历史消息两条路径均在 Provider 参数准备前受检查；权限测试不得使用 `sudo()`。
7. 测试完成后临时 stub/hook 被移除，不发出真实网络请求。

CC-005 的原始 ATR-RUN-001 是 append-only 历史证据，不得覆盖。修复后需建立新的 IHR/ATR/HVR/FR 记录，并绑定修复代码基线。

## 5. 当前明确未覆盖的事项

- CC-005 的 `CC-TEST-005`/`CC-TEST-008` 内部 handoff 验证保持原状态：`BLOCKED` / `INCONCLUSIVE`。修复 CC 只验证安全拒绝，不验证交给内部路由服务。
- CC-004 spawn/import 缺陷与其 FR `NOT SATISFIED` 状态不变；不得据本修复将 CC-004 或 Phase 5 整体标为通过。
- 不创建内部 handoff、上传 UI、Mapping UI、Skill、Provider 工具、下载、通用附件扫描平台或新业务状态。

## 6. 技术决策与治理

| 决策 | 结论 |
|---|---|
| TD-PRF-001 Provider 前身份闸门 | MIME、扩展名与签名冲突一律在独立 Addon Provider 前拒绝；有效 Office 在当前阶段仍拒绝外发 |
| TD-PRF-002 读取边界 | 魔数仅读取 2048 字节；不完整读取附件做签名校验；目标运行时不能有界读取时 fail closed |
| TD-PRF-003 OOXML 初步检查 | 可选；若启用，单条解压最多 1 MiB、累计最多 5 MiB；不调用无界解压 |
| TD-PRF-004 历史上下文 | 拒绝消息不得在当前线程后续轮次进入 Provider history |
| TD-PRF-005 代码边界 | 只在 `office_engine_odoo` 标准继承中实现，不修改上游/官方源码 |

本补充由负责人明确批准冻结为 V1.0.0。其冻结仅确立专项技术设计；修复 CC 仍须单独评审、冻结并获实施授权。Implementation Plan V0.4 建立本修复的阶段映射；各自冻结不改变 CC-005/CC-004 的历史测试状态。
