"""
GPS ↔ 도면 좌표 변환 서비스

최소 2개의 FloorAnchor 기준점을 이용하여 affine transform으로 변환.
- 2개: 정확한 affine (스케일 + 이동)
- 3개 이상: least squares fit (회전 포함)
"""

from sqlalchemy.orm import Session
from typing import Optional, Tuple, List
import numpy as np

from app.models.building import FloorAnchor


def _get_anchors(floor_id: int, db: Session) -> List[FloorAnchor]:
    """해당 층의 앵커 목록 조회"""
    return db.query(FloorAnchor).filter(FloorAnchor.floor_id == floor_id).all()


def _compute_affine_matrix(
    src_points: List[Tuple[float, float]],
    dst_points: List[Tuple[float, float]],
) -> Optional[np.ndarray]:
    """
    src → dst 변환을 위한 affine 행렬 계산.
    반환: 2x3 행렬 [[a, b, tx], [c, d, ty]]

    2점: 스케일 + 이동 (회전 없음)
    3점 이상: least squares fit (회전 + 스케일 + 이동)
    """
    n = len(src_points)
    if n < 2:
        return None

    if n == 2:
        # 2점 기반: 스케일 + 이동 (회전 무시)
        (sx0, sy0), (sx1, sy1) = src_points
        (dx0, dy0), (dx1, dy1) = dst_points

        # x, y 각각 독립 선형 매핑
        dsx = sx1 - sx0
        dsy = sy1 - sy0

        if abs(dsx) < 1e-10 or abs(dsy) < 1e-10:
            # 두 점이 같은 축 위에 있으면 변환 불가
            return None

        scale_x = (dx1 - dx0) / dsx
        scale_y = (dy1 - dy0) / dsy
        tx = dx0 - scale_x * sx0
        ty = dy0 - scale_y * sy0

        return np.array([
            [scale_x, 0, tx],
            [0, scale_y, ty],
        ])

    # 3점 이상: least squares로 affine 계수 추정
    # [x'] = [a b tx] [x]
    # [y']   [c d ty] [y]
    #                 [1]
    A = np.zeros((2 * n, 6))
    b = np.zeros(2 * n)

    for i, ((sx, sy), (dx, dy)) in enumerate(zip(src_points, dst_points)):
        A[2 * i] = [sx, sy, 1, 0, 0, 0]
        A[2 * i + 1] = [0, 0, 0, sx, sy, 1]
        b[2 * i] = dx
        b[2 * i + 1] = dy

    # least squares solve
    result, _, _, _ = np.linalg.lstsq(A, b, rcond=None)
    a, bv, tx, c, d, ty = result

    return np.array([
        [a, bv, tx],
        [c, d, ty],
    ])


def _apply_affine(matrix: np.ndarray, x: float, y: float) -> Tuple[float, float]:
    """affine 행렬을 좌표에 적용"""
    point = np.array([x, y, 1.0])
    result = matrix @ point
    return float(result[0]), float(result[1])


def gps_to_floor(
    lat: float, lng: float, floor_id: int, db: Session
) -> Optional[Tuple[float, float]]:
    """
    GPS 좌표 (위도, 경도) → 도면 좌표 (px_x, px_y) 변환

    Returns:
        (px_x, px_y) 또는 앵커 부족 시 None
    """
    anchors = _get_anchors(floor_id, db)
    if len(anchors) < 2:
        return None

    # src: GPS (lng, lat) → dst: 도면 (px_x, px_y)
    src_points = [(a.gps_lng, a.gps_lat) for a in anchors]
    dst_points = [(a.px_x, a.px_y) for a in anchors]

    matrix = _compute_affine_matrix(src_points, dst_points)
    if matrix is None:
        return None

    return _apply_affine(matrix, lng, lat)


def floor_to_gps(
    px_x: float, px_y: float, floor_id: int, db: Session
) -> Optional[Tuple[float, float]]:
    """
    도면 좌표 (px_x, px_y) → GPS 좌표 (위도, 경도) 변환

    Returns:
        (lat, lng) 또는 앵커 부족 시 None
    """
    anchors = _get_anchors(floor_id, db)
    if len(anchors) < 2:
        return None

    # src: 도면 (px_x, px_y) → dst: GPS (lng, lat)
    src_points = [(a.px_x, a.px_y) for a in anchors]
    dst_points = [(a.gps_lng, a.gps_lat) for a in anchors]

    matrix = _compute_affine_matrix(src_points, dst_points)
    if matrix is None:
        return None

    lng, lat = _apply_affine(matrix, px_x, px_y)
    return (lat, lng)


def has_anchors(floor_id: int, db: Session) -> bool:
    """해당 층에 변환 가능한 앵커가 2개 이상 있는지 확인"""
    count = db.query(FloorAnchor).filter(FloorAnchor.floor_id == floor_id).count()
    return count >= 2
