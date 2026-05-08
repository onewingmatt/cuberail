from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi_jwt_auth import AuthJWT
from pydantic import BaseModel
from app.db import get_db
from app.models.schema import Game, GamePlayer, GameMove, User
from app.engine.games.simple_rail import SimpleRailEngine, SimpleRailState
from app.engine.games.northern_pacific import NPEngine, NPState
import uuid
from typing import List, Dict, Any

router = APIRouter()

class MoveRequest(BaseModel):
    action_type: str
    payload: dict

@router.post("/")
async def create_game(game_type: str, mode: str = "async", Authorize: AuthJWT = Depends(), db: AsyncSession = Depends(get_db)):
    Authorize.jwt_required()
    user_id = Authorize.get_jwt_subject()

    game = Game(game_type=game_type, mode=mode, created_by_id=uuid.UUID(user_id))
    db.add(game)
    await db.commit()
    await db.refresh(game)

    player = GamePlayer(game_id=game.id, user_id=uuid.UUID(user_id), player_index=0)
    db.add(player)
    await db.commit()

    return {"game_id": str(game.id)}

@router.post("/{game_id}/join")
async def join_game(game_id: str, Authorize: AuthJWT = Depends(), db: AsyncSession = Depends(get_db)):
    Authorize.jwt_required()
    user_id = Authorize.get_jwt_subject()

    result = await db.execute(select(Game).where(Game.id == uuid.UUID(game_id)))
    game = result.scalars().first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    result = await db.execute(select(GamePlayer).where(GamePlayer.game_id == uuid.UUID(game_id)))
    players = result.scalars().all()

    if any(str(p.user_id) == user_id for p in players):
        return {"message": "Already joined"}

    # Look up joiner's username
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    joiner = result.scalars().first()
    joiner_name = joiner.username if joiner else "Someone"

    player = GamePlayer(game_id=uuid.UUID(game_id), user_id=uuid.UUID(user_id), player_index=len(players))
    db.add(player)
    await db.commit()

    # Notify the game creator
    from app.services.notifications import notify_player_joined
    await notify_player_joined(str(game.created_by_id), joiner_name, game_id, db)

    return {"message": "Joined"}

@router.post("/{game_id}/start")
async def start_game(game_id: str, Authorize: AuthJWT = Depends(), db: AsyncSession = Depends(get_db)):
    Authorize.jwt_required()
    user_id = Authorize.get_jwt_subject()

    result = await db.execute(select(Game).where(Game.id == uuid.UUID(game_id)))
    game = result.scalars().first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    game.status = "in_progress"
    await db.commit()

    # Notify all players
    result = await db.execute(select(GamePlayer).where(GamePlayer.game_id == uuid.UUID(game_id)))
    players = result.scalars().all()
    player_ids = [str(p.user_id) for p in players]
    from app.services.notifications import notify_game_started
    await notify_game_started(player_ids, game_id, db)

    return {"message": "Started"}

async def rebuild_state(game_id: str, db: AsyncSession) -> Dict[str, Any]:
    # 1. Get Players
    result = await db.execute(select(GamePlayer).where(GamePlayer.game_id == uuid.UUID(game_id)).order_by(GamePlayer.player_index))
    players = result.scalars().all()
    player_ids = [str(p.user_id) for p in players]

    # 2. Get Game
    result = await db.execute(select(Game).where(Game.id == uuid.UUID(game_id)))
    game = result.scalars().first()

    if game.game_type == "simple_rail":
        engine = SimpleRailEngine()
        state = engine.setup_game(player_ids)
    elif game.game_type == "northern_pacific":
        engine = NPEngine()
        state = engine.setup_game(player_ids)
    else:
        raise ValueError("Unknown game type")

    # 3. Get Moves
    result = await db.execute(select(GameMove).where(GameMove.game_id == uuid.UUID(game_id)).order_by(GameMove.move_number))
    moves = result.scalars().all()

    for move in moves:
        state = engine.apply_move(state, str(move.user_id), move.action_type, move.payload)

    return state.to_dict()

@router.get("/{game_id}/state")
async def get_state(game_id: str, db: AsyncSession = Depends(get_db)):
    state = await rebuild_state(game_id, db)
    return state

@router.post("/{game_id}/moves")
async def make_move(game_id: str, move_req: MoveRequest, Authorize: AuthJWT = Depends(), db: AsyncSession = Depends(get_db)):
    Authorize.jwt_required()
    user_id = Authorize.get_jwt_subject()

    # Quick rebuild to validate
    # 1. Get Players
    result = await db.execute(select(GamePlayer).where(GamePlayer.game_id == uuid.UUID(game_id)).order_by(GamePlayer.player_index))
    players = result.scalars().all()
    player_ids = [str(p.user_id) for p in players]

    result = await db.execute(select(GameMove).where(GameMove.game_id == uuid.UUID(game_id)).order_by(GameMove.move_number.desc()))
    last_move = result.scalars().first()
    next_move_num = last_move.move_number + 1 if last_move else 1

    result = await db.execute(select(Game).where(Game.id == uuid.UUID(game_id)))
    game = result.scalars().first()

    if game.game_type == "simple_rail":
        engine = SimpleRailEngine()
    elif game.game_type == "northern_pacific":
        engine = NPEngine()
    else:
        raise ValueError("Unknown game type")

    state = engine.setup_game(player_ids)
    result = await db.execute(select(GameMove).where(GameMove.game_id == uuid.UUID(game_id)).order_by(GameMove.move_number))
    moves = result.scalars().all()
    for move in moves:
        state = engine.apply_move(state, str(move.user_id), move.action_type, move.payload)

    try:
        new_state = engine.apply_move(state, user_id, move_req.action_type, move_req.payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Valid move, save it
    new_move = GameMove(
        game_id=uuid.UUID(game_id),
        user_id=uuid.UUID(user_id),
        move_number=next_move_num,
        action_type=move_req.action_type,
        payload=move_req.payload
    )
    db.add(new_move)
    await db.commit()

    from app.main import sio
    await sio.emit('STATE_UPDATED', {"payload": new_state.to_dict()}, room=game_id)

    # Notification triggers
    from app.services.notifications import notify_your_turn, notify_game_over

    if new_state.is_game_over:
        # Find winner by highest balance
        winner = None
        if new_state.to_dict().get("balances"):
            balances = new_state.to_dict()["balances"]
            if balances:
                winner = max(balances, key=balances.get)
        # Look up winner name
        winner_name = None
        if winner:
            r = await db.execute(select(User).where(User.id == uuid.UUID(winner)))
            w = r.scalars().first()
            if w:
                winner_name = w.username
        await notify_game_over(player_ids, game_id, winner_name, db)
    elif game.mode == "async":
        next_player = new_state.get_current_actor()
        if next_player:
            # Look up the player who just moved
            r = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
            mover = r.scalars().first()
            mover_name = mover.username if mover else None
            # Don't notify the player who just moved
            if next_player != user_id:
                await notify_your_turn(next_player, game_id, mover_name, db)

    return {"message": "Move accepted"}
