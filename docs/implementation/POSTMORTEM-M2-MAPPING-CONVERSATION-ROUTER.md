# M2 聊天映射链路故障定位报告

| 项目 | 记录 |
|---|---|
| 状态 | 代码级尸检与路由修复完成 |
| 检查范围 | `llm_thread.py`、`mapping_conversation.py`、`ai_orchestrator.py`、`mapping_service.py`、`chat_entrypoint.py` |
| 目的 | 解释疑问句被误当成修改、无变更却声称已更新、以及多轮状态是否持久化 |
| 行号说明 | 以下行号对应本报告检查时的工作树版本；后续修改会改变行号 |

## 结论摘要

故障并非单一的“模型幻觉”。实现中已有会话和疑问句分支，但没有完整的三类意图路由。普通文本在确认分支之外默认进入修改流程；疑问句虽然会进入独立回答函数，该函数在预览过期时仍会重新渲染预览；修改服务只要得到一个可预览的 Proposal，就会固定声称“已按你的修改更新映射”，即使新旧 Proposal 实际相同。结果是**路由边界和回复依据不可靠**，并非可以归咎于 LLM 的自然语言幻觉。

## 四项尸检结果

### 1. 状态断链：是否读取已有 Proposal？

**结论：有持久化状态读取；不是每轮都重新分析模板。**

- 普通文本入口在 [llm_thread.py](/Users/lijianqiang/Documents/odoo18_global_search/mymodules/office_engine_m2/models/llm_thread.py:31) 的 `generate()` 中查找当前 Thread 的活动 Session，并把找到的 `session.id` 交给 `process_mapping_chat_turn()`（第 41–57 行）。
- 疑问回答通过 [mapping_conversation.py](/Users/lijianqiang/Documents/odoo18_global_search/mymodules/office_engine_m2/services/mapping_conversation.py:307) 的 `_post_mapping_question()` 调用 `_load_mapping_data(session)` 读取 `mapping_rules_json`（第 309–318 行），直接据此回答目标单元格当前映射。该分支不调用 LLM。
- 修改分支的 [ai_orchestrator.py](/Users/lijianqiang/Documents/odoo18_global_search/mymodules/office_engine_m2/services/ai_orchestrator.py:879) `revise_mapping_from_chat()` 也先通过 `_load_mapping_data(session)` 读取当前 Proposal（第 915–916 行），并将它作为 `current_proposal` 放入下一次 Provider 请求（第 957–969 行）。只有输入被送入此修改分支时才会请求 LLM。
- Session 选择器按 Thread、owner、company 和活动状态检索并排序（[mapping_conversation.py:52](/Users/lijianqiang/Documents/odoo18_global_search/mymodules/office_engine_m2/services/mapping_conversation.py:52) 至第 69 行）；还尝试用最近带预览附件的助手消息绑定 Session（第 77–105 行）。因此状态并非不存在，但依赖“最近附件/最新 Session”启发式选择，且入口与处理函数各选一次，仍有选错会话的空间。

### 2. 意图路由：疑问为何可能触发预览？

**结论：存在简单问题正则，但没有完整的提问/修改/确认/不明确四路 Router。**

- 目前只有 `_QUESTION` 和 `_CONFIRM` 两条正则（[mapping_conversation.py:17](/Users/lijianqiang/Documents/odoo18_global_search/mymodules/office_engine_m2/services/mapping_conversation.py:17) 至第 20 行）。
- 处理顺序是先识别 `_QUESTION`，再识别 `_CONFIRM`，其余所有文本都在第 268–269 行默认调用 `revise_mapping_from_chat()`。这意味着“看起来像问句但未匹配正则”的表达、闲聊或含糊指令都会被当作修改请求发给 LLM。
- 更直接的副作用在 `_post_mapping_question()`：当问题涉及已映射坐标时，会检查预览数据指纹；若过期，则第 351–356 行调用 `render_preview()`。因此即使问句识别正确，也可能在问答过程中生成新预览。这违反了“提问只读 Proposal、绝不生成文件”的业务边界。
- `chat_entrypoint.py` 的职责是首次 Office 上传时建立 Session、解析模板和启动初次映射；它不是多轮意图路由器。其入口位置见 [chat_entrypoint.py:1](/Users/lijianqiang/Documents/odoo18_global_search/mymodules/office_engine_m2/services/chat_entrypoint.py:1) 及 `start_mapping_from_chat()` 定义。聊天文本续轮由 `llm_thread.generate()` 转交 `mapping_conversation.py`。

**附带发现：** 问题回答中原先还有按固定坐标 B4/B7 写死的地址语义说明（当时 `mapping_conversation.py` 第 335–341 行）。它不是从用户当前 Proposal 的单元格标签推导的，可能对其他模板说错。本次一并删除；问答现在只报告 Proposal 中实际存储的目标与来源字段。

### 3. “已按你的修改更新映射”从哪里来？

**结论：这是服务端硬编码的固定话术，不是 Provider 自己输出；旧逻辑没有证明 Proposal 确实改变。**

- `revise_mapping_from_chat()` 将候选 Proposal 保存到 Session（[ai_orchestrator.py:1000](/Users/lijianqiang/Documents/odoo18_global_search/mymodules/office_engine_m2/services/ai_orchestrator.py:1000) 至第 1008 行），随后可能创建预览（第 1011–1020 行）。
- 第 1021–1025 行只依据 `preview` 是否存在选择回复。只要有预览，就固定使用第 1022 行的“已按你的修改更新映射并生成新预览”；该处没有把旧 Proposal 与候选 Proposal 做规范化比较，也没有验证用户要求对应的目标是否真的发生了变化。
- 因此该句不是已证实的“LLM 幻觉”，而是**服务端未经状态差异验证就作出的事实性断言**。即使模型返回原 Proposal、拒绝理解指令或把修改应用到错误位置，只要渲染成功，也会出现这句误导性话术。

### 4. 多轮状态机：每条消息是否都是独立任务？

**结论：不是完全无状态；但续轮处理仍把不明确输入默认为一次修改任务，状态机边界不完整。**

- Session 保存当前 Proposal、状态、revision 和预览引用；例如修改流程读取现有 Proposal 后再保存新版本（[ai_orchestrator.py:915](/Users/lijianqiang/Documents/odoo18_global_search/mymodules/office_engine_m2/services/ai_orchestrator.py:915)、第 1000–1008 行）。确认分支也绑定 `confirmation_required` 和当前 revision 后才调用正式渲染（[mapping_conversation.py:223](/Users/lijianqiang/Documents/odoo18_global_search/mymodules/office_engine_m2/services/mapping_conversation.py:223) 至第 260 行）。
- 但除疑问句和精确确认短语外，剩余文本一律作为修改（第 268–269 行）；“多轮推进”没有明确的 `question / correction / confirm / ambiguous` 路由结果，也没有要求修改分支证明 Proposal 已改变后再宣称成功。
- 问答分支还可能刷新预览（第 342–364 行）。所以现状是“有持久 Session 的若干分支”，而不是严格的、无副作用的多轮状态机。

## 修复边界

本次修复只处理聊天编排正确性：

1. 在纯聊天入口先将输入分类为 `question`、`correction`、`confirm` 或 `ambiguous`。
2. `question` 只读取当前 Session Proposal 并回答；不得调用 Provider、改 Proposal/revision、生成或刷新预览。
3. `correction` 才调用 Proposal 修改服务。必须比较变更前后的规范化 Proposal；未发生实际变化时不得声称已修改或生成新预览，也不得因无变化而重渲染。
4. `confirm` 才能进入 M1 正式生成流程。
5. `ambiguous` 只追问用户意图，不修改、不渲染。
6. 保留当前 ACL、公司隔离、revision 锁和数据新鲜度检查。

不扩展模板识别、字段白名单或 Office 引擎能力；相关问题不属于本次故障修复。

## 修复实施与验证

### 已实施的路由约束

- 在 `llm_thread.generate()` 入口先调用 `classify_mapping_intent()`，再查找当前 Session；入口位置为 [llm_thread.py:31](/Users/lijianqiang/Documents/odoo18_global_search/mymodules/office_engine_m2/models/llm_thread.py:31) 至第 47 行。
- Router 实现在 [mapping_conversation.py:29](/Users/lijianqiang/Documents/odoo18_global_search/mymodules/office_engine_m2/services/mapping_conversation.py:29)。顺序为明确确认、明确修改、纯问题、含糊输入。带疑问标点但含“把…改成…”的明确修改仍走修改；“接受…继续生成”作为明确确认处理。
- 分流在 [mapping_conversation.py:241](/Users/lijianqiang/Documents/odoo18_global_search/mymodules/office_engine_m2/services/mapping_conversation.py:241) 至第 258 行：问题只走只读回答，含糊输入只追问，确认才调用正式渲染，修改才进入 `revise_mapping_from_chat()`。
- `_post_mapping_question()` 现在只加载现有 Session Proposal 并回答（[mapping_conversation.py:337](/Users/lijianqiang/Documents/odoo18_global_search/mymodules/office_engine_m2/services/mapping_conversation.py:337)）；移除了对 `render_preview()` 的调用。因此即使数据指纹过期，提问也不刷新预览、不改变 Proposal/revision、不挂载附件。
- 修改服务在保存和渲染前比较规范化的当前/候选 Proposal（[ai_orchestrator.py:1001](/Users/lijianqiang/Documents/odoo18_global_search/mymodules/office_engine_m2/services/ai_orchestrator.py:1001) 至第 1025 行）。相同则原样保留 Session revision 和现有预览，不创建新文件，只说明没有检测到实际变化；只有确实变化才继续保存并生成预览。

### 自动化证据

- 新增/更新回归测试：疑问句只读且即使源数据过期也不刷新预览；没有映射的历史候选仍按已有 Proposal 回答；含糊输入不调用 Provider、不改 revision；明确提问/修改/确认分类；Provider 返回未变化 Proposal 时不递增 revision、不生成新预览、不输出“已按你的修改更新”。测试位置：[test_conversational_preview.py](/Users/lijianqiang/Documents/odoo18_global_search/mymodules/office_engine_m2/tests/test_conversational_preview.py)。
- 最终源码定向运行记录：`/private/tmp/office_engine_m2_router_postmortem_targeted_final.log`，`TestOfficeM2ConversationalPreview`：14 tests，0 failed，0 error。该运行包括本报告所述最终路由查找条件。
- 全量 Addon 运行记录：`/private/tmp/office_engine_m2_router_postmortem_full_retry.log`，103 tests，0 failed，0 error（Addon 统计 129 tests，88.06s，9101 queries）。此全量运行未使用 `-u`，以避免与 8091 运行中的服务并发更新模块状态。之后删除了问答中的 B4/B7 坐标专用说明；该最终小改动由后续 14 项对话链定向回归覆盖。
- 首次带 `-u` 的全量测试在断言已跑完后，提交 `ir_module_module` 状态时与 8091 服务并发，发生 PostgreSQL `SerializationFailure`。为保护现有服务，未停止 8091；随后不升级模块的全量运行通过。该环境并发情况已记录，不将第一次进程退出码冒充测试失败或成功。
- 静态检查：`py_compile` 和 `git diff --check` 通过。8091 当前仍由原进程监听（PID 49298）；本次验证进程使用 `--http-port=0`，没有接管或停止该端口。

### 行为边界

“提问只回答当前 Proposal”意味着不因询问而同步业务数据或生成新预览。若用户随后明确接受并要求继续生成（例如“接受订单交货地址，继续生成”），Router 会将其识别为确认；正式生成服务仍执行自身的权限、revision 和源数据新鲜度校验，必要时要求再次确认。
