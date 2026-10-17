#!/usr/bin/env python3
"""
APEX-01 Telemetry Bridge
========================
Relays telemetry data to the FastAPI backend from one of three sources:

  --mode simulator  (default)  Stream from the FastF1-backed Monza simulator
  --mode serial                Read JSON lines from ESP32 #1 via USB Serial
  --mode wifi                  Poll ESP32 #1 directly over Wi-Fi HTTP (no PC bridge needed)

Usage examples:
  python bridge.py                          # software-only simulator mode
  python bridge.py --mode serial --port COM3
  python bridge.py --mode serial --port /dev/ttyUSB0 --baud 115200
  python bridge.py --mode wifi   --esp-host 192.168.1.200

The simulator mode requires no hardware.  Serial and wifi modes require
ESP32 #1 (apex01_telemetry_master) running and accessible.
"""

import argparse
import json
import subprocess
import requests
import time
import sys
from pathlib import Path

# â”€â”€ Argument parsing â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
parser = argparse.ArgumentParser(
    description="APEX-01 Telemetry Bridge â€” simulator / serial / wifi"
)
parser.add_argument(
    "--mode",
    choices=["simulator", "serial", "wifi"],
    default="simulator",
    help="Data source mode (default: simulator)",
)
parser.add_argument(
    "--port",
    default="COM3",
    help="Serial port for ESP32 #1 (serial mode only), e.g. COM3 or /dev/ttyUSB0",
)
parser.add_argument(
    "--baud",
    type=int,
    default=115200,
    help="Serial baud rate (default: 115200)",
)
parser.add_argument(
    "--esp-host",
    default="http://192.168.1.200:80",
    help="ESP32 #1 Wi-Fi HTTP host (wifi mode). Must expose POST /telemetry or GET /status.",
)
parser.add_argument(
    "--backend",
    default="http://127.0.0.1:8000",
    help="FastAPI backend base URL (default: http://127.0.0.1:8000)",
)

args = parser.parse_args()

MODE         = args.mode
BACKEND_URL  = args.backend.rstrip("/") + "/telemetry"
LATEST_URL   = args.backend.rstrip("/") + "/telemetry/latest"
HEALTH_URL   = args.backend.rstrip("/") + "/openapi.json"

# â”€â”€ Check backend is reachable â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print(f"[Bridge] Mode: {MODE.upper()}")
print(f"[Bridge] Backend: {args.backend}")

try:
    r = requests.get(HEALTH_URL, timeout=5)
    r.raise_for_status()
    print("[Bridge] Backend reachable OK")
except requests.RequestException as exc:
    raise SystemExit(
        f"[Bridge] Backend not reachable: {exc}\n"
        "Start FastAPI first:  cd backend && uvicorn main:app --reload"
    )

# â”€â”€ Recover previous sequence number â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
start_seq = 0
try:
    r = requests.get(LATEST_URL, timeout=3)
    if r.status_code == 200:
        meta = r.json().get("telemetry", {}).get("metadata", {})
        start_seq = int(meta.get("sequence_number", 0))
        print(f"[Bridge] Resuming from sequence #{start_seq}")
except Exception:
    pass

seq_counter  = start_seq
current_time = time.time()


# â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def send_packet(session: requests.Session, payload: dict) -> None:
    """POST a clean telemetry packet to the FastAPI backend."""
    global seq_counter, current_time

    seq_counter  += 1
    current_time  = max(time.time(), current_time + 0.001)

    payload["metadata"]["sequence_number"] = seq_counter
    payload["metadata"]["timestamp"]       = current_time

    try:
        resp = session.post(BACKEND_URL, json=payload, timeout=3)
        if resp.status_code in (200, 201):
            v = payload["gps"]["speed"]
            r = payload["vehicle_can"]["rpm"]
            g = payload["vehicle_can"]["gear"]
            t = payload["vehicle_can"]["throttle"]
            b = payload["vehicle_can"]["brake_pressure"]
            src = payload["metadata"]["transmission_information"]
            print(
                f"[#{seq_counter}|{src}] "
                f"SPD={v:.1f} RPM={r:.0f} G{g} "
                f"THR={t:.0f}% BRK={b:.0f}%",
                flush=True,
            )
        else:
            print(f"[#{seq_counter}] HTTP {resp.status_code}: {resp.text[:200]}", flush=True)
    except requests.RequestException as exc:
        print(f"[#{seq_counter}] POST failed: {exc}", flush=True)


def normalise_packet(raw: dict, source: str) -> dict:
    """
    Convert any incoming packet shape to the canonical backend schema.

    Handles both:
    - Simulator packets  (has 'vehicle' key for CAN data)
    - ESP32 packets      (already uses 'vehicle_can' key)
    """
    meta         = raw.get("metadata") or {}
    gps          = raw.get("gps") or {}
    imu          = raw.get("imu") or {}
    temperature  = raw.get("temperature") or {}
    wheels       = raw.get("wheel_speeds") or {}

    # 'vehicle' key = simulator; 'vehicle_can' key = ESP32 firmware
    vehicle = raw.get("vehicle_can") or raw.get("vehicle") or {}

    # Normalise status_error_information to string
    err_info = meta.get("status_error_information", "OK")
    if isinstance(err_info, dict):
        codes   = err_info.get("error_codes", [])
        status  = err_info.get("status", "OK")
        err_str = f"{status}:{','.join(map(str, codes))}" if codes else str(status)
    else:
        err_str = str(err_info)

    return {
        "gps": {
            "latitude":        float(gps.get("latitude", 0)),
            "longitude":       float(gps.get("longitude", 0)),
            "speed":           float(gps.get("speed", 0)),
            "altitude":        float(gps.get("altitude", 0)),
            "satellite_count": int(gps.get("satellite_count", 0)),
            "fix_status":      str(gps.get("fix_status", "3D_FIX")),
        },
        "imu": {
            "ax": float(imu.get("ax", 0)),
            "ay": float(imu.get("ay", 0)),
            "az": float(imu.get("az", 0)),
            "gx": float(imu.get("gx", 0)),
            "gy": float(imu.get("gy", 0)),
            "gz": float(imu.get("gz", 0)),
        },
        "temperature": {
            "coolant_temperature": float(temperature.get("coolant_temperature", 85.0)),
            "engine_temperature":  float(temperature.get("engine_temperature", 105.0)),
            "brake_temp_fl":       float(temperature.get("brake_temp_fl", 720.0)),
            "brake_temp_fr":       float(temperature.get("brake_temp_fr", 720.0)),
            "brake_temp_rl":       float(temperature.get("brake_temp_rl", 680.0)),
            "brake_temp_rr":       float(temperature.get("brake_temp_rr", 680.0)),
        },
        "wheel_speeds": {
            "front_left":  float(wheels.get("front_left", 0)),
            "front_right": float(wheels.get("front_right", 0)),
            "rear_left":   float(wheels.get("rear_left", 0)),
            "rear_right":  float(wheels.get("rear_right", 0)),
        },
        "vehicle_can": {
            "rpm":             float(vehicle.get("rpm", 0)),
            "throttle":        float(vehicle.get("throttle", 0)),
            "brake_pressure":  float(vehicle.get("brake_pressure", 0)),
            "battery_voltage": float(vehicle.get("battery_voltage", 12.0)),
            "battery_current": abs(float(vehicle.get("battery_current", 0))),
            "gear":            int(vehicle.get("gear", 0)),
        },
        "tyre_wear": raw.get("tyre_wear", {}),
        "metadata": {
            "sequence_number":          0,         # filled by send_packet()
            "timestamp":                0.0,       # filled by send_packet()
            "sampling_rate":            float(meta.get("sampling_rate", 50.0)),
            "transmission_information": source,
            "status_error_information": err_str,
        },
    }


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# MODE: simulator â€” FastF1-backed Monza telemetry
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
def run_simulator():
    BASE_DIR = Path(__file__).resolve().parent
    sim_candidates = [
        BASE_DIR / "telemetry-simulator" / "v10_monza.py",
        BASE_DIR / "v10_monza.py",
    ]
    sim_file = next((p for p in sim_candidates if p.is_file()), None)

    if sim_file is None:
        raise SystemExit(
            "[Bridge] Could not find v10_monza.py. "
            "Place it beside bridge.py or inside telemetry-simulator/."
        )

    print(f"[Bridge] Starting simulator: {sim_file}")
    sim = subprocess.Popen(
        [sys.executable, "-u", str(sim_file)],
        cwd=str(sim_file.parent),
        stdout=subprocess.PIPE,
        stderr=None,
        text=True,
        bufsize=1,
    )

    print("[Bridge] Streaming FastF1 Monza data -> FastAPI")
    try:
        with requests.Session() as http:
            for line in sim.stdout:
                line = line.strip()
                if not line:
                    continue
                try:
                    raw    = json.loads(line)
                    packet = normalise_packet(raw, "SIMULATOR_FASTF1")
                    send_packet(http, packet)
                except (json.JSONDecodeError, ValueError, TypeError) as exc:
                    print(f"[Bridge] Bad line: {exc} | {line[:200]}", flush=True)
    finally:
        if sim.stdout:
            sim.stdout.close()
        if sim.poll() is None:
            sim.terminate()
            try:
                sim.wait(timeout=3)
            except subprocess.TimeoutExpired:
                sim.kill()
                sim.wait()
        print("[Bridge] Simulator stopped.")


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# MODE: serial â€” ESP32 #1 via USB Serial (JSON lines at 115200 baud)
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
def run_serial():
    try:
        import serial
    except ImportError:
        raise SystemExit(
            "[Bridge] pyserial not installed. Run: pip install pyserial"
        )

    port = args.port
    baud = args.baud

    print(f"[Bridge] Opening serial port {port} at {baud} baud")
    print("[Bridge] Waiting for ESP32 #1 JSON stream...")

    while True:
        try:
            with serial.Serial(port, baud, timeout=2) as ser, \
                 requests.Session() as http:
                print(f"[Bridge] Serial port {port} open âœ“")
                while True:
                    try:
                        line = ser.readline().decode("utf-8", errors="ignore").strip()
                    except serial.SerialException as exc:
                        print(f"[Bridge] Serial read error: {exc}")
                        break

                    if not line:
                        continue

                    # Skip non-JSON debug lines printed by Arduino Serial.println
                    if not line.startswith("{"):
                        print(f"[ESP32] {line}", flush=True)
                        continue

                    try:
                        raw    = json.loads(line)
                        packet = normalise_packet(raw, "ESP32_SERIAL")
                        send_packet(http, packet)
                    except (json.JSONDecodeError, ValueError, TypeError) as exc:
                        print(f"[Bridge] Bad packet: {exc} | {line[:200]}", flush=True)

        except serial.SerialException as exc:
            print(f"[Bridge] Cannot open {port}: {exc}. Retrying in 3 s...", flush=True)
            time.sleep(3)
        except KeyboardInterrupt:
            print("\n[Bridge] Stopped.")
            break


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# MODE: wifi â€” Poll ESP32 #1 over Wi-Fi HTTP
#   Expects ESP32 #1 to expose GET /status returning the same JSON schema.
#   The poll rate matches the backend expected rate (50 Hz target, throttled here).
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
def run_wifi():
    esp_url = args.esp_host.rstrip("/") + "/status"
    poll_interval = 0.05  # 20 Hz â€” ESP32 HTTP server can't reliably sustain 50 Hz

    print(f"[Bridge] Wi-Fi polling ESP32 #1 at {esp_url} every {int(poll_interval*1000)} ms")

    with requests.Session() as http:
        while True:
            t_start = time.time()
            try:
                r = http.get(esp_url, timeout=1)
                if r.status_code == 200:
                    raw    = r.json()
                    packet = normalise_packet(raw, "ESP32_WIFI")
                    send_packet(http, packet)
                else:
                    print(f"[Bridge] ESP32 HTTP {r.status_code}", flush=True)
            except requests.RequestException as exc:
                print(f"[Bridge] Wi-Fi poll failed: {exc}", flush=True)

            elapsed = time.time() - t_start
            sleep_for = max(0.0, poll_interval - elapsed)
            try:
                time.sleep(sleep_for)
            except KeyboardInterrupt:
                print("\n[Bridge] Stopped.")
                break


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# ENTRY POINT
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
if __name__ == "__main__":
    try:
        if   MODE == "simulator": run_simulator()
        elif MODE == "serial":    run_serial()
        elif MODE == "wifi":      run_wifi()
    except KeyboardInterrupt:
        print("\n[Bridge] Interrupted. Goodbye.")
