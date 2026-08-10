from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Optional

from app.models.location import WorkerLocation, EvacuationStatus


def update_worker_location(
    user_id: int,
    floor_id: int,
    x: float,
    y: float,
    accuracy: Optional[float],
    heart_rate: Optional[int],
    db: Session,
) -> dict:
    """스마트워치에서 위치 갱신"""
    # 위치 기록 추가
    location = WorkerLocation(
        user_id=user_id,
        floor_id=floor_id,
        x=x,
        y=y,
        accuracy=accuracy,
    )
    db.add(location)

    # 대피 상태 업데이트
    evac_status = db.query(EvacuationStatus).filter(EvacuationStatus.user_id == user_id).first()
    if evac_status:
        evac_status.last_floor_id = floor_id
        evac_status.last_x = x
        evac_status.last_y = y
        evac_status.updated_at = datetime.utcnow()
        if heart_rate is not None:
            evac_status.heart_rate = heart_rate
        # 움직임 감지: 이전 위치와 비교
        evac_status.is_moving = True
    else:
        evac_status = EvacuationStatus(
            user_id=user_id,
            status="in_building",
            last_floor_id=floor_id,
            last_x=x,
            last_y=y,
            heart_rate=heart_rate,
            is_moving=True,
        )
        db.add(evac_status)

    db.commit()
    return {"user_id": user_id, "floor_id": floor_id, "x": x, "y": y}


def detect_unconscious(user_id: int, db: Session, timeout_seconds: int = 30) -> bool:
    """의식 불명 감지: 일정 시간 움직임 없음 + 비정상 심박"""
    evac_status = db.query(EvacuationStatus).filter(EvacuationStatus.user_id == user_id).first()
    if not evac_status:
        return False

    # 마지막 업데이트 이후 timeout 초과
    if evac_status.updated_at:
        elapsed = (datetime.utcnow() - evac_status.updated_at).total_seconds()
        if elapsed > timeout_seconds and not evac_status.is_moving:
            return True

    # 심박수 비정상 (40 이하 또는 감지 안됨)
    if evac_status.heart_rate is not None and evac_status.heart_rate < 40:
        return True

    return False


def get_floor_workers(floor_id: int, db: Session) -> List[dict]:
    """특정 층의 현재 재실자 목록"""
    statuses = (
        db.query(EvacuationStatus)
        .filter(EvacuationStatus.last_floor_id == floor_id)
        .filter(EvacuationStatus.status.in_(["in_building", "evacuating"]))
        .all()
    )

    return [
        {
            "user_id": s.user_id,
            "x": s.last_x,
            "y": s.last_y,
            "status": s.status,
            "is_moving": s.is_moving,
            "heart_rate": s.heart_rate,
            "sos_sent": s.sos_sent,
        }
        for s in statuses
    ]


def get_unconscious_workers(db: Session) -> List[dict]:
    """의식 불명 / 미대피 근로자 목록"""
    workers = (
        db.query(EvacuationStatus)
        .filter(EvacuationStatus.status == "unconscious")
        .all()
    )

    return [
        {
            "user_id": w.user_id,
            "floor_id": w.last_floor_id,
            "x": w.last_x,
            "y": w.last_y,
            "heart_rate": w.heart_rate,
            "updated_at": str(w.updated_at) if w.updated_at else None,
        }
        for w in workers
    ]
