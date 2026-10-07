# CC-011 Global Search 最终验收与交付

## 0. 文档治理

| 项 | 内容 |
|---|---|
| Coding Contract | CC-011 |
| 版本 | v0.1 FROZEN |
| 状态 | FROZEN，进入实施 |
| Intent ID | `GS-SEARCH-FINAL-ACCEPTANCE` |
| 上游 SRS | [SRS_global_search](../../requirement/SRS_global_search.md) v1.4 FROZEN |
| 上游 TDD | [TDD_global_search](../../design/TDD_global_search.md) v0.3 FROZEN |
| 实施计划 | [IMPLEMENTATION_PLAN_global_search](../../implementation/IMPLEMENTATION_PLAN_global_search.md) v0.2 FROZEN，Phase 11 |
| 前置 CC | CC-001~CC-010；TD-001 |
| 模块 | `wd_global_search` |
| 目标 | 汇总需求、技术边界、TV、性能、权限、错误、Preview、升级与发布证据，形成可复现交付结论 |

CC-011 只负责最终验收、补测、范围决定和发布候选交付，不新增未经批准的业务功能。

## 1. 验收范围

- SRS MUST/SHOULD/OUT 验收矩阵；
- TDD 技术边界和禁止项；
- TV-01 至 TV-06 结果和补测；
- CC-001 至 CC-010 的 ATR/HVR/IHR 证据；
- 权限、失败关闭、错误协议、边界、日志和审计；
- Workspace、Preview、窄屏和浏览器兼容性；
- 性能轻量验证、升级 preflight 和回滚范围；
- 发布候选版本、已知限制和后续技术债。

## 2. 验收不变量

1. MUST 需求必须有通过证据，或有明确批准的变更/豁免；
2. SHOULD 需求必须记录通过、未验证或延期原因；
3. OUT 需求不得伪装成已实现；
4. 错误、权限、数据隔离和安全边界不得因补测而放宽；
5. 验收报告必须能从干净环境复现，记录 commit、模块版本和测试命令；
6. 未通过项不得返回发布成功状态，必须归类为阻塞、部分通过或明确延期。

## 3. 必测矩阵

| ID | 验收项 | 证据 | 门槛 |
|---|---|---|---|
| CC11-TEST-001 | SRS MUST 矩阵 | 验收报告 | 全部 PASS 或批准豁免 |
| CC11-TEST-002 | TDD 防护栏 | ATR/IHR | 不违反禁止项 |
| CC11-TEST-003 | TV-04 泄露回归 | TV 报告 | 无跨用户/字段泄露 |
| CC11-TEST-004 | TV-05 浏览器 HVR | HVR | 桌面与窄屏证据完整 |
| CC11-TEST-005 | TV-06 时间/多值/部分失败 | TV 报告 | 语义检查全部通过 |
| CC11-TEST-006 | 权限与失败关闭 | Odoo 测试 | 普通、Portal、多公司均符合契约 |
| CC11-TEST-007 | 错误、日志和审计 | ATR | code 稳定且无敏感输入泄露 |
| CC11-TEST-008 | CC-010 升级与回滚 | 隔离库报告 | 未演练不得发布 |
| CC11-TEST-009 | 文档和复现性 | 发布清单 | 命令、版本、证据齐全 |

## 4. 发布门禁

- 所有阻塞级 MUST 项通过；
- TV-04、TV-05、TV-06 通过；
- CC-010 回滚演练通过，或获得明确的范围豁免并标记不可发布；
- 工作区、依赖、migration、测试和文档在同一发布候选 commit；
- 不修改 Odoo 核心或官方 addons；
- 不引入 Elasticsearch、OpenSearch、LLM 或向量检索；
- 发布候选版本包含已知限制和后续技术债清单。

## 5. 交付物

- SRS 验收矩阵；
- TDD 边界矩阵；
- TV-01~TV-06 报告；
- 性能、权限、错误、Preview、升级报告；
- Chrome/Firefox/Safari 证据及未覆盖矩阵；
- 发布候选版本和回滚清单；
- 最终验收报告。

## 6. 明确不做

- 不在最终验收阶段扩展产品范围；
- 不以未执行的浏览器或回滚测试替代真实证据；
- 不删除失败记录、不修改历史审计、不静默降低门槛；
- 不把 PARTIAL 或 BLOCKED 结论写成 PASS。

## 7. 冻结批准与首轮实施

- 用户批准冻结：2026-10-07 19:14（+08:00）；
- 已进入最终验收实施；
- 首轮 compileall、`git diff --check`、Odoo 模块测试和 TV-06 回归通过；
- 当前结论仍为 `PARTIAL`，未将未执行的隔离数据库回滚和浏览器矩阵写成 PASS；
- CC-011 状态：FROZEN，进入实施。
