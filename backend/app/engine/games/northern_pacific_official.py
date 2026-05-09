"""
Northern Pacific engine — official Rio Grande Games rules (2018).

Replaces the simplified flat-$10-payout version with the actual board game:
- 3 rounds, each player has 1 enhanced + 3 standard cubes per round
- Two actions: invest (place cube) or lay_track (extend railroad)
- Payout when railroad reaches a city: cubes return + bonus from supply
- Scoring: good investments (cubes in hand) vs bad investments (cubes on map)
- After 3 rounds, most good investments wins (tiebreak: fewest bad)

Track segments defined in northern_pacific_data.py.
"""

from typing import List, Dict, Any, Optional, Set, Tuple
from app.engine.core import GameEngine, GameState
from app.engine.games.northern_pacific_data import (
    TRACK_SEGMENTS,
    ALL_CITIES,
    get_outgoing_segments,
    NP_GRAPH,
)


def _city_capacity_for(player_count: int) -> int:
    """Maximum cubes per city based on player count."""
    if player_count <= 3:
        return 2
    elif player_count <= 5:
        return 3
    return 4


class NPState(GameState):
    """Game state for Northern Pacific (official rules)."""

    def __init__(self, players: List[str], player_count: int):
        self.turn_order = players
        self.current_player_index = 0
        self.is_game_over = False
        self.phase = "main"

        # Round and scoring
        self.current_round: int = 1
        self.cumulative_good: Dict[str, int] = {p: 0 for p in players}
        self.cumulative_bad: Dict[str, int] = {p: 0 for p in players}

        # Track state
        self.train_endpoint: str = "StPaul"
        self.laid_tracks: List[str] = []          # segment IDs in order
        self.used_bidirectional: Set[str] = set() # pair IDs used (one per pair)

        # City investment — track standard vs enhanced separately
        self.city_cubes: Dict[str, Dict[str, int]] = {}       # city -> {player: standard_count}
        self.city_enhanced: Dict[str, Dict[str, int]] = {}    # city -> {player: enhanced_count}

        # Player supplies (cubes in hand)
        self.player_supply: Dict[str, int] = {p: 3 for p in players}
        self.player_enhanced: Dict[str, int] = {p: 1 for p in players}

        # City capacity
        self.city_capacity = _city_capacity_for(player_count)

        # Track who laid the last track (for round start rotation)
        self.last_track_layer: Optional[str] = None

        # Winner
        self.winner: Optional[str] = None
        self.final_scores: Optional[Dict[str, int]] = None

    # ---- Helpers ----

    def _get_connected_cities(self) -> Set[str]:
        """Return set of all cities reached by the railroad this round."""
        connected = {"StPaul"}
        for seg_id in self.laid_tracks:
            seg = self._find_segment(seg_id)
            if seg:
                connected.add(seg[2])
        return connected

    def _find_segment(self, segment_id: str) -> Optional[Tuple[str, str, str, Optional[str]]]:
        """Find a track segment by its ID."""
        for t in TRACK_SEGMENTS:
            if t[0] == segment_id:
                return t
        return None

    def _total_cubes_in_city(self, city: str) -> int:
        """Count all cubes (standard + enhanced) in a city."""
        std = sum(self.city_cubes.get(city, {}).values())
        enh = sum(self.city_enhanced.get(city, {}).values())
        return std + enh

    def _is_connected(self, city: str) -> bool:
        """Check if a city has been reached by the railroad this round."""
        return city in self._get_connected_cities()

    def _available_invest_cities(self) -> List[str]:
        """Return cities that can receive investments."""
        connected = self._get_connected_cities()
        result = []
        for city in ALL_CITIES:
            if city in ("StPaul", "Seattle"):
                continue
            if city in connected:
                continue
            if self._total_cubes_in_city(city) >= self.city_capacity:
                continue
            result.append(city)
        return result

    def _available_track_segments(self) -> List[Tuple[str, str, str, Optional[str]]]:
        """Return track segments that can be laid from the current endpoint."""
        current = self.train_endpoint
        connected = self._get_connected_cities()
        result = []
        for seg in TRACK_SEGMENTS:
            seg_id, source, target, bidir = seg
            if source != current:
                continue
            if seg_id in self.laid_tracks:
                continue
            if bidir and bidir in self.used_bidirectional:
                continue
            if target in connected and target != "Seattle":
                # Can only reach Seattle at the end; already-visited cities
                # that aren't Seattle are illegal.
                continue
            result.append(seg)
        return result

    # ---- Engine interface ----

    def get_current_actor(self) -> Optional[str]:
        if self.current_player_index < len(self.turn_order):
            return self.turn_order[self.current_player_index]
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "game_type": "northern_pacific",
            "current_player": self.get_current_actor(),
            "phase": self.phase,
            "players": [{"id": p} for p in self.turn_order],
            "train_endpoint": self.train_endpoint,
            "laid_tracks": self.laid_tracks,
            "used_bidirectional": list(self.used_bidirectional),
            "city_cubes": self.city_cubes,
            "city_enhanced": self.city_enhanced,
            "player_supply": self.player_supply,
            "player_enhanced": self.player_enhanced,
            "current_round": self.current_round,
            "cumulative_good": self.cumulative_good,
            "cumulative_bad": self.cumulative_bad,
            "city_capacity": self.city_capacity,
            "game_over": self.is_game_over,
            "winner": self.winner,
            "final_scores": self.final_scores,
            "graph": NP_GRAPH,
            "available_invest_cities": self._available_invest_cities(),
            "available_tracks": [
                {"segment_id": t[0], "source": t[1], "target": t[2]}
                for t in self._available_track_segments()
            ],
        }


class NPEngineOfficial(GameEngine):
    """Northern Pacific engine implementing official Rio Grande Games rules."""

    def setup_game(self, players: List[str], player_count: int = 0) -> NPState:
        """Create a new game state. player_count defaults to len(players)."""
        if player_count <= 0:
            player_count = len(players)
        return NPState(players, player_count)

    def apply_move(self, state: NPState, player_id: str, action_type: str, payload: dict) -> NPState:
        if state.is_game_over:
            raise ValueError("Game is already over")

        if state.get_current_actor() != player_id:
            raise ValueError("Not your turn")

        if action_type == "invest":
            self._do_invest(state, player_id, payload)
        elif action_type == "lay_track":
            self._do_lay_track(state, player_id, payload)
        elif action_type == "pass":
            pass  # Skip turn (no legal moves)
        else:
            raise ValueError(f"Unknown action: {action_type}")

        # Advance turn (unless game just ended)
        if not state.is_game_over:
            state.current_player_index = (state.current_player_index + 1) % len(state.turn_order)

        return state

    def _do_invest(self, state: NPState, player_id: str, payload: dict):
        city = payload.get("city", "")
        enhanced = payload.get("enhanced", False)

        if city in ("StPaul", "Seattle"):
            raise ValueError("Cannot invest in starting or ending city")

        if city not in ALL_CITIES:
            raise ValueError(f"Invalid city: {city}")

        if state._is_connected(city):
            raise ValueError("City already connected to the railroad")

        if state._total_cubes_in_city(city) >= state.city_capacity:
            raise ValueError("City is at investment capacity")

        if enhanced:
            if state.player_enhanced.get(player_id, 0) <= 0:
                raise ValueError("No enhanced cubes remaining")
            state.player_enhanced[player_id] -= 1
        else:
            if state.player_supply.get(player_id, 0) <= 0:
                raise ValueError("No standard cubes remaining")
            state.player_supply[player_id] -= 1

        # Place the cube
        target_dict = state.city_enhanced if enhanced else state.city_cubes
        if city not in target_dict:
            target_dict[city] = {}
        target_dict[city][player_id] = target_dict[city].get(player_id, 0) + 1

    def _do_lay_track(self, state: NPState, player_id: str, payload: dict):
        segment_id = payload.get("segment_id", "")

        seg = state._find_segment(segment_id)
        if not seg:
            raise ValueError(f"Invalid track segment: {segment_id}")

        _, source, target, bidir = seg

        if segment_id in state.laid_tracks:
            raise ValueError("Track segment already laid")

        if source != state.train_endpoint:
            raise ValueError(f"Track must extend from {state.train_endpoint}")

        if bidir and bidir in state.used_bidirectional:
            raise ValueError("Other direction of this bidirectional pair already used")

        if target in state._get_connected_cities() and target != "Seattle":
            raise ValueError("Cannot revisit an already-connected city")

        # Lay the track
        state.laid_tracks.append(segment_id)
        if bidir:
            state.used_bidirectional.add(bidir)
        state.train_endpoint = target
        state.last_track_layer = player_id

        # Payout: when railroad reaches a city with investments
        self._process_payout(state, target)

        # Check round end
        if target == "Seattle":
            self._end_round(state)

    def _process_payout(self, state: NPState, city: str):
        """Pay out investments when the railroad reaches a city."""
        if city not in state.city_cubes and city not in state.city_enhanced:
            return

        # Standard cubes payout
        if city in state.city_cubes:
            for owner, count in list(state.city_cubes[city].items()):
                if count > 0:
                    del state.city_cubes[city][owner]
                    # Return cube + 1 bonus per standard cube
                    state.player_supply[owner] = state.player_supply.get(owner, 0) + count * 2

        # Enhanced cubes payout
        if city in state.city_enhanced:
            for owner, count in list(state.city_enhanced[city].items()):
                if count > 0:
                    del state.city_enhanced[city][owner]
                    # Return cube + 2 bonus standard cubes per enhanced cube
                    state.player_supply[owner] = state.player_supply.get(owner, 0) + count * 2
                    # Also return the enhanced cube itself back to the pool
                    state.player_enhanced[owner] = state.player_enhanced.get(owner, 0) + count

        # Clean up empty entries
        if city in state.city_cubes and not state.city_cubes[city]:
            del state.city_cubes[city]
        if city in state.city_enhanced and not state.city_enhanced[city]:
            del state.city_enhanced[city]

    def _end_round(self, state: NPState):
        """Score the round, reset for next round or end game."""
        # Count good investments (cubes in hand)
        for p in state.turn_order:
            supply = state.player_supply.get(p, 0)
            enhanced = state.player_enhanced.get(p, 0)
            state.cumulative_good[p] += supply + enhanced

        # Count bad investments (cubes on map) for tiebreaking
        for p in state.turn_order:
            bad = 0
            for city_cubes in state.city_cubes.values():
                bad += city_cubes.get(p, 0)
            for city_cubes in state.city_enhanced.values():
                bad += city_cubes.get(p, 0)
            state.cumulative_bad[p] += bad

        # Check if game is over
        if state.current_round >= 3:
            state.is_game_over = True
            self._determine_winner(state)
            return

        # Reset for next round
        state.current_round += 1
        state.train_endpoint = "StPaul"
        state.laid_tracks = []
        state.used_bidirectional = set()
        state.city_cubes = {}
        state.city_enhanced = {}
        state.player_supply = {p: 3 for p in state.turn_order}
        state.player_enhanced = {p: 1 for p in state.turn_order}

        # New start player: next player after the one who laid the last track
        if state.last_track_layer and state.last_track_layer in state.turn_order:
            idx = state.turn_order.index(state.last_track_layer)
            state.current_player_index = (idx + 1) % len(state.turn_order)
        else:
            state.current_player_index = 0

    def _determine_winner(self, state: NPState):
        """Determine the winner based on cumulative scores."""
        if not state.turn_order:
            return

        best_player = state.turn_order[0]
        best_good = state.cumulative_good[best_player]
        best_bad = state.cumulative_bad[best_player]

        for p in state.turn_order[1:]:
            g = state.cumulative_good[p]
            b = state.cumulative_bad[p]
            if g > best_good:
                best_player = p
                best_good = g
                best_bad = b
            elif g == best_good and b < best_bad:
                # Tiebreaker: fewest bad investments
                best_player = p
                best_good = g
                best_bad = b

        state.winner = best_player
        state.final_scores = {
            "good": dict(state.cumulative_good),
            "bad": dict(state.cumulative_bad),
        }
