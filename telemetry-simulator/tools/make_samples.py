"""Regenerates everything in samples/ deterministically:  python tools/make_samples.py"""
import json
import os
import subprocess
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from telemetry_sim import SimConfig, Simulator, get_playlist  # noqa: E402

OUT = os.path.join(ROOT, "samples")
START = 1_759_651_200_000
os.makedirs(OUT, exist_ok=True)

rows = list(Simulator(SimConfig(seed=42, start_time_ms=START), get_playlist("full")).run())
by = defaultdict(list)
for pkt, truth in rows:
    by[truth["scenario"]].append(pkt)

pick = {   # the most characteristic moment of each scenario
    "normal_driving": lambda ps: ps[150],
    "acceleration": lambda ps: max(ps, key=lambda p: p["imu"]["ax"]),
    "braking": lambda ps: min(ps, key=lambda p: p["imu"]["ax"]),
    "cornering": lambda ps: max(ps, key=lambda p: p["imu"]["ay"]),
    "hard_corner": lambda ps: max(ps, key=lambda p: p["imu"]["ay"]),
    "wheel_slip": lambda ps: max(ps, key=lambda p: p["wheel_speeds"]["front_left"] - p["wheel_speeds"]["rear_left"]),
    "gps_loss": lambda ps: ps[len(ps) // 2],
    "high_temperature": lambda ps: ps[-1],
    "low_battery": lambda ps: ps[-1],
}
samples = {name: f(by[name]) for name, f in pick.items()}
with open(os.path.join(OUT, "sample_packet.json"), "w") as fh:
    json.dump(samples["normal_driving"], fh, indent=2)
with open(os.path.join(OUT, "sample_packets_by_scenario.json"), "w") as fh:
    json.dump(samples, fh, indent=2)
with open(os.path.join(OUT, "custom_playlist_example.json"), "w") as fh:
    json.dump([p.to_dict() for p in get_playlist("braking")], fh, indent=2)

subprocess.run([sys.executable, "-m", "telemetry_sim", "--seed", "42", "--start-time", str(START),
                "--drop-rate", "0.01", "--dup-rate", "0.01", "--reorder-rate", "0.01",
                "--reboot-at", "100",
                "--output", "file:" + os.path.join(OUT, "full_run_with_faults.jsonl"),
                "--labels", os.path.join(OUT, "full_run_with_faults.labels.jsonl")], cwd=ROOT, check=True)
print("samples written to", OUT)
