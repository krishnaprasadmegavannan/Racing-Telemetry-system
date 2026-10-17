import math


def resultant_acceleration(ax: float, ay: float, az: float) -> float:
    return math.sqrt(ax * ax + ay * ay + az * az)


def cornering_intensity(lateral_acceleration: float) -> float:
    return abs(lateral_acceleration)


def braking_intensity(longitudinal_acceleration: float, brake_pressure: float) -> float:
    return max(0.0, -longitudinal_acceleration) * max(0.0, brake_pressure) / 100.0


def acceleration_intensity(longitudinal_acceleration: float, throttle: float) -> float:
    return max(0.0, longitudinal_acceleration) * max(0.0, throttle) / 100.0


def yaw_rate(gz: float) -> float:
    return gz
