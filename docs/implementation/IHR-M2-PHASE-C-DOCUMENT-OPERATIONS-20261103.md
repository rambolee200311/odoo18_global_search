# IHR-M2-PHASE-C-DOCUMENT-OPERATIONS：Document Operations 并入 `office_core`

| 项目 | 值 |
|---|---|
| 日期 | 2026-11-03 |
| 工作区 | `/Users/lijianqiang/Documents/odoo18_global_search` |
| 分支 / 基线 | `main` / `201d5e777082e1db6be4c9329468455148769dee`（开始前记录） |
| Addon / 引擎 | Odoo 18 CE；`office_core`、`office_document_operations`、`office_verify`、`office_engine_m2`、`office_engine_odoo` |
| 关联 TDD | [`TDD_office_engine_m2_v1.1.0.md`](../design/TDD_office_engine_m2_v1.1.0.md)，第 10 节 |
| 交付结论 | 初始记录为 BLOCKED；见文末 2026-11-03 集成补充：TransactionCase 与本轮指定的 Sales/Purchase 真实浏览器验收现已通过 |

## 目标与根因

阶段 C 将阶段 B 的 XLSX Document Operations 收敛到 `office_core`，避免生产 Mapping Writes 在 Odoo 调用层另走文件写入实现。实施前已确认两处兼容缺口：

1. `office_core.render_candidate()` 的 Worker 参数没有接收 M2 传入的 `authorized_blank_targets`，所以明确清空操作无法沿候选生成与回读链路完成。
2. `office_verify` 对合法、未格式化且没有出现在源 OOXML 中的显式坐标目标过度依赖源文件中已有的单元格记录，拒绝了写入器支持的目标。该问题属于通用坐标验证，不是特定模板问题。

另在 `_validate_mapping()` 检查显式坐标时发现旧 inspection 元素查找路径不适用新建目标；改为使用已验证并构造的目标元素。

## 实施记录

| 文件 | 层次 | 实施内容 |
|---|---|---|
| `mymodules/office_core/service.py` | core API / Worker | `render_candidate()` 将 `preprocessing` 与 `authorized_blank_targets` 传给受限 Worker；新增 `execute_document_operations()` 字节 API。Odoo 调用方不传文件系统路径。 |
| `mymodules/office_core/engine.py` | core 执行 | XLSX 旧 Mapping Writes 转为 Schema 1.1 的 `repeat_rows`、`set_value`、`set_formula`、`format` 操作序列；通过 `DocumentOperationEngine.execute()` 执行。修复显式坐标元素验证；将操作保存回读与 `office_verify.verify_inline()` 结果放入同一候选返回门禁。 |
| `mymodules/office_document_operations/schema.py`、`schemas/document_operation_v1.1.schema.json` | Canonical contract | 保留 1.0 兼容读取；1.1 增加源文件 SHA、首位 `repeat_rows` 和受限算术公式操作。 |
| `mymodules/office_document_operations/engine.py`、`validator.py`、`xlsx_adapter.py` | XLSX adapter / executor | 保持完整操作列表预检、原子候选发布、资源预算、保存后重新打开并与参考执行状态比对。repeat-row 由注入的 core handler 执行并做确定性重放检查。 |
| `mymodules/office_verify/verify.py` | 语义回读 | 支持对现有工作表中的合法显式坐标进行目标检查；空白清除仍需显式授权；非目标结构比较保留。 |
| `mymodules/office_engine_m2/services/render_bridge.py` | M2 生产调用方 | `render_preview()` 使用 `render_candidate()`，要求验证状态 PASS 且 SHA 一致后才创建预览附件。 |
| `mymodules/office_engine_odoo/models/office_document_request.py` | Odoo 生产调用方 | 同样使用 core 候选 API；验证报告缺失、失败或摘要不匹配时不进入附件交付。 |
| `mymodules/office_core/tests/test_document_operations_integration.py` | 集成测试 | 新增 8 个字节 API、Schema、repeat-row、Mapping 转换、显式坐标写入/清空、回读与源指纹测试。 |
| `mymodules/office_core/tests/test_office_core.py` | 回归测试 | DOCX 候选要求带保存后验证报告。 |
| `docs/design/TDD_office_engine_m2_v1.1.0.md` | 设计记录 | 新增第 10 节 Phase C 的实际实现、测试和限制记录。 |

## 生产数据流

```text
M2 render_preview / office_document_request
    -> office_core.render_candidate(bytes, mapping, preprocessing, blank authorization)
        -> bounded Worker
            -> inspect / validate Mapping targets
            -> translate XLSX Mapping Writes to Schema 1.1 operation list
            -> DocumentOperationEngine.execute()
                 -> schema preflight
                 -> repeat_rows handler (if present)
                 -> operations preflight + execution
                 -> save temporary candidate
                 -> validate_saved_output() on reopened candidate
                 -> atomic replacement in Worker temporary directory
            -> office_verify.verify_inline() on source and candidate bytes
            -> return candidate only with passing verification and matching SHA
    -> Odoo caller checks report and SHA
    -> attachment lifecycle continues in existing Odoo services
```

静态搜索中，生产直接调用 `DocumentOperationEngine.execute()` 只有 `office_core`。M2 Preview 和 Odoo Document Request 两个生产 Odoo 调用点都进入 `render_candidate()`。`office_verify.verify_output()` 仍是可供测试/独立调用的服务 API，但生产调用点未发现 core 之外的二次发布验证路径。

### 明确兼容边界

- `render_candidate()` 暂时接受旧 Mapping Writes，但 XLSX Writes 在 core 内转换为正式操作列表后执行；旧 Mapping Writer 没有作为第二套 XLSX 写入器保留。
- repeat-row 的结构算法继续复用 `office_core.row_expansion.expand_repeat_rows()`，但生产候选通过 Schema 1.1 的首位 `repeat_rows` 操作和 `DocumentOperationEngine` 执行。普通 `insert_rows` 不被用来替代既有合计行/公式/合并区域处理语义。
- `_render_xlsx()` 会在执行前展开一次输入副本以检查扩展后目标结构；最终候选则由 canonical `repeat_rows` 操作从原始源文件生成。前者仅用于目标验证，不是候选发布旁路。
- Schema 1.1 当前仅覆盖 XLSX。DOCX 保留 core 内既有 Mapping Adapter 并经过回读；没有声称 DOCX 已迁入操作 Schema。
- `office_document_operations.validate_saved_output()` 检查操作列表对应的保存状态，`office_verify.verify_inline()` 检查 Mapping/文件语义。两者是不同的内部检查；core 只有在两者均通过时才返回可交付候选。若架构要求只有一个验证算法实现体而非一个复合发布门禁，这仍需进一步决策和验证。
- 公式验证检查公式文本和结构，不执行 Excel/LibreOffice 公式重算。

## 变更边界

本记录涉及上述自有引擎、调用方和测试文件。未修改 Odoo 官方 `odoo/` 源码；本轮没有操作数据库、附件或浏览器，没有升级模块，也没有暂存、提交或推送。工作树开始时已包含大量未提交项目变更，均保留。

验证证据和未完成项详见 [`ATR-M2-PHASE-C-DOCUMENT-OPERATIONS-20261103.md`](ATR-M2-PHASE-C-DOCUMENT-OPERATIONS-20261103.md)。

## 2026-11-03 集成补充：Odoo 回归与真实浏览器验收

本节补充并取代上文“本轮未在 Odoo / 浏览器运行”的**当时状态**；上文记录的是阶段 C 核心改造完成时的首轮验收结果，不删除历史结论。

### 实际发现和最小修复

真实浏览器中的采购模板回读发现，先前模型和工具消息虽然声称格式与清空已应用，下载文件中 `D4:E5` 仍为 `General`，`M4` 仍留有 `REMOVE AFTER IMPORT`。问题不是 XLSX Adapter，而是工具契约与执行方法签名不一致：Provider 的 JSON Schema 将 `clear_columns`、`format_patches` 发在 `proposal` 旁边；`office_save_mapping_preview()` 未接收这两个顶层参数，`llm_tool` 按签名构造参数时不会把它们传给执行器。

最小修复位于：

- `mymodules/office_engine_m2/models/llm_thread.py`：在工具 Provider Schema 中将既有的 `clear_columns`、`format_patches` 属性暴露在顶层，兼容嵌套表示。
- `mymodules/office_engine_m2/models/office_mapping_tools.py`：`office_save_mapping_preview()` 显式接收这两个可选参数，合并到 Mapping Proposal 后再做严格解析；同一操作同时出现在顶层与嵌套对象时返回 `duplicate_operation_location`，避免静默覆盖。
- `mymodules/office_engine_m2/tests/test_native_chat_integration.py`：增加真实 Odoo TransactionCase，验证顶层清空与格式参数到达预览执行器，并回读表头、未修改订单号、清空值和数字格式；更新 repeat-row 之后公式目标仍接受用户明确数字覆盖的回归。

这次检查同时保留一项重要负面证据：在修复前，真实 Thread `10125` 的较早预览文件实际回读失败，不能用模型回复或 `preview_ready` 代替文件证据。修复后重建的 Preview 与 Finalize 文件则分别独立回读通过。

### 本轮真实执行证据

| 验收项 | 实际结果 |
|---|---|
| Odoo TransactionCase | Odoo 最终测试汇总为 `0 failed, 0 error(s) of 160 tests`；日志另分别输出 `office_engine_m2: 166 tests` 与 `office_engine_odoo: 26 tests` 模块统计。命令与日志见 ATR。 |
| Python Document Operations / core / verify | 最新 `97 passed in 13.05s`；完整日志 `/private/tmp/phase_c_final_python_tests_after_opsfix.log`。 |
| Sales → CRM 风格工作簿 | 真实 OpenAI Provider `gpt-5.6-luna`、Thread `10004`；读取当前用户可访问的 `sale.order` 记录 GS-SO-0001..0003（记录 ID 5052..5054），按订单号升序。预览和正式下载的金额、`0.00` 格式、M4:M6 清空、标题与表头回读通过。下载文件分别为 `preview_GS-SO-0001_sales_crm_template.xlsx`（5,609 bytes）和 `office-output-fe5e854c-f847-5f8f-a015-5a805fe45ae7.xlsx`（5,608 bytes）。 |
| Purchase → 对账工作簿 | 真实 OpenAI Provider `gpt-5.6-luna`、Thread `10125`、Session `7872`；Retriever 查询 `purchase.order` IDs 1、2，选中 P00001 与 P00002，按 `name` 升序。用户指令明确将原金额乘 1.1，EUR 保留 2 位小数。修复后 Preview 为 revision 10 / proposal revision 3，附件 25658、聊天消息 68379；Finalize 为 revision 13，附件 25659、聊天消息 68384，结果状态 `finalized`。 |
| 浏览器下载与展示 | 采购正式文件在真实 Thread 显示 XLSX 附件卡片；浏览器实际触发下载，Odoo 记录 `/web/content/25659?...office-output-a1de374a-0d59-5107-89e3-ed64fa40945e.xlsx&download=true` 返回 HTTP 200。 |
| 独立回读 | 修复后采购 Preview 和 Finalize 文件均用 openpyxl 读取：P00001/Wood Corner/3026.50/3329.15 EUR，P00002/Gemini Furniture/3095.00/3404.50 EUR；D4:E5 `0.00`；E4/E5 是数字而非公式；M3 `Review Note` 保留、M4/M5 为空；ZIP `testzip()` 无错误。正式文件大小 5,556 bytes，SHA-256 `1be41584f761570fc8f0843160f04e11a3ced67acea3af16f8374bf79b23512e`。 |

### 边界与判定

- 本轮指定的 Odoo 集成与两个业务场景验收项达到 PASS；这不是对所有模型、所有 Office 格式或任意 Document Operation 的无限范围通用性证明。
- 本轮未在浏览器里注入附件发布故障；附件发布失败恢复由 Odoo TransactionCase 中的 retry / same-request 测试覆盖，但不把自动化故障注入写成浏览器人工恢复验收。
- 公式按用户指令写入的是直接数值；本轮没有把 openpyxl 对公式文本的保存或验证表述成 Excel 公式重算。
- 工作区既有修改均保留；没有 stage、commit、push、reset 或 clean。8091 当前由 PID 49929 监听。
