import { useEffect, useState, useCallback } from "react";
import api, { getStoredAuth } from "../hooks/useApi";
import { useWebSocket, WSMessage } from "../hooks/useWebSocket";
import FloorCanvas, {
  NodeData,
  EdgeData,
  WorkerMarker,
  FireZone,
} from "../components/FloorCanvas";

interface EvacuationStatusItem {
  user_id: number;
  user_name?: string | null;
  status: string; // in_building, evacuating, evacuated, unconscious
  last_floor_id?: number | null;
  last_x?: number | null;
  last_y?: number | null;
  is_moving?: boolean | null;
  heart_rate?: number | null;
  sos_sent?: boolean | null;
  updated_at?: string | null;
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

// 더미 데이터 (서버 연결 불가 시 fallback)
const DUMMY_EVAC_STATUS: EvacuationStatusItem[] = [
  { user_id: 1, user_name: "김철수", status: "evacuated", last_floor_id: 1, last_x: 5000, last_y: 3000, is_moving: false, heart_rate: 78, sos_sent: false, updated_at: new Date().toISOString() },
  { user_id: 2, user_name: "이영희", status: "in_building", last_floor_id: 1, last_x: 12000, last_y: 5000, is_moving: true, heart_rate: 95, sos_sent: false, updated_at: new Date().toISOString() },
  { user_id: 3, user_name: "박민수", status: "unconscious", last_floor_id: 1, last_x: 20000, last_y: 8000, is_moving: false, heart_rate: 42, sos_sent: false, updated_at: new Date().toISOString() },
  { user_id: 4, user_name: "정소연", status: "in_building", last_floor_id: 1, last_x: 8000, last_y: 9000, is_moving: false, heart_rate: 88, sos_sent: true, updated_at: new Date().toISOString() },
  { user_id: 5, user_name: "최동현", status: "evacuating", last_floor_id: 1, last_x: 25000, last_y: 4000, is_moving: true, heart_rate: 102, sos_sent: false, updated_at: new Date().toISOString() },
];

export default function RescuerView() {
  const [evacuationStatus, setEvacuationStatus] = useState<EvacuationStatusItem[]>(DUMMY_EVAC_STATUS);
  const [floors, setFloors] = useState<Floor[]>([]);
  const [selectedFloorId, setSelectedFloorId] = useState<number | null>(1);
  const [nodes, setNodes] = useState<NodeData[]>([]);
  const [edges, setEdges] = useState<EdgeData[]>([]);
  const [fireZones, setFireZones] = useState<FireZone[]>([]);

  const { userId, role } = getStoredAuth();
  const parsedUserId = userId ? parseInt(userId, 10) : 0;

  // 층 목록 로드
  useEffect(() => {
    async function loadFloors() {
      try {
        const bRes = await api.get("/api/buildings/");
        if (bRes.data.length > 0) {
          const fRes = await api.get(`/api/buildings/${bRes.data[0].id}/floors`);
          setFloors(fRes.data);
          const f1 = fRes.data.find((f: Floor) => f.floor_number === 1);
          if (f1) setSelectedFloorId(f1.id);
          else if (fRes.data.length > 0) setSelectedFloorId(fRes.data[0].id);
        }
      } catch { /* 무시 */ }
    }
    loadFloors();
  }, []);

  // 노드/엣지 로드
  useEffect(() => {
    if (!selectedFloorId) return;
    async function loadGraph() {
      try {
        const [nodesRes, edgesRes] = await Promise.all([
          api.get(`/api/buildings/floors/${selectedFloorId}/nodes`),
          api.get(`/api/buildings/floors/${selectedFloorId}/edges`),
        ]);
        setNodes(nodesRes.data);
        setEdges(edgesRes.data);
      } catch {
        setNodes([]);
        setEdges([]);
      }
    }
    loadGraph();
  }, [selectedFloorId]);

  // 화재 구역 로드
  useEffect(() => {
    if (!selectedFloorId) return;
    async function loadFireZones() {
      try {
        const res = await api.get("/api/alerts/active");
        const zones = (res.data as Array<{ type: string; floor_id?: number; x?: number; y?: number }>)
          .filter((a) => a.type === "fire" && a.floor_id === selectedFloorId && a.x != null && a.y != null)
          .map((a) => ({ x: a.x!, y: a.y!, radius: 50 }));
        setFireZones(zones);
      } catch {
        setFireZones([]);
      }
    }
    loadFireZones();
  }, [selectedFloorId]);

  // 대피 현황 로드
  useEffect(() => {
    async function loadEvacStatus() {
      try {
        const res = await api.get("/api/evacuation/status");
        if (res.data && res.data.length > 0) {
          setEvacuationStatus(res.data);
        }
      } catch { /* 더미 데이터 유지 */ }
    }
    loadEvacStatus();
    const interval = setInterval(loadEvacStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  // WebSocket — 실시간 업데이트
  const handleWSMessage = useCallback(
    (msg: WSMessage) => {
      if (msg.type === "unconscious_detected" || msg.type === "worker_location") {
        // 대피 상태 재로드
        api.get("/api/evacuation/status").then((res) => {
          if (res.data && res.data.length > 0) setEvacuationStatus(res.data);
        }).catch(() => {});
      }
      if (msg.type === "fire_alert" && msg.floor_id === selectedFloorId) {
        if (msg.x != null && msg.y != null) {
          setFireZones((prev) => [...prev, { x: msg.x as number, y: msg.y as number, radius: 50 }]);
        }
      }
    },
    [selectedFloorId]
  );

  useWebSocket({
    userId: parsedUserId,
    role: role || "rescuer",
    autoConnect: !!userId,
    onMessage: handleWSMessage,
  });

  // 미대피자 필터 (대피 완료가 아닌 사람들)
  const notEvacuated = evacuationStatus.filter((s) => s.status !== "evacuated");
  const unconscious = evacuationStatus.filter((s) => s.status === "unconscious");
  const sosUsers = evacuationStatus.filter((s) => s.sos_sent);
  const evacuated = evacuationStatus.filter((s) => s.status === "evacuated");

  // 현재 선택된 층의 미대피자를 WorkerMarker로 변환
  const floorWorkers: WorkerMarker[] = notEvacuated
    .filter((s) => s.last_floor_id === selectedFloorId && s.last_x != null && s.last_y != null)
    .map((s) => ({
      user_id: s.user_id,
      x: s.last_x!,
      y: s.last_y!,
      status: s.status,
      is_moving: s.is_moving ?? false,
      worker_state: s.status === "unconscious" ? "rescue_needed" : s.is_moving ? "normal" : "at_risk",
    }));

  // 상태에 따른 색상 뱃지
  function getStatusBadge(status: string, sos?: boolean | null) {
    if (sos) return <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-yellow-100 text-yellow-700">SOS</span>;
    switch (status) {
      case "unconscious":
        return <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-red-100 text-red-700">의식불명</span>;
      case "in_building":
        return <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-orange-100 text-orange-700">재실</span>;
      case "evacuating":
        return <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-blue-100 text-blue-700">대피 중</span>;
      case "evacuated":
        return <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-green-100 text-green-700">대피 완료</span>;
      default:
        return <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-gray-100 text-gray-700">{status}</span>;
    }
  }

  const selectedFloor = floors.find((f) => f.id === selectedFloorId);

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">구조대 현황</h1>

      {/* 미대피자 요약 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-sm text-red-600">의식 불명</p>
          <p className="text-3xl font-bold text-red-700">{unconscious.length}</p>
        </div>
        <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
          <p className="text-sm text-orange-600">미대피 (재실)</p>
          <p className="text-3xl font-bold text-orange-700">{notEvacuated.length}</p>
        </div>
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <p className="text-sm text-yellow-600">SOS 요청</p>
          <p className="text-3xl font-bold text-yellow-700">{sosUsers.length}</p>
        </div>
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <p className="text-sm text-green-600">대피 완료</p>
          <p className="text-3xl font-bold text-green-700">{evacuated.length}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 도면 위 미대피자 위치 */}
        <div className="bg-white rounded-lg shadow p-4 lg:col-span-2">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold">미대피자 위치</h2>
            {/* 층 선택 */}
            <select
              className="px-3 py-1.5 border rounded text-sm"
              value={selectedFloorId || ""}
              onChange={(e) => setSelectedFloorId(Number(e.target.value))}
            >
              {floors.length > 0 ? (
                floors.map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.name || `${f.floor_number}층`}
                  </option>
                ))
              ) : (
                <option value={1}>1층</option>
              )}
            </select>
          </div>

          <FloorCanvas
            width={selectedFloor?.width || 30000}
            height={selectedFloor?.height || 12800}
            floorPlanUrl={selectedFloor?.floor_plan_url || null}
            nodes={nodes}
            edges={edges}
            workers={floorWorkers}
            fireZones={fireZones}
          />

          {/* 범례 */}
          <div className="mt-3 flex flex-wrap gap-4 text-xs text-gray-600">
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 bg-blue-500 rounded-full inline-block"></span>
              정상 이동
            </span>
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 bg-red-600 rounded-full inline-block"></span>
              의식불명/구조필요
            </span>
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 bg-red-500 rounded-full inline-block"></span>
              정지/위험
            </span>
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 bg-red-500 rounded-full inline-block opacity-30"></span>
              화재 구역
            </span>
          </div>
        </div>

        {/* 미대피자 목록 */}
        <div className="bg-white rounded-lg shadow p-4 overflow-y-auto max-h-[600px]">
          <h2 className="text-lg font-semibold mb-4">미대피자 목록 ({notEvacuated.length}명)</h2>

          {notEvacuated.length === 0 ? (
            <p className="text-gray-400 text-sm">미대피자가 없습니다.</p>
          ) : (
            <div className="space-y-3">
              {notEvacuated.map((person) => (
                <div
                  key={person.user_id}
                  className={`p-3 rounded-lg border transition ${
                    person.status === "unconscious"
                      ? "border-red-300 bg-red-50"
                      : person.sos_sent
                      ? "border-yellow-300 bg-yellow-50"
                      : "border-gray-200 bg-gray-50"
                  }`}
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="font-medium text-sm">
                        {person.user_name || `근로자 #${person.user_id}`}
                      </p>
                      <p className="text-xs text-gray-500 mt-0.5">
                        {person.last_floor_id ? `${person.last_floor_id}층` : "위치 미상"}
                        {person.is_moving ? " · 이동 중" : " · 정지"}
                      </p>
                    </div>
                    {getStatusBadge(person.status, person.sos_sent)}
                  </div>
                  <div className="mt-2 flex items-center gap-3 text-xs text-gray-500">
                    {person.heart_rate != null && (
                      <span className={person.heart_rate < 50 ? "text-red-600 font-medium" : ""}>
                        ❤️ {person.heart_rate} bpm
                      </span>
                    )}
                    {person.updated_at && (
                      <span>
                        🕒 {new Date(person.updated_at).toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit" })}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          <hr className="my-4" />

          <h3 className="font-semibold mb-2">활성 SOS ({sosUsers.length}건)</h3>
          {sosUsers.length === 0 ? (
            <p className="text-gray-400 text-sm">활성 SOS가 없습니다.</p>
          ) : (
            <div className="space-y-2">
              {sosUsers.map((u) => (
                <div key={u.user_id} className="p-2 bg-yellow-50 border border-yellow-200 rounded text-sm">
                  <span className="font-medium">{u.user_name || `#${u.user_id}`}</span>
                  <span className="ml-2 text-xs text-yellow-600">
                    {u.last_floor_id ? `${u.last_floor_id}층` : ""}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
