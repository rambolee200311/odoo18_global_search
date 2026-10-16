# Automated Test Record — CC-OPENAI-001

## 1. Execution Metadata

| Field | Value |
|---|---|
| Intent ID | CC-OPENAI-001 |
| IHR | IHR-CC-OPENAI-001.md |
| CC version | v1.0.0 Frozen |
| Module | llm_openai |
| Environment | Local development database odoo18ce; HTTP port 8091; no isolated database |
| Test framework | Odoo --test-enable, TransactionCase |
| Odoo / Python | Odoo 18.0 / Python 3.11.9 |
| PostgreSQL server version | Not collected; project verification does not query server metadata directly |
| Source baseline | 609ec6dda3645165f6a4a843d7af5d286081a29d plus implementation working-tree changes |
| Branches | Parent repository main; nested source checkout 18.0 |
| Executed by | Codex |
| Latest execution | 2026-10-16 06:41 UTC |

## 2. Test Contract Baseline

Required test set: CC-OPENAI-001 §11, CC-TEST-001 through CC-TEST-013. This record references those IDs and does not redefine their expected behavior.

## 3. Current Automated Test Status

| Metric | Value |
|---|---:|
| Required automated tests | 10 |
| PASS | 10 |
| FAIL | 0 |
| SKIPPED | 0 |
| BLOCKED | 0 |
| NOT RUN | 0 |
| Latest valid run | ATR-RUN-003 |
| Current code baseline | Base commit plus implementation working tree represented by ATR-RUN-003 |
| Evidence baseline match | Yes |

## 4. Core Test Contract Coverage

| CC / TEST source | Automated test | Run | Result | Evidence |
|---|---|---|---|---|
| CC-TEST-001 | test_empty_values_leave_request_unchanged | ATR-RUN-003 | PASS | §5; run log |
| CC-TEST-002 | test_empty_objects_are_valid_and_do_not_add_effort | ATR-RUN-003 | PASS | §5; run log |
| CC-TEST-003 | test_non_openai_provider_ignores_namespace_without_parsing | ATR-RUN-003 | PASS | §5; run log |
| CC-TEST-004 | test_unknown_namespaces_and_keys_are_ignored | ATR-RUN-003 | PASS | §5; run log |
| CC-TEST-005 | test_invalid_json_and_non_object_top_level_are_rejected; runtime portion of test_invalid_runtime_configuration_stops_before_http_call | ATR-RUN-003 | PASS | §5; run log |
| CC-TEST-006 | test_invalid_namespace_and_effort_values_are_rejected; runtime portion of test_invalid_runtime_configuration_stops_before_http_call | ATR-RUN-003 | PASS | §5; run log |
| CC-TEST-007 | test_reasoning_effort_is_added_to_request | ATR-RUN-003 | PASS | §5; run log |
| CC-TEST-008 | test_model_owned_request_fields_are_not_overridden | ATR-RUN-003 | PASS | §5; run log |
| CC-TEST-009 | test_tool_and_stream_matrix | ATR-RUN-003 | PASS | §5; run log |
| CC-TEST-010 | test_invalid_runtime_configuration_stops_before_http_call | ATR-RUN-003 | PASS | §5; run log |
| CC-TEST-011 | Real configured Provider response | — | NOT RUN | §8.1 |
| CC-TEST-012 | Other model / compatible endpoint regression | — | NOT RUN | §8.2 |
| CC-TEST-013 | Actual Odoo tool execution | — | BLOCKED | §8.3 |

## 5. Test Run History

### ATR-RUN-001 — Initial logging attempt

| Field | Value |
|---|---|
| Timestamp | 2026-10-16 06:38 UTC |
| Code baseline | Base commit plus initial implementation working tree |
| Environment | odoo18ce |
| Invocation | ./venv/bin/python odoo-bin -c odoo.conf -d odoo18ce --test-enable --test-tags /llm_openai --stop-after-init --http-port=0 --gevent-port=0 -u llm_openai |
| Scope | Target module update and tests |
| Result | PARTIAL; process exited 0, but default log level did not retain an explicit test count. This run is not used as PASS evidence. |
| Evidence | Initial temporary log was replaced by the subsequent verbose run; no PASS is claimed from this attempt. |
| Follow-up | Re-ran with explicit Odoo test and module-loading log handlers in ATR-RUN-002. |

### ATR-RUN-002 — Verbose test run

| Field | Value |
|---|---|
| Timestamp | 2026-10-16 06:39 UTC |
| Code baseline | Base commit plus initial implementation working tree |
| Environment | odoo18ce |
| Invocation | Same as ATR-RUN-001, with --log-handler=odoo.tests:INFO --log-handler=odoo.modules.loading:INFO |
| Scope | llm_openai module tests |
| Executed | 10 test cases; 0 failures; 0 errors |
| Result | PASS for that code baseline |
| Evidence | Odoo emitted “0 failed, 0 error(s) of 10 tests”; temporary log was replaced by the next run |
| Follow-up | Test assertions were expanded and runtime error messaging tightened; re-run as ATR-RUN-003. |

### ATR-RUN-003 — Latest code baseline

| Field | Value |
|---|---|
| Timestamp | 2026-10-16 06:41 UTC |
| Code baseline | Base commit plus final implementation working tree |
| Environment | odoo18ce; Odoo 18.0; Python 3.11.9 |
| Invocation | ./venv/bin/python odoo-bin -c odoo.conf -d odoo18ce --test-enable --test-tags /llm_openai --stop-after-init --http-port=0 --gevent-port=0 -u llm_openai --log-handler=odoo.tests:INFO --log-handler=odoo.modules.loading:INFO |
| Scope | llm_openai module tests and module data/view load |
| Expected / executed | 10 / 10 test cases |
| PASS / FAIL / SKIPPED / BLOCKED | 10 / 0 / 0 / 0 |
| Result | PASS for CC-TEST-001–010 |
| Evidence | evidence/ATR-CC-OPENAI-001-RUN-003.log |
| Follow-up | Real Provider and end-to-end statuses remain as §4 and §8 state them. |

The run log also reports unrelated unavailable custom addons: wd_advanced_m2o_record_panel, wd_evidence_album, and wd_qooling_app. No llm_openai test failed. Normal server startup also logs that existing wd_global_search code imports its test framework; this is outside this CC and was not changed.

## 6. Regression Verification

| CC-PRESERVE | Automated verification | Run | Result | Code baseline |
|---|---|---|---|---|
| CC-PRESERVE-001 | Empty / absent parameter request assertions | ATR-RUN-003 | PASS | Latest working tree |
| CC-PRESERVE-002 | Provider-owned model/messages/stream/tools/tool_choice assertions | ATR-RUN-003 | PASS | Latest working tree |
| CC-PRESERVE-003 | Non-OpenAI namespace parser isolation | ATR-RUN-003 | PASS | Latest working tree |
| CC-PRESERVE-004 | Unknown parameter filtering | ATR-RUN-003 | PASS | Latest working tree |
| CC-PRESERVE-005 | Existing Chat Completions endpoint observed in diagnostic request capture | ATR-RUN-003 | PARTIAL; endpoint observed, Provider response timed out | Latest working tree |
| CC-PRESERVE-006 | Output/documentation review for credentials and raw request content | ATR-RUN-003 | PASS | Latest working tree |

## 7. Issues

| ID | Test | Run | Type | Reason | Status | Follow-up |
|---|---|---|---|---|---|---|
| OI-001 | CC-TEST-011 | — | NOT RUN | Required model setting was not applied to the database; the single diagnostic request used the current unconfigured model and timed out. | Open | User/provider validation window required |
| OI-002 | CC-TEST-012 | — | NOT RUN | No second model or compatible endpoint was selected for this authorized request. | Open | Configure a test endpoint/model |
| OI-003 | CC-TEST-013 | — | BLOCKED | Known MCP schema-generation compatibility issue remains; tool execution was not attempted. | Open | Resolve separately in llm_tool, then authorize E2E |

## 8. Special Verification — Provider / Tool Integration

### 8.1 Authorized outgoing-payload diagnostic

One real request was sent through the configured Odoo OpenAI Provider. The redacted capture showed POST https://api.openai.com/v1/chat/completions, model gpt-5.6-luna, tool odoo_record_retriever, payload keys messages, model, stream, tool_choice, tools, and no reasoning_effort. The HTTP client timed out and returned no Provider response. No key, authorization value, message body, or tool arguments were recorded. This diagnostic closes the outgoing-payload capture gate but is not CC-TEST-011 and is not evidence of a successful real API response.

### 8.2 CC-TEST-011 / CC-TEST-012

CC-TEST-011 is NOT RUN to its acceptance criteria: the model database parameters was not changed to the required “none” setting, and no HTTP 200 tool-call response was received. No further external call was made after the single authorized attempt. CC-TEST-012 is NOT RUN because no alternate endpoint/model was configured for this turn.

### 8.3 CC-TEST-013

CC-TEST-013 is BLOCKED by the separately known mcp schema-generation compatibility issue. This task did not execute odoo_record_retriever or read any sales-order data.

### 8.4 Mock / Real transparency

CC-TEST-001–010 use Odoo ORM tests and a mocked OpenAI SDK client for request-construction assertions. The single real transport request is diagnostic only and timed out. No successful real external integration is claimed.

## 9. Evidence Inventory

| Evidence ID | Type | Location | Run |
|---|---|---|---|
| E-001 | Odoo test-run log | evidence/ATR-CC-OPENAI-001-RUN-003.log | ATR-RUN-003 |
| E-002 | Redacted runtime output captured in IHR-001 / §8.1 | This record; no raw payload persisted | Diagnostic only |

## 10. Handoff to HVR / FR

Required automated tests: 10. PASS: 10; FAIL: 0; SKIPPED: 0; BLOCKED: 0; NOT RUN: 0. Latest valid run: ATR-RUN-003. Evidence baseline match: Yes. Outstanding: CC-TEST-011 NOT RUN, CC-TEST-012 NOT RUN, CC-TEST-013 BLOCKED.

This ATR records execution evidence only; it does not decide CC closure, merge, or release.
