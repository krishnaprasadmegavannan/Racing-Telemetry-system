"""Simple but physically consistent vehicle model.

Everything the sensors report is derived from one shared state, so signals agree with
each other: braking shows up as negative ax, nose-dive pitch rate, falling wheel speeds,
falling GPS speed and falling RPM at the same time.

Body frame follows ISO 8855: x forward, y left, z up. Positive yaw = left turn.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .config import G, VehicleParams


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def approach(cur: float, target: float, dt: float, tau: float) -> float:
    """First-order lag toward target with time constant tau (seconds)."""
    if tau <= 0:
        return target
    return cur + (target - cur) * min(1.0, dt / tau)


@dataclass
class Controls:
    throttle_pct: float = 0.0
    brake_bar: float = 0.0
    lat_accel_target: float = 0.0   # m/s², + = left turn
    mu: float = 1.0                 # road friction coefficient
    cooling_failure: bool = False
    alternator_failure: bool = False


class VehicleModel:
    def __init__(self, p: VehicleParams, start_alt_m: float, heading_deg: float,
                 fault_time_scale: float, battery_time_scale: float):
        self.p = p
        self.fts = fault_time_scale
        self.bts = battery_time_scale
        # motion
        self.v = 0.0                      # m/s
        self.heading = math.radians(heading_deg)
        self.north = self.east = self.dist = 0.0
        self.base_alt = start_alt_m
        self.a_long = self.a_lat = self.yaw_rate = 0.0
        self.pitch = self.roll = self.pitch_rate = self.roll_rate = 0.0
        self.grade_theta = self._grade(0.0)
        self.slip = self.brake_slip = 0.0
        self.wheels = [0.0, 0.0, 0.0, 0.0]   # m/s: FL, FR, RL, RR
        # powertrain
        self.gear = 1
        self.rpm = p.idle_rpm
        self.throttle = 0.0
        self.brake_bar = 0.0
        # thermal / electrical
        self.coolant = p.nominal_coolant_c
        self.engine_temp = p.nominal_coolant_c + 7.0
        self.soc = 0.85
        self.batt_i = 3.0
        self.batt_v = 14.0

    # --- road profile: gentle hills so altitude and ax gravity component vary -------------
    def altitude(self) -> float:
        s = self.dist
        return self.base_alt + 4.0 * math.sin(s / 350.0) + 1.5 * math.sin(s / 90.0)

    @staticmethod
    def _grade(s: float) -> float:
        return math.atan(4.0 / 350.0 * math.cos(s / 350.0) + 1.5 / 90.0 * math.cos(s / 90.0))

    def _rpm_for(self, gear: int, wheel_speed: float) -> float:
        p = self.p
        return wheel_speed / p.wheel_radius_m * p.gear_ratios[gear - 1] * p.final_drive * 60 / (2 * math.pi)

    # --- one integration step ---------------------------------------------------------------
    def step(self, dt: float, c: Controls) -> None:
        p = self.p
        self.throttle = approach(self.throttle, clamp(c.throttle_pct, 0, 100), dt, 0.15)
        self.brake_bar = approach(self.brake_bar, clamp(c.brake_bar, 0, 150), dt, 0.12)
        v = self.v
        thr = self.throttle / 100.0

        # Longitudinal: drive force limited by power and by traction on the driven axle
        a_drive_cmd = thr * min(p.max_drive_accel, p.max_power_w / (p.mass_kg * max(v, 1.0)))
        a_trac = c.mu * G * p.driven_axle_load_fraction
        if a_drive_cmd > a_trac:                       # wheels break loose
            a_drive = 0.85 * a_trac                    # sliding friction < static
            target_slip = min(0.8, 0.10 + 0.5 * (a_drive_cmd - a_trac) / a_trac)
        else:
            a_drive = a_drive_cmd
            target_slip = 0.03 * a_drive_cmd / max(a_trac, 0.1)   # normal 0-3 % slip
        self.slip = approach(self.slip, target_slip, dt, 0.3)

        a_brake = min(self.brake_bar * p.brake_gain, c.mu * G)
        self.brake_slip = approach(self.brake_slip, 0.05 * a_brake / (c.mu * G), dt, 0.2)
        a_res = (0.5 * p.air_density * p.drag_cda_m2 * v * v / p.mass_kg
                 + (p.rolling_coeff * G if v > 0.05 else 0.0))
        theta = self.grade_theta
        a = a_drive - a_brake - a_res - G * math.sin(theta)
        if v <= 0.0 and a < 0:
            a = 0.0                                    # parked: brakes/static friction hold it
        new_v = v + a * dt
        if new_v < 0:
            a, new_v = -v / dt, 0.0
        self.a_long, self.v = a, new_v

        # Lateral: driver asks for a lateral acceleration, capped by friction, with lag
        lat_target = clamp(c.lat_accel_target, -c.mu * G, c.mu * G) * min(1.0, self.v / 5.0)
        self.a_lat = approach(self.a_lat, lat_target, dt, 0.35)
        self.yaw_rate = self.a_lat / self.v if self.v > 0.5 else 0.0   # rad/s, + = left

        # Pose integration (heading is compass/clockwise, yaw is CCW-positive)
        self.heading -= self.yaw_rate * dt
        ds = self.v * dt
        self.north += ds * math.cos(self.heading)
        self.east += ds * math.sin(self.heading)
        self.dist += ds
        new_theta = self._grade(self.dist)
        grade_rate = (new_theta - theta) / dt
        self.grade_theta = new_theta

        # Body pitch/roll on suspension: nose dives under braking, body rolls out of a corner
        pitch_t = -0.0075 * self.a_long      # rad, + = nose down
        roll_t = 0.009 * self.a_lat          # rad, + = right side down
        new_pitch = approach(self.pitch, pitch_t, dt, 0.25)
        new_roll = approach(self.roll, roll_t, dt, 0.25)
        self.pitch_rate = (new_pitch - self.pitch) / dt - grade_rate
        self.roll_rate = (new_roll - self.roll) / dt
        self.pitch, self.roll = new_pitch, new_roll

        # Wheel speeds: inside wheels slower in a corner, driven wheels spin on low grip
        kappa = self.yaw_rate / self.v if self.v > 0.5 else 0.0
        half = p.track_width_m / 2
        base = [self.v * (1 - kappa * half), self.v * (1 + kappa * half)] * 2
        driven = (0, 1) if p.drivetrain == "fwd" else (2, 3)
        spin_ref = max(self.v, 3.0)
        wheels = []
        for i, w in enumerate(base):
            w *= (1 - self.brake_slip)
            if i in driven:
                # open differential: once slipping, one wheel spins up more than the other
                bias = (1.3 if i in (0, 2) else 0.7) if self.slip > 0.08 else 1.0
                w += self.slip * spin_ref * bias
            wheels.append(max(0.0, w))
        self.wheels = wheels

        # Gearbox and engine speed
        driven_speed = sum(wheels[i] for i in driven) / 2
        up = p.upshift_rpm + thr * (p.redline_rpm - 400 - p.upshift_rpm)
        r = self._rpm_for(self.gear, driven_speed)
        if r > up and self.gear < len(p.gear_ratios):
            self.gear += 1
        elif r < p.downshift_rpm and self.gear > 1:
            self.gear -= 1
        r = self._rpm_for(self.gear, driven_speed)
        if self.gear == 1:
            r = max(r, p.idle_rpm + thr * 2200)        # clutch slipping when pulling away
        r = clamp(r, p.idle_rpm, p.redline_rpm)        # idle governor / rev limiter
        self.rpm = approach(self.rpm, r, dt, 0.08)

        # Temperatures (time-compressed during faults so they fit in a short scenario)
        load = 0.6 * thr + 0.4 * self.rpm / p.redline_rpm
        if c.cooling_failure:
            cool_target, tau_c = 124.0, 40.0 / self.fts
        else:
            cool_target = p.nominal_coolant_c + 3.0 * load
            tau_c = 40.0 / self.fts if self.coolant > cool_target + 3 else 40.0
        self.coolant = approach(self.coolant, cool_target, dt, tau_c)
        eng_target = self.coolant + 5.0 + 12.0 * load + (8.0 if c.cooling_failure else 0.0)
        self.engine_temp = approach(self.engine_temp, eng_target, dt, 8.0)

        # 12 V battery: alternator charges normally; on failure the loads drain it
        if c.alternator_failure:
            i_target = -(24.0 + 4.0 * load)            # ECU, fuel pump, fan, lights
        else:
            i_target = 2.0 + 25.0 * max(0.0, 0.9 - self.soc)
        self.batt_i = approach(self.batt_i, i_target, dt, 0.5)
        scale = self.bts if self.batt_i < 0 else 1.0
        self.soc = clamp(self.soc + self.batt_i * dt * scale / 3600.0 / p.battery_capacity_ah, 0.0, 1.0)
        ocv = 11.65 + 1.05 * self.soc
        v_target = (13.9 + 0.3 * (1 - self.soc)) if not c.alternator_failure \
            else ocv + self.batt_i * p.battery_internal_r_ohm
        self.batt_v = approach(self.batt_v, v_target, dt, 0.5)
