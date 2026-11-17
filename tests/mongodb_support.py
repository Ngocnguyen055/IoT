"""Fixtures shared by mock contract tests and owner-run Atlas verification."""

from backend.app.validation import telemetry_payload


def seed_readings(repository, rows):
    if not rows:
        return
    start = repository.counters.find_one({"_id": "readings"})["value"]
    documents = []
    for offset, (device, timestamp, event, latitude, longitude) in enumerate(rows, start=1):
        reading = telemetry_payload({"device_id": device, "event": event, "lat": latitude, "lon": longitude})
        documents.append({"_id": start + offset, **reading, "ts": timestamp})
    repository.readings.insert_many(documents)
    repository.counters.update_one({"_id": "readings"}, {"$max": {"value": start + len(documents)}})
