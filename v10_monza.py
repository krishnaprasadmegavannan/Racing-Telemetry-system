# v10_monza.py
import json
import time

def lerp(a, b, t):
    return a + (b - a) * max(0, min(1, t))

# [lap_progress, speed_kmh, gear, throttle_pct, brake_pct, lat_g]
monza_profile = [
    [0.00, 320, 7, 100, 0,   0.0],
    [0.10, 350, 7, 100, 0,   0.0],   # End of pit straight (Speed Trap)
    [0.12, 80,  2, 0,   100, 0.5],   # T1 Apex
    [0.14, 110, 3, 50,  0,  -0.8],   # T2 Apex
    [0.22, 310, 7, 100, 0,   2.5],   # Curva Grande
    [0.27, 320, 7, 100, 0,   0.0],   # Approaching Roggia
    [0.29, 110, 3, 0,   90, -1.5],   # Roggia 1
    [0.31, 120, 3, 60,  0,   1.5],   # Roggia 2
    [0.40, 280, 6, 100, 0,   0.0],   # Approaching Lesmo 1
    [0.42, 160, 4, 20,  40,  2.0],   # Lesmo 1
    [0.46, 260, 6, 100, 0,   0.0],   # Straight
    [0.48, 170, 4, 30,  30,  2.2],   # Lesmo 2
    [0.64, 330, 7, 100, 0,   0.0],   # Serraglio / Approaching Ascari
    [0.66, 180, 4, 0,   85, -2.0],   # Ascari Entry
    [0.67, 190, 4, 40,  0,   2.5],   # Ascari Mid
    [0.69, 210, 5, 100, 0,  -1.5],   # Ascari Exit
    [0.85, 345, 7, 100, 0,   0.0],   # Back Straight
    [0.87, 180, 4, 0,   70,  2.5],   # Parabolica Entry
    [0.91, 200, 5, 50,  0,   2.8],   # Parabolica Mid
    [0.95, 270, 6, 100, 0,   1.0],   # Parabolica Exit
    [1.00, 320, 7, 100, 0,   0.0]
]

def get_telemetry(progress):
    for i in range(len(monza_profile) - 1):
        p1, p2 = monza_profile[i], monza_profile[i+1]
        if p1[0] <= progress <= p2[0]:
            t = (progress - p1[0]) / (p2[0] - p1[0])
            return (lerp(p1[j], p2[j], t) for j in range(1, 6))
    return 320, 7, 100, 0, 0.0

# Base brake disk temperatures (°C)
base_brake_front = 720.0
base_brake_rear = 680.0

tick = 0
while True:
    total_seconds = tick * 0.02
    lap_number = int(total_seconds // 81.0) + 1
    t = total_seconds % 81.0  # 81-second lap at 50Hz
    progress = t / 81.0
    
    speed, gear, throttle, brake, lat_g = get_telemetry(progress)
    gear_int = int(round(gear))
    if gear_int < 1:
        gear_int = 1
    
    # Simulate V10 Engine Acoustics & RPM
    rpm_base = 7000 if gear_int <= 1 else 6000 + (speed / (gear_int * 50 + 10)) * 13000
    rpm = min(19500, max(6000, rpm_base))
    
    # Calculate G-Forces (Throttle = +, Brake = -)
    long_g = (throttle / 100.0) * 1.5 - (brake / 100.0) * 4.8
    
    # Brake temperatures in °C (heats up dynamically with brake % and speed, cools on straights)
    brake_heat = (brake / 100.0) * (speed / 350.0) * 220.0
    fl_extra = 12.0 if lat_g > 0 else 0.0
    fr_extra = 12.0 if lat_g < 0 else 0.0
    rl_extra = 8.0 if lat_g > 0 else 0.0
    rr_extra = 8.0 if lat_g < 0 else 0.0

    brake_temp_fl = round(base_brake_front + brake_heat + fl_extra, 1)
    brake_temp_fr = round(base_brake_front + brake_heat + fr_extra, 1)
    brake_temp_rl = round(base_brake_rear + brake_heat * 0.85 + rl_extra, 1)
    brake_temp_rr = round(base_brake_rear + brake_heat * 0.85 + rr_extra, 1)
    
    # Tyre wear in % (starts at realistic baseline and gradually increases over laps)
    lap_wear_delta = (lap_number - 1) * 2.5 + (progress * 2.5)
    wear_fl = round(11.0 + lap_wear_delta + 1.5, 2)
    wear_fr = round(10.0 + lap_wear_delta + 1.0, 2)
    wear_rl = round(9.5 + lap_wear_delta + 0.8, 2)
    wear_rr = round(9.0 + lap_wear_delta + 0.5, 2)

    # GPS coordinates near Monza track
    lat = 45.6180 + 0.007 * (1.0 - progress)
    lon = 9.2810 + 0.009 * progress

    packet = {
        "metadata": {
            "timestamp": time.time(),
            "sequence_number": tick,
            "sampling_rate": 50,
            "status_error_information": "OK",
            "transmission_information": "F1_TELEMETRY_LINK"
        },
        "gps": {
            "latitude": round(lat, 6),
            "longitude": round(lon, 6),
            "speed": round(speed, 2),
            "altitude": 183.0,
            "satellite_count": 14,
            "fix_status": "3D_FIX"
        },
        "imu": {
            "ax": round(long_g, 3),
            "ay": round(lat_g, 3),
            "az": 9.81,
            "gx": round(lat_g * 0.2, 3),
            "gy": round(long_g * 0.3, 3),
            "gz": round(lat_g * 1.5, 3)
        },
        "temperature": {
            "coolant_temperature": round(92.5 + (throttle / 100) * 5.0, 1),
            "engine_temperature": round(105.0 + (rpm / 19000) * 15.0, 1),
            "brake_temp_fl": brake_temp_fl,
            "brake_temp_fr": brake_temp_fr,
            "brake_temp_rl": brake_temp_rl,
            "brake_temp_rr": brake_temp_rr
        },
        "wheel_speeds": {
            "front_left": round(speed, 2),
            "front_right": round(speed, 2),
            "rear_left": round(speed + (throttle / 100) * 4.0, 2),
            "rear_right": round(speed + (throttle / 100) * 4.0, 2)
        },
        "vehicle": {
            "rpm": round(rpm, 0),
            "throttle": round(throttle, 1),
            "brake_pressure": round(brake, 1),
            "battery_voltage": 14.2,
            "battery_current": round(2.5 + (throttle / 100) * 1.8, 2),
            "gear": gear_int
        },
        "tyre_wear": {
            "fl": wear_fl,
            "fr": wear_fr,
            "rl": wear_rl,
            "rr": wear_rr,
            "age_lap": lap_number
        }
    }
    
    print(json.dumps(packet), flush=True)
    time.sleep(0.02)
    tick += 1