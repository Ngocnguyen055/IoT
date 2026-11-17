"""Only fresh, device-specific real uploads count towards the hardware check."""

import unittest

from scripts.check_device import new_baseline, summarize


def reading(identifier, timestamp, event="telemetry", **fields):
    return {"id": identifier, "ts": timestamp, "device_id": "device-a", "event": event,
            "bpm": None, "spo2": None, "battery_pct": None, "battery_voltage": None,
            "lat": None, "lon": None, **fields}


class DeviceObservationTests(unittest.TestCase):
    def test_old_sos_and_measurements_do_not_pass_the_new_hardware_test(self):
        status = {"now": 1000, "history": [reading(312, 900, "button", bpm=72, spo2=98, battery_pct=80, battery_voltage=4)], "commands": []}
        baseline = new_baseline(status, "device-a")
        self.assertEqual(baseline["last_id"], 312)
        self.assertFalse(any(summarize(status, baseline)["flags"].values()))

    def test_new_rows_from_another_device_are_excluded_and_zero_battery_and_gps_are_valid(self):
        baseline = {"device_id": "device-a", "started_at": 1000, "last_id": 312}
        status = {"now": 1020, "history": [reading(313, 1010, bpm=72, spo2=98, battery_pct=0, battery_voltage=3.1, lat=0, lon=0),
                                             reading(314, 1011, "button", device_id="device-b")], "commands": []}
        report = summarize(status, baseline)
        self.assertEqual([row["id"] for row in report["observed"]], [313])
        self.assertTrue(report["flags"]["fresh_data"])
        self.assertTrue(report["flags"]["battery_received"])
        self.assertTrue(report["flags"]["gps_fix_received"])
        self.assertFalse(report["flags"]["sos_received"])

    def test_observations_survive_history_window_and_locate_requires_response_and_ack(self):
        baseline = {"device_id": "device-a", "started_at": 1000, "last_id": 312}
        first = summarize({"now": 1020, "history": [reading(313, 1010, "button")], "commands": []}, baseline)
        waiting = summarize({"now": 1030, "history": [reading(314, 1025, "remote")], "commands": [{"device_id": "device-a", "cmd": "LOCATE"}]}, baseline, first)
        self.assertTrue(waiting["flags"]["sos_received"])
        self.assertFalse(waiting["flags"]["locate_response_received"])
        done = summarize({"now": 1200, "history": [], "commands": [{"device_id": "device-a", "cmd": "NONE"}]}, baseline, waiting)
        self.assertTrue(done["flags"]["locate_response_received"])
        self.assertFalse(done["flags"]["fresh_data"])

    def test_previous_run_cannot_supply_missing_sos_or_measurement_evidence(self):
        old = summarize({"now": 1020, "history": [reading(313, 1010, "button", bpm=72)], "commands": []},
                        {"device_id": "device-a", "started_at": 1000, "last_id": 312})
        report = summarize({"now": 1100, "history": [], "commands": []},
                           {"device_id": "device-a", "started_at": 1100, "last_id": 313}, old)
        self.assertEqual(report["observed"], [])
        self.assertFalse(report["complete"])
        self.assertFalse(report["flags"]["fresh_data_ever"])

    def test_gps_deferral_preserves_evidence_and_does_not_claim_a_fix(self):
        baseline = {"device_id": "device-a", "started_at": 1000, "last_id": 312}
        first = summarize({"now": 1020, "history": [reading(313, 1010, "button", bpm=72, spo2=98, battery_pct=0, battery_voltage=3.1)], "commands": []}, baseline)
        status = {"now": 1030, "history": [reading(314, 1025, "remote")], "commands": []}
        waiting = summarize(status, baseline, first)
        self.assertTrue(waiting["core_complete"])
        self.assertFalse(waiting["complete"])
        approved = summarize(status, {**baseline, "gps_test_deferred": True}, first)
        self.assertTrue(approved["complete"])
        self.assertFalse(approved["flags"]["gps_fix_received"])
        self.assertEqual(approved["verification_scope"], "indoor_gps_deferred")
        self.assertEqual([row["id"] for row in approved["observed"]], [313, 314])
