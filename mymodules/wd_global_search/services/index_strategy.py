"""Lightweight, read-only index strategy validation for CC-006."""


SUPPORTED_STRATEGIES = frozenset({"btree", "pattern_ops", "gin_trgm", "none"})
DEFAULT_STRATEGIES = {
    "exact": "btree",
    "prefix": "pattern_ops",
    "contains": "gin_trgm",
}


def expected_strategy(operator_set):
    try:
        return DEFAULT_STRATEGIES[operator_set]
    except KeyError as exc:
        raise ValueError("Unsupported operator set: %s" % operator_set) from exc


def validate_strategy(operator_set, strategy):
    if strategy not in SUPPORTED_STRATEGIES:
        raise ValueError("Unsupported index strategy: %s" % strategy)
    if strategy == "none":
        return True
    if strategy != expected_strategy(operator_set):
        raise ValueError(
            "Index strategy %s is not compatible with %s"
            % (strategy, operator_set)
        )
    return True
