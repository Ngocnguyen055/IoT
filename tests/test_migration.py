"""Migration contracts shared by local mocks and disposable real Atlas databases."""

import hashlib
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from backend.app.migrations.sqlite_to_mongodb import MigrationConflict, MigrationError, migrate_snapshot, read_snapshot, verify_read_models, verify_snapshot
from backend.app.repositories.mongodb import MongoDBRepository
from backend.app.repositories.sqlite import SQLiteRepository
from backend.app.validation import telemetry_payload


ROOT = Path(__file__).resolve().parents[1]


class MigrationContractTests(unittest.TestCase):
    real_transactions = False

    def setUp(self):
        (ROOT / ".runtime").mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="migration-test-", dir=ROOT / ".runtime")
        self.addCleanup(self.temporary.cleanup)
        self.source = Path(self.temporary.name) / "source.sqlite3"
        self.sqlite = SQLiteRepository(self.source)
        self.sqlite.initialize()
        with self.sqlite.connect() as connection:
            connection.executemany("""INSERT INTO readings
                (id,device_id,ts,event,lat,lon,gps_satellites,bpm,spo2,battery_pct,battery_voltage,current_ma)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""", [
                (2, "device-a", 1000, "button", 0, 0, 0, 0, None, 0, 0, 0),
                (8, "device-b", 1001, "telemetry", None, None, None, None, 98, 80.4, 4.004, 0.6),
                (15, "device-a", 1002, "remote", 21.03, 105.85, 5, 72, 99, None, None, None),
                (20, "device-a", 1003, "telemetry", None, None, None, None, None, None, None, None),
            ])
            connection.execute("DELETE FROM readings WHERE id=20")
            connection.executemany("INSERT INTO commands(device_id,cmd) VALUES(?,?)", [("device-a", "LOCATE"), ("device-b", "NONE")])
        self.snapshot = read_snapshot(self.source)
        self.repository = self.make_repository()

    def make_repository(self):
        import mongomock

        class MockRepository(MongoDBRepository):
            def _with_transaction(self, operation):
                return operation(None)

        repository = MockRepository(mongomock.MongoClient(), "migration_test")
        repository._initialize_storage()
        self.addCleanup(repository.close)
        return repository

    def test_source_is_read_only_and_preserves_null_zero_ids_timestamps_and_sequence(self):
        before = hashlib.sha256(self.source.read_bytes()).hexdigest()
        snapshot = read_snapshot(self.source)
        self.assertEqual([row["_id"] for row in snapshot.readings], [2, 8, 15])
        self.assertEqual([row["ts"] for row in snapshot.readings], [1000, 1001, 1002])
        self.assertEqual(snapshot.readings[0]["bpm"], 0)
        self.assertIsNone(snapshot.readings[1]["bpm"])
        self.assertEqual(snapshot.readings[0]["lat"], 0)
        self.assertIsNone(snapshot.readings[1]["lat"])
        self.assertEqual(snapshot.sequence, 20)
        self.assertEqual(before, hashlib.sha256(self.source.read_bytes()).hexdigest())
        missing = self.source.with_name("missing.sqlite3")
        with self.assertRaises(MigrationError):
            read_snapshot(missing)
        self.assertFalse(missing.exists())

    def test_migration_repeats_without_duplicates_or_changing_pending_commands(self):
        first = migrate_snapshot(self.snapshot, self.repository)
        again = migrate_snapshot(self.snapshot, self.repository)
        self.assertEqual((first["inserted_readings"], first["inserted_commands"]), (3, 2))
        self.assertEqual((again["inserted_readings"], again["inserted_commands"]), (0, 0))
        self.assertEqual(first["source_fingerprint"], again["source_fingerprint"])
        self.assertEqual(self.repository.pending_command("device-a"), "LOCATE")
        self.assertEqual(self.repository.readings.count_documents({}), 3)

    def test_matching_partial_import_resumes(self):
        self.repository.readings.insert_one(dict(self.snapshot.readings[0]))
        self.repository.commands.insert_one(dict(self.snapshot.commands[0]))
        result = migrate_snapshot(self.snapshot, self.repository)
        self.assertEqual((result["inserted_readings"], result["inserted_commands"]), (2, 1))
        verify_snapshot(self.snapshot, self.repository)

    def test_conflicting_reading_is_preserved_and_no_other_rows_are_imported(self):
        conflict = {**self.snapshot.readings[0], "bpm": 123}
        self.repository.readings.insert_one(conflict)
        with self.assertRaises(MigrationConflict):
            migrate_snapshot(self.snapshot, self.repository)
        self.assertEqual(list(self.repository.readings.find()), [conflict])
        self.assertEqual(self.repository.commands.count_documents({}), 0)

    def test_extra_target_reading_stops_import(self):
        self.repository.readings.insert_one({**self.snapshot.readings[0], "_id": 999})
        with self.assertRaises(MigrationConflict):
            migrate_snapshot(self.snapshot, self.repository)
        self.assertEqual(self.repository.readings.count_documents({}), 1)

    def test_conflicting_command_stops_import_before_any_reading_is_written(self):
        self.repository.commands.insert_one({"_id": "device-a", "cmd": "NONE"})
        with self.assertRaises(MigrationConflict):
            migrate_snapshot(self.snapshot, self.repository)
        self.assertEqual(self.repository.readings.count_documents({}), 0)
        self.assertEqual(self.repository.pending_command("device-a"), "NONE")

    def test_counter_never_moves_back_and_next_upload_uses_a_fresh_id(self):
        self.repository.counters.update_one({"_id": "readings"}, {"$set": {"value": 100}})
        result = migrate_snapshot(self.snapshot, self.repository)
        self.assertEqual(result["target_counter"], 100)
        self.repository.save_reading(telemetry_payload({"device_id": "device-a", "event": "telemetry"}), 1004)
        self.assertEqual(self.repository.readings.find_one({"_id": 101})["ts"], 1004)

    def test_dashboard_and_gps_queries_match_sqlite_after_migration(self):
        migrate_snapshot(self.snapshot, self.repository)
        result = verify_read_models(self.sqlite, self.repository)
        self.assertEqual(result, {"dashboard_matches": True, "gps_devices_checked": 2})

    def test_verification_detects_missing_or_modified_values(self):
        with self.assertRaises(MigrationError):
            verify_snapshot(self.snapshot, self.repository)
        migrate_snapshot(self.snapshot, self.repository)
        self.repository.readings.update_one({"_id": 2}, {"$set": {"lat": None}})
        with self.assertRaises(MigrationConflict):
            verify_snapshot(self.snapshot, self.repository)

    def test_real_interrupted_transaction_rolls_back_every_collection_then_retries(self):
        if not self.real_transactions:
            self.skipTest("Rollback is checked against Atlas; mongomock has no transactions")
        with patch.object(self.repository.commands, "insert_many", side_effect=RuntimeError("verification interruption")):
            with self.assertRaises(RuntimeError):
                migrate_snapshot(self.snapshot, self.repository)
        self.assertEqual(self.repository.readings.count_documents({}), 0)
        self.assertEqual(self.repository.commands.count_documents({}), 0)
        self.assertEqual(self.repository.counters.find_one({"_id": "readings"})["value"], 0)
        migrate_snapshot(self.snapshot, self.repository)
        verify_snapshot(self.snapshot, self.repository)
