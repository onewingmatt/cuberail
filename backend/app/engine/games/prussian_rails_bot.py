"""
Prussian Rails bot AI — rule-based opponent.

Handles three decision points:
1. Initial auction bid/pass
2. Round play (build track, auction share, pass)
3. Round auctions (bid/pass on share offerings)

Strategy uses scoring heuristics with random jitter for variety.
"""

import random
from typing import List, Dict, Optional, Tuple, Set

# ─── Constants ───────────────────────────────────────────────────────

# Map terrain keys to their q,r coords for hex grid operations
# We use the hex_grid utilities for pathfinding when available,
# otherwise fall back to simple adjacency checks.


def _hex_neighbors(q: int, r: int) -> List[Tuple[int, int]]:
    """Flat-top axial hex neighbors."""
    return [
        (q + 1, r), (q - 1, r),
        (q, r + 1), (q, r - 1),
        (q + 1, r - 1), (q - 1, r + 1),
    ]


def _is_adjacent(a: Tuple[int, int], b: Tuple[int, int]) -> bool:
    """Check if two hex coordinates are adjacent."""
    return b in _hex_neighbors(a[0], a[1])


def _parse_hex_key(key: str) -> Tuple[int, int]:
    """Parse 'q,r' string to tuple."""
    parts = key.split(",")
    return (int(parts[0]), int(parts[1]))


def _get_company_network(state_dict: dict, company_id: str) -> Set[Tuple[int, int]]:
    """Get all hexes occupied by a company."""
    network: Set[Tuple[int, int]] = set()
    for entry in state_dict.get("board", []):
        hex_key, companies = entry[0], entry[1]
        if company_id in companies:
            network.add(_parse_hex_key(hex_key))
    return network


def _get_buildable_hexes(
    state_dict: dict, company_id: str
) -> List[Tuple[int, int]]:
    """
    Return hexes that this company can build on (adjacent to network,
    playable, not already owned by this company).
    """
    network = _get_company_network(state_dict, company_id)
    if not network:
        return []

    map_data = state_dict.get("map_data", {})
    hexes_data = map_data.get("hexes", {})
    berlin_approaches = {tuple(h.values()) for h in map_data.get("berlin_approach_hexes", [])}

    candidates: Set[Tuple[int, int]] = set()
    for hq, hr in network:
        for nq, nr in _hex_neighbors(hq, hr):
            key = f"{nq},{nr}"
            hex_info = hexes_data.get(key, {})
            terrain = hex_info.get("terrain", "water")
            if terrain == "water":
                continue
            # Don't build on hex already owned by this company
            already_owned = False
            for entry in state_dict.get("board", []):
                if entry[0] == key and company_id in entry[1]:
                    already_owned = True
                    break
            if already_owned:
                continue
            # Berlin approach: only 1 company per approach hex
            if (nq, nr) in berlin_approaches:
                occupied = False
                for entry in state_dict.get("board", []):
                    if entry[0] == key and entry[1]:
                        occupied = True
                        break
                if occupied:
                    continue
            candidates.add((nq, nr))
    return list(candidates)


def _get_terrain_cost(state_dict: dict, q: int, r: int) -> int:
    """Get the base terrain cost for a hex."""
    map_data = state_dict.get("map_data", {})
    hexes = map_data.get("hexes", {})
    terrain_costs = map_data.get("terrain_costs", {})
    hex_info = hexes.get(f"{q},{r}", {})
    terrain = hex_info.get("terrain", "water")
    return terrain_costs.get(terrain, 99)


def _is_city_hex(state_dict: dict, q: int, r: int) -> Optional[str]:
    """Return city name if hex contains a city, else None."""
    map_data = state_dict.get("map_data", {})
    hexes = map_data.get("hexes", {})
    hex_info = hexes.get(f"{q},{r}", {})
    return hex_info.get("city")


def _get_city_income(state_dict: dict, q: int, r: int) -> int:
    """Get income value of a city hex."""
    map_data = state_dict.get("map_data", {})
    hexes = map_data.get("hexes", {})
    hex_info = hexes.get(f"{q},{r}", {})
    return hex_info.get("income", 0)


# ─── Company scoring ─────────────────────────────────────────────────

def _score_company_for_auction(state_dict: dict, company_id: str) -> float:
    """Score a company for initial auction bidding decisions."""
    info = state_dict.get("companies", {}).get(company_id, {})
    if isinstance(info, dict):
        income = state_dict.get("company_income", {}).get(company_id, 0)
        track = info.get("track_remaining", 10)
        ability = state_dict.get("company_ability", {}).get(company_id, "")
    else:
        income = getattr(info, "start_income", getattr(info, "company_income", 0))
        track = getattr(info, "track_remaining", getattr(info, "max_track", 10))
        ability = state_dict.get("company_ability", {}).get(company_id, "")

    # Base score from income and track count
    score = income * 3 + track * 0.3

    # Ability bonuses
    ability_bonus = {
        "build_4": 3.0,       # More building flexibility
        "discount_1": 2.5,    # Cost efficiency
        "free_rural": 1.5,    # Cost savings
        "double_best_income": 2.0,  # Higher potential payouts
        "no_city_penalty": 1.0,
        "connect_both": 1.0,
        "build_1_2": -1.0,    # Restrictive
        "max_spend_5": -0.5,  # Restrictive
    }
    score += ability_bonus.get(ability, 0)

    # Centrality: prefer companies whose home is near many cities
    home = state_dict.get("company_home", {}).get(company_id, "")
    if home:
        map_data = state_dict.get("map_data", {})
        hexes = map_data.get("hexes", {})
        # Find home hex
        home_hex = None
        for key, h in hexes.items():
            if h.get("city") == home:
                home_hex = _parse_hex_key(key)
                break
        if home_hex:
            # Count cities within 3 hexes
            nearby = 0
            hq, hr = home_hex
            for dq in range(-3, 4):
                for dr in range(-3, 4):
                    nq, nr = hq + dq, hr + dr
                    neighbor_key = f"{nq},{nr}"
                    neighbor = hexes.get(neighbor_key, {})
                    if neighbor.get("city") and neighbor.get("city") != home:
                        nearby += 1
            score += nearby * 0.8

    return score


# ─── Build scoring ───────────────────────────────────────────────────

def _score_hex_for_build(
    state_dict: dict,
    company_id: str,
    hex_coord: Tuple[int, int],
    player_id: str,
) -> float:
    """Score a candidate hex for building. Higher = better."""
    q, r = hex_coord
    score = 0.0

    # Prefer low-cost terrain (efficiency)
    cost = _get_terrain_cost(state_dict, q, r)
    score += (4 - cost) * 1.5  # plains=3, hills=1.5, mountains=0

    # Prefer hexes that lead toward cities (income gains)
    city = _is_city_hex(state_dict, q, r)
    if city:
        income = _get_city_income(state_dict, q, r)
        score += income * 5.0

    # Prefer hexes adjacent to other companies (dividend triggers)
    for nq, nr in _hex_neighbors(q, r):
        nk = f"{nq},{nr}"
        for entry in state_dict.get("board", []):
            if entry[0] == nk:
                other_companies = [c for c in entry[1] if c != company_id]
                if other_companies:
                    # Don't double-count pairs already connected
                    pair = tuple(sorted([company_id, other_companies[0]]))
                    if pair not in state_dict.get("connected_pairs", set()):
                        score += 8.0  # Big bonus for new connections
                    break

    # Prefer moving toward Berlin (high value)
    map_data = state_dict.get("map_data", {})
    berlin_hexes = [tuple(h.values()) for h in map_data.get("berlin_approach_hexes", [])]
    berlin_center = (9, 7)  # Berlin itself
    if berlin_hexes:
        # Average position of approach hexes
        avg_q = sum(h[0] for h in berlin_hexes) / len(berlin_hexes)
        avg_r = sum(h[1] for h in berlin_hexes) / len(berlin_hexes)
    else:
        avg_q, avg_r = berlin_center

    # Get company's closest hex to Berlin
    network = _get_company_network(state_dict, company_id)
    if network:
        closest_dist = min(
            abs(hq - avg_q) + abs(hr - avg_r) for hq, hr in network
        )
        candidate_dist = abs(q - avg_q) + abs(r - avg_r)
        if candidate_dist < closest_dist:
            score += (closest_dist - candidate_dist) * 1.5

    # Random jitter for variety
    score += random.uniform(-1.5, 1.5)

    return score


def _find_best_build(
    state_dict: dict, company_id: str, player_id: str
) -> Optional[Tuple[List[List[int]], int]]:
    """
    Find the best build action for a company.
    Returns (hex_path, total_cost) or None.
    """
    ability = state_dict.get("company_ability", {}).get(company_id, "")
    treasury = state_dict.get("company_treasury", {}).get(company_id, 0)
    track_remaining = state_dict.get("companies", {}).get(company_id, {})
    if isinstance(track_remaining, dict):
        remaining = track_remaining.get("track_remaining", 0)
    else:
        remaining = getattr(track_remaining, "track_remaining", 0)

    if treasury <= 0 or remaining <= 0:
        return None

    # Max cubes based on ability
    max_cubes = 3
    if ability == "build_4":
        max_cubes = 4
    elif ability == "build_1_2":
        max_cubes = 2
    max_cubes = min(max_cubes, remaining)

    buildable = _get_buildable_hexes(state_dict, company_id)
    if not buildable:
        return None

    # Score each candidate hex
    scored = [(h, _score_hex_for_build(state_dict, company_id, h, player_id)) for h in buildable]
    scored.sort(key=lambda x: -x[1])

    # Try to build a path of up to max_cubes hexes
    path = []
    total_cost = 0
    free_rural_used = False
    used: Set[Tuple[int, int]] = set()

    for hex_coord, _ in scored:
        if len(path) >= max_cubes:
            break
        if hex_coord in used:
            continue

        q, r = hex_coord
        cost = _get_terrain_cost(state_dict, q, r)

        # Apply ability discounts
        if ability == "discount_1":
            cost = max(1, cost - 1)
        if ability == "free_rural" and not free_rural_used:
            terrain = state_dict.get("map_data", {}).get("hexes", {}).get(f"{q},{r}", {}).get("terrain", "")
            if terrain in ("plains", "hills", "mountains"):
                cost = 0
                free_rural_used = True

        # City stacking penalty
        city = _is_city_hex(state_dict, q, r)
        if city and ability != "no_city_penalty":
            key = f"{q},{r}"
            for entry in state_dict.get("board", []):
                if entry[0] == key:
                    cost += len(entry[1])
                    break

        # Check adjacency to path so far
        if path:
            last = path[-1]
            if not _is_adjacent(tuple(last), hex_coord):
                continue

        # Check treasury + max_spend
        if ability == "max_spend_5" and total_cost + cost > 5:
            continue
        if total_cost + cost > treasury:
            break

        path.append([q, r])
        total_cost += cost
        used.add(hex_coord)

    if not path:
        return None
    return (path, total_cost)


# ─── Main decision function ──────────────────────────────────────────

def decide_move(
    bot_player_id: str,
    bot_username: str,
    state_dict: dict,
) -> Tuple[str, dict]:
    """
    Decide what action to take based on game state.

    Returns (action_type, payload).
    """
    phase = state_dict.get("phase", "")
    auction_state = state_dict.get("auction_state")

    # ── Initial auction ──────────────────────────────────────────
    if phase == "auction" and state_dict.get("round_phase") is None:
        if not auction_state:
            return ("pass", {})

        company_id = auction_state.get("item")
        current_bid = auction_state.get("current_bid", 0)
        bidders = auction_state.get("bidders", [])

        if bot_player_id not in bidders:
            return ("pass", {})

        cash = state_dict.get("player_cash", {}).get(bot_player_id, 0)
        company_score = _score_company_for_auction(state_dict, company_id)

        # Max bid: higher for better companies, but don't overpay
        max_bid = min(cash, int(4 + company_score * 1.2))

        if cash >= current_bid + 1 and current_bid + 1 <= max_bid:
            bid = current_bid + 1
            # Occasionally bid more aggressively
            if random.random() < 0.3:
                bid = min(current_bid + random.randint(1, 3), max_bid)
                bid = max(bid, current_bid + 1)
            return ("bid", {"bid": bid})
        else:
            return ("pass", {})

    # ── Round auction ────────────────────────────────────────────
    if phase == "round" and auction_state:
        company_id = auction_state.get("item")
        current_bid = auction_state.get("current_bid", 0)
        bidders = auction_state.get("bidders", [])

        if bot_player_id not in bidders:
            return ("pass", {})

        cash = state_dict.get("player_cash", {}).get(bot_player_id, 0)
        income = state_dict.get("company_income", {}).get(company_id, 0)
        treasury = state_dict.get("company_treasury", {}).get(company_id, 0)

        # Value = income potential + treasury health
        value = income * 2 + treasury * 0.5
        max_bid = min(cash, int(2 + value))

        if cash >= current_bid + 1 and current_bid + 1 <= max_bid:
            return ("bid", {"bid": current_bid + 1})
        else:
            return ("pass", {})

    # ── Round play ───────────────────────────────────────────────
    if phase == "round" and not auction_state:
        # Get companies the bot owns shares in
        shares = state_dict.get("shares", {}).get(bot_player_id, {})
        if not shares:
            return ("pass", {})

        # Score each company for building potential
        company_scores = []
        for company_id in shares:
            build = _find_best_build(state_dict, company_id, bot_player_id)
            if build:
                path, cost = build
                # Score based on path length, cost efficiency, strategic value
                score = len(path) * 3.0 - cost * 0.5
                # Bonus for companies with high income
                income = state_dict.get("company_income", {}).get(company_id, 0)
                score += income * 1.0
                company_scores.append((score, company_id, path))

        if company_scores:
            company_scores.sort(key=lambda x: -x[0])
            _, company_id, path = company_scores[0]
            return ("build_track", {"company": company_id, "hex_path": path})

        # No good builds — consider auctioning a share
        cash = state_dict.get("player_cash", {}).get(bot_player_id, 0)
        if cash >= 3 and random.random() < 0.15:
            # Pick a company with unissued shares to auction
            companies = state_dict.get("companies", {})
            for cid in shares:
                info = companies.get(cid, {})
                unissued = info.get("unissued_shares", 0) if isinstance(info, dict) else getattr(info, "unissued_shares", 0)
                if unissued > 0:
                    return ("auction_share", {"company": cid})

        # Nothing to do — pass
        return ("pass", {})

    # Fallback
    return ("pass", {})
