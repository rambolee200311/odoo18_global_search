# M2 阶段底层架构与核心代码白皮书

| 项目 | 值 |
|---|---|
| 快照日期 | 2026-10-29 |
| 范围 | 当前工作树中的 Odoo 18 CE、自有 odoo-llm fork、office_engine_m2、office_core |
| 文档状态 | 工作树快照；未提交 |
| 运行环境 | 本地 Odoo 18 CE，数据库 odoo18ce，聊天 Thread 5180 |
| 本次 Provider | 配置中的 OpenAI gpt-5.6-luna；真实调用证据见下文 |
| 限制 | 本文记录现状和缺口，不把设计意图当作运行证据 |

> 本文展示当前实际源码片段及文件位置。代码片段只保留关键语句；省略处不代表源文件中没有其他逻辑。路径均相对仓库根目录。

## 执行摘要

M2 已接入 llm_assistant 的 Thread 历史、Provider 工具调用循环和 llm.tool 注册机制。用户消息由原生聊天入口发布一次，OpenAI Provider 根据完整历史和工具 schema 发起工具调用；M2 工具负责 Office Session、字段与目标校验、Proposal revision、预览生成和最终确认。office_core 执行通用 XLSX 重复行扩展，office_verify 对输出回读检查。

本次完成字段语义元数据、通用地址选择约束、合并单元格视觉标签/写入目标关联，并删除 `run_mapping()`、`revise_mapping_from_chat()` 旧本地 Provider/正则路由函数。真实 `gpt-5.6-luna` 在 8091 调用 Retriever、Context、Preview 和 Finalize 工具。预览与正式 XLSX 附件卡片均显示正确文件名/MIME；服务器访问日志记录了正式文件下载 HTTP 200。M1 提交后的输出元数据通过独立游标返回，M2 不再从旧快照重读附件；模型可见的 Finalize 结果只含文件名/MIME 和“附件已发到聊天”状态，不含附件 ID 或下载 URL，避免模型拼接出错误链接。

正式文件回读确认：B4 写入 Odoo 的完整仓库 `contact_address` 字符串、B7 写入完整客户地址，订单号在合并写入锚点 E17、空参考号 E19 留白；6 行明细位于 23–28，合计在 29 行，扩展公式和合并区域均保留。仓库地址字符串末尾的 `Netherlands` 与其 San Francisco 地址存在源数据一致性疑点，不能据此宣布国家信息正确。这里的 CMR 字段名只出现在模板与本次业务验收资料中，通用引擎没有按模板名称分支。仍有工具候选数量上限、单一重复区域和受限公式语法等通用能力边界，详见“遗留代码与技术债”。

## 1. 当前真实调用链

### 1.1 架构图

~~~mermaid
sequenceDiagram
    participant UI as llm_thread 聊天 UI
    participant Route as /llm/thread/generate
    participant Native as llm_assistant Thread
    participant Provider as OpenAI gpt-5.6-luna
    participant Retriever as odoo_record_retriever
    participant Office as office.mapping.tool
    participant Core as office_core + M1
    participant Verify as office_verify
    participant Store as Discuss Store / 前端

    UI->>Route: 用户正文 + attachment_ids
    Route->>Native: generate(message, attachment_ids)
    Native->>Native: M1 附件预检；消息只发布一次
    Native->>Native: M2 绑定 Office tools（活动 Office Thread）
    Native->>Provider: 原生历史 + tools + Office 规则
    Provider-->>Native: Assistant tool_call
    Native->>Retriever: 通过 llm.tool 执行 Odoo 记录检索
    Retriever-->>Provider: ORM 当前用户可读结果
    Provider-->>Native: office_prepare_context tool_call
    Native->>Office: 检查 Thread、上传附件、Session、目标、字段
    Office-->>Provider: target_manifest、allowed_fields、repeat rows、限制
    Provider-->>Native: office_save_mapping_preview tool_call
    Native->>Office: 校验 Proposal / revision / 实际差异
    Office->>Core: expand_repeat_rows + render_candidate
    Core-->>Office: XLSX 候选
    Office->>Verify: verify_output 回读验证
    Verify-->>Office: PASS / FAIL
    Office->>Store: 生成 preview attachment 和 mail.message
    Native-->>Store: message_create + mail.message/ir.attachment Store payload
    Store-->>UI: 更新原生消息流与可下载 XLSX 卡片
    Office-->>Provider: 工具结果 preview_ready
    Provider-->>UI: 原生助手最终文本
~~~

### 1.2 HTTP、原生 Thread 与附件边界

1. mymodules/odoo-llm/llm_thread/controllers/main.py:86-114 提供认证后的 /llm/thread/generate SSE 入口，解析 Thread、正文和附件 ID。
2. mymodules/office_engine_odoo/models/llm_thread.py:70-103 在进入原生循环前执行 Office 附件类型、宏扩展名和文件大小预检；合法文件仍调用 super().generate(...)。
3. mymodules/odoo-llm/llm_thread/models/llm_thread.py:374-411 由原生 generate() 发布用户消息，然后调用 generate_messages()。
4. M1 在 mymodules/office_engine_odoo/models/llm_thread.py:105-118 保留正常历史，只在“不支持附件”检查阶段排除 Office 附件；mail.message._get_attachments_by_mimetype() 在 :125-155 对 Office 返回空附件 recordset。因此上传消息正文仍被 Provider 序列化，Office 二进制不进入 OpenAI 的图像、PDF、音频或文本附件序列化路径。
5. Provider 序列化见 mymodules/odoo-llm/llm_openai/models/mail_message.py:12-96：正文经 html2plaintext 转为文本；只有附件 helper 返回的图片/PDF/音频/文本附件才会形成对应 payload。Office 文件本身由服务端 M1 inspector 读取。

### 1.3 原生工具调用循环与 M2 扩展

mymodules/odoo-llm/llm_assistant/models/llm_thread.py:225-284 负责原生循环：读取消息历史、调用 Assistant response、执行 assistant tool calls、保存工具结果并继续生成。原生 _generate_assistant_response() 在 :289-329 通过 model_id.chat() 调 Provider；OpenAI 请求/工具格式化代码在 mymodules/odoo-llm/llm_openai/models/openai_provider.py。

M2 mymodules/office_engine_m2/models/llm_thread.py:99-113 只在活动 Office Session 下绑定 Office tools，随后委托 super().generate()。_prepare_chat_kwargs() 在 :115-154 选出 Office tools 并加入 Office 操作契约。_execute_tool_call() 在 :234-275 委托原生工具执行，并对预览附件补充实时 Store 事件。

**注意：** mymodules/office_engine_m2/models/llm_thread.py:156-188 为 Office Thread 重载了 _generate_assistant_response()，直接调用 model_id.chat() 并使用原生非流式响应处理函数。它没有重写 Provider 的工具循环；工具执行仍由 llm_assistant.generate_messages() 驱动。但它复制了原生响应处理的一部分，并为当前 GPT-5 Chat Completions 配置加 reasoning_effort="none"，是需要持续跟踪上游变化的技术债。

## 2. 工具注册与实际 JSON Schema

### 2.1 Odoo 工具记录注册

mymodules/office_engine_m2/data/office_tools.xml 将工具名映射到 office.mapping.tool 的方法。两个核心工具实际记录如下：

~~~xml
<record id="llm_tool_office_prepare_context" model="llm.tool">
    <field name="name">office_prepare_context</field>
    <field name="implementation">function</field>
    <field name="decorator_model">office.mapping.tool</field>
    <field name="decorator_method">office_prepare_context</field>
    <field name="active">True</field>
    <field name="read_only_hint">False</field>
    <field name="destructive_hint">True</field>
</record>
<record id="llm_tool_office_save_mapping_preview" model="llm.tool">
    <field name="name">office_save_mapping_preview</field>
    <field name="implementation">function</field>
    <field name="decorator_model">office.mapping.tool</field>
    <field name="decorator_method">office_save_mapping_preview</field>
    <field name="active">True</field>
    <field name="read_only_hint">False</field>
    <field name="destructive_hint">True</field>
</record>
~~~

来源：mymodules/office_engine_m2/data/office_tools.xml:3-27。

office_prepare_context 的 Python 参数为 target_model: str, target_record_id: int；office_save_mapping_preview 的参数为 session_id: int, expected_revision: int, proposal: dict, repeat_rows: list | None（`office_mapping_tools.py:411`、`:682`）。`mymodules/office_engine_m2/models/llm_thread.py:289-400` 用 llm.tool 现有 Pydantic 签名构建器生成基础 schema，并为 Proposal 与 repeat_rows 增加封闭 JSON Schema。关键 schema 片段：

~~~python
schema["properties"]["repeat_rows"] = {
    "type": "array",
    "maxItems": 1,
    "items": {
        "type": "object",
        "additionalProperties": False,
        "required": ["collection_field", "sheet", "start_row", "columns"],
        "properties": {
            "collection_field": {"type": "string"},
            "sheet": {"type": "string"},
            "start_row": {"type": "integer", "minimum": 1},
            "columns": {"type": "array", "minItems": 1, "maxItems": 64, ...},
        },
    },
}
schema["properties"]["proposal"] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["schema_version", "mappings", "clarifications", "skipped_targets"],
    "properties": {
        "schema_version": {"type": "string", "enum": ["m2.mapping-proposal.v1"]},
        "mappings": {"type": "array", "items": {
            "type": "object",
            "additionalProperties": False,
            "required": ["element_id", "value_type"],
            "properties": {
                "element_id": {"type": "string"},
                "source_field": {"type": "string"},
                "source_fields": {"type": "array", "minItems": 2, "maxItems": 8},
                "formula": {"type": "string", "maxLength": 512},
                "value_type": {"type": "string",
                    "enum": ["string", "number", "boolean", "formula"]},
            },
        }},
    },
}
~~~

来源：mymodules/office_engine_m2/models/llm_thread.py:289-400。上面 ... 是文档摘录省略号，不是运行时 schema。实际列 schema 额外限定了大写列标识、单一映射模式（source_field / fallback_fields / formula），每个 repeat 操作最多一个区域。

### 2.2 Context 和 Preview 的服务端门槛

- `office_prepare_context()` 位于 `mymodules/office_engine_m2/models/office_mapping_tools.py:411` 起。它要求本轮先通过 Retriever 得到精确记录；使用当前 Thread 最新合法 XLSX 上传，调用 M1 inspector 得到模板结构；创建或读取同 Thread、用户、公司、附件、目标记录绑定的 Session；返回 target_manifest、template_text、allowed_fields、现有 Proposal、重复行集合候选和能力边界。
- `office_save_mapping_preview()` 位于同文件 `:682` 起。验证 Session 属于当前 Thread/用户、expected_revision 一致、Proposal JSON 合法，随后调用 validate_proposal()；比较规范化 Proposal 和上下文，只在真实差异时写 revision 并渲染预览。若无变化且已有预览，返回 status: unchanged。
- `office_finalize()` 位于同文件 `:908` 起。要求最新用户消息严格等于批准的确认短语，并绑定 session_id、revision、proposal revision、预览 revision；再进入 M1 最终渲染及数据新鲜度验证。只预览不代表已经正式归档。

## 3. 字段候选和权限过滤：没有静态业务模型白名单

### 3.1 当前 allowed_fields 如何产生

当前实现没有一个固定的 allowed_fields = ["partner_id.name", ...] 常量。chat_entrypoint.py 动态枚举字段候选；关系字段的常用名称仅影响排序，不构成硬白名单。候选必须逐段通过当前用户的模型读取权限与字段读取权限，最多经过两段 many2one；敏感凭证、薪资、银行账户等字段名被过滤。结果还有候选数量上限。

当前常用字段排序片段（mymodules/office_engine_m2/services/chat_entrypoint.py:25-57）：

~~~python
_RELATED_FIELD_PRIORITY = (
    "contact_address",
    "name",
    "display_name",
    "complete_name",
    "street",
    "street2",
    "city",
    "zip",
    "ref",
    "barcode",
    "default_code",
    "weight",
    "net_weight",
    "gross_weight",
    "volume",
)
~~~

字段路径通过权限和类型检查后，工具再附上 Odoo 字段的显示标签及帮助文本。元数据只辅助模型做语义选择，不扩大可读范围；读取时仍按当前用户的 ORM 权限重新校验。实现位置：`chat_entrypoint.py:_field_metadata()`。

~~~python
descriptor = {
    "type": value_type,
    "label": str(field.string or segments[-1])[:200],
}
help_text = field.help
if isinstance(help_text, str) and help_text.strip():
    descriptor["help"] = help_text.strip()[:500]
result[path] = descriptor
~~~

工具返回结构示例（值为当前 Odoo registry 元数据；示例中的中文 label 取决于字段翻译）：

~~~json
{
  "warehouse_id.partner_id.contact_address": {
    "type": "string",
    "label": "Contact Address",
    "help": "..."
  }
}
~~~

该路径不是硬编码的地址特例；任意获准关系路径都使用同一段元数据生成逻辑。最终真实映射由 `gpt-5.6-luna` 结合这些元数据和模板标签选择。

这些是候选优先级，不是将每个路径无条件放行。真实授权判定函数 `mymodules/office_engine_m2/services/ai_orchestrator.py:24-65` 的关键逻辑：

~~~python
def _authorized_scalar_field_type(target, field_name):
    if (
        not isinstance(field_name, str)
        or not field_name
        or field_name.count(".") > 2
        or _is_sensitive_field(field_name)
    ):
        return None
    try:
        segments = field_name.split(".")
        current = target
        for index, segment in enumerate(segments):
            model = current.env[current._name]
            model.check_access("read")
            model.check_field_access_rights("read", [segment])
            field = model._fields.get(segment)
            if not field:
                return None
            if index == len(segments) - 1:
                return _VALUE_TYPES.get(field.type)
            if field.type != "many2one":
                return None
            related_model = current.env[field.comodel_name]
            related_model.check_access("read")
            current = current[segment]
            if current:
                current.check_access("read")
            else:
                current = related_model
        return None
    except (AccessError, UserError):
        return None
~~~

根候选、one-hop 和 two-hop 字段从真实模型元数据中发现并调用上述检查：`chat_entrypoint.py:70-198`。字段标签/帮助描述由 `:199-234` 动态取得；repeat 集合候选也由可读 one2many 和其可读字段动态生成：`:236-280`。当前上限包括 500 个主记录候选、160 个 repeat 字段及 20,000 次嵌套候选检查。部署数据外发策略另由 `:60-68` 的 `OFFICE_ENGINE_M2_DATA_POLICY_APPROVED=1` 开关控制；这不是“本地 Mock 自动放行”。

### 3.2 本次真实样例的校正结果

本次第一份历史预览曾把 B4 写成 `YourCompany`，证明“字段路径可见/授权”与“语义上确实是完整地址”不是一回事。之后改用字段元数据 label/help，并在通用 System Prompt 要求比较 address 语义后，新的真实预览及正式输出 B4 回读为 `warehouse_id.partner_id.contact_address` 的完整值。该值包含 San Francisco 地址信息，但末尾的 Odoo 来源值为 `Netherlands`；代码不能替业务数据纠错，因而本次证明了完整地址字段被选择和写入，不能证明仓库主数据的国家值符合业务预期。字段 schema 与 ACL 本身仍不能保证语义正确；业务验收必须回读输出值，不得仅因工具返回 `preview_ready` 宣告映射正确。

odoo_record_retriever 的 M2 适配在 mymodules/office_engine_m2/models/llm_thread.py:393-652：活动 Office Session 下不设模型名白名单，仍执行用户环境的 ACL/Record Rules、字段访问检查、Session 绑定记录 ID、related collection ID 集合、当前公司域和敏感字段过滤；不使用 sudo() 执行数据查询。基础 Retriever 的实际 search_read 在 mymodules/odoo-llm/llm_tool/models/llm_tool_record_retriever.py:18-47。

### 3.3 合并单元格的可写目标与视觉标签

M1 inspection 对每个 XLSX 元素暴露 `merged_range`；M2 TargetManifest 将合并锚点、区域和邻近可见标签一并提供给模型。原标签文本保留在模板结构中，目标的 `write_target` 指向实际合并区域锚点，而不是将 F16/F18 这类视觉标签单元格当作写入位置：

~~~python
target = {
    "element_id": item.element_id,
    "required": required,
    "writable": True,
    "allowed_value_types": ["string", "number", "formula"],
    "approved_to_skip": not required,
}
if merged:
    target["merge_range"] = merged
    target["write_target"] = item.element_id
if visual_labels:
    target["visual_labels"] = [
        {"element_id": element_id, "text": text, "relation": relation}
        for _rank, _distance, element_id, text, relation in visual_labels[:3]
    ]
~~~

代码位置：`mymodules/office_engine_m2/services/chat_entrypoint.py:_template_context()`；底层合并范围元数据来自 `mymodules/office_core/models.py:Element.merged_range` 和 `mymodules/office_core/engine.py` 的 XLSX inspection。合并区域只影响目标解释和锚点写入；模板中非公式且 M1 标记可写的占位/旧值单元格可以作为覆盖目标，未被 Proposal 指定的内容仍保留。

## 4. 重复行与公式：从 AI 参数到 M1

### 4.1 Server 先重算明细行数

模型只提供集合字段、工作表、起始行和列映射；模型不能提供记录数量或任意行 ID。`_repeat_mapping_context()`（`mymodules/office_engine_m2/models/office_mapping_tools.py:47` 起）读取绑定业务记录上的 one2many，在当前用户权限下检查目标和每条明细，再从 Server 计算 `len(records)`。关键转换：

~~~python
expansion = expand_repeat_rows(
    source,
    {
        "action": "insert_repeat_rows",
        "sheet": sheet,
        "start_row": start_row,
        "record_count": len(records),
        "columns": {
            item["column_id"]: item.get("source_field")
            or (item.get("source_fields") or ["formula"])[0]
            for item in clean_columns
        },
    },
    _resource_budget(),
)
expanded = inspect_document(expansion.content, filename, mime, _resource_budget())
manifest, template_text = _template_context(expanded)
~~~

`office_save_mapping_preview()` 随后按 Server 生成的 target_rows 展开 Proposal：每一条实际数据行得到 namespaced source 字段，`{row}` 公式模板替换成真实 Excel 行号（`office_mapping_tools.py:682` 起）。Render bridge 再从 Session 的授权集合重新读取最新行，校验行数与 Proposal 一致，复算 repeat-row 指令，创建 M1 writes（`mymodules/office_engine_m2/services/render_bridge.py:77` 起）。因此 expand_repeat_rows 不是被放在 prompt 里“告诉模型已支持”；它在工具和 M1 两处真实执行。

### 4.2 office_core 的通用结构扩展实现

mymodules/office_core/row_expansion.py:414-486 接受通用结构命令，不读取模板名、模型名或业务标签。其关键步骤：

~~~python
def expand_repeat_rows(source, instruction, budget):
    required = {"action", "sheet", "start_row", "record_count", "columns"}
    if set(instruction) != required:
        raise _fail("重复行结构指令字段无效。")
    if instruction.get("action") != "insert_repeat_rows":
        raise _fail("不支持的结构指令。", "OFFICE_UNSUPPORTED_FEATURE")
    # 校验 sheet、start_row、record_count、columns 和资源预算
    summary_row = find_summary_row(
        source, sheet_name=sheet, first_row=start_row, budget=budget
    )
    capacity = summary_row - start_row
    inserted_rows = max(0, record_count - capacity)
    content = expand_xlsx_rows(
        source, sheet_name=sheet, first_row=start_row,
        row_count=record_count, summary_row=summary_row, budget=budget
    ) if inserted_rows else source
    return RepeatRowsResult(
        content=content, sheet=sheet, start_row=start_row,
        record_count=record_count, inserted_rows=inserted_rows,
        summary_row_before=summary_row,
        summary_row_after=summary_row + inserted_rows,
        columns=normalized_columns,
    )
~~~

expand_xlsx_rows()（:289-410）复制前一明细行样式/公式原型，移动汇总行之后的行，更新公式引用和行区间元数据，再扩展已有 SUM 汇总公式。它要求模板中已经存在可验证的汇总公式行；它不是通用的“自动猜业务合计位置”，也不会任意创建用户业务公式。

### 4.3 公式、Fallback、空值边界

- Mapping 支持 direct field、同类型有序 fallback、受限算术公式。
- office_mapping_verify/formula.py:13-89 只接受同表单元格引用、数字、括号和 + - * /；拒绝 Excel 函数、范围、跨表/外部链接、名称和字符串。=F{row}*3 经 Server 替换行号后属于可解析算术公式。
- 模板中已经存在的公式（例如 =SUM(F23:F28)）由 M1 保留并在插行时平移/扩展，不代表模型可提交任意 SUM() 公式。
- render_bridge.py:205-237 按 source_fields 顺序取第一个非 None、非 False、非空字符串值；所有字段为空且目标类型是 string 时写空字符串。
- Conditions、任意 Excel 函数、跨表/外部公式、.docx 当前属于显式不支持项。相关契约在 office_mapping_tools.py:596-617。

## 5. 预览渲染、验证及正式文件

### 5.1 Preview

`render_preview()` 位于 `mymodules/office_engine_m2/services/render_bridge.py:257` 起：

1. 校验当前用户拥有 Session、revision 匹配、状态可预览、模板大小限制。
2. _compile_plan() 重新检查 thread/message/attachment 权限和绑定关系，重新读取数据和 repeat rows，并产生 M1 plan。
3. office_core.render_candidate() 生成候选文件。
4. office_verify.verify_output() 回读校验；失败时不发布预览。
5. 新建非公开 ir.attachment，文件名包含 .xlsx 和正确 MIME。
6. 乐观锁保存 Preview 并递增服务端 revision；新预览成功后删除旧 preview attachment。
7. _post_preview_message() 将附件关联到原 Thread 的 assistant 消息。

### 5.2 Finalize

`office_finalize()`（`office_mapping_tools.py:908` 起）检查最近一条当前用户消息必须是精确确认短语，且 session_id、expected_revision、proposal_revision 与已预览版本一致。`render_confirmed_mapping()`（`render_bridge.py:356` 起）重新检查来源数据快照、权限、模板指纹及幂等 request_uuid；数据有变化会要求重新确认，不静默归档。

M1 将正式输出写入私有 `ir.attachment` 后，在持有已验证 Thread 的新环境中以当前用户权限检查 request/thread/output，再调用 `thread.message_post()` 创建含正式附件的 assistant 消息。附件与聊天消息在同一输出事务内提交；返回 `filename`、`mimetype` 和 `delivery_message_id`。已生成请求的幂等重试也会补齐/复用唯一聊天附件消息。关键实现位于 `mymodules/office_engine_odoo/models/office_document_request.py:_ensure_output_chat_message()`、`_deliver_result()`、`_existing_result()` 和 `_ensure_output_delivery_message()`：

~~~python
existing = env["mail.message"].search(
    [("model", "=", thread._name), ("res_id", "=", thread.id),
     ("llm_role", "=", "assistant"), ("attachment_ids", "in", output.ids)],
    limit=1,
)
if existing:
    return existing.id, False
message = thread.message_post(
    body=_("已生成并归档正式 Office 文件。"),
    llm_role="assistant",
    author_id=False,
    attachment_ids=[output.id],
)
return message.id, True
~~~

M2 `render_confirmed_mapping()` 在服务端内部返回已提交输出 ID、文件名/MIME 和附件消息 ID；`office_finalize()` 先验证这些交付元数据，再把模型可见结果收敛为状态、Session、Proposal revision、文件名/MIME 及附件已发到 Thread 的布尔值。它不在一个已过期的外层游标中重新读取 M1 刚提交的附件，也不向模型暴露附件 ID 或下载 URL。系统提示明确要求模型指向聊天附件卡片，禁止自行构造 URL 或 `attachment://` 链接：

~~~python
return {
    "status": "completed",
    "session_id": session.id,
    "proposal_revision": session.confirmed_revision,
    "filename": filename,
    "mimetype": mimetype,
    "attachment_posted_to_thread": True,
}
~~~

`llm_thread.py` 同时要求只有在 `attachment_posted_to_thread=true` 时才告知用户附件可下载；缺少该标志时，模型不得声称交付成功。当前真实浏览器流程已执行 Preview、明确确认、Finalize、幂等重复确认，并从 Thread 附件卡片实际下载正式文件，证据见 §7。

## 6. HTML 与实时附件卡片渲染

### 6.1 裸 HTML / 假附件链接

自有 fork 文件 mymodules/odoo-llm/llm_thread/models/llm_thread.py:287-315 的 _process_llm_body() 会识别被实体编码的 HTML 片段、移除模型伪造的 attachment:// 链接，再将 Markdown/HTML 规范化并经 Odoo html_sanitize()：

~~~python
decoded = unescape(content)
if decoded != content and re.search(
    r"</?(?:p|ul|ol|li|div|span|strong|b|em|i|code|pre|br|a|h[1-6])\b",
    decoded,
    re.IGNORECASE,
):
    content = decoded
content = re.sub(r"\s+href\s*=\s*([\"'])attachment://[^\"']*\1", "", content, flags=re.IGNORECASE)
content = re.sub(r"attachment://\d+", "", content, flags=re.IGNORECASE)
rendered = markdown2.markdown(emoji.demojize(content))
return tools.html_sanitize(rendered, sanitize_attributes=True, strip_classes=True)
~~~

对应回归测试 `mymodules/office_engine_m2/tests/test_native_chat_integration.py:122-141` 检查 <p> / <ul> 不以转义文本显示、伪 attachment:// 不残留。

### 6.2 实时附件卡片缺元数据 Bug

根因是原生 mail.message.to_store_format() 只提供 message 行数据；实时 Store 同时需要 ir.attachment 的 name 与 mimetype 才能立即绘制 XLSX 图标和下载卡片。M2 修复后的 mymodules/office_engine_m2/models/llm_thread.py:190-206, 234-275 从真实 preview 消息构造完整 Store payload：

~~~python
def _office_message_store_payload(self, message):
    from odoo.addons.mail.tools.discuss import Store
    store = Store()
    message._to_store(store)
    payload = store.get_result()
    message_data = next(
        item for item in payload.get("mail.message", []) if item["id"] == message.id
    )
    return message_data, payload

# 成功的 preview tool 后：
message_data, store_data = self._office_message_store_payload(preview_message)
yield {
    "type": "message_create",
    "message": message_data,
    "store_data": store_data,
}
~~~

mymodules/odoo-llm/llm_thread/static/src/services/llm_store_service.js:145-173 现在先插入 data.store_data，再把 message 加入 Thread 的消息集合；以前只有 mail.message 行会令新附件在刷新前呈匿名灰盒。

## 7. 最近真实浏览器验证、Finalize 与文件回读

### 7.1 实际运行证据

- 本地页面：http://127.0.0.1:8091/odoo/action-631?debug=assets&active_id=llm.thread_5180。
- Provider/model：实际配置的 OpenAI `gpt-5.6-luna`；Odoo 日志记录 `POST https://api.openai.com/v1/chat/completions` 的 200 响应。
- 真实预览轮次：模型调用 `odoo_record_retriever`、`office_prepare_context`、`office_save_mapping_preview`；工具返回成功，Thread 出现 `preview_S05457_CMR-危险品禾麦CMR模板.xlsx` 绿色 XLSX 附件卡片。
- 真实 Finalize：用户在浏览器输入“确认并生成正式文件”，模型调用 `office_finalize` 成功；Thread 显示正式生成成功和输出文件名 `office-output-79d641c7-abb3-5f74-9b59-f86a00b768e3.xlsx`。M1 将正式附件挂到 Thread 的 assistant 消息，MIME 为 XLSX。
- 下载证据：Odoo server log `debug_logs/odoo_181.log` 记录当前用户对正式附件 `16673` 的下载请求 `GET /web/content/16673?download=true HTTP/1.1 200`（2026-10-29 02:41:10；此前带 filename/unique 参数的请求也返回 200）。随后通过浏览器附件卡片执行下载，Playwright download 事件返回本地路径 `/Users/lijianqiang/Downloads/office-output-79d641c7-abb3-5f74-9b59-f86a00b768e3.xlsx`，本地文件为 9,373 字节；与 ORM 导出回读副本 SHA-256 一致：`a084fc65bb79b54c314cc443057449bacc2f8beb1427de35574020e8aa5e38fc`，因此浏览器下载落盘已确认。
- Odoo ORM 在当前用户读取附件 `16673` 的字节并复制到 `/private/tmp/office-output-79d641c7-abb3-5f74-9b59-f86a00b768e3.xlsx`，用于本地回读。浏览器客户端阻止了直接在新标签导航到 `/web/content` 的尝试；因此 workbook 内容验证是 ORM 导出副本检查，不将其描述成桌面下载落盘验证。

### 7.2 下载文件回读结果

使用 Python zipfile.testzip() 和 openpyxl.load_workbook(data_only=False) 读取上述正式附件的 ORM 导出副本：

| 检查项 | 实际结果 | 判定 |
|---|---|---|
| 文件可打开 / OOXML ZIP | zip_integrity=PASS；工作表 Blad1 可读 | PASS |
| B3 | Azure Interior | PASS（值存在） |
| B4 | `My Company (San Francisco)\n250 Executive Park Blvd, Suite 3400\n\n94134 San Francisco\nNetherlands` | 字段映射/写入 PASS；业务地址正确性 INCONCLUSIVE：Odoo 来源值的国家与 San Francisco 地址不一致 |
| B7 | `Azure Interior\n4557 De Silva St\n\nFremont CA 94538\nUnited States` | PASS：客户完整地址 |
| 订单号 | E17=`S05457` | PASS：写入标签 F16 下方合并区域 E17:H17 的锚点 |
| 参考号 | E19=None | 空值保持为空 |
| F16 / F18 | 保留原模板标签 REF号 / Unloading ref号 | 标签保留；实际合并目标分别为 E17:H17、E19:H19 |
| 明细行 | B23-B28 共 6 行，末行 Office Lamp | PASS |
| 模板公式 | F23-F28 为 =D行*E行；G23-G28 为 =F行*3；F29/G29 为 SUM 汇总 | PASS（公式文本保留） |
| 合并单元格 | 15 个合并区域仍存在 | PASS |
| 计算标志 | fullCalcOnLoad=True | PASS |
| 正式文件 | `office-output-79d641c7-abb3-5f74-9b59-f86a00b768e3.xlsx` | PASS：Finalize 成功、正式附件已挂到 Thread、服务器下载请求 HTTP 200 |

**技术闭环结论：本次 S05457 XLSX 的真实 Provider、检索、映射、预览、用户确认、M1 正式生成、附件卡片和 Odoo 下载端点均有证据。** B4 完整反映 Odoo 的 `contact_address`，但该来源地址自身的国家字段与 San Francisco 地址不一致，因此 B4 的业务主数据正确性仍为 INCONCLUSIVE，需要由数据负责人确认来源记录。6 行数据、锚点、留空和公式文本的文件结构回读通过；公式值为公式文本且工作簿标记打开时全量重算，本机未以桌面 Excel/WPS 实际重算公式缓存。

### 7.3 附件实时 Store 定向测试

新增 `test_preview_tool_streams_attachment_metadata_to_native_chat_store`：创建带 XLSX MIME 和名称的 preview attachment，模拟原生 tool call 结果，断言助手实时事件只对该 preview message 发出一次，并在 Store payload 中包含 mail.message、ir.attachment、附件 name 和 mimetype。测试位置：`mymodules/office_engine_m2/tests/test_native_chat_integration.py:201` 起；正式输出消息幂等测试在 `mymodules/office_engine_odoo/tests/test_attachment_identity.py:20` 起。

本次最终回归命令（日志文件 `/private/tmp/m2_final_all_regression_after_finalize_link.log`）：

~~~sh
PYTHONPATH=/private/tmp/cc_m2_002_shellshim ./venv/bin/python odoo-bin -c odoo.conf -d odoo18ce --http-port=0 -u office_engine_m2,office_engine_odoo --test-enable --test-tags /office_engine_m2,/office_engine_odoo --stop-after-init --log-level=test --logfile=/private/tmp/m2_final_all_regression_after_finalize_link.log
~~~

结果：Odoo Addon 统计行分别报告 `office_engine_m2: 126 tests`、`office_engine_odoo: 23 tests`；最终汇总行为 `0 failed, 0 error(s) of 117 tests`。三个计数口径不相加，本文保留日志原值，不把它们解释为 149 个唯一用例。这是共享 `odoo18ce` 数据库的 Odoo TransactionCase 回归，不是隔离数据库；运行升级了两个 Addon，Odoo 日志包含测试后 filestore GC。既有环境仍报告未加载模块 `wd_advanced_m2o_record_panel`、`wd_evidence_album`、`wd_qooling_app`，与上述两个 Addon 的测试结果无关。

## 8. 遗留代码与技术债清单

1. **[数据问题] 仓库地址来源值有地理信息不一致。** 本次授权的 `warehouse_id.partner_id.contact_address` 返回 San Francisco 街道/邮编但以 Netherlands 结束；引擎按该授权来源原样写入，没有擅自修正。数据负责人应核对对应仓库联系人国家字段。
2. **[技术债] 候选字段发现受性能阈值限制。** `chat_entrypoint.py` 有字段数和 nested-check 上限；超出预算的合法候选可能不会出现在模型字典里。优先级只影响候选顺序，不是字段白名单，也不保证任何业务字段被发现。
3. **[技术债] repeat rows 不是任意表格变换。** 当前 Proposal 至多一个 repeat region、64 列；结构扩展依赖可识别的聚合公式来定位合计行。多个重复区域、复杂表格对象、跨表依赖没有交付证据。
4. **[技术债] 新公式只支持安全算术子集。** 映射公式接受单元格引用、数字、括号、`+ - * /`；不支持模型新增任意 Excel 函数、外链、跨表或命名区域。模板已有公式可由 M1 扩展并保留。
5. **[技术债] Thread 响应方法有局部重载。** `office_engine_m2/models/llm_thread.py` 为 Office 工具流复用原生调用，但定制 `_generate_assistant_response()` 并设置当前 Provider 的参数；上游 Assistant 变更时仍需兼容回归。
6. **[技术债] 人工文件落盘与公式缓存未在桌面 Office 程序核验。** Odoo 下载请求返回 HTTP 200，且以 ORM 读取的正式附件副本可解析；未核实浏览器 Downloads 目录，也未启动 Excel/WPS 重新计算公式缓存。
7. **[技术债] 本次工作树原有未提交改动很多。** 本次未暂存、提交、清理或覆盖；全量回归在共享 DB 上升级模块并触发 Odoo 测试清理。项目有既存的第三方模块未安装警告。

## 9. 代码与证据索引

| 职责 | 真实文件 |
|---|---|
| M2 Tool schema / Retriever adapter / Session tool gating | mymodules/office_engine_m2/models/llm_thread.py |
| Office Context / Preview / Finalize 工具实现 | mymodules/office_engine_m2/models/office_mapping_tools.py |
| Tool 数据库注册 | mymodules/office_engine_m2/data/office_tools.xml |
| 动态字段发现 / TargetManifest / 数据外发 gate | mymodules/office_engine_m2/services/chat_entrypoint.py |
| 字段读取授权与类型辅助逻辑（不含聊天意图路由） | mymodules/office_engine_m2/services/ai_orchestrator.py |
| M1 plan、预览、正式渲染和幂等 | mymodules/office_engine_m2/services/render_bridge.py |
| 通用 XLSX 重复行扩展 | mymodules/office_core/row_expansion.py |
| Mapping JSON 与算术公式解析 | mymodules/office_mapping_verify/ |
| M1 读回验证 | mymodules/office_verify/verify.py |
| Office 上传预检与二进制排除 | mymodules/office_engine_odoo/models/llm_thread.py |
| 原生 SSE 入口 / Assistant loop / Provider serializer | mymodules/odoo-llm/llm_thread/、llm_assistant/、llm_openai/ |
| HTML 与实时 Store 回归测试 | mymodules/office_engine_m2/tests/test_native_chat_integration.py |
| 本次自动化日志 | /private/tmp/m2_preview_attachment_stream_test.log |
| 正式输出 ORM 导出回读副本 | /private/tmp/office-output-79d641c7-abb3-5f74-9b59-f86a00b768e3.xlsx |
| 浏览器与最终回归日志 | debug_logs/odoo_181.log；/private/tmp/m2_final_all_regression_after_finalize_link.log |

## 10. Git 与交付声明

分支 `main`；工作树含大量用户及当前任务未提交改动。本次没有 reset、checkout、清理、暂存或提交。白皮书仍为未提交文件。最终全量回归日志在 `/private/tmp/m2_final_all_regression_after_finalize_link.log`。浏览器端已保留 Thread 5180，显示真实 Provider 的正式确认、幂等重复确认和绿色 XLSX 附件卡片；用户从卡片下载到本地 XLSX。

**最终结论：** 通用字段元数据与合并单元格语义接线后，真实 Provider 的 Preview 与 Finalize 成功，正式 XLSX 经 Odoo 下载端点返回 HTTP 200，ORM 导出副本中的明细、模板锚点及公式结构回读通过。B4 的字段映射成功，但 Odoo 仓库 `contact_address` 源值带有“San Francisco 地址 + Netherlands 国家”的一致性疑点，故该地址的业务正确性不能判 PASS。公式文本和工作簿重算标记得到验证，但没有在桌面 Excel/WPS 打开并刷新公式计算缓存。旧自然语言路由函数已不在 `ai_orchestrator.py` 中；该文件目前只保留字段授权、Retriever 访问及映射类型辅助逻辑。
