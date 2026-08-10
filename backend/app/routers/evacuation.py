from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from app.models.database import get_db
from app.models.location import EvacuationStatus
from app.models.user import User
from app.models.building import Floor
from app.models.alert import Alert, AlertType
from app.services.evacuation import calculate_evacuation_route, calculate_rescuer_route
from app.services.direction import compute_next_step, direction_to_degrees, direction_to_arrow
from app.services.ai_route import generate_ai_guidance
from app.services.location import get_unconscious_workers as svc_get_unconscious

router = APIRouter(prefix="/api/evacuation", tags=["evacuation"])


# --- Request Schemas ---

class RouteRequest(BaseModel):
    user_id: int
    floor_id: int
    x: float
    y: float


class EvacuationStatusUpdate(BaseModel):
    user_id: int
    status: str  # in_building, evacuating, evacuated, unconscious


# --- Response Schemas ---

class PathNode(BaseModel):
    node_id: int
    x: float
    y: float
    node_type: str


class RouteResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    start_node: Optional[int] = None
    exit_node: Optional[int] = None
    distance: Optional[float] = None
    path: Optional[List[PathNode]] = None


class RescuerRouteResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    start_node: Optional[int] = None
    target_node: Optional[int] = None
    distance: Optional[float] = None
    path: Optional[List[PathNode]] = None


class EvacuationStatusResponse(BaseModel):
    user_id: int
    user_name: Optional[str] = None
    status: str
    last_floor_id: Optional[int] = None
    last_x: Optional[float] = None
    last_y: Optional[float] = None
    is_moving: Optional[bool] = None
    heart_rate: Optional[int] = None
    sos_sent: Optional[bool] = None
    updated_at: Optional[str] = None


class UnconsciousWorker(BaseModel):
    user_id: int
    floor_id: Optional[int] = None
    x: Optional[float] = None
    y: Optional[float] = None
    heart_rate: Optional[int] = None
    updated_at: Optional[str] = None


VALID_STATUSES = {"in_building", "evacuating", "evacuated", "unconscious"}


# --- Endpoints ---

@router.post("/route", response_model=RouteResponse)
def get_evacuation_route(data: RouteRequest, db: Session = Depends(get_db)):
    """현재 위치 기반 최적 탈출 경로 계산"""
    result = calculate_evacuation_route(data.floor_id, data.x, data.y, db)

    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("message", "경로를 찾을 수 없습니다."))

    return RouteResponse(
        success=True,
        start_node=result["start_node"],
        exit_node=result["exit_node"],
        distance=result["distance"],
        path=[PathNode(**node) for node in result["path"]],
    )


@router.get("/status", response_model=List[EvacuationStatusResponse])
def get_all_evacuation_status(db: Session = Depends(get_db)):
    """전체 대피 현황 (관리자/구조대용)"""
    statuses = db.query(EvacuationStatus).all()

    results = []
    for s in statuses:
        user = db.query(User).filter(User.id == s.user_id).first()
        results.append(EvacuationStatusResponse(
            user_id=s.user_id,
            user_name=user.name if user else None,
            status=s.status,
            last_floor_id=s.last_floor_id,
            last_x=s.last_x,
            last_y=s.last_y,
            is_moving=s.is_moving,
            heart_rate=s.heart_rate,
            sos_sent=s.sos_sent,
            updated_at=str(s.updated_at) if s.updated_at else None,
        ))

    return results


@router.get("/status/{user_id}", response_model=EvacuationStatusResponse)
def get_user_evacuation_status(user_id: int, db: Session = Depends(get_db)):
    """특정 근로자 대피 상태"""
    s = db.query(EvacuationStatus).filter(EvacuationStatus.user_id == user_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="해당 사용자의 대피 상태가 없습니다.")

    user = db.query(User).filter(User.id == s.user_id).first()
    return EvacuationStatusResponse(
        user_id=s.user_id,
        user_name=user.name if user else None,
        status=s.status,
        last_floor_id=s.last_floor_id,
        last_x=s.last_x,
        last_y=s.last_y,
        is_moving=s.is_moving,
        heart_rate=s.heart_rate,
        sos_sent=s.sos_sent,
        updated_at=str(s.updated_at) if s.updated_at else None,
    )


@router.put("/status", response_model=EvacuationStatusResponse)
def update_evacuation_status(data: EvacuationStatusUpdate, db: Session = Depends(get_db)):
    """대피 상태 갱신"""
    if data.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"유효하지 않은 상태입니다. 허용값: {', '.join(VALID_STATUSES)}",
        )

    s = db.query(EvacuationStatus).filter(EvacuationStatus.user_id == data.user_id).first()
    if s:
        s.status = data.status
        s.updated_at = datetime.utcnow()
    else:
        s = EvacuationStatus(
            user_id=data.user_id,
            status=data.status,
        )
        db.add(s)

    db.commit()
    db.refresh(s)

    user = db.query(User).filter(User.id == s.user_id).first()
    return EvacuationStatusResponse(
        user_id=s.user_id,
        user_name=user.name if user else None,
        status=s.status,
        last_floor_id=s.last_floor_id,
        last_x=s.last_x,
        last_y=s.last_y,
        is_moving=s.is_moving,
        heart_rate=s.heart_rate,
        sos_sent=s.sos_sent,
        updated_at=str(s.updated_at) if s.updated_at else None,
    )


@router.get("/unconscious", response_model=List[UnconsciousWorker])
def get_unconscious_workers_endpoint(db: Session = Depends(get_db)):
    """의식 불명/미대피 근로자 목록 (구조대 뷰)"""
    workers = svc_get_unconscious(db)
    return [UnconsciousWorker(**w) for w in workers]


@router.get("/rescuer-route/{target_user_id}", response_model=RescuerRouteResponse)
def get_rescuer_route(
    target_user_id: int,
    floor_id: int,
    x: float,
    y: float,
    db: Session = Depends(get_db),
):
    """구조대원 → 미대피자까지 최적 진입 경로"""
    # 대상자의 마지막 위치 조회
    target_status = (
        db.query(EvacuationStatus)
        .filter(EvacuationStatus.user_id == target_user_id)
        .first()
    )
    if not target_status:
        raise HTTPException(status_code=404, detail="대상자의 위치 정보가 없습니다.")

    if target_status.last_x is None or target_status.last_y is None:
        raise HTTPException(status_code=404, detail="대상자의 좌표 정보가 없습니다.")

    # 구조대원 위치(floor_id, x, y)에서 대상자 위치까지 경로 계산
    # 같은 층인 경우만 경로 계산 (다층 경로는 추후 확장)
    target_floor = target_status.last_floor_id
    if target_floor != floor_id:
        raise HTTPException(
            status_code=400,
            detail=f"구조대원과 대상자가 다른 층에 있습니다. (구조대원: {floor_id}층, 대상자: {target_floor}층)",
        )

    result = calculate_rescuer_route(
        floor_id=floor_id,
        rescuer_x=x,
        rescuer_y=y,
        target_x=target_status.last_x,
        target_y=target_status.last_y,
        db=db,
    )

    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("message", "경로를 찾을 수 없습니다."))

    return RescuerRouteResponse(
        success=True,
        start_node=result["start_node"],
        target_node=result["target_node"],
        distance=result["distance"],
        path=[PathNode(**node) for node in result["path"]],
    )


# --- AI Guidance Endpoint ---

class GuidanceRequest(BaseModel):
    floor_id: int
    x: float            # 현재 도면 좌표 (mm)
    y: float
    heading: Optional[float] = 0.0  # 사용자 진행 방향 (degree, 디바이스 컴퍼스. 0=북)
    user_id: Optional[int] = None   # 도착 시 대피 상태 자동 전환용


class GuidanceResponse(BaseModel):
    success: bool
    direction: Optional[str] = None         # straight, left, right, ...
    arrow: Optional[str] = None             # ⬆️, ⬅️, ➡️, ...
    rotate_deg: Optional[float] = None      # CSS rotate 각도 (프론트 화살표용)
    distance_m: Optional[float] = None      # 다음 waypoint까지 거리 (m)
    instruction: Optional[str] = None       # 한국어 안내 문구
    warning: Optional[str] = None           # 위험 경고 (화재 근처 시)
    next_landmark: Optional[str] = None     # 다음 랜드마크 (출구A, 계단1 등)
    bearing: Optional[float] = None         # 절대 방위각
    total_distance_m: Optional[float] = None  # 출구까지 총 남은 거리
    exit_name: Optional[str] = None         # 목표 출구 이름
    path: Optional[List[PathNode]] = None   # 전체 경로 (프론트 시각화용)
    arrived: bool = False                   # 출구 도착 여부
    message: Optional[str] = None           # 에러 메시지


@router.post("/guidance", response_model=GuidanceResponse)
async def get_guidance(data: GuidanceRequest, db: Session = Depends(get_db)):
    """
    Worker 모바일 화살표 방향 안내 API

    현재 위치 + 층 정보를 받아:
    1. 최적 대피 경로 계산 (Dijkstra)
    2. 로컬 방향/거리 계산 (즉시 응답)
    3. OpenAI 자연어 안내 생성 (선택적 보강)

    반환: 화살표 방향 + 거리 + 안내 문구
    """
    # 1. 경로 계산
    route_result = calculate_evacuation_route(data.floor_id, data.x, data.y, db)

    if not route_result.get("success"):
        return GuidanceResponse(
            success=False,
            message=route_result.get("message", "경로를 찾을 수 없습니다."),
        )

    path_coords = route_result["path"]
    total_distance_mm = route_result["distance"]

    # 2. 로컬 방향 계산 (즉시)
    step = compute_next_step(
        current_x=data.x,
        current_y=data.y,
        path_coords=path_coords,
        user_heading=data.heading or 0.0,
    )

    # 출구 이름 찾기
    exit_name = None
    if path_coords:
        last_node = path_coords[-1]
        exit_name = last_node.get("label") or (
            "출구" if last_node.get("node_type") == "exit" else None
        )

    # 3. 화재 위치 조회 (경고 메시지용)
    fire_alerts = (
        db.query(Alert)
        .filter(Alert.alert_type == AlertType.FIRE, Alert.is_resolved == False)
        .filter(Alert.floor_id == data.floor_id)
        .all()
    )
    fire_positions = [{"x": a.x, "y": a.y} for a in fire_alerts if a.x and a.y]

    # 화재 근접 경고 (현재 위치에서 10m 이내 화재)
    warning = None
    for fire in fire_positions:
        from app.services.direction import calculate_distance_m
        fire_dist = calculate_distance_m(data.x, data.y, fire["x"], fire["y"])
        if fire_dist < 10:
            warning = f"⚠️ {fire_dist:.0f}m 앞에 화재 구역이 있습니다. 우회 경로로 이동 중입니다."
            break

    # 4. OpenAI 보강 (API 키가 설정된 경우에만)
    ai_instruction = None
    try:
        floor = db.query(Floor).filter(Floor.id == data.floor_id).first()
        floor_name = floor.name if floor else "알 수 없음"

        # path_coords에 label 정보 추가
        from app.models.building import FloorNode
        enriched_path = []
        for p in path_coords:
            node = db.query(FloorNode).filter(FloorNode.id == p["node_id"]).first()
            enriched_path.append({
                **p,
                "label": node.label if node else "",
            })

        ai_result = await generate_ai_guidance(
            current_x=data.x,
            current_y=data.y,
            path_coords=enriched_path,
            fire_positions=fire_positions,
            floor_name=floor_name,
        )

        if ai_result:
            ai_instruction = ai_result.get("instruction")
            if ai_result.get("warning"):
                warning = ai_result["warning"]
    except Exception:
        pass  # AI 실패 시 로컬 결과만 사용

    # 5. 도착 감지: 출구 노드까지 5m(5000mm) 이내이면 대피 완료 처리
    ARRIVAL_THRESHOLD_MM = 5000.0
    arrived = False
    total_dist_m = round(total_distance_mm * 0.001, 1)

    if total_distance_mm <= ARRIVAL_THRESHOLD_MM:
        arrived = True
        # 대피 상태를 evacuated로 자동 전환
        if data.user_id:
            evac_status = (
                db.query(EvacuationStatus)
                .filter(EvacuationStatus.user_id == data.user_id)
                .first()
            )
            if evac_status and evac_status.status != "evacuated":
                evac_status.status = "evacuated"
                evac_status.updated_at = datetime.utcnow()
                db.commit()

    return GuidanceResponse(
        success=True,
        direction=step["direction"],
        arrow=step["arrow"],
        rotate_deg=step["rotate_deg"],
        distance_m=step["distance_m"],
        instruction="🎉 출구에 도착했습니다! 건물 밖으로 대피하세요." if arrived else (ai_instruction or step["instruction"]),
        warning=warning,
        next_landmark=step["next_landmark"],
        bearing=step["bearing"],
        total_distance_m=total_dist_m,
        exit_name=exit_name,
        path=[PathNode(**node) for node in path_coords],
        arrived=arrived,
        message=None,
    )
