"""Pure Python parser and validator for untrusted M2 mapping proposals."""

from .contracts import (
    MAPPING_SCHEMA_VERSION,
    SUPPORTED_VALUE_TYPES,
    MappingParseError,
    ParseLimits,
    ValidationReport,
)
from .parser import parse_mapping_proposal
from .validator import apply_manual_edits, validate_proposal, validate_user_revision

__all__ = [
    "MAPPING_SCHEMA_VERSION",
    "SUPPORTED_VALUE_TYPES",
    "MappingParseError",
    "ParseLimits",
    "ValidationReport",
    "parse_mapping_proposal",
    "validate_proposal",
    "validate_user_revision",
    "apply_manual_edits",
]
