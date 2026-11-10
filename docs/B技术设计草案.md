# Office Engine — Phase B 技术设计草案 v0.3

**项目：** Odoo 18 CE / Office Engine M2
**阶段：** Phase B — Technical Design
**状态：** FROZEN v0.3 — 用户于 2026-11-06 批准冻结；DESIGN BASELINE ONLY — NOT AUTHORIZED FOR IMPLEMENTATION
**日期：** 2026-11-06
**上游审计：** [Phase A 审计报告](A审计报告.md)、[Phase A2 补充审计报告](A2审计报告.md)

> 本文是契约与接口设计，不是已实现功能或验收报告。未运行测试、未操作 8091、未修改代码或数据库。任何方案都须经审批后另行授权实施。

**评审修订依据：** Phase B v0.2 评审意见 (/Users/lijianqiang/.codex/attachments/1df23ff3-5729-44b4-8bdb-71d3987868aa/Pasted text.txt)，以及 2026-11-06 提出的三项最小收口意见。本版只澄清完成声明边界、dormant 规则恢复语义和确认绑定的最终 Effect，不扩展架构，也不授权实施。

## 1. 设计结论

保留“原始 Office 文件 + 当前授权数据 + 当前完整 Proposal → 编译操作 → Preview → 确认 → Finalize”的重编译架构、线性操作序列、Mapping Validator、Office Core、Session/Proposal revisions、确认门、保存后回读、附件交付机制及原生 odoo-llm 工具循环。

建议围绕四类已审计缺口补齐最小契约，并将意图覆盖、值类型和 Patch 语义进一步收口：

1. 以有限、类型化的值表达树统一字面量、字段引用和组合转换，替代把所有动态值压成字段名列表的做法。
2. 在工具边界表达 Agent 解析出的可核验目标与预期效果，并让服务端把预期与实际编译操作及文件回读结果比较。
3. 明确 Proposal revision、编译基线、待确认范围、Preview 收据和交付状态之间的归属；继续从原始模板重编译，不把上一份输出文件隐式改成新基线。
4. 以兼容适配层将已有 Office 状态映射为统一的对外结果语义；保留内部错误码用于诊断，避免由模型自由发挥完成状态。
5. 分开表达 Engine 的 execution_verified、Agent 提交的 coverage_declared 和面向用户的 task_completed；覆盖清单不能自证完整，也不能证明 Agent 没有遗漏用户原话。
6. 将 Proposal 的 set/remove/clear/restore 与文档操作区分，并明确目标随结构、筛选变化后的行为。

不引入 Operation DAG、事件总线、任意 Python/eval、通用工作流引擎或事件溯源。只在实施前验证现有字段是否足以承载建议契约；若足够，应优先在服务端适配而不是增加持久化状态。

### 1.1 评审意见响应索引

| 评审项 | v0.3 修订位置 |
|---|---|
| P0-01 Expected Effects 不能自证自然语言 | §4.2 分离 Execution Verification / Intent Coverage，并规定未覆盖或不确定时不得报告整体完成 |
| P0-02 表达式类型、空值、精度和嵌套 | §3.1–3.5 增加类型矩阵、Decimal/除法参数、null 与 clear 区分及嵌套边界 |
| P0-03 Proposal 修改/删除/清空/恢复 | §5.2 定义 set/remove/clear/restore；§5.3–5.5 定义顺序、目标和确认 |
| P1-04 Office 序列化回读语义 | §3.5 分为 Typed Evaluation 与 Document Readback |
| P1-05 completed 不等于正式文件交付 | §6.1–6.2 将 outcome、artifact_stage、delivery_state 分开 |
| P1-06 实施范围过大 | §11 分拆为 CC-01 至 CC-06，逐轮授权与验收 |
| 边界一：歧义需澄清，确认不可代替定位 | §5.5 |
| 边界二：通用目标不依赖 Odoo record ID | §5.5 |
| v0.2 P0：覆盖清单不能证明 Agent 未遗漏要求 | §4.2–4.3 定义 execution_verified、coverage_declared、task_completed 三层，并明确自然语言语义证明边界 |
| v0.2 P0：dormant 规则重新进入范围时的行为未定 | §5.2 明确不自动重新激活；仅用户明确重新启用或恢复整份已确认 Proposal 后才可能生效；第一版不支持局部恢复 |
| v0.2 P1：确认须绑定最终表达式效果 | §5.4–5.5 将表达式、求值数据基线、解析目标、具体 Effect、旧值和覆盖范围列为确认不变量 |

## 2. 审计依据和证据限制

- Phase A §1：8091 进程路径与工作区路径一致，但进程内已加载 Python 模块的源码指纹无法确认；结论为 UNVERIFIED，且没有证据支持笼统的 Runtime Code != Workspace Code。
- Phase A §3：Canonical Operations 是有序线性序列；Mapping 编译顺序为 repeat_rows、映射写入、显式 cell edits。当前坐标在执行时针对当前中间文件；repeat_rows 后续目标使用扩展后文件坐标。Phase A 未将缺少逻辑 ID 映射认定为缺陷。
- Phase A §4–7：确认门绑定用户/Thread、revision、预览/模板/上下文/文件指纹、观察值和操作范围；公开工具状态已部分区分执行、附件和交付，但命名不统一；原生 tool message 的 completed 只代表函数调用返回。缺少 Office 工具成功后下一次 Provider 请求超时的专项测试。
- Phase A2 §1：Thread 12063 的历史确认重试返回 force_override_flag_required，与当前工作区确认门不符；具体进程内模块路径/哈希及历史 pending payload 均 UNVERIFIED。该差异不能直接证明当前确认门实现错误。
- Phase A2 §2–4：Proposal patch 合并、重新从 source attachment 编译和当前数据读取已有实现证据；Thread 12063 同一失败 Session 的恢复未验证。测试源码不是本轮实际运行结果。
- Phase A2 §3：现有表达能力包含 typed literal、字段映射、有限 concat_fields 和 date_offset。A2 指出直接布尔字段 False 会被 _first_nonempty_mapping_value 视作空值，是源码证据支持的缺陷，但真实运行未复现。Thread 13139 中 concat 操作成功返回并生成附件，但实际文件没有用户要求的“remark”字面前缀，构成真实的 Intent/Result 反馈偏差。
- Phase A2 §5–6：工具执行结果持久化与后续 Provider 响应是不同阶段；超时与某次成功 Office 工具调用的因果关系、附件浏览器可见性及重试幂等性未验证。

以上引用仅支撑设计动因，不等于本阶段重新验证了代码或运行环境。

## 3. B1 — Expression Contract

### 3.1 最小值表达结构

建议在现有 Mapping/Transform 契约内增加带版本的有限表达树。下列为设计草案，不是已冻结 JSON Schema：

    {
      "expression_version": "1",
      "value": {
        "kind": "concat",
        "parts": [
          {"kind": "field", "path": "comment"},
          {"kind": "literal", "value_type": "string", "value": " — "},
          {"kind": "field", "path": "name"}
        ],
        "null_policy": "skip_segment",
        "separator": ""
      }
    }

第一版节点范围建议限定为下表。除有限嵌套外，不支持任意函数、隐式类型转换或任意代码：

| 节点 | 语义 | 约束 |
|---|---|---|
| literal | 明确类型的常量，包括字符串、数值、布尔、日期、日期时间及显式 null | 文本永远是文本，不按字段名推断 |
| field | 从当前记录/数据行上下文读取一个已授权字段路径 | 必须由现有字段授权及 ORM 读取链验证 |
| concat | 按顺序组合子表达式 | 第一版只接受字符串和显式 null；数字、布尔、日期不得自动转字符串 |
| coalesce | 从候选值中按明示空值策略取值 | 候选非空值须为兼容类型；null 可作为中性候选；不得把 False/0 当空 |
| arithmetic | 有限的 add/subtract/multiply/divide | 整数与 Decimal 统一为十进制运算；小数位和舍入由显式参数指定，不读取 Odoo 币种配置 |
| date_offset | 日期或日期时间加减整天数 | 复用现有受限转换语义，不支持代码执行 |

草案建议表达树最大深度 8、单表达式节点数 64、concat 最多 32 段；这些是资源边界建议，须通过现有文件/Provider 限制与中性边界测试校准后审批，不能作为未经验证的现行限制。禁止未知节点、循环引用、任意函数、Python 表达式及 eval。

### 3.2 类型兼容与求值规则

| 操作 | 输入兼容规则 | 输出/失败规则 |
|---|---|---|
| literal | value_type 与值必须吻合；显式 null 不得伪装成字符串 | 保留声明类型 |
| field | 运行时值类型由授权字段元数据及实际 ORM 值确定 | 字段不存在、不可读或类型不符时给出带路径的错误 |
| concat | 字符串 + 字符串；null 按明确的 null_policy 处理。数字、布尔、日期/日期时间均拒绝隐式格式化 | 返回字符串；非兼容类型返回 type_error。若以后需要格式化，须另行定义 locale/格式契约 |
| coalesce | 所有非 null 候选必须为同一逻辑类型；仅对字符串可选择将空字符串视为空；False、0、0.0 始终是有效值 | 返回首个满足所选空值策略的候选；没有候选时返回 typed null |
| add/subtract/multiply | 仅接受有限整数/Decimal；输入浮点按 Decimal(str(value)) 规范化，非有限值拒绝 | 采用十进制运算；不自动应用货币或数量精度 |
| divide | 同上，除数为零返回 division_by_zero | 必须显式提供结果 scale 和 rounding 模式；不隐式读取 Odoo 币种精度 |
| date_offset | 日期加/减整数天；datetime 只接受其既有明确时区语义 | 类型、时区不兼容或无效天数时返回定位错误 |

金额或数量的业务精度必须由调用方在表达式参数中显式传入；Office Engine 只执行指定的十进制规则，不推断币种、税额或数量精度。

补充运算规则：Arithmetic 的 null 操作数按 null 传播，不替换为零；传播到目标时仍须由 null_result 显式选择 error、skip 或 clear。Boolean 即使在 Python 中可转成整数，也不是 arithmetic 的数值输入。加、减、乘以 Decimal 做精确十进制运算；未声明 scale 时不做业务量化；声明 scale 时按声明 rounding 量化。除法必须声明 scale 与舍入模式。Date offset 第一版只复用既有已定义行为；若实际输入 datetime 的时区/本地日期语义未被源契约明确，返回类型/时区错误，不自行推断。

Concat 的 null_policy 枚举在第一版限定为：skip_segment（忽略 null 段，分隔符只连接保留段）、empty_segment（该段作为空字符串保留其分隔位置）、propagate（整个表达式返回 typed null）。分隔符自身必须是 string literal。Coalesce 的空值策略为 null_only 或 null_or_empty_string；后者仅对 string 类型有效。任何候选的类型不兼容都在编译/求值前报 type_error，不通过隐式转换“抢救”。

### 3.3 类型与空值

- 值使用显式类型，不以 truthiness 判断是否存在。
- null、false、空字符串、0、0.0、日期和日期时间保持不同值。Boolean False 是有效布尔值；不得被回退逻辑丢弃。
- coalesce 要求显式选择 null_only 或 null_or_empty_string。数值零及 False 永不因 coalesce 被跳过。
- 表达式求值为 null 不等于清空单元格。Mapping 必须显式声明 null_result=error、skip 或 clear；省略时按 error 处理。clear 编译成明确的文档 clear 操作；skip 不写该目标；空字符串仍是字符串赋值，其文件存储规范化另见回读规则。
- 数值计算使用确定的 Decimal 运算及显式舍入参数；日期解析失败、类型不兼容、除零或缺失必需字段必须返回可定位的表达式错误，禁止静默写空。
- 错误位置应包括 proposal/revision、mapping rule、expression 节点路径、记录目标（如有）及目标单元格。

允许有限嵌套，以支持例如 concat 中包含 coalesce；建议深度 8、节点数 64、concat 段数 32 仍只是待测试的资源上限，不能在设计批准时直接当作已冻结限制。第一版不提供隐式 number/date/boolean-to-string 节点。

### 3.4 现有契约兼容

- literal_value 迁移为 kind=literal 的兼容输入；保留旧字段读取，规范化后内部只生成一种表达表示。
- 直接字段映射迁移为 kind=field。
- concat_fields 与 separator 可适配为 concat(field...)；旧 separator 只表示字段间分隔符，不能被解释为前缀或后缀。新增任意常量片段时必须使用 literal 节点，避免重演 A2 Thread 13139 的“工具成功但少了字面前缀”偏差。
- date_offset 适配为受限 date_offset 节点；不得扩大到任意 Python 或日期表达式。
- A2 报告中的 fallback_fields 适配为明确的 coalesce，而不是在字段缺失时默认以 False/0 代表空值。
- 兼容期由解析器读取旧、新输入，编译器只输出新规范化表示；移除旧输入须待已有 Proposal/历史版本迁移策略确定。

### 3.5 求值基线、逐目标与文件公式

每个 repeat-row 记录目标独立提供 row context，表达式对该行求值；不得先算出脱离目标的共享值列表。数据版本/读取时刻必须记录在编译结果指纹中，以便确认和回读基于同一输入。

Mapping 表达式产出写入单元格的值；XLSX 公式是文档内容/操作的一部分。表达式求值不能冒充 Excel 公式重算，读取到公式字符串也不能声称已验证公式结果。保留公式时应回读公式文本、引用范围和非目标公式；如业务要求公式计算值，必须明确需要真实计算引擎或独立计算断言。

验证分为两个确定性层次：

1. **Typed Evaluation Verification**：在写入前验证表达式树、输入/输出类型、null 策略和逐记录求值结果。此层证明结构化表达式被正确求值，不证明它正确理解了用户自然语言。
2. **Document Readback Verification**：保存后由格式 Adapter 重新打开文件，按 Office 存储语义验证值、类型、公式和结构。不得简单用字符串比较全部值，也不得要求底层 Python 类型在序列化前后完全相同。

回读规则应按目标格式规定：日期按工作簿日期系统解析后比较日期/日期时间类型和值；带时区 datetime 在转换策略未明确时拒绝。整数和 Decimal/Excel 数值按显式目标类型及 scale 比较，不把所有数值转成字符串；浮点读取以十进制文本规范化，并使用操作声明的 scale/rounding，不使用全局宽松 epsilon。公式核验公式文本与引用结构，不声称计算了公式结果。清空目标检查文件中的实际空白语义；空字符串经 XLSX 保存后可能被规范化为空白，需按 Adapter 的明示规范判断，但绝不等同于 0 或 False。样式和非目标区域另行验证。

Typed Evaluation 与 Document Readback 两层都通过，才可报告结构化 expected effect 已实现。目标无法稳定关联时，应澄清或阻断，不允许仅以“非空”作为成功证明。

## 4. B2 — Intent / Operation / Result 一致性

### 4.1 三层最小契约

| 层 | 责任 | 建议最小内容 |
|---|---|---|
| Intent | Agent 对用户自然语言的结构化解释 | 目标文档/范围、操作语义、目标选择方式、预期结果及用户明确限制；由 Agent 生成，仍可能有歧义 |
| Operation | 可执行的规范操作 | Canonical Operation List、Mapping/Expression、显式顺序、目标、参数、操作 ID |
| Result | 服务端执行事实 | 规范操作摘要、已验证目标值/公式/结构、文件指纹、Preview/Finalize artifact 状态、交付状态、错误或确认范围 |

expected_effects 作为 Intent 与 Operation 间的可核验约束，建议使用目标选择器、预期操作、类型化期望值/表达式及验证方法。服务端须确认每条可执行预期都映射到一个或多个实际 Operation，且执行后的文件回读满足预期。未覆盖的用户要求不能被 Agent 默默替换成“当前可执行的其他内容”。

expected_effects 不是 ACL、业务授权或确认凭据，也不能使不支持操作自动变得可执行。即使 Operation 和 expected_effects 一致，二者也可能同源于 Agent 的错误解释；文件回读只能证明执行结果符合结构化预期，不能证明结构化预期符合用户原话。

### 4.2 三层结果：execution_verified、coverage_declared、task_completed

三层结果必须分别表达，不能互相冒充：

| 结果 | 产生者 | 最小含义 | 不构成的证明 |
|---|---|---|---|
| execution_verified | Engine/Validator | 提交的规范操作已执行，文件保存后回读符合这些操作及其可检查的 expected effects | 不证明 Agent 正确理解或完整提取了用户自然语言 |
| coverage_declared | Agent | Agent 对本轮识别出的要求逐项声明 covered、not_covered 或 uncertain，并关联操作/效果及来源消息 | 不证明该清单包含用户原话中的全部要求，也不是独立语义审查 |
| task_completed | Agent 面向用户的结果结论 | Agent 根据 execution_verified 与 coverage_declared 形成的用户反馈；不得描述为机器独立证明了自然语言语义 | 不得由工具调用成功、单有 execution_verified 或模型自述成功推出 |

Intent Coverage 项建议包含 request item ID、来源消息 ID/原句片段引用、规范化要求、关联 operation/effect ID、coverage 状态及解释。原句引用用于追踪审阅，不等于语义验证器；服务端可以验证清单字段及引用结构，不能验证遗漏的自然语言要求。

若已列要求中存在 not_covered 或 uncertain，或已列要求无法关联到操作/预期结果，Agent 不得把整项任务报告为 task_completed；必须明确说明未结构化、未覆盖或不确定的要求，必要时请求澄清。用户要求中有任何部分无法安全、明确地转成结构化操作时，也必须显式反馈，不得静默忽略。即使全部已声明项目均为 covered，最多只能说明“已声明的要求均已执行并验证”；Agent 不得宣称获得了独立的自然语言语义完整性证明。无需增加第二个 LLM 审核器或完整自然语言验证引擎。

### 4.3 执行验证与用户完成声明门槛

工具的 success 或原生 llm.tool 消息 completed 不能单独构成 task_completed。服务端只有在以下事实均成立时才能给出 execution_verified=true：

1. Operation 列表已通过全量静态校验；
2. 权限、安全、目标和执行前置条件通过；
3. 操作序列实际执行完成；
4. 保存后文件安全与结构验证通过；
5. 所有已结构化的 expected effects 都由独立回读验证；
6. 候选文件存在且可重新读取，验证对象与文件指纹一致；附件创建、消息关联和 delivery 状态独立表达，不纳入 execution_verified。

Agent 只能在 execution_verified=true 且 coverage_declared 中没有未覆盖或不确定项时形成 task_completed 反馈，并须明确其依据是 Agent 自身列出的要求而非独立自然语言证明。某项意图无法结构化或无法验证时，Agent 应报告该项未完成、说明限制或请求澄清。自然语言不能凌驾服务端执行与回读事实。

## 5. B3 — 多轮状态连续性

### 5.1 基线与重编译

继续以原始上传附件（及其字节指纹）作为模板基线。每轮使用当前有效完整 Proposal、当前授权数据和原始模板重新编译；上一 Preview 是该 Proposal 的产物及交付物，不默认成为下轮文件编辑基线。Phase A2 §2 已有源附件重编译、字段/记录重新读取、patch 合并及 savepoint 保护的源码证据。

建议把下列身份明确区分并记录/返回（优先复用现有 Session 字段）：

- session_revision：一次 Session 状态变更序号；
- proposal_revision：完整逻辑 Proposal 的版本；
- source_fingerprint：原始 Office 文件身份；
- data_context_fingerprint：用于本轮编译的授权数据输入指纹；
- compiled_operation_fingerprint：规范化完整操作序列及表达式的指纹；
- preview_revision / artifact 指纹：一次成功产出的预览；
- confirmation_scope_fingerprint：上述必要身份 + 具体操作和实际 Effect 集合。

不要求所有字段均新增持久化列；实现阶段先核实现有字段/确认 payload 能否准确承载。若某一指纹不可重建或持久化，确认后无法判断是否仍是同一内容时，才提出最小新增字段。

### 5.2 Proposal Patch 操作语义

Proposal Patch 是对“当前完整 Proposal”的修改协议，不是 Canonical Document Operations。至少区分以下动作：

| Patch 动作 | Proposal 语义 | 文件效果 |
|---|---|---|
| set | 按 rule ID 或稳定目标新增/替换当前有效规则；重复 set 以明确的 rule ID 作为替换，不另增重复规则 | 编译后的完整 Proposal 决定文件值 |
| remove | 从当前 Proposal 移除指定规则 | 不直接写空；从原始模板重编译后，该规则不再产生写入，目标回到模板基线或其他仍有效规则的效果 |
| clear | 保留一条明确的清空意图/规则 | 编译成 Document Operations 的 clear，实际清空目标内容；与删除 Proposal 规则不同 |
| restore | 选择整份曾确认的历史 Proposal snapshot 作为新当前 Proposal 内容，并生成新的 proposal_revision | 第一版仅支持整份已确认 Proposal Restore；重新编译、验证和确认；不恢复或复用历史 Preview/Finalize 文件及确认令牌 |

历史动作与文档效果必须区分。示例：V1 的有效规则写 A，V2 set 为 B；整份 restore 已确认的 V1 后有效值应回到 A，而不是清空。若用户要清空，必须提交 clear。第一版不支持局部 Proposal Restore；用户只要求恢复部分规则时，需澄清并由用户明确给出新的 Patch，不得由系统猜测局部合并范围。

规则目标不在当前有效数据/筛选范围时，不得静默把操作改到另一条记录。规则可保留在 Proposal 历史中并标记为 dormant/out_of_scope，但在不在范围内时不执行。即使目标之后重新进入范围，也不得自动重新激活此前未应用的修改。只有用户明确重新启用该规则（通过引用该 dormant 规则的新 Patch）或恢复一份整份已确认的 Proposal 后，规则才可重新进入编译；随后仍须重新编译、验证并按当前 Effect 请求确认，历史确认不复用。恢复未确认的历史 Proposal 不构成重新激活授权。若本轮用户要求必须作用于当前范围，或目标身份无法重定位，应 clarification_required。物理坐标目标始终指当前编译状态的该坐标，不承诺跨插行/排序跟随同一逻辑元素。

### 5.3 顺序、目标与重复提交

- 同一目标的操作顺序由 Canonical Operation List 的线性顺序决定。Mapping 写入后显式 cell edit 可作为后序覆盖；覆盖风险仍走 Confirmation Gate。无明确顺序且结果不确定时属于真实冲突。
- Office Engine 接受通用当前文件坐标及可由调用方/Adapter 稳定解析的逻辑目标。M2 的 record_target 是业务映射场景的一种逻辑身份，不要求所有 Office 操作携带 Odoo record ID。
- 目标使用逻辑身份时，需在本轮结构变化、排序或筛选后的最终范围中重新解析；只有当前目标唯一且仍在允许范围内才执行。若逻辑目标缺失/多重/超范围，保留已有有效 Preview 并澄清，不能退回旧行号或另一个记录。坐标引用则按其明确的物理位置语义执行。
- 排序、筛选和范围变化时，对依赖记录上下文的表达式按当前数据集和顺序重算；纯字面量规则按当前逻辑目标/坐标语义重新应用。无法确定原修改是否仍指向相同逻辑对象时，标记未应用并询问用户。
- 对同一已接受 Patch 的幂等重发，应由 revision/规范化 request fingerprint 识别为 unchanged 或返回既有结果；不得重复插入行。具体幂等键与现有 request/session 数据的关系须在 Phase C 前置审计确认，不新增独立事件账本。

### 5.4 Preview、失败、确认、Finalize 和恢复

| 情况 | 基线/状态建议 |
|---|---|
| Proposal 更新 | 新 proposal_revision；旧 Preview 仍可保留作历史，但不再代表当前修订 |
| Preview 编译/保存失败 | 不推进 latest valid preview；保留此前有效 artifact 和 Proposal；记录失败结果，不把失败候选绑定为可确认 Preview |
| 需要确认 | 不写候选文件、不推进成功 Preview；pending confirmation 绑定 revision、source/data/structure fingerprints、规范化表达式、表达式求值数据基线、解析后的目标集合、实际写入值/结构 Effect、观察到的原值和精确覆盖范围 |
| 用户确认 | 重新读权限、源文件/上下文和当前目标，重编译并重新计算 Effect；表达式、求值数据基线、解析目标、实际 Effect、观察原值及覆盖范围均与确认绑定一致才执行；任一项变化、超出范围或内容变化则旧确认失效并重新评估风险 |
| Preview 成功 | 只有回读验证通过后才推进当前有效 Preview；附件创建/关联状态另行表达 |
| Finalize | 引用明确确认的 proposal_revision 和 preview_revision；Finalize 前重验数据/模板指纹。发布失败时保留已验证生成物和 pending delivery 状态 |
| Finalize 后继续编辑 | 仍以原始模板 + 新的当前完整 Proposal 重编译；Finalize artifact 是历史正式产物，不自动替代模板基线 |
| 历史 Proposal 恢复 | 恢复产生新当前 revision 或显式引用历史版本；确认和 Preview 不复用，必须重新校验数据、目标、表达式和文件效果 |

具体 session 状态枚举沿用现有模型；上述为状态语义，不要求引入新状态机。Phase A2 已有 savepoint/旧版本保护的当前源码证据，但 Thread 12063 的同一失败 Session 是否成功恢复仍未验证。

### 5.5 目标身份与确认边界不变量

1. **目标不确定只能澄清，不能用确认代替定位。** 如果自然语言对应多个目标、逻辑目标解析为零条/多条记录，或排序/筛选后无法确认目标身份，返回 clarification_required。不得把含糊目标包装成“是否覆盖”的 confirmation_required，因为用户确认一个不明确范围不能产生有效授权。
2. **确认仅针对确定目标上的可确认风险。** 目标、执行顺序、操作内容及精确 Effect 均确定后，才可请求业务风险确认。确认只能解除该范围内的业务风险；ACL、Record Rules、路径安全、资源限制和文件完整性始终不可绕过。
3. **通用文档目标不依赖 Odoo 身份。** Canonical Operation 的目标可以是当前文件坐标，也可以是调用方/Adapter 能可靠解析的逻辑目标键。M2 的 record_target 是映射场景提供的逻辑目标形式之一，不要求所有 Document Operation 都关联 Odoo record ID。
4. **结构变化后重新解析。** 逻辑目标须在排序、插行、过滤后的执行状态中重新唯一解析；坐标目标继续表示明确的物理坐标。解析身份变化或范围扩张时，旧确认失效；不得静默转移到相邻行/其他记录。
5. **确认绑定最终 Effect，而不只是操作描述。** 确认必须绑定规范化表达式、表达式求值所用的数据基线、解析后的目标集合、实际写入值或结构效果、被覆盖目标的原值及精确覆盖范围。表达式不变但数据变化导致实际 Effect 改变时，旧确认同样失效；重新求值和风险分析后，必要时再次请求确认。确认答复或 force_override 本身不得绕过该绑定检查。

## 6. B4 — User-facing Outcome Contract

### 6.1 对外结果映射

优先从现有嵌套结果适配，不把原生工具调用消息状态当 Office 状态。建议公开稳定的 outcome 语义，并映射到既有字段；是否需要新增字段待核对当前 JSON Schema 与消费端。

| outcome | 服务端判定 | 必要结果内容 | 不代表什么 |
|---|---|---|---|
| completed | 本次提交的结构化操作已执行，文件保存后验证成功，且相应 expected effects 满足 | outcome、artifact_stage、delivery_state、operation_status、revision、附件/消息元数据 | 不证明 Agent 已完整提取用户原话，也不单独代表 task_completed；该状态本身不能说明是预览还是正式文件 |
| confirmation_required | 目标、顺序、精确 Effect 已确定，仅存在可由用户确认的业务风险 | 风险类型、旧/新值、范围、待确认指纹、确认问题；operation_executed=false | 不表示已写入或成功 |
| clarification_required | 目标或必要输入仍不明确，至少有多个合理解释 | 缺失信息、候选目标/问题 | 不应制造确认令牌 |
| blocked | ACL、Record Rules、文件/路径安全、资源边界或当前不支持的技术约束不允许执行 | 安全的诊断类别及可行动说明 | 业务确认不能绕过 |
| failed | 执行异常，或执行/验证事实不能可靠确认 | 稳定用户可读消息、内部 error_code、失败阶段、是否有候选 artifact | 不能报告完成 |

结果使用三个正交维度，而不是让单个 completed 词承载全部含义。工具 outcome=completed 仅表示提交的结构化操作达到其验证条件；Agent 的 task_completed 还须结合 coverage_declared，且不构成独立自然语言语义证明：

- outcome：本次用户请求/操作的结果，例如 completed、confirmation_required、clarification_required、blocked、failed。
- artifact_stage：文件当前阶段，建议映射为 none、preview、finalized。
- delivery_state：该阶段文件的交付状态，沿用 posted、pending、failed 等现有事实（具体枚举以当前接口核验为准）。

例：outcome=completed + artifact_stage=preview + delivery_state=posted 的用户文案应为“预览文件已生成并附在对话中，请查看”，不能说正式文件已完成。只有 outcome=completed + artifact_stage=finalized + delivery_state=posted 才可说“正式文件已生成并附在对话中”。若 delivery_state=pending，应说明文件已生成但聊天交付尚未确认；不能说用户已经收到。优先从现有 artifact_state、工具结果和附件字段推导 artifact_stage，不要求新增数据库字段。

### 6.2 兼容策略与超时恢复

Phase A §5/A2 §5 已记录 status、operation_status、artifact_state、delivery_state、附件元数据及原生 Tool 外层 completed；目前存在 preview_ready/success/unchanged、needs_confirmation/requires_reconfirmation、needs_input/incomplete、blocked、error/failed 多套词汇。

实施时增加一个适配函数，把既有内部返回投影为 outcome + artifact_stage + delivery_state；保留原有字段一段兼容期，消费端逐步改读新映射。若已有字段能无歧义表达，不增加冗余字段。错误码用于日志/诊断，业务消息由服务端提供安全、行动导向的摘要，Agent 可润色但不得暴露内部堆栈或改变结果类别。

Provider 超时发生在工具消息持久化之后时，Operation/Preview 的已提交事实不应回滚或改称失败。下次模型请求应从 Thread 中可见的工具结果及 Session 当前 revision 恢复；重试同一请求应识别既有 operation fingerprint 和 artifact，不重复插入/写入。此路径目前缺少专项真实测试，不能视为已实现或已验证。

## 7. 端到端契约流程

1. Thread 原样接收用户消息；Agent 结合上下文形成完整 Proposal patch、coverage_declared 和可核验 expected effects，并标记无法结构化或不确定的要求。缺信息或目标不确定时先澄清。
2. Prepare Context 返回当前 Session/Proposal revision、源文件身份、授权数据上下文、目标清单及能力描述。不能由模型自行授予 Odoo 权限。
3. 服务端规范化值表达和操作列表；检查 schema、字段路径、目标、操作顺序、资源及权限。
4. 在未持久化候选文件的执行前状态上模拟/计算实际 Effect。纯技术阻断返回 blocked；目标/解释不确定返回 clarification_required；仅当目标、顺序和 Effect 范围明确且存在可确认业务风险时返回 confirmation_required。
5. 若需确认，保存待确认范围及表达式、数据求值基线、解析目标、具体 Effect、原值和覆盖范围 fingerprints，不执行风险写入。用户回答后重新读取权限、数据和文件并重新求值；所有绑定保持一致才执行，否则旧确认失效并重新分析。
6. 通过后从原始输入重编译完整 Proposal，按有序 Canonical Operations 执行。
7. 独立重开候选文件，检查安全、结构、非目标区域及 expected_effects。失败时不升级最新有效 Preview，不发布合格文件。
8. 创建并关联 Preview artifact；分别返回 artifact 和 delivery 事实。原生工具结果进入 Thread 历史，Provider 可继续回复或超时。
9. Finalize 只接受明确 preview/proposal revision，重新验证关键输入，生成正式 artifact、回读并分别记录发布结果。
10. Engine 返回 execution_verified；Agent 另行提交 coverage_declared，并仅在执行已验证且清单没有未覆盖/不确定项时形成 task_completed 用户反馈。Agent 必须显式报告无法结构化的用户要求，并说明完成声明基于 Agent 自身列出的要求，不是独立自然语言语义证明。再根据 artifact_stage 和 delivery_state 使用“预览生成”“正式文件生成”“交付待完成”等准确文案。自然语言不能凌驾服务端结果。

## 8. 接口兼容与预计影响范围

设计阶段不改接口。Phase C 若获批，预计首先核实并可能涉及：

| 范围 | 关注点 |
|---|---|
| office_mapping_verify/contracts.py、parser.py、transforms.py、validator.py | 值表达规范化、类型/空值语义、expected-effect 的确定性校验；保留旧 Proposal 读取兼容 |
| office_engine_m2/services/render_bridge.py | 按记录 context 求值、完整 Proposal 重编译、编译/Preview 指纹和回读结果 |
| office_engine_m2/models/office_mapping_session.py | 复用 revision、历史快照、pending confirmation、preview binding；仅在无法承载时提出最小字段扩展 |
| office_engine_m2/models/office_mapping_tools.py | Prepare/Save/Finalize/Restore 的契约适配及 outcome 构造 |
| office_engine_m2/models/llm_thread.py 与原生 llm_assistant 消费链 | 工具结果恢复、Agent 最终回复与已持久化结果一致 |
| 现有 operation/validator/core 接口与相关测试 | 不增加绕行生产入口；确认操作与回读都经过统一链 |

具体文件/方法以 Phase C 实施前重新核对为准。不得因本设计修改 Odoo 官方 addon、Adapter 业务边界或生产执行入口。

## 9. 测试矩阵（设计，不是执行结果）

### A. 通用表达/操作契约测试

| 用例 | 核验重点 |
|---|---|
| typed literal / field reference / concat literal+field | 常量不被解析成字段；任意常量片段不丢失；数字/布尔/日期不隐式转文本 |
| 多记录逐目标求值 | 各行使用自身上下文，不串行、不共享错值 |
| null / False / empty / 0 / 0.0 / 日期 | 类型、coalesce、传播、skip、clear 语义逐项保留 |
| arithmetic/date_offset/coalesce | Decimal 混合规则、必须显式的除法精度、类型错误、缺失字段、除零和 null policy |
| Excel formula 与 Mapping expression | 模板公式文本/引用范围验证，不伪称重新计算 |
| sort/insert/record target 与坐标目标 | 操作顺序后目标按声明语义解析；结构变化后旧坐标不会假装跟随逻辑记录 |
| 有序同目标写入与无序冲突 | 后序显式覆盖按序执行；无顺序且结果不确定时拒绝 |
| 保存回读 expected_effects | Typed Evaluation 与格式感知回读分别断言；每个期望值按最终目标比对 |
| Intent Coverage 三层结果 | 验证 execution_verified 只证明结构化执行；coverage_declared 明确列项及未覆盖/不确定项；task_completed 不宣称独立语义证明；无法结构化的要求必须显式反馈 |

### B. Agent 结果契约测试

覆盖无法表达时的澄清/阻断并显式报告未结构化要求、用户目标有歧义时必须 clarification 而非 confirmation、Operation 与 expected-effect 不一致、工具返回成功但回读不满足、execution_verified 与 coverage_declared 分离、已识别要求未覆盖时不得形成 task_completed、Agent 不宣称清单证明语义完整、confirmation/clarification/blocked/failed、Preview 成功后 Provider 超时、附件已生成但发布 pending、同请求重试不重复执行、Agent 文本不能推翻 nested outcome。

### C. 多轮 Proposal 重编译和确认测试

覆盖多个增量 patch 保留未改规则、set/remove/clear/整份 restore 的差异、V1→V2→restore V1 恢复规则而非清空文件、dormant 目标出范围时不执行且重新进入范围后不自动激活、仅显式重新启用或整份恢复可重新纳入编译、Preview 失败保留上一有效版本、待确认前后不写、文件/数据/结构/规范化表达式/解析目标/实际 Effect/原值变化令旧确认失效、历史 Proposal 恢复后重新校验、Finalize 后继续修改仍从原始模板重编译。

### D. 真实 Odoo 集成验证

在当前用户 ORM 权限下使用真实数据和通用模板走 Thread → Provider → tools → Preview → 回读 → Finalize → Attachment/Thread。分别验证业务权限、相关数据重载、Session revision、附件消息关联、Provider 超时恢复和浏览器可见性。不得以纯 Python、mock tool、模型自述或数据库中单有附件记录代替浏览器交付证据。

以上均为拟设计的测试；未执行，不构成通过声明。

## 10. Phase C 前置验证与环境区分

| 验证项 | 类型 | 最小证据/判定 |
|---|---|---|
| 8091 模块身份 | 环境/部署 | 只读获取运行进程解释器、实际 import module __file__、源码/字节码指纹，并与工作区匹配；A2 当前为 UNVERIFIED。若无法取证，授权后重启/部署，再重复检查 |
| Thread 12063 确认错误 | 历史数据与运行行为 | 若保留原始工具参数、pending payload、Session/proposal/document fingerprints 和服务日志，则可比对当前逻辑；A2 缺历史 pending payload。不可用另一个 Session 的成功代替原 Session 恢复 |
| 当前确认门行为 | 当前代码测试 | 隔离测试复现确认前无写、精确确认后写、Scope/版本变化后失效；再在授权测试环境使用同一 Session 做真实流程 |
| Provider 成功后超时 | 代码/运行 | 在可控测试环境让 Office tool 先持久化，再让下一 Provider 请求超时；检查 Thread、Session、artifact 与安全重试；A2 现有日志不足以关联因果 |
| 浏览器附件可见 | 集成/UI | 真实 Thread 发布后确认卡片可见且下载字节与 artifact fingerprint 相同；DB attachment relation 不是 UI 验收 |

模块身份和历史缺失证据属于环境/取证条件，不能仅靠改代码解决。确认门行为、超时幂等和意图/结果一致性需要当前代码测试。开始 Phase C 前应先解决运行身份不明或明确把其作为阻塞；不允许把历史错误码直接当作当前实现根因。

## 11. Phase C Implementation Decomposition（建议分轮授权）

下表是后续实施拆分建议，不构成实施授权。每一轮需单独签发范围并按其完成条件验收；未通过时不得以后一轮覆盖失败证据。

| 轮次 | 范围 | 依赖 | 完成条件 |
|---|---|---|---|
| CC-01 | 运行身份核查、当前基线和现有回归测试基线 | 无；Phase C 入口门槛 | 可证明测试进程实际导入的模块与目标工作区版本；记录当前 Python/Odoo 测试结果和未解释差异。运行身份仍不明则暂停依赖真实服务的轮次 |
| CC-02 | 类型与 Expression Contract | CC-01 | 中性测试覆盖 literal、field、concat、coalesce、四则运算、date_offset、有限嵌套及空值/布尔/零；旧字段兼容；禁止任意代码执行 |
| CC-03 | Proposal Patch 与多轮状态 | CC-01、CC-02 | set/remove/clear/restore 各自语义、目标超范围处理、重编译、确认失效及幂等重发有独立测试；历史 Proposal 兼容边界明确 |
| CC-04 | Intent Coverage、Expected Effects 与文件回读 | CC-02、CC-03 | Execution Verification 与 Intent Coverage 独立；未覆盖/不确定项不能报告整体完成；两级回读断言覆盖实际格式语义及非目标保护 |
| CC-05 | Outcome、附件状态与 Provider 超时恢复 | CC-01、CC-04 | outcome/artifact_stage/delivery_state 对外一致；注入工具成功后 Provider 超时，恢复不重放非幂等操作；用户文案与持久化结果一致 |
| CC-06 | Odoo + Browser 集成验收 | CC-01 至 CC-05 | 当前用户 ORM 权限、真实 Provider/Thread、Preview/Finalize、附件关联和浏览器下载形成可核验证据；所有失败项如实保留 |

CC-01 的源码身份检查属于运行环境证据，不得用“服务刚重启”本身替代模块路径/指纹核对。CC-02 至 CC-05 应先通过相应自动化层级，再进入 CC-06。真实业务场景只作为集成数据，不允许为其增加核心引擎特例。

## 12. 风险、兼容、回退与明确不实施事项

### 风险和兼容

- 新表达树改变 Proposal/Tool JSON；需要旧版本反序列化兼容策略，尤其是已持久化历史 Proposal。
- False 从“空”恢复为布尔值可能改变既有 mapping 的输出；须用字段类型和显式 null policy 控制，并回归当前用户场景。
- 表达式结果与 XLSX 单元格类型转换可能不一致；需独立回读和精确目标断言。
- expected_effects 仍是 Agent 的结构化解释，不能证明其正确理解自然语言；服务端只能证明被结构化的目标已经满足。
- 指纹过宽会导致不必要的确认失效，过窄会允许陈旧确认；必须以既有 confirmation scope 为基础，通过变化边界测试校准。
- 状态兼容适配应同时保留旧字段，避免旧聊天消费方误读状态。
- 超时恢复依赖工具结果先持久化及幂等键稳定；真实 Provider/浏览器验证不能被单测替代。

### 回退原则

若新表达或结果适配导致回归，保留旧 Proposal 读取和旧工具字段；关闭新表达节点的生成入口，仅在保证旧方案可读且执行安全时回退。不得把确认后状态、失败候选或附件交付状态回滚成虚假 success。回退步骤与模块升级/数据库 schema 影响须在实施审批前补充。

### 本阶段明确不实施

- 不改变原始附件重编译架构，不对上一 Preview 进行隐式字节增量修改。
- 不引入 DAG、事件溯源、事件总线、工作流平台或任意代码表达式。
- 不让 LLM 决定 Odoo ACL、安全边界、确认有效性或文件验证成功。
- 不让 Office Core 解释业务模型或字段语义。
- 不假设所有 Excel 公式均可重算；不把 openpyxl 公式读取当计算结果。
- 不新增模板、客户、单元格或业务模型特例。
- 不在本阶段修改代码、测试、配置、数据库或部署。

## 13. 待审批决策

1. 确认 concat 仅接受 string/null、拒绝隐式 number/date/boolean 格式化；coalesce 候选类型兼容规则和三种 concat null_policy（skip_segment / empty_segment / propagate）是否满足产品需求。
2. 确认 arithmetic 采用 Decimal 语义、Boolean 拒绝作为数字；除法必须由调用方提供 scale/rounding，其他运算只有显式 scale 才量化。该设计不自动读取 Odoo 币种精度。
3. 确认 null_result 默认 error、clear 与 remove 的差异，以及 null 到 XLSX 空白的 Adapter 规范。
4. 确认表达树深度 8、节点数 64、concat 段数 32 仅作为待测建议；在中性压力/边界测试后再冻结实际资源上限。
5. 确认 Outcome 是否只在服务端适配为 outcome + artifact_stage + delivery_state，及旧 Tool Schema/历史 Proposal 的兼容窗口。
6. Provider 超时后的产品体验：恢复时显示既有工具结果/附件，或继续让模型生成说明；无论选择何者都不得重放非幂等操作。
7. 真实浏览器/Provider 验收所需运行环境证据和隔离测试 Thread 的方式。

本版已按 2026-11-06 评审意见收口并冻结：覆盖清单不能证明 Agent 未遗漏自然语言要求；dormant 规则不自动重新激活且第一版仅支持整份已确认 Proposal Restore；确认绑定最终求值 Effect 并在 Effect 变化时失效。表达式资源限制仍是待中性测试确定的建议，不视为已验证阈值。用户于 2026-11-06 在当前会话明确批准冻结 Phase B v0.3；该批准仅冻结设计基线，不授权编码、测试执行或部署。

## 14. 状态声明

| 项目 | 状态 |
|---|---|
| Phase A / A2 报告阅读及引用 | 已用于本设计；未重做审计 |
| 设计文档 | FROZEN v0.3；用户于 2026-11-06 批准冻结；不构成实施授权 |
| 代码/测试/配置/数据库变更 | 未授权，未执行 |
| 自动化测试 | 未运行 |
| 8091 / Provider / Browser E2E | 未运行 |
| Phase C 实施 | 未授权，未开始 |

本设计草案提交后即停止，等待人工评审和单独的实施授权。
