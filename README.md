# Racing Telemetry | Pitwall (Project Racing Telemetry system)
### Real-Time Formula 1 Telemetry & Data Acquisition System

**Live Production Demonstration:** [https://telemetry-project-theta.vercel.app](https://telemetry-project-theta.vercel.app)

---

## 1. Overview & Dataset

**Racing Telemetry Pitwall** is a high-performance motorsport telemetry and data acquisition visualization platform. The telemetry engine is directly integrated with the **FastF1 Python Library**, extracting authentic real-world Formula 1 telemetry from the **2022 Italian Grand Prix at Autodromo Nazionale Monza** (Charles Leclerc Pole Position Lap — `1:20.161`).

### Authentic Telemetry Physics & Correlations
Every channel in the live data stream is physically correlated and synchronized:
* **Speed & Gear Mapping**: 343 km/h in 8th gear on the Rettifilo Tribune straight with DRS active; 73 km/h in 2nd gear at Variante del Rettifilo (Turn 1 / Turn 2).
* **Driver Pedal Inputs**: 100% full throttle on straights transitioning to 100% threshold braking in heavy decel zones with 0% throttle.
* **Longitudinal Acceleration ($a_x$)**: Massive decel up to $-4.8\text{ G}$ in braking zones, $+1.6\text{ G}$ under full-power traction.
* **Lateral Acceleration ($a_y$)**: Realistic cornering loads up to $4.2\text{ G}$ through Curva Grande, Curve di Lesmo, Variante Ascari, and Curva Parabolica (Alboreto).
* **Thermal Dynamics**: Brake disc temperatures heat up dynamically to over $850^\circ\text{C}$ in braking zones and cool down on high-speed straights.
* **True Track Positioning**: The circuit map is rendered using a vector SVG path derived from the exact FastF1 spatial telemetry coordinates, guaranteeing the vehicle position marker is **100% on the tarmac at all times**.

---

## 2. Architecture & Components

```
FastF1 Library ───> [scripts/extract_fastf1_monza.py]
                             │
                             ▼
               [api/monza_fastf1_telemetry.json]
                             │
                             ▼
                [api/index.py] (FastAPI Serverless)
                             │
                    WebSocket Stream (10 Hz)
                             │
                             ▼
      [dashboard-js] (React 19 + Vite + Tailwind CSS v4)
      ├── Cockpit HUD (Compact SuperbikeCluster, Monza Vector Map, Sector Timing)
      ├── F1 Telemetry Client (14 Gauges, RPM, Speed, Pedals, Power Traces)
      ├── Powertrain & Dynamics (G-G Friction Circle, 6-Axis IMU, Wheel Slip)
      └── Schema & Hardware Inspector (Raw Data Inspector & Link Diagnostics)
```

---

## 3. Dual-ESP32 Hardware Integration & Harmony

The system is architected for seamless dual-mode operation:
* **Default Mode**: Operates out-of-the-box using the FastF1 Monza telemetry stream.
* **Hardware Mode**: Connect your dual ESP32s (ESP32 #1 DAQ Master + ESP32 #2 ECU Simulator) to stream live hardware sensors, potentiometers, and CAN bus data without altering the backend or dashboard.

For complete wiring, CAN bus schematics, firmware upload steps, and physical correlation notes, see the dedicated guides:
* 📘 [**Master Hardware Integration Guide**](file:///C:/Users/megav/.gemini/scratch/apex-01-working/telemetry-project/HARDWARE_INTEGRATION_GUIDE.md) — Dual-ESP32 architecture, launch checklist, and harmonization.
* 🔌 [**Complete 53-Row Wiring Guide**](file:///C:/Users/megav/.gemini/scratch/apex-01-working/telemetry-project/esp32-telemetry-firmware/WIRING_GUIDE.md) — Pinout tables, pull-up resistors, and power distribution.
* 📦 [**Firmware Libraries Guide**](file:///C:/Users/megav/.gemini/scratch/apex-01-working/telemetry-project/esp32-telemetry-firmware/LIBRARIES.md) — Required Arduino libraries and versions.

---

## 4. Local Installation & Development

### Prerequisites
* Python 3.11+
* Node.js 20+

### Step 1: Install Python Dependencies & Virtualenv
```bash
python -m venv .venv
.venv\Scripts\activate        # On Windows (or source .venv/bin/activate on Linux/macOS)
pip install -r requirements.txt fastf1
```

### Step 2: (Optional) Re-extract FastF1 Dataset
To extract fresh telemetry directly from Formula 1 live timing cache via FastF1:
```bash
python scripts/extract_fastf1_monza.py
```

### Step 3: Run the Dashboard
```bash
cd dashboard-js
npm install
npm run dev
```

### Step 4: Run the Telemetry Streamer Backend
```bash
uvicorn api.index:app --host 0.0.0.0 --port 8000 --reload
```

---

## 4. Production Deployment on Vercel

The production deployment runs on Vercel Serverless:
* **Frontend**: Static React single-page application built with Vite and Tailwind CSS.
* **API & WebSocket**: Python 3.12 ASGI serverless function streaming FastF1 telemetry packets over `wss://`.
* **Zero Deployment Auth Blockers**: Open public demonstration link accessible from any desktop, tablet, or mobile device.

**Production URL:** [https://telemetry-project-theta.vercel.app](https://telemetry-project-theta.vercel.app)
