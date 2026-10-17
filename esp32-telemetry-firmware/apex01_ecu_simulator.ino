/*
 * =====================================================================================
 * PROJECT APEX-01: FORMULA / MOTORSPORT TELEMETRY SYSTEM
 * FIRMWARE: ESP32 #2 — VEHICLE ECU SIMULATOR (CAN-Bus)
 * =====================================================================================
 * Target : ESP32 DevKit V1 (ESP-WROOM-32) — UNIT 2
 *
 * ROLE:
 *   Reads REAL throttle and brake potentiometers via ADC.
 *   Simulates engine RPM, vehicle speed and gear from a lap profile.
 *   Merges real pedal inputs with simulated ECU values and broadcasts
 *   an 8-byte CAN frame at 50 Hz on CAN ID 0x100 for ESP32 #1 to consume.
 *
 * ACTUAL WIRING (verified Oct 2026):
 *   Throttle potentiometer wiper  -> GPIO 34 (ADC1_CH6)
 *   Brake    potentiometer wiper  -> GPIO 35 (ADC1_CH7)
 *   SN65HVD230 CTX / TXD          -> GPIO 25
 *   SN65HVD230 CRX / RXD          -> GPIO 26
 *   SN65HVD230 VCC                -> 3V3
 *   SN65HVD230 GND                -> GND
 *   CAN termination               -> 120 Ohm across CANH-CANL at each end
 *   Status LED                    -> GPIO 2 (onboard)
 *
 * CAN FRAME LAYOUT (ID 0x100, 8 bytes, little-endian):
 *   Bytes 0-1  : RPM         uint16  (0 - 19500)
 *   Byte  2    : Throttle    uint8   (0 - 100 %, from real ADC pot)
 *   Byte  3    : Brake       uint8   (0 - 100 %, from real ADC pot)
 *   Bytes 4-5  : Speed       uint16  (km/h x 10, e.g. 2315 = 231.5 km/h)
 *   Byte  6    : Gear        uint8   (0 - 7)
 *   Byte  7    : Flags       uint8   (bit0=ignition on, bit1=pit limiter)
 *
 * LIBRARY REQUIRED:
 *   CAN by Sandeep Mistry (Arduino Library Manager)
 * =====================================================================================
 */

#include <Arduino.h>
#include <CAN.h>

// =====================================================================================
// 1. PIN ASSIGNMENTS — VERIFIED AGAINST ACTUAL WIRING
// =====================================================================================
#define PIN_THROTTLE_POT   34   // ADC1_CH6 — throttle potentiometer wiper
#define PIN_BRAKE_POT      35   // ADC1_CH7 — brake potentiometer wiper
#define CAN_TX_PIN         25   // SN65HVD230 CTX / TXD
#define CAN_RX_PIN         26   // SN65HVD230 CRX / RXD
#define PIN_LED             2   // Onboard blue LED (blinks on each CAN frame)

// =====================================================================================
// 2. CAN CONFIGURATION
// =====================================================================================
#define CAN_ID_ECU   0x100       // Primary ECU broadcast frame ID
#define CAN_BAUD     500E3       // 500 kbps — standard automotive CAN

// =====================================================================================
// 3. LAP PROFILE — simulated speed targets (km/h) for RPM and gear derivation
//    Based on a simplified Monza-style circuit with 32 waypoints.
//    Throttle and brake come from the REAL pots, not this profile.
// =====================================================================================
const uint8_t LAP_WAYPOINTS = 32;

const float lapSpeed[LAP_WAYPOINTS] = {
    320, 310, 290, 260,   // Pit exit -> T1 approach
     80,  90, 160, 200,   // T1 braking -> Biassono
    230, 280, 310, 325,   // Back straight
    320, 315, 300, 240,   // Lesmo 1 approach
    120, 140, 200, 250,   // Lesmo 1 -> 2
    290, 310, 320, 325,   // Ascari straight
    140, 160, 200, 260,   // Ascari chicane
    300, 320, 325, 160    // Parabolica entry -> finish line
};

const uint16_t lapDuration[LAP_WAYPOINTS] = {
    1500, 1200,  800,  600,
     600,  500,  700,  900,
    1000, 1100, 1200, 1300,
    1400, 1200,  800,  500,
     400,  500,  800, 1000,
    1100, 1200, 1300, 1400,
     500,  600,  800, 1000,
    1100, 1300, 1400,  800
};

// =====================================================================================
// 4. STATE
// =====================================================================================
uint8_t  waypointIdx   = 0;
float    currentSpeed  = 0.0f;
float    targetSpeed   = lapSpeed[0];

unsigned long waypointStart = 0;
unsigned long lastTxTime    = 0;

const unsigned long TX_INTERVAL_MS = 20;   // 50 Hz

// =====================================================================================
// 5. DERIVE GEAR FROM SPEED
// =====================================================================================
uint8_t deriveGear(float speed_kmh) {
    if (speed_kmh >= 300.0f) return 7;
    if (speed_kmh >= 240.0f) return 6;
    if (speed_kmh >= 185.0f) return 5;
    if (speed_kmh >= 135.0f) return 4;
    if (speed_kmh >=  90.0f) return 3;
    if (speed_kmh >=  40.0f) return 2;
    return 1;
}

// =====================================================================================
// 6. DERIVE RPM FROM SPEED AND GEAR
// =====================================================================================
uint16_t deriveRPM(float speed_kmh, uint8_t gear) {
    const float gearRatios[8] = { 0, 3.2f, 2.3f, 1.72f, 1.35f, 1.09f, 0.91f, 0.77f };
    float ratio    = gearRatios[min(gear, (uint8_t)7)];
    float wheelRPS = (speed_kmh / 3.6f) / (0.64f * 3.14159f);
    float rpm      = wheelRPS * ratio * 3.5f * 60.0f;
    return (uint16_t)constrain(rpm, 800.0f, 19500.0f);
}

// =====================================================================================
// 7. READ POTENTIOMETERS
// =====================================================================================
uint8_t readPot(uint8_t pin) {
    // Average 4 samples to reduce ADC noise
    uint32_t sum = 0;
    for (int i = 0; i < 4; i++) sum += analogRead(pin);
    uint32_t avg = sum / 4;
    return (uint8_t)constrain((avg / 4095.0f) * 100.0f, 0.0f, 100.0f);
}

// =====================================================================================
// 8. SETUP
// =====================================================================================
void setup() {
    Serial.begin(115200);
    pinMode(PIN_LED, OUTPUT);
    digitalWrite(PIN_LED, LOW);

    analogReadResolution(12);           // 12-bit ADC (0-4095)
    analogSetAttenuation(ADC_11db);     // Full 0-3.3V range

    Serial.println("\n==========================================");
    Serial.println("  APEX-01 ECU SIMULATOR (Unit 2 / CAN)   ");
    Serial.println("==========================================");
    Serial.println("[OK] ADC initialized — reading throttle (GPIO34) and brake (GPIO35)");

    CAN.setPins(CAN_RX_PIN, CAN_TX_PIN);
    if (!CAN.begin(CAN_BAUD)) {
        Serial.println("[ERR] CAN bus init FAILED. Check SN65HVD230 wiring.");
        while (true) {
            digitalWrite(PIN_LED, HIGH); delay(150);
            digitalWrite(PIN_LED, LOW);  delay(150);
        }
    }

    Serial.println("[OK] CAN bus initialized at 500 kbps (GPIO25=TX, GPIO26=RX)");
    Serial.println("[OK] Broadcasting ECU frame 0x100 at 50 Hz");
    Serial.println("[INFO] Throttle and brake values come from real potentiometers.");

    waypointStart = millis();
    lastTxTime    = millis();
}

// =====================================================================================
// 9. MAIN LOOP
// =====================================================================================
void loop() {
    unsigned long now = millis();

    // -- Advance waypoint when duration elapsed --
    if (now - waypointStart >= lapDuration[waypointIdx]) {
        waypointStart = now;
        waypointIdx   = (waypointIdx + 1) % LAP_WAYPOINTS;
        targetSpeed   = lapSpeed[waypointIdx];
    }

    // -- Smooth speed ramp toward target --
    float maxStep = 15.0f * (TX_INTERVAL_MS / 1000.0f);
    if (currentSpeed < targetSpeed)
        currentSpeed = min(currentSpeed + maxStep, targetSpeed);
    else
        currentSpeed = max(currentSpeed - maxStep * 2.0f, targetSpeed);

    // -- Transmit CAN frame at 50 Hz --
    if (now - lastTxTime >= TX_INTERVAL_MS) {
        lastTxTime = now;

        // ECU-simulated values
        uint8_t  gear     = deriveGear(currentSpeed);
        uint16_t rpm      = deriveRPM(currentSpeed, gear);
        uint16_t speedRaw = (uint16_t)(currentSpeed * 10.0f);
        uint8_t  flags    = 0x01;   // bit0 = ignition ON

        // Real pedal values from physical potentiometers
        uint8_t throttle = readPot(PIN_THROTTLE_POT);
        uint8_t brake    = readPot(PIN_BRAKE_POT);

        CAN.beginPacket(CAN_ID_ECU);
        CAN.write((uint8_t)(rpm & 0xFF));           // byte 0: RPM low
        CAN.write((uint8_t)(rpm >> 8));             // byte 1: RPM high
        CAN.write(throttle);                        // byte 2: Throttle % (REAL ADC)
        CAN.write(brake);                           // byte 3: Brake %   (REAL ADC)
        CAN.write((uint8_t)(speedRaw & 0xFF));      // byte 4: Speed low
        CAN.write((uint8_t)(speedRaw >> 8));        // byte 5: Speed high
        CAN.write(gear);                            // byte 6: Gear
        CAN.write(flags);                           // byte 7: Flags
        CAN.endPacket();

        // Blink LED
        digitalWrite(PIN_LED, !digitalRead(PIN_LED));

        Serial.printf(
            "[CAN TX 0x100] RPM=%u SPD=%.1f G=%u | THR=%u%% (real) BRK=%u%% (real)\n",
            rpm, currentSpeed, gear, throttle, brake
        );
    }
}
