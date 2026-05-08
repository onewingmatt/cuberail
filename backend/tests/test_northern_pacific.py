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
    assert state.balances["alice"] == 15  # Alice owns Fargo (share value 10 + 5 increase)
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

    # Cheat train to Richland to test ending (Richland -> Seattle is valid)
    state.train_pos = "Richland"

    state = engine.apply_move(state, "alice", "move_train", {"city": "Seattle"})

    assert state.train_pos == "Seattle"
    assert state.is_game_over


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
    # Alice got the payout based on share value
    assert state.balances["alice"] > 0


def test_buy_share():
    engine = NPEngine()
    state = engine.setup_game(["alice", "bob"])

    # Alice invests in Fargo
    state = engine.apply_move(state, "alice", "invest", {"city": "Fargo"})

    # Bob moves train to Fargo — Alice gets payout
    state = engine.apply_move(state, "bob", "move_train", {"city": "Fargo"})

    # Alice now has cash (share value 10 + 5 increase = 15 payout)
    assert state.balances["alice"] == 15

    # Alice's turn again — she buys a share in Fargo
    state = engine.apply_move(state, "alice", "buy_share", {"city": "Fargo"})

    # Alice holds 1 share in Fargo
    assert state.shares_held["alice"].get("Fargo") == 1
    # Balance: 15 - 15 (share price after increase) = 0
    assert state.balances["alice"] == 0


def test_final_score_includes_shares():
    engine = NPEngine()
    state = engine.setup_game(["alice", "bob"])

    # Alice invests in Fargo
    state = engine.apply_move(state, "alice", "invest", {"city": "Fargo"})

    # Bob moves train to Fargo — Alice gets payout
    state = engine.apply_move(state, "bob", "move_train", {"city": "Fargo"})

    # Alice now has $15. She buys a share in Fargo
    state = engine.apply_move(state, "alice", "buy_share", {"city": "Fargo"})

    # Calculate final scores (not game over — just test the calculation)
    scores = engine.calculate_final_scores(state)
    assert "alice" in scores
    assert "bob" in scores
    # Alice: cash 0 + share value 15 (city) + share value 15 (held share) = 30
    assert scores["alice"] == 30
    # Bob: cash 0 + 0 shares + 0 city = 0
    assert scores["bob"] == 0
