"""SQLite persistence preserving the existing schema and transaction boundaries."""

from contextlib import contextmanager
import sqlite3

from ..alerts import ALERT_EVENTS, ALERT_PAGE_SIZE, HOME_ALERT_LIMIT, alert_page_result


EVENT_SQL = "event IN (" + ",".join("'" + event + "'" for event in ALERT_EVENTS) + ")"


class SQLiteRepository:
    def __init__(self, database):
        self.database = database

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.database, timeout=15)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def initialize(self):
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS readings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, device_id TEXT NOT NULL, ts INTEGER NOT NULL,
                    event TEXT NOT NULL, lat REAL, lon REAL, gps_satellites INTEGER,
                    bpm INTEGER, spo2 INTEGER, battery_pct REAL, battery_voltage REAL, current_ma REAL
                );
                CREATE INDEX IF NOT EXISTS idx_readings_device_ts ON readings(device_id, ts);
                CREATE TABLE IF NOT EXISTS commands (
                    device_id TEXT PRIMARY KEY, cmd TEXT NOT NULL DEFAULT 'NONE'
                );
            """)
            db.execute(f"CREATE INDEX IF NOT EXISTS idx_readings_alerts_id ON readings(id DESC) WHERE {EVENT_SQL}")
            db.execute("CREATE INDEX IF NOT EXISTS idx_readings_location_id ON readings(id DESC) WHERE lat IS NOT NULL AND lon IS NOT NULL")
            db.execute("CREATE INDEX IF NOT EXISTS idx_readings_device_location_id ON readings(device_id,id DESC) WHERE lat IS NOT NULL AND lon IS NOT NULL")

    def save_reading(self, reading, timestamp):
        with self.connect() as db:
            db.execute("""
                INSERT INTO readings(device_id,ts,event,lat,lon,gps_satellites,bpm,spo2,battery_pct,battery_voltage,current_ma)
                VALUES(?,?,?,?,?,?,?,?,?,?,?)
            """, (reading["device_id"], timestamp, reading["event"], reading["lat"], reading["lon"],
                  reading["gps_satellites"], reading["bpm"], reading["spo2"], reading["battery_pct"],
                  reading["battery_voltage"], reading["current_ma"]))
            if reading["event"] == "remote":
                db.execute("UPDATE commands SET cmd='NONE' WHERE device_id=?", (reading["device_id"],))

    def pending_command(self, device_id):
        with self.connect() as db:
            row = db.execute("SELECT cmd FROM commands WHERE device_id=?", (device_id,)).fetchone()
        return row["cmd"] if row else "NONE"

    def queue_locate(self, device_id):
        with self.connect() as db:
            db.execute("""
                INSERT INTO commands(device_id,cmd) VALUES(?, 'LOCATE')
                ON CONFLICT(device_id) DO UPDATE SET cmd='LOCATE'
            """, (device_id,))

    def dashboard_snapshot(self, *, compact=False):
        with self.connect() as db:
            history = [dict(row) for row in db.execute("SELECT * FROM readings ORDER BY id DESC LIMIT ?", (1 if compact else 150,))]
            location = db.execute("""
                SELECT device_id,lat,lon,ts FROM readings
                WHERE lat IS NOT NULL AND lon IS NOT NULL ORDER BY id DESC LIMIT 1
            """).fetchone()
            alerts = [dict(row) for row in db.execute(
                f"SELECT * FROM readings WHERE {EVENT_SQL} ORDER BY id DESC LIMIT ?", (HOME_ALERT_LIMIT if compact else 20,)
            )]
            commands = [dict(row) for row in db.execute("SELECT device_id,cmd FROM commands")]
        result = {
            "latest": history[0] if history else None,
            "history": history,
            "last_location": dict(location) if location else None,
            "alerts": alerts,
            "commands": commands,
        }
        if compact:
            result.pop("history")
        return result

    def alert_page(self, snapshot=None, before=None, after=None):
        clauses, parameters = [EVENT_SQL], []
        for operator, value in (("<=", snapshot), ("<", before), (">", after)):
            if value is not None:
                clauses.append(f"id {operator} ?")
                parameters.append(value)
        direction = "ASC" if after is not None else "DESC"
        with self.connect() as db:
            rows = [dict(row) for row in db.execute(f"SELECT * FROM readings WHERE {' AND '.join(clauses)} ORDER BY id {direction} LIMIT ?", (*parameters, ALERT_PAGE_SIZE + 1))]
            extra = len(rows) > ALERT_PAGE_SIZE
            rows = rows[:ALERT_PAGE_SIZE]
            if after is not None:
                rows.reverse()
            if snapshot is None:
                snapshot = rows[0]["id"] if rows else 0
            has_previous = extra if after is not None else False
            has_next = extra if after is None else False
            if rows and before is not None:
                has_previous = db.execute(f"SELECT 1 FROM readings WHERE {EVENT_SQL} AND id > ? AND id <= ? LIMIT 1", (rows[0]["id"], snapshot)).fetchone() is not None
            if rows and after is not None:
                has_next = db.execute(f"SELECT 1 FROM readings WHERE {EVENT_SQL} AND id < ? AND id <= ? LIMIT 1", (rows[-1]["id"], snapshot)).fetchone() is not None
        return alert_page_result(rows, snapshot, has_previous=has_previous, has_next=has_next)

    def track_points(self, device_id, since):
        with self.connect() as db:
            rows = db.execute("""
                SELECT id,ts,lat,lon,gps_satellites,event FROM readings
                WHERE device_id=? AND ts>=? AND lat IS NOT NULL AND lon IS NOT NULL
                ORDER BY id DESC LIMIT 1000
            """, (device_id, since)).fetchall()
        return [dict(row) for row in reversed(rows)]
