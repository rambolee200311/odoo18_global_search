"""Ordered operation execution with atomic output promotion after verification."""

from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .errors import DocumentOperationError
from .schema import validate_operation_list
from .validator import validate_saved_output
from .xlsx_adapter import XlsxAdapter


@dataclass
class ExecutionReport:
    status: str
    stage: str
    operations: list[dict[str, Any]] = field(default_factory=list)
    error: dict[str, Any] | None = None
    output: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "stage": self.stage,
            "operations": self.operations,
            "error": self.error,
            "output": self.output,
        }


class DocumentOperationEngine:
    """Independent XLSX operation engine; no Odoo, LLM, or business imports."""

    def __init__(self, adapter: XlsxAdapter | None = None):
        self.adapter = adapter or XlsxAdapter()

    def execute(self, input_path: str | Path, output_path: str | Path, operation_list: object) -> ExecutionReport:
        """Execute in order, validate a saved candidate, then atomically publish it.

        Input files are never opened for writing. The destination is only
        replaced after the independent Validator passes on a temporary XLSX.
        """
        input_path, output_path = Path(input_path), Path(output_path)
        normalized = None
        try:
            normalized = validate_operation_list(operation_list)
            if input_path.resolve() == output_path.resolve():
                raise DocumentOperationError("input_output_collision", "preflight", "Input and output paths must be different.")
            if output_path.suffix.lower() != ".xlsx":
                raise DocumentOperationError("unsupported_file_type", "preflight", "Output path must end in .xlsx.")
            source_sha = _sha256(input_path)

            # Preflight the entire ordered sequence against an independent
            # in-memory simulation before modifying the execution Workbook.
            simulation = self.adapter.load(input_path)
            simulation_results = []
            try:
                for operation in normalized["operations"]:
                    simulation_results.append(self.adapter.apply(simulation, operation))
            finally:
                simulation.close()

            workbook = self.adapter.load(input_path)
            operation_results = []
            try:
                for operation in normalized["operations"]:
                    result = self.adapter.apply(workbook, operation)
                    operation_results.append(result)
                if _sha256(input_path) != source_sha:
                    raise DocumentOperationError("input_changed_during_execution", "execution", "Input file changed while operations were running.")

                try:
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    fd, temp_name = tempfile.mkstemp(prefix=f".{output_path.stem}.", suffix=".xlsx", dir=output_path.parent)
                    os.close(fd)
                except OSError as exc:
                    raise DocumentOperationError(
                        "output_prepare_failed", "save", "Could not prepare a temporary output file."
                    ) from exc
                candidate = Path(temp_name)
                try:
                    workbook.save(candidate)
                except Exception as exc:
                    candidate.unlink(missing_ok=True)
                    raise DocumentOperationError("xlsx_save_failed", "save", "openpyxl failed to save the candidate XLSX.") from exc
            finally:
                workbook.close()

            try:
                validation = validate_saved_output(input_path, candidate, normalized)
                # Replace only after the candidate has been independently
                # reopened and fully compared with the ordered operations.
                if _sha256(candidate) != validation["output_sha256"]:
                    raise DocumentOperationError("output_changed_after_validation", "validation", "Candidate bytes changed after validation.")
                try:
                    os.replace(candidate, output_path)
                except OSError as exc:
                    raise DocumentOperationError(
                        "output_publish_failed", "publish", "Could not atomically publish the validated output."
                    ) from exc
            except Exception:
                candidate.unlink(missing_ok=True)
                raise

            return ExecutionReport(
                status="PASS",
                stage="complete",
                operations=[{**result, "status": "verified"} for result in operation_results],
                output={
                    "path": str(output_path),
                    "size": validation["output_size"],
                    "sha256": validation["output_sha256"],
                    "validation": validation,
                },
            )
        except DocumentOperationError as exc:
            return self._failure_report(exc, normalized)
        except Exception as exc:
            error = DocumentOperationError("unexpected_engine_error", "engine", "Unexpected document operation failure.")
            return self._failure_report(error, normalized)

    @staticmethod
    def _failure_report(error: DocumentOperationError, normalized: dict[str, Any] | None) -> ExecutionReport:
        operations = []
        failed_id = error.operation_id
        if normalized:
            found_failed = False
            for operation in normalized["operations"]:
                operation_id = operation["operation_id"]
                if operation_id == failed_id:
                    operations.append({
                        "operation_id": operation_id,
                        "status": "failed",
                        "target": operation.get("target"),
                        "error_code": error.code,
                        "message": error.message,
                    })
                    found_failed = True
                elif not found_failed:
                    operations.append({"operation_id": operation_id, "status": "not_committed"})
                else:
                    operations.append({"operation_id": operation_id, "status": "not_run"})
        return ExecutionReport(
            status="FAIL",
            stage=error.stage,
            operations=operations,
            error=error.as_dict(),
            output=None,
        )


def _sha256(path: Path) -> str:
    if not path.is_file():
        raise DocumentOperationError("input_file_missing_or_empty", "preflight", "Input XLSX is missing or empty.")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
