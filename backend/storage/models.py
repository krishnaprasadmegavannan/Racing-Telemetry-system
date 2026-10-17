from sqlalchemy import Boolean, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from storage.database import Base


class RawTelemetry(Base):
    __tablename__ = "raw_telemetry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    speed: Mapped[float] = mapped_column(Float)
    altitude: Mapped[float] = mapped_column(Float)
    satellite_count: Mapped[int] = mapped_column(Integer)
    fix_status: Mapped[str] = mapped_column(String)

    ax: Mapped[float] = mapped_column(Float)
    ay: Mapped[float] = mapped_column(Float)
    az: Mapped[float] = mapped_column(Float)
    gx: Mapped[float] = mapped_column(Float)
    gy: Mapped[float] = mapped_column(Float)
    gz: Mapped[float] = mapped_column(Float)

    coolant_temperature: Mapped[float] = mapped_column(Float)
    engine_temperature: Mapped[float] = mapped_column(Float)

    front_left: Mapped[float] = mapped_column(Float)
    front_right: Mapped[float] = mapped_column(Float)
    rear_left: Mapped[float] = mapped_column(Float)
    rear_right: Mapped[float] = mapped_column(Float)

    rpm: Mapped[float] = mapped_column(Float)
    throttle: Mapped[float] = mapped_column(Float)
    brake_pressure: Mapped[float] = mapped_column(Float)
    battery_voltage: Mapped[float] = mapped_column(Float)
    battery_current: Mapped[float] = mapped_column(Float, default=0.0)

    timestamp: Mapped[float] = mapped_column(Float)
    sequence_number: Mapped[int] = mapped_column(Integer)
    sampling_rate: Mapped[float] = mapped_column(Float)
    transmission_information: Mapped[str] = mapped_column(String)
    status_error_information: Mapped[str] = mapped_column(String)


class ProcessedTelemetryDB(Base):
    __tablename__ = "processed_telemetry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    timestamp: Mapped[float] = mapped_column(Float)
    sequence_number: Mapped[int] = mapped_column(Integer)

    longitudinal_acceleration: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    lateral_acceleration: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    vertical_acceleration: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )

    resultant_acceleration: Mapped[float] = mapped_column(Float)
    yaw_rate: Mapped[float | None] = mapped_column(Float, nullable=True)

    cornering_intensity: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    braking_intensity: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    acceleration_intensity: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )

    wheel_speed_difference: Mapped[float] = mapped_column(Float)
    fastest_wheel: Mapped[str] = mapped_column(String)
    slowest_wheel: Mapped[str] = mapped_column(String)

    possible_wheel_slip: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True
    )
    possible_wheel_lock: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True
    )
    wheel_speed_mismatch: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True
    )

    speed_acceleration: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )


class SessionDB(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    session_name: Mapped[str] = mapped_column(String)
    start_timestamp: Mapped[float] = mapped_column(Float)
    end_timestamp: Mapped[float | None] = mapped_column(Float, nullable=True)

    status: Mapped[str] = mapped_column(String, default="ACTIVE")
    track_name: Mapped[str | None] = mapped_column(String, nullable=True)


class LapDB(Base):
    __tablename__ = "laps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    session_id: Mapped[int] = mapped_column(Integer)
    lap_number: Mapped[int] = mapped_column(Integer)

    start_timestamp: Mapped[float] = mapped_column(Float)
    end_timestamp: Mapped[float] = mapped_column(Float)
    lap_time: Mapped[float] = mapped_column(Float)


class SectorDB(Base):
    __tablename__ = "sectors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    session_id: Mapped[int] = mapped_column(Integer)
    lap_number: Mapped[int] = mapped_column(Integer)
    sector_number: Mapped[int] = mapped_column(Integer)

    start_timestamp: Mapped[float] = mapped_column(Float)
    end_timestamp: Mapped[float] = mapped_column(Float)
    sector_time: Mapped[float] = mapped_column(Float)


class EventDB(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    timestamp: Mapped[float] = mapped_column(Float)
    sequence_number: Mapped[int] = mapped_column(Integer)

    event_type: Mapped[str] = mapped_column(String)
    severity: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String)


class AlertDB(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    timestamp: Mapped[float] = mapped_column(Float)
    sequence_number: Mapped[int] = mapped_column(Integer)

    alert_type: Mapped[str] = mapped_column(String)
    severity: Mapped[str] = mapped_column(String)
    message: Mapped[str] = mapped_column(String)

    value: Mapped[float | None] = mapped_column(Float, nullable=True)

    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)

    # True while the underlying fault remains present.
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Timestamp at which the fault cleared.
    cleared_timestamp: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )