from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.models.database import get_db

router = APIRouter(prefix="/api/ontology", tags=["ontology"])


# --- Schemas ---

class FacilityCreate(BaseModel):
    name: str
    location: Optional[str] = None
    facility_type: Optional[str] = None


class ProcessCreate(BaseModel):
    facility_id: int
    name: str
    process_type: Optional[str] = None
    description: Optional[str] = None


class JobRequirementCreate(BaseModel):
    process_id: int
    job_title: str
    skill_category: Optional[str] = None
    headcount: int = 1
    experience_years: int = 0
    description: Optional[str] = None


class SupplyChainCreate(BaseModel):
    facility_id: int
    target_name: str
    target_location: Optional[str] = None
    max_delivery_minutes: Optional[int] = None
    transport_mode: Optional[str] = None
    priority: str = "normal"


# --- Facility ---

@router.get("/facilities")
def list_facilities(db: Session = Depends(get_db)):
    """시설 목록 조회"""
    # TODO: 구현
    pass


@router.post("/facilities")
def create_facility(data: FacilityCreate, db: Session = Depends(get_db)):
    """시설 등록"""
    # TODO: 구현
    pass


@router.get("/facilities/{facility_id}")
def get_facility(facility_id: int, db: Session = Depends(get_db)):
    """시설 상세 조회 (연결된 공정·직무 포함)"""
    # TODO: 구현
    pass


# --- Process ---

@router.get("/processes")
def list_processes(facility_id: Optional[int] = None, db: Session = Depends(get_db)):
    """공정 목록 조회"""
    # TODO: 구현
    pass


@router.post("/processes")
def create_process(data: ProcessCreate, db: Session = Depends(get_db)):
    """공정 등록"""
    # TODO: 구현
    pass


# --- Job Requirement ---

@router.get("/jobs")
def list_job_requirements(process_id: Optional[int] = None, db: Session = Depends(get_db)):
    """직무 요구사항 목록"""
    # TODO: 구현
    pass


@router.post("/jobs")
def create_job_requirement(data: JobRequirementCreate, db: Session = Depends(get_db)):
    """직무 요구사항 등록"""
    # TODO: 구현
    pass


# --- Supply Chain ---

@router.get("/supply-chains")
def list_supply_chains(facility_id: Optional[int] = None, db: Session = Depends(get_db)):
    """공급망 목록 조회"""
    # TODO: 구현
    pass


@router.post("/supply-chains")
def create_supply_chain(data: SupplyChainCreate, db: Session = Depends(get_db)):
    """공급망 등록"""
    # TODO: 구현
    pass


# --- Graph ---

@router.get("/graph/{facility_id}")
def get_ontology_graph(facility_id: int, db: Session = Depends(get_db)):
    """시설 기준 온톨로지 그래프 (노드 + 엣지)"""
    # TODO: 구현
    pass
