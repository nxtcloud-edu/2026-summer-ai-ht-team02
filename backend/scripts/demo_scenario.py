"""
데모 시나리오 스크립트 — 전체 흐름 순차 실행

실행: python scripts/demo_scenario.py (backend/ 디렉토리에서)
사전 조건: 서버 실행 중 (uvicorn app.main:app --reload)

시나리오:
1. 출근 (gate 통과)
2. 건강 데이터 정상 수집
3. 화재 발생
4. 작업자 위치 업데이트 (대피 시뮬레이션)
5. 심박 이상 투입
6. 의식불명 트리거
7. 구조대 진입 경로 요청
8. 알림 resolve
"""

import requests
import time

BASE = "http://127.0.0.1:8000"

# 로그인하여 토큰 획득
def login(email: str, password: str = "demo1234") -> str:
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"Login failed: {r.text}"
    return r.json()["access_token"]


def headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def step(num: int, title: str):
    print(f"\n{'='*50}")
    print(f"  Step {num}: {title}")
    print(f"{'='*50}")


def main():
    print("=" * 60)
    print("  FireEscape AI — 데모 시나리오 실행")
    print("=" * 60)

    # 토큰 획득
    admin_token = login("admin@fire.io")
    worker1_token = login("worker1@fire.io")
    worker2_token = login("worker2@fire.io")
    rescuer_token = login("rescuer@fire.io")
    print("\n[준비] 로그인 완료 (admin, worker1, worker2, rescuer)")

    # ============================================================
    step(1, "출근 (gate 통과 시뮬레이션)")
    # ============================================================
    # 각 worker 토큰으로 직접 check-in (JWT 기반)
    worker_tokens = {}
    for i in range(1, 6):
        token = login(f"worker{i}@fire.io")
        worker_tokens[i] = token
        r = requests.post(f"{BASE}/api/attendance/check-in", headers=headers(token))
        print(f"  Worker{i} check_in: {r.status_code}")
    time.sleep(1)

    r = requests.get(f"{BASE}/api/attendance/today")
    print(f"  오늘 출퇴근 현황: {len(r.json())}건")

    # ============================================================
    step(2, "건강 데이터 정상 수집")
    # ============================================================
    for uid in [3, 4, 5, 6, 7]:
        for _ in range(3):
            r = requests.post(f"{BASE}/api/health/record", json={
                "user_id": uid, "heart_rate": 72, "temperature": 36.5
            })
        print(f"  User {uid}: 정상 건강 데이터 3회 전송")
    time.sleep(1)

    # ============================================================
    step(3, "화재 발생")
    # ============================================================
    r = requests.post(f"{BASE}/api/alerts/fire", json={
        "floor_id": 2,  # 1F (id=2, floor_number=1)
        "x": 20000,
        "y": 9600,
        "message": "1F 식당 화재 발생!"
    })
    print(f"  화재 알림: {r.status_code} → {r.json()}")
    alert_id = r.json()["alert_id"]
    time.sleep(1)

    # ============================================================
    step(4, "작업자 위치 업데이트 (대피 이동)")
    # ============================================================
    # worker1 (박민수) — 1F 강의실 → 복도로 이동
    moves = [
        (4000, 3200),   # 강의실 입구
        (8000, 3200),   # 복도 하단
        (8000, 6400),   # 복도 중앙
    ]
    for x, y in moves:
        r = requests.post(f"{BASE}/api/locations/update", json={
            "floor_id": 2, "x": x, "y": y
        }, headers=headers(worker1_token))
    print(f"  Worker1 이동: 강의실 → 복도 중앙 ({r.status_code})")

    # worker2 (최지연) — 1F 식당 (화재 근처!) → 정지
    r = requests.post(f"{BASE}/api/locations/update", json={
        "floor_id": 2, "x": 20000, "y": 9600
    }, headers=headers(worker2_token))
    print(f"  Worker2 위치: 식당 (화재 근처) ({r.status_code})")
    time.sleep(1)

    # ============================================================
    step(5, "심박 이상 투입 (Worker2)")
    # ============================================================
    # 심박 180bpm — baseline(avg~72, std~6) 대비 z > 15로 확실한 이상
    for i in range(3):
        r = requests.post(f"{BASE}/api/admin/simulate/health/4?hr=180&temp=39.5")
        result = r.json().get("result", {})
        print(f"  Worker2 심박 이상 #{i+1}: anomaly={result.get('anomaly_detected')}, count={result.get('consecutive_count')}")
    time.sleep(1)

    # ============================================================
    step(6, "의식불명 트리거 (Worker2)")
    # ============================================================
    r = requests.post(f"{BASE}/api/admin/simulate/unconscious/4")
    print(f"  Worker2 → unconscious: {r.status_code} {r.json()['message']}")
    time.sleep(1)

    # ============================================================
    step(7, "구조대 진입 경로 요청")
    # ============================================================
    # 화재 해제 전이므로 일부 엣지 차단 상태 — 비상계단 방향에서 진입
    r = requests.get(
        f"{BASE}/api/evacuation/rescuer-route/4",
        params={"floor_id": 2, "x": 8000, "y": 6400},  # 복도 중앙에서 출발 (차단 밖)
        headers=headers(rescuer_token),
    )
    if r.status_code == 200:
        data = r.json()
        print(f"  구조대 → Worker2 경로: 거리 {data.get('distance')}m, 노드 {len(data.get('path', []))}개")
    else:
        print(f"  경로 요청: {r.status_code} — {r.json().get('detail', r.text)}")
        # 차단으로 실패 시 알림 해제 후 재시도
        print("  → 화재 해제 후 재시도...")
        requests.put(f"{BASE}/api/alerts/{alert_id}/resolve")
        time.sleep(0.5)
        r = requests.get(
            f"{BASE}/api/evacuation/rescuer-route/4",
            params={"floor_id": 2, "x": 8000, "y": 6400},
            headers=headers(rescuer_token),
        )
        if r.status_code == 200:
            data = r.json()
            print(f"  (해제 후) 구조대 경로: 거리 {data.get('distance')}m, 노드 {len(data.get('path', []))}개")
        else:
            print(f"  재시도 실패: {r.status_code} {r.json().get('detail', '')}")
    time.sleep(1)

    # ============================================================
    step(8, "알림 해제 (화재 진압)")
    # ============================================================
    r = requests.put(f"{BASE}/api/alerts/{alert_id}/resolve")
    print(f"  알림 해제: {r.status_code} {r.json()}")

    # 최종 상태 확인
    r = requests.get(f"{BASE}/api/alerts/active")
    print(f"  활성 알림: {len(r.json())}개")

    r = requests.get(f"{BASE}/api/health/anomalies")
    print(f"  건강 이상: {len(r.json())}명")

    print("\n" + "=" * 60)
    print("  데모 시나리오 완료!")
    print("=" * 60)


if __name__ == "__main__":
    main()
