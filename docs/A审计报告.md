# Office Engine Phase A：通用操作契约专项审计

**范围：只读审计。未修改文件、数据库或服务；未运行测试。**

## 1. Runtime Evidence

- 8091 当前由 Python 进程 **PID 4295** 监听。进程工作目录为 `/Users/lijianqiang/Documents/odoo18_global_search`，使用 Python 3.11；`odoo.conf` 指向数据库 `odoo18ce`，Addon 路径包含工作区内的 `mymodules`、`mymodules/odoo-llm` 和其他目录。
- 当前工作区 `HEAD` 与 `origin/main` 均为 `3ccb863430cd33b70952fd57cadc7624d284e3cf`。Git 状态为 `main...origin/main`，仅有未跟踪文件 `.coverage`。
- 服务日志记录了 Thread `13139` 的 Provider 请求超时（`APITimeoutError`），随后有 HTTP 200 请求记录。日志没有证明这些后续请求与超时请求属于同一轮完整对话或对应同一工具结果。
- 进程路径与工作区一致，**但无法直接证明该进程内已加载的 M2 Python 模块与当前工作区文件内容一致**。进程信息和日志均不能给出已加载模块的源码指纹。因此标记为 **UNVERIFIED**；没有证据支持 `Runtime Code != Workspace Code`。本阶段没有重启服务。

## 2. Current Execution Chain

```text
llm.thread.generate
  → 原生 llm_assistant.generate_messages 循环
  → Provider 响应 / assistant tool_calls
  → 原生 llm_tool 创建并执行 tool message
  → office_prepare_context 或 office_save_mapping_preview
  → Proposal / repeat_rows / cell_edits 校验与确认
  → render_bridge 编译映射和当前数据
  → office_core 将写入编译为 Document Operation List
  → DocumentOperationEngine 执行候选文件并验证
  → office_verify 独立验证
  → Preview 或 Finalize 附件关联聊天消息
  → 工具结果写入对话历史，原生循环继续请求 Provider
```

代码依据：M2 入口调用原生 `generate()` 见 [llm_thread.py:131](/Users/lijianqiang/Documents/odoo18_global_search/mymodules/office_engine_m2/models/llm_thread.py:131)；原生助手循环见 [`generate_messages()`](/Users/lijianqiang/Documents/odoo18_global_search/mymodules/odoo-llm/llm_assistant/models/llm_thread.py:225)；工具结果在原生 `mail.message` 中保存，见 [mail_message.py:135](/Users/lijianqiang/Documents/odoo18_global_search/mymodules/odoo-llm/llm_tool/models/mail_message.py:135)。M2 对 Preview/Finalize 消息的附件 Store 处理见 [llm_thread.py:420](/Users/lijianqiang/Documents/odoo18_global_search/mymodules/office_engine_m2/models/llm_thread.py:420)。

## 3. Dependency / Precondition / Conflict

### Dependency 与执行顺序

Canonical Schema 1.1 用有序 `operations` 数组表达执行顺序，`operation_id` 必须唯一；没有 `depends_on`、前序操作输出引用或通用 Effect/产物引用字段。Schema 明确要求 `repeat_rows` 必须为第一项，见 [schema.py:29](/Users/lijianqiang/Documents/odoo18_global_search/mymodules/office_document_operations/schema.py:29)。

生产 Mapping 编译时，`_mapping_operation_list()` 将 `repeat_rows` 放在首位，随后放映射写入，再放显式单元格编辑；同一目标上的明确编辑因此可以有序覆盖前面的映射值，见 [office_core/engine.py:688](/Users/lijianqiang/Documents/odoo18_global_search/mymodules/office_core/engine.py:688)。

`repeat_rows` 是特殊处理项：执行器调用已配置的 Handler 扩展文件，再对扩展后的文件执行剩余操作。它没有按 `operation_id` 产出可供后续操作引用的逻辑目标；后续操作使用的是当前中间文件中的坐标。见 [engine.py:73](/Users/lijianqiang/Documents/odoo18_global_search/mymodules/office_document_operations/engine.py:73)。

### Precondition 与中间状态

执行器先把完整的后续操作序列应用于独立 Workbook 模拟，再执行真实候选文件上的同一序列；目标不存在或后续操作不适用时，预检会失败。输出保存后还会重新打开并独立验证，验证通过才原子替换输出。见 [engine.py:120](/Users/lijianqiang/Documents/odoo18_global_search/mymodules/office_document_operations/engine.py:120) 和 [validator.py:24](/Users/lijianqiang/Documents/odoo18_global_search/mymodules/office_document_operations/validator.py:24)。

对 `repeat_rows`，执行器验证 Handler 对原始输入的重复调用结果一致；但通用 Validator 随后以扩展后的中间文件作为验证输入，校验后续操作，不是独立重放结构扩展本身。M1 的 `office_verify` 也接收预扩展文件进行映射结果验证，见 [office_core/engine.py:751](/Users/lijianqiang/Documents/odoo18_global_search/mymodules/office_core/engine.py:751) 和 [office_core/engine.py:817](/Users/lijianqiang/Documents/odoo18_global_search/mymodules/office_core/engine.py:817)。这是结构扩展独立验证覆盖的**边界**，现有证据不足以将其判为运行缺陷。

### Target 与 Conflict

- 通用 Document Operation 的目标主要是工作表、单元格、区域或列范围。坐标表示当前文件状态中的位置；Schema 没有跨操作的逻辑目标引用。
- M2 在重复行映射中提供稳定 `record_target`。记录目标的最终行在当前重复行排序确定后解析，见 [office_mapping_tools.py:2906](/Users/lijianqiang/Documents/odoo18_global_search/mymodules/office_engine_m2/models/office_mapping_tools.py:2906)。对应测试 `test_record_targeted_cell_edit_follows_repeat_row_after_sort_and_confirmation` 存在。
- Mapping 校验保留真实冲突检查，但能按调用方声明的顺序允许映射后编辑同一目标；M2 和 M1 均传入 `ordered_cell_edit_overrides=True`。相关实现见 [validator.py:508](/Users/lijianqiang/Documents/odoo18_global_search/mymodules/office_mapping_verify/validator.py:508) 和 [office_mapping_tools.py:3002](/Users/lijianqiang/Documents/odoo18_global_search/mymodules/office_engine_m2/models/office_mapping_tools.py:3002)。重复映射、明确编辑重复项及不兼容的澄清/清空仍会被检测。
- 这表明同一目标被多个操作引用并不总是被视为非法：格式和值写入分属不同属性；映射后明确编辑也可按顺序执行。相关测试包括 `test_explicit_cell_edit_is_ordered_after_mapping_write_but_duplicate_mappings_still_conflict`。
- **实际 Thread 证据与当前源码/测试存在未解释差异**：用户提供的 Thread `12063` 记录显示，重复行扩展确认后，工具结果报告执行阶段又要求 `cell_edits` 确认。当前源码将重复行扩展风险作为 `additional_risks` 传入同一个确认 Gate，见 [office_mapping_tools.py:3060](/Users/lijianqiang/Documents/odoo18_global_search/mymodules/office_engine_m2/models/office_mapping_tools.py:3060)；测试 `test_repeat_row_confirmation_authorizes_its_derived_cells_and_formulas` 覆盖了确认后成功生成文件。所提供对话没有原始工具参数、Pending payload 或对应服务器异常栈，且运行模块与当前工作区的对应关系未证实，故这次失败的具体根因是 **UNVERIFIED**。

## 4. Authorization

单元格覆盖确认绑定 Thread、用户、请求消息、Session 和 Proposal revision、当前 Preview 附件、模板/上下文/文档指纹、观测到的原值、操作范围及风险；Gate 执行时重新比较这些值，并要求唯一且精确的用户确认消息。见 [office_mapping_tools.py:221](/Users/lijianqiang/Documents/odoo18_global_search/mymodules/office_engine_m2/models/office_mapping_tools.py:221) 和 [office_mapping_tools.py:1542](/Users/lijianqiang/Documents/odoo18_global_search/mymodules/office_engine_m2/models/office_mapping_tools.py:1542)。

重复行扩展风险记录新增明细范围、插入行数、汇总行位移及公式影响，随后进入同一确认 Gate，见 [office_mapping_tools.py:366](/Users/lijianqiang/Documents/odoo18_global_search/mymodules/office_engine_m2/models/office_mapping_tools.py:366)。`force_override` 本身不构成授权，代码以用户消息及服务端绑定条件决定是否通过。

Finalize 另行要求当前 Proposal/Session revision 与预览一致、最新用户消息符合精确确认语义，并在生成前重新编译与比较源数据指纹；变化时要求重新确认，见 [office_mapping_tools.py:3268](/Users/lijianqiang/Documents/odoo18_global_search/mymodules/office_engine_m2/models/office_mapping_tools.py:3268) 和 [render_bridge.py:618](/Users/lijianqiang/Documents/odoo18_global_search/mymodules/office_engine_m2/services/render_bridge.py:618)。

## 5. Public Tool Return Inventory

| 工具 | 当前返回语义与字段 | 状态表达能力及消费方 |
|---|---|---|
| `office_prepare_context` | 成功时 `status=ready`；返回 Session/Proposal revision、目标模型及锚点记录、所选记录及顺序、文档格式、`target_manifest`、`allowed_fields`、当前 Proposal、重复行集合、历史 revision 和 Mapping 限制。见 [office_mapping_tools.py:2362](/Users/lijianqiang/Documents/odoo18_global_search/mymodules/office_engine_m2/models/office_mapping_tools.py:2362)。 | Agent 读取上下文后选择后续工具；不是文件执行结果。 |
| `office_save_mapping_preview` | 生成或复用预览时最终为 `status=success`，并带 `operation_status=preview_ready/unchanged`、`operation_executed`、revision、附件 ID/文件名及 `attachment_posted_to_thread` 等交付元数据。风险返回 `needs_confirmation`，含 `error_code`、影响范围、原值/新值、确认问题和操作范围。失败还可能是 `blocked` 或 `error`。见 [office_mapping_tools.py:61](/Users/lijianqiang/Documents/odoo18_global_search/mymodules/office_engine_m2/models/office_mapping_tools.py:61)、[office_mapping_tools.py:1733](/Users/lijianqiang/Documents/odoo18_global_search/mymodules/office_engine_m2/models/office_mapping_tools.py:1733)。 | M2 的原生 Thread 代码检查业务结果、附件关联并发布消息到 Store，见 [llm_thread.py:432](/Users/lijianqiang/Documents/odoo18_global_search/mymodules/office_engine_m2/models/llm_thread.py:432)。 |
| `office_finalize` | 成功为 `finalized`，含 revision、附件和 delivery message ID；数据或模板变化可返回 `requires_reconfirmation`；其他失败返回 `failed`，带阶段、artifact/delivery 状态及错误信息。见 [office_mapping_tools.py:3238](/Users/lijianqiang/Documents/odoo18_global_search/mymodules/office_engine_m2/models/office_mapping_tools.py:3238)。 | Thread 验证并加载正式附件 Store 数据；加载失败会把工具结果改为 `failed`，见 [llm_thread.py:478](/Users/lijianqiang/Documents/odoo18_global_search/mymodules/office_engine_m2/models/llm_thread.py:478)。 |
| `office_restore_proposal_revision` | 可返回 `restored`、`unchanged`，或生成预览后的 `preview_ready`；含 revision 和附件交付信息。见 [office_mapping_tools.py:3163](/Users/lijianqiang/Documents/odoo18_global_search/mymodules/office_engine_m2/models/office_mapping_tools.py:3163)。 | 由原生工具循环消费并在预览可见时发布附件 Store 事件。 |

现有接口**没有统一表达**要求列出的五个对外结果：
- `confirmation_required` 实际为 `status=needs_confirmation`、`error_code=confirmation_required`。
- 没有统一的 `clarification_required` 状态；不完整 Proposal 的 `incomplete` 会被包装成 `status=error` 并保留细节。
- `blocked` 在 Preview 可见，但 Finalize 的权限异常映射为 `failed`。
- `completed` 是原生工具消息的执行状态或 Session 状态，不是所有 Office 工具共用的结果状态。
- 预览成功、附件已发布有独立字段；Finalize 对“文件已生成、聊天交付待完成”也能表达 `artifact_state=generated`、`delivery_state=pending`。这与工具本身执行失败可在嵌套结果中区分，但状态字段并不统一。

原生 `llm_tool` 会把任何正常返回的 dict 标为外层工具消息 `completed`，Office 的业务结果放在嵌套 `result.status`。因此“工具函数调用完成”不等于“Office 操作成功”。见 [mail_message.py:135](/Users/lijianqiang/Documents/odoo18_global_search/mymodules/odoo-llm/llm_tool/models/mail_message.py:135)。

## 6. User-facing Outcome

原生助手把 Provider 消息写入 Thread；工具执行结果持久化后，循环会继续调用模型。Provider 异常被记录为 `LLM API Error` 消息，见 [llm_assistant/llm_thread.py:289](/Users/lijianqiang/Documents/odoo18_global_search/mymodules/odoo-llm/llm_assistant/models/llm_thread.py:289)。由于每个工具调用后会 commit，**工具已执行并保存结果、但随后模型响应超时**在调用链上可与“工具执行失败”分离。

不过，本次没有找到覆盖“工具成功后下一次 Provider 请求超时”的专项测试；当前日志中的 Thread `13139` 超时也没有与某次已成功工具调用建立可核验的关联。

Preview 错误包装可能把 `str(exc)` 放入工具结果；Finalize 对非预期异常使用较通用的消息。Agent Prompt 指示模型按状态解释，但最终自然语言回复没有代码级校验来确保其与文件/附件状态一致。已有附件 Store 检查能发现交付关联问题，却不能从代码本身证明模型每次最终陈述都与操作状态一致。

## 7. Test Coverage

**本次只读检查了测试源码，没有执行测试。** 现有相关测试包括：

- 顺序执行、repeat rows 和统一 Core 路径：`test_repeat_rows_is_an_ordered_core_operation_before_mapping_writes`、`test_legacy_mapping_writes_and_repeat_rows_use_the_same_core_operation_path`，见 [test_document_operations_integration.py:101](/Users/lijianqiang/Documents/odoo18_global_search/mymodules/office_core/tests/test_document_operations_integration.py:101)。
- 同目标的合法有序写入与重复映射冲突：`test_explicit_cell_edit_is_ordered_after_mapping_write_but_duplicate_mappings_still_conflict`，见 [test_office_core.py:300](/Users/lijianqiang/Documents/odoo18_global_search/mymodules/office_core/tests/test_office_core.py:300)。
- 重复行确认、确认后写入、公式扩展：`test_repeat_row_confirmation_authorizes_its_derived_cells_and_formulas`，见 [test_native_chat_integration.py:354](/Users/lijianqiang/Documents/odoo18_global_search/mymodules/office_engine_m2/tests/test_native_chat_integration.py:354)。
- 确认后排序的记录定位：`test_record_targeted_cell_edit_follows_repeat_row_after_sort_and_confirmation`，见 [test_native_chat_integration.py:587](/Users/lijianqiang/Documents/odoo18_global_search/mymodules/office_engine_m2/tests/test_native_chat_integration.py:587)。
- 文件变化、范围扩张和越权目标使确认失效：`test_confirmation_is_invalidated_when_preview_file_changes`、`test_confirmation_cannot_be_reused_after_mapping_scope_expands`、`test_force_override_cannot_expand_to_target_outside_manifest`。
- 工具结果、附件投递与恢复：`test_finalize_reports_generated_artifact_when_chat_delivery_is_pending`、`test_finalize_store_failure_updates_tool_result_and_live_message`、`test_preview_tool_streams_attachment_metadata_to_native_chat_store`。
- 原生工具循环与断连：`test_native_tool_call_response_continues_through_assistant_loop`、`test_sse_client_disconnect_does_not_cancel_native_tool_loop`。

**覆盖缺口：**未发现“已提交 Office 工具成功结果后，下一次真实 Provider 请求超时”的专项测试；也未发现能解释 Thread `12063` 这次确认不匹配的工具参数和确认状态测试证据。以上测试均为源码中存在的测试，不代表本轮重新执行通过。

## 8. Findings

| 级别 / 状态 | 发现与证据 |
|---|---|
| **High — UNVERIFIED** | Thread `12063` 对话记录报告了重复行确认后的执行失败；工作区源码与对应 TransactionCase 展示了共用确认 Gate 的成功路径。因没有该次工具参数、Pending 状态和异常栈，且 8091 的加载代码身份未确认，不能确定根因。 |
| **Medium — 已证实的接口现状** | Office 工具状态词汇不统一；“工具调用 completed”与 Office 业务状态分层存放。五种对外结果不能由单一、统一字段直接区分。 |
| **Medium — 能力边界，不等于缺陷** | Canonical 操作列表支持线性顺序和当前状态坐标，但没有通用依赖边、操作输出引用。M2 的稳定记录定位能力限于其重复行映射契约。 |
| **Medium — 验证证据边界** | 重复行扩展由专用 Handler 执行；Canonical Validator 对扩展后续操作独立回读，但没有从原始文件独立重放该结构扩展。重复行本身有专门算法与测试；本次证据不足以判断为错误结果。 |
| **Medium — 测试缺口** | Provider 超时可发生在工具执行结果持久化后的后续模型请求阶段，但没有对应专项测试，也无法把当前日志中的超时和某次工具成功关联。 |
| **UNVERIFIED** | 8091 进程使用工作区路径，但当前加载的 Python 模块是否与工作区源码完全一致，无法直接证明。 |

## 9. Phase B Inputs

后续阶段需要评审的事实问题：

1. 线性有序操作是否足以描述所需依赖，哪些场景需要让后续操作引用前序结构操作产物？
2. 对跨排序或结构变化的操作，现有物理坐标和 M2 `record_target` 分别覆盖哪些使用情形？
3. 现有 Preview、Finalize、确认、澄清及权限失败状态如何被 Agent 和界面消费，当前混合状态是否满足审计与业务反馈需要？
4. 重复行扩展需要怎样的独立验证证据，才能覆盖从源文件到扩展后文件的结构变化？
5. Thread `12063` 的确认失败如何与当时实际工具参数、确认绑定和 8091 已加载代码对应起来？

**审计结论：**工作区源码显示，生产写入存在明确的线性执行顺序、执行前模拟、确认范围重验和保存后验证；坐标目标及重复行记录目标各有不同语义。当前最大的证据问题是 Thread `12063` 的确认失败无法与当前源码和已有测试相互印证，以及 8091 实际加载源码身份未证实。阶段 A 到此停止；未设计或实施修复。