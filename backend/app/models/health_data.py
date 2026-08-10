from sqlalchemy import Column, Integer, Float, DateTime
from sqlalchemy.sql import func

from app.models.database import Base


class HealthRecord(Base):
    """건강 데이터 개별 기록 (스마트워치 → 서버)"""
    __tablename__ = "health_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    heart_rate = Column(Integer)            # bpm
    temperature = Column(Float)             # 체온 (°C)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())


class HealthBaseline(Base):
    """개인별 건강 baseline (EMA 기반 이동 평균/표준편차)"""
    __tablename__ = "health_baselines"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, unique=True)
    avg_hr = Column(Float)                  # 이동 평균 심박
    std_hr = Column(Float)                  # 심박 표준편차
    avg_temp = Column(Float)                # 이동 평균 체온
    std_temp = Column(Float)                # 체온 표준편차
    sample_count = Column(Integer, default=0)       # 누적 샘플 수
    anomaly_count = Column(Integer, default=0)      # 연속 이상 횟수
    updated_at = Column(DateTime(timezone=True), server_default=func.now())
