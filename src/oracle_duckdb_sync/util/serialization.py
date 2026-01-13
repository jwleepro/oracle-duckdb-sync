"""
Serialization utilities for JSON encoding of datetime and pandas objects.

This module provides unified serialization support for:
- datetime.datetime, datetime.date
- pandas Timestamp
- Any object with isoformat() method
"""
import json
from datetime import date, datetime
from typing import Any


def serialize_datetime(value: Any) -> Any:
    """
    Convert datetime-like objects to ISO format string.

    Supports:
    - datetime.datetime, datetime.date
    - pandas Timestamp (via isoformat check)
    - Any object with isoformat() method

    Args:
        value: Value to convert

    Returns:
        ISO format string if datetime-like, otherwise original value
    """
    # pandas Timestamp 및 isoformat 지원 객체 처리
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


class DateTimeJSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder that handles datetime and pandas Timestamp objects.

    Usage:
        json.dumps(data, cls=DateTimeJSONEncoder)
    """

    def default(self, obj: Any) -> Any:
        """Override default to handle datetime-like objects."""
        if hasattr(obj, "isoformat"):
            return obj.isoformat()
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)


def json_dumps_safe(obj: Any, **kwargs) -> str:
    """
    Safely serialize object to JSON string with datetime support.

    Convenience wrapper around json.dumps with DateTimeJSONEncoder.

    Args:
        obj: Object to serialize
        **kwargs: Additional arguments passed to json.dumps

    Returns:
        JSON string
    """
    kwargs.setdefault("ensure_ascii", False)
    return json.dumps(obj, cls=DateTimeJSONEncoder, **kwargs)
