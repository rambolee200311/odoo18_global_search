# 实施历史记录 — CC-LLM-TOOL-002

## 1. 执行元数据

| 字段 | 值 |
|---|---|
| Intent ID | `CC-LLM-TOOL-002` |
| CC | `CC-LLM-TOOL-002_record_retriever_schema.md` v1.0.0 Frozen |
| 模块 | `llm_tool`、`llm_openai` |
| 工作类型 | 缺陷修复 |
| 实施负责人 | Codex（按用户授权） |
| 开始 / 最后更新 | 2026-10-16 / 2026-10-19 |
| 上游代码基线 | `609ec6dda3645165f6a4a843d7af5d286081a29d`；工作树中含先前 CC-OPENAI-001 未提交变更 |
| CC-002 实现提交 | `67baad4a1d3c49b11618d380b8b5bc54ae9abe57` |
| 执行环境 | `venv`、`odoo.conf`、Odoo 18、现有数据库 `odoo18ce`、端口 8091 |
| 当前实施状态 | CC-002 白名单内实现、定向验证及用户确认的人工验收完成；FR-CC-LLM-TOOL-002 判定 CC Closure SATISFIED |

## 2. Coding Contract 基线

| 项 | 引用 |
|---|---|
| Scope | CC §3 |
| 修改白名单 | CC §4 |
| 行为变更 | `CC-CHANGE-001a`、`001b`、`002`、`003` |
| 保留行为 | `CC-PRESERVE-001`–`004` |
| 测试契约 | `CC-TEST-001`–`011` |
| 技术基线 | TDD-LLM-TOOL-002 v1.0.0 Frozen |
| 实施计划 | IMPLEMENTATION_PLAN_CC-LLM-TOOL-002 v1.0.0 Frozen |

## 3. 当前实施状态摘要

| 项目 | 状态 |
|---|---|
| CC-CHANGE 落实 | 4 / 4（限定方法内） |
| CC-TEST-001–009、011 | PASS；最终定向运行 ATR-RUN-003 共 14 个方法，0 failures / 0 errors |
| CC-TEST-010 | PASS；内置浏览器真实聊天工具链成功；UI 模块升级后复验 |
| CC-PRESERVE-001–004 | PASS；含无销售读取 ACL 用户被拒绝和 6 个活动工具前后快照相同 |
| Preservation impact | 活动工具存储 Schema 未改变；formatter 保留无关 Schema；未改权限实现 |
| Deviation | ATR-ISSUE-001：既有 retriever INFO 日志可能记录业务参数，但其 callable 明确在本 CC 白名单之外 |
| Stop condition | 发现了既有日志风险；FR 评估其不阻塞本 CC 关闭。底层风险仍 Open，未修改 excluded file |
| 当前状态 | Implementation Complete; CC closure assessed SATISFIED in FR-CC-LLM-TOOL-002 |

## 4. 实施历史条目（仅追加）

### IHR-001 — 冻结基线及实施前置核验

| 字段 | 值 |
|---|---|
| 时间 | 2026-10-16 08:44 UTC |
| 阶段 | Implementation preparation |
| Action | 按用户授权冻结 CC-002 和实施计划；通过 `odoo-bin shell -c odoo.conf` 对现有 `odoo18ce` 执行只读环境 / 模块核验、Provider-only 前置请求和活动工具 Schema 快照 |
| Reason | 满足 CC 开工门禁并保存实施前证据 |
| Files / Components | CC、实施计划、CC-OPENAI-001 ATR、只读 Odoo ORM |
| Contract Reference | CC §10、`CC-TEST-008` 前置、实施计划阶段 1 |
| Upstream Reference | TDD-LLM-TOOL-002 v1.0.0 Frozen |
| Result | Provider HTTP 200 并返回 `odoo_record_retriever` tool call；当时停止在工具分派前；6 个活动工具存储 Schema 均为空；无数据库写入 |
| Deviation | None |
| Follow-up | 按 CC 白名单实现代码，并用 ATR / HVR 记录验证 |

### IHR-002 — 动态 Schema 生成和 OpenAI 转换修复

| 字段 | 值 |
|---|---|
| 时间 | 2026-10-16 08:50 UTC |
| 阶段 | Implementation |
| Action | 用执行签名共用的 Pydantic 模型生成动态 Schema；对存储 Schema、object 根类型和异常实行受控验证；formatter 失败时移除空 fallback；转换 Schema 使用深拷贝并保持完整 JSON Schema / union 语义 |
| Reason | 修复 TV 确认的 MCP 2.x 导入不兼容、空 Schema fallback 和 `anyOf` 语义损坏 |
| Files / Components | `llm_tool/models/llm_tool.py:get_input_schema()`；`llm_openai/models/openai_provider.py:_openai_format_tool()`、`_recursively_patch_schema_items()`、`_create_openai_tool_from_schema()` |
| Contract Reference | CC-CHANGE-001a/001b/002/003；CC §4 白名单 |
| Result | 动态 Schema 精确要求 `model`，可选参数保留类型 / 默认值；OpenAI formatter 保留 Schema 结构、不修改输入；生成 / 格式错误 fail-closed 并给受控错误 |
| Deviation | None within method whitelist |
| Follow-up | 执行自动化测试和受控 Provider / Browser E2E |

### IHR-003 — 自动化测试、ACL 回归和端到端验证

| 字段 | 值 |
|---|---|
| 时间 | 2026-10-16 09:05 UTC |
| 阶段 | Verification |
| Action | 新增 `llm_tool/tests/test_llm_tool_schema.py` 和 `llm_openai/tests/test_openai_tool_schema.py` 用例；测试缺少销售读取 ACL 的用户会被拒绝；修正第一轮测试桩后，14 个定向测试通过；使用 Odoo UI 分别升级 `llm_tool` 和 `llm_openai`；在 Codex 内置浏览器完成两次成功聊天工具调用 |
| Reason | 按 CC-TEST-001–011 和用户要求验证真实用户流程、ACL、Schema / execute 一致性及用户可见结果 |
| Files / Components | CC §4 白名单内的测试文件；本地 Odoo 模块升级；内置浏览器 LLM Chat |
| Contract Reference | CC-TEST-001–011、CC-PRESERVE-001–004 |
| Result | ATR-RUN-003：14 项 0 failed / 0 error；两个模块 UI Upgrade 返回正常 Odoo 页面；Provider 发起 retriever 调用，Odoo 工具成功，助手返回一条订单摘要。E2E 未验证链接。 |
| Deviation | 发现 `llm_tool_record_retriever.py` callable 的现存 INFO 参数日志与 TDD §15 不一致；该方法在冻结 CC §3.2 / §4 明确排除，没有修改。详见 ATR-ISSUE-001。 |
| Follow-up | 需独立冻结变更明确是否修复 excluded logger；CC-002 不得据此声明完全闭环。 |

### IHR-004 — 人工验收确认及 CC 关闭评估

| 字段 | 值 |
|---|---|
| 时间 | 2026-10-19 |
| 阶段 | Closure assessment |
| Action | 将用户明确声明“人工验收通过”记录到 HVR-RUN-001；基于冻结 CC 与 IHR/ATR/HVR 证据创建 FR-CC-LLM-TOOL-002。 |
| Reason | 完成用户批准的 CC-002 关闭流程，避免将用户确认误写为 Codex 执行的人工测试。 |
| Files / Components | HVR、ATR、IHR、FR；无产品代码变更。 |
| Contract Reference | CC-TEST-010、CC §3.2 / §4 修改范围。 |
| Result | FR 评定合同义务 SATISFIED。ATR-ISSUE-001 的既有 INFO 参数日志和 ATR-RUN-001 的广泛回归错误仍保留为未解决事项；它们未被声称修复。 |
| Deviation | None. |
| Follow-up | 独立处理 ATR-ISSUE-001 及模块级既有回归错误；不改变本次 CC 关闭判定。 |

## 5. 实际变更清单

### 本 CC 白名单内变更

| 文件 / 方法 | 变更 |
|---|---|
| `llm_tool/models/llm_tool.py:get_input_schema()` | 空存储 Schema 时从 execute 共用的签名 Pydantic 模型生成；校验 object 根；所有内部错误包装成稳定 `UserError`；不依赖 FastMCP 1.x 路径 |
| `llm_openai/models/openai_provider.py:_openai_format_tool()` | 调用工具 Schema 生成；异常 fail-closed；不再返回空对象 fallback；日志不附带异常详情 |
| `llm_openai/models/openai_provider.py:_recursively_patch_schema_items()` | 保留兼容方法名，返回深拷贝且不虚构 `type`，不修改 union 节点 |
| `llm_openai/models/openai_provider.py:_create_openai_tool_from_schema()` | 校验 object root / properties / required 后，将完整 Schema 放入 Provider parameters，不重构丢失约束 |
| `llm_tool/tests/test_llm_tool_schema.py` | 存储 / 动态 Schema、非法输入、缺少必填参数、默认值、受限用户 ACL 用例 |
| `llm_openai/tests/test_openai_tool_schema.py`、`llm_openai/tests/__init__.py` | formatter union / immutability、无关工具回归、Provider 参数链、零 HTTP fail-closed、聊天错误脱敏测试 |

`llm_openai/models/openai_provider.py` 同时包含先前 CC-OPENAI-001 的未提交变更；本 CC 只负责上表列出的三个方法，不把同文件其他既有差异归入 CC-002。未修改 manifest、依赖、retriever callable、权限、UI、LLM thread / assistant 或 bridge 模块。

### 实施验证产物

- `ATR-CC-LLM-TOOL-002.md`：自动化运行及 E2E 证据摘要。
- `HVR-CC-LLM-TOOL-002.md`：明确区分 Agent Playwright E2E 与 Human Verification 状态。
- `evidence/ATR-CC-LLM-TOOL-002-PRE-TOOLS.json`、`...-POST-TOOLS.json`：脱敏 ORM 快照。
- `FR-CC-LLM-TOOL-002.md`：基于上述证据作出的关闭评估。

## 6. 偏差 / 停止事件

1. ATR-RUN-001 的 56 项广泛模块运行有 14 errors。3 项属于本 CC 新测试最初用 `MagicMock` 替换 callable 后丢失签名元数据，已修正测试桩并在 ATR-RUN-002 / 003 通过；其余为 CC 外已有并发 / MCP 接口断言错误，原始失败保留于 ATR。
2. `llm_tool_record_retriever.py` 内现存 INFO 参数日志与 TDD §15 的允许日志字段不一致；该方法被 CC 明确排除。实施者未扩展白名单，遗留风险保持 Open；FR 将其评定为不阻塞本 CC 关闭，不表示风险已修复。

## 7. 未决项

- ATR-ISSUE-001：既有 retriever INFO 参数日志仍需独立治理；该 callable 不在 CC-002 白名单内，本 CC 未新增或修改该日志行为，FR 将其列为本 CC closure 的非阻塞遗留风险。
- ATR-RUN-001：模块级并发 / MCP API 断言错误仍未解决，不属于本 CC 定向验收。
- HVR-RUN-001：用户于 2026-10-19 明确确认人工验收通过；具体交互细节未提供，HVR 按用户确认如实记录。

## 8. 交接摘要

冻结 CC-002 白名单内实现和指定验证均完成，自动化、受限 ACL 回归、浏览器工具调用及用户确认的人工验收通过。FR-CC-LLM-TOOL-002 对冻结 CC 的义务作出 SATISFIED 关闭判断。ATR-ISSUE-001 的既有 INFO 参数日志风险及 ATR-RUN-001 的广泛模块测试错误继续保留为 CC 范围外的未解决事项；关闭 CC 不表示它们已修复。
