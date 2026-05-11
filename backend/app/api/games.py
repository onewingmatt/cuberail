from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi_jwt_auth import AuthJWT
from pydantic import BaseModel
from app.db import get_db
from app.models.schema import Game, GamePlayer, GameMove, User
from app.engine.games.simple_rail import SimpleRailEngine, SimpleRailState
from app.engine.games.northern_pacific_official import NPEngineOfficial, NPState
from app.engine.games.prussian_rails import PrussianRailsEngine, PrussianRailsState
import uuid
from typing import List, Dict, Any, Optional

router = APIRouter()


BOT_NAMES = ["Bot Alpha", "Bot Beta", "Bot Gamma", "Bot Delta"]


class MoveRequest(BaseModel):
    action_type: str
    payload: dict


@router.get("/")
async def list_games(db: AsyncSession = Depends(get_db)):
    """Return all waiting (open) games with player counts and creator names."""
    result = await db.execute(
        select(Game).where(Game.status == "waiting").order_by(Game.created_at.desc())
    )
    games = result.scalars().all()

    output = []
    for g in games:
        # Count human players (non-bots)
        gp_result = await db.execute(
            select(GamePlayer).where(GamePlayer.game_id == g.id)
        )
        players = gp_result.scalars().all()
        human_count = 0
        for p in players:
            u_result = await db.execute(select(User).where(User.id == p.user_id))
            u = u_result.scalars().first()
            if u and u.username and not u.username.startswith("Bot"):
                human_count += 1

        # Creator name
        creator_result = await db.execute(select(User).where(User.id == g.created_by_id))
        creator = creator_result.scalars().first()
        creator_name = creator.username if creator else "Unknown"

        output.append({
            "id": str(g.id),
            "game_type": g.game_type,
            "mode": g.mode,
            "created_by": creator_name,
            "human_players": human_count,
            "total_players": len(players),
            "created_at": g.created_at.isoformat() if g.created_at else None,
        })

    return output


@router.post("/")
async def create_game(
    game_type: str,
    mode: str = "async",
    bot_count: int = 0,
    Authorize: AuthJWT = Depends(),
    db: AsyncSession = Depends(get_db),
):
    Authorize.jwt_required()
    user_id = Authorize.get_jwt_subject()
    bot_count = max(0, min(bot_count, 3))

    game = Game(game_type=game_type, mode=mode, created_by_id=uuid.UUID(user_id))
    db.add(game)
    await db.commit()
    await db.refresh(game)

    # Human creator is player 0
    player = GamePlayer(game_id=game.id, user_id=uuid.UUID(user_id), player_index=0)
    db.add(player)

    # Add bot players
    bot_ids = []
    for i in range(bot_count):
        import time
        suffix = str(int(time.time() * 1000))[-6:]
        bot_username = f"{BOT_NAMES[i]}_{suffix}"
        bot_user = User(
            username=bot_username,
            email=f"bot_{i}_{uuid.uuid4().hex[:8]}@bot.cuberail",
            hashed_password="",
        )
        db.add(bot_user)
        await db.flush()
        bot_ids.append(bot_user.id)

        bot_player = GamePlayer(
            game_id=game.id,
            user_id=bot_user.id,
            player_index=i + 1,
        )
        db.add(bot_player)

    await db.commit()

    return {
        "game_id": str(game.id),
        "bot_count": bot_count,
    }


@router.post("/{game_id}/join")
async def join_game(
    game_id: str,
    Authorize: AuthJWT = Depends(),
    db: AsyncSession = Depends(get_db),
):
    Authorize.jwt_required()
    user_id = Authorize.get_jwt_subject()

    result = await db.execute(select(Game).where(Game.id == uuid.UUID(game_id)))
    game = result.scalars().first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    result = await db.execute(
        select(GamePlayer).where(GamePlayer.game_id == uuid.UUID(game_id))
    )
    players = result.scalars().all()

    if any(str(p.user_id) == user_id for p in players):
        return {"message": "Already joined"}

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    joiner = result.scalars().first()
    joiner_name = joiner.username if joiner else "Someone"

    player = GamePlayer(
        game_id=uuid.UUID(game_id),
        user_id=uuid.UUID(user_id),
        player_index=len(players),
    )
    db.add(player)
    await db.commit()

    try:
        from app.services.notifications import notify_player_joined
        await notify_player_joined(str(game.created_by_id), joiner_name, game_id, db)
    except ImportError:
        pass

    return {"message": "Joined"}


@router.post("/{game_id}/start")
async def start_game(
    game_id: str,
    Authorize: AuthJWT = Depends(),
    db: AsyncSession = Depends(get_db),
):
    Authorize.jwt_required()
    user_id = Authorize.get_jwt_subject()

    result = await db.execute(select(Game).where(Game.id == uuid.UUID(game_id)))
    game = result.scalars().first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    game.status = "in_progress"
    await db.commit()

    result = await db.execute(
        select(GamePlayer).where(GamePlayer.game_id == uuid.UUID(game_id))
    )
    players = result.scalars().all()
    player_ids = [str(p.user_id) for p in players]
    try:
        from app.services.notifications import notify_game_started
        await notify_game_started(player_ids, game_id, db)
    except ImportError:
        pass

    # If first player is a bot, auto-play immediately
    engine, state, player_ids = await _load_game(game_id, db)
    from app.main import sio

    await _process_bot_turns(game_id, engine, state, db, sio, 1)

    return {"message": "Started"}


async def _load_game(
    game_id: str, db: AsyncSession
) -> tuple:
    """Load game engine and state from DB."""
    result = await db.execute(
        select(GamePlayer)
        .where(GamePlayer.game_id == uuid.UUID(game_id))
        .order_by(GamePlayer.player_index)
    )
    players = result.scalars().all()
    player_ids = [str(p.user_id) for p in players]

    result = await db.execute(select(Game).where(Game.id == uuid.UUID(game_id)))
    game = result.scalars().first()

    if game.game_type == "simple_rail":
        engine = SimpleRailEngine()
        state = engine.setup_game(player_ids)
    elif game.game_type == "northern_pacific":
        engine = NPEngineOfficial()
        player_count = len(player_ids)
        state = engine.setup_game(player_ids, player_count=player_count)
    elif game.game_type == "prussian_rails":
        engine = PrussianRailsEngine()
        state = engine.setup_game(player_ids)
    else:
        raise ValueError("Unknown game type")

    result = await db.execute(
        select(GameMove)
        .where(GameMove.game_id == uuid.UUID(game_id))
        .order_by(GameMove.move_number)
    )
    moves = result.scalars().all()
    for move in moves:
        try:
            state = engine.apply_move(state, str(move.user_id), move.action_type, move.payload)
        except ValueError as e:
            # During replay, random cup-draw can produce different turn order.
            # Skip moves that don't match — they were already validated when made.
            import logging
            logging.getLogger("cuberail").warning(
                "Skipping move %d during replay: %s", move.move_number, e
            )
            continue

    return engine, state, player_ids


async def _is_bot(user_id: str, db: AsyncSession) -> tuple[bool, Optional[str]]:
    """Check if a user ID belongs to a bot. Returns (is_bot, username)."""
    try:
        result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
        user = result.scalars().first()
        if user and user.username and (user.username.startswith("Bot_") or user.username.startswith("Bot ")):
            return True, user.username
        return False, user.username if user else None
    except Exception:
        return False, None


async def _process_bot_turns(
    game_id: str,
    engine,
    state,
    db: AsyncSession,
    sio,
    next_move_num: int,
):
    """
    After a human move, auto-process any consecutive bot turns.
    Returns the final state after all bot moves.
    """
    # Import the right bot for this game type
    engine_name = type(engine).__name__
    if engine_name == "NPEngineOfficial":
        from app.engine.games.northern_pacific_bot import decide_move, _available_track_segments
    elif engine_name == "PrussianRailsEngine":
        from app.engine.games.prussian_rails_bot import decide_move
        # For Prussian Rails, the fallback is handled differently
        _available_track_segments = None
    else:
        # Unknown game type — no bot support
        return

    while not state.is_game_over:
        current = state.get_current_actor()
        if not current:
            break
        is_bot, username = await _is_bot(current, db)
        if not is_bot:
            break

        # Bot decides — guard against individual move failures
        action_type = "pass"
        payload = {}
        try:
            action_type, payload = decide_move(current, username, state.to_dict())
            new_state = engine.apply_move(state, current, action_type, payload)
            state = new_state
        except Exception as exc:
            import logging
            logging.getLogger("cuberail").warning(
                "Bot move failed for %s (%s): %s — forcing pass", current, username, exc
            )
            # NP bot has track segment fallback; PR bot just passes
            if _available_track_segments is not None:
                fallback_tracks = _available_track_segments(state.to_dict())
                if fallback_tracks:
                    action_type = "lay_track"
                    payload = {"segment_id": fallback_tracks[0][0]}
                else:
                    action_type = "pass"
                    payload = {}
            else:
                action_type = "pass"
                payload = {}
            new_state = engine.apply_move(state, current, action_type, payload)
            state = new_state

        # Save the move
        move = GameMove(
            game_id=uuid.UUID(game_id),
            user_id=uuid.UUID(current),
            move_number=next_move_num,
            action_type=action_type,
            payload=payload,
        )
        db.add(move)
        await db.commit()
        next_move_num += 1

        # Emit incremental update
        await sio.emit("STATE_UPDATED", {"payload": state.to_dict()}, room=game_id)

    return state


@router.get("/{game_id}/state")
async def get_state(game_id: str, db: AsyncSession = Depends(get_db)):
    _, state, _ = await _load_game(game_id, db)
    result = state.to_dict()

    # Inject game_type for frontend routing
    game_result = await db.execute(select(Game).where(Game.id == uuid.UUID(game_id)))
    game = game_result.scalars().first()
    if game:
        result["game_type"] = game.game_type

    # Enrich with player info (usernames, bot status)
    result["players"] = []
    gp_result = await db.execute(
        select(GamePlayer)
        .where(GamePlayer.game_id == uuid.UUID(game_id))
        .order_by(GamePlayer.player_index)
    )
    for gp in gp_result.scalars().all():
        user_result = await db.execute(select(User).where(User.id == gp.user_id))
        user = user_result.scalars().first()
        pid = str(gp.user_id)
        if user:
            result["players"].append({
                "id": pid,
                "username": user.username,
                "is_bot": user.username.startswith("Bot_") or user.username.startswith("Bot ") if user.username else False,
                "cash": result.get("player_cash", {}).get(pid),
                "income": result.get("player_income", {}).get(pid),
                "shares": result.get("shares", {}).get(pid, {}),
            })

    return result


@router.post("/{game_id}/moves")
async def make_move(
    game_id: str,
    move_req: MoveRequest,
    Authorize: AuthJWT = Depends(),
    db: AsyncSession = Depends(get_db),
):
    Authorize.jwt_required()
    user_id = Authorize.get_jwt_subject()

    engine, state, player_ids = await _load_game(game_id, db)

    result = await db.execute(
        select(GameMove)
        .where(GameMove.game_id == uuid.UUID(game_id))
        .order_by(GameMove.move_number.desc())
    )
    last_move = result.scalars().first()
    next_move_num = last_move.move_number + 1 if last_move else 1

    result = await db.execute(select(Game).where(Game.id == uuid.UUID(game_id)))
    game = result.scalars().first()

    # Auto-start game if still waiting
    if game and game.status == "waiting":
        game.status = "in_progress"
        await db.commit()

    try:
        new_state = engine.apply_move(state, user_id, move_req.action_type, move_req.payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Save human move
    new_move = GameMove(
        game_id=uuid.UUID(game_id),
        user_id=uuid.UUID(user_id),
        move_number=next_move_num,
        action_type=move_req.action_type,
        payload=move_req.payload,
    )
    db.add(new_move)
    await db.commit()
    next_move_num += 1

    from app.main import sio

    # Auto-process bot turns BEFORE any WS emit, so the first STATE_UPDATED
    # already includes the bot's move. This prevents the frontend from
    # seeing an intermediate "bot's turn" state.
    try:
        await _process_bot_turns(
            game_id, engine, new_state, db, sio, next_move_num
        )
    except Exception as exc:
        import logging
        logging.getLogger("cuberail").exception("Bot processing failed: %s", exc)

    # Emit final state (after human + bot processing)
    try:
        await sio.emit("STATE_UPDATED", {"payload": new_state.to_dict()}, room=game_id)
    except Exception:
        pass  # WebSocket state broadcast is non-critical

    # Notification triggers (optional — resend module may not be installed)
    try:
        from app.services.notifications import notify_your_turn, notify_game_over
    except ImportError:
        notify_your_turn = notify_game_over = None

    if new_state.is_game_over:
        if notify_game_over:
            winner = new_state.to_dict().get("winner")
            winner_name = None
            if winner:
                r = await db.execute(select(User).where(User.id == uuid.UUID(winner)))
                w = r.scalars().first()
                if w:
                    winner_name = w.username
            await notify_game_over(player_ids, game_id, winner_name, db)
    elif game and game.mode == "async" and notify_your_turn:
        next_player = new_state.get_current_actor()
        if next_player:
            r = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
            mover = r.scalars().first()
            mover_name = mover.username if mover else None
            if next_player != user_id:
                is_bot, _ = await _is_bot(next_player, db)
                if not is_bot:
                    await notify_your_turn(next_player, game_id, mover_name, db)

    return {"message": "Move accepted", "state": new_state.to_dict()}
