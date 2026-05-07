from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi_jwt_auth import AuthJWT
from pydantic import BaseModel
from app.db import get_db
from app.models.schema import Game, GamePlayer, GameMove, User
from app.engine.games.simple_rail import SimpleRailEngine, SimpleRailState
import uuid
from typing import List, Dict, Any

router = APIRouter()

class MoveRequest(BaseModel):
    action_type: str
    payload: dict

@router.post("/")
async def create_game(game_type: str, Authorize: AuthJWT = Depends(), db: AsyncSession = Depends(get_db)):
    Authorize.jwt_required()
    user_id = Authorize.get_jwt_subject()

    game = Game(game_type=game_type, created_by_id=uuid.UUID(user_id))
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

    result = await db.execute(select(GamePlayer).where(GamePlayer.game_id == uuid.UUID(game_id)))
    players = result.scalars().all()

    if any(str(p.user_id) == user_id for p in players):
        return {"message": "Already joined"}

    player = GamePlayer(game_id=uuid.UUID(game_id), user_id=uuid.UUID(user_id), player_index=len(players))
    db.add(player)
    await db.commit()
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

    engine = SimpleRailEngine()
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

    return {"message": "Move accepted"}
