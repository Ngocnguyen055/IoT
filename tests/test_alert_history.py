"""Exercise history navigation against both supported repositories, without real data."""

import importlib.util
from pathlib import Path
import tempfile
import unittest

from backend.app import create_app
from backend.app.alerts import ALERT_EVENTS
from backend.app.validation import telemetry_payload


ROOT = Path(__file__).resolve().parents[1]
CONFIG = {"TESTING": True, "DATABASE_BACKEND": "sqlite", "ADMIN_PASSWORD": "history-test-admin",
          "DEVICE_KEY": "history-test-device", "SESSION_SECRET": "history-test-session"}


class HistoryContract:
    def setUp(self):
        self.app = self.make_app()
        self.repository = self.app.extensions["sos_repository"]
        self.client = self.app.test_client()
        self.client.post("/login", data={"password": CONFIG["ADMIN_PASSWORD"]})

    def seed(self, alerts=45):
        # Interleaved telemetry creates ID gaps. Identical/reversed timestamps must
        # not change insertion order or lose rows at page boundaries.
        identifiers = []
        for number in range(alerts):
            self.repository.save_reading(telemetry_payload({"device_id": "history-device", "event": "telemetry"}), 2000)
            self.repository.save_reading(telemetry_payload({"device_id": "history-device", "event": ALERT_EVENTS[number % len(ALERT_EVENTS)], "bpm": 0, "spo2": 99, "battery_pct": 0}), 2000 - number)
            identifiers.append(2 * (number + 1))
        return list(reversed(identifiers))

    def page(self, **parameters):
        response = self.client.get("/api/alerts", query_string=parameters)
        self.assertEqual(response.status_code, 200)
        return response.json

    def test_history_requires_admin_session_even_with_device_key(self):
        anonymous = self.app.test_client()
        self.assertEqual(anonymous.get("/history").headers["Location"], "/login")
        for endpoint in ("/api/alerts", "/api/dashboard"):
            self.assertEqual(anonymous.get(endpoint, headers={"X-Device-Key": CONFIG["DEVICE_KEY"]}).status_code, 401)
        self.assertEqual(self.client.get("/history").status_code, 200)

    def test_empty_history_and_explicit_zero_snapshot(self):
        for parameters in ({}, {"snapshot": 0}):
            result = self.page(**parameters)
            self.assertEqual(result, {"items": [], "pagination": {"snapshot": 0, "page_size": 20,
                "has_previous": False, "has_next": False, "previous_after": None, "next_before": None}})

    def test_forward_and_backward_cover_all_alerts_with_no_telemetry_or_duplicates(self):
        expected = self.seed()
        pages = [self.page()]
        while pages[-1]["pagination"]["has_next"]:
            cursor = pages[-1]["pagination"]
            pages.append(self.page(snapshot=cursor["snapshot"], before=cursor["next_before"]))
        self.assertEqual([len(page["items"]) for page in pages], [20, 20, 5])
        self.assertEqual([item["id"] for page in pages for item in page["items"]], expected)
        self.assertFalse(pages[0]["pagination"]["has_previous"])
        self.assertTrue(pages[-1]["pagination"]["has_previous"])
        for item in pages[0]["items"]:
            self.assertIn(item["event"], ALERT_EVENTS)
            self.assertEqual(item["bpm"], 0)
            self.assertEqual(item["battery_pct"], 0)
            self.assertIsNone(item["lat"])
        current = pages[-1]
        for expected_page in reversed(pages[:-1]):
            cursor = current["pagination"]
            current = self.page(snapshot=cursor["snapshot"], after=cursor["previous_after"])
            self.assertEqual(current, expected_page)

    def test_new_alert_does_not_shift_open_pages_and_refresh_includes_it(self):
        expected = self.seed()
        first = self.page()
        snapshot = first["pagination"]["snapshot"]
        self.repository.save_reading(telemetry_payload({"device_id": "history-device", "event": "button"}), 3000)
        second = self.page(snapshot=snapshot, before=first["pagination"]["next_before"])
        self.assertEqual([item["id"] for item in second["items"]], expected[20:40])
        previous = self.page(snapshot=snapshot, after=second["pagination"]["previous_after"])
        self.assertEqual(previous, first)
        self.assertEqual(self.page()["items"][0]["id"], snapshot + 1)

    def test_exact_page_boundary_has_no_empty_next_page(self):
        self.seed(20)
        page = self.page()
        self.assertEqual(len(page["items"]), 20)
        self.assertFalse(page["pagination"]["has_next"])
        self.assertFalse(page["pagination"]["has_previous"])

    def test_invalid_cursors_are_rejected(self):
        for parameters in ({"before": 1}, {"after": 1}, {"snapshot": 10, "before": 2, "after": 3},
                           {"snapshot": -1}, {"snapshot": "1.0"}, {"snapshot": "١"}, {"snapshot": ""},
                           {"snapshot": 2**63}, {"snapshot": 10, "before": 0}, {"snapshot": 10, "after": 11},
                           {"snapshot": 10, "before": "garbage"}, {"snapshot": 10, "after": -1}):
            with self.subTest(parameters=parameters):
                self.assertEqual(self.client.get("/api/alerts", query_string=parameters).status_code, 400)

    def test_compact_dashboard_keeps_metrics_and_legacy_status_contract(self):
        self.seed(80)
        compact = self.client.get("/api/dashboard").json
        legacy = self.client.get("/api/status").json
        self.assertNotIn("history", compact)
        self.assertEqual(len(compact["alerts"]), 8)
        self.assertEqual(len(legacy["alerts"]), 20)
        self.assertEqual(len(legacy["history"]), 150)
        for key in ("latest", "last_location", "commands"):
            self.assertEqual(compact[key], legacy[key])
        self.assertEqual(compact["latest"]["id"], 160)


class SQLiteHistoryTests(HistoryContract, unittest.TestCase):
    def make_app(self):
        (ROOT / ".runtime").mkdir(exist_ok=True)
        temporary = tempfile.TemporaryDirectory(prefix="history-", dir=ROOT / ".runtime")
        self.addCleanup(temporary.cleanup)
        return create_app({**CONFIG, "DB_PATH": Path(temporary.name) / "history.sqlite3"})


@unittest.skipUnless(importlib.util.find_spec("mongomock"), "Install test dependencies first")
class MongoHistoryTests(HistoryContract, unittest.TestCase):
    def make_app(self):
        import mongomock
        from backend.app.repositories.mongodb import MongoDBRepository

        class MockRepository(MongoDBRepository):
            def initialize(self):
                self._initialize_storage()

            def _with_transaction(self, operation):
                return operation(None)

        repository = MockRepository(mongomock.MongoClient(), "history_test")
        self.addCleanup(repository.close)
        return create_app(CONFIG, repository=repository)

    def test_partial_indexes_include_only_alerts_and_valid_gps(self):
        from backend.app.repositories.indexes import ALERT_INDEX, GPS_FILTER, LOCATION_INDEX, verify_reading_indexes
        verify_reading_indexes(self.repository.readings)
        information = self.repository.readings.index_information()
        self.assertEqual(information[ALERT_INDEX]["partialFilterExpression"], {"event": {"$in": list(ALERT_EVENTS)}})
        self.assertEqual(information[LOCATION_INDEX]["partialFilterExpression"], GPS_FILTER)


if __name__ == "__main__":
    unittest.main()
