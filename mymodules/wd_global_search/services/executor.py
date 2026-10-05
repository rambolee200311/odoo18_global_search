import time

from .errors import error
from .permission_boundary import (
    AuthorizationError,
    authorize_fields,
    authorize_relation_path,
    authorize_resource,
)
from .types import ResourceOutcome


def _condition_domain(fields, conditions):
    grouped = {}
    for condition in conditions.values:
        field = condition["dimension"]
        if field not in fields:
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
            alternatives.extend([(field, operator, value)])
        if len(alternatives) == 1:
            domain.extend(alternatives)
        elif alternatives:
            domain.extend(["|"] * (len(alternatives) - 1) + alternatives)
    return domain


def execute(env, resource, conditions, limit, context=None):
    started = time.monotonic()
    outcomes = []
    try:
        authorize_resource(env, resource, context)
        for model_config in resource.get("models", ()):
            model_name = model_config["model_name"]
            model = env[model_name]
            fields = [item["name"] for item in model_config.get("fields", ())]
            fields = authorize_fields(model, fields, context)
            for path in resource.get("relation_paths", ()):
                authorize_relation_path(env, resource, path["path"], context)
            domain = _condition_domain(fields, conditions)
            records = model.search(domain, limit=limit, order="id asc")
            values = records.read(fields)
            for value in values:
                value.update(
                    {
                        "_resource": resource["key"],
                        "_model": model_name,
                        "_record_id": value["id"],
                    }
                )
            outcomes.append(
                ResourceOutcome(
                    resource=resource["key"],
                    status="SUCCESS",
                    results=values,
                    count=len(values),
                    latency=time.monotonic() - started,
                )
            )
    except AuthorizationError as exc:
        return ResourceOutcome(
            resource=resource["key"],
            status="FAILED",
            error=error(exc.code, resource=resource["key"]),
            latency=time.monotonic() - started,
        )
    if not outcomes:
        return ResourceOutcome(
            resource=resource["key"],
            status="FAILED",
            error=error("CONFIGURATION_ERROR", resource=resource["key"]),
            latency=time.monotonic() - started,
        )
    results = [item for outcome in outcomes for item in outcome.results]
    return ResourceOutcome(
        resource=resource["key"],
        status="SUCCESS",
        results=results,
        count=len(results),
        latency=time.monotonic() - started,
    )
