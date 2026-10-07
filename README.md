# WD Global Search

基于 Odoo 18 的只读全局搜索与 Preview 工作区。项目面向 Odoo 内部业务资源，
通过服务端 ORM、当前用户权限和已发布配置快照，提供跨资源搜索、筛选、分页和
只读记录预览。

> 当前发布状态：**CC-011 最终验收实施中（PARTIAL）**
> 当前模块版本：`18.0.1.1.0`

## 功能概览

- 已发布配置驱动的 Business Resource、字段、状态和词汇；
- Raw Query、资源筛选、日期/状态 Refinement；
- 分页、cursor、限流、并发控制和取消请求；
- 当前用户权限边界和多公司/Portal 失败关闭；
- 只读 Form View Preview，不提供编辑、删除、Chatter、附件或活动写入口；
- `EMPTY`、`PARTIAL_SUCCESS`、`CANCELLED`、`RATE_LIMITED` 等稳定错误协议；
- Odoo 原生日志、`wd.gs.audit.event` 审计和 HMAC 脱敏观测；
- 用户语言、时区、日期边界和缺失翻译英文回退；
- 配置 snapshot checksum、升级 preflight 和 Odoo migration 入口。

## 技术边界

项目明确不使用：

- Elasticsearch / OpenSearch；
- LLM、向量检索或外部翻译 API；
- 动态 Python/ORM Domain 执行；
- `sudo()` 绕过业务权限；
- 对 Odoo 核心或官方 addons 的修改；
- 直接读写数据库的业务逻辑。

业务数据查询使用 Odoo ORM，并由服务端 `request.env.user` 决定权限、公司、语言
和时区。客户端请求体中的 `uid`、`company_id`、`groups`、`lang` 和 `tz` 不作为
权限或用户上下文来源。

## 快速开始

在项目根目录执行：

```bash
./venv/bin/python odoo-bin -c odoo.conf \
  -d <数据库名> \
  -i wd_global_search \
  --stop-after-init
```

升级已有模块：

```bash
./venv/bin/python odoo-bin -c odoo.conf \
  -d <数据库名> \
  -u wd_global_search \
  --stop-after-init
```

开发服务器示例：

```bash
./venv/bin/python odoo-bin -c odoo.conf \
  -d <数据库名> \
  --http-port=8091
```

安装后登录 Odoo，进入 Global Search Workspace。配置管理员可在配置菜单维护
Domain、Version、Resource 和 Vocabulary；搜索用户只消费 Published Snapshot。

## 目录结构

```text
mymodules/wd_global_search/
  controllers/       Search、Cancel、Preview 和 Workspace 路由
  models/            配置、Published Snapshot 和 audit event
  services/          facade、provider、条件、聚合、权限、i18n、观测和升级校验
  static/src/        Preview 前端资源
  migrations/        Odoo 模块升级入口
  tests/             Odoo 和服务层自动化测试

mymodules/wd_tv_global_search/
  tv_01_nfr_001_performance/
  tv_02_index_strategy/
  tv_03_freshness/
  tv_04_complex_permissions/
  tv_05_preview_browser/
  tv_06_multi_value_time_failure/

docs/requirement/    SRS
docs/design/         TDD
docs/implementation/实施计划
docs/context/intent/ Coding Contract（CC）
docs/context/history/ IHR、ATR、HVR 验证记录
docs/context/debt/   技术债登记
```

## 关键边界

Search Request Boundary：

- Raw Query 最长 500 字符；
- 条件总数最多 20；
- 条件嵌套深度最多 3；
- Relation Path 最多 2 层；
- `query` 必须为服务端定义的文本类型；非法类型、控制字符及超出结构边界的请求返回 `INVALID_REQUEST`；
- 超限统一返回 `INVALID_REQUEST`，不回显用户输入。

Model、Field、Operator、Domain Structure 和 Permission Context 均由服务端
Published Configuration / UserContext 决定，客户端不得直接指定。用户输入不会直接
转换为可执行 ORM Domain。

错误、日志和审计不得记录原始 Query、完整 conditions、业务字段值、SQL、
Record Rule 或 token。前端以文本方式展示服务端消息，不把消息当作 HTML。

## 验证

编译和差异检查：

```bash
./venv/bin/python -m compileall -q mymodules/wd_global_search
git diff --check
```

Odoo 模块测试：

```bash
./venv/bin/python odoo-bin -c odoo.conf \
  --http-port=8092 \
  -d <数据库名> \
  -u wd_global_search \
  --test-enable \
  --stop-after-init \
  --log-level=test
```

TV-06 回归：

```bash
./venv/bin/python odoo-bin shell -c odoo.conf \
  -d wd_tv_gs01_20261002_100k \
  --no-http \
  < mymodules/wd_tv_global_search/tv_06_multi_value_time_failure/scripts/run.py
```

TV-06 需要确认输出中的 `all_semantic_checks_pass` 为 `true`。该 harness 当前
验证时间、多值条件、边界和部分失败语义；它不等同于生产 Search Service 的完整
错误注入验收。

## 文档和交付状态

主要契约：

- [SRS](docs/requirement/SRS_global_search.md)
- [TDD](docs/design/TDD_global_search.md)
- [实施计划](docs/implementation/IMPLEMENTATION_PLAN_global_search.md)
- [CC-009 国际化与时区](docs/context/intent/CC-009_global_search_i18n_timezone.md)
- [CC-010 升级策略](docs/context/intent/CC-010_global_search_upgrade_strategy.md)
- [CC-011 最终验收](docs/context/intent/CC-011_global_search_final_acceptance.md)
- [TD-001 Search Request Boundary](docs/context/debt/TD-001_search_request_boundary_hardening.md)
- [配置与搜索验证手册](docs/implementation/CC-001_configuration_admin_guide.md)

当前最终验收记录：

- [ATR-GS-FINAL-ACCEPTANCE](docs/context/history/ATR-GS-FINAL-ACCEPTANCE.md)
- [IHR-GS-FINAL-ACCEPTANCE](docs/context/history/IHR-GS-FINAL-ACCEPTANCE.md)
- [HVR-011-GS-FINAL-ACCEPTANCE](docs/context/history/HVR-011_GS-FINAL-ACCEPTANCE.md)

TD-001 已落实并关闭；其边界契约、错误/日志规则和相关测试记录保留在
[TD-001](docs/context/debt/TD-001_search_request_boundary_hardening.md)、
CC-002、CC-007 及对应 ATR 中。

当前已通过编译、Odoo 模块测试和 TV-06 回归。最终发布仍受以下事项阻塞：

- CC-010 隔离数据库备份恢复与回滚演练；
- Firefox、Safari、Edge 桌面/窄屏浏览器矩阵；
- 生产 Search Service 的完整 TV-06 错误注入；
- SRS MUST 逐项签署和发布候选版本确认。

`PARTIAL` 不表示发布通过；未完成项必须在最终验收记录中保持 `PARTIAL`、`BLOCKED`
或 `NOT RUN`。

## Release Gate

当前版本 `18.0.1.1.0` 尚未达到 Final Release。必须全部满足：

- [ ] CC-011 Final Acceptance = `PASS`
- [ ] CC-010 backup / restore / rollback = `PASS`
- [ ] Browser matrix = `PASS`
- [ ] Production Search Service TV-06 error injection = `PASS`
- [ ] SRS MUST traceability = `PASS`
- [ ] Release Candidate confirmation = `APPROVED`

在上述条件全部满足前，`PARTIAL` 不得解释为发布通过。

## 版本与提交

模块版本由 [__manifest__.py](mymodules/wd_global_search/__manifest__.py) 管理。
项目采用按 Coding Contract 分阶段提交的方式，提交应同时包含实现、测试和对应
IHR/ATR/HVR 证据。
