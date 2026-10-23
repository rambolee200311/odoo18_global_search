# IHR-M2-005-DYNAMIC-ROWS：动态列表映射实施记录

| 项目 | 值 |
|---|---|
| CC | `CC-M2-005` 动态列表映射 V1.0.0 |
| 日期 | 2026-10-23 |
| Addon | `office_engine_m2`，版本 `18.0.6.0.0` |
| Odoo / Python | Odoo 18.0 / Python 3.11.9 |
| 数据库 | `odoo.conf` 指向既有 `odoo18ce`；未创建隔离库 |
| Provider | 全部自动化使用 Mock；未调用真实 API |

## 实施内容

1. `mapping_service.py` 增加服务端拥有的有界 `mapping_groups` 校验、稳定行槽位校验及 `mapping_rows[]` / `mapping_groups[]` 卡片上下文。明细样例经当前用户 Retriever 授权读取；每组最多 50 行。
2. `ai_orchestrator.py` Prompt 明确支持单值与列表循环识别，但模型只能引用服务端提供的具体目标 ID 和字段 ID。因现有 Retriever 不接受 `in` 列表 domain，服务端从关系记录集取得顺序和 ID，再对每个服务端 ID 使用固定 `id = N`、`limit = 1` 查询；记录数、返回 ID 或字段授权不一致时停止，不调用 M1。
3. `render_bridge.py` 对已确认映射重新校验授权，并按服务端行槽位把明细值展开为 M1 V1 的显式 `set_value` writes；不修改 M1 API。
4. Owl 卡片使用 `t-foreach` 逐行渲染下拉框，按 `row_id` 维护各行选择，并显示服务端生成的循环摘要。保留旧 scalar 卡片上下文兼容。
5. Addon manifest 版本提升至 `18.0.6.0.0`。

## 变更范围

实现仅修改 `office_engine_m2` Addon、自有 CC 文档及 M2-005 实施/验收记录。没有修改 Odoo 官方源码、`office_core`、`office_verify`、`office_engine_odoo` 或 Provider；没有新增依赖。
