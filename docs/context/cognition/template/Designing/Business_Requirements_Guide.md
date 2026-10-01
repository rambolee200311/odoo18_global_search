# Business Requirements Guide
## 业务需求梳理指导说明

> Document Type: Guide  
> Version: v0.1 Draft  
> Applicable Scope: Software / Odoo Custom Development  
> Positioning: Business Requirement Definition Guidance  
> Downstream: SRS — Software Requirements Specification

---

# 0. 定位

Business Requirements Guide 用于指导项目在进入 SRS 之前，对真实业务需求进行梳理、讨论、确认和收口。

本 Guide 不规定固定的 BRD 文档格式。

业务需求可以来源于：

- 业务人员口述；
- 业务会议；
- 现有 Excel / Word / WPS 文档；
- 现行业务流程；
- 现有系统；
- 客户需求；
- 管理层要求；
- 问题反馈；
- 操作案例；
- 邮件或聊天记录；
- 流程图；
- 业务规则说明；
- 已有 BRD；
- 其他能够证明业务事实的材料。

这些材料可以整理为：

- BRD；
- 业务规范；
- 需求讨论稿；
- 流程说明；
- 业务规则说明；
- 会议决议；
- 多份业务材料的组合。

不要求所有项目使用统一 BRD 模板。

核心目标只有一个：

> **在进入 SRS 之前，把业务问题讲清楚。**

---

# 1. BRD 与 SRS 的边界

BRD / Business Specification 关注：

> **真实业务是什么，以及业务为什么需要这样运行。**

SRS 关注：

> **软件系统必须提供什么能力，才能支持已经确认的业务。**

因此 BRD 不应提前承担 SRS、DDD 或 TDD 的职责。

典型关系：

```text
真实业务
    ↓
业务调查 / 讨论 / 梳理
    ↓
BRD / Business Specification
    ↓
Business Ready Gate
    ↓
SRS
    ↓
DDD（Optional）
    ↓
Technical Verification（按需）
    ↓
TDD