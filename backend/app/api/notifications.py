from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update
from fastapi_jwt_auth import AuthJWT
from pydantic import BaseModel
from typing import List, Dict, Any
from app.db import get_db
from app.models.schema import Notification, User
import uuid

router = APIRouter()


class PrefsUpdate(BaseModel):
    notification_preferences: Dict[str, bool]


@router.get("/notifications")
async def get_notifications(
    limit: int = 20,
    unread_only: bool = False,
    Authorize: AuthJWT = Depends(),
    db: AsyncSession = Depends(get_db),
):
    Authorize.jwt_required()
    user_id = Authorize.get_jwt_subject()

    query = select(Notification).where(
        Notification.user_id == uuid.UUID(user_id)
    ).order_by(Notification.created_at.desc())

    if unread_only:
        query = query.where(Notification.read == False)

    result = await db.execute(query.limit(limit))
    notifs = result.scalars().all()

    return [
        {
            "id": str(n.id),
            "type": n.type,
            "title": n.title,
            "body": n.body,
            "game_id": str(n.game_id) if n.game_id else None,
            "read": n.read,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in notifs
    ]


@router.get("/notifications/unread-count")
async def unread_count(
    Authorize: AuthJWT = Depends(),
    db: AsyncSession = Depends(get_db),
):
    Authorize.jwt_required()
    user_id = Authorize.get_jwt_subject()

    result = await db.execute(
        select(Notification).where(
            Notification.user_id == uuid.UUID(user_id),
            Notification.read == False,
        )
    )
    count = len(result.scalars().all())
    return {"count": count}


@router.post("/notifications/{notif_id}/read")
async def mark_read(
    notif_id: str,
    Authorize: AuthJWT = Depends(),
    db: AsyncSession = Depends(get_db),
):
    Authorize.jwt_required()
    user_id = Authorize.get_jwt_subject()

    result = await db.execute(
        select(Notification).where(Notification.id == uuid.UUID(notif_id))
    )
    n = result.scalars().first()
    if not n or str(n.user_id) != user_id:
        raise HTTPException(status_code=404, detail="Notification not found")

    n.read = True
    await db.commit()
    return {"message": "Marked as read"}


@router.post("/notifications/read-all")
async def mark_all_read(
    Authorize: AuthJWT = Depends(),
    db: AsyncSession = Depends(get_db),
):
    Authorize.jwt_required()
    user_id = Authorize.get_jwt_subject()

    await db.execute(
        update(Notification).where(
            Notification.user_id == uuid.UUID(user_id),
            Notification.read == False,
        ).values(read=True)
    )
    await db.commit()
    return {"message": "All marked as read"}


@router.get("/notifications/preferences")
async def get_preferences(
    Authorize: AuthJWT = Depends(),
    db: AsyncSession = Depends(get_db),
):
    Authorize.jwt_required()
    user_id = Authorize.get_jwt_subject()

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user.notification_preferences or {}


@router.put("/notifications/preferences")
async def update_preferences(
    body: PrefsUpdate,
    Authorize: AuthJWT = Depends(),
    db: AsyncSession = Depends(get_db),
):
    Authorize.jwt_required()
    user_id = Authorize.get_jwt_subject()

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.notification_preferences = body.notification_preferences
    await db.commit()
    return {"message": "Preferences updated"}
