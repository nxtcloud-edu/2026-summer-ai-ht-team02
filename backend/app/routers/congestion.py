"""
밀집도(혼잡도) API 라우터

- GET /api/congestion/floors      — 전체 층 밀집도 요약
- GET /api/congestion/floor/{id}  — 특정 층 구역별 밀집도
- GET /api/congestion/alerts      — 현재 밀집 경고 목록
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.services.congestion import (
    get_all_floors_density,
    get_floor_density,
    get_congestion_alerts,
)

router = APIRouter(prefix="/api/congestion", tags=["congestion"])


@router.get("/floors")
def all_floors_density(db: Session = Depends(get_db)):
    """전체 층 밀집도 요약 (층별 총 인원 + 구역별 밀집 레벨)"""
    return get_all_floors_density(db)


@router.get("/floor/{floor_id}")
def floor_density(floor_id: int, db: Session = Depends(get_db)):
    """특정 층의 구역별 밀집도 상세"""
    return get_floor_density(floor_id, db)


@router.get("/alerts")
def congestion_alerts(db: Session = Depends(get_db)):
    """현재 밀집 경고가 발생한 구역 목록"""
    return get_congestion_alerts(db)
