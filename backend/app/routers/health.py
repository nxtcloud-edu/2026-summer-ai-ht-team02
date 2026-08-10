from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from app.models.database import get_db
from app.models.health_data import HealthRecord, HealthBaseline
from app.services.health_monitor import record_and_check, get_anomaly_users
from app.websocket_manager import manager

router = APIRouter(prefix="/api/health", tags=["health"])


# --- Schemas ---

class HealthRecordRequest(BaseModel):
    user_id: int
    heart_rate: int
    temperature: float


class HealthRecordResponse(BaseModel):
    recorded: bool
    anomaly_detected: bool
    anomaly_type: Optional[str] = None
    value: Optional[float] = None
    baseline_avg: Optional[float] = None
    z_score: Optional[float] = None
    consecutive_count: Optional[int] = None
    action: Optional[str] = None
    message: Optional[str] = None


class BaselineResponse(BaseModel):
    user_id: int
    avg_hr: Optional[float] = None
    std_hr: Optional[float] = None
    avg_temp: Optional[float] = None
    std_temp: Optional[float] = None
    sample_count: int
    anomaly_count: int
    updated_at: Optional[str] = None


class HealthHistoryItem(BaseModel):
    id: int
    heart_rate: Optional[int] = None
    temperature: Optional[float] = None
    timestamp: Optional[str] = None


# --- Endpoints ---

@router.post("/record", response_model=HealthRecordResponse)
async def post_health_record(data: HealthRecordRequest, db: Session = Depends(get_db)):
    """건강 데이터 기록 + Z-score 이상 즉시 체크"""
    result = record_and_check(
        user_id=data.user_id,
        heart_rate=data.heart_rate,
        temperature=data.temperature,
        db=db,
    )

    # 이상 감지 시 WebSocket push (관리자/구조대)
    if result.get("anomaly_detected"):
        ws_msg = {
            "type": "health_anomaly",
            "user_id": data.user_id,
            "anomaly_type": result.get("anomaly_type"),
            "value": result.get("value"),
            "baseline_avg": result.get("baseline_avg"),
            "z_score": result.get("z_score"),
            "consecutive_count": result.get("consecutive_count"),
            "action": result.get("action"),
        }
        await manager.broadcast_to_admins(ws_msg)
        await manager.broadcast_to_rescuers(ws_msg)

    return HealthRecordResponse(**result)


@router.get("/baseline/{user_id}", response_model=BaselineResponse)
def get_baseline(user_id: int, db: Session = Depends(get_db)):
    """개인 건강 baseline 조회"""
    baseline = db.query(HealthBaseline).filter(HealthBaseline.user_id == user_id).first()
    if not baseline:
        raise HTTPException(status_code=404, detail="해당 유저의 baseline이 없습니다.")

    return BaselineResponse(
        user_id=baseline.user_id,
        avg_hr=round(baseline.avg_hr, 1) if baseline.avg_hr else None,
        std_hr=round(baseline.std_hr, 2) if baseline.std_hr else None,
        avg_temp=round(baseline.avg_temp, 2) if baseline.avg_temp else None,
        std_temp=round(baseline.std_temp, 3) if baseline.std_temp else None,
        sample_count=baseline.sample_count,
        anomaly_count=baseline.anomaly_count,
        updated_at=str(baseline.updated_at) if baseline.updated_at else None,
    )


@router.get("/anomalies")
def get_anomalies(db: Session = Depends(get_db)):
    """현재 이상 감지된 근로자 목록"""
    return get_anomaly_users(db)


@router.get("/history/{user_id}", response_model=List[HealthHistoryItem])
def get_health_history(user_id: int, limit: int = 100, db: Session = Depends(get_db)):
    """건강 데이터 이력 (최신순)"""
    records = (
        db.query(HealthRecord)
        .filter(HealthRecord.user_id == user_id)
        .order_by(HealthRecord.timestamp.desc())
        .limit(limit)
        .all()
    )
    return [
        HealthHistoryItem(
            id=r.id,
            heart_rate=r.heart_rate,
            temperature=r.temperature,
            timestamp=str(r.timestamp) if r.timestamp else None,
        )
        for r in records
    ]
