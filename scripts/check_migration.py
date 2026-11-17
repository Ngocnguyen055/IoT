"""Exercise the migration on disposable Atlas databases, never the application database."""

from datetime import datetime, timezone
import json
import re
import sys
import unittest
from uuid import uuid4

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from backend.app.mongodb_config import load_mongodb_settings
from backend.app.repositories.factory import build_repository
from project_config import ROOT

sys.path.insert(0, str(ROOT / "tests"))
from test_migration import MigrationContractTests


def run_checks(settings, stream):
    prefix = "sosm_" + uuid4().hex[:24] + "_"
    owned = set()
    control = MongoClient(settings["MONGODB_URI"], serverSelectionTimeoutMS=settings["MONGODB_TIMEOUT_MS"], connectTimeoutMS=settings["MONGODB_TIMEOUT_MS"], socketTimeoutMS=10000, maxPoolSize=5)

    def cleanup(name):
        if name not in owned or not re.fullmatch(re.escape(prefix) + r"[0-9]+", name):
            raise RuntimeError("Refusing to clean an unowned verification database")
        for collection in ("readings", "commands", "counters"):
            control[name].drop_collection(collection)
        owned.remove(name)

    class AtlasMigrationTests(MigrationContractTests):
        real_transactions = True
        next_database = 0

        def make_repository(self):
            type(self).next_database += 1
            name = prefix + str(type(self).next_database)
            if name == settings["MONGODB_DATABASE"]:
                raise RuntimeError("Verification cannot use the application database")
            owned.add(name)
            repository = build_repository({**settings, "DATABASE_BACKEND": "mongodb", "MONGODB_DATABASE": name})

            def release():
                try:
                    cleanup(name)
                finally:
                    repository.close()
            self.addCleanup(release)
            repository.initialize()
            return repository

    try:
        control.admin.command("ping")
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(AtlasMigrationTests)
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


def main():
    from scripts.check_mongodb import Tee
    from backend.app.repositories.errors import DatabaseUnavailable

    runtime = ROOT / ".runtime"
    runtime.mkdir(exist_ok=True)
    report = {"ok": False, "checked_at_utc": datetime.now(timezone.utc).isoformat()}
    with (runtime / "migration-check.log").open("w", encoding="utf-8") as log:
        output = Tee(sys.stdout, log)
        try:
            report.update(run_checks(load_mongodb_settings(), output))
        except (PyMongoError, DatabaseUnavailable):
            print("Chua kiem tra duoc Atlas; kiem tra ket noi, IP va database user.", file=output)
        except (ValueError, OSError):
            print("Khong doc duoc cau hinh Atlas tren may.", file=output)
        print("KIEM TRA CHUYEN DU LIEU DAT." if report["ok"] else "KIEM TRA CHUYEN DU LIEU CHUA DAT.", file=output)
    (runtime / "migration-check.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
