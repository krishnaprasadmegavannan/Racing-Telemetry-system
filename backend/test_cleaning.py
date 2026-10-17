import math

from processing.cleaning import (
    clean_numeric_value,
    clean_telemetry_packet
)


print("========================================")
print("DATA CLEANING TEST")
print("========================================")


# ----------------------------------------
# TEST 1 — Normal value
# ----------------------------------------

value = 120.5

result = clean_numeric_value(value)

print("\nTEST 1 — Normal value")
print("Input :", value)
print("Output:", result)

assert result == 120.5


# ----------------------------------------
# TEST 2 — NaN
# ----------------------------------------

value = float("nan")

result = clean_numeric_value(value)

print("\nTEST 2 — NaN")
print("Input : NaN")
print("Output:", result)

assert result is None


# ----------------------------------------
# TEST 3 — Positive infinity
# ----------------------------------------

value = float("inf")

result = clean_numeric_value(value)

print("\nTEST 3 — Positive infinity")
print("Input : +Infinity")
print("Output:", result)

assert result is None


# ----------------------------------------
# TEST 4 — Negative infinity
# ----------------------------------------

value = float("-inf")

result = clean_numeric_value(value)

print("\nTEST 4 — Negative infinity")
print("Input : -Infinity")
print("Output:", result)

assert result is None


# ----------------------------------------
# TEST 5 — None
# ----------------------------------------

value = None

result = clean_numeric_value(value)

print("\nTEST 5 — None")
print("Input : None")
print("Output:", result)

assert result is None


# ----------------------------------------
# TEST 6 — Default value
# ----------------------------------------

value = float("nan")

result = clean_numeric_value(
    value,
    default=0.0
)

print("\nTEST 6 — Invalid value with default")
print("Input :", value)
print("Output:", result)

assert result == 0.0


# ----------------------------------------
# FINAL RESULT
# ----------------------------------------

print("\n========================================")
print("ALL CLEANING TESTS PASSED")
print("========================================")