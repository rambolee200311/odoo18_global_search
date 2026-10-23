# M2 动态列表映射实施计划补充 V1.1.0

| 项目 | 内容 |
|---|---|
| 状态 | **FROZEN V1.1.0** |
| 批准 | 负责人于 2026-10-23 批准 CC-M2-005 动态列表映射实施 |
| 上游 | M2 SRS V1.0.0 Frozen；M2 TDD V1.0.0 Frozen + 动态列表补充 V1.1.0 Frozen；M2 实施计划 V1.0.0 Frozen |
| 目的 | 仅为 CC-M2-005 增加有限集合映射与多行卡片的执行门禁；不替代原计划 |

## 1. 实施顺序与门禁

| 阶段 | 内容 | 验收门禁 |
|---|---|---|
| 1 | 锁定 CC-M2-005 动态映射契约与文件白名单 | frozen CC 与本补充追溯一致；不改冻结 SRS/M1 |
| 2 | 服务端 `mapping_groups` 校验及卡片多行数据 | 至少六个稳定目标行；每个 `<select>` 独立；分组摘要来自服务端；旧 scalar 上下文继续兼容 |
| 3 | Prompt/Validator 编排和单次修复 | Prompt 给出有限目标/字段目录；至少五项 mock 映射通过；5/20 漏项重试一次；仍缺项时澄清且无 M1 调用 |
| 4 | 授权集合读取和 M1 writes 编译 | 当前用户权限下 Retriever 返回集合与 server target slots 一一匹配；无 `sudo()`；不匹配 fail-closed |
| 5 | M1 引擎及 Odoo 端到端 | 合成 `.xlsx` 通过 `office_core` 写入、`office_verify` 回读和幂等附件交付；Provider 不访问外网 |
| 6 | 内置浏览器 HVR、清理和交付记录 | 真实聊天卡片显示至少六行/集合摘要；操作不同下拉框不串行；附件下载成功或明确记录阻塞，不虚报 PASS |

## 2. 退出条件

- `office_mapping_verify` 原 V1 schema 测试与覆盖率仍通过；列表映射复用明确 element IDs，不接受模型坐标推算。
- `office_engine_m2` 完整 TransactionCase 通过；前端静态检查通过；Playwright/HVR 证据与 ATR/IHR/FR 相符。
- 有真实 M1 纯 Python 生成与独立回读证据。若 Odoo Spawn 交付失败，记录失败，不扩大到 M1 源码修改或宣告生成闭环完成。
- 测试记录和生成附件按 ORM 清理；开发库仅使用授权的 `odoo18ce`；不创建隔离库。
- 本补充和 CC 的所有实施文件按项目工作流记录、审阅与提交。
