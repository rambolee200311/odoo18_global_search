"""Stable, sanitized errors exposed by the Office core."""

from __future__ import annotations


class OfficeCoreError(Exception):
    """A public error with a stable code and no parser/path details."""

    def __init__(self, code: str, stage: str, message: str):
        super().__init__(message)
        self.code = code
        self.stage = stage
        self.message = message

    def as_dict(self) -> dict[str, str]:
        return {"error_code": self.code, "failed_stage": self.stage, "message": self.message}
