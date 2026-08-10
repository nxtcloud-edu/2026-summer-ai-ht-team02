# Ontology-driven Site Planning Agent

기업의 운영 구조를 읽고, 지방 이전 가능성을 사전에 검증하는 AI

ERP·HR·MES·SCM에서 기업 온톨로지를 구축하고, 3-Tier 보안 구조로 지역의 인력·산업·교통·인프라 데이터와 연결해 후보지 조사부터 채용 가능성 시뮬레이션, 리스크 분석, 이전 기획안까지 자동 생성합니다.

## 기술 스택

| 영역 | 기술 |
|---|---|
| Frontend | React + TypeScript + Vite + Tailwind CSS |
| Backend | FastAPI (Python) |
| DB | SQLite (개발) / PostgreSQL (운영) |
| Graph | NetworkX (온톨로지 관계 표현) |
| AI/LLM | OpenAI API + LangChain |
| 지도 | Leaflet (후보지 시각화) |

## 프로젝트 구조

```
├── frontend/          # React 클라이언트
├── backend/           # FastAPI 서버
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

## 핵심 기능

1. **Enterprise Ontology** — 기업 내부 데이터를 시설·공정·직무·스킬·물류 관계로 구조화
2. **3-Tier Secure Architecture** — 원천데이터 보호, 의미 단위만 공유
3. **Regional Intelligence** — 지역 인력풀·교육·산업·교통·부지 데이터 매핑
4. **Feasibility Scoring** — 실제 채용·운영 가능성 계산
5. **Planning Agent** — 사전 타당성 기획안 자동 생성

## 기능 상세

| 기능 | 설명 |
|---|---|
| 온톨로지 구축 | ERP/HR/MES/SCM 데이터에서 관계 그래프 자동 생성 |
| 후보지 탐색 | 지역 데이터 기반 조건 매칭 |
| Feasibility Score | 인력·물류·인프라 종합 점수 산출 |
| 시뮬레이션 | 채용 가능 인력, 경쟁수요, 통근권 분석 |
| 기획안 생성 | LLM 기반 타당성 보고서 자동 작성 |
| 리스크 분석 | 미분양·인력 미스매치·공급망 병목 사전 탐지 |
