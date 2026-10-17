from dataclasses import dataclass


@dataclass
class Alert:
    alert_type: str
    severity: str
    message: str
    value: float | None = None


def generate_alerts(packet, processed) -> list[Alert]:
    alerts = []

    # --------------------------------------------------
    # 1. GPS HEALTH CHECK
    # --------------------------------------------------
    fix_status = (packet.gps.fix_status or "").strip().upper()
    satellite_count = packet.gps.satellite_count

    # Accept the GPS status formats used by the simulator.
    valid_fix_statuses = {
        "FIX",
        "3D",
        "VALID",
        "3D_FIX",
    }

    if (
        fix_status not in valid_fix_statuses
        or satellite_count < 5
    ):
        alerts.append(
            Alert(
                "GPS_LOST",
                "CRITICAL",
                "GPS fix lost or insufficient satellites.",
            )
        )

    # --------------------------------------------------
    # 2. IMU HEALTH CHECK
    # --------------------------------------------------
    status = (
        packet.metadata.status_error_information or ""
    ).upper()

    if "IMU" in status and (
        "FAIL" in status or "ERROR" in status
    ):
        alerts.append(
            Alert(
                "IMU_FAILURE",
                "CRITICAL",
                "IMU failure reported.",
            )
        )

    # --------------------------------------------------
    # 3. CAN BUS HEALTH CHECK
    # --------------------------------------------------
    if "CAN" in status and (
        "FAIL" in status or "ERROR" in status
    ):
        alerts.append(
            Alert(
                "CAN_FAILURE",
                "CRITICAL",
                "CAN failure reported.",
            )
        )

    # --------------------------------------------------
    # 4. COOLANT TEMPERATURE
    # --------------------------------------------------
    coolant_temp = packet.temperature.coolant_temperature

    if coolant_temp >= 105:
        alerts.append(
            Alert(
                "HIGH_TEMPERATURE",
                "CRITICAL",
                "Coolant temperature is high.",
                coolant_temp,
            )
        )

    # --------------------------------------------------
    # 5. ENGINE TEMPERATURE
    # --------------------------------------------------
    engine_temp = packet.temperature.engine_temperature

    if engine_temp >= 120:
        alerts.append(
            Alert(
                "HIGH_TEMPERATURE",
                "CRITICAL",
                "Engine temperature is high.",
                engine_temp,
            )
        )

    # --------------------------------------------------
    # 6. BATTERY VOLTAGE
    # --------------------------------------------------
    battery_voltage = packet.vehicle_can.battery_voltage

    if battery_voltage < 11.5:
        alerts.append(
            Alert(
                "LOW_BATTERY",
                "WARNING",
                "Battery voltage is low.",
                battery_voltage,
            )
        )

    # --------------------------------------------------
    # 7. POSSIBLE WHEEL SLIP
    # --------------------------------------------------
    if processed.possible_wheel_slip:
        alerts.append(
            Alert(
                "WHEEL_SLIP",
                "WARNING",
                "Possible wheel slip detected.",
                processed.wheel_speed_difference,
            )
        )

    # --------------------------------------------------
    # 8. WHEEL SPEED MISMATCH
    # --------------------------------------------------
    if processed.wheel_speed_mismatch:
        alerts.append(
            Alert(
                "WHEEL_SPEED_MISMATCH",
                "WARNING",
                "Wheel-speed mismatch detected.",
                processed.wheel_speed_difference,
            )
        )

    # --------------------------------------------------
    # 9. EXCESSIVE LATERAL ACCELERATION
    # --------------------------------------------------
    lateral_acceleration = processed.lateral_acceleration

    if abs(lateral_acceleration) >= 12.0:
        alerts.append(
            Alert(
                "EXCESSIVE_LATERAL_G",
                "CRITICAL",
                "Excessive lateral acceleration.",
                lateral_acceleration,
            )
        )

    return alerts