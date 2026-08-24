import { useEffect, useState } from "react";
import * as runsApi from "../api/runs";
import type { Run, WSEvent } from "../types";
import { useWebSocket } from "./useWebSocket";

interface UseRunDetailReturn {
  run: Run | null;
  events: WSEvent[];
  isConnected: boolean;
  isLoading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useRunDetail(runId: string | undefined): UseRunDetailReturn {
  const [run, setRun] = useState<Run | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { events, isConnected } = useWebSocket(runId);

  const fetchRun = async () => {
    if (!runId) return;
    try {
      const data = await runsApi.getRun(runId);
      setRun(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load run");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchRun();
  }, [runId]); // eslint-disable-line react-hooks/exhaustive-deps

  // Update run status from WebSocket events
  useEffect(() => {
    if (events.length === 0) return;
    const last = events[events.length - 1];

    if (last.type === "run_complete") {
      setRun((prev: Run | null) => (prev ? { ...prev, status: "completed" } : prev));
      // Refresh to get final result
      fetchRun();
    }
    if (last.type === "run_error") {
      setRun((prev: Run | null) =>
        prev ? { ...prev, status: "failed", error: last.detail } : prev,
      );
    }
    if (last.type === "run_started") {
      setRun((prev: Run | null) => (prev ? { ...prev, status: "running" } : prev));
    }
  }, [events]); // eslint-disable-line react-hooks/exhaustive-deps

  return { run, events, isConnected, isLoading, error, refetch: fetchRun };
}