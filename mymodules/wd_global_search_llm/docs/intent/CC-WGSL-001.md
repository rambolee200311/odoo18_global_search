# CC-WGSL-001 — Addon 基础与依赖注册

> 文档版本：v0.1 Draft
> 状态：**Draft — 等待审阅；当前不得据此开始实施**
> Intent ID：`CC-WGSL-001`
> 模块：`wd_global_search_llm`
> 计划阶段：Phase 1 — Addon 基础与依赖注册
> 上游基线：[桥接 SRS v1.0.0 Frozen](../designing/SRS_wd_global_search_llm.md)；DDD N/A；[桥接 TDD v1.0.0 Frozen](../designing/TDD_wd_global_search_llm.md)；[Implementation Plan v1.2 Frozen](../implemention/IMPLEMENTATION_PLAN_wd_global_search_llm.md)
> 首个 CC 门禁：PASSED — 2026-10-15；见 [Implementation Plan §0](../implemention/IMPLEMENTATION_PLAN_wd_global_search_llm.md)
> 起草日期：2026-10-16

本文件依据 `docs/skill/odoo-project-workflow/references/templates/Coding/Coding_Contract模板.md` 起草。它只冻结第一阶段的实施范围；Draft 状态不构成实施授权，也不代表任何实现或测试已完成。

---

## 1. 变更概述

| 字段 | 值 |
|---|---|
| Intent ID | `CC-WGSL-001` |
| 模块 | `wd_global_search_llm` |
| 工作类型 | 新功能 / Odoo addon 基础 |
| 变更类型 | 新增独立 addon 元数据与静态配置 |
| 目标 | 建立可安装、可升级的桥接 addon，声明冻结基线要求的依赖，并登记与 TDD §5.1 一致的搜索工具元数据及专用 Assistant 配置；所有新增工具、Prompt 和 Assistant 均保持不可用状态，不执行搜索或 Provider 请求。 |
| 背景 | Implementation Plan Phase 1 要求先验证 addon 依赖、工具 Schema 和 Assistant 数据记录；访问组及启用流程仍是开放决策 WGSL-OD-007，因此本阶段只建立 fail-closed 配置基础。 |

## 2. 上游基线与追溯

### 2.1 SRS 引用

| SRS ID | 标题 | 与本次 CC 的相关性 |
|---|---|---|
| `FR-LLM-07`、`NFR-LLM-04` | [搜索能力只读](../designing/SRS_wd_global_search_llm.md) | 仅作为后续实现背景；本 CC 不交付可调用搜索行为，也不宣称只读安全已由元数据保证。 |

本 CC 不把任何 SRS 用户可见功能声明为本次实现范围。其验收仅覆盖 addon 安装和 fail-closed 元数据。

### 2.2 DDD 引用

**N/A。** 用户决定本项目不需要 DDD；原因与记录见 Implementation Plan v1.2 §13 `WGSL-OD-008`。本 CC 不新增领域模型、业务状态或不变量。

### 2.3 TDD 引用

| TDD ID / 章节 | 标题 | 相关性 |
|---|---|---|
| §1.2 | 模块依赖 | [冻结 TDD §1.2](../designing/TDD_wd_global_search_llm.md)；使用 `wd_global_search` 与 `odoo-llm` 18.0 模块依赖；本地 `odoo-llm` 源码基线为 commit `609ec6dda3645165f6a4a843d7af5d286081a29d`。 |
| §2 | 模块目录结构 | [冻结 TDD §2](../designing/TDD_wd_global_search_llm.md)；新增桥接 addon 基础目录及静态配置。 |
| §3 | ORM 模型设计 | [冻结 TDD §3](../designing/TDD_wd_global_search_llm.md)；复用依赖模块的 `llm.tool`、`llm.prompt`、`llm.assistant`；不新增 ORM 模型或数据库字段。 |
| §5.1 | 工具契约 | [冻结 TDD §5.1](../designing/TDD_wd_global_search_llm.md)；`wd_global_search` 的静态 Schema 必须与冻结工具契约一致。 |
| §16.1 | 运行前置 | [冻结 TDD §16.1](../designing/TDD_wd_global_search_llm.md)；目标开发库使用 `odoo.conf` 中的 `odoo18ce`，调用显式包含嵌套的 `mymodules/odoo-llm` addons 路径。 |
| `T-LLM-008` | Assistant / 工具配置不得作为唯一执行授权 | `active=False`、非公开、`read_only_hint` 等配置只用于保持本阶段未启用；它们不构成服务端执行白名单，也不得宣称为完整安全边界。 |

### 2.4 计划追溯

按 [Implementation Plan v1.2 §4 Phase 1、§7、§14.2](../implemention/IMPLEMENTATION_PLAN_wd_global_search_llm.md) 执行 addon 骨架、依赖、`llm.tool` Schema 与专用 Assistant 配置；在 `odoo18ce` 执行安装 / 升级验证，记录实际 IHR / ATR 证据。不得建立隔离数据库。

### 2.5 Bug Report / 事件报告

N/A — 新功能基础阶段。

## 3. 范围冻结

### 3.1 在范围内（In Scope）

- 新建独立 addon `mymodules/wd_global_search_llm`，声明直接使用的依赖：`wd_global_search`、`llm_tool`、`llm_thread`、`llm_assistant`。具体版本兼容依据为冻结 TDD §1.2 与上述 pinned 源码；不得加入 `llm_openai`，本阶段不发起任何 Provider 调用。
- 新增 addon 初始化文件、manifest 和 TDD §2 所要求的静态数据文件布局；不新增业务 ORM 模型、字段或迁移。
- 通过 addon XML 数据定义登记技术名为 `wd_global_search` 的 `llm.tool` 元数据，保存与 TDD §5.1 一致的输入 JSON Schema。工具记录设置 `active=False`、`default=False`；不绑定可执行的 decorator model / method，也不实现搜索函数。
- 新增专用 `llm.prompt` 与 `llm.assistant` XML 记录。Prompt 和 Assistant 均 `active=False`；Assistant 设置 `is_public=False`、`is_default=False`、不配置 provider / model / 用户组，且只关联上述搜索工具记录。该配置符合 WGSL-OD-007 的 fail-closed 当前状态，不等于最终用户授权方案。
- 为 addon 数据定义编写最小自动化元数据检查，验证外部 ID、工具名、Schema 和 inactive 状态，以及 Assistant / Prompt 的 inactive 与非公开状态。
- 按 CC 冻结后，在当前开发数据库 `odoo18ce` 验证首次安装和模块升级；仅使用 CLI 显式 addons path，不改写 `odoo.conf`，不建立隔离数据库，不执行卸载。

### 3.2 超出范围（Out of Scope）

- 搜索工具的可执行 Python 方法、参数解析、`SearchRequest` 构造、`SearchService` 调用、结果序列化、链接生成或分页。
- Provider / 模型配置、OpenAI / DeepSeek API 凭证、`llm_openai` 安装、模型拉取、聊天调用或真实 / mock Provider 测试。
- `llm.thread` / `mail.message` 继承扩展、资源描述注入、工具列表过滤或服务端工具执行白名单。
- Assistant 的激活、公开、默认化、用户组授权或上线；这些须待 WGSL-OD-007 决议，并由后续 CC 承载。
- 修改 `wd_global_search`、其已发布域 / 版本、SearchService、业务记录或 `odoo.conf`；修改 `mymodules/odoo-llm` 上游源码。
- 对 `odoo18ce` 执行数据库创建、复制、还原、模块卸载或业务数据写入。

### 3.3 非目标（Non-Goals）

- 本 CC 不提供任何可供用户实际搜索的聊天能力。
- 本 CC 不以 inactive 标志、非公开设置、`read_only_hint` 或默认工具关联替代后续服务端双层白名单。
- 本 CC 不解决 Provider 适用的隐私 / 留存、凭证运维或访问组产品决策。

### 3.4 仅限范围的追溯规则

本 CC 只覆盖 Implementation Plan Phase 1 的 addon / 静态注册义务；不把完整 SRS 需求或 TDD 搜索执行契约纳入本次实现授权。Phase 2–5 的行为须由各自 CC 追溯和承载。

## 4. 变更边界

### 4.1 允许

| 类型 | 详情 |
|---|---|
| 新增 addon 根文件 | `mymodules/wd_global_search_llm/__init__.py`、`mymodules/wd_global_search_llm/__manifest__.py` |
| 新增 Python 包骨架 | `mymodules/wd_global_search_llm/models/__init__.py`；不得在其中加入执行逻辑 |
| 新增数据定义 | `mymodules/wd_global_search_llm/data/llm_assistant_data.xml`，仅含本 CC 规定的工具、Prompt、Assistant 记录 |
| 新增测试 | `mymodules/wd_global_search_llm/tests/__init__.py`、`mymodules/wd_global_search_llm/tests/test_module_registration.py` |
| 文档 | 本 CC 对应的 IHR / ATR；实施期间按 workflow 维护 |

若实现需要超出以上路径，应先停止并修订 CC，不得顺带添加。

### 4.2 禁止

| 类型 | 详情 |
|---|---|
| 上游依赖源码 | 禁止修改 `mymodules/odoo-llm/**` 或 `mymodules/wd_global_search/**` |
| 搜索执行代码 | 禁止新增或调用 SearchService、导航服务及搜索相关业务模型方法 |
| Provider | 禁止新增 Provider / 模型 / 凭证数据，禁止网络请求 |
| 安全配置 | 禁止激活、公开、设为默认或授权用户组给新增 Assistant / Prompt / 工具 |
| 数据库配置 | 禁止修改 `odoo.conf`、创建隔离库或卸载任何模块 |
| 业务数据 | 禁止创建、修改、删除或审批业务记录；不得改写现有 Global Search 配置 |
| UI / 权限 | 禁止增加视图、菜单、客户端组件、ACL 或 Record Rule |

## 5. 必需的行为变更

| ID | 当前行为 | 期望行为 | CC-CHANGE ID |
|---|---|---|---|
| 1 | 仓库中尚无桥接 addon 安装入口 | 新 addon manifest 声明本次依赖并可由 Odoo 发现；不改动既有 addon manifest | `CC-CHANGE-001` |
| 2 | 尚无桥接搜索工具静态元数据 | 新增 XML 管理的 `wd_global_search` 工具 Schema；工具记录保持停用、无默认绑定、无可执行方法 | `CC-CHANGE-002` |
| 3 | 尚无桥接专用 Prompt / Assistant 配置 | 新增仅供后续阶段使用的 Prompt / Assistant 数据记录；二者均停用，Assistant 非公开、非默认且不指定 Provider / Model / 用户组 | `CC-CHANGE-003` |
| 4 | 新 addon 没有注册数据自动化检查 | 新增明确断言上述 manifest / 数据记录约束的测试 | `CC-CHANGE-004` |

## 6. 既有行为保留（回归边界）

| ID | 行为 / 契约 | 为什么不得改变 | CC-PRESERVE ID |
|---|---|---|---|
| 1 | `wd_global_search` 已发布配置与搜索行为保持原状，当前 `global_search_baseline` 发布版本 5 不变 | 本 CC 只新增可选桥接 addon，不修改搜索执行层 | `CC-PRESERVE-001` |
| 2 | 不修改 `odoo-llm` 源码及其既有 Provider、工具、Prompt、Assistant 数据定义 | 上游基线锁定于 TDD §1.2 的 pinned commit；本 CC 只能声明依赖 | `CC-PRESERVE-002` |
| 3 | 不对业务模型记录产生新增、更新、删除或审批 | 本 CC 仅建立 addon 与技术元数据，不执行工具 | `CC-PRESERVE-003` |

## 7. 适用的 TDD 防护栏

| TDD 防护栏 | 适用性 | 本次落实位置 | 验证方式 |
|---|---|---|---|
| `T-LLM-008` | 适用 | 工具、Prompt、Assistant 均保持停用；不把元数据提示当作授权控制；本阶段没有可执行工具方法 | `CC-TEST-002`、`CC-TEST-003`；源码检查 XML 配置 |
| `T-LLM-001` 至 `T-LLM-007` | 当前不适用为实现项；其约束对后续搜索执行 CC 仍有效 | 本 CC 不实现搜索工具或聊天执行路径 | 核查本 CC 文件边界与 diff；发现执行逻辑即停止并升级 |

## 8. 数据 / 迁移影响

| 字段 | 值 |
|---|---|
| 需要迁移 | 否；不新增模型、字段、索引或业务数据迁移 |
| 数据变更 | 首次安装会按本 addon XML 创建 inactive 的 `llm.tool`、`llm.prompt`、`llm.assistant` 元数据；依赖模块安装会按上游自身定义创建其模型 / 数据。当前 pinned `llm_assistant` 源码含有自己的非公开 Assistant / 工具种子记录；这些是上游安装副作用，不由本 addon 创建或修改，实施前须检查并在安装后确认未被配置为公开或绑定 Provider / Model |
| 数据库 | 使用 `odoo.conf` 中的 `odoo18ce`（`127.0.0.1:5555`）；不建立隔离数据库 |
| 恢复 / 回滚策略 | 本 CC 不执行模块卸载。若安装或升级产生异常，在该开发库停止后续操作并保留日志，由项目负责人决定修复方案；不得自行删除记录或卸载依赖 |
| 验证 | 通过 Odoo 日志与只读 ORM / Odoo shell 核对本 addon XML ID、依赖模块状态及 Global Search 发布版本；核对业务记录未被本 addon 逻辑触碰 |

## 9. API / 集成影响

| 字段 | 值 |
|---|---|
| 修改的端点 | 无 |
| 向后兼容 | 是；新增可选 addon，不修改现有公共接口 |
| Adapter 变更 | 无；搜索适配器留待 `CC-WGSL-002` |
| 外部服务请求 | 无；不调用 DeepSeek、OpenAI 或其他 Provider |

## 10. 安全 / 权限影响

| 字段 | 值 |
|---|---|
| 新权限 | 无；不新增 ACL / Record Rule，不授予 Assistant 用户组 |
| 变更的 ACL | 无 |
| 新增配置状态 | 工具记录 `active=False`、`default=False`；Prompt / Assistant `active=False`；Assistant `is_public=False`、`is_default=False`、不绑定 Provider / Model / 用户组 |
| 安全边界说明 | 上述静态状态仅确保本阶段配置不主动开放；不代表 `llm_tool` 会在所有执行入口强制检查 inactive，也不代替 TDD §12 / §18 的服务端白名单。后续激活必须由适用 CC 明确授权并实现必要服务端控制。 |
| 敏感数据暴露检查 | 不写 API key、token、原始提示或业务记录；本 CC 不发送任何 Provider 请求。 |

## 11. 测试契约

下表是冻结后须执行并记入 ATR 的要求；**起草时均为 NOT RUN**。实施者不得把计划断言写成已通过证据。

| 测试 ID | 对应变更 | 上游来源 | 测试类型 | 预期结果 | 人工验证 | 原因 |
|---|---|---|---|---|---|---|
| `CC-TEST-001` | `CC-CHANGE-001` | Plan Phase 1；TDD §1.2 / §2 | Odoo 模块集成安装 | 在 `odoo18ce`、显式 addons path 下可发现并安装 `wd_global_search_llm`；依赖状态满足；日志无模块加载错误 | 是 | 验证真实 Odoo 模块依赖和加载路径 |
| `CC-TEST-002` | `CC-CHANGE-002` | TDD §5.1、`T-LLM-008` | Odoo `TransactionCase` / 元数据断言 | XML ID 存在；工具名为 `wd_global_search`；JSON Schema 可解析且字段契约与 TDD §5.1 一致；`active=False`、`default=False`；没有 decorator model / method；不调用搜索或 Provider | 否 | 验证静态注册准确且本阶段不可执行 |
| `CC-TEST-003` | `CC-CHANGE-003` | Plan Phase 1；WGSL-OD-007；`T-LLM-008` | Odoo `TransactionCase` + ORM 检查 | Prompt / Assistant XML ID 存在且 inactive；Assistant 非公开、非默认，无 Provider / Model / 用户组，只关联桥接搜索工具 | 是 | 开放流程未批准前维持 fail-closed 配置 |
| `CC-TEST-004` | `CC-CHANGE-001`–`003` | Plan Phase 1；`CC-PRESERVE-001` | Odoo 模块升级 / 元数据回归 | 在同一 `odoo18ce` 上升级模块成功；无重复桥接记录；桥接工具 / Assistant 仍为 inactive；`global_search_baseline` 仍 active 且发布版本仍为 5 | 是 | 验证升级及对既有搜索配置的保留 |
| `CC-TEST-005` | `CC-CHANGE-004` | `CC-TEST-001`–`004` | 自动化测试 / 安装后只读核查 | 自动化检查覆盖必要 XML ID 和 fail-closed 字段；安装与升级过程中没有桥接业务搜索调用、Provider 请求或业务记录写操作 | 是 | 将本阶段的边界要求变成可复核证据 |

测试运行命令（从仓库根目录执行，实施阶段使用）：

```bash
./venv/bin/python odoo/odoo-bin -c odoo.conf -d odoo18ce \
  --addons-path=addons,odoo/addons,mymodules,mymodules/odoo-llm \
  --test-enable --test-tags /wd_global_search_llm \
  -i wd_global_search_llm --stop-after-init
```

升级验证将 `-i` 替换为 `-u`。Odoo-LLM 依赖模块会按其上游 manifest 加载自带数据；安装前核对这些数据定义，安装后只读核对其 Assistant 未公开且未绑定 Provider / Model。若发现凭证、公开 Assistant 或其他非预期可调用配置，停止并交由用户决定后续处理，不在本 CC 中修改上游记录。命令只作本 CC 的拟定执行方式；此 Draft 尚未执行命令或测试，不授权实际安装。

## 12. 停止条件 / 升级闸门

| 触发条件 | 升级路径 |
|---|---|
| 冻结 TDD §5.1 Schema 与当前代码 / `llm.tool` 字段无法兼容 | 停止并返回 TDD 评审；不得自行删改参数或改变工具契约 |
| Odoo-LLM pinned 源码缺失、版本不匹配、依赖无法在显式 addons path 下解析 | 停止并复核 Implementation Plan / TDD 依赖基线 |
| 安装要求修改 `odoo.conf`、建立新数据库、卸载模块或清理现有记录 | 停止；当前 CC 不授权这些操作，提交用户 / 项目负责人决策 |
| 安装 / 升级会修改 `wd_global_search` 配置、发布版本或业务记录 | 立即停止，保留日志并报告，不得继续或自行回滚数据 |
| Odoo-LLM 依赖安装将创建可被普通用户访问的 Assistant，或发现 Provider / Model 凭证已配置并可能使上游种子 Assistant 可运行 | 停止安装 / 后续步骤并报告；本 CC 不授权修改或停用上游 Assistant / Provider 记录 |
| 新增 Assistant / Prompt / 工具需要激活、公开、授权用户组或绑定 Provider 才能通过验收 | 停止并返回需求 / 安全决策及后续 CC；不得以放宽 fail-closed 状态绕过 |
| 需要加入可执行搜索方法、Provider 调用、白名单、权限逻辑或文件超出 §4 | 停止并修订 CC；由 Phase 2 / 3 CC 承载 |

## 13. 完成定义 / 关闭标准

此处定义未来实施的关闭条件，**不是本 Draft 的执行结果**。

| ID | 标准 | 闸门类型 |
|---|---|---|
| 1 | §3.1 / §5 所有 In-Scope 项均已实现，且新增文件符合 §4 边界 | 硬闸门 |
| 2 | 所有适用 `CC-TEST-001`–`005` 均已在 `odoo18ce` 对应代码基线上执行，原生结果与证据如实记录在 ATR | 硬闸门 |
| 3 | 工具、Prompt、Assistant 均保持本 CC 规定的 inactive / 非公开配置；无 Provider / Model 绑定 | 硬闸门 |
| 4 | `CC-PRESERVE-001`–`003` 有实际核验记录；无卸载、无配置文件改动、无业务数据修改 | 硬闸门 |
| 5 | IHR / ATR 与 CC、代码基线、安装 / 升级日志对应；任何失败 / 跳过 / 缺失项按 workflow 明确处置 | 硬闸门 |

## 14. 追溯矩阵

### 14.1 正向：In-Scope 上游 → CC

| 上游 ID | CC-CHANGE ID | 备注 |
|---|---|---|
| Plan Phase 1 addon / dependency / metadata deliverables | `CC-CHANGE-001`、`002`、`003` | 仅实现阶段 1 静态基线 |
| TDD §5.1 工具 Schema | `CC-CHANGE-002` | 只登记 Schema，不提供执行实现 |
| `T-LLM-008` | `CC-CHANGE-002`、`003` | 标记 inactive 配置不是执行授权；本阶段不开放工具 |

### 14.2 反向：CC → 上游

| CC ID | 上游 ID | 类型 |
|---|---|---|
| `CC-CHANGE-001` | Implementation Plan §4 Phase 1；TDD §1.2、§2 | Plan / TDD |
| `CC-CHANGE-002` | TDD §3、§5.1、`T-LLM-008` | TDD |
| `CC-CHANGE-003` | Implementation Plan §4 Phase 1；WGSL-OD-007；`T-LLM-008` | Plan / Open Decision / TDD |
| `CC-CHANGE-004` | Plan §7 Phase 1 acceptance；CC-TEST-001–005 | Plan / CC |

### 14.3 无 DDD 路径

本项目 DDD 为 N/A；追溯按 Implementation Plan → SRS / TDD → CC → IHR / ATR → FR 执行。本 CC 不虚构 DDD 编号。

## 附录 A — 变更决策（CC-DEC）

| CC-DEC ID | 决策 | 考虑的替代方案 | 理由 |
|---|---|---|---|
| `CC-DEC-001` | 在 `odoo18ce` 开发库上验证；显式补充 `mymodules/odoo-llm` 到 Odoo 进程 addons path，不改 `odoo.conf` | 建立独立隔离库；永久改写共享配置 | 用户明确决定不建立隔离库；计划已有该开发环境与 CLI 路径基线 |
| `CC-DEC-002` | 本阶段只登记无可执行绑定的 inactive 工具元数据，并保持 Prompt / Assistant inactive、非公开 | Phase 1 即可调用；只依赖 UI 隐藏或 `read_only_hint` | WGSL-OD-007 的访问 / 启用流程未决；符合 `T-LLM-008` 且不把配置字段误作执行授权 |
| `CC-DEC-003` | Provider / model 暂不绑定，`llm_openai` 不作为本 addon 的直接依赖 | 预先选择 OpenAI / DeepSeek 并触发 API 验证 | Phase 1 不调用模型；保持环境中性，Provider 及真实工具调用留待后续阶段 |

## 附录 B — 版本历史

| 版本 | 日期 | 变更说明 | 状态 |
|---|---|---|---|
| v0.1 | 2026-10-16 | 首稿；定义 Phase 1 addon 与静态注册范围，记录直接使用 `odoo18ce` 和 inactive 配置边界 | Draft |
