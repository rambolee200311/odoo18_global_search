import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .errors import error
from .permission_boundary import (
    AuthorizationError,
    authorize_fields,
    authorize_relation_path,
    authorize_resource,
)
from .types import ResourceOutcome


def _relation_search_fields(model, path):
    relation = model
    for segment in path.split("."):
        field = relation._fields.get(segment)
        if field is None or not field.comodel_name:
            return []
        relation = model.env[field.comodel_name]
        model = relation
    return [
        "%s.%s" % (path, field_name)
        for field_name in ("name", "display_name", "ref", "default_code")
        if field_name in relation._fields
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


def _condition_domain(model, fields, relation_paths, resource, conditions, context):
    grouped = {}
    date_conditions = []
    for condition in conditions.values:
        field = condition["dimension"]
        if field == "date":
            date_conditions.append(condition)
            continue
        search_fields = [field] if field in fields else []
        if field == "name":
            search_fields = list(fields)
            for path in relation_paths:
                search_fields.extend(_relation_search_fields(model, path))
        if not search_fields:
            continue
        grouped.setdefault(field, []).append(condition)

    domain = []
    for field, values in grouped.items():
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
            alternatives.extend([(search_field, operator, value) for search_field in search_fields])
        if len(alternatives) == 1:
            domain.extend(alternatives)
        elif alternatives:
            domain.extend(["|"] * (len(alternatives) - 1) + alternatives)
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
                domain.extend(
                    [
                        (field_name, ">=", bounds[0][:10]),
                        (field_name, "<", bounds[1][:10]),
                    ]
                )
            else:
                domain.extend(
                    [
                        (field_name, ">=", bounds[0]),
                        (field_name, "<", bounds[1]),
                    ]
                )
            break
    return domain


def execute(env, resource, conditions, limit, context=None, offset=0):
    started = time.monotonic()
    try:
        authorize_resource(env, resource, context)
        results = []
        resource_count = 0
        remaining_offset = max(0, offset)
        remaining_limit = max(0, limit)
        for model_config in sorted(
            resource.get("models", ()), key=lambda item: item["model_name"]
        ):
            model_name = model_config["model_name"]
            model = env[model_name]
            fields = [item["name"] for item in model_config.get("fields", ())]
            fields = authorize_fields(model, fields, context)
            for path in resource.get("relation_paths", ()):
                authorize_relation_path(env, resource, path["path"], context)
            relation_paths = [
                path["path"]
                for path in resource.get("relation_paths", ())
                if path.get("path")
            ]
            domain = _condition_domain(
                model, fields, relation_paths, resource, conditions, context
            )
            model_count = model.search_count(domain)
            resource_count += model_count
            model_offset = min(remaining_offset, model_count)
            remaining_offset -= model_offset
            if remaining_limit == 0 or model_offset == model_count:
                continue
            records = model.search(
                domain,
                offset=model_offset,
                limit=remaining_limit,
                order="id asc",
            )
            values = records.read(fields)
            for value in values:
                value.update(
                    {
                        "_resource": resource["key"],
                        "_model": model_name,
                        "_record_id": value["id"],
                    }
                )
            results.extend(values)
            remaining_limit -= len(values)
    except AuthorizationError as exc:
        return ResourceOutcome(
            resource=resource["key"],
            status="FAILED",
            error=error(exc.code, resource=resource["key"]),
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
