"""Back up source, private configuration and a consistent SQLite snapshot locally."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess


ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRECTORIES = {".git", ".venv", ".runtime", "__pycache__", "node_modules"}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def create_backup(root=ROOT):
    root = Path(root).resolve()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    destination = root / ".runtime" / "backups" / ("snapshot-" + stamp)
    destination.mkdir(parents=True)
    manifest = {"created_at_utc": stamp, "git_commit": None, "files": [], "database": None}
    try:
        result = subprocess.run(
            ["git", "-c", f"safe.directory={root.as_posix()}", "rev-parse", "HEAD"],
            cwd=root, capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            manifest["git_commit"] = result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    for source in root.rglob("*"):
        relative = source.relative_to(root)
        if (EXCLUDED_DIRECTORIES.intersection(relative.parts) or not source.is_file()
                or source.suffix in {".pyc", ".log"} or source.name.startswith("iot_ngoc.sqlite3")):
            continue
        target = destination / "files" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        manifest["files"].append({"path": relative.as_posix(), "sha256": digest(target)})
    source_db = root / "iot_ngoc.sqlite3"
    if source_db.exists():
        target_db = destination / "iot_ngoc.sqlite3"
        source = sqlite3.connect(source_db.as_uri() + "?mode=ro", uri=True)
        target = sqlite3.connect(target_db)
        try:
            source.backup(target)
            if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise RuntimeError("SQLite backup integrity check failed")
            tables = {row[0] for row in target.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            counts = {name: target.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
                      for name in ("readings", "commands") if name in tables}
        finally:
            target.close()
            source.close()
        manifest["database"] = {"path": "iot_ngoc.sqlite3", "sha256": digest(target_db), "counts": counts}
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return destination, manifest


if __name__ == "__main__":
    destination, manifest = create_backup()
    print("Backup:", destination)
    print("Source/config files:", len(manifest["files"]))
    if manifest["database"]:
        print("SQLite integrity: OK; counts:", manifest["database"]["counts"])
