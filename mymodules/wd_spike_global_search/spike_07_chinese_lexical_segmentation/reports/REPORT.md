# SPIKE-GS-07 中文连续文本词法切分报告

## 1. 执行信息

| 项 | 值 |
|---|---|
| ID | SPIKE-GS-07 |
| 版本 | v0.1 |
| 状态 | Executed - Conditional |
| 执行日期 | 2026-10-02 |
| 语料数量 | 100 |
| 识别范围 | FR-L3-001 有限语法 |

## 2. 摘要

本 Spike 使用固定词典和确定性规则验证中文连续文本的语义单元切分，不承诺完整自然语言解析。

100 条测试输入全部正确：

- 识别率：100%（100/100）；
- `A客户今年6月没完成的出库单` 正确切分为 Entity、Time、State、Resource；
- `MSCU1234567 Rotterdam` 正确切分为 Identifier、Location；
- `上个月 出库` 正确切分为 Time、Resource；
- `张三 本周` 正确切分为 Entity、Time；
- 空格可选变体与连续文本结果等价；
- 无法识别输入全部安全降级为 Free Text；
- 同输入重复解析结果完全一致。

整体结论：**有条件可行**。在 SRS 明确的有限语法和固定词典范围内达到目标；不应将结果外推为完整中文自然语言理解。

## 3. SRS 追溯

- FR-L3-001：V1 有限查询语法；
- FR-L3-002：条件解析；
- AC-008：中文连续文本；
- FR-L3-005：Free Text 降级。

## 4. 测试语料

| 类别 | 数量 | 目标 |
|---|---:|---|
| 中文连续文本 | 20 | Entity + Time + State + Resource |
| Identifier + Location | 20 | `MSCU1234567 Rotterdam` |
| 月份 + Resource | 20 | `上个月 出库` |
| Entity + Time | 20 | `张三 本周` |
| 空格变体 | 10 | 连续文本与空格可选 |
| 完全 Free Text | 10 | 无法识别时安全降级 |
| **合计** | **100** |  |

## 5. 词法规则

执行顺序和规则：

1. 时间表达优先：`今年6月`、`今年 6月`、`上个月`、`本周`；
2. Identifier：匹配 `[A-Z]{4}[0-9]{7}`；
3. Entity：匹配配置词典中的 `A客户`、`张三`；
4. Location：匹配 `Rotterdam`；
5. State：`没完成` 和 `未完成` 映射为 `未完成`；
6. Resource：`出库单` 映射为 `出库`；
7. 助词 `的`、`了` 在存在已识别单元时忽略；
8. 剩余内容进入 Free Text；
9. 完全没有识别单元时保留完整输入作为 Free Text。

## 6. 结果

### 6.1 代表性结果

输入：

```text
A客户今年6月没完成的出库单
```

输出：

```text
Entity:   A客户
Time:     2026-06
State:    未完成
Resource: 出库
Free Text: ""
```

输入：

```text
MSCU1234567 Rotterdam
```

输出：

```text
Identifier: MSCU1234567
Location:   Rotterdam
Free Text:   ""
```

### 6.2 指标

| 指标 | 结果 | 目标 |
|---|---:|---:|
| 测试输入数 | 100 | 100 |
| 正确识别数 | 100 | >= 90 |
| 识别率 | 100% | >= 90% |
| Free Text 安全降级 | 100/100 | 100% |
| 重复解析稳定 | `true` | `true` |
| 失败案例 | 0 | 允许但需安全 |

### 6.3 安全降级

完全无法识别的输入，例如：

```text
不存在的自由文本01
```

输出：

```text
units: []
free_text: "不存在的自由文本01"
```

不会生成伪造的 Entity、Time、State 或 Resource 条件，也不会因此执行宽泛业务搜索。

## 7. 成功标准判定

| 子问题 | 判定 | 证据 |
|---|---|---|
| 核心中文连续文本 | 通过 | 20/20 |
| Identifier + Location | 通过 | 20/20 |
| Time + Resource | 通过 | 20/20 |
| Entity + Time | 通过 | 20/20 |
| 空格可选 | 通过 | 10/10 |
| Free Text 降级 | 通过 | 10/10 安全保留 |
| 识别率 >= 90% | 通过 | 100% |
| 同输入同结果 | 通过 | 所有案例重复一致 |

## 8. 限制与后续工作

1. 本 Spike 仅验证有限词典和确定性切分，不实现完整自然语言解析；
2. 年份缺省、时区和“6月”默认年份推断需由日期语义组件继续处理；
3. 词典应由 Business Resource、State、Location 配置提供，而不是硬编码；
4. 同义词推断、否定词、布尔表达式、括号和复杂句式仍属于 SRS OUT；
5. 需要在 TDD 中定义词典冲突时的评分和 Query Understanding 展示。

## 9. 复现

```bash
cd /Users/lijianqiang/Documents/odoo18_global_search
python3 mymodules/wd_spike_global_search/spike_07_chinese_lexical_segmentation/data/generate.py
./venv/bin/python odoo-bin shell -c odoo.conf --no-http \
  < mymodules/wd_spike_global_search/spike_07_chinese_lexical_segmentation/scripts/run.py
```

## 10. 产出物

- `PLAN.md`
- `README.md`
- `data/generate.py`
- `scripts/run.py`
- `results/query_corpus.json`
- `results/spike_result.json`
- `reports/REPORT.md`

