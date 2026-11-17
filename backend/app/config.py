"""Resolve runtime settings without binding them to a global Flask instance."""

import os
from pathlib import Path

from project_config import ROOT, REQUIRED_KEYS, application_config


def build_config(overrides=None):
    overrides = dict(overrides or {})
    for name in REQUIRED_KEYS:
        if name in overrides and (not isinstance(overrides[name], str) or not overrides[name].strip()):
            raise ValueError(f"Missing or invalid {name}")

    settings = {} if all(name in overrides for name in REQUIRED_KEYS) else application_config()
    settings.update(overrides)
    settings["SECRET_KEY"] = settings["SESSION_SECRET"]

    database = settings.get("DB_PATH", os.environ.get("DB_PATH") or ROOT / "iot_ngoc.sqlite3")
    if not isinstance(database, (str, os.PathLike)) or not str(database).strip() or str(database) == ":memory:":
        raise ValueError("DB_PATH must be a SQLite file path; use a temporary file for tests")
    database = Path(database)
    if not database.is_absolute():
        database = ROOT / database
    settings["DB_PATH"] = str(database)
    return settings
