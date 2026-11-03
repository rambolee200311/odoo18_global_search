# ATR — M2 通用 XLSX 重复行扩展

| 项目 | 结果 |
|---|---|
| 执行日期 | 2026-10-27 |
| 实现 | `office_core.expand_repeat_rows()` 通用结构指令 |
| Addon 版本 | `office_engine_m2` 18.0.18.0.0 |
| Odoo / 数据库 | Odoo 18 / 本机开发库 `odoo18ce` |
| Provider | 本机 `127.0.0.1:8909` OpenAI-compatible Mock；未调用外部 Provider |
| 总体结果 | 定向结构测试 PASS；Addon 全量测试 PASS；S05457 聊天生成与 M1 回读 PASS |

## 变更内容

- `office_core` 新增 `expand_repeat_rows(source, instruction, budget)`。调用方传入 `{action: "insert_repeat_rows", sheet, start_row, record_count, columns}`；引擎校验指令、按汇总公式识别汇总行、仅在现有容量不足时扩展行，并返回扩展前后位置和插入行数。
- 行扩展不读取文件名、业务模型或模板标签。公式按相对引用向下填充；汇总行的 `SUM` 区间随明细末行扩展；下方单元格、公式引用和合并区域同步平移。超过工作表或资源预算时拒绝处理。
- 聊天入口和 M1 渲染桥均使用相同的通用指令结构；聊天入口从调用方提供的起始单元格、当前模板可写列和当前集合行数构造指令。映射仍由 M2 映射规则负责。
- 已确认 `office_core`、`office_verify`、`ai_orchestrator.py`、`render_bridge.py`、`chat_entrypoint.py` 中没有业务模板名称、固定明细坐标、固定汇总坐标、专用行数上限或 `cmr_layout` 引用。`cmr_layout.py` 不存在。

## 自动化测试

### 5 行精确行号契约

指令从第 23 行开始，`record_count=5`，原汇总行第 26 行，模板容量 3 行。测试确认引擎新增 2 个物理行，使明细区为 23–27，汇总行移至第 28 行，并验证 `SUM(D23:D27)`、`SUM(F23:F27)`、首行相对公式复制及下方内容移动。

定向执行日志：`/private/tmp/office_engine_repeat_instruction_targeted_final.log`

```text
TestXlsxRowExpansion: 7 tests
0 failed, 0 error(s)
```

### Addon 全量回归

日志：`/private/tmp/office_engine_repeat_instruction_final_full.log`

```text
office_engine_m2: 123 tests 75.27s
0 failed, 0 error(s) of 97 tests
```

运行时对项目中 3 个既有不可安装模块的告警仍存在，与本次改动无关；`office_engine_m2` 测试全部通过。

## S05457 本地聊天闭环

- 使用 Odoo 用户 2 的权限，在 `llm.thread_2500` 复用该线程已有模板附件 ID `11834`，通过 `thread.generate()` 触发实际聊天服务、Mock Provider、M2 Proposal、M1 `render_candidate` 和 `office_verify` 回读。
- 销售订单 `S05457` 实际有 6 条明细。结果没有为符合 5 行演示而省略订单行：明细按源顺序写入第 23–28 行，汇总公式行在第 29 行。
- 最终重启后的复验助手消息 ID `38737`，输出附件 ID `12318`：`preview_S05457_CMR-危险品禾麦CMR模板.xlsx`，MIME 为标准 XLSX，大小 9,408 字节。浏览器页面显示 6 行摘要及绿色 XLSX 附件卡片。
- 独立回读文件：`/private/tmp/office_engine_S05457_repeat_instruction.xlsx`。B23:B28 为 6 条产品描述，D23:D28 为数量，E23:E28 为产品档案重量，F23:F28 均保留相对公式 `=Drow*Erow`；D29、F29、G29 的公式分别覆盖 `23:28`。M1 验证状态为 PASS。
- 浏览器验收通过内置浏览器查看本地聊天页完成。由于聊天文件选择器既有问题，本轮用当前用户 ORM 触发原附件的生成链路，再在 8091 页面确认了真实助手消息和结果附件；不把该操作描述为浏览器文件选择器上传成功。

## 截图与证据

- 内置浏览器当前留在 `http://127.0.0.1:8091/odoo/action-631?active_id=llm.thread_2500`，可见最新 S05457 请求、AI 映射摘要和绿色 XLSX 预览附件。截图在本轮内置浏览器验收记录中。
- 生成文件与两份 Odoo 测试日志保留在上列路径，可直接下载/复核。

## 验收结论与限制

- 5 行样例：明细行 23–27，汇总行 28，PASS。
- S05457 全量：6 条明细全部保留在 23–28，汇总行 29，PASS。
- 该能力是通用 XLSX 结构操作，不代表支持任意 Office 格式、任意公式类型或任意未验证模板。共享公式/特殊公式等无法安全平移的结构仍会拒绝处理；M2 当前聊天入口的数据模型能力边界沿用既有实现。
- 浏览器通过重新加载确认生成消息和附件卡片可见；附件内容另由独立 XLSX 回读确认。没有声称在界面中逐格打开电子表格应用。
