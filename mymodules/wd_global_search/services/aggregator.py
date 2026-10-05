from .types import SearchResponse


def merge(outcomes, request_id, offset, limit, config_version):
    all_results = []
    identities = set()
    counts = {}
    errors = []
    for outcome in outcomes:
        if outcome.status == "SUCCESS":
            counts[outcome.resource] = outcome.count
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
    if errors and page:
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
        counts={"all": len(all_results), "by_resource": counts},
        errors=errors,
        meta={
            "request_id": request_id,
            "config_version": config_version,
            "completed_resources": [item.resource for item in outcomes if item.status == "SUCCESS"],
            "failed_resources": [item.resource for item in outcomes if item.error],
        },
    )
