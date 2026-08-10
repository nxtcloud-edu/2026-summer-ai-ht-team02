# 구현 계획 — FireEscape AI

## 현재 상태 요약

Phase 1 인증 + Phase 2 위치 수집 + Phase 3 경로 계산/의식불명 감지 구현 완료. JWT 인증, 위치 5개 API, 탈출 경로 A*, 의식불명 자동 감지(타임아웃+심박) + Admin 시뮬레이션 API, WebSocket 연동, 프론트엔드 GPS 훅이 동작한다.

---

## 이벤트 발행 정책 (디바이스 전제)

| 기능 | 실제 소스 | 데모 방식 |
|---|---|---|
| 위치 추적 | 스마트폰 GPS → 앱이 서버로 주기적 POST | 실제 동작 (Geolocation API) |
| 심박수 이상 | 스마트워치 (없음) | 서버 Admin API로 특정 유저 상태 강제 전환 |
| 낙상 감지 | 스마트워치 (없음) | 서버 Admin API 트리거 |
| 화재 감지 | IoT 센서 (없음) | Admin이 화재 알림 API 호출 |

**원칙:**
- 스마트폰 위치 추적은 실제로 동작 — 코어 로직(경로 계산, 실시간 추적) 검증 가능
- 스마트워치/IoT 기능은 "데모 시연용 Admin 트리거 API"로 대체 — 시나리오 제어 용이
- 타임아웃 기반 의식불명 감지(위치 업데이트가 N초 없으면 자동 전환)는 유지

---

## Phase 1 — 인증 및 기본 CRUD (Week 1)

### 1-1. JWT 인증 구현

- [x] `services/auth.py` 생성 — 비밀번호 해싱, 토큰 발급/검증
- [x] `routers/auth.py` 내부 구현 — register, login, me
- [x] `dependencies.py` — `get_current_user` 의존성 (토큰 → User 변환)
- [x] 역할별 접근 제어 데코레이터 (`require_role("admin")`)

검증: `/api/auth/register` → `/api/auth/login` → `/api/auth/me` 동작 확인 ✅

### 1-2. 건물/도면 CRUD

- [ ] `routers/buildings.py` 내부 구현 — 건물/층 생성/조회
- [ ] 도면 이미지 업로드 (로컬 `uploads/` 저장)
- [ ] 노드/엣지 CRUD 구현
- [ ] 엣지 차단/해제 API 구현

검증: 건물 생성 → 층 추가 → 도면 업로드 → 노드 5개 + 엣지 연결 → `/docs`에서 확인

---

## Phase 2 — 위치 추적 및 화재 알림 (Week 2)

### 2-1. 위치 수집 API (스마트폰 기반)

- [x] `routers/locations.py` 내부 구현 — update, current, floor별
- [x] 서비스 연결 (`services/location.py`는 이미 구현됨)
- [x] 위치 이력 조회 API 연결
- [x] 스마트폰 위치 수집 간격 정의 (5초마다 POST)
- [x] 프론트엔드 모바일 웹에서 Geolocation API 호출 → 서버 POST 로직

검증: 스마트폰 브라우저에서 위치 갱신 → GET으로 현재 위치 확인 → 층별 재실자 목록 ✅

### 2-2. 화재 알림 시스템

- [ ] `routers/alerts.py` 내부 구현 — fire, active, resolve
- [ ] 서비스 연결 (`services/alert.py`는 이미 구현됨)
- [ ] 화재 발생 시 해당 반경 엣지 자동 차단 확인
- [ ] 알림 해제 시 엣지 복구 확인

검증: 화재 알림 발생 → 엣지 차단 확인 → 알림 해제 → 엣지 복구 확인

### 2-3. WebSocket 실시간 연동

- [ ] 화재 알림 시 전체 broadcast 동작 확인
- [x] 위치 업데이트 시 admin/rescuer에게 push 확인
- [ ] 프론트엔드 WebSocket 연결 훅 (`hooks/useWebSocket.ts`)

검증: 2개 브라우저 탭 — 한쪽에서 화재 발생 → 다른 쪽에서 알림 수신

---

## Phase 3 — 탈출 경로 계산 (Week 3)

### 3-1. 경로 API 연결

- [x] `routers/evacuation.py` 내부 구현 — route, status, unconscious
- [x] 서비스 연결 (`services/evacuation.py`는 이미 구현됨)
- [x] 구조대 진입 경로 API 연결 (`rescuer-route`)
- [x] 대피 상태 업데이트 API 구현

검증: 노드/엣지 데이터 있는 상태에서 → 경로 요청 → 최단 경로 응답 확인 → 엣지 차단 후 우회 경로 확인

### 3-2. 의식 불명 감지

- [x] 위치 업데이트 타임아웃 체크 로직 연동 (N초간 위치 갱신 없으면 자동 전환)
- [x] 미대피자 목록 API 동작 확인
- [x] **데모 시연용 Admin 트리거 API 구현:**
  - `POST /api/admin/simulate/unconscious/{user_id}` — 의식불명 강제 전환
  - `POST /api/admin/simulate/fall/{user_id}` — 낙상 감지 트리거
  - `POST /api/admin/simulate/heartrate/{user_id}` — 심박 이상 트리거
- [x] Admin 트리거 시 WebSocket broadcast → 구조대 뷰 반영

검증: Admin API로 unconscious 트리거 → 구조대 뷰에 해당 유저 표시 → 타임아웃 기반도 별도 검증 ✅

---

## Phase 4 — 동료 SOS 및 프론트엔드 (Week 4)

### 4-1. 동료 간 SOS

- [ ] `routers/peers.py` 내부 구현 — sos, respond, nearby, active
- [ ] 서비스 연결 (`services/peers.py`는 이미 구현됨)
- [ ] WebSocket SOS 메시지 동료에게 전파 확인

검증: 근로자 A가 SOS → 같은 층 근로자 B에게 수신 → B가 respond

### 4-2. 프론트엔드 API 연동

- [x] `hooks/useApi.ts` — axios 인스턴스 + 인터셉터 (JWT)
- [ ] `hooks/useWebSocket.ts` — 연결/재연결/메시지 핸들링
- [ ] Dashboard: 상태 카드 숫자 실데이터 연결
- [ ] Dashboard: 실시간 알림 피드 WebSocket 연동

검증: 로그인 → 대시보드에 실제 데이터 표시 → 화재 발생 시 알림 피드 업데이트

### 4-3. 도면 Canvas 렌더링

- [ ] `components/FloorCanvas.tsx` — SVG 기반 도면 렌더링
- [ ] 도면 이미지 배경 위에 노드/엣지 오버레이
- [ ] 근로자 위치 마커 (실시간 업데이트)
- [ ] 경로 하이라이트 (탈출 경로 표시)
- [ ] 화재 구역 표시 (빨간 영역)

검증: FloorPlan 페이지에서 도면 + 노드/엣지 시각 확인 → Evacuation 페이지에서   경로 표시

---

## Phase 5 — 통합 및 시나리오 테스트 (Week 5)

### 5-1. 전체 시나리오 테스트

- [ ] 시나리오: 화재 발생(Admin 트리거) → 근로자 알림 수신 → 경로 안내 → 대피 완료
- [ ] 시나리오: 의식 불명(Admin 트리거) → 구조대 뷰에 위치 표시 → 진입 경로 제공
- [ ] 시나리오: 타임아웃 기반 의식불명 자동 감지 → 구조대 뷰 반영
- [ ] 시나리오: 동료 SOS → 주변 동료 수신 → 응답 → 도움

### 5-2. 역할별 UI 분기

- [ ] Worker: 탈출 경로 + SOS 버튼만 표시
- [ ] Admin: 전체 대시보드 + 도면 관리
- [ ] Rescuer: 미대피자 목록 + 진입 경로

### 5-3. 마무리

- [ ] 데모용 시드 데이터 스크립트 (`scripts/seed.py`)
- [ ] Docker Compose (backend + frontend)
- [ ] README 최종 업데이트

---

## 의존 관계

```
Phase 1 (인증 + CRUD)
    ↓
Phase 2 (위치 + 알림 + WebSocket)
    ↓
Phase 3 (경로 계산 + 의식불명)
    ↓
Phase 4 (SOS + 프론트엔드 연동)
    ↓
Phase 5 (통합 테스트 + 배포)
```

각 Phase는 이전 Phase에 의존. Phase 1이 끝나야 Phase 2 API를 인증 적용해서 테스트 가능.

---

## 예상 일정

| Phase | 기간 | 핵심 산출물 |
|---|---|---|
| 1 | Week 1 | 로그인 동작 + 건물/도면 데이터 입력 가능 |
| 2 | Week 2 | 위치 추적 + 화재 알림 + 실시간 push |
| 3 | Week 3 | 탈출 경로 계산 동작 + 의식불명 감지 |
| 4 | Week 4 | SOS + 프론트엔드 실데이터 연동 + 도면 시각화 |
| 5 | Week 5 | 전체 시나리오 동작 + 데모 준비 |
