"""
Track segment definitions for Northern Pacific (official Rio Grande Games rules).

Each track segment has: (segment_id, source_city, target_city, bidirectional_pair_id)
- bidirectional_pair_id: None if unpaired, otherwise shared string matching the other segment
  in the pair. Only one segment of a bidirectional pair may be used per round.
"""

from typing import List, Dict, Tuple, Optional, Set

TRACK_SEGMENTS: List[Tuple[str, str, str, Optional[str]]] = [
    # StPaul spokes
    ("t01", "StPaul", "Duluth", None),
    ("t02", "StPaul", "Fargo", None),
    ("t03", "StPaul", "Aberdeen", None),
    ("t04", "StPaul", "SiouxFalls", None),

    # Duluth
    ("t05", "Duluth", "GrandForks", None),
    ("t06", "Duluth", "Fargo", None),

    # GrandForks
    ("t07", "GrandForks", "Minot", None),
    ("t08", "Fargo", "GrandForks", "bi_fargo_gf"),    # bidirectional
    ("t09", "GrandForks", "Fargo", "bi_fargo_gf"),     # bidirectional (other way)

    # Fargo
    ("t10", "Fargo", "Minot", None),
    ("t11", "Fargo", "Bismarck", None),

    # SiouxFalls
    ("t12", "SiouxFalls", "Aberdeen", None),
    ("t13", "SiouxFalls", "RapidCity", None),

    # Aberdeen
    ("t14", "Aberdeen", "Bismarck", None),
    ("t15", "Aberdeen", "RapidCity", None),

    # Minot
    ("t16", "Minot", "Glasgow", None),
    ("t17", "Minot", "Bismarck", None),

    # Bismarck
    ("t18", "Bismarck", "Terry", None),

    # RapidCity
    ("t19", "RapidCity", "Terry", None),
    ("t20", "RapidCity", "Billings", None),
    ("t21", "RapidCity", "Casper", None),

    # Terry
    ("t22", "Terry", "Glasgow", "bi_terry_glasgow"),   # bidirectional
    ("t23", "Terry", "GreatFalls", None),
    ("t24", "Terry", "Billings", None),

    # Glasgow
    ("t25", "Glasgow", "Chinook", None),
    ("t26", "Glasgow", "Terry", "bi_terry_glasgow"),    # bidirectional (other way)

    # Casper
    ("t27", "Casper", "Billings", None),
    ("t28", "Casper", "Butte", None),

    # Billings
    ("t29", "Billings", "GreatFalls", None),
    ("t30", "Billings", "Butte", None),

    # Chinook
    ("t31", "Chinook", "Shelby", None),
    ("t32", "Chinook", "GreatFalls", None),

    # Shelby
    ("t33", "Shelby", "BonnersFerry", None),
    ("t34", "Shelby", "GreatFalls", None),

    # GreatFalls
    ("t35", "GreatFalls", "Lewiston", None),
    ("t36", "GreatFalls", "Butte", None),

    # Butte
    ("t37", "Butte", "Lewiston", None),

    # Lewiston
    ("t38", "Lewiston", "Spokane", None),
    ("t39", "Lewiston", "Richland", None),

    # BonnersFerry
    ("t40", "BonnersFerry", "Oroville", None),
    ("t41", "BonnersFerry", "Spokane", None),
    ("t42", "BonnersFerry", "Lewiston", None),

    # Oroville
    ("t43", "Oroville", "Vancouver", None),
    ("t44", "Oroville", "Spokane", None),

    # Spokane
    ("t45", "Spokane", "Richland", None),

    # Vancouver
    ("t46", "Vancouver", "Seattle", None),
    ("t47", "Vancouver", "Portland", None),

    # Richland
    ("t48", "Richland", "Seattle", None),
    ("t49", "Richland", "Portland", None),
]

# All unique city names in the graph
ALL_CITIES: List[str] = sorted(list(set(
    city for t in TRACK_SEGMENTS for city in (t[1], t[2])
)))

# Precompute adjacency: city -> list of outgoing segment tuples
_OUTGOING_CACHE: Dict[str, List[Tuple[str, str, Optional[str]]]] = {}

def _build_cache():
    if _OUTGOING_CACHE:
        return
    for t in TRACK_SEGMENTS:
        _OUTGOING_CACHE.setdefault(t[1], []).append((t[2], t[0], t[3]))

def get_outgoing_segments(city: str) -> List[Tuple[str, str, Optional[str]]]:
    """Return list of (target_city, segment_id, bidir_pair_id) from a given city."""
    _build_cache()
    return _OUTGOING_CACHE.get(city, [])


# ---- Graph helpers for the frontend (visual connections) ----

def build_graph_dict() -> Dict[str, List[str]]:
    """
    Build a directed graph dict compatible with the frontend renderer.
    Like NP_GRAPH but includes all edges without duplicates.
    """
    graph: Dict[str, List[str]] = {}
    for t in TRACK_SEGMENTS:
        graph.setdefault(t[1], []).append(t[2])
        graph.setdefault(t[2], [])  # ensure terminals appear
    return graph


def build_segment_positions() -> Dict[str, Tuple[str, str]]:
    """Map segment_id -> (source, target) for frontend rendering."""
    return {t[0]: (t[1], t[2]) for t in TRACK_SEGMENTS}


# ---- Adjacency dict for backward compat (UI) ----

NP_GRAPH = build_graph_dict()
