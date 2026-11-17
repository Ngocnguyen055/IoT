"""Coordinate validation, timestamps, readings and pending device commands."""

import time

from ..validation import command_payload, telemetry_payload, track_parameters


class MonitoringService:
    def __init__(self, repository):
        self.repository = repository

    def record_telemetry(self, payload):
        reading = telemetry_payload(payload)
        self.repository.save_reading(reading, int(time.time()))

    def pending_command(self, device_id):
        return self.repository.pending_command(device_id)

    def issue_locate(self, payload):
        self.repository.queue_locate(command_payload(payload))

    def status(self):
        result = self.repository.dashboard_snapshot()
        result["now"] = int(time.time())
        return result

    def track(self, device_id, hours):
        device_id, hours = track_parameters(device_id, hours)
        since = int(time.time()) - hours * 3600
        return {"device_id": device_id, "hours": hours,
                "points": self.repository.track_points(device_id, since)}
