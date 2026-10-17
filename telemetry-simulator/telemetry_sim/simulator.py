"""Runs the vehicle model through a playlist and yields (packet, ground_truth) pairs."""
from __future__ import annotations

import random
import time
from typing import Iterator

from .config import SimConfig
from .scenarios import Driver, Phase
from .sensors import PacketBuilder
from .vehicle import VehicleModel


class Simulator:
    def __init__(self, cfg: SimConfig, playlist: list[Phase], loop: bool = False,
                 reboot_at_s: float | None = None, reboot_gap_s: float = 2.0):
        if cfg.sampling_rate_hz <= 0:
            raise ValueError("sampling rate must be > 0 Hz")
        self.cfg, self.playlist, self.loop = cfg, playlist, loop
        self.reboot_at_s, self.reboot_gap_s = reboot_at_s, reboot_gap_s
        self.rng = random.Random(cfg.seed)
        self.model = VehicleModel(cfg.vehicle, cfg.start_alt_m, cfg.start_heading_deg,
                                  cfg.fault_time_scale, cfg.battery_time_scale)
        self.driver = Driver(cfg.vehicle)
        self.builder = PacketBuilder(cfg, self.rng)

    @property
    def playlist_duration_s(self) -> float:
        return sum(p.duration_s for p in self.playlist)

    def _new_boot_id(self) -> str:
        return f"{self.rng.getrandbits(32):08x}"

    def run(self, duration_s: float | None = None) -> Iterator[tuple[dict, dict]]:
        cfg = self.cfg
        rate = cfg.sampling_rate_hz
        dt = 1.0 / rate
        if duration_s is None and not self.loop:
            duration_s = self.playlist_duration_s
        n_samples = None if duration_s is None else int(round(duration_s * rate))
        start_ms = cfg.start_time_ms if cfg.start_time_ms is not None else int(time.time() * 1000)

        boot_id, seq, boot_start_k, last_ts = self._new_boot_id(), 0, 0, None
        idx, t_phase = 0, 0.0
        rebooted, offline_until_k, boot_count = False, None, 0
        k = 0
        while n_samples is None or k < n_samples:
            phase = self.playlist[idx]
            if t_phase == 0.0:
                self.driver.reset()
            self.model.step(dt, self.driver.controls(phase, t_phase, self.model))
            t = k * dt

            t_phase += dt
            if t_phase >= phase.duration_s - 1e-9:
                t_phase = 0.0
                idx += 1
                if idx >= len(self.playlist):
                    idx = 0 if self.loop else len(self.playlist) - 1

            # Simulated power cycle: device goes silent, then restarts with sequence 1
            if self.reboot_at_s is not None and not rebooted and t >= self.reboot_at_s:
                rebooted, offline_until_k = True, k + max(1, int(round(self.reboot_gap_s * rate)))
            if offline_until_k is not None:
                if k < offline_until_k:
                    k += 1
                    continue
                boot_id, seq, boot_start_k, offline_until_k = self._new_boot_id(), 0, k, None
                boot_count += 1

            seq += 1
            ts = start_ms + int(round(t * 1000 + self.rng.gauss(0, cfg.timestamp_jitter_ms)))
            if last_ts is not None and ts <= last_ts:
                ts = last_ts + 1
            last_ts = ts
            uptime_ms = int(round((k - boot_start_k) * dt * 1000))
            packet = self.builder.build(t=t, m=self.model, gps_loss=phase.gps_loss, timestamp_ms=ts,
                                        seq=seq, boot_id=boot_id, uptime_ms=uptime_ms)
            truth = {"boot_id": boot_id, "boot_number": boot_count, "sequence_number": seq,
                     "timestamp": ts, "sim_time_s": round(t, 3), "scenario": phase.name}
            yield packet, truth
            k += 1
