# PR #6 — 의식 불명 감지 시스템 구현 (Phase 3-2)

## 변경 사항

의식 불명(unconscious) 감지 시스템을 3가지 경로로 구현:
1. **타임아웃 자동 감지** — 위치 갱신이 30초 이상 없으면 백그라운드 루프가 자동으로 상태 전환
2. **심박 이상 즉시 감지** — 위치 업데이트 시 heart_rate < 40bpm이면 즉시 unconscious 전환
3. **Admin 데모 트리거** — 스마트워치 없이 시연 가능하도록 강제 전환 API 제공

모든 경로에서 상태 전환 → Alert 생성 (CRITICAL) → WebSocket broadcast (rescuer + admin) 파이프라인이 동일하게 동작한다.

## 관련 이슈
- closes #6
- Plan: `docs/plan/1-upto.md` Phase 3-2

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
| `app/services/unconscious_checker.py` | 백그라운드 asyncio 루프 — 10초 주기로 stale 유저 탐지 → unconscious 전환 → alert → broadcast |
| `app/routers/admin_simulate.py` | 데모용 Admin 트리거 3개 엔드포인트 |

### 수정 파일

| 파일 | 변경 내용 |
|------|-----------|
| `app/config.py` | `UNCONSCIOUS_TIMEOUT_SECONDS=30`, `UNCONSCIOUS_CHECK_INTERVAL=10`, `HEARTRATE_THRESHOLD_LOW=40` 추가 |
| `app/services/location.py` | `check_stale_locations()` 함수 추가 — timeout 초과 유저의 `is_moving=False` 전환 |
| `app/services/alert.py` | `create_unconscious_alert()` 함수 추가 — AlertType.UNCONSCIOUS, CRITICAL 레벨 |
| `app/routers/locations.py` | `POST /update` 에서 심박 이상 시 즉시 unconscious 감지 로직 추가 |
| `app/routers/__init__.py` | `admin_simulate_router` 등록 |
| `app/main.py` | `admin_simulate_router` include + startup 이벤트에서 `unconscious_check_loop()` 백그라운드 태스크 등록 |

---

## API Endpoints (신규)

### Admin Simulate (`/api/admin/simulate`)

| Method | Path | Auth | 설명 |
|--------|------|------|------|
| POST | `/unconscious/{user_id}` | - | 의식불명 강제 전환 |
| POST | `/fall/{user_id}` | - | 낙상 감지 트리거 |
| POST | `/heartrate/{user_id}?bpm=30` | - | 심박 이상 트리거 (bpm 지정 가능) |

### 기존 엔드포인트 (동작 확인)

| Method | Path | 변경 내용 |
|--------|------|-----------|
| POST | `/api/locations/update` | 심박 이상 감지 로직 추가 |
| GET | `/api/evacuation/unconscious` | unconscious 상태 유저 목록 (기존, 정상 동작) |

---

## Architecture

```
감지 경로 3가지
├── 1. 타임아웃 (자동)
│     unconscious_checker.py (10초 주기)
│       → check_stale_locations() → is_moving=False
│       → detect_unconscious() → status="unconscious"
│       → create_unconscious_alert() → broadcast
│
├── 2. 심박 이상 (위치 업데이트 시)
│     POST /api/locations/update
│       → heart_rate < 40 감지
│       → detect_unconscious() → 즉시 전환 → broadcast
│
└── 3. Admin 트리거 (데모용)
      POST /api/admin/simulate/{type}/{user_id}
        → 즉시 상태 전환 → alert → broadcast
```

**WebSocket 메시지 포맷:**
```json
{
  "type": "unconscious_detected",
  "user_id": 3,
  "floor_id": 1,
  "x": 120.5,
  "y": 45.2,
  "reason": "timeout | fall_detected | abnormal_heartrate | admin_trigger"
}
```

---

## 설정값 (config.py)

| 설정 | 기본값 | 설명 |
|------|--------|------|
| `UNCONSCIOUS_TIMEOUT_SECONDS` | 30 | 위치 갱신 없음 → 의식불명 판정 기준 (초) |
| `UNCONSCIOUS_CHECK_INTERVAL` | 10 | 백그라운드 체크 주기 (초) |
| `HEARTRATE_THRESHOLD_LOW` | 40 | 심박 이상 하한선 (bpm) |

`.env`에서 오버라이드 가능.

---

## 테스트

TestClient로 서버 기동 및 라우트 등록 검증:

```
1. Health check                          → 200 OK
2. Simulate routes registered:
   - /api/admin/simulate/unconscious/{user_id}  ✓
   - /api/admin/simulate/fall/{user_id}         ✓
   - /api/admin/simulate/heartrate/{user_id}    ✓
```

### 수동 검증 시나리오

| # | 시나리오 | 검증 방법 |
|---|----------|-----------|
| 1 | 타임아웃 자동 감지 | 유저 위치 업데이트 후 30초 대기 → `GET /api/evacuation/unconscious`에서 확인 |
| 2 | Admin unconscious 트리거 | `POST /api/admin/simulate/unconscious/3` → 200 + broadcast 수신 |
| 3 | Admin fall 트리거 | `POST /api/admin/simulate/fall/3` → 200 + broadcast 수신 |
| 4 | Admin heartrate 트리거 | `POST /api/admin/simulate/heartrate/3?bpm=25` → 200 + broadcast 수신 |
| 5 | 심박 이상 즉시 감지 | `POST /api/locations/update` (heart_rate=35) → unconscious 전환 확인 |

---

## Known Limitations

- Admin simulate API에 인증/권한 체크 미적용 (데모 편의상 열어둠 — 프로덕션에서는 `require_role("admin")` 추가 필요)
- `is_moving=False` 전환은 백그라운드 체커에 의존 → 서버 재시작 시 체커가 다시 시작될 때까지 최대 10초 공백
- SQLite 환경에서 백그라운드 태스크와 API 동시 DB 접근 시 lock 가능성 (소규모 데모에서는 문제 없음)

---

## Related

- Plan: `docs/plan/1-upto.md` Phase 3-2
- 선행: PR #3 위치 수집 API
- 다음 작업: Phase 4-1 동료 SOS (`routers/peers.py` 구현)
