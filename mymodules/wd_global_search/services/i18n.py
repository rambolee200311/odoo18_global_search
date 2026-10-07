"""Small, server-owned i18n and timezone helpers for CC-009."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


DEFAULT_LANG = "en_US"
DEFAULT_TZ = "UTC"


def translate(labels, lang):
    """Return the requested label, falling back to the server's English label."""
    if not isinstance(labels, dict):
        raise TypeError("labels must be a mapping")
    requested = labels.get(lang)
    return requested or labels.get(DEFAULT_LANG) or next(iter(labels.values()), "")


def user_timezone(tz_name):
    try:
        return ZoneInfo(tz_name or DEFAULT_TZ)
    except (TypeError, ZoneInfoNotFoundError):
        return ZoneInfo(DEFAULT_TZ)


def format_datetime(value, tz_name=DEFAULT_TZ):
    """Format a UTC datetime as an ISO value in the current user's timezone."""
    if not isinstance(value, datetime):
        raise TypeError("value must be a datetime")
    aware = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
    return aware.astimezone(user_timezone(tz_name)).isoformat()


def week_start(lang):
    """Return Python's weekday index; en_US Sunday, other supported languages Monday."""
    return 6 if (lang or DEFAULT_LANG).lower().startswith("en_us") else 0
