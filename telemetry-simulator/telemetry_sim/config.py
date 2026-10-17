"""Static configuration: vehicle parameters, sensor noise, warning thresholds, sim settings."""
from __future__ import annotations

from dataclasses import dataclass, field, fields

SCHEMA_VERSION = "1.0.0"
G = 9.80665  # m/s²


@dataclass
class VehicleParams:
    """Defaults describe a ~1.3 t front-wheel-drive car with a 12 V electrical system."""
    mass_kg: float = 1300.0
    max_power_w: float = 90_000.0
    max_drive_accel: float = 4.5          # m/s², gearing/traction cap at full throttle
    drag_cda_m2: float = 0.70             # drag coefficient x frontal area
    air_density: float = 1.2
    rolling_coeff: float = 0.015
    brake_gain: float = 0.12              # m/s² of deceleration per bar of line pressure
    wheel_radius_m: float = 0.31
    track_width_m: float = 1.50
    gear_ratios: tuple = (3.6, 2.1, 1.45, 1.1, 0.87)
    final_drive: float = 3.9
    idle_rpm: float = 850.0
    redline_rpm: float = 6500.0
    upshift_rpm: float = 2800.0           # light throttle; rises toward redline with throttle
    downshift_rpm: float = 1300.0
    drivetrain: str = "fwd"               # "fwd" or "rwd" (which axle can spin)
    driven_axle_load_fraction: float = 0.6
    nominal_coolant_c: float = 88.0
    battery_capacity_ah: float = 45.0
    battery_internal_r_ohm: float = 0.02


@dataclass
class NoiseParams:
    gps_pos_m: float = 1.2                # std dev of slowly wandering position error
    gps_speed_kmh: float = 0.3
    gps_alt_m: float = 1.5
    accel_ms2: float = 0.05
    gyro_dps: float = 0.15
    road_vibration_ms2: float = 0.008     # extra az noise per km/h of speed
    wheel_kmh: float = 0.15
    temp_c: float = 0.1
    voltage_v: float = 0.02
    current_a: float = 0.3
    rpm: float = 8.0
    throttle_pct: float = 0.2
    brake_bar: float = 0.15

    def scaled(self, k: float) -> "NoiseParams":
        return NoiseParams(**{f.name: getattr(self, f.name) * k for f in fields(self)})


@dataclass
class Thresholds:
    """Device-side warning thresholds (what the ESP32 firmware would flag itself)."""
    coolant_warn_c: float = 105.0
    coolant_crit_c: float = 112.0
    engine_warn_c: float = 115.0
    engine_crit_c: float = 125.0
    battery_warn_v: float = 12.0
    battery_crit_v: float = 11.5
    discharge_warn_a: float = -5.0        # current below this while engine runs = not charging
    min_satellites: int = 5


@dataclass
class SimConfig:
    sampling_rate_hz: float = 10.0
    gps_rate_hz: float = 5.0              # real GPS modules update at 1-10 Hz; values are held between fixes
    device_id: str = "SIM-ESP32-01"
    transport: str = "stdout"
    start_lat: float = 28.3487            # arbitrary default start point, configurable
    start_lon: float = 77.5331
    start_alt_m: float = 195.0
    start_heading_deg: float = 90.0       # compass heading, clockwise from north
    start_time_ms: int | None = None      # None = current wall-clock time
    timestamp_jitter_ms: float = 1.5
    fault_time_scale: float = 6.0         # speeds up thermal faults so they fit in a short phase
    battery_time_scale: float = 120.0     # speeds up battery discharge during alternator failure
    seed: int | None = None
    noise_scale: float = 1.0
    vehicle: VehicleParams = field(default_factory=VehicleParams)
    noise: NoiseParams = field(default_factory=NoiseParams)
    thresholds: Thresholds = field(default_factory=Thresholds)
