from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, timedelta
from jose import jwt
import bcrypt

from app.config import settings
from app.models.database import get_db
from app.models.user import User, UserRole
from app.dependencies import get_current_user, require_role

router = APIRouter(prefix="/api/auth", tags=["auth"])


# --- Schemas ---

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
    user_id: int
    role: str


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    role: str
    department: Optional[str] = None
    floor_id: Optional[int] = None
    is_active: bool

    class Config:
        from_attributes = True


# --- Helpers ---

def create_access_token(user_id: int) -> str:
    """JWT 토큰 생성"""
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def hash_password(password: str) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")


# --- Endpoints ---

@router.post("/register", response_model=TokenResponse)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """회원가입"""
    # 이메일 중복 확인
    existing = db.query(User).filter(User.email == request.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 등록된 이메일입니다",
        )

    # 역할 검증
    try:
        role = UserRole(request.role)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"유효하지 않은 역할입니다: {request.role}",
        )

    # 유저 생성
    user = User(
        email=request.email,
        hashed_password=hash_password(request.password),
        name=request.name,
        role=role,
        department=request.department,
        smartwatch_id=request.smartwatch_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        role=user.role.value,
    )


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """로그인"""
    user = db.query(User).filter(User.email == request.email).first()
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="비활성화된 계정입니다",
        )

    token = create_access_token(user.id)
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        role=user.role.value,
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """현재 사용자 정보"""
    return current_user


@router.get("/workers", response_model=List[UserResponse])
def list_workers(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.RESCUER)),
):
    """전체 근로자 목록 (관리자/구조대용)"""
    workers = db.query(User).filter(User.role == UserRole.WORKER, User.is_active == True).all()
    return workers
