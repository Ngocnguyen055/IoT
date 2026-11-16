#include <Arduino.h>
#include <Wire.h>
#include <TinyGPS++.h>
#include <MAX30105.h>
#include "spo2_algorithm.h"
#include <Adafruit_INA219.h>
#include <math.h>
#include "modem_protocol.h"

// IOT - NGOC: A7670C LTE HTTPS + GPS + MAX30102 + INA219 + SOS
// Board: classic ESP32 Dev Module (two independent I2C controllers)
#define MODEM_RX 16  // ESP32 receives from A7670C TXD
#define MODEM_TX 17  // ESP32 transmits to A7670C RXD
#define GPS_RX 18    // ESP32 receives from NEO-6M TX
#define GPS_TX 19    // ESP32 transmits to NEO-6M RX
#define MAX_SCL 22
#define MAX_SDA 23
#define INA_SCL 26
#define INA_SDA 27
#define BUTTON_PIN 21 // button to GND, INPUT_PULLUP

// EDIT: Use exactly the DEVICE_KEY configured on Flask.
const char* DEVICE_ID = "ngoc-01";
const char* DEVICE_KEY = "3445fc58fe14088666f4c8e49ea8a3c167f4f8df72004eeacbcf771f18c820ce";
const char* APN = "v-internet"; // informational; existing Viettel CID 1 is used
const char* SERVER_BASE = "https://culture-silent-lie-tactics.trycloudflare.com";
const char* CA_FILE = "gts_r4.pem"; // already uploaded to A7670C
const uint32_t MODEM_BAUD = 115200;
// Tracking: 15s is a practical starting point for a blocking HTTPS modem.
// The actual update interval can be longer while an HTTP request is running.
const uint32_t TELEMETRY_MS = 15000;
const uint32_t POLL_MS = 20000;
const uint32_t RETRY_MS = 15000;

// ===== DEMO ALERT THRESHOLDS: change 200 to 100 for presentation =====
const int BPM_ALERT_THRESHOLD = 100;    // Trigger when BPM > this value
const int SPO2_ALERT_THRESHOLD = 90;    // Trigger when SpO2 < this value
const uint8_t ALERT_CONSECUTIVE_READINGS = 3;
const uint32_t ALERT_COOLDOWN_MS = 120000;
// ============================================================== 

HardwareSerial modem(1), gpsPort(2);
TwoWire maxBus = TwoWire(0), inaBus = TwoWire(1);
TinyGPSPlus gps;
MAX30105 maxSensor;
Adafruit_INA219 ina(0x40);
bool maxOK=false, inaOK=false;
uint32_t redBuf[100], irBuf[100];
int sampleCount=0, newSamples=0;
int32_t bpm=0, spo2=0;
int8_t validBpm=0, validSpO2=0;
uint32_t lastRed=0,lastIR=0;
uint32_t lastMaxPoll=0, lastMaxSample=0, lastSensorService=0, lastStateReport=0;
float voltage=NAN, currentMA=NAN, batteryPct=NAN;
uint32_t lastTelemetry=0,lastPoll=0,lastBattery=0,lastEventAttempt=0;
int highBpmCount=0, lowSpO2Count=0;
uint32_t lastHighBpmAlert=0, lastLowSpO2Alert=0;
bool highBpmHasAlerted=false, lowSpO2HasAlerted=false;
bool buttonWasDown=false;
uint32_t lastButtonTime=0;

// SOS queue: do not overwrite a button alert with a later telemetry/remote alert.
// RAM queue survives modem resets but not a complete ESP32 power loss.
const uint8_t QUEUE_MAX=8;
struct PendingEvent {
  String reason;
  String body;
};
PendingEvent alerts[QUEUE_MAX];
uint8_t alertCount=0;
bool modemReady=false;
bool resetSeen=false;
uint32_t retryAt=0;
String modemLine;

String makeJson(const String& reason);
void collectMAX();
void readBattery();
void checkButton();
void serviceDevice();
void cooperativeDelay(uint32_t duration);

void queueEvent(const String& reason) {
  if (reason != "button") {
    for(uint8_t i=0;i<alertCount;i++) if(alerts[i].reason==reason) return;
  }
  if(alertCount < QUEUE_MAX) {
    alerts[alertCount].reason=reason;
    alerts[alertCount].body=makeJson(reason);
    ++alertCount;
    Serial.printf("[EVENT] queued=%s pending=%u\n",reason.c_str(),unsigned(alertCount));
  }
  else Serial.println("[QUEUE] FULL: alert not saved; increase QUEUE_MAX or persistent storage");
}
void removeEvent() {
  if(!alertCount)return;
  for(uint8_t i=1;i<alertCount;i++) alerts[i-1]=alerts[i];
  --alertCount;
}
void gpsPump() {while(gpsPort.available())gps.encode(gpsPort.read());}
void noteModem(char c) {
  if(c=='\n') {
    modemLine.trim();
    if(modemLine.indexOf("*ATREADY: 1")>=0) {resetSeen=true;modemReady=false;}
    modemLine="";
  } else if(c!='\r') {
    modemLine+=c;
    if(modemLine.length()>180)modemLine="";
  }
}
void pumpModem() {
  while(modem.available()) {char c=modem.read();Serial.write(c);noteModem(c);serviceDevice();}
}
String jsonEscape(const String& s) {
  String out;
  for(size_t i=0;i<s.length();i++){
    char c=s[i];
    if(c=='"'||c=='\\')out+='\\';
    if(c=='\r'||c=='\n')out+=' ';
    else out+=c;
  }
  return out;
}
String numOrNull(double x,int d=2){return isfinite(x)?String(x,d):"null";}
String gpsLat(){return gps.location.isValid() && gps.location.age()<10000?String(gps.location.lat(),6):"null";}
String gpsLon(){return gps.location.isValid() && gps.location.age()<10000?String(gps.location.lng(),6):"null";}
String makeJson(const String& reason){
  String s="{\"device_id\":\""+String(DEVICE_ID)+"\",\"event\":\""+jsonEscape(reason)+"\"";
  s+=",\"lat\":"+gpsLat()+",\"lon\":"+gpsLon();
  s+=",\"gps_satellites\":"+String(gps.satellites.isValid()?int(gps.satellites.value()):0);
  s+=",\"bpm\":"+(validBpm && bpm>0 && bpm<260 && lastIR>=50000?String(bpm):"null");
  s+=",\"spo2\":"+(validSpO2 && spo2>0 && spo2<=100 && lastIR>=50000?String(spo2):"null");
  s+=",\"battery_pct\":"+numOrNull(batteryPct,1);
  s+=",\"battery_voltage\":"+numOrNull(voltage,3);
  s+=",\"current_ma\":"+numOrNull(currentMA,1)+"}";
  return s;
}

// Returns full AT response, INCLUDING any asynchronous URC which arrives quickly.
// Caller must check both command result OK and async HTTP/NTP result separately.
void checkButton();
String readAT(uint32_t limit,const String& wanted="",bool needOK=true){
  String out,line;bool hasOK=!needOK,hasWanted=wanted.isEmpty();
  uint32_t started=millis();
  while(millis()-started<limit){
    serviceDevice();
    while(modem.available()){
      char c=(char)modem.read();Serial.write(c);noteModem(c);out+=c;
      if(out.length()>6500)out.remove(0,1600);
      if(c=='\n'){
        line.trim();
        if(line=="OK")hasOK=true;
        if(line=="ERROR"||line.startsWith("+CME ERROR:")||line.startsWith("+CMS ERROR:"))return out;
        line="";
      }else if(c!='\r')line+=c;
      if(!hasWanted && (IotProtocol::containsCompleteLine(out.c_str(),wanted.c_str())
          || (wanted=="DOWNLOAD" && out.indexOf("DOWNLOAD")>=0)))hasWanted=true;
      serviceDevice();
    }
    if(hasOK&&hasWanted)return out;
    delay(2);
  }
  return out;
}
bool hasOK(const String& r){return r.indexOf("\r\nOK\r\n")>=0 || r.endsWith("\nOK\r\n") || r.startsWith("OK\r\n");}
String at(const String& cmd,uint32_t timeout=5000,const String& wanted=""){
  pumpModem();
  Serial.print("\n[AT] ");Serial.println(cmd.startsWith("AT+HTTPPARA=\"USERDATA\"")?"HTTP auth header [redacted]":cmd);
  modem.print(cmd);modem.print("\r\n");
  return readAT(timeout,wanted,true);
}
bool atOK(const String& cmd,uint32_t timeout=5000,const String& wanted=""){
  String r=at(cmd,timeout,wanted);
  return hasOK(r) && (wanted.isEmpty()||r.indexOf(wanted)>=0);
}
int parseHttpStatus(const String& r,int expectedMethod){
  return IotProtocol::parseHttpAction(r.c_str(),expectedMethod);
}
int httpAction(int method){
  String r=at(String("AT+HTTPACTION=")+method,10000);
  if(!hasOK(r))return -1;
  int code=parseHttpStatus(r,method);
  if(code>=0)return code;
  // HTTPACTION emits status as an unsolicited result AFTER the initial OK.
  String urc=readAT(60000,"+HTTPACTION:",false);
  return parseHttpStatus(urc,method);
}

bool validClock(){
  String r=at("AT+CCLK?",4000);
  int i=r.indexOf("+CCLK: \"");
  if(!hasOK(r)||i<0)return false;
  int y=r.substring(i+8,i+10).toInt();
  return y>=26 && y<=40; // rough sanity check, not accurate RTC verification
}
bool ntpSync(){
  if(!atOK("AT+CNTPCFG=\"CID\",1"))return false;
  if(!atOK("AT+CNTP=\"pool.ntp.org\",0"))return false;
  String r=at("AT+CNTP",5000);
  if(!hasOK(r))return false;
  if(r.indexOf("+CNTP: 0")<0)r+=readAT(45000,"+CNTP: 0",false);
  return r.indexOf("+CNTP: 0")>=0 && validClock();
}
bool modemRecover(){
  modemReady=false;
  Serial.println("\n[4G] Starting recovery...");
  bool alive=false;
  for(int i=0;i<6;i++){if(atOK("AT",2500)){alive=true;break;}cooperativeDelay(1000);}
  if(!alive)return false;
  if(!atOK("AT+CMEE=2")||!atOK("AT+CPIN?",4000,"+CPIN: READY"))return false;
  String reg=at("AT+CEREG?",4000);int p=reg.indexOf("+CEREG:");
  if(!hasOK(reg)||p<0)return false;
  int comma=reg.indexOf(',',p);if(comma<0)return false;
  int stat=reg.substring(comma+1).toInt();
  if(stat!=1 && stat!=5){Serial.println("[4G] Waiting for registration");return false;}
  if(!atOK("AT+CGATT?",4000,"+CGATT: 1"))return false;
  String pdp=at("AT+CGACT?",4000);
  if(!hasOK(pdp)||pdp.indexOf("+CGACT: 1,1")<0)return false;
  if(!validClock()&&!ntpSync())return false;
  String certs=at("AT+CCERTLIST",5000);
  if(!hasOK(certs)||certs.indexOf(CA_FILE)<0){Serial.println("[TLS] gts_r4.pem missing");return false;}
  if(!atOK("AT+CSSLCFG=\"sslversion\",0,4"))return false;
  if(!atOK(String("AT+CSSLCFG=\"cacert\",0,\"")+CA_FILE+"\""))return false;
  if(!atOK("AT+CSSLCFG=\"authmode\",0,1"))return false;
  if(!atOK("AT+CSSLCFG=\"enableSNI\",0,1"))return false;
  if(!atOK("AT+CSSLCFG=\"ignorelocaltime\",0,0"))return false;
  resetSeen=false;
  modemReady=true;
  Serial.println("[4G] RECOVERY READY: NTP + TLS CA/SNI");
  return true;
}

// Reads HTTP response body from AT+HTTPREAD. Small plain-text command only.
String readHttpBody(){
  String r=at("AT+HTTPREAD=0,256",10000);
  int p=r.indexOf("+HTTPREAD:");
  if(p<0)return "";
  int nl=r.indexOf('\n',p);if(nl<0)return "";
  String s=r.substring(nl+1);
  int tail=s.lastIndexOf("\r\nOK");if(tail>=0)s.remove(tail);
  s.trim();return s;
}
bool httpRequest(bool post,const String& path,const String& data,String& resp){
  resp="";
  if(!modemReady || resetSeen){
    Serial.println("[HTTP-ERROR] Modem not ready or restart detected");
    return false;
  }
  // HTTPDATA requires exact bytes: validate that we send a valid JSON payload.
  if(post && (data.length()<2 || data[0]!='{' || data[data.length()-1]!='}')){
    Serial.println("[HTTP-ERROR] Invalid JSON payload structure");
    return false;
  }
  char requestUrl[384];
  if(!IotProtocol::joinUrl(SERVER_BASE,path.c_str(),requestUrl,sizeof(requestUrl))){
    Serial.println("[HTTP-ERROR] Invalid server URL/path; check SERVER_BASE");
    return false;
  }
  bool session=false, success=false;
  String stage="HTTPINIT";
  // Cleanup is best-effort: it may return ERROR if no previous session exists.
  at("AT+HTTPTERM",2000);
  if(resetSeen){Serial.println("[HTTP-ERROR] Modem reboot during cleanup");return false;}
  if(!atOK("AT+HTTPINIT",10000)) goto failed;
  session=true;
  {
    stage="SSLCFG";
    if(!atOK("AT+HTTPPARA=\"SSLCFG\",0",7000))goto failed;
    stage="URL";
    if(!atOK(String("AT+HTTPPARA=\"URL\",\"")+requestUrl+"\"",10000))goto failed;
    if(post){
      stage="CONTENT";
      if(!atOK("AT+HTTPPARA=\"CONTENT\",\"application/json\"",7000))goto failed;
    }
    stage="USERDATA";
    if(!atOK(String("AT+HTTPPARA=\"USERDATA\",\"X-Device-Key: ")+DEVICE_KEY+"\"",7000))goto failed;
    if(resetSeen){stage="MODEM_RESET";goto failed;}
    if(post){
      stage="HTTPDATA_PROMPT";
      // DOWNLOAD is a prompt, not the final OK of HTTPDATA.
      while(modem.available()){
        char c=(char)modem.read();noteModem(c);serviceDevice();
      }
      Serial.printf("[HTTP] Uploading %u bytes of JSON\n",(unsigned)data.length());
      modem.printf("AT+HTTPDATA=%u,15000\r\n",(unsigned)data.length());
      String ready=readAT(10000,"DOWNLOAD",false);
      if(ready.indexOf("DOWNLOAD")<0 || ready.indexOf("ERROR")>=0 || resetSeen)goto failed;
      stage="HTTPDATA_PAYLOAD";
      modem.write((const uint8_t*)data.c_str(),data.length());
      String accepted=readAT(20000);
      if(!hasOK(accepted)||resetSeen)goto failed;
    }
    stage="HTTPACTION";
    int code=httpAction(post?1:0);
    Serial.printf("[HTTPS] %s %s => %d\n",post?"POST":"GET",path.c_str(),code);
    if(code<200 || code>=300 || resetSeen)goto failed;
    if(!post)resp=readHttpBody();
    success=true;
  }
failed:
  if(!success)Serial.printf("[HTTP-ERROR] stage=%s (modem_reset=%s)\n",stage.c_str(),resetSeen?"YES":"NO");
  if(session && !resetSeen)at("AT+HTTPTERM",5000);
  if(!success)modemReady=false;
  return success;
}

void resetMaxWindow() {
  sampleCount=0;newSamples=0;validBpm=0;validSpO2=0;
  highBpmCount=0;lowSpO2Count=0;
  highBpmHasAlerted=false;lowSpO2HasAlerted=false;
}
void collectMAX() {
  if(!maxOK)return;
  uint32_t now=millis();
  if(lastMaxPoll && now-lastMaxPoll>1000){
    resetMaxWindow();maxSensor.clearFIFO();lastRed=0;lastIR=0;
    Serial.println("[SENSOR] Sampling gap; collecting a fresh window");
  }
  lastMaxPoll=now;
  uint16_t fetched=maxSensor.check();
  if(fetched>=STORAGE_SIZE){
    resetMaxWindow();
    Serial.println("[SENSOR] FIFO backlog; discarded old calculation window");
  }
  while(maxSensor.available()) {
    uint32_t red=maxSensor.getFIFORed();lastIR=maxSensor.getFIFOIR();maxSensor.nextSample();
    lastRed=red;
    lastMaxSample=millis();
    if(lastIR<50000){resetMaxWindow();continue;}
    if(sampleCount<100){redBuf[sampleCount]=red;irBuf[sampleCount]=lastIR;sampleCount++;}
    else {memmove(redBuf,redBuf+1,99*sizeof(uint32_t));memmove(irBuf,irBuf+1,99*sizeof(uint32_t));redBuf[99]=red;irBuf[99]=lastIR;}
    newSamples++;
    if(sampleCount==100 && newSamples>=25) {
      newSamples=0;
      maxim_heart_rate_and_oxygen_saturation(irBuf,100,redBuf,&spo2,&validSpO2,&bpm,&validBpm);
      const bool bpmReadingOK = validBpm && bpm>0 && bpm<260;
      const bool spo2ReadingOK = validSpO2 && spo2>0 && spo2<=100;
      const bool highBpm = bpmReadingOK && bpm>BPM_ALERT_THRESHOLD;
      const bool lowSpO2 = spo2ReadingOK && spo2<SPO2_ALERT_THRESHOLD;
      // Bad/invalid readings never trigger alerts.
      highBpmCount = highBpm ? min(highBpmCount+1, 100) : 0;
      lowSpO2Count = lowSpO2 ? min(lowSpO2Count+1, 100) : 0;
      if (!highBpm) highBpmHasAlerted=false;
      if (!lowSpO2) lowSpO2HasAlerted=false;
      uint32_t now=millis();
      if(highBpmCount>=ALERT_CONSECUTIVE_READINGS && !highBpmHasAlerted &&
         (lastHighBpmAlert==0 || now-lastHighBpmAlert>=ALERT_COOLDOWN_MS)) {
        queueEvent("high_bpm");
        highBpmHasAlerted=true;
        lastHighBpmAlert=now;
        Serial.printf("[ALERT] HIGH BPM: %ld > %d; GPS=%s,%s\n", (long)bpm,BPM_ALERT_THRESHOLD,gpsLat().c_str(),gpsLon().c_str());
      }
      if(lowSpO2Count>=ALERT_CONSECUTIVE_READINGS && !lowSpO2HasAlerted &&
         (lastLowSpO2Alert==0 || now-lastLowSpO2Alert>=ALERT_COOLDOWN_MS)) {
        queueEvent("low_spo2");
        lowSpO2HasAlerted=true;
        lastLowSpO2Alert=now;
        Serial.printf("[ALERT] LOW SpO2: %ld < %d; GPS=%s,%s\n", (long)spo2,SPO2_ALERT_THRESHOLD,gpsLat().c_str(),gpsLon().c_str());
      }
    }
  }
  if(lastMaxSample && millis()-lastMaxSample>1500){resetMaxWindow();lastRed=0;lastIR=0;}
}
// Approximate resting voltage-to-SoC lookup for a 1S LiPo battery.
// This is NOT a fuel gauge: charging, voltage sag, and battery chemistry affect results.
float estimateLiPoPercent(float volts) {
  const float v[] = {3.00f, 3.30f, 3.50f, 3.60f, 3.70f, 3.75f, 3.80f, 3.85f, 3.90f, 4.00f, 4.10f, 4.20f};
  const float p[] = {0.0f,  5.0f,  10.0f,  15.0f,  25.0f,  35.0f,  45.0f,  55.0f,  65.0f,  80.0f,  90.0f,  100.0f};
  const int n = sizeof(v) / sizeof(v[0]);
  if (!isfinite(volts)) return NAN;
  if (volts <= v[0]) return 0.0f;
  if (volts >= v[n-1]) return 100.0f;
  for (int i=1; i<n; ++i) {
    if (volts <= v[i]) {
      float alpha=(volts-v[i-1])/(v[i]-v[i-1]);
      return p[i-1]+alpha*(p[i]-p[i-1]);
    }
  }
  return NAN;
}

void readBattery() {
  if(!inaOK)return;
  currentMA=ina.getCurrent_mA();
  float busV=ina.getBusVoltage_V(), shuntMV=ina.getShuntVoltage_mV();
  // IN+ near TP4056 OUT+; IN- towards Boost IN+.
  // INA219 bus voltage is measured at IN-, shunt voltage is IN+ minus IN-.
  // Estimate upstream 1S battery-side voltage (not Boost 5V output).
  voltage=busV+shuntMV/1000.0f;
  batteryPct=estimateLiPoPercent(voltage);
  // This estimate is rough under load and unreliable while charging.

}
void checkButton() {
  bool down=digitalRead(BUTTON_PIN)==LOW;
  if(down && !buttonWasDown && millis()-lastButtonTime>250) {
    Serial.println("[SOS] Button press detected");
    queueEvent("button");lastButtonTime=millis();
  }
  buttonWasDown=down;
}

// Keep sensors and SOS input serviced while the modem waits for AT/HTTP replies.
void serviceDevice() {
  gpsPump();
  checkButton();
  uint32_t now=millis();
  if(now-lastSensorService>=10){lastSensorService=now;collectMAX();}
  if(now-lastBattery>=3000){lastBattery=now;readBattery();}
  if(now-lastStateReport>=5000){
    lastStateReport=now;
    Serial.printf("[STATE] modem=%s MAX=%s RED=%lu IR=%lu BPM=%ld(valid=%d) SpO2=%ld(valid=%d) battery=%.3fV pct=%.1f queue=%u\n",
      modemReady?"READY":"OFFLINE",maxOK?"OK":"MISSING",(unsigned long)lastRed,(unsigned long)lastIR,
      (long)bpm,int(validBpm),(long)spo2,int(validSpO2),voltage,batteryPct,unsigned(alertCount));
  }
}
void cooperativeDelay(uint32_t duration) {
  uint32_t started=millis();
  while(millis()-started<duration){serviceDevice();delay(1);}
}
void sendTelemetry(const String& eventName,const String& body,bool queued){
  String response;
  Serial.println("[UPLOAD] event="+eventName+" (GPS="+gpsLat()+","+gpsLon()+")");
  if(httpRequest(true,"/api/device/telemetry",body,response)){
    Serial.println("[UPLOAD] OK");
    if(queued)removeEvent();
  }else Serial.println("[UPLOAD] FAILED; alert kept in RAM");
}
void pollCommand(){
  String s;
  if(httpRequest(false,String("/api/device/command?device_id=")+DEVICE_ID,"",s)){
    if(s.indexOf("LOCATE")>=0) queueEvent("remote");
  }
}
void setup(){
  Serial.begin(115200);delay(400);
  pinMode(BUTTON_PIN,INPUT_PULLUP);
  modem.begin(MODEM_BAUD,SERIAL_8N1,MODEM_RX,MODEM_TX);
  gpsPort.begin(9600,SERIAL_8N1,GPS_RX,GPS_TX);
  maxBus.begin(MAX_SDA,MAX_SCL,100000);
  inaBus.begin(INA_SDA,INA_SCL,100000);
  maxOK=maxSensor.begin(maxBus,I2C_SPEED_STANDARD);
  if(maxOK){maxSensor.setup(60,4,2,100,411,4096);maxSensor.clearFIFO();}
  inaOK=ina.begin(&inaBus);
  Serial.printf("[SENSORS] MAX30102=%s INA219=%s\n",maxOK?"OK":"MISSING",inaOK?"OK":"MISSING");
  Serial.println("[IOT-NGOC] Full firmware boot. USB monitor baud 115200");
  Serial.println("[FIRMWARE] SOS telemetry fix 2026-11-17");
  char endpoint[384];
  if(IotProtocol::joinUrl(SERVER_BASE,"/",endpoint,sizeof(endpoint)))Serial.println(String("[SERVER] ")+endpoint);
  Serial.printf("[ALERT] Thresholds: BPM > %d OR SpO2 < %d (%u readings)\n",BPM_ALERT_THRESHOLD,SPO2_ALERT_THRESHOLD,ALERT_CONSECUTIVE_READINGS);
  Serial.println("[WARNING] Power A7670C from stable board-compatible power; not raw 5V VBAT");
  retryAt=millis()+8000;
  lastTelemetry=millis();lastPoll=millis();
}
void loop(){
  serviceDevice();
  pumpModem();
  if(resetSeen){resetSeen=false;modemReady=false;retryAt=millis()+7000;Serial.println("[MODEM] Boot detected, reconnect scheduled");}
  if(!modemReady && (int32_t)(millis()-retryAt)>=0){
    if(!modemRecover()) {Serial.println("[4G] Retry in 15s");retryAt=millis()+RETRY_MS;}
  }
  if(modemReady){
    if(alertCount && (lastEventAttempt==0||millis()-lastEventAttempt>=RETRY_MS)){
      String reason=alerts[0].reason, body=alerts[0].body;
      lastEventAttempt=millis();sendTelemetry(reason,body,true);lastTelemetry=millis();
    }else if(millis()-lastTelemetry>=TELEMETRY_MS){
      lastTelemetry=millis();sendTelemetry("telemetry",makeJson("telemetry"),false);
    }else if(millis()-lastPoll>=POLL_MS){
      lastPoll=millis();pollCommand();
    }
  }
  delay(1);
}
