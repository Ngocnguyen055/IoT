"""Monotonic reading identifier; never replaces IDs inherited from SQLite."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ReadingCounter:
    value: int = 0

    def __post_init__(self):
        if not isinstance(self.value, int) or isinstance(self.value, bool) or not 0 <= self.value <= 2**63 - 1:
            raise ValueError("Readings counter must be a nonnegative BSON integer")

    def to_document(self):
        return {"_id": "readings", "value": self.value}

    @classmethod
    def from_document(cls, document, *, strict=False):
        if document.get("_id") != "readings" or (strict and set(document) != {"_id", "value"}):
            raise ValueError("Stored counter differs from the model")
        return cls(document["value"])

    @staticmethod
    def json_schema():
        return {"bsonType": "object", "required": ["_id", "value"], "additionalProperties": False,
                "properties": {"_id": {"enum": ["readings"]}, "value": {"bsonType": ["int", "long"], "minimum": 0}}}
