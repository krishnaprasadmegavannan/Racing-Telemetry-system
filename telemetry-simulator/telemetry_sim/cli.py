"""Command-line entry point:  python -m telemetry_sim --help"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time

from .config import SimConfig
from .faults import FaultInjector, parse_seq_list
from .scenarios import SCENARIO_NAMES, get_playlist, load_playlist
from .simulator import Simulator
from .transport import make_sink


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="telemetry_sim", description="ESP32 vehicle telemetry simulator")
    g = ap.add_argument_group("simulation")
    g.add_argument("--rate", type=float, default=10.0, help="packet sampling rate in Hz (default 10)")
    g.add_argument("--gps-rate", type=float, default=5.0, help="GPS update rate in Hz (default 5)")
    g.add_argument("--scenario", default="full", choices=["full", *SCENARIO_NAMES])
    g.add_argument("--playlist", help="JSON file with a custom list of phases (overrides --scenario)")
    g.add_argument("--duration", type=float, help="seconds to simulate (default: one pass of the playlist)")
    g.add_argument("--loop", action="store_true", help="repeat the playlist (runs forever without --duration)")
    g.add_argument("--seed", type=int, help="random seed for reproducible runs")
    g.add_argument("--start-time", type=int, help="first timestamp, Unix ms (default: now)")
    g.add_argument("--device-id", default="SIM-ESP32-01")
    g.add_argument("--noise-scale", type=float, default=1.0, help="0 = noiseless signals")
    g.add_argument("--jitter-ms", type=float, default=1.5, help="timestamp jitter std dev")

    o = ap.add_argument_group("output")
    o.add_argument("--output", default="stdout", help="stdout | file:PATH | udp://HOST:PORT | http(s)://URL")
    o.add_argument("--labels", help="write ground-truth labels (scenario + injected faults) to this JSONL file")
    o.add_argument("--realtime", action=argparse.BooleanOptionalAction, default=None,
                   help="pace output at the sampling rate (default: on for udp/http, off otherwise)")
    o.add_argument("--pretty", action="store_true", help="indent JSON (stdout viewing only, breaks JSONL)")

    f = ap.add_argument_group("network faults")
    f.add_argument("--drop-rate", type=float, default=0.0, help="probability a packet is lost")
    f.add_argument("--dup-rate", type=float, default=0.0, help="probability a packet arrives twice")
    f.add_argument("--reorder-rate", type=float, default=0.0, help="probability a packet arrives late")
    f.add_argument("--reorder-depth", type=int, default=3, help="max packets a late packet is overtaken by")
    f.add_argument("--drop-seq", help="exact sequence numbers to drop, e.g. 15,16,40-45")
    f.add_argument("--dup-seq", help="exact sequence numbers to duplicate")
    f.add_argument("--reorder-seq", help="exact sequence numbers to deliver late (by --reorder-depth)")
    f.add_argument("--reboot-at", type=float, help="simulate a device reboot at this sim time (s)")
    f.add_argument("--reboot-gap", type=float, default=2.0, help="seconds offline during the reboot")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    sink = make_sink(args.output)
    cfg = SimConfig(sampling_rate_hz=args.rate, gps_rate_hz=args.gps_rate, device_id=args.device_id,
                    transport=sink.kind, start_time_ms=args.start_time, seed=args.seed,
                    noise_scale=args.noise_scale, timestamp_jitter_ms=args.jitter_ms)
    playlist = load_playlist(args.playlist) if args.playlist else get_playlist(args.scenario)
    sim = Simulator(cfg, playlist, loop=args.loop, reboot_at_s=args.reboot_at, reboot_gap_s=args.reboot_gap)
    fault_seed = None if args.seed is None else args.seed + 1
    injector = FaultInjector(random.Random(fault_seed), args.drop_rate, args.dup_rate, args.reorder_rate,
                             args.reorder_depth, parse_seq_list(args.drop_seq), parse_seq_list(args.dup_seq),
                             parse_seq_list(args.reorder_seq))
    realtime = sink.realtime_default if args.realtime is None else args.realtime
    labels = open(args.labels, "w", encoding="utf-8") if args.labels else None
    indent = 2 if args.pretty else None
    seps = None if args.pretty else (",", ":")

    wall0 = time.monotonic()
    try:
        for packet, truth in sim.run(args.duration):
            if realtime:
                delay = wall0 + truth["sim_time_s"] - time.monotonic()
                if delay > 0:
                    time.sleep(delay)
            line = json.dumps(packet, indent=indent, separators=seps)
            out, tags = injector.process(truth["sequence_number"], line,
                                         apply_explicit=truth["boot_number"] == 0)
            for item in out:
                sink.send(item)
            if labels:
                truth["faults"] = tags
                labels.write(json.dumps(truth, separators=(",", ":")) + "\n")
        for item in injector.flush():
            sink.send(item)
    except KeyboardInterrupt:
        pass
    except BrokenPipeError:                      # e.g. piped into `head`
        sys.stdout = open(os.devnull, "w")
    finally:
        try:
            sink.close()
        except BrokenPipeError:
            pass
        if labels:
            labels.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
