# ATR-GS-P0-CONCURRENCY-MODE

## 0. 执行元数据

| 项 | 内容 |
|---|---|
| 修复 | P0-03 in-process limiter/request/cancellation state |
| 基线 | `main @ 878a2f7` + 本次工作树 |
| 环境 | macOS；Odoo 18 CE |
| 日期 | 2026-10-14 |
| 执行者 | Copilot assistant |

## 1. 自动化验证

| 验证项 | 结果 | 覆盖 |
|---|---|---|
| `test_service_core` | **39/39 PASS** | limiter 释放和同进程线程并发互斥；请求取消仅允许原所有者；限流拒绝不残留 owner；既有 service core 回归 |
| Python 编译 | **PASS** | `services/facade.py`、`tests/test_service_core.py` |
| `git diff --check` | **PASS** | 补丁格式无 whitespace errors |

## 2. 部署模式结论

- **支持：** Odoo 单进程，显式配置 `workers = 0`；该进程内部的并发 HTTP 线程共享 limiter、owner map 和 cancellation set。
- **不支持：** Odoo 多进程 worker (`workers > 0`)；各进程的 limiter 配额和取消状态互不共享，请求可能无法被另一 worker 取消。
- **验证边界：** 通过代码和同进程线程单元测试验证受支持模式；没有启动多 worker Odoo 实例，因为该模式明确不受支持，也没有进行持久化状态或数据库测试。

## 3. 当前结论

P0-03 的部署支持模式已明确，单进程内线程并发、取消所有权及限流拒绝清理的定向验证通过。本文档不是多 worker 兼容保证。
