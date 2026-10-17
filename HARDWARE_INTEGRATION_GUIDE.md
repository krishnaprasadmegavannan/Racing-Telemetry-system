# APEX-01 — Master Hardware Integration & Harmonization Guide
### Dual-ESP32 Telemetry & ECU Simulation Architecture

---

## 1. System Philosophy & Harmonious Integration

Project **Apex-01 (Racing Telemetry Pitwall)** is designed with a **unified data contract**. The dashboard, backend, and timing engine operate identically whether data originates from the **software simulation (FastF1 Monza dataset)** or from **live physical hardware (Dual-ESP32 ecosystem)**.

```
┌────────────────────────────────────────────────────────────────────────┐
│                   ESP32 #2 — VEHICLE ECU SIMULATOR                     │
│  • Reads Real Throttle Potentiometer (GPIO 34 ADC)                     │
│  • Reads Real Brake Potentiometer (GPIO 35 ADC)                        │
│  • Simulates V10 Engine RPM, Gear, Speed, DRS                          │
│  • Transmits 50Hz CAN Bus Packets (ID: 0x100) via SN65HVD230           │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ CAN Bus (CANH / CANL @ 500 kbps)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│              ESP32 #1 — TELEMETRY DAQ MASTER UNIT (LMU/DAQ)            │
│  • Intercepts & decodes CAN Bus packets from ESP32 #2                  │
│  • Hall Effect Wheel Speed Sensors (FL: GPIO 32, FR: GPIO 33)          │
│  • Current Sensing (ACS712 on GPIO 34) & Voltage Divider (GPIO 35)     │
│  • 6-Axis IMU (MPU6050 I2C: GPIO 21 SDA / 22 SCL)                      │
│  • DS18B20 1-Wire Thermal Probes (GPIO 4)                              │
│  • NEO-6M GPS (UART2: GPIO 16 RX / 17 TX)                             │
│  • MicroSD Logging (SPI: GPIO 5 CS, 18 SCK, 19 MISO, 23 MOSI)          │
│  • Merges Sensor Data + CAN Data into Unified JSON Telemetry Frame     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ USB Serial (115200) or Wi-Fi (HTTP/WS)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                       TELEMETRY BRIDGE (bridge.py)                     │
│  • Auto-detects data source: [SIMULATOR_FASTF1] vs [ESP32_SERIAL_CAN]  │
│  • Normalizes packet structure & forwards to FastAPI backend           │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ REST / WebSockets
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                  RACING TELEMETRY PITWALL (React 19)                   │
│  • Cockpit HUD with Live Ticking Lap Clock & Dynamic Sector Timers     │
│  • F1 Telemetry Client (14 Gauges, RPM, Speed, Pedals, Power)          │
│  • Powertrain & G-G Friction Circle                                    │
│  • Schema & Hardware Bus Diagnostics Inspector                         │
└────────────────────────────────────────────────────────────────────────┘
```

### Automatic Source Arbitration (Software $\leftrightarrow$ Hardware Harmony)
1. **Default Mode (No Hardware Connected):** The system streams the authentic FastF1 Monza dataset. The dashboard header shows:
   `HOTLAP SESSION // FASTF1 MONZA (DEFAULT DATASET)` with an emerald badge `FASTF1 50Hz STREAM`.
2. **Hardware Mode (Dual ESP32s Plugged In):** When `bridge.py` starts reading serial data from ESP32 #1 or receives Wi-Fi packets, the transmission information is tagged as `ESP32_SERIAL_CAN` or `ESP32_WIFI_CAN`. The dashboard dynamically detects this and highlights:
   `HARDWARE LINK // ESP32_SERIAL_CAN (DUAL ESP32)` with a cyan badge `ESP32 HARDWARE LIVE`.
3. **Fail-Safe Fallback:** If ESP32 #2 is disconnected from the CAN bus, ESP32 #1 detects stale CAN data ($>500\text{ ms}$) and smoothly falls back to software-derived RPM and gear, tagging packets as `ESP32_SERIAL` without interrupting the pitwall stream.

---

## 2. Complete Hardware Wiring & Pinout Tables

### ESP32 #1 — Main Telemetry DAQ Master Unit (30-Pin NodeMCU ESP32)

| Module / Sensor | Sensor Pin | ESP32 #1 Pin | Power / Voltage | Function / Notes |
|:---|:---|:---|:---|:---|
| **SN65HVD230 CAN** | 3V3 / VCC | 3V3 | 3.3V DC | Transceiver power |
| | GND | GND | GND | Shared ground reference |
| | CTX / TXD | GPIO 25 | 3.3V Logic | ESP32 TWAI Transmit |
| | CRX / RXD | GPIO 26 | 3.3V Logic | ESP32 TWAI Receive |
| | CANH | CAN Bus High | — | Connected to ESP32 #2 CANH (120Ω Term) |
| | CANL | CAN Bus Low | — | Connected to ESP32 #2 CANL (120Ω Term) |
| **Hall Effect FL** | VCC | 3V3 or 5V | 3.3V–5V DC | Front-Left wheel sensor |
| | GND | GND | GND | Common Ground |
| | OUT | GPIO 32 | 3.3V Logic | Pulse interrupt on falling edge |
| **Hall Effect FR** | VCC | 3V3 or 5V | 3.3V–5V DC | Front-Right wheel sensor |
| | GND | GND | GND | Common Ground |
| | OUT | GPIO 33 | 3.3V Logic | Pulse interrupt on falling edge |
| **ACS712 Current** | VCC | 5V / VIN | 5.0V DC | Current sensor power |
| | GND | GND | GND | Common Ground |
| | OUT | GPIO 34 | 0–3.3V (ADC1_CH6)| Battery discharge current (input-only) |
| **Voltage Divider** | VCC (IN) | Battery (+) | 0–25V DC | 5:1 divider module input |
| | GND | Battery (-) | GND | Battery Ground reference |
| | S (Signal) | GPIO 35 | 0–3.3V (ADC1_CH7)| Scaled voltage analog input (input-only) |
| **MPU6050 (IMU)** | VCC | 3V3 | 3.3V DC | 6-Axis Accelerometer & Gyro |
| | GND | GND | GND | Common Ground |
| | SCL | GPIO 22 | 3.3V I2C | I2C Clock line |
| | SDA | GPIO 21 | 3.3V I2C | I2C Data line |
| **DS18B20 (Temp)** | VDD / VCC | 3V3 | 3.3V DC | Digital temperature probe |
| | GND | GND | GND | Common Ground |
| | DATA | GPIO 4 | 3.3V 1-Wire | Requires 4.7kΩ pull-up to 3.3V |
| **NEO-6M (GPS)** | VCC | 3V3 or 5V | 3.3V–5V DC | Satellite positioning |
| | GND | GND | GND | Common Ground |
| | TX | GPIO 16 | 3.3V UART | ESP32 RX2 (Serial2) |
| | RX | GPIO 17 | 3.3V UART | ESP32 TX2 (Serial2) |
| **MicroSD SPI** | VCC | 3V3 or 5V | 3.3V–5V DC | On-board telemetry datalogger |
| | GND | GND | GND | Common Ground |
| | CS | GPIO 5 | 3.3V SPI | Chip Select |
| | SCK / CLK | GPIO 18 | 3.3V SPI | SPI Bus Clock |
| | MISO | GPIO 19 | 3.3V SPI | SPI Master In Slave Out |
| | MOSI | GPIO 23 | 3.3V SPI | SPI Master Out Slave In |

---

### ESP32 #2 — Vehicle ECU Simulator (30-Pin NodeMCU ESP32)

| Module / Component | Component Pin | ESP32 #2 Pin | Function / Purpose |
|:---|:---|:---|:---|
| **Throttle Potentiometer** | Outer Pin 1 | 3V3 | Reference 3.3V DC supply |
| | Outer Pin 2 | GND | Ground reference |
| | Centre Pin (Wiper) | GPIO 34 | Analog throttle input (ADC1_CH6, 0–4095) |
| **Brake Potentiometer** | Outer Pin 1 | 3V3 | Reference 3.3V DC supply |
| | Outer Pin 2 | GND | Ground reference |
| | Centre Pin (Wiper) | GPIO 35 | Analog brake pressure input (ADC1_CH7, 0–4095) |
| **SN65HVD230 CAN** | 3V3 | 3V3 | 3.3V DC transceiver power |
| | GND | GND | Shared Ground reference |
| | CTX / TXD | GPIO 25 | ESP32 TWAI Transmit line |
| | CRX / RXD | GPIO 26 | ESP32 TWAI Receive line |
| | CANH | CAN Bus High | Connected to ESP32 #1 CANH (120Ω Term) |
| | CANL | CAN Bus Low | Connected to ESP32 #1 CANL (120Ω Term) |

---

### CAN Bus Interconnection Diagram

```
       ESP32 #1 (DAQ MASTER)                  ESP32 #2 (ECU SIMULATOR)
    ┌─────────────────────────┐            ┌─────────────────────────┐
    │ GPIO 25 (CTX) ────────┐ │            │ ┌──────── GPIO 25 (CTX) │
    │ GPIO 26 (CRX) ──────┐ │ │            │ │ ┌────── GPIO 26 (CRX) │
    └─────────────────────┼─┼─┘            └─┼─┼─────────────────────┘
                          │ │                │ │
                    ┌─────┴─┴──────────┐   ┌─┴─┴──────────────┐
                    │  SN65HVD230 #1   │   │   SN65HVD230 #2  │
                    │   TRANSCEIVER    │   │    TRANSCEIVER   │
                    └─────┬──────┬─────┘   └─────┬──────┬─────┘
                          │CANH  │CANL           │CANH  │CANL
                          │      │               │      │
                          ├──────┴──[ 120Ω ]─────┤      │
     CANH Wire ═══════════╪══════════════════════╪══════╪══════════ CANH Bus
     CANL Wire ═══════════╪══════════════════════╪══════╪══════════ CANL Bus
                          │      ├──[ 120Ω ]─────┴──────┤
                          │      │                      │
     GND Wire  ───────────┴──────┴──────────────────────┴────────── Common GND
```

> [!IMPORTANT]
> **CAN Bus Termination:** Ensure a **120Ω resistor** is connected across CANH and CANL at both ends of the bus. Many SN65HVD230 breakout boards have an on-board SMD resistor labeled `120R` or `R2` with jumper pads. If present on both boards, no external resistor is required. Both ESP32s **must share a common ground wire**.

---

## 3. Sensor Reactions & Physical Correlation in Harmony

When the hardware is active, all data channels react synchronously according to vehicle dynamics physics:

1. **Throttle Application (GPIO 34 Potentiometer on ESP32 #2):**
   - Rotating the throttle pot clockwise increases analog voltage on GPIO 34 ($0\text{V} \rightarrow 3.3\text{V}$).
   - ESP32 #2 calculates throttle percentage ($0\% \rightarrow 100\%$) and dynamically increases simulated engine RPM ($6,000 \rightarrow 19,000\text{ RPM}$) and gear shifts ($1 \rightarrow 8$).
   - Current sensor on ESP32 #1 (ACS712) registers increased electrical load from fuel pumps and ECU actuation ($2.5\text{A} \rightarrow 4.5\text{A}$).
   - Engine and coolant temperatures rise dynamically on the dashboard.

2. **Braking Zone (GPIO 35 Potentiometer on ESP32 #2):**
   - Turning the brake pot clockwise increases brake pressure ($0\% \rightarrow 100\%$).
   - Throttle cuts to $0\%$; gear downshifts automatically.
   - Longitudinal acceleration ($a_x$) registers high negative decel (up to $-4.8\text{ G}$).
   - Front and rear brake disk temperatures climb dynamically on the dashboard ($720^\circ\text{C} \rightarrow 880^\circ\text{C}$).
   - A single **`HEAVY BRAKING ZONE`** warning banner flashes on the pitwall without stacking.

3. **Wheel Speed & Wheel Slip:**
   - Hall effect sensors on GPIO 32 and GPIO 33 detect rotational pulses from wheel magnet rings.
   - Rear driven wheels accelerate faster under high throttle, creating realistic wheel slip delta traces on the *Powertrain & Dynamics* page.

4. **Lap Timing & Dynamic Sectors:**
   - GPS coordinates and progress tracking advance the car through Sector 1, Sector 2, and Sector 3.
   - The Cockpit live lap timer actively ticks every 100ms.
   - Each completed lap calculates deltas against Charles Leclerc's benchmark `1:20.161` lap time.

---

## 4. Firmware Setup & Upload Instructions

### Required Arduino Libraries
In Arduino IDE $\rightarrow$ **Sketch** $\rightarrow$ **Include Library** $\rightarrow$ **Manage Libraries**:
1. `ArduinoJson` (v6.21.3 or v7.x) — by Benoit Blanchon
2. `Adafruit MPU6050` & `Adafruit Unified Sensor` — by Adafruit
3. `TinyGPSPlus` — by Mikal Hart
4. `OneWire` — by Paul Stoffregen
5. `DallasTemperature` — by Miles Burton

*(Note: The ESP32 TWAI CAN driver is built directly into the ESP32 Arduino Core — no extra CAN library needed).*

### Flashing Procedure
1. **ESP32 #2 (ECU Simulator):**
   - Connect ESP32 #2 via micro-USB to your PC.
   - Open `esp32-telemetry-firmware/apex01_ecu_simulator.ino`.
   - Select Board: **ESP32 Dev Module**, select its COM port.
   - Click **Upload**.
   - Open Serial Monitor at **115200 baud** — you should see:
     `[APEX-01 ECU] CAN Transmit OK -> ID: 0x100 | RPM=... THROTTLE=... BRAKE=...`

2. **ESP32 #1 (DAQ Master):**
   - Connect ESP32 #1 via micro-USB to your PC.
   - Open `esp32-telemetry-firmware/apex01_telemetry_master.ino`.
   - (Optional) Enter your Wi-Fi SSID and Password if you plan to use Wi-Fi mode.
   - Select Board: **ESP32 Dev Module**, select its COM port.
   - Click **Upload**.
   - Open Serial Monitor at **115200 baud** — you should see valid JSON lines:
     `{"metadata":{...},"gps":{...},"imu":{...},"vehicle_can":{"rpm":...},"temperature":{...}}`
   - Notice the tag: `"transmission_information": "ESP32_SERIAL_CAN"` confirming CAN frames are successfully merged.

---

## 5. Launch Checklist: Seamless Hardware Integration

Follow this sequence to launch the complete system:

### Step 1: Start the Backend
Open a terminal in the project directory:
```powershell
cd C:\Users\megav\.gemini\scratch\apex-01-working\telemetry-project\backend
..\.venv\Scripts\Activate.ps1
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Step 2: Start the Telemetry Bridge
Connect ESP32 #1 to your PC via USB cable (e.g. `COM3`):
```powershell
cd C:\Users\megav\.gemini\scratch\apex-01-working\telemetry-project
.venv\Scripts\Activate.ps1
python bridge.py --mode serial --port COM3
```
*If you are in Wi-Fi mode instead, run:*
```powershell
python bridge.py --mode wifi --esp-host http://192.168.1.xxx
```
The bridge console will immediately display live streams:
```
[#000142|ESP32_SERIAL_CAN] SPD=284.5 RPM=11840 G7 THR=100% BRK=0%
```

### Step 3: Launch the React Dashboard
Open a third terminal:
```powershell
cd C:\Users\megav\.gemini\scratch\apex-01-working\telemetry-project\dashboard-js
npm run dev
```
Navigate to `http://localhost:5173` (or open the deployed site [https://telemetry-project-theta.vercel.app](https://telemetry-project-theta.vercel.app)).

---

## 6. Hardware Troubleshooting & Verification Matrix

| Symptom | Diagnostic Root Cause | Solution |
|:---|:---|:---|
| **ESP32 #1 says `[WARN] CAN Stale`** | ESP32 #2 is unpowered or CAN lines reversed | Check that CANH is wired to CANH and CANL to CANL. Verify common ground. |
| **CAN Initialization Failed** | Missing 120Ω termination or bad GPIO | Check for 120Ω resistance across CANH-CANL with multimeter when powered down. |
| **Throttle / Brake inputs stuck at 0% or 100%** | Wiper pin disconnected or bad pot ground | Test voltage at GPIO 34/35 with multimeter ($0\text{V} \rightarrow 3.3\text{V}$ sweep). |
| **Serial Bridge: `PermissionError` on COM port** | Arduino Serial Monitor is holding the port open | Close Arduino IDE Serial Monitor before running `python bridge.py`. |
| **Wheel Speed is 0 km/h** | Magnet gap too large or inverted magnet | Adjust Hall sensor gap to 2–5 mm. Ensure magnet south pole faces sensor face. |
| **GPS shows 0.000000 coordinates** | Indoor testing with no satellite fix | Move GPS antenna near window or outdoors. Wait 45s for satellite lock (blinking LED). |
| **DS18B20 reads `-127.0°C`** | Missing pull-up resistor | Connect a 4.7kΩ resistor between GPIO 4 and 3V3. |
| **Current sensor reads 0A or erratic** | Offset calibration needed | Ensure ACS712 has solid 5V supply and zero-current baseline is calibrated (~2.5V). |

---

## 7. File Directory Reference

All hardware code, bridge utilities, and documentation reside in your workspace:
- Firmware DAQ Master: [`esp32-telemetry-firmware/apex01_telemetry_master.ino`](file:///C:/Users/megav/.gemini/scratch/apex-01-working/telemetry-project/esp32-telemetry-firmware/apex01_telemetry_master.ino)
- Firmware ECU Simulator: [`esp32-telemetry-firmware/apex01_ecu_simulator.ino`](file:///C:/Users/megav/.gemini/scratch/apex-01-working/telemetry-project/esp32-telemetry-firmware/apex01_ecu_simulator.ino)
- Wiring Guide: [`esp32-telemetry-firmware/WIRING_GUIDE.md`](file:///C:/Users/megav/.gemini/scratch/apex-01-working/telemetry-project/esp32-telemetry-firmware/WIRING_GUIDE.md)
- Telemetry Relay Bridge: [`bridge.py`](file:///C:/Users/megav/.gemini/scratch/apex-01-working/telemetry-project/bridge.py)
- Web Dashboard: [`dashboard-js/`](file:///C:/Users/megav/.gemini/scratch/apex-01-working/telemetry-project/dashboard-js/)
- Backend Service: [`backend/`](file:///C:/Users/megav/.gemini/scratch/apex-01-working/telemetry-project/backend/)
