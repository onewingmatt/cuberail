from pydantic import BaseSettings
import os

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://cube_user:cube_password@localhost:5432/cube_db"
    SECRET_KEY: str = "supersecretjwtkeyforproduction"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"
    STATIC_DIR: str = os.path.join(os.path.dirname(__file__), "..", "..", "static")
    RESEND_API_KEY: str = ""

    class Config:
        env_file = ".env"

settings = Settings()

# Resolve STATIC_DIR relative to this file if not set
if not settings.STATIC_DIR:
    settings.STATIC_DIR = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "static")
    )
