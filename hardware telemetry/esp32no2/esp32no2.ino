
#include "driver/twai.h"

#define CAN_TX 14
#define CAN_RX 36

uint32_t lastSend = 0;
uint32_t counter = 0;

bool startCAN() {
  twai_general_config_t g =
      TWAI_GENERAL_CONFIG_DEFAULT(
          (gpio_num_t)CAN_TX,
          (gpio_num_t)CAN_RX,
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

  Serial.println("ECU simulator CAN started at 500 kbit/s");
  return true;
}

bool sendCAN(uint32_t id, uint8_t b0, uint8_t b1) {
  twai_message_t msg = {};
  msg.identifier = id;
  msg.extd = 0;
  msg.rtr = 0;
  msg.data_length_code = 2;
  msg.data[0] = b0;
  msg.data[1] = b1;

  esp_err_t result = twai_transmit(&msg, pdMS_TO_TICKS(100));

  if (result != ESP_OK) {
    Serial.printf("CAN TX failed for ID 0x%03lX\n",
                  (unsigned long)id);
    return false;
  }

  return true;
}

void sendValue(uint32_t id, uint16_t value) {
  sendCAN(id, (value >> 8) & 0xFF, value & 0xFF);
}

void setup() {
  Serial.begin(115200);
  delay(500);

  if (!startCAN()) {
    Serial.println("Check CAN wiring and restart.");
  }

  Serial.println("APEX-01 ESP32 #2 ECU simulator ready");
}

void loop() {
  if (millis() - lastSend < 1000) return;
  lastSend = millis();
  counter++;

  // Simulated ECU values
  uint16_t rpm = 2500 + (counter % 20) * 100;
  uint16_t speed = 800 + (counter % 20) * 10; // 0.1 km/h
  uint16_t throttle = 350 + (counter % 10) * 20; // 0.1%
  uint16_t coolant = 900 + (counter % 10) * 5; // 0.1 deg C
  uint8_t gear = 3;
  uint16_t brakePressure = 120 + (counter % 5) * 10; // 0.1 bar

  sendValue(0x100, rpm);
  sendValue(0x101, speed);
  sendValue(0x102, throttle);
  sendValue(0x103, coolant);

  // Gear is sent as the first byte of its two-byte frame.
  sendCAN(0x104, gear, 0);

  sendValue(0x105, brakePressure);

  Serial.printf(
    "ECU TX | RPM=%u | Speed=%.1f km/h | "
    "Throttle=%.1f%% | Coolant=%.1f C | "
    "Gear=%u | Brake=%.1f bar\n",
    rpm, speed / 10.0f, throttle / 10.0f,
    coolant / 10.0f, gear, brakePressure / 10.0f
  );
}
