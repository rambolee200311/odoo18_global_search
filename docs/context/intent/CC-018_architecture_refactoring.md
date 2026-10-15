# CC-018 — Global Search Architecture Refactoring

## 0. Governance

| 字段 | 值 |
|---|---|
| Coding Contract | CC-018 |
| 版本 | v1.2.0 |
| 状态 | APPROVED / FROZEN；已批准继续阶段 1 实施 |
| Intent ID | `GS-SEARCH-ARCHITECTURE-REFACTORING` |
| 上游 SRS | [SRS_global_search](../../requirement/SRS_global_search.md) v1.5 FROZEN |
| 上游 TDD | [TDD_global_search](../../design/TDD_global_search.md) v0.4 FROZEN |
| 前置 CC | CC-001 ~ CC-017、CC-014-1、CC-014-2 |
| 相关 CC | CC-017-1 Structured Result Card Template Output |
| 模块 | `wd_global_search` |
| 目标 | 先建立可重复的 Playwright UI 回归基线，再以不改变行为的方式抽出 Workspace HTML 并拆分 controller、前端脚本和配置模型文件 |
| 代码核对基线 | `main @ 09205c7` |
| 批准 / 冻结 | v1.0.0 于 2026-10-14 批准；v1.1.0 于同日批准并冻结；用户于 2026-10-15 批准 v1.2.0 正式修订并重新冻结 |

**治理边界：** CC-018 只授权既有实现的测试先行与文件职责拆分，不授权新增业务能力或改变运行时契约。本文档不修改 SRS v1.5、TDD v0.4 或任何既有 CC。若实现要求改变其中任何一项，必须停止并发起正式影响评审。

### v1.1.0 正式修订：测试环境

用户于 2026-10-14 批准使用现有本机 `odoo18ce`（`http://127.0.0.1:8091`）执行 CC-018 测试，并允许通过 Odoo 正常 UI/ORM 创建及清理专用测试夹具。此项仅修订测试环境与夹具策略，不改变任何产品行为或既有业务契约。

- 所有测试夹具必须使用 `CC018-<run-id>-<uuid>` 唯一标记，由具备相应正常权限的 Odoo 用户经 UI/ORM 创建、清理和核验。
- 不得通过 fixture 修改或删除既有业务记录、已发布配置、用户、公司、ACL 或 Record Rule；配置生命周期测试仅能操作专用临时 Draft 夹具，不得 Publish 或 Apply 到现有配置。
- 不得使用数据库客户端、裸 SQL、游标、`sudo()`、superuser 或未经当前用户授权的 admin 环境。测试角色必须使用正常授权账号。
- 测试必须串行运行；每次结束须经 ORM 核验本次唯一标记已清零。创建、清理或核验失败均为显式失败，停止后续测试/阶段，不得静默遗留数据。
- 运行产物、认证状态和凭据仍不得入库；本修订不授权访问或导出 Odoo 登录凭据。
- 若测试必须修改既有共享记录、已发布配置或权限数据才能继续，立即停止并另行评审。

### v1.2.0 正式修订：临时测试用户

用户于 2026-10-15 批准本正式修订并重新冻结，以便阶段 1 可建立多角色测试会话。

本版本仅授权以下受限行为：

- 仅在本机 `odoo18ce` 中通过正常 Odoo UI/ORM 创建本轮测试专用的 `reader`、`fixture_writer`、`restricted`、`config_manager` 临时用户；使用既有 Odoo/模块组定义，不创建或修改 Group、ACL、Record Rule 或应用权限逻辑。
- 临时用户使用 `CC018-<run-id>-<uuid>` 唯一标记；登录名须唯一且不可路由到真实邮箱。只可为新建临时用户分配必要的既有角色组和最小公司访问；不得改变任何既有用户、公司字段或其他用户的组/公司关系。
- 创建动作必须由当前已授权的普通 Odoo 用户经 UI/ORM 执行。若普通权限不足，或需 `sudo()`、superuser、admin environment、临时放宽权限或修改既有用户/组/公司定义，立即停止。
- 不使用硬编码、共享或弱预设密码。测试密码须逐用户随机生成、仅在进程内短暂使用，不写入源码、日志、终端输出、聊天或版本控制；认证状态须限本机权限保存并在本轮结束后清除。不得发送邀请、重置邮件或其他外部通知。
- 清理顺序为先清理本轮业务 fixture，再经正常 ORM 删除仅由本轮创建且唯一标记匹配的临时用户及其专用关联数据，并核验标记计数为零。若记录引用阻止安全清理，不得强制删除或绕过权限；停止阶段并报告遗留项。
- 本例外不授权修改 SRS、TDD、既有 CC、既有用户、既有公司定义、Group、ACL、Record Rule、发布配置或产品权限边界。若不能用当前既有权限配置表达所需测试角色，停止并另行评审。

本修订收窄 v1.1.0 §0 中“不得触碰用户/公司/权限数据”的限制，仅为上述新建、临时、唯一标记的测试用户提供例外；未列出的 v1.1.0 控制继续适用。

**版本基线处理：**

- 本 CC 基于 SRS v1.5 FROZEN、TDD v0.4 FROZEN，以及已冻结的 CC-001 ~ CC-017、CC-014-1、CC-014-2 和 CC-017-1。
- CC-018 不修改上述任何冻结文档的既有语义。
- 若评审或实施要求修改任一冻结基线，必须先停止并完成正式影响评审；不得在本 CC 内静默修订。

**审批门：** 所有阶段均须按 §4 顺序执行。阶段 1 UI 回归基线没有通过并冻结前，不得开始阶段 2–5。

## 1. Contract Goal

**一句话目标：** 为后续验证工作建立可信的浏览器回归基线，并在该基线上分阶段整理 Workspace HTML、HTTP Controller、Workspace JavaScript 和配置模型文件，同时保持用户可见及服务端行为完全不变。

```text
当前冻结基线（main @ 09205c7）
          │
          ▼
阶段 1：Playwright 关键 UI 场景 + DOM/视口基线
          │ 通过并独立关闭
          ▼
阶段 2：Workspace HTML 提取为 Odoo QWeb 模板
          │ UI 与响应契约回归
          ▼
阶段 3：controllers/main.py 按页面、API、配置生命周期拆分
          │ 路由、安全、响应及行为回归
          ▼
阶段 4：preview.js 按 Workspace、Search API、配置快照职责拆分
          │ UI、条件、Count、分页及错误回归
          ▼
阶段 5：models/configuration.py 按模型、生命周期、职责拆分
          │ ORM、发布、权限、升级及模块回归
          ▼
IHR + ATR + HVR；所有阶段分别验收和关闭
```

本 CC 为可维护性重构和后续验证做准备；不实施或集成 LLM，不授权搜索能力变化。

## 2. Background and Acceptance Findings

### 2.1 起草前核对

核对日期：2026-10-14。

| 核对元数据 | 值 |
|---|---|
| Branch | `main` |
| Commit | `09205c7` |
| 模块 | `wd_global_search` |
| 核对方式 | 只读检查源码、冻结文档、测试文件及 Playwright 项目规范 |
| 未执行事项 | 未启动/操作 Odoo runtime，未使用 ORM，未直接读写数据库，未运行浏览器测试，未修改配置、业务数据或既有文档 |

本节是源码和文档层面的核对结果，不构成运行时或浏览器测试证据。

| 核对项 | 当前事实 | 证据 |
|---|---|---|
| Controller | [controllers/main.py](../../../mymodules/wd_global_search/controllers/main.py) 共 874 行。单个 `GlobalSearchController` 同时提供 Workspace HTML、Result Card Template 管理页面及配置端点、Preview、表单导航、Search 和 Cancel。`/wd_global_search` 在控制器方法内拼接完整 HTML 字符串，并插入 Resource 描述、配置版本和用户时区。 | 当前路由定义；第 47–220、238–766、767–874 行 |
| Workspace HTML | HTML 含既有标签、顺序、ID、class、ARIA 属性、`data-testid`、文案和 CSS/JS URL；资源标签列表由当前用户可见的已发布描述生成，并经 HTML escaping 写入响应。 | `/wd_global_search` 路由 |
| Workspace JavaScript | [preview.js](../../../mymodules/wd_global_search/static/src/js/preview.js) 共 1,557 行，单一 IIFE 混合 DOM 初始化、条件输入与展示、日期/时区转换、Resource 选择与状态、Count、结果卡片、导航、分页、Search fetch、错误处理和事件绑定。 | 当前 `preview.js` |
| 页面脚本边界 | Template Designer 已使用独立的 `template_designer_page.js` 和 `template_designer_field.js`；它们不是 CC-018 的 `preview.js` 拆分范围。 | `static/src/js/` |
| 配置模型 | [models/configuration.py](../../../mymodules/wd_global_search/models/configuration.py) 共 1,450 行，包含 Mutation Mixin、Domain/Version 生命周期、Business Resource、资源/字段/关系/日期/状态/Snapshot 配置、Vocabulary、Scoring、Performance 和 Audit 模型。 | 当前 `configuration.py` |
| 配置边界 | 配置文件含发布、暂存变更、Apply、校验、Snapshot/checksum、审计及模型初始化逻辑。`BusinessResource.init()` 含既有 `cr.execute()` 语句；本 CC 不授权新增、手动执行或改变任何数据库操作。若拆分与此边界冲突，停止评审。 | `ConfigurationVersion`、`BusinessResource` 等模型 |
| 现有测试 | 模块测试目录包含 15 个 Python 测试模块（另有 `__init__.py`），采用 Odoo `TransactionCase`；覆盖服务、配置、权限、模板、导航、请求边界和升级等。未发现模块级 `HttpCase` 或 `tests/ui` Playwright 回归套件。 | [tests/](../../../mymodules/wd_global_search/tests/) |
| 现有选择器 | Workspace 已有 `data-testid`，包括 `global-search-workspace`、`search-query`、`resource-*`、`condition-*`、`date-*`、`query-understanding`、`results-pane`、`result-list` 和分页选择器。新增选择器只用于稳定测试，不得改动可见行为。 | Workspace HTML |
| E2E 规范 | 项目 Playwright 规范要求真实浏览器用户流程、语义化选择器、业务 UI readiness、隔离测试数据、保存状态不入库；不得以 ORM 断言替代 UI E2E。 | `docs/skill/odoo-e2e-user-simulation/` |
| 技术债 | 当前仓库只有 TD-001～TD-006；未找到 TD-007～TD-011 的定义文件或权威标题。§17 的映射只能作为待确认建议。 | `docs/context/debt/` |

### 2.2 Implementation Gap

- HTML 和页面入口耦合在 controller 方法中，当前缺少独立模板边界和自动化 UI 基线，后续文件迁移缺少可靠的行为等价判据。
- Workspace JavaScript 将页面状态、条件编辑、Search 请求和呈现混在单一 IIFE 中，边界不便于独立理解和测试。
- `configuration.py` 聚合多个配置模型及其生命周期逻辑，模型文件职责不清晰；但这些模型共享既有 ORM、发布和审计边界，不能借拆分引入新的 Repository、Service 或持久化架构。
- 当前模块没有 Playwright 测试入口；此前的人工浏览器观察不是可重复的自动化回归基线。

### 2.3 Existing Contract Support

- SRS v1.5 的 Search Workspace、Snapshot、Preview、打开完整记录、权限、过滤、Count、配置和错误要求是行为权威。
- TDD v0.4 §3、§4–§7、§9–§12 已定义 Search Service、配置生命周期、权限、Preview、错误、接口和测试约束。
- CC-001 ~ CC-017（含 CC-014-1、CC-014-2）以及 CC-017-1 已定义各自冻结的行为与回归要求；CC-018 只消费、不重定义。
- 当前实现的实际 HTTP URL、认证、方法、CSRF、状态码、响应体和资源加载方式优先作为重构前基线；TDD 中的逻辑接口名称不构成更改实际端点的授权。
- 当前 SRS/TDD 对照仅用于追溯；任何行为差异均以冻结上游契约和现有 CC 为准，不能通过更新 UI 快照掩盖差异。

**冻结文件声明：** 不修改 `docs/requirement/SRS_global_search.md`、`docs/design/TDD_global_search.md`、任何既有 CC、IHR、ATR、HVR 或技术债文档。若追溯发现上游缺少执行契约，停止并提请正式变更。

## 3. Scope

### 3.1 In Scope

- 在现有代码基线上建立并冻结 Playwright 浏览器 UI 自动化回归基线。
- 增加最小测试专用 Playwright/pytest 配置及运行证据忽略规则；依赖仅供开发/测试使用，不加入 Odoo 模块运行时依赖。
- 从 `/wd_global_search` controller route 中抽出 Workspace 页面 HTML；建议采用 Odoo 原生 QWeb 模板。
- 按职责拆分 `controllers/main.py` 中的 Workspace、Search/Cancel API、配置管理端点和 Preview/导航端点。
- 按职责拆分 Workspace `preview.js`，保持现有 Workspace 脚本入口及可观察契约。
- 按 ORM 模型、配置生命周期和职责拆分 `models/configuration.py`。
- 为新增模板、Controller、JavaScript 模块和模型文件补充必要的 Odoo 注册/import 与测试。
- 每一阶段都执行对应服务端、浏览器及既有回归，并分别记录 IHR、ATR、HVR。

### 3.2 Out of Scope

- 修改 SRS、TDD、CC-001 ~ CC-017、CC-014-1、CC-014-2、CC-017-1 或其语义。
- 增加或改变任何搜索、过滤、排序、配置、卡片、Preview、导航或错误行为。
- 引入新架构、Web/JS 框架、通用 Controller/Repository/DAO/DTO 层、独立服务、事件总线、缓存层或构建系统。
- 引入 LLM、Elasticsearch、OpenSearch、向量检索或外部搜索服务。
- 改变 Odoo ORM 模型 `_name`、字段、表/关系表、权限文件、业务数据或数据库 schema。
- 新增、手动执行或重写原始 SQL；直接使用数据库客户端或游标读写数据库。
- 修改 `odoo/`、官方 `addons/`、CSS 视觉规则或 Template Designer 专用脚本。
- 将 Playwright 登录凭据、认证 `storage_state`、业务数据或运行时截图加入版本控制。
- 将此重构扩展为 LLM 评估、搜索质量改进或 SRS/TDD 修订。

### 3.3 与既有 CC 的边界

| 既有契约 | CC-018 的接口边界 |
|---|---|
| CC-001 ~ CC-003 | 保留配置语义、Search Service 契约和当前用户权限边界；不放宽字段、记录或多公司访问。 |
| CC-004、CC-013 | 保留 Preview 只读行为、结果身份及原生表单导航路径。 |
| CC-005、CC-015、CC-016 | 保留 Query、Refinement、条件组合、编辑、日期/状态和 Query Understanding 行为。 |
| CC-006 ~ CC-010 | 保留性能/索引、部分失败、日志、语言/时区及升级兼容要求。 |
| CC-011、CC-012 | 保留验收约束、Resource Selector、Facet 和 Count 语义。 |
| CC-014、CC-014-1、CC-014-2 | 保留纯文本模板、关系字段、多层可搜索字段和兼容路径。 |
| CC-017、CC-017-1 | 保留 Workspace 视觉规则、结构化/legacy 卡片响应及 DOM 契约。 |

## 4. Refactoring Order

| 阶段 | 工作 | 前置条件 | 阶段通过与关闭条件 |
|---|---|---|---|
| 1 | 建立 Playwright UI 回归测试和重构前基线 | CC-018 v1.1.0 获批；`odoo18ce`、所需角色会话及专用 ORM 夹具可用 | §5 所有 MUST UI 流程通过；基线、浏览器/视口、语言、数据 fixture、依赖配置、性能基线、证据索引和运行命令归档；Safari HVR 完成；用户 HVR 签署。未通过不得进入阶段 2。 |
| 2 | Workspace HTML 从 controller 抽出 | 阶段 1 SATISFIED | DOM/文案/本地化/响应头及 HTTP 行为与阶段 1 等价；CC-TEST-024 与 UI 回归通过；阶段 IHR/ATR/HVR 关闭。 |
| 3 | 拆分 `controllers/main.py` | 阶段 2 SATISFIED | 所有当前路由、安全参数、错误及响应契约保持；CC-TEST-025、服务端及浏览器回归通过；独立关闭。 |
| 4 | 拆分 Workspace `preview.js` | 阶段 3 SATISFIED | 搜索、条件、配置版本更新、Count、分页、结果呈现、导航及失败处理等价；CC-TEST-026、所有目标浏览器回归通过；独立关闭。 |
| 5 | 拆分 `models/configuration.py` | 阶段 4 SATISFIED | ORM 模型、配置生命周期、权限、审计、Snapshot、升级和现有数据行为等价；CC-TEST-027、既有模块测试及 UI 回归通过；独立关闭。 |

阶段不得并行实施，不得把多个阶段合并为一个无独立证据的重构提交。若需调整顺序，先停止并取得正式评审批准。

## 5. Browser UI Regression Tests

### 5.1 工具与执行方式

- 使用 Playwright 执行真实 Chromium、Firefox、WebKit 浏览器流程；WebKit 结果不得描述成真实 Safari 已通过。另按 TDD §7.4/§12.5 对 Safari 最新版执行人工 HVR；WebKit 不能替代 Safari 验收。
- 按项目 E2E 规范模拟真实用户，使用当前 Odoo 登录会话及用户角色。优先使用语义化 role/label/text selector；已有稳定 `data-testid` 可作为后备选择器。
- 使用本机 `odoo18ce` 和 §0 v1.1.0 规定的可重复、命名空间化 ORM fixture；不得依赖任意既有业务记录或触碰生产数据。
- 使用业务界面 readiness、相关 RPC 和可见结果断言；不得以 `networkidle` 或任意 sleep 作为通用等待。
- 测试认证通过环境配置或本机受保护的 `storage_state` 提供；不得提交凭据、cookie 或认证状态文件。
- Playwright 只能验证用户可见的端到端行为；配置约束、ACL 和 ORM 模型行为仍由既有 Odoo 测试承担。
- 测试依赖安装：在隔离的开发/测试环境执行 `python3 -m pip install pytest-playwright`，再执行 `python3 -m playwright install chromium firefox webkit`。依赖不得加入模块运行时依赖；若项目使用锁文件，须固定并记录实际版本。
- 使用单一仓库测试配置 `pytest.ini`；集中声明 Playwright browser projects、超时及失败证据目录，不创建互相冲突的多套配置。
- 预期执行入口：`ODOO_BASE_URL=http://127.0.0.1:8091 PLAYWRIGHT_STORAGE_STATE=<protected-local-file> ./venv/bin/python -m pytest -q mymodules/wd_global_search/tests/ui`。测试必须记录数据库标识 `odoo18ce`、专用 fixture 标记和浏览器版本；环境变量值、认证文件不写入源码或日志。

### 5.1.1 测试 Fixture 规范

- Fixture 位置：`mymodules/wd_global_search/tests/fixtures/`；浏览器流程由 Odoo ORM 或受控模块 fixture 准备数据，不使用 SQL、数据库驱动或裸游标。
- 覆盖至少 Contact、Sales Order、Purchase Order 三类 Resource，以及 Char、Date/Datetime、Selection、Many2one 等当前可配置字段类型。
- 覆盖至少普通用户可读、无权、部分字段可读及配置管理员/非管理员角色；语言与时区使用当前系统中已启用的设置。
- 每个测试使用 §0 定义的唯一标记；不得依赖任意现有业务记录。共享库夹具创建范围和清理要求按 §0 v1.1.0 执行。
- 测试结束通过正常权限下的 ORM 清理本测试创建的 fixture，并确认对应唯一标记数量为零；失败清理须显式报告并停止后续阶段，不能静默留下数据。

### 5.1.2 临时测试用户

- 每次运行仅创建 `reader`、`fixture_writer`、`restricted`、`config_manager` 所需的临时角色用户；角色映射必须对应现有 Odoo / Global Search 权限定义。
- 角色映射固定为：`reader` 使用 `base.group_user`；`fixture_writer` 使用 `base.group_user` 与既有 `base.group_partner_manager` 联系人管理组；`restricted` 使用既有 `base.group_portal`；`config_manager` 使用 `base.group_user` 与 `wd_global_search.group_config_manager`。不得创建临时安全组。
- 临时用户的登录名、显示名和关联 fixture 使用同一 `CC018-<run-id>-<uuid>` 命名空间；不得使用真实人员邮箱或可投递地址。
- 账号创建、组分配、认证和清理遵守 §0 v1.2.0 边界。
- 任何角色若需新增组、改 ACL/Record Rule、提权、修改既有用户/公司或无法验证最小权限，停止并保持阶段 OPEN。

### 5.2 基线内容

阶段 1 必须在未重构代码上建立：

1. 每个 §5.3 MUST 场景的可重复测试、通过断言和失败判据。
2. 数据库 `odoo18ce`、脱敏测试角色映射、语言、时区、Resource 配置版本和受控 fixture 标记的可追溯记录；不得记录真实用户名或凭据。
3. Playwright Chromium、Firefox、WebKit 的浏览器版本及至少桌面和窄屏视口记录；另记录 Safari 最新版人工 HVR 版本/视口。
4. 主要页面的稳定语义/DOM 基线及截图证据。截图用于视觉复核，不以跨平台像素完全相等代替语义验收。
5. 浏览器控制台错误、未预期 RPC/写操作和失败证据策略。

**截图与证据存储：**

- Playwright 失败/基线截图输出到 `mymodules/wd_global_search/tests/ui/evidence/`，命名格式为 `<test_id>_<browser>_<viewport>_<timestamp>.png`。
- 同目录的 `INDEX.md` 记录证据路径、测试 ID、浏览器/版本、视口、fixture 标识及结果；不得记录用户名、cookie、原始查询值或业务敏感内容。
- 运行截图、trace、video、storage state 等运行时产物不得提交；仅索引模板/脱敏测试元数据可纳入版本控制。阶段实施时须以精确 `.gitignore` 规则排除运行时文件。

**浏览器/视口矩阵：** 视口固定为 Desktop `1440×900`、Tablet `768×1024`、Narrow `390×844`。每阶段在所有矩阵单元执行 CC-TEST-020 smoke；完整 CC-TEST-001～012 在 Desktop 执行。Safari 必须是真实 Safari 最新版的人工 HVR，Playwright WebKit 仅作为独立兼容性证据。

| 浏览器 | 执行方式 | Desktop | Tablet | Narrow |
|---|---|---|---|---|
| Chromium 最新版 | Playwright | CC-TEST-001～012 + CC-TEST-020 | CC-TEST-020 | CC-TEST-020 |
| Firefox 最新版 | Playwright | CC-TEST-001～012 + CC-TEST-020 | CC-TEST-020 | CC-TEST-020 |
| WebKit 最新版 | Playwright | CC-TEST-001～012 + CC-TEST-020 | CC-TEST-020 | CC-TEST-020 |
| Safari 最新版 | 人工 HVR | HVR-001～012 | HVR-012 + 布局/交互 smoke | HVR-012 + 布局/交互 smoke |

基线冻结后不得仅为使重构测试通过而自动更新快照。任何差异须先证明其仅为结构迁移且可观察行为等价；若出现可见差异，停止并评审。

### 5.3 MUST 场景

| 测试 ID | 用户流程 | 可执行通过标准 |
|---|---|---|
| CC-TEST-001 | 登录后打开 Search Workspace | 当前有权用户看到 Workspace；未授权访客按既有认证行为处理；页面无未处理 JS 错误。 |
| CC-TEST-002 | 输入关键词并执行搜索 | 结果、状态、Resource 标签和 Query Understanding 与受控基线一致；Search 从 UI 发起，不直接调用 ORM。 |
| CC-TEST-003 | 选择/取消 Resource 并重新搜索 | Resource 选择状态、结果集合及各 Resource Count 与基线一致；清空选择的既有提示行为不变。 |
| CC-TEST-004 | 添加/编辑/删除结构化条件及关键词 | 字段、运算符、值校验、有效条件展示、查询和结果与当前 CC-016/CC-015 行为一致。 |
| CC-TEST-005 | 日期预设、自定义 From/To 与状态筛选 | 日期边界、时区、状态可见选项、错误提示和清除行为保持当前契约；无效输入不得悄然放宽条件。 |
| CC-TEST-006 | 浏览结果 Count 和分页 | Count、Resource Count、每页条数、页码边界和切页内容/身份与基线一致；无权限记录不得通过 Count 泄露。 |
| CC-TEST-007 | 查看结果卡片和打开记录 | title/meta/summary/details、legacy 文本和字段 Snapshot 各自按现行模式渲染；打开目标记录仍使用既有导航动作。 |
| CC-TEST-008 | 部分失败、无结果和请求错误 | 错误状态、可见文案、重试/结果清理行为与基线一致；无成功形态的伪回退。 |
| CC-TEST-009 | 当前用户权限与配置角色隔离 | 搜索结果、Count、Resource/字段描述和配置 UI 与已授权用户基线一致；测试不得借管理员权限替代普通用户。 |
| CC-TEST-010 | 管理员的模板配置生命周期 | 仅配置管理员可操作现有 Designer；Check、Save、Apply 的可见结果和持久性与现状一致。 |
| CC-TEST-011 | 用户语言、时区和本地化文案 | 资源标签、日期呈现、错误提示和现有翻译行为不变；语言与时区 fixture 可重复。 |
| CC-TEST-012 | 桌面/窄屏和键盘交互 | 区域顺序、折叠、选择、分页、焦点和键盘操作符合 CC-016/CC-017；无横向溢出或意外写操作。 |

**覆盖门槛：** CC-TEST-001～012 均须有自动化用例并在重构前基线上通过，覆盖率为 12/12；每个后续阶段也必须运行全部 12 个回归流程。不得用代码行覆盖率替代用户流程覆盖率。

### 5.4 Human Verification (HVR)

以下人工验收在重构前基线及各 UI 相关阶段分别执行；验收人按真实普通用户或配置管理员角色操作。HVR 记录浏览器、用户角色、视口、结果和截图/证据索引；自动化通过不能替代人工签署。

| HVR ID | 人工验收场景 | 通过标准 |
|---|---|---|
| HVR-001 | 打开 Search Workspace | 用户看到当前版本 Workspace，区域顺序及初始状态符合基线。 |
| HVR-002 | 输入关键词并搜索 | 用户看到与基线一致的状态、条件摘要和结果。 |
| HVR-003 | 选择/取消 Resource | 标签选择、结果和 Resource Count 与基线一致。 |
| HVR-004 | 添加/编辑/删除条件 | 控件状态、验证提示和 Query Understanding 一致。 |
| HVR-005 | 使用日期和状态筛选 | 日期边界、时区、状态选择、错误及清除行为一致。 |
| HVR-006 | 浏览 Count 和分页 | 总数、每页条数、页码摘要和切页结果一致。 |
| HVR-007 | 查看卡片并打开记录 | structured/legacy 卡片语义和目标 Odoo 表单导航一致。 |
| HVR-008 | 检查部分失败、无结果及请求错误 | 用户提示、错误态和部分结果保持基线。 |
| HVR-009 | 检查权限边界 | 普通用户看不到无权记录、字段、Count 或配置操作。 |
| HVR-010 | 检查本地化 | 代表性启用语言及用户时区下的文案和日期行为不变。 |
| HVR-011 | 检查响应式布局 | Desktop、Tablet、Narrow 无横向溢出；布局和区域顺序一致。 |
| HVR-012 | 检查键盘交互 | Tab/Enter/Space/Escape 等既有操作保持，搜索不产生写请求。 |

### 5.5 Performance Soft Gate

- 仅测量本次重构直接影响的 Workspace 页面就绪和客户端结果渲染；不开展 NFR-001 全规模负载/容量测试，不做性能优化。
- 同一 `odoo18ce` 环境、fixture 标记、浏览器版本、视口、网络条件和缓存策略下，预热后重复 30 次并记录 P95；测试 fixture 必须按 §0 规则清理。
- 软预算：Workspace 页面从导航开始到 `[data-testid="global-search-workspace"]` 可见，P95 ≤ 1,000 ms；收到 Search response 到结果列表完成更新，P95 ≤ 500 ms。
- 每阶段还须与阶段 1 相同指标对比；P95 回退超过 10% 或超过上述绝对软预算时，记录为性能警告并停止阶段关闭，提交用户评审。若阶段 1 基线本身超过绝对软预算，也须先由用户确认适用目标或偏差，不能重置基线掩盖。
- 上述数值是 CC-018 的重构软闸门，不改变或替代 SRS NFR-001 / TDD 性能要求；不得据此修改搜索负载、Count、超时或降级语义。

## 6. Workspace HTML Extraction

- 将 Workspace 页面标记从 `GlobalSearchController.workspace()` 中抽出到独立的 Odoo QWeb 模板，建议文件为 `mymodules/wd_global_search/views/workspace.xml`；路由继续由当前认证用户的 Workspace controller 提供。
- 控制器继续负责获取当前用户可见的 Resource 描述、配置版本、用户时区和既有配置错误，并通过 QWeb 的正常转义上下文传值。不得把不可信值拼接为原始 HTML。
- QWeb 模板仅表达页面标记，不执行 Search、不读取业务记录、不引入新的数据访问或权限路径。
- 保持 `<html>` / Workspace / header / query / resources / conditions / refinements / understanding / results / pagination 的节点层级与先后顺序；保留所有现有 ID、class、ARIA、`data-testid`、标签、默认值和静态文案。
- 保持 `<html lang>`、当前英文静态文案、配置 Resource 的语言翻译、用户时区、日期输入语义及错误信息完全不变。不新增或改写翻译项。
- 保持 CSS/JS 路径、query string、Content-Type、状态码、缓存语义和认证边界不变。
- 对动态 Resource 按原有顺序输出；序列化的状态、字段描述、版本、时区和标签须在 HTML attribute/text context 中安全转义一次。
- 如果 QWeb 引入自动翻译、额外页面包装、DOM 节点或响应头差异，必须在阶段 2 修正或停止，不得通过放宽基线接受差异。

### 6.1 QWeb 模板测试

- 单元/模板测试：以受控 Resource 描述、配置版本和时区渲染 QWeb，断言动态文本与 attribute 的转义、节点顺序、ID、class、ARIA 和 `data-testid`。
- Controller 集成测试：以认证用户请求 Workspace 路由，断言调用 QWeb 后的状态码、Content-Type、页面文案和动态 Resource 输出。
- 对比方式：与阶段 1 基线比较 normalized DOM、可见文本及 HTTP 响应；原始 HTML 中不相关的空白可规范化，但不可忽略标签、属性、文案、响应头或状态差异。
- 对应测试：CC-TEST-024；同时运行 CC-TEST-001～012。QWeb 单元/集成测试不能替代浏览器验证。

## 7. `controllers/main.py` Split

### 7.1 职责边界

| 职责 | 当前路由/方法 | 建议文件职责 |
|---|---|---|
| Workspace 页面 | `GET /wd_global_search`、`workspace()` | `controllers/workspace.py`；只组合已发布 Resource 描述并呈现 QWeb。 |
| Search API | `POST /wd_global_search/api/search`、`search()`；`POST /wd_global_search/api/cancel`、`cancel()` | `controllers/search_api.py`；保留 SearchService 使用方式、request parsing、错误映射和 response schema。 |
| 配置页面与生命周期 API | `/wd_global_search/card_templates`、`descriptor`、`records`、`preview`、`check`、`save`、`apply` | `controllers/configuration.py`；保留配置管理员校验、请求验证、CSRF、ORM 权限和生命周期次序。 |
| Preview 与导航 | `/wd_global_search/api/preview`、`/api/form_url`、`/open_result` | `controllers/navigation.py`；保留只读 Preview、用户权限和已配置 Form Action 路径。 |

### 7.2 拆分规则

- 一个路由族一个清晰的 Controller 模块；通过 `controllers/__init__.py` 显式导入，使 Odoo 路由注册确定。
- 保留所有实际 URL、HTTP/RPC route type、`auth`、HTTP method、CSRF 设置、参数名、状态码、Content-Type、response key 和错误 code。
- 保留 `GlobalSearchController` 当前构造/共享的 Search Service、限流状态、预览 token 限制及安全检查语义；不得因复制类或模块变量而产生多个不一致实例。
- 仅移动 cohesive 的辅助函数到其唯一消费者模块或现有 service；禁止为拆文件引入新通用 Controller 基类、Repository 或 Service 层。
- Route 装饰器、CSRF、认证或 import 任一项无法通过浏览器/API 回归等价证明时，停止阶段 3。

### 7.3 路由注册与接口测试

- 单元/注册测试：启动 Odoo registry 后确认当前路由集合已注册，无遗漏、冲突或重复。
- Controller 集成测试：对 §7.1 每个现有 route family 发出认证/未授权请求，核对 URL、route type、method、`auth`、CSRF、状态码、response schema、权限结果和错误 code。
- 比对 Search/Cancel、模板 Designer 生命周期、Preview/导航的 API 响应及权限/错误行为与阶段 1 基线。
- 对应测试：CC-TEST-025；完整运行 CC-TEST-001～012。API 调用测试不得绕开用户流程验收。

## 8. `preview.js` Split

### 8.1 职责边界

- 保留 Workspace 页面入口 `/wd_global_search/static/src/js/preview.js`；不得拆动 Template Designer 页面脚本。
- 按单一职责拆分当前 IIFE 内的代码：页面入口与事件绑定、条件/日期/关键词、Resource 描述与配置版本协调、Search API、结果卡片/导航及分页。
- 配置生命周期仅指 Workspace 对已发布 `config_version`、Resource 描述、Search 请求响应和不再受支持条件的现有同步行为；不扩展为管理配置的前端状态机。

### 8.2 建议边界与约束

| 模块职责 | 允许承载的行为 |
|---|---|
| Workspace entry/bootstrap | 发现必需 DOM、创建单一页面状态、初始化并注册事件。 |
| Conditions/refinements | 字段和值校验、keyword/structured/date/state 表现和 Query Understanding；不重写其语义。 |
| Resource/configuration state | Resource 选择、已发布描述、Count、配置版本变化和无效旧条件处理。 |
| Search API adapter | 既有同源 Search 请求、竞态序号、响应状态和错误传递；不得更改请求 schema、URL 或重试语义。 |
| Results/navigation/pagination | 卡片 DOM、只读导航和现有分页 UI；不改变 Count 或结果身份。 |

- 保持单一状态所有权及明确模块依赖；避免循环依赖、散布式全局变量、重复事件绑定或复制请求状态。
- 不增加前端框架、打包器、第三方运行时依赖、全局事件总线或新的 API。若所需模块加载机制不兼容 TDD §7.4 的浏览器范围，停止并评审，不可缩减目标浏览器。
- 保留现有入口 URL、请求时机、请求顺序、payload、竞态/旧响应丢弃、DOM 安全写入方式、可访问性和错误文案。
- 结构拆分不得重排或改样式；CSS 变更不在本阶段范围，除非正式评审批准。

### 8.3 JavaScript 模块加载测试

- 单元测试：每个新模块可被入口稳定加载，职责接口输入/输出明确，无循环依赖或重复事件注册。
- 集成测试：Odoo 提供 Workspace 入口及全部依赖 JS 文件，模块调用和初始化顺序正确。
- Playwright：CC-TEST-001～012 在 Chromium、Firefox、WebKit 通过；CC-TEST-020 浏览器/视口 smoke 与 CC-TEST-026 模块加载全部通过；浏览器控制台无未处理异常或资源加载失败。
- Safari 由真实 Safari 人工执行 §5.4 HVR；不能以 WebKit 自动化结果替代。

## 9. `models/configuration.py` Split

### 9.1 职责边界

仅按既有 ORM 模型边界、配置生命周期和关联职责移动定义。可采用以下候选分组，实施前须在阶段 IHR 中确认实际依赖顺序：

| 候选模块 | 现有模型 / 职责 |
|---|---|
| `models/configuration_lifecycle.py` | Mutation Mixin、Configuration Domain、Configuration Version；暂存、Validate、Apply、Publish、Retire、Snapshot checksum 和审计触发。 |
| `models/business_resource.py` | Business Resource；Resource 校验、模型映射关联、导航快照及结果卡片/Resource Snapshot 配置。 |
| `models/resource_mapping.py` | Resource Model Mapping、Searchable Field、Relation Path、Business Date Mapping、State Mapping、Snapshot Field。 |
| `models/configuration_policy.py` | Vocabulary Entry、Entity Scoring Config、Performance Config。 |
| `models/audit_event.py` | Audit Event 模型及审计字段/验证。 |

若经过代码依赖检查发现上述候选组会引入循环 import、改变 registry 顺序或拆出不稳定抽象，应减少文件数量并保留 Odoo 原生模型结构；不为达到文件数量而拆分。

### 9.2 ORM 与持久化不变量

- 保持每个 `_name`、字段名与类型、关系方向、`ondelete`、默认值、compute/inverse/constraint、SQL constraint 名称、表/关系表、模型访问权限及 security rule 完全不变。
- 保持 `models/__init__.py` 注册顺序及模块安装/升级加载行为；所有模型仍由 Odoo ORM 注册，不引入额外持久层。
- 保持 `ConfigurationMutationMixin`、Draft/Published/Retired 生命周期、Pending Changes、Apply/Publish 验证、checksum、Snapshot、审计动作和通知错误语义不变。
- `BusinessResource.init()` 中既有初始化行为只能在其现有模型定义中等价保留；不得手动运行、扩展、改写或新增直接 SQL。若必须改动该行为才能拆分，立即停止评审。
- 不增加字段、迁移、`sudo()`、superuser/admin 环境或记录规则例外；测试通过 Odoo 正常模型 API 和权限用户执行。

### 9.3 模型注册与升级测试

- Registry 测试：确认所有原模型 `_name`、字段名、字段类型、关系、方法入口和 ACL 仍可由 Odoo registry 正常访问。
- ORM 集成测试：分别验证 Domain/Version、Business Resource、mapping、Snapshot、policy 和 Audit 模型的现有读写/校验/权限行为。
- 安装/升级测试：在 `odoo18ce` 经 Odoo 应用层执行模块安装/升级验证；不得改变既有已发布配置或业务记录，并验证配置快照、审计和旧数据兼容。
- Schema/关系测试通过 Odoo ORM metadata 和模块测试断言，不直接查询或写入数据库。
- 权限/审计测试：以正常授权用户验证模型 ACL、约束失败语义和 Audit Event；不得使用 superuser 绕过边界。
- 对应测试：CC-TEST-027；任一模型注册、字段 metadata、权限或升级差异均阻止阶段关闭。

### 9.4 Migration and Compatibility Strategy

- 不新增数据库迁移、字段或 schema 变更；纯文件拆分不要求修改现存配置。
- 既有 Published Snapshot 保持可读取；`card_template`、`snapshot.rendered_text` 和 `snapshot.fields` 继续由现有兼容路径消费。
- 不自动转换 legacy/structured 配置，不自动 Apply/Publish/Retire，不要求为重构重新发布配置。
- 配置生命周期只能通过正常授权用户对专用临时 Draft fixture 执行既有 Odoo ORM action 测试；不得 Publish/Apply 至既有配置，也不得修改共享业务数据。
- 若发现需要迁移数据或改写 Snapshot schema，超出本 CC，按 §13 停止。

### 9.5 Logging Boundary

- 不新增日志事件、不改变日志级别、采样、字段或审计行为；日志契约继续以 CC-008 和当前白名单为准。
- 重构不得将 Raw Query、字段值、模板原文、Record Rule、cookie、token 或认证状态写入日志、trace 或截图。
- 不在本 CC 中扩展 request_id、config_version、resource、latency 等日志字段；如发现缺失或确需变化，单独评审，不随文件拆分附带修改。

## 10. Invariants

以下不变量对全部阶段冻结：

1. **CC18-INV-001：不改变外部行为。** 页面、路由、响应、用户流程和资源加载的可观察行为保持重构前一致。
2. **CC18-INV-002：不改变搜索语义。** Query、条件合并、Refinement、匹配、排序和结果身份保持不变。
3. **CC18-INV-003：不改变权限边界。** 当前用户、ACL、Record Rule、字段权限、多公司和配置管理边界不放宽。
4. **CC18-INV-004：不改变 Count。** 总数、Resource Count、去重和权限过滤后的计数含义不变。
5. **CC18-INV-005：不改变分页。** Page size、offset/cursor、顺序、切页边界和结果身份不变。
6. **CC18-INV-006：不改变错误行为。** HTTP 状态、RPC 状态、错误 code、可见提示和失败关闭行为不变。
7. **CC18-INV-007：不修改 SRS / TDD / 既有 CC。** 冻结上游文件只读。
8. **CC18-INV-008：不引入新架构。** 不新增层、服务、通用框架、构建平台或持久化机制。
9. **CC18-INV-009：不引入 LLM / 向量检索 / 外部搜索引擎。**
10. **CC18-INV-010：不修改 `odoo/` 或官方 `addons/`。**
11. **CC18-INV-011：每个阶段独立验证。** 每阶段都需运行自己及适用的既有回归。
12. **CC18-INV-012：每个阶段独立关闭。** 未关闭的阶段不得计入已完成或并入后续阶段。
13. **CC18-INV-013：先测试，再重构。** 重构前先在阶段 1 冻结 Playwright 回归基线。
14. **CC18-INV-014：UI 回归测试是其他阶段前置。** UI 自动化未通过并关闭前，禁止开始任何结构拆分。
15. **CC18-INV-015：不改变本地化。** 文案、翻译选择、日期时区呈现和用户语言行为均保持不变。
16. **CC18-INV-016：临时测试用户仅可按获批的 v1.2.0 例外创建。** 仅使用唯一标记的新用户、当前 Odoo 应用权限和既有最小角色组；未获批时 v1.1.0 禁令完全有效。
17. **CC18-INV-017：不使用固定或共享测试密码。** 凭据仅在进程内短暂存在；认证状态按敏感本机文件处理，不得进入源码、日志、聊天或 Git。
18. **CC18-INV-018：临时用户及其专用 fixture 必须清理并核验。** 清理失败即停止；不得用 superuser、直接数据库操作或其他权限旁路补救。
19. **CC18-INV-019：测试用户创建不得产生外部通知。** 不发送邀请、邮件或密码重置通知，不触发外部服务。

## 11. Test Matrix

每个测试行须可在本机 `odoo18ce` 环境按 §0 当前已批准版本的 fixture 规则复现。Odoo 模块测试执行入口为 `./venv/bin/python odoo-bin -c odoo.conf -d odoo18ce --stop-after-init --test-enable -u wd_global_search`；UI 命令及环境变量见 §5.1。两者均须由 Odoo 应用层执行，不得使用数据库客户端或裸 SQL；测试串行执行。

| 测试 ID | 验证面 | 执行方式 | 可执行通过标准 |
|---|---|---|---|
| CC-TEST-001 ~ 012 | UI 回归测试 | Playwright Chromium、Firefox、WebKit；按 §5.3 逐项执行 | 12/12 流程在基线和每阶段代码通过；记录浏览器版本及证据。 |
| CC-TEST-013 | 现有测试回归 | Odoo `--test-enable` 运行模块现有 TransactionCase | 所有既有测试通过；不得跳过、隔离或删除失败测试来制造通过。 |
| CC-TEST-014 | 搜索语义回归 | 现有 Search Service、条件和请求边界测试 + UI 搜索场景 | 同一受控输入的状态、有效条件、结果身份和顺序与基线一致。 |
| CC-TEST-015 | 权限边界回归 | 既有 Permission Boundary/Navigation 测试 + Playwright 普通用户/配置用户 | 记录/字段/Count/配置可见性无额外泄露或提权。 |
| CC-TEST-016 | Count 回归 | 既有 Result Identity/Count 测试 + UI | `counts.all`、`counts.by_resource`、页面摘要与基线逐项相同。 |
| CC-TEST-017 | 分页回归 | 既有 Search/Pagination 测试 + UI 首页、尾页、page-size 流程 | `offset`/cursor、page size、页面摘要和结果身份一致，无重复/漏项。 |
| CC-TEST-018 | 错误行为回归 | 既有 Request Boundary/Error Aggregator 测试 + UI 部分失败/错误 fixture | 同输入保持 status、错误码、重试属性及用户提示；不产生成功形回退。 |
| CC-TEST-019 | 配置测试回归 | 现有 Configuration/Template/Upgrade 测试 + 配置管理员 Playwright 流程 | Draft/Apply/Validate/Publish/Retire、Snapshot 和权限结果一致。 |
| CC-TEST-020 | 浏览器兼容性 | Playwright Chromium、Firefox、WebKit，桌面/平板/窄屏；Safari 最新版人工 HVR | Desktop 的 MUST UI 场景及全部矩阵单元 smoke 无 JS 错误、布局溢出或行为差异；WebKit 不冒称 Safari，Safari 必须有独立人工证据。 |
| CC-TEST-021 | 本地化及时区 | Odoo 现有 i18n/timezone 测试 + Playwright 代表性已启用语言 | 资源翻译、日期和时区呈现与重构前一致。 |
| CC-TEST-022 | 只读/写请求边界 | Playwright 检查 Workspace 搜索流的请求；管理流程单独检查已授权写入 | 搜索/Preview/导航不产生写 RPC；配置写操作只由授权管理流程触发。 |
| CC-TEST-023 | 重构性能软闸门 | Playwright 30 次预热采样；按 §5.5 比较导航就绪与结果渲染 P95 | 两项不超过软预算，且相对阶段 1 回退不超过 10%；超出时保持 OPEN 并请求评审。 |
| CC-TEST-024 | QWeb 模板渲染与 HTTP 输出 | Odoo 模板测试 + Controller `HttpCase` + normalized DOM/text/HTTP 基线对比 | 转义、节点/文案、状态码、Content-Type 和响应内容保持等价。 |
| CC-TEST-025 | Controller 路由注册与端点契约 | Registry 路由检查 + 认证/未授权 `HttpCase` + Playwright | 路由无遗漏/冲突；URL、认证、method、CSRF、权限、状态码、错误和 response schema 与基线一致。 |
| CC-TEST-026 | JavaScript 模块加载与初始化 | 静态依赖检查 + Playwright 三引擎浏览器加载/console 检查 | 所有入口依赖成功加载；无循环依赖、重复绑定、未处理异常或资源错误。 |
| CC-TEST-027 | ORM 模型注册、schema metadata 与升级 | Odoo registry/ORM 测试 + `odoo18ce` 模块安装/升级 | 模型/字段/关系/权限/审计和旧配置行为与基线一致；不使用直接 SQL 断言，不修改既有发布配置或业务记录。 |
| CC-TEST-028 | 临时测试用户生命周期 | 通过正常 UI/ORM 创建四类最小权限角色、执行角色场景并清理 | 角色映射符合既有权限；仅本轮临时用户及专用关联 fixture 被清理；ORM 核验唯一标记计数为零；无权限定义/既有用户/公司变更、外发通知或凭据泄露。 |

阶段 1 需建立完整的 §5.3 自动化用例；未被 Playwright 覆盖的服务端约束仍由现有 Odoo 测试覆盖，不得用浏览器用例替代。

## 12. Regression Requirements

### 12.1 CC-001 ~ CC-017

所有既有契约及对应测试均为回归边界。至少按下表逐项追踪，并在每阶段 ATR 中记录实际运行命令、结果和未运行项：

| 契约 | 必须保留的回归行为 |
|---|---|
| CC-001 | 配置基础模型、可见性及配置数据解释。 |
| CC-002 | Search Service 请求/响应、资源执行和结果聚合。 |
| CC-003 | 当前用户权限、字段过滤和多公司边界。 |
| CC-004 | Preview 加载、只读行为与失败状态。 |
| CC-005 | Search Workspace、Query 与 Refinement。 |
| CC-006 | 搜索索引/性能设计和现有性能预算，不借重构改变查询路径。 |
| CC-007 | 错误分类、部分成功及错误呈现。 |
| CC-008 | Audit/observability 事件、日志白名单和 request id。 |
| CC-009 | 语言、用户时区、日期与周起始语义。 |
| CC-010 | 安装、模块升级、旧 Snapshot/配置兼容。 |
| CC-011 | 既有验收状态、通过标准和最终用户流程。 |
| CC-012 | Resource Selector、Facet/Resource Count 和排除规则。 |
| CC-013 | 结果身份、原生表单导航和权限变化处理。 |
| CC-014 | 纯文本 Result Card Template、格式化、escaping 和错误。 |
| CC-014-1 | 多层 relation path、One2many loop 和深度限制。 |
| CC-014-2 | 多层 searchable field、字段授权及条件映射。 |
| CC-015 | 多条件解析/组合、同字段 OR 与跨字段既有语义。 |
| CC-016 | 条件选择器、值控件、Query Understanding、键盘及提示行为。 |
| CC-017 | Workspace 区域顺序、折叠状态、视觉规则和响应式布局。 |
| CC-017-1 | Structured/legacy card schema、独立 DOM、权限及兼容输出。 |

### 12.2 TD-001

TD-001 Search Request Boundary Hardening 保持不变：请求形状、类型、范围限制、非法输入处理、错误关闭及现有边界测试必须通过。Controller 路由拆分不得把参数校验移出既有边界或创建绕过路径。

## 13. Stop Conditions

出现以下任一情况，立即停止当前阶段，不得以“纯重构”为由继续：

1. 需要修改 SRS、TDD、CC-001 ~ CC-017、CC-014-1、CC-014-2 或 CC-017-1。
2. 需要引入新架构、框架、构建系统、服务层、Repository、消息总线或额外持久化机制。
3. 需要引入 LLM、向量检索、Elasticsearch、OpenSearch 或外部搜索服务。
4. 需要 `sudo()`、superuser、admin environment、绕过 ACL/Record Rule 或直接数据库读写。
5. 需要修改 `odoo/` 或官方 `addons/`。
6. 任何变更超出 §3 范围，或触及未被本 CC 授权的文件/行为。
7. 拆分需要新的外部 API、路由、响应 schema、模型字段或迁移。
8. 结果显示搜索语义、权限边界、Count、分页、错误行为或本地化有任何差异。
9. 阶段 1 Playwright UI 基线无法建立、不可重复或无法覆盖 §5.3 MUST 场景。
10. UI 自动化覆盖低于 §5.3 的 12/12 门槛，或某浏览器/视口存在未解释失败。
11. HTML/QWeb 提取导致 DOM、文案、资源顺序、escaping、Content-Type 或状态码变化。
12. Controller 拆分改变 `auth`、HTTP method、CSRF、路由注册、权限校验或错误映射。
13. JavaScript 拆分导致共享状态重复、事件重复、竞态差异、未捕获异常或新增全局/构建依赖。
14. ORM 模型拆分造成 registry 顺序、字段/关系、发布生命周期、审计或模块升级差异。
15. TD-007～TD-011 的正式定义与 §17 暂定映射冲突，或其目标要求超出当前范围。
16. 任一阶段的既有回归失败、需跳过测试或只能通过修改基线快照掩盖。
17. 性能指标超过 §5.5 的软闸门且未取得用户偏差批准，或阶段 1 性能基线未被记录。
18. 临时测试用户创建或使用不符合 CC18-INV-016～019 与 §0 v1.2.0 控制。
19. 临时用户创建需要当前普通用户无权执行的操作，或需要 `sudo()`、superuser、admin environment 或权限旁路。
20. 需要新增/修改 Group、ACL、Record Rule、既有用户、既有公司定义或既有用户的组/公司关系才能建立测试角色。
21. 无法证明临时用户只使用最小必要的既有组/公司访问，或角色与现有权限契约不一致。
22. 用户创建会发送邮件/邀请、触发外部通知，或无法确保认证凭据和状态安全保存。
23. 临时用户、关联 fixture 或认证状态无法在本轮结束后安全清理和核验。
24. 清理被引用关系或 Odoo 约束阻止；不得强制删除、绕过 ORM 或遗留后继续下一阶段。

## 14. Definition of Done

CC-018 只有在以下条件全部满足后才可判定完成：

- [ ] 阶段 1 的 Playwright 测试、12/12 覆盖、浏览器/视口与可重复数据基线已冻结，并有用户 HVR 验收。
- [ ] Workspace HTML 已从 controller 抽出，DOM、文案、本地化、资源输出和 HTTP 响应保持等价。
- [ ] `controllers/main.py` 按批准职责拆分；实际路由与权限/错误/响应契约不变。
- [ ] `preview.js` 已按职责拆分；Workspace 行为、配置版本同步、Search、结果、Count、分页、导航和错误保持不变。
- [ ] `models/configuration.py` 已按模型/生命周期/职责拆分；模型 schema、数据、权限、发布、审计和升级保持不变。
- [ ] CC-TEST-001～027 中适用测试通过；所有既有模块测试通过；所有未运行测试明确列为 OPEN，不得声称通过。
- [ ] CC-TEST-023 已在相同环境比较阶段 1 与最终基线；达到 §5.5 软预算，或已取得明确的性能偏差批准。
- [ ] CC-001 ~ CC-017、CC-014-1、CC-014-2、CC-017-1 与 TD-001 回归记录完整。
- [ ] 五个阶段分别具备实施记录 IHR、自动化报告 ATR 和 UI 人工验收记录 HVR，并分别关闭。
- [ ] 没有修改冻结上游文档、官方代码、数据库 schema 或本 CC 以外的业务行为。
- [ ] 若 v1.2.0 获批并创建临时测试用户，所有用户、专用关联 fixture 和认证状态均已按 ORM/本机安全规则清理；零遗留已核验。若 v1.2.0 未获批，不得创建临时用户。

阶段性完成不等于 CC-018 整体完成；任一阶段未关闭时，后续阶段不得开始。

## 15. Decisions

| 决策 ID | 决策 | 理由 |
|---|---|---|
| CC18-DEC-001 | 先建立浏览器侧 UI 回归测试，并以重构前代码冻结基线。 | 缺少现有 Playwright 基线时，无法证明 UI 文件迁移行为等价。 |
| CC18-DEC-002 | Workspace HTML 从 controller 抽出，优先使用 Odoo 原生 QWeb 模板。 | 保留 Odoo 原生转义和模板机制，避免增加新模板引擎；是否影响输出由 UI 基线验证。 |
| CC18-DEC-003 | `controllers/main.py` 按 Workspace 页面、API、配置生命周期及 Preview/导航职责拆分。 | 当前单控制器承载多个不同路由族；保持接口不变即可降低阅读和维护成本。 |
| CC18-DEC-004 | `preview.js` 按页面入口、条件/Resource 状态、Search API、结果/分页职责拆分。 | 保持单一状态所有权和明确边界；不新增前端框架、构建系统或外部依赖。 |
| CC18-DEC-005 | `models/configuration.py` 按 ORM 模型、配置生命周期和职责拆分。 | 文件组织变化不应改变 Odoo registry 模型、发布生命周期或数据 schema。 |
| CC18-DEC-006 | 不改变外部行为。 | 本次是结构重构，不是产品功能变更。 |
| CC18-DEC-007 | 不改变搜索语义。 | 搜索语义只由冻结 SRS/TDD 和既有 CC 定义。 |
| CC18-DEC-008 | 不改变权限边界。 | 当前用户权限是 Search/Preview 安全契约，不因文件移动改变。 |
| CC18-DEC-009 | 不改变 Count、分页或错误行为。 | 这些输出被 UI 与调用方依赖，任何变化都需要独立契约。 |
| CC18-DEC-010 | 每个阶段独立验证、独立关闭。 | 分阶段回归使差异可定位，避免多子系统同时变化后无法归因。 |
| CC18-DEC-011 | CC-018 不进行性能优化，只保持并测量重构前性能基线；采用 §5.5 的软预算。 | 本任务授权文件重组而非性能变更；独立性能优化应另立契约，避免混淆归因。 |
| CC18-DEC-012 | 仅在本地测试库通过正常 UI/ORM 创建、使用、清理带唯一标记的临时测试角色用户。 | 多角色回归需分别验证 reader、fixture writer、restricted 和 config manager 权限；使用临时账号可避免触碰既有用户，但必须受严格作用域和清理控制。 |
| CC18-DEC-013 | 使用逐用户随机的一次性密码，不设硬编码/共享预设密码；凭据只在进程内短暂使用。 | 降低测试凭据泄露和跨运行复用风险，同时允许自动化登录；敏感认证状态不得入库。 |
| CC18-DEC-014 | 临时账号与专用关联 fixture 在本轮结束时全部经 ORM 清理并核验。 | 共享本地数据库必须避免测试用户残留或影响后续业务；任何清理失败均须停止，不得绕权。 |

## 16. Implementation Structure

以下是候选文件组织，不表示必须机械拆成指定文件数。实施者须优先保持简洁、可读和 Odoo 原生模式；如依赖分析要求改变方案，应在对应阶段 IHR 说明理由并确认不违反本 CC。

```text
mymodules/wd_global_search/
├── controllers/
│   ├── __init__.py
│   ├── workspace.py
│   ├── search_api.py
│   ├── configuration.py
│   └── navigation.py
├── models/
│   ├── __init__.py
│   ├── configuration_lifecycle.py
│   ├── business_resource.py
│   ├── resource_mapping.py
│   ├── configuration_policy.py
│   └── audit_event.py
├── static/src/js/
│   ├── preview.js                 # 既有稳定入口
│   └── workspace/
│       ├── conditions.js
│       ├── resources.js
│       ├── search_api.js
│       └── results.js
├── views/
│   └── workspace.xml
└── tests/
    └── ui/
        ├── conftest.py
        ├── test_workspace_search.py
        ├── test_workspace_refinements.py
        ├── test_workspace_results.py
        └── test_workspace_configuration.py
```

现有 `template_designer_page.js`、`template_designer_field.js`、CSS、Search Service 和其他模块保持原位置和职责；除必要的 import/template 注册外，不扩大修改面。

## 17. Appendix

### 17.1 SRS / TDD 追溯矩阵

| 上游 | 相关内容 | CC-018 保留方式 |
|---|---|---|
| SRS FR-SW-001 ~ FR-SW-007 | Workspace、结果 Snapshot、Preview、打开完整记录 | UI、导航和 Snapshot 显示按重构前用户流程验证。 |
| SRS FR-RF-001 ~ FR-RF-009、BR-006 ~ BR-010 | Query Refinement、条件与日期/状态语义 | 条件和筛选用例保留当前输入、状态与结果语义。 |
| SRS FR-PM-001 ~ FR-PM-008、AC-016 ~ AC-019、AC-024、AC-036 | 用户权限、字段/记录隔离及 Count 不泄露 | 真实用户角色、ORM 权限测试和浏览器场景共同验证。 |
| SRS CFG-001 ~ CFG-013、BR-014/BR-015、AC-026/027/032~034/045/046 | 配置模型、发布、Apply、回滚与权限 | 配置模型和 Controller 拆分后使用既有配置测试及 UI 流程验证。 |
| SRS BR-011/BR-013、AC-035/038 | Result Identity、去重 Count 和复合资源计数 | Search/Count/分页结果逐项对比重构基线。 |
| SRS NFR-001 | 搜索与 Preview 性能预算 | CC-TEST-023 仅增加重构相关 UI 软闸门，不替代或修改 SRS 性能基准。 |
| SRS NFR-003/004/005/007、CON-008/009/011 | 安全、可用性、响应式、可维护性、失败关闭和只读边界 | 不削弱原行为；新增文件职责不得扩大运行时风险或权限。 |
| TDD §3.10、§3.14 | 分页、语言与时区 | 对照现有输入/输出和浏览器语言/时区基线。 |
| TDD §12.3 | 性能测试 | 仅执行 CC-TEST-023 重构软闸门；全规模负载基准不在 CC-018 范围内。 |
| TDD §§4–5 | 配置模型与配置版本生命周期 | 保持 ORM 模型、发布、Snapshot、审计及升级语义。 |
| TDD §6 | 权限边界 | 保持当前用户 Environment、字段过滤、失败关闭。 |
| TDD §7、§12.5–12.6 | Preview、浏览器兼容和测试数据 | 使用 Playwright 真实用户流程、受控 ORM fixture；测试环境规则按 CC-018 §0 当前已批准版本执行。 |
| TDD §§9–10 | 错误/部分失败及逻辑接口 | 逻辑接口与当前实际端点映射不变。 |

本 CC 不以重构为由重新判定上游需求是否满足；若发现既有实现与 SRS/TDD 矛盾，按 §13 停止并提交评审。

### 17.2 与 CC-001 ~ CC-017 的接口契约

| 接口面 | 冻结来源 | CC-018 责任 |
|---|---|---|
| Search request/response、结果身份、Count、分页 | CC-002、CC-005、CC-012、CC-015 | 保留 API 输入输出及结果行为；按 CC-TEST-014/016/017 回归。 |
| 权限和 Preview | CC-003、CC-004、CC-013 | 保留当前用户访问及只读导航边界；按 CC-TEST-015/022 回归。 |
| Workspace UI 与日期/条件状态 | CC-005、CC-009、CC-016、CC-017 | 保留 DOM、输入、日期语言、交互顺序及视觉规则。 |
| 配置生命周期 | CC-001、CC-010、CC-014、CC-017-1 | 保留配置模型/模板兼容、Apply/Publish、升级和权限。 |
| 错误与观测 | CC-007、CC-008 | 保留状态码、错误内容、日志安全字段及失败关闭。 |
| 搜索字段、关系与模板输出 | CC-014-1、CC-014-2、CC-017-1 | 保留路径权限、字段集合、structured/legacy response 和 escaping。 |

### 17.3 与 TD-007 ~ TD-011 的对应关系

仓库当前仅包含 TD-001～TD-006，未发现 TD-007～TD-011 的权威定义。因此下表是按本 CC 阶段顺序给出的**候选追溯映射**，不是对现存技术债标题、状态或验收标准的事实陈述。用户于 2026-10-14 批准冻结本版本，候选映射仅用于本 CC 的阶段追溯；不得以候选标题推定未提供的技术债要求。若后续取得的正式 TD 定义与该映射或本 CC 范围冲突，按 §13 停止并评审。

| 技术债 ID | 本 CC 候选对应阶段 | 候选主题（非权威标题） | 冻结前置条件 |
|---|---|---|---|
| TD-007 | 阶段 1 | Browser UI 回归基线 | 核实正式 TD 定义是否为 UI 自动化/回归基线。 |
| TD-008 | 阶段 2 | Workspace HTML 模板提取 | 核实正式 TD 定义及其与 QWeb/静态模板范围的一致性。 |
| TD-009 | 阶段 3 | Controller 职责拆分 | 核实正式 TD 定义与当前路由分组一致。 |
| TD-010 | 阶段 4 | Workspace JavaScript 职责拆分 | 核实正式 TD 定义与 `preview.js` 的范围一致。 |
| TD-011 | 阶段 5 | Configuration ORM 模块拆分 | 核实正式 TD 定义与配置模型/生命周期边界一致。 |

### 17.4 术语表

| 术语 | 定义 |
|---|---|
| 行为等价 | 在相同用户、配置、语言、时区、输入和数据下，可观察 DOM、请求/响应、状态、结果、权限、Count、分页和错误均与冻结基线一致。 |
| UI 回归基线 | 阶段 1 冻结的 Playwright 测试、受控数据、浏览器/视口、语义断言和辅助截图；不是允许产品行为变化的快照。 |
| Workspace | `/wd_global_search` 提供的 Global Search 页面。 |
| 配置生命周期 | Draft、Validate、Apply、Publish、Retire、Snapshot/checksum 和审计等现有配置行为。 |
| 独立阶段关闭 | 单阶段具备自己的 IHR、ATR、HVR 与通过证据；该状态不得替代其他阶段关闭。 |

### 17.5 版本历史

| 版本 | 日期 | 变更 | 状态 |
|---|---|---|---|
| v0.1.0 | 2026-10-14 | 基于 `main @ 09205c7` 起草架构重构执行契约；记录起草核对、分阶段顺序、Playwright 基线、边界、不变量、回归矩阵和待确认 TD 映射。 | Superseded Draft |
| v0.2.0 | 2026-10-14 | 按评审补充版本基线/核对范围、Playwright 配置与证据、Fixture、QWeb/路由/模块/模型测试、迁移与日志边界、HVR/浏览器矩阵、性能软闸门和评审记录。 | Superseded Draft |
| v1.0.0 | 2026-10-14 | 用户批准冻结；授权按 §4 顺序从阶段 1 开始实施，TD-007～TD-011 仅按候选追溯映射处理。 | Superseded by v1.1.0 |
| v1.1.0 | 2026-10-14 | 用户正式批准在本机 `odoo18ce` 执行测试并通过正常 Odoo UI/ORM 创建、清理专用唯一标记夹具；补充禁止触碰既有业务/发布配置、清理失败停止及串行运行规则。未改变 SRS、TDD、既有 CC 或产品行为。 | SUPERSEDED BY v1.2.0 |
| v1.2.0 | 2026-10-15 | 用户正式批准修订：授权通过正常 UI/ORM 创建、使用、清理唯一标记的临时多角色测试用户；规定最小权限、一次性随机凭据、禁止外发通知和失败停止条件。未改变 SRS、TDD、既有 CC 或产品行为。 | APPROVED / FROZEN |

### 17.6 评审记录

| 版本 | 日期 | 评审输入 | 结论 | 治理状态 |
|---|---|---|---|---|
| v0.1.0 | 2026-10-14 | 用户提供的 CC-018 评审文本（评审人署名未提供） | 建议补充版本基线、核对范围、Playwright 配置/证据、模板/路由/模块/模型测试、性能软闸门、兼容策略、fixture、HVR 与浏览器矩阵后进入 Freeze 流程；本修订已纳入适用项。 | 评审建议不等于用户批准；仍为 DRAFT，待用户明确批准冻结。 |
| v1.0.0 | 2026-10-14 | 用户 | 批准冻结并进入实施。 | APPROVED / FROZEN；阶段 1 优先。 |
| v1.1.0 | 2026-10-14 | 用户 | 正式批准修订测试环境要求，使用现有本机 `odoo18ce` 和受控 Odoo UI/ORM 夹具，并重新冻结。 | APPROVED / FROZEN；适用范围与控制见 §0。 |
| v1.2.0 | 2026-10-15 | 用户 | 批准 CC-018 v1.2.0 正式修订并重新冻结，授权在 §0 列明的边界内创建临时多角色测试用户并继续阶段 1。 | APPROVED / FROZEN；阶段 1继续，测试用户仍须遵守最小权限、一次性随机凭据和 ORM 清理要求。 |
