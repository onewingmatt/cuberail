from typing import List, Dict, Any
from app.engine.core import GameEngine, GameState, Company, AuctionManager, StockMarket
from app.engine.utils.map_loader import MapLoader

class PrussianRailsState(GameState):
    def __init__(self, players: List[str]):
        self.turn_order = players
        self.current_player_index = 0
        self.is_game_over = False
        self.phase = "auction" # starts with initial auctions
        self.active_player_stack = players.copy()

        # Player balances
        # Starting cash depends on player count in PR, simplifed to $30 here
        self.balances: Dict[str, int] = {p: 30 for p in players}

        # Player shares {player_id: {company_id: count}}
        self.shares: Dict[str, Dict[str, int]] = {p: {} for p in players}

        # Track on board {city_id: [company_ids]}
        self.board: Dict[str, List[str]] = {}

        # Setup companies based on historic PR
        self.companies: Dict[str, Company] = {
            "Berlin-Hamburger": Company("Berlin-Hamburger", "#006400", initial_shares=3, max_track=14),
            "Koln-Mindener": Company("Koln-Mindener", "#800080", initial_shares=3, max_track=13),
            "Main-Wesel": Company("Main-Wesel", "#DAA520", initial_shares=3, max_track=15),
            "Badische": Company("Badische", "#FF0000", initial_shares=3, max_track=16),
            "Bayerische": Company("Bayerische", "#0000FF", initial_shares=3, max_track=17),
            "Sachsische": Company("Sachsische", "#FFA500", initial_shares=3, max_track=12),
            "Niederschlesische": Company("Niederschlesische", "#8B4513", initial_shares=3, max_track=18),
            "Preussische Ostbahn": Company("Preussische Ostbahn", "#000000", initial_shares=3, max_track=21),
        }

        # Initial Auction Setup
        self.company_auction_queue = list(self.companies.keys())

        self.map_data = MapLoader.load_map("prussian_rails")
        self.graph = self.map_data.get("edges", {})

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_player": self.get_current_actor(),
            "phase": self.phase,
            "balances": self.balances,
            "shares": self.shares,
            "board": self.board,
            "companies": {k: v.to_dict() for k, v in self.companies.items()},
            "game_over": self.is_game_over,
            "graph": self.graph,
            "map_data": self.map_data,
            "auction_state": getattr(self, "auction_state", None)
        }

class PrussianRailsEngine(GameEngine, AuctionManager, StockMarket):
    def setup_game(self, players: List[str]) -> PrussianRailsState:
        state = PrussianRailsState(players)
        # Start the first auction automatically
        first_company = state.company_auction_queue.pop(0)
        self.start_auction(state, first_company, state.turn_order)
        return state

    def apply_move(self, state: PrussianRailsState, player_id: str, action_type: str, payload: dict) -> PrussianRailsState:
        if state.is_game_over:
            raise ValueError("Game is already over")

        if state.get_current_actor() != player_id:
            raise ValueError(f"Not your turn. Expected {state.get_current_actor()}, got {player_id}")

        if state.phase == "auction":
            if action_type == "bid":
                bid_amount = payload.get("bid", 0)
                if state.balances[player_id] < bid_amount:
                    raise ValueError("Not enough money to bid that amount.")
                self.handle_auction_bid(state, player_id, bid_amount)
            elif action_type == "pass":
                concluded = self.handle_auction_pass(state, player_id)
                if concluded:
                    self._resolve_auction(state)
            else:
                raise ValueError("Invalid action during auction phase")

        elif state.phase == "main":
            if action_type == "build_track":
                company_id = payload.get("company")
                city_id = payload.get("city")

                if company_id not in state.companies:
                    raise ValueError("Invalid company")
                if state.shares[player_id].get(company_id, 0) == 0:
                    raise ValueError("Must own a share to build track for this company")
                if city_id not in state.graph:
                    raise ValueError("Invalid city")
                if state.companies[company_id].treasury < 1: # simplified cost
                     raise ValueError("Company does not have enough treasury to build")

                state.companies[company_id].treasury -= 1
                state.companies[company_id].track_remaining -= 1

                if city_id not in state.board:
                    state.board[city_id] = []
                state.board[city_id].append(company_id)

                # Advance turn
                state.current_player_index = (state.current_player_index + 1) % len(state.turn_order)

            elif action_type == "auction_share":
                company_id = payload.get("company")
                if company_id not in state.companies:
                    raise ValueError("Invalid company")
                if state.companies[company_id].unissued_shares <= 0:
                    raise ValueError("No unissued shares left to auction")

                self.start_auction(state, company_id, state.turn_order)
            else:
                raise ValueError(f"Unknown action: {action_type}")

        return state

    def _resolve_auction(self, state: PrussianRailsState):
        auction = state.auction_state
        winner = auction["highest_bidder"]
        bid = auction["current_bid"]
        company_id = auction["item"]

        if winner:
            state.balances[winner] -= bid
            state.companies[company_id].treasury += bid
            state.companies[company_id].unissued_shares -= 1
            state.shares[winner][company_id] = state.shares[winner].get(company_id, 0) + 1

        state.auction_state = None
        state.active_player_stack = []

        if state.company_auction_queue:
            # Continue initial auctions
            next_company = state.company_auction_queue.pop(0)
            self.start_auction(state, next_company, state.turn_order)
        else:
            # Transition to main phase
            state.phase = "main"
