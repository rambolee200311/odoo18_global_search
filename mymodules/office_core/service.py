"""Public synchronous service API with a killable, bounded worker process."""

from __future__ import annotations

import multiprocessing
import math
import sys
import time
from typing import Any

from .errors import OfficeCoreError
from .models import DocumentInspection, Element, RenderCandidate, ResourceBudget


def _apply_child_limits(timeout_seconds: float) -> None:
    """Apply an optional CPU guard; memory is supervised by the parent RSS sampler.

    RLIMIT_AS is deliberately not used: macOS Python processes commonly reserve
    virtual address space far above their resident memory, so a reasonable RSS
    budget can otherwise reject a worker before it starts parsing.
    """
    try:
        import resource
        if hasattr(resource, "RLIMIT_CPU"):
            cpu_seconds = max(1, math.ceil(float(timeout_seconds)))
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds + 1))
    except ImportError:
        # The parent still enforces a wall-clock timeout and RSS budget.
        return
    except (OSError, ValueError) as exc:
        raise OfficeCoreError("OFFICE_RESOURCE_LIMIT", "worker_limits", "当前运行环境无法落实进程 CPU 限制，已拒绝处理。") from exc


def _process_rss_bytes(pid: int) -> int | None:
    """Return a worker's resident set size on supported platforms.

    The parent samples at 50 ms intervals. This is a bounded, fail-closed
    supervisor with possible sampling overshoot, not an OS-enforced hard cap.
    """
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


def _stop_worker(process) -> None:
    if process.pid is None:
        return
    if process.is_alive():
        try:
            process.terminate()
        except OSError:
            pass
        process.join(timeout=0.5)
    if process.is_alive() and hasattr(process, "kill"):
        try:
            process.kill()
        except OSError:
            pass
        process.join(timeout=0.5)


def _child_worker(send_conn, operation: str, args: tuple[Any, ...], budget: ResourceBudget) -> None:
    try:
        _apply_child_limits(budget.timeout_seconds)
        from .engine import inspect_inline, render_inline

        if operation == "inspect":
            result = inspect_inline(*args, budget)
        elif operation == "render":
            result = render_inline(*args, budget)
        else:
            raise RuntimeError("invalid internal operation")
        send_conn.send(("ok", result))
    except OfficeCoreError as exc:
        send_conn.send(("office_error", (exc.code, exc.stage, exc.message)))
    except BaseException:
        # Deliberately do not expose tracebacks, paths, or parser details.
        try:
            send_conn.send(("engine_error", None))
        except Exception:
            pass
    finally:
        send_conn.close()


def _run_worker(operation: str, args: tuple[Any, ...], budget: ResourceBudget):
    budget.validate()
    recv_conn, send_conn = multiprocessing.get_context("spawn").Pipe(duplex=False)
    process = multiprocessing.get_context("spawn").Process(
        target=_child_worker,
        args=(send_conn, operation, args, budget),
        daemon=True,
    )
    started = time.monotonic()
    try:
        process.start()
        send_conn.close()
        deadline = started + float(budget.timeout_seconds)
        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            if process.is_alive():
                rss = _process_rss_bytes(process.pid)
                if rss is None:
                    _stop_worker(process)
                    raise OfficeCoreError("OFFICE_RESOURCE_LIMIT", operation, "无法监测 Office 处理进程内存，已终止处理。")
                if rss > budget.max_memory_bytes:
                    _stop_worker(process)
                    raise OfficeCoreError("OFFICE_RESOURCE_LIMIT", operation, "Office 处理进程超过内存限制，已终止处理。")
            if recv_conn.poll(min(0.05, max(0.0, remaining))):
                try:
                    kind, result = recv_conn.recv()
                except EOFError as exc:
                    raise OfficeCoreError("OFFICE_ENGINE_FAILED", operation, "Office 处理进程异常退出。") from exc
                process.join(timeout=0.2)
                _stop_worker(process)
                if kind == "ok":
                    return result
                if kind == "office_error":
                    raise OfficeCoreError(*result)
                raise OfficeCoreError("OFFICE_ENGINE_FAILED", operation, "Office 文件处理失败。")
            if not process.is_alive():
                process.join(timeout=0.1)
                raise OfficeCoreError("OFFICE_ENGINE_FAILED", operation, "Office 处理进程异常退出。")
        _stop_worker(process)
        raise OfficeCoreError("OFFICE_RESOURCE_LIMIT", operation, "Office 处理超过时间限制，已终止并清理候选数据。")
    except OfficeCoreError:
        raise
    except (OSError, RuntimeError, ValueError) as exc:
        raise OfficeCoreError("OFFICE_ENGINE_FAILED", operation, "无法启动受限 Office 处理进程。") from exc
    finally:
        recv_conn.close()
        try:
            send_conn.close()
        except OSError:
            pass
        _stop_worker(process)


def inspect_document(
    content: bytes,
    filename: str,
    mime_type: str,
    budget: ResourceBudget,
) -> DocumentInspection:
    """Inspect a bounded Office byte stream; no file path or Odoo object accepted."""
    return _run_worker("inspect", (content, filename, mime_type), budget)


def render_candidate(
    content: bytes,
    filename: str,
    mime_type: str,
    mapping: dict[str, object],
    budget: ResourceBudget,
) -> RenderCandidate:
    """Render an isolated candidate byte stream; this is never a delivery result."""
    return _run_worker("render", (content, filename, mime_type, mapping), budget)
