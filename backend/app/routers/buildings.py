from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from app.models.database import get_db

router = APIRouter(prefix="/api/buildings", tags=["buildings"])


# --- Schemas ---

class BuildingCreate(BaseModel):
    name: str
    address: Optional[str] = None
    total_floors: int = 1


class FloorCreate(BaseModel):
    building_id: int
    floor_number: int
    name: Optional[str] = None
    width: Optional[float] = None
    height: Optional[float] = None


class NodeCreate(BaseModel):
    floor_id: int
    x: float
    y: float
    node_type: str = "path"  # path, exit, stair, elevator, room
    label: Optional[str] = None


class EdgeCreate(BaseModel):
    floor_id: int
    from_node_id: int
    to_node_id: int
    distance: Optional[float] = None


# --- Building ---

@router.get("/")
def list_buildings(db: Session = Depends(get_db)):
    """건물 목록"""
    # TODO: 구현
    pass


@router.post("/")
def create_building(data: BuildingCreate, db: Session = Depends(get_db)):
    """건물 등록"""
    # TODO: 구현
    pass


@router.get("/{building_id}")
def get_building(building_id: int, db: Session = Depends(get_db)):
    """건물 상세 (층 목록 포함)"""
    # TODO: 구현
    pass


# --- Floor ---

@router.get("/{building_id}/floors")
def list_floors(building_id: int, db: Session = Depends(get_db)):
    """층 목록"""
    # TODO: 구현
    pass


@router.post("/{building_id}/floors")
def create_floor(building_id: int, data: FloorCreate, db: Session = Depends(get_db)):
    """층 등록"""
    # TODO: 구현
    pass


@router.post("/floors/{floor_id}/plan")
def upload_floor_plan(floor_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """도면 이미지 업로드"""
    # TODO: 구현
    pass


# --- Nodes & Edges (경로 그래프 편집) ---

@router.get("/floors/{floor_id}/nodes")
def list_nodes(floor_id: int, db: Session = Depends(get_db)):
    """층의 노드 목록"""
    # TODO: 구현
    pass


@router.post("/floors/{floor_id}/nodes")
def create_node(floor_id: int, data: NodeCreate, db: Session = Depends(get_db)):
    """노드 추가"""
    # TODO: 구현
    pass


@router.get("/floors/{floor_id}/edges")
def list_edges(floor_id: int, db: Session = Depends(get_db)):
    """층의 엣지 목록"""
    # TODO: 구현
    pass


@router.post("/floors/{floor_id}/edges")
def create_edge(floor_id: int, data: EdgeCreate, db: Session = Depends(get_db)):
    """엣지 추가"""
    # TODO: 구현
    pass


@router.put("/edges/{edge_id}/block")
def block_edge(edge_id: int, db: Session = Depends(get_db)):
    """엣지 차단 (화재로 경로 차단)"""
    # TODO: 구현
    pass


@router.put("/edges/{edge_id}/unblock")
def unblock_edge(edge_id: int, db: Session = Depends(get_db)):
    """엣지 차단 해제"""
    # TODO: 구현
    pass
