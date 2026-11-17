"""Persistent local credentials shared by the existing launchers and Flask app."""

import json
import os
from pathlib import Path
import secrets


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.local.json"
REQUIRED_KEYS = ("ADMIN_PASSWORD", "DEVICE_KEY", "SESSION_SECRET")


def load_config():
    """Keep existing credentials; generate independent values on a new checkout."""
    if not CONFIG_PATH.exists():
        config = {
            "ADMIN_PASSWORD": "SOS-" + secrets.token_hex(6),
            "DEVICE_KEY": secrets.token_hex(32),
            "SESSION_SECRET": secrets.token_hex(32),
        }
        with CONFIG_PATH.open("x", encoding="utf-8") as handle:
            json.dump(config, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))
    if not isinstance(config, dict):
        raise ValueError(f"Expected a JSON object in {CONFIG_PATH.name}")
    for name in REQUIRED_KEYS:
        if not isinstance(config.get(name), str) or not config[name].strip():
            raise ValueError(f"Missing or invalid {name} in {CONFIG_PATH.name}")
    return config


def application_config():
    """Allow isolated tests/deployments to supply all credentials via environment."""
    local = {} if all(os.environ.get(name) for name in REQUIRED_KEYS) else load_config()
    return {name: os.environ.get(name) or local[name] for name in REQUIRED_KEYS}
