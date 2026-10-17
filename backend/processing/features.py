import math

from models.telemetry import IMUData, TelemetryPacket
from processing.output import ProcessedTelemetry
from processing.vehicle_dynamics import (
    acceleration_intensity,
    braking_intensity,
    cornering_intensity,
    resultant_acceleration,
    yaw_rate,
)
from analytics.wheel_analysis import analyze_wheels


def calculate_longitudinal_acceleration(imu: IMUData) -> float:
    return imu.ax


def calculate_lateral_acceleration(imu: IMUData) -> float:
    return imu.ay


def calculate_vertical_acceleration(imu: IMUData) -> float:
    return imu.az


def calculate_resultant_acceleration(imu: IMUData) -> float:
    return math.sqrt(imu.ax ** 2 + imu.ay ** 2 + imu.az ** 2)


def calculate_yaw_rate(imu: IMUData) -> float:
    return imu.gz


def calculate_cornering_intensity(imu: IMUData) -> float:
    return cornering_intensity(imu.ay)


def calculate_braking_intensity(imu: IMUData, brake_pressure: float) -> float:
    return braking_intensity(imu.ax, brake_pressure)


def calculate_acceleration_intensity(imu: IMUData, throttle: float) -> float:
    return acceleration_intensity(imu.ax, throttle)


def calculate_wheel_speed_difference(wheels) -> float:
    values = [wheels.front_left, wheels.front_right, wheels.rear_left, wheels.rear_right]
    return max(values) - min(values)


def analyze_wheel_speeds(wheels) -> dict:
    values = {
        "front_left": wheels.front_left,
        "front_right": wheels.front_right,
        "rear_left": wheels.rear_left,
        "rear_right": wheels.rear_right,
    }
    fastest = max(values, key=values.get)
    slowest = min(values, key=values.get)
    return {
        "difference": values[fastest] - values[slowest],
        "fastest_wheel": fastest,
        "slowest_wheel": slowest,
    }


def calculate_speed_acceleration(previous_speed: float, current_speed: float,
                                 previous_timestamp: float, current_timestamp: float) -> float:
    delta_time = current_timestamp - previous_timestamp
    if delta_time <= 0:
        raise ValueError("Current timestamp must be greater than previous timestamp.")
    return ((current_speed - previous_speed) / 3.6) / delta_time


def process_telemetry(packet: TelemetryPacket,
                      previous_speed: float | None = None,
                      previous_timestamp: float | None = None) -> ProcessedTelemetry:
    wheel = analyze_wheels(
        packet.wheel_speeds,
        packet.gps.speed,
        packet.vehicle_can.brake_pressure,
    )

    speed_acceleration = None
    if previous_speed is not None and previous_timestamp is not None:
        speed_acceleration = calculate_speed_acceleration(
            previous_speed,
            packet.gps.speed,
            previous_timestamp,
            packet.metadata.timestamp,
        )

    return ProcessedTelemetry(
        longitudinal_acceleration=calculate_longitudinal_acceleration(packet.imu),
        lateral_acceleration=calculate_lateral_acceleration(packet.imu),
        vertical_acceleration=calculate_vertical_acceleration(packet.imu),
        resultant_acceleration=calculate_resultant_acceleration(packet.imu),
        yaw_rate=calculate_yaw_rate(packet.imu),
        cornering_intensity=calculate_cornering_intensity(packet.imu),
        braking_intensity=calculate_braking_intensity(packet.imu, packet.vehicle_can.brake_pressure),
        acceleration_intensity=calculate_acceleration_intensity(packet.imu, packet.vehicle_can.throttle),
        wheel_speed_difference=wheel["difference"],
        fastest_wheel=wheel["fastest_wheel"],
        slowest_wheel=wheel["slowest_wheel"],
        possible_wheel_slip=wheel["possible_wheel_slip"],
        possible_wheel_lock=wheel["possible_wheel_lock"],
        wheel_speed_mismatch=wheel["wheel_speed_mismatch"],
        speed_acceleration=speed_acceleration,
    )
