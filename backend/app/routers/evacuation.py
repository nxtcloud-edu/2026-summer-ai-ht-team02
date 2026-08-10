from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.models.database import get_db

router = APIRouter(prefix="/api/evacuation", tags=["evacuation"])


# --- Schemas ---

class RouteRequest(BaseModel):
    user_id: int
    floor_id: int
    x: float
    y: float


class EvacuationStatusUpdate(BaseModel):
    user_id: int
    status: str  # in_building, evacuating, evacuated, unconscious


# --- Endpoints ---

@router.post("/route")
def get_evacuation_route(data: RouteRequest, db: Session = Depends(get_db)):
    """현재 위치 기반 최적 탈출 경로 계산"""
    # TODO: 구현 — 화재 구역 회피 + A*/Dijkstra
    pass


@router.get("/status")
def get_all_evacuation_status(db: Session = Depends(get_db)):
    """전체 대피 현황 (관리자/구조대용)"""
    # TODO: 구현
    pass


@router.get("/status/{user_id}")
def get_user_evacuation_status(user_id: int, db: Session = Depends(get_db)):
    """특정 근로자 대피 상태"""
    # TODO: 구현
    pass


@router.put("/status")
def update_evacuation_status(data: EvacuationStatusUpdate, db: Session = Depends(get_db)):
    """대피 상태 갱신"""
    # TODO: 구현
    pass


@router.get("/unconscious")
def get_unconscious_workers(db: Session = Depends(get_db)):
    """의식 불명/미대피 근로자 목록 (구조대 뷰)"""
    # TODO: 구현
    pass


@router.get("/rescuer-route/{target_user_id}")
def get_rescuer_route(target_user_id: int, floor_id: int, x: float, y: float, db: Session = Depends(get_db)):
    """구조대원 → 미대피자까지 최적 진입 경로"""
    # TODO: 구현
    pass
