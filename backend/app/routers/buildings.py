from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
import os
import uuid

from app.models.database import get_db
from app.models.building import Building, Floor, FloorNode, FloorEdge, FloorAnchor

router = APIRouter(prefix="/api/buildings", tags=["buildings"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")


# --- Request Schemas ---

class BuildingCreate(BaseModel):
    name: str
    address: Optional[str] = None
    total_floors: int = 1


class FloorCreate(BaseModel):
    floor_number: int
    name: Optional[str] = None
    width: Optional[float] = None
    height: Optional[float] = None


class NodeCreate(BaseModel):
    x: float
    y: float
    node_type: str = "path"  # path, exit, stair, elevator, room
    label: Optional[str] = None


class EdgeCreate(BaseModel):
    from_node_id: int
    to_node_id: int
    distance: Optional[float] = None


# --- Response Schemas ---

class BuildingResponse(BaseModel):
    id: int
    name: str
    address: Optional[str] = None
    total_floors: int

    class Config:
        from_attributes = True


class FloorResponse(BaseModel):
    id: int
    building_id: int
    floor_number: int
    name: Optional[str] = None
    floor_plan_url: Optional[str] = None
    width: Optional[float] = None
    height: Optional[float] = None

    class Config:
        from_attributes = True


class BuildingDetailResponse(BaseModel):
    id: int
    name: str
    address: Optional[str] = None
    total_floors: int
    floors: List[FloorResponse] = []


class NodeResponse(BaseModel):
    id: int
    floor_id: int
    x: float
    y: float
    node_type: str
    label: Optional[str] = None

    class Config:
        from_attributes = True


class EdgeResponse(BaseModel):
    id: int
    floor_id: int
    from_node_id: int
    to_node_id: int
    distance: Optional[float] = None
    is_blocked: int

    class Config:
        from_attributes = True


# --- Building ---

@router.get("/", response_model=List[BuildingResponse])
def list_buildings(db: Session = Depends(get_db)):
    """건물 목록"""
    return db.query(Building).all()


@router.post("/", response_model=BuildingResponse, status_code=201)
def create_building(data: BuildingCreate, db: Session = Depends(get_db)):
    """건물 등록"""
    building = Building(
        name=data.name,
        address=data.address,
        total_floors=data.total_floors,
    )
    db.add(building)
    db.commit()
    db.refresh(building)
    return building


@router.get("/{building_id}", response_model=BuildingDetailResponse)
def get_building(building_id: int, db: Session = Depends(get_db)):
    """건물 상세 (층 목록 포함)"""
    building = db.query(Building).filter(Building.id == building_id).first()
    if not building:
        raise HTTPException(status_code=404, detail="건물을 찾을 수 없습니다.")

    floors = db.query(Floor).filter(Floor.building_id == building_id).all()
    return BuildingDetailResponse(
        id=building.id,
        name=building.name,
        address=building.address,
        total_floors=building.total_floors,
        floors=[FloorResponse.model_validate(f) for f in floors],
    )


# --- Floor ---

@router.get("/{building_id}/floors", response_model=List[FloorResponse])
def list_floors(building_id: int, db: Session = Depends(get_db)):
    """층 목록"""
    building = db.query(Building).filter(Building.id == building_id).first()
    if not building:
        raise HTTPException(status_code=404, detail="건물을 찾을 수 없습니다.")

    return db.query(Floor).filter(Floor.building_id == building_id).all()


@router.post("/{building_id}/floors", response_model=FloorResponse, status_code=201)
def create_floor(building_id: int, data: FloorCreate, db: Session = Depends(get_db)):
    """층 등록"""
    building = db.query(Building).filter(Building.id == building_id).first()
    if not building:
        raise HTTPException(status_code=404, detail="건물을 찾을 수 없습니다.")

    floor = Floor(
        building_id=building_id,
        floor_number=data.floor_number,
        name=data.name,
        width=data.width,
        height=data.height,
    )
    db.add(floor)
    db.commit()
    db.refresh(floor)
    return floor


@router.post("/floors/{floor_id}/plan", response_model=FloorResponse)
def upload_floor_plan(floor_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """도면 이미지 업로드"""
    floor = db.query(Floor).filter(Floor.id == floor_id).first()
    if not floor:
        raise HTTPException(status_code=404, detail="층을 찾을 수 없습니다.")

    # 허용 확장자 검증
    allowed_extensions = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}
    ext = os.path.splitext(file.filename)[1].lower() if file.filename else ""
    if ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"허용되지 않는 파일 형식입니다. 허용: {allowed_extensions}")

    # uploads 디렉토리 보장
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # 고유 파일명 생성
    filename = f"floor_{floor_id}_{uuid.uuid4().hex[:8]}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    # 파일 저장
    with open(filepath, "wb") as f:
        content = file.file.read()
        f.write(content)

    # DB 업데이트
    floor.floor_plan_url = f"/uploads/{filename}"
    db.commit()
    db.refresh(floor)
    return floor


# --- Nodes & Edges (경로 그래프 편집) ---

@router.get("/floors/{floor_id}/nodes", response_model=List[NodeResponse])
def list_nodes(floor_id: int, db: Session = Depends(get_db)):
    """층의 노드 목록"""
    return db.query(FloorNode).filter(FloorNode.floor_id == floor_id).all()


@router.post("/floors/{floor_id}/nodes", response_model=NodeResponse, status_code=201)
def create_node(floor_id: int, data: NodeCreate, db: Session = Depends(get_db)):
    """노드 추가"""
    floor = db.query(Floor).filter(Floor.id == floor_id).first()
    if not floor:
        raise HTTPException(status_code=404, detail="층을 찾을 수 없습니다.")

    node = FloorNode(
        floor_id=floor_id,
        x=data.x,
        y=data.y,
        node_type=data.node_type,
        label=data.label,
    )
    db.add(node)
    db.commit()
    db.refresh(node)
    return node


@router.get("/floors/{floor_id}/edges", response_model=List[EdgeResponse])
def list_edges(floor_id: int, db: Session = Depends(get_db)):
    """층의 엣지 목록"""
    return db.query(FloorEdge).filter(FloorEdge.floor_id == floor_id).all()


@router.post("/floors/{floor_id}/edges", response_model=EdgeResponse, status_code=201)
def create_edge(floor_id: int, data: EdgeCreate, db: Session = Depends(get_db)):
    """엣지 추가"""
    floor = db.query(Floor).filter(Floor.id == floor_id).first()
    if not floor:
        raise HTTPException(status_code=404, detail="층을 찾을 수 없습니다.")

    # 노드 존재 확인
    from_node = db.query(FloorNode).filter(FloorNode.id == data.from_node_id).first()
    to_node = db.query(FloorNode).filter(FloorNode.id == data.to_node_id).first()
    if not from_node or not to_node:
        raise HTTPException(status_code=400, detail="존재하지 않는 노드입니다.")

    edge = FloorEdge(
        floor_id=floor_id,
        from_node_id=data.from_node_id,
        to_node_id=data.to_node_id,
        distance=data.distance,
        is_blocked=0,
    )
    db.add(edge)
    db.commit()
    db.refresh(edge)
    return edge


@router.put("/edges/{edge_id}/block", response_model=EdgeResponse)
def block_edge(edge_id: int, db: Session = Depends(get_db)):
    """엣지 차단 (화재로 경로 차단)"""
    edge = db.query(FloorEdge).filter(FloorEdge.id == edge_id).first()
    if not edge:
        raise HTTPException(status_code=404, detail="엣지를 찾을 수 없습니다.")

    edge.is_blocked = 1
    db.commit()
    db.refresh(edge)
    return edge


@router.put("/edges/{edge_id}/unblock", response_model=EdgeResponse)
def unblock_edge(edge_id: int, db: Session = Depends(get_db)):
    """엣지 차단 해제"""
    edge = db.query(FloorEdge).filter(FloorEdge.id == edge_id).first()
    if not edge:
        raise HTTPException(status_code=404, detail="엣지를 찾을 수 없습니다.")

    edge.is_blocked = 0
    db.commit()
    db.refresh(edge)
    return edge


# --- Anchors (GPS ↔ 도면 좌표 매핑 기준점) ---

class AnchorCreate(BaseModel):
    px_x: float
    px_y: float
    gps_lat: float
    gps_lng: float
    label: Optional[str] = None


class AnchorResponse(BaseModel):
    id: int
    floor_id: int
    px_x: float
    px_y: float
    gps_lat: float
    gps_lng: float
    label: Optional[str] = None

    class Config:
        from_attributes = True


@router.get("/floors/{floor_id}/anchors", response_model=List[AnchorResponse])
def list_anchors(floor_id: int, db: Session = Depends(get_db)):
    """층의 좌표 변환 기준점(앵커) 목록"""
    return db.query(FloorAnchor).filter(FloorAnchor.floor_id == floor_id).all()


@router.post("/floors/{floor_id}/anchors", response_model=AnchorResponse, status_code=201)
def create_anchor(floor_id: int, data: AnchorCreate, db: Session = Depends(get_db)):
    """좌표 변환 기준점 추가 (최소 2개 필요)"""
    floor = db.query(Floor).filter(Floor.id == floor_id).first()
    if not floor:
        raise HTTPException(status_code=404, detail="층을 찾을 수 없습니다.")

    anchor = FloorAnchor(
        floor_id=floor_id,
        px_x=data.px_x,
        px_y=data.px_y,
        gps_lat=data.gps_lat,
        gps_lng=data.gps_lng,
        label=data.label,
    )
    db.add(anchor)
    db.commit()
    db.refresh(anchor)
    return anchor


@router.delete("/anchors/{anchor_id}", status_code=204)
def delete_anchor(anchor_id: int, db: Session = Depends(get_db)):
    """기준점 삭제"""
    anchor = db.query(FloorAnchor).filter(FloorAnchor.id == anchor_id).first()
    if not anchor:
        raise HTTPException(status_code=404, detail="기준점을 찾을 수 없습니다.")

    db.delete(anchor)
    db.commit()
    return None


@router.post("/floors/{floor_id}/convert/gps-to-floor")
def convert_gps_to_floor(
    floor_id: int,
    lat: float,
    lng: float,
    db: Session = Depends(get_db),
):
    """GPS 좌표 → 도면 좌표 변환 (테스트/디버그용)"""
    from app.services.coordinate import gps_to_floor

    result = gps_to_floor(lat, lng, floor_id, db)
    if result is None:
        raise HTTPException(status_code=400, detail="앵커가 부족합니다 (최소 2개 필요)")

    px_x, px_y = result
    return {"floor_id": floor_id, "px_x": round(px_x, 2), "px_y": round(px_y, 2)}
