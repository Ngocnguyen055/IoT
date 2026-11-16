#include <cassert>
#include <cmath>
#include <cstring>
#include <iostream>
#include "../firmware/ESP32_Firmware/modem_protocol.h"

float estimateLiPoPercent(float voltage);
void testQueuedSnapshots();
void testAtReader();

int main() {
  char url[384];
  assert(IotProtocol::joinUrl("https://example.trycloudflare.com ",
                             "/api/device/telemetry", url, sizeof(url)));
  assert(std::strcmp(url, "https://example.trycloudflare.com/api/device/telemetry") == 0);
  assert(IotProtocol::joinUrl(" \thttps://example.trycloudflare.com///\r\n",
                             " /api/device/command?device_id=ngoc-01 \n", url, sizeof(url)));
  assert(std::strcmp(url, "https://example.trycloudflare.com/api/device/command?device_id=ngoc-01") == 0);
  assert(IotProtocol::joinUrl("https://example.trycloudflare.com", "/", url, sizeof(url)));
  assert(std::strcmp(url, "https://example.trycloudflare.com/") == 0);
  assert(!IotProtocol::joinUrl("https://bad host", "/api", url, sizeof(url)));
  assert(!IotProtocol::joinUrl("http://example.com", "/api", url, sizeof(url)));
  assert(!IotProtocol::joinUrl("https://", "/api", url, sizeof(url)));
  assert(!IotProtocol::joinUrl("https://example.com", "/bad path", url, sizeof(url)));
  char shortBuffer[4] = "old";
  assert(!IotProtocol::joinUrl("https://example.com", "/api", shortBuffer, sizeof(shortBuffer)));
  assert(shortBuffer[0] == '\0');
  assert(!IotProtocol::joinUrl(nullptr, "/", url, sizeof(url)));

  assert(!IotProtocol::containsCompleteLine("\r\n+HTTPACTION: 1,200,12", "+HTTPACTION:"));
  assert(IotProtocol::containsCompleteLine("\r\n+HTTPACTION: 1,200,12\r\n", "+HTTPACTION:"));
  assert(IotProtocol::parseHttpAction("\r\n+HTTPACTION: 1,200,12", 1) == -1);
  assert(IotProtocol::parseHttpAction("\r\nOK\r\n+HTTPACTION: 1,200,12\r\n", 1) == 200);
  assert(IotProtocol::parseHttpAction("+HTTPACTION: 0,200,4\n", 1) == -1);
  assert(IotProtocol::parseHttpAction("+HTTPACTION: 0,200,4\n+HTTPACTION: 1,201,0\r\n", 1) == 201);
  assert(IotProtocol::parseHttpAction("+HTTPACTION: 1,603,0\r\n", 1) == 603);
  assert(IotProtocol::parseHttpAction("+HTTPACTION: 1,200,\r\n", 1) == -1);
  assert(IotProtocol::parseHttpAction("+HTTPACTION: 1,200,-1\r\n", 1) == -1);
  assert(IotProtocol::parseHttpAction("+HTTPACTION: 1,200,12junk\r\n", 1) == -1);

  assert(estimateLiPoPercent(2.988f) == 0.0f);
  assert(estimateLiPoPercent(3.0f) == 0.0f);
  assert(std::fabs(estimateLiPoPercent(3.8f) - 45.0f) < 0.01f);
  assert(estimateLiPoPercent(4.2f) == 100.0f);
  assert(std::isnan(estimateLiPoPercent(NAN)));
  testQueuedSnapshots();
  testAtReader();
  std::cout << "PASS: URL whitespace, fragmented modem replies, event snapshots, cooperative waits, battery lookup\n";
}
