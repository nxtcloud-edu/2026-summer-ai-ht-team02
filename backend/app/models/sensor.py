from sqlalchemy import Column, Integer, String, Float, DateTime, Enum as SAEnum
from sqlalchemy.sql import func
import enum

from app.models.database import Base


class SensorType(str, enum.Enum):
    SMOKE = "smoke"         # 연기 감지기
    HEAT = "heat"           # 열 감지기
    FLAME = "flame"         # 불꽃 감지기
    GAS = "gas"             # 가스 감지기
    SPRINKLER = "sprinkler" # 스프링클러


class SensorStatus(str, enum.Enum):
    NORMAL = "normal"
    WARNING = "warning"
    DANGER = "danger"
    OFFLINE = "offline"


class Sensor(Base):
    """화재 감지 센서"""
    __tablename__ = "sensors"

    id = Column(Integer, primary_key=True, index=True)
    floor_id = Column(Integer, nullable=False)
    sensor_type = Column(SAEnum(SensorType), nullable=False)
    x = Column(Float, nullable=False)   # 도면 위 위치
    y = Column(Float, nullable=False)
    status = Column(SAEnum(SensorStatus), default=SensorStatus.NORMAL)
    last_value = Column(Float)          # 최근 측정값
    last_updated = Column(DateTime(timezone=True), server_default=func.now())
    installed_at = Column(DateTime(timezone=True), server_default=func.now())
