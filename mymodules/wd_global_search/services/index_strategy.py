"""Lightweight, read-only index strategy validation for CC-006."""


SUPPORTED_STRATEGIES = frozenset(
    {"btree", "pattern_ops", "gin_trgm", "gist_trgm", "none"}
)
DEFAULT_STRATEGIES = {
    "exact": "btree",
    "prefix": "pattern_ops",
    "contains": "gin_trgm",
}
COMPATIBLE_STRATEGIES = {
    "exact": frozenset({"btree", "none"}),
    "prefix": frozenset({"pattern_ops", "btree", "none"}),
    "contains": frozenset({"gin_trgm", "gist_trgm", "none"}),
}


def expected_strategy(operator_set):
    try:
        return DEFAULT_STRATEGIES[operator_set]
    except KeyError as exc:
        raise ValueError("Unsupported operator set: %s" % operator_set) from exc


def validate_strategy(operator_set, strategy):
    if not isinstance(strategy, str) or strategy not in SUPPORTED_STRATEGIES:
        raise ValueError("Unsupported index strategy: %s" % strategy)
    if not isinstance(operator_set, str) or operator_set not in COMPATIBLE_STRATEGIES:
        raise ValueError("Unsupported operator set: %s" % operator_set)
    if strategy not in COMPATIBLE_STRATEGIES[operator_set]:
        raise ValueError(
            "Index strategy %s is not compatible with %s"
            % (strategy, operator_set)
        )
    return True
