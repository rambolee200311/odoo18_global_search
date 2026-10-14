# HVR-GS-CC017-1-STRUCTURED-RESULT-CARD

## 0. 验证治理

本记录区分自动化结果、agent-assisted 尝试和用户人工验收。No observation, no PASS；自动化测试不能替代人工 HVR。

## 1. 元数据

| 字段 | 值 |
|---|---|
| Intent | CC-017-1 v1.0.1 APPROVED / FROZEN |
| 实现基线 | `main @ bb6d3d9` + 未提交工作树 |
| 环境 | 本地 Odoo 18 CE；自动测试 DB `odoo18ce` |
| 目标页面 | `http://127.0.0.1:8091/wd_global_search` |
| 浏览器/视口 | Chromium 150.0.7871.250；1440×900、390×844；恢复为 784×856 |
| 页面配置版本 / checksum | Published version 5；7 个 Resource 均为 structured；checksum `1f6249ccec0415a47b5454d0ee76d3e66062dff38ffea13c88a6fae3f76c6815` |
| 人类验证者 | 用户通过本次会话确认 |
| 日期 | 2026-10-14 |

## 2. 当前状态

**USER ACCEPTED / PARTIAL COVERAGE.** 用户于 2026-10-14 确认人工验证通过。在 `127.0.0.1:8091` 的 `odoo18ce` 环境中，Result Card Template 管理页已隐藏，warehouse、storage_location、product、contact、stock_picking、sale_order、purchase_order 均配置为结构化 Result Card。最终 Published version 5 checksum 为 `1f6249ccec0415a47b5454d0ee76d3e66062dff38ffea13c88a6fae3f76c6815`；legacy runtime 兼容仍保留。该人工确认不替代未执行的 Firefox/WebKit、恶意 HTML/script、键盘导航等独立覆盖项。

## 3. 浏览器矩阵

| 引擎 | Viewport | 状态 | 证据 |
|---|---|---|---|
| Chromium | 1440 × 900 | PARTIAL | agent-assisted：7 个 Resource 均已结构化；搜索 `office` 显示 Purchase Order、Sales Order 结构卡片且无横向溢出 |
| Chromium | 390 × 844 | PARTIAL | agent-assisted：此前 Sales Order 结构化样例 document width 375px、卡片宽 317px，无横向溢出；未对全部七类重复窄屏验证 |
| Firefox | 1440 × 900 | NOT RUN | 无浏览器运行证据 |
| Firefox | 390 × 844 | NOT RUN | 无浏览器运行证据 |
| WebKit | 1440 × 900 | NOT RUN | 无浏览器运行证据 |
| WebKit | 390 × 844 | NOT RUN | 无浏览器运行证据 |

## 4. HVR 场景覆盖

| 场景 | 状态 | 通过标准摘要 |
|---|---|---|
| Workspace 区域顺序、折叠、Resource Selector | PARTIAL | 8091 页面观察到 Search、Resource、Search by field、Date/state、Query Understanding、results；旧模板配置页已隐藏 |
| 独立 title/meta/summary/details DOM | PARTIAL | 七类 Resource 的实际结果均观察到结构化语义节点；仅 Chromium 与本地样例数据 |
| 0/1/3 条明细与第 4 条省略 | PARTIAL | Sales Order 四条以上明细显示前三项及 `...`；Purchase Order 明细也渲染；0/1/3 行边界组合未逐一覆盖 |
| 空区域和空标题 | NOT RUN | 不造默认值/字段名；保留记录导航身份 |
| 恶意 HTML/script 文本 | NOT RUN | 按文字显示，不执行、不双重 escape |
| Legacy `rendered_text` / `fields` | PARTIAL | 后端 legacy runtime 兼容由服务端回归覆盖；当前 Workspace 未渲染 legacy 节点，fields-only 卡片与键盘/点击/双击/新 Tab 未完整验证 |
| Count、分页、筛选、Resource 状态 | PARTIAL | `gemini chair lamp` 的 Sales Order 为 2；`office` 返回 Purchase Order 6、Sales Order 17（共 23，首屏 10）；更多筛选组合未覆盖 |

## 5. Agent-assisted 浏览器观察与自动化边界

1. 已通过 Odoo UI 配置全部七个 Resource：warehouse、storage_location、product、contact、stock_picking、sale_order、purchase_order；旧 Result Card Template 编辑页在管理界面不可见，legacy runtime 兼容保留。
2. Chromium 150.0.7871.250 下逐类结果：Warehouse `NL Company`（1）、Storage Location `WH/Stock`（4）、Product `Office Lamp`（1）、Contact `Gemini Furniture`（1）、Stock Transfer `WH/IN/00001`（1）、Sales Order `gemini chair lamp`（2）、Purchase Order 在 `office` 查询中有结果。每个已检查结果的 legacy `.wd-card-template-text` 节点数为 0。
3. `office` 查询返回 Purchase Order 6 与 Sales Order 17，共 23 条；首屏 10 条均显示结构化标题、Meta、摘要，订单卡片还显示明细摘要和溢出标记。
4. 最终配置 Published version 5 checksum：`1f6249ccec0415a47b5454d0ee76d3e66062dff38ffea13c88a6fae3f76c6815`。`gemini chair lamp` 的 Sales Order Count 保持 2。
5. 1440×900 下无横向溢出；此前 Sales Order 单独样例在 390×844 下 document width 375px、卡片宽 317px，无横向溢出；本次未在窄屏逐个重复七类 Resource。
6. 结构化模式截图曾捕获但未归档为稳定文件；本 HVR 以可复核的 DOM、视口与 Count 观察为证据。未对恶意 HTML/script、Firefox/WebKit 或键盘导航作通过声明。

- 自动化服务端证据：见 [ATR-GS-CC017-1-STRUCTURED-RESULT-CARD](./ATR-GS-CC017-1-STRUCTURED-RESULT-CARD.md)；该 ATR 不代表浏览器 DOM 或 HVR 通过。
- Python/Node 语法检查及 Odoo 103 tests 通过，不替代本记录中的浏览器场景。
- 结构化 mode 截图未归档为稳定文件；当前 structured 配置 checksum 已记录；人类 HVR 仍未签署。

## 6. 人工签署

| 验收人 | 日期 | 结果 | 签署 / 证据引用 |
|---|---|---|---|
| 用户（本次会话确认） | 2026-10-14 | PASS | 用户明确确认“人工验证通过”；范围为当前结构化卡片交付，未执行的跨浏览器与安全场景仍按上表标记 |

**结论：** 用户已通过人工验收。8091 的七个 Resource 均已切换为 structured 并完成 Chromium 观察；完整跨浏览器和专项场景矩阵仍部分开放，不将未执行场景宣称为通过。
