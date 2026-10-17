# APEX-01 Telemetry System — Wiring Guide (Verified Oct 2026)

> All connections listed here have been verified against the actual physical build.

---

## System Overview

```
┌────────────────────────────────────────────────────────────────────┐
│  ESP32 #1 — Primary DAQ Master (apex01_telemetry_master.ino)       │
│  Sensors: GPS, IMU, DS18B20 x2, Hall FL/FR, ACS712, Voltage, SD   │
│  CAN receive: GPIO 25 (CTX) / GPIO 26 (CRX) via SN65HVD230 #1     │
│  Output: Wi-Fi HTTP POST / USB Serial -> FastAPI backend            │
└───────────────────────────┬────────────────────────────────────────┘
                            │  CAN bus (500 kbps)
                            │  CANH / CANL (twisted pair)
                            │  120 Ohm termination at each physical end
┌───────────────────────────┴────────────────────────────────────────┐
│  ESP32 #2 — ECU Simulator (apex01_ecu_simulator.ino)               │
│  Real inputs:  Throttle pot (GPIO 34), Brake pot (GPIO 35)         │
│  Simulated:    RPM, Vehicle speed, Gear (Monza lap profile)        │
│  CAN transmit: GPIO 25 (CTX) / GPIO 26 (CRX) via SN65HVD230 #2    │
└────────────────────────────────────────────────────────────────────┘
```

---

## Complete Connection Table (50 rows — verified)

| No. | Component | Component Pin | Connect To | Purpose |
|----:|-----------|---------------|------------|---------|
| 1 | **ESP32 #1** | USB | USB power | Power during bench testing |
| 2 | MPU6050 | VCC | ESP32 #1 — 3V3 | Sensor power |
| 3 | MPU6050 | GND | ESP32 #1 — GND | Ground |
| 4 | MPU6050 | SDA | ESP32 #1 — GPIO 21 | I2C data |
| 5 | MPU6050 | SCL | ESP32 #1 — GPIO 22 | I2C clock |
| 6 | NEO-6M GPS | VCC | Regulated supply (check module) | Verify 3.3V or 5V |
| 7 | NEO-6M GPS | GND | ESP32 #1 — GND | Ground |
| 8 | NEO-6M GPS | TX | ESP32 #1 — GPIO 16 (RX2) | GPS data to ESP32 |
| 9 | NEO-6M GPS | RX | ESP32 #1 — GPIO 17 (TX2) | ESP32 to GPS |
| 10 | DS18B20 Coolant | VCC (red) | ESP32 #1 — 3V3 | Power |
| 11 | DS18B20 Coolant | GND (black) | ESP32 #1 — GND | Ground |
| 12 | DS18B20 Coolant | DATA (yellow) | ESP32 #1 — GPIO 4 | Shared 1-Wire data |
| 13 | DS18B20 Engine | VCC (red) | ESP32 #1 — 3V3 | Power |
| 14 | DS18B20 Engine | GND (black) | ESP32 #1 — GND | Ground |
| 15 | DS18B20 Engine | DATA (yellow) | ESP32 #1 — GPIO 4 | Join both DATA wires together |
| 16 | 4.7 kΩ resistor | One end | Shared DS18B20 DATA / GPIO 4 | Pull-up |
| 17 | 4.7 kΩ resistor | Other end | ESP32 #1 — 3V3 | Pull-up supply |
| 18 | Hall sensor — FL | VCC | Compatible regulated supply | Check sensor voltage rating |
| 19 | Hall sensor — FL | GND | ESP32 #1 — GND | Ground |
| 20 | Hall sensor — FL | OUT | ESP32 #1 — GPIO 32 | Front Left wheel-speed pulses |
| 21 | Hall sensor — FR | VCC | Compatible regulated supply | Check sensor voltage rating |
| 22 | Hall sensor — FR | GND | ESP32 #1 — GND | Ground |
| 23 | Hall sensor — FR | OUT | ESP32 #1 — GPIO 33 | Front Right wheel-speed pulses |
| 24 | ACS712 current sensor | VCC | 5V (if module requires) | Sensor power |
| 25 | ACS712 current sensor | GND | ESP32 #1 — GND | Ground |
| 26 | ACS712 current sensor | OUT | ESP32 #1 — GPIO 34 (via voltage conditioning) | Analog current measurement |
| 27 | Battery-voltage sensor | OUT | ESP32 #1 — GPIO 35 (via voltage conditioning) | Battery voltage measurement |
| 28 | Battery-voltage sensor | GND | ESP32 #1 — GND | Ground |
| 29 | MicroSD SPI module | VCC | Supply for exact module | Verify voltage compatibility |
| 30 | MicroSD SPI module | GND | ESP32 #1 — GND | Ground |
| 31 | MicroSD SPI module | CS | ESP32 #1 — GPIO 5 | SPI chip select |
| 32 | MicroSD SPI module | SCK | ESP32 #1 — GPIO 18 | SPI clock |
| 33 | MicroSD SPI module | MISO | ESP32 #1 — GPIO 19 | SPI data to ESP32 |
| 34 | MicroSD SPI module | MOSI | ESP32 #1 — GPIO 23 | SPI data from ESP32 |
| 35 | SN65HVD230 #1 (ESP32 #1) | VCC | ESP32 #1 — 3V3 | Transceiver power |
| 36 | SN65HVD230 #1 (ESP32 #1) | GND | ESP32 #1 — GND | Ground |
| 37 | SN65HVD230 #1 (ESP32 #1) | CTX / TXD | ESP32 #1 — GPIO 25 | CAN transmit |
| 38 | SN65HVD230 #1 (ESP32 #1) | CRX / RXD | ESP32 #1 — GPIO 26 | CAN receive |
| 39 | **ESP32 #2** | USB | USB power | Power during bench testing |
| 40 | SN65HVD230 #2 (ESP32 #2) | VCC | ESP32 #2 — 3V3 | Transceiver power |
| 41 | SN65HVD230 #2 (ESP32 #2) | GND | ESP32 #2 — GND | Ground |
| 42 | SN65HVD230 #2 (ESP32 #2) | CTX / TXD | ESP32 #2 — GPIO 25 | CAN transmit |
| 43 | SN65HVD230 #2 (ESP32 #2) | CRX / RXD | ESP32 #2 — GPIO 26 | CAN receive |
| 44 | CAN bus | CANH — module #1 | CANH — module #2 | CAN High wire |
| 45 | CAN bus | CANL — module #1 | CANL — module #2 | CAN Low wire |
| 46 | CAN termination | 120 Ohm resistor | Across CANH and CANL at ESP32 #1 end | Bus termination |
| 47 | CAN termination | 120 Ohm resistor | Across CANH and CANL at ESP32 #2 end | Bus termination |
| 48 | Throttle potentiometer | Outer pin 1 | ESP32 #2 — 3V3 | Reference voltage |
| 49 | Throttle potentiometer | Outer pin 2 | ESP32 #2 — GND | Ground |
| 50 | Throttle potentiometer | Centre pin (wiper) | ESP32 #2 — GPIO 34 | Reads throttle position |
| 51 | Brake potentiometer | Outer pin 1 | ESP32 #2 — 3V3 | Reference voltage |
| 52 | Brake potentiometer | Outer pin 2 | ESP32 #2 — GND | Ground |
| 53 | Brake potentiometer | Centre pin (wiper) | ESP32 #2 — GPIO 35 | Reads brake input |

---

## ESP32 #1 — GPIO Summary

| GPIO | Function | Connected To |
|------|----------|-------------|
| 4 | 1-Wire DATA | DS18B20 x2 (both probes share this pin) + 4.7 kΩ pull-up to 3V3 |
| 5 | SPI CS | MicroSD module |
| 16 | UART2 RX | NEO-6M GPS TX |
| 17 | UART2 TX | NEO-6M GPS RX |
| 18 | SPI SCK | MicroSD module |
| 19 | SPI MISO | MicroSD module |
| 21 | I2C SDA | MPU6050 |
| 22 | I2C SCL | MPU6050 |
| 23 | SPI MOSI | MicroSD module |
| 25 | CAN CTX/TXD | SN65HVD230 #1 transceiver |
| 26 | CAN CRX/RXD | SN65HVD230 #1 transceiver |
| 32 | Digital IN | Hall sensor — Front Left |
| 33 | Digital IN | Hall sensor — Front Right |
| 34 | ADC1 (input only) | ACS712 current sensor OUT |
| 35 | ADC1 (input only) | Battery voltage sensor OUT |

> **Not wired in current build:** Hall RL / RR (GPIO 27, 14), Throttle / Brake pots (on ESP32 #2 instead)

---

## ESP32 #2 — GPIO Summary

| GPIO | Function | Connected To |
|------|----------|-------------|
| 25 | CAN CTX/TXD | SN65HVD230 #2 transceiver |
| 26 | CAN CRX/RXD | SN65HVD230 #2 transceiver |
| 34 | ADC1 (input only) | Throttle potentiometer wiper |
| 35 | ADC1 (input only) | Brake potentiometer wiper |

---

## CAN Bus Wiring Detail

```
ESP32 #1                SN65HVD230 #1           BUS             SN65HVD230 #2           ESP32 #2
GPIO 25 (CTX) -------> TXD                                       TXD <------------- GPIO 25 (CTX)
GPIO 26 (CRX) <------- RXD       CANH --twisted pair-- CANH      RXD -------------> GPIO 26 (CRX)
3V3 --------------------VCC       CANL --twisted pair-- CANL      VCC ---------------- 3V3
GND -------------------- GND                                      GND ---------------- GND

                      [120 Ohm]                               [120 Ohm]
                   CANH to CANL                            CANH to CANL
                  (at ESP32 #1 end)                       (at ESP32 #2 end)
```

**RS / slope-control pin**: Connect to GND for high-speed mode (required at 500 kbps).

---

## SN65HVD230 Breakout Pinout Reference

| Module Label | Function | Connect To |
|-------------|----------|------------|
| VCC | Power | 3V3 |
| GND | Ground | GND |
| CTX or TXD or D | CAN transmit in | ESP32 GPIO 25 |
| CRX or RXD or R | CAN receive out | ESP32 GPIO 26 |
| CANH | CAN High | Bus CANH wire |
| CANL | CAN Low | Bus CANL wire |
| RS | Slope control | GND (enables high-speed mode) |

> Module label names vary by manufacturer. CTX/TXD/D all mean the same pin.

---

## CAN Frame Protocol (ID 0x100, 50 Hz)

| Byte(s) | Field | Type | Source |
|---------|-------|------|--------|
| 0–1 | RPM | uint16 LE (0–19500) | Simulated (lap profile) |
| 2 | Throttle % | uint8 (0–100) | **Real ADC** — GPIO 34 pot |
| 3 | Brake % | uint8 (0–100) | **Real ADC** — GPIO 35 pot |
| 4–5 | Speed km/h x10 | uint16 LE | Simulated (lap profile) |
| 6 | Gear | uint8 (0–7) | Simulated (derived from speed) |
| 7 | Flags | uint8 | bit0 = ignition on |

---

## Resistor Reference

| Signal | Value | Between |
|--------|-------|---------|
| DS18B20 DATA pull-up | 4.7 kΩ | DATA line and 3V3 |
| CAN bus termination | 120 Ohm | CANH and CANL at each end |

---

## Notes on ADC Pins

- GPIO **34** and **35** are **input-only** on ESP32 — no internal pull-up, output, or `INPUT_PULLUP` mode. This is correct for potentiometers and analog sensors.
- Both are on **ADC1** — safe to use while Wi-Fi is active (ADC2 is disabled by Wi-Fi).
- GPIO **32** and **33** are also on ADC1, used here as digital interrupt inputs for Hall sensors. External pull-up resistors required (no internal pull-up on input-only GPIOs).

---

## Software Modes

| Mode | Command | Notes |
|------|---------|-------|
| Simulator (no hardware) | `python bridge.py` | Uses FastF1 Monza data |
| Serial (ESP32 #1 via USB) | `python bridge.py --mode serial --port COM3` | ESP32 #1 must be running |
| Wi-Fi | `python bridge.py --mode wifi --esp-host http://192.168.x.x` | ESP32 #1 posts directly |

---

## Future Expansion (not yet wired)

| Sensor | Planned GPIO | Notes |
|--------|-------------|-------|
| Hall sensor — Rear Left | GPIO 27 | Firmware ready, commented out |
| Hall sensor — Rear Right | GPIO 14 | Firmware ready, commented out |
