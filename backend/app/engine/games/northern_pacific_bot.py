"""
NPC Bot AI for Northern Pacific.

Bots are identified by usernames starting with "Bot_".
Each bot has a configurable archetype that biases its decisions.
"""

import random
from typing import List, Dict, Optional, Tuple

# NP graph — cities and their connections
NP_GRAPH = {
    "StPaul":       ["Duluth", "Fargo", "Aberdeen", "SiouxFalls"],
    "Duluth":       ["GrandForks", "Fargo"],
    "GrandForks":   ["Fargo"],
    "Fargo":        ["Minot", "Bismarck", "Aberdeen"],
    "SiouxFalls":   ["Aberdeen", "RapidCity"],
    "Aberdeen":     ["Bismarck", "RapidCity"],
    "Minot":        ["Glasgow", "Bismarck"],
    "Bismarck":     ["Terry"],
    "RapidCity":    ["Terry", "Billings", "Casper"],
    "Terry":        ["Glasgow", "GreatFalls", "Billings"],
    "Glasgow":      ["Chinook", "Terry"],
    "Casper":       ["Billings", "Butte"],
    "Billings":     ["GreatFalls", "Butte"],
    "Chinook":      ["Shelby", "GreatFalls"],
    "Shelby":       ["BonnersFerry", "GreatFalls"],
    "GreatFalls":   ["Lewiston", "Butte"],
    "Butte":        ["Lewiston"],
    "Lewiston":     ["Spokane", "Richland"],
    "BonnersFerry": ["Oroville", "Spokane", "Lewiston"],
    "Oroville":     ["Vancouver", "Spokane"],
    "Spokane":      ["Richland"],
    "Vancouver":    ["Seattle", "Portland"],
    "Richland":     ["Seattle", "Portland"],
    "Seattle":      [],
    "Portland":     [],
}

# Centrality score: how many connections each city has
CENTRALITY: Dict[str, int] = {c: len(n) for c, n in NP_GRAPH.items()}

# Regions (West-ish to East-ish)
REGION_ORDER = [
    "Vancouver", "Seattle", "Portland",
    "Oroville", "Spokane", "Richland",
    "BonnersFerry", "Shelby", "Chinook", "GreatFalls",
    "Lewiston", "Butte", "Glasgow",
    "Terry", "Billings", "Casper",
    "RapidCity", "Bismarck", "Minot",
    "Aberdeen", "SiouxFalls", "Fargo",
    "GrandForks", "Duluth", "StPaul",
]


def _bfs_distance(start: str, target: str) -> int:
    """BFS shortest path distance between two cities."""
    if start == target:
        return 0
    visited = {start}
    queue = [(start, 0)]
    while queue:
        city, dist = queue.pop(0)
        for neighbor in NP_GRAPH.get(city, []):
            if neighbor == target:
                return dist + 1
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, dist + 1))
    return 999


def _reachable_cities(from_city: str) -> List[str]:
    """All cities reachable from a given city."""
    visited = set()
    queue = [from_city]
    while queue:
        city = queue.pop(0)
        if city in visited:
            continue
        visited.add(city)
        for neighbor in NP_GRAPH.get(city, []):
            if neighbor not in visited:
                queue.append(neighbor)
    return list(visited)


def pick_invest(
    bot_name: str,
    train_pos: str,
    investments: Dict[str, str],
    all_player_ids: List[str],
) -> Optional[str]:
    """
    Decide which city to invest in.
    Returns None if no good target.
    """
    available = [c for c in NP_GRAPH if c not in investments and c != "StPaul"]
    if not available:
        return None

    # Cities already invested by this bot
    my_cities = {c for c, owner in investments.items() if owner == bot_name}

    # Score each available city
    def score(city: str) -> float:
        s = 0.0

        # Centrality bonus: more connections = more likely train visits
        s += CENTRALITY.get(city, 0) * 3

        # Distance from train: prefer closer for early payout
        dist = _bfs_distance(train_pos, city)
        if dist < 10:
            s += (10 - dist) * 2

        # Avoid cities very close to train if they're too obvious
        if dist <= 1:
            s -= 5

        # Prefer cities on paths toward Seattle/Portland (westward)
        # Cities further west (lower index in REGION_ORDER) get bonus
        west_idx = REGION_ORDER.index(city) if city in REGION_ORDER else 99
        s += (len(REGION_ORDER) - west_idx) * 0.5

        # Synergy: prefer cities near our existing investments
        for mc in my_cities:
            d = _bfs_distance(city, mc)
            if d < 4:
                s += (4 - d) * 2

        # Blocking: extra value for cities near opponent investments
        for opp_city, owner in investments.items():
            if owner != bot_name:
                d = _bfs_distance(city, opp_city)
                if d < 3:
                    s += (3 - d) * 1.5

        # Random jitter for variety
        s += random.uniform(-3, 3)

        return s

    scored = [(c, score(c)) for c in available]
    scored.sort(key=lambda x: -x[1])

    # Return top choice
    return scored[0][0]


def pick_move(
    bot_name: str,
    train_pos: str,
    investments: Dict[str, str],
    player_ids: List[str],
) -> Optional[str]:
    """
    Decide where to move the train.
    Returns a connected city, or None to pass (not applicable in NP).
    Raises if no valid moves.
    """
    options = NP_GRAPH.get(train_pos, [])
    if not options:
        return None

    # My invested cities
    my_cities = {c for c, owner in investments.items() if owner == bot_name}

    # Opponent investments
    opp_cities = {c for c, owner in investments.items() if owner != bot_name}

    def score(city: str) -> float:
        s = 0.0

        # Major bonus: moving to a city I own pays out
        if city in my_cities:
            s += 20

        # Bonus for moving closer to my cities
        for mc in my_cities:
            dist = _bfs_distance(city, mc)
            if dist < 5:
                s += (5 - dist) * 2

        # Prefer moving to unclaimed cities over opponent cities
        if city in opp_cities:
            s -= 3  # Still OK, but less ideal — gives opponent payout
        else:
            s += 2  # Unclaimed is better

        # Avoid moving toward terminals too fast (end game early)
        if city in ("Seattle", "Portland"):
            s -= 8

        # Prefer high-centrality cities
        s += CENTRALITY.get(city, 0) * 1.5

        # Random jitter
        s += random.uniform(-2, 2)

        return s

    scored = [(c, score(c)) for c in options]
    scored.sort(key=lambda x: -x[1])
    return scored[0][0]


def decide_move(
    bot_player_id: str,
    bot_username: str,
    state_dict: dict,
) -> Tuple[str, dict]:
    """
    Given the current game state (as dict from to_dict()),
    decide what action to take.
    Returns (action_type, payload).
    """
    train_pos = state_dict.get("train_pos", "StPaul")
    investments = state_dict.get("investments", {})

    # Determine all player IDs from balances
    balances = state_dict.get("balances", {})
    player_ids = list(balances.keys())

    # Simple heuristic: if we don't have many investments, invest
    my_invest_count = sum(
        1 for c, owner in investments.items() if owner == bot_player_id
    )
    total_investments = len(investments)
    total_cities = len([c for c in NP_GRAPH if c != "StPaul"])

    # Bias toward investing until about half the cities are claimed
    invest_bias = 0.6 - (total_investments / total_cities) * 0.3
    invest_bias -= my_invest_count * 0.05  # Less eager after each investment

    if random.random() < invest_bias and total_investments < total_cities:
        city = pick_invest(bot_player_id, train_pos, investments, player_ids)
        if city:
            return ("invest", {"city": city})

    # Otherwise move the train
    target = pick_move(bot_player_id, train_pos, investments, player_ids)
    if target:
        return ("move_train", {"city": target})

    # Fallback: invest in anything
    fallback_city = pick_invest(bot_player_id, train_pos, investments, player_ids)
    if fallback_city:
        return ("invest", {"city": fallback_city})

    return ("move_train", {"city": NP_GRAPH[train_pos][0]})
