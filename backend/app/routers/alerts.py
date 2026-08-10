from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.models.database import get_db

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


# --- Schemas ---

class FireAlertCreate(BaseModel):
    floor_id: int
    x: Optional[float] = None
    y: Optional[float] = None
    message: Optional[str] = None


class AlertResolve(BaseModel):
    alert_id: int


# --- Endpoints ---

@router.post("/fire")
def trigger_fire_alert(data: FireAlertCreate, db: Session = Depends(get_db)):
    """화재 알림 발생 → 해당 층/건물 전체 근로자에게 전송"""
    # TODO: 구현
    pass


@router.get("/active")
def get_active_alerts(db: Session = Depends(get_db)):
    """현재 활성 알림 목록"""
    # TODO: 구현
    pass


@router.get("/history")
def get_alert_history(limit: int = 50, db: Session = Depends(get_db)):
    """알림 이력"""
    # TODO: 구현
    pass


@router.put("/{alert_id}/resolve")
def resolve_alert(alert_id: int, db: Session = Depends(get_db)):
    """알림 해제 (상황 종료)"""
    # TODO: 구현
    pass
