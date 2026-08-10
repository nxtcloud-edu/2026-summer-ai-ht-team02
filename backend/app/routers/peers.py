from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.models.database import get_db

router = APIRouter(prefix="/api/peers", tags=["peers"])


# --- Schemas ---

class SOSRequest(BaseModel):
    sender_id: int
    floor_id: int
    x: float
    y: float
    message: Optional[str] = None


class SOSResponse(BaseModel):
    responder_id: int
    sos_alert_id: int
    message: Optional[str] = None


# --- Endpoints ---

@router.post("/sos")
def send_sos(data: SOSRequest, db: Session = Depends(get_db)):
    """동료에게 SOS 전송 (위기 상황)"""
    # TODO: 구현 — 같은 층/인근 동료에게 WebSocket push
    pass


@router.post("/sos/{alert_id}/respond")
def respond_to_sos(alert_id: int, data: SOSResponse, db: Session = Depends(get_db)):
    """SOS에 응답 (도움 가겠다는 의사 표시)"""
    # TODO: 구현
    pass


@router.get("/nearby/{user_id}")
def get_nearby_peers(user_id: int, radius: float = 30.0, db: Session = Depends(get_db)):
    """근처 동료 목록 (반경 내 위치한 근로자)"""
    # TODO: 구현
    pass


@router.get("/sos/active")
def get_active_sos(db: Session = Depends(get_db)):
    """현재 활성 SOS 목록"""
    # TODO: 구현
    pass
