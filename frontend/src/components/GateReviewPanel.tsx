import { useState } from "react";
import type { GateDecisionIn } from "../types";
import { submitDecision } from "../api/runs";
import { CheckCircle, RotateCcw, ArrowLeft, PenSquare } from "lucide-react";

type DecisionMode = "approve" | "regenerate" | "send_back" | "edit";

interface GateReviewPanelProps {
  runId: string;
  gateId: string;
  stage: number;
  question: string;
  artifact: Record<string, unknown> | null;
  onDecisionSubmitted: () => void;
}

export default function GateReviewPanel({
  runId,
  gateId,
  stage,
  question,
  onDecisionSubmitted,
}: GateReviewPanelProps) {
  const [mode, setMode] = useState<DecisionMode>("approve");
  const [feedback, setFeedback] = useState("");
  const [targetStage, setTargetStage] = useState<number>(Math.max(1, stage - 1));
  const [editPayload, setEditPayload] = useState(
    "{\n  \n}",
  );
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const modes: { key: DecisionMode; label: string; icon: typeof CheckCircle }[] = [
    { key: "approve", label: "Approve", icon: CheckCircle },
    { key: "regenerate", label: "Regenerate", icon: RotateCcw },
    { key: "send_back", label: "Send Back", icon: ArrowLeft },
    { key: "edit", label: "Edit", icon: PenSquare },
  ];

  const handleSubmit = async () => {
    setSubmitting(true);
    setError(null);

    const payload: GateDecisionIn = {
      action: mode,
      feedback: feedback || undefined,
    };

    if (mode === "send_back") {
      payload.target_stage = targetStage;
    }
    if (mode === "edit") {
      try {
        payload.edit_payload = JSON.parse(editPayload) as Record<string, unknown>;
      } catch {
        setError("Invalid JSON in edit payload");
        setSubmitting(false);
        return;
      }
    }

    try {
      await submitDecision(runId, gateId, payload);
      onDecisionSubmitted();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit decision");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="gate-panel rounded-lg border border-slate-700 bg-slate-800/80 p-4 md:p-6">
      <h3 className="mb-1 text-lg font-semibold text-slate-100">Gate Review</h3>
      <p className="mb-4 text-sm text-slate-400">{question}</p>

      {/* Mode selector */}
      <div className="mb-4 flex flex-wrap gap-2">
        {modes.map((m) => {
          const Icon = m.icon;
          const isActive = mode === m.key;
          const base =
            "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors";
          const activeMap: Record<string, string> = {
            approve: "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30",
            regenerate: "bg-amber-500/20 text-amber-400 border border-amber-500/30",
            send_back: "bg-rose-500/20 text-rose-400 border border-rose-500/30",
            edit: "bg-sky-500/20 text-sky-400 border border-sky-500/30",
          };

          return (
            <button
              key={m.key}
              onClick={() => setMode(m.key)}
              className={`${base} ${
                isActive
                  ? activeMap[m.key]
                  : "border border-slate-600 text-slate-400 hover:bg-slate-700"
              }`}
            >
              <Icon size={14} />
              {m.label}
            </button>
          );
        })}
      </div>

      {/* Mode-specific inputs */}
      <div className="mb-4 space-y-3">
        <div>
          <label className="mb-1 block text-xs font-medium text-slate-400">
            Feedback {mode !== "approve" && "(required)"}
          </label>
          <textarea
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            placeholder={
              mode === "approve"
                ? "Optional feedback..."
                : "Describe what needs to change..."
            }
            rows={3}
            className="w-full rounded-md border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-slate-200 placeholder-slate-500 focus:border-emerald-500 focus:outline-none"
          />
        </div>

        {mode === "send_back" && (
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-400">
              Target Stage
            </label>
            <select
              value={targetStage}
              onChange={(e) => setTargetStage(Number(e.target.value))}
              className="w-full rounded-md border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-slate-200 focus:border-emerald-500 focus:outline-none"
            >
              {[1, 2, 3, 4, 5].map((s) => (
                <option key={s} value={s}>
                  Stage {s}
                </option>
              ))}
            </select>
          </div>
        )}

        {mode === "edit" && (
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-400">
              Edit Payload (JSON)
            </label>
            <textarea
              value={editPayload}
              onChange={(e) => setEditPayload(e.target.value)}
              rows={4}
              className="w-full rounded-md border border-slate-600 bg-slate-900 px-3 py-2 font-mono text-xs text-slate-200 focus:border-emerald-500 focus:outline-none"
            />
          </div>
        )}
      </div>

      {error && (
        <div className="mb-3 rounded-md bg-rose-500/10 px-3 py-2 text-xs text-rose-400">
          {error}
        </div>
      )}

      <button
        onClick={handleSubmit}
        disabled={submitting}
        className="flex w-full items-center justify-center gap-2 rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-emerald-500 disabled:opacity-50"
      >
        {submitting ? (
          <>
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
            Submitting...
          </>
        ) : (
          "Submit Decision"
        )}
      </button>
    </div>
  );
}