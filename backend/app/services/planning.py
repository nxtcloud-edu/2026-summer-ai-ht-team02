from sqlalchemy.orm import Session
from typing import List

from app.services.scoring import calculate_feasibility_score
from app.services.ontology import get_total_headcount
from app.services.regional import get_region_intelligence, match_labor_supply


def generate_planning_report(facility_id: int, region_ids: List[int], db: Session) -> dict:
    """사전 타당성 기획안 생성"""

    # 1. 후보지 Shortlist & 적합도 비교
    shortlist = []
    for region_id in region_ids:
        score = calculate_feasibility_score(facility_id, region_id, db)
        intelligence = get_region_intelligence(region_id, db)
        shortlist.append({
            "region_id": region_id,
            "region_name": intelligence.get("region", {}).get("name", ""),
            **score,
        })

    shortlist.sort(key=lambda x: x["overall_score"], reverse=True)

    # 2. 채용 가능 인력 분석
    labor_analysis = _analyze_labor(facility_id, region_ids, db)

    # 3. 물류·인프라 분석
    logistics_analysis = _analyze_logistics(region_ids, db)

    # 4. 리스크 분석
    risk_analysis = _analyze_risks(shortlist, labor_analysis)

    # 5. 시나리오
    scenarios = _build_scenarios(shortlist)

    return {
        "shortlist": shortlist,
        "labor_analysis": labor_analysis,
        "logistics_analysis": logistics_analysis,
        "risk_analysis": risk_analysis,
        "scenarios": scenarios,
        "recommendation": _generate_recommendation(shortlist),
    }


def _analyze_labor(facility_id: int, region_ids: List[int], db: Session) -> dict:
    """후보지별 채용 가능 인력 분석"""
    headcount = get_total_headcount(facility_id, db)
    result = {}

    for region_id in region_ids:
        region_labor = {}
        for category, info in headcount.items():
            match = match_labor_supply(region_id, category, info["headcount"], db)
            region_labor[category] = match
        result[region_id] = region_labor

    return result


def _analyze_logistics(region_ids: List[int], db: Session) -> dict:
    """후보지별 물류 인프라 분석"""
    result = {}
    for region_id in region_ids:
        intelligence = get_region_intelligence(region_id, db)
        result[region_id] = {
            "infrastructure": intelligence.get("infrastructure", []),
            "industrial_sites": intelligence.get("industrial_sites", []),
        }
    return result


def _analyze_risks(shortlist: list, labor_analysis: dict) -> list:
    """리스크 요인 도출"""
    risks = []

    for item in shortlist:
        region_risks = []
        if item["risk_level"] == "high":
            region_risks.append("종합 위험도 높음")
        if item["labor_score"] < 50:
            region_risks.append("인력 확보 어려움 — 채용 미스매치 예상")
        if item["logistics_score"] < 50:
            region_risks.append("물류 접근성 부족 — 납기 지연 위험")
        if item["infra_score"] < 50:
            region_risks.append("인프라 부족 — 추가 투자 필요")

        risks.append({
            "region_id": item["region_id"],
            "region_name": item["region_name"],
            "risks": region_risks,
        })

    return risks


def _build_scenarios(shortlist: list) -> list:
    """이전 시나리오 구성"""
    scenarios = []
    for i, item in enumerate(shortlist[:3]):  # 상위 3개 후보지
        scenarios.append({
            "rank": i + 1,
            "region_name": item["region_name"],
            "score": item["overall_score"],
            "pros": [],  # TODO: LLM으로 구체적 장단점 생성
            "cons": [],
        })
    return scenarios


def _generate_recommendation(shortlist: list) -> str:
    """최종 권고안 생성 (향후 LLM 연동)"""
    if not shortlist:
        return "평가 가능한 후보지가 없습니다."

    best = shortlist[0]
    return (
        f"종합 분석 결과, {best['region_name']}이(가) "
        f"적합도 {best['overall_score']}점으로 1순위 후보지입니다. "
        f"리스크 수준: {best['risk_level']}"
    )
