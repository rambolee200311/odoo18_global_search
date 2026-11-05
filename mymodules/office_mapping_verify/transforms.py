"""Small, explicit transformations for already-authorized scalar values."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Mapping


MAX_DATE_OFFSET_DAYS = 365_000


def validate_transform(transform: Any, value_type: str) -> dict[str, Any]:
    """Validate the bounded transform contract; never evaluate user code."""
    if (
        not isinstance(transform, Mapping)
        or set(transform) != {"type", "days"}
        or transform.get("type") != "date_offset"
        or value_type not in {"date", "datetime"}
        or type(transform.get("days")) is not int
        or abs(transform["days"]) > MAX_DATE_OFFSET_DAYS
    ):
        raise ValueError("invalid_date_offset_transform")
    return {"type": "date_offset", "days": transform["days"]}


def apply_transform(value: Any, transform: Mapping[str, Any], value_type: str) -> str:
    """Apply the bounded date offset and return a typed ISO value."""
    clean = validate_transform(transform, value_type)
    offset = timedelta(days=clean["days"])
    if value_type == "date":
        if isinstance(value, datetime):
            raise ValueError("date_offset_type_mismatch")
        parsed = value if isinstance(value, date) else date.fromisoformat(value)
        return (parsed + offset).isoformat()

    parsed_datetime = (
        value
        if isinstance(value, datetime)
        else datetime.fromisoformat(value.replace("Z", "+00:00"))
    )
    if parsed_datetime.utcoffset() is not None:
        raise ValueError("timezone_unsupported")
    return (parsed_datetime + offset).isoformat()
