"""
scripts/extract_fastf1_monza.py
Extracts real Charles Leclerc 2022 Monza Pole Lap (1:20.161) telemetry using FastF1,
computes synchronized vehicle dynamics, rotated track coordinates, and outputs
clean JSON datasets for the backend stream and the frontend map.
"""
import os
import json
import math
import numpy as np
import fastf1

def extract_and_process():
    cache_dir = os.path.join(os.path.dirname(__file__), '..', 'scratch', 'f1_cache')
    os.makedirs(cache_dir, exist_ok=True)
    fastf1.Cache.enable_cache(cache_dir)

    print("Loading FastF1 2022 Monza Qualifying session...")
    session = fastf1.get_session(2022, 'Monza', 'Q')
    session.load(telemetry=True, weather=False, messages=False)

    fastest_lap = session.laps.pick_fastest()
    driver = fastest_lap['Driver']
    lap_time = fastest_lap['LapTime'].total_seconds()
    print(f"Loaded fastest lap: Driver {driver}, Lap Time: {lap_time:.3f}s")

    tel = fastest_lap.get_telemetry()
    n_points = len(tel)
    print(f"Total telemetry data points: {n_points}")

    # Raw FastF1 coordinates
    raw_x = tel['X'].values
    raw_y = tel['Y'].values
    speeds = tel['Speed'].values          # km/h
    rpms = tel['RPM'].values              # RPM
    gears = tel['nGear'].values           # 2 to 8
    throttles = tel['Throttle'].values    # 0 to 100
    brakes = tel['Brake'].values          # boolean True/False
    drs_status = tel['DRS'].values        # 0, 8, 10, 12, 14
    distances = tel['Distance'].values    # meters
    times = tel['Time'].dt.total_seconds().values  # seconds

    # Rotation: 95 degrees rotates Monza so the main straight is at the bottom,
    # going right-to-left into T1, matching the standard FIA Monza circuit layout.
    rad = np.radians(95.0)
    xr = raw_x * np.cos(rad) - raw_y * np.sin(rad)
    yr = raw_x * np.sin(rad) + raw_y * np.cos(rad)

    # SVG Canvas space: 1000 x 520 with 45px padding
    W, H, PAD = 1000.0, 520.0, 45.0
    min_x, max_x = float(xr.min()), float(xr.max())
    min_y, max_y = float(yr.min()), float(yr.max())
    span_x = max_x - min_x
    span_y = max_y - min_y
    scale = min((W - 2 * PAD) / span_x, (H - 2 * PAD) / span_y)

    offset_x = PAD + ((W - 2 * PAD) - span_x * scale) / 2.0
    offset_y = PAD + ((H - 2 * PAD) - span_y * scale) / 2.0

    svg_coords = []
    for i in range(n_points):
        px = round(offset_x + (xr[i] - min_x) * scale, 2)
        py = round(offset_y + (max_y - yr[i]) * scale, 2)  # Invert Y for screen
        svg_coords.append((px, py))

    # Identify corners and sector regions by distance along the 5,793m circuit
    def get_corner_info(dist, spd):
        if dist < 650:
            return "Rettifilo Tribune (Main Straight)", 1
        elif dist < 1250:
            return "Variante del Rettifilo (T1/T2)", 1
        elif dist < 1850:
            return "Curva Grande (Curva Biassono)", 1
        elif dist < 2400:
            return "Variante della Roggia (T4/T5)", 2
        elif dist < 2750:
            return "Curva di Lesmo 1 (T6)", 2
        elif dist < 3200:
            return "Curva di Lesmo 2 (T7)", 2
        elif dist < 3650:
            return "Curva del Serraglio", 2
        elif dist < 4250:
            return "Variante Ascari (T8/T9/T10)", 3
        elif dist < 4950:
            return "Rettifilo del Rettilineo (Back Straight)", 3
        elif dist < 5600:
            return "Curva Parabolica (Curva Alboreto)", 3
        else:
            return "Pit Straight", 3

    # Physics derivation: Longitudinal and Lateral Accelerations
    processed_frames = []
    base_brake_temp = 540.0
    brake_heat = 0.0

    for i in range(n_points):
        t_sec = float(times[i])
        dist_m = float(distances[i])
        spd_kmh = float(speeds[i])
        rpm_val = float(rpms[i])
        gear_val = int(gears[i])
        thr_pct = float(throttles[i])
        is_braking = bool(brakes[i])
        drs_val = int(drs_status[i])
        sx, sy = svg_coords[i]

        # Longitudinal G: from dt and dv
        if 0 < i < n_points - 1:
            dt = times[i+1] - times[i-1]
            dv_ms = (speeds[i+1] - speeds[i-1]) / 3.6
            ax = dv_ms / max(0.01, dt)
        else:
            ax = 0.0
        # Realistic clamping: F1 decel up to -4.8 G, accel up to 1.6 G
        ax = max(-48.0, min(16.0, ax))
        long_g = round(ax / 9.81, 2)

        # Lateral G: derived from curvature of the trajectory
        if 1 < i < n_points - 2:
            dx1 = xr[i] - xr[i-2]
            dy1 = yr[i] - yr[i-2]
            dx2 = xr[i+2] - xr[i]
            dy2 = yr[i+2] - yr[i]
            heading1 = math.atan2(dy1, dx1)
            heading2 = math.atan2(dy2, dx2)
            dheading = (heading2 - heading1 + math.pi) % (2 * math.pi) - math.pi
            dt_curv = times[i+2] - times[i-2]
            yaw_rate = dheading / max(0.01, dt_curv)
            v_ms = spd_kmh / 3.6
            ay = v_ms * yaw_rate
        else:
            ay = 0.0
            yaw_rate = 0.0
        ay = max(-45.0, min(45.0, ay))
        lat_g = round(ay / 9.81, 2)

        resultant_g = round(math.sqrt(long_g**2 + lat_g**2 + 1.0), 2)
        cornering_intensity = min(100, int(round((abs(lat_g) / 3.5) * 100)))

        # Realistic Brake Pressure (0 - 100%)
        if is_braking:
            brake_pressure = min(100.0, max(25.0, abs(long_g) * 22.0))
            brake_heat = min(360.0, brake_heat + (brake_pressure / 100.0) * 18.0)
        else:
            brake_pressure = 0.0
            brake_heat = max(0.0, brake_heat * 0.96)  # air cooling on straights

        # Brake disc temperatures (°C)
        b_temp_fl = round(base_brake_temp + brake_heat + (15.0 if lat_g > 0 else 0.0), 1)
        b_temp_fr = round(base_brake_temp + brake_heat + (15.0 if lat_g < 0 else 0.0), 1)
        b_temp_rl = round(base_brake_temp * 0.92 + brake_heat * 0.85 + (10.0 if lat_g > 0 else 0.0), 1)
        b_temp_rr = round(base_brake_temp * 0.92 + brake_heat * 0.85 + (10.0 if lat_g < 0 else 0.0), 1)

        # Wheel speeds (km/h) with subtle rear wheel acceleration slip
        rear_slip = 1.0 + (0.015 * (thr_pct / 100.0) if thr_pct > 70 and spd_kmh < 220 else 0.0)
        wheel_fl = round(spd_kmh, 2)
        wheel_fr = round(spd_kmh, 2)
        wheel_rl = round(spd_kmh * rear_slip, 2)
        wheel_rr = round(spd_kmh * rear_slip, 2)

        # GPS coordinates mapped to Monza latitude & longitude
        # Center of Monza: lat 45.6180, lon 9.2810
        # 1 deg lat ≈ 111,000m, 1 deg lon ≈ 77,800m
        lat_coord = round(45.6180 + (raw_y[i] / 10.0) / 111000.0, 6)
        lon_coord = round(9.2810 + (raw_x[i] / 10.0) / 77800.0, 6)

        corner_name, sector_num = get_corner_info(dist_m, spd_kmh)

        frame = {
            "index": i,
            "time_sec": round(t_sec, 3),
            "distance_m": round(dist_m, 1),
            "speed": round(spd_kmh, 1),
            "rpm": int(round(rpm_val)),
            "gear": gear_val,
            "throttle": round(thr_pct, 1),
            "brake_pressure": round(brake_pressure, 1),
            "is_braking": is_braking,
            "drs": drs_val,
            "track_x": sx,
            "track_y": sy,
            "latitude": lat_coord,
            "longitude": lon_coord,
            "ax": round(ax, 2),
            "ay": round(ay, 2),
            "az": 9.81,
            "long_g": long_g,
            "lat_g": lat_g,
            "resultant_g": resultant_g,
            "cornering_intensity": cornering_intensity,
            "brake_temp_fl": b_temp_fl,
            "brake_temp_fr": b_temp_fr,
            "brake_temp_rl": b_temp_rl,
            "brake_temp_rr": b_temp_rr,
            "coolant_temp": round(92.0 + 3.0 * math.sin(i * 0.05), 1),
            "engine_temp": round(108.0 + 4.0 * math.sin(i * 0.05), 1),
            "wheel_fl": wheel_fl,
            "wheel_fr": wheel_fr,
            "wheel_rl": wheel_rl,
            "wheel_rr": wheel_rr,
            "wheel_slip_delta": round(max(0.0, wheel_rl - wheel_fl), 1),
            "corner_name": corner_name,
            "sector": sector_num,
            "progress": round(i / (n_points - 1), 4),
        }
        processed_frames.append(frame)

    # Build SVG track path
    path_d = f"M {svg_coords[0][0]} {svg_coords[0][1]}"
    for x, y in svg_coords[1:]:
        path_d += f" L {x} {y}"
    path_d += " Z"

    dataset = {
        "metadata": {
            "circuit": "Autodromo Nazionale Monza",
            "country": "Italy",
            "session": "2022 Formula 1 Italian Grand Prix - Qualifying",
            "driver": driver,
            "car": "#16 Ferrari F1-75",
            "lap_time": "1:20.161",
            "lap_time_ms": 80161,
            "total_points": n_points,
            "circuit_length_m": 5793,
            "svg_width": W,
            "svg_height": H,
            "svg_path": path_d,
            "landmarks": [
                {"name": "Start / Finish", "x": 741.6, "y": 473.2, "sector": 1},
                {"name": "Variante del Rettifilo (T1)", "x": 388.8, "y": 457.6, "sector": 1},
                {"name": "Curva Grande", "x": 195.2, "y": 380.0, "sector": 1},
                {"name": "Variante della Roggia", "x": 78.5, "y": 175.4, "sector": 2},
                {"name": "Curve di Lesmo", "x": 167.0, "y": 46.1, "sector": 2},
                {"name": "Curva del Serraglio", "x": 360.5, "y": 250.2, "sector": 2},
                {"name": "Variante Ascari", "x": 540.7, "y": 368.2, "sector": 3},
                {"name": "Back Straight", "x": 760.0, "y": 385.0, "sector": 3},
                {"name": "Curva Parabolica (Alboreto)", "x": 928.9, "y": 413.3, "sector": 3},
            ]
        },
        "telemetry": processed_frames
    }

    # Output paths
    backend_data_dir = os.path.join(os.path.dirname(__file__), '..', 'backend', 'data')
    os.makedirs(backend_data_dir, exist_ok=True)
    backend_out = os.path.join(backend_data_dir, 'monza_fastf1_telemetry.json')

    api_out = os.path.join(os.path.dirname(__file__), '..', 'api', 'monza_fastf1_telemetry.json')
    frontend_out = os.path.join(os.path.dirname(__file__), '..', 'dashboard-js', 'src', 'assets', 'monza_fastf1_track.json')

    for p in [backend_out, api_out, frontend_out]:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w') as f:
            json.dump(dataset, f)
        print(f"Saved dataset to: {p} ({os.path.getsize(p) / 1024:.1f} KB)")

    print("FastF1 Monza dataset extraction completed successfully!")

if __name__ == '__main__':
    extract_and_process()
