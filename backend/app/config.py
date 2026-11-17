"""Resolve runtime settings without binding them to a global Flask instance."""

import os
from pathlib import Path

from project_config import ROOT, REQUIRED_KEYS, application_config
from .mongodb_config import load_mongodb_settings, validate_mongodb_settings


def build_config(overrides=None):
    overrides = dict(overrides or {})
    for name in REQUIRED_KEYS:
        if name in overrides and (not isinstance(overrides[name], str) or not overrides[name].strip()):
            raise ValueError(f"Missing or invalid {name}")

    settings = {} if all(name in overrides for name in REQUIRED_KEYS) else dict(application_config())
    settings.update(overrides)
    settings["SECRET_KEY"] = settings["SESSION_SECRET"]

    def setting(name, default=None):
        if name in overrides:
            return overrides[name]
        return os.environ.get(name, settings.get(name, default))

    backend = setting("DATABASE_BACKEND", "sqlite")
    if not isinstance(backend, str) or backend not in {"sqlite", "mongodb"}:
        raise ValueError("DATABASE_BACKEND must be sqlite or mongodb")
    settings["DATABASE_BACKEND"] = backend
    if backend == "mongodb":
        keys = ("MONGODB_URI", "MONGODB_DATABASE", "MONGODB_TIMEOUT_MS")
        mongo = {name: setting(name) for name in keys}
        mongo = {name: value for name, value in mongo.items() if value is not None}
        if not mongo.get("MONGODB_URI"):
            mongo = {**load_mongodb_settings(), **mongo}
        settings.update(validate_mongodb_settings(mongo))

    database = setting("DB_PATH", ROOT / "iot_ngoc.sqlite3")
    if not isinstance(database, (str, os.PathLike)) or not str(database).strip() or str(database) == ":memory:":
        raise ValueError("DB_PATH must be a SQLite file path; use a temporary file for tests")
    database = Path(database)
    if not database.is_absolute():
        database = ROOT / database
    settings["DB_PATH"] = str(database)
    return settings
