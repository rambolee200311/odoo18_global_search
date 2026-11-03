"""Standalone, Odoo-independent document operation execution package."""

from .engine import DocumentOperationEngine, ExecutionReport
from .errors import DocumentOperationError
from .schema import validate_operation_list
from .validator import validate_saved_output

__all__ = [
    "DocumentOperationEngine",
    "DocumentOperationError",
    "ExecutionReport",
    "validate_operation_list",
    "validate_saved_output",
]
