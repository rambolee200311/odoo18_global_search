# Office Engine M2 — Architecture Change Impact Assessment v0.1

| 项目 | 内容 |
|---|---|
| 文档类型 | Architecture Change Assessment / 架构变更影响分析 |
| 状态 | **DRAFT — FOR HUMAN REVIEW; NOT AUTHORIZED FOR IMPLEMENTATION** |
| 日期 | 2026-11-06 |
| 项目 | Odoo 18 CE / Office Engine M2 |
| 范围 | 文档影响、技术路线比较、TV 计划输入及 CC-02 至 CC-06 调整建议 |
| 代码/运行验证 | 本次未修改代码、未运行测试、未操作数据库/服务/浏览器/Provider |

## 1. 摘要与结论

本次评估提出的是**技术实现路线变更**，不是新增“数据填充”或“多轮自然语言修改”产品需求。首轮使用当前 Odoo 用户权限读取数据并填入模板，以及用户随后连续修改生成文件，均属于原始产品目标；它们不能被描述为本次新增需求。

当前冻结实现以本地 Mapping / Canonical Document Operations 处理首轮填充和后续 Proposal 修改。新提案希望保留本地数据获取、首轮填充、安全、版本、确认、验证和交付，同时评估把首轮填充后的开放式 Excel 编辑交给 LLM 及受控文件编辑环境。该路线**尚未验证**，不等同于已获准切换，也不证明它能保真地修改任意工作簿。

影响判断：

- 保留当前授权 ORM 检索、本地首轮数据填充、文件资源限制、独立验证、用户确认和附件交付等成熟边界。
- 不直接覆盖冻结 SRS、Phase B v0.3、TDD 或 Implementation Plan v0.2；如 TV 支持新路线，需先由负责人批准正式变更，再按版本化变更流程更新受影响基线。
- 原 SRS 对 AI 仅提出受约束映射建议、不得读写文件或执行代码的条款，与“LLM 编辑文件”提案存在需要正式解决的规范差异；不能假定受控环境自动消除该差异。
- 先执行本文件配套的 TV 草案，比较本地操作执行与受控 LLM 文件编辑。TV 通过和人工批准之前，不调整技术路线、不启动 CC-02 至 CC-06、不编码。
- CC-01 保持冻结契约和原只读审计范围。本评估不修改、不暂停或重开 CC-01；当前 IHR/ATR 的 `COMPLETE WITH OPEN / UNVERIFIED ITEMS` 状态保持不变。

## 2. 依据与证据边界

本报告只检查当前工作区的文档和源码，未验证 8091 的实际运行模块身份，也未复验历史浏览器结果。

| 证据 | 相关事实 | 证据限制 |
|---|---|---|
| `docs/requirement/SRS_office_engine_m2_ai_mapping.md` §§1–3、5、7 | 产品目标为将自然语言、模板结构和授权数据映射成文件；FR-M2-007 支持用户对映射进行修改；AI 被限定为映射建议者，不直接读写服务器文件或执行代码 | 冻结业务需求，非本次可修改文件 |
| `docs/requirement/SRS_office_engine_m2_ai_mapping_v1.1.0.md` §§2–5 | 多轮修改作用于完整 Proposal 的受控增量更新；需绑定 revision、刷新数据并重新预览/确认 | 冻结 SRS 变更基线 |
| `docs/B技术设计草案.md` v0.3 §§3–7、§10 | 冻结了表达式、Intent/Expected Effect、Proposal Patch、确认 Effect 和 outcome 设计 | 设计基线；本次不覆写 |
| `docs/design/TDD_office_engine_m2_v1.1.0.md` §§1–5、§9–10 | 本地 AI Proposal → Mapping 校验 → `office_core` 渲染/回读 → Preview/Finalize/附件；明确不允许 AI 直接读写文件或通过浏览器编辑 | 当前 TDD 的架构描述；不是新路线的能力证据 |
| `docs/design/TDD_office_engine_m2_dynamic_rows_addendum_v1.1.0.md` §§1–5 | repeat-row 为受限服务端目标扩展；由统一校验和 M1/Office Core 执行 | 保留其已冻结安全边界 |
| `docs/implementation/IMPLEMENTATION_PLAN_office_engine_m2_state-continuity_v0.2.md` §§2–8、§13 | CC-01～06 是冻结计划分解；CC-02 表达式、CC-03 Proposal/确认、CC-04 Intent/Effect、CC-05 Outcome/恢复、CC-06 集成验收 | 计划标记冻结，但基线有效性为 `IMPACT REVIEW REQUIRED`；非编码授权 |
| `docs/verification/TV_office_engine_m2_plan.md` §§1–10 | 既有 TV 限定当前 OpenAI Provider / `gpt-5.6-luna`，要求数据策略门禁和分层证据 | 新 TV 草案应兼容这些限制，不能用合成数据冒充真实业务 E2E |
| `docs/verification/TV_office_engine_m2_report.md` §§1、11 | TV-M2-001 `FAIL`、TV-M2-002/004 `INCONCLUSIVE`、TV-M2-003 `PASS`，仅在其各自范围内成立 | 历史结果，不是 LLM 文件编辑验证 |
| `mymodules/office_engine_m2/models/llm_thread.py`、`office_mapping_tools.py` | 当前 Office Tool 流围绕 `office_prepare_context`、`office_save_mapping_preview`、`office_finalize`；提示词规定模型生成受约束的 Mapping Proposal / cell edits | 仅为工作区源码证据，不证明运行环境加载该源码 |
| `mymodules/office_engine_m2/services/render_bridge.py`、`mymodules/office_core/service.py` | 预览/正式生成从已绑定模板字节与 Mapping 数据编译候选，走有界 Office Core Worker 和回读验证 | 说明当前本地执行链；新路线尚无实际接入证据 |
| CC-01 v0.2、配套 IHR/ATR | CC-01 为只读基线审计；Runtime/历史事件仍有未验证项 | 本次不扩大其证据来源或执行范围 |

## 3. 文档影响清单

状态标签：`KEEP` 保持现状；`MODIFY` 在 TV 和变更审批后提出修订；`REPLACE` 仅表示建议以新版本替换旧路线描述，不是本次替换；`DEFER` 暂缓决策；`UNVERIFIED` 缺乏技术证据。

| 文档/基线 | 状态 | 已确认内容与影响 | 评估处置 |
|---|---|---|---|
| SRS M2 V1.0.0 | `KEEP + MODIFY 提案待审` | 首轮数据填充及映射成功后生成文件是原需求，不变。其 1.3/5.1 将 AI 限于受约束映射建议，并禁止 AI 直接读写服务器文件/执行代码；若新架构把自然语言文件编辑委派给 LLM，这个实施边界不能原样解释成“已经允许” | 不覆盖冻结文档。TV 后提交 SRS 变更提案，明确哪些 LLM 文件编辑行为纳入产品范围、用户确认/隐私边界和不支持范围。若只改变底层工具路线而不改变用户行为，也仍须解决该职责表述冲突 |
| SRS M2 V1.1.0 | `KEEP + MODIFY 提案待审` | FR-M2-007 已有连续自然语言修改，但当前语义是修改完整 Mapping Proposal；FR-M2-008 将确认绑定 Proposal/预览，并在 Finalize 前重新读 Odoo 数据 | 保留用户功能目标；评估将“当前 Proposal”扩展为版本化工作簿状态/LLM 候选文件，且确认仍绑定具体文件版本、Effect 和数据状态。任意文件编辑若越过现有 M2 范围，须明确判为需求扩展而非实现细节 |
| Phase B v0.3 冻结设计 | `KEEP；后续走正式变更` | 类型表达式、多轮状态、Effect 确认和结果契约已冻结。LLM 外部文件编辑可能减少部分本地通用编辑表达式的需求，但不消除首轮映射/数据刷新/回读所需的类型语义 | 不重写、不撤销。TV 后列出保留、缩窄、推迟的条款，提交版本化设计变更；只有批准后才改变规范语义 |
| 原始 M2 TV Plan / Report | `KEEP` | 旧 TV 限定 `gpt-5.6-luna`，且已有 FAIL/INCONCLUSIVE 结果 | 保留原文件和原状态；新增单独的 LLM Office Editing TV Plan/Report，不把新测试伪装成旧 TV 的 PASS，也不改变模型基线而不审批 |
| M2 TDD V1.1.0 | `MODIFY 提案待 TV` | 现有架构将 Proposal/编辑操作在 Odoo 本地转换并由 `office_core` 写文件、验证。新路线要增加 LLM 文件编辑候选的输入/输出、信任边界、验证和版本衔接 | TV 通过后，以新修订/补充说明 LLM 编辑环境边界、文档版本来源、candidate validation、数据刷新与失败恢复。保留 ACL、Worker 资源限制、回读和交付门禁 |
| 动态行 TDD 补充 V1.1.0 | `KEEP；必要时 LIMITED MODIFY` | 首轮或数据刷新中的明细填充仍需要受限集合、目标清单和扩展规则。若后续 LLM 修改结构，不得让外部编辑结果绕过最终结构验证 | 先保留。若 TV 发现 refresh 与已编辑工作簿明细区域无法可靠交互，再提出最小兼容补充；不以新编辑器删除 repeat-row 约束 |
| Implementation Plan v0.2 | `KEEP 当前冻结版本；评估新修订` | 六轮 CC 顺序和 G1–G5 门禁已冻结，CC-02～06 均计划于该架构下工作；状态仍有 `IMPACT REVIEW REQUIRED` | 不直接改文档。TV 后向审批者提交 v0.3 修订建议，把确定的路线决策映射到 CC-02～06；继续保留独立 CC、分层证据和授权门禁 |
| CC-M2-B-01 v0.2 | `KEEP` | 已冻结且授权 workspace-only 只读审计；其 IHR/ATR 交付和 OPEN/UNVERIFIED 项已记录 | 不变更范围、不暂停、不以本架构评估重开 CC-01。后续工作按其既定关闭结论处理 |
| CC-M2-B-02 至 CC-M2-B-06 独立契约 | `UNVERIFIED / 尚未创建` | 仓库检索未发现独立冻结 CC 文档；这些 ID 仅作为 Implementation Plan 中的拟建阶段 | 不启动新 CC，不补写冻结契约。下表只给未来 CC 草拟调整方向；须先完成 TV、修订计划并分别获得 G3/G4 授权 |

### 3.1 产品需求与技术路线的区分

| 项目 | 归类 | 本评估处理 |
|---|---|---|
| 用当前 Odoo 用户权限读取数据并填入用户指定模板 | 原始产品需求 | 保留。初始 Mapping/数据读取依旧由本地 Odoo 权限和确定性文件链承担 |
| 用户以自然语言连续修改已生成文件 | 原始产品需求 | 保留，不描述为新需求。当前 SRS 将其具体化为 Mapping Proposal 增量修改；若开放操作范围超出已有产品行为，须另行说明并审批 |
| 将开放式后续 Excel 修改交给 LLM/受控文件编辑环境 | 技术路线提案 | 待 TV 比较。不能以架构评估本身当作技术可行性证据 |
| LLM 能否访问 Odoo、接触业务数据、直接交付文件 | 安全/产品边界 | 未决定；必须与 Odoo ACL、Provider 数据政策和候选文件验证分离 |
| Odoo 数据刷新后保留此前人工/LLM 编辑 | 技术风险与产品语义交叉项 | 独立测试。无法稳定识别数据区/记录身份或冲突范围时应澄清/确认；不能声称可自动合并 |

## 4. 新旧路线对比

本表为待验证的架构假设，不是当前系统的实测结论。

| 维度 | 本地 Operation / Expression 驱动 | LLM 驱动的受控文件编辑 | 当前判断 |
|---|---|---|---|
| 功能覆盖 | 明确支持的操作可确定性执行；新能力需扩展受限契约 | 可能覆盖难以预先穷举的编辑意图；支持范围取决于 Provider/编辑环境 | 用中性工作簿对照测试；不得以“LLM 更灵活”作为证据 |
| 开发成本 | 新增操作要维护 Schema、编译、Adapter、冲突/确认、回读与测试 | 需连接文件输入/输出、隔离执行或受控 Provider 工具，并验证长尾结构 | TV 记录原型工作量及未覆盖能力；不先假定哪边更低 |
| 维护成本 | 可预测但本地操作语义可能持续增长 | 可能减少专用操作实现，但依赖外部 API/模型版本、文件处理行为和环境 | 记录版本升级、兼容/回退成本，不只比较初次编码 |
| 文件保真度 | `office_core` Adapter 对受支持结构可进行明确读写与独立验证；格式范围仍有限 | LLM/工具可能重写工作簿包或对象；公式、样式、图表、名称、验证、打印设置等是否保真未知 | 用字节/结构/视觉差异和实际 Excel 打开验证；不预设全保真 |
| 权限与安全 | Odoo 当前用户 ORM、Manifest、资源边界和本地验证链已明确 | 必须限定可见文件、不能取得 ORM 凭据/秘密、网络和执行资源；外送数据政策及 Provider 保留未知 | 只有隔离边界/数据政策/可审计工具调用都通过才可接受 |
| 用户确认 | 当前 Confirmation Gate 可绑定 Session/Proposal/文件/目标/观察值等 | 需要确认 LLM 输出的实际候选及其差异；现有 Gate 是否能绑定 LLM candidate 尚无证据 | 验证确认对象是候选字节和精确 Effect，确认前不得发布 |
| 多轮连续性 | 完整 Proposal 重编译，规则 patch/revision 有现有状态模型 | 可能以文件版本/会话上下文为基线；模型上下文是否持续、重试是否幂等未知 | 通过跨轮候选、历史恢复、服务重启/超时恢复用例验证 |
| Odoo 数据刷新 | 现有本地 Retriever 可按当前权限重新取数；映射表达可把值写入原模板 | 需定位刷新字段/记录行并与模型改动分离，避免覆盖已有修改 | 是关键风险；单列 TV，不以填表成功代替刷新成功 |
| Provider 依赖 | LLM 用于意图/Mapping 提案；文件执行本地确定 | 文件编辑能力和结果可能强依赖 Provider 的文档工具或模型能力 | TV 仅使用当前计划许可的 `gpt-5.6-luna` 基线；能力可用性尚未证明 |
| 测试复杂度 | Schema/执行/回读可做确定性测试，再做 Odoo 集成 | 除文件差异外，还要测自然语言、多轮、外部 API 超时、候选损坏、数据外发和恢复 | 需要三层测试（本地契约、Odoo 集成、真实 Provider/Browser） |
| 失败恢复 | 候选生成/验证失败可保留 last-valid Preview（现有实现和测试有相关路径） | 模型超时但文件已返回、文件生成但 API 结果丢失、格式损坏/附件未发等需额外复验 | 实际恢复路径未测；必须以实际文件身份和幂等键验证 |

候选实现方式至少包含：①当前本地规范 Operation 方案（基线）；②若当前批准 Provider 有可用能力，评估 Provider 原生文档编辑；③评估在隔离、短生命周期、无业务凭据/非必要网络的受控文件编辑环境中处理文件。TV 不假定 XML Patch、Python 脚本、完整 XML 替换或某一 API 为最终实现，也不授权在 Odoo 服务进程中执行模型生成的任意代码。

## 5. 建议的目标数据流（概念性，待 TV 验证）

```mermaid
flowchart LR
  U[自然语言 + 模板] --> R[当前用户 ORM Retriever]
  R --> M[本地首轮 Mapping 与文件填充]
  M --> V[独立文件/结构验证]
  V --> P[Preview V1]
  P --> L[LLM + 受控编辑环境]
  L --> C[候选 V2/V3]
  C --> D[差异、结构与结果验证]
  D --> G[必要的风险确认]
  G --> A[安全附件发布与聊天反馈]
  P -. 用户要求刷新数据 .-> R
  R -. 重新映射/更新，保留已确认改动或澄清 .-> M
```

此图只表示责任边界的候选形式。真实编辑候选是否由 Provider API、隔离工具环境或别的受控方式产生，以及数据刷新具体如何把更新应用到已编辑文档，均需通过 TV 和设计审批；不能直接据图编码。

## 6. 数据刷新专项风险

文件编辑后再获取 Odoo 数据不是普通“重新填模板”。潜在冲突包括：LLM 改过目标列、重新排序或增删行；旧 Mapping 以行坐标为目标；业务记录集合新增/删除；字段值变化；公式/样式/结构影响数据区域判定。

TV 必须分别记录：

1. 刷新输入的 source record/field identity、数据读取指纹及当前用户权限；
2. 原始模板、首轮填充版本和最新 LLM 编辑版本之间的文件 lineage；
3. 能可靠定位的数据区域、行记录身份和本轮更新字段；
4. 刷新产生的精确候选差异，以及对用户编辑的覆盖/保留范围；
5. 发生行重排、记录离开范围、表头变更、合并区冲突或目标不唯一时的结果。

成功条件：只更新已确认/已映射的数据目标，保留刷新范围外的用户编辑；通过独立回读确认 Odoo 值、行身份和公式/结构；任何范围外覆盖都获得精确确认。失败条件：无法唯一定位数据项、刷新需要默默丢弃用户编辑、权限/数据指纹不匹配、候选回读不一致或无法确认保存状态。此时保留 last-valid 文件并澄清/阻断。

## 7. TDD 修订建议清单（不在本任务修改 TDD）

| TDD 区域 | 建议修订方向 | 前置证据/决策 | 不应删减的现有约束 |
|---|---|---|---|
| §1 架构职责 | 区分本地首轮填充/数据刷新与 LLM 后续文件编辑；定义受控编辑环境和候选归属 | TV 比较路线通过；安全/数据使用决策批准 | 当前用户权限、AI 不绕过 ORM、文件安全与职责分层 |
| §3 自然语言编排与多轮状态 | 把“Proposal 修改”与“LLM 生成新工作簿版本”分别建模；定义文件版本/源附件/数据状态 lineage | 多轮 TV、超时/重试观察 | 完整状态和 revision、失败不得污染有效版本、确认不复用 |
| §4 M1 预览/Finalize | 定义本地与外部编辑候选的共同验证/候选接受边界；只有已验证候选可进入 Preview/Finalize | TV 文件保真与回读结果 | 独立 Validator、资源/ZIP/file size 检查、验证失败禁止发布 |
| §5 附件与并发 | 明确候选、消息、Thread 和下载对象的关联及幂等恢复 | Provider 超时与附件失败 TV | ACL、私有附件、last-valid 保护 |
| §7 测试 | 增加跨轮编辑、文件差异、刷新保留用户编辑、失败恢复和格式边界矩阵 | TV 实测和产品范围批准 | 自动化/Provider/Browser/HVR 分层；不把单测说成 E2E |
| §8/§10 安全和 Document Operations | 明确 Local Operation 路线作为首轮/数据刷新能力是否保留；受控外部文件编辑不得绕过统一保存后验证 | 路线决策 | 不在 Odoo 服务进程执行模型任意代码；不以外部模型返回值替代验证 |

在正式变更获批前，冻结 TDD 原文仍是当前权威设计；本清单只是候选修改方向。

## 8. Implementation Plan v0.2 修订建议

| 计划条款 | 建议处置 | 理由 / 条件 |
|---|---|---|
| G1–G5 独立门禁 | `KEEP` | 路线选择不降低授权、Runtime Validation 和 Release 门槛 |
| CC-01 | `KEEP` | 原契约和 IHR/ATR 状态独立，不因路线讨论更改 |
| CC-02 Typed Expression | `MODIFY AFTER TV` | 冻结语义仍可能用于本地首轮映射和数据刷新；外部编辑若承担开放式编辑，可缩小对编辑功能的表达式实现范围。需先确定保留的本地转换用例，不能直接取消 |
| CC-03 Proposal/Confirmation | `MODIFY AFTER TV` | 需从仅 Proposal revision 扩展为可追踪 LLM 文件候选/历史，并将确认绑定最终候选和具体 Effect；复用现有会话/确认门，验证是否足够 |
| CC-04 Intent/Effect | `KEEP + EXTEND` | LLM 外部修改仍需 Intent、结构化请求/Expected Effects 与独立文件回读；不允许模型自证语义完成 |
| CC-05 Outcome/Recovery | `KEEP + EXTEND` | 新路线增加 Provider 工具执行、候选文件返回、验证和交付分阶段状态/超时恢复 |
| CC-06 集成验收 | `MODIFY AFTER TV` | 增加本地首填 → LLM 多轮修改 → Odoo refresh → LLM 后续修改 → Finalize/下载；不得在 TV 前选择具体 Provider edit API |
| §5 依赖顺序 | `DEFER` | TV 后再判断表达式契约是否仍是 CC-03/04 的前置条件；六轮总体拆分先保留，未审批前不调整冻结计划 |
| 回退计划 | `KEEP + ADD CANDIDATE` | 不删除当前本地引擎或既有工作簿。新入口若失败应能关闭新编辑入口并保留最后有效候选；不能以关闭入口等于安全回滚已产生的文件/状态 |

六个 CC 的总体 ID 与门禁先保留；表中仅作为未来修订建议。TV 通过和负责人批准前，CC-02～06 不因本报告获得启动授权。

## 9. TV 计划与决策门

配套 [TV-Llm Office Editing Plan v0.1](../verification/TV_LLM_OFFICE_EDITING_PLAN_v0.1.md) 设计了本地操作基线和受控 LLM 编辑候选的比较，重点覆盖首轮填充、多轮变更、结构/格式/公式保真、确认、刷新 Odoo 数据、刷新后再编辑以及失败恢复。

建议顺序：

1. 人工评审并批准 TV 草案、样本、当前 Provider 和数据权限；本评估不授权执行。
2. 先用合成 Office 文件进行候选方式的隔离、质量与差异检查；这只能证明候选文件处理能力。
3. 通过当前用户 ORM 及适用授权执行 Odoo 集成；对外 Provider 真实业务数据需满足 SRS 数据使用批准，否则使用合成数据并把真实链路标记 `BLOCKED`。
4. 对所有候选执行单轮、多轮、刷新、确认、失败恢复与实际文件下载回读；分别记录 `PASS/FAIL/INCONCLUSIVE/BLOCKED/NOT RUN`。
5. 形成路线决策 ADR/变更请求。人工批准后，才修订 SRS/TDD/Implementation Plan 并草拟 CC-02～06 新契约。

## 10. 待评审决策与未验证项

1. “连续修改”是否只覆盖当前 SRS 的映射/清空/格式等明确范围，还是产品范围扩展为通用 Excel 操作。原始能力不变，但越过当前 SRS 语义的部分需产品负责人定界。
2. “LLM 文件编辑”中模型是否直接接触文件字节、通过 Provider 工具操作，或委派给隔离执行环境。当前没有选定或验证。
3. 允许的 Excel 功能/结构边界及超限时的失败策略；不能承诺任意 XLSX 对象保真。
4. 外部 Provider 的文件留存、训练/日志、地理位置和数据政策是否允许具体模板与业务字段；当前不得假设获批。
5. 公式要求是仅保留公式文本、计算结果必须重算，还是两者；本地 openpyxl/文件工具的重算能力未由本评估验证。
6. 数据刷新后识别记录行、仅更新数据字段并保存用户编辑的可行性；当前 `UNVERIFIED`，为重点 TV 风险。
7. CC-02 的表达式语义是全量实施、仅用于本地首填/刷新，还是部分延期；在 TV 和路线评审之前不改冻结设计。
8. CC-02～CC-06 独立契约尚未在工作区发现；本报告不创建它们。

## 11. 变更控制与停止条件

- 本文及配套 TV 为评审草案，不是架构切换批准或编码授权。
- SRS V1.0/V1.1、Phase B v0.3、TDD V1.1、Implementation Plan v0.2、CC-01 均未在本次修改。
- 没有运行测试、Provider/Browser、Odoo 服务、数据库、模块升级或文件转换；没有更改工作区既有业务代码。
- 本次 Git 状态未清理、未暂存、未提交、未推送。审计前状态为 `main`，HEAD `f9801fca76f7c248a9cc823c583138ab0191b978`，且有既有未跟踪文件和本地 ahead commit；报告不得把这些既有状态归因于本评估。
- 等待人工评审。TV 只有另行批准后执行；TV 结果不自动修改冻结基线。
