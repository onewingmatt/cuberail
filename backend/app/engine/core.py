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
