# Office Engine M1 — CC-005 Provider 前路由 Spike 报告

## 1. 结论

**Spike 结果：FAIL（同时有 BLOCKED / INCONCLUSIVE 项）。** 已证明当前 Odoo-LLM 对四类标准 Office MIME 在 Provider 前拒绝；普通文本和 tools-enabled 流程在本地 stub 下可继续。跨用户线程/附件权限拒绝通过。但存在 MIME/扩展名身份不一致路径：文件名 `.xlsx`、内容为合成纯文本时，Odoo 将附件 MIME 归为 `text/plain`，Office 预检未拒绝，文本进入本地 Provider mock 的格式化 payload。

此次没有发出任何真实 Provider HTTP 请求，没有真实业务附件或业务记录参与。发现的是确定的 fail-closed 缺口；由于真实 Provider 未调用，不能说真实外部服务收到该内容，但相同请求路径若换回真实 Provider 会继续尝试发送被识别为文本的内容。

## 2. 执行基线

| 项 | 值 |
|---|---|
| CC | CC-OFFICE-M1-005 `v1.0.0 Frozen` |
| Odoo-LLM | `609ec6dda3645165f6a4a843d7af5d286081a29d`；工作树 clean |
| Odoo | 18.0；`odoo18ce`；`odoo.conf`；进程 41995 / 8091 |
| Python / PostgreSQL | Python 3.11.9 / PostgreSQL 16.14 |
| 已安装目标模块 | `llm`、`llm_thread`、`llm_assistant`、`llm_openai`，均 installed |
| Provider 覆盖 | 1 active provider，service `openai`；未安装/启用其他 Provider service |
| 执行身份 | 消息 owner uid 6，攻击方 uid 103，ORM 清理 uid 2；三者用于探针的环境均 `su=False` |
| 测试替身 | OpenAI `openai_chat` 与 tool executor 均进程内 stub；真实 HTTP 调用数 0 |

## 3. 验证方法

1. 先检查 Odoo-LLM HEAD 和 tracked/untracked 状态，再停止旧 Odoo PID；使用项目 `venv` 和 `odoo.conf` 启动目标实例。
2. 通过 `venv/bin/python odoo-bin shell -c odoo.conf -d odoo18ce --no-http` 执行临时运行时探针；不安装/升级模块、不修改配置/schema。
3. 以普通用户创建唯一标记的合成 Office 附件和 LLM thread，运行真实 `llm.thread.generate` 与真实 Odoo MIME/Record Rule 行为。mock provider 调用真正的 OpenAI message/tool formatter，但在网络请求前本地返回合成响应。
4. Office 样本包括 OOXML ZIP 结构的 `.xlsx/.docx` 和 OLE 签名的 `.xls/.doc`。另以 `.xlsx` 文件名 + 纯文本内容验证 MIME 身份不一致边界。
5. 工具循环仅用临时 stub executor 返回合成结果；不执行任何已配置业务工具。
6. 所有记录由 ORM 精确清理；未直接操作 filestore；临时 hook/脚本在运行后物理删除。

## 4. 结果矩阵

| 场景 | 观察 | 判定 |
|---|---|---|
| 标准 `.xlsx` MIME | 附件预检拒绝 1；mock Provider dispatch 0 | PASS |
| 标准 `.xls` MIME | 附件预检拒绝 1；mock Provider dispatch 0 | PASS |
| 标准 `.docx` MIME | 附件预检拒绝 1；mock Provider dispatch 0 | PASS |
| 标准 `.doc` MIME | 附件预检拒绝 1；mock Provider dispatch 0 | PASS |
| Office 序列化隔离 | 已识别 Office 附件经 formatter 检查不含合成 Office sentinel；真实调用被更早拒绝 | PASS（限当前 OpenAI formatter 和样本） |
| 跨用户 thread/attachment | owner uid 6 可见；uid 103 搜索结果为 0；攻击方 `generate` 返回 `UserError`；Provider 调用增量 0 | PASS（拒绝路径） |
| `.xlsx` 名称 + 纯文本内容 / MIME 不一致 | Odoo 将链接后的 MIME 设为 `text/plain`；预检拒绝 0；mock Provider dispatch 1；文本 sentinel 存在于 mock payload | **FAIL** |
| 普通 `text/plain` 附件 | 既有文本附件能在 mock Provider payload 中读取；无 Office sentinel | PASS |
| Tools-enabled loop | OpenAI formatter 生成 tool schema；mock Provider 两次 dispatch；stub executor 一次；无真实工具执行 | PASS（stub 范围） |
| Provider service 覆盖 | 实例只有 OpenAI；其余未启用 Provider 无法作为当前目标路径测试 | 当前实例范围满足，不能外推 |
| 独立 Addon 到 Office 服务的 handoff | 未实现/安装该路由 Addon；仅观察了现有拒绝路径 | INCONCLUSIVE |

## 5. 对安全边界的解释

- 四种标准 MIME 的早期拒绝是当前已有通用拒绝逻辑，不是 Office 生成能力，也不是新增路由实现。
- MIME 不一致失败仅使用合成纯文本 sentinel。mock payload 中出现它，证明身份不一致时未 fail closed；这不是合法 `.xlsx` 二进制、客户数据或真实外发证据。
- 跨用户拒绝证明 Odoo thread/attachment 访问边界在此调用场景生效；它不证明任何服务 handoff 会携带授权上下文。
- 模拟工具循环只证明 Odoo 线程状态机在本地 stub 下运行，不证明 `odoo_record_retriever` 或其他真实工具执行安全。

## 6. Test Contract 汇总

| 测试 | 状态 | 汇总 |
|---|---|---|
| CC-TEST-001 | PASS | 运行时基线与已安装模块可核对 |
| CC-TEST-002 | PASS | 已识别标准 MIME 的预检先于 Provider |
| CC-TEST-003 | PASS（限定） | 已识别 Office MIME 的内容未进入 Provider payload |
| CC-TEST-004 | PASS（当前配置） | 仅 OpenAI service；工具循环全 stub |
| CC-TEST-005 | BLOCKED | 跨用户拒绝通过；授权服务 handoff 缺运行路径 |
| CC-TEST-006 | FAIL | MIME/扩展名不一致未 fail closed |
| CC-TEST-007 | PASS | 普通文本附件回归 |
| CC-TEST-008 | BLOCKED（可行性结论 INCONCLUSIVE） | 独立 Addon/Office 服务 handoff 未验证 |
| CC-TEST-009 | PASS | 证据脱敏、无真实外发 |
| CC-TEST-010 | PASS | 临时 hook / 文件清理证明完整 |

汇总：7 PASS、1 FAIL、2 BLOCKED；其中 CC-TEST-008 的可行性结论为 INCONCLUSIVE。HVR N/A，不计作通过。

## 7. 后续处置建议

1. 不进入 CC-006；不启用用户可用 Office 生成，不把本次标准 MIME 拒绝误认为文件读写或路由已实现。
2. 另行建立批准的技术/实施基线，定义扩展名、实际内容类型和 Odoo MIME 不一致时的确定策略；至少应拒绝可疑 Office 文件而不将其作为文本发送。修复后需用有效和伪装样本重新运行 CC-TEST-002/003/006。
3. 另外解决 CC-004 spawn/import 缺陷并重新验证真实成功生成/附件交付，不能沿用本 Spike 结论。
4. 在独立 Addon 和受控服务 handoff 设计获批并实现前，CC-TEST-005 的服务路由上下文和 CC-TEST-008 继续保持未满足。
5. 本报告不修改 Frozen TDD/Implementation Plan/SRS，也不授权以上修复。

## 8. 证据索引

- [IHR](IHR-OFFICE-ENGINE-M1-PROVIDER-ROUTE-SPIKE.md)
- [ATR](ATR-OFFICE-ENGINE-M1-PROVIDER-ROUTE-SPIKE.md)
- [HVR N/A](HVR-OFFICE-ENGINE-M1-PROVIDER-ROUTE-SPIKE.md)
- [FR](FR-OFFICE-ENGINE-M1-PROVIDER-ROUTE-SPIKE.md)
- `evidence/ATR-RUN-001-provider-route.json`
- `evidence/environment-snapshot.json`
- `evidence/cleanup-proof.txt`
