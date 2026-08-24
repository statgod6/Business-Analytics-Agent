import { STAGE_NAMES, STAGE_COLORS } from "../types";
import { Check, Circle, Loader } from "lucide-react";

interface StageTimelineProps {
  currentStage: number | null;
  signedStages: Set<number>;
  onStageClick?: (stage: number) => void;
}

export default function StageTimeline({
  currentStage,
  signedStages,
  onStageClick,
}: StageTimelineProps) {
  return (
    <div className="stage-timeline mb-6">
      <div className="flex items-center justify-between gap-1">
        {[1, 2, 3, 4, 5, 6].map((stage) => {
          const isSigned = signedStages.has(stage);
          const isCurrent = stage === currentStage;
          const isPast = (currentStage !== null && stage < currentStage) || isSigned;

          return (
            <div key={stage} className="flex flex-1 flex-col items-center">
              <button
                disabled={!isPast && !isCurrent}
                onClick={() => onStageClick?.(stage)}
                className={`flex h-8 w-8 items-center justify-center rounded-full border-2 text-xs font-bold transition-all ${
                  isSigned
                    ? "border-emerald-500 bg-emerald-500/20 text-emerald-400"
                    : isCurrent
                      ? "border-sky-400 bg-sky-400/20 text-sky-400"
                      : isPast
                        ? "border-slate-600 bg-slate-800 text-slate-400"
                        : "border-slate-700 bg-slate-800/50 text-slate-600"
                } ${isCurrent ? "animate-pulse" : ""} cursor-pointer`}
              >
                {isSigned ? (
                  <Check size={14} />
                ) : isCurrent ? (
                  <Loader size={14} className="animate-spin" />
                ) : (
                  <Circle size={14} />
                )}
              </button>
              <span
                className={`mt-1 text-[10px] leading-tight ${
                  isCurrent
                    ? "text-sky-400"
                    : isSigned
                      ? "text-emerald-400"
                      : "text-slate-500"
                } ${STAGE_COLORS[stage]}`}
              >
                {STAGE_NAMES[stage]}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}