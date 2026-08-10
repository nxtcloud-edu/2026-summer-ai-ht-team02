# PR #7 — 동료 간 SOS 시스템 구현 (Phase 4-1)

## 변경 사항

위기 상황에서 근로자가 동료에게 도움을 요청하고, 근처 동료가 응답할 수 있는 SOS 기능 구현:
1. **SOS 발송** — 근로자가 위치 + 메시지를 포함하여 SOS 발신 → 같은 층 동료 + 관리자/구조대에 실시간 push
2. **SOS 응답** — 근처 동료가 "도움 가겠다" 의사 표시 → 발신자에게 실시간 알림
3. **근처 동료 조회** — 반경 기반으로 같은 층 근로자 목록 제공
4. **활성 SOS 목록** — 미해결 SOS 현황 + 응답자 정보 조회

모든 REST 엔드포인트는 JWT 인증 필수이며, sender/responder ID는 토큰에서 추출(보안). WebSocket push는 브로드캐스트 전용 원칙 유지.

## 관련 이슈
- closes #7
- Plan: `docs/plan/1-upto.md` Phase 4-1

## 변경 유형
- [x] 새 기능
- [ ] 버그 수정
- [ ] 리팩토링
- [ ] 기타:

---

## Changes

### 신규 파일

| 파일 | 설명 |
|------|------|
| `app/models/alert.py` (추가) | `SOSResponse` 모델 — SOS 응답 기록 테이블 |

### 수정 파일

| 파일 | 변경 내용 |
|------|-----------|
| `app/models/alert.py` | `SOSResponse` 모델 추가, `ForeignKey` import 추가 |
| `app/services/peers.py` | `respond_to_sos()`, `get_active_sos()` 함수 추가 + Alert/SOSResponse import |
| `app/websocket_manager.py` | `send_to_floor_workers()` 메서드 추가 — 같은 층 근로자 대상 push (발신자 제외) |
| `app/routers/peers.py` | 4개 엔드포인트 전면 구현 (JWT 인증 + WebSocket 연동) |

---

## API Endpoints

### Peers (`/api/peers`)

| Method | Path | Auth | 설명 |
|--------|------|------|------|
| POST | `/sos` | JWT (worker) | SOS 발송 — 같은 층 동료 + admin/rescuer에 push |
| POST | `/sos/{alert_id}/respond` | JWT (worker) | SOS 응답 — 발신자에게 push |
| GET | `/nearby/{user_id}?radius=30` | JWT | 반경 내 동료 목록 |
| GET | `/sos/active` | JWT | 현재 활성 SOS 목록 + 응답자 정보 |

---

## Request / Response 예시

### POST /api/peers/sos

```json
// Request (JWT 필수, sender_id는 토큰에서 추출)
{
  "floor_id": 2,
  "x": 150.0,
  "y": 80.0,
  "message": "다리를 다쳐서 이동 불가"
}

// Response 201
{
  "alert_id": 7,
  "type": "sos",
  "sender_id": 3,
  "floor_id": 2,
  "x": 150.0,
  "y": 80.0,
  "message": "다리를 다쳐서 이동 불가",
  "nearby_peers": [
    {"user_id": 5, "x": 140.0, "y": 75.0, "distance": 11.2, "status": "evacuating"}
  ]
}
```

### POST /api/peers/sos/{alert_id}/respond

```json
// Request (JWT 필수, responder_id는 토큰에서 추출)
{
  "message": "지금 갑니다"
}

// Response 200
{
  "alert_id": 7,
  "responder_id": 5,
  "sender_id": 3,
  "message": "지금 갑니다",
  "responded_at": "2026-08-11T10:30:00"
}
```

### GET /api/peers/nearby/3?radius=30

```json
// Response 200
[
  {"user_id": 5, "x": 140.0, "y": 75.0, "distance": 11.2, "status": "evacuating"},
  {"user_id": 8, "x": 160.0, "y": 90.0, "distance": 14.1, "status": "in_building"}
]
```

### GET /api/peers/sos/active

```json
// Response 200
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

---

## Architecture

```
SOS 흐름
├── 1. SOS 발송
│     POST /api/peers/sos (JWT → sender_id)
│       → services/peers.send_sos()
│         → create_sos_alert() → DB 저장
│         → EvacuationStatus.sos_sent = True
│         → get_nearby_peers() → 반경 내 동료 목록
│       → manager.send_to_floor_workers() → 같은 층 동료에게 peer_sos push
│       → manager.broadcast_to_admins/rescuers() → sos_alert push
│
├── 2. SOS 응답
│     POST /api/peers/sos/{alert_id}/respond (JWT → responder_id)
│       → services/peers.respond_to_sos()
│         → SOSResponse DB 저장 (중복 방지)
│       → manager.send_to_user(sender) → sos_responded push
│       → manager.broadcast_to_admins/rescuers() → sos_response_update push
│
├── 3. 근처 동료 조회
│     GET /api/peers/nearby/{user_id}
│       → EvacuationStatus에서 현재 위치 조회
│       → services/peers.get_nearby_peers() → 거리 계산 + 정렬
│
└── 4. 활성 SOS 목록
      GET /api/peers/sos/active
        → services/peers.get_active_sos()
          → Alert(type=SOS, is_resolved=False) + SOSResponse join
```

---

## WebSocket 메시지 규격

| 이벤트 | type | 수신 대상 | payload |
|--------|------|-----------|---------|
| SOS 발생 | `peer_sos` | 같은 층 worker (발신자 제외) | alert_id, sender_id, sender_name, floor_id, x, y, message |
| SOS 발생 | `sos_alert` | admin, rescuer | alert_id, sender_id, sender_name, floor_id, x, y, message |
| SOS 응답 | `sos_responded` | SOS 발신자 | alert_id, responder_id, responder_name, message |
| SOS 응답 | `sos_response_update` | admin, rescuer | alert_id, responder_id, responder_name, sender_id |

---

## DB Schema (추가)

### sos_responses

| Column | Type | 설명 |
|--------|------|------|
| id | Integer PK | |
| alert_id | Integer FK(alerts.id) | 응답 대상 SOS 알림 |
| responder_id | Integer FK(users.id) | 응답한 유저 |
| message | Text | 응답 메시지 (선택) |
| responded_at | DateTime | 응답 시각 |

---

## 테스트

서버 기동 및 라우트 등록 검증:

```
1. Health check                              → 200 OK
2. Peers routes registered:
   - POST /api/peers/sos                     ✓
   - POST /api/peers/sos/{alert_id}/respond  ✓
   - GET  /api/peers/nearby/{user_id}        ✓
   - GET  /api/peers/sos/active              ✓
```

### 수동 검증 시나리오

| # | 시나리오 | 검증 방법 |
|---|----------|-----------|
| 1 | SOS 발송 | Worker A 로그인 → `POST /api/peers/sos` → 201 + alert_id 반환 |
| 2 | 동료 수신 | Worker B WebSocket 연결 → `peer_sos` 메시지 수신 확인 |
| 3 | SOS 응답 | Worker B → `POST /api/peers/sos/7/respond` → 200 |
| 4 | 발신자 알림 | Worker A WebSocket → `sos_responded` 메시지 수신 확인 |
| 5 | 중복 응답 방지 | Worker B 재응답 → 404 반환 |
| 6 | 활성 SOS 목록 | `GET /api/peers/sos/active` → responders 배열에 B 포함 |
| 7 | 근처 동료 조회 | `GET /api/peers/nearby/3?radius=50` → 반경 내 동료 목록 |

---

## Known Limitations

- `send_to_floor_workers()`에서 DB 세션을 별도 생성하여 같은 층 유저를 조회 — 대규모 트래픽에서는 캐시 레이어 추가 권장
- SOS 해제(resolve) 기능은 기존 `services/alert.resolve_alert()` 활용 가능하나, 별도 peers 엔드포인트는 미구현 (필요 시 추가)
- 역할별 접근 제어(`require_role`)는 `/sos/active`, `/nearby` 엔드포인트에 미적용 — 모든 인증된 유저가 조회 가능 (Phase 5에서 분기 예정)

---

## Related

- Plan: `docs/plan/1-upto.md` Phase 4-1
- 선행: PR #6 의식 불명 감지
- 다음 작업: Phase 4-2 프론트엔드 API 연동 + Phase 4-3 도면 Canvas 렌더링
