# wd_global_search_llm Technical Verification

| Item | Value |
|---|---|
| Status | CLOSED — source-level verification complete |
| Date | 2026-10-15 |
| Scope | Business Date capability descriptor and `odoo-llm` extension / execution hooks |
| TDD disposition | Approved in `TDD_wd_global_search_llm.md` v1.0.0 by explicit user approval in this conversation |

## TV-LLM-01 — Business Date capability in authorized resource descriptors

**Question**  
Can the bridge tell the model whether each currently authorized search resource supports a date condition without copying private Business Date configuration or changing search execution semantics?

**Method**  
Reviewed the current `wd_global_search` source for published resource snapshot construction, resource authorization, public descriptor generation, and date-condition execution.

**Result**  
**VERIFIED** — `business_dates` is present in the published resource snapshot. `SearchService.resource_descriptors(env, domain_key)` first filters resources through `_authorized_resources(...)`, then builds each public descriptor. Search execution independently checks the selected resources' Business Date mappings. Therefore the public descriptor can safely add only `date_supported = bool(resource.get("business_dates"))`; no model name, field name, timezone behavior, or empty-date policy needs to be exposed. This is a descriptor-only capability signal; `SearchService.search` remains the validation and execution authority.

**Evidence**

- `mymodules/wd_global_search/models/business_resource.py:348-355` serializes Business Date configuration into the published resource snapshot.
- `mymodules/wd_global_search/services/facade.py:125-145` authorizes resources before returning descriptors.
- `mymodules/wd_global_search/services/facade.py:349-357` constructs public descriptors and is the narrow place for the boolean capability.
- `mymodules/wd_global_search/services/facade.py:211-212` checks selected resources' `business_dates` when handling date filtering.

**TDD Impact**  
Closes `TD-009`: add a server-computed `date_supported: boolean` to each authorized resource descriptor. The bridge exposes date conditions only for resources where this value is true. Implementation and regression verification remain in `TEST-LLM-DATE-DESC-012`; no runtime code was changed or tested in this TV.

## TV-LLM-02 — Tool exposure and execution extension points

**Question**  
Does the current `odoo-llm` source provide server-side extension points to filter provider-visible tools and to reject disallowed tool execution while retaining the calling Odoo environment?

**Method**  
Reviewed the local `odoo-llm` 18.0 source at commit `609ec6dda3645165f6a4a843d7af5d286081a29d`, focusing on thread request construction and tool dispatch.

**Result**  
**VERIFIED** — `llm.thread._prepare_chat_kwargs(message_history, use_streaming)` is an overridable hook that supplies `self.tool_ids` to the provider. `mail.message._execute_tool_with_context(tool_name, arguments_str, thread_model=None)` resolves the selected thread tool and invokes it with the message context. The bridge can override these server-side hooks for the provider allowlist and execution-time assistant/tool check. This confirms source-level integration points; target-instance integration tests remain future implementation verification.

**Evidence**

- `mymodules/odoo-llm/llm_assistant/models/llm_thread.py:331-338` builds provider kwargs, including tools.
- `mymodules/odoo-llm/llm_tool/models/mail_message.py:226-260` resolves and executes the tool from the owning thread.
- The tool executes through the current Odoo environment and the reviewed path contains no `sudo()` call.

**TDD Impact**  
The provider-list and execution-entry hooks and their source signatures are recorded in TDD §3.3 and §12.2. `TEST-LLM-TOOLS-003` remains NOT RUN until the addon is implemented and tested against the target Odoo installation.

## Verification boundary

This TV establishes source-level feasibility only. It does not claim a live Odoo integration test, module installation test, provider call, or runtime permission test has passed. Those checks belong to the approved Implementation Plan and corresponding Coding Contracts.
