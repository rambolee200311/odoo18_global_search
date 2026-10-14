# IHR-GS-P0-RELATION-DEPTH

## 0. 治理与基线

| 项 | 内容 |
|---|---|
| 问题 | P0-04：运行时解析 `max_relation_depth`，但部分字段路径校验没有使用该值 |
| 模块 | `wd_global_search` |
| 基线 | `main @ 878a2f7` + 本次工作树 |
| 状态 | 发布期与执行期预算统一；定向回归通过 |
| 日期 | 2026-10-14 |

## 1. 实施历史

| Entry | 实施事实 | 文件 |
|---|---|---|
| IHR-001 | `authorize_searchable_fields` 将每 Resource 的运行时上限传给 `validate_field_path`。超出预算的既有/旧 snapshot 字段路径在授权阶段按配置错误拒绝。 | `services/permission_boundary.py`, `services/field_path.py` |
| IHR-002 | SearchService 先从 Published snapshot 建立经校验的性能配置，再将 Resource 对应上限传入候选 Resource 校验、有效条件校验和 executor。未知/未授权 Resource 的显式性能项仍拒绝；用于超时和结果数的性能映射仍只保留已授权 Resource。 | `services/facade.py` |
| IHR-003 | Executor 在 ORM 搜索前再次以相同上限校验 Resource 字段路径，避免仅依赖发布期校验或 UI 条件校验。 | `services/executor.py` |
| IHR-004 | 老 snapshot 未包含性能项时继续使用默认深度 2；非法上限（非整数、布尔值、范围外值）由既有运行时配置校验拒绝。 | `services/facade.py` |
| IHR-005 | 补充运行时授权、有效条件、executor 预算传递和异常配置测试；既有测试替身适配新增的可选上限参数。 | `tests/test_permission_boundary.py`, `tests/test_service_core.py`, `tests/test_cc015_contract.py` |

## 2. 约束与回滚

- 保持发布期 `max_relation_depth` 规则和默认值；不改变关系路径上限以外的查询语义。
- 未迁移或写入数据库；没有修改 SRS、TDD 或既有 CC。
- 可回滚本次 `facade.py`、`executor.py`、`permission_boundary.py` 及相关测试改动；无持久化数据或迁移需回滚。
