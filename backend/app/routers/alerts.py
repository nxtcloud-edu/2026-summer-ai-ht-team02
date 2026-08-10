from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from app.models.database import get_db
from app.models.alert import Alert
from app.services.alert import (
    create_fire_alert,
    get_active_alerts as svc_get_active,
    resolve_alert as svc_resolve,
)

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


# --- Request Schemas ---

class FireAlertCreate(BaseModel):
    floor_id: int
    x: Optional[float] = None
    y: Optional[float] = None
    message: Optional[str] = None


# --- Response Schemas ---

class FireAlertResponse(BaseModel):
    alert_id: int
    type: str
    level: str
    floor_id: int
    message: str


class AlertResponse(BaseModel):
    id: int
    type: str
    level: str
    floor_id: Optional[int] = None
    x: Optional[float] = None
    y: Optional[float] = None
    message: Optional[str] = None
    source_user_id: Optional[int] = None
    is_resolved: bool
    created_at: Optional[str] = None
    resolved_at: Optional[str] = None


# --- Endpoints ---

@router.post("/fire", response_model=FireAlertResponse, status_code=201)
def trigger_fire_alert(data: FireAlertCreate, db: Session = Depends(get_db)):
    """
    화재 알림 발생 → 해당 반경 엣지 자동 차단 + 알림 생성

    - 화재 위치(x, y) 주변 반경 50px 내 노드가 포함된 엣지를 자동 차단
    - 전체 근로자에게 화재 알림 전송 (WebSocket은 별도)
    """
    result = create_fire_alert(
        floor_id=data.floor_id,
        x=data.x,
        y=data.y,
        message=data.message,
        db=db,
    )

    return FireAlertResponse(
        alert_id=result["alert_id"],
        type=result["type"],
        level=result["level"],
        floor_id=result["floor_id"],
        message=result["message"],
    )


@router.get("/active", response_model=List[AlertResponse])
def get_active_alerts(db: Session = Depends(get_db)):
    """현재 활성 알림 목록 (해제되지 않은 알림)"""
    alerts = svc_get_active(db)
    return [
        AlertResponse(
            id=a["id"],
            type=a["type"],
            level=a["level"],
            floor_id=a["floor_id"],
            x=a["x"],
            y=a["y"],
            message=a["message"],
            source_user_id=a["source_user_id"],
            is_resolved=False,
            created_at=a["created_at"],
        )
        for a in alerts
    ]


@router.get("/history", response_model=List[AlertResponse])
def get_alert_history(limit: int = 50, db: Session = Depends(get_db)):
    """알림 이력 (최신순)"""
    alerts = (
        db.query(Alert)
        .order_by(Alert.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        AlertResponse(
            id=a.id,
            type=a.alert_type.value,
            level=a.level.value,
            floor_id=a.floor_id,
            x=a.x,
            y=a.y,
            message=a.message,
            source_user_id=a.source_user_id,
            is_resolved=a.is_resolved,
            created_at=str(a.created_at) if a.created_at else None,
            resolved_at=str(a.resolved_at) if a.resolved_at else None,
        )
        for a in alerts
    ]


@router.put("/{alert_id}/resolve")
def resolve_alert(alert_id: int, db: Session = Depends(get_db)):
    """
    알림 해제 (상황 종료)

    - 화재 알림인 경우 차단된 엣지를 자동 복구
    """
    success = svc_resolve(alert_id, db)
    if not success:
        raise HTTPException(status_code=404, detail="알림을 찾을 수 없습니다.")

    return {"message": "알림이 해제되었습니다.", "alert_id": alert_id}
