# PR #18 — 프론트엔드 버그 수정 + GPS 좌표 변환 + 데모 시드 구성

## 변경 사항

프론트엔드 인증 흐름, 도면 렌더링, 탈출 경로 표시 관련 버그를 수정하고, GPS↔도면 좌표 변환 레이어 및 데모용 시드 데이터를 추가:

1. **로그인 페이지 추가 + 인증 흐름 수정** — 401 시 빈 화면 문제 해결
2. **로그인 후 화면 전환 안 되는 문제** — React 상태 기반 인증으로 변경
3. **도면 이미지 렌더링 수정** — 백엔드 URL 프리픽스 + 대시보드 건물 현황 구현
4. **탈출 경로/내 위치 미표시 수정** — viewBox 좌표계 스케일링 + 유저 위치 자동 로드
5. **GPS↔도면 좌표 변환** — FloorAnchor 모델 + affine transform 서비스 + 위치 파이프라인 적용
6. **데모용 시드 스크립트** — 실제 도면 기반 4층 건물 데이터 자동 등록

## 관련 이슈
- closes docs/issue/gps.md
- Plan: `docs/plan/1-upto.md` Phase 4-2, 4-3

## 변경 유형
- [x] 새 기능
- [x] 버그 수정
- [ ] 리팩토링
- [ ] 기타:

---

## Changes

### 신규 파일

| 파일 | 설명 |
|------|------|
| `backend/app/services/coordinate.py` | GPS↔도면 좌표 affine transform 변환 서비스 |
| `backend/scripts/seed.py` | 데모용 시드 스크립트 (4층 건물, 노드/엣지/앵커/유저) |
| `backend/uploads/floor_1_demo.svg` | 데모 도면 SVG (시드용, 교체 예정) |
| `frontend/src/pages/Login.tsx` | 로그인 페이지 (데모 계정 안내 포함) |

### 수정 파일

| 파일 | 변경 내용 |
|------|-----------|
| `backend/app/models/building.py` | `FloorAnchor` 모델 추가 |
| `backend/app/routers/buildings.py` | 앵커 CRUD 4개 + GPS→도면 변환 테스트 API |
| `backend/app/routers/locations.py` | `POST /update` 시 GPS→도면 자동 변환 적용 |
| `frontend/src/App.tsx` | 상태 기반 인증 + 로그인/로그아웃 흐름 재구성 |
| `frontend/src/pages/Login.tsx` | `onLoginSuccess` 콜백 방식으로 화면 전환 |
| `frontend/src/hooks/useApi.ts` | 401 인터셉터 무한 리다이렉트 방지 |
| `frontend/src/pages/Dashboard.tsx` | "건물 현황" 플레이스홀더 → 실제 도면+층탭 컴포넌트 |
| `frontend/src/components/FloorCanvas.tsx` | 이미지 URL 프리픽스 + viewBox 스케일 대응 |
| `frontend/src/pages/Evacuation.tsx` | 유저 위치 서버에서 로드 + viewBox 30000x12800 + 폴백 |

---

## 버그 수정 상세

### Bug 1: 도면관리 탭 이동 시 화면 사라짐

**원인:** API 호출 시 JWT 없으면 401 → `window.location.href = "/login"` → `/login` 라우트 미존재 → 빈 화면

**수정:** Login 페이지 생성, App.tsx에 라우트 추가, 401 인터셉터에서 이미 /login이면 중복 리다이렉트 방지

### Bug 2: 로그인 성공 후 대시보드로 안 넘어감

**원인:** `getStoredAuth()`는 초기 렌더링 시점 값만 읽음. localStorage 업데이트 후에도 App 리렌더링 안 됨

**수정:** `useState(isAuthenticated)` + `onLoginSuccess` 콜백으로 상태 즉시 갱신 → 리렌더링 → 라우팅

### Bug 3: 도면 이미지가 깨진 아이콘으로 표시

**원인:** DB에 `/uploads/floor_1f_plan.png`(상대 경로)로 저장 → 프론트(5173)에서 요청 시 백엔드(8000)가 아닌 자기 서버로 향함

**수정:** FloorCanvas에서 `http://localhost:8000` 프리픽스 자동 추가

### Bug 4: 탈출 경로 404 + 내 위치 미표시

**원인:**
- `floorId` 하드코딩(1) — 실제 1F ID는 2 (B1F가 먼저 생성돼서)
- `currentPos` 하드코딩({x:100, y:100}) — mm 좌표계에서 의미 없는 값
- viewBox 800x600 vs 노드 좌표 30000x12800 — 스케일 불일치

**수정:**
- 유저 위치를 `GET /api/locations/current/{user_id}`에서 로드
- 위치 없으면 첫 번째 건물 1F로 폴백
- viewBox를 실제 도면 크기(30000x12800)로 설정
- 노드/마커/선 두께를 viewBox 비율에 맞게 스케일링

---

## GPS 좌표 변환 (신규 기능)

### 동작 흐름

```
앵커 미등록 시: GPS 원본 그대로 저장 (하위호환)
앵커 2개 이상 등록 시:
  POST /locations/update(x=lng, y=lat)
    → has_anchors(floor_id) = True
    → gps_to_floor(lat, lng, floor_id) → affine transform
    → DB 저장(도면 좌표) + WebSocket broadcast(도면 좌표)
```

### API

| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/buildings/floors/{id}/anchors` | 앵커 목록 |
| POST | `/api/buildings/floors/{id}/anchors` | 앵커 등록 |
| DELETE | `/api/buildings/anchors/{id}` | 앵커 삭제 |
| POST | `/api/buildings/floors/{id}/convert/gps-to-floor?lat=&lng=` | 변환 테스트 |

---

## 데모 시드 스크립트

실행: `cd backend && .\venv\Scripts\python.exe scripts\seed.py`

등록 내용:
- 건물: FireEscape 교육센터 (4층: B1F~3F)
- 1F: 23노드, 28엣지 (로비, 강의실, 식당, 관리사무실, 계단, 출구)
- 2F/3F: 각 9노드, 9~12엣지
- 층간 계단 엣지 6개
- GPS 앵커 2개 (1F)
- 유저 7명 (admin 1, rescuer 1, worker 5)
- 초기 위치 5명 (worker만)

로그인: 모든 계정 비밀번호 `demo1234`

---

## 테스트

### 검증 완료

| 항목 | 결과 |
|------|------|
| 시드 실행 | ✅ DB 초기화 + 전체 데이터 등록 |
| 1F 경로 계산 (강의실→후문) | ✅ 16.8m, 5개 노드 |
| 2F 경로 계산 (교육실→비상계단) | ✅ 27.7m, 6개 노드 |
| GPS→도면 변환 | ✅ (37.4975, 127.0277) → (15000, 6400) |
| 로그인 → 대시보드 전환 | ✅ |
| TypeScript 빌드 | ✅ 에러 0 |
| Vite 프로덕션 빌드 | ✅ |

### 수동 검증 시나리오

| # | 시나리오 | 방법 |
|---|----------|------|
| 1 | 로그인 | admin@fire.io / demo1234 → 대시보드 표시 |
| 2 | 도면관리 탭 | 층 선택 → 노드/엣지 표시 |
| 3 | 탈출 경로 | worker1으로 로그인 → 경로 자동 계산 + 내 위치 마커 |
| 4 | 화재 시나리오 | Swagger에서 POST /api/alerts/fire → 경로 우회 재계산 |
| 5 | 건물 현황 | 대시보드 → 층 탭 전환 → 도면 표시 |

---

## Known Limitations

- 도면 이미지 URL에 `localhost:8000` 하드코딩 — 프로덕션 배포 시 환경변수로 교체 필요
- admin 계정은 위치 데이터 없어서 탈출 경로 페이지에서 "내 위치" 미표시 (의도된 동작)
- 도면 이미지 파일(`floor_1f_plan.png`)은 사용자가 직접 `backend/uploads/`에 배치해야 함
- React Router v7 deprecation warning — 기능 무관, 추후 마이그레이션 시 처리

---

## Related

- Issue: `docs/issue/gps.md`
- Plan: `docs/plan/1-upto.md` Phase 4-2, 4-3
- 선행: PR #7 동료 SOS, PR #6 의식불명 감지
- 다음 작업: Phase 5 통합 시나리오 테스트 + 도면 편집 UI
