from pydantic import ValidationError
from models.telemetry import TelemetryPacket


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


# --------------------------------------------------
# TEST 1 — VALID PACKET
# --------------------------------------------------

print("\nTEST 1: Valid packet")

try:
    TelemetryPacket(**valid_packet)
    print("PASS: Valid packet accepted")
except ValidationError as error:
    print("FAIL: Valid packet rejected")
    print(error)


# --------------------------------------------------
# TEST 2 — MISSING GPS LATITUDE
# --------------------------------------------------

print("\nTEST 2: Missing GPS latitude")

missing_field_packet = valid_packet.copy()
missing_field_packet["gps"] = valid_packet["gps"].copy()
del missing_field_packet["gps"]["latitude"]

try:
    TelemetryPacket(**missing_field_packet)
    print("FAIL: Invalid packet was accepted")
except ValidationError:
    print("PASS: Missing latitude correctly rejected")


# --------------------------------------------------
# TEST 3 — WRONG RPM TYPE
# --------------------------------------------------

print("\nTEST 3: Wrong RPM data type")

wrong_type_packet = valid_packet.copy()
wrong_type_packet["vehicle_can"] = valid_packet["vehicle_can"].copy()
wrong_type_packet["vehicle_can"]["rpm"] = "FAST"

try:
    TelemetryPacket(**wrong_type_packet)
    print("FAIL: Invalid RPM was accepted")
except ValidationError:
    print("PASS: Wrong RPM type correctly rejected")


# --------------------------------------------------
# TEST 4 — MISSING IMU
# --------------------------------------------------

print("\nTEST 4: Missing IMU")

missing_imu_packet = valid_packet.copy()
del missing_imu_packet["imu"]

try:
    TelemetryPacket(**missing_imu_packet)
    print("FAIL: Missing IMU was accepted")
except ValidationError:
    print("PASS: Missing IMU correctly rejected")