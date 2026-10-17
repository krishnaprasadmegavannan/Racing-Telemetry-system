"""
api/index.py — Project Apex-01 / Racing Telemetry Vercel Serverless Entry Point

FastAPI application for Vercel deployment streaming authentic Formula 1 telemetry
sourced from the FastF1 library (2022 Italian Grand Prix, Monza - Charles Leclerc Pole Lap).
"""
import asyncio
import json
import logging
import os
import time as _time
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Racing Telemetry — Monza F1 Pitwall",
    description="Real-world Formula 1 telemetry stream from FastF1 at Autodromo Nazionale Monza.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load the FastF1 Monza dataset
TELEMETRY_DATA = []
TELEMETRY_META = {}

try:
    json_path = os.path.join(os.path.dirname(__file__), "monza_fastf1_telemetry.json")
    if os.path.exists(json_path):
        with open(json_path, "r") as f:
            raw_data = json.load(f)
            TELEMETRY_META = raw_data.get("metadata", {})
            TELEMETRY_DATA = raw_data.get("telemetry", [])
            logger.info("Loaded %d FastF1 telemetry points from %s", len(TELEMETRY_DATA), json_path)
    else:
        logger.warning("Dataset file not found at %s", json_path)
except Exception as e:
    logger.error("Failed to load FastF1 telemetry dataset: %s", e)


@app.get("/")
def root():
    return {
        "project": "Racing Telemetry Pitwall",
        "status": "online",
        "circuit": "Autodromo Nazionale Monza",
        "data_source": "FastF1 2022 Italian Grand Prix (Charles Leclerc Pole Lap - 1:20.161)",
        "total_points": len(TELEMETRY_DATA),
    }


@app.get("/health")
def health():
    return {"status": "healthy", "service": "racing-telemetry-pitwall"}


def get_simulated_lap(lap_num: int, mode: str = "HOTLAP"):
    # Realistic lap sequence for Monza FastF1
    if mode.upper() == "ENDURANCE":
        # Realistic race stint pace at Monza:
        # Base race lap: 84.230s (1:24.230 - 105 kg fuel load)
        # As fuel burns off (-1.85kg/lap), pace improves, but tyre wear adds time
        endurance_deltas = [
            0.0,       # Lap 1: 84.230 (race start pace)
            0.485,     # Lap 2: 84.715 (+0.485, heavy fuel)
            0.250,     # Lap 3: 84.480 (+0.250)
            -0.340,    # Lap 4: 83.890 (-0.340 -> PURPLE Stint Best!)
            0.390,     # Lap 5: 84.620 (+0.390)
            0.920,     # Lap 6: 85.150 (+0.920, tyre thermal deg)
            0.080,     # Lap 7: 84.310 (+0.080)
            0.660,     # Lap 8: 84.890 (+0.660)
            -0.490,    # Lap 9: 83.740 (-0.490 -> PURPLE Stint Best!)
            1.190,     # Lap 10: 85.420 (+1.190, high tyre wear)
        ]
        delta = endurance_deltas[(lap_num - 1) % len(endurance_deltas)]
        base_time = 84.230
        total_time = round(base_time + delta, 3)
        s1 = round(28.640 + (delta * 0.35), 3)
        s2 = round(39.180 + (delta * 0.45), 3)
        s3 = round(total_time - s1 - s2, 3)
    else:
        # HOTLAP Qualifying mode:
        # Base pole lap: 80.161s (1:20.161 - low fuel 12 kg, Soft C4 tyres)
        hotlap_deltas = [
            0.0,       # Lap 1: 80.161 (pole benchmark)
            0.324,     # Lap 2: 80.485 (+0.324)
            0.112,     # Lap 3: 80.273 (+0.112)
            -0.215,    # Lap 4: 79.946 (-0.215 -> PURPLE PB!)
            0.489,     # Lap 5: 80.650 (+0.489)
            0.720,     # Lap 6: 80.881 (+0.720, tyre degradation)
            -0.080,    # Lap 7: 80.081 (-0.080)
            0.250,     # Lap 8: 80.411 (+0.250)
            -0.290,    # Lap 9: 79.871 (-0.290 -> PURPLE PB!)
            0.510,     # Lap 10: 80.671 (+0.510)
        ]
        delta = hotlap_deltas[(lap_num - 1) % len(hotlap_deltas)]
        base_time = 80.161
        total_time = round(base_time + delta, 3)
        s1 = round(27.412 + (delta * 0.35), 3)
        s2 = round(37.224 + (delta * 0.45), 3)
        s3 = round(total_time - s1 - s2, 3)

    return {
        "lap_number": lap_num,
        "lap_time": total_time,
        "lap_time_ms": int(round(total_time * 1000)),
        "s1": s1,
        "s2": s2,
        "s3": s3,
        "mode": mode.upper(),
    }


@app.get("/telemetry/modes")
def get_modes():
    return {
        "modes": {
            "HOTLAP": {
                "benchmark_lap": "1:20.161",
                "fuel_load_kg": 12.0,
                "tyre_compound": "SOFT (C4)",
                "ers_mode": "HOTLAP QUALIFYING DEPLOY (100%)",
                "sectors": {"s1": 27.412, "s2": 37.224, "s3": 15.525},
                "max_speed_kmh": 345.5,
            },
            "ENDURANCE": {
                "benchmark_lap": "1:24.230",
                "fuel_load_kg": 105.0,
                "tyre_compound": "MEDIUM (C3)",
                "ers_mode": "RACE BALANCED (HARVEST/DEPLOY)",
                "sectors": {"s1": 28.640, "s2": 39.180, "s3": 16.410},
                "max_speed_kmh": 330.0,
            },
        }
    }


@app.get("/telemetry/laps")
def get_laps(mode: str = "HOTLAP"):
    mode_clean = mode.upper() if mode else "HOTLAP"
    laps = [get_simulated_lap(i, mode_clean) for i in range(1, 11)]
    return {
        "circuit": "Autodromo Nazionale Monza",
        "mode": mode_clean,
        "benchmark": "1:24.230" if mode_clean == "ENDURANCE" else "1:20.161",
        "laps": laps,
    }


@app.websocket("/telemetry/ws")
async def telemetry_ws(websocket: WebSocket, mode: str = "HOTLAP"):
    """
    WebSocket endpoint streaming authentic FastF1 Monza telemetry at ~10 Hz.
    Frames repeat continuously in a loop simulating real race pace.
    Supports ?mode=HOTLAP (qualifying pace) and ?mode=ENDURANCE (race stint pace).
    """
    await websocket.accept()
    mode_clean = mode.upper() if mode else "HOTLAP"
    is_endurance = (mode_clean == "ENDURANCE")
    logger.info("WebSocket client connected (Mode: %s): %s", mode_clean, websocket.client)

    if not TELEMETRY_DATA:
        # Fallback if dataset failed to load
        logger.error("No telemetry data loaded, closing connection")
        await websocket.close()
        return

    seq = 0
    total_frames = len(TELEMETRY_DATA)
    idx = 0
    lap_number = 1
    
    base_fastest_ms = 84230 if is_endurance else 80161
    base_fastest_time = 84.230 if is_endurance else 80.161
    fastest_lap_ms = base_fastest_ms
    fastest_lap_time = base_fastest_time
    fastest_lap_num = 1
    last_completed_lap = None

    try:
        while True:
            frame = TELEMETRY_DATA[idx]
            now_ts = _time.time()

            # Check for lap completion on first frame of a new lap
            lap_just_finished = None
            if idx == 0 and lap_number > 1:
                prev_lap_num = lap_number - 1
                lap_just_finished = get_simulated_lap(prev_lap_num, mode_clean)
                last_completed_lap = lap_just_finished
                if lap_just_finished["lap_time_ms"] < fastest_lap_ms:
                    fastest_lap_ms = lap_just_finished["lap_time_ms"]
                    fastest_lap_time = lap_just_finished["lap_time"]
                    fastest_lap_num = prev_lap_num

            # Mode physics adjustments using same FastF1 data:
            raw_throttle = frame["throttle"]
            raw_brake = frame["brake_pressure"]
            if raw_brake > 15:
                throttle_adj = 0.0
                brake_adj = raw_brake
            elif raw_throttle > 15:
                brake_adj = 0.0
                throttle_adj = raw_throttle
            else:
                throttle_adj = raw_throttle
                brake_adj = raw_brake

            long_g_adj = frame["long_g"]
            if brake_adj > 15 and long_g_adj > -0.5:
                long_g_adj = -round(min(5.2, brake_adj / 21.0), 2)
            elif throttle_adj > 50 and long_g_adj < 0.2:
                long_g_adj = round(throttle_adj / 65.0, 2)
            ax_adj = round(long_g_adj * 9.81, 2)

            if is_endurance:
                # Endurance Race Stint: 105 kg fuel load, slightly reduced peak VMAX, medium tyres
                speed_adj = round(frame["speed"] * 0.965, 1)
                rpm_adj = min(18200, int(round(frame["rpm"] * 0.97)))
                fuel_kg = max(15.0, round(105.0 - (lap_number - 1) * 1.85 - (frame["progress"] * 1.85), 2))
                tyre_compound = "MEDIUM (C3)"
                ers_mode = "RACE BALANCED (HARVEST/DEPLOY)"
                driver_desc = "Charles Leclerc (Race Stint - High Fuel)"
                tyre_fl = round(15.0 + lap_number * 1.4, 1)
                tyre_fr = round(13.0 + lap_number * 1.1, 1)
                tyre_rl = round(12.5 + lap_number * 1.3, 1)
                tyre_rr = round(11.8 + lap_number * 1.0, 1)
            else:
                # Hotlap Qualifying: 12 kg low fuel, max VMAX (345+ km/h), soft tyres
                speed_adj = frame["speed"]
                rpm_adj = frame["rpm"]
                fuel_kg = max(2.5, round(12.0 - (lap_number - 1) * 2.2 - (frame["progress"] * 2.2), 2))
                tyre_compound = "SOFT (C4)"
                ers_mode = "HOTLAP QUALIFYING DEPLOY (100%)"
                driver_desc = "Charles Leclerc (Q3 Qualifying Pole)"
                tyre_fl = round(13.0 + lap_number * 2.5, 1)
                tyre_fr = round(11.0 + lap_number * 2.0, 1)
                tyre_rl = round(11.0 + lap_number * 2.2, 1)
                tyre_rr = round(10.0 + lap_number * 1.8, 1)

            # Alerts generation: strictly ONE distinct active event at a time
            alerts = []
            if brake_adj > 80:
                alerts.append({
                    "id": "heavy_braking_zone",
                    "severity": "warning",
                    "alert_type": "HEAVY BRAKING ZONE",
                    "message": f"Threshold decel {long_g_adj:.1f}G into {frame['corner_name']}",
                })
            elif speed_adj > 330 and frame["drs"] > 0:
                alerts.append({
                    "id": "speed_trap_active",
                    "severity": "info",
                    "alert_type": "DRS HIGH SPEED TRAP",
                    "message": f"VMAX {speed_adj:.0f} km/h - DRS Active on Rettifilo",
                })

            packet = {
                "type": "telemetry_update",
                "timestamp": now_ts,
                "telemetry_mode": mode_clean,
                "fuel_kg": fuel_kg,
                "tyre_compound": tyre_compound,
                "ers_mode": ers_mode,
                "lap": {
                    "lap_number": lap_number,
                    "fastest_lap_ms": fastest_lap_ms,
                    "fastest_lap_time": fastest_lap_time,
                    "fastest_lap_number": fastest_lap_num,
                    "driver": driver_desc,
                    "car": "#16 Ferrari F1-75",
                    "telemetry_mode": mode_clean,
                },
                "lap_completed": lap_just_finished,
                "raw": {
                    "gps": {
                        "latitude": frame["latitude"],
                        "longitude": frame["longitude"],
                        "altitude": 183.0,
                        "speed": speed_adj,
                        "satellite_count": 14,
                        "fix_status": "3D_FIX",
                        "track_x": frame["track_x"],
                        "track_y": frame["track_y"],
                    },
                    "vehicle_can": {
                        "rpm": rpm_adj,
                        "gear": frame["gear"],
                        "throttle": throttle_adj,
                        "brake_pressure": brake_adj,
                        "battery_voltage": 14.2,
                        "battery_current": 2.5 if not is_endurance else round(2.0 + (throttle_adj / 100) * 1.5, 2),
                        "drs": frame["drs"],
                    },
                    "imu": {
                        "ax": frame["ax"],
                        "ay": frame["ay"],
                        "az": 9.81,
                        "gx": 0.0,
                        "gy": 0.0,
                        "gz": round(frame["lat_g"] * 0.12, 3),
                    },
                    "temperature": {
                        "coolant_temperature": frame["coolant_temp"],
                        "engine_temperature": frame["engine_temp"],
                        "brake_temp_fl": frame["brake_temp_fl"],
                        "brake_temp_fr": frame["brake_temp_fr"],
                        "brake_temp_rl": frame["brake_temp_rl"],
                        "brake_temp_rr": frame["brake_temp_rr"],
                    },
                    "wheel_speeds": {
                        "front_left": speed_adj,
                        "front_right": speed_adj,
                        "rear_left": speed_adj,
                        "rear_right": speed_adj,
                    },
                    "tyre_wear": {
                        "fl": tyre_fl,
                        "fr": tyre_fr,
                        "rl": tyre_rl,
                        "rr": tyre_rr,
                        "age_lap": lap_number,
                    },
                    "metadata": {
                        "timestamp": now_ts,
                        "sequence_number": seq,
                        "sampling_rate": 10,
                        "status_error_information": "OK",
                        "transmission_information": "FastF1 Telemetry",
                    },
                    "track_x": frame["track_x"],
                    "track_y": frame["track_y"],
                    "speed": speed_adj,
                    "rpm": rpm_adj,
                    "gear": frame["gear"],
                    "throttle": throttle_adj,
                    "brake_pressure": brake_adj,
                    "corner_name": frame["corner_name"],
                    "sector": frame["sector"],
                    "distance": frame["distance_m"],
                    "progress": frame["progress"],
                    "fuel_kg": fuel_kg,
                    "tyre_compound": tyre_compound,
                    "ers_mode": ers_mode,
                },
                "processed": {
                    "longitudinal_acceleration": ax_adj,
                    "lateral_acceleration": frame["ay"],
                    "vertical_acceleration": 9.81,
                    "long_g": long_g_adj,
                    "lat_g": frame["lat_g"],
                    "resultant_g": frame["resultant_g"],
                    "cornering_intensity": frame["cornering_intensity"],
                    "braking_intensity": brake_adj,
                    "corner_name": frame["corner_name"],
                },
                "alerts": alerts,
            }

            await websocket.send_text(json.dumps(packet))
            seq += 1
            idx += 1

            if idx >= total_frames:
                idx = 0
                lap_number += 1

            # Sleep duration: Hotlap ~128ms (80.16s / 623), Endurance ~135ms (84.23s / 623)
            sleep_duration = 0.135 if is_endurance else 0.128
            await asyncio.sleep(sleep_duration)

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected cleanly")
    except Exception as exc:
        logger.error("WebSocket error: %s", exc)
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
