"""Public synchronous service API with a killable, bounded worker process."""

from __future__ import annotations

import multiprocessing
import math
import time
from typing import Any

from .errors import OfficeCoreError
from .models import DocumentInspection, Element, RenderCandidate, ResourceBudget


def _apply_child_limits(memory_bytes: int, timeout_seconds: float) -> None:
    try:
        import resource

        if not hasattr(resource, "RLIMIT_AS"):
            raise OfficeCoreError("OFFICE_RESOURCE_LIMIT", "worker_limits", "当前运行环境无法落实内存上限，已拒绝处理。")
        soft, hard = resource.getrlimit(resource.RLIMIT_AS)
        limit = memory_bytes if hard in (-1, resource.RLIM_INFINITY) else min(memory_bytes, hard)
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
        if hasattr(resource, "RLIMIT_CPU"):
            cpu_seconds = max(1, math.ceil(float(timeout_seconds)))
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds + 1))
    except ImportError as exc:
        raise OfficeCoreError("OFFICE_RESOURCE_LIMIT", "worker_limits", "当前运行环境无法落实进程资源上限，已拒绝处理。") from exc
    except (OSError, ValueError) as exc:
        raise OfficeCoreError("OFFICE_RESOURCE_LIMIT", "worker_limits", "当前运行环境无法落实调用方声明的内存上限，已拒绝处理。") from exc


def _child_worker(send_conn, operation: str, args: tuple[Any, ...], budget: ResourceBudget) -> None:
    try:
        _apply_child_limits(budget.max_memory_bytes, budget.timeout_seconds)
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
            if recv_conn.poll(min(0.05, max(0.0, remaining))):
                try:
                    kind, result = recv_conn.recv()
                except EOFError as exc:
                    raise OfficeCoreError("OFFICE_ENGINE_FAILED", operation, "Office 处理进程异常退出。") from exc
                process.join(timeout=0.2)
                if process.is_alive():
                    process.terminate()
                    process.join(timeout=1)
                if kind == "ok":
                    return result
                if kind == "office_error":
                    raise OfficeCoreError(*result)
                raise OfficeCoreError("OFFICE_ENGINE_FAILED", operation, "Office 文件处理失败。")
            if not process.is_alive():
                process.join(timeout=0.1)
                raise OfficeCoreError("OFFICE_ENGINE_FAILED", operation, "Office 处理进程异常退出。")
        process.terminate()
        process.join(timeout=1)
        if process.is_alive() and hasattr(process, "kill"):
            process.kill()
            process.join(timeout=1)
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
        if process.pid is not None and process.is_alive():
            process.terminate()
            process.join(timeout=1)
        if process.pid is not None and process.is_alive() and hasattr(process, "kill"):
            process.kill()
            process.join(timeout=1)


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
