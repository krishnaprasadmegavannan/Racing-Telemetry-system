import csv
import io

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from models.telemetry import TelemetryPacket
from processing.cleaning import clean_telemetry_packet
from processing.features import process_telemetry
from processing.validation import validate_engineering_values

from analytics.event_detection import detect_events
from analytics.lap_analysis import haversine_m, split_into_three_sectors

from alerts.alert_engine import generate_alerts

from storage.database import Base, engine
from storage.models import (
    RawTelemetry,
    ProcessedTelemetryDB,
    SessionDB,
    LapDB,
    SectorDB,
    EventDB,
    AlertDB,
)

from websocket.manager import manager


router = APIRouter(prefix="/telemetry", tags=["Telemetry"])


# ============================================================
# DATABASE INITIALIZATION AND MIGRATION
# ============================================================

def _ensure_database():
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

    with engine.begin() as connection:
        inspector = inspect(connection)

        for table_name, columns in additions.items():
            if not inspector.has_table(table_name):
                continue

            existing_columns = {
                column["name"]
                for column in inspector.get_columns(table_name)
            }

            for column_name, column_type in columns.items():
                if column_name not in existing_columns:
                    connection.execute(
                        text(
                            f"ALTER TABLE {table_name} "
                            f"ADD COLUMN {column_name} {column_type}"
                        )
                    )

                    existing_columns.add(column_name)

                    # When migrating an old database containing repeated
                    # per-packet alerts, preserve only the latest record
                    # for each alert type/message as active.
                    if (
                        table_name == "alerts"
                        and column_name == "is_active"
                    ):
                        connection.execute(
                            text("""
                                UPDATE alerts
                                SET is_active = 0,
                                    cleared_timestamp = timestamp
                                WHERE id NOT IN (
                                    SELECT MAX(id)
                                    FROM alerts
                                    GROUP BY alert_type, message
                                )
                            """)
                        )


# ============================================================
# SESSION HELPERS
# ============================================================

def _active_session(session):
    return (
        session.query(SessionDB)
        .filter(SessionDB.status == "ACTIVE")
        .order_by(SessionDB.id.desc())
        .first()
    )


def _get_or_create_session(session, packet):
    current = _active_session(session)

    if current:
        return current

    current = SessionDB(
        session_name="Apex-01 Session",
        start_timestamp=packet.metadata.timestamp,
        status="ACTIVE",
        track_name="SIMULATED TRACK",
    )

    session.add(current)
    session.flush()

    return current


# ============================================================
# SERIALIZATION HELPERS
# ============================================================

def _raw_dict(record):
    return {
        "gps": {
            "latitude": record.latitude,
            "longitude": record.longitude,
            "speed": record.speed,
            "altitude": record.altitude,
            "satellite_count": record.satellite_count,
            "fix_status": record.fix_status,
        },
        "imu": {
            "ax": record.ax,
            "ay": record.ay,
            "az": record.az,
            "gx": record.gx,
            "gy": record.gy,
            "gz": record.gz,
        },
        "temperature": {
            "coolant_temperature": record.coolant_temperature,
            "engine_temperature": record.engine_temperature,
        },
        "wheel_speeds": {
            "front_left": record.front_left,
            "front_right": record.front_right,
            "rear_left": record.rear_left,
            "rear_right": record.rear_right,
        },
        "vehicle_can": {
            "rpm": record.rpm,
            "throttle": record.throttle,
            "brake_pressure": record.brake_pressure,
            "battery_voltage": record.battery_voltage,
            "battery_current": record.battery_current,
        },
        "metadata": {
            "timestamp": record.timestamp,
            "sequence_number": record.sequence_number,
            "sampling_rate": record.sampling_rate,
            "transmission_information": record.transmission_information,
            "status_error_information": record.status_error_information,
        },
    }


def _processed_dict(record):
    return {
        column.name: getattr(record, column.name)
        for column in ProcessedTelemetryDB.__table__.columns
        if column.name != "id"
    }


def _session_dict(session_record):
    return {
        "id": session_record.id,
        "session_name": session_record.session_name,
        "start_timestamp": session_record.start_timestamp,
        "end_timestamp": session_record.end_timestamp,
        "status": session_record.status,
        "track_name": session_record.track_name,
    }


def _lap_dict(lap):
    return {
        "id": lap.id,
        "session_id": lap.session_id,
        "lap_number": lap.lap_number,
        "start_timestamp": lap.start_timestamp,
        "end_timestamp": lap.end_timestamp,
        "lap_time": lap.lap_time,
    }


def _alert_dict(alert):
    return {
        "id": alert.id,
        "timestamp": alert.timestamp,
        "sequence_number": alert.sequence_number,
        "alert_type": alert.alert_type,
        "severity": alert.severity,
        "message": alert.message,
        "value": alert.value,
        "acknowledged": alert.acknowledged,
        "is_active": alert.is_active,
        "cleared_timestamp": alert.cleared_timestamp,
    }


# ============================================================
# RECEIVE TELEMETRY
# ============================================================

@router.post("")
async def receive_telemetry(packet: TelemetryPacket):
    errors = validate_engineering_values(packet)

    if errors:
        raise HTTPException(
            status_code=422,
            detail={
                "status": "rejected",
                "errors": errors,
            },
        )

    clean_telemetry_packet(packet)

    with Session(engine) as session:
        try:
            previous = (
                session.query(RawTelemetry)
                .order_by(RawTelemetry.sequence_number.desc())
                .first()
            )

            missing_packets = 0
            previous_speed = None
            previous_timestamp = None

            # Validate sequence number and timestamp.
            if previous:
                sequence_number = packet.metadata.sequence_number

                # Hardware power-cycle / reboot detection:
                # If microcontroller restarts (seq resets to <= 1 or timestamp decreases),
                # archive previous session and start clean new session without rejecting.
                if sequence_number <= 1 or packet.metadata.timestamp < previous.timestamp:
                    active_sess = _active_session(session)
                    if active_sess:
                        active_sess.status = "COMPLETED"
                        active_sess.end_timestamp = previous.timestamp
                        session.flush()
                    previous = None
                else:
                    if sequence_number == previous.sequence_number:
                        raise HTTPException(
                            status_code=409,
                            detail={
                                "status": "rejected",
                                "reason": "Duplicate sequence number.",
                            },
                        )

                    if sequence_number < previous.sequence_number:
                        raise HTTPException(
                            status_code=409,
                            detail={
                                "status": "rejected",
                                "reason": "Out-of-order telemetry packet.",
                            },
                        )

                    if packet.metadata.timestamp <= previous.timestamp:
                        raise HTTPException(
                            status_code=409,
                            detail={
                                "status": "rejected",
                                "reason": "Telemetry timestamp must increase.",
                            },
                        )

                    missing_packets = max(
                        0,
                        sequence_number - previous.sequence_number - 1,
                    )

                    previous_speed = previous.speed
                    previous_timestamp = previous.timestamp

            # Obtain the active session.
            current_session = _get_or_create_session(
                session,
                packet,
            )

            # Process telemetry and generate events/alerts.
            processed = process_telemetry(
                packet,
                previous_speed,
                previous_timestamp,
            )

            events = detect_events(packet, processed)
            alerts = generate_alerts(packet, processed)

            # ------------------------------------------------
            # SAVE RAW TELEMETRY
            # ------------------------------------------------

            raw = RawTelemetry(
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

                coolant_temperature=(
                    packet.temperature.coolant_temperature
                ),
                engine_temperature=(
                    packet.temperature.engine_temperature
                ),

                front_left=packet.wheel_speeds.front_left,
                front_right=packet.wheel_speeds.front_right,
                rear_left=packet.wheel_speeds.rear_left,
                rear_right=packet.wheel_speeds.rear_right,

                rpm=packet.vehicle_can.rpm,
                throttle=packet.vehicle_can.throttle,
                brake_pressure=packet.vehicle_can.brake_pressure,
                battery_voltage=packet.vehicle_can.battery_voltage,
                battery_current=packet.vehicle_can.battery_current,

                timestamp=packet.metadata.timestamp,
                sequence_number=packet.metadata.sequence_number,
                sampling_rate=packet.metadata.sampling_rate,
                transmission_information=(
                    packet.metadata.transmission_information
                ),
                status_error_information=(
                    packet.metadata.status_error_information
                ),
            )

            session.add(raw)

            # ------------------------------------------------
            # SAVE PROCESSED TELEMETRY
            # ------------------------------------------------

            processed_record = ProcessedTelemetryDB(
                timestamp=packet.metadata.timestamp,
                sequence_number=packet.metadata.sequence_number,

                longitudinal_acceleration=(
                    processed.longitudinal_acceleration
                ),
                lateral_acceleration=(
                    processed.lateral_acceleration
                ),
                vertical_acceleration=(
                    processed.vertical_acceleration
                ),

                resultant_acceleration=(
                    processed.resultant_acceleration
                ),
                yaw_rate=processed.yaw_rate,

                cornering_intensity=processed.cornering_intensity,
                braking_intensity=processed.braking_intensity,
                acceleration_intensity=processed.acceleration_intensity,

                wheel_speed_difference=(
                    processed.wheel_speed_difference
                ),
                fastest_wheel=processed.fastest_wheel,
                slowest_wheel=processed.slowest_wheel,

                possible_wheel_slip=processed.possible_wheel_slip,
                possible_wheel_lock=processed.possible_wheel_lock,
                wheel_speed_mismatch=processed.wheel_speed_mismatch,

                speed_acceleration=processed.speed_acceleration,
            )

            session.add(processed_record)

            # ------------------------------------------------
            # SAVE EVENTS
            # ------------------------------------------------

            for event in events:
                session.add(
                    EventDB(
                        timestamp=packet.metadata.timestamp,
                        sequence_number=packet.metadata.sequence_number,
                        event_type=event["type"],
                        severity=event["severity"],
                        description=event["description"],
                    )
                )

            # ------------------------------------------------
            # ALERT INCIDENT MANAGEMENT
            # ------------------------------------------------
            #
            # An alert is created only when a condition becomes active.
            # It remains active while that condition persists.
            # When the condition disappears, the incident is cleared.
            # If it happens again later, a new incident is created.
            #
            # This prevents one database row per telemetry packet.
            # ------------------------------------------------

            current_alerts = {
                (alert.alert_type, alert.message): alert
                for alert in alerts
            }

            new_alerts = []

            active_rows = (
                session.query(AlertDB)
                .filter(AlertDB.is_active.is_(True))
                .all()
            )

            active_by_key = {}

            for row in active_rows:
                key = (row.alert_type, row.message)
                active_by_key.setdefault(key, []).append(row)

            # Resolve alerts that are no longer present.
            for key, rows in active_by_key.items():
                if key not in current_alerts:
                    for row in rows:
                        row.is_active = False
                        row.cleared_timestamp = packet.metadata.timestamp

            # Create incidents only for newly appearing conditions.
            for key, alert in current_alerts.items():
                if key in active_by_key:
                    continue

                incident = AlertDB(
                    timestamp=packet.metadata.timestamp,
                    sequence_number=packet.metadata.sequence_number,
                    alert_type=alert.alert_type,
                    severity=alert.severity,
                    message=alert.message,
                    value=alert.value,
                    acknowledged=False,
                    is_active=True,
                    cleared_timestamp=None,
                )

                session.add(incident)
                session.flush()

                new_alerts.append(_alert_dict(incident))

            # ------------------------------------------------
            # LAP AND SECTOR DETECTION
            # ------------------------------------------------

            lap_created = None

            if previous:
                first_raw = (
                    session.query(RawTelemetry)
                    .order_by(RawTelemetry.sequence_number.asc())
                    .first()
                )

                if first_raw:
                    now_distance = haversine_m(
                        first_raw.latitude,
                        first_raw.longitude,
                        packet.gps.latitude,
                        packet.gps.longitude,
                    )

                    previous_distance = haversine_m(
                        first_raw.latitude,
                        first_raw.longitude,
                        previous.latitude,
                        previous.longitude,
                    )

                    # A lap is detected when the vehicle returns
                    # within 30 metres of its starting position
                    # after having moved farther away.
                    if now_distance <= 30 and previous_distance > 30:
                        lap_count = (
                            session.query(LapDB)
                            .filter(
                                LapDB.session_id == current_session.id
                            )
                            .count()
                        )

                        lap_number = lap_count + 1

                        last_lap = (
                            session.query(LapDB)
                            .filter(
                                LapDB.session_id == current_session.id
                            )
                            .order_by(LapDB.lap_number.desc())
                            .first()
                        )

                        lap_start = (
                            last_lap.end_timestamp
                            if last_lap
                            else current_session.start_timestamp
                        )

                        lap_created = LapDB(
                            session_id=current_session.id,
                            lap_number=lap_number,
                            start_timestamp=lap_start,
                            end_timestamp=packet.metadata.timestamp,
                            lap_time=(
                                packet.metadata.timestamp - lap_start
                            ),
                        )

                        session.add(lap_created)
                        session.flush()

                        sectors = split_into_three_sectors(
                            lap_start,
                            packet.metadata.timestamp,
                        )

                        for sector_number, (start, end, duration) in enumerate(
                            sectors,
                            start=1,
                        ):
                            session.add(
                                SectorDB(
                                    session_id=current_session.id,
                                    lap_number=lap_number,
                                    sector_number=sector_number,
                                    start_timestamp=start,
                                    end_timestamp=end,
                                    sector_time=duration,
                                )
                            )

            # ------------------------------------------------
            # COMMIT TRANSACTION
            # ------------------------------------------------

            session.commit()

            result = {
                "status": "accepted",
                "session_id": current_session.id,
                "sequence_number": packet.metadata.sequence_number,
                "missing_packets": missing_packets,
                "processed": processed.model_dump(),
                "events": events,
                "alerts": [alert.__dict__ for alert in alerts],
                "lap_created": (
                    _lap_dict(lap_created)
                    if lap_created
                    else None
                ),
            }

            # Send all telemetry updates to the dashboard.
            # Only newly opened alert incidents are broadcast.
            await manager.broadcast(
                {
                    "type": "telemetry_update",
                    "raw": packet.model_dump(),
                    "processed": processed.model_dump(),
                    "events": events,
                    "alerts": new_alerts,
                    "session": _session_dict(current_session),
                    "lap": _lap_dict(lap_created) if lap_created else None,
                    "stream": {
                        "missing_packets": missing_packets,
                    },
                }
            )

            return result

        except HTTPException:
            session.rollback()
            raise

        except Exception as exc:
            session.rollback()

            raise HTTPException(
                status_code=500,
                detail={
                    "status": "error",
                    "message": str(exc),
                },
            )


# ============================================================
# RAW TELEMETRY ENDPOINTS
# ============================================================

@router.get("")
def get_telemetry(limit: int = 50):
    return get_telemetry_history(limit)


@router.get("/latest")
def get_latest():
    with Session(engine) as session:
        record = (
            session.query(RawTelemetry)
            .order_by(RawTelemetry.sequence_number.desc())
            .first()
        )

        if not record:
            raise HTTPException(
                status_code=404,
                detail="No telemetry available.",
            )

        return {
            "status": "success",
            "telemetry": _raw_dict(record),
        }


@router.get("/history")
def get_telemetry_history(limit: int = 50):
    if not 1 <= limit <= 1000:
        raise HTTPException(
            status_code=400,
            detail="limit must be between 1 and 1000",
        )

    with Session(engine) as session:
        rows = (
            session.query(RawTelemetry)
            .order_by(RawTelemetry.sequence_number.desc())
            .limit(limit)
            .all()
        )

        return {
            "status": "success",
            "count": len(rows),
            "telemetry": [_raw_dict(row) for row in rows],
        }


# ============================================================
# PROCESSED TELEMETRY ENDPOINTS
# ============================================================

@router.get("/processed/latest")
def processed_latest():
    with Session(engine) as session:
        record = (
            session.query(ProcessedTelemetryDB)
            .order_by(ProcessedTelemetryDB.sequence_number.desc())
            .first()
        )

        if not record:
            raise HTTPException(
                status_code=404,
                detail="No processed telemetry available.",
            )

        return {
            "status": "success",
            "processed": _processed_dict(record),
        }


@router.get("/processed/history")
def processed_history(limit: int = 50):
    if not 1 <= limit <= 1000:
        raise HTTPException(
            status_code=400,
            detail="limit must be between 1 and 1000",
        )

    with Session(engine) as session:
        rows = (
            session.query(ProcessedTelemetryDB)
            .order_by(ProcessedTelemetryDB.sequence_number.desc())
            .limit(limit)
            .all()
        )

        return {
            "status": "success",
            "count": len(rows),
            "processed": [_processed_dict(row) for row in rows],
        }


# ============================================================
# SESSION ENDPOINTS
# ============================================================

@router.get("/session")
def get_session():
    with Session(engine) as session:
        current = (
            _active_session(session)
            or session.query(SessionDB)
            .order_by(SessionDB.id.desc())
            .first()
        )

        if not current:
            raise HTTPException(
                status_code=404,
                detail="No session available.",
            )

        return {
            "status": "success",
            "session": _session_dict(current),
        }


@router.post("/session/start")
def start_session(name: str = "Apex-01 Session"):
    with Session(engine) as session:
        current = _active_session(session)

        if current:
            return {
                "status": "already_active",
                "session": _session_dict(current),
            }

        latest = (
            session.query(RawTelemetry)
            .order_by(RawTelemetry.sequence_number.desc())
            .first()
        )

        start_timestamp = latest.timestamp if latest else 0.0

        new_session = SessionDB(
            session_name=name,
            start_timestamp=start_timestamp,
            status="ACTIVE",
            track_name="SIMULATED TRACK",
        )

        session.add(new_session)
        session.commit()
        session.refresh(new_session)

        return {
            "status": "started",
            "session": _session_dict(new_session),
        }


@router.post("/session/stop")
def stop_session():
    with Session(engine) as session:
        current = _active_session(session)

        if not current:
            raise HTTPException(
                status_code=404,
                detail="No active session.",
            )

        latest = (
            session.query(RawTelemetry)
            .order_by(RawTelemetry.sequence_number.desc())
            .first()
        )

        current.end_timestamp = (
            latest.timestamp
            if latest
            else current.start_timestamp
        )

        current.status = "COMPLETED"

        session.commit()
        session.refresh(current)

        return {
            "status": "stopped",
            "session": _session_dict(current),
        }


# ============================================================
# LAP AND SECTOR ENDPOINTS
# ============================================================

@router.get("/laps")
def get_laps(session_id: int | None = None):
    with Session(engine) as session:
        query = session.query(LapDB).order_by(LapDB.lap_number.asc())

        if session_id is not None:
            query = query.filter(LapDB.session_id == session_id)

        rows = query.all()

        return {
            "status": "success",
            "count": len(rows),
            "laps": [_lap_dict(row) for row in rows],
        }


@router.get("/sectors")
def get_sectors(
    session_id: int | None = None,
    lap_number: int | None = None,
):
    with Session(engine) as session:
        query = session.query(SectorDB).order_by(
            SectorDB.lap_number.asc(),
            SectorDB.sector_number.asc(),
        )

        if session_id is not None:
            query = query.filter(SectorDB.session_id == session_id)

        if lap_number is not None:
            query = query.filter(SectorDB.lap_number == lap_number)

        rows = query.all()

        sectors = [
            {
                column.name: getattr(row, column.name)
                for column in SectorDB.__table__.columns
                if column.name != "id"
            }
            for row in rows
        ]

        return {
            "status": "success",
            "count": len(rows),
            "sectors": sectors,
        }


# ============================================================
# EVENT ENDPOINT
# ============================================================

@router.get("/events")
def get_events(limit: int = 100):
    with Session(engine) as session:
        rows = (
            session.query(EventDB)
            .order_by(EventDB.id.desc())
            .limit(max(1, min(limit, 1000)))
            .all()
        )

        events = [
            {
                column.name: getattr(row, column.name)
                for column in EventDB.__table__.columns
                if column.name != "id"
            }
            | {"id": row.id}
            for row in rows
        ]

        return {
            "status": "success",
            "count": len(rows),
            "events": events,
        }


# ============================================================
# ALERT ENDPOINTS
# ============================================================

@router.get("/alerts")
def get_alerts(
    limit: int = 100,
    active_only: bool = False,
):
    with Session(engine) as session:
        query = session.query(AlertDB)

        if active_only:
            query = query.filter(AlertDB.is_active.is_(True))

        rows = (
            query.order_by(AlertDB.id.desc())
            .limit(max(1, min(limit, 1000)))
            .all()
        )

        return {
            "status": "success",
            "count": len(rows),
            "alerts": [_alert_dict(row) for row in rows],
        }


@router.patch("/alerts/{alert_id}/ack")
def acknowledge_alert(alert_id: int):
    with Session(engine) as session:
        alert = session.get(AlertDB, alert_id)

        if not alert:
            raise HTTPException(
                status_code=404,
                detail="Alert not found.",
            )

        alert.acknowledged = True

        session.commit()

        return {
            "status": "acknowledged",
            "alert_id": alert_id,
        }


# ============================================================
# CSV EXPORT
# ============================================================

@router.get("/export")
def export_data(kind: str = "raw"):
    def generate_csv():
        with Session(engine) as session:
            output = io.StringIO()
            writer = csv.writer(output)

            if kind.lower() == "processed":
                columns = [
                    column.name
                    for column in ProcessedTelemetryDB.__table__.columns
                ]
                writer.writerow(columns)
                yield output.getvalue()
                output.seek(0)
                output.truncate(0)

                query = (
                    session.query(ProcessedTelemetryDB)
                    .order_by(ProcessedTelemetryDB.sequence_number.asc())
                    .yield_per(1000)
                )
                for row in query:
                    writer.writerow([getattr(row, col) for col in columns])
                    yield output.getvalue()
                    output.seek(0)
                    output.truncate(0)

            else:
                columns = [
                    column.name
                    for column in RawTelemetry.__table__.columns
                ]
                writer.writerow(columns)
                yield output.getvalue()
                output.seek(0)
                output.truncate(0)

                query = (
                    session.query(RawTelemetry)
                    .order_by(RawTelemetry.sequence_number.asc())
                    .yield_per(1000)
                )
                for row in query:
                    writer.writerow([getattr(row, col) for col in columns])
                    yield output.getvalue()
                    output.seek(0)
                    output.truncate(0)

    filename = (
        "apex01_processed.csv"
        if kind.lower() == "processed"
        else "apex01_raw.csv"
    )

    return StreamingResponse(
        generate_csv(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        },
    )


# ============================================================
# WEBSOCKET
# ============================================================

@router.websocket("/ws")
async def telemetry_websocket(websocket: WebSocket):
    await manager.connect(websocket)

    try:
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        manager.disconnect(websocket)

    except Exception:
        manager.disconnect(websocket)