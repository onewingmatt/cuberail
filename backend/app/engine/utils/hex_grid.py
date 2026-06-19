"""
Hex grid geometry utilities for flat-top hexagons using axial coordinates (q, r).

Flat-top hex neighbor directions:
  NE: (+1, -1), E: (+1, 0), SE: (0, +1),
  SW: (-1, +1), W: (-1, 0), NW: (0, -1)
"""

from typing import List, Tuple, Set, Dict, Any, Optional

# Directions for flat-top hex grid in axial coords
AXIAL_DIRECTIONS = [
    (1, -1),  # NE
    (1, 0),   # E
    (0, 1),   # SE
    (-1, 1),  # SW
    (-1, 0),  # W
    (0, -1),  # NW
]


def hex_neighbors(q: int, r: int) -> List[Tuple[int, int]]:
    """Return the 6 neighboring hex coordinates."""
    return [(q + dq, r + dr) for dq, dr in AXIAL_DIRECTIONS]


def hex_distance(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    """Axial coordinate distance between two hexes."""
    dq = a[0] - b[0]
    dr = a[1] - b[1]
    return max(abs(dq), abs(dr), abs(dq + dr))


def hex_to_pixel(q: int, r: int, size: float) -> Tuple[float, float]:
    """
    Convert axial hex coordinates to pixel center for flat-top hex.
    size = distance from center to vertex.
    """
    x = size * (3.0 / 2.0 * q)
    y = size * (3.0 ** 0.5 / 2.0 * q + 3.0 ** 0.5 * r)
    return (x, y)


def pixel_to_hex(px: float, py: float, size: float) -> Tuple[int, int]:
    """
    Convert pixel coordinates to the nearest axial hex coordinates.
    Uses the standard fractional-axial rounding method.
    """
    q = (2.0 / 3.0 * px) / size
    r = (-1.0 / 3.0 * px + 3.0 ** 0.5 / 3.0 * py) / size
    return _hex_round(q, r)


def _hex_round(q_frac: float, r_frac: float) -> Tuple[int, int]:
    """Round fractional axial coordinates to integer hex coordinates."""
    s_frac = -q_frac - r_frac
    qi = round(q_frac)
    ri = round(r_frac)
    si = round(s_frac)
    q_diff = abs(qi - q_frac)
    r_diff = abs(ri - r_frac)
    s_diff = abs(si - s_frac)
    if q_diff > r_diff and q_diff > s_diff:
        qi = -ri - si
    elif r_diff > s_diff:
        ri = -qi - si
    return (qi, ri)


def hex_corners(q: int, r: int, size: float) -> List[Tuple[float, float]]:
    """
    Return the 6 corner points of a flat-top hexagon centered at (cx, cy).
    Used for SVG rendering.
    """
    cx, cy = hex_to_pixel(q, r, size)
    corners = []
    for i in range(6):
        angle_deg = 60 * i
        angle_rad = 3.141592653589793 / 180 * angle_deg
        corners.append((
            cx + size * __import__('math').cos(angle_rad),
            cy + size * __import__('math').sin(angle_rad),
        ))
    return corners


def hex_corner_path(q: int, r: int, size: float) -> str:
    """Return SVG path 'd' string for a flat-top hexagon."""
    corners = hex_corners(q, r, size)
    points = [f"{x},{y}" for x, y in corners]
    return "M " + " L ".join(points) + " Z"


def hexes_in_range(center: Tuple[int, int], distance: int) -> Set[Tuple[int, int]]:
    """Return all hex coordinates within the given distance of center."""
    results = set()
    q0, r0 = center
    for dq in range(-distance, distance + 1):
        for dr in range(max(-distance, -dq - distance), min(distance, -dq + distance) + 1):
            results.add((q0 + dq, r0 + dr))
    return results


def is_adjacent(a: Tuple[int, int], b: Tuple[int, int]) -> bool:
    """Check if two hexes are adjacent."""
    return hex_distance(a, b) == 1


def hex_line(start: Tuple[int, int], end: Tuple[int, int]) -> List[Tuple[int, int]]:
    """
    Return hex coordinates along a straight line from start to end.
    Uses Bresenham-style line on hex grid.
    """
    dist = hex_distance(start, end)
    results = []
    for i in range(dist + 1):
        t = i / max(dist, 1)
        q_frac = start[0] + (end[0] - start[0]) * t
        r_frac = start[1] + (end[1] - start[1]) * t
        results.append(_hex_round(q_frac, r_frac))
    return results


class HexGrid:
    """
    Wraps a hex map and provides lookup and validation methods.
    """

    def __init__(self, hexes: Dict[str, Any], berlin_approaches: List[Dict] = None,
                 terrain_costs: Dict[str, int] = None):
        self._hexes = hexes
        self._berlin_approaches = set()
        if berlin_approaches:
            for ba in berlin_approaches:
                self._berlin_approaches.add((ba["q"], ba["r"]))
        self._terrain_costs = terrain_costs or {
            "plains": 2, "hills": 3, "mountains": 4,
            "berlin_approach": 2, "urban": 2, "water": 999
        }

    def get_hex(self, q: int, r: int) -> Optional[Dict]:
        """Get hex data for a coordinate. Returns None for out-of-bounds."""
        key = f"{q},{r}"
        return self._hexes.get(key)

    def get_terrain(self, q: int, r: int) -> str:
        """Get terrain type for a hex. Returns 'water' for out-of-bounds."""
        h = self.get_hex(q, r)
        return h["terrain"] if h else "water"

    def get_cost(self, q: int, r: int) -> int:
        """Get base terrain cost for a hex."""
        return self._terrain_costs.get(self.get_terrain(q, r), 999)

    def get_city(self, q: int, r: int) -> Optional[str]:
        """Get city name if hex is urban, None otherwise."""
        h = self.get_hex(q, r)
        return h.get("city") if h else None

    def get_income(self, q: int, r: int) -> int:
        """Get income value for an urban hex. Returns 0 for non-urban."""
        h = self.get_hex(q, r)
        return h.get("income", 0) if h else 0

    def is_urban(self, q: int, r: int) -> bool:
        h = self.get_hex(q, r)
        return h is not None and h.get("terrain") == "urban"

    def is_rural(self, q: int, r: int) -> bool:
        h = self.get_hex(q, r)
        if not h:
            return False
        return h["terrain"] in ("plains", "hills", "mountains")

    def is_berlin_approach(self, q: int, r: int) -> bool:
        return (q, r) in self._berlin_approaches or self.get_terrain(q, r) == "berlin_approach"

    def is_playable(self, q: int, r: int) -> bool:
        """Check if a hex is playable (not water, not out-of-bounds)."""
        return self.get_terrain(q, r) != "water"

    def find_city_hex(self, city_name: str) -> Optional[Tuple[int, int]]:
        """Find hex coordinates for a named city."""
        for key, h in self._hexes.items():
            if h.get("city") == city_name:
                q, r = map(int, key.split(","))
                return (q, r)
        return None
