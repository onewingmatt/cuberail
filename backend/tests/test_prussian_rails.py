"""
Tests for Prussian Rails engine.
NOTE: The initial auction phase is non-deterministic (random starter),
so these tests use a simplified flow.
"""
import pytest
from app.engine.games.prussian_rails import PrussianRailsEngine, PrussianRailsState


def test_pr_setup():
    """Basic setup creates a game with correct initial state."""
    engine = PrussianRailsEngine()
    state = engine.setup_game(["alice", "bob", "charlie"])

    assert state.phase == "auction"  # starts in auction phase
    assert state.auction_state is not None
    assert state.auction_state["item"] is not None
    assert len(state.auction_state["bidders"]) == 3
    assert all(p in state.player_cash for p in ["alice", "bob", "charlie"])
    assert state.player_cash["alice"] == 40  # 3 players = $40 each


def test_pr_company_defs():
    """All 8 companies are initialized correctly."""
    engine = PrussianRailsEngine()
    state = engine.setup_game(["alice", "bob"])

    companies = state.companies
    assert len(companies) == 8
    assert "Preußische Ostbahn" in companies
    assert "Bayerische" in companies
    # Each starts with 3 unissued shares
    assert all(c.unissued_shares == 3 for c in companies.values())
    # Track counts
    assert companies["Preußische Ostbahn"].track_remaining == 20
    assert companies["Bayerische"].track_remaining == 16


def test_pr_hex_grid():
    """Hex grid is loaded with the Prussian Rails map."""
    engine = PrussianRailsEngine()
    state = engine.setup_game(["alice", "bob"])

    assert state.hex_grid is not None
    # Berlin should exist as an urban hex
    berlin = state.hex_grid.find_city_hex("Berlin")
    assert berlin is not None
    assert state.hex_grid.is_urban(*berlin)
    # Some terrain types
    assert state.hex_grid.get_terrain(0, 3) == "plains"
    assert state.hex_grid.get_terrain(0, 0) == "water"


def test_pr_map_data_serialized():
    """to_dict includes full map_data for the frontend."""
    engine = PrussianRailsEngine()
    state = engine.setup_game(["alice", "bob"])

    d = state.to_dict()
    assert "map_data" in d
    assert "hexes" in d["map_data"]
    assert len(d["map_data"]["hexes"]) > 0
    assert d["map_data"]["hex_size"] == 40
