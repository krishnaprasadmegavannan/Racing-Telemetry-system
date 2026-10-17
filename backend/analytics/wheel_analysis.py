def wheel_speed_values(wheels):
    return {
        "front_left": wheels.front_left,
        "front_right": wheels.front_right,
        "rear_left": wheels.rear_left,
        "rear_right": wheels.rear_right,
    }


def analyze_wheels(wheels, vehicle_speed: float, brake_pressure: float,
                   mismatch_threshold: float = 8.0,
                   slip_threshold: float = 12.0,
                   lock_threshold: float = 15.0) -> dict:
    values = wheel_speed_values(wheels)
    fastest = max(values, key=values.get)
    slowest = min(values, key=values.get)
    difference = values[fastest] - values[slowest]

    mismatch = difference > mismatch_threshold
    slip = False
    lock = False

    if vehicle_speed >= 5.0:
        slip = max(abs(v - vehicle_speed) for v in values.values()) > slip_threshold

    if brake_pressure > 5.0 and vehicle_speed >= 10.0:
        lock = min(values.values()) < vehicle_speed - lock_threshold

    return {
        "difference": difference,
        "fastest_wheel": fastest,
        "slowest_wheel": slowest,
        "possible_wheel_slip": slip,
        "possible_wheel_lock": lock,
        "wheel_speed_mismatch": mismatch,
    }
