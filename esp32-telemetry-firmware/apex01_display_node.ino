/*
 * =====================================================================================
 * PROJECT APEX-01: FORMULA / MOTORSPORT TELEMETRY SYSTEM
 * FIRMWARE: ESP32 SECONDARY — PIT-WALL DISPLAY & ALERT NODE
 * =====================================================================================
 * Target: ESP32 DevKit V1 (ESP-WROOM-32) — UNIT 2
 *
 * ROLE:
 *   This node connects to the same Wi-Fi hotspot as the primary DAQ node and polls
 *   the FastAPI backend's REST endpoint for the latest telemetry packet.  It renders
 *   a live compact dashboard on a 128×64 OLED (SSD1306 over I2C) and drives an RGB
 *   LED strip for alarm states — pit-wall visual warnings without needing a laptop.
 *
 * HARDWARE ON THIS NODE:
 *   - SSD1306 OLED 128×64  → I2C (SDA: GPIO 21 / SCL: GPIO 22)
 *   - RGB LED (common cathode or WS2812 single pixel) → GPIO 15 (R), 2 (G), 4 (B)
 *     For WS2812 strip: connect data-in to GPIO 15 only, comment out non-WS lines.
 *   - Optional: Piezo buzzer → GPIO 13
 *
 * WHAT IT DISPLAYS (auto-rotates pages every 3 s):
 *   Page 0 — SPEED  |  RPM  |  GEAR
 *   Page 1 — THR %  |  BRK %  |  VOLTAGE
 *   Page 2 — COOLANT °C | ENGINE °C
 *   Page 3 — GPS LAT / LON  (updates every 15 s – no flicker)
 *   Page 4 — FL/FR WHEEL km/h  |  RL/RR WHEEL km/h
 *
 * ALERT STATES (RGB LED):
 *   GREEN  — nominal
 *   YELLOW — coolant > 105 °C or brake temp > 850 °C any corner
 *   RED    — coolant > 115 °C or brake temp > 950 °C or RPM > 17 000
 *   BLUE   — Wi-Fi connecting / polling error
 *
 * LIBRARIES NEEDED (install via Arduino Library Manager):
 *   • Adafruit SSD1306      (by Adafruit)
 *   • Adafruit GFX Library  (by Adafruit — dependency of SSD1306)
 *   • ArduinoJson           (by Benoit Blanchon, v6 or v7)
 * =====================================================================================
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// =====================================================================================
// 1. NETWORK CONFIGURATION  — must match primary node's hotspot / router
// =====================================================================================
// NETWORK CONFIGURATION
// Set these values for your local test network before flashing the ESP32.
// Never commit real Wi-Fi credentials to a public repository.
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

// Base URL of the computer running FastAPI.
// Replace the example address with that computer's LAN IP.
const char* BACKEND_HOST = "http://YOUR_COMPUTER_LAN_IP:8000";
// =====================================================================================
// 2. DISPLAY CONFIGURATION
// =====================================================================================
#define SCREEN_WIDTH  128
#define SCREEN_HEIGHT  64
#define OLED_RESET     -1     // No reset pin; use -1
#define OLED_ADDR    0x3C     // Default SSD1306 I2C address

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

// =====================================================================================
// 3. PIN ASSIGNMENTS
// =====================================================================================
#define PIN_LED_R   15   // RGB LED Red (PWM)
#define PIN_LED_G    2   // RGB LED Green (PWM)
#define PIN_LED_B    4   // RGB LED Blue (PWM)
#define PIN_BUZZER  13   // Piezo buzzer (optional)

// =====================================================================================
// 4. LIVE TELEMETRY STATE (populated by polled JSON)
// =====================================================================================
struct TelemetrySnapshot {
  float speed_kmh       = 0.0f;
  int   rpm             = 0;
  int   gear            = 0;
  float throttle_pct    = 0.0f;
  float brake_pct       = 0.0f;
  float battery_voltage = 0.0f;
  float coolant_temp    = 0.0f;
  float engine_temp     = 0.0f;
  float brake_temp_fl   = 0.0f;
  float brake_temp_fr   = 0.0f;
  float brake_temp_rl   = 0.0f;
  float brake_temp_rr   = 0.0f;
  float wheel_fl        = 0.0f;
  float wheel_fr        = 0.0f;
  float wheel_rl        = 0.0f;
  float wheel_rr        = 0.0f;
  float lat             = 0.0f;
  float lon             = 0.0f;
  unsigned long seq     = 0;
};

TelemetrySnapshot tele;

// =====================================================================================
// 5. ALERT STATES
// =====================================================================================
enum AlertLevel { ALERT_OK, ALERT_WARN, ALERT_CRIT, ALERT_NOLINK };

AlertLevel currentAlert = ALERT_NOLINK;

void setRGB(uint8_t r, uint8_t g, uint8_t b) {
  // Common cathode: write duty 0–255
  analogWrite(PIN_LED_R, r);
  analogWrite(PIN_LED_G, g);
  analogWrite(PIN_LED_B, b);
}

void applyAlert(AlertLevel level) {
  switch (level) {
    case ALERT_OK:     setRGB(0,   200, 0);   break;  // Green
    case ALERT_WARN:   setRGB(200, 140, 0);   break;  // Amber
    case ALERT_CRIT:   setRGB(255, 0,   0);   break;  // Red
    case ALERT_NOLINK: setRGB(0,   0,   150); break;  // Blue
  }
}

void evaluateAlerts() {
  if (tele.rpm == 0 && tele.speed_kmh == 0) {
    currentAlert = ALERT_NOLINK;
    return;
  }
  if (tele.coolant_temp > 115.0f ||
      tele.brake_temp_fl > 950.0f || tele.brake_temp_fr > 950.0f ||
      tele.brake_temp_rl > 950.0f || tele.brake_temp_rr > 950.0f ||
      tele.rpm > 17000) {
    currentAlert = ALERT_CRIT;
    // Short buzzer beep on critical
    digitalWrite(PIN_BUZZER, HIGH);
    delay(50);
    digitalWrite(PIN_BUZZER, LOW);
  } else if (tele.coolant_temp > 105.0f ||
             tele.brake_temp_fl > 850.0f || tele.brake_temp_fr > 850.0f ||
             tele.brake_temp_rl > 850.0f || tele.brake_temp_rr > 850.0f) {
    currentAlert = ALERT_WARN;
  } else {
    currentAlert = ALERT_OK;
  }
}

// =====================================================================================
// 6. OLED PAGE RENDERING
// =====================================================================================
uint8_t  displayPage    = 0;
const uint8_t PAGE_COUNT = 5;
unsigned long lastPageFlip = 0;
const unsigned long PAGE_DURATION_MS = 3000;

void renderPage0() {
  // Speed | RPM | Gear
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);
  display.print(F("APEX-01  TELEMETRY"));
  display.drawFastHLine(0, 10, 128, SSD1306_WHITE);

  display.setTextSize(2);
  display.setCursor(0, 14);
  display.print((int)tele.speed_kmh);
  display.setTextSize(1);
  display.setCursor(50, 14);
  display.print(F("km/h"));

  display.setTextSize(2);
  display.setCursor(0, 34);
  display.print(tele.rpm / 1000, 1);
  display.setTextSize(1);
  display.setCursor(50, 34);
  display.print(F("k RPM"));

  display.setTextSize(2);
  display.setCursor(100, 14);
  display.print(F("G"));
  display.print(tele.gear);
}

void renderPage1() {
  // Throttle | Brake | Voltage
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.print(F("PEDALS & POWER"));
  display.drawFastHLine(0, 10, 128, SSD1306_WHITE);

  display.setCursor(0, 15);
  display.print(F("THR: "));
  display.print((int)tele.throttle_pct);
  display.print(F(" %"));

  display.setCursor(0, 27);
  display.print(F("BRK: "));
  display.print((int)tele.brake_pct);
  display.print(F(" %"));

  display.setCursor(0, 39);
  display.print(F("BATT: "));
  display.print(tele.battery_voltage, 1);
  display.print(F(" V"));

  // Mini bar graphs for throttle and brake
  int thrBar = map((int)tele.throttle_pct, 0, 100, 0, 64);
  int brkBar = map((int)tele.brake_pct,    0, 100, 0, 64);
  display.fillRect(64, 15, thrBar, 6, SSD1306_WHITE);
  display.fillRect(64, 27, brkBar, 6, SSD1306_WHITE);
}

void renderPage2() {
  // Coolant | Engine | Brake temps
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.print(F("TEMPERATURES"));
  display.drawFastHLine(0, 10, 128, SSD1306_WHITE);

  display.setCursor(0, 14);
  display.print(F("COOL: "));
  display.print((int)tele.coolant_temp);
  display.print(F(" C"));

  display.setCursor(0, 24);
  display.print(F(" ENG: "));
  display.print((int)tele.engine_temp);
  display.print(F(" C"));

  display.setCursor(0, 36);
  display.print(F("FL:"));
  display.print((int)tele.brake_temp_fl);
  display.print(F(" FR:"));
  display.print((int)tele.brake_temp_fr);

  display.setCursor(0, 48);
  display.print(F("RL:"));
  display.print((int)tele.brake_temp_rl);
  display.print(F(" RR:"));
  display.print((int)tele.brake_temp_rr);

  display.setCursor(100, 36);
  display.print(F("BRK"));
  display.setCursor(100, 44);
  display.print(F("C"));
}

void renderPage3() {
  // GPS
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.print(F("GPS POSITION"));
  display.drawFastHLine(0, 10, 128, SSD1306_WHITE);

  display.setCursor(0, 14);
  display.print(F("LAT:"));
  display.print(tele.lat, 5);

  display.setCursor(0, 26);
  display.print(F("LON:"));
  display.print(tele.lon, 5);

  display.setCursor(0, 44);
  display.print(F("SEQ #"));
  display.print(tele.seq);
}

void renderPage4() {
  // Wheel speeds
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.print(F("WHEEL SPEEDS km/h"));
  display.drawFastHLine(0, 10, 128, SSD1306_WHITE);

  display.setCursor(0, 15);
  display.print(F("FL: "));
  display.print((int)tele.wheel_fl);

  display.setCursor(64, 15);
  display.print(F("FR: "));
  display.print((int)tele.wheel_fr);

  display.setCursor(0, 32);
  display.print(F("RL: "));
  display.print((int)tele.wheel_rl);

  display.setCursor(64, 32);
  display.print(F("RR: "));
  display.print((int)tele.wheel_rr);

  // Show slip: rear avg vs front avg
  float frontAvg = (tele.wheel_fl + tele.wheel_fr) / 2.0f;
  float rearAvg  = (tele.wheel_rl + tele.wheel_rr) / 2.0f;
  float slip     = (frontAvg > 1.0f) ? ((rearAvg - frontAvg) / frontAvg * 100.0f) : 0.0f;
  display.setCursor(0, 50);
  display.print(F("SLIP: "));
  display.print(slip, 1);
  display.print(F(" %"));
}

void renderDisplay() {
  display.clearDisplay();

  switch (displayPage) {
    case 0: renderPage0(); break;
    case 1: renderPage1(); break;
    case 2: renderPage2(); break;
    case 3: renderPage3(); break;
    case 4: renderPage4(); break;
  }
  display.display();
}

// =====================================================================================
// 7. HTTP POLLING FROM FASTAPI /telemetry/latest
// =====================================================================================
bool pollTelemetry() {
  if (WiFi.status() != WL_CONNECTED) return false;

  HTTPClient http;
  String url = String(BACKEND_HOST) + "/telemetry/latest";
  http.begin(url);
  http.setTimeout(400); // Must complete within one poll interval

  int code = http.GET();
  if (code != 200) {
    http.end();
    return false;
  }

  String payload = http.getString();
  http.end();

  // Parse JSON — ArduinoJson v7 style (filter to reduce memory)
  JsonDocument doc;
  DeserializationError err = deserializeJson(doc, payload);
  if (err) return false;

  JsonObject t = doc["telemetry"];
  if (t.isNull()) return false;

  JsonObject gps   = t["gps"];
  JsonObject can   = t["vehicle_can"];
  JsonObject temp  = t["temperature"];
  JsonObject ws    = t["wheel_speeds"];
  JsonObject meta  = t["metadata"];

  tele.speed_kmh       = gps["speed"]           | 0.0f;
  tele.lat             = gps["latitude"]         | 0.0f;
  tele.lon             = gps["longitude"]        | 0.0f;
  tele.rpm             = can["rpm"]              | 0;
  tele.gear            = can["gear"]             | 0;
  tele.throttle_pct    = can["throttle"]         | 0.0f;
  tele.brake_pct       = can["brake_pressure"]   | 0.0f;
  tele.battery_voltage = can["battery_voltage"]  | 0.0f;
  tele.coolant_temp    = temp["coolant_temperature"] | 0.0f;
  tele.engine_temp     = temp["engine_temperature"]  | 0.0f;
  tele.brake_temp_fl   = temp["brake_temp_fl"]   | 0.0f;
  tele.brake_temp_fr   = temp["brake_temp_fr"]   | 0.0f;
  tele.brake_temp_rl   = temp["brake_temp_rl"]   | 0.0f;
  tele.brake_temp_rr   = temp["brake_temp_rr"]   | 0.0f;
  tele.wheel_fl        = ws["front_left"]        | 0.0f;
  tele.wheel_fr        = ws["front_right"]       | 0.0f;
  tele.wheel_rl        = ws["rear_left"]         | 0.0f;
  tele.wheel_rr        = ws["rear_right"]        | 0.0f;
  tele.seq             = meta["sequence_number"] | 0UL;

  return true;
}

// =====================================================================================
// 8. SETUP & LOOP
// =====================================================================================
void setup() {
  Serial.begin(115200);

  // RGB LED pins
  pinMode(PIN_LED_R, OUTPUT);
  pinMode(PIN_LED_G, OUTPUT);
  pinMode(PIN_LED_B, OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);
  applyAlert(ALERT_NOLINK);

  // OLED
  Wire.begin(21, 22);
  if (!display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR)) {
    Serial.println(F("[Display] SSD1306 not found — check wiring!"));
    while (true) { delay(1000); }
  }
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);
  display.println(F("APEX-01"));
  display.println(F("DISPLAY NODE"));
  display.println(F("Connecting WiFi..."));
  display.display();

  // Wi-Fi
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("[Display] Connecting to Wi-Fi");
  unsigned long wifiStart = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - wifiStart < 15000) {
    delay(500);
    Serial.print('.');
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n[Display] Wi-Fi connected: " + WiFi.localIP().toString());
    display.clearDisplay();
    display.setCursor(0, 0);
    display.println(F("WiFi OK"));
    display.println(WiFi.localIP().toString());
    display.display();
    delay(1500);
  } else {
    Serial.println("\n[Display] Wi-Fi FAILED");
  }

  lastPageFlip = millis();
}

unsigned long lastPollTime = 0;

void loop() {
  unsigned long now = millis();

  // Auto-reconnect Wi-Fi
  if (WiFi.status() != WL_CONNECTED) {
    applyAlert(ALERT_NOLINK);
    WiFi.reconnect();
    delay(1000);
    return;
  }

  // Poll telemetry at POLL_INTERVAL_MS
  if (now - lastPollTime >= POLL_INTERVAL_MS) {
    lastPollTime = now;
    bool ok = pollTelemetry();
    if (!ok) {
      Serial.println("[Display] Poll failed");
    }
    evaluateAlerts();
    applyAlert(currentAlert);
  }

  // Auto-advance display page
  if (now - lastPageFlip >= PAGE_DURATION_MS) {
    displayPage = (displayPage + 1) % PAGE_COUNT;
    lastPageFlip = now;
  }

  renderDisplay();
  delay(40); // ~25 fps OLED refresh max (I2C limited anyway)
}
