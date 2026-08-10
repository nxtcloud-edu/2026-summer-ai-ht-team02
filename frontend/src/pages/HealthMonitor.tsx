import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceArea,
  ResponsiveContainer,
} from "recharts";
import api from "../hooks/useApi";

interface HealthHistoryItem {
  id: number;
  heart_rate: number | null;
  temperature: number | null;
  timestamp: string | null;
}

interface Baseline {
  avg_hr: number | null;
  std_hr: number | null;
  avg_temp: number | null;
  std_temp: number | null;
  sample_count: number;
  anomaly_count: number;
}

interface AnomalyUser {
  user_id: number;
  anomaly_count: number;
  avg_hr: number | null;
  latest_hr: number | null;
  latest_temp: number | null;
}

export default function HealthMonitor() {
  const [workers, setWorkers] = useState<Array<{ id: number; name: string }>>([]);
  const [selectedUser, setSelectedUser] = useState<number | null>(null);
  const [history, setHistory] = useState<HealthHistoryItem[]>([]);
  const [baseline, setBaseline] = useState<Baseline | null>(null);
  const [anomalyUsers, setAnomalyUsers] = useState<AnomalyUser[]>([]);

  // 근로자 목록 로드
  useEffect(() => {
    async function loadWorkers() {
      try {
        const res = await api.get("/api/auth/workers");
        setWorkers(res.data.map((w: { id: number; name: string }) => ({ id: w.id, name: w.name })));
        if (res.data.length > 0) setSelectedUser(res.data[0].id);
      } catch {
        // 권한 없으면 무시
      }
    }
    loadWorkers();
  }, []);

  // 이상 근로자 목록
  useEffect(() => {
    async function loadAnomalies() {
      try {
        const res = await api.get("/api/health/anomalies");
        setAnomalyUsers(res.data);
      } catch { /* ignore */ }
    }
    loadAnomalies();
    const interval = setInterval(loadAnomalies, 15000);
    return () => clearInterval(interval);
  }, []);

  // 선택된 유저 데이터 로드
  useEffect(() => {
    if (!selectedUser) return;
    async function loadData() {
      try {
        const [histRes, baseRes] = await Promise.all([
          api.get(`/api/health/history/${selectedUser}?limit=60`),
          api.get(`/api/health/baseline/${selectedUser}`).catch(() => ({ data: null })),
        ]);
        setHistory(histRes.data.reverse()); // 시간순 정렬
        setBaseline(baseRes.data);
      } catch {
        setHistory([]);
        setBaseline(null);
      }
    }
    loadData();
    const interval = setInterval(loadData, 10000);
    return () => clearInterval(interval);
  }, [selectedUser]);

  // 차트 데이터 변환
  const chartData = history.map((h, idx) => ({
    idx,
    time: h.timestamp ? new Date(h.timestamp).toLocaleTimeString("ko-KR", { hour: "2-digit", minute: "2-digit", second: "2-digit" }) : "",
    heart_rate: h.heart_rate,
    temperature: h.temperature,
    isAnomaly: baseline && baseline.avg_hr && baseline.std_hr && h.heart_rate
      ? Math.abs(h.heart_rate - baseline.avg_hr) > baseline.std_hr * 2
      : false,
  }));

  const hrUpper = baseline?.avg_hr && baseline?.std_hr ? baseline.avg_hr + baseline.std_hr * 2 : null;
  const hrLower = baseline?.avg_hr && baseline?.std_hr ? baseline.avg_hr - baseline.std_hr * 2 : null;

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">건강 모니터</h1>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* 사이드바: 근로자 선택 + 이상 목록 */}
        <div className="space-y-4">
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="font-semibold mb-3">근로자 선택</h3>
            <select
              className="w-full px-3 py-2 border rounded text-sm"
              value={selectedUser || ""}
              onChange={(e) => setSelectedUser(Number(e.target.value))}
            >
              <option value="" disabled>선택</option>
              {workers.map((w) => (
                <option key={w.id} value={w.id}>{w.name} (#{w.id})</option>
              ))}
            </select>
          </div>

          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="font-semibold mb-3 text-red-600">이상 감지 근로자</h3>
            {anomalyUsers.length === 0 ? (
              <p className="text-sm text-gray-400">이상 없음</p>
            ) : (
              <div className="space-y-2">
                {anomalyUsers.map((u) => (
                  <button
                    key={u.user_id}
                    onClick={() => setSelectedUser(u.user_id)}
                    className={`w-full text-left px-3 py-2 rounded text-sm transition ${
                      selectedUser === u.user_id ? "bg-red-100 text-red-700" : "bg-pink-50 hover:bg-pink-100"
                    }`}
                  >
                    <span className="font-medium">#{u.user_id}</span>
                    <span className="ml-2 text-xs text-red-500">
                      연속 {u.anomaly_count}회
                    </span>
                    {u.latest_hr && (
                      <span className="ml-1 text-xs text-gray-500">HR:{u.latest_hr}</span>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Baseline 정보 */}
          {baseline && (
            <div className="bg-white rounded-lg shadow p-4">
              <h3 className="font-semibold mb-2">Baseline</h3>
              <div className="text-sm space-y-1 text-gray-600">
                <p>심박 평균: {baseline.avg_hr?.toFixed(1) || "—"} bpm</p>
                <p>심박 편차: ±{baseline.std_hr?.toFixed(1) || "—"}</p>
                <p>체온 평균: {baseline.avg_temp?.toFixed(1) || "—"} °C</p>
                <p>샘플 수: {baseline.sample_count}</p>
                <p className={baseline.anomaly_count > 0 ? "text-red-600 font-medium" : ""}>
                  연속 이상: {baseline.anomaly_count}회
                </p>
              </div>
            </div>
          )}
        </div>

        {/* 차트 영역 */}
        <div className="lg:col-span-3 space-y-6">
          {/* 심박 차트 */}
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="font-semibold mb-4">심박수 (bpm)</h3>
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" tick={{ fontSize: 10 }} />
                <YAxis domain={["auto", "auto"]} />
                <Tooltip />
                <Legend />
                {/* Baseline 밴드 */}
                {hrUpper && hrLower && (
                  <ReferenceArea
                    y1={hrLower}
                    y2={hrUpper}
                    fill="#d1fae5"
                    fillOpacity={0.4}
                    label={{ value: "정상 범위", fontSize: 10, fill: "#6b7280" }}
                  />
                )}
                <Line
                  type="monotone"
                  dataKey="heart_rate"
                  stroke="#ef4444"
                  strokeWidth={2}
                  dot={(props: { cx: number; cy: number; payload: { isAnomaly: boolean } }) => {
                    const { cx, cy, payload } = props;
                    if (payload.isAnomaly) {
                      return <circle cx={cx} cy={cy} r={5} fill="#ef4444" stroke="#fff" strokeWidth={2} />;
                    }
                    return <circle cx={cx} cy={cy} r={2} fill="#ef4444" />;
                  }}
                  name="심박수"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* 체온 차트 */}
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="font-semibold mb-4">체온 (°C)</h3>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" tick={{ fontSize: 10 }} />
                <YAxis domain={[35, 40]} />
                <Tooltip />
                <Legend />
                {/* 38도 위험선 */}
                <ReferenceArea y1={38} y2={40} fill="#fef2f2" fillOpacity={0.5} />
                <Line
                  type="monotone"
                  dataKey="temperature"
                  stroke="#f97316"
                  strokeWidth={2}
                  dot={{ r: 2 }}
                  name="체온"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
