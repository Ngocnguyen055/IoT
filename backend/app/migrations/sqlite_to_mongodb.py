"""Copy a consistent SQLite snapshot without changing IDs or overwriting Atlas data."""

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sqlite3

from ..models import READING_FIELDS


class MigrationError(RuntimeError):
    pass


class MigrationConflict(MigrationError):
    pass


@dataclass(frozen=True)
class Snapshot:
    readings: tuple
    commands: tuple
    sequence: int

    @property
    def fingerprint(self):
        content = {"readings": self.readings, "commands": self.commands, "sequence": self.sequence}
        encoded = json.dumps(content, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


def read_snapshot(path):
    """Read one SQLite transaction; mode=ro never creates or changes the source."""
    path = Path(path).resolve()
    try:
        connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("BEGIN")
            if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise MigrationError("SQLite integrity check failed")
            columns = ",".join(("id", *READING_FIELDS))
            rows = connection.execute(f"SELECT {columns} FROM readings ORDER BY id").fetchall()
            readings = tuple({"_id": row["id"], **{key: row[key] for key in READING_FIELDS}} for row in rows)
            commands = tuple({"_id": row["device_id"], "cmd": row["cmd"]} for row in connection.execute("SELECT device_id,cmd FROM commands ORDER BY device_id"))
            row = connection.execute("SELECT seq FROM sqlite_sequence WHERE name='readings'").fetchone()
            sequence = row[0] if row else 0
        finally:
            connection.close()
    except sqlite3.Error:
        raise MigrationError("Cannot read the expected SQLite schema; source was not modified") from None
    if any(not isinstance(row["_id"], int) or isinstance(row["_id"], bool) or row["_id"] <= 0
           or not isinstance(row["ts"], int) for row in readings):
        raise MigrationError("SQLite readings must have positive integer IDs and integer timestamps")
    if any(not isinstance(row["_id"], str) or not row["_id"] or row["cmd"] not in {"NONE", "LOCATE"} for row in commands):
        raise MigrationError("SQLite commands contain an unsupported device or command")
    if not isinstance(sequence, int) or sequence < 0:
        raise MigrationError("SQLite readings sequence must be a nonnegative integer")
    snapshot = Snapshot(readings, commands, max(sequence, readings[-1]["_id"] if readings else 0))
    try:
        snapshot.fingerprint
    except (ValueError, TypeError):
        raise MigrationError("SQLite values cannot be represented without data loss") from None
    return snapshot


def _plan(snapshot, repository, session=None):
    """Check every existing row before writing; a partial matching import can resume."""
    missing = {}
    for name, source in (("readings", snapshot.readings), ("commands", snapshot.commands)):
        expected = {row["_id"]: row for row in source}
        found = set()
        for document in getattr(repository, name).find({}, session=session):
            key = document["_id"]
            valid_key = isinstance(key, int) and not isinstance(key, bool) if name == "readings" else isinstance(key, str)
            if not valid_key:
                raise MigrationConflict(f"Atlas {name} uses incompatible IDs")
            if key not in expected or document != expected[key]:
                raise MigrationConflict(f"Atlas {name} differs from SQLite; no rows were overwritten")
            found.add(key)
        missing[name] = [row for row in source if row["_id"] not in found]
    counter = repository.counters.find_one({"_id": "readings"}, session=session)
    if counter is not None and (not isinstance(counter.get("value"), int)
                                or isinstance(counter["value"], bool) or counter["value"] < 0):
        raise MigrationConflict("Atlas readings counter is invalid")
    return missing


def verify_snapshot(snapshot, repository, session=None):
    missing = _plan(snapshot, repository, session)
    if any(missing.values()):
        raise MigrationError("Atlas is missing SQLite rows")
    counter = repository.counters.find_one({"_id": "readings"}, session=session)
    if counter is None or counter["value"] < snapshot.sequence:
        raise MigrationError("Atlas counter would reuse an existing SQLite ID")
    return {"readings": len(snapshot.readings), "commands": len(snapshot.commands),
            "source_sequence": snapshot.sequence, "target_counter": counter["value"],
            "source_fingerprint": snapshot.fingerprint}


def migrate_snapshot(snapshot, repository):
    """Import all rows atomically. Repeating a matching import inserts nothing."""
    def copy(session):
        missing = _plan(snapshot, repository, session)
        if missing["readings"]:
            repository.readings.insert_many(missing["readings"], session=session)
        if missing["commands"]:
            repository.commands.insert_many(missing["commands"], session=session)
        repository.counters.update_one({"_id": "readings"}, {"$max": {"value": snapshot.sequence}}, upsert=True, session=session)
        verify_snapshot(snapshot, repository, session)
        return {"inserted_readings": len(missing["readings"]), "inserted_commands": len(missing["commands"])}

    inserted = repository._with_transaction(copy)
    return {**inserted, **verify_snapshot(snapshot, repository)}


def verify_read_models(sqlite_repository, mongodb_repository):
    """Compare the data returned to the dashboard and GPS history, without fake writes."""
    def normalized_dashboard(repository):
        data = repository.dashboard_snapshot()
        data["commands"] = sorted(data["commands"], key=lambda row: row["device_id"])
        return data

    expected = normalized_dashboard(sqlite_repository)
    if normalized_dashboard(mongodb_repository) != expected:
        raise MigrationError("MongoDB dashboard differs from the SQLite snapshot")
    devices = {row["device_id"] for row in expected["history"]}
    # Include devices older than the dashboard's 150-row window.
    with sqlite_repository.connect() as connection:
        devices.update(row[0] for row in connection.execute("SELECT DISTINCT device_id FROM readings"))
    for device in devices:
        if sqlite_repository.track_points(device, 0) != mongodb_repository.track_points(device, 0):
            raise MigrationError("MongoDB GPS history differs from the SQLite snapshot")
    return {"dashboard_matches": True, "gps_devices_checked": len(devices)}
