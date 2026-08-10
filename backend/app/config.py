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

    # Unconscious Detection
    UNCONSCIOUS_TIMEOUT_SECONDS: int = 30   # 위치 갱신 없음 → 의식불명 판정 (초)
    UNCONSCIOUS_CHECK_INTERVAL: int = 10    # 백그라운드 체크 주기 (초)
    HEARTRATE_THRESHOLD_LOW: int = 40       # 심박 이상 하한선 (bpm)

    class Config:
        env_file = ".env"


settings = Settings()
