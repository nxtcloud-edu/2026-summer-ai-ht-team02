from sqlalchemy.orm import Session
from datetime import datetime
from typing import List

from app.models.alert import Alert, AlertType, AlertLevel
from app.models.building import FloorEdge


def create_fire_alert(
    floor_id: int,
    x: float = None,
    y: float = None,
    message: str = None,
    db: Session = None,
) -> dict:
    """화재 알림 생성 + 해당 구역 경로 차단"""
    alert = Alert(
        alert_type=AlertType.FIRE,
        level=AlertLevel.CRITICAL,
        floor_id=floor_id,
        x=x,
        y=y,
        message=message or f"{floor_id}층 화재 발생",
    )
    db.add(alert)

    # 화재 위치 주변 엣지 차단 (반경 기반)
    if x is not None and y is not None:
        _block_nearby_edges(floor_id, x, y, radius=3000.0, db=db)

    db.commit()
    db.refresh(alert)

    return {
        "alert_id": alert.id,
        "type": alert.alert_type.value,
        "level": alert.level.value,
        "floor_id": floor_id,
        "message": alert.message,
    }


def create_sos_alert(
    sender_id: int,
    floor_id: int,
    x: float,
    y: float,
    message: str = None,
    db: Session = None,
) -> dict:
    """동료 SOS 알림 생성"""
    alert = Alert(
        alert_type=AlertType.SOS,
        level=AlertLevel.WARNING,
        floor_id=floor_id,
        x=x,
        y=y,
        message=message or "SOS 도움 요청",
        source_user_id=sender_id,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)

    return {
        "alert_id": alert.id,
        "type": alert.alert_type.value,
        "sender_id": sender_id,
        "floor_id": floor_id,
        "x": x,
        "y": y,
        "message": alert.message,
    }


def get_active_alerts(db: Session) -> List[dict]:
    """현재 활성 알림 목록"""
    alerts = db.query(Alert).filter(Alert.is_resolved == False).all()
    return [
        {
            "id": a.id,
            "type": a.alert_type.value,
            "level": a.level.value,
            "floor_id": a.floor_id,
            "x": a.x,
            "y": a.y,
            "message": a.message,
            "source_user_id": a.source_user_id,
            "created_at": str(a.created_at),
        }
        for a in alerts
    ]


def resolve_alert(alert_id: int, db: Session) -> bool:
    """알림 해제"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        return False

    alert.is_resolved = True
    alert.resolved_at = datetime.utcnow()

    # 화재 알림이면 차단된 엣지 복구
    if alert.alert_type == AlertType.FIRE and alert.x and alert.y:
        _unblock_nearby_edges(alert.floor_id, alert.x, alert.y, radius=3000.0, db=db)

    db.commit()
    return True


def _block_nearby_edges(floor_id: int, x: float, y: float, radius: float, db: Session):
    """화재 반경 내 엣지 차단"""
    from app.models.building import FloorNode

    # 반경 내 노드 찾기
    nodes = db.query(FloorNode).filter(FloorNode.floor_id == floor_id).all()
    nearby_node_ids = []
    for node in nodes:
        dist = ((node.x - x) ** 2 + (node.y - y) ** 2) ** 0.5
        if dist <= radius:
            nearby_node_ids.append(node.id)

    # 해당 노드가 포함된 엣지 차단
    if nearby_node_ids:
        edges = (
            db.query(FloorEdge)
            .filter(FloorEdge.floor_id == floor_id)
            .filter(
                (FloorEdge.from_node_id.in_(nearby_node_ids))
                | (FloorEdge.to_node_id.in_(nearby_node_ids))
            )
            .all()
        )
        for edge in edges:
            edge.is_blocked = 1


def _unblock_nearby_edges(floor_id: int, x: float, y: float, radius: float, db: Session):
    """엣지 차단 해제"""
    from app.models.building import FloorNode

    nodes = db.query(FloorNode).filter(FloorNode.floor_id == floor_id).all()
    nearby_node_ids = []
    for node in nodes:
        dist = ((node.x - x) ** 2 + (node.y - y) ** 2) ** 0.5
        if dist <= radius:
            nearby_node_ids.append(node.id)

    if nearby_node_ids:
        edges = (
            db.query(FloorEdge)
            .filter(FloorEdge.floor_id == floor_id)
            .filter(
                (FloorEdge.from_node_id.in_(nearby_node_ids))
                | (FloorEdge.to_node_id.in_(nearby_node_ids))
            )
            .all()
        )
        for edge in edges:
            edge.is_blocked = 0


def create_unconscious_alert(
    user_id: int,
    floor_id: int,
    x: float,
    y: float,
    reason: str,
    db: Session,
) -> dict:
    """의식 불명 감지 알림 생성

    Args:
        reason: "timeout" | "fall" | "heartrate" | "admin"
    """
    alert = Alert(
        alert_type=AlertType.UNCONSCIOUS,
        level=AlertLevel.CRITICAL,
        floor_id=floor_id,
        x=x,
        y=y,
        message=f"의식불명 감지 (원인: {reason}), user_id={user_id}",
        source_user_id=user_id,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)

    return {
        "alert_id": alert.id,
        "type": alert.alert_type.value,
        "user_id": user_id,
        "floor_id": floor_id,
        "x": x,
        "y": y,
        "reason": reason,
    }
