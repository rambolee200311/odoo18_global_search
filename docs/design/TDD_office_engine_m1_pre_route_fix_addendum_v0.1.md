# Office Engine M1 TDD 补充草案：Provider 前附件类型与签名校验

| 字段 | 内容 |
|---|---|
| 补充编号 | `TDD-OFFICE-ENGINE-M1-PRE-ROUTE-FIX` |
| 版本 | `v0.1 Draft` |
| 状态 | **Superseded Draft — 非权威版本；已由 V1.0.0 Frozen 取代** |
| 适用基线 | Office Engine M1 TDD V0.4 Frozen；SRS V1.0.0 Frozen |
| 关联问题证据 | CC-OFFICE-M1-005 / `ISSUE-005-01` / CC-TEST-006 FAIL |
| Intent | `OFFICE-ENGINE-M1-PRE-ROUTE-FIX` |

> 历史草案，已由 [TDD 补充 V1.0.0 Frozen](TDD_office_engine_m1_pre_route_fix_addendum_v1.0.0.md) 取代。保留本文仅供变更追溯，不构成技术基线或编码依据。

## 1. 目的与范围

补足 TDD V0.4 §7.1、§7.3、§8.2 `TEST-OFFICE-015` 对 Provider 前附件校验的实施细节，修复 CC-005 发现的类型伪装缺口：文件名为 `.xlsx`、内容为纯文本、Odoo `ir.attachment.mimetype` 为 `text/plain` 时，现有 MIME-only 检查没有拒绝，OpenAI formatter 将附件文本加入 Provider 消息。

本补充只设计聊天附件身份一致性闸门。它不启用 Office 聊天读取、解析、路由或生成，也不处理 CC-004 的 spawn/import 缺陷。

## 2. 当前执行链与缺口定位

源码调查基线为 Odoo-LLM commit `609ec6dda3645165f6a4a843d7af5d286081a29d`；CC-005 的 ATR-RUN-001 在同一干净源码基线上复现：

1. `llm.thread.generate()` 先将上传的附件通过 `message_post()` 关联到新 `mail.message`，随后调用 `_check_unsupported_attachments(last_message)`，再进入 `generate_messages()`。
2. `_check_unsupported_attachments()` 将消息交给 `mail.message._get_unsupported_attachments()`；该方法按 `ir.attachment.mimetype` 与 Office MIME 列表分类，没有以文件名扩展名或内容签名交叉检查。
3. `.xlsx` 名称但内容为纯文本的附件在 Odoo 中成为 `text/plain`，因此没有被 Office MIME 分支拒绝。
4. `llm_assistant` 继续构造消息历史并调用 `_prepare_chat_kwargs()`；之后才调用 `llm.model.chat()` / Provider。
5. `llm_openai` 的 `openai_format_message()` 调用 `_get_text_attachments()`，按 `text/*` MIME 解码附件，并把文本并入用户消息内容。因此被误识别为文本的伪装附件可能进入 Provider payload。

`llm_thread/controllers/main.py` 会捕获生成器异常并通过 SSE 返回错误；`_prepare_chat_kwargs()` 在 `_generate_assistant_response()` 的 Provider 调用 `try` 块之前执行。实现须在这两个可由 Odoo 标准模型继承覆盖的服务端检查位置阻断，不修改官方 `llm_thread`、`llm` 或 Provider Addon。

## 3. 拟议独立 Addon 设计

### 3.1 扩展边界

在已存在的 `mymodules/office_engine_odoo` Addon 中使用标准 `_inherit = "llm.thread"` 扩展。其 manifest 已依赖 `llm_thread`；不得直接修改 `mymodules/odoo-llm/` 的官方/上游源码。

建议提供一个只做附件身份预检的内部 helper，不调用 Provider，不读取业务模型，不访问任意文件系统路径，不触发 `office_core` 渲染或内部 Office 服务 handoff。

### 3.2 强类型 MIME 与签名联合判定

判定依据包括：

- 附件名称的大小写不敏感扩展名；
- 去除参数后的 `ir.attachment.mimetype`；
- 在当前 Odoo 用户授权上下文中读取的附件字节签名；必要时以受限 ZIP 目录信息确认 OOXML 主部件，避免把任意 ZIP 直接等同于 Office。

只要扩展名、MIME 或 OOXML/OLE 内容特征中的任一项将附件识别为 Office 候选，就进入一致性校验。扩展名和 MIME 若均属于 Office，二者声明的 Office 家族必须一致；内容容器也必须与该家族相符：

| Office 家族 | 声明信息 | 必需的内容特征 |
|---|---|---|
| OOXML Word / Excel / PowerPoint | `.docx/.xlsx/.pptx` 或对应 MIME | ZIP local-file signature，且受限读取确认 `[Content_Types].xml` 与对应主部件（`word/document.xml`、`xl/workbook.xml` 或 `ppt/presentation.xml`） |
| 旧版 OLE Word / Excel / PowerPoint | `.doc/.xls/.ppt` 或对应 MIME | OLE Compound File signature `D0 CF 11 E0 A1 B1 1A E1` |

以下情况必须在 Provider 调用前抛出脱敏 `UserError` 并拒绝：Office 扩展名或 Office MIME 与签名/容器不符；扩展名与 MIME 声明相互冲突；Office 候选为空、截断、签名不匹配、ZIP 目录损坏或无法在限制内确认；检测过程出现异常或结果不确定。错误文案只说明“附件类型与内容不一致或无法安全识别，已拒绝发送”，不得包含文件内容、路径、内部 traceback 或 Provider 凭据。

内容识别也必须检查 MIME/扩展名以外的 Office 特征：若其他扩展名的附件 MIME 声明为 Office，按相同规则验证；若 MIME/扩展名不是 Office、但内容可确定为 OOXML/OLE Office 包，则将其视为类型不一致候选并拒绝，不得作为普通文本或通用文件发送。

签名只证明容器类型候选，不能证明文件完整、无恶意或支持解析。完整 ZIP/OLE 结构安全、条目/膨胀限制及格式能力仍归 `office_core` 的准入校验；本聊天闸门不得宣称替代它。

### 3.3 Provider 前执行位置

在 `llm.thread` 的继承扩展中复用同一 helper：

1. 覆盖 `_check_unsupported_attachments(message=None)`：对本次新消息及该方法要求检查的消息先执行类型/签名一致性校验，再委托 `super()` 保留现有“有效 Office 附件不支持聊天处理”的拒绝行为。身份失败抛 `UserError`，不能降级为普通文本。
2. 覆盖 `_prepare_chat_kwargs(message_history, use_streaming)`：在构造 Provider 参数前复核即将发送的全部历史用户消息附件，再委托 `super()`。这样保护已有历史附件、模型切换和任何绕过新增消息预检的上下文路径。
3. 对被拒绝的新消息，按现有 `is_error=True` 语义从后续 LLM context 排除；保证 SSE 错误路径与消息记录行为在目标运行时验证。
4. 校验异常、附件不可读、附件大小超出预检上限或无法安全取得足够签名时一律 fail closed。使用 `ir.attachment` 当前用户权限；不使用 `sudo()`、超级用户环境或公开附件 token。

普通 `.txt` / `.png` 的既有 MIME 与处理路径不变。非 Office MIME 且没有 OOXML/OLE 内容特征时，闸门不得误报为 Office。有效 Office 附件仍按当前能力边界拒绝发给 Provider；本补充不增加 Office 读取能力。

## 4. 验证契约

回归需在当前获准的开发环境 `odoo18ce`、项目 `venv`、`odoo.conf` 运行；Provider 网络调用全部 stub，Provider dispatch 计数可观测且必须为零（拒绝场景）。不创建隔离数据库，不使用真实业务文件或真实外部 API。

至少验证：

1. 重跑 CC-005 `CC-TEST-006` 的原始失败样例：`.xlsx` 名称、`text/plain` MIME、合成纯文本字节；应抛 `UserError`、无 Provider dispatch、拒绝内容不在历史上下文中。
2. Office MIME 配纯文本/错误签名；任意扩展名配 Office MIME 但签名不符；Office 扩展名与 MIME 互相冲突；均抛 `UserError` 且 Provider dispatch 为零。
3. 正确 MIME/扩展名但截断或损坏的 Office 候选，在安全预检失败时抛 `UserError` 且 Provider dispatch 为零。
4. 正常 `.txt`（`text/plain`）和有效 `.png`（`image/png`）仍按既有路径到达本地 mock；断言消息正文/附件处理未被 Office 闸门改变。
5. 新消息路径和已存历史消息路径均在最终 Provider 参数构造前受检查；检查异常时仍 fail closed。
6. 至少一条目标用户/附件权限路径以普通用户环境运行，证明读取检查没有 `sudo()`；证据不含 API key、附件正文或 Base64。

旧 CC-005 ATR-RUN-001 是 append-only 历史证据，不得改写。修复 CC 需建立新的测试运行记录并引用原始 FAIL；只有新的有效证据能证明该缺陷已修复。

## 5. 明确未覆盖事项

- CC-005 的 CC-TEST-005 与 CC-TEST-008 因当前尚无已建立的 `office_engine_odoo` 聊天路由服务，仍为 BLOCKED / handoff 可行性 INCONCLUSIVE。此补救只验证正确拒绝，不测试转交内部路由服务，不得把它们改为 PASS。
- 不实现上传 UI、文件读取/渲染、Mapping Plan、Provider 工具、内部 handoff 或用户下载。
- 不修复 CC-004 spawn/import 缺陷，不据此开放 CC-006 或宣称 Phase 5 整体通过。

## 6. 基线与治理门禁

1. 本草案如获批准，须纳入 TDD V0.5 或项目批准的下一递增版本，评审并冻结后才可成为实现依据；TDD V0.4 保留且不覆盖。
2. Implementation Plan V0.3 当前没有本修复 CC 的阶段映射，且 CC-005 的实际 FAIL 使原聊天适配入口条件未满足。必须先完成计划影响复核，新增修复阶段/CC 映射并批准、冻结新计划版本；不能直接以计划 V0.3 冻结本 CC 或开工。
3. 完成上述上游门禁后，修复 CC 仍须单独评审、冻结并获得明确实施授权。

