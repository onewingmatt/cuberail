# Cube Rail Game Platform Architecture

This document outlines the architecture for a scalable, web-based platform hosting asynchronous multiplayer "cube rail" board games. Designed for extensibility, it uses an event-sourced game engine to support multiple game rulesets (e.g., Northern Pacific, Irish Gauge, Chicago Express) while providing a modern, real-time user experience. The code will be built utilizing Google IDX (Project Jules) to ensure a standardized, modern development environment.

## 1. High-Level Architecture Diagram

```mermaid
graph TD
    %% Frontend
    subgraph Frontend [Client - Vite / React]
        UI[User Interface]
        State[State Management / Zustand]
        APIClient[API Client / Axios]
        WSClient[WebSocket Client]
    end

    %% Network / API Gateway (Conceptual)
    Internet((Internet))

    %% Backend
    subgraph Backend [Backend - FastAPI]
        Router[API & WS Routers]
        Auth[Auth & User Service]
        GameMgr[Game Manager Service]
        NotifSvc[Notification Service]

        subgraph Engine [Game Engine Core]
            Dispatcher[Action Dispatcher]
            StateBuilder[State Rebuilder]
            GameRules[Abstract Game Ruleset]

            subgraph Rulesets [Specific Game Rulesets]
                NP[Northern Pacific]
                IG[Irish Gauge]
                Generic[Simple Cube Rail]
            end
        end

        DBClient[SQLAlchemy ORM]
    end

    %% External / Storage
    subgraph Storage [Data Layer - PostgreSQL]
        DB[(Relational DB)]
    end

    subgraph External [External Services]
        Email[Email Provider / SendGrid]
    end

    %% Connections
    UI <--> State
    State <--> APIClient
    State <--> WSClient

    APIClient <-->|REST over HTTPS| Internet
    WSClient <-->|WSS| Internet

    Internet <--> Router

    Router --> Auth
    Router --> GameMgr
    Router --> WSClient
    Router --> NotifSvc

    GameMgr --> Engine
    GameRules <|-- NP
    GameRules <|-- IG
    GameRules <|-- Generic
    Dispatcher --> GameRules
    StateBuilder --> GameRules

    Auth --> DBClient
    GameMgr --> DBClient
    DBClient --> DB

    NotifSvc --> Email
```

### Component Details
*   **Frontend (Vite + React):** A responsive SPA managing state (e.g., using Zustand or Redux). It uses standard REST calls for out-of-game actions (lobby, profile) and WebSockets for in-game real-time updates.
*   **Backend (FastAPI):** High-performance Python framework. Handles RESTful routing, background tasks (emails), and WebSocket connections.
*   **Game Engine (Event Sourced):** Central to the architecture. The current state of any game is derived purely by replaying a sequence of stored valid "Move" events. This guarantees perfect replayability and simplifies asynchronous state handling.
*   **Database (PostgreSQL):** Robust relational database, ideal for strict schemas, ACID compliance, and handling JSON/JSONB payloads for event payloads and cached state snapshots.

---

## 2. Database Schema

The database uses a relational model with JSONB fields to accommodate the varied states of different cube rail games.

### `users`
*   `id` (UUID, Primary Key)
*   `username` (String, Unique)
*   `email` (String, Unique)
*   `hashed_password` (String)
*   `created_at` (Timestamp)
*   `updated_at` (Timestamp)

### `games`
*   `id` (UUID, Primary Key)
*   `game_type` (String) - e.g., "northern_pacific", "irish_gauge"
*   `status` (String) - e.g., "waiting", "in_progress", "completed"
*   `created_by_id` (UUID, Foreign Key -> users.id)
*   `created_at` (Timestamp)
*   `completed_at` (Timestamp, Nullable)

### `game_players` (Join Table)
*   `game_id` (UUID, Foreign Key -> games.id)
*   `user_id` (UUID, Foreign Key -> users.id)
*   `player_index` (Integer) - Turn order
*   `joined_at` (Timestamp)

### `game_moves` (Event Sourcing)
*   `id` (UUID, Primary Key)
*   `game_id` (UUID, Foreign Key -> games.id)
*   `user_id` (UUID, Foreign Key -> users.id)
*   `move_number` (Integer) - Monotonically increasing per game to ensure sequence.
*   `action_type` (String) - e.g., "place_track", "buy_share", "auction_bid"
*   `payload` (JSONB) - The specific data for the move (e.g., `{"hex": "A1", "company": "Red"}`).
*   `created_at` (Timestamp)

### `game_snapshots` (Optimization)
*   `game_id` (UUID, Primary Key -> games.id)
*   `last_move_number` (Integer)
*   `state_data` (JSONB) - The fully derived JSON state up to `last_move_number`. Prevents replaying 1000s of moves on every request.
*   `updated_at` (Timestamp)

### `notifications`
*   `id` (UUID, Primary Key)
*   `user_id` (UUID, Foreign Key -> users.id)
*   `type` (String) - e.g., "your_turn", "game_invite", "game_over"
*   `message` (String)
*   `is_read` (Boolean, Default False)
*   `created_at` (Timestamp)

---

## 3. API Design

The API consists of standard REST endpoints for CRUD operations and a WebSocket endpoint for real-time game interaction.

### REST Endpoints
*   **Auth & Users**
    *   `POST /api/auth/register` - Create a new user.
    *   `POST /api/auth/login` - Authenticate and return JWT.
    *   `GET /api/users/me` - Get current user profile.
*   **Games (Lobby)**
    *   `GET /api/games` - List open or active games.
    *   `POST /api/games` - Create a new game instance (specify `game_type`).
    *   `POST /api/games/{game_id}/join` - Join an existing game.
    *   `POST /api/games/{game_id}/start` - Lock lobby and initialize the game state.
*   **Game State & Moves**
    *   `GET /api/games/{game_id}/state` - Fetch the current derived state (using snapshots + recent moves).
    *   `GET /api/games/{game_id}/moves` - Fetch the event log (history).
    *   `POST /api/games/{game_id}/moves` - Submit a new move.
*   **Notifications**
    *   `GET /api/notifications` - Fetch unread notifications.
    *   `POST /api/notifications/{notif_id}/read` - Mark as read.

### WebSocket Flow
*   **Endpoint:** `ws /api/ws/games/{game_id}`
*   **Connection:** Client connects using JWT for authentication.
*   **Message Flow:**
    1.  **Client:** Submits a move event (fallback for REST `POST`).
    2.  **Server:** Validates the move via the Game Engine.
    3.  **Server:** If valid, writes to DB (`game_moves`), updates snapshot.
    4.  **Server:** Broadcasts `STATE_UPDATED` or `MOVE_ACCEPTED` event to all connected clients in that room.
    5.  **Server:** Triggers background task to check if the next player is offline. If so, sends a "Your Turn" email.

---

## 4. Game Engine Interface

To support various Cube Rail games (Northern Pacific, Irish Gauge, etc.), the engine uses an Event Sourcing pattern backed by abstract Python classes.

### Core Interface (`engine/core.py`)

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class GameState(ABC):
    """
    Abstract base class for the state of a game.
    Contains the canonical representation of the board, player hands, etc.
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
```

### Simple Cube Rail Example (`engine/games/simple_rail.py`)

```python
from engine.core import GameEngine, GameState

class SimpleRailState(GameState):
    def __init__(self, players: List[str]):
        self.turn_order = players
        self.current_player_index = 0
        self.is_game_over = False
        self.board_hexes = {} # e.g., {"A1": "Red"}
        self.player_shares = {p: {} for p in players}

    def to_dict(self):
        return {
            "current_player": self.turn_order[self.current_player_index],
            "board": self.board_hexes,
            "shares": self.player_shares,
            "game_over": self.is_game_over
        }

class SimpleRailEngine(GameEngine):
    def setup_game(self, players):
        return SimpleRailState(players)

    def apply_move(self, state: SimpleRailState, player_id: str, action_type: str, payload: dict):
        if state.turn_order[state.current_player_index] != player_id:
            raise ValueError("Not your turn")

        if action_type == "place_track":
            hex_id = payload.get("hex")
            company = payload.get("company")

            if hex_id in state.board_hexes:
                raise ValueError("Hex already occupied")

            state.board_hexes[hex_id] = company

        elif action_type == "buy_share":
            # Logic to deduct money and add share
            pass
        else:
            raise ValueError("Unknown action")

        # Advance turn
        state.current_player_index = (state.current_player_index + 1) % len(state.turn_order)
        return state
```

### How Event Sourcing Works in the Backend
When a game is loaded via the API, the `GameManager`:
1. Fetches the latest `GameSnapshot`.
2. Fetches any `GameMove` records created *after* the snapshot.
3. Instantiates the specific `GameEngine` (e.g., `NorthernPacificEngine`).
4. Iterates through the raw moves, calling `engine.apply_move()` sequentially to rebuild the current real-time state.

---

## 5. Frontend Component Tree (React/Vite)

```text
App
├── AppRouter (react-router-dom)
│   ├── Navbar
│   │   ├── UserMenu
│   │   └── NotificationBadge
│   │
│   ├── AuthPages
│   │   ├── Login
│   │   ├── Register
│   │   └── PasswordReset
│   │
│   ├── Dashboard (Lobby)
│   │   ├── ActiveGamesList
│   │   ├── OpenGamesList
│   │   └── CreateGameModal
│   │
│   ├── Profile
│   │   ├── UserStats
│   │   └── NotificationSettings
│   │
│   └── GameRoom (Route: /game/:id)
│       ├── GameHeader (Info, Turn indicator)
│       ├── MainBoard
│       │   ├── HexGrid (Generic rendering for cube rails)
│       │   │   └── HexCell (Renders tracks/cubes)
│       │   └── UIOverlay (Popups for specific hex actions)
│       ├── PlayerDashboard
│       │   ├── PlayerRoster (List of players, scores, turn order)
│       │   └── CompanyMarket (Shares available, current values)
│       ├── ActionPanel
│       │   ├── ContextualActions (Buttons based on current state phase e.g., "Pass", "Buy", "Build")
│       │   └── ActionLogs (Scrollable history of moves)
│       └── WebSocketManager (Invisible component managing WS connection and Zustand dispatch)
```

---

## 6. Implementation Roadmap

### Phase 1: Foundation & "Hello Cube Rail" (Weeks 1-3)
*   **Backend:** Set up FastAPI, PostgreSQL schemas, User Auth (JWT), and basic REST API.
*   **Frontend:** Initialize Vite/React app, routing, login/registration, and a basic lobby.
*   **Engine:** Implement the `GameEngine` base classes. Create a dummy "SimpleRail" game with just track placement to validate the Event Sourcing architecture.

### Phase 2: Asynchronous Play & Notifications (Weeks 4-5)
*   **Backend:** Implement WebSocket connections for real-time play. Implement the State Rebuilder and Snapshotting logic.
*   **Notifications:** Integrate Celery (or FastAPI `BackgroundTasks`) with an email provider (SendGrid/AWS SES). Trigger emails on "Turn Change".
*   **Frontend:** Add WebSocket listeners. Build the Action Logs component to display real-time moves.

### Phase 3: Northern Pacific (Weeks 6-8)
*   **Engine:** Implement the exact ruleset for *Northern Pacific* (handling the specific map graph, investment phases, train movement, and payouts).
*   **Frontend:** Build a robust Hex/Node rendering engine using SVG or Canvas (e.g., `react-konva`). Create custom UI overlays for Northern Pacific actions.
*   **Testing:** Comprehensive unit tests on the engine to ensure perfect state replayability.

### Phase 4: Expansion & Polish (Weeks 9+)
*   **Engine:** Add *Irish Gauge* (introducing auctions and dynamic dividends). The architecture supports this without changing DB schema—just a new Python Engine class.
*   **Frontend:** Generalize the board renderer. Add user profiles, stats, and Elo ratings.
*   **Infrastructure:** Set up CI/CD, load test WebSocket connections, optimize snapshot frequency.
