import networkx as nx
from sqlalchemy.orm import Session
from typing import List, Optional, Tuple

from app.models.building import FloorNode, FloorEdge


def build_floor_graph(floor_id: int, db: Session) -> nx.Graph:
    """층의 노드/엣지로 NetworkX 그래프 생성"""
    G = nx.Graph()

    nodes = db.query(FloorNode).filter(FloorNode.floor_id == floor_id).all()
    edges = db.query(FloorEdge).filter(FloorEdge.floor_id == floor_id).all()

    for node in nodes:
        G.add_node(node.id, x=node.x, y=node.y, node_type=node.node_type, label=node.label)

    for edge in edges:
        if edge.is_blocked:
            continue  # 화재로 차단된 경로 제외
        weight = edge.distance if edge.distance else 1.0
        G.add_edge(edge.from_node_id, edge.to_node_id, weight=weight, edge_id=edge.id)

    return G


def find_nearest_node(floor_id: int, x: float, y: float, db: Session) -> Optional[int]:
    """좌표에서 가장 가까운 노드 ID 반환"""
    nodes = db.query(FloorNode).filter(FloorNode.floor_id == floor_id).all()
    if not nodes:
        return None

    nearest = None
    min_dist = float("inf")

    for node in nodes:
        dist = ((node.x - x) ** 2 + (node.y - y) ** 2) ** 0.5
        if dist < min_dist:
            min_dist = dist
            nearest = node.id

    return nearest


def find_exit_nodes(floor_id: int, db: Session) -> List[int]:
    """출구 노드 목록"""
    exits = (
        db.query(FloorNode)
        .filter(FloorNode.floor_id == floor_id, FloorNode.node_type == "exit")
        .all()
    )
    return [e.id for e in exits]


def calculate_evacuation_route(
    floor_id: int, x: float, y: float, db: Session
) -> dict:
    """현재 위치에서 가장 가까운 출구까지 최적 경로 계산"""
    G = build_floor_graph(floor_id, db)

    if G.number_of_nodes() == 0:
        return {"success": False, "message": "도면에 노드가 없습니다."}

    # 현재 위치에서 가장 가까운 노드 찾기
    start_node = find_nearest_node(floor_id, x, y, db)
    if start_node is None or start_node not in G:
        return {"success": False, "message": "현재 위치 근처에 경로 노드가 없습니다."}

    # 출구 노드 목록
    exit_nodes = find_exit_nodes(floor_id, db)
    if not exit_nodes:
        return {"success": False, "message": "출구가 등록되지 않았습니다."}

    # 각 출구까지 최단 경로 계산 후 가장 짧은 경로 선택
    best_path = None
    best_distance = float("inf")
    best_exit = None

    for exit_node in exit_nodes:
        if exit_node not in G:
            continue
        try:
            path = nx.shortest_path(G, source=start_node, target=exit_node, weight="weight")
            distance = nx.shortest_path_length(G, source=start_node, target=exit_node, weight="weight")
            if distance < best_distance:
                best_distance = distance
                best_path = path
                best_exit = exit_node
        except nx.NetworkXNoPath:
            continue

    if best_path is None:
        return {"success": False, "message": "모든 출구로의 경로가 차단되었습니다."}

    # 경로 노드의 좌표 목록 생성
    path_coords = []
    for node_id in best_path:
        node_data = G.nodes[node_id]
        path_coords.append({
            "node_id": node_id,
            "x": node_data["x"],
            "y": node_data["y"],
            "node_type": node_data["node_type"],
        })

    return {
        "success": True,
        "start_node": start_node,
        "exit_node": best_exit,
        "distance": round(best_distance, 2),
        "path": path_coords,
    }


def calculate_rescuer_route(
    floor_id: int,
    rescuer_x: float, rescuer_y: float,
    target_x: float, target_y: float,
    db: Session,
) -> dict:
    """구조대원 → 대상자까지 최적 진입 경로"""
    G = build_floor_graph(floor_id, db)

    if G.number_of_nodes() == 0:
        return {"success": False, "message": "도면에 노드가 없습니다."}

    start_node = find_nearest_node(floor_id, rescuer_x, rescuer_y, db)
    target_node = find_nearest_node(floor_id, target_x, target_y, db)

    if start_node is None or target_node is None:
        return {"success": False, "message": "위치 근처에 노드가 없습니다."}

    if start_node not in G or target_node not in G:
        return {"success": False, "message": "노드가 그래프에 포함되지 않았습니다."}

    try:
        path = nx.shortest_path(G, source=start_node, target=target_node, weight="weight")
        distance = nx.shortest_path_length(G, source=start_node, target=target_node, weight="weight")
    except nx.NetworkXNoPath:
        return {"success": False, "message": "대상자까지의 경로가 차단되었습니다."}

    path_coords = []
    for node_id in path:
        node_data = G.nodes[node_id]
        path_coords.append({
            "node_id": node_id,
            "x": node_data["x"],
            "y": node_data["y"],
            "node_type": node_data["node_type"],
        })

    return {
        "success": True,
        "start_node": start_node,
        "target_node": target_node,
        "distance": round(distance, 2),
        "path": path_coords,
    }
