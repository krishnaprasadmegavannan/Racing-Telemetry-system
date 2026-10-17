import json
from models.telemetry import TelemetryPacket


def parse_packet(payload: str | bytes | dict) -> TelemetryPacket:
    if isinstance(payload, dict):
        data = payload
    else:
        try:
            data = json.loads(payload)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError("Invalid telemetry JSON.") from exc

    return TelemetryPacket.model_validate(data)
