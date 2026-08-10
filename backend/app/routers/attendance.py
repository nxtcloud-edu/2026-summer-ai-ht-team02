from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.models.database import get_db
from app.models.user import User
from app.dependencies import get_current_user
from app.services.attendance import manual_check, get_today_attendance, get_user_attendance

router = APIRouter(prefix="/api/attendance", tags=["attendance"])


@router.post("/check-in")
def check_in(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """수동 출근 기록"""
    result = manual_check(user_id=current_user.id, check_type="in", db=db)
    return result


@router.post("/check-out")
def check_out(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """수동 퇴근 기록"""
    result = manual_check(user_id=current_user.id, check_type="out", db=db)
    return result


@router.get("/today")
def today_attendance(db: Session = Depends(get_db)):
    """관리자: 전체 오늘 출퇴근 현황"""
    return get_today_attendance(db)


@router.get("/me")
def my_attendance(
    days: int = 7,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """개인 출퇴근 이력 (최근 N일)"""
    return get_user_attendance(user_id=current_user.id, db=db, days=days)
