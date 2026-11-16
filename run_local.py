"""Start the SOS website with persistent local configuration."""

import argparse
import json
import os
from pathlib import Path
import re
import secrets
import threading
import urllib.error
import urllib.request
import webbrowser

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.local.json"


def load_config():
    if not CONFIG_PATH.exists():
        # Match the existing ESP32 firmware's key from the supplied guide.
        guide = (ROOT / "Hướng dẫn chạy sản phẩm.txt").read_text(encoding="utf-8-sig")
        match = re.search(r'set "DEVICE_KEY=([^"\r\n]+)"', guide)
        config = {
            "ADMIN_PASSWORD": "SOS-" + secrets.token_hex(6),
            "DEVICE_KEY": match.group(1) if match else secrets.token_hex(32),
            "SESSION_SECRET": secrets.token_hex(32),
        }
        with CONFIG_PATH.open("x", encoding="utf-8") as handle:
            json.dump(config, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))
    for name in ("ADMIN_PASSWORD", "DEVICE_KEY", "SESSION_SECRET"):
        if not isinstance(config.get(name), str) or not config[name]:
            raise ValueError(f"Missing or invalid {name} in {CONFIG_PATH.name}")
    return config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    os.chdir(ROOT)
    config = load_config()
    os.environ.update(config)
    os.environ["DB_PATH"] = str(ROOT / "iot_ngoc.sqlite3")

    from app import app

    url = "http://127.0.0.1:5000"
    print(f"\nWeb: {url}", flush=True)
    print(f"Mat khau dang nhap: {config['ADMIN_PASSWORD']}", flush=True)
    print("Giu cua so nay mo. Dung web bang Ctrl+C.", flush=True)
    print("Cau hinh duoc luu trong config.local.json.\n", flush=True)
    try:
        with urllib.request.urlopen(url + "/login", timeout=1) as response:
            already_running = "IOT - Ngọc" in response.read().decode("utf-8")
    except (urllib.error.URLError, OSError):
        already_running = False
    if already_running:
        print("Web da dang chay. Mo trang web hien tai.", flush=True)
        if not args.no_browser:
            webbrowser.open(url)
        return
    if not args.no_browser:
        timer = threading.Timer(1.5, webbrowser.open, args=(url,))
        timer.daemon = True
        timer.start()
    app.run(host="127.0.0.1", port=5000, debug=False)


if __name__ == "__main__":
    main()
