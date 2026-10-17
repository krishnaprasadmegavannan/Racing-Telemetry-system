# Vehicle Telemetry Simulator (ESP32 stand-in)

Generates telemetry packets that look and behave like the eventual ESP32 + sensor node, so the
backend can be built and tested before the hardware exists. Packets follow the fixed JSON
contract in `schema/telemetry.schema.json` (schema_version **1.0.0**).

Pure Python 3.10+, standard library only. `jsonschema` is optional (schema checks in tests/tools).

## Quick start

```bash
python -m telemetry_sim --seed 42                          # full scenario, JSON Lines to stdout
python -m telemetry_sim --output file:run.jsonl --labels run.labels.jsonl
python -m telemetry_sim --output udp://127.0.0.1:5005      # paced in real time by default
python -m telemetry_sim --output http://localhost:8000/ingest
python -m telemetry_sim --scenario wheel_slip --rate 50 --pretty
python -m telemetry_sim --loop --output udp://127.0.0.1:5005   # run forever (Ctrl-C to stop)

python -m unittest discover -s tests -v                    # 15 tests
python tools/stream_checker.py run.jsonl --schema schema/telemetry.schema.json
python tools/make_samples.py                               # regenerate samples/
```

## How it works

```
Scenario playlist ─► Driver ─► VehicleModel (physics) ─► Sensors + noise ─► Packet (schema)
                                                                              │
                                     Sink (stdout/file/UDP/HTTP) ◄─ FaultInjector (drop/dup/reorder)
```

All signals come from one shared physical state, so they stay consistent with each other.
Braking shows up at the same moment as negative `ax`, rising `brake_pressure`, a nose-dive
pitch rate on `gy`, falling wheel speeds, falling GPS speed and downshifting RPM. A random
number generator alone can't give the backend that kind of cross-signal consistency to test against.

| Module | Responsibility |
|---|---|
| `config.py` | Vehicle parameters, sensor noise, warning thresholds, schema version |
| `vehicle.py` | Longitudinal/lateral dynamics, tyre slip, gearbox, thermal and 12 V battery models |
| `scenarios.py` | Phases, the default playlist, single-scenario playlists, virtual driver |
| `sensors.py` | GPS receiver (own update rate, fix loss), IMU, packet assembly, device status codes |
| `faults.py` | Packet loss, duplication, reordering |
| `transport.py` | Output sinks |
| `simulator.py` | Timing, timestamps, sequence numbers, reboot simulation |
| `tools/stream_checker.py` | Reference detector for missing/duplicate/out-of-order packets |

## Packet schema (v1.0.0)

One packet = one sample. See `samples/sample_packet.json` for a full example.

| Group | Field | Type | Unit / values |
|---|---|---|---|
| metadata | schema_version | string | `1.0.0` |
| | device_id | string | |
| | timestamp | int | Unix **milliseconds** |
| | sequence_number | int | 1, 2, 3 … per boot |
| | sampling_rate | number | Hz |
| | transmission_information.transport | string | stdout, file, udp, http, mqtt, websocket, serial |
| | transmission_information.boot_id | string | 8 hex chars, new on every power-up |
| | transmission_information.uptime_ms | int | ms since boot |
| | transmission_information.rssi_dbm | int / null | dBm (null on wired links) |
| | status_error_information.status | string | OK, WARNING, ERROR |
| | status_error_information.error_codes | string[] | see below |
| gps | latitude, longitude | number / null | degrees WGS84 |
| | speed | number / null | km/h |
| | altitude | number / null | m |
| | satellite_count | int | |
| | fix_status | string | NO_FIX, 2D_FIX, 3D_FIX |
| imu | ax, ay, az | number | m/s² |
| | gx, gy, gz | number | °/s |
| temperature | coolant_temperature, engine_temperature | number | °C |
| wheel_speeds | front_left, front_right, rear_left, rear_right | number | km/h |
| vehicle | rpm | int | rpm |
| | throttle | number | % (0–100) |
| | brake_pressure | number | bar |
| | battery_voltage | number | V |
| | battery_current | number | A |

### Conventions (part of the contract, not optional)

- **Axes:** ISO 8855 body frame, x forward, y left, z up. `ay > 0` and `gz > 0` in a left turn.
  `gy > 0` = nose pitching down (braking). `gx > 0` = rolling toward the right.
- **Gravity:** the accelerometer reports specific force, as a real MPU-6050/ICM-type sensor does.
  `az ≈ +9.81` at rest on level ground, and `ax` contains `g·sin(slope)` on hills.
- **Battery current:** `+` = charging, `−` = discharging.
- **No GPS fix:** latitude, longitude, speed and altitude are `null`, never `0`.
  On a 2D fix only altitude is `null`.
- **GPS update rate:** GPS fields update at `--gps-rate` (default 5 Hz) and are held between fixes,
  so consecutive packets can carry identical GPS values. That's expected.
- **Timestamp:** Unix ms with ~1.5 ms jitter, strictly increasing within a boot.
- **Sequence number:** starts at 1 on every boot. A reset to 1 under a new `boot_id` is a reboot,
  not reordering.

### Device status codes

| Code | Severity | Condition (defaults in `config.Thresholds`) |
|---|---|---|
| GPS_NO_FIX | WARNING | fix_status = NO_FIX |
| GPS_LOW_SATELLITES | WARNING | fix but < 5 satellites |
| COOLANT_TEMP_HIGH / _CRITICAL | WARNING / ERROR | ≥ 105 °C / ≥ 112 °C |
| ENGINE_TEMP_HIGH / _CRITICAL | WARNING / ERROR | ≥ 115 °C / ≥ 125 °C |
| BATTERY_VOLTAGE_LOW / _CRITICAL | WARNING / ERROR | < 12.0 V / < 11.5 V |
| BATTERY_NOT_CHARGING | WARNING | current < −5 A |
| SENSOR_READ_FAILURE | ERROR | reserved for hardware (not produced by the simulator) |

Codes use hysteresis (2 °C, 0.15 V) so they don't flicker on sensor noise. Things that need
analysis across many packets, like wheel slip, hard cornering and lost packets, are deliberately
**not** flagged by the device. Detecting them is the backend's job.

### Changing the schema

Field names and units are frozen for `1.x`. Adding an optional field means a minor bump (1.1.0)
and the backend must ignore unknown fields. Renaming, removing or changing a unit means a major
bump (2.0.0) agreed by both sides. The schema uses `additionalProperties: false` so accidental
drift fails validation immediately.

## Scenarios

`--scenario full` (default, ~145 s) runs:

| # | Phase | What happens | What the backend should see |
|---|---|---|---|
| 1 | normal_driving | 0 → 50 km/h, gentle weaving | ay ±0.6 m/s², stable temps, 14 V charging |
| 2 | acceleration | 95 % throttle | ax up to ~4 m/s², 50 → ~119 km/h, upshifts |
| 3 | braking | 70 bar until 25 km/h | ax ≈ −8.5 m/s², gy spike, downshifts |
| 4 | cornering | 45 km/h, 3.5 m/s² | ay ≈ 3.5, gz ≈ 25 °/s, inside wheels slower |
| 5 | hard_corner | 50 km/h, 8 m/s² | ay ≈ 8 (0.8 g), gz ≈ 34 °/s |
| 6 | wheel_slip | full throttle on μ = 0.3 | driven front wheel up to ~2× the rear, RPM flare |
| 7 | gps_loss | satellites drop to 0 | NO_FIX, null position, then 2D → 3D recovery |
| 8 | high_temperature | cooling failure | coolant → ~124 °C, engine → ~136 °C, ERROR |
| 9 | low_battery | alternator failure | current ≈ −25 A, voltage 13.9 → ~11.5 V, ERROR |

Lead-in `normal_driving` segments sit between some phases to set the car up (for example slowing
to 15 km/h before the slip test). Single scenarios such as `--scenario braking` include a short
lead-in and tail. Custom sequences come from a JSON file (`--playlist`), see
`samples/custom_playlist_example.json` for the format.

**Time compression:** the overheating and battery-drain faults run 6× and 120× faster than
real life so they fit in 30 s. The *levels* are realistic. The *rates of change* in those two
phases are not, so don't tune rate-of-change alarms on them (see `fault_time_scale` and
`battery_time_scale` in `config.py`).

## Network fault injection

Faults are applied after serialisation, so a duplicate is byte-identical to the original
(same sequence number, same timestamp), exactly like a retransmission.

```bash
# random
python -m telemetry_sim --drop-rate 0.02 --dup-rate 0.01 --reorder-rate 0.01 --reorder-depth 3
# deterministic, for unit tests
python -m telemetry_sim --drop-seq 15,16,40-45 --dup-seq 30 --reorder-seq 50 --reorder-depth 2
# device reboot at t = 60 s, offline for 2 s, sequence restarts at 1 with a new boot_id
python -m telemetry_sim --reboot-at 60
```

`--reorder-seq 50 --reorder-depth 2` delivers …49, 51, 52, 50, 53…. Explicit sequence lists
apply to the first boot only. Fault randomness uses its own seed (`--seed` + 1), so enabling
faults doesn't change any sensor values.

### Ground-truth labels

`--labels FILE` writes one line per *generated* packet, including dropped ones:

```json
{"boot_id":"a3b1799d","boot_number":0,"sequence_number":275,"timestamp":1759651227400,
 "sim_time_s":27.4,"scenario":"acceleration","faults":["dropped"]}
```

The scenario label lives in this sidecar file, not in the packet, because the real ESP32 can't
know which scenario it's in. Putting it in the packet would make the simulator's schema differ
from the hardware's. Use the labels to score backend detection automatically.
`samples/full_run_with_faults.jsonl` plus its `.labels.jsonl` is a ready-made test fixture
(1 % loss, 1 % duplicates, 1 % reordering, one reboot).

## CLI reference

| Option | Default | Meaning |
|---|---|---|
| `--rate` | 10 | packet sampling rate, Hz |
| `--gps-rate` | 5 | GPS update rate, Hz |
| `--scenario` | full | `full` or a single scenario name |
| `--playlist` | — | JSON phase list (overrides `--scenario`) |
| `--duration` | playlist length | seconds to simulate |
| `--loop` | off | repeat the playlist |
| `--seed` | random | reproducible output |
| `--start-time` | now | first timestamp, Unix ms |
| `--device-id` | SIM-ESP32-01 | |
| `--noise-scale` | 1.0 | 0 = noiseless |
| `--jitter-ms` | 1.5 | timestamp jitter std dev |
| `--output` | stdout | `stdout`, `file:PATH`, `udp://HOST:PORT`, `http(s)://URL` |
| `--labels` | — | ground-truth JSONL file |
| `--realtime / --no-realtime` | on for udp/http | pace output at the sampling rate |
| `--pretty` | off | indented JSON for reading (not valid JSONL) |
| `--drop-rate`, `--dup-rate`, `--reorder-rate` | 0 | random fault probabilities |
| `--reorder-depth` | 3 | how many packets can overtake a late one |
| `--drop-seq`, `--dup-seq`, `--reorder-seq` | — | exact sequence numbers, e.g. `10,12,20-25` |
| `--reboot-at`, `--reboot-gap` | —, 2 s | simulated power cycle |

## Model assumptions (change in `config.py`)

A ~1.3 t front-wheel-drive car with a 12 V system, 90 kW, 5-speed gearbox and an automatic
shift strategy. If the target vehicle is an EV or a Formula Student car, adjust
`VehicleParams` and especially the battery model, because a high-voltage pack behaves nothing
like a 12 V lead-acid battery. Start position is an arbitrary configurable point.

## Moving to the ESP32 (deliverable 10)

The firmware must emit the exact same JSON. In particular:

- Keep `sequence_number` as a `uint32` starting at 1 after boot. Generate `boot_id` from
  `esp_random()` at startup.
- Take `timestamp` from an NTP-synced RTC, not from GPS time, or timestamps break during
  GPS loss. `uptime_ms` comes from `esp_timer_get_time()/1000`.
- Send `null` for GPS fields without a fix. ArduinoJson: `doc["gps"]["latitude"] = nullptr`.
- Convert sensor units before sending: MPU-6050 raw → m/s² and °/s; wheel pulses → km/h.
- Rotate the IMU into the ISO 8855 vehicle frame in firmware, based on how the board is mounted.
- Validate a captured hardware stream with `tools/stream_checker.py --schema …` before integration.

## Project layout

```
telemetry_sim/      simulator package
schema/             telemetry.schema.json (the contract)
samples/            sample packets, per-scenario examples, fault fixture + labels
tools/              stream_checker.py, make_samples.py
tests/              unit tests
```
