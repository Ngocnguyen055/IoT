"""Model invariants and schema setup control flow; MongoDB enforces validators in Atlas checks."""

from copy import deepcopy
from dataclasses import replace
import unittest

import mongomock

from backend.app.database import initialize_database
from backend.app.models import DeviceCommand, Reading, ReadingCounter
from backend.app.repositories.mongodb import MongoDBRepository


class MetadataDatabase:
    """Track DDL metadata locally; this deliberately does not emulate BSON validation."""
    def __init__(self, database):
        self.database = database
        self.options = {}
        self.changes = []

    def __getitem__(self, name):
        return self.database[name]

    def list_collections(self):
        return [{"name": name, "options": deepcopy(self.options.get(name, {}))} for name in self.database.list_collection_names()]

    def create_collection(self, name, **options):
        self.database.create_collection(name)
        self.options[name] = deepcopy(options)
        self.changes.append(("create", name))

    def command(self, command):
        name = command["collMod"]
        self.options[name] = deepcopy({key: value for key, value in command.items() if key != "collMod"})
        self.changes.append(("modify", name))
        return {"ok": 1}


class ModelTests(unittest.TestCase):
    def test_reading_round_trip_preserves_id_timestamp_zero_null_and_fractional_values(self):
        reading = Reading(8, "device-a", 1000, "button", lat=0, lon=0, bpm=72.5, spo2=0, battery_pct=None)
        self.assertEqual(Reading.from_document(reading.to_document(), strict=True), reading)
        public = reading.to_public()
        self.assertEqual((public["id"], public["ts"], public["lat"], public["spo2"]), (8, 1000, 0, 0))
        self.assertEqual(public["bpm"], 72.5)
        self.assertIsNone(public["battery_pct"])
        self.assertNotIn("_id", public)

    def test_invalid_readings_are_rejected(self):
        reading = Reading(1, "device-a", 1000, "telemetry")
        for changes in ({"id": True}, {"id": 0}, {"device_id": ""}, {"ts": -1}, {"event": "unknown"},
                        {"bpm": float("nan")}, {"bpm": True}, {"spo2": 101}, {"lat": 0}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                replace(reading, **changes)

    def test_command_and_counter_models_preserve_the_existing_storage_contract(self):
        self.assertEqual(DeviceCommand.from_document({"_id": "device-a", "cmd": "LOCATE"}, strict=True).to_document(), {"_id": "device-a", "cmd": "LOCATE"})
        self.assertEqual(ReadingCounter.from_document({"_id": "readings", "value": 312}, strict=True).value, 312)
        for value in (-1, True, 1.5):
            with self.assertRaises(ValueError):
                ReadingCounter(value)
        with self.assertRaises(ValueError):
            DeviceCommand("device-a", "DELETE")


class SchemaInitializationTests(unittest.TestCase):
    def setUp(self):
        self.repository = MongoDBRepository(mongomock.MongoClient(), "schema_test")
        self.metadata = MetadataDatabase(self.repository.database)
        self.repository.database = self.metadata
        self.addCleanup(self.repository.close)

    def test_fresh_setup_creates_all_collections_indexes_and_initial_counter(self):
        result = initialize_database(self.repository)
        self.assertEqual(result["counts"], {"readings": 0, "commands": 0, "counters": 1})
        self.assertEqual(result["counter"], 0)
        self.assertTrue(initialize_database(self.repository, check_only=True)["ok"])

    def test_repeat_setup_preserves_documents_and_does_not_repeat_metadata_changes(self):
        initialize_database(self.repository)
        reading = Reading(8, "device-a", 1000, "telemetry", bpm=0).to_document()
        self.repository.readings.insert_one(reading)
        self.repository.commands.insert_one(DeviceCommand("device-a", "LOCATE").to_document())
        initialize_database(self.repository)
        changes = list(self.metadata.changes)
        initialize_database(self.repository)
        self.assertEqual(self.metadata.changes, changes)
        self.assertEqual(list(self.repository.readings.find()), [reading])
        self.assertEqual(self.repository.pending_command("device-a"), "LOCATE")
        self.assertEqual(self.repository.counters.find_one()["value"], 8)

    def test_old_collections_receive_validators_without_rewriting_data(self):
        reading = Reading(8, "device-a", 1000, "button").to_document()
        self.repository.readings.insert_one(reading)
        initialize_database(self.repository)
        self.assertIn(("modify", "readings"), self.metadata.changes)
        self.assertEqual(list(self.repository.readings.find()), [reading])

    def test_invalid_existing_data_or_foreign_validator_stops_before_metadata_changes(self):
        self.repository.readings.insert_one({"_id": 1, "bpm": 999})
        with self.assertRaises(ValueError):
            initialize_database(self.repository)
        self.assertEqual(self.metadata.changes, [])
        self.metadata.database.drop_collection("readings")
        self.metadata.database.create_collection("readings")
        self.metadata.options["readings"] = {"validator": {"unrelated": True}}
        with self.assertRaises(ValueError):
            initialize_database(self.repository)
        self.assertEqual(self.metadata.changes, [])

    def test_check_only_never_initializes_a_missing_collection(self):
        with self.assertRaises(ValueError):
            initialize_database(self.repository, check_only=True)
        self.assertEqual(self.metadata.changes, [])
        self.assertEqual(self.metadata.database.list_collection_names(), [])
