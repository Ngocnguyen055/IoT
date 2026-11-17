"""Stored telemetry and alert model; units and field names match the device API."""

from dataclasses import dataclass
import math


EVENTS = {"telemetry", "button", "high_bpm", "low_spo2", "remote"}
MEASUREMENT_RANGES = {
    "lat": (-90, 90), "lon": (-180, 180), "gps_satellites": (0, 100),
    "bpm": (0, 300), "spo2": (0, 100), "battery_pct": (0, 100),
    "battery_voltage": (0, 100), "current_ma": (-10000, 10000),
}
READING_FIELDS = ("device_id", "ts", "event", *MEASUREMENT_RANGES)
NUMBER_TYPES = ["double", "int", "long"]


@dataclass(frozen=True)
class Reading:
    id: int
    device_id: str
    ts: int
    event: str
    lat: float | None = None
    lon: float | None = None
    gps_satellites: float | None = None
    bpm: float | None = None
    spo2: float | None = None
    battery_pct: float | None = None
    battery_voltage: float | None = None
    current_ma: float | None = None

    def __post_init__(self):
        if not isinstance(self.id, int) or isinstance(self.id, bool) or not 1 <= self.id <= 2**63 - 1:
            raise ValueError("Reading ID must be a positive BSON integer")
        if not isinstance(self.device_id, str) or not 1 <= len(self.device_id) <= 64:
            raise ValueError("Reading device_id must have 1 to 64 characters")
        if not isinstance(self.ts, int) or isinstance(self.ts, bool) or self.ts < 0:
            raise ValueError("Reading timestamp must be Unix seconds")
        if self.event not in EVENTS:
            raise ValueError("Unsupported reading event")
        for name, (lower, upper) in MEASUREMENT_RANGES.items():
            value = getattr(self, name)
            if value is not None and (not isinstance(value, (int, float)) or isinstance(value, bool)
                                      or not math.isfinite(value) or not lower <= value <= upper):
                raise ValueError(f"Invalid reading field: {name}")
        if (self.lat is None) != (self.lon is None):
            raise ValueError("Latitude and longitude must be present together")

    def to_document(self):
        return {"_id": self.id, **{name: getattr(self, name) for name in READING_FIELDS}}

    def to_public(self):
        result = {name: getattr(self, name) for name in READING_FIELDS}
        result["id"] = self.id
        for name in ("gps_satellites", "bpm", "spo2"):
            value = result[name]
            if isinstance(value, float) and value.is_integer():
                result[name] = int(value)
        return result

    @classmethod
    def from_document(cls, document, *, strict=False):
        if strict and set(document) != {"_id", *READING_FIELDS}:
            raise ValueError("Stored reading fields differ from the model")
        return cls(id=document["_id"], **{name: document.get(name) for name in READING_FIELDS})

    @staticmethod
    def json_schema():
        properties = {
            "_id": {"bsonType": ["int", "long"], "minimum": 1},
            "device_id": {"bsonType": "string", "minLength": 1, "maxLength": 64},
            "ts": {"bsonType": ["int", "long"], "minimum": 0},
            "event": {"enum": sorted(EVENTS)},
        }
        properties.update({name: {"bsonType": [*NUMBER_TYPES, "null"], "minimum": limits[0], "maximum": limits[1]}
                           for name, limits in MEASUREMENT_RANGES.items()})
        return {"bsonType": "object", "required": ["_id", *READING_FIELDS], "additionalProperties": False,
                "properties": properties,
                "oneOf": [{"properties": {"lat": {"bsonType": "null"}, "lon": {"bsonType": "null"}}},
                          {"properties": {"lat": {"bsonType": NUMBER_TYPES}, "lon": {"bsonType": NUMBER_TYPES}}}]}
