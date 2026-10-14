# IHR-GS-CC017-1-STRUCTURED-RESULT-CARD

## 0. 治理与基线

| 项 | 内容 |
|---|---|
| Intent ID | `GS-SEARCH-STRUCTURED-RESULT-CARD-TEMPLATE-OUTPUT` |
| Coding Contract | [CC-017-1](../intent/CC-017-1_structured_result_card_template_output.md) v1.0.1 APPROVED / FROZEN |
| 模块 | `wd_global_search` |
| 工作类型 | 新功能 |
| 实施负责人 | Copilot assistant |
| 日期 | 2026-10-14 |
| Branch / Base | `main` / `bb6d3d9`；本次实施尚未提交 |
| 当前状态 | 实现代码已落地；7 个 Resource 已配置结构化模板；Chromium 实际搜索验证完成；浏览器矩阵及人工 HVR 仍未闭环 |

## 1. 当前实施状态

| 项 | 状态 |
|---|---|
| 结构化模板配置与 Publish 校验 | 已实现 |
| `snapshot.card` 与当前用户明细过滤/截断 | 已实现 |
| 前端语义 DOM、schema 安全提示 | 已实现；Chromium 已观察结构化 DOM，完整自动化与多引擎验证未执行 |
| 旧 `rendered_text` / `fields` 兼容 | 已实现并有服务端回归 |
| 配置界面 | 已隐藏旧 Result Card Template 页，提供结构化配置说明；legacy runtime 兼容保留 |
| Stop Conditions | 未触发 |
| 部署数据库状态 | `odoo18ce` Published version 5；7 个 Resource 均为结构化模式；checksum `1f6249ccec0415a47b5454d0ee76d3e66062dff38ffea13c88a6fae3f76c6815` |
| 偏离 | 无；legacy 模板保留为后端兼容路径，不再作为管理员日常配置入口 |

## 2. Coding Contract 基线

执行范围、接口、不变量、测试及验收以 CC-017-1 v1.0.1 §§3–15 为准；没有修改 SRS、TDD、CC-014、CC-014-1 或 CC-017。

## 3. 实施历史条目

### IHR-001

| 字段 | 内容 |
|---|---|
| 时间 | 2026-10-14 |
| 阶段 | Implementation |
| Action | 为 Business Resource 增加结构化模板区域字段；Publish 校验 schema、区域、loop、复合 Resource model mapping 和合计预算；随既有 Snapshot 生命周期输出显式结构对象。 |
| Reason | 落实 CC17-1-DEC-001、002、005。 |
| Files / Components | `models/configuration.py`、`views/configuration_views.xml`、`services/template.py` |
| Contract Reference | CC17-1-INV-004、005；TEST-001、006、007、012、018 |
| Result | Completed |
| Deviation | None |
| Follow-up | 真实多模型 structured Publish 案例仍需补充验收证据。 |

### IHR-002

| 字段 | 内容 |
|---|---|
| 时间 | 2026-10-14 |
| 阶段 | Implementation |
| Action | 增加结构区域渲染、独立 `snapshot.card`、最多三条可读明细及按当前用户可见明细判断的截断标记；扩展 executor deadline 检查。 |
| Reason | 落实结构化响应与当前用户权限边界，不从纯文本推断。 |
| Files / Components | `services/card.py`、`services/template.py`、`services/executor.py` |
| Contract Reference | CC17-1-INV-006、010–014、017；TEST-002、003、009、013 |
| Result | Completed |
| Deviation | None |
| Follow-up | 跨公司权限用例待补充。 |

### IHR-003

| 字段 | 内容 |
|---|---|
| 时间 | 2026-10-14 |
| 阶段 | Implementation |
| Action | 添加结构语义节点、纯文本写入和未知/malformed schema 卡片级提示；增加结构卡片相关 CSS 规则，复用 CC-017 字号/颜色层级。 |
| Reason | 落实前端声明式区域渲染并保留卡片身份/导航。 |
| Files / Components | `static/src/js/preview.js`、`static/src/css/preview.css` |
| Contract Reference | CC17-1-INV-002、007–009；TEST-014、017、021、022 |
| Result | Partial |
| Deviation | None |
| Follow-up | 自动浏览器矩阵与人工 HVR 尚未执行/签署。 |

### IHR-004

| 字段 | 内容 |
|---|---|
| 时间 | 2026-10-14 |
| 阶段 | Implementation |
| Action | 增加结构卡片发布、渲染、截断、权限过滤、预算、schema 和 legacy payload 回归测试，并注册 Odoo 测试模块。 |
| Reason | 为新增接口和兼容模式建立可执行证据。 |
| Files / Components | `tests/test_structured_card.py`、`tests/test_backward_compatibility.py`、`tests/test_configuration.py`、`tests/test_template.py`、`tests/__init__.py` |
| Contract Reference | CC17-1-TEST-001–020 |
| Result | Partial |
| Deviation | None |
| Follow-up | 见 ATR/HVR：部分跨公司、完整语言、日志及浏览器场景未运行。 |

### IHR-005

| 字段 | 内容 |
|---|---|
| 时间 | 2026-10-14 |
| 阶段 | Documentation Correction |
| Action | 按用户批准将 CC 示例 `sale.order.date_order` 的格式键由 `date` 修正为 `datetime`，发布 CC-017-1 v1.0.1。 |
| Reason | 与既有字段类型/formatter Publish 校验一致；不改变执行行为。 |
| Files / Components | `docs/context/intent/CC-017-1_structured_result_card_template_output.md` |
| Contract Reference | CC17-1-DEC-016 |
| Result | Completed |
| Deviation | Approved documentation erratum |
| Follow-up | None |

### IHR-006

| 字段 | 内容 |
|---|---|
| 时间 | 2026-10-14 |
| 阶段 | Implementation / Shared Environment Restoration |
| Action | 增加经校验的 legacy 模式恢复动作，供临时验收配置安全回滚；补充有效切换与无效模板不得清除结构化配置的回归测试。最新 UI 隐藏该入口及旧模板编辑页，legacy runtime 仍兼容既有快照。 |
| Reason | 临时切换需能经合法配置生命周期回滚；后续用户反馈要求管理员只看到明确的结构化配置入口，避免双模板模式造成困惑。 |
| Files / Components | `models/configuration.py`、`views/configuration_views.xml`、`tests/test_configuration.py` |
| Contract Reference | CC17-1-INV-003、004、010、014；§7 Backward Compatibility |
| Result | Completed；`odoo18ce` 模块测试 103/103 通过；该恢复动作未作为常规 UI 按钮呈现 |
| Deviation | None |
| Follow-up | 浏览器矩阵及人工 HVR 签署仍开放。 |

### IHR-007

| 字段 | 内容 |
|---|---|
| 时间 | 2026-10-14 |
| 阶段 | Configuration UX / Browser Verification |
| Action | 隐藏 Resource 表单中的 Result Card Template 页，新增结构化配置提示；通过 Odoo UI 为 warehouse、storage_location、product、contact、stock_picking、sale_order、purchase_order 配置显式 title/meta/summary/details 模板并 Apply。 |
| Reason | 管理员界面只强调一种推荐路径，减少对模板优先级及有效模式的困惑；不删除 legacy 渲染兼容。 |
| Files / Components | `views/configuration_views.xml`；共享 `odoo18ce` 配置 version 5 |
| Contract Reference | CC17-1-INV-003、004、005；§4、§5、§7 |
| Result | Applied；Published version 5 checksum 为 `1f6249ccec0415a47b5454d0ee76d3e66062dff38ffea13c88a6fae3f76c6815`；7 个 Resource 均通过 Publish/Apply 校验，Chromium 搜索结果有结构化语义节点且无 legacy text 节点。 |
| Deviation | None |
| Follow-up | Firefox/WebKit、恶意文本和人工 HVR 签署仍开放。 |

## 4. 实际变更清单

| 文件 | 动作 | 实际变更 |
|---|---|---|
| `mymodules/wd_global_search/models/configuration.py` | Modified | 结构区域配置、互斥及发布验证、Snapshot、经校验的双向模式切换 |
| `mymodules/wd_global_search/views/configuration_views.xml` | Modified | 隐藏旧模板页；结构化模板配置提示与入口 |
| `mymodules/wd_global_search/services/template.py` | Modified | aggregate validation、details 项渲染与授权观察 |
| `mymodules/wd_global_search/services/card.py` | Modified | 结构化区域字段收集及序列化 |
| `mymodules/wd_global_search/services/executor.py` | Modified | 结构模式选择、安全失败及 `snapshot.card` |
| `mymodules/wd_global_search/static/src/js/preview.js` | Modified | 独立语义 DOM 与 schema mismatch 安全提示 |
| `mymodules/wd_global_search/static/src/css/preview.css` | Modified | 结构节点与冻结视觉层级对齐 |
| `mymodules/wd_global_search/tests/` | Modified / Added | 结构、兼容和生命周期回归测试 |

## 5. 偏离与停止条件

- Stop Conditions：None。
- Deviation：None。
- 不新增架构、依赖、缓存、数据库直连或独立配置生命周期。
- 没有执行数据库直接读写或使用 `sudo()` 绕过业务授权。

## 6. 遗留问题

| ID | 问题 | 级别 | 状态 |
|---|---|---|---|
| OI-001 | 仅完成 Chromium 结构化模式的 agent-assisted 观察；Firefox/WebKit、恶意文本/XSS 场景及人工 HVR 签署未完成。7 个 Resource 当前均为结构化模式。 | Major | Open |
| OI-002 | 示例格式键与 `sale.order.date_order` 字段类型不符 | Minor | Resolved by approved v1.0.1 documentation erratum |

## 7. 移交

已实施代码交由 ATR 验证；浏览器/HVR 尚未闭环。当前记录不声明 CC-017-1 Definition of Done 全部完成，也不作 Merge/Release 判定。
