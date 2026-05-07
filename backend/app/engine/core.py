from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class GameState(ABC):
    """
    Abstract base class for the state of a game.
    """
    turn_order: List[str]
    current_player_index: int
    is_game_over: bool

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
