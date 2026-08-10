import { useEffect, useState, useCallback } from "react";
import api, { getStoredAuth } from "../hooks/useApi";
import { useWebSocket, WSMessage } from "../hooks/useWebSocket";
import FloorCanvas, {
  NodeData,
  EdgeData,
  WorkerMarker,
  FireZone,
} from "../components/FloorCanvas";

interface Building {
  id: number;
  name: string;
  total_floors: number;
}

interface Floor {
  id: number;
  building_id: number;
  floor_number: number;
  name?: string | null;
  floor_plan_url?: string | null;
  width?: number | null;
  height?: number | null;
}

export default function FloorPlan() {
  const [buildings, setBuildings] = useState<Building[]>([]);
  const [floors, setFloors] = useState<Floor[]>([]);
  const [selectedBuilding, setSelectedBuilding] = useState<number | null>(null);
  const [selectedFloor, setSelectedFloor] = useState<Floor | null>(null);
  const [nodes, setNodes] = useState<NodeData[]>([]);
  const [edges, setEdges] = useState<EdgeData[]>([]);
  const [workers, setWorkers] = useState<WorkerMarker[]>([]);
  const [fireZones, setFireZones] = useState<FireZone[]>([]);
  const [loading, setLoading] = useState(false);

  const { userId, role } = getStoredAuth();
  const parsedUserId = userId ? parseInt(userId, 10) : 0;

  // 건물 목록 로드
  useEffect(() => {
    async function loadBuildings() {
      try {
        const res = await api.get("/api/buildings/");
        setBuildings(res.data);
        if (res.data.length > 0) {
          setSelectedBuilding(res.data[0].id);
        }
      } catch {
        // 로드 실패 시 무시
      }
    }
    loadBuildings();
  }, []);

  // 층 목록 로드
  useEffect(() => {
    if (!selectedBuilding) return;
    async function loadFloors() {
      try {
        const res = await api.get(`/api/buildings/${selectedBuilding}/floors`);
        setFloors(res.data);
        if (res.data.length > 0) {
          setSelectedFloor(res.data[0]);
        }
      } catch {
        setFloors([]);
      }
    }
    loadFloors();
  }, [selectedBuilding]);

  // 노드/엣지 로드
  useEffect(() => {
    if (!selectedFloor) return;
    async function loadGraph() {
      setLoading(true);
      try {
        const [nodesRes, edgesRes] = await Promise.all([
          api.get(`/api/buildings/floors/${selectedFloor!.id}/nodes`),
          api.get(`/api/buildings/floors/${selectedFloor!.id}/edges`),
        ]);
        setNodes(nodesRes.data);
        setEdges(edgesRes.data);
      } catch {
        setNodes([]);
        setEdges([]);
      } finally {
        setLoading(false);
      }
    }
    loadGraph();
  }, [selectedFloor]);

  // 재실자 위치 로드
  useEffect(() => {
    if (!selectedFloor) return;
    async function loadWorkers() {
      try {
        const res = await api.get(`/api/locations/floor/${selectedFloor!.id}`);
        setWorkers(
          res.data.map((w: { user_id: number; x: number; y: number; status?: string; is_moving?: boolean }) => ({
            user_id: w.user_id,
            x: w.x,
            y: w.y,
            status: w.status,
            is_moving: w.is_moving,
          }))
        );
      } catch {
        setWorkers([]);
      }
    }
    loadWorkers();
  }, [selectedFloor]);

  // 화재 구역 로드
  useEffect(() => {
    async function loadFireZones() {
      try {
        const res = await api.get("/api/alerts/active");
        const zones = (res.data as Array<{ type: string; floor_id?: number; x?: number; y?: number }>)
          .filter(
            (a) =>
              a.type === "fire" &&
              a.floor_id === selectedFloor?.id &&
              a.x != null &&
              a.y != null
          )
          .map((a) => ({ x: a.x!, y: a.y!, radius: 50 }));
        setFireZones(zones);
      } catch {
        setFireZones([]);
      }
    }
    if (selectedFloor) loadFireZones();
  }, [selectedFloor]);

  // WebSocket — 근로자 위치 실시간 업데이트
  const handleWSMessage = useCallback(
    (msg: WSMessage) => {
      if (msg.type === "worker_location" && msg.floor_id === selectedFloor?.id) {
        setWorkers((prev) => {
          const filtered = prev.filter((w) => w.user_id !== (msg.user_id as number));
          return [
            ...filtered,
            {
              user_id: msg.user_id as number,
              x: msg.x as number,
              y: msg.y as number,
            },
          ];
        });
      }

      if (msg.type === "fire_alert" && msg.floor_id === selectedFloor?.id) {
        if (msg.x != null && msg.y != null) {
          setFireZones((prev) => [
            ...prev,
            { x: msg.x as number, y: msg.y as number, radius: 50 },
          ]);
        }
        // 엣지 리로드 (차단 상태 변경)
        if (selectedFloor) {
          api
            .get(`/api/buildings/floors/${selectedFloor.id}/edges`)
            .then((res) => setEdges(res.data))
            .catch(() => {});
        }
      }
    },
    [selectedFloor]
  );

  useWebSocket({
    userId: parsedUserId,
    role: role || "admin",
    autoConnect: !!userId,
    onMessage: handleWSMessage,
  });

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">도면 관리</h1>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* 층 선택 사이드바 */}
        <div className="bg-white rounded-lg shadow p-4">
          <h2 className="text-lg font-semibold mb-4">건물 / 층</h2>

          {/* 건물 선택 */}
          <select
            className="w-full mb-3 px-3 py-2 border rounded text-sm"
            value={selectedBuilding || ""}
            onChange={(e) => setSelectedBuilding(Number(e.target.value))}
          >
            <option value="" disabled>
              건물 선택
            </option>
            {buildings.map((b) => (
              <option key={b.id} value={b.id}>
                {b.name}
              </option>
            ))}
          </select>

          {/* 층 목록 */}
          <div className="space-y-1">
            {floors.length === 0 && (
              <p className="text-gray-400 text-sm">층 정보가 없습니다.</p>
            )}
            {floors.map((f) => (
              <button
                key={f.id}
                onClick={() => setSelectedFloor(f)}
                className={`w-full text-left px-3 py-2 rounded text-sm transition ${
                  selectedFloor?.id === f.id
                    ? "bg-red-100 text-red-700 font-medium"
                    : "hover:bg-gray-100 text-gray-700"
                }`}
              >
                {f.name || `${f.floor_number}층`}
              </button>
            ))}
          </div>

          {/* 통계 */}
          {selectedFloor && (
            <div className="mt-4 pt-4 border-t text-sm text-gray-600 space-y-1">
              <p>노드: {nodes.length}개</p>
              <p>엣지: {edges.length}개</p>
              <p>재실자: {workers.length}명</p>
              <p>
                화재 구역: {fireZones.length}개
              </p>
            </div>
          )}
        </div>

        {/* 도면 뷰 */}
        <div className="bg-white rounded-lg shadow p-4 lg:col-span-3">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold">
              {selectedFloor
                ? `${selectedFloor.name || `${selectedFloor.floor_number}층`} 도면`
                : "도면 뷰"}
            </h2>
          </div>

          {loading ? (
            <div className="h-96 flex items-center justify-center">
              <p className="text-gray-400">로딩 중...</p>
            </div>
          ) : (
            <FloorCanvas
              width={selectedFloor?.width || 800}
              height={selectedFloor?.height || 600}
              floorPlanUrl={selectedFloor?.floor_plan_url || null}
              nodes={nodes}
              edges={edges}
              workers={workers}
              fireZones={fireZones}
            />
          )}

          {/* 범례 */}
          <div className="mt-4 flex flex-wrap gap-4 text-sm text-gray-600">
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 bg-green-500 rounded-full inline-block"></span>{" "}
              출구
            </span>
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 bg-blue-500 rounded-full inline-block"></span>{" "}
              계단
            </span>
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 bg-gray-400 rounded-full inline-block"></span>{" "}
              경로 노드
            </span>
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 bg-red-500 rounded-full inline-block"></span>{" "}
              화재 구역
            </span>
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 bg-blue-500 rounded-full inline-block border-2 border-white"></span>{" "}
              근로자
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
