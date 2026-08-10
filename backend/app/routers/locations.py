from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from app.models.database import get_db
from app.models.user import User, UserRole
from app.dependencies import get_current_user, require_role
from app.services.location import (
    update_worker_location,
    detect_unconscious,
    get_user_current_location,
    get_all_current_locations,
    get_floor_workers,
    get_location_history,
)
from app.services.alert import create_unconscious_alert
from app.models.location import EvacuationStatus
from app.websocket_manager import manager
from app.config import settings

router = APIRouter(prefix="/api/locations", tags=["locations"])


# --- Schemas ---

class LocationUpdateRequest(BaseModel):
    """스마트폰 GPS 위치 갱신 요청"""
    floor_id: int
    x: float  # 도면 좌표 또는 경도 (longitude)
    y: float  # 도면 좌표 또는 위도 (latitude)
    accuracy: Optional[float] = None  # GPS 정확도 (m)
    heart_rate: Optional[int] = None  # 스마트워치 연동 시


class LocationResponse(BaseModel):
    user_id: int
    floor_id: Optional[int] = None
    x: Optional[float] = None
    y: Optional[float] = None
    status: Optional[str] = None
    is_moving: Optional[bool] = None
    heart_rate: Optional[int] = None
    updated_at: Optional[str] = None


class LocationHistoryItem(BaseModel):
    id: int
    floor_id: int
    x: float
    y: float
    accuracy: Optional[float] = None
    timestamp: Optional[str] = None


class FloorWorkerResponse(BaseModel):
    user_id: int
    x: Optional[float] = None
    y: Optional[float] = None
    status: Optional[str] = None
    is_moving: Optional[bool] = None
    heart_rate: Optional[int] = None
    sos_sent: Optional[bool] = None


# --- Endpoints ---

@router.post("/update", response_model=LocationResponse)
async def update_location(
    data: LocationUpdateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    스마트폰에서 위치 갱신 (5초 주기 POST)

    - user_id는 JWT 토큰에서 자동 추출
    - 위치 이력 저장 + 대피 상태 업데이트
    - WebSocket으로 관리자/구조대에게 실시간 브로드캐스트
    """
    result = update_worker_location(
        user_id=current_user.id,
        floor_id=data.floor_id,
        x=data.x,
        y=data.y,
        accuracy=data.accuracy,
        heart_rate=data.heart_rate,
        db=db,
    )

    # WebSocket 브로드캐스트 (비동기 — 응답 지연 방지)
    await manager.broadcast_location_update(
        user_id=current_user.id,
        floor_id=data.floor_id,
        x=data.x,
        y=data.y,
    )

    # 심박 이상 감지: 임계값 이하이면 즉시 의식불명 판정
    if data.heart_rate is not None and data.heart_rate < settings.HEARTRATE_THRESHOLD_LOW:
        if detect_unconscious(current_user.id, db, settings.UNCONSCIOUS_TIMEOUT_SECONDS):
            evac = (
                db.query(EvacuationStatus)
                .filter(EvacuationStatus.user_id == current_user.id)
                .first()
            )
            if evac and evac.status != "unconscious":
                evac.status = "unconscious"
                evac.is_moving = False
                db.commit()

                create_unconscious_alert(
                    user_id=current_user.id,
                    floor_id=evac.last_floor_id,
                    x=evac.last_x,
                    y=evac.last_y,
                    reason="heartrate",
                    db=db,
                )

                msg = {
                    "type": "unconscious_detected",
                    "user_id": current_user.id,
                    "floor_id": evac.last_floor_id,
                    "x": evac.last_x,
                    "y": evac.last_y,
                    "reason": "abnormal_heartrate",
                    "heart_rate": data.heart_rate,
                }
                await manager.broadcast_to_rescuers(msg)
                await manager.broadcast_to_admins(msg)

    return LocationResponse(
        user_id=result["user_id"],
        floor_id=result["floor_id"],
        x=result["x"],
        y=result["y"],
    )


@router.get("/current", response_model=List[LocationResponse])
def get_all_locations(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.RESCUER)),
):
    """전체 근로자 현재 위치 (관리자/구조대용)"""
    locations = get_all_current_locations(db)
    return [LocationResponse(**loc) for loc in locations]


@router.get("/current/{user_id}", response_model=LocationResponse)
def get_user_location(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    특정 근로자 현재 위치

    - 본인 조회 또는 admin/rescuer만 타인 조회 가능
    """
    # 권한 검증: 본인이 아니면 admin 또는 rescuer여야 함
    if current_user.id != user_id and current_user.role not in (UserRole.ADMIN, UserRole.RESCUER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="다른 사용자의 위치를 조회할 권한이 없습니다",
        )

    location = get_user_current_location(user_id, db)
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="위치 정보가 없습니다",
        )
    return LocationResponse(**location)


@router.get("/floor/{floor_id}", response_model=List[FloorWorkerResponse])
def get_floor_locations(
    floor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.RESCUER)),
):
    """특정 층 재실자 위치 목록 (관리자/구조대용)"""
    workers = get_floor_workers(floor_id, db)
    return [FloorWorkerResponse(**w) for w in workers]


@router.get("/history/{user_id}", response_model=List[LocationHistoryItem])
def get_user_location_history(
    user_id: int,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    위치 이력 (이동 경로 추적)

    - 본인 이력 또는 admin/rescuer만 타인 이력 조회 가능
    """
    if current_user.id != user_id and current_user.role not in (UserRole.ADMIN, UserRole.RESCUER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="다른 사용자의 이력을 조회할 권한이 없습니다",
        )

    history = get_location_history(user_id, db, limit=limit)
    return [LocationHistoryItem(**item) for item in history]
