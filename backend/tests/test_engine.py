import pytest
from app.engine.games.simple_rail import SimpleRailEngine, SimpleRailState

def test_engine_setup():
    engine = SimpleRailEngine()
    state = engine.setup_game(["alice", "bob"])

    assert state.turn_order == ["alice", "bob"]
    assert state.current_player_index == 0
    assert not state.is_game_over

def test_apply_valid_move():
    engine = SimpleRailEngine()
    state = engine.setup_game(["alice", "bob"])

    # Alice places track
    new_state = engine.apply_move(state, "alice", "place_track", {"hex": "0,0", "company": "Red"})

    assert new_state.board_hexes["0,0"] == "Red"
    assert new_state.current_player_index == 1 # Now bob's turn

def test_apply_invalid_move_wrong_turn():
    engine = SimpleRailEngine()
    state = engine.setup_game(["alice", "bob"])

    with pytest.raises(ValueError, match="Not your turn"):
        engine.apply_move(state, "bob", "place_track", {"hex": "1,1", "company": "Red"})

def test_apply_invalid_move_occupied_hex():
    engine = SimpleRailEngine()
    state = engine.setup_game(["alice", "bob"])

    new_state = engine.apply_move(state, "alice", "place_track", {"hex": "0,0", "company": "Red"})

    with pytest.raises(ValueError, match="Hex already occupied"):
        engine.apply_move(new_state, "bob", "place_track", {"hex": "0,0", "company": "Blue"})
