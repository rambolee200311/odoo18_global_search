# ATR-GS-DYNAMIC-RESOURCE-SELECTOR-COUNTS

## 状态

PARTIAL

## 验收结果

| 验收项 | 结果 | 证据 |
|---|---|---|
| Published Snapshot 驱动 Resource Descriptor | PASS | Workspace 显示 7 个当前授权 Resource |
| 无权 Resource 不显示 | PASS（当前用户） | Workspace 经过 `authorize_resource` |
| Resource 多选 | PASS | Contact 与 Sales Order 同时选中 |
| 空选择表示全部授权 Resource | PASS | All 选择清空 Resource Set |
| 未知 Resource key 拒绝 | PASS（代码路径） | Facade 返回 `INVALID_REQUEST` |
| Permission Boundary 后计算 Count | PASS（代码路径/API） | Executor 先授权再 `search_count()` |
| Count 与 Resource key 一致 | PASS | `counts.by_resource` 与 UI `data-count-for` 对齐 |
| Query/Selection/Refinement 刷新 Count | PASS（Chromium） | `GS-CUSTOMER-001` 浏览器验证 |
| Partial/Failure 不伪造 Count | PASS（代码路径） | Aggregator 仅合并成功 outcome count |
| Python 编译 | PASS | `compileall` |
| JavaScript 语法 | PASS | `node --check` |
| 空数组/未知 key 全部边界组合 | PARTIAL | 代码覆盖，尚未完成独立 Odoo 集成测试矩阵 |
| 性能预算 P95 | NOT RUN | 尚未执行正式性能采样 |
| Firefox/Safari/Edge 矩阵 | NOT RUN | 尚未执行 |

## 结论

CC-012 的核心功能已实现并通过当前 Chromium 和 API 验证，但不能将本记录
解释为完整跨浏览器或性能验收通过。性能、浏览器矩阵和 Odoo 原生集成测试
证据补齐前，CC-012 保持 `PARTIAL`。

## 发布阻塞项

- 完成 Firefox、Safari、Edge 桌面/窄屏验证；
- 完成 Count P95 与刷新 P95 测量；
- 在 Odoo 测试运行器中执行 Resource Selector、未知 key、权限隔离测试；
- 将最终证据回填到 CC-011 Final Acceptance。
