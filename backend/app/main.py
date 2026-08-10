from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.models.database import Base, engine
from app.routers import (
    auth_router,
    ontology_router,
    regional_router,
    scoring_router,
    planning_router,
)

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Ontology-driven Site Planning Agent API",
    version="0.1.0",
    description="기업 온톨로지 기반 산업이전 사전 타당성 검증 AI",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router)
app.include_router(ontology_router)
app.include_router(regional_router)
app.include_router(scoring_router)
app.include_router(planning_router)


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "site-planning-agent"}
