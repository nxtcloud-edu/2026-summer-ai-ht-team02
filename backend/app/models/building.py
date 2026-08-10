from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON
from sqlalchemy.sql import func

from app.models.database import Base


class Building(Base):
    """건물"""
    __tablename__ = "buildings"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    address = Column(String)
    total_floors = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Floor(Base):
    """층"""
    __tablename__ = "floors"

    id = Column(Integer, primary_key=True, index=True)
    building_id = Column(Integer, nullable=False)
    floor_number = Column(Integer, nullable=False)
    name = Column(String)               # "B1", "1F", "2F" 등
    floor_plan_url = Column(String)     # 도면 이미지 경로
    width = Column(Float)               # 도면 가로 (px 또는 m)
    height = Column(Float)              # 도면 세로
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class FloorNode(Base):
    """도면 위 노드 (경로 탐색용 그래프 노드)"""
    __tablename__ = "floor_nodes"

    id = Column(Integer, primary_key=True, index=True)
    floor_id = Column(Integer, nullable=False)
    x = Column(Float, nullable=False)   # 도면 위 X 좌표
    y = Column(Float, nullable=False)   # 도면 위 Y 좌표
    node_type = Column(String, default="path")  # path, exit, stair, elevator, room
    label = Column(String)              # 출구A, 계단1 등


class FloorEdge(Base):
    """노드 간 연결 (경로 탐색용 그래프 엣지)"""
    __tablename__ = "floor_edges"

    id = Column(Integer, primary_key=True, index=True)
    floor_id = Column(Integer, nullable=False)
    from_node_id = Column(Integer, nullable=False)
    to_node_id = Column(Integer, nullable=False)
    distance = Column(Float)            # 거리 (가중치)
    is_blocked = Column(Integer, default=0)  # 0: 통행가능, 1: 차단(화재 등)


class FloorAnchor(Base):
    """도면 기준점 — GPS 좌표 ↔ 도면 px 좌표 매핑용 (최소 2개 필요)"""
    __tablename__ = "floor_anchors"

    id = Column(Integer, primary_key=True, index=True)
    floor_id = Column(Integer, nullable=False)
    # 도면 좌표 (px)
    px_x = Column(Float, nullable=False)
    px_y = Column(Float, nullable=False)
    # GPS 좌표
    gps_lat = Column(Float, nullable=False)
    gps_lng = Column(Float, nullable=False)
    label = Column(String)              # "출입구A", "비상구B" 등
