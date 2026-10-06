# IHR-GS-OBSERVABILITY-AUDIT

## 实施范围

CC-008 已冻结并进入实施。首轮实现使用 Odoo 原生 Python logger 和服务端 HMAC hash，未引入外部日志、指标或追踪平台。

## 已实现

- `services/observability.py`：
  - Odoo logger；
  - 观测字段白名单；
  - `raw_query_hash` / `conditions_hash`；
  - HMAC-SHA256；
  - `hash_version=v1`；
  - 缺失 secret 时拒绝明文 fallback。
- `tests/test_observability.py`：
  - hash 稳定性和 secret 绑定；
  - canonical conditions；
  - 字段白名单；
  - 结构化日志调用。
- 配置审计继续复用既有 `wd.gs.audit.event` 模型和 ACL。
- Search Service 已接入 `gs.search.completed`、`gs.search.partial`、
  `gs.search.failed`、`gs.search.rate_limited`、`gs.search.cancelled` 和
  `gs.boundary.rejected` Odoo 日志事件。

## 边界

本轮没有创建新的 audit_log 模型，也没有把业务数据、原始 Query、字段值或 SQL 写入日志。

## 待续实施

- 将 Search、Preview、Boundary 事件接入统一 logger；
- 将配置生命周期事件补齐为 CC8 规定的事件名；
- 验证 audit_log 保留周期；
- 完成验收环境采集和浏览器 HVR。

## ATR 结果

Python 编译、Odoo 模块测试、HMAC、字段白名单、Boundary 拒绝、限流和取消事件
均已通过；详细结果见 ATR。
