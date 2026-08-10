import { useEffect, useState, useCallback } from "react";
import api, { getStoredAuth } from "../hooks/useApi";
import { useWebSocket, WSMessage } from "../hooks/useWebSocket";

interface DashboardStats {
  inBuilding: number;
  evacuating: number;
  unconscious: number;
  activeAlerts: number;
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
  });
  const [alertFeed, setAlertFeed] = useState<AlertFeedItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const { userId, role } = getStoredAuth();

  // 대시보드 데이터 로드
  const fetchStats = useCallback(async () => {
    try {
      const [evacuationRes, unconsciousRes, alertsRes] = await Promise.all([
        api.get("/api/evacuation/status"),
        api.get("/api/evacuation/unconscious"),
        api.get("/api/alerts/active"),
      ]);

      const evacuationData = evacuationRes.data as Array<{ status: string }>;
      const inBuilding = evacuationData.filter((s) => s.status === "in_building").length;
      const evacuating = evacuationData.filter((s) => s.status === "evacuating").length;

      setStats({
        inBuilding,
        evacuating,
        unconscious: (unconsciousRes.data as Array<unknown>).length,
        activeAlerts: (alertsRes.data as Array<unknown>).length,
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
    if (msg.type === "fire_alert" || msg.type === "sos_alert" || msg.type === "peer_sos") {
      const newAlert: AlertFeedItem = {
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        type: msg.type as string,
        message: (msg.message as string) || getAlertLabel(msg.type as string),
        floor_id: msg.floor_id as number | undefined,
        timestamp: new Date().toISOString(),
      };

      setAlertFeed((prev) => [newAlert, ...prev].slice(0, 20));

      // 통계도 즉시 갱신
      if (msg.type === "fire_alert") {
        setStats((prev) => ({ ...prev, activeAlerts: prev.activeAlerts + 1 }));
      }
    }

    // 대피 완료 시 카운터 업데이트
    if (msg.type === "evacuation_complete") {
      setStats((prev) => ({
        ...prev,
        inBuilding: Math.max(0, prev.inBuilding - 1),
      }));
    }
  }, []);

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
        <h1 className="text-2xl font-bold">FireEscape 관리자 대시보드</h1>
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
          <div className="h-64 flex items-center justify-center border-2 border-dashed border-gray-200 rounded">
            <p className="text-gray-400">층별 도면 + 근로자 위치 표시 영역</p>
          </div>
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
