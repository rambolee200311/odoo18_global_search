ERROR_CODES = {
    "SUCCESS",
    "PARTIAL_SUCCESS",
    "FAILED",
    "TIMEOUT",
    "RATE_LIMITED",
    "PERMISSION_DENIED",
    "CONFIGURATION_ERROR",
    "CONFIGURATION_TOO_LARGE",
    "CONCURRENCY_LIMIT",
    "CURSOR_INVALID",
    "CURSOR_EXPIRED",
    "INTERNAL_ERROR",
    "INVALID_REQUEST",
    "RESOURCE_NOT_ACCESSIBLE",
    "FIELD_NOT_READABLE",
    "RELATION_PATH_BLOCKED",
}


def error(code, message="Some search data is unavailable", scope="request", resource=None):
    return {
        "scope": scope,
        "resource": resource,
        "code": code,
        "message": message,
        "retryable": code in {"TIMEOUT", "RATE_LIMITED", "CONCURRENCY_LIMIT"},
    }
