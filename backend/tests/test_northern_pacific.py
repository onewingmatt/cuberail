import pytest
from app.engine.games.northern_pacific import NPEngine, NPState

def test_np_setup():
    engine = NPEngine()
    state = engine.setup_game(["alice", "bob"])

    assert state.train_pos == "StPaul"
    assert state.turn_order == ["alice", "bob"]
    assert state.current_player_index == 0
    assert state.balances["alice"] == 0
    assert state.balances["bob"] == 0

def test_np_invest():
    engine = NPEngine()
    state = engine.setup_game(["alice", "bob"])

    new_state = engine.apply_move(state, "alice", "invest", {"city": "Duluth"})

    assert new_state.investments["Duluth"] == "alice"
    assert new_state.current_player_index == 1 # bob's turn

def test_np_invalid_invest():
    engine = NPEngine()
    state = engine.setup_game(["alice", "bob"])

    with pytest.raises(ValueError, match="Cannot invest in starting city"):
        engine.apply_move(state, "alice", "invest", {"city": "StPaul"})

    engine.apply_move(state, "alice", "invest", {"city": "Fargo"})

    with pytest.raises(ValueError, match="City already invested"):
        engine.apply_move(state, "bob", "invest", {"city": "Fargo"})

def test_np_move_train_and_payout():
    engine = NPEngine()
    state = engine.setup_game(["alice", "bob"])

    # Alice invests in Fargo
    state = engine.apply_move(state, "alice", "invest", {"city": "Fargo"})

    # Bob moves train to Fargo
    state = engine.apply_move(state, "bob", "move_train", {"city": "Fargo"})

    assert state.train_pos == "Fargo"
    assert state.balances["alice"] == 10 # Alice owns Fargo
    assert state.balances["bob"] == 0
    assert not state.is_game_over

def test_np_move_train_invalid():
    engine = NPEngine()
    state = engine.setup_game(["alice", "bob"])

    with pytest.raises(ValueError, match="Not connected"):
        engine.apply_move(state, "alice", "move_train", {"city": "Seattle"})

def test_np_game_over():
    engine = NPEngine()
    state = engine.setup_game(["alice"])

    # Cheat train to Richland to test ending (Richland connects to Seattle)
    state.train_pos = "Richland"

    state = engine.apply_move(state, "alice", "move_train", {"city": "Seattle"})

    assert state.train_pos == "Seattle"
    assert state.is_game_over
