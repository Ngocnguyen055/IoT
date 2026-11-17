"""Create or verify the application's MongoDB collections, indexes and validators."""

import argparse
from datetime import datetime, timezone
import json
import sys

from pymongo.errors import OperationFailure, PyMongoError

from backend.app.config import build_config
from backend.app.database import collection_options, initialize_database
from backend.app.repositories.errors import DatabaseUnavailable
from backend.app.repositories.factory import build_repository
from project_config import ROOT
from scripts.check_mongodb import Tee
from scripts.check_schema import run_checks
from scripts.migrate_mongodb import require_stopped_web


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Only read and verify existing schema; create nothing")
    args = parser.parse_args()
    runtime = ROOT / ".runtime"
    runtime.mkdir(exist_ok=True)
    report = {"ok": False, "checked_at_utc": datetime.now(timezone.utc).isoformat()}
    repository = None
    with (runtime / "db-init.log").open("w", encoding="utf-8") as log:
        output = Tee(sys.stdout, log)
        try:
            settings = build_config({"DATABASE_BACKEND": "mongodb"})
            if not args.check:
                require_stopped_web()
                print("Kiem tra model/schema tren Atlas tam...", file=output)
                report["verification"] = run_checks(settings, output)
                (runtime / "schema-check.json").write_text(json.dumps(report["verification"], indent=2), encoding="utf-8")
                if not report["verification"]["ok"]:
                    print("KIEM TRA SCHEMA CHUA DAT. Chua sua database ung dung.", file=output)
                    return 1
            repository = build_repository(settings)
            repository.client.admin.command("ping")
            if not args.check:
                previous = {"database": settings["MONGODB_DATABASE"], "collections": collection_options(repository.database)}
                stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
                (runtime / ("db-schema-before-" + stamp + ".json")).write_text(json.dumps(previous, indent=2), encoding="utf-8")
            report.update(initialize_database(repository, check_only=args.check))
            print("DATABASE:", report["database"], "| COLLECTIONS:", ", ".join(report["collections"]), file=output)
            print("DOCUMENTS:", report["counts"], file=output)
            print("KIEM TRA DATABASE DAT." if args.check else "KHOI TAO MONGODB DAT. Du lieu cu duoc giu nguyen.", file=output)
            return 0
        except OperationFailure as error:
            report["mongo_code"] = error.code
            if error.code == 13:
                print("Thieu quyen quan ly schema. Them role dbAdmin cho database", settings["MONGODB_DATABASE"], "trong Atlas Database Access, roi chay lai.", file=output)
            else:
                print("Atlas tu choi thao tac. MongoDB error code:", error.code, file=output)
        except (DatabaseUnavailable, PyMongoError):
            print("Chua ket noi duoc Atlas. Kiem tra mang, IP va database user.", file=output)
        except (ValueError, RuntimeError) as error:
            print("CHUA DAT:", str(error), file=output)
        except OSError:
            print("Khong doc/ghi duoc cau hinh hoac bao cao tren may.", file=output)
        finally:
            if repository is not None:
                repository.close()
            (runtime / "db-init-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
