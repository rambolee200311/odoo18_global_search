# P0-C 本机 Queue Job 运行补充记录

本记录补充 `P0_Resource_Budget_20261019.md` 的静态配置检查，不覆盖其当时“未安装/未运行”的历史结论。

## 已验证

- OCA `queue_job 18.0.3.1.3` 已安装在现有开发库 `odoo18ce`。
- 项目 `venv` 中有 `requests 2.31.0`。
- 最终本机配置：`addons_path` 包含 `mymodules/queue`；`server_wide_modules=base,web,queue_job`；`workers=0`；Queue channels `root:1`；runner 回调 host/port 为 `127.0.0.1:8091`。
- Odoo runner 能执行只读 `ir.config_parameter.get_param('web.base.url')` 队列任务。最终配置下测试任务状态 `done`，方法执行 `0.002916 s`，从任务记录创建到完成约 `0.049 s`。
- 服务在验证完成后仍监听 `8091`。

## 已发现的拓扑边界

试设 `workers=2` 时，直连 8091 的浏览器请求无法经当前拓扑路由到 Odoo evented port 8072，日志产生 websocket 绑定错误。没有配置反向代理，因此本机最终恢复 `workers=0` threaded 开发模式。该模式可验证队列基本行为，但不代表生产 prefork worker 的 websocket、并发、性能或稳定性。

runner 初始使用 `http_interface=0.0.0.0` 作为回调 host，`/queue_job/runjob` 请求返回 502。增加 `[queue_job] host=127.0.0.1` 与 `port=8091` 后，先前待处理任务恢复完成，后续新任务也成功执行。

## 未验证/不作结论

当前只执行了微型只读任务，没有执行 Office 文件解析/转换，也没有测量完整任务峰值 RSS、worker/LibreOffice 进程树、生产负载并发或服务超时预算。因此不能据此决定正式环境必须异步或同步安全。目标部署资源预算仍待提供并在目标拓扑中测量。

详细任务 UUID、UTC 时间戳、配置与限制见 `P0_QueueJob_Runtime_20261019.json`。
