# PR #18 — GPS ↔ 도면 좌표 변환 레이어 구현

## 변경 사항

GPS 좌표(위도/경도)와 도면 좌표(px) 간 자동 변환 레이어를 구현하여 두 좌표계를 연결:
1. **FloorAnchor 모델** — 도면 위 기준점에 GPS 좌표를 매핑하는 앵커 포인트
2. **Affine Transform 서비스** — 2점 이상의 앵커로 선형 변환 행렬 계산 (numpy 기반)
3. **위치 업데이트 파이프라인 통합** — `POST /api/locations/update` 시 앵커가 등록된 층이면 GPS→도면 자동 변환 후 저장
4. **앵커 관리 API** — CRUD + 변환 테스트 엔드포인트

이로써 프론트엔드 GPS 수집 → 도면 위 위치 표시 → 탈출 경로 계산이 하나의 좌표계로 연동된다.

## 관련 이슈
- closes docs/issue/gps.md
- Plan: `docs/plan/1-upto.md` Phase 2-1 (위치 수집) 보강

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
| `app/services/coordinate.py` | GPS↔도면 변환 핵심 로직 — affine transform 계산, 변환 적용, 앵커 조회 |

### 수정 파일

| 파일 | 변경 내용 |
|------|-----------|
| `app/models/building.py` | `FloorAnchor` 모델 추가 (floor_id, px_x, px_y, gps_lat, gps_lng, label) |
| `app/routers/buildings.py` | 앵커 CRUD 엔드포인트 4개 + FloorAnchor import 추가 |
| `app/routers/locations.py` | `POST /update` 에서 `has_anchors()` → `gps_to_floor()` 변환 적용 |

---

## API Endpoints (신규)

### Anchors (`/api/buildings`)

| Method | Path | 설명 |
|--------|------|------|
| GET | `/floors/{floor_id}/anchors` | 층의 앵커 목록 조회 |
| POST | `/floors/{floor_id}/anchors` | 앵커 등록 (최소 2개 필요) |
| DELETE | `/anchors/{anchor_id}` | 앵커 삭제 |
| POST | `/floors/{floor_id}/convert/gps-to-floor?lat=&lng=` | GPS→도면 변환 테스트 |

### 기존 엔드포인트 (동작 변경)

| Method | Path | 변경 내용 |
|--------|------|-----------|
| POST | `/api/locations/update` | 앵커 등록 시 GPS→도면 자동 변환 후 저장 (미등록 시 기존 동작 유지) |

---

## Request / Response 예시

### POST /api/buildings/floors/1/anchors

```json
// Request
{
  "px_x": 0.0,
  "px_y": 0.0,
  "gps_lat": 37.4979,
  "gps_lng": 127.0276,
  "label": "출입구A"
}

// Response 201
{
  "id": 1,
  "floor_id": 1,
  "px_x": 0.0,
  "px_y": 0.0,
  "gps_lat": 37.4979,
  "gps_lng": 127.0276,
  "label": "출입구A"
}
```

### POST /api/buildings/floors/1/convert/gps-to-floor?lat=37.498&lng=127.028

```json
// Response 200
{
  "floor_id": 1,
  "px_x": 250.0,
  "px_y": 150.0
}
```

---

## Architecture

```
기존 흐름 (앵커 미등록)
  스마트폰 GPS → POST /locations/update(x=lng, y=lat) → DB 저장(GPS 원본)

변경 후 흐름 (앵커 2개 이상 등록)
  스마트폰 GPS → POST /locations/update(x=lng, y=lat)
    → has_anchors(floor_id) = True
    → gps_to_floor(lat=y, lng=x, floor_id)
      → FloorAnchor 조회 (2개 이상)
      → affine transform 계산
      → (px_x, px_y) 반환
    → DB 저장(도면 좌표) + WebSocket broadcast(도면 좌표)
```

### 변환 알고리즘

```
앵커 2개: 독립 축 스케일 + 이동 (회전 없음)
  scale_x = (dst_x1 - dst_x0) / (src_x1 - src_x0)
  tx = dst_x0 - scale_x * src_x0

앵커 3개 이상: least squares affine fit (회전 + 스케일 + 이동)
  [x'] = [a b tx] [x]
  [y']   [c d ty] [y]
                  [1]
  → numpy.linalg.lstsq로 최적 계수 추정
```

---

## DB Schema (추가)

### floor_anchors

| Column | Type | 설명 |
|--------|------|------|
| id | Integer PK | |
| floor_id | Integer | 대상 층 |
| px_x | Float | 도면 X 좌표 (px) |
| px_y | Float | 도면 Y 좌표 (px) |
| gps_lat | Float | GPS 위도 |
| gps_lng | Float | GPS 경도 |
| label | String | 기준점 이름 (선택) |

---

## 하위 호환성

- 앵커가 등록되지 않은 층: **기존과 동일하게 동작** (GPS 원본 그대로 저장)
- 앵커가 2개 미만인 층: 변환 건너뜀, GPS 원본 저장
- 기존 데이터: 영향 없음 (새 테이블 추가만, 기존 테이블 변경 없음)

---

## 테스트

서버 기동 및 라우트 등록 검증:

```
1. Import OK — 모듈 로드 성공
2. Health check → 200 OK
3. Anchor routes registered:
   - GET  /api/buildings/floors/{floor_id}/anchors           ✓
   - POST /api/buildings/floors/{floor_id}/anchors           ✓
   - DELETE /api/buildings/anchors/{anchor_id}               ✓
   - POST /api/buildings/floors/{floor_id}/convert/gps-to-floor ✓
```

### 수학적 검증

```
앵커1: GPS(127.000, 37.000) → 도면(0, 0)
앵커2: GPS(127.001, 37.001) → 도면(500, 300)

입력: GPS(127.0005, 37.0005) — 정확히 중간점
결과: 도면(250.0, 150.0) ← 기대값과 일치 ✓
```

### 수동 검증 시나리오

| # | 시나리오 | 검증 방법 |
|---|----------|-----------|
| 1 | 앵커 등록 | 2개 앵커 POST → 201 반환 |
| 2 | 변환 테스트 | `/convert/gps-to-floor?lat=37.0005&lng=127.0005` → 도면 중간점 |
| 3 | 위치 업데이트 (앵커 O) | POST /locations/update → DB에 도면 좌표 저장 확인 |
| 4 | 위치 업데이트 (앵커 X) | 앵커 없는 층 → DB에 GPS 원본 저장 확인 |
| 5 | 탈출 경로 연동 | 변환된 좌표로 /evacuation/route → 정상 경로 반환 |

---

## Known Limitations

- **2점 변환은 회전을 처리하지 못함** — 건물이 정북 방향이 아니면 3점 이상 앵커 필요
- **실내 GPS 정확도** — 건물 내부에서 GPS 신호가 약해지면 변환 결과도 부정확. BLE 비콘 등 실내 측위 기술 연동이 장기적으로 필요
- **앵커 등록은 수동** — 관리자가 현장에서 GPS 좌표를 측정하여 입력해야 함
- **numpy 의존성** — requirements.txt에 이미 포함 (1.26.4), 서버 사이즈에 영향 미미

---

## Related

- Issue: `docs/issue/gps.md`
- Plan: `docs/plan/1-upto.md` Phase 2-1
- 선행: PR #3 위치 수집 API, PR #6 의식불명 감지
- 연관: 프론트엔드 FloorPlan 렌더링 시 변환된 좌표로 마커 표시
