"""One pending location command per device."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DeviceCommand:
    device_id: str
    cmd: str = "NONE"

    def __post_init__(self):
        if not isinstance(self.device_id, str) or not 1 <= len(self.device_id) <= 64:
            raise ValueError("Command device_id must have 1 to 64 characters")
        if self.cmd not in {"NONE", "LOCATE"}:
            raise ValueError("Unsupported device command")

    def to_document(self):
        return {"_id": self.device_id, "cmd": self.cmd}

    @classmethod
    def from_document(cls, document, *, strict=False):
        if strict and set(document) != {"_id", "cmd"}:
            raise ValueError("Stored command fields differ from the model")
        return cls(document["_id"], document.get("cmd", "NONE"))

    @staticmethod
    def json_schema():
        return {"bsonType": "object", "required": ["_id", "cmd"], "additionalProperties": False,
                "properties": {"_id": {"bsonType": "string", "minLength": 1, "maxLength": 64},
                               "cmd": {"enum": ["NONE", "LOCATE"]}}}
