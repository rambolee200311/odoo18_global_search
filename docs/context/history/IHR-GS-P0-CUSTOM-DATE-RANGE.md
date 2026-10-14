# IHR-GS-P0-CUSTOM-DATE-RANGE

## 0. 治理与基线

| 项 | 内容 |
|---|---|
| 问题 | P0-01：自定义日期范围被请求边界拒绝；不完整范围可能清除已有日期条件并扩大查询 |
| 适用契约 | SRS FR-RF-003/004、BR-009；CC-005 date Refinement；TDD §3.5 |
| 模块 | `wd_global_search` |
| 开始基线 | `main @ 878a2f7` + 本次工作树 |
| 状态 | 实施完成；agent-assisted 浏览器验证通过，人工 HVR 待签署 |
| 日期 | 2026-10-14 |

未修改 SRS、TDD 或既有 CC；自定义范围仍按 `[start_inclusive, end_exclusive)` 和既有 Business Date 执行路径处理。

## 1. 实施历史

| Entry | 实施事实 | 文件 |
|---|---|---|
| IHR-001 | 请求边界仅允许 `dimension=date`、`operator=between` 使用 `{start,end}` 对象；只接受精确键集合、规范 `YYYY-MM-DD` 日期以及 `end > start`。其它条件仍要求 scalar。 | `services/request_boundary.py` |
| IHR-002 | 日期控件输入不完整或结束日不晚于起始日时，展示可访问错误提示并停止；不移除当前日期 Refinement、不重置分页、不发送 Search API 请求。仅有效范围或明确清空时更新 Refinement。 | `static/src/js/preview.js`; `controllers/main.py`; `static/src/css/preview.css` |
| IHR-003 | 为缓存期内的浏览器载入本次 CSS/JS 更新，分别更新静态资源版本令牌。 | `controllers/main.py` |
| IHR-004 | 增加请求边界合法/非法范围用例，以及日期 Business Date `[start,end)` ORM domain 单元测试。 | `tests/test_request_boundary.py`; `tests/test_service_core.py` |

## 2. 安全与行为边界

- Search API 结构仅新增日期条件的受限值形状，不新增日期语义、接口或查询维度。
- 不完整/非法用户输入不会转成无日期条件的 SearchRequest。
- 执行仍使用既有 executor 的 `_date_bounds` 和 Resource Business Date 配置。
- 未读写数据库、未修改业务数据、未使用 `sudo()` 或引入外部依赖。

## 3. 回滚方案

可单独回滚本问题涉及的 request-boundary 日期分支、日期控件错误处理、测试和对应静态资源版本变更；无需数据迁移或数据库恢复。回滚前需确认不存在依赖 `{start,end}` 日期值的后续修改。
