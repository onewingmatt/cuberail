from typing import List, Dict, Any
from app.engine.core import GameEngine, GameState

# Northern Pacific full map graph
# The train starts at Minneapolis/St. Paul and builds westward toward Seattle/Portland
# Directions follow the arrows on the physical board to ensure westward-only flow.
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
    "Portland":     []
}

class NPState(GameState):
    def __init__(self, players: List[str]):
        self.turn_order = players
        self.current_player_index = 0
        self.is_game_over = False
        self.phase = "main"
        self.active_player_stack = []

        self.train_pos: str = "StPaul"
        self.investments: Dict[str, str] = {}
        self.balances: Dict[str, int] = {p: 0 for p in players}
        self.winner: Optional[str] = None
        self.share_values: Dict[str, int] = {city: 10 for city in NP_GRAPH}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_player": self.get_current_actor(),
            "phase": self.phase,
            "train_pos": self.train_pos,
            "investments": self.investments,
            "balances": self.balances,
            "game_over": self.is_game_over,
            "graph": NP_GRAPH,
            "winner": self.winner,
            "share_values": self.share_values,
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

            # Increase share value for the visited city
            if target_city in state.share_values:
                state.share_values[target_city] += 5

            owner = state.investments.get(target_city)
            if owner:
                payout = state.share_values.get(target_city, 10)
                state.balances[owner] += payout
            if target_city == "Seattle" or target_city == "Portland":
                state.is_game_over = True
                # Determine winner: player with highest balance
                if state.balances:
                    state.winner = max(state.balances, key=state.balances.get)
        else:
            raise ValueError(f"Unknown action: {action_type}")

        if not state.is_game_over:
            state.current_player_index = (state.current_player_index + 1) % len(state.turn_order)

        return state
