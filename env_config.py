"""Read private dotenv files without changing the process environment."""

import json
from pathlib import Path
import re


def read_env(path):
    path = Path(path)
    if not path.exists():
        return {}
    try:
        from dotenv import dotenv_values
    except ImportError:
        raise RuntimeError("Run Cai-dat.cmd to install python-dotenv") from None
    # Passwords and URI strings are literal, even when they contain ${...}.
    values = dotenv_values(path, encoding="utf-8-sig", interpolate=False)
    return {key: value for key, value in values.items() if value is not None}


def write_env(path, values, *, expected=None):
    """Check a round trip before replacing a private file atomically."""
    from dotenv import dotenv_values
    from io import StringIO

    path = Path(path)
    if path.exists():
        if expected is None or path.read_bytes() != expected:
            raise ValueError("The .env file changed; existing values were not overwritten")
    elif expected is not None:
        raise ValueError("The .env file was removed during the update")
    if any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key) or not isinstance(value, str) for key, value in values.items()):
        raise ValueError("Environment settings must use valid names and string values")
    lines = ["# Private local configuration. Do not commit this file.", "# Process environment variables take priority over these values."]
    lines.extend(f"{key}={json.dumps(value, ensure_ascii=False)}" for key, value in values.items())
    content = "\n".join(lines) + "\n"
    if dict(dotenv_values(stream=StringIO(content), interpolate=False)) != values:
        raise ValueError("Cannot encode the configuration in .env without changing values")
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def update_env(path, updates, *, expected=None):
    path = Path(path)
    before = path.read_bytes() if expected is None else expected
    write_env(path, {**read_env(path), **{key: str(value) for key, value in updates.items()}}, expected=before)
