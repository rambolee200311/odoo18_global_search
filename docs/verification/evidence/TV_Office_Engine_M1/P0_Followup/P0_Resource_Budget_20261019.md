# P0 目标 Odoo 资源预算与 Queue Job 检查

## 本机配置证据

| 项目 | 当前本地配置/实测 | 结论范围 |
|---|---|---|
| Odoo | `Odoo Server 18.0` | 当前仓库/开发环境，不代表独立目标主机。 |
| `addons_path` | `addons,odoo/addons,mymodules,mymodules/odoo-llm` | 没有 `mymodules/queue`。 |
| `queue_job` 模块发现 | Odoo `get_module_path("queue_job")` 返回未发现 | 当前该配置不能定位 `mymodules/queue/queue_job`。本项只做配置解析和模块发现，不连接数据库。 |
| `server_wide_modules` | `base,web` | 未加载 `queue_job`。 |
| 有效 `workers` | `0` | 本机当前有效配置值；不代表目标主机配置。 |
| Odoo 请求超时 | `limit_time_cpu`、`limit_time_real` 未显式配置 | 不推测 Odoo 默认值。 |
| Worker 内存限制 | `limit_memory_soft`、`limit_memory_hard` 未显式配置 | 不推测默认值。 |
| 代理/容器预算 | 未提供/未验证 | 仍缺目标预算。 |

## Queue Job 源码检查

`mymodules/queue/queue_job` 存在，Manifest 版本 `18.0.3.1.3`，外部 Python 依赖 `requests` 已在项目 venv 安装（2.31.0）。源码 README 说明 Jobrunner 将排队任务通过 HTTP 分派给可用 Odoo Worker，并使用独立任务事务。配置文档要求生产场景启用 `queue_job`，并使用大于 1 的 Worker 数量；示例还设置 `server_wide_modules` 和 channels。

当前配置的 `addons_path` 未包含模块直接父目录 `mymodules/queue`，且 `server_wide_modules` 未包含 `queue_job`。因此源码可用不等于本机服务已接入该队列。本轮不查询数据库，不能确认 `queue_job` 是否已安装，也不能确认 Jobrunner 是否在运行。

## 同步/异步判断

**结论仍为 `INCONCLUSIVE`；`queue_job` 是否必须仍未决定。** 当前确认了本地配置存在队列接入缺口，但这不是“文档任务必须异步”的性能证据。判断还需目标主机的请求/Worker 时间和内存限制、代理超时、并发目标，以及真实 `.docx` / `.xlsx` 全流程（含 LibreOffice 子进程树）的耗时与峰值 RSS。

## 目标环境待提供

- 目标主机 OS、Python、`openpyxl`、`python-docx`、`lxml`、LibreOffice 稳定版本与路径。
- Odoo 版本/部署方式、Worker 数、`limit_time_cpu`、`limit_time_real`、`limit_memory_soft`、`limit_memory_hard`。
- 容器/主机 CPU 与内存配额、反向代理超时、预期文件任务并发数。
- `queue_job` 目标 addons 路径、数据库安装状态、`server_wide_modules`、channels 与 Jobrunner 启动日志。请不要提供数据库密码、API key 或会话 token。
- 目标测试环境采集 Python/LibreOffice 完整进程树 RSS 与任务后残留进程的能力。
