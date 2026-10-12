---
name: odoo-project-workflow
description: "用于遵循 SRS、DDD、TDD、Coding Contract、实施证据和项目收口流程的 Odoo 项目工作。要求在 TDD 冻结后、首个 CC 前完成并基线化 Implementation Plan。"
---

# Odoo 项目工作流

当 Odoo 项目采用仓库中的契约和证据流程时，使用本 skill 进行规划、实施或收口。遵守项目已冻结文档的权威边界，并使用随 skill 提供的对应模板。

术语约定：**冻结**指按对应模板和项目治理流程完成审阅 / 批准，并留下有效的 `Frozen` 状态记录；**基线化**指在计划和追溯中记录该已批准文档的准确版本，供下游引用。不得把 Draft 或未经批准的材料称为冻结基线。本文统一使用“未通过项”指 `Failed / Skipped / Blocked / Missing`；`FROZEN WITH OPEN ITEMS` 是规定的机器可读状态值，其中文说明为“带未通过项冻结”。

## 必需工作顺序

项目实施按以下顺序进行：

1. 在 SRS 中建立已批准的业务基线。领域复杂时使用 DDD。TDD 前仍有重要技术不确定性时，先完成 Technical Verification。
2. 基于适用的 SRS 和 DDD 基线，完成并冻结 TDD。
3. **TDD 冻结后、创建首个 Coding Contract（CC）之前，必须通过下方的 Implementation Plan 门禁。门禁完成前不得创建首个 CC，也不得进入实施。**
4. 根据已基线化的计划拆分边界清晰的 CC。每个 CC 定义一轮实施范围及其完成条件。
5. 实施每个 CC 时持续维护 IHR。将实际自动化测试记录在 ATR；按要求进行人工验证并记录在 HVR。基于 CC 和实际证据编写 FR。
6. 各轮编码工作结束后，使用 PVR 和 PCR 完成项目级验证与收口，再进入 Project Final Review。

如果已有 Implementation Plan，先确认它对应当前冻结的上游版本和预期范围。计划过期或不完整时，先更新并重新基线化，再开始首个受影响的 CC。Draft 计划不得被 CC 或任何下游材料引用为基线。未经实际授权和记录，不得声称计划已获批准或处于 Frozen 状态。

### 首个 CC 前的硬门禁

创建首个 CC 前，逐项检查以下两组。必须项无条件满足；条件项必须先完成触发判断，触发后满足对应要求，不触发时记录判断及理由。

**必须项**

- [ ] **SRS** 已冻结；若权威负责人批准判定为不适用，记录决定和理由，不得由 Agent 自行豁免。
- [ ] **TDD** 已冻结，并对应适用的 SRS / DDD / TV 版本。
- [ ] **Implementation Plan** 已创建、完成所需评审并基线化；准确引用上述冻结文档版本。Draft 计划不得被 CC、实施记录或下游文档引用为基线，也不得据此拆分或创建 CC。
- [ ] **计划阶段映射**完整：每个计划阶段至少映射到一个拟建 CC ID 和范围；每个拟建 CC 也归属于一个计划阶段。首个 CC 创建后将拟建映射回填为实际引用。
- [ ] **未通过项处置**：截至本门禁已有结果或应有证据的测试 / 检查项中，所有 `Failed / Skipped / Blocked / Missing` 项均已记录完整豁免（含有效授权人）并由操作者确认已获授权，或已确认没有未通过项。

**条件项**

- [ ] **DDD 触发判断**已记录：若领域复杂或项目流程要求 DDD，DDD 已冻结并被 TDD 引用；否则记录不触发的判断依据和理由。
- [ ] **TV 触发判断**已记录：若 TDD 前存在重要技术不确定性，TV 已关闭所有适用事项、有结论和获批处置，且没有阻碍 TDD 的未解决不确定性；否则记录不触发的判断依据和理由。不得静默跳过未验证或结论不确定的事项。

该门禁只检查截至当前已有或应有证据，不预判尚未到执行阶段的测试。每个 FR / PVR 冻结仍须再次通过下文的“未通过项豁免门禁”；新产生的未通过项不能沿用此前的门禁结论。豁免不能绕过其他首个 CC 门禁或需求验证。

#### 门禁未通过时

任一项不满足时：

1. 将工作状态明确报告为 `BLOCKED — 首个 CC 门禁未通过`，逐项列出未通过项、证据 / 缺失内容以及负责的上游文档或负责人。
2. **拒绝创建 CC，也拒绝进入实施。** 不生成 CC 空壳、伪造批准 / Frozen 声明，或把未完成项写成已通过。
3. 指明解除阻塞所需的下一步，例如修订并冻结 SRS / DDD / TDD、关闭 TV 事项、补齐计划阶段与拟建 CC 映射，或取得计划批准。
4. 可按用户请求准备标为 `Draft` 的上游材料或计划草稿，但不得让 CC 或其他下游材料引用 Draft 作为基线，也不得据此创建 CC 或开始实施。

如果 TDD 尚未冻结，不得假设技术决策已经确定，也不得创建 CC。先解决上游设计状态。计划可以记录待解决的前置条件，但不能代替 SRS、DDD 或 TDD 决定这些事项。

## Implementation Plan 内容要求

将计划放在仓库已有的实施文档目录中；通常使用 `docs/implementation/IMPLEMENTATION_PLAN_<scope>.md`。如项目已有命名或状态约定，则遵循项目约定。计划至少记录：

- 文档状态、范围、目标，以及准确的 SRS / DDD / TDD / TV 基线；
- 范围内、范围外事项及实施约束；
- 开工所需的前置条件、环境、数据、访问权限和负责人；
- 实施阶段、阶段依赖、交付物和逐阶段验收门禁；
- 阶段依赖图和里程碑；只有具备估算依据时才填写估算；
- 验证策略，包括适用的自动化、ORM、权限、浏览器、性能、迁移和人工验证；
- 风险、缓解措施、未决事项、变更控制和最终交付物；
- SRS 需求及 TDD 约束到实施阶段的追溯，以及每个阶段到一个或多个**拟建 CC ID 和范围**的映射；在门禁通过后回填实际 CC 引用。

计划详略可按项目规模调整，但计划门禁本身不可省略。小项目也需要简明计划，明确范围、验收标准、依赖关系，并在首个 CC 前记录计划状态。Draft 计划只能作为草稿审阅，不得成为下游基线或用于拆分 CC。不得编造日期、批准状态、测试结果或资源承诺。首个 CC 门禁检查的是每阶段已分配的**拟建 CC ID 与范围**；尚未创建的 CC 必须明确标记为拟建，创建后回填实际路径 / ID。

创建计划时使用随 skill 提供的 `references/templates/Planning/IMPLEMENTATION_PLAN_TEMPLATE.md`。`docs/implementation/IMPLEMENTATION_PLAN_global_search.md` 是阶段规划、门禁、依赖和追溯的项目实例；可参考其结构，但不得直接沿用其中的业务范围、假设或环境。

## 权威边界与变更规则

明确区分各文档的职责：

- **SRS** 定义业务需求及验收含义。
- **DDD**（如适用）定义领域概念和不变量。
- **TDD** 定义技术设计和防护栏。
- **Implementation Plan** 编排工作顺序，并定义阶段交付物、依赖、项目准备条件和阶段门禁。它不得创建或修改业务、领域或技术权威。
- **CC** 冻结一轮实施的范围和完成标准，必须追溯到计划及适用的上游需求 / 设计。
- **IHR / ATR / HVR** 记录实施和验证事实；**FR** 评估单个 CC；**PVR / PCR** 负责项目级验证和收口。

如果计划暴露出 SRS / DDD / TDD 决策缺失或相互冲突，暂停受影响的工作，并将问题交回相应的上游文档处理。**一旦发现已基线化的 SRS / DDD / TDD 发生变化且可能影响计划，立即将计划的 Baseline validity 标为 `IMPACT REVIEW REQUIRED`，暂停受影响的 CC（不得创建、继续实施或关闭），并完成上游审批、计划基线更新、影响分析和 CC 映射更新。**所有要求的评审 / 重新批准完成后，才可将基线状态恢复为 `VALID` 并继续。若尚未完成这些步骤，报告 `BLOCKED` 并列出差异；不得自行推断为不影响。

对每个实施阶段保持双向追溯：

`SRS / DDD / TDD 约束 → 实施阶段 → CC → IHR / ATR / HVR → FR`

项目收口时，除规范性需求覆盖外，还应在项目证据审查中核对各计划阶段和交付物的处置情况：

`计划阶段 / 交付物 → CC → FR → PVR 证据`

计划阶段完成本身不能证明需求已经通过。证据必须来自适用代码基线上的实际执行，并如实保留失败、跳过、阻塞和证据缺失状态。豁免只允许按记录接受未通过项并按 `FROZEN WITH OPEN ITEMS` 冻结，不能把失败改写为通过，也不能替代需求验证。

任一追溯环节缺失、引用断裂或无法绑定到当前代码基线时，将受影响阶段标为未完成，并列出断点及缺失证据。不得以“计划阶段已完成”代替需求验证，不得把受影响 CC 或项目报告判为满足；按各自模板的原生状态报告 `NOT RUN`、`EVIDENCE MISSING`、`BLOCKED` 等状态，直至追溯和证据补齐。

### 证据状态必须显式填写

每个必需的测试、人工场景、契约义务和项目覆盖行都必须填写统一的 `Workflow Evidence Status`：`Passed / Failed / Skipped / Blocked / Missing`，并保留来源模板的原生状态和证据引用。只写“已测试”“已完成”或留空不可接受。`N/A` 是适用性标记，不是证据状态；应单独填写适用性及理由。`PARTIAL` 等汇总状态必须拆到具体测试 / 场景，不得遮盖未通过项。

常见原生状态映射和豁免记录格式见 `references/templates/Planning/AUTHORIZATION_RECORDS.md`。例如 `ATR: FAIL` 同时填写 `Workflow Evidence Status: Failed`。授权不得把底层状态改成 `Passed`。

同时遵守各模板自己的原生状态字段和判定语义：

- **ATR**：每项自动化测试记录 `PASS / FAIL / SKIPPED / BLOCKED / NOT RUN`。
- **HVR**：每个必需 Scenario / Run 使用模板规定的 `PASS / FAIL / BLOCKED / NOT RUN` 等状态；Run 汇总状态按模板填写。
- **FR**：Closure 使用 `SATISFIED / NOT SATISFIED / BLOCKED`；适用性为 N/A 时按模板记录。缺少证据不得写 PASS，应按 FR 规则判定并暴露 Evidence Gap。
- **PVR**：分别填写 Mapping Status、Verification Status、Verification Run Result 和 PVR 自身状态；缺证据时使用模板定义的 `EVIDENCE MISSING`、`NOT VERIFIED`、`NOT RUN` 等状态。
- **PCR**：继承 FR Closure Status 和 PVR Coverage 状态，按 PCR 模板的三态 / Gap 规则判定，不重新解释底层证据。

不得因新增统一字段而改写或删除 Frozen 模板的原生状态枚举；使用授权记录附录补充工作流字段。需改变模板原生字段时，先走模板版本变更流程。

### 未通过项豁免与带未通过项冻结

本节定义永久豁免的记录格式与处理通道；是否启用豁免由人类授权决定，skill 无权决定某个未通过项应否豁免。

冻结不要求所有测试都通过，但每个未通过项必须有完整、显式、由人授权的永久豁免记录。冻结门禁逐项检查：

- [ ] 所有未通过项已记录豁免（含授权人），或已确认无未通过项。

发现 `Failed / Skipped / Blocked / Missing` 项时，默认报告 `BLOCKED` 并拒绝 FR / PVR 冻结。仅当完整豁免记录已存入项目授权登记册，且操作者明确声明“已获授权”时，才可按 `FROZEN WITH OPEN ITEMS` 强制冻结。每条记录必须包含：

```text
豁免项：<测试 / 检查项标识>
状态：<Failed / Skipped / Blocked / Missing>
原因：<为什么现在不处理>
影响：<对需求、数据、上线、后续阶段的影响>
授权人：<项目已知负责人、维护者或明确指派批准人的姓名及可核验标识>
```

授权人必须是当前项目已知的负责人、维护者或明确指派的批准人，且记录足以对应到具体自然人。匿名身份、仅写角色名（如“团队”）、或无法对应到人的账号 / 标识均不合格。授权人字段缺失、授权人不可识别，或没有操作者明确确认已获授权，均不得放行冻结。Agent 只能检查记录是否完整，不得自行判断测试可以忽略，不得推测、补写或代替人类授权。豁免永久接受，不设有效期或复审条件。

若豁免项是某条 SRS 需求的唯一验证手段，不得放行该豁免或强制冻结。暂停受影响的 FR / PVR 冻结，退回 SRS 负责人处理，或先补充并实际执行足以验证该需求的替代验证。

每份 FR 列出其对应 CC 的豁免记录 ID；PVR 汇总项目级全部豁免记录 ID。两处均须记录 `Freeze disposition: FROZEN WITH OPEN ITEMS`。完整豁免字段保存在项目授权登记册中，FR / PVR 引用登记册路径与 ID，不重复抄写授权内容。原始失败状态和证据保持不变；此冻结标记不等于测试通过，也不自动把 FR Closure Status 或 PCR Project Closure Status 判为满足。PVR / PCR 状态来源若存在冲突，按下文冲突规则停止处理。

若同一变更既需要 TDD 偏移又涉及测试豁免，必须先完成偏移授权、偏移实施、反向生成并冻结新版本 TDD、更新基线；然后按新 TDD 重新执行和评估相关验证。偏移前的豁免结论不得沿用，仍需豁免的项目必须在新基线下重新取得授权并登记。这是新技术基线带来的影响评估，不是豁免有效期或定期复审；旧记录仍作为原证据 / 基线下的永久授权保留。

### TDD 偏移授权与反向生成新版本

本节定义 TDD 偏移的授权通道与记录格式；是否启用偏移由人类授权决定，skill 无权自行批准偏移。

发现拟实施内容偏离当前冻结 TDD 的条款或约束时，默认立即暂停受影响 CC 和实现，并报告 `BLOCKED`。只有完整偏移记录已存入项目授权登记册，且操作者明确声明已获人类授权后，才允许在所授权范围内恢复受影响工作。偏移记录必须包含：

```text
偏移项：<TDD 条款 / 约束标识>
原 TDD 版本：<当前冻结版本>
实际实施：<授权前填写拟实施的偏离方案；完成后更新为实际实施内容>
偏移原因：<为什么必须偏离>
影响：<对需求、数据、后续阶段的影响>
授权人：<项目已知负责人、维护者或明确指派批准人的姓名及可核验标识>
反向生成 TDD 版本：<目标新版本号>
```

授权人和所有字段均为强制项；授权人必须是当前项目已知负责人、维护者或明确指派批准人，并可对应到具体自然人。匿名、角色名（如“团队”）或无法对应到人的标识不合格。缺少任何字段或操作者确认时不得放行。Agent 不得自行判断偏移合理或代替授权。目标版本必须在授权记录中确定；按项目版本规则递增，不存在版本规则时先由负责人决定，不能猜测。

恢复工作前，“实际实施”栏必须描述人类批准的拟实施方案和偏移边界。实施完成后，必须将该栏更新为实际实施事实并关联 CC / IHR 证据；实际实施与获批方案不一致时，立即停止受影响工作并重新取得授权，禁止事后补写或改写记录使两者看似一致。

获准偏移实施完成后，必须依据实际实施反向生成一个递增的新版本 TDD：新版本另存，严格按 `references/templates/Designing/TDD模板.md` §0.5 的冻结与变更规则完成评审、批准和冻结后，成为当前基线；旧冻结版本归档保留，不覆盖、不删除。更新 Implementation Plan 的 TDD 版本基线、影响分析及阶段 / CC 映射。反向 TDD 完成、批准并冻结前，不得关闭受影响 CC / FR，也不得把计划基线有效性恢复为 `VALID`。

每个 CC、IHR、ATR、HVR、FR 必须标明其实际依据的 TDD 版本；适用的 PVR / PCR 也应记录各项所追溯的版本。历史记录保留原版本事实；对受影响记录补充偏移 ID 和新 TDD 版本的反向更新引用，不得伪称它们起初就基于新版本。后续 CC 及追溯以新冻结版本为基线。

偏移若触及 SRS 业务含义、需求或验收语义，立即停止受影响 CC 的实施及其 FR / PVR 冻结，并将问题交回 SRS 负责人。SRS 在此流程中不可修改；不得通过 TDD 偏移、新 TDD、豁免或计划变更绕过 SRS 流程，已批准的业务需求基线保持稳定。

测试豁免与 TDD 偏移是不同授权：豁免永久接受一条未通过证据，不产生新基线；TDD 偏移只授权所记录的实施差异，并要求完成后反向生成新 TDD 基线。两类授权都必须由人给出并留下可审计记录，且不得用“已完成”“已测试”等无证据表述替代。

## Odoo 工程选择

选择实现方案时遵循 `docs/context/cognition/Odoo_Engineering_Guidelines.md`：优先使用 Odoo 原生能力、简单 ORM 模型和标准视图、显式业务逻辑及稳健实现，并尽量基于真实 Odoo Runtime 验证。只有在 SRS / TDD 明确要求，或 Technical Verification 证明 Odoo 原生能力无法稳健满足已批准要求时，才允许引入额外抽象、层次或基础设施；理由和选择必须先记录在 TDD 并按其流程批准，再进入受影响的 CC。若仍认为需要额外抽象但没有上述依据，停止并退回 TDD / TV 处理，不得在 CC 中自行决定。

## 模板与仓库文档

本 skill 在 `references/templates/` 中包含完整的文档模板和指导文件。每次只读取当前任务需要的模板。即使 skill 被单独安装或调用，也可以使用这些内置模板。

| 文档 | skill 内模板 / 指导文件 |
|---|---|
| SRS 前的业务需求梳理 | `references/templates/Designing/Business_Requirements_Guide.md`（Draft 指导，不是 Frozen 权威文档） |
| SRS | `references/templates/Designing/SRS模板.md` |
| DDD | `references/templates/Designing/DDD模板.md` |
| Technical Verification | `references/templates/Designing/Technical_Verification_Guide.md` |
| TDD | `references/templates/Designing/TDD模板.md` |
| Implementation Plan | `references/templates/Planning/IMPLEMENTATION_PLAN_TEMPLATE.md` |
| Coding Contract（CC） | `references/templates/Coding/Coding_Contract模板.md` |
| Implementation History Record（IHR） | `references/templates/Coding/IHR模板.md` |
| Automated Test Record（ATR） | `references/templates/Coding/ATR模板.md` |
| Human Verification Record（HVR） | `references/templates/Coding/HVR模板.md` |
| Final Report（FR） | `references/templates/Coding/FR模板.md` |
| Project Verification Record（PVR） | `references/templates/Closoure/PVR模板.md` |
| Project Closure Report（PCR） | `references/templates/Closoure/PCR模板.md` |
| 授权记录与统一证据状态附录 | `references/templates/Planning/AUTHORIZATION_RECORDS.md` |

Designing 和 Coding 模板是从 `docs/context/cognition/template/` 完整复制而来。源仓库中的 Closure 目录目前拼写为 `Closoure`；使用 skill 内模板时也保留该拼写。

每个模板副本文件头部都有 HTML 注释元数据，记录来源路径、来源版本 / 状态和同步日期。**每次使用模板创建或修改项目文档前，必须先核对来源：**

1. 在仓库根目录运行 `python3 docs/skill/odoo-project-workflow/scripts/check_template_sync.py --template <模板键>`。
2. `<模板键>` 使用表格中对应类别：`srs`、`ddd`、`technical-verification`、`tdd`、`implementation-plan`、`cc`、`ihr`、`atr`、`hvr`、`fr`、`pvr`、`pcr` 或 `business-requirements`。
3. 脚本比较元数据的来源路径、来源头部版本 / 状态及副本正文。若来源没有静态版本 / 状态，则按该事实记录并核对正文。
4. 命令返回非零、来源不可读、版本 / 状态不符或正文不一致时，**立即停止使用该模板**；不得使用它创建或修改权威文档，也不得用旧副本顶替。报告来源与副本的差异，先同步副本、更新元数据和重新校验。在阻塞解除前，只能准备明确标为 `Draft` 且不被下游引用为基线的材料。

脚本需要项目来源文件；单独安装 skill、无法访问项目来源时，必须报告 `BLOCKED`，不得把“无法核对”当作版本一致。相关权威文件包括：

- `docs/context/cognition/Odoo_Engineering_Guidelines.md`
- `docs/context/cognition/Project_Workflow.md`
- 当前项目的 SRS、DDD、TV、TDD 和已批准的 Implementation Plan

`docs/implementation/IMPLEMENTATION_PLAN_global_search.md` 是特定项目的冻结实例，不是通用计划模板。不得未经核对就将其中的业务范围、环境、假设或日期复制到其他项目。

### 工作流文档冲突与同步

- 权威顺序为：批准的 SRS 业务基线约束业务含义；`Project_Workflow.md` 规定组织级 Project Closure 流程；各 Frozen 模板规定对应文档的字段、原生状态和判定语义；本 skill 补充执行步骤、模板副本核对、人工授权记录及 TDD 后首个 CC 前的 Implementation Plan 门禁。skill 不得覆盖上游权威或改写模板原生语义；新增门禁作为额外要求执行。
- 若本 skill 与 `Project_Workflow.md` 对流程或收口规则存在实质冲突，以 `Project_Workflow.md` 为组织流程权威；若需继续使用 skill 中与之冲突的要求，先由文档维护者正式修订并统一来源。期间停止受影响工作，报告冲突，不自行调和或跳过任何门禁。
- 使用前检查 `Project_Workflow.md` 是否有新版本或相关修改。同步脚本以已评估版本的 SHA-256 基线核对；来源发生变化时返回失败并阻止使用，须先审查差异、更新 skill 与基线，再重新校验。
- 当前 `Project_Workflow.md` §0.3 与 PVR / PCR 模板头均将 PVR、PCR 标为 v1.0.0 Frozen。使用前仍须运行同步脚本核对模板正文、来源元数据和工作流基线；任一来源后续变化时先评估并统一，再使用相关模板。
- `Closoure` 是当前仓库实际目录名。若上游将目录更正为 `Closure`，同步重命名 skill 内目录、模板路由和检查脚本，然后运行 `python3 docs/skill/odoo-project-workflow/scripts/check_template_sync.py`（不传 `--template`，检查全部模板），并确认全部模板校验通过；不得长期保留过期路径。

本 skill 不包含 `PROJECT_COGNITION.md`：仓库中的该文件包含具体项目身份、路径、环境和业务背景，应在项目级维护，不应视为可复用的工作流指令。
