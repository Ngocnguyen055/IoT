"""Verify alert paging and bounded Atlas query plans in an isolated database."""

from datetime import datetime, timezone
import json
import sys
from uuid import uuid4

from pymongo import MongoClient
from pymongo.errors import OperationFailure, PyMongoError

from backend.app import create_app
from backend.app.alerts import ALERT_EVENTS, ALERT_PAGE_SIZE, alert_filter
from backend.app.config import build_config
from backend.app.database import initialize_database
from backend.app.models import Reading
from backend.app.repositories.errors import DatabaseUnavailable
from backend.app.repositories.indexes import (
    ALERT_INDEX, DEVICE_LOCATION_INDEX, GPS_FILTER, LOCATION_INDEX,
    ensure_reading_indexes, verify_reading_indexes,
)
from backend.app.repositories.mongodb import MongoDBRepository
from backend.app.validation import telemetry_payload
from project_config import ROOT
from scripts.check_mongodb import Tee
from scripts.migrate_mongodb import require_stopped_web


def plan_stages(value):
    """Inspect classic and slot-based explain trees without depending on one version."""
    result = set()
    if isinstance(value, dict):
        if isinstance(value.get("stage"), str):
            result.add(value["stage"])
        for child in value.values():
            result.update(plan_stages(child))
    elif isinstance(value, list):
        for child in value:
            result.update(plan_stages(child))
    return result


def explain_query(database, query, index, *, direction=-1, limit=21):
    result = database.command({"explain": {"find": "readings", "filter": query,
        "sort": {"_id": direction}, "limit": limit, "hint": index}, "verbosity": "executionStats"})
    statistics = result["executionStats"]
    stages = plan_stages(result.get("queryPlanner", {}).get("winningPlan", {})) | plan_stages(statistics.get("executionStages", {}))
    summary = {"index": index, "returned": statistics["nReturned"],
        "keys_examined": statistics["totalKeysExamined"], "documents_examined": statistics["totalDocsExamined"],
        "execution_ms": statistics["executionTimeMillis"], "stages": sorted(stages)}
    if stages.intersection({"COLLSCAN", "SORT"}):
        raise ValueError("Query used a collection scan or blocking sort: " + index)
    # These queries have no extra selective predicates after the index range.
    # Allow a few boundary seeks; avoid asserting unstable wall-clock timings.
    if max(summary["keys_examined"], summary["documents_examined"]) > 2 * limit + 5:
        raise ValueError("Query examined too many records for one page: " + index)
    return summary


def run_checks(settings, stream, *, telemetry_count=10000):
    name = "sos_hist_" + uuid4().hex[:20]
    if name == settings["MONGODB_DATABASE"] or len(name.encode("utf-8")) > 38:
        raise ValueError("Verification database must be separate from the application database")
    client = MongoClient(settings["MONGODB_URI"], serverSelectionTimeoutMS=settings["MONGODB_TIMEOUT_MS"],
        connectTimeoutMS=settings["MONGODB_TIMEOUT_MS"], socketTimeoutMS=30000, maxPoolSize=5, appname="iot-history-check")
    owned = False
    repository_client = None
    report = {"fixture_telemetry": telemetry_count, "fixture_alerts": 60, "queries": {}, "temporary_database_removed": False}
    try:
        client.admin.command("ping")
        if client[name].list_collection_names():
            raise ValueError("Verification namespace already exists; refusing to overwrite it")
        owned = True
        # Keep cleanup on an independent client: repository.initialize() closes
        # its own client if application startup fails.
        repository_client = MongoClient(settings["MONGODB_URI"], serverSelectionTimeoutMS=settings["MONGODB_TIMEOUT_MS"],
            connectTimeoutMS=settings["MONGODB_TIMEOUT_MS"], socketTimeoutMS=30000, maxPoolSize=5, appname="iot-history-fixture")
        repository = MongoDBRepository(repository_client, name)
        initialize_database(repository)
        # All alerts predate a large tail of telemetry. A scan of recent generic
        # readings would therefore inspect thousands of unrelated documents.
        documents = [Reading(number, "history-check", 1000, ALERT_EVENTS[(number - 1) % len(ALERT_EVENTS)],
            lat=0 if number in (10, 20, 30) else None, lon=0 if number in (10, 20, 30) else None,
            bpm=72, spo2=98, battery_pct=80).to_document() for number in range(1, 61)]
        documents.extend(Reading(number, "history-check", 1000, "telemetry").to_document()
                         for number in range(61, 61 + telemetry_count))
        for start in range(0, len(documents), 1000):
            repository.readings.insert_many(documents[start:start + 1000])
        repository.counters.update_one({"_id": "readings"}, {"$set": {"value": len(documents)}})
        app = create_app({"TESTING": True, "DATABASE_BACKEND": "mongodb", **settings, "MONGODB_DATABASE": name,
            "ADMIN_PASSWORD": "history-check-admin", "DEVICE_KEY": "history-check-device", "SESSION_SECRET": "history-check-session"}, repository=repository)
        browser = app.test_client()
        browser.post("/login", data={"password": "history-check-admin"})

        def page(**parameters):
            response = browser.get("/api/alerts", query_string=parameters)
            if response.status_code != 200:
                raise ValueError("History API did not return HTTP 200")
            return response.json

        first = page()
        if [row["id"] for row in first["items"]] != list(range(60, 40, -1)):
            raise ValueError("First history page has unexpected alert order")
        repository.save_reading(telemetry_payload({"device_id": "history-check", "event": "button"}), 2000)
        second = page(snapshot=60, before=41)
        third = page(snapshot=60, before=21)
        if [row["id"] for result in (first, second, third) for row in result["items"]] != list(range(60, 0, -1)):
            raise ValueError("History paging lost, repeated or mixed new records")
        if third["pagination"]["has_next"] or not third["pagination"]["has_previous"]:
            raise ValueError("Last history page has incorrect navigation")
        if page(snapshot=60, after=40) != first or page(snapshot=60, after=20) != second:
            raise ValueError("Previous page does not return the nearest newer records")
        if page()["items"][0]["id"] != len(documents) + 1:
            raise ValueError("Refreshing history did not include the new alert")
        dashboard = browser.get("/api/dashboard")
        if dashboard.status_code != 200 or len(dashboard.json["alerts"]) != 8 or "history" in dashboard.json:
            raise ValueError("Compact home dashboard has an unexpected payload")
        if [row["id"] for row in repository.track_points("history-check", 0)] != [10, 20, 30]:
            raise ValueError("GPS history changed after adding partial indexes")
        verify_reading_indexes(repository.readings)

        queries = {
            "latest_alerts": (alert_filter(), ALERT_INDEX, -1, ALERT_PAGE_SIZE + 1),
            "older_page": (alert_filter(60, before=41), ALERT_INDEX, -1, ALERT_PAGE_SIZE + 1),
            "newer_page": (alert_filter(60, after=20), ALERT_INDEX, 1, ALERT_PAGE_SIZE + 1),
            "last_location": (GPS_FILTER, LOCATION_INDEX, -1, 1),
            "device_location": ({**GPS_FILTER, "device_id": "history-check"}, DEVICE_LOCATION_INDEX, -1, 1),
            "missing_location": ({**GPS_FILTER, "device_id": "no-gps-device"}, DEVICE_LOCATION_INDEX, -1, 1),
        }
        for label, (query, index, direction, limit) in queries.items():
            summary = explain_query(repository.database, query, index, direction=direction, limit=limit)
            report["queries"][label] = summary
            print(f"{label}: returned={summary['returned']} keys={summary['keys_examined']} docs={summary['documents_examined']} ms={summary['execution_ms']}", file=stream)

        # Only add/verify indexes in the real database, after the disposable test
        # passes. Never insert test readings or rewrite existing application data.
        actual = client[settings["MONGODB_DATABASE"]]["readings"]
        ensure_reading_indexes(actual)
        verify_reading_indexes(actual)
        report["application_query"] = explain_query(actual.database, alert_filter(), ALERT_INDEX)
        report["application_indexes_verified"] = True
        report["ok"] = True
        print(f"DAT: {telemetry_count} telemetry + 60 su kien tren database tam; index database ung dung da san sang.", file=stream)
        return report
    finally:
        try:
            if owned:
                # Exact UUID namespace is owned by this invocation. Drop only the
                # three known collections, never the application or another DB.
                if not name.startswith("sos_hist_") or name == settings["MONGODB_DATABASE"]:
                    raise RuntimeError("Refusing to clean an unowned verification database")
                for collection in ("readings", "commands", "counters"):
                    client[name].drop_collection(collection)
                report["temporary_database_removed"] = True
        finally:
            if repository_client is not None:
                repository_client.close()
            client.close()


def main():
    runtime = ROOT / ".runtime"
    runtime.mkdir(exist_ok=True)
    report = {"ok": False, "checked_at_utc": datetime.now(timezone.utc).isoformat()}
    with (runtime / "history-query-check.log").open("w", encoding="utf-8") as log:
        output = Tee(sys.stdout, log)
        try:
            require_stopped_web()
            settings = build_config({"DATABASE_BACKEND": "mongodb"})
            print("Kiem tra phan trang va explain tren Atlas tam (10.000 telemetry + 60 su kien).", file=output)
            report.update(run_checks(settings, output))
        except OperationFailure as error:
            report["mongo_code"] = error.code
            print("Atlas tu choi thao tac. MongoDB error code:", error.code, file=output)
        except (DatabaseUnavailable, PyMongoError):
            report["reason"] = "connection_or_permissions"
            print("Chua ket noi/kiem tra duoc Atlas. Kiem tra mang, IP va database user.", file=output)
        except (ValueError, RuntimeError) as error:
            report["reason"] = "verification"
            print("CHUA DAT:", str(error), file=output)
        except OSError:
            report["reason"] = "local_files"
            print("Khong doc/ghi duoc cau hinh hoac bao cao.", file=output)
        print("KIEM TRA LICH SU DAT." if report["ok"] else "KIEM TRA LICH SU CHUA DAT. Xem .runtime/history-query-check.log.", file=output)
    (runtime / "history-query-check.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
