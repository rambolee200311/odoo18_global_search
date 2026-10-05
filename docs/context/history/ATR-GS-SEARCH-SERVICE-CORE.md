# ATR GS-SEARCH-SERVICE-CORE

## 0. 文档治理

| 项 | 内容 |
|---|---|
| ATR 文档 | `ATR-GS-SEARCH-SERVICE-CORE.md` |
| Intent ID | `GS-SEARCH-SERVICE-CORE` |
| IHR 文档 | [IHR-GS-SEARCH-SERVICE-CORE](./IHR-GS-SEARCH-SERVICE-CORE.md) |
| CC Version | CC-002 v0.2 FROZEN |
| Module | `wd_global_search` |
| Environment | macOS，Python 3.11，Odoo 18，数据库 `odoo18ce` |
| Test Framework | Odoo `--test-enable`；Python `compileall`；`git diff --check` |
| Code Baseline | 未提交工作区，当前 CC-002 实施切片 |
| Execution Start | 2026-10-04 19:25 |
| Execution End | 2026-10-04 21:41 |
| Executed By | Copilot Agent |

## 1. Test Contract Baseline

| 来源 | 验证点 |
|---|---|
| CC-TEST-004 | 条件合并 |
| CC-TEST-005 | 去重、稳定排序和 cursor 相关核心逻辑 |
| CC-TEST-007 | 限制器核心行为 |
| CC-TEST-001~003、006、008~010 | 本次尚未形成完整自动化执行证据 |
| CC-PRESERVE-002 | 既有 Preview 路由和只读行为回归，尚未单独执行 |

## 2. 当前自动化测试状态

| 指标 | 值 |
|---|---:|
| Required Automated Tests | 10 |
| PASS | 4 个核心纯单元测试 |
| FAIL | 0 |
| SKIPPED | 0 |
| BLOCKED | 0 |
| NOT RUN | 10 项契约级测试尚未全部执行 |
| Latest Valid Run | ATR-RUN-001 |
| Current Code Baseline | 未提交工作区 |
| Evidence Baseline Match | Yes（仅限本次执行切片） |

## 3. Core Test Contract Coverage

| CC Test | Automated Test / Scope | Run | Result | Evidence |
|---|---|---|---|---|
| CC-TEST-004 | `TestSearchServiceCore.test_conditions_merge_uses_distinct_dimensions_and_drops_invalid_values` | ATR-RUN-001 | PASS | Odoo test run |
| CC-TEST-005 | `test_aggregator_deduplicates_after_stable_sort`、cursor 核心断言 | ATR-RUN-001 | PASS | Odoo test run |
| CC-TEST-007 | `test_limiter_releases_user_capacity` | ATR-RUN-001 | PASS | Odoo test run |
| CC-TEST-001~003 | Facade/Provider 集成 | — | NOT RUN | — |
| CC-TEST-006 | 真实超时和总请求预算 | — | NOT RUN | — |
| CC-TEST-008 | 完整错误协议回归 | — | NOT RUN | — |
| CC-TEST-009 | Preview/安装回归 | — | NOT RUN | — |
| CC-TEST-010 | 完整 cursor 跨用户/跨版本/过期集成 | — | NOT RUN | — |

## 4. Test Run History

### ATR-RUN-001

| 字段 | 内容 |
|---|---|
| Timestamp | 2026-10-04 19:30–19:35 |
| Code Baseline | 未提交工作区 |
| Environment | Odoo 18 / `odoo18ce` / macOS |
| Invocation | `python -m compileall -q ...`；`git diff --check`；`odoo-bin -c odoo.conf --http-port=8092 -d odoo18ce -u wd_global_search --test-enable --stop-after-init --log-level=test` |
| Scope | CC-002 当前 Search Service 核心切片、模块加载和已接入测试 |
| Expected Tests | Odoo 模块测试及 4 个核心单元测试 |
| Executed | Odoo 命令 exit code 0；编译和 diff check exit code 0 |
| PASS / FAIL / SKIPPED / BLOCKED | 4 / 0 / 0 / 0 |
| Result | PARTIAL |
| Evidence | 本地命令退出码和测试日志 |
| Follow-up | 由 IHR-003 追踪；继续补齐 CC-TEST-001~003、006、008~010 |

### ATR-RUN-002

| 字段 | 内容 |
|---|---|
| Timestamp | 2026-10-04 21:41 |
| Code Baseline | 未提交工作区，含 cursor/limiter/pagination 修正 |
| Environment | Odoo 18 / `odoo18ce` / macOS |
| Invocation | `odoo-bin -c odoo.conf --http-port=8092 -d odoo18ce -u wd_global_search --test-enable --stop-after-init --log-level=test`；`python -m compileall`；`git diff --check` |
| Scope | 模块加载、既有测试发现、最新服务代码编译 |
| Executed | Odoo 命令 exit code 0；compileall exit code 0；diff check exit code 0 |
| PASS / FAIL / SKIPPED / BLOCKED | 4 core unit tests / 0 / 0 / 0 |
| Result | PARTIAL |
| Evidence | 本地命令退出码和测试日志 |
| Follow-up | 增加 facade/provider/cursor API 集成测试，不将浏览器 HVR 观察计入 ATR 自动化 PASS |

## 5. Regression Verification

| CC-PRESERVE | 回归测试 | Run | Result |
|---|---|---|---|
| CC-PRESERVE-001 | CC-001 配置模型既有测试随模块测试执行 | ATR-RUN-001 | PASS（模块测试范围内） |
| CC-PRESERVE-002 | 既有 Preview 路由/只读浏览器回归 | — | NOT RUN |
| CC-PRESERVE-003 | 模块安装/升级加载 | ATR-RUN-001 | PASS |
| CC-PRESERVE-004 | Preview 错误响应保持不变 | — | NOT RUN |
| CC-PRESERVE-005 | 普通用户配置模型菜单隔离 | — | NOT RUN |

## 6. Issues

| ID | 类型 | 状态 | 说明 | Follow-up |
|---|---|---|---|---|
| ATR-ISSUE-001 | NOT RUN | Open | CC-002 10 项契约测试尚未全部覆盖 | 后续 ATR Run |
| ATR-ISSUE-002 | Scope gap | Open | 真实超时、队列和速率窗口尚未实现/验证 | IHR 后续 Entry |

## 7. Handoff Summary

- 当前 ATR 只证明 CC-002 初始实现切片可编译、模块可升级、4 个核心纯单元测试通过；
- 不证明 CC-002 全部完成；
- 未执行项目明确保持 `NOT RUN`；
- 后续需要继续实施并追加 `ATR-RUN-002`，不能覆盖或删除 `ATR-RUN-001`。
