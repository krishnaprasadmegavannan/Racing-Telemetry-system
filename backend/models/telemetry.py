from pydantic import BaseModel, ConfigDict


class ApexModel(BaseModel):
    """
    Base model for all Apex-01 telemetry structures.
    Tolerates extra fields to support ESP32 microcontroller additions.
    """

    model_config = ConfigDict(extra="ignore")


class GPSData(ApexModel):
    latitude: float
    longitude: float
    speed: float
    altitude: float
    satellite_count: int
    fix_status: str


class IMUData(ApexModel):
    # ax = longitudinal acceleration
    # ay = lateral acceleration
    # az = vertical acceleration

    ax: float
    ay: float
    az: float

    gx: float
    gy: float
    gz: float


class TemperatureData(ApexModel):
    coolant_temperature: float
    engine_temperature: float
    brake_temp_fl: float = 0.0
    brake_temp_fr: float = 0.0
    brake_temp_rl: float = 0.0
    brake_temp_rr: float = 0.0


class WheelSpeedData(ApexModel):
    front_left: float
    front_right: float
    rear_left: float
    rear_right: float


class VehicleCANData(ApexModel):
    rpm: float
    throttle: float
    brake_pressure: float
    battery_voltage: float

    # ACS712 / electrical telemetry
    battery_current: float = 0.0
    gear: int = 0


class TelemetryMetadata(ApexModel):
    timestamp: float
    sequence_number: int
    sampling_rate: float
    transmission_information: str
    status_error_information: str


class TelemetryPacket(ApexModel):
    gps: GPSData
    imu: IMUData
    temperature: TemperatureData
    wheel_speeds: WheelSpeedData
    vehicle_can: VehicleCANData
    metadata: TelemetryMetadata
    tyre_wear: dict | None = None