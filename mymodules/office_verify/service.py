"""Public synchronous API with bounded, killable process isolation."""

from __future__ import annotations

import multiprocessing
import os
import sys
import time
from typing import Any

from .errors import OfficeVerifyError
from .models import VerificationBudget, VerificationPolicy, VerificationReport


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
        source, candidate, filename, mime_type, mapping, policy, budget = args
        _validate_worker_budget(budget.max_memory_bytes, budget.timeout_seconds)
        from .verify import verify_inline

        report = verify_inline(source, candidate, filename, mime_type, mapping, policy, budget)
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


def verify_output(
    source_bytes: bytes,
    candidate_bytes: bytes,
    filename: str,
    mime_type: str,
    mapping_plan: dict[str, object],
    policy: VerificationPolicy | None = None,
    budget: VerificationBudget | None = None,
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
    context = multiprocessing.get_context("spawn")
    recv_conn, send_conn = context.Pipe(duplex=False)
    process = context.Process(
        target=_worker,
        args=(send_conn, (source_bytes, candidate_bytes, filename, mime_type, mapping_plan, selected_policy, selected_budget)),
        daemon=True,
    )
    started = time.monotonic()
    try:
        process.start()
        send_conn.close()
        deadline = started + float(selected_budget.timeout_seconds)
        while time.monotonic() < deadline:
            remaining = max(0.0, deadline - time.monotonic())
            if process.is_alive():
                rss = _process_rss_bytes(process.pid)
                if rss is None:
                    _stop(process)
                    raise OfficeVerifyError("OFFICE_RESOURCE_LIMIT", "worker_limits", "当前环境无法观察回读进程内存，已拒绝处理。")
                if rss > selected_budget.max_memory_bytes:
                    _stop(process)
                    raise OfficeVerifyError("OFFICE_RESOURCE_LIMIT", "worker_limits", "回读进程超过内存限制，已终止处理。")
            if recv_conn.poll(min(0.01, remaining)):
                try:
                    result_type, payload = recv_conn.recv()
                except EOFError as exc:
                    raise OfficeVerifyError("OFFICE_ENGINE_FAILED", "verify", "独立回读进程异常退出。") from exc
                process.join(timeout=0.2)
                _stop(process)
                if result_type == "ok":
                    return payload
                if result_type == "office_error":
                    raise OfficeVerifyError(payload["error_code"], payload["failed_stage"], payload["message"])
                raise OfficeVerifyError("OFFICE_ENGINE_FAILED", "verify", "Office 回读失败。")
            if not process.is_alive():
                process.join(timeout=0.1)
                raise OfficeVerifyError("OFFICE_ENGINE_FAILED", "verify", "独立回读进程异常退出。")
        _stop(process)
        raise OfficeVerifyError("OFFICE_RESOURCE_LIMIT", "verify", "Office 回读超过时间限制，已终止处理进程。")
    except OfficeVerifyError:
        raise
    except (OSError, RuntimeError, ValueError) as exc:
        raise OfficeVerifyError("OFFICE_ENGINE_FAILED", "verify", "无法启动受限 Office 回读进程。") from exc
    finally:
        recv_conn.close()
        try:
            send_conn.close()
        except OSError:
            pass
        _stop(process)
