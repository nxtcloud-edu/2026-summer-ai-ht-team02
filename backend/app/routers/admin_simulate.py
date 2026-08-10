from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.database import get_db
from app.models.location import EvacuationStatus
from app.services.alert import create_unconscious_alert
from app.websocket_manager import manager

router = APIRouter(prefix="/api/admin/simulate", tags=["admin-simulate"])


@router.post("/unconscious/{user_id}")
async def simulate_unconscious(user_id: int, db: Session = Depends(get_db)):
    """데모용: 의식불명 강제 전환"""
    evac = db.query(EvacuationStatus).filter(EvacuationStatus.user_id == user_id).first()
    if not evac:
        raise HTTPException(status_code=404, detail="해당 유저의 대피 상태가 없습니다.")

    evac.status = "unconscious"
    evac.is_moving = False
    evac.updated_at = datetime.utcnow()
    db.commit()

    create_unconscious_alert(
        user_id=user_id,
        floor_id=evac.last_floor_id,
        x=evac.last_x,
        y=evac.last_y,
        reason="admin",
        db=db,
    )

    msg = {
        "type": "unconscious_detected",
        "user_id": user_id,
        "floor_id": evac.last_floor_id,
        "x": evac.last_x,
        "y": evac.last_y,
        "reason": "admin_trigger",
    }
    await manager.broadcast_to_rescuers(msg)
    await manager.broadcast_to_admins(msg)

    return {"success": True, "message": f"User {user_id} → unconscious (admin trigger)"}


@router.post("/fall/{user_id}")
async def simulate_fall(user_id: int, db: Session = Depends(get_db)):
    """데모용: 낙상 감지 트리거"""
    evac = db.query(EvacuationStatus).filter(EvacuationStatus.user_id == user_id).first()
    if not evac:
        raise HTTPException(status_code=404, detail="해당 유저의 대피 상태가 없습니다.")

    evac.status = "unconscious"
    evac.is_moving = False
    evac.updated_at = datetime.utcnow()
    db.commit()

    create_unconscious_alert(
        user_id=user_id,
        floor_id=evac.last_floor_id,
        x=evac.last_x,
        y=evac.last_y,
        reason="fall",
        db=db,
    )

    msg = {
        "type": "unconscious_detected",
        "user_id": user_id,
        "floor_id": evac.last_floor_id,
        "x": evac.last_x,
        "y": evac.last_y,
        "reason": "fall_detected",
    }
    await manager.broadcast_to_rescuers(msg)
    await manager.broadcast_to_admins(msg)

    return {"success": True, "message": f"User {user_id} → fall detected → unconscious"}


@router.post("/heartrate/{user_id}")
async def simulate_heartrate(user_id: int, bpm: int = 30, db: Session = Depends(get_db)):
    """데모용: 심박 이상 트리거

    Query params:
        bpm: 시뮬레이션할 심박수 (기본값: 30)
    """
    evac = db.query(EvacuationStatus).filter(EvacuationStatus.user_id == user_id).first()
    if not evac:
        raise HTTPException(status_code=404, detail="해당 유저의 대피 상태가 없습니다.")

    evac.heart_rate = bpm
    evac.status = "unconscious"
    evac.is_moving = False
    evac.updated_at = datetime.utcnow()
    db.commit()

    create_unconscious_alert(
        user_id=user_id,
        floor_id=evac.last_floor_id,
        x=evac.last_x,
        y=evac.last_y,
        reason="heartrate",
        db=db,
    )

    msg = {
        "type": "unconscious_detected",
        "user_id": user_id,
        "floor_id": evac.last_floor_id,
        "x": evac.last_x,
        "y": evac.last_y,
        "reason": "abnormal_heartrate",
        "heart_rate": bpm,
    }
    await manager.broadcast_to_rescuers(msg)
    await manager.broadcast_to_admins(msg)

    return {"success": True, "message": f"User {user_id} → heartrate {bpm}bpm → unconscious"}
