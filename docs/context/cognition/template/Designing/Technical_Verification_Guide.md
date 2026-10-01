# Technical Verification Guide
## 技术验证指导说明

## 1. 定位

Technical Verification（TV）用于在 TDD 编写前，对影响技术设计的关键不确定事项进行事实验证。

TV 的目的不是设计系统，而是回答：

> **这个技术假设是否真实成立？**

Technical Verification 是按需执行的活动，不是每个项目必须产生的正式设计文档。

---

## 2. 何时需要 Technical Verification

存在以下情况之一时，应在 TDD 前进行技术验证：

- 目标 Odoo 版本的能力或 API 不确定；
- 官方模块实际行为不确定；
- OCA / 第三方模块是否满足需求不确定；
- ORM、View、Owl、QWeb、Portal、PDF 等技术行为不确定；
- 外部 API / SDK / Protocol 的能力不确定；
- Module Upgrade / Migration 路径存在不确定性；
- 某项关键技术方案的可行性尚未被证明；
- 如果该假设错误，将明显影响 TDD 设计。

没有关键技术不确定性时，可以直接进入 TDD。

---

## 3. 验证方式

根据问题选择最简单、最可靠的验证方式：

- 阅读目标版本官方源码；
- 阅读官方文档；
- 检查现有项目代码；
- 检查 OCA / 第三方源码；
- `odoo-bin shell + ORM` 实际验证；
- 最小可运行实验；
- Technical Spike；
- API / Integration 实测；
- Module Upgrade 实测；
- 必要的性能实验。

原则：

> **只做足以消除技术不确定性的验证，不提前实现正式功能。**

---

## 4. 最小记录要求

Technical Verification 不要求固定模板。

但每个重要验证事项至少应留下：

### TV-XXX — {验证事项}

**Question**  
需要验证什么？

**Method**  
如何验证？

**Result**  
- VERIFIED
- NOT VERIFIED
- INCONCLUSIVE

**Evidence**  
支持结论的源码位置、运行结果、日志、实验代码、官方资料或其他证据。

**TDD Impact**  
该结果对 TDD 有什么影响？

---

## 5. 验证结果处理

### VERIFIED

技术假设成立。

结果可作为 TDD 的事实输入。

### NOT VERIFIED

技术假设不成立。

不得继续基于该假设编写 TDD，应调整技术方向；如果影响业务需求或领域设计，应升级到对应上游。

### INCONCLUSIVE

现有证据不足以得出可靠结论。

不得把假设当成事实写入 TDD，应继续验证或 Stop / Escalate。

---

## 6. 与 TDD 的边界

Technical Verification：

> **验证事实。**

TDD：

> **基于已确认的事实作出技术设计。**

因此 TV 不负责：

- 完整 ORM 设计；
- 完整 Service 设计；
- 完整事务设计；
- 完整并发设计；
- 完整 API Contract；
- 完整测试设计；
- Implementation Plan。

不得把 Technical Verification 演变成第二份 TDD。

---

## 7. 与 Odoo Engineering Rules 的关系

所有 Technical Verification 必须遵守：

- `Odoo_Engineering_Rules.md`

并参考：

- `Odoo_Engineering_Guidelines.md`

Technical Verification 不获得任何绕过 Engineering Rules 的特殊权限。

---

## 8. 核心原则

> **Verify uncertainty before designing around it.**
>
> **在围绕一个技术假设进行设计之前，先验证它。**

> **Technical Verification proves facts; TDD makes design decisions.**
>
> **TV 验证事实，TDD 作出设计。**