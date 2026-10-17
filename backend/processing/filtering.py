from collections import deque


class MovingAverageFilter:
    """
    Simple moving-average filter for telemetry signals.

    Keeps the most recent values and returns their average.

    Example:
        window_size = 3

        Input:  10, 20, 30
        Output: 20
    """

    def __init__(self, window_size: int = 3):
        if window_size <= 0:
            raise ValueError("Window size must be greater than zero.")

        self.window_size = window_size
        self.values = deque(maxlen=window_size)

    def update(self, value: float) -> float:
        """
        Add a new value and return the filtered value.
        """

        self.values.append(value)

        return sum(self.values) / len(self.values)

    def reset(self):
        """
        Clear all stored samples.
        """

        self.values.clear()


def moving_average(
    values: list[float],
    window_size: int = 3
) -> list[float]:
    """
    Apply a moving-average filter to a complete list
    of telemetry values.

    The initial samples use the values available so far.

    Example:
        values = [10, 20, 30]
        window_size = 3

        result = [10, 15, 20]
    """

    if window_size <= 0:
        raise ValueError("Window size must be greater than zero.")

    if not values:
        return []

    filtered = []
    window = deque(maxlen=window_size)

    for value in values:
        window.append(value)

        average = sum(window) / len(window)

        filtered.append(average)

    return filtered