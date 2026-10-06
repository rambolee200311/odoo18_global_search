# TD-001 Search Request Boundary Hardening

## 基本信息

| 项 | 内容 |
|---|---|
| 技术债 ID | TD-001 |
| 标题 | Search Request Boundary Hardening |
| 登记日期 | 2026-10-05 |
| 登记人 | — |
| 状态 | Done |
| 优先级 | P1（高） |
| 类型 | Contract Hardening / 安全边界 |
| 关联 CC | CC-002（Search Service）、CC-007（错误与部分失败） |
| 关联 SRS | SRS V1.4 FROZEN |
| 关联 TDD | TDD V0.3 FROZEN |

## 问题描述

CC-002 和 CC-007 已定义 Search Service 与错误协议，但部分请求边界数值和验收测试尚未写死：

| 缺口 | 需要 |
|---|---|
| Raw Query 最大长度 | 明确数值 |
| 关键词 / 条件数量限制 | 明确数值 |
| 条件嵌套深度 | 明确数值 |
| Relation Path 最大深度 | 明确数值，与 TDD §3.10 一致 |
| Request / Resource Timeout | 补充实现验收 |
| Rate / Concurrency | 补充实现验收 |
| Unicode / Control Character | 基础规范化边界 |
| Error / Log 输入泄漏 | 明确禁止原文和完整条件 |

定位：这是 Contract Hardening，不是已确认的严重注入漏洞。

## 影响

- 安全：超长输入、深层条件和异常请求可能造成资源消耗；
- 性能：请求边界不明确可能放大查询和解析成本；
- 合规：日志不得记录用户原始输入；
- 用户体验：超限请求需要明确的 `INVALID_REQUEST`。

## 已有防护

| 注入类型 | 现状 |
|---|---|
| SQL 注入 | Odoo ORM 参数化查询 |
| ORM 注入 | 前端不拼接 domain，条件使用结构化 JSON |
| 权限注入 | 权限来自服务端 `request.env`，不信任请求体 |
| 动态代码执行 | 架构级禁止 |

## V1 必须补充的边界

### Search Request Boundary

1. Raw Query 最大长度：≤ 500 字符；
2. 关键词 / 条件数量：≤ 20 个；
3. 条件嵌套深度：≤ 3 层；
4. Relation Path 最大深度：≤ 2 层；
5. Request Timeout：≤ 5 秒；
6. Resource Timeout：≤ 3 秒；
7. Result limit / pagination limit 沿用 CC-002；
8. Rate limit / concurrency limit 沿用 CC-002；
9. 动态代码和可执行 domain 禁止进入请求协议。

### Error / Log Boundary

1. 服务端错误消息使用服务端控制模板；
2. 用户 Query 和条件值不得插入错误消息；
3. 前端使用文本渲染错误消息，不把用户输入作为 HTML；
4. 日志不记录 Raw Query；
5. 日志不记录完整 conditions；
6. 日志不记录业务字段值；
7. 如需输入摘要，只允许记录 `hash(query)`。

## 明确不采用

- 字符白名单防注入；
- 全局 SQL 通配符转义；
- 全局正则元字符转义；
- 将 Unicode NFC 作为安全阻塞项；
- 复杂日志转义系统替代“不记录原文”；
- 面向内部 NAT 用户的 IP 限流；
- 在 AI Search 之前引入 Prompt Injection 防护。

## V1.x / V2

| 项目 | 时机 | 说明 |
|---|---|---|
| Unicode NFC 完整规范化 | V1.x | 搜索质量问题，不作为安全边界 |
| 特殊字符语义 | V1.x | 由 Operator / Field Adapter 定义 |
| IP 限流 | V2 / 对外开放时 | 避免内部 NAT 误伤 |
| AI Prompt Injection 防护 | 未来 AI Search | 单独设计 |

## 验收标准

| 项 | 标准 |
|---|---|
| Raw Query 超长 | 返回 `INVALID_REQUEST` |
| 条件数量超限 | 返回 `INVALID_REQUEST` |
| 条件嵌套超深 | 返回 `INVALID_REQUEST` |
| Relation Path 超深 | 返回 `INVALID_REQUEST` |
| Request Timeout | 返回 `TIMEOUT` |
| Resource Timeout | 返回 `TIMEOUT` |
| Rate limit 超限 | 返回 `RATE_LIMITED` |
| Concurrency 超限 | 返回 `RATE_LIMITED` |
| 错误消息 | 不包含用户输入 |
| 日志 | 不包含 Raw Query |
| 前端渲染 | 使用文本节点或 `textContent`，不用用户输入拼接 `innerHTML` |

## 处理时机

```text
CC Freeze
   ↓
Implementation
   ↓
TD-001 安全边界落实（CC-002 / CC-007）
   ↓
V1 Acceptance
```

TD-001 不阻塞 CC-001~CC-007 Freeze，但必须在 V1 实现前进入 CC-002 / CC-007 的实施与验收。

## 关联文档

| 文档 | 关联点 |
|---|---|
| SRS V1.4 | FR-L3-001、FR-ER-002 |
| TDD V0.3 | §3.3、§3.9、§3.10、§3.13 |
| CC-002 | API 契约、安全和请求边界 |
| CC-007 | 错误协议、日志和失败关闭 |

## 后续动作

| # | 动作 | 负责 | 截止 | 状态 |
|---|---|---|---|---|
| 1 | 在 CC-002 中补充 Search Request Boundary | — | 2026-10-06 | 完成 |
| 2 | 在 CC-007 中补充 Error / Log 规则 | — | 2026-10-06 | 完成 |
| 3 | 补充边界验收测试 | — | 2026-10-06 | 完成 |
| 4 | V1 Acceptance 前完成验收 | — | 2026-10-06 | 完成 |

## 备注

- 不改变现有架构；
- 不改变 CC-002 / CC-003 Permission Boundary；
- 不采用字符白名单或统一特殊字符过滤；
- 不将该技术债描述为已确认的注入漏洞。

## 变更历史

| 版本 | 日期 | 变更 | 作者 |
|---|---|---|---|
| v0.1 | 2026-10-05 | 初始登记 | — |
| v0.2 | 2026-10-05 | 重写为 Search Request Boundary Hardening | — |
| v0.3 | 2026-10-06 | 完成 CC-002/CC-007 落实和边界验收 | — |
