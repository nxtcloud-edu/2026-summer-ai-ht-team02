# 동료 간 SOS 구현 계획

## 현재 상태

| 구성 요소 | 상태 | 비고 |
|---|---|---|
| `models/alert.py` — Alert 모델 (AlertType.SOS) | ✅ 완료 | SOS 알림 저장 가능 |
| `models/location.py` — EvacuationStatus.sos_sent | ✅ 완료 | SOS 발송 여부 플래그 |
| `services/peers.py` — send_sos, get_nearby_peers | ✅ 완료 | 비즈니스 로직 구현됨 |
| `services/alert.py` — create_sos_alert | ✅ 완료 | SOS Alert DB 저장 |
| `routers/peers.py` — 4개 엔드포인트 스텁 | 🔲 TODO | pass 상태, 구현 필요 |
| `websocket_manager.py` — broadcast 메서드 | ✅ 완료 | 동료 전파용 메서드 존재 |
| `main.py` — WebSocket "sos" 메시지 핸들링 | ✅ 완료 | peer_sos 브로드캐스트 동작 |

**결론:** 서비스 레이어와 WebSocket은 이미 준비됨. 라우터 엔드포인트 구현 + SOS 응답 서비스 로직 추가가 핵심 작업.

---

## 구현 대상 API

### 1. `POST /api/peers/sos` — SOS 발송

**역할:** 위기 상황의 근로자가 도움을 요청

```
요청 (JWT 인증 필수):
{
  "floor_id": 2,
  "x": 150.0,
  "y": 80.0,
  "message": "다리를 다쳐서 이동 불가"   // optional
}

응답 201:
{
  "alert_id": 7,
  "type": "sos",
  "sender_id": 3,
  "floor_id": 2,
  "x": 150.0,
  "y": 80.0,
  "message": "다리를 다쳐서 이동 불가",
  "nearby_peers": [
    {"user_id": 5, "x": 140.0, "y": 75.0, "distance": 11.2, "status": "evacuating"},
    {"user_id": 8, "x": 160.0, "y": 90.0, "distance": 14.1, "status": "in_building"}
  ]
}
```

**로직:**
1. JWT에서 `sender_id` 추출 (body에 넣지 않음 — 보안)
2. `services/peers.send_sos()` 호출 → Alert 생성 + EvacuationStatus.sos_sent = True
3. WebSocket으로 같은 층 동료에게 `peer_sos` 메시지 push
4. 관리자/구조대에게 `sos_alert` 메시지 push

### 2. `POST /api/peers/sos/{alert_id}/respond` — SOS 응답

**역할:** 근처 동료가 "도움 가겠다" 의사 표시

```
요청 (JWT 인증 필수):
{
  "message": "지금 갑니다"   // optional
}

응답 200:
{
  "alert_id": 7,
  "responder_id": 5,
  "sender_id": 3,
  "message": "지금 갑니다",
  "responded_at": "2026-08-11T10:30:00"
}
```

**로직:**
1. JWT에서 `responder_id` 추출
2. 해당 alert_id의 Alert 존재 + 미해결 상태 검증
3. DB에 응답 기록 (신규 모델 `SOSResponse` 추가 or Alert에 responder 필드 추가)
4. SOS 발신자에게 WebSocket `sos_responded` 메시지 push
5. 관리자/구조대에게도 알림

### 3. `GET /api/peers/nearby/{user_id}` — 근처 동료 조회

**역할:** 특정 유저 주변 동료 목록 조회 (관리자/구조대/본인 사용)

```
요청: GET /api/peers/nearby/3?radius=30.0

응답 200:
[
  {"user_id": 5, "x": 140.0, "y": 75.0, "distance": 11.2, "status": "evacuating"},
  {"user_id": 8, "x": 160.0, "y": 90.0, "distance": 14.1, "status": "in_building"}
]
```

**로직:**
1. user_id의 현재 위치 조회 (EvacuationStatus)
2. `services/peers.get_nearby_peers()` 호출
3. 거리순 정렬 반환

### 4. `GET /api/peers/sos/active` — 활성 SOS 목록

**역할:** 현재 미해결된 SOS 알림 목록

```
응답 200:
[
  {
    "alert_id": 7,
    "sender_id": 3,
    "floor_id": 2,
    "x": 150.0,
    "y": 80.0,
    "message": "다리를 다쳐서 이동 불가",
    "created_at": "2026-08-11T10:25:00",
    "responders": [5]
  }
]
```

**로직:**
1. Alert 테이블에서 `alert_type=SOS`, `is_resolved=False` 필터
2. 응답자 정보 포함하여 반환

---

## 구현 순서 (체크리스트)

### Step 1: 모델 보강

- [ ] `models/alert.py`에 `SOSResponse` 모델 추가

```python
class SOSResponse(Base):
    __tablename__ = "sos_responses"

    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(Integer, nullable=False)       # FK → alerts.id
    responder_id = Column(Integer, nullable=False)   # FK → users.id
    message = Column(Text)
    responded_at = Column(DateTime(timezone=True), server_default=func.now())
```

### Step 2: 서비스 보강

- [ ] `services/peers.py`에 `respond_to_sos()` 함수 추가
- [ ] `services/peers.py`에 `get_active_sos()` 함수 추가

```python
def respond_to_sos(alert_id: int, responder_id: int, message: str = None, db: Session = None) -> dict:
    """SOS 응답 기록"""
    alert = db.query(Alert).filter(Alert.id == alert_id, Alert.alert_type == AlertType.SOS, Alert.is_resolved == False).first()
    if not alert:
        return None

    response = SOSResponse(alert_id=alert_id, responder_id=responder_id, message=message)
    db.add(response)
    db.commit()
    db.refresh(response)

    return {
        "alert_id": alert_id,
        "responder_id": responder_id,
        "sender_id": alert.source_user_id,
        "message": message,
        "responded_at": str(response.responded_at),
    }


def get_active_sos(db: Session) -> list:
    """미해결 SOS 알림 목록 + 응답자 정보"""
    alerts = db.query(Alert).filter(Alert.alert_type == AlertType.SOS, Alert.is_resolved == False).all()
    result = []
    for a in alerts:
        responders = db.query(SOSResponse).filter(SOSResponse.alert_id == a.id).all()
        result.append({
            "alert_id": a.id,
            "sender_id": a.source_user_id,
            "floor_id": a.floor_id,
            "x": a.x,
            "y": a.y,
            "message": a.message,
            "created_at": str(a.created_at),
            "responders": [r.responder_id for r in responders],
        })
    return result
```

### Step 3: 라우터 구현

- [ ] `routers/peers.py` — 4개 엔드포인트 구현
- [ ] JWT 인증 적용 (`get_current_user` 의존성)
- [ ] sender_id는 body가 아닌 JWT에서 추출하도록 수정

### Step 4: WebSocket 연동

- [ ] `POST /api/peers/sos` 호출 시 → nearby 동료에게 `peer_sos` WebSocket push
- [ ] `POST /api/peers/sos/{alert_id}/respond` 호출 시 → 발신자에게 `sos_responded` push
- [ ] `websocket_manager.py`에 `send_to_floor_workers()` 메서드 추가 (같은 층 동료 대상)

```python
async def send_to_floor_workers(self, floor_id: int, exclude_user_id: int, message: dict):
    """같은 층 근로자에게만 메시지 전송 (SOS 발신자 제외)"""
    from app.models.database import SessionLocal
    from app.models.location import EvacuationStatus

    db = SessionLocal()
    try:
        floor_workers = db.query(EvacuationStatus).filter(
            EvacuationStatus.last_floor_id == floor_id,
            EvacuationStatus.user_id != exclude_user_id,
        ).all()
        target_ids = {w.user_id for w in floor_workers}
    finally:
        db.close()

    for uid in target_ids:
        if uid in self.worker_connections:
            ws = self.active_connections.get(uid)
            if ws:
                await ws.send_json(message)
```

### Step 5: 검증

- [ ] 근로자 A가 SOS 발송 → Alert DB 생성 확인
- [ ] 같은 층 근로자 B에게 WebSocket `peer_sos` 수신 확인
- [ ] 근로자 B가 respond → SOSResponse DB 생성 확인
- [ ] 근로자 A에게 WebSocket `sos_responded` 수신 확인
- [ ] 관리자/구조대에게 `sos_alert` 수신 확인
- [ ] `GET /api/peers/sos/active`에서 활성 SOS 목록 조회 확인

---

## WebSocket 메시지 규격

| 이벤트 | type | 수신 대상 | payload |
|---|---|---|---|
| SOS 발생 | `peer_sos` | 같은 층 worker | sender_id, floor_id, x, y, message, alert_id |
| SOS 발생 | `sos_alert` | admin, rescuer | sender_id, floor_id, x, y, message, alert_id |
| SOS 응답 | `sos_responded` | SOS 발신자 | responder_id, alert_id, message |
| SOS 응답 | `sos_response_update` | admin, rescuer | responder_id, alert_id, sender_id |

---

## 의존 관계

```
models/alert.py (SOSResponse 추가)
    ↓
services/peers.py (respond_to_sos, get_active_sos 추가)
    ↓
websocket_manager.py (send_to_floor_workers 추가)
    ↓
routers/peers.py (4개 엔드포인트 구현)
    ↓
검증 (Swagger + 2개 브라우저 탭 테스트)
```

---

## 스키마 변경 요약 (Pydantic)

```python
# routers/peers.py 내부

class SOSCreateRequest(BaseModel):
    floor_id: int
    x: float
    y: float
    message: Optional[str] = None

class SOSRespondRequest(BaseModel):
    message: Optional[str] = None

# 응답은 서비스가 반환하는 dict를 그대로 JSONResponse로 반환
```

기존 `SOSRequest`의 `sender_id` 필드 제거 — JWT에서 추출하는 것이 보안 원칙.

---

## 예상 소요

| 단계 | 예상 시간 |
|---|---|
| Step 1: 모델 보강 | 10분 |
| Step 2: 서비스 보강 | 20분 |
| Step 3: 라우터 구현 | 30분 |
| Step 4: WebSocket 연동 | 20분 |
| Step 5: 검증 | 20분 |
| **합계** | **~100분** |
