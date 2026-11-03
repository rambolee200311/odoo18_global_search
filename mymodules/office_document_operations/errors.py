"""Stable, structured errors for the independent document operation package."""

from __future__ import annotations


class DocumentOperationError(Exception):
    def __init__(self, code: str, stage: str, message: str, operation_id: str | None = None):
        super().__init__(message)
        self.code = code
        self.stage = stage
        self.message = message
        self.operation_id = operation_id

    def as_dict(self) -> dict[str, str | None]:
        return {
            "error_code": self.code,
            "stage": self.stage,
            "message": self.message,
            "operation_id": self.operation_id,
        }
