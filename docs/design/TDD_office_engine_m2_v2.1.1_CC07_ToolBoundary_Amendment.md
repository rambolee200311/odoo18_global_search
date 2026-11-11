# Office Engine M2 TDD V2.1.1 — CC-M2-CB-07 Tool Boundary Amendment

| 项目 | 内容 |
|---|---|
| 基线 | `TDD_office_engine_m2_v2.1.0_LLM_Native.md`（Frozen） |
| 修订 | V2.1.1 Amendment 1 — Tool Boundary |
| 适用 CC | `CC-M2-CB-07 — Route B End-to-End Integration & Cross-layer Regression` |
| 状态 | **APPROVED IMPLEMENTATION AMENDMENT** |
| 决策依据 | 负责人明确要求保留独立 `odoo_record_retriever` 与 `office`，并批准冻结 CC-M2-CB-07、进入实施。 |

本 amendment 以版本化增补方式修订 V2.1.0；不覆盖原冻结文件。除以下明确变更外，V2.1.0 全部要求保持有效。

## 1. 修订决议

适用的 Route B Agent Thread 向 Agent 提供两个既有公开工具：

1. `odoo_record_retriever`：只读 Odoo 数据查询，保持既有 `llm.tool.execute()`、当前用户 ORM/ACL/Record Rules/多公司权限、Schema、序列化和 M1 兼容行为。
2. `office`：Office 文件编辑及 Candidate、Accept、Reject、Finalize/Delivery 生命周期入口。Office 不代理 Retriever 查询。

不新增第三个公开工具、查询服务、Snapshot/Incremental 框架或新的业务查询逻辑。Agent 使用 Retriever 的真实工具返回，并按用户意图将所需结果交给 `office(action="edit")`。

## 2. 对 V2.1.0 条款的最小修改

| V2.1.0 条款 | Amendment 后语义 |
|---|---|
| §0.2、§1.1、§1.2 | 将“唯一公开 `office` Tool”改为上述两个既有工具；各自职责保持独立。 |
| §2.1 | Route B Thread 中 Agent 可见 `office` 与 `odoo_record_retriever`；M1 工具可见性和既有调用保持兼容。 |
| §2.2 | 删除 `retrieve` 作为 `office` action 的接口定义；`office` action 集合保留文件生命周期操作，如 `status/plan/edit/accept/reject/finalize`。 |
| §2.3 | 删除“`office(action="retrieve")` 是唯一数据读取入口”；改为 Agent 独立调用现有 Retriever，按其当前用户权限返回数据。 |
| §10 | 工具注册和权限测试覆盖两个既有工具及 M1 兼容性；不新增公开工具。 |
| §11.3 | 后续数据读取由 Retriever 完成，再以当前 Accepted Current 调用 `office(action="edit")`；不增加 Workbook 版本锁作为只读查询前置条件。 |
| §14、§15 | 将“不得额外公开 Retriever”修订为“不得新增第三个 Office/Data 工具”；记录本 amendment。 |

## 3. 不变约束

- Retriever 仍只读并执行当前 Odoo 用户 ORM 权限；不得 `sudo()` 或绕过 Record Rules。
- 真实业务数据外发、Provider dispatch、版本/确认/验证/Finalize 与生产发布门禁均不因本 amendment 自动开放。
- `EXTERNAL_PROVIDER_DISPATCH_ENABLED=False` 仍为默认 fail-closed 状态；测试启用必须遵循 CC-M2-CB-07 §7 的单独授权及受控服务端配置。
- LLM 主导 Office 内容生产；Odoo 保留权限、安全、技术验证、版本、用户决策、审计和交付权威。

