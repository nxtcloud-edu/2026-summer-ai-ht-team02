# FireEscape AI — 위치 기반 실시간 탈출 경로 제공 시스템

화재 발생 시 스마트워치 기반 실시간 위치 추적과 AI 경로 계산으로 근로자에게 최적 탈출 경로를 안내하고, 관리자·구조대에게 미대피자 위치를 도면 위에 표시하는 시스템

## 핵심 기능

| # | 기능 | 설명 |
|---|---|---|
| ① | 사용자 관리 | 근로자, 관리자, 구조대 역할 분리 |
| ② | 건물 도면 관리 | 층별 도면 업로드 + 노드/경로 편집 |
| ③ | 실시간 위치 추적 | 스마트워치(BLE/WiFi) 기반 위치 수집 |
| ④ | 화재 감지/알림 | 센서 연동, 화재 정보를 근로자에게 자동 전송 |
| ⑤ | AI 탈출 경로 계산 | 화재 구역 회피 + 최단 경로 (A*/Dijkstra) |
| ⑥ | 근로자 탈출 안내 | 스마트워치/모바일에 경로 표시 |
| ⑦ | 관리자 대시보드 | 도면 위 재실자 위치, 탈출 현황, 미대피자 강조 |
| ⑧ | 구조대 뷰 | 의식 잃은/미대피 사용자 위치 + 최적 진입 경로 |
| ⑨ | 동료 간 SOS | 위기 상황 동료에게 전송, 상호 도움 체계 |

## 기술 스택

| 영역 | 기술 |
|---|---|
| Frontend | React + TypeScript + Vite + Tailwind CSS |
| Backend | FastAPI (Python) |
| 실시간 통신 | WebSocket |
| 경로 알고리즘 | NetworkX (A*, Dijkstra) |
| DB | SQLite (개발) / PostgreSQL (운영) |
| 도면 렌더링 | Canvas / SVG |

## 프로젝트 구조

```
├── frontend/          # React 클라이언트
│   └── src/
│       ├── pages/     # 대시보드, 도면뷰, 탈출경로, 구조대뷰
│       ├── components/
│       └── hooks/
├── backend/           # FastAPI 서버
│   └── app/
│       ├── models/    # DB 모델
│       ├── routers/   # API 엔드포인트
│       └── services/  # 비즈니스 로직
├── .github/           # 이슈/PR 템플릿
└── README.md
```

## 시작하기

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## 시스템 흐름

```
화재 감지 → 근로자 알림 전송 → 스마트워치 위치 수집
    → AI 탈출 경로 계산 (화재 구역 회피)
    → 근로자: 개인 탈출 경로 안내
    → 관리자: 도면 위 전체 현황 모니터링
    → 구조대: 미대피자 위치 확인 + 진입 경로
    → 동료 간 SOS 전송/수신
```
