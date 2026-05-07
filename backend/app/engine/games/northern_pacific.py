from typing import List, Dict, Any
from app.engine.core import GameEngine, GameState

NP_GRAPH = {
    "StPaul": ["Fargo", "Duluth"],
    "Duluth": ["Fargo", "StPaul"],
    "Fargo": ["StPaul", "Duluth", "Bismarck"],
    "Bismarck": ["Fargo", "Billings"],
    "Billings": ["Bismarck", "Helena"],
    "Helena": ["Billings", "Spokane"],
    "Spokane": ["Helena", "Seattle"],
    "Seattle": ["Spokane"]
}

class NPState(GameState):
    def __init__(self, players: List[str]):
        self.turn_order = players
        self.current_player_index = 0
        self.is_game_over = False
        self.phase = "main"
        self.active_player_stack = []

        self.train_pos: str = "StPaul"
        # Maps city name to player_id who invested there.
        self.investments: Dict[str, str] = {}
        # Player balances
        self.balances: Dict[str, int] = {p: 0 for p in players}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_player": self.get_current_actor(),
            "phase": self.phase,
            "train_pos": self.train_pos,
            "investments": self.investments,
            "balances": self.balances,
            "game_over": self.is_game_over,
            "graph": NP_GRAPH
        }

class NPEngine(GameEngine):
    def setup_game(self, players: List[str]) -> NPState:
        return NPState(players)

    def apply_move(self, state: NPState, player_id: str, action_type: str, payload: dict) -> NPState:
        if state.is_game_over:
            raise ValueError("Game is already over")

        if not state.turn_order or state.get_current_actor() != player_id:
            raise ValueError("Not your turn")

        if action_type == "invest":
            city = payload.get("city")
            if not city or city not in NP_GRAPH:
                raise ValueError("Invalid city")
            if city == "StPaul":
                raise ValueError("Cannot invest in starting city")
            if city in state.investments:
                raise ValueError("City already invested by someone")

            state.investments[city] = player_id

        elif action_type == "move_train":
            target_city = payload.get("city")
            if not target_city:
                raise ValueError("Missing target city")

            if target_city not in NP_GRAPH[state.train_pos]:
                raise ValueError(f"Cannot move train from {state.train_pos} to {target_city}. Not connected.")

            state.train_pos = target_city

            # Payout if someone owns the city
            owner = state.investments.get(target_city)
            if owner:
                state.balances[owner] += 10

            if target_city == "Seattle":
                state.is_game_over = True

        else:
            raise ValueError(f"Unknown action: {action_type}")

        # Advance turn
        if not state.is_game_over:
            state.current_player_index = (state.current_player_index + 1) % len(state.turn_order)

        return state
