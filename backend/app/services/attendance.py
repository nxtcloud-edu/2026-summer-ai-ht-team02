from datetime import datetime, date
from typing import Optional, List

from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func

from app.models.attendance import Attendance
from app.models.building import FloorNode


# gate 인식 반경 (px 또는 m — 도면 좌표 기준)
GATE_DETECTION_RADIUS = 5.0


def auto_check_by_location(
    user_id: int, floor_id: int, x: float, y: float, db: Session
) -> Optional[str]:
    """
    gate 노드 반경 내 진입 감지 → 출근/퇴근 자동 기록.
    반환: "in", "out", 또는 None (gate 근처 아님)
    """
    # 해당 층의 gate 노드 조회
    gates = (
        db.query(FloorNode)
        .filter(FloorNode.floor_id == floor_id, FloorNode.node_type == "gate")
        .all()
    )

    if not gates:
        return None

    # 가장 가까운 gate 찾기
    nearest_gate = None
    min_dist = float("inf")
    for gate in gates:
        dist = ((gate.x - x) ** 2 + (gate.y - y) ** 2) ** 0.5
        if dist < min_dist:
            min_dist = dist
            nearest_gate = gate

    # 반경 밖이면 무시
    if min_dist > GATE_DETECTION_RADIUS:
        return None

    # 오늘 이미 기록이 있는지 확인 (중복 방지)
    today_start = datetime.combine(date.today(), datetime.min.time())
    existing = (
        db.query(Attendance)
        .filter(
            Attendance.user_id == user_id,
            Attendance.checked_at >= today_start,
        )
        .order_by(Attendance.checked_at.desc())
        .first()
    )

    # 출퇴근 판정: 마지막 기록이 없거나 "out"이면 → "in", "in"이면 → "out"
    if existing is None:
        check_type = "in"
    elif existing.check_type == "in":
        # 같은 gate에서 연속 "in" 방지 — 최소 5분 간격
        elapsed = (datetime.utcnow() - existing.checked_at).total_seconds()
        if elapsed < 300:
            return None
        check_type = "out"
    else:
        check_type = "in"

    # 기록 생성
    record = Attendance(
        user_id=user_id,
        gate_id=nearest_gate.id,
        check_type=check_type,
        method="auto",
    )
    db.add(record)
    db.commit()

    return check_type


def manual_check(user_id: int, check_type: str, db: Session) -> dict:
    """수동 출근/퇴근 기록"""
    record = Attendance(
        user_id=user_id,
        gate_id=None,
        check_type=check_type,
        method="manual",
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {
        "id": record.id,
        "user_id": record.user_id,
        "check_type": record.check_type,
        "checked_at": str(record.checked_at),
        "method": record.method,
    }


def get_today_attendance(db: Session) -> List[dict]:
    """전체 근로자 오늘 출퇴근 현황"""
    today_start = datetime.combine(date.today(), datetime.min.time())
    records = (
        db.query(Attendance)
        .filter(Attendance.checked_at >= today_start)
        .order_by(Attendance.checked_at.desc())
        .all()
    )

    return [
        {
            "id": r.id,
            "user_id": r.user_id,
            "gate_id": r.gate_id,
            "check_type": r.check_type,
            "checked_at": str(r.checked_at),
            "method": r.method,
        }
        for r in records
    ]


def get_user_attendance(user_id: int, db: Session, days: int = 7) -> List[dict]:
    """개인 출퇴근 이력 (최근 N일)"""
    from datetime import timedelta

    since = datetime.utcnow() - timedelta(days=days)
    records = (
        db.query(Attendance)
        .filter(Attendance.user_id == user_id, Attendance.checked_at >= since)
        .order_by(Attendance.checked_at.desc())
        .all()
    )

    return [
        {
            "id": r.id,
            "gate_id": r.gate_id,
            "check_type": r.check_type,
            "checked_at": str(r.checked_at),
            "method": r.method,
        }
        for r in records
    ]
