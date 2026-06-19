# Northern Pacific — Official Rules Implementation

> **For Hermes:** Use the plan to guide implementation. This replaces the current simplified Northern Pacific game with the actual Rio Grande Games / Winsome Games rules.

**Goal:** Rewrite Northern Pacific to match the official board game rules (2018 Rio Grande Games edition).

**Current state:** Simple game with flat $10 payouts, one-investment-per-city, train-move action, single round, cash-based scoring.

**Target state:** Full implementation with limited cube supply, city capacity limits, track-laying (not train-moving), directional track segments, payout on visit, 3-round cumulative scoring (good vs bad investments), and proper round transitions.

**Tech Stack:** Python/FastAPI backend, React/TypeScript frontend, Zustand stores, Socket.IO for live state.

---

### Terminology

| Term | Meaning |
|------|---------|
| Standard cube | Small investment cube (1 point, pays +1 from supply) |
| Enhanced cube | Large investment cube (1 point, pays +2 from supply) |
| Hand / Supply | Cubes a player has available to place |
| City capacity | Max cubes per city (2-4 depending on player count) |
| Track segment | Directional route between two cities (one-way arrow) |
| Bidirectional pair | Two parallel track segments between the same cities (one each way) |
| Train endpoint | The city where the last track was laid |
| Good investments | Cubes in hand at end of round (scored) |
| Bad investments | Cubes left on map at end of round (scored negatively for tiebreaking) |

---

### Track Layout

Each track segment has a source, target, and an ID. Bidirectional pairs have two segments (one each way). Only one of a bidirectional pair can be used per round.

```

StPaul -> Duluth
StPaul -> Fargo
StPaul -> Aberdeen
StPaul -> SiouxFalls

Duluth -> GrandForks
Duluth -> Fargo

GrandForks -> Minot

Fargo -> Minot
Fargo -> Bismarck
Fargo -> GrandForks          # bidirectional with GrandForks -> Fargo

SiouxFalls -> Aberdeen
SiouxFalls -> RapidCity

Aberdeen -> Bismarck
Aberdeen -> RapidCity

Minot -> Glasgow
Minot -> Bismarck

Bismarck -> Terry

RapidCity -> Terry
RapidCity -> Billings
RapidCity -> Casper

Terry -> Glasgow              # bidirectional with Glasgow -> Terry
Terry -> GreatFalls
Terry -> Billings

Glasgow -> Chinook
Glasgow -> Terry              # bidirectional with Terry -> Glasgow

Casper -> Billings
Casper -> Butte

Billings -> GreatFalls
Billings -> Butte

Chinook -> Shelby
Chinook -> GreatFalls

Shelby -> BonnersFerry
Shelby -> GreatFalls

GreatFalls -> Lewiston
GreatFalls -> Butte

Butte -> Lewiston

Lewiston -> Spokane
Lewiston -> Richland

BonnersFerry -> Oroville
BonnersFerry -> Spokane
BonnersFerry -> Lewiston

Oroville -> Vancouver
Oroville -> Spokane

Spokane -> Richland

Vancouver -> Seattle
Vancouver -> Portland

Richland -> Seattle
Richland -> Portland
```

Total: ~44 track segments, 24 cities.

---

## Implementation Plan

### Phase 0: Track Data Model (Backend)

#### Task 0.1: Define track segments as data

**Objective:** Replace the simple NP_GRAPH with a track_segments list that captures directional edges and bidirectional pairs.

**Files:**
- Create: `backend/app/engine/games/northern_pacific_data.py`

**Content:**

```python
"""Track segment definitions for Northern Pacific (official rules)."""

from typing import List, Dict, Tuple

# Each track segment: (segment_id, source_city, target_city, bidirectional_pair_id)
# bidirectional_pair_id: None if unpaired, otherwise shared string matching the other segment
TRACK_SEGMENTS: List[Tuple[str, str, str, str | None]] = [
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
    ("t08", "Fargo", "GrandForks", "bi_fargo_gf"),   # bidirectional pair
    ("t09", "GrandForks", "Fargo", "bi_fargo_gf"),    # ← this one (other direction)

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
    ("t22", "Terry", "Glasgow", "bi_terry_glasgow"),  # bidirectional
    ("t23", "Terry", "GreatFalls", None),
    ("t24", "Terry", "Billings", None),

    # Glasgow
    ("t25", "Glasgow", "Chinook", None),
    ("t26", "Glasgow", "Terry", "bi_terry_glasgow"),   # bidirectional (other way)

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

ALL_CITIES = sorted(list(set(
    city for t in TRACK_SEGMENTS for city in (t[1], t[2])
)))

# Helper: map source city to list of (target, segment_id, bidir_pair_id)
def get_outgoing_segments(city: str) -> List[Tuple[str, str, str | None]]:
    return [(t[2], t[0], t[3]) for t in TRACK_SEGMENTS if t[1] == city]

# Helper: get all cities that have outgoing tracks from them
CITIES_WITH_OUTGOING = sorted(list(set(t[1] for t in TRACK_SEGMENTS)))
```

**Verification:** Run `python3 -c "from app.engine.games.northern_pacific_data import *; print(len(TRACK_SEGMENTS), 'segments,', len(ALL_CITIES), 'cities')"` — should print `49 segments, 24 cities`.

---

### Phase 1: Backend Engine Rewrite

#### Task 1.1: New NPState with official rules

**Objective:** Replace the existing NPState with one that stores player supplies, city cube counts, track segments, round tracking, and cumulative scores.

**Files:**
- Modify: `backend/app/engine/games/northern_pacific.py`
- Create: `backend/tests/test_northern_pacific_rules.py`

**State fields:**

```python
class NPState(GameState):
    def __init__(self, players: List[str], player_count: int):
        self.turn_order = players
        self.current_player_index = 0
        self.is_game_over = False
        self.phase = "main"  # "main" or "game_over"

        # Round and scoring
        self.current_round = 1
        self.cumulative_good: Dict[str, int] = {p: 0 for p in players}  # total good investments across rounds

        # Track state
        self.train_endpoint: str = "StPaul"  # city where the last track was laid
        self.laid_tracks: List[str] = []  # track segment IDs laid this round (in order)
        self.used_bidirectional: set = set()  # bidirectional pair IDs used (one per pair)

        # City investment state
        self.city_cubes: Dict[str, Dict[str, int]] = {}  # city -> {player_id: count}
        # city_cubes["Fargo"]["alice"] = 2 means Alice has 2 cubes in Fargo

        # Player supplies (cubes in hand)
        self.player_supply: Dict[str, int] = {p: 3 for p in players}  # standard cubes (small)
        self.player_enhanced_supply: Dict[str, int] = {p: 1 for p in players}  # enhanced cubes (large)

        # City capacity (depends on player count)
        if player_count == 3:
            self.city_capacity = 2
        elif player_count <= 5:
            self.city_capacity = 3
        else:
            self.city_capacity = 4
```

**Key methods:**

- `to_dict()` — serialize for frontend
- `get_available_tracks()` — returns list of track segments that can be laid from the current train endpoint (not yet laid, not blocked by bidir constraint)
- `get_available_cities_for_investment()` — returns cities that aren't at max capacity and aren't Seattle or connected to the train

**Actions (apply_move):**

1. `"invest"` with `{"city": "...", "enhanced": bool}` — place a cube from supply into city
2. `"lay_track"` with `{"segment_id": "..."}` — place a locomotive on a track segment, extending the line
3. `"pass"` with `{}` — skip (in case no legal moves)

**Payout logic (when train reaches a city):**
- When a track segment is laid that reaches a new city, check if that city has cubes
- For each cube in that city: return it to owner's supply + bonus
  - Standard cube: return + 1 extra standard cube from "the bank" (unlimited supply)
  - Enhanced cube: return + 2 extra standard cubes from the bank
- Remove all cubes from that city

**Round end detection:**
- After a track is laid, if the train endpoint is Seattle, the round ends
- Score: count cubes in each player's hand (supply) = good investments this round
- Add to cumulative_good
- Track bad investments (cubes left on map) for tiebreaking

**Round reset:**
- Clear all tracks and cubes from map
- Reset each player's supply to 1 enhanced + 3 standard
- New start player = player to the left of whoever laid the final track
- If round 3 just ended, game is over

---

#### Task 1.2: Implement invest action

**Objective:** Validate and process investment cube placement.

**Validation:**
- Player must have at least 1 cube of the chosen type in supply
- City must not be at capacity
- City must not be Seattle/StPaul
- City must not already be connected to the train (i.e., on the track path)

**Implementation in apply_move:**

```python
if action_type == "invest":
    city = payload.get("city", "")
    enhanced = payload.get("enhanced", False)
    
    if city in ("StPaul", "Seattle"):
        raise ValueError("Cannot invest in starting or ending city")
    
    if city not in city_positions:
        raise ValueError("Invalid city")
    
    # Check city capacity
    cubes_in_city = sum(self.city_cubes.get(city, {}).values())
    if cubes_in_city >= self.city_capacity:
        raise ValueError("City is at investment capacity")
    
    # Check if city is already connected to train
    if self._is_city_connected(city):
        raise ValueError("City already connected to railroad")
    
    # Check supply
    supply_key = "player_enhanced_supply" if enhanced else "player_supply"
    if self.__dict__[supply_key][player_id] <= 0:
        raise ValueError("No cubes of that type remaining")
    
    # Place cube
    if city not in self.city_cubes:
        self.city_cubes[city] = {}
    self.city_cubes[city][player_id] = self.city_cubes[city].get(player_id, 0) + 1
    self.__dict__[supply_key][player_id] -= 1
```

`_is_city_connected(city)` checks if `city` is in the set of all cities reachable by following the laid track segments from StPaul.

---

#### Task 1.3: Implement lay_track action

**Objective:** Validate and process track laying.

**Validation:**
- Segment must be valid (in TRACK_SEGMENTS)
- Segment's source must be the current train endpoint
- Segment must not already be laid
- If segment is part of a bidirectional pair, the other segment in the pair must not already be laid
- The target city must not already be connected (no revisiting cities)

**Payout on arrival:**

```python
if action_type == "lay_track":
    segment_id = payload.get("segment_id", "")
    
    # Find segment
    segment = next((t for t in TRACK_SEGMENTS if t[0] == segment_id), None)
    if not segment:
        raise ValueError("Invalid track segment")
    
    _, source, target, bidir_pair = segment
    
    if source != self.train_endpoint:
        raise ValueError(f"Track must extend from {self.train_endpoint}")
    
    if segment_id in self.laid_tracks:
        raise ValueError("Track segment already laid")
    
    if bidir_pair and bidir_pair in self.used_bidirectional:
        raise ValueError("Other direction of this bidirectional pair already used")
    
    if self._is_city_connected(target):
        raise ValueError("City already visited by railroad")
    
    # Lay the track
    self.laid_tracks.append(segment_id)
    if bidir_pair:
        self.used_bidirectional.add(bidir_pair)
    self.train_endpoint = target
    
    # Payout: if target has investment cubes, pay them out
    if target in self.city_cubes:
        for owner_id, count in list(self.city_cubes[target].items()):
            for _ in range(count):
                if self.city_cubes[target].get(owner_id, 0) > 0:
                    self.city_cubes[target][owner_id] -= 1
                    # Return cube to supply + bonus
                    self.player_supply[owner_id] += 1  # base return
                    # Bonus depends on cube type — simplified: all cubes get +1
                    # Actually in the rules, enhanced cubes give +2 bonus vs +1 for standard
                    # But we're tracking per-cube type... we need to track which cubes are enhanced
                    # For now: assume we track enhanced vs standard separately in city_cubes
                    # Enhanced cube bonus: +2 extra standard cubes
                    self.player_supply[owner_id] += 1  # bonus (or +2 for enhanced)
    
    # Clean up empty city entries
    if target in self.city_cubes and sum(self.city_cubes[target].values()) == 0:
        del self.city_cubes[target]
    
    # Check round end
    if target == "Seattle":
        self._end_round()
```

**Note on enhanced cube tracking:** Need to track enhanced cubes separately in city_cubes. Use a parallel dict or store city_cubes as `{city: {player_id: {"standard": N, "enhanced": M}}}`.

Simplified for now: `city_cubes = {city: {player_id: count}}` and `city_enhanced_cubes = {city: {player_id: count}}` — all cubes count as 1 each for capacity, but enhanced cubes pay out differently.

---

#### Task 1.4: Round end and scoring

**Objective:** Implement round-end scoring, cumulative totals, and board reset.

**Scoring:**
- Good investments this round = all cubes in player's supply (standard + enhanced, each counts as 1)
- Add to cumulative_good[player]
- Bad investments this round = cubes left on the map (any remaining in city_cubes + city_enhanced_cubes, each counts as 1)
- Store as tiebreaker

**Round reset:**
- Clear laid_tracks, used_bidirectional, city_cubes, city_enhanced_cubes
- train_endpoint = "StPaul"
- Reset each player's supply: 3 standard + 1 enhanced
- New start player = next player in turn order after whoever laid the last track
- current_round += 1
- If current_round > 3: game over, winner = player with highest cumulative_good (tiebreak by fewest bad investments)

---

### Phase 2: Bot AI

#### Task 2.1: Simple heuristic bot for official rules

**Objective:** Bot that decides between invest and lay_track based on simple heuristics.

**Logic:**
- If bot has no cubes in supply, must lay track
- If bot has cubes, evaluate:
  - Score available cities for investment (centrality, proximity to train, existing investments by self/others)
  - Score available track segments (proximity to own investments, ability to strand opponents)
  - Choose based on weighted score with random jitter

---

### Phase 3: Frontend

#### Task 3.1: Update NorthernPacificBoard for official rules

**Objective:** Redesign the board UI for the official rules.

**Changes needed:**
- Show player's supply (cubes remaining: N standard, M enhanced)
- Show city cube counts (how many cubes in each city, by whom)
- Show available track segments from current train endpoint (highlight valid ones)
- Replace "Move Train" + "Invest" buttons with official actions:
  - "Invest (Standard)" and "Invest (Enhanced)" buttons when a city is selected
  - Click on a track segment to lay track
- Show current round number
- Show cumulative scores
- Show score track (good investments bar)
- Show city capacity info

**Layout:**
- Left: SVG board with track segments (laid tracks visible, available tracks highlighted)
- Right panel: Player info, supply, scores, controls

---

### Phase 4: Integration

#### Task 4.1: Wire up the new engine in games.py

**Objective:** Replace the old NPEngine import with the new one in the games API.

**Files:**
- Modify: `backend/app/api/games.py`

**Changes:**
- Import `NPEngineV2` (or rename the new engine to `NPEngine` and old one to `NPEngineV1`)
- Pass player_count to setup_game
- Update move validation for new action types

---

### Phase 5: Tests

#### Task 5.1: Write comprehensive tests

Test scenarios:
- Setup with various player counts
- Invest action (valid, invalid city, capacity, supply)
- Lay track action (valid, invalid, bidirectional constraint, revisit prevention)
- Payout on city arrival (standard, enhanced, multiple owners)
- Round end detection (Seattle reached)
- Scoring (good/bad investments)
- Round reset and cumulative scoring
- Game over after 3 rounds
- Winner determination

---

## Execution Strategy

Use subagent-driven-development with parallel worker agents for independent phases (backend engine, data model) and sequential for dependent ones (frontend depends on backend API shape).

Each task = one subagent delegation with spec compliance review after completion.
