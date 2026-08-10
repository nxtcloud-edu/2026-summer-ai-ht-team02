# #29 OpenAI 기반 실시간 대피 경로 안내 시스템

## 개요

현재 시스템은 NetworkX Dijkstra 기반으로 **좌표 경로(path)**만 반환한다.
이 PR에서는 OpenAI API를 활용하여:

1. 위험 지도(fire/hazard map) 기반 **가중치 경로 점수 평가**
2. 경로 좌표 → **자연어 방향 안내** 생성 ("앞으로 7m 이동 후 좌회전")
3. 실시간 상황 변화 시 **동적 재안내**

를 구현한다.

---

## 현재 아키텍처 (AS-IS)

```
사용자 GPS (5초 주기)
  → coordinate.gps_to_floor() → 도면 (x, y)
  → evacuation.calculate_evacuation_route()
      → NetworkX shortest_path (Dijkstra)
      → [{node_id, x, y, node_type}, ...]  ← 좌표 배열만 반환
```

**한계점:**
- 경로 = 좌표 배열 → 사용자가 해석할 수 없음
- 위험도 = 이진값 (blocked/unblocked) → 연속적 위험 가중치 없음
- 최단 거리 ≠ 최안전 경로 (연기 확산 방향 미고려)

---

## 목표 아키텍처 (TO-BE)

```
[사용자 실시간 위치]
       ↓
  coordinate.gps_to_floor() → (x, y)
       ↓
┌─────────────────────┐
│ 위험 지도 생성       │
│ - 🔥 화재 = 통행불가  │
│ - 🟠 주변 = 높은 비용 │
│ - 🟢 안전 = 낮은 비용 │
└─────────────────────┘
       ↓
 A* 경로 계산 (가중치 반영)
 모든 탈출구에 대해 비교
       ↓
 "가장 안전한 경로" 선택
       ↓
 OpenAI API 호출
 (경로 좌표 + 노드 라벨 + 위험 정보)
       ↓
 자연어 방향 안내 생성
 "앞으로 7m 이동 후 좌회전"
       ↓
 WebSocket push → 프론트엔드
```

---

## 구현 계획

### Phase 1: 인프라 설정

| 작업 | 파일 | 내용 |
|------|------|------|
| 1-1 | `backend/.env.example` | `OPENAI_API_KEY=sk-xxx` 추가 |
| 1-2 | `backend/app/config.py` | `OPENAI_API_KEY: str`, `OPENAI_MODEL: str = "gpt-4o-mini"` 설정 추가 |
| 1-3 | `backend/requirements.txt` | `openai>=1.35.0` 추가 |

---

### Phase 2: 위험 가중치 그래프 개선

**파일:** `backend/app/services/evacuation.py`

현재 `is_blocked` 이진 차단 → 연속 가중치 시스템으로 확장:

```python
def build_weighted_floor_graph(floor_id: int, fire_positions: list, db: Session) -> nx.Graph:
    """화재 위치 기반 거리 비례 가중치 그래프 생성"""
    G = nx.Graph()
    nodes = db.query(FloorNode).filter(FloorNode.floor_id == floor_id).all()
    edges = db.query(FloorEdge).filter(FloorEdge.floor_id == floor_id).all()

    for node in nodes:
        # 각 노드에 위험도 점수 부여
        danger_score = calculate_danger_score(node.x, node.y, fire_positions)
        G.add_node(node.id, x=node.x, y=node.y, 
                   node_type=node.node_type, danger=danger_score)

    for edge in edges:
        if edge.is_blocked:
            continue
        # 기본 거리 + 위험도 가중치
        base_weight = edge.distance or 1.0
        danger_penalty = _edge_danger_penalty(G, edge, fire_positions)
        G.add_edge(edge.from_node_id, edge.to_node_id,
                   weight=base_weight + danger_penalty)

    return G


def calculate_danger_score(x: float, y: float, fires: list) -> float:
    """좌표의 위험도 계산 (0.0 안전 ~ 1.0 위험)"""
    if not fires:
        return 0.0
    min_dist = min(
        ((x - fx)**2 + (y - fy)**2)**0.5
        for fx, fy in fires
    )
    # 50px 이내: 위험, 50~150px: 주의, 150px+: 안전
    if min_dist < 50:
        return 1.0
    elif min_dist < 150:
        return max(0.0, 1.0 - (min_dist - 50) / 100)
    return 0.0
```

**가중치 공식:**
```
edge_cost = base_distance + (danger_score × DANGER_MULTIPLIER)
DANGER_MULTIPLIER = 200  (위험 구간 통과 비용 ≈ 200px 우회와 동등)
```

---

### Phase 3: OpenAI 방향 안내 서비스

**새 파일:** `backend/app/services/ai_route.py`

```python
"""OpenAI API를 활용한 자연어 경로 안내 생성"""

from openai import AsyncOpenAI
from app.config import settings

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

SYSTEM_PROMPT = """
당신은 건물 내 화재 대피 안내 시스템입니다.
사용자의 현재 위치와 경로 좌표를 받아 간결한 방향 안내를 생성합니다.

규칙:
1. 방향은 "직진", "좌회전", "우회전", "뒤돌아"로 표현
2. 거리는 미터(m) 단위, 소수점 없이 반올림
3. 위험 구역 근처일 경우 경고 메시지 포함
4. 한 번에 다음 1~2 구간만 안내 (너무 많은 정보 금지)
5. 반드시 JSON 형식으로 응답

응답 형식:
{
  "direction": "left" | "right" | "straight" | "back",
  "distance_m": <정수>,
  "instruction": "<한국어 안내 문장>",
  "warning": "<위험 경고 또는 null>",
  "next_landmark": "<다음 랜드마크 (출구A, 계단1 등)>"
}
"""


async def generate_route_guidance(
    current_x: float,
    current_y: float,
    path_coords: list[dict],
    fire_positions: list[dict],
    floor_info: dict,
) -> dict:
    """경로 좌표 + 위험 정보 → 자연어 방향 안내 생성"""

    # 다음 2~3개 waypoint만 전달 (토큰 절약)
    upcoming_path = path_coords[:3]

    user_message = f"""
현재 위치: ({current_x:.1f}, {current_y:.1f})
층 정보: {floor_info.get('name', '알 수 없음')}

경로 waypoints (다음 구간):
{_format_waypoints(upcoming_path)}

활성 화재 위치:
{_format_fires(fire_positions)}

현재 위치에서 다음 waypoint까지의 방향 안내를 생성해주세요.
"""

    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,  # 일관성 우선
        max_tokens=200,
    )

    return _parse_guidance_response(response.choices[0].message.content)
```

---

### Phase 4: API 엔드포인트

**파일:** `backend/app/routers/evacuation.py`에 엔드포인트 추가

```python
class GuidanceRequest(BaseModel):
    user_id: int
    floor_id: int
    x: float          # 현재 도면 좌표
    y: float
    heading: float | None = None  # 사용자 진행 방향 (degree, 선택)


class GuidanceResponse(BaseModel):
    success: bool
    direction: str | None = None        # left, right, straight, back
    distance_m: int | None = None
    instruction: str | None = None      # "앞으로 7m 이동 후 좌회전"
    warning: str | None = None          # 위험 경고
    next_landmark: str | None = None    # "출구A"
    path: list[PathNode] | None = None  # 전체 경로 좌표 (프론트 시각화용)
    exit_name: str | None = None


@router.post("/guidance", response_model=GuidanceResponse)
async def get_ai_guidance(data: GuidanceRequest, db: Session = Depends(get_db)):
    """OpenAI 기반 실시간 방향 안내"""
    # 1. 위험 지도 기반 경로 계산
    # 2. OpenAI API 호출 → 자연어 안내 생성
    # 3. 응답 반환
    ...
```

---

### Phase 5: 방향 계산 유틸리티

**새 파일:** `backend/app/services/direction.py`

OpenAI API 호출 전 로컬에서 기본 방향 계산 (fallback + 보조 정보):

```python
import math

def calculate_bearing(from_x, from_y, to_x, to_y) -> float:
    """두 점 사이 방위각 (0=북, 90=동, 180=남, 270=서)"""
    dx = to_x - from_x
    dy = -(to_y - from_y)  # 도면 y축은 아래가 +
    angle = math.degrees(math.atan2(dx, dy)) % 360
    return angle


def bearing_to_direction(bearing: float, user_heading: float = 0) -> str:
    """방위각 → 상대 방향 (사용자 진행방향 기준)"""
    relative = (bearing - user_heading + 360) % 360
    if relative < 30 or relative >= 330:
        return "straight"
    elif 30 <= relative < 150:
        return "right"
    elif 150 <= relative < 210:
        return "back"
    else:
        return "left"


def calculate_distance(x1, y1, x2, y2, scale=0.05) -> float:
    """도면 px 거리 → 실제 미터 (scale: m/px)"""
    px_dist = ((x2 - x1)**2 + (y2 - y1)**2)**0.5
    return px_dist * scale
```

---

### Phase 6: WebSocket 실시간 푸시

**기존 파일 수정:** `backend/app/websocket_manager.py`

```python
async def broadcast_guidance_update(user_id: int, guidance: dict):
    """특정 사용자에게 방향 안내 WebSocket 푸시"""
    await self.send_personal(user_id, {
        "type": "guidance_update",
        "data": guidance,
    })
```

위치 갱신(POST /api/locations/update) 시 자동으로 guidance도 재계산:

```
위치 갱신 → 경로 재계산 (3초 throttle) → AI 안내 생성 → WS push
```

---

### Phase 7: 프론트엔드 연동

**파일:** `frontend/src/pages/Evacuation.tsx`

- 방향 화살표 UI (↖ ← ↑ → ↗)
- 안내 문구 표시 ("앞으로 7m 이동 후 좌회전")
- 위험 경고 배너 (빨간색)
- 도면 위 경로 시각화 (FloorCanvas에 path overlay)

---

## API 비용 최적화 전략

| 전략 | 설명 |
|------|------|
| **Throttle** | 위치 갱신 5초 × guidance 재계산 3초 → 최소 5초 간격 호출 |
| **캐시** | 같은 구간(start_node → next_node) 동일하면 이전 안내 재사용 |
| **로컬 fallback** | direction.py로 기본 방향 계산, AI는 자연어 생성에만 사용 |
| **gpt-4o-mini** | 비용 효율 모델 사용 (input $0.15/1M, output $0.60/1M) |
| **max_tokens=200** | 응답 길이 제한 |
| **Batch 가능성** | 동일 층 다수 사용자 → 위험지도 1회 생성 후 공유 |

**예상 비용:** 20명 사용자 × 5초 간격 × 5분 대피 = ~1,200 호출 → ~$0.05 (gpt-4o-mini)

---

## 시퀀스 다이어그램

```
User App        Backend                  OpenAI API
   │                │                        │
   │ GPS (5초)      │                        │
   ├───────────────►│                        │
   │                │ gps_to_floor()         │
   │                │ build_weighted_graph() │
   │                │ A* route calculation   │
   │                │                        │
   │                │ path + fires + context │
   │                ├───────────────────────►│
   │                │                        │
   │                │◄───────────────────────┤
   │                │ {direction, instruction}│
   │                │                        │
   │◄───────────────┤ WS: guidance_update    │
   │                │                        │
   │ 화면 표시      │                        │
   │ "좌회전 7m"    │                        │
```

---

## 파일 변경 목록

| 상태 | 파일 | 설명 |
|------|------|------|
| 수정 | `backend/.env.example` | OPENAI_API_KEY 추가 |
| 수정 | `backend/app/config.py` | OpenAI 설정 필드 추가 |
| 수정 | `backend/requirements.txt` | openai 패키지 추가 |
| **신규** | `backend/app/services/ai_route.py` | OpenAI 방향 안내 생성 서비스 |
| **신규** | `backend/app/services/direction.py` | 로컬 방향/거리 계산 유틸리티 |
| 수정 | `backend/app/services/evacuation.py` | 위험 가중치 그래프 함수 추가 |
| 수정 | `backend/app/routers/evacuation.py` | `/guidance` 엔드포인트 추가 |
| 수정 | `backend/app/routers/__init__.py` | (기존 evacuation 라우터에 추가이므로 변경 없을 수 있음) |
| 수정 | `backend/app/websocket_manager.py` | guidance 푸시 메서드 추가 |
| 수정 | `frontend/src/pages/Evacuation.tsx` | 방향 안내 UI 추가 |

---

## 의존성

- `openai>=1.35.0` (AsyncOpenAI 클라이언트)
- 기존: `networkx`, `numpy`, `fastapi`, `sqlalchemy`

---

## 위험/고려사항

1. **API 응답 지연**: OpenAI 평균 ~500ms → 대피 시 체감 지연. fallback으로 로컬 계산 결과 먼저 전송 후 AI 안내 도착 시 업데이트.
2. **API 장애**: OpenAI 다운 시 `direction.py` 로컬 계산만으로 기본 방향 안내 유지.
3. **할루시네이션**: 존재하지 않는 출구/경로 안내 방지 → response에 node_id 포함시켜 검증.
4. **동시 호출 제한**: OpenAI rate limit (RPM) → asyncio.Semaphore로 동시 호출 수 제한.
5. **실내 GPS 정확도**: 기존 coordinate.py 앵커 시스템 의존 → 오차 큰 경우 nearest_node로 보정.
