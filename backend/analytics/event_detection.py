def detect_events(packet, processed) -> list[dict]:
    events = []

    if processed.braking_intensity > 2.0:
        events.append({"type": "BRAKING", "severity": "INFO", "description": "Braking event detected."})

    if processed.acceleration_intensity > 2.0:
        events.append({"type": "ACCELERATION", "severity": "INFO", "description": "Acceleration event detected."})

    if processed.cornering_intensity >= 6.0:
        events.append({"type": "CORNERING", "severity": "INFO", "description": "High lateral acceleration detected."})

    if processed.possible_wheel_slip:
        events.append({"type": "WHEEL_SLIP", "severity": "WARNING", "description": "Possible wheel slip detected."})

    if processed.possible_wheel_lock:
        events.append({"type": "WHEEL_LOCK", "severity": "CRITICAL", "description": "Possible wheel lock detected."})

    if processed.wheel_speed_mismatch:
        events.append({"type": "WHEEL_SPEED_MISMATCH", "severity": "WARNING", "description": "Wheel speeds differ significantly."})

    return events
