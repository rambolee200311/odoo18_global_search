# Office Engine M1 — Spawn 导入与内存边界调查

| 项 | 记录 |
|---|---|
| 状态 | **调查记录 / Partial；不是冻结 TV Plan 或 PASS 验收** |
| 日期 | 2026-10-22 |
| 范围 | 只读定位 CC-OFFICE-M1-004 spawn 导入失败及目标开发环境内存限制现象 |
| 环境 | 项目 `venv`；Odoo 18；`odoo.conf`；数据库 `odoo18ce`；macOS；Python 3.11 |
| 数据变更 | 无；Odoo shell 仅读取模块导入元数据，未写 ORM 数据 |
| 外部请求 | 无；未调用 Provider |
| 产品代码变更 | 无 |

## TV-001 — Odoo 动态 Addon 命名空间在独立 spawn 进程中的导入性

**Question**  
CC-004 的 `multiprocessing` `spawn` 子进程为何无法重新导入 `office_core` / `office_verify`？是否可在当前运行时按普通 Python 包名导入？

**Method**

1. 按项目纪律运行 `venv/bin/python odoo-bin shell -c odoo.conf -d odoo18ce --no-http`，只检查 Odoo addon 搜索路径、`sys.path`、两个已加载模块的 `__name__` / `__spec__`，以及普通顶层模块的 `find_spec`；不读业务记录、不写数据库。
2. 用项目 `venv` 的临时 Python 探针，在子进程启动前把 `mymodules` 加入 `sys.path`，以 `office_core.service._child_worker` 作为 `spawn` target，观察子进程能否按普通模块名导入目标及数据契约。探针在运行后删除，不进入仓库。

**Result** — `VERIFIED`（限模块导入原因和候选入口可导入性；不证明 Office 处理成功）

- Odoo shell 观察到 addons 路径包含仓库 `mymodules`，但运行时 `sys.path` 不包含 `mymodules`。
- 父进程中两个服务模块名分别为 `odoo.addons.office_core.service` 和 `odoo.addons.office_verify.service`；`importlib.util.find_spec("office_core")` 与 `find_spec("office_verify")` 均为 `None`。
- CC-004 ATR-RUN-004 已记录 `spawn` 子进程反序列化时 `ModuleNotFoundError: No module named 'odoo.addons.office_core'`。本次运行时元数据与该异常一致：Odoo 动态 addon 名称依赖父 Odoo 进程的 addon 加载环境。
- 临时探针通过顶层包名 `office_core.service` 启动 spawn target。子进程完成模块导入并进入 `_child_worker`，随后因 8 GiB `RLIMIT_AS` 无法施加而返回 `OFFICE_RESOURCE_LIMIT`。这只证明顶层包名可被 spawn 导入，不证明候选写入、回读或交付可用。

**Evidence**

- 只读 Odoo shell 输出：`odoo.addons.__path__` 含 `.../mymodules`，`sys.path_mymodules=[]`；两个模块 `__spec__.name` 为 `odoo.addons.*`，顶层 `find_spec` 均为空。
- 临时顶层包探针输出：`target_module=office_core.service`、`child_exitcode=0`、`child_result_kind=office_error`、错误码 `OFFICE_RESOURCE_LIMIT`。探针脚本已删除。
- 既有 [CC-004 ATR](../implementation/office-engine-m1/CC-OFFICE-M1-004/ATR-OFFICE-ENGINE-M1-ODOO-REQUEST-PERSISTENCE.md) 的 ATR-RUN-004 记录原始 `ModuleNotFoundError`；该历史状态未修改。

**TDD Impact**

需要为纯 Python worker 定义一种普通 Python 新进程可以重新导入的稳定入口，并确保父进程传递的类/数据契约使用同一模块命名空间。通过 `sys.path` 暴露 Addon 根目录、顶层包导入等只是候选，不应在 TDD 冻结前直接作为实现决定。任何实现不得把 Odoo `env` 或业务访问带入 worker。

## TV-002 — macOS `RLIMIT_AS` 与受限 worker 的兼容性

**Question**  
当前 `office_core` 通过 `RLIMIT_AS` 设置 worker 内存预算，是否能在项目 macOS 开发环境的实际 Python 进程上应用？

**Method**

1. 用项目 `venv` 读取 Python `RLIMIT_AS` 软/硬值及探针进程的虚拟地址空间 / 常驻内存。
2. 用临时 spawn 探针申请 `8 GiB` 地址空间上限，确认 worker 是否能进入处理阶段；不改源代码、不修改系统限制。

**Result** — `NOT VERIFIED`（该内存限制策略在本机的 8 GiB 场景失败；其他平台/阈值未测）

- 当前 Python 进程的 `RLIMIT_AS` 软/硬值均约 `9.22e18` 字节；探针进程虚拟地址空间约 `475,345,338,368` 字节，RSS 约 `17,694,720` 字节。
- 8 GiB 小于该进程当前虚拟地址空间，`office_core._apply_child_limits` 无法施加限制，子进程受控返回 `OFFICE_RESOURCE_LIMIT`。
- `office_verify` 已有 RSS 采样代码，但本调查未验证将其策略用于 `office_core` 的资源上限、竞态窗口、进程树内存或 Linux 目标部署行为；不得据此直接认定等价安全。

**Evidence**

- `venv/bin/python` 只读输出：`RLIMIT_AS=(9223372036854775807, 9223372036854775807)`、`current_vms=475345338368`、`current_rss=17694720`。
- 临时 spawn 探针结果见 TV-001；探针文件已删除。

**TDD Impact**

导入修复不足以使 CC-004 成功路径通过。TDD 补充必须给出可在目标开发运行时落实、可观察且失败关闭的有界内存策略；需继续验证 RSS 采样/终止策略或其他受控方案，并明确 macOS 与 Linux 的适用范围。未经测试，不得移除内存限制或把超大 `RLIMIT_AS` 视为有效预算。

## 总结与后续门禁

1. CC-004 的动态 Odoo addon 导入错误已由运行时元数据与历史失败共同定位；普通顶层包名是可导入候选，但完整服务路径未通过。
2. macOS 上的 `RLIMIT_AS` 与当前进程虚拟地址空间不兼容；该问题会在修正 import 后继续阻断 worker 成功路径。
3. 因此 **CC-004 FR 仍为 `NOT SATISFIED`**，不能将本调查写作 Phase 4 PASS。
4. 下一步先评审并冻结一份范围受限的 TV Plan，验证稳定 worker import 契约、内存强制/监控与超时清理；根据 TV 结果修订 TDD 并重基线 Implementation Plan，再创建专门的 CC 修复 CC-004 成功链路。
5. CC-004 成功路径闭环后，另立 Phase 5 Resume CC 验证独立 Addon 到受控 Office 服务的授权 handoff 和 Provider payload 隔离。原 CC-005 ATR/FR 保持 append-only，不回写历史失败/阻塞状态。

## 运行历史与限制

首次独立探针因临时脚本缺少 `if __name__ == "__main__"` 保护而在 Python spawn bootstrap 阶段失败；随后修正探针并重跑，得到上述结果。首次探针未触及 Odoo 数据或产品代码，也不计为产品功能测试结果。
