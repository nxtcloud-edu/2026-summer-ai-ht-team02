from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func

from app.models.database import Base


class Attendance(Base):
    """출퇴근 기록 (gate 센서 통과 또는 수동)"""
    __tablename__ = "attendances"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    gate_id = Column(Integer)               # gate 노드 ID (자동 인식 시)
    check_type = Column(String, nullable=False)  # "in" 또는 "out"
    checked_at = Column(DateTime(timezone=True), server_default=func.now())
    method = Column(String, default="auto")  # auto, manual, admin
