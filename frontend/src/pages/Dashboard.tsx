import { useEffect, useState, useCallback } from "react";
import api, { getStoredAuth } from "../hooks/useApi";
import { useWebSocket, WSMessage } from "../hooks/useWebSocket";

interface DashboardStats {
  inBuilding: number;
  evacuating: number;
  unconscious: number;
  activeAlerts: number;
  healthAnomalies: number;
  workerStates: {
    normal: number;
    confused: number;
    delayed: number;
    at_risk: number;
    rescue_needed: number;
  };
}

interface AlertFeedItem {
  id: string;
  type: string;
  message: string;
  floor_id?: number;
  timestamp: string;
}

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats>({
    inBuilding: 0,
    evacuating: 0,
    unconscious: 0,
    activeAlerts: 0,
    healthAnomalies: 0,
    workerStates: { normal: 0, confused: 0, delayed: 0, at_risk: 0, rescue_needed: 0 },
  });
  const [alertFeed, setAlertFeed] = useState<AlertFeedItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const { userId, role } = getStoredAuth();

  // 대시보드 데이터 로드
  const fetchStats = useCallback(async () => {
    try {
      const [evacuationRes, unconsciousRes, alertsRes, healthRes] = await Promise.all([
        api.get("/api/evacuation/status"),
        api.get("/api/evacuation/unconscious"),
        api.get("/api/alerts/active"),
        api.get("/api/health/anomalies").catch(() => ({ data: [] })),
      ]);

      const evacuationData = evacuationRes.data as Array<{ status: string; worker_state?: string }>;
      const inBuilding = evacuationData.filter((s) => s.status === "in_building").length;
      const evacuating = evacuationData.filter((s) => s.status === "evacuating").length;

      // worker_state 카운트
      const workerStates = { normal: 0, confused: 0, delayed: 0, at_risk: 0, rescue_needed: 0 };
      for (const s of evacuationData) {
        const state = (s.worker_state || "normal") as keyof typeof workerStates;
        if (state in workerStates) workerStates[state]++;
      }

      setStats({
        inBuilding,
        evacuating,
        unconscious: (unconsciousRes.data as Array<unknown>).length,
        activeAlerts: (alertsRes.data as Array<unknown>).length,
        healthAnomalies: (healthRes.data as Array<unknown>).length,
        workerStates,
      });
      setError(null);
    } catch (err) {
      setError("데이터를 불러올 수 없습니다. 로그인 상태를 확인하세요.");
    } finally {
      setLoading(false);
    }
  }, []);

  // 초기 로드 + 30초마다 폴링
  useEffect(() => {
    fetchStats();
    const interval = setInterval(fetchStats, 30000);
    return () => clearInterval(interval);
  }, [fetchStats]);

  // 기존 알림 이력 로드
  useEffect(() => {
    async function loadAlertHistory() {
      try {
        const res = await api.get("/api/alerts/history?limit=10");
        const history = (res.data as Array<{
          id: number;
          type: string;
          message: string;
          floor_id?: number;
          created_at?: string;
        }>).map((a) => ({
          id: String(a.id),
          type: a.type,
          message: a.message || "",
          floor_id: a.floor_id,
          timestamp: a.created_at || new Date().toISOString(),
        }));
        setAlertFeed(history);
      } catch {
        // 이력 로드 실패 시 무시
      }
    }
    loadAlertHistory();
  }, []);

  // WebSocket 실시간 알림 수신
  const handleWSMessage = useCallback((msg: WSMessage) => {
    if (msg.type === "fire_alert" || msg.type === "sos_alert" || msg.type === "peer_sos" || msg.type === "health_anomaly") {
      const newAlert: AlertFeedItem = {
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        type: msg.type as string,
        message: (msg.message as string) || getAlertLabel(msg.type as string),
        floor_id: msg.floor_id as number | undefined,
        timestamp: new Date().toISOString(),
      };

      setAlertFeed((prev) => [newAlert, ...prev].slice(0, 20));

      if (msg.type === "fire_alert") {
        setStats((prev) => ({ ...prev, activeAlerts: prev.activeAlerts + 1 }));
      }
      if (msg.type === "health_anomaly") {
        setStats((prev) => ({ ...prev, healthAnomalies: prev.healthAnomalies + 1 }));
      }
    }

    if (msg.type === "worker_state_change") {
      // 상태 카운트 즉시 반영
      fetchStats();
    }

    if (msg.type === "evacuation_complete") {
      setStats((prev) => ({
        ...prev,
        inBuilding: Math.max(0, prev.inBuilding - 1),
      }));
    }
  }, [fetchStats]);

  // WebSocket 연결 (userId가 있을 때만)
  const parsedUserId = userId ? parseInt(userId, 10) : 0;
  const { isConnected } = useWebSocket({
    userId: parsedUserId,
    role: role || "admin",
    autoConnect: !!userId,
    onMessage: handleWSMessage,
  });

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">ITDA 관리자 대시보드</h1>
        <div className="flex items-center gap-2">
          <span
            className={`w-2 h-2 rounded-full ${isConnected ? "bg-green-500" : "bg-gray-400"}`}
          />
          <span className="text-xs text-gray-500">
            {isConnected ? "실시간 연결됨" : "연결 대기"}
          </span>
        </div>
      </div>

      {error && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-4">
          <p className="text-sm text-yellow-700">{error}</p>
        </div>
      )}

      {/* 상태 요약 카드 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-white rounded-lg shadow p-4 border-l-4 border-green-500">
          <p className="text-sm text-gray-500">재실 인원</p>
          <p className="text-2xl font-bold">
            {loading ? "..." : stats.inBuilding}
          </p>
        </div>
        <div className="bg-white rounded-lg shadow p-4 border-l-4 border-yellow-500">
          <p className="text-sm text-gray-500">대피 중</p>
          <p className="text-2xl font-bold">
            {loading ? "..." : stats.evacuating}
          </p>
        </div>
        <div className="bg-white rounded-lg shadow p-4 border-l-4 border-red-500">
          <p className="text-sm text-gray-500">미대피 / 위험</p>
          <p className="text-2xl font-bold">
            {loading ? "..." : stats.unconscious}
          </p>
        </div>
        <div className="bg-white rounded-lg shadow p-4 border-l-4 border-blue-500">
          <p className="text-sm text-gray-500">활성 알림</p>
          <p className="text-2xl font-bold">
            {loading ? "..." : stats.activeAlerts}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 도면 미니맵 */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">건물 현황</h2>
          <BuildingOverview />

          {/* 작업자 상태 상세 (접이식) */}
          <details className="mt-4 pt-4 border-t">
            <summary className="text-sm font-medium text-gray-600 cursor-pointer hover:text-gray-900 select-none">
              작업자 상태 상세 ▸
            </summary>
            <div className="grid grid-cols-3 gap-2 mt-3">
              <div className="text-center p-2 bg-blue-50 rounded">
                <p className="text-xs text-gray-500">정상</p>
                <p className="text-lg font-bold text-blue-600">{stats.workerStates.normal}</p>
              </div>
              <div className="text-center p-2 bg-yellow-50 rounded">
                <p className="text-xs text-gray-500">혼란</p>
                <p className="text-lg font-bold text-yellow-600">{stats.workerStates.confused}</p>
              </div>
              <div className="text-center p-2 bg-orange-50 rounded">
                <p className="text-xs text-gray-500">지연</p>
                <p className="text-lg font-bold text-orange-600">{stats.workerStates.delayed}</p>
              </div>
              <div className="text-center p-2 bg-red-50 rounded">
                <p className="text-xs text-gray-500">위험</p>
                <p className="text-lg font-bold text-red-600">{stats.workerStates.at_risk}</p>
              </div>
              <div className="text-center p-2 bg-red-50 rounded">
                <p className="text-xs text-gray-500">구조필요</p>
                <p className="text-lg font-bold text-red-800">{stats.workerStates.rescue_needed}</p>
              </div>
              <div className="text-center p-2 bg-pink-50 rounded">
                <p className="text-xs text-gray-500">건강이상</p>
                <p className="text-lg font-bold text-pink-600">{stats.healthAnomalies}</p>
              </div>
            </div>
          </details>
        </div>

        {/* 실시간 알림 피드 */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">실시간 알림</h2>
          <div className="space-y-3 max-h-64 overflow-y-auto">
            {alertFeed.length === 0 ? (
              <p className="text-gray-400">알림이 없습니다.</p>
            ) : (
              alertFeed.map((alert) => (
                <div
                  key={alert.id}
                  className={`flex items-start gap-3 p-3 rounded-lg ${getAlertBgColor(alert.type)}`}
                >
                  <span className="text-lg">{getAlertIcon(alert.type)}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{alert.message}</p>
                    <p className="text-xs text-gray-500">
                      {alert.floor_id ? `${alert.floor_id}층` : ""}{" "}
                      {formatTime(alert.timestamp)}
                    </p>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// --- Helper Functions ---

function BuildingOverview() {
  const [floors, setFloors] = useState<Array<{ id: number; name?: string; floor_plan_url?: string }>>([]);
  const [selectedFloor, setSelectedFloor] = useState<{ id: number; name?: string; floor_plan_url?: string } | null>(null);
  const [workers, setWorkers] = useState<Array<{ user_id: number; x: number; y: number; status?: string }>>([]);
  const [fireAlerts, setFireAlerts] = useState<Array<{ x: number; y: number; message?: string }>>([]);
  // 도면 실제 크기 (FloorCanvas 기준 30000 x 12800)
  const PLAN_WIDTH = 30000;
  const PLAN_HEIGHT = 12800;

  useEffect(() => {
    async function load() {
      try {
        const bRes = await api.get("/api/buildings/");
        if (bRes.data.length > 0) {
          const fRes = await api.get(`/api/buildings/${bRes.data[0].id}/floors`);
          setFloors(fRes.data);
          if (fRes.data.length > 0) {
            // 1F가 있으면 선택, 없으면 첫 번째
            const f1 = fRes.data.find((f: { floor_number: number }) => f.floor_number === 1) || fRes.data[0];
            setSelectedFloor(f1);
          }
        }
      } catch { /* ignore */ }
    }
    load();
  }, []);

  useEffect(() => {
    if (!selectedFloor) return;
    async function loadWorkers() {
      try {
        const res = await api.get(`/api/locations/floor/${selectedFloor!.id}`);
        setWorkers(res.data);
      } catch {
        setWorkers([]);
      }
    }
    loadWorkers();
  }, [selectedFloor]);

  // 현재 층의 화재 알림 좌표 로드
  useEffect(() => {
    if (!selectedFloor) return;
    async function loadFireAlerts() {
      try {
        const res = await api.get("/api/alerts/active");
        const fires = (res.data as Array<{ type: string; floor_id?: number; x?: number; y?: number; message?: string }>)
          .filter((a) => a.type === "fire" && a.floor_id === selectedFloor!.id && a.x != null && a.y != null)
          .map((a) => ({ x: a.x!, y: a.y!, message: a.message }));
        setFireAlerts(fires);
      } catch {
        setFireAlerts([]);
      }
    }
    loadFireAlerts();
  }, [selectedFloor]);

  if (floors.length === 0) {
    return <p className="text-gray-400 text-sm">건물 데이터를 불러오는 중...</p>;
  }

  const floorPlanSrc = selectedFloor?.floor_plan_url || null;

  return (
    <div>
      {/* 층 탭 */}
      <div className="flex gap-1 mb-3">
        {floors.map((f) => (
          <button
            key={f.id}
            onClick={() => setSelectedFloor(f)}
            className={`px-3 py-1 rounded text-xs transition ${
              selectedFloor?.id === f.id ? "bg-red-100 text-red-700 font-medium" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            {f.name || `${f.id}층`}
          </button>
        ))}
      </div>

      {/* 도면 + 근로자 + 화재 위치 */}
      <div className="relative h-56 border rounded overflow-hidden bg-gray-50">
        {floorPlanSrc ? (
          <img src={floorPlanSrc} alt="도면" className="w-full h-full object-contain opacity-80" />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-300 text-sm">
            도면 미등록
          </div>
        )}
        {/* 화재 위치 마커 오버레이 */}
        {fireAlerts.map((fire, idx) => (
          <div
            key={`fire-${idx}`}
            className="absolute flex items-center justify-center"
            style={{
              left: `${(fire.x / PLAN_WIDTH) * 100}%`,
              top: `${(fire.y / PLAN_HEIGHT) * 100}%`,
              transform: "translate(-50%, -50%)",
            }}
            title={fire.message || "화재 발생 지점"}
          >
            <span className="absolute w-8 h-8 bg-red-500 rounded-full opacity-30 animate-ping" />
            <span className="relative text-lg">🔥</span>
          </div>
        ))}
        {/* 근로자 마커 오버레이 */}
        {workers.length > 0 && (
          <div className="absolute top-2 left-2 bg-white/80 rounded px-2 py-1 text-xs text-gray-600">
            재실자 {workers.length}명
          </div>
        )}
        {/* 화재 카운트 배지 */}
        {fireAlerts.length > 0 && (
          <div className="absolute top-2 right-2 bg-red-600 text-white rounded px-2 py-1 text-xs font-bold animate-pulse">
            🔥 화재 {fireAlerts.length}건
          </div>
        )}
      </div>
    </div>
  );
}

function getAlertIcon(type: string): string {
  switch (type) {
    case "fire_alert":
    case "fire":
      return "🔥";
    case "sos_alert":
    case "sos":
      return "🆘";
    case "peer_sos":
      return "🤝";
    case "unconscious":
      return "⚠️";
    case "health_anomaly":
      return "💓";
    default:
      return "🔔";
  }
}

function getAlertBgColor(type: string): string {
  switch (type) {
    case "fire_alert":
    case "fire":
      return "bg-red-50";
    case "sos_alert":
    case "sos":
    case "peer_sos":
      return "bg-orange-50";
    case "unconscious":
      return "bg-yellow-50";
    case "health_anomaly":
      return "bg-pink-50";
    default:
      return "bg-gray-50";
  }
}

function getAlertLabel(type: string): string {
  switch (type) {
    case "fire_alert":
      return "화재 발생";
    case "sos_alert":
      return "SOS 도움 요청";
    case "peer_sos":
      return "동료 SOS";
    case "health_anomaly":
      return "건강 이상 감지";
    default:
      return "알림";
  }
}

function formatTime(timestamp: string): string {
  try {
    const date = new Date(timestamp);
    return date.toLocaleTimeString("ko-KR", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return "";
  }
}
