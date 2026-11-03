"""Ordered operation execution with atomic output promotion after verification."""

from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

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

    def execute(
        self,
        input_path: str | Path,
        output_path: str | Path,
        operation_list: object,
        *,
        repeat_rows_handler: Callable | None = None,
        candidate_postprocessor: Callable | None = None,
        max_output_bytes: int = 64 * 1024 * 1024,
    ) -> ExecutionReport:
        """Execute in order, validate a saved candidate, then atomically publish it.

        Input files are never opened for writing. The destination is only
        replaced after the independent Validator passes on a temporary XLSX.
        """
        input_path, output_path = Path(input_path), Path(output_path)
        normalized = None
        temporary_input = None
        candidate = None
        try:
            normalized = validate_operation_list(operation_list)
            if input_path.resolve() == output_path.resolve():
                raise DocumentOperationError("input_output_collision", "preflight", "Input and output paths must be different.")
            if output_path.suffix.lower() != ".xlsx":
                raise DocumentOperationError("unsupported_file_type", "preflight", "Output path must end in .xlsx.")
            source_sha = _sha256(input_path)
            if normalized["schema_version"] == "1.1" and source_sha != normalized["source_sha256"]:
                raise DocumentOperationError(
                    "source_fingerprint_mismatch", "preflight", "Operation List does not match the input file fingerprint."
                )

            operations = normalized["operations"]
            execution_input = input_path
            repeat_result = None
            if operations and operations[0]["type"] == "repeat_rows":
                if repeat_rows_handler is None:
                    raise DocumentOperationError(
                        "repeat_rows_handler_unavailable", "preflight", "No verified repeat-row adapter is configured.", operations[0]["operation_id"]
                    )
                try:
                    expanded = repeat_rows_handler(input_path.read_bytes(), operations[0])
                    if isinstance(expanded, tuple):
                        expanded_bytes, repeat_result = expanded
                    else:
                        expanded_bytes, repeat_result = expanded, None
                    if not isinstance(expanded_bytes, bytes) or not expanded_bytes:
                        raise ValueError("repeat-row adapter returned no bytes")
                    repeated = repeat_rows_handler(input_path.read_bytes(), operations[0])
                    repeated_bytes = repeated[0] if isinstance(repeated, tuple) else repeated
                    if not isinstance(repeated_bytes, bytes) or hashlib.sha256(repeated_bytes).digest() != hashlib.sha256(expanded_bytes).digest():
                        raise DocumentOperationError(
                            "repeat_rows_replay_mismatch", "validation", "repeat_rows could not be reproduced from the original input.", operations[0]["operation_id"]
                        )
                except DocumentOperationError:
                    raise
                except Exception as exc:
                    raise DocumentOperationError(
                        "repeat_rows_failed", "preflight", "The repeat-row operation failed.", operations[0]["operation_id"]
                    ) from exc
                if len(expanded_bytes) > max_output_bytes:
                    raise DocumentOperationError(
                        "repeat_rows_resource_limit", "preflight", "Expanded XLSX exceeds the operation engine limit.", operations[0]["operation_id"]
                    )
                temporary_input = tempfile.TemporaryDirectory(prefix="office-repeat-source-")
                execution_input = Path(temporary_input.name) / "expanded.xlsx"
                execution_input.write_bytes(expanded_bytes)
                operations = operations[1:]
                if not operations:
                    raise DocumentOperationError(
                        "repeat_rows_without_file_operation", "preflight", "repeat_rows must be followed by at least one file operation.", normalized["operations"][0]["operation_id"]
                    )

            validation_list = {
                "schema_version": "1.1",
                "source_sha256": _sha256(execution_input),
                "operations": operations,
            }

            # Preflight the entire ordered sequence against an independent
            # in-memory simulation before modifying the execution Workbook.
            simulation = self.adapter.load(execution_input)
            try:
                for operation in operations:
                    self.adapter.apply(simulation, operation)
            finally:
                simulation.close()

            workbook = self.adapter.load(execution_input)
            operation_results = []
            try:
                for operation in operations:
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
                if candidate_postprocessor is not None:
                    try:
                        processed = candidate_postprocessor(execution_input.read_bytes(), candidate.read_bytes(), operations)
                    except DocumentOperationError:
                        raise
                    except Exception as exc:
                        raise DocumentOperationError(
                            "candidate_postprocess_failed", "serialize", "The candidate compatibility transform failed."
                        ) from exc
                    if not isinstance(processed, bytes) or not processed:
                        raise DocumentOperationError("candidate_postprocess_failed", "serialize", "The candidate compatibility transform returned no bytes.")
                    if len(processed) > max_output_bytes:
                        raise DocumentOperationError("candidate_resource_limit", "serialize", "Processed candidate exceeds the operation engine limit.")
                    candidate.write_bytes(processed)

                validation = validate_saved_output(execution_input, candidate, validation_list)
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

            if normalized["operations"] and normalized["operations"][0]["type"] == "repeat_rows":
                operation_results.insert(0, {
                    "operation_id": normalized["operations"][0]["operation_id"],
                    "status": "verified",
                    "target": normalized["operations"][0]["target"],
                    "result": repeat_result if isinstance(repeat_result, dict) else {"applied": True},
                })

            return ExecutionReport(
                status="PASS",
                stage="complete",
                operations=[{**result, "status": "verified"} for result in operation_results],
                output={
                    "path": str(output_path),
                    "size": validation["output_size"],
                    "sha256": validation["output_sha256"],
                    "validation": {**validation, "operation_count": len(normalized["operations"])},
                },
            )
        except DocumentOperationError as exc:
            return self._failure_report(exc, normalized)
        except Exception as exc:
            error = DocumentOperationError("unexpected_engine_error", "engine", "Unexpected document operation failure.")
            return self._failure_report(error, normalized)
        finally:
            if candidate is not None:
                candidate.unlink(missing_ok=True)
            if temporary_input is not None:
                temporary_input.cleanup()

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
