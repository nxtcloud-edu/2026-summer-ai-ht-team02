from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.models.database import get_db

router = APIRouter(prefix="/api/regional", tags=["regional"])


# --- Schemas ---

class RegionCreate(BaseModel):
    name: str
    province: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class LaborPoolCreate(BaseModel):
    region_id: int
    skill_category: str
    total_workers: int = 0
    available_workers: int = 0
    avg_wage: Optional[int] = None
    competition_demand: int = 0
    data_year: Optional[int] = None


class IndustrialSiteCreate(BaseModel):
    region_id: int
    name: str
    site_type: Optional[str] = None
    total_area_m2: Optional[float] = None
    available_area_m2: Optional[float] = None
    price_per_m2: Optional[float] = None
    occupancy_rate: Optional[float] = None


# --- Region ---

@router.get("/regions")
def list_regions(db: Session = Depends(get_db)):
    """지역 목록 조회"""
    # TODO: 구현
    pass


@router.post("/regions")
def create_region(data: RegionCreate, db: Session = Depends(get_db)):
    """지역 등록"""
    # TODO: 구현
    pass


@router.get("/regions/{region_id}")
def get_region_detail(region_id: int, db: Session = Depends(get_db)):
    """지역 상세 (인력풀, 교육기관, 산단, 인프라 포함)"""
    # TODO: 구현
    pass


# --- Labor Pool ---

@router.get("/labor-pools")
def list_labor_pools(region_id: Optional[int] = None, skill_category: Optional[str] = None, db: Session = Depends(get_db)):
    """인력풀 조회"""
    # TODO: 구현
    pass


@router.post("/labor-pools")
def create_labor_pool(data: LaborPoolCreate, db: Session = Depends(get_db)):
    """인력풀 등록"""
    # TODO: 구현
    pass


# --- Industrial Site ---

@router.get("/industrial-sites")
def list_industrial_sites(region_id: Optional[int] = None, db: Session = Depends(get_db)):
    """산업단지 목록"""
    # TODO: 구현
    pass


@router.post("/industrial-sites")
def create_industrial_site(data: IndustrialSiteCreate, db: Session = Depends(get_db)):
    """산업단지 등록"""
    # TODO: 구현
    pass


# --- Infrastructure ---

@router.get("/infrastructures")
def list_infrastructures(region_id: Optional[int] = None, infra_type: Optional[str] = None, db: Session = Depends(get_db)):
    """인프라 목록"""
    # TODO: 구현
    pass
