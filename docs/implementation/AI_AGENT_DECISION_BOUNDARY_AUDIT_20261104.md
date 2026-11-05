# AI Agent 决策边界审查与修复记录 — 2026-11-04

## 范围与结论

本次审查覆盖 `office_engine_m2` 的 Proposal 校验、显式单元格编辑确认、`office_core` 操作验证、XLSX Adapter 结构预检及 M2 渲染验证链。审查目标是区分用户可以决定的业务风险与不可绕过的安全/技术约束，不把所有异常都视为“过度防御”。本次结论为 **PARTIAL**：代码和回归已更新，测试命令完成；Odoo 测试计数差异 28 项尚无证据解释，且浏览器记录为已有真实对话证据，本轮没有重新发起 Provider 请求。

发现一处真实的业务决策错误：`office.mapping.tool.office_save_mapping_preview()` 过去会根据旧 TargetManifest 中的 `required` 标记，在用户省略目标时合成清空操作，并可能移除该目标的澄清/跳过状态。已删除该隐式决策，并增加 TransactionCase 回归测试。其它硬拦截按下文分类保留。

## 决策边界与代码证据

### 用户可决定的风险

- `mymodules/office_engine_m2/models/office_mapping_tools.py:323-348`：`_cell_override_needs_confirmation()` 比较实际旧值和请求新值，对非空值、公式及检测到的表头生成风险项。
- 同文件 `:1194-1393`：`_cell_override_confirmation_gate()` 在写入前读取文件并构造影响范围；确认状态绑定 Thread、用户、Session revision、Proposal revision、Preview、模板/上下文/文档指纹、旧值和操作范围。只有唯一的后续用户确认消息与相同操作匹配时，`force_override=True` 才可继续。确认单独不写入；拒绝返回 `blocked`；状态或文件变化会要求重新确认。
- 同文件 `:2456-2482`：显式 `cell_edits` 与 `clear_targets` 进入风险门禁。确认通过后才继续保存和渲染。
- `mymodules/office_engine_m2/models/office_mapping_session.py:490-567`：待确认状态由服务方法写入/清除，并校验当前用户访问和预期 revision。
- `mymodules/office_engine_m2/models/llm_thread.py:223-230, 520-548`：模型指令要求依据工具实际返回的 `needs_confirmation` 解释风险、等待用户回复并重试同一范围；Schema 中确认标记可选，服务端才是授权依据。
- `mymodules/office_mapping_verify/validator.py:517-534, 576-584`：跳过和清空均按显式操作处理；`required` 不是自动写入指令，未映射目标保持原样。

### 已修复的业务决策错误

- 修复位置：`mymodules/office_engine_m2/models/office_mapping_tools.py:2332-2336`。
- 旧行为会把遗留 `required=true`、可写且未映射的目标自动加入 `clear_targets`，并清除相关 clarification/skip。其行为不是风险提示，而是系统替用户做了“清空”的决定。
- 新行为：省略目标是 no-op；只有明确的 `clear_targets` 才清空，且会经过风险门禁。
- 回归测试：`mymodules/office_engine_m2/tests/test_native_chat_integration.py::TestNativeOfficeChatIntegration.test_legacy_required_target_omission_preserves_original_value`。测试将 F2 标为旧式 required 目标，只修改 F1；确认后验证 F2 原值仍在、没有生成 F2 clear 操作，同时 F1 更新并发布到当前 Thread。
- 缺陷复现日志：`/private/tmp/m2-decision-boundary-red.log` 中服务返回 `needs_confirmation`，将未提及的 F2 列入 `affected_scope`，并给出 `content_clear`、旧值 `old value`、新值空白和 `clear` 操作。测试因此失败；返回显示合成了不属于用户请求的清空操作，但尚未执行写入。修复后定向日志：`/private/tmp/m2-decision-boundary-red2.log`（该测试的结果行是 0 failed / 0 error of 1 tests；Odoo 模块 stats 显示 3 tests，统计口径不一致仍需关注）。

## 保留的硬约束及分类

以下阻断不是让系统替用户作业务决定，当前不应改成可由普通确认绕过的风险警告：

| 位置 | 约束 | 分类与理由 |
|---|---|---|
| `office_mapping_tools.py:1185-1191, 1473-1539, 2016-2020, 2423` | Thread/Session 所有权、模型/记录/字段与会话绑定、revision 类型和目标记录可读性 | **安全/授权**：未获当前用户授权的数据或不属于当前 Session 的对象不可由确认放行。 |
| `office_mapping_tools.py:358-539, 594` | 重复行结构、关联字段、表达式、坐标等 Schema/授权校验 | **契约/安全/能力边界**：非法结构或未授权数据路径不属于业务风险；必须返回明确错误。 |
| `office_core/engine.py:30-66, 120-120, 586-632, 771-799` | 不受支持/损坏结构、资源预算、操作版本/文件指纹、候选文件大小、独立验证器缺失或失败 | **文件安全/技术完整性**：确认不能使损坏输入、超限资源或未验证候选文件安全。 |
| `office_document_operations/xlsx_adapter.py:185-195, 211-215, 237-288` | 非锚点合并区域操作、公式覆盖的显式 opt-in、表头清除显式参数、存在无法保证公式/表格/图形/名称引用安全性的中段插行 | **结构安全/执行契约**：保留内容或结构语义无法保证时须拒绝；明确支持的操作通过参数表达，M2 风险确认发生在业务层。 |
| `mymodules/office_engine_m2/services/render_bridge.py:120-168, 182-232, 293-358, 395-454, 480-552` | Session/来源字段重授权、模板/版本新鲜度、M1/统一引擎结果检查、保存后回读、附件字节一致性 | **安全/发布门禁**：失败不得交付成功预览或正式文件。 |
| `mymodules/office_engine_m2/models/llm_thread.py:118, 365-369` | 工具缺失、正式文件未附加或附件不可读 | **部署/交付完整性**：不应虚报成功。 |

### 仍存在的明确能力边界

- 常规 Mapping 将数据字段写入检测到的表头仍被 Proposal 校验拒绝（`office_mapping_verify/validator.py:351-357`）；表头文字修改必须走显式坐标 `cell_edits`，后者经 M2 风险确认。该分流防止把数据来源映射误当成表头编辑，并不阻止用户明确编辑表头。
- 公式写入只能使用受限公式语法（`office_core/engine.py:273-...`），openpyxl 校验的是公式文本，不会重算公式。中段插行遇到公式、定义名称、表格、合并区、筛选、图形或数据验证时，如果无法保证引用安全，Adapter 会拒绝；本次没有通过警告绕过这些结构限制。
- 本次未把所有 `UserError` 改为 `needs_confirmation`：异常还承载 ACL、无效 Schema、损坏文件、资源超限和验证失败等不可绕过情形。未发现其它针对用户业务选择的硬拒绝需要在本次删除；后续对新增操作应依照 `docs/AGENTS.md` 做逐项分类。

## 测试证据

- 修复前新增回归用例失败，并直接观察到旧实现为未提及目标合成 `clear` 风险操作；此时工具没有执行写入。证据见上述 red 日志。
- 修复后定向 TransactionCase：

  ```text
  venv/bin/python odoo-bin -c odoo.conf -d odoo18ce --stop-after-init --http-port=0 --gevent-port=0 --test-enable --test-tags /office_engine_m2:TestNativeOfficeChatIntegration.test_legacy_required_target_omission_preserves_original_value --log-level=test --logfile=/private/tmp/m2-decision-boundary-red2.log
  ```

  Odoo 的 result 行为 `0 failed, 0 error(s) of 1 tests`；模块 stats 行显示 `3 tests`。因此测试发现数与结果统计数存在口径差异，不能把日志简化成“3 个测试全绿”。
- 完整 `/office_engine_m2` TransactionCase 重跑命令：

  ```text
  venv/bin/python odoo-bin -c odoo.conf -d odoo18ce --stop-after-init --http-port=0 --gevent-port=0 --test-enable --test-tags /office_engine_m2 --log-level=test --logfile=/private/tmp/m2-decision-boundary-full-rerun.log
  ```

  退出码 `0`。最终日志：`office_engine_m2: 182 tests 228.26s 14952 queries`；Odoo result：`0 failed, 0 error(s) of 154 tests`；日志中 `Starting Test` 记录数也是 `154`。模块 stats 与结果/启动记录相差 `28`，日志没有说明其含义，记录为 **OPEN**。完整日志另报告三个无关 addon 未加载：`wd_advanced_m2o_record_panel`、`wd_evidence_album`、`wd_qooling_app`；本次 M2 测试仍执行完毕。
- 纯 Python 回归命令：`venv/bin/python -m pytest mymodules/office_mapping_verify/tests mymodules/office_core/tests mymodules/office_document_operations/tests -q`；结果 `210 passed in 13.38s`。
- 静态检查：`git diff --check` 与 `python3 -m py_compile mymodules/office_engine_m2/models/office_mapping_tools.py mymodules/office_engine_m2/tests/test_native_chat_integration.py` 均退出 `0`。
- 首次完整回归 `/private/tmp/m2-decision-boundary-full.log` 出现一项失败：旧测试仍要求未提及的 F18 自动清空。修正测试语义为“保留遗留 required 但未提及的 F18”，随后上面的完整重跑通过。保留首次失败日志，不删除失败事实。
- 真实浏览器证据：本轮在 8091 的 Thread `11292` 读取到已有真实 `gpt-5.6-luna` 对话记录。A2 已有值 `P00001` 被请求临时覆盖为 `OVERRIDE-TEST`，模型展示风险问题，用户回复“确认”，随后工具成功并显示新的 XLSX 附件卡片；后续同样通过确认将 A2 恢复。另有 F1 表头从“供应商产品名称”改成“供应商商品描述”的风险提示、用户确认、成功工具结果及预览附件卡片。本轮未重新发出真实 Provider 请求，也未把该浏览器记录当作新增 required-omission 端到端用例；新回归仍仅由 TransactionCase 覆盖。

## 本次范围外

未改变 Odoo ACL/Record Rules、模板结构保护、M2 附件发布、Finalization 状态、Operation Schema、公式语义或 repeat-row 算法；未提交、暂存或推送代码。最终审查状态保持 **PARTIAL / OPEN**，直到 182 vs 154 的 Odoo 计数差异获得可验证解释；本次没有执行新的真实 Provider 对话。
