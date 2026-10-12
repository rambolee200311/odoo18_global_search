# ATR-GS-RESULT-CARD-TEMPLATE-DESIGNER

## 1. Execution Metadata

| Field | Value |
|---|---|
| Intent ID | `GS-SEARCH-RESULT-CARD-TEMPLATE-DESIGNER` |
| IHR | `IHR-GS-RESULT-CARD-TEMPLATE-DESIGNER.md` |
| Contract | CC-014 v0.1 FROZEN |
| Module | `wd_global_search` |
| Environment | Odoo 18 CE, local `odoo18ce`, macOS |
| Test framework | Odoo `--test-enable`; Python compile; Node.js syntax; integrated browser |
| Code baseline | `3024403` + uncommitted CC-014 implementation |
| Executed by | Copilot assistant |

## 2. Test Contract Baseline

The authoritative test requirements are CC14-TEST-001~031 in
`docs/context/intent/CC-014_result_card_template_designer.md` §11. This ATR records evidence and
explicit gaps; it does not replace or reduce that contract.

## 3. Current Automated Test Status

| Metric | Result |
|---|---:|
| Latest Odoo module run | 37 tests; 0 failures; 0 errors |
| Python syntax compilation | PASS |
| JavaScript syntax (`node --check`) | PASS |
| `git diff --check` | PASS |
| CC14-TEST coverage | Partial; see §4 |
| Browser performance budgets | NOT RUN |
| Cross-browser compatibility | NOT RUN; integrated browser version not captured |
| Overall ATR | PARTIAL; not sufficient for CC-014 closure |

The Odoo environment also reports unrelated optional addon packages unavailable during startup;
`wd_global_search` loaded and its 36-test run completed with zero failures/errors.

## 4. Coverage Matrix

| CC test | Evidence | Result |
|---|---|---|
| 001 Published template/staging/Apply | `test_explicit_card_template_is_staged_until_applied`; separate Search Executor rendering test | PARTIAL — no single A→B runtime assertion |
| 002 constants/escapes/newline/tab | parser and constant-only ORM tests; browser text-node check | PASS |
| 003 field substitution/repetition | Search Executor renders `{name}` | PARTIAL — repeated-variable automated case not added |
| 004 type formatter matrix | No complete locale/tz/type matrix | NOT RUN |
| 005 partial field permission | unauthorized placeholder/blank renderer tests; explicit `AccessError` branch regression; existing permission boundary suite | PARTIAL — no real reduced-role Search run |
| 006 HTML/XSS | Browser preview rendered `<img onerror>` as text with zero `img` nodes | PARTIAL — full payload suite and production Search DOM case not run |
| 007 injection/parser safety | rejects code/property/method/invalid syntax; accepts escaped braces | PASS |
| 008 drag and keyboard insertion | Arrow/Enter insertion verified in browser | PARTIAL — mouse drag positions not tested |
| 009 real-time preview | successive editor changes rendered after debounce | PASS |
| 010 Save then Apply | ORM snapshot/checksum staging test | PARTIAL — no browser Save/Apply on an isolated configuration |
| 011 Card refresh after template change | Search Executor output and Snapshot Apply tested separately | PARTIAL |
| 012 CC-013 navigation regression | full module suite, including navigation fixtures with templates | PASS |
| 013 CC-012 selector/count regression | existing full module suite | PASS |
| 014 authorization changes | current-user Many2one check and permission service tests | PARTIAL — no revoke-between-search-and-render scenario |
| 015 CC-007 failure semantics | renderer/formatter fault injection not run | NOT RUN |
| 016 designer layout | no horizontal overflow at 390, 768 and 1280 CSS pixels after a field-list wrapping fix | PASS for tested widths |
| 017 preview sources | latest record, manual record selection, synthetic example exercised in browser | PASS |
| 018 stale Preview ordering | aborted requests observed; final latest response displayed | PARTIAL — no controlled out-of-order response harness |
| 019 permission warning | persistent warning displayed in designer | PARTIAL — restricted-group metadata not exercised |
| 020 Preview/Search formatter equivalence | shared renderer path implemented; locale/tz comparison not run | NOT RUN |
| 021 empty/false values | empty Many2one rendered `—`; Boolean False matrix not run | PARTIAL |
| 022 no-variable-field access | unit-level placeholders only | PARTIAL — actual API role/field-group scenario not run |
| 023 Preview HTML safety | injected image text had zero image nodes; no script execution observed | PASS for tested browser payload |
| 024 cross-model missing field | no composite Publish rejection fixture | NOT RUN |
| 025 template bounds/unknown format | 8 KiB and 50-variable bounds plus unknown formatter/parser tests | PASS |
| 026 manager ACL/forged model | controller enforces group and rejects extra args by implementation; negative HTTP test not run | NOT RUN |
| 027 Record Rule | actual ORM reads used for latest/manual record sources; hidden-rule case not constructed | PARTIAL |
| 028 legacy migration | deterministic conversion and stop cases implemented; end-to-end migration fixture not run | PARTIAL |
| 029 keyboard Save/Apply/Escape | field insertion verified; Save/Apply keyboard and Escape behavior not verified | PARTIAL |
| 030 performance P95 | 100-sample parser/render/validation/API measurement not run | NOT RUN |
| 031 session/CSRF/rate boundary | authenticated CSRF-protected Preview succeeded; rejection/61st request not tested | PARTIAL |

## 5. Test Run History

### ATR-RUN-001 — Initial full module run (superseded)

| Field | Value |
|---|---|
| Date | 2026-10-10 |
| Scope | CC-014 + module regression |
| Invocation | `./venv/bin/python odoo-bin -c odoo.conf -d odoo18ce -u wd_global_search --test-enable --test-tags /wd_global_search --stop-after-init --http-port=0 --logfile=/dev/stdout --log-level=test` |
| Result | FAIL — 3 CC-013 navigation fixture tests failed because their Resource fixture did not yet supply the now-required template |
| Resolution | Added the required template to the navigation fixture; no production navigation behavior was changed |

### ATR-RUN-002 — Corrected full module suite

| Field | Value |
|---|---|
| Date | 2026-10-10 |
| Scope | `wd_global_search` module tests |
| Result | PASS — 34 tests, 0 failures, 0 errors |
| Evidence | Odoo test log after fixture correction |

### ATR-RUN-003 — Latest full module suite

| Field | Value |
|---|---|
| Date | 2026-10-10 |
| Scope | Parser, renderer, Search Executor, configuration lifecycle, navigation and existing module tests |
| Invocation | `./venv/bin/python odoo-bin -c odoo.conf -d odoo18ce -u wd_global_search --test-enable --test-tags /wd_global_search --stop-after-init --http-port=0 --logfile=/dev/stdout --log-level=test` |
| Executed | 36 |
| PASS / FAIL / ERROR | 36 / 0 / 0 |
| Result | PASS |
| Evidence | Odoo test summary: `0 failed, 0 error(s) of 36 tests` |

### ATR-RUN-004 — Python, JavaScript and whitespace checks (superseded)

| Check | Result |
|---|---|
| `python -m py_compile` on changed Python files | PASS |
| `node --check` on `template_designer.js` and `preview.js` | PASS |
| `git diff --check` | PASS |
| Baseline caveat | Superseded by ATR-RUN-006 |

### ATR-RUN-005 — Authenticated integrated-browser inspection

| Field | Value |
|---|---|
| Date | 2026-10-10 |
| Environment | Odoo 18 local `odoo18ce`, temporary verification server on port 8092 |
| Browser | Integrated Chromium-like browser; exact version unavailable |
| Results | Designer loaded as configuration manager; latest/manual/synthetic source previews worked; keyboard field insertion worked; injected image remained text with zero DOM image nodes; responsive widths 390/768/1280 had no horizontal document overflow |
| Result | PARTIAL |
| Limitations | Shared active configuration was not saved/applied; role revocation, browser matrix, controlled stale-response ordering, keyboard Save/Apply and performance were not tested |

### ATR-RUN-006 — Permission denial regression and static checks

| Field | Value |
|---|---|
| Date | 2026-10-10 |
| Scope | Field ACL denial handling plus final Python, JavaScript and whitespace checks |
| Invocation | `./venv/bin/python odoo-bin -c odoo.conf -d odoo18ce -u wd_global_search --test-enable --test-tags /wd_global_search --stop-after-init --http-port=0 --logfile=/dev/stdout --log-level=test` |
| Executed | 37 |
| PASS / FAIL / ERROR | 37 / 0 / 0 |
| Additional checks | Python compilation; `node --check` for `template_designer.js` and `preview.js`; `git diff --check` |
| Result | PASS |
| Evidence | Odoo test summary: `0 failed, 0 error(s) of 37 tests`; `test_card_value_reader_handles_field_access_denial` exercises the `AccessError` path |

### ATR-RUN-007 — Resource-form designer integration

| Field | Value |
|---|---|
| Date | 2026-10-12 |
| Environment | Odoo 18 local `odoo18ce`, upgraded module, authenticated configuration-manager session |
| Scope | Business Resource form integration, per-Resource field descriptor, live preview, Save and Apply |
| Results | Designer rendered inside the selected Warehouse Resource form; field list and latest-record preview loaded; changing the template updated preview from `name:NL Company` to `Preview: NL Company` and back; Save → Apply completed from the form with a success status |
| Database verification | Published version 5 has `pending_changes=false`; all seven Resource snapshot entries have zero legacy Card fields |
| Result | PASS for the integrated UI path |
| Limitations | No restricted-user session, other browser engine, or responsive-width matrix was run for the embedded form |

### ATR-RUN-008 — Resource summary and same-tab editor return

| Field | Value |
|---|---|
| Date | 2026-10-12 |
| Environment | Odoo 18 local `odoo18ce`, upgraded module, authenticated configuration-manager browser session |
| Scope | Resource result-only summary, resource-specific editor route, preview, and return navigation |
| Results | Warehouse Resource displayed only `name:NL Company` and an **Edit Template** button. The editor opened in the same tab as a full-viewport page for Resource 138, loaded its field list and preview, and rendered a temporary unsaved `Preview: {name}` change as `Preview: NL Company`; restoring the editor text returned the preview to `name:NL Company`. No Save or Apply was performed during this check. |
| Return navigation | Both browser history Back and the editor's **Back to Resource** control closed the editor while preserving the Warehouse Resource form dialog and its existing preview. |
| Result | PASS for the verified UI flow |
| Limitations | No restricted-user/browser-engine matrix or Save/Apply action was run in this navigation-only verification; controller APIs continue to enforce their existing manager, field, record, and configuration checks |

### ATR-RUN-009 — Single-step editor return regression

| Field | Value |
|---|---|
| Date | 2026-10-12 |
| Environment | Odoo 18 local `odoo18ce`, authenticated integrated browser |
| Scope | Regression for the editor's **Back to Resource** control and browser Back |
| Root cause | The editor overlay inserted two identical browser-history entries, so the first Back only moved between editor entries and appeared unresponsive. |
| Fix | Insert one history entry for the editor; retain the Odoo router state needed to return to the open Resource dialog. |
| Results | Opened Warehouse Resource 138, verified the result-only summary and editor preview, then used **Back to Resource** and browser Back separately. Each closed the editor in one action, preserved both Odoo dialogs and the Resource preview, and left the current card configuration unchanged. |
| Result | PASS |

## 6. Issues and Handoff

- Do not interpret module PASS as all 31 CC14 tests passing.
- Resource-form UI is now a read-only result summary; editing uses the Resource-specific same-tab page and preserves the nested Resource form on return.
- ATR-RUN-009 resolves the duplicate-history-entry issue reported during manual verification.
- Final static checks cover the summary widget, editor page script, controller, and workspace whitespace.
- Complete the open cases from IHR OI-001~OI-005 before Coding Contract closure/FR.
