from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON
from sqlalchemy.sql import func

from app.models.database import Base


class Region(Base):
    """후보 지역"""
    __tablename__ = "regions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    province = Column(String)  # 시도
    city = Column(String)      # 시군구
    latitude = Column(Float)
    longitude = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class LaborPool(Base):
    """지역 인력풀"""
    __tablename__ = "labor_pools"

    id = Column(Integer, primary_key=True, index=True)
    region_id = Column(Integer, nullable=False)
    skill_category = Column(String, nullable=False)  # 금속가공, 전기전자 등
    total_workers = Column(Integer, default=0)
    available_workers = Column(Integer, default=0)
    avg_wage = Column(Integer)  # 월 평균 임금 (만원)
    competition_demand = Column(Integer, default=0)  # 경쟁 수요
    data_year = Column(Integer)


class Education(Base):
    """교육기관 (대학, 폴리텍 등)"""
    __tablename__ = "educations"

    id = Column(Integer, primary_key=True, index=True)
    region_id = Column(Integer, nullable=False)
    institution_name = Column(String, nullable=False)
    institution_type = Column(String)  # 대학교, 폴리텍, 직업훈련원
    department = Column(String)
    annual_graduates = Column(Integer, default=0)
    skill_category = Column(String)


class IndustrialSite(Base):
    """산업단지/부지"""
    __tablename__ = "industrial_sites"

    id = Column(Integer, primary_key=True, index=True)
    region_id = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    site_type = Column(String)  # 국가산단, 일반산단, 도시첨단 등
    total_area_m2 = Column(Float)
    available_area_m2 = Column(Float)
    price_per_m2 = Column(Float)  # 분양가
    occupancy_rate = Column(Float)  # 입주율
    utilities = Column(JSON)  # {"power": true, "water": true, "gas": true}


class Infrastructure(Base):
    """인프라 (교통, 전력, 용수 등)"""
    __tablename__ = "infrastructures"

    id = Column(Integer, primary_key=True, index=True)
    region_id = Column(Integer, nullable=False)
    infra_type = Column(String, nullable=False)  # highway, port, power, water, housing
    name = Column(String)
    capacity = Column(String)
    distance_km = Column(Float)  # 후보지까지 거리
    description = Column(Text)
