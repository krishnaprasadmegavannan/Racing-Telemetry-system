from processing.filtering import (
    MovingAverageFilter,
    moving_average
)


print("========================================")
print("DATA FILTERING TEST")
print("========================================")


# ----------------------------------------
# TEST 1 — Moving average
# ----------------------------------------

values = [10, 20, 30, 40, 50]

result = moving_average(
    values,
    window_size=3
)

print("\nTEST 1 — Moving average")
print("Input :", values)
print("Output:", result)

expected = [10.0, 15.0, 20.0, 30.0, 40.0]

assert result == expected


# ----------------------------------------
# TEST 2 — Streaming filter
# ----------------------------------------

filter_ = MovingAverageFilter(window_size=3)

stream_values = [10, 20, 30, 40, 50]

stream_result = []

for value in stream_values:
    stream_result.append(
        filter_.update(value)
    )

print("\nTEST 2 — Streaming moving average")
print("Input :", stream_values)
print("Output:", stream_result)

assert stream_result == expected


# ----------------------------------------
# TEST 3 — Reset
# ----------------------------------------

filter_.reset()

result_after_reset = filter_.update(100)

print("\nTEST 3 — Filter reset")
print("Input :", 100)
print("Output:", result_after_reset)

assert result_after_reset == 100.0


# ----------------------------------------
# TEST 4 — Empty list
# ----------------------------------------

result = moving_average([])

print("\nTEST 4 — Empty input")
print("Output:", result)

assert result == []


# ----------------------------------------
# TEST 5 — Invalid window
# ----------------------------------------

try:
    MovingAverageFilter(window_size=0)

    raise AssertionError(
        "Invalid window size was accepted."
    )

except ValueError:
    print("\nTEST 5 — Invalid window size")
    print("Correctly rejected.")


# ----------------------------------------
# FINAL RESULT
# ----------------------------------------

print("\n========================================")
print("ALL FILTERING TESTS PASSED")
print("========================================")