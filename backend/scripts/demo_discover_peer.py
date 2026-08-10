"""
데모 시나리오: 새 유저가 대피 중 위험 동료를 발견하는 플로우

실행: python scripts/demo_discover_peer.py (backend/ 디렉토리에서)
사전 조건: 서버 실행 중 + seed.py 실행 완료

시나리오:
1. 새 유저(worker6 "송하영") 회원가입
2. 출근 처리
3. 화재 발생
4. worker2(최지연)가 화재 근처에서 의식불명 상태로 전환
5. 새 유저(송하영)가 대피 이동 중 → 위치 업데이트
6. 근처 동료 조회 API → 위험 동료 발견
7. SOS 응답 (도움 의사 표시)
8. 시나리오 결과 출력
"""

import requests
import time

BASE = "http://127.0.0.1:8000"


def login(email: str, password: str = "demo1234") -> str:
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"Login failed for {email}: {r.text}"
    return r.json()["access_token"]


def headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def step(num: int, title: str):
    print(f"\n{'='*50}")
    print(f"  Step {num}: {title}")
    print(f"{'='*50}")


def main():
    print("=" * 60)
    print("  데모: 새 유저가 위험 동료를 발견하는 플로우")
    print("=" * 60)

    # ============================================================
    step(1, "새 유저 회원가입 (송하영, worker)")
    # ============================================================
    r = requests.post(f"{BASE}/api/auth/register", json={
        "email": "worker6@fire.io",
        "password": "demo1234",
        "name": "송하영",
        "role": "worker",
        "department": "마케팅팀",
    })
    if r.status_code == 200:
        new_user = r.json()
        new_token = new_user["access_token"]
        new_user_id = new_user["user_id"]
        print(f"  가입 완료: user_id={new_user_id}, email=worker6@fire.io")
    elif r.status_code == 400 and "이미 등록" in r.text:
        # 이미 가입된 경우 로그인
        print("  이미 가입된 유저 → 로그인")
        new_token = login("worker6@fire.io")
        me = requests.get(f"{BASE}/api/auth/me", headers=headers(new_token))
        new_user_id = me.json()["id"]
        print(f"  로그인 완료: user_id={new_user_id}")
    else:
        print(f"  가입 실패: {r.status_code} {r.text}")
        return

    # ============================================================
    step(2, "출근 처리")
    # ============================================================
    r = requests.post(f"{BASE}/api/attendance/check-in", headers=headers(new_token))
    print(f"  송하영 출근: {r.status_code}")

    # 초기 위치 등록 (1F 강의실 입구)
    r = requests.post(f"{BASE}/api/locations/update", json={
        "floor_id": 2, "x": 4000, "y": 3200
    }, headers=headers(new_token))
    print(f"  초기 위치 설정 (1F 강의실 입구): {r.status_code}")
    time.sleep(0.5)

    # ============================================================
    step(3, "화재 발생 (1F 식당)")
    # ============================================================
    r = requests.post(f"{BASE}/api/alerts/fire", json={
        "floor_id": 2,
        "x": 20000,
        "y": 9600,
        "message": "1F 식당에서 화재 발생!"
    })
    print(f"  화재 알림 생성: {r.status_code}")
    if r.status_code == 200:
        alert_id = r.json()["alert_id"]
        print(f"  alert_id={alert_id}")
    else:
        alert_id = None
        print(f"  (이미 활성 화재가 있을 수 있음)")
    time.sleep(0.5)

    # ============================================================
    step(4, "worker2(최지연) 의식불명 전환")
    # ============================================================
    # worker2 위치를 식당 근처에 배치
    worker2_token = login("worker2@fire.io")
    r = requests.post(f"{BASE}/api/locations/update", json={
        "floor_id": 2, "x": 18000, "y": 8000, "heart_rate": 35
    }, headers=headers(worker2_token))
    print(f"  최지연 위치 (식당 근처, 심박 35): {r.status_code}")

    # 의식불명 시뮬레이션
    r = requests.post(f"{BASE}/api/admin/simulate/unconscious/4")
    if r.status_code == 200:
        print(f"  최지연 → unconscious: {r.json()['message']}")
    else:
        print(f"  unconscious 시뮬: {r.status_code} (이미 unconscious일 수 있음)")
    time.sleep(0.5)

    # ============================================================
    step(5, "송하영 대피 이동 (강의실 → 복도 → 식당 방향)")
    # ============================================================
    # 대피 경로를 따라 이동하다가 최지연 근처에 도달
    moves = [
        (4000, 3200, "강의실 입구 출발"),
        (8000, 3200, "복도 하단"),
        (8000, 6400, "복도 중앙"),
        (12000, 6400, "중앙계단 방향"),
        (16000, 6400, "중앙 교차점"),
        (18000, 7000, "식당 방향 (최지연 근처 도착)"),
    ]

    for x, y, desc in moves:
        r = requests.post(f"{BASE}/api/locations/update", json={
            "floor_id": 2, "x": x, "y": y
        }, headers=headers(new_token))
        print(f"  이동 → {desc} ({x},{y}): {r.status_code}")
        time.sleep(0.3)

    # ============================================================
    step(6, "근처 동료 조회 → 위험 유저 발견!")
    # ============================================================
    r = requests.get(
        f"{BASE}/api/peers/nearby/{new_user_id}",
        params={"radius": 5000},  # 5m(5000mm) 반경
        headers=headers(new_token),
    )
    if r.status_code == 200:
        nearby = r.json()
        print(f"  반경 5m 내 동료: {len(nearby)}명")
        for peer in nearby:
            status_text = peer.get("status", "unknown")
            name = peer.get("name", f"#{peer.get('user_id', '?')}")
            distance = peer.get("distance", 0)
            hr = peer.get("heart_rate")
            marker = " ⚠️ 위험!" if status_text in ("unconscious", "at_risk") else ""
            hr_text = f", 심박={hr}bpm" if hr else ""
            print(f"    → {name}: 상태={status_text}, 거리={distance:.0f}mm{hr_text}{marker}")
    else:
        print(f"  근처 조회 실패: {r.status_code} {r.text}")

    # 반경 넓혀서 재조회
    r = requests.get(
        f"{BASE}/api/peers/nearby/{new_user_id}",
        params={"radius": 10000},  # 10m 반경
        headers=headers(new_token),
    )
    if r.status_code == 200:
        nearby = r.json()
        print(f"\n  반경 10m 내 동료: {len(nearby)}명")
        for peer in nearby:
            status_text = peer.get("status", "unknown")
            name = peer.get("name", f"#{peer.get('user_id', '?')}")
            distance = peer.get("distance", 0)
            hr = peer.get("heart_rate")
            marker = " ⚠️ 위험!" if status_text in ("unconscious", "at_risk") else ""
            hr_text = f", 심박={hr}bpm" if hr else ""
            print(f"    → {name}: 상태={status_text}, 거리={distance:.0f}mm{hr_text}{marker}")

    # ============================================================
    step(7, "SOS 응답 (도움 의사 표시)")
    # ============================================================
    # 활성 SOS 목록 확인
    r = requests.get(f"{BASE}/api/peers/sos/active", headers=headers(new_token))
    if r.status_code == 200 and len(r.json()) > 0:
        sos_list = r.json()
        print(f"  활성 SOS: {len(sos_list)}건")
        # 첫 번째 SOS에 응답
        sos_id = sos_list[0].get("alert_id") or sos_list[0].get("id")
        r = requests.post(
            f"{BASE}/api/peers/sos/{sos_id}/respond",
            json={"message": "근처에 있습니다! 도와드리겠습니다."},
            headers=headers(new_token),
        )
        print(f"  SOS 응답: {r.status_code}")
    else:
        print(f"  활성 SOS 없음 → 송하영이 직접 SOS 발송 (위험 동료 발견 신고)")
        r = requests.post(f"{BASE}/api/peers/sos", json={
            "floor_id": 2,
            "x": 18000,
            "y": 7000,
            "message": "근처에 의식불명 동료 발견! 도움 필요합니다.",
        }, headers=headers(new_token))
        if r.status_code == 201:
            print(f"  SOS 발송 완료: {r.json()}")
        else:
            print(f"  SOS 발송: {r.status_code} {r.text}")

    # ============================================================
    step(8, "최종 상태 확인")
    # ============================================================
    # 대피 현황
    r = requests.get(f"{BASE}/api/evacuation/status")
    if r.status_code == 200:
        statuses = r.json()
        print(f"\n  전체 대피 현황: {len(statuses)}명")
        for s in statuses:
            name = s.get("user_name", f"#{s['user_id']}")
            emoji = {"evacuated": "✅", "unconscious": "🚨", "evacuating": "🏃", "in_building": "🏢"}.get(s["status"], "❓")
            print(f"    {emoji} {name}: {s['status']}")

    # 의식불명 목록
    r = requests.get(f"{BASE}/api/evacuation/unconscious")
    if r.status_code == 200:
        unconscious = r.json()
        print(f"\n  의식불명 근로자: {len(unconscious)}명")
        for u in unconscious:
            print(f"    🚨 user_id={u['user_id']}, 심박={u.get('heart_rate')}, 위치=({u.get('x')},{u.get('y')})")

    # 정리: 화재 해제
    if alert_id:
        requests.put(f"{BASE}/api/alerts/{alert_id}/resolve")
        print(f"\n  화재 알림 해제 (alert_id={alert_id})")

    print("\n" + "=" * 60)
    print("  데모 시나리오 완료!")
    print("  ")
    print("  [플로우 요약]")
    print("  송하영(신규 유저) → 출근 → 화재 발생 → 대피 이동")
    print("  → 근처 동료 조회 → 의식불명 최지연 발견 → SOS/신고")
    print("=" * 60)


if __name__ == "__main__":
    main()
