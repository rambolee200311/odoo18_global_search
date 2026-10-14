import math
import re
import time
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from odoo.osv.expression import AND, OR

from .card import (
    authorized_card_field_names,
    read_card_values,
    serialize_card_fields,
    serialize_card_template,
)
from .errors import error
from .permission_boundary import (
    AuthorizationError,
    authorize_fields,
    authorize_relation_path,
    authorize_resource,
    authorize_searchable_fields,
)
from .field_path import (
    FieldPathError,
    operator_domain,
    validate_field_path,
    wrap_path_domain,
)
from .types import ResourceOutcome


class SearchTimeout(Exception):
    pass


def _check_deadline(deadline):
    if deadline is not None and time.monotonic() >= deadline:
        raise SearchTimeout()


def _relation_search_fields(model, path, context):
    relation = model
    for segment in path.split("."):
        field = relation._fields.get(segment)
        if field is None or not field.comodel_name:
            return []
        relation = model.env[field.comodel_name]
        model = relation
    candidates = [
        field_name
        for field_name in ("name", "display_name", "ref", "default_code", "barcode")
        if field_name in relation._fields
    ]
    try:
        readable_fields = authorize_fields(relation, candidates, context)
    except AuthorizationError:
        return []
    return [
        "%s.%s" % (path, field_name)
        for field_name in readable_fields
    ]


def _date_bounds(value, context):
    tz = ZoneInfo(context.tz or "UTC")
    now = datetime.now(tz)
    if isinstance(value, dict):
        start = value.get("start")
        end = value.get("end")
    elif value == "today":
        start = end = now.date().isoformat()
        end = (now.date() + timedelta(days=1)).isoformat()
    elif value == "this_week":
        week_start = 6 if (context.lang or "en_US").startswith("en_US") else 0
        delta = (now.weekday() - week_start) % 7
        start_date = now.date() - timedelta(days=delta)
        start = start_date.isoformat()
        end = (start_date + timedelta(days=7)).isoformat()
    elif value == "this_month":
        start_date = now.date().replace(day=1)
        next_month = (start_date.replace(day=28) + timedelta(days=4)).replace(day=1)
        start = start_date.isoformat()
        end = next_month.isoformat()
    else:
        return None
    if not isinstance(start, str) or not isinstance(end, str) or end <= start:
        return None
    start_local = datetime.fromisoformat(start).replace(tzinfo=tz)
    end_local = datetime.fromisoformat(end).replace(tzinfo=tz)
    return (
        start_local.astimezone(ZoneInfo("UTC")).replace(tzinfo=None).isoformat(sep=" "),
        end_local.astimezone(ZoneInfo("UTC")).replace(tzinfo=None).isoformat(sep=" "),
    )


def _keyword_field_value(field_type, value):
    if field_type in {"char", "text", "selection"}:
        return value
    if field_type == "integer":
        if not re.fullmatch(r"[+-]?[0-9]+", value):
            return None
        return int(value)
    if field_type in {"float", "monetary"}:
        try:
            parsed = Decimal(value)
            converted = float(parsed)
        except (InvalidOperation, OverflowError, ValueError):
            return None
        return converted if parsed.is_finite() and math.isfinite(converted) else None
    if field_type == "date":
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            return None
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    if field_type == "datetime":
        if not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?",
            value,
        ):
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    if field_type == "boolean":
        normalized = value.casefold()
        if normalized == "true":
            return True
        if normalized == "false":
            return False
        return None
    return None


def _keyword_term_domain(model, field_configs, term):
    alternatives = []
    eligible_field_count = 0
    for field_config in field_configs:
        resolved_path = validate_field_path(
            model,
            field_config.get("name"),
            operator_set=field_config.get("operator_set", "exact"),
            index_strategy=field_config.get("index_strategy", "none"),
            collection_match=field_config.get("collection_match", "any"),
        )
        field_type = resolved_path.fields[-1].type
        if field_type in {"char", "text"}:
            eligible_field_count += 1
            escaped_value = (
                term.value.replace("\\", "\\\\")
                .replace("%", "\\%")
                .replace("_", "\\_")
            )
            operator, value = "ilike", "%%%s%%" % escaped_value
        elif field_config.get("operator_set", "exact") == "exact":
            value = _keyword_field_value(field_type, term.value)
            eligible_field_count += 1
            if value is None:
                continue
            operator, value = operator_domain("exact", value)
        else:
            continue
        if value is None:
            continue
        alternatives.append(
            wrap_path_domain(
                resolved_path,
                [(resolved_path.segments[-1], operator, value)],
            )
        )
    if not eligible_field_count:
        raise FieldPathError(
            "No readable Searchable Field is available for this query."
        )
    return OR(alternatives) if alternatives else [("id", "=", 0)]


def _condition_domain(model, field_configs, relation_paths, resource, conditions, context):
    configs_by_name = {item["name"]: item for item in field_configs}
    direct_fields = [
        name for name in configs_by_name if "." not in name
    ]
    grouped = {}
    path_grouped = {}
    date_conditions = []
    state_conditions = []
    for condition in conditions.values:
        field = condition["dimension"]
        if field == "date":
            date_conditions.append(condition)
            continue
        if field == "state":
            state_conditions.append(condition)
            continue
        if field == "name":
            grouped.setdefault(field, []).append(condition)
        elif field in configs_by_name:
            target = path_grouped if "." in field else grouped
            target.setdefault(field, []).append(condition)

    domain_parts = []
    for field, values in grouped.items():
        search_fields = (
            direct_fields
            if field == "name"
            else [field]
        )
        if field == "name":
            for path in relation_paths:
                search_fields.extend(_relation_search_fields(model, path, context))
        alternatives = []
        for condition in values:
            operator = condition["operator"]
            if operator not in {"=", "ilike", "prefix"}:
                operator = "ilike"
            if operator == "prefix":
                operator = "ilike"
                value = "%s%%" % condition["value"]
            else:
                value = condition["value"]
            alternatives.extend(
                [[(search_field, operator, value)] for search_field in search_fields]
            )
        if alternatives:
            domain_parts.append(OR(alternatives))

    for field_name, values in path_grouped.items():
        field_config = configs_by_name[field_name]
        resolved_path = validate_field_path(
            model,
            field_name,
            operator_set=field_config.get("operator_set", "exact"),
            index_strategy=field_config.get("index_strategy", "none"),
            collection_match=field_config.get("collection_match", "any"),
        )
        predicates = []
        seen_values = set()
        for condition in values:
            value = condition["value"]
            value_key = (type(value).__name__, repr(value))
            if value_key in seen_values:
                continue
            seen_values.add(value_key)
            operator, query_value = operator_domain(
                field_config.get("operator_set", "exact"), value
            )
            if operator == "ilike" and not isinstance(value, str):
                continue
            terminal_field = resolved_path.segments[-1]
            predicates.append(
                wrap_path_domain(
                    resolved_path,
                    [(terminal_field, operator, query_value)],
                )
            )
        if predicates:
            if (
                resolved_path.collection_match_applicable
                and field_config.get("collection_match", "any") == "all"
            ):
                domain_parts.append(AND(predicates))
            else:
                domain_parts.append(OR(predicates))

    for condition in state_conditions:
        value = condition.get("value")
        if condition.get("operator") != "=" or not isinstance(value, str):
            raise FieldPathError("Invalid business state condition.")
        mapping = next(
            (
                item
                for item in resource.get("states", ())
                if item.get("business_state") == value
            ),
            None,
        )
        if mapping is None:
            raise FieldPathError("Business state is not configured.")
        technical_values = mapping.get("technical_values")
        if not isinstance(technical_values, str):
            raise FieldPathError("Invalid business state mapping.")
        values = [item.strip() for item in technical_values.split(",")]
        if not values or any(not item for item in values):
            raise FieldPathError("Invalid business state mapping.")
        if "state" not in model._fields:
            raise FieldPathError("State field is not available.")
        domain_parts.append([("state", "in", list(dict.fromkeys(values)))])

    for term in getattr(conditions, "keyword_terms", ()):
        domain_parts.append(_keyword_term_domain(model, field_configs, term))

    for date_condition in date_conditions:
        bounds = _date_bounds(date_condition.get("value"), context)
        if not bounds:
            continue
        for business_date in resource.get("business_dates", ()):
            if business_date.get("model_name") != model._name:
                continue
            field_name = business_date.get("field_name")
            if field_name not in model._fields:
                continue
            if model._fields[field_name].type == "date":
                domain_parts.append(
                    [
                        (field_name, ">=", bounds[0][:10]),
                        (field_name, "<", bounds[1][:10]),
                    ]
                )
            else:
                domain_parts.append(
                    [
                        (field_name, ">=", bounds[0]),
                        (field_name, "<", bounds[1]),
                    ]
                )
            break
    return AND(domain_parts)


def authorize_search_resource(
    env, resource, context=None, max_relation_depth=None
):
    authorize_resource(env, resource, context)
    model_configs = resource.get("models", ())
    if not model_configs:
        raise AuthorizationError("RESOURCE_NOT_ACCESSIBLE")
    for model_config in model_configs:
        model = env[model_config["model_name"]]
        if max_relation_depth is None:
            authorize_searchable_fields(
                env, model, model_config.get("fields", ()), context
            )
        else:
            authorize_searchable_fields(
                env,
                model,
                model_config.get("fields", ()),
                context,
                max_relation_depth=max_relation_depth,
            )
    for path in resource.get("relation_paths", ()):
        authorize_relation_path(env, resource, path["path"], context)


def execute(
    env,
    resource,
    conditions,
    limit,
    context=None,
    offset=0,
    deadline=None,
    max_relation_depth=None,
):
    started = time.monotonic()
    try:
        _check_deadline(deadline)
        if max_relation_depth is None:
            authorize_search_resource(env, resource, context)
        else:
            authorize_search_resource(
                env,
                resource,
                context,
                max_relation_depth=max_relation_depth,
            )
        _check_deadline(deadline)
        results = []
        resource_count = 0
        remaining_offset = max(0, offset)
        remaining_limit = max(0, limit)
        for model_config in sorted(
            resource.get("models", ()), key=lambda item: item["model_name"]
        ):
            model_name = model_config["model_name"]
            model = env[model_name]
            field_configs = authorize_searchable_fields(
                env, model, model_config.get("fields", ()), context
            )
            if any(
                condition["dimension"] == "state"
                for condition in conditions.values
            ):
                authorize_fields(model, ["state"], context)
            relation_paths = [
                path["path"]
                for path in resource.get("relation_paths", ())
                if path.get("path")
            ]
            domain = _condition_domain(
                model, field_configs, relation_paths, resource, conditions, context
            )
            _check_deadline(deadline)
            model_count = model.search_count(domain)
            _check_deadline(deadline)
            resource_count += model_count
            model_offset = min(remaining_offset, model_count)
            remaining_offset -= model_offset
            if remaining_limit == 0 or model_offset == model_count:
                continue
            readable_card_fields = authorized_card_field_names(
                resource, model, context
            )
            _check_deadline(deadline)
            records = model.search(
                domain,
                offset=model_offset,
                limit=remaining_limit,
                order="id asc",
            )
            _check_deadline(deadline)
            values = (
                read_card_values(
                    records, readable_card_fields, resource["card_template"]
                )
                if resource.get("card_template")
                else [(value, readable_card_fields) for value in records.read(readable_card_fields)]
            )
            _check_deadline(deadline)
            for value, row_readable_fields in values:
                record_id = value["id"]
                results.append(
                    {
                        "id": record_id,
                        "_resource": resource["key"],
                        "_model": model_name,
                        "_record_id": record_id,
                        "snapshot": (
                            {
                                "rendered_text": serialize_card_template(
                                    env,
                                    resource,
                                    model_name,
                                    value,
                                    row_readable_fields,
                                )
                            }
                            if resource.get("card_template")
                            else {
                                "fields": serialize_card_fields(
                                    env,
                                    resource,
                                    model_name,
                                    value,
                                    row_readable_fields,
                                    context,
                                )
                            }
                        ),
                    }
                )
            remaining_limit -= len(values)
    except AuthorizationError as exc:
        return ResourceOutcome(
            resource=resource["key"],
            status="FAILED",
            error=error(exc.code, resource=resource["key"]),
            latency=time.monotonic() - started,
        )
    except (FieldPathError, SearchTimeout) as exc:
        code = "TIMEOUT" if isinstance(exc, SearchTimeout) else "CONFIGURATION_ERROR"
        return ResourceOutcome(
            resource=resource["key"],
            status="FAILED",
            error=error(code, resource=resource["key"]),
            latency=time.monotonic() - started,
        )
    if not resource.get("models"):
        return ResourceOutcome(
            resource=resource["key"],
            status="FAILED",
            error=error("CONFIGURATION_ERROR", resource=resource["key"]),
            latency=time.monotonic() - started,
        )
    return ResourceOutcome(
        resource=resource["key"],
        status="SUCCESS",
        results=results,
        count=resource_count,
        latency=time.monotonic() - started,
    )
