# CC-LLM-TOOL-002：记录读取工具的参数 Schema 契约

> 文档版本：v1.0.0
> 状态：Frozen
> Intent ID：`CC-LLM-TOOL-002`
> 模块：`llm_tool`（由 OpenAI 工具 Schema 转换器消费）
> 日期：2026-10-16
> 工作区集成基线：根仓库 commit `55a930fbb234f9b82c4a9a3f6292b8f081ac956a`；嵌套上游代码 checkout `mymodules/odoo-llm` HEAD `609ec6dda3645165f6a4a843d7af5d286081a29d`
> 冻结批准：用户于 2026-10-16 明确批准冻结 CC-002 并进入实施
> 实施计划：[`IMPLEMENTATION_PLAN_CC-LLM-TOOL-002.md`](../implementation/IMPLEMENTATION_PLAN_CC-LLM-TOOL-002.md) v1.0.0 Frozen

## 0. 治理

本文是 `odoo_record_retriever` 参数 Schema 问题的冻结实施契约，授权范围仅限本文白名单及验收要求。用户于 2026-10-16 明确批准冻结并进入实施。实施顺序与门禁见关联 Implementation Plan。现有 Global Search Implementation Plan 不作为本 CC 的实施计划。

本 CC 的唯一技术基线为 [`TDD-LLM-TOOL-002.md`](../technical/TDD-LLM-TOOL-002.md) v1.0.0 Frozen。`llm_tool/OPENAI_SCHEMA_COMPATIBILITY.md` 只是技术资料，不替代冻结 TDD。

## 1. 变更摘要

| 项目 | 内容 |
|---|---|
| Intent ID | `CC-LLM-TOOL-002` |
| 工作类型 | 缺陷调查与修复 |
| 目标 | 修复当前已由 TV 确认的动态 Schema 生成失败、formatter 空 Schema fallback 及 union 语义损坏；用分层证据区分 Provider 参数生成与 Odoo runtime。历史 `{}` 失败的具体归因未知，不作为当前已确认缺陷的修复前置 |
| 与 `CC-OPENAI-001` 的关系 | 本 CC 处理 retriever Schema / 运行时参数链路；`CC-OPENAI-001` 处理 OpenAI Provider 请求兼容性（`reasoning_effort`）。两者可并行诊断。本 CC 实施前须有 `CC-OPENAI-001` 的 `CC-TEST-011` 通过证据；仅当该项因 Provider 环境未就绪而为 `NOT RUN / BLOCKED` 时，项目已知技术负责人可用具名书面记录明确授权本 CC 在缺少该证据时继续。授权须按工作流授权记录格式写入项目级 `docs/implementation/AUTHORIZATION_RECORDS.md`（或项目已指定的受控登记册），标明前置测试原状态、原因、影响、授权人及明确许可范围；不得把测试状态改写为通过。随后 `CC-TEST-010` 必须验证 Provider 请求成功并完成符合 Schema 的工具调用。若前置项为 `FAILED`，不得以此例外放行 |
| 触发证据 | 早先一次 Odoo 对话把 `{}` 传给工具，因缺少必填 `model` 被 `llm.tool.execute()` 拒绝，没有读取记录。用户之后提供的截图显示工具成功执行并返回 3 条采购订单及链接、摘要。失败运行的代码基线和存储 Schema 未记录，不能认定两次运行处于同一运行态。参见 §2.3、`ATR-CC-OPENAI-001.md` §§8.3–8.5、`IHR-CC-OPENAI-001.md` IHR-004 / IHR-005、`HVR-CC-OPENAI-001.md` HVR-RUN-001。当前运行时另有已核实的 Schema 生成缺陷，见 TV 报告。 |

## 2. 基线与追溯

### 2.1 SRS / DDD

N/A。这是现有工具接口的技术兼容性修复，不定义新业务流程或领域模型。

### 2.2 技术设计

本 CC 的技术基线为 [`../technical/TDD-LLM-TOOL-002.md`](../technical/TDD-LLM-TOOL-002.md) v1.0.0 Frozen。该 TDD 定义了：

- 如何捕获生成的 Schema、Provider 请求中的 `tools` Schema、Provider 返回的工具参数，以及 `execute()` 收到并校验的参数。
- 如何区分 Schema 生成缺陷、Provider 参数生成行为和 Odoo 运行时校验缺陷。
- 当前已确认的生成 / 转换缺陷的修复方式，以及 Provider 参数或 runtime 偏差超出设计时的停止 / 重新定界方式。
- Schema 生成或转换失败时的 fail-closed 行为，以及是否阻止 Provider 请求。

本 CC 不得放宽 TDD 的 Schema 保留、fail-closed、受控错误、权限和日志约束。TDD 若发生偏移，必须暂停受影响 CC，并按工作流完成授权、反向生成新 TDD 及计划基线影响复核。

### 2.3 源码观察与运行时证据

- `llm_tool/models/llm_tool_record_retriever.py` 定义 `odoo_record_retriever_execute(model, domain=[], fields=[], limit=100)`；只有 `model` 是必填参数。
- `llm_tool/models/llm_tool.py:get_input_schema()` 优先使用存储的 `input_schema`；为空时当前路径调用 FastMCP 1.x `func_metadata()`，在安装的 MCP 2.x 环境中导入失败。
- `llm_tool/data/llm_tool_data.xml` 未给 `odoo_record_retriever` 提供存储的 `input_schema`。
- `llm_openai/models/openai_provider.py:_openai_format_tool()` 捕获 Schema 格式化异常后，会生成 `properties` 和 `required` 均为空的备用 Schema。这会把生成失败隐藏起来。
- `llm_tool/models/llm_tool.py:execute()` 会独立按方法签名构造 Pydantic 模型并校验参数。即使 Provider 收到空的备用 Schema，空参数仍会因为缺少 `model` 被拒绝。

当前运行时缺陷的具体证据见 [TV-LLM-TOOL-002 Schema 生成核查](../technical/TV-LLM-TOOL-002-schema-generation.md) v0.2 的“结果”表和“只读运行时采集记录”：活动工具的存储 Schema 为空，`get_input_schema()` 在 MCP 2.x 环境因导入路径不兼容报错，实际 formatter 输出空 `properties` / `required`；签名派生 Schema 正确要求 `model`，递归 patch 会改变 `anyOf` 节点语义。本 CC 不重复技术核查，但实施时须在 ATR 中对当前代码基线重新采集适用证据。冻结 TDD 已据此定义修复。历史失败对话的配置和运行基线仍未知，按 ATR 记录，但不阻塞修复当前已确认缺陷。

#### 失败和成功运行对比

| 观察项 | 早先失败：IHR-004 | 后来成功：HVR-RUN-001 | 对比状态 |
|---|---|---|---|
| 时间 | 2026-10-16 约 15:20（上海时间） | 2026-10-16 约 15:30（上海时间） | 已记录 |
| 模型 / Provider | OpenAI `gpt-5.6-luna` | OpenAI `gpt-5.6-luna` | 记录显示相同 |
| Odoo 实例 / 数据库 | 对话界面 URL 为 `127.0.0.1:8091`；数据库未记入 IHR-004 | 本地 Odoo `127.0.0.1:8091`；数据库 `odoo18ce` | 实例 URL 一致；数据库无法对照 |
| 代码基线 | 此 UI 运行未记录 | 记录为 `55a930fbb234f9b82c4a9a3f6292b8f081ac956a` | 无法对照；诊断时补采可取得的信息 |
| 工具状态 | 对话启用了 `odoo_record_retriever`；未保存 `llm.tool.input_schema` | 工具调用成功；未保存 `llm.tool.input_schema` | 无法对照；诊断时只读记录 Schema |
| 模型参数 | 失败验证时设置了 `reasoning_effort="none"` | 截图未包含当时持久化值 | 两次运行设置是否一致未记录；通过 `CC-OPENAI-001` 的 `CC-TEST-011` 前置或经批准的例外后由 `CC-TEST-010` 验证当前请求成功，不能反推历史值 |
| 结果 | Provider 请求了 `{}`；Odoo 校验报告缺少必填 `model`；未读记录 | 工具成功并返回 3 条采购订单 | 结果不同，历史根因未定 |

成功运行不能证明失败在相同代码和配置下不可复现：失败时的代码基线、存储 Schema 和成功时模型参数快照都缺失。实施 ATR 必须按冻结 TDD 的顺序记录 Schema 生成、Provider Schema、Provider 参数和 `execute()` 输入；历史缺失字段标为未知。由于当前 Schema 生成 / 转换缺陷已由 TV 确认，本 CC 不再以追溯历史 `{}` 对话为修复前置，也不得将历史未知推断成已知根因。

## 3. 冻结范围

### 3.1 范围内

- 按冻结 TDD 修复内置 `odoo_record_retriever` 的 Schema 生成和 OpenAI formatter 转换。
- 明确覆盖 `_openai_format_tool()`、`_recursively_patch_schema_items()`、`_create_openai_tool_from_schema()` 的 union 语义保留、非原地转换和 fail-closed 行为。
- ATR 按依赖顺序脱敏记录：`get_input_schema()` 输出 / 失败、Provider `tools` Schema、Provider 工具参数、`execute()` 参数及校验结果；前一阶段失败时后续证据标记不适用，不伪造。
- 历史运行缺失的模型行、Schema、Provider payload 或 commit 记录为未知，不阻塞当前缺陷修复 / 验收。
- Provider 可见函数 Schema 必须表达实际 callable：`model` 必填；`domain`、`fields`、`limit` 可选，并与签名类型和默认值一致。
- Schema 生成或转换错误必须可见，并阻止发送空 fallback Schema。
- 测试模型看到的 Schema 与 `llm.tool.execute()` 接受的参数之间存在明确、可验证关系。
- 实施冻结 TDD 的 `TEST-LLM-TOOL-001` 至 `TEST-LLM-TOOL-011`；使用现有 `odoo18ce` 和用户指定内置浏览器完成获准的受控 Provider E2E。
- 保留 Odoo 当前用户环境和访问检查；本 CC 不扩大模型权限。

### 3.2 范围外

- 修改 `CC-OPENAI-001` 覆盖的 `llm_openai` reasoning-effort 行为。
- 开发 `wd_global_search_llm` 桥接、自然语言搜索计划、导航链接或搜索结果卡片。
- 修改权限、记录规则、`sudo()` 行为或 retriever 通用模型访问策略。
- 修改 creator、updater、unlinker 或模型方法执行工具。
- 声称 retriever 会返回安全导航 URL；当前工具返回的是记录数据。
- 迁移聊天栈到其他 Provider API，或改动无关工具 Schema。

## 4. 变更边界

最终白名单由冻结 TDD 和 CC 确定。下表仅为候选方法 / 数据元素。冻结文件白名单必须精确到方法、函数或单个 XML 记录，不得授权整文件修改。

| 候选路径与方法 / 元素 | 限定用途 |
|---|---|
| `llm_tool/models/llm_tool.py:get_input_schema()` | 移除不可用的 FastMCP 路径；空存储 Schema 时从共用签名 Pydantic model 生成；非法存储 Schema 受控失败 |
| `llm_openai/models/openai_provider.py:_openai_format_tool()` | Schema 生成 / 转换失败时 fail-closed；在 Provider HTTP 前抛受控错误，不返回空 fallback |
| `llm_openai/models/openai_provider.py:_recursively_patch_schema_items()` | 保留 `anyOf` union 语义，不给 union 节点猜测补 `type: string` |
| `llm_openai/models/openai_provider.py:_create_openai_tool_from_schema()` | 不原地改变输入 Schema 语义；不能保留约束时请求前失败 |
| `llm_tool/tests/test_llm_tool_schema.py` | 覆盖 `TEST-LLM-TOOL-001`–`003`、`005`–`007`、`009`、`011` 中适用于工具模型的断言 |
| `llm_openai/tests/test_openai_tool_schema.py`、`llm_openai/tests/__init__.py` | 新增并注册 formatter / provider schema 测试，覆盖 `TEST-LLM-TOOL-004`、`008` 及 Provider 请求零调用断言 |

`CC-TEST-010` 是内置浏览器 E2E，不通过上述单元测试文件执行；在现有 `odoo18ce` 环境运行，执行 / 证据记录位置为本 CC 对应的 ATR 与 HVR，不新增 E2E 测试文件。

不得在本 CC 冻结和实施计划门禁通过前修改候选代码。候选路径不等于全文件授权。`get_pydantic_model_from_signature()`、`execute()`、`llm_tool_record_retriever.py` callable、XML 数据、依赖清单、权限、`llm_thread`、`llm_assistant` UI / API 均不在本次修改白名单内。

## 5. 必需行为

| ID | 当前行为 / 证据 | 预期行为 |
|---|---|---|
| `CC-CHANGE-001a` 分层诊断 | 当前 TV 已确认 Schema 导入失败、空 fallback 和 union 转换损坏；历史两次运行配置不完整 | 按 TDD §14.2 依顺序记录 Schema 生成、Provider Schema、Provider 参数和 `execute()` 输入 / 校验；历史未知写入 ATR，不推断历史因果，也不阻塞已确认缺陷修复 |
| `CC-CHANGE-001b` 缺陷修复 | 生成异常被空 fallback 隐藏；签名可生成正确 Schema；递归 patch 改变 `anyOf` 语义 | 按冻结 TDD 修复 `get_input_schema()` 与 formatter；不得修复未确认的历史原因或扩大到其他 API / Provider 协议 |
| `CC-CHANGE-002` Schema / 运行时一致性 | Provider Schema 与运行时校验分别生成 | 测试证明：(a) Schema 的 `required` 等于 callable 中无默认值的参数；(b) JSON 类型 / nullability 与运行时接受范围一致；(c) 参数省略时使用 callable 默认值；(d) 固定 Schema fixture 精确断言各字段 `description` 与 callable 的字段说明（docstring / annotation，如有；无则不编造）一致，不得承诺 callable 未实现的搜索语义、权限语义或返回字段 |
| `CC-CHANGE-003` 受控错误 | 现有 `_generate_assistant_response()` 捕获异常后经 `_post_error_message()` 将 `str(error)` 显示在聊天中；该通路本身不会自动脱敏异常字符串 | Schema 生成 / 转换层必须在异常离开该层前包装底层错误为不含内部细节的受控文案；不得依赖 `_post_error_message()` 脱敏。HTTP 调用为零；聊天显示不暴露 traceback、文件路径、凭据、完整 Schema 或业务数据，按 `TEST-LLM-TOOL-011` 验证。若既有通路无法满足，暂停并按 TDD 流程修订设计 |

## 6. 保持行为

| ID | 必须保持的行为 |
|---|---|
| `CC-PRESERVE-001` | Odoo 记录访问继续使用调用用户环境，并保留 ACL / record rules |
| `CC-PRESERVE-002` | `odoo_record_retriever` 保持只读，本 CC 不增加写入或审批动作 |
| `CC-PRESERVE-003` | 无关工具的有效 Schema 不变。实施前通过 `odoo-bin shell -c odoo.conf` 只读快照所有活动 `llm.tool` 的 `name`、`input_schema`；ATR 仅记录脱敏后的值长度和 Schema 结构摘要，不记录完整 Schema 内容。实施后对相同记录 / 字段作只读比较并记录结果 |
| `CC-PRESERVE-004` | 缺少 `model` 时不允许静默默认成其他模型 |

## 7. 测试契约草案

以下测试尚未执行。CC 测试编号与冻结 TDD §14.1 编号一一对应；`CC-TEST-008` 另覆盖 CC 的只读 ORM 快照，不改变 TDD 测试含义。

| 测试 ID | TDD 测试 | 场景 | 预期结果 |
|---|---|---|---|
| `CC-TEST-001` | `TEST-LLM-TOOL-001` | 空存储 Schema 时从签名动态生成 | 精确断言 `required=["model"]`、`model` 为字符串、`domain` 为数组且 union 保留、`fields` 为字符串数组、`limit` 为整数且默认 `100`；不依赖 FastMCP |
| `CC-TEST-002` | `TEST-LLM-TOOL-002` | 存储有效 Schema | 存储 Schema 优先且不被动态 Schema 覆盖 |
| `CC-TEST-003` | `TEST-LLM-TOOL-003` | 非法 JSON / 非 object 存储 Schema | 受控失败、fail-closed、不回退空 Schema，Provider HTTP mock 调用为零 |
| `CC-TEST-004` | `TEST-LLM-TOOL-004` | OpenAI formatter 转换数组和 `anyOf` | fixture 的类型、`required`、`items` 和 union 语义不变，不猜测补写类型，不原地修改源 Schema |
| `CC-TEST-005` | `TEST-LLM-TOOL-005` | 签名模型生成函数抛错 | Provider HTTP mock 调用为零；错误不泄露内部细节；测试 patch 实际调用的生成函数 |
| `CC-TEST-006` | `TEST-LLM-TOOL-006` | 缺少必填 `model` 执行工具 | Pydantic 校验先失败；业务搜索 mock 调用为零 |
| `CC-TEST-007` | `TEST-LLM-TOOL-007` | 合法参数、省略可选参数 | 参数通过校验并采用 callable 默认值；当前用户 ACL / record rules 保持 |
| `CC-TEST-008` | `TEST-LLM-TOOL-008` | 无关工具 formatter 回归及 ORM Schema 快照 | 既有无关工具仍能格式化；实施前后 `llm.tool` 名称 / `input_schema` 只读快照符合 preserve 契约 |
| `CC-TEST-009` | `TEST-LLM-TOOL-009` | stub Provider 返回符合 Schema 的参数 | 参数可到达 `execute()` 并通过校验；不访问外部网络 |
| `CC-TEST-010` | `TEST-LLM-TOOL-010` | 内置浏览器端到端读取少量授权记录 | 明确验证 Provider 请求成功且响应包含目标工具调用；脱敏证据只保留参数键、类型、非空状态及 `model` 是否匹配预期，不记录完整值；工具参数符合发出 Schema，执行后返回当前用户可访问的真实数据。若参数空 / 不符合 Schema，归类为 Provider 参数生成行为而非 Odoo runtime 缺陷；不验证链接渲染 |
| `CC-TEST-011` | `TEST-LLM-TOOL-011` | Schema 生成 / 转换失败的聊天错误路径 | monkey-patch `get_input_schema()` 抛出包含测试专用内部标记的异常，经真实 formatter / 聊天错误路径处理；断言聊天只显示受控文案，不含标记、traceback、路径、凭据、完整 Schema 或业务数据，且 Provider HTTP mock 调用为零 |

执行顺序固定如下：

1. 实施代码前先执行 `CC-TEST-008` 的只读 ORM 前置快照。
2. 执行 `CC-TEST-001`–`CC-TEST-009` 自动化测试，其中 `CC-TEST-008` 执行 formatter 回归部分。
3. 执行 `CC-TEST-011` 受控错误注入测试。
4. 最后执行 `CC-TEST-010` 内置浏览器 E2E，并完成 `CC-TEST-008` 的实施后快照比较。

`CC-TEST-001` 至 `CC-TEST-007`、`CC-TEST-009` 是自动化验收；`CC-TEST-008` 包含自动化 formatter 回归和前 / 后只读 ORM 快照；`CC-TEST-010` 使用现有 `odoo18ce` 开发库及用户指定内置浏览器，按授权调用真实 Provider；`CC-TEST-011` 用受控异常注入验证现有聊天消息错误路径。不得将尚未执行的项目标记为通过。

## 8. 安全和数据边界

- 不得新增 `sudo()` 或调用者可传入的 UID。
- 缺少或无效参数必须在业务记录搜索前终止。
- 诊断材料不得记录 API key、完整 Prompt、完整工具参数或业务记录。
- ATR 可记录 Schema 结构、参数字段名 / 类型和校验结果；不保留业务值或完整 Provider payload。
- ATR 提交前由实施者逐项执行脱敏检查，并在记录中确认：无 API key、完整 Prompt、完整工具参数、业务记录、文件路径或 traceback。
- E2E 使用现有开发数据库和当前用户；不创建隔离数据库。

## 9. 停止条件

如果实现需要改 Odoo 权限、添加新的公共工具 API、改变桥接 / 搜索逻辑或替换 Provider 协议，应暂停并修订 TDD / CC。若 Provider 拒绝 `anyOf` union Schema，不得静默将 `domain` 简化为 `list` / `string` 或迁移 Responses API；这些是新的技术决策，须先修订并重新冻结 TDD / CC。如果 Schema 与运行时仍不一致、Provider 拒绝 TDD 规定的 Schema，或修复后当前已确认缺陷仍可复现，应停止并先修订 TDD、重新评估实施范围。如果捕获到的 Provider Schema 与源码生成 Schema 不一致且未被设计覆盖，或 Schema 正确而符合 Schema 的参数仍被本 CC 范围外的 runtime 拒绝，也必须停止并重新定界。若实施期间 TDD-002 被修订（包括 TV 更新引起的设计变更），立即暂停本 CC，复核方法白名单、必需行为和实施计划基线，修订并重新评审 CC 后才可继续。历史 `{}` 对话仍无法归因时记入 ATR，不构成本 CC 停止条件。

## 10. 冻结与开工门禁

- [x] 已检查源码和可观察到的运行时校验错误。
- [x] TDD-002 v1.0.0 Frozen 与 `TV-LLM-TOOL-002-01` v0.2 当前缺陷证据一致；历史归因未知已明确为不阻塞修复。
- [x] 实施计划已覆盖本 CC，准确引用 TDD-002 v1.0.0，并按用户授权冻结。
- [x] 本版方法级白名单、错误语义和验收已由用户批准并冻结。
- [x] 本 CC 已评审并明确冻结。
- [x] 用户已授权进入实施。

实施及关闭 CC 前，ATR 必须按冻结 TDD §14.2 记录适用的分层证据；历史缺失项标为未知，不阻塞当前修复。生产实施仍须满足 `CC-OPENAI-001` 的既有前置：记录其 `CC-TEST-011` 通过证据；唯一例外是 §1 所述、因 Provider 环境未就绪导致的 `NOT RUN / BLOCKED`，并已由具名项目技术负责人按工作流登记册书面授权。`FAILED` 不可用该例外豁免；采用例外时，`CC-TEST-010` 必须完整验证 Provider 成功响应和工具执行链路。

开工顺序：先完成计划阶段 1 的 CC-OPENAI-001 `CC-TEST-011` 严格 Provider-only 验证和实施前快照；前置未 PASS 时不得修改产品代码。此要求不改变 CC-OPENAI-001 的原始 `NOT RUN` 历史记录。除此之外，所有本 CC 测试仍为待执行，不得预先标记通过。

## 附录 A：版本记录

| 版本 | 日期 | 变更 | 状态 |
|---|---|---|---|
| v0.1 | 2026-10-16 | 初稿，将 retriever 参数 Schema / 运行时问题从 OpenAI `reasoning_effort` 修复中拆分 | 草稿 |
| v0.2 | 2026-10-16 | 纳入用户提供的后续成功运行截图；要求先复现并捕获 Schema，再选择修复方案 | 草稿 |
| v0.3 | 2026-10-16 | 增加失败 / 成功运行对比、三段诊断、条件修复 / 不改代码处置、ATR 证据、方法级边界、parity、快照回归、链接责任和与 CC-OPENAI-001 的顺序关系 | 草稿 |
| v0.4 | 2026-10-16 | 合入评审意见，澄清历史未知项、诊断证据、方法职责、故障注入方式和 parity；引用 TDD 草稿及当前 ORM shell 核查 | 草稿 |
| v0.5 | 2026-10-16 | 同步 TDD-002 v1.0.0 Frozen；将已确认 Schema 生成 / 转换缺陷定为修复目标；明确方法与测试文件白名单、11 项验收、历史未知不阻塞及实施计划门禁 | 草稿 |
| v0.6 | 2026-10-16 | 细化三种 formatter 方法与 §3.1 范围对应、E2E 执行和证据位置、TV v0.2 引用、异常脱敏及失败注入方式、字段描述 fixture、全量活动工具快照范围、测试顺序与 ATR 脱敏检查；明确 TDD 更新与 Provider 前置例外的停工 / 授权规则 | 草稿 |
| v1.0.0 | 2026-10-16 | 用户批准冻结；实施计划 v1.0.0 冻结，冻结方法级范围、测试矩阵和开工门禁 | Frozen |
