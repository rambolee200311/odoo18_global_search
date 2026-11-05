"""Shared, dependency-free data contracts for mapping proposal validation."""

from dataclasses import asdict, dataclass
from typing import Any, Mapping

MAPPING_SCHEMA_VERSION = "m2.mapping-proposal.v1"
SUPPORTED_VALUE_TYPES = frozenset({"string", "number", "boolean", "date", "datetime"})
TARGET_VALUE_TYPES = SUPPORTED_VALUE_TYPES | {"formula"}
CLARIFICATION_REASON_CODES = frozenset(
    {"missing_source", "ambiguous_mapping", "unsupported_target", "conflicting_instruction"}
)
ROOT_KEYS = frozenset({"schema_version", "mappings", "clarifications", "skipped_targets"})
OPTIONAL_ROOT_KEYS = frozenset({"clear_targets", "clear_columns", "format_patches", "cell_edits", "header_edits"})
EXTENDED_ROOT_KEYS = ROOT_KEYS | OPTIONAL_ROOT_KEYS


def has_valid_root_keys(keys: Any) -> bool:
    return ROOT_KEYS.issubset(keys) and keys.issubset(EXTENDED_ROOT_KEYS)
MAPPING_KEYS = frozenset({"element_id", "source_field", "value_type"})
FALLBACK_MAPPING_KEYS = frozenset({"element_id", "source_fields", "value_type"})
CONCAT_MAPPING_KEYS = frozenset({"element_id", "concat_fields", "value_type"})
CONCAT_SEPARATOR_MAPPING_KEYS = CONCAT_MAPPING_KEYS | {"separator"}
FORMULA_MAPPING_KEYS = frozenset({"element_id", "formula", "value_type"})
LITERAL_MAPPING_KEYS = frozenset({"element_id", "literal_value", "value_type"})
MAPPING_TRANSFORM_KEYS = MAPPING_KEYS | {"transform"}
FALLBACK_TRANSFORM_MAPPING_KEYS = FALLBACK_MAPPING_KEYS | {"transform"}
MAPPING_KEY_SHAPES = (
    MAPPING_KEYS,
    FALLBACK_MAPPING_KEYS,
    CONCAT_MAPPING_KEYS,
    CONCAT_SEPARATOR_MAPPING_KEYS,
    FORMULA_MAPPING_KEYS,
    LITERAL_MAPPING_KEYS,
    MAPPING_TRANSFORM_KEYS,
    FALLBACK_TRANSFORM_MAPPING_KEYS,
)
CLARIFICATION_KEYS = frozenset({"element_id", "reason_code", "question"})


def normalize_empty_value_mappings(proposal: Any) -> Any:
    """Represent explicit empty literal mappings as clear targets.

    The compact ``{"element_id": ..., "value": ""}`` form is accepted
    only as an explicit blank operation. A model may also include a
    ``value_type`` hint; it is syntax metadata and does not change the clear
    operation. Non-empty values use the explicit typed ``literal_value`` shape.
    """
    if not isinstance(proposal, Mapping) or not isinstance(proposal.get("mappings"), list):
        return proposal
    remaining: list[Any] = []
    empty_targets: list[Any] = []
    for item in proposal["mappings"]:
        if (
            isinstance(item, Mapping)
            and set(item) in (
                {"element_id", "value"},
                {"element_id", "value", "value_type"},
            )
            and item.get("value") in ("", None)
            and (
                "value_type" not in item
                or item.get("value_type") in SUPPORTED_VALUE_TYPES
            )
        ):
            empty_targets.append(item.get("element_id"))
        else:
            remaining.append(item)
    if not empty_targets:
        return proposal
    normalized = dict(proposal)
    normalized["mappings"] = remaining
    clear_targets = normalized.get("clear_targets", [])
    if isinstance(clear_targets, list):
        normalized["clear_targets"] = [*clear_targets, *empty_targets]
    return normalized


def normalize_legacy_header_edits(proposal: Any) -> Any:
    """Read historical header edits as the generic explicit cell operation.

    ``header_edits`` is retained as an input compatibility shape for Sessions
    created before explicit writes were generalized. New Proposals use
    ``cell_edits`` and carry a typed scalar value.
    """
    if not isinstance(proposal, Mapping) or "header_edits" not in proposal:
        return proposal
    normalized = dict(proposal)
    legacy = normalized.pop("header_edits")
    if "cell_edits" in normalized:
        # Leave both keys in place so the strict parser/validator rejects the
        # ambiguous duplicate instead of guessing which operation wins.
        normalized["header_edits"] = legacy
        return normalized
    if isinstance(legacy, list):
        normalized["cell_edits"] = [
            {**item, "value_type": "string"}
            if isinstance(item, Mapping) and set(item) == {"element_id", "value"}
            else item
            for item in legacy
        ]
    else:
        normalized["cell_edits"] = legacy
    return normalized


class MappingParseError(ValueError):
    """A stable, safe-to-display parse failure without the rejected input."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class ParseLimits:
    """Finite input limits frozen for CC-M2-001."""

    max_json_bytes: int = 65_536
    max_mappings: int = 200
    max_clarifications: int = 100
    max_skipped_targets: int = 200
    max_identifier_chars: int = 255
    max_question_chars: int = 2_000

    def __post_init__(self) -> None:
        for value in asdict(self).values():
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError("parse limits must be positive integers")


@dataclass(frozen=True)
class ValidationReport:
    """Deterministic validation result suitable for JSON serialization."""

    structural_errors: tuple[str, ...] = ()
    unknown_targets: tuple[str, ...] = ()
    unknown_fields: tuple[str, ...] = ()
    type_errors: tuple[str, ...] = ()
    duplicates: tuple[str, ...] = ()
    missing_required: tuple[str, ...] = ()
    clarifications: tuple[str, ...] = ()
    skipped_unapproved: tuple[str, ...] = ()
    ready_for_review: bool = False

    @property
    def status(self) -> str:
        if self.ready_for_review:
            return "ready"
        if (
            self.structural_errors
            or self.unknown_targets
            or self.unknown_fields
            or self.type_errors
            or self.duplicates
            or self.skipped_unapproved
        ):
            return "invalid"
        return "incomplete"

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        for key, value in result.items():
            if isinstance(value, tuple):
                result[key] = list(value)
        result["status"] = self.status
        return result
