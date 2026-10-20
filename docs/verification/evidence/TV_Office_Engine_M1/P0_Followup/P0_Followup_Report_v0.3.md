# Office Engine M1 TV P0 补验报告

| 项目 | 内容 |
|---|---|
| 报告编号 | TV-OFFICE-ENGINE-M1-P0-FOLLOWUP |
| 版本 | 0.3 |
| 执行日期 | 2026-10-19（Asia/Shanghai） |
| 基线 | `TV_Office_Engine_M1_Plan.md` V1.0.0 Frozen |
| 上一版 | `P0_Followup_Report_v0.2.md` |
| 当前结论 | P0-A `BLOCKED`；P0-B `PARTIAL`；P0-C 本机队列链路 `PASS`，生产资源预算 `INCONCLUSIVE`；M1 TV 仍为 `Partial` |

## 1. 执行摘要

本版保留 v0.2 的 P0-A、P0-B 证据，只补充 P0-C 的开发环境运行验证。用户指定的 `mymodules/queue/queue_job` 已在现有 `odoo18ce` 数据库中安装，版本 `18.0.3.1.3`。在 threaded Odoo 开发服务中，使用 Odoo ORM 投递了两个只读 `ir.config_parameter.get_param()` 任务；最终配置下第二个任务从创建到完成约 0.049 秒，任务方法执行耗时 0.002916 秒。

本次验证还找到并修复了两个真实配置问题：

1. 原 `addons_path` 未包含 `mymodules/queue`，因此 Odoo 无法发现模块。
2. 试用 `workers=2` 时，当前浏览器直连 8091、没有 websocket 反向代理，日志持续报告 websocket 请求未到 evented port 8072。切回 `workers=0` 后保留直接开发访问；此模式受 OCA 文档支持用于开发验证，但不能作为生产 prefork 运行证据。
3. runner 初始继承 `http_interface=0.0.0.0` 作为回调 host，向 `http://0.0.0.0:8091/queue_job/runjob` 调度时得到 HTTP 502。配置 runner 回调为 `127.0.0.1:8091` 后，挂起任务被重试并成功完成，随后新投递任务也成功。

因此可以确认：**在当前 Odoo 开发环境，安装与配置 `queue_job` 后，基本入队和后台执行链路可工作。** 这不证明 Office 文件转换的耗时、内存、安全隔离或目标生产环境 worker 配置满足预算。同步/异步产品决策仍需真实文件全流程与目标资源限制数据。

## 2. P0 状态汇总

| 项目 | 状态 | 本版判断 |
|---|---|---|
| P0-A 真实 `.docx` 读写 | `BLOCKED` | 未提供脱敏 DOCX 样本，沿用 v0.2。 |
| P0-B 真实 `.xlsx` 公式与格式 | `PARTIAL` | 真实销售管理模板证据详见 v0.2 和 `P0_Xlsx_Results_20261019_RealSample.json`。 |
| P0-C Odoo 资源预算与队列 | 本机队列链路 `PASS`；生产预算 `INCONCLUSIVE` | 本机模块已安装且只读任务执行成功；真实 Office 负载、目标 worker/代理/内存预算及 prefork+websocket 反向代理未验证。 |

## 3. P0-C：queue_job 实际安装与执行

### 3.1 环境和配置

所有数据库操作均使用项目虚拟环境及 `odoo-bin shell -c odoo.conf -d odoo18ce --no-http`，通过 Odoo ORM 执行；未使用独立数据库、直接数据库驱动或 SQL 客户端。

| 项目 | 最终验证环境 |
|---|---|
| Odoo 数据库 | 现有开发库 `odoo18ce` |
| Python | 项目 `venv`，Python 3.11.9 |
| `queue_job` | OCA 18.0，版本 `18.0.3.1.3`，数据库状态 `installed` |
| Python 依赖 | `requests 2.31.0` |
| addons 路径 | 已加入 `mymodules/queue` |
| `server_wide_modules` | `base,web,queue_job` |
| Odoo worker 模式 | `workers=0`（threaded 开发模式） |
| Queue channels | `root:1` |
| Runner 回调 | `127.0.0.1:8091` |
| Odoo 端口 | 8091，验证结束后服务保持运行 |

`odoo.conf` 是本机运行配置，不纳入本次文档提交范围；文档不记录数据库凭据。配置变更前的副本放在权限为仅当前用户可读的系统临时目录。

### 3.2 安装验证

在更新 Odoo 模块清单后，`ir.module.module` 能发现 `queue_job`；通过 `button_immediate_install()` 安装并提交事务。后续新 Odoo shell 会话读取到：

- 模块状态：`installed`
- 模块版本：`18.0.3.1.3`
- `queue.job` 和 `queue.job.channel` 模型均已注册

### 3.3 运行时故障及修复

首次按 OCA prefork 配置试验时，使用 `workers=2`、`server_wide_modules=base,web,queue_job`。当前开发浏览器直接访问 `http://127.0.0.1:8091`，未配置反向代理将 `/websocket` 转发到 evented port 8072；服务日志出现 websocket 绑定错误。因此最终开发验证切回 `workers=0`，避免破坏用户当前直连的 UI 会话。OCA `queue_job` 文档说明 threaded Odoo 可用于开发，但不代表生产运行方式。

切回 threaded 后，队列 runner 已启动，但第一次回调地址继承 `http_interface=0.0.0.0`，日志记录对 `http://0.0.0.0:8091/queue_job/runjob` 的请求返回 502，任务停留在待分派状态。将 `[queue_job]` 的 `host` 和 `port` 明确设置为 `127.0.0.1` 和 `8091`，重启服务后，原任务自动完成。最终配置下新投递的第二个任务也正常完成。

### 3.4 只读任务执行证据

任务只调用 `ir.config_parameter().get_param('web.base.url')`，不读写销售、采购或其他业务记录。测试只新增 queue job 技术记录。

| 证据 | 观察值 |
|---|---|
| 最终配置下测试任务 UUID | `c948845e-f980-4f07-a2ae-dbd6f301926d` |
| 状态 | `done` |
| 方法 | `ir.config_parameter().get_param('web.base.url')` |
| `date_created` | `2026-10-19 10:13:39.662354 UTC` |
| `date_started` | `2026-10-19 10:13:39.708463 UTC` |
| `date_done` | `2026-10-19 10:13:39.711379 UTC` |
| 方法执行时间 | `0.002916 s` |
| 创建到完成 | 约 `0.049 s` |

另一个在第一次回调 host 错误期间入队的相同只读任务，在回调修正并重启后由 runner 重试完成；其第一次失败及恢复过程保留在 `P0_QueueJob_Runtime_20261019.json`。这条证据说明重试/恢复链路，不用来代表正常调度延迟。

### 3.5 P0-C 判定

**本机队列接入和后台执行：`PASS`。生产资源预算和同步/异步最终决策：`INCONCLUSIVE`。**

已验证模块可安装、runner 可启动、可通过当前用户事务创建任务，并能在后台完成无业务副作用的只读任务。仍未验证：

- 真实 `.xlsx` / `.docx` 文件经完整解析、LLM 映射、渲染、回读和附件保存的耗时与峰值 RSS；
- `workers > 1` 下的 queue job 执行、websocket 反向代理路由和真实并发；
- 目标部署的 Worker 时间/内存限制、容器资源、代理超时、并发任务目标；
- LibreOffice 子进程树及任务期间的进程残留。

不能仅凭一个只读配置查询任务得出“Office 生成必须异步”或“同步安全”的结论。若生产采用 Odoo prefork worker，应另行提供/配置 websocket 反向代理并在目标运行拓扑中补验；当前 `workers=0` 仅适用于本机开发 UI。

## 4. 其他日志观察

测试期间 Odoo registry 仍报告未加载模块 `wd_advanced_m2o_record_panel`、`wd_evidence_album`、`wd_qooling_app`。日志还显示 `wd_global_search/__init__.py` 导入其 `tests` 包，触发 Odoo “Importing test framework” 诊断。这些不是本次 queue_job 的安装依赖；本轮未修改或排查这些模块。`workers=2` 试运行阶段的 websocket 错误通过切回 threaded 开发模式消除；最终 runner host 修正后，队列测试任务完成。

## 5. 总体结论与后续

本机 P0-C 队列基础链路已取得真实运行证据，可供 M1 TDD 评估 `queue_job` 作为长任务执行选项；它尚不足以决定生产部署形态。P0-A 未执行、P0-B 仍为 PARTIAL，P0-C 的 Office 负载及生产预算未验证，**M1 TV 继续保持 `Partial`**。

建议后续顺序：

1. 提供真实脱敏 `.docx`，完成 P0-A。
2. 为真实 `.xlsx` 补做目标稳定版 LibreOffice/Office 视觉人工验收，处理 P0-B 中扩展 OOXML 和公式缓存边界。
3. 以真实 Office 转换任务压测同步与 queue_job 路径，采集完整耗时、父子进程 RSS、并发及清理情况。
4. 对生产 prefork 拓扑单独验证 worker 数、`/websocket` 反代、超时及资源限额；不得将本机 `workers=0` 结果外推为生产结论。

本版只补充验证证据，不修改冻结的 SRS、TV Plan，不编写 TDD，也不构成生产环境实施基线。
