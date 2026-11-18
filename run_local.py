"""Start the SOS website with persistent local configuration."""

import argparse
import os
import threading
import urllib.error
import urllib.request
import webbrowser

from project_config import ROOT, application_config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    os.chdir(ROOT)
    config = application_config()
    url = "http://127.0.0.1:5000"
    print(f"\nWeb: {url}", flush=True)
    print(f"Mat khau dang nhap: {config['ADMIN_PASSWORD']}", flush=True)
    print("Giu cua so nay mo. Dung web bang Ctrl+C.", flush=True)
    print("Cau hinh: .env neu co; JSON cu duoc ho tro de tuong thich.\n", flush=True)
    try:
        with urllib.request.urlopen(url + "/login", timeout=1) as response:
            login_html = response.read().decode("utf-8")
            already_running = 'data-app="iot-sos"' in login_html or "IOT - Ngọc" in login_html
    except (urllib.error.URLError, OSError):
        already_running = False
    if already_running:
        print("Web da dang chay. Mo trang web hien tai.", flush=True)
        if not args.no_browser:
            webbrowser.open(url)
        return
    from backend.app import create_app

    app = create_app({**config, "DB_PATH": config.get("DB_PATH", str(ROOT / "iot_ngoc.sqlite3"))})
    if not args.no_browser:
        timer = threading.Timer(1.5, webbrowser.open, args=(url,))
        timer.daemon = True
        timer.start()
    app.run(host="127.0.0.1", port=5000, debug=False)


if __name__ == "__main__":
    main()
