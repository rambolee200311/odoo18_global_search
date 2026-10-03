# TV-03 NFR-002 数据新鲜度

## 1. TV 标识

| 项 | 值 |
|---|---|
| ID | TV-03 |
| 名称 | NFR-002 数据新鲜度 |
| 版本 | v0.1 |
| 状态 | Executed with configuration gap |
| 负责人 | Odoo 18 Technical Verification 助手 |
| 日期 | 2026-10-03 |

## 2. 背景与动机

验证 SRS NFR-002、AC-044 和 CON-010：业务记录提交成功后，Global Search 是否在最终上限内可见；配置发布后，搜索请求是否无需重启即可使用新配置。

本次 TV 使用 Odoo ORM 作为真实业务提交和读取路径。当前 `mymodules/wd_global_search` 尚无可执行搜索服务或配置模型，因此配置发布/停用只能进行能力预检并明确记录未验证。

## 3. 验证问题

1. 业务记录创建到搜索可见的时间。
2. 业务记录更新到搜索可见的时间。
3. 业务记录删除到搜索不可见的时间。
4. 配置发布到搜索生效的时间。
5. 配置停用到搜索失效的时间。
6. 批量操作时的延迟。
7. 高并发时的延迟。

业务操作的通过标准为 P95 <= 5 秒；配置操作必须无需进程重启即可生效。配置接口不存在时判定为未验证。

## 4. 假设

### 技术

- Odoo ORM `create`、`write`、`unlink` 的成功提交时间是业务事件时间；
- 搜索请求使用新的 ORM cursor/environment，避免仅测量同一事务缓存；
- 当前搜索等价测试使用 `res.partner` 的 ORM domain 查询；
- 不使用 `sudo()`、裸 SQL 或数据库驱动。

### 数据

- 使用独立 TV-01 数据库 `wd_tv_gs01_20261002_100k`；
- 测试记录使用 `TV03-` 标记；
- 每次运行先通过 ORM 清理已有 TV03 fixture。

### 环境

- Odoo 18、Python 3.11、项目 `./venv` 和 `./odoo.conf`；
- 读写通过 ORM；
- 当前自定义 `wd_global_search` 模块没有配置模型或搜索入口。

假设不成立时，结果只能判定为未验证或有条件通过。

## 5. 范围

### In Scope

- 单条 Partner 创建、更新、删除后新 cursor 搜索可见性；
- 100 条批量创建、更新、删除；
- 20 并发读取已提交记录；
- 精确时间戳和 P50/P95/P99；
- 配置模型/服务能力预检。

### Out of Scope

- 修改 `odoo/` 或官方 addons；
- Elasticsearch/OpenSearch/LLM/向量检索；
- 直接数据库读写；
- 伪造 Global Search 配置发布；
- 未实现的异步索引队列。

## 6. 方法

### 单条操作

1. 通过 ORM 创建一条 `res.partner`；
2. `env.cr.commit()`；
3. 使用新 cursor/environment 搜索；
4. 记录 commit 成功到第一次可见的纳秒时间差；
5. 对更新和删除重复执行。

### 批量操作

- 每批 100 条，ORM 批量 create/write/unlink；
- 每批提交后使用新 cursor 搜索；
- 记录全批次可见延迟。

### 高并发

- 提交 20 条记录；
- 使用 20 个独立 ORM cursor 并发执行搜索；
- 记录每个请求的可见延迟和错误。

### 配置预检

- 检查 `wd_global_search` 是否安装；
- 检查 registry 是否存在配置模型、发布/停用方法和可调用搜索入口；
- 不存在时输出 `NOT_VERIFIED` 和阻塞原因。

## 7. 通过标准

| 子问题 | 通过标准 |
|---|---|
| 创建 | 单条和批量可见 P95 <= 5 秒 |
| 更新 | 新值可见 P95 <= 5 秒，旧值不可再命中 |
| 删除 | 删除后不可见 P95 <= 5 秒 |
| 配置发布/停用 | 无重启即可生效/失效 |
| 批量 | 批量全量可见/不可见 P95 <= 5 秒 |
| 高并发 | 错误率 <= 1%，P95 <= 5 秒 |

## 8. 风险与缓解

| 风险 | 缓解 |
|---|---|
| 同一事务缓存造成假阳性 | 每次搜索使用新 cursor/environment |
| 模块不存在 | 记录配置能力未验证，不伪造结论 |
| 测试记录污染 | 使用 TV03 标记，开始/结束均 ORM 清理 |
| 删除测试影响共享数据 | 仅处理 TV03 标记记录和隔离数据库 |

## 9. 产出物

- `PLAN.md`
- `README.md`
- `scripts/run.py`
- `results/freshness_result.json`
- `reports/REPORT.md`

## 10. 参考

- SRS NFR-002、AC-044、AC-045、CON-010；
- `docs/verification/SPIKE_global_search_report.md`；
- TV-01 隔离数据库和 ORM fixture。

## 11. 变更历史

| 版本 | 日期 | 变更 |
|---|---|---|
| v0.1 | 2026-10-03 | 创建 TV-03 计划 |
| v0.2 | 2026-10-03 | 完成业务记录 ORM 新鲜度、批量和并发测量；配置发布/停用标记未验证 |
