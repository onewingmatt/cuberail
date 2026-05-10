# Prussian Rails — Full Rebuild Plan

**Goal:** Replace the placeholder node-edge Prussian Rails implementation with a hex-grid-based proper implementation matching the Rio Grande Games 2023 rules.

**Context:** Current `prussian_rails.json` has fake coordinates, wrong cities, and a bidirectional graph. The real game uses a hex map of 19th-century Germany with terrain-based track building, income tracks, dividend triggers, cup-draw turn order, and 8 companies with special abilities.

## Map Data

The hex map needs:
- Axial hex coordinates (q, r) for ~200+ hexes
- Terrain per hex: plains ($2), hills ($3), mountains ($4), Berlin approach ($2), urban (variable)
- Urban hexes (cities): name, income value
- The 8 company home cities
- Berlin approaches (special hexes surrounding Berlin)

Initial coordinates will be approximated from real German geography. Calibration pass after rendering.

## Backend — Files to Create/Modify

### 1. Map Data: `backend/app/engine/maps/prussian_rails.json` → `prussian_rails_hex.json`
New format with hex grid data:
```json
{
  "name": "prussian_rails",
  "grid_type": "hex_axial",
  "board_width": 1200,
  "board_height": 900,
  "background_image": "",
  "hexes": {
    "0,0": {"terrain": "plains", "city": null},
    "5,3": {"terrain": "urban", "city": "Berlin", "income": 3},
    ...
  },
  "companies": [...],
  "berlin_approaches": ["8,5", "8,6", ...]
}
```

### 2. Engine: `backend/app/engine/games/prussian_rails.py` — Full rewrite

New state model:
- `phase`: "initial_auction" | "round"
- `round_phase`: "determine_order" | "player_turns"
- `turn_order`: list drawn from cup
- `cup`: dict of player_id → disk count
- `player_income`: dict of player_id → income
- `player_cash`: dict of player_id → cash  
- `shares`: dict of player_id → {company_id: count}
- `company_treasury`: dict of company_id → cash
- `company_income`: dict of company_id → current income
- `company_track_remaining`: dict of company_id → remaining cubes
- `board`: dict of hex_coord → list of company_ids
- `connected_companies`: set of company pairs already connected (for dividend tracking)
- `companies`: dict of Company objects with special abilities

Actions:
- `bid` / `pass` — during initial auction phase
- `auction_share` — during main phase, offer unsold share
- `build_track` — place 1-4 cubes on hex path
- `pass` — skip turn

### 3. Company definitions: 8 companies with abilities

| Company | Home | Color | Income | Cubes | Ability |
|---------|------|-------|--------|-------|---------|
| Preußische Ostbahn | Königsberg | #000000 | 3 | 20 | Build up to 4 |
| Niederschlesische | Breslau | #8B4513 | 2 | 17 | No city penalty |
| Sächsische | Leipzig | #FFA500 | 1 | 11 | Only 1-2 cubes |
| Bayerische | München | #0000FF | 3 | 16 | $1 discount/hex |
| Main-Wesel | Kassel | #DAA520 | 2 | 14 | Double best city income |
| Badische | Mannheim | #FF0000 | 1 | 15 | One free rural/round |
| Köln-Mindener | Essen | #800080 | 1 | 12 | Max $5/build |
| Berlin-Hamburger | Wittenberge | #006400 | 1 | 13 | Must connect both Berlin+Hamburg |

### 4. Route validation: `_validate_track_path(state, company, hex_path)`
- Must connect to company's existing network (or home city)
- Terrain costs summed
- City penalties for stacking
- Hex availability (rural blocked after first company, Berlin approach limits)
- Company ability applied (discount, free rural, max spend, etc.)
- Treasury check

### 5. Dividend logic: when company A connects to company B (direct hex adjacency between their networks)
- All 8 companies pay dividends = company_income × shares_owned
- Connecting company pays DOUBLE
- Track connected pairs to avoid re-triggering

## Frontend — Files to Modify

### 1. `frontend/src/components/PrussianRailsBoard.tsx` — Full rewrite

New rendering:
- Hex grid SVG (flat-top hexagons)
- Terrain coloring (plains=light green, hills=tan, mountains=gray, urban=light yellow, berlin_approach=light red)
- City names on urban hexes
- Track cubes rendered in company colors on hexes
- Company home city indicators (star icon)

Interactive elements:
- Click hex → show terrain, cost, available companies
- Select company + click adjacent hex → propose track build
- Multi-hex path selection for 1-4 cube builds

Sidebar:
- Phase indicator (initial auction vs round)
- Auction panel (bid/pass)
- Company selector + hex path builder
- Player info (cash, shares, income)
- Income tracks per company

### 2. `frontend/src/components/HexGridBoard.tsx` — New component
Reusable hex grid renderer with:
- Flat-top hex geometry (width, height, spacing calculations)
- Zoom/pan (reuse from InteractiveMapBoard)
- Hex click detection (point-in-hex math)
- Terrain color mapping
- Track cube rendering per hex

## API — Files to Modify

### 1. `backend/app/api/games.py`
- Update `create_game` for Prussian Rails game type
- Update `apply_move` dispatch for new actions
- Add initial auction handling

### 2. `backend/app/socket_handlers.py`
- Wire Prussian Rails state updates

## Test — New File

### `backend/tests/test_prussian_rails_hex.py`
- Track building validation (terrain costs, city penalties)
- Company ability tests (Ostbahn 4 track, Bayerische discount, etc.)
- Dividend calculation
- Turn order generation
- Income tracking

## Slices (Execution Order)

1. **Hex map data + geometry utils** — Create `prussian_rails_hex.json` with city positions, hex grid utils
2. **Engine rewrite** — New `PrussianRailsState`, `PrussianRailsEngine`, company abilities
3. **API wiring** — Update game creation, move handling, state serialization
4. **Frontend hex renderer** — `HexGridBoard` component
5. **Frontend Prussian Rails board** — Rewrite with hex grid + sidebar
6. **Calibration** — City position nudging after visual review
7. **Tests** — Validation of all mechanics
8. **Bot AI** — Basic AI for Prussian Rails
