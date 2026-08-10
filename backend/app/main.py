from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json

from app.models.database import Base, engine
from app.websocket_manager import manager
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
                await manager.broadcast_location_update(
                    user_id=user_id,
                    floor_id=message.get("floor_id"),
                    x=message.get("x"),
                    y=message.get("y"),
                )

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
                # SOS → 관리자/구조대 + 동료에게 전송
                sos_msg = {
                    "type": "sos_alert",
                    "sender_id": user_id,
                    "floor_id": message.get("floor_id"),
                    "x": message.get("x"),
                    "y": message.get("y"),
                    "message": message.get("message"),
                }
                await manager.broadcast_to_admins(sos_msg)
                await manager.broadcast_to_rescuers(sos_msg)
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
