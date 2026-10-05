# ATR GS-SEARCH-PERMISSION-BOUNDARY

## 0. 文档治理

| 项 | 内容 |
|---|---|
| ATR 文档 | `ATR-GS-PERMISSION-BOUNDARY.md` |
| CC | [CC-003](../intent/CC-003_global_search_permission_boundary.md) v0.2 FROZEN |
| IHR | [IHR-GS-PERMISSION-BOUNDARY](./IHR-GS-PERMISSION-BOUNDARY.md) |
| 状态 | PARTIAL |
| Environment | Odoo 18 / Python 3.11 / `odoo18ce` |
| Execution Date | 2026-10-05 |

## 1. Automated Evidence

| Check | Result |
|---|---|
| `compileall` | PASS |
| Odoo module upgrade and `--test-enable` | PASS |
| `git diff --check` | PASS |
| Permission boundary unit tests | PASS |
| Direct configuration model read by ordinary user | DENIED as expected |
| Ordinary user company-scoped Search | PASS |
| Portal resource access | FAIL-CLOSED with `RESOURCE_NOT_ACCESSIBLE` |

## 2. CC-003 Coverage

| Contract | Result | Evidence |
|---|---|---|
| CC3-TEST-001 UserContext/request authority | PARTIAL | Service always builds context from `env`; request payload does not provide identity |
| CC3-TEST-002 Record Rule/model access | PARTIAL PASS | Existing users 102/103 and ORM Search |
| CC3-TEST-003 Field permission | UNIT PASS | Fake restricted-field boundary test; real restricted business field fixture pending |
| CC3-TEST-004 Relation Path | UNIT PASS | Non-relation path rejection test; real middle-segment fixture pending |
| CC3-TEST-005 Failure close | PASS | Portal users receive `RESOURCE_NOT_ACCESSIBLE`, no business results |
| CC3-TEST-006 Multi-company/Portal | PARTIAL PASS | Company 1/2 and Portal ORM evidence |
| CC3-TEST-007 Permission change | NOT RUN | Requires controlled user permission mutation and new request |
| CC3-TEST-008 CC-001/CC-002 regression | PASS | Module tests and current-user browser Search |
| CC3-TEST-009 Cross-user cache isolation | NOT RUN | No shared result cache exists; explicit integration test pending |
| CC3-TEST-010 Published permission references | PARTIAL | Published config consumed through control-plane boundary; invalid reference fixture pending |

## 3. Current Conclusion

CC-003 尚未完成。权限边界基础实现和多公司/Portal 的 ORM 证据已建立；字段权限、关系路径中间段、权限变化、跨用户缓存和正式浏览器 HVR 仍需补齐。
