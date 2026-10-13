"""Server-side bounds for SearchRequest input (TD-001)."""

import unicodedata

from .types import ConditionQueryObject, KeywordTerm

MAX_RAW_QUERY_LENGTH = 500
MAX_CONDITIONS = 20
MAX_CONDITION_DEPTH = 3
MAX_RELATION_PATH_DEPTH = 2
MAX_DIMENSION_LENGTH = 100
MAX_KEYWORD_TERMS = 10
MAX_KEYWORD_LENGTH = 100
_BIDI_CONTROLS = frozenset(
    {
        0x061C,
        0x200E,
        0x200F,
        *range(0x202A, 0x202F),
        *range(0x2066, 0x206A),
    }
)
_ZERO_WIDTH_CONTROLS = frozenset({*range(0x200B, 0x200E), 0x2060, 0xFEFF})


class RequestBoundaryError(ValueError):
    """A request is outside the supported Search Service contract."""


def _validate_keyword_token(token):
    if not token or len(token) > MAX_KEYWORD_LENGTH:
        raise RequestBoundaryError("Query token length is invalid")
    for character in token:
        codepoint = ord(character)
        category = unicodedata.category(character)
        if (
            category in {"Cc", "Cs", "Pi", "Pf"}
            or codepoint in _BIDI_CONTROLS
            or codepoint in _ZERO_WIDTH_CONTROLS
            or character in "'\"()"
        ):
            raise RequestBoundaryError("Query contains an unsupported character")
    if token.upper() in {"OR", "NOT"}:
        raise RequestBoundaryError("Boolean query operators are unsupported")


def parse_multi_query(raw_query):
    if not raw_query or not raw_query.strip():
        return ()
    if not any(character.isspace() or character == "+" for character in raw_query):
        return ()

    terms = []
    explicit_plus = "+" in raw_query
    position = 0
    while position < len(raw_query):
        while position < len(raw_query) and raw_query[position].isspace():
            position += 1
        if position == len(raw_query):
            break
        if raw_query[position] == "+":
            raise RequestBoundaryError("Query contains an empty token")

        start = position
        while (
            position < len(raw_query)
            and not raw_query[position].isspace()
            and raw_query[position] != "+"
        ):
            position += 1
        token = raw_query[start:position]
        terms.append(token)

        had_whitespace = False
        while position < len(raw_query) and raw_query[position].isspace():
            position += 1
            had_whitespace = True
        if position == len(raw_query):
            break
        if raw_query[position] == "+":
            position += 1
            while position < len(raw_query) and raw_query[position].isspace():
                position += 1
            if position == len(raw_query) or raw_query[position] == "+":
                raise RequestBoundaryError("Query contains an empty token")
        elif not had_whitespace:
            raise RequestBoundaryError("Query separator is invalid")

    if len(terms) < 2 and not explicit_plus:
        return ()
    if len(terms) > MAX_KEYWORD_TERMS:
        raise RequestBoundaryError("Query has too many tokens")
    for term in terms:
        _validate_keyword_token(term)
    return tuple(KeywordTerm(term) for term in terms)


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
    if "dimension" in condition and not isinstance(condition["dimension"], str):
        raise RequestBoundaryError("Condition dimension must be text")
    if len(condition.get("dimension", "")) > MAX_DIMENSION_LENGTH:
        raise RequestBoundaryError("Condition dimension exceeds the supported length")
    if "operator" in condition and not isinstance(condition["operator"], str):
        raise RequestBoundaryError("Condition operator must be text")
    for key in ("relation_path", "path"):
        if key in condition:
            _validate_relation_path(condition[key])


def validate_search_request(request):
    if not isinstance(request.raw_query, str):
        raise RequestBoundaryError("Query must be text")
    if len(request.raw_query) > MAX_RAW_QUERY_LENGTH:
        raise RequestBoundaryError("Query exceeds the supported length")
    if any(unicodedata.category(character) == "Cc" for character in request.raw_query):
        raise RequestBoundaryError("Query contains unsupported control characters")

    keyword_terms = parse_multi_query(request.raw_query)
    field_conditions = list(request.parsed_conditions)
    if not keyword_terms and request.raw_query.strip():
        field_conditions.append(
            {
                "dimension": "name",
                "operator": "ilike",
                "value": request.raw_query.strip(),
            }
        )
    query_object = ConditionQueryObject(
        keyword_terms=keyword_terms,
        field_conditions=tuple(field_conditions),
    )
    conditions = [*request.parsed_conditions, *request.refinement_conditions]
    condition_count = (
        len(request.parsed_conditions)
        + len(request.refinement_conditions)
        + len(keyword_terms)
        + (1 if not keyword_terms and request.raw_query.strip() else 0)
    )
    if condition_count > MAX_CONDITIONS:
        raise RequestBoundaryError("Too many search conditions")
    for condition in conditions:
        _validate_condition(condition)
    return query_object
