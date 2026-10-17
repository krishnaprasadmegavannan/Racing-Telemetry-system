from processing.output import ProcessedTelemetry


processed = ProcessedTelemetry(
    resultant_acceleration=13.124785712536415,
    wheel_speed_difference=2.4,
    fastest_wheel="front_right",
    slowest_wheel="rear_left",
    speed_acceleration=2.7777777777777777
)


print("Processed telemetry model: VALID")
print()
print(processed)