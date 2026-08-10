import { useEffect, useState, useCallback } from "react";
import api, { getStoredAuth } from "../hooks/useApi";
import { useWebSocket, WSMessage } from "../hooks/useWebSocket";
import FloorCanvas, {
  NodeData,
  EdgeData,
  WorkerMarker,
  FireZone,
} from "../components/FloorCanvas";

interface PeerInfo {
  user_id: number;
  name?: string | null;
  x: number;
  y: number;
  distance: number;
  status: string;
  heart_rate?: number | null;
  is_moving?: boolean | null;
  sos_sent?: boolean | null;
}

interface Floor {
  id: number;
  floor_number: number;
  name?: string | null;
  width?: number | null;
  height?: number | null;
  floor_plan_url?: string | null;
}

export default function PeerMap() {
  const { userId, role } = getStoredAuth();
  const parsedUserId = userId ? parseInt(userId, 10) : 0;

  const [floors, setFloors] = useState<Floor[]>([]);
  const [selectedFloorId, setSelectedFloorId] = useState<number | null>(null);
  const [nodes, setNodes] = useState<NodeData[]>([]);
  const [edges, setEdges] = useState<EdgeData[]>([]);
  const [fireZones, setFireZones] = useState<FireZone[]>([]);
  const [peers, setPeers] = useState<PeerInfo[]>([]);
  const [myPos, setMyPos] = useState<{ x: number; y: number } | null>(null);
  const [loading, setLoading] = useState(false);

  // 내 위치 및 층 로드
  useEffect(() => {
    async function loadMyLocation() {
      try {
        const res = await api.get(`/api/locations/current/${parsedUserId}`);
        const data = res.data;
        if (data.floor_id) setSelectedFloorId(data.floor_id);
        if (data.x != null && data.y != null) setMyPos({ x: data.x, y: data.y });
      } catch {
        // 위치 없으면 기본 층 로드
        loadDefaultFloor();
      }
    }
    async function loadDefaultFloor() {
      try {
        const bRes = await api.get("/api/buildings/");
        if (bRes.data.length > 0) {
          const fRes = await api.get(`/api/buildings/${bRes.data[0].id}/floors`);
          setFloors(fRes.data);
          const f1 = fRes.data.find((f: Floor) => f.floor_number === 1);
          if (f1) setSelectedFloorId(f1.id);
          else if (fRes.data.length > 0) setSelectedFloorId(fRes.data[0].id);
        }
      } catch { /* ignore */ }
    }
    if (parsedUserId) loadMyLocation();
  }, [parsedUserId]);

  // 층 목록 로드
  useEffect(() => {
    async function loadFloors() {
      try {
        const bRes = await api.get("/api/buildings/");
        if (bRes.data.length > 0) {
          const fRes = await api.get(`/api/buildings/${bRes.data[0].id}/floors`);
          setFloors(fRes.data);
        }
      } catch { /* ignore */ }
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

  // 화재 구역
  useEffect(() => {
    if (!selectedFloorId) return;
    async function loadFires() {
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
    loadFires();
  }, [selectedFloorId]);

  // 근처 동료 조회
  useEffect(() => {
    if (!parsedUserId) return;
    async function loadPeers() {
      setLoading(true);
      try {
        const res = await api.get(`/api/peers/nearby/${parsedUserId}`, {
          params: { radius: 100000 }, // 전체 층 범위 (100m)
        });
        setPeers(res.data);
      } catch {
        setPeers([]);
      } finally {
        setLoading(false);
      }
    }
    loadPeers();
    const interval = setInterval(loadPeers, 5000);
    return () => clearInterval(interval);
  }, [parsedUserId]);

  // WebSocket
  const handleWSMessage = useCallback(
    (msg: WSMessage) => {
      if (msg.type === "worker_location" || msg.type === "unconscious_detected" || msg.type === "peer_sos") {
        // 동료 목록 갱신
        api.get(`/api/peers/nearby/${parsedUserId}`, { params: { radius: 100000 } })
          .then((res) => setPeers(res.data))
          .catch(() => {});
      }
    },
    [parsedUserId]
  );

  useWebSocket({
    userId: parsedUserId,
    role: role || "worker",
    autoConnect: !!userId,
    onMessage: handleWSMessage,
  });

  // FloorCanvas용 worker markers
  const workerMarkers: WorkerMarker[] = [
    // 내 위치
    ...(myPos ? [{ user_id: parsedUserId, x: myPos.x, y: myPos.y, worker_state: "normal" as const }] : []),
    // 동료들
    ...peers.map((p) => ({
      user_id: p.user_id,
      x: p.x,
      y: p.y,
      status: p.status,
      is_moving: p.is_moving ?? undefined,
      worker_state: p.status === "unconscious" || p.sos_sent
        ? "rescue_needed" as const
        : p.is_moving === false
        ? "at_risk" as const
        : "normal" as const,
    })),
  ];

  const selectedFloor = floors.find((f) => f.id === selectedFloorId);
  const dangerPeers = peers.filter((p) => p.status === "unconscious" || p.sos_sent || (p.heart_rate != null && p.heart_rate < 50));

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">동료 위치</h1>

      {/* 위험 동료 알림 배너 */}
      {dangerPeers.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <div className="flex items-center gap-2">
            <span className="text-2xl">⚠️</span>
            <div>
              <p className="font-semibold text-red-700">위험 동료 감지!</p>
              <p className="text-sm text-red-600">
                {dangerPeers.map((p) => p.name || `#${p.user_id}`).join(", ")} — 
                의식불명 또는 이상 심박 감지됨
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 지도 */}
        <div className="bg-white rounded-lg shadow p-4 lg:col-span-2">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold">현재 층 동료 위치</h2>
            <select
              className="px-3 py-1.5 border rounded text-sm"
              value={selectedFloorId || ""}
              onChange={(e) => setSelectedFloorId(Number(e.target.value))}
            >
              {floors.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.name || `${f.floor_number}층`}
                </option>
              ))}
            </select>
          </div>

          <FloorCanvas
            width={selectedFloor?.width || 30000}
            height={selectedFloor?.height || 12800}
            floorPlanUrl={selectedFloor?.floor_plan_url || null}
            nodes={nodes}
            edges={edges}
            workers={workerMarkers}
            fireZones={fireZones}
          />

          <div className="mt-3 flex flex-wrap gap-4 text-xs text-gray-600">
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 bg-blue-500 rounded-full inline-block"></span>
              나 / 정상 동료
            </span>
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 bg-red-600 rounded-full inline-block"></span>
              의식불명 (구조 필요)
            </span>
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 bg-red-500 rounded-full inline-block"></span>
              정지 (위험)
            </span>
          </div>
        </div>

        {/* 동료 목록 */}
        <div className="bg-white rounded-lg shadow p-4">
          <h2 className="text-lg font-semibold mb-4">
            주변 동료 {loading ? "" : `(${peers.length}명)`}
          </h2>

          {peers.length === 0 && !loading ? (
            <p className="text-gray-400 text-sm">주변에 동료가 없습니다.</p>
          ) : (
            <div className="space-y-3">
              {peers.map((peer) => (
                <div
                  key={peer.user_id}
                  className={`p-3 rounded-lg border ${
                    peer.status === "unconscious" || peer.sos_sent
                      ? "border-red-300 bg-red-50"
                      : peer.is_moving === false
                      ? "border-orange-200 bg-orange-50"
                      : "border-gray-200 bg-gray-50"
                  }`}
                >
                  <div className="flex justify-between items-start">
                    <p className="font-medium text-sm">
                      {peer.name || `근로자 #${peer.user_id}`}
                    </p>
                    <StatusBadge status={peer.status} sos={peer.sos_sent} />
                  </div>
                  <div className="mt-1 text-xs text-gray-500 flex gap-3">
                    <span>거리: {(peer.distance / 1000).toFixed(1)}m</span>
                    {peer.heart_rate != null && (
                      <span className={peer.heart_rate < 50 ? "text-red-600 font-medium" : ""}>
                        ❤️ {peer.heart_rate}bpm
                      </span>
                    )}
                    <span>{peer.is_moving ? "이동 중" : "정지"}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function StatusBadge({ status, sos }: { status: string; sos?: boolean | null }) {
  if (sos) return <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-red-100 text-red-700">SOS</span>;
  switch (status) {
    case "unconscious":
      return <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-red-100 text-red-700">의식불명</span>;
    case "in_building":
      return <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-gray-100 text-gray-600">재실</span>;
    case "evacuating":
      return <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-blue-100 text-blue-700">대피 중</span>;
    default:
      return <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-gray-100 text-gray-600">{status}</span>;
  }
}
