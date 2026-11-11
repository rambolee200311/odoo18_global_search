"""Public data contracts for independent Office readback."""

from __future__ import annotations

import math
from dataclasses import dataclass


def _candidate_json_value(value):
    """Make nested OOXML structural evidence JSON-compatible for receipts."""
    if isinstance(value, bytes):
        # Structural byte values are canonical UTF-8 OOXML fragments.
        return value.decode("utf-8", errors="replace")
    if isinstance(value, dict):
        return {key: _candidate_json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_candidate_json_value(item) for item in value]
    return value


@dataclass(frozen=True)
class VerificationBudget:
    max_file_size: int = 32 * 1024 * 1024
    max_expanded_size: int = 100 * 1024 * 1024
    max_zip_entries: int = 512
    max_entry_size: int = 20 * 1024 * 1024
    max_xml_elements: int = 1_000_000
    max_cells: int = 500_000
    max_paragraphs: int = 100_000
    max_mapping_bytes: int = 1 * 1024 * 1024
    max_memory_bytes: int = 4 * 1024 * 1024 * 1024
    timeout_seconds: float = 15.0

    def validate(self) -> None:
        for name in (
            "max_file_size", "max_expanded_size", "max_zip_entries", "max_entry_size",
            "max_xml_elements", "max_cells", "max_paragraphs", "max_mapping_bytes",
            "max_memory_bytes",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if isinstance(self.timeout_seconds, bool) or not isinstance(self.timeout_seconds, (int, float)):
            raise ValueError("timeout_seconds must be positive")
        try:
            finite = math.isfinite(float(self.timeout_seconds))
        except (OverflowError, ValueError):
            finite = False
        if not finite or self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")


@dataclass(frozen=True)
class VerificationPolicy:
    """Capability policy. Required parts are package-relative OOXML names."""

    enabled_formats: tuple[str, ...] = ("xlsx", "docx")
    require_styles: bool = False
    required_parts: tuple[str, ...] = ()
    require_relationships: bool = True

    def validate(self) -> None:
        if not isinstance(self.enabled_formats, tuple) or any(x not in {"xlsx", "docx"} for x in self.enabled_formats):
            raise ValueError("enabled_formats only accepts xlsx/docx")
        if not isinstance(self.require_styles, bool) or not isinstance(self.require_relationships, bool):
            raise ValueError("policy flags must be boolean")
        if not isinstance(self.required_parts, tuple) or any(not isinstance(x, str) for x in self.required_parts):
            raise ValueError("required_parts must be a tuple of strings")


@dataclass(frozen=True)
class VerificationReport:
    status: str
    format: str
    input_sha256: str
    output_sha256: str
    checked_targets: int
    checked_formulas: int
    cached_value_changed: bool
    formula_cache_status: tuple[dict[str, object], ...]
    warnings: tuple[dict[str, str], ...]
    summary: str = "完整性回读检查通过；此结果不代表附件已获准交付。"

    def as_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "format": self.format,
            "input_sha256": self.input_sha256,
            "output_sha256": self.output_sha256,
            "checked_targets": self.checked_targets,
            "checked_formulas": self.checked_formulas,
            "cached_value_changed": self.cached_value_changed,
            "formula_cache_status": [dict(item) for item in self.formula_cache_status],
            "warnings": [dict(item) for item in self.warnings],
            "summary": self.summary,
        }


@dataclass(frozen=True)
class CandidateValidationReport:
    """Read-only facts comparing one XLSX candidate with its bound parent."""

    validation_result: str
    input_sha256: str | None
    output_sha256: str
    actual_effects: tuple[dict[str, object], ...]
    risk_facts: tuple[dict[str, object], ...]
    feature_results: tuple[dict[str, object], ...]
    unknowns: tuple[str, ...] = ()
    error: dict[str, str] | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "validation_result": self.validation_result,
            "input_sha256": self.input_sha256,
            "output_sha256": self.output_sha256,
            "actual_effects": [_candidate_json_value(item) for item in self.actual_effects],
            "risk_facts": [_candidate_json_value(item) for item in self.risk_facts],
            "feature_results": [_candidate_json_value(item) for item in self.feature_results],
            "unknowns": list(self.unknowns),
            "error": dict(self.error) if self.error else None,
        }
