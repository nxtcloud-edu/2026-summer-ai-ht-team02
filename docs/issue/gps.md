# Issue: GPS 좌표 → 도면 좌표 변환 레이어 구현

## 문제 요약

현재 프론트엔드에서 수집하는 위치 데이터(GPS 위도/경도)와 도면 기반 경로 계산 시스템(FloorNode px 좌표)의 좌표계가 다르다. 두 시스템이 연동되지 않아 GPS로 수집한 실제 위치를 도면 위에 표시하거나 탈출 경로를 계산하는 것이 불가능한 상태.

## 현재 상황

```
프론트엔드 (useGeolocation.ts)
  x = longitude (예: 127.0276)
  y = latitude  (예: 37.4979)
        ↓ POST /api/locations/update
서버 DB 저장 (EvacuationStatus)
  last_x = 127.0276 (경도)
  last_y = 37.4979  (위도)

도면 시스템 (FloorNode)
  x = 250.0 (도면 px)
  y = 180.0 (도면 px)
```

- `services/evacuation.py`의 `find_nearest_node()`는 유클리드 거리 기반으로 가장 가까운 노드를 찾는데, GPS 좌표(127, 37)와 도면 좌표(250, 180)를 직접 비교하면 의미 없는 결과가 나옴
- `services/peers.py`의 `get_nearby_peers()`도 동일한 문제 — 유저 간 거리 계산이 좌표계 불일치로 부정확

## 영향 범위

| 기능 | 영향 |
|---|---|
| 탈출 경로 계산 (`calculate_evacuation_route`) | GPS 위치에서 가장 가까운 노드 매칭 불가 |
| 구조대 진입 경로 (`calculate_rescuer_route`) | 구조대 위치 → 대상자 위치 경로 계산 불가 |
| 도면 위 근로자 위치 표시 (FloorPlan 페이지) | GPS 좌표를 도면 위에 렌더링 불가 |
| 근처 동료 검색 (`get_nearby_peers`) | 거리 계산 부정확 |
| 화재 반경 엣지 차단 (`_block_nearby_edges`) | 화재 좌표와 노드 좌표 비교 시 좌표계 혼재 가능 |

## 해결 방안

### Option A: 도면에 기준점(anchor) 등록 → 선형 변환

도면 위 최소 2개 기준점의 GPS 좌표를 등록하고, 선형 보간(affine transform)으로 변환.

```python
# Floor 모델에 추가
class FloorAnchor(Base):
    __tablename__ = "floor_anchors"
    id = Column(Integer, primary_key=True)
    floor_id = Column(Integer, nullable=False)
    # 도면 좌표
    px_x = Column(Float, nullable=False)
    px_y = Column(Float, nullable=False)
    # GPS 좌표
    gps_lat = Column(Float, nullable=False)
    gps_lng = Column(Float, nullable=False)
```

변환 함수:
```python
def gps_to_floor_coords(lat: float, lng: float, floor_id: int, db: Session) -> tuple[float, float]:
    """GPS 좌표 → 도면 px 좌표 변환 (2점 기반 선형 변환)"""
    anchors = db.query(FloorAnchor).filter(FloorAnchor.floor_id == floor_id).all()
    # affine transform 계산...
    return (px_x, px_y)
```

**장점:** 정확도 높음, 범용적
**단점:** 관리자가 기준점 GPS를 현장에서 측정해야 함

### Option B: 도면 좌표 = GPS 좌표 통일 (소규모 데모용)

도면 노드를 GPS 좌표계로 직접 등록. FloorNode의 x, y를 경도/위도로 설정.

**장점:** 변환 레이어 불필요, 단순
**단점:** 도면 이미지와 좌표 스케일이 안 맞음, 실내 정밀도 저하

### Option C: 프론트엔드에서 변환 후 전송

프론트엔드가 도면의 기준점 정보를 받아 GPS → px 변환 후 서버에 px 좌표로 POST.

**장점:** 서버 수정 최소화
**단점:** 프론트엔드에 변환 로직 집중, 기준점 데이터 API 추가 필요

## 제안 구현 계획 (Option A 기준)

### Step 1: 모델 추가
- [ ] `models/building.py`에 `FloorAnchor` 모델 추가
- [ ] `routers/buildings.py`에 앵커 CRUD API 추가

### Step 2: 변환 서비스
- [ ] `services/coordinate.py` 생성 — `gps_to_floor()`, `floor_to_gps()` 변환 함수
- [ ] 최소 2개 앵커 → affine transform, 3개 이상 → least squares fit

### Step 3: 위치 업데이트 파이프라인 수정
- [ ] `POST /api/locations/update` 호출 시 GPS 좌표를 도면 좌표로 변환 후 저장
- [ ] 또는 GPS 원본 + 변환 좌표 둘 다 저장 (이력 추적용)

### Step 4: 프론트엔드 연동
- [ ] `useGeolocation.ts`에서 floor_id에 맞는 앵커 데이터 로드
- [ ] 도면 위 위치 렌더링 시 변환된 좌표 사용

### Step 5: 검증
- [ ] 실제 건물에서 2개 기준점 GPS 측정 → 앵커 등록
- [ ] GPS 위치 전송 → 도면 위 올바른 위치에 마커 표시 확인
- [ ] 탈출 경로 계산이 GPS 위치 기반으로 정상 동작 확인

## 우선순위

**High** — 이 이슈가 해결되지 않으면 핵심 기능(도면 위 위치 표시, 경로 계산)이 실환경에서 동작하지 않음. 데모 시연 시 GPS 기반 실시간 추적 → 경로 안내 시나리오가 깨짐.

## 라벨

`enhancement` `backend` `frontend` `coordinate-system`
