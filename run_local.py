"""Start the SOS website with persistent local configuration."""

import argparse
import os
import threading
import urllib.error
import urllib.request
import webbrowser

from project_config import ROOT, load_config


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
