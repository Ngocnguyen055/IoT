"""MongoDB data/query contracts using mongomock; real transactions run on Atlas."""

import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from backend.app import create_app
from backend.app.config import build_config
from backend.app.mongodb_config import load_mongodb_settings, validate_mongodb_settings
from backend.app.repositories.errors import DatabaseUnavailable
from backend.app.repositories.factory import build_repository
from scripts.configure_mongodb import complete_atlas_uri
import test_api as contract


ROOT = Path(__file__).resolve().parents[1]
HAVE_MONGO = bool(importlib.util.find_spec("pymongo") and importlib.util.find_spec("mongomock"))


@unittest.skipUnless(HAVE_MONGO, "Run Cai-thu-vien-kiem-thu.cmd first")
class AtlasVerificationTests(unittest.TestCase):
    def test_verification_names_fit_atlas_limit_and_cleanup_is_isolated(self):
        from scripts import check_mongodb

        settings = {"MONGODB_URI": "mongodb://localhost/", "MONGODB_DATABASE": "application_data", "MONGODB_TIMEOUT_MS": 5000}
        control = MagicMock()
        control.admin.command.return_value = {"ok": 1, "setName": "verification"}
        names = []

        def make_app(config):
            name = config["MONGODB_DATABASE"]
            self.assertLessEqual(len(name.encode("utf-8")), 38)
            self.assertNotEqual(name, settings["MONGODB_DATABASE"])
            names.append(name)

        def exercise_database_lifecycle(suite):
            # Exercise each real case's database setup/cleanup without a network connection.
            for case in suite:
                try:
                    case.make_app(Path("unused.sqlite3"))
                finally:
                    self.assertTrue(case.doCleanups())
            return SimpleNamespace(wasSuccessful=lambda: True, testsRun=len(names), failures=[], errors=[])

        with patch.object(check_mongodb, "MongoClient", return_value=control), patch.object(check_mongodb, "create_app", side_effect=make_app), patch.object(check_mongodb.unittest, "TextTestRunner") as runner:
            runner.return_value.run.side_effect = exercise_database_lifecycle
            report = check_mongodb.run_checks(settings, io.StringIO())

        self.assertTrue(report["ok"])
        self.assertGreaterEqual(len(names), 10)  # Also exercise two-digit case numbers.
        self.assertEqual(len(set(names)), len(names))
        self.assertEqual(report["test_databases_remaining"], [])
        self.assertEqual([call.args[0] for call in control.__getitem__.call_args_list], [name for name in names for _ in range(3)])
        self.assertEqual(control.__getitem__.return_value.drop_collection.call_count, 3 * len(names))
        control.close.assert_called_once()


@unittest.skipUnless(HAVE_MONGO, "Run Cai-thu-vien-kiem-thu.cmd first")
class MongoApiContractTests(contract.ApiContractTests):
    def make_app(self, database):
        import mongomock
        from backend.app.repositories.mongodb import MongoDBRepository

        class MockRepository(MongoDBRepository):
            def initialize(self):
                self._initialize_storage()

            def _with_transaction(self, operation):
                # mongomock has no sessions; rollback is checked separately against Atlas.
                return operation(None)

        repository = MockRepository(mongomock.MongoClient(), "contract_test")
        return create_app({**contract.TEST_CONFIG, "DB_PATH": str(database), "TESTING": True}, repository=repository)

    def seed(self, rows):
        from mongodb_support import seed_readings
        seed_readings(self.repository, rows)


class MongoConfigurationTests(unittest.TestCase):
    def test_atlas_settings_validate_without_connecting_or_printing_uri(self):
        settings = validate_mongodb_settings({"MONGODB_URI": "mongodb+srv://YOUR_USER:YOUR_PASSWORD@YOUR_CLUSTER.mongodb.net/", "MONGODB_DATABASE": "iot_sos"})
        self.assertEqual(settings["MONGODB_DATABASE"], "iot_sos")
        self.assertEqual(settings["MONGODB_TIMEOUT_MS"], 5000)

    def test_invalid_uris_databases_and_timeouts_are_rejected(self):
        for changes in (
            {"MONGODB_URI": ""}, {"MONGODB_URI": "https://example.com"},
            {"MONGODB_URI": "mongodb+srv://<username>:<password>@cluster.mongodb.net/"},
            {"MONGODB_URI": "mongodb+srv://cluster.mongodb.net/?tls=false"},
            {"MONGODB_URI": "mongodb://localhost/?tlsAllowInvalidCertificates=true"},
            {"MONGODB_DATABASE": "admin"}, {"MONGODB_DATABASE": "bad/name"},
            {"MONGODB_TIMEOUT_MS": 0}, {"MONGODB_TIMEOUT_MS": "bad"},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validate_mongodb_settings({"MONGODB_URI": "mongodb://localhost/", **changes})

    def test_private_configuration_file_is_read_without_modification(self):
        with tempfile.TemporaryDirectory(prefix="mongo-config-", dir=ROOT / ".runtime") as folder:
            path = Path(folder) / "mongodb.local.json"
            path.write_text(json.dumps({"MONGODB_URI": "mongodb://localhost/", "MONGODB_DATABASE": "iot_sos"}), encoding="utf-8-sig")
            before = path.read_bytes()
            self.assertEqual(load_mongodb_settings(path)["MONGODB_DATABASE"], "iot_sos")
            self.assertEqual(path.read_bytes(), before)

    def test_sqlite_default_does_not_read_mongodb_credentials(self):
        with patch("backend.app.config.load_mongodb_settings", side_effect=AssertionError("MongoDB config must not be read")):
            settings = build_config({**contract.TEST_CONFIG, "DB_PATH": ROOT / ".runtime/unused.sqlite3"})
        self.assertEqual(settings["DATABASE_BACKEND"], "sqlite")

    def test_explicit_mongodb_settings_do_not_read_private_configuration(self):
        with patch("backend.app.config.load_mongodb_settings", side_effect=AssertionError("Private config must not be read")):
            settings = build_config({**contract.TEST_CONFIG, "DATABASE_BACKEND": "mongodb", "MONGODB_URI": "mongodb://localhost/", "MONGODB_DATABASE": "isolated_test"})
        self.assertEqual(settings["MONGODB_DATABASE"], "isolated_test")
        self.assertEqual(settings["DATABASE_BACKEND"], "mongodb")

    def test_optional_settings_follow_override_environment_local_priority(self):
        local = {**contract.TEST_CONFIG, "DATABASE_BACKEND": "mongodb", "MONGODB_URI": "mongodb://localhost/", "MONGODB_DATABASE": "local_test"}
        with patch("backend.app.config.application_config", return_value=local):
            with patch.dict(os.environ, {"DATABASE_BACKEND": "sqlite"}, clear=True):
                self.assertEqual(build_config()["DATABASE_BACKEND"], "sqlite")
            with patch.dict(os.environ, {"MONGODB_DATABASE": "environment_test"}, clear=True):
                self.assertEqual(build_config()["MONGODB_DATABASE"], "environment_test")
                self.assertEqual(build_config({"MONGODB_DATABASE": "override_test"})["MONGODB_DATABASE"], "override_test")
        self.assertEqual(local["DATABASE_BACKEND"], "mongodb")
        self.assertEqual(local["MONGODB_DATABASE"], "local_test")

    def test_database_failure_returns_503_without_connection_details(self):
        with tempfile.TemporaryDirectory(prefix="mongo-error-", dir=ROOT / ".runtime") as folder:
            app = create_app({**contract.TEST_CONFIG, "DB_PATH": Path(folder) / "error.sqlite3", "TESTING": True})
            client = app.test_client()
            client.post("/login", data={"password": contract.TEST_CONFIG["ADMIN_PASSWORD"]})
            with patch.object(app.extensions["sos_repository"], "dashboard_snapshot", side_effect=DatabaseUnavailable()):
                response = client.get("/api/status")
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.json, {"error": "database unavailable"})

    def test_configuration_helper_encodes_password_and_rejects_missing_placeholder_values(self):
        uri = complete_atlas_uri("mongodb+srv://YOUR_USER:<db_password>@YOUR_CLUSTER.mongodb.net/", password="a@b:c/ d")
        self.assertIn("a%40b%3Ac%2F+d@", uri)
        with self.assertRaises(ValueError):
            complete_atlas_uri("mongodb+srv://YOUR_USER:<db_password>@YOUR_CLUSTER.mongodb.net/")


@unittest.skipUnless(HAVE_MONGO, "Run Cai-thu-vien-kiem-thu.cmd first")
class MongoRepositoryTests(unittest.TestCase):
    def repository(self):
        import mongomock
        from backend.app.repositories.mongodb import MongoDBRepository
        repository = MongoDBRepository(mongomock.MongoClient(), "repository_test")
        repository._initialize_storage()
        return repository

    def test_existing_reading_ids_advance_but_never_reset_counter(self):
        repository = self.repository()
        repository.readings.insert_one({"_id": 40, "device_id": "ngoc-01", "event": "telemetry", "ts": 1000})
        repository._initialize_storage()
        self.assertEqual(repository.counters.find_one({"_id": "readings"})["value"], 40)
        repository.readings.delete_many({})
        repository._initialize_storage()
        self.assertEqual(repository.counters.find_one({"_id": "readings"})["value"], 40)

    def test_internal_fields_are_not_exported_to_dashboard(self):
        repository = self.repository()
        repository.readings.insert_one({"_id": 1, "device_id": "ngoc-01", "event": "button", "ts": 1000, "internal": "not-public", "bpm": 72.0})
        latest = repository.dashboard_snapshot()["latest"]
        self.assertNotIn("_id", latest)
        self.assertNotIn("internal", latest)
        self.assertEqual(latest["id"], 1)
        self.assertIsInstance(latest["bpm"], int)

    def test_indexes_cover_device_time_and_id_order(self):
        repository = self.repository()
        indexes = repository.readings.index_information()
        self.assertIn("_id_", indexes)
        self.assertEqual(indexes["idx_readings_device_ts"]["key"], [("device_id", 1), ("ts", 1)])
        self.assertEqual(indexes["idx_readings_device_id"]["key"], [("device_id", 1), ("_id", -1)])

    def test_driver_error_is_translated_to_database_unavailable(self):
        from pymongo.errors import ConnectionFailure
        repository = self.repository()
        with patch.object(repository.readings, "find", side_effect=ConnectionFailure("private-server-details")):
            with self.assertRaises(DatabaseUnavailable) as raised:
                repository.dashboard_snapshot()
        self.assertEqual(str(raised.exception), "database unavailable")
        self.assertNotIn("private-server-details", str(raised.exception))

    def test_factory_selects_mongodb_and_keeps_connection_details_private(self):
        import mongomock
        from pymongo.errors import ConnectionFailure
        from backend.app.repositories.mongodb import MongoDBRepository
        settings = {"DATABASE_BACKEND": "mongodb", "MONGODB_URI": "mongodb://localhost/", "MONGODB_DATABASE": "factory_test", "MONGODB_TIMEOUT_MS": 5000}
        with patch("pymongo.MongoClient", return_value=mongomock.MongoClient()):
            repository = build_repository(settings)
        self.assertIsInstance(repository, MongoDBRepository)
        self.assertEqual(repository.database_name, "factory_test")
        with patch("pymongo.MongoClient", side_effect=ConnectionFailure("private-server-details")):
            with self.assertRaises(DatabaseUnavailable) as raised:
                build_repository(settings)
        self.assertEqual(str(raised.exception), "database unavailable")

    def test_startup_requires_transactions_and_closes_failed_client(self):
        from unittest.mock import MagicMock
        from backend.app.repositories.mongodb import MongoDBRepository
        client = MagicMock()
        client.admin.command.return_value = {"ok": 1}
        repository = MongoDBRepository(client, "startup_test")
        with patch.object(repository, "_initialize_storage") as initialize:
            with self.assertRaises(DatabaseUnavailable) as raised:
                repository.initialize()
        self.assertEqual(raised.exception.reason, "transactions_require_replica_set")
        initialize.assert_not_called()
        client.close.assert_called_once()
