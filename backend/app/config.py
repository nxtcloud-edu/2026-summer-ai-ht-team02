from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./fire_escape.db"

    # Auth
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 5  # seconds

    # Evacuation
    FIRE_ALERT_COOLDOWN: int = 10  # 중복 알림 방지 (초)
    ROUTE_RECALCULATE_INTERVAL: int = 3  # 경로 재계산 주기 (초)

    class Config:
        env_file = ".env"


settings = Settings()
