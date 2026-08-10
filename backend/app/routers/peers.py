from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from app.models.database import get_db
from app.models.location import EvacuationStatus
from app.models.user import User
from app.dependencies import get_current_user
from app.services.peers import send_sos, get_nearby_peers, respond_to_sos, get_active_sos
from app.websocket_manager import manager

router = APIRouter(prefix="/api/peers", tags=["peers"])


# --- Schemas ---

class SOSCreateRequest(BaseModel):
    floor_id: int
    x: float
    y: float
    message: Optional[str] = None


class SOSRespondRequest(BaseModel):
    message: Optional[str] = None


# --- Endpoints ---

@router.post("/sos", status_code=201)
async def create_sos(
    data: SOSCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """동료에게 SOS 전송 (위기 상황) — JWT에서 sender 추출"""
    result = send_sos(
        sender_id=current_user.id,
        floor_id=data.floor_id,
        x=data.x,
        y=data.y,
        message=data.message,
        db=db,
    )

    # WebSocket: 같은 층 동료에게 peer_sos push
    sos_ws_msg = {
        "type": "peer_sos",
        "alert_id": result["alert_id"],
        "sender_id": current_user.id,
        "sender_name": current_user.name,
        "floor_id": data.floor_id,
        "x": data.x,
        "y": data.y,
        "message": data.message,
    }
    await manager.send_to_floor_workers(data.floor_id, current_user.id, sos_ws_msg)

    # WebSocket: 관리자/구조대에게 sos_alert push
    admin_msg = {
        "type": "sos_alert",
        "alert_id": result["alert_id"],
        "sender_id": current_user.id,
        "sender_name": current_user.name,
        "floor_id": data.floor_id,
        "x": data.x,
        "y": data.y,
        "message": data.message,
    }
    await manager.broadcast_to_admins(admin_msg)
    await manager.broadcast_to_rescuers(admin_msg)

    return result


@router.post("/sos/{alert_id}/respond")
async def respond_sos(
    alert_id: int,
    data: SOSRespondRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """SOS에 응답 (도움 가겠다는 의사 표시) — JWT에서 responder 추출"""
    result = respond_to_sos(
        alert_id=alert_id,
        responder_id=current_user.id,
        message=data.message,
        db=db,
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="해당 SOS를 찾을 수 없거나 이미 응답했습니다",
        )

    # WebSocket: SOS 발신자에게 sos_responded push
    await manager.send_to_user(result["sender_id"], {
        "type": "sos_responded",
        "alert_id": alert_id,
        "responder_id": current_user.id,
        "responder_name": current_user.name,
        "message": data.message,
    })

    # WebSocket: 관리자/구조대에게 응답 현황 push
    update_msg = {
        "type": "sos_response_update",
        "alert_id": alert_id,
        "responder_id": current_user.id,
        "responder_name": current_user.name,
        "sender_id": result["sender_id"],
    }
    await manager.broadcast_to_admins(update_msg)
    await manager.broadcast_to_rescuers(update_msg)

    return result


@router.get("/nearby/{user_id}")
def get_nearby(
    user_id: int,
    radius: float = 30.0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """근처 동료 목록 (반경 내 위치한 근로자)"""
    # 대상 유저의 현재 위치 조회
    evac = (
        db.query(EvacuationStatus)
        .filter(EvacuationStatus.user_id == user_id)
        .first()
    )
    if not evac or evac.last_floor_id is None:
        raise HTTPException(status_code=404, detail="해당 유저의 위치 정보가 없습니다")

    nearby = get_nearby_peers(
        user_id=user_id,
        floor_id=evac.last_floor_id,
        x=evac.last_x or 0.0,
        y=evac.last_y or 0.0,
        radius=radius,
        db=db,
    )
    return nearby


@router.get("/sos/active")
def get_active_sos_list(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """현재 활성 SOS 목록"""
    return get_active_sos(db=db)
