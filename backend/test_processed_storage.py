from sqlalchemy.orm import Session

from models.telemetry import TelemetryPacket
from processing.features import process_telemetry
from storage.database import engine
from storage.models import ProcessedTelemetryDB


packet_data = {
    "gps": {
        "latitude": 13.0827,
        "longitude": 80.2707,
        "speed": 110.0,
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
        "timestamp": 11.0,
        "sequence_number": 2,
        "sampling_rate": 50,
        "transmission_information": "SIMULATED",
        "status_error_information": "OK"
    }
}


# --------------------------------------------------
# 1. Validate packet
# --------------------------------------------------

packet = TelemetryPacket(**packet_data)

print("Telemetry packet validated.")


# --------------------------------------------------
# 2. Process packet
# --------------------------------------------------

processed = process_telemetry(
    packet=packet,
    previous_speed=100.0,
    previous_timestamp=10.0
)

print("Telemetry processed.")


# --------------------------------------------------
# 3. Convert processed result to database record
# --------------------------------------------------

record = ProcessedTelemetryDB(
    timestamp=packet.metadata.timestamp,
    sequence_number=packet.metadata.sequence_number,

    resultant_acceleration=processed.resultant_acceleration,

    wheel_speed_difference=processed.wheel_speed_difference,

    fastest_wheel=processed.fastest_wheel,

    slowest_wheel=processed.slowest_wheel,

    speed_acceleration=processed.speed_acceleration
)


# --------------------------------------------------
# 4. Store processed telemetry
# --------------------------------------------------

with Session(engine) as session:

    session.add(record)
    session.commit()

    print("PROCESSED TELEMETRY: STORED")
    print("Database record ID:", record.id)