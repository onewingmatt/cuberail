import uuid
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.schema import User, Game, GamePlayer, Notification
from app.services import email as mail


NOTIF_TYPES = {
    "game_invite",
    "game_started",
    "your_turn",
    "game_over",
    "player_joined",
}


async def get_user_prefs(user_id: str, db: AsyncSession) -> Dict[str, bool]:
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalars().first()
    if not user:
        return {}
    prefs = user.notification_preferences or {}
    return {k: bool(v) for k, v in prefs.items() if k in NOTIF_TYPES}


async def create_notification(
    user_id: str,
    notif_type: str,
    title: str,
    body: str,
    game_id: Optional[str],
    db: AsyncSession,
) -> Notification:
    n = Notification(
        user_id=uuid.UUID(user_id),
        type=notif_type,
        title=title,
        body=body,
        game_id=uuid.UUID(game_id) if game_id else None,
    )
    db.add(n)
    await db.commit()
    return n


async def _user_email(user_id: str, db: AsyncSession) -> Optional[str]:
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalars().first()
    return user.email if user else None


async def notify_game_invite(
    target_user_id: str,
    inviter_name: str,
    game_id: str,
    db: AsyncSession,
):
    await create_notification(
        target_user_id, "game_invite",
        title="Game Invitation",
        body=f"{inviter_name} invited you to a game!",
        game_id=game_id, db=db,
    )
    prefs = await get_user_prefs(target_user_id, db)
    if prefs.get("game_invite", True):
        email = await _user_email(target_user_id, db)
        if email:
            mail.send_game_invite(email, inviter_name, game_id)


async def notify_game_started(
    player_ids: List[str],
    game_id: str,
    db: AsyncSession,
):
    for pid in player_ids:
        await create_notification(
            pid, "game_started",
            title="Game Started",
            body="The game has started!",
            game_id=game_id, db=db,
        )
        prefs = await get_user_prefs(pid, db)
        if prefs.get("game_started", True):
            email = await _user_email(pid, db)
            if email:
                mail.send_game_started(email, game_id)


async def notify_your_turn(
    target_user_id: str,
    game_id: str,
    opponent_name: Optional[str],
    db: AsyncSession,
):
    await create_notification(
        target_user_id, "your_turn",
        title="Your Turn",
        body=f"{opponent_name or 'Someone'} moved — it's your turn!",
        game_id=game_id, db=db,
    )
    prefs = await get_user_prefs(target_user_id, db)
    if prefs.get("your_turn", True):
        email = await _user_email(target_user_id, db)
        if email:
            mail.send_your_turn(email, game_id, opponent_name)


async def notify_game_over(
    player_ids: List[str],
    game_id: str,
    winner_name: Optional[str],
    db: AsyncSession,
):
    for pid in player_ids:
        await create_notification(
            pid, "game_over",
            title="Game Over",
            body=f"The game ended!{' Winner: ' + winner_name if winner_name else ''}",
            game_id=game_id, db=db,
        )
        prefs = await get_user_prefs(pid, db)
        if prefs.get("game_over", True):
            email = await _user_email(pid, db)
            if email:
                mail.send_game_over(email, game_id, winner_name)


async def notify_player_joined(
    creator_user_id: str,
    joiner_name: str,
    game_id: str,
    db: AsyncSession,
):
    await create_notification(
        creator_user_id, "player_joined",
        title="Player Joined",
        body=f"{joiner_name} joined your game!",
        game_id=game_id, db=db,
    )
    prefs = await get_user_prefs(creator_user_id, db)
    if prefs.get("player_joined", True):
        email = await _user_email(creator_user_id, db)
        if email:
            mail.send_player_joined(email, game_id, joiner_name)
