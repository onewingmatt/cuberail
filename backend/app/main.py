from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi_jwt_auth import AuthJWT
from fastapi_jwt_auth.exceptions import AuthJWTException
from pydantic import BaseModel
from app.api import games, auth, notifications
import socketio
import os

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

origins = settings.CORS_ORIGINS.split(",") if settings.CORS_ORIGINS else ["*"]
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

fastapi_app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
fastapi_app.include_router(games.router, prefix="/api/games", tags=["Games"])
fastapi_app.include_router(notifications.router, prefix="/api", tags=["Notifications"])

# Serve frontend static files (must be after API routes)
STATIC_DIR = settings.STATIC_DIR

@fastapi_app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    # Let API routes handle their own 404s
    if full_path.startswith("api/"):
        return JSONResponse(status_code=404, content={"detail": "Not found"})

    file_path = os.path.join(STATIC_DIR, full_path)
    if os.path.isfile(file_path):
        return FileResponse(file_path)

    # SPA fallback — serve index.html for client-side routing
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path)
    return JSONResponse(status_code=404, content={"detail": "Not found"})

sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')

@sio.on('join_game')
async def handle_join(sid, data):
    game_id = data.get('game_id')
    if game_id:
        await sio.enter_room(sid, game_id)

# Export 'app' globally so Uvicorn can pick it up via app.main:app
app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)
