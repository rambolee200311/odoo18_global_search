# M2 动态列表映射技术设计补充 V1.1.0

| 项目 | 内容 |
|---|---|
| 状态 | **FROZEN V1.1.0** |
| 批准 | 负责人于 2026-10-23 批准 CC-M2-005 动态列表映射进入实施；本补充限定其技术语义 |
| 基线 | `TDD_office_engine_m2.md` V1.0.0 Frozen；本文件只补充列表映射，不改写历史版本 |
| 范围 | M2 AI 映射提案、映射卡片、授权集合读取及 M1 writes 编译 |

## 1. 兼容契约

列表循环是服务端对多个明确目标映射的分组/展开行为，不是任意坐标生成能力。Proposal 继续使用 `m2.mapping-proposal.v1` 和 `mappings[]`。模型必须逐项引用本次服务端提供的具体 `element_id`；不得输出 `list_mappings`、坐标偏移、行号公式、Python、业务值或新目标。这样保持 `office_mapping_verify` V1 和 M1 Mapping Plan V1 的契约兼容。

## 2. 服务端列表上下文

内部服务可为一个 Session 配置有限的 `mapping_groups`。每组由服务端提供：

- `group_id`：稳定标识；
- `collection_field`：目标记录上的关系字段，必须是经当前用户读权限检查的 O2M/M2M；
- `relation_model`：必须等于该关系字段的 `comodel_name`；
- `row_count`：本轮授权读取到的集合记录数，范围 1–50；
- `target_rows`：每个稳定行索引及该行有限的 `{column_id, element_id}` 目录；所有目标必须存在于 TargetManifest 且唯一；
- `allowed_fields`：关系模型允许提供给 AI 的标量字段类型映射，必须与部署安全字段基线及当前字段 ACL 取交集。

`target_rows` 数、连续行索引、每行列 ID 和 `row_count` 必须匹配。超限、重复、缺行或与 Odoo 字段元数据不符时，拒绝配置。

## 3. AI 输出及用户交互

Prompt 说明模型可以识别单字段映射，也可以识别集合循环需求（例如订单明细）；后者必须将每个集合列映射展开为该组 TargetManifest 中明确提供的逐行 `element_id`。目标不够、集合长度不匹配或映射不确定时，输出澄清，不猜测。

卡片逐行显示具体目标单元格。分组摘要由服务端生成，例如“将按订单明细顺序遍历 6 条记录，填充 6 行”；UI 将模型映射的 `source_field` 与目标所属的服务端行槽位关联。用户逐行修改仍提交普通标量 edits，原有 Validator、ACL、状态和 revision 门禁保持有效。

## 4. 授权读取与 M1 编译

运行时先在当前 `env` 对目标记录、关系字段、关系记录和字段读权限重新校验。集合记录 ID 由服务端读取关系字段得到；因现有 Retriever 的 domain schema 不支持 `in` 列表值，服务端对最多 50 个授权 ID 逐条调用既有 `odoo_record_retriever`，domain 固定为 `id = 当前服务端 ID`、fields 固定为已批准字段、limit 固定为 1。每次响应必须恰好对应该记录；保持关系 recordset 顺序，不足、额外、重复或超限均失败关闭。禁止 `sudo()`、客户端传入模型/domain/ID/字段或模型扩大查询。

服务端根据 `target_rows[row_index]` 将关系记录的已授权标量字段转成 M1 `writes[]`。输出仍为 M1 Mapping Plan V1 的显式 `set_value`。目标 ID 全部来自既有 manifest；集合记录数不等于服务端目标槽位数时拒绝生成，不静默截断、补空值或创建坐标。M1 原有校验、回读与幂等交付不变。

## 5. 失败行为和测试门禁

未知集合/字段/目标、关系字段类型不符、权限变更、记录数与目标槽位数不匹配、Retriever 返回不完整、必填目标遗漏或一次修复后仍不完整时，Session 进入 `needs_clarification` 或受控 `failed`；不调用 M1、不创建可下载输出。

自动验收至少覆盖：Proposal 对至少 5 个显式目标的校验；集合字段只从服务器目录读取；关系记录顺序与目标行顺序一致；集合数越界/少行/多行拒绝；逐行修订互不影响；二次校验失败不进入 M1；真实 `office_core` 生成与 `office_verify` 回读；普通聊天回归。所有真实 API 调用须符合已批准的数据政策；自动化优先使用 Provider Mock。

## 6. 冻结边界

本补充不修改冻结 SRS、M1、`office_mapping_verify` V1、M1 Mapping Plan V1、Provider 集合或数据库权限边界。无法满足上述服务端有限目录与授权 Retriever 条件时，列表映射保持关闭；标量映射仍按 TDD V1.0.0 处理。
