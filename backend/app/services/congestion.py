"""
밀집도(혼잡도) 계산 서비스

구역(zone) 단위로 현재 인원 밀집도를 계산하고,
임계치 초과 시 경고를 생성한다.

Zone 정의: FloorNode 중 label이 있는 path/room 노드를 구역 중심점으로 사용.
각 구역은 ZONE_RADIUS 내의 작업자를 카운트한다.
"""

from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.building import FloorNode, Floor
from app.models.location import EvacuationStatus


# 구역 반경 (mm 단위 — 도면 좌표 기준, 약 3m)
ZONE_RADIUS = 3000.0

# 밀집도 임계치 (구역 내 인원 수)
CONGESTION_THRESHOLD_WARNING = 4   # 주의
CONGESTION_THRESHOLD_DANGER = 7    # 위험

# zone으로 인식할 node_type 목록
ZONE_NODE_TYPES = ("path", "room")


def _distance(x1: float, y1: float, x2: float, y2: float) -> float:
    return ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5


def get_floor_zones(floor_id: int, db: Session) -> List[dict]:
    """해당 층의 구역(zone) 목록 반환 (label이 있는 노드만)"""
    nodes = (
        db.query(FloorNode)
        .filter(
            FloorNode.floor_id == floor_id,
            FloorNode.node_type.in_(ZONE_NODE_TYPES),
            FloorNode.label.isnot(None),
        )
        .all()
    )
    return [
        {
            "id": n.id,
            "floor_id": n.floor_id,
            "x": n.x,
            "y": n.y,
            "label": n.label,
            "node_type": n.node_type,
        }
        for n in nodes
    ]


def get_floor_density(floor_id: int, db: Session) -> Dict:
    """
    층별 구역 밀집도 계산.

    반환: {
        "floor_id": int,
        "total_workers": int,
        "zones": [
            {
                "zone_id": int,
                "label": str,
                "x": float,
                "y": float,
                "worker_count": int,
                "level": "normal" | "warning" | "danger",
                "workers": [user_id, ...]
            }
        ]
    }
    """
    # 구역 노드 조회
    zones = get_floor_zones(floor_id, db)

    # 현재 해당 층 재실 작업자 위치
    workers = (
        db.query(EvacuationStatus)
        .filter(
            EvacuationStatus.last_floor_id == floor_id,
            EvacuationStatus.status.in_(["in_building", "evacuating"]),
        )
        .all()
    )

    total_workers = len(workers)

    zone_results = []
    for zone in zones:
        # 구역 내 작업자 카운트
        nearby_workers = []
        for w in workers:
            if w.last_x is not None and w.last_y is not None:
                dist = _distance(zone["x"], zone["y"], w.last_x, w.last_y)
                if dist <= ZONE_RADIUS:
                    nearby_workers.append(w.user_id)

        count = len(nearby_workers)

        # 밀집도 레벨 판정
        if count >= CONGESTION_THRESHOLD_DANGER:
            level = "danger"
        elif count >= CONGESTION_THRESHOLD_WARNING:
            level = "warning"
        else:
            level = "normal"

        zone_results.append({
            "zone_id": zone["id"],
            "label": zone["label"],
            "x": zone["x"],
            "y": zone["y"],
            "worker_count": count,
            "level": level,
            "workers": nearby_workers,
        })

    return {
        "floor_id": floor_id,
        "total_workers": total_workers,
        "zones": zone_results,
    }


def get_all_floors_density(db: Session) -> List[Dict]:
    """전체 층 밀집도 요약"""
    floors = db.query(Floor).order_by(Floor.floor_number).all()
    results = []
    for floor in floors:
        density = get_floor_density(floor.id, db)
        # 해당 층의 최대 밀집 레벨 계산
        max_level = "normal"
        for z in density["zones"]:
            if z["level"] == "danger":
                max_level = "danger"
                break
            elif z["level"] == "warning":
                max_level = "warning"

        results.append({
            "floor_id": floor.id,
            "floor_name": floor.name,
            "floor_number": floor.floor_number,
            "total_workers": density["total_workers"],
            "max_level": max_level,
            "zones": density["zones"],
        })
    return results


def get_congestion_alerts(db: Session) -> List[Dict]:
    """현재 밀집 경고가 발생한 구역 목록"""
    all_density = get_all_floors_density(db)
    alerts = []
    for floor_data in all_density:
        for zone in floor_data["zones"]:
            if zone["level"] in ("warning", "danger"):
                alerts.append({
                    "floor_id": floor_data["floor_id"],
                    "floor_name": floor_data["floor_name"],
                    "zone_id": zone["zone_id"],
                    "zone_label": zone["label"],
                    "worker_count": zone["worker_count"],
                    "level": zone["level"],
                    "x": zone["x"],
                    "y": zone["y"],
                    "threshold": CONGESTION_THRESHOLD_DANGER if zone["level"] == "danger" else CONGESTION_THRESHOLD_WARNING,
                    "timestamp": datetime.utcnow().isoformat(),
                })
    return alerts
