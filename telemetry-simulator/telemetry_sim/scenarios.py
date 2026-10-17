"""Driving scenarios (phases), playlists and the virtual driver that executes them."""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, asdict

from .config import G, VehicleParams
from .vehicle import Controls, VehicleModel, clamp


@dataclass
class Phase:
    name: str                                   # ground-truth label written to the labels file
    duration_s: float
    target_speed_kmh: float | None = None       # closed-loop speed hold
    throttle_pct: float | None = None           # open-loop override
    brake_bar: float | None = None              # open-loop override
    release_brake_below_kmh: float | None = None
    lat_accel: float = 0.0                      # m/s², + = left turn
    weave_amplitude: float = 0.0                # gentle sinusoidal steering in normal driving
    weave_period_s: float = 8.0
    mu: float = 1.0                             # road friction (0.3 = wet/ice-like)
    gps_loss: bool = False
    cooling_failure: bool = False
    alternator_failure: bool = False

    @classmethod
    def from_dict(cls, d: dict) -> "Phase":
        return cls(**d)

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v not in (None, False, 0.0) or k in ("name", "duration_s")}


SCENARIO_NAMES = ("normal_driving", "acceleration", "braking", "cornering", "hard_corner",
                  "wheel_slip", "gps_loss", "high_temperature", "low_battery")


def normal(duration: float, speed: float = 50.0) -> Phase:
    return Phase("normal_driving", duration, target_speed_kmh=speed, weave_amplitude=0.6)


PHASES = {
    "acceleration":     lambda d=8:  Phase("acceleration", d, throttle_pct=95.0),
    "braking":          lambda d=5:  Phase("braking", d, brake_bar=70.0, release_brake_below_kmh=25.0),
    "cornering":        lambda d=12: Phase("cornering", d, target_speed_kmh=45.0, lat_accel=3.5),
    "hard_corner":      lambda d=6:  Phase("hard_corner", d, target_speed_kmh=50.0, lat_accel=8.0),
    "wheel_slip":       lambda d=5:  Phase("wheel_slip", d, throttle_pct=100.0, mu=0.3),
    "gps_loss":         lambda d=15: Phase("gps_loss", d, target_speed_kmh=50.0, weave_amplitude=0.6, gps_loss=True),
    "high_temperature": lambda d=30: Phase("high_temperature", d, target_speed_kmh=60.0, weave_amplitude=0.6,
                                           cooling_failure=True),
    "low_battery":      lambda d=30: Phase("low_battery", d, target_speed_kmh=50.0, weave_amplitude=0.6,
                                           alternator_failure=True),
}

# Full sequence: normal -> acceleration -> braking -> cornering -> hard corner -> wheel slip
#                -> GPS loss -> high temperature -> low battery   (about 145 s)
FULL_PLAYLIST = [
    normal(20),
    PHASES["acceleration"](),
    PHASES["braking"](),
    PHASES["cornering"](),
    PHASES["hard_corner"](),
    normal(6, speed=15),            # slow down to set up the low-grip launch
    PHASES["wheel_slip"](),
    normal(8),
    PHASES["gps_loss"](),
    PHASES["high_temperature"](),
    PHASES["low_battery"](),
]

# Each single scenario gets a lead-in so the vehicle is in a sensible state when it starts.
SINGLE = {
    "normal_driving":   [normal(60)],
    "acceleration":     [normal(10, 40), PHASES["acceleration"](), normal(8, 60)],
    "braking":          [normal(18, 90), PHASES["braking"](6), normal(6, 40)],
    "cornering":        [normal(10, 45), PHASES["cornering"](), normal(6)],
    "hard_corner":      [normal(10, 50), PHASES["hard_corner"](8), normal(6)],
    "wheel_slip":       [normal(8, 15), PHASES["wheel_slip"](), normal(8, 40)],
    "gps_loss":         [normal(10), PHASES["gps_loss"](20), normal(10)],
    "high_temperature": [normal(10, 60), PHASES["high_temperature"](40), normal(20)],
    "low_battery":      [normal(10), PHASES["low_battery"](40), normal(10)],
}


def get_playlist(name: str) -> list[Phase]:
    if name == "full":
        return list(FULL_PLAYLIST)
    if name in SINGLE:
        return list(SINGLE[name])
    raise ValueError(f"unknown scenario {name!r}; choose 'full' or one of {SCENARIO_NAMES}")


def load_playlist(path: str) -> list[Phase]:
    with open(path, encoding="utf-8") as fh:
        return [Phase.from_dict(d) for d in json.load(fh)]


class Driver:
    """Turns a phase description into throttle / brake / steering commands."""

    def __init__(self, p: VehicleParams):
        self.p = p
        self.brake_released = False

    def reset(self) -> None:
        self.brake_released = False

    def controls(self, ph: Phase, t: float, m: VehicleModel) -> Controls:
        p = self.p
        v_kmh = m.v * 3.6
        if ph.throttle_pct is not None or ph.brake_bar is not None:
            thr = ph.throttle_pct or 0.0
            brk = ph.brake_bar or 0.0
            if ph.release_brake_below_kmh is not None and v_kmh <= ph.release_brake_below_kmh:
                self.brake_released = True
            if self.brake_released:
                thr, brk = 0.0, 0.0                       # coast after the stop
        else:
            target = ph.target_speed_kmh if ph.target_speed_kmh is not None else v_kmh
            err = target - v_kmh
            v = m.v
            a_res = (0.5 * p.air_density * p.drag_cda_m2 * v * v / p.mass_kg
                     + p.rolling_coeff * G + G * math.sin(m.grade_theta))
            a_cap = min(p.max_drive_accel, p.max_power_w / (p.mass_kg * max(v, 1.0)))
            feedforward = max(0.0, a_res / a_cap * 100.0)
            if err >= -1.5:
                thr, brk = clamp(feedforward + 4.0 * err, 0.0, 65.0), 0.0
            else:
                thr, brk = 0.0, clamp(-1.5 * err, 0.0, 35.0)
        lat = ph.lat_accel
        if ph.weave_amplitude:
            lat += ph.weave_amplitude * math.sin(2 * math.pi * t / ph.weave_period_s)
        return Controls(thr, brk, lat, ph.mu, ph.cooling_failure, ph.alternator_failure)
