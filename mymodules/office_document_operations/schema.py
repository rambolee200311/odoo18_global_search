"""Versioned JSON Schema loading and operation-list preflight validation."""

from __future__ import annotations

import copy
import json
import math
from datetime import date, datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from .errors import DocumentOperationError

SCHEMA_PATH = Path(__file__).with_name("schemas") / "document_operation_v1.0.schema.json"
with SCHEMA_PATH.open("r", encoding="utf-8") as schema_file:
    OPERATION_SCHEMA: dict[str, Any] = json.load(schema_file)
Draft202012Validator.check_schema(OPERATION_SCHEMA)
_VALIDATOR = Draft202012Validator(OPERATION_SCHEMA, format_checker=FormatChecker())


def validate_operation_list(document: object) -> dict[str, Any]:
    """Validate and normalize the complete operation list before file access.

    Normalization applies only documented defaults. It never repairs an
    invalid target or changes the order of operations.
    """
    if not isinstance(document, dict):
        raise DocumentOperationError("invalid_operation_list", "schema", "Operation List must be a JSON object.")
    errors = sorted(_VALIDATOR.iter_errors(document), key=lambda error: list(error.absolute_path))
    if errors:
        error = errors[0]
        location = ".".join(str(part) for part in error.absolute_path) or "document"
        raise DocumentOperationError(
            "invalid_operation_schema",
            "schema",
            f"Invalid Operation List at {location}: {error.message}",
        )

    normalized = copy.deepcopy(document)
    operation_ids: set[str] = set()
    for operation in normalized["operations"]:
        operation_id = operation["operation_id"]
        if operation_id in operation_ids:
            raise DocumentOperationError(
                "duplicate_operation_id", "schema", "operation_id values must be unique.", operation_id
            )
        operation_ids.add(operation_id)
        parameters = operation["parameters"]
        if operation["type"] == "clear":
            parameters.setdefault("formula_policy", "preserve")
            parameters.setdefault("include_header", False)
        if operation["type"] == "set_value":
            parameters.setdefault("overwrite_formula", False)
        _validate_typed_values(operation)
    return normalized


def _validate_typed_values(operation: dict[str, Any]) -> None:
    parameters = operation["parameters"]
    values: list[dict[str, Any]] = []
    if operation["type"] == "set_value":
        if "value" in parameters:
            values.append(parameters["value"])
        else:
            values.extend(value for row in parameters["values"] for value in row)
    for value in values:
        kind, data = value["type"], value["data"]
        if kind == "number" and not math.isfinite(float(data)):
            raise DocumentOperationError(
                "invalid_numeric_value", "schema", "Numeric values must be finite.", operation["operation_id"]
            )
        if kind == "date":
            try:
                date.fromisoformat(data)
            except ValueError as exc:
                raise DocumentOperationError(
                    "invalid_date_value", "schema", "Date values must use a valid ISO-8601 date.", operation["operation_id"]
                ) from exc
        elif kind == "datetime":
            try:
                parsed = datetime.fromisoformat(data.replace("Z", "+00:00"))
            except ValueError as exc:
                raise DocumentOperationError(
                    "invalid_datetime_value", "schema", "Datetime values must use a valid ISO-8601 timestamp.", operation["operation_id"]
                ) from exc
            if parsed.utcoffset() is not None:
                raise DocumentOperationError(
                    "timezone_unsupported",
                    "schema",
                    "XLSX date-time cells do not preserve timezone offsets; provide a timezone-naive local datetime.",
                    operation["operation_id"],
                )
