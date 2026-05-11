"""
Prussian Rails game engine — Rio Grande Games 2023 edition.

Hex-based track building with terrain costs, company income tracks,
dividend payouts, cup-draw turn order, and 8 companies with historical
special abilities.
"""

import random
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass, field

from app.engine.core import GameEngine, GameState, Company, AuctionManager, StockMarket
from app.engine.utils.hex_grid import (
    HexGrid, hex_neighbors, hex_distance, is_adjacent,
)
from app.engine.utils.map_loader import MapLoader


# ─── Company definitions ───────────────────────────────────────────

COMPANY_DEFS = [
    {"id": "Preußische Ostbahn", "color": "#1a1a1a", "home": "Königsberg",
     "start_income": 3, "track_count": 20, "ability": "build_4"},
    {"id": "Niederschlesisch-Märkische", "color": "#8B4513", "home": "Breslau",
     "start_income": 2, "track_count": 17, "ability": "no_city_penalty"},
    {"id": "Königlich-Sächsische", "color": "#FF8C00", "home": "Leipzig",
     "start_income": 1, "track_count": 11, "ability": "build_1_2"},
    {"id": "Königlich-Bayerische", "color": "#0000FF", "home": "München",
     "start_income": 3, "track_count": 16, "ability": "discount_1"},
    {"id": "Main-Weser-Bahn", "color": "#DAA520", "home": "Kassel",
     "start_income": 2, "track_count": 14, "ability": "double_best_income"},
    {"id": "Großherzoglich Badische", "color": "#CC0000", "home": "Mannheim",
     "start_income": 1, "track_count": 15, "ability": "free_rural"},
    {"id": "Köln-Mindener", "color": "#800080", "home": "Köln",
     "start_income": 1, "track_count": 12, "ability": "max_spend_5"},
    {"id": "Berlin-Hamburger", "color": "#006400", "home": "Hamburg",
     "start_income": 1, "track_count": 13, "ability": "connect_both"},
]

STARTING_MONEY = {3: 40, 4: 30, 5: 24}


# ─── State ──────────────────────────────────────────────────────────

class PrussianRailsState(GameState):
    """Full game state for Prussian Rails."""

    def __init__(self, players: List[str]):
        self.turn_order = players
        self.current_player_index = 0
        self.active_player_stack: List[str] = []
        self.is_game_over = False
        self.phase = "auction"
        self.round_phase: Optional[str] = None

        # Player resources
        num_players = len(players)
        self.player_cash: Dict[str, int] = {p: STARTING_MONEY.get(num_players, 30) for p in players}
        self.player_income: Dict[str, int] = {p: 0 for p in players}
        self.shares: Dict[str, Dict[str, int]] = {p: {} for p in players}

        # Company tracking
        self.companies: Dict[str, Company] = {}
        self.company_income: Dict[str, int] = {}
        self.company_treasury: Dict[str, int] = {}
        self.company_home: Dict[str, str] = {}
        self.company_ability: Dict[str, str] = {}
        self.company_start_income: Dict[str, int] = {}

        for cdef in COMPANY_DEFS:
            cid = cdef["id"]
            self.companies[cid] = Company(
                id=cid,
                color=cdef["color"],
                initial_shares=3,
                initial_treasury=0,
                max_track=cdef["track_count"],
            )
            self.company_income[cid] = cdef["start_income"]
            self.company_treasury[cid] = 0
            self.company_home[cid] = cdef["home"]
            self.company_ability[cid] = cdef["ability"]
            self.company_start_income[cid] = cdef["start_income"]

        # Board state: hex_coord ("q,r") -> list of company_ids present
        self.board: Dict[str, List[str]] = {}

        # Initial auction queue (order: Ostbahn → ... → Berlin-Hamburger)
        self.company_auction_queue: List[str] = [c["id"] for c in COMPANY_DEFS]
        self.auction_state: Optional[Dict] = None

        # Track which company pairs have already triggered dividends
        self.connected_pairs: Set[Tuple[str, str]] = set()

        # Track which companies have used their Berlin approach (1 per game)
        self.berlin_approach_used: Dict[str, bool] = {c["id"]: False for c in COMPANY_DEFS}

        # Round management
        self.current_round_number = 0
        self.player_turn_order: List[str] = []  # drawn from cup for this round
        self.turn_position = 0  # index into player_turn_order for current action

        # Cup data for turn order determination
        self.cup_pending: Dict[str, int] = {}  # player_id -> disk count (set at round start)

        # Income bonus tracking
        self._main_wesel_best_city_income: Dict[str, int] = {}  # company -> best city income

        # Move history for frontend display
        self.move_history: List[str] = []

        # Map
        self._raw_map = MapLoader.load_map("prussian_rails_hex")
        self.hex_grid = HexGrid(
            hexes=self._raw_map.get("hexes", {}),
            berlin_approaches=self._raw_map.get("berlin_approach_hexes", []),
            terrain_costs=self._raw_map.get("terrain_costs", {}),
        )

    def get_current_actor(self) -> Optional[str]:
        if self.auction_state:
            if self.active_player_stack:
                return self.active_player_stack[-1]
            return self.auction_state.get("bidders", [None])[0] if self.auction_state.get("bidders") else None
        if self.phase == "round" and self.round_phase == "player_turns":
            if self.player_turn_order and self.turn_position < len(self.player_turn_order):
                return self.player_turn_order[self.turn_position]
        return None

    def to_dict(self) -> Dict[str, Any]:
        # Convert board dict keys to serializable format
        board_serializable = list(self.board.items())

        return {
            "current_player": self.get_current_actor(),
            "phase": self.phase,
            "round_phase": self.round_phase,
            "round_number": self.current_round_number,
            "player_cash": self.player_cash,
            "player_income": self.player_income,
            "shares": self.shares,
            "companies": {k: v.to_dict() for k, v in self.companies.items()},
            "company_income": self.company_income,
            "company_treasury": self.company_treasury,
            "company_home": self.company_home,
            "company_ability": self.company_ability,
            "company_start_income": self.company_start_income,
            "board": board_serializable,
            "auction_state": self.auction_state,
            "game_over": self.is_game_over,
            "map_data": self._raw_map,
            "player_turn_order": self.player_turn_order,
            "turn_position": self.turn_position,
            "connected_pairs": [[a, b] for a, b in self.connected_pairs],
            "move_history": self.move_history[-30:],  # last 30 entries
        }


# ─── Engine ─────────────────────────────────────────────────────────

class PrussianRailsEngine(GameEngine, AuctionManager, StockMarket):
    """Full rules engine for Prussian Rails."""

    def setup_game(self, players: List[str]) -> PrussianRailsState:
        state = PrussianRailsState(players)
        # Start the first initial auction with deterministic starter
        # (first player in turn order always starts first auction;
        #  subsequent auction starters are determined by previous winner)
        first_company = state.company_auction_queue.pop(0)
        starter = state.turn_order[0]
        bidder_order = self._build_bidder_order(state.turn_order, starter)
        self.start_auction(state, first_company, bidder_order, starting_bid=5)
        return state

    # ── Move dispatch ──────────────────────────────────────────────

    def apply_move(
        self, state: PrussianRailsState, player_id: str,
        action_type: str, payload: dict
    ) -> PrussianRailsState:
        if state.is_game_over:
            raise ValueError("Game is already over")

        if state.get_current_actor() != player_id:
            raise ValueError(
                f"Not your turn. Expected {state.get_current_actor()}, got {player_id}"
            )

        if state.phase == "auction" and state.round_phase is None:
            self._handle_initial_auction_move(state, player_id, action_type, payload)
        elif state.phase == "round":
            self._handle_round_move(state, player_id, action_type, payload)
        else:
            raise ValueError(f"Unknown phase: {state.phase}")

        return state

    # ── Initial auction ─────────────────────────────────────────────

    def _handle_initial_auction_move(
        self, state: PrussianRailsState, player_id: str,
        action_type: str, payload: dict
    ):
        if action_type == "bid":
            bid_amount = payload.get("bid", 0)
            if state.player_cash[player_id] < bid_amount:
                raise ValueError("Not enough cash to bid that amount")
            concluded = self.handle_auction_bid(state, player_id, bid_amount)
            if concluded:
                self._resolve_auction(state)
            else:
                # Auction continues — advance to next bidder
                if state.active_player_stack and player_id in state.active_player_stack:
                    state.active_player_stack.remove(player_id)
                    state.active_player_stack.insert(0, player_id)

        elif action_type == "pass":
            auction = state.auction_state
            # If the last remaining bidder passes without any bid placed,
            # the company goes unsold — skip to the next auction
            if len(auction["bidders"]) == 1 and auction["highest_bidder"] is None:
                company_id = auction["item"]
                state.move_history.append(f"No bids for {company_id} — unsold")
                state.auction_state = None
                state.active_player_stack = []
                if state.company_auction_queue:
                    next_company = state.company_auction_queue.pop(0)
                    bidder_order = self._build_bidder_order(
                        state.turn_order, state.turn_order[0]
                    )
                    self.start_auction(state, next_company, bidder_order, starting_bid=5)
                else:
                    state.phase = "round"
                    self._start_new_round(state)
            else:
                concluded = self.handle_auction_pass(state, player_id)
                if concluded:
                    self._resolve_auction(state)

        else:
            raise ValueError(f"Invalid action during initial auction: {action_type}")

    def _resolve_auction(self, state: PrussianRailsState):
        """Resolve the current auction: assign share, fund treasury, queue next or start rounds."""
        auction = state.auction_state
        if not auction:
            return

        winner = auction.get("highest_bidder")
        bid = auction.get("current_bid", 0)
        company_id = auction["item"]

        if winner and bid >= 1:
            # Winner pays bid from personal cash into company treasury
            state.player_cash[winner] -= bid
            state.company_treasury[company_id] += bid

        # Assign share: one share of this company (starting from unissued 3→2 or 2→1 or 1→0)
        company = state.companies[company_id]
        company.unissued_shares -= 1

        # Give share to winner (or free to first bidder if no one bid)
        if winner and bid >= 1:
            share_recipient = winner
        else:
            # Nobody bid — first person in the bid order gets it free
            share_recipient = (auction.get("passed_bidders") or auction.get("bidders") or [None])[0]
        if share_recipient:
            if company_id not in state.shares[share_recipient]:
                state.shares[share_recipient][company_id] = 0
            state.shares[share_recipient][company_id] += 1

            # Update player income immediately (share value = company income)
            state.player_income[share_recipient] += state.company_income[company_id]

            state.move_history.append(
                f"{share_recipient} won {company_id} for ${bid}"
            )

        # Cleanup
        state.auction_state = None
        state.active_player_stack = []

        # Place company's home hex on the board (free, part of initial network)
        home_city = state.company_home.get(company_id)
        if home_city:
            home_hex = state.hex_grid.find_city_hex(home_city)
            if home_hex:
                hk = f"{home_hex[0]},{home_hex[1]}"
                if hk not in state.board:
                    state.board[hk] = []
                if company_id not in state.board[hk]:
                    state.board[hk].append(company_id)

        # Determine next auction starter (winner of this auction starts next)
        next_starter = share_recipient if share_recipient else state.turn_order[0]

        if state.company_auction_queue:
            # Continue initial auctions
            next_company = state.company_auction_queue.pop(0)
            # Build bidder order starting with previous winner
            bidder_order = self._build_bidder_order(state.turn_order, next_starter)
            self.start_auction(state, next_company, bidder_order, starting_bid=5)
        else:
            # All initial auctions done → start first round
            state.phase = "round"
            self._start_new_round(state)

    def _build_bidder_order(self, players: List[str], starter: str) -> List[str]:
        """Build bidder order starting from starter, wrapping around.
        Returns reversed order so the first bidder is the last element
        (AuctionManager pops from the end of active_player_stack)."""
        idx = players.index(starter) if starter in players else 0
        order = players[idx:] + players[:idx]
        order.reverse()  # last in list acts first
        return order

    # ── Round structure ─────────────────────────────────────────────

    def _start_new_round(self, state: PrussianRailsState):
        """Initialize a new round: pay round income, determine turn order, reset position."""
        # Pay accumulated income to all players (round-end income)
        if state.current_round_number >= 1:
            for p in state.turn_order:
                income = state.player_income.get(p, 0)
                state.player_cash[p] = state.player_cash.get(p, 0) + income
                state.move_history.append(
                    f"{p} received ${income} income (Round {state.current_round_number} end)"
                )

        state.current_round_number += 1
        state.round_phase = "determine_order"
        state.turn_position = 0
        state.active_player_stack = []

        # Phase 1: Determine player turn order (cup draw)
        self._determine_turn_order(state)
        # Phase 2: Player turns
        state.round_phase = "player_turns"

    def _determine_turn_order(self, state: PrussianRailsState):
        """
        Cup-draw mechanism:
        - Player(s) with highest income put 1 disk in cup
        - Second highest income: 2 disks
        - Third: 3 disks, etc.
        - Draw as many disks as there are players to form turn order.
        """
        players = state.turn_order
        if len(players) <= 1:
            state.player_turn_order = players.copy()
            return

        # Sort by income ascending (lowest income = most disks)
        incomes = sorted(set(state.player_income[p] for p in players))
        # Map: income → disk count (highest income = 1 disk, next = 2, etc.)
        disk_count = {}
        for rank, inc in enumerate(reversed(incomes)):
            disk_count[inc] = rank + 1

        # Build the cup
        cup: List[str] = []
        for p in players:
            inc = state.player_income[p]
            count = disk_count.get(inc, 5)
            cup.extend([p] * count)
        # Deterministic shuffle for replay consistency (same players + round = same order)
        seed_key = "|".join(sorted(players)) + str(state.current_round_number)
        random.Random(seed_key).shuffle(cup)

        # Draw N disks (N = number of players)
        drawn = cup[:len(players)]
        state.player_turn_order = drawn
        state.cup_pending = {p: disk_count.get(state.player_income[p], 5) for p in players}

    def _advance_turn(self, state: PrussianRailsState):
        """Move to the next player's turn in the round. Start new round if all done."""
        state.turn_position += 1
        if state.turn_position >= len(state.player_turn_order):
            # All players have acted this round
            # For multiplayer: start a new round
            # For single-player: just reset position (player keeps building until pass)
            if len(state.player_turn_order) <= 1:
                state.turn_position = 0
            else:
                if self._check_game_over(state):
                    return
                self._start_new_round(state)

    def _check_game_over(self, state: PrussianRailsState) -> bool:
        """Check if game-end conditions are met. Sets is_game_over if so."""
        # Condition 1: All companies have exhausted track cubes
        all_exhausted = all(
            c.track_remaining == 0 for c in state.companies.values()
        )
        # Condition 2: Any company has reached Berlin
        berlin_reached = any(
            state.berlin_approach_used.get(cid, False)
            for cid in state.companies
        )
        # Condition 3: Maximum rounds reached (safety limit)
        max_rounds = 50
        if all_exhausted or berlin_reached or state.current_round_number >= max_rounds:
            state.is_game_over = True
            return True
        return False

    # ── Round moves ─────────────────────────────────────────────────

    def _handle_round_move(
        self, state: PrussianRailsState, player_id: str,
        action_type: str, payload: dict
    ):
        if state.round_phase != "player_turns":
            raise ValueError("Not in player turns phase")

        # If there's an active auction during a round, route bid/pass to auction handlers
        if state.auction_state:
            if action_type == "bid":
                self._handle_round_auction_bid(state, player_id, payload)
                return
            elif action_type == "pass":
                self._handle_round_auction_pass(state, player_id)
                return
            else:
                raise ValueError(f"Cannot {action_type} during an active auction; only bid or pass")

        if action_type == "pass":
            # For single-player: passing ends the round
            if len(state.player_turn_order) <= 1:
                if self._check_game_over(state):
                    return
                self._start_new_round(state)
            else:
                # Multiplayer: advance to next player
                self._advance_turn(state)

        elif action_type == "auction_share":
            company_id = payload.get("company")
            if company_id not in state.companies:
                raise ValueError("Invalid company")
            if state.companies[company_id].unissued_shares <= 0:
                raise ValueError("No unissued shares left")
            # Check that a third share isn't auctioned before all have 2
            unsold_3 = any(
                state.companies[cid].unissued_shares == 1  # 2 of 3 sold
                for cid in state.companies
            )
            if state.companies[company_id].unissued_shares == 1 and not unsold_3:
                raise ValueError(
                    "Cannot auction a third share until all companies have sold their second share"
                )

            # Start auction: bidder order starts with offering player
            bidder_order = self._build_bidder_order(state.turn_order, player_id)
            state.phase = "round"  # stays in round, but we enter auction sub-phase
            # Set auction state manually (not via start_auction which changes phase)
            state.auction_state = {
                "item": company_id,
                "current_bid": 0,
                "highest_bidder": None,
                "bidders": bidder_order.copy(),
                "passed_bidders": [],
                "return_to_player": player_id,  # who offered it
            }
            state.active_player_stack = bidder_order.copy()

        elif action_type == "build_track":
            hex_path = payload.get("hex_path", [])  # list of [q, r] pairs
            company_id = payload.get("company")
            self._do_build_track(state, player_id, company_id, hex_path)
            self._advance_turn(state)

        else:
            raise ValueError(f"Unknown action: {action_type}")

    def _handle_round_auction_bid(
        self, state: PrussianRailsState, player_id: str, payload: dict
    ):
        auction = state.auction_state
        if not auction:
            raise ValueError("No active auction")

        bid = payload.get("bid", 0)
        concluded = self.handle_auction_bid(state, player_id, bid)
        if concluded:
            self._resolve_round_auction(state)

    def _handle_round_auction_pass(self, state: PrussianRailsState, player_id: str):
        """Called when player passes during a round auction."""
        auction = state.auction_state
        if not auction:
            raise ValueError("No active auction")

        auction["bidders"].remove(player_id)
        if player_id in state.active_player_stack:
            state.active_player_stack.remove(player_id)

        if len(auction["bidders"]) <= 1 and auction["highest_bidder"] is not None:
            self._resolve_round_auction(state)
        elif len(auction["bidders"]) == 0:
            self._resolve_round_auction(state)

    def _resolve_round_auction(self, state: PrussianRailsState):
        """Resolve a round auction: assign share, fund treasury."""
        auction = state.auction_state
        if not auction:
            return

        company_id = auction["item"]
        winner = auction.get("highest_bidder")
        bid = auction.get("current_bid", 0)

        if winner and bid >= 1:
            state.player_cash[winner] -= bid
            state.company_treasury[company_id] += bid

        company = state.companies[company_id]
        company.unissued_shares -= 1

        recipient = winner if winner else auction.get("return_to_player")
        if recipient:
            if company_id not in state.shares[recipient]:
                state.shares[recipient][company_id] = 0
            state.shares[recipient][company_id] += 1
            state.player_income[recipient] += state.company_income[company_id]

        # Cleanup
        state.auction_state = None
        state.active_player_stack = []

        # Advance turn after auction
        self._advance_turn(state)

    # ── Track building ──────────────────────────────────────────────

    def _do_build_track(
        self, state: PrussianRailsState, player_id: str,
        company_id: str, hex_path: List[List[int]]
    ):
        """
        Build track cubes for a company along a hex path.
        Validation:
        - Player owns at least 1 share of the company
        - Path connects to company's existing network (or home city)
        - Each hex is a valid, playable hex
        - Terrain costs are paid from company treasury
        - City penalties applied for stacking
        - Company abilities applied
        """
        if company_id not in state.companies:
            raise ValueError("Invalid company")

        player_shares = state.shares.get(player_id, {}).get(company_id, 0)
        if player_shares <= 0:
            raise ValueError("Must own at least one share to build track")

        company = state.companies[company_id]
        ability = state.company_ability.get(company_id)
        home_hex = state.hex_grid.find_city_hex(state.company_home[company_id])

        if not hex_path:
            raise ValueError("Must specify at least one hex to build")

        # Convert path to tuples
        path = [tuple(h) for h in hex_path]

        # Check max cubes per build based on ability
        max_cubes = 3
        if ability == "build_4":
            max_cubes = 4
        elif ability == "build_1_2":
            max_cubes = 2

        if len(path) > max_cubes:
            raise ValueError(f"{company_id} can only build up to {max_cubes} cubes per turn")

        if company.track_remaining < len(path):
            raise ValueError(f"Only {company.track_remaining} track cubes remaining")

        # Validate path continuity and connectivity
        for i, hex_coord in enumerate(path):
            q, r = hex_coord
            h = state.hex_grid.get_hex(q, r)
            if not h or not state.hex_grid.is_playable(q, r):
                raise ValueError(f"Hex ({q},{r}) is not playable")

            # Cannot build on a hex already occupied by this company
            k = f"{q},{r}"
            if k in state.board and company_id in state.board[k]:
                raise ValueError(f"Hex ({q},{r}) already has {company_id} track")

            # Check adjacency: each hex must be adjacent to previous
            if i > 0 and not is_adjacent(path[i - 1], hex_coord):
                raise ValueError(f"Path must be adjacent hexes; ({path[i-1]}) to ({hex_coord}) is not")

            # Each hex must be adjacent to an already-owned hex of this company
            # (or the home city if this is the first build)
            if i == 0:
                connected_to_network = False
                # Check if adjacent to any existing company hex
                for nq, nr in hex_neighbors(q, r):
                    nkey = f"{nq},{nr}"
                    if nkey in state.board and company_id in state.board[nkey]:
                        connected_to_network = True
                        break
                # Check if this hex is the home city or adjacent to it
                if home_hex:
                    if hex_coord == home_hex:
                        connected_to_network = True
                    elif is_adjacent(hex_coord, home_hex):
                        connected_to_network = True
                if not connected_to_network:
                    raise ValueError(
                        f"First hex ({q},{r}) must be adjacent to {company_id}'s existing network"
                    )

        # Calculate costs with abilities
        total_cost = 0
        free_rural_used = False

        for hex_coord in path:
            q, r = hex_coord
            base_cost = state.hex_grid.get_cost(q, r)
            is_urban = state.hex_grid.is_urban(q, r)
            is_rural = state.hex_grid.is_rural(q, r)

            hex_cost = base_cost

            # Bayerische discount
            if ability == "discount_1":
                hex_cost = max(1, hex_cost - 1)

            # Badische free rural (one per build)
            if ability == "free_rural" and is_rural and not free_rural_used:
                hex_cost = 0
                free_rural_used = True

            # City penalty for stacking
            k = f"{q},{r}"
            existing_companies = state.board.get(k, [])
            if is_urban and existing_companies:
                # Niederschlesische never pays city penalty
                if ability != "no_city_penalty":
                    city_penalty = len(existing_companies)  # +$1 per existing company
                    hex_cost += city_penalty

            # Berlin approach: only 1 per company per game, only 1 company per approach hex
            if state.hex_grid.is_berlin_approach(q, r):
                if state.berlin_approach_used.get(company_id, False):
                    raise ValueError(f"{company_id} has already used its Berlin approach")
                if k in state.board and state.board[k]:
                    raise ValueError(f"Berlin approach hex ({q},{r}) already occupied")
                state.berlin_approach_used[company_id] = True

            total_cost += hex_cost

        # Köln-Mindener max spend
        if ability == "max_spend_5" and total_cost > 5:
            raise ValueError(f"Köln-Mindener cannot spend more than $5 per build (would cost ${total_cost})")

        # Check treasury
        if state.company_treasury.get(company_id, 0) < total_cost:
            raise ValueError(
                f"Not enough treasury: need ${total_cost}, have ${state.company_treasury.get(company_id, 0)}"
            )

        # All valid — apply the build
        state.company_treasury[company_id] -= total_cost
        company.track_remaining -= len(path)

        for hex_coord in path:
            q, r = hex_coord
            k = f"{q},{r}"
            if k not in state.board:
                state.board[k] = []
            state.board[k].append(company_id)

            # Entering urban hex → increase company income
            city = state.hex_grid.get_city(q, r)
            if city:
                income_gain = state.hex_grid.get_income(q, r)
                old_income = state.company_income[company_id]
                state.company_income[company_id] += income_gain

                # Update all shareholders' player income
                income_delta = income_gain
                for p, portfolio in state.shares.items():
                    if company_id in portfolio:
                        state.player_income[p] += income_delta * portfolio[company_id]

        # Check for dividend triggers (new connections between companies)
        self._check_dividends(state, company_id, path)

        state.move_history.append(
            f"{player_id} built {len(path)} track with {company_id}"
        )

        # Advance turn
        self._advance_turn(state)

    # ── Dividends ───────────────────────────────────────────────────

    def _check_dividends(
        self, state: PrussianRailsState, company_id: str, new_hexes: List[Tuple[int, int]]
    ):
        """
        Check if the newly built track creates a direct connection between
        this company and another previously unconnected company.
        If so, trigger dividend payouts for ALL companies.
        """
        # Get all companies present in the newly built hexes
        companies_reached: Set[str] = set()
        for hex_coord in new_hexes:
            k = f"{hex_coord[0]},{hex_coord[1]}"
            for cid in state.board.get(k, []):
                if cid != company_id:
                    # Check adjacency: is there a direct hex-to-hex connection?
                    companies_reached.add(cid)

        # Also check if the new hexes are adjacent to hexes belonging to other companies
        for hex_coord in new_hexes:
            for nq, nr in hex_neighbors(hex_coord[0], hex_coord[1]):
                nk = f"{nq},{nr}"
                for cid in state.board.get(nk, []):
                    if cid != company_id:
                        companies_reached.add(cid)

        triggered = False
        for other_id in companies_reached:
            pair = tuple(sorted([company_id, other_id]))
            if pair not in state.connected_pairs:
                state.connected_pairs.add(pair)
                triggered = True

        if triggered:
            self._pay_dividends(state, company_id)

    def _pay_dividends(self, state: PrussianRailsState, connecting_company: str):
        """
        All companies pay dividends equal to their current income × shares held.
        The connecting company pays DOUBLE.
        """
        for cid in state.companies:
            income = state.company_income[cid]

            # Berlin-Hamburger: only receives dividends if connected to BOTH Berlin and Hamburg
            if cid == "Berlin-Hamburger":
                if not self._is_connected_to_both(state, cid):
                    continue

            # Main-Weser-Bahn: double the best city income in its network
            if cid == "Main-Weser-Bahn":
                best = self._get_best_city_income(state, cid)
                income = max(income, income + best)  # effectively double best

            # Apply income
            multiplier = 2 if cid == connecting_company else 1
            payout_per_share = income * multiplier

            for player_id, portfolio in state.shares.items():
                shares = portfolio.get(cid, 0)
                if shares > 0:
                    state.player_cash[player_id] += payout_per_share * shares

    def _is_connected_to_both(self, state: PrussianRailsState, company_id: str) -> bool:
        """Check if Berlin-Hamburger has connected to both Berlin and Hamburg."""
        berlin_hex = state.hex_grid.find_city_hex("Berlin")
        hamburg_hex = state.hex_grid.find_city_hex("Hamburg")

        connected_to_berlin = False
        connected_to_hamburg = False

        for k, companies in state.board.items():
            if company_id in companies:
                q, r = map(int, k.split(","))
                if berlin_hex and hex_distance((q, r), berlin_hex) == 0:
                    connected_to_berlin = True
                if hamburg_hex and hex_distance((q, r), hamburg_hex) == 0:
                    connected_to_hamburg = True

        return connected_to_berlin and connected_to_hamburg

    def _get_best_city_income(self, state: PrussianRailsState, company_id: str) -> int:
        """Find the highest-income city in a company's network for Main-Weser-Bahn ability."""
        best = 0
        for k, companies in state.board.items():
            if company_id in companies:
                q, r = map(int, k.split(","))
                income = state.hex_grid.get_income(q, r)
                if income > best:
                    best = income
        # Also check home city income
        home_hex = state.hex_grid.find_city_hex(state.company_home.get(company_id, ""))
        if home_hex:
            best = max(best, state.hex_grid.get_income(home_hex[0], home_hex[1]))
        return best
