from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from app.models.database import get_db
from app.models.location import EvacuationStatus
from app.models.user import User
from app.services.evacuation import calculate_evacuation_route, calculate_rescuer_route
from app.services.location import get_unconscious_workers as svc_get_unconscious

router = APIRouter(prefix="/api/evacuation", tags=["evacuation"])


# --- Request Schemas ---

class RouteRequest(BaseModel):
    user_id: int
    floor_id: int
    x: float
    y: float


class EvacuationStatusUpdate(BaseModel):
    user_id: int
    status: str  # in_building, evacuating, evacuated, unconscious


# --- Response Schemas ---

class PathNode(BaseModel):
    node_id: int
    x: float
    y: float
    node_type: str


class RouteResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    start_node: Optional[int] = None
    exit_node: Optional[int] = None
    distance: Optional[float] = None
    path: Optional[List[PathNode]] = None


class RescuerRouteResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    start_node: Optional[int] = None
    target_node: Optional[int] = None
    distance: Optional[float] = None
    path: Optional[List[PathNode]] = None


class EvacuationStatusResponse(BaseModel):
    user_id: int
    user_name: Optional[str] = None
    status: str
    last_floor_id: Optional[int] = None
    last_x: Optional[float] = None
    last_y: Optional[float] = None
    is_moving: Optional[bool] = None
    heart_rate: Optional[int] = None
    sos_sent: Optional[bool] = None
    updated_at: Optional[str] = None


class UnconsciousWorker(BaseModel):
    user_id: int
    floor_id: Optional[int] = None
    x: Optional[float] = None
    y: Optional[float] = None
    heart_rate: Optional[int] = None
    updated_at: Optional[str] = None


VALID_STATUSES = {"in_building", "evacuating", "evacuated", "unconscious"}


# --- Endpoints ---

@router.post("/route", response_model=RouteResponse)
def get_evacuation_route(data: RouteRequest, db: Session = Depends(get_db)):
    """현재 위치 기반 최적 탈출 경로 계산"""
    result = calculate_evacuation_route(data.floor_id, data.x, data.y, db)

    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("message", "경로를 찾을 수 없습니다."))

    return RouteResponse(
        success=True,
        start_node=result["start_node"],
        exit_node=result["exit_node"],
        distance=result["distance"],
        path=[PathNode(**node) for node in result["path"]],
    )


@router.get("/status", response_model=List[EvacuationStatusResponse])
def get_all_evacuation_status(db: Session = Depends(get_db)):
    """전체 대피 현황 (관리자/구조대용)"""
    statuses = db.query(EvacuationStatus).all()

    results = []
    for s in statuses:
        user = db.query(User).filter(User.id == s.user_id).first()
        results.append(EvacuationStatusResponse(
            user_id=s.user_id,
            user_name=user.name if user else None,
            status=s.status,
            last_floor_id=s.last_floor_id,
            last_x=s.last_x,
            last_y=s.last_y,
            is_moving=s.is_moving,
            heart_rate=s.heart_rate,
            sos_sent=s.sos_sent,
            updated_at=str(s.updated_at) if s.updated_at else None,
        ))

    return results


@router.get("/status/{user_id}", response_model=EvacuationStatusResponse)
def get_user_evacuation_status(user_id: int, db: Session = Depends(get_db)):
    """특정 근로자 대피 상태"""
    s = db.query(EvacuationStatus).filter(EvacuationStatus.user_id == user_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="해당 사용자의 대피 상태가 없습니다.")

    user = db.query(User).filter(User.id == s.user_id).first()
    return EvacuationStatusResponse(
        user_id=s.user_id,
        user_name=user.name if user else None,
        status=s.status,
        last_floor_id=s.last_floor_id,
        last_x=s.last_x,
        last_y=s.last_y,
        is_moving=s.is_moving,
        heart_rate=s.heart_rate,
        sos_sent=s.sos_sent,
        updated_at=str(s.updated_at) if s.updated_at else None,
    )


@router.put("/status", response_model=EvacuationStatusResponse)
def update_evacuation_status(data: EvacuationStatusUpdate, db: Session = Depends(get_db)):
    """대피 상태 갱신"""
    if data.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"유효하지 않은 상태입니다. 허용값: {', '.join(VALID_STATUSES)}",
        )

    s = db.query(EvacuationStatus).filter(EvacuationStatus.user_id == data.user_id).first()
    if s:
        s.status = data.status
        s.updated_at = datetime.utcnow()
    else:
        s = EvacuationStatus(
            user_id=data.user_id,
            status=data.status,
        )
        db.add(s)

    db.commit()
    db.refresh(s)

    user = db.query(User).filter(User.id == s.user_id).first()
    return EvacuationStatusResponse(
        user_id=s.user_id,
        user_name=user.name if user else None,
        status=s.status,
        last_floor_id=s.last_floor_id,
        last_x=s.last_x,
        last_y=s.last_y,
        is_moving=s.is_moving,
        heart_rate=s.heart_rate,
        sos_sent=s.sos_sent,
        updated_at=str(s.updated_at) if s.updated_at else None,
    )


@router.get("/unconscious", response_model=List[UnconsciousWorker])
def get_unconscious_workers_endpoint(db: Session = Depends(get_db)):
    """의식 불명/미대피 근로자 목록 (구조대 뷰)"""
    workers = svc_get_unconscious(db)
    return [UnconsciousWorker(**w) for w in workers]


@router.get("/rescuer-route/{target_user_id}", response_model=RescuerRouteResponse)
def get_rescuer_route(
    target_user_id: int,
    floor_id: int,
    x: float,
    y: float,
    db: Session = Depends(get_db),
):
    """구조대원 → 미대피자까지 최적 진입 경로"""
    # 대상자의 마지막 위치 조회
    target_status = (
        db.query(EvacuationStatus)
        .filter(EvacuationStatus.user_id == target_user_id)
        .first()
    )
    if not target_status:
        raise HTTPException(status_code=404, detail="대상자의 위치 정보가 없습니다.")

    if target_status.last_x is None or target_status.last_y is None:
        raise HTTPException(status_code=404, detail="대상자의 좌표 정보가 없습니다.")

    # 구조대원 위치(floor_id, x, y)에서 대상자 위치까지 경로 계산
    # 같은 층인 경우만 경로 계산 (다층 경로는 추후 확장)
    target_floor = target_status.last_floor_id
    if target_floor != floor_id:
        raise HTTPException(
            status_code=400,
            detail=f"구조대원과 대상자가 다른 층에 있습니다. (구조대원: {floor_id}층, 대상자: {target_floor}층)",
        )

    result = calculate_rescuer_route(
        floor_id=floor_id,
        rescuer_x=x,
        rescuer_y=y,
        target_x=target_status.last_x,
        target_y=target_status.last_y,
        db=db,
    )

    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("message", "경로를 찾을 수 없습니다."))

    return RescuerRouteResponse(
        success=True,
        start_node=result["start_node"],
        target_node=result["target_node"],
        distance=result["distance"],
        path=[PathNode(**node) for node in result["path"]],
    )
