"""Alert history ordering and response shape, shared by both storage backends."""

from .models import EVENTS


ALERT_EVENTS = tuple(sorted(EVENTS - {"telemetry"}))
ALERT_PAGE_SIZE = 20
HOME_ALERT_LIMIT = 8


def alert_filter(snapshot=None, before=None, after=None):
    query = {"event": {"$in": list(ALERT_EVENTS)}}
    bounds = {}
    if snapshot is not None:
        bounds["$lte"] = snapshot
    if before is not None:
        bounds["$lt"] = before
    if after is not None:
        bounds["$gt"] = after
    if bounds:
        query["_id"] = bounds
    return query


def alert_page_result(items, snapshot, *, has_previous, has_next):
    has_previous, has_next = bool(items) and has_previous, bool(items) and has_next
    return {"items": items, "pagination": {
        "page_size": ALERT_PAGE_SIZE, "snapshot": snapshot,
        "has_previous": has_previous, "has_next": has_next,
        "previous_after": items[0]["id"] if has_previous else None,
        "next_before": items[-1]["id"] if has_next else None,
    }}
