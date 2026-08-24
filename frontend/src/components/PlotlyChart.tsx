import { lazy, Suspense } from "react";

const PlotlyComponent = lazy(() =>
  import("react-plotly.js").then((mod) => ({ default: mod.default })),
);

interface PlotlyChartProps {
  data: unknown[];
  layout: Record<string, unknown>;
}

export default function PlotlyChart({ data, layout }: PlotlyChartProps) {
  return (
    <Suspense
      fallback={
        <div className="flex h-48 items-center justify-center rounded-md bg-slate-800/50">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-emerald-500 border-t-transparent" />
        </div>
      }
    >
      <div className="w-full">
        <PlotlyComponent
          data={data}
          layout={
            {
              ...layout,
              autosize: true,
              paper_bgcolor: "rgba(0,0,0,0)",
              plot_bgcolor: "rgba(0,0,0,0)",
              font: { color: "#94a3b8" },
            } as Record<string, unknown>
          }
          useResizeHandler
          style={{ width: "100%", height: "100%" }}
          config={{ displayModeBar: false, responsive: true }}
        />
      </div>
    </Suspense>
  );
}