"""Read-only application checks after cutover; never insert simulated telemetry."""

import json
from pathlib import Path

from pymongo.errors import PyMongoError

from backend.app import create_app
from backend.app.config import build_config
from backend.app.migrations.sqlite_to_mongodb import MigrationError, read_snapshot
from backend.app.repositories.errors import DatabaseUnavailable
from project_config import ROOT


def check_active():
    settings = build_config()
    if settings["DATABASE_BACKEND"] != "mongodb":
        raise MigrationError("Web chua duoc cau hinh dung MongoDB.")
    report_path = ROOT / ".runtime" / "migration-report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("ok") is not True or report.get("state") != "mongodb_enabled":
        raise MigrationError("Chua co bao cao chuyen du lieu thanh cong.")
    backup = Path(report["backup"]).resolve()
    if not backup.is_relative_to((ROOT / ".runtime/backups").resolve()):
        raise MigrationError("Duong dan sao luu khong thuoc du an.")
    snapshot = read_snapshot(backup / "iot_ngoc.sqlite3")
    if snapshot.fingerprint != report.get("source_fingerprint"):
        raise MigrationError("Ban sao luu khong khop bao cao chuyen du lieu.")
    app = create_app(settings)
    repository = app.extensions["sos_repository"]
    try:
        expected = {row["_id"]: row for row in snapshot.readings}
        imported = list(repository.readings.find({"_id": {"$in": list(expected)}}))
        if len(imported) != len(expected) or any(row != expected[row["_id"]] for row in imported):
            raise MigrationError("Cac so do da chuyen khong con khop ban sao luu.")
        client = app.test_client()
        if client.post("/login", data={"password": app.config["ADMIN_PASSWORD"]}).status_code != 302 or client.get("/api/status").status_code != 200:
            raise MigrationError("API web MongoDB chua hoat dong.")
        return {"ok": True, "backend": "mongodb", "imported_readings_verified": len(imported),
                "total_readings": repository.readings.count_documents({}), "web_api_ok": True}
    finally:
        repository.close()


def main():
    try:
        result = check_active()
        (ROOT / ".runtime/mongodb-active-check.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        print("MONGODB DANG HOAT DONG. So do da doi chieu:", result["imported_readings_verified"], "| Tong so do:", result["total_readings"])
        return 0
    except (MigrationError, ValueError, OSError, KeyError):
        print("CHUA XAC NHAN DUOC MONGODB. Kiem tra .runtime/migration-report.json va cau hinh tren may.")
    except (PyMongoError, DatabaseUnavailable):
        print("CHUA KET NOI DUOC MONGODB. Kiem tra mang, IP va database user.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
