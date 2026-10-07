# IHR-GS-UPGRADE-STRATEGY

## 状态

CC-010 已批准冻结并进入实施。

## 实施记录

- 增加 Published 配置升级前置校验；
- 校验 snapshot JSON、版本号和 SHA-256 checksum；
- 校验失败显式抛出 `ValidationError`，不修改 Published 配置；
- 迁移成功写入 `wd.gs.audit.event` 的 `upgrade` 事件；
- 增加 Odoo 标准 `18.0.1.1.0/post-migrate.py` 入口；
- 增加升级前置校验测试。

本阶段不执行破坏性索引删除或直接数据库写入；物理索引迁移待后续具备索引模型后按 CC-010 故障演练执行。
