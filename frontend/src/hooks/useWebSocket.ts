import { useEffect, useRef, useState, useCallback } from "react";

/** WebSocket 메시지 타입 */
export interface WSMessage {
  type: string;
  [key: string]: unknown;
}

/** WebSocket 연결 상태 */
export interface WebSocketState {
  isConnected: boolean;
  lastMessage: WSMessage | null;
  error: string | null;
}

/** useWebSocket 옵션 */
interface UseWebSocketOptions {
  /** 사용자 ID */
  userId: number;
  /** 역할 (worker, admin, rescuer) */
  role?: string;
  /** 서버 URL (기본: ws://localhost:8000) */
  baseUrl?: string;
  /** 자동 연결 여부 (기본: true) */
  autoConnect?: boolean;
  /** 재연결 시도 간격 ms (기본: 3000) */
  reconnectInterval?: number;
  /** 최대 재연결 시도 횟수 (기본: 5) */
  maxReconnectAttempts?: number;
  /** 메시지 수신 콜백 */
  onMessage?: (message: WSMessage) => void;
  /** 연결 성공 콜백 */
  onConnect?: () => void;
  /** 연결 종료 콜백 */
  onDisconnect?: () => void;
}

const WS_BASE_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8000";

/**
 * WebSocket 실시간 연결 훅
 *
 * 사용 예:
 * ```tsx
 * const { isConnected, lastMessage, sendMessage } = useWebSocket({
 *   userId: 1,
 *   role: "worker",
 *   onMessage: (msg) => {
 *     if (msg.type === "fire_alert") { ... }
 *   },
 * });
 * ```
 */
export function useWebSocket(options: UseWebSocketOptions) {
  const {
    userId,
    role = "worker",
    baseUrl = WS_BASE_URL,
    autoConnect = true,
    reconnectInterval = 3000,
    maxReconnectAttempts = 5,
    onMessage,
    onConnect,
    onDisconnect,
  } = options;

  const [state, setState] = useState<WebSocketState>({
    isConnected: false,
    lastMessage: null,
    error: null,
  });

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isManualCloseRef = useRef(false);

  // 콜백 refs (stale closure 방지)
  const onMessageRef = useRef(onMessage);
  const onConnectRef = useRef(onConnect);
  const onDisconnectRef = useRef(onDisconnect);

  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);
  useEffect(() => {
    onConnectRef.current = onConnect;
  }, [onConnect]);
  useEffect(() => {
    onDisconnectRef.current = onDisconnect;
  }, [onDisconnect]);

  /** WebSocket 연결 */
  const connect = useCallback(() => {
    // 이미 연결 중이면 무시
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    isManualCloseRef.current = false;
    const url = `${baseUrl}/ws/${userId}?role=${role}`;

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        reconnectAttemptsRef.current = 0;
        setState((prev) => ({ ...prev, isConnected: true, error: null }));
        onConnectRef.current?.();
      };

      ws.onmessage = (event) => {
        try {
          const message: WSMessage = JSON.parse(event.data);
          setState((prev) => ({ ...prev, lastMessage: message }));
          onMessageRef.current?.(message);
        } catch {
          console.warn("[WebSocket] 메시지 파싱 실패:", event.data);
        }
      };

      ws.onclose = () => {
        setState((prev) => ({ ...prev, isConnected: false }));
        wsRef.current = null;
        onDisconnectRef.current?.();

        // 수동 종료가 아니면 자동 재연결
        if (!isManualCloseRef.current && reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current += 1;
          reconnectTimerRef.current = setTimeout(() => {
            connect();
          }, reconnectInterval);
        }
      };

      ws.onerror = () => {
        setState((prev) => ({
          ...prev,
          error: "WebSocket 연결 오류",
        }));
      };
    } catch (err) {
      setState((prev) => ({
        ...prev,
        error: "WebSocket 연결 실패",
      }));
    }
  }, [userId, role, baseUrl, reconnectInterval, maxReconnectAttempts]);

  /** WebSocket 연결 종료 */
  const disconnect = useCallback(() => {
    isManualCloseRef.current = true;
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setState((prev) => ({ ...prev, isConnected: false }));
  }, []);

  /** 서버로 메시지 전송 */
  const sendMessage = useCallback((data: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    } else {
      console.warn("[WebSocket] 연결되지 않은 상태에서 메시지 전송 시도");
    }
  }, []);

  // 자동 연결 + 클린업
  useEffect(() => {
    if (autoConnect) {
      connect();
    }
    return () => {
      disconnect();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId, role]);

  return {
    ...state,
    connect,
    disconnect,
    sendMessage,
  };
}

export default useWebSocket;
