from typing import List, Dict, Any
from app.engine.core import GameEngine, GameState

class SimpleRailState(GameState):
    def __init__(self, players: List[str]):
        self.turn_order = players
        self.current_player_index = 0
        self.is_game_over = False
        self.board_hexes: Dict[str, str] = {} # e.g., {"0,0": "Red"}
        self.player_shares: Dict[str, Dict[str, int]] = {p: {} for p in players}
        self.phase = "main"
        self.active_player_stack = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_player": self.get_current_actor(),
            "phase": self.phase,
            "board": self.board_hexes,
            "shares": self.player_shares,
            "game_over": self.is_game_over
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], players: List[str]):
        state = cls(players)
        if data.get("current_player") in players:
            state.current_player_index = players.index(data["current_player"])
        state.board_hexes = data.get("board", {})
        state.player_shares = data.get("shares", {p: {} for p in players})
        state.is_game_over = data.get("game_over", False)
        return state

class SimpleRailEngine(GameEngine):
    def setup_game(self, players: List[str]) -> SimpleRailState:
        return SimpleRailState(players)

    def apply_move(self, state: SimpleRailState, player_id: str, action_type: str, payload: dict) -> SimpleRailState:
        if state.is_game_over:
            raise ValueError("Game is already over")

        if not state.turn_order or state.get_current_actor() != player_id:
            raise ValueError("Not your turn")

        if action_type == "place_track":
            hex_id = payload.get("hex")
            company = payload.get("company")

            if not hex_id or not company:
                raise ValueError("Missing hex or company in payload")

            if hex_id in state.board_hexes:
                raise ValueError("Hex already occupied")

            state.board_hexes[hex_id] = company

        elif action_type == "buy_share":
            company = payload.get("company")
            if not company:
                raise ValueError("Missing company in payload")
            if company not in state.player_shares[player_id]:
                state.player_shares[player_id][company] = 0
            state.player_shares[player_id][company] += 1

        elif action_type == "pass":
            pass # Explicit pass
        else:
            raise ValueError(f"Unknown action: {action_type}")

        # Advance turn
        state.current_player_index = (state.current_player_index + 1) % len(state.turn_order)
        return state
