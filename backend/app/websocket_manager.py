from fastapi import WebSocket
from typing import Dict, Set


class ConnectionManager:
    """WebSocket 연결 관리 — 라우터에서도 import하여 broadcast 가능"""

    def __init__(self):
        # user_id → WebSocket 매핑
        self.active_connections: Dict[int, WebSocket] = {}
        # 역할별 그룹
        self.admin_connections: Set[int] = set()
        self.rescuer_connections: Set[int] = set()
        self.worker_connections: Set[int] = set()

    async def connect(self, websocket: WebSocket, user_id: int, role: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        if role == "admin":
            self.admin_connections.add(user_id)
        elif role == "rescuer":
            self.rescuer_connections.add(user_id)
        else:
            self.worker_connections.add(user_id)

    def disconnect(self, user_id: int):
        self.active_connections.pop(user_id, None)
        self.admin_connections.discard(user_id)
        self.rescuer_connections.discard(user_id)
        self.worker_connections.discard(user_id)

    async def send_to_user(self, user_id: int, message: dict):
        """특정 사용자에게 메시지 전송"""
        ws = self.active_connections.get(user_id)
        if ws:
            await ws.send_json(message)

    async def broadcast_to_workers(self, message: dict):
        """전체 근로자에게 브로드캐스트"""
        for uid in self.worker_connections:
            ws = self.active_connections.get(uid)
            if ws:
                await ws.send_json(message)

    async def broadcast_to_admins(self, message: dict):
        """관리자에게 브로드캐스트"""
        for uid in self.admin_connections:
            ws = self.active_connections.get(uid)
            if ws:
                await ws.send_json(message)

    async def broadcast_to_rescuers(self, message: dict):
        """구조대에게 브로드캐스트"""
        for uid in self.rescuer_connections:
            ws = self.active_connections.get(uid)
            if ws:
                await ws.send_json(message)

    async def broadcast_all(self, message: dict):
        """전체 브로드캐스트"""
        for uid, ws in self.active_connections.items():
            await ws.send_json(message)

    async def broadcast_location_update(self, user_id: int, floor_id: int, x: float, y: float):
        """위치 업데이트를 관리자/구조대에게 브로드캐스트"""
        message = {
            "type": "worker_location",
            "user_id": user_id,
            "floor_id": floor_id,
            "x": x,
            "y": y,
        }
        await self.broadcast_to_admins(message)
        await self.broadcast_to_rescuers(message)


# 싱글톤 인스턴스 — 라우터에서 import 가능
manager = ConnectionManager()
