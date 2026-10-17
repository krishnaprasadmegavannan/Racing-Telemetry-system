"""Lightweight integration checks. Run only if time permits: python tests/test_backend.py"""
from models.telemetry import TelemetryPacket
from processing.features import process_telemetry
from alerts.alert_engine import generate_alerts


def sample():
    return TelemetryPacket.model_validate({
        "gps": {"latitude": 13.0827, "longitude": 80.2707, "speed": 120.0, "altitude": 18.5, "satellite_count": 10, "fix_status": "FIX"},
        "imu": {"ax": 2.1, "ay": 8.7, "az": 9.6, "gx": 0.2, "gy": 1.4, "gz": 18.2},
        "temperature": {"coolant_temperature": 91.2, "engine_temperature": 87.4},
        "wheel_speeds": {"front_left": 119.2, "front_right": 120.1, "rear_left": 117.7, "rear_right": 118.4},
        "vehicle_can": {"rpm": 7820, "throttle": 84.5, "brake_pressure": 0.0, "battery_voltage": 13.8, "battery_current": 4.2},
        "metadata": {"timestamp": 1726849201.245, "sequence_number": 1, "sampling_rate": 50.0, "transmission_information": "SIMULATED", "status_error_information": "OK"},
    })


if __name__ == "__main__":
    packet = sample()
    processed = process_telemetry(packet)
    alerts = generate_alerts(packet, processed)
    print("PROCESSED OK")
    print(processed.model_dump())
    print("ALERTS OK")
    print([a.__dict__ for a in alerts])
