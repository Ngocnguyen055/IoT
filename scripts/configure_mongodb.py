"""Save Atlas credentials locally without changing the active web database."""

from datetime import datetime, timezone
import getpass
import json
from pathlib import Path
import shutil
from urllib.parse import quote_plus

from backend.app.mongodb_config import CONFIG_PATH, validate_mongodb_settings
from project_config import ROOT
from env_config import update_env


def complete_atlas_uri(uri, *, username=None, password=None):
    uri = uri.strip()
    for placeholder in ("<db_username>", "<username>"):
        if placeholder in uri:
            if not username:
                raise ValueError("Database username is required")
            uri = uri.replace(placeholder, quote_plus(username))
    for placeholder in ("<db_password>", "<password>"):
        if placeholder in uri:
            if not password:
                raise ValueError("Database password is required")
            uri = uri.replace(placeholder, quote_plus(password))
    if not uri.startswith("mongodb+srv://"):
        raise ValueError("Use the mongodb+srv Atlas connection string from Connect > Drivers")
    return validate_mongodb_settings({"MONGODB_URI": uri})["MONGODB_URI"]


def save_settings(settings, destination=CONFIG_PATH):
    destination = Path(destination)
    settings = validate_mongodb_settings(settings)
    env = ROOT / ".env"
    if destination.resolve() == CONFIG_PATH.resolve() and env.exists():
        backups = ROOT / ".runtime" / "backups"
        backups.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        shutil.copy2(env, backups / ("env-" + stamp + ".env"))
        update_env(env, settings)
        return
    if destination.exists():
        backups = ROOT / ".runtime" / "backups"
        backups.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        shutil.copy2(destination, backups / ("mongodb-config-" + stamp + ".json"))
    temporary = destination.with_name(destination.name + ".tmp")
    temporary.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    temporary.replace(destination)


def main():
    print("Lay URI tu MongoDB Atlas > Connect > Drivers > Python.")
    print("Noi dung URI/mat khau se duoc an khi nhap; ban van co the dan bang Ctrl+V.")
    uri = getpass.getpass("Dan URI Atlas: ")
    username = input("Ten database user: ").strip() if any(value in uri for value in ("<db_username>", "<username>")) else None
    password = getpass.getpass("Mat khau DATABASE USER (khong phai mat khau tai khoan Atlas): ") if any(value in uri for value in ("<db_password>", "<password>")) else None
    uri = complete_atlas_uri(uri, username=username, password=password)
    database = input("Ten database ung dung [iot_sos]: ").strip() or "iot_sos"
    save_settings({"MONGODB_URI": uri, "MONGODB_DATABASE": database})
    print("DA LUU CAU HINH vao .env neu co, hoac mongodb.local.json.")
    print("Backend dang dung duoc giu nguyen. Chay Kiem-tra-MongoDB.cmd de thu Atlas.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as error:
        print("LOI CAU HINH:", str(error))
        raise SystemExit(1)
