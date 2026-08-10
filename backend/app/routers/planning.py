from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from app.models.database import get_db

router = APIRouter(prefix="/api/planning", tags=["planning"])


# --- Schemas ---

class PlanningRequest(BaseModel):
    facility_id: int
    region_ids: List[int]  # 후보지 목록


class PlanningResponse(BaseModel):
    title: str
    shortlist: dict
    labor_analysis: dict
    logistics_analysis: dict
    risk_analysis: dict
    scenarios: dict
    recommendation: str


# --- Endpoints ---

@router.post("/generate")
def generate_plan(request: PlanningRequest, db: Session = Depends(get_db)):
    """사전 타당성 기획안 생성 (LLM 기반)"""
    # TODO: 구현
    pass


@router.get("/results")
def list_planning_results(facility_id: Optional[int] = None, db: Session = Depends(get_db)):
    """기획안 결과 목록"""
    # TODO: 구현
    pass


@router.get("/results/{result_id}")
def get_planning_result(result_id: int, db: Session = Depends(get_db)):
    """기획안 상세 조회"""
    # TODO: 구현
    pass


@router.post("/simulate-labor")
def simulate_labor(facility_id: int, region_id: int, db: Session = Depends(get_db)):
    """채용 가능성 시뮬레이션"""
    # TODO: 구현
    pass


@router.post("/analyze-risk")
def analyze_risk(facility_id: int, region_id: int, db: Session = Depends(get_db)):
    """리스크 분석"""
    # TODO: 구현
    pass
