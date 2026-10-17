# APEX-01 — Operating Modes (Simulator / Serial / Wi-Fi Hardware)

---

## Overview

APEX-01 supports three data source modes, all feeding into the **same FastAPI backend and React dashboard**:

| Mode | Data Source | Bridge Command | Hardware needed |
|------|-------------|----------------|-----------------|
| **Simulator** | FastF1 Monza Python sim | `python bridge.py` | None |
| **Serial** | ESP32 #1 via USB | `python bridge.py --mode serial --port COM3` | ESP32 #1 |
| **Wi-Fi** | ESP32 #1 over Wi-Fi HTTP | `python bridge.py --mode wifi --esp-host http://192.168.x.x` | ESP32 #1 on Wi-Fi |

The FastAPI backend **does not change** between modes. `POST /telemetry` accepts packets from all three.

---

## Mode A: Simulator (Software-Only / Development)

No hardware needed. Uses FastF1-backed Monza telemetry.

### Start sequence (3 terminals)

**Terminal 1 — FastAPI backend:**
```powershell
cd "C:\Users\megav\.gemini\scratch\apex-01-working\telemetry-project\backend"
..\.venv\Scripts\Activate.ps1
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

**Terminal 2 — Bridge (simulator mode):**
```powershell
cd "C:\Users\megav\.gemini\scratch\apex-01-working\telemetry-project"
.venv\Scripts\Activate.ps1
python bridge.py
```

**Terminal 3 — React dashboard (local dev):**
```powershell
cd "C:\Users\megav\.gemini\scratch\apex-01-working\telemetry-project\dashboard-js"
npm run dev
```

Open: http://localhost:5173

---

## Mode B: Hardware via USB Serial (ESP32 #1 connected by cable)

ESP32 #1 prints JSON lines over USB Serial at 115200 baud.

### Step 1 — Flash ESP32 #1
1. Open `apex01_telemetry_master.ino` in Arduino IDE
2. Set SSID/password if you also want Wi-Fi fallback
3. Upload, open Serial Monitor at 115200 — you should see JSON lines like `{"gps":...}`

### Step 2 — Flash ESP32 #2 (ECU Simulator)
1. Open `apex01_ecu_simulator.ino` in Arduino IDE
2. Upload to Unit 2
3. Serial Monitor should show CAN frames: `[CAN TX 0x100] RPM=12450 THR=85% ...`
4. When CAN bus is wired: Unit 1 will merge ECU data automatically (logged as `ESP32_SERIAL_CAN`)

### Step 3 — Start FastAPI
```powershell
cd backend
..\.venv\Scripts\Activate.ps1
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

### Step 4 — Run bridge in serial mode
```powershell
python bridge.py --mode serial --port COM3
# Linux/Mac:
python bridge.py --mode serial --port /dev/ttyUSB0
```

Find the correct COM port in Device Manager (Windows) or `ls /dev/tty*` (Linux).

---

## Mode C: Hardware via Wi-Fi (ESP32 #1 posts directly)

ESP32 #1 posts JSON to FastAPI over Wi-Fi. The bridge only polls and forwards.

### Step 1 — Find your PC's local IP
```powershell
ipconfig
```
Note the **IPv4 Address** under your Wi-Fi adapter, e.g. `YOUR_COMPUTER_LAN_IP`

### Step 2 — Update ESP32 #1 firmware
In `apex01_telemetry_master.ino`:
```cpp
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char* SERVER_URL    = "http://YOUR_COMPUTER_LAN_IP:8000/telemetry";  // ← your PC IP
```

### Step 3 — Start FastAPI bound to all interfaces
```powershell
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

> ⚠️ Use `--host 0.0.0.0` so the ESP32 can reach it over Wi-Fi (not just localhost).

### Step 4 — Run bridge in wifi mode (optional, for forwarding)
```powershell
python bridge.py --mode wifi --esp-host http://YOUR_ESP32_IP
```

Or if ESP32 posts directly to FastAPI, you can skip the bridge entirely.

---

## Dual ESP32 Boot Sequence (Hardware Mode)

```
1. Power on both ESP32s
2. ESP32 #2 (ECU Sim) starts broadcasting CAN @ 50 Hz immediately
3. ESP32 #1 (DAQ Master) boots, initialises sensors, connects to Wi-Fi
4. ESP32 #1 begins reading CAN bus — merges ECU data with sensor readings
5. ESP32 #1 POSTs telemetry JSON to FastAPI every 20 ms
6. Dashboard shows live data with source tag "ESP32_WIFI_CAN"
```

When CAN hardware is absent (Unit 2 not connected):
- ESP32 #1 logs `"[WARN] CAN Bus initialization failed"` 
- Falls back to software-derived RPM/gear/throttle/brake
- Source tag becomes `"ESP32_WIFI"` or `"ESP32_SERIAL"`

---

## Firewall Note (Windows)

```powershell
New-NetFirewallRule -DisplayName "APEX01 FastAPI" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
```

---

## Verify Data is Arriving

```powershell
Invoke-WebRequest -Uri "http://127.0.0.1:8000/telemetry/latest" | Select-Object -ExpandProperty Content
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Bridge crashes at startup | Backend not running | Start FastAPI first |
| `No telemetry` in dashboard | Bridge not running | Run `python bridge.py` |
| Serial mode: no data | Wrong COM port | Check Device Manager |
| Serial mode: JSON parse errors | Firmware debug prints | Only JSON lines are forwarded; debug lines ignored |
| CAN not working | SN65HVD230 wiring or termination | Check 60Ω resistors at both ends |
| GPS shows 0,0 | No satellite fix | Wait outdoors 30–90 seconds |
| DS18B20 reads -127°C | Missing pull-up | Check 4.7 kΩ on GPIO 4 |
| Wheel speed always 0 | Hall sensor gap | Check 2–5 mm air gap, magnet polarity |
| SD card fails | Wrong format | Format FAT32 ≤ 32 GB, check GPIO 5/18/19/23 |
| Transmission rate | Too fast for Wi-Fi | Increase `TELEMETRY_INTERVAL_MS` to 50 ms |

---

## Transmission Rate Tuning

| Rate | `TELEMETRY_INTERVAL_MS` | Use case |
|------|------------------------|---------|
| 50 Hz | 20 ms | Optimal — best data fidelity |
| 20 Hz | 50 ms | Congested Wi-Fi |
| 10 Hz | 100 ms | Debug / power saving |
