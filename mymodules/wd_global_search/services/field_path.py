import re
from dataclasses import dataclass

from .index_strategy import validate_strategy


MAX_FIELD_PATH_LENGTH = 100
FIELD_PATH_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*")
SUPPORTED_TERMINAL_TYPES = frozenset(
    {"char", "text", "integer", "float", "date", "datetime", "boolean", "selection", "monetary"}
)
RELATION_TYPES = frozenset({"many2one", "many2many", "one2many"})
class FieldPathError(ValueError):
    pass


@dataclass(frozen=True)
class ResolvedFieldPath:
    segments: tuple[str, ...]
    fields: tuple
    relation_types: tuple[str, ...]
    relation_depth: int
    collection_match_applicable: bool


def validate_field_path(
    root_model,
    field_path,
    operator_set="exact",
    index_strategy="none",
    collection_match="any",
    max_relation_depth=None,
):
    if (
        not isinstance(field_path, str)
        or len(field_path) > MAX_FIELD_PATH_LENGTH
        or not FIELD_PATH_PATTERN.fullmatch(field_path)
    ):
        raise FieldPathError("Searchable Field path has invalid syntax or exceeds 100 characters.")

    segments = tuple(field_path.split("."))
    if len(segments) > 4:
        raise FieldPathError("Searchable Field path exceeds the maximum segment count.")

    model = root_model
    resolved_fields = []
    relation_types = []
    visited_edges = set()

    for position, field_name in enumerate(segments):
        field = model._fields.get(field_name)
        if field is None:
            raise FieldPathError(
                "Field %s does not exist on %s." % (field_name, model._name)
            )
        resolved_fields.append(field)
        is_terminal = position == len(segments) - 1
        if is_terminal:
            continue
        if field.type not in RELATION_TYPES or not field.comodel_name:
            raise FieldPathError(
                "Intermediate field %s on %s must be a supported relation."
                % (field_name, model._name)
            )

        edge = (model._name, field_name)
        if edge in visited_edges:
            raise FieldPathError("Searchable Field path contains a repeated relation edge.")
        visited_edges.add(edge)

        if position and field.type != "many2one":
            raise FieldPathError(
                "Only Many2one fields may follow the initial relation."
            )
        relation_types.append(field.type)
        try:
            model = model.env[field.comodel_name]
        except KeyError as exc:
            raise FieldPathError(
                "Related model %s does not exist." % field.comodel_name
            ) from exc

    if relation_types:
        first_type = relation_types[0]
        maximum_depth = {
            "many2one": 3,
            "many2many": 2,
            "one2many": 3,
        }[first_type]
        if len(relation_types) > maximum_depth:
            raise FieldPathError(
                "Searchable Field path exceeds the %s relation-depth limit."
                % first_type
            )
    else:
        first_type = None

    terminal = resolved_fields[-1]
    if terminal.type in RELATION_TYPES or terminal.type not in SUPPORTED_TERMINAL_TYPES:
        raise FieldPathError("Terminal field type is not supported for Searchable Field paths.")
    if not terminal.store:
        raise FieldPathError("Terminal field must be stored and ORM-searchable.")
    try:
        validate_strategy(operator_set, index_strategy)
    except ValueError as exc:
        raise FieldPathError(str(exc)) from exc
    if operator_set != "exact" and terminal.type not in {"char", "text"}:
        raise FieldPathError(
            "Prefix and contains operators require a Char or Text terminal field."
        )
    if index_strategy in {"gin_trgm", "gist_trgm", "pattern_ops"} and terminal.type not in {
        "char",
        "text",
    }:
        raise FieldPathError("Text index strategies require a Char or Text terminal field.")
    if index_strategy != "none" and not terminal.store:
        raise FieldPathError("An index strategy requires a stored terminal field.")
    if collection_match not in {"any", "all"}:
        raise FieldPathError("Collection match must be any or all.")
    collection_match_applicable = first_type in {"many2many", "one2many"}
    if not collection_match_applicable and collection_match != "any":
        raise FieldPathError("Collection match applies only to Many2many and One2many paths.")
    if (
        max_relation_depth is not None
        and len(relation_types) > max_relation_depth
    ):
        raise FieldPathError(
            "Searchable Field path exceeds the Resource relation-depth limit."
        )

    return ResolvedFieldPath(
        segments=segments,
        fields=tuple(resolved_fields),
        relation_types=tuple(relation_types),
        relation_depth=len(relation_types),
        collection_match_applicable=collection_match_applicable,
    )


def wrap_path_domain(resolved_path, terminal_domain):
    domain = terminal_domain
    for field_name in reversed(resolved_path.segments[:-1]):
        domain = [(field_name, "any", domain)]
    return domain


def operator_domain(operator_set, value):
    if operator_set == "exact":
        return "=", value
    if operator_set == "prefix":
        return "ilike", "%s%%" % value
    if operator_set == "contains":
        return "ilike", "%%%s%%" % value
    raise FieldPathError("Searchable Field operator is unsupported.")
