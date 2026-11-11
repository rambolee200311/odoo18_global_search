# IHR-M2-CB-09 — Fileless Office Generation

## 状态

**IMPLEMENTATION COMPLETE — FINAL ACCEPTED / CLOSED BY OWNER (2026-11-11)**

本记录依据冻结的 CC-M2-CB-09 v0.2 及负责人对 CC-09 上游对齐门槛的明确豁免。SRS、TDD 与 Implementation Plan 未修改。工作区原有其他改动保留。

## 实施摘要

- 在唯一 `office` Tool 增加 `create` action 和 Agent 指引；现有 `edit/accept/reject/finalize` 保持原路线。
- Responses Adapter 支持无输入 XLSX 的创建请求。请求只含自然语言/经授权 Retriever 结果，不伪造输入文件或 input SHA；仍使用已有服务端 Provider gate、限制、Hosted Code Interpreter、下载及最小 XLSX 检查。
- 新增受控 fileless Session 来源标记和创建服务入口。无上传、无 Current 时绑定真实用户指令；现有 M1 上传 Session 创建仍要求真实附件及记录绑定。
- 新增 source-less 初始版本登记、输出附件实际字节/SHA 绑定、typed Validation Receipt、幂等和受控 V1/Current 推进；`PARTIALLY_VERIFIED` 保持原等级并在交付说明中披露。
- fileless 输出复用现有 Finalize/Thread 附件交付。后续 `edit` 从 V1 实际附件读取字节和 SHA，之后仍走 Candidate → Accept/Reject。
- XLSX 无源验证只报告完整性/可读取性事实；缺少源文件时业务完整性与任务完成度保持未验证。

## 变更文件

- `mymodules/odoo-llm/llm_openai/services/responses_adapter.py`
- `mymodules/odoo-llm/llm_openai/tests/test_responses_adapter.py`
- `mymodules/odoo-llm/llm_openai/__manifest__.py`
- `mymodules/office_engine_m2/models/llm_thread.py`
- `mymodules/office_engine_m2/models/office_mapping_session.py`
- `mymodules/office_engine_m2/models/office_mapping_tools.py`
- `mymodules/office_engine_m2/models/office_workbook_version.py`
- `mymodules/office_engine_m2/services/mapping_service.py`
- `mymodules/office_engine_m2/services/workbook_version_service.py`
- `mymodules/office_engine_m2/services/candidate_validator.py`
- `mymodules/office_engine_m2/services/edit_orchestrator.py`
- `mymodules/office_engine_m2/__manifest__.py`
- `mymodules/office_verify/{__init__.py,models.py,service.py,verify.py}`
- `mymodules/office_verify/tests/test_candidate_verify.py`

这些文件处于已有 dirty worktree；列表描述 CC-09 所需接口，不表示其中全部差异都由 CC-09 单独引入。

## 未执行 / 范围外

- 生产部署、生产数据处理：**OUT OF SCOPE**。

## 2026-11-11 集成验收补充

- 测试运行时现有 `odoo18ce` 连接不可用；按本次服务操作授权启动已有 PostgreSQL 16 LaunchDaemon（`launchctl kickstart system/postgresql-16`），未改 PostgreSQL/Odoo 配置。完成模块升级和测试后，使用 `odoo.conf` 启动当前工作区源码的 Odoo 8091，以便在同一已登录 Thread 继续 HVR。
- 按负责人授权，使用现有非生产数据库 `odoo18ce`。运行 `-u office_engine_m2,office_engine_odoo` 并执行两个模块的完整 Odoo 测试集：最终 `tests.result` 为 **240 tests, 0 failed, 0 errors**。模块 `tests.stats` 分别记录 258 与 28，合计与最终结果不同；原因未证实，未将 286 宣称为实际测试数。
- 聚焦回归 `TestEditOrchestration.test_fileless_current_is_used_as_parent_for_next_edit`：**1/1 PASS**，覆盖接受 V2 后解析真实 Current 字节并调用正式 `office(action="finalize")` 服务。
- 实际根因：无源创建所得 Session 可正常登记 V1；当编辑 Candidate V2 被接受后，`_resolve_current()` 仅允许 `version_kind="initial"`，并把后续有效编辑版本误当成不一致绑定。该错误阻断了 Finalize，但没有改变 Current。
- 最小修复：fileless 来源 Session 的 Current 允许为受控 `initial`、`edit`、`restore` 版本；仍要求版本状态为 accepted/finalized、Current 与 Last Valid 相同；根初始版本不能有虚构父版本/输入文件绑定，非初始版本必须有父版本。变更位于 `mymodules/office_engine_m2/services/edit_orchestrator.py::_resolve_current`。
- 新增回归断言位于 `mymodules/office_engine_m2/tests/test_edit_orchestration.py::test_fileless_current_is_used_as_parent_for_next_edit`。未改变 M1 上传 Session 的源文件绑定规则。
- 真实 UI Thread `llm.thread_19720`：OpenAI Responses API + Hosted Code Interpreter 创建 V1；同 Thread 编辑产生 V2 Candidate；用户通过 Agent 正式接受 Candidate 3282；修复后再次经 `office(action="finalize")` 完成交付。V1 → V2 的父子 SHA 一致。
- Finalize 结果：Session 15301，Current/Last Valid 3282，Revision 2，状态 finalized，验证等级保持 `PARTIALLY_VERIFIED`，交付附件 49337，delivery message 116185；Finalize SHA 与 V2 Candidate SHA 相同。
- Odoo Discuss 下载控件触发 `/web/content/49337?...&download=true`，8091 日志返回 **HTTP 200**。内嵌浏览器未暴露本地下载路径；对该同一附件的真实字节只读导出至 Evidence，并以独立 openpyxl/ZIP 检查及 SHA 比对验证。未声称取得嵌入式浏览器的本地下载路径。
- 全程只使用虚构工作簿数据，没有读取或修改任何 Odoo 业务记录。
- 完整执行证据见 [HVR-M2-CB-09.md](HVR-M2-CB-09.md)、[ATR-M2-CB-09.md](ATR-M2-CB-09.md) 和 `evidence/CB-M2-CB-09/`。真实 Provider 成本未单独核实；记录实际 token usage。

CC-09 已提交 `READY FOR FINAL ACCEPTANCE`，本记录不代替负责人最终接受或关闭决定。

## 2026-11-11 补充：真实 Discuss 产品档案 HVR

- 排查 Thread 19915 发现，fileless、无 Attachment/Session/Current 的创建请求在 `llm_thread.py::generate()` 之前未激活 Office；Agent 的 Provider 请求因此没有现有 `office` / Retriever 工具 schema，也没有 Route B Office 指引。M2 `office(create)` 服务和 Provider Dispatch 本身可用，不是配置开关关闭。
- 最小实现：`_office_requests_fileless_workbook()` 识别同一用户的最近文件请求；`generate()` 在原生 Agent 构造请求前激活并绑定现有工具；`_office_is_active()` 对 fileless Session 和后续上下文保持激活；`_office_has_versioned_current()` 识别无源版本链。没有新增 Tool 或数据库模型。
- 使用 Odoo UI 真实执行：Retriever 返回 `product.template` 记录 ID 1–5；Agent 随后调用 `office(action="create")`，真实 Provider 创建文件，登记 V1/Current 并交付 attachment 49900。Current=Last Valid=3369，Revision=1，状态 `PARTIALLY_VERIFIED`。产品查询只读，没有调用产品写入工具。
- 在 Discuss 附件卡实际下载文件并独立校验：XLSX ZIP/openpyxl 读取通过，5 条记录的名称、价格、重量及计数方式与 Retriever 结果逐项一致；SHA 与 Odoo/Provider 回执相同。
- 完整调用、结果、版本、Provider usage 和 SHA 见 [HVR 产品档案补充](evidence/CB-M2-CB-09/HVR-products-discuss-20261111.md) 及 Evidence Index。
- 新增两项回归断言后在 `odoo18ce` 运行 TransactionCase：2 tests, 0 failed, 0 errors。详细日志为 `ATR-fileless-tool-binding-and-current-20261111-rerun.log`。
