from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://cube_user:cube_password@localhost:5432/cube_db"
    SECRET_KEY: str = "super_secret_jwt_key_for_dev_only"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    RESEND_API_KEY: str = ""

    class Config:
        env_file = ".env"

settings = Settings()
