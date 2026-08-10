from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.models.database import get_db

router = APIRouter(prefix="/api/scoring", tags=["scoring"])


# --- Schemas ---

class ScoringRequest(BaseModel):
    facility_id: int
    region_id: int


class ScoringResponse(BaseModel):
    overall_score: float
    labor_score: float
    logistics_score: float
    infra_score: float
    cost_score: float
    risk_level: str
    summary: str


# --- Endpoints ---

@router.post("/evaluate", response_model=ScoringResponse)
def evaluate_feasibility(request: ScoringRequest, db: Session = Depends(get_db)):
    """특정 시설 × 지역 조합의 타당성 평가 실행"""
    # TODO: 구현
    pass


@router.get("/reports")
def list_reports(facility_id: Optional[int] = None, db: Session = Depends(get_db)):
    """타당성 평가 보고서 목록"""
    # TODO: 구현
    pass


@router.get("/reports/{report_id}")
def get_report(report_id: int, db: Session = Depends(get_db)):
    """보고서 상세 조회"""
    # TODO: 구현
    pass


@router.get("/compare")
def compare_regions(facility_id: int, region_ids: str, db: Session = Depends(get_db)):
    """복수 지역 비교 (region_ids: comma-separated)"""
    # TODO: 구현
    pass
