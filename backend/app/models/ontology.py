from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.database import Base


class Facility(Base):
    """시설 (공장, 사업장)"""
    __tablename__ = "facilities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    location = Column(String)
    facility_type = Column(String)  # 공장, 물류센터, R&D 등
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    processes = relationship("Process", back_populates="facility")


class Process(Base):
    """공정"""
    __tablename__ = "processes"

    id = Column(Integer, primary_key=True, index=True)
    facility_id = Column(Integer, ForeignKey("facilities.id"))
    name = Column(String, nullable=False)
    process_type = Column(String)  # CNC가공, 조립, 도장 등
    description = Column(Text)

    facility = relationship("Facility", back_populates="processes")
    job_requirements = relationship("JobRequirement", back_populates="process")


class JobRequirement(Base):
    """직무 요구사항"""
    __tablename__ = "job_requirements"

    id = Column(Integer, primary_key=True, index=True)
    process_id = Column(Integer, ForeignKey("processes.id"))
    job_title = Column(String, nullable=False)
    skill_category = Column(String)  # 금속가공, 전기전자, SW 등
    headcount = Column(Integer, default=1)
    experience_years = Column(Integer, default=0)
    description = Column(Text)

    process = relationship("Process", back_populates="job_requirements")


class SupplyChain(Base):
    """공급망 요구조건"""
    __tablename__ = "supply_chains"

    id = Column(Integer, primary_key=True, index=True)
    facility_id = Column(Integer, ForeignKey("facilities.id"))
    target_name = Column(String, nullable=False)  # 주요 고객/공급처
    target_location = Column(String)
    max_delivery_minutes = Column(Integer)  # 최대 납품 시간(분)
    transport_mode = Column(String)  # 도로, 철도, 항만 등
    priority = Column(String, default="normal")  # high, normal, low


class OntologyRelation(Base):
    """온톨로지 관계 (그래프 엣지)"""
    __tablename__ = "ontology_relations"

    id = Column(Integer, primary_key=True, index=True)
    source_type = Column(String, nullable=False)  # facility, process, job, supply
    source_id = Column(Integer, nullable=False)
    relation = Column(String, nullable=False)  # requires, produces, connects_to 등
    target_type = Column(String, nullable=False)
    target_id = Column(Integer, nullable=False)
    metadata = Column(JSON)
