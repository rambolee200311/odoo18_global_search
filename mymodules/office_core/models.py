"""Small immutable data contracts for office_core."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class ResourceBudget:
    max_file_size: int
    max_expanded_size: int
    max_zip_entries: int
    max_entry_size: int
    max_xml_elements: int
    max_cells: int
    max_paragraphs: int
    max_memory_bytes: int
    timeout_seconds: float

    def validate(self) -> None:
        for name in (
            "max_file_size",
            "max_expanded_size",
            "max_zip_entries",
            "max_entry_size",
            "max_xml_elements",
            "max_cells",
            "max_paragraphs",
            "max_memory_bytes",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if isinstance(self.timeout_seconds, bool) or not isinstance(self.timeout_seconds, (int, float)):
            raise ValueError("timeout_seconds must be a positive number")
        try:
            timeout_is_finite = math.isfinite(float(self.timeout_seconds))
        except (OverflowError, ValueError):
            timeout_is_finite = False
        if not timeout_is_finite or self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be a positive number")


@dataclass(frozen=True)
class Element:
    element_id: str
    kind: str
    value: object
    writable: bool
    order: int


@dataclass(frozen=True)
class DocumentInspection:
    format: str
    template_sha256: str
    elements: tuple[Element, ...]
    unknown_structures: tuple[str, ...]
    warnings: tuple[str, ...]
    capability: str

    def as_dict(self) -> dict[str, object]:
        return {
            "format": self.format,
            "template_sha256": self.template_sha256,
            "elements": [
                {
                    "element_id": item.element_id,
                    "kind": item.kind,
                    "value": item.value,
                    "writable": item.writable,
                    "order": item.order,
                }
                for item in self.elements
            ],
            "unknown_structures": list(self.unknown_structures),
            "warnings": list(self.warnings),
            "capability": self.capability,
        }


@dataclass(frozen=True)
class RenderCandidate:
    format: str
    template_sha256: str
    candidate_sha256: str
    content: bytes
    applied_writes: int
    warnings: tuple[str, ...]
    delivery_status: str = "candidate_only_not_verified_or_deliverable"

    def as_summary(self) -> dict[str, object]:
        return {
            "format": self.format,
            "template_sha256": self.template_sha256,
            "candidate_sha256": self.candidate_sha256,
            "applied_writes": self.applied_writes,
            "warnings": list(self.warnings),
            "delivery_status": self.delivery_status,
        }
