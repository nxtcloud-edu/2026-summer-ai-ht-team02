# PR: 모바일 실시간 화살표 대피 안내 시스템

## 요약

Worker가 화재 발생 시 핸드폰을 들고 있으면, 현재 위치와 폰 방향을 기반으로 **"어디로 가야 하는지"를 큰 화살표로 실시간 안내**하는 기능 구현.

- 백엔드: 경로 계산 + OpenAI 자연어 안내 생성 API
- 프론트: Android Chrome 방향 센서 연동 + 실시간 회전 화살표 UI

---

## 주요 변경사항

### 백엔드

| 파일 | 변경 | 설명 |
|------|------|------|
| `app/config.py` | 수정 | `OPENAI_API_KEY`, `OPENAI_MODEL` 설정 추가 |
| `requirements.txt` | 수정 | `openai==1.35.14` 추가 |
| `app/services/direction.py` | **신규** | 로컬 방향/거리 계산 유틸리티 (bearing, 상대 방향, mm→m 변환) |
| `app/services/ai_route.py` | **신규** | OpenAI 기반 자연어 경로 안내 생성 (fallback 지원) |
| `app/routers/evacuation.py` | 수정 | `POST /api/evacuation/guidance` 엔드포인트 추가 |
| `app/services/alert.py` | 수정 | 화재 차단 반경 50mm→3000mm 버그 수정 |
| `app/main.py` | 수정 | CORS `allow_origins=["*"]` (모바일 디바이스 접속 허용) |

### 프론트엔드

| 파일 | 변경 | 설명 |
|------|------|------|
| `src/pages/NavigationPage.tsx` | **신규** | 모바일 전체화면 화살표 대피 안내 페이지 |
| `src/App.tsx` | 수정 | `/navigate` 라우트 + 네비게이션 링크 추가 |
| `src/hooks/useApi.ts` | 수정 | baseURL `""` (vite proxy 경유) |
| `vite.config.ts` | 수정 | `host: true`, mkcert HTTPS, proxy `127.0.0.1` |
| `package.json` | 수정 | `vite-plugin-mkcert` devDependency 추가 |

---

## 핵심 구현 상세

### 1. Guidance API (`POST /api/evacuation/guidance`)

**Request:**
```json
{
  "floor_id": 2,
  "x": 15000,
  "y": 6400,
  "heading": 45.0
}
```

**Response:**
```json
{
  "success": true,
  "direction": "straight",
  "arrow": "⬆️",
  "rotate_deg": 0,
  "distance_m": 3.4,
  "instruction": "직진 방향으로 3m 이동하세요 (다음: 중앙계단)",
  "warning": "⚠️ 4m 앞에 화재 구역이 있습니다. 우회 경로로 이동 중입니다.",
  "next_landmark": "중앙계단",
  "bearing": 45.0,
  "total_distance_m": 6.4,
  "exit_name": "후문",
  "path": [{"node_id": 19, "x": 16000, "y": 6400, "node_type": "path"}, ...]
}
```

**동작 흐름:**
1. Dijkstra 최단 안전 경로 계산 (차단 엣지 우회)
2. `direction.py`로 방위각 + 상대 방향 즉시 계산
3. OpenAI API로 자연어 안내 보강 (키 미설정 시 로컬 결과만 사용)
4. 화재 10m 이내 시 경고 메시지 포함

### 2. 실시간 화살표 회전 (프론트)

```
서버 응답: bearing = 45° (출구는 북동쪽)
디바이스 센서: heading = 90° (폰이 동쪽을 향함)
→ 화살표 각도 = (45° - 90° + 360°) % 360° = 315° (좌측 전방)
→ 폰을 돌릴 때마다 즉시 반영
```

- `deviceorientationabsolute` 이벤트 사용 (Android Chrome 전용, 절대 방위)
- 서버 요청은 5초 간격, 화살표 회전은 센서 이벤트마다 즉시
- CSS `transition-transform 500ms`로 부드러운 회전 애니메이션

### 3. 화재 차단 반경 수정

- **Before**: `radius=50mm` → 노드 정확 위치에 화재 놓지 않으면 차단 불가
- **After**: `radius=3000mm` (3m) → 현실적 차단 범위, 우회 경로 생존 보장
- 엣지 평균 거리 3757mm 대비 적절한 값

---

## 모바일 접속 환경 설정

```bash
# 백엔드
cd backend
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# 프론트 (HTTPS + host 노출)
cd frontend
npm run dev
```

핸드폰 핫스팟으로 노트북 연결 후, 핸드폰 Chrome에서:
```
https://<노트북 IP>:5173/navigate
```

- `vite-plugin-mkcert`로 자체서명 HTTPS 제공 → 센서 API 활성화
- 첫 접속 시 인증서 경고 → "고급 → 계속 진행"

---

## 테스트 결과

### 화재 없는 상황
| 위치 | 방향 | 거리 | 출구 |
|------|------|------|------|
| 1F 중앙 (15000, 6400) | ⬆️ 직진 | 3m | 후문 |
| 1F 강의실 (4000, 1600) | ⬇️ 뒤로 | 2m | 후문 |

### 화재 발생 상황 (중앙계단 12000, 6400)
| 위치 | 방향 | 경고 | 우회 출구 |
|------|------|------|------|
| 복도 중앙 (8000, 6400) | ⬇️ 뒤로 3m | ⚠️ 4m 앞 화재 | 정문 (상단 우회) |
| 식당 입구 (20000, 9600) | ⬆️ 직진 3m | ⚠️ 9m 앞 화재 | 비상계단 |
| 관리사무실 (27000, 6400) | ⬅️ 좌회전 3m | (안전) | 비상계단 |
| 복도 하단 (8000, 3200) | ➡️ 우회전 8m | ⚠️ 5m 앞 화재 | 후문 |

### heading 연동
- heading=0° (북쪽): "뒤로" → heading=90° (동쪽): 같은 위치에서 "우회전"으로 변경 ✅

---

## 비용 (OpenAI)

- 모델: `gpt-4o-mini`
- API 키 미설정 시 로컬 계산만으로 동작 (AI 없이도 방향 안내 정상)
- 예상: 20명 × 5분 대피 ≈ 1,200 호출 → ~$0.05

---

## 남은 작업 / 후속 PR

- [ ] 프로덕션 배포 시 CORS origin 제한 복원
- [ ] 다층 경로 안내 (계단 이동 시 층 변경 감지)
- [ ] 도착 감지 (출구 5m 이내 → "대피 완료" 상태 자동 전환)
- [ ] WebSocket 기반 실시간 push (현재는 5초 polling)
