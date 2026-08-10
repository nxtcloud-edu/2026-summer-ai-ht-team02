from sqlalchemy.orm import Session
from typing import List

from app.models.location import EvacuationStatus
from app.services.alert import create_sos_alert


def send_sos(
    sender_id: int,
    floor_id: int,
    x: float,
    y: float,
    message: str = None,
    db: Session = None,
) -> dict:
    """동료에게 SOS 전송"""
    # SOS 알림 생성
    alert_info = create_sos_alert(sender_id, floor_id, x, y, message, db)

    # 발신자 SOS 상태 업데이트
    evac_status = db.query(EvacuationStatus).filter(EvacuationStatus.user_id == sender_id).first()
    if evac_status:
        evac_status.sos_sent = True
        db.commit()

    # 같은 층 근처 동료 목록 (WebSocket으로 push할 대상)
    nearby = get_nearby_peers(sender_id, floor_id, x, y, radius=50.0, db=db)

    return {
        **alert_info,
        "nearby_peers": nearby,
    }


def get_nearby_peers(
    user_id: int,
    floor_id: int,
    x: float,
    y: float,
    radius: float = 30.0,
    db: Session = None,
) -> List[dict]:
    """반경 내 동료 목록"""
    workers = (
        db.query(EvacuationStatus)
        .filter(EvacuationStatus.last_floor_id == floor_id)
        .filter(EvacuationStatus.user_id != user_id)
        .filter(EvacuationStatus.status.in_(["in_building", "evacuating"]))
        .all()
    )

    nearby = []
    for w in workers:
        if w.last_x is None or w.last_y is None:
            continue
        dist = ((w.last_x - x) ** 2 + (w.last_y - y) ** 2) ** 0.5
        if dist <= radius:
            nearby.append({
                "user_id": w.user_id,
                "x": w.last_x,
                "y": w.last_y,
                "distance": round(dist, 1),
                "status": w.status,
            })

    nearby.sort(key=lambda p: p["distance"])
    return nearby
