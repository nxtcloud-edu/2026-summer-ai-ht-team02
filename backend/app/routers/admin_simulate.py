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


@router.post("/health/{user_id}")
async def simulate_health(
    user_id: int,
    hr: int = 130,
    temp: float = 39.2,
    db: Session = Depends(get_db),
):
    """데모용: 건강 데이터 시뮬레이션 (이상치 투입)

    Query params:
        hr: 심박수 (기본값: 130)
        temp: 체온 (기본값: 39.2)
    """
    from app.services.health_monitor import record_and_check

    result = record_and_check(user_id=user_id, heart_rate=hr, temperature=temp, db=db)

    # 이상 감지 시 WebSocket push
    if result.get("anomaly_detected"):
        msg = {
            "type": "health_anomaly",
            "user_id": user_id,
            "anomaly_type": result.get("anomaly_type"),
            "value": result.get("value"),
            "baseline_avg": result.get("baseline_avg"),
            "z_score": result.get("z_score"),
            "consecutive_count": result.get("consecutive_count"),
            "action": result.get("action"),
            "source": "admin_simulate",
        }
        await manager.broadcast_to_admins(msg)
        await manager.broadcast_to_rescuers(msg)

    return {
        "success": True,
        "message": f"User {user_id} → health data recorded (hr={hr}, temp={temp})",
        "result": result,
    }
