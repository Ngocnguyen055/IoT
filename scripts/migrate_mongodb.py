"""Back up, verify and migrate the stopped local website to MongoDB Atlas."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import sys

from pymongo.errors import PyMongoError

from backend.app import create_app
from backend.app.config import build_config
from backend.app.migrations.sqlite_to_mongodb import MigrationError, migrate_snapshot, read_snapshot, verify_read_models
from backend.app.repositories.errors import DatabaseUnavailable
from backend.app.repositories.factory import build_repository
from backend.app.repositories.sqlite import SQLiteRepository
from project_config import ROOT, REQUIRED_KEYS, application_config
from env_config import update_env
from scripts.backup_project import create_backup
from scripts.check_mongodb import Tee
from scripts.check_migration import run_checks


def require_stopped_web(port=5000):
    with socket.socket() as connection:
        connection.settimeout(1)
        if connection.connect_ex(("127.0.0.1", port)) == 0:
            raise MigrationError("Web con dang chay. Dung bang Ctrl+C hoac Dung-web.cmd roi chay lai.")


def save_report(root, report):
    path = root / ".runtime" / "migration-report.json"
    path.parent.mkdir(exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def enable_mongodb(path, original):
    if path.read_bytes() != original:
        raise MigrationError("Cau hinh web vua thay doi; chua bat MongoDB. Chay lai de doi chieu.")
    if path.name == ".env":
        update_env(path, {"DATABASE_BACKEND": "mongodb"}, expected=original)
        return
    settings = json.loads(original.decode("utf-8-sig"))
    if not isinstance(settings, dict) or any(not isinstance(settings.get(key), str) or not settings[key].strip() for key in REQUIRED_KEYS):
        raise MigrationError("Cau hinh web khong hop le; chua bat MongoDB.")
    settings["DATABASE_BACKEND"] = "mongodb"
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(settings, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def verify_web(config, settings, repository, source, root):
    expected = source.dashboard_snapshot()
    app = create_app({**config, **settings, "DATABASE_BACKEND": "mongodb", "DB_PATH": str(root / "iot_ngoc.sqlite3")}, repository=repository)
    client = app.test_client()
    if client.post("/login", data={"password": config["ADMIN_PASSWORD"]}).status_code != 302:
        raise MigrationError("Khong dang nhap duoc web voi cau hinh MongoDB.")
    response = client.get("/api/status")
    if response.status_code != 200 or any(response.json.get(key) != expected[key] for key in ("latest", "history", "alerts", "last_location")):
        raise MigrationError("API web khong khop ban SQLite; chua bat MongoDB.")
    if sorted(response.json["commands"], key=lambda row: row["device_id"]) != sorted(expected["commands"], key=lambda row: row["device_id"]):
        raise MigrationError("Lenh cho tren API web khong khop SQLite.")


def cutover(root, settings, output=sys.stdout):
    """Only activate after a consistent backup, exact comparison and HTTP read checks."""
    root = Path(root).resolve()
    require_stopped_web()
    config_path = root / ".env" if (root / ".env").exists() else root / "config.local.json"
    original_config = config_path.read_bytes()
    config = application_config(root / "config.local.json")
    backup, _ = create_backup(root)
    print("Ban sao luu:", backup, file=output, flush=True)
    snapshot = read_snapshot(backup / "iot_ngoc.sqlite3")
    source = SQLiteRepository(backup / "iot_ngoc.sqlite3")
    report = {"ok": False, "state": "backed_up", "checked_at_utc": datetime.now(timezone.utc).isoformat(),
              "backup": str(backup), "source_fingerprint": snapshot.fingerprint,
              "readings": len(snapshot.readings), "commands": len(snapshot.commands)}
    save_report(root, report)
    repository = None
    try:
        repository = build_repository({**settings, "DATABASE_BACKEND": "mongodb"})
        repository.initialize()
        report.update(migrate_snapshot(snapshot, repository))
        report.update(verify_read_models(source, repository))
        verify_web(config, settings, repository, source, root)
        if read_snapshot(root / "iot_ngoc.sqlite3").fingerprint != snapshot.fingerprint:
            raise MigrationError("SQLite vua nhan them/thay doi du lieu; chua bat MongoDB. Dung web va chay lai.")
        require_stopped_web()
        report["state"] = "verified"
        save_report(root, report)
        enable_mongodb(config_path, original_config)
        report.update(ok=True, state="mongodb_enabled", web_api_matches=True)
        save_report(root, report)
        return report
    except Exception:
        report["state"] = "failed_before_activation" if config_path.read_bytes() == original_config else "configuration_changed"
        save_report(root, report)
        raise
    finally:
        if repository is not None:
            repository.close()


def main():
    runtime = ROOT / ".runtime"
    runtime.mkdir(exist_ok=True)
    with (runtime / "migration.log").open("w", encoding="utf-8") as log:
        output = Tee(sys.stdout, log)
        try:
            current = build_config()
            if current["DATABASE_BACKEND"] == "mongodb":
                from scripts.check_active_mongodb import check_active
                check_active()
                print("MongoDB da duoc bat. Khong nhap lai ban SQLite cu; du lieu moi tiep tuc o Atlas.", file=output)
                return 0
            require_stopped_web()
            target = build_config({"DATABASE_BACKEND": "mongodb"})
            if Path(current["DB_PATH"]).resolve() != ROOT / "iot_ngoc.sqlite3":
                raise MigrationError("DB_PATH dang tro den SQLite khac; can doi chieu duong dan truoc khi chuyen.")
            # An environment override must not silently keep app.py on SQLite after activation.
            if os.environ.get("DATABASE_BACKEND") not in {None, "mongodb"}:
                raise MigrationError("Go bien moi truong DATABASE_BACKEND dang ep SQLite truoc khi chuyen.")
            settings = {key: target[key] for key in ("MONGODB_URI", "MONGODB_DATABASE", "MONGODB_TIMEOUT_MS")}
            print("Buoc 1: kiem tra chuyen du lieu va rollback tren database Atlas tam...", file=output)
            verification = run_checks(settings, output)
            (runtime / "migration-check.json").write_text(json.dumps({**verification, "checked_at_utc": datetime.now(timezone.utc).isoformat()}, indent=2), encoding="utf-8")
            if not verification["ok"]:
                print("KIEM TRA CHUYEN DU LIEU CHUA DAT. Chua chuyen du lieu that.", file=output)
                return 1
            print("Buoc 2: sao luu, chuyen du lieu that va doi chieu...", file=output)
            report = cutover(ROOT, settings, output)
            print("So do:", report["readings"], "| Lenh:", report["commands"], "| Chen moi:", report["inserted_readings"], file=output)
            print("DA CHUYEN SANG MONGODB. Mo Chay-web.cmd de xem lai du lieu.", file=output)
            return 0
        except MigrationError as error:
            print("CHUA CHUYEN XONG:", str(error), file=output)
        except (PyMongoError, DatabaseUnavailable):
            print("CHUA CHUYEN XONG: khong ket noi/ghi duoc Atlas. Kiem tra mang, IP va database user roi chay lai.", file=output)
        except (ValueError, OSError):
            print("CHUA CHUYEN XONG: khong doc/ghi duoc cau hinh hoac ban sao luu. Xem dung luong dia va quyen thu muc.", file=output)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
