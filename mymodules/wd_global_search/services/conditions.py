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
        key = (dimension, repr(value), condition.get("operator", "contains"))
        if key not in seen:
            seen.add(key)
            merged.append(
                {
                    "dimension": dimension,
                    "value": value,
                    "operator": condition.get("operator", "contains"),
                }
            )
    return EffectiveConditions(tuple(merged), tuple(keyword_terms))
