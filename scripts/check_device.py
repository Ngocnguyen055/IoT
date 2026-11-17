"""Observe real device uploads through the running web API; never send fake telemetry."""

import argparse
from http.cookiejar import CookieJar
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener

from project_config import ROOT, application_config


BASE_URL = "http://127.0.0.1:5000"
BASELINE = ROOT / ".runtime/device-check-baseline.json"
REPORT = ROOT / ".runtime/device-check.json"


def read_status(password):
    opener = build_opener(HTTPCookieProcessor(CookieJar()))
    request = Request(BASE_URL + "/login", data=urlencode({"password": password}).encode(), method="POST")
    with opener.open(request, timeout=15) as response:
        if response.status != 200:
            raise ValueError("Web login failed")
    request = Request(BASE_URL + "/api/status", headers={"Cache-Control": "no-cache"})
    with opener.open(request, timeout=15) as response:
        return json.load(response)


def device_rows(status, device):
    rows = [*status.get("history", []), *status.get("alerts", [])]
    if status.get("latest"):
        rows.append(status["latest"])
    return {row["id"]: row for row in rows if row.get("device_id") == device}


def new_baseline(status, device):
    return {"device_id": device, "started_at": status["now"], "last_id": max(device_rows(status, device), default=0)}


def summarize(status, baseline, previous=None):
    device = baseline["device_id"]
    if previous and any(previous.get(key) != baseline[key] for key in ("device_id", "started_at", "last_id")):
        previous = None
    rows = {row["id"]: row for row in (previous or {}).get("observed", [])}
    candidates = device_rows(status, device)
    rows.update({key: row for key, row in candidates.items()
                 if key > baseline["last_id"] and row["ts"] >= baseline["started_at"]})
    observed = sorted(rows.values(), key=lambda row: row["id"])
    pending = next((row["cmd"] for row in status.get("commands", []) if row["device_id"] == device), "NONE")

    def positive(name):
        return any(isinstance(row.get(name), (int, float)) and row[name] > 0 for row in observed)

    flags = {
        "fresh_data": any(0 <= status["now"] - row["ts"] <= 90 for row in observed),
        "sos_received": any(row["event"] == "button" for row in observed),
        "bpm_received": positive("bpm"), "spo2_received": positive("spo2"),
        "battery_received": any(row.get("battery_pct") is not None and (row.get("battery_voltage") or 0) > 0 for row in observed),
        "locate_response_received": any(row["event"] == "remote" for row in observed) and pending == "NONE",
        "gps_fix_received": any(row.get("lat") is not None and row.get("lon") is not None for row in observed),
    }
    flags["fresh_data_ever"] = flags["fresh_data"] or (previous or {}).get("flags", {}).get("fresh_data_ever", False)
    required = [name for name in flags if name not in {"fresh_data", "gps_fix_received"}]
    core_complete = all(flags[name] for name in required)
    gps_deferred = baseline.get("gps_test_deferred", False)
    return {**baseline, "checked_at": status["now"], "flags": flags, "pending_command": pending,
            "observed": observed, "latest_observed_id": max(rows, default=baseline["last_id"]),
            "core_complete": core_complete, "gps_test_deferred": gps_deferred,
            "verification_scope": "full" if flags["gps_fix_received"] else "indoor_gps_deferred" if gps_deferred else "awaiting_gps",
            "complete": core_complete and (flags["gps_fix_received"] or gps_deferred)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", action="store_true", help="Save a baseline before the hardware test; exclude existing history")
    parser.add_argument("--require-complete", action="store_true", help="Verify the saved hardware report before committing the completed phase")
    parser.add_argument("--defer-gps", action="store_true", help="Record the owner's decision to test outdoor GPS later; never claim a GPS fix")
    args = parser.parse_args()
    try:
        config = application_config()
        if args.require_complete:
            report = json.loads(REPORT.read_text(encoding="utf-8"))
            if not report.get("complete") or report.get("device_id") != config.get("DEVICE_ID", "ngoc-01"):
                print("CHUA DU BANG CHUNG THU THIET BI. Xem .runtime/device-check.json.")
                return 1
            print("BAO CAO THU THIET BI DAT. Device:", report["device_id"], "| Last ID:", report["latest_observed_id"])
            if report.get("gps_test_deferred") and not report["flags"]["gps_fix_received"]:
                print("GPS ngoai troi: chu du an hen thu sau; chua xac nhan toa do.")
            return 0
        status = read_status(config["ADMIN_PASSWORD"])
        BASELINE.parent.mkdir(exist_ok=True)
        if args.start:
            baseline = new_baseline(status, config.get("DEVICE_ID", "ngoc-01"))
            if args.defer_gps:
                baseline["gps_test_deferred"] = True
            BASELINE.write_text(json.dumps(baseline, indent=2), encoding="utf-8")
            REPORT.write_text(json.dumps(summarize(status, baseline), indent=2), encoding="utf-8")
            print("DA LUU MOC THU THIET BI. ID cuoi truoc khi thu:", baseline["last_id"])
            return 0
        if not BASELINE.exists():
            print("Chay lenh nay voi --start truoc khi bat dau thu thiet bi.")
            return 1
        baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
        if args.defer_gps:
            baseline["gps_test_deferred"] = True
            BASELINE.write_text(json.dumps(baseline, indent=2), encoding="utf-8")
        previous = json.loads(REPORT.read_text(encoding="utf-8")) if REPORT.exists() else None
        report = summarize(status, baseline, previous)
        REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print("Device:", report["device_id"], "| New readings:", len(report["observed"]), "| Last ID:", report["latest_observed_id"])
        for name, value in report["flags"].items():
            print(name + ":", "OBSERVED" if value else "NOT YET OBSERVED")
        print("Pending command:", report["pending_command"])
        if report["gps_test_deferred"] and not report["flags"]["gps_fix_received"]:
            print("GPS ngoai troi: chu du an hen thu sau; chua xac nhan toa do.")
        return 0
    except HTTPError as error:
        print("Khong doc duoc API web. HTTP status:", error.code)
    except (OSError, URLError, ValueError, KeyError):
        print("Chua doc duoc web/moc thu. Mo Chay-web.cmd va kiem tra cau hinh dang nhap.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
