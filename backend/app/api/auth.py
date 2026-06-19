from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from fastapi_jwt_auth import AuthJWT
from app.db import get_db
from app.models.schema import User
import uuid

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Ensure bcrypt backend loads correctly on Python 3.13
# Try to pre-load the backend; pass silently if it fails
import logging
logger = logging.getLogger(__name__)
try:
    pwd_context.hash("test")
except Exception:
    logger.warning("passlib bcrypt backend failed — falling back to direct bcrypt")
    import bcrypt as _bcrypt
    class _BcryptFallback:
        @staticmethod
        def hash(secret):
            return _bcrypt.hashpw(secret.encode() if isinstance(secret, str) else secret, _bcrypt.gensalt()).decode()
        @staticmethod
        def verify(secret, hash):
            return _bcrypt.checkpw(secret.encode() if isinstance(secret, str) else secret, hash.encode() if isinstance(hash, str) else hash)
    pwd_context.hash = _BcryptFallback.hash
    pwd_context.verify = _BcryptFallback.verify

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class PasswordReset(BaseModel):
    email: EmailStr

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where((User.username == user.username) | (User.email == user.email)))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Username or Email already registered")

    new_user = User(
        username=user.username,
        email=user.email,
        hashed_password=get_password_hash(user.password)
    )
    db.add(new_user)
    await db.commit()
    return {"message": "User registered successfully"}

@router.post("/login")
async def login(user: UserLogin, Authorize: AuthJWT = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == user.username))
    db_user = result.scalars().first()

    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    access_token = Authorize.create_access_token(subject=str(db_user.id))
    return {"access_token": access_token, "user_id": str(db_user.id)}

@router.post("/reset-password")
async def reset_password(req: PasswordReset, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == req.email))
    db_user = result.scalars().first()
    if not db_user:
        # Don't reveal if email exists or not
        return {"message": "If an account with that email exists, a reset link has been sent."}

    # Stub: send email here
    from app.services.email import send_reset_email
    await send_reset_email(db_user.email, "dummy-reset-token")
    return {"message": "If an account with that email exists, a reset link has been sent."}
