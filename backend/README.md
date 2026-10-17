# Apex-01 Backend

Person 2 backend for the simulated motorsport telemetry system.

## Run

From `backend`:

```powershell
.\.venv\Scripts\Activate.ps1
python create_tables.py
uvicorn main:app --reload
```

Open:

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/health`

## Main data flow

JSON telemetry -> Pydantic schema -> engineering validation -> cleaning -> derived metrics -> wheel/event/alert analysis -> SQLite -> REST/WebSocket.

## REST

- `POST /telemetry`
- `GET /telemetry`
- `GET /telemetry/latest`
- `GET /telemetry/history`
- `GET /telemetry/processed/latest`
- `GET /telemetry/processed/history`
- `GET /telemetry/session`
- `POST /telemetry/session/start`
- `POST /telemetry/session/stop`
- `GET /telemetry/laps`
- `GET /telemetry/sectors`
- `GET /telemetry/events`
- `GET /telemetry/alerts`
- `PATCH /telemetry/alerts/{alert_id}/ack`
- `GET /telemetry/export?kind=raw`
- `GET /telemetry/export?kind=processed`

## WebSocket

`ws://127.0.0.1:8000/telemetry/ws`

Every accepted packet broadcasts raw telemetry, processed telemetry, events, alerts and session information.

## Processing implemented

- longitudinal/lateral/vertical acceleration
- resultant acceleration
- yaw rate
- cornering intensity
- braking intensity
- acceleration intensity
- wheel-speed difference
- possible wheel slip
- possible wheel lock
- wheel-speed mismatch
- GPS speed-based acceleration
- event detection
- alert generation
- session/lap/sector persistence

The simulator can later be replaced by the ESP32 without changing the backend telemetry contract.
