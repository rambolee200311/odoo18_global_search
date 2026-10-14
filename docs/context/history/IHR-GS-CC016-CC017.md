# IHR-GS-CC016-CC017

## 0. 文档治理

| 项 | 内容 |
|---|---|
| Intent | CC-016 Condition Builder and Visualization; CC-017 UI Layout Optimization subgoal |
| CC 基线 | [CC-016 v0.2 FROZEN](../intent/CC-016_condition_builder_visualization.md); [CC-017 v0.4 FROZEN](../intent/CC-017_ui_layout_optimization.md) |
| 模块 | `wd_global_search` |
| 当前状态 | 实施范围已完成；CC-016/CC-017 严格 Closure 证据仍有缺口 |
| 实施基线 | `main @ 2a360d0` |
| 记录日期 | 2026-10-14 |
| 记录方式 | 根据实际变更和已执行验证整理；不将回忆或用户总体确认扩写为未观察的事实 |

本记录与实现同步整理，仅描述实现事实，不宣布 Coding Contract 满足或关闭。

## 1. 实施范围

- **CC-016：** 为既有 Raw Query 增加关键词 chip 的编辑/删除/添加交互；提供遵守 Published field/operator 约束的结构化条件构建与分区展示；服务端进一步按终端字段类型校验条件值。
- **CC-017：** 统一 Workspace 字体、字号层级、颜色、留白、卡片边框和分页视觉；按冻结顺序排列 Workspace 区域；以原生 `<details>/<summary>` 使 Search by field、Date and state filters、Query Understanding 默认收缩且可展开。
- **未实施：** 从 `snapshot.rendered_text` 推断卡片标题、Label/Value 或明细语义；未增加 Search API、搜索语义、外部依赖、数据库/schema 变更或权限旁路。

## 2. 实施历史

| Entry | 实际实施事实 | 影响范围 / 证据 |
|---|---|---|
| IHR-001 | 在 `services/facade.py` 增加结构化条件值与 Published 终端字段类型之间的校验；非法类型失败关闭。 | `facade.py`; `test_service_core.py`; `test_cc015_contract.py` |
| IHR-002 | 接入 CC-016 搜索 Workspace 的关键词 chip、字段选择、结构化条件和 Query Understanding 分区交互，保持既有 Search API 请求边界。 | `static/src/js/preview.js`; CC-016 §14.1 |
| IHR-003 | 调整 CC-017 Workspace HTML 区域顺序，以原生 disclosure 实现三个默认收缩区，并更新 CSS 静态资源版本令牌。 | `controllers/main.py`; `preview.css` |
| IHR-004 | 实施字号层级、统一字体栈、颜色、间距、无卡片边框/阴影及分页外观。 | `preview.css`; CC-017 §§3–12 |
| IHR-005 | 检查结果卡片响应后确认 template-based 卡片仅提供 `snapshot.rendered_text`。依 CC-017 §17 停止语义拆分；未按分隔符或标签文本猜测字段。 | CC-017-UI-TEST-002/003/004；当前 response shape |

## 3. 实际变更清单

| 文件 | 变更关系 |
|---|---|
| `mymodules/wd_global_search/controllers/main.py` | Workspace DOM 顺序、原生 disclosure 和 CSS 资源版本 |
| `mymodules/wd_global_search/services/facade.py` | 结构化条件值类型校验 |
| `mymodules/wd_global_search/static/src/css/preview.css` | CC-017 视觉层级、布局和分页样式 |
| `mymodules/wd_global_search/static/src/js/preview.js` | CC-016 条件构建器与交互 |
| `mymodules/wd_global_search/tests/test_cc015_contract.py` | 终端字段类型校验的 ORM 回归 |
| `mymodules/wd_global_search/tests/test_service_core.py` | 条件值类型校验回归 |
| `docs/context/intent/CC-017_ui_layout_optimization.md` | 冻结的 CC-017 UI 子目标基线 |

未修改 CC-015/CC-016 冻结语义、SRS、TDD、`services/` 之外的搜索执行逻辑、models、Published schema、官方 Odoo 代码或业务数据。

## 4. 偏差、停止与开放项

| 项 | 事实 | 状态 |
|---|---|---|
| CC-017 卡片结构 | `rendered_text` 是单一文本；稳定字段节点不可用。依 §17 停止，没有越界读取或猜测。 | OPEN / BLOCKING |
| CC-017 Query Understanding Count | 当前只完成轻量视觉样式和结果区前位置；“About X results”响应 Count 未实现。 | OPEN / BLOCKING |
| CC-017 分页交互 | 当前两条结果不足以呈现分页按钮，未执行翻页与页大小交互验证。 | OPEN / NOT RUN |
| 浏览器矩阵 | 观察覆盖 Chromium 的指定宽度，不含 Firefox、Safari、Edge 全矩阵。 | OPEN / NOT RUN |
| CC-016 HVR 细项 | 用户总体确认 HVR 通过，但没有逐项步骤、观察、请求结果及 Published checksum 记录。 | OPEN / EVIDENCE GAP |

用户批准以带例外的方式整理并提交本轮成果；此批准被记录为处置指示，不替代冻结 CC 的验收义务或证据。

## 5. 交接

代码实施符合 UI/搜索语义边界；严格 Contract Closure 由 FR 依据本 IHR、ATR、HVR 和冻结 CC 分别判断。所有未完成项不得标记为 PASS。
