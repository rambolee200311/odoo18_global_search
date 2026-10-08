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

## CC-012 v1.1 Verification Addendum

### Automated / Browser Test Status

| Area | Result | Evidence / Limit |
|---|---|---|
| Facet Count vs selected-result count | PASS | Unit test verifies selected `counts` and all-candidate `resource_counts` are separate |
| Empty `resources[]` result scope | PASS | Unit test verifies empty Results with non-empty Facet map |
| Partial failure with empty result scope | PASS | Unit test preserves `PARTIAL_SUCCESS` and failure Resource |
| Authorized candidate filtering | PASS (unit) | Denied candidate omitted by the shared authorization preflight |
| Odoo add-on test suite | PASS | 8 Odoo tests, `wd_global_search` module test stats |
| Core service/permission unit suite | PASS | 13 tests via Odoo shell |
| JavaScript syntax / Python compile / diff checks | PASS | `node --check`, `compileall`, `git diff --check` |
| First Search selector initialization | PASS (Chromium automation) | Selector hidden before Search; first request sent all 7 authorized keys |
| Facet scope independent of selection | PASS (Chromium automation) | After removing `sale_order`, its Facet stayed 20; selected Results count became 21 |
| Empty selection and explicit reselect-all | PASS (Chromium automation) | Empty array returned zero Results, Facets remained visible; reselect sent all authorized keys |
| Zero hide / later positive reappearance | PASS (Chromium automation) | No-match query hid zero-count Resources; subsequent match displayed positive Resources unselected |
| Page-size/pagination regression | PASS (Chromium automation) | Sizes 20/50/100 honored; `009` page 2 returned rows 11–20 of 324 |
| Preview-free Workspace regression | PASS (Chromium automation) | Desktop/Narrow had no Preview pane or Preview API requests |
| Partial failure UI presentation | PASS (synthetic response) | Failure-only presentation showed `— Timeout`; not a server fault-injection test |

### v1.1 Test Run History

#### ATR-RUN-001 — CC-012 service, module and browser checks

| Field | Value |
|---|---|
| Date | 2026-10-08 |
| Code baseline | CC-012 v1.1 working tree after its approved freeze |
| Environment | Odoo 18, `odoo18ce`, Chromium shared browser |
| Scope | Unit/permission tests, module tests, targeted Workspace/API browser scenarios |
| Result | PASS for listed executed checks; overall CC-012 remains PARTIAL |
| Evidence | Odoo shell output (13/13); Odoo module stats (8 tests); browser observations listed above |

### Not Run / Remaining

- Real ORM fault injection for per-Resource `TIMEOUT` and execution failure; the UI failure state was exercised with a synthetic browser response only.
- Multi-user, multi-company and permission-context isolation integration runs.
- Published Configuration version transition in a live browser.
- Firefox/Safari/Edge Desktop/Narrow matrix.
- Count P95 ≤500 ms, refresh P95 ≤1 s and formal performance sampling.
- Human HVR. Automated browser checks are not HVR evidence.

Conclusion: CC-012 v1.1 implementation checks are substantially covered, but the full
31-test matrix and HVR/performance gates are not closed. Do not report complete DoD.
