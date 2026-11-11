"""Narrow Responses API + Code Interpreter file transport adapter.

This module deliberately has no Odoo imports and never executes returned code.
It accepts a pre-authorized SDK client and XLSX bytes, makes one Responses
request with automatic retries disabled, downloads one XLSX artifact, performs
only a bounded ZIP/OOXML container check, and returns a candidate. Semantic
verification and business acceptance belong to higher layers.
"""

from __future__ import annotations

import base64
import hashlib
import re
import time
import zipfile
import zlib
from dataclasses import dataclass, field
from io import BytesIO
from typing import Any, Literal

from openai import APIConnectionError, APIStatusError, APITimeoutError


OperationStatus = Literal["candidate_received", "blocked", "failed", "indeterminate"]
_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_REQUIRED_XLSX_PARTS = frozenset(
    {"[Content_Types].xml", "xl/workbook.xml", "xl/_rels/workbook.xml.rels"}
)
_VALID_MEMORY_LIMITS = frozenset({"1g", "4g", "16g", "64g"})
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


@dataclass(frozen=True)
class AdapterLimits:
    """Per-call resource policy supplied by a trusted caller.

    ``allowed_models`` is policy input, not a business-model allowlist. The
    adapter does not select or substitute a model. ``remote_cleanup_required``
    is rejected before upload because this component cannot guarantee remote
    deletion; it can only make a best-effort cleanup call after receiving a
    container identifier.
    """

    allowed_models: frozenset[str]
    max_input_bytes: int
    max_output_bytes: int
    max_output_tokens: int
    timeout_seconds: float
    memory_limit: str = "1g"
    max_archive_entries: int = 10_000
    max_uncompressed_bytes: int = 100_000_000
    remote_cleanup_required: bool = False


@dataclass(frozen=True)
class AdapterError:
    category: str
    retryable: bool = False
    retry_decision: str = "not_automatic"
    http_status: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "retryable": self.retryable,
            "retry_decision": self.retry_decision,
            "http_status": self.http_status,
        }


@dataclass(frozen=True)
class AdapterResult:
    """In-process result; ``to_dict`` intentionally omits file bytes."""

    operation_status: OperationStatus
    candidate_bytes: bytes | None = field(default=None, repr=False, compare=False)
    input_sha256: str | None = None
    candidate_sha256: str | None = None
    provider_response_id: str | None = None
    request_id: str | None = None
    download_request_id: str | None = None
    tool_call_ids: tuple[str, ...] = ()
    container_id: str | None = None
    provider_file_ids: tuple[str, ...] = ()
    provider_filename: str | None = None
    usage: dict[str, int | None] = field(default_factory=dict)
    duration_ms: int = 0
    cleanup_state: Literal["not_required", "completed", "cleanup_pending", "unknown"] = "not_required"
    error: AdapterError | None = None
    correlation_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return safe, JSON-serializable metadata without workbook contents."""
        return {
            "operation_status": self.operation_status,
            "candidate_present": self.candidate_bytes is not None,
            "input_sha256": self.input_sha256,
            "candidate_sha256": self.candidate_sha256,
            "provider_response_id": self.provider_response_id,
            "request_id": self.request_id,
            "download_request_id": self.download_request_id,
            "tool_call_ids": list(self.tool_call_ids),
            "container_id": self.container_id,
            "provider_file_ids": list(self.provider_file_ids),
            "provider_filename": self.provider_filename,
            "usage": dict(self.usage),
            "duration_ms": self.duration_ms,
            "cleanup_state": self.cleanup_state,
            "error": self.error.to_dict() if self.error else None,
            "correlation_id": self.correlation_id,
        }


@dataclass(frozen=True)
class _XlsxCheck:
    valid: bool
    reason: str | None = None


class _AdapterFailure(Exception):
    """Safe adapter failure category; never carries remote content."""

    def __init__(self, category: str) -> None:
        self.category = category
        super().__init__(category)


class ResponsesAdapter:
    """One-request Responses adapter for an already configured SDK client."""

    def execute(
        self,
        *,
        provider_client: Any,
        model: str,
        input_xlsx: bytes | None,
        instruction: str,
        limits: AdapterLimits,
        operation: str = "edit",
        input_sha256: str | None = None,
        correlation_id: str | None = None,
    ) -> AdapterResult:
        started = time.monotonic()
        input_digest = hashlib.sha256(input_xlsx).hexdigest() if isinstance(input_xlsx, bytes) else None

        blocked_reason = self._preflight(
            provider_client=provider_client,
            model=model,
            input_xlsx=input_xlsx,
            instruction=instruction,
            limits=limits,
            operation=operation,
            input_digest=input_digest,
            claimed_digest=input_sha256,
            correlation_id=correlation_id,
        )
        if blocked_reason:
            return self._result(
                "blocked",
                started,
                input_sha256=input_digest,
                correlation_id=correlation_id,
                error=AdapterError(blocked_reason),
            )

        active_client: Any | None = None
        container_id: str | None = None
        response_id: str | None = None
        request_id: str | None = None
        download_request_id: str | None = None
        tool_call_ids: list[str] = []
        file_id: str | None = None
        provider_filename: str | None = None
        usage: dict[str, int | None] = {}
        result: AdapterResult | None = None
        request_started = False
        response_received = False

        try:
            active_client = provider_client.with_options(
                timeout=limits.timeout_seconds,
                max_retries=0,
            )
            content = []
            if input_xlsx is not None:
                file_data = "data:" + _XLSX_MIME + ";base64," + base64.b64encode(input_xlsx).decode("ascii")
                content.append({"type": "input_file", "filename": "input.xlsx", "file_data": file_data})
            content.append({"type": "input_text", "text": instruction})
            request_started = True
            response = active_client.responses.create(
                model=model,
                input=[
                    {
                        "role": "user",
                        "content": content,
                    }
                ],
                tools=[
                    {
                        "type": "code_interpreter",
                        "container": {
                            "type": "auto",
                            "memory_limit": limits.memory_limit,
                            "network_policy": {"type": "disabled"},
                        },
                    }
                ],
                tool_choice="required",
                max_output_tokens=limits.max_output_tokens,
                store=False,
            )
            response_received = True
            response_id = _nonempty_string(_get(response, "id"))
            request_id = _nonempty_string(_get(response, "_request_id"))
            usage = _normalize_usage(_get(response, "usage"))
            file_refs, tool_call_ids, container_id = _collect_output_refs(_get(response, "output", []))

            if _get(response, "status") != "completed":
                result = self._result(
                    "failed", started, input_sha256=input_digest,
                    correlation_id=correlation_id, provider_response_id=response_id,
                    request_id=request_id, tool_call_ids=tuple(tool_call_ids),
                    container_id=container_id, provider_file_ids=tuple(item[0] for item in file_refs),
                    usage=usage, error=AdapterError("provider_response_incomplete"),
                )
            elif len(file_refs) != 1:
                result = self._result(
                    "failed", started, input_sha256=input_digest,
                    correlation_id=correlation_id, provider_response_id=response_id,
                    request_id=request_id, tool_call_ids=tuple(tool_call_ids),
                    container_id=container_id, provider_file_ids=tuple(item[0] for item in file_refs),
                    usage=usage, error=AdapterError("xlsx_output_missing_or_ambiguous"),
                )
            elif not container_id:
                result = self._result(
                    "failed", started, input_sha256=input_digest,
                    correlation_id=correlation_id, provider_response_id=response_id,
                    tool_call_ids=tuple(tool_call_ids),
                    provider_file_ids=(file_refs[0][0],), usage=usage,
                    error=AdapterError("output_container_missing"),
                )
            else:
                file_id, provider_filename = file_refs[0]
                candidate_bytes, download_request_id = self._download_candidate(
                    active_client,
                    container_id=container_id,
                    file_id=file_id,
                    timeout_seconds=limits.timeout_seconds,
                    max_bytes=limits.max_output_bytes,
                )
                check = _check_xlsx(candidate_bytes, limits, max_bytes=limits.max_output_bytes)
                if not check.valid:
                    result = self._result(
                        "failed", started, input_sha256=input_digest,
                        correlation_id=correlation_id, provider_response_id=response_id,
                        request_id=request_id, tool_call_ids=tuple(tool_call_ids),
                    download_request_id=download_request_id,
                        container_id=container_id, provider_file_ids=(file_id,),
                        provider_filename=provider_filename, usage=usage,
                        error=AdapterError(check.reason or "invalid_xlsx_candidate"),
                    )
                else:
                    result = self._result(
                        "candidate_received", started, input_sha256=input_digest,
                        correlation_id=correlation_id, provider_response_id=response_id,
                        request_id=request_id, tool_call_ids=tuple(tool_call_ids),
                    download_request_id=download_request_id,
                        container_id=container_id, provider_file_ids=(file_id,),
                        provider_filename=provider_filename, usage=usage,
                        candidate_bytes=candidate_bytes,
                        candidate_sha256=hashlib.sha256(candidate_bytes).hexdigest(),
                    )
        except (APIConnectionError, APITimeoutError):
            if response_received:
                result = self._result(
                    "failed", started, input_sha256=input_digest,
                    correlation_id=correlation_id,
                    provider_response_id=response_id,
                    request_id=request_id,
                    download_request_id=download_request_id,
                    tool_call_ids=tuple(tool_call_ids),
                    container_id=container_id,
                    provider_file_ids=(file_id,) if file_id else (),
                    provider_filename=provider_filename,
                    usage=usage,
                    error=AdapterError("provider_file_download_error"),
                )
            else:
                result = self._result(
                    "indeterminate", started, input_sha256=input_digest,
                    correlation_id=correlation_id,
                    error=AdapterError("provider_connection_or_timeout"),
                )
        except APIStatusError as exc:
            result = self._result(
                "failed", started, input_sha256=input_digest,
                correlation_id=correlation_id,
                provider_response_id=response_id,
                request_id=_nonempty_string(_get(exc, "request_id")) or request_id,
                download_request_id=(
                    _nonempty_string(_get(exc, "request_id")) if response_received else None
                ) or download_request_id,
                tool_call_ids=tuple(tool_call_ids),
                container_id=container_id,
                provider_file_ids=(file_id,) if file_id else (),
                provider_filename=provider_filename,
                usage=usage,
                error=AdapterError(
                    "provider_file_download_http_error" if response_received else "provider_http_error",
                    http_status=_positive_int(_get(exc, "status_code")),
                ),
            )
        except _AdapterFailure as exc:
            result = self._result(
                "failed", started, input_sha256=input_digest,
                correlation_id=correlation_id,
                provider_response_id=response_id,
                request_id=request_id,
                download_request_id=download_request_id,
                tool_call_ids=tuple(tool_call_ids),
                container_id=container_id,
                provider_file_ids=(file_id,) if file_id else (),
                provider_filename=provider_filename,
                usage=usage,
                error=AdapterError(exc.category),
            )
        except Exception:
            # Do not put SDK exception text, response bodies, prompts, or file
            # data into the result. Detailed diagnostics belong in protected logs.
            result = self._result(
                "failed", started, input_sha256=input_digest,
                correlation_id=correlation_id,
                provider_response_id=response_id,
                request_id=request_id,
                download_request_id=download_request_id,
                tool_call_ids=tuple(tool_call_ids),
                container_id=container_id,
                provider_file_ids=(file_id,) if file_id else (),
                provider_filename=provider_filename,
                usage=usage,
                error=AdapterError("adapter_request_or_download_error"),
            )
        finally:
            cleanup_state: Literal["not_required", "completed", "cleanup_pending", "unknown"] = "not_required"
            if container_id:
                try:
                    assert active_client is not None
                    active_client.containers.delete(container_id, timeout=limits.timeout_seconds)
                    cleanup_state = "completed"
                except Exception:
                    cleanup_state = "cleanup_pending"
            elif request_started:
                cleanup_state = "unknown"
            if result is not None:
                result = self._replace_cleanup_state(result, cleanup_state, started)

        assert result is not None
        return result

    @staticmethod
    def _preflight(
        *, provider_client: Any, model: str, input_xlsx: Any, instruction: Any,
        limits: AdapterLimits, operation: Any, input_digest: str | None, claimed_digest: str | None,
        correlation_id: str | None,
    ) -> str | None:
        if provider_client is None or not callable(getattr(provider_client, "with_options", None)):
            return "provider_client_invalid"
        if not isinstance(limits, AdapterLimits):
            return "resource_policy_invalid"
        if (
            not isinstance(limits.allowed_models, (set, frozenset))
            or not limits.allowed_models
            or any(not isinstance(allowed, str) or not allowed for allowed in limits.allowed_models)
            or not isinstance(model, str)
            or model not in limits.allowed_models
        ):
            return "model_not_approved"
        if operation not in {"edit", "create"}:
            return "operation_invalid"
        if operation == "edit" and (not isinstance(input_xlsx, bytes) or not input_xlsx):
            return "input_xlsx_invalid"
        if operation == "create" and (input_xlsx is not None or claimed_digest is not None):
            return "creation_must_not_claim_source_file"
        if not isinstance(instruction, str) or not instruction.strip():
            return "instruction_invalid"
        if correlation_id is not None and (
            not isinstance(correlation_id, str) or len(correlation_id) > 128
        ):
            return "correlation_id_invalid"
        numeric_limits = (
            limits.max_input_bytes,
            limits.max_output_bytes,
            limits.max_output_tokens,
            limits.max_archive_entries,
            limits.max_uncompressed_bytes,
        )
        if any(not isinstance(value, int) or isinstance(value, bool) or value <= 0 for value in numeric_limits):
            return "resource_policy_invalid"
        if (
            isinstance(limits.timeout_seconds, bool)
            or not isinstance(limits.timeout_seconds, (int, float))
            or limits.timeout_seconds <= 0
        ):
            return "resource_policy_invalid"
        if not isinstance(limits.memory_limit, str) or limits.memory_limit not in _VALID_MEMORY_LIMITS:
            return "resource_policy_invalid"
        if limits.remote_cleanup_required:
            return "remote_cleanup_guarantee_unsupported"
        if input_xlsx is not None and len(input_xlsx) > limits.max_input_bytes:
            return "input_size_limit_exceeded"
        if claimed_digest is not None:
            if not isinstance(claimed_digest, str) or not _SHA256_RE.fullmatch(claimed_digest):
                return "input_sha256_invalid"
            if input_digest is None or claimed_digest.lower() != input_digest:
                return "input_sha256_mismatch"
        if input_xlsx is not None:
            check = _check_xlsx(input_xlsx, limits, max_bytes=limits.max_input_bytes)
            if not check.valid:
                return check.reason or "input_xlsx_invalid"
        return None

    @staticmethod
    def _download_candidate(
        client: Any, *, container_id: str, file_id: str,
        timeout_seconds: float, max_bytes: int,
    ) -> tuple[bytes, str | None]:
        content = client.containers.files.content
        streaming = getattr(content, "with_streaming_response", None)
        retrieve = getattr(streaming, "retrieve", None)
        if not callable(retrieve):
            raise _AdapterFailure("streamed_file_download_unavailable")
        response_manager = retrieve(
            file_id,
            container_id=container_id,
            timeout=timeout_seconds,
        )
        chunks: list[bytes] = []
        total = 0
        download_request_id: str | None = None
        with response_manager as response:
            download_request_id = _nonempty_string(_get(response, "request_id"))
            for chunk in response.iter_bytes(chunk_size=64 * 1024):
                if not isinstance(chunk, bytes):
                    raise _AdapterFailure("download_chunk_invalid")
                total += len(chunk)
                if total > max_bytes:
                    raise _AdapterFailure("output_size_limit_exceeded")
                chunks.append(chunk)
        return b"".join(chunks), download_request_id

    @staticmethod
    def _result(
        status: OperationStatus,
        started: float,
        *,
        candidate_bytes: bytes | None = None,
        input_sha256: str | None = None,
        candidate_sha256: str | None = None,
        provider_response_id: str | None = None,
        request_id: str | None = None,
        download_request_id: str | None = None,
        tool_call_ids: tuple[str, ...] = (),
        container_id: str | None = None,
        provider_file_ids: tuple[str, ...] = (),
        provider_filename: str | None = None,
        usage: dict[str, int | None] | None = None,
        cleanup_state: Literal["not_required", "completed", "cleanup_pending", "unknown"] = "not_required",
        error: AdapterError | None = None,
        correlation_id: str | None = None,
    ) -> AdapterResult:
        return AdapterResult(
            operation_status=status,
            candidate_bytes=candidate_bytes,
            input_sha256=input_sha256,
            candidate_sha256=candidate_sha256,
            provider_response_id=provider_response_id,
            request_id=request_id,
            download_request_id=download_request_id,
            tool_call_ids=tool_call_ids,
            container_id=container_id,
            provider_file_ids=provider_file_ids,
            provider_filename=provider_filename,
            usage=usage or _unknown_usage(),
            duration_ms=max(0, int((time.monotonic() - started) * 1000)),
            cleanup_state=cleanup_state,
            error=error,
            correlation_id=correlation_id,
        )

    @classmethod
    def _replace_cleanup_state(
        cls,
        result: AdapterResult,
        cleanup_state: Literal["not_required", "completed", "cleanup_pending", "unknown"],
        started: float,
    ) -> AdapterResult:
        return cls._result(
            result.operation_status,
            started,
            candidate_bytes=result.candidate_bytes,
            input_sha256=result.input_sha256,
            candidate_sha256=result.candidate_sha256,
            provider_response_id=result.provider_response_id,
            request_id=result.request_id,
            download_request_id=result.download_request_id,
            tool_call_ids=result.tool_call_ids,
            container_id=result.container_id,
            provider_file_ids=result.provider_file_ids,
            provider_filename=result.provider_filename,
            usage=result.usage,
            cleanup_state=cleanup_state,
            error=result.error,
            correlation_id=result.correlation_id,
        )


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)


def _nonempty_string(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _safe_filename(value: Any) -> str | None:
    filename = _nonempty_string(value)
    if filename is None:
        return None
    basename = filename.replace("\\", "/").rsplit("/", 1)[-1]
    if not basename or len(basename) > 255 or "\x00" in basename:
        return None
    return basename


def _positive_int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else None


def _normalize_usage(raw_usage: Any) -> dict[str, int | None]:
    details = _get(raw_usage, "output_tokens_details") if raw_usage else None
    names = ("input_tokens", "output_tokens", "total_tokens")
    normalized = {
        name: _positive_or_zero_int(_get(raw_usage, name)) if raw_usage else None
        for name in names
    }
    normalized["reasoning_tokens"] = (
        _positive_or_zero_int(_get(details, "reasoning_tokens")) if details else None
    )
    return normalized


def _positive_or_zero_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _unknown_usage() -> dict[str, int | None]:
    return {
        "input_tokens": None,
        "output_tokens": None,
        "total_tokens": None,
        "reasoning_tokens": None,
    }


def _collect_output_refs(output: Any) -> tuple[list[tuple[str, str | None]], list[str], str | None]:
    file_refs: list[tuple[str, str | None]] = []
    tool_call_ids: list[str] = []
    container_ids: set[str] = set()
    if not isinstance(output, (list, tuple)):
        return file_refs, tool_call_ids, None
    for item in output:
        item_type = _get(item, "type")
        if item_type == "code_interpreter_call":
            item_container = _nonempty_string(_get(item, "container_id"))
            if item_container:
                container_ids.add(item_container)
            call_id = _nonempty_string(_get(item, "id"))
            if call_id:
                tool_call_ids.append(call_id)
        if item_type != "message":
            continue
        contents = _get(item, "content", [])
        if not isinstance(contents, (list, tuple)):
            continue
        for content_item in contents:
            annotations = _get(content_item, "annotations", [])
            if not isinstance(annotations, (list, tuple)):
                continue
            for annotation in annotations:
                if _get(annotation, "type") != "container_file_citation":
                    continue
                filename = _safe_filename(_get(annotation, "filename"))
                file_id = _nonempty_string(_get(annotation, "file_id"))
                candidate_container = _nonempty_string(_get(annotation, "container_id"))
                if candidate_container:
                    container_ids.add(candidate_container)
                if filename and filename.lower().endswith(".xlsx") and file_id:
                    file_refs.append((file_id, filename))
    # A Response normally shares one auto-created container. If the Provider
    # surfaces conflicting container identities, refuse to guess which one
    # owns the cited file.
    container_id = next(iter(container_ids)) if len(container_ids) == 1 else None
    return file_refs, tool_call_ids, container_id


def _check_xlsx(data: bytes, limits: AdapterLimits, *, max_bytes: int) -> _XlsxCheck:
    if not isinstance(data, bytes) or not data:
        return _XlsxCheck(False, "xlsx_empty")
    if len(data) > max_bytes:
        return _XlsxCheck(False, "xlsx_size_limit_exceeded")
    try:
        with zipfile.ZipFile(BytesIO(data), "r") as archive:
            infos = archive.infolist()
            if not infos or len(infos) > limits.max_archive_entries:
                return _XlsxCheck(False, "xlsx_archive_entry_limit_or_empty")
            names = {info.filename for info in infos}
            if not _REQUIRED_XLSX_PARTS.issubset(names) or any(
                sum(info.filename == required for info in infos) != 1
                for required in _REQUIRED_XLSX_PARTS
            ):
                return _XlsxCheck(False, "xlsx_required_parts_missing")
            expanded_size = sum(info.file_size for info in infos)
            if expanded_size > limits.max_uncompressed_bytes:
                return _XlsxCheck(False, "xlsx_expanded_size_limit_exceeded")
            if archive.testzip() is not None:
                return _XlsxCheck(False, "xlsx_crc_invalid")
    except (OSError, ValueError, zlib.error, zipfile.BadZipFile, zipfile.LargeZipFile):
        return _XlsxCheck(False, "xlsx_container_invalid")
    return _XlsxCheck(True)
