# ATR — M2 聊天入口接入

| 项目 | 结果 |
|---|---|
| 范围 | 将用户真实 `llm.thread.generate()` Office 上传消息路由到 M2 编排入口 |
| 状态 | 路由回归通过；真实 Provider 已到达并显示映射卡；完整业务生成未完成 |
| 环境 | Odoo 18、项目 `venv`、`odoo.conf`、既有 `odoo18ce` |
| Provider | OpenAI `gpt-5.6-luna`；本次受限真实调用 2 次（首次提案及修复重试） |
| UI | 内置浏览器确认消息流渲染 `office_mapping_card_v1` |

## 实施内容

- 在 `office_engine_m2` 中继承 M1 的 `_office_engine_generate_inspection` 扩展点；不修改官方 `llm_thread`。
- 用户提交单个 Office 模板及自然语言请求后，检查附件所有权、线程关联、格式和宏边界，再解析请求中的销售订单号。
- 按当前 Odoo 用户 ACL/记录规则检查目标记录；从部署安全字段基线筛选可用字段。
- 建立用户私有 Mapping Session，生成映射 Proposal，并将服务端卡片消息返回聊天流。
- Provider 请求异常会记录脱敏诊断信息；不会返回“文件已接收”之类的成功假象。
- 未配置数据用途策略或安全字段基线时，在读取/外发业务字段前停止。

## 自动化证据

定向聊天入口测试：`0 failed, 0 error(s) of 3 tests`。

全量 `office_engine_m2` 测试通过现有 `odoo18ce` 执行：

```text
PYTHONPATH=/private/tmp/cc_m2_002_shellshim ./venv/bin/python odoo-bin \
  -c odoo.conf -d odoo18ce --http-port=0 -u office_engine_m2 \
  --test-enable --test-tags /office_engine_m2 --stop-after-init \
  --log-level=test --logfile=/private/tmp/m2_chat_full_test.log

office_engine_m2: 90 tests 21.47s 6750 queries
0 failed, 0 error(s) of 68 tests
```

模型分类兼容修复后，全量回归再次执行：

```text
office_engine_m2: 90 tests 22.63s 6750 queries
0 failed, 0 error(s) of 68 tests
```

测试覆盖真实 `llm.thread.generate()` 入口、Mock Provider 的 Proposal/卡片路径、缺少部署授权时不调用 Provider，以及缺少明确业务记录时拒绝执行。

## 真实 Provider 与聊天复验

发现真实配置把 `gpt-5.6-luna` 分类为 `multimodal`，而 `_provider_model()` 只接受 `chat`，因此真实请求在 Provider 前被误拒绝。M2 请求只发送受限文本 JSON、不发送二进制附件；代码现接受 `chat` 和 `multimodal` 两种模型用途，并有回归测试。

在一次性验证进程中，负责人批准的字段范围仅包括 `sale.order` 的 `name`、`client_order_ref`、`date_order`、`amount_untaxed`、`amount_tax`、`amount_total`，以及模板可见文本标签。无客户地址或销售订单行字段。经该线程用户上下文调用同一 `llm.thread.generate()` 路由后：

```text
Provider usage attempts: 2 (gpt-5.6-luna)
Mapping Session: needs_clarification, revision=2
Mapping Proposal: 0 accepted mappings, 22 clarification items
Mapping card message: persisted and visible in the existing chat thread
Rendered output/download: not produced; confirmation remained disabled
```

真实结果说明模型分类误判已修复，实际聊天入口调用了 Provider 并显示映射卡；但当前授权字段范围不足以完成此 CMR。请求被正确停留在需澄清状态，没有生成不完整文件。一次性验证策略随后已移除，8091 服务已用项目 `venv` 和 `odoo.conf` 在无 M2 白名单环境下恢复。

## 尚未完成的项目

- 本次映射卡有 22 项澄清；未进行用户确认或 M1 渲染。
- CMR 完整填充需要后续明确并配置客户地址、联系人及销售订单行字段的授权策略，且须确认对应关联数据的外发范围。
- 目前部署没有持久化 M2 白名单；验证结束已恢复默认拒绝策略。不得将临时进程变量视为产品配置。

## 关闭判定

模型用途兼容修复与真实 Provider 卡片路径已验证。完整 CMR 生成仍为 **INCOMPLETE**，不能宣称端到端完成；需先通过受控配置为目标模型、字段及关联行数据定义可持续、可审计的授权策略，再验证确认和 M1 渲染交付。
