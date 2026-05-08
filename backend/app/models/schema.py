import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import JSON
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

DEFAULT_NOTIF_PREFS = {
    "game_invite": True,
    "game_started": True,
    "your_turn": True,
    "game_over": True,
    "player_joined": True,
}

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    notification_preferences = Column(JSONB, default=DEFAULT_NOTIF_PREFS)
    created_at = Column(DateTime, default=datetime.utcnow)

class Game(Base):
    __tablename__ = "games"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    game_type = Column(String)
    status = Column(String, default="waiting") # waiting, in_progress, completed
    mode = Column(String, default="async") # "async" or "realtime"
    created_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    players = relationship("GamePlayer", back_populates="game")


class GamePlayer(Base):
    __tablename__ = "game_players"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    game_id = Column(UUID(as_uuid=True), ForeignKey("games.id"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    player_index = Column(Integer)

    game = relationship("Game", back_populates="players")
    user = relationship("User")


class GameMove(Base):
    __tablename__ = "game_moves"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    game_id = Column(UUID(as_uuid=True), ForeignKey("games.id"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    move_number = Column(Integer)
    action_type = Column(String)
    payload = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    type = Column(String)       # game_invite, game_started, your_turn, game_over, player_joined
    title = Column(String)
    body = Column(String)
    game_id = Column(UUID(as_uuid=True), ForeignKey("games.id"), nullable=True)
    read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
    game = relationship("Game")
