"""
NPC Bot AI for Northern Pacific — official rules (2018 Rio Grande Games).

Bots decide between two actions per turn:
1. invest: place a standard or enhanced cube in an unconnected city
2. lay_track: place a locomotive on a track segment extending from the train endpoint

Strategy uses scoring heuristics with random jitter for variety.
"""

import random
from typing import List, Dict, Optional, Tuple, Set

from app.engine.games.northern_pacific_data import (
    TRACK_SEGMENTS,
    ALL_CITIES,
    get_outgoing_segments,
)

# Segment lookup by ID
SEGMENT_MAP = {t[0]: t for t in TRACK_SEGMENTS}


def _get_connected_cities(state_dict: dict) -> Set[str]:
    """Recompute connected cities from laid_tracks."""
    connected = {"StPaul"}
    for seg_id in state_dict.get("laid_tracks", []):
        seg = SEGMENT_MAP.get(seg_id)
        if seg:
            connected.add(seg[2])
    return connected


def _available_invest_cities(state_dict: dict) -> List[str]:
    """Return cities that can receive investments."""
    connected = _get_connected_cities(state_dict)
    city_cubes: dict = state_dict.get("city_cubes", {})
    city_enhanced: dict = state_dict.get("city_enhanced", {})
    capacity = state_dict.get("city_capacity", 3)

    result = []
    for city in ALL_CITIES:
        if city in ("StPaul", "Seattle"):
            continue
        if city in connected:
            continue
        total = sum(city_cubes.get(city, {}).values()) + sum(city_enhanced.get(city, {}).values())
        if total >= capacity:
            continue
        result.append(city)
    return result


def _available_track_segments(state_dict: dict) -> List[tuple]:
    """Return track segments that can be laid."""
    endpoint = state_dict.get("train_endpoint", "StPaul")
    laid = set(state_dict.get("laid_tracks", []))
    used_bidir = set(state_dict.get("used_bidirectional", []))
    connected = _get_connected_cities(state_dict)

    result = []
    for t in TRACK_SEGMENTS:
        seg_id, source, target, bidir = t
        if source != endpoint:
            continue
        if seg_id in laid:
            continue
        if bidir and bidir in used_bidir:
            continue
        if target in connected and target != "Seattle":
            continue
        result.append(t)
    return result


def _bfs_distance(start: str, target: str) -> int:
    """BFS shortest path from start to target using outgoing segments."""
    if start == target:
        return 0
    visited = {start}
    queue = [(start, 0)]
    while queue:
        city, dist = queue.pop(0)
        for neighbor_seg in get_outgoing_segments(city):
            neighbor = neighbor_seg[0]
            if neighbor == target:
                return dist + 1
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, dist + 1))
    return 999


def _score_invest_city(
    city: str,
    state_dict: dict,
    bot_player_id: str,
    my_invested_cities: Set[str],
) -> float:
    """Score a city for investment potential."""
    s = 0.0
    endpoint = state_dict.get("train_endpoint", "StPaul")

    # Centrality: more outgoing connections = more likely train will pass through
    outgoing = get_outgoing_segments(city)
    s += len(outgoing) * 4

    # Proximity to train: closer cities pay out sooner
    dist = _bfs_distance(endpoint, city)
    if dist < 10:
        s += (10 - dist) * 2

    # Avoid investing too close — risk of getting skipped
    if dist <= 1:
        s -= 3

    # Prefer cities on paths that have multiple branches (more likely to be visited)
    branch_count = sum(len(get_outgoing_segments(c)) for c, _, _, _ in _available_track_segments(state_dict))
    s += branch_count * 0.5

    # Synergy: invest near other bot investments
    for mc in my_invested_cities:
        d = _bfs_distance(city, mc)
        if d < 4:
            s += (4 - d) * 3

    # Random jitter
    s += random.uniform(-4, 4)

    return s


def _score_track_segment(
    seg: tuple,
    state_dict: dict,
    bot_player_id: str,
    my_invested_cities: Set[str],
    opp_invested_cities: Set[str],
) -> float:
    """Score a track segment for laying."""
    seg_id, source, target, bidir = seg
    s = 0.0

    # Major bonus: moving to a city the bot invested in
    if target in my_invested_cities:
        cube_count = sum(state_dict.get("city_cubes", {}).get(target, {}).values())
        enhanced_count = sum(state_dict.get("city_enhanced", {}).get(target, {}).values())
        total_my = cube_count + enhanced_count
        s += 20 + total_my * 8  # Strong incentive to collect payout

    # Moderate bonus: moving toward cities the bot invested in
    for mc in my_invested_cities:
        d = _bfs_distance(target, mc)
        if d < 4:
            s += (4 - d) * 3

    # Slight penalty: giving opponents a payout
    payout_to_opp = sum(state_dict.get("city_cubes", {}).get(target, {}).values())
    if payout_to_opp > 0:
        s -= payout_to_opp * 3

    # Prefer high-centrality targets (more future options)
    outgoing = get_outgoing_segments(target)
    s += len(outgoing) * 2

    # Avoid ending the round too early
    if target in ("Seattle", "Portland"):
        s -= 10

    # Random jitter
    s += random.uniform(-3, 3)

    return s


def _should_invest(state_dict: dict, bot_player_id: str) -> bool:
    """Heuristic: should the bot invest or lay track?"""
    supply = state_dict.get("player_supply", {}).get(bot_player_id, 0)
    enhanced = state_dict.get("player_enhanced", {}).get(bot_player_id, 0)
    total_cubes = supply + enhanced

    if total_cubes == 0:
        return False  # No cubes to place

    # More likely to invest when we have lots of cubes and the game is early
    available = _available_invest_cities(state_dict)
    if not available:
        return False  # No valid investment targets

    # Early game: invest more
    round_num = state_dict.get("current_round", 1)
    # Use total_rounds = 3 by default
    invested_count = sum(
        1 for c in state_dict.get("city_cubes", {})
        if bot_player_id in state_dict["city_cubes"].get(c, {})
    ) + sum(
        1 for c in state_dict.get("city_enhanced", {})
        if bot_player_id in state_dict["city_enhanced"].get(c, {})
    )

    # Bias toward investing when we have unplaced cubes
    invest_bias = 0.5 + (total_cubes / 4) * 0.3
    invest_bias -= invested_count * 0.05  # Less eager after each investment

    return random.random() < invest_bias


def decide_move(
    bot_player_id: str,
    bot_username: str,
    state_dict: dict,
) -> Tuple[str, dict]:
    """
    Decide what action to take based on game state.

    Returns (action_type, payload).
    """
    # Gather bot's investment positions
    city_cubes: dict = state_dict.get("city_cubes", {})
    city_enhanced: dict = state_dict.get("city_enhanced", {})

    my_invested: Set[str] = set()
    opp_invested: Set[str] = set()

    for city, owners in city_cubes.items():
        for pid in owners:
            if pid == bot_player_id:
                my_invested.add(city)
            else:
                opp_invested.add(city)
    for city, owners in city_enhanced.items():
        for pid in owners:
            if pid == bot_player_id:
                my_invested.add(city)
            else:
                opp_invested.add(city)

    # Decision: invest or lay track?
    if _should_invest(state_dict, bot_player_id):
        available = _available_invest_cities(state_dict)
        if available:
            supply = state_dict.get("player_supply", {}).get(bot_player_id, 0)
            enhanced = state_dict.get("player_enhanced", {}).get(bot_player_id, 0)

            # Score each
            scored = [(c, _score_invest_city(c, state_dict, bot_player_id, my_invested)) for c in available]
            scored.sort(key=lambda x: -x[1])
            best_city = scored[0][0]

            # Decide enhanced vs standard — only choose options we can actually afford
            is_high_value = len(get_outgoing_segments(best_city)) >= 3
            use_enhanced = False
            if enhanced > 0 and supply == 0:
                # No standard cubes left — must use enhanced
                use_enhanced = True
            elif enhanced > 0 and supply > 0 and is_high_value and random.random() < 0.4:
                use_enhanced = True

            if use_enhanced:
                return ("invest", {"city": best_city, "enhanced": True})
            elif supply > 0:
                return ("invest", {"city": best_city, "enhanced": False})
            # If neither standard nor enhanced available, fall through to lay track

    # Lay track — always available unless game is over
    available_tracks = _available_track_segments(state_dict)
    scored = [(t, _score_track_segment(t, state_dict, bot_player_id, my_invested, opp_invested)) for t in available_tracks]
    scored.sort(key=lambda x: -x[1])
    best_seg = scored[0][0]
    return ("lay_track", {"segment_id": best_seg[0]})
