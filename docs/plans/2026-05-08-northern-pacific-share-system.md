# Northern Pacific — Share System & Game Loop

> **For Hermes:** Use subagent-driven-development skill to implement this plan
> task-by-task. Each task is 2-5 minutes of focused work. Commit after every task.

**Goal:** Implement the core Northern Pacific stock/share value system and
complete the game loop so players can play a full game with proper scoring.

**Architecture:** The NPEngine currently uses a simplified flat $10 payout per
city visit. We need to replace this with a proper share system where each city
has a share value that increases as the train passes through it, players can buy
shares in cities they've invested in, and final scoring values shares plus cash.

**Tech Stack:** Python/FastAPI backend, React/TypeScript frontend, Zustand stores.

---

### Phase 1: Git Hygiene

#### Task 1: Create main branch

**Objective:** Set up a proper `main` branch so feature branches can be PR'd.

**Files:**
- No code changes — pure git ops

**Steps:**

```bash
cd /home/onewing/cuberail
git checkout -b main
git push origin main
git checkout add-architecture-md-4571389397446890098
```

Then update the default branch on GitHub to `main`.

---

### Phase 2: Share Value System (Backend)

#### Task 2: Add share_value tracking to NPState

**Objective:** Each city has a numerical share value that starts at 10 and
increases when the train passes through.

**Files:**
- Modify: `backend/app/engine/games/northern_pacific.py`

**Step 1: Write failing test**

Add to `backend/tests/test_northern_pacific.py`:

```python
def test_share_value_increases_on_visit():
    engine = NPEngine()
    state = engine.setup_game(["alice", "bob"])

    # Check initial share value
    assert state.share_values["Fargo"] == 10

    # Alice invests in Fargo
    state = engine.apply_move(state, "alice", "invest", {"city": "Fargo"})

    # Bob moves train to Fargo — share value should increase
    state = engine.apply_move(state, "bob", "move_train", {"city": "Fargo"})

    # Fargo's share value went up
    assert state.share_values["Fargo"] > 10
    # Alice got the payout (increased share value, not flat $10)
    assert state.balances["alice"] > 0
```

**Step 2: Run test to verify failure**

```bash
cd /home/onewing/cuberail/backend
python -m pytest tests/test_northern_pacific.py::test_share_value_increases_on_visit -v
```

Expected: FAIL — `NPState` has no `share_values` attribute

**Step 3: Modify NPState**

In `northern_pacific.py`, add to `NPState.__init__`:

```python
self.share_values: Dict[str, int] = {city: 10 for city in NP_GRAPH}
```

Add to `NPState.to_dict()`:

```python
"share_values": self.share_values,
```

In `NPEngine.apply_move`, change the payout logic for `move_train`:

```python
if target_city in state.share_values:
    state.share_values[target_city] += 5  # Share value increases by 5

owner = state.investments.get(target_city)
if owner:
    payout = state.share_values[target_city]
    state.balances[owner] += payout
```

**Step 4: Run test to verify pass**

```bash
cd /home/onewing/cuberail/backend
python -m pytest tests/test_northern_pacific.py::test_share_value_increases_on_visit -v
```

Expected: PASS

**Step 5: Commit**

```bash
cd /home/onewing/cuberail
git add backend/app/engine/games/northern_pacific.py backend/tests/test_northern_pacific.py
git commit -m "feat: add share value tracking that increases on train visits"
```

---

#### Task 3: Add share_buying action type

**Objective:** Players can buy shares in cities they've invested in during stock
rounds, paying from their balance.

**Files:**
- Modify: `backend/app/engine/games/northern_pacific.py`
- Modify: `backend/tests/test_northern_pacific.py`

**Step 1: Write failing test**

```python
def test_buy_share():
    engine = NPEngine()
    state = engine.setup_game(["alice", "bob"])

    # Alice invests in Fargo
    state = engine.apply_move(state, "alice", "invest", {"city": "Fargo"})

    # Alice buys a share in Fargo
    state = engine.apply_move(state, "bob", "buy_share", {"city": "Fargo", "player": "alice"})

    # Check ownership
    assert "Fargo" in state.shares_held["alice"]
    # Balance decreased by share price
    assert state.balances["alice"] == -10  # Share base price
```

**Step 2: Run test to verify failure**

```bash
cd /home/onewing/cuberail/backend
python -m pytest tests/test_northern_pacific.py::test_buy_share -v
```

Expected: FAIL — unknown action type

**Step 3: Add buy_share to NPState**

Add to `NPState.__init__`:

```python
self.shares_held: Dict[str, Dict[str, int]] = {p: {} for p in players}
# shares_held[player_id][city_name] = number of shares
```

Add to `NPState.to_dict()`:

```python
"shares_held": self.shares_held,
```

Add to `apply_move` in the action_type branching:

```python
elif action_type == "buy_share":
    city = payload.get("city")
    target_player = payload.get("player")
    if not city or not target_player:
        raise ValueError("Missing city or player")
    if city not in state.investments or state.investments[city] != target_player:
        raise ValueError("City not invested by that player")
    if target_player not in state.shares_held:
        state.shares_held[target_player] = {}
    state.shares_held[target_player][city] = state.shares_held[target_player].get(city, 0) + 1
    share_price = state.share_values.get(city, 10)
    if state.balances[target_player] < share_price:
        raise ValueError("Not enough cash")
    state.balances[target_player] -= share_price
```

Note: `buy_share` does NOT advance the turn (it's a sub-action during stock round).

**Step 4: Run test to verify pass**

```bash
cd /home/onewing/cuberail/backend
python -m pytest tests/test_northern_pacific.py::test_buy_share -v
```

Expected: PASS

**Step 5: Commit**

```bash
cd /home/onewing/cuberail
git add backend/app/engine/games/northern_pacific.py backend/tests/test_northern_pacific.py
git commit -m "feat: add buy_share action with share price deduction"
```

---

#### Task 4: Update game-over scoring to include share value

**Objective:** Final score = cash balance + (share_value * number_of_shares) for
each city invested. The winner is the player with the highest total.

**Files:**
- Modify: `backend/app/engine/games/northern_pacific.py`
- Modify: `backend/tests/test_northern_pacific.py`

**Step 1: Write failing test**

```python
def test_final_score_includes_shares():
    engine = NPEngine()
    state = engine.setup_game(["alice", "bob"])

    # Alice invests in Fargo
    state = engine.apply_move(state, "alice", "invest", {"city": "Fargo"})
    # Bob invests in Duluth
    state = engine.apply_move(state, "bob", "invest", {"city": "Duluth"})

    # Bob moves train to Fargo (Alice gets $10 payout)
    state = engine.apply_move(state, "alice", "move_train", {"city": "Fargo"})

    # Alice buys a share in Fargo
    state = engine.apply_move(state, "bob", "buy_share", {"city": "Fargo", "player": "alice"})

    # Calculate final scores
    scores = engine.calculate_final_scores(state)
    assert "alice" in scores
    assert "bob" in scores
    # Alice has cash + share value
    assert scores["alice"] > 0
```

**Step 2: Run test to verify failure**

```bash
cd /home/onewing/cuberail/backend
python -m pytest tests/test_northern_pacific.py::test_final_score_includes_shares -v
```

Expected: FAIL — `NPEngine` has no `calculate_final_scores` method

**Step 3: Add calculate_final_scores to NPEngine**

```python
def calculate_final_scores(self, state: NPState) -> Dict[str, int]:
    scores = {}
    for player in state.turn_order:
        cash = state.balances.get(player, 0)
        share_value = 0
        held = state.shares_held.get(player, {})
        for city, count in held.items():
            value = state.share_values.get(city, 10)
            share_value += value * count
        # Also credit the value of invested cities themselves
        invested_value = 0
        for city, owner in state.investments.items():
            if owner == player:
                invested_value += state.share_values.get(city, 10)
        scores[player] = cash + share_value + invested_value
    return scores
```

Update the winner determination in `apply_move`:

```python
if target_city == "Seattle" or target_city == "Portland":
    state.is_game_over = True
    scores = self.calculate_final_scores(state)
    if scores:
        state.winner = max(scores, key=scores.get)
    state.final_scores = scores
```

And add `final_scores` to `to_dict()`.

**Step 4: Run test to verify pass**

```bash
cd /home/onewing/cuberail/backend
python -m pytest tests/test_northern_pacific.py::test_final_score_includes_shares -v
```

Expected: PASS

**Step 5: Commit**

```bash
cd /home/onewing/cuberail
git add backend/app/engine/games/northern_pacific.py backend/tests/test_northern_pacific.py
git commit -m "feat: add final score calculation including share value"
```

---

#### Task 5: Run all existing tests to confirm no regressions

**Objective:** Make sure existing game logic still works.

```bash
cd /home/onewing/cuberail/backend
python -m pytest tests/ -v
```

Expected: ALL PASS

---

### Phase 3: Stock Round Cycle (Backend)

#### Task 6: Add stock_round phase between turns

**Objective:** After each train move (or every N moves), insert a stock round
where players can buy/shares. The stock round cycles through all players before
returning to normal play.

**Files:**
- Modify: `backend/app/engine/games/northern_pacific.py`
- Modify: `backend/tests/test_northern_pacific.py`

**Step 1: Write failing test**

```python
def test_stock_round_phase():
    engine = NPEngine()
    state = engine.setup_game(["alice", "bob"])

    # Stock round should trigger after first N moves (or configurable)
    # For now: stock round after every 3 city visits
    assert state.moves_since_stock_round == 0
```

**Step 2: Design the stock round flow**

In real Northern Pacific, the game alternates:
1. Move train phase (players take turns moving the train)
2. Stock round (players buy/sell shares)
3. Repeat until train reaches Seattle/Portland

Simplified approach for digital:
- Stock round triggers after every 3 train moves
- During stock round, each player gets 1 buy action in turn order
- Share prices from the move phase are used

Add to NPState:

```python
self.moves_since_stock_round = 0
self.stock_round_active = False
self.stock_round_player_index = 0
self.moves_before_stock_round = 3  # Configurable
```

In `apply_move`, after each successful move_train:

```python
if action_type == "move_train":
    # ... existing move logic ...
    state.moves_since_stock_round += 1
    if state.moves_since_stock_round >= state.moves_before_stock_round:
        state.phase = "stock_round"
        state.stock_round_active = True
        state.stock_round_player_index = 0
        # Set current player to first in stock round
        state.current_player_index = state.stock_round_player_index
```

For buy_share during stock round:

```python
elif action_type == "buy_share":
    # ... existing buy logic ...
    if state.stock_round_active:
        state.stock_round_player_index += 1
        if state.stock_round_player_index >= len(state.turn_order):
            # End stock round
            state.stock_round_active = False
            state.phase = "main"
            state.moves_since_stock_round = 0
            state.current_player_index = 0  # Reset to first player
        else:
            state.current_player_index = state.stock_round_player_index
```

For `pass` during stock round:

```python
elif action_type == "pass":
    if state.stock_round_active:
        # Skip this player's stock buy
        state.stock_round_player_index += 1
        if state.stock_round_player_index >= len(state.turn_order):
            state.stock_round_active = False
            state.phase = "main"
            state.moves_since_stock_round = 0
        else:
            state.current_player_index = state.stock_round_player_index
    else:
        state.current_player_index = (state.current_player_index + 1) % len(state.turn_order)
```

Update `get_current_actor` logic if needed.

**Step 3: Run tests**

```bash
cd /home/onewing/cuberail/backend
python -m pytest tests/ -v
```

Expected: ALL PASS

**Step 4: Commit**

```bash
cd /home/onewing/cuberail
git add backend/app/engine/games/northern_pacific.py
git commit -m "feat: add stock round phase between train moves"
```

---

### Phase 4: Stock Round Frontend

#### Task 7: Show share values and enable share buying in UI

**Objective:** The NorthernPacificBoard should display share values for each
city and allow buying shares during stock round phases.

**Files:**
- Modify: `frontend/src/components/NorthernPacificBoard.tsx`

**Step 1: Update the controls panel**

When `gameState.phase === 'stock_round'`, show stock round controls instead of
normal controls:

```tsx
{gameState.phase === 'stock_round' ? (
  <div className="bg-white p-4 rounded shadow">
    <h3 className="font-bold border-b pb-2 mb-2">Stock Round</h3>
    <p className="text-sm mb-2">Buy shares in invested cities:</p>
    {Object.entries(gameState.investments || {}).map(([city, owner]) => {
      const myInvestment = owner === user?.id;
      const value = gameState.share_values?.[city] ?? 10;
      const myShares = gameState.shares_held?.[user?.id]?.[city] ?? 0;
      return (
        <div key={city} className="flex justify-between text-sm items-center py-1">
          <span>{city} (${value})</span>
          {myInvestment && (
            <button
              onClick={() => sendMove('buy_share', { city, player: user?.id })}
              disabled={!isMyTurn}
              className="bg-green-600 text-white px-2 py-0.5 rounded text-xs disabled:opacity-40"
            >
              Buy ({myShares})
            </button>
          )}
        </div>
      );
    })}
    <button
      onClick={() => sendMove('pass', {})}
      className="mt-2 bg-gray-500 text-white px-3 py-1 rounded text-sm w-full"
    >
      Pass
    </button>
  </div>
) : ( /* existing controls */ )}
```

**Step 2: Show share values on city nodes**

Under each city circle, show the current share value:

```tsx
<text
  x={px.x}
  y={px.y + 18}
  textAnchor="middle"
  fontSize={8}
  fill="#666"
  style={{ userSelect: 'none', pointerEvents: 'none' }}
>
  ${gameState.share_values?.[city] ?? 10}
</text>
```

**Step 3: Verify TypeScript compiles**

```bash
cd /home/onewing/cuberail/frontend
npx tsc --noEmit
```

Expected: No errors

**Step 4: Commit**

```bash
cd /home/onewing/cuberail
git add frontend/src/components/NorthernPacificBoard.tsx
git commit -m "feat: add stock round UI with share buying and price display"
```

---

### Phase 5: Lobby & Game Lifecycle

#### Task 8: Add Start Game button to Lobby

**Objective:** After creating a game, the creator should be able to start it
from the lobby. The open games listing should show a "Start" button for the
creator and "Join" for others.

**Files:**
- Modify: `frontend/src/components/Lobby.tsx`

**Step 1: Update the open games list**

```tsx
{openGames.map((g) => (
  <div key={g.id} className="flex items-center justify-between border border-gray-200 rounded p-3 hover:bg-gray-50">
    <div>
      <span className="font-medium">{gameTypeLabel(g.game_type)}</span>
      <span className={`ml-2 text-xs px-2 py-0.5 rounded ${g.mode === 'async' ? 'bg-blue-100 text-blue-700' : 'bg-green-100 text-green-700'}`}>
        {g.mode}
      </span>
      <div className="text-sm text-gray-600 mt-1">
        by {g.created_by} &middot; {g.human_players}/{g.total_players} players
      </div>
    </div>
    <div className="flex gap-2">
      {g.created_by === currentUsername && (
        <button
          onClick={() => handleStartGame(g.id)}
          className="bg-green-600 text-white px-4 py-1.5 rounded text-sm hover:bg-green-700 cursor-pointer"
        >
          Start
        </button>
      )}
      <button
        onClick={() => handleJoinGame(g.id)}
        className="bg-indigo-600 text-white px-4 py-1.5 rounded text-sm hover:bg-indigo-700 cursor-pointer"
      >
        Join
      </button>
    </div>
  </div>
))}
```

Add the handler:

```tsx
const handleStartGame = async (gameId: string) => {
  try {
    await axios.post(
      `${API_BASE}/api/games/${gameId}/start`,
      {},
      { headers: { Authorization: `Bearer ${token}` } }
    );
    navigate(`/game/${gameId}`);
  } catch (err) {
    console.error('Failed to start game', err);
  }
};
```

Need to get current username from the auth store, and include it in the GET
response (add `created_by_id` to the response or pass `currentUsername` from
the store).

**Step 2: Add created_by_id to list_games response**

In `backend/app/api/games.py`, add `"created_by_id": str(g.created_by_id)` to
the game dict in `list_games`.

**Step 3: Verify TypeScript compiles**

```bash
cd /home/onewing/cuberail/frontend
npx tsc --noEmit
```

Expected: No errors

**Step 4: Commit**

```bash
cd /home/onewing/cuberail
git add frontend/src/components/Lobby.tsx backend/app/api/games.py
git commit -m "feat: add Start Game button for game creator in lobby"
```

---

### Phase 6: Async Bot Processing

#### Task 9: Make bot processing asynchronous

**Objective:** `_process_bot_turns` runs synchronously in the request handler
and can timeout. Move it to a background task.

**Files:**
- Modify: `backend/app/api/games.py`
- Modify: `backend/app/main.py` (add BackgroundTasks import if not present)

**Step 1: Use FastAPI BackgroundTasks**

Change the bot processing calls to use `BackgroundTasks`:

```python
from fastapi import BackgroundTasks

@router.post("/{game_id}/start")
async def start_game(
    game_id: str,
    background_tasks: BackgroundTasks,
    Authorize: AuthJWT = Depends(),
    db: AsyncSession = Depends(get_db),
):
    # ... existing logic ...
    background_tasks.add_task(
        _process_bot_turns, game_id, engine, state, db, sio, 1
    )
    return {"message": "Started"}
```

Same for the `make_move` endpoint.

**Step 2: Handle async session in background task**

Background tasks need their own DB session. Modify `_process_bot_turns` to
create a new session:

```python
async def _process_bot_turns(
    game_id: str, engine, state, db: AsyncSession, sio, next_move_num: int,
):
    from app.db import async_session
    async with async_session() as bg_db:
        # Use bg_db instead of db for all DB operations
        ...
```

**Step 3: Run tests**

```bash
cd /home/onewing/cuberail/backend
python -m pytest tests/ -v
```

Expected: ALL PASS

**Step 4: Commit**

```bash
cd /home/onewing/cuberail
git add backend/app/api/games.py
git commit -m "fix: move bot processing to background tasks to avoid timeouts"
```

---

### Phase 7: Deployment Prep

#### Task 10: Add frontend .env.example and deployment config

**Objective:** Make it easy to deploy the app on the VPS behind Pangolin/Caddy.

**Files:**
- Create: `frontend/.env.example`
- Create: `docker-compose.prod.yml`
- Create: `backend/.env.example`

**Step 1: Create `.env.example` files**

`frontend/.env.example`:

```env
VITE_API_URL=https://cuberail.yourdomain.com/api
VITE_WS_URL=wss://cuberail.yourdomain.com
```

`backend/.env.example`:

```env
DATABASE_URL=postgresql+asyncpg://cube_user:cube_password@db:5432/cube_db
SECRET_KEY=generate-a-real-secret-key
RESEND_API_KEY=optional
```

**Step 2: Create `docker-compose.prod.yml`**

```yaml
version: '3.8'
services:
  db:
    image: postgres:15
    environment:
      POSTGRES_USER: cube_user
      POSTGRES_PASSWORD: cube_password
      POSTGRES_DB: cube_db
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  backend:
    build: ./backend
    ports:
      - "8098:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://cube_user:cube_password@db:5432/cube_db
      SECRET_KEY: ${SECRET_KEY}
    depends_on:
      - db
    restart: unless-stopped

  frontend:
    build: ./frontend
    ports:
      - "8099:80"
    restart: unless-stopped

volumes:
  postgres_data:
```

**Step 3: Check if a Dockerfile exists for frontend/backend**

Create if missing:

`frontend/Dockerfile`:

```dockerfile
FROM node:20 AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
ARG VITE_API_URL
ARG VITE_WS_URL
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_WS_URL=$VITE_WS_URL
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

`backend/Dockerfile`:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Step 4: Commit**

```bash
cd /home/onewing/cuberail
git add frontend/.env.example backend/.env.example docker-compose.prod.yml frontend/Dockerfile backend/Dockerfile
git commit -m "docs: add deployment configuration and examples"
```

---

### Phase 8: Final Verification

#### Task 11: Full integration test

**Objective:** Verify everything works end-to-end.

**Steps:**

1. Start backend: `cd backend && uvicorn app.main:app --reload`
2. Start frontend: `cd frontend && npx vite`
3. Create a user, create a game, start it, play through
4. Verify stock rounds trigger after N moves
5. Verify share buying works
6. Verify game-over shows winner with final score breakdown
7. Verify Socket.IO events update the UI in real-time

---

**Plan complete.** Ready to execute using subagent-driven-development — dispatch
a fresh subagent per task with full context, spec compliance review after each,
code quality review after spec passes. Proceed task-by-task in phases.
