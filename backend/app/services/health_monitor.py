import math
from datetime import datetime
from typing import Optional, List

from sqlalchemy.orm import Session

from app.models.health_data import HealthRecord, HealthBaseline
from app.models.location import EvacuationStatus
from app.config import settings


def record_and_check(user_id: int, heart_rate: int, temperature: float, db: Session) -> dict:
    """건강 데이터 저장 + Z-score 이상 판정"""
    # 1. HealthRecord 저장
    record = HealthRecord(
        user_id=user_id,
        heart_rate=heart_rate,
        temperature=temperature,
    )
    db.add(record)

    # 2. Baseline 조회 또는 생성
    baseline = db.query(HealthBaseline).filter(HealthBaseline.user_id == user_id).first()
    if not baseline:
        baseline = HealthBaseline(
            user_id=user_id,
            avg_hr=float(heart_rate),
            std_hr=0.0,
            avg_temp=temperature,
            std_temp=0.0,
            sample_count=1,
            anomaly_count=0,
        )
        db.add(baseline)
        db.commit()
        db.refresh(baseline)
        return {
            "recorded": True,
            "anomaly_detected": False,
            "message": "baseline 초기화 (첫 데이터)",
        }

    # 3. 이상 판정
    anomaly = check_anomaly(baseline, heart_rate, temperature)

    # 4. anomaly_count 관리
    if anomaly:
        baseline.anomaly_count += 1
    else:
        baseline.anomaly_count = 0

    # 5. 상태 전환 처리
    action = None
    if anomaly and anomaly.get("action") == "rescue_needed":
        action = "rescue_needed"
        _update_worker_state(user_id, "unconscious", db)
    elif baseline.anomaly_count >= settings.HEALTH_ANOMALY_CONSECUTIVE:
        action = "at_risk"
        _update_worker_state(user_id, "unconscious", db)

    # 6. Baseline EMA 업데이트
    update_baseline_ema(baseline, heart_rate, temperature)

    db.commit()

    result = {
        "recorded": True,
        "anomaly_detected": anomaly is not None,
        "consecutive_count": baseline.anomaly_count,
    }
    if anomaly:
        result.update(anomaly)
    if action:
        result["action"] = action

    return result


def update_baseline_ema(baseline: HealthBaseline, heart_rate: int, temperature: float):
    """EMA(지수이동평균)로 baseline 업데이트"""
    alpha = settings.HEALTH_EMA_ALPHA

    # 심박 EMA
    old_avg_hr = baseline.avg_hr or float(heart_rate)
    new_avg_hr = (1 - alpha) * old_avg_hr + alpha * float(heart_rate)
    old_std_hr = baseline.std_hr or 0.0
    new_std_hr = math.sqrt(
        (1 - alpha) * (old_std_hr ** 2) + alpha * ((float(heart_rate) - new_avg_hr) ** 2)
    )

    # 체온 EMA
    old_avg_temp = baseline.avg_temp or temperature
    new_avg_temp = (1 - alpha) * old_avg_temp + alpha * temperature
    old_std_temp = baseline.std_temp or 0.0
    new_std_temp = math.sqrt(
        (1 - alpha) * (old_std_temp ** 2) + alpha * ((temperature - new_avg_temp) ** 2)
    )

    baseline.avg_hr = new_avg_hr
    baseline.std_hr = new_std_hr
    baseline.avg_temp = new_avg_temp
    baseline.std_temp = new_std_temp
    baseline.sample_count += 1
    baseline.updated_at = datetime.utcnow()


def check_anomaly(baseline: HealthBaseline, heart_rate: int, temperature: float) -> Optional[dict]:
    """Z-score 기반 이상 판정"""
    # 심박 절대 위험값 (즉시 판정)
    if heart_rate < settings.HEALTH_HR_ABSOLUTE_MIN:
        return {
            "anomaly_type": "heart_rate_critical",
            "value": heart_rate,
            "message": f"심박 {heart_rate}bpm — 즉시 위험",
            "action": "rescue_needed",
        }

    # Baseline 미성숙 시 판정 생략
    if baseline.sample_count < settings.HEALTH_BASELINE_MIN_SAMPLES:
        return None

    # 심박 Z-score
    if baseline.std_hr and baseline.std_hr > 0:
        z_hr = (float(heart_rate) - baseline.avg_hr) / baseline.std_hr
        if abs(z_hr) > settings.HEALTH_HR_ZSCORE_THRESHOLD:
            return {
                "anomaly_type": "heart_rate",
                "value": heart_rate,
                "baseline_avg": round(baseline.avg_hr, 1),
                "z_score": round(z_hr, 2),
                "message": f"심박 이상 (z={z_hr:.1f})",
            }

    # 체온 절대값
    if temperature >= settings.HEALTH_TEMP_ABSOLUTE_MAX:
        return {
            "anomaly_type": "temperature",
            "value": temperature,
            "baseline_avg": round(baseline.avg_temp, 1) if baseline.avg_temp else None,
            "message": f"체온 {temperature}°C — 고열",
        }

    # 체온 Z-score
    if baseline.std_temp and baseline.std_temp > 0:
        z_temp = (temperature - baseline.avg_temp) / baseline.std_temp
        if abs(z_temp) > settings.HEALTH_TEMP_ZSCORE_THRESHOLD:
            return {
                "anomaly_type": "temperature",
                "value": temperature,
                "baseline_avg": round(baseline.avg_temp, 2),
                "z_score": round(z_temp, 2),
                "message": f"체온 이상 (z={z_temp:.1f})",
            }

    return None


def get_anomaly_users(db: Session) -> List[dict]:
    """현재 이상 감지된 근로자 목록 (anomaly_count >= 1)"""
    baselines = (
        db.query(HealthBaseline)
        .filter(HealthBaseline.anomaly_count >= 1)
        .all()
    )

    results = []
    for b in baselines:
        # 최근 기록 1건
        latest = (
            db.query(HealthRecord)
            .filter(HealthRecord.user_id == b.user_id)
            .order_by(HealthRecord.timestamp.desc())
            .first()
        )
        results.append({
            "user_id": b.user_id,
            "anomaly_count": b.anomaly_count,
            "avg_hr": round(b.avg_hr, 1) if b.avg_hr else None,
            "avg_temp": round(b.avg_temp, 2) if b.avg_temp else None,
            "latest_hr": latest.heart_rate if latest else None,
            "latest_temp": latest.temperature if latest else None,
            "updated_at": str(b.updated_at) if b.updated_at else None,
        })

    return results


def _update_worker_state(user_id: int, status: str, db: Session):
    """EvacuationStatus의 상태를 갱신 (이상 감지 시)"""
    evac = db.query(EvacuationStatus).filter(EvacuationStatus.user_id == user_id).first()
    if evac:
        evac.status = status
        evac.is_moving = False
        evac.updated_at = datetime.utcnow()
