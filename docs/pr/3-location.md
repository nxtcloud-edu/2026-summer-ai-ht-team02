# PR #3 — 위치 수집 API (스마트폰 기반) 구현

## Summary

스마트폰 GPS 기반 실시간 위치 수집 파이프라인을 end-to-end로 구현.
JWT 인증 → 위치 POST → DB 저장 → WebSocket 브로드캐스트 → 프론트엔드 Geolocation 훅까지 전체 흐름이 동작한다.

---

## Changes

### Backend — 신규 파일

| 파일 | 설명 |
|---|---|
| `app/dependencies.py` | JWT 토큰 검증, `get_current_user` 의존성, `require_role` 팩토리 |
| `app/websocket_manager.py` | ConnectionManager를 별도 모듈로 분리 (라우터에서 import 가능) |

### Backend — 수정 파일

| 파일 | 변경 내용 |
|---|---|
| `app/routers/auth.py` | register, login, me, workers 전체 구현. bcrypt 직접 사용 (passlib 미사용) |
| `app/routers/locations.py` | 5개 엔드포인트 구현 — update, current, current/{id}, floor/{id}, history/{id} |
| `app/services/location.py` | `get_user_current_location`, `get_all_current_locations`, `get_location_history` 추가 |
| `app/main.py` | ConnectionManager를 `websocket_manager.py`에서 import하도록 리팩토링 |

### Frontend — 신규 파일

| 파일 | 설명 |
|---|---|
| `src/hooks/useApi.ts` | axios 인스턴스 + JWT 인터셉터 + login/register/logout 헬퍼 |
| `src/hooks/useGeolocation.ts` | GPS watchPosition + 5초 주기 서버 POST 훅 |

### Steering 문서

| 파일 | 설명 |
|---|---|
| `.kiro/steering/backend-conventions.md` | 신규 — 백엔드 기술 주의사항 (fileMatch 조건부 포함) |
| `.kiro/steering/implementation-guide.md` | 구현 상태 현행화 |
| `.kiro/steering/project-context.md` | Common Gotchas 보강 |

---

## Architecture Decisions

1. **REST가 저장 정본, WebSocket은 브로드캐스트 전용**
   - `POST /api/locations/update` → DB 저장 + WebSocket push
   - WebSocket `location_update` 메시지는 relay만 (DB 저장 안 함)

2. **user_id는 JWT에서 추출 (request body 아님)**
   - 클라이언트가 user_id를 위조할 수 없도록 보안 강화

3. **passlib 제거 → bcrypt 직접 사용**
   - bcrypt 5.0과 passlib 비호환 문제 회피
   - `bcrypt.hashpw()` / `bcrypt.checkpw()` 직접 호출

4. **ConnectionManager 모듈 분리**
   - `main.py`에 있으면 circular import 위험
   - `websocket_manager.py` 싱글톤으로 라우터에서 자유롭게 import

---

## API Endpoints (구현 완료)

### Auth (`/api/auth`)
| Method | Path | Auth | 설명 |
|---|---|---|---|
| POST | `/register` | - | 회원가입 → JWT 발급 |
| POST | `/login` | - | 로그인 → JWT 발급 |
| GET | `/me` | Bearer | 현재 사용자 정보 |
| GET | `/workers` | Admin/Rescuer | 전체 근로자 목록 |

### Locations (`/api/locations`)
| Method | Path | Auth | 설명 |
|---|---|---|---|
| POST | `/update` | Bearer | 위치 갱신 (5초 주기) |
| GET | `/current` | Admin/Rescuer | 전체 재실자 현재 위치 |
| GET | `/current/{user_id}` | Bearer (본인+Admin/Rescuer) | 특정 근로자 위치 |
| GET | `/floor/{floor_id}` | Admin/Rescuer | 층별 재실자 목록 |
| GET | `/history/{user_id}` | Bearer (본인+Admin/Rescuer) | 위치 이력 |

---

## Testing

TestClient로 전체 플로우 검증 완료:

```
1. Health check          → 200 OK
2. Register (worker)     → 200 + JWT 발급
3. Login                 → 200 + JWT 발급
4. GET /auth/me          → 200 + 유저 정보
5. POST /locations/update → 200 + 위치 저장
6. GET /locations/current/1 → 200 + 현재 위치
7. POST /locations/update (2차) → 200 + 이동 반영
8. GET /locations/history/1 → 200 + 이력 2건
9. GET /locations/floor/1 (admin) → 200 + 재실자 목록
10. GET /locations/current (admin) → 200 + 전체 현위치
```

---

## Known Limitations

- GPS→도면 좌표 변환 미구현 (현재 GPS 위경도를 그대로 x/y로 저장)
- 타임아웃 기반 의식불명 자동 전환 스케줄러 미구현 (서비스 함수는 있으나 주기 호출 없음)
- SQLite 동시 쓰기 제약 — 20명 이상 동시 위치 갱신 시 PostgreSQL 전환 필요

---

## Related

- Plan: `docs/plan/1-upto.md` Phase 2-1
- 다음 작업: Phase 2-2 화재 알림 시스템 (`routers/alerts.py` 구현)
