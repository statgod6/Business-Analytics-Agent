import { useCallback, useEffect, useRef, useState } from "react";
import { getToken } from "../api/client";
import type { WSEvent } from "../types";

interface UseWebSocketReturn {
  events: WSEvent[];
  isConnected: boolean;
  clearEvents: () => void;
}

const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_BASE_MS = 1000;

export function useWebSocket(runId: string | undefined): UseWebSocketReturn {
  const [events, setEvents] = useState<WSEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout>>();
  const mountedRef = useRef(true);

  const clearEvents = useCallback(() => setEvents([]), []);

  const connect = useCallback(() => {
    if (!runId) return;

    const token = getToken();
    if (!token) return;

    const ws = new WebSocket(
      `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}/api/runs/${runId}/ws?token=${token}`,
    );

    ws.onopen = () => {
      setIsConnected(true);
      reconnectAttemptRef.current = 0;
    };

    ws.onmessage = (msg) => {
      try {
        const event = JSON.parse(msg.data) as WSEvent;
        setEvents((prev: WSEvent[]) => [...prev, event]);
      } catch {
        // ignore malformed messages
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      if (!mountedRef.current) return;

      // Auto-reconnect with exponential backoff
      if (reconnectAttemptRef.current < MAX_RECONNECT_ATTEMPTS) {
        const delay =
          RECONNECT_BASE_MS * 2 ** reconnectAttemptRef.current;
        reconnectAttemptRef.current += 1;
        reconnectTimerRef.current = setTimeout(connect, delay);
      }
    };

    ws.onerror = () => {
      ws.close();
    };

    wsRef.current = ws;
  }, [runId]);

  useEffect(() => {
    mountedRef.current = true;
    connect();

    return () => {
      mountedRef.current = false;
      clearTimeout(reconnectTimerRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return { events, isConnected, clearEvents };
}