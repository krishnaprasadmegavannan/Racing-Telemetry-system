import math


def haversine_m(lat1, lon1, lat2, lon2):
    radius = 6_371_000.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


class LapDetector:
    """Generic simulated-track detector using a GPS start/finish point."""

    def __init__(self, start_latitude=None, start_longitude=None, radius_m=30.0):
        self.start_latitude = start_latitude
        self.start_longitude = start_longitude
        self.radius_m = radius_m
        self.was_away = False
        self.lap_start_timestamp = None
        self.lap_number = 0

    def update(self, latitude, longitude, timestamp):
        if self.start_latitude is None:
            self.start_latitude = latitude
            self.start_longitude = longitude
            self.lap_start_timestamp = timestamp
            return None

        distance = haversine_m(self.start_latitude, self.start_longitude, latitude, longitude)

        if distance > self.radius_m:
            self.was_away = True

        if self.was_away and distance <= self.radius_m and self.lap_start_timestamp is not None:
            self.lap_number += 1
            result = {
                "lap_number": self.lap_number,
                "start_timestamp": self.lap_start_timestamp,
                "end_timestamp": timestamp,
                "lap_time": timestamp - self.lap_start_timestamp,
            }
            self.lap_start_timestamp = timestamp
            self.was_away = False
            return result

        return None


def split_into_three_sectors(start_timestamp, end_timestamp):
    total = end_timestamp - start_timestamp
    sector = total / 3.0
    return [
        (start_timestamp + i * sector, start_timestamp + (i + 1) * sector, sector)
        for i in range(3)
    ]
