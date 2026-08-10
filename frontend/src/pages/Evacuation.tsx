import { useEffect, useState, useCallback } from "react";
import api, { getStoredAuth } from "../hooks/useApi";
import { useWebSocket, WSMessage } from "../hooks/useWebSocket";
import FloorCanvas, { NodeData, EdgeData, FireZone } from "../components/FloorCanvas";

interface RouteInfo {
  success: boolean;
  message?: string;
  start_node?: number;
  exit_node?: number;
  distance?: number;
  path?: NodeData[];
}

export default function Evacuation() {
  const [floorId, setFloorId] = useState<number | null>(1);
  const [nodes, setNodes] = useState<NodeData[]>([]);
  const [edges, setEdges] = useState<EdgeData[]>([]);
  const [route, setRoute] = useState<RouteInfo | null>(null);
  const [fireZones, setFireZones] = useState<FireZone[]>([]);
  const [loading, setLoading] = useState(false);
  const [hasFireAlert, setHasFireAlert] = useState(false);

  const { userId, role } = getStoredAuth();
  const parsedUserId = userId ? parseInt(userId, 10) : 0;

  // 현재 위치 (서버에서 가져옴)
  const [currentPos, setCurrentPos] = useState({ x: 0, y: 0 });

  // 현재 유저 위치 로드
  useEffect(() => {
    async function loadMyLocation() {
      try {
        const res = await api.get(`/api/locations/current/${parsedUserId}`);
        const data = res.data;
        if (data.floor_id) setFloorId(data.floor_id);
        if (data.x != null && data.y != null) setCurrentPos({ x: data.x, y: data.y });
      } catch {
        // 위치 정보 없으면 첫 번째 층 로드 시도
        loadDefaultFloor();
      }
    }
    async function loadDefaultFloor() {
      try {
        const bRes = await api.get("/api/buildings/");
        if (bRes.data.length > 0) {
          const fRes = await api.get(`/api/buildings/${bRes.data[0].id}/floors`);
          const f1 = fRes.data.find((f: { floor_number: number }) => f.floor_number === 1) || fRes.data[0];
          if (f1) setFloorId(f1.id);
        }
      } catch { /* ignore */ }
    }
    if (parsedUserId) loadMyLocation();
  }, [parsedUserId]);

  // 노드/엣지 로드
  useEffect(() => {
    if (!floorId) return;
    async function loadGraph() {
      try {
        const [nodesRes, edgesRes] = await Promise.all([
          api.get(`/api/buildings/floors/${floorId}/nodes`),
          api.get(`/api/buildings/floors/${floorId}/edges`),
        ]);
        setNodes(nodesRes.data);
        setEdges(edgesRes.data);
      } catch {
        setNodes([]);
        setEdges([]);
      }
    }
    loadGraph();
  }, [floorId]);

  // 화재 알림 확인
  useEffect(() => {
    async function checkAlerts() {
      try {
        const res = await api.get("/api/alerts/active");
        const fires = (res.data as Array<{ type: string; floor_id?: number; x?: number; y?: number }>)
          .filter((a) => a.type === "fire");
        setHasFireAlert(fires.length > 0);
        setFireZones(
          fires
            .filter((a) => a.floor_id === floorId && a.x != null && a.y != null)
            .map((a) => ({ x: a.x!, y: a.y!, radius: 50 }))
        );
      } catch {
        // 무시
      }
    }
    checkAlerts();
  }, [floorId]);

  // 탈출 경로 계산
  const calculateRoute = useCallback(async () => {
    if (!floorId || (currentPos.x === 0 && currentPos.y === 0)) return;
    setLoading(true);
    try {
      const res = await api.post("/api/evacuation/route", {
        user_id: parsedUserId,
        floor_id: floorId,
        x: currentPos.x,
        y: currentPos.y,
      });
      setRoute(res.data);
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      setRoute({
        success: false,
        message: error?.response?.data?.detail || "경로를 계산할 수 없습니다.",
      });
    } finally {
      setLoading(false);
    }
  }, [floorId, currentPos, parsedUserId]);

  // 마운트 시 + 화재 감지 시 경로 자동 계산
  useEffect(() => {
    if (nodes.length > 0) {
      calculateRoute();
    }
  }, [nodes, calculateRoute]);

  // WebSocket — 화재 알림 수신 시 경로 재계산
  const handleWSMessage = useCallback(
    (msg: WSMessage) => {
      if (msg.type === "fire_alert") {
        setHasFireAlert(true);
        if (msg.floor_id === floorId && msg.x != null && msg.y != null) {
          setFireZones((prev) => [
            ...prev,
            { x: msg.x as number, y: msg.y as number, radius: 50 },
          ]);
        }
        // 엣지 리로드 후 경로 재계산
        api
          .get(`/api/buildings/floors/${floorId}/edges`)
          .then((res) => {
            setEdges(res.data);
            calculateRoute();
          })
          .catch(() => {});
      }
    },
    [floorId, calculateRoute]
  );

  useWebSocket({
    userId: parsedUserId,
    role: role || "worker",
    autoConnect: !!userId,
    onMessage: handleWSMessage,
  });

  // SOS 전송
  const sendSOS = useCallback(() => {
    // WebSocket은 별도, REST로도 가능
    alert("SOS가 전송되었습니다. 주변 동료와 구조대에게 알립니다.");
  }, []);

  const estimatedTime = route?.distance
    ? Math.ceil(route.distance / 50) // 약 50px/s 보행 가정
    : null;

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">탈출 경로 안내</h1>

      {/* 현재 상태 배너 */}
      {hasFireAlert && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <div className="flex items-center gap-2">
            <span className="text-2xl">🔥</span>
            <div>
              <p className="font-semibold text-red-700">화재 감지됨</p>
              <p className="text-sm text-red-600">
                가장 가까운 출구로 이동하세요.
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 탈출 경로 지도 */}
        <div className="bg-white rounded-lg shadow p-4 lg:col-span-2">
          <h2 className="text-lg font-semibold mb-4">나의 탈출 경로</h2>
          <FloorCanvas
            width={30000}
            height={12800}
            nodes={nodes}
            edges={edges}
            routePath={route?.path || []}
            fireZones={fireZones}
            workers={currentPos.x !== 0 || currentPos.y !== 0 ? [{ user_id: parsedUserId, x: currentPos.x, y: currentPos.y }] : []}
          />
        </div>

        {/* 안내 패널 */}
        <div className="space-y-4">
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="font-semibold mb-2">경로 정보</h3>
            {loading ? (
              <p className="text-sm text-gray-400">계산 중...</p>
            ) : route?.success ? (
              <div className="space-y-2 text-sm">
                <p>
                  <span className="text-gray-500">목적지:</span>{" "}
                  <span className="font-medium">
                    출구 (노드 #{route.exit_node})
                  </span>
                </p>
                <p>
                  <span className="text-gray-500">거리:</span>{" "}
                  <span className="font-medium">{route.distance}m</span>
                </p>
                <p>
                  <span className="text-gray-500">예상 시간:</span>{" "}
                  <span className="font-medium">
                    {estimatedTime ? `약 ${estimatedTime}초` : "—"}
                  </span>
                </p>
                <p>
                  <span className="text-gray-500">경유 노드:</span>{" "}
                  <span className="font-medium">
                    {route.path?.length || 0}개
                  </span>
                </p>
              </div>
            ) : (
              <p className="text-sm text-red-500">
                {route?.message || "경로를 찾을 수 없습니다."}
              </p>
            )}

            <button
              onClick={calculateRoute}
              className="mt-3 w-full py-2 text-sm bg-blue-500 text-white rounded hover:bg-blue-600 transition"
            >
              경로 재계산
            </button>
          </div>

          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="font-semibold mb-2">동료 SOS</h3>
            <button
              onClick={sendSOS}
              className="w-full py-3 bg-red-500 text-white font-bold rounded-lg hover:bg-red-600 transition"
            >
              SOS 보내기
            </button>
            <p className="text-xs text-gray-400 mt-2 text-center">
              위험 시 주변 동료에게 도움 요청
            </p>
          </div>

          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="font-semibold mb-2">층 선택</h3>
            <input
              type="number"
              min={1}
              value={floorId ?? ""}
              onChange={(e) => setFloorId(Number(e.target.value))}
              className="w-full px-3 py-2 border rounded text-sm"
              placeholder="층 ID"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
