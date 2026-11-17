"""Consolidate existing private JSON settings into .env without rotating credentials."""

import json
from pathlib import Path

from backend.app.mongodb_config import validate_mongodb_settings
from env_config import read_env, write_env
from project_config import ROOT, REQUIRED_KEYS
from scripts.backup_project import create_backup


def configure(root=ROOT):
    root = Path(root).resolve()
    destination = root / ".env"
    if destination.exists():
        values = read_env(destination)
        if any(not values.get(key, "").strip() for key in REQUIRED_KEYS):
            raise ValueError(".env da ton tai nhung thieu thong tin bat buoc; giu nguyen file de kiem tra.")
        if values.get("DATABASE_BACKEND") == "mongodb":
            validate_mongodb_settings(values)
        return {"created": False, "path": str(destination)}
    web = json.loads((root / "config.local.json").read_text(encoding="utf-8-sig"))
    if not isinstance(web, dict) or any(not isinstance(web.get(key), str) or not web[key].strip() for key in REQUIRED_KEYS):
        raise ValueError("Cau hinh web cu khong hop le; chua tao .env.")
    values = {key: web[key] for key in REQUIRED_KEYS}
    values["DEVICE_ID"] = web.get("DEVICE_ID", "ngoc-01")
    values["DATABASE_BACKEND"] = web.get("DATABASE_BACKEND", "sqlite")
    if values["DATABASE_BACKEND"] not in {"sqlite", "mongodb"}:
        raise ValueError("DATABASE_BACKEND cu khong hop le; chua tao .env.")
    if "DB_PATH" in web:
        values["DB_PATH"] = str(web["DB_PATH"])
    mongo_path = root / "mongodb.local.json"
    if mongo_path.exists():
        mongo = validate_mongodb_settings(json.loads(mongo_path.read_text(encoding="utf-8-sig")))
        values.update({key: str(value) for key, value in mongo.items()})
    elif values["DATABASE_BACKEND"] == "mongodb":
        raise ValueError("Thieu cau hinh MongoDB cu; chua tao .env.")
    backup, _ = create_backup(root)
    write_env(destination, values)
    return {"created": True, "path": str(destination), "backup": str(backup)}


def main():
    try:
        result = configure()
        print("DA TAO .env. Mat khau, khoa va database duoc giu nguyen." if result["created"] else ".env da ton tai; giu nguyen cac gia tri.")
        print("JSON cu duoc giu de tuong thich; sua cau hinh chinh trong .env.")
        return 0
    except (ValueError, OSError, RuntimeError):
        print("CHUA TAO DUOC .env. Kiem tra thu vien va cac file cau hinh rieng; khong dan mat khau vao log.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
