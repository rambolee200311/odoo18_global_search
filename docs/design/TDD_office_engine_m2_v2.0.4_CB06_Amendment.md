# Office Engine M2 TDD V2.0.4 — CB-06 Finalize Alignment Amendment

| 项目 | 内容 |
|---|---|
| 基线 | Frozen TDD V2.0.3 |
| 变更范围 | 仅对齐已冻结 CC-M2-CB-06 v0.2 中已接受 Candidate 的 Finalize 语义 |
| 状态 | **AUTHORIZED IMPLEMENTATION AMENDMENT — SCOPE LIMITED TO CC-M2-CB-06** |
| 生效依据 | 负责人批准冻结并实施 CC-M2-CB-06 v0.2 |

本文件为 V2.0.3 的窄范围、版本化补充；保留 V2.0.3 原件和历史文字。本补充只覆盖下列条款，不改变 CB-03 验证等级含义、权限/安全/文件完整性门、CB-02 的受控接受入口或 M1 行为。

## 替换与补充条款

### §5.2 状态语义补充

- `VERIFIED` 和 `PARTIALLY_VERIFIED` 描述验证结果；`accepted_current` 描述 CB-02 已完成的用户授权接受。二者是独立维度。
- CB-02 可在其受控接受机制及既定授权条件满足时接受 `PARTIALLY_VERIFIED` Candidate；接受不改变其原验证等级。
- `FAILED`、`REJECTED`、`STALE` 或未接受 Candidate 不得成为 Current，也不得 Finalize。
- 只有 Current 已被正式接受，才可进入 Finalize；Finalize 不代替 Accept，也不推进 Current、Last Valid 或 Document Revision。

### §6.3 `PARTIALLY_VERIFIED` 交付语义

`PARTIALLY_VERIFIED` 的技术判定及未验证事项含义不变。它本身不是接受或交付授权。若 CB-02 已按既有受控流程将其正式接受为 Current，CB-06 可以交付该 Current；Finalize 不重新运行 Validator、不改变验证等级、不宣称未验证事项已解决。`FAILED` 仍不可接受或交付。权限、安全、资源和文件完整性限制不能由用户 Accept 或 Finalize 绕过。

### Appendix A.3.1 生命周期

将“`partially_verified / failed / stale → never accepted_current`”替换为：

```text
partially_verified + valid CB-02 acceptance → accepted_current (grade remains PARTIALLY_VERIFIED)
failed / rejected / stale → never accepted_current
accepted_current → CB-06 finalize/delivery; finalize does not validate or promote the grade
```

### Appendix A.3.2 接受/交付规则

- `VERIFIED`：按 CB-02 既有接受授权成为 Current；接受后可按 CB-06 规则 Finalize。
- `PARTIALLY_VERIFIED`：仅在 CB-02 既有受控接受入口接受后成为 Current；接受及 Finalize 均保留该等级，并继续展示未验证事项。
- `FAILED`：不得接受或交付，Current/Last Valid 保持不变。

以上不要求修改 CB-03 的 Receipt schema 或验证行为。

### Appendix A.3.4 逻辑接口

`accept_candidate(candidate, authorization)` 可接收 `VERIFIED` 或 `PARTIALLY_VERIFIED` Candidate，但只能通过 CB-02 服务端受控接受流程；实际授权主体、Thread、Session、Candidate、父版本、revision、附件字节/SHA 和适用绑定必须按 CB-02 契约重验。客户端不得直接改变状态。

`finalize(accepted_current)` 只接受服务端解析的当前已接受版本，复用该版本的私有附件字节并登记 Thread 消息/交付引用；不执行候选验证、不重新接受 Candidate、不改变验证等级或版本指针。

### Appendix A.5 测试预期

测试须证明：已接受的 `PARTIALLY_VERIFIED` Current 可正式交付且等级不变；`FAILED` 或未接受 Candidate 不可交付；重复 Finalize 复用同一附件和消息；Finalize 不改变 Current、Last Valid、Document Revision 或 SHA；权限、Thread/Session 绑定及附件完整性失败仍会阻止交付。

## 保持不变

V2.0.3 的其余条款、验证能力矩阵、Provider 外发政策、M1 流程和 Candidate 验证定义保持不变。此 Amendment 不授权真实 Provider 调用或生产部署。
