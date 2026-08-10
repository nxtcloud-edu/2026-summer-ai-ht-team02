from sqlalchemy.orm import Session
from typing import List

from app.services.ontology import get_total_headcount
from app.services.regional import match_labor_supply, get_region_intelligence


def calculate_feasibility_score(facility_id: int, region_id: int, db: Session) -> dict:
    """타당성 종합 점수 계산"""
    # 1. 인력 점수
    labor_score = _calculate_labor_score(facility_id, region_id, db)

    # 2. 물류 점수
    logistics_score = _calculate_logistics_score(facility_id, region_id, db)

    # 3. 인프라 점수
    infra_score = _calculate_infra_score(region_id, db)

    # 4. 비용 점수
    cost_score = _calculate_cost_score(region_id, db)

    # 종합 (가중 평균)
    weights = {"labor": 0.35, "logistics": 0.25, "infra": 0.20, "cost": 0.20}
    overall = (
        labor_score * weights["labor"]
        + logistics_score * weights["logistics"]
        + infra_score * weights["infra"]
        + cost_score * weights["cost"]
    )

    # 리스크 레벨
    if overall >= 70:
        risk_level = "low"
    elif overall >= 40:
        risk_level = "medium"
    else:
        risk_level = "high"

    return {
        "overall_score": round(overall, 1),
        "labor_score": round(labor_score, 1),
        "logistics_score": round(logistics_score, 1),
        "infra_score": round(infra_score, 1),
        "cost_score": round(cost_score, 1),
        "risk_level": risk_level,
    }


def _calculate_labor_score(facility_id: int, region_id: int, db: Session) -> float:
    """인력 확보 가능성 점수 (0-100)"""
    headcount = get_total_headcount(facility_id, db)
    if not headcount:
        return 50.0  # 기본값

    total_required = 0
    total_feasible = 0

    for category, info in headcount.items():
        result = match_labor_supply(region_id, category, info["headcount"], db)
        total_required += result["required"]
        total_feasible += min(result["effective_supply"], result["required"])

    if total_required == 0:
        return 50.0

    return (total_feasible / total_required) * 100


def _calculate_logistics_score(facility_id: int, region_id: int, db: Session) -> float:
    """물류 접근성 점수 (0-100)"""
    # TODO: 공급망 요구조건 vs 지역 교통 인프라 비교
    return 60.0  # 임시 기본값


def _calculate_infra_score(region_id: int, db: Session) -> float:
    """인프라 충족도 점수 (0-100)"""
    intelligence = get_region_intelligence(region_id, db)
    infra = intelligence.get("infrastructure", [])

    if not infra:
        return 30.0

    # 핵심 인프라 유형별 가용 여부
    required_types = {"highway", "power", "water"}
    available_types = {i["type"] for i in infra}
    coverage = len(required_types & available_types) / len(required_types)

    return coverage * 100


def _calculate_cost_score(region_id: int, db: Session) -> float:
    """비용 경쟁력 점수 (0-100)"""
    intelligence = get_region_intelligence(region_id, db)
    sites = intelligence.get("industrial_sites", [])

    if not sites:
        return 50.0

    # 분양가 기준 (낮을수록 높은 점수)
    avg_price = sum(s["price_per_m2"] or 0 for s in sites) / len(sites)

    # 기준: 50만원/m2 이하면 만점, 200만원 이상이면 0점
    if avg_price <= 500000:
        return 100.0
    elif avg_price >= 2000000:
        return 0.0
    else:
        return (1 - (avg_price - 500000) / 1500000) * 100
