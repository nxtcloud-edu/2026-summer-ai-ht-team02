import { useEffect, useRef, useState, useCallback } from "react";
import api from "./useApi";

/** 위치 수집 상태 */
export interface GeolocationState {
  latitude: number | null;
  longitude: number | null;
  accuracy: number | null;
  timestamp: number | null;
  error: string | null;
  isTracking: boolean;
}

/** 위치 수집 옵션 */
interface UseGeolocationOptions {
  /** 서버 전송 간격 (ms). 기본 5000ms */
  intervalMs?: number;
  /** 현재 층 ID (도면 매핑용) */
  floorId: number;
  /** 자동 시작 여부 */
  autoStart?: boolean;
  /** GPS 고정밀 모드 */
  enableHighAccuracy?: boolean;
}

const SEND_INTERVAL_DEFAULT = 5000;

/**
 * 스마트폰 GPS 위치를 수집하고 서버에 주기적으로 POST하는 훅
 *
 * 사용 예:
 * ```tsx
 * const { isTracking, start, stop, latitude, longitude, error } = useGeolocation({ floorId: 1 });
 * ```
 */
export function useGeolocation(options: UseGeolocationOptions): GeolocationState & {
  start: () => void;
  stop: () => void;
} {
  const {
    intervalMs = SEND_INTERVAL_DEFAULT,
    floorId,
    autoStart = true,
    enableHighAccuracy = true,
  } = options;

  const [state, setState] = useState<GeolocationState>({
    latitude: null,
    longitude: null,
    accuracy: null,
    timestamp: null,
    error: null,
    isTracking: false,
  });

  // 최신 위치를 ref로 저장 (interval 콜백에서 stale closure 방지)
  const latestPosition = useRef<{ lat: number; lng: number; acc: number } | null>(null);
  const watchIdRef = useRef<number | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const floorIdRef = useRef(floorId);

  // floorId 변경 추적
  useEffect(() => {
    floorIdRef.current = floorId;
  }, [floorId]);

  /** 서버에 위치 전송 */
  const sendLocationToServer = useCallback(async () => {
    const pos = latestPosition.current;
    if (!pos) return;

    try {
      await api.post("/api/locations/update", {
        floor_id: floorIdRef.current,
        x: pos.lng, // 경도 → x
        y: pos.lat, // 위도 → y
        accuracy: pos.acc,
      });
    } catch (err) {
      // 네트워크 오류 시 다음 주기에 재시도 — 조용히 실패
      console.warn("[Geolocation] 위치 전송 실패:", err);
    }
  }, []);

  /** GPS 추적 시작 */
  const start = useCallback(() => {
    if (!navigator.geolocation) {
      setState((prev) => ({ ...prev, error: "이 기기에서 위치 서비스를 지원하지 않습니다" }));
      return;
    }

    // watchPosition으로 지속적 위치 수신
    const watchId = navigator.geolocation.watchPosition(
      (position) => {
        const { latitude, longitude, accuracy } = position.coords;
        latestPosition.current = { lat: latitude, lng: longitude, acc: accuracy };
        setState((prev) => ({
          ...prev,
          latitude,
          longitude,
          accuracy,
          timestamp: position.timestamp,
          error: null,
          isTracking: true,
        }));
      },
      (err) => {
        let message = "위치를 가져올 수 없습니다";
        switch (err.code) {
          case err.PERMISSION_DENIED:
            message = "위치 권한이 거부되었습니다. 브라우저 설정에서 허용해주세요.";
            break;
          case err.POSITION_UNAVAILABLE:
            message = "위치 정보를 사용할 수 없습니다";
            break;
          case err.TIMEOUT:
            message = "위치 요청 시간이 초과되었습니다";
            break;
        }
        setState((prev) => ({ ...prev, error: message }));
      },
      {
        enableHighAccuracy,
        timeout: 10000,
        maximumAge: 3000,
      }
    );

    watchIdRef.current = watchId;

    // 주기적 서버 전송 (intervalMs 간격)
    const interval = setInterval(sendLocationToServer, intervalMs);
    intervalRef.current = interval;

    setState((prev) => ({ ...prev, isTracking: true }));
  }, [intervalMs, enableHighAccuracy, sendLocationToServer]);

  /** GPS 추적 중지 */
  const stop = useCallback(() => {
    if (watchIdRef.current !== null) {
      navigator.geolocation.clearWatch(watchIdRef.current);
      watchIdRef.current = null;
    }
    if (intervalRef.current !== null) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    setState((prev) => ({ ...prev, isTracking: false }));
  }, []);

  // 자동 시작 + 클린업
  useEffect(() => {
    if (autoStart) {
      start();
    }
    return () => {
      stop();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return { ...state, start, stop };
}

export default useGeolocation;
