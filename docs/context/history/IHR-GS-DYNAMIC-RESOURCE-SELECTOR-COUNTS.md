# IHR-GS-DYNAMIC-RESOURCE-SELECTOR-COUNTS

## 状态

CC-012 v1.1 FROZEN；v1.1 implementation is complete, automated checks pass, HVR remains pending.

## Current Snapshot — CC-012 v1.1

- Facet Count is separate from selected-result counts; `resource_counts` covers every current authorized candidate, while `counts` covers only selected Resources.
- Empty `resources[]` is a no-results scope and runs count-only Facets; it never expands to all results.
- Selector initializes the first Query with all current authorized stable keys, then hides successful zero-count Resources and removes them from selection.
- Runtime failures remain visible with unknown/error status; they are not converted to zero.
- CC-012 v1.1 changed implementation status only; SRS/TDD and CC-003 permission semantics are unchanged.
- IHR v1.1 entry set: IHR-001~005 below; final browser/user verification remains open.

## CC-012 v1.0 Historical Implementation

## 实施范围

CC-012 已接入 Published Configuration 驱动的 Resource Descriptor、多选
Resource Selector、权限安全的 Resource Count，以及未知 Resource key 的拒绝。

## 关键实现

- Workspace 从当前 Published Snapshot 读取 Resource，而不是使用静态模型列表；
- Workspace 先经过 `authorize_resource`，无读权限的 Resource 不显示；
- 前端使用 `Set` 维护多选 Resource，空集合表示全部授权 Resource；
- Search 请求使用同一 Published Resource key；
- Facade 拒绝不属于当前 Published Snapshot 的未知 key；
- Executor 在 Permission Boundary 后使用 `search_count()` 计算匹配总数；
- Aggregator 将成功 Resource count 写入 `counts.by_resource`，失败 Resource 不伪造 count；
- Workspace 显示 `label + count`，并在 Query、Resource 或 Refinement 变化后刷新；
- JS cache version 更新为 `cc012`，避免浏览器继续使用旧 Selector 代码。

## 验证

通过：

```bash
./venv/bin/python -m compileall -q mymodules/wd_global_search
node --check mymodules/wd_global_search/static/src/js/preview.js
git diff --check
```

浏览器验证通过：

- Published Configuration 自动显示 Warehouse、Storage Location、Product、
  Contact、Stock Transfer、Sales Order、Purchase Order；
- `GS-CUSTOMER-001` 返回 Contact `1`、Stock Transfer `20`、Sales Order `20`；
- Contact 与 Sales Order 可同时选中；
- 多选后结果按 Resource scope 过滤；
- Count 从 `—` 更新为真实匹配数量。

## 当前限制

- 当前仅完成 Chromium 浏览器验证；
- Firefox、Safari、Edge 及窄屏矩阵尚未执行；
- Odoo 原生 unittest 直接导入方式受 Odoo addon import 约束，未作为独立
  `unittest` 命令执行；compileall、JavaScript syntax check 和浏览器 API/UI
  验证已完成；
- Odoo cron 线程仍有环境相关异常，未发现影响本 CC Search Workspace 的证据。

## CC-012 v1.1 Implementation Entries

### IHR-001 — Separating result and facet count scopes

- **Action:** Facade executes selected Resources for Results and count-only execution for unselected authorized candidates; Aggregator returns selected `counts` separately from all-authorized `meta.resource_counts`.
- **Reason:** Enforce self-excluding Facet Counts without expanding the selected Results scope.
- **Files:** `services/facade.py`, `services/aggregator.py`, `controllers/main.py`
- **Contract:** CC12-CHANGE-006; CC12-INV-003/005/006
- **Result:** Completed

### IHR-002 — Making empty Resource scope explicit

- **Action:** An empty `resource_scope` now executes no business-result searches while refreshing authorized Facet Counts; unknown or unauthorized keys fail generically.
- **Reason:** Prevent empty selection from becoming an all-Resource search or disclosing unauthorized keys.
- **Files:** `services/facade.py`, `controllers/main.py`
- **Contract:** CC12-CHANGE-001/002; CC12-INV-008/009/012
- **Result:** Completed

### IHR-003 — Filtering authorized Resource candidates

- **Action:** Added a shared Resource preflight for model read access, readable search fields and configured relation paths; the same candidate filtering supplies page and Search Response Descriptors.
- **Reason:** Keep unauthorized Resources out of Descriptors, Facet Count maps and Resource-level errors.
- **Files:** `services/executor.py`, `services/facade.py`, `controllers/main.py`
- **Contract:** CC12-CHANGE-001/004; CC12-INV-001/002/009/012
- **Result:** Completed

### IHR-004 — Refreshing the multi-select Selector

- **Action:** Selector is hidden before first Search, initializes the first request with all authorized keys, tracks selection independently, removes successful zero-count keys, retains visible failures, and offers an explicit reselect-all action for empty selection.
- **Reason:** Match the frozen initial-selection, zero-count, failure and empty-scope rules.
- **Files:** `controllers/main.py`, `static/src/js/preview.js`, `static/src/css/preview.css`
- **Contract:** CC12-CHANGE-001~005; CC12-INV-004/008/011/013
- **Result:** Completed

### IHR-005 — Preserving Facet status across pagination and partial failure

- **Action:** Aggregation keeps Facet counts independent from page length and reports partial Facet failures even when the selected result scope is empty.
- **Reason:** Preserve failure ≠ empty and exact count semantics.
- **Files:** `services/aggregator.py`, `tests/test_service_core.py`
- **Contract:** CC12-CHANGE-006/007; CC12-INV-005/006/011
- **Result:** Completed
