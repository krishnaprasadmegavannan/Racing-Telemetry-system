# APEX-01 ESP32 Firmware — Arduino Library Dependencies

Install all libraries via **Arduino IDE → Sketch → Include Library → Manage Libraries…**

---

## Unit 1 — Primary DAQ Node (`apex01_telemetry_master.ino`)

| Library | Author | Version | Purpose |
|---------|--------|---------|---------|
| **ArduinoJson** | Benoit Blanchon | >= 6.21 (v7 preferred) | JSON serialization for HTTP payload |
| **TinyGPSPlus** | Mikal Hart | >= 1.0.3 | NMEA parsing from NEO-6M GPS |
| **OneWire** | Jim Studt et al. | >= 2.3.7 | 1-Wire protocol for DS18B20 |
| **DallasTemperature** | Miles Burton | >= 3.9.0 | DS18B20 high-level driver |
| **CAN** | Sandeep Mistry | >= 0.3.1 | CAN-bus receive from ESP32 #2 via SN65HVD230 |
| WiFi | Espressif (built-in) | — | Wi-Fi connection |
| HTTPClient | Espressif (built-in) | — | HTTP POST to FastAPI |
| Wire | Arduino (built-in) | — | I2C for MPU6050 |
| SPI | Arduino (built-in) | — | SPI for MicroSD |
| SD | Arduino/Espressif (built-in) | — | FAT32 file logging |

### Install via Library Manager:
1. Search **ArduinoJson** → install "ArduinoJson by Benoit Blanchon"
2. Search **TinyGPSPlus** → install "TinyGPSPlus by Mikal Hart"
3. Search **OneWire** → install "OneWire by Jim Studt, ..."
4. Search **DallasTemperature** → install "DallasTemperature by Miles Burton, ..."
5. Search **CAN** → install "CAN by Sandeep Mistry"

---

## Unit 2 — ECU Simulator (`apex01_ecu_simulator.ino`)

| Library | Author | Version | Purpose |
|---------|--------|---------|---------|
| **CAN** | Sandeep Mistry | >= 0.3.1 | CAN-bus transmit via SN65HVD230 |

> This is the **only** third-party library needed for Unit 2.
> WiFi is not used — Unit 2 communicates exclusively over the CAN bus.

### Install via Library Manager:
1. Search **CAN** → install "CAN by Sandeep Mistry"

---

## Board Package

Add ESP32 board support if not already done:

1. **File → Preferences → Additional Boards Manager URLs**, add:
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
2. **Tools → Board → Boards Manager** → search `esp32` → install **"esp32 by Espressif Systems"** (v2.x or v3.x)
3. Select **Tools → Board → esp32 → ESP32 Dev Module**

### Upload Settings (both units)
| Setting | Value |
|---------|-------|
| Board | ESP32 Dev Module |
| Upload Speed | 921600 |
| CPU Frequency | 240 MHz |
| Flash Mode | QIO |
| Flash Size | 4MB (32Mb) |
| Partition Scheme | Default 4MB with spiffs |
| PSRAM | Disabled |

---

## CAN Bus Notes

- Both ESP32s use **GPIO 25 (CTX/TXD)** and **GPIO 26 (CRX/RXD)** for CAN.
- Both use the same baud rate: **500 kbps**.
- **120 Ohm termination resistor** required at each physical end of the CAN bus.
- Connect the SN65HVD230 **RS pin to GND** to enable high-speed mode (required at 500 kbps).
- CAN frame **ID 0x100** carries throttle and brake from real pots on ESP32 #2 + simulated RPM/gear/speed.
- ESP32 #1 considers CAN data **stale** after 500 ms and falls back to derived values automatically.

---

## ArduinoJson Version Note

The Unit 1 firmware uses the v7 API. If you have v6 installed, upgrade to v7 or swap:
```cpp
// v6:
DynamicJsonDocument doc(2048);
// v7 (default in this firmware):
StaticJsonDocument<1024> doc;
```
