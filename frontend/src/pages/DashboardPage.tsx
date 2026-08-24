import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import * as runsApi from "../api/runs";
import type { Run } from "../types";
import { Plus, FileText, Loader } from "lucide-react";

export default function DashboardPage() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showNew, setShowNew] = useState(false);
  const [request, setRequest] = useState("");
  const [creating, setCreating] = useState(false);
  const navigate = useNavigate();

  const fetchRuns = async () => {
    try {
      const data = await runsApi.listRuns();
      setRuns(data.runs);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load runs");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchRuns();
  }, []);

  const createRun = async () => {
    if (!request.trim()) return;
    setCreating(true);
    try {
      const run = await runsApi.createRun(request.trim());
      navigate(`/runs/${run.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create run");
      setCreating(false);
    }
  };

  const statusColor = (status: string) => {
    switch (status) {
      case "completed":
        return "text-emerald-400 bg-emerald-500/10";
      case "running":
        return "text-sky-400 bg-sky-500/10";
      case "failed":
        return "text-rose-400 bg-rose-500/10";
      default:
        return "text-slate-400 bg-slate-500/10";
    }
  };

  return (
    <div className="mx-auto max-w-4xl">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-lg font-semibold text-slate-100">Analyses</h1>
        <button
          onClick={() => setShowNew((p: boolean) => !p)}
          className="flex items-center gap-1.5 rounded-md bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-emerald-500"
        >
          <Plus size={16} />
          New Analysis
        </button>
      </div>

      {/* New run form */}
      {showNew && (
        <div className="mb-6 rounded-lg border border-slate-700 bg-slate-800/50 p-4">
          <label className="mb-2 block text-sm font-medium text-slate-300">
            What business question would you like to analyze?
          </label>
          <textarea
            value={request}
            onChange={(e) => setRequest(e.target.value)}
            placeholder="e.g., Analyze our Q4 sales data and identify key growth drivers..."
            rows={3}
            className="mb-3 w-full rounded-md border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-slate-200 placeholder-slate-500 focus:border-emerald-500 focus:outline-none"
          />
          <div className="flex justify-end gap-2">
            <button
              onClick={() => setShowNew(false)}
              className="rounded-md px-3 py-1.5 text-sm text-slate-400 transition-colors hover:bg-slate-700"
            >
              Cancel
            </button>
            <button
              onClick={createRun}
              disabled={creating || !request.trim()}
              className="flex items-center gap-1.5 rounded-md bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-emerald-500 disabled:opacity-50"
            >
              {creating ? (
                <>
                  <Loader size={14} className="animate-spin" />
                  Starting...
                </>
              ) : (
                "Start Analysis"
              )}
            </button>
          </div>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="mb-4 rounded-md bg-rose-500/10 px-4 py-3 text-sm text-rose-400">
          {error}
          <button onClick={fetchRuns} className="ml-2 underline">
            Retry
          </button>
        </div>
      )}

      {/* Loading skeleton */}
      {isLoading && (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-20 animate-pulse rounded-lg bg-slate-800/50" />
          ))}
        </div>
      )}

      {/* Empty state */}
      {!isLoading && runs.length === 0 && !error && (
        <div className="rounded-lg border border-slate-700 bg-slate-800/30 p-12 text-center">
          <FileText size={40} className="mx-auto mb-3 text-slate-600" />
          <h2 className="mb-1 text-sm font-medium text-slate-400">
            No analyses yet
          </h2>
          <p className="mb-4 text-xs text-slate-500">
            Start your first business analysis to see it here
          </p>
          <button
            onClick={() => setShowNew(true)}
            className="inline-flex items-center gap-1.5 rounded-md bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-500"
          >
            <Plus size={16} />
            Start Analysis
          </button>
        </div>
      )}

      {/* Run list */}
      {!isLoading && runs.length > 0 && (
        <div className="space-y-2">
          {runs.map((run) => (
            <button
              key={run.id}
              onClick={() => navigate(`/runs/${run.id}`)}
              className="flex w-full items-center justify-between rounded-lg border border-slate-700 bg-slate-800/30 px-4 py-3 text-left transition-colors hover:bg-slate-800/60"
            >
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-slate-200">
                  {run.user_request}
                </p>
                <p className="mt-0.5 text-xs text-slate-500">
                  {new Date(run.created_at).toLocaleString()}
                  {run.current_stage && ` • Stage ${run.current_stage}/6`}
                </p>
              </div>
              <span
                className={`ml-3 shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium uppercase ${statusColor(run.status)}`}
              >
                {run.status}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}