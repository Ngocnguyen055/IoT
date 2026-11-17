"""Indexes match the positive predicates used by alert and GPS queries."""

from copy import deepcopy

from ..alerts import alert_filter


ALERT_INDEX = "idx_readings_alerts_id"
LOCATION_INDEX = "idx_readings_location_id"
DEVICE_LOCATION_INDEX = "idx_readings_device_location_id"
GPS_FILTER = {"lat": {"$type": "number"}, "lon": {"$type": "number"}}

# Include a second key in the global indexes: the built-in _id index cannot be partial.
READING_INDEXES = (
    ("idx_readings_device_ts", (("device_id", 1), ("ts", 1)), None),
    ("idx_readings_device_id", (("device_id", 1), ("_id", -1)), None),
    (ALERT_INDEX, (("_id", -1), ("event", 1)), alert_filter()),
    (LOCATION_INDEX, (("_id", -1), ("lat", 1)), GPS_FILTER),
    (DEVICE_LOCATION_INDEX, (("device_id", 1), ("_id", -1)), GPS_FILTER),
)


def ensure_reading_indexes(collection):
    for name, keys, partial in READING_INDEXES:
        options = {"partialFilterExpression": deepcopy(partial)} if partial else {}
        collection.create_index(list(keys), name=name, **options)


def verify_reading_indexes(collection):
    existing = collection.index_information()
    for name, keys, partial in READING_INDEXES:
        actual = existing.get(name, {})
        if actual.get("key") != list(keys) or actual.get("partialFilterExpression") != partial:
            raise ValueError(f"MongoDB reading index is missing or different: {name}")
