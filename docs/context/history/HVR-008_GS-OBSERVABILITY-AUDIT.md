# HVR-008 GS Observability and Audit

## 状态

PARTIAL — 已使用 Playwright 完成搜索、Query Understanding、结果、只读 Preview、
Request Boundary、部分成功、限流和取消状态模拟；成功、Boundary 和限流日志事件
已在临时 INFO 运行参数下观测。配置 audit_log 的完整生命周期仍待独立注入。

## 计划场景

1. 人工执行成功搜索，检查 Odoo 日志包含 `gs.search.completed`；
2. 人工触发部分成功，检查 `gs.search.partial`；
3. 人工触发失败、取消和限流，检查对应事件；
4. 人工打开 Preview 并触发安全失败，检查 `gs.preview.failed`；
5. 人工触发 Request Boundary 拒绝，检查 `gs.boundary.rejected`；
6. 配置发布、拒绝、停用和缓存失效后检查 `wd.gs.audit.event`；
7. 检查日志无原始 Query、条件值、字段值、SQL、Record Rule 和 token；
8. 检查相同输入的 hash 稳定；
9. 检查桌面和窄屏浏览器无观测相关前端错误。

## 已执行结果（2026-10-06）

- 搜索 `Acme`：通过，显示 `Acme Corporation`；
- Query Understanding：通过，显示 `name=Acme`；
- 结果联动 Preview：通过，显示只读 Form View；
- Odoo 日志文件可读，未发现禁止的明文字段键；
- 日志事件计数为 0，原因是当前配置 `log_level = error` 抑制了 INFO/WARNING
  观测事件，因此不能据此宣称日志事件已完成人工验收。

## 临时 INFO 验证（2026-10-06）

- `gs.search.completed`：1；
- `gs.boundary.rejected`：1；
- 禁止明文字段键：0；
- Playwright 超长 Query：`INVALID_REQUEST`；
- 超长 Query 未出现在响应中。
- Playwright 真实限流：65 个请求中 18 个返回 `RATE_LIMITED`；
- Odoo 日志 `gs.search.rate_limited`：18；
- Playwright 部分成功：显示 `Some resources are unavailable.`；
- Playwright 取消状态：显示 `CANCELLED`。

本次仅通过启动参数临时使用 INFO，不修改 `odoo.conf`。

## 浏览器矩阵

| 浏览器 | 桌面 | 窄屏 | 状态 |
|---|---|---|---|
| Chrome | 待验证 | 待验证 | PENDING |
| Firefox | 待验证 | 待验证 | PENDING |
| Safari | 待验证 | 待验证 | PENDING |
| Edge | 待验证 | 待验证 | PENDING |
