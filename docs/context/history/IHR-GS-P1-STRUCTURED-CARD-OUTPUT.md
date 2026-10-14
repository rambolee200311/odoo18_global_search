# IHR-GS-P1-STRUCTURED-CARD-OUTPUT

## 0. 治理与基线

| 项 | 内容 |
|---|---|
| 问题 | P1-05：模板卡片与结构化字段卡片采用不同输出形态 |
| 模块 | `wd_global_search` |
| 基线 | `main @ 878a2f7` + 本次工作树 |
| 状态 | **BLOCKED：须先进行独立输出契约评审** |
| 日期 | 2026-10-14 |

## 1. 核查结果（未实施）

| 核查点 | 现状 |
|---|---|
| CC-014 | 将模板结果定义为常量/字段变量组成的纯文本输出，并要求浏览器以 text node 展示 |
| CC-014-1 | 继承 CC-014 的纯文本模板渲染；不定义标题、摘要、Meta、明细等独立结构化输出槽位 |
| CC-013 | 无模板 Card 使用 `snapshot.fields`，按字段顺序展示 Label/Value |
| Executor | 配置模板时仅生成 `snapshot.rendered_text`；未配置模板时才生成 `snapshot.fields` |
| Workspace | 有 `rendered_text` 时按文本显示，不从内容推断字段语义；结构化 `fields` 才有独立 DOM 节点 |

## 2. 停止原因

要让管理员配置模板后仍输出独立的卡片主标题、Meta、摘要和明细，需要新定义结构化模板输出/字段角色、Search response shape 与兼容规则。仅改 CSS/JS 无法从纯文本安全还原语义；改 executor 输出则会改变冻结 CC-014/CC-014-1 所定义的纯文本接口。

依任务停止条件，未修改服务、API、前端、SRS、TDD 或既有 CC；未新增或代拟新的 Coding Contract。应先评审一个独立 CC/正式契约变更，明确配置语法、结构化输出 schema、无模板兼容、权限过滤及测试边界。

## 3. 下一步门禁

在新的结构化输出契约获正式批准前，P1-05 保持 BLOCKED，不得解析 `rendered_text`、猜测字段、改变 response shape 或绕过既有纯文本安全边界。
