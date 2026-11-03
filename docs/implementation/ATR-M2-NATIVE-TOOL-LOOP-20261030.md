# ATR-M2-NATIVE-TOOL-LOOP — SSE 断开后原生工具循环恢复

| 项目 | 结果 |
|---|---|
| 日期 | 2026-10-30 |
| 环境 | Odoo 18 CE，数据库 `odoo18ce`，本地 `8091` |
| Thread | `llm.thread/7501` |
| Provider / Model | OpenAI / `gpt-5.6-luna` |
| 状态 | 工具循环恢复已验证；四轮文件验收部分通过（净重目标缺失，未生成正式归档文件） |

## 故障定位

原生 `llm_assistant.generate_messages()` 会在 Assistant 请求工具后执行工具并继续生成；但 HTTP SSE 控制器在客户端断开时会结束 `llm_thread.generate()` 的迭代。原生 `_execute_tool_call()` 先 yield 一条 `requested` 工具消息，之后才调用工具执行器。因此关闭 SSE 响应可使工具记录停留在 `requested`，后续 Provider 请求也不会发生。

本 Thread 的旧 `office_save_mapping_preview` 调用 `call_ujpooWEX5OUBw6u6leza0u7z` 仍显示 `requested`，与上述停止点一致。旧请求没有记录精确的 socket 断开原因；所以历史请求的触发源不能仅凭日志断定，但控制器的截断路径已由回归测试复现。

## 实施与测试

- `mymodules/odoo-llm/llm_thread/controllers/main.py`：将 SSE 监听断开与助手生成分离；客户端不可用后继续消费原生生成器，处理 `GeneratorExit` 时排空剩余工具/模型循环，不再尝试向已关闭响应发送事件。
- `mymodules/office_engine_m2/tests/test_native_chat_integration.py`：新增 `test_sse_client_disconnect_does_not_cancel_native_tool_loop`。修复前断言失败：事件只有 `assistant_tool_call`，未到达工具结果和后续 Assistant；修复后通过。
- 定向 Odoo 回归：`0 failed, 0 error(s) of 1 tests`，日志 `/private/tmp/m2_sse_disconnect_fixed.log`。
- `office_engine_m2` 全量回归：最终结果 `0 failed, 0 error(s) of 106 tests`；模块统计行报告 134 个 test events，日志 `/private/tmp/m2_office_engine_full_after_sse_fix.log`。
- `py_compile`、`git diff --check` 通过。

## 真实 Thread 验收

8091 页面保持在 `http://127.0.0.1:8091/odoo/llm.thread/7501?debug=assets`。同一 Thread 的重试、修改和问答均经过真实 OpenAI Provider；服务器日志记录 2026-10-30 10:35–10:37 多次 `/v1/chat/completions` `200 OK`。

| 轮次 | Tool Call | 结果 |
|---|---|---|
| 第二轮同 Thread 重试：送货地址 | `office_prepare_context` `call_Rfc8aEu2TZgCLlw7C4eRlyas`；`office_save_mapping_preview` `call_W9DWx0J1BSUSNtO1n1YLUDw5` | 两个工具完成。当前规则已是 `partner_shipping_id.contact_address`，模型确认无差异、保留现有预览，没有谎称新预览已生成。 |
| 第三轮：总毛重改为乘 2 | `office_prepare_context` `call_HVeSCRVmhKJEEERu366WrSsB`；`office_save_mapping_preview` `call_lOGrqJH2rJjeUHGXTQmQfscg` | 工具完成，生成新的真实预览附件 `21273`。 |
| 第四轮：净重缺失时留空 | `office_prepare_context` `call_CgzMVlcpO3lLnzOn86rZxVyE`；`office_save_mapping_preview` `call_xemjhfAuqhSnHVfRbcR9uq9E` | 工具完成。模板没有单独净重列/目标，Proposal 未变，模型明确说明预览保持不变。 |

## Excel 回读

真实 Odoo 附件 `21273` 已从 ORM 导出到 `/private/tmp/preview_S05457_thread7501_turn3.xlsx`，MIME 为 XLSX，文件可由 openpyxl 打开。回读断言结果：

- 客户、仓库地址及送货地址与销售订单对应的 ORM 字段值一致；订单在 Mitchell Admin 当前用户权限下唯一可见，共 6 条明细。
- 订单号位于模板实际写入目标 `E17`；无参考号对应 `E19` 保持空白。
- 6 行明细位于第 23–28 行，`G23:G28` 公式均为 `=D{row}*E{row}*2`；合计公式在第 29 行汇总 `D23:D28`、`F23:F28`、`G23:G28`。
- 由于明细从原 3 行扩展到 6 行，原合计行下移 3 行，原第 28 行的 ADR 说明移动到第 31 行。对原模板按该行位移比较后，未映射区域无意外单元格值变化。
- Python 计算的数量合计为 21，按 `数量 × 单件毛重 × 2` 计算的总毛重合计为 16.26。openpyxl 验证的是实际公式文本；未运行 Excel/LibreOffice 公式计算器，文件中的缓存计算值未作为通过证据。
- 模板表头没有净重列，所以无法验证或写入独立净重值；当前预览没有创建净重映射。

## 限制与工作树

当前交付是预览文件，不是经 `office_finalize` 生成的正式归档文件。8091 服务保持运行，PID `66678`。工作树原有未提交改动均保留；没有暂存、提交或推送代码。
