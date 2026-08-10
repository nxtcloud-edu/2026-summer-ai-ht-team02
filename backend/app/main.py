from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Set
import json

from app.models.database import Base, engine
from app.routers import (
    auth_router,
    buildings_router,
    locations_router,
    alerts_router,
    evacuation_router,
    peers_router,
)

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="FireEscape AI API",
    version="0.1.0",
    description="위치 기반 실시간 탈출 경로 제공 시스템",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# REST Routers
app.include_router(auth_router)
app.include_router(buildings_router)
app.include_router(locations_router)
app.include_router(alerts_router)
app.include_router(evacuation_router)
app.include_router(peers_router)


# --- WebSocket Connection Manager ---

class ConnectionManager:
    """WebSocket 연결 관리"""

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


manager = ConnectionManager()


# --- WebSocket Endpoints ---

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int, role: str = "worker"):
    """
    WebSocket 연결
    - 근로자: 화재 알림 수신, 탈출 경로 수신, SOS 수신
    - 관리자: 위치 업데이트 수신, 알림 수신
    - 구조대: 미대피자 위치, 알림 수신
    """
    await manager.connect(websocket, user_id, role)

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            msg_type = message.get("type")

            if msg_type == "location_update":
                # 근로자 위치 업데이트 → 관리자/구조대에 전달
                await manager.broadcast_to_admins({
                    "type": "worker_location",
                    "user_id": user_id,
                    "floor_id": message.get("floor_id"),
                    "x": message.get("x"),
                    "y": message.get("y"),
                })
                await manager.broadcast_to_rescuers({
                    "type": "worker_location",
                    "user_id": user_id,
                    "floor_id": message.get("floor_id"),
                    "x": message.get("x"),
                    "y": message.get("y"),
                })

            elif msg_type == "fire_alert":
                # 화재 알림 → 전체 브로드캐스트
                await manager.broadcast_all({
                    "type": "fire_alert",
                    "floor_id": message.get("floor_id"),
                    "x": message.get("x"),
                    "y": message.get("y"),
                    "message": message.get("message", "화재 발생"),
                })

            elif msg_type == "sos":
                # SOS → 같은 층 동료 + 관리자/구조대에게 전송
                await manager.broadcast_to_admins({
                    "type": "sos_alert",
                    "sender_id": user_id,
                    "floor_id": message.get("floor_id"),
                    "x": message.get("x"),
                    "y": message.get("y"),
                    "message": message.get("message"),
                })
                await manager.broadcast_to_rescuers({
                    "type": "sos_alert",
                    "sender_id": user_id,
                    "floor_id": message.get("floor_id"),
                    "x": message.get("x"),
                    "y": message.get("y"),
                    "message": message.get("message"),
                })
                # 동료에게도 전송
                await manager.broadcast_to_workers({
                    "type": "peer_sos",
                    "sender_id": user_id,
                    "floor_id": message.get("floor_id"),
                    "x": message.get("x"),
                    "y": message.get("y"),
                    "message": message.get("message"),
                })

            elif msg_type == "evacuation_complete":
                # 대피 완료 알림
                await manager.broadcast_to_admins({
                    "type": "evacuation_complete",
                    "user_id": user_id,
                })

    except WebSocketDisconnect:
        manager.disconnect(user_id)


# --- Health Check ---

@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "fire-escape-ai"}
