from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, ForeignKey
from sqlalchemy.sql import func

from app.models.database import Base


class FeasibilityReport(Base):
    """타당성 평가 보고서"""
    __tablename__ = "feasibility_reports"

    id = Column(Integer, primary_key=True, index=True)
    region_id = Column(Integer, nullable=False)
    facility_id = Column(Integer, nullable=False)
    overall_score = Column(Float)  # 종합 점수 (0-100)
    labor_score = Column(Float)    # 인력 점수
    logistics_score = Column(Float)  # 물류 점수
    infra_score = Column(Float)    # 인프라 점수
    cost_score = Column(Float)     # 비용 점수
    risk_level = Column(String)    # low, medium, high
    summary = Column(Text)         # LLM 생성 요약
    details = Column(JSON)         # 상세 분석 데이터
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(Integer)


class ScoringCriteria(Base):
    """채점 기준"""
    __tablename__ = "scoring_criteria"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String, nullable=False)  # labor, logistics, infra, cost
    name = Column(String, nullable=False)
    weight = Column(Float, default=1.0)
    description = Column(Text)


class PlanningResult(Base):
    """기획안 결과"""
    __tablename__ = "planning_results"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("feasibility_reports.id"))
    title = Column(String, nullable=False)
    shortlist = Column(JSON)         # 후보지 목록 + 점수
    labor_analysis = Column(JSON)    # 채용 가능 인력 분석
    logistics_analysis = Column(JSON)  # 물류 분석
    risk_analysis = Column(JSON)     # 리스크 분석
    scenarios = Column(JSON)         # 이전 시나리오
    recommendation = Column(Text)    # 최종 권고안
    created_at = Column(DateTime(timezone=True), server_default=func.now())
