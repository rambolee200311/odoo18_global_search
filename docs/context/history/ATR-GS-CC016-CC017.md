# ATR-GS-CC016-CC017

## 0. 文档治理

| 项 | 内容 |
|---|---|
| Intent | CC-016 Condition Builder and Visualization; CC-017 UI Layout Optimization subgoal |
| CC 基线 | [CC-016 v0.2 FROZEN](../intent/CC-016_condition_builder_visualization.md); [CC-017 v0.4 FROZEN](../intent/CC-017_ui_layout_optimization.md) |
| IHR | [IHR-GS-CC016-CC017.md](./IHR-GS-CC016-CC017.md) |
| 模块 | `wd_global_search` |
| 维护原则 | 仅记录真实运行；No execution, no PASS |

## 1. 执行元数据

| 字段 | 值 |
|---|---|
| 环境 | macOS，本地 Odoo 18 CE 工作区 |
| 测试框架 | Odoo addon namespace unittest、Python 编译、Node.js 语法检查、浏览器观察 |
| 基线 | `main @ 689ae87` 加本次工作树变更；报告中的运行按各自范围区分 |
| 执行日期 | 2026-10-14 |
| 执行者 | Copilot assistant（自动化/浏览器辅助观察） |

## 2. 测试契约基线

- CC-016 §14 的 `CC16-TEST-001~027`、§14.1/14.2 HVR 场景。
- CC-017 §§15–18 的 `CC17-UI-TEST-001~016` 与 Stop Conditions。
- 本 ATR 不缩减测试契约，未明确映射到契约 ID 的测试只证明其实际断言。

## 3. 当前自动化状态

| 验证 | 实际结果 | 基线与范围 |
|---|---|---|
| Search Core 单元测试 | **34/34 PASS** | 本次最终工作树；由 Odoo addon namespace 加载 `test_service_core` |
| Python 编译 | **PASS** | `controllers/main.py`、`services/facade.py` |
| JavaScript 语法 | **PASS** | `node --check static/src/js/preview.js` |
| `git diff --check` | **PASS** | 本次代码工作树 |
| Odoo 模块套件 | **81/81 PASS（历史）** | CC-016 类型校验实施后、CC-017 HTML/CSS/交互最终修改前；不宣称为 CC-017 最终基线的全套回归 |
| CC16-TEST-001~027 全量逐项映射 | **NOT EVIDENCED** | 34 项服务单测不等同于逐项覆盖全部契约测试 |
| CC17-UI-TEST-002/003/004 | **BLOCKED** | 当前 card response 只有 `snapshot.rendered_text`；不得猜测语义 |
| CC17-UI-TEST-005 | **NOT SATISFIED** | 样式/位置有观察；响应 Count 与 “About X results”未实现 |
| CC17-UI-TEST-010 | **NOT RUN** | 两条结果场景没有分页按钮，未验证分页交互 |
| CC17-UI-TEST-013 | **NOT RUN** | 未执行完整浏览器/设备矩阵 |

纯单元测试命令：

```sh
./venv/bin/python -c "import odoo; odoo.tools.config.parse_config(['-c', 'odoo.conf']); import unittest; unittest.main(module='odoo.addons.wd_global_search.tests.test_service_core', argv=['test_service_core'], exit=False)"
```

## 4. 浏览器辅助观察（不是 HVR PASS）

共享授权浏览器的 agent-assisted 观察记录如下；这些记录可用于页面范围核对，但不替代 CC-016 要求的用户逐项 HVR。

| CC-017 测试 | 观察 | 结果 |
|---|---|---|
| UI-TEST-001 | 观测 H1 32px、H2 20px、Query Understanding 14px、摘要 14px、Meta 12px 等已存在角色 | PARTIAL；卡片标题/Label/Value 角色不存在 |
| UI-TEST-002~004 | template-based 卡片只有单一 rendered text | BLOCKED；依 §17 停止 |
| UI-TEST-005 | Query Understanding 位于结果之前，轻量灰色样式；无响应 Count 文案 | NOT SATISFIED |
| UI-TEST-006 | 卡片间距 28px、内部留白 8px；仅对现存节点测量 | PARTIAL |
| UI-TEST-007 | 页面及输入/按钮/选择器/分页相关控件使用统一字体栈 | PASS（已观测元素） |
| UI-TEST-008 | 已观测角色使用目标颜色；缺失的字段 Label/Value 无法测量 | PARTIAL |
| UI-TEST-009 | 结果卡无边框/阴影 | PASS |
| UI-TEST-010 | 两条结果时分页按钮未显示 | NOT RUN |
| UI-TEST-011/012 | `gemini chair lamp` 页面返回 2 条；disclosure 切换未修改查询状态 | PARTIAL；未执行完整 API/错误/权限回归矩阵 |
| UI-TEST-013 | Chromium，1600×1800 与 375px 窄屏无横向溢出 | PARTIAL；Firefox/Safari/Edge 和完整设备矩阵未运行 |
| UI-TEST-014 | Search by field、Date and state filters、Query Understanding 初始收缩；键盘 Enter/Space 可切换 | PASS |
| UI-TEST-015 | 七个 Workspace 区域 DOM 顺序符合冻结要求 | PASS |
| UI-TEST-016 | 仅切换 disclosure 时观察到 0 个 Search API 请求 | PASS |

## 5. Run History

### ATR-RUN-001 — 当前工作树定向验证

| 字段 | 值 |
|---|---|
| 运行日期 | 2026-10-14 |
| 命令/操作 | `test_service_core`（34 tests）、`py_compile`、`node --check`、`git diff --check` |
| 结果 | 34/34 单元测试通过；三项静态检查通过 |
| 能证明 | Search Core 当前单元测试及语法/补丁格式有效 |
| 不能证明 | CC16-TEST 全量满足、数据库集成全量、CC17 结构化卡片、人工 HVR 或浏览器兼容矩阵 |

### ATR-RUN-002 — 既有 Odoo 模块套件（历史基线）

| 字段 | 值 |
|---|---|
| 结果 | 81 tests，0 failures，0 errors |
| 时间关系 | 在 CC-016 类型校验完成后运行，早于 CC-017 最终 HTML/CSS/JS 工作树 |
| 有效性 | 保留为历史证据；不把它扩展为 CC-017 最终基线完整回归 |

## 6. 当前状态与交接

自动化验证对已运行的 34 项服务核心测试为 PASS；全量 CC-016 测试映射未建立。CC-017 存在已知 NOT SATISFIED、BLOCKED 和 NOT RUN 项。严格 Closure 影响由 FR 按冻结契约判定；本 ATR 不宣布完成。
