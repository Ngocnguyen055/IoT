"""Validate HTTP input as plain Python data, independently of Flask and storage."""

from .models import EVENTS, MEASUREMENT_RANGES

class ValidationError(ValueError):
    """A request cannot be accepted under the current API contract."""


def require_object(payload):
    if not isinstance(payload, dict):
        raise ValidationError("JSON required")
    return payload


def device_identifier(value, error="bad device_id"):
    identifier = str(value)
    if not 1 <= len(identifier) <= 64:
        raise ValidationError(error)
    return identifier


def finite_measurement(name, value):
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        raise ValidationError(f"bad field: {name}") from None
    lower, upper = MEASUREMENT_RANGES[name]
    if not lower <= number <= upper:
        raise ValidationError(f"bad field: {name}")
    return number


def telemetry_payload(payload):
    payload = require_object(payload)
    event = payload.get("event", "telemetry")
    if not isinstance(event, str) or event not in EVENTS:
        raise ValidationError("bad event")
    result = {"device_id": device_identifier(payload.get("device_id", "")), "event": event}
    for name in MEASUREMENT_RANGES:
        result[name] = finite_measurement(name, payload.get(name))
        if name == "lon" and (result["lat"] is None) != (result["lon"] is None):
            raise ValidationError("lat/lon together")
    return result


def command_payload(payload):
    payload = require_object(payload)
    identifier = device_identifier(payload.get("device_id", "ngoc-01"), error="bad device")
    if payload.get("command") != "LOCATE":
        raise ValidationError("bad command")
    return identifier


def track_parameters(device_id, hours):
    identifier = device_identifier(device_id)
    try:
        hours = int(hours)
    except (TypeError, ValueError, OverflowError):
        raise ValidationError("bad hours") from None
    if not 1 <= hours <= 168:
        raise ValidationError("hours out of range")
    return identifier, hours


def alert_parameters(snapshot=None, before=None, after=None):
    values = {}
    for name, value in (("snapshot", snapshot), ("before", before), ("after", after)):
        if value is None:
            values[name] = None
            continue
        if not isinstance(value, str) or not value.isascii() or not value.isdecimal():
            raise ValidationError(f"bad {name}")
        try:
            number = int(value)
        except ValueError:
            raise ValidationError(f"bad {name}") from None
        if not (0 if name == "snapshot" else 1) <= number <= 2**63 - 1:
            raise ValidationError(f"bad {name}")
        values[name] = number
    cursors = [values[name] for name in ("before", "after") if values[name] is not None]
    if len(cursors) > 1:
        raise ValidationError("before and after cannot be used together")
    if cursors and (values["snapshot"] is None or cursors[0] > values["snapshot"]):
        raise ValidationError("cursor requires a matching snapshot")
    return values
