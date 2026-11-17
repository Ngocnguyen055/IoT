"""Domain models shared by persistence, validation and database initialization."""

from .command import DeviceCommand
from .counter import ReadingCounter
from .reading import EVENTS, MEASUREMENT_RANGES, READING_FIELDS, Reading


COLLECTION_MODELS = {"readings": Reading, "commands": DeviceCommand, "counters": ReadingCounter}
