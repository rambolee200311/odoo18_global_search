"""Bounded, stateless Office document inspection and candidate rendering."""

from .errors import OfficeCoreError
from .models import DocumentInspection, Element, ResourceBudget, RenderCandidate
from .service import execute_document_operations, inspect_document, render_candidate
from .row_expansion import (
    RepeatRowsResult,
    expand_repeat_rows,
    expand_xlsx_rows,
    find_summary_row,
)

__all__ = [
    "DocumentInspection",
    "Element",
    "OfficeCoreError",
    "RenderCandidate",
    "ResourceBudget",
    "RepeatRowsResult",
    "expand_repeat_rows",
    "expand_xlsx_rows",
    "execute_document_operations",
    "find_summary_row",
    "inspect_document",
    "render_candidate",
]
