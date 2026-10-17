from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase


DATABASE_URL = "sqlite:///./apex01_telemetry.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)


class Base(DeclarativeBase):
    pass


def initialize_database():
    """Create new tables and upgrade the existing prototype DB in place."""
    Base.metadata.create_all(bind=engine)

    additions = {
        "raw_telemetry": {
            "battery_current": "FLOAT",
        },
        "processed_telemetry": {
            "longitudinal_acceleration": "FLOAT",
            "lateral_acceleration": "FLOAT",
            "vertical_acceleration": "FLOAT",
            "yaw_rate": "FLOAT",
            "cornering_intensity": "FLOAT",
            "braking_intensity": "FLOAT",
            "acceleration_intensity": "FLOAT",
            "possible_wheel_slip": "BOOLEAN",
            "possible_wheel_lock": "BOOLEAN",
            "wheel_speed_mismatch": "BOOLEAN",
        },
        "alerts": {
            "cleared_timestamp": "FLOAT",
            "is_active": "BOOLEAN NOT NULL DEFAULT 1",
        },
    }

    inspector = inspect(engine)

    with engine.begin() as connection:
        for table, columns in additions.items():
            if not inspector.has_table(table):
                continue

            existing = {
                column["name"]
                for column in inspect(engine).get_columns(table)
            }

            for name, sql_type in columns.items():
                if name not in existing:
                    connection.execute(
                        text(
                            f"ALTER TABLE {table} "
                            f"ADD COLUMN {name} {sql_type}"
                        )
                    )
