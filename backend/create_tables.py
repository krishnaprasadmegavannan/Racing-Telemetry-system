from storage.database import initialize_database

print("Creating / upgrading Apex-01 database...")
initialize_database()
print("DATABASE READY")
print("Tables: raw_telemetry, processed_telemetry, sessions, laps, sectors, events, alerts")
