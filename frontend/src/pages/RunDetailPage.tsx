import { useParams, Link } from "react-router-dom";
import { useRunDetail } from "../hooks/useRuns";
import { useWebSocket } from "../hooks/useWebSocket";
import { useCallback, useMemo } from "react";
import type { WSGateOpen } from "../types";
import StageTimeline from "../components/StageTimeline";
import StageCard from "../components/StageCard";
import GateReviewPanel from "../components/GateReviewPanel";
import { ArrowLeft, Wifi, WifiOff, Loader } from "lucide-react";

export default function RunDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { run, events, isConnected, isLoading, error, refetch } = useRunDetail(id);
  const { clearEvents } = useWebSocket(id);

  // Derive signed stages and current gate from WebSocket events
  const signedStages = useMemo(() => {
    const stages = new Set<number>();
    for (const ev of events) {
      if (ev.type === "stage_signed") {
        stages.add(ev.stage);
      }
    }
    return stages;
  }, [events]);

  const openGate = useMemo(() => {
    // Find the last gate_open that hasn't been closed
    let lastOpen: WSGateOpen | null = null;
    for (const ev of events) {
      if (ev.type === "gate_open") lastOpen = ev;
      if (ev.type === "gate_closed") lastOpen = null;
    }
    return lastOpen;
  }, [events]);

  const isRunComplete = run?.status === "completed";
  const isRunFailed = run?.status === "failed";
  const isRunning = run?.status === "running" || run?.status === "pending";

  const handleDecisionSubmitted = useCallback(() => {
    refetch();
  }, [refetch]);

  if (isLoading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-emerald-500 border-t-transparent" />
      </div>
    );
  }

  if (error || !run) {
    return (
      <div className="mx-auto max-w-4xl pt-8 text-center">
        <p className="text-sm text-rose-400">{error || "Run not found"}</p>
        <Link
          to="/dashboard"
          className="mt-4 inline-flex items-center gap-1 text-sm text-emerald-400 hover:text-emerald-300"
        >
          <ArrowLeft size={14} />
          Back to dashboard
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl">
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <Link
          to="/dashboard"
          className="flex items-center gap-1 text-sm text-slate-400 hover:text-slate-200"
        >
          <ArrowLeft size={14} />
          Back
        </Link>
        <div className="flex items-center gap-2">
          <span
            className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium uppercase ${
              isConnected
                ? "text-emerald-400 bg-emerald-500/10"
                : "text-slate-400 bg-slate-500/10"
            }`}
          >
            {isConnected ? (
              <Wifi size={10} />
            ) : (
              <WifiOff size={10} />
            )}
            {isConnected ? "Live" : "Offline"}
          </span>
          <span
            className={`rounded-full px-2 py-0.5 text-[10px] font-medium uppercase ${
              run.status === "completed"
                ? "text-emerald-400 bg-emerald-500/10"
                : run.status === "failed"
                  ? "text-rose-400 bg-rose-500/10"
                  : run.status === "running"
                    ? "text-sky-400 bg-sky-500/10"
                    : "text-slate-400 bg-slate-500/10"
            }`}
          >
            {run.status}
          </span>
        </div>
      </div>

      {/* User request */}
      <div className="mb-4">
        <h1 className="text-base font-semibold text-slate-100">Analysis Request</h1>
        <p className="mt-1 text-sm text-slate-300">{run.user_request}</p>
      </div>

      {/* Stage Timeline */}
      <StageTimeline
        currentStage={run.current_stage}
        signedStages={signedStages}
      />

      {/* Active Gate Review */}
      {openGate && (
        <div className="mb-6">
          <GateReviewPanel
            runId={id!}
            gateId={openGate.gate_id}
            stage={openGate.stage}
            question={openGate.question}
            artifact={openGate.artifact}
            onDecisionSubmitted={handleDecisionSubmitted}
          />
        </div>
      )}

      {/* Running state (no gate open) */}
      {isRunning && !openGate && (
        <div className="flex items-center justify-center gap-2 py-8 text-sm text-slate-400">
          <Loader size={16} className="animate-spin" />
          Processing... waiting for the next stage.
        </div>
      )}

      {/* Completed state */}
      {isRunComplete && (
        <div className="mb-6 rounded-lg border border-emerald-500/20 bg-emerald-500/5 px-4 py-3">
          <p className="text-sm font-medium text-emerald-400">
            Analysis complete
          </p>
          <p className="mt-1 text-xs text-slate-400">
            All 6 stages have been completed. View the artifacts below or start a new analysis.
          </p>
        </div>
      )}

      {/* Failed state */}
      {isRunFailed && (
        <div className="mb-6 rounded-lg border border-rose-500/20 bg-rose-500/5 px-4 py-3">
          <p className="text-sm font-medium text-rose-400">Analysis failed</p>
          <p className="mt-1 text-xs text-slate-400">
            {run.error || "An error occurred during processing."}
          </p>
          <Link
            to="/dashboard"
            className="mt-2 inline-flex items-center gap-1 text-xs text-rose-400 hover:text-rose-300"
          >
            <ArrowLeft size={12} />
            Back to dashboard
          </Link>
        </div>
      )}
    </div>
  );
}