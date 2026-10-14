# IHR-GS-P0-CONCURRENCY-MODE

## 0. 治理与基线

| 项 | 内容 |
|---|---|
| 问题 | P0-03：限流、请求所有权及取消标记保存在进程内存 |
| 模块 | `wd_global_search` |
| 基线 | `main @ 878a2f7` + 本次工作树 |
| 状态 | 单进程支持模式已明确；定向测试通过 |
| 日期 | 2026-10-14 |

## 1. 实施历史

| Entry | 实施事实 | 文件 |
|---|---|---|
| IHR-001 | 将支持边界明确为 Odoo 单进程模式：显式设置 `workers = 0`。Odoo 多线程请求由同一进程内的 `UserLimiter` 锁协调。 | `docs/implementation/wd_global_search_deployment.md` |
| IHR-002 | 明确 `workers > 0` 不受支持：各 worker 的 limiter quota 独立，请求与取消可能落到不同进程，取消状态不可跨 worker 共享。 | `docs/implementation/wd_global_search_deployment.md` |
| IHR-003 | 若 Search 被 limiter 拒绝，在快速返回前移除其临时 request-owner 条目，避免失败请求残留进程内存状态。 | `services/facade.py` |
| IHR-004 | 增加同进程多线程 limiter 互斥、取消所有权校验及限流拒绝清理测试。 | `tests/test_service_core.py` |

## 2. 约束与回滚

- 没有引入共享状态、数据库存储或新架构；没有改变限流阈值或搜索/取消语义。
- 多进程 Odoo 的支持范围被明确为不支持；如需启用，先停止并进行正式设计/契约评审。
- 代码改动可通过回滚 `facade.py` 与相应单测撤销；部署约束文档撤销会重新留下部署模式歧义。
