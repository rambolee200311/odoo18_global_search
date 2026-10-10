# ATR-GS-RESULT-CARD-NATIVE-FORM

## 1. Execution Metadata

| Field | Value |
|---|---|
| Intent ID | `GS-SEARCH-RESULT-CARD-NATIVE-FORM` |
| IHR | `IHR-GS-RESULT-CARD-NATIVE-FORM.md` |
| Contract | CC-013 v0.1 FROZEN |
| Module | `wd_global_search` |
| Environment | Odoo 18 CE, `odoo18ce`, macOS |
| Test Framework | Odoo `--test-enable`; Odoo shell/unittest; Node.js |
| Branch | `main` |
| Code baseline | CC-013 implementation working tree with post-verification navigation fixes |
| Executed by | Copilot assistant |

## 2. Test Contract Baseline

| Source | IDs | Test scope |
|---|---|---|
| CC-013 | CC13-TEST-001~008, 018 | Publish/Card/Action configuration and Composite guard |
| CC-013 | CC13-TEST-005/012/020/022 | Permission, Action group and internal-data behavior |
| CC-013 | CC13-TEST-009~011, 019 | Browser Action/keyboard behavior; requires HVR/browser setup |
| CC-013 | CC13-TEST-014~017 | Workspace, CC-003, CC-012 and CC-007 regression |
| CC-013 | CC13-TEST-002/007/009 | Playwright smoke and post-fix resolver checks against Published v5 |

## 3. Current Automated Test Status

| Metric | Result |
|---|---:|
| Odoo module tests | 20 PASS (latest module-upgrade test command exited 0) |
| Explicit Odoo-context tests | 29 PASS |
| JavaScript syntax | PASS |
| Python compileall | PASS |
| `git diff --check` | PASS |
| Browser/Card/Action HVR | Human verifier confirmed HVR-SCN-001~007 PASS in HVR-RUN-001 |
| Chromium rendering: 100 Cards | 10 samples; P95 32 ms from Search response end through two animation frames |
| Post-fix navigation resolver | 7/7 configured resources resolve; invalid record is safely rejected |

## 4. Coverage Matrix

| CC test area | Automated verification | Result | Evidence |
|---|---|---|---|
| Card and Action Publish validation | configuration TransactionCase tests | PASS | Action/model mismatch, duplicate sequence, unsupported field format, missing Card config and invalid Action target rejected |
| Published Snapshot contents | configuration TransactionCase test | PASS | Action identity/metadata and Card Sequence/Visible emitted |
| Card field Sequence/authorization | permission-boundary component test | PASS | Visible authorized fields retain order; hidden/unreadable fields omitted; translated Label used |
| Resolver uses configured Action/current record | navigation TransactionCase and ATR-RUN-008 | PASS | Seven published Resources resolve their configured Action and record identity |
| Action Context/Domain standalone navigation safety | configuration TransactionCase test | PASS | `active_id` in Action Context or Domain is rejected before publish/apply |
| Unknown Resource/client model input | navigation test | PASS | Safe failure for non-key payload/unknown Resource |
| Action drift after Publish | navigation test | PASS | Changed Action metadata fails closed |
| Action group restrictions | helper test | PASS | Ineligible group set rejected |
| CC-002/CC-012 selected scope and counts | core service tests | PASS | Existing 29-test combined test run includes count/facet/pagination tests |
| CC13-TEST-023 responsive Card disclosure | Chromium Playwright, ATR-RUN-006 | PASS (tested widths) | Disclosure defaults closed below 768px, open at/above 768px; no horizontal overflow at 375, 767, 768, 900, 1023, 1024, or 1440px; card order retained |
| CC13-TEST-019 keyboard selection subset | Chromium Playwright, ATR-RUN-006 | PASS (Space/Escape) | Space selects; Escape clears selection |
| CC-005 pagination/page-size regression | Chromium Playwright, ATR-RUN-006 | PASS | Page 2 showed 11–20 of 41; changing page size to 20 reset to page 1 and showed 1–20 |
| No-Preview interaction regression | Chromium Playwright, ATR-RUN-006 | PASS | Card selection/page navigation issued no `/api/preview` request |
| CC13-TEST-009/010 configured Action and new Tab | ATR-RUN-008 plus integrated-browser attempt | PARTIAL | All seven server-side resolvers succeed; visible Odoo Form startup after double-click was not verified in the hidden integrated-browser session |
| CC13-TEST-002 legacy Card rendering | Chromium Playwright | PARTIAL | `GS-CUSTOMER-001` displays existing legacy Snapshot values as text; v5 has no sequence/visible/action metadata |
| CC13-TEST-007/009 configured Action | ATR-RUN-008 | PASS (server-side) | Published v5 has valid action bindings and all seven resolver checks succeed |
| Configuration admin UI | Chromium Playwright | BLOCKED | `/odoo/action-495` rendered empty Odoo Web Client; `odoo.isReady=false` |
| CC13-TEST-010/019 new Tab and keyboard behavior | Integrated browser | NOT RUN | The integrated page remained hidden with an empty body; this run is not evidence of a rendered Form |
| Current-user distinct group/multi-company Action integration | Not run in authenticated multi-user browser/session | NOT RUN | Requires separate-user HVR/integration evidence |

## 5. Test Run History

### ATR-RUN-001 — Odoo-context unit/regression tests

| Field | Value |
|---|---|
| Date | 2026-10-09 |
| Scope | Configuration, Card permission serialization, Action navigation, Search core |
| Invocation | `odoo-bin shell -c odoo.conf -d odoo18ce --no-http` with `unittest.TextTestRunner` |
| Executed | 29 |
| PASS / FAIL | 29 / 0 |
| Result | PASS |
| Evidence | Terminal output: `Ran 29 tests ... OK` |

### ATR-RUN-002 — Odoo module update tests

| Field | Value |
|---|---|
| Date | 2026-10-09 |
| Scope | `wd_global_search` module update/test suite |
| Invocation | `./venv/bin/python odoo-bin -c odoo.conf --http-port=8092 -d odoo18ce -u wd_global_search --test-enable --stop-after-init --log-level=test` |
| Odoo module test count | 19 |
| Result | PASS |
| Evidence | Odoo test log: `wd_global_search: 19 tests 0.57s 600 queries`; process exit 0 |

### ATR-RUN-003 — Static checks

| Scope | Python compile, JavaScript syntax, whitespace |
| Invocation | `python -m compileall -q mymodules/wd_global_search`; `node --check .../preview.js`; `git diff --check` |
| Result | PASS |

### ATR-RUN-004 — Playwright Card/Action smoke

| Field | Value |
|---|---|
| Date | 2026-10-09 |
| Environment | Authenticated Chromium Workspace, `odoo18ce` |
| Scope | Search `GS-CUSTOMER-001`, inspect first Card, request the server Form Action resolver |
| Result | PARTIAL |
| Evidence | Existing legacy Card renders `Email`, `Name`, `Phone` values; resolver returns generic safe `PERMISSION_OR_DELETED` because Published v5 has no Action binding |

### ATR-RUN-005 — Configuration administration page

| Field | Value |
|---|---|
| Date | 2026-10-09 |
| Scope | Open configuration Action `495` at `/odoo/action-495` using Playwright |
| Result | BLOCKED |
| Evidence | Page title `Odoo`, empty body, `.o_web_client` has zero children and `odoo.isReady=false` |

### ATR-RUN-006 — Responsive Card, keyboard, and Workspace regression

| Field | Value |
|---|---|
| Date | 2026-10-10 |
| Environment | Authenticated Odoo 18 local Workspace at `http://127.0.0.1:8091`; Chromium Integrated Browser |
| Code Baseline | `68a7289` + uncommitted CC-013 implementation working tree |
| Scope | Search `GS-CUSTOMER-001`; Card disclosure across viewport changes; keyboard selection; pagination/page-size; no-Preview and write-RPC observation |
| Result | PASS for the tested Chromium scope |
| Evidence | Workspace served script `preview.js?v=cc013-v02`; 375/767px details closed; 768/900/1023/1024/1440px details open; compact 12px card padding at 768–1023px and 14px at 1024px+; no horizontal document overflow; field order retained; manual disclosure survived a same-range resize; Space selected and Escape cleared; page-size 20 reset page 2 to page 1; no console errors, business write requests, or `/api/preview` requests observed. Ten 100-card runs measured response-end-to-two-animation-frame rendering P95 of 32 ms (target ≤100 ms). |

### ATR-RUN-007 — Configured double-click navigation attempt

| Field | Value |
|---|---|
| Date | 2026-10-10 |
| Environment | Authenticated Odoo 18 local Workspace at `http://127.0.0.1:8091`; Chromium Integrated Browser |
| Code Baseline | `68a7289` + uncommitted CC-013 implementation working tree |
| Scope | Double-click the first Contact Result Card and observe the configured Action resolver and new Tab |
| Result | BLOCKED — no successful Native Form navigation |
| Evidence | The double-click invoked `/wd_global_search/api/form_url`; the resolver returned HTTP 403 and the Workspace displayed the generic safe message `Record unavailable or permission changed`. No Native Form remained open. The current shared Published configuration has no available CC-013 Action binding for this Resource; Published configuration was not modified. |

### ATR-RUN-008 — Post-fix all-resource navigation verification

| Field | Value |
|---|---|
| Date | 2026-10-10 |
| Environment | Odoo 18 CE local database `odoo18ce`; integrated Chromium browser |
| Scope | Add a dedicated standalone `stock.location` Form Action, reject active-record variables in Action Context/Domain, apply the published Storage Location mapping, and resolve one accessible record for each of the seven published Resources |
| Result | PASS for module upgrade/tests and server-side resolver checks; visual Odoo Form startup remains NOT VERIFIED |
| Evidence | `global_search_baseline` v5 is applied with no pending changes; action IDs are Warehouse 247, Storage Location 517, Product 497, Contact 299, Stock Picking 265, Sales Order 499, and Purchase Order 440. `resolve_form_navigation()` returned `SUCCESS` for all seven. An invalid Warehouse ID returned the generic `PERMISSION_OR_DELETED` result. The integrated browser page remained hidden with an empty body after direct navigation, so no Form-rendering PASS is claimed. |

## 6. Regression Verification

| Preservation | Result | Evidence |
|---|---|---|
| CC-002 search/pagination/count protocol | PASS | Combined service tests |
| CC-003 field/model permission helpers | PASS | Card serialization and PermissionBoundary tests |
| CC-005 Results-only Workspace state | PASS (tested interaction scope) | ATR-RUN-006 observed no Preview request during Card selection/pagination; this is not a full browser regression matrix |
| CC-007 failure protocol | PARTIAL | Existing status protocol unchanged; no live Resource fault injection |
| CC-009 language/format | PARTIAL | Card uses server lang labels and Odoo date/number format helpers; browser locale HVR not run |
| CC-012 key/selector/facet | PASS (service/unit scope) | Combined service tests; no live new Published version browser check |

## 7. Issues / Not Run

- ATR-RUN-005 records an earlier blank admin-page attempt. The later authenticated browser run loaded the Workspace and the running Odoo service was restarted to load the updated controller cache key.
- The earlier ATR-RUN-007 failure was caused by standard Actions whose Context or Domain depended on `active_id`. The local Published v5 mapping has since been corrected through the Apply Changes workflow; this local database change is not automatically applied to other databases.
- Visible double-click-to-Form startup after the action fixes, multi-user Action-group/revoked-permission integration, Firefox/Safari/Edge, server-side Snapshot serialization/ACL timing isolation, and action-view locale checks remain NOT RUN.

## 8. Handoff

ATR-RUN-006 supplies Chromium evidence for responsive density, keyboard selection, pagination/page-size, and no-Preview interaction. ATR-RUN-008 verifies all seven published navigation resolvers and records the remaining browser-visible Form startup gap. HVR-RUN-001 is historical and is superseded for the current code/configuration by the later Action `active_id` failures and fixes. The user explicitly approved closing CC-013; the unverified browser matrix, visible Form startup, and partial CC-002~CC-012 regression evidence are recorded as accepted closure deferrals in the FR.
