import networkx as nx
from sqlalchemy.orm import Session

from app.models.ontology import (
    Facility,
    Process,
    JobRequirement,
    SupplyChain,
    OntologyRelation,
)


def build_ontology_graph(facility_id: int, db: Session) -> dict:
    """시설 기준 온톨로지 그래프 구축 (NetworkX)"""
    G = nx.DiGraph()

    facility = db.query(Facility).filter(Facility.id == facility_id).first()
    if not facility:
        return {"nodes": [], "edges": []}

    # 시설 노드
    G.add_node(f"facility_{facility.id}", label=facility.name, type="facility")

    # 공정 노드
    processes = db.query(Process).filter(Process.facility_id == facility_id).all()
    for proc in processes:
        G.add_node(f"process_{proc.id}", label=proc.name, type="process")
        G.add_edge(f"facility_{facility.id}", f"process_{proc.id}", relation="has_process")

        # 직무 노드
        jobs = db.query(JobRequirement).filter(JobRequirement.process_id == proc.id).all()
        for job in jobs:
            G.add_node(f"job_{job.id}", label=job.job_title, type="job")
            G.add_edge(f"process_{proc.id}", f"job_{job.id}", relation="requires")

    # 공급망 노드
    chains = db.query(SupplyChain).filter(SupplyChain.facility_id == facility_id).all()
    for chain in chains:
        G.add_node(f"supply_{chain.id}", label=chain.target_name, type="supply")
        G.add_edge(f"facility_{facility.id}", f"supply_{chain.id}", relation="supplies_to")

    # 그래프 → dict 변환
    nodes = [{"id": n, **G.nodes[n]} for n in G.nodes]
    edges = [{"source": u, "target": v, **G.edges[u, v]} for u, v in G.edges]

    return {"nodes": nodes, "edges": edges}


def get_total_headcount(facility_id: int, db: Session) -> dict:
    """시설의 전체 인력 요구사항 집계"""
    processes = db.query(Process).filter(Process.facility_id == facility_id).all()
    skill_summary = {}

    for proc in processes:
        jobs = db.query(JobRequirement).filter(JobRequirement.process_id == proc.id).all()
        for job in jobs:
            category = job.skill_category or "기타"
            if category not in skill_summary:
                skill_summary[category] = {"headcount": 0, "jobs": []}
            skill_summary[category]["headcount"] += job.headcount
            skill_summary[category]["jobs"].append(job.job_title)

    return skill_summary
