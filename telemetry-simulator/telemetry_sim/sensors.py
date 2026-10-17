"""Sensor models and packet assembly. This file is where the JSON contract is produced."""
from __future__ import annotations

import math
import random

from .config import G, SCHEMA_VERSION, NoiseParams, SimConfig
from .vehicle import VehicleModel, approach, clamp

EARTH_R = 6_378_137.0
WHEEL_NAMES = ("front_left", "front_right", "rear_left", "rear_right")


class GpsReceiver:
    """Updates at gps_rate_hz and holds its last reading in between, like a real module."""

    def __init__(self, cfg: SimConfig, rng: random.Random, noise: NoiseParams):
        self.cfg, self.rng, self.n = cfg, rng, noise
        self.period = 1.0 / cfg.gps_rate_hz
        self.next_t = 0.0
        self.sats_f = 10.0
        self.err_n = self.err_e = self.err_alt = 0.0
        self.reading: dict = {}

    def sample(self, t: float, m: VehicleModel, gps_loss: bool) -> dict:
        if t + 1e-9 >= self.next_t:
            while self.next_t <= t + 1e-9:
                self.next_t += self.period
            self._update(t, m, gps_loss)
        return dict(self.reading)

    def _update(self, t: float, m: VehicleModel, gps_loss: bool) -> None:
        rng, n, cfg = self.rng, self.n, self.cfg
        target = 0.3 if gps_loss else 10.5 + 1.5 * math.sin(t / 40.0)
        self.sats_f = approach(self.sats_f, target, self.period, 0.6 if gps_loss else 2.5)
        sats = max(0, int(round(self.sats_f + rng.gauss(0, 0.25))))
        fix = "NO_FIX" if sats < 3 else ("2D_FIX" if sats == 3 else "3D_FIX")

        # Position error wanders slowly (Gauss-Markov) and grows as satellites drop
        k = math.exp(-self.period / 20.0)
        q = math.sqrt(1 - k * k)
        sigma = n.gps_pos_m * 10.0 / max(sats, 3)
        self.err_n = k * self.err_n + q * sigma * rng.gauss(0, 1)
        self.err_e = k * self.err_e + q * sigma * rng.gauss(0, 1)
        self.err_alt = k * self.err_alt + q * n.gps_alt_m * 10.0 / max(sats, 3) * rng.gauss(0, 1)

        if fix == "NO_FIX":
            self.reading = {"latitude": None, "longitude": None, "speed": None, "altitude": None,
                            "satellite_count": sats, "fix_status": fix}
            return
        lat0 = cfg.start_lat
        lat = lat0 + math.degrees((m.north + self.err_n) / EARTH_R)
        lon = cfg.start_lon + math.degrees((m.east + self.err_e) / (EARTH_R * math.cos(math.radians(lat0))))
        speed = m.v * 3.6 + rng.gauss(0, n.gps_speed_kmh) if m.v > 0.1 else abs(rng.gauss(0, n.gps_speed_kmh / 2))
        alt = None if fix == "2D_FIX" else round(m.altitude() + self.err_alt, 1)
        self.reading = {"latitude": round(lat, 7), "longitude": round(lon, 7), "speed": round(max(0.0, speed), 2),
                        "altitude": alt, "satellite_count": sats, "fix_status": fix}


class PacketBuilder:
    def __init__(self, cfg: SimConfig, rng: random.Random):
        self.cfg, self.rng = cfg, rng
        self.n = cfg.noise.scaled(cfg.noise_scale)
        self.gps = GpsReceiver(cfg, rng, self.n)
        self.rssi = -58.0
        self.levels: dict[str, int] = {}
        self.not_charging = False

    def _g(self, sigma: float) -> float:
        return self.rng.gauss(0.0, sigma)

    def build(self, *, t: float, m: VehicleModel, gps_loss: bool, timestamp_ms: int,
              seq: int, boot_id: str, uptime_ms: int) -> dict:
        cfg, n, g = self.cfg, self.n, self._g
        v_kmh = m.v * 3.6
        gps = self.gps.sample(t, m, gps_loss)
        theta = m.grade_theta
        imu = {   # accelerometer reports specific force: includes gravity, so az ≈ +9.81 at rest
            "ax": round(m.a_long + G * math.sin(theta) + g(n.accel_ms2), 3),
            "ay": round(m.a_lat + g(n.accel_ms2), 3),
            "az": round(G * math.cos(theta) + g(n.accel_ms2 + n.road_vibration_ms2 * v_kmh), 3),
            "gx": round(math.degrees(m.roll_rate) + g(n.gyro_dps), 2),
            "gy": round(math.degrees(m.pitch_rate) + g(n.gyro_dps), 2),
            "gz": round(math.degrees(m.yaw_rate) + g(n.gyro_dps), 2),
        }
        temperature = {
            "coolant_temperature": round(m.coolant + g(n.temp_c), 1),
            "engine_temperature": round(m.engine_temp + g(n.temp_c), 1),
        }
        wheel_speeds = {name: (0.0 if w < 0.05 else round(max(0.0, w * 3.6 + g(n.wheel_kmh)), 2))
                        for name, w in zip(WHEEL_NAMES, m.wheels)}
        vehicle = {
            "rpm": int(round(m.rpm + g(n.rpm))),
            "throttle": round(clamp(m.throttle + g(n.throttle_pct), 0.0, 100.0), 1),
            "brake_pressure": round(max(0.0, m.brake_bar + g(n.brake_bar)), 2),
            "battery_voltage": round(m.batt_v + g(n.voltage_v), 2),
            "battery_current": round(m.batt_i + g(n.current_a), 2),
        }
        self.rssi = approach(self.rssi, -58.0 + 6.0 * math.sin(t / 23.0), 1.0, 5.0)
        return {
            "metadata": {
                "schema_version": SCHEMA_VERSION,
                "device_id": cfg.device_id,
                "timestamp": timestamp_ms,
                "sequence_number": seq,
                "sampling_rate": cfg.sampling_rate_hz,
                "transmission_information": {
                    "transport": cfg.transport,
                    "boot_id": boot_id,
                    "uptime_ms": uptime_ms,
                    "rssi_dbm": int(round(self.rssi + g(1.5))),
                },
                "status_error_information": self._status(gps, temperature, vehicle),
            },
            "gps": gps,
            "imu": imu,
            "temperature": temperature,
            "wheel_speeds": wheel_speeds,
            "vehicle": vehicle,
        }

    # --- device-side status flags, with hysteresis so codes don't flicker on noise ---------
    def _level(self, key: str, x: float, warn: float, crit: float, hyst: float, rising: bool = True) -> int:
        if not rising:
            x, warn, crit = -x, -warn, -crit
        prev = self.levels.get(key, 0)
        if x >= crit:
            lvl = 2
        elif x >= warn:
            lvl = 2 if (prev == 2 and x >= crit - hyst) else 1
        else:
            lvl = min(prev, 1) if x >= warn - hyst else 0
        self.levels[key] = lvl
        return lvl

    def _status(self, gps: dict, temp: dict, veh: dict) -> dict:
        th = self.cfg.thresholds
        codes, worst = [], 0
        if gps["fix_status"] == "NO_FIX":
            codes.append("GPS_NO_FIX"); worst = max(worst, 1)
        elif gps["satellite_count"] < th.min_satellites:
            codes.append("GPS_LOW_SATELLITES"); worst = max(worst, 1)
        checks = [
            ("COOLANT_TEMP", temp["coolant_temperature"], th.coolant_warn_c, th.coolant_crit_c, 2.0, True),
            ("ENGINE_TEMP", temp["engine_temperature"], th.engine_warn_c, th.engine_crit_c, 2.0, True),
            ("BATTERY_VOLTAGE", veh["battery_voltage"], th.battery_warn_v, th.battery_crit_v, 0.15, False),
        ]
        for key, x, warn, crit, hyst, rising in checks:
            lvl = self._level(key, x, warn, crit, hyst, rising)
            if lvl:
                suffix = ("HIGH" if rising else "LOW") if lvl == 1 else "CRITICAL"
                codes.append(f"{key}_{suffix}")
                worst = max(worst, lvl)
        i = veh["battery_current"]
        if i < th.discharge_warn_a:
            self.not_charging = True
        elif i > -2.0:
            self.not_charging = False
        if self.not_charging:
            codes.append("BATTERY_NOT_CHARGING"); worst = max(worst, 1)
        return {"status": ("OK", "WARNING", "ERROR")[worst], "error_codes": codes}
