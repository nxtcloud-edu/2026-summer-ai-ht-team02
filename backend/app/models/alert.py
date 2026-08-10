from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, Enum as SAEnum
from sqlalchemy.sql import func
import enum

from app.models.database import Base


class AlertLevel(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertType(str, enum.Enum):
    FIRE = "fire"                # 화재 발생
    SOS = "sos"                  # 동료 SOS
    UNCONSCIOUS = "unconscious"  # 의식 불명 감지
    ROUTE_BLOCKED = "route_blocked"  # 경로 차단


class Alert(Base):
    """알림/경고"""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    alert_type = Column(SAEnum(AlertType), nullable=False)
    level = Column(SAEnum(AlertLevel), default=AlertLevel.WARNING)
    floor_id = Column(Integer)
    x = Column(Float)               # 발생 위치
    y = Column(Float)
    message = Column(Text)
    source_user_id = Column(Integer)  # SOS 발신자
    is_resolved = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True))
