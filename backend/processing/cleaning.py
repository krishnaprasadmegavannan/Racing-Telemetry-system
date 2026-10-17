import math


def clean_numeric_value(
    value: float | None,
    default: float | None = None
) -> float | None:
    """
    Clean a single numeric telemetry value.

    Valid finite values are returned unchanged.

    NaN and infinite values are treated as invalid
    and replaced with the supplied default.

    Args:
        value: Numeric telemetry value.
        default: Value to use when the input is invalid.

    Returns:
        Cleaned numeric value or default.
    """

    if value is None:
        return default

    if not math.isfinite(value):
        return default

    return value


def clean_telemetry_packet(packet):
    """
    Clean numeric values from a validated telemetry packet.

    This function does NOT modify valid physical values.
    It only protects the processing pipeline from invalid
    numeric values such as NaN and infinity.

    Args:
        packet: Validated TelemetryPacket.

    Returns:
        Dictionary containing cleaned telemetry values.
    """

    numeric_values = {
        # -----------------------------
        # GPS
        # -----------------------------
        "latitude": packet.gps.latitude,
        "longitude": packet.gps.longitude,
        "speed": packet.gps.speed,
        "altitude": packet.gps.altitude,

        # -----------------------------
        # IMU
        # -----------------------------
        "ax": packet.imu.ax,
        "ay": packet.imu.ay,
        "az": packet.imu.az,
        "gx": packet.imu.gx,
        "gy": packet.imu.gy,
        "gz": packet.imu.gz,

        # -----------------------------
        # Temperature
        # -----------------------------
        "coolant_temperature":
            packet.temperature.coolant_temperature,

        "engine_temperature":
            packet.temperature.engine_temperature,

        # -----------------------------
        # Wheel speeds
        # -----------------------------
        "front_left":
            packet.wheel_speeds.front_left,

        "front_right":
            packet.wheel_speeds.front_right,

        "rear_left":
            packet.wheel_speeds.rear_left,

        "rear_right":
            packet.wheel_speeds.rear_right,

        # -----------------------------
        # Vehicle / CAN
        # -----------------------------
        "rpm":
            packet.vehicle_can.rpm,

        "throttle":
            packet.vehicle_can.throttle,

        "brake_pressure":
            packet.vehicle_can.brake_pressure,

        "battery_voltage":
            packet.vehicle_can.battery_voltage,

        "battery_current":
            packet.vehicle_can.battery_current,
    }

    cleaned = {}

    for name, value in numeric_values.items():
        cleaned[name] = clean_numeric_value(value)

    return cleaned