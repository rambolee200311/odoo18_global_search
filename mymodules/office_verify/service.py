"""Public synchronous API with bounded, killable process isolation."""

from __future__ import annotations

import multiprocessing
import os
import sys
import time
from typing import Any

from .errors import OfficeVerifyError
from .models import CandidateValidationReport, VerificationBudget, VerificationPolicy, VerificationReport


def _validate_worker_budget(memory_bytes: int, timeout_seconds: float) -> None:
    # Memory is enforced by the parent sampling the child's resident set. On
    # macOS, Python reserves a very large virtual address range, so RLIMIT_AS
    # would reject ordinary workers before parsing begins. The child is still
    # killable and its actual resident memory is bounded by the caller budget.
    if memory_bytes <= 0 or timeout_seconds <= 0:
        raise OfficeVerifyError("OFFICE_RESOURCE_LIMIT", "worker_limits", "当前环境无法落实所声明的进程资源限制。")


def _process_rss_bytes(pid: int) -> int | None:
    if sys.platform == "darwin":
        try:
            import ctypes

            libproc = ctypes.CDLL("/usr/lib/libproc.dylib")
            proc_pidinfo = libproc.proc_pidinfo
            proc_pidinfo.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint64, ctypes.c_void_p, ctypes.c_int]
            proc_pidinfo.restype = ctypes.c_int
            buffer = ctypes.create_string_buffer(256)
            # PROC_PIDTASKINFO (4); resident_size is the second uint64 field.
            returned = proc_pidinfo(pid, 4, 0, buffer, len(buffer))
            if returned < 16:
                return None
            return int.from_bytes(buffer.raw[8:16], byteorder=sys.byteorder, signed=False)
        except (AttributeError, OSError, ValueError):
            return None
    if sys.platform.startswith("linux"):
        try:
            with open(f"/proc/{pid}/status", "r", encoding="ascii") as stream:
                for line in stream:
                    if line.startswith("VmRSS:"):
                        return int(line.split()[1]) * 1024
        except (OSError, ValueError, IndexError):
            return None
    return None


def _worker(send_conn, args: tuple[Any, ...]) -> None:
    try:
        mode, payload = args
        if mode == "mapping":
            source, candidate, filename, mime_type, mapping, policy, budget, authorized_blank_targets = payload
        elif mode == "candidate":
            source, candidate, filename, mime_type, policy, budget = payload
        elif mode == "created":
            source, candidate, filename, mime_type, policy, budget = payload
        else:
            raise ValueError("unsupported verification mode")
        _validate_worker_budget(budget.max_memory_bytes, budget.timeout_seconds)
        if mode == "mapping":
            from .verify import verify_inline

            report = verify_inline(
                source,
                candidate,
                filename,
                mime_type,
                mapping,
                policy,
                budget,
                authorized_blank_targets=authorized_blank_targets,
            )
        elif mode == "candidate":
            from .verify import verify_candidate_inline

            report = verify_candidate_inline(source, candidate, filename, mime_type, policy, budget)
        elif mode == "created":
            from .verify import verify_created_inline

            report = verify_created_inline(candidate, filename, mime_type, policy, budget)
        else:
            raise ValueError("unsupported verification mode")
        send_conn.send(("ok", report))
    except OfficeVerifyError as exc:
        try:
            send_conn.send(("office_error", exc.as_dict()))
        except (BrokenPipeError, EOFError, OSError):
            pass
    except BaseException:
        try:
            send_conn.send(("engine_error", None))
        except (BrokenPipeError, EOFError, OSError):
            pass
    finally:
        send_conn.close()


def _stop(process) -> None:
    if process.pid is None:
        return
    if process.is_alive():
        process.terminate()
        process.join(timeout=0.5)
    if process.is_alive() and hasattr(process, "kill"):
        process.kill()
        process.join(timeout=0.5)


def _run_worker(mode: str, payload: tuple[Any, ...], budget: VerificationBudget, *, capture_metrics: bool = False):
    context = multiprocessing.get_context("spawn")
    recv_conn, send_conn = context.Pipe(duplex=False)
    process = context.Process(target=_worker, args=(send_conn, (mode, payload)), daemon=True)
    started = time.monotonic()
    max_observed_rss_bytes: int | None = None

    def execution_metrics() -> dict[str, int | float | bool | None]:
        return {
            "elapsed_seconds": max(0.0, time.monotonic() - started),
            "rss_observed": max_observed_rss_bytes is not None,
            "max_observed_rss_bytes": max_observed_rss_bytes,
            "worker_exited": process.pid is None or process.exitcode is not None,
        }

    def fail(error: OfficeVerifyError):
        error.execution_metrics = execution_metrics()
        raise error

    try:
        process.start()
        send_conn.close()
        deadline = started + float(budget.timeout_seconds)
        while time.monotonic() < deadline:
            remaining = max(0.0, deadline - time.monotonic())
            if process.is_alive():
                rss = _process_rss_bytes(process.pid)
                if rss is None:
                    _stop(process)
                    fail(OfficeVerifyError("OFFICE_RESOURCE_LIMIT", "worker_limits", "当前环境无法观察回读进程内存，已拒绝处理。"))
                max_observed_rss_bytes = max(max_observed_rss_bytes or 0, rss)
                if rss > budget.max_memory_bytes:
                    _stop(process)
                    fail(OfficeVerifyError("OFFICE_RESOURCE_LIMIT", "worker_limits", "回读进程超过内存限制，已终止处理。"))
            if recv_conn.poll(min(0.01, remaining)):
                try:
                    result_type, result_payload = recv_conn.recv()
                except EOFError as exc:
                    error = OfficeVerifyError("OFFICE_ENGINE_FAILED", "verify", "独立回读进程异常退出。")
                    error.__cause__ = exc
                    fail(error)
                process.join(timeout=0.2)
                _stop(process)
                if result_type == "ok":
                    if capture_metrics:
                        return result_payload, execution_metrics()
                    return result_payload
                if result_type == "office_error":
                    fail(OfficeVerifyError(result_payload["error_code"], result_payload["failed_stage"], result_payload["message"]))
                fail(OfficeVerifyError("OFFICE_ENGINE_FAILED", "verify", "Office 回读失败。"))
            if not process.is_alive():
                process.join(timeout=0.1)
                fail(OfficeVerifyError("OFFICE_ENGINE_FAILED", "verify", "独立回读进程异常退出。"))
        _stop(process)
        fail(OfficeVerifyError("OFFICE_RESOURCE_LIMIT", "verify", "Office 回读超过时间限制，已终止处理进程。"))
    except OfficeVerifyError as exc:
        if not hasattr(exc, "execution_metrics"):
            exc.execution_metrics = execution_metrics()
        raise
    except (OSError, RuntimeError, ValueError) as exc:
        error = OfficeVerifyError("OFFICE_ENGINE_FAILED", "verify", "无法启动受限 Office 回读进程。")
        error.__cause__ = exc
        fail(error)
    finally:
        recv_conn.close()
        try:
            send_conn.close()
        except OSError:
            pass
        _stop(process)


def verify_output(
    source_bytes: bytes,
    candidate_bytes: bytes,
    filename: str,
    mime_type: str,
    mapping_plan: dict[str, object],
    policy: VerificationPolicy | None = None,
    budget: VerificationBudget | None = None,
    *,
    authorized_blank_targets: tuple[str, ...] = (),
) -> VerificationReport:
    """Verify a candidate without accepting paths, Odoo objects, or file I/O."""
    selected_policy = policy or VerificationPolicy()
    selected_budget = budget or VerificationBudget()
    try:
        selected_policy.validate()
        selected_budget.validate()
    except (AttributeError, TypeError, ValueError) as exc:
        raise OfficeVerifyError("OFFICE_INVALID_OR_MISMATCHED", "input", "验证策略或资源预算无效。") from exc
    if not isinstance(source_bytes, bytes) or not isinstance(candidate_bytes, bytes):
        raise OfficeVerifyError("OFFICE_INVALID_OR_MISMATCHED", "input", "源文件和候选文件必须以字节传入。")
    if len(source_bytes) > selected_budget.max_file_size or len(candidate_bytes) > selected_budget.max_file_size:
        raise OfficeVerifyError("OFFICE_RESOURCE_LIMIT", "input", "文件超过输入大小限制。")
    return _run_worker(
        "mapping",
        (
            source_bytes,
            candidate_bytes,
            filename,
            mime_type,
            mapping_plan,
            selected_policy,
            selected_budget,
            authorized_blank_targets,
        ),
        selected_budget,
    )


def _verify_candidate_output(
    source_bytes: bytes,
    candidate_bytes: bytes,
    filename: str,
    mime_type: str,
    policy: VerificationPolicy | None = None,
    budget: VerificationBudget | None = None,
    *,
    capture_metrics: bool,
) -> CandidateValidationReport | tuple[CandidateValidationReport, dict[str, int | float | bool | None]]:
    """Internal Candidate worker entry preserving the existing bounded boundary."""
    selected_policy = policy or VerificationPolicy(enabled_formats=("xlsx",))
    selected_budget = budget or VerificationBudget()
    try:
        selected_policy.validate()
        selected_budget.validate()
    except (AttributeError, TypeError, ValueError) as exc:
        raise OfficeVerifyError("OFFICE_INVALID_OR_MISMATCHED", "input", "验证策略或资源预算无效。") from exc
    if not isinstance(source_bytes, bytes) or not isinstance(candidate_bytes, bytes):
        raise OfficeVerifyError("OFFICE_INVALID_OR_MISMATCHED", "input", "源文件和候选文件必须以字节传入。")
    if len(source_bytes) > selected_budget.max_file_size or len(candidate_bytes) > selected_budget.max_file_size:
        raise OfficeVerifyError("OFFICE_RESOURCE_LIMIT", "input", "文件超过输入大小限制。")
    return _run_worker(
        "candidate",
        (source_bytes, candidate_bytes, filename, mime_type, selected_policy, selected_budget),
        selected_budget,
        capture_metrics=capture_metrics,
    )


def verify_candidate_output(
    source_bytes: bytes,
    candidate_bytes: bytes,
    filename: str,
    mime_type: str,
    policy: VerificationPolicy | None = None,
    budget: VerificationBudget | None = None,
) -> CandidateValidationReport:
    """Verify XLSX candidate bytes using the existing bounded worker."""
    return _verify_candidate_output(
        source_bytes, candidate_bytes, filename, mime_type, policy, budget,
        capture_metrics=False,
    )


def verify_candidate_output_with_metrics(
    source_bytes: bytes,
    candidate_bytes: bytes,
    filename: str,
    mime_type: str,
    policy: VerificationPolicy | None = None,
    budget: VerificationBudget | None = None,
) -> tuple[CandidateValidationReport, dict[str, int | float | bool | None]]:
    """Verify a Candidate and return parent-observed worker timing/RSS data."""
    return _verify_candidate_output(
        source_bytes, candidate_bytes, filename, mime_type, policy, budget,
        capture_metrics=True,
    )


def verify_created_output_with_metrics(
    candidate_bytes: bytes,
    filename: str,
    mime_type: str,
    policy: VerificationPolicy | None = None,
    budget: VerificationBudget | None = None,
) -> tuple[CandidateValidationReport, dict[str, int | float | bool | None]]:
    """Validate a newly created XLSX without inventing an input workbook."""
    selected_policy = policy or VerificationPolicy(enabled_formats=("xlsx",))
    selected_budget = budget or VerificationBudget()
    try:
        selected_policy.validate()
        selected_budget.validate()
    except (AttributeError, TypeError, ValueError) as exc:
        raise OfficeVerifyError("OFFICE_INVALID_OR_MISMATCHED", "input", "验证策略或资源预算无效。") from exc
    if not isinstance(candidate_bytes, bytes):
        raise OfficeVerifyError("OFFICE_INVALID_OR_MISMATCHED", "input", "新建文件必须以字节传入。")
    if len(candidate_bytes) > selected_budget.max_file_size:
        raise OfficeVerifyError("OFFICE_RESOURCE_LIMIT", "input", "文件超过输入大小限制。")
    return _run_worker(
        "created",
        (None, candidate_bytes, filename, mime_type, selected_policy, selected_budget),
        selected_budget,
        capture_metrics=True,
    )
