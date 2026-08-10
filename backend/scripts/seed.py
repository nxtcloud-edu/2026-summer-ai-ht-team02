"""
데모용 시드 데이터 스크립트 — 실제 도면 기반

실행: python scripts/seed.py (backend/ 디렉토리에서)

건물 구조 (종단면도 기반):
  B1F: 기계실, 전기실, 설비실, 창고
  1F:  로비, 강의실, 식당/카페, 관리사무실 (평면도 사용)
  2F:  교육실 2-1, 교육실 2-2, 라운지, 휴게공간
  3F:  교육실 3-1, 교육실 3-2, 회의실, 휴게공간

도면 크기: 30,000mm x 12,800mm → 좌표계는 mm 단위 사용
X축: X1=0, X2=8000, X3=16000, X4=24000, X5=30000
Y축: Y1=0 (하단), Y2=12800 (상단)

출입구: 상단 중앙(정문), 하단 중앙(후문)
계단: 중앙 2곳 (X2~X3 사이), 우측 외부 비상계단 (X5 부근)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import bcrypt
from datetime import datetime, timezone

from app.models.database import Base, engine, SessionLocal
from app.models.user import User, UserRole
from app.models.building import Building, Floor, FloorNode, FloorEdge, FloorAnchor
from app.models.location import WorkerLocation, EvacuationStatus
from app.models.alert import Alert, SOSResponse


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def seed():
    print("=" * 50)
    print("FireEscape AI — 데모 시드 데이터 생성")
    print("=" * 50)

    # DB 초기화
    print("\n[1/8] DB 초기화...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        # ============================================================
        # 유저 등록
        # ============================================================
        print("[2/8] 유저 등록 (admin 1, rescuer 1, worker 6)...")
        pw = hash_password("demo1234")

        users = [
            User(email="admin@fire.io", hashed_password=pw, name="관리자 김철수", role=UserRole.ADMIN, department="안전관리팀"),
            User(email="rescuer@fire.io", hashed_password=pw, name="구조대 이영희", role=UserRole.RESCUER, department="소방대"),
            User(email="worker1@fire.io", hashed_password=pw, name="박민수", role=UserRole.WORKER, department="교육팀", floor_id=1),
            User(email="worker2@fire.io", hashed_password=pw, name="최지연", role=UserRole.WORKER, department="디자인팀", floor_id=1),
            User(email="worker3@fire.io", hashed_password=pw, name="정도현", role=UserRole.WORKER, department="서버팀", floor_id=2),
            User(email="worker4@fire.io", hashed_password=pw, name="이수진", role=UserRole.WORKER, department="기획팀", floor_id=2),
            User(email="worker5@fire.io", hashed_password=pw, name="한동우", role=UserRole.WORKER, department="교육팀", floor_id=3),
            User(email="worker6@fire.io", hashed_password=pw, name="송하영", role=UserRole.WORKER, department="마케팅팀", floor_id=1),
        ]
        db.add_all(users)
        db.flush()

        # ============================================================
        # 건물 + 층
        # ============================================================
        print("[3/8] 건물/층 생성...")
        building = Building(name="FireEscape 교육센터", address="서울시 강남구 테헤란로 123", total_floors=4)
        db.add(building)
        db.flush()

        floors = [
            Floor(building_id=building.id, floor_number=-1, name="B1F", floor_plan_url=None, width=30000.0, height=12800.0),
            Floor(building_id=building.id, floor_number=1, name="1F", floor_plan_url="/uploads/floor_1f_plan.png", width=30000.0, height=12800.0),
            Floor(building_id=building.id, floor_number=2, name="2F", floor_plan_url=None, width=30000.0, height=12800.0),
            Floor(building_id=building.id, floor_number=3, name="3F", floor_plan_url=None, width=30000.0, height=12800.0),
        ]
        db.add_all(floors)
        db.flush()

        f_b1 = floors[0]
        f_1f = floors[1]
        f_2f = floors[2]
        f_3f = floors[3]

        # ============================================================
        # 1F 노드 (평면도 기반 — mm 좌표)
        # ============================================================
        print("[4/8] 1F 노드 등록 (평면도 기반)...")

        # 좌표 기준:
        # X: X1=0, X2=8000, X3=16000, X4=24000, X5=30000
        # Y: Y1=0(하단), Y2=12800(상단)
        # 정문: 상단 중앙 (~X2, Y2=12800)
        # 후문: 하단 중앙 (~X3, Y1=0)

        nodes_1f_data = [
            # 출입구/출구
            (4000, 12800, "exit", "정문"),              # N0
            (16000, 0, "exit", "후문"),                 # N1
            (30000, 6400, "exit", "비상계단 출구"),      # N2

            # 로비 영역 (X1~X2, 상단)
            (4000, 9600, "path", "로비 중앙"),           # N3
            (7500, 9600, "path", None),             # N4

            # 중앙 복도 (X2 부근, 상하 연결)
            (8000, 9600, "path", "복도 상단"),           # N5
            (8000, 6400, "path", "복도 중앙"),           # N6
            (8000, 3200, "path", "복도 하단"),           # N7

            # 화장실 앞
            (10000, 9600, "path", "남자화장실 앞"),       # N8
            (14000, 9600, "path", "여자화장실 앞"),       # N9

            # 계단 (중앙)
            (12000, 6400, "stair", "중앙계단 1F"),       # N10
            (16000, 3200, "stair", "중앙계단2 1F"),      # N11

            # 식당/카페 영역 (X3~X4, 상단)
            (20000, 9600, "path", "식당 입구"),           # N12
            (20000, 6400, "path", "식당 중앙"),           # N13

            # 관리사무실 (X4~X5, 상단)
            (27000, 9600, "path", "관리사무실 입구"),     # N14
            (27000, 6400, "path", "관리사무실 내부"),     # N15

            # 강의실 (X1~X2, 하단)
            (4000, 3200, "path", "강의실 입구"),          # N16
            (4000, 1600, "path", "강의실 내부"),          # N17

            # 우측 하단 복도
            (16000, 6400, "path", "중앙 교차점"),         # N18
            (24000, 6400, "path", "우측 복도"),           # N19
            (30000, 3200, "path", "비상계단 입구"),       # N20

            # 상단 횡복도 (Y2 라인 근처)
            (16000, 9600, "path", "상단복도 중앙"),       # N21
            (24000, 9600, "path", "상단복도 우측"),       # N22
        ]

        nodes_1f = []
        for x, y, ntype, label in nodes_1f_data:
            node = FloorNode(floor_id=f_1f.id, x=x, y=y, node_type=ntype, label=label)
            db.add(node)
            nodes_1f.append(node)
        db.flush()

        # ============================================================
        # 1F 엣지 (이동 가능 경로)
        # ============================================================
        print("[5/8] 1F 엣지 등록...")

        edges_1f_data = [
            # 정문 → 로비
            (0, 3),    # 정문 → 로비 중앙
            # 로비 내부
            (3, 4),    # 로비 중앙 → 로비→복도 연결
            (4, 5),    # 로비→복도 연결 → 복도 상단
            # 복도 종축 (상하)
            (5, 6),    # 복도 상단 → 복도 중앙
            (6, 7),    # 복도 중앙 → 복도 하단
            # 상단 횡복도
            (5, 8),    # 복도 상단 → 남자화장실 앞
            (8, 9),    # 남자화장실 앞 → 여자화장실 앞
            (9, 21),   # 여자화장실 앞 → 상단복도 중앙
            (21, 12),  # 상단복도 중앙 → 식당 입구
            (12, 22),  # 식당 입구 → 상단복도 우측
            (22, 14),  # 상단복도 우측 → 관리사무실 입구
            # 중앙 횡복도
            (6, 10),   # 복도 중앙 → 중앙계단
            (10, 18),  # 중앙계단 → 중앙 교차점
            (18, 13),  # 중앙 교차점 → 식당 중앙
            (18, 19),  # 중앙 교차점 → 우측 복도
            (19, 15),  # 우측 복도 → 관리사무실 내부
            (19, 20),  # 우측 복도 → 비상계단 입구
            (20, 2),   # 비상계단 입구 → 비상계단 출구
            # 식당 내부
            (12, 13),  # 식당 입구 → 식당 중앙
            # 관리사무실 내부
            (14, 15),  # 관리사무실 입구 → 관리사무실 내부
            # 강의실 연결
            (7, 16),   # 복도 하단 → 강의실 입구
            (16, 17),  # 강의실 입구 → 강의실 내부
            # 하단계단 연결
            (7, 11),   # 복도 하단 → 중앙계단2
            (11, 18),  # 중앙계단2 → 중앙 교차점
            # 후문 연결
            (11, 1),   # 중앙계단2 → 후문
        ]

        for from_idx, to_idx in edges_1f_data:
            n1 = nodes_1f[from_idx]
            n2 = nodes_1f[to_idx]
            dist = ((n1.x - n2.x) ** 2 + (n1.y - n2.y) ** 2) ** 0.5
            edge = FloorEdge(floor_id=f_1f.id, from_node_id=n1.id, to_node_id=n2.id, distance=round(dist, 1), is_blocked=0)
            db.add(edge)

        # ============================================================
        # 2F 노드/엣지 (간소화)
        # ============================================================
        print("[5/8] 2F/3F 노드/엣지 등록...")

        nodes_2f_data = [
            (12000, 6400, "stair", "중앙계단 2F"),       # 0
            (16000, 3200, "stair", "중앙계단2 2F"),      # 1
            (30000, 6400, "exit", "비상계단 2F"),         # 2
            (4000, 6400, "path", "교육실 2-1"),           # 3
            (12000, 9600, "path", "교육실 2-2"),          # 4
            (20000, 6400, "path", "라운지"),              # 5
            (27000, 6400, "path", "휴게공간"),            # 6
            (8000, 6400, "path", "2F 복도 좌"),           # 7
            (24000, 6400, "path", "2F 복도 우"),          # 8
        ]

        nodes_2f = []
        for x, y, ntype, label in nodes_2f_data:
            node = FloorNode(floor_id=f_2f.id, x=x, y=y, node_type=ntype, label=label)
            db.add(node)
            nodes_2f.append(node)
        db.flush()

        edges_2f_data = [
            (3, 7), (7, 0), (0, 4), (0, 1), (7, 1),
            (1, 5), (5, 8), (8, 6), (8, 2),
        ]
        for fi, ti in edges_2f_data:
            n1, n2 = nodes_2f[fi], nodes_2f[ti]
            dist = ((n1.x - n2.x) ** 2 + (n1.y - n2.y) ** 2) ** 0.5
            db.add(FloorEdge(floor_id=f_2f.id, from_node_id=n1.id, to_node_id=n2.id, distance=round(dist, 1), is_blocked=0))

        # ============================================================
        # 3F 노드/엣지
        # ============================================================
        nodes_3f_data = [
            (12000, 6400, "stair", "중앙계단 3F"),       # 0
            (16000, 3200, "stair", "중앙계단2 3F"),      # 1
            (30000, 6400, "exit", "비상계단 3F"),         # 2
            (4000, 6400, "path", "교육실 3-1"),           # 3
            (12000, 9600, "path", "교육실 3-2"),          # 4
            (20000, 6400, "path", "회의실"),              # 5
            (27000, 6400, "path", "휴게공간 3F"),         # 6
            (8000, 6400, "path", "3F 복도 좌"),           # 7
            (24000, 6400, "path", "3F 복도 우"),          # 8
        ]

        nodes_3f = []
        for x, y, ntype, label in nodes_3f_data:
            node = FloorNode(floor_id=f_3f.id, x=x, y=y, node_type=ntype, label=label)
            db.add(node)
            nodes_3f.append(node)
        db.flush()

        edges_3f_data = [
            (3, 7), (7, 0), (0, 4), (0, 1), (7, 1),
            (1, 5), (5, 8), (8, 6), (8, 2),
        ]
        for fi, ti in edges_3f_data:
            n1, n2 = nodes_3f[fi], nodes_3f[ti]
            dist = ((n1.x - n2.x) ** 2 + (n1.y - n2.y) ** 2) ** 0.5
            db.add(FloorEdge(floor_id=f_3f.id, from_node_id=n1.id, to_node_id=n2.id, distance=round(dist, 1), is_blocked=0))

        # ============================================================
        # 층간 연결 (계단 엣지 — 같은 위치의 계단 노드끼리 연결)
        # ============================================================
        print("[6/8] 층간 계단 연결...")

        # 중앙계단: 1F N10 ↔ 2F[0] ↔ 3F[0]
        db.add(FloorEdge(floor_id=f_1f.id, from_node_id=nodes_1f[10].id, to_node_id=nodes_2f[0].id, distance=4400.0, is_blocked=0))
        db.add(FloorEdge(floor_id=f_2f.id, from_node_id=nodes_2f[0].id, to_node_id=nodes_3f[0].id, distance=4400.0, is_blocked=0))

        # 중앙계단2: 1F N11 ↔ 2F[1] ↔ 3F[1]
        db.add(FloorEdge(floor_id=f_1f.id, from_node_id=nodes_1f[11].id, to_node_id=nodes_2f[1].id, distance=4400.0, is_blocked=0))
        db.add(FloorEdge(floor_id=f_2f.id, from_node_id=nodes_2f[1].id, to_node_id=nodes_3f[1].id, distance=4400.0, is_blocked=0))

        # 비상계단: 1F N20 ↔ 2F[2] ↔ 3F[2]  (→ 비상출구)
        db.add(FloorEdge(floor_id=f_1f.id, from_node_id=nodes_1f[20].id, to_node_id=nodes_2f[2].id, distance=4400.0, is_blocked=0))
        db.add(FloorEdge(floor_id=f_2f.id, from_node_id=nodes_2f[2].id, to_node_id=nodes_3f[2].id, distance=4400.0, is_blocked=0))

        # ============================================================
        # GPS 앵커 (1F 기준 — 가상 GPS 좌표)
        # ============================================================
        print("[7/8] GPS 앵커 등록 (1F)...")

        # 가상 매핑: 건물 좌하단(0,0) = GPS(37.4970, 127.0270)
        #           건물 우상단(30000,12800) = GPS(37.4982, 127.0300)
        anchors = [
            FloorAnchor(floor_id=f_1f.id, px_x=0.0, px_y=0.0, gps_lat=37.4970, gps_lng=127.0270, label="좌하단 (Y1,X1)"),
            FloorAnchor(floor_id=f_1f.id, px_x=30000.0, px_y=12800.0, gps_lat=37.4982, gps_lng=127.0300, label="우상단 (Y2,X5)"),
        ]
        db.add_all(anchors)

        # ============================================================
        # 근로자 초기 위치
        # ============================================================
        print("[8/8] 근로자 초기 위치 배치...")

        now = datetime.now(timezone.utc)
        worker_positions = [
            # (user_idx, floor, x, y, description)
            (2, f_1f, 4000.0, 1600.0),    # 박민수 → 1F 강의실 내부
            (3, f_1f, 20000.0, 9600.0),   # 최지연 → 1F 식당
            (4, f_2f, 4000.0, 6400.0),    # 정도현 → 2F 교육실 2-1
            (5, f_2f, 20000.0, 6400.0),   # 이수진 → 2F 라운지
            (6, f_3f, 20000.0, 6400.0),   # 한동우 → 3F 회의실
        ]

        for user_idx, floor, x, y in worker_positions:
            user = users[user_idx]
            db.add(WorkerLocation(user_id=user.id, floor_id=floor.id, x=x, y=y))
            db.add(EvacuationStatus(
                user_id=user.id,
                status="in_building",
                last_floor_id=floor.id,
                last_x=x,
                last_y=y,
                is_moving=True,
                updated_at=now,
            ))

        db.commit()

        # ============================================================
        # Gate 노드 추가 (출퇴근 자동 인식용)
        # ============================================================
        print("[추가] Gate 노드 등록 (1F 출입구)...")
        gate_nodes = [
            FloorNode(floor_id=f_1f.id, x=4000, y=12800, node_type="gate", label="정문 게이트"),
            FloorNode(floor_id=f_1f.id, x=16000, y=0, node_type="gate", label="후문 게이트"),
        ]
        db.add_all(gate_nodes)
        db.commit()

        # ============================================================
        # 건강 Baseline 초기 데이터 (유저당 50개)
        # ============================================================
        print("[추가] 건강 baseline 초기 데이터 생성...")
        import random
        from app.models.health_data import HealthRecord, HealthBaseline

        for user_idx in [2, 3, 4, 5, 6]:  # worker 5명
            user = users[user_idx]
            hr_values = []
            temp_values = []
            for i in range(50):
                hr = random.randint(62, 82)
                temp = round(random.uniform(36.2, 36.8), 1)
                hr_values.append(hr)
                temp_values.append(temp)
                db.add(HealthRecord(user_id=user.id, heart_rate=hr, temperature=temp))

            # Baseline 계산
            import statistics
            avg_hr = statistics.mean(hr_values)
            std_hr = statistics.stdev(hr_values)
            avg_temp = statistics.mean(temp_values)
            std_temp = statistics.stdev(temp_values)
            db.add(HealthBaseline(
                user_id=user.id,
                avg_hr=avg_hr,
                std_hr=std_hr,
                avg_temp=avg_temp,
                std_temp=std_temp,
                sample_count=50,
                anomaly_count=0,
            ))

        db.commit()
        print(f"  → 5명 × 50개 = 250개 건강 기록 + baseline 생성 완료")

        # ============================================================
        # 결과 출력
        # ============================================================
        print("\n" + "=" * 50)
        print("시드 데이터 등록 완료!")
        print("=" * 50)
        print(f"\n건물: {building.name}")
        print(f"주소: {building.address}")
        print(f"\n층 구성:")
        for f in floors:
            node_count = db.query(FloorNode).filter(FloorNode.floor_id == f.id).count()
            edge_count = db.query(FloorEdge).filter(FloorEdge.floor_id == f.id).count()
            plan = f.floor_plan_url or "(도면 미등록)"
            print(f"  {f.name}: 노드 {node_count}개, 엣지 {edge_count}개 | {plan}")

        print(f"\nGPS 앵커: 2개 (1F)")
        print(f"\n로그인 정보 (모든 계정 비밀번호: demo1234):")
        print("-" * 50)
        for u in users:
            print(f"  {u.role.value:8s} | {u.email:20s} | {u.name}")
        print("-" * 50)
        print(f"\n서버 시작: cd backend && python -m uvicorn app.main:app --reload")
        print(f"Swagger UI: http://localhost:8000/docs")

    except Exception as e:
        db.rollback()
        print(f"\nERROR: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
