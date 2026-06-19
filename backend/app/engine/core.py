from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class Company:
    """
    Standard entity for a railway company in a Cube Rail game.
    """
    def __init__(self, id: str, color: str, initial_treasury: int = 0, initial_shares: int = 10, max_track: int = 15):
        self.id = id
        self.color = color
        self.treasury = initial_treasury
        self.unissued_shares = initial_shares
        self.track_remaining = max_track

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "color": self.color,
            "treasury": self.treasury,
            "unissued_shares": self.unissued_shares,
            "track_remaining": self.track_remaining
        }

class GameState(ABC):
    """
    Abstract base class for the state of a game.
    """
    turn_order: List[str]
    current_player_index: int
    is_game_over: bool

    # Support for phases (e.g. Stock Phase, Operating Phase)
    phase: str = "main"

    # Stack for sub-turns (e.g. Auctions). If not empty, the top player acts instead of current_player_index
    active_player_stack: List[str] = []

    # Standard company tracking (optional for simpler games)
    companies: Dict[str, Company] = {}

    def get_current_actor(self) -> Optional[str]:
        """Returns the player who must act right now."""
        if self.active_player_stack:
            return self.active_player_stack[-1]
        if self.turn_order:
            return self.turn_order[self.current_player_index]
        return None

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Serialize state for frontend/snapshotting."""
        pass

class GameEngine(ABC):
    """
    Abstract base class defining the lifecycle of a Cube Rail game.
    """
    def __init__(self, state: Optional[GameState] = None):
        self.state = state

    @abstractmethod
    def setup_game(self, players: List[str]) -> GameState:
        """Initialize the game state for a new game."""
        pass

    @abstractmethod
    def apply_move(self, state: GameState, player_id: str, action_type: str, payload: Dict[str, Any]) -> GameState:
        """
        Validates and applies a move.
        Raises ValueError if the move is invalid or out of turn.
        Returns the mutated/new GameState.
        """
        pass

class AuctionManager:
    """
    Mixin for managing basic Cube Rail game auctions.
    """
    def start_auction(self, state: GameState, auction_item: str, bidders: List[str], starting_bid: int = 1):
        state.phase = "auction"
        state.active_player_stack = bidders.copy()

        if not hasattr(state, "auction_state"):
            state.auction_state = {}

        state.auction_state = {
            "item": auction_item,
            "current_bid": starting_bid - 1,
            "highest_bidder": None,
            "bidders": bidders.copy(),
            "passed_bidders": []
        }

    def handle_auction_bid(self, state: GameState, player_id: str, bid: int) -> bool:
        """Handle a bid. Returns True if the auction is concluded (only 1 bidder remains)."""
        auction = getattr(state, "auction_state", {})
        if not auction:
            raise ValueError("No active auction.")

        if player_id not in auction["bidders"]:
            raise ValueError("Player not in auction.")

        if bid <= auction["current_bid"]:
            raise ValueError(f"Bid must be higher than current bid of {auction['current_bid']}.")

        auction["current_bid"] = bid
        auction["highest_bidder"] = player_id

        current = state.active_player_stack.pop()
        state.active_player_stack.insert(0, current)

        # Auto-conclude if only 1 bidder left and there's a highest bidder
        if len(auction["bidders"]) == 1 and auction["highest_bidder"] is not None:
            return True
        return False

    def handle_auction_pass(self, state: GameState, player_id: str) -> bool:
        """
        Handles a pass in the auction.
        Returns True if the auction is concluded.
        """
        auction = getattr(state, "auction_state", {})
        if not auction:
            raise ValueError("No active auction.")

        if player_id not in auction["bidders"]:
            raise ValueError("Player not in auction.")

        auction["bidders"].remove(player_id)
        auction["passed_bidders"].append(player_id)

        if player_id in state.active_player_stack:
            state.active_player_stack.remove(player_id)

        if len(auction["bidders"]) == 1 and auction["highest_bidder"] is not None:
            return True
        elif len(auction["bidders"]) == 0:
            return True

        return False

class StockMarket:
    """
    Mixin for managing typical Cube Rail share markets.
    """

    def buy_share(self, state: GameState, player_id: str, company_id: str, price: int):
        """Allows a player to buy a share if available and they have enough funds."""
        if not hasattr(state, "shares"):
            raise ValueError("GameState does not support shares.")
        if not hasattr(state, "balances"):
            raise ValueError("GameState does not support balances.")

        company = state.companies.get(company_id)
        if not company:
            raise ValueError("Invalid company.")

        if company.unissued_shares <= 0:
            raise ValueError("No unissued shares available.")

        if state.balances.get(player_id, 0) < price:
            raise ValueError("Insufficient funds.")

        # Deduct funds and add share
        state.balances[player_id] -= price
        company.unissued_shares -= 1

        if player_id not in state.shares:
            state.shares[player_id] = {}
        state.shares[player_id][company_id] = state.shares[player_id].get(company_id, 0) + 1

    def pay_dividends(self, state: GameState, company_id: str, amount_per_share: int):
        """Pays dividends to all shareholders of a given company."""
        if not hasattr(state, "shares"):
            raise ValueError("GameState does not support shares.")
        if not hasattr(state, "balances"):
            raise ValueError("GameState does not support balances.")

        for player_id, portfolio in state.shares.items():
            shares_owned = portfolio.get(company_id, 0)
            if shares_owned > 0:
                payout = shares_owned * amount_per_share
                state.balances[player_id] = state.balances.get(player_id, 0) + payout
