"""Characterize the current HTTP contract using isolated SQLite databases."""

import importlib.util
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
TEST_CONFIG = {
    "ADMIN_PASSWORD": "test-admin-only",
    "DEVICE_KEY": "test-device-only",
    "SESSION_SECRET": "test-session-only",
}


class ApiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (ROOT / ".runtime").mkdir(exist_ok=True)
        cls.temporary = tempfile.TemporaryDirectory(prefix="api-tests-", dir=ROOT / ".runtime")
        cls.directory = Path(cls.temporary.name)
        spec = importlib.util.spec_from_file_location("sos_contract_under_test", ROOT / "app.py")
        cls.server = importlib.util.module_from_spec(spec)
        with patch.dict(os.environ, {**TEST_CONFIG, "DB_PATH": str(cls.directory / "initial.sqlite3")}):
            spec.loader.exec_module(cls.server)
        cls.server.app.config.update(TESTING=True)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def setUp(self):
        self.server.DB = str(self.directory / (self._testMethodName + ".sqlite3"))
        self.server.init_db()
        self.client = self.server.app.test_client()
        self.headers = {"X-Device-Key": TEST_CONFIG["DEVICE_KEY"]}

    def login(self):
        response = self.client.post("/login", data={"password": TEST_CONFIG["ADMIN_PASSWORD"]})
        self.assertEqual(response.status_code, 302)

    def post_reading(self, **changes):
        payload = {
            "device_id": "ngoc-01", "event": "telemetry",
            "lat": None, "lon": None, "gps_satellites": 0,
            "bpm": 72, "spo2": 98, "battery_pct": 80.4,
            "battery_voltage": 4.004, "current_ma": 0.6,
        }
        payload.update(changes)
        return self.client.post("/api/device/telemetry", json=payload, headers=self.headers)

    def seed(self, rows):
        with self.server.connect() as db:
            db.executemany(
                "INSERT INTO readings(device_id,ts,event,lat,lon) VALUES(?,?,?,?,?)", rows
            )

    def test_access_boundaries(self):
        self.assertEqual(self.client.get("/").headers["Location"], "/login")
        self.assertEqual(self.client.get("/login").status_code, 200)
        for path in ("/api/status", "/api/track"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.json, {"error": "login required"})
        self.assertEqual(self.client.post("/api/command", json={}).status_code, 401)
        for headers in ({}, {"X-Device-Key": "wrong-key"}):
            with self.subTest(headers=headers):
                self.assertEqual(self.client.get("/api/device/command", headers=headers).status_code, 401)
                self.assertEqual(self.client.post("/api/device/telemetry", json={}, headers=headers).status_code, 401)

    def test_login_dashboard_static_files_and_logout(self):
        self.assertEqual(self.client.post("/login", data={"password": "wrong"}).status_code, 401)
        self.login()
        self.assertEqual(self.client.get("/").status_code, 200)
        for path in ("/static/app.js", "/static/style.css"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            response.close()
        self.assertEqual(self.client.post("/logout").headers["Location"], "/login")
        self.assertEqual(self.client.get("/api/status").status_code, 401)

    def test_empty_dashboard(self):
        self.login()
        response = self.client.get("/api/status")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json), {"latest", "history", "last_location", "alerts", "commands", "now"})
        for field in ("history", "alerts", "commands"):
            self.assertEqual(response.json[field], [])
        self.assertIsNone(response.json["latest"])
        self.assertIsNone(response.json["last_location"])

    def test_reading_round_trip_and_server_timestamp(self):
        before = int(time.time())
        response = self.post_reading(ts=1)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"ok": True})
        self.login()
        reading = self.client.get("/api/status").json["latest"]
        self.assertEqual(reading["device_id"], "ngoc-01")
        self.assertEqual(reading["bpm"], 72)
        self.assertEqual(reading["spo2"], 98)
        self.assertAlmostEqual(reading["battery_pct"], 80.4)
        self.assertAlmostEqual(reading["battery_voltage"], 4.004)
        self.assertAlmostEqual(reading["current_ma"], 0.6)
        self.assertGreaterEqual(reading["ts"], before)
        self.assertLessEqual(reading["ts"], int(time.time()))

    def test_missing_values_stay_null_and_zero_is_preserved(self):
        response = self.client.post("/api/device/telemetry", json={"device_id": "ngoc-01"}, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.login()
        reading = self.client.get("/api/status").json["latest"]
        for field in ("lat", "lon", "bpm", "spo2", "battery_pct", "battery_voltage", "current_ma", "gps_satellites"):
            self.assertIsNone(reading[field])
        self.assertEqual(self.post_reading(battery_pct=0, current_ma=0).status_code, 200)
        reading = self.client.get("/api/status").json["latest"]
        self.assertEqual(reading["battery_pct"], 0)
        self.assertEqual(reading["current_ma"], 0)

    def test_all_event_types_and_alerts(self):
        events = ("telemetry", "button", "high_bpm", "low_spo2", "remote")
        for event in events:
            self.assertEqual(self.post_reading(event=event).status_code, 200)
        self.login()
        status = self.client.get("/api/status").json
        self.assertEqual([r["event"] for r in status["history"]], list(reversed(events)))
        self.assertEqual([r["event"] for r in status["alerts"]], list(reversed(events[1:])))

    def test_invalid_json_and_event_are_rejected(self):
        for payload in (None, [], "text", 42):
            with self.subTest(payload=payload):
                response = self.client.post("/api/device/telemetry", json=payload, headers=self.headers)
                self.assertEqual(response.status_code, 400)
        self.assertEqual(self.post_reading(event="unknown").status_code, 400)
        self.assertEqual(self.post_reading(device_id="").status_code, 400)
        self.assertEqual(self.post_reading(device_id="x" * 65).status_code, 400)

    def test_invalid_measurements_do_not_get_saved(self):
        bad_fields = {
            "lat": (91, -91), "lon": (181, -181), "bpm": (-1, 301),
            "spo2": (-1, 101), "battery_pct": (-1, 101),
            "battery_voltage": (-1, 101), "current_ma": (-10001, 10001),
            "gps_satellites": (-1, 101),
        }
        for field, values in bad_fields.items():
            for value in (*values, "invalid", "NaN", "Infinity"):
                with self.subTest(field=field, value=value):
                    self.assertEqual(self.post_reading(**{field: value}).status_code, 400)
        self.assertEqual(self.post_reading(lat=21, lon=None).status_code, 400)
        self.assertEqual(self.post_reading(lat=None, lon=105).status_code, 400)
        with self.server.connect() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM readings").fetchone()[0], 0)

    def test_command_is_plain_text_and_retained_until_remote_upload(self):
        poll = lambda device="ngoc-01": self.client.get(
            "/api/device/command", query_string={"device_id": device}, headers=self.headers
        )
        self.assertEqual(poll().data, b"NONE")
        self.assertEqual(poll().mimetype, "text/plain")
        self.login()
        self.assertEqual(self.client.post("/api/command", json={"device_id": "ngoc-01", "command": "LOCATE"}).status_code, 200)
        self.assertEqual(poll().data, b"LOCATE")
        self.assertEqual(poll().data, b"LOCATE")
        self.assertEqual(poll("other-device").data, b"NONE")
        self.post_reading(event="telemetry")
        self.assertEqual(poll().data, b"LOCATE")
        self.assertEqual(self.post_reading(event="remote", spo2=101).status_code, 400)
        self.assertEqual(poll().data, b"LOCATE")
        self.assertEqual(self.post_reading(event="remote").status_code, 200)
        self.assertEqual(poll().data, b"NONE")

    def test_invalid_commands(self):
        self.login()
        for payload in ({"command": "RESET"}, {"command": "LOCATE", "device_id": ""}):
            self.assertEqual(self.client.post("/api/command", json=payload).status_code, 400)

    def test_status_limits_and_last_known_location(self):
        now = int(time.time())
        self.seed([("ngoc-01", now - 500, "telemetry", 21.02, 105.84)])
        self.seed([("ngoc-01", now, "button", None, None) for _ in range(200)])
        self.login()
        status = self.client.get("/api/status").json
        self.assertEqual(len(status["history"]), 150)
        self.assertEqual(len(status["alerts"]), 20)
        self.assertEqual(status["latest"]["id"], 201)
        self.assertEqual(status["history"][-1]["id"], 52)
        self.assertEqual(status["last_location"]["lat"], 21.02)
        self.assertIsNone(status["latest"]["lat"])

    def test_track_device_time_filter_and_order(self):
        now = int(time.time())
        self.seed([
            ("ngoc-01", now - 90000, "telemetry", 20, 104),
            ("ngoc-01", now - 30, "telemetry", 21, 105),
            ("ngoc-01", now - 20, "button", 21.1, 105.1),
            ("other", now - 10, "telemetry", 22, 106),
            ("ngoc-01", now, "telemetry", None, None),
        ])
        self.login()
        result = self.client.get("/api/track?device_id=ngoc-01&hours=24").json
        self.assertEqual(result["hours"], 24)
        self.assertEqual([p["id"] for p in result["points"]], [2, 3])
        self.assertEqual(set(result["points"][0]), {"id", "ts", "lat", "lon", "gps_satellites", "event"})
        self.assertEqual(len(self.client.get("/api/track?hours=168").json["points"]), 3)

    def test_track_limits_and_validation(self):
        self.login()
        for query in ("hours=0", "hours=169", "hours=abc", "hours=1.5", "device_id="):
            self.assertEqual(self.client.get("/api/track?" + query).status_code, 400)
        now = int(time.time())
        self.seed([("ngoc-01", now, "telemetry", 21, 105) for _ in range(1005)])
        points = self.client.get("/api/track").json["points"]
        self.assertEqual(len(points), 1000)
        self.assertEqual(points[0]["id"], 6)
        self.assertEqual(points[-1]["id"], 1005)


if __name__ == "__main__":
    unittest.main()
