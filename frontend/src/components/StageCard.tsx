import { STAGE_NAMES } from "../types";
import { CheckCircle, ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";

interface StageCardProps {
  stage: number;
  artifact: Record<string, unknown>;
}

export default function StageCard({ stage, artifact }: StageCardProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="rounded-lg border border-slate-700 bg-slate-800/50">
      <button
        onClick={() => setExpanded((p: boolean) => !p)}
        className="flex w-full items-center justify-between px-4 py-3 text-left"
      >
        <div className="flex items-center gap-2">
          <CheckCircle size={16} className="text-emerald-400" />
          <span className="text-sm font-medium text-slate-200">
            Stage {stage}: {STAGE_NAMES[stage]}
          </span>
        </div>
        {expanded ? (
          <ChevronUp size={16} className="text-slate-500" />
        ) : (
          <ChevronDown size={16} className="text-slate-500" />
        )}
      </button>

      {expanded && (
        <div className="border-t border-slate-700 px-4 py-3">
          {Object.entries(artifact).map(([key, value]) => (
            <div key={key} className="mb-2 last:mb-0">
              <span className="text-xs font-medium uppercase tracking-wide text-slate-500">
                {key.replace(/_/g, " ")}
              </span>
              <p className="mt-0.5 text-sm text-slate-300">
                {typeof value === "string"
                  ? value
                  : JSON.stringify(value, null, 2)}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}