from pydantic import BaseModel


class ProcessedTelemetry(BaseModel):
    """Engineering values derived from one telemetry packet."""

    longitudinal_acceleration: float = 0.0
    lateral_acceleration: float = 0.0
    vertical_acceleration: float = 0.0
    resultant_acceleration: float = 0.0

    yaw_rate: float = 0.0
    cornering_intensity: float = 0.0
    braking_intensity: float = 0.0
    acceleration_intensity: float = 0.0

    wheel_speed_difference: float = 0.0
    fastest_wheel: str = ""
    slowest_wheel: str = ""

    possible_wheel_slip: bool = False
    possible_wheel_lock: bool = False
    wheel_speed_mismatch: bool = False

    speed_acceleration: float | None = None
