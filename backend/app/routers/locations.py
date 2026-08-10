from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.models.database import get_db

router = APIRouter(prefix="/api/locations", tags=["locations"])


# --- Schemas ---

class LocationUpdate(BaseModel):
    user_id: int
    floor_id: int
    x: float
    y: float
    accuracy: Optional[float] = None
    heart_rate: Optional[int] = None


# --- Endpoints ---

@router.post("/update")
def update_location(data: LocationUpdate, db: Session = Depends(get_db)):
    """스마트워치에서 위치 갱신"""
    # TODO: 구현
    pass


@router.get("/current")
def get_all_current_locations(db: Session = Depends(get_db)):
    """전체 근로자 현재 위치 (관리자/구조대용)"""
    # TODO: 구현
    pass


@router.get("/current/{user_id}")
def get_user_location(user_id: int, db: Session = Depends(get_db)):
    """특정 근로자 현재 위치"""
    # TODO: 구현
    pass


@router.get("/floor/{floor_id}")
def get_floor_locations(floor_id: int, db: Session = Depends(get_db)):
    """특정 층 재실자 위치 목록"""
    # TODO: 구현
    pass


@router.get("/history/{user_id}")
def get_location_history(user_id: int, limit: int = 50, db: Session = Depends(get_db)):
    """위치 이력 (이동 경로 추적)"""
    # TODO: 구현
    pass
