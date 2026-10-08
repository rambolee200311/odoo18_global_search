from .types import SearchResponse


def merge(outcomes, request_id, offset, limit, config_version, count_scope=None):
    all_results = []
    identities = set()
    counts = {}
    resource_counts = {}
    errors = []
    selected_resources = None if count_scope is None else set(count_scope)
    for outcome in outcomes:
        if outcome.status == "SUCCESS":
            resource_counts[outcome.resource] = (
                resource_counts.get(outcome.resource, 0) + outcome.count
            )
            if selected_resources is None or outcome.resource in selected_resources:
                counts[outcome.resource] = counts.get(outcome.resource, 0) + outcome.count
        for result in outcome.results:
            identity = (
                result.get("_resource"),
                result.get("_model"),
                result.get("_record_id", result.get("id")),
            )
            if identity not in identities:
                identities.add(identity)
                all_results.append(result)
        if outcome.error and outcome.resource not in {item.get("resource") for item in errors}:
            errors.append(outcome.error)

    errors.sort(key=lambda item: item.get("resource") or "")
    all_results.sort(key=lambda item: (item.get("_resource", ""), item.get("_model", ""), item.get("id", 0)))
    page = all_results[offset : offset + limit]
    has_success = any(item.status == "SUCCESS" for item in outcomes)
    if errors and (page or has_success):
        status = "PARTIAL_SUCCESS"
    elif errors:
        status = "FAILED"
    elif not page:
        status = "EMPTY"
    else:
        status = "SUCCESS"
    return SearchResponse(
        status=status,
        request_id=request_id,
        results=page,
        counts={"all": sum(counts.values()), "by_resource": counts},
        errors=errors,
        meta={
            "request_id": request_id,
            "config_version": config_version,
            "completed_resources": [item.resource for item in outcomes if item.status == "SUCCESS"],
            "failed_resources": [item.resource for item in outcomes if item.error],
            "resource_counts": resource_counts,
        },
    )
