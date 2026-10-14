from dataclasses import dataclass

from .types import KeywordTerm


@dataclass(frozen=True)
class EffectiveConditions:
    values: tuple[dict, ...] = ()
    keyword_terms: tuple[KeywordTerm, ...] = ()


def merge(parsed, refinement, deleted=(), *, keyword_terms=()):
    merged = []
    seen = set()
    for condition in [*(parsed or ()), *(refinement or ())]:
        dimension = condition.get("dimension")
        value = condition.get("value")
        if not dimension or value in (None, ""):
            continue
        operator = condition.get(
            "operator", "=" if dimension == "state" else "contains"
        )
        key = (dimension, repr(value), operator)
        if key not in seen:
            seen.add(key)
            merged.append(
                {
                    "dimension": dimension,
                    "value": value,
                    "operator": operator,
                }
            )
    return EffectiveConditions(tuple(merged), tuple(keyword_terms))
