from sqlalchemy.orm import Session
from typing import Optional

from app.models.regional import Region, LaborPool, Education, IndustrialSite, Infrastructure


def get_region_intelligence(region_id: int, db: Session) -> dict:
    """지역 종합 정보 조회"""
    region = db.query(Region).filter(Region.id == region_id).first()
    if not region:
        return {}

    labor_pools = db.query(LaborPool).filter(LaborPool.region_id == region_id).all()
    educations = db.query(Education).filter(Education.region_id == region_id).all()
    sites = db.query(IndustrialSite).filter(IndustrialSite.region_id == region_id).all()
    infra = db.query(Infrastructure).filter(Infrastructure.region_id == region_id).all()

    return {
        "region": {
            "id": region.id,
            "name": region.name,
            "province": region.province,
            "city": region.city,
        },
        "labor": [
            {
                "skill_category": lp.skill_category,
                "total_workers": lp.total_workers,
                "available_workers": lp.available_workers,
                "avg_wage": lp.avg_wage,
                "competition_demand": lp.competition_demand,
            }
            for lp in labor_pools
        ],
        "education": [
            {
                "institution": ed.institution_name,
                "type": ed.institution_type,
                "department": ed.department,
                "annual_graduates": ed.annual_graduates,
            }
            for ed in educations
        ],
        "industrial_sites": [
            {
                "name": s.name,
                "type": s.site_type,
                "available_area_m2": s.available_area_m2,
                "price_per_m2": s.price_per_m2,
                "occupancy_rate": s.occupancy_rate,
            }
            for s in sites
        ],
        "infrastructure": [
            {
                "type": inf.infra_type,
                "name": inf.name,
                "distance_km": inf.distance_km,
            }
            for inf in infra
        ],
    }


def match_labor_supply(region_id: int, skill_category: str, required_headcount: int, db: Session) -> dict:
    """인력 매칭: 지역의 공급 vs 기업의 수요"""
    labor = (
        db.query(LaborPool)
        .filter(LaborPool.region_id == region_id, LaborPool.skill_category == skill_category)
        .first()
    )

    if not labor:
        return {
            "skill_category": skill_category,
            "required": required_headcount,
            "available": 0,
            "competition_demand": 0,
            "effective_supply": 0,
            "shortage": required_headcount,
            "feasible": False,
        }

    effective_supply = max(0, labor.available_workers - labor.competition_demand)
    shortage = max(0, required_headcount - effective_supply)

    return {
        "skill_category": skill_category,
        "required": required_headcount,
        "available": labor.available_workers,
        "competition_demand": labor.competition_demand,
        "effective_supply": effective_supply,
        "shortage": shortage,
        "feasible": shortage == 0,
    }
