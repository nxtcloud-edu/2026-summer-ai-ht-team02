from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SAEnum
from sqlalchemy.sql import func
import enum

from app.models.database import Base


class UserRole(str, enum.Enum):
    WORKER = "worker"       # 근로자
    ADMIN = "admin"         # 관리자
    RESCUER = "rescuer"     # 구조대


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    name = Column(String, nullable=False)
    role = Column(SAEnum(UserRole), default=UserRole.WORKER)
    department = Column(String)           # 소속 부서
    floor_id = Column(Integer)            # 평소 근무 층
    smartwatch_id = Column(String)        # 스마트워치 기기 ID
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
