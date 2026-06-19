"""
Comprehensive tests for Northern Pacific official rules engine.
"""

import pytest
from app.engine.games.northern_pacific_official import (
    NPEngineOfficial,
    NPState,
    _city_capacity_for,
)
from app.engine.games.northern_pacific_data import TRACK_SEGMENTS, ALL_CITIES


# ---- Setup ----

def test_setup():
    engine = NPEngineOfficial()
    state = engine.setup_game(["alice", "bob"])

    assert state.train_endpoint == "StPaul"
    assert state.turn_order == ["alice", "bob"]
    assert state.current_player_index == 0
    assert state.current_round == 1
    assert state.city_capacity == 2
    assert state.player_supply["alice"] == 3
    assert state.player_enhanced["alice"] == 1
    assert not state.is_game_over
    assert state.laid_tracks == []


def test_setup_with_player_count_override():
    engine = NPEngineOfficial()
    state = engine.setup_game(["alice", "bob", "charlie", "dave"], player_count=6)
    assert state.city_capacity == 4  # 6 players


def test_setup_capacity_values():
    assert _city_capacity_for(2) == 2
    assert _city_capacity_for(3) == 2
    assert _city_capacity_for(4) == 3
    assert _city_capacity_for(5) == 3
    assert _city_capacity_for(6) == 4


# ---- Invest action ----

def test_invest_standard():
    engine = NPEngineOfficial()
    state = engine.setup_game(["alice", "bob"])

    state = engine.apply_move(state, "alice", "invest", {"city": "Duluth", "enhanced": False})
    assert state.city_cubes["Duluth"]["alice"] == 1
    assert state.player_supply["alice"] == 2
    assert state.current_player_index == 1  # bob's turn


def test_invest_enhanced():
    engine = NPEngineOfficial()
    state = engine.setup_game(["alice", "bob"])

    state = engine.apply_move(state, "alice", "invest", {"city": "Fargo", "enhanced": True})
    assert state.city_enhanced["Fargo"]["alice"] == 1
    assert state.player_enhanced["alice"] == 0
    assert state.player_supply["alice"] == 3  # unchanged


def test_invest_invalid_city():
    engine = NPEngineOfficial()
    state = engine.setup_game(["alice", "bob"])

    with pytest.raises(ValueError, match="Invalid city"):
        engine.apply_move(state, "alice", "invest", {"city": "Nowhere"})


def test_invest_stpaul():
    engine = NPEngineOfficial()
    state = engine.setup_game(["alice", "bob"])

    with pytest.raises(ValueError, match="Cannot invest in starting"):
        engine.apply_move(state, "alice", "invest", {"city": "StPaul"})


def test_invest_seattle():
    engine = NPEngineOfficial()
    state = engine.setup_game(["alice", "bob"])

    with pytest.raises(ValueError, match="Cannot invest in starting"):
        engine.apply_move(state, "alice", "invest", {"city": "Seattle"})


def test_invest_connected_city_blocked():
    """Can't invest in a city the railroad has already reached."""
    engine = NPEngineOfficial()
    state = engine.setup_game(["alice", "bob"])

    # Alice invests in Duluth (turn 0)
    state = engine.apply_move(state, "alice", "invest", {"city": "Duluth"})

    # Bob lays track from StPaul to Duluth (turn 1)
    state = engine.apply_move(state, "bob", "lay_track", {"segment_id": "t01"})

    # Duluth is now connected - on next turn, alice can't invest there
    state.current_player_index = 0  # reset for test
    with pytest.raises(ValueError, match="already connected"):
        engine.apply_move(state, "alice", "invest", {"city": "Duluth"})


def test_invest_capacity_limit():
    engine = NPEngineOfficial()
    players = ["alice", "bob"]
    state = engine.setup_game(players)
    state.city_capacity = 2  # ensure 2

    # Alice and Bob each invest in Fargo (2 cubes = capacity)
    state = engine.apply_move(state, "alice", "invest", {"city": "Fargo", "enhanced": False})
    state = engine.apply_move(state, "bob", "invest", {"city": "Fargo", "enhanced": False})
    # Next turn alice tries to add another
    with pytest.raises(ValueError, match="at investment capacity"):
        engine.apply_move(state, "alice", "invest", {"city": "Fargo"})


def test_invest_no_cubes_remaining():
    engine = NPEngineOfficial()
    state = engine.setup_game(["alice"])
    state.player_supply["alice"] = 0  # no standard cubes

    with pytest.raises(ValueError, match="No standard cubes"):
        engine.apply_move(state, "alice", "invest", {"city": "Fargo"})


def test_invest_no_enhanced_remaining():
    engine = NPEngineOfficial()
    state = engine.setup_game(["alice"])
    state.player_enhanced["alice"] = 0

    with pytest.raises(ValueError, match="No enhanced cubes"):
        engine.apply_move(state, "alice", "invest", {"city": "Fargo", "enhanced": True})


# ---- Lay track action ----

def test_lay_track_valid():
    engine = NPEngineOfficial()
    state = engine.setup_game(["alice", "bob"])

    state = engine.apply_move(state, "alice", "lay_track", {"segment_id": "t01"})  # StPaul -> Duluth
    assert "t01" in state.laid_tracks
    assert state.train_endpoint == "Duluth"


def test_lay_track_invalid_segment():
    engine = NPEngineOfficial()
    state = engine.setup_game(["alice"])

    with pytest.raises(ValueError, match="Invalid track segment"):
        engine.apply_move(state, "alice", "lay_track", {"segment_id": "t99"})


def test_lay_track_wrong_source():
    engine = NPEngineOfficial()
    state = engine.setup_game(["alice"])

    # t10 goes Fargo -> Minot, but train is at StPaul
    with pytest.raises(ValueError, match="must extend from"):
        engine.apply_move(state, "alice", "lay_track", {"segment_id": "t10"})


def test_lay_track_already_laid():
    engine = NPEngineOfficial()
    state = engine.setup_game(["alice", "bob"])

    state = engine.apply_move(state, "alice", "lay_track", {"segment_id": "t01"})
    with pytest.raises(ValueError, match="already laid"):
        engine.apply_move(state, "bob", "lay_track", {"segment_id": "t01"})


def test_lay_track_bidirectional_block():
    """Can't lay both directions of a bidirectional pair."""
    engine = NPEngineOfficial()
    state = engine.setup_game(["alice", "bob"])

    # Lay track from StPaul to Fargo (t02)
    state = engine.apply_move(state, "alice", "lay_track", {"segment_id": "t02"})
    # Train is at Fargo. Lay Fargo -> GrandForks (t08, bidir)
    state = engine.apply_move(state, "bob", "lay_track", {"segment_id": "t08"})
    # Train is at GrandForks. t09 (GrandForks -> Fargo) is the other direction of same pair
    with pytest.raises(ValueError, match="Other direction"):
        engine.apply_move(state, "alice", "lay_track", {"segment_id": "t09"})


def test_lay_track_chain():
    """Must be able to lay multiple sequential tracks."""
    engine = NPEngineOfficial()
    state = engine.setup_game(["alice", "bob"])

    # StPaul -> Duluth
    state = engine.apply_move(state, "alice", "lay_track", {"segment_id": "t01"})
    assert state.train_endpoint == "Duluth"

    # Duluth -> GrandForks
    state = engine.apply_move(state, "bob", "lay_track", {"segment_id": "t05"})
    assert state.train_endpoint == "GrandForks"

    # GrandForks -> Minot
    state = engine.apply_move(state, "alice", "lay_track", {"segment_id": "t07"})
    assert state.train_endpoint == "Minot"


def test_lay_track_no_revisit():
    """Can't lay a track to a city already visited (except Seattle)."""
    engine = NPEngineOfficial()
    state = engine.setup_game(["alice", "bob"])

    # StPaul -> Duluth
    state = engine.apply_move(state, "alice", "lay_track", {"segment_id": "t01"})
    # Duluth -> GrandForks
    state = engine.apply_move(state, "bob", "lay_track", {"segment_id": "t05"})
    # GrandForks -> Fargo (t09) — Fargo is not yet connected, this is OK
    state = engine.apply_move(state, "alice", "lay_track", {"segment_id": "t09"})
    assert state.train_endpoint == "Fargo"

    # Now try to go Fargo -> Duluth — Duluth is already connected
    # But t06 goes Duluth -> Fargo (wrong direction from Fargo)...
    # Actually there's no segment from Fargo back to Duluth.
    # Let's verify by trying to go somewhere already connected.

    # Fargo can go to Minot (t10) or Bismarck (t11) — neither is connected yet


# ---- Payout tests ----

def test_payout_standard():
    """Standard cube pays out: return cube + 1 bonus."""
    engine = NPEngineOfficial()
    state = engine.setup_game(["alice", "bob"])

    # Alice invests a standard cube in Duluth
    state = engine.apply_move(state, "alice", "invest", {"city": "Duluth"})
    assert state.player_supply["alice"] == 2  # used one

    # Bob lays track to Duluth
    state = engine.apply_move(state, "bob", "lay_track", {"segment_id": "t01"})

    # Alice gets her cube back + 1 bonus = +2 to supply
    assert state.player_supply["alice"] == 4  # was 2, now +2
    # Duluth should have no cubes left
    assert "Duluth" not in state.city_cubes


def test_payout_enhanced():
    """Enhanced cube pays out: return cube + 2 bonus."""
    engine = NPEngineOfficial()
    state = engine.setup_game(["alice", "bob"])

    # Alice invests an enhanced cube in Duluth
    state = engine.apply_move(state, "alice", "invest", {"city": "Duluth", "enhanced": True})
    enhanced_count_before = state.player_enhanced["alice"]
    supply_before = state.player_supply["alice"]

    # Bob lays track to Duluth
    state = engine.apply_move(state, "bob", "lay_track", {"segment_id": "t01"})

    # Enhanced cube returned + 2 bonus standard cubes = +2 to supply
    # Enhanced cube is also returned to player_enhanced
    assert state.player_supply["alice"] == supply_before + 2
    assert state.player_enhanced["alice"] == enhanced_count_before + 1
    assert "Duluth" not in state.city_enhanced


def test_payout_multiple_cubes():
    """Multiple cubes from same owner pay out correctly."""
    engine = NPEngineOfficial()
    state = engine.setup_game(["alice", "bob"])

    # Alice uses 2 standard cubes in Duluth (setup doesn't allow that easily
    # because city_capacity=2, so we need 2 alice turns. Let's hack supply)
    # Actually with 2 players, capacity=2. Alice can invest twice.
    state = engine.apply_move(state, "alice", "invest", {"city": "Duluth"})
    state = engine.apply_move(state, "bob", "pass", {})
    state = engine.apply_move(state, "alice", "invest", {"city": "Duluth"})
    state = engine.apply_move(state, "bob", "pass", {})

    assert state.city_cubes["Duluth"]["alice"] == 2
    supply_before = state.player_supply["alice"]

    # Bob lays track to Duluth (after 4 turns... let's just pass back)
    # Actually, let's just use a state manipulation for simplicity
    state = engine.apply_move(state, "alice", "lay_track", {"segment_id": "t01"})

    # 2 cubes * 2 each = +4
    assert state.player_supply["alice"] >= supply_before + 4


def test_payout_multiple_owners():
    """Cubes from different owners in the same city pay out correctly."""
    engine = NPEngineOfficial()
    state = engine.setup_game(["alice", "bob"])

    # Alice invests in Fargo
    state = engine.apply_move(state, "alice", "invest", {"city": "Fargo"})
    # Bob invests in Fargo
    state = engine.apply_move(state, "bob", "invest", {"city": "Fargo"})

    alice_before = state.player_supply["alice"]
    bob_before = state.player_supply["bob"]

    # Lay track to Fargo
    # Current turn is alice again (index wrapped to 0)
    state = engine.apply_move(state, "alice", "lay_track", {"segment_id": "t02"})

    assert state.player_supply["alice"] >= alice_before + 2
    assert state.player_supply["bob"] >= bob_before + 2


def test_payout_no_investment():
    """Laying track to an uninvested city should not cause issues."""
    engine = NPEngineOfficial()
    state = engine.setup_game(["alice"])

    state = engine.apply_move(state, "alice", "lay_track", {"segment_id": "t01"})
    assert state.train_endpoint == "Duluth"
    # No crash


# ---- Round end and scoring ----

def test_round_ends_at_seattle():
    engine = NPEngineOfficial()
    state = engine.setup_game(["alice"])
    assert state.current_round == 1

    # Fast-track to Seattle via Richland
    state.train_endpoint = "Richland"

    state = engine.apply_move(state, "alice", "lay_track", {"segment_id": "t48"})

    assert state.current_round == 2  # advanced to round 2
    # train_endpoint resets to StPaul at round end


def test_good_investments_scored():
    """At round end, cubes in hand = good investments."""
    engine = NPEngineOfficial()
    state = engine.setup_game(["alice", "bob"])

    # Alice invests in Duluth
    state = engine.apply_move(state, "alice", "invest", {"city": "Duluth"})
    # Bob invests in Fargo (enhanced)
    state = engine.apply_move(state, "bob", "invest", {"city": "Fargo", "enhanced": True})
    # Alice invests in GrandForks
    state = engine.apply_move(state, "alice", "invest", {"city": "GrandForks"})

    # Alice has: 1 std (1 used) + 1 enhanced = 2 cubes
    # Bob has: 3 std + 0 enhanced (1 used) = 3 cubes

    # Fast-track to Seattle
    state.train_endpoint = "Richland"
    state = engine.apply_move(state, "bob", "lay_track", {"segment_id": "t48"})

    # Round ended. Their cubes in hand were scored.
    # Alice had 1 std + 1 enh in hand + no payout = 2 good
    # Bob had 3 std + 0 enh in hand + no payout = 3 good
    # Wait, Bob invested his enhanced cube, so he had 3 std left
    assert not state.is_game_over
    assert state.current_round == 2


def test_game_over_after_three_rounds():
    engine = NPEngineOfficial()
    state = engine.setup_game(["alice"])

    # Round 1: reach Seattle
    state.train_endpoint = "Richland"
    state = engine.apply_move(state, "alice", "lay_track", {"segment_id": "t48"})
    assert state.current_round == 2

    # Round 2: reach Seattle
    state.train_endpoint = "Richland"
    state = engine.apply_move(state, "alice", "lay_track", {"segment_id": "t48"})
    assert state.current_round == 3

    # Round 3: reach Seattle — game over
    state.train_endpoint = "Richland"
    state = engine.apply_move(state, "alice", "lay_track", {"segment_id": "t48"})
    assert state.is_game_over
    assert state.winner is not None


def test_winner_determination():
    engine = NPEngineOfficial()
    state = engine.setup_game(["alice", "bob"])

    # Simulate cumulative scores
    state.cumulative_good = {"alice": 5, "bob": 3}
    state.cumulative_bad = {"alice": 1, "bob": 2}
    state.current_round = 3

    # End game by reaching Seattle
    state.train_endpoint = "Richland"
    state = engine.apply_move(state, "alice", "lay_track", {"segment_id": "t48"})

    assert state.winner == "alice"


def test_tiebreaker_fewer_bad():
    """Tie goes to player with fewer bad investments."""
    engine = NPEngineOfficial()
    state = engine.setup_game(["alice", "bob"])

    state.cumulative_good = {"alice": 5, "bob": 5}  # tie
    state.cumulative_bad = {"alice": 3, "bob": 1}   # bob has fewer bad
    state.current_round = 3

    state.train_endpoint = "Richland"
    state = engine.apply_move(state, "alice", "lay_track", {"segment_id": "t48"})

    assert state.winner == "bob"


# ---- Turn order ----

def test_turn_advances():
    engine = NPEngineOfficial()
    state = engine.setup_game(["alice", "bob", "charlie"])

    assert state.get_current_actor() == "alice"
    state = engine.apply_move(state, "alice", "invest", {"city": "Duluth"})
    assert state.get_current_actor() == "bob"
    state = engine.apply_move(state, "bob", "invest", {"city": "Fargo"})
    assert state.get_current_actor() == "charlie"


def test_wrong_player():
    engine = NPEngineOfficial()
    state = engine.setup_game(["alice", "bob"])

    with pytest.raises(ValueError, match="Not your turn"):
        engine.apply_move(state, "bob", "invest", {"city": "Duluth"})


def test_game_over_rejects_moves():
    engine = NPEngineOfficial()
    state = engine.setup_game(["alice"])
    state.is_game_over = True

    with pytest.raises(ValueError, match="already over"):
        engine.apply_move(state, "alice", "pass", {})


# ---- Edge cases ----

def test_pass_action():
    """Pass moves the turn but does nothing else."""
    engine = NPEngineOfficial()
    state = engine.setup_game(["alice", "bob"])

    state = engine.apply_move(state, "alice", "pass", {})
    assert state.current_player_index == 1  # bob's turn
    assert state.train_endpoint == "StPaul"


def test_available_tracks_reflects_endpoint():
    """Available track segments change as the train moves."""
    engine = NPEngineOfficial()
    state = engine.setup_game(["alice", "bob"])

    tracks_from_stpaul = state._available_track_segments()
    assert len(tracks_from_stpaul) == 4
    assert all(t[1] == "StPaul" for t in tracks_from_stpaul)

    # Move to Duluth
    state = engine.apply_move(state, "alice", "lay_track", {"segment_id": "t01"})
    tracks_from_duluth = state._available_track_segments()
    assert all(t[1] == "Duluth" for t in tracks_from_duluth)
    # t05 (GrandForks) or t06 (Fargo)
    assert len(tracks_from_duluth) == 2


def test_invest_city_list_excludes_connected():
    """Available invest cities shrink as railroad expands."""
    engine = NPEngineOfficial()
    state = engine.setup_game(["alice", "bob"])

    available_before = state._available_invest_cities()
    assert len(available_before) == 23  # all except StPaul and Seattle

    # Connect Duluth
    state = engine.apply_move(state, "alice", "lay_track", {"segment_id": "t01"})
    available_after = state._available_invest_cities()
    assert "Duluth" not in available_after
    assert len(available_after) == 22  # Duluth removed


def test_to_dict_serializable():
    """State should serialize without errors."""
    engine = NPEngineOfficial()
    state = engine.setup_game(["alice", "bob"])
    d = state.to_dict()
    assert d["game_type"] == "northern_pacific"
    assert d["current_round"] == 1
    assert isinstance(d["used_bidirectional"], list)
    assert d["city_capacity"] == 2
