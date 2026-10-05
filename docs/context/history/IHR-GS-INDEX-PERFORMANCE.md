# IHR-GS-INDEX-PERFORMANCE

## 实施范围

CC-006 已冻结为可选的轻量性能验证。首轮实施只增加索引策略映射和兼容性校验，不执行生产迁移、不执行冷缓存或 20 并发压测。

## 已实现

- `services/index_strategy.py`：
  - Exact → B-tree；
  - Prefix → `text_pattern_ops`；
  - Contains → GIN trigram；
  - 支持显式 `none`；
  - 拒绝未知或不兼容策略。
- `tests/test_index_strategy.py` 覆盖默认映射、可选索引和不兼容策略。

## 边界

性能数据生成、5 万级热缓存探针和 5 并发测试可在开发环境单独执行；不阻塞 CC-001~CC-005 上线。
