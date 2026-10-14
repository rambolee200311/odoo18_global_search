# ATR-GS-P0-SEARCH-LATENCY

## 0. 执行元数据

| 项 | 内容 |
|---|---|
| 修复 | P0-02 Search latency telemetry |
| 基线 | `main @ 878a2f7` + 本次工作树 |
| 环境 | macOS；Odoo 18 CE；本地 `odoo18ce` 应用 |
| 日期 | 2026-10-14 |
| 执行者 | Copilot assistant |

## 1. 自动化验证

| 验证项 | 结果 | 范围 |
|---|---|---|
| `test_service_core` | **36/36 PASS** | 总耗时真实计算；每 Resource 成功/失败事件；跳过未启动 Resource；SearchResponse 不新增 latency meta |
| `test_observability` | **4/4 PASS** | 日志 allowlist、结构化 JSON 和 secret-bound hash 回归 |
| Python 编译 | **PASS** | `services/facade.py`、测试模块 |
| `git diff --check` | **PASS** | 补丁格式无 whitespace errors |

## 2. Odoo 应用运行采样

通过授权 Workspace 发送只读 Search API 查询 `gemini chair lamp` 6 次。每次均为 `SUCCESS`、Count 为 2；在 Odoo app 日志中按 request ID 对应的总耗时事件与 Resource 事件整理出下列匿名化统计：

| 指标 | 6 次本地采样 |
|---|---:|
| 总耗时最小值 | 63.484 ms |
| 总耗时中位数 | 71.309 ms |
| 总耗时最大值 | 121.894 ms |
| `sale_order` Resource 耗时中位数 | 48.895 ms |
| `contact` Resource 耗时中位数 | 11.102 ms |
| `purchase_order` Resource 耗时中位数 | 5.526 ms |
| 其它已授权 Resource 耗时中位数 | 0.290–1.536 ms |

每次 Search 都有非零总耗时；7 个实际执行的 Resource 分别产生非零耗时事件。Response JSON 不暴露 `latency_ms`，保持既有 API shape。日志仅提取事件类型、状态、Resource 和数值；request ID、查询/条件 hash 未保存到报告。

## 3. 解释与限制

- 以上为一个本地数据库/授权用户/相同 Query 的 6 次校准样本，不是负载测试、生产基线或 P95 服务等级结论。
- 可用它定位后续针对 `sale_order` Resource 的测试假设；是否需要优化仍需更多不同 Query、Resource 数和负载样本。
- 没有运行会写入数据库的模块升级/集成测试；验证使用无数据库单元测试及正常 Odoo Search API 只读调用。

## 4. 当前结论

**P0-02 的总耗时与分 Resource 观测链路通过定向验证。** 初始本地样本已可供后续 TD-005/问题 6 评估；不得把 6 条样本外推为生产性能结论。
