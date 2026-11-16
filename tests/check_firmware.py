"""Run host regressions and compile the sketch with the installed ESP32 toolchain."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / ".runtime" / "firmware-checks"
SOURCE = ROOT / "firmware" / "ESP32_Firmware" / "ESP32_Firmware.ino"


def run(command):
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=60)
    if result.stdout:
        print(result.stdout, end="", flush=True)
    if result.stderr:
        print(result.stderr, end="", flush=True)
    result.check_returncode()


def create_fixtures(source):
    battery = source[source.index("float estimateLiPoPercent("):source.index("\nvoid readBattery() {")]
    queue_globals = source[source.index("const uint8_t QUEUE_MAX="):source.index("bool modemReady=")]
    queue_functions = source[source.index("void queueEvent("):source.index("void gpsPump()")]
    at_reader = source[source.index("String readAT("):source.index("\nbool hasOK(")]
    fixture = r'''
#include <cassert>
#include <cmath>
#include <cstdint>
#include <string>
#include <vector>
#include "../../firmware/ESP32_Firmware/modem_protocol.h"
using std::isfinite;
''' + battery + r'''
namespace QueueFixture {
using String = std::string;
struct QuietSerial {
  template<class... T> void printf(const char*, T...) {}
  void println(const char*) {}
} Serial;
std::string payload;
int snapshots = 0;
String makeJson(const String&) { ++snapshots; return payload; }
''' + queue_globals + queue_functions + r'''
}
void testQueuedSnapshots() {
  using namespace QueueFixture;
  payload = "{\"bpm\":123,\"spo2\":98}";
  queueEvent("high_bpm");
  payload = "{\"bpm\":null,\"spo2\":null}";
  assert(alerts[0].body == "{\"bpm\":123,\"spo2\":98}");
  queueEvent("high_bpm");
  assert(alertCount == 1 && snapshots == 1);
  queueEvent("button");
  payload = "{\"bpm\":80}";
  queueEvent("button");
  assert(alertCount == 3);
  assert(alerts[1].body == "{\"bpm\":null,\"spo2\":null}");
  assert(alerts[2].body == "{\"bpm\":80}");
  removeEvent();
  assert(alertCount == 2 && alerts[0].reason == "button");
  while (alertCount < QUEUE_MAX) queueEvent("button");
  const String first = alerts[0].body;
  queueEvent("button");
  assert(alertCount == QUEUE_MAX && alerts[0].body == first);
}
namespace AtFixture {
class String : public std::string {
 public:
  using std::string::string;
  using std::string::operator=;
  bool isEmpty() const { return empty(); }
  int indexOf(const std::string& token) const {
    auto found = find(token);
    return found == npos ? -1 : static_cast<int>(found);
  }
  void remove(size_t start, size_t count) { erase(start, count); }
  bool startsWith(const std::string& prefix) const { return compare(0, prefix.size(), prefix) == 0; }
  void trim() {
    auto begin = find_first_not_of(" \r\n\t");
    if (begin == npos) { clear(); return; }
    erase(find_last_not_of(" \r\n\t") + 1);
    erase(0, begin);
  }
};
uint32_t clockMs = 0;
unsigned services = 0;
struct Chunk { uint32_t at; std::string data; };
std::vector<Chunk> chunks;
size_t chunk = 0, position = 0;
struct Modem {
  bool available() {
    while (chunk < chunks.size() && position >= chunks[chunk].data.size()) { ++chunk; position = 0; }
    return chunk < chunks.size() && chunks[chunk].at <= clockMs;
  }
  char read() { return chunks[chunk].data[position++]; }
} modem;
struct SerialMock { void write(char) {} } Serial;
uint32_t millis() { return clockMs; }
void delay(uint32_t duration) { clockMs += duration; }
void serviceDevice() { ++services; }
void noteModem(char) {}
void feed(std::vector<Chunk> response) {
  chunks = response; chunk = position = 0; clockMs = 0; services = 0;
}
''' + at_reader + r'''
}
void testAtReader() {
  using namespace AtFixture;
  feed({{0, "\r\n+HTTPACTION:"}, {40, " 1,200,12"}, {80, "\r\n"}});
  auto response = readAT(200, "+HTTPACTION:", false);
  assert(clockMs >= 80 && IotProtocol::parseHttpAction(response.c_str(), 1) == 200);
  assert(services >= 30);
  feed({{10, "DOWNLOAD"}});
  response = readAT(100, "DOWNLOAD", false);
  assert(clockMs < 100 && response.indexOf("DOWNLOAD") >= 0);
  feed({{0, "\r\n+CPIN: READY\r\n"}, {30, "OK\r\n"}});
  response = readAT(100, "+CPIN: READY", true);
  assert(clockMs >= 30 && response.indexOf("OK") >= 0);
  feed({{0, "\r\n+CME ERROR: SIM not inserted\r\n"}});
  response = readAT(100, "+CPIN: READY", true);
  assert(clockMs < 100 && response.indexOf("+CME ERROR:") >= 0);
  feed({});
  response = readAT(50, "+HTTPACTION:", false);
  assert(clockMs >= 50 && services >= 25);
  feed({{0, "+HTTPACTION: 1,200,12"}});
  response = readAT(50, "+HTTPACTION:", false);
  assert(clockMs >= 50 && IotProtocol::parseHttpAction(response.c_str(), 1) == -1);
}
'''
    path = OUT / "fixtures.cpp"
    path.write_text(fixture, encoding="utf-8")
    return path


def compile_esp32():
    local = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
    choices = sorted((local / "arduino/sketches").glob("*/compile_commands.json"),
                     key=lambda p: p.stat().st_mtime, reverse=True)
    entry = None
    for path in choices:
        for candidate in json.loads(path.read_text(encoding="utf-8-sig")):
            if candidate["file"].replace("\\", "/").endswith("/ESP32_Firmware.ino.cpp"):
                entry = candidate
                break
        if entry:
            break
    if not entry or not isinstance(entry.get("arguments"), list):
        raise RuntimeError("Cannot find structured ESP32 compiler arguments from Arduino IDE")
    arguments = entry["arguments"]
    flags = []
    index = 1
    replaced = False
    while index < len(arguments):
        arg = arguments[index]
        if arg in ("-o", "-MF", "-MT", "-MQ"):
            index += 2
            continue
        if arg in ("-c", "-MMD", "-MD", "-MP"):
            index += 1
            continue
        if arg.replace("\\", "/").endswith("/ESP32_Firmware.ino.cpp"):
            flags.extend(["-x", "c++", str(SOURCE)])
            replaced = True
        else:
            flags.append(arg)
        index += 1
    if not replaced:
        raise RuntimeError("Cannot identify the old sketch source argument")
    compilers = sorted((local / "Arduino15/packages/esp32/tools/esp-x32").glob(
        "*/bin/xtensa-esp32-elf-g++.exe"))
    if not compilers:
        raise RuntimeError("Installed ESP32 compiler not found")
    print("Compiling updated sketch for ESP32 Dev Module...", flush=True)
    run([str(compilers[-1]), *flags, "-c", "-o", str(OUT / "ESP32_Firmware.o")])
    print("PASS: ESP32 sketch compilation (object build; no device flash)", flush=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    source = SOURCE.read_text(encoding="utf-8-sig")
    fixture = create_fixtures(source)
    compiler = shutil.which("g++")
    if not compiler:
        raise RuntimeError("Host g++ compiler not found")
    executable = OUT / "firmware_tests.exe"
    print("Building host regressions...", flush=True)
    run([compiler, "-std=c++11", "-Wall", "-Wextra",
         str(ROOT / "tests/firmware_protocol_test.cpp"), str(fixture), "-o", str(executable)])
    run([str(executable)])
    compile_esp32()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("CHECK FAILED:", error, file=sys.stderr)
        raise SystemExit(1)
