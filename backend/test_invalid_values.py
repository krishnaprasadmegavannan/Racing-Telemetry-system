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


def test_case(name, modify):
    packet_data = valid_packet.copy()

    # Copy nested dictionaries so the original packet
    # is not modified.
    packet_data["gps"] = valid_packet["gps"].copy()
    packet_data["vehicle_can"] = valid_packet["vehicle_can"].copy()
    packet_data["wheel_speeds"] = valid_packet["wheel_speeds"].copy()
    packet_data["metadata"] = valid_packet["metadata"].copy()

    modify(packet_data)

    packet = TelemetryPacket(**packet_data)
    errors = validate_engineering_values(packet)

    if errors:
        print(f"PASS: {name}")
        for error in errors:
            print(f"      {error}")
    else:
        print(f"FAIL: {name} was accepted")


print("\nENGINEERING VALIDATION TESTS")
print("============================")


test_case(
    "Negative RPM",
    lambda p: p["vehicle_can"].update(rpm=-500)
)

test_case(
    "Invalid latitude",
    lambda p: p["gps"].update(latitude=200)
)

test_case(
    "Throttle above 100%",
    lambda p: p["vehicle_can"].update(throttle=150)
)

test_case(
    "Negative front-left wheel speed",
    lambda p: p["wheel_speeds"].update(front_left=-20)
)

test_case(
    "Zero sampling rate",
    lambda p: p["metadata"].update(sampling_rate=0)
)