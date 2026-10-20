# Office Engine M1 TV P0 补验报告索引

当前有效补验结论见 [`P0_Followup_Report_v0.4.md`](P0_Followup_Report_v0.4.md)。该版本补入用户指定 `TARGET.docx` 的 P0-A 实测结果，并保留此前 P0-B 与 P0-C 的结论。

## 当前状态

| 补验项 | 状态 |
|---|---|
| P0-A 真实 `.docx` 读写 | `PARTIAL`：真实样本普通段落隔离写回和结构检查通过；目标 venv 依赖与 CJK 字体视觉验证未完成 |
| P0-B 真实 `.xlsx` 公式/格式 | `PARTIAL`：真实模板已测，格式和扩展 OOXML 仍需进一步验证 |
| P0-C 本机 queue_job 链路 | `PASS`：模块安装，最终配置下只读后台任务完成 |
| P0-C 生产资源预算 | `INCONCLUSIVE`：Office 真实负载、prefork、代理、worker 限额和 RSS 尚未测 |
| M1 TV | `Partial` |

## 版本沿革

- [`P0_Followup_Report_v0.1.md`](P0_Followup_Report_v0.1.md)：初始环境盘点；当时 P0-A/B/C 均未运行。
- [`P0_Followup_Report_v0.2.md`](P0_Followup_Report_v0.2.md)：取得真实 Excel 样本并完成 P0-B 部分验证；P0-C 当时仅做配置/源码检查。
- [`P0_Followup_Report_v0.3.md`](P0_Followup_Report_v0.3.md)：补充 queue_job 实际安装与后台任务运行证据。
- [`P0_Followup_Report_v0.4.md`](P0_Followup_Report_v0.4.md)：使用 `TARGET.docx` 完成 P0-A 隔离读写和结构回读。

DOCX 结构化证据见 [`P0_Docx_Results_20261019_TARGET.json`](P0_Docx_Results_20261019_TARGET.json)；队列运行的结构化证据见 [`P0_QueueJob_Runtime_20261019.json`](P0_QueueJob_Runtime_20261019.json)，资源预算补充见 [`P0_Resource_Budget_Runtime_20261019.md`](P0_Resource_Budget_Runtime_20261019.md)。
