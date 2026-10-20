# P0 目标 Odoo 资源预算盘点

## 当前可核实信息

| 项目 | 当前开发环境 | 目标环境状态 | 对结论的影响 |
|---|---|---|---|
| Odoo | 本地仓库命令报告 `Odoo Server 18.0` | 目标主机是否同版/同部署方式未确认 | 不能据此认定目标 Worker 配置。 |
| OS | macOS 27.0.1 arm64 | 未提供 | 既有 LibreOffice 测量不能外推到目标 OS。 |
| Python | venv Python 3.11.9 | 未提供 | 需确认目标解释器及虚拟环境。 |
| `openpyxl` | 3.0.9 | 未提供 | 低于 TV Plan 候选 3.1.x；本轮未升级。 |
| `python-docx` | 未安装 | 未提供 | 真实 Word 写入补验无法启动。 |
| LibreOffice | LibreOfficeDev 26.8 Alpha | 未提供；目标稳定版未确认 | Alpha 转换和公式重算不能视为目标证据。 |
| Worker 数量 | `odoo.conf` 无显式 `workers` | 未提供 | 不猜 Odoo 默认行为。 |
| `limit_time_cpu` / `limit_time_real` | `odoo.conf` 无显式配置 | 未提供 | 无请求时间预算，不能判定同步可行性。 |
| `limit_memory_soft` / `limit_memory_hard` | `odoo.conf` 无显式配置 | 未提供 | 无 Worker 内存预算，不能判断 OOM 风险。 |
| 容器/主机内存限制 | 本机物理内存 16 GiB，盘点时可用约 3.51 GiB | 未提供 | 本机物理内存不是 Odoo 服务配额。 |
| 反向代理超时 | 未验证 | 未提供 | 可能成为实际请求时限，需提供配置值或测量依据。 |
| `queue_job` / 独立队列 | 未验证 | 未提供 | 不决定队列产品或必要性。 |
| 完整 Python + LibreOffice 进程树峰值 RSS | 当前沙箱不能完整枚举系统进程；上一轮证据只记录可见启动 PID | 未提供 | 真实任务总内存仍未知。 |

## 现有性能证据的适用边界

上一轮合成 50,000 行、3 列 `.xlsx` 的完整加载/修改/保存/回读中位耗时为 1.924 秒；可见 Python 启动 PID 峰值约 123–130 MiB。它来自 macOS 开发环境、`openpyxl 3.0.9` 和合成工作簿，且不含完整进程树 RSS。它不能证明真实文件在目标 Odoo Worker 中能同步完成，也不能证明内存安全。

上一轮 9.73 MB `.docx` 仅做 ZIP/XML 检查和一次 LibreOffice PDF 转换，没有 `python-docx` 读写。该数据不能用于真实 Word 的 Worker 时间/内存预算。原有 LibreOffice 并发测试同样未能审计全部进程后代。

## 需要补齐的目标预算数据

请提供或安排在目标测试机只读采集以下非敏感项目：

1. OS/架构、Python 版本和实际 Odoo 虚拟环境路径。
2. `openpyxl`、`python-docx`、`lxml` 版本；LibreOffice 稳定版版本与 `soffice` 路径。
3. Odoo 版本/部署方式、HTTP Worker 数量、`limit_time_cpu`、`limit_time_real`、`limit_memory_soft`、`limit_memory_hard`。
4. 容器/虚拟机/主机实际内存限额、CPU 配额及预期同时处理的文件数。
5. Nginx/反向代理/负载均衡器的请求超时；异步任务队列或 `queue_job` 是否部署。
6. 测试主机是否允许安全采集 Python 与 LibreOffice 子进程树峰值 RSS、PID/PPID、挂起/超时和任务后孤儿进程。

不要提供数据库密码、API key、会话 token 或其他秘密。只需提交上述配置项的值及其来源（Odoo 配置、服务管理器、容器限制或代理配置）。

## 当前决策

**同步/异步：`INCONCLUSIVE`。`queue_job` 必要性：`INCONCLUSIVE`。** 目标超时、Worker 内存限制、真实样本执行时间和整个进程树 RSS 均未齐备。不得据当前证据承诺同步安全，也不得断言必须使用特定队列。
