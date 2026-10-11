"""Small geometry helpers on WGS84 coordinates (lat, lon in degrees)."""
import math

EARTH_RADIUS_M = 6_371_000


def distance_m(a, b):
    """Great-circle distance in metres between two (lat, lon) points."""
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(h))


def bearing_deg(a, b):
    """Compass bearing from a to b, 0..360 (0 = north)."""
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    y = math.sin(lon2 - lon1) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(lon2 - lon1)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def turn_angle(bearing_in, bearing_out):
    """Signed turn in degrees: negative = left, positive = right, range -180..180."""
    return (bearing_out - bearing_in + 540) % 360 - 180


class GridIndex:
    """Bucket points into a coarse grid so nearest-point lookups stay fast."""

    def __init__(self, points, cell_deg=0.002):
        self.cell = cell_deg
        self.buckets = {}
        for key, (lat, lon) in points.items():
            self.buckets.setdefault(self._cell(lat, lon), []).append((key, (lat, lon)))

    def _cell(self, lat, lon):
        return int(lat // self.cell), int(lon // self.cell)

    def nearest(self, point, max_m):
        """Return (key, distance_m) of the closest point within max_m, or (None, None)."""
        ci, cj = self._cell(*point)
        reach = max(1, math.ceil(max_m / (self.cell * 111_000)))
        best, best_d = None, None
        for di in range(-reach, reach + 1):
            for dj in range(-reach, reach + 1):
                for key, p in self.buckets.get((ci + di, cj + dj), ()):
                    d = distance_m(point, p)
                    if d <= max_m and (best_d is None or d < best_d):
                        best, best_d = key, d
        return best, best_d
