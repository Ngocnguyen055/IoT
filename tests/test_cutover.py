"""The live backend changes only after a verified migration and a stable source."""

import io
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

import mongomock

from backend.app.migrations.sqlite_to_mongodb import MigrationError, read_snapshot
from backend.app.repositories.mongodb import MongoDBRepository
from backend.app.repositories.sqlite import SQLiteRepository
from backend.app.validation import telemetry_payload
from scripts import migrate_mongodb
from scripts import check_active_mongodb
from env_config import read_env, write_env


ROOT = Path(__file__).resolve().parents[1]


class CutoverTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="cutover-test-", dir=ROOT / ".runtime")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.config_path = self.root / "config.local.json"
        self.config = {"ADMIN_PASSWORD": "test-admin-only", "DEVICE_KEY": "test-device-only", "SESSION_SECRET": "test-session-only", "custom_setting": "preserved"}
        self.config_path.write_text(json.dumps(self.config), encoding="utf-8")
        self.original_config = self.config_path.read_bytes()
        self.sqlite = SQLiteRepository(self.root / "iot_ngoc.sqlite3")
        self.sqlite.initialize()
        self.sqlite.save_reading(telemetry_payload({"device_id": "device-a", "event": "button", "bpm": 0, "lat": 0, "lon": 0}), 1000)
        self.sqlite.queue_locate("device-a")
        self.original_database = self.sqlite.database.read_bytes()
        self.settings = {"MONGODB_URI": "mongodb://localhost/", "MONGODB_DATABASE": "cutover_test", "MONGODB_TIMEOUT_MS": 5000}

        class MockRepository(MongoDBRepository):
            def initialize(self):
                self._initialize_storage()

            def _with_transaction(self, operation):
                return operation(None)

        self.repository = MockRepository(mongomock.MongoClient(), "cutover_test")
        self.repository.initialize()

    def run_cutover(self):
        with patch.object(migrate_mongodb, "require_stopped_web"), patch.object(migrate_mongodb, "build_repository", return_value=self.repository):
            return migrate_mongodb.cutover(self.root, self.settings, io.StringIO())

    def assert_sqlite_unchanged(self):
        self.assertEqual(self.sqlite.database.read_bytes(), self.original_database)
        self.assertEqual(self.config_path.read_bytes(), self.original_config)

    def test_success_backs_up_data_and_credentials_before_enabling_mongodb(self):
        report = self.run_cutover()
        self.assertTrue(report["ok"])
        self.assertTrue(report["web_api_matches"])
        self.assertEqual(report["state"], "mongodb_enabled")
        self.assertEqual(json.loads(self.config_path.read_text()), {**self.config, "DATABASE_BACKEND": "mongodb"})
        self.assertEqual(self.sqlite.database.read_bytes(), self.original_database)
        backup = Path(report["backup"])
        self.assertTrue(backup.is_relative_to(self.root / ".runtime/backups"))
        self.assertEqual((backup / "files/config.local.json").read_bytes(), self.original_config)
        self.assertEqual(read_snapshot(backup / "iot_ngoc.sqlite3").fingerprint, read_snapshot(self.sqlite.database).fingerprint)
        saved = json.loads((self.root / ".runtime/migration-report.json").read_text())
        self.assertEqual(saved, report)

    def test_conflict_does_not_enable_backend_or_overwrite_sqlite(self):
        self.repository.readings.insert_one({"_id": 1, "bpm": 123})
        with self.assertRaises(MigrationError):
            self.run_cutover()
        self.assert_sqlite_unchanged()
        self.assertEqual(self.repository.readings.find_one()["bpm"], 123)

    def test_failed_read_verification_can_resume_without_duplicates(self):
        with patch.object(migrate_mongodb, "verify_read_models", side_effect=MigrationError("verification failure")):
            with self.assertRaises(MigrationError):
                self.run_cutover()
        self.assert_sqlite_unchanged()
        report = self.run_cutover()
        self.assertTrue(report["ok"])
        self.assertEqual(report["inserted_readings"], 0)
        self.assertEqual(self.repository.readings.count_documents({}), 1)

    def test_source_changed_during_copy_prevents_activation(self):
        def add_reading(*args):
            self.sqlite.save_reading(telemetry_payload({"device_id": "device-a", "event": "telemetry"}), 1001)
            return {}

        with patch.object(migrate_mongodb, "verify_read_models", side_effect=add_reading):
            with self.assertRaisesRegex(MigrationError, "SQLite vua"):
                self.run_cutover()
        self.assertEqual(self.config_path.read_bytes(), self.original_config)

    def test_configuration_changed_during_copy_is_not_overwritten(self):
        changed = {**self.config, "custom_setting": "changed-during-copy"}

        def edit_config(*args):
            self.config_path.write_text(json.dumps(changed), encoding="utf-8")
            return {}

        with patch.object(migrate_mongodb, "verify_read_models", side_effect=edit_config):
            with self.assertRaisesRegex(MigrationError, "Cau hinh web vua"):
                self.run_cutover()
        self.assertEqual(json.loads(self.config_path.read_text()), changed)
        self.assertEqual(self.sqlite.database.read_bytes(), self.original_database)

    def test_running_web_blocks_cutover_before_backup_or_database_writes(self):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen()
            with self.assertRaisesRegex(MigrationError, "Web con dang chay"):
                migrate_mongodb.require_stopped_web(listener.getsockname()[1])
        with patch.object(migrate_mongodb, "require_stopped_web", side_effect=MigrationError("Web con dang chay")), patch.object(migrate_mongodb, "create_backup") as backup:
            with self.assertRaises(MigrationError):
                migrate_mongodb.cutover(self.root, self.settings, io.StringIO())
        backup.assert_not_called()
        self.assert_sqlite_unchanged()

    def check_active(self):
        from backend.app import create_app
        settings = {**self.config, **self.settings, "DATABASE_BACKEND": "mongodb", "DB_PATH": str(self.sqlite.database)}
        with patch.object(check_active_mongodb, "ROOT", self.root), patch.object(check_active_mongodb, "build_config", return_value=settings), patch.object(check_active_mongodb, "create_app", side_effect=lambda config: create_app(config, repository=self.repository)):
            return check_active_mongodb.check_active()

    def test_active_check_allows_new_telemetry_and_updated_commands_after_cutover(self):
        self.run_cutover()
        self.repository.save_reading(telemetry_payload({"device_id": "device-a", "event": "remote"}), 1001)
        result = self.check_active()
        self.assertEqual(result["imported_readings_verified"], 1)
        self.assertEqual(result["total_readings"], 2)
        self.assertEqual(self.repository.pending_command("device-a"), "NONE")

    def test_active_check_detects_a_modified_imported_measurement(self):
        self.run_cutover()
        self.repository.readings.update_one({"_id": 1}, {"$set": {"bpm": 123}})
        with self.assertRaises(MigrationError):
            self.check_active()

    def test_cutover_updates_dotenv_when_it_is_the_primary_configuration(self):
        env = self.root / ".env"
        values = {**self.config, **self.settings, "DATABASE_BACKEND": "sqlite"}
        write_env(env, {key: str(value) for key, value in values.items()})
        report = self.run_cutover()
        self.assertTrue(report["ok"])
        self.assertEqual(read_env(env)["DATABASE_BACKEND"], "mongodb")
        self.assertEqual(read_env(env)["DEVICE_KEY"], self.config["DEVICE_KEY"])
        self.assertEqual(self.config_path.read_bytes(), self.original_config)
