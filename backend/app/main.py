from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi_jwt_auth import AuthJWT
from fastapi_jwt_auth.exceptions import AuthJWTException
from pydantic import BaseModel
from app.api import games, auth, notifications
import socketio

fastapi_app = FastAPI(title="Cube Rail API")

from app.config import settings

from datetime import timedelta

class JWTSettings(BaseModel):
    authjwt_secret_key: str = settings.SECRET_KEY
    authjwt_access_token_expires: timedelta = timedelta(days=7)

@AuthJWT.load_config
def get_config():
    return JWTSettings()

@fastapi_app.exception_handler(AuthJWTException)
def authjwt_exception_handler(request: Request, exc: AuthJWTException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message}
    )

fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000", "http://localhost:8000", "http://0.0.0.0:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

fastapi_app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
fastapi_app.include_router(games.router, prefix="/api/games", tags=["Games"])
fastapi_app.include_router(notifications.router, prefix="/api", tags=["Notifications"])

sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')

@sio.on('join_game')
async def handle_join(sid, data):
    game_id = data.get('game_id')
    if game_id:
        await sio.enter_room(sid, game_id)

# Export 'app' globally so Uvicorn can pick it up via app.main:app
app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)
