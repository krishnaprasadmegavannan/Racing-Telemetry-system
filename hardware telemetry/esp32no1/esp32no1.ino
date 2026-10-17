
#include <Wire.h>
#include <SPI.h>
#include <SD.h>
#include <TinyGPSPlus.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include "driver/twai.h"

// ---------- PIN CONFIGURATION ----------
#define DS_PIN       4
#define SD_CS        5
#define HALL_FL      25
#define HALL_FR      26
#define HALL_RL      27
#define HALL_RR      13
#define CAN_TX       14
#define CAN_RX       36
#define GPS_RX       16
#define GPS_TX       17
#define ACS_PIN      34
#define VOLT_PIN     35
#define POT1_PIN     32
#define POT2_PIN     33

// ---------- CALIBRATION ----------
const float WHEEL_CIRCUMFERENCE_M = 1.80f; // CHANGE to actual circumference
const float MAGNETS_PER_REV = 2.0f;         // CHANGE if needed
const float ACS_ZERO_V = 2.50f;             // Calibrate at zero current
const float ACS_SENSITIVITY = 0.100f;       // Example: 100mV/A for 20A ACS712
const float VOLTAGE_DIVIDER_RATIO = 1.0f;   // Set for your voltage sensor
const uint32_t SAMPLE_MS = 1000;

// ---------- OBJECTS ----------
TinyGPSPlus gps;
HardwareSerial GPSSerial(2);
OneWire oneWire(DS_PIN);
DallasTemperature tempSensors(&oneWire);
Adafruit_MPU6050 mpu;
File logFile;

// ---------- SENSOR VALUES ----------
float coolantC = NAN, engineC = NAN;
float ax = 0, ay = 0, az = 0;
float gx = 0, gy = 0, gz = 0;
float currentA = 0, batteryV = 0;
float wheelKmh[4] = {0, 0, 0, 0};

double latitude = 0, longitude = 0;
float gpsSpeed = 0, altitude = 0;
uint32_t satellites = 0;
bool gpsFix = false;

uint16_t rpm = 0;
float throttle = 0, brakePressure = 0, ecuSpeed = 0;
float ecuCoolantC = NAN;
uint8_t gear = 0;
bool ecuSeen = false;

volatile uint32_t wheelPulses[4] = {0, 0, 0, 0};
uint32_t lastPulses[4] = {0, 0, 0, 0};
uint32_t lastSample = 0;
uint32_t sequenceNumber = 0;

// ---------- HALL INTERRUPTS ----------
void IRAM_ATTR hallFL() { wheelPulses[0]++; }
void IRAM_ATTR hallFR() { wheelPulses[1]++; }
void IRAM_ATTR hallRL() { wheelPulses[2]++; }
void IRAM_ATTR hallRR() { wheelPulses[3]++; }

// ---------- CAN ----------
bool startCAN() {
  twai_general_config_t g =
      TWAI_GENERAL_CONFIG_DEFAULT(
          (gpio_num_t)CAN_TX, (gpio_num_t)CAN_RX,
          TWAI_MODE_NORMAL);

  twai_timing_config_t t = TWAI_TIMING_CONFIG_500KBITS();
  twai_filter_config_t f = TWAI_FILTER_CONFIG_ACCEPT_ALL();

  if (twai_driver_install(&g, &t, &f) != ESP_OK) {
    Serial.println("CAN driver installation failed");
    return false;
  }

  if (twai_start() != ESP_OK) {
    Serial.println("CAN start failed");
    return false;
  }

  Serial.println("CAN started at 500 kbit/s");
  return true;
}

void readCAN() {
  twai_message_t msg;

  while (twai_receive(&msg, 0) == ESP_OK) {
    if (msg.extd || msg.rtr || msg.data_length_code < 2) continue;

    uint16_t raw =
        ((uint16_t)msg.data[0] << 8) | msg.data[1];

    switch (msg.identifier) {
      case 0x100:
        rpm = raw;
        ecuSeen = true;
        break;

      case 0x101:
        ecuSpeed = raw / 10.0f;
        ecuSeen = true;
        break;

      case 0x102:
        throttle = raw / 10.0f;
        ecuSeen = true;
        break;

      case 0x103:
        ecuCoolantC = raw / 10.0f;
        ecuSeen = true;
        break;

      case 0x104:
        gear = msg.data[0];
        ecuSeen = true;
        break;

      case 0x105:
        brakePressure = raw / 10.0f;
        ecuSeen = true;
        break;
    }
  }
}

// ---------- SENSOR READINGS ----------
void readGPS() {
  while (GPSSerial.available()) {
    gps.encode(GPSSerial.read());
  }

  gpsFix = gps.location.isValid() &&
           gps.location.age() < 3000;

  if (gpsFix) {
    latitude = gps.location.lat();
    longitude = gps.location.lng();
  }

  if (gps.speed.isValid()) gpsSpeed = gps.speed.kmph();
  if (gps.altitude.isValid()) altitude = gps.altitude.meters();

  if (gps.satellites.isValid()) satellites = gps.satellites.value();
}

void readIMU() {
  sensors_event_t a, g, t;
  mpu.getEvent(&a, &g, &t);

  ax = a.acceleration.x;
  ay = a.acceleration.y;
  az = a.acceleration.z;

  // Adafruit library reports gyro in radians/second.
  gx = g.gyro.x;
  gy = g.gyro.y;
  gz = g.gyro.z;
}

void readTemperatures() {
  tempSensors.requestTemperatures();

  // Device index is not guaranteed to identify a particular probe.
  coolantC = tempSensors.getTempCByIndex(0);
  engineC  = tempSensors.getTempCByIndex(1);

  if (coolantC == DEVICE_DISCONNECTED_C) coolantC = NAN;
  if (engineC == DEVICE_DISCONNECTED_C) engineC = NAN;
}

float readCurrent() {
  // ACS712 OUT is reduced by the external 10k/20k divider.
  // The divider ratio at GPIO34 is 2/3.
  const float ADC_DIVIDER_RATIO = 2.0f / 3.0f;

  uint32_t sum = 0;
  for (int i = 0; i < 20; i++) {
    sum += analogRead(ACS_PIN);
  }

  float adc = (sum / 20.0f) / 4095.0f;
  float pinV = adc * 3.3f;
  float sensorV = pinV / ADC_DIVIDER_RATIO;

  return (sensorV - ACS_ZERO_V) / ACS_SENSITIVITY;
}

float readBatteryVoltage() {
  uint32_t sum = 0;
  for (int i = 0; i < 20; i++) {
    sum += analogRead(VOLT_PIN);
  }

  float pinV = (sum / 20.0f) * 3.3f / 4095.0f;
  return pinV * VOLTAGE_DIVIDER_RATIO;
}

void readWheelSpeeds(float dtSeconds) {
  uint32_t currentPulses[4];

  noInterrupts();
  for (int i = 0; i < 4; i++) {
    currentPulses[i] = wheelPulses[i];
  }
  interrupts();

  for (int i = 0; i < 4; i++) {
    uint32_t delta = currentPulses[i] - lastPulses[i];
    lastPulses[i] = currentPulses[i];

    float revolutions = delta / MAGNETS_PER_REV;
    float metres = revolutions * WHEEL_CIRCUMFERENCE_M;

    wheelKmh[i] = dtSeconds > 0
        ? metres / dtSeconds * 3.6f
        : 0;
  }
}

// ---------- SD LOGGING ----------
void logCSV() {
  if (!logFile) return;

  logFile.printf(
    "%lu,%lu,%.7f,%.7f,%.2f,%.2f,%lu,%d,"
    "%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,"
    "%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,%.2f,"
    "%u,%.1f,%.1f,%.1f,%u\n",
    (unsigned long)millis(),
    (unsigned long)sequenceNumber,
    latitude, longitude, gpsSpeed, altitude,
    (unsigned long)satellites, gpsFix,
    ax, ay, az, gx, gy, gz,
    coolantC, engineC,
    wheelKmh[0], wheelKmh[1],
    wheelKmh[2], wheelKmh[3],
    currentA, batteryV,
    rpm, throttle, brakePressure, ecuSpeed, gear
  );

  logFile.flush();
}

// ---------- OUTPUT ----------
void printTelemetry() {
  Serial.printf(
    "{\"timestamp_ms\":%lu,\"sequence_number\":%lu,"
    "\"gps\":{\"latitude\":%.7f,\"longitude\":%.7f,"
    "\"speed_kmh\":%.2f,\"altitude_m\":%.2f,"
    "\"satellite_count\":%lu,\"fix_status\":\"%s\"},"
    "\"imu\":{\"ax\":%.3f,\"ay\":%.3f,\"az\":%.3f,"
    "\"gx\":%.3f,\"gy\":%.3f,\"gz\":%.3f},"
    "\"temperature\":{\"coolant_c\":%.2f,\"engine_c\":%.2f},"
    "\"wheel_speed_kmh\":{\"front_left\":%.2f,"
    "\"front_right\":%.2f,\"rear_left\":%.2f,"
    "\"rear_right\":%.2f},"
    "\"vehicle\":{\"rpm\":%u,\"throttle_pct\":%.1f,"
    "\"brake_pressure\":%.1f,\"gear\":%u,"
    "\"ecu_speed_kmh\":%.1f},"
    "\"electrical\":{\"battery_current_a\":%.2f,"
    "\"battery_voltage_v\":%.2f},"
    "\"status\":{\"can_received\":%s}}\n",
    (unsigned long)millis(),
    (unsigned long)sequenceNumber,
    latitude, longitude, gpsSpeed, altitude,
    (unsigned long)satellites, gpsFix ? "FIX" : "NO_FIX",
    ax, ay, az, gx, gy, gz,
    coolantC, engineC,
    wheelKmh[0], wheelKmh[1],
    wheelKmh[2], wheelKmh[3],
    rpm, throttle, brakePressure, gear, ecuSpeed,
    currentA, batteryV, ecuSeen ? "true" : "false"
  );
}

// ---------- SETUP ----------
void setup() {
  Serial.begin(115200);
  delay(500);

  analogReadResolution(12);
  analogSetPinAttenuation(ACS_PIN, ADC_11db);
  analogSetPinAttenuation(VOLT_PIN, ADC_11db);

  Wire.begin(21, 22);
  GPSSerial.begin(9600, SERIAL_8N1, GPS_RX, GPS_TX);

  pinMode(HALL_FL, INPUT_PULLUP);
  pinMode(HALL_FR, INPUT_PULLUP);
  pinMode(HALL_RL, INPUT_PULLUP);
  pinMode(HALL_RR, INPUT_PULLUP);

  attachInterrupt(digitalPinToInterrupt(HALL_FL), hallFL, FALLING);
  attachInterrupt(digitalPinToInterrupt(HALL_FR), hallFR, FALLING);
  attachInterrupt(digitalPinToInterrupt(HALL_RL), hallRL, FALLING);
  attachInterrupt(digitalPinToInterrupt(HALL_RR), hallRR, FALLING);

  if (!mpu.begin()) {
    Serial.println("MPU6050 not detected; check wiring.");
  } else {
    mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
    mpu.setGyroRange(MPU6050_RANGE_500_DEG);
    mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);
    Serial.println("MPU6050 ready");
  }

  tempSensors.begin();

  if (!SD.begin(SD_CS)) {
    Serial.println("MicroSD initialization failed");
  } else {
    logFile = SD.open("/apex01.csv", FILE_APPEND);
    if (logFile && logFile.size() == 0) {
      logFile.println(
        "time_ms,sequence,latitude,longitude,gps_kmh,altitude_m,"
        "satellites,gps_fix,ax,ay,az,gx,gy,gz,coolant_c,engine_c,"
        "fl_kmh,fr_kmh,rl_kmh,rr_kmh,current_a,voltage_v,"
        "rpm,throttle_pct,brake_pressure,ecu_speed_kmh,gear"
      );
      logFile.flush();
    }
  }

  startCAN();
  Serial.println("APEX-01 ESP32 #1 DAQ ready");
}

// ---------- LOOP ----------
void loop() {
  readGPS();
  readCAN();

  uint32_t now = millis();

  if (now - lastSample >= SAMPLE_MS) {
    float dt = (now - lastSample) / 1000.0f;
    lastSample = now;
    sequenceNumber++;

    readIMU();
    readTemperatures();
    readWheelSpeeds(dt);

    currentA = readCurrent();
    batteryV = readBatteryVoltage();

    printTelemetry();
    logCSV();
  }
}
