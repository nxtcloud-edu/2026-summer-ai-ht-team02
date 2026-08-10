import { useState, useEffect, useRef, useCallback } from "react";
import api from "../hooks/useApi";

/** /api/evacuation/guidance 응답 타입 */
interface GuidanceData {
  success: boolean;
  direction: string | null;
  arrow: string | null;
  rotate_deg: number | null;
  distance_m: number | null;
  instruction: string | null;
  warning: string | null;
  next_landmark: string | null;
  bearing: number | null;
  total_distance_m: number | null;
  exit_name: string | null;
  arrived: boolean;
  message: string | null;
}

/** 방향 → 한국어 라벨 */
const DIRECTION_LABELS: Record<string, string> = {
  straight: "직진",
  slight_right: "우측 전방",
  right: "우회전",
  back: "뒤돌아",
  left: "좌회전",
  slight_left: "좌측 전방",
};

export default function NavigationPage() {
  const [guidance, setGuidance] = useState<GuidanceData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [gpsStatus, setGpsStatus] = useState<"waiting" | "active" | "error">("waiting");
  const [floorId, setFloorId] = useState<number>(2); // 기본 1F (id=2)
  const [heading, setHeading] = useState(0);

  const watchIdRef = useRef<number | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const latestPos = useRef<{ lat: number; lng: number } | null>(null);

  /** 서버에 guidance 요청 */
  const fetchGuidance = useCallback(async (x: number, y: number) => {
    try {
      const userId = localStorage.getItem("user_id");
      const res = await api.post<GuidanceData>("/api/evacuation/guidance", {
        floor_id: floorId,
        x,
        y,
        heading,
        user_id: userId ? Number(userId) : undefined,
      });
      setGuidance(res.data);
      setError(null);
    } catch (err: any) {
      const msg = err?.response?.data?.detail || "서버 연결 실패";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [floorId, heading]);

  /** GPS 추적 시작 */
  useEffect(() => {
    if (!navigator.geolocation) {
      setGpsStatus("error");
      setError("이 기기에서 위치 서비스를 지원하지 않습니다");
      setLoading(false);
      return;
    }

    const watchId = navigator.geolocation.watchPosition(
      (pos) => {
        latestPos.current = {
          lat: pos.coords.latitude,
          lng: pos.coords.longitude,
        };
        setGpsStatus("active");
      },
      (err) => {
        setGpsStatus("error");
        switch (err.code) {
          case err.PERMISSION_DENIED:
            setError("위치 권한이 거부되었습니다. 설정에서 허용해주세요.");
            break;
          case err.POSITION_UNAVAILABLE:
            setError("위치 정보를 사용할 수 없습니다");
            break;
          default:
            setError("위치 요청 시간 초과");
        }
        setLoading(false);
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 3000 }
    );
    watchIdRef.current = watchId;

    return () => {
      if (watchIdRef.current !== null) {
        navigator.geolocation.clearWatch(watchIdRef.current);
      }
    };
  }, []);

  /** 디바이스 방향 — Android Chrome absolute compass */
  useEffect(() => {
    const handleOrientation = (e: Event) => {
      const evt = e as DeviceOrientationEvent;
      if (evt.alpha !== null) {
        // Android Chrome: alpha = 디바이스 상단이 가리키는 절대 방위각 (0=북, 시계방향)
        setHeading(evt.alpha);
      }
    };

    // Android Chrome은 deviceorientationabsolute 지원 (권한 요청 불필요)
    const eventName = "ondeviceorientationabsolute" in window
      ? "deviceorientationabsolute"
      : "deviceorientation";

    window.addEventListener(eventName, handleOrientation);
    return () => window.removeEventListener(eventName, handleOrientation);
  }, []);

  /** 주기적 guidance fetch (5초) */
  useEffect(() => {
    // 초기 1회 요청 (GPS 없어도 데모용 고정 좌표)
    const doFetch = () => {
      if (latestPos.current) {
        // GPS → 서버에 경도(x), 위도(y) 전달 (서버가 앵커로 변환)
        fetchGuidance(latestPos.current.lng, latestPos.current.lat);
      }
    };

    // GPS 수신 후 첫 호출
    const startTimer = setTimeout(() => {
      doFetch();
      intervalRef.current = setInterval(doFetch, 5000);
    }, 1000);

    return () => {
      clearTimeout(startTimer);
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [fetchGuidance]);

  /** 데모 모드: GPS 없이 직접 좌표 입력 테스트 */
  const handleDemoFetch = () => {
    setLoading(true);
    // 1F 중앙 좌표 (도면 mm)
    fetchGuidance(15000, 6400);
  };

  // --- RENDER ---

  // 실시간 화살표 각도: 서버가 알려준 절대 방위(bearing)에서 현재 디바이스 heading을 빼면
  // "화면 기준으로 화살표가 가리킬 각도"가 된다.
  const serverBearing = guidance?.bearing ?? 0;
  const rotateDeg = ((serverBearing - heading) + 360) % 360;

  // 실시간 방향 라벨 계산
  const getRealtimeDirection = (deg: number): string => {
    if (deg < 20 || deg >= 340) return "straight";
    if (deg >= 20 && deg < 70) return "slight_right";
    if (deg >= 70 && deg < 150) return "right";
    if (deg >= 150 && deg < 210) return "back";
    if (deg >= 210 && deg < 290) return "left";
    return "slight_left";
  };
  const realtimeDirection = getRealtimeDirection(rotateDeg);

  return (
    <div className="min-h-screen bg-gray-900 text-white flex flex-col items-center justify-between p-4 select-none">
      {/* 상단: 상태 바 */}
      <header className="w-full max-w-md flex items-center justify-between py-2">
        <div className="flex items-center gap-2">
          <span
            className={`w-2.5 h-2.5 rounded-full ${
              gpsStatus === "active"
                ? "bg-green-400 animate-pulse"
                : gpsStatus === "error"
                ? "bg-red-400"
                : "bg-yellow-400 animate-pulse"
            }`}
          />
          <span className="text-xs text-gray-400">
            {gpsStatus === "active" ? "GPS 수신 중" : gpsStatus === "error" ? "GPS 오류" : "GPS 대기..."}
          </span>
        </div>
        <div className="text-xs text-gray-500">
          {guidance?.exit_name && `목표: ${guidance.exit_name}`}
        </div>
        {/* 층 선택 */}
        <select
          value={floorId}
          onChange={(e) => setFloorId(Number(e.target.value))}
          className="bg-gray-800 text-xs text-gray-300 border border-gray-700 rounded px-2 py-1"
          aria-label="층 선택"
        >
          <option value={2}>1F</option>
          <option value={3}>2F</option>
          <option value={4}>3F</option>
        </select>
      </header>

      {/* 경고 배너 */}
      {guidance?.warning && (
        <div className="w-full max-w-md bg-red-600/90 rounded-lg px-4 py-3 text-center text-sm font-medium animate-pulse">
          {guidance.warning}
        </div>
      )}

      {/* 중앙: 큰 화살표 */}
      <main className="flex-1 flex flex-col items-center justify-center gap-6 w-full max-w-md">
        {loading && !guidance ? (
          <div className="flex flex-col items-center gap-4">
            <div className="w-20 h-20 border-4 border-gray-600 border-t-blue-400 rounded-full animate-spin" />
            <p className="text-gray-400 text-sm">경로 계산 중...</p>
          </div>
        ) : error && !guidance ? (
          <div className="flex flex-col items-center gap-4">
            <div className="text-5xl">❌</div>
            <p className="text-red-400 text-center text-sm">{error}</p>
            <button
              onClick={handleDemoFetch}
              className="mt-4 px-4 py-2 bg-blue-600 rounded-lg text-sm hover:bg-blue-500 transition"
            >
              데모 모드로 테스트
            </button>
          </div>
        ) : guidance && !guidance.success ? (
          <div className="flex flex-col items-center gap-4">
            <div className="text-5xl">🚫</div>
            <p className="text-yellow-400 text-center">{guidance.message}</p>
          </div>
        ) : guidance && guidance.arrived ? (
          <div className="flex flex-col items-center gap-6">
            <div className="text-7xl animate-bounce">✅</div>
            <h2 className="text-2xl font-bold text-green-400">대피 완료!</h2>
            <p className="text-gray-300 text-center text-lg">
              출구에 도착했습니다.<br />건물 밖으로 이동하세요.
            </p>
            <div className="mt-4 px-6 py-3 bg-green-600/20 border border-green-500 rounded-xl text-center">
              <p className="text-green-400 text-sm">도착 출구</p>
              <p className="text-white text-xl font-semibold">{guidance.exit_name || "출구"}</p>
            </div>
          </div>
        ) : guidance ? (
          <>
            {/* 방향 라벨 */}
            <p className="text-lg text-gray-300 font-medium">
              {DIRECTION_LABELS[realtimeDirection] || "직진"}
            </p>

            {/* 대형 화살표 */}
            <div
              className="relative w-48 h-48 flex items-center justify-center"
              role="img"
              aria-label={`방향: ${guidance.instruction}`}
            >
              {/* 외곽 링 */}
              <div className="absolute inset-0 rounded-full border-4 border-gray-700" />
              {/* 화살표 SVG */}
              <svg
                viewBox="0 0 100 100"
                className="w-32 h-32 transition-transform duration-500 ease-out"
                style={{ transform: `rotate(${rotateDeg}deg)` }}
              >
                <polygon
                  points="50,10 70,60 50,50 30,60"
                  fill="currentColor"
                  className="text-blue-400"
                />
                <line
                  x1="50" y1="50" x2="50" y2="85"
                  stroke="currentColor"
                  strokeWidth="6"
                  strokeLinecap="round"
                  className="text-blue-400"
                />
              </svg>
            </div>

            {/* 거리 */}
            <div className="text-center">
              <span className="text-4xl font-bold text-white">
                {guidance.distance_m !== null ? Math.round(guidance.distance_m) : "?"}
              </span>
              <span className="text-xl text-gray-400 ml-1">m</span>
            </div>

            {/* 안내 문구 */}
            <p className="text-center text-gray-200 text-base px-4 leading-relaxed">
              {guidance.instruction}
            </p>
          </>
        ) : null}
      </main>

      {/* 하단: 요약 정보 */}
      <footer className="w-full max-w-md space-y-3 pb-4">
        {guidance?.success && (
          <div className="flex items-center justify-between bg-gray-800 rounded-xl px-4 py-3">
            <div className="text-center">
              <p className="text-xs text-gray-500">남은 거리</p>
              <p className="text-lg font-semibold">
                {guidance.total_distance_m !== null
                  ? `${Math.round(guidance.total_distance_m)}m`
                  : "-"}
              </p>
            </div>
            <div className="text-center">
              <p className="text-xs text-gray-500">다음</p>
              <p className="text-lg font-semibold">
                {guidance.next_landmark || "-"}
              </p>
            </div>
            <div className="text-center">
              <p className="text-xs text-gray-500">출구</p>
              <p className="text-lg font-semibold text-green-400">
                {guidance.exit_name || "-"}
              </p>
            </div>
          </div>
        )}

        {/* 데모 버튼 (GPS 미수신 시) */}
        {gpsStatus !== "active" && (
          <button
            onClick={handleDemoFetch}
            className="w-full py-3 bg-blue-600 hover:bg-blue-500 rounded-xl text-sm font-medium transition"
          >
            📍 데모 모드로 테스트 (GPS 없이)
          </button>
        )}
      </footer>
    </div>
  );
}
