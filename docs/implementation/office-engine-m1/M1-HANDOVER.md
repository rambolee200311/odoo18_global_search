# M1 阶段交付摘要 — Office Engine

**总体状态：PARTIAL。** CC-006 已由负责人批准按 MVP 范围关闭；这不代表 SRS/M1 全范围已验收通过。

请以[《M1 最终交付报告》](M1-FINAL-DELIVERY-REPORT.md)作为本阶段证据汇总入口。该报告区分 CC 行政关闭、FR 满足状态、后续补充样本证据和未完成门禁，并链接到各原始 ATR/HVR/TV 报告。

## 当前已证明

- `office_core`：纯 Python、受控读写及资源/格式拒绝能力已通过各自 CC 范围的自动化验证。
- `office_verify`：独立回读目标值、公式表达式及声明结构；CC-002 按契约范围通过。
- Odoo 封装：spawn 修复后，在开发数据库、当前用户上下文中有 Core → Verify → 私有附件生成成功证据。RSS 监督存在超调风险，不是硬内存限制。
- 聊天：CC-006 MVP 的附件显示、安全拒绝、错误气泡和输入恢复已由负责人验收。后续有一个复杂 XLSX 样本完成聊天生成、校验和浏览器下载。
- DOCX：限定服务端读取、写入及独立回读通过；复杂 DOCX 验证未证明浏览器文件选择器上传和输出下载。

## 正式状态与遗留门禁

| 项目 | 正式状态 | 说明 |
|---|---|---|
| CC-001 / FR | SATISFIED | 纯 Python 核心契约范围 |
| CC-002 / FR | SATISFIED | 独立回读验证契约范围 |
| CC-003 / FR | SATISFIED | 附件事务 Spike 范围 |
| CC-004 / FR | NOT SATISFIED | 后续成功样本不自动改写原冻结契约结果，需正式复评未满足项 |
| CC-005 / FR | NOT SATISFIED | Provider handoff/隔离仍有 BLOCKED/INCONCLUSIVE；Pre-route Fix 只关闭伪装附件限定缺陷 |
| CC-006 | CLOSED（MVP） | 不宣称 M1 全范围通过 |
| `.xls` / `.doc` | 未开放 | 产品保持拒绝；本机转换样本不构成保真承诺 |
| 生产容量与异步容量 | 未验证 / INCONCLUSIVE | 当前证据限开发环境；Queue Job 不属于 M1 同步核心前置 |

## 下一步验收重点

1. 按正式流程复评 CC-004：用最新实现重跑原契约中并发幂等、事务、权限、失败清理和附件交付等未满足项。
2. 独立关闭 CC-005 handoff 与 Provider payload 隔离门禁，不以 Pre-route Fix 或单个 XLSX 样本替代。
3. 补齐 DOCX 浏览器文件选择器上传、下载及原生 Word/WPS 打开验证。
4. 在目标生产环境验证资源预算、平台行为及并发容量；如要支持 `.xls/.doc`，先另行完成格式准入验证。
