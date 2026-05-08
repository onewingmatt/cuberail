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
        self.shares_held: Dict[str, Dict[str, int]] = {p: {} for p in players}
        self.final_scores: Optional[Dict[str, int]] = None
        self.moves_since_stock_round: int = 0
        self.stock_round_active: bool = False
        self.stock_round_player_index: int = 0
        self.moves_before_stock_round: int = 3

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
            "shares_held": self.shares_held,
            "final_scores": self.final_scores,
            "moves_since_stock_round": self.moves_since_stock_round,
            "stock_round_active": self.stock_round_active,
        }

class NPEngine(GameEngine):
    def setup_game(self, players: List[str]) -> NPState:
        return NPState(players)

    def calculate_final_scores(self, state: NPState) -> Dict[str, int]:
        """Final score = cash + sum(share_value * shares_held) + sum(invested city values)."""
        scores = {}
        for player in state.turn_order:
            cash = state.balances.get(player, 0)
            # Value of held shares
            held_value = 0
            for city, count in state.shares_held.get(player, {}).items():
                held_value += state.share_values.get(city, 10) * count
            # Value of invested cities
            invested_value = 0
            for city, owner in state.investments.items():
                if owner == player:
                    invested_value += state.share_values.get(city, 10)
            scores[player] = cash + held_value + invested_value
        return scores

    def apply_move(self, state: NPState, player_id: str, action_type: str, payload: dict) -> NPState:
        if state.is_game_over:
            raise ValueError("Game is already over")

        if not state.turn_order or state.get_current_actor() != player_id:
            raise ValueError("Not your turn")

        entered_stock = False

        # Block invest and move_train during stock round
        if state.stock_round_active and action_type in ("invest", "move_train"):
            action_label = "invest" if action_type == "invest" else "move the train"
            raise ValueError(f"Cannot {action_label} during stock round")

        if action_type == "invest":
            if state.stock_round_active:
                raise ValueError("Cannot invest during stock round")
            city = payload.get("city")
            if not city or city not in NP_GRAPH:
                raise ValueError("Invalid city")
            if city == "StPaul":
                raise ValueError("Cannot invest in starting city")
            if city in state.investments:
                raise ValueError("City already invested by someone")
            state.investments[city] = player_id

        elif action_type == "move_train":
            if state.stock_round_active:
                raise ValueError("Cannot move train during stock round")
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

            # Track moves and trigger stock round if threshold reached
            state.moves_since_stock_round += 1
            entered_stock = False
            if state.moves_since_stock_round >= state.moves_before_stock_round:
                state.stock_round_active = True
                state.phase = "stock_round"
                state.stock_round_player_index = 0
                state.current_player_index = 0
                entered_stock = True

            if target_city == "Seattle" or target_city == "Portland":
                state.is_game_over = True
                state.stock_round_active = False
                # Determine winner using final scores (cash + shares + cities)
                scores = self.calculate_final_scores(state)
                if scores:
                    state.winner = max(scores, key=scores.get)
                state.final_scores = scores

        elif action_type == "buy_share":
            city = payload.get("city")
            if not city or city not in NP_GRAPH:
                raise ValueError("Invalid city")
            if city not in state.investments:
                raise ValueError("City not invested yet")
            if city == "StPaul":
                raise ValueError("Cannot buy shares in starting city")
            share_price = state.share_values.get(city, 10)
            if state.balances[player_id] < share_price:
                raise ValueError("Not enough cash to buy share")
            if player_id not in state.shares_held:
                state.shares_held[player_id] = {}
            state.shares_held[player_id][city] = state.shares_held[player_id].get(city, 0) + 1
            state.balances[player_id] -= share_price

        elif action_type == "pass":
            if not state.stock_round_active:
                raise ValueError("Can only pass during stock round")

        else:
            raise ValueError(f"Unknown action: {action_type}")

        # Advance turn
        if not state.is_game_over and not entered_stock:
            if state.stock_round_active:
                # Advance to next player in stock round
                state.stock_round_player_index += 1
                if state.stock_round_player_index >= len(state.turn_order):
                    # End stock round
                    state.stock_round_active = False
                    state.phase = "main"
                    state.moves_since_stock_round = 0
                    # Next train move turn starts at the player after the last mover
                    state.current_player_index = (state.current_player_index + 1) % len(state.turn_order)
                else:
                    state.current_player_index = state.stock_round_player_index
            else:
                state.current_player_index = (state.current_player_index + 1) % len(state.turn_order)

        return state
