# SPIKE-GS-02 Entity Resolution 评分报告

## 1. 执行信息

| 项 | 值 |
|---|---|
| ID | SPIKE-GS-02 |
| 版本 | v0.1 |
| 状态 | Executed - Conditional |
| 执行日期 | 2026-10-02 |
| 数据库 | `odoo18ce` |
| 用户 | Odoo ORM 当前用户，UID 1 |
| 固定种子 | `20261002` |

## 2. 摘要

本 Spike 在 `res.partner` 中通过 Odoo ORM 创建了 1,000 条带 `GS02-` 标记的相似实体记录，覆盖完全同名、简称、别名、拼音近似和大小写差异。

评分规则能够稳定复现排序和决策：

- 唯一标识符命中：110 分，分差 110，判定 `unique_match`；
- 完全同名：100 分，但 20 个同名实体并列，分差 0，判定 `candidate_list`；
- 简称/别名多字段同时命中：90 分，分差 0，判定 `candidate_list`；
- 拼音近似：60 分，分差 0，判定 `candidate_list`；
- 大小写归一化：95 分，分差 0，判定 `candidate_list`；
- 候选最多返回 10 个，并正确设置 `has_more=true`；
- 所有查询的重复执行结果稳定，阈值 30 的边界行为符合要求。

整体结论：**有条件可行**。评分顺序、阈值决策、稳定排序和候选截断已得到技术证据；生产评分公式、字段权重和拼音算法仍需在 TDD 中正式定义。

## 3. SRS 追溯

- FR-L2-002：实体匹配规则；
- FR-L2-003：实体歧义处理；
- CFG-010：唯一命中阈值 30、候选最大数量 10 和可配置权重；
- AC-005：分差小于 30 时展示候选；
- AC-006：分差大于等于 30 时唯一命中。

## 4. 测试数据

| 项 | 结果 |
|---|---:|
| 请求记录数 | 1,000 |
| 实际创建记录数 | 1,000 |
| 当前标记记录数 | 1,000 |
| 技术模型 | `res.partner` |
| 数据写入 | Odoo ORM，已提交 |
| 数据标记 | `GS02-` |

每个测试实体包含名称、编号、简称、别名、拼音近似字段和地址标记。重复执行生成脚本会复用已有 `GS02-` 编号，不重复创建。

## 5. 评分规则

| 匹配类型 | 基础分 |
|---|---:|
| 编号精确匹配 | 110 |
| 名称精确匹配 | 100 |
| 名称大小写归一化匹配 | 95 |
| 简称匹配 | 80 |
| 别名匹配 | 70 |
| 拼音近似匹配 | 60 |
| 多字段额外命中 | 每个 +10，最多 +20 |

排序键为 `(score DESC, id ASC)`。本 Spike 的多字段案例中，简称和别名同时命中，基础分 80 加 10，最终为 90 分。

## 6. 结果

| 场景 | 最高分 | 次高分 | 分差 | 命中实体数 | 返回数 | 决策 | 截断提示 |
|---|---:|---:|---:|---:|---:|---|---|
| 唯一编号精确 | 110 | 0 | 110 | 1 | 1 | `unique_match` | 否 |
| 完全同名 | 100 | 100 | 0 | 20 | 10 | `candidate_list` | 是 |
| 简称 | 90 | 90 | 0 | 20 | 10 | `candidate_list` | 是 |
| 别名 | 90 | 90 | 0 | 20 | 10 | `candidate_list` | 是 |
| 拼音近似 | 60 | 60 | 0 | 20 | 10 | `candidate_list` | 是 |
| 大小写差异 | 95 | 95 | 0 | 20 | 10 | `candidate_list` | 是 |

原始证据见 `results/spike_result.json`，数据写入证据见 `results/simulation_result.json`。

### 6.1 阈值边界

在评分决策函数中验证：

| 分差 | 预期 | 实际 |
|---:|---|---|
| 30 | `unique_match` | `unique_match` |
| 29 | `candidate_list` | `candidate_list` |

因此，阈值比较采用 `>= 30`，与 CFG-010 和 AC-006 一致。

### 6.2 候选截断

20 个候选实体的场景均只返回前 10 个，并设置 `has_more=true`。这证明后续 UI 可以根据该信号显示“还有更多候选”提示；本 Spike 不实现前端文案。

### 6.3 稳定性

每个输入均执行两次比较；此外对 `E01` 重复执行五次。所有重复结果的决策、分数、候选数量和 ID 排序完全一致，`same_input_stable=true`。

## 7. 成功标准判定

| 子问题 | 判定 | 证据 |
|---|---|---|
| 精确、简称、别名、拼音评分差异 | 通过 | 评分分别为 100、90、90、60；多字段加分已记录 |
| 多字段合并 | 通过 | `short_name + alias` 得 90 分 |
| 分差阈值 30 | 通过 | 30/29 边界测试符合预期 |
| 候选截断感知 | 通过 | 10/20 返回并设置 `has_more=true` |
| 同输入同结果 | 通过 | 所有场景重复稳定 |

## 8. 限制与后续工作

1. 本 Spike 的“拼音近似”使用预生成的拼音字段标记验证评分层，不代表最终拼音转换算法；
2. 当前样本集中每个名称组有 20 个实体，尚未覆盖真实多公司 Record Rule 隔离；
3. 评分公式仅为技术验证模型，CFG-010 的管理员配置模型需在 TDD 中定义；
4. 需要在后续权限与多公司 Spike 中验证简称、别名不得跨公司；
5. 需要在 TDD/TV 中确认字段权重、同分 tie-breaker 和候选展示文案。

## 9. 复现

```bash
cd /Users/lijianqiang/Documents/odoo18_global_search
./venv/bin/python odoo-bin shell -c odoo.conf --no-http \
  < mymodules/wd_spike_global_search/spike_02_entity_resolution/data/generate_orm.py
./venv/bin/python odoo-bin shell -c odoo.conf --no-http \
  < mymodules/wd_spike_global_search/spike_02_entity_resolution/scripts/run.py
```

## 10. 产出物

- `PLAN.md`
- `README.md`
- `data/generate_orm.py`
- `scripts/run.py`
- `results/simulation_result.json`
- `results/spike_result.json`
- `reports/REPORT.md`

