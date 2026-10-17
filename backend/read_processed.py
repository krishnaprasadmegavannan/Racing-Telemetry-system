from sqlalchemy import select
from sqlalchemy.orm import Session

from storage.database import engine
from storage.models import ProcessedTelemetryDB


with Session(engine) as session:

    statement = select(ProcessedTelemetryDB).order_by(
        ProcessedTelemetryDB.id
    )

    records = session.execute(statement).scalars().all()

    print("PROCESSED TELEMETRY RECORDS")
    print("==========================")

    for record in records:
        print()
        print("Record ID:", record.id)
        print("Timestamp:", record.timestamp)
        print("Sequence:", record.sequence_number)

        print("Resultant acceleration:",
              record.resultant_acceleration, "m/s²")

        print("Wheel-speed difference:",
              record.wheel_speed_difference, "km/h")

        print("Fastest wheel:",
              record.fastest_wheel)

        print("Slowest wheel:",
              record.slowest_wheel)

        print("Speed acceleration:",
              record.speed_acceleration, "m/s²")