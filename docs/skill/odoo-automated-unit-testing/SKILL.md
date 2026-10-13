---
name: odoo-automated-unit-testing
description: 用于设计、编写、运行或排查 Odoo 自定义模块的自动化单元测试与 ORM 测试，并按项目配置执行 RPC/XML-RPC 模块升级验证；浏览器端真实用户流程使用 odoo-e2e-user-simulation。
---

# Odoo 自动化单元测试

## 适用范围

处理 Odoo 自定义模块的纯 Python 单元测试、服务端 / ORM 自动化测试、测试发现与运行，以及获准后的模块升级验证。先选择能直接验证目标行为的最小测试层：

| 测试层 | 用途 | 常用方式 |
|---|---|---|
| 纯 Python 单元测试 | 不依赖 Odoo 环境的纯函数和算法 | `unittest` 或项目已有测试框架 |
| Odoo ORM 测试 | 模型、权限、约束、计算字段、事务内业务流程 | Odoo `TransactionCase` 等测试基类和 Odoo test runner |
| 运行时 ORM 核验 | 通过当前 Odoo Runtime 检查实际模型、数据或权限行为 | 项目虚拟环境中的 `odoo-bin shell` |
| 浏览器 E2E | 跨 UI、OWL/JS、RPC 与服务端的用户旅程 | 使用 `odoo-e2e-user-simulation` 和 Playwright |

不要用 ORM 查询代替用户可见行为验证，也不要用浏览器 E2E 代替适合在低层快速验证的逻辑测试。Mock 只用于隔离单元测试；TDD 指定的关键路径须覆盖真实 ORM / Runtime。

## 项目环境约定

- 默认项目根目录是**主工作区**：`odoo-bin`、`odoo.conf`、`venv/` 位于同一根目录。即使当前位于 worktree，也优先定位主工作区的虚拟环境，不假设 worktree 内有独立 `venv`。
- Python 默认使用 `<主工作区>/venv/bin/python`；不要自行改用系统 Python、其他环境或 `./.venv`。
- `<主工作区>/odoo.conf` 是数据库端口和 Odoo HTTP 端口的配置来源。每次执行前读取 `db_port` 与 `http_port`，通过配置文件连接；不要从历史记录猜端口、硬编码端口或打印配置中的密码 / 密钥。
- 目标数据库优先读取 `odoo.conf` 的 `db_name`。运行会修改数据库的测试或升级前，确认数据库身份、用途和用户授权；不得把生产库当作测试库。

## 测试编写与运行

1. 先检查 TDD / CC 对测试范围、关键路径、权限和升级行为的要求，以及模块现有测试组织方式。
2. 纯逻辑测试使用隔离的 Python 测试；涉及真实 Odoo 模型和环境的测试使用 Odoo 测试基类，不用普通 `unittest.TestCase` 冒充 ORM 测试。
3. 检查模块 `tests/__init__.py` 是否导入新增测试文件、测试标签是否能被目标命令选中。测试文件未被发现时，先检查注册、基类和标签，不能把“命令退出码为 0”单独当作测试通过证据。
4. 正式自动化 ORM 测试使用 Odoo test runner，并明确目标模块、数据库和标签；记录命令、执行数量、结果及日志。示例（将占位符替换成实际值）：

   ```bash
   ./venv/bin/python odoo-bin -c odoo.conf -d <测试数据库> \
     --test-enable --test-tags /<模块技术名> --stop-after-init \
     --http-port=0 --gevent-port=0 -u <模块技术名>
   ```

   这个命令中的 `-u` 用于 test runner 加载目标模块并执行其测试，不代表已完成下文要求的 RPC/XML-RPC 升级验证。运行前确认目标数据库可用于测试；测试 runner 会更新模块和数据库。

5. 按项目约定，对当前 Odoo Runtime 做即时 / 交互式 ORM 测试或核验时，默认使用 Odoo shell 入口：

   ```bash
   ./venv/bin/python odoo-bin shell -c odoo.conf
   ```

   在 shell 中只通过 Odoo ORM、模型方法和事务机制读写；禁止裸 SQL、数据库驱动和直接数据库客户端。需要可重复回归的 ORM 自动化测试时，仍应把用例写入模块测试并通过 Odoo test runner 执行；shell 核验本身不会自动成为自动化回归证据。

6. 若测试有副作用或会写数据，明确记录测试数据范围和清理 / 回滚方式。失败、跳过、阻塞或未执行的测试如实记录，不得汇报为通过。

## ATR 测试记录

项目使用 `odoo-project-workflow` 时，正式自动化测试必须在对应 CC 的 ATR 中记录，不得只把结果写在聊天、CC 或 shell 输出中。进入自动化测试阶段时，按项目模板创建或更新 ATR；每次正式执行（包括失败和重测）追加一个 `ATR-RUN-{NNN}`，记录测试范围、命令、代码基线、执行结果和可复核证据位置。未执行的测试记录为 `NOT RUN` 并写明原因，不得伪造 Run 或 PASS。

使用项目提供的 ATR 模板：[`docs/skill/odoo-project-workflow/references/templates/Coding/ATR模板.md`](../odoo-project-workflow/references/templates/Coding/ATR模板.md)。若项目明确不采用该工作流，则写入该项目指定的测试记录；此时不要生成项目工作流格式的 ATR。

## 模块升级验证：运行中服务器的 RPC/XML-RPC 操作

当任务要求验证模块升级时，使用配置文件所指向的 Odoo 服务和数据库，执行与 Web 客户端“立即升级”操作等价的 `ir.module.module.button_immediate_upgrade` 模型方法调用。Odoo 18 的 XML-RPC Models API 通过 `/xmlrpc/2/object` 的 `execute_kw` 调用模型方法；不要把单独运行 `odoo-bin -u ... --stop-after-init` 当成 RPC / Web 客户端升级证据。[Odoo 18 XML-RPC API](https://www.odoo.com/documentation/18.0/developer/reference/external_api.html)

操作要点：

- 先从 `odoo.conf` 读取 `http_port`、`db_port` 和 `db_name`，确认 RPC 地址指向本项目预期的运行中服务器和目标数据库；不要另造端口或默认连接其他实例。
- 使用已获授权的账号凭据；从安全的运行时输入或环境变量读取，不将密码写入 skill、脚本、日志或命令行回显。
- 通过 XML-RPC 登录，按模块技术名在 `ir.module.module` 中查找唯一模块记录，再对该记录调用 `button_immediate_upgrade`。找不到记录、匹配不唯一、服务器 / 数据库不符或升级失败时停止，不要改用另一数据库或 CLI 升级掩盖问题。
- 升级是数据库变更。未获用户明确授权时，只准备步骤和报告前置条件，不触发升级；不得据此执行删除、清理、回填或其他破坏性数据操作。
- 升级后检查 RPC 调用结果、服务端完整相关日志、模块安装状态 / 版本，并通过新的 ORM shell 会话核验受影响行为。只有这些证据齐全才报告升级验证通过。

## 结果记录

报告至少包含：测试类型和范围、目标模块与数据库、实际运行命令 / RPC 操作、测试发现与通过 / 失败 / 跳过数量、关键日志位置、ORM 或升级后的验证结果，以及未验证项和原因。适用 `odoo-project-workflow` 时，将正式自动化测试证据写入对应 ATR，并在 CC / FR 中引用；只有项目明确不采用该工作流时，才改用项目指定的验证记录。不能用“测试通过”“升级成功”等无证据表述替代结果。

## 与 E2E skill 的边界

遇到需要真实浏览器、Backend Web Client、Portal、OWL 交互、可见 UI 结果、持久化用户流程或 Playwright 的任务时，使用 `odoo-e2e-user-simulation`。需要低层测试和浏览器 E2E 同时覆盖时，分别记录两层范围与证据。
