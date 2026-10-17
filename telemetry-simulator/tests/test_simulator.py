"""Run with:  python -m unittest discover -s tests -v   (from the project root)"""
import json
import os
import random
import sys
import unittest
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

from telemetry_sim import FaultInjector, SimConfig, Simulator, get_playlist  # noqa: E402
from stream_checker import check  # noqa: E402

try:
    import jsonschema
except ImportError:  # schema test is skipped if jsonschema isn't installed
    jsonschema = None

START = 1_759_651_200_000


def run(scenario="full", seed=7, **kw):
    cfg = SimConfig(seed=seed, start_time_ms=START, **kw)
    return list(Simulator(cfg, get_playlist(scenario)).run())


class TestSimulator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = run()
        cls.by = defaultdict(list)
        for pkt, truth in cls.rows:
            cls.by[truth["scenario"]].append(pkt)

    @unittest.skipIf(jsonschema is None, "jsonschema not installed")
    def test_every_packet_matches_schema(self):
        with open(os.path.join(ROOT, "schema", "telemetry.schema.json"), encoding="utf-8") as fh:
            validator = jsonschema.Draft202012Validator(json.load(fh))
        for pkt, _ in self.rows:
            errors = list(validator.iter_errors(pkt))
            self.assertFalse(errors, errors[:1])

    def test_sequence_and_timestamps(self):
        seqs = [p["metadata"]["sequence_number"] for p, _ in self.rows]
        self.assertEqual(seqs, list(range(1, len(seqs) + 1)))
        ts = [p["metadata"]["timestamp"] for p, _ in self.rows]
        self.assertTrue(all(b > a for a, b in zip(ts, ts[1:])))
        self.assertAlmostEqual((ts[-1] - ts[0]) / (len(ts) - 1), 100, delta=1)  # 10 Hz

    def test_all_scenarios_present(self):
        for name in ("normal_driving", "acceleration", "braking", "cornering", "hard_corner",
                     "wheel_slip", "gps_loss", "high_temperature", "low_battery"):
            self.assertIn(name, self.by)

    def test_braking_decelerates(self):
        self.assertLess(min(p["imu"]["ax"] for p in self.by["braking"]), -7.0)
        self.assertGreater(max(p["vehicle"]["brake_pressure"] for p in self.by["braking"]), 60)

    def test_hard_corner_exceeds_normal_cornering(self):
        self.assertGreater(max(p["imu"]["ay"] for p in self.by["hard_corner"]), 7.0)
        self.assertLess(max(p["imu"]["ay"] for p in self.by["cornering"]), 4.5)

    def test_wheel_slip_driven_wheel_faster(self):
        ratio = max(p["wheel_speeds"]["front_left"] / max(p["wheel_speeds"]["rear_left"], 1)
                    for p in self.by["wheel_slip"])
        self.assertGreater(ratio, 1.5)

    def test_gps_loss_uses_null_not_zero(self):
        lost = [p for p in self.by["gps_loss"] if p["gps"]["fix_status"] == "NO_FIX"]
        self.assertGreater(len(lost), 100)
        for p in lost:
            self.assertIsNone(p["gps"]["latitude"])
            self.assertIn("GPS_NO_FIX", p["metadata"]["status_error_information"]["error_codes"])

    def test_high_temperature_flags_error(self):
        last = self.by["high_temperature"][-1]
        self.assertGreater(last["temperature"]["coolant_temperature"], 112)
        self.assertEqual(last["metadata"]["status_error_information"]["status"], "ERROR")

    def test_low_battery_flags(self):
        last = self.by["low_battery"][-1]
        self.assertLess(last["vehicle"]["battery_voltage"], 11.6)
        self.assertLess(last["vehicle"]["battery_current"], 0)
        self.assertIn("BATTERY_NOT_CHARGING", last["metadata"]["status_error_information"]["error_codes"])

    def test_seed_is_reproducible(self):
        a = run("braking", seed=3)
        b = run("braking", seed=3)
        self.assertEqual([p for p, _ in a], [p for p, _ in b])

    def test_configurable_rate(self):
        rows = run("acceleration", sampling_rate_hz=50)
        self.assertEqual(rows[0][0]["metadata"]["sampling_rate"], 50)
        self.assertEqual(len(rows), 26 * 50)


class TestFaults(unittest.TestCase):
    def _stream(self, injector, rows):
        out, tags = [], {}
        for pkt, truth in rows:
            line = json.dumps(pkt)
            sent, t = injector.process(truth["sequence_number"], line)
            out.extend(sent)
            tags[truth["sequence_number"]] = t
        out.extend(injector.flush())
        return out, tags

    def test_explicit_faults_detected(self):
        rows = run("braking")
        inj = FaultInjector(random.Random(0), drop_seqs={10, 11, 12}, dup_seqs={20}, reorder_seqs={30},
                            reorder_depth=3)
        out, _ = self._stream(inj, rows)
        rep = check(out)["boots"][0]
        self.assertEqual(rep["missing"], [10, 11, 12])
        self.assertEqual(rep["duplicates"], [20])
        self.assertEqual(rep["out_of_order"], [30])
        order = [json.loads(line)["metadata"]["sequence_number"] for line in out]
        self.assertEqual(order[order.index(29) + 1: order.index(29) + 5], [31, 32, 33, 30])

    def test_duplicate_is_byte_identical(self):
        rows = run("braking")
        out, _ = self._stream(FaultInjector(random.Random(0), dup_seqs={5}), rows)
        dups = [line for line in out if json.loads(line)["metadata"]["sequence_number"] == 5]
        self.assertEqual(len(dups), 2)
        self.assertEqual(dups[0], dups[1])

    def test_random_faults_match_labels(self):
        rows = run("normal_driving")
        inj = FaultInjector(random.Random(1), drop_rate=0.03, dup_rate=0.02, reorder_rate=0.02)
        out, tags = self._stream(inj, rows)
        rep = check(out)["boots"][0]
        dropped = sorted(s for s, t in tags.items() if "dropped" in t)
        # a drop at the very end of the stream can't be detected without a later packet
        self.assertEqual(rep["missing"], [s for s in dropped if s < rep["last_seq"]])
        self.assertEqual(len(rep["duplicates"]), sum("duplicated" in t for t in tags.values()))

    def test_reboot_resets_sequence_with_new_boot_id(self):
        cfg = SimConfig(seed=2, start_time_ms=START)
        rows = list(Simulator(cfg, get_playlist("normal_driving"), reboot_at_s=10).run(20))
        boots = check(json.dumps(p) for p, _ in rows)["boots"]
        self.assertEqual(len(boots), 2)
        self.assertEqual(boots[1]["first_seq"], 1)
        self.assertEqual(boots[0]["missing"] + boots[1]["missing"], [])


if __name__ == "__main__":
    unittest.main()
