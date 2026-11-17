"""Check strict model validators on fresh disposable Atlas collections."""

import re
import unittest
from uuid import uuid4

from pymongo import MongoClient
from pymongo.errors import OperationFailure, PyMongoError

from backend.app.database import initialize_database
from backend.app.models import DeviceCommand, Reading
from backend.app.repositories.factory import build_repository
from backend.app.validation import telemetry_payload


def run_checks(settings, stream):
    prefix = "soss_" + uuid4().hex[:24] + "_"
    owned = set()
    control = MongoClient(settings["MONGODB_URI"], serverSelectionTimeoutMS=settings["MONGODB_TIMEOUT_MS"], connectTimeoutMS=settings["MONGODB_TIMEOUT_MS"], socketTimeoutMS=10000)

    def cleanup(name):
        if name not in owned or not re.fullmatch(re.escape(prefix) + r"[0-9]+", name):
            raise RuntimeError("Refusing to clean an unowned schema database")
        for collection in ("readings", "commands", "counters"):
            control[name].drop_collection(collection)
        owned.remove(name)

    class AtlasSchemaTests(unittest.TestCase):
        number = 0

        def setUp(self):
            type(self).number += 1
            name = prefix + str(type(self).number)
            if name == settings["MONGODB_DATABASE"]:
                raise RuntimeError("Schema verification cannot use the application database")
            owned.add(name)
            self.repository = build_repository({**settings, "DATABASE_BACKEND": "mongodb", "MONGODB_DATABASE": name})

            def release():
                try:
                    cleanup(name)
                finally:
                    self.repository.close()
            self.addCleanup(release)
            initialize_database(self.repository)

        def test_initialization_repeats_without_changing_readings_commands_or_counter(self):
            self.repository.queue_locate("schema-device")
            self.repository.save_reading(telemetry_payload({"device_id": "schema-device", "event": "button", "bpm": 0, "lat": 0, "lon": 0}), 1000)
            before = {name: list(self.repository.database[name].find()) for name in ("readings", "commands", "counters")}
            initialize_database(self.repository)
            self.assertEqual({name: list(self.repository.database[name].find()) for name in before}, before)
            self.assertTrue(initialize_database(self.repository, check_only=True)["ok"])

        def test_invalid_documents_are_rejected_by_mongodb_itself(self):
            reading = Reading(1, "schema-device", 1000, "telemetry").to_document()
            self.repository.readings.insert_one(reading)
            invalid = [
                ("readings", {**reading, "_id": 2, "spo2": 101}),
                ("readings", {**reading, "_id": 2, "bpm": True}),
                ("readings", {**reading, "_id": 2, "lat": 0, "lon": None}),
                ("readings", {**reading, "_id": 2, "event": "unknown"}),
                ("commands", {"_id": "schema-device", "cmd": "DELETE"}),
                ("counters", {"_id": "unknown", "value": 0}),
            ]
            for name, document in invalid:
                with self.subTest(collection=name), self.assertRaises(OperationFailure) as raised:
                    self.repository.database[name].insert_one(document)
                self.assertEqual(raised.exception.code, 121)
            self.repository.commands.insert_one(DeviceCommand("schema-device").to_document())

    try:
        control.admin.command("ping")
        result = unittest.TextTestRunner(stream=stream, verbosity=2, failfast=True).run(unittest.defaultTestLoader.loadTestsFromTestCase(AtlasSchemaTests))
        return {"ok": result.wasSuccessful() and not owned, "tests_run": result.testsRun,
                "failures": len(result.failures), "errors": len(result.errors), "test_databases_remaining": sorted(owned)}
    finally:
        for name in list(owned):
            try:
                cleanup(name)
            except PyMongoError:
                pass
        control.close()
