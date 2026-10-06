import hashlib
import json
import time
import uuid

from odoo.exceptions import AccessError

from .aggregator import merge
from .conditions import merge as merge_conditions
from .cursor import decode, encode
from .errors import error
from .executor import execute
from .limiter import UserLimiter
from .provider import ConfigurationError, published_snapshot
from .request_boundary import RequestBoundaryError, validate_search_request
from .observability import hash_value, log_event
from .types import ResourceOutcome, SearchRequest, UserContext


_limiter = UserLimiter()
_cancelled = set()
_request_owners = {}
_SEARCH_TIMEOUT_SECONDS = 5
_CURSOR_SORT_VERSION = "v1"


def _failure_outcome(code):
    return ResourceOutcome(resource="request", status="FAILED", error=error(code))


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
    def search(self, env, request, domain_key):
        context = user_context(env)
        request_id = str(uuid.uuid4())
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
            conditions = merge_conditions(
                request.parsed_conditions, request.refinement_conditions
            )
            cursor_secret = env["ir.config_parameter"].sudo().get_param("database.secret")
            if not cursor_secret:
                return merge([_failure_outcome("CONFIGURATION_ERROR")], request_id, 0, 0, None)
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
                    "resources": list(request.resource_scope),
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
                    return merge([_failure_outcome("CURSOR_EXPIRED")], request_id, 0, 0, None)
                except ValueError:
                    return merge([_failure_outcome("CURSOR_INVALID")], request_id, 0, 0, None)
                cursor_offset = int(cursor_data.get("offset", request.offset))
            resources = snapshot.get("resources", [])
            if request.resource_scope:
                resources = [item for item in resources if item["key"] in request.resource_scope]
            outcomes = []
            deadline = time.monotonic() + _SEARCH_TIMEOUT_SECONDS
            for resource in resources:
                if request_id in _cancelled:
                    outcomes.append(_failure_outcome("CANCELLED"))
                    break
                if time.monotonic() >= deadline:
                    outcomes.append(_failure_outcome("TIMEOUT"))
                    break
                fetch_limit = min(max(request.limit + cursor_offset, request.limit), 50)
                outcomes.append(execute(env, resource, conditions, fetch_limit, context))
            response = merge(
                outcomes,
                request_id,
                cursor_offset,
                request.limit,
                snapshot_info["version_id"],
            )
            if response.results and len(response.results) == request.limit:
                response.meta["next_cursor"] = encode(
                    {
                        "offset": cursor_offset + request.limit,
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
