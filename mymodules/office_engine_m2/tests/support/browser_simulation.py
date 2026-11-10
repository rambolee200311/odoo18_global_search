"""Process-isolated Mock Candidate adapter for the CC-04 browser simulation.

This module is imported only by ``dispatch_office_action`` when a dedicated
loopback Odoo process explicitly enables the test hook. It never calls a
Provider. It turns the persisted, CB-03-shaped Expected Effect into XLSX bytes;
the production orchestrator, CB-03 Validator, CB-02 receipt/version services,
ORM permissions and Thread tool history remain in the real call path.
"""

from __future__ import annotations

import hashlib
import os
from io import BytesIO
from types import SimpleNamespace
from zipfile import ZIP_DEFLATED, ZipFile

from openpyxl import load_workbook
from odoo.tools import config


class ExpectedEffectWorkbookAdapter:
    def __init__(self, env, thread, tool_message, effect):
        self.env = env
        self.thread = thread
        self.tool_message = tool_message
        self.effect = effect

    def execute(self, *, input_xlsx, instruction, input_sha256, **_kwargs):
        actual_input_sha = hashlib.sha256(input_xlsx).hexdigest()
        if actual_input_sha != input_sha256 or self.effect.get("input_sha256") != actual_input_sha:
            return _result("failed", error="synthetic_input_binding_mismatch")
        workbook = load_workbook(BytesIO(input_xlsx), data_only=False)
        for assertion in self.effect.get("expected_assertions", []):
            if assertion.get("kind") != "cell_value":
                return _result("blocked", error="synthetic_effect_kind_unsupported")
            sheet_name = assertion.get("sheet")
            address = assertion.get("address")
            if sheet_name not in workbook.sheetnames:
                return _result("failed", error="synthetic_target_sheet_missing")
            value_type, value = assertion.get("value_type"), assertion.get("value")
            if value_type == "blank":
                value = None
            elif value_type not in {"string", "number", "boolean", "date", "datetime"}:
                return _result("blocked", error="synthetic_value_type_unsupported")
            workbook[sheet_name][address] = value
        output = BytesIO()
        workbook.save(output)
        candidate = _preserve_core_properties(input_xlsx, output.getvalue())
        return SimpleNamespace(
            operation_status="candidate_received",
            candidate_bytes=candidate,
            input_sha256=actual_input_sha,
            candidate_sha256=hashlib.sha256(candidate).hexdigest(),
            provider_response_id="synthetic-browser-simulation-response",
            request_id="synthetic-browser-simulation-request",
            tool_call_ids=("synthetic-browser-simulation-tool-call",),
            provider_file_ids=("synthetic-browser-simulation-file",),
            provider_filename="cb04-synthetic-candidate.xlsx",
            usage={"synthetic": True},
            duration_ms=0,
            cleanup_state="not_required",
            error=None,
            to_dict=lambda: {
                "operation_status": "candidate_received",
                "provider": "CC-04 browser simulation adapter; no external Provider request",
                "candidate_sha256": hashlib.sha256(candidate).hexdigest(),
            },
        )


def dependencies_for(env, thread, tool_message):
    """Return the test dependency tuple only for an explicitly isolated process."""
    if os.environ.get("OFFICE_CB04_BROWSER_SIMULATION") != "1":
        return None
    if (
        env.cr.dbname != "odoo18ce"
        or config.get("http_interface") not in {"127.0.0.1", "localhost"}
        or int(config.get("http_port") or 0) != 8092
        or int(config.get("workers") or 0) != 0
    ):
        return None
    raw_ids = os.environ.get("OFFICE_CB04_BROWSER_SIMULATION_THREAD_IDS", "")
    try:
        allowed_ids = {int(value) for value in raw_ids.split(",") if value.strip()}
    except ValueError:
        return None
    if not allowed_ids or thread.id not in allowed_ids:
        return None

    # Read the bound plan from actual preceding `office` tool history. The
    # adapter does not infer targets from natural-language keywords.
    from ...services.edit_orchestrator import _latest_plan, _resolve_current

    context = _resolve_current(env, thread)
    _plan_message, plan_result = _latest_plan(env, context, tool_message)
    if not plan_result or not isinstance(plan_result.get("expected_effect"), dict):
        return None
    adapter = ExpectedEffectWorkbookAdapter(
        env, thread, tool_message, plan_result["expected_effect"]
    )
    return adapter, object(), "cb04-synthetic-browser-mock", SimpleNamespace(synthetic=True)


def _result(status, *, error):
    return SimpleNamespace(
        operation_status=status,
        candidate_bytes=None,
        error=SimpleNamespace(category=error),
        to_dict=lambda: {"operation_status": status, "error_code": error},
    )


def _preserve_core_properties(source_xlsx, candidate_xlsx):
    """Avoid treating openpyxl's serialization timestamp as an edit Effect."""
    with ZipFile(BytesIO(source_xlsx), "r") as source, ZipFile(
        BytesIO(candidate_xlsx), "r"
    ) as candidate:
        source_names = set(source.namelist())
        candidate_names = set(candidate.namelist())
        if "docProps/core.xml" not in source_names or "docProps/core.xml" not in candidate_names:
            return candidate_xlsx
        preserved_core = source.read("docProps/core.xml")
        output = BytesIO()
        with ZipFile(output, "w", ZIP_DEFLATED) as normalized:
            for entry in candidate.infolist():
                data = (
                    preserved_core
                    if entry.filename == "docProps/core.xml"
                    else candidate.read(entry.filename)
                )
                normalized.writestr(entry, data)
        return output.getvalue()
