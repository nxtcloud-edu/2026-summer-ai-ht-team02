from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./site_planning.db"

    # Auth
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # 3-Tier Security
    TIER1_PRIVATE: bool = True       # 기업 Raw Data 접근 제한
    TIER2_SEMANTIC: bool = True      # 비식별·추상화 계층
    TIER3_PLANNING: bool = True      # LLM/Agent 분석 계층

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"

    # External APIs (공공데이터)
    PUBLIC_DATA_API_KEY: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
