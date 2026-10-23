"""Shared, dependency-free data contracts for mapping proposal validation."""

from dataclasses import asdict, dataclass
from typing import Any

MAPPING_SCHEMA_VERSION = "m2.mapping-proposal.v1"
SUPPORTED_VALUE_TYPES = frozenset({"string", "number", "boolean"})
CLARIFICATION_REASON_CODES = frozenset(
    {"missing_source", "ambiguous_mapping", "unsupported_target", "conflicting_instruction"}
)
ROOT_KEYS = frozenset({"schema_version", "mappings", "clarifications", "skipped_targets"})
MAPPING_KEYS = frozenset({"element_id", "source_field", "value_type"})
CLARIFICATION_KEYS = frozenset({"element_id", "reason_code", "question"})


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
