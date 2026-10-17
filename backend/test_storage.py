from sqlalchemy.orm import Session

from models.telemetry import TelemetryPacket
from storage.database import engine
from storage.models import RawTelemetry


packet_data = {
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


# -----------------------------------------
# 1. Validate the telemetry packet
# -----------------------------------------

packet = TelemetryPacket(**packet_data)

print("Telemetry packet validated.")


# -----------------------------------------
# 2. Convert validated packet into
#    database record
# -----------------------------------------

record = RawTelemetry(
    latitude=packet.gps.latitude,
    longitude=packet.gps.longitude,
    speed=packet.gps.speed,
    altitude=packet.gps.altitude,
    satellite_count=packet.gps.satellite_count,
    fix_status=packet.gps.fix_status,

    ax=packet.imu.ax,
    ay=packet.imu.ay,
    az=packet.imu.az,
    gx=packet.imu.gx,
    gy=packet.imu.gy,
    gz=packet.imu.gz,

    coolant_temperature=packet.temperature.coolant_temperature,
    engine_temperature=packet.temperature.engine_temperature,

    front_left=packet.wheel_speeds.front_left,
    front_right=packet.wheel_speeds.front_right,
    rear_left=packet.wheel_speeds.rear_left,
    rear_right=packet.wheel_speeds.rear_right,

    rpm=packet.vehicle_can.rpm,
    throttle=packet.vehicle_can.throttle,
    brake_pressure=packet.vehicle_can.brake_pressure,
    battery_voltage=packet.vehicle_can.battery_voltage,

    timestamp=packet.metadata.timestamp,
    sequence_number=packet.metadata.sequence_number,
    sampling_rate=packet.metadata.sampling_rate,
    transmission_information=packet.metadata.transmission_information,
    status_error_information=packet.metadata.status_error_information
)


# -----------------------------------------
# 3. Store in SQLite
# -----------------------------------------

with Session(engine) as session:

    session.add(record)
    session.commit()

    print("RAW TELEMETRY: STORED")
    print("Database record ID:", record.id)