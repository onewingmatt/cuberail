from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi_jwt_auth import AuthJWT
from fastapi_jwt_auth.exceptions import AuthJWTException
from pydantic import BaseModel
from app.api import games, auth
import socketio

app = FastAPI(title="Cube Rail API")

class JWTSettings(BaseModel):
    authjwt_secret_key: str = "super_secret_jwt_key_for_dev_only"

@AuthJWT.load_config
def get_config():
    return JWTSettings()

@app.exception_handler(AuthJWTException)
def authjwt_exception_handler(request: Request, exc: AuthJWTException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message}
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(games.router, prefix="/api/games", tags=["Games"])

sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
socket_app = socketio.ASGIApp(sio, app)

@sio.on('join_game')
async def handle_join(sid, data):
    game_id = data.get('game_id')
    if game_id:
        sio.enter_room(sid, game_id)

app.mount("/", socket_app)
