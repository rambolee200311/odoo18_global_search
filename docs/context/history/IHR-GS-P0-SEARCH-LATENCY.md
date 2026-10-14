# IHR-GS-P0-SEARCH-LATENCY

## 0. 治理与基线

| 项 | 内容 |
|---|---|
| 问题 | P0-02：Search completion 日志读取缺失的 `response.meta["latency_ms"]`，固定回退为 0；Resource 耗时没有写入日志 |
| 模块 | `wd_global_search` |
| 适用边界 | 既有 CC-008 observability allowlist；不变更 Search API/响应契约 |
| 基线 | `main @ 878a2f7` + 本次工作树 |
| 状态 | 实施完成；自动化与本地只读请求采样通过 |
| 日期 | 2026-10-14 |

## 1. 实施历史

| Entry | 实施事实 | 文件 |
|---|---|---|
| IHR-001 | completion latency 改为由 SearchService 请求入口的 `time.monotonic()` 起点计算至记录事件时；不再读取不存在的 response meta 默认值。 | `services/facade.py` |
| IHR-002 | 对每个实际执行且有计时的 ResourceOutcome，写一条带 `request_id`、Resource key、状态和 `latency_ms` 的结构化事件。未启动的 Resource 不伪记为 0ms。 | `services/facade.py` |
| IHR-003 | Rate-limited、limit/request boundary 事件改记实际已耗时间；cancel endpoint 不再伪报 `latency_ms=0`（其不持有原搜索起始时间）。 | `services/facade.py` |
| IHR-004 | 由单元测试固定总耗时与各 Resource 耗时的字段、精度、事件顺序，并确认 SearchResponse meta/API shape 不被扩展。 | `tests/test_service_core.py` |

## 2. 约束与回滚

- Resource 耗时复用 `executor.execute()` 已测得的 `ResourceOutcome.latency`。
- 总耗时包含配置、授权/描述、聚合和响应构建阶段，直到 completion event 记录前。
- 结构化日志继续经过既有 allowlist；日志不写 Raw Query、条件明文或用户身份。
- 未新增缓存、数据模型、服务或外部依赖，也未直接读写数据库。
- 可通过回滚 `facade.py` 与对应单测恢复原日志行为；无持久化数据或迁移需回滚。
