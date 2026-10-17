"""Reference checker: reads a JSONL telemetry stream (file or stdin) and reports, per boot,
lost, duplicated and out-of-order packets. Person 2 can use it as a test oracle for the backend.

    python tools/stream_checker.py run.jsonl
    python -m telemetry_sim --drop-rate 0.02 | python tools/stream_checker.py -
    python tools/stream_checker.py run.jsonl --schema schema/telemetry.schema.json
"""
from __future__ import annotations

import argparse
import json
import sys


def check(lines, validator=None) -> dict:
    boots: dict[str, dict] = {}
    boot_order: list[str] = []
    invalid = 0
    for line in lines:
        line = line.strip()
        if not line:
            continue
        pkt = json.loads(line)
        if validator is not None and not validator.is_valid(pkt):
            invalid += 1
        md = pkt["metadata"]
        boot = md["transmission_information"]["boot_id"]
        seq = md["sequence_number"]
        st = boots.get(boot)
        if st is None:
            st = boots[boot] = {"seen": set(), "max": 0, "received": 0, "duplicates": [], "late": []}
            boot_order.append(boot)
        st["received"] += 1
        if seq in st["seen"]:
            st["duplicates"].append(seq)
        else:
            if seq < st["max"]:
                st["late"].append(seq)
            st["seen"].add(seq)
            st["max"] = max(st["max"], seq)

    report = {"boots": [], "invalid_packets": invalid}
    for boot in boot_order:
        st = boots[boot]
        first = min(st["seen"])
        missing = sorted(set(range(first, st["max"] + 1)) - st["seen"])
        report["boots"].append({
            "boot_id": boot, "first_seq": first, "last_seq": st["max"], "received": st["received"],
            "unique": len(st["seen"]), "missing": missing, "duplicates": sorted(st["duplicates"]),
            "out_of_order": sorted(st["late"]),
        })
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", help="JSONL file, or - for stdin")
    ap.add_argument("--schema", help="validate every packet against this JSON Schema (needs jsonschema)")
    ap.add_argument("--json", action="store_true", help="print the full report as JSON")
    args = ap.parse_args()
    validator = None
    if args.schema:
        import jsonschema
        with open(args.schema, encoding="utf-8") as fh:
            validator = jsonschema.Draft202012Validator(json.load(fh))
    fh = sys.stdin if args.path == "-" else open(args.path, encoding="utf-8")
    report = check(fh, validator)
    if args.json:
        print(json.dumps(report, indent=2))
        return 0
    for b in report["boots"]:
        print(f"boot {b['boot_id']}: seq {b['first_seq']}..{b['last_seq']}, received {b['received']} "
              f"({b['unique']} unique)")
        print(f"  missing      ({len(b['missing'])}): {b['missing'][:20]}{' ...' if len(b['missing']) > 20 else ''}")
        print(f"  duplicates   ({len(b['duplicates'])}): {b['duplicates'][:20]}")
        print(f"  out of order ({len(b['out_of_order'])}): {b['out_of_order'][:20]}")
    if len(report["boots"]) > 1:
        print(f"{len(report['boots']) - 1} reboot(s) detected (sequence restarted under a new boot_id)")
    if args.schema:
        print(f"schema-invalid packets: {report['invalid_packets']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
