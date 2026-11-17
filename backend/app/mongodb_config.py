"""Read and validate private MongoDB settings without opening a network connection."""

import json
from pathlib import Path
import re
from urllib.parse import parse_qs, urlsplit

from project_config import ROOT


CONFIG_PATH = ROOT / "mongodb.local.json"


def validate_mongodb_settings(settings):
    uri = settings.get("MONGODB_URI", "")
    if not isinstance(uri, str):
        raise ValueError("MONGODB_URI must be a MongoDB connection string")
    uri = uri.strip()
    try:
        parsed = urlsplit(uri)
        if (parsed.scheme not in {"mongodb", "mongodb+srv"} or not parsed.hostname
                or any(character.isspace() or character in "<>" for character in uri)):
            raise ValueError
        options = {name.lower(): values for name, values in parse_qs(parsed.query).items()}
        insecure = ("tlsinsecure", "tlsallowinvalidcertificates", "tlsallowinvalidhostnames")
        if any(value.lower() in {"true", "1"} for name in insecure for value in options.get(name, [])):
            raise ValueError
        if parsed.scheme == "mongodb+srv" and any(value.lower() in {"false", "0"} for name in ("tls", "ssl") for value in options.get(name, [])):
            raise ValueError
    except ValueError:
        raise ValueError("Invalid MONGODB_URI; use the Atlas Drivers URI and keep TLS verification enabled") from None
    database = settings.get("MONGODB_DATABASE", "iot_sos")
    if (not isinstance(database, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,62}", database)
            or database.lower() in {"admin", "config", "local"}):
        raise ValueError("MONGODB_DATABASE must be a dedicated application database name")
    try:
        timeout = int(settings.get("MONGODB_TIMEOUT_MS", 5000))
    except (TypeError, ValueError, OverflowError):
        raise ValueError("MONGODB_TIMEOUT_MS must be between 1000 and 30000") from None
    if not 1000 <= timeout <= 30000:
        raise ValueError("MONGODB_TIMEOUT_MS must be between 1000 and 30000")
    return {"MONGODB_URI": uri, "MONGODB_DATABASE": database, "MONGODB_TIMEOUT_MS": timeout}


def load_mongodb_settings(path=None):
    path = Path(path) if path is not None else CONFIG_PATH
    if not path.exists():
        raise ValueError("Missing mongodb.local.json; run Tao-cau-hinh-MongoDB.cmd first")
    settings = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(settings, dict):
        raise ValueError("Expected a JSON object in mongodb.local.json")
    return validate_mongodb_settings(settings)
