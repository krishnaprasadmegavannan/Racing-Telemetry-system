import math
from models.telemetry import TelemetryPacket


def validate_engineering_values(packet: TelemetryPacket) -> list[str]:
    errors = []

    numeric_groups = {
        "GPS": [packet.gps.latitude, packet.gps.longitude, packet.gps.speed, packet.gps.altitude],
        "IMU": [packet.imu.ax, packet.imu.ay, packet.imu.az, packet.imu.gx, packet.imu.gy, packet.imu.gz],
        "temperature": [packet.temperature.coolant_temperature, packet.temperature.engine_temperature],
        "wheels": [packet.wheel_speeds.front_left, packet.wheel_speeds.front_right, packet.wheel_speeds.rear_left, packet.wheel_speeds.rear_right],
        "CAN": [packet.vehicle_can.rpm, packet.vehicle_can.throttle, packet.vehicle_can.brake_pressure, packet.vehicle_can.battery_voltage, packet.vehicle_can.battery_current],
        "metadata": [packet.metadata.timestamp, packet.metadata.sampling_rate],
    }
    for group, values in numeric_groups.items():
        if any(not math.isfinite(v) for v in values):
            errors.append(f"{group} contains NaN or infinity.")

    if not -90 <= packet.gps.latitude <= 90:
        errors.append("GPS latitude is outside valid range.")
    if not -180 <= packet.gps.longitude <= 180:
        errors.append("GPS longitude is outside valid range.")
    if packet.gps.speed < 0:
        errors.append("GPS speed cannot be negative.")
    if packet.gps.satellite_count < 0:
        errors.append("Satellite count cannot be negative.")

    for name, value in vars(packet.imu).items():
        if not -1000 <= value <= 1000:
            errors.append(f"IMU value {name} is outside expected range.")

    if not -50 <= packet.temperature.coolant_temperature <= 200:
        errors.append("Coolant temperature is outside expected range.")
    if not -50 <= packet.temperature.engine_temperature <= 250:
        errors.append("Engine temperature is outside expected range.")

    for name, value in vars(packet.wheel_speeds).items():
        if value < 0:
            errors.append(f"Wheel speed {name} cannot be negative.")

    if packet.vehicle_can.rpm < 0:
        errors.append("RPM cannot be negative.")
    if not 0 <= packet.vehicle_can.throttle <= 100:
        errors.append("Throttle must be between 0 and 100%.")
    if not 0 <= packet.vehicle_can.brake_pressure <= 100:
        errors.append("Brake pressure must be between 0 and 100%.")
    if packet.vehicle_can.battery_voltage < 0:
        errors.append("Battery voltage cannot be negative.")
    if packet.vehicle_can.battery_current < 0:
        errors.append("Battery current cannot be negative.")

    if packet.metadata.timestamp < 0:
        errors.append("Timestamp cannot be negative.")
    if packet.metadata.sequence_number < 0:
        errors.append("Sequence number cannot be negative.")
    if packet.metadata.sampling_rate <= 0:
        errors.append("Sampling rate must be greater than zero.")

    return errors
