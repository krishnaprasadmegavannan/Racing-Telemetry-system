from models.telemetry import TelemetryPacket
from processing.validation import validate_engineering_values


valid_packet = {
    "gps": {
        "latitude": 13.0827,
        "longitude": 80.2707,
        "speed": 142.3,
        "altitude": 18.5,
        "satellite_count": 10,
        "fix_status": "FIX"
    },

    "imu": {
        "ax": 2.1,
        "ay": 8.7,
        "az": 9.6,
        "gx": 0.2,
        "gy": 1.4,
        "gz": 18.2
    },

    "temperature": {
        "coolant_temperature": 91.2,
        "engine_temperature": 87.4
    },

    "wheel_speeds": {
        "front_left": 141.2,
        "front_right": 142.1,
        "rear_left": 139.7,
        "rear_right": 140.4
    },

    "vehicle_can": {
        "rpm": 7820,
        "throttle": 84.5,
        "brake_pressure": 0,
        "battery_voltage": 13.8
    },

    "metadata": {
        "timestamp": 1726849201.245,
        "sequence_number": 1,
        "sampling_rate": 50,
        "transmission_information": "SIMULATED",
        "status_error_information": "OK"
    }
}


# Create validated Pydantic object
packet = TelemetryPacket(**valid_packet)


# Run engineering validation
errors = validate_engineering_values(packet)


if not errors:
    print("ENGINEERING VALIDATION: PASS")
    print("All telemetry values are within expected ranges.")
else:
    print("ENGINEERING VALIDATION: FAIL")

    for error in errors:
        print("-", error)