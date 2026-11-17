"""Persistent local credentials shared by the existing launchers and Flask app."""

import json
import os
from pathlib import Path
import secrets

from env_config import read_env


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.local.json"
REQUIRED_KEYS = ("ADMIN_PASSWORD", "DEVICE_KEY", "SESSION_SECRET")
CONFIG_KEYS = (*REQUIRED_KEYS, "DEVICE_ID", "DATABASE_BACKEND", "DB_PATH", "MONGODB_URI", "MONGODB_DATABASE", "MONGODB_TIMEOUT_MS")


def load_config(path=None):
    """Keep existing credentials; generate independent values on a new checkout."""
    path = Path(path) if path is not None else CONFIG_PATH
    if not path.exists():
        config = {
            "ADMIN_PASSWORD": "SOS-" + secrets.token_hex(6),
            "DEVICE_KEY": secrets.token_hex(32),
            "SESSION_SECRET": secrets.token_hex(32),
        }
        with path.open("x", encoding="utf-8") as handle:
            json.dump(config, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    config = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(config, dict):
        raise ValueError(f"Expected a JSON object in {path.name}")
    for name in REQUIRED_KEYS:
        if not isinstance(config.get(name), str) or not config[name].strip():
            raise ValueError(f"Missing or invalid {name} in {path.name}")
    return config


def dotenv_config(path=None):
    path = Path(path) if path is not None else CONFIG_PATH.with_name(".env")
    return {key: value for key, value in read_env(path).items() if key in CONFIG_KEYS}


def application_config(path=None):
    """Process environment > .env > legacy JSON; do not mutate os.environ."""
    path = Path(path) if path is not None else CONFIG_PATH
    # Fully supplied deployment credentials also isolate tests from local files.
    explicit = all(os.environ.get(name) for name in REQUIRED_KEYS)
    dotenv = {} if explicit else dotenv_config(path.with_name(".env"))
    process = {key: os.environ[key] for key in CONFIG_KEYS if key in os.environ}
    supplied = {**dotenv, **process}
    local = {}
    if not explicit and path.exists():
        local = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(local, dict):
            raise ValueError(f"Expected a JSON object in {path.name}")
    elif not explicit and not all(supplied.get(name) for name in REQUIRED_KEYS):
        local = load_config(path)
    result = {**local, **dotenv, **process}
    for name in REQUIRED_KEYS:
        if not isinstance(result.get(name), str) or not result[name].strip():
            raise ValueError(f"Missing or invalid {name} in application configuration")
    return result
