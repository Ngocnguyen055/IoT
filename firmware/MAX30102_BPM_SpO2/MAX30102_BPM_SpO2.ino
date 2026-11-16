#include <Arduino.h>
#include <Wire.h>
#include <MAX30105.h>
#include "spo2_algorithm.h"
#include <string.h>

// Standalone MAX30102 test for the supplied ESP32 Dev Module.
// Fixed I2C pins: SDA=23, SCL=22. Serial Monitor: 115200 baud.
// No 4G, GPS, SOS or website uploads in this sketch.
// Algorithm/reference: SparkFun MAX3010x Example8_SPO2.
constexpr uint8_t SDA_PIN = 23;
constexpr uint8_t SCL_PIN = 22;
constexpr uint8_t SENSOR_ADDRESS = 0x57;
constexpr size_t WINDOW_SAMPLES = 100;
constexpr uint32_t FINGER_IR_MIN = 50000;  // Presence heuristic; inspect RAW IR if needed.

MAX30105 sensor;
uint32_t redBuffer[WINDOW_SAMPLES];
uint32_t irBuffer[WINDOW_SAMPLES];
uint32_t lastRed = 0;
uint32_t lastIr = 0;
uint32_t sampleTotal = 0;
size_t sampleCount = 0;
uint8_t newSamples = 0;
int32_t bpm = 0;
int32_t spo2 = 0;
int8_t bpmValid = 0;
int8_t spo2Valid = 0;
bool busStarted = false;
bool sensorReady = false;
uint32_t lastInitAttempt = 0;
uint32_t lastSampleAt = 0;
uint32_t lastReportAt = 0;

void resetWindow() {
  sampleCount = 0;
  newSamples = 0;
  bpmValid = 0;
  spo2Valid = 0;
}

int readPartId() {
  Wire.beginTransmission(SENSOR_ADDRESS);
  Wire.write(uint8_t(0xFF));
  if (Wire.endTransmission(false) != 0) return -1;
  if (Wire.requestFrom(SENSOR_ADDRESS, uint8_t(1)) != 1) return -1;
  return Wire.read();
}

bool initSensor() {
  resetWindow();
  lastRed = lastIr = 0;
  if (busStarted) {
    Wire.end();
    busStarted = false;
  }
  Serial.println("\n[INIT] MAX30102 SDA=D23 SCL=D22 I2C=100000");
  busStarted = Wire.begin(SDA_PIN, SCL_PIN, 100000);
  if (!busStarted) {
    Serial.println("[ERROR] I2C_INIT_FAILED");
    return false;
  }
  Wire.setTimeOut(50);
  Wire.beginTransmission(SENSOR_ADDRESS);
  uint8_t result = Wire.endTransmission();
  Serial.printf("[I2C] address=0x57 result=%u SDA_level=%d SCL_level=%d\n",
                unsigned(result), digitalRead(SDA_PIN), digitalRead(SCL_PIN));
  if (result != 0) {
    if (result == 5) {
      Serial.println("[ERROR] I2C_TIMEOUT: kiem tra nguon, GND va day SDA/SCL.");
    } else if (result == 2) {
      Serial.println("[ERROR] SENSOR_NO_ACK: chua nhan duoc cam bien tai 0x57.");
    } else {
      Serial.println("[ERROR] I2C_TRANSFER_FAILED");
    }
    return false;
  }
  int partId = readPartId();
  if (partId < 0) {
    Serial.println("[ERROR] PART_ID_READ_FAILED");
    return false;
  }
  Serial.printf("[CHIP] PART_ID=0x%02X\n", unsigned(partId));
  if (partId != 0x15) {
    Serial.println(partId == 0x11
      ? "[ERROR] MAX30100_ID: can dung driver khac cho loai chip nay."
      : "[ERROR] UNEXPECTED_PART_ID: can doi chieu loai chip/ket noi.");
    return false;
  }
  if (!sensor.begin(Wire, I2C_SPEED_STANDARD)) {
    Serial.println("[ERROR] SENSOR_INIT_FAILED");
    return false;
  }
  // 100 conversions/s averaged by 4 -> 25 samples/s.
  // spo2_algorithm.h uses FreqS=25; its 100-sample window spans 4 seconds.
  sensor.setup(60, 4, 2, 100, 411, 4096);
  sensor.clearFIFO();
  lastSampleAt = millis();
  Serial.println("[READY] MAX30102 detected; RED + IR enabled.");
  Serial.println("[HELP] Dat ngon tay len mat cam bien, giu yen de thu du 100 mau.");
  return true;
}

void acceptSample(uint32_t red, uint32_t ir) {
  lastRed = red;
  lastIr = ir;
  lastSampleAt = millis();
  ++sampleTotal;
  if (ir < FINGER_IR_MIN) {
    resetWindow();
    return;
  }
  if (sampleCount < WINDOW_SAMPLES) {
    redBuffer[sampleCount] = red;
    irBuffer[sampleCount] = ir;
    ++sampleCount;
  } else {
    memmove(redBuffer, redBuffer + 1, (WINDOW_SAMPLES - 1) * sizeof(redBuffer[0]));
    memmove(irBuffer, irBuffer + 1, (WINDOW_SAMPLES - 1) * sizeof(irBuffer[0]));
    redBuffer[WINDOW_SAMPLES - 1] = red;
    irBuffer[WINDOW_SAMPLES - 1] = ir;
  }
  ++newSamples;
  if (sampleCount == WINDOW_SAMPLES && newSamples >= 25) {
    newSamples = 0;
    maxim_heart_rate_and_oxygen_saturation(
      irBuffer, int32_t(WINDOW_SAMPLES), redBuffer,
      &spo2, &spo2Valid, &bpm, &bpmValid);
  }
}

void reportReading() {
  Serial.printf("[DATA] RED=%lu IR=%lu samples=%lu ",
                (unsigned long)lastRed, (unsigned long)lastIr,
                (unsigned long)sampleTotal);
  if (lastIr < FINGER_IR_MIN) {
    Serial.println("state=NO_FINGER_OR_LOW_IR BPM=-- SpO2=--");
    return;
  }
  if (sampleCount < WINDOW_SAMPLES) {
    Serial.printf("state=COLLECTING window=%u/100 BPM=-- SpO2=--\n", unsigned(sampleCount));
    return;
  }
  bool hrOK = bpmValid && bpm > 0 && bpm <= 300;
  bool oxygenOK = spo2Valid && spo2 > 0 && spo2 <= 100;
  Serial.print("BPM=");
  if (hrOK) Serial.print(bpm); else Serial.print("--");
  Serial.print(" SpO2=");
  if (oxygenOK) {
    Serial.print(spo2);
    Serial.print('%');
  } else Serial.print("--");
  Serial.printf(" HRvalid=%d SpO2valid=%d\n", int(hrOK), int(oxygenOK));
}

void setup() {
  Serial.begin(115200);
  delay(600);
  Serial.println("\n=== MAX30102 BPM / SpO2 - SDA23 SCL22 ===");
  Serial.println("Serial Monitor: 115200 baud. Ket qua chi in tai day.");
  sensorReady = initSensor();
  lastInitAttempt = millis();
}

void loop() {
  if (!sensorReady) {
    if (millis() - lastInitAttempt >= 3000) {
      sensorReady = initSensor();
      lastInitAttempt = millis();
    }
    delay(1);
    return;
  }
  sensor.check();
  while (sensor.available()) {
    uint32_t red = sensor.getRed();
    uint32_t ir = sensor.getIR();
    sensor.nextSample();
    acceptSample(red, ir);
  }
  if (millis() - lastSampleAt > 2500) {
    Serial.println("[ERROR] NO_NEW_SAMPLES: se khoi tao lai cam bien.");
    sensorReady = false;
    resetWindow();
    lastInitAttempt = millis();
  } else if (millis() - lastReportAt >= 1000) {
    lastReportAt = millis();
    reportReading();
  }
  delay(1);
}
