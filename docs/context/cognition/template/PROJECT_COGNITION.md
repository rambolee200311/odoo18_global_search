# 项目认知

## 1. 项目身份

| 项目 | 值 |
|---|---|
| GitHub 仓库 | `rambolee200311/odoo18_qooling_app` |
| Git Remote | `git@github.com:rambolee200311/odoo18_qooling_app.git` |
| Odoo 版本 | `18.0` |
| Python 要求 | `>= 3.10` |
| 共享项目目录 | `/Users/lijianqiang/Documents/odoo18_qooling` |
| 当前文档 Worktree | `/Users/lijianqiang/Documents/odoo18_qooling.worktrees/docs-review-summary` |
| 共享虚拟环境 | `/Users/lijianqiang/Documents/odoo18_qooling/venv` |

Odoo 版本以共享项目目录中的
[`odoo/release.py`](../../../../../odoo18_qooling/odoo/release.py) 为准，并已通过共享虚拟环境实际导入验证。

## 2. 工作目录分层

### 2.1 组织级认知与模板

`docs/context/cognition/` 保存项目需要遵循的工程认知、流程和模板。

其中：

- `template/` 只保存组织级模板；
- 模板不是项目实例文档；
- 模板内容不能被当作当前项目已经完成的需求、设计、测试或验收证据。

### 2.2 项目执行文档

项目实例文档按以下目录保存：

| 目录 | 用途 |
|---|---|
| `docs/context/designing/` | SRS、DDD、TDD 和其他设计阶段基线 |
| `docs/context/intent/` | 需求意图、Coding Contract、实施范围和执行前约束 |
| `docs/context/history/` | 实施历史、自动化测试、人工验证和其他事实证据 |
| `docs/context/report/` | Final Report、项目验证报告和项目收口报告 |

## 3. 权威文档链

项目采用以下文档链：

```text
业务材料
  → SRS
  → DDD（复杂项目按需）
  → Technical Verification（技术不确定性按需验证）
  → TDD
  → Coding Contract
  → Implementation + IHR
  → ATR
  → HVR
  → FR
  → Human Review
  → PVR / PCR（项目级收口）
  → Project Final Review
```

职责边界：

- SRS 定义业务目标、需求、规则、状态和验收；
- DDD 定义复杂领域的概念组织、聚合、权威关系和领域不变量；
- TDD 定义 ORM、服务、Adapter、队列、事务、权限、UI 和技术 Guardrail；
- Coding Contract 冻结单次任务的变更范围和完成条件；
- IHR 记录实际实施事实；
- ATR 记录真实执行的自动化测试；
- HVR 记录真实人类验证；
- FR 判断单次 Coding Contract 是否闭环；
- PVR 汇总项目级验证证据；
- PCR 判断项目级 Closure；
- Human Review / Project Final Review 分别决定 Merge / Release。

## 4. Agent 操作纪律

必须遵守
[`AGENT_OPERATION_PRINCIPLES.md`](../principle/AGENT_OPERATION_PRINCIPLES.md)：

1. 不修改 Odoo 官方核心代码和官方模块；
2. 业务需求通过自定义模块、继承和标准扩展点实现；
3. 不使用 `psql`、裸 SQL、数据库驱动或其他方式直接读写数据库；
4. 数据操作必须经过 Odoo ORM、权限、约束和事务机制；
5. 允许使用共享虚拟环境中的 `odoo-bin shell`，但只能通过 ORM；
6. 批量删除、批量更新、状态回退等破坏性 ORM 操作必须先说明影响并取得许可；
7. 删除任何文件或目录前必须取得用户明确许可；
8. 发生纪律冲突时必须停止、指出冲突、说明替代方案并等待授权。

## 5. Odoo 工程偏好

默认遵循
[`Odoo_Engineering_Guidelines.md`](Odoo_Engineering_Guidelines.md)：

- Odoo Native First；
- 优先使用简单 Model、View、ORM 和 Business Action；
- 核心业务逻辑必须显式存在于模型或业务动作中；
- 避免不必要的 Repository、DAO、DTO、Generic Engine 和额外持久化层；
- 避免过早抽象、复杂元编程和不必要的基础设施；
- 以真实 Odoo Runtime、权限、模块依赖和升级路径为准；
- 技术复杂度必须由真实问题驱动。

## 6. Python、Odoo 和测试命令

命令默认使用共享虚拟环境，不使用当前 Worktree 内不存在的 `.venv` 或 `venv`：

```bash
/Users/lijianqiang/Documents/odoo18_qooling/venv/bin/python
/Users/lijianqiang/Documents/odoo18_qooling/venv/bin/pytest
/Users/lijianqiang/Documents/odoo18_qooling/venv/bin/odoo-bin
```

共享 Odoo 源码、配置和运行入口位于：

```text
/Users/lijianqiang/Documents/odoo18_qooling/odoo
/Users/lijianqiang/Documents/odoo18_qooling/odoo-bin
/Users/lijianqiang/Documents/odoo18_qooling/odoo.conf
```

## 7. E2E 用户模拟规则

项目的 Odoo 浏览器端到端测试遵循
[`odoo-e2e-user-simulation`](../../../../../odoo18_qooling/docs/skill/odoo-e2e-user-simulation/SKILL.md)：

- Python ORM / Server Test 验证服务端业务逻辑；
- QUnit / OWL Test 验证隔离的前端组件；
- Playwright 验证真实 Backend / Portal 用户旅程；
- E2E 必须以用户角色和业务目标为起点；
- 等待业务 UI 就绪，不使用 `networkidle`、固定资源等待或任意 `sleep()` 作为通用规则；
- Save / Submit 后需要重新加载或重新打开验证持久化；
- 优先使用 role、label、text 和稳定 `data-testid` 选择器；
- 自定义 `data-testid` 必须在 TDD 中作为 UI Test Contract 定义；
- 不硬编码任意业务记录 ID，使用隔离 Fixture 或数据驱动导航；
- 弱网络测试需验证用户可见行为，并在使用 CDP 时标注 Chromium-specific；
- 失败时保留 Trace、截图及必要的浏览器证据；
- E2E 不得自行发明业务需求，发现需求或设计问题必须回到上游文档处理。

## 8. 证据纪律

所有验证结论必须来自真实执行：

- 没有执行，不能写 `PASS`；
- 旧代码基线的 PASS 不能自动继承到新代码基线；
- 测试失败历史不能删除；
- Mock / Stub / Sandbox 通过不能宣称真实外部集成通过；
- Agent 不得冒充人工验证者；
- 缺失证据必须明确暴露，不能由报告文档补写或推断。

项目级 Closure 必须区分：

1. Final Project Authority Baseline：最终依据哪个版本的 SRS / DDD / TDD；
2. Final Project Code Baseline：最终验证哪个 Commit / Build。

## 9. 当前认知边界

- 本文件记录的是已经确认的项目环境和工程规则；
- 具体业务需求、领域设计、技术方案和编码任务必须以各自冻结的项目文档为准；
- 不得因为本文件存在就推断某项业务已经实现或某项测试已经通过；
- 新事实、上游基线或目录约定发生变化时，应更新本文件，并保留可追溯性。

## 10. 项目业务目标（需求材料初步认知）

根据
[`Qooling Overview.docx`](../../../../../odoo18_qooling/docs/requirement/Qooling%20Overview.docx)
和
[`QOOLING Instruction.pptx`](../../../../../odoo18_qooling/docs/requirement/QOOLING%20Instruction.pptx)，
本项目的总体目标是：

> 将 PANEX WD Europe 当前在 Qooling 中使用的相关功能迁移并整合到 Odoo，使仓库运营、安全、合规、设备、培训、文件和员工资格管理能够在 Odoo 中持续执行、追溯和维护。

### 10.1 当前识别出的业务能力

- **Forms**：运营登记、周期检查和仓库控制表单；
- **Issues**：问题、损坏、缺陷、事故和异常的登记、跟进与追溯；
- **Procedures**：受控流程、作业指导书和仓库程序；
- **Training**：员工培训计划、培训结果和相关资格；
- **Tools**：设备台账、检查、维护和证书跟踪；
- **Files**：安全、运营和合规文件的集中管理；
- **Registers**：事故、温度、检验、非符合项、SDS、测试报告等结构化登记；
- **Employees**：员工信息，以及培训、证书和有效期监控。

### 10.2 重点仓库流程

需求材料特别指出以下流程需要评估并纳入 Odoo：

- 入库表单（Inbound Form / Goederenontvangst）；
- 出库表单（Outbound Form）；
- 司机登记；
- 作业前安全检查；
- 每日关闭检查；
- 周度温度控制；
- 隔离区温度登记；
- ADR 锂电池抽查；
- 气体测量；
- BIO 产品投诉登记；
- 维修申请和损坏报告。

其中入库和出库流程应重点关注：

- 是否为 BIO 产品；
- 是否涉及 ADR 危险品，尤其是锂电池 `UN3480`、ADR Class 9；
- 入库/出库数量和装载检查；
- 可见损坏及包装问题；
- 重量分布；
- 与司机确认装载计划；
- 车辆 ADR 橙色标志检查；
- 出库装载照片要求。

### 10.3 合规、设备和人员管理要求

- 设备记录至少需要支持类别、标识、检查/维护类型、下次到期日、状态和证书/报告；
- 应能识别即将到期或已逾期的检查，并支持到期提醒；
- 培训和证书需要关联员工，记录类型、签发日期、到期日期和当前有效性；
- 员工资质和证书临近到期时应支持自动提醒；
- 员工个人信息需要基于角色控制访问；
- 文件需要考虑所有者、版本、访问权限，以及与流程、设备、培训和合规记录的关联；
- 登记记录应可搜索，并可关联产品、货物、客户、设备或仓库流程；
- SDS、测试报告等附件应能从相关业务记录中重新获取。

### 10.4 当前范围的治理说明

上述内容是现有 Qooling 功能和业务目标的初步输入，不等同于已经冻结的 SRS。后续必须继续明确：

- 本期迁移范围和明确排除范围；
- Odoo 原生能力与自定义模块的边界；
- 各能力的业务角色和权限；
- 业务状态、流转、阻断规则和异常处理；
- 配置项、提醒策略和数据保留要求；
- Qooling 与 Odoo 的历史数据迁移策略；
- 每条规范性需求对应的验收标准和追溯关系。
