import hashlib
import json
import math
import time
import uuid

from odoo.exceptions import AccessError

from .aggregator import merge
from .conditions import merge as merge_conditions
from .cursor import decode, encode
from .errors import error
from .executor import authorize_search_resource, execute
from .limiter import UserLimiter
from .permission_boundary import AuthorizationError, authorize_searchable_fields
from .provider import ConfigurationError, published_snapshot
from .request_boundary import RequestBoundaryError, validate_search_request
from .observability import hash_value, log_event
from .types import ResourceOutcome, SearchRequest, UserContext


_limiter = UserLimiter()
_cancelled = set()
_request_owners = {}
_SEARCH_TIMEOUT_SECONDS = 5
_CURSOR_SORT_VERSION = "v1"


def _failure_outcome(code, resource="request"):
    return ResourceOutcome(
        resource=resource,
        status="FAILED",
        error=error(
            code,
            scope="resource" if resource != "request" else "request",
            resource=resource,
        ),
    )


def _hash(value):
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def user_context(env):
    user = env.user
    return UserContext(
        uid=env.uid,
        company_id=env.company.id,
        company_ids=tuple(env.companies.ids),
        lang=user.lang or "en_US",
        tz=user.tz or "UTC",
        groups=tuple(user.groups_id.ids),
    )


def _authorized_resources(env, resources, context):
    eligible = []
    for resource in resources:
        try:
            authorize_search_resource(env, resource, context)
        except AuthorizationError as exc:
            if exc.code == "CONFIGURATION_ERROR":
                raise ConfigurationError() from exc
            continue
        eligible.append(resource)
    return sorted(eligible, key=lambda item: item["key"])


def _performance_config(snapshot, resources):
    configured = {}
    resource_keys = {
        resource["key"] for resource in snapshot.get("resources", ())
    }
    for item in snapshot.get("performance", ()):
        if not isinstance(item, dict):
            raise ConfigurationError()
        resource_key = item.get("resource_key")
        if resource_key not in resource_keys or resource_key in configured:
            raise ConfigurationError()
        values = {
            "max_results": item.get("max_results", 200),
            "resource_timeout": item.get("resource_timeout", 3.0),
            "request_timeout": item.get("request_timeout", 5.0),
            "max_relation_depth": item.get("max_relation_depth", 2),
        }
        if (
            not isinstance(values["max_results"], int)
            or isinstance(values["max_results"], bool)
            or not 1 <= values["max_results"] <= 200
            or not isinstance(values["resource_timeout"], (int, float))
            or isinstance(values["resource_timeout"], bool)
            or not math.isfinite(values["resource_timeout"])
            or not 0 < values["resource_timeout"] <= 3.0
            or not isinstance(values["request_timeout"], (int, float))
            or isinstance(values["request_timeout"], bool)
            or not math.isfinite(values["request_timeout"])
            or not 0 < values["request_timeout"] <= 5.0
            or not isinstance(values["max_relation_depth"], int)
            or isinstance(values["max_relation_depth"], bool)
            or not 1 <= values["max_relation_depth"] <= 3
        ):
            raise ConfigurationError()
        configured[resource_key] = values
    return {
        resource["key"]: configured.get(
            resource["key"],
            {
                "max_results": 200,
                "resource_timeout": 3.0,
                "request_timeout": 5.0,
                "max_relation_depth": 2,
            },
        )
        for resource in resources
    }


def _effective_conditions(env, resources, selected_keys, conditions, context):
    configured_fields = {}
    selected_resources = [
        resource for resource in resources if resource["key"] in selected_keys
    ]
    has_business_date = any(
        resource.get("business_dates") for resource in selected_resources
    )
    for resource in selected_resources:
        for model_config in resource.get("models", ()):
            model = env[model_config["model_name"]]
            try:
                readable_fields = authorize_searchable_fields(
                    env, model, model_config.get("fields", ()), context
                )
            except AuthorizationError as exc:
                if exc.code == "CONFIGURATION_ERROR":
                    raise ConfigurationError() from exc
                continue
            for field_config in readable_fields:
                configured_fields.setdefault(field_config["name"], []).append(
                    field_config
                )

    visible = []
    for condition in conditions.values:
        dimension = condition["dimension"]
        if dimension == "name":
            visible.append(condition)
        elif dimension == "date":
            if has_business_date:
                visible.append(condition)
        elif dimension in configured_fields:
            if "." in dimension:
                value = condition.get("value")
                if not isinstance(value, (str, int, float, bool)) or value == "":
                    raise RequestBoundaryError("Invalid searchable field value")
                if isinstance(value, float) and not math.isfinite(value):
                    raise RequestBoundaryError("Invalid searchable field value")
                for field_config in configured_fields[dimension]:
                    if (
                        field_config.get("operator_set") in {"prefix", "contains"}
                        and not isinstance(value, str)
                    ):
                        raise RequestBoundaryError("Invalid searchable field value")
            visible.append(condition)
        elif "." in dimension:
            raise RequestBoundaryError("Condition is not an available searchable field")
    return visible


def _localized_value(translations, fallback, lang):
    if isinstance(translations, dict):
        return translations.get(lang) or translations.get("en_US") or fallback
    return fallback


def _resource_descriptor(resource, lang="en_US"):
    return {
        "key": resource["key"],
        "label": _localized_value(
            resource.get("name_translations"),
            resource.get("label") or resource.get("name") or resource["key"],
            lang,
        ),
    }


def _observe_response(response, request, context, secret):
    status = response.status
    event = {
        "request_id": response.request_id,
        "config_version": response.meta.get("config_version"),
        "status": status,
        "latency_ms": response.meta.get("latency_ms", 0),
        "result_count": response.counts.get("all", 0),
        "user_context_hash": hash_value(
            secret,
            "%s|%s" % (context.uid, ",".join(map(str, context.company_ids))),
        ),
    }
    if request.raw_query:
        event["raw_query_hash"] = hash_value(secret, request.raw_query)
    event["conditions_hash"] = hash_value(
        secret,
        repr((request.parsed_conditions, request.refinement_conditions)),
    )
    if status == "PARTIAL_SUCCESS":
        event["failed_resources"] = response.meta.get("failed_resources", [])
        log_event("warning", "gs.search.partial", event)
    elif status in {"FAILED", "TIMEOUT"}:
        first_error = response.errors[0] if response.errors else {}
        event.update(
            {
                "error_code": first_error.get("code", status),
                "retryable": first_error.get("retryable", status == "TIMEOUT"),
            }
        )
        log_event("error", "gs.search.failed", event)
    else:
        log_event("info", "gs.search.completed", event)
    return response


class SearchService:
    def resource_descriptors(self, env, domain_key):
        context = user_context(env)
        snapshot_info = published_snapshot(env, domain_key)
        resources = _authorized_resources(
            env,
            snapshot_info["snapshot"].get("resources", []),
            context,
        )
        return {
            "config_version": snapshot_info["version_id"],
            "resources": [
                _resource_descriptor(resource, context.lang) for resource in resources
            ],
        }

    def search(self, env, request, domain_key):
        context = user_context(env)
        request_id = str(uuid.uuid4())
        request_started = time.monotonic()
        _request_owners[request_id] = context.uid
        if not _limiter.acquire(context.uid):
            log_event(
                "warning",
                "gs.search.rate_limited",
                {"request_id": request_id, "latency_ms": 0},
            )
            return merge(
                [_failure_outcome("RATE_LIMITED")],
                request_id,
                request.offset,
                request.limit,
                None,
            )
        try:
            validate_search_request(request)
            if request.limit < 1 or request.limit > 200:
                log_event(
                    "warning",
                    "gs.boundary.rejected",
                    {"request_id": request_id, "error_code": "INVALID_REQUEST", "boundary": "limit"},
                )
                return merge(
                    [_failure_outcome("INVALID_REQUEST")],
                    request_id,
                    0,
                    0,
                    None,
                )
            snapshot_info = published_snapshot(env, domain_key)
            snapshot = snapshot_info["snapshot"]
            resources = _authorized_resources(env, snapshot.get("resources", []), context)
            performance = _performance_config(snapshot, resources)
            descriptors = [
                _resource_descriptor(resource, context.lang) for resource in resources
            ]
            selected_keys = set(request.resource_scope)

            def response_for(outcomes, offset=0, limit=request.limit):
                response = merge(
                    outcomes,
                    request_id,
                    offset,
                    limit,
                    snapshot_info["version_id"],
                    count_scope=selected_keys,
                )
                response.meta["resource_descriptors"] = descriptors
                return response

            cursor_secret = env["ir.config_parameter"].sudo().get_param("database.secret")
            if not cursor_secret:
                return response_for(
                    [_failure_outcome("CONFIGURATION_ERROR")], 0, 0
                )
            if (
                len(selected_keys) != len(request.resource_scope)
                or selected_keys - {item["key"] for item in resources}
            ):
                return _observe_response(
                    response_for([_failure_outcome("INVALID_REQUEST")], 0, 0),
                    request,
                    context,
                    cursor_secret,
                )
            conditions = merge_conditions(
                request.parsed_conditions, request.refinement_conditions
            )
            visible_conditions = _effective_conditions(
                env, resources, selected_keys, conditions, context
            )
            effective_limit = min(
                [request.limit]
                + [
                    performance[key]["max_results"]
                    for key in selected_keys
                    if key in performance
                ]
            )
            response_timeout = min(
                [_SEARCH_TIMEOUT_SECONDS]
                + [item["request_timeout"] for item in performance.values()]
            )
            deadline = request_started + response_timeout
            context_hash = _hash(
                {
                    "uid": context.uid,
                    "company_ids": context.company_ids,
                    "lang": context.lang,
                    "tz": context.tz,
                }
            )
            conditions_hash = _hash(
                {
                    "conditions": list(conditions.values),
                    "resources": sorted(selected_keys),
                }
            )
            cursor_offset = request.offset
            if request.cursor:
                try:
                    cursor_data = decode(
                        request.cursor,
                        cursor_secret.encode(),
                        {
                            "config_version": snapshot_info["version_id"],
                            "conditions_hash": conditions_hash,
                            "user_context_hash": context_hash,
                            "sort_version": _CURSOR_SORT_VERSION,
                        },
                    )
                except TimeoutError:
                    return _observe_response(
                        response_for([_failure_outcome("CURSOR_EXPIRED")], 0, 0),
                        request,
                        context,
                        cursor_secret,
                    )
                except ValueError:
                    return _observe_response(
                        response_for([_failure_outcome("CURSOR_INVALID")], 0, 0),
                        request,
                        context,
                        cursor_secret,
                    )
                cursor_offset = int(cursor_data.get("offset", request.offset))
            outcomes = []
            request_page_offset = cursor_offset
            remaining_offset = cursor_offset
            remaining_limit = effective_limit
            for index, resource in enumerate(resources):
                if request_id in _cancelled:
                    outcomes.extend(
                        _failure_outcome("CANCELLED", item["key"])
                        for item in resources[index:]
                    )
                    break
                if time.monotonic() >= deadline:
                    outcomes.extend(
                        _failure_outcome("TIMEOUT", item["key"])
                        for item in resources[index:]
                    )
                    break
                selected = resource["key"] in selected_keys
                resource_deadline = min(
                    deadline,
                    time.monotonic()
                    + performance[resource["key"]]["resource_timeout"],
                )
                outcome = execute(
                    env,
                    resource,
                    conditions,
                    min(
                        remaining_limit,
                        performance[resource["key"]]["max_results"],
                    )
                    if selected
                    else 0,
                    context,
                    offset=remaining_offset if selected else 0,
                    deadline=resource_deadline,
                )
                outcomes.append(outcome)
                if not selected or outcome.status != "SUCCESS":
                    continue
                if remaining_offset >= outcome.count:
                    remaining_offset -= outcome.count
                    continue
                remaining_offset = 0
                remaining_limit = max(0, remaining_limit - len(outcome.results))
            response = response_for(outcomes, 0, effective_limit)
            response.meta["effective_conditions"] = visible_conditions
            response.meta["page_limit"] = effective_limit
            if response.results and len(response.results) == effective_limit:
                response.meta["next_cursor"] = encode(
                    {
                        "offset": request_page_offset + effective_limit,
                        "config_version": snapshot_info["version_id"],
                        "conditions_hash": conditions_hash,
                        "user_context_hash": context_hash,
                        "sort_version": _CURSOR_SORT_VERSION,
                    },
                    cursor_secret.encode(),
                )
            return _observe_response(response, request, context, cursor_secret)
        except RequestBoundaryError:
            log_event(
                "warning",
                "gs.boundary.rejected",
                {"request_id": request_id, "error_code": "INVALID_REQUEST", "boundary": "request"},
            )
            return merge([_failure_outcome("INVALID_REQUEST")], request_id, 0, 0, None)
        except ConfigurationError:
            return merge(
                [_failure_outcome("CONFIGURATION_ERROR")],
                request_id,
                0,
                0,
                None,
            )
        except AccessError:
            return merge(
                [_failure_outcome("PERMISSION_DENIED")],
                request_id,
                0,
                0,
                None,
            )
        finally:
            _limiter.release(context.uid)
            _request_owners.pop(request_id, None)
            _cancelled.discard(request_id)

    def cancel(self, env, request_id):
        if not request_id or not isinstance(request_id, str):
            return False
        if _request_owners.get(request_id) != env.uid:
            return False
        _cancelled.add(request_id)
        log_event("info", "gs.search.cancelled", {"request_id": request_id, "latency_ms": 0})
        return True
