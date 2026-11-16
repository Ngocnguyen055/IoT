#include <Arduino.h>
#include <Wire.h>
#include <MAX30105.h>

// Temporary sensor test: no cellular modem, GPS, SOS handling or web uploads.
// Test only the two GPIOs used by the supplied firmware.
static const uint8_t SENSOR_ADDRESS = 0x57;
MAX30105 sensor;
bool busStarted = false;
bool sensorReady = false;
int activeSda = -1;
int activeScl = -1;
uint32_t redValue = 0;
uint32_t irValue = 0;
uint32_t sampleTotal = 0;
uint32_t lastReport = 0;
uint32_t lastRetry = 0;

int readPartId() {
  Wire.beginTransmission(SENSOR_ADDRESS);
  Wire.write(uint8_t(0xFF));
  if (Wire.endTransmission(false) != 0) return -1;
  if (Wire.requestFrom(SENSOR_ADDRESS, uint8_t(1)) != 1) return -1;
  return Wire.read();
}

bool tryPins(int sda, int scl) {
  if (busStarted) {
    Wire.end();
    busStarted = false;
  }
  Serial.printf("\n[TEST] SDA=D%d SCL=D%d\n", sda, scl);
  busStarted = Wire.begin(sda, scl, 100000);
  if (!busStarted) {
    Serial.println("[I2C] BUS_INIT_FAILED");
    return false;
  }
  Wire.setTimeOut(30);
  Wire.beginTransmission(SENSOR_ADDRESS);
  uint8_t result = Wire.endTransmission();
  Serial.printf("[I2C] addr=0x57 result=%u SDA_level=%d SCL_level=%d\n",
                unsigned(result), digitalRead(sda), digitalRead(scl));
  if (result != 0) {
    Serial.println("[RESULT] NO_ACK: chua giao tiep duoc voi cam bien.");
    return false;
  }
  int partId = readPartId();
  if (partId < 0) {
    Serial.println("[RESULT] ID_READ_FAILED");
    return false;
  }
  Serial.printf("[CHIP] PART_ID=0x%02X\n", unsigned(partId));
  if (partId == 0x11) {
    Serial.println("[RESULT] ID_MAX30100: thu vien MAX30102 hien tai khong phu hop.");
    return false;
  }
  if (partId != 0x15) {
    Serial.println("[RESULT] UNKNOWN_ID: can doi chieu loai chip/ket noi.");
    return false;
  }
  if (!sensor.begin(Wire, I2C_SPEED_STANDARD)) {
    Serial.println("[RESULT] LIBRARY_INIT_FAILED");
    return false;
  }
  // Red + IR, low LED current, continuous acquisition without 4G blocking.
  sensor.setup(0x1F, 4, 2, 100, 411, 4096);
  activeSda = sda;
  activeScl = scl;
  redValue = irValue = sampleTotal = 0;
  Serial.printf("[RESULT] SENSOR_OK SDA=D%d SCL=D%d; RED + IR enabled.\n", sda, scl);
  return true;
}

void findSensor() {
  sensorReady = tryPins(23, 22);
  if (!sensorReady) sensorReady = tryPins(22, 23);
}

void setup() {
  Serial.begin(115200);
  delay(600);
  Serial.println("\n=== KIEM TRA CAM BIEN MAX3010x ===");
  Serial.println("Serial Monitor: 115200 baud.");
  Serial.println("Ban test nay tam dung SOS va gui web. Nap lai ESP32_Firmware sau khi kiem tra.");
  findSensor();
  lastRetry = millis();
}

void loop() {
  if (sensorReady) {
    sensor.check();
    while (sensor.available()) {
      redValue = sensor.getRed();
      irValue = sensor.getIR();
      sensor.nextSample();
      ++sampleTotal;
    }
    if (millis() - lastReport >= 1000) {
      lastReport = millis();
      Serial.printf("[RAW] SDA=D%d SCL=D%d RED=%lu IR=%lu samples=%lu\n",
                    activeSda, activeScl, (unsigned long)redValue,
                    (unsigned long)irValue, (unsigned long)sampleTotal);
    }
  } else if (millis() - lastRetry >= 5000) {
    findSensor();
    lastRetry = millis();
  }
  delay(1);
}
