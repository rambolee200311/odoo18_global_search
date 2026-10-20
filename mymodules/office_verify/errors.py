"""Stable, sanitized errors for the readback verifier."""

from __future__ import annotations


class OfficeVerifyError(Exception):
    def __init__(self, code: str, stage: str, message: str) -> None:
        self.code = code
        self.stage = stage
        self.message = message
        super().__init__(f"{code}:{stage}: {message}")

    def as_dict(self) -> dict[str, str]:
        return {"error_code": self.code, "failed_stage": self.stage, "message": self.message}
