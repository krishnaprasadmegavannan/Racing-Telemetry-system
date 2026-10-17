/*
 * =====================================================================================
 * PROJECT APEX-01: FORMULA / MOTORSPORT TELEMETRY SYSTEM
 * FIRMWARE: ESP32 PRIMARY DAQ & TELEMETRY MASTER NODE
 * =====================================================================================
 * Target: ESP32 DevKit V1 (ESP-WROOM-32)
 *
 * HARDWARE SENSORS & INTERFACES INTEGRATED:
 *  1. MPU6050 (6-Axis IMU: 3-Axis Accel, 3-Axis Gyro) via I2C (GPIO 21 SDA, 22 SCL)
 *  2. NEO-6M GPS Module via Hardware Serial2 (GPIO 16 RX2, 17 TX2)
 *  3. DS18B20 Waterproof Temperature Probes x2 (Coolant & Engine) via OneWire (GPIO 4)
 *  4. ACS712 Current Sensor via ADC1 (GPIO 33)
 *  5. 0-25V DC Voltage Sensor via ADC1 (GPIO 32)
 *  6. 10k Throttle Potentiometer (0-100%) via ADC1 (GPIO 34)
 *  7. 10k Brake Potentiometer (0-100%) via ADC1 (GPIO 35)
 *  8. Hall Effect Speed Sensors x4 with Neodymium Magnets via Hardware Interrupts:
 *     - Front Left (FL) : GPIO 25
 *     - Front Right (FR): GPIO 26
 *     - Rear Left (RL)  : GPIO 27
 *     - Rear Right (RR) : GPIO 14
 *  9. MicroSD SPI Module (FAT32 Datalogger) via Hardware SPI (CS: GPIO 5)
 * 10. Wi-Fi HTTP / JSON Transceiver streaming to FastAPI backend: POST /telemetry
 * =====================================================================================
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <SPI.h>
#include <SD.h>
#include <ArduinoJson.h>       // ArduinoJson v6 or v7
#include <TinyGPSPlus.h>       // For NEO-6M GPS parsing
#include <OneWire.h>           // For DS18B20 1-Wire
#include <DallasTemperature.h> // For DS18B20 Probes
#include <CAN.h>               // arduino-CAN by Sandeep Mistry — for SN65HVD230

// =====================================================================================
// 1. NETWORK & BACKEND CONFIGURATION
// =====================================================================================
// NETWORK CONFIGURATION
// Configure these values for your own test network before flashing.
// Never commit real Wi-Fi credentials to a public repository.
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// Base URL of the computer running FastAPI.
const char* SERVER_URL = "http://YOUR_COMPUTER_LAN_IP:8000/telemetry";

// Target transmission rate (50Hz = 20ms interval; adjust to 20Hz (50ms) for high Wi-Fi congestion)
const unsigned long TELEMETRY_INTERVAL_MS = 20;

// =====================================================================================
// 2. PIN ASSIGNMENTS — VERIFIED AGAINST ACTUAL WIRING (Oct 2026)
// =====================================================================================
// Analog inputs — ADC1 only (ADC2 disabled when Wi-Fi is active)
#define PIN_CURRENT_SENSE  34  // ADC1_CH6 — ACS712 current sensor OUT
#define PIN_VOLTAGE_SENSE  35  // ADC1_CH7 — Battery voltage sensor OUT
// Note: Throttle and Brake potentiometers NOT wired in current build.
//       GPIO 36 / 39 reserved for future pot additions.

// DS18B20 1-Wire temperature (both coolant and engine probes share one pin)
#define PIN_ONE_WIRE_BUS   4   // Shared 1-Wire DATA — 4.7 kΩ pull-up to 3.3V required

// Hall-effect wheel speed sensors (only FL and FR wired in current build)
#define PIN_HALL_FL        32  // Front Left  wheel speed
#define PIN_HALL_FR        33  // Front Right wheel speed
// RL and RR not wired in current build; reserved for future use:
// #define PIN_HALL_RL     27
// #define PIN_HALL_RR     14

// MicroSD SPI datalogger
#define PIN_SD_CS          5   // SPI Chip Select (SCK: 18, MISO: 19, MOSI: 23)
#define PIN_STATUS_LED     2   // Onboard Blue Status LED

// NEO-6M GPS — Hardware Serial2
#define GPS_RX_PIN         16  // ESP32 RX2 <- NEO-6M TX
#define GPS_TX_PIN         17  // ESP32 TX2 -> NEO-6M RX

// CAN Bus — SN65HVD230 transceiver (ESP32 #1 receives ECU data from ESP32 #2)
// ACTUAL WIRING: CTX/TXD -> GPIO 25 | CRX/RXD -> GPIO 26
#define CAN_TX_PIN         25  // SN65HVD230 CTX/TXD
#define CAN_RX_PIN         26  // SN65HVD230 CRX/RXD
#define CAN_ID_ECU         0x100  // Frame ID broadcast by ESP32 #2

// --- CAN ECU state (populated when CAN frame 0x100 received from ESP32 #2) ---
struct CANECUData {
    uint16_t rpm          = 0;
    uint8_t  throttle     = 0;
    uint8_t  brake        = 0;
    float    canSpeed     = 0.0f;
    uint8_t  gear         = 0;
    uint8_t  flags        = 0x00;
    bool     valid        = false;        // true once a frame has been received
    unsigned long lastMs  = 0;           // millis() of last received frame
};

CANECUData canECU;

// CAN frame staleness threshold: if no frame in 500 ms, fall back to derived values
const unsigned long CAN_STALE_MS = 500;

// =====================================================================================
// 3. VEHICLE DYNAMICS & CALIBRATION CONSTANTS
// =====================================================================================
// Wheel Dimensions & Magnet Configuration
const float WHEEL_DIAMETER_METERS = 0.65f; // Formula tyre ~650mm diameter
const float WHEEL_CIRCUMFERENCE   = 3.14159265f * WHEEL_DIAMETER_METERS; // ~2.042 meters
const int   MAGNETS_PER_WHEEL     = 2;     // 2 magnets mounted on wheel disc

// Voltage Sensor 5:1 divider calibration (25V max into 3.3V ADC)
const float VOLTAGE_DIVIDER_RATIO = 5.0f * (3.3f / 4095.0f);

// ACS712 Current Sensor Calibration (20A module: 100mV/A; 30A module: 66mV/A)
const float ACS712_ZERO_VOLTS     = 2.50f; // Quiescent output at 0A (approx VCC/2)
const float ACS712_SENSITIVITY    = 0.10f; // 100 mV per Ampere for 20A version

// MPU6050 Registers
#define MPU6050_ADDR       0x68
#define MPU6050_PWR_MGMT_1 0x6B
#define MPU6050_ACCEL_XOUT 0x3B
#define MPU6050_GYRO_XOUT  0x43

// =====================================================================================
// 4. GLOBAL OBJECTS & INTERRUPT COUNTERS
// =====================================================================================
HardwareSerial gpsSerial(2);
TinyGPSPlus gps;

OneWire oneWire(PIN_ONE_WIRE_BUS);
DallasTemperature tempSensors(&oneWire);

// Hall Effect pulse counters (must be volatile for interrupt modification)
volatile unsigned long pulsesFL = 0;
volatile unsigned long pulsesFR = 0;
volatile unsigned long pulsesRL = 0;
volatile unsigned long pulsesRR = 0;

// Interrupt Service Routines (ISRs) placed in IRAM for instant execution
void IRAM_ATTR isrWheelFL() { pulsesFL++; }
void IRAM_ATTR isrWheelFR() { pulsesFR++; }
void IRAM_ATTR isrWheelRL() { pulsesRL++; }
void IRAM_ATTR isrWheelRR() { pulsesRR++; }

// Logging & sequence variables
unsigned long sequenceNumber = 0;
unsigned long lastTelemetryTime = 0;
unsigned long lastWheelCalcTime = 0;
unsigned long lastTempReadTime  = 0;

float currentSpeedFL = 0.0f;
float currentSpeedFR = 0.0f;
float currentSpeedRL = 0.0f;
float currentSpeedRR = 0.0f;

float coolantTemp = 90.0f;
float engineTemp  = 105.0f;

bool sdAvailable = false;
File logFile;

// =====================================================================================
// 5. MPU-6050 LOW-LEVEL DRIVER (NO EXTERNAL HEAVY LIBRARIES NEEDED)
// =====================================================================================
struct MPUData {
  float ax, ay, az; // In m/s^2
  float gx, gy, gz; // In deg/s
};

void initMPU6050() {
  Wire.begin(21, 22, 400000); // Fast I2C 400kHz
  Wire.beginTransmission(MPU6050_ADDR);
  Wire.write(MPU6050_PWR_MGMT_1);
  Wire.write(0x00); // Wake up device
  Wire.endTransmission(true);
}

MPUData readMPU6050() {
  MPUData data = {0, 0, 9.81f, 0, 0, 0};
  Wire.beginTransmission(MPU6050_ADDR);
  Wire.write(MPU6050_ACCEL_XOUT);
  if (Wire.endTransmission(false) != 0) return data;
  
  if (Wire.requestFrom(MPU6050_ADDR, 14, true) == 14) {
    int16_t rawAx = (Wire.read() << 8) | Wire.read();
    int16_t rawAy = (Wire.read() << 8) | Wire.read();
    int16_t rawAz = (Wire.read() << 8) | Wire.read();
    Wire.read(); Wire.read(); // Skip internal temp sensor
    int16_t rawGx = (Wire.read() << 8) | Wire.read();
    int16_t rawGy = (Wire.read() << 8) | Wire.read();
    int16_t rawGz = (Wire.read() << 8) | Wire.read();

    // Default scales: Accel +/- 2g (16384 LSB/g), Gyro +/- 250 deg/s (131 LSB/deg/s)
    data.ax = (rawAx / 16384.0f) * 9.80665f;
    data.ay = (rawAy / 16384.0f) * 9.80665f;
    data.az = (rawAz / 16384.0f) * 9.80665f;

    data.gx = rawGx / 131.0f;
    data.gy = rawGy / 131.0f;
    data.gz = rawGz / 131.0f;
  }
  return data;
}

// =====================================================================================
// 6. WHEEL SPEED CALCULATION FROM HALL INTERRUPTS
// =====================================================================================
void updateWheelSpeeds() {
  unsigned long now = millis();
  float dtSeconds = (now - lastWheelCalcTime) / 1000.0f;
  if (dtSeconds <= 0.05f) return; // Update at least every 50ms

  noInterrupts(); // Atomic copy of counters
  unsigned long countFL = pulsesFL; pulsesFL = 0;
  unsigned long countFR = pulsesFR; pulsesFR = 0;
  unsigned long countRL = pulsesRL; pulsesRL = 0;
  unsigned long countRR = pulsesRR; pulsesRR = 0;
  interrupts();

  // Speed (km/h) = (pulses / magnets_per_rev / dt) * circumference * 3.6
  float pulseToKmh = (WHEEL_CIRCUMFERENCE / (float)MAGNETS_PER_WHEEL / dtSeconds) * 3.6f;
  currentSpeedFL = countFL * pulseToKmh;
  currentSpeedFR = countFR * pulseToKmh;
  currentSpeedRL = countRL * pulseToKmh;
  currentSpeedRR = countRR * pulseToKmh;

  lastWheelCalcTime = now;
}

// =====================================================================================
// 7. TEMPERATURE SENSOR SAMPLING (1-WIRE ASYNC SAFE)
// =====================================================================================
void updateTemperatures() {
  unsigned long now = millis();
  if (now - lastTempReadTime < 1000) return; // Update once per second

  tempSensors.requestTemperatures();
  float t1 = tempSensors.getTempCByIndex(0);
  float t2 = tempSensors.getTempCByIndex(1);

  if (t1 > -40.0f && t1 < 150.0f) coolantTemp = t1;
  if (t2 > -40.0f && t2 < 180.0f) engineTemp  = t2;

  lastTempReadTime = now;
}

// =====================================================================================
// 8. SETUP INITIALIZATION
// =====================================================================================
void setup() {
  Serial.begin(115200);
  pinMode(PIN_STATUS_LED, OUTPUT);
  digitalWrite(PIN_STATUS_LED, LOW);

  Serial.println("\n==========================================");
  Serial.println("  APEX-01 TELEMETRY DAQ MASTER SYSTEM     ");
  Serial.println("==========================================");

  // 1. Initialize Analog ADC configuration
  analogReadResolution(12); // 0-4095
  analogSetAttenuation(ADC_11db); // Full 0-3.3V range

  // 2. Initialize Hall Effect Interrupts (FL and FR only in current build)
  //    GPIO 32 and 33 are input-only on ESP32; use external pull-up resistors.
  //    RL and RR sensors not wired — interrupts commented out.
  pinMode(PIN_HALL_FL, INPUT);
  pinMode(PIN_HALL_FR, INPUT);
  attachInterrupt(digitalPinToInterrupt(PIN_HALL_FL), isrWheelFL, FALLING);
  attachInterrupt(digitalPinToInterrupt(PIN_HALL_FR), isrWheelFR, FALLING);
  // attachInterrupt(digitalPinToInterrupt(PIN_HALL_RL), isrWheelRL, FALLING);
  // attachInterrupt(digitalPinToInterrupt(PIN_HALL_RR), isrWheelRR, FALLING);

  // 3. Initialize I2C and MPU6050
  initMPU6050();
  Serial.println("[OK] MPU-6050 6-Axis IMU Initialized (Fast I2C 400kHz)");

  // 4. Initialize Hardware Serial2 for GPS
  gpsSerial.begin(9600, SERIAL_8N1, GPS_RX_PIN, GPS_TX_PIN);
  Serial.println("[OK] NEO-6M GPS Serial2 Initialized @ 9600 baud");

  // 5. Initialize DS18B20 Temperature Probes
  tempSensors.begin();
  tempSensors.setWaitForConversion(false); // Non-blocking conversion
  Serial.println("[OK] Dallas DS18B20 Probes Initialized on 1-Wire");

  // 6. Initialize MicroSD Card SPI Datalogger
  if (SD.begin(PIN_SD_CS)) {
    sdAvailable = true;
    Serial.println("[OK] MicroSD Card Module Initialized (FAT32 Datalogger Ready)");
    logFile = SD.open("/telemetry.csv", FILE_APPEND);
    if (logFile) {
      logFile.println("seq,timestamp,speed,rpm,gear,throttle,brake,voltage,current,ax,ay,az");
      logFile.close();
    }
  } else {
    Serial.println("[WARN] MicroSD Card not detected or failed. Logging to SD disabled.");
  }

  // 6b. Initialize CAN Bus — receives ECU data from ESP32 #2 (ECU Simulator)
  //     Non-blocking: if SN65HVD230 is absent, telemetry falls back to derived values.
  CAN.setPins(CAN_RX_PIN, CAN_TX_PIN);
  if (CAN.begin(500E3)) {  // 500 kbps
    Serial.println("[OK] CAN Bus Initialized at 500 kbps — awaiting ECU frames from Unit 2");
  } else {
    Serial.println("[WARN] CAN Bus initialization failed. Falling back to software-derived ECU values.");
  }

  // 7. Connect to Pit-Wall Wi-Fi Network
  Serial.printf("[WIFI] Connecting to SSID: %s ", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  unsigned long wifiStart = millis();
  while (WiFi.status() != WL_CONNECTED && (millis() - wifiStart < 8000)) {
    delay(250);
    Serial.print(".");
    digitalWrite(PIN_STATUS_LED, !digitalRead(PIN_STATUS_LED));
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("\n[OK] Connected to Pit-Wall Wi-Fi! Local IP: %s\n", WiFi.localIP().toString().c_str());
    digitalWrite(PIN_STATUS_LED, HIGH);

    // Synchronize sequence number with Pit-Wall backend if available
    HTTPClient http;
    String latestUrl = String(SERVER_URL) + "/latest";
    http.begin(latestUrl);
    http.setTimeout(1000);
    int code = http.GET();
    if (code == 200) {
      StaticJsonDocument<512> syncDoc;
      deserializeJson(syncDoc, http.getString());
      unsigned long lastSeq = syncDoc["telemetry"]["metadata"]["sequence_number"] | 0UL;
      if (lastSeq > sequenceNumber) {
        sequenceNumber = lastSeq;
        Serial.printf("[SYNC] Synchronized sequence_number to %lu from Pit-Wall backend\n", sequenceNumber);
      }
    }
    http.end();
  } else {
    Serial.println("\n[WARN] Wi-Fi connection timed out. Telemetry will stream via Serial and buffer to SD.");
    digitalWrite(PIN_STATUS_LED, LOW);
  }
}

// =====================================================================================
// 9. MAIN REAL-TIME ACQUISITION & TRANSMISSION LOOP
// =====================================================================================
void loop() {
  // ── 0. Non-blocking CAN receive (ECU data from ESP32 #2) ──────────────────────────
  int packetSize = CAN.parsePacket();
  if (packetSize >= 8 && CAN.packetId() == CAN_ID_ECU) {
    uint8_t buf[8] = {0};
    for (int i = 0; i < 8 && CAN.available(); i++) {
      buf[i] = (uint8_t)CAN.read();
    }
    canECU.rpm       = (uint16_t)(buf[0] | (buf[1] << 8));
    canECU.throttle  = buf[2];
    canECU.brake     = buf[3];
    canECU.canSpeed  = (float)((uint16_t)(buf[4] | (buf[5] << 8))) / 10.0f;
    canECU.gear      = buf[6];
    canECU.flags     = buf[7];
    canECU.valid     = true;
    canECU.lastMs    = millis();
  }

  // Feed GPS parser as bytes arrive on Serial2
  while (gpsSerial.available() > 0) {
    gps.encode(gpsSerial.read());
  }

  unsigned long currentMillis = millis();
  if (currentMillis - lastTelemetryTime < TELEMETRY_INTERVAL_MS) {
    return; // Wait for next 50Hz transmission cycle
  }
  lastTelemetryTime = currentMillis;

  // 1. Read Hall Effect Wheel Speeds
  updateWheelSpeeds();

  // 2. Read MPU-6050 6-Axis IMU
  MPUData imu = readMPU6050();

  // 3. Read Analog Inputs (Electrical only — throttle/brake pots are on ESP32 #2)
  int rawCurrent = analogRead(PIN_CURRENT_SENSE);  // GPIO 34 — ACS712 OUT
  int rawVolt    = analogRead(PIN_VOLTAGE_SENSE);  // GPIO 35 — Battery voltage sensor

  // Electrical bus calculations
  float voltage = constrain(rawVolt * VOLTAGE_DIVIDER_RATIO, 0.0f, 25.0f);
  float sensorVoltage = (rawCurrent / 4095.0f) * 3.3f;
  float currentAmps   = abs((sensorVoltage - ACS712_ZERO_VOLTS) / ACS712_SENSITIVITY);

  // 4. Read Temperatures
  updateTemperatures();

  // 5. Determine whether to use CAN (ESP32 #2) or software-derived ECU values
  bool useCANData = canECU.valid && (millis() - canECU.lastMs < CAN_STALE_MS);

  // Overall vehicle speed: hall sensors fused with GPS, and optionally CAN speed
  float derivedSpeed = (currentSpeedFL + currentSpeedFR) * 0.5f;
  if (gps.speed.isValid() && gps.speed.kmh() > 5.0f) {
    derivedSpeed = (derivedSpeed * 0.7f) + (gps.speed.kmh() * 0.3f);
  }

  float rpm;
  int   gear;
  float finalThrottle;
  float finalBrake;

  if (useCANData) {
    // ── Hardware mode: use real ECU data from ESP32 #2 via CAN ──────────────────
    rpm          = (float)canECU.rpm;
    gear         = (int)canECU.gear;
    finalThrottle = (float)canECU.throttle;
    finalBrake    = (float)canECU.brake;
    // Blend CAN speed into derived speed for validation
    if (canECU.canSpeed > 5.0f) {
      derivedSpeed = (derivedSpeed * 0.5f) + (canECU.canSpeed * 0.5f);
    }
  } else {
    // ── Software / sim mode: derive ECU values from wheel/GPS speed ─────────────
    gear = 1;
    if (derivedSpeed >= 300.0f)      gear = 7;
    else if (derivedSpeed >= 240.0f) gear = 6;
    else if (derivedSpeed >= 180.0f) gear = 5;
    else if (derivedSpeed >= 130.0f) gear = 4;
    else if (derivedSpeed >= 90.0f)  gear = 3;
    else if (derivedSpeed >= 10.0f)  gear = 2;

    rpm = (gear <= 1) ? 7000.0f : 6000.0f + (derivedSpeed / (gear * 50.0f + 10.0f)) * 13000.0f;
    rpm = constrain(rpm, 1000.0f, 19500.0f);

    // Throttle and brake pots are on ESP32 #2, received via CAN.
    // In software-only / no-CAN mode, default to 0.
    finalThrottle = 0.0f;
    finalBrake    = 0.0f;
  }

  // Dynamic brake disk temperature models based on brake % and dissipation
  float brakeHeat = (brakePct / 100.0f) * (derivedSpeed / 350.0f) * 220.0f;
  float brakeTempFL = 720.0f + brakeHeat;
  float brakeTempFR = 720.0f + brakeHeat;
  float brakeTempRL = 680.0f + brakeHeat * 0.85f;
  float brakeTempRR = 680.0f + brakeHeat * 0.85f;

  sequenceNumber++;

  // 6. Assemble JSON matching FastAPI & Apex-01 Telemetry Schema
  StaticJsonDocument<1024> doc;

  // GPS block
  JsonObject gpsObj = doc.createNestedObject("gps");
  gpsObj["latitude"]        = gps.location.isValid() ? gps.location.lat() : 45.6180;
  gpsObj["longitude"]       = gps.location.isValid() ? gps.location.lng() : 9.2810;
  gpsObj["speed"]           = round(derivedSpeed * 100.0f) / 100.0f;
  gpsObj["altitude"]        = gps.altitude.isValid() ? gps.altitude.meters() : 183.0;
  gpsObj["satellite_count"] = gps.satellites.isValid() ? gps.satellites.value() : 12;
  gpsObj["fix_status"]      = gps.location.isValid() ? "3D_FIX" : "NO_FIX";

  // IMU block
  JsonObject imuObj = doc.createNestedObject("imu");
  imuObj["ax"] = round(imu.ax * 1000.0f) / 1000.0f;
  imuObj["ay"] = round(imu.ay * 1000.0f) / 1000.0f;
  imuObj["az"] = round(imu.az * 1000.0f) / 1000.0f;
  imuObj["gx"] = round(imu.gx * 10.0f) / 10.0f;
  imuObj["gy"] = round(imu.gy * 10.0f) / 10.0f;
  imuObj["gz"] = round(imu.gz * 10.0f) / 10.0f;

  // Temperature block
  JsonObject tempObj = doc.createNestedObject("temperature");
  tempObj["coolant_temperature"] = round(coolantTemp * 10.0f) / 10.0f;
  tempObj["engine_temperature"]  = round(engineTemp * 10.0f) / 10.0f;
  tempObj["brake_temp_fl"]       = round(brakeTempFL);
  tempObj["brake_temp_fr"]       = round(brakeTempFR);
  tempObj["brake_temp_rl"]       = round(brakeTempRL);
  tempObj["brake_temp_rr"]       = round(brakeTempRR);

  // Wheel speeds block
  JsonObject wheelsObj = doc.createNestedObject("wheel_speeds");
  wheelsObj["front_left"]  = round(currentSpeedFL * 10.0f) / 10.0f;
  wheelsObj["front_right"] = round(currentSpeedFR * 10.0f) / 10.0f;
  wheelsObj["rear_left"]   = round(currentSpeedRL * 10.0f) / 10.0f;
  wheelsObj["rear_right"]  = round(currentSpeedRR * 10.0f) / 10.0f;

  // Vehicle CAN / Electrical block — uses CAN ECU values if hardware is present
  JsonObject canObj = doc.createNestedObject("vehicle_can");
  canObj["rpm"]             = round(rpm);
  canObj["throttle"]        = round(finalThrottle * 10.0f) / 10.0f;
  canObj["brake_pressure"]  = round(finalBrake * 10.0f) / 10.0f;
  canObj["battery_voltage"] = round(voltage * 100.0f) / 100.0f;
  canObj["battery_current"] = round(currentAmps * 100.0f) / 100.0f;
  canObj["gear"]            = gear;

  // Metadata block
  String txInfo;
  if (WiFi.status() == WL_CONNECTED) {
    txInfo = useCANData ? "ESP32_WIFI_CAN" : "ESP32_WIFI";
  } else {
    txInfo = useCANData ? "ESP32_SERIAL_CAN" : "ESP32_SERIAL";
  }

  JsonObject metaObj = doc.createNestedObject("metadata");
  metaObj["timestamp"]                = (float)(millis() / 1000.0);
  metaObj["sequence_number"]          = sequenceNumber;
  metaObj["sampling_rate"]            = 50.0;
  metaObj["transmission_information"] = txInfo;
  metaObj["status_error_information"] = "OK";

  String jsonPayload;
  serializeJson(doc, jsonPayload);

  // Stream JSON telemetry packet over USB Serial (for bridge.py or direct PC monitoring at 115200 baud)
  Serial.println(jsonPayload);

  // 7. Write to MicroSD Black-Box Datalogger
  if (sdAvailable) {
    logFile = SD.open("/telemetry.csv", FILE_APPEND);
    if (logFile) {
      logFile.printf("%lu,%lu,%.1f,%.0f,%d,%.1f,%.1f,%.2f,%.2f,%.2f,%.2f,%.2f\n",
                     sequenceNumber, millis(), derivedSpeed, rpm, gear,
                     throttlePct, brakePct, voltage, currentAmps,
                     imu.ax, imu.ay, imu.az);
      logFile.close();
    }
  }

  // 8. Stream JSON Payload to FastAPI Backend
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(SERVER_URL);
    http.addHeader("Content-Type", "application/json");
    http.setTimeout(15); // Fast non-blocking timeout for real-time streaming

    int httpCode = http.POST(jsonPayload);
    if (httpCode == 200 || httpCode == 201) {
      digitalWrite(PIN_STATUS_LED, HIGH);
    } else {
      digitalWrite(PIN_STATUS_LED, LOW);
    }
    http.end();
  } else {
    // If Wi-Fi dropped, retry connection in background
    WiFi.reconnect();
  }
}
