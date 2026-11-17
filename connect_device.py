"""Open a temporary Cloudflare connection for the existing ESP32 firmware."""

import hashlib
import json
from pathlib import Path
import re
import subprocess
import urllib.error
import urllib.request
from urllib.parse import urlsplit

from project_config import load_config

ROOT = Path(__file__).resolve().parent
RUNTIME = ROOT / ".runtime"
FIRMWARE = ROOT / "firmware" / "ESP32_Firmware" / "ESP32_Firmware.ino"
FIRMWARE_CONFIG = FIRMWARE.with_name("device_config.local.h")


def download_cloudflared():
    target = RUNTIME / "cloudflared.exe"
    if target.exists():
        return target
    print("Dang tai Cloudflare tu kho chinh thuc; chi can tai lan dau.", flush=True)
    request = urllib.request.Request(
        "https://api.github.com/repos/cloudflare/cloudflared/releases/latest",
        headers={"User-Agent": "SOS-local-setup", "Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        release = json.load(response)
    asset = next(a for a in release["assets"] if a["name"] == "cloudflared-windows-amd64.exe")
    digest = asset.get("digest") or ""
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise RuntimeError("Khong tim thay ma SHA-256 de kiem tra ban tai Cloudflare.")
    temporary = target.with_suffix(".download")
    checksum = hashlib.sha256()
    with urllib.request.urlopen(asset["browser_download_url"], timeout=60) as response:
        with temporary.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                checksum.update(chunk)
                output.write(chunk)
    if checksum.hexdigest() != digest.removeprefix("sha256:"):
        raise RuntimeError("Ma kiem tra Cloudflare khong khop. Chua chay file vua tai.")
    temporary.replace(target)
    print("Da tai va kiem tra Cloudflare " + release["tag_name"], flush=True)
    return target


def prepare_firmware(url):
    if not FIRMWARE.exists():
        print("Chua co ban firmware trong thu muc firmware; can sua SERVER_BASE thu cong.")
        return
    url = url.strip().rstrip("/")
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
            or parsed.query or parsed.fragment or any(c.isspace() or c in '\"\\' for c in url)):
        raise ValueError("SERVER_BASE must be an HTTPS URL without whitespace or credentials")
    config = load_config()
    device_id = config.get("DEVICE_ID", "ngoc-01")
    if not isinstance(device_id, str) or not 1 <= len(device_id) <= 64:
        raise ValueError("DEVICE_ID must be a string of 1 to 64 characters")
    values = {"DEVICE_ID": device_id, "DEVICE_KEY": config["DEVICE_KEY"], "SERVER_BASE": url}
    lines = ["#pragma once", "// Generated locally by connect_device.py. Keep this file out of Git."]
    lines.extend(f"const char* {name} = {json.dumps(value)};" for name, value in values.items())
    FIRMWARE_CONFIG.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\nDA CHUAN BI FIRMWARE: " + str(FIRMWARE), flush=True)
    print("Cau hinh rieng: " + FIRMWARE_CONFIG.name, flush=True)
    print("Mo file nay bang Arduino IDE, chon board ESP32/cung COM roi Upload.", flush=True)
    print("Giu ca cua so web va cua so Cloudflare nay mo.\n", flush=True)


def main():
    RUNTIME.mkdir(exist_ok=True)
    try:
        with urllib.request.urlopen("http://127.0.0.1:5000/login", timeout=5) as response:
            if response.status != 200:
                raise RuntimeError("Web chua tra ve trang dang nhap.")
    except (urllib.error.URLError, OSError) as error:
        raise RuntimeError("Hay mo Chay-web.cmd truoc, sau do chay lai file nay.") from error

    load_config()
    executable = download_cloudflared()
    print("Dang mo ket noi 4G toi web. Nhan Ctrl+C de dong ket noi.", flush=True)
    process = subprocess.Popen(
        [str(executable), "tunnel", "--no-autoupdate", "--url", "http://127.0.0.1:5000"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        encoding="utf-8", errors="replace", cwd=ROOT,
    )
    found_url = None
    try:
        with (RUNTIME / "tunnel.log").open("w", encoding="utf-8") as log:
            for line in process.stdout:
                print(line, end="", flush=True)
                log.write(line)
                log.flush()
                match = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", line)
                if match and not found_url:
                    found_url = match.group(0)
                    (RUNTIME / "tunnel-url.txt").write_text(found_url + "\n", encoding="utf-8")
                    prepare_firmware(found_url)
        if process.wait() != 0:
            raise RuntimeError("Cloudflare da dung; xem thong bao phia tren.")
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nDa dong ket noi Cloudflare.")
    except Exception as error:
        print("\nLOI: " + str(error), flush=True)
        raise SystemExit(1)
