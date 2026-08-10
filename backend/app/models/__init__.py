from app.models.database import Base, engine, get_db
from app.models.user import User, UserRole
from app.models.ontology import (
    Facility,
    Process,
    JobRequirement,
    SupplyChain,
    OntologyRelation,
)
from app.models.regional import (
    Region,
    LaborPool,
    Education,
    IndustrialSite,
    Infrastructure,
)
from app.models.scoring import (
    FeasibilityReport,
    ScoringCriteria,
    PlanningResult,
)
