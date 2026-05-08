import pytest
from app.engine.games.prussian_rails import PrussianRailsEngine, PrussianRailsState

def test_pr_setup_and_initial_auction():
    engine = PrussianRailsEngine()
    state = engine.setup_game(["alice", "bob", "charlie"])

    assert state.phase == "auction"
    assert state.auction_state["item"] == "Berlin-Hamburger"
    assert "alice" in state.auction_state["bidders"]

def test_pr_auction_flow():
    engine = PrussianRailsEngine()
    state = engine.setup_game(["alice", "bob"])

    # The active_player_stack has "alice", "bob", so bob acts first usually if we don't reverse
    # Wait, if stack is [alice, bob], bob is top of stack and acts first.

    # Bob passes
    state = engine.apply_move(state, "bob", "pass", {})

    # Alice bids 5
    state = engine.apply_move(state, "alice", "bid", {"bid": 5})
    assert state.auction_state["highest_bidder"] == "alice"
    assert state.auction_state["current_bid"] == 5

    # Since there was only bob and alice, after bob passed, alice bidding 5 should win if we also pass or just resolve if 1 bidder
    state = engine.apply_move(state, "alice", "pass", {})

    # Auction resolved, next company in queue
    assert state.phase == "auction"
    assert state.auction_state["item"] == "Koln-Mindener"

    # Alice should have the share and less money, company has money
    assert state.shares["alice"]["Berlin-Hamburger"] == 1
    assert state.balances["alice"] == 25
    assert state.companies["Berlin-Hamburger"].treasury == 5

def test_pr_build_track():
    engine = PrussianRailsEngine()
    state = engine.setup_game(["alice", "bob"])

    # Skip all initial auctions by everyone passing
    while state.phase == "auction":
        current_actor = state.get_current_actor()
        state = engine.apply_move(state, current_actor, "pass", {})

    assert state.phase == "main"

    # Cheat give Alice a share and company treasury
    state.shares["alice"]["Berlin-Hamburger"] = 1
    state.companies["Berlin-Hamburger"].treasury = 10

    state = engine.apply_move(state, "alice", "build_track", {
        "company": "Berlin-Hamburger",
        "city": "Berlin"
    })

    assert "Berlin-Hamburger" in state.board["Berlin"]
    assert state.companies["Berlin-Hamburger"].treasury == 9
    assert state.companies["Berlin-Hamburger"].track_remaining == 13
