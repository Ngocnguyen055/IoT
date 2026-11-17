"""Run the API contract and rollback checks on disposable Atlas test databases."""

from datetime import datetime, timezone
import json
import re
import sys
import unittest
from uuid import uuid4

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from backend.app import create_app
from backend.app.mongodb_config import load_mongodb_settings
from backend.app.repositories.errors import DatabaseUnavailable
from backend.app.validation import telemetry_payload
from project_config import ROOT


sys.path.insert(0, str(ROOT / "tests"))
import test_api as contract
from mongodb_support import seed_readings


def run_checks(settings, stream):
    # Leave room for the test number within Atlas's 38-byte database name limit.
    token = uuid4().hex[:24]
    prefix = "sosv_" + token + "_"
    owned = set()
    control = MongoClient(settings["MONGODB_URI"], serverSelectionTimeoutMS=settings["MONGODB_TIMEOUT_MS"], connectTimeoutMS=settings["MONGODB_TIMEOUT_MS"], socketTimeoutMS=10000, maxPoolSize=5)

    def cleanup(name):
        if name not in owned or not re.fullmatch(re.escape(prefix) + r"[0-9]+", name):
            raise RuntimeError("Refusing to clean an unowned database")
        for collection in ("readings", "commands", "counters"):
            control[name].drop_collection(collection)
        owned.remove(name)

    class AtlasApiContractTests(contract.ApiContractTests):
        next_database = 0

        def make_app(self, database):
            type(self).next_database += 1
            name = prefix + str(type(self).next_database)
            if name == settings["MONGODB_DATABASE"]:
                raise RuntimeError("Verification must not use the configured application database")
            owned.add(name)

            def release():
                try:
                    cleanup(name)
                finally:
                    repository = getattr(self, "repository", None)
                    if repository is not None:
                        repository.close()
            self.addCleanup(release)
            return create_app({**contract.TEST_CONFIG, **settings, "DATABASE_BACKEND": "mongodb", "MONGODB_DATABASE": name, "DB_PATH": str(database), "TESTING": True})

        def seed(self, rows):
            seed_readings(self.repository, rows)

        def test_real_transaction_rolls_back_reading_counter_and_command(self):
            self.repository.queue_locate("ngoc-01")
            commands = self.repository.commands

            class IntentionalRollback(RuntimeError):
                pass

            class FailAcknowledgement:
                def update_one(self, *args, **kwargs):
                    raise IntentionalRollback("verification rollback")

            reading = telemetry_payload({"device_id": "ngoc-01", "event": "remote"})
            try:
                self.repository.commands = FailAcknowledgement()
                with self.assertRaises(IntentionalRollback):
                    self.repository.save_reading(reading, 1000)
            finally:
                self.repository.commands = commands
            self.assertEqual(self.repository.readings.count_documents({}), 0)
            self.assertEqual(self.repository.counters.find_one({"_id": "readings"})["value"], 0)
            self.assertEqual(self.repository.pending_command("ngoc-01"), "LOCATE")
            self.repository.save_reading(reading, 1000)
            self.assertEqual(self.repository.readings.find_one()["_id"], 1)
            self.assertEqual(self.repository.pending_command("ngoc-01"), "NONE")

    try:
        control.admin.command("ping")
        hello = control.admin.command("hello")
        if not hello.get("setName") and hello.get("msg") != "isdbgrid":
            raise DatabaseUnavailable("transactions_require_replica_set")
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(AtlasApiContractTests)
        result = unittest.TextTestRunner(stream=stream, verbosity=2, failfast=True).run(suite)
        return {"ok": result.wasSuccessful() and not owned, "tests_run": result.testsRun,
                "failures": len(result.failures), "errors": len(result.errors),
                "test_databases_remaining": sorted(owned)}
    finally:
        for name in list(owned):
            try:
                cleanup(name)
            except PyMongoError:
                pass
        control.close()


class Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, value):
        for stream in self.streams:
            stream.write(value)
            stream.flush()

    def flush(self):
        for stream in self.streams:
            stream.flush()


def main():
    runtime = ROOT / ".runtime"
    runtime.mkdir(exist_ok=True)
    report = {"ok": False, "checked_at_utc": datetime.now(timezone.utc).isoformat()}
    with (runtime / "atlas-check.log").open("w", encoding="utf-8") as log:
        output = Tee(sys.stdout, log)
        try:
            settings = load_mongodb_settings()
            print("Kiem tra Atlas tren database tam rieng; web va SQLite dang dung duoc giu nguyen.", file=output)
            report.update(run_checks(settings, output))
        except (DatabaseUnavailable, PyMongoError):
            report["reason"] = "connection_or_permissions"
            print("Chua ket noi/kiem tra duoc Atlas. Kiem tra cluster, Network Access va database user.", file=output)
        except (ValueError, OSError) as error:
            report["reason"] = "configuration"
            print("LOI CAU HINH:", str(error), file=output)
        print("ATLAS KIEM TRA DAT." if report["ok"] else "ATLAS CHUA DAT. Xem .runtime/atlas-check.log.", file=output)
    (runtime / "atlas-check.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
