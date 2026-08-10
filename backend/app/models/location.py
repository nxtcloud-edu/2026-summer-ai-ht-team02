from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.sql import func

from app.models.database import Base


class WorkerLocation(Base):
    """근로자 실시간 위치 (스마트워치 기반)"""
    __tablename__ = "worker_locations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    floor_id = Column(Integer, nullable=False)
    x = Column(Float, nullable=False)
    y = Column(Float, nullable=False)
    accuracy = Column(Float)            # 위치 정확도 (m)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())


class EvacuationStatus(Base):
    """대피 상태 추적"""
    __tablename__ = "evacuation_status"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, unique=True)
    status = Column(String, default="in_building")  # in_building, evacuating, evacuated, unconscious
    last_floor_id = Column(Integer)
    last_x = Column(Float)
    last_y = Column(Float)
    is_moving = Column(Boolean, default=True)       # 움직임 감지 여부
    heart_rate = Column(Integer)                    # 스마트워치 심박수
    sos_sent = Column(Boolean, default=False)       # SOS 발송 여부
    updated_at = Column(DateTime(timezone=True), server_default=func.now())
