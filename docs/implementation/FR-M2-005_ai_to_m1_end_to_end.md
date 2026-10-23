# FR-M2-005：AI 映射到 M1 文件交付

## 1. 评估元数据

| 字段 | 值 |
|---|---|
| Intent ID | `OFFICE-ENGINE-M2-005` |
| CC | `CC-M2-005 FROZEN V1.0.0；执行处置 CONDITIONALLY CLOSED` |
| IHR | [IHR-M2-005](IHR-M2-005_ai_to_m1_end_to_end.md) |
| ATR | [ATR-M2-005](ATR-M2-005.md) |
| HVR | [HVR-M2-005](HVR-M2-005_ai_to_m1_end_to_end.md) |
| 评估日期 | 2026-10-23 |
| 总体关闭状态 | **NOT SATISFIED — 保持 PARTIAL** |

## 2. 义务评估

| CC 义务 | 证据 | 状态 | 说明 |
|---|---|---|---|
| AI Proposal、一次修复与 5/20 澄清 | ATR CC-TEST-004 | SATISFIED（指定路径） | Mock 两次均返回 5/20，列出 15 项缺失并停止 M1。 |
| JSON/幻觉输入拒绝 | ATR CC-TEST-005 | SATISFIED（已测自动化边界） | 非法 JSON、未知字段/目标、额外键和类型不符均被拒绝或转澄清，未调用 M1；本项不宣称模型对所有提示注入具有统计性免疫。 |
| 每次 Provider 调用 Usage 记录与隐私 | ATR CC-TEST-006 | SATISFIED（自动化范围） | 正常及缺失 Usage、两轮修复计量、Provider 异常计量持久化、哨兵不落消息/Usage字段、Usage 写入失败阻断均通过。 |
| 当前用户 Retriever 与实时取数 | ATR CC-TEST-002/008 | SATISFIED（合成记录） | 以当前测试 `env` 调用真实 Retriever 读取合成 `res.partner`。 |
| M1 Mapping Plan、稳定 UUID 和幂等 | ATR CC-TEST-008/011 | PARTIAL | 真实 M1 成功请求/附件及同 UUID 唯一请求已验证；独立并发事务竞态未验证。 |
| 真实 Office 引擎生成与回读 | ATR CC-TEST-007 | SATISFIED（合成 `.xlsx`） | 真实 `office_core` 写入，独立 `office_verify` 回读通过。 |
| M1 Odoo 持久化、私有附件与浏览器下载 | ATR CC-TEST-009、HVR-SCN-001 | SATISFIED（预置 Session） | 内置浏览器确认后真实 `_render_request_sync` 生成；私有附件 ORM 回读正确，刷新后下载链接恢复。 |
| 失败无附件交付 | ATR CC-TEST-010 | PARTIAL | Provider/Usage 错误停止在 M1 前，M1 failure 无下载；Retriever 撤权/超时、verify、附件交付和清理完整矩阵未测。 |
| UI 上传→自然语言→AI→确认→下载 | ATR CC-TEST-012、HVR | NOT SATISFIED | 当前缺少安全的上传→目标解析→TargetManifest/Session 创建入口；HVR 仅覆盖预置 Session 的确认与下载。 |
| 自动化/人工验证记录 | IHR/ATR/HVR | SATISFIED（记录完整） | 文件记录真实证据和限制；全量 Addon 48 项中 1 个历史数据敏感断言失败、1 个 HttpCase 跳过；排除该既有用例后 47 项全通过。报告完整不等于功能验收通过。 |

## 3. 缺口与关闭条件

1. 设计并实现安全的聊天上传、自然语言目标解析、M1 Inspection/TargetManifest 生成及 Session 创建入口，客户端不能传任意业务记录 ID 或 Manifest。
2. 由数据/隐私负责人处置 Provider 数据政策和安全字段基线；未批准前真实业务数据外发必须拒绝。
3. 补做 UI 上传启动映射、5/20 澄清和权限/渲染失败场景；确认真实全链路成功后由负责人验收。
4. 用独立并发事务验证同确认版本的唯一请求/附件，并完成 Retriever、M1 verify、附件交付失败和失败清理矩阵。
5. 处理前序 Session 测试对共享库全表计数为 0 的脆弱断言，并在有 `websocket-client` 的授权环境重跑全量 Addon。

本 FR 的需求满足结论仍为 **NOT SATISFIED**，因为 UI 上传启动链路及其他列明缺口尚未满足。负责人已批准 CC 的行政/实施处置为 **CONDITIONALLY CLOSED**；该处置仅接受共享开发库脆弱 Session 全表计数测试不阻塞 CC 关闭，不改变本 FR 的需求判断或任何测试原始状态。全表计数测试仍为 FAIL，授权记录为 `EXEMPTION-CC-M2-005-001`。不得据此宣告 M2 阶段完整 E2E 交付完成。
