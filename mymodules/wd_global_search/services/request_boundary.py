"""Server-side bounds for SearchRequest input (TD-001)."""

MAX_RAW_QUERY_LENGTH = 500
MAX_CONDITIONS = 20
MAX_CONDITION_DEPTH = 3
MAX_RELATION_PATH_DEPTH = 2


class RequestBoundaryError(ValueError):
    """A request is outside the supported Search Service contract."""


def _condition_depth(value, depth=0):
    if not isinstance(value, (dict, list, tuple)):
        return depth
    children = value.values() if isinstance(value, dict) else value
    return max((_condition_depth(item, depth + 1) for item in children), default=depth)


def _validate_relation_path(value):
    if not isinstance(value, str):
        raise RequestBoundaryError("Relation path must be a string")
    if len([segment for segment in value.split(".") if segment]) > MAX_RELATION_PATH_DEPTH:
        raise RequestBoundaryError("Relation path exceeds the supported depth")


def _validate_condition(condition):
    if not isinstance(condition, dict):
        raise RequestBoundaryError("Conditions must be objects")
    if _condition_depth(condition) > MAX_CONDITION_DEPTH:
        raise RequestBoundaryError("Condition nesting exceeds the supported depth")
    for key in ("relation_path", "path"):
        if key in condition:
            _validate_relation_path(condition[key])


def validate_search_request(request):
    if not isinstance(request.raw_query, str):
        raise RequestBoundaryError("Query must be text")
    if len(request.raw_query) > MAX_RAW_QUERY_LENGTH:
        raise RequestBoundaryError("Query exceeds the supported length")
    if any(ord(character) < 32 for character in request.raw_query):
        raise RequestBoundaryError("Query contains unsupported control characters")

    conditions = [*request.parsed_conditions, *request.refinement_conditions]
    if len(conditions) > MAX_CONDITIONS:
        raise RequestBoundaryError("Too many search conditions")
    for condition in conditions:
        _validate_condition(condition)
    return request
