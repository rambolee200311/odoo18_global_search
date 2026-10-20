# Odoo-LLM Office 自动化源码调查记录

> **记录元信息**
>
> - 状态：源码调查草稿，供 SRS 评审参考
> - 检查日期：2026-10-19
> - 主仓库：/Users/lijianqiang/Documents/odoo18_global_search
> - 主仓库分支 / commit：main / b8d5c4fd46da4902c3ef632b8bdd15ed884856f8
> - Odoo-LLM 路径：mymodules/odoo-llm
> - Odoo-LLM 分支 / commit：18.0 / 609ec6dda3645165f6a4a843d7af5d286081a29d
> - 状态说明：主仓库和 Odoo-LLM 子仓库均有未提交改动；本文针对检查时的工作树，不把 commit 单独视为完整源码状态。

## 1 检查范围与限制

阅读了 llm_thread、llm_tool、llm_assistant、llm_openai、llm_tool_ocr_mistral、llm_knowledge 的 Python、XML、JavaScript、manifest、依赖清单和相关测试。检查还覆盖 llm_generate 的模块清单。

本轮是静态源码调查，没有执行 Odoo 安装、运行时权限验证、Office 文件读写 Spike、格式保留实验或真实 Provider 请求。因此不能据此证明运行时附件 ACL、记录规则和具体模型权限行为，也不能承诺 Office 库对复杂文档的保留能力。

上游任务提示词附件在 M1-FR-008 的第一条要求后即结束，未包含其余完整阶段要求。SRS 对补足部分保持 Draft/待评审。

## 2 仓库、模块与依赖

| 项目 | 检查事实 |
|---|---|
| Odoo-LLM checkout | 分支 18.0，commit 609ec6dda3645165f6a4a843d7af5d286081a29d |
| 未提交的相关改动 | llm_openai/models/openai_provider.py、llm_tool/models/llm_tool.py 存在修改，llm_openai 下另有未提交文件；功能调查以当前工作树为准 |
| 主要模块版本 | llm_thread 18.0.1.4.5；llm_tool 18.0.4.1.2；llm_assistant 18.0.1.5.4；llm_openai 18.0.1.4.0；llm_tool_ocr_mistral 18.0.1.0.1；llm_knowledge 18.0.1.1.0 |
| Office 依赖 | requirements.txt 和这些模块清单未发现 openpyxl、python-docx/docx 声明；源码检索未发现相应库调用 |

## 3 已确认能力及源码证据

### 3.1 聊天附件与当前支持范围

- 聊天界面使用 Odoo mail 的 FileUploader / AttachmentList；提交服务将附件 ID 带入聊天请求。证据：llm_thread/static/src/templates/chatter_ai_button.xml:69-91；llm_thread/static/src/services/llm_store_service.js:72-103；llm_thread/static/src/patches/composer_patch.js:58-69。
- 控制器解析 attachment_ids 并传给线程生成方法。证据：llm_thread/controllers/main.py:88-112。
- 线程将附件关联到新 user 消息；线程附件集合由消息附件计算。证据：llm_thread/models/llm_thread.py:198-204、351-371。
- 聊天“可以附加文件”与“Office 可送入模型”是不同能力。llm/models/mail_message.py 将 Office MIME 列为不支持；llm_thread/models/llm_thread.py 检查新消息，不支持时标记错误并在调用模型前返回。证据：llm/models/mail_message.py:50-58、366-420；llm_thread/models/llm_thread.py:377-385。
- 准确现状：聊天 UI 有附件接收/关联机制，但当前聊天生成路径拒绝处理 Office 文档。

### 3.2 Provider 附件格式

llm_openai/models/mail_message.py 将文本附件读成文本内容；多模态路径支持图片/PDF及特定音频格式，没有 xlsx/docx 的结构读取或模板回填。证据：llm_openai/models/mail_message.py:24-92。其他 Provider 的具体附件格式行为需另行核验。

### 3.3 工具框架与 Odoo 数据查询

- llm_tool 提供工具定义、JSON Schema、装饰器登记和统一执行入口。证据：llm_tool/models/llm_tool.py:10-32、126-180；llm_tool/decorators.py:10-35。
- llm_assistant 的线程从助手取得工具集合；Provider 请求将 thread.tool_ids 作为工具传入；执行时按线程中的工具名查找并调用。证据：llm_assistant/models/llm_thread.py:27-70、331-338；llm_tool/models/mail_message.py:226-260。
- 工具元数据中的 read_only_hint 不能单独作为服务端写入拦截保证；现有工具集合也包含创建、更新、删除工具。
- odoo_record_retriever 接受 model、domain、fields、limit，并直接对 self.env[model] 执行 search_read/read。实现中未见固定的模型/字段白名单。证据：llm_tool/models/llm_tool_record_retriever.py:18-47。不能据此推断所有模型、字段和关联关系都满足此需求的准入范围。
- 该查询方法使用当前模型环境且未见 sudo，但本轮没有进行 ACL/Record Rules 运行时验证。

### 3.4 OCR、知识库与 Office 文件

- llm_tool_ocr_mistral 的用途是 PDF/图片 OCR；实现读取附件后调用 Mistral OCR，没有 Office 表格/文档结构解析。证据：llm_tool_ocr_mistral/models/ir_attachment.py:18-40、103-151。
- llm_knowledge 上传向导的文件扩展名列表包含 doc/docx/xls/xlsx。证据：llm_knowledge/wizards/upload_resource_wizard_views.xml:35-41。
- 该上传能力不等于 Office 内容解析：默认解析器为 PDF、文本、HTML、图片、JSON 分派专用解析，其余类型进入通用描述，指出该 MIME 不能直接解析为文本。证据：llm_knowledge/models/llm_resource_parser.py:92-117、311-320。

## 4 未发现或未验证的能力

| 能力 | 调查结论 |
|---|---|
| xlsx 单元格、公式、合并区域的结构化读取 | 未发现 |
| docx 段落、表格的结构化读取 | 未发现 |
| Office 模板填充/渲染、生成结果附件 | 未发现 |
| Excel 公式计算、缓存刷新 | 未发现；不能把保留公式等同于计算 |
| Office 扩展名、MIME、容器内容一致性安全校验 | 未发现完整 Office 容器校验；聊天现有检查主要按 MIME |
| Office 读取/渲染专用工具和映射契约 | 未发现 |
| 通用工具中的模型/字段固定准入、关系深度策略 | 在 odoo_record_retriever 主体中未发现 |
| 模板映射 Skill 的验证、版本和生命周期 | 未发现对应能力 |
| Office 文件大小、展开容量、超时专用阈值 | 未发现 |
| Office 渲染格式回归样本 | 未发现相关测试 |

“未发现”限定于本报告的路径和静态检索范围，不证明仓库外或未检查模块绝不存在。

## 5 独立 Addon 扩展判断

已有模型继承、工具装饰器、XML 工具记录和独立 addon 扩展先例。例如 llm_tool_ocr_mistral 通过独立 addon 扩展 ir.attachment 并注册工具，说明通用工具扩展模式存在。

但 Office MIME 拒绝逻辑位于 llm 与 llm_thread；附件到 Provider 的内容格式化也由 Provider 处理。能否仅靠独立 addon 安全覆盖聊天拒绝、读写流程和各 Provider，而不修改上游源码，尚未验证。因此初步判断为“存在扩展模式先例；端到端无上游修改待 Spike 确认”。

## 6 后续 Technical Verification / Spike 建议

1. 验证独立 addon 可使聊天 Office 附件进入受控工具流程，同时阻止未解析 Office 二进制直接发送给不支持它的 Provider。
2. 运行时验证当前用户对附件、消息、线程、根记录和关联字段的 ACL、记录规则及跨用户/跨公司隔离。
3. 对真实 xlsx 样本验证公式、缓存值、样式、合并单元格、行列布局、外链和复杂对象保留情况。
4. 对真实 docx 样本验证段落、表格、页眉页脚、图片、文本框、域、修订标记、嵌入对象和分页边界。
5. 验证 MIME 伪装、损坏/加密文件、异常压缩结构、文件大小/展开容量和附件重复提交。
6. 验证映射 schema 拒绝、用户确认、工具错误反馈、生成附件授权与结果追溯。
7. 基于 Odoo 运行时及代表性样本实测后再选择 Office 库；本 SRS 不预先指定库。

## 7 调查结论

当前 Odoo-LLM 可提供聊天、附件关联和通用工具调用扩展宿主，但源码尚未提供本需求所需的 Office 结构读取、受控渲染、完整格式安全准入、业务映射确认或 Skill 生命周期。OCR 和知识库当前能力不能替代这些功能。后续 DDD/TDD 应引用本调查，并关闭适用 Spike；若 Spike 未完成，应如实记录风险和未验证边界。
