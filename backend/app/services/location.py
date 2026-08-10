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


def check_stale_locations(db: Session, timeout_seconds: int = 30) -> List[int]:
    """
    위치 갱신이 timeout_seconds 이상 없는 유저를 찾아
    is_moving=False로 전환. 반환값: 전환된 user_id 리스트
    """
    threshold = datetime.utcnow() - timedelta(seconds=timeout_seconds)
    stale = (
        db.query(EvacuationStatus)
        .filter(EvacuationStatus.updated_at < threshold)
        .filter(EvacuationStatus.is_moving == True)
        .filter(EvacuationStatus.status.in_(["in_building", "evacuating"]))
        .all()
    )
    stale_user_ids = []
    for s in stale:
        s.is_moving = False
        stale_user_ids.append(s.user_id)
    if stale_user_ids:
        db.commit()
    return stale_user_ids


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


def get_user_current_location(user_id: int, db: Session) -> Optional[dict]:
    """특정 근로자의 현재 위치 (EvacuationStatus 기반)"""
    evac_status = db.query(EvacuationStatus).filter(EvacuationStatus.user_id == user_id).first()
    if not evac_status:
        return None

    return {
        "user_id": evac_status.user_id,
        "floor_id": evac_status.last_floor_id,
        "x": evac_status.last_x,
        "y": evac_status.last_y,
        "status": evac_status.status,
        "is_moving": evac_status.is_moving,
        "heart_rate": evac_status.heart_rate,
        "updated_at": str(evac_status.updated_at) if evac_status.updated_at else None,
    }


def get_all_current_locations(db: Session) -> List[dict]:
    """전체 재실자 현재 위치 목록"""
    statuses = (
        db.query(EvacuationStatus)
        .filter(EvacuationStatus.status.in_(["in_building", "evacuating"]))
        .all()
    )

    return [
        {
            "user_id": s.user_id,
            "floor_id": s.last_floor_id,
            "x": s.last_x,
            "y": s.last_y,
            "status": s.status,
            "is_moving": s.is_moving,
            "heart_rate": s.heart_rate,
            "updated_at": str(s.updated_at) if s.updated_at else None,
        }
        for s in statuses
    ]


def get_location_history(user_id: int, db: Session, limit: int = 50) -> List[dict]:
    """위치 이력 조회 (이동 경로 추적)"""
    locations = (
        db.query(WorkerLocation)
        .filter(WorkerLocation.user_id == user_id)
        .order_by(WorkerLocation.timestamp.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": loc.id,
            "floor_id": loc.floor_id,
            "x": loc.x,
            "y": loc.y,
            "accuracy": loc.accuracy,
            "timestamp": str(loc.timestamp) if loc.timestamp else None,
        }
        for loc in locations
    ]
