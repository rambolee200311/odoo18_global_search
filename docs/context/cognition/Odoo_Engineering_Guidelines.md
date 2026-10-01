# Odoo Engineering Guidelines
## Odoo 开发工程准则
## Status: Frozen
## Version Policy: Odoo 版本无关

本文件定义 Odoo 开发的默认工程行动准则。

这些准则属于 SHOULD / SHOULD NOT。

Agent 应默认遵守，但在具体项目存在明确、合理的工程原因时允许偏离。

偏离时必须：

1. 有明确技术理由；
2. 不违反任何 Odoo Engineering Rule；
3. 不改变 SRS / DDD / TDD 已冻结语义；
4. 重大偏离记录在适当的 TDD / Coding Contract / IHR 中。

---

## 1. Odoo Native First

优先使用 Odoo 原生能力解决问题。

默认优先顺序：

Odoo 原生能力
→ 简单 Model / View / Python
→ Odoo 官方扩展机制
→ 必要的成熟第三方组件
→ 自研额外技术

标准 Odoo 能够合理解决的问题，不增加额外技术层。

---

## 2. Simple Models

Model 应保持简单、直接、符合 Odoo ORM 习惯。

优先使用：

- 标准 Field；
- Many2one / One2many / Many2many；
- Related；
- Compute；
- Constraint；
- 标准 ORM Method；
- 清晰的 Business Action。

避免无必要增加：

- Repository；
- DAO；
- DTO；
- Mapper；
- Entity Wrapper；
- Generic Engine；
- 自建 ORM；
- 额外 Persistence Layer。

> **不要在 Odoo Framework 上再造一个 Framework。**

---

## 3. Simple Views

View 应优先使用 Odoo 标准能力：

- Form；
- List；
- Search；
- Kanban；
- Wizard；
- Domain；
- Context；
- Modifier；
- Standard Widget；
- View Inheritance。

标准 XML View 可以合理解决的问题，不开发自定义 Owl / JavaScript / Widget。

避免：

- 复杂 XPath；
- 多层脆弱继承；
- 复制整个官方 View；
- 大量动态 UI 逻辑；
- 将核心业务正确性建立在 UI 隐藏逻辑上。

---

## 4. Explicit Business Logic

核心业务规则应清楚地存在于 Model / Business Action 中。

避免：

- 隐式副作用；
- Compute 中执行复杂业务动作；
- Context 中隐藏关键业务事实；
- View 中实现核心业务规则；
- 通过技术技巧隐藏实际执行路径。

> **Simple Models, Simple Views, Explicit Business Logic.**

---

## 5. Robust Before Clever

优先选择：

- 清晰；
- 可预测；
- 易测试；
- 易排错；
- 易升级；
- 易维护；

的代码。

避免为了技术技巧使用：

- Meta-programming；
- Monkey Patch；
- Runtime Method Replacement；
- 复杂 Decorator；
- 过度 Generic；
- 难以理解的动态代码。

> **健壮优先于聪明。**

---

## 6. Avoid Premature Abstraction

不要为了消除少量重复代码过早建立通用框架。

少量、清晰、容易理解的重复代码，可以优于错误的抽象。

只有多个场景已经形成稳定、真实的共同模式时，再进行抽象。

> **可以拆方法，不要轻易造框架。**

---

## 7. Minimize Additional Technology

能够通过 Odoo 原生能力稳定完成的，不应无必要引入：

- Redis；
- Kafka；
- RabbitMQ；
- Celery；
- 独立 Worker；
- 微服务；
- Elasticsearch；
- 独立缓存层；
- Event Bus；
- CQRS；
- Event Sourcing；
- 自建前端框架；
- 大型第三方技术依赖。

额外技术必须解决真实存在的问题。

> **技术复杂度必须由问题驱动，而不是由 Agent 的技术偏好驱动。**

---

## 8. Real Odoo Behavior First

设计、编码和测试应尽可能遵循真实 Odoo Runtime 行为。

优先：

- ORM；
- 正式 Business Action；
- 真实用户权限；
- 真实 Module Dependency；
- 真实 Odoo Runtime；
- 真实 Upgrade Path。

Mock、Shortcut 和辅助脚本可以用于开发，但不能替代对关键真实行为的验证。

---

# Agent Default Decision Rule

当存在多个可行方案时，默认选择：

**Odoo Native
→ Simple
→ Explicit
→ Robust
→ Testable
→ Maintainable**

而不是：

**More Layers
→ More Frameworks
→ More Infrastructure
→ More Cleverness**

最终原则：

> **Use the simplest Odoo-native solution that robustly satisfies the requirement.**
>
> **在能够稳健满足需求的前提下，优先采用最简单的 Odoo 原生方案。**