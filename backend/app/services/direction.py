"""
로컬 방향/거리 계산 유틸리티

OpenAI API 호출 없이 좌표 기반으로 방향과 거리를 계산한다.
- 도면 좌표계: X 오른쪽 +, Y 아래쪽 + (일반적인 이미지 좌표계)
- 단위: mm (도면 기준)
"""

import math
from typing import Tuple, List


# 도면 mm → 실제 m 변환 스케일 (1px = 1mm, 1000mm = 1m)
MM_TO_M = 0.001


def calculate_bearing(from_x: float, from_y: float, to_x: float, to_y: float) -> float:
    """
    두 점 사이 방위각 계산 (도면 좌표 기준)

    반환: 0~360도 (0=위(북), 90=오른쪽(동), 180=아래(남), 270=왼쪽(서))
    도면 Y축은 아래가 + 이므로 반전 처리
    """
    dx = to_x - from_x
    dy = -(to_y - from_y)  # Y축 반전 (도면: 아래가 +, 방위: 위가 +)
    angle = math.degrees(math.atan2(dx, dy)) % 360
    return angle


def bearing_to_direction(bearing: float, user_heading: float = 0.0) -> str:
    """
    절대 방위각 → 사용자 기준 상대 방향

    Args:
        bearing: 절대 방위각 (0=북)
        user_heading: 사용자가 바라보는 방향 (0=북, 디바이스 컴퍼스)

    Returns:
        "straight" | "left" | "right" | "back" | "slight_left" | "slight_right"
    """
    relative = (bearing - user_heading + 360) % 360

    if relative < 20 or relative >= 340:
        return "straight"
    elif 20 <= relative < 70:
        return "slight_right"
    elif 70 <= relative < 150:
        return "right"
    elif 150 <= relative < 210:
        return "back"
    elif 210 <= relative < 290:
        return "left"
    else:
        return "slight_left"


def calculate_distance_mm(x1: float, y1: float, x2: float, y2: float) -> float:
    """두 점 사이 유클리드 거리 (mm)"""
    return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5


def calculate_distance_m(x1: float, y1: float, x2: float, y2: float) -> float:
    """두 점 사이 유클리드 거리 (m)"""
    return calculate_distance_mm(x1, y1, x2, y2) * MM_TO_M


def direction_to_arrow(direction: str) -> str:
    """방향 문자열 → 화살표 이모지"""
    arrows = {
        "straight": "⬆️",
        "slight_right": "↗️",
        "right": "➡️",
        "back": "⬇️",
        "left": "⬅️",
        "slight_left": "↖️",
    }
    return arrows.get(direction, "⬆️")


def direction_to_degrees(direction: str) -> float:
    """방향 문자열 → CSS rotate 각도 (0=위)"""
    degrees = {
        "straight": 0,
        "slight_right": 45,
        "right": 90,
        "back": 180,
        "left": 270,
        "slight_left": 315,
    }
    return degrees.get(direction, 0)


def direction_to_korean(direction: str) -> str:
    """방향 → 한국어"""
    labels = {
        "straight": "직진",
        "slight_right": "우측 전방",
        "right": "우회전",
        "back": "뒤로",
        "left": "좌회전",
        "slight_left": "좌측 전방",
    }
    return labels.get(direction, "직진")


def compute_next_step(
    current_x: float,
    current_y: float,
    path_coords: List[dict],
    user_heading: float = 0.0,
) -> dict:
    """
    현재 위치 + 경로 좌표 → 다음 이동 안내 계산

    Args:
        current_x, current_y: 현재 도면 좌표 (mm)
        path_coords: 경로 노드 리스트 [{x, y, node_type, node_id, ...}, ...]
        user_heading: 사용자 진행 방향 (degree, 디바이스 컴퍼스)

    Returns:
        {
            direction: str,
            arrow: str,
            rotate_deg: float,
            distance_m: float,
            instruction: str,
            next_landmark: str | None,
            bearing: float,
        }
    """
    if not path_coords or len(path_coords) < 1:
        return {
            "direction": "straight",
            "arrow": "⬆️",
            "rotate_deg": 0,
            "distance_m": 0,
            "instruction": "경로 정보가 없습니다",
            "next_landmark": None,
            "bearing": 0,
        }

    # 다음 목표 노드 (경로의 첫 번째 또는 두 번째 — 첫 번째가 현재 위치 근처면 스킵)
    target_idx = 0
    if len(path_coords) > 1:
        dist_to_first = calculate_distance_mm(
            current_x, current_y, path_coords[0]["x"], path_coords[0]["y"]
        )
        # 첫 노드가 2m 이내면 다음 노드를 타겟으로
        if dist_to_first < 2000:
            target_idx = 1

    target = path_coords[target_idx]
    target_x = target["x"]
    target_y = target["y"]

    bearing = calculate_bearing(current_x, current_y, target_x, target_y)
    direction = bearing_to_direction(bearing, user_heading)
    distance = calculate_distance_m(current_x, current_y, target_x, target_y)

    # 다음 랜드마크 (exit/stair 노드 중 가장 가까운 것)
    next_landmark = None
    for node in path_coords[target_idx:]:
        if node.get("node_type") in ("exit", "stair"):
            next_landmark = node.get("label") or node.get("node_type")
            break

    # 안내 문구 생성
    dir_korean = direction_to_korean(direction)
    dist_rounded = round(distance)
    if dist_rounded < 1:
        instruction = f"{dir_korean} 방향으로 이동하세요"
    else:
        instruction = f"{dir_korean} 방향으로 {dist_rounded}m 이동하세요"

    if next_landmark:
        instruction += f" (다음: {next_landmark})"

    return {
        "direction": direction,
        "arrow": direction_to_arrow(direction),
        "rotate_deg": direction_to_degrees(direction),
        "distance_m": round(distance, 1),
        "instruction": instruction,
        "next_landmark": next_landmark,
        "bearing": round(bearing, 1),
    }
