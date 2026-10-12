# ATR-GS-RELATION-FIELD-MULTI-LEVEL

## 1. Execution Metadata

| Field | Value |
|---|---|
| Intent ID | `GS-SEARCH-RESULT-CARD-RELATION-FIELD-MULTI-LEVEL` |
| IHR | [IHR-GS-RELATION-FIELD-MULTI-LEVEL.md](./IHR-GS-RELATION-FIELD-MULTI-LEVEL.md) |
| Contract | [CC-014-1 v0.1 FROZEN](../intent/CC-014-1_relation_field_multi_level.md) |
| Module | `wd_global_search` |
| Environment | Odoo 18 CE, local `odoo18ce`, macOS |
| Code baseline | `09f2629` plus uncommitted CC-014-1 changes, including the 100-sample performance test |
| Executed by | Copilot assistant |

## 2. Test Contract Baseline

The authoritative requirements are CC14-1-TEST-001~038 in CC-014-1 §15. This ATR records
execution evidence and gaps; it does not replace or reduce the frozen contract.

## 3. Current Automated Test Status

| Check | Result |
|---|---|
| Final `wd_global_search` Odoo module suite | PASS — 59 tests, 0 failures, 0 errors |
| CC14-1-TEST mapping | 38/38 PASS; multiple requirements share focused test methods |
| Python `py_compile` on changed Python files | PASS |
| `node --check` on `template_designer_page.js` | PASS |
| `git diff --check` | PASS |
| Human/browser verification | User-confirmed pass; see HVR-RUN-001 |
| 100-sample parser / validation / renderer benchmark | PASS; all measured P95 values are below CC-014 §7.3 budgets |
| Preview API end-to-end benchmark | PASS — 100 successful actual Preview API requests; P95 16 ms |
| Overall automated evidence | PASS for the executed module suite; not a Contract closure decision |

## 4. Core Test Contract Coverage Matrix

| CC14-1 Test | Automated evidence | Result |
|---|---|---|
| 001 | `test_warehouse_many2one_paths_render_one_two_and_three_hops` | PASS |
| 002 | `test_warehouse_many2one_paths_render_one_two_and_three_hops` | PASS |
| 003 | `test_warehouse_many2one_paths_render_one_two_and_three_hops` | PASS |
| 004 | `test_warehouse_many2one_path_over_three_hops_is_rejected` | PASS |
| 005 | `test_many2many_paths_render_values_and_use_configured_separator` | PASS |
| 006 | `test_many2many_paths_render_values_and_use_configured_separator` | PASS |
| 007 | `test_many2many_path_depth_and_mixed_relation_types_are_rejected` | PASS |
| 008 | `test_many2many_path_depth_and_mixed_relation_types_are_rejected` | PASS |
| 009 | `test_many2many_path_depth_and_mixed_relation_types_are_rejected`; `test_one2many_cannot_be_used_as_a_scalar_or_path` | PASS |
| 010 | `test_one2many_cannot_be_used_as_a_scalar_or_path` | PASS |
| 011 | `test_search_executor_renders_one2many_rows_from_the_search_root`; `test_one2many_order_lines_render_current_item_paths_and_format_keys` | PASS |
| 012 | `test_empty_one2many_loop_emits_no_loop_body`; loop content is rendered between surrounding constants | PASS |
| 013 | `test_nested_one2many_loops_render_current_scope_only` | PASS |
| 014 | `test_loop_labels_nesting_count_and_body_length_are_bounded` | PASS |
| 015 | `test_one2many_order_lines_render_current_item_paths_and_format_keys`; `test_loop_scope_rejects_fields_only_available_on_the_root_model` | PASS |
| 016 | `test_loop_scope_rejects_fields_only_available_on_the_root_model` | PASS |
| 017 | `test_empty_one2many_loop_emits_no_loop_body` | PASS |
| 018 | `test_one2many_order_lines_render_current_item_paths_and_format_keys` | PASS |
| 019 | `test_one2many_order_lines_render_current_item_paths_and_format_keys` verifies formatted Monetary values | PASS |
| 020 | `test_one2many_order_lines_render_current_item_paths_and_format_keys`; `test_loop_constants_escapes_and_html_remain_plain_text` | PASS |
| 021 | `test_loop_constants_escapes_and_html_remain_plain_text` | PASS |
| 022 | `test_loop_labels_nesting_count_and_body_length_are_bounded` | PASS |
| 023 | `test_loop_labels_nesting_count_and_body_length_are_bounded` | PASS |
| 024 | `test_loop_labels_nesting_count_and_body_length_are_bounded` | PASS |
| 025 | `test_loop_labels_nesting_count_and_body_length_are_bounded` | PASS |
| 026 | `test_loop_constants_escapes_and_html_remain_plain_text` verifies literal text output | PASS |
| 027 | `test_search_executor_resolves_from_the_searched_warehouse_root` | PASS |
| 028 | `test_search_executor_renders_one2many_rows_from_the_search_root` | PASS |
| 029 | `test_relation_rule_filters_many2many_members_for_current_user` | PASS |
| 030 | `test_one2many_loop_applies_current_users_record_rules` | PASS |
| 031 | Search Executor and Published Card renderer tests in `test_template.py` | PASS |
| 032 | `test_navigation.py` regression tests in the full module run | PASS |
| 033 | `test_empty_many2one_and_many2many_paths_render_an_em_dash`; `test_empty_one2many_loop_emits_no_loop_body` | PASS |
| 034 | `test_many2many_paths_render_values_and_use_configured_separator`; `test_many2many_separator_uses_the_published_snapshot_lifecycle` | PASS |
| 035 | `test_many2many_path_depth_and_mixed_relation_types_are_rejected` | PASS |
| 036 | `test_structure_validation_uses_model_metadata_without_business_reads` | PASS |
| 037 | Shared validator tests plus invalid Apply / active Snapshot preservation tests | PASS |
| 038 | `test_relation_template_performance_uses_100_samples`; parser, validation, and cold-/warm-cache rendering measured for each relation type | PASS |

## 5. Test Run History

### ATR-RUN-001 — Initial full-suite execution

| Field | Value |
|---|---|
| Scope | `wd_global_search` module tests |
| Result | FAIL — 57 tests; 1 failure and 13 errors |
| Observed causes | Parser translation helper shadowing; current-scope/related-field rejection for the frozen `product_id.name` example; a fake recordset missing `browse`; and a group-scoped record-rule fixture whose rule semantics did not restrict the test user as intended |
| Follow-up | Corrected in IHR-004; retained here as failure history |

### ATR-RUN-002 — Focused template retest before currency compatibility fix

| Field | Value |
|---|---|
| Scope | `TestCardTemplate`, 28 tests |
| Result | PARTIAL — 1 error in Monetary currency-field validation |
| Follow-up | Resolved in IHR-004 by using Odoo's model-aware `get_currency_field()` |

### ATR-RUN-003 — Focused template retest

| Field | Value |
|---|---|
| Scope | `TestCardTemplate`, 28 tests |
| Result | PASS — 0 failures, 0 errors |
| Validity | Superseded by later test strengthening and final full-suite run |

### ATR-RUN-004 — Final full module suite

| Field | Value |
|---|---|
| Timestamp | 2026-10-12 03:35 |
| Scope | Entire `wd_global_search` module test suite |
| Invocation | `venv/bin/python odoo-bin -c odoo.conf -d odoo18ce --http-port=0 --gevent-port=0 --test-enable --test-tags /wd_global_search --stop-after-init --log-level=test --logfile=/dev/stdout -u wd_global_search` |
| Executed | 57 |
| PASS / FAIL / ERROR | 57 / 0 / 0 |
| Result | PASS |
| Validity | Superseded: the suite did not discover the newly added descriptor test because it inherited `unittest.TestCase`; corrected to Odoo `TransactionCase` and rerun in ATR-RUN-006 |
| Evidence | Odoo summary: `0 failed, 0 error(s) of 57 tests`; final output captured by the session tool |

The module update logs non-fatal skipped deletions for absent legacy designer menu/action XML IDs.
Odoo continued the module update and test run successfully; no unrelated view cleanup was made.

### ATR-RUN-005 — Static checks on final code

| Check | Result |
|---|---|
| `venv/bin/python -m py_compile` on changed Python modules/tests | PASS |
| `node --check mymodules/wd_global_search/static/src/js/template_designer_page.js` | PASS |
| `git diff --check` | PASS |

### ATR-RUN-006 — Full suite after descriptor test discovery fix

| Field | Value |
|---|---|
| Scope | Entire `wd_global_search` module test suite |
| Executed | 58 |
| PASS / FAIL / ERROR | 58 / 0 / 0 |
| Result | PASS |
| Note | `TestTemplateFieldDescriptor` was discovered after changing it to Odoo `TransactionCase`; superseded by the performance-test-inclusive RUN-008 |

### ATR-RUN-007 — Focused 100-sample performance test

| Field | Value |
|---|---|
| Timestamp | 2026-10-12 07:03 |
| Scope | `TestCardTemplate.test_relation_template_performance_uses_100_samples` |
| Result | PASS — 1 test, 0 failures, 0 errors |
| Measurements | Many2one: parser 0.002 ms, validation 0.010 ms, cold render 2.038 ms, hot render 0.374 ms; Many2many: 0.001 / 0.006 / 0.390 / 0.152 ms; One2many loop: 0.006 / 0.017 / 3.141 / 0.900 ms |
| Sample definition | 100 samples per operation; cold render invalidated the Odoo ORM cache before each sample; hot render reused the warmed cache |

### ATR-RUN-008 — Final full module suite with performance test

| Field | Value |
|---|---|
| Timestamp | 2026-10-12 07:10 |
| Scope | Entire `wd_global_search` module test suite |
| Invocation | `./venv/bin/python odoo-bin -c odoo.conf -d odoo18ce -u wd_global_search --test-enable --test-tags /wd_global_search --stop-after-init --http-port=0 --gevent-port=0 --logfile=/dev/stdout --log-level=test` |
| Executed | 59 |
| PASS / FAIL / ERROR | 59 / 0 / 0 |
| Result | PASS |
| Evidence | Odoo summary: `0 failed, 0 error(s) of 59 tests`; descriptor and performance tests were both discovered |
| Measurements | Many2one: parser 0.002 ms, validation 0.010 ms, cold render 2.895 ms, hot render 0.837 ms; Many2many: 0.001 / 0.005 / 0.397 / 0.152 ms; One2many loop: 0.006 / 0.015 / 3.174 / 0.898 ms |

### ATR-RUN-009 — Preview API end-to-end 100-sample benchmark

| Field | Value |
|---|---|
| Timestamp | 2026-10-12 07:13 |
| Scope | Actual `/wd_global_search/card_templates/preview` endpoint using the applied `sale_order` template and selected readable order S00024 |
| Samples | 100 successful requests (60 + 40 across the configured limiter window); no failed responses in this run |
| Fixture volume | One Sales Order with one order line and its customer/product relations |
| Environment | Odoo 18 CE `odoo18ce`, local macOS development instance at `127.0.0.1:8091`, integrated browser session as Odoo Administrator |
| Cold / warm state | Warm running server; each HTTP request used a fresh ORM request environment. A cold process/database startup was not measured. |
| P95 | 16 ms across all 100 samples; first sample 27.3 ms; remaining 99 warm-state P95 16 ms; min 9.3 ms, max 71.2 ms |
| Budget | PASS — Preview API P95 ≤500 ms per CC-014 §7.3 |

### ATR-RUN-010 — Final static checks

| Check | Result |
|---|---|
| `py_compile` on changed Python modules and tests | PASS |
| `node --check mymodules/wd_global_search/static/src/js/template_designer_page.js` | PASS |
| `git diff --check` | PASS |

## 6. Regression Verification

| Regression boundary | Evidence | Result |
|---|---|---|
| CC-014 template behavior / formatter / published configuration | Template and configuration tests in the 59-test module run | PASS |
| CC-013 Result Card navigation | `test_navigation.py` in the full module run | PASS |
| CC-012 Resource selector / counts | Existing module regression tests in the full module run | PASS |
| CC-003 access boundary | Current-user relation Record Rule tests and permission-boundary suite | PASS |
| CC-007 failure semantics | Existing module error/service tests in the full module run | PASS |
| CC-008 observability | Existing observability tests in the full module run | PASS |
| CC-009 language/timezone | Existing i18n/timezone tests in the full module run | PASS |
| CC-010 published version/checksum | Configuration lifecycle tests in the full module run | PASS |
| CC-002 response contract | Existing service/request boundary tests in the full module run | PASS |

## 7. Issues

| ID | Run | Issue | Status | Follow-up |
|---|---|---|---|---|
| ATR-ISSUE-001 | RUN-001 | Initial implementation errors and one Record Rule fixture failure | Resolved | IHR-004; final RUN-004 PASS |
| ATR-ISSUE-002 | RUN-002 | Monetary field currency metadata can be model-defaulted by Odoo | Resolved | IHR-004; final RUN-004 PASS |
| ATR-ISSUE-003 | RUN-004 | Missing legacy designer XML IDs are logged as skipped deletions during upgrade | Non-blocking observation | No runtime/test failure; not changed in this CC |
| ATR-ISSUE-004 | exploratory Preview API samples | An unpaced attempt reached the configured 60-request/60-second user limit | Resolved; expected limiter behavior | The measured 100-request run was repeated in two successful batches after the rate-limit window; no application change was needed |

## 8. Special Verification

- **Security:** ORM tests verified Many2many membership and One2many loop results obey current-user
  Record Rules. This does not replace human role/UI verification.
- **Migration:** The module update path was exercised as part of Odoo's `-u wd_global_search`
  module test command; no direct SQL was used.
- **Performance:** RUN-008 and RUN-009 measured parser, validation, relation rendering and the actual Preview API route; all recorded P95 values are within the inherited budgets.
- **Browser/API:** RUN-009 used an authenticated browser session to execute the real Preview API route. Manual acceptance is separately recorded in HVR.

## 9. Evidence Inventory

| Evidence | Type | Reference |
|---|---|---|
| E-001 | Odoo test run | ATR-RUN-004 command and Odoo summary in §5 |
| E-002 | Python syntax | ATR-RUN-005 |
| E-003 | JavaScript syntax | ATR-RUN-005 |
| E-004 | Patch formatting | ATR-RUN-005 |
| E-005 | 100-sample parser / validation / render benchmark | ATR-RUN-008 |
| E-006 | 100-sample Preview API benchmark | ATR-RUN-009 |

## 10. Handoff to HVR / FR

```text
Required automated test IDs: 38
Mapped PASS: 38
Final module run: 59 tests; 0 failures; 0 errors
Human scenarios: User-confirmed pass in HVR-RUN-001; detailed observations not supplied
Performance: Parser, validation, rendering and Preview API P95 measured below their CC-014 §7.3 budgets
Evidence baseline: 09f2629 + uncommitted CC-014-1 working-tree changes
```

ATR reports automated evidence only; it does not declare CC-014-1 complete or authorize merge or
release.
