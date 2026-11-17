"""Exercise application isolation and the edge cases fixed during backend extraction."""

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from backend.app import create_app


ROOT = Path(__file__).resolve().parents[1]
CREDENTIALS = {"ADMIN_PASSWORD": "factory-test-admin", "DEVICE_KEY": "factory-test-device", "SESSION_SECRET": "factory-test-session"}


class FactoryTests(unittest.TestCase):
    def setUp(self):
        (ROOT / ".runtime").mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="factory-tests-", dir=ROOT / ".runtime")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)

    def app(self, name="a", **changes):
        return create_app({**CREDENTIALS, "DB_PATH": self.directory / (name + ".sqlite3"), "TESTING": True, **changes})

    def test_explicit_configuration_never_loads_private_credentials(self):
        with patch("backend.app.config.application_config", side_effect=AssertionError("Local configuration must not be read")):
            app = self.app()
        self.assertEqual(app.config["DEVICE_KEY"], CREDENTIALS["DEVICE_KEY"])

    def test_database_credentials_and_sessions_are_isolated_between_apps(self):
        first = self.app("first")
        second = self.app("second", ADMIN_PASSWORD="second-test-admin", DEVICE_KEY="second-test-device", SESSION_SECRET="second-test-session")
        a, b = first.test_client(), second.test_client()
        payload = {"device_id": "ngoc-01", "event": "button", "bpm": 75}
        self.assertEqual(a.post("/api/device/telemetry", json=payload, headers={"X-Device-Key": CREDENTIALS["DEVICE_KEY"]}).status_code, 200)
        self.assertEqual(b.post("/api/device/telemetry", json=payload, headers={"X-Device-Key": CREDENTIALS["DEVICE_KEY"]}).status_code, 401)
        self.assertEqual(a.post("/login", data={"password": CREDENTIALS["ADMIN_PASSWORD"]}).status_code, 302)
        self.assertEqual(b.post("/login", data={"password": CREDENTIALS["ADMIN_PASSWORD"]}).status_code, 401)
        b.set_cookie("session", a.get_cookie("session").value)
        self.assertEqual(b.get("/api/status").status_code, 401)
        self.assertEqual(b.post("/login", data={"password": "second-test-admin"}).status_code, 302)
        self.assertIsNone(b.get("/api/status").json["latest"])
        self.assertEqual(a.get("/api/status").json["latest"]["bpm"], 75)
        a.post("/api/command", json={"command": "LOCATE"})
        self.assertEqual(b.get("/api/device/command?device_id=ngoc-01", headers={"X-Device-Key": "second-test-device"}).data, b"NONE")

    def test_template_and_static_paths_are_independent_of_working_directory(self):
        original_directory = Path.cwd()
        try:
            os.chdir(self.directory)
            client = self.app().test_client()
            self.assertEqual(client.get("/login").status_code, 200)
            client.post("/login", data={"password": CREDENTIALS["ADMIN_PASSWORD"]})
            self.assertEqual(client.get("/").status_code, 200)
            for path in ("/static/app.js", "/static/style.css"):
                response = client.get(path)
                self.assertEqual(response.status_code, 200)
                response.close()
        finally:
            os.chdir(original_directory)

    def test_invalid_factory_settings_fail_before_reading_local_configuration(self):
        with patch("backend.app.config.application_config", side_effect=AssertionError("Local configuration must not be read")):
            for changes in ({"ADMIN_PASSWORD": ""}, {"DEVICE_KEY": None}, {"SESSION_SECRET": 42}, {"DB_PATH": ":memory:"}):
                with self.subTest(changes=changes), self.assertRaises(ValueError):
                    self.app(**changes)

    def test_api_urls_and_methods_match_the_original_contract(self):
        rules = {(rule.rule, method) for rule in self.app().url_map.iter_rules()
                 for method in rule.methods - {"OPTIONS", "HEAD"}}
        self.assertEqual(rules, {
            ("/", "GET"), ("/history", "GET"), ("/login", "GET"), ("/login", "POST"), ("/logout", "POST"),
            ("/static/<path:filename>", "GET"), ("/api/device/telemetry", "POST"),
            ("/api/device/command", "GET"), ("/api/status", "GET"), ("/api/track", "GET"),
            ("/api/command", "POST"), ("/api/dashboard", "GET"), ("/api/alerts", "GET"),
        })

    def test_unusual_json_returns_400_without_saving_readings(self):
        app = self.app()
        client = app.test_client()
        client.post("/login", data={"password": CREDENTIALS["ADMIN_PASSWORD"]})
        for payload in ([1], "string", 42, None):
            with self.subTest(payload=payload):
                response = client.post("/api/command", json=payload)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json, {"error": "JSON required"})
        for event in (["button"], {"event": "button"}):
            with self.subTest(event=event):
                response = client.post("/api/device/telemetry", json={"device_id": "ngoc-01", "event": event}, headers={"X-Device-Key": CREDENTIALS["DEVICE_KEY"]})
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json, {"error": "bad event"})
        for endpoint in ("/api/command", "/api/device/telemetry"):
            response = client.post(endpoint, data="{", content_type="application/json", headers={"X-Device-Key": CREDENTIALS["DEVICE_KEY"]})
            self.assertEqual(response.status_code, 400)
        self.assertIsNone(client.get("/api/status").json["latest"])

    def test_oversized_number_returns_400_and_unicode_password_is_supported(self):
        app = self.app(ADMIN_PASSWORD="mật-khẩu-thử-nghiệm")
        client = app.test_client()
        self.assertEqual(client.post("/login", data={"password": "mật-khẩu-thử-nghiệm"}).status_code, 302)
        response = client.post("/api/device/telemetry", json={"device_id": "ngoc-01", "bpm": 10 ** 400}, headers={"X-Device-Key": CREDENTIALS["DEVICE_KEY"]})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json, {"error": "bad field: bpm"})


if __name__ == "__main__":
    unittest.main()
