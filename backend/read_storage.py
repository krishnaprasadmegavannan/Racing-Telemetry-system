from sqlalchemy import select
from sqlalchemy.orm import Session

from storage.database import engine
from storage.models import RawTelemetry


with Session(engine) as session:

    statement = select(RawTelemetry).order_by(
        RawTelemetry.id
    )

    records = session.execute(statement).scalars().all()

    print("RAW TELEMETRY RECORDS")
    print("=====================")

    for record in records:
        print()
        print("Record ID:", record.id)
        print("Timestamp:", record.timestamp)
        print("Sequence:", record.sequence_number)

        print("GPS:")
        print("  Latitude:", record.latitude)
        print("  Longitude:", record.longitude)
        print("  Speed:", record.speed)

        print("IMU:")
        print("  ax:", record.ax)
        print("  ay:", record.ay)
        print("  az:", record.az)

        print("Temperatures:")
        print("  Coolant:", record.coolant_temperature)
        print("  Engine:", record.engine_temperature)

        print("Wheel speeds:")
        print("  FL:", record.front_left)
        print("  FR:", record.front_right)
        print("  RL:", record.rear_left)
        print("  RR:", record.rear_right)

        print("Vehicle:")
        print("  RPM:", record.rpm)
        print("  Throttle:", record.throttle)
        print("  Brake pressure:", record.brake_pressure)
        print("  Battery voltage:", record.battery_voltage)

        print("Status:", record.status_error_information)