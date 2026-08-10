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

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Health Monitoring (Z-score)
    HEALTH_EMA_ALPHA: float = 0.05          # EMA 가중치
    HEALTH_BASELINE_MIN_SAMPLES: int = 50   # baseline 초기화 최소 샘플
    HEALTH_HR_ZSCORE_THRESHOLD: float = 2.0 # 심박 이상 임계 z-score
    HEALTH_TEMP_ZSCORE_THRESHOLD: float = 1.5  # 체온 이상 임계 z-score
    HEALTH_TEMP_ABSOLUTE_MAX: float = 38.0  # 체온 절대 임계값 (°C)
    HEALTH_HR_ABSOLUTE_MIN: int = 40        # 심박 절대 위험값 (bpm)
    HEALTH_ANOMALY_CONSECUTIVE: int = 3     # 연속 이상 → 상태 전환

    class Config:
        env_file = ".env"


settings = Settings()
