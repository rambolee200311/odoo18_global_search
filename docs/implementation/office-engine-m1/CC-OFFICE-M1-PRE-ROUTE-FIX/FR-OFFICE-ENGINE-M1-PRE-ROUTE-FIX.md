# FR — CC-OFFICE-M1-PRE-ROUTE-FIX

## 1. 结论元数据

| 字段 | 值 |
|---|---|
| Intent ID | `OFFICE-ENGINE-M1-PRE-ROUTE-FIX` |
| CC | `CC-OFFICE-M1-PRE-ROUTE-FIX v1.0.0 Frozen` |
| IHR / ATR / HVR | [IHR](IHR-OFFICE-ENGINE-M1-PRE-ROUTE-FIX.md) / [ATR](ATR-OFFICE-ENGINE-M1-PRE-ROUTE-FIX.md) / [HVR](HVR-OFFICE-ENGINE-M1-PRE-ROUTE-FIX.md) |
| FR 状态 | **SATISFIED — CC 实施与规定范围的验证完成，等待负责人批准关闭 CC** |
| CC 关闭 | 未请求、未批准 |

## 2. 追溯判定

| CC 义务 | 证据 | 状态 |
|---|---|---|
| Office 候选在 Provider 前 fail closed | ATR CC-TEST-001/002/003/005 | SATISFIED（冻结范围内的合成测试路径） |
| 有效最小 OOXML 被识别为 Office 候选；坏中央目录安全拒绝 | ATR CC-TEST-003 | SATISFIED；验证候选识别与 fail-closed，不宣称完整 OOXML 解析 |
| 普通文本/PNG 不被闸门误拒且真实序列化结构正确 | ATR CC-TEST-004、HVR | SATISFIED（真实 OpenAI formatter + 本地 stub；无真实 Provider） |
| 拒绝消息及附件不污染下一轮 | ATR CC-TEST-005 | SATISFIED（自动化 stub 路径） |
| 当前用户附件访问权限、不使用 sudo | ATR CC-TEST-005 | SATISFIED（私有附件访问拒绝测试） |
| 2048 字节有界读取且无完整附件物化 | ATR CC-TEST-008 | SATISFIED；验证 5 MiB 附件只读 2048 字节。解压限制不适用，因为本实现不解压 |
| Odoo 模块升级和运行时继承加载 | ATR CC-TEST-007 | SATISFIED（数据库状态/版本及 ORM 方法核验） |
| 浏览器可见拒绝错误及普通附件回归 | HVR CC-TEST-007 | SATISFIED（负责人批准 ORM 注入模拟；曲别针草稿上传路径被绕过，仍需单独跟踪） |
| 无真实 Provider 外发 | ATR/HVR CC-TEST-006/007 | SATISFIED（未执行真实 Provider 调用） |

## 3. 判定

冻结 CC 的自动化测试均有通过证据，包含本轮新增的真实最小 OOXML/坏中央目录测试、OpenAI 消息序列化断言、5 MiB 文件头有界读取，以及按负责人指示执行的 ORM 注入 + 内置浏览器 HVR。伪装 Office 附件在 Provider 调用前得到 `UserError`；普通 `.txt` / `.png` 序列化保持既有结构；所有验证均未请求真实 Provider。

因此本 FR 记为 **SATISFIED**，提交负责人进行最终关闭审批。该状态不等于 CC 已关闭；CC 仍保持 Frozen/实施待审批状态。CC-005 的 handoff BLOCKED / INCONCLUSIVE 与 CC-004 的既有 FR 状态不变。

## 4. 未覆盖的独立问题

内置浏览器曲别针上传后聊天草稿不呈现附件的问题仍存在。本轮用 ORM 创建消息和附件以完成指定的拦截/UI 展示模拟，不代表上传组件已经修复，也不证明文件选择器到自然聊天发送的 UI 原生 E2E 链路通过。该缺陷应另行登记/修复，不扩展本 CC 范围。
