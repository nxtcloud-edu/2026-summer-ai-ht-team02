from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional

from app.models.database import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str = "worker"  # worker, admin, rescuer
    department: Optional[str] = None
    smartwatch_id: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/register", response_model=TokenResponse)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """회원가입"""
    # TODO: 구현
    pass


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """로그인"""
    # TODO: 구현
    pass


@router.get("/me")
def get_current_user():
    """현재 사용자 정보"""
    # TODO: 구현
    pass


@router.get("/workers")
def list_workers(db: Session = Depends(get_db)):
    """전체 근로자 목록 (관리자용)"""
    # TODO: 구현
    pass
