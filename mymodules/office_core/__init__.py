"""Bounded, stateless Office document inspection and candidate rendering."""

from .errors import OfficeCoreError
from .models import DocumentInspection, Element, ResourceBudget, RenderCandidate
from .service import inspect_document, render_candidate

__all__ = [
    "DocumentInspection",
    "Element",
    "OfficeCoreError",
    "RenderCandidate",
    "ResourceBudget",
    "inspect_document",
    "render_candidate",
]
